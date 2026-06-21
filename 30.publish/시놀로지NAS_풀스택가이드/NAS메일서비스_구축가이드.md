---

## 이 가이드를 읽기 전에 — 전체 그림 먼저 이해하기

이 가이드는 **시놀로지 NAS를 이메일 서버로 사용하는 방법**을 단계별로 설명합니다.

일반적으로 자체 메일 서버를 구축하려면 포트 25(SMTP)를 외부에 공개해야 합니다. 그러나 국내 가정·사무용 인터넷 회선은 스팸 방지 목적으로 포트 25 인바운드를 차단하며, Cloudflare Tunnel 역시 HTTP/HTTPS 전용이라 SMTP를 터널링할 수 없습니다.

이 가이드는 그 제약을 우회하기 위해 다음 세 가지 무료 서비스를 조합합니다.

| 역할 | 서비스 | 비용 |
|------|--------|------|
| 이메일 발신 SMTP 릴레이 | Resend | 무료 (100건/일, 3,000건/월) |
| 이메일 수신 MX 처리 | Cloudflare Email Routing | 무료 |
| 수신 이메일 NAS 전달 | Cloudflare Email Worker + NAS Bridge | 무료 |

> **전제 조건**: NAS 웹 서비스 구축 가이드의 내용(Cloudflare 도메인, Tunnel, Worker 환경)이 이미 완성되어 있어야 합니다.

---

## 전체 구성도

```
【발신 흐름】
사용자 (MailPlus 작성)
    │
    ▼
Synology MailPlus Server
    │  SMTP (포트 587, STARTTLS)
    ▼
Resend SMTP Relay  (smtp.resend.com)
    │  실제 SMTP 발송
    ▼
수신자 받은편지함

【수신 흐름】
외부 발신자
    │  (to: 누구든@worksfree.kr)
    ▼
Cloudflare Email Routing  ← MX 레코드 자동 관리
    │  Email Worker 호출
    ▼
Cloudflare Email Worker  (email-receiver)
    │  HTTP POST — raw MIME 스트림
    ▼
bridge.worksfree.kr  ← Cloudflare Tunnel 경유
    │  NAS 내부 포트 3001
    ▼
NAS Email Bridge  (Docker, Node.js)
    │  localhost:25 (내부 SMTP)
    ▼
Synology MailPlus Server
    │
    ▼
사용자 받은편지함
```

**핵심 원리**: 수신 경로에서 포트 25는 NAS 내부(localhost)에서만 사용됩니다. 외부로 포트 25를 열지 않아도 되는 이유입니다.

---

## 사전 준비물

| 항목 | 확인 사항 |
|------|----------|
| 시놀로지 NAS | DSM 7.x 이상, Docker(컨테이너 관리자) 패키지 설치됨 |
| Cloudflare 계정 | 도메인 DNS 관리 중, Tunnel 운영 중 |
| Resend 계정 | resend.com 가입 완료, API 키 보유 |
| 도메인 | 예: `worksfree.kr` (Cloudflare DNS 관리 중) |
| NAS SSH 접속 | wfadmin 또는 admin 계정 |

---

## 1장. Synology MailPlus Server 설치 및 도메인 설정

### 1.1 MailPlus Server 패키지 설치

DSM → **패키지 센터** → 검색: `MailPlus Server` → **설치**

> MailPlus Server(메일 서버)와 MailPlus(메일 클라이언트)는 별개 패키지입니다. 둘 다 설치하면 DSM 안에서 웹 메일 클라이언트까지 사용할 수 있습니다.

### 1.2 도메인 추가

**MailPlus Server → 도메인 → 추가**

| 항목 | 값 |
|------|-----|
| 도메인 이름 | `worksfree.kr` |
| 기본 이메일 주소 형식 | 계정 이름 |

> **"도메인 이름이 이미 있습니다" 오류가 나는 경우**
>
> 해당 도메인이 기존 도메인의 추가 도메인(별칭)으로 등록되어 있을 수 있습니다.
> MailPlus → 도메인 → 기존 도메인 선택 → **편집** → 추가 도메인 필드에서 해당 도메인 제거 후 저장.
> 그 다음 다시 독립 도메인으로 추가합니다.

