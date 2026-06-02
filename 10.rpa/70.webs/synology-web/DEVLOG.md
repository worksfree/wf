# WorksFree Hub 개발 일지

> **프로젝트**: WorksFree Hub — `portal.worksfree.kr`  
> **형태**: 단일 HTML 파일 SPA + 시놀로지 NAS 정적 서빙  
> **기간**: 2026년 4월 25일 ~ (진행 중)  
> **목적**: RPA 앱 배포 포털 + GFC 컨설팅 도구 + 크레딧 기반 과금 플랫폼

---

## 이 문서에 대해

구축가이드(`NAS웹서비스_구축가이드.md`)가 **"어떻게 만드는가"** 를 설명한다면,  
이 일지는 **"왜 그렇게 결정했고, 무엇이 문제였으며, 어떤 순서로 진화했는가"** 를 기록합니다.

---

## 프로젝트 배경 — 왜 만들었나

WorksFree는 기계설계·제조업 엔지니어를 위한 Python RPA 앱을 만든다.  
앱이 여러 개로 늘어나면서 두 가지 문제가 생겼다:

1. **배포 채널 없음**: 앱을 어디서 받는지 알려줄 공식 창구가 없었다
2. **GFC 컨설팅 도구 산재**: GFC 파트너들이 쓰는 컨설팅 도구(경영진단, CEO 플랜 등)가 
   각기 다른 파일/링크로 흩어져 있었다

처음에는 단순한 앱 다운로드 페이지를 생각했다.  
그러다 "어차피 회원 관리, 크레딧 과금도 해야 하는데 한 곳에 다 모으자"로 확장됐다.

**초기 결정**: 별도 서버 없이 **시놀로지 NAS**를 웹 서버로 사용.  
이유: 이미 NAS가 있고, 추가 비용 0원, 데이터가 외부로 나가지 않음.

---

## 주 1 (4월 25일 주간): 컨텐츠 준비 & 인프라 설계

### 가장 먼저 한 것 — 콘텐츠

기이하게도, 허브(Hub) 자체보다 **컨설팅 플라이어가 먼저 만들어졌다.**  
GFC 파트너들이 고객사에 보여줄 홍보 자료(CEO 플랜, 안전보건 관련)를 HTML로 제작.  
이것이 나중에 컨설팅 메뉴의 첫 번째 콘텐츠가 됐다.

```
consulting/gfc/flyers/
├── flyer-ceo.html           ← CEO 플랜 홍보 자료
├── flyer-safety-all.html    ← 산업안전 통합
└── flyer-safety-only.html   ← 안전보건 단독
```

**교훈**: 인프라보다 콘텐츠가 먼저 생기는 게 오히려 자연스러운 순서였다.  
콘텐츠가 있어야 "어디에, 어떻게 보여줄지"가 결정된다.

### 인프라 설계 결정

포털 서비스를 어떻게 호스팅할지 여러 옵션을 검토했다:

| 옵션 | 비용 | 복잡도 | 결정 |
|------|------|--------|------|
| Vercel / Netlify | 무료 (제한 있음) | 낮음 | ❌ 데이터 통제 어려움 |
| AWS/GCP 인스턴스 | 월 ~$20+ | 높음 | ❌ 비용 부담 |
| **시놀로지 NAS** | 이미 있음 = **0원** | 중간 | ✅ 채택 |

**Cloudflare Tunnel 채택 이유**: 공유기 포트포워딩을 하면 NAS IP가 노출된다.  
터널 방식은 NAS가 먼저 Cloudflare에 연결을 맺어두어 외부 IP 노출 없이 서비스 가능.  
보안 + 무료 HTTPS가 자동으로 따라온다.

**3단계 배포 환경** 설계:
```
test.worksfree.kr    → NAS 8081포트 → /volume1/web/test
staging.worksfree.kr → NAS 8082포트 → /volume1/web/staging
portal.worksfree.kr  → NAS 8080포트 → /volume1/web/portal
```
처음부터 "운영/스테이징/테스트" 분리를 설계한 것은 나중에 큰 도움이 됐다.  
실수로 운영 서버에 개발 중인 코드가 올라가는 사고를 방지할 수 있다.

---

