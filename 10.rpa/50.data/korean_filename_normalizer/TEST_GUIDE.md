# UI 자동화 테스트 가이드

## 개요

한글 파일명 복원 앱의 UI 기반 자동화 테스트 스크립트입니다. pytest를 사용하여 GUI 컴포넌트와 핵심 기능을 자동으로 테스트합니다.

## 테스트 범위

### 1. UI 컴포넌트 테스트 (`TestUIComponents`)
- ✅ UI 초기화 확인
- ✅ 창 제목 검증
- ✅ 버튼 존재 여부
- ✅ 진행률 바 초기 상태

### 2. 폴더 선택 기능 (`TestFolderSelection`)
- ✅ 폴더 경로 변수 설정
- ✅ 폴더 없이 스캔 시도
- ✅ 유효한 폴더 선택

### 3. 파일명 정규화 (`TestFilenameNormalization`)
- ✅ NFC 정규화 동작
- ✅ 자소 분리 감지
- ✅ 자소 분리 파일 검색
- ✅ 정상 파일 필터링

### 4. 진행 상황 추적 (`TestProgressTracking`)
- ✅ 초기 카운트 확인
- ✅ 진행률 업데이트
- ✅ 스피너 애니메이션

### 5. 스캔 기능 (`TestScanFunctionality`)
- ✅ 자소 분리 파일 스캔
- ✅ 빈 폴더 처리
- ✅ 버튼 상태 변경

### 6. 관리자 모드 (`TestAdminMode`)
- ✅ 관리자 모드 진입
- ✅ 관리자 모드 종료
- ✅ 로그 프레임 생성/제거

### 7. 테스트 데이터 생성 (`TestTestDataGeneration`)
- ✅ 테스트 파일 생성
- ✅ 테스트 파일 삭제

### 8. 전체 워크플로우 (`TestEndToEndWorkflow`)
- ✅ 폴더 선택 → 스캔 → 정규화 완전 흐름

### 9. UI 반응성 (`TestUIResponsiveness`)
- ✅ 버튼 클릭 반응
- ✅ 크레딧 표시 업데이트

## 설치

### 필수 패키지 설치
```powershell
pip install pytest pytest-timeout
```

## 실행 방법

### 방법 1: PowerShell 스크립트 실행 (권장)
```powershell
.\run_ui_tests.ps1
```

### 방법 2: 직접 pytest 실행
```powershell
python -m pytest test_ui_automation.py -v -s
```

### 방법 3: Python 스크립트로 실행
```powershell
python test_ui_automation.py
```

## 테스트 옵션

### 상세 출력
```powershell
pytest test_ui_automation.py -v -s
```

### 특정 테스트 클래스만 실행
```powershell
pytest test_ui_automation.py::TestUIComponents -v
```

### 특정 테스트 메서드만 실행
```powershell
pytest test_ui_automation.py::TestUIComponents::test_ui_initialization -v
```

### 실패한 테스트만 재실행
```powershell
pytest test_ui_automation.py --lf
```

### 커버리지 리포트 생성
```powershell
pip install pytest-cov
pytest test_ui_automation.py --cov=. --cov-report=html
```

## 테스트 결과 예시

```
================================ test session starts ================================
platform win32 -- Python 3.13.x, pytest-8.x.x
collected 25 items

test_ui_automation.py::TestUIComponents::test_ui_initialization PASSED        [  4%]
test_ui_automation.py::TestUIComponents::test_window_title PASSED             [  8%]
test_ui_automation.py::TestUIComponents::test_buttons_exist PASSED            [ 12%]
test_ui_automation.py::TestUIComponents::test_progress_bar_initial_state PASSED [ 16%]
test_ui_automation.py::TestFolderSelection::test_folder_path_variable PASSED  [ 20%]
test_ui_automation.py::TestFolderSelection::test_scan_toggle_without_folder PASSED [ 24%]
...

================================ 25 passed in 15.23s ================================
```

## 주요 기능

### 1. 자동 임시 폴더 생성
테스트는 `tempfile.mkdtemp()`를 사용하여 임시 폴더를 생성하고 테스트 후 자동으로 정리합니다.

### 2. 등록 우회
테스트 실행 시 환경변수 `WF_FORCE_REGISTERED=1`을 설정하여 사용자 등록 과정을 우회합니다.

### 3. Mock 객체 사용
실제 파일 시스템 작업이 필요 없는 경우 Mock 객체를 사용하여 빠른 테스트를 수행합니다.

### 4. 다양한 테스트 케이스
- NFD 분해 파일
- 자모 분리 파일
- 정상 파일
- 혼합 케이스

## 문제 해결

### pytest를 찾을 수 없음
```powershell
python -m pip install pytest
```

### tkinter 에러
Windows에서는 일반적으로 tkinter가 Python과 함께 설치됩니다. 만약 에러가 발생하면:
```powershell
# Python 재설치 시 "tcl/tk and IDLE" 옵션 체크
```

### 테스트 타임아웃
일부 UI 테스트는 시간이 걸릴 수 있습니다. 타임아웃 설정:
```powershell
pytest test_ui_automation.py --timeout=300
```

## 테스트 확장

새로운 테스트를 추가하려면:

1. `test_ui_automation.py`에 새 테스트 클래스 추가
2. `@pytest.fixture`로 필요한 픽스처 정의
3. `test_` 접두사로 테스트 메서드 작성

예시:
```python
class TestNewFeature:
    @pytest.fixture
    def app(self):
        root = tk.Tk()
        app = KoreanFilenameNormalizerApp(root)
        yield app
        root.destroy()
    
    def test_my_feature(self, app):
        # 테스트 코드
        assert app.some_attribute == expected_value
```

## CI/CD 통합

GitHub Actions 예시:
```yaml
name: UI Tests

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
      - run: pip install pytest
      - run: pytest test_ui_automation.py -v
```

## 참고 자료

- [pytest 공식 문서](https://docs.pytest.org/)
- [tkinter 테스트 가이드](https://docs.python.org/3/library/tkinter.html)
- [unittest.mock 문서](https://docs.python.org/3/library/unittest.mock.html)
