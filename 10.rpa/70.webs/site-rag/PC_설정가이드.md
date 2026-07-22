# PC 로컬 AI 서버 설정 가이드 — Ollama + Cloudflare Tunnel + Access

"🤖 AI 상담사" 노드가 이 PC의 Ollama를 답변 생성 백엔드로 쓰기 위한 설정. 코드/스크립트로 자동화할 수 없는
Cloudflare 대시보드 단계 위주로 정리했다.

## 0. 설치·모델 상태 (완료됨 — 이 PC 기준)

- Ollama `0.32.0`, cloudflared `2026.6.0` 이미 설치돼 있음 (`winget install`로 새로 설치할 필요 없음)
- GPU: RTX 5090 (32GB VRAM) — 여유 충분
- 임베딩 모델: `bge-m3` (1024차원) — pull 완료, `localhost:11434/api/embeddings`로 정상 응답 확인
- 생성 모델: `gemma4:12b` — 이미 로컬 보유, 웜 상태 5~10초 응답 확인 (Korean 품질 양호)
  - `qwen3:30b`는 hybrid-thinking 때문에 매 요청 12초 이상 걸려 제외 (직접 측정 결과)
- OCR 모델: `glm-ocr:latest` (0.9B, 2.2GB) — pull 완료. **반드시 `/api/generate` 사용**
  (`/api/chat`은 vision 처리에 공식적으로 알려진 문제 있음), **`options.stop:["```"]` 필수** —
  없으면 텍스트 추출 후 멈추지 못하고 "```"를 토큰 상한까지 무한 반복 생성함(직접 재현 확인).
  `ocr-service` 워커(`workers/ocr-service/index.js`)에 이미 반영됨.

## 1. cloudflared 터널 생성 (대시보드)

기존 NAS 터널(`worksfree-nas`)과 완전히 별도인 새 터널을 만든다. **로컬 인증서 기반(`cloudflared tunnel login`)
방식 대신 대시보드에서 만드는 원격 관리형(token 기반) 터널을 쓴다** — 이 PC엔 `cert.pem`이 없고
(`cloudflared tunnel list` 실행 시 "Cannot determine default origin certificate path" 에러 확인됨),
token 방식은 로그인 절차 없이 바로 동작한다.

1. `one.dash.cloudflare.com` → **Networks → Tunnels → Create a tunnel**
2. 이름: `pc-ai`
3. 환경: **Windows** 선택 → 설치 명령어 화면에서 **토큰 문자열만 복사** (cloudflared는 이미 설치돼 있으므로
   설치 명령은 무시해도 됨)
4. **Public Hostname** 탭에서 라우트 추가:

   | 필드 | 값 |
   |------|-----|
   | Subdomain | `pc-ai` |
   | Domain | `worksfree.kr` |
   | Service Type | `HTTP` |
   | URL | `localhost:8765` ← **`11434`가 아니라 `8765`** (아래 1-1 참고) |

### 1-1. Host 헤더 재작성 프록시 (필수 — 안 하면 모든 요청이 403)

Ollama는 요청의 `Host` 헤더가 `localhost`/`127.0.0.1` 계열이 아니면 보안상 요청을 거부한다
(`OLLAMA_ORIGINS`로는 우회 안 됨 — 직접 재현 확인). Cloudflare Tunnel은 클라이언트가 요청한
원래 Host(`pc-ai.worksfree.kr`)를 그대로 넘기므로, Tunnel → Ollama를 바로 연결하면 매번 403이 난다.

그래서 `pc-host-rewrite-proxy.js`(Host 헤더만 `localhost:11434`로 바꿔주는 초경량 프록시, 8765번
포트)를 Tunnel과 Ollama 사이에 둔다. 위 Public Hostname의 URL을 `11434`가 아니라 `8765`로 잡은
이유가 이것이다.

**PC 재부팅 후에도 자동으로 켜지게 만들기** (1회, 관리자 권한 PowerShell 필요):

```powershell
# 시작 메뉴 → PowerShell 검색 → 마우스 오른쪽 클릭 → "관리자 권한으로 실행"
cd D:\drive_files\10.worksfree\10.rpa\70.webs\site-rag
.\register_host_rewrite_task.ps1
```

Windows 작업 스케줄러에 `WorksFree-PC-Host-Rewrite-Proxy` 작업으로 등록되며, 로그온할 때마다
콘솔 창 없이 자동 실행되고 죽으면 1분 뒤 자동 재시작한다. 등록 직후 바로 테스트하려면:

```powershell
Start-ScheduledTask -TaskName "WorksFree-PC-Host-Rewrite-Proxy"
curl.exe http://127.0.0.1:8765/api/tags   # Ollama 모델 목록 JSON이 나오면 성공
```

5. PowerShell(관리자)에서 Windows 서비스로 등록 — PC 재부팅 후에도 자동 시작:

   ```powershell
   cloudflared service install <3번에서 복사한 토큰>
   ```

## 2. Cloudflare Access로 잠그기 (필수 — 건너뛰지 말 것)

