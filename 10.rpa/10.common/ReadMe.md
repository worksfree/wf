# 프로젝트 개요
기구설계자 및 제조업 엔지니어를 위한 Python 업무자동화 앱 및 앱 스토어의 공통 라이선스 관리 모듈

## 앱 목록 및 약어

| 앱 이름 | 약어 | 설명 | 크레딧 정책 |
|--------|------|------|------------|
| bom_exporter | be | BOM 엑셀 변환 (SolidWorks) | 100 크레딧/작업 |
| dwg_batch_print | dp | DWG 도면 일괄 인쇄 | 40 크레딧/작업 |
| dwg_classifier | dc | DWG 도면 분류 | 50 크레딧/작업 |
| conversion_verifier | cv | PDF/DWG 변환 검증 | 무료 앱 |
| korean_filename_normalizer | kfn | 한글 자소분리 파일명 정규화 | 무료 앱 |
| attribute_reset | ar | 도면 속성 초기화 | 200 크레딧/작업 |

## 프로젝트 폴더 구조

<detail>
<pre>
10.rpa/
├── 10.common/
│   ├── config/                        # 통합 앱 설정 (개발 환경)
│   │   ├── wf_rpa_config.json         # 전역 RPA 설정
│   │   ├── {service-account}.json     # Google 서비스 계정 키
│   │   ├── bom_exporter/
│   │   │   ├── settings.json          # 앱 설정
│   │   │   ├── policy.json            # 크레딧 정책
│   │   │   └── credit_history.json    # 크레딧 이력
│   │   ├── dwg_batch_print/
│   │   ├── dwg_classifier/
│   │   ├── conversion_verifier/
│   │   ├── korean_filename_normalizer/
│   │   └── attribute_reset/
│   ├── wf_credit_manager.py           # 크레딧 관리
│   ├── wf_email.py                    # 이메일 발송
│   ├── wf_googlesheets_manager.py     # Google Sheets 연동
│   ├── wf_hwinfo.py                   # 하드웨어 지문
│   ├── wf_log.py                      # 로깅 (30일 자동 삭제)
│   ├── wf_register.py                 # 사용자 등록
│   └── wf_settings_common.py          # 공통 설정
├── 30.apps/                           # SolidWorks 연동 앱
│   ├── bom_exporter/
│   ├── dwg_batch_print/
│   └── attribute_reset/
├── 50.data/                           # 데이터 처리 앱
│   ├── dwg_classifier/
│   ├── conversion_verifier/
│   └── korean_filename_normalizer/
├── 90.tests/                          # 테스트
│   ├── dynamic/unit/
│   ├── dynamic/integration/
│   └── conftest.py
└── pytest.ini
</pre>
</detail>

## 실행 모드 (dev / demo / release)

### 모드 개요

| 모드 | 용도 | 감지 방법 | 환경변수 설정 |
|------|------|----------|--------------|
| **dev** | 개발/디버깅 | `.py` 파일 직접 실행 | 불필요 (자동 감지) |
| **demo** | 데모 시연/화면 캡처 | 환경변수 명시적 설정 | `WF_RPA_MODE=demo` |
| **release** | 배포/사용자 실행 | PyInstaller exe 실행 | 불필요 (자동 감지) |

### 모드 감지 로직 (통일된 방식)

모든 6개 앱이 동일한 모드 감지 로직을 사용합니다:

```python
def _detect_run_mode():
    """
    실행 모드 감지 (환경변수 + sys.argv 기반 통일 방식)
    - 1순위: WF_RPA_MODE 환경변수 (demo 모드 명시적 지정용)
    - 2순위: .py 파일 직접 실행 → dev
    - 3순위: 기본값 release (exe 실행)
    """
    # 1순위: 환경변수 WF_RPA_MODE (명시적 제어)
    env_mode = (os.environ.get("WF_RPA_MODE") or "").strip().lower()
    if env_mode in ("dev", "demo", "release"):
        return env_mode
    # 2순위: .py 파일 직접 실행 → dev
    if sys.argv[0].endswith(".py"):
        return "dev"
    # 3순위: 기본값 release
    return "release"
```

