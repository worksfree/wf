/**
 * Cloudflare Worker — 메일 발송 (Resend) + 수신거부 관리 + Supabase 발송 이력
 *                   + 이메일 캠페인 관리 (v2)
 *
 * 배포: wrangler deploy --config wrangler-mail.toml
 *
 * Fetch API:
 *   GET  /                        → 이번 달 발송 현황
 *   POST /                        → 메일 발송 (단건/대량)
 *   POST /unsubscribe             → 수신거부 등록
 *   GET  /db-stats                → DB 캠페인 통계 (레거시, biz_contacts)
 *   GET  /db-pending              → 오늘 발송 가능 배치 (레거시, biz_contacts)
 *   GET  /db-list                 → 전체 발송 현황 목록 (레거시, biz_contacts)
 *   POST /db-send                 → DB 캠페인 배치 발송 (레거시, biz_contacts)
 *
 *   GET  /gov/db-stats            → DB 캠페인 통계 (gov_contacts — 지자체·공공기관)
 *   GET  /gov/db-pending          → 오늘 발송 가능 배치 (gov_contacts)
 *   GET  /gov/db-list             → 전체 발송 현황 목록 (gov_contacts)
 *   ※ 실제 발송(POST)은 기존 /db-send를 그대로 재사용한다 — /db-send는 body로
 *     받은 {to,subject,html}만 처리하는 소스 무관 엔드포인트라 gov 이메일도
 *     그대로 통과한다. 일일/월 한도(MAIL_USAGE)도 Resend 계정 전체 기준이므로
 *     biz/gov 구분 없이 하나의 카운터를 공유한다.
 *
 * 캠페인 API:
 *   GET  /campaigns               → 캠페인 목록
 *   POST /campaigns               → 캠페인 생성 { name, subject, flyer_src, flyer_name, html_body, env }
 *   POST /campaigns/:id/activate  → 활성화 (draft → active, campaign_emails 스냅샷 생성)
 *   POST /campaigns/:id/pause     → 일시중지
 *   POST /campaigns/:id/resume    → 재개 (paused → active)
 *   POST /campaigns/:id/cancel    → 취소
 *   POST /campaigns/:id/send-now  → 즉시 1배치 발송 (manual)
 *   GET  /campaigns/:id/runs      → 실행 이력
 *
 * Cron Trigger (0 0 * * * UTC = KST 09:00):
 *   active 캠페인 모두 순회 → 일일 한도 내에서 1배치씩 자동 발송
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

const MONTHLY_LIMIT        = 3000;
const DAILY_CAMPAIGN_LIMIT = 100;

// ── 날짜 키 헬퍼 ────────────────────────────────────────────────────

function monthKey() {
  const d = new Date(Date.now() + 9 * 3600 * 1000);
  return 'sent_' + d.getUTCFullYear() + '_' + String(d.getUTCMonth() + 1).padStart(2, '0');
}

function dailyCampaignKey() {
  const d = new Date(Date.now() + 9 * 3600 * 1000);
  return 'camp_' + d.getUTCFullYear() + '_'
    + String(d.getUTCMonth() + 1).padStart(2, '0') + '_'
    + String(d.getUTCDate()).padStart(2, '0');
}

function kstDateStr() {
  const d = new Date(Date.now() + 9 * 3600 * 1000);
  return d.getUTCFullYear() + '-'
    + String(d.getUTCMonth() + 1).padStart(2, '0') + '-'
    + String(d.getUTCDate()).padStart(2, '0');
}

// ── Supabase REST 헬퍼 ──────────────────────────────────────────────

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

/** INSERT — 실패해도 throw하지 않음 (로그 실패가 발송을 막으면 안 됨) */
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

/** INSERT — 생성된 row 반환 */
async function sbInsert(env, table, row) {
  if (!env.SUPABASE_URL || !env.SUPABASE_SERVICE_KEY) return null;
  try {
    const res = await fetch(env.SUPABASE_URL + '/rest/v1/' + table, {
      method:  'POST',
      headers: {
        'apikey':        env.SUPABASE_SERVICE_KEY,
        'Authorization': 'Bearer ' + env.SUPABASE_SERVICE_KEY,
        'Content-Type':  'application/json',
        'Prefer':        'return=representation',
      },
      body: JSON.stringify(row),
    });
    if (!res.ok) return null;
    const data = await res.json();
    return Array.isArray(data) ? data[0] : data;
  } catch { return null; }
}

