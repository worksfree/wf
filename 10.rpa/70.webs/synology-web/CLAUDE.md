# CLAUDE.md — synology-web

WorksFree Hub 정적 웹사이트 (index.html 단일 파일 SPA).  
배포: 시놀로지 NAS + Cloudflare Tunnel. 인증: Supabase Auth.

## KO/EN 이중 언어 구현 패턴

상위 CLAUDE.md의 KO/EN 필수 규칙을 이 프로젝트에 적용하는 구체적 방법.

### 번역 사전 — HUB_I18N

모든 사용자 노출 문자열은 `HUB_I18N` 객체에 ko/en 쌍으로 등록한다.

```javascript
const HUB_I18N = {
  ko: {
    my_key: '한국어 텍스트',
  },
  en: {
    my_key: 'English text',
  }
};
function t(key) { return HUB_I18N[lang][key] || HUB_I18N.ko[key]; }
```

### 언어 적용 — applyHubLang()

언어 전환 시 `applyHubLang()`이 호출된다.  
신규 UI 요소를 추가할 때는 반드시 이 함수 안에 갱신 로직을 추가한다.

```javascript
// 텍스트 노드
document.getElementById('my-el').textContent = t('my_key');

// innerHTML (링크·강조 포함 시)
document.getElementById('my-el').innerHTML = t('my_key_html');

// placeholder
document.getElementById('my-input').placeholder = t('my_ph_key');

// 동적 조합 (클릭 핸들러 포함)
el.innerHTML = t('question_text') + ' <span onclick="fn()">' + t('action_text') + '</span>';
```

### JS 함수 내 동적 메시지

사용자에게 표시되는 에러·알림 문자열도 하드코딩 금지.

```javascript
// 올바른 방법
setAuthMsg('el-msg', 'err', t('auth_err_invalid_login'));

// 금지
setAuthMsg('el-msg', 'err', '이메일 또는 비밀번호가 틀렸습니다.');
```

### 신규 페이지/섹션 추가 시 체크리스트

- [ ] `HUB_I18N.ko`에 모든 문자열 추가
- [ ] `HUB_I18N.en`에 동일 키 영어 번역 추가
- [ ] `applyHubLang()` 안에 DOM 갱신 코드 추가
- [ ] HTML 요소에 ID 부여 (applyHubLang에서 참조용)
- [ ] HTML 초기값은 ko로 작성 (페이지 로드 직후 applyHubLang이 덮어씀)

## 컨설팅 진단 페이지 — 스티키 헤더 + 프로그레스바 템플릿

프로그레스바가 있는 모든 컨설팅 진단 페이지는 아래 구조를 **그대로** 복사해서 시작한다.  
확정된 레퍼런스 구현: `gfc/index.html`, `inheritance/index.html`, `jdh/index.html`

### ❌ 절대 하지 말 것

```html
<!-- iframe 임베드 시 헤더를 숨기는 스크립트 — 절대 추가 금지 -->
<script>
(function(){
  if(window.self !== window.top){
    document.querySelector('header').style.display = 'none'; // ← 금지
  }
})();
</script>
```
> 이 스크립트가 있으면 허브(index.html)의 iframe 안에서 헤더가 사라진다.  
> 컨설팅 페이지는 항상 iframe으로 로드되므로 헤더가 완전히 숨겨지는 버그 발생.

---

### HTML 구조 (템플릿)

```html
<!DOCTYPE html>
<html lang="ko">
<head>
<!-- ↑ iframe hide 스크립트 없음 — 절대 추가 금지 -->
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>페이지 제목 — WorksFree</title>
<style>
/* ... CSS ... */
</style>
</head>
<body>

<!-- 1. 스티키 헤더 (72px) — 항상 화면 상단에 고정 -->
<header>
  <div class="hdr-icon">🔷</div>          <!-- 페이지 대표 이모지/아이콘 -->
  <div class="hdr-info">
    <div class="hdr-title">진단 페이지 제목</div>
    <div class="hdr-sub">부제목 · 키워드 · 설명</div>
  </div>
  <div class="hdr-r" id="hdr-r"></div>    <!-- JS가 진행 단계 표시 (선택) -->
</header>

<!-- 2. 트렌드 배너 — 스티키 아님, 스크롤 시 사라짐 -->
<div class="trend-banner">
  <div class="trend-inner">
    <div class="trend-title">배너 제목</div>
    <div class="trend-grid">
      <div class="trend-stat"><div class="ts-val">수치</div><div class="ts-label">설명</div></div>
      <!-- 3~4개 통계 카드 -->
    </div>
    <div class="trend-note"><strong>핵심 문제:</strong> ...</div>
  </div>
</div>

<!-- 3. 기타 섹션 (시뮬레이터 등, 선택) -->

<!-- 4. 스티키 프로그레스바 — header 바로 아래 고정 (top:72px) -->
<div class="prog-wrap">
  <div class="prog-inner">
    <div class="prog-meta"><span id="prog-lbl">진단 시작</span><span id="prog-pct">0%</span></div>
    <div class="prog-track"><div class="prog-fill" id="prog-fill" style="width:0%"></div></div>
    <div class="breadcrumb" id="bc"></div>
  </div>
</div>

<!-- 5. 질문 렌더링 영역 -->
<div class="page">
  <div id="view"></div>
</div>

<script>
/* ... */
</script>
</body>
</html>
```

