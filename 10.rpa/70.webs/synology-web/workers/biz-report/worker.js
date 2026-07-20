/**
 * biz-report — 지원제도 내비게이터 "AI 종합 분석" 유료 기능용 Cloudflare Worker.
 *
 * 흐름:
 *   1) 클라이언트가 보낸 Supabase access_token 으로 실제 로그인 사용자를 검증한다
 *      (클라이언트가 임의로 보낸 user_id 를 신뢰하지 않는다 — 토큰으로 직접 재조회).
 *   2) 검증된 user_id 로 deduct_credits RPC 를 호출해 크레딧 1개를 차감한다.
 *      잔액 부족 시 402 를 반환하고 여기서 종료 — Claude API 는 호출되지 않는다.
 *   3) Claude API 로 선택된 카드들을 종합한 분석 텍스트를 생성해 반환한다.
 *
 * ANTHROPIC_API_KEY 는 Worker 시크릿으로만 주입한다:
 *   npx wrangler secret put ANTHROPIC_API_KEY
 */

const SUPABASE_URL = "https://rkycwfpkzorfpcxfvaqt.supabase.co";
// 허브 index.html 에 이미 공개되어 있는 anon key 그대로 사용 (client-safe key)
const SUPABASE_ANON =
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJreWN3ZnBrem9yZnBjeGZ2YXF0Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzgzMDk4OTQsImV4cCI6MjA5Mzg4NTg5NH0.u1HC0KiArbdqFAPpkRWsfZmMYqfZ-euRTHeNtUr2NBs";

const ALLOWED_ORIGINS = new Set([
  "https://test.worksfree.kr",
  "https://staging.worksfree.kr",
  "https://www.worksfree.kr",
  "https://portal.worksfree.kr",
]);

const APP_ID = "biz-support-ai-report";
const CREDIT_COST = 1;
const MAX_CARDS = 10;

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

async function deductCredit(accessToken, userId, note) {
  const r = await fetch(`${SUPABASE_URL}/rest/v1/rpc/deduct_credits`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${accessToken}`,
      apikey: SUPABASE_ANON,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ p_user_id: userId, p_amount: CREDIT_COST, p_app_id: APP_ID, p_note: note }),
  });
  if (r.ok) return { ok: true };
  const text = await r.text();
  if (text.includes("insufficient_credits")) return { ok: false, reason: "insufficient_credits" };
  return { ok: false, reason: "rpc_error", detail: text };
}

function buildPrompt(cards, question) {
  const lines = cards
    .map(
      (c) =>
        `- ${c.name} (${c.category})\n  대상: ${c.target}\n  혜택: ${c.benefit}\n  방법: ${c.how}\n  시기: ${c.when}`
    )
    .join("\n");
  const context = question ? `\n[기업 상황]\n${question}\n` : "";
  return `다음은 한 중소기업이 함께 검토 중인 지원제도 목록입니다.

${lines}
${context}
이 제도들을 함께 활용할 때의 종합 전략을 한국어로 작성하세요. 반드시 포함할 내용:
1. 이 조합이 서로 어떻게 연계되는지 (시너지가 있는 조합인지, 성격이 다른 제도들인지)
2. 동시 적용이 제한되거나 신청 순서가 중요한 제도 조합이 있다면 구체적으로 지적
3. 실행 순서 제안 (무엇을 먼저 준비·신청해야 하는지)
4. 확실하지 않은 사항은 "최신 공고 확인 필요"라고 명시

과장 없이 사실 기반으로, 4~6문장 분량으로 작성하세요.`;
}

async function callClaude(apiKey, cards, question) {
  const r = await fetch("https://api.anthropic.com/v1/messages", {
    method: "POST",
    headers: {
      "x-api-key": apiKey,
      "anthropic-version": "2023-06-01",
      "content-type": "application/json",
    },
    body: JSON.stringify({
      model: "claude-opus-4-8",
      max_tokens: 1200,
      thinking: { type: "adaptive" },
      messages: [{ role: "user", content: buildPrompt(cards, question) }],
    }),
  });
  if (!r.ok) {
    const detail = await r.text();
    return { ok: false, status: r.status, detail };
  }
  const data = await r.json();
  const text = (data.content || [])
    .filter((b) => b.type === "text")
    .map((b) => b.text)
    .join("\n")
    .trim();
  return { ok: true, text, usage: data.usage };
}

export default {
  async fetch(request, env) {
    const origin = request.headers.get("Origin") || "";

    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: corsHeaders(origin) });
    }
    if (request.method !== "POST") {
      return json({ error: "method_not_allowed" }, 405, origin);
    }

    let body;
    try {
      body = await request.json();
    } catch {
      return json({ error: "invalid_json" }, 400, origin);
    }

    const { access_token, cards, question } = body || {};
    if (!access_token || typeof access_token !== "string") {
      return json({ error: "unauthenticated" }, 401, origin);
    }
    if (!Array.isArray(cards) || cards.length === 0) {
      return json({ error: "no_cards" }, 400, origin);
    }
    if (cards.length > MAX_CARDS) {
      return json({ error: "too_many_cards", max: MAX_CARDS }, 400, origin);
    }

    // 1) 세션 검증 — 클라이언트가 보낸 user_id 는 신뢰하지 않고 토큰으로 직접 재조회
    const user = await verifyUser(access_token);
    if (!user) return json({ error: "invalid_session" }, 401, origin);

    // 2) 크레딧 차감 (부족하면 여기서 종료 — Claude 미호출)
    const deduct = await deductCredit(access_token, user.id, `AI 종합 분석 (${cards.length}건)`);
    if (!deduct.ok) {
      if (deduct.reason === "insufficient_credits") {
        return json({ error: "insufficient_credits" }, 402, origin);
      }
      return json({ error: "credit_deduct_failed", detail: deduct.detail }, 500, origin);
    }

    // 3) Claude 종합 호출
    if (!env.ANTHROPIC_API_KEY) {
      return json({ error: "server_misconfigured" }, 500, origin);
    }
    const result = await callClaude(env.ANTHROPIC_API_KEY, cards, question);
    if (!result.ok) {
      return json({ error: "anthropic_error", status: result.status, detail: result.detail }, 502, origin);
    }

    return json({ ok: true, text: result.text }, 200, origin);
  },
};
