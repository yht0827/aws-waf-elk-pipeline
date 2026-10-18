import json
import urllib.request
import uuid

KIBANA_URL = "http://localhost:5601"
DATA_VIEW_ID = "fd79cc11-4a0d-44d5-ae16-1a4d2e6c3b3d"
DASHBOARD_ID = "903ed5d6-6d02-4786-827c-d2b77990f82c"

def post_saved_object(obj_type, payload):
    req = urllib.request.Request(
        f"{KIBANA_URL}/api/saved_objects/{obj_type}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "kbn-xsrf": "true"},
        method="POST"
    )
    with urllib.request.urlopen(req) as res:
        return json.loads(res.read())

def create_metric(title, query_str, label):
    layer_id = str(uuid.uuid4())
    col_count = str(uuid.uuid4())
    ref_name = f"indexpattern-datasource-layer-{layer_id}"
    payload = {
        "attributes": {
            "title": title,
            "visualizationType": "lnsMetric",
            "state": {
                "visualization": {
                    "layerId": layer_id,
                    "accessor": col_count,
                    "layerType": "data"
                },
                "query": {"query": query_str, "language": "kuery"},
                "filters": [],
                "datasourceStates": {
                    "formBased": {
                        "layers": {
                            layer_id: {
                                "columns": {
                                    col_count: {
                                        "label": label,
                                        "dataType": "number",
                                        "operationType": "count",
                                        "isBucketed": False,
                                        "scale": "ratio",
                                        "sourceField": "___records___",
                                        "params": {"emptyAsNull": True}
                                    }
                                },
                                "columnOrder": [col_count],
                                "incompleteColumns": {},
                                "sampling": 1
                            }
                        }
                    },
                    "indexpattern": {"layers": {}},
                    "textBased": {"layers": {}}
                },
                "internalReferences": [],
                "adHocDataViews": {}
            }
        },
        "references": [{"type": "index-pattern", "id": DATA_VIEW_ID, "name": ref_name}]
    }
    res = post_saved_object("lens", payload)
    print(f"[SUCCESS] Metric created: {title} ({res['id']})")
    return res["id"]

def create_bar_chart(title, field_name, label, top_n=5, is_horizontal=False):
    layer_id = str(uuid.uuid4())
    col_term = str(uuid.uuid4())
    col_count = str(uuid.uuid4())
    ref_name = f"indexpattern-datasource-layer-{layer_id}"
    stype = "bar_horizontal" if is_horizontal else "bar_stacked"
    payload = {
        "attributes": {
            "title": title,
            "visualizationType": "lnsXY",
            "state": {
                "visualization": {
                    "legend": {"isVisible": True, "position": "right"},
                    "valueLabels": "hide",
                    "preferredSeriesType": stype,
                    "layers": [{
                        "layerId": layer_id,
                        "accessors": [col_count],
                        "position": "top",
                        "seriesType": stype,
                        "showGridlines": False,
                        "layerType": "data",
                        "xAccessor": col_term
                    }]
                },
                "query": {"query": "", "language": "kuery"},
                "filters": [],
                "datasourceStates": {
                    "formBased": {
                        "layers": {
                            layer_id: {
                                "columns": {
                                    col_term: {
                                        "label": label,
                                        "dataType": "string",
                                        "operationType": "terms",
                                        "scale": "ordinal",
                                        "sourceField": field_name,
                                        "isBucketed": True,
                                        "params": {
                                            "size": top_n,
                                            "orderBy": {"type": "column", "columnId": col_count},
                                            "orderDirection": "desc",
                                            "otherBucket": False,
                                            "missingBucket": False
                                        }
                                    },
                                    col_count: {
                                        "label": "건수",
                                        "dataType": "number",
                                        "operationType": "count",
                                        "isBucketed": False,
                                        "scale": "ratio",
                                        "sourceField": "___records___",
                                        "params": {"emptyAsNull": True}
                                    }
                                },
                                "columnOrder": [col_term, col_count],
                                "incompleteColumns": {},
                                "sampling": 1
                            }
                        }
                    },
                    "indexpattern": {"layers": {}},
                    "textBased": {"layers": {}}
                },
                "internalReferences": [],
                "adHocDataViews": {}
            }
        },
        "references": [{"type": "index-pattern", "id": DATA_VIEW_ID, "name": ref_name}]
    }
    res = post_saved_object("lens", payload)
    print(f"[SUCCESS] Bar chart created: {title} ({res['id']})")
    return res["id"]