---

### 필수 CSS

```css
/* ── 헤더 (스티키, 72px) ── */
header {
  position: sticky; top: 0; z-index: 100;
  min-height: 72px; padding: 14px 24px;
  display: flex; align-items: center; gap: 14px;
  background: var(--surface);
  border-bottom: 1px solid var(--border);
}
.hdr-icon  { font-size: 26px; flex-shrink: 0; }
.hdr-info  { flex: 1; }
.hdr-title { font-size: 17px; font-weight: 600; letter-spacing: -.2px; }
.hdr-sub   { font-size: 13px; color: var(--muted); margin-top: 2px; }
.hdr-r     { font-size: 12px; color: var(--hint); font-weight: 500; margin-left: auto; flex-shrink: 0; }

/* ── 프로그레스바 래퍼 (스티키, 헤더 바로 아래) ── */
.prog-wrap  { position: sticky; top: 72px; z-index: 99; background: var(--surface); border-bottom: 1px solid var(--border); padding: 12px 24px 0; }
.prog-inner { max-width: 740px; margin: 0 auto; }
.prog-meta  { display: flex; justify-content: space-between; font-size: 11px; color: var(--hint); margin-bottom: 7px; }
.prog-track { height: 3px; background: var(--border); border-radius: 2px; }
.prog-fill  { height: 100%; background: var(--blue); border-radius: 2px; transition: width .4s; }
.breadcrumb { display: flex; flex-wrap: wrap; gap: 4px; min-height: 24px; padding-bottom: 10px; align-items: center; }
.crumb      { font-size: 11px; background: var(--surface); border: 1px solid var(--border); color: var(--muted); padding: 2px 9px; border-radius: 20px; }

/* ── 콘텐츠 영역 ── */
.page { max-width: 740px; margin: 0 auto; padding: 8px 18px 72px; }
```

---

### 필수 JS — scrollToQ()

질문 선택·뒤로 가기·재시작 시 `window.scrollTo({top:0})` 금지.  
`top:0`으로 스크롤하면 트렌드 배너가 화면을 가려 질문이 프로그레스바 뒤에 묻힌다.

```javascript
function scrollToQ() {
  const pw = document.querySelector('.prog-wrap');
  window.scrollTo({top: pw ? Math.max(0, pw.offsetTop - 72) : 0, behavior:'smooth'});
}

function pick(pos, optIdx) {
  /* ... 로직 ... */
  render();
  scrollToQ(); // ← window.scrollTo({top:0}) 금지
}
function goBack()  { /* ... */ render(); scrollToQ(); }
function restart() { /* ... */ render(); scrollToQ(); }
```

---

### 신규 진단 페이지 추가 시 체크리스트

- [ ] `<head>` 상단에 iframe hide 스크립트 없음 확인 (추가 금지)
- [ ] `<header>` — `min-height:72px`, `position:sticky; top:0` + `.hdr-icon` / `.hdr-info` / `.hdr-title` / `.hdr-sub` 구조
- [ ] `<div class="prog-wrap">` — `.page` 컨테이너 **밖**에 배치, `position:sticky; top:72px`
- [ ] `.page` — `padding-top:8px` (상단 여백 최소화)
- [ ] JS — `scrollToQ()` 사용, `window.scrollTo({top:0})` 사용 금지
- [ ] 트렌드 배너 — `<header>` 바로 아래, `.prog-wrap` 바로 위 (스티키 아님)

## 파일 구조

```
synology-web/
├── index.html          # 단일 SPA — 모든 UI/JS/CSS 포함
├── consulting/         # 컨설팅 상세 페이지 (iframe으로 로드)
├── service/            # 서비스 상세 페이지 (iframe으로 로드)
├── app-store/          # 앱 다운로드 페이지 (iframe으로 로드)
├── deploy.ps1          # 배포 스크립트 (NAS tar+SSH)
├── deploy.bat          # deploy.ps1 래퍼 (더블클릭용)
└── nginx-wfhub.conf    # NAS Nginx 설정 참고용
```

## 배포

```powershell
.\deploy.ps1   # 또는 deploy.bat 더블클릭
# [1] test → [2] staging → [3] portal 순서 권장
```

### 자동 처리 항목 (매 배포 시)

1. **버전 자동 증가** — 환경에 따라 다른 자리수 증가 (버전 규칙 섹션 참고)  
2. **`index.html` 동기화** — `HUB_VERSION` 상수를 deploy.ps1의 `$VERSION`과 동일하게 업데이트  
3. **tar+SSH 전송** — Google Drive 클라우드 파일 포함 전송  
4. **Cloudflare 캐시 퍼지** — 배포 후 Edge 캐시 자동 초기화  

### 브라우저 캐시 버스팅 패턴

