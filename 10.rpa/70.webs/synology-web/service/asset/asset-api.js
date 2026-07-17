/**
 * Cloudflare Worker — 자산관리 API (asset-api)
 *
 * 배포: wrangler deploy --config wrangler-asset.toml
 *
 * Endpoints:
 *   GET /search?q=삼성전자              → 종목 검색
 *   GET /quote?code=005930             → 단일 종목 시세
 *   GET /quotes?codes=005930,069500    → 다중 종목 시세
 *   GET /debug?code=005930             → raw Naver 응답 (디버그)
 *   GET /debug-search?q=삼성전자       → 검색 API raw 응답 (디버그)
 */

const CORS = {
  'Access-Control-Allow-Origin':  '*',
  'Access-Control-Allow-Methods': 'GET, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type',
};

const NAVER_HDRS = {
  'Referer':    'https://finance.naver.com/',
  'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36',
  'Accept':     'application/json, text/javascript, */*',
};
const DAUM_HDRS = {
  'Referer':    'https://finance.daum.net/',
  'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36',
  'Accept':     'application/json, text/plain, */*',
};

export default {
  async fetch(request) {
    if (request.method === 'OPTIONS') return new Response(null, { headers: CORS });

    const url  = new URL(request.url);
    const path = url.pathname;

    try {
      if (path === '/search')           return await handleSearch(url);
      if (path === '/quote')            return await handleQuote(url);
      if (path === '/quotes')           return await handleQuotes(url);
      if (path === '/dividends')        return await handleDividends(url);
      if (path === '/debug')            return await handleDebug(url);
      if (path === '/debug-search')     return await handleDebugSearch(url);
      if (path === '/debug-dividends')  return await handleDebugDividends(url);
      return new Response('asset-api OK', { headers: CORS });
    } catch (e) {
      return jsonRes({ error: e.message }, 500);
    }
  },
};

// ── /debug-search ─────────────────────────────────────────────────────────
async function handleDebugSearch(url) {
  const q = (url.searchParams.get('q') || '삼성전자').trim();
  const results = { query: q };

  // 1. ac.finance.naver.com
  try {
    const u = `https://ac.finance.naver.com/ac?q=${encodeURIComponent(q)}&q_enc=UTF-8&st=111&r_format=json&r_enc=UTF-8&r_lt=111&r_unicode=0&r_escape=1`;
    const res = await fetch(u, { headers: NAVER_HDRS });
    const text = await res.text();
    results.ac = { status: res.status, contentType: res.headers.get('content-type'), raw: text.slice(0, 800) };
  } catch (e) { results.ac = { error: e.message }; }

  // 2. m.stock.naver.com autoComplete
  try {
    const u = `https://m.stock.naver.com/api/search/autoComplete?query=${encodeURIComponent(q)}&target=stock,etf`;
    const res = await fetch(u, { headers: NAVER_HDRS });
    const text = await res.text();
    results.mstock = { status: res.status, contentType: res.headers.get('content-type'), raw: text.slice(0, 800) };
  } catch (e) { results.mstock = { error: e.message }; }

  // 3. finance.daum.net (새 검색 소스)
  try {
    const u = `https://finance.daum.net/api/search?q=${encodeURIComponent(q)}`;
    const res = await fetch(u, { headers: DAUM_HDRS });
    const text = await res.text();
    results.daum = { status: res.status, contentType: res.headers.get('content-type'), raw: text.slice(0, 600) };
  } catch (e) { results.daum = { error: e.message }; }

  return jsonRes(results);
}

