# EP01: 클라우드 Vision API 대신 집 PC — Ollama + Cloudflare Tunnel로 로컬 GPU를 안전하게 서비스로 노출하기

**시리즈**: OCR 서비스구축 #1
**이 글을 읽고 나면**: RTX 5090이 달린 집 PC를 월 구독료 0원으로 웹 서비스의 AI 백엔드로 쓰는 구조를 이해하고, Ollama를 Cloudflare Tunnel + Access로 안전하게 외부에 노출할 수 있습니다.

---

## 핵심 한 줄 요약
> PC는 "상시 서버"가 아니라 "온디맨드 백엔드"로만 쓴다 — 꺼져 있으면 사용자에게 명확한 안내가 뜨는 구조로 설계하면, 가정용 PC도 프로덕션 AI 백엔드가 될 수 있다.

> **자주 묻는 질문**
> **Q. 클라우드 Vision API(Google/Naver Clova 등)를 안 쓰는 이유는?** → 이미지 1장당 과금되는 구조라 사용량이 늘수록 비용이 선형으로 늘어난다. 로컬 GPU는 전기료 외 추가 비용이 없다.
> **Q. PC가 꺼져 있으면 서비스가 완전히 죽나요?** → OCR·AI 답변 생성만 실패하고, 나머지 UI·정적 콘텐츠는 그대로 동작한다. Worker가 8~10초 타임아웃으로 빠르게 실패해 사용자를 무한 로딩에 가두지 않는다.
> **Q. Ollama를 인터넷에 그냥 노출하면 안 되나요?** → Ollama 자체엔 인증이 없다. 아무나 GPU를 공짜로 쓸 수 있게 되므로 반드시 Cloudflare Access(Service Token)로 앞단을 잠가야 한다.

---

## 문제 상황

웹서비스에 OCR·AI 답변 생성 기능을 붙이려면 방법은 셋 중 하나다.

1. **클라우드 Vision API** — 정확하지만 이미지 1장당 과금, 트래픽 늘면 비용도 같이 는다
2. **클라우드 GPU 서버 임대** — 상시 요금이 나간다(안 써도 나간다)
3. **집에 있는 GPU를 그대로 쓴다** — 이미 RTX 5090이 있다면 추가 비용은 전기료뿐

3번을 택했다. 다만 가정용 PC는 24시간 안정적으로 켜져 있다는 보장이 없다. 그래서 **"PC가 꺼져 있어도 서비스 전체가 안 죽는 구조"**로 설계하는 게 핵심이다.

---

## STEP 1: 전체 아키텍처

```
[브라우저] → [Cloudflare Worker] → (Cloudflare Tunnel + Access) → [집 PC: Ollama]
                    │
                    ├─ Supabase 세션 검증
                    ├─ KV 일일 사용량 제한
                    └─ 8~10초 타임아웃 → PC 오프라인 시 즉시 에러 반환
```

- **Worker가 게이트 역할**: 로그인 여부·일일 횟수 제한을 여기서 먼저 거른다. PC까지 요청이 가기 전에 남용을 차단한다.
- **PC는 순수 추론만 담당**: Ollama가 이미지를 받아 텍스트를 뽑아내는 일만 한다. 인증·과금·CORS는 전부 Worker 몫이다.

---

## STEP 2: Ollama 설치 + 모델 준비

```powershell
winget install Ollama.Ollama

# OCR용 모델 (이 시리즈 EP02에서 5종 비교 후 최종 채택)
ollama pull richardyoung/olmocr2:7b-q8

# 절전 모드 비활성화 필수 — PC가 잠들면 Ollama도 응답 못 함
powercfg /change standby-timeout-ac 0
```

---

## STEP 3: Cloudflare Tunnel로 외부 공개

```powershell
winget install --id Cloudflare.cloudflared
cloudflared tunnel create pc-ai
cloudflared service install --token <TUNNEL_TOKEN>
```

Cloudflare 대시보드 → Zero Trust → Networking → Tunnels → `pc-ai` → Public Hostname 추가:

| 필드 | 값 |
|------|-----|
| Subdomain | `pc-ai` |
| Domain | `worksfree.kr` |
| Service | `HTTP` → `localhost:11434` |

---

## STEP 4: Cloudflare Access로 잠그기 (필수)