## 주 2 (5월 7~10일): 인프라 구성 & 콘텐츠 페이지

### 5월 7일 — 배포 인프라 완성

한 번에 여러 파일을 NAS에 올리는 작업이 번거로워서 자동화를 먼저 만들었다.

**deploy.ps1 핵심 아이디어**: Git Bash의 `tar`로 파일을 묶어 SSH 파이프로 전송.  
Windows에서는 `tar`가 없거나 경로 변환 문제가 있어서 Git Bash 경유 방식으로 해결했다.

```powershell
# tar로 묶어서 SSH로 스트리밍 전송 — 중간 파일 없음
$cmd = "cd '$posix' && tar -czf - . | ssh ${NAS_USER}@${NAS_IP} 'tar -xzf - -C ${REMOTE}'"
& $GIT_BASH -c $cmd
```

**SSH 무비번 로그인 문제**: 키를 등록했는데도 비밀번호를 계속 묻는 상황.  
DSM의 홈 폴더 권한 구조가 표준 Linux와 달라 `StrictModes no`가 필수였다.  
(DSM 업데이트 후 `sshd_config`가 초기화되면 다시 설정해야 하는 함정이 있다)

**nginx 설정** (`nginx-wfhub.conf`): Web Station에서 생성된 기본 설정을  
`X-Frame-Options`와 캐시 헤더 등 보안 관련 설정을 추가해 커스터마이징.

### 5월 8~9일 — 콘텐츠 페이지

**앱스토어 페이지** (7개 RPA 앱 각각):
각 앱의 소개, 다운로드 링크, 크레딧 정책을 담은 정적 페이지.  
이 시점엔 다운로드 링크가 GitHub Release를 가리키는 임시 방편이었다.  
(추후 NAS 직접 서빙 + 토큰 게이팅으로 교체 예정 — Phase 5)

**게시판** (`board/index.html`):  
FormSubmit을 이용한 이메일 폼 방식.  
"DB 없이 이메일로 받는 임시 방편"임을 알면서도, DB 설계 전에 기능이 필요했다.  
(추후 Supabase posts 테이블로 교체 예정 — Phase 6)

> **패턴 발견**: 이 프로젝트에서 여러 번 반복된 패턴이 있다.  
> "지금 당장은 임시 방편, 나중에 교체"  
> 완벽한 솔루션을 기다리느라 서비스가 늦어지는 것보다 낫다.

### 5월 10일 — 문서화

`README.md`와 `CLAUDE.md`를 작성.  
Claude Code와 협업하는 방식이라 AI에게 컨텍스트를 주는 것도 중요한 개발 작업이 됐다.

---

## 주 3 (5월 13~14일): 핵심 플랫폼 기능 집중 개발

이 주는 가장 많은 것이 결정되고 만들어진 주다.  
2026년 5월 13~14일 이틀 동안 이전 2주 분량의 개발을 한 것 같다.

### Hub SPA 아키텍처 결정

**단일 HTML 파일(index.html)** 방식을 선택했다.

다른 선택지였던 React/Vue/Next.js를 쓰지 않은 이유:
- NAS에서 Node.js 빌드 파이프라인을 운영하기 싫었다
- 정적 파일 서빙이 훨씬 단순하고 안정적이다
- 이 프로젝트의 UI 복잡도는 바닐라 JS로 충분히 감당 가능하다

**결과**: `index.html` 하나에 모든 CSS, JS, HTML이 들어간다.  
배포는 `deploy.ps1` 한 번 실행으로 끝난다. 빌드 단계가 없다.

### Prezi 스타일 컨설팅 캔버스

예비창업패키지 페이지(`consulting/prebiz/index.html`)는  
일반 레이아웃 대신 **Prezi 스타일 무한 캔버스**를 채택했다.

`transform-origin:0 0` + `translate/scale`로 카드를 배치하고,  
중앙의 허브 노드("예비창업패키지")를 중심으로 위성 노드들이 연결되는 구조.  
허브 노드 크기: 52px 폰트, 420×220px 타원 — 주변 노드(40px)보다 압도적으로 크게.

왜 이런 UI를 썼냐: 텍스트 위주 나열보다 **시각적 관계**가 명확해 보였고,  
GFC 파트너가 고객사에 설명할 때 더 임팩트가 있다고 판단.