**왜 필요한가**: Cloudflare 퍼지는 Edge 캐시만 지운다. 브라우저 로컬 캐시는 URL이 달라야 만료된다.  
NAS nginx가 HTML 파일에 `Cache-Control` 헤더를 보내지 않으면 브라우저는 `Last-Modified` 기반 휴리스틱 캐시를 사용하며, 이 경우 배포 후에도 구버전이 서빙될 수 있다.

#### 레이어 1 — 허브 → 컨설팅 페이지

`index.html`은 컨설팅 페이지를 iframe으로 로드할 때 `?v=HUB_VERSION`을 붙인다.  
매 배포마다 버전이 올라가므로 consulting/*.html은 항상 새 URL을 받는다.

```javascript
// index.html 내부
iframe.src = src + '?v=' + HUB_VERSION;
```

#### 레이어 2 — 컨설팅 페이지 → 하위 HTML 파일 (플라이어 등)

컨설팅 페이지가 추가 HTML 파일을 로드하는 경우(예: `consulting/ceo/` → 플라이어 모달), 그 페이지도 캐시 버스팅이 필요하다.  
허브가 전달한 `?v=` 값을 재사용하고, 직접 접근 시에는 `Date.now()`로 대체한다.

```javascript
// consulting/ceo/index.html 등 — 하위 HTML을 로드하는 컨설팅 페이지에 반드시 추가
const _FV = new URLSearchParams(location.search).get('v') || Date.now();

// 썸네일 iframe들 캐시 버스팅 (페이지 로드 시 1회)
document.querySelectorAll('.flyer-thumb iframe').forEach(function(f){
  var s = f.getAttribute('src');
  if(s) f.src = s + '?v=' + _FV;
});

// 모달 iframe 열기 시
function openFlyer(src) {
  document.getElementById('flyer-modal-iframe').src = 'flyers/' + src + '?v=' + _FV;
  ...
}
```

#### 레이어 3 — nginx HTML no-cache (서버 측, 1회 DSM 설정)

NAS nginx가 HTML 파일에 `Cache-Control: no-cache, no-store, must-revalidate`를 보내면 브라우저가 항상 서버에 재검증 요청을 보낸다. `?v=` 파라미터 없이도 최신 HTML이 서빙된다.

`nginx-wfhub.conf`에 설정이 이미 작성돼 있다. **DSM → 웹 스테이션 → 가상 호스트 → 각 환경(test/staging/portal) → 사용자 설정 → 사용자 nginx 설정**에 아래 블록을 추가하면 적용된다.

```nginx
# HTML은 항상 재검증 (브라우저 휴리스틱 캐시 방지)
location ~* \.html$ {
    add_header Cache-Control "no-cache, no-store, must-revalidate";
    add_header Pragma "no-cache";
    add_header Expires "0";
}
# 정적 자산은 캐시 (7일)
location ~* \.(js|css|png|jpg|svg|ico|woff2?)$ {
    expires 7d;
    add_header Cache-Control "public";
}
```

> **레이어 1·2로 대부분의 케이스는 커버된다. 레이어 3은 안전망(defense in depth).**

## 버전 규칙 (웹 전용)

버전 형식: `MAJOR.MINOR.PATCH.BUILD` (예: `0.7.4.12`)

배포 환경마다 증가하는 자리가 다르며, `deploy.ps1`이 선택된 환경에 따라 자동 증가한다.

| 환경 | 증가 자리 | 동작 | 예시 |
|------|----------|------|------|
| test (1번) | BUILD (4번째) | 자연 증가, 상한 없음 | `0.7.4.9` → `0.7.4.10` |
| staging (2번) | PATCH (3번째) | BUILD를 0으로 리셋 | `0.7.4.15` → `0.7.5.0` |
| portal (3번) | MINOR (2번째) | PATCH·BUILD를 0으로 리셋 | `0.7.5.3` → `0.8.0.0` |
| g1consulting (4번) | BUILD (4번째) | test와 동일 | `0.7.4.9` → `0.7.4.10` |

- BUILD는 test 반복 횟수 — 상한 없이 자연 증가 (`0.7.4.9 → 0.7.4.10`, 캐스케이드 없음).
- PATCH·MINOR cascade: PATCH가 9 초과 시 MINOR 올림 (`0.7.9.x` staging → `0.8.0.0`).
- Q(취소)·R(롤백) 선택 시 버전 변경 없음.
- 버전은 `deploy.ps1`의 `$VERSION`과 `index.html`의 `HUB_VERSION`에 동기화됨.

## 인증 구조

- **소셜 로그인**: Google OAuth, Kakao OAuth (Supabase Provider)
- **이메일 가입**: signInWithOtp 매직 링크 → 리다이렉트 후 updateUser로 비밀번호 설정
- **비밀번호 임시 보관**: sessionStorage (`wf_signup_pw`, `wf_signup_name`) — 매직 링크 리다이렉트 생존
- **개인정보 동의**: 최초 로그인 시 1회. `public.profiles` 테이블의 `agreed_at`으로 판별
- **Dev 모드**: `?dev=1` 또는 `localStorage.wf_dev='1'` → Supabase 없이 목업 사용자로 UI 테스트

## 3단계 배포 환경

| 환경 | URL | NAS 경로 | 포트 |
|------|-----|----------|------|
| test | test.worksfree.kr | /volume1/web/test | 8081 |
| staging | staging.worksfree.kr | /volume1/web/staging | 8082 |
| portal | www.worksfree.kr | /volume1/web/portal | 8080 |

## 결제 데이터 환경 격리 (env 컬럼)

test/staging/portal 세 환경이 **동일한 Supabase DB**를 공유하므로, 결제 관련 테이블에 `env` 컬럼으로 출처를 구분한다.

### 컬럼 추가 SQL (최초 1회)

```sql
ALTER TABLE payments      ADD COLUMN IF NOT EXISTS env text NOT NULL DEFAULT 'portal';
ALTER TABLE credits       ADD COLUMN IF NOT EXISTS env text NOT NULL DEFAULT 'portal';
ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS env text NOT NULL DEFAULT 'portal';
```

### env 값 결정 규칙

| 조건 | env 값 |
|------|--------|
| IS_DEV = true (dev 툴바) | `'dev'` |
| hostname이 `test.`로 시작 | `'test'` |
| hostname이 `staging.`로 시작 | `'staging'` |
| 그 외 (portal, www 등) | `'portal'` |

```javascript
function getPaymentEnv() {
  if (IS_DEV) return 'dev';
  const h = location.hostname;
  if (h.startsWith('test.'))    return 'test';
  if (h.startsWith('staging.')) return 'staging';
  return 'portal';
}
```

### 사용 패턴

- `_recordPurchase()` — 모든 insert/upsert에 `env: getPaymentEnv()` 추가
- `loadCreditBalance()` / `loadCreditHistory()` — 모든 credits/subscriptions 쿼리에 `.eq('env', getPaymentEnv())` 추가
- 이렇게 하면 각 환경은 자기 데이터만 보임

### 출시 전 데이터 청소 SQL

Supabase → SQL Editor에서 환경별 선택 삭제:

```sql
-- 개발 모드 데이터 삭제
DELETE FROM credits       WHERE env = 'dev';
DELETE FROM payments      WHERE env = 'dev';
DELETE FROM subscriptions WHERE env = 'dev';

-- test 서버 데이터 삭제
DELETE FROM credits       WHERE env = 'test';
DELETE FROM payments      WHERE env = 'test';
DELETE FROM subscriptions WHERE env = 'test';

-- staging 데이터 삭제
DELETE FROM credits       WHERE env = 'staging';
DELETE FROM payments      WHERE env = 'staging';
DELETE FROM subscriptions WHERE env = 'staging';

-- portal 데이터 삭제 (출시 전 시험 구매 정리)
DELETE FROM credits       WHERE env = 'portal';
DELETE FROM payments      WHERE env = 'portal';
DELETE FROM subscriptions WHERE env = 'portal';

-- 전체 한 번에 (완전 초기화)
DELETE FROM credits;
DELETE FROM payments;
DELETE FROM subscriptions;
```

> **출시 체크리스트**: 정식 서비스 오픈 직전에 portal 데이터 삭제 후 시작. 그 이후에는 portal 데이터 = 실제 고객 데이터.

## Supabase 설정 필수값

- `SUPABASE_URL` / `SUPABASE_ANON`: `index.html` 상단 상수

### Redirect URLs 설정 경로

```
Supabase 대시보드
  → Authentication
    → URL Configuration
      → Auth → Redirect URLs
```

등록 필요 URL:
- `https://test.worksfree.kr/**`
- `https://staging.worksfree.kr/**`
- `https://portal.worksfree.kr/**`
- `https://www.worksfree.kr/**` (www 사용 시)

Site URL: `https://www.worksfree.kr`

## Cloudflare Tunnel 서브도메인 설정

### 신규 서브도메인 추가 경로

```
Cloudflare 대시보드 (one.dash.cloudflare.com)
  → Protect & Connect
    → Networking
      → Tunnels
        → synology-tunnel
          → Configure
            → Public Hostnames 탭
              → Add a public hostname  (또는 기존 행 Edit route)
```

| 필드 | 값 |
|------|-----|
| Subdomain | `test` / `staging` / `portal` / `www` |
| Domain | `worksfree.kr` |
| Service Type | `HTTP` |
| URL | `localhost:포트` (환경별 포트 아래 표 참고) |

Public Hostname을 저장하면 Cloudflare DNS에 Tunnel CNAME 레코드가 **자동 생성**된다.  
DNS 탭에서 직접 레코드를 추가/삭제하지 말 것 — Tunnel이 관리하는 레코드임.

### www 서브도메인 추가 시 주의

www를 추가해도 NAS nginx의 `server_name`에 `www.worksfree.kr`이 없으면 404/502가 발생한다.  
`nginx-wfhub.conf`의 portal 서버 블록에 추가 필요:

```nginx
server_name portal.worksfree.kr www.worksfree.kr;
```

## 어드민 페이지 패턴

### 위치 규칙

```
admin/
├── users/index.html      # 사용자·역할·크레딧 관리
├── monitor/index.html    # 시스템 모니터
├── content/index.html    # 콘텐츠 관리
└── recruit/index.html    # 채용 관리 (잡코리아 포지션 제안)
```

어드민 전용 기능은 `consulting/` 하위가 아닌 `admin/` 하위에 배치한다.

### 이중 보호 패턴

어드민 페이지는 두 레이어로 접근을 제한한다.

**레이어 1 — Hub 사이드바**: `adminOnly:true` 플래그 → 비관리자에게 노드 자체를 숨김.

**레이어 2 — 페이지 내부**: Supabase `profiles.role` 확인 → admin이 아니면 `#admin-gate` 표시.

```javascript
// 페이지 최상단에서 실행
(async () => {
  // localhost bypass: Live Server는 운영 도메인과 localStorage가 격리되어 세션 없음
  if (location.hostname === 'localhost' || location.hostname === '127.0.0.1') {
    document.getElementById('admin-gate').style.display = 'none';
    document.getElementById('main').classList.add('visible');
    return;
  }
  try {
    const { data: { session } } = await sb.auth.getSession();
    if (session) {
      const { data: p } = await sb.from('profiles').select('role').eq('id', session.user.id).single();
      if (p?.role === 'admin') {
        document.getElementById('admin-gate').style.display = 'none';
        document.getElementById('main').classList.add('visible');
        return;
      }
    }
  } catch(e) {}
  document.getElementById('admin-gate').classList.add('visible');
})();
```

레이어 2가 없으면 직접 URL 접근으로 우회 가능하므로 **반드시 두 레이어 모두 필요**.

### 어드민 게이트 CSS 규칙 — `display` 중복 금지

`#admin-gate`는 **기본값이 `display:flex`**이어야 한다 (인증 통과 전 항상 표시).

```css
/* ✅ 올바른 패턴 — display 하나만 선언 */
#admin-gate {
  display: flex;
  position: fixed; inset: 0;
  align-items: center; justify-content: center; flex-direction: column;
  /* ... */
}

