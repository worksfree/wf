# Synology NAS 웹서비스 구축 완전 가이드
### Gabia · Cloudflare Tunnel/Worker · Supabase 인증·DB · 역할 기반 접근 제어 · 온라인 결제까지 원스톱

> **대상 독자**: 자체 도메인과 Synology NAS를 보유한 개인·소기업 운영자  
> **전제 조건**: DSM 7.x, Cloudflare Free 플랜, Supabase Free 플랜  
> **예시 도메인**: `example.co.kr` (실제 작업 시 자신의 도메인으로 교체)  
> **실제 구현 사례**: WorksFree Hub (`portal.worksfree.kr`) — 이 가이드의 실례는 이 프로젝트를 기준으로 합니다.

---

## 이 가이드를 읽기 전에 — 전체 그림 먼저 이해하기

### 도메인 + NAS만으로도 웹사이트는 열 수 있다

많은 사람들이 웹사이트를 만들려면 별도의 서버를 빌려야 한다고 생각합니다.  
하지만 집이나 사무실에 **Synology NAS**가 있고 **도메인**을 하나 구입했다면,  
그것만으로 이미 웹사이트를 인터넷에 공개할 수 있습니다.

> NAS는 파일 저장 장치이지만, 동시에 작은 웹 서버이기도 합니다.  
> 도메인은 인터넷 주소입니다. 이 두 가지만 있으면 기본 웹 호스팅이 가능합니다.

### 그런데 왜 다른 서비스들이 필요한가?

기본 웹사이트(정적 페이지)를 넘어서, 아래와 같은 기능이 필요해지면  
각각의 서비스가 추가됩니다.

| 필요한 기능 | 사용하는 서비스 | 이 가이드의 챕터 |
|------------|----------------|----------------|
| 보안·성능 강화, 도메인 관리 | Cloudflare | 2장 |
| 공유기 설정 없이 NAS 외부 공개 | Cloudflare Tunnel | 4장 |
| 외부 API 데이터 가져오기 (예: DART 기업정보) | Cloudflare Worker | 6장 |
| 회원 가입·로그인 (Google, 카카오 등) | Supabase 인증 | 7장 |
| 회원 정보·결제 이력·크레딧 저장 | Supabase 데이터베이스 | 8장 |
| 온라인 결제 (카드·계좌이체) | PG사 연동 (토스페이먼츠 등) | 9장 |

### 이 가이드를 따라가면 만들 수 있는 것

- 내 도메인 주소(`portal.example.co.kr`)로 접속하는 웹사이트
- Google 계정 또는 카카오 계정으로 로그인하는 회원 시스템
- 사용자별 크레딧·결제 이력을 관리하는 데이터베이스
- 온라인 결제 후 크레딧이 자동으로 충전되는 결제 시스템
- 개발용·테스트용·실 서비스용 환경을 분리한 배포 구조

---

## 전체 구성도 — 각 서비스가 하는 역할

```
┌─────────────────────────────────────────────────────────────┐
│  방문자 브라우저                                              │
│  (portal.example.co.kr 접속, 로그인, 결제 등)                │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  Cloudflare                                                  │
│  ① 도메인 주소를 실제 서버로 연결해주는 안내원               │
│  ② 악성 트래픽을 걸러주는 보안 검문소                        │
│  ③ 터널·워커 등 부가 기능 제공                               │
└──────────┬──────────────────────────────┬───────────────────┘
           │ 일반 웹페이지 요청           │ 외부 API 요청
           │ (터널로 NAS에 전달)          │ (Worker가 대신 처리)
           ▼                              ▼
┌──────────────────────┐    ┌─────────────────────────────────┐
│  Cloudflare Tunnel   │    │  Cloudflare Worker               │
│  NAS와 인터넷을      │    │  DART 등 외부 API를 대신         │
│  연결하는 비밀 통로  │    │  호출하는 심부름꾼               │
└──────────┬───────────┘    └─────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────┐
│  Synology NAS                                                │
│  실제 웹 파일(HTML/CSS/JS)이 저장된 내 서버                  │
│  /volume1/web/portal  /volume1/web/test  등                  │
└──────────┬──────────────────────────────┬───────────────────┘
           │ 로그인·회원 확인             │ 결제 요청
           ▼                              ▼
┌──────────────────────┐    ┌─────────────────────────────────┐
│  Supabase 인증       │    │  PG사 (결제대행사)               │
│  Google·카카오 로그인│    │  토스페이먼츠(국내)              │
│  회원 가입·탈퇴 처리 │    │  Stripe(해외)                   │
└──────────┬───────────┘    └─────────────┬───────────────────┘
           │                              │ 결제 완료 통보
           ▼                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Supabase 데이터베이스 (PostgreSQL)                          │
│  · 회원 프로필 (이름, 가입일, 동의 여부)                     │
│  · 결제 이력 (결제일, 금액, 결제수단)                        │
│  · 크레딧 잔액 및 사용 내역                                   │
└─────────────────────────────────────────────────────────────┘
```

> **요약**: 방문자는 도메인 주소 하나로 접속합니다.  
> Cloudflare가 NAS로 연결하고, 로그인은 Supabase가, 결제는 PG사가 처리하며,  
> 모든 데이터는 Supabase 데이터베이스에 안전하게 보관됩니다.

---

## 사전 준비물

| 항목 | 설명 |
|------|------|
| 가비아 계정 | 도메인 등록용 |
| Cloudflare 계정 | cloudflare.com 무료 가입 |
| Synology NAS | DSM 7.x 이상, 유선 LAN 연결, 공유기 내 고정 IP 설정 권장 |
| Supabase 계정 | supabase.com GitHub 로그인 |
| Google Cloud Console 계정 | OAuth 자격증명 발급용 |
| 카카오 개발자 계정 | Kakao OAuth 사용 시 |

---

## 1장. 가비아 — 도메인 구입 및 네임서버 변경

> **이 장에서 하는 이유**  
> 도메인은 웹사이트의 "주소"입니다.  
> 아무리 좋은 웹사이트를 만들어도 주소가 없으면 아무도 찾아올 수 없습니다.  
> `192.168.1.5` 같은 숫자 주소 대신 `portal.example.co.kr` 같은 기억하기 쉬운 주소를 갖기 위해 도메인을 구입합니다.  
>  
> 구입 후 **네임서버를 Cloudflare로 변경**하는 이유는, 가비아보다 Cloudflare의 DNS가 더 많은 기능(터널, 워커, 보안 등)을 제공하기 때문입니다. 도메인 자체는 가비아에 그대로 있고, 주소 안내 역할만 Cloudflare로 넘기는 것입니다.

### 1.1 도메인 구입

