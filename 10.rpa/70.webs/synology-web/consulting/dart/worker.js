const ALLOWED_ORIGIN = '*';
const DART_API_KEY_DEFAULT = 'e294b0073fed80d6bd91699c93926f8832e39d90';
const CACHE_KEY = 'https://dart-corp-index/v3';

// Worker가 직접 프록시할 수 있는 DART API 엔드포인트 허용 목록
const PROXY_EPS = new Set([
  'company.json',
  'fnlttSinglAcntAll.json',  // 단일회사 전체 재무제표
  'fnlttSinglAcnt.json',     // 단일회사 주요 재무제표
]);

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

  const apiKey = (typeof DART_API_KEY !== 'undefined' && DART_API_KEY)
               ? DART_API_KEY : DART_API_KEY_DEFAULT;

  const params = new URLSearchParams(url.search);
  params.delete('ep');
  params.set('crtfc_key', apiKey);

  if (params.has('corpname')) {
    params.set('corp_name', params.get('corpname'));
    params.delete('corpname');
  }

  // 대량조회용: 이름/종목코드 → corp_code 해소 후 상세 조회 (1 Worker call)
  if (ep === 'corp_info.json') {
    return resolveAndFetch(params, apiKey);
  }

  // 허용되지 않은 엔드포인트 차단
  if (!PROXY_EPS.has(ep)) {
    return jsonResp({ status: 'ERR', message: `지원하지 않는 엔드포인트: ${ep}` }, 400);
  }

  const hasCorpName = params.has('corp_name');
  const hasCorpCode = params.has('corp_code');

  // 회사명 검색 → corpCode.xml 인덱스 기반 (company.json 전용)
  if (ep === 'company.json' && hasCorpName && !hasCorpCode) {
    return searchByName(params, apiKey);
  }

  // 직접 프록시: ep 파라미터를 DART API 경로로 사용
  params.delete('stock_code'); // DART API 미지원 파라미터 제거
  const dartUrl = `https://opendart.fss.or.kr/api/${ep}?${params}`;
  try {
    const resp = await fetch(dartUrl, { headers: { 'User-Agent': 'Mozilla/5.0' } });
    return new Response(await resp.text(), {
      status: resp.status,
      headers: { 'Content-Type': 'application/json;charset=utf-8', ...corsHeaders() },
    });
  } catch (e) {
    return jsonResp({ status: 'ERR', message: e.message }, 502);
  }
}

// ── 이름/종목코드 → corp_code 해소 후 상세 조회 (대량조회용 단일 call)
async function resolveAndFetch(params, apiKey) {
  const corpName  = params.get('corp_name')  || '';
  const stockCode = params.get('stock_code') || '';
  let   corpCode  = params.get('corp_code')  || '';

  if (!corpCode) {
    const index = await getCorpIndex(apiKey);
    let match;
    if (stockCode) {
      match = index.find(c => c.stock_code === stockCode.trim());
    } else if (corpName) {
      const norm = normalizeCorpName(corpName);
      // 우선순위: 정확일치 → 전방일치 → 부분일치
      match = index.find(c => c.corp_name === norm)
           || index.find(c => c.corp_name.startsWith(norm))
           || index.find(c => c.corp_name.includes(norm));
    }
    if (!match) return jsonResp({ status: '000', message: '정상', corp_code: '', corp_name: '' });
    corpCode = match.corp_code;
  }

  try {
    const resp = await fetch(
      `https://opendart.fss.or.kr/api/company.json?corp_code=${corpCode}&crtfc_key=${apiKey}`,
      { headers: { 'User-Agent': 'Mozilla/5.0' } }
    );
    return new Response(await resp.text(), {
      status: resp.status,
      headers: { 'Content-Type': 'application/json;charset=utf-8', ...corsHeaders() },
    });
  } catch (e) {
    return jsonResp({ status: 'ERR', message: e.message }, 502);
  }
}

// ── 회사명 정규화
function normalizeCorpName(name) {
  return name
    .replace(/^\(주\)\s*/, '').replace(/^주식회사\s*/, '')
    .replace(/\s*\(주\)$/, '').replace(/\s*주식회사$/, '')
    .replace(/\s*\(유\)$/, '').replace(/\s*\(합\)$/, '')
    .trim();
}

