/**
 * Cloudflare Worker — 법원경매 크롤러 + 데이터 서비스
 *
 * KV 바인딩 (Workers 설정에서 추가):
 *   이름: AUCTION_DATA   (namespace 생성 후 연결)
 *
 * 환경변수 (Workers Settings → Variables):
 *   PROXY_SECRET   아무 문자열 (관리자 API 보호용)
 *
 * KV 키 구조 (멀티테넌트):
 *   data:{tenant}       경매 데이터 JSON
 *   meta:{tenant}       { status, started_at, finished_at, count, next_page, total }
 *
 * 엔드포인트:
 *   GET  /health                  동작 확인
 *   GET  /data?tenant=X           데이터 조회 (공개)
 *   GET  /status?tenant=X         수집 상태 조회 (공개)
 *   POST /crawl?tenant=X          수집 실행 (공개 — 인증 불필요)
 *   POST /reset?tenant=X          데이터 초기화 (PROXY_SECRET 필요)
 */

const COURT_BASE = 'https://www.courtauction.go.kr';
const SEARCH_URL = `${COURT_BASE}/pgj/pgjsearch/searchControllerMain.on`;
const PAGE_URL   = `${COURT_BASE}/pgj/index.on?w2xPath=/pgj/ui/pgj100/PGJ151F00.xml`;
const UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36';

const CORS_HEADERS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type, X-Proxy-Secret',
};

/* ── 응답 헬퍼 ── */
const jsonResp = (data, status = 200) =>
  new Response(JSON.stringify(data, null, 0), {
    status,
    headers: { 'Content-Type': 'application/json; charset=utf-8', ...CORS_HEADERS },
  });

/* ── 인증 ── */
function checkAuth(request, env) {
  const secret = env.PROXY_SECRET;
  if (!secret) return true; // 미설정 시 통과 (개발용)
  return request.headers.get('X-Proxy-Secret') === secret;
}

/* ── 세션 쿠키 획득 ── */
async function getSessionCookies() {
  const resp = await fetch(PAGE_URL, {
    headers: { 'User-Agent': UA, 'Accept': 'text/html,*/*', 'Accept-Language': 'ko-KR,ko;q=0.9' },
    redirect: 'follow',
  });
  const parts = [];
  resp.headers.forEach((val, key) => {
    if (key.toLowerCase() === 'set-cookie') {
      const main = val.split(';')[0].trim();
      if (main) parts.push(main);
    }
  });
  return parts.join('; ');
}

