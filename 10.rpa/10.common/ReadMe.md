# 프로젝트 개요
기구설계자 및 제조업 엔지니어를 위한 Python 업무자동화 앱 및 앱 스토어의 공통 라이선스 관리 모듈

## 프로젝트 폴더 구조

<detail>
<pre>
rpa_project/
├── 10.common/
│   ├── wf_config.py
│   ├── wf_credit.py
│   ├── wf_email.py
│   ├── wf_googlesheets.py
│   ├── wf_hwinfo.py
│   ├── wf_log.py
│   ├── wf_register.py
│   ├── wf_single_instance.py
│   ├── [USERHOME].wf_rpa_config.json
│   ├── [USERHOME].silver-argon-445712-a0-4ce021aa64be.json
│   ├── [USERHOME].app_name_history.json
│   ├── [USERHOME].temp/
│   └── [USERHOME].[app_name]_[timestamp].log
├── 10.common_tests/
│   ├── test_wf_all.py
│   ├── test_wf_register.py
│   ├── test_wf_gen_code.py
│   ├── test_wf_log.py
│   ├── test_wf_hwinfo.py
│   └── test_wf_email.py
├── 30.apps/
│   ├── bom2excel/
│   │   ├── bom2excel.py
│   │   ├── bom2excel.spec
│   │   └── res/
│   │       ├── uhd/
│   │       ├── qhd/
│   │       ├── fhd/
│   │       └── bom2excel.xlsx
│   ├── mct_print/
│   │   ├── mct_print.py
│   │   ├── mct_print.spec
│   │   └── res/
│   └── attribute_reset/
│       ├── attribute_reset.py
│       ├── attribute_reset.spec
│       └── res/
├── 50.data/
│   ├── dwg_classify/
│   │   ├── dwg_classify.py
│   │   ├── dwg_classify.spec
│   │   └── res/
│   ├── conversion_verify/
│   │   ├── conversion_verify.py
│   │   ├── conversion_verify.spec
│   │   └── res/
│   └── korean_filename_normalizer/
│       ├── korean_filename_normalizer.py
│       ├── korean_filename_normalizer.spec
│       └── res/
└── 90.docs/
    ├── README.md
    ├── LICENSE.txt
    ├── CHANGELOG.md
    └── INSTALL.md
</pre>
</detail>


# 공통 모듈

## 공통 모듈의 공통 구조
- 기본적으로 클래스 구조
- 각 모듈별로 독립적인 실행을 통해 테스트 가능
- GUI가 있어도 GUI 없이 테스트 가능
- 각 모듈별로 독립적인 유닛 테스트 코드 포함(quick_test 함수)
- 테스트는 set_argv() 함수를 통해 명령행 인자 설정
- set_argv()는 기본적으로 test, clean, test-and-clean 옵션 지원
- UI는 Tkinter 기반 (필요시 PyQt5로 변경 가능)
- set_argv() 함수로 설정된 아규먼트가 없으면 GUI 실행, GUI 기반이 아니면 test, clean, test-and-clean 옵션 안내 문구 출력하고 종료
- 테스트시 데이터를 생성하는 경우 clean 옵션으로 생성된 데이터 삭제 가능
- 임시 데이터의 저장 위치는 사용자 홈 디렉토리의 .temp 폴더
- .temp 폴더는 자동으로 생성되며, 사용자가 직접 삭제 가능
- 언제든 테스트를 실행할 때 .temp 폴더에 기존 데이터가 있다면 해당 데이터를 삭제하고 시작
- 구글 시트에 접속하는 모듈은 구글 서비스 계정 키 파일을 사용자 홈 디렉토리의 .silver-argon-445712-a0-4ce021aa64be.json 파일로 저장
- 구글 시트에 접속하는 모듈은 접근 빈도수 제한이 있으므로 테스트 코드에서는 접속간격을 10초로 설정


## 1단계 MVP
### 1. wf_config.py:
- 글로벌 설정 및 앱별 설정 관리 모듈 (json 파일 읽기/쓰기)
- 앱별 체험판 크레딧 관리 기능 포함
- 통합 크레딧 관리 기능 포함
- 설정 파일은 사용자 홈 폴더에 .wf_rpa_config.json 파일로 저장
- 크레딧 변경 플래그 관리 기능 포함

### 2. wf_credit.py:
- 크레딧 관리 모듈 (Google Sheets 연동)
- 기본적으로 크레딧 관리는 로컬 캐시 파일을 사용하여 오프라인 상태에서 크레딧 관리
- 크레딧 변경 플래그가 설정된 경우에만 구글 시트와 동기화
- 크레딧 차감, 크레딧 사용량 로그 기록 기능 포함
- 크레딧이 -1, -2인 경우는 크레딧을 차감하지는 않지만 사용량 로그는 여전히 기록해야 함

