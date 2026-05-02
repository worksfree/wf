# 기업 정보 수집 자동화 스크립트

## 1. 개요

본 스크립트는 특정 기업 정보 사이트에서 원하는 조건의 기업 데이터를 자동으로 검색하고 수집하기 위해 개발되었습니다. 특히, 대표자의 연령, 특정 인증(메인비즈, 이노비즈 등) 보유 여부 등 복합적인 필터를 적용하여 타겟 기업 목록을 추출하고, 결과를 파일로 저장하는 것을 목표로 합니다.

가장 큰 특징은 웹 자동화 로직(클릭, 입력 등)이 코드에 하드코딩되어 있지 않고, **외부 Excel 설정 파일**을 통해 정의된다는 점입니다. 이를 통해 개발 지식이 없는 사용자도 Excel 파일 수정만으로 손쉽게 자동화 흐름을 변경하거나 유지보수할 수 있습니다.

## 2. 주요 기능

- **Excel 기반 동작 정의**: 웹사이트에서의 모든 사용자 행동(클릭, 텍스트 입력, 마우스 오버 등)을 Excel 파일에 정의하여 사용합니다.
- **동적 웹 자동화**: 정의된 Excel 시트를 순차적으로 읽어 Selenium, Playwright 등의 라이브러리를 통해 웹 자동화를 수행합니다.
- **상세 조건 필터링**: 다음과 같은 특정 조건으로 기업을 필터링합니다.
    - 대표자 연령대 (예: 60대 ~ 70대)
    - 정부 인증 정보 (메인비즈, 이노비즈 미보유 기업)
    - 기타 필요한 비즈니스 조건
- **데이터 추출 및 저장**: 필터링된 기업의 정보를 수집하여 CSV 또는 Excel 파일로 다운로드합니다.
- **모듈식 및 확장 가능한 구조**: 기능별 모듈화가 용이하여 새로운 검색 조건을 추가하거나 다른 사이트에 적용하기 편리합니다.

## 3. 아키텍처

본 스크립트는 3가지 주요 구성 요소로 이루어집니다.

1.  **동작 정의서 (`actions.xlsx`)**: 자동화 흐름, 데이터 추출, 반복 로직을 모두 정의하는 Excel 파일입니다.
2.  **자동화 실행 엔진 (`corp_info.py`)**: `actions.xlsx` 파일을 읽어 웹 자동화를 실제로 수행하는 메인 스크립트입니다.
3.  **웹 드라이버 (WebDriver)**: `corp_info.py`의 명령에 따라 웹 브라우저를 제어하는 인터페이스입니다.

```
┌─────────────────────────┐      ┌───────────────────────────┐      ┌──────────────────┐
│  actions.xlsx           │      │  corp_info.py             │      │  Web Browser     │
│  (사용자 동작 시나리오)   │──읽기→│  (자동화 실행 엔진)       │──제어→│  (Target Website)│
└─────────────────────────┘      └───────────────────────────┘      └──────────────────┘
```

### `actions.xlsx` 파일 구조 예시

자동화 동작은 `입력`, `액션`, `읽기`, `제어`의 4가지 타입으로 확장된 `Action Type`을 통해 관리됩니다. `Output Variable` 열이 추가되어 `읽기` 동작의 결과를 변수로 저장하고, 후속 단계에서 활용할 수 있습니다.

| Step | UI Element Name | Action Type | Locator (XPath) | Value | Output Variable |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | 사이트 접속 | `navigate` | | `https://example-corp-info.com/search` | |
| 2 | 상세검색 버튼 | `click` | `//button[@id='adv-search']` | | |
| 3 | 대표자 최소연령 | `input` | `//input[@name='ceo_age_min']` | `60` | |
| 4 | 대표자 최대연령 | `input` | `//input[@name='ceo_age_max']` | `79` | |
| 5 | 메인비즈 인증 해제 | `uncheck` | `//input[@id='cert-mainbiz']` | | |
| 6 | 이노비즈 인증 해제 | `uncheck` | `//input[@id='cert-innobiz']` | | |
| 7 | 검색 실행 버튼 | `click` | `//button[@class='search-submit']` | | |
| 8 | 검색 결과 로딩 대기 | `wait` | `//div[@class='search-results']` | `30` | |
| 9 | 결과 페이지 반복 시작 | `loop_start`| | `max_pages=5` | |
| 10 | 현재 페이지 번호 읽기 | `read_text` | `//span[@class='current-page-num']` | | `current_page_num` |
| 11 | 기업 목록 테이블 읽기 | `read_table`| `//table[@id='corp-results']` | | `page_corp_data` |
| 12 | 읽은 데이터 누적 | `accumulate`| `page_corp_data` | `all_corp_data` | |
| 13 | 다음 페이지 버튼 클릭 | `click_next`| `//a[@class='pagination-next' and not(@disabled)]` | | |
| 14 | 결과 페이지 반복 종료 | `loop_end` | | | |
| 15 | 최종 데이터 필터링 | `run_filter`| `filter_ceo_age_and_cert` | `all_corp_data` | `filtered_final_data` |
| 16 | 필터링된 데이터 저장 | `save_csv` | `filtered_corp_data.csv` | `filtered_final_data` | |
| 17 | 특정 기업명 추출 | `read_text` | `//h1[@class='corp-name']` | | `company_name_example` |
| 18 | 특정 속성 (링크) 추출 | `read_attribute` | `//a[@id='corp-homepage-link']` | `href` | `company_homepage` |
| 19 | 특정 경고 메시지 확인 | `read_text` | `//div[@class='warning-message']` | | `warning_msg` |


