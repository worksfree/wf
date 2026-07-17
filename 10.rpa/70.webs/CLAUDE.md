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

---

## 멀티테넌트 — 전 노드 공통 필수 (설계 표준)

WorksFree 허브의 **모든 노드(기능·페이지)는 다른 사이트(테넌트)에서도 재구축될 수 있다**는 전제로 설계한다. 공유 Supabase DB 를 여러 테넌트(worksfree.kr, lifeart.ai.kr, …)가 함께 쓰므로, **DB 에 행(row)을 쓰는 모든 기능은 반드시 테넌트로 격리**되어야 한다.

**핵심 원칙**: 지금 DB 를 쓰지 않는 노드(순수 계산기·localStorage 도구)는 격리 대상이 없어 무관하다. 그러나 **그런 노드가 나중에 DB 를 쓰게 되면, 그 순간 이 표준을 반드시 반영**해야 한다. "허브 전용이라 안 붙였다"는 이유로 tenant_id 를 생략하지 않는다.

### 1. tenant_id 규약 (통일)
- 공유 DB 에 테넌트/사용자별 행을 저장하는 **모든 테이블**은 다음 컬럼을 가진다:
  ```sql
  tenant_id uuid NOT NULL REFERENCES public.tenants(id) DEFAULT '<worksfree-uuid>'::uuid
  ```
- `tenants` = 도메인 레지스트리(`domain` → `id`). 기존 데이터/기존 호출부 무변경을 위해 DEFAULT 는 worksfree 테넌트.
- 과거 `tenant_id TEXT DEFAULT 'worksfree'`(auction·email 계열)·`env TEXT`(page_views) 방식은 **레거시**. 신규는 항상 **uuid FK** 로 만든다.

### 2. 클라이언트 — 호스트명으로 테넌트 해석
페이지는 열린 도메인으로 테넌트를 판별한다(루트 도메인 → `tenants` 조회). 참고 구현: [asset](synology-web/consulting/asset/index.html) 의 `getRootDomain()`+`initTenant()`, [esg](synology-web/consulting/esg/index.html) 동일 패턴.
- 모든 INSERT 에 `tenant_id: tenantId || undefined`(미해석 시 DB DEFAULT 로 폴백).
- SELECT/UPDATE/DELETE 는 RLS 가 자동으로 테넌트 스코프 처리(아래) — 클라이언트에서도 `tenant_id=eq.` 필터를 병행하면 방어적.

### 3. RLS 패턴 (유형별)
- **사용자 소유 데이터**(portfolios·esg_reports 등): `FOR ALL USING(auth.uid()=user_id AND tenant_id=(SELECT tenant_id FROM profiles WHERE id=auth.uid()))` + 동일 `WITH CHECK`.
- **Worker 기록 로그**(jobkorea_proposals·campaign·biz_contacts 등): 쓰기 정책 없음 → service_role 전용. 읽기는 `is_admin() AND tenant_id=본인테넌트`.
- **공개 읽기 레지스트리**(tenants·site_config): `FOR SELECT USING(true)`, 쓰기 정책 없음.
- ⚠️ `is_admin()` 은 **worksfree 테넌트 관리자로 스코핑**됨(허브 관리자가 타 테넌트로 승격되는 구멍 차단). 타 테넌트의 관리자는 `is_lifeart_admin()` 처럼 **테넌트별 헬퍼**를 쓴다.

### 4. 신규 노드/테이블 추가 시 체크리스트
- [ ] 이 노드가 Supabase 에 행을 쓰는가? → 예면 아래 전부 필수
- [ ] 테이블에 `tenant_id uuid NOT NULL REFERENCES tenants(id)` (DEFAULT worksfree)
- [ ] RLS 활성화 + 위 유형별 정책(테넌트 조건 **반드시** 포함)
- [ ] 클라이언트가 `initTenant()` 로 tenant 해석 + INSERT 에 tenant_id 태깅
- [ ] 정본 스키마(`supabase/core/`)와 마이그레이션(`supabase/migration/`) 양쪽에 반영
- [ ] 검증: anon 으로 타 테넌트 행 접근 불가 확인

### 5. 정본·마이그레이션 위치
- DB 정본: [`supabase/core/`](supabase/core/) · 멀티테넌트 마이그레이션: [`supabase/migration/2026-07_multitenant/`](supabase/migration/2026-07_multitenant/) (적용 상태표는 그 폴더 README).
- ⚠️ 정본 `complete_db_setup.sql` 의 `is_admin()`·`profiles`/`page_views` 정의는 마이그레이션(04·19)이 **테넌트 스코핑으로 덮어씀**. 정본을 재실행하면 되돌아가니, 재실행 시 04·19 도 이어서 적용할 것(정본 상단 경고 참조).