/** PATCH by id */
async function sbPatch(env, table, id, data) {
  if (!env.SUPABASE_URL || !env.SUPABASE_SERVICE_KEY) return;
  try {
    await fetch(env.SUPABASE_URL + '/rest/v1/' + table + '?id=eq.' + id, {
      method:  'PATCH',
      headers: {
        'apikey':        env.SUPABASE_SERVICE_KEY,
        'Authorization': 'Bearer ' + env.SUPABASE_SERVICE_KEY,
        'Content-Type':  'application/json',
        'Prefer':        'return=minimal',
      },
      body: JSON.stringify(data),
    });
  } catch { }
}

/** RPC 호출 */
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

async function getUnsubscribes(env) {
  const rows = await sbGet(env, '/email_unsubscribes?select=email');
  if (!Array.isArray(rows)) return new Set();
  return new Set(rows.map(r => r.email.toLowerCase()));
}

// ── 캠페인 배치 발송 ────────────────────────────────────────────────

/**
 * 단일 캠페인의 오늘 배치를 발송하고 DB를 갱신한다.
 * @returns { sent, failed, remaining_pending, completed, today_remaining }
 */
async function runCampaignBatch(campaignId, env, triggeredBy = 'manual') {
  const todayKey       = dailyCampaignKey();
  const todaySent      = parseInt((await env.MAIL_USAGE.get(todayKey)) || '0');
  const todayRemaining = Math.max(0, DAILY_CAMPAIGN_LIMIT - todaySent);

  if (todayRemaining === 0) {
    return { error: `오늘 발송 한도 소진 (${todaySent}/${DAILY_CAMPAIGN_LIMIT}건)`, today_remaining: 0 };
  }

  const camps = await sbGet(env, '/campaigns?id=eq.' + campaignId + '&select=*');
  if (!Array.isArray(camps) || !camps[0]) return { error: '캠페인을 찾을 수 없습니다.' };
  const campaign = camps[0];

  if (campaign.status !== 'active') {
    return { error: `발송 불가 — 캠페인 상태: ${campaign.status}` };
  }
  if (!campaign.html_body) {
    return { error: '이메일 본문(html_body)이 저장되지 않은 캠페인입니다.' };
  }

  const batchLimit = Math.min(campaign.daily_limit || DAILY_CAMPAIGN_LIMIT, todayRemaining);

  const batch = await sbRpc(env, 'get_campaign_batch', {
    p_campaign_id: campaignId,
    p_limit:       batchLimit,
  });
  if (!Array.isArray(batch) || batch.length === 0) {
    return { error: '발송 대기 중인 이메일이 없습니다.', today_remaining: todayRemaining };
  }

  const unsubSet  = await getUnsubscribes(env);
  const toSend    = batch.filter(e => !unsubSet.has(e.email.toLowerCase()));
  const unsubRows = batch.filter(e =>  unsubSet.has(e.email.toLowerCase()));

  // 수신거부 항목은 failed로 처리해 pending에서 제외
  if (unsubRows.length > 0) {
    await sbRpc(env, 'complete_campaign_batch', {
      p_campaign_id:  campaignId,
      p_sent_ids:     [],
      p_failed_ids:   unsubRows.map(e => e.id),
      p_run_date:     kstDateStr(),
      p_triggered_by: triggeredBy,
    });
  }

  if (toSend.length === 0) {
    return { sent: 0, failed: unsubRows.length, today_remaining: todayRemaining };
  }

  const mKey      = monthKey();
  const monthSent = parseInt((await env.MAIL_USAGE.get(mKey)) || '0');
  if (monthSent + toSend.length > MONTHLY_LIMIT) {
    return { error: `월 발송 한도 초과 (${monthSent}/${MONTHLY_LIMIT})`, today_remaining: todayRemaining };
  }

  const from      = env.MAIL_FROM || 'WorksFree 컨설팅 <onboarding@resend.dev>';
  const batchBody = toSend.map(e => ({
    from,
    to:      [e.email],
    subject: campaign.subject,
    html:    campaign.html_body,
  }));

  const sentIds = [], failedIds = [];
  try {
    const res  = await fetch('https://api.resend.com/emails/batch', {
      method:  'POST',
      headers: { Authorization: 'Bearer ' + env.RESEND_API_KEY, 'Content-Type': 'application/json' },
      body:    JSON.stringify(batchBody),
    });
    const data = await res.json();
    if (res.ok) {
      const results = Array.isArray(data.data) ? data.data : [];
      toSend.forEach((e, idx) => {
        if (results[idx]?.id) sentIds.push(e.id);
        else                  failedIds.push(e.id);
      });
    } else {
      toSend.forEach(e => failedIds.push(e.id));
    }
  } catch {
    toSend.forEach(e => failedIds.push(e.id));
  }

  const sentCount = sentIds.length;

  const result = await sbRpc(env, 'complete_campaign_batch', {
    p_campaign_id:  campaignId,
    p_sent_ids:     sentIds,
    p_failed_ids:   failedIds,
    p_run_date:     kstDateStr(),
    p_triggered_by: triggeredBy,
  });

  if (sentCount > 0) {
    const newDailySent = todaySent + sentCount;
    await env.MAIL_USAGE.put(todayKey, String(newDailySent));
    await env.MAIL_USAGE.put(mKey, String(monthSent + sentCount));
  }

  // email_log 기록 (비동기)
  const now     = new Date().toISOString();
  const sentSet = new Set(sentIds);
  const logRows = batch
    .filter(e => sentSet.has(e.id))
    .map(e => ({
      sent_at:         now,
      recipient_email: e.email.toLowerCase(),
      flyer_src:       campaign.flyer_src  || null,
      flyer_name:      campaign.flyer_name || null,
      subject:         campaign.subject,
      env:             campaign.env || 'portal',
      status:          'sent',
    }));
  if (logRows.length > 0) sbPost(env, 'email_log', logRows);

  return {
    sent:              sentCount,
    failed:            failedIds.length + unsubRows.length,
    remaining_pending: result?.remaining_pending ?? null,
    completed:         result?.completed ?? false,
    today_remaining:   Math.max(0, DAILY_CAMPAIGN_LIMIT - todaySent - sentCount),
  };
}

