# 동적 테스트 (Dynamic Testing)

## 개요
코드를 실행하여 실제 동작을 검증하는 테스트 모음입니다.

## 디렉토리 구조
```
90.tests/dynamic/
├── run_dynamic_tests.py           # 메인 실행 스크립트
├── unit/                          # 유닛 테스트
│   ├── test_credit_manager.py     # 크레딧 매니저 테스트
│   └── test_ui_functions.py       # UI 함수 테스트
├── integration/                   # 통합 테스트
│   └── test_credit_registration_flow.py
├── results/                       # 테스트 결과 저장
│   ├── dynamic_test_report_YYYYMMDD_HHMMSS.txt
│   └── dynamic_test_results_YYYYMMDD_HHMMSS.json
└── README.md                      # 이 파일
```

## 실행 방법

### 전체 동적 테스트 실행
```bash
cd d:\drive_files\10.worksfree\10.rpa\90.tests\dynamic
python run_dynamic_tests.py
```

### 카테고리별 실행
```bash
# 유닛 테스트만
pytest -m unit

# 통합 테스트만
pytest -m integration

# 스모크 테스트만
pytest 90.tests/dwg_smoke_test.py 90.tests/kfn_smoke_test.py
```

### 특정 파일 실행
```bash
pytest 90.tests/dynamic/unit/test_credit_manager.py -v
```

### 실패한 테스트만 재실행
```bash
pytest --lf  # last-failed
```

## 테스트 카테고리

### 1. 유닛 테스트 (Unit Tests)
**목적**: 개별 함수/메서드의 정확성 검증

#### test_credit_manager.py
- **TestCreditManagerBasics**: 기본 초기화 및 싱글톤 패턴
- **TestCreditDeduction**: 크레딧 차감 로직
- **TestCreditRefresh**: 크레딧 새로고침 기능
- **TestPolicyLoading**: 정책 파일 로딩
- **TestRegistrationCheck**: 사용자 등록 확인
- **TestUsageLogging**: 사용 내역 로깅

#### test_ui_functions.py
- **TestDWGClassifierFunctions**: DWG Classifier 함수 존재 확인
- **TestBOM2ExcelFunctions**: BOM2Excel 함수 일관성
- **TestConversionVerifierFunctions**: Conversion Verifier 함수
- **TestKoreanFilenameNormalizerFunctions**: KFN 함수
- **TestFunctionNamingConvention**: 4개 앱 함수명 통일성
- **TestAdminModeFunctions**: 관리자 모드 함수
- **TestStartFunctionPattern**: start_* 패턴 검증

### 2. 통합 테스트 (Integration Tests)
**목적**: 여러 모듈의 상호작용 검증

#### test_credit_registration_flow.py
- **TestCreditRegistrationIntegration**: 크레딧 + 등록 통합
- **TestMultiAppCreditManagement**: 다중 앱 크레딧 관리
- **TestCreditPolicyWorkflow**: 전체 워크플로우

### 3. 스모크 테스트 (Smoke Tests)
**목적**: 앱이 기본적으로 실행되는지 확인

- **dwg_smoke_test.py**: DWG Classifier 실행 가능 여부
- **kfn_smoke_test.py**: Korean Filename Normalizer 실행 가능 여부

## 테스트 마커

pytest 마커를 사용하여 테스트를 분류합니다:

```python
@pytest.mark.unit         # 유닛 테스트
@pytest.mark.integration  # 통합 테스트
@pytest.mark.smoke        # 스모크 테스트
@pytest.mark.slow         # 느린 테스트 (10초+)
```

## Fixtures

테스트에서 사용 가능한 주요 fixture들:

### 환경 Fixtures
- `isolated_wf_environment`: 독립된 테스트 환경
- `temp_wf_rpa_home`: 임시 WF_RPA_HOME
- `auto_registered_user`: 자동 등록된 사용자

### Mock Fixtures
- `mock_google_sheets`: Google Sheets API 모킹
- `mock_hardware_info`: 하드웨어 정보 모킹
- `mock_credit_manager_sheets`: 크레딧 매니저 시트 모킹

### 데이터 Fixtures
- `sample_credit_data`: 샘플 크레딧 데이터
- `sample_unlimited_credit_data`: 무제한 크레딧
- `sample_user_config`: 샘플 사용자 설정

## 테스트 작성 가이드