#### 앱별 크레딧 정책
app_name                    |  icon_text  |  description                |  default_credit  |  credit_per_work  |  available_work  |  permanant-price
----------------------------|-------------|-----------------------------|------------------|-------------------|------------------|-----------------
Bom2Excel_Exporter          |  B2E        |  도면 처리 앱                    |  2,000           |  100              |  20              |  2,000,000      
DWG_Classifier              |  D2F        |  도면 분류 앱                    |  2,000           |  50               |  40              |  1,000,000      
Conversion_Verifier         |  C2V        |  변환 검증 앱                    |  2,000           |  10               |  200             |  500,000        
Korean_FileName_Normalizer  |  HFN        |  자소분리된 한글 파일이름을 다시 결합해주는 앱  |  -1              |  0                |  -1              |  0              
DWG_Batch_Print             |  DBP        |  DWG 도면 파일을 자동 출력해주는 앱      |  2,000           |  40               |  50              |  500,000        
Drawing_Attribute_Reset     |  DAR        |  파트 파일의 속성을 정리해주는 앱         |  2,000           |  200              |  10              |  2,000,000      

#### 크레딧 계산 방식
- **credit_per_work**: 작업당 소모되는 크레딧, 복잡한 앱은 많이 차감되고 단순한 앱은 적게 차감됨
- **available_work**: 해당 앱이 현재 보유한 크레딧으로 작업 가능한 횟수
- **pay_load**: 크레딧의 결제 단위, 기본 결제 단위는 금액으로 2만원, 2000 크레딧 단위로 구매 가능

#### 크레딧 타입
1. **trial credit**: 체험판 (기본 크레딧 제공, 크레딧 차감), 기본 크레딧은 모든 앱 공통으로 2000 크레딧
2. **paid credit**: 유료 구매 (크레딧 차감), 0, 양수 무한대
3. **free credit**: 무료 (크레딧 차감 없음), -1
4. **permanent license**: 영구 라이선스 (크레딧 차감 없음), -2

### 2. wf_register.py:
- 사용자 이메일, 하드웨어 지문(CPU/메인보드 등) 관리
- 사용자 등록 및 조회 기능
- 이메일과 하드웨어 지문 중복 체크 기능

#### registrations 시트 (Sheet1: "registrations")

| Column        | DataType           |  Description              | Example
|---------------|-------------------|------------------|----------------
|user_email            | string  | 사용자 이메일         | user@company.com
|user_name             | string  | 사용자 이름          | 홍길동
|user_phone            | string  | 전화번호            | 010-1234-5678
|user_email_consent    | string  | 마케팅 동의 (Y/N)    | Y
|user_hw_fingerprint   | string  | 하드웨어 지문         | 1234567890
|user_hw_cpuinfo       | string  | CPU 정보            | Intel(R) Core(TM) i7-9700K CPU @ 3.60GHz
|user_hw_mbinfo        | string  | MotherBoard UUID    | 123e4567-e89b-12d3-a456-426614174000
|ts_created_at         | datetime  | 등록 시간           | 2025-01-01 10:30:00
|ts_updated_at         | datetime  | 수정 시간           | 2025-01-15 14:20:00
|ts_last_access        | datetime  | 최근 접속 시간      | 2025-01-15 14:20:00
|status                | string  | 상태 (ACTIVE/BLOCKED)      | ACTIVE
|first_app             | string  | 처음 등록한 앱      | Bom2Excel_Exporter
|acc_purchased_credit  | string  | 구매 크레딧 (수식)  | "=sumif(purchase_history!A:A,10000)"
|acc_usage_credit      | string  | 사용 크레딧 (수식)  | "=sumif(credit_usage!A:A,10000)"

### 구글 시트 컬럼명 명명규칙
- 컬럼명은 소문자, 밑줄(_)로 구분
- user_로 시작하는 컬럼은 사용자가 입력한 정보
- ts_로 시작하는 컬럼은 타임스탬프 정보
- uc_로 시작하는 컬럼은 사용자의 클라이언트PC 정보로 앱에서 읽어와서 등록한 정보
- ua_로 시작하는 컬럼은 사용자 관련 정보이나 관리자가 수정하고 관리하는 정보

