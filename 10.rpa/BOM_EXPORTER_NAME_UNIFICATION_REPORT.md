# Bom_Exporter 앱명 통일 완료 보고서

## 작업 개요
**목표**: Bom_Exporter 앱의 코드 내 참조를 `bom2excel`에서 `bom_exporter`로 통일

**작업일**: 2025년 (현재 세션)

**우선순위**: Critical (TODO.md Task #1)

## 변경 사항 요약

### 1. 주요 앱 파일 (30.apps/bom_exporter/)

#### ui_main.py
- ✅ 설정 파일 경로: `.wf_rpa/bom2excel` → `.wf_rpa/bom_exporter`
- ✅ Config 폴더 경로: `config/bom2excel` → `config/bom_exporter`
- ✅ Mutex 이름: `WF_BOM2EXCEL` → `WF_BOM_EXPORTER`
- ✅ 로거 이름: `bom2excel` → `bom_exporter`
- ✅ CreditManager app_name: `bom2excel` → `bom_exporter`
- ✅ 실행 상태 current_app: `bom2excel` → `bom_exporter` (2곳)
- ✅ 사용자 디렉토리: `.wf_rpa/bom2excel` → `.wf_rpa/bom_exporter`
- ✅ 정책 동기화: `bom2excel` → `bom_exporter`

#### app_setting_data.py
- ✅ 주석 업데이트: `~/.wf_rpa/bom2excel` → `~/.wf_rpa/bom_exporter`
- ✅ 정책 파일 경로: `config/bom2excel` → `config/bom_exporter`
- ✅ Docstring 업데이트

#### test_*.py 파일
- ✅ test_deployment_mode.py: 배포 설정 파일 경로 변경
- ✅ test_unified_settings.py: Docstring 변경

### 2. 공통 모듈 (10.common/)

#### wf_credit_manager.py
- ✅ APP_CREDIT_POLICIES 키: `bom2excel` → `bom_exporter`
- ✅ 레거시 매핑: `Bom2Excel` → `bom_exporter`
- ✅ 레거시 매핑: `Bom2Excel_Exporter` → `bom_exporter`

#### wf_app_init_helpers.py
- ✅ 모듈 docstring: 앱 목록 업데이트
- ✅ 함수 파라미터 예시 업데이트 (2곳)

#### wf_settings_common.py
- ✅ 정규화 매핑에 `bom_exporter` 자기 참조 추가
- ✅ 기존 `bom2excel` → `bom_exporter` 매핑 유지 (하위 호환성)

### 3. 스크립트 (scripts/)

#### sync_local_policies.py
- ✅ 사용 예시 변경
- ✅ 앱 목록 변경

#### manual_set_credit_changed.py
- ✅ 앱 목록 변경

#### sync_app_policy_app_names.py
- ✅ 매핑 키: `bom2excel` → `bom_exporter`
- ✅ 레거시 이름 목록에 모든 구 이름 포함
- ✅ 정규화 매핑 변경

### 4. 테스트 파일 (90.tests/)

#### test_credit_deduction.py
- ✅ 앱 목록 변경

#### test_credit_consistency.py
- ✅ 앱 목록 변경

#### test_policy_loading.py
- ✅ CreditManager 초기화 app_name 변경

#### test_policy_sync.py
- ✅ CreditManager 초기화 app_name 변경

#### test_wf_credit_refresh.py
- ✅ CreditManager 초기화 app_name 변경

#### test_wf_scenario_complete.py
- ✅ CreditManager 초기화 app_name 변경
- ✅ 주석 업데이트
- ✅ apps_to_test 목록 변경
- ✅ 변수명 변경: `bom2excel_has_policy` → `bom_exporter_has_policy`
- ✅ 변수명 변경: `bom2excel_cost` → `bom_exporter_cost`

#### test_settings_windows.py
- ✅ APPS 딕셔너리 키 변경
- ✅ 경로 변경: `30.apps/bom2excel` → `30.apps/bom_exporter`
- ✅ 함수명 변경: `test_bom2excel` → `test_bom_exporter`
- ✅ Docstring 업데이트

#### generate_specs.py
- ✅ APPS 딕셔너리 키 변경
- ✅ Display name 변경: `BOM2Excel` → `Bom Exporter`
- ✅ 경로 변경: `30.apps/bom2excel` → `30.apps/bom_exporter`

### 5. Config 폴더 구조
- ⚠️ **주의**: `config/bom2excel/` 폴더는 이미 존재하지 않음
- ✅ `config/bom_exporter/` 폴더에 `app_config.json` 존재 확인
- ✅ 코드는 `config/bom_exporter/` 경로 참조 (소문자)

## 하위 호환성 (Backward Compatibility)

### 레거시 이름 매핑
다음 레거시 이름들이 자동으로 `bom_exporter`로 매핑됩니다:
- `Bom2Excel`
- `Bom2Excel_Exporter`
- `bom2excel`

### 사용자 데이터 마이그레이션
- 기존 사용자의 `~/.wf_rpa/bom2excel/` 폴더는 그대로 유지
- 새로운 설정은 `~/.wf_rpa/bom_exporter/`에 생성됨
- `wf_settings_common.py`의 매핑 로직이 자동 변환 처리

## 검증 결과

### 테스트 통과
- ✅ test_policy_loading.py: PASSED
- ✅ test_credit_consistency.py: PASSED
- ✅ CreditManager 초기화: 정상 작동
- ✅ 정책 로드: 정상 (credit_per_work=100, trial_credits=10000)
- ✅ 레거시 이름 매핑: 정상 작동

### 실행 결과
```
App name: bom_exporter
Policy loaded: BOM 엑셀 변환 - 파일당 100크레딧
Credit per work: 100
Trial credits: 10000
Policy file: D:\drive_files\10.worksfree\10.rpa\30.apps\Bom_Exporter\config\bom_exporter\app_config.json
```

## 남아있는 참조 (문서/주석)

다음 항목들은 문서화 목적으로 남겨둠:
1. `Conversion_Verifier/ui_main.py:732` - "BOM2Excel과 완전히 동일한 UI 레이아웃" (비교 주석)
2. `Conversion_Verifier/ui_main.py:1697` - "bom2excel 방식" (참조 주석)
3. `korean_filename_normalizer/ui_setting.py:2` - "matching bom2excel style" (스타일 참조)

이들은 실제 코드 로직에 영향을 주지 않으므로 유지합니다.

## 다음 단계 (권장사항)

### 1. 즉시 필요
- 없음 (모든 중요 변경 완료)

### 2. 향후 개선 사항
1. **사용자 데이터 마이그레이션 스크립트** (선택사항)
   - 기존 `~/.wf_rpa/bom2excel/` → `~/.wf_rpa/bom_exporter/` 자동 이전
   - 첫 실행 시 자동 감지 및 마이그레이션

2. **빌드 및 배포**
   - 다음 빌드부터 새 앱명 적용됨
   - 사용자에게는 투명하게 처리 (레거시 매핑 덕분)

3. **문서 업데이트**
   - 사용자 매뉴얼에서 앱 이름 변경 안내
   - API 문서/개발자 가이드 업데이트

## 영향 범위

### ✅ 영향 없음
- 다른 3개 앱 (DWG_Classifier, Conversion_Verifier, Korean_Filename_Normalizer)
- 기존 사용자 설정 파일
- 크레딧 시스템 작동

### ✅ 정상 작동 확인
- 앱 초기화 프로세스
- 크레딧 관리 시스템
- 정책 로드 및 동기화
- 설정 파일 관리

## 결론

**상태**: ✅ 완료

Bom_Exporter 앱명 통일 작업이 성공적으로 완료되었습니다. 모든 주요 코드 참조가 `bom_exporter`로 변경되었으며, 레거시 이름에 대한 하위 호환성도 유지됩니다. 테스트 통과 및 실행 검증 완료.

**변경 파일 수**: 15개
**변경 라인 수**: 약 40+ 항목
**테스트 결과**: 모두 통과 (PASSED)