/* ❌ 금지 패턴 — 같은 규칙 안에 display:none 뒤에 display:flex */
#admin-gate { display: none; ... display: flex; }
/* → display:none은 무시되고 display:flex가 적용되어 구조는 맞지만 의도가 불분명 */
```

- JS 인증 성공 시: `element.style.display = 'none'` (인라인 스타일로 CSS 오버라이드)
- JS 인증 실패 시: `element.classList.add('visible')` — 별도 `.visible` 클래스 불필요 (이미 flex)

### Live Server(localhost) 테스트 시 관리자 게이트 차단 원인

> **증상**: 운영 서버에서 admin으로 로그인한 상태임에도 Live Server(`localhost:5500`)로 어드민 페이지를 열면 "🔒 관리자 전용" 게이트가 사라지지 않음.
>
> **원인**: `localStorage`는 **origin(프로토콜+도메인+포트) 단위로 격리**된다. Supabase 세션 토큰은 `portal.worksfree.kr`의 localStorage에 저장되어 있으며, `localhost:5500`의 localStorage에는 존재하지 않는다. `sb.auth.getSession()`이 `null`을 반환하므로 인증이 항상 실패한다.
>
> **해결책**: 위 코드 패턴처럼 `location.hostname === 'localhost'` 조건 분기를 **모든 어드민 페이지에 반드시 추가**한다.
>
> **주의**: 이 bypass는 `localhost`에서만 동작하므로 프로덕션 보안에 영향 없음.

## 비활성 유료 서비스 UI 패턴

구현은 완료하되 UI에서만 비활성화하는 패턴. 나중에 인프라 연동만 완료하면 바로 활성화 가능.

```html
<!-- disabled 속성 + 안내 문구 -->
<button class="claude-btn" disabled title="서비스 준비 중">
  🔒 서비스 준비 중 (Claude Vision API)
