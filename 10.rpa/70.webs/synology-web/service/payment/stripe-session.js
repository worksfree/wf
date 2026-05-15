/**
 * Cloudflare Worker — Stripe Checkout 세션 생성 + 검증
 *
 * 배포: wrangler deploy (또는 Cloudflare 대시보드에서 직접 붙여넣기)
 * 환경 변수 (Cloudflare → Workers → Settings → Variables):
 *   STRIPE_SECRET_KEY : Stripe 대시보드 → Developers → API keys → Secret key
 *                       형식: sk_test_... (테스트) / sk_live_... (실서비스)
 *
 * 라우팅:
 *   POST /          → Checkout 세션 생성 → { url: string }
 *   POST /verify    → 세션 검증 → { success: true, amountUsd: number }
 */

const CORS_HEADERS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'POST, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type',
};

export default {
  async fetch(request, env) {
    if (request.method === 'OPTIONS') {
      return new Response(null, { headers: CORS_HEADERS });
    }

    if (request.method !== 'POST') {
      return json({ error: 'Method not allowed' }, 405);
    }

    if (!env.STRIPE_SECRET_KEY) {
      return json({ error: 'STRIPE_SECRET_KEY not configured' }, 500);
    }

    const url = new URL(request.url);

    if (url.pathname.endsWith('/verify')) {
      return handleVerify(request, env);
    }
    return handleCreateSession(request, env);
  },
};

/** Stripe Checkout 세션 생성 */
async function handleCreateSession(request, env) {
  let body;
  try { body = await request.json(); } catch { return json({ error: 'Invalid JSON' }, 400); }

  const { credits, amountUsd, userId, userEmail, successUrl, cancelUrl } = body;
  if (!credits || !amountUsd || !successUrl || !cancelUrl) {
    return json({ error: 'credits, amountUsd, successUrl, cancelUrl are required' }, 400);
  }

  // Stripe API: Checkout 세션 생성
  // 문서: https://stripe.com/docs/api/checkout/sessions/create
  const params = new URLSearchParams({
    'mode':                            'payment',
    'success_url':                     successUrl + '&session_id={CHECKOUT_SESSION_ID}',
    'cancel_url':                      cancelUrl,
    'line_items[0][quantity]':         '1',
    'line_items[0][price_data][currency]':              'usd',
    'line_items[0][price_data][unit_amount]':           String(Math.round(amountUsd * 100)),
    'line_items[0][price_data][product_data][name]':   `WorksFree ${credits} Credits`,
    'line_items[0][price_data][product_data][description]': `WorksFree 앱 크레딧 ${credits}개 충전`,
    'metadata[user_id]':               userId || '',
    'metadata[credits]':               String(credits),
  });
  if (userEmail) params.set('customer_email', userEmail);

  const stripeRes = await fetch('https://api.stripe.com/v1/checkout/sessions', {
    method: 'POST',
    headers: {
      'Authorization': 'Bearer ' + env.STRIPE_SECRET_KEY,
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    body: params.toString(),
  });

  const data = await stripeRes.json();
  if (!stripeRes.ok) {
    return json({ error: data.error?.message || 'Stripe API error' }, 400);
  }

  return json({ url: data.url, sessionId: data.id });
}

/** Stripe 세션 검증 — 결제 완료 후 호출 */
async function handleVerify(request, env) {
  let body;
  try { body = await request.json(); } catch { return json({ error: 'Invalid JSON' }, 400); }

  const { sessionId } = body;
  if (!sessionId) return json({ error: 'sessionId required' }, 400);

  const stripeRes = await fetch(`https://api.stripe.com/v1/checkout/sessions/${sessionId}`, {
    headers: { 'Authorization': 'Bearer ' + env.STRIPE_SECRET_KEY },
  });

  const session = await stripeRes.json();
  if (!stripeRes.ok) {
    return json({ error: session.error?.message || 'Stripe fetch error' }, 400);
  }

  if (session.payment_status !== 'paid') {
    return json({ error: 'Payment not completed: ' + session.payment_status }, 400);
  }

  return json({
    success:   true,
    amountUsd: session.amount_total / 100,
    credits:   parseInt(session.metadata?.credits || '0'),
    userId:    session.metadata?.user_id || '',
  });
}

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { ...CORS_HEADERS, 'Content-Type': 'application/json' },
  });
}