**사용 예시:**
```powershell
# dev 모드 (자동 감지)
python ui_main.py

# demo 모드 (환경변수 설정)
$env:WF_RPA_MODE = "demo"; python ui_main.py

# release 모드 (exe 실행 시 자동)
.\bom_exporter.exe
```

---

## 모드별 상세 비교

### 1. 파일 경로 비교

| 항목 | dev | demo | release |
|------|-----|------|---------|
| **설정 파일** | `10.common/config/{app}/settings.json` | `10.common/config/{app}/settings.json` | `~/.wf_rpa/{app}/settings.json` |
| **정책 파일** | `10.common/config/{app}/policy.json` | `10.common/config/{app}/policy.json` | `~/.wf_rpa/{app}/policy.json` |
| **로그 디렉토리** | `{app_folder}/logs/` | `{app_folder}/logs/` | `~/.wf_rpa/{app}/logs/` |
| **Startup Profile** | `{cwd}/startup_profile.log` | `{cwd}/startup_profile.log` | `~/.wf_rpa/{app}/startup_profile.log` |
| **데모 캡처** | `{app_folder}/demo_captures/` | `{app_folder}/demo_captures/` | `~/.wf_rpa/{app}/demo_captures/` |

### 2. 기능/동작 비교

| 기능 | dev | demo | release |
|------|-----|------|---------|
| **관리자 암호** | 불필요 (즉시 진입) | 필요 | 필요 |
| **관리자 암호 소스** | - | Google Sheets → fallback | Google Sheets → fallback |
| **콘솔 로그 레벨** | DEBUG | DEBUG | INFO |
| **파일 로그 레벨** | DEBUG | DEBUG | DEBUG |
| **데모 비디오 모드** | Off | On (3초/2초 pause) | Off |
| **Alt+C 캡처** | 수동 가능 | 수동 가능 | 수동 가능 |
| **Alt+G Geometry 저장** | 가능 | 가능 | 가능 |
| **라이선스 체크 (콘솔)** | 비활성화 | 비활성화 | 활성화 |

### 3. 설정 파일 경로 우선순위

#### **DEV / DEMO 모드:**
```
1순위: 10.common/config/{app_name}/settings.json       ← 개발자 설정
2순위: {app_folder}/config/{app_name}/settings.json    ← 폴백
```

#### **RELEASE 모드:**
```
1순위: ~/.wf_rpa/{app_name}/settings.json              ← 사용자 설정 우선
2순위: {MEIPASS}/.wf_rpa/{app_name}/settings.json      ← 번들 fallback
```

> **설계 의도**: 
> - **DEV/DEMO**: 개발자가 프로젝트 내 설정 파일로 빠르게 테스트
> - **RELEASE**: 사용자 홈의 설정을 우선 읽어 사용자 커스터마이제이션 반영

---

## 로깅 시스템

### 로거 사용법
```python
from wf_log import get_app_logger
logger = get_app_logger("bom_exporter")
```

### 로그 레벨별 출력

| 레벨 | dev 콘솔 | demo 콘솔 | release 콘솔 | 파일 (전 모드) |
|------|----------|-----------|--------------|---------------|
| DEBUG | O | O | X | O |
| INFO | O | O | O | O |
| WARNING | O | O | O | O |
| ERROR | O | O | O | O |

### 로그 파일 관리
- **포맷**: `YYYYMMDD.txt` (일별 파일)
- **자동 삭제**: 30일 이상된 로그 파일 자동 정리
- **위치**:
  - dev/demo: `{app_folder}/logs/`
  - release: `~/.wf_rpa/{app_name}/logs/`

---

## 관리자 모드

