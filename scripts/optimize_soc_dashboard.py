#!/usr/bin/env python3
import json
import urllib.request
import uuid

KIBANA_URL = "http://localhost:5601"
DATA_VIEW_ID = "fd79cc11-4a0d-44d5-ae16-1a4d2e6c3b3d"
DASHBOARD_ID = "903ed5d6-6d02-4786-827c-d2b77990f82c"

def post_lens(title, vis_type, state_vis, datasource_layers, query_str=""):
    payload = {
        "attributes": {
            "title": title,
            "visualizationType": vis_type,
            "state": {
                "visualization": state_vis,
                "query": {"query": query_str, "language": "kuery"},
                "filters": [],
                "datasourceStates": {
                    "formBased": {"layers": datasource_layers},
                    "indexpattern": {"layers": {}},
                    "textBased": {"layers": {}}
                },
                "internalReferences": [],
                "adHocDataViews": {}
            }
        },
        "references": []
    }
    for layer_id in datasource_layers.keys():
        payload["references"].append({
            "type": "index-pattern",
            "id": DATA_VIEW_ID,
            "name": f"indexpattern-datasource-layer-{layer_id}"
        })

    req = urllib.request.Request(
        f"{KIBANA_URL}/api/saved_objects/lens",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "kbn-xsrf": "true"},
        method="POST"
    )
    res = json.loads(urllib.request.urlopen(req).read())
    return res["id"]

# 1. 상단 3개 메트릭 (Lens Metric)
def create_lens_metric(title, query_str, label):
    l_id = str(uuid.uuid4())
    col_id = str(uuid.uuid4())
    state_vis = {
        "layerId": l_id,
        "layerType": "data",
        "metricAccessor": col_id,
        "showBar": False
    }
    layers = {
        l_id: {
            "columns": {
                col_id: {
                    "label": label,
                    "dataType": "number",
                    "operationType": "count",
                    "isBucketed": False,
                    "scale": "ratio",
                    "sourceField": "___records___",
                    "params": {"emptyAsNull": False}
                }
            },
            "columnOrder": [col_id],
            "incompleteColumns": {},
            "sampling": 1
        }
    }
    return post_lens(title, "lnsMetric", state_vis, layers, query_str)

# 2. 피격 룰셋 순위 (Default_Action 제거하고 오직 차단된 위협만!)
def create_blocked_rules_chart():
    l_id = str(uuid.uuid4())
    col_term = str(uuid.uuid4())
    col_count = str(uuid.uuid4())
    state_vis = {
        "legend": {"isVisible": False, "position": "right"},
        "valueLabels": "show",
        "preferredSeriesType": "bar_horizontal",
        "yTitle": "탐지 룰셋",
        "xTitle": "차단 건수",
        "layers": [{
            "layerId": l_id,
            "accessors": [col_count],
            "position": "top",
            "seriesType": "bar_horizontal",
            "showGridlines": False,
            "layerType": "data",
            "xAccessor": col_term
        }]
    }
    layers = {
        l_id: {
            "columns": {
                col_term: {
                    "label": "WAF 탐지 룰셋",
                    "dataType": "string",
                    "operationType": "terms",
                    "scale": "ordinal",
                    "sourceField": "terminatingRuleId.keyword",
                    "isBucketed": True,
                    "params": {
                        "size": 5,
                        "orderBy": {"type": "column", "columnId": col_count},
                        "orderDirection": "desc",
                        "otherBucket": False,
                        "missingBucket": False
                    }
                },
                col_count: {
                    "label": "차단 건수",
                    "dataType": "number",
                    "operationType": "count",
                    "isBucketed": False,
                    "scale": "ratio",
                    "sourceField": "___records___"
                }
            },
            "columnOrder": [col_term, col_count],
            "incompleteColumns": {},
            "sampling": 1
        }
    }
    return post_lens("WAF 차단 룰셋별 피격 순위 (Threat Defense)", "lnsXY", state_vis, layers, query_str="action: \"BLOCK\"")

# 3. 악성 공격 도구 / 스캐너 (Data Table 형태로 깔끔하게 표현!)
def create_user_agent_table():
    l_id = str(uuid.uuid4())
    col_term = str(uuid.uuid4())
    col_count = str(uuid.uuid4())
    state_vis = {
        "layerId": l_id,
        "columns": [
            {"columnId": col_term},
            {"columnId": col_count}
        ]
    }
    layers = {
        l_id: {
            "columns": {
                col_term: {
                    "label": "공격 도구 / User-Agent",
                    "dataType": "string",
                    "operationType": "terms",
                    "scale": "ordinal",
                    "sourceField": "userAgent.keyword",
                    "isBucketed": True,
                    "params": {
                        "size": 6,
                        "orderBy": {"type": "column", "columnId": col_count},
                        "orderDirection": "desc",
                        "otherBucket": False,
                        "missingBucket": False
                    }
                },
                col_count: {
                    "label": "공격 요청 건수",
                    "dataType": "number",
                    "operationType": "count",
                    "isBucketed": False,
                    "scale": "ratio",
                    "sourceField": "___records___"
                }
            },
            "columnOrder": [col_term, col_count],
            "incompleteColumns": {},
            "sampling": 1
        }
    }
    return post_lens("악성 공격 도구 / 스캐너 목록 (Top User-Agents)", "lnsDatatable", state_vis, layers, query_str="action: \"BLOCK\"")