### 1.3 메일 계정 생성

**MailPlus Server → 계정 → 생성**

- 도메인: `worksfree.kr` 선택
- 계정 이름: 예) `wfadmin` → 이메일 주소: `wfadmin@worksfree.kr`

### 1.4 FQDN 설정 확인

**MailPlus Server → 메일 배달 → 일반 탭**

| 항목 | 권장값 |
|------|--------|
| 호스트 이름 (FQDN) | `mail.worksfree.kr` |
| 전자 메일당 최대 크기 (MB) | `25` |

> 최대 크기를 25MB로 설정해야 Cloudflare Email Routing의 최대 수신 크기(25MB)와 일치합니다.

### 1.5 이메일 별칭 설정 — 5개 계정으로 더 많은 주소 운영하기

MailPlus Server 무료 라이선스는 계정 5개까지만 허용합니다. 별칭(Alias)을 사용하면 추가 라이선스 없이 여러 이메일 주소를 한 계정에서 수신할 수 있습니다.

**예시**: `info@worksfree.kr`, `support@worksfree.kr`, `hello@worksfree.kr` → 모두 `wfadmin` 계정 받은편지함으로 수신. 라이선스는 1개만 사용.

> **별칭 vs 메일 그룹**
>
> - **별칭(Alias)**: 여러 이메일 주소 → 한 계정. 계정 수 절약용.
> - **메일 그룹(Group)**: 하나의 주소 → 여러 계정 동시 전달. 팀 공지용.

#### 별칭 설정 방법

**MailPlus Server → 도메인 탭 → `worksfree.kr` 선택 → 편집**

도메인 편집 창 안에서 **별칭(Aliases)** 항목을 찾아 추가합니다.

| 입력 항목 | 예시 값 |
|----------|---------|
| 별칭 주소 | `info` (→ `info@worksfree.kr`) |
| 수신 계정 | `wfadmin` (또는 다른 활성 계정 선택) |

**추가 가능한 별칭 예시:**

| 별칭 주소 | 용도 | 수신 계정 |
|----------|------|----------|
| `info` | 일반 문의 | `wfadmin` |
| `support` | 기술 지원 | `wfadmin` |
| `noreply` | 자동 발신 전용 | `wfadmin` |
| `admin` | 관리자 | `wfadmin` |
| `hello` | 마케팅 문의 | `wfadmin` |

> 별칭은 수신 전용입니다. 발신 시 `From` 주소를 별칭으로 표시하려면 MailPlus 클라이언트에서 **설정 → 계정 → 보낸 사람 주소 추가** 후 원하는 별칭 주소를 등록하세요.

#### 별칭 동작 확인

외부에서 `info@worksfree.kr`로 테스트 메일 발송 → `wfadmin` 계정 받은편지함에 수신되면 성공입니다.

---

## 2장. 발신 설정 — Resend SMTP 릴레이 연동

### 2.1 Resend에 도메인 등록 및 DNS 인증

**resend.com → Domains → Add Domain → `worksfree.kr` 입력**

Resend가 표시하는 DNS 레코드를 Cloudflare DNS에 추가합니다.

| 타입 | 이름 | 값 |
|------|------|----|
| TXT | `resend._domainkey` | `p=MIGf...` (DKIM) |
| MX | `send` | `feedback-smtp.us-east-1.amazonses.com` 우선순위 10 |
| TXT | `send` | `v=spf1 include:amazonses.com ~all` |
| TXT | `_dmarc` | `v=DMARC1; p=none;` (선택) |

> **Auto configure** 버튼을 클릭하면 Cloudflare와 연동하여 자동으로 레코드를 추가해줍니다. 모든 항목이 **Verified** 상태가 되어야 합니다.

### 2.2 Resend API 키 발급

**Resend → API Keys → Create API Key**

