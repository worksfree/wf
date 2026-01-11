# 90.tests - 테스트 디렉토리

WorksFree RPA 프로젝트의 모든 테스트를 포함하는 디렉토리입니다.

## 📁 폴더 구조

```
90.tests/
├── conftest.py                    # pytest 공통 fixture 설정
├── __init__.py
├── 10.common/                     # 공통 모듈 테스트
│   ├── test_wf_credit_manager_policies.py
│   ├── test_wf_credit_refresh.py
│   ├── test_wf_credit_logging_integration.py
│   ├── test_wf_scenario_complete.py
│   ├── test_wf_hidden_attributes.py
│   ├── test_wf_email_success.py           # 이메일 전송 테스트
│   └── test_wf_email_config_save.py       # 이메일 설정 저장 테스트
└── 30.apps/                       # 앱별 테스트
    └── bom2excel/
        ├── test_unlimited_credits.py
        └── test_integration.py
```

## 🏷️ 테스트 분류 (마커)

### Unit Tests (단위 테스트)
- **마커**: `@pytest.mark.unit`
- **목적**: 개별 함수/클래스의 독립적인 동작 검증
- **특징**: 
  - 외부 의존성 최소화 (모킹 사용)
  - 빠른 실행 속도 (1초 미만)
  - 높은 격리성

**예시:**
```python
@pytest.mark.unit
def test_credit_deduction_logic():
    """크레딧 차감 로직만 테스트"""
    pass
```

### Integration Tests (통합 테스트)
- **마커**: `@pytest.mark.integration`
- **목적**: 여러 모듈 간 상호작용 검증
- **특징**:
  - 실제 파일 시스템 사용 (격리된 환경)
  - Google Sheets API는 모킹
  - 중간 실행 속도 (1~5초)

**예시:**
```python
@pytest.mark.integration
def test_credit_sync_workflow(isolated_wf_environment, mock_google_sheets):
    """크레딧 동기화 전체 흐름 테스트"""
    pass
```

### Staging Tests (스테이징 테스트)
- **마커**: `@pytest.mark.staging`
- **목적**: 프로덕션 환경 시뮬레이션
- **특징**:
  - 실제 환경과 유사한 조건
  - 전체 워크플로우 검증
  - 느린 실행 속도 (5초 이상)

**예시:**
```python
@pytest.mark.staging
def test_full_bom2excel_workflow():
    """BOM2Excel 전체 프로세스 E2E 테스트"""
    pass
```

## 🚀 테스트 실행 방법

### 기본 사용법

```powershell
# 프로젝트 루트에서 실행
cd D:\drive_files\10.worksfree\10.rpa

# 모든 테스트 실행
pytest

# 특정 마커만 실행
pytest -m unit              # 단위 테스트만
pytest -m integration       # 통합 테스트만
pytest -m staging           # 스테이징 테스트만

# 특정 모듈만 실행
pytest 90.tests/10.common                    # 공통 모듈 테스트
pytest 90.tests/30.apps/bom2excel           # bom2excel 테스트

# 특정 파일만 실행
pytest 90.tests/10.common/test_wf_credit_refresh.py

# 특정 테스트 함수만 실행
pytest 90.tests/30.apps/bom2excel/test_integration.py::test_full_workflow_simulation
```

### PowerShell 스크립트 사용 (통합 러너)

```powershell
# 통합 러너 위치로 이동
cd D:\drive_files\10.worksfree\10.rpa\90.tests

# 모든 테스트 실행
./run.ps1

# 범위별 실행
./run.ps1 -Scope unit
./run.ps1 -Scope integration
./run.ps1 -Scope sanity
./run.ps1 -Scope regression

# 정적 분석만 실행 (ruff, mypy)
./run.ps1 -Scope static

# 커버리지/상세/실패 즉시 중단
./run.ps1 -Coverage -Detail -FailFast
```

### 고급 옵션

```powershell
# 마지막 실패한 테스트만 재실행
pytest --lf

# 실패한 테스트 먼저 실행
pytest --ff

# 병렬 실행 (pytest-xdist 필요)
pytest -n auto

# 특정 테스트 키워드로 필터링
pytest -k "credit"          # 이름에 "credit"이 포함된 테스트만

# 여러 마커 조합
pytest -m "unit and not slow"     # 단위 테스트 중 slow가 아닌 것만
pytest -m "integration or staging" # 통합 또는 스테이징 테스트
```

## 🧪 Fixture 사용법

### 기본 Fixtures

#### `temp_wf_rpa_home`
임시 WF_RPA_HOME 디렉토리를 생성하여 실제 사용자 홈을 오염시키지 않습니다.

```python
def test_something(temp_wf_rpa_home):
    # temp_wf_rpa_home은 Path 객체
    assert temp_wf_rpa_home.exists()
    credit_file = temp_wf_rpa_home / "bom2excel" / ".bom2excel_credits.json"
```

