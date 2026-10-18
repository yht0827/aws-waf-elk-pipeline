# AWS WAF와 ELK를 활용한 실시간 웹 보안 관제 시스템

Terraform 코드로 AWS에 고가용성 웹 서버와 방화벽(WAF)을 구축하고, 차단된 공격 로그를 실시간으로 모니터링할 수 있는 대시보드(ELK)를 구현한 프로젝트입니다.

---

## Architecture

웹 방화벽(AWS WAF v2)이 5단계 규칙으로 악성 요청을 사전 차단하고, 차단 로그는 CloudWatch와 파이썬 수집기를 통해 Elasticsearch에 실시간 적재되어 Kibana 대시보드에 시각화됩니다. 백엔드 웹 서버는 보안 그룹(Security Group)으로 외부 직접 접근을 막고 로드밸런서(ALB) 경유 트래픽만 허용합니다.

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
- 2개 가용영역(`2a`, `2c`)에 VPC, 로드밸런서(ALB), 웹 서버를 코드로 배포해 무중단 고가용성 구조를 구축했습니다.
- 보안 그룹으로 웹 서버의 외부 직접 접근을 차단하고 ALB 경유 트래픽만 수신하도록 격리했습니다.

### 2. 5단계 웹 방화벽(WAF) 차단 규칙
검사 지연을 줄이고 보안성을 높이기 위해 처리 우선순위에 따라 5단계로 규칙을 배치했습니다.
1. **자체 SQLi·XSS 차단 (`priority = 5`)**: URL 디코딩 및 소문자 정규화를 거쳐 파라미터 변조와 스크립트 삽입 즉시 차단
2. **AWS 공통 보안 규칙 (`priority = 10`)**: 시스템 파일 침투(Path Traversal) 등 알려진 웹 취약점 패턴 방어
3. **AWS SQLi 전용 규칙 (`priority = 20`)**: 심층 DB 인젝션 시그니처 2차 방어
4. **해킹 도구 차단 (`priority = 30`)**: `sqlmap`, `nikto` 등 자동화 취약점 스캐너 도구 차단
5. **요청 횟수 제한 (`priority = 40`)**: 동일 IP에서 5분간 100회 초과 요청 시 차단해 L7 DDoS 및 무차별 대입 완화

### 3. 서버 정보 노출 방지 (커스텀 403 화면)
- 차단 시 웹 서버 종류와 버전(Nginx)이 드러나지 않도록 커스텀 403 에러 페이지를 적용했습니다.
- 내부 시스템 정보를 숨기고 고유 차단 코드(`sec-waf-block`)만 반환해 공격자의 사전 정찰(Fingerprinting)을 차단했습니다.

### 4. 실시간 위협 모니터링 대시보드 (ELK)
- WAF 차단 로그를 파이썬 수집기로 가공해 Elasticsearch에 실시간으로 적재했습니다.
- 수집된 466건의 공격 데이터를 기반으로 Kibana 대시보드에 **공격 국가 지도(GeoIP), 주요 표적 주소, 공격자 IP Top 5, 실시간 로그 목록**을 시각화했습니다.

![Kibana SOC Dashboard](docs/screenshots/13_kibana_soc_dashboard_clean.png)

---

## 대표 검증 시나리오

공격 시뮬레이션을 통해 6가지 시나리오를 직접 테스트하고 방어 동작을 검증했습니다.

| 점검 항목 | 공격 유형 및 페이로드 | 대응 룰셋 | 판정 |
| :--- | :--- | :--- | :---: |
| **정상 서비스 접속 및 오탐 검증** (`TC-01`) | `GET /search?q=C%2B%2B&lang=ko` (정상 파라미터 및 특수문자 인입 시 오탐 여부) | Default Action | **200 OK (정상 허용)** |
| **SQL Injection (우회 시도)** (`TC-02`) | `' UNION SELECT NULL, version()--`, URL 인코딩(`%27`) 변조 | Custom Inline SQLi (URL Decode 정규화) | **403 Forbidden (차단)** |
| **Reflected XSS (난독화 대응)** (`TC-03`) | `<img src=x onerror=alert(1)>`, 대소문자 혼합(`sCrIpt`) 삽입 | Custom Inline XSS (Lowercase 변환) | **403 Forbidden (차단)** |
| **시스템 파일 침투 (LFI/Path Traversal)** (`TC-04`) | `../../../../etc/passwd`, 널 바이트(`%00`) 삽입 우회 | AWS Core Managed Rule (CRS) | **403 Forbidden (차단)** |
| **자동화 스캐너 및 무단 크롤링** (`TC-05`) | `User-Agent: sqlmap`, `Nikto`, `python-requests` 헤더 변조 | Custom Scanner & Bot Rule | **403 Forbidden (차단)** |
| **L7 DDoS 및 무차별 대입 방어** (`TC-06`) | 동일 IP에서 5분간 100회 초과 고빈도 요청 (임계치 초과) | Custom Rate Limit Rule | **403 Forbidden (차단)** |

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
