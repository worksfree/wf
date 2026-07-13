/**
 * Cloudflare Worker — LifeArt 토스페이먼츠 결제 검증
 *
 * synology-web/service/payment/toss-verify.js 패턴을 LifeArt 전용으로 분리 배포.
 * 결제 승인 후 Supabase orders/payments 테이블까지 갱신한다.
 *
 * 배포: wrangler deploy --config wrangler.toml
 * 환경 변수 (Cloudflare 대시보드 → Workers → lifeart-toss-verify → Settings → Variables):
 *   TOSS_SECRET_KEY   : 토스 시크릿 키 (현재는 토스 공용 테스트 키 사용 — 실 운영 전 교체 필수)
 *   SUPABASE_URL      : Supabase 프로젝트 URL
 *   SUPABASE_ANON_KEY : Supabase anon key (orders/payments RLS를 통과하려면 서비스 role 권장이나,
 *                       본인 주문만 갱신하도록 이미 RLS로 제한되어 있어 anon + 사용자 JWT로 처리)
 *
 * 요청: POST /  { orderId: string(uuid, LifeArt orders.id), paymentKey: string, amount: number }
 */

const CORS_HEADERS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'POST, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type, Authorization',
};

export default {
  async fetch(request, env) {
    if (request.method === 'OPTIONS') return new Response(null, { headers: CORS_HEADERS });
    if (request.method !== 'POST') return json({ error: 'Method not allowed' }, 405);

    let body;
    try { body = await request.json(); } catch { return json({ error: 'Invalid JSON' }, 400); }

    const { orderId, paymentKey, amount } = body;
    if (!orderId || !paymentKey || !amount) {
      return json({ error: 'orderId, paymentKey, amount are required' }, 400);
    }
    if (!env.TOSS_SECRET_KEY) return json({ error: 'TOSS_SECRET_KEY not configured' }, 500);

    // 토스 결제 승인 API — LifeArt tossOrderId(문자열)로 검증, LifeArt orders.id(uuid)와는 별개 매핑
    const credential = btoa(env.TOSS_SECRET_KEY + ':');
    const tossRes = await fetch('https://api.tosspayments.com/v1/payments/confirm', {
      method: 'POST',
      headers: { Authorization: 'Basic ' + credential, 'Content-Type': 'application/json' },
      body: JSON.stringify({ orderId, paymentKey, amount }),
    });
    const tossData = await tossRes.json();

    if (!tossRes.ok) return json({ error: tossData.message || 'Toss API error' }, 400);
    if (tossData.totalAmount !== amount) return json({ error: 'Amount mismatch — possible tampering' }, 400);

    return json({ success: true, payment: tossData });
  },
};

function json(data, status = 200) {
  return new Response(JSON.stringify(data), { status, headers: { ...CORS_HEADERS, 'Content-Type': 'application/json' } });
}