- 이름: `mailplus-relay` (구분용)
- Permission: Full access
- 생성 후 `re_...` 값을 즉시 복사 (이후 재확인 불가)

### 2.3 MailPlus SMTP 릴레이 설정

**MailPlus Server → 메일 배달 → 릴레이 설정 탭**

1. **"릴레이 서버를 통해 메일 보내기"** 선택
2. **서버 목록** → **추가**

| 항목 | 값 |
|------|-----|
| 호스트 이름 | `smtp.resend.com` |
| 포트 | `587` |
| 보안 | STARTTLS |
| 인증 사용 | ☑ 체크 |
| 사용자 이름 | `resend` |
| 비밀번호 | 위에서 발급한 `re_...` API 키 |

3. **확인** → **저장**

### 2.4 발신 테스트

MailPlus 웹 클라이언트(또는 DSM → MailPlus)에서 외부 이메일로 테스트 메일 발송.
Gmail 등 외부 메일함에 정상 수신되면 성공입니다.

> **SPF/DKIM 실패 오류가 나는 경우**
>
> 에러 메시지의 발신 IP가 NAS 공인 IP라면 릴레이 설정이 저장되지 않은 것입니다.
> 릴레이 설정 탭을 다시 확인하고 저장 버튼을 눌렀는지 확인하세요.

---

## 3장. Cloudflare Email Routing 활성화

수신 이메일의 MX 레코드를 Cloudflare가 관리하도록 합니다.

### 3.1 Email Routing 활성화

**Cloudflare 대시보드 → 좌측 메뉴 → Email → Email Routing → worksfree.kr 선택**

**Enable Email Routing** 클릭 → MX 레코드 자동 추가 확인

자동으로 추가되는 레코드:

| 타입 | 이름 | 값 |
|------|------|----|
| MX | `@` | `route1.mx.cloudflare.net` 우선순위 46 |
| MX | `@` | `route2.mx.cloudflare.net` 우선순위 47 |
| MX | `@` | `route3.mx.cloudflare.net` 우선순위 60 |
| TXT | `@` | `v=spf1 include:_spf.mx.cloudflare.net ~all` |

> 이 레코드들이 `@worksfree.kr`로 오는 모든 이메일을 Cloudflare가 먼저 수신하게 만듭니다.

### 3.2 기존 Routing 규칙 확인

**Routing rules 탭** → Catch-all 규칙이 **Drop / Disabled** 상태인지 확인

아직 Worker가 없으므로 이 상태로 두고 다음 장으로 진행합니다.

---

## 4장. NAS Email Bridge 구축

Cloudflare Email Worker에서 보내는 HTTP 요청을 받아 NAS 내부의 MailPlus(localhost:25)로 전달하는 경량 HTTP→SMTP 브릿지입니다.

### 4.1 브릿지 파일 생성

NAS SSH 접속:

```bash
ssh wfadmin@192.168.x.x
```

폴더 및 파일 생성:

```bash
mkdir -p /volume1/docker/email-bridge
cd /volume1/docker/email-bridge
```

**`package.json`**:

```bash
cat > package.json << 'EOF'
{
  "type": "module",
  "dependencies": {
    "express": "^4",
    "nodemailer": "^6"
  }
}
EOF
```

**`server.js`**:

```bash
cat > server.js << 'EOF'
import express from 'express';
import nodemailer from 'nodemailer';

const app = express();

const transport = nodemailer.createTransport({
  host: '127.0.0.1',
  port: 25,
  secure: false,
  tls: { rejectUnauthorized: false },
});

// Worker에서 오는 raw MIME 스트림 (첨부 파일 포함)
app.post('/email-inject',
  express.raw({ type: 'message/rfc822', limit: '50mb' }),
  async (req, res) => {
    if (req.headers['x-secret'] !== process.env.BRIDGE_SECRET)
      return res.status(403).json({ error: 'forbidden' });
    try {
      const from = req.headers['x-mail-from'];
      const to   = req.headers['x-mail-to'];
      await transport.sendMail({ envelope: { from, to }, raw: req.body });
      res.json({ ok: true });
    } catch (e) {
      console.error('inject error:', e.message);
      res.status(500).json({ error: e.message });
    }
  }
);

// 직접 테스트용 JSON 엔드포인트
app.post('/email-inject-json',
  express.json({ limit: '10mb' }),
  async (req, res) => {
    if (req.headers['x-secret'] !== process.env.BRIDGE_SECRET)
      return res.status(403).json({ error: 'forbidden' });
    try {
      const { from, to, subject, text, html } = req.body;
      await transport.sendMail({ from, to, subject, text, html });
      res.json({ ok: true });
    } catch (e) {
      console.error('inject error:', e.message);
      res.status(500).json({ error: e.message });
    }
  }
);

app.listen(3001, () => console.log('email-bridge :3001'));
EOF
```

