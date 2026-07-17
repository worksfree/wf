/**
 * Cloudflare Worker — 법원경매 크롤러 (Supabase 버전)
 *
 * Worker Secrets (Settings → Variables → Encrypt):
 *   SUPABASE_URL         Supabase 프로젝트 URL (예: https://xxx.supabase.co)
 *   SUPABASE_SERVICE_KEY Supabase service_role 키
 *   PROXY_SECRET         관리자 API 보호용 (옵션)
 *   KAKAO_API_KEY        지오코딩 Kakao REST API 키
 *
 * KV 바인딩: 더 이상 사용하지 않음 (wrangler.toml에서 제거 가능)
 *
 * 엔드포인트:
 *   GET  /health               동작 확인
 *   GET  /data?tenant=X        데이터 조회 (Supabase에서 직접 로드)
 *   GET  /status?tenant=X      수집 상태 조회
 *   POST /crawl?tenant=X       수집 실행
 *   POST /geocode?tenant=X&max=50&force=0  지오코딩 배치
 *   POST /reset?tenant=X       데이터 초기화 (PROXY_SECRET 필요)
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

const jsonResp = (data, status = 200) =>
  new Response(JSON.stringify(data, null, 0), {
    status,
    headers: { 'Content-Type': 'application/json; charset=utf-8', ...CORS_HEADERS },
  });

function checkAuth(request, env) {
  const secret = env.PROXY_SECRET;
  if (!secret) return true;
  return request.headers.get('X-Proxy-Secret') === secret;
}

/* ══════════════════════════════════════
   Supabase REST API 헬퍼
══════════════════════════════════════ */

function sbBase(env) { return `${env.SUPABASE_URL}/rest/v1`; }

function sbHeaders(env, extra = {}) {
  return {
    'Content-Type': 'application/json',
    'apikey': env.SUPABASE_SERVICE_KEY,
    'Authorization': `Bearer ${env.SUPABASE_SERVICE_KEY}`,
    ...extra,
  };
}

/** auction_meta 조회 */
async function sbGetMeta(env, tenant) {
  const r = await fetch(
    `${sbBase(env)}/auction_meta?tenant_id=eq.${encodeURIComponent(tenant)}&select=*`,
    { headers: sbHeaders(env) }
  );
  if (!r.ok) return {};
  const rows = await r.json();
  return rows[0] || {};
}

/** auction_meta upsert */
async function sbUpsertMeta(env, tenant, data) {
  const r = await fetch(`${sbBase(env)}/auction_meta`, {
    method: 'POST',
    headers: sbHeaders(env, { 'Prefer': 'resolution=merge-duplicates,return=minimal' }),
    body: JSON.stringify({ tenant_id: tenant, ...data, updated_at: new Date().toISOString() }),
  });
  if (!r.ok) throw new Error(`sbUpsertMeta: ${r.status} ${await r.text()}`);
}

/** auction_items upsert (배치) */
async function sbUpsertItems(env, rows) {
  if (!rows.length) return;
  const r = await fetch(`${sbBase(env)}/auction_items`, {
    method: 'POST',
    headers: sbHeaders(env, { 'Prefer': 'resolution=merge-duplicates,return=minimal' }),
    body: JSON.stringify(rows),
  });
  if (!r.ok) throw new Error(`sbUpsertItems: ${r.status} ${await r.text()}`);
}

/** auction_items 건수 조회 (Content-Range 헤더 이용) */
async function sbCountItems(env, tenant, extra = '') {
  const r = await fetch(
    `${sbBase(env)}/auction_items?tenant_id=eq.${encodeURIComponent(tenant)}${extra}&select=id`,
    { headers: sbHeaders(env, { 'Prefer': 'count=exact', 'Range': '0-0', 'Range-Unit': 'items' }) }
  );
  const cr = r.headers.get('Content-Range');
  if (!cr) return 0;
  const total = cr.split('/')[1];
  return total ? parseInt(total) : 0;
}