### 관리자 암호 정책

| 실행 모드 | 암호 필요 | 설명 |
|-----------|----------|------|
| dev | X | 개발 편의를 위해 암호 없이 즉시 진입 |
| demo | O | 데모 시연 시 관리자 기능 보호 |
| release | O | 배포 버전에서 관리자 기능 보호 |

### 관리자 암호 소스 우선순위
1. Google Sheets `admin_config` 시트의 `admin_pw` 값
2. fallback: `"admin2024"` (기본값)

### 구현 코드
```python
# ui_main.py - 관리자 모드 진입
run_mode = _detect_run_mode()
if run_mode == "dev":  # dev 모드에서만 암호 없이 진입
    self._enter_admin_mode()
else:
    # demo/release 모드에서는 암호 입력 필요
    password = simpledialog.askstring("관리자 모드", "암호를 입력하세요:", show='*')
    if password == self.admin_password:
        self._enter_admin_mode()
```

### 관리자 모드 기능

관리자 모드 진입 시 하드웨어 정보를 로그에 기록:
```python
if self.is_admin_mode:
    from wf_hwinfo import get_hw_fingerprint, get_cpuinfo, get_mbinfo
    self.logger.info(f"[ADMIN] HW Fingerprint: {get_hw_fingerprint()}")
    self.logger.info(f"[ADMIN] CPU Info: {get_cpuinfo()}")
    self.logger.info(f"[ADMIN] MB Info: {get_mbinfo()}")
```

---

## 데모 모드 전용 기능

### 데모 비디오 모드
`demo` 모드에서만 활성화되는 기능:

| 설정 | 값 | 용도 |
|------|-----|------|
| `demo_video_mode` | True | 화면 녹화용 속도 조절 |
| `demo_pause_after_click` | 3.0초 | UI 클릭 후 대기 시간 |
| `demo_pause_after_dialog` | 2.0초 | 다이얼로그 후 대기 시간 |

### 단축키

| 키 | 기능 | dev | demo | release |
|----|------|-----|------|---------|
| Alt+G | 창 geometry 저장 | O | O | O |
| Alt+C | 화면 캡처 | O | O | O |

> **참고**: Alt+C 캡처는 모든 모드에서 수동으로 사용 가능하나, demo 모드에서는 `demo_video_mode` 설정으로 자동화 속도가 느려져 캡처에 유리함

### Alt+G Geometry 저장 기능 상세

모든 앱의 **메인창, 설정창, 등록창**에서 Alt+G 단축키로 현재 창의 위치와 크기를 `settings.json`에 저장합니다.

#### 저장 위치 및 키

| 창 종류 | 저장 키 | 설명 |
|---------|---------|------|
| 메인창 | `ui_config.window_geometry_override` | 앱 메인 윈도우 |
| 설정창 | `ui_config.settings_window_geometry` | 설정 다이얼로그 |
| 등록창 | `ui_config.registration_window_geometry` | 체험판 등록 창 |

#### settings.json 구조 예시

```json
{
  "ui_config": {
    "window_geometry_override": "800x600+100+100",
    "settings_window_geometry": "600x400+150+150",
    "registration_window_geometry": "500x350+200+200",
    "last_selected_folder": "D:\\projects"
  }
}
```

#### 구현 위치

- **메인창**: 각 앱의 `ui_main.py` → `_on_debug_geometry_capture()` → `config.update_window_geometry_override()`
- **설정창**: 각 앱의 `ui_setting.py` → `_on_debug_geometry_capture()` → `config.update_settings_window_geometry()`
- **등록창**: `wf_register.py` → `_on_debug_geometry_capture()` → `config.update_registration_window_geometry()`

#### 토스트 메시지

저장 성공 시: `"geometry 저장됨: 800x600+100+100"`
저장 실패 시: `"geometry: 800x600+100+100"` (저장 없이 표시만)

---