def create_timeline_chart(title):
    layer_id = str(uuid.uuid4())
    col_date = str(uuid.uuid4())
    col_split = str(uuid.uuid4())
    col_count = str(uuid.uuid4())
    ref_name = f"indexpattern-datasource-layer-{layer_id}"
    payload = {
        "attributes": {
            "title": title,
            "visualizationType": "lnsXY",
            "state": {
                "visualization": {
                    "legend": {"isVisible": True, "position": "top"},
                    "preferredSeriesType": "bar_stacked",
                    "layers": [{
                        "layerId": layer_id,
                        "accessors": [col_count],
                        "position": "top",
                        "seriesType": "bar_stacked",
                        "showGridlines": False,
                        "layerType": "data",
                        "xAccessor": col_date,
                        "splitAccessor": col_split
                    }]
                },
                "query": {"query": "", "language": "kuery"},
                "filters": [],
                "datasourceStates": {
                    "formBased": {
                        "layers": {
                            layer_id: {
                                "columns": {
                                    col_date: {
                                        "label": "시간대",
                                        "dataType": "date",
                                        "operationType": "date_histogram",
                                        "scale": "interval",
                                        "sourceField": "@timestamp",
                                        "isBucketed": True,
                                        "params": {"interval": "auto"}
                                    },
                                    col_split: {
                                        "label": "WAF 조치 (BLOCK / ALLOW)",
                                        "dataType": "string",
                                        "operationType": "terms",
                                        "scale": "ordinal",
                                        "sourceField": "action.keyword",
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
                                        "label": "트래픽 요청 수",
                                        "dataType": "number",
                                        "operationType": "count",
                                        "isBucketed": False,
                                        "scale": "ratio",
                                        "sourceField": "___records___",
                                        "params": {"emptyAsNull": True}
                                    }
                                },
                                "columnOrder": [col_date, col_split, col_count],
                                "incompleteColumns": {},
                                "sampling": 1
                            }
                        }
                    },
                    "indexpattern": {"layers": {}},
                    "textBased": {"layers": {}}
                },
                "internalReferences": [],
                "adHocDataViews": {}
            }
        },
        "references": [{"type": "index-pattern", "id": DATA_VIEW_ID, "name": ref_name}]
    }
    res = post_saved_object("lens", payload)
    print(f"[SUCCESS] Timeline chart created: {title} ({res['id']})")
    return res["id"]