</button>
<div class="claude-notice">
  ⚠ <strong>회원 전용 유료 서비스</strong> — 크레딧을 소모합니다.
  일반 텍스트 PDF는 위 PDF.js 방식으로 무료 처리됩니다.
</div>
```

CSS:
```css
.claude-card.disabled { opacity: .6; }
.claude-btn:disabled  { cursor: not-allowed; }
.paid-badge { background: rgba(239,68,68,.2); color: #fca5a5; }
```

## PDF 파싱 — PDF.js 클라이언트사이드

디지털 생성 PDF(크레탑·DART 등)는 서버 없이 브라우저에서 텍스트 추출 가능.

```javascript
// CDN
// <script src="https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js"></script>
pdfjsLib.GlobalWorkerOptions.workerSrc =
  'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';

// 텍스트 추출 (좌표 기반 정렬로 테이블 행 순서 보존)
const pdf = await pdfjsLib.getDocument({ data: arrayBuffer }).promise;
for (let i = 1; i <= pdf.numPages; i++) {
  const items = (await (await pdf.getPage(i)).getTextContent()).items;
  const sorted = items.sort((a, b) => {
    const dy = Math.round(b.transform[5]) - Math.round(a.transform[5]);
    return dy !== 0 ? dy : a.transform[4] - b.transform[4];
  });
  text += sorted.map(it => it.str).join(' ') + '\n';
}
```

스캔 PDF 감지: 텍스트 추출 후 200자 미만이면 스캔 문서로 판단 → Claude Vision 권장.

---

## 컨설팅 페이지 UX 패턴 (2026-06 분석)

### 패턴 A: 진단형 (다단계 선택 → 자동 결과)
**적용 페이지**: CEO 플랜, GFC 보험진단, 상속세, 주식평가

- 단계별 카드(Step 1, Step 2...)를 순서대로 선택하면 자동으로 다음 단계가 펼쳐짐
- 별도 "계산하기" 버튼 없음 — 선택 완료 시 즉시 결과 렌더링
- 인쇄/공유용 보고서 버튼 없음 (플라이어 등 별도 출력물 존재)

### 패턴 B: 시뮬레이터형 (입력값 변경 → 자동 계산 → 보고서 생성)
**적용 페이지**: 연금 절세 시뮬레이터 (`consulting/pension/index.html`)

```
[헤더] 📋 보고서 생성 버튼 (첫 계산 후 표시)
[auto-bar] 자동업데이트 표시 (autoDot pulse 애니메이션)
[입력 패널] oninput="onIC()" → debounce 200ms → calculate()
[결과 섹션] #resultsSection (초기 display:none → 계산 후 display:block)
```

**핵심 구현 규칙:**
1. `oninput="onIC()"` 모든 입력 필드에 → `clearTimeout` + `setTimeout(calculate, 200)` 패턴
2. 결과 표시: `document.getElementById('resultsSection').style.display = 'block'` (CSS 룰 오버라이드이므로 `''` 아닌 `'block'` 필수)
3. 자동 업데이트 피드백: autoDot 애니메이션 — `classList.remove('pulse'); void el.offsetWidth; classList.add('pulse')`
4. 별도 계산 버튼 없음

**📋 보고서 생성 패턴 (ESG/연금 공통):**
```html
<!-- 헤더 우측 -->
<button id="rptBtn" style="display:none" onclick="showReport()">📋 보고서 생성</button>

<!-- body 끝 (오버레이) -->
<div class="pension-report" id="pensionReport">
  <div class="rpt-topbar">  <!-- sticky, 인쇄/닫기 버튼 포함 -->
  <div class="rpt-body" id="rptContent"></div>  <!-- 동적 생성 -->
</div>
```
```css
/* 오버레이 패턴 */
.pension-report { display:none; position:fixed; inset:0; background:#fff; z-index:200; overflow-y:auto; }
.pension-report.open { display:block; }
@media print {
  body > *:not(.pension-report) { display:none !important; }
  .pension-report { display:block !important; position:static !important; }
  .rpt-topbar { display:none !important; }
}
```
```js
function showReport() {
  // lastResult / lastInput으로 innerHTML 동적 빌드
  document.getElementById('pensionReport').classList.add('open');
}
function closeReport() { document.getElementById('pensionReport').classList.remove('open'); }
function printReport() { window.print(); }
```
- 계산 성공 시 `rptBtn.style.display = ''` 로 버튼 노출
- 보고서 내용: 입력 조건 요약 → 핵심 지표 → 연도별 명세 → 면책고지

**금액 단위 표시 규칙:**
- 요약 카드 월수령: 값 옆에 `<span class="unit-badge">/월</span>` 표기
- 요약 카드 합산: sub-line에 "(총 N년 합산)" 명시
- 시나리오 카드: 연간 금액은 `원/년`, 월 금액은 `원/월` 접미사
- 테이블 헤더: 섹션 소제목에 "(연 합산 기준 · 월 열만 원/월)" 명시

### 패턴 선택 기준
| 상황 | 권장 패턴 |
|------|-----------|
| 선택지가 이산적 (유형 선택) | 패턴 A (진단형) |
| 수치 입력 + 연속적 시뮬레이션 | 패턴 B (시뮬레이터형) |
| 결과가 프린트용 보고서로 필요 | 📋 보고서 생성 버튼 추가 |

## 접근 제어 규칙 (2026-07-11 확정) — 위반 구현 금지

### 사이드바 원칙

**모든 항목을 항상 표시한다. 역할에 따라 사이드바 항목을 숨기지 않는다.**

접근이 제한된 항목에는 🔒 아이콘을 표시한다. 클릭 시 블러 오버레이(showAccessBlur)를 띄운다.

### `_isNodeLocked(node)` 패턴

```javascript
function _isNodeLocked(node) {
  if (node.iframe && getAccessLevel(node.iframe) === 'hidden') return true;
  if (node.adminOnly    && userRole !== 'admin') return true;
  if (node.partnerOnly  && !IS_PARTNER)          return true;
  if (node.consultantOnly && !canConsult())       return true;
  return false;
}
```

### 역할별 콘텐츠 분기 페이지

아래 페이지들은 Hub에서 전달받은 `wf_role` postMessage에 따라 내부 콘텐츠가 달라진다.

| 페이지 | 분기 방식 |
|--------|----------|
| `board/index.html` | `wf_role` 수신 → 어드민 메모 노출 여부 |
| `consulting/bizdb/index.html` | `applyRole(role)` 호출 |
| `consulting/gfc/index.html` | 역할별 진단 깊이 변경 |
| `consulting/marketing/index.html` | `applyMarketingRole(role)` 호출 |
| `consulting/ceo/index.html` | `partnerOnly:true` — partner/admin만 접근 |
| `consulting/ceo/flyers/*.html` | 플라이어 — 역할별 표시 분기 |

### `_reapplyCurrentPageAccess()` — 역할 변경 즉시 적용

역할이 바뀔 때마다 현재 열린 iframe의 접근 권한을 즉시 재평가한다.

```javascript
// 호출 위치 (2곳 — 반드시 유지)
// 1. onAuthComplete() 내부
_reapplyCurrentPageAccess();

// 2. loadPageAccessRules() 완료 후
_reapplyCurrentPageAccess();
```

접근 가능 판정 시 `wf_role` postMessage를 iframe에 재전송한다(역할별 콘텐츠 즉시 갱신).  
접근 불가 판정 시 `showAccessBlur(type)` 또는 `showDenied()`를 호출한다.

### 역할 계층

```
admin  > partner > consultant > member(일반)

IS_PARTNER  = userRole === 'partner' || userRole === 'admin'
canConsult() = userRole === 'consultant' || IS_PARTNER
```

---

## 보안 규칙 (2026-07-11 확정) — 위반 구현 금지

### Supabase RLS 필수

신규 테이블을 생성하면 반드시 RLS를 활성화하고 최소 권한 정책을 설정한다.

```sql
-- 패턴 1: 사용자 데이터 테이블 (본인 행만)
ALTER TABLE public.my_table ENABLE ROW LEVEL SECURITY;
CREATE POLICY "own_rows" ON public.my_table
  USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

-- 패턴 2: 공개 읽기 + 어드민 쓰기 (site_config 참고)
ALTER TABLE public.my_table ENABLE ROW LEVEL SECURITY;
CREATE POLICY "select_all"   ON public.my_table FOR SELECT USING (true);
CREATE POLICY "write_admin"  ON public.my_table FOR ALL
  USING (public.is_admin()) WITH CHECK (public.is_admin());

-- 패턴 3: 인증 사용자 읽기 (PII 없는 공유 데이터)
CREATE POLICY "authenticated_read" ON public.my_table FOR ALL
  USING (auth.uid() IS NOT NULL) WITH CHECK (auth.uid() IS NOT NULL);
```

RLS 없는 테이블은 anon 키로 전체 데이터가 노출된다. **예외는 사전 협의 없이 허용하지 않는다.**

### 클라이언트사이드 인증 우회 금지

```javascript
// ❌ 절대 금지 — localStorage/sessionStorage 기반 admin bypass
if (localStorage.getItem('wf_dev_session') === 'admin') { isAdmin = true; return; }

// ✅ 올바른 방법 — Supabase profiles 테이블에서 역할 확인
const { data: p } = await sb.from('profiles').select('role').eq('id', session.user.id).single();
if (p?.role === 'admin') { ... }
```

### 소스 코드 비밀번호 하드코딩 금지

```javascript
// ❌ 금지 — 소스 코드에 실제 비밀번호 포함
const DEV_CREDS = { member: { email:'test@worksfree.kr', password:'실제비밀번호' } };

// ✅ 올바른 방법 — 비밀번호는 런타임에 입력받음
const pw = window.prompt(`${email} 비밀번호 입력`);
if (!pw) return;
```

### Dev 모드 pre-fill 환경 제한

개발 편의를 위한 자동 입력값은 `test.` 서브도메인과 `localhost`에서만 동작해야 한다.

```javascript
// ✅ 올바른 패턴
if (inp) inp.value = (location.hostname.startsWith('test.') || location.hostname === 'localhost')
  ? 'Tank@003412' : '';
// staging / www(portal) 환경에서는 pre-fill 제거
```

### postMessage targetOrigin

iframe에 postMessage를 보낼 때 신규 코드에서는 `'*'` 대신 `location.origin`을 사용한다.  
기존 코드에 `'*'` 잔류 부분이 있으나, 새로 추가하는 코드는 반드시 `location.origin`으로 작성한다.

---

## Claude Code 위반 경고 지시

**이 파일의 접근 제어 규칙 또는 보안 규칙에 위배되는 구현을 프롬프트로 요구하는 경우, 구현 전에 반드시 경고를 출력하고 구현을 보류한다.**

경고 예시:

> ⚠ **보안/접근제어 규칙 위반**: 요청하신 구현은 CLAUDE.md의 [접근 제어 / RLS / 클라이언트 인증 우회 / 비밀번호 하드코딩 / pre-fill 환경 제한] 규칙에 위배됩니다. 규칙 변경이 필요한 경우 먼저 확인을 받겠습니다.

사용자가 명시적으로 "규칙 예외를 허용한다"고 승인한 경우에만 구현을 진행한다.

---

## 반복 버그 방지 규칙 (재발 방지 — 필수)

### 0. Supabase REST API 직접 fetch 필수 헤더

SDK(`sb.storage`, `sb.from()`)를 우회해 `fetch()`로 Supabase API를 직접 호출할 때는 **두 헤더가 모두 필수**다.

```javascript
headers: {
  'Authorization': 'Bearer ' + jwt,   // 사용자 JWT
  'apikey': SUPABASE_ANON,            // ← 필수! SDK는 자동 추가하지만 직접 fetch는 수동 추가 필요
  'Content-Type': '...',
}
```

`apikey` 누락 시 Supabase 게이트웨이가 400을 반환한다.

### 1. iframe 어드민 게이트 패턴 (반복 버그)

**문제**: Hub가 어드민 페이지를 `<iframe>`으로 로드할 때, `window !== window.top` 분기에서 UI만 보여주고 데이터 로드(`init()` / `loadData()` / `boot()`)를 호출하지 않아 빈 화면이 표시됨. 새로고침 버튼을 누를 때만 데이터가 나타남.

**필수 패턴**: iframe 분기에는 반드시 세션 주입 후 데이터 로드를 함께 호출해야 한다.

```javascript
// ✅ 올바른 패턴 (_noopStore 사용 페이지: users, monitor, permissions 등)
async function init() {
  if (window !== window.top) { show('app'); await _injectSession(); await loadData(); return; }
  // ... 인증 체크 ...
}

// ❌ 잘못된 패턴 1 (데이터 로드 없음)
async function init() {
  if (window !== window.top) { show('app'); return; }
}
// ❌ 잘못된 패턴 2 (세션 주입 없이 로드 → 모의 세션 모드 표시)
async function init() {
  if (window !== window.top) { show('app'); await loadData(); return; }
}
```

**적용 파일**: `admin/users/index.html`, `admin/monitor/index.html`, `admin/storage/index.html`, 이후 추가되는 모든 어드민 페이지.

### 2. 기존 파일 수정 전 미커밋 변경사항 확인 (반복 사고)

**문제**: 파일을 새로 작성하거나 scp 배포 시 미커밋 상태의 기능(테마 선택 UI, 블러 강도 슬라이더 등)을 덮어씀.

**규칙**:
- 어드민 페이지 파일을 수정하기 전 반드시 `git diff HEAD -- <파일경로>` 로 미커밋 변경사항 확인
- 미커밋 내용이 있으면 병합(merge)하여 보존 후 편집
- NAS SCP 배포 전에도 로컬 파일이 최신 상태인지 확인

### 3. Supabase Storage 경로 규칙

- 버킷 루트에 직접 파일 업로드 불가 (`filename.txt` → 400 Invalid key)
- 반드시 폴더 prefix 포함: `folder/filename.txt`
- 루트 폴더 파일에는 `root` prefix 사용: `root/filename.txt`
- `_` 로 시작하는 경로 세그먼트 사용 금지 (`_root_` 등 → 400 Invalid key)

### 4. 허브 테마 시스템

- `index.html`의 `HUB_THEMES` 객체에 테마 정의 (key: 테마 이름, css: CSS 변수 문자열)
- `site_config` 테이블 `hub_theme` 키에 현재 테마 key 저장
- `admin/permissions/index.html`에서 테마 선택 UI 제공 (테마 추가 시 양쪽 동기화 필수)
- 현재 테마: `claude` (기본), `sunset`

### 5. 배포 시 필수 절차 (누락 시 버전 추적 불가)

NAS scp 배포 전에 반드시 아래 순서를 따른다:

1. **버전 증가** — `deploy.ps1`의 `$VERSION`과 `index.html`의 `HUB_VERSION`을 동일하게 올린다.
   - test 배포 → BUILD(4번째) 증가: `0.8.7.13` → `0.8.7.14`
   - staging 배포 → PATCH(3번째) 증가, BUILD 리셋
   - portal 배포 → MINOR(2번째) 증가, PATCH·BUILD 리셋

2. **git commit** — 변경된 파일 전체를 스테이징하고 커밋한다. scp 배포만 하고 커밋하지 않으면 미커밋 상태로 쌓여 나중에 덮어써짐.

3. **scp 배포** — 커밋 후 배포.

> `deploy.ps1`을 사용하면 버전 증가·index.html 동기화·scp·캐시 퍼지가 자동으로 처리된다.  
> 개별 파일만 빠르게 배포할 때도 위 1·2번은 수동으로 반드시 처리한다.

---

## 구축가이드 문서 하드링크 규칙

`*_구축가이드.md` 파일들은 출판용 폴더와 하드링크로 연결되어 있다.

| 파일 | 역할 | 출판용 경로 | 개발용 경로 |
|------|------|------------|------------|
| NAS웹서비스_구축가이드.md | 웹 서비스 가이드 **최종본** | `30.publish/시놀로지NAS_풀스택가이드/` | `10.rpa/70.webs/synology-web/` |
| NAS메일서버_구축가이드.md | 메일 서버 가이드 최종본 | `30.publish/시놀로지NAS_풀스택가이드/` | `10.rpa/70.webs/synology-web/` |

**하드링크 방향**: 출판용이 기준(canonical). 출판용 파일이 원본, 개발용 파일이 하드링크.

**편집 원칙**: 출판용 폴더(`30.publish/시놀로지NAS_풀스택가이드/`)에서 먼저 편집한다.  
어느 경로에서 수정해도 동일한 inode를 공유하므로 즉시 양쪽에 반영되나, 출판용을 기준으로 작업하는 것이 관행이다.