### 인증 시스템

**소셜 로그인 선택**: Google + 카카오. 네이버는 Supabase 기본 지원 없음.  
페이스북은 Meta 앱 심사 과정이 복잡해서 포기.

**이메일 가입 흐름**:  
처음엔 소셜 로그인만 지원하려 했다.  
"해외 카드로 Stripe 결제는 하고 싶은데 구글 계정이 없는 경우"를 대비해  
이메일 + 매직 링크 방식을 추가했다.

**매직 링크 리다이렉트 문제**:  
이메일 링크 클릭 → 리다이렉트 → 비밀번호 설정 화면  
이 흐름에서 `sessionStorage`에 임시 비밀번호를 보관하는 트릭이 필요했다.  
리다이렉트 후 페이지가 새로 로드되면 JS 변수는 초기화되지만,  
`sessionStorage`는 같은 탭에서는 유지된다.

**개인정보 동의**:  
최초 로그인 시 1회만 받는다. `profiles.agreed_at`에 타임스탬프로 기록.  
`agreed_at`이 null이면 동의 모달 표시 — 간단하지만 충분하다.

### DART Cloudflare Worker 배포 문제

기업공시 조회 기능을 위한 DART API 프록시 Worker를 만들었다.  
Worker 코드는 정상인데 **모든 기업 조회가 오류**로 나오는 황당한 상황 발생.

원인 분석:
1. Worker 코드에 `corp_info.json` 라우트가 있어야 종목코드 → corp_code 변환 가능
2. Cloudflare 대시보드에서 코드를 직접 수정했는데, 배포된 버전은 이 라우트가 없었다
3. `wrangler deploy`를 한 번도 실행하지 않아서 로컬 코드가 반영이 안 됐던 것

**해결**: `wrangler.toml` 생성 후 `wrangler deploy` 실행.  
PowerShell로 직접 API 호출해서 삼성전자 데이터가 나오는 걸 확인.

**교훈**: Cloudflare 대시보드에서 편집한 것과 로컬 코드가 다를 수 있다.  
`wrangler deploy`를 명시적으로 해야 코드가 실제로 배포된다.

### 크레딧 시스템 설계

**잔액 방식 vs 원장(Ledger) 방식** 검토:

처음엔 단순하게 `credits` 컬럼 하나에 잔액을 저장하는 방식을 생각했다.  
그런데 "환불할 때 어떻게?", "크레딧 지급 이벤트 이력이 필요한데?" 를 고민하다  
**원장 방식**으로 결정했다.

```
모든 거래를 행(row)으로 기록:
+500 purchase   (토스 결제)
 -50 use_app    (QR 생성 앱 사용)
+100 admin_grant (이벤트 지급)
────────────────
잔액 = SUM(delta) = 550
```

이렇게 하면 잔액은 `credit_balance` 뷰에서 `SUM(delta)`으로 실시간 집계된다.  
데이터 조작이 불가능하고, 전체 이력이 남는다.

**RLS 정책 설계 핵심**:
- 프런트엔드에서 `purchase` (충전)만 직접 INSERT 가능
- `use_app` (차감)은 **서버 함수**(`deduct_credits`)만 가능
- 이유: 사용자가 직접 `-100 use_app`을 INSERT할 수 없게 막아야 한다

```sql
CREATE POLICY "credits_insert_purchase"
  ON credits FOR INSERT
  WITH CHECK (auth.uid() = user_id AND delta > 0 AND reason = 'purchase');
```

### Phase 1 DB 구성 중 발견한 함정들

**함정 1 — 기존 profiles 테이블의 미지 컬럼**  
우리 스크립트를 짜기 전에 이미 Supabase에서 테이블을 만든 흔적이 있었다.  
`role_set_at`이라는 컬럼이 우리 설계에 없는데 존재했다.  
해결: `ADD COLUMN IF NOT EXISTS`로만 우리가 필요한 것만 추가, 기존 것 건드리지 않음.