## PyInstaller 빌드 및 배포

### Frozen 감지

PyInstaller로 빌드된 exe 실행 여부 감지:
```python
is_frozen = getattr(sys, "frozen", False)

if is_frozen:
    # Release/exe 모드: PyInstaller 번들에서 실행
    bundle_dir = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
else:
    # Dev/source 모드: 소스 코드에서 실행
    bundle_dir = Path(__file__).parent
```

### 번들 설정 파일 복사 (첫 실행 시)

release 모드 첫 실행 시 번들된 설정 파일을 사용자 홈으로 복사:
```python
if is_frozen:
    bundled_config = Path(sys._MEIPASS) / ".wf_rpa" / "bom_exporter" / "settings.json"
    user_config = Path.home() / ".wf_rpa" / "bom_exporter" / "settings.json"

    if not user_config.exists() and bundled_config.exists():
        user_config.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(bundled_config, user_config)
```

### 배포 폴더 구조

**개발 환경 (소스 트리)**:
```
10.rpa/
├── 10.common/
│   └── config/
│       └── bom_exporter/
│           ├── settings.json
│           └── policy.json
└── 30.apps/
    └── bom_exporter/
        ├── ui_main.py
        └── ...
```

**배포 환경 (PyInstaller 번들)**:
```
bom_exporter/
├── bom_exporter.exe
└── _internal/
    └── .wf_rpa/
        └── bom_exporter/
            ├── settings.json
            └── policy.json
```

**사용자 환경 (설치 후)**:
```
%USERPROFILE%/.wf_rpa/
├── wf_rpa_config.json          # 전역 설정
├── bom_exporter/
│   ├── settings.json           # 앱 설정
│   ├── policy.json             # 크레딧 정책
│   ├── credit_history.json     # 크레딧 이력
│   └── logs/
│       └── YYYYMMDD.txt        # 로그 파일
└── dwg_batch_print/
    └── ...
```

---

## 앱 템플릿 구조

### 2입력 앱 (dwg_classifier 참조)
- **입력**: 폴더 선택 + 엑셀 파일 선택 (Listbox, 다중 선택)
- **UI**: ~2,600 라인
- **Automation**: ~1,400 라인

### 1입력 앱 (다른 5개 앱 참조)
- **입력**: 폴더/파일 선택 (Entry)
- **UI**:
  - 간단형 (attribute_reset): ~380 라인
  - 복잡형 (bom_exporter): ~2,900 라인
- **Automation**: 300~2,600 라인

### 신규 앱 개발 시 수정 파일
1. `ui_main.py` - 메인 UI
2. `ui_setting.py` - 설정 창
3. `automation.py` - 자동화 로직
4. `app_setting_data.py` - 설정 로더 (템플릿 복사 후 앱 이름만 변경)

### 버전 정보 단일 소스 원칙

앱 버전 정보는 반드시 `ui_main.py`에서 로드하고, 다른 모듈은 이를 import해서 사용합니다:

```python
# ui_main.py - 버전 정보 로드 (단일 소스)
APP_VERSION_FULL = _load_version_from_settings()  # "v0.8.4.9"
APP_VERSION_DISPLAY = "v" + ".".join(APP_VERSION_FULL.lstrip("v").split(".")[:2])  # "v0.8"

# ui_setting.py - 버전 정보 import (단일 소스 원칙)
def _get_version_from_main():
    """ui_main.py에서 버전 정보 가져오기"""
    global APP_VERSION_FULL, APP_VERSION_DISPLAY
    if APP_VERSION_FULL is not None:
        return APP_VERSION_FULL, APP_VERSION_DISPLAY
    try:
        from ui_main import APP_VERSION_FULL as main_full, APP_VERSION_DISPLAY as main_display
        APP_VERSION_FULL = main_full
        APP_VERSION_DISPLAY = main_display
    except ImportError:
        APP_VERSION_FULL = _load_version_fallback()  # 설정 파일에서 직접 로드
        ...
    return APP_VERSION_FULL, APP_VERSION_DISPLAY
```