// ── /search ────────────────────────────────────────────────────────────────
async function handleSearch(url) {
  const q = (url.searchParams.get('q') || '').trim();
  if (!q) return jsonRes([]);

  // 1차: 다음(카카오) 증권 검색 API — 한글 종목명 지원, 안정적
  try {
    const res  = await fetch(
      `https://finance.daum.net/api/search?q=${encodeURIComponent(q)}`,
      { headers: DAUM_HDRS }
    );
    const text = await res.text();
    const body = JSON.parse(text);
    const items = body?.suggestItems ?? [];
    if (items.length > 0) {
      const out = items.slice(0, 20).map(item => {
        const code   = item.displayedCode ?? '';
        const name   = item.koreanName    ?? '';
        // symbolCode 접두사: A=유가(KOSPI), Q=코스닥(KOSDAQ)
        const prefix = String(item.symbolCode ?? '').charAt(0).toUpperCase();
        const market = prefix === 'Q' ? 'KOSDAQ' : 'KOSPI';
        const nameU  = name.toUpperCase();
        const kind   = (nameU.includes('KODEX') || nameU.includes('TIGER') ||
                        nameU.includes('RISE')  || nameU.includes('ACE')   ||
                        nameU.includes('KBSTAR')|| nameU.includes('HANARO')||
                        nameU.includes('ETF'))
                       ? 'ETF' : 'STOCK';
        return { code, name, kind, market };
      }).filter(r => r.code && r.name);
      if (out.length > 0) return jsonRes(out);
    }
  } catch (e) { /* Daum 실패 시 2차로 */ }

  // 2차: Naver 검색 (혹시 복구된 경우 대비)
  try {
    const res  = await fetch(
      `https://m.stock.naver.com/api/search/autoComplete?query=${encodeURIComponent(q)}&target=stock,etf`,
      { headers: NAVER_HDRS }
    );
    const text = await res.text();
    if (text.trim().startsWith('{')) {
      const body  = JSON.parse(text);
      const items = body?.result?.d ?? [];
      if (items.length > 0) {
        return jsonRes(items.slice(0, 20).map(item => ({
          code:   item.code,
          name:   item.name,
          kind:   item.typeCode === 'STOCK' ? 'STOCK' : 'ETF',
          market: normalizeMarket(item.marketName ?? item.stockExchangeType?.code ?? ''),
        })));
      }
    }
  } catch (_) {}

  return jsonRes([]);
}

// ── /quote ─────────────────────────────────────────────────────────────────
async function handleQuote(url) {
  const code = (url.searchParams.get('code') || '').trim();
  if (!code) return jsonRes({ error: 'code required' }, 400);
  return jsonRes(await fetchSingleQuote(code));
}

// ── /quotes ────────────────────────────────────────────────────────────────
async function handleQuotes(url) {
  const codes = (url.searchParams.get('codes') || '')
    .split(',').map(s => s.trim()).filter(Boolean);
  if (!codes.length) return jsonRes([]);
  return jsonRes(await Promise.all(codes.map(fetchSingleQuote)));
}

// ── /debug ─────────────────────────────────────────────────────────────────
async function handleDebug(url) {
  const code = (url.searchParams.get('code') || '').trim();
  if (!code) return jsonRes({ error: 'code required' }, 400);

  const results = {};

  try {
    const res  = await fetch(`https://m.stock.naver.com/api/stock/${code}/basic`, { headers: NAVER_HDRS });
    const data = await res.json();
    results.mstock = { status: res.status, data };
  } catch (e) { results.mstock = { error: e.message }; }

  try {
    const res  = await fetch(`https://api.finance.naver.com/service/itemSummary.nhn?itemcode=${code}`, { headers: { ...NAVER_HDRS, 'Accept': 'application/json' } });
    const text = await res.text();
    results.summary = { status: res.status, raw: text.slice(0, 500) };
  } catch (e) { results.summary = { error: e.message }; }

  return jsonRes(results);
}