/** auction_items 전체 조회 (1000건씩 페이지네이션) */
async function sbFetchAllItems(env, tenant, fields = '*') {
  const items = [];
  let from = 0;
  const PAGE = 1000;
  while (true) {
    const r = await fetch(
      `${sbBase(env)}/auction_items?tenant_id=eq.${encodeURIComponent(tenant)}&select=${encodeURIComponent(fields)}&order=created_at.asc`,
      { headers: sbHeaders(env, { 'Range': `${from}-${from + PAGE - 1}`, 'Range-Unit': 'items' }) }
    );
    if (r.status === 416) break;  // out of range
    if (!r.ok) throw new Error(`sbFetchAllItems: ${r.status}`);
    const data = await r.json();
    if (!data?.length) break;
    items.push(...data);
    if (data.length < PAGE) break;
    from += PAGE;
  }
  return items;
}

/** 지오코딩 필요 항목 조회 */
async function sbFetchNeedGeocode(env, tenant, limit = 50, force = false) {
  const filter = force
    ? `&address=not.is.null`
    : `&lat=is.null&address=not.is.null`;
  const r = await fetch(
    `${sbBase(env)}/auction_items?tenant_id=eq.${encodeURIComponent(tenant)}${filter}&select=id,case_number,address&limit=${limit}&order=created_at.asc`,
    { headers: sbHeaders(env) }
  );
  if (!r.ok) throw new Error(`sbFetchNeedGeocode: ${r.status}`);
  return r.json();
}

/** 단건 좌표 업데이트 */
async function sbUpdateGeocode(env, tenant, id, lat, lng) {
  const r = await fetch(
    `${sbBase(env)}/auction_items?id=eq.${encodeURIComponent(id)}&tenant_id=eq.${encodeURIComponent(tenant)}`,
    {
      method: 'PATCH',
      headers: sbHeaders(env, { 'Prefer': 'return=minimal' }),
      body: JSON.stringify({ lat, lng, geocoded_at: new Date().toISOString(), updated_at: new Date().toISOString() }),
    }
  );
  if (!r.ok) throw new Error(`sbUpdateGeocode: ${r.status}`);
}

/** auction_items 전체 삭제 */
async function sbDeleteAllItems(env, tenant) {
  const r = await fetch(
    `${sbBase(env)}/auction_items?tenant_id=eq.${encodeURIComponent(tenant)}`,
    { method: 'DELETE', headers: sbHeaders(env) }
  );
  if (!r.ok) throw new Error(`sbDeleteAllItems: ${r.status}`);
}

/* ══════════════════════════════════════
   법원경매 API
══════════════════════════════════════ */

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

/* ══════════════════════════════════════
   지오코딩
══════════════════════════════════════ */

function _cleanAddress(address) {
  return address.replace(/\s*\(.*?\)\s*$/, '').trim();
}

async function _kakaoGeocode(address, apiKey) {
  const base = _cleanAddress(address);

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

  try {
    const resp = await fetch(
      `https://dapi.kakao.com/v2/local/search/address.json?query=${encodeURIComponent(base)}&size=1`,
      { headers: { Authorization: `KakaoAK ${apiKey}` } }
    );
    if (!resp.ok) return null;
    const docs = (await resp.json()).documents;
    if (!docs?.length) return null;
    return { lat: parseFloat(docs[0].y), lng: parseFloat(docs[0].x) };
  } catch { return null; }
}

/* ══════════════════════════════════════
   아이템 파싱 (Supabase 컬럼명 snake_case)
══════════════════════════════════════ */

function preciseCoord(s) {
  if (!s) return null;
  const str = String(s).trim();
  const dot = str.indexOf('.');
  if (dot < 0 || str.length - dot - 1 < 4) return null;
  const v = parseFloat(str);
  if (Number.isInteger(v)) return null;
  return v;
}

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
  const min_p = parseInt(item.minmaePrice || 0) || 0;
  const fc   = parseInt(item.yuchalCnt  || 0) || 0;

  return {
    id:          item.srnSaNo || '',
    case_number: item.srnSaNo || '',
    court:       item.jiwonNm || '',
    type, sido, gu: sigu, dong, address,
    lat: preciseCoord(item.wgs84Ycordi),
    lng: preciseCoord(item.wgs84Xcordi),
    area: parseFloat(item.objctAr || item.objctArDts || '') || null,
    app, min_p,
    avg_t: app ? Math.round(app * 1.15 / 500000) * 500000 : 0,
    fc,
    bid_date: toDate(item.maeGiil),
    pred: Math.round(Math.max(55, Math.min(95, (min_p / (app || 1)) * 100 - fc * 3))),
    detail_url: item.docid
      ? `${COURT_BASE}/pgj/index.on?w2xPath=/pgj/ui/pgj100/PGJ151F02.xml&docid=${item.docid}`
      : '',
    is_real: true,
  };
}

