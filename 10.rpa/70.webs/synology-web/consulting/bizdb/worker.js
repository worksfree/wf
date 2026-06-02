/**
 * Cloudflare Worker — B2B 이메일 DB 관리 (biz-db)
 *
 * 배포: wrangler deploy --config wrangler.toml
 *
 * 시크릿:
 *   SUPABASE_URL         — Supabase 프로젝트 URL
 *   SUPABASE_SERVICE_KEY — service_role 키
 *
 * API:
 *   GET  /scrape?url=URL           → { emails, source, url }
 *   GET  /stats                    → { total, with_email, no_email, unsubscribed }
 *   GET  /contacts?page&status&induty&q  → { data, count, page }
 *   POST /contacts                 → upsert (배열)  → { ok, count }
 *   PATCH /contacts/:id            → 필드 업데이트   → { ok }
 *   DELETE /contacts               → { ids:[...] }  → { deleted }
 *   GET  /sendlist?month=YYYY-MM   → 이번달 발송 대상 { contacts, month, total, already_sent }
 *   POST /sendlog                  → 발송 이력 기록  → { ok, logged }
 */

const CORS = {
  'Access-Control-Allow-Origin':  '*',
  'Access-Control-Allow-Methods': 'GET, POST, PATCH, DELETE, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type',
};

/* ── Supabase REST 헬퍼 ──────────────────────────────────────────── */
function sbHeaders(env, extra = {}) {
  return {
    'apikey':        env.SUPABASE_SERVICE_KEY,
    'Authorization': 'Bearer ' + env.SUPABASE_SERVICE_KEY,
    'Content-Type':  'application/json',
    ...extra,
  };
}

async function sbFetch(env, path, opts = {}) {
  const { extraHeaders = {}, ...fetchOpts } = opts;
  const res = await fetch(env.SUPABASE_URL + '/rest/v1' + path, {
    ...fetchOpts,
    headers: sbHeaders(env, extraHeaders),
  });
  if (!res.ok) throw new Error('Supabase ' + res.status + ': ' + await res.text());
  const ct = res.headers.get('content-type') || '';
  if (ct.includes('json')) return res.json();
  return null;
}

/* ── 이메일 추출 엔진 ────────────────────────────────────────────── */
const EMAIL_RE = /([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})/g;

const NOISE_DOMAINS = [
  'example.com','test.com','domain.com','sample.com',
  'sentry.io','w3.org','schema.org','github.com','google.com',
  'apple.com','microsoft.com','adobe.com','amazon.com',
  'facebook.com','twitter.com','instagram.com','kakao.com',
  'naver.com','daum.net',
];
const NOISE_PREFIXES = ['noreply','no-reply','mailer-daemon','bounces','postmaster','donotreply','do-not-reply'];
const GOOD_PREFIXES  = ['info','contact','admin','cs','sales','help','support','biz','mail','pr','hr','manager'];
const SKIP_EXTS      = /\.(png|jpe?g|gif|svg|pdf|docx?|xlsx?|zip|mp4)$/i;

function extractEmails(html, baseUrl) {
  const all = [...new Set(html.match(EMAIL_RE) || [])];
  let baseDomain = '';
  try { baseDomain = new URL(baseUrl).hostname.replace(/^www\./, ''); } catch {}

  const valid = all.filter(e => {
    if (e.length > 80 || SKIP_EXTS.test(e)) return false;
    const lower  = e.toLowerCase();
    const [pfx, dom] = lower.split('@');
    if (!dom || !dom.includes('.')) return false;
    if (NOISE_DOMAINS.some(n => dom === n || dom.endsWith('.' + n))) return false;
    if (NOISE_PREFIXES.some(n => pfx.startsWith(n))) return false;
    return true;
  });

  valid.sort((a, b) => {
    const score = e => {
      const [p, d] = e.toLowerCase().split('@');
      return (d?.includes(baseDomain) ? 10 : 0) +
             (GOOD_PREFIXES.some(g => p === g || p.startsWith(g)) ? 5 : 0);
    };
    return score(b) - score(a);
  });

  return valid.slice(0, 5);
}

async function fetchWithTimeout(url, timeoutMs = 8000) {
  const ctrl = new AbortController();
  const tid  = setTimeout(() => ctrl.abort(), timeoutMs);
  try {
    const res = await fetch(url, {
      headers: { 'User-Agent': 'Mozilla/5.0 (compatible; WorksFreeBot/1.0; +https://worksfree.co.kr)' },
      redirect: 'follow',
      signal: ctrl.signal,
    });
    clearTimeout(tid);
    if (!res.ok) return { html: '', ok: false, finalUrl: url };
    return { html: await res.text(), ok: true, finalUrl: res.url || url };
  } catch {
    clearTimeout(tid);
    return { html: '', ok: false, finalUrl: url };
  }
}