// ── /dividends ────────────────────────────────────────────────────────────
// 분배금/배당금 이력 조회
// 응답: { code, payments: [{ date:"2026-06", perShare:65, payDate:"2026-06-25" }] }
async function handleDividends(url) {
  const code = (url.searchParams.get('code') || '').trim();
  if (!code) return jsonRes({ error: 'code required' }, 400);

  // ① Yahoo Finance — events=div (가장 신뢰도 높은 소스)
  try {
    const now    = Math.floor(Date.now() / 1000);
    const ago2yr = now - 730 * 86400;
    const yUrl   = `https://query1.finance.yahoo.com/v8/finance/chart/${code}.KS?period1=${ago2yr}&period2=${now}&interval=1mo&events=div`;
    const res    = await fetch(yUrl, { headers: { 'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json' } });
    if (res.ok) {
      const data   = await res.json();
      const divs   = data?.chart?.result?.[0]?.events?.dividends ?? {};
      const entries = Object.entries(divs);
      if (entries.length > 0) {
        const out = entries.map(([, d]) => {
          const payDate = new Date((d.date || 0) * 1000);
          const ym = `${payDate.getFullYear()}-${String(payDate.getMonth() + 1).padStart(2, '0')}`;
          return { date: ym, payDate: payDate.toISOString().slice(0, 10), perShare: d.amount };
        }).filter(d => d.perShare > 0).sort((a, b) => a.date.localeCompare(b.date));
        if (out.length) return jsonRes({ code, payments: out, source: 'YAHOO' });
      }
    }
  } catch {}

  // ② Naver /api/etf/ 경로 (ETF 전용 — /api/stock/ 와 다른 베이스)
  const naverEtfPaths = [
    `https://m.stock.naver.com/api/etf/${code}/distribution`,
    `https://m.stock.naver.com/api/etf/${code}/distributions?page=1&pageSize=24`,
    `https://m.stock.naver.com/api/etf/${code}/price/distributions?page=1&pageSize=24`,
  ];
  for (const ep of naverEtfPaths) {
    try {
      const res  = await fetch(ep, { headers: NAVER_HDRS });
      if (!res.ok) continue;
      const body = await res.json();
      const list = Array.isArray(body) ? body
                 : (body?.items ?? body?.distributions ?? body?.data ?? body?.list ?? []);
      if (!list.length) continue;
      const out = list.flatMap(d => {
        const rawDate  = d.paymentDate || d.distributionDate || d.exDividendDate
                       || d.stdDate    || d.date             || '';
        const perShare = parseFloat(
          String(d.cashDividend || d.distribution || d.amount
              || d.perShare     || d.distribAmt   || d.divAmt || 0)
          .replace(/,/g, '')
        );
        if (!rawDate || perShare <= 0) return [];
        return [{ date: rawDate.slice(0, 7), payDate: rawDate, perShare }];
      });
      if (out.length) return jsonRes({ code, payments: out, source: 'NAVER_ETF' });
    } catch {}
  }

  // ② Naver /api/stock/ 경로 (기존 ETF 하위 경로 — 구버전 폴백)
  const naverStockPaths = [
    `https://m.stock.naver.com/api/stock/${code}/etf/distribution`,
    `https://m.stock.naver.com/api/stock/${code}/etf/distributions?page=1&pageSize=24`,
    `https://m.stock.naver.com/api/stock/${code}/dividend`,
  ];
  for (const ep of naverStockPaths) {
    try {
      const res  = await fetch(ep, { headers: NAVER_HDRS });
      if (!res.ok) continue;
      const body = await res.json();
      const list = Array.isArray(body) ? body
                 : (body?.items ?? body?.distributions ?? body?.dividends ?? body?.data ?? body?.list ?? []);
      if (!list.length) continue;
      const out = list.flatMap(d => {
        const rawDate  = d.paymentDate || d.distributionDate || d.recordDate
                       || d.stdDate    || d.date             || '';
        const perShare = parseFloat(
          String(d.cashDividend || d.distribution || d.amount
              || d.perShare     || d.distribAmt   || d.divAmt || 0)
          .replace(/,/g, '')
        );
        if (!rawDate || perShare <= 0) return [];
        return [{ date: rawDate.slice(0, 7), payDate: rawDate, perShare }];
      });
      if (out.length) return jsonRes({ code, payments: out, source: 'NAVER_STOCK' });
    } catch {}
  }

  // ③ Daum Finance — 배당/분배금 API (A{code} 형식)
  const daumPaths = [
    `https://finance.daum.net/api/quote/A${code}/dividends`,
    `https://finance.daum.net/api/quote/A${code}/dividend`,
    `https://finance.daum.net/api/quote/A${code}/distributions`,
  ];
  for (const ep of daumPaths) {
    try {
      const res  = await fetch(ep, { headers: DAUM_HDRS });
      if (!res.ok) continue;
      const body = await res.json();
      const list = Array.isArray(body) ? body
                 : (body?.data ?? body?.items ?? body?.dividends ?? body?.distributions ?? []);
      if (!list.length) continue;
      const out = list.flatMap(d => {
        const rawDate  = d.paymentDate || d.stdDt || d.baseDate || d.date || '';
        const perShare = parseFloat(
          String(d.cashDividend || d.distribution || d.amount
              || d.perShare     || d.distribAmt   || 0)
          .replace(/,/g, '')
        );
        if (!rawDate || perShare <= 0) return [];
        const isoDate = rawDate.replace(/\./g, '-').slice(0, 10);
        return [{ date: isoDate.slice(0, 7), payDate: isoDate, perShare }];
      });
      if (out.length) return jsonRes({ code, payments: out, source: 'DAUM' });
    } catch {}
  }

  // ④ KRX 공공데이터 — ETF 분배금 이력 (최종 폴백)
  try {
    const endDd  = new Date().toISOString().slice(0,10).replace(/-/g,'');
    const strtDd = new Date(Date.now() - 730 * 86400000).toISOString().slice(0,10).replace(/-/g,'');
    const krxBody = new URLSearchParams({
      bld:           'dbms/MDC/STAT/standard/MDCSTAT04901',
      indIsuCd:      code,
      strtDd,
      endDd,
      share:         '1',
      money:         '1',
      csvxls_isNo:   'false',
    }).toString();
    const res = await fetch('https://data.krx.co.kr/comm/bldAttendant/getJsonData.cmd', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'Referer':    'https://data.krx.co.kr/',
        'User-Agent': NAVER_HDRS['User-Agent'],
        'Accept':     'application/json',
      },
      body: krxBody,
    });
    if (res.ok) {
      const data = await res.json();
      const list = data?.output ?? data?.OutBlock_1 ?? [];
      const out = list.flatMap(d => {
        const rawDate  = d.DPST_DT || d.PAY_DT || d.STD_DT || '';
        const perShare = parseFloat(String(d.DPST_AMT || d.DIV_AMT || 0).replace(/,/g,''));
        if (!rawDate || perShare <= 0) return [];
        const iso = `${rawDate.slice(0,4)}-${rawDate.slice(4,6)}-${rawDate.slice(6,8)}`;
        return [{ date: iso.slice(0,7), payDate: iso, perShare }];
      });
      if (out.length) return jsonRes({ code, payments: out, source: 'KRX' });
    }
  } catch {}

  return jsonRes({ code, payments: [] });
}

