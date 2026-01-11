# 로그인 후 요소 찾기 진단 가이드

## 문제 현황
로그인 후 요소를 찾지 못하는 이유:
1. **iframe 내부에 요소가 있음** - DOM에 iframe이 추가됨
2. **XPath/CSS 선택자가 변경됨** - 로그인 전후로 HTML 구조가 다름
3. **요소가 동적으로 로드됨** - JavaScript로 나중에 추가되는 요소
4. **요소가 숨겨짐** - `display:none` 또는 `visibility:hidden`
5. **URL이 변경됨** - 로그인 후 다른 페이지로 리다이렉트됨

---

## 자동 진단 기능

### 1️⃣ 로그인 후 자동 페이지 정보 출력
로그인(Step 2) 완료 후 자동으로 다음 정보가 출력됩니다:

```
📊 페이지 상세 정보:
URL: https://k-startup.go.kr/...
제목: K-Startup ...
열린 창: 1
페이지 소스 크기: 123456 bytes
iframe: 3개
버튼: 5개, 링크: 12개, 입력필드: 8개
```

**확인 항목:**
- ✓ URL이 예상한 페이지인가?
- ✓ iframe이 새로 추가되었는가?
- ✓ 버튼/링크 개수가 달라졌는가?

---

### 2️⃣ 요소 찾기 실패 시 자동 진단
요소를 찾지 못하면 자동으로 다음 정보가 출력됩니다:

```
🔍 요소 찾기 진단: //button[contains(text(), '저장')]
현재 URL: https://k-startup.go.kr/...
현재 페이지 제목: K-Startup
창 핸들 개수: 1
현재 페이지 iframe 개수: 2
  [1] id='mainFrame' name='main'
  [2] id='contentFrame' name='content'
❌ XPath에 일치하는 요소가 없음
```

**진단 결과 해석:**
- `✓ 요소 발견:` - XPath는 맞지만 접근 방법이 잘못됨
- `❌ XPath에 일치하는 요소가 없음:` - XPath를 수정해야 함
- `iframe 개수:` - iframe 안에 있는지 확인

---

### 3️⃣ 수동 진단 명령어

#### 현재 페이지 상태 확인
```python
show_page_status()
```
**출력:**
- 현재 URL, 제목
- 페이지 크기
- iframe 정보
- 버튼, 링크, 입력필드 개수

#### 모든 링크 보기
```python
show_all_links()
```
**출력:** 처음 20개 링크의 텍스트, href, 표시 여부

#### 모든 버튼 보기
```python
show_all_buttons()
```
**출력:** 처음 20개 버튼의 텍스트, 표시 여부

#### 특정 요소 진단
```python
# 예시 1: 텍스트가 '저장'인 버튼
diagnose_element("//button[contains(text(), '저장')]")

# 예시 2: id가 'saveBtn'인 요소
diagnose_element("//*[@id='saveBtn']")

# 예시 3: CSS로 진단 (변환 필요)
# CSS: button.primary → XPath: //button[@class='primary']
diagnose_element("//button[@class='primary']")
```

**진단 결과:**
```
🔍 요소 찾기 진단: //button[contains(text(), '저장')]
현재 URL: ...
현재 페이지 제목: ...
현재 페이지 iframe 개수: 2
✓ 요소 발견: 1개
  [1] button | 표시: True | 활성: True | 텍스트: 저장
```

---

## 단계별 해결 방법

### 😞 상황: 요소를 찾을 수 없음

#### Step 1️⃣: 페이지 상태 확인
```python
show_page_status()
```

**Q: URL이 로그인 전과 다른가?**
- ✓ Yes → 로그인 후 새로운 페이지로 이동했음. Excel 설정의 XPath/CSS를 새 페이지에 맞게 수정 필요
- ✗ No → Step 2로 진행

**Q: iframe 개수가 증가했는가?**
- ✓ Yes → iframe 안의 요소를 찾아야 함 (Step 3으로 진행)
- ✗ No → Step 2로 진행

#### Step 2️⃣: 개발자 도구에서 XPath 재확인
1. 브라우저에서 **F12** 키를 눌러 개발자 도구 열기
2. **Elements** 탭에서 Ctrl+F로 요소 검색
3. 요소를 찾으면 우클릭 → **Copy XPath** 또는 **Copy selector**
4. Excel의 XPath/CSS 칼럼을 새로운 값으로 업데이트
5. 다시 실행

#### Step 3️⃣: iframe 안의 요소 찾기
iframe이 있으면:
```python
# 현재 iframe 나열
show_page_status()  # iframe 정보 확인

# 개발자 도구에서:
# 1. Elements 탭의 <iframe> 태그 클릭
# 2. iframe 내부의 HTML을 확인
# 3. iframe 내부에서 XPath 복사
```

**Excel 설정:**
- 단순 요소: XPath 그대로 사용 (자동으로 iframe 감지)
- iframe 직접 지정: `iframe_name` 또는 `iframe_id` 칼럼 추가

---

## 일반적인 원인과 해결법

### 🔴 "Timeout" 또는 "NoSuchElement" 에러