def main():
    print("🚀 Rebuilding SOC Dashboard panels with refined schemas...")
    m_total = create_lens_metric("전체 인입 트래픽", "", "전체 요청 수")
    m_block = create_lens_metric("차단된 위협 공격", "action: \"BLOCK\"", "위협 차단 수")
    m_allow = create_lens_metric("정상 허용 트래픽", "action: \"ALLOW\"", "정상 허용 수")
    rules_chart = create_blocked_rules_chart()
    ua_table = create_user_agent_table()
    print("✅ Created refined panels!")

    # Fetch existing dashboard to preserve Timeline, Donut, Map, IP
    req = urllib.request.Request(f"{KIBANA_URL}/api/saved_objects/dashboard/{DASHBOARD_ID}", headers={"kbn-xsrf": "true"})
    dash = json.loads(urllib.request.urlopen(req).read())
    old_panels = json.loads(dash["attributes"]["panelsJSON"])
    old_refs = dash["references"]

    # Reconstruct 10 panels grid
    panels = []
    refs = []

    def add_panel(lens_id, x, y, w, h, title):
        p_idx = str(uuid.uuid4())
        ref_name = f"panel_{p_idx}"
        panels.append({
            "type": "lens",
            "gridData": {"x": x, "y": y, "w": w, "h": h, "i": p_idx},
            "panelIndex": p_idx,
            "embeddableConfig": {},
            "panelRefName": ref_name,
            "title": title
        })
        refs.append({
            "name": f"{p_idx}:{ref_name}",
            "type": "lens",
            "id": lens_id
        })

    # Row 1 (y: 0, h: 4) - 3 Top Metric Cards
    add_panel(m_total, x=0, y=0, w=16, h=4, title="전체 인입 트래픽")
    add_panel(m_block, x=16, y=0, w=16, h=4, title="차단된 위협 공격")
    add_panel(m_allow, x=32, y=0, w=16, h=4, title="정상 허용 트래픽")

    # Row 2 (y: 4, h: 12) - Timeline & Donut from old
    timeline_ref = next((r for r in old_refs if "55ced436" in r.get("name", "")), None)
    donut_ref = next((r for r in old_refs if "7392224e" in r.get("name", "")), None)
    if timeline_ref:
        add_panel(timeline_ref["id"], x=0, y=4, w=30, h=12, title="실시간 위협 발생 및 차단 추이")
    if donut_ref:
        add_panel(donut_ref["id"], x=30, y=4, w=18, h=12, title="WAF 차단 및 룰셋 비율")

    # Row 3 (y: 16, h: 14) - World Map & NEW Blocked Rules (Default_Action 제거됨!)
    map_panel = next((p for p in old_panels if p.get("title") == "공격자 국가별 분포"), None)
    if map_panel:
        map_panel["gridData"] = {"x": 0, "y": 16, "w": 24, "h": 14, "i": map_panel["panelIndex"]}
        panels.append(map_panel)
        for r in old_refs:
            if "71e6bce6" in r.get("name", ""):
                refs.append(r)
    add_panel(rules_chart, x=24, y=16, w=24, h=14, title="WAF 차단 룰셋별 피격 순위 (BLOCK Only)")

    # Row 4 (y: 30, h: 12) - Top URIs, Top IPs, NEW User-Agent Data Table
    uri_panel = next((p for p in old_panels if p.get("title") == "공격당한 URI 경로 순위"), None)
    if uri_panel:
        uri_panel["gridData"] = {"x": 0, "y": 30, "w": 16, "h": 12, "i": uri_panel["panelIndex"]}
        panels.append(uri_panel)
        for r in old_refs:
            if "d56226c5" in r.get("name", ""):
                refs.append(r)

    ips_ref = next((r for r in old_refs if "29ee0eae" in r.get("name", "")), None)
    if ips_ref:
        add_panel(ips_ref["id"], x=16, y=30, w=16, h=12, title="최다 공격자 IP Top 5")

    # User-Agent Table!
    add_panel(ua_table, x=32, y=30, w=16, h=12, title="악성 공격 도구 / 스캐너 (User-Agent)")

    # Update Dashboard
    dash["attributes"]["panelsJSON"] = json.dumps(panels)
    dash["references"] = refs
    dash["attributes"]["title"] = "AWS WAF Enterprise SOC Threat Intelligence Dashboard"

    req_update = urllib.request.Request(
        f"{KIBANA_URL}/api/saved_objects/dashboard/{DASHBOARD_ID}",
        data=json.dumps({"attributes": dash["attributes"], "references": refs}).encode("utf-8"),
        headers={"Content-Type": "application/json", "kbn-xsrf": "true"},
        method="PUT"
    )
    urllib.request.urlopen(req_update)
    print("🎉 Dashboard successfully upgraded with crystal clear panels!")

if __name__ == "__main__":
    main()
