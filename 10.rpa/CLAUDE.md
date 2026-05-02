# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 프로젝트 개요

WorksFree RPA — 기구설계자/제조업 엔지니어를 위한 Python 기반 업무 자동화 솔루션 모음. Windows 전용, Tkinter GUI, PyInstaller 패키징.

## 폴더 구조

```
10.rpa/
├── 10.common/          # 모든 앱이 공유하는 공통 모듈 + 개발용 설정 파일
├── 30.apps/            # 외부 앱(SolidWorks/AutoCAD) GUI 자동화 앱
├── 50.data/            # 순수 Python 데이터 처리 앱
├── 70.webs/            # 웹 자동화 (kstartup-web 등)
├── 90.tests/           # WF-ACT 인증 툴킷 및 단위 테스트
├── build_all.ps1       # 전체 앱 일괄 빌드
└── pytest.ini
```

## 앱 목록 (약어 → 폴더)

| 약어 | 앱 이름 | 위치 | 크레딧 |
|------|---------|------|--------|
| be | bom_exporter | 30.apps/bom_exporter | 100/파일 |
| dp | batch_print (dwg_batch_print) | 30.apps/batch_print | 40/파일 |
| ar | attribute_reset | 30.apps/attribute_reset | 200/작업 |
| dc | dwg_classifier | 50.data/dwg_classifier | 50/작업 |
| cv | conversion_verifier | 50.data/conversion_verifier | 무료(-1) |
| kfn | korean_filename_normalizer | 50.data/korean_filename_normalizer | 무료(-1) |
| qr | qrcode_generator | 50.data/qrcode_generator | 무료(-1) |

## 실행 방법

```powershell
# 개발 모드 (자동 감지: .py 직접 실행)
python 30.apps/bom_exporter/ui_main.py

# 데모 모드
$env:WF_RPA_MODE = "demo"; python 30.apps/bom_exporter/ui_main.py

# release 모드 (exe 실행 시 자동)
.\bom_exporter.exe
```

## 빌드

```powershell
# 빌드 전 환경 검증 (필수)
cd D:\drive_files\10.worksfree\10.rpa
.\check_build_environment.ps1

# 개별 앱 빌드 (각 앱 폴더에서)
cd 30.apps/bom_exporter
.\build_bom_exporter.ps1

# 전체 일괄 빌드
.\build_all.ps1
```

빌드 결과는 `D:\release\candidates\{app}_{timestamp}\`에 생성됨:
- `{app}_{version}_installer.exe` (NSIS 인스톨러)
- `{app}_{version}_portable.zip`

**규칙**: `pyinstaller {app}.spec` 직접 실행 금지. 반드시 `build_{app}.ps1` 사용.

## 테스트 (WF-ACT)

```powershell
cd 90.tests/ui_lifecycle_test

# 전체 앱 FULL 인증
python run_certification.py --level full

# 특정 앱
python run_certification.py --app bom_exporter --level full
python run_certification.py --app be dc ar --level standard

# 빠른 코드 검증 (정적만)
python run_static_certification.py --app bom_exporter

# EXE 패키지 인증
python run_certification.py --exe --level full
```

pytest 단위 테스트:
```powershell
cd D:\drive_files\10.worksfree\10.rpa
pytest 90.tests/ -v
```

## 아키텍처 핵심 패턴

### 실행 모드 감지
모든 앱이 동일한 `_detect_run_mode()` 사용:
- `dev`: `.py` 직접 실행 (설정 경로 `10.common/config/`)
- `demo`: `WF_RPA_MODE=demo` 환경변수 (설정 경로 `10.common/config/`)
- `release`: exe 실행 (설정 경로 `~/.wf_rpa/`)

### 설정 파일 계층
```
~/.wf_rpa/                      # 사용자 환경 (release)
  wf_rpa_config.json            # 전역: 이메일, HW지문, 등록상태
  {app}/
    policy.json                 # 크레딧 정책
    credit_history.json         # 크레딧 잔고 및 사용 이력
    settings.json               # UI 설정 (geometry, 경로 등)

10.common/config/               # 개발 환경 (dev/demo)
  wf_rpa_config.json
  {app}/policy.json, settings.json, credit_history.json
```

### 앱 파일 구조 (각 앱 공통)
- `ui_main.py` — 메인 GUI + 앱 라이프사이클
- `automation.py` — 핵심 자동화 로직 (Lazy import: 버튼 클릭 시 로드)
- `app_setting_data.py` — 설정 로더 (앱 이름만 다름, 구조 동일)
- `ui_setting.py` — 설정 창 (Toplevel)
- `{app}.spec` — PyInstaller 빌드 설정

### 크레딧 타입
- `trial_credits: -1` → 무료 앱 (차감 없음, 로그는 기록)
- `purchased_credits: -1` → 영구 라이선스
- 양수 → 유료 크레딧 차감

### UI 단축키 (모든 앱 공통)
- `Alt+G`: 현재 창 geometry를 settings.json에 저장
- `Alt+C`: 화면 캡처

### 단일 인스턴스 정책
자사 앱은 한 번에 하나만 실행 가능 (크레딧 통합 관리 정책). Mutex 기반 `_acquire_single_instance()`.

## 기술 스택

- Python 3.13.7 / Tkinter / pywinauto (UIA 백엔드) / pyautogui
- pandas, openpyxl (데이터 처리)
- PyInstaller 6.16.0 / NSIS 3.11 (패키징)
- Google Sheets API (크레딧 동기화, 서비스 계정 키: `10.common/credentials/google-service-account.json`)

## 개발 규칙

- 버전 정보 단일 소스: `ui_main.py`의 `APP_VERSION_FULL` → `ui_setting.py`는 import해서 사용
- PyInstaller: `python -m PyInstaller {app}.spec --noconfirm --log-level=WARN` (빌드 스크립트가 자동 실행)
- `strip=False` (Windows에서 strip 도구 부재)
- 로깅: `from wf_log import get_app_logger; logger = get_app_logger("app_name")`
