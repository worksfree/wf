# K-Startup 웹 자동화 (simple_test.py)

Excel 기반의 웹 자동화 스크립트입니다. K-Startup 플랫폼에서 반복적인 업무를 자동화합니다.

---

## 📋 목차

1. [개요](#개요)
2. [설치 및 환경 설정](#설치-및-환경-설정)
3. [Excel 파일 구조](#excel-파일-구조)
4. [액션 타입 상세](#액션-타입-상세)
5. [이미지 기반 vs 엘리먼트 기반 클릭](#이미지-기반-vs-엘리먼트-기반-클릭)
6. [loop_click (반복 파일 업로드)](#loop_click-반복-파일-업로드)
7. [텍스트 입력 방식](#텍스트-입력-방식)
8. [iframe 처리](#iframe-처리)
9. [개발 중 발생한 이슈 및 해결](#개발-중-발생한-이슈-및-해결)
10. [XPath 작성 가이드](#xpath-작성-가이드)

---

## 개요

### 주요 기능
- **Excel 기반 시나리오 정의**: Config와 Actions 시트로 자동화 흐름 정의
- **다양한 클릭 방식**: 엘리먼트 클릭, XPath 클릭, 이미지 클릭 지원
- **파일 반복 업로드**: `loop_click`으로 여러 파일 순차 업로드
- **한글 입력 지원**: `copy_text`로 클립보드를 통한 한글 경로 입력
- **iframe 전환**: 중첩된 iframe 내 요소 접근
- **TEST_MODE**: 실제 실행 없이 시나리오 검증

### 의존성
```bash
pip install openpyxl selenium pyautogui pyperclip opencv-python
```

---

## 설치 및 환경 설정

### 1. Chrome 디버깅 모드 실행
```powershell
chrome.exe --remote-debugging-port=9222 --user-data-dir="C:\chrome_debug"
```

### 2. 스크립트 실행
```powershell
python simple_test.py
```

### 3. TEST_MODE 설정
```python
# 스크립트 상단에서 설정
TEST_MODE = True   # 실제 실행 없이 시나리오만 검증
TEST_MODE = False  # 실제 자동화 실행
```

---

## Excel 파일 구조

### Config 시트
| 키 | 값 | 설명 |
|---|---|---|
| site_url | https://www.k-startup.go.kr | 접속할 사이트 URL |
| loop_files_folder | C:\업로드파일 | loop_click에서 사용할 파일 폴더 |
| loop_files_ext | .pdf | 대상 파일 확장자 (생략 시 .pdf) |

### Actions 시트
| 순번 | 타입 | 액션명 | XPath | 값 | 대기시간 |
|-----|------|--------|-------|-----|---------|
| 1 | click | 로그인 버튼 | //*[@id="login"] | | 2 |
| 2 | input | 아이디 입력 | //*[@id="userId"] | admin | |
| 22 | loop_click | 파일업로드시작 | //*[@id="addBtn"] | | |
| 22-1 | copy_text | 파일경로입력 | | {current_file} | |
| 22-2 | hotkey | 엔터 | | enter | |

> **순번 형식**: 하이픈(`-`)을 사용하여 서브 액션 정의 (예: 22-1, 22-2)

---

## 액션 타입 상세

### 클릭 계열
| 타입 | 별칭 | 설명 | XPath 필요 |
|------|------|------|-----------|
| `click` | `클릭` | 웹 요소 클릭 (Selenium) | ✓ |
| `xpath_click` | `xp_click`, `xpath클릭` | XPath 요소 직접 클릭 | ✓ |
| `image_click` | `이미지클릭` | 이미지 인식 클릭 (pyautogui) | ✗ (값에 이미지 경로) |
| `loop_click` | `루프클릭`, `repeat_click` | 파일 수만큼 반복 클릭 | ✓ |

### 입력 계열
| 타입 | 별칭 | 설명 | 한글 지원 |
|------|------|------|----------|
| `input` | `입력` | 웹 요소에 직접 입력 (send_keys) | ✓ |
| `type_text` | `텍스트입력`, `keyboard_input` | pyautogui 타이핑 (ASCII만) | ✗ |
| `copy_text` | `복사붙여넣기`, `paste_text` | 클립보드 붙여넣기 (Ctrl+V) | ✓ |
| `hotkey` | `핫키`, `windows_key` | 키보드 단축키 | - |

### 탐색/대기 계열
| 타입 | 별칭 | 설명 |
|------|------|------|
| `wait` | `대기` | 고정 시간 대기 (초) |
| `wait_element` | `요소대기` | 요소 나타날 때까지 대기 |
| `scroll` | `스크롤` | 페이지 스크롤 |
| `switch_window` | `창전환` | 브라우저 창 전환 |
| `switch_site` | `사이트이동` | URL 이동 |

### iframe 계열
| 타입 | 별칭 | 설명 |
|------|------|------|
| `iframe_in` | `frame_in`, `프레임진입` | iframe 내부로 진입 |
| `iframe_out` | `frame_out`, `프레임복귀` | iframe에서 복귀 |

---

## 이미지 기반 vs 엘리먼트 기반 클릭

### 엘리먼트 기반 클릭 (권장)
```
타입: click 또는 xpath_click
XPath: //*[@id="submitBtn"]
```

**장점:**
- 해상도/DPI 무관
- 정확한 요소 식별
- 에러 핸들링 용이

**단점:**
- iframe 내부 요소는 프레임 전환 필요
- 동적 ID 처리 필요

### 이미지 기반 클릭
```
타입: image_click
값: images/submit_button.png
```

**장점:**
- 복잡한 XPath 불필요
- 네이티브 대화상자 클릭 가능

**단점:**
- 해상도/테마 변경 시 이미지 업데이트 필요
- confidence 조정 필요 (기본 0.8)
- 화면에 보여야만 클릭 가능

### 언제 어떤 방식을 사용할까?

| 상황 | 권장 방식 |
|------|----------|
| 일반 웹 버튼/링크 | `click` 또는 `xpath_click` |
| Windows 파일 대화상자 | `image_click` + `copy_text` |
| 동적 팝업 버튼 | `xpath_click` (contains 사용) |
| Canvas 요소 | `image_click` |

---

## loop_click (반복 파일 업로드)

### 개념
`loop_click`은 지정된 폴더의 파일 수만큼 클릭을 반복하고, 각 반복마다 서브 액션을 실행합니다.

### Excel 설정 예시
```
순번   타입         액션명          XPath                    값
22     loop_click   파일추가시작    //*[@id="addFileBtn"]    
22-1   copy_text    파일경로입력                             {current_file}
22-2   hotkey       엔터입력                                 enter
22-3   wait         대기                                     1
```

### 동작 순서
1. Config의 `loop_files_folder`에서 파일 목록 수집
2. 각 파일에 대해:
   - 메인 액션 (22번 - 파일추가 버튼 클릭)
   - 서브 액션 순차 실행 (22-1, 22-2, 22-3)
   - `{current_file}` → 현재 파일 경로로 치환

### Config 설정
```
키                   값
loop_files_folder    D:\업로드파일\증빙서류
loop_files_ext       .pdf
```

### 서브 액션에서 지원하는 타입
- `copy_text`: 파일 경로 붙여넣기 (한글 지원)
- `type_text`: ASCII 텍스트 입력
- `hotkey`: 키보드 단축키 (enter, tab 등)
- `wait`: 대기
- `click`: 요소 클릭

---

## 텍스트 입력 방식

### type_text (ASCII 전용)
```python
# 내부 동작
pyautogui.typewrite("500000", interval=0.05)
```

**특징:**
- XPath 있으면 요소 클릭 → Ctrl+A (기존 텍스트 선택) → 타이핑
- 숫자, 영문만 지원
- 한글은 깨짐

**사용 예시:**
```
타입: type_text
XPath: //*[@id="price"]
값: 500000
```

### copy_text (한글 지원)
```python
# 내부 동작
pyperclip.copy("D:\파일\증빙서류.pdf")
pyautogui.hotkey('ctrl', 'v')
```

**특징:**
- 클립보드를 통해 붙여넣기
- 한글 파일 경로 완벽 지원
- Windows 파일 대화상자에서 사용

**사용 예시:**
```
타입: copy_text
값: D:\업로드\증빙서류.pdf
또는
값: {current_file}
```

### 사용 구분
| 입력 내용 | 권장 타입 |
|----------|----------|
| 숫자 (공급가, 부가세) | `type_text` |
| 한글 파일 경로 | `copy_text` |
| 영문 텍스트 | `type_text` 또는 `input` |
| 웹 폼 입력 | `input` |

---

## iframe 처리

### iframe 진입
```
순번   타입       액션명           XPath                               값
24     iframe_in  프레임진입       //*[@id="raonkupload_context_menu"]
25     click      확인버튼         //button[text()='예']
26     iframe_out 프레임복귀
```

### 값으로 iframe 지정
```
타입: iframe_in
값: id:raonkupload_context_menu
또는
값: name:uploadFrame
또는
값: index:0
```

### iframe_out 옵션
| 값 | 설명 |
|---|------|
| (빈값) | 최상위(루트)로 복귀 |
| parent | 한 단계 상위로 복귀 |
| levels:2 | 2단계 상위로 복귀 |

---

### ⚠️ Cross-origin iframe 처리

#### 문제 상황
K-Startup 사이트에는 보안을 위한 Cross-domain iframe이 존재합니다:
```html
<iframe title="Cross Domain Process" 
        src="https://pms.k-startup.go.kr/biz/static/3rdparty/initech/webui/crossd_iframe.html"
        style="position: absolute; width: 1px; height: 1px; left: -9999px; top: -9999px;">
</iframe>
```

이런 iframe은:
- **화면 밖에 숨겨짐** (left: -9999px)
- **크기가 매우 작음** (1x1px)
- **Cross-origin 정책**으로 DOM 접근 차단
- **자동화 대상이 아님** (보안 프로세스용)

#### 자동 감지 및 경고
스크립트가 자동으로 감지하여 경고를 표시합니다:
```
⚠️ Cross-domain 프로세스 iframe 감지: https://pms.k-startup.go.kr/.../crossd_iframe.html
   → 이 iframe은 접근이 제한될 수 있습니다. 필요 없다면 건너뛰세요.
❌ Cross-origin iframe 접근 거부
   → 해결책: 1) iframe_out으로 복귀 2) 다른 방법 사용 3) 이 단계 건너뛰기
```

#### 대응 방법

**방법 1: iframe 진입 액션 제거**
```excel
# 불필요한 Cross-origin iframe 진입은 삭제
# ❌ 24  iframe_in  크로스도메인  //*[@title='Cross Domain Process']
   25  click      실제작업       //*[@id="submitBtn"]
```

**방법 2: 조건부 실행 (try-except)**
스크립트가 자동으로 실패 시 루트로 복귀하므로, 다음 액션을 계속 진행합니다.

**방법 3: 올바른 iframe 선택**
```excel
# 작업 대상이 되는 실제 iframe을 찾아서 진입
순번   타입       XPath/값
24     iframe_in  //*[@id="mainContent"]    ← 실제 작업 영역 iframe
25     click      //*[@id="submitBtn"]      ← iframe 내부 요소
26     iframe_out (빈값)                    ← 루트로 복귀
```

#### 숨겨진 iframe 식별 팁
Chrome DevTools에서 확인:
1. F12 → Elements 탭
2. iframe 태그 검색 (`Ctrl+F` → `iframe`)
3. 각 iframe의 속성 확인:
   - `style="left: -9999px"` → 숨겨진 iframe (건너뛰기)
   - `id="mainContent"` 등 명확한 ID → 작업 대상 iframe

---

## 개발 중 발생한 이슈 및 해결

### 1. 숫자 0 전달 문제 ⚠️

**증상:**
```
[ERROR] type_text에 텍스트(값)가 필요합니다
```
부가세 `0` 입력 시 값이 없는 것으로 처리됨

**원인:**
```python
# 기존 코드 (문제)
raw_value = action.get('값') or action.get('value')
# 0 or None → 0은 falsy이므로 None 반환

if not value:  # 0은 falsy이므로 True
    raise ValueError('텍스트가 필요합니다')
```

**해결:**
```python
# 수정된 코드
raw_value = action.get('값')
if raw_value is None:
    raw_value = action.get('value')

if value is None or value == '':  # 0은 통과
    raise ValueError('텍스트가 필요합니다')
```

**교훈:** Python의 `or` 연산자는 falsy 값(0, '', [], {}, None, False)에 주의

---

### 2. 서브 액션 미인식 문제

**증상:**
```
🔁 loop_click 시작: 서브 액션 0개
```

**원인:**
Excel 헤더가 `순번`인데 코드에서 `번호`만 인식

**해결:**
```python
def canonical_key(h):
    if key in ('번호', '순번', 'no', 'num', 'number', 'index', 'idx'):
        return '번호'
```

---

### 3. 동적 ID 문제 ⚠️

**증상:**
```
[ERROR] Timeout: //*[@id="confirm45024887582530795_btn_message"]
```
세션마다 ID의 숫자 부분이 변경됨

**원인:**
```
//*[@id="confirm45024887582530795_wframe_gen_btnArea_0_btn_message"]
                 ^^^^^^^^^^^^^^^^^ 동적 생성 숫자
```

**해결 방법:**

1. **contains() 사용:**
```xpath
//*[contains(@id, 'btn_message') and contains(@id, 'confirm')]
```

2. **텍스트로 찾기:**
```xpath
//button[text()='예'] | //a[text()='예']
```

3. **Union 연산자:**
```xpath
//*[contains(@id, 'btn_message')] | //button[text()='예']
```

**권장:** 가능하면 텍스트 기반 XPath 사용

---

### 4. 한글 파일 경로 깨짐

**증상:**
```
D:\??????\??????.pdf
```

**원인:**
`pyautogui.typewrite()`는 ASCII만 지원

**해결:**
`copy_text` 타입 추가 (pyperclip + Ctrl+V)
```python
def copy_text(text_str):
    pyperclip.copy(text_str)
    pyautogui.hotkey('ctrl', 'v')
```

---

### 5. type_text가 엉뚱한 곳에 입력

**증상:**
공급가 입력이 다른 필드에 들어감

**원인:**
`type_text`가 현재 포커스된 곳에 입력

**해결:**
XPath가 있으면 먼저 요소 클릭 → Ctrl+A → 타이핑
```python
if xpath:
    elem = locate()
    elem.click()
    time.sleep(0.3)
    pyautogui.hotkey('ctrl', 'a')  # 기존 텍스트 선택
```

---

## XPath 작성 가이드

### 1. 고정 ID (가장 권장)
```xpath
//*[@id="submitButton"]
```
**장점:** 가장 빠르고 정확  
**단점:** 동적 ID에는 사용 불가

---

### 2. 동적 ID 처리 (실전 필수!)

#### 문제 상황
```xpath
# 이런 ID는 페이지 로드마다 변경됨
//*[@id="uuid_1451"]  ❌ 다음에 uuid_1452로 변경됨
//*[@id="button_20250111_1234"]  ❌ 시간마다 변경
```

#### 해결 방법 1: contains() - 부분 매칭 (가장 많이 사용)
```xpath
# 예시: //*[@id="mf_wfm_contents_...uuid_1451"]
//*[contains(@id, 'mf_wfm_contents')]
//*[contains(@id, 'wq_uuid_')]  ← 고정된 부분만 사용

# 복수 조건 조합
//*[contains(@id, 'submit') and contains(@id, 'btn')]
```

#### 해결 방법 2: starts-with() - 시작 부분 매칭
```xpath
//*[starts-with(@id, 'button_')]
//*[starts-with(@id, 'mf_wfm_contents_')]
```

#### 해결 방법 3: 부모 + 자식 조합
```xpath
# 안정적인 부모에서 시작
//div[@id='stable-container']//button[contains(@id, 'uuid_')]

# 여러 단계 탐색
//form[@name='userForm']//div[@class='button-group']//button[contains(@id, 'submit')]
```

#### 해결 방법 4: class 속성 사용
```xpath
//*[@class='submit-button']
//*[contains(@class, 'btn-primary')]
```

#### 해결 방법 5: 다른 속성과 조합
```xpath
# type + name
//input[@type='text' and @name='userId']

# class + data 속성
//button[@class='btn' and @data-action='submit']

# 동적 ID + 안정 속성
//*[contains(@id, 'uuid_') and @type='submit']
```

**실전 팁:**
```
동적 ID: //*[@id="mf_wfm_contents_tabCtrl_...uuid_1451"]

✅ 권장 XPath:
   //*[contains(@id, 'wq_uuid_')]
   
   또는 (더 구체적)
   //*[contains(@id, 'NBEG0112P06_wframe_wq_uuid_')]
```

---

### 3. 텍스트 기반 (매우 안정적)
```xpath
# 정확한 텍스트 매칭
//button[text()='확인']
//a[text()='다음 단계']

# 부분 텍스트 매칭
//button[contains(text(), '저장')]
//span[contains(text(), '등록')]

# 텍스트 + 상위 요소
//span[text()='저장']/parent::button
//div[contains(text(), '완료')]/ancestor::button
```

---

### 4. 복합 조건
```xpath
# AND 조건
//input[@type='text' and @name='userId']
//button[@class='btn' and contains(text(), '확인')]

# 계층 구조 + 조건
//div[@class='modal']//button[text()='확인']
//form[@id='loginForm']//input[@type='password']
```

---

### 5. 형제/부모 탐색
```xpath
# 라벨 → 입력 필드
//label[text()='이메일']/following-sibling::input

# 테이블 셀
//td[text()='합계']/following-sibling::td[1]

# 부모로 이동
//span[@class='error']/parent::div

# 조상으로 이동
//span[text()='에러']/ancestor::form
```

---

### 6. Chrome DevTools로 XPath 테스트

1. **F12** → **Elements** 탭
2. **Ctrl+F** (검색창)
3. XPath 입력:
   ```
   //*[contains(@id, 'uuid_')]
   ```
4. **결과 확인:**
   - `1 of 1` → ✅ 완벽! 하나만 찾음
   - `1 of 5` → ⚠️ 5개 중 1번째, 조건 추가 필요
   - `0 of 0` → ❌ 못 찾음, XPath 수정

**팁:** 요소에 마우스 우클릭 → **Copy** → **Copy XPath** 로 기본 XPath 확인 후 동적 부분 수정

---

### 7. XPath vs CSS Selector 선택

| 상황 | 권장 |
|------|------|
| 고정 ID | 둘 다 가능 (`#id` vs `//*[@id='id']`) |
| 동적 ID | **XPath** (contains 지원) |
| 텍스트로 찾기 | **XPath** (text() 지원) |
| 부모로 이동 | **XPath** (parent, ancestor) |
| nth-child | CSS가 더 간결 |

### 피해야 할 패턴
```xpath
# ❌ 동적 숫자 ID
//*[@id="confirm12345678_btn"]

# ❌ 너무 긴 경로
/html/body/div[3]/div[2]/div[1]/form/div/button

# ❌ 인덱스 의존
//div[5]/span[2]/button[1]
```

---

## 디버깅 팁

### 1. Chrome 개발자 도구에서 XPath 테스트
```javascript
$x('//*[@id="myElement"]')
$x('//button[text()="확인"]')
```

### 2. iframe 내부 요소 확인
개발자 도구 상단에서 iframe 선택 후 Elements 탭에서 검색

### 3. 로그 레벨 조정
```python
logging.basicConfig(level=logging.DEBUG)
```

### 4. TEST_MODE로 시나리오 검증
```python
TEST_MODE = True  # 실제 실행 없이 흐름만 확인
```

---

## 변경 이력

| 날짜 | 변경 내용 |
|------|----------|
| 2026-01-10 | copy_text 추가 (한글 경로 지원) |
| 2026-01-10 | type_text에 Ctrl+A 추가 (기존 텍스트 덮어쓰기) |
| 2026-01-10 | 숫자 0 전달 버그 수정 |
| 2026-01-10 | loop_click 서브 액션 인식 수정 (순번→번호 매핑) |
| 2026-01-09 | loop_click {current_file} 플레이스홀더 추가 |
| 2026-01-09 | iframe_in/out 깊이 추적 기능 |

---

## 라이선스

내부 사용 목적