Ollama는 자체 인증이 없다. Tunnel만 걸면 URL을 아는 누구나 GPU를 쓸 수 있다. **Zero Trust → Access → Applications**에서 `pc-ai.worksfree.kr`을 등록하고, 정책을 **Service Token 전용**으로 설정한다 — 브라우저 로그인 화면 없이 헤더 인증만으로 통과시키는 방식이다.

```js
// Cloudflare Worker에서 PC 호출 시
fetch(`${PC_AI_URL}/api/generate`, {
  headers: {
    "CF-Access-Client-Id": env.CF_ACCESS_CLIENT_ID,
    "CF-Access-Client-Secret": env.CF_ACCESS_CLIENT_SECRET,
  },
  // ...
});
```

---

## STEP 5: 실전에서 터진 버그 — Ollama의 Host 헤더 거부

Tunnel + Access까지 세팅하고 첫 호출을 날렸는데 **원인 불명의 403**이 떴다. WAF도, Access 정책도, Tunnel 설정도 문제가 없었다. 임시로 두 번째 cloudflared 연결(replica)을 `--loglevel debug`로 띄워 실제 요청·응답 로그를 직접 잡아본 뒤에야 범인을 찾았다.

> **Ollama는 기본적으로 `Host` 헤더가 `localhost`/`127.0.0.1`/`0.0.0.0`가 아니면 요청을 거부한다.** Tunnel을 거치면 Host 헤더가 `pc-ai.worksfree.kr`로 도착하므로 이 보안 기능에 걸려 조용히 막힌다. `OLLAMA_ORIGINS` 환경변수로는 해결되지 않는다(그건 CORS Origin 체크지 Host 헤더 체크가 아니다).

**해결책**: Ollama 앞에 Host 헤더만 재작성하는 초경량 Node.js 프록시를 하나 둔다.

```js
// pc-host-rewrite-proxy.js — 의존성 없음, Tunnel과 Ollama 사이에서 Host만 바꿔치기
const http = require("http");
http.createServer((req, res) => {
  const proxyReq = http.request(
    { host: "localhost", port: 11434, path: req.url, method: req.method,
      headers: { ...req.headers, host: "localhost:11434" } },
    (proxyRes) => { res.writeHead(proxyRes.statusCode, proxyRes.headers); proxyRes.pipe(res); }
  );
  req.pipe(proxyReq);
}).listen(8765, "127.0.0.1");
```

Tunnel의 Public Hostname 대상을 `localhost:11434`가 아니라 `localhost:8765`(이 프록시)로 바꾸면 해결된다.

---

## ✅ 완료 확인

- [ ] `ollama run richardyoung/olmocr2:7b-q8 "test"`가 로컬에서 정상 응답
- [ ] 외부망(LTE 등)에서 `https://pc-ai.worksfree.kr` 직접 접속 시 Access 로그인 화면으로 막힘
- [ ] Service Token 헤더를 실은 curl 요청은 정상 통과
- [ ] PC를 꺼둔 상태로 Worker 호출 시 `pc_offline` 에러가 10초 내 반환

---

## 다음 편 예고
> **EP02**: 로컬 GPU가 준비됐으니 이제 어떤 모델을 올릴지가 문제다. dots.ocr·PaddleOCR-VL·Baidu Unlimited-OCR까지 실제로 받아서 돌려본 결과, 셋 다 이 환경에서 막혔다 — 그 이유를 낱낱이 기록한다.

---

## 📱 30초 쇼츠 스크립트

**제목**: "집 PC로 OCR API를 만들면 진짜 공짜일까?"
**길이**: 27초

| 구간 | 화면 | 자막 |
|------|------|------|
| 00:00~00:03 | 블랙 자막 | "Q. 클라우드 Vision API 대신 집 PC를 쓰면?" |
| 00:03~00:06 | 요금 계산기 화면 | "이미지 1장당 과금 → 0원" |
| 00:06~00:09 | Ollama 403 에러 화면 | "그런데 첫 시도부터 알 수 없는 403" |
| 00:09~00:22 | 원인: Host 헤더 → 프록시 코드 → 정상 응답 | "Ollama가 Host 헤더를 검사하고 있었다 — 프록시 하나로 해결" |
| 00:22~00:27 | 블로그 링크 | "→ 전체 구조는 블로그에" |

**해시태그**: `#Ollama #CloudflareTunnel #로컬LLM #OCR #worksfree`