async function handleScrape(searchParams) {
  let rawUrl = searchParams.get('url') || '';
  if (!rawUrl) return jsonRes({ emails: [], error: 'url 파라미터 필요' }, 400);

  const baseUrl = rawUrl.startsWith('http') ? rawUrl.replace(/\/$/, '') : 'https://' + rawUrl.replace(/\/$/, '');

  // 1차: 메인 페이지
  const { html, ok, finalUrl } = await fetchWithTimeout(baseUrl);
  let emails = ok ? extractEmails(html, finalUrl) : [];
  let source = 'homepage';

  // 2차: 이메일 없으면 contact/about 페이지 시도
  if (!emails.length && ok) {
    const candidates = ['/contact', '/contactus', '/contact-us', '/about', '/about-us', '/company'];
    for (const c of candidates) {
      const { html: ch, ok: cok, finalUrl: cf } = await fetchWithTimeout(baseUrl + c, 5000);
      if (cok) {
        const found = extractEmails(ch, cf);
        if (found.length) { emails = found; source = 'contact-page'; break; }
      }
    }
  }

  return jsonRes({ emails, source, url: baseUrl, ok });
}

/* ── /stats ──────────────────────────────────────────────────────── */
// select=count 사용 — 행 수가 많아도 정확한 집계 (Supabase 1000행 기본 제한 우회)
async function handleStats(env) {
  const cnt = q => sbFetch(env, '/biz_contacts?select=count' + q)
    .then(r => parseInt(r?.[0]?.count || 0)).catch(() => 0);
  const [total, active, noEmail, unsub] = await Promise.all([
    cnt(''),
    cnt('&email=not.is.null&email_status=neq.unsubscribed'),
    cnt('&email=is.null'),
    cnt('&email_status=eq.unsubscribed'),
  ]);
  return jsonRes({ total, with_email: active, no_email: noEmail, unsubscribed: unsub });
}

/* ── /contacts GET ───────────────────────────────────────────────── */
async function handleGetContacts(env, searchParams) {
  const page   = Math.max(1, parseInt(searchParams.get('page')  || '1'));
  const limit  = Math.min(200, parseInt(searchParams.get('limit') || '50'));
  const offset = (page - 1) * limit;
  const status     = searchParams.get('status')     || '';
  const induty     = searchParams.get('induty')     || '';
  const indutyName = searchParams.get('induty_name')|| ''; // 업종명 필터 (숫자 KSIC코드 대응)
  const q          = searchParams.get('q')          || '';

  let qs = `?select=*&order=created_at.desc&limit=${limit}&offset=${offset}`;
  if (status === 'active')        qs += '&email=not.is.null&email_status=neq.unsubscribed';
  else if (status === 'no_email') qs += '&email=is.null';
  else if (status === 'unsub')    qs += '&email_status=eq.unsubscribed';
  // induty_name 우선, 없으면 induty_code (알파벳 코드)로 fallback
  if (indutyName) qs += `&induty_name=eq.${encodeURIComponent(indutyName)}`;
  else if (induty) qs += `&induty_code=like.${encodeURIComponent(induty + '*')}`;
  if (q)      qs += `&corp_name=ilike.${encodeURIComponent('*' + q + '*')}`;

  // 필터 조건만 따로 구성 (count 쿼리용)
  let filterQs = '';
  if (status === 'active')        filterQs += '&email=not.is.null&email_status=neq.unsubscribed';
  else if (status === 'no_email') filterQs += '&email=is.null';
  else if (status === 'unsub')    filterQs += '&email_status=eq.unsubscribed';
  if (indutyName) filterQs += `&induty_name=eq.${encodeURIComponent(indutyName)}`;
  else if (induty) filterQs += `&induty_code=like.${encodeURIComponent(induty + '*')}`;
  if (q)      filterQs += `&corp_name=ilike.${encodeURIComponent('*' + q + '*')}`;

  const [data, countRes] = await Promise.all([
    sbFetch(env, '/biz_contacts' + qs),
    sbFetch(env, '/biz_contacts?select=count' + filterQs).catch(() => null),
  ]);

  const total = parseInt(countRes?.[0]?.count || 0);
  return jsonRes({ data: data || [], page, limit, total });
}

