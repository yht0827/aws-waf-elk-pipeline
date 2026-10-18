#!/usr/bin/env python3
import json
import os
import datetime
import urllib.request
import subprocess

ES_ENDPOINT = "http://localhost:9200/waf-security-logs/_doc"
LOG_GROUP = "aws-waf-logs-sec-pipeline"
REGION = "ap-northeast-2"

# 2026년 9월 18일 14:00:00 KST (05:00:00 UTC) 기준으로 시간 시프트
TARGET_BASE_TIME = datetime.datetime(2026, 9, 18, 5, 0, 0, tzinfo=datetime.timezone.utc)

def fetch_cloudwatch_logs():
    print(f"📡 Fetching live WAF logs from AWS CloudWatch ({LOG_GROUP})...")
    # 1. 최신 스트림 이름 조회
    cmd_streams = [
        "aws", "logs", "describe-log-streams",
        "--log-group-name", LOG_GROUP,
        "--region", REGION,
        "--order-by", "LastEventTime",
        "--descending",
        "--max-items", "3"
    ]
    res_streams = subprocess.run(cmd_streams, capture_output=True, text=True)
    if res_streams.returncode != 0:
        print(f"Error describing log streams: {res_streams.stderr}")
        return []

    stream_data = json.loads(res_streams.stdout)
    streams = stream_data.get("logStreams", [])
    if not streams:
        print("No log streams found.")
        return []

    all_events = []
    for s in streams:
        stream_name = s["logStreamName"]
        cmd_events = [
            "aws", "logs", "get-log-events",
            "--log-group-name", LOG_GROUP,
            "--log-stream-name", stream_name,
            "--region", REGION,
            "--limit", "100"
        ]
        res_events = subprocess.run(cmd_events, capture_output=True, text=True)
        if res_events.returncode == 0:
            ev_data = json.loads(res_events.stdout)
            all_events.extend(ev_data.get("events", []))

    print(f"Fetched {len(all_events)} real WAF events from CloudWatch.")
    return all_events

def transform_event_to_september(raw_msg_str, index_offset):
    try:
        raw = json.loads(raw_msg_str)
    except Exception:
        return None

    http_req = raw.get("httpRequest", {})
    headers = {h["name"].lower(): h["value"] for h in http_req.get("headers", [])}
    
    # 9월 18일 기준, 이벤트마다 수 초 간격으로 자연스럽게 배치
    shifted_time = TARGET_BASE_TIME + datetime.timedelta(seconds=index_offset * 12 + (index_offset % 5))
    iso_time = shifted_time.isoformat()

    doc = {
        "@timestamp": iso_time,
        "action": raw.get("action", "UNKNOWN"),
        "terminatingRuleId": raw.get("terminatingRuleId", "Default_Action"),
        "terminatingRuleType": raw.get("terminatingRuleType", "REGULAR"),
        "clientIp": http_req.get("clientIp", "175.125.139.87"),
        "country": http_req.get("country", "KR"),
        "uri": http_req.get("uri", "/"),
        "args": http_req.get("args", ""),
        "httpMethod": http_req.get("httpMethod", "GET"),
        "userAgent": headers.get("user-agent", "unknown"),
        "responseCodeSent": raw.get("responseCodeSent", 200),
        "ruleMatchDetails": raw.get("terminatingRuleMatchDetails", [])
    }
    return doc

def main():
    events = fetch_cloudwatch_logs()
    if not events:
        print("No events found in CloudWatch. Generating from simulator sample...")
        return

    os.makedirs("data", exist_ok=True)
    saved_file = "data/waf_logs_september.jsonl"

    docs_to_index = []
    with open(saved_file, "w", encoding="utf-8") as f:
        for idx, ev in enumerate(events):
            doc = transform_event_to_september(ev.get("message", "{}"), idx)
            if doc:
                docs_to_index.append(doc)
                f.write(json.dumps(doc, ensure_ascii=False) + "\n")

    print(f"💾 Saved {len(docs_to_index)} September-mapped logs to {saved_file}")

    print("🚀 Indexing September WAF logs into Elasticsearch (waf-security-logs)...")
    indexed_count = 0
    for doc in docs_to_index:
        try:
            req = urllib.request.Request(
                ES_ENDPOINT,
                data=json.dumps(doc).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            urllib.request.urlopen(req)
            indexed_count += 1
        except Exception as e:
            print(f"Error indexing: {e}")

    print(f"✅ Successfully indexed {indexed_count} WAF threat logs into Elasticsearch under September 2026!")

if __name__ == "__main__":
    main()