**`docker-compose.yml`**:

```bash
cat > docker-compose.yml << 'EOF'
services:
  email-bridge:
    image: node:20-alpine
    working_dir: /app
    volumes:
      - /volume1/docker/email-bridge:/app
    command: sh -c "npm install && node server.js"
    environment:
      - BRIDGE_SECRET=여기를_강력한_임의문자열로_변경
    restart: unless-stopped
    network_mode: host
EOF
```

> `BRIDGE_SECRET` 값은 따옴표 없이 입력합니다. 예: `BRIDGE_SECRET=wf-email-2026-xK9mP3`
> `network_mode: host`는 컨테이너가 NAS의 localhost:25에 접근하기 위해 필수입니다.

### 4.2 브릿지 실행

```bash
sudo docker compose up -d
sudo docker compose logs -f
```

`email-bridge :3001` 로그가 출력되면 성공입니다. `Ctrl+C`로 로그 모니터링 종료.

---

## 5장. Cloudflare Tunnel에 브릿지 엔드포인트 추가

Cloudflare Email Worker가 브릿지를 호출할 수 있도록 공개 URL을 만듭니다.

### 5.1 Routes 추가 (Published application)

**Cloudflare 대시보드 → Networking → Tunnels → [tunnel 이름] 클릭 → Configure → Routes 탭 → [Add route] 버튼 → Published application**

| 항목 | 값 |
|------|-----|
| Subdomain | `bridge` |
| Domain | `worksfree.kr` |
| Service URL | `http://192.168.x.x:3001` (NAS 내부 IP) |

저장 후 `https://bridge.worksfree.kr` 엔드포인트가 생성됩니다.

### 5.2 브릿지 동작 확인

로컬 PowerShell에서 테스트:

```powershell
Invoke-RestMethod -Uri "https://bridge.worksfree.kr/email-inject-json" `
  -Method POST `
  -Headers @{
    "x-secret"      = "여기에_BRIDGE_SECRET_값"
    "Content-Type"  = "application/json"
  } `
  -Body '{"from":"test@worksfree.kr","to":"wfadmin@worksfree.kr","subject":"브릿지 테스트","text":"정상 동작 확인"}'
```

`{ ok: true }` 응답과 함께 MailPlus 받은편지함에 메일이 도착하면 성공입니다.

---

## 6장. Cloudflare Email Worker 배포

Cloudflare Email Routing에서 수신한 이메일을 NAS 브릿지로 전달하는 Worker입니다.

### 6.1 Worker 파일 생성

로컬 프로젝트에서:

**`synology-web/workers/email-receiver/worker.js`**:

```javascript
/**
 * Cloudflare Email Worker — 수신 이메일 → NAS MailPlus 브릿지
 *
 * 배포: wrangler deploy --config workers/email-receiver/wrangler.toml
 *
 * 시크릿:
 *   BRIDGE_SECRET — NAS email-bridge 인증 키
 */