**주의**: `ui_setting.py`에서 버전 정보를 직접 로드하면 경로 불일치로 잘못된 버전이 표시될 수 있습니다.

## 로딩 최적화

| 앱 | 로딩 시간 목표 | 최적화 기법 |
|----|---------------|------------|
| bom_exporter | < 1초 | Lazy import, 비동기 정책 로드 |
| dwg_batch_print | < 1초 | Lazy import |
| dwg_classifier | < 1초 | Lazy import |
| conversion_verifier | < 1초 | Lazy import |
| korean_filename_normalizer | < 1초 | Lazy import |
| attribute_reset | < 1초 | 간단한 구조 |


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

---

## 🔐 Google Sheets API 자격증명

### 개발 환경 구조

```
10.common/
├── credentials/
│   ├── README.md                    # 이 파일
│   ├── google-service-account.json  # 실제 구글 서비스 계정 키 (gitignore)
│   └── google-service-account.json.template  # 템플릿 파일
└── wf_googlesheets_manager.py
```

### 배포 환경 구조

각 앱 배포 시:
```
app_folder/
├── res/
│   └── google-service-account.json  # PyInstaller로 번들링
└── app.exe
```

### 사용자 환경 구조

사용자 설치 후:
```
%USERPROFILE%/.wf_rpa/
├── credentials/
│   └── google-service-account.json  # 런타임에 복사/생성
├── .wf_rpa_config.json
└── .wf_app_policies.json
```

### 주의사항

1. **개발 환경**: `google-service-account.json`은 절대 git에 커밋하지 마세요
2. **배포 환경**: PyInstaller가 자동으로 각 앱에 포함시킵니다
3. **사용자 환경**: 앱 초기 실행시 자동으로 홈 폴더에 복사됩니다

### 사용법

1. Google Cloud Console에서 서비스 계정 키를 다운로드
2. `10.common/credentials/google-service-account.json`로 저장
3. `.spec` 파일이 자동으로 배포에 포함
4. 앱 실행시 사용자 홈에 자동 설치

---

## 📊 Google Sheets 데이터 구조

### 전체 데이터 구조 분석

#### 현재 상황 분석
- 사용자별 앱 크레딧: 각 사용자가 각 앱에 대해 독립적인 크레딧 보유
- 로컬 관리: .wf_rpa/[app_name]/.{app_name}_credits.json 파일로 관리
- 동기화 필요: 로컬 변경사항을 구글 시트에 주기적으로 동기화

#### 관리해야 할 핵심 데이터
- 사용자 등록 정보 (기존 registrations 시트)
- 앱별 정책 정보 (새로운 app_policies 시트)
- 사용자별 크레딧 현황 (새로운 credit_sync 시트)
- 크레딧 구매 내역 (새로운 purchase_history 시트)
- 크레딧 사용 내역 (새로운 usage_history 시트)
- 관리자 설정 (기존 admin_config 시트)

### 구글 시트 구조 정의

#### 1. registrations 시트 (기존 유지)
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

#### 2. app_policies 시트 (신규)
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

#### 3. credit_sync 시트 (신규 - 핵심)
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

#### 4. purchase_history 시트 (신규)
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

#### 5. usage_history 시트 (신규)
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

#### 6. admin_config 시트 (기존 유지 + 확장)
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

##### admin_config 주요 설정 키:

- **email_from**: 발신 이메일
- **email_to**: 수신 이메일
- **email_login**: 이메일 로그인 키
- **smtp_server**: SMTP 서버
- **smtp_port**: SMTP 포트
- **credit_unit_price**: 크레딧 단가 (원/2000크레딧)
- **trial_credits_default**: 기본 체험판 크레딧
- **sync_interval**: 동기화 간격 (초)

