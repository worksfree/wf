# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 역할

웹 자동화 및 웹 관련 스크립트 모음.

## 폴더 목록

| 폴더 | 내용 |
|------|------|
| `kstartup-web/` | K-Startup 웹사이트 자동화 (Selenium 기반) |
| `learn_investment/` | 투자 학습 관련 웹 스크립트 |
| `시연/` | 데모/시연용 웹 스크립트 |

## kstartup-web

K-Startup 포털 웹 자동화 스크립트. 주요 문서:
- `README.md` — 프로젝트 개요 및 실행 방법
- `ELEMENT_CLICK_INTERCEPTED_FIX.md` — `ElementClickInterceptedException` 해결 가이드
- `ELEMENT_FINDING_DIAGNOSTIC_GUIDE.md` — 요소 탐색 진단 가이드
- `IMAGE_CLICK_WEB_SCENARIOS.md` — 이미지 기반 클릭 시나리오

Selenium WebDriver 기반. 요소 탐색 실패 및 클릭 인터셉트 이슈가 빈번하므로 위 가이드 문서를 참고.

---

## 웹 접근성 (GS 인증 / KWCAG 2.2) — 전체 웹 개발 공통 필수

`70.webs/` 아래 **모든 사용자 대면 웹 페이지**는 아래 항목을 준수한다. GS 인증(SW 품질) 및 한국형 웹 콘텐츠 접근성 지침(KWCAG)을 기준으로 한다. 신규 페이지·컴포넌트 작성 시 반드시 반영하고, 위반이 없는지 배포 전 점검한다.

### 1. 인식의 용이성 (Perceivable)
- **대체 텍스트(1.1.1)**: 모든 `<img>` 에 의미 있는 `alt`. 장식용 이미지·인라인 SVG 는 `alt=""` 또는 `aria-hidden="true"`. 의미 있는 SVG 는 `role="img"` + `aria-label`.
- **표의 구성(1.3.1)**: 데이터 표의 `<th>` 에 `scope="col|row"`, 가능하면 `<caption>`(시각적 숨김 가능). 레이아웃 목적의 표 금지.
- **명도 대비(1.4.3)**: 일반 텍스트 **4.5:1 이상**, 큰 텍스트(≥18pt 또는 14pt bold) 3:1 이상. 링크·강조색도 텍스트로 쓰이면 4.5:1 확보. (예: 옅은 회색/골드를 텍스트로 쓰지 말 것 — 계산 후 사용)

### 2. 운용의 용이성 (Operable)
- **키보드 접근(2.1.1)**: 마우스로 되는 모든 기능은 키보드로도 가능해야 함. **hover 전용 메뉴/툴팁 금지** → `:focus-within`/`:focus-visible` 병행, 필요 시 상위 요소에 `tabindex="0"`.
- **정지·일시정지(2.2.2)**: 자동으로 움직이는 콘텐츠(캐러셀·자동 슬라이드 등)는 hover/focus 시 멈추거나 정지 컨트롤 제공.
- **반복 영역 건너뛰기(2.4.1)**: 페이지 상단에 "본문 바로가기(skip nav)" 링크 + 본문 `<main id="main">`.
- **포커스 시각화(2.4.7)**: `:focus-visible` 로 명확한 포커스 링(윤곽선) 제공. `outline:none` 만 두고 대체 없는 것 금지.

### 3. 이해의 용이성 (Understandable)
- **언어 표시**: `<html lang="ko">` 필수. 문서 내 다른 언어 구간은 `lang` 로 표시(고유명사는 예외 허용).
- **레이블 제공(3.3.2)**: 모든 폼 컨트롤은 `<label for>`/`aria-label`/`aria-labelledby` 로 **프로그래밍적 연결**. 시각적 인접만으로 부족.
- **오류 정정(3.3.1)**: 입력 오류는 `aria-invalid` + `aria-describedby` 로 메시지에 연결, 정정 방법 안내.

### 4. 견고성 (Robust)
- **이름·역할·값(4.1.2)**: 커스텀 위젯(탭·아코디언·드롭다운·모달)은 적절한 ARIA role/state 부여. 탭 = `role="tablist/tab/tabpanel"` + `aria-selected`. 모달 = `role="dialog"` + `aria-modal` + 포커스 트랩 + ESC 닫기.
- **상태 메시지(4.1.3)**: 동적으로 나타나는 알림/폼 결과는 `role="status"`/`aria-live="polite"`(오류는 `assertive`) 로 스크린리더에 전달.
- **유효한 마크업**: 태그 닫힘·중복 id 금지·유효한 속성.

### 구현 팁 (lifeart-web 참고 패턴)
- **전역 자동 보강은 `assets/layout.js` 에 모아 둔다** — 전 페이지에서 1회 실행되어 다음을 자동 처리: `.form-row` 라벨↔입력 `for/id` 연결, 폼 `aria-describedby`, 표 `th scope`, 탭 ARIA role, `.form-msg` 라이브 영역화. 신규 폼/표/탭은 같은 클래스만 쓰면 자동 적용됨.
- **skip nav·`<main>` 랜드마크**는 `deploy.ps1` 의 헤더/푸터 인라인 주입 단계에서 자동 삽입. 공통 `header.html` 에 skip 링크와 `<nav aria-label>`.
- **명도 대비**는 `:root` CSS 변수에서 관리(텍스트로 쓰는 색은 배경 대비 4.5:1 검증 후 확정).
- 배포 전 회귀 점검: `lifeart-web/tests/full-check.js` 가 전 페이지 로드·콘솔에러·CLS·헤더 인라인을 자동 검사(패턴 재사용 권장).

> 미완/후속(신규 위젯 도입 시 유의): 완전한 모달 포커스 트랩, 캐러셀 명시적 정지 버튼, 영문 구간 `lang` 세분화, `aria-current` 로 현재 위치 표시.
