# 시놀로지 NAS 웹서비스 완전 구축 가이드
**최종 업데이트:** 2026년 5월 17일  
**대상 도메인:** `worksfree.kr` (예시 — 실제 운영: `worksfree.co.kr`)  
**환경:** 시놀로지 NAS + Cloudflare Tunnel + Windows 배포 + Supabase Auth  
**목적:** SOHO 수준의 최저 비용으로 test/staging/portal 3단계 웹서비스 + 소셜·이메일 회원가입 구축

---

## 📖 목차

0. [시작 전 반드시 확인 — 사전 조건](#0-시작-전-반드시-확인--사전-조건)
1. [전체 구조 이해](#1-전체-구조-이해)
2. [시놀로지 NAS 기초 설정](#2-시놀로지-nas-기초-설정)
3. [Cloudflare Tunnel 설정](#3-cloudflare-tunnel-설정)
4. [Windows 배포 환경 설정](#4-windows-배포-환경-설정)
5. [Supabase 프로젝트 설정](#5-supabase-프로젝트-설정)
6. [Google OAuth 설정](#6-google-oauth-설정)
7. [Kakao OAuth 설정](#7-kakao-oauth-설정)
8. [이메일+비밀번호 회원가입 구현](#8-이메일비밀번호-회원가입-구현)
9. [개인정보 동의 처리](#9-개인정보-동의-처리)
10. [전체 연동 테스트 체크리스트](#10-전체-연동-테스트-체크리스트)
11. [반복 테스트 방법](#11-반복-테스트-방법)
12. [용어 사전](#12-용어-사전)

---

## 0. 시작 전 반드시 확인 — 사전 조건

> ⚠️ **이 섹션을 건너뛰면 이후 모든 단계가 실패합니다.**

### 0-1. 도메인 등록 (필수 — 없으면 아무것도 안 됨)

**도메인이 등록되어 있지 않으면?**  
Cloudflare에 추가 자체가 불가능합니다. 서브도메인(`test.worksfree.kr`)이 존재하지 않으므로 인터넷 어디서도 접속할 수 없습니다.

| 등록사 | 사이트 | `.kr` 연간 비용 |
|--------|--------|----------------|
| 가비아 | gabia.com | 약 22,000원/년 |
| 후이즈 | whois.co.kr | 약 22,000원/년 |
| 아이네임즈 | inames.co.kr | 약 22,000원/년 |

> ℹ️ 도메인 등록 후 Cloudflare 설정까지 완료해야 실제 사용 가능합니다.

### 0-2. Cloudflare 계정 (필수)

https://cloudflare.com 무료 계정. DNS 관리 + HTTPS + Tunnel 기능 무료 제공.

### 0-3. 시놀로지 NAS (필수)

- DSM 7.x 이상 권장
- **Container Manager** 설치 가능 모델 필요 (패키지 센터에서 확인)
- J 시리즈 일부 저가 모델은 Docker 미지원 → Cloudflare Tunnel 설치 불가

### 0-4. 공유기 고정 IP 설정 (권장)

> ⚠️ NAS 내부 IP가 바뀌면 Cloudflare 라우팅 전체를 다시 설정해야 합니다.

공유기 관리 페이지 → **DHCP 고정 할당** → NAS MAC 주소에 고정 IP 지정 (예: `192.168.100.38`)

### 0-5. Windows 개발 환경

| 도구 | 용도 | 비고 |
|------|------|------|
| Git for Windows | tar+SSH 배포 (Git Bash 포함) | 필수 |
| OpenSSH 클라이언트 | SSH 키 생성 | Windows 10/11 기본 포함 |
| PowerShell 5.1+ | deploy.ps1 실행 | Windows 기본 포함 |

### 0-6. 사전 조건 체크리스트

- [ ] 도메인 등록 완료 + 등록사 네임서버 변경 권한 확보
- [ ] Cloudflare 계정 생성
- [ ] 시놀로지 NAS 전원 ON + DSM 접속 가능 + Container Manager 지원 모델
- [ ] NAS 내부 고정 IP 설정
- [ ] Git for Windows 설치

---

## 1. 전체 구조 이해

```
[사용자 브라우저]
       ↓  https://portal.worksfree.kr
[Cloudflare CDN + 자동 HTTPS]
       ↓  Zero Trust Tunnel (포트 포워딩 불필요, 암호화)
[시놀로지 NAS — Web Station / Nginx]
       ↓  HTTP 내부 포트
[/volume1/web/portal/  ← HTML/CSS/JS 정적 파일]
       ↓  Supabase JS SDK (CDN)
[Supabase Cloud — Auth + PostgreSQL DB]
```

**3단계 배포 환경 (비용: 전기료 + 도메인비만 발생)**

| 환경 | 용도 | URL | NAS 경로 | 포트 |
|------|------|-----|----------|------|
| test | 개발 중 기능 검증 | test.worksfree.kr | /volume1/web/test | 8081 |
| staging | 배포 전 최종 점검 | staging.worksfree.kr | /volume1/web/staging | 8082 |
| portal | 실 서비스 (Production) | portal.worksfree.kr | /volume1/web/portal | 8080 |

**비용 구조 요약**

| 항목 | 비용 |
|------|------|
| 시놀로지 NAS | 초기 구매비 (이후 전기료만) |
| Cloudflare | 무료 (Free 플랜) |
| Supabase | 무료 (Free 플랜: 50,000 MAU, 500MB DB) |
| 도메인 | 연 22,000원~ |
| Google/Kakao OAuth | 무료 |

---

## 2. 시놀로지 NAS 기초 설정

### 2-1. Web Station 설치

DSM → **패키지 센터** → `Web Station` 검색 → 설치 → 실행

### 2-2. 웹 서비스 3개 생성

> ⚠️ **실수 포인트:** **웹 서비스**(백엔드)와 **웹 포털**(포트 연결)을 **둘 다** 만들어야 합니다.  
> 웹 서비스만 만들고 포털을 안 만들면 외부에서 접속 불가.

**웹 서비스** (Web Station → 웹 서비스 탭 → 생성):

| 항목 | test | staging | portal |
|------|------|---------|--------|
| 이름 | web-test | web-staging | web-portal |
| 문서 루트 | /volume1/web/test | /volume1/web/staging | /volume1/web/portal |
| 백엔드 | Nginx | Nginx | Nginx |

**웹 포털** (Web Station → 웹 포털 탭 → 생성):

| 항목 | test | staging | portal |
|------|------|---------|--------|
| 포털 유형 | 포트 기반 | 포트 기반 | 포트 기반 |
| HTTP 포트 | 8081 | 8082 | 8080 |
| 연결 서비스 | web-test | web-staging | web-portal |

### 2-3. 웹 루트 폴더 생성

> ⚠️ **실수 포인트:** 폴더가 없으면 배포 후 404 오류.

DSM → **File Station** → `/volume1/web/` 아래에 `test`, `staging`, `portal` 폴더 생성

### 2-4. SSH 활성화

DSM → **제어판** → **터미널 및 SNMP** → **SSH 서비스 활성화** → 포트 `22` → 적용

### 2-5. 내부망 접속 확인

배포 전 내부 Wi-Fi에서 브라우저로 확인:
- `http://192.168.100.38:8080` → portal
- `http://192.168.100.38:8081` → test
- `http://192.168.100.38:8082` → staging

---

## 3. Cloudflare Tunnel 설정

### 3-1. 도메인 네임서버 이관

> ⚠️ **전제 조건:** 도메인이 등록된 상태여야 합니다.

**이관이 필요한 이유:** 도메인 등록사가 기본 DNS를 제공하지만, Cloudflare의 Tunnel·CDN·HTTPS를 쓰려면 DNS 관리 권한을 Cloudflare로 이전해야 합니다.

1. Cloudflare 로그인 → **Add a site** → 도메인 입력 → Free 요금제
2. DNS 스캔 결과 0개여도 정상 → **Continue**
3. Cloudflare가 제공하는 네임서버 2개 복사 *(매번 다르게 배정됨)*
4. 도메인 등록사(가비아 등) → 네임서버 설정 → 기존 전체 삭제 후 Cloudflare 2개 입력
5. **Done, check nameservers** 클릭

> ⚠️ 반영까지 최대 24시간. 보통 10분~2시간. Cloudflare 대시보드 상태가 **Active**이면 완료.

### 3-2. Zero Trust Tunnel 생성

Cloudflare Dashboard → **Zero Trust** → **Networks** → **Tunnels** → **Create a tunnel** → 이름 입력 → Next

### 3-3. NAS에 Tunnel Connector 설치 (Docker)

> ⚠️ **실수 포인트:** 화면에 Windows 설치가 기본으로 표시됩니다.  
> 상단 운영체제 탭에서 반드시 🐋 **Docker** 를 클릭하세요.

1. `--token` 뒤의 긴 문자열만 복사
2. NAS → **Container Manager** → **프로젝트** → **생성**
3. Docker Compose 입력:

```yaml
version: '3.9'
services:
  cloudflare-tunnel:
    container_name: cloudflare-tunnel
    image: cloudflare/cloudflared:latest
    restart: unless-stopped
    command: tunnel --no-autoupdate run --token 여기에_토큰_붙여넣기
```

4. 저장 → 시작 → Cloudflare에서 터널 상태 **HEALTHY** 확인

### 3-4. 서브도메인 라우팅 3개 설정

> ⚠️ **실수 포인트:**  
> - ❌ `Hostname routes Beta` — 기업 내부망 전용. 절대 사용 금지.  
> - ⭕ `Published application routes` (= `Public Hostname`) — 이것만 사용.

터널 → **Configure** → **Public Hostname** → **Add a public hostname**:

| Subdomain | Domain | Service Type | Service URL |
|-----------|--------|-------------|-------------|
| test | worksfree.kr | HTTP | http://192.168.100.38:8081 |
| staging | worksfree.kr | HTTP | http://192.168.100.38:8082 |
| portal | worksfree.kr | HTTP | http://192.168.100.38:8080 |

> ⚠️ **실수 포인트:** Service URL에 `localhost` 사용 절대 금지.  
> Docker 컨테이너 내부에서 `localhost`는 컨테이너 자신입니다. 반드시 NAS 실제 IP를 사용하세요.

스마트폰 LTE(Wi-Fi OFF)로 `https://test.worksfree.kr` 접속 확인.

---

## 4. Windows 배포 환경 설정

### 4-1. SSH 키 생성 및 NAS 등록 (최초 1회)

Git Bash에서:

```bash
ssh-keygen -t ed25519
ssh-copy-id wfadmin@192.168.100.38
```

> ℹ️ NAS 재부팅 후 비밀번호를 다시 요구하면 `ssh-copy-id`를 한 번 더 실행하세요.

### 4-2. deploy.ps1 — 3단계 + 파트너 배포 스크립트

**실행 방법 (택 1):**
- `deploy.bat` 더블클릭
- PowerShell: `.\deploy.ps1`
- VS Code: `Ctrl+Shift+B`

**실행 흐름:**
```
[1] test          → 기능 검증 (즉시 배포)
[2] staging       → 최종 점검 (즉시 배포)
[3] portal        → 실 서비스 ('yes' 입력 이중 확인 후 배포)
[4] g1consulting  → GFC 파트너 전용 서버
[Q] 취소 / [R] 롤백
```

**배포 시 자동 처리:**

| 단계 | 내용 |
|------|------|
| ① 버전 증가 | 환경에 따라 자리수 선택 (test·g1=4번째, staging=3번째, portal=2번째) |
| ② index.html 동기화 | `HUB_VERSION` 상수를 새 버전으로 자동 업데이트 |
| ③ tar+SSH 전송 | Git Bash tar로 묶어 SSH 파이프 전송 (Google Drive 파일 포함) |
| ④ Cloudflare 캐시 퍼지 | 배포 후 Edge 캐시 자동 초기화 (`purge_everything`) |
| ⑤ 배포 검증 | NAS SSH 접속 → index.html 존재 여부 확인 |

**브라우저 캐시 버스팅:**  
`HUB_VERSION` 값이 매 배포마다 바뀌므로, iframe URL(`?v=HUB_VERSION`)도 함께 바뀐다.  
Cloudflare 퍼지는 Edge 캐시만 지우지만, URL 변경은 브라우저 로컬 캐시도 우회한다.

> ⚠️ Q(취소)·R(롤백) 선택 시 버전이 증가하지 않습니다.

### 4-3. Google Drive 경로에서 배포 시 주의사항

> ⚠️ **배경:** 이 프로젝트는 `D:\drive_files\`(Google Drive for Desktop 마운트)에 위치합니다.  
> Windows `scp -r`은 클라우드 전용(오프라인) 파일의 `readdir()`이 빈 목록을 반환해 파일을 건너뜁니다.

**해결책 (deploy.ps1 적용됨):** Git Bash의 `tar`로 전체 압축 → SSH 파이프로 NAS에 전달 → NAS에서 압축 해제.  
tar는 파일 내용을 직접 `read()` syscall로 읽으므로 Google Drive 강제 다운로드가 유발되어 클라우드 전용 파일도 누락 없이 전송됩니다.

```bash
# deploy.ps1 내부 핵심 명령 (참고용)
tar -czf - --exclude='.git' --exclude='*.log' . \
  | ssh user@nas-ip 'tar -xzf - -C /volume1/web/test/ --no-same-permissions --no-same-owner 2>/dev/null; exit 0'
```

> ⚠️ `--no-same-permissions --no-same-owner 2>/dev/null; exit 0` 없으면  
> NAS의 BusyBox tar가 디렉토리 권한 변경 실패 오류를 내며 배포 실패로 잘못 판정됩니다.

### 4-4. 배포 실패 시 체크리스트

1. NAS IP 확인 (`192.168.100.38`)
2. SSH 활성화: DSM → 제어판 → 터미널 및 SNMP
3. SSH 키 등록: `ssh wfadmin@192.168.100.38` 접속 테스트
4. 폴더 존재: `/volume1/web/test`, `/volume1/web/staging`, `/volume1/web/portal`

---

## 5. Supabase 프로젝트 설정

### 5-1. 프로젝트 생성

https://supabase.com → **New project** → 이름, DB 비밀번호, 리전(Northeast Asia - Seoul) 입력 → 약 2분 대기

### 5-2. API 키 확인

> ⚠️ **실수 포인트:** 정확한 경로를 찾아야 합니다.

- **Project URL**: Settings → API → URL 항목
- **Anon Key**: Settings → API → API Keys → `anon public` 항목

> `service_role` 키는 절대 프론트엔드 코드에 노출하지 마세요.

### 5-3. HTML에 키 입력

```javascript
const SUPABASE_URL  = 'https://YOUR_PROJECT_ID.supabase.co';
const SUPABASE_ANON = 'eyJhbGci...'; // anon public 키만 사용
```

### 5-4. URL Configuration 설정

> ⚠️ **실수 포인트:** 이 설정이 없으면 OAuth 로그인 및 매직 링크가 차단됩니다.

**Authentication → URL Configuration**:

- **Site URL**: `https://portal.worksfree.kr` (기본 리다이렉트 주소)
- **Redirect URLs** — 아래 4개 모두 등록:

```
https://test.worksfree.kr/**
https://staging.worksfree.kr/**
https://portal.worksfree.kr/**
http://localhost:*/**
```

> ℹ️ 코드에서 `emailRedirectTo: location.origin + location.pathname`을 명시하면  
> 각 환경(test/staging/portal)에서 로그인 후 해당 환경으로 자동 복귀합니다.

### 5-5. Email Provider 설정

**Authentication → Sign In / Providers → Email**:

| 설정 | 권장값 | 설명 |
|------|--------|------|
| Enable Email Signup | ON | 이메일 회원가입 허용 |
| Confirm Email | ON | 매직 링크 인증 필수화 |
| Secure Email Change | ON | 이메일 변경 시 인증 |

### 5-6. profiles 테이블 생성

> ⚠️ **실수 포인트:** Supabase는 `auth.users`(자동)와 `public.profiles`(커스텀)를 분리합니다.  
> profiles 없으면 개인정보 동의 저장 및 회원 등급 관리 불가.

**SQL Editor → New query** → 실행:

```sql
CREATE TABLE IF NOT EXISTS public.profiles (
  id               uuid REFERENCES auth.users ON DELETE CASCADE PRIMARY KEY,
  agreed_at        timestamptz,
  marketing_agreed boolean DEFAULT false,
  role             text DEFAULT 'member',
  created_at       timestamptz DEFAULT now()
);

ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;

CREATE POLICY "본인만 조회·수정" ON public.profiles
  FOR ALL USING (auth.uid() = id);

-- 신규 가입 시 자동으로 profiles 행 생성
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO public.profiles (id)
  VALUES (new.id)
  ON CONFLICT (id) DO NOTHING;
  RETURN new;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE OR REPLACE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();
```

**Run** → `Success` 확인

---

## 6. Google OAuth 설정

### 6-1. Google Cloud Console

1. https://console.cloud.google.com → 프로젝트 생성
2. **APIs & Services → OAuth consent screen** → External → 앱 이름·이메일 저장
3. **Credentials → Create Credentials → OAuth client ID**
   - Type: Web application
   - Authorized redirect URIs: `https://YOUR_PROJECT_ID.supabase.co/auth/v1/callback`
4. **Client ID**, **Client Secret** 복사

### 6-2. Supabase Google Provider 설정

> ⚠️ **실수 포인트:** Providers는 **조직 레벨이 아닌 프로젝트 안**에 있습니다.  
> Supabase 접속 후 반드시 프로젝트 카드를 클릭해 프로젝트 대시보드로 진입하세요.

Authentication → **Sign In / Providers** → **Google**:

| 항목 | 값 |
|------|-----|
| Enable | ON |
| Client ID | Google Client ID |
| Client Secret | Google Client Secret |

Save → Supabase가 표시하는 **Callback URL** 복사

### 6-3. Google Console에 Callback URL 등록

> ⚠️ **실수 포인트:** 이 단계 누락 시 `redirect_uri_mismatch` 오류 발생.

Google Console → Credentials → OAuth 클라이언트 수정 → Authorized redirect URIs에 Supabase Callback URL 추가

---

## 7. Kakao OAuth 설정

### 7-1. 앱 생성 및 REST API 키 확인

1. https://developers.kakao.com → 내 애플리케이션 → 애플리케이션 추가
2. **앱 키 탭** → **REST API 키** 복사 (Supabase Client ID로 사용)

### 7-2. 카카오 로그인 활성화

> ⚠️ **실수 포인트:** 활성화 전에는 하위 설정들이 저장되지 않습니다.

카카오 로그인 → **일반** → **활성화 설정 → ON**

### 7-3. Redirect URI 등록

카카오 로그인 → 일반 → Redirect URI:
```
https://YOUR_PROJECT_ID.supabase.co/auth/v1/callback
```

### 7-4. Client Secret (비즈 앱 전용)

> ℹ️ **보안 탭이 없는 이유:** 비즈 앱 전환 전에는 보안 탭이 표시되지 않습니다.  
> 개인 개발자 앱은 Client Secret 없이 REST API 키만으로 작동합니다.

### 7-5. 동의항목 설정

| 항목 | 설정 | 비고 |
|------|------|------|
| 닉네임 | 필수 동의 | |
| 프로필 사진 | 선택 동의 | |
| 카카오계정(이메일) | 선택 동의 | 카카오 정책상 필수 불가 — null 처리 필요 |

### 7-6. Supabase Kakao Provider 설정

> ⚠️ **실수 포인트:** 활성화 누락 시 `"Unsupported provider: provider is not enabled"` 오류.

Authentication → Sign In / Providers → **Kakao**:

| 항목 | 값 |
|------|-----|
| Enable | ON |
| Client ID | REST API 키 |
| Client Secret | 비워두기 (비즈 앱 아닌 경우) |

---

## 8. 이메일+비밀번호 회원가입 구현

소셜 로그인 없이 이메일+비밀번호로 가입하는 방식. 매직 링크로 이메일 소유를 검증합니다.

### 8-1. 가입 흐름

```
① 이름 / 이메일 / 비밀번호 / 비밀번호 확인 입력
② "인증 메일 받기" 클릭
   → Supabase가 매직 링크 이메일 발송
   → UI: "이메일의 링크를 클릭하면 자동으로 가입이 완료됩니다"
③ 사용자가 이메일의 링크 클릭
   → 가입 시 사용한 환경(test/staging/portal)으로 리다이렉트
   → onAuthStateChange 발화 → 비밀번호·이름 자동 설정
④ 개인정보 동의 모달 표시 → 동의 → 로그인 완료
```

### 8-2. 매직 링크란?

일반 이메일+비밀번호 가입에서 흔히 쓰는 "이메일 인증 링크 클릭" 방식입니다.  
Supabase가 발송하는 이메일에 포함된 버튼/링크를 클릭하면 이메일 소유가 증명되고 계정이 활성화됩니다.

> ℹ️ 6자리 숫자 OTP(번호 입력 방식)는 Supabase에서 SMS 전화번호 인증에 사용됩니다.  
> 이메일 방식은 매직 링크(클릭 방식)가 기본입니다.

### 8-3. 환경별 리다이렉트 처리

```javascript
// 가입 시 현재 환경 URL로 돌아오도록 명시
await supabase.auth.signInWithOtp({
  email,
  options: {
    shouldCreateUser: true,
    emailRedirectTo: location.origin + location.pathname  // 현재 환경 자동 감지
  }
});
```

| 가입 환경 | 링크 클릭 후 이동 |
|----------|-----------------|
| test.worksfree.kr | test.worksfree.kr |
| staging.worksfree.kr | staging.worksfree.kr |
| portal.worksfree.kr | portal.worksfree.kr |

### 8-4. 비밀번호 보안 처리

매직 링크 클릭 후 리다이렉트가 발생하므로 JavaScript 메모리의 비밀번호가 초기화됩니다.  
이를 방지하기 위해 `sessionStorage`에 임시 저장합니다.

```javascript
// 발송 전: sessionStorage에 임시 저장
sessionStorage.setItem('wf_signup_pw',   pw);
sessionStorage.setItem('wf_signup_name', name);

// 리다이렉트 후 onAuthStateChange 발화 시: 비밀번호 설정 후 삭제
const pw = sessionStorage.getItem('wf_signup_pw');
if (pw) {
  await supabase.auth.updateUser({ password: pw });
  sessionStorage.removeItem('wf_signup_pw');
  sessionStorage.removeItem('wf_signup_name');
}
```

### 8-5. 이메일 오류 방지

- 미인증 상태로 로그인 시도 → "이메일 인증 필요" 메시지 + **인증 메일 재발송** 링크 표시
- 이메일 변경 필요 시 → "← 이메일 변경" 링크로 Step1 복귀
- 링크 재발송 → "링크 재발송" 링크

---

## 9. 개인정보 동의 처리

### 9-1. 동의 시점

소셜 로그인 또는 이메일 가입 후 **최초 1회** 동의 모달이 표시됩니다.  
이후 재로그인 시에는 동의 모달이 표시되지 않습니다.

### 9-2. 동의 항목 (한국 개인정보보호법 기준)

| 항목 | 필수 여부 | 내용 |
|------|----------|------|
| 회원 관리 | 필수 | 이름, 이메일, 가입일 수집 |
| RPA 앱 데이터 | 필수 | 앱 실행 결과·로그 이메일 수집 |
| 크레딧 결제 정보 | 필수 | 결제 내역 보관 |
| 마케팅 정보 수신 | 선택 | 이메일·SMS 광고 수신 |

### 9-3. 동의 데이터 저장 구조

```sql
-- profiles 테이블
agreed_at        timestamptz  -- 동의 일시 (NULL이면 미동의)
marketing_agreed boolean      -- 마케팅 선택 동의 여부
```

### 9-4. Supabase 미설정 시 fallback

Supabase가 설정되지 않은 경우 `localStorage`에 동의 기록을 저장합니다.

```javascript
localStorage.setItem('wf_agreed_' + userId, JSON.stringify({
  agreed_at: new Date().toISOString(),
  marketing: marketingAgreed
}));
```

---

## 10. 전체 연동 테스트 체크리스트

### NAS & Cloudflare

- [ ] `http://192.168.100.38:8080` 내부망 접속 확인
- [ ] `https://test.worksfree.kr` 외부망(LTE, Wi-Fi OFF) 접속 확인
- [ ] `https://staging.worksfree.kr` 접속 확인
- [ ] `https://portal.worksfree.kr` 접속 확인

### 배포 스크립트

- [ ] `deploy.ps1` → test 배포 성공 + NAS 파일 검증 OK
- [ ] `deploy.ps1` → staging 배포 성공
- [ ] `deploy.ps1` → portal 배포 성공 (yes 입력)

### 소셜 로그인

- [ ] Google 로그인 → 개인정보 동의 모달 표시 → 동의 완료
- [ ] Supabase Table Editor → profiles 테이블에 행 생성 확인
- [ ] 카카오 로그인 → 동의 모달 → profiles 저장 확인
- [ ] 재로그인 시 동의 모달이 **다시 뜨지 않는지** 확인

### 이메일 회원가입

- [ ] 이메일 탭 → 정보 입력 → "인증 메일 받기" 클릭
- [ ] 해당 이메일 수신 확인 → 링크 클릭
- [ ] 가입한 환경(test/staging/portal)으로 정상 리다이렉트
- [ ] 개인정보 동의 모달 표시 → 동의 완료
- [ ] 이메일+비밀번호로 로그인 가능 확인

---

## 11. 반복 테스트 방법

Google·카카오·이메일 계정으로 가입/동의 흐름을 반복 테스트할 때 사용합니다.

### 방법 1 — 동의만 초기화 (가장 빠름)

계정 유지, 동의 기록만 삭제. 재로그인 시 동의 모달 재표시.

Supabase → **SQL Editor**:
```sql
DELETE FROM public.profiles
WHERE id = (
  SELECT id FROM auth.users WHERE email = '테스트계정@gmail.com'
);
```

### 방법 2 — 계정 완전 삭제 (신규 가입부터 재현)

Supabase → **Authentication → Users** → 해당 계정 → **Delete user**

profiles도 CASCADE로 자동 삭제됩니다.

### 방법 3 — Gmail `+` 별칭 트릭 (이메일 테스트 전용)

```
yourname+test1@gmail.com   ← 동일 Gmail 수신, Supabase에서 별개 계정
yourname+test2@gmail.com
yourname+test3@gmail.com
```

> ⚠️ Google OAuth는 `+` 별칭으로 로그인 불가. 이메일+비밀번호 가입 테스트에만 사용 가능.

### 방법 4 — Dev 모드 (Supabase 없이 UI만 테스트)

```
https://test.worksfree.kr/?dev=1
```

또는 브라우저 콘솔:
```javascript
localStorage.setItem('wf_dev', '1'); location.reload();
```

목업 사용자로 전체 UI(회원 전용 메뉴, 동의 모달 등) 테스트 가능.

---

## 12. 용어 사전

| 용어 | 설명 |
|------|------|
| 네임서버 이관 | 도메인 DNS 관리를 등록사(가비아 등)에서 Cloudflare로 옮기는 작업. Cloudflare Tunnel 사용의 전제 조건 |
| Web Station | 시놀로지 NAS의 웹 서버 관리 패키지. Nginx 기반 |
| Cloudflare Zero Trust | Cloudflare 보안 네트워크. Tunnel 기능으로 공유기 포트 포워딩 없이 외부 접속 가능 |
| Public Hostname | Cloudflare Tunnel에서 외부 도메인과 내부 서비스를 연결하는 라우팅 설정 |
| Hostname routes Beta | 기업 내부망 전용 메뉴. 웹사이트 배포에 사용 금지 |
| tar+SSH | Google Drive 마운트 경로의 클라우드 전용 파일 전송 방법. scp -r 대신 사용 |
| Supabase anon key | 프론트엔드 공개 API 키. service_role 키와 혼동 금지 |
| profiles 테이블 | 동의 정보·회원 등급 등 커스텀 데이터 저장 테이블 (auth.users와 분리) |
| RLS (Row Level Security) | DB 행 단위 접근 제어. `auth.uid() = id` 정책으로 본인 데이터만 접근 |
| 매직 링크 | 이메일로 발송된 클릭 링크로 본인 인증하는 방식. Supabase 이메일 가입의 기본 인증 방법 |
| Redirect URI | OAuth/매직 링크 완료 후 사용자가 돌아올 주소. Supabase와 Google/Kakao 양쪽에 동일 등록 필요 |
| emailRedirectTo | signInWithOtp 호출 시 지정하는 리다이렉트 주소. location.origin으로 환경별 자동 분기 |
| Biz 앱 (카카오) | 사업자 등록 후 전환하는 카카오 앱 유형. 비즈 앱 전환 후에만 Client Secret(보안 탭) 활성화됨 |
| sessionStorage | 브라우저 탭 세션 내 임시 저장소. 매직 링크 리다이렉트 시 비밀번호 유지에 사용 |

---

**[문서 끝]** 이 가이드는 실제 구축 경험을 기반으로 작성되었습니다.
