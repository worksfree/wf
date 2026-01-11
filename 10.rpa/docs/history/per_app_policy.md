# 앱별 정책 파일 분산 구조 적용 완료 보고서

## 📋 작업 개요
- **작업일**: 2025-11-09
- **목적**: 전역 `.wf_app_policies.json`을 앱별 `.{app}.app_policy.json`으로 분산하여 독립적 배포 지원
- **영향 범위**: 모든 WorksFree 앱 (bom2excel, conversion_verifier 등)

---

## ✅ 완료된 작업

### 1. 앱별 정책 파일 구조 변경
**이전 구조 (Global)**
```
~/.wf_rpa/
  └── .wf_app_policies.json  # 모든 앱 정책 포함
      ├── bom2excel
      ├── conversion_verifier
      └── ...
```

**새 구조 (Per-App)**
```
~/.wf_rpa/
  ├── bom2excel/
  │   └── .bom2excel.app_policy.json  # bom2excel 정책만
  ├── conversion_verifier/
  │   └── .conversion_verifier.app_policy.json  # conversion_verifier 정책만
  └── ...
```

**장점**
- ✅ 앱별 독립 배포 가능
- ✅ 정책 충돌 방지
- ✅ 배포 패키지 단순화
- ✅ 앱 삭제 시 정책도 함께 제거

---

### 2. CreditManager 정책 로드 경로 수정
**파일**: `10.common/wf_credit_manager.py`

**변경 사항**
1. **새 메서드 추가**: `_load_app_policy_file(app_name)`
   - 앱별 정책 파일 로드: `~/.wf_rpa/{app_name}/.{app_name}.app_policy.json`
   - 기존 전역 파일 대신 앱별 파일 우선 로드

2. **정책 로드 우선순위 변경**
   ```python
   # 1) 내장 정책 (기본값)
   # 2) 레포 정책 JSON 로드 (10.common/app_policies.json)
   # 3) 로컬 앱별 정책 로드 (Sheets 동기화 정책) ← 변경
   ```

3. **정책 파일 경로 변경**
   ```python
   # 이전: self.policy_file = self.wf_rpa_dir / '.wf_app_policies.json'
   # 이후: self.policy_file = self.app_dir / f'.{app_name}.app_policy.json'
   ```

4. **`_update_policy_file()` 메서드 수정**
   - 전역 구조 → 앱별 구조로 변경
   - 앱별 정책만 저장 (다른 앱 정책 포함 안 함)

5. **`get_all_policies()` 메서드 수정**
   - 레포 기본 정책 JSON 반환 (전역 파일 대신)

---

### 3. PyInstaller Spec 파일 업데이트
**파일**: 
- `30.apps/bom2excel/bom2excel.spec`
- `50.data/conversion_verifier/conversion_verifier.spec`

**변경 사항**: `collect_essential_resources()` 함수에 추가
```python
# 3. 앱별 정책 파일 (템플릿)
app_policy_template = SPEC_DIR / 'config' / f'dev_{APP_NAME}.app_policy.json'
if app_policy_template.exists():
    datas.append((str(app_policy_template), 'config'))
    print(f"✓ 정책 템플릿 포함: {app_policy_template.name}")
```

**결과**: 빌드 시 앱별 정책 템플릿이 자동으로 포함됨

---

### 4. Config 템플릿 Installer 스크립트 생성
**파일**: `scripts/install_config_templates.ps1`

**기능**
- 개발 템플릿(`dev_*.json`)을 사용자 홈으로 배포
- Hidden 속성 자동 설정 (Windows)
- 기존 파일 보호 (`-Force` 옵션으로 덮어쓰기 가능)
- 앱별 정책 파일 배포 지원

**사용법**
```powershell
# 모든 앱 배포
.\install_config_templates.ps1

# 특정 앱만 배포
.\install_config_templates.ps1 -AppName bom2excel

# 기존 파일 덮어쓰기
.\install_config_templates.ps1 -Force

# 배포된 파일 목록 확인
.\install_config_templates.ps1 -Verbose
```

**배포 과정**
1. `.wf_rpa` 디렉토리 생성
2. 앱별 디렉토리 생성 (예: `~/.wf_rpa/bom2excel`)
3. `config/dev_*.json` → `~/.wf_rpa/{app}/.*.json` 복사
4. Hidden 속성 설정
5. 정책 파일 배포: `dev_{app}.app_policy.json` → `.{app}.app_policy.json`

---

### 5. 빌드 스크립트 통합
**파일**
- `30.apps/bom2excel/build_bom2excel.ps1` (신규 생성)
- `50.data/conversion_verifier/build_conversion_verifier.ps1` (수정)

**변경 사항**
1. **파라미터 추가**: `-SkipInstaller` (Config 설치 건너뛰기)
2. **자동 Config 설치**: 빌드 완료 후 installer 스크립트 자동 실행
3. **에러 핸들링**: Config 설치 실패 시에도 빌드는 성공으로 처리

**빌드 흐름**
```
1. PyInstaller 실행
2. 빌드 완료
3. Config 템플릿 자동 설치 (optional)
4. 결과 출력
```

**사용법**
```powershell
# 일반 빌드 (Config 자동 설치)
.\build_bom2excel.ps1

# Config 설치 건너뛰기
.\build_bom2excel.ps1 -SkipInstaller

# Clean 빌드
.\build_bom2excel.ps1 -Clean
```

---

## 📁 생성된 파일 목록

### Config 템플릿
```
30.apps/bom2excel/config/
  └── dev_bom2excel.app_policy.json

50.data/conversion_verifier/config/
  └── dev_conversion_verifier.app_policy.json
```

### 스크립트
```
scripts/
  └── install_config_templates.ps1

30.apps/bom2excel/
  └── build_bom2excel.ps1
```

---

## 🔄 마이그레이션 가이드

### 기존 사용자 (전역 정책 파일 사용 중)
1. **자동 마이그레이션**: CreditManager가 기존 전역 파일 무시하고 앱별 파일 생성
2. **수동 정리** (선택):
   ```powershell
   Remove-Item "$env:USERPROFILE\.wf_rpa\.wf_app_policies.json"
   ```

### 새 설치 (빌드 배포)
1. PyInstaller 빌드 시 템플릿 자동 포함
2. 첫 실행 시 `_update_policy_file()`이 앱별 정책 파일 생성
3. Hidden 속성 자동 설정 (Release 모드)

---

## 🧪 테스트 체크리스트

### 개발 환경
- [ ] `wf_credit_manager.py` 정책 로드 확인
- [ ] 앱별 정책 파일 생성 확인
- [ ] 정책 파일 경로 정확성 확인
- [ ] 기존 전역 파일과 충돌 없음 확인

### 빌드 테스트
- [ ] Spec 파일 빌드 성공 확인
- [ ] 정책 템플릿 포함 확인 (`config/dev_*.json`)
- [ ] 빌드 후 Config 자동 설치 확인

### 배포 테스트
- [ ] Installer 스크립트 실행 확인
- [ ] Hidden 속성 설정 확인 (Windows)
- [ ] 기존 파일 보호 확인 (`-Force` 없을 때)
- [ ] 앱별 정책 파일 배포 확인

### 실행 테스트
- [ ] 앱 첫 실행 시 정책 파일 생성
- [ ] 정책 값 정확성 확인 (credit_per_work 등)
- [ ] 정책 동기화 (Sheets) 정상 작동 확인
- [ ] 크레딧 차감 정확성 확인

---

## 📊 변경 통계

| 항목 | 변경 전 | 변경 후 |
|-----|---------|---------|
| 정책 파일 구조 | 전역 1개 | 앱별 N개 |
| 배포 복잡도 | 높음 (의존성) | 낮음 (독립) |
| 정책 충돌 가능성 | 있음 | 없음 |
| 앱 독립성 | 낮음 | 높음 |
| 코드 수정 라인 | - | ~100줄 |
| 신규 파일 | - | 4개 |

---

## 🎯 다음 단계

### 즉시 수행
1. 개발 환경에서 테스트 실행
2. 빌드 테스트 (bom2excel, conversion_verifier)
3. Config 설치 테스트

### 추후 작업
1. 다른 앱들(dwg_classifier 등)에 동일 패턴 적용
2. NSIS Installer에 Config 배포 로직 추가
3. 마이그레이션 가이드 문서화
4. 레거시 전역 파일 정리 스크립트 작성

---

## 💡 주요 개선 사항

### 코드 품질
- ✅ Single Responsibility: 각 앱이 자신의 정책만 관리
- ✅ Loose Coupling: 앱 간 의존성 제거
- ✅ Easy Deployment: 독립적 배포 가능

### 유지보수성
- ✅ 정책 변경 시 영향 범위 최소화
- ✅ 디버깅 용이 (앱별 파일 분리)
- ✅ 테스트 독립성 향상

### 사용자 경험
- ✅ 앱 설치/삭제 간편
- ✅ 정책 충돌 방지
- ✅ 투명한 파일 관리

---

## 📝 참고 자료

### 코드 위치
- CreditManager: `10.common/wf_credit_manager.py` (Line 620~870)
- Spec 파일: `30.apps/{app}/{app}.spec` (collect_essential_resources)
- Installer: `scripts/install_config_templates.ps1`
- Build Script: `30.apps/{app}/build_{app}.ps1`

### 정책 파일 스키마
```json
{
  "version": "1.0",
  "app_name": "bom2excel",
  "last_updated": "2025-11-09T00:00:00",
  "source": "repo|sheets|builtin",
  "policy": {
    "credit_per_work": 100,
    "trial_credits": 2000,
    "...": "..."
  }
}
```

---

## ✅ 작업 완료 확인

모든 작업이 완료되었습니다:

1. ✅ 앱별 정책 파일 구조 변경
2. ✅ CreditManager 정책 로드 경로 수정
3. ✅ PyInstaller spec 파일 업데이트
4. ✅ Installer 스크립트 생성
5. ✅ 빌드 스크립트 통합

**다음 단계**: 개발 환경 테스트 및 빌드 테스트 진행

---

## 메모리 설정 관리 (추가 상세)

운영 중 동적으로 조정되는 메모리/타임아웃 관련 설정을 정책으로 관리합니다. UI에는 노출하지 않고 Google Sheets에서만 조정합니다.

### 우선순위
```
1) {app}/credit_policy.json (Sheets 동기화)
2) 사용자 설정 (.{app}_settings.json)
3) 레포 기본 정책 (10.common/app_policies.json)
4) 코드 기본값
```

### 운영 설정 목록
| 항목 | 설명 | 기본값 |
|---|---|---|
| memory_threshold_percent | 가용 메모리 임계치(%) | 20 |
| enable_memory_monitor | 메모리 모니터 사용 | true |
| base_wait_time | 기본 대기 시간(초) | 60 |
| seconds_per_10mb | 10MB당 추가 시간(초) | 60 |
| restart_count | 정기 재시작 주기(건) | 15 |
| consec_timeout_limit | 연속 타임아웃 허용 | 2 |

### 파일 구조
- 기본 정책: `10.common/app_policies.json`
- 앱별 정책 파일: `%USERPROFILE%/.wf_rpa/{app}/credit_policy.json`
- 사용자 설정: `%USERPROFILE%/.wf_rpa/{app}/.settings.json`

### 동기화와 적용 예시
```python
from wf_credit_manager import WorksFreeManager
WorksFreeManager(is_dev_mode=False).refresh_policies_from_sheets()
```

```python
# 적용 순서 의사코드
config = load_user_settings()
policy = load_app_policy()
if policy:
  config['app_config'].update(policy)
apply(config)
```

### 테스트
```powershell
cd d:\drive_files\10.worksfree\10.rpa\90.tests\30.apps\bom2excel
python test_policy_loading.py
```
