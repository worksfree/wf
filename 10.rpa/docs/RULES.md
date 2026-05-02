# WF-RPA 기본 규칙 (Basic Rules)

> **중요**: 이 문서에 정의된 값들은 각 앱에 최적화된 값입니다.
> **절대로 일괄 변경하지 마세요.** 특정 앱 수정 요청 시 해당 앱만 수정하세요.

---

## 🎯 0. 설정값 폴백 체인 (Configuration Fallback Chain)

### ⚠️ 중요: 실행 모드에 따라 다릅니다!

#### **DEV 모드 (개발/디버깅용)**
```
1순위: 10.common/config/{app}/settings.json    ← 우선 사용
        ↓ (설정값 없으면)
2순위: app_setting_data.py                     ← fallback
        ↓ (기본값 없으면)
3순위: ui_main.py 기본값                       ← final fallback
```

**용도**: 개발자가 `python ui_main.py` 직접 실행
**설정 위치**: 프로젝트 내 `10.common/config/`
**변경 시 영향**: 즉시 반영 (코드 수정 없이)

---

#### **DEMO/RELEASE 모드 (배포/사용자 실행)**
```
1순위: ~/.wf_rpa/{app}/settings.json           ← 사용자 설정 우선
        ↓ (설정값 없으면)
2순위: app_setting_data.py                     ← fallback
        ↓ (기본값 없으면)
3순위: ui_main.py 기본값                       ← final fallback
```

