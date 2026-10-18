# AWS WAF & ELK Real-Time Web Security Pipeline

Terraform 코드로 AWS에 고가용성 웹 서버와 방화벽(WAF)을 구축하고, 차단된 공격 로그를 실시간으로 모니터링할 수 있는 대시보드(ELK)를 구현한 프로젝트입니다.

---

## Architecture

사용자 요청이 웹 서버에 닿기 전에 웹 방화벽(AWS WAF v2)이 5단계로 패킷을 먼저 검사해 해킹 시도를 차단합니다. 차단된 로그는 CloudWatch를 거쳐 파이썬 프로그램이 실시간으로 Elasticsearch에 전달하고, 관리자는 Kibana 대시보드에서 공격 현황을 지도와 차트로 바로 확인할 수 있습니다. 백엔드 웹 서버는 인터넷에 직접 노출되지 않도록 가두고, 로드밸런서(ALB)를 통해서만 안전하게 접근할 수 있도록 보안 그룹을 설정했습니다.

![System Architecture](docs/screenshots/00_system_architecture.png)

---

## Infrastructure Specifications

실제 코드로 구축된 AWS 인프라 리소스와 네트워크 구성 스펙입니다.

| 구분 | AWS 서비스 | 사양 및 설정 | 설명 |
| :--- | :--- | :--- | :--- |
| **Region** | AWS Global | `ap-northeast-2` (서울) | 2개 가용영역(`2a`, `2c`) 분산 배치 |
| **Network** | Amazon VPC | CIDR `10.0.0.0/16` | Public 서브넷 2개, Private 서브넷 2개 분리 |
| **Load Balancer** | Application Load Balancer | Internet-facing ALB (Dual-AZ) | HTTP 80번 포트로 들어오는 트래픽 분산 |
| **Web Server** | Amazon EC2 | `t3.micro` (Amazon Linux 2023, Nginx) x 2 | Private 서브넷에 안전하게 격리 배치 |
| **Security Group** | Security Groups | ALB: 모든 사용자(80 포트) 허용<br>EC2: ALB를 통과한 트래픽만 허용 | 외부에서 웹 서버로 직접 접속하는 경로 차단 |
| **Web Firewall** | AWS WAF v2 | Regional Web ACL (5단계 차단 규칙) | ALB에 연결되어 5단계 검사 및 403 차단 수행 |
| **Log Storage** | CloudWatch Logs | Log Group (보관 주기 7일) | WAF에서 탐지·차단한 전체 접속 로그 수집 |

---

## Key Implementations

### 1. 웹 인프라 자동 구축 (Terraform)
- 2개 가용영역(`2a`, `2c`)에 웹 서버와 로드밸런서(ALB)를 코드로 한 번에 구축해, 서버 한 대가 다운되어도 서비스가 멈추지 않는 구조를 만들었습니다.
- 보안 그룹(Security Group)을 연결해 외부 인터넷에서 웹 서버로 직접 접속하지 못하도록 막고, 로드밸런서를 거친 정상 요청만 받도록 안전하게 격리했습니다.

### 2. 5단계 웹 방화벽(WAF) 차단 규칙
검사 속도가 느려지지 않도록 중요도와 처리 순서에 맞춰 5단계 규칙을 차례대로 배치했습니다.
1. **자체 SQLi·XSS 차단 (`priority = 5`)**: 주소창이나 입력창에 악성 코드나 스크립트를 넣는 공격을 가장 먼저 감지해 차단합니다. (URL 디코딩 및 소문자 변환 검사)
2. **AWS 공통 보안 규칙 (`priority = 10`)**: 리눅스 시스템 파일 접근이나 널리 알려진 웹 해킹 패턴을 자동으로 막아줍니다.
3. **AWS SQL Injection 전용 규칙 (`priority = 20`)**: 1단계를 우회하려는 정교한 DB 조작 공격을 한 번 더 걸러냅니다.
4. **해킹 도구 차단 (`priority = 30`)**: `sqlmap`, `nikto` 같은 자동화된 취약점 공격 도구의 접속을 감지해 차단합니다.
5. **요청 횟수 제한 (`priority = 40`)**: 한 IP에서 5분 동안 100번 넘게 비정상적으로 빠르게 요청하면 자동으로 차단해 대량 공격(DDoS)을 완화합니다.

### 3. 서버 정보 노출 방지 (커스텀 403 화면)
- 해킹이 차단되었을 때 뜨는 에러 화면에서 웹 서버 종류나 버전(Nginx 등)이 드러나지 않도록 별도 차단 페이지를 적용했습니다.
- 내부 시스템 정보를 숨기고 고유 차단 코드(`sec-waf-block`)만 보여주어, 공격자가 시스템 정보를 파악하는 것을 원천 차단했습니다.