Ollama 자체엔 인증 기능이 없다. Access 없이 터널만 걸면 `https://pc-ai.worksfree.kr`을 아는 누구나
이 PC의 GPU를 무료로 쓸 수 있다.

1. `one.dash.cloudflare.com` → **Access → Applications → Add an application → Self-hosted**
2. Application domain: `pc-ai.worksfree.kr`
3. 정책(Policy) 추가 — **Service Auth** 타입으로 만들고 브라우저 로그인 UI는 비활성화 (사람이 아니라
   `biz-rag` Worker만 호출해야 하므로)
4. 저장 후 **Service Tokens** 메뉴에서 토큰 발급 → `Client ID` / `Client Secret` 확보
5. 이 두 값을 `biz-rag` Worker 시크릿으로 등록한다 (아래 4번 참고):

   ```powershell
   cd 10.rpa/70.webs/synology-web/workers/biz-rag
   npx wrangler secret put CF_ACCESS_CLIENT_ID
   npx wrangler secret put CF_ACCESS_CLIENT_SECRET
   ```

## 3. 검증

```powershell
# 브라우저로 직접 접속 시 Access에 막혀야 정상 (그냥 접속되면 2번 설정 재확인)
# 반대로 Service Token 헤더를 실어 보내면 통과해야 함
curl.exe -s -X POST https://pc-ai.worksfree.kr/api/embeddings `
  -H "CF-Access-Client-Id: <Client ID>" `
  -H "CF-Access-Client-Secret: <Client Secret>" `
  -H "Content-Type: application/json" `
  --data-binary "{\"model\":\"bge-m3\",\"prompt\":\"테스트\"}"
```

## 4. PC 상시 가동을 위한 설정

- **절전 모드 비활성화**: 설정 → 시스템 → 전원 및 절전 → "화면 켜짐 유지 시간"·"절전 모드" 둘 다 "안 함"
  (노트북이면 전원 연결 시에도 동일하게 설정)
- **모델 상주 유지(선택)**: Ollama는 기본적으로 5분간 미사용 시 모델을 GPU에서 내린다. 매 첫 요청마다
  재로딩 지연(수 초)을 피하려면 시스템 환경 변수 `OLLAMA_KEEP_ALIVE=30m` 설정 후 Ollama 재시작을 고려할 수
  있다. 다만 이 PC는 다른 대형 모델(`gpt-oss:120b` 등)도 자주 쓰므로, 무기한(`-1`)이 아니라 30분 정도로
  제한해 VRAM을 계속 점유하지 않도록 한다.

## 5. 나머지 배포 전 준비 (Worker 폴더에서 1회)

```powershell
cd 10.rpa/70.webs/synology-web/workers/biz-rag

# 사용량 제한용 KV
npx wrangler kv namespace create RAG_RATE_LIMIT
# → 출력된 id를 wrangler.toml의 REPLACE_WITH_KV_NAMESPACE_ID에 채워 넣기

# 검색용 Vectorize 인덱스 (site-rag/scripts/build_rag_index.py 로 vectors.ndjson 을 먼저 만들어둘 것)
npx wrangler vectorize create biz-rag-index --dimensions=1024 --metric=cosine
npx wrangler vectorize insert biz-rag-index --file=../../../site-rag/vectors.ndjson

# PC 터널 주소
npx wrangler secret put PC_AI_URL   # 예: https://pc-ai.worksfree.kr
```

**Supabase**: `10.rpa/70.webs/supabase/core/ai_helper_setup.sql` 파일 전체를 Supabase 대시보드
SQL Editor에서 1회 실행 — 대화 기록 테이블(`ai_helper_messages`)과 보관 정리 RPC를 만든다. 실행 후
파일 맨 아래 검증 쿼리 3개 결과를 확인.

마지막으로 워커 배포:
```powershell
npx wrangler deploy
```

## 6. ocr-service Worker 배포 준비

`biz-rag`와 같은 `pc-ai.worksfree.kr` 터널 + Access 앱을 그대로 재사용한다 — 새 터널·Access 앱 불필요.

```powershell
cd 10.rpa/70.webs/synology-web/workers/ocr-service
# KV는 이미 생성됨(OCR_RATE_LIMIT, wrangler.toml에 id 기입 완료)
npx wrangler secret put CF_ACCESS_CLIENT_ID       # biz-rag와 동일한 biz-rag-worker 토큰 값
npx wrangler secret put CF_ACCESS_CLIENT_SECRET   # 위와 동일 토큰의 Secret
npx wrangler secret put PC_AI_URL                 # https://pc-ai.worksfree.kr
npx wrangler deploy
```

## 참고 — 왜 이렇게 나눴는가

- NAS 터널(`worksfree-nas`)과 PC 터널(`pc-ai`)은 서로 완전히 독립적이다. PC가 꺼져 있어도 NAS 웹사이트
  자체는 정상 동작하고, "AI 상담사" 기능만 "로컬 AI 서버가 오프라인입니다" 메시지를 띄운다.
- Access를 Worker 전용으로 잠근 이유: Ollama가 브라우저에 직접 노출되면 인증 수단이 전혀 없어
  누구나 이 PC의 GPU 자원을 무단으로 사용할 수 있기 때문이다.
