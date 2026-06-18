/**
 * Cloudflare Worker — 메일 발송 (Resend) + 수신거부 관리 + Supabase 발송 이력
 *
 * 배포: wrangler deploy --config wrangler-mail.toml
 *
 * API:
 *   GET  /            → 이번 달 발송 현황  { sent, limit, remaining, period }
 *   POST /            → 메일 발송 (수신거부 자동 필터 + Supabase 로그)
 *                       단건: { to, subject, html, meta? }
 *                       대량: { emails: [{to, subject, html}, ...], meta? }  최대 100건
 *                       meta: { senderEmail, senderName, flyerSrc, flyerName, env }
 *                       응답: { success, sent, filtered: [{email, reason}], totalSent, remaining }
 *   POST /unsubscribe → { email } → 수신거부 등록  { success, email }
 *
 * 시크릿 (wrangler secret put ... --config wrangler-mail.toml):
 *   RESEND_API_KEY       — Resend API 키
 *   MAIL_FROM            — 발신자 주소 (미설정 시 onboarding@resend.dev)
 *   SUPABASE_URL         — Supabase 프로젝트 URL
 *   SUPABASE_SERVICE_KEY — Supabase service_role 키 (RLS 우회)
 */

const CORS_HEADERS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type',
};

const MONTHLY_LIMIT = 3000;
const DAILY_CAMPAIGN_LIMIT = 100;

function monthKey() {
  // KST(UTC+9) 기준 월 키
  const d = new Date(Date.now() + 9 * 3600 * 1000);
  return 'sent_' + d.getUTCFullYear() + '_' + String(d.getUTCMonth() + 1).padStart(2, '0');
}

function dailyCampaignKey() {
  const d = new Date(Date.now() + 9 * 3600 * 1000);
  return 'camp_' + d.getUTCFullYear() + '_'
    + String(d.getUTCMonth() + 1).padStart(2, '0') + '_'
    + String(d.getUTCDate()).padStart(2, '0');
}

// ── Supabase REST 헬퍼 ──────────────────────────────────────────────

/**
 * Supabase REST API GET 요청
 * @returns {Promise<Array|null>} 결과 배열 또는 null (실패 시)
 */
async function sbGet(env, path) {
  if (!env.SUPABASE_URL || !env.SUPABASE_SERVICE_KEY) return null;
  try {
    const res = await fetch(env.SUPABASE_URL + '/rest/v1' + path, {
      headers: {
        'apikey':        env.SUPABASE_SERVICE_KEY,
        'Authorization': 'Bearer ' + env.SUPABASE_SERVICE_KEY,
      },
    });
    if (!res.ok) return null;
    return res.json();
  } catch { return null; }
}

/**
 * Supabase REST API POST 요청 (INSERT)
 * 실패해도 throw하지 않음 — 로그 실패가 메일 발송을 막으면 안 됨
 */
async function sbPost(env, table, rows) {
  if (!env.SUPABASE_URL || !env.SUPABASE_SERVICE_KEY) return;
  try {
    await fetch(env.SUPABASE_URL + '/rest/v1/' + table, {
      method:  'POST',
      headers: {
        'apikey':        env.SUPABASE_SERVICE_KEY,
        'Authorization': 'Bearer ' + env.SUPABASE_SERVICE_KEY,
        'Content-Type':  'application/json',
        'Prefer':        'return=minimal',
      },
      body: JSON.stringify(rows),
    });
  } catch { /* 로그 실패는 무시 */ }
}

/**
 * Supabase RPC 호출 (SECURITY DEFINER 함수용 — service_role 키 사용)
 */