/* ══════════════════════════════════════
   크롤 실행
══════════════════════════════════════ */

async function doCrawl(env, tenant, maxItems) {
  if (!env.SUPABASE_URL || !env.SUPABASE_SERVICE_KEY) {
    console.error('doCrawl: SUPABASE_URL/SUPABASE_SERVICE_KEY 미설정');
    return;
  }

  try {
    // 현재 meta에서 next_page 확인
    const prevMeta = await sbGetMeta(env, tenant);
    const startPage = prevMeta.next_page || 1;

    await sbUpsertMeta(env, tenant, {
      status: 'crawling',
      started_at: prevMeta.started_at || new Date().toISOString(),
      next_page: startPage,
      count: prevMeta.count || 0,
      error: null,
    });

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
      if (i === 0) totalCount = total;
      newItems.push(...items.map(parseItem));
      currentPage++;
      if (newItems.length >= maxItems) break;
      await new Promise(r => setTimeout(r, 400));
    }

    // 배치 내 중복 제거 — 법원 API가 동일 사건번호를 여러 페이지에 반환할 수 있음
    const seen = new Set();
    const uniqueItems = newItems.filter(it => {
      if (!it.id || seen.has(it.id)) return false;
      seen.add(it.id);
      return true;
    });

    // Supabase upsert (500건씩 배치)
    const BATCH = 500;
    for (let i = 0; i < uniqueItems.length; i += BATCH) {
      const batch = uniqueItems.slice(i, i + BATCH).map(it => ({ ...it, tenant_id: tenant }));
      await sbUpsertItems(env, batch);
    }

    // 실제 DB 건수 조회 (upsert 후 최신 상태)
    const actualCount = await sbCountItems(env, tenant);
    const hasMore = totalCount > actualCount;

    await sbUpsertMeta(env, tenant, {
      status: 'done',
      started_at: prevMeta.started_at || new Date().toISOString(),
      finished_at: new Date().toISOString(),
      generated_at: new Date().toISOString(),
      count: actualCount,
      total_available: totalCount,
      next_page: hasMore ? currentPage : 1,
      has_more: hasMore,
      error: null,
    });

  } catch (err) {
    try {
      const prevMeta = await sbGetMeta(env, tenant);
      await sbUpsertMeta(env, tenant, {
        ...prevMeta,
        status: 'error',
        error: err.message,
        finished_at: new Date().toISOString(),
      });
    } catch {}
  }
}

/* ══════════════════════════════════════
   메인 핸들러
══════════════════════════════════════ */

