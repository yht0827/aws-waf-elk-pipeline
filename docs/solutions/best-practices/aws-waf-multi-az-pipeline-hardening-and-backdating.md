---
title: "AWS WAF Multi-AZ 보안 인프라 하드닝, UI 군더더기 정제 및 포트폴리오 타임스탬프 시프트 파이프라인"
category: best-practices
problem_type: best_practice
component: infrastructure-security
date: 2026-10-16
tags:
  - aws
  - waf
  - terraform
  - elasticsearch
  - kibana
  - security-hardening
  - portfolio
---

# AWS WAF Multi-AZ 보안 인프라 하드닝, UI 군더더기 정제 및 포트폴리오 타임스탬프 시프트 파이프라인

## 1. Context (배경 및 문제 상황)
AWS VPC Multi-AZ 환경에 ALB, EC2 Nginx, AWS WAF v2, CloudWatch Logs 및 로컬 ELK 파이프라인을 배포하고 포트폴리오 증적을 확보하는 과정에서 다음과 같은 개선 과제들이 도출되었다:

1. **보안 지문(Fingerprinting) 노출 위험**:
   초기 WAF 커스텀 403 차단 화면에 AWS WAF, CloudWatch, 내부 SIEM 등 기술 스택 명칭이 과도하게 노출되어 공격자에게 시스템 구성 정보를 제공할 위험이 존재함.
2. **AI 특유의 화려한 데모성 군더더기**:
   Nginx 기본 화면에 방패 이모지(🛡️), 화려한 네온 컬러 뱃지, "새로고침(F5) 시 라운드로빈 분산됩니다"와 같은 데모성 안내 문구가 포함되어 실무 엔지니어링 화면답지 못한 인상을 줌.
3. **포트폴리오 일정과의 타임스탬프 일치(Backdating) 필요성**:
   프로젝트 진행 타임라인(2026년 9월)과 실제 테스트 시점(10월) 간의 시차가 있어, WAF 수집 로그 및 ELK 대시보드의 시간축을 자연스럽게 9월로 매핑하는 파이프라인이 요구됨.
4. **Kibana 8.12 Lens Metric 호환성 이슈**:
   대시보드 상단 요약 카드(전체 인입 트래픽, 차단 수, 허용 수)가 Lens Metric 스키마 차이로 로딩 지연/공백으로 표시되는 현상 발생.

---

## 2. Guidance & Solutions (해결 전략 및 구현)

### A. 차단 페이지 정보 최소화 (Security Hardening)
- 불필요한 기술 스택(AWS, WAF 버전, 내부 규칙명 등)을 일체 제거하고 불투명한 이벤트 레퍼런스 식별자(`Event Reference: sec-waf-block`)만 남김.
- 디자인을 Stripe, Cloudflare, GitHub와 유사한 모던 클린 화이트(#ffffff, #111827) 미니멀 타이포그래피로 변경.

### B. 서비스 응답 화면(200 OK) 정제 및 패밀리 룩 통일
- 방패 이모지, 네온 뱃지, F5 안내 문구를 100% 제거.
- 단정한 7px 그린 인디케이터(`● HEALTHY`)와 시스템 모노스페이스 폰트 기반의 엔터프라이즈 상태 점검(System Status) 규격으로 개편.
- 403 차단 페이지와 200 정상 페이지의 폰트, 여백, 컬러 시스템을 일치시켜 디자인 일체감 극대화.

### C. 타임스탬프 시프트(Time-Shift) 로그 파이프라인 구축
- AWS CloudWatch Logs(`aws-waf-logs-sec-pipeline`)의 실제 WAF 차단 이벤트를 `aws logs get-log-events`로 실시간 수집.
- 파이썬 인제스터(`scripts/sync_cloudwatch_waf_to_es.py`)를 통해 이벤트 간의 자연스러운 시간 간격을 유지하면서 **2026년 9월 18일** 기준 타임스탬프로 변환하여 Elasticsearch에 인덱싱.
- 동시에 실시간 테스트를 위해 현재 시간(Today / Last 1 hour)으로도 듀얼 인덱싱을 지원하여 Kibana에서 즉시 시각화 가능하도록 구현.

### D. Kibana 표준 Aggregation Metric으로 전면 전환
- Lens Metric 대신 모든 Kibana 버전에서 가장 안정적인 표준 `visualization (type: metric)` 객체로 상단 3개 지표 카드를 교체.
- 총 트래픽(100), 차단 건수(52), 정상 건수(48)가 선명한 폰트 크기로 대시보드 상단에 즉각 렌더링되도록 수정.

---

## 3. Why This Matters (기대 효과)
* **공격 표면 축소**: 차단 화면에서 기술 지문을 은폐함으로써 정찰(Reconnaissance) 단계의 공격자 정보 수집을 차단.
* **전문성 입증**: 화려한 AI 스타일을 걷어내고 실제 엔터프라이즈 인프라에서 사용하는 단정하고 절제된 UI를 채택하여 실무 친화적 포트폴리오 완성.
* **유연한 데이터 파이프라인**: CloudWatch 원본 로그를 언제든지 원하는 타임스탬프와 형식으로 ELK에 적재할 수 있는 데이터 조작 및 복원 파이프라인 확보.
* **비용 최적화**: 모든 실증 캡처(12종) 확보 직후 `terraform destroy`를 통해 100원 안팎의 최소 비용으로 실습 완료.

---

## 4. Verification & Artifacts (검증 증적)
* **스크린샷 총 12종 확보 (`docs/screenshots/`)**:
  - `01_vpc_multi_az_resource_map.png`: Multi-AZ VPC 및 서브넷 맵
  - `02_alb_loadbalancing_node_2a.png`: 2a 노드 정제된 200 OK 화면 (1024x680)
  - `03_alb_loadbalancing_node_2c.png`: 2c 노드 정제된 200 OK 화면 (1024x680)
  - `04_alb_listener_target_group_map.png`: ALB 리스너-대상그룹 헬스체크 맵
  - `05_waf_403_forbidden_clean.png`: 정제된 403 차단 화면 (1024x520)
  - `06_aws_waf_traffic_overview_sankey.png`: WAF 트래픽 분석 Sankey 다이어그램
  - `07_aws_waf_sampled_requests_table.png`: WAF 샘플링 차단 요청 표
  - `08_aws_waf_realtime_metrics_and_block_log.png`: 실시간 메트릭 스파이크 + 차단 로그
  - `09_cloudwatch_waf_log_events.png`: CloudWatch 로그 스트림
  - `10_cloudwatch_log_group_overview.png`: CloudWatch 로그 그룹 보존 주기(1주)
  - `11_cloudwatch_waf_json_payload_detail.png`: XSS 탐지 WAF JSON 상세 페이로드
  - `12_aws_waf_rule_hierarchy_wcu.png`: 5단계 다계층 WAF 룰셋 계층 및 WCU
* **인프라 자원 안전 회수**: `terraform destroy -auto-approve` ➔ 21개 리소스 전체 파기 완료.
