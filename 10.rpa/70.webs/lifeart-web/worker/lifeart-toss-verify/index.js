/**
 * Cloudflare Worker — LifeArt 토스페이먼츠 결제 검증 + 주문/결제 확정
 *                     + (임시) 이메일 확인 우회
 *
 * 토스 결제 승인을 서버에서 시크릿 키로 검증한 뒤, 그 결과가 성공일 때만
 * service_role 로 lifeart_orders.status='paid' 갱신 + lifeart_payments INSERT.
 * 클라이언트는 이 두 테이블에 대한 쓰기 RLS 정책이 없어 위조 불가.
 *
 * 배포: wrangler deploy --config wrangler.toml
 * Worker secrets (wrangler secret put ...):
 *   TOSS_SECRET_KEY           : 토스 시크릿 키 (현재 공용 테스트 키 — 실 운영 전 교체)
 *   SUPABASE_URL              : Supabase 프로젝트 URL
 *   SUPABASE_SERVICE_ROLE_KEY : Supabase service_role 키 (RLS bypass)
 *   SKIP_EMAIL_CONFIRM        : "true" 로 설정하면 POST /confirm-email 활성화
 *                               (Auth SMTP 설정 전 임시 — 세팅 완료 후 이 시크릿만
 *                                삭제하거나 "false" 로 바꾸면 코드 변경 없이 원복됨)
 *
 * 요청: POST /  { orderId, paymentKey, amount }  — 토스 결제 검증(기존)
 *       POST /confirm-email  { id }              — LifeArt 신규가입 즉시 이메일 확인(임시)
 */

const CORS_HEADERS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'POST, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type, Authorization',
};

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.pathname === '/confirm-email') return handleConfirmEmail(request, env);
    return handleTossVerify(request, env);
  },
};

// Supabase Auth 이메일 확인 임시 우회 — SMTP 미설정 기간 한정.
// 남용 방지: LifeArt 가입 표식(user_metadata.tenant==='lifeart') + 가입 10분 이내 계정만 허용.
async function handleConfirmEmail(request, env) {
  if (request.method === 'OPTIONS') return new Response(null, { headers: CORS_HEADERS });
  if (request.method !== 'POST') return json({ error: 'Method not allowed' }, 405);
  if (env.SKIP_EMAIL_CONFIRM !== 'true') return json({ error: 'disabled' }, 403);
  if (!env.SUPABASE_URL || !env.SUPABASE_SERVICE_ROLE_KEY) return json({ error: 'not configured' }, 500);

  let body;
  try { body = await request.json(); } catch { return json({ error: 'Invalid JSON' }, 400); }
  const { id } = body;
  if (!id) return json({ error: 'id is required' }, 400);

  const adminHeaders = {
    apikey: env.SUPABASE_SERVICE_ROLE_KEY,
    Authorization: 'Bearer ' + env.SUPABASE_SERVICE_ROLE_KEY,
    'Content-Type': 'application/json',
  };

  const getRes = await fetch(`${env.SUPABASE_URL}/auth/v1/admin/users/${id}`, { headers: adminHeaders });
  if (!getRes.ok) return json({ error: 'user not found' }, 404);
  const user = await getRes.json();

  if (user.user_metadata?.tenant !== 'lifeart') return json({ error: 'not a lifeart signup' }, 403);
  if (Date.now() - new Date(user.created_at).getTime() > 10 * 60 * 1000) {
    return json({ error: 'signup too old' }, 403);
  }
  if (user.email_confirmed_at) return json({ success: true, already: true });

  const upRes = await fetch(`${env.SUPABASE_URL}/auth/v1/admin/users/${id}`, {
    method: 'PUT', headers: adminHeaders,
    body: JSON.stringify({ email_confirm: true }),
  });
  if (!upRes.ok) return json({ error: 'confirm failed' }, 500);
  return json({ success: true });
}

