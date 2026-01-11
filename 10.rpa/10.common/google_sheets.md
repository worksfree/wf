## 전체 데이터 구조 분석
### 현재 상황 분석
- 사용자별 앱 크레딧: 각 사용자가 각 앱에 대해 독립적인 크레딧 보유
- 로컬 관리: .wf_rpa/[app_name]/.{app_name}_credits.json 파일로 관리
- 동기화 필요: 로컬 변경사항을 구글 시트에 주기적으로 동기화

### 관리해야 할 핵심 데이터
- 사용자 등록 정보 (기존 registrations 시트)
- 앱별 정책 정보 (새로운 app_policies 시트)
- 사용자별 크레딧 현황 (새로운 credit_sync 시트)
- 크레딧 구매 내역 (새로운 purchase_history 시트)
- 크레딧 사용 내역 (새로운 usage_history 시트)
- 관리자 설정 (기존 admin_config 시트)

## 구글 시트 구조 정의
### 1. registrations 시트 (기존 유지)
사용자 등록 정보를 관리하는 시트

| 컬럼명              | 타입           | 설명             | 예시                          |
|---------------------|----------------|------------------|-------------------------------|
| user_email          | String         | 사용자 이메일    | insung.lee1973@gmail.com      |
| user_name           | String         | 사용자 이름      | 이인성                        |
| user_phone          | String         | 사용자 전화번호  | 010-1234-5678                 |
| user_email_consent  | String         | 이메일 수신 동의 | Y/N                           |
| uc_hw_fingerprint   | String         | 하드웨어 지문    | abc123def456...               |
| uc_hw_cpuinfo       | String         | CPU 정보         | Intel Core i7...              |
| uc_hw_mbinfo        | String         | 메인보드 정보    | ASUSTeK...                    |
| uc_first_app        | String         | 최초 등록 앱     | bom2excel                     |
| ts_created_at       | Datetime       | 등록일시         | 2025-10-12 10:30:00           |
| ts_updated_at       | ISO DateTime   | 업데이트일시     | 2025-10-12T10:30:00.123Z      |

### 2. app_policies 시트 (신규)
앱별 정책 정보를 관리하는 시트

| 컬럼명             | 타입       | 설명                        | 예시                        |
|--------------------|------------|-----------------------------|-----------------------------|
| app_name           | String     | 앱 이름 (Primary Key)       | bom2excel                   |
| app_display_name   | String     | 앱 표시명                   | BOM2Excel Exporter          |
| icon_text          | String     | 아이콘 텍스트               | B2E                         |
| description        | String     | 간단 설명                   | 도면 처리 앱                |
| full_description   | String     | 상세 설명                   | BOM 엑셀 변환 - 파일당 100크레딧 |
| trial_credits      | Integer    | 체험판 크레딧               | 2000 (-1: 무료앱)           |
| credit_per_work    | Integer    | 작업당 크레딧               | 100                         |
| credit_type        | String     | 크레딧 타입                 | per_file, per_execution, free |
| available_work     | Integer    | 체험판으로 가능한 작업수     | 20                          |
| permanent_price    | Integer    | 영구 라이선스 가격 (원)      | 2000000                     |
| credit_unit_price  | Integer    | 크레딧 단가 (원/2000크레딧)  | 20000                       |
| is_active          | Boolean    | 활성 상태                   | TRUE/FALSE                  |
| created_at         | Datetime   | 생성일시                    | 2025-10-12 10:00:00         |
| updated_at         | Datetime   | 업데이트일시                 | 2025-10-12 10:00:00         |

### 3. credit_sync 시트 (신규 - 핵심)
사용자별 앱별 크레딧 현황을 실시간 동기화하는 시트

| 컬럼명                  | 타입         | 설명                        | 예시                                 |
|-------------------------|--------------|-----------------------------|--------------------------------------|
| sync_id                 | String       | 동기화 ID (Primary Key)     | user@example.com_bom2excel_hw123     |
| user_email              | String       | 사용자 이메일               | insung.lee1973@gmail.com             |
| app_name                | String       | 앱 이름                     | bom2excel                            |
| hardware_fingerprint    | String       | 하드웨어 지문               | abc123def456...                      |
| trial_credits           | Integer      | 체험판 크레딧 잔고          | 1800 (-1: 무료앱)                    |
| purchased_credits       | Integer      | 구매 크레딧 잔고            | 4000 (-1: 영구라이선스)              |
| total_credits_used      | Integer      | 총 사용한 크레딧            | 2200                                 |
| total_purchase_amount   | Integer      | 총 구매 금액 (원)           | 40000                                |
| last_usage_timestamp    | ISO DateTime | 마지막 사용 시간            | 2025-10-12T09:30:00.123Z             |
| last_purchase_timestamp | ISO DateTime | 마지막 구매 시간            | 2025-10-11T14:20:00.456Z             |
| created_at              | Datetime     | 최초 생성일시               | 2025-10-10 15:00:00                  |
| last_synced_at          | ISO DateTime | 마지막 동기화일시           | 2025-10-12T10:35:00.789Z             |
| sync_version            | Integer      | 동기화 버전                 | 15                                   |
| is_active               | Boolean      | 활성 상태                   | TRUE/FALSE                           |

### 4. purchase_history 시트 (신규)
크레딧 구매 내역을 관리하는 시트