**함정 2 — RLS 정책 이름 충돌**  
이전에 만든 정책들이 `본인만 조회`, `본인만 수정`, `본인만 삽입`, `본인만 조회·수정`  
4개였다. `DROP POLICY IF EXISTS "profiles_self"`를 해봤자 이 정책들은 안 지워진다.  
해결: 동적 루프로 테이블의 모든 정책을 이름 불문하고 삭제 후 `profiles_self` 하나로 통일.

```sql
DO $$ DECLARE r record;
BEGIN
  FOR r IN SELECT policyname FROM pg_policies WHERE tablename = 'profiles' LOOP
    EXECUTE format('DROP POLICY IF EXISTS %I ON profiles', r.policyname);
  END LOOP;
END $$;
```

**함정 3 — role 기본값 불일치**  
초기 설계에서 role 기본값을 `'member'`로 했는데,  
실제 DB는 `'general'`이 기본값이었다.  
전체 코드에서 `'member'` → `'general'` 일괄 수정 필요.

> 교훈: DB를 건드리기 전에 **현재 상태 진단 쿼리를 먼저 실행**하라.  
> `phase1_check_before_run.sql`이 이 교훈에서 나온 파일이다.

### 역할 기반 접근 제어 (RBAC) 설계 결정

컨설팅 메뉴를 누구에게 보여줄지 결정하는 논의가 있었다.

**처음 생각**: 경영지도사와 GFC에게만 보여주자.  
**재검토**: 일반 회원(RPA 앱 사용자)에게 컨설팅 메뉴가 보이면  
  "이런 서비스도 있구나" 하고 문의가 올 수 있지 않을까?

**최종 결정**: 보이되 잠근다.
- 일반 회원 → 초록 "컨설팅 전용" 칩 + 클릭 시 "문의하기" 안내
- 경영지도사/GFC → 실 사용
- GFC 전용 (보험/경영진단) → 아예 숨김 (테이저도 없음)

이 결정이 `consultantOnly` 플래그라는 새로운 개념을 낳았다.  
기존에 있던 `roleOnly`(완전 숨김)와 `memberOnly`(비로그인 차단)에  
`consultantOnly`(보이지만 역할 없으면 접근 차단)가 추가됐다.

### 테스트 전략

**문제**: DART 조회, QR 생성, 결제 등 외부 API에 의존하는 기능을 어떻게 테스트하나?

**2계층 전략** 채택:
1. `mock` 테스트: Playwright로 모든 외부 API를 인터셉트. 인터넷 없이 실행 가능.  
   매 커밋마다 실행 (빠름, 안정적)
2. `realdb` 테스트: 실제 Supabase Project B에 연결. RLS 정책 검증용.  
   DB 스키마 변경 시 실행

**CSV 테스트 파일 인코딩 문제**:  
DART 조회용 CSV 파일을 만들었더니 Excel에서 한글이 깨졌다.  
원인: UTF-8 파일을 BOM 없이 저장하면 Excel이 CP949로 해석한다.  
해결: `UTF-8 BOM`으로 저장 → Excel 자동 인식.  
이 문제가 전체 프로젝트 규칙(`CLAUDE.md`)에 추가됐다.

---

## 현재 상태 (2026년 5월 14일 기준)

### 완료된 것

| 기능 | 상태 |
|------|------|
| NAS + Cloudflare Tunnel 서빙 | ✅ 운영 중 |
| 3단계 배포 환경 (test/staging/portal) | ✅ 완료 |
| 배포 자동화 (deploy.ps1) | ✅ 완료 |
| Google / 카카오 소셜 로그인 | ✅ 완료 |
| 이메일 매직 링크 가입 | ✅ 완료 |
| 개인정보 동의 흐름 | ✅ 완료 |
| 역할 기반 접근 제어 (general/consultant/gfc) | ✅ 완료 |
| Phase 1 DB (profiles/credits/payments) | ✅ 완료 |
| 크레딧 잔액 표시 (드롭다운) | ✅ 완료 |
| 크레딧 내역 모달 | ✅ 완료 |
| Toss Payments 연동 (테스트 모드) | ✅ 완료 |
| Stripe 연동 (테스트 모드) | ✅ 완료 |
| DART 기업공시 조회 (Cloudflare Worker) | ✅ 완료 |
| Playwright 테스트 (mock + realdb) | ✅ 완료 |
| 앱스토어 페이지 (7개 앱) | ✅ 완료 |
| 컨설팅 페이지 (6종 + GFC 전용 2종) | ✅ 완료 |
| 게시판 (FormSubmit 임시) | ✅ 임시 완료 |
| KO/EN 이중 언어 | ✅ 완료 |
| NAS 웹서비스 구축가이드 | ✅ 완료 |