### 3. wf_googlesheets.py:
- 구글 시트 연동 모듈
- 구글 시트 읽기/쓰기 기능 포함
- 구글 시트 데이터프레임 변환 기능 포함
- 구글 시트 테스트용 ID : 1bUqpV1vSGwsVeWav-6enZUzaKBTJdxX5eZ737lNh6Ww
- 구글 시트 서비스용 ID : 13OuY3j6nzUxOfIT07LiU264OImtkxrdPDEdRW8eRTv8
- 현재는 테스트용 ID로만 구현
- scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
- gspread json key file : .silver-argon-445712-a0-4ce021aa64be.json (사용자 홈 디렉토리에 저장)
- 구글 시트 접근 빈도수 제한이 있으므로 테스트 코드에서는 접속간격을 10초로 설정

### 4. wf_hwinfo.py:
- 하드웨어 지문(CPU, 메인보드 등) 조회 모듈
- 윈도우만 구현
- 사용자 등록시 하드웨어 지문 정보를 구글 시트에 저장
- 하드웨어 지문은 CPU 정보, 메인보드 UUID를 조합하여 생성
- cpu의 processorid를 얻기 어려운 경우에는 cpu의 name, mode등 대체 정보를 사용
- mainboard의 uuid를 얻기 어려운 경우에는 serialnumber, product등 대체 정보를 사용
- 하드웨어 지문은 CPU 정보와 메인보드 UUID를 조합하여 생성
  
### 5. wf_log.py:
- 로그 파일 관리 모듈
- 로그 파일 생성 및 회전 기능 포함
- 로그 레벨 설정 기능 포함
- 로그 포맷터 설정 기능 포함
- 로그는 기본적으로 콘솔 출력과 파일 출력 모두 지원
- 콘솔 로그는 로그 레벨로 조정하지만 파일 로그는 항상 DEBUG 레벨로 모든 내용을 기록
- 로그 파일은 사용자 홈 디렉토리에 [app_name]_[timestamp].log 형식으로 저장
- 30일 이상된 로그 파일은 자동으로 삭제

### 6. wf_email.py:
- 이메일 발송 모듈
- 이메일 발송 기능 포함
- SMTP 서버 설정 기능 포함
- 이메일 템플릿 기능 포함
- 이메일 발송 로그 기록 기능 포함
- 이메일 발송 실패시 재시도 기능 포함

### 7. wf_single_instance.py:
- 싱글 인스턴스(다중 실행 방지) 모듈
- 앱이 다중 실행되지 않도록 방지하는 기능 포함
- 윈도우만 구현
- 당사에서 배포한 앱은 모두 싱글 인스턴스로 실행
- 이종 앱일지라도 자사 앱은 한번에 하나만 실행 가능함
- 다중 실행시 기존 앱을 종료하고 새 앱을 실행하는 옵션 포함
- 크레딧을 통합 관리하는 정책때문에 앱이 2개 이상 실행되면 크레딧 관리가 어려워짐
- 따라서 앱은 한번에 하나만 실행되도록 제한함
- 

## 2단계 안정화 및 3단계 고도화 
### 2단계 안정화
- wf_desktop_shortcut_v02.py: 바탕화면 바로가기 생성 모듈
- wf_auto_start_v02.py: 윈도우 시작프로그램 등록 모듈
- wf_crash_handler_v02.py: 크래시 핸들러 모듈
- wf_gui_v02.py: 공통 GUI 모듈 (Tkinter 기반)
- wf_app_updater_v02.py: 앱 자동 업데이트 GUI 모듈
- wf_app_installer_v02.py: 앱 설치 관리자 GUI 모듈
- wf_app_manager_v02.py: 앱 매니저 GUI 모듈 (설치/삭제/업데이트)
- wf_app_launcher_v02.py: 앱 실행기 GUI 모듈 (설치된 앱 목록 표시 및 실행)

### 3단계 고도화
- wf_app_store_v02.py: 앱 스토어 GUI 모듈 (앱 목록 표시 및 구매/설치)
- wf_updater_v02.py: 앱 자동 업데이트 모듈 (GitHub 릴리즈 연동)
- wf_app_license_v02.py: 앱 라이선스 GUI 모듈 (앱별 라이선스 관리)
- wf_app_help_v02.py: 앱 도움말 GUI 모듈 (앱별 도움말 및 문서 보기)
- wf_app_about_v02.py: 앱 정보 GUI 모듈 (앱별 정보 및 버전 표시)
- wf_app_feedback_v02.py: 앱 피드백 GUI 모듈 (앱별 피드백 및 문의)
- wf_app_update_checker_v02.py: 앱 업데이트 확인 모듈 (GitHub 릴리즈 연동)


#### 크레딧 관리를 위한 플로우차트