1. [gabia.com](https://www.gabia.com) 로그인
2. 상단 검색창에 원하는 도메인 입력 → **[검색]**
3. 원하는 도메인 선택 → 장바구니 → 결제

### 1.2 네임서버를 Cloudflare로 변경

> 가비아의 DNS 대신 Cloudflare DNS를 사용하도록 설정합니다.  
> 이 작업은 Cloudflare에서 네임서버 주소를 확인한 뒤 진행합니다 (2장 참조).

**메뉴 경로**:  
`로그인 → 우측 상단 [My가비아] → 왼쪽 메뉴 [도메인] → 도메인 목록에서 해당 도메인의 [관리] 버튼`

1. **[네임서버]** 탭 클릭
2. **[설정]** 버튼 클릭
3. 네임서버 1, 2에 Cloudflare에서 받은 네임서버 주소 입력  
   (예: `aria.ns.cloudflare.com`, `ben.ns.cloudflare.com`)
4. **[적용]** 클릭

> ⏱ 네임서버 변경은 전파에 최대 48시간이 걸립니다.  
> 실제로는 보통 30분~2시간 내에 완료됩니다.

---

## 2장. Cloudflare — 계정 설정 및 도메인 등록

> **이 장에서 하는 이유**  
> Cloudflare는 전 세계 300개 이상의 도시에 서버를 두고 있는 인터넷 인프라 회사입니다.  
> 이 가이드에서 Cloudflare를 사용하는 이유는 세 가지입니다.  
> ① **보안**: 악성 봇이나 공격 트래픽을 NAS에 도달하기 전에 차단  
> ② **무료 HTTPS**: 모든 서브도메인에 자동으로 자물쇠(보안 인증서)를 달아줌  
> ③ **터널·워커**: 공유기 포트포워딩 없이 NAS를 공개하고, 외부 API를 안전하게 중계  
>  
> 이 모든 기능이 **무료 플랜**으로 제공됩니다.

### 2.1 Cloudflare 계정 생성

1. [cloudflare.com](https://www.cloudflare.com) → 우측 상단 **[Sign Up]**
2. 이메일 · 비밀번호 입력 → **[Create Account]**
3. 이메일 인증 완료

### 2.2 도메인 추가 (Add a Site)

**메뉴 경로**:  
`대시보드 홈 → 상단 또는 우측의 [Add a site] 버튼`

1. 도메인 입력 (예: `example.co.kr`) → **[Add site]**
2. 플랜 선택 → **Free** → **[Continue]**
3. 기존 DNS 레코드 검색 결과 화면 → 내용 확인 후 **[Continue]**
4. **Cloudflare 네임서버 2개 주소** 화면 표시 → 복사해둠
5. **[Done, check nameservers]** 클릭

> 이 네임서버 주소를 가비아 1.2 단계에서 입력합니다.

### 2.3 SSL/TLS 모드 설정

**메뉴 경로**:  
`대시보드 → 해당 도메인 선택 → 왼쪽 사이드바 [SSL/TLS] → Overview`

- 암호화 모드: **Full (strict)** 선택

> NAS에 자체 서명 인증서가 있거나 Let's Encrypt를 사용한다면 **Full (strict)**을 권장합니다.  
> NAS에 별도 인증서가 없으면 임시로 **Full**을 사용합니다.

### 2.4 HTTPS 자동 리디렉션 설정

**메뉴 경로**:  
`SSL/TLS → Edge Certificates`

- **Always Use HTTPS**: 토글 **ON**
- **Automatic HTTPS Rewrites**: 토글 **ON**

---

## 3장. Synology NAS — DSM 7.x 웹 서비스 설정

### 3.1 SSH 활성화

**메뉴 경로**:  
`DSM 로그인 → 제어판 → 터미널 및 SNMP → [터미널] 탭`

1. **SSH 서비스 활성화** 체크박스 ON
2. 포트: **22** (기본값, 변경 권장)
3. **[적용]** 클릭

### 3.2 사용자 홈 폴더 활성화

> SSH 키 인증에 필요한 `~/.ssh` 경로가 생성되려면 홈 폴더 서비스가 활성화되어야 합니다.

**메뉴 경로**:  
`제어판 → 사용자 및 그룹 → [고급] 탭`

- **사용자 홈 서비스 활성화** 체크박스 ON → **[적용]**

### 3.3 Web Station 설치

**메뉴 경로**:  
`DSM 메인 화면 → 패키지 센터 → 검색창에 "Web Station" 입력`

1. **Web Station** → **[설치]**
2. 의존성 패키지 설치 안내 팝업 → **[예]**  
   (Nginx, PHP 등 자동 선택됨)
3. 설치 완료 후 **[열기]**

### 3.4 웹 서비스 포털 생성 (가상 호스트)

> 서브도메인별로 다른 폴더를 서빙하기 위해 가상 호스트를 설정합니다.

**메뉴 경로**:  
`Web Station → 상단 탭 [웹 서비스 포털] → [생성] 버튼`

1. 포털 유형: **가상 호스트 기반의 웹 서비스** → **[다음]**
2. 설정 입력:

| 항목 | 입력값 |
|------|--------|
| 포털 이름 | `portal` |
| 호스트 이름 | `portal.example.co.kr` |
| HTTP 포트 | `8080` |
| HTTPS 포트 | `비워두기` (Cloudflare Tunnel이 처리) |
| 백엔드 서버 | Nginx |
| PHP | 필요 없으면 없음 |
| 문서 루트 | `/volume1/web/portal` |

3. **[완료]**

> 서브도메인별로 이 과정을 반복합니다.  
> 예: `test` → 포트 `8081` → 문서 루트 `/volume1/web/test`

**문서 루트 폴더 생성** (SSH 또는 File Station에서):
```bash
mkdir -p /volume1/web/portal
mkdir -p /volume1/web/staging
mkdir -p /volume1/web/test
```

### 3.5 SSH 무비번 로그인 설정 (배포 자동화용)

> 배포 스크립트가 비밀번호 없이 NAS에 접속할 수 있도록 설정합니다.

**로컬 PC(Windows)에서**:

```bash
# Git Bash에서 실행 — passphrase 없이 키 생성
ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519 -N '' -C 'deploy-key'
```

```bash
# 공개키를 NAS에 등록 (비밀번호 마지막 1회)
cat ~/.ssh/id_ed25519.pub | ssh admin@192.168.x.x "cat > ~/.ssh/authorized_keys"
```

**NAS에 SSH로 접속하여** (비밀번호 입력 후):

```bash
# sshd_config 수정 — StrictModes는 NAS 홈 폴더 권한 문제로 off 필요
sudo sed -i 's/#StrictModes yes/StrictModes no/' /etc/ssh/sshd_config
sudo sed -i 's/#PubkeyAuthentication yes/PubkeyAuthentication yes/' /etc/ssh/sshd_config
sudo /usr/syno/bin/synosystemctl restart sshd
```

확인:
```bash
ssh admin@192.168.x.x "echo SSH key OK"
# → SSH key OK (비밀번호 없이 출력되면 성공)
```

> ⚠️ DSM 업데이트 후 sshd_config가 초기화될 수 있습니다.  
> 그럴 경우 위 `sed` 명령어를 다시 실행하세요.

---

## 4장. Cloudflare Tunnel — 공유기 설정 없이 NAS를 외부에 연결하기

### 터널이 왜 필요한가?

집이나 사무실에 있는 NAS는 기본적으로 외부 인터넷에서 접근할 수 없습니다.  
일반적인 해결책은 공유기에서 **포트포워딩**이라는 설정을 해야 하는데,  
이 방법은 복잡한 데다 보안에도 취약합니다.

**Cloudflare Tunnel은 이 문제를 완전히 다른 방식으로 해결합니다.**

> 비유: 일반 포트포워딩은 "우리 집 주소와 현관 번호를 인터넷에 공개"하는 것과 같습니다.  
> 반면 Cloudflare Tunnel은 **NAS가 먼저 Cloudflare에 전화를 걸어 항상 연결 대기 상태를 유지**하는 방식입니다.  
> 외부에서 접속 요청이 오면, 이미 열려있는 이 통화 채널을 통해 안전하게 전달됩니다.  
> 우리 집 주소는 전혀 공개되지 않습니다.

**결과적으로**:
- 공유기 설정 불필요
- NAS IP 주소 외부 노출 없음
- Cloudflare의 보안 필터링 자동 적용
- 무료

---

### 터널 연결 흐름

```
방문자 브라우저
      │  "portal.example.co.kr 보여줘"
      ▼
Cloudflare 서버 (전 세계 중계 서버)
      │
      │  NAS가 미리 연결해 놓은 통로
      ▼
cloudflared 프로그램 (NAS 안에서 실행 중)
      │
      ▼
Synology NAS — 웹 파일 전달
```

---

### 4.1 터널 관리 메뉴(Zero Trust) 접속

> "Zero Trust"라는 이름이 생소하게 느껴질 수 있습니다.  
> 이것은 Cloudflare가 터널과 접근 제어 기능을 모아놓은 메뉴의 이름입니다.  
> 여기서는 터널을 만들고 관리하는 용도로만 사용합니다.

**메뉴 경로**:  
`Cloudflare 대시보드 로그인 → 왼쪽 사이드바 맨 아래 [Zero Trust] 클릭`  
또는 브라우저 주소창에 `one.dash.cloudflare.com` 직접 입력

- 처음 접속 시 팀 이름 입력 팝업 → 아무 이름이나 입력 → **[Next]**
- 요금제 선택 → **Free** → **[Proceed]**

### 4.2 터널 만들기

**메뉴 경로**:  
`왼쪽 메뉴 [Networks] → [Tunnels] → 오른쪽 상단 [Create a tunnel] 버튼`

1. 연결 방식 선택: **Cloudflared** 선택 → **[Next]**
2. 터널 이름 입력 (예: `my-nas-tunnel`, 아무 이름이나 가능) → **[Save Tunnel]**
3. 다음 화면에서 **NAS에 설치할 명령어**가 표시됩니다 → 다음 단계에서 사용

### 4.3 NAS에 연결 프로그램(cloudflared) 설치

> `cloudflared`는 NAS 안에서 항상 실행되면서 Cloudflare와 연결을 유지하는 작은 프로그램입니다.  
> 이 프로그램이 설치되어야 터널이 실제로 작동합니다.

**화면에서 선택**:

1. 운영체제 항목 → **Linux** 선택
2. 배포판 항목 → **Debian** 선택 (Synology NAS는 내부적으로 Debian Linux를 사용)
3. 아키텍처(CPU 종류) 항목 → 아래 기준으로 선택:
   - **amd64**: 인텔 또는 AMD CPU NAS (대부분의 최신 NAS)
   - **arm64**: ARM CPU NAS (구형 저가형 NAS)
   
   > NAS 모델명을 Synology 공식 사이트에서 검색하면 CPU 종류를 확인할 수 있습니다.

4. 화면에 표시된 명령어 블록 오른쪽 **복사 아이콘** 클릭

**PC에서 NAS에 SSH 접속 후**, 복사한 명령어를 붙여넣고 Enter:

```bash
# 화면에서 복사한 명령어를 그대로 붙여넣기 — 아래는 형식 예시
curl -L --output cloudflared.deb \
  https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared.deb
sudo cloudflared service install eyJhIjoiXXX...토큰값...
```

> 명령어 맨 뒤의 긴 문자열(토큰)이 이 터널의 고유 인증값입니다. 절대 다른 사람과 공유하지 마세요.

5. 설치 완료 후 Cloudflare 대시보드로 돌아오면 커넥터 상태가 **Connected** (초록 점)로 바뀝니다
6. **[Next]** 클릭

### 4.4 서브도메인과 NAS 연결하기

> 이 단계에서 "어떤 주소로 접속하면 NAS의 어느 폴더로 연결할지"를 지정합니다.  
> `portal.example.co.kr` → NAS 포트 8080 → `/volume1/web/portal` 폴더 순서로 연결됩니다.

**메뉴 경로**:  
`터널 설정 화면 → [Public Hostname] 탭 → [Add a public hostname] 버튼`

서브도메인마다 아래 항목을 입력하고 **[Save]**:

| 항목 | 설명 | 입력 예시 (portal) |
|------|------|-------------------|
| Subdomain | 서브도메인 이름 | `portal` |
| Domain | 보유한 도메인 | `example.co.kr` |
| Type | 연결 방식 | `HTTP` 선택 |
| URL | NAS 내부 주소:포트 | `localhost:8080` |

운영할 서브도메인 수만큼 반복:

| 용도 | Subdomain | URL |
|------|-----------|-----|
| 실 서비스 | `portal` | `localhost:8080` |
| 최종 점검용 | `staging` | `localhost:8082` |
| 개발 테스트용 | `test` | `localhost:8081` |

**[Save tunnel]** 클릭

### 4.5 연결 확인

브라우저 주소창에 `https://portal.example.co.kr` 입력 →  
NAS에 업로드해 둔 `index.html` 내용이 화면에 보이면 터널 연결 완료

---

## 5장. 서브도메인 DNS 설정

> Cloudflare Tunnel을 사용하면 DNS 레코드는 자동으로 생성됩니다.  
> 아래는 수동으로 확인하거나 추가하는 방법입니다.

**메뉴 경로**:  
`Cloudflare 대시보드 → 해당 도메인 선택 → 왼쪽 메뉴 [DNS] → [Records]`

Tunnel 설정 후 자동 생성된 CNAME 레코드 확인:

| 이름 | 유형 | 내용 |
|------|------|------|
| `portal` | CNAME | `tunnel-id.cfargotunnel.com` |
| `staging` | CNAME | `tunnel-id.cfargotunnel.com` |
| `test` | CNAME | `tunnel-id.cfargotunnel.com` |

> 프록시 상태(주황색 구름 아이콘): **프록시됨** 상태여야 합니다.

**수동으로 추가하는 경우**:

1. **[Add record]** 클릭
2. Type: **CNAME**
3. Name: `portal` (서브도메인명)
4. Target: Tunnel URL (`tunnel-id.cfargotunnel.com`)
5. Proxy status: **Proxied** (주황색)
6. **[Save]**

---

## 6장. Cloudflare Worker — 외부 API를 대신 불러오는 심부름꾼

### Worker가 왜 필요한가?

웹 서비스를 만들다 보면 외부 데이터를 가져와야 할 때가 있습니다.  
예를 들어 **DART(금융감독원 전자공시시스템)** 에서 기업 공시 정보를 조회하는 기능을 만든다고 할 때,  
브라우저에서 DART API에 직접 요청을 보내면 **거절**당합니다.

> **왜 거절당할까?**  
> 보안 정책 때문입니다. DART API를 운영하는 쪽에서 "우리 API는 허가된 서버에서만 호출할 수 있고,  
> 일반 웹 브라우저에서 직접 호출하는 것은 허용하지 않겠다"고 설정해 놓았기 때문입니다.  
> 이것을 **CORS 차단**이라고 하는데, 기술 용어는 몰라도 됩니다.  
> "브라우저에서 직접 부르면 막힌다"는 사실만 기억하면 됩니다.

**Cloudflare Worker가 이 문제를 해결합니다.**

> 비유: 식당에서 손님이 주방에 직접 들어가 음식을 가져오는 것은 금지되어 있습니다.  
> 하지만 웨이터(Worker)는 주방(DART API)에 들어가 음식을 받아서 손님(브라우저)에게 전달할 수 있습니다.  
> Worker는 브라우저 대신 DART에 요청하고, 받아온 데이터를 브라우저에 전달하는 **웨이터 역할**을 합니다.

**추가 이점**: DART API 키(인증 코드)를 Worker 안에 보관하므로,  
웹 페이지 코드에 API 키가 노출되지 않아 보안도 강화됩니다.

---

### Worker 연결 흐름 (DART 기업 조회 예시)

```
사용자가 기업명 검색
      │
      ▼
브라우저 → "DART에서 삼성전자 정보 가져와줘"
      │
      │  ← 브라우저가 DART에 직접 접근 불가
      ▼
Cloudflare Worker (웨이터)
      │  ← Worker가 DART API에 대신 요청
      ▼
DART API (금융감독원 서버)
      │  ← 결과 반환
      ▼
Cloudflare Worker
      │  ← 브라우저에 결과 전달
      ▼
브라우저 화면에 기업 정보 표시
```

---

### 6.1 Worker 만들기

**메뉴 경로**:  
`Cloudflare 대시보드 → 왼쪽 메뉴 [Workers & Pages] → [Create application] → [Create Worker]`

1. Worker 이름 입력 (예: `dart-proxy`)  
   이름은 나중에 Worker 주소가 됩니다: `dart-proxy.계정명.workers.dev`
2. 기본 코드가 편집창에 표시됩니다 → 아래 단계에서 실제 코드로 교체
3. **[Deploy]** 클릭 (일단 저장)

### 6.2 DART 전용 Worker 코드 입력

> 아래 코드는 브라우저 대신 DART API에 접속해서 데이터를 받아오는 전체 코드입니다.  
> 코드 내용을 이해하지 못해도 됩니다. 그대로 복사해서 붙여넣으면 됩니다.

**코드 편집 메뉴 경로**:  
`Workers & Pages → dart-proxy 클릭 → [Edit Code] 버튼`

기존 코드를 전부 지우고 아래 코드를 붙여넣은 후 **[Deploy]**:

```javascript
// DART API 대리 요청 Worker
// 브라우저 대신 DART API에 접속하고 결과를 브라우저에 전달합니다.

const DART_API_KEY = '여기에_DART_API_키_입력';  // ← DART 개발자센터에서 발급받은 키

addEventListener('fetch', event => {
  event.respondWith(handleRequest(event.request));
});

async function handleRequest(request) {
  // 브라우저의 사전 확인 요청 처리 (기술적 필수 절차)
  if (request.method === 'OPTIONS') {
    return new Response(null, { status: 204, headers: corsHeaders() });
  }

  const url    = new URL(request.url);
  const ep     = url.searchParams.get('ep');  // 어떤 DART 기능을 쓸지 지정
  const params = new URLSearchParams(url.search);
  params.delete('ep');
  params.set('crtfc_key', DART_API_KEY);      // API 키를 DART 요청에 추가

  // DART API에 대신 요청
  const dartUrl = `https://opendart.fss.or.kr/api/${ep}?${params}`;
  const resp    = await fetch(dartUrl, { headers: { 'User-Agent': 'Mozilla/5.0' } });

  // 결과를 브라우저에 전달
  return new Response(await resp.text(), {
    status: resp.status,
    headers: {
      'Content-Type': 'application/json;charset=utf-8',
      ...corsHeaders()
    }
  });
}

// 브라우저 직접 호출을 허용하는 설정
function corsHeaders() {
  return {
    'Access-Control-Allow-Origin':  '*',
    'Access-Control-Allow-Methods': 'GET, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
  };
}
```

> **DART API 키 발급 방법**:  
> [opendart.fss.or.kr](https://opendart.fss.or.kr) → 로그인 → [개발자센터] → [인증키 신청/관리] → 신청 후 발급된 키를 위 코드에 입력

### 6.3 Worker 주소를 내 도메인에 연결하기

> 이 단계를 하면 `dart-proxy.계정명.workers.dev` 대신  
> `https://api.example.co.kr` 같은 내 도메인 주소로 Worker를 사용할 수 있습니다.

**메뉴 경로**:  
`Workers & Pages → dart-proxy → [Settings] 탭 → [Triggers] → [Add Custom Domain]`

| 항목 | 입력 예시 |
|------|----------|
| Custom Domain | `api.example.co.kr` |

**[Add Custom Domain]** 클릭

또는 특정 경로에만 Worker를 연결하고 싶을 때 **[Add Route]**:

| 항목 | 입력 예시 |
|------|----------|
| Route | `portal.example.co.kr/dart/*` |
| Zone | `example.co.kr` |

**[Add route]** 클릭

### 6.4 웹 페이지에서 Worker 호출

> 이제 브라우저에서 DART 데이터를 조회할 때 DART API 주소 대신 Worker 주소를 사용합니다.

```javascript
// 기업명으로 DART 공시 조회 예시
const response = await fetch(
  'https://api.example.co.kr/?ep=company.json&corp_name=삼성전자'
);
const data = await response.json();
console.log(data);
```

---

## 7장. Supabase — 회원 로그인 시스템 구축

### 왜 Supabase인가? — SNS 계정 연동 로그인을 가장 쉽게 구현하는 방법

우리가 만들려는 웹사이트는 "카카오 계정으로 로그인" 또는 "Google 계정으로 로그인" 버튼을 제공합니다.  
이 방식을 **소셜 로그인(SNS 로그인)** 이라고 부릅니다.

사용자 입장에서는 새 비밀번호를 만들 필요 없이 평소에 쓰던 카카오나 Google 계정으로 바로 가입·로그인할 수 있어 편리합니다.  
서비스 운영자 입장에서도 비밀번호를 직접 관리하지 않아도 되므로 보안 부담이 줄어듭니다.

그런데 이 소셜 로그인을 **직접 구현**하려면 이야기가 달라집니다.  
Google, 카카오 각각이 요구하는 **OAuth 2.0 프로토콜**을 구현해야 하는데,  
이것은 보안 토큰 발급·갱신·세션 관리까지 포함한 상당히 복잡한 작업입니다.  
전문 개발자도 실수하기 쉬운 영역이고, 한 번 잘못 구현하면 사용자 계정이 탈취될 수 있습니다.

**Supabase는 이 복잡한 OAuth 구현을 대신 처리해주는 서비스입니다.**  
각 SNS 플랫폼에서 발급받은 앱 키를 Supabase에 등록하면,  
이후 코드 몇 줄만으로 소셜 로그인 버튼을 만들 수 있습니다.

---

### 검토했던 SNS 플랫폼들 — 그리고 최종 선택

처음에는 더 많은 SNS를 지원하는 방향을 검토했습니다.

| 검토한 플랫폼 | 국내·해외 커버리지 | Supabase 기본 지원 | 최종 결정 |
|------------|----------------|------------------|---------|
| **카카오** | 국내 (스마트폰 사용자의 97%+) | ✅ 기본 지원 | ✅ **채택** |
| **Google** | 해외 + 국내 (기업·대학 이메일) | ✅ 기본 지원 | ✅ **채택** |
| 네이버 | 국내 한정 | ❌ 기본 지원 없음 | ✗ 포기 |
| 페이스북 | 해외 (Meta 계열) | ⚠️ 지원하지만 Meta 앱 심사 필요 | ✗ 포기 |
| 인스타그램 | 해외 (Meta 계열) | ❌ Instagram 직접 지원 없음 (페이스북 경유) | ✗ 포기 |

#### 네이버를 포기한 이유

네이버 로그인은 Supabase가 **기본 제공하는 OAuth Provider 목록에 없습니다.**  
지원하려면 Supabase의 Custom OAuth 기능을 사용하거나, 별도 서버에서 직접 네이버 OAuth를 구현해야 합니다.  
구현 난이도가 올라가는 반면, 국내 커버리지에서는 카카오(97% 이상)가 이미 네이버를 대체할 수 있습니다.  
두 가지를 동시에 지원해도 사용자 경험이 복잡해질 뿐이라 카카오 하나로 국내를 커버하기로 했습니다.

#### 페이스북·인스타그램을 포기한 이유

페이스북 OAuth는 Supabase가 지원하지만, Meta 개발자 플랫폼에서  
**비즈니스 인증과 앱 심사**를 별도로 받아야 합니다. (심사 기간 최대 수 주)  
인스타그램은 독립적인 OAuth를 제공하지 않고 Facebook Login을 경유하는 구조여서  
결국 Facebook과 동일한 심사 절차가 필요합니다.  
심사를 통과해도 제공하는 추가 커버리지가 Google로 이미 충당되는 해외 사용자층과 크게 겹쳐  
투자 대비 효과가 낮다고 판단했습니다.

#### 결론 — 카카오 + Google 두 가지로 충분한 이유

> **카카오** → 국내 사용자 사실상 전원 커버  
> **Google** → 해외 사용자 + 기업·대학 이메일 계정 보유자 커버  
> 이 두 가지를 Supabase가 **무료로, 설정만으로** 제공합니다.

---

### Supabase Free 플랜이 제공하는 것

| 기능 | 설명 |
|------|------|
| 소셜 로그인 | Google, 카카오 등 OAuth Provider를 대시보드에서 설정만으로 연동 |
| 이메일 로그인 | 이메일 인증 링크 발송, 비밀번호 설정 |
| 사용자 관리 | 회원 목록, 가입일, 마지막 로그인 등 자동 기록 |
| 데이터베이스 | 회원별 데이터를 안전하게 저장하는 PostgreSQL DB (8장에서 다룸) |
| 보안 | 토큰 기반 인증, 자동 만료, 세션 관리 |

> **무료 한도**: 월 활성 사용자 **50,000명**까지 무료.  
> 소규모 서비스를 시작할 때는 비용 없이 운영할 수 있습니다.

---

### 7.1 Supabase 프로젝트 생성

1. [supabase.com](https://supabase.com) → 우측 상단 **[Start your project]**
2. GitHub 계정으로 로그인 (권장)
3. 대시보드 → **[New project]** 버튼
4. 입력:

| 항목 | 입력 |
|------|------|
| 조직(Organization) | 기본값 또는 새 조직 생성 |
| Project name | `myproject` |
| Database password | 강력한 비밀번호 입력 (저장 필수) |
| Region | **Northeast Asia (Tokyo)** 권장 |

5. **[Create new project]** → 2~3분 대기 (프로비저닝)

### 7.2 API 키 확인

**메뉴 경로**:  
`프로젝트 대시보드 → 왼쪽 메뉴 [Project Settings] → [API]`

| 항목 | 설명 |
|------|------|
| Project URL | `https://xxxxxxxxxxxx.supabase.co` |
| anon public | 프런트엔드 코드에 사용하는 공개 키 |
| service_role | 서버 전용 (절대 프런트엔드 노출 금지) |

**Project URL**과 **anon public** 키를 복사해둡니다.

### 7.3 Google OAuth 설정

#### ① Google Cloud Console에서 OAuth 자격증명 발급

1. [console.cloud.google.com](https://console.cloud.google.com)
2. 상단 프로젝트 선택 → **[새 프로젝트]** 또는 기존 프로젝트 선택
3. 왼쪽 메뉴 **[APIs & Services]** → **[Credentials]**
4. **[+ CREATE CREDENTIALS]** → **OAuth client ID**
5. 처음 생성 시 **Configure Consent Screen** 안내 팝업:
   - User Type: **External** → **[Create]**
   - 앱 이름, 사용자 지원 이메일, 개발자 연락처 이메일 입력 → **[Save and Continue]**
   - Scopes: **[Save and Continue]** (기본값)
   - Test users: **[Save and Continue]**
   - **[Back to Dashboard]**
6. 다시 **Credentials → [+ CREATE CREDENTIALS] → OAuth client ID**
7. Application type: **Web application**
8. 이름: `Supabase Auth` (임의)
9. **Authorized redirect URIs** → **[+ ADD URI]**:
   ```
   https://[프로젝트ID].supabase.co/auth/v1/callback
   ```
10. **[CREATE]** → 팝업에서 **Client ID**, **Client Secret** 복사

#### ② Supabase에 Google 정보 입력

**메뉴 경로**:  
`Supabase 프로젝트 → 왼쪽 메뉴 [Authentication] → [Providers] → [Google]`

1. **Enable Sign in with Google** 토글 **ON**
2. Client ID 붙여넣기
3. Client Secret 붙여넣기
4. **[Save]**

### 7.4 Kakao OAuth 설정

#### ① 카카오 개발자 콘솔에서 앱 생성

1. [developers.kakao.com](https://developers.kakao.com) → 로그인
2. 상단 **[내 애플리케이션]** → **[애플리케이션 추가하기]**
3. 앱 이름, 회사명, 카테고리 입력 → **[저장]**
4. 생성된 앱 클릭 → **앱 키** 섹션에서 **REST API 키** 복사

#### ② 카카오 로그인 활성화 및 Redirect URI 등록

**메뉴 경로**:  
`앱 → 왼쪽 메뉴 [제품 설정] → [카카오 로그인]`

1. 활성화 설정: **ON**
2. **[Redirect URI]** → **[Redirect URI 등록]**:
   ```
   https://[프로젝트ID].supabase.co/auth/v1/callback
   ```
3. **[저장]**

**메뉴 경로**:  
`[플랫폼] → [Web 플랫폼 등록]`

- 사이트 도메인: `https://portal.example.co.kr` → **[저장]**

#### ③ Supabase에 Kakao 정보 입력

**메뉴 경로**:  
`Supabase 프로젝트 → [Authentication] → [Providers] → [Kakao]`

1. **Enable Sign in with Kakao** 토글 **ON**
2. Kakao App Key: REST API 키 붙여넣기
3. **[Save]**

### 7.5 Redirect URL 허용 목록 설정

> 로그인 후 리디렉션할 URL을 명시적으로 허용해야 합니다.

**메뉴 경로**:  
`[Authentication] → [URL Configuration]`

| 항목 | 입력값 |
|------|--------|
| Site URL | `https://portal.example.co.kr` |

**Redirect URLs** (Additional redirect URLs):

```
https://portal.example.co.kr/**
https://staging.example.co.kr/**
https://test.example.co.kr/**
http://127.0.0.1:5500/**
```

**[Save]** 클릭

> `http://127.0.0.1:5500/**` 는 로컬 개발 환경(VS Code Live Server)에서 테스트할 때 필요합니다.

---

## 8장. Supabase 데이터베이스 — 회원 정보·결제·크레딧 저장

> **이 장에서 하는 이유**  
> 로그인(7장)으로 "이 사람이 누구인지"는 알았습니다.  
> 이제 그 사람의 **데이터를 저장**해야 합니다.  
> Supabase는 인증 기능 외에 **PostgreSQL 데이터베이스**도 함께 제공합니다.

### 8.1 DB 설계 원칙

실제로 운영하다 보면 DB 스크립트를 **여러 번 실행**해야 하는 상황이 생깁니다.  
(설정 변경, 컬럼 추가, 정책 수정 등) 이때 **멱등성(Idempotency)** 을 보장해야 합니다.

> **멱등성**: 같은 스크립트를 몇 번 실행해도 항상 동일한 결과가 나오는 성질.  
> `CREATE TABLE IF NOT EXISTS`, `ALTER TABLE ADD COLUMN IF NOT EXISTS`,  
> `CREATE OR REPLACE FUNCTION`, `DROP POLICY IF EXISTS` 패턴으로 구현합니다.

**권장 파일 구조**:

```
supabase/
├── phase1_check_before_run.sql   # 실행 전 현재 상태 진단
└── phase1_db_setup.sql           # 실제 설정 스크립트 (멱등성 보장)
```

### 8.2 실행 전 현재 상태 진단

스크립트를 실행하기 전에 **현재 DB 상태**를 먼저 파악합니다.  
Supabase SQL Editor는 마지막 SELECT만 표시하므로 UNION ALL로 하나의 결과로 통합합니다.

```sql
-- phase1_check_before_run.sql
SELECT category, item, detail FROM (
  SELECT '1_tables'  AS category, table_name AS item, table_type AS detail
  FROM information_schema.tables
  WHERE table_schema = 'public'
    AND table_name IN ('profiles','credits','payments','credit_balance')
  UNION ALL
  SELECT '2_profiles_cols', column_name,
    data_type || ' | default=' || COALESCE(column_default,'NULL') || ' | nullable=' || is_nullable
  FROM information_schema.columns
  WHERE table_schema = 'public' AND table_name = 'profiles'
  UNION ALL
  SELECT '3_policies', tablename || '.' || policyname, cmd
  FROM pg_policies WHERE tablename IN ('profiles','credits','payments')
  UNION ALL
  SELECT '4_triggers', trigger_name, event_object_table
  FROM information_schema.triggers WHERE trigger_name = 'on_auth_user_created'
  UNION ALL
  SELECT '5_functions', routine_name, routine_type
  FROM information_schema.routines
  WHERE routine_schema = 'public'
    AND routine_name IN ('handle_new_user','get_user_credit_balance','deduct_credits','admin_grant_credits')
) q ORDER BY category, item;
```

**확인 포인트**: 이미 존재하는 테이블/컬럼/정책이 무엇인지 파악한 후 스크립트를 조정합니다.

> **WorksFree Hub 사례**: 기존 `profiles` 테이블에 `role_set_at` 컬럼이 이미 있었음.  
> 미지의 컬럼은 건드리지 않고, 우리가 필요한 컬럼만 `ADD COLUMN IF NOT EXISTS`로 추가.  
> 기존 RLS 정책 이름이 달라 (`본인만 조회`, `본인만 수정` 등) 동적 루프로 전부 삭제 후 통일.

### 8.3 크레딧 설계 — 잔액 vs 원장

크레딧을 저장하는 방법에는 두 가지가 있습니다:

| 방식 | 설명 | 장점 | 단점 |
|------|------|------|------|
| **잔액 방식** | `balance` 컬럼에 현재 잔액을 덮어씀 | 조회 간단 | 이력 없음, 조작 가능 |
| **원장(Ledger) 방식** | 모든 변동을 `delta` 행으로 기록, 잔액은 SUM | 완전한 이력, 감사 가능 | 조회 시 집계 필요 |

**권장: 원장 방식** (`delta` 기반). 충전·사용·환불의 모든 내역이 남아 분쟁 대응이 가능합니다.

```
credits 테이블 예시:
user_id  | delta | reason        | note
---------|-------|---------------|------------------
user-001 | +500  | purchase      | 토스 결제 #order-123
user-001 | -50   | use_app       | QR 생성기 사용
user-001 | +100  | admin_grant   | 이벤트 지급
-----    잔액 = SUM(delta) = 550  -----
```

### 8.4 테이블·뷰·함수 생성 (멱등 스크립트)

**메뉴 경로**:  
`Supabase → SQL Editor → New query → 아래 내용 붙여넣기 → [Run]`

```sql
-- ─────────────────────────────────────────────────────────
-- 0. profiles 보완 (기존 테이블에 필요 컬럼 추가)
-- ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS profiles (
  id               uuid REFERENCES auth.users PRIMARY KEY,
  agreed_at        timestamptz,
  marketing_agreed boolean     DEFAULT false,
  role             text        DEFAULT 'general',
  created_at       timestamptz DEFAULT now()
);
ALTER TABLE profiles
  ADD COLUMN IF NOT EXISTS role             text        DEFAULT 'general',
  ADD COLUMN IF NOT EXISTS marketing_agreed boolean     DEFAULT false,
  ADD COLUMN IF NOT EXISTS agreed_at        timestamptz,
  ADD COLUMN IF NOT EXISTS created_at       timestamptz DEFAULT now();

ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;

-- 기존 정책명이 무엇이든 전부 정리 후 하나로 통일
DO $$ DECLARE r record;
BEGIN
  FOR r IN SELECT policyname FROM pg_policies WHERE tablename = 'profiles' LOOP
    EXECUTE format('DROP POLICY IF EXISTS %I ON profiles', r.policyname);
  END LOOP;
END $$;
CREATE POLICY "profiles_self"
  ON profiles FOR ALL
  USING (auth.uid() = id) WITH CHECK (auth.uid() = id);

-- 신규 가입 시 profiles 행 자동 생성 트리거
CREATE OR REPLACE FUNCTION handle_new_user()
RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
BEGIN
  INSERT INTO public.profiles (id) VALUES (NEW.id) ON CONFLICT (id) DO NOTHING;
  RETURN NEW;
END; $$;
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users FOR EACH ROW EXECUTE FUNCTION handle_new_user();

-- 기존 가입자 소급 처리
INSERT INTO public.profiles (id) SELECT id FROM auth.users ON CONFLICT (id) DO NOTHING;

-- ─────────────────────────────────────────────────────────
-- 1. credits 테이블 (원장 방식)
-- ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS credits (
  id           bigint       GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  user_id      uuid         NOT NULL REFERENCES auth.users ON DELETE CASCADE,
  delta        integer      NOT NULL,
  reason       text         NOT NULL
               CHECK (reason IN ('purchase', 'use_app', 'admin_grant', 'refund')),
  app_id       text,
  ref_order_id text,
  note         text,
  created_at   timestamptz  NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS credits_user_created ON credits (user_id, created_at DESC);
ALTER TABLE credits ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "credits_select_own"      ON credits;
DROP POLICY IF EXISTS "credits_insert_purchase" ON credits;
CREATE POLICY "credits_select_own"
  ON credits FOR SELECT USING (auth.uid() = user_id);
-- 프런트에서 충전(purchase, delta>0)만 직접 INSERT 허용
-- 차감(use_app)은 서버 함수(service_role)에서만
CREATE POLICY "credits_insert_purchase"
  ON credits FOR INSERT
  WITH CHECK (auth.uid() = user_id AND delta > 0 AND reason = 'purchase');

-- ─────────────────────────────────────────────────────────
-- 2. payments 테이블
-- ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS payments (
  id           bigint        GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  user_id      uuid          NOT NULL REFERENCES auth.users ON DELETE CASCADE,
  order_id     text          NOT NULL UNIQUE,
  pg           text          NOT NULL CHECK (pg IN ('toss', 'stripe')),
  amount_krw   integer       NOT NULL DEFAULT 0,
  amount_usd   numeric(10,2) NOT NULL DEFAULT 0,
  credits      integer       NOT NULL,
  status       text          NOT NULL DEFAULT 'paid'
               CHECK (status IN ('paid', 'cancelled', 'refunded')),
  created_at   timestamptz   NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS payments_user_created ON payments (user_id, created_at DESC);
ALTER TABLE payments ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "payments_select_own" ON payments;
DROP POLICY IF EXISTS "payments_insert_own" ON payments;
CREATE POLICY "payments_select_own" ON payments FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "payments_insert_own" ON payments FOR INSERT WITH CHECK (auth.uid() = user_id);

-- ─────────────────────────────────────────────────────────
-- 3. credit_balance 뷰 (잔액 실시간 집계)
-- ─────────────────────────────────────────────────────────
CREATE OR REPLACE VIEW credit_balance
  WITH (security_invoker = true) AS   -- ← RLS가 뷰를 통해서도 적용됨
SELECT
  user_id,
  COALESCE(SUM(delta), 0)::int                           AS balance,
  COALESCE(SUM(delta)  FILTER (WHERE delta > 0), 0)::int AS total_charged,
  COALESCE(SUM(-delta) FILTER (WHERE delta < 0), 0)::int AS total_used
FROM credits GROUP BY user_id;

-- ─────────────────────────────────────────────────────────
-- 4. 서버 측 헬퍼 함수 (SECURITY DEFINER — RLS 우회)
-- ─────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION get_user_credit_balance(p_user_id uuid)
RETURNS integer LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public AS $$
  SELECT COALESCE(SUM(delta), 0)::int FROM credits WHERE user_id = p_user_id;
$$;

-- 크레딧 차감 (잔액 부족 시 예외 발생)
CREATE OR REPLACE FUNCTION deduct_credits(
  p_user_id uuid, p_amount integer, p_app_id text, p_note text DEFAULT NULL
) RETURNS integer LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE v_balance integer;
BEGIN
  SELECT get_user_credit_balance(p_user_id) INTO v_balance;
  IF v_balance < p_amount THEN
    RAISE EXCEPTION 'insufficient_credits: balance=%, required=%', v_balance, p_amount;
  END IF;
  INSERT INTO credits (user_id, delta, reason, app_id, note)
  VALUES (p_user_id, -p_amount, 'use_app', p_app_id, p_note);
  RETURN v_balance - p_amount;
END; $$;

-- 관리자 크레딧 지급
CREATE OR REPLACE FUNCTION admin_grant_credits(
  p_user_id uuid, p_amount integer, p_note text DEFAULT '관리자 지급'
) RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
BEGIN
  INSERT INTO credits (user_id, delta, reason, note)
  VALUES (p_user_id, p_amount, 'admin_grant', p_note);
END; $$;
```

### 8.5 사용자 역할(role) 지정

서비스에 따라 사용자 등급이 다릅니다. `profiles.role` 컬럼으로 관리합니다.

> **WorksFree Hub 역할 체계**:
>
> | role 값 | 의미 | 접근 범위 |
> |---------|------|-----------|
> | `general` | 기본 회원 (RPA 앱 사용자) | 공개 + 회원 전용 도구 |
> | `consultant` | 경영지도사 | general + 컨설팅 메뉴 |
> | `gfc` | GFC 파트너 | consultant + 보험 관련 전용 메뉴 |
> | `ceo`, `staff` | 향후 확장용 | — |

**관리자 계정 role 지정** (Supabase SQL Editor):

```sql
-- 1. 대상 계정의 UUID 확인
--    Supabase → Authentication → Users 탭에서 이메일로 검색
-- 2. role 업데이트
UPDATE profiles SET role = 'gfc' WHERE id = '<GFC_파트너_UUID>';

-- 초기 크레딧 지급도 함께
SELECT admin_grant_credits('<UUID>', 9999, '파트너 계정 초기 지급');
```

### 8.6 프런트엔드에서 잔액 조회

```javascript
// credit_balance 뷰에서 잔액 조회 (RLS가 자동으로 본인 데이터만 반환)
async function loadCreditBalance() {
  const { data } = await _sb
    .from('credit_balance')
    .select('balance')
    .eq('user_id', authUser.id)
    .maybeSingle();
  return data?.balance ?? 0;
}
```

---

## 9장. 온라인 결제 연동 — 국내(토스페이먼츠) + 해외(Stripe)

> **이 장에서 하는 이유**  
> 크레딧을 충전하거나 서비스를 구매할 때 실제 돈을 받아야 합니다.  
> 카드 결제·계좌이체 처리는 금융 보안 규정이 엄격해서 직접 구현하면 불법이 될 수 있습니다.  
> **결제대행사(PG사)**에 등록하면 이 모든 것을 합법적으로 처리할 수 있습니다.  
>  
> 국내는 **토스페이먼츠** (카드·계좌이체·카카오페이·네이버페이 등 포함),  
> 해외는 **Stripe** (신용카드·Apple Pay·Google Pay 등 포함)를 사용합니다.

### 결제 흐름 이해하기

```
사용자: [크레딧 충전 버튼 클릭]
      │
      ▼
웹사이트 프런트엔드
      │ PG사 결제창 호출
      ▼
토스페이먼츠 / Stripe 결제창 팝업
      │ 사용자가 카드 정보 입력 후 결제
      ▼
PG사가 결제 처리 (성공 / 실패)
      │ 결제 결과를 웹사이트에 통보 (Webhook)
      ▼
웹사이트 서버 (또는 Cloudflare Worker)
      │ 결제 결과 검증 후 DB에 기록
      ▼
Supabase DB: payments 테이블에 이력 저장
             credits 테이블에 크레딧 추가
```

### 배포 전 사전 준비 — 토스페이먼츠·Stripe에서 받아야 하는 것

결제 기능은 PG사(결제대행사) 계정이 있어야 합니다.  
코드 개발과 동시에 계정 신청을 시작하면 됩니다.  
**테스트 모드는 계정만 만들면 즉시 사용 가능**합니다. 사업자 심사는 실서비스 전환 시에만 필요합니다.

---

#### 토스페이먼츠에서 받아야 하는 것

| 단계 | 받는 것 | 시점 |
|------|---------|------|
| 회원가입 직후 | 테스트 클라이언트 키 (`test_ck_...`) | 즉시 |
| 회원가입 직후 | 테스트 시크릿 키 (`test_sk_...`) | 즉시 |
| 사업자 인증 완료 후 | 실서비스 클라이언트 키 (`live_ck_...`) | 심사 후 1~3 영업일 |
| 사업자 인증 완료 후 | 실서비스 시크릿 키 (`live_sk_...`) | 심사 후 1~3 영업일 |

**가입 절차:**

1. [www.tosspayments.com](https://www.tosspayments.com) → **[시작하기]**
2. 이메일·비밀번호로 가입 → 대시보드 진입
3. `대시보드 → [개발] → [API 키]` → **테스트 키** 복사 (즉시 사용 가능)
4. 실서비스 전환 시: `대시보드 → [사업자 인증]` → 사업자등록증 제출 → 심사 대기

> **사업자가 없는 경우**: 개인 자격으로는 실서비스(실제 돈 수납) 전환이 불가능합니다.  
> 개인사업자 또는 법인 등록 후 신청해야 합니다.  
> 개발·테스트는 사업자 없이도 무제한 가능합니다.

---

#### Stripe에서 받아야 하는 것

| 단계 | 받는 것 | 시점 |
|------|---------|------|
| 회원가입 직후 | 테스트 퍼블리셔블 키 (`pk_test_...`) | 즉시 |
| 회원가입 직후 | 테스트 시크릿 키 (`sk_test_...`) | 즉시 |
| 계정 인증 완료 후 | 실서비스 퍼블리셔블 키 (`pk_live_...`) | 즉시 (자동 심사) |
| 계정 인증 완료 후 | 실서비스 시크릿 키 (`sk_live_...`) | 즉시 (자동 심사) |

**가입 절차:**

1. [stripe.com](https://stripe.com) → **[Start now]**
2. 이메일·비밀번호 가입 → 대시보드 진입
3. `대시보드 → [Developers] → [API keys]` → **Test keys** 탭에서 복사
4. 실서비스 전환: 대시보드 안내에 따라 사업자 정보 입력 (자동 심사, 보통 즉시)

> Stripe는 개인(프리랜서 포함)도 실서비스 계정 전환이 가능합니다.  
> 한국 원화(KRW) 정산도 지원하지만, 해외 결제(USD 등)와 정산 통화를 별도 확인하세요.

---

### 9.1 토스페이먼츠 가입 및 설정 (국내 결제)

#### ① API 키 확인

**메뉴 경로**:  
`토스페이먼츠 대시보드 → 왼쪽 메뉴 [개발] → [API 키]`

| 키 이름 | 용도 |
|--------|------|
| 클라이언트 키 | 결제창 호출 (웹페이지에 삽입) |
| 시크릿 키 | 결제 검증 (서버/Worker에서만 사용, 절대 노출 금지) |

> 테스트용 키와 실서비스용 키가 별도로 존재합니다. 개발 중에는 반드시 **테스트 키** 사용.

#### ③ 프런트엔드 결제창 호출 코드

```html
<!-- index.html: 토스페이먼츠 SDK 로드 -->
<script src="https://js.tosspayments.com/v1/payment"></script>
```

```javascript
const TOSS_CLIENT_KEY = 'test_ck_여기에_클라이언트키_입력';

async function openTossPayment(amount, credits) {
  const toss = TossPayments(TOSS_CLIENT_KEY);
  const orderId = 'order_' + Date.now();  // 고유 주문 번호

  try {
    await toss.requestPayment('카드', {
      amount: amount,                          // 결제 금액 (원)
      orderId: orderId,
      orderName: `크레딧 ${credits}개 충전`,
      successUrl: 'https://portal.example.co.kr/payment/success',
      failUrl:    'https://portal.example.co.kr/payment/fail',
    });
  } catch (error) {
    console.error('결제 오류:', error);
  }
}
```

#### ④ 결제 완료 후 검증 (Cloudflare Worker)

> 결제가 완료되면 토스페이먼츠가 `successUrl`로 주문 정보를 전달합니다.  
> 이 정보를 토스 서버에 한 번 더 확인(검증)해야 위변조를 방지할 수 있습니다.  
> 이 검증 작업은 시크릿 키가 필요하므로 반드시 Worker(서버)에서 처리해야 합니다.

```javascript
// Cloudflare Worker: payment-verify
const TOSS_SECRET_KEY = '시크릿키를_여기에_입력';  // 절대 프런트엔드에 노출 금지

addEventListener('fetch', event => {
  event.respondWith(handlePayment(event.request));
});

async function handlePayment(request) {
  const { paymentKey, orderId, amount } = await request.json();

  // 토스 서버에 결제 확인 요청
  const response = await fetch('https://api.tosspayments.com/v1/payments/confirm', {
    method: 'POST',
    headers: {
      'Authorization': 'Basic ' + btoa(TOSS_SECRET_KEY + ':'),
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ paymentKey, orderId, amount })
  });

  const result = await response.json();

  if (result.status === 'DONE') {
    // 결제 성공 → DB에 기록 (Supabase service role key 필요)
    return new Response(JSON.stringify({ success: true }), { status: 200 });
  } else {
    return new Response(JSON.stringify({ success: false }), { status: 400 });
  }
}
```

---

### 9.2 Stripe 가입 및 설정 (해외 결제)

#### ① 가입

1. [stripe.com](https://stripe.com) → **[Start now]**
2. 이메일 · 비밀번호 입력 후 가입
3. 대시보드 진입 → 사업자 정보 입력 (선택, 나중에 해도 됨)
4. 테스트 모드에서는 즉시 사용 가능

#### ② API 키 확인

**메뉴 경로**:  
`Stripe 대시보드 → 왼쪽 메뉴 [Developers] → [API keys]`

| 키 이름 | 용도 |
|--------|------|
| Publishable key | 결제창 호출 (웹페이지에 삽입) |
| Secret key | 결제 검증 (Worker에서만 사용) |

> 대시보드 오른쪽 상단 **[Test mode]** 토글이 켜져 있는지 확인 후 테스트 키 사용.

#### ③ 프런트엔드 결제창 호출

```html
<!-- Stripe.js 로드 -->
<script src="https://js.stripe.com/v3/"></script>
```

```javascript
const STRIPE_KEY = 'pk_test_여기에_퍼블리셔블키_입력';
const stripe = Stripe(STRIPE_KEY);

async function openStripePayment(amountUSD, credits) {
  // 1. 서버(Worker)에서 결제 세션 생성
  const res = await fetch('https://api.example.co.kr/stripe/create-session', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ amount: amountUSD, credits })
  });
  const { sessionId } = await res.json();

  // 2. Stripe 결제 페이지로 이동
  const { error } = await stripe.redirectToCheckout({ sessionId });
  if (error) console.error(error);
}
```

#### ④ Worker에서 Stripe 세션 생성

```javascript
// Cloudflare Worker: stripe-session
const STRIPE_SECRET = 'sk_test_시크릿키_입력';

async function createStripeSession(request) {
  const { amount, credits } = await request.json();

  const body = new URLSearchParams({
    'payment_method_types[]': 'card',
    'line_items[0][price_data][currency]': 'usd',
    'line_items[0][price_data][unit_amount]': amount,  // 센트 단위 (100 = $1)
    'line_items[0][price_data][product_data][name]': `크레딧 ${credits}개`,
    'line_items[0][quantity]': '1',
    'mode': 'payment',
    'success_url': 'https://portal.example.co.kr/payment/success?session_id={CHECKOUT_SESSION_ID}',
    'cancel_url':  'https://portal.example.co.kr/payment/cancel',
  });

  const response = await fetch('https://api.stripe.com/v1/checkout/sessions', {
    method: 'POST',
    headers: {
      'Authorization': 'Basic ' + btoa(STRIPE_SECRET + ':'),
      'Content-Type': 'application/x-www-form-urlencoded'
    },
    body: body.toString()
  });

  const session = await response.json();
  return new Response(JSON.stringify({ sessionId: session.id }), {
    headers: { 'Content-Type': 'application/json' }
  });
}
```

### 9.3 결제 후 크레딧 자동 충전

> 결제가 성공하면 Supabase DB에 결제 이력을 기록하고 크레딧을 추가해야 합니다.  
> 이 작업은 Worker에서 Supabase API를 호출하여 처리합니다.

```javascript
// Worker에서 결제 확인 후 DB 업데이트
async function updateCreditsAfterPayment(userId, amount, credits, orderId, provider) {
  const SUPABASE_URL      = 'https://xxxx.supabase.co';
  const SUPABASE_SERVICE  = 'service_role_키_입력';  // 서버 전용 키

  const headers = {
    'apikey': SUPABASE_SERVICE,
    'Authorization': `Bearer ${SUPABASE_SERVICE}`,
    'Content-Type': 'application/json'
  };

  // ① payments 테이블에 결제 이력 기록
  await fetch(`${SUPABASE_URL}/rest/v1/payments`, {
    method: 'POST',
    headers,
    body: JSON.stringify({
      user_id: userId, amount, credits,
      status: 'paid', pg_provider: provider,
      pg_order_id: orderId, paid_at: new Date().toISOString()
    })
  });

  // ② credits 테이블에 잔액 추가
  // (현재 잔액을 먼저 조회한 후 합산)
  const balRes = await fetch(
    `${SUPABASE_URL}/rest/v1/credits?user_id=eq.${userId}&order=created_at.desc&limit=1`,
    { headers }
  );
  const [lastRow] = await balRes.json();
  const newBalance = (lastRow?.balance ?? 0) + credits;

  await fetch(`${SUPABASE_URL}/rest/v1/credits`, {
    method: 'POST',
    headers,
    body: JSON.stringify({
      user_id: userId, delta: credits,
      reason: 'purchase', balance: newBalance
    })
  });
}
```

---

### 9.4 개발 중 반복 테스트 — 가결제로 기능 검증하기

PG사 테스트 모드에서는 **실제 돈이 전혀 오가지 않습니다.**  
아래 테스트 카드 번호를 입력하면 결제 성공·실패를 원하는 만큼 시뮬레이션할 수 있습니다.

---

#### 토스페이먼츠 테스트 카드

`test_ck_...` 키를 사용하는 상태에서 아래 정보를 입력합니다.

| 항목 | 입력값 |
|------|--------|
| 카드 번호 | `4242 4242 4242 4242` |
| 유효기간 | 아무 미래 날짜 (예: `12/26`) |
| CVC | 아무 3자리 (예: `123`) |
| 카드 비밀번호 | 아무 2자리 (예: `00`) |
| 생년월일 | 아무 6자리 (예: `900101`) |

**의도적 실패 테스트** (실패 케이스도 반드시 확인해야 합니다):

| 카드 번호 | 결과 |
|----------|------|
| `4000 0000 0000 0002` | 카드 거절 |
| `4100 0000 0000 0019` | 한도 초과 |

> 토스 테스트 카드 전체 목록: [docs.tosspayments.com → 테스트 카드 번호](https://docs.tosspayments.com/reference/testing)

---

#### Stripe 테스트 카드

`pk_test_...` / `sk_test_...` 키를 사용하는 상태에서 입력합니다.

| 항목 | 입력값 |
|------|--------|
| 카드 번호 | `4242 4242 4242 4242` |
| 유효기간 | 아무 미래 날짜 (예: `12/28`) |
| CVC | `424` |
| 우편번호 | `12345` (아무 숫자) |

**의도적 실패 테스트:**

| 카드 번호 | 결과 |
|----------|------|
| `4000 0000 0000 0002` | 카드 거절 |
| `4000 0000 0000 9995` | 잔액 부족 |
| `4000 0025 0000 3155` | 3D Secure 인증 필요 (추가 인증 화면 테스트 가능) |

> Stripe 테스트 카드 전체 목록: [stripe.com/docs/testing](https://stripe.com/docs/testing)

---

#### 테스트 시 확인해야 할 체크리스트

결제 기능을 충분히 검증하려면 아래 시나리오를 모두 통과해야 합니다.

**정상 흐름 (Happy Path):**

- [ ] 크레딧 구매 모달이 열린다
- [ ] 패키지를 선택하면 결제 버튼이 활성화된다
- [ ] Toss 결제창이 정상적으로 열린다
- [ ] 테스트 카드 입력 후 결제 성공
- [ ] 페이지가 서비스로 돌아온다 (리다이렉트)
- [ ] Worker가 결제 검증을 완료한다 (Worker 로그 확인)
- [ ] Supabase `payments` 테이블에 결제 기록이 삽입됐다
- [ ] Supabase `credits` 테이블에 크레딧 delta가 삽입됐다
- [ ] 화면에 "크레딧이 충전됐습니다" 토스트 메시지가 나타난다
- [ ] Stripe 흐름도 동일하게 통과한다

**오류 흐름 (Error Path):**

- [ ] 결제창에서 [취소] 클릭 → "결제가 취소됐습니다" 메시지 표시
- [ ] 거절 카드 번호 입력 → 오류 메시지 표시, 크레딧 충전되지 않음
- [ ] Worker URL이 잘못된 경우 → 오류 메시지 표시 (DB에 미기록 확인)
- [ ] 비로그인 상태에서 구매 버튼 클릭 → 로그인 모달로 유도

**토스페이먼츠 대시보드에서 확인:**

`대시보드 → [거래] → [결제 내역]` → 테스트 결제 내역이 표시되는지 확인

**Stripe 대시보드에서 확인:**

`대시보드 → [Payments]` (Test mode ON) → 결제 세션이 `Succeeded` 상태인지 확인

---

#### 반복 테스트 팁

- 토스 테스트 모드에서는 같은 `orderId`로 2번 이상 결제하면 오류가 납니다.  
  매번 새 주문번호가 생성되는지 코드에서 확인하세요. (`Date.now()` 기반이면 자동으로 달라집니다.)
- Stripe Checkout 세션은 30분 뒤 만료됩니다. 테스트 중 너무 오래 기다리면 새로 시작하세요.
- Supabase `payments`·`credits` 테이블에 테스트 데이터가 쌓입니다.  
  실서비스 전환 전에 `DELETE FROM payments WHERE pg = 'toss';` 등으로 테스트 데이터를 정리하세요.

---

### 9.5 실서비스 전환 전 최종 점검 — 실제 결제로 검증하기

> 개발 완료 후, 서비스 오픈 직전에 실키(live key)로 전환하고  
> **자기 카드로 실제 소액 결제**를 해봐야 합니다.  
> 이것이 마지막 안전망입니다.

---

#### 전환 절차

**Step 1. 토스페이먼츠 실서비스 키로 교체**

1. 토스 대시보드 → `[개발] → [API 키]` → **실서비스** 탭
2. 실서비스 클라이언트 키 (`live_ck_...`) 복사
3. `index.html`의 `TOSS_CLIENT_KEY` 값 교체
4. Cloudflare Worker → `toss-verify` → `Settings → Variables`  
   → `TOSS_SECRET_KEY` 값을 실서비스 시크릿 키 (`live_sk_...`)로 교체

**Step 2. Stripe 실서비스 키로 교체**

1. Stripe 대시보드 오른쪽 상단 **[Test mode]** 토글 OFF (= Live mode)
2. `[Developers] → [API keys]` → `Publishable key` / `Secret key` 복사
3. Cloudflare Worker → `stripe-session` → `Settings → Variables`  
   → `STRIPE_SECRET_KEY` 값을 실서비스 시크릿 키 (`sk_live_...`)로 교체

> `index.html`에는 Stripe의 퍼블리셔블 키가 현재 이 구현에서는 사용되지 않습니다 (Checkout Session 방식).  
> Worker만 교체하면 됩니다.

**Step 3. 배포**

키 교체 후 `deploy.ps1`을 실행해서 index.html과 Worker를 반영합니다.

---

#### 실결제 점검 시나리오

아래 항목을 순서대로 실행합니다. **자신의 카드로 실제 결제**합니다.

| # | 점검 항목 | 확인 방법 |
|---|----------|---------|
| 1 | 가장 저렴한 패키지(베이직 ₩5,500)로 토스 결제 | 실제 결제문자 수신 확인 |
| 2 | 토스 대시보드 → 거래 내역에 ₩5,500 결제 기록 | 상태: 완료 |
| 3 | Supabase `payments` 테이블 → 레코드 삽입 확인 | `status = 'paid'` |
| 4 | Supabase `credits` 테이블 → delta = 50 삽입 확인 | 크레딧 충전 |
| 5 | 서비스 내 크레딧 잔액 UI 갱신 확인 (있는 경우) | 50 크레딧 표시 |
| 6 | 토스 대시보드에서 해당 결제 **환불** 처리 | 테스트 비용 회수 |
| 7 | Stripe로 $4.99 결제 반복 (위 1~5 동일) | 달러 결제문자 수신 |
| 8 | Stripe 대시보드에서 환불 처리 | Refund 완료 |

> 환불은 각 PG 대시보드에서 수동으로 처리할 수 있습니다.  
> 토스: `거래 → 결제 상세 → [취소/환불]`  
> Stripe: `Payments → 결제 상세 → [Refund]`

---

#### 실서비스 전환 후 주의사항

- 테스트 카드 번호(`4242 4242 ...`)는 **실서비스 키에서는 작동하지 않습니다.**  
  실제 카드만 사용 가능합니다.
- Worker 환경 변수에 실서비스 시크릿 키를 저장할 때 반드시 **Encrypt** 옵션을 켜세요.  
  키가 외부에 노출되면 타인이 내 계정으로 결제 조작을 할 수 있습니다.
- 실서비스 중 결제 오류가 발생하면, 토스/Stripe 대시보드의 **로그(Logs)** 탭에서  
  어떤 에러가 반환됐는지 먼저 확인하세요.
- 정산일·정산 주기를 각 PG 대시보드에서 미리 확인해두세요.  
  (토스는 기본 D+1, Stripe는 기본 주 1회 또는 월 1회)

---

## 10장. 웹사이트 코드와 Supabase 연결

### 8.1 HTML 파일에 Supabase 클라이언트 추가

```html
<!-- index.html <head> 안에 추가 -->
<script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2"></script>
<script>
  const SUPABASE_URL  = 'https://xxxxxxxxxxxx.supabase.co';  // Project URL
  const SUPABASE_ANON = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...'; // anon public key
  const _sb = supabase.createClient(SUPABASE_URL, SUPABASE_ANON);
</script>
```

### 8.2 Google 로그인 버튼

```javascript
async function signInWithGoogle() {
  const { error } = await _sb.auth.signInWithOAuth({
    provider: 'google',
    options: {
      redirectTo: 'https://portal.example.co.kr'
    }
  });
  if (error) console.error(error);
}
```

### 8.3 Kakao 로그인 버튼

```javascript
async function signInWithKakao() {
  const { error } = await _sb.auth.signInWithOAuth({
    provider: 'kakao',
    options: {
      redirectTo: 'https://portal.example.co.kr'
    }
  });
  if (error) console.error(error);
}
```

### 8.4 로그인 상태 감지

```javascript
_sb.auth.onAuthStateChange((event, session) => {
  if (session) {
    console.log('로그인됨:', session.user.email);
    // 로그인 후 UI 처리
  } else {
    console.log('로그아웃 상태');
  }
});
```

---

## 11장. 배포 자동화 스크립트 (Windows PowerShell)

> 로컬에서 작업한 파일을 NAS에 자동으로 업로드하는 스크립트입니다.  
> Git Bash의 `tar`를 사용하여 Google Drive 클라우드 파일도 포함 전송합니다.

```powershell
# deploy.ps1
$NAS_USER   = "admin"
$NAS_IP     = "192.168.x.x"
$LOCAL_PATH = "C:\path\to\your\webfiles"
$REMOTE_PATH = "/volume1/web/portal"
$GIT_BASH   = "C:\Program Files\Git\bin\bash.exe"

# POSIX 경로 변환
$drive   = $LOCAL_PATH.Substring(0,1).ToLower()
$posix   = '/' + $drive + ($LOCAL_PATH.Substring(2) -replace '\\', '/')

# tar로 묶어서 SSH 파이프로 전송
$cmd = "cd '$posix' && tar -czf - . | ssh -o StrictHostKeyChecking=no ${NAS_USER}@${NAS_IP} 'tar -xzf - -C ${REMOTE_PATH}/ --no-same-permissions'"
& $GIT_BASH -c $cmd
```

```batch
rem deploy.bat (더블클릭으로 실행)
@echo off
powershell -ExecutionPolicy Bypass -File "%~dp0deploy.ps1"
pause
```

---

## 12장. 역할 기반 접근 제어 (RBAC)

> 같은 웹사이트라도 사용자의 역할에 따라 다른 메뉴를 보여줘야 하는 경우가 많습니다.  
> DB의 `profiles.role` 값과 프런트엔드 로직을 연결하여 구현합니다.

### 12.1 설계 원칙

- **DB**: `profiles.role` 컬럼에 역할 문자열 저장 (`general`, `consultant`, `gfc` 등)
- **프런트엔드**: 로그인 후 profiles를 조회해 `userRole` 변수에 저장, UI 렌더링 시 참조
- **숨기기 vs 잠그기**: 완전히 숨기는 항목(`roleOnly`)과 보이지만 클릭 차단(`consultantOnly`)을 구분

```
사용자 유형    role 값       볼 수 있는 것
─────────────────────────────────────────────────────
비로그인        —            공개 + 미리보기(preview) 모드
일반 회원      general       공개 + 회원 전용 + 컨설팅 테이저(잠김)
경영지도사     consultant    general + 컨설팅 메뉴 실사용
GFC 파트너     gfc           consultant + 보험/전문 메뉴
```

### 12.2 로그인 후 역할 로드

```javascript
let userRole = 'general';  // 기본값

async function loadUserRole(userId) {
  const { data } = await _sb
    .from('profiles')
    .select('agreed_at, role')
    .eq('id', userId)
    .maybeSingle();
  if (data?.role) userRole = data.role;
  return !!(data?.agreed_at);  // 동의 완료 여부 반환
}
```

### 12.3 메뉴 데이터 플래그 체계

```javascript
const MENU = [
  // ① 공개: 누구나 볼 수 있음 (플래그 없음)
  { label:'도구', children:[...] },

  // ② 회원 전용: 비로그인 → preview, 로그인 → 정상 이용
  { label:'앱 스토어', memberOnly: true, iframe:'...' },

  // ③ 컨설팅 전용: 모든 로그인 사용자에게 보이되,
  //    consultant/gfc만 실 사용 — general은 "전용 서비스" 안내
  { label:'컨설팅', consultantOnly: true, iframe:'...' },

  // ④ GFC 전용: consultant/general에게 완전히 숨김
  { label:'경영종합진단', roleOnly: 'gfc', iframe:'...' },
];
```

### 12.4 렌더링 로직

```javascript
const canConsult = () => userRole === 'consultant' || userRole === 'gfc';

function renderMenu(node) {
  // GFC 전용 → 해당 role 아니면 아예 렌더 안 함
  if (node.roleOnly && userRole !== node.roleOnly) return;

  // 클릭 핸들러
  el.onclick = () => {
    if (node.consultantOnly) {
      if (!authUser)     { showPreview(node.iframe); return; }
      if (!canConsult()) { showDenied('consultant'); return; }  // "컨설팅 서비스 전용" 안내
    }
    if (node.memberOnly && !authUser) { showPreview(node.iframe); return; }
    loadPage(node.iframe);
  };
}
```

> **WorksFree Hub 사례**:  
> 컨설팅 노드 6개 항목 → `consultantOnly:true` (모든 로그인 사용자에게 초록 "컨설팅 전용" 칩으로 표시)  
> 경영종합진단·CEO 플랜 → `roleOnly:'gfc'` (GFC 아니면 메뉴 자체가 없음)

---

## 13장. 테스트 환경 구축 — Playwright + Supabase 분리

### 13.1 DB 환경 분리 전략

| 환경 | Supabase 프로젝트 | 용도 |
|------|-----------------|------|
| **Project A** | 운영 | 실 사용자 데이터, 실 결제 |
| **Project B** | 테스트/스테이징 | Playwright 자동 테스트, 테스트 계정 |

> Supabase Free 플랜은 프로젝트 2개까지 무료.  
> 테스트에서 `service_role` 키를 사용해도 운영 DB에 영향 없음.

### 13.2 테스트 계층 구조

```
tests/
├── fixtures.js            # 공통 픽스처 — 외부 API 모킹, 로그인 헬퍼
├── global-setup.js        # realdb 전용 — 테스트 계정 생성
├── global-teardown.js     # realdb 전용 — 테스트 계정 삭제
├── smoke.spec.js          # 빠른 스모크 테스트 (mock 모드)
├── auth.spec.js           # 인증 흐름 (mock 모드)
├── credit.realdb.spec.js  # 크레딧 RLS 검증 (real DB)
└── fixtures/
    ├── dart_valid_test.csv   # DART 조회 테스트 데이터 (UTF-8 BOM)
    └── dart_error_test.csv   # 오류 케이스 테스트 데이터
```

**두 가지 테스트 모드**:

| 모드 | 특징 | 언제 사용 |
|------|------|----------|
| `mock` | 외부 API 전부 인터셉트, 인터넷 불필요 | 매 커밋, CI |
| `realdb` | 실제 Supabase Project B 사용 | DB 스키마/RLS 검증 |

### 13.3 환경 변수 설정

`.env.test.example`을 복사해 `.env.test` 생성 (`.gitignore`에 추가 필수):

```bash
# .env.test — Project B 키 입력 (절대 커밋 금지)
TEST_SUPABASE_URL=https://YOUR_TEST_PROJECT_ID.supabase.co
TEST_SUPABASE_ANON=eyJ...anon_key...
TEST_SUPABASE_SERVICE_KEY=eyJ...service_role_key...   # Admin API 용

TEST_USER_PASSWORD=TestPassword123!
TEST_ADMIN_PASSWORD=AdminPassword123!
```

> `TEST_SUPABASE_SERVICE_KEY`는 테스트 계정 생성(Admin API)에만 사용.  
> **절대 프런트엔드 코드나 git에 포함시키지 않습니다.**

### 13.4 글로벌 Setup / Teardown

```javascript
// tests/global-setup.js
module.exports = async function globalSetup() {
  const admin = createClient(TEST_SUPABASE_URL, TEST_SUPABASE_SERVICE_KEY, {
    auth: { autoRefreshToken: false, persistSession: false }
  });

  // 테스트 계정 3종 생성
  const [userId, adminId, freeId] = await Promise.all([
    createTestUser(admin, 'test-paid@worksfree-test.local',  'general', 500),
    createTestUser(admin, 'test-admin@worksfree-test.local', 'gfc',     9999),
    createTestUser(admin, 'test-free@worksfree-test.local',  'general', 0),
  ]);

  // 다음 테스트 파일에서 참조 가능
  process.env.TEST_USER_ID  = userId;
  process.env.TEST_ADMIN_ID = adminId;
};

// tests/global-teardown.js — CASCADE로 credits/payments도 자동 삭제
module.exports = async function globalTeardown() {
  for (const id of [TEST_USER_ID, TEST_ADMIN_ID, TEST_FREE_ID]) {
    await admin.auth.admin.deleteUser(id);
  }
};
```

### 13.5 RLS 검증 테스트 패턴

```javascript
// credit.realdb.spec.js — 실제 DB에서 RLS 정책 검증
test('일반 사용자는 다른 사용자의 credits를 SELECT할 수 없다', async () => {
  const { data } = await userClient   // anon key + user JWT
    .from('credits')
    .select('*')
    .eq('user_id', adminId);          // 다른 사람 ID
  expect(data).toHaveLength(0);       // RLS가 빈 배열 반환
});

test('use_app reason으로는 INSERT 불가 (RLS 차단)', async () => {
  const { error } = await userClient
    .from('credits')
    .insert({ user_id: userId, delta: -50, reason: 'use_app' });
  expect(error).not.toBeNull();       // 정책 위반 → 오류
});
```

### 13.6 실행 방법

```powershell
# mock 테스트 (인터넷 불필요, 빠름)
npm test

# real DB 테스트 (Project B 연결 필요)
npm run test:realdb

# 전체
npm run test:all
```

---

## 부록 A. 전체 설정 순서 요약

```
[ 기초: 도메인·서버·인터넷 연결 ]
 1. 가비아에서 도메인 구매
 2. Cloudflare 계정 생성 → 도메인 추가 → 네임서버 주소 확인
 3. 가비아에서 네임서버를 Cloudflare로 변경 (전파 최대 48시간)
 4. DSM → 제어판 → SSH 활성화 / 홈 폴더 활성화
 5. DSM → 패키지 센터 → Web Station 설치
 6. Web Station → 가상 호스트 생성 (서브도메인별)
 7. Cloudflare Zero Trust → Tunnel 생성
 8. NAS SSH 접속 → cloudflared 설치 및 실행
 9. Tunnel → Public Hostname 설정 (서브도메인 ↔ NAS 포트)
10. 브라우저에서 https://portal.example.co.kr 접속 확인

[ 외부 API 연동 — 필요한 경우 ]
11. Cloudflare Worker 생성 (예: DART API 프록시)
12. Worker에 API 키 입력 후 Deploy
13. Worker Route 설정 (도메인 경로에 연결)

[ 회원 로그인 ]
14. Supabase → 프로젝트 생성 → API 키 복사
15. Google Cloud Console → OAuth 자격증명 발급 → Supabase에 입력
16. 카카오 개발자 콘솔 → 앱 생성 → Supabase에 입력
17. Supabase → URL Configuration → 허용 URL 등록
18. index.html에 Supabase 클라이언트 코드 추가 → 로그인 테스트

[ 데이터베이스 ]
19. supabase/phase1_check_before_run.sql 실행 → 현재 DB 상태 진단
20. supabase/phase1_db_setup.sql 실행 → profiles 보완 + credits/payments/credit_balance 생성
21. Authentication → Users에서 관리자 UUID 확인 → role='gfc' 지정 + 초기 크레딧 지급
22. 프런트엔드에서 credit_balance 뷰 조회 → 잔액 표시 확인

[ 결제 연동 ]
21. 토스페이먼츠 가입 → 테스트 API 키 확인 (즉시 가능)
22. Stripe 가입 → 테스트 API 키 확인 (즉시 가능)
23. 결제 검증 Cloudflare Worker 생성 및 배포 (toss-verify, stripe-session)
24. Worker 환경 변수에 시크릿 키 등록 (Encrypt 체크)
25. 결제 후 크레딧 DB 업데이트 로직 연결
26. 테스트 카드로 전체 흐름 반복 검증 (9.4 체크리스트)
27. 사업자 인증 완료 → 실서비스 키로 교체 → 실결제 점검 (9.5 체크리스트)

[ 역할 기반 접근 제어 ]
28. profiles.role 컬럼에 역할 값 정의 (general / consultant / gfc 등)
29. 프런트엔드 메뉴에 roleOnly / consultantOnly / memberOnly 플래그 설정
30. 로그인 후 profiles 조회 → userRole 변수에 저장 → 렌더링 시 참조

[ 테스트 환경 ]
31. Supabase Project B 생성 (테스트 전용)
32. .env.test.example → .env.test 복사 후 Project B 키 입력
33. npm test (mock) 및 npm run test:realdb 실행 확인

[ 배포 ]
34. 배포 스크립트(deploy.ps1) 작성
35. NAS에 SSH 무비번 로그인 설정
36. 배포 실행 → https://portal.example.co.kr 최종 확인
```

---

## 부록 B. 트러블슈팅

### Tunnel이 Disconnected 상태일 때

```bash
# NAS에서 cloudflared 상태 확인
sudo systemctl status cloudflared

# 재시작
sudo systemctl restart cloudflared
```

### SSH 접속 시 비밀번호를 계속 묻는 경우

```bash
# NAS 홈 폴더 권한 문제 → StrictModes off 확인
grep StrictModes /etc/ssh/sshd_config
# → StrictModes no 가 출력되어야 함

# 출력 없거나 yes이면 다시 설정
sudo sed -i 's/#StrictModes yes/StrictModes no/' /etc/ssh/sshd_config
sudo /usr/syno/bin/synosystemctl restart sshd
```

### Supabase 로그인 후 URL이 이상한 경우

- Supabase → Authentication → URL Configuration
- **Site URL**과 **Redirect URLs**에 서비스 도메인이 정확히 등록되어 있는지 확인
- 와일드카드 `/**` 포함 여부 확인

### `authorized_keys` 등록 후 키 인증이 안 될 때

Windows에서 `type` 명령으로 파일을 파이프하면 BOM이 붙어 키가 무효화됩니다.  
반드시 **Git Bash의 `cat`** 을 사용하세요:

```bash
# Git Bash에서 실행
cat ~/.ssh/id_ed25519.pub | ssh admin@192.168.x.x 'cat > ~/.ssh/authorized_keys'
```

### Web Station 포트 충돌

- DSM 기본 포트(80, 443)와 Web Station 포트가 겹치는 경우 발생
- Web Station은 8080~8090 대역 사용 권장
- DSM → 제어판 → 네트워크 → DSM 설정에서 DSM 포트 변경 가능

### Cloudflare SSL 에러 (526 오류)

- SSL/TLS 모드를 **Full**로 변경 (Full strict → Full)
- NAS에 유효한 인증서가 없을 때 발생

---

## 부록 C. 포트 구성 참고표

| 환경 | 서브도메인 | NAS 포트 | 문서 루트 |
|------|-----------|---------|----------|
| 운영(prod) | `portal.example.co.kr` | 8080 | `/volume1/web/portal` |
| 스테이징 | `staging.example.co.kr` | 8082 | `/volume1/web/staging` |
| 테스트 | `test.example.co.kr` | 8081 | `/volume1/web/test` |

---

*이 가이드는 2025~2026년 WorksFree Hub 구축 경험을 바탕으로 작성되었습니다. 각 서비스의 UI는 업데이트될 수 있으므로 공식 문서를 병행하여 확인하세요.*

---

## 부록 D. 파일 위치 참고 (WorksFree Hub 기준)

| 항목 | 경로 |
|------|------|
| 메인 SPA | `synology-web/index.html` |
| DB 상태 진단 | `synology-web/supabase/phase1_check_before_run.sql` |
| DB 설정 스크립트 | `synology-web/supabase/phase1_db_setup.sql` |
| 테스트 픽스처 | `synology-web/tests/fixtures/` |
| 테스트 환경변수 템플릿 | `synology-web/.env.test.example` |
| Playwright 설정 | `synology-web/playwright.config.js` |
| 배포 스크립트 | `synology-web/deploy.ps1` |
| DART Worker | `synology-web/consulting/dart/worker.js` |
| 이 가이드 | `synology-web/NAS웹서비스_구축가이드.md` |