/* ── 법원 API 1페이지 호출 ── */
async function fetchCourtPage(cookies, pageNo, pageSize = 20) {
  const body = {
    dma_pageInfo: {
      pageNo, pageSize, bfPageNo: '', startRowNo: '',
      totalCnt: '', totalYn: 'Y', groupTotalCount: '',
    },
    dma_srchGdsDtlSrchInfo: {
      rletDspslSpcCondCd: '', bidDvsCd: '', mvprpRletDvsCd: '00031R',
      cortAuctnSrchCondCd: '0004601',
      rprsAdongSdCd: '', rprsAdongSggCd: '', rprsAdongEmdCd: '',
      rdnmSdCd: '', rdnmSggCd: '', rdnmNo: '',
      mvprpDspslPlcAdongSdCd: '', mvprpDspslPlcAdongSggCd: '',
      mvprpDspslPlcAdongEmdCd: '', rdDspslPlcAdongSdCd: '',
      rdDspslPlcAdongSggCd: '', rdDspslPlcAdongEmdCd: '',
      cortOfcCd: '', jdbnCd: '', execrOfcDvsCd: '',
      lclDspslGdsLstUsgCd: '', mclDspslGdsLstUsgCd: '', sclDspslGdsLstUsgCd: '',
      cortAuctnMbrsId: '', aeeEvlAmtMin: '', aeeEvlAmtMax: '',
      lwsDspslPrcRateMin: '', lwsDspslPrcRateMax: '',
      flbdNcntMin: '', flbdNcntMax: '', objctArDtsMin: '', objctArDtsMax: '',
      lafjOrderBy: '', pgmId: 'PGJ151F01', csNo: '',
      cortStDvs: '1', statNum: 1,
      bidBgngYmd: '', bidEndYmd: '', dspslDxdyYmd: '', sideDvsCd: '',
    },
  };

  const resp = await fetch(SEARCH_URL, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json, text/plain, */*',
      'Accept-Language': 'ko-KR,ko;q=0.9',
      'Origin': COURT_BASE, 'Referer': PAGE_URL,
      'User-Agent': UA, 'Cookie': cookies,
    },
    body: JSON.stringify(body),
  });

  const data = await resp.json();
  if (data?.data?.ipcheck === false) return { items: [], total: 0, blocked: true };
  if (data?.status !== 200) return { items: [], total: 0 };

  const items = data.data?.dlt_srchResult ?? [];
  const total = parseInt(data.data?.dma_pageInfo?.totalCnt ?? 0) || 0;
  return { items, total };
}

/* ── 지오코딩 헬퍼 ── */
function _needsGeocode(item) {
  const lat = item.lat, lng = item.lng;
  if (lat == null || lng == null) return true;
  const ld = String(lat).includes('.') ? String(lat).split('.')[1].length : 0;
  const rd = String(lng).includes('.') ? String(lng).split('.')[1].length : 0;
  return ld < 3 || rd < 3;
}

function _cleanAddress(address) {
  return address.replace(/\s*\(.*?\)\s*$/, '').trim();
}

async function _kakaoGeocode(address, apiKey) {
  const base = _cleanAddress(address);

  // 건물명이 있으면 keyword search 우선 — 필지 중심점 대신 건물 POI 좌표를 반환해 아파트 정확도 ↑
  const bm = address.match(/\(([^)]+)\)/);
  if (bm) {
    const keyword = `${base} ${bm[1].trim()}`;
    try {
      const kr = await fetch(
        `https://dapi.kakao.com/v2/local/search/keyword.json?query=${encodeURIComponent(keyword)}&size=1`,
        { headers: { Authorization: `KakaoAK ${apiKey}` } }
      );
      if (kr.ok) {
        const docs = (await kr.json()).documents;
        if (docs?.length) return { lat: parseFloat(docs[0].y), lng: parseFloat(docs[0].x) };
      }
    } catch {}
  }

  // fallback: address search (토지·상업용 등 건물명 없는 경우)
  const url = `https://dapi.kakao.com/v2/local/search/address.json?query=${encodeURIComponent(base)}&size=1`;
  try {
    const resp = await fetch(url, { headers: { Authorization: `KakaoAK ${apiKey}` } });
    if (!resp.ok) return null;
    const docs = (await resp.json()).documents;
    if (!docs?.length) return null;
    return { lat: parseFloat(docs[0].y), lng: parseFloat(docs[0].x) };
  } catch { return null; }
}

// 소수점 4자리 미만 or 정수값(법원 기본 "37.0000") = 법원/지역 수준 좌표 → null 처리
function preciseCoord(s) {
  if (!s) return null;
  const str = String(s).trim();
  const dot = str.indexOf('.');
  if (dot < 0 || str.length - dot - 1 < 4) return null;
  const v = parseFloat(str);
  if (Number.isInteger(v)) return null; // "37.0000" → 정수 → 법원 기본값 제거
  return v;
}

/* ── 아이템 파싱 ── */
function parseItem(item) {
  const sido  = item.hjguSido  || item.bgPlaceSido  || '';
  const sigu  = item.hjguSigu  || item.bgPlaceSigu  || '';
  const dong  = item.hjguDong  || item.bgPlaceDong  || '';
  const lotno = item.daepyoLotno || '';
  const buld  = item.buldNm || '';
  const buildL = item.buldList || '';
  let address = [sido, sigu, dong, lotno].filter(Boolean).join(' ');
  if (buld) address += ` (${buld}${buildL ? ' ' + buildL : ''})`;

  const mc = item.mclsUtilCd || '';
  const lc = item.lclsUtilCd || '';
  const type =
    mc === '20400' ? 'house' :
    ['20500','20600','20700'].includes(mc) ? 'commercial' :
    ['20200','20300'].includes(mc) ? 'apartment' :
    lc === '10000' ? 'land' : 'other';

  const toDate = s => s && s.length === 8 ? `${s.slice(0,4)}-${s.slice(4,6)}-${s.slice(6)}` : null;
  const app  = parseInt(item.gamevalAmt  || 0) || 0;
  const minP = parseInt(item.minmaePrice || 0) || 0;
  const fc   = parseInt(item.yuchalCnt  || 0) || 0;

  return {
    id:          item.srnSaNo || '',
    case_number: item.srnSaNo || '',
    court:       item.jiwonNm || '',
    type, sido, gu: sigu, dong, address,
    lat: preciseCoord(item.wgs84Ycordi),
    lng: preciseCoord(item.wgs84Xcordi),
    area: parseFloat(item.objctAr || item.objctArDts || '') || null,
    floor: null, yr: null,
    app, minP,
    avgT: app ? Math.round(app * 1.15 / 500000) * 500000 : 0,
    fc,
    bid_date: toDate(item.maeGiil),
    pred: Math.round(Math.max(55, Math.min(95, (minP / (app || 1)) * 100 - fc * 3))),
    detail_url: item.docid
      ? `${COURT_BASE}/pgj/index.on?w2xPath=/pgj/ui/pgj100/PGJ151F02.xml&docid=${item.docid}`
      : '',
    is_real: true,
  };
}

/* ── 크롤 실행 (ctx.waitUntil에서 호출) ── */
async function doCrawl(env, tenant, maxItems) {
  const metaKey = `meta:${tenant}`;
  const dataKey = `data:${tenant}`;

  try {
    // 현재 meta 확인 → next_page 이어서 수집
    const prevMetaRaw = await env.AUCTION_DATA.get(metaKey);
    const prevMeta = prevMetaRaw ? JSON.parse(prevMetaRaw) : {};
    const startPage = prevMeta.next_page || 1;
    // startPage가 1이어도 기존 데이터를 유지 — 재시작 시 전체 데이터 유실 방지
    const prevItems = JSON.parse(await env.AUCTION_DATA.get(dataKey) || '{"items":[]}').items;

    // 상태 업데이트
    await env.AUCTION_DATA.put(metaKey, JSON.stringify({
      ...prevMeta,
      status: 'crawling',
      started_at: new Date().toISOString(),
      next_page: startPage,
    }));

    const cookies = await getSessionCookies();
    const pageSize = 20;
    const newItems = [];
    let totalCount = 0;
    let currentPage = startPage;
    const maxPages = Math.ceil(maxItems / pageSize);

    for (let i = 0; i < maxPages; i++) {
      const { items, total, blocked } = await fetchCourtPage(cookies, currentPage, pageSize);
      if (blocked) throw new Error('IP_BLOCKED');
      if (!items.length) break;
      if (currentPage === startPage) totalCount = total;
      newItems.push(...items.map(parseItem));
      currentPage++;
      if (newItems.length >= maxItems) break;
      await new Promise(r => setTimeout(r, 400)); // rate limit
    }

    // 사건번호(id) 기준 중복 제거 — prevItems + 동일 배치 내 중복 모두 처리
    const seen = new Set(prevItems.map(i => i.id).filter(Boolean));
    const uniqueNew = newItems.filter(i => {
      if (!i.id || seen.has(i.id)) return false;
      seen.add(i.id);
      return true;
    });
    const allItems = [...prevItems, ...uniqueNew];
    const hasMore = totalCount > allItems.length;
    const payload = {
      generated_at: new Date().toISOString(),
      count: allItems.length,
      total_available: totalCount,
      items: allItems,
    };

    await env.AUCTION_DATA.put(dataKey, JSON.stringify(payload));
    await env.AUCTION_DATA.put(metaKey, JSON.stringify({
      status: 'done',
      started_at: prevMeta.started_at || new Date().toISOString(),
      finished_at: new Date().toISOString(),
      count: allItems.length,
      total_available: totalCount,
      next_page: hasMore ? currentPage : 1, // 다음 수집 시 이어서 or 처음부터
      has_more: hasMore,
    }));
  } catch (err) {
    const prevMetaRaw = await env.AUCTION_DATA.get(metaKey);
    const prevMeta = prevMetaRaw ? JSON.parse(prevMetaRaw) : {};
    await env.AUCTION_DATA.put(metaKey, JSON.stringify({
      ...prevMeta,
      status: 'error',
      error: err.message,
      finished_at: new Date().toISOString(),
    }));
  }
}

/* ── 메인 핸들러 ── */
export default {
  async fetch(request, env, ctx) {
    const url    = new URL(request.url);
    const tenant = url.searchParams.get('tenant') || 'default';
    const method = request.method;

    if (method === 'OPTIONS') return new Response(null, { status: 204, headers: CORS_HEADERS });

    // ── GET /health ──
    if (url.pathname === '/health') {
      const kvOk = !!env.AUCTION_DATA;
      return jsonResp({ ok: true, kv: kvOk, ts: Date.now() });
    }

    // ── GET /data?tenant=X ── (공개)
    if (url.pathname === '/data' && method === 'GET') {
      if (!env.AUCTION_DATA) return jsonResp({ error: 'KV not configured' }, 503);
      const raw = await env.AUCTION_DATA.get(`data:${tenant}`);
      if (!raw) return jsonResp({ count: 0, items: [], message: 'No data yet. Run /crawl first.' });
      return new Response(raw, {
        headers: { 'Content-Type': 'application/json; charset=utf-8', ...CORS_HEADERS },
      });
    }

    // ── GET /status?tenant=X ── (공개)
    if (url.pathname === '/status' && method === 'GET') {
      if (!env.AUCTION_DATA) return jsonResp({ error: 'KV not configured' }, 503);
      const raw = await env.AUCTION_DATA.get(`meta:${tenant}`);
      const meta = raw ? JSON.parse(raw) : { status: 'idle' };
      return jsonResp(meta);
    }

    // ── POST /crawl?tenant=X&max=200 ── (인증 불필요)
    if (url.pathname === '/crawl' && method === 'POST') {
      if (!env.AUCTION_DATA) return jsonResp({ error: 'KV not configured. Add AUCTION_DATA KV binding.' }, 503);

      // 이미 수집 중이면 거부
      const metaRaw = await env.AUCTION_DATA.get(`meta:${tenant}`);
      const meta = metaRaw ? JSON.parse(metaRaw) : {};
      if (meta.status === 'crawling') {
        return jsonResp({ status: 'crawling', message: '이미 수집 중입니다.' });
      }

      const maxItems = parseInt(url.searchParams.get('max') || '200');

      // 비동기 크롤 시작 (응답은 즉시 반환)
      ctx.waitUntil(doCrawl(env, tenant, maxItems));

      return jsonResp({ status: 'started', tenant, max: maxItems });
    }

    // ── GET /geocode-data?tenant=X ── Worker KV 지오코딩 오버레이 조회 (공개)
    if (url.pathname === '/geocode-data' && method === 'GET') {
      if (!env.AUCTION_DATA) return jsonResp({ error: 'KV not configured' }, 503);
      const raw = await env.AUCTION_DATA.get(`geocode:${tenant}`);
      if (!raw) return jsonResp({});
      return new Response(raw, {
        headers: { 'Content-Type': 'application/json; charset=utf-8', ...CORS_HEADERS },
      });
    }

    // ── POST /geocode?tenant=X&max=50 ── 카카오 API 지오코딩 배치 (관리자 전용)
    if (url.pathname === '/geocode' && method === 'POST') {
      if (!env.AUCTION_DATA) return jsonResp({ error: 'KV not configured' }, 503);
      const apiKey = env.KAKAO_API_KEY;
      if (!apiKey) return jsonResp({ error: 'KAKAO_API_KEY not set in Worker environment variables' }, 500);

      const max   = Math.min(parseInt(url.searchParams.get('max')   || '50'), 200);
      const force = url.searchParams.get('force') === '1';

      const dataRaw = await env.AUCTION_DATA.get(`data:${tenant}`);
      if (!dataRaw) return jsonResp({ error: 'No data. Run /crawl first.' }, 404);
      const items = JSON.parse(dataRaw).items || [];

      const overlayRaw = await env.AUCTION_DATA.get(`geocode:${tenant}`);
      const overlay = overlayRaw ? JSON.parse(overlayRaw) : {};

      const need = items.filter(it => it.address && (_needsGeocode(it) || force) && (!overlay[it.case_number] || force));
      const batch = need.slice(0, max);

      let ok = 0, fail = 0;
      for (const item of batch) {
        const result = await _kakaoGeocode(item.address, apiKey);
        if (result) { overlay[item.case_number] = result; ok++; }
        else fail++;
        await new Promise(r => setTimeout(r, 120)); // 카카오 API 속도 제한 준수
      }

      if (ok > 0) {
        await env.AUCTION_DATA.put(`geocode:${tenant}`, JSON.stringify(overlay));
      }

      const remaining = items.filter(it => it.address && _needsGeocode(it) && !overlay[it.case_number]).length;
      return jsonResp({ processed: batch.length, success: ok, fail, total_coverage: Object.keys(overlay).length, remaining });
    }


    // ── POST /reset?tenant=X ── (관리자 전용)
    if (url.pathname === '/reset' && method === 'POST') {
      if (!checkAuth(request, env)) return jsonResp({ error: 'Unauthorized' }, 401);
      if (!env.AUCTION_DATA) return jsonResp({ error: 'KV not configured' }, 503);
      await env.AUCTION_DATA.delete(`data:${tenant}`);
      await env.AUCTION_DATA.delete(`meta:${tenant}`);
      return jsonResp({ status: 'reset', tenant });
    }

    return jsonResp({ error: 'Not found' }, 404);
  },

  /* ── Cron Trigger 핸들러 ── */
  async scheduled(event, env, ctx) {
    const tenant = 'worksfree';

    // 주간 리셋: 매주 월요일 03:00 KST (= 일요일 18:00 UTC)
    // → 법원 데이터는 upcoming 경매만 반환하므로 완전 재수집이 가장 깔끔함
    if (event.cron === '0 18 * * SUN') {
      await env.AUCTION_DATA.delete(`data:${tenant}`);
      await env.AUCTION_DATA.delete(`meta:${tenant}`);
      ctx.waitUntil(doCrawl(env, tenant, 500));
      return;
    }

    // 시간별: 수집이 남아있을 때만 실행
    const metaRaw = await env.AUCTION_DATA.get(`meta:${tenant}`);
    const meta = metaRaw ? JSON.parse(metaRaw) : {};

    // stale 크롤 처리: 2시간 이상 crawling 상태 = 타임아웃으로 간주 → 재시작
    if (meta.status === 'crawling') {
      const age = Date.now() - new Date(meta.started_at || 0).getTime();
      if (age < 2 * 3600000) return; // 아직 진행 중
      await env.AUCTION_DATA.put(`meta:${tenant}`, JSON.stringify({
        ...meta, status: 'error', error: 'timeout_stale',
        finished_at: new Date().toISOString(),
      }));
    }

    // 미수집 or 에러 or has_more → 이어서 수집
    const needsCrawl = !meta.status
      || meta.status === 'error'
      || (meta.status === 'done' && meta.has_more);

    if (needsCrawl) {
      ctx.waitUntil(doCrawl(env, tenant, 500));
    }
    // status==='done' && !has_more → 전체 수집 완료, 주간 크론까지 대기
  },
};
