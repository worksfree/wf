# 설정 파일 경로 정책

## 개요

WorksFree RPA 앱들은 **실행 환경**과 **실행 모드**에 따라 다른 설정 파일 경로를 사용합니다.

## 실행 환경

| 환경 | 설명 | 감지 방법 |
|------|------|----------|
| **소스** | Python 소스 코드로 직접 실행 | `sys.frozen == False` |
| **exe** | PyInstaller로 빌드된 실행 파일 | `sys.frozen == True` |

## 실행 모드

| 모드 | 용도 | 설정 위치 (소스) | 설정 위치 (exe) | 특징 |
|------|------|-----------------|-----------------|------|
| **dev** | 개발 환경 | `소스트리/config/앱이름/` | N/A | 로컬 파일 직접 수정 |
| **demo** | 데모/영상 녹화 | `~/.wf_rpa/앱이름/` | `~/.wf_rpa/앱이름/` | 데이터 격리, 재사용 가능 |
| **release** | 일반 배포 | `~/.wf_rpa/앱이름/` | `~/.wf_rpa/앱이름/` | 사용자별 독립 설정 |

실행 모드는 `settings.json`의 `runtime_config.run_mode` 값으로 결정됩니다.

## 설정 파일 경로 결정 로직

```python
import sys
from pathlib import Path

run_mode = _detect_run_mode()  # settings.json에서 읽음

if run_mode == "dev":
    # dev 모드: 항상 소스 트리 사용
    app_config_dir = Path(__file__).parent / "config" / "앱이름"
else:
    # demo/release 모드: 항상 사용자 홈 사용
    app_config_dir = Path.home() / ".wf_rpa" / "앱이름"
```

## 동작 매트릭스

| 실행 방식 | run_mode | 설정 파일 경로 | 쓰기 가능 |
|-----------|----------|---------------|----------|
| **python (소스)** | dev | `소스트리/config/앱이름/settings.json` | ✅ |
| **python (소스)** | demo | `~/.wf_rpa/앱이름/settings.json` | ✅ |
| **python (소스)** | release | `~/.wf_rpa/앱이름/settings.json` | ✅ |
| **exe** | dev | N/A (불가능) | N/A |
| **exe** | demo | `~/.wf_rpa/앱이름/settings.json` | ✅ |
| **exe** | release | `~/.wf_rpa/앱이름/settings.json` | ✅ |

## exe 빌드 시 초기 설정 복사 메커니즘

### 문제점
- exe로 빌드된 앱은 번들된 `config/` 폴더가 읽기 전용
- Alt+G로 창 위치 저장, 폴더 경로 저장 등 쓰기 작업 불가

### 해결책
**첫 실행 시 번들 설정 → 사용자 홈으로 복사**

```python
def _ensure_settings_file(self):
    """exe 첫 실행 시 번들된 설정을 사용자 홈으로 복사"""
    if not self.settings_file.exists():
        is_frozen = getattr(sys, 'frozen', False)
        if is_frozen:
            bundled = Path(self.base_dir) / "config" / "앱이름" / "settings.json"
            if bundled.exists():
                shutil.copy2(bundled, self.settings_file)
                return
        
        # 번들 파일 없으면 기본값으로 생성
        unified_settings = {...}
        with open(self.settings_file, "w") as f:
            json.dump(unified_settings, f)
```

### 동작 흐름

1. **exe 첫 실행**:
   - `~/.wf_rpa/앱이름/settings.json` 없음
   - 번들된 `config/앱이름/settings.json` 발견
   - 사용자 홈으로 복사 (demo 설정 포함)

2. **이후 실행**:
   - 사용자 홈의 `settings.json` 사용
   - Alt+G 등으로 수정된 내용 유지

3. **업데이트 설치**:
   - 기존 `~/.wf_rpa/` 파일은 보존
   - 새 버전 번들 파일은 무시됨
   - **주의**: 설정 구조 변경 시 마이그레이션 로직 필요

## demo 모드 exe의 특수성

### demo 모드로 빌드하는 이유
- 영상 녹화용 화면 캡처 기능 (Alt+C, Alt+G)
- 데모 지연 효과 (우클릭 후 3초 sleep 등)
- 미리 설정된 창 위치, 폴더 경로

### exe demo의 동작
```
소스 demo 실행:
  config/bom_exporter/settings.json (직접 읽기/쓰기)
  ↓
  Alt+G → 즉시 settings.json 수정

exe demo 실행:
  config/bom_exporter/settings.json (번들, 읽기 전용)
  ↓ 첫 실행 시 복사
  ~/.wf_rpa/bom_exporter/settings.json (쓰기 가능)
  ↓
  Alt+G → 사용자 홈 settings.json 수정
```

### 장점
1. **demo 설정 활용**: 번들된 geometry, 폴더 경로 초기값 사용
2. **쓰기 가능**: Alt+G로 창 위치 저장 가능
3. **사용자별 독립**: 다른 사용자가 실행해도 간섭 없음

### 단점
1. **업데이트 미반영**: 업데이트된 demo 설정이 자동 적용 안됨
2. **혼동 가능성**: run_mode=demo인데 경로는 release와 동일

## 모범 사례

### 개발 중
```bash
# 소스에서 직접 실행
python bom_exporter.py
# → config/bom_exporter/settings.json (dev/demo)
```

### 영상 녹화
```bash
# 1. settings.json run_mode=demo 설정
# 2. 소스에서 실행 (번들 불필요)
python bom_exporter.py
# → config/bom_exporter/settings.json 직접 사용
# → Alt+G로 즉시 저장
```

### 배포
```bash
# 1. settings.json run_mode=demo (or release)
# 2. exe 빌드
# 3. 첫 실행 시 자동으로 ~/.wf_rpa/로 복사
# 4. 이후 사용자 홈 파일만 수정됨
```

## 주의사항

### 1. 설정 초기화 방법
사용자가 설정을 초기화하려면:
```bash
# Windows
del %USERPROFILE%\.wf_rpa\bom_exporter\settings.json

# 다음 실행 시 번들 설정으로 다시 복사됨
```

### 2. 버전 업데이트 시
```python
# 설정 구조가 변경된 경우 마이그레이션 로직 필요
def _migrate_settings(old_version, new_version):
    if old_version < "0.8.0":
        # 새 필드 추가
        settings["ui_config"]["new_field"] = default_value
```

### 3. 디버깅
로그에서 실제 사용 중인 경로 확인:
```
[CONFIG] run_mode=demo, settings_file=C:\Users\USER\.wf_rpa\bom_exporter\settings.json
```

## 적용 앱 목록

- ✅ bom_exporter (v0.8.8.6+)
- ✅ dwg_classifier (v0.8.3.4+)
- ✅ dwg_batch_print (v0.7.5.x+)
- ✅ korean_filename_normalizer (v0.8.1.6+)
- ✅ conversion_verifier (v0.8.1.2+)

## 관련 파일

- `app_setting_data.py`: 설정 경로 결정 로직
- `settings.json`: 실행 모드 및 사용자 설정
- `build_*.ps1`: exe 빌드 스크립트 (config 번들링)

---
**작성일**: 2026-01-03  
**마지막 수정**: 2026-01-03

---

## 부록 A: JSON 필드 상세 분류

### policy.json - 앱별 정책 (불변)

#### 유지할 값 (배포 시 그대로 복사)

| 필드 | 예시 값 | 설명 | 변경 금지 이유 |
|------|---------|------|---------------|
| identity.app_name | "bom_exporter" | 앱 내부 ID | 앱 식별자 |
| identity.short_name | "be" | 앱 단축명 | 코드에서 사용 |
| identity.display_name | "BOM Exporter" | UI 표시명 | 사용자 표시용 |
| policy.icon_text | "B2E" | 아이콘 텍스트 | UI 아이콘 |
| policy.description | "도면 처리 앱" | 앱 설명 | 메타데이터 |
| policy.trial_credits | 10000 / 50000 / -1 | 체험판 크레딧 | **핵심 비즈니스 정책** |
| policy.credit_per_work | 100 | 작업당 차감 크레딧 | **핵심 비즈니스 정책** |
| policy.credit_type | "per_file" | 크레딧 차감 방식 | 정책 설정 |

### settings.json - 런타임 설정 (가변)

#### runtime_config 섹션 (빌드 시 주입)

| 필드 | 예시 값 | 설명 | 주입 시점 |
|------|---------|------|----------|
| runtime_config.run_mode | "release" | 실행 모드 | spec 파일이 강제로 "release" 설정 |
| runtime_config.full_version | "v0.9.1.2" | 전체 버전 | spec 파일이 빌드 시 주입 |
| runtime_config.build_count | 212 | 빌드 횟수 | spec 파일이 빌드 시 주입 |
| runtime_config.last_updated | "2026-01-05 21:17:43" | 마지막 업데이트 | spec 파일이 빌드 시 주입 |

#### ui_config 섹션 (사용자 경로 초기화)

| 필드 | 초기화 값 | 이유 | 배포 시 처리 |
|------|----------|------|-------------|
| ui_config.last_selected_folder | "" | 개발자 경로 유출 방지 | spec 파일이 빈 문자열로 초기화 |
| ui_config.window_geometry_override | "" | 개발PC 창 위치 유출 방지 | spec 파일이 빈 문자열로 초기화 |

### credit_history.json - 크레딧 이력 (배포 제외)

이 파일은 사용자가 앱을 처음 등록할 때 자동으로 생성됩니다.

**배포 시 처리**:
- ❌ 번들에 포함하지 않음
- ❌ 템플릿 파일도 필요 없음
- ✅ 사용자 등록 시 `wf_credit_manager.py`가 자동 생성

---

## 부록 B: JSON 값 분류 및 배포 전략

### 배포 필수 - 변하지 않는 값

- policy.json: 전체 (identity + policy)
- settings.json: solidworks, runtime_config 기본값

### 배포 필수 - 초기값 설정 필요

- settings.json: full_version, build_count, last_updated (빌드 시 주입)
- settings.json: ui_config (빈 문자열로 초기화)

### 사용자별 값 (배포 제외, 런타임 생성)

- credit_history.json: 전체 파일
- 하드웨어 지문, CPU ID, 메인보드 ID는 사용자 등록 시 자동 생성

### 보안 체크리스트

#### 배포 시 자동 보장되는 사항 (spec 파일)

1. **개발자 정보 유출 방지**
   - ui_config.last_selected_folder: 빈 문자열로 초기화
   - ui_config.window_geometry_override: 빈 문자열로 초기화
   - 앱별 경로 필드: 빈 문자열로 초기화

2. **하드웨어 정보 유출 방지**
   - credit_history.json: 번들에 미포함
   - hardware_fingerprint: 번들에 미포함
   - cpu_id: 번들에 미포함
   - mainboard_id: 번들에 미포함

3. **배포 모드 보장**
   - runtime_config.run_mode: 강제로 "release"
   - 소스가 "demo"여도 배포는 "release"

4. **버전 정보 자동화**
   - runtime_config.full_version: 빌드 시 자동 주입
   - runtime_config.build_count: 빌드 시 자동 증가
   - runtime_config.last_updated: 빌드 시각 자동 기록

---

**마지막 업데이트**: 2026-01-14
