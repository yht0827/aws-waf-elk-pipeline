# AWS WAF & ELK Real-Time Web Security Monitoring Pipeline

> **Terraform** 기반 Multi-AZ 인프라 자동 구축, **AWS WAF v2 5단계 차단 정책**, 그리고 **ELK 스택 실시간 위협 관제 대시보드**를 결합한 엔드투엔드 클라우드 웹 보안 파이프라인

[![Terraform](https://img.shields.io/badge/Terraform-1.5+-623CE4?logo=terraform&logoColor=white)](https://www.terraform.io/)
[![AWS WAF](https://img.shields.io/badge/AWS-WAF%20v2-FF9900?logo=amazon-aws&logoColor=white)](https://aws.amazon.com/waf/)
[![Elasticsearch](https://img.shields.io/badge/Elasticsearch-8.12.0-005571?logo=elasticsearch&logoColor=white)](https://www.elastic.co/)
[![Kibana](https://img.shields.io/badge/Kibana-8.12.0-005571?logo=kibana&logoColor=white)](https://www.elastic.co/kibana)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](https://www.python.org/)

---

## 📌 Architecture Overview

인터넷 트래픽이 Multi-AZ ALB로 인입되기 전 AWS WAF v2에서 5단계 규칙으로 패킷을 검사하여 악성 요청을 사전 차단합니다. 차단 및 허용 로그는 CloudWatch Logs를 거쳐 Python 수집기를 통해 Elasticsearch에 실시간 인덱싱되며, Kibana SOC 관제 화면에서 공격 현황을 시각화합니다. 백엔드 웹 서버는 보안 그룹(Security Group)을 통해 ALB 경유 트래픽만 허용하여 외부 직접 접근을 원천 차단합니다.

![System Architecture](docs/screenshots/00_system_architecture.png)

---

## 🛡️ Key Features

### 1. Terraform 기반 Multi-AZ 고가용성 인프라
- 2개 가용 영역(`ap-northeast-2a`, `ap-northeast-2c`)에 걸쳐 Public/Private 서브넷과 Multi-AZ ALB, EC2 Nginx 웹 서버를 코드로 배포
- 보안 그룹 체인 설계를 통해 백엔드 인스턴스로의 80/443 직접 접근을 차단하고 ALB를 경유한 인입만 허용

### 2. 5단계 WAF 차단 계층 (Rule Hierarchy)
보안성과 성능 최적화를 고려하여 검사 비용과 처리 우선순위에 따라 규칙을 단계별로 배치했습니다.
1. **Priority 0 (SQLi Block)**: `admin' OR '1'='1--` 등 인증 우회 및 쿼리 변조 패턴 즉각 차단
2. **Priority 1 (XSS Block)**: `<script>`, `onerror=` 등 웹 스크립트 삽입 패턴 즉각 차단
3. **Priority 2 (AWS Core Managed Rule Set)**: OS 파일 침투(Path Traversal), LFI/RFI 등 알려진 웹 취약점 방어
4. **Priority 3 (Scanner & Bot Block)**: `sqlmap`, `nikto`, `curl`, `python-requests` 등 악성 스캐너 및 무단 크롤링 도구 탐지
5. **Priority 4 (Rate Limiting)**: 동일 IP에서 5분간 100회 초과 요청 시 자동 차단하여 L7 DDoS 및 무차별 대입(Brute-force) 완화

### 3. 서버 정보 노출 방지 (Security Hardening 403 Response)
- WAF 차단 시 웹 서버 버전이나 AWS 내부 구성 정보가 노출되지 않도록 커스텀 에러 응답을 구성
- 불필요한 기술 지문을 일체 은폐하고 불투명한 고유 이벤트 식별자(`sec-waf-block`)만 반환하도록 구현

### 4. 실시간 로그 파이프라인 & Kibana SOC 대시보드
- CloudWatch Logs(`aws-waf-logs-sec-pipeline`)에 누적되는 WAF 차단 로그를 파이썬 인제스터로 실시간 파싱 및 지오코딩(GeoIP) 매핑
- Elasticsearch 8.12에 적재 후 Kibana SOC 대시보드로 시각화 (수집 공격 데이터 466건 실증):
  - **글로벌 공격 국가 지도 (GeoIP Coordinates)**
  - **주요 표적 URL Top 5 바 차트**
  - **공격자 IP Top 5 파이 차트**
  - **실시간 차단 로그 스트림 테이블**

![Kibana SOC Dashboard](docs/screenshots/13_kibana_soc_dashboard_clean.png)

---

## 🧪 Verification Test Scenarios

| 점검 항목 | 공격 유형 및 페이로드 | 대응 룰셋 | 결과 |
| :--- | :--- | :--- | :---: |
| **정상 서비스 접속** (`TC-01`) | `GET /?page=home` (정상 브라우저 User-Agent) | Default Action | **200 OK (허용)** |
| **SQL Injection 공격** (`TC-02`) | `/login?user=admin' OR '1'='1--` (인증 우회·데이터 탈취) | Custom Inline SQLi Rule | **403 Forbidden (차단)** |
| **Reflected XSS 공격** (`TC-03`) | `/search?q=<script>alert(1)</script>` | Custom Inline XSS Rule | **403 Forbidden (차단)** |
| **시스템 파일 침투** (`TC-04`) | `/view?file=../../../../etc/passwd` (Path Traversal) | AWS Core Managed Rule | **403 Forbidden (차단)** |
| **자동화 스캐너 및 크롤링 탐지** (`TC-05`) | `User-Agent: sqlmap`, `Nikto`, `python-requests` (무단 스크래핑) | Custom Scanner & Bot Rule | **403 Forbidden (차단)** |
| **L7 DDoS 및 무차별 대입 방어** (`TC-06`) | 동일 IP에서 5분간 100회 초과 고빈도 요청 인입 | Custom Rate Limit Rule | **403 Forbidden (차단)** |

---

## 📂 Project Structure

```text
aws-waf-elk-pipeline/
├── terraform/                   # Terraform 인프라 코드
│   ├── alb.tf                   # Application Load Balancer 및 리스너/타겟그룹
│   ├── ec2.tf                   # Multi-AZ Nginx 백엔드 인스턴스
│   ├── security.tf              # 보안 그룹 체인 설정
│   ├── vpc.tf                   # Multi-AZ VPC 및 서브넷/인터넷게이트웨이
│   ├── waf.tf                   # AWS WAF v2 웹 ACL 및 5단계 차단 룰셋
│   ├── outputs.tf               # ALB DNS 등 출력 변수
│   └── templates/
│       ├── user_data.sh.tpl     # Nginx 초기 구성 템플릿
│       └── waf_403.html         # 커스텀 403 차단 응답 화면
├── scripts/                     # 자동화 및 파이프라인 스크립트
│   ├── attack_simulator.sh      # 6종 공격 시나리오 자동 시뮬레이션
│   ├── sync_cloudwatch_waf_to_es.py  # CloudWatch -> Elasticsearch 로그 수집기
│   ├── setup_soc_dashboard.py   # Kibana 대시보드 자동 프로비저닝
│   └── optimize_soc_dashboard.py # 대시보드 메트릭 최적화
├── data/                        # 테스트용 WAF 차단 로그 데이터셋
├── docker-compose.yml           # 로컬 Elasticsearch & Kibana 구동 환경
├── docs/                        # 프로젝트 문서 및 증적 캡처
│   └── screenshots/             # 콘솔, WAF 메트릭, Kibana 대시보드 캡처
└── .gitignore                   # 민감 정보 및 Terraform 상태 파일 차단
```

---

## 🚀 Quick Start

### 1. 인프라 배포 (Terraform)
```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars # 환경 변수 설정
terraform init
terraform apply
```

### 2. 관제 스택 실행 (Docker Compose)
```bash
docker-compose up -d
# Elasticsearch: http://localhost:9200
# Kibana: http://localhost:5601
```

### 3. 공격 시뮬레이션 및 로그 수집
```bash
# 공격 시뮬레이션 실행 (ALB DNS로 6종 시나리오 트래픽 인입)
./scripts/attack_simulator.sh <ALB_DNS_NAME>

# CloudWatch WAF 로그를 Elasticsearch로 동기화
python3 scripts/sync_cloudwatch_waf_to_es.py
```

### 4. 리소스 정리 (Teardown)
```bash
cd terraform
terraform destroy
docker-compose down -v
```