**용도**: 사용자가 설치된 앱 실행 (exe 또는 demo 명시)
**설정 위치**: 사용자 홈 `C:\Users\{username}\.wf_rpa\`
**변경 시 영향**: 재실행 시 반영 (사용자 설정 우선)

---

### 📊 모드별 폴백 비교표

| 항목 | DEV 모드 | DEMO/RELEASE 모드 |
|------|---------|------------------|
| **1순위 경로** | `10.common/config/{app}/` | `~/.wf_rpa/{app}/` |
| **2순위 경로** | `app_setting_data.py` | `app_setting_data.py` |
| **3순위 경로** | `ui_main.py` 기본값 | `ui_main.py` 기본값 |
| **실행 방식** | `python ui_main.py` | `exe 또는 WF_RPA_MODE=demo python ui_main.py` |
| **적용 시점** | 즉시 (재실행 불필요) | 재시작 시 |

### 🔧 구현 코드 (ui_main.py 예시)

```python
# 설정값 로드 (폴백 체인 적용)
self.original_window_height = self.ui.get(
    "window_height",  # 1순위: settings.json ui_config.window_height
    getattr(self.config, "window_height", DEFAULT_HEIGHT)  # 2순위: app_setting_data.py의 config
)
# 3순위: DEFAULT_HEIGHT는 ui_main.py에 정의된 기본값
```

---

# Part 1: UI 규칙

## 1.1 메인창 높이 규칙

### 윈도우 크기 설정 (Plan A - Adaptive UI)
| 구분 | window_width | window_height | 앱 |
|------|--------------|---------------|-----|
| 1-input | **580** | **200** | BE, DP, CV, KFN, QR |
| 2-input | **580** | **320** | AR, DC |
| 특수 레이아웃 | **760** | **200** | QR (가로 QR코드 표시) |

> **Plan A 원칙**: 모든 앱이 settings.json의 `ui_config.window_height` 값을 우선 적용합니다.

### 기본 높이 (입력 수 기준)
| 입력 수 | 기본 높이 | 앱 |
|---------|-----------|-----|
| 1개 | **200px** | BE, CV, DP, KFN, QR |
| 2개 | **320px** | AR, DC (다중 입력 필드용) |

### 관리자 모드 확장
```python
expanded_window_height = original_window_height + 300  # 모든 앱 공통
```
| 입력 수 | 정상 모드 | 어드민 모드 (+300px) |
|---------|---------|------------------|
| 1개 | 200px | **500px** |
| 2개 | 320px | **620px** |

### 설정창 크기 (앱별 최적화)
| 앱 | min_width | min_height | 비고 |
|----|-----------|------------|------|
| bom_exporter | 600 | 580 | 항목 7개 |
| dwg_classifier | 660 | 700 (DPI) | 항목 많음 |
| conversion_verifier | - | - | 기본값 |
| dwg_batch_print | 700 | 500 | 항목 5개 |
| attribute_reset | 400 | 250 | 항목 1개 |
| korean_filename_normalizer | 660 | 640 | 기본값 |
| qrcode_generator | 660 | 580 | 항목 5개 |

## 1.2 폰트 규칙

- 모든 폰트 >= Windows 타이틀바 폰트 크기
- `_get_titlebar_font_size()` 함수로 동적 감지
```python
from wf_ui_adaptive import apply_global_fonts  # 언더스코어 없음!
apply_global_fonts(self.master, ui_settings)
```

---

# Part 2: 크레딧 정책

## 2.1 앱별 크레딧 정책

| 앱 | short | trial_credits | credit_per_work | credit_type | 비고 |
|----|-------|---------------|-----------------|-------------|------|
| bom_exporter | BE | 10,000 | 100 | per_file | 유료 |
| dwg_classifier | DC | 5,000 | 50 | per_file | 유료 |
| dwg_batch_print | DBP | 4,000 | 40 | per_file | 유료 |
| attribute_reset | AR | 20,000 | 200 | per_file | 유료 |
| conversion_verifier | CV | -1 | 0 | free | 무료 |
| korean_filename_normalizer | KFN | -1 | 0 | free | 무료 |
| qrcode_generator | QR | -1 | 0 | free | 무료 |

### 크레딧 타입 설명
- `per_file`: 파일당 크레딧 차감
- `standard`: 작업당 크레딧 차감
- `free`: 무료 앱 (trial_credits = -1)

## 2.2 무료(Free) vs 무제한(Unlimited) 구분

> **중요**: 무료와 무제한은 완전히 다른 개념입니다. 혼동하지 마세요.

### 무료 앱 (Free)
- **정의**: `trial_credits = -1`로 배포되는 앱
- **의미**: 유료 판매가 없는 앱, 모든 사용자가 무료로 사용
- **대상 앱**: CV, KFN, QR
- **구현**: 크레딧 차감만 비활성화, 사용량 로깅/동기화는 동일하게 수행

### 무제한 (Unlimited)
- **정의**: `charged_credits = -1`로 설정된 사용자
- **의미**: 영구 라이선스를 구매하여 무제한 사용 권한 획득
- **대상**: 특정 사용자 (영구 라이선스 구매자)
- **구현**: 크레딧 차감은 되지만 잔액 체크를 건너뜀

### 사용량 추적 (공통)
```
무료 앱이든, 무제한 사용자든, 유료 앱이든
모든 앱의 크레딧 사용량은 Google Sheets로 전송됨
→ 사용자 사용 패턴 분석 및 서비스 개선 목적
```

| 구분 | trial_credits | charged_credits | 크레딧 차감 | 사용량 추적 |
|------|---------------|-----------------|-------------|-------------|
| 유료 앱 (체험판) | > 0 | 0 | O | O |
| 유료 앱 (충전) | >= 0 | > 0 | O | O |
| 무료 앱 | -1 | - | X | O |
| 무제한 (영구) | - | -1 | X (건너뜀) | O |

## 2.3 정책 파일 구조

```json
{
  "identity": {
    "app_name": "bom_exporter",
    "short_name": "be",
    "display_name": "Bom Exporter"
  },
  "policy": {
    "icon_text": "BE",
    "description": "BOM 엑셀 저장 자동화 앱",
    "trial_credits": 10000,
    "credit_per_work": 100,
    "credit_type": "per_file"
  }
}
```

## 2.4 정책 파일 위치

- **번들 정책**: `10.common/config/{app_name}/policy.json`
- **사용자 정책**: `~/.wf_rpa/{app_name}/policy.json`
- **우선순위**: 사용자 정책 > 번들 정책 > 하드코딩 기본값

## 2.5 체험판 크레딧 정책

### 체험판 공식

```
trial_credits = credit_per_work × 100
```

모든 유료 앱은 **100건 작업**을 체험할 수 있는 분량의 크레딧을 제공합니다.

### 앱별 체험판 크레딧

| 앱 | 약어 | credit_per_work | trial_credits | 체험 가능 |
|----|------|-----------------|---------------|-----------|
| bom_exporter | BE | 100 | 10,000 | 100건 |
| dwg_classifier | DC | 50 | 5,000 | 100건 |
| dwg_batch_print | DBP | 40 | 4,000 | 100건 |
| attribute_reset | AR | 200 | 20,000 | 100건 |
| conversion_verifier | CV | 0 | -1 | 무제한 (무료) |
| korean_filename_normalizer | KFN | 0 | -1 | 무제한 (무료) |
| qrcode_generator | QR | 0 | -1 | 무제한 (무료) |

> **참고**: `trial_credits = -1`은 무료 앱을 의미합니다.

## 2.6 크레딧 차감 패턴

```python
# 작업 성공 후 크레딧 차감
if self.credit_manager:
    result = self.credit_manager.deduct_credits_by_policy(
        1, f"작업 완료: {file_name}"
    )
    if result.get("success"):
        self.credit_update_callback()  # UI 갱신
    else:
        # 크레딧 부족: 롤백 + 중단
        self.rollback_operation()
        self.credit_shortage_stop = True
```

---

# Part 3: 폴더 네이밍 규칙

## 3.2 설정/리소스 경로 규칙 (모드별)

> **중요**: 사용자 홈(`~/.wf_rpa`)은 **demo/release 모드 또는 exe 실행 시에만** 사용한다.
> dev 모드(소스 실행)는 **항상 소스트리 `10.common/config`**을 사용한다.

### 모드별 경로 기준
| 모드 | 설정/정책 경로 | 로그/리소스 경로 |
|------|----------------|-----------------|
| dev (소스 실행) | `10.common/config/{app}` | 소스트리 앱 폴더 (`{app}/logs`, `{app}/res`) |
| demo/release 또는 exe | `~/.wf_rpa/{app}` | `~/.wf_rpa/{app}/logs`, `~/.wf_rpa/{app}/res` |

### 금지 사항
- dev 모드에서 `~/.wf_rpa`를 사용하지 말 것
- demo/release(exe)에서 소스트리 `10.common/config`을 직접 참조하지 말 것

## 3.1 앱 소스 코드 위치 (중요)

> **경고**: 앱 소스 코드 위치를 잘못 지정하면 빌드 스크립트, 인증 테스트, 경로 탐색이 실패합니다.
> 아래 표를 반드시 확인하세요.

### 30.apps vs 50.data 구분 기준

| 폴더 | 용도 | 특징 |
|------|------|------|
| **30.apps/** | 외부 소프트웨어 자동화 앱 | SolidWorks, AutoCAD 등 연동 |
| **50.data/** | 데이터 처리/변환 앱 | 파일 시스템, 이미지 처리 등 |

### 앱별 소스 코드 위치 (절대 변경 금지)

| 앱 | 약어 | 소스 위치 | 유형 |
|----|------|----------|------|
| bom_exporter | BE | `30.apps/bom_exporter/` | SolidWorks 자동화 |
| dwg_batch_print | DBP | `30.apps/dwg_batch_print/` | AutoCAD 자동화 |
| attribute_reset | AR | `30.apps/attribute_reset/` | SolidWorks 자동화 |
| dwg_classifier | DC | `50.data/dwg_classifier/` | 파일 분류 |
| conversion_verifier | CV | `50.data/conversion_verifier/` | 파일 비교 |
| korean_filename_normalizer | KFN | `50.data/korean_filename_normalizer/` | 파일명 처리 |
| qrcode_generator | QR | `50.data/qrcode_generator/` | 이미지 생성 |

```
프로젝트 루트/
├── 30.apps/                          ← 외부 SW 자동화 앱 (3개)
│   ├── bom_exporter/                 BE
│   ├── dwg_batch_print/              DBP
│   └── attribute_reset/              AR
│
└── 50.data/                          ← 데이터 처리 앱 (4개)
    ├── dwg_classifier/               DC
    ├── conversion_verifier/          CV
    ├── korean_filename_normalizer/   KFN
    └── qrcode_generator/             QR
```

> **주의**: cv, kfn, qr 앱을 30.apps에 생성하지 마세요.
> 빌드 스크립트와 인증 테스트가 50.data 경로를 참조합니다.

## 3.2 런타임 설정 폴더

**모든 앱 폴더명은 소문자 + 언더스코어 형식**

| 앱 | 폴더명 | 런타임 위치 |
|----|--------|------------|
| bom_exporter | `bom_exporter` | `~/.wf_rpa/bom_exporter/` |
| dwg_classifier | `dwg_classifier` | `~/.wf_rpa/dwg_classifier/` |
| dwg_batch_print | `dwg_batch_print` | `~/.wf_rpa/dwg_batch_print/` |
| conversion_verifier | `conversion_verifier` | `~/.wf_rpa/conversion_verifier/` |
| attribute_reset | `attribute_reset` | `~/.wf_rpa/attribute_reset/` |
| korean_filename_normalizer | `korean_filename_normalizer` | `~/.wf_rpa/korean_filename_normalizer/` |
| qrcode_generator | `qrcode_generator` | `~/.wf_rpa/qrcode_generator/` |

## 3.3 금지 패턴

```
# 잘못된 패턴 (사용 금지)
DWG_Batch_Print      # Title Case
Dwg_Classifier       # Mixed Case
BomExporter          # CamelCase
30.apps/qrcode_generator  # 잘못된 위치!

# 올바른 패턴
dwg_batch_print      # 소문자 + 언더스코어
50.data/qrcode_generator  # 올바른 위치
dwg_classifier
bom_exporter
```

## 3.4 policy.json app_name

`identity.app_name`은 반드시 폴더명과 동일하게 소문자로 지정:

```json
{
  "identity": {
    "app_name": "dwg_batch_print",  // 소문자
    "short_name": "dbp",
    "display_name": "DWG Batch Print"  // 표시명은 자유
  }
}
```

---

# Part 4: 공통 개발 규칙

## 4.1 변경 금지 규칙

### 절대 하지 말 것
- **일괄 변경 금지**: 한 앱 수정 요청에 다른 앱까지 수정하지 않음
- **임의 최적화 금지**: validator 경고를 해결하려고 작동하는 코드를 변경하지 않음
- **범용 규칙 적용 금지**: 앱마다 항목 수가 다르므로 동일 값 적용 불가

### 수정 시 확인사항
```
1. 수정 요청된 앱만 수정했는가?
2. 다른 앱 파일을 건드리지 않았는가?
3. 수정 후 해당 앱을 직접 실행하여 확인했는가?
```

## 4.2 검증 방법

### UI 검증
```bash
python 10.common/ui_rules_validator.py --all
```

### 앱별 테스트
```bash
python 30.apps/bom_exporter/ui_main.py  # 직접 실행
```

## 4.3 빌드 규칙

### 빌드 타입 기본값
```
BuildType = 2 (기본값)
```

별도의 지시가 없는 경우, 모든 앱 빌드는 **BuildType 2**로 실행합니다.

| BuildType | 설명 |
|-----------|------|
| 1 | onedir만 생성 |
| **2** | **onedir + zip (기본값)** |
| 3 | onedir + zip + installer |
| 4 | zip만 |
| 5 | installer만 |

### 빌드 명령어 예시
```powershell
# 기본 빌드 (BuildType 2)
powershell -ExecutionPolicy Bypass -File build_bom_exporter.ps1

# BuildType 명시적 지정
powershell -ExecutionPolicy Bypass -File build_bom_exporter.ps1 -BuildType 2
```

### 버저닝 규칙

**버전 형식**: `vX.Y.Z.B` (4자리)
```
v1.0.0.2
 │ │ │ └── 빌드 번호 (B)
 │ │ └──── 패치 버전 (Z)
 │ └────── 마이너 버전 (Y)
 └──────── 메이저 버전 (X)
```

**자동 버전 증가 규칙** (빌드 시 자동 적용):
- 각 자리는 **0~9** 범위만 사용
- 빌드마다 마지막 자리(B) +1 증가
- 9를 초과하면 0으로 리셋하고 앞자리 +1 증가 (자리 올림)

```
예시: 0.7.0.0 시작
0.7.0.0 → 0.7.0.1 → ... → 0.7.0.9 → 0.7.1.0  (B가 9 초과 → Z 증가)
0.7.1.0 → 0.7.1.1 → ... → 0.7.9.9 → 0.8.0.0  (Z가 9 초과 → Y 증가)
0.8.0.0 → ... → 0.9.9.9 → 1.0.0.0            (Y가 9 초과 → X 증가)
```

**규칙 요약**:
| 자리 | 범위 | 증가 조건 | 비고 |
|------|------|----------|------|
| X (메이저) | 0~9 | Y가 9 초과 시 | 0.x = 베타, 1.x = 정식 |
| Y (마이너) | 0~9 | Z가 9 초과 시 | 주요 기능 추가 |
| Z (패치) | 0~9 | B가 9 초과 시 | 버그 수정 |
| B (빌드) | 0~9 | 매 빌드마다 | 자동 증가 |

**초기 버전**: `v0.7.0.0` (새 앱 생성 시 기본값)

**버전 설정 파일 위치**:
- 빌드 시: `10.common/config/{app_name}/settings.json` → `runtime_config.full_version`
- 번들 시: `_internal/.wf_rpa/{app_name}/settings.json` → `runtime_config.full_version`
- 사용자: `~/.wf_rpa/{app_name}/settings.json` → `runtime_config.full_version`

**구현 위치**: 각 앱의 `*.spec` 파일 내 `load_and_increment_version()` 함수

**버전 로딩 우선순위 (ui_main.py 필수 규칙)**:
```python
# ❌ 잘못된 예: 사용자 홈만 확인
settings_file = Path.home() / ".wf_rpa" / "{app_name}" / "settings.json"

# ✅ 올바른 예: 번들 버전 우선, fallback으로 사용자 홈
if getattr(sys, "frozen", False):
    # 1순위: 번들된 설정 (정확한 빌드 버전)
    base_path = Path(sys._MEIPASS) if hasattr(sys, '_MEIPASS') else Path(sys.executable).parent
    settings_file = base_path / ".wf_rpa" / "{app_name}" / "settings.json"
    
    # 2순위: 사용자 홈 (버전이 없을 수 있음 - 사용자 설정만 저장)
    if not settings_file.exists():
        settings_file = Path.home() / ".wf_rpa" / "{app_name}" / "settings.json"
```

> **중요**: 사용자 홈의 settings.json은 사용자 설정만 저장하므로 `full_version`이 없을 수 있습니다.  
> **반드시 번들 버전을 우선**적으로 확인하여 정확한 앱 버전을 표시해야 합니다.

> **주의**: 0.x.x.x 버전은 베타를 의미합니다. 정식 릴리스된 앱은 반드시 1.x.x.x로 시작해야 합니다.

## 4.4 성능 요구사항

### 앱 로딩 시간 (필수)

| 요구 | 기준 | 비고 |
|------|------|------|
| **필수** | < 3초 | 모든 앱이 충족해야 함 |
| **권장** | < 1초 | 사용자 경험 최적화 |

**측정 기준**: 앱 실행부터 UI가 완전히 표시되고 사용 가능한 상태까지

### 로딩 시간 최적화 전략

```python
# 1. 무거운 초기화는 지연 로드 (Lazy Loading)
def _lazy_init_managers(self):
    """UI 표시 후 비동기로 매니저 초기화"""
    threading.Thread(target=_worker, daemon=True).start()

# 2. 조건부 임포트
if FEATURE_NEEDED:
    from heavy_module import HeavyClass
```

### 로딩 시간에 영향을 주는 요소

| 요소 | 영향 | 해결책 |
|------|------|--------|
| 대형 모듈 임포트 | 높음 | 지연 임포트 |
| 네트워크 요청 | 매우 높음 | 비동기 처리 |
| 파일 I/O | 중간 | 캐싱, 비동기 |
| CreditManager 초기화 | 중간 | `recovery_delay_ms`, `policy_delay_ms` 활용 |

## 4.5 서브 윈도우 규칙

### Topmost 상속 (필수)

메인 창이 `topmost`일 때, 모든 서브 윈도우(설정창, 등록창, 다이얼로그)도 `topmost`로 설정해야 합니다.

```python
# 모달 창 생성 패턴 (깜빡임 방지 포함)
dialog = tk.Toplevel(self.master)
dialog.withdraw()  # ⚠️ 깜빡임 방지: geometry 설정 전 숨김

dialog.transient(self.master)  # 부모 창과 연결
dialog.grab_set()  # 모달로 설정 - 절대 제거하지 말 것

# ⚠️ 중요: 메인 창이 topmost이면 서브 창도 topmost
if self.master.attributes("-topmost"):
    dialog.wm_attributes("-topmost", 1)
```

### 중앙 정렬 (필수)

모든 서브 윈도우는 **메인 창 중앙**에 배치해야 합니다.

```python
# 메인 창 중앙에 서브 윈도우 배치
dialog.update_idletasks()
parent_x = self.master.winfo_rootx()
parent_y = self.master.winfo_rooty()
parent_w = self.master.winfo_width()
parent_h = self.master.winfo_height()
dialog_w = dialog.winfo_reqwidth()
dialog_h = dialog.winfo_reqheight()
x = parent_x + (parent_w - dialog_w) // 2
y = parent_y + (parent_h - dialog_h) // 2
dialog.geometry(f"{dialog_w}x{dialog_h}+{x}+{y}")

dialog.deiconify()  # ⚠️ 위치 설정 완료 후 표시
dialog.focus_set()
```

### MessageBox 처리 (필수)

`messagebox`는 `parent=` 파라미터로 중앙 정렬됩니다. 단, 메인 창이 `topmost`일 때는 messagebox가 뒤로 갈 수 있으므로 헬퍼 메서드를 사용합니다.

```python
def _show_messagebox(self, msg_type: str, title: str, message: str, **kwargs):
    """topmost 상태에서도 정상 표시되는 messagebox 헬퍼"""
    try:
        # topmost 일시 해제
        is_topmost = self.master.attributes("-topmost")
        if is_topmost:
            self.master.wm_attributes("-topmost", 0)
            self.master.update_idletasks()

        # messagebox 표시 (parent로 중앙 정렬)
        msg_func = getattr(messagebox, msg_type, messagebox.showinfo)
        result = msg_func(title, message, parent=self.master, **kwargs)

        # topmost 복원
        if is_topmost:
            self.master.wm_attributes("-topmost", 1)
        return result
    except Exception:
        return getattr(messagebox, msg_type)(title, message, **kwargs)
```

### 서브 윈도우 체크리스트

| 항목 | 필수 | 설명 |
|------|------|------|
| `withdraw()` | ✅ | 생성 직후 숨김 (깜빡임 방지) |
| `transient(parent)` | ✅ | 부모 창과 연결 |
| `grab_set()` | ✅ | 모달로 설정 |
| topmost 상속 | ✅ | 부모가 topmost면 자식도 topmost |
| 중앙 정렬 | ✅ | 부모 창 중앙에 배치 |
| `deiconify()` | ✅ | geometry 설정 후 표시 |
| `parent=` (messagebox) | ✅ | messagebox에 parent 전달 |

---

# Part 5: JSON 설정 파일 목록

## 5.1 전역 설정 파일 (모든 앱 공유)

| 파일명 | 위치 | 용도 |
|--------|------|------|
| `wf_rpa_config.json` | `.wf_rpa/` | 사용자 등록정보, 이메일 설정, Google Sheets 설정 |
| `silver-argon-*.json` | `.wf_rpa/` | Google Service Account 인증 자격증명 |

### wf_rpa_config.json 구조
```json
{
  "user_info": {
    "email": "user@example.com",
    "company_name": "회사명",
    "registration_date": "2026-01-01"
  },
  "email_settings": {
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 587
  },
  "google_sheets": {
    "sheet_id_release": "...",
    "sheet_id_dev": "...",
    "credentials_file_release": "worksfree-*.json",
    "credentials_file_dev": "silver-argon-*.json"
  },
  "execution_status": {
    "is_running": false,
    "running_app": null,
    "running_pid": null
  }
}
```

**환경별 Google Sheets 설정:**
- `RELEASE` (배포 환경): `sheet_id_release` + `credentials_file_release` 사용
- `DEV` (개발 환경): `sheet_id_dev` + `credentials_file_dev` 사용

## 5.2 앱별 설정 파일

각 앱의 설정 폴더: `.wf_rpa/{app_name}/`

| 파일명 | 용도 | 생성 시점 | 수정 |
|--------|------|----------|------|
| `settings.json` | 앱 런타임 설정, UI 레이아웃, 사용자 환경설정 | 빌드 시 번들 | O |
| `policy.json` | 앱 ID, 크레딧 정책 (불변) | 빌드 시 번들 | X |
| `credit_history.json` | 크레딧 잔액 및 사용 기록 | 최초 실행 시 자동 생성 | 자동 |

### settings.json 구조
```json
{
  "runtime_config": {
    "run_mode": "release",        // dev, demo, release
    "full_version": "v0.8.5.5",
    "build_count": 155,
    "ui_scale": 1.0,
    "language": "ko",
    "last_updated": "2026-01-25 00:00:00"
  },
  "ui_config": {
    "topmost": true,
    "window_geometry_override": "",
    "last_selected_folder": ""
  },
  "logging_config": {
    "log_level": "INFO",
    "max_log_size_mb": 10,
    "rotate_logs": true
  }
}
```

### policy.json 구조
```json
{
  "identity": {
    "app_name": "bom_exporter",
    "short_name": "be",
    "display_name": "Bom Exporter"
  },
  "policy": {
    "icon_text": "BE",
    "description": "BOM 엑셀 저장 자동화 앱",
    "trial_credits": 10000,
    "credit_per_work": 100,
    "credit_type": "per_file"
  }
}
```

## 5.3 앱별 설정 파일 현황

| 앱 | settings.json | policy.json | credit_history.json |
|----|---------------|-------------|---------------------|
| bom_exporter | 번들 | 번들 | 자동생성 |
| dwg_classifier | 번들 | 번들 | 자동생성 |
| dwg_batch_print | 번들 | 번들 | 자동생성 |
| attribute_reset | 번들 | 번들 | 자동생성 |
| conversion_verifier | 번들 | 번들 | 자동생성 |
| korean_filename_normalizer | 번들 | 번들 | 자동생성 |
| qrcode_generator | 번들 | 번들 | 자동생성 |

> **참고**: `credit_history.json`은 앱 최초 실행 시 `CreditManager`가 자동 생성.
> 무료/유료 관계없이 모든 앱에서 사용량 로깅 및 Google Sheets 동기화 수행.

---

# Part 6: 개발 환경 vs 배포 환경

## 6.1 환경 감지 로직

```python
# wf_credit_manager.py
def is_development_mode():
    if getattr(sys, "frozen", False):
        return False  # PyInstaller 실행파일
    if sys.argv[0].endswith(".py"):
        return True   # Python 스크립트 실행
    if os.environ.get("WF_RPA_DEV") == "1":
        return True   # 환경변수 설정
    return False
```

## 6.2 설정 파일 경로 차이

### 개발 환경 (Development)
```
프로젝트 루트/
├── 10.common/
│   └── config/                           ← 설정 파일 위치
│       ├── wf_rpa_config.json
│       ├── silver-argon-*.json
│       ├── bom_exporter/
│       │   ├── settings.json
│       │   └── policy.json
│       └── [다른 앱들...]
└── 30.apps/
    └── bom_exporter/
        └── ui_main.py                    ← 실행 위치
```

**경로 탐색 로직**:
1. 실행 위치에서 상위 5단계까지 `10.common/config/` 탐색
2. 없으면 `~/.wf_rpa/` (사용자 홈) 사용

### 배포 환경 (Deployment)
```
설치 폴더/
├── bom_exporter.exe                      ← 실행 파일
└── _internal/
    ├── .wf_rpa/                          ← 번들된 설정 (읽기 전용)
    │   ├── wf_rpa_config.json
    │   ├── silver-argon-*.json
    │   └── bom_exporter/
    │       ├── settings.json
    │       └── policy.json
    └── [기타 의존성...]

사용자 홈/
└── .wf_rpa/                              ← 실제 사용되는 설정
    ├── wf_rpa_config.json
    ├── silver-argon-*.json
    └── bom_exporter/
        ├── settings.json
        └── policy.json
```

**경로 탐색 로직**:
1. 항상 `~/.wf_rpa/` (사용자 홈) 사용
2. `_internal/.wf_rpa/`는 초기 복사 원본으로만 사용

## 6.3 환경별 동작 차이

| 항목 | 개발 환경 | 배포 환경 |
|------|----------|----------|
| **설정 경로** | `10.common/config/` 또는 `~/.wf_rpa/` | `~/.wf_rpa/` (항상) |
| **감지 방법** | `.py` 실행 또는 `WF_RPA_DEV=1` | `sys.frozen == True` |
| **폴더 숨김** | X (개발 시 보이게) | O (Windows 숨김 속성) |
| **레지스트리** | X (미사용) | O (NSIS 설치 시 작성) |
| **바로가기** | X (미생성) | O (바탕화면+시작메뉴) |
| **버전 주입** | 런타임 읽기 | 빌드 시 주입 |
| **로그 위치** | `~/.wf_rpa/{app}/logs/` | 동일 (숨김 폴더 내) |

## 6.4 PyInstaller 번들링 구조

### spec 파일의 datas 설정
```python
def collect_essential_resources():
    return [
        # 전역 설정
        (str(wf_rpa_config), ".wf_rpa/"),
        (str(credentials_file), ".wf_rpa/"),
        # 앱별 설정
        (str(settings_file), f".wf_rpa/{APP_NAME}/"),
        (str(policy_file), f".wf_rpa/{APP_NAME}/"),
        # 공통 모듈
        (str(wf_log_path), "."),
        (str(wf_credit_manager_path), "."),
        # 리소스
        (str(manual_pdf), "."),
    ]
```

### 빌드 시 버전 주입
```python
# spec 파일에서 빌드 시 실행됨
settings_data["runtime_config"]["full_version"] = f"v{APP_VERSION}"
settings_data["runtime_config"]["build_count"] = BUILD_COUNT
```

## 6.5 환경변수 목록

| 환경변수 | 용도 | 값 |
|----------|------|-----|
| `WF_RPA_DEV` | 강제 개발 모드 활성화 | `1` |
| `WF_RPA_HOME` | 설정 폴더 경로 재지정 | 경로 |
| `WF_EXTERNAL_PACKAGER` | 외부 빌드 도구 사용 표시 | `1` |
| `WF_SKIP_INSTALLER` | NSIS 인스톨러 생성 건너뛰기 | `1` |
| `WF_BUILD_INSTALLER` | NSIS 인스톨러 강제 생성 | `1` |

---

# Part 7: 표준화 이슈 및 방안

## 7.1 현재 표준화된 항목

| 항목 | 표준 | 적용 상태 |
|------|------|----------|
| spec 함수명 | `collect_essential_resources()` | 완료 |
| 앱 폴더명 | 소문자_언더스코어 | 완료 |
| policy.json app_name | 폴더명과 동일 | 완료 |
| 빌드 스크립트 | `build_{app_name}.ps1` | 완료 |
| 매뉴얼 포함 | `*_USER_MANUAL.pdf` | 완료 |

## 7.2 미표준화 이슈

### 이슈 #1: 앱 소스 위치 혼재
```
현재:
├── 30.apps/           ← 유료 앱 (BE, AR, DBP)
│   ├── bom_exporter/
│   ├── attribute_reset/
│   └── dwg_batch_print/
└── 50.data/           ← 무료 앱 + 일부 유료
    ├── conversion_verifier/    (무료)
    ├── dwg_classifier/         (유료!)
    ├── korean_filename_normalizer/  (무료)
    └── qrcode_generator/       (무료)
```
**문제**: `dwg_classifier`는 유료인데 `50.data`에 위치
**권장**: 현재 상태 유지 (이동 시 참조 경로 변경 리스크)

### 이슈 #2: 자격증명 파일 탐색 순서 불일치
```python
# wf_googlesheets_manager.py - 현재 탐색 순서
1. 10.common/config/         (개발)
2. config/                    (앱 폴더)
3. _internal/.wf_rpa/        (번들)
4. ~/.wf_rpa/                 (사용자 홈)

# wf_credit_manager.py - 현재 탐색 순서
1. ~/.wf_rpa/                 (사용자 홈)
2. _internal/.wf_rpa/        (번들)
```
**표준화 방안**: 배포 환경에서는 `~/.wf_rpa/` 우선으로 통일

### ~~이슈 #3: credit_history.json~~ (해결됨)

`credit_history.json`은 앱 최초 실행 시 `CreditManager._initialize_credits()`가 자동 생성.
소스 코드에 포함되지 않으며, 런타임에 `~/.wf_rpa/{app_name}/` 경로에 생성됨.

| 구분 | 크레딧 차감 | 사용량 로깅 | Google Sheets 동기화 |
|------|------------|-----------|---------------------|
| 유료 앱 | O | O | O |
| 무료 앱 | X | O | O |

### 이슈 #4: run_mode 값 불일치
```
현재 사용되는 값들:
- "dev"      : 개발 모드
- "demo"     : 데모 모드
- "release"  : 배포 모드
```
| 앱 | settings.json run_mode |
|----|------------------------|
| bom_exporter | release |
| dwg_classifier | demo |
| conversion_verifier | demo |
| attribute_reset | release |
| korean_filename_normalizer | demo |
| qrcode_generator | dev |

**표준화 방안**:
- `dev`: 개발 중 (로컬 테스트)
- `demo`: 체험판 배포
- `release`: 정식 배포

## 7.3 표준 참조 코드 위치

| 기능 | 파일 | 라인 |
|------|------|------|
| 환경 감지 | `wf_credit_manager.py` | 136-189 |
| 경로 해석 | `wf_credit_manager.py` | 156-188 |
| 자격증명 탐색 | `wf_googlesheets_manager.py` | 87-200 |
| 버전 관리 | `*_exporter.spec` | 24-80 |
| 번들링 로직 | `*_exporter.spec` | `collect_essential_resources()` |

---

# Part 8: 터미널 한글 인코딩

## 8.1 문제 현상

Windows 터미널에서 한글이 깨지는 현상:
```
[OK] ���� ����: wf-rpa-users@worksfree.iam.gserviceaccount.com
[OK] 테스트 완료  (정상)
```

## 8.2 PowerShell 설정

### 세션 시작 시 설정 (필수)
```powershell
# UTF-8 출력 인코딩 설정
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# 코드 페이지 UTF-8로 변경
chcp 65001
```

### 영구 설정 (PowerShell 프로필)
```powershell
# $PROFILE 파일에 추가 (보통 ~\Documents\PowerShell\Microsoft.PowerShell_profile.ps1)
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
```

## 8.3 Python 인코딩 설정

### 환경변수 설정
```powershell
$env:PYTHONIOENCODING = "utf-8"
```

### Python 스크립트 내부
```python
import sys
import io

# stdout/stderr UTF-8 강제 설정
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
```

### print() 사용 시 주의
```python
# 잘못된 방법 (인코딩 에러 가능)
print("한글 메시지")

# 안전한 방법 (에러 대체)
print("한글 메시지".encode('utf-8', errors='replace').decode('utf-8'))

# 또는 flush 추가
print("한글 메시지", flush=True)
```

## 8.4 빌드 스크립트 표준 헤더

모든 `build_*.ps1` 스크립트 시작 부분에 추가:
```powershell
# === Korean Encoding Fix ===
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
chcp 65001 | Out-Null
# ===========================
```

## 8.5 subprocess 호출 시 인코딩

```python
import subprocess

# 잘못된 방법
result = subprocess.run(["python", "script.py"], capture_output=True)

# 올바른 방법
result = subprocess.run(
    ["python", "script.py"],
    capture_output=True,
    encoding='utf-8',
    errors='replace'
)
```

## 8.6 로깅 설정

```python
import logging

# 파일 핸들러에 UTF-8 인코딩 명시
file_handler = logging.FileHandler(
    'app.log',
    encoding='utf-8',
    errors='replace'
)
```

## 8.7 체크리스트

새 스크립트 작성 시 확인사항:

| 항목 | 설정 |
|------|------|
| PowerShell 스크립트 | `$OutputEncoding = [System.Text.Encoding]::UTF8` |
| Python 환경변수 | `PYTHONIOENCODING=utf-8` |
| subprocess 호출 | `encoding='utf-8', errors='replace'` |
| 파일 I/O | `encoding='utf-8'` 명시 |
| 로그 파일 | `encoding='utf-8'` 핸들러 |

## 8.8 VSCode 터미널 설정

`settings.json`에 추가:
```json
{
    "terminal.integrated.defaultProfile.windows": "PowerShell",
    "terminal.integrated.profiles.windows": {
        "PowerShell": {
            "source": "PowerShell",
            "args": ["-NoExit", "-Command", "$OutputEncoding = [System.Text.Encoding]::UTF8; [Console]::OutputEncoding = [System.Text.Encoding]::UTF8; chcp 65001"]
        }
    }
}
```

---

# Part 9: 수정 이력

| 날짜 | 대상 | 변경 내용 | 이유 |
|------|------|----------|------|
| 2026-01-26 | UI | 기본 높이: 160(1입력), 270(2입력) | 여백 최적화 |
| 2026-01-26 | UI | 관리자 모드 확장: +300 고정 | 로그 영역 일관성 |
| 2026-01-26 | 문서 | UI_RULES.md + 크레딧 정책 → BASIC_RULES.md 통합 | 관리 단순화 |
| 2026-01-26 | 폴더 | 앱 폴더명 소문자 통일 (DWG_Batch_Print → dwg_batch_print) | 일관성 |
| 2026-01-26 | 정책 | QR Code Generator 무료 앱으로 변경 | 무료 배포 |
| 2026-01-26 | 문서 | 무료(Free) vs 무제한(Unlimited) 구분 명시 | 개념 혼동 방지 |
| 2026-01-26 | 문서 | JSON 파일 목록, 개발/배포 환경 차이 추가 | 환경 이해 |
| 2026-01-26 | 문서 | 표준화 이슈 및 방안 정리 | 일관성 개선 |
| 2026-01-26 | 문서 | Part 8: 터미널 한글 인코딩 가이드 추가 | 인코딩 문제 방지 |
| 2026-01-26 | 성능 | Part 4.3: 앱 로딩 시간 요구사항 추가 (<3초 필수, <1초 권장) | 사용자 경험 |
| 2026-01-27 | 정책 | Part 2.5: 체험판 크레딧 공식 추가 (trial = credit_per_work × 100) | 정책 명확화 |
| 2026-01-27 | 폴더 | Part 3.1: 앱 소스 코드 위치 명시 (30.apps vs 50.data) | 경로 혼동 방지 |

---

# Part 10: 핵심 원칙

> **"작동하는 코드는 건드리지 마라"**
>
> 특정 앱의 문제를 수정할 때, 그 앱만 수정한다.
> validator 경고는 참고용이며, 실제 앱이 정상이면 무시한다.

> **"개발과 배포 환경을 구분하라"**
>
> 개발 환경: `10.common/config/` 직접 수정
> 배포 환경: `~/.wf_rpa/` 사용자 폴더에 설정 저장
> 동일한 코드가 두 환경에서 올바르게 동작해야 한다.