[대체 FlowChart](FlowChart.md)
```mermaid
flowchart TD
    A1([앱 다운로드 및 설치]) --> A2[앱 실행 상태 체크<br/> 단일 실행]
    A2 -- 기존 앱 실행중 --> A3[기존 앱 종료 후 새 앱 실행] --> A2
    A2 -- 실행 가능 --> B1[앱 실행 및 버튼 활성화]
    B1 -- 찾기 클릭 --> C1{로컬 캐시 파일 존재?}
    C1 -- 있음 --> D1[변경 플래그 확인]
    C1 -- 없음 --> C2[구글 시트에서 사용자 등록 조회]
    C2 -- 없음 --> C3[사용자 등록 안내]
    C2 -- 있음 --> D2[크레딧 상태 확인]

    C3 --> C4[사용자 등록/저장] --> D2

    D1 -- 변경플래그 O --> E1[서버 동기화 시도]
    D1 -- 변경플래그 X --> D2
    E1 -- 성공 --> E2[변경 플래그 초기화] --> D2
    E1 -- 실패 --> Z2[사용자 안내]

    D2{크레딧 유형/수치 판별}
    D2 -- -2(무료)/-1(영구) --> D3[차감 없이 로그만 기록,<br/>플래그 미설정] --> Z1[앱 종료]
    D2 -- 0(없음) --> Z2
    D2 -- X(양수/유효) --> F1[크레딧 충분 여부 판별]

    F1 -- 부족 --> F2[보유 크레딧 만큼만 처리] 
    F1 -- 충분 --> G1
    F2 -- 일단 진행 --> G1[로컬 캐시 차감 및 변경 플래그 설정]
    F2 -- 미진행 --> Z2
    G1 --> H1{종료 유형}
    H1 -- 정상 --> I1[크레딧 차감 및 로그 기록 → 서버 동기화] --> Z1
    H1 -- 비정상 --> I2[차감 및 플래그 설정,<br/>종료 후 재시도] --> Z1

    J1([사용자가 크레딧 구매]) --> E1

    Z1([앱 종료])
    Z2([사용자 안내])
    
```

## 추가적인 Google Sheets 구조 (개정)

### 구매 이력 시트 (Sheet2: "purchase_history")
| 컬럼명 (Column) | 데이터타입 (Type) | 설명 (Description) | 예시 (Example) |
|-----------------|------------------|--------------------|----------------|
| transaction_id  | string           | 거래 ID (Primary Key) | TXN_20250830_130919_91b429 |
| email           | string           | 구매자 이메일 | phoneonly_27a87071@test.com |
| purchase_type   | string           | 구매 유형 (credits/permanent 등) | credits |
| credits_amount  | integer          | 구매 크레딧 수량 또는 -1(영구) | 10 |
| price           | integer          | 결제 금액 (원) | 10000 |
| payment_method  | string           | 결제 수단 | test_card |
| purchase_date   | datetime         | 구매일시 | 2025-08-30 13:09:19 |
| status          | string           | 결제 상태 (completed 등) | completed |
| notes           | string           | 비고/메모 | 테스트 구매 10크레딧 |

### 사용 로그 시트 (Sheet3: "usage_logs")
Column                |  데이터 타입        |  Description            | 예시(Example) |
-----------------------|---------------------|------------------|----------------|
log_id             |  VARCHAR(64)   |  로그 고유 식별자 (예: LOG_YYYYMMDD_HHMMSS_HASH)| LOG_20250830_130628_c331c1 |
email              |  VARCHAR(255)  |  사용자 이메일                                | complete_e3ec8fc1@test.com |
app_name           |  VARCHAR(100)  |  실행된 앱 이름                               | B2E_Processor |
app_version        |  VARCHAR(20)   |  앱 버전 정보                                 | 1.0.0 |
action             |  VARCHAR(50)   |  수행된 동작 유형 (예: process_items, login 등) | process_items |
items_processed    |  INT           |  처리된 항목 개수                              | 5 |
credits_used       |  INT           |  사용한 크레딧 총합                              | 1 |
credits_deducted   |  INT           |  차감된 크레딧 실제 값                           | 1 |
remaining_credits  |  INT           |  실행 이후 잔여 크레딧                           | 49 |
accumulated_after  |  INT           |  실행 후 누적(또는 추가)된 크레딧                    | 0 |
timestamp          |  DATETIME      |  로그 발생 시각                                | 2025-08-30 13:06:28 |
hw_fingerprint     |  CHAR(32)      |  하드웨어 지문 해시값                           | 0123456789abcdef0123456789abcdef |

