# WorksFree Hub — Playwright 테스트 리포트

**테스트 일시**: 2026-07-01  
**버전**: v0.8.5.32  
**환경**: mock (localhost:3001, Chromium headless)  
**총 결과**: **85 passed · 1 skipped · 0 failed** ✅

---

## 1. 실행 요약

| 항목 | 값 |
|------|-----|
| 테스트 파일 | 5개 (smoke, navigation, auth, permissions, privacy) |
| 전체 테스트 수 | 86 |
| 통과 (passed) | **85** |
| 실패 (failed) | **0** |
| 건너뜀 (skipped) | **1** |
| 소요 시간 | 약 1분 20초 |
| 브라우저 | Chromium (headless) |
| 서버 | `npx serve . -p 3001` (로컬 정적 서버) |

---

## 2. 파일별 결과

### 2.1 smoke.spec.js — 기본 페이지 로드 (10/10 통과)

| # | 테스트 | 결과 |
|---|--------|------|
| 1 | 홈 페이지 로드 — title 확인 | ✅ |
| 2 | 홈 페이지 로드 — sidebar 존재 | ✅ |
| 3 | 홈 페이지 로드 — logo 영역 존재 | ✅ |
| 4 | 홈 페이지 로드 — 로그인 버튼 표시 (비로그인) | ✅ |
| 5 | 홈 페이지 로드 — home-screen 표시 | ✅ |
| 6 | 홈 페이지 로드 — contentFrame 존재 | ✅ |
| 7 | 홈 페이지 로드 — 2초 이내 DOMContentLoaded | ✅ |
| 8 | 404 → 홈으로 폴백 (hash 라우팅) | ✅ |
| 9 | HUB_VERSION — 숫자 형식 버전 표시 | ✅ |
| 10 | HTTPS redirect 없음 (로컬 서버) | ✅ |

### 2.2 navigation.spec.js — Hub-and-Spoke 네비게이션 (19/19 통과)

| # | 테스트 | 결과 |
|---|--------|------|
| 1 | 루트 URL → home-screen 표시 | ✅ |
| 2 | 해시 URL — 유효하지 않은 slug 홈 폴백 | ✅ |
| 3 | logo → showHome 함수 존재 | ✅ |
| 4 | showSectionDash 함수 존재 | ✅ |
| 5 | navigateToHash 함수 존재 | ✅ |
| 6 | iframeToSlug 함수 존재 | ✅ |
| 7 | iframeToSlug — /index.html 제거 | ✅ |
| 8 | iframeToSlug — .html 제거 | ✅ |
| 9 | logo 요소 — onclick showHome 속성 존재 | ✅ |
| 10 | logo cursor:pointer 스타일 | ✅ |
| 11 | TREE — 소스에 6개 섹션 slug 정의됨 | ✅ |
| 12 | currentSection — 소스 선언 확인 | ✅ |
| 13 | popstate 이벤트 — navigateToHash 호출 | ✅ |
| 14 | renderHomeSections 함수 존재 | ✅ |
| 15 | DASH_CARDS — 소스에 section 필드 정의됨 | ✅ |
| 16 | renderDashCards — sectionFilter 파라미터 지원 | ✅ |
| 17 | SECTION_DESCS — 소스에 6개 섹션 설명 정의됨 | ✅ |
| 18 | _buildSectionSidebar 함수 존재 | ✅ |
| 19 | _buildFullSidebar 함수 존재 | ✅ |

### 2.3 auth.spec.js — 세션 및 인증 흐름 (25/25 통과) ⭐ 중점 검증

| # | 테스트 | 결과 |
|---|--------|------|
| 1 | 비로그인 — userRole 선언 확인 (let userRole 소스 검사) | ✅ |
| 2 | 비로그인 — authUser null (getAccessLevel 동작 간접 확인) | ✅ |
| 3 | 비로그인 — IS_PARTNER false (소스 선언) | ✅ |
| 4 | 비로그인 — preview-overlay 또는 login modal 표시 | ✅ |
| 5 | onAuthComplete 함수 존재 | ✅ |
| 6 | updateAuthUI 함수 존재 | ✅ |
| 7 | refreshTreeAndCards 함수 존재 | ✅ |
| 8 | checkConsent 함수 존재 | ✅ |
| 9 | saveConsent 함수 존재 | ✅ |
| 10 | onAuthComplete — wf_last_page 읽지 않음 (hash 라우팅 대체) | ✅ |
| 11 | hash 기반 복원 — navigateToHash 사용 (onAuthComplete 소스) | ✅ |
| 12 | hash 기반 복원 — showHome 사용 (onAuthComplete 소스) | ✅ |
| 13 | hash 없는 홈 접근 — showHome 경로 진입 | ✅ |
| 14 | hash 있는 접근 — hash 유지 | ✅ |
| 15 | canConsult — 소스에 정의됨 | ✅ |
| 16 | canConsult — consultant|partner|admin 역할 허용 소스 확인 | ✅ |
| 17 | getAccessLevel — 비로그인(member) GFC hidden 반환 | ✅ |
| 18 | Supabase 세션 — onAuthStateChange 핸들러 등록 | ✅ |
| 19 | Supabase Anon Key — 소스 내 존재 (의도적 공개, RLS 보호) | ✅ |
| 20 | Supabase Service Key — 소스에 없음 (CF Worker에만) | ✅ |
| 21 | IS_DEV 상수 존재 | ✅ |
| 22 | loadCreditBalance 함수 존재 | ✅ |
| 23 | loadPageAccessRules 함수 존재 | ✅ |
| 24 | signOut 함수 존재 | ✅ |
| 25 | 로그아웃 후 — wf_last_login localStorage 사용 | ✅ |

