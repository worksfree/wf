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

허브(`index.html`)는 컨설팅 페이지를 iframe으로 로드한다.  
배포 시 버전이 바뀌면 iframe URL에 `?v=HUB_VERSION`이 붙어 브라우저가 새 리소스로 인식한다.

```javascript
// index.html 내부 — iframe 로드 시점
iframe.src = src + '?v=' + HUB_VERSION;
```

- **왜 필요한가**: Cloudflare 퍼지는 Edge 캐시만 지운다. 브라우저 로컬 캐시는 URL이 달라야 만료된다.
- **효과**: 매 배포마다 `?v=` 값이 달라지므로 사용자가 강제 새로고침 없이도 최신 콘텐츠를 받는다.

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
| portal | portal.worksfree.kr | /volume1/web/portal | 8080 |

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

Site URL: `https://portal.worksfree.kr` (또는 www로 변경 시 `https://www.worksfree.kr`)

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