export default {
  async email(message, env) {
    // raw MIME 스트림을 직접 브릿지로 전달 (base64 변환 없음 — CPU 절약)
    const chunks = [];
    const reader = message.raw.getReader();
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      chunks.push(value);
    }
    const merged = chunks.reduce((a, b) => {
      const c = new Uint8Array(a.length + b.length);
      c.set(a); c.set(b, a.length);
      return c;
    });

    const res = await fetch('https://bridge.worksfree.kr/email-inject', {
      method: 'POST',
      headers: {
        'Content-Type': 'message/rfc822',
        'x-secret':    env.BRIDGE_SECRET,
        'x-mail-from': message.from,
        'x-mail-to':   message.to,
      },
      body: merged,
    });

    if (!res.ok) {
      const err = await res.text();
      throw new Error(`bridge inject failed (${res.status}): ${err}`);
    }
  },
};
```

**`synology-web/workers/email-receiver/wrangler.toml`**:

```toml
name               = "email-receiver"
main               = "worker.js"
compatibility_date = "2025-01-01"
```

\pagebreak

### 6.2 시크릿 등록 및 배포

```powershell
cd synology-web

# BRIDGE_SECRET 등록
wrangler secret put BRIDGE_SECRET --config workers/email-receiver/wrangler.toml
# 프롬프트에 docker-compose.yml의 BRIDGE_SECRET 값 입력

# Worker 배포
wrangler deploy --config workers/email-receiver/wrangler.toml
```

---

## 7장. Cloudflare Email Routing 규칙 설정

### 7.1 Catch-all 규칙 변경

**Cloudflare → Email Routing → worksfree.kr → Routing rules 탭**

1. **Catch-all** 행의 `···` 클릭 → **Edit**
2. Action: `Drop` → **Send to a Worker** 변경
3. Worker: **email-receiver** 선택
4. **Save**
5. Status 토글 → **Enabled** 로 활성화

이 시점부터 `아무거나@worksfree.kr`로 오는 이메일이 MailPlus로 수신됩니다.

### 7.2 특정 주소 전용 규칙 추가 (선택)

Catch-all 외에 특정 주소만 다르게 처리하고 싶을 때 추가합니다.

**+ Create routing rule**

| 항목 | 예시 |
|------|------|
| Matcher | `To` / `info@worksfree.kr` |
| Action | Send to a Worker / email-receiver |

---

## 8장. 테스트 및 검증

### 8.1 발신 테스트

MailPlus 작성 → 외부 이메일(Gmail 등)로 발송

확인 항목:
- ✅ 수신자에게 정상 도착
- ✅ 발신자 주소가 `@worksfree.kr`로 표시
- ✅ 스팸함이 아닌 받은편지함 도착

### 8.2 수신 테스트 — 텍스트

외부에서 `wfadmin@worksfree.kr`로 텍스트 메일 발송 → MailPlus 받은편지함 확인

### 8.3 수신 테스트 — HTML + 인라인 이미지

외부에서 서식 있는 메일(이미지 포함) 발송 → MailPlus에서 이미지 정상 표시 확인

### 8.4 수신 테스트 — 첨부 파일

외부에서 파일 첨부 메일 발송 → MailPlus에서 첨부 파일 다운로드 확인

> 첨부 파일 수신이 안 된다면 Worker 로그를 확인하세요.
> ```powershell
> wrangler tail email-receiver --config workers/email-receiver/wrangler.toml
> ```
> `Exceeded CPU Limit` 오류 시 worker.js의 `body` 필드가 `merged` (Uint8Array)로 전달되는지 확인합니다.

### 8.5 답장 흐름 테스트

1. MailPlus에서 외부로 발송
2. 수신자가 답장
3. 답장이 MailPlus 받은편지함에 정상 수신

---

## 부록 A. 한도 및 제약사항

### 수신 한도

| 구간 | 제한 | 비고 |
|------|------|------|
| Cloudflare Email Routing | **25MB/통** | 절대 상한, 변경 불가 |
| Cloudflare Email Worker | 10만 호출/일 | 무료 플랜 기준 |
| NAS Email Bridge (express) | 50MB | `server.js`에서 조정 가능 |
| MailPlus 최대 메시지 크기 | 설정값 | 기본 10MB → 25MB로 변경 권장 |

### 발신 한도

| 구간 | 제한 | 비고 |
|------|------|------|
| Resend 무료 플랜 | **100건/일, 3,000건/월** | 초과 시 Resend 유료 전환 필요 |
| Resend 메시지 크기 | 40MB | MailPlus → Resend 발신 기준 |

> **Resend 유료 플랜**: $20/월 → 50,000건/월. 업무 메일 발송량이 많다면 업그레이드 고려.

### 수신에 Resend가 관여하지 않는 이유

수신 경로는 `Cloudflare Email Routing → Email Worker → NAS Bridge`로 구성됩니다.
Resend는 발신에만 사용되므로 수신량이 아무리 많아도 Resend 한도에 영향을 주지 않습니다.

---

## 부록 B. 트러블슈팅

### 발신 메일이 스팸으로 분류될 때

```
확인 순서:
1. Resend Domains → worksfree.kr → DKIM / SPF 상태가 Verified인지 확인
2. Cloudflare DNS에 DMARC 레코드 추가
   타입: TXT  이름: _dmarc  값: v=DMARC1; p=none;
