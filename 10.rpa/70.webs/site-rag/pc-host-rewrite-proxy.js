// pc-host-rewrite-proxy.js — Ollama 앞단 초경량 Host-헤더 재작성 프록시
//
// 문제: Ollama는 DNS 리바인딩 방지를 위해 요청의 Host 헤더가 localhost/127.0.0.1 계열이
// 아니면 403으로 거부한다(OLLAMA_ORIGINS로는 우회 안 됨 — 별도 검증 로직, 직접 재현 확인).
// Cloudflare Tunnel은 클라이언트가 요청한 원래 Host(pc-ai.worksfree.kr)를 그대로 origin에
// 전달하므로 매번 차단당한다.
//
// 해결: 터널의 Service URL을 Ollama(11434) 대신 이 프록시(기본 8765)로 향하게 하고,
// 이 프록시가 Host 헤더만 "localhost:11434"로 바꿔서 실제 Ollama에 전달한다.
// biz-rag, ocr-service 등 pc-ai.worksfree.kr을 쓰는 모든 기능에 공통 적용됨.
//
// 실행: node pc-host-rewrite-proxy.js
// (PC_설정가이드.md에 상시 실행 방법 별도 정리)

const http = require("http");

const LISTEN_PORT = process.env.PROXY_PORT || 8765;
const TARGET_HOST = "localhost";
const TARGET_PORT = 11434;

const server = http.createServer((req, res) => {
  const proxyReq = http.request(
    {
      host: TARGET_HOST,
      port: TARGET_PORT,
      path: req.url,
      method: req.method,
      headers: { ...req.headers, host: `${TARGET_HOST}:${TARGET_PORT}` },
    },
    (proxyRes) => {
      res.writeHead(proxyRes.statusCode, proxyRes.headers);
      proxyRes.pipe(res);
    }
  );
  proxyReq.on("error", (err) => {
    console.error("[proxy] upstream error:", err.message);
    res.writeHead(502, { "content-type": "text/plain" });
    res.end("Bad Gateway (Ollama unreachable)");
  });
  req.pipe(proxyReq);
});

// "0.0.0.0"(전체 인터페이스) 바인딩 — 원래는 127.0.0.1(로컬 전용)이었는데, pc-ai.worksfree.kr의
// Cloudflare Tunnel 라우트가 이 PC 자신이 커넥터인 터널(lifeart_ai)에서 NAS가 커넥터인
// 터널(worksfree)로 옮겨가면서(2026-07-25) NAS가 LAN IP(192.168.100.36:8765)로 이 프록시에
// 접근해야 하게 됐다 — 127.0.0.1 바인딩으로는 같은 PC 안에서만 접근 가능해서 NAS발 요청이
// 전부 응답 없이 타임아웃났다. 인증 자체는 없지만(detect_server.py와 동일 패턴), Cloudflare
// Access가 터널 앞단에서 막아주므로 로컬 서버는 신뢰된 요청만 받는다고 가정한다.
server.listen(LISTEN_PORT, "0.0.0.0", () => {
  console.log(`[proxy] listening on 0.0.0.0:${LISTEN_PORT} -> ${TARGET_HOST}:${TARGET_PORT} (Host header rewritten)`);
});