### 4. 실시간 위협 모니터링 대시보드 (ELK)
- WAF가 차단한 로그를 파이썬 프로그램(`scripts/sync_cloudwatch_waf_to_es.py`)으로 가공해 검색 엔진(Elasticsearch)에 실시간으로 저장합니다.
- 수집된 466건의 공격 데이터를 바탕으로 Kibana 대시보드에서 **공격자 국가 지도**, **가장 많이 공격받은 주소**, **공격자 IP Top 5**, **실시간 차단 로그 목록**을 직관적으로 볼 수 있게 구성했습니다.

![Kibana SOC Dashboard](docs/screenshots/13_kibana_soc_dashboard_clean.png)

---

## Verification Scenarios

공격 스크립트를 이용해 6가지 시나리오를 직접 테스트하고 방어 동작을 검증했습니다.

| 점검 항목 | 테스트 공격 내용 | 동작한 차단 규칙 | 결과 |
| :--- | :--- | :--- | :---: |
| **정상 접속 및 오탐 검증** (`TC-01`) | `GET /search?q=C%2B%2B&lang=ko` (정상 검색 요청) | 기본 규칙 (Default) | **200 OK (정상 허용)** |
| **SQL Injection 공격** (`TC-02`) | `' UNION SELECT NULL, version()--` (DB 데이터 탈취 시도) | 1단계 자체 SQLi 규칙 | **403 Forbidden (차단)** |
| **XSS 스크립트 공격** (`TC-03`) | `<img src=x onerror=alert(1)>` (악성 스크립트 실행 시도) | 1단계 자체 XSS 규칙 | **403 Forbidden (차단)** |
| **시스템 파일 접근** (`TC-04`) | `../../../../etc/passwd` (서버 내부 설정 파일 조회 시도) | 2단계 AWS 공통 규칙 | **403 Forbidden (차단)** |
| **자동화 해킹 도구** (`TC-05`) | `sqlmap`, `nikto` (해킹 스캐너 프로그램으로 접속) | 4단계 도구 차단 규칙 | **403 Forbidden (차단)** |
| **비정상 대량 요청** (`TC-06`) | 한 IP에서 5분간 100회 이상 빠른 속도로 접속 | 5단계 요청 제한 규칙 | **403 Forbidden (차단)** |

---

## Directory Structure

```text
aws-waf-elk-pipeline/
├── terraform/                   # Terraform 인프라 배포 코드
│   ├── alb.tf                   # 트래픽 분산 로드밸런서 설정
│   ├── ec2.tf                   # Nginx 웹 서버 인스턴스 설정
│   ├── security.tf              # 접근 제어 보안 그룹 설정
│   ├── vpc.tf                   # 네트워크 및 서브넷 설정
│   ├── waf.tf                   # 5단계 WAF 방화벽 규칙 설정
│   ├── outputs.tf               # 배포 후 생성된 주소 출력
│   └── templates/
│       ├── user_data.sh.tpl     # 서버 부팅 시 Nginx 자동 설치 스크립트
│       └── waf_403.html         # 커스텀 403 차단 화면 파일
├── scripts/                     # 자동화 및 로그 수집 스크립트
│   ├── attack_simulator.sh      # 6가지 공격 시나리오 자동 테스트 도구
│   ├── sync_cloudwatch_waf_to_es.py  # WAF 로그를 Elasticsearch로 실시간 전송
│   ├── setup_soc_dashboard.py   # Kibana 대시보드 자동 생성 도구
│   └── optimize_soc_dashboard.py # 대시보드 화면 최적화
├── data/                        # 테스트용 WAF 로그 데이터
├── docker-compose.yml           # Elasticsearch & Kibana 실행 설정
├── docs/                        # 시스템 아키텍처 및 대시보드 캡처
└── .gitignore                   # 중요 설정 파일 및 상태 파일 제외 설정
```

---

## Getting Started

### 1. 인프라 배포 (Terraform)
```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
terraform init
terraform apply
```

### 2. 관제 시스템 실행 (Docker Compose)
```bash
docker-compose up -d
# Elasticsearch: http://localhost:9200
# Kibana: http://localhost:5601
```

### 3. 공격 테스트 및 로그 수집
```bash
# 로드밸런서 주소로 6가지 공격 테스트 실행
./scripts/attack_simulator.sh <ALB_DNS_NAME>

# WAF 차단 로그를 Elasticsearch로 실시간 전송
python3 scripts/sync_cloudwatch_waf_to_es.py
```

### 4. 실습 종료 후 자원 삭제
```bash
cd terraform
terraform destroy
docker-compose down -v
```