// ── 회사명 검색
async function searchByName(params, apiKey) {
  const corpName  = normalizeCorpName(params.get('corp_name'));
  const pageNo    = Math.max(1, parseInt(params.get('page_no')    || '1'));
  const pageCount = Math.max(1, parseInt(params.get('page_count') || '10'));

  const index   = await getCorpIndex(apiKey);
  const matches = index.filter(c => c.corp_name.includes(corpName));
  const total   = matches.length;
  const page    = matches.slice((pageNo - 1) * pageCount, pageNo * pageCount);

  return jsonResp({ status:'000', message:'정상', total_count:total, page_no:pageNo, page_count:pageCount, list:page });
}

// ── corpCode.xml 인덱스 (캐시 24시간)
async function getCorpIndex(apiKey) {
  const cache = caches.default;
  const hit   = await cache.match(CACHE_KEY);
  if (hit) return hit.json();

  // ZIP 다운로드
  const resp = await fetch(
    `https://opendart.fss.or.kr/api/corpCode.xml?crtfc_key=${apiKey}`,
    { headers: { 'User-Agent': 'Mozilla/5.0' } }
  );
  if (!resp.ok) throw new Error(`corpCode 다운로드 실패: ${resp.status}`);

  const buf = await resp.arrayBuffer();
  const xml = await unzipFirst(buf);
  const idx = parseCorpXml(xml);

  // 결과 캐시
  await cache.put(CACHE_KEY, new Response(JSON.stringify(idx), {
    headers: {
      'Content-Type': 'application/json;charset=utf-8',
      'Cache-Control': 'public, max-age=86400',
    },
  }));
  return idx;
}

// ── ZIP Central Directory에서 압축 크기 읽기 (Data Descriptor 대응)
function cdCompressedSize(view, buf) {
  // End of Central Directory 시그니처(0x06054b50)를 뒤에서 탐색
  for (let i = buf.byteLength - 22; i >= 0; i--) {
    if (view.getUint32(i, true) === 0x06054b50) {
      const cdOffset = view.getUint32(i + 16, true);
      // Central Directory Entry +20 = compressed size
      return view.getUint32(cdOffset + 20, true);
    }
  }
  return buf.byteLength - 22;
}

// ── ZIP 첫 번째 파일 압축 해제 (Deflate)
async function unzipFirst(buf) {
  const view     = new DataView(buf);
  const flag     = view.getUint16(6,  true);
  const method   = view.getUint16(8,  true);
  let   compSize = view.getUint32(18, true);
  const nameLen  = view.getUint16(26, true);
  const extraLen = view.getUint16(28, true);
  const start    = 30 + nameLen + extraLen;

  // Data Descriptor 방식(bit 3)이면 로컬 헤더의 compSize=0 → Central Directory에서 읽기
  if ((flag & 0x08) || compSize === 0) {
    compSize = cdCompressedSize(view, buf);
  }

  const compressed = new Uint8Array(buf, start, compSize);

  if (method === 0) {
    return tryDecode(compressed);
  }

  // Deflate 압축 해제
  const ds     = new DecompressionStream('deflate-raw');
  const writer = ds.writable.getWriter();
  writer.write(compressed);
  writer.close();

  const chunks = [];
  const reader = ds.readable.getReader();
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    chunks.push(value);
  }

  const total  = chunks.reduce((s, c) => s + c.length, 0);
  const merged = new Uint8Array(total);
  let off = 0;
  for (const c of chunks) { merged.set(c, off); off += c.length; }

  return tryDecode(merged);
}

function tryDecode(bytes) {
  try { return new TextDecoder('utf-8', { fatal: true }).decode(bytes); }
  catch { return new TextDecoder('euc-kr').decode(bytes); }
}

// ── XML 파싱 (split 방식, regex보다 빠름)
function parseCorpXml(xml) {
  const result = [];
  const blocks = xml.split('<list>');
  for (let i = 1; i < blocks.length; i++) {
    const b   = blocks[i];
    const get = tag => {
      const s = b.indexOf(`<${tag}>`), e = b.indexOf(`</${tag}>`);
      return s >= 0 && e > s ? b.slice(s + tag.length + 2, e).trim() : '';
    };
    const corp_code = get('corp_code');
    const corp_name = get('corp_name');
    if (corp_code && corp_name) {
      result.push({ corp_code, corp_name, stock_code: get('stock_code') });
    }
  }
  return result;
}

// ── 공통
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