### 남은 것 (Phase 2~6)

| Phase | 내용 | 우선순위 |
|-------|------|---------|
| **Phase 2** | 크레딧 내역 모달 (완료), 크레딧 히스토리 페이지 | 높음 |
| **Phase 3** | Toss/Stripe 실서비스 전환 (사업자 인증 후) | 높음 |
| **Phase 4** | Python 앱 ↔ 크레딧 연동 (Edge Function) | 높음 |
| **Phase 5** | NAS 대용량 파일 다운로드 (토큰 게이팅) | 중간 |
| **Phase 6** | 게시판 DB 마이그레이션 (FormSubmit → Supabase) | 낮음 |
| **O&M** | 관리자 페이지 (admin.worksfree.kr 별도 사이트) | 중간 |

---

## 반복되는 패턴 — 이 프로젝트에서 배운 것

### 1. 임시 → 교체 순환이 정상이다
게시판은 FormSubmit 임시로 시작, DB 마이그레이션 예정.  
다운로드 링크는 GitHub → NAS 토큰 방식으로 교체 예정.  
"완벽한 솔루션이 나올 때까지 기다리기"보다 "지금 쓸 수 있는 것으로 시작"이 낫다.

### 2. DB 건드리기 전에 현재 상태 확인 먼저
`phase1_check_before_run.sql`이 생긴 이유다.  
예상과 다른 현실(기존 컬럼, 다른 이름의 정책 등)을 먼저 파악해야  
멱등 스크립트를 제대로 짤 수 있다.

### 3. 보안은 처음부터 설계에 넣어야 한다
RLS를 나중에 추가하면 기존 코드 전체를 수정해야 한다.  
`credits_insert_purchase` 정책(프런트는 충전만, 차감은 서버 함수만)처럼  
**어떤 경로로 데이터를 쓸 수 있는지**를 테이블 설계 시점에 정해야 한다.

### 4. 배포 자동화를 일찍 만들어라
`deploy.ps1` 없이 일일이 파일을 올렸다면 개발 속도가 크게 떨어졌을 것이다.  
"배포 자동화는 나중에"가 아니라 "배포 자동화부터"가 맞다.

### 5. 테스트 픽스처도 운영 데이터처럼 다뤄라
CSV 파일의 UTF-8 BOM 문제에서 배웠다.  
테스트 데이터라도 실제 서비스와 동일한 품질 기준을 적용해야  
"테스트에서는 됐는데 실제에선 안 된다"는 상황을 막는다.

---

---

## Session 3 (2026년 6월 2일): 채용 자동화 정비 + 비상장주식 PDF 파싱

### 배경 — 왜 이 세션을 "구축 3"으로 명명했나

이전 세션들에서 기능이 `consulting/jobkorea/`에 임시 배치되어 있었다.  
기능이 늘면서 "컨설팅 페이지에 왜 관리자 전용 자동화 도구가 있지?"라는 혼선이 생겼다.  
이번 세션의 첫 번째 과제는 **기능을 역할에 맞는 위치로 재배치**하는 것이었다.

### 1. 채용 관리 → admin/recruit 이전

**결정 배경**:  
잡코리아 포지션 제안 자동화는 어드민만 쓰는 내부 도구다.  
`consulting/` 하위가 아닌 `admin/` 하위가 맞다는 판단.

```
이전: consulting/jobkorea/index.html  (consultantOnly)
이후: admin/recruit/index.html        (adminOnly)
```

**파일 구성**:
- `admin/recruit/index.html` — Hub 어드민 UI (잡코리아 실행/로그 + 발송 이력 2탭)
- `admin/recruit/jobkorea_auto.py` — Playwright 기반 포지션 제안 자동화
- `admin/recruit/local_server.py` — Flask API 서버 (포트 8765, Hub ↔ Python 브릿지)
- `admin/recruit/requirements.txt` — 의존성
- `admin/recruit/.env.example` — 환경변수 템플릿

