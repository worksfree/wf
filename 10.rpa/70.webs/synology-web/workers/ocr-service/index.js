/**
 * ocr-service — "OCR" 노드(서비스 섹션)용 Cloudflare Worker.
 *
 * 흐름:
 *   1) Supabase access_token으로 로그인 사용자를 검증한다 (biz-rag/biz-report와 동일 패턴).
 *   2) KV로 사용자당 일일 호출 횟수를 제한한다 (PC GPU를 실제로 쓰는 기능이라 남용 방지 필요).
 *   3) PC의 Ollama(olmOCR-2-7B 모델, Cloudflare Tunnel + Access로 보호됨)에 이미지를 보내 텍스트를 추출한다.
 *   4) PC가 꺼져 있으면 명확한 에러 코드를 반환한다.
 *
 * 모델 비교 실측 결과 (2026-07-22, RTX 5090 로컬 PC에서 자동차등록증 PDF·영수증 사진·손글씨
 * 이미지로 직접 테스트, 문자 단위 오류율로 채점):
 *   - glm-ocr(0.9B, 이전 기본값): 표가 있는 복잡한 문서에서 표 섹션 전체를 통째로 누락하는
 *     현상이 반복 확인됨. 동그라미 숫자·표 서식이 많으면 실제 없는 LaTeX 마크업을 지어냄.
 *   - dots.ocr, PaddleOCR-VL, DeepSeek-OCR(frob/unlimited-ocr) — 이 PC의 Ollama에서 전부
 *     실사용 불가로 확인(dots.ocr: CLIP 비전 인코더 로드 자체가 실패 / PaddleOCR-VL: 커뮤니티
 *     빌드에 mmproj가 누락되어 텍스트 전용으로만 동작 / DeepSeek-OCR: 프롬프트를 바꿔가며
 *     재시도해도 반복 폭주 또는 빈 응답만 발생). 세 모델 모두 아키텍처 자체보다 Ollama용
 *     커뮤니티 패키징이 아직 불완전한 것이 원인으로 보임.
 *   - olmOCR-2-7B(Qwen2.5-VL 기반): 위 문제가 없고 표 섹션까지 정확히 인식, 손글씨는
 *     별도 후처리 없이도 오차율 1~3% 수준(사실상 목표 90% 초과 달성). 이번 교체의 근거.
 *
 * 반드시 /api/generate 사용 (biz-rag·glm-ocr와 동일 패턴 유지, /api/chat의 vision 처리에
 * 알려진 문제가 있어 비권장). temperature:0으로 결과 안정성 확보.
 *
 * 반복 폭주는 모델을 바꿔도 여전히 발생한다 — 실측으로 확인: olmOCR-2도 심하게 흐릿하거나
 * 저해상도인 사진에서는 동일 문구를 수십 회 반복하는 증상이 재현됨. repeat_penalty +
 * 응답 후처리(truncateRunawayRepetition)는 모델과 무관한 안전장치이므로 그대로 유지한다.
 *
 * 고해상도 원본 사진(스마트폰 12MP=4000x3000 등)을 그대로 보내면 비전 인코더가 소모하는
 * 토큰 수가 모델의 컨텍스트 예산(num_ctx)을 넘어서 요청이 실패하거나 응답이 몇 글자만에
 * 잘리는 현상이 실측으로 확인됨(원인 규명 전에는 "회전 문제"로 오인하기 쉬우니 주의).
 * 그래서 클라이언트(service/ocr/index.html)에서 긴 변 기준 1800px로 미리 축소해 전송하고,
 * 이 워커도 num_ctx를 여유 있게 잡는다.
 *
 * PDF는 이 워커에서 처리하지 않는다 — 클라이언트(PDF.js)가 페이지별로 이미지 렌더링 후
 * 페이지마다 이 엔드포인트를 호출하는 구조 (service/ocr/index.html 참고).
 *
 * 시크릿(전부 `wrangler secret put`으로만 설정, 평문 기재 금지):
 *   CF_ACCESS_CLIENT_ID / CF_ACCESS_CLIENT_SECRET — biz-rag와 동일 Service Token 재사용 가능
 *   PC_AI_URL          — 예: https://pc-ai.worksfree.kr
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

const DAILY_LIMIT = 30; // 이미지 1장 = 1회 (PDF는 페이지당 1회 소모). 관리자(profiles.role)는 무제한 — isAdmin() 참고
const OCR_MODEL = "richardyoung/olmocr2:7b-q8";
// 프롬프트는 짧고 단순하게 유지한다 — 실측으로 "HTML/Markdown 표를 쓰지 마라" 같은
// 부정 지시를 추가하면 오히려 결과가 더 불안정해짐을 확인했다(정상 문서에서 CER
// 0.19 → 0.47로 악화, <th colspan="2"> 같은 깨진 태그까지 섞여 나옴). OCR 특화
// 모델은 일반 지시문 준수보다 짧고 직접적인 요청에 더 안정적으로 반응한다.
const OCR_PROMPT =
  "Extract all text from this image exactly as it appears, preserving line breaks and reading order. " +
  "Output only the extracted text, no commentary.";
const OCR_TIMEOUT_MS = 30000;
const MAX_IMAGE_B64_CHARS = 12_000_000; // 대략 원본 이미지 9MB 상당 상한

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

// 관리자는 일일 횟수 제한 없이 사용 — profiles.role은 클라이언트가 아니라 서버(여기)에서
// 직접 조회해 신뢰한다(클라이언트가 role을 보내는 방식은 위조 가능해 금지 패턴).
async function isAdmin(accessToken, userId) {
  const r = await fetch(`${SUPABASE_URL}/rest/v1/profiles?id=eq.${userId}&select=role`, {
    headers: { Authorization: `Bearer ${accessToken}`, apikey: SUPABASE_ANON },
  });
  if (!r.ok) return false;
  const rows = await r.json().catch(() => []);
  return rows?.[0]?.role === "admin";
}

async function checkAndBumpRateLimit(env, userId) {
  const today = new Date().toISOString().slice(0, 10);
  const key = `${today}:${userId}`;
  const cur = parseInt((await env.OCR_RATE_LIMIT.get(key)) || "0", 10);
  if (cur >= DAILY_LIMIT) return { ok: false };
  await env.OCR_RATE_LIMIT.put(key, String(cur + 1), { expirationTtl: 90000 });
  return { ok: true, remaining: DAILY_LIMIT - cur - 1 };
}

function fetchWithTimeout(url, options, timeoutMs) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  return fetch(url, { ...options, signal: controller.signal }).finally(() => clearTimeout(timer));
}

// 두 모델 모두 "텍스트만 그대로 뽑아달라"는 요청에 가끔 서식 마크업을 섞어 낸다.
// - glm-ocr(구 기본 모델): 표·동그라미 숫자·굵은 글씨가 많은 문서에서 실제로 없는 LaTeX
//   문법(\textcircled{1}, \textbf{...}, $...$ 등)을 지어냄(해상도를 올려도 동일 — 실측으로
//   해상도가 원인이 아님을 확인).
// - olmOCR-2(현재 모델): 프롬프트로 "HTML/Markdown 표 금지"를 지시해도 빈 셀이 많은 표에서
//   가끔 <table><tr><td> 마크업을 섞어 냄(실측 확인). 표 자체 인식은 정확하므로 태그만 걷어내고
//   내용은 살린다.
// 두 경우 다 모델 출력은 그대로 두고 후처리로 마크업만 걷어내는 편이 안전하다(모델에게
// "이렇게 하지 마"를 프롬프트로 지시해도 100% 지켜지지 않는 것도 실측으로 확인됨).
function stripMarkupArtifacts(t) {
  let s = t;
  s = s.replace(/\\textcircled\{([^{}]*)\}/g, "($1)");
  for (let i = 0; i < 2; i++) {
    s = s.replace(/\\(?:textbf|textit|texttt|textsc|mathrm|mathbf|text)\s*\{([^{}]*)\}/g, "$1");
  }
  s = s.replace(/\\[a-zA-Z]+/g, ""); // 남은 영문 LaTeX 명령어
  s = s.replace(/\\+/g, ""); // 명령어로 인식 안 된 잔여 백슬래시(한글 등에 바로 붙은 경우)
  s = s.replace(/\$/g, "");
  s = s.replace(/[{}]/g, "");
  s = s.replace(/<\/?(?:table|thead|tbody)>/gi, "");
  s = s.replace(/<\/tr>/gi, "\n");
  s = s.replace(/<tr>/gi, "");
  s = s.replace(/<\/?(?:td|th)>/gi, "\t");
  s = s.replace(/<br\s*\/?>/gi, "\n");
  s = s.replace(/[ \t]{2,}/g, " ");
  s = s.replace(/\n{3,}/g, "\n\n");
  return s.trim();
}

// 모델이 헷갈리면 텍스트를 무한 반복하는 증상의 안전장치.
// repeat_penalty를 걸어도 완전히 똑같은 문자열이 아니라 한자·영단어가 살짝 섞여 변주되며
// 반복되는 경우가 실측으로 확인됨(예: "매일샴페인 / 컵/CSO)" → "...龙 instyle" → "...科使제" 식으로
// 매번 조금씩 달라짐) — 그래서 정확 문자열 반복 탐지로는 못 잡는다. 대신 "줄 시작 부분이
// 최근 몇 줄 안에서 이미 나왔으면 그 줄부터 잘라낸다"는 느슨한 기준으로 판단한다.
function truncateRunawayRepetition(text) {
  // PREFIX_LEN을 짧게 잡으면 "(1)", "①" 같은 번호 매김이 서로 다른 섹션에서 우연히
  // 겹치는 것까지 반복으로 오판한다(실측으로 확인 — "1. 제원" 절이 번호를 ①부터 다시
  // 시작하는 문서에서 오탐 발생). 접두어를 충분히 길게 잡고, 2번이 아니라 "3번째 등장"에서만
  // 자르도록 해서 진짜 폭주(수십~수백 회 반복)만 잡고 우연의 일치는 통과시킨다.
  const lines = text.split("\n");
  const WINDOW = 6;
  const PREFIX_LEN = 16;
  const REPEAT_THRESHOLD = 3;
  const counts = new Map();
  const order = [];
  for (let i = 0; i < lines.length; i++) {
    const prefix = lines[i].trim().slice(0, PREFIX_LEN);
    if (prefix.length >= PREFIX_LEN) {
      const next = (counts.get(prefix) || 0) + 1;
      counts.set(prefix, next);
      if (next >= REPEAT_THRESHOLD) {
        return lines.slice(0, i).join("\n").trim();
      }
      order.push(prefix);
      if (order.length > WINDOW) {
        const dropped = order.shift();
        counts.set(dropped, (counts.get(dropped) || 1) - 1);
      }
    }
  }
  // 줄바꿈 없이 한 줄 안에서 반복되는 경우(완전 동일 문자열 폭주)도 방어.
  // 반복 단위 1글자·4회 기준은 "A04-1-00005-0004-1207" 같은 정상 문서번호 속 "0000"까지
  // 오탐하는 게 실측으로 확인되어, 단위 최소 3글자·6회 이상으로 훨씬 보수적으로 잡는다
  // (줄 단위 반복은 위 로직이 이미 담당하므로 이건 어디까지나 마지막 보루).
  const exact = text.match(/(.{3,20}?)\1{5,}/su);
  if (exact && typeof exact.index === "number") {
    return text.slice(0, exact.index).trim();
  }
  return text;
}

async function callOllamaGenerate(env, imageBase64, options) {
  const r = await fetchWithTimeout(
    `${env.PC_AI_URL}/api/generate`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "CF-Access-Client-Id": env.CF_ACCESS_CLIENT_ID,
        "CF-Access-Client-Secret": env.CF_ACCESS_CLIENT_SECRET,
      },
      body: JSON.stringify({
        model: OCR_MODEL,
        prompt: OCR_PROMPT,
        images: [imageBase64],
        stream: false,
        options,
      }),
    },
    OCR_TIMEOUT_MS
  );
  if (!r.ok) {
    const detail = await r.text().catch(() => "");
    console.error(`ocr failed: status=${r.status} body=${detail.slice(0, 500)}`);
    throw new Error(`ocr failed: ${r.status}`);
  }
  const data = await r.json();
  return (data.response || "").trim();
}

// num_ctx: 기본값 4096은 클라이언트가 축소 전송해도(1800px) 여유가 빠듯해 실측으로 문제가
// 재현됨(비전 토큰이 예산을 넘기면 응답이 몇 글자만에 끊김) — 6144로 여유 확보.
const BASE_OPTIONS = { temperature: 0, num_predict: 3000, num_ctx: 6144 };
// repeat_penalty는 상시로 걸지 않는다 — 실측으로 확인: 정상 문서(표에 "종합검사"·동그라미
// 번호 등 정당한 반복이 있는 문서)에서 repeat_penalty를 걸면 그 정상 반복까지 억제되어
// 오히려 정확도가 크게 나빠짐(문자 오류율 0.19 → 1.08까지 악화된 사례 확인). 그래서 1차
// 호출은 penalty 없이 시도하고, 후처리로 실제 반복 폭주가 감지된 경우에만 penalty를 걸어
// 같은 이미지를 한 번 더 호출한다(흔치 않은 실패 케이스에서만 추가 지연 발생).
const REPEAT_RETRY_OPTIONS = { ...BASE_OPTIONS, repeat_penalty: 1.3, repeat_last_n: 256 };

// 반복 폭주가 감지됐다는 것은 원본 이미지 자체가 모델이 다루기 어려운 상태였다는
// 신뢰할 만한 신호다(실측: 심하게 흐릿한 사진·구겨진 영수증에서 반복적으로 재현됨).
// 기하 왜곡 보정(UVDoc 등 최신 document dewarping 모델)을 별도 PC 서비스로 도입하는
// 방안도 검토했으나, 합성 왜곡·그림자로 통제 실험을 해본 결과 olmOCR-2는 이미 이런
// 왜곡에 상당히 강건해서 사전 보정이 오히려 정확도를 깎는 경우도 있었다(실측: CER
// 0.246→0.281 악화) — 그래서 별도 전처리 인프라 대신, 폭주가 감지되면 결과와 함께
// "낮은 신뢰도" 신호만 반환해 클라이언트가 사용자에게 재촬영을 안내하도록 한다.
async function runOcr(env, imageBase64) {
  const first = await callOllamaGenerate(env, imageBase64, BASE_OPTIONS);
  // 순서 중요: 마크업 제거를 먼저 해야 한다 — 서로 다른 줄이 마크업 때문에 앞부분이 우연히
  // 같아지는 경우, 반복 감지가 먼저 돌면 정상 내용을 반복으로 오판해 잘라버릴 수 있다.
  const firstCleaned = stripMarkupArtifacts(first);
  const firstFinal = truncateRunawayRepetition(firstCleaned);
  if (firstFinal.length === firstCleaned.length) {
    return { text: firstFinal, lowConfidence: false }; // 반복 폭주 없음 — 재시도 없이 그대로 반환
  }
  // 반복이 감지된 경우에만 repeat_penalty를 걸어 재시도 — 원본이 폭주로 잘려나간 결과보다
  // 길고(더 많은 내용을 건졌고) 반복도 없다면 재시도 결과를 채택한다. 재시도로 살아나든
  // 못 살아나든, 1차 시도에서 폭주가 있었다는 사실 자체가 "낮은 신뢰도" 신호이므로 유지한다.
  try {
    const retry = await callOllamaGenerate(env, imageBase64, REPEAT_RETRY_OPTIONS);
    const retryCleaned = stripMarkupArtifacts(retry);
    const retryFinal = truncateRunawayRepetition(retryCleaned);
    if (retryFinal.length > firstFinal.length) return { text: retryFinal, lowConfidence: true };
  } catch (e) {
    console.error(`ocr retry failed: ${e}`);
  }
  return { text: firstFinal, lowConfidence: true };
}

export default {
  async fetch(request, env) {
    const origin = request.headers.get("Origin") || "";
    const url = new URL(request.url);

    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: corsHeaders(origin) });
    }
    if (request.method !== "POST" || url.pathname !== "/ocr") {
      return json({ error: "not_found" }, 404, origin);
    }

    let body;
    try {
      body = await request.json();
    } catch {
      return json({ error: "invalid_json" }, 400, origin);
    }

    const { access_token, image_base64 } = body || {};
    if (!access_token || typeof access_token !== "string") {
      return json({ error: "unauthenticated" }, 401, origin);
    }
    if (!image_base64 || typeof image_base64 !== "string") {
      return json({ error: "no_image" }, 400, origin);
    }
    if (image_base64.length > MAX_IMAGE_B64_CHARS) {
      return json({ error: "image_too_large" }, 400, origin);
    }

    const user = await verifyUser(access_token);
    if (!user) return json({ error: "invalid_session" }, 401, origin);

    const admin = await isAdmin(access_token, user.id);
    let rate = { ok: true, remaining: null, unlimited: true };
    if (!admin) {
      rate = await checkAndBumpRateLimit(env, user.id);
      if (!rate.ok) return json({ error: "rate_limited", limit: DAILY_LIMIT }, 429, origin);
    }

    if (!env.PC_AI_URL || !env.CF_ACCESS_CLIENT_ID || !env.CF_ACCESS_CLIENT_SECRET) {
      return json({ error: "server_misconfigured" }, 500, origin);
    }

    let result;
    try {
      result = await runOcr(env, image_base64);
    } catch (e) {
      return json({ error: "pc_offline", detail: String(e) }, 503, origin);
    }

    return json(
      {
        ok: true,
        text: result.text,
        low_confidence: result.lowConfidence,
        remaining_today: rate.remaining,
        unlimited: !!rate.unlimited,
      },
      200,
      origin
    );
  },
};