### 데이터 플로우

```
로컬 .json 파일 (credit_changed: true)
        ↓
sync_scheduler 감지 (주기적 체크)
        ↓
wf_creditmanager_simple.py (동기화 실행)
        ↓
google_sheets_manager.py (시트 업데이트)
        ↓
구글 시트 6개 시트 동기화:
├── credit_sync (현재 잔고)
├── usage_history (사용 내역)
├── purchase_history (구매 내역)
├── app_policies (앱 정책)
├── registrations (사용자 등록)
└── admin_config (관리자 설정)
```

### 구현 우선순위
1차: credit_sync 시트 구현 (현재 잔고 동기화)
2차: usage_history 시트 구현 (사용 내역 동기화)
3차: app_policies 시트 구현 (앱 정책 관리)
4차: purchase_history 시트 구현 (구매 내역 관리)
5차: admin_config 시트 확장 (고급 설정)

---

## 🔄 크레딧 관리 플로우차트

### 시나리오 1: 신규 사용자 체험판 사용

```mermaid
sequenceDiagram
    participant U as 사용자
    participant A as 앱
    participant L as 로컬 파일
    participant G as 구글 시트

    U->>A: 앱 첫 실행
    A->>U: 사용자 등록 창
    U->>A: 정보 입력 (이메일, 이름 등)
    A->>A: 하드웨어 지문 생성
    A->>G: registrations 테이블에 등록
    A->>L: .bom2excel_credits.json 생성
    A->>G: credit_sync 테이블에 체험판 2000 기록
    A->>U: 등록 완료, 체험판 2000 크레딧 제공
```

### 시나리오 2: 크레딧 사용 및 동기화

```mermaid
sequenceDiagram
    participant U as 사용자
    participant A as 앱
    participant L as 로컬 파일
    participant S as 동기화 스케줄러
    participant G as 구글 시트

    U->>A: 파일 처리 요청
    A->>A: 크레딧 잔고 확인 (1900 잔고)
    A->>A: 작업 수행 (100 크레딧 차감)
    A->>L: credit_changed = true 설정
    A->>L: usage_history에 기록
    A->>U: 작업 완료, 잔고 1800

    Note over S: 5분마다 체크
    S->>L: credit_changed 확인
    S->>G: credit_sync 테이블 업데이트
    S->>G: usage_history 테이블에 기록
    S->>L: credit_changed = false 설정
```

### 시나리오 3: 크레딧 구매 및 활성화

```mermaid
sequenceDiagram
    participant U as 사용자
    participant A as 앱
    participant N as 네이버 스마트스토어
    participant Admin as 관리자
    participant G as 구글 시트
    participant E as 이메일 시스템

    U->>A: 크레딧 부족 상황
    A->>U: 구매 안내 메시지
    U->>N: 네이버 스마트스토어에서 구매
    N->>U: 구매 완료

    Admin->>G: purchase_history에 구매 정보 입력
    Admin->>Admin: 활성화 코드 생성 (AC_BOM_001)
    Admin->>E: 구매자에게 활성화 코드 이메일 발송

    E->>U: 활성화 코드 이메일 수신
    U->>A: 앱에서 활성화 코드 입력
    A->>G: 활성화 코드 검증
    A->>G: credit_sync 테이블에 구매 크레딧 추가
    A->>U: 활성화 완료, 새 잔고 표시
```

---

## 부록

### 부록 A: 빌드/패키징 불변 규칙 (BUILD INVARIANTS)

> 빌드 및 패키징 과정에서 **반드시** 지켜져야 할 규칙

