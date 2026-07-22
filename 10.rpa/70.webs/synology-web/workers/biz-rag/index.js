/**
 * biz-rag — "🤖 AI 상담사" 노드용 Cloudflare Worker (RAG 챗봇 게이트웨이).
 *
 * 흐름:
 *   1) 클라이언트가 보낸 Supabase access_token으로 로그인 사용자를 검증한다
 *      (biz-report와 동일 패턴 — 클라이언트가 보낸 user_id는 신뢰하지 않음).
 *   2) KV로 사용자당 일일 호출 횟수를 제한한다(무료 기능이므로 크레딧 차감 대신 사용량 제한).
 *   3) Supabase(ai_helper_messages)에서 최근 대화(최근 CONTEXT_TURNS턴)를 불러온다 —
 *      멀티턴 문맥은 여기서만 쓰이고, 전체 보관 이력과는 별개(보관 상한은 RPC가 처리).
 *   4) PC의 Ollama(Cloudflare Tunnel + Access로 보호됨)에 질문 임베딩을 요청한다.
 *   5) Cloudflare Vectorize(RAG_VECTORIZE 바인딩)에 그 임베딩으로 top-k 유사 청크를 질의한다.
 *      — 인덱스를 통째로 fetch+parse하던 이전 방식(정적 rag_index.json)은 청크 수가
 *        수천 건으로 늘면서(45.Slife 포함 후 6,305개, 80MB) Worker 메모리 한도(128MB)에
 *        위험할 정도로 근접해 Vectorize로 전환했다.
 *   6) PC의 Ollama에 (이전 대화 + 컨텍스트 + 질문) 메시지로 답변 생성을 요청한다.
 *      body.stream===true 면 NDJSON으로 실시간 스트리밍, 아니면 완성된 답변을 한 번에 반환.
 *   7) 생성된 질문·답변을 Supabase에 저장하고 보관 상한을 정리한다(prune RPC) — 응답을
 *      막지 않도록 ctx.waitUntil로 백그라운드 처리.
 *   8) PC가 꺼져 있으면(터널 연결 실패/타임아웃) 명확한 에러 코드를 반환한다.
 *
 * 사전 준비:
 *   - Supabase: 10.rpa/70.webs/supabase/core/ai_helper_setup.sql 를 SQL Editor에서 1회 실행
 *   - Vectorize: npx wrangler vectorize create biz-rag-index --dimensions=1024 --metric=cosine
 *                npx wrangler vectorize insert biz-rag-index --file=../../../site-rag/vectors.ndjson
 *
 * 시크릿(전부 `wrangler secret put`으로만 설정, 평문 기재 금지):
 *   CF_ACCESS_CLIENT_ID / CF_ACCESS_CLIENT_SECRET — PC 터널의 Cloudflare Access Service Token
 *   PC_AI_URL          — 예: https://pc-ai.worksfree.kr
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

const DAILY_LIMIT = 20; // 관리자(profiles.role)는 무제한 — isAdmin() 참고
const TOP_K = 5;
const CONTEXT_TURNS = 3; // 최근 3턴(6개 메시지)만 생성 프롬프트에 포함 — 보관 상한과는 별개
const EMBED_MODEL = "bge-m3";
const CHAT_MODEL = "gemma4:12b";
const EMBED_TIMEOUT_MS = 8000;
const CHAT_TIMEOUT_MS = 20000;
const CHAT_STREAM_TIMEOUT_MS = 45000; // 스트리밍은 첫 바이트 이후 트리클되므로 여유를 더 둠
const MAX_QUESTION_LEN = 500;

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
// 직접 조회해 신뢰한다(클라이언트가 role을 보내는 방식은 위조 가능해 금지 패턴). ocr-service와
// 동일 패턴.
async function isAdmin(accessToken, userId) {
  const r = await fetch(`${SUPABASE_URL}/rest/v1/profiles?id=eq.${userId}&select=role`, {
    headers: { Authorization: `Bearer ${accessToken}`, apikey: SUPABASE_ANON },
  });
  if (!r.ok) return false;
  const rows = await r.json().catch(() => []);
  return rows?.[0]?.role === "admin";
}

async function checkAndBumpRateLimit(env, userId) {
  const today = new Date().toISOString().slice(0, 10); // YYYY-MM-DD (UTC)
  const key = `${today}:${userId}`;
  const cur = parseInt((await env.RAG_RATE_LIMIT.get(key)) || "0", 10);
  if (cur >= DAILY_LIMIT) return { ok: false };
  await env.RAG_RATE_LIMIT.put(key, String(cur + 1), { expirationTtl: 90000 }); // ~25h
  return { ok: true, remaining: DAILY_LIMIT - cur - 1 };
}

// ── 대화 기록 (Supabase) ──
// 전부 호출자의 access_token으로 호출 — RLS가 본인 행으로 자동 스코핑한다.

async function fetchHistory(accessToken, userId) {
  const url =
    `${SUPABASE_URL}/rest/v1/ai_helper_messages` +
    `?user_id=eq.${userId}&select=role,content&order=created_at.desc&limit=${CONTEXT_TURNS * 2}`;
  const r = await fetch(url, { headers: { Authorization: `Bearer ${accessToken}`, apikey: SUPABASE_ANON } });
  if (!r.ok) return [];
  const rows = await r.json();
  return rows.reverse().map((row) => ({ role: row.role, content: row.content }));
}

async function saveTurn(accessToken, userId, question, answer, sources) {
  const rows = [
    { user_id: userId, role: "user", content: question },
    { user_id: userId, role: "assistant", content: answer, sources },
  ];
  await fetch(`${SUPABASE_URL}/rest/v1/ai_helper_messages`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${accessToken}`,
      apikey: SUPABASE_ANON,
      "Content-Type": "application/json",
      Prefer: "return=minimal",
    },
    body: JSON.stringify(rows),
  });
}

async function pruneHistory(accessToken) {
  await fetch(`${SUPABASE_URL}/rest/v1/rpc/prune_ai_helper_messages`, {
    method: "POST",
    headers: { Authorization: `Bearer ${accessToken}`, apikey: SUPABASE_ANON, "Content-Type": "application/json" },
    body: "{}",
  });
}

function fetchWithTimeout(url, options, timeoutMs) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  return fetch(url, { ...options, signal: controller.signal }).finally(() => clearTimeout(timer));
}

function pcAccessHeaders(env) {
  return {
    "Content-Type": "application/json",
    "CF-Access-Client-Id": env.CF_ACCESS_CLIENT_ID,
    "CF-Access-Client-Secret": env.CF_ACCESS_CLIENT_SECRET,
  };
}

async function embedQuestion(env, question) {
  const r = await fetchWithTimeout(
    `${env.PC_AI_URL}/api/embeddings`,
    { method: "POST", headers: pcAccessHeaders(env), body: JSON.stringify({ model: EMBED_MODEL, prompt: question }) },
    EMBED_TIMEOUT_MS
  );
  if (!r.ok) throw new Error(`embed failed: ${r.status}`);
  const data = await r.json();
  return data.embedding;
}

async function queryChunks(env, queryEmbedding, k) {
  const result = await env.RAG_VECTORIZE.query(queryEmbedding, { topK: k, returnMetadata: "all" });
  return (result.matches || []).map((m) => ({
    title: m.metadata?.title || "",
    source: m.metadata?.source || "",
    text: m.metadata?.text || "",
  }));
}

function buildMessages(history, chunks, question) {
  const context = chunks.map((c, i) => `[${i + 1}] ${c.title}\n${c.text}`).join("\n\n---\n\n");
  const finalUser = `다음은 참고 문서 발췌입니다. 이 내용만을 근거로 질문에 한국어로 답하세요.
문서에 없는 내용은 지어내지 말고 "제공된 자료에서 확인할 수 없습니다"라고 답하세요.
이전 대화가 있다면 자연스럽게 이어서 답하세요.

[참고 문서]
${context}

[질문]
${question}

[답변 지침]
- 3~6문장, 사실 기반, 과장 없이
- 가능하면 어느 문서 번호([1], [2] 등)를 근거로 했는지 언급`;
  return [...history, { role: "user", content: finalUser }];
}

async function generateAnswer(env, messages) {
  const r = await fetchWithTimeout(
    `${env.PC_AI_URL}/api/chat`,
    { method: "POST", headers: pcAccessHeaders(env), body: JSON.stringify({ model: CHAT_MODEL, messages, stream: false }) },
    CHAT_TIMEOUT_MS
  );
  if (!r.ok) throw new Error(`chat failed: ${r.status}`);
  const data = await r.json();
  return data.message?.content?.trim() || "";
}

async function openAnswerStream(env, messages) {
  const r = await fetchWithTimeout(
    `${env.PC_AI_URL}/api/chat`,
    { method: "POST", headers: pcAccessHeaders(env), body: JSON.stringify({ model: CHAT_MODEL, messages, stream: true }) },
    CHAT_STREAM_TIMEOUT_MS
  );
  if (!r.ok || !r.body) throw new Error(`chat stream failed: ${r.status}`);
  return r.body;
}

// Ollama의 NDJSON 스트림(각 줄 {message:{content},done}) 을 우리 프로토콜
// ({"type":"chunk","text":...} / {"type":"done",...} / {"type":"error",...}) 로 변환해 흘려보낸다.
// 완료 후 전체 텍스트를 Supabase에 저장 — 응답 스트림을 막지 않도록 이 함수 자체가 ctx.waitUntil 대상.
async function pumpStream(ollamaStream, writer, ctx2) {
  const { sourcesPayload, accessToken, userId, question, encoder, decoder } = ctx2;
  const reader = ollamaStream.getReader();
  let buffer = "";
  let fullText = "";
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      let idx;
      while ((idx = buffer.indexOf("\n")) >= 0) {
        const line = buffer.slice(0, idx).trim();
        buffer = buffer.slice(idx + 1);
        if (!line) continue;
        let obj;
        try {
          obj = JSON.parse(line);
        } catch {
          continue;
        }
        const delta = obj.message?.content || "";
        if (delta) {
          fullText += delta;
          await writer.write(encoder.encode(JSON.stringify({ type: "chunk", text: delta }) + "\n"));
        }
        if (obj.done) {
          await writer.write(
            encoder.encode(JSON.stringify({ type: "done", ...sourcesPayload }) + "\n")
          );
        }
      }
    }
  } catch (e) {
    try {
      await writer.write(encoder.encode(JSON.stringify({ type: "error", error: "pc_offline" }) + "\n"));
    } catch {}
  } finally {
    try {
      await writer.close();
    } catch {}
    if (fullText.trim()) {
      try {
        await saveTurn(accessToken, userId, question, fullText.trim(), sourcesPayload.sources);
        await pruneHistory(accessToken);
      } catch {}
    }
  }
}

export default {
  async fetch(request, env, ctx) {
    const origin = request.headers.get("Origin") || "";
    const url = new URL(request.url);

    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: corsHeaders(origin) });
    }
    if (request.method !== "POST" || url.pathname !== "/chat") {
      return json({ error: "not_found" }, 404, origin);
    }

    let body;
    try {
      body = await request.json();
    } catch {
      return json({ error: "invalid_json" }, 400, origin);
    }

    const { access_token, question, stream } = body || {};
    if (!access_token || typeof access_token !== "string") {
      return json({ error: "unauthenticated" }, 401, origin);
    }
    if (!question || typeof question !== "string" || !question.trim()) {
      return json({ error: "no_question" }, 400, origin);
    }
    if (question.length > MAX_QUESTION_LEN) {
      return json({ error: "question_too_long", max: MAX_QUESTION_LEN }, 400, origin);
    }

    // 1) 세션 검증
    const user = await verifyUser(access_token);
    if (!user) return json({ error: "invalid_session" }, 401, origin);

    // 2) 일일 사용량 제한 (관리자는 무제한)
    const admin = await isAdmin(access_token, user.id);
    let rate = { ok: true, remaining: null, unlimited: true };
    if (!admin) {
      rate = await checkAndBumpRateLimit(env, user.id);
      if (!rate.ok) return json({ error: "rate_limited", limit: DAILY_LIMIT }, 429, origin);
    }

    if (!env.PC_AI_URL || !env.CF_ACCESS_CLIENT_ID || !env.CF_ACCESS_CLIENT_SECRET || !env.RAG_VECTORIZE) {
      return json({ error: "server_misconfigured" }, 500, origin);
    }

    // 3) 최근 대화 불러오기 (Supabase, 실패해도 빈 배열로 계속 진행)
    const history = await fetchHistory(access_token, user.id).catch(() => []);

    // 4) 질문 임베딩 (PC), 5) Vectorize 검색 (Cloudflare) — PC가 꺼져 있으면 여기서 실패
    let chunks, messages;
    try {
      const queryEmbedding = await embedQuestion(env, question);
      chunks = await queryChunks(env, queryEmbedding, TOP_K);
      messages = buildMessages(history, chunks, question);
    } catch (e) {
      console.error(`pc_offline path failed: ${e && e.stack ? e.stack : e}`);
      return json({ error: "pc_offline", detail: String(e) }, 503, origin);
    }
    if (!chunks.length) {
      return json({ error: "index_empty" }, 500, origin);
    }

    const sourcesPayload = {
      sources: chunks.map((c) => ({ title: c.title, source: c.source })),
      remaining_today: rate.remaining,
      unlimited: !!rate.unlimited,
    };

    // 6) 생성 — stream 여부에 따라 분기
    if (stream === true) {
      let ollamaStream;
      try {
        ollamaStream = await openAnswerStream(env, messages);
      } catch (e) {
        return json({ error: "pc_offline", detail: String(e) }, 503, origin);
      }
      const { readable, writable } = new TransformStream();
      const writer = writable.getWriter();
      ctx.waitUntil(
        pumpStream(ollamaStream, writer, {
          sourcesPayload,
          accessToken: access_token,
          userId: user.id,
          question,
          encoder: new TextEncoder(),
          decoder: new TextDecoder(),
        })
      );
      return new Response(readable, {
        status: 200,
        headers: { "content-type": "application/x-ndjson; charset=utf-8", ...corsHeaders(origin) },
      });
    }

    // 7) 비스트리밍 — PC가 꺼져 있으면 여기서 실패
    let answer;
    try {
      answer = await generateAnswer(env, messages);
    } catch (e) {
      return json({ error: "pc_offline", detail: String(e) }, 503, origin);
    }

    ctx.waitUntil(
      saveTurn(access_token, user.id, question, answer, sourcesPayload.sources)
        .then(() => pruneHistory(access_token))
        .catch(() => {})
    );

    return json({ ok: true, answer, ...sourcesPayload }, 200, origin);
  },
};