3. Resend SMTP 릴레이가 정상 동작 중인지 확인
   (발신 IP가 NAS IP가 아닌 Amazon SES IP여야 함)
```

### 수신 메일이 오지 않을 때

```
확인 순서:
1. Cloudflare Email Routing → Routing rules → Catch-all이 Enabled인지 확인
2. Worker 로그 확인
   wrangler tail email-receiver --config workers/email-receiver/wrangler.toml
3. NAS 브릿지 로그 확인
   sudo docker compose -f /volume1/docker/email-bridge/docker-compose.yml logs --tail=30
4. bridge.worksfree.kr 접근 가능 여부 확인 (Cloudflare Tunnel 상태)
```

### 이메일 본문이 코드(헤더)로 보일 때

Worker의 `body`가 raw MIME이 아닌 텍스트 문자열로 전달된 경우입니다.
`worker.js`의 `fetch` 호출에서 `body: merged` (Uint8Array)인지 확인하세요.

### Docker 브릿지 실행 오류

```bash
# 권한 오류 시 sudo 사용
sudo docker compose up -d

# 포트 3001 충돌 확인
sudo netstat -tlnp | grep 3001

# 컨테이너 재시작
sudo docker compose -f /volume1/docker/email-bridge/docker-compose.yml restart
```

### MailPlus 패키지 재시작 방법

```bash
sudo synopkg stop MailPlus-Server
sudo synopkg start MailPlus-Server
```

---

## 부록 C. 파일 위치 참조

```
synology-web/
├── workers/
│   └── email-receiver/
│       ├── worker.js          # Cloudflare Email Worker
│       └── wrangler.toml      # Worker 배포 설정
│
└── NAS메일서버_구축가이드.md   # 이 문서

NAS 내부:
/volume1/docker/email-bridge/
├── server.js                  # HTTP→SMTP 브릿지
├── package.json
└── docker-compose.yml
```

---

## 부록 D. 전체 서비스 역할 요약

```
Resend              — 발신 SMTP 릴레이 (smtp.resend.com:587)
                      DKIM/SPF 서명 처리
                      무료 3,000건/월

Cloudflare Email    — 수신 MX 레코드 관리
Routing               @worksfree.kr 메일을 Cloudflare가 먼저 수신
                      Email Worker로 라우팅

Cloudflare Email    — 수신 메일을 NAS 브릿지로 HTTP 전달
Worker                raw MIME 스트림 그대로 전달 (CPU 최소화)
(email-receiver)

Cloudflare Tunnel   — bridge.worksfree.kr → NAS 내부 3001 포트 연결
                      포트 개방 없이 안전한 내부 접근

NAS Email Bridge    — HTTP 수신 → localhost:25 SMTP 전달
(Docker)              텍스트, HTML, 인라인 이미지, 첨부 파일 모두 처리
                      최대 50MB (조정 가능)

Synology MailPlus   — 최종 이메일 저장 및 사용자 인터페이스
Server                도메인별 계정 관리, 웹 클라이언트 제공
```