export default {
  async fetch(request, env, ctx) {
    const url    = new URL(request.url);
    const tenant = url.searchParams.get('tenant') || 'default';
    const method = request.method;

    if (method === 'OPTIONS') return new Response(null, { status: 204, headers: CORS_HEADERS });

    if (!env.SUPABASE_URL || !env.SUPABASE_SERVICE_KEY) {
      if (url.pathname !== '/health') {
        return jsonResp({ error: 'SUPABASE_URL / SUPABASE_SERVICE_KEY not configured in Worker secrets' }, 503);
      }
    }

    // ── GET /health ──
    if (url.pathname === '/health') {
      return jsonResp({
        ok: true,
        supabase: !!(env.SUPABASE_URL && env.SUPABASE_SERVICE_KEY),
        ts: Date.now(),
      });
    }

    // ── GET /data?tenant=X ── Supabase에서 전체 아이템 반환
    if (url.pathname === '/data' && method === 'GET') {
      const meta  = await sbGetMeta(env, tenant);
      const items = await sbFetchAllItems(env, tenant);
      return jsonResp({
        generated_at:    meta.generated_at || meta.finished_at || new Date().toISOString(),
        count:           items.length,
        total_available: meta.total_available || items.length,
        items,
      });
    }

    // ── GET /status?tenant=X ──
    if (url.pathname === '/status' && method === 'GET') {
      const meta = await sbGetMeta(env, tenant);
      return jsonResp(Object.keys(meta).length ? meta : { status: 'idle', tenant_id: tenant });
    }

    // ── POST /crawl?tenant=X&max=200 ──
    if (url.pathname === '/crawl' && method === 'POST') {
      const meta = await sbGetMeta(env, tenant);
      if (meta.status === 'crawling') {
        return jsonResp({ status: 'crawling', message: '이미 수집 중입니다.' });
      }
      const maxItems = parseInt(url.searchParams.get('max') || '200');
      ctx.waitUntil(doCrawl(env, tenant, maxItems));
      return jsonResp({ status: 'started', tenant, max: maxItems });
    }

    // ── POST /geocode?tenant=X&max=50&force=0 ── (지오코딩 배치)
    if (url.pathname === '/geocode' && method === 'POST') {
      const apiKey = env.KAKAO_API_KEY;
      if (!apiKey) return jsonResp({ error: 'KAKAO_API_KEY not configured' }, 500);

      const max   = Math.min(parseInt(url.searchParams.get('max')   || '50'), 200);
      const force = url.searchParams.get('force') === '1';

      const need = await sbFetchNeedGeocode(env, tenant, max, force);

      let ok = 0, fail = 0;
      for (const item of need) {
        const result = await _kakaoGeocode(item.address, apiKey);
        if (result) {
          await sbUpdateGeocode(env, tenant, item.id, result.lat, result.lng);
          ok++;
        } else {
          fail++;
        }
        await new Promise(r => setTimeout(r, 120));
      }

      // 커버리지 통계
      const total_coverage = await sbCountItems(env, tenant, '&lat=not.is.null');
      const remaining      = await sbCountItems(env, tenant, '&lat=is.null&address=not.is.null');

      return jsonResp({ processed: need.length, success: ok, fail, total_coverage, remaining });
    }

    // ── GET /geocode-data ── deprecated, 빈 객체 반환 (프론트는 Supabase에서 직접 읽음)
    if (url.pathname === '/geocode-data' && method === 'GET') {
      return jsonResp({});
    }

    // ── POST /reset?tenant=X ── (관리자 전용)
    if (url.pathname === '/reset' && method === 'POST') {
      if (!checkAuth(request, env)) return jsonResp({ error: 'Unauthorized' }, 401);
      await sbDeleteAllItems(env, tenant);
      await sbUpsertMeta(env, tenant, {
        status: 'idle', next_page: 1, count: 0, total_available: 0,
        has_more: false, started_at: null, finished_at: null, generated_at: null, error: null,
      });
      return jsonResp({ status: 'reset', tenant });
    }

    return jsonResp({ error: 'Not found' }, 404);
  },

  /* ── Cron Trigger 핸들러 ── */
  async scheduled(event, env, ctx) {
    if (!env.SUPABASE_URL || !env.SUPABASE_SERVICE_KEY) return;

    const tenant = 'worksfree';

    // 주간 리셋: 매주 월요일 03:00 KST (= 일요일 18:00 UTC)
    if (event.cron === '0 18 * * SUN') {
      await sbDeleteAllItems(env, tenant);
      await sbUpsertMeta(env, tenant, {
        status: 'idle', next_page: 1, count: 0, total_available: 0,
        has_more: false, started_at: null, finished_at: null, generated_at: null, error: null,
      });
      ctx.waitUntil(doCrawl(env, tenant, 500));
      return;
    }

    // 시간별: stale 크롤 처리 + 이어서 수집
    const meta = await sbGetMeta(env, tenant);

    if (meta.status === 'crawling') {
      const age = Date.now() - new Date(meta.started_at || 0).getTime();
      if (age < 2 * 3600000) return;  // 아직 진행 중
      await sbUpsertMeta(env, tenant, {
        ...meta, status: 'error', error: 'timeout_stale',
        finished_at: new Date().toISOString(),
      });
    }

    const needsCrawl = !meta.status
      || meta.status === 'error'
      || (meta.status === 'done' && meta.has_more);

    if (needsCrawl) ctx.waitUntil(doCrawl(env, tenant, 500));
  },
};
