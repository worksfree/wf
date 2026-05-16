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
