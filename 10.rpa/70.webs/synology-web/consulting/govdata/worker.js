/**
 * Cloudflare Worker — 공공데이터포털 프록시 (지자체·공공기관 이메일 캠페인용)
 *
 * 배포: wrangler deploy --config wrangler.toml
 * 시크릿: GOVDATA_SERVICE_KEY (data.go.kr 활용신청 후 발급되는 일반 인증키)
 *
 * API:
 *   GET /?ep=getNFcltBizInqire&<원본 파라미터...>
 *     → 전국사회복지시설표준데이터 (노인복지관 등) 프록시, CORS 허용, JSON 강제
 *
 * 주의: 실제 응답 필드(홈페이지/이메일 포함 여부)는 배포 후 1회 호출로 확인 필요.
 *       필드가 다르면 이 파일의 PROXY_EPS/BASE만 맞춰 확장하면 됨 — admin/gov-contacts
 *       수집 UI 쪽 파싱 로직은 그대로 두고 여기서 흡수한다.
 */

const ALLOWED_ORIGIN = '*';

// 엔드포인트별 base URL — 필요시 여기에 추가
const ENDPOINTS = {
  // 전국사회복지시설표준데이터 (노인복지관 등 사회복지시설 전체)
  getNFcltBizInqire: 'https://apis.data.go.kr/B554287/sclWlfrFcltInfoInqirService1/getNFcltBizInqire',
};

addEventListener('fetch', event => {
  event.respondWith(handleRequest(event.request));
});

async function handleRequest(request) {
  if (request.method === 'OPTIONS') {
    return new Response(null, { status: 204, headers: corsHeaders() });
  }

  const url = new URL(request.url);
  const ep  = url.searchParams.get('ep');
  if (!ep) return jsonResp({ status: 'ERR', message: 'ep 파라미터가 없습니다.' }, 400);

  const base = ENDPOINTS[ep];
  if (!base) return jsonResp({ status: 'ERR', message: `지원하지 않는 엔드포인트: ${ep}` }, 400);

  const serviceKey = (typeof GOVDATA_SERVICE_KEY !== 'undefined' && GOVDATA_SERVICE_KEY) || '';
  if (!serviceKey) return jsonResp({ status: 'ERR', message: 'GOVDATA_SERVICE_KEY가 설정되지 않았습니다.' }, 500);

  const params = new URLSearchParams(url.search);
  params.delete('ep');
  params.set('serviceKey', serviceKey);
  if (!params.has('pageNo'))     params.set('pageNo', '1');
  if (!params.has('numOfRows'))  params.set('numOfRows', '100');
  if (!params.has('_type'))      params.set('_type', 'json'); // XML 기본 응답 → JSON 강제

  try {
    const resp = await fetch(`${base}?${params}`, { headers: { 'User-Agent': 'Mozilla/5.0' } });
    const text = await resp.text();
    return new Response(text, {
      status: resp.status,
      headers: { 'Content-Type': 'application/json;charset=utf-8', ...corsHeaders() },
    });
  } catch (e) {
    return jsonResp({ status: 'ERR', message: e.message }, 502);
  }
}

function corsHeaders() {
  return {
    'Access-Control-Allow-Origin':  ALLOWED_ORIGIN,
    'Access-Control-Allow-Methods': 'GET, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Max-Age':       '86400',
  };
}
function jsonResp(obj, status = 200) {
  return new Response(JSON.stringify(obj), {
    status,
    headers: { 'Content-Type': 'application/json;charset=utf-8', ...corsHeaders() },
  });
}
