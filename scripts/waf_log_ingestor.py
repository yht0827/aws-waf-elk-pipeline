import json
import datetime
import urllib.request
import os

ES_ENDPOINT = "http://localhost:9200/waf-security-logs/_doc"

def transform_waf_log(raw_log: dict) -> dict:
    http_req = raw_log.get("httpRequest", {})
    headers = {h["name"].lower(): h["value"] for h in http_req.get("headers", [])}
    
    ts_ms = raw_log.get("timestamp", int(datetime.datetime.now().timestamp() * 1000))
    iso_time = datetime.datetime.fromtimestamp(ts_ms / 1000.0, tz=datetime.timezone.utc).isoformat()

    return {
        "@timestamp": iso_time,
        "action": raw_log.get("action", "UNKNOWN"),
        "terminatingRuleId": raw_log.get("terminatingRuleId", "Default_Action"),
        "terminatingRuleType": raw_log.get("terminatingRuleType", "REGULAR"),
        "clientIp": http_req.get("clientIp", "127.0.0.1"),
        "country": http_req.get("country", "KR"),
        "uri": http_req.get("uri", "/"),
        "args": http_req.get("args", ""),
        "httpMethod": http_req.get("httpMethod", "GET"),
        "userAgent": headers.get("user-agent", "unknown"),
    }

def ingest_file(filepath: str):
    if not os.path.exists(filepath):
        print(f"[ERROR] File not found: {filepath}")
        return

    count = 0
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                raw = json.loads(line)
                doc = transform_waf_log(raw)
                req = urllib.request.Request(
                    ES_ENDPOINT,
                    data=json.dumps(doc).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST"
                )
                urllib.request.urlopen(req)
                count += 1
            except Exception as e:
                print(f"[ERROR] Indexing failure: {e}")
                
    print(f"[SUCCESS] Successfully indexed {count} WAF logs into Elasticsearch (index: waf-security-logs)")

if __name__ == "__main__":
    import sys
    target = sys.argv[1] if len(sys.argv) > 1 else "data/sample_waf_logs.jsonl"
    ingest_file(target)
