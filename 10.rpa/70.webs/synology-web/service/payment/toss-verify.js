/**
 * Cloudflare Worker — Toss Payments 결제 검증
 *
 * 배포: wrangler deploy (또는 Cloudflare 대시보드에서 직접 붙여넣기)
 * 환경 변수 (Cloudflare → Workers → Settings → Variables):
 *   TOSS_SECRET_KEY  : Toss 대시보드 → 개발 → API 키 → 테스트 시크릿 키
 *                      형식: test_sk_... (테스트) / live_sk_... (실서비스)
 *
 * 요청: POST /
 *   { orderId: string, paymentKey: string, amount: number }
 *
 * 응답 성공: { success: true, payment: { ... } }
 * 응답 실패: { error: string }
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

    let body;
    try {
      body = await request.json();
    } catch {
      return json({ error: 'Invalid JSON' }, 400);
    }

    const { orderId, paymentKey, amount } = body;
    if (!orderId || !paymentKey || !amount) {
      return json({ error: 'orderId, paymentKey, amount are required' }, 400);
    }

    if (!env.TOSS_SECRET_KEY) {
      return json({ error: 'TOSS_SECRET_KEY not configured' }, 500);
    }

    // Toss Payments 결제 승인 API 호출
    // 문서: https://docs.tosspayments.com/reference#결제-승인
    const credential = btoa(env.TOSS_SECRET_KEY + ':');
    const tossRes = await fetch('https://api.tosspayments.com/v1/payments/confirm', {
      method: 'POST',
      headers: {
        'Authorization': 'Basic ' + credential,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ orderId, paymentKey, amount }),
    });

    const tossData = await tossRes.json();

    if (!tossRes.ok) {
      // Toss API 에러: { code, message }
      return json({ error: tossData.message || 'Toss API error' }, 400);
    }

    // 금액 이중 검증 (위변조 방지)
    if (tossData.totalAmount !== amount) {
      return json({ error: 'Amount mismatch — possible tampering' }, 400);
    }

    return json({ success: true, payment: tossData });
  },
};

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { ...CORS_HEADERS, 'Content-Type': 'application/json' },
  });
}