| 원인 | 진단 방법 | 해결법 |
|------|---------|--------|
| **iframe 안에 요소** | `show_page_status()`에서 iframe 확인 | XPath가 맞으면 자동 감지됨 |
| **XPath 틀림** | `diagnose_element(xpath)`로 확인 | 개발자 도구에서 다시 복사 |
| **요소가 동적 로드** | 페이지 로드 후 시간 경과 필요 | Excel의 `대기시간` 칼럼 증가 |
| **요소가 숨겨짐** | `diagnose_element()`에서 "표시: False" | CSS 확인, 요소의 부모 확인 |
| **다른 창으로 이동** | `show_page_status()`에서 URL 확인 | 창 전환 필요 |

---

## 실제 예시

### 예시 1: 로그인 후 페이지 변경

```
로그인 전: https://k-startup.go.kr/login
로그인 후: https://k-startup.go.kr/mypage
```

**해결:**
1. `show_page_status()` 실행 → URL 확인
2. 개발자 도구(F12)에서 새 페이지의 XPath 복사
3. Excel의 XPath 업데이트

### 예시 2: iframe 안의 요소

```
show_page_status() 출력:
iframe: 1개
  [1] id='contentFrame' name='content'

하지만 버튼: 0개  ← 버튼이 보이지 않음!
```

**진단:**
1. iframe 안을 확인: 개발자 도구에서 `<iframe id="contentFrame">` 클릭
2. iframe 내부에서 버튼 찾기
3. XPath는 자동으로 감지됨

### 예시 3: XPath 오류

```python
diagnose_element("//button[@id='save']")

출력:
❌ XPath에 일치하는 요소가 없음
💡 시도:
   1. XPath가 정확한지 개발자 도구(F12)에서 확인
   2. 요소가 iframe 안에 있는지 확인
```

**해결:**
1. 개발자 도구에서 `Copy XPath` 다시 수행
2. 맞는 XPath: `//button[contains(text(), '저장')]`로 업데이트

---

## 디버그 로그 읽는 방법

### 로그 수준
- 🔵 `DEBUG`: 세부 디버깅 정보 (일반 사용자는 무시)
- ℹ️ `INFO`: 일반 진행 상황
- ⚠️ `WARNING`: 주의 필요 (로그인 실패, 팝업 없음 등)
- 🔴 `ERROR`: 심각한 오류 (요소를 찾지 못함 등)

### 주요 로그 메시지

| 메시지 | 의미 | 해결법 |
|--------|------|--------|
| `[LOCATE] 요소 찾기 시작` | 요소 검색 중 | 정상 진행 중 |
| `[LOCATE] ✓ 요소 발견 성공` | 요소를 찾음 | 정상 |
| `[LOCATE] ❌ Timeout` | 요소를 찾지 못함 | 진단 실행 |
| `현재 페이지 iframe 개수: 2` | iframe 정보 | iframe 확인 필요 |
| `✓ 요소 발견: 1개` | 요소가 존재함 | XPath 맞음 |
| `❌ XPath에 일치하는 요소가 없음` | DOM에 없음 | XPath 수정 필요 |

---

## FAQ

**Q: 로그인 후 처음부터 모든 요소를 찾을 수 없습니다**
- A: Step 1: `show_page_status()`로 URL 및 iframe 확인
- A: Step 2: 개발자 도구에서 요소 위치 재확인
- A: Step 3: Excel XPath/CSS 모두 업데이트

**Q: iframe은 있는데 요소를 여전히 찾을 수 없습니다**
- A: `diagnose_element("//button[text()]")`로 iframe 내부의 모든 버튼 검색
- A: 개발자 도구에서 iframe 내부를 더블클릭하여 내부 HTML 확인

**Q: 요소가 보이는데 "표시: False"라고 나옵니다**
- A: CSS 확인: `display: none`이거나 `visibility: hidden`
- A: 부모 요소도 숨겨져 있을 수 있음
- A: 다른 버튼이나 요소로 대체할 수 있는지 확인

**Q: 매번 다른 XPath를 사용해야 합니다**
- A: 요소의 ID나 name이 있으면 사용 (더 안정적)
- A: 텍스트 기반: `//button[contains(text(), '저장')]`
- A: CSS class 사용: `//button[@class='primary']`

---

## 요약

| 단계 | 작업 | 명령 |
|------|------|------|
| **1. 로그인** | Step 2 실행 | `login()` |
| **2. 페이지 확인** | 자동으로 출력됨 | 로그 확인 |
| **3. 요소 찾기** | Step 3 실행 시도 | `execute_actions()` |
| **4. 실패 시** | 진단 유틸리티 실행 | `show_page_status()` |
| **5. XPath 수정** | 개발자 도구에서 확인 | F12 키 |
| **6. Excel 수정** | 새 XPath/CSS 입력 | Config 시트 업데이트 |
| **7. 재실행** | Step 3 다시 실행 | `execute_actions()` |

---

## 문제 해결 못하셨을 때

1. **로그 파일 확인**: 콘솔 출력 전체 복사
2. **진단 결과 확인**:
   ```python
   show_page_status()
   show_all_links()
   diagnose_element("//button")
   ```
3. **스크린샷**: 개발자 도구에서 Elements 탭 스크린샷
4. **정보 제공**: 로그 + 스크린샷 + Excel 설정

---

**마지막 팁**: 안정성을 위해 ID나 class 기반 XPath를 사용하세요!
```
❌ 불안정: //button[3]/following-sibling::a
✅ 안정적: //button[@id='saveBtn']
✅ 안정적: //button[@class='primary-action']
```