| 컬럼명                   | 타입         | 설명                    | 예시                        |
|--------------------------|--------------|-------------------------|-----------------------------|
| purchase_id              | String       | 구매 ID (Primary Key)   | PUR_20251012_001            |
| user_email               | String       | 구매자 이메일           | insung.lee1973@gmail.com    |
| app_name                 | String       | 대상 앱                 | bom2excel                   |
| hardware_fingerprint     | String       | 하드웨어 지문           | abc123def456...             |
| purchase_type            | String       | 구매 타입               | CREDIT_2000, PERMANENT_LICENSE |
| credit_amount            | Integer      | 구매 크레딧 수량        | 2000 (-1: 영구라이선스)     |
| purchase_price           | Integer      | 구매 가격 (원)          | 20000                       |
| payment_method           | String       | 결제 방법               | CARD, BANK_TRANSFER, PAYPAL |
| payment_status           | String       | 결제 상태               | COMPLETED, PENDING, FAILED  |
| payment_transaction_id   | String       | 결제 트랜잭션 ID        | TXN_ABC123                  |
| purchased_at             | ISO DateTime | 구매일시                | 2025-10-12T10:30:00.123Z    |
| activated_at             | ISO DateTime | 활성화일시              | 2025-10-12T10:31:00.456Z    |
| notes                    | String       | 비고                    | 프로모션 할인 적용          |

### 5. usage_history 시트 (신규)
크레딧 사용 내역을 관리하는 시트

| 컬럼명                  | 타입         | 설명                        | 예시                                   |
|-------------------------|--------------|-----------------------------|----------------------------------------|
| usage_id                | String       | 사용 ID (Primary Key)       | USE_20251012_001                       |
| user_email              | String       | 사용자 이메일               | insung.lee1973@gmail.com               |
| app_name                | String       | 사용 앱                     | bom2excel                              |
| hardware_fingerprint    | String       | 하드웨어 지문               | abc123def456...                        |
| credits_used            | Integer      | 사용 크레딧                 | 100                                    |
| work_description        | String       | 작업 설명                   | BOM 변환: 25ASC010-A00-120-00.SLDDRW   |
| credits_from_trial      | Integer      | 체험판에서 차감한 크레딧    | 100                                    |
| credits_from_purchased  | Integer      | 구매크레딧에서 차감한 크레딧| 0                                      |
| trial_balance_after     | Integer      | 차감 후 체험판 잔고         | 1700                                   |
| purchased_balance_after | Integer      | 차감 후 구매크레딧 잔고     | 4000                                   |
| used_at                 | ISO DateTime | 사용일시                    | 2025-10-12T09:30:00.123Z               |
| sync_status             | String       | 동기화 상태                 | SYNCED, PENDING, FAILED                |
| synced_at               | ISO DateTime | 동기화일시                  | 2025-10-12T09:35:00.456Z               |

### 6. admin_config 시트 (기존 유지 + 확장)
관리자 설정을 관리하는 시트

| 컬럼명        | 타입      | 설명                    | 예시                        |
|---------------|-----------|-------------------------|-----------------------------|
| config_key    | String    | 설정 키 (Primary Key)   | email_from                  |
| config_value  | String    | 설정 값                 | insung.lee1973@gmail.com    |
| config_type   | String    | 설정 타입               | EMAIL, SYSTEM, POLICY       |
| description   | String    | 설정 설명               | 시스템 발신 이메일 주소     |
| enabled       | Boolean   | 활성 상태               | TRUE/FALSE                  |
| created_at    | Datetime  | 생성일시                | 2025-10-12 10:00:00         |
| updated_at    | Datetime  | 업데이트일시            | 2025-10-12 10:00:00         |

#### admin_config 주요 설정 키:

- **email_from**: 발신 이메일
- **email_to**: 수신 이메일
- **email_login**: 이메일 로그인 키
- **smtp_server**: SMTP 서버
- **smtp_port**: SMTP 포트
- **credit_unit_price**: 크레딧 단가 (원/2000크레딧)
- **trial_credits_default**: 기본 체험판 크레딧
- **sync_interval**: 동기화 간격 (초)

## 데이터 플로우
로컬 .json 파일 (credit_changed: true)<br/>
        ↓<br/>
sync_scheduler 감지 (주기적 체크)<br/>
        ↓<br/>
wf_creditmanager_simple.py (동기화 실행)<br/>
        ↓<br/>
google_sheets_manager.py (시트 업데이트)<br/>
        ↓<br/>
구글 시트 6개 시트 동기화:<br/>
├── credit_sync (현재 잔고)<br/>
├── usage_history (사용 내역)<br/>
├── purchase_history (구매 내역)<br/>
├── app_policies (앱 정책)<br/>
├── registrations (사용자 등록)<br/>
└── admin_config (관리자 설정)

## 구현 우선순위
1차: credit_sync 시트 구현 (현재 잔고 동기화)
2차: usage_history 시트 구현 (사용 내역 동기화)
3차: app_policies 시트 구현 (앱 정책 관리)
4차: purchase_history 시트 구현 (구매 내역 관리)
5차: admin_config 시트 확장 (고급 설정)
이 구조로 구현하면 사용자별, 앱별 크레딧을 체계적으로 관리하고, 나중에 통합 관리로 확장하기도 용이합니다.