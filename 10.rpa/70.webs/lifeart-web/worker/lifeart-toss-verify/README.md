# lifeart-toss-verify — 이식성(portability) 확인

## 결론
`index.js`는 **Cloudflare 전용 API를 하나도 쓰지 않습니다** — 확인된 사용 API 전부가
표준 Web API(`fetch`, `Request`, `Response`, `URL`, `btoa`, `JSON`)뿐입니다.
(`caches`, KV 바인딩, Durable Objects, `ctx.waitUntil` 등 Cloudflare 고유 기능 사용 0건 — 직접 grep 검증)

즉 **`export default { async fetch(request, env) {...} }` 형태를 그대로 받아주는
어떤 런타임에서도 코드 한 줄 수정 없이 그대로 구동됩니다**: Cloudflare Workers,
Deno Deploy, Vercel Edge Functions 등. Node.js(18+)에서도 아래처럼 얇은 어댑터
하나만 씌우면 동일 파일을 그대로 씁니다.

## 필요 환경변수 (플랫폼 무관, 이름만 맞으면 됨)
```
TOSS_SECRET_KEY            토스 시크릿 키
SUPABASE_URL                Supabase 프로젝트 URL
SUPABASE_SERVICE_ROLE_KEY   Supabase service_role 키
SKIP_EMAIL_CONFIRM          "true"/"false" (선택, 이메일 인증 임시 우회용)
```
Cloudflare에서는 `wrangler secret put <이름>`으로 등록했던 것과 동일한 이름/값을
새 플랫폼의 환경변수(예: Vercel `vercel env add`, Node라면 `.env` + dotenv)로
그대로 옮기면 됩니다. **단, 시크릿 "값"은 어느 플랫폼에서든 한번 저장하면 재조회가
안 되므로(write-only 설계가 업계 공통 관행), 이관 시엔 각 서비스(Toss/Supabase)
대시보드에서 값을 다시 발급/복사해 새 플랫폼에 입력해야 합니다.**

## Node.js 18+ 최소 어댑터 (index.js 무수정, 그대로 import)
```js
// server.js — Cloudflare 없이 순수 Node로 동일 index.js 구동
import { createServer } from 'node:http';
import worker from './index.js';           // 수정 없이 그대로 재사용

const env = {
  TOSS_SECRET_KEY: process.env.TOSS_SECRET_KEY,
  SUPABASE_URL: process.env.SUPABASE_URL,
  SUPABASE_SERVICE_ROLE_KEY: process.env.SUPABASE_SERVICE_ROLE_KEY,
  SKIP_EMAIL_CONFIRM: process.env.SKIP_EMAIL_CONFIRM,
};

createServer(async (req, res) => {
  const chunks = [];
  for await (const c of req) chunks.push(c);
  const request = new Request(`http://localhost${req.url}`, {
    method: req.method,
    headers: req.headers,
    body: chunks.length ? Buffer.concat(chunks) : undefined,
  });
  const response = await worker.fetch(request, env);
  res.writeHead(response.status, Object.fromEntries(response.headers));
  res.end(Buffer.from(await response.arrayBuffer()));
}).listen(8787);
```
(Node 18+ 는 `Request`/`Response`/`fetch`가 전역으로 이미 내장돼 있어 별도 폴리필 불필요)

## 배포 파이프라인 자체(다른 것)
`wrangler deploy` 명령·`wrangler.toml`은 Cloudflare 고유 배포 도구이므로 이것만
새 플랫폼 방식(예: Vercel `vercel deploy`, 일반 서버라면 `pm2`/systemd)으로
바뀝니다 — **로직(index.js)은 그대로, 배포 명령만 플랫폼에 맞게 교체.**