// ── /debug-dividends ───────────────────────────────────────────────────────
// ?code=475720&src=site (site = RISE/KODEX 홈페이지 접근 테스트)
async function handleDebugDividends(url) {
  const code = (url.searchParams.get('code') || '').trim();
  const src  = (url.searchParams.get('src')  || 'site').toLowerCase();
  if (!code) return jsonRes({ error: 'code required' }, 400);

  const UA = NAVER_HDRS['User-Agent'];

  if (src === 'yahoo') {
    try {
      const now = Math.floor(Date.now() / 1000);
      const res = await fetch(
        `https://query1.finance.yahoo.com/v8/finance/chart/${code}.KS?period1=${now-730*86400}&period2=${now}&interval=1mo&events=div`,
        { headers: { 'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json' } }
      );
      const data = await res.json();
      return jsonRes({ status: res.status, events: data?.chart?.result?.[0]?.events ?? null });
    } catch (e) { return jsonRes({ error: String(e) }); }
  }

  // RISE ETF finder 페이지에서 종목코드 → 내부 productId 탐색
  if (src === 'rise_find') {
    const RISE_H = { 'User-Agent': UA, 'Referer': 'https://www.riseetf.co.kr/', 'Accept': 'text/html', 'Accept-Language': 'ko-KR,ko;q=0.9' };
    try {
      const res  = await fetch(`https://www.riseetf.co.kr/etf/view/${code}`, { headers: RISE_H });
      const html = await res.text();

      // 모든 finderDetail 링크 수집
      const allProdIds = [...new Set([...html.matchAll(/\/prod\/finderDetail\/([A-Za-z0-9]+)/g)].map(m => m[1]))];

      // HTML에서 종목코드 직접 검색
      const codeIdx = html.indexOf(code);
      const codeCtx = codeIdx >= 0
        ? html.slice(Math.max(0, codeIdx - 300), codeIdx + 400)
        : null;

      // __NEXT_DATA__ 에서 검색
      let nextCtx = null;
      const ndm = html.match(/<script id="__NEXT_DATA__"[^>]*>([\s\S]+?)<\/script>/);
      if (ndm) {
        const nd = ndm[1];
        const ni = nd.indexOf(code);
        if (ni >= 0) nextCtx = nd.slice(Math.max(0, ni - 150), ni + 350);
      }

      return jsonRes({ status: res.status, len: html.length, allProdIds, codeFound: codeIdx >= 0, codeCtx, nextCtx });
    } catch (e) { return jsonRes({ error: String(e) }); }
  }

  // RISE 특정 productId 상세 페이지 파싱 (pid 파라미터 필요)
  if (src === 'rise_detail') {
    const pid = (url.searchParams.get('pid') || '').trim();
    if (!pid) return jsonRes({ error: 'pid required (e.g. &pid=44H2)' }, 400);
    const RISE_H = { 'User-Agent': UA, 'Referer': 'https://www.riseetf.co.kr/', 'Accept': 'text/html', 'Accept-Language': 'ko-KR,ko;q=0.9' };
    try {
      const res  = await fetch(`https://www.riseetf.co.kr/prod/finderDetail/${pid}`, { headers: RISE_H });
      const html = await res.text();

      const dates   = [...html.matchAll(/20\d\d[.\/-]\d\d[.\/-]\d\d/g)].map(m=>m[0]).slice(0, 30);
      const amounts = [...html.matchAll(/(\d{1,4}(?:,\d{3})*)(?:\s*원)?(?=\s*<)/g)].map(m=>m[0]).slice(0, 30);
      const divHints = html.split('\n').filter(l=>/분배|배당|distribution/i.test(l)).slice(0, 10).join('\n').slice(0, 800);

      // __NEXT_DATA__ 파싱 시도
      const ndm = html.match(/<script id="__NEXT_DATA__"[^>]*>([\s\S]+?)<\/script>/);
      let ndDistribs = null;
      if (ndm) {
        try {
          const nd = JSON.parse(ndm[1]);
          // 재귀 탐색으로 분배금 배열 찾기
          const findDistribs = (obj, depth = 0) => {
            if (depth > 10 || !obj || typeof obj !== 'object') return null;
            if (Array.isArray(obj) && obj.length > 0 && obj[0]?.paymentDate) return obj.slice(0, 24);
            for (const v of Object.values(obj)) {
              const r = findDistribs(v, depth + 1);
              if (r) return r;
            }
            return null;
          };
          ndDistribs = findDistribs(nd);
        } catch {}
      }

      return jsonRes({ status: res.status, len: html.length, dates, amounts, divHints, ndDistribs });
    } catch (e) { return jsonRes({ error: String(e) }); }
  }

  // 한국 운용사 사이트 직접 접근 (병렬) — 한국 CF 엣지에서 실행 시 빠름
  const sites = [
    // RISE (KB자산운용)
    { key: 'rise_v1',   url: `https://www.riseetf.co.kr/etf/view/${code}`,      ref: 'https://www.riseetf.co.kr/' },
    { key: 'rise_v2',   url: `https://www.riseetf.co.kr/etf/detail/${code}`,    ref: 'https://www.riseetf.co.kr/' },
    { key: 'kbam_v1',   url: `https://www.kbam.co.kr/etf/view/${code}`,         ref: 'https://www.kbam.co.kr/' },
    // KODEX (삼성자산운용)
    { key: 'kodex_v1',  url: `https://www.kodex.com/Product/Product.aspx?codeNo=${code}`, ref: 'https://www.kodex.com/' },
    // TIGER (미래에셋)
    { key: 'tiger_v1',  url: `https://www.tigeretf.com/ko/fund/view.do?fundCode=${code}`, ref: 'https://www.tigeretf.com/' },
    // ACE (한국투자신탁)
    { key: 'ace_v1',    url: `https://www.acetf.co.kr/etf/view/${code}`,        ref: 'https://www.acetf.co.kr/' },
  ];

  const results = await Promise.all(sites.map(async s => {
    try {
      const res  = await fetch(s.url, { headers: { 'Referer': s.ref, 'User-Agent': UA, 'Accept': 'text/html', 'Accept-Language': 'ko-KR,ko;q=0.9' } });
      const html = await res.text();
      const dateMatches = [...html.matchAll(/20\d\d[.\/-]\d\d[.\/-]\d\d/g)].map(m=>m[0]).slice(0,5);
      const wonMatches  = [...html.matchAll(/(\d{1,5})\s*(?:원|₩)/g)].map(m=>m[0]).slice(0,5);
      const divHints    = html.split('\n').filter(l=>/dividend|distribut|분배|배당/i.test(l)).slice(0,5).join('|').slice(0,400);
      return [s.key, { status: res.status, htmlLen: html.length, dateMatches, wonMatches, divHints }];
    } catch (e) { return [s.key, { error: String(e) }]; }
  }));

  return jsonRes(Object.fromEntries(results));
}