### 유닛 테스트 예제
```python
import pytest
from wf_credit_manager import CreditManager

@pytest.mark.unit
class TestMyCreditFeature:
    def test_credit_calculation(self, isolated_wf_environment):
        """크레딧 계산이 정확한지 확인"""
        manager = CreditManager("test_app")
        status = manager.get_credit_status()
        
        assert status['total_credits'] >= 0
```

### 통합 테스트 예제
```python
@pytest.mark.integration
class TestCreditSync:
    def test_sync_with_sheets(self, mock_google_sheets):
        """시트와 동기화가 정상 작동하는지 확인"""
        # 테스트 코드...
```

### 스모크 테스트 예제
```python
def test_app_launches():
    """앱이 실행되는지만 확인"""
    # 최소한의 초기화
    # 예외 발생하지 않으면 통과
```

## 테스트 결과 해석

### 출력 예시
```
========================================
동적 테스트 결과 리포트
실행 시각: 2025-11-20 13:00:00
========================================

[단위 테스트 (개별 함수/메서드)]
------------------------------------------------------------
  상태: ✓ PASS
  통과: 25
  실패: 0
  실행 시간: 3.45초

[통합 테스트 (모듈 간 상호작용)]
------------------------------------------------------------
  상태: ✓ PASS
  통과: 8
  실패: 0
  실행 시간: 2.10초

========================================
요약
========================================
총 테스트: 33
통과: 33
실패: 0
총 실행 시간: 5.55초
통과율: 100.0%
```

### 상태 코드
- **PASS** (✓): 모든 테스트 통과
- **FAIL** (✗): 일부 테스트 실패
- **TIMEOUT** (⏱): 실행 시간 초과
- **ERROR** (✗): 실행 오류
- **SKIP** (-): 테스트 건너뜀

## CI/CD 통합

### GitHub Actions 예제
```yaml
name: Dynamic Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.13'
      - name: Install dependencies
        run: pip install pytest
      - name: Run dynamic tests
        run: python 90.tests/dynamic/run_dynamic_tests.py
```

## 디버깅

### Verbose 모드
```bash
pytest -v -s  # 모든 출력 표시
```

### 특정 테스트 디버깅
```bash
pytest -v -s test_credit_manager.py::TestCreditDeduction::test_deduct_credit_success
```

### PDB 디버거 사용
```python
def test_something():
    import pdb; pdb.set_trace()
    # 디버깅...
```

### 로그 레벨 조정
```bash
pytest --log-cli-level=DEBUG
```

## 성능 측정

### 느린 테스트 찾기
```bash
pytest --durations=10  # 가장 느린 10개 표시
```

### 타임아웃 설정
```python
@pytest.mark.timeout(5)  # 5초 제한
def test_fast_operation():
    pass
```

## 커버리지 측정

### 커버리지 리포트 생성
```bash
pip install pytest-cov
pytest --cov=10.common --cov-report=html
```

### 결과 확인
```
htmlcov/index.html  # 브라우저에서 열기
```

## 베스트 프랙티스

### ✅ DO
1. 각 테스트는 독립적으로 실행 가능해야 함
2. fixture를 사용하여 환경 격리
3. 의미 있는 테스트 이름 사용
4. assert 메시지로 실패 원인 명시
5. 테스트는 빠르게 (1초 이내)

### ❌ DON'T
1. 테스트 간 의존성 생성 금지
2. 실제 Google Sheets API 호출 금지 (mock 사용)
3. 하드코딩된 경로 사용 금지
4. Sleep 사용 자제 (비동기 대신 polling)
5. 너무 많은 것을 한 테스트에 검증

## 문제 해결

### ImportError 발생 시
```python
# conftest.py에서 경로 추가 확인
sys.path.insert(0, str(PROJECT_ROOT / "10.common"))
```

### Fixture not found
```python
# conftest.py에 fixture가 정의되어 있는지 확인
# scope와 autouse 설정 확인
```

### 테스트 격리 실패
```python
# isolated_wf_environment fixture 사용
# 싱글톤 초기화 확인
```

## 참고 자료
- [Pytest 공식 문서](https://docs.pytest.org/)
- [함수 네이밍 컨벤션](../../FUNCTION_NAMING_CONVENTION.md)
- [정적 테스트](../static/README.md)

## 변경 이력
- 2025-11-20: 동적 테스트 인프라 구축 및 초기 테스트 작성