async function handleTossVerify(request, env) {
    if (request.method === 'OPTIONS') return new Response(null, { headers: CORS_HEADERS });
    if (request.method !== 'POST') return json({ error: 'Method not allowed' }, 405);

    let body;
    try { body = await request.json(); } catch { return json({ error: 'Invalid JSON' }, 400); }

    const { orderId, paymentKey, amount } = body;
    if (!orderId || !paymentKey || !amount) {
      return json({ error: 'orderId, paymentKey, amount are required' }, 400);
    }
    if (!env.TOSS_SECRET_KEY) return json({ error: 'TOSS_SECRET_KEY not configured' }, 500);

    // 1) 토스 결제 승인
    const credential = btoa(env.TOSS_SECRET_KEY + ':');
    const tossRes = await fetch('https://api.tosspayments.com/v1/payments/confirm', {
      method: 'POST',
      headers: { Authorization: 'Basic ' + credential, 'Content-Type': 'application/json' },
      body: JSON.stringify({ orderId, paymentKey, amount }),
    });
    const tossData = await tossRes.json();
    if (!tossRes.ok) return json({ error: tossData.message || 'Toss API error' }, 400);
    if (tossData.totalAmount !== amount) return json({ error: 'Amount mismatch — possible tampering' }, 400);

    // 2) service_role 로 주문 확정 + 결제 기록 (키 없으면 검증만 하고 반환 — 로컬/키 미설정 대비)
    if (env.SUPABASE_URL && env.SUPABASE_SERVICE_ROLE_KEY) {
      const sbHeaders = {
        apikey: env.SUPABASE_SERVICE_ROLE_KEY,
        Authorization: 'Bearer ' + env.SUPABASE_SERVICE_ROLE_KEY,
        'Content-Type': 'application/json',
      };

      // 주문 조회 — select=* 로 스키마 무관하게 동작(공유 DB엔 tenant_id 있고,
      // 이관된 독립 프로젝트엔 없음 — 아래서 존재할 때만 결제 기록에 반영).
      // ★ 이 조회를 tenant_id 컬럼명으로 고정하면 독립(standalone) 스키마로
      //   이관 시 "column tenant_id does not exist" 로 즉시 깨짐 — 이관 완전성을
      //   위해 의도적으로 스키마에 무관하게 동작하도록 작성함.
      const ordRes = await fetch(
        `${env.SUPABASE_URL}/rest/v1/lifeart_orders?id=eq.${orderId}&select=*`,
        { headers: sbHeaders });
      const ords = await ordRes.json();
      const order = Array.isArray(ords) ? ords[0] : null;
      if (!order) return json({ error: 'order not found' }, 404);
      if (order.amount !== amount) return json({ error: 'order amount mismatch' }, 400);

      if (order.status !== 'paid') {
        // 주문 확정
        await fetch(`${env.SUPABASE_URL}/rest/v1/lifeart_orders?id=eq.${orderId}`, {
          method: 'PATCH', headers: sbHeaders,
          body: JSON.stringify({ status: 'paid' }),
        });
        // 결제 기록 — tenant_id/env 는 주문 레코드에 그 컬럼이 실제로 있을 때만 포함
        const paymentPayload = {
          order_id: orderId,
          pg_provider: 'toss',
          pg_tid: paymentKey,
          amount,
          status: 'approved',
          approved_at: new Date().toISOString(),
        };
        if ('tenant_id' in order) paymentPayload.tenant_id = order.tenant_id;
        if ('env' in order)       paymentPayload.env       = order.env;
        await fetch(`${env.SUPABASE_URL}/rest/v1/lifeart_payments`, {
          method: 'POST', headers: sbHeaders,
          body: JSON.stringify(paymentPayload),
        });
      }
    }

    return json({ success: true, payment: tossData });
}

function json(data, status = 200) {
  return new Response(JSON.stringify(data), { status, headers: { ...CORS_HEADERS, 'Content-Type': 'application/json' } });
}