// ── 단일 종목 시세 ────────────────────────────────────────────────────────
async function fetchSingleQuote(code) {
  // 1차: m.stock.naver.com/api/stock/{code}/basic
  try {
    const res  = await fetch(`https://m.stock.naver.com/api/stock/${code}/basic`, { headers: NAVER_HDRS });
    const data = await res.json();
    if (res.ok && data && data.code !== 'StockConflict') {
      const priceStr =
        data.closePrice || data.currentPrice || data.stockEndPrice ||
        data.tradePrice || data.nav          || data.price         || '0';
      const price  = parseInt(priceStr.toString().replace(/,/g, ''), 10);
      const change = parseFloat((data.fluctuationsRatio || data.fluctuationRate || '0').toString().replace(/%/g, ''));
      if (price > 0) return { code, price, change, source: 'NAVER', delayed: 15 };
    }
  } catch {}

  // 2차: itemSummary (now 필드)
  try {
    const res  = await fetch(`https://api.finance.naver.com/service/itemSummary.nhn?itemcode=${code}`, { headers: { ...NAVER_HDRS, 'Accept': 'application/json' } });
    const text = await res.text();
    if (text && text.trim().startsWith('{')) {
      const data   = JSON.parse(text);
      const price  = parseInt((data.now || data.closePrice || data.currentPrice || 0).toString().replace(/,/g, ''), 10);
      const change = parseFloat((data.rate || data.fluctuationsRatio || 0).toString());
      if (price > 0) return { code, price, change, source: 'NAVER', delayed: 15 };
    }
  } catch {}

  // 3차: Yahoo Finance ({code}.KS)
  try {
    const res  = await fetch(`https://query1.finance.yahoo.com/v8/finance/chart/${code}.KS?interval=1d&range=1d`, { headers: { 'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json' } });
    const data = await res.json();
    const meta = data?.chart?.result?.[0]?.meta;
    if (meta) {
      const price  = Math.round(meta.regularMarketPrice || meta.previousClose || 0);
      const change = parseFloat((meta.regularMarketChangePercent || 0).toFixed(2));
      if (price > 0) return { code, price, change, source: 'YAHOO', delayed: 15 };
    }
  } catch {}

  return { code, price: 0, change: 0, source: 'UNAVAILABLE', delayed: 0 };
}

// ── 유틸 ──────────────────────────────────────────────────────────────────
function normalizeMarket(raw) {
  const s = (raw || '').toUpperCase();
  if (s.includes('KOSDAQ') || s.includes('코스닥')) return 'KOSDAQ';
  if (s.includes('KONEX')  || s.includes('코넥스')) return 'KONEX';
  return 'KOSPI';
}

function jsonRes(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { ...CORS, 'Content-Type': 'application/json' },
  });
}