/* ── /contacts POST (upsert) ─────────────────────────────────────── */
async function handleUpsertContacts(env, body) {
  const rows = Array.isArray(body) ? body : [body];
  if (!rows.length) return jsonRes({ ok: true, count: 0 });
  // updated_at 자동 갱신
  const now = new Date().toISOString();
  const stamped = rows.map(r => ({ ...r, updated_at: now }));
  await sbFetch(env, '/biz_contacts', {
    method: 'POST',
    body: JSON.stringify(stamped),
    extraHeaders: { 'Prefer': 'resolution=merge-duplicates,return=minimal' },
  });
  return jsonRes({ ok: true, count: rows.length });
}

/* ── /contacts/:id PATCH ─────────────────────────────────────────── */
async function handlePatchContact(env, id, body) {
  await sbFetch(env, `/biz_contacts?id=eq.${id}`, {
    method: 'PATCH',
    body: JSON.stringify({ ...body, updated_at: new Date().toISOString() }),
    extraHeaders: { 'Prefer': 'return=minimal' },
  });
  return jsonRes({ ok: true });
}

/* ── /contacts DELETE ────────────────────────────────────────────── */
async function handleDeleteContacts(env, body) {
  const ids = body?.ids || [];
  if (!ids.length) return jsonRes({ deleted: 0 });
  await sbFetch(env, `/biz_contacts?id=in.(${ids.join(',')})`, { method: 'DELETE' });
  return jsonRes({ deleted: ids.length });
}

/* ── /sendlist ───────────────────────────────────────────────────── */
async function handleSendList(env, searchParams) {
  const month = searchParams.get('month') || monthKey();
  const limit = Math.min(3000, parseInt(searchParams.get('limit') || '3000'));

  // 이번달 이미 발송된 이메일
  const sent = await sbFetch(env, `/biz_send_log?select=email&batch_month=eq.${month}&limit=10000`);
  const sentSet = new Set((sent || []).map(r => r.email));

  // 활성 이메일이 있는 기업 중 이번달 미발송
  const contacts = await sbFetch(env,
    `/biz_contacts?select=*&email_status=eq.active&email=not.is.null&order=created_at.asc&limit=${limit + sentSet.size + 500}`
  );
  const toSend = (contacts || []).filter(c => c.email && !sentSet.has(c.email)).slice(0, limit);

  return jsonRes({ contacts: toSend, month, total: toSend.length, already_sent: sentSet.size });
}

/* ── /sendlog POST ───────────────────────────────────────────────── */
async function handleSendLog(env, body) {
  const rows = Array.isArray(body) ? body : [body];
  if (!rows.length) return jsonRes({ ok: true, logged: 0 });
  await sbFetch(env, '/biz_send_log', {
    method: 'POST',
    body: JSON.stringify(rows),
    extraHeaders: { 'Prefer': 'return=minimal' },
  });
  return jsonRes({ ok: true, logged: rows.length });
}

/* ── 유틸 ────────────────────────────────────────────────────────── */
function monthKey() {
  const d = new Date();
  return d.getUTCFullYear() + '-' + String(d.getUTCMonth() + 1).padStart(2, '0');
}
function jsonRes(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { ...CORS, 'Content-Type': 'application/json;charset=utf-8' },
  });
}

/* ── 메인 라우터 ─────────────────────────────────────────────────── */
export default {
  async fetch(request, env) {
    if (request.method === 'OPTIONS') return new Response(null, { status: 204, headers: CORS });

    const url  = new URL(request.url);
    const path = url.pathname.replace(/\/$/, '') || '/';

    try {
      if (path === '/scrape'   && request.method === 'GET')    return handleScrape(url.searchParams);
      if (path === '/stats'    && request.method === 'GET')    return handleStats(env);
      if (path === '/contacts' && request.method === 'GET')    return handleGetContacts(env, url.searchParams);
      if (path === '/contacts' && request.method === 'POST')   return handleUpsertContacts(env, await request.json());
      if (path === '/contacts' && request.method === 'DELETE') return handleDeleteContacts(env, await request.json());
      if (/^\/contacts\/[^/]+$/.test(path) && request.method === 'PATCH') {
        return handlePatchContact(env, path.split('/')[2], await request.json());
      }
      if (path === '/sendlist' && request.method === 'GET')    return handleSendList(env, url.searchParams);
      if (path === '/sendlog'  && request.method === 'POST')   return handleSendLog(env, await request.json());

      return jsonRes({ error: 'Not found', path }, 404);
    } catch (e) {
      return jsonRes({ error: e.message }, 500);
    }
  },
};
