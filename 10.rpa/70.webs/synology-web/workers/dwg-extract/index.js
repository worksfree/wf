/**
 * dwg-extract — DWG(AutoCAD 도면) 표제란/BOM 추출 전용 Cloudflare Worker.
 *
 * 흐름:
 *   1) Supabase access_token으로 로그인 사용자를 검증한다 (ocr-service/biz-rag와 동일 패턴).
 *   2) PC 로컬 서버(workers/dwg-extract-pc, Cloudflare Tunnel + Access로 보호됨)에
 *      DWG 파일을 base64로 보내 표제란/BOM 추출 결과를 받아온다.
 *   3) PC가 꺼져 있으면 명확한 에러 코드를 반환한다.
 *
 * ocr-service의 /ocr, /receipt와 달리 Ollama/GPU를 전혀 쓰지 않는다 — DWG는
 * GNU LibreDWG(오픈소스)로 벡터 텍스트를 직접 파싱하는 것이라 PC 부하가
 * 가볍고 응답도 빠르다(수 초 이내). 그래서 /detect(ocr-service)와 동일하게
 * 일일 횟수 제한(KV) 없이 로그인만 요구한다.
 *
 * 표제란/BOM 추출 알고리즘 자체와 실측 검증 근거는 워커가 아니라 PC 로컬
 * 서버 쪽(workers/dwg-extract-pc/dwg_extract.py)에 있다 — 이 워커는 인증과
 * 프록시 역할만 한다.
 *
 * POST /thumbnail — 텍스트 없는 도형 와이어프레임 SVG 생성(dwg_thumbnail.py).
 * O&M(admin/dwg-samples)에서 샘플 DWG를 교체할 때 썸네일을 재생성하는 용도로만
 * 쓰이며, /extract와 동일하게 로그인만 요구한다(관리자 전용 강제는 admin 페이지
 * 쪽에서 이미 이중 게이트로 처리 — 이 워커는 그 페이지가 호출하는 프록시일 뿐).
 *

 * 시크릿(전부 `wrangler secret put`으로만 설정, 평문 기재 금지):
 *   CF_ACCESS_CLIENT_ID / CF_ACCESS_CLIENT_SECRET — ocr-service와 동일 Service Token 재사용 가능
 *   PC_EXTRACT_URL      — 예: https://dwg-extract.worksfree.kr (workers/dwg-extract-pc)
 */

const SUPABASE_URL = "https://rkycwfpkzorfpcxfvaqt.supabase.co";
const SUPABASE_ANON =
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJreWN3ZnBrem9yZnBjeGZ2YXF0Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzgzMDk4OTQsImV4cCI6MjA5Mzg4NTg5NH0.u1HC0KiArbdqFAPpkRWsfZmMYqfZ-euRTHeNtUr2NBs";

const ALLOWED_ORIGINS = new Set([
  "https://test.worksfree.kr",
  "https://staging.worksfree.kr",
  "https://www.worksfree.kr",
  "https://portal.worksfree.kr",
]);

const EXTRACT_TIMEOUT_MS = 30000;
const MAX_DWG_B64_CHARS = 30_000_000; // 대략 원본 DWG 22MB 상당 상한(dwg_extract_server.py와 동일)

function corsHeaders(origin) {
  const allow = ALLOWED_ORIGINS.has(origin) ? origin : "https://test.worksfree.kr";
  return {
    "Access-Control-Allow-Origin": allow,
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
    Vary: "Origin",
  };
}
function json(obj, status, origin) {
  return new Response(JSON.stringify(obj), {
    status,
    headers: { "content-type": "application/json", ...corsHeaders(origin) },
  });
}

async function verifyUser(accessToken) {
  const r = await fetch(`${SUPABASE_URL}/auth/v1/user`, {
    headers: { Authorization: `Bearer ${accessToken}`, apikey: SUPABASE_ANON },
  });
  if (!r.ok) return null;
  const u = await r.json();
  return u && u.id ? u : null;
}

function fetchWithTimeout(url, options, timeoutMs) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  return fetch(url, { ...options, signal: controller.signal }).finally(() => clearTimeout(timer));
}

// PC 로컬 서버(dwg-extract-pc) 호출 — Ollama(PC_AI_URL)와는 별개 프로세스/포트.
async function runExtract(env, dwgBase64) {
  const r = await fetchWithTimeout(
    `${env.PC_EXTRACT_URL}/extract`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "CF-Access-Client-Id": env.CF_ACCESS_CLIENT_ID,
        "CF-Access-Client-Secret": env.CF_ACCESS_CLIENT_SECRET,
      },
      body: JSON.stringify({ dwg_base64: dwgBase64 }),
    },
    EXTRACT_TIMEOUT_MS
  );
  if (!r.ok) {
    const detail = await r.text().catch(() => "");
    console.error(`extract failed: status=${r.status} body=${detail.slice(0, 500)}`);
    throw new Error(`extract failed: ${r.status}`);
  }
  return r.json();
}

async function runThumbnail(env, dwgBase64) {
  const r = await fetchWithTimeout(
    `${env.PC_EXTRACT_URL}/thumbnail`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "CF-Access-Client-Id": env.CF_ACCESS_CLIENT_ID,
        "CF-Access-Client-Secret": env.CF_ACCESS_CLIENT_SECRET,
      },
      body: JSON.stringify({ dwg_base64: dwgBase64 }),
    },
    EXTRACT_TIMEOUT_MS
  );
  if (!r.ok) {
    const detail = await r.text().catch(() => "");
    console.error(`thumbnail failed: status=${r.status} body=${detail.slice(0, 500)}`);
    throw new Error(`thumbnail failed: ${r.status}`);
  }
  return r.json();
}

export default {
  async fetch(request, env) {
    const origin = request.headers.get("Origin") || "";
    const url = new URL(request.url);

    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: corsHeaders(origin) });
    }
    const KNOWN_PATHS = new Set(["/extract", "/thumbnail"]);
    if (request.method !== "POST" || !KNOWN_PATHS.has(url.pathname)) {
      return json({ error: "not_found" }, 404, origin);
    }

    let body;
    try {
      body = await request.json();
    } catch {
      return json({ error: "invalid_json" }, 400, origin);
    }

    const { access_token, dwg_base64 } = body || {};
    if (!access_token || typeof access_token !== "string") {
      return json({ error: "unauthenticated" }, 401, origin);
    }
    if (!dwg_base64 || typeof dwg_base64 !== "string") {
      return json({ error: "no_file" }, 400, origin);
    }
    if (dwg_base64.length > MAX_DWG_B64_CHARS) {
      return json({ error: "file_too_large" }, 400, origin);
    }

    const user = await verifyUser(access_token);
    if (!user) return json({ error: "invalid_session" }, 401, origin);

    if (!env.PC_EXTRACT_URL || !env.CF_ACCESS_CLIENT_ID || !env.CF_ACCESS_CLIENT_SECRET) {
      return json({ error: "server_misconfigured" }, 500, origin);
    }

    try {
      if (url.pathname === "/thumbnail") {
        const result = await runThumbnail(env, dwg_base64);
        return json({ ok: true, svg: result.svg || "" }, 200, origin);
      }
      const result = await runExtract(env, dwg_base64);
      return json(
        {
          ok: true,
          title_block: result.title_block || {},
          bom_headers: result.bom_headers || [],
          bom_rows: result.bom_rows || [],
          bom_found: !!result.bom_found,
        },
        200,
        origin
      );
    } catch (e) {
      return json({ error: "pc_offline", detail: String(e) }, 503, origin);
    }
  },
};