#### `isolated_wf_environment`
WorksFreeManager 싱글톤을 리셋하여 완전히 격리된 환경을 제공합니다.

```python
def test_manager(isolated_wf_environment):
    from wf_credit_manager import WorksFreeManager
    wf_manager = WorksFreeManager()  # 새로운 독립 인스턴스
```

#### `mock_google_sheets`
Google Sheets API 호출을 모킹합니다.

```python
def test_sync(mock_google_sheets):
    mock_google_sheets.read_sheet.return_value = [['header'], ['data']]
    # 실제 API 호출 없이 테스트 가능
```

### 데이터 Fixtures

```python
def test_credit_data(sample_credit_data):
    # 미리 정의된 샘플 크레딧 데이터 사용
    assert sample_credit_data['trial_credits'] == 500

def test_unlimited(sample_unlimited_credit_data):
    # 무제한 크레딧 샘플 데이터
    assert sample_unlimited_credit_data['trial_credits'] == -1
```

## 📝 테스트 작성 가이드

### 단위 테스트 예시

```python
# 90.tests/10.common/test_wf_credit_deduction.py
import pytest

@pytest.mark.unit
def test_credit_deduction_calculation():
    """크레딧 차감 계산 로직 테스트"""
    # Given
    initial_credits = 1000
    deduction = 50
    
    # When
    result = initial_credits - deduction
    
    # Then
    assert result == 950
```

### 통합 테스트 예시

```python
# 90.tests/30.apps/bom2excel/test_integration.py
import pytest

@pytest.mark.integration
def test_credit_workflow(isolated_wf_environment, mock_credit_manager_sheets):
    """크레딧 전체 워크플로우 테스트"""
    from wf_credit_manager import CreditManager
    
    # Given
    cm = CreditManager('bom2excel', 'test@example.com')
    
    # When
    cm.deduct_credit(count=10)
    
    # Then
    status = cm.get_credit_status()
    assert status['remaining_credits'] < 2000  # 초기값보다 작아야 함
```

### 스테이징 테스트 예시

```python
# 90.tests/30.apps/bom2excel/test_staging.py
import pytest

@pytest.mark.staging
@pytest.mark.slow
def test_full_bom2excel_process():
    """BOM2Excel 전체 프로세스 E2E 테스트"""
    # 실제 환경과 유사하게 전체 워크플로우 검증
    pass
```

## 🔧 개발 환경 설정

### pytest 설치

```powershell
pip install pytest pytest-cov pytest-mock
```

### VS Code 설정

`.vscode/settings.json`:
```json
{
    "python.testing.pytestEnabled": true,
    "python.testing.pytestArgs": [
        "90.tests",
        "-v",
        "--tb=short"
    ],
    "python.testing.cwd": "${workspaceFolder}/10.rpa"
}
```

## 📊 커버리지 리포트

```powershell
# 커버리지 측정
pytest --cov=10.common --cov=30.apps --cov-report=html

# 리포트 열기
Invoke-Item htmlcov\index.html
```

## 🐛 트러블슈팅

### Import 오류
```
ImportError: No module named 'wf_credit_manager'
```

**해결책:**
- `pytest.ini`의 `pythonpath` 설정 확인
- `conftest.py`의 `sys.path` 추가 확인

### 환경변수 충돌
```
실제 사용자 홈의 크레딧 파일이 변경됨
```

**해결책:**
- `isolated_wf_environment` fixture 사용
- 수동으로 `WF_RPA_HOME` 설정 확인

### 싱글톤 초기화 문제
```
WorksFreeManager가 이전 테스트의 상태를 유지함
```

**해결책:**
- `isolated_wf_environment` fixture 사용
- 각 테스트에서 싱글톤 리셋

## 📚 참고 자료

- [Pytest 공식 문서](https://docs.pytest.org/)
- [Pytest Fixtures](https://docs.pytest.org/en/stable/fixture.html)
- [Pytest Markers](https://docs.pytest.org/en/stable/example/markers.html)
- [pytest-cov](https://pytest-cov.readthedocs.io/)

## 🎯 테스트 작성 원칙

1. **AAA 패턴**: Arrange (준비) → Act (실행) → Assert (검증)
2. **독립성**: 각 테스트는 서로 독립적으로 실행 가능해야 함
3. **반복성**: 같은 입력에 항상 같은 결과
4. **명확성**: 테스트 이름과 내용만으로 목적 파악 가능
5. **격리성**: 실제 환경에 영향을 주지 않음

## 📈 CI/CD 통합

```yaml
# .github/workflows/test.yml 예시
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.13'
      - run: pip install -r requirements.txt
      - run: pip install pytest pytest-cov
      - run: pytest --cov --cov-report=xml
      - uses: codecov/codecov-action@v2
```
