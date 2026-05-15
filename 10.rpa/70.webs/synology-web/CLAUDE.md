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

## Supabase 설정 필수값

- `SUPABASE_URL` / `SUPABASE_ANON`: `index.html` 상단 상수
- Redirect URLs: `https://test.worksfree.kr/**`, `https://staging.worksfree.kr/**`, `https://portal.worksfree.kr/**`
- Site URL: `https://portal.worksfree.kr`