### 2.4 permissions.spec.js — 역할 기반 접근 제어 (22/22 통과) ⭐ 중점 검증

| # | 테스트 | 결과 |
|---|--------|------|
| 1 | TREE — admin 섹션 adminOnly:true 소스 확인 | ✅ |
| 2 | TREE — consulting 섹션 consultantOnly:true 소스 확인 | ✅ |
| 3 | TREE — finance 섹션 정의됨 | ✅ |
| 4 | TREE — service 섹션 consultantOnly 없음 (공개) | ✅ |
| 5 | TREE — pilot 섹션 타코매니저 consultantOnly 소스 확인 | ✅ |
| 6 | getAccessLevel 함수 존재 | ✅ |
| 7 | getAccessLevel — 규칙 없는 페이지 full 반환 | ✅ |
| 8 | getAccessLevel — GFC 페이지 비로그인(member) hidden 반환 | ✅ |
| 9 | getAccessLevel — GFC consultant 모의 시 내부 로직 확인 | ✅ |
| 10 | DEFAULT_ACCESS_RULES — GFC 규칙 소스 확인 | ✅ |
| 11 | DEFAULT_ACCESS_RULES — general:hidden, member:hidden 소스 확인 | ✅ |
| 12 | DEFAULT_ACCESS_RULES — consultant:blur 소스 확인 | ✅ |
| 13 | applyAccessOverlay 함수 존재 | ✅ |
| 14 | buildTree 함수 존재 | ✅ |
| 15 | 비로그인 — CEO 플랜 미노출 (DOM 확인) | ✅ |
| 16 | 비로그인 — O&M 메뉴 미노출 (DOM 확인) | ✅ |
| 17 | 비로그인 — service 메뉴 공개 (DOM 확인) | ✅ |
| 18 | pageAccessRules 소스 선언 확인 | ✅ |
| 19 | canConsult — consultant|partner|admin 허용 정의 | ✅ |
| 20 | IS_PARTNER — partner|admin 조건 소스 확인 | ✅ |
| 21 | adminOnly 플래그 — admin만 허용 코드 존재 | ✅ |
| 22 | consultantOnly 플래그 — canConsult() 통과 확인 코드 존재 | ✅ |

### 2.5 privacy.spec.js — 자산 통합 관리 숨김처리 (9/9: 8 통과 · 1 건너뜀)

| # | 테스트 | 결과 | 비고 |
|---|--------|------|------|
| 1 | asset 페이지 로드 — 기본 접근 가능 | ✅ | |
| 2 | pv-toggle — 요소 존재 | ⏭ | 비인증 접근 시 조건부 skip |
| 3 | pv-toggle — 헤더 좌측 (hdr-r 외부) | ✅ | |
| 4 | pv-toggle — hdr-info 이후에 위치 | ✅ | |
| 5 | pv-toggle — checkbox input 포함 | ✅ | |
| 6 | pv-toggle — "숨김처리" 텍스트 포함 | ✅ | |
| 7 | blur 타겟 — 금액 필드 ID 존재 | ✅ | |
| 8 | blur 토글 — 체크박스 클릭 시 blur 클래스 적용 | ✅ | |
| 9 | blur 대상 — pv- CSS 스타일 선택자 존재 | ✅ | |

> **[1 Skipped]** `pv-toggle — 요소 존재`: asset 페이지는 Hub iframe 내부에서만 완전히 동작함. 직접 URL 접근 시 비인증 상태로 인식되어 토글 미렌더링 — 조건부 `test.skip()` 처리됨.

---

## 3. 핵심 검증 항목 (세션·권한 관리)

### 3.1 세션 관리 검증 결과

| 검증 항목 | 결과 | 상세 |
|---------|------|------|
| `onAuthComplete` — 로그인 완료 콜백 존재 | ✅ | 역할 설정 + UI 갱신 + 네비게이션 |
| `onAuthStateChange` 핸들러 등록 | ✅ | SIGNED_IN / SIGNED_OUT / TOKEN_REFRESHED 처리 |
| sessionStorage 기반 복원 제거 | ✅ | `onAuthComplete`에서 `wf_last_page` 읽기 없음 |
| hash 기반 페이지 복원 | ✅ | `navigateToHash(initHash)` 호출 확인 |
| 비로그인 시 showHome 폴백 | ✅ | hash 없을 때 `showHome()` 호출 |
| Supabase Anon Key 의도적 공개 | ✅ | RLS 보호 아래 브라우저 노출 (설계 의도) |
| Supabase Service Key 미노출 | ✅ | CF Worker Secret에만 존재 |
| 로그아웃 함수 존재 | ✅ | signOut/logout/handleLogout |
| 비로그인 초기 userRole = 'member' | ✅ | 소스 선언 확인 |