**어드민 접근 제어 패턴**:  
HTML 페이지 내부에서 Supabase `profiles.role === 'admin'` 확인 후 `#main-content` 표시.  
부모 허브의 `adminOnly:true` 플래그와 이중 보호.

### 2. jobkorea_dev.ipynb — 셀 단위 개발 방법론

**문제 인식**:  
`jobkorea_auto.py`는 완성된 스크립트 형태라 DOM 셀렉터 검증이 어렵다.  
잡코리아 UI는 수시로 바뀌므로 셀렉터를 확인하면서 개발해야 한다.

**해결 — Notebook 단계별 개발 → 통합 워크플로**:
```
jobkorea_dev.ipynb  (개발·검증)
  └─ CONFIRMED_SELECTORS 딕셔너리 완성
         ↓
  jobkorea_auto.py 에 확정 셀렉터 반영
         ↓
  local_server.py + admin/recruit UI 에서 운영
```

노트북 핵심 설계:
- `JK` 전역 딕셔너리로 브라우저 인스턴스를 셀 간 공유 (`JK['page']`)
- `nest_asyncio.apply()` — Playwright sync API의 Jupyter 이벤트 루프 충돌 방지
- Playwright `slow_mo=500` — 개발 중 각 동작을 눈으로 확인
- 셀렉터 탐색 헬퍼 패턴: 후보 셀렉터 목록 → 실제 발견된 것만 ✅ 출력

**이메일 수집·발송과 잡코리아의 분리**:  
이번 세션에서 명확히 정리됐다.
- 잡코리아: 사이트 내 포지션 제안 기능 (이메일 직접 발송 아님)
- 이메일 수집: `consulting/bizdb/` (B2B 기업 이메일 DB)
- 이메일 발송: `consulting/marketing/` (Resend + Cloudflare Worker)

### 3. 비상장주식 가치평가 — PDF 파싱 + Claude Vision

**기존 stockval 페이지**:  
결정 트리(체크리스트)로 평가 방법론을 안내하고,  
결과에 맞는 계산기(상증세법 가중평균 / 순자산 / DCF / 멀티플)를 제공.

**이번에 추가한 것**:  
세법 결과 화면에 **재무제표 PDF 자동 입력 섹션** 추가.  
체크리스트 → PDF 파싱 → 계산기 자동 채우기의 원스톱 흐름.

**PDF.js 파싱 구조**:
```javascript
// 1. PDF.js로 텍스트 추출 (디지털 PDF → 텍스트 레이어 있음)
const pdf = await pdfjsLib.getDocument({ data: buf }).promise;

// 2. 좌표 기반 정렬 (테이블 행 순서 보존)
const sorted = items.sort((a, b) => {
  const dy = Math.round(b.transform[5]) - Math.round(a.transform[5]);
  return dy !== 0 ? dy : a.transform[4] - b.transform[4];
});

// 3. 단위 자동 감지 + 만원 변환
// 4. 레이블 뒤 숫자 N개 추출 (3년치 처리)
// 5. 음수 처리: △1,234 / (1,234) / -1,234 모두 인식
```

**크레탑·DART 등 디지털 PDF** → PDF.js로 충분 (무료, 브라우저 내 처리).  
**스캔 PDF·사진 파일** → OCR 필요.

**오픈소스 OCR vs Claude Vision 검토**:

| 방식 | 정확도 | 한계 |
|------|--------|------|
| Tesseract.js | ~82% | 테이블 구조 인식 취약 |
| PaddleOCR | ~95% | Python 서버 필요 |
| **Claude Vision** | ~99% | 유료 (페이지당 $0.003) |

재무 데이터는 숫자 하나가 틀려도 치명적이므로  
오픈소스 OCR → 후처리 로직 구현 공수 vs Claude Vision 비용 검토.  
**결론**: Claude Vision 방식 채택. 단, 현재는 비활성화 상태로 구현.

**Claude Vision 비활성화 구현 패턴**:
```html
<button class="claude-btn" disabled title="서비스 준비 중">
  🔒 서비스 준비 중 (Claude Vision API)
</button>
<div class="claude-notice">
  ⚠ 회원 전용 유료 서비스 — 크레딧을 소모합니다.
</div>
```

