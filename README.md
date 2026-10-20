# AWS WAF와 ELK를 활용한 실시간 웹 보안 관제 시스템

Terraform 코드로 AWS에 고가용성 웹 서버와 방화벽(WAF)을 구축하고, 차단된 공격 로그를 실시간으로 모니터링할 수 있는 관제 대시보드(ELK)를 구축한 프로젝트입니다.

---

## Architecture

웹 방화벽(AWS WAF v2)이 5단계 규칙으로 악성 요청을 먼저 걸러내고, 차단된 로그는 파이썬 수집기를 통해 Elasticsearch에 실시간 저장되어 Kibana 대시보드에 시각화됩니다. 백엔드 웹 서버는 보안 그룹(Security Group)을 통해 외부 직접 접속을 막고 로드밸런서(ALB)를 통과한 정상 트래픽만 받도록 격리했습니다.

![System Architecture](docs/screenshots/00_system_architecture.png)

### WAF 5단계 차단 흐름 (AWS 공식 가이드라인 적용)

[AWS 공식 아키텍처 가이드(Defense-in-Depth using AWS WAF)](https://aws.amazon.com/blogs/security/defense-in-depth-using-aws-managed-rules-for-aws-waf-part-1/)에서 권장하는 **계층형 심층 방어(Layered Defense)** 모델을 적용했습니다. 방화벽 처리 비용(WCU)과 지연 시간을 줄이기 위해 가벼운 맞춤형 규칙을 가장 앞단에 배치해 **발견 즉시 조기 차단**하도록 구성했습니다.

> **차단 순서 흐름**:  
> `사용자 접속 요청` ➔ **1단계: 자체 맞춤 차단**(`우선순위 5`) ➔ **2단계: AWS 공통 보안 규칙**(`10`) ➔ **3단계: DB 전용 규칙**(`20`) ➔ **4단계: 해킹 도구 차단**(`30`) ➔ **5단계: 반복 접속 제한**(`40`) ➔ `안전한 요청만 웹 서버 전달 (200 OK)`

| 계층 (AWS 가이드라인) | 설계 원칙 | 프로젝트 적용 규칙 (우선순위) | 주요 차단 대상 및 동작 방식 |
| :--- | :--- | :--- | :--- |
| **1단계 (Layer 1)**<br>자체 맞춤 규칙 | 비용과 검사 지연을 줄이기 위해 가장 먼저 검사하고 즉시 차단 | `Custom-Inline-Web-Attack-Defense`<br>(`priority = 5`) | 주소 변환(URL 디코딩) 및 소문자 정리를 거쳐 교묘하게 숨긴 SQL 조작 및 악성 스크립트(XSS) 즉시 차단 |
| **2단계 (Layer 2)**<br>기본 보안 규칙 | 가장 흔한 웹 보안 취약점(OWASP Top 10) 1차 필터링 | `AWS-AWSManagedRulesCommonRuleSet`<br>(`priority = 10`) | 시스템 내부 파일 몰래 읽기(경로 탐색) 등 대표적인 웹 공격 패턴 방어 |
| **3단계 (Layer 3)**<br>서버 환경 맞춤 규칙 | 데이터베이스 등 실제 서버 환경에 맞춘 전문 규칙 추가 | `AWS-AWSManagedRulesSQLiRuleSet`<br>(`priority = 20`) | 데이터베이스를 노리는 정밀한 SQL 인젝션 공격 시그니처 2차 방어 |
| **4단계 (Layer 4)**<br>해킹 도구 차단 | 공격자가 사용하는 자동화 스캐너나 도구 차단 | `Custom-Block-Scanner-UserAgent`<br>(`priority = 30`) | `sqlmap`, `nikto` 등 해커들이 사용하는 자동 취약점 점검 도구 차단 |
| **5단계 (Layer 5)**<br>접속 횟수 제한 | 짧은 시간 동안 비정상적으로 많이 들어오는 접속 제어 | `Custom-RateLimit-DDoS-Protection`<br>(`priority = 40`) | 동일 IP 기준 5분 동안 100회 초과 접속 시 차단 (서비스 마비 디도스 및 반복 공격 방어) |
| **관제 (Monitoring)**<br>중앙 로그 수집 | 차단 로그를 중앙에 모아 실시간 관제 및 분석 | CloudWatch Logs + 파이썬 수집기 + ELK | 차단된 공격자 IP, 국가 위치 지도, 실시간 침해 로그를 한눈에 보는 보안 대시보드 구축 |

#### 규칙 우선순위(Priority) 및 WCU 설계 의도
- **앞단 조기 차단을 통한 연산 비용 절감**: [AWS 규칙 처리 순서 공식 가이드(Processing order of rules)](https://docs.aws.amazon.com/waf/latest/developerguide/web-acl-processing-order.html) 원칙에 따라, 약 80 WCU의 가벼운 자체 규칙(`priority = 5`)을 맨 앞에 배치하여 대다수 공격을 앞단에서 즉시 차단함으로써 뒤쪽 무거운 AWS 관리형 룰(700 WCU)의 불필요한 연산을 방지했습니다.
- **유연한 규칙 확장을 위한 번호 간격 (5, 10, 20...)**: `1, 2, 3` 연속 번호 대신 간격을 두어, 향후 긴급 IP 차단이나 신규 규칙을 기존 룰 사이(`priority = 7`, `15` 등)에 무중단으로 유연하게 추가할 수 있도록 설계했습니다.

```hcl
# terraform/waf.tf (규칙 우선순위 설정)
rule {
  name     = "Custom-Inline-Web-Attack-Defense"
  priority = 5  # 가벼운 맞춤 룰을 최우선 검사하여 조기 차단 (약 80 WCU)
  ...
}
rule {
  name     = "AWS-AWSManagedRulesCommonRuleSet"
  priority = 10 # 범용 취약점 필터링 (700 WCU)
  ...
}
```

---

## Key Implementations

1. **AWS 권장 5단계 계층형 방어**: 처리 비용과 속도를 최적화하기 위해 우선순위에 따라 순차 검사하고 악성 요청을 앞단에서 즉시 차단합니다.
2. **변조·난독화 공격 무력화 (주소 정규화)**: 영문 대소문자를 섞거나 특수문자 코드로 숨긴 공격 글자를 깨끗하게 복원(URL 디코딩/소문자 변환)하여 탐지 우회를 원천 차단했습니다.
3. **서버 정보 노출 차단 (커스텀 403 화면)**: 차단 시 웹 서버 종류(Nginx)와 버전 정보를 숨기고 고유 차단 코드(`sec-waf-block`)만 반환해 공격자의 사전 정보 수집을 방지했습니다.
4. **실시간 위협 관제 대시보드 및 분석 파이프라인 (ELK)**: 
   - **실제 AWS WAF 차단 데이터 검증**: 임의의 모의 데이터가 아닌, 6가지 공격 시뮬레이션을 통해 AWS WAF 및 CloudWatch에 실제 기록된 466건의 원본 텔레메트리 로그를 기반으로 관제 파이프라인을 구축했습니다.
   - **Kibana SOC 보안 관제 5대 패널 구축**:
     - **공격자 국가 지도 (GeoIP)**: 국내외 공격 트래픽의 유입 국가 및 글로벌 위협 분포 시각화
     - **규칙별 차단 통계**: 5단계 룰 중 어떤 규칙(Inline SQLi, CRS, Scanner 등)에 가장 많이 탐지되었는지 차단 비중 분석
     - **표적 주소 Top 5**: 공격자가 집중 정찰하는 취약 경로(`/login`, `/search`, `/view` 등) 식별
     - **최다 공격자 IP Top 5**: 고빈도 침해 시도를 유발하는 악성 IP 블랙리스트 도출
     - **실시간 침해 로그 상세 테이블**: 발생 시각, 공격 페이로드, 차단 룰, User-Agent, 응답 코드(403) 상세 추적
   - **하이브리드 비용 최적화(FinOps)**: 클라우드 비용이 높은 OpenSearch 대신 로컬 Docker ELK를 활용하고, 무거운 Logstash(자바 기반 1GB+) 대신 **경량 파이썬 수집기**를 자체 구현하여 클라우드 비용을 최소화하면서 실시간 관제 환경을 검증했습니다. *(대규모 엔터프라이즈 환경 시 CloudWatch Subscription Filter 및 AWS Lambda를 통한 서버리스 파이프라인으로 유연하게 확장 가능)*

![Kibana SOC Dashboard](docs/screenshots/13_kibana_soc_dashboard_clean.png)

---

## Infrastructure Specifications

콘솔 수동 설정으로 인한 설정 누락과 인적 실수(휴먼 에러)를 방지하고, 보안 아키텍처를 100% 일관되게 재현·형상 관리할 수 있도록 모든 인프라 리소스를 Terraform(IaC) 코드로 표준화하여 자동 배포했습니다.

| 구분 | AWS 서비스 | 설정 및 사양 | 역할 설명 |
| :--- | :--- | :--- | :--- |
| **서비스 지역** | AWS Global | `ap-northeast-2` (서울) | 2개 가용영역(`2a`, `2c`) 분산 배치 |
| **가상 네트워크** | Amazon VPC | CIDR `10.0.0.0/16` | 사설 표준 대역(IP 충돌 방지 및 6.5만 개 확장성 확보), 외부용·내부용 서브넷 분리 |
| **트래픽 분산** | Application Load Balancer | 인터넷 연결 ALB (Dual-AZ) | 2개 가용영역(`2a`, `2c`) 이중화로 무중단 고가용성(HA) 보장 및 사용자 트래픽 분산 |
| **웹 서버** | Amazon EC2 | `t3.micro` (Amazon Linux 2023, Nginx) x 2 | 최신 보안 OS 기반 웹 서버 2대 분산으로 단일 장애점(SPOF) 방지 및 내부 서브넷 격리 |
| **접근 제어** | Security Groups | ALB: 80번 포트 전체 허용<br>EC2: ALB를 거친 트래픽만 허용 | 외부에서 웹 서버로 직접 접속하는 경로 차단 |
| **웹 방화벽** | AWS WAF v2 | 지역 기반 Web ACL (5단계 차단) | ALB 앞단에 연결되어 5단계 검사 및 403 차단 수행 |
| **원격 관리** | AWS IAM | 인스턴스 프로파일 (`SSM Core`) | 22번 SSH 포트 개방 없이 안전한 원격 터미널 접속 지원 |
| **로그 저장소** | CloudWatch Logs | 로그 그룹 (보관 주기 7일) | ELK 실시간 전송 연동 및 불필요한 클라우드 저장 비용 절감을 위해 7일 보관 주기 적용 |

---

## 대표 검증 시나리오

공격 시뮬레이션 도구([`scripts/attack_simulator.sh`](file:///Users/ht/aws-waf-elk-pipeline/scripts/attack_simulator.sh))를 통해 6가지 시나리오를 직접 테스트하고 차단 동작을 검증했습니다. 악성 요청 차단 시 백엔드 웹 서버(Nginx) 종류와 버전 정보 노출을 완벽히 차단하고, 커스텀 403 화면 및 고유 차단 코드(`sec-waf-block`)가 반환됨을 확인했습니다.

| 점검 항목 | 공격 유형 및 페이로드 | 적용 규칙 | 검증 판정 |
| :--- | :--- | :--- | :---: |
| **정상 접속 (오탐 점검)** (`TC-01`) | `GET /search?q=C%2B%2B&lang=ko` (정상 특수문자 요청 허용 여부) | Default Action | **200 OK (정상 허용)** |
| **SQL 인젝션 공격** (`TC-02`) | `' UNION SELECT NULL, version()--`, URL 특수문자 변조 우회 | 1단계 자체 맞춤 차단 (URL 정규화) | **403 차단 (서버 정보 은닉)** |
| **크로스 사이트 스크립팅 (XSS)** (`TC-03`) | `<img src=x onerror=alert(1)>`, 대소문자 혼합(`sCrIpt`) 삽입 | 1단계 자체 맞춤 차단 (소문자 정규화) | **403 차단 (서버 정보 은닉)** |
| **경로 조작 공격 (Path Traversal)** (`TC-04`) | `../../../../etc/passwd` (상위 경로 이동 및 필터 우회 시도) | 2단계 AWS 공통 보안 규칙 (CRS) | **403 차단 (서버 정보 은닉)** |
| **자동 해킹 도구 탐지** (`TC-05`) | `sqlmap`, `nikto` 등 취약점 스캐너 헤더 포함 접속 | 4단계 해킹 도구 차단 규칙 | **403 차단 (서버 정보 은닉)** |
| **대량 접속 서비스 거부 (DDoS)** (`TC-06`) | 동일 IP에서 5분 동안 100회 초과 대량 접속 (임계치 초과) | 5단계 접속 횟수 제한 규칙 | **403 차단 (서버 정보 은닉)** |

---

## Directory Structure

```text
aws-waf-elk-pipeline/
├── terraform/                   # AWS 인프라(VPC, ALB, EC2, IAM) 코드
│   ├── waf.tf                   # 5단계 WAF 차단 규칙 설정
│   ├── alb.tf
│   ├── ec2.tf
│   ├── iam.tf
│   ├── security.tf
│   └── vpc.tf
├── scripts/                     # 관제 자동화 도구
│   ├── attack_simulator.sh      # 6가지 공격 시뮬레이션
│   ├── sync_cloudwatch_waf_to_es.py  # CloudWatch ➔ Elasticsearch 수집기
│   └── setup_soc_dashboard.py   # Kibana 대시보드 자동 생성
├── docker-compose.yml           # 관제 시스템(Elasticsearch & Kibana) 설정
└── docs/                        # 아키텍처 및 관제 대시보드 증적
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

### 3. 공격 테스트 및 실시간 관제 확인
```bash
# 로드밸런서 주소로 6가지 공격 테스트 실행
./scripts/attack_simulator.sh <ALB_DNS_NAME>

# CloudWatch WAF 차단 로그를 Elasticsearch로 동기화
python3 scripts/sync_cloudwatch_waf_to_es.py
```