/**
 * Cron 핸들러: 모든 active 캠페인을 순회하며 일일 한도 내에서 배치 발송
 */
async function runDailyCampaigns(env) {
  if (!env.RESEND_API_KEY) return;

  const campaigns = await sbGet(
    env,
    '/campaigns?status=eq.active&select=id,name,daily_limit&order=created_at.asc'
  );
  if (!Array.isArray(campaigns) || campaigns.length === 0) return;

  for (const camp of campaigns) {
    const todayKey  = dailyCampaignKey();
    const todaySent = parseInt((await env.MAIL_USAGE.get(todayKey)) || '0');
    if (todaySent >= DAILY_CAMPAIGN_LIMIT) break;

    await runCampaignBatch(camp.id, env, 'cron');
  }
}

// ── 메인 핸들러 ────────────────────────────────────────────────────

export default {

  async fetch(request, env, ctx) {
    if (request.method === 'OPTIONS') {
      return new Response(null, { status: 204, headers: CORS_HEADERS });
    }

    const url = new URL(request.url);

    // ── GET /db-stats : DB 캠페인 통계 (레거시) ────────────────────
    if (request.method === 'GET' && url.pathname === '/db-stats') {
      const stats     = await sbRpc(env, 'get_campaign_stats');
      const todayKey  = dailyCampaignKey();
      const todaySent = parseInt((await env.MAIL_USAGE.get(todayKey)) || '0');
      return json({
        ...(stats || { total: 0, active: 0, sent: 0, unsubscribed: 0, pending: 0 }),
        today_sent:      todaySent,
        today_limit:     DAILY_CAMPAIGN_LIMIT,
        today_remaining: Math.max(0, DAILY_CAMPAIGN_LIMIT - todaySent),
      });
    }

    // ── GET /db-pending : 오늘 발송 가능한 배치 (레거시) ────────────
    if (request.method === 'GET' && url.pathname === '/db-pending') {
      const todayKey       = dailyCampaignKey();
      const todaySent      = parseInt((await env.MAIL_USAGE.get(todayKey)) || '0');
      const todayRemaining = Math.max(0, DAILY_CAMPAIGN_LIMIT - todaySent);
      if (todayRemaining === 0) {
        return json({ emails: [], today_sent: todaySent, today_remaining: 0, today_limit: DAILY_CAMPAIGN_LIMIT });
      }
      const reqLimit       = parseInt(url.searchParams.get('limit') || '100');
      const effectiveLimit = Math.min(reqLimit, todayRemaining);
      const emails         = await sbRpc(env, 'get_campaign_pending', { p_limit: effectiveLimit });
      return json({
        emails:          emails || [],
        today_sent:      todaySent,
        today_remaining: todayRemaining,
        today_limit:     DAILY_CAMPAIGN_LIMIT,
      });
    }

    // ── GET /db-list : 전체 발송 현황 목록 (레거시) ─────────────────
    if (request.method === 'GET' && url.pathname === '/db-list') {
      const list = await sbRpc(env, 'get_campaign_list');
      if (!list) return json({ error: 'DB 조회 실패 — Supabase RPC 오류' }, 500);
      return json(list);
    }

    // ── GET /gov/db-stats : gov_contacts 캠페인 통계 ────────────────
    if (request.method === 'GET' && url.pathname === '/gov/db-stats') {
      const stats     = await sbRpc(env, 'get_gov_campaign_stats');
      const todayKey  = dailyCampaignKey();
      const todaySent = parseInt((await env.MAIL_USAGE.get(todayKey)) || '0');
      return json({
        ...(stats || { total: 0, active: 0, sent: 0, unsubscribed: 0, pending: 0 }),
        today_sent:      todaySent,
        today_limit:     DAILY_CAMPAIGN_LIMIT,
        today_remaining: Math.max(0, DAILY_CAMPAIGN_LIMIT - todaySent),
      });
    }

    // ── GET /gov/db-pending : gov_contacts 오늘 발송 가능 배치 ──────
    if (request.method === 'GET' && url.pathname === '/gov/db-pending') {
      const todayKey       = dailyCampaignKey();
      const todaySent      = parseInt((await env.MAIL_USAGE.get(todayKey)) || '0');
      const todayRemaining = Math.max(0, DAILY_CAMPAIGN_LIMIT - todaySent);
      if (todayRemaining === 0) {
        return json({ emails: [], today_sent: todaySent, today_remaining: 0, today_limit: DAILY_CAMPAIGN_LIMIT });
      }
      const reqLimit       = parseInt(url.searchParams.get('limit') || '100');
      const effectiveLimit = Math.min(reqLimit, todayRemaining);
      const emails         = await sbRpc(env, 'get_gov_campaign_pending', { p_limit: effectiveLimit });
      return json({
        emails:          emails || [],
        today_sent:      todaySent,
        today_remaining: todayRemaining,
        today_limit:     DAILY_CAMPAIGN_LIMIT,
      });
    }

    // ── GET /gov/db-list : gov_contacts 전체 발송 현황 목록 ─────────
    if (request.method === 'GET' && url.pathname === '/gov/db-list') {
      const list = await sbRpc(env, 'get_gov_campaign_list');
      if (!list) return json({ error: 'DB 조회 실패 — Supabase RPC 오류' }, 500);
      return json(list);
    }

    // ── GET /campaigns : 캠페인 목록 ───────────────────────────────
    if (request.method === 'GET' && url.pathname === '/campaigns') {
      const list = await sbRpc(env, 'get_campaigns_list');
      return json(list || []);
    }

    // ── GET /campaigns/:id/runs : 실행 이력 ────────────────────────
    const runsMatch = url.pathname.match(/^\/campaigns\/([^/]+)\/runs$/);
    if (request.method === 'GET' && runsMatch) {
      const runs = await sbRpc(env, 'get_campaign_runs', { p_campaign_id: runsMatch[1] });
      return json(runs || []);
    }

    // ── GET / : 월 발송 현황 ────────────────────────────────────────
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
      await sbPost(env, 'email_unsubscribes', [{
        email,
        source: body.source || 'link',
        note:   body.note   || null,
      }]);
      return json({ success: true, email });
    }

    // ── POST /db-send : DB 캠페인 배치 발송 (레거시) ────────────────
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

      const allowedEmails = dbEmails.slice(0, todayRemaining);
      const unsubSet      = await getUnsubscribes(env);
      const toSend        = allowedEmails.filter(e => !unsubSet.has((e.to || '').toLowerCase()));
      const filtered      = allowedEmails
        .filter(e => unsubSet.has((e.to || '').toLowerCase()))
        .map(e => ({ email: e.to, reason: '수신거부' }));

      const mKey      = monthKey();
      const monthSent = parseInt((await env.MAIL_USAGE.get(mKey)) || '0');
      if (monthSent + toSend.length > MONTHLY_LIMIT) {
        return json({ error: `월 발송 한도 초과 (${monthSent}/${MONTHLY_LIMIT})` }, 429);
      }

      const from       = env.MAIL_FROM || 'WorksFree 컨설팅 <onboarding@resend.dev>';
      const authHeader = 'Bearer ' + env.RESEND_API_KEY;
      const sentEmails = [], failed = [];

      // 숨김 Unicode 문자 제거 후 이메일 형식 검증 (DART 스크래핑 데이터의 BOM·ZWSP 등 처리)
      const cleanEmail = raw => { let s = (raw || '').replace(/[\u0000-\u001F\u007F\u00A0\u200B-\u200F\u2028\u2029\uFEFF]/g, '').trim(); const at = s.lastIndexOf('@'); if (at > 0) { const loc = s.slice(0, at).replace(/^\.+|\.+$/g, '').replace(/\.{2,}/g, '.'); s = loc + s.slice(at); } return s; };
      const isEmail    = addr => { const m = addr.match(/^([^\s@]+)@([^\s@]+\.[^\s@]{2,})$/); if (!m) return false; const l = m[1]; return !l.startsWith('.') && !l.endsWith('.') && !l.includes('..'); };

      const readyToSend = [];
      toSend.forEach(e => {
        const clean = cleanEmail(e.to);
        if (!clean || !isEmail(clean)) {
          failed.push({ email: e.to || '', reason: `이메일 형식 오류 (원본: "${e.to}")` });
        } else {
          readyToSend.push({ ...e, to: clean });
        }
      });

      const batchBody = readyToSend.map(e => ({
        from, to: [e.to], subject: e.subject, html: e.html,
      }));
      let _debug = null;
      if (batchBody.length > 0) {
        try {
          const batchRes  = await fetch('https://api.resend.com/emails/batch', {
            method:  'POST',
            headers: { Authorization: authHeader, 'Content-Type': 'application/json' },
            body:    JSON.stringify(batchBody),
          });
          const batchData = await batchRes.json();
          _debug = {
            status: batchRes.status,
            resend_response: batchData,
            to_sample: batchBody.slice(0, 3).map(e => ({
              to: e.to,
              to_type: typeof e.to,
              to_len:  JSON.stringify(e.to).length,
              from:    e.from,
              subject_len: (e.subject || '').length,
              html_len:    (e.html || '').length,
            })),
          };
          if (!batchRes.ok) {
            const errMsg = batchData.message || 'Resend batch error';
            readyToSend.forEach(e => failed.push({ email: e.to, reason: errMsg }));
          } else {
            const results = Array.isArray(batchData.data) ? batchData.data : [];
            readyToSend.forEach((e, idx) => {
              if (results[idx] && results[idx].id) sentEmails.push(e);
              else failed.push({ email: e.to, reason: '발송 ID 없음' });
            });
          }
        } catch (err) {
          _debug = { error: err.message };
          readyToSend.forEach(e => failed.push({ email: e.to, reason: err.message }));
        }
      }

      const sentCount    = sentEmails.length;
      const newDailySent = todaySent + sentCount;

      if (sentCount > 0) {
        await env.MAIL_USAGE.put(mKey,     String(monthSent + sentCount));
        await env.MAIL_USAGE.put(todayKey, String(newDailySent));
      }

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
        _debug,
      });
    }

    // ── POST /campaigns : 캠페인 생성 ─────────────────────────────
    if (url.pathname === '/campaigns') {
      const { name, subject, flyer_src, flyer_name, html_body, env: campEnv } = body;
      if (!name || !subject) return json({ error: 'name, subject 필수' }, 400);

      const campaign = await sbInsert(env, 'campaigns', {
        name,
        subject,
        flyer_src:  flyer_src  || null,
        flyer_name: flyer_name || null,
        html_body:  html_body  || null,
        env:        campEnv    || 'portal',
      });

      if (!campaign) return json({ error: '캠페인 생성 실패 — Supabase 오류' }, 500);
      return json({ success: true, campaign });
    }

    // ── POST /campaigns/:id/:action ────────────────────────────────
    const actionMatch = url.pathname.match(
      /^\/campaigns\/([^/]+)\/(activate|pause|resume|cancel|send-now)$/
    );
    if (actionMatch) {
      const [, campId, action] = actionMatch;

      if (action === 'activate') {
        const result = await sbRpc(env, 'activate_campaign', { p_campaign_id: campId });
        if (!result) return json({ error: 'RPC 실패' }, 500);
        if (result.error) return json(result, 400);
        return json(result);
      }

      if (action === 'pause') {
        await sbPatch(env, 'campaigns', campId, { status: 'paused' });
        return json({ success: true, status: 'paused' });
      }

      if (action === 'resume') {
        await sbPatch(env, 'campaigns', campId, { status: 'active' });
        return json({ success: true, status: 'active' });
      }

      if (action === 'cancel') {
        await sbPatch(env, 'campaigns', campId, { status: 'cancelled' });
        return json({ success: true, status: 'cancelled' });
      }

      if (action === 'send-now') {
        if (!env.RESEND_API_KEY) return json({ error: 'RESEND_API_KEY not configured' }, 500);
        const result = await runCampaignBatch(campId, env, 'manual');
        if (result.error) return json(result, result.today_remaining === 0 ? 429 : 400);
        return json({ success: true, ...result });
      }
    }

    // ── POST / : 일반 메일 발송 ─────────────────────────────────────
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

    if (toSend.length === 0) {
      const key     = monthKey();
      const curSent = parseInt((await env.MAIL_USAGE.get(key)) || '0');
      return json({
        success: true, sent: 0, filtered,
        totalSent: curSent, remaining: Math.max(0, MONTHLY_LIMIT - curSent),
      });
    }

    const key         = monthKey();
    const currentSent = parseInt((await env.MAIL_USAGE.get(key)) || '0');
    if (currentSent + toSend.length > MONTHLY_LIMIT) {
      return json({
        error: `월 발송 한도 초과 — 이번 달 ${currentSent}/${MONTHLY_LIMIT}건 사용됨`,
      }, 429);
    }

    const auth       = 'Bearer ' + env.RESEND_API_KEY;
    const CHUNK      = 100;
    const RATE_MS    = 550;
    const sentEmails = [];
    const failed     = [];
    const sendErrors = [];

    const sleep = ms => new Promise(r => setTimeout(r, ms));

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
      if (i > 0) await sleep(RATE_MS);
      const chunk = toSend.slice(i, i + CHUNK);

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
      }

      const resendRes = await fetch('https://api.resend.com/emails/batch', {
        method:  'POST',
        headers: { Authorization: auth, 'Content-Type': 'application/json' },
        body:    JSON.stringify(chunk.map(e => ({ from, to: [e.to], subject: e.subject, html: e.html }))),
      });
      const resendData = await resendRes.json();
      if (!resendRes.ok) {
        const chunkMsg = resendData.message || 'Resend API error';
        sendErrors.push(`${i + 1}-${i + chunk.length}번째 묶음 실패: ${chunkMsg}`);
        chunk.forEach(e => failed.push({ email: e.to, reason: chunkMsg }));
        continue;
      }
      sentEmails.push(...chunk);
    }

    const sentCount = sentEmails.length;
    if (sentCount === 0 && (sendErrors.length > 0 || failed.length > 0)) {
      return json({ error: sendErrors[0] }, 400);
    }

    const newTotal = currentSent + sentCount;
    await env.MAIL_USAGE.put(key, String(newTotal));

    const now          = new Date().toISOString();
    const senderEmail  = (meta.senderEmail || '').toLowerCase() || null;
    const logRows      = sentEmails.map(e => ({
      sent_at:         now,
      recipient_email: e.to.toLowerCase(),
      sender_email:    senderEmail,
      sender_name:     meta.senderName   || null,
      sender_user_id:  meta.senderUserId || null,
      flyer_src:       meta.flyerSrc     || null,
      flyer_name:      meta.flyerName    || null,
      subject:         e.subject         || null,
      env:             meta.env          || 'portal',
      status:          'sent',
    }));
    const filterRows = filtered.map(f => ({
      sent_at:         now,
      recipient_email: f.email.toLowerCase(),
      sender_email:    senderEmail,
      sender_name:     meta.senderName || null,
      flyer_src:       meta.flyerSrc   || null,
      flyer_name:      meta.flyerName  || null,
      env:             meta.env        || 'portal',
      status:          'filtered',
    }));

    const allRows = [...logRows, ...filterRows];
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

  // ── Cron (0 0 * * * UTC = KST 09:00) ──────────────────────────────
  async scheduled(event, env, ctx) {
    ctx.waitUntil(runDailyCampaigns(env));
  },
};

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { ...CORS_HEADERS, 'Content-Type': 'application/json' },
  });
}