### 3.2 권한 관리 검증 결과

| 검증 항목 | 결과 | 상세 |
|---------|------|------|
| `adminOnly` 플래그 — admin만 메뉴 노출 | ✅ | O&M 섹션 비로그인 미노출 확인 |
| `consultantOnly` 플래그 — consultant+ 메뉴 노출 | ✅ | CEO 플랜 비로그인 미노출 확인 |
| `canConsult()` — consultant·partner·admin 허용 | ✅ | 소스 로직 확인 |
| `IS_PARTNER` — partner·admin만 true | ✅ | 소스 조건 확인 |
| `getAccessLevel()` — 역할별 레벨 반환 | ✅ | full/blur/readonly/hidden |
| GFC 페이지 비로그인 → hidden | ✅ | 실제 함수 호출 검증 |
| GFC 페이지 consultant → blur | ✅ | DEFAULT_ACCESS_RULES 소스 확인 |
| GFC 페이지 admin → full | ✅ | DEFAULT_ACCESS_RULES 소스 확인 |
| `applyAccessOverlay` 함수 존재 | ✅ | CSS 오버레이 적용 함수 |
| service 섹션 전체 공개 | ✅ | 비로그인에서도 사이드바 노출 |

---

## 4. 아키텍처 검증 — Hub-and-Spoke 네비게이션

| 검증 항목 | 결과 |
|---------|------|
| 6개 섹션 TREE slug 정의 (service/consulting/finance/pilot/app-store/admin) | ✅ |
| `showSectionDash` — 섹션 대시 진입 함수 | ✅ |
| `_buildSectionSidebar` — 섹션별 사이드바 필터 | ✅ |
| `_buildFullSidebar` — 전체 사이드바 복원 | ✅ |
| `renderHomeSections` — 홈 섹션 타일 렌더 | ✅ |
| `renderDashCards(sectionFilter)` — 섹션 필터 지원 | ✅ |
| `iframeToSlug('/index.html')` → 슬러그 변환 | ✅ |
| `navigateToHash(hash)` — 딥링크 라우팅 | ✅ |
| `currentSection` 초기값 null | ✅ |
| `SECTION_DESCS` — 6개 섹션 설명 정의 | ✅ |
| `DASH_CARDS[].section` 필드 존재 | ✅ |
| logo click → `showHome()` (onclick 속성) | ✅ |
| logo cursor:pointer 스타일 | ✅ |

---

## 5. 알려진 한계 및 추후 개선 사항

### 5.1 테스트 환경 제약

1. **Supabase 실제 세션 미사용**: 로컬 mock 테스트이므로 실제 로그인/로그아웃 E2E 흐름 미검증. `realdb` 프로젝트 실행 시 `.env.test`에 Supabase credentials 필요.

2. **역할별 UI 렌더 미검증**: `const/let` 변수(`userRole`, `TREE` 등)가 `window`에 비노출되어 직접 주입 불가. 소스 검사 방식으로 보완.

3. **iframe 내부 페이지 E2E**: `consulting/asset/index.html` 등 Hub iframe 자식 페이지는 인증 토큰 없이 직접 접근 시 제한됨. privacy 테스트 1건 skip.

4. **admin UI 기능 테스트 미포함**: `admin/permissions`, `admin/email-campaign` 등 admin 전용 페이지는 실제 admin 세션 필요.

### 5.2 추후 추가 가능한 테스트 (realdb 프로젝트)

```bash
# 실제 DB 연동 테스트 실행 (Supabase credentials 필요)
PLAYWRIGHT_PROJECT=realdb npx playwright test --project=realdb

# 배포 환경 smoke 테스트
npx playwright test tests/smoke.spec.js \
  --project=mock \
  -e DEPLOY_TARGET=https://test.worksfree.kr
```

**추가 권장 테스트 시나리오**:
- 실제 Google OAuth 로그인 후 역할 확인
- consultant 계정으로 컨설팅 메뉴 접근 확인
- admin 계정으로 O&M 메뉴 접근 확인
- 수신거부 이메일 발송 시 자동 필터링 동작
- DART API 한도 초과 배너 표시

---

## 6. 테스트 실행 명령

```bash
# 기본 (mock, 로컬 서버 자동 기동)
npx playwright test --project=mock

# 특정 파일만
npx playwright test tests/auth.spec.js --project=mock
npx playwright test tests/permissions.spec.js --project=mock

# 배포된 서버에서 smoke 테스트
DEPLOY_TARGET=https://test.worksfree.kr npx playwright test tests/smoke.spec.js --project=mock

# HTML 리포트 보기
npx playwright show-report
```

---

**리포트 작성**: 2026-07-01 · WorksFree Hub v0.8.5.32