활성화 시 Cloudflare Worker 경유로 Claude Files API 호출 예정.  
크레딧 차감 로직은 기존 `deduct_credits` 함수 재사용.

### 이번 세션에서 발견한 패턴

**이중 보호 패턴 (admin 페이지)**:
```
Hub 사이드바: adminOnly:true → 비관리자에게 노드 숨김
페이지 자체: Supabase role 확인 → admin이 아니면 #admin-gate 표시
```
직접 URL 접근 시에도 차단되므로 두 레이어 모두 필요.

**비활성 유료 기능 표시 패턴**:  
구현은 완료하되 UI에서만 비활성화. `disabled` 속성 + 안내 문구.  
나중에 Worker + 크레딧 연동만 추가하면 바로 활성화 가능한 상태로 유지.

---

## 주 7 (6월 2일): Dev UX 개선 + 결제 live/test 분리 + 관리자 페이지 개선

### 1. Dev 로그인 → 실제 Supabase 세션 연동

**기존 문제**: `devLogin()`이 모의 세션(UI 우회)만 생성 → iframe 내 컨설팅 페이지가 실제 Supabase 세션 없어 role 인식 불가.

**해결**: `devLogin()`에 실제 `signInWithPassword()` 시도 추가. 성공 시 `onAuthStateChange(SIGNED_IN)` 자동 발화, 실패 시 UI 우회 폴백으로 하향.

**필수 사전 조건**: `fix_dev_profiles_roles.sql` 실행 — dev 계정 UUID를 고정 형식으로 profiles 테이블에 UPSERT.
```
d0000001-...: test@worksfree.co.kr     (general)
d0000002-...: consultant@worksfree.co.kr (consultant)
d0000003-...: gfc@worksfree.co.kr       (gfc)
d0000004-...: admin@worksfree.co.kr     (admin)
```

**_devLoginReal 플래그**: 실제 Supabase 세션 여부 → `updateDevStatus()`에서 페이지뷰 추적 상태 표시.

### 2. 결제 환경 test/live 분리

**PAYMENT_MODE**: `portal` → `'live'`, 그 외 → `'test'`.

**Toss Worker** (`toss-verify.js`): `env` 파라미터로 `TOSS_SECRET_KEY_TEST` / `TOSS_SECRET_KEY_LIVE` 선택.  
> `TOSS_SECRET_KEY_LIVE`는 Toss 라이브 발급 후 `wrangler secret put` 필요 — 미설정 시 Worker가 500 반환.

**결제 모달 배너**: 테스트 환경 → 노란 경고 배너, portal → 초록 실결제 배너.

### 3. 비밀번호 표시/숨기기 (눈 아이콘)

로그인 / 회원가입(2개) / 프로필 비밀번호 변경(2개) — 총 5개 인풋에 `togglePw()` 추가.

### 4. 잠금 카드 UI

`consultantOnly` 또는 `memberOnly` 카드 — 아이콘·설명 영역에 blur 오버레이 + 🔒 배지 표시.  
제목은 상단에 노출, hover 색상 변화 없음.

### 5. 어드민 사용자 관리 페이지 (`admin/users/index.html`) 전면 개선

- **탭 구조**: 회원 목록 / 역할 관리 / 크레딧 지급
- **회원 목록**: 검색·필터·정렬, 로그인 상태 도트(7일·30일 활성 집계)
- **편집 모달**: 이름 + 역할 즉시 변경 (`admin_set_user_name` / `admin_set_user_role` RPC)
- **크레딧 지급**: 이메일 검색 → `admin_grant_credits` RPC
- **로그인 이력**: `admin_get_user_logins` RPC 폴백 포함

### 6. 마인드맵 편집 모드 (`consulting/mindmap/index.html`)

- **Edit Mode**: 노드 드래그·생성·삭제, 연결선 connect mode
- **노드 편집 모달**: 아이콘·제목·설명·태그·href·색상 수정, 체크리스트 편집
- **localStorage 저장/복원 + Undo/Redo**
- **fitAll()**: 전체 노드가 화면에 맞게 초기 뷰 자동 조정

---

*마지막 업데이트: 2026년 6월 2일*