def setup_full_dashboard():
    # 1. Create all new Lens objects
    id_m_total = create_metric("전체 인입 트래픽 (Total Requests)", "", "총 요청 수")
    id_m_block = create_metric("차단된 위협 공격 (Blocked Threats)", "action.keyword: \"BLOCK\"", "차단 건수")
    id_m_allow = create_metric("정상 비즈니스 허용 (Allowed Traffic)", "action.keyword: \"ALLOW\"", "허용 건수")
    
    id_timeline = create_timeline_chart("실시간 공격 발생 및 차단 추이 (Time Series)")
    id_donut = "c9342dc3-fb81-4cda-a6c9-962d5626b073" # Existing Pie Chart
    
    id_rules = create_bar_chart("WAF 탐지 룰셋별 피격 순위 (Top Rules)", "terminatingRuleId.keyword", "WAF 룰셋", top_n=6, is_horizontal=True)
    id_ips = create_bar_chart("최다 공격자 IP Top 5 (Top Attacker IPs)", "clientIp.keyword", "공격자 IP", top_n=5, is_horizontal=False)
    id_tools = create_bar_chart("악성 공격 도구 및 스캐너 (User-Agent)", "userAgent.keyword", "User-Agent", top_n=5, is_horizontal=True)

    # 2. Get existing dashboard to preserve map & URI panels
    req = urllib.request.Request(
        f"{KIBANA_URL}/api/saved_objects/dashboard/{DASHBOARD_ID}",
        headers={"kbn-xsrf": "true"}
    )
    with urllib.request.urlopen(req) as res:
        dash_obj = json.loads(res.read())

    existing_panels = json.loads(dash_obj["attributes"]["panelsJSON"])
    map_panel = next((p for p in existing_panels if p.get("title") == "공격자 국가별 분포"), None)
    uri_panel = next((p for p in existing_panels if p.get("title") == "공격당한 URI 경로 순위"), None)

    # 3. Assemble Full SOC Grid (Width: 48)
    panels = []
    references = []

    # Helper to add lens reference panel
    def add_lens_panel(lens_id, x, y, w, h, title=""):
        p_idx = str(uuid.uuid4())
        ref_name = f"panel_{p_idx}"
        panels.append({
            "type": "lens",
            "gridData": {"x": x, "y": y, "w": w, "h": h, "i": p_idx},
            "panelIndex": p_idx,
            "embeddableConfig": {"enhancements": {}},
            "panelRefName": ref_name,
            "title": title
        })
        references.append({
            "name": f"{p_idx}:{ref_name}",
            "type": "lens",
            "id": lens_id
        })

    # Row 1 (y: 0, h: 4) - 3 Metric Cards
    add_lens_panel(id_m_total, x=0, y=0, w=16, h=4, title="전체 인입 트래픽")
    add_lens_panel(id_m_block, x=16, y=0, w=16, h=4, title="차단된 위협 공격")
    add_lens_panel(id_m_allow, x=32, y=0, w=16, h=4, title="정상 허용 트래픽")

    # Row 2 (y: 4, h: 12) - Timeline & Donut
    add_lens_panel(id_timeline, x=0, y=4, w=30, h=12, title="실시간 위협 발생 및 차단 추이")
    add_lens_panel(id_donut, x=30, y=4, w=18, h=12, title="WAF 차단 및 룰셋 비율")

    # Row 3 (y: 16, h: 14) - World Map & Top Triggered Rules
    if map_panel:
        map_panel["gridData"] = {"x": 0, "y": 16, "w": 24, "h": 14, "i": map_panel["panelIndex"]}
        panels.append(map_panel)
        # Add map references from original
        for r in dash_obj["references"]:
            if "71e6bce6" in r.get("name", ""):
                references.append(r)

    add_lens_panel(id_rules, x=24, y=16, w=24, h=14, title="WAF 탐지 룰셋별 피격 순위")

    # Row 4 (y: 30, h: 12) - Top URIs, Top Attacker IPs, Top Tools
    if uri_panel:
        uri_panel["gridData"] = {"x": 0, "y": 30, "w": 16, "h": 12, "i": uri_panel["panelIndex"]}
        panels.append(uri_panel)
        for r in dash_obj["references"]:
            if "d56226c5" in r.get("name", ""):
                references.append(r)

    add_lens_panel(id_ips, x=16, y=30, w=16, h=12, title="최다 공격자 IP Top 5")
    add_lens_panel(id_tools, x=32, y=30, w=16, h=12, title="악성 공격 도구 / 스캐너 (User-Agent)")

    # 4. Save Dashboard
    dash_payload = {
        "attributes": {
            "title": "AWS WAF Enterprise SOC Threat Intelligence Dashboard",
            "description": "Enterprise-grade SOC dashboard tracking WAF blocks, real-time attack spikes, top threat rules, malicious tools, and attacker geo distributions.",
            "panelsJSON": json.dumps(panels),
            "optionsJSON": json.dumps({"useMargins": True, "syncColors": False, "syncCursor": True, "syncTooltips": True, "hidePanelTitles": False}),
            "timeRestore": False,
            "kibanaSavedObjectMeta": {
                "searchSourceJSON": json.dumps({"query": {"query": "", "language": "kuery"}, "filter": []})
            }
        },
        "references": references
    }

    req_update = urllib.request.Request(
        f"{KIBANA_URL}/api/saved_objects/dashboard/{DASHBOARD_ID}",
        data=json.dumps(dash_payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "kbn-xsrf": "true"},
        method="PUT"
    )
    with urllib.request.urlopen(req_update) as res:
        print("[SUCCESS] Successfully upgraded Kibana Dashboard to Full Enterprise SOC Dashboard!")

if __name__ == "__main__":
    setup_full_dashboard()