async function sbRpc(env, fn, body = {}) {
  if (!env.SUPABASE_URL || !env.SUPABASE_SERVICE_KEY) return null;
  try {
    const res = await fetch(env.SUPABASE_URL + '/rest/v1/rpc/' + fn, {
      method: 'POST',
      headers: {
        'apikey':        env.SUPABASE_SERVICE_KEY,
        'Authorization': 'Bearer ' + env.SUPABASE_SERVICE_KEY,
        'Content-Type':  'application/json',
      },
      body: JSON.stringify(body),
    });
    if (!res.ok) return null;
    return res.json();
  } catch { return null; }
}

/**
 * 수신거부 이메일 목록을 Set<string>으로 반환
 * Supabase 미설정 또는 실패 시 빈 Set 반환 (발송은 계속 진행)
 */
async function getUnsubscribes(env) {
  const rows = await sbGet(env, '/email_unsubscribes?select=email');
  if (!Array.isArray(rows)) return new Set();
  return new Set(rows.map(r => r.email.toLowerCase()));
}

// ── 메인 핸들러 ────────────────────────────────────────────────────

export default {
  async fetch(request, env, ctx) {
    if (request.method === 'OPTIONS') {
      return new Response(null, { status: 204, headers: CORS_HEADERS });
    }

    const url = new URL(request.url);

    // ── GET /db-stats : DB 캠페인 통계 ──────────────────────────
    if (request.method === 'GET' && url.pathname === '/db-stats') {
      const stats = await sbRpc(env, 'get_campaign_stats');
      const todayKey = dailyCampaignKey();
      const todaySent = parseInt((await env.MAIL_USAGE.get(todayKey)) || '0');
      return json({
        ...(stats || { total: 0, active: 0, sent: 0, unsubscribed: 0, pending: 0 }),
        today_sent:      todaySent,
        today_limit:     DAILY_CAMPAIGN_LIMIT,
        today_remaining: Math.max(0, DAILY_CAMPAIGN_LIMIT - todaySent),
      });
    }

    // ── GET /db-pending : 오늘 발송 가능한 다음 배치 ────────────
    if (request.method === 'GET' && url.pathname === '/db-pending') {
      const todayKey = dailyCampaignKey();
      const todaySent = parseInt((await env.MAIL_USAGE.get(todayKey)) || '0');
      const todayRemaining = Math.max(0, DAILY_CAMPAIGN_LIMIT - todaySent);
      if (todayRemaining === 0) {
        return json({ emails: [], today_sent: todaySent, today_remaining: 0, today_limit: DAILY_CAMPAIGN_LIMIT });
      }
      const reqLimit = parseInt(url.searchParams.get('limit') || '100');
      const effectiveLimit = Math.min(reqLimit, todayRemaining);
      const emails = await sbRpc(env, 'get_campaign_pending', { p_limit: effectiveLimit });
      return json({
        emails:          emails || [],
        today_sent:      todaySent,
        today_remaining: todayRemaining,
        today_limit:     DAILY_CAMPAIGN_LIMIT,
      });
    }

    // ── GET /db-list : 전체 발송 현황 목록 ─────────────────────────
    if (request.method === 'GET' && url.pathname === '/db-list') {
      const list = await sbRpc(env, 'get_campaign_list');
      if (!list) return json({ error: 'DB 조회 실패 — Supabase RPC 오류' }, 500);
      return json(list);
    }

    // ── GET / : 발송 현황 조회 ───────────────────────────────────
    if (request.method === 'GET') {
      const key  = monthKey();
      const sent = parseInt((await env.MAIL_USAGE.get(key)) || '0');
      const d    = new Date();
      return json({
        sent,
        limit:     MONTHLY_LIMIT,
        remaining: Math.max(0, MONTHLY_LIMIT - sent),
        period:    d.getUTCFullYear() + '-' + String(d.getUTCMonth() + 1).padStart(2, '0'),
      });
    }

    if (request.method !== 'POST') {
      return json({ error: 'Method not allowed' }, 405);
    }

    let body;
    try { body = await request.json(); } catch { return json({ error: 'Invalid JSON' }, 400); }

    // ── POST /unsubscribe : 수신거부 등록 ──────────────────────────
    if (url.pathname === '/unsubscribe') {
      const email = (body.email || '').trim().toLowerCase();
      if (!email || !email.includes('@')) {
        return json({ error: '유효한 이메일 주소가 필요합니다.' }, 400);
      }
      // UPSERT: 이미 등록된 경우 무시 (UNIQUE 제약)
      await sbPost(env, 'email_unsubscribes', [{
        email,
        source: body.source || 'link',
        note:   body.note   || null,
      }]);
      return json({ success: true, email });
    }

    // ── POST /db-send : DB 캠페인 발송 (일일 한도 100건 강제) ────
    if (url.pathname === '/db-send') {
      if (!env.RESEND_API_KEY) return json({ error: 'RESEND_API_KEY not configured' }, 500);

      const todayKey       = dailyCampaignKey();
      const todaySent      = parseInt((await env.MAIL_USAGE.get(todayKey)) || '0');
      const todayRemaining = Math.max(0, DAILY_CAMPAIGN_LIMIT - todaySent);
      if (todayRemaining === 0) {
        return json({ error: `오늘 발송 한도 소진 (${todaySent}/${DAILY_CAMPAIGN_LIMIT}건) — 자정(KST) 이후 재시도` }, 429);
      }

      const dbEmails = Array.isArray(body.emails) ? body.emails : [];
      const meta     = body.meta || {};
      if (!dbEmails.length) return json({ error: 'No emails specified' }, 400);

      // 일일 한도 내로 제한
      const allowedEmails = dbEmails.slice(0, todayRemaining);

      // 수신거부 필터
      const unsubSet = await getUnsubscribes(env);
      const toSend   = allowedEmails.filter(e => !unsubSet.has((e.to || '').toLowerCase()));
      const filtered = allowedEmails
        .filter(e => unsubSet.has((e.to || '').toLowerCase()))
        .map(e => ({ email: e.to, reason: '수신거부' }));

      // 월 한도 확인
      const mKey       = monthKey();
      const monthSent  = parseInt((await env.MAIL_USAGE.get(mKey)) || '0');
      if (monthSent + toSend.length > MONTHLY_LIMIT) {
        return json({ error: `월 발송 한도 초과 (${monthSent}/${MONTHLY_LIMIT})` }, 429);
      }

      const from       = env.MAIL_FROM || 'WorksFree 컨설팅 <onboarding@resend.dev>';
      const authHeader = 'Bearer ' + env.RESEND_API_KEY;
      const sentEmails = [], failed = [];

      // Resend batch API: 단일 요청으로 최대 100건 → 초당 2건 레이트 제한 회피
      const batchBody = toSend.map(e => ({
        from, to: [e.to], subject: e.subject, html: e.html,
      }));
      try {
        const batchRes  = await fetch('https://api.resend.com/emails/batch', {
          method:  'POST',
          headers: { Authorization: authHeader, 'Content-Type': 'application/json' },
          body:    JSON.stringify(batchBody),
        });
        const batchData = await batchRes.json();
        if (!batchRes.ok) {
          const errMsg = batchData.message || 'Resend batch error';
          toSend.forEach(e => failed.push({ email: e.to, reason: errMsg }));
        } else {
          // batchData.data: [{id: "..."}, ...] 순서 대응
          const results = Array.isArray(batchData.data) ? batchData.data : [];
          toSend.forEach((e, idx) => {
            if (results[idx] && results[idx].id) {
              sentEmails.push(e);
            } else {
              failed.push({ email: e.to, reason: '발송 ID 없음 (Resend 응답 불일치)' });
            }
          });
        }
      } catch (err) {
        toSend.forEach(e => failed.push({ email: e.to, reason: err.message }));
      }

      const sentCount    = sentEmails.length;
      const newDailySent = todaySent + sentCount;

      if (sentCount > 0) {
        await env.MAIL_USAGE.put(mKey,      String(monthSent + sentCount));
        await env.MAIL_USAGE.put(todayKey,  String(newDailySent));
      }

      // email_log 기록
      const now     = new Date().toISOString();
      const logRows = sentEmails.map(e => ({
        sent_at:         now,
        recipient_email: e.to.toLowerCase(),
        sender_email:    (meta.senderEmail || '').toLowerCase() || null,
        sender_name:     meta.senderName   || null,
        sender_user_id:  meta.senderUserId || null,
        flyer_src:       meta.flyerSrc     || null,
        flyer_name:      meta.flyerName    || null,
        subject:         e.subject         || null,
        env:             meta.env          || 'portal',
        status:          'sent',
      }));
      if (logRows.length > 0) ctx.waitUntil(sbPost(env, 'email_log', logRows));

      return json({
        success:         true,
        sent:            sentCount,
        filtered,
        failed,
        today_sent:      newDailySent,
        today_remaining: Math.max(0, DAILY_CAMPAIGN_LIMIT - newDailySent),
        today_limit:     DAILY_CAMPAIGN_LIMIT,
      });
    }

    // ── POST / : 메일 발송 ───────────────────────────────────────
    if (!env.RESEND_API_KEY) {
      return json({ error: 'RESEND_API_KEY not configured' }, 500);
    }

    const from   = env.MAIL_FROM || 'WorksFree 컨설팅 <onboarding@resend.dev>';
    const emails = Array.isArray(body.emails) ? body.emails : [body];
    const meta   = body.meta || {};

    if (!emails.length) return json({ error: 'No emails specified' }, 400);

    for (const e of emails) {
      if (!e.to || !e.subject || !e.html) {
        return json({ error: 'Each email needs to, subject, html' }, 400);
      }
    }

    // ── 수신거부 필터 ──────────────────────────────────────────────
    const unsubSet = await getUnsubscribes(env);
    const filtered  = [];
    const toSend    = [];

    for (const e of emails) {
      if (unsubSet.has(e.to.toLowerCase())) {
        filtered.push({ email: e.to, reason: '수신거부' });
      } else {
        toSend.push(e);
      }
    }

    // 모두 필터링된 경우 — 발송 없이 바로 반환
    if (toSend.length === 0) {
      const key     = monthKey();
      const curSent = parseInt((await env.MAIL_USAGE.get(key)) || '0');
      return json({
        success: true, sent: 0, filtered,
        totalSent: curSent, remaining: Math.max(0, MONTHLY_LIMIT - curSent),
      });
    }

    // 월 한도 사전 확인
    const key         = monthKey();
    const currentSent = parseInt((await env.MAIL_USAGE.get(key)) || '0');
    if (currentSent + toSend.length > MONTHLY_LIMIT) {
      return json({
        error: `월 발송 한도 초과 — 이번 달 ${currentSent}/${MONTHLY_LIMIT}건 사용됨`,
      }, 429);
    }

    // ── Resend API 호출 (100건씩 청크 — Resend batch 단건 제한) ──────
    const auth      = 'Bearer ' + env.RESEND_API_KEY;
    const CHUNK     = 100;
    const sentEmails = [];
    const failed = [];
    const sendErrors = [];

    async function sendOne(e) {
      const res = await fetch('https://api.resend.com/emails', {
        method:  'POST',
        headers: { Authorization: auth, 'Content-Type': 'application/json' },
        body:    JSON.stringify({ from, to: [e.to], subject: e.subject, html: e.html }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.message || 'Resend API error');
      return data;
    }

    for (let i = 0; i < toSend.length; i += CHUNK) {
      const chunk = toSend.slice(i, i + CHUNK);
      let resendRes;

      if (chunk.length === 1) {
        try {
          await sendOne(chunk[0]);
          sentEmails.push(chunk[0]);
        } catch (err) {
          const msg = err.message || 'Resend API error';
          failed.push({ email: chunk[0].to, reason: msg });
          sendErrors.push(msg);
        }
        continue;
      } else {
        resendRes = await fetch('https://api.resend.com/emails/batch', {
          method:  'POST',
          headers: { Authorization: auth, 'Content-Type': 'application/json' },
          body:    JSON.stringify(chunk.map(e => ({ from, to: [e.to], subject: e.subject, html: e.html }))),
        });
      }

      const resendData = await resendRes.json();
      if (!resendRes.ok) {
        const chunkMsg = resendData.message || 'Resend API error';
        const errorMsg = `${i + 1}-${i + chunk.length}번째 묶음 실패: ${chunkMsg}. (묶음 내 잘못된 이메일 주소가 있는지 확인하세요.)`;
        sendErrors.push(errorMsg);
        // 개별 재시도 로직 제거 - 전체 묶음을 실패 처리하고 다음 묶음으로 이동
        chunk.forEach(e => failed.push({ email: e.to, reason: `${chunkMsg}일괄 발송 실패` }));
        // // Batch는 한 주소 오류로 전체 묶음이 실패할 수 있어, 실패 묶음만 개별 재시도한다.
        // for (const e of chunk) {
        //   try {
        //     await sendOne(e);
        //     sentEmails.push(e);
        //   } catch (err) {
        //     const msg = err.message || chunkMsg;
        //     failed.push({ email: e.to, reason: msg });
        //   }
        // }
        continue;
      }
      sentEmails.push(...chunk);
    }

    const sentCount = sentEmails.length;
    if (sentCount === 0 && (sendErrors.length > 0 || failed.length > 0)) {
      return json({ error: sendErrors[0] }, 400);
    }

    // 발송 성공 → KV 카운터 업데이트 (실제 발송된 건수만)
    const newTotal = currentSent + sentCount;
    await env.MAIL_USAGE.put(key, String(newTotal));

    // ── Supabase 발송 이력 기록 (비동기 — 실패해도 응답 차단 없음) ──
    const now      = new Date().toISOString();
    const senderEmail  = (meta.senderEmail || '').toLowerCase() || null;
    const senderName   = meta.senderName   || null;
    const flyerSrc     = meta.flyerSrc     || null;
    const flyerName    = meta.flyerName    || null;
    const envTag       = meta.env          || 'portal';
    const senderUserId = meta.senderUserId || null;

    // 발송 성공 로그 (실제 발송된 건만)
    const logRows = sentEmails.map(e => ({
      sent_at:          now,
      recipient_email:  e.to.toLowerCase(),
      sender_email:     senderEmail,
      sender_name:      senderName,
      sender_user_id:   senderUserId,
      flyer_src:        flyerSrc,
      flyer_name:       flyerName,
      subject:          e.subject || null,
      env:              envTag,
      status:           'sent',
    }));

    // 필터링(수신거부) 이력도 함께 기록
    const filterRows = filtered.map(f => ({
      sent_at:          now,
      recipient_email:  f.email.toLowerCase(),
      sender_email:     senderEmail,
      sender_name:      senderName,
      sender_user_id:   senderUserId,
      flyer_src:        flyerSrc,
      flyer_name:       flyerName,
      subject:          null,
      env:              envTag,
      status:           'filtered',
    }));

    const allRows = [...logRows, ...filterRows];
    // ctx.waitUntil: Worker 응답 반환 후에도 fetch가 완료될 때까지 실행 컨텍스트 유지
    if (allRows.length > 0) ctx.waitUntil(sbPost(env, 'email_log', allRows));

    return json({
      success:   true,
      sent:      sentCount,
      filtered,
      failed,
      totalSent: newTotal,
      remaining: Math.max(0, MONTHLY_LIMIT - newTotal),
      ...(sendErrors.length > 0 || failed.length > 0 ? { partial_error: sendErrors[0] || failed[0].reason } : {}),
    });
  },
};

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { ...CORS_HEADERS, 'Content-Type': 'application/json' },
  });
}