#### 빌드 스크립트 사용 필수
- `pyinstaller {app}.spec` 직접 실행 금지
- 반드시 `build_{app}.ps1` 사용
- 출력 위치: `D:\release\candidates\{app}_{version}\`
- 빌드 완료 후 앱 폴더 내 `build/`, `dist/` 삭제

#### 패키지 필수 포함 항목
**설정 파일**:
- `_internal/.wf_rpa/wf_rpa_config.json` (공통 설정)
- `_internal/.wf_rpa/{app}/policy.json` (앱별 정책)
- `_internal/.wf_rpa/{app}/settings.json` (앱별 설정, 버전 정보 포함)

**아이콘**:
- `_internal/res/{nn}_{AppName}.ico` (멀티사이즈: 16, 32, 48, 256)

**설정 스크립트** (BAT 파일 6종):
- `setup_worksfree.bat`, `바로가기_생성.bat`, `설정_초기화.bat`
- `전체_초기화.bat`, `등록정보_동기화.bat`, `제거.bat`

#### 아이콘 규칙
- 파일명 형식: `{번호}_{AppDisplayName}.ico`
- 필수 사이즈: 16x16, 32x32, 48x48, 256x256
- 소스 SVG 보존: `res/{번호}_{AppDisplayName}.svg`

#### 버전 관리
- 형식: `v{major}.{minor}.{patch}.{build}`
- 빌드 시 마지막 자리 자동 증가
- 저장 위치: `settings.json`의 `runtime_config.full_version`
- 표시 규칙: 메인 UI (2자리), 설정창 (4자리)

#### 절대 하지 말아야 할 것
- pyinstaller 직접 실행 (빌드 스크립트 우회)
- spec 파일에서 icon 파라미터 None으로 설정
- settings.json의 full_version 필드 제거
- BAT 파일 복사 로직 제거
- res 폴더 번들링 제거

---

### 부록 B: 다국어화(i18n) 설계 (향후 구현 예정)

> **상태**: 설계 완료, 구현 대기 (배포 형상 완성 후 진행)

#### 개요
- **목적**: 해외 고객 지원 (영어), 문자열 중앙 관리
- **범위**: UI 텍스트, 로그 메시지, 이메일 내용
- **지원 언어**: 한국어 (ko), 영어 (en)

#### 파일 구조
```
10.common/
├── i18n/
│   ├── wf_i18n.py            # 핵심 로직
│   └── locales/
│       ├── ko.json           # 한국어 (기본)
│       └── en.json           # 영어
└── config/
    └── wf_rpa_config.json    # language 설정 추가
```

#### 사용 예시
```python
from wf_i18n import t

# 버튼 텍스트
self.start_button = tk.Button(text=t("common.buttons.start"))

# 윈도우 타이틀
self.master.title(t("apps.bom_exporter.title", version="v0.8.1"))

# 에러 메시지
messagebox.showerror(
    t("common.messages.error"),
    t("errors.file_not_selected")
)
```

#### 주요 번역 문자열 예시

| 키 | 한국어 | 영어 |
|---|--------|------|
| common.buttons.start | 시작 | Start |
| common.buttons.settings | 설정 | Settings |
| common.labels.progress | 진행률: | Progress: |
| errors.file_not_selected | 파일을 먼저 선택해주세요. | Please select a file first. |
| apps.bom_exporter.title | BOM 엑셀 저장 {version} | BOM Excel Export {version} |

자세한 내용은 `10.common/docs/i18n_design.md` 참조

---

### 부록 C: 코드 정리 이력

#### wf_googlesheets_manager 불필요 메서드 정리 (2025년)

**제거한 메서드** (실제 사용 안 함):
```python
def get_cpu_info(self) -> str
def get_motherboard_info(self) -> str  
def get_storage_info(self) -> str
```

**이유**: 
- `prepare_registration_data()`에서 `_get_hardware_info_once()`를 직접 사용
- 프로덕션 코드에서 호출하는 곳 없음

**유지한 메서드** (실제 사용 중):
```python
def get_hardware_fingerprint(self) -> str
    # sync_credit_data(), get_synced_credit_data()에서 사용
```

---

*최종 수정: 2026-01-28*
                     