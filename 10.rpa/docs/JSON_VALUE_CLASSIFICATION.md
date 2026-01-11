# JSON 값 분류 및 배포 패키징 가이드

## 📊 JSON 파일 개요

WorksFree RPA 시스템은 3가지 주요 JSON 파일로 구성됩니다:

### 1. `policy.json` (앱별 정책)
**위치**: `~/.wf_rpa/{app_name}/policy.json`  
**번들 위치**: `_internal/.wf_rpa/{app_name}/policy.json`  
**특성**: ✅ **불변** - 설치 후 변경되지 않음

### 2. `settings.json` (앱별 런타임 설정)
**위치**: `~/.wf_rpa/{app_name}/settings.json`  
**번들 위치**: `_internal/.wf_rpa/{app_name}/settings.json`  
**특성**: 🔄 **가변** - 실행 중 변경됨

### 3. `credit_history.json` (앱별 크레딧 이력)
**위치**: `~/.wf_rpa/{app_name}/credit_history.json`  
**번들 위치**: ❌ 번들 안됨  
**특성**: 🔄 **가변** - 사용자 등록/사용 시 생성됨

---

## 📋 값 분류 매트릭스

### 🔵 policy.json - 앱 신원 및 정책 (불변)

#### ✅ **배포 필수 - 변하지 않는 값**

| 키 경로 | 값 예시 | 설명 | 초기화 필요 |
|---------|---------|------|------------|
| `identity.app_name` | `"bom_exporter"` | 앱 내부 식별자 | ❌ |
| `identity.short_name` | `"be"` | 앱 단축명 | ❌ |
| `identity.display_name` | `"BOM Exporter"` | 사용자 표시명 | ❌ |
| `policy.icon_text` | `"B2E"` | 아이콘 텍스트 | ❌ |
| `policy.description` | `"도면 처리 앱"` | 앱 설명 | ❌ |
| `policy.trial_credits` | `10000` | **체험판 크레딧** | ❌ |
| `policy.credit_per_work` | `100` | **작업당 크레딧** | ❌ |
| `policy.credit_type` | `"per_file"` | 크레딧 차감 방식 | ❌ |

#### 📦 **배포 전략**:
```python
# spec 파일에서 그대로 복사 (수정 안함)
shutil.copy2(policy_src, bundled_policy)
```

**중요**: `policy.json`에는 버전 정보나 빌드 카운트를 **추가하지 않음**. 순수하게 identity + policy만 포함.

---

### 🟢 settings.json - 런타임 설정 (가변)

#### 🔄 **배포 필수 - 초기값 설정 필요**

##### **A. solidworks 섹션** (환경별 기본값)

| 키 경로 | 값 예시 | 설명 | 배포시 처리 |
|---------|---------|------|------------|
| `solidworks.program_path` | `"C:\\Program Files\\SOLIDWORKS Corp\\SOLIDWORKS\\SLDWORKS.exe"` | SW 실행 경로 | ✅ 기본값 포함 |

##### **B. runtime_config 섹션** (앱 동작 설정)

| 키 경로 | 값 예시 | 설명 | 변경 여부 | 배포시 처리 |
|---------|---------|------|----------|------------|
| `runtime_config.run_mode` | `"release"` | 실행 모드 | 🔄 개발자 변경 | ✅ "release" 고정 |
| `runtime_config.restart_count` | `20` | 재시작 횟수 | 🔄 정책 동기화 | ✅ 기본값 포함 |
| `runtime_config.topmost` | `true` | 최상위 창 | 🔄 사용자 설정 | ✅ 기본값 포함 |
| `runtime_config.auto_restart` | `true` | 자동 재시작 | 🔄 정책 동기화 | ✅ 기본값 포함 |
| `runtime_config.speed_mode` | `"normal"` | 속도 모드 | 🔄 사용자 설정 | ✅ 기본값 포함 |
| `runtime_config.base_wait_time` | `60` | 기본 대기시간 | 🔄 정책 동기화 | ✅ 기본값 포함 |
| `runtime_config.seconds_per_10mb` | `60` | 10MB당 초 | 🔄 정책 동기화 | ✅ 기본값 포함 |
| `runtime_config.include_thumbnail` | `true` | 썸네일 포함 | 🔄 사용자 설정 | ✅ 기본값 포함 |
| `runtime_config.ui_scale` | `1.0` | UI 배율 | 🔄 사용자 설정 | ✅ 기본값 포함 |
| `runtime_config.full_version` | `"v0.9.1.2"` | **빌드 버전** | 🔄 빌드마다 | ✅ 빌드 시 주입 |
| `runtime_config.build_count` | `212` | **빌드 횟수** | 🔄 빌드마다 | ✅ 빌드 시 주입 |
| `runtime_config.last_updated` | `"2026-01-05 21:17:43"` | 마지막 업데이트 | 🔄 저장시마다 | ✅ 빌드 시 주입 |

##### **C. ui_config 섹션** (사용자 UI 설정)

| 키 경로 | 값 예시 | 설명 | 변경 여부 | 배포시 처리 |
|---------|---------|------|----------|------------|
| `ui_config.last_selected_folder` | `"D:/test"` | 마지막 선택 폴더 | 🔄 사용시마다 | ⚠️ 빈 문자열로 초기화 |
| `ui_config.window_geometry_override` | `"719x241+2521+212"` | 창 위치/크기 | 🔄 사용시마다 | ⚠️ 빈 문자열로 초기화 |

#### 📦 **배포 전략**:
```python
# 1. settings.json 로드
with open(settings_src, "r", encoding="utf-8") as f:
    settings_data = json.load(f)

# 2. 버전 정보 주입 (runtime_config에만)
settings_data["runtime_config"]["full_version"] = f"v{APP_VERSION_FULL}"
settings_data["runtime_config"]["build_count"] = VERSION_INFO["build_count"]
settings_data["runtime_config"]["last_updated"] = datetime.now().isoformat()

# 3. 사용자 경로 초기화
settings_data["ui_config"]["last_selected_folder"] = ""
settings_data["ui_config"]["window_geometry_override"] = ""

# 4. 저장
with open(bundled_settings, "w", encoding="utf-8") as f:
    json.dump(settings_data, f, ensure_ascii=False, indent=2)
```

---

### 🟡 credit_history.json - 크레딧 사용 이력 (사용자별 생성)

#### ⚠️ **배포 제외 - 런타임 생성**

| 키 경로 | 값 예시 | 설명 | 초기화 필요 |
|---------|---------|------|------------|
| `user_email` | `"user@example.com"` | 사용자 이메일 | ✅ 사용자 등록시 |
| `hardware_fingerprint` | `"ABC123..."` | **하드웨어 지문** | ✅ 매번 새로 생성 |
| `cpu_id` | `"BFEBFBFF..."` | **CPU ID** | ✅ 매번 새로 생성 |
| `mainboard_id` | `"BASE123..."` | **메인보드 ID** | ✅ 매번 새로 생성 |
| `trial_credits_remaining` | `9500` | 남은 크레딧 | 🔄 사용시마다 |
| `used_credits` | `500` | 사용한 크레딧 | 🔄 사용시마다 |
| `registration_date` | `"2026-01-05T10:30:00"` | 등록 일시 | ✅ 사용자 등록시 |
| `license_type` | `"trial"` | 라이센스 타입 | 🔄 구매시 변경 |
| `history` | `[{...}]` | 사용 이력 | 🔄 사용시마다 추가 |

#### 📦 **배포 전략**:
```python
# credit_history.json은 번들에 포함하지 않음
# 사용자가 처음 등록할 때 wf_credit_manager.py가 자동 생성
```

**중요**: 
- ❌ 번들에 포함하면 안됨
- ❌ 템플릿 파일도 필요 없음
- ✅ `wf_credit_manager.py`의 `_init_credit_history()`가 자동 생성

---

## 🔐 보안 및 초기화 체크리스트

### ✅ **배포 시 반드시 포함해야 하는 값**

1. **policy.json** (전체 파일 - 수정 없이 복사)
   - ✅ `trial_credits: 10000` - **체험판 크레딧**
   - ✅ `credit_per_work: 100` - **작업당 크레딧**
   - ✅ `credit_type: "per_file"` - 크레딧 방식

2. **settings.json**
   - ✅ `runtime_config.full_version` - 빌드 시 주입
   - ✅ `runtime_config.build_count` - 빌드 시 주입
   - ✅ `runtime_config.run_mode: "release"` - 고정값

### ⚠️ **배포 시 반드시 초기화해야 하는 값**

1. **settings.json**
   - ⚠️ `ui_config.last_selected_folder: ""` - 빈 문자열
   - ⚠️ `ui_config.window_geometry_override: ""` - 빈 문자열

2. **credit_history.json**
   - ❌ 파일 자체를 포함하지 않음 (자동 생성됨)
   - ⚠️ 만약 실수로 포함되었다면:
     - `hardware_fingerprint` 삭제 필수
     - `cpu_id` 삭제 필수
     - `mainboard_id` 삭제 필수
     - `user_email` 삭제 필수

### 🚫 **배포 시 절대 포함하면 안되는 값**

1. **개발자 환경 경로**
   - ❌ `ui_config.last_selected_folder: "D:/개발자경로/..."`
   - ❌ `ui_config.window_geometry_override: "개발PC위치"`

2. **하드웨어 정보**
   - ❌ `cpu_id: "개발PC_CPU"`
   - ❌ `mainboard_id: "개발PC_MB"`
   - ❌ `hardware_fingerprint: "개발PC_지문"`

3. **사용자 정보**
   - ❌ `user_email: "개발자@email.com"`
   - ❌ `used_credits: 500` (사용 이력)

---

## 🔍 배포 패키징 검증 방법

### 1. **policy.json 검증**
```python
# 체크리스트:
# ✅ identity 섹션 존재
# ✅ policy 섹션 존재
# ✅ trial_credits = 10000
# ✅ credit_per_work = 100
# ❌ app_config 섹션 없음
# ❌ build_count 없음
# ❌ last_updated 없음
```

### 2. **settings.json 검증**
```python
# 체크리스트:
# ✅ runtime_config 섹션 존재
# ✅ runtime_config.full_version = "v{빌드버전}"
# ✅ runtime_config.build_count = {빌드번호}
# ✅ runtime_config.run_mode = "release"
# ✅ ui_config.last_selected_folder = ""
# ✅ ui_config.window_geometry_override = ""
# ❌ app_info 섹션 없음
# ❌ app_config 섹션 없음 (runtime_config로 변경됨)
```

### 3. **credit_history.json 검증**
```python
# 체크리스트:
# ❌ 번들에 파일 없음
# ❌ _internal/.wf_rpa/{app}/credit_history.json 없음
```

### 4. **번들 파일 구조 확인**
```
dist/bom_exporter/
└── _internal/
    └── .wf_rpa/
        ├── wf_rpa_config.json (전역 설정)
        ├── .silver-argon-*.json (Google 인증)
        └── bom_exporter/
            ├── policy.json ✅ (identity + policy만)
            ├── settings.json ✅ (버전 주입됨, 경로 초기화됨)
            └── credit_history.json ❌ (없어야 정상)
```

---

## 🛠️ 자동 검증 스크립트

```python
# 배포 전 검증 (spec 파일에 추가 가능)
def verify_bundle_integrity(bundle_dir):
    """배포 번들의 JSON 파일 무결성 검증"""
    wf_rpa = bundle_dir / "_internal" / ".wf_rpa"
    app_name = "bom_exporter"  # 앱별 변경
    
    # 1. policy.json 검증
    policy = wf_rpa / app_name / "policy.json"
    assert policy.exists(), "❌ policy.json 없음"
    with open(policy) as f:
        data = json.load(f)
    assert "identity" in data, "❌ identity 섹션 없음"
    assert "policy" in data, "❌ policy 섹션 없음"
    assert data["policy"]["trial_credits"] == 10000, "❌ trial_credits 불일치"
    assert "app_config" not in data, "❌ policy.json에 app_config 있음"
    print("✅ policy.json 검증 통과")
    
    # 2. settings.json 검증
    settings = wf_rpa / app_name / "settings.json"
    assert settings.exists(), "❌ settings.json 없음"
    with open(settings) as f:
        data = json.load(f)
    assert "runtime_config" in data, "❌ runtime_config 없음"
    assert data["runtime_config"]["run_mode"] == "release", "❌ run_mode != release"
    assert data["ui_config"]["last_selected_folder"] == "", "❌ 경로 초기화 안됨"
    assert "app_info" not in data, "❌ app_info 섹션 있음"
    assert "app_config" not in data, "❌ app_config 섹션 있음"
    print("✅ settings.json 검증 통과")
    
    # 3. credit_history.json 검증
    credit = wf_rpa / app_name / "credit_history.json"
    assert not credit.exists(), "❌ credit_history.json이 번들에 있음"
    print("✅ credit_history.json 미포함 확인")
    
    print("\n🎉 배포 번들 검증 완료!")
```

---

## 📝 요약

### 불변 값 (배포 필수, 수정 안함)
- **policy.json**: 전체 (identity + policy)
- **settings.json**: solidworks, runtime_config 기본값

### 가변 값 (배포 필수, 초기값 설정)
- **settings.json**: full_version, build_count, last_updated (빌드 시 주입)
- **settings.json**: ui_config (빈 문자열로 초기화)

### 사용자별 값 (배포 제외, 런타임 생성)
- **credit_history.json**: 전체 파일
- 하드웨어 지문, CPU ID, 메인보드 ID는 사용자 등록 시 자동 생성

### 배포 체크리스트
- ✅ policy.json - 그대로 복사
- ✅ settings.json - 버전 주입 + 경로 초기화
- ❌ credit_history.json - 포함 금지
- ✅ 전역 설정 (wf_rpa_config.json, Google credentials)
