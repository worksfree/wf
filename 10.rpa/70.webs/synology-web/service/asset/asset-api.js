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
      if (path === '/search')        return await handleSearch(url);
      if (path === '/quote')         return await handleQuote(url);
      if (path === '/quotes')        return await handleQuotes(url);
      if (path === '/debug')         return await handleDebug(url);
      if (path === '/debug-search')  return await handleDebugSearch(url);
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