### 앱별 정책 시트 (Sheet4: "app_policies")
app_name                  |  icon_text  |  description                |  default_credit  |  credit_per_work  |  available_work  |  permanant-price
--------------------------|-------------|-----------------------------|------------------|-------------------|------------------|-----------------
Bom2Excel_Exporter        |  B2E        |  도면 처리 앱                    |  2,000           |  100              |  20              |  2,000,000      
DWG_Classifier            |  D2F        |  도면 분류 앱                    |  2,000           |  50               |  40              |  1,000,000      
Conversion_Verifier       |  C2V        |  변환 검증 앱                    |  2,000           |  10               |  200             |  500,000        
Han_File_Name_Normalizer  |  HFN        |  자소분리된 한글 파일이름을 다시 결합해주는 앱  |  -1              |  0                |  -1              |  0              
DWG_Batch_Print           |  DBP        |  DWG 도면 파일을 자동 출력해주는 앱      |  2,000           |  40               |  50              |  500,000        
Drawing_Attribute_Reset   |  DAR        |  파트 파일의 속성을 정리해주는 앱         |  2,000           |  200              |  10              |  2,000,000      


### 앱별 정책 시트 (Sheet4: "admin_config")
컬럼명          |  데이터 타입        |  설명                      |  예시                        
-------------|----------------|--------------------------|----------------------------
amin_pw      |  VARCHAR(100)  |  관리자 비밀번호 또는 인증용 키       |  admin3838                 
email_to     |  VARCHAR(255)  |  수신 이메일 주소               |  insung.lee@worksfree.co.kr
email_from   |  VARCHAR(255)  |  발신 이메일 주소               |  insung.lee1973@gmail.com  
email_login  |  VARCHAR(255)  |  SMTP 로그인용 앱 비밀번호 또는 토큰  |  yxvn ebai aori lytb       
smtp_server  |  VARCHAR(100)  |  SMTP 서버 주소              |  smtp.gmail.com            
smtp_port    |  INT           |  SMTP 포트 번호              |  587                       
enabled      |  BOOLEAN       |  이메일 발송 기능 활성화 여부        |  TRUE

## 📦 PyInstaller 빌드 최적화 가이드

### 🚀 최적화된 .spec 파일 구성

모든 WorksFree 앱은 다음 최적화 설정을 적용합니다:

#### 1. 성능 최적화 설정
- **onedir 모드**: 빠른 로딩 시간 (1초 이내 목표)
- **UPX 비활성화**: 압축으로 인한 로딩 지연 방지
- **디버그 심볼 제거**: 실행 파일 크기 감소
- **필수 모듈만 포함**: 대용량 라이브러리 제외

#### 2. 크기 최적화
```python
# 최적화된 excludes 설정
excludes=[
    'matplotlib', 'scipy', 'numpy.testing', 'pandas.tests',
    'tensorflow', 'torch', 'jupyter', 'IPython', 'notebook',
    'cv2', 'PIL.ImageCms', 'sklearn', 'seaborn', 'plotly',
    'bokeh', 'altair', 'statsmodels', 'sympy'
]

# EXE 최적화 설정
exe = EXE(
    strip=True,              # 디버그 심볼 제거
    upx=False,               # UPX 비활성화
    exclude_binaries=True,   # onedir 모드
)
```

#### 3. 필수 모듈 설정
```python
essential_imports = [
    # WorksFree 핵심
    'wf_log', 'wf_credit_manager', 'wf_app_base', 'wf_register',
    
    # GUI 필수
    'tkinter', 'tkinter.ttk', 'tkinter.messagebox', 'tkinter.filedialog',
    
    # PyInstaller 런타임
    'zipfile', 'multiprocessing',
    
    # 기본 시스템
    'json', 'datetime', 'threading'
]
```

#### 4. 빌드 자동화
```bash
# 새 앱 .spec 파일 생성
python generate_specs.py <app_name>

# 모든 앱 .spec 파일 업데이트  
python generate_specs.py all

# 빌드 실행
pyinstaller --noconfirm <app_name>.spec
```

### 📊 최적화 결과
- **크기 감소**: 평균 70% 감소 (104MB → 34MB)
- **로딩 시간**: 3초 이내 (콘솔 모드 1초 이내)
- **안정성**: Runtime 에러 완전 방지
- **배포**: D:\release\candidates에 타임스탬프 폴더 자동 생성

### ⚡ 빌드 최적화 체크리스트
- [ ] pyautogui 등 필수 모듈 설치 확인
- [ ] enhanced_app.spec.template 기반 .spec 생성
- [ ] onedir 모드 설정
- [ ] UPX 비활성화
- [ ] 대용량 라이브러리 excludes 설정
- [ ] 필수 hiddenimports만 포함
- [ ] strip=True로 디버그 심볼 제거
- [ ] 빌드 후 자동 패키징 확인                      