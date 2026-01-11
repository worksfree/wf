# DC Refactoring Tests

DC (dwg_classifier) 리팩토링 후 기존 기능에 side effect가 없음을 검증하는 테스트 모음입니다.

## 📁 테스트 구조

```
10.rpa/90.tests/
├── 10.common/
│   └── test_wf_credit_session_utils.py    # wf_credit_session_utils 함수 단위 테스트 (7개)
│
└── 50.data/
    └── dwg_classifier/
        ├── test_integration.py             # DC 통합 테스트 (4개)
        ├── test_refactoring_side_effects.py # 리팩토링 전/후 로직 비교 (7개)
        ├── test_session_logic.py           # 세션 관리 워크플로우 (4개)
        └── test_function_calls.py          # ui_main.py 함수 호출 검증 (6개)
```

## ✅ 테스트 개요

### 1. test_wf_credit_session_utils.py
**위치:** `10.rpa/90.tests/10.common/`  
**목적:** wf_credit_session_utils.py의 7개 함수 단위 테스트

**테스트 항목:**
- calculate_processable_count
- compute_session_stats
- format_progress_label (3가지 상태)
- build_credit_shortage_init_message (allow/block)
- build_credit_shortage_completion_message
- build_normal_completion_message
- get_credit_purchase_url

**실행:**
```powershell
python 10.rpa\90.tests\10.common\test_wf_credit_session_utils.py
```

### 2. test_integration.py
**위치:** `10.rpa/90.tests/50.data/dwg_classifier/`  
**목적:** DC import chain 및 통합 검증

**테스트 항목:**
- wf_credit_session_utils import 성공
- 공통 모듈(wf_log) 사용 가능
- DC ui_main.py 문법 검증
- Utils 함수 호출 확인

**실행:**
```powershell
python 10.rpa\90.tests\50.data\dwg_classifier\test_integration.py
```

### 3. test_refactoring_side_effects.py
**위치:** `10.rpa/90.tests/50.data/dwg_classifier/`  
**목적:** 리팩토링 전/후 로직이 동일한 출력을 생성하는지 비교

**테스트 항목:**
- 처리 가능 파일 수 계산 (5개 케이스)
- 진행률 라벨 포맷 (4개 상태)
- 크레딧 부족 메시지 (allow/block)
- 중단 메시지
- 완료 메시지
- Edge cases (크레딧 0, 파일 0, 빈 통계, 큰 숫자)
- 세션 통계 계산

**실행:**
```powershell
$env:PYTHONIOENCODING="utf-8"; python 10.rpa\90.tests\50.data\dwg_classifier\test_refactoring_side_effects.py
```

### 4. test_session_logic.py
**위치:** `10.rpa/90.tests/50.data/dwg_classifier/`  
**목적:** 세션 관리 및 크레딧 로직 정확성 검증

**테스트 시나리오:**
- 전체 워크플로우 (100개 파일, 3번 중단)
- 이전 처리 파일 없는 경우
- 모든 파일 이미 처리된 경우
- 크레딧 계산 정확성 (충분/부족/정확)

**실행:**
```powershell
python 10.rpa\90.tests\50.data\dwg_classifier\test_session_logic.py
```

### 5. test_function_calls.py
**위치:** `10.rpa/90.tests\50.data\dwg_classifier/`  
**목적:** ui_main.py에서 utils 함수 호출이 올바른지 검증

**검증 항목:**
- 7개 함수 import 확인
- 각 함수 호출 위치 및 횟수
- 파라미터 일관성
- 하드코딩 메시지 잔존 여부

**실행:**
```powershell
$env:PYTHONIOENCODING="utf-8"; python 10.rpa\90.tests\50.data\dwg_classifier\test_function_calls.py
```

## 📊 전체 테스트 실행

모든 테스트를 한 번에 실행:

```powershell
# 10.common 테스트
python 10.rpa\90.tests\10.common\test_wf_credit_session_utils.py

# DC 통합 테스트
python 10.rpa\90.tests\50.data\dwg_classifier\test_integration.py

# DC 세션 로직
python 10.rpa\90.tests\50.data\dwg_classifier\test_session_logic.py

# Side effect 검증 (UTF-8 인코딩 필요)
$env:PYTHONIOENCODING="utf-8"; python 10.rpa\90.tests\50.data\dwg_classifier\test_refactoring_side_effects.py

# 함수 호출 검증 (UTF-8 인코딩 필요)
$env:PYTHONIOENCODING="utf-8"; python 10.rpa\90.tests\50.data\dwg_classifier\test_function_calls.py
```

## ✅ 검증 결과

**총 테스트:** 28/28 통과 (100%)

| 테스트 파일 | 테스트 수 | 상태 |
|------------|----------|------|
| test_wf_credit_session_utils.py | 7 | ✅ |
| test_integration.py | 4 | ✅ |
| test_refactoring_side_effects.py | 7 | ✅ |
| test_session_logic.py | 4 | ✅ |
| test_function_calls.py | 6 | ✅ |

**최종 결론:** ✅ Side effect 없음, 즉시 배포 가능

## 📋 관련 문서

- **TEST_REPORT.md** - 전체 테스트 리포트
- **SIDE_EFFECT_REPORT.md** - Side effect 검증 상세 보고서

## 💡 주의사항

### 인코딩 문제
일부 테스트는 UTF-8 인코딩이 필요합니다 (이모지 출력 포함):

```powershell
$env:PYTHONIOENCODING="utf-8"
```

### 경로 구조
- `10.common` 테스트: 공통 모듈 테스트
- `50.data/dwg_classifier` 테스트: DC 특화 테스트

이 구조는 프로젝트 전체 테스트 구조를 따릅니다:
```
90.tests/
├── 10.common/     # 공통 모듈 테스트
├── 30.apps/       # 앱별 테스트
└── 50.data/       # 데이터 앱 테스트
```