- **Action Type 확장**:
    - **`navigate`**: 지정된 URL(`Value`)로 이동합니다.
    - **`input`**: 텍스트를 입력합니다.
    - **`click`**: 요소를 클릭합니다.
    - **`wait`**: 특정 요소가 나타날 때까지 대기합니다.
    - **`read_text`**: 요소의 텍스트를 읽어 `Output Variable`에 저장합니다.
    - **`read_table`**: `<table>` 전체를 읽어 `Output Variable`에 (e.g., DataFrame 형태로) 저장합니다.
    - **`read_list`**: 여러 요소의 텍스트 목록을 읽어 `Output Variable`에 저장합니다.
    - **`loop_start`**: 반복 블록을 시작합니다. `Value`는 최대 반복 횟수를 의미합니다.
    - **`loop_end`**: 반복 블록을 종료합니다.
    - **`click_next`**: 다음 페이지 버튼처럼, 클릭 후 비활성화되면 자동으로 `loop`를 탈출하는 특별한 클릭 액션입니다.
    - **`accumulate`**: `loop` 안에서 읽은 임시 데이터를 최종 결과 변수에 누적합니다.
    - **`run_filter`**: 수집된 데이터에 대해 `Value`에 명시된 사용자 정의 필터링 함수를 실행합니다.
    - **`save_csv`**: `Output Variable`에 저장된 데이터를 CSV 파일로 저장합니다.

## 4. 동작 흐름

1.  스크립트(`corp_info.py`)가 실행됩니다.
2.  `pandas` 라이브러리를 사용하여 `actions.xlsx` 파일을 로드하고, 데이터 저장을 위한 내부 변수 공간(e.g., 딕셔너리)을 초기화합니다.
3.  웹 드라이버(예: ChromeDriver)를 초기화합니다.
4.  Excel 파일의 `Step` 순서에 따라 각 행을 순회하는 메인 루프를 시작합니다.
5.  **Action Type에 따라 분기 처리**:
    - **입력/액션 (`input`, `click`, `navigate` 등)**: `Locator`로 요소를 찾아 `Value`를 이용해 동작을 수행합니다.
    - **읽기 (`read_table`, `read_text` 등)**: `Locator`로 요소를 찾아 데이터를 추출한 뒤, `Output Variable`에 지정된 이름으로 내부 변수 공간에 저장합니다.
    - **제어 (`loop_start`, `click_next` 등)**:
        - `loop_start`를 만나면, 내장된 서브 루프를 시작합니다.
        - `click_next`가 `loop` 내에서 실행될 때, 클릭할 버튼이 없거나 비활성화 상태이면 서브 루프를 중단시킵니다.
        - `loop_end`를 만나면 서브 루프를 종료합니다.
    - **데이터 처리 (`accumulate`, `run_filter`, `save_csv` 등)**:
        - `accumulate`: `Value`에 지정된 변수의 데이터를 `Output Variable` 변수에 누적합니다.
        - `run_filter`: `Output Variable`의 데이터에 `Value` 이름의 필터 함수를 적용하고 결과를 다시 저장합니다.
        - `save_csv`: `Output Variable`의 최종 데이터를 `Value`에 지정된 파일 이름으로 저장합니다.
6.  모든 `Step`이 완료되면 웹 드라이버를 안전하게 종료합니다.

## 5. 사전 준비 사항

- Python 3.8 이상
- 필요한 Python 라이브러리 설치:
  ```bash
  pip install pandas openpyxl selenium
  ```
- 시스템에 맞는 WebDriver(예: ChromeDriver) 설치 및 경로 설정

## 6. 사용법

1.  대상 웹사이트의 구조에 맞게 `actions.xlsx` 파일의 내용을 작성합니다.
2.  터미널에서 아래 명령어를 실행하여 스크립트를 시작합니다.
    ```bash
    python corp_info.py
    ```
