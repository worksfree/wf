/**
 * WorksFree Hub — 혼합 부하 테스트 (Mixed Workload)
 * ================================================
 *
 * DART API 조회 사용자와 일반 페이지 접속 사용자를 동시에 실행.
 * "API 조회가 진행 중일 때 일반 페이지 접속이 영향받는가?" 검증.
 *
 * [기본 실행]
 *   k6 run nas-mixed-test.js
 *
 * [DART 조회 비율 조정]
 *   k6 run --env DART_VUS=10 --env PAGE_MAX_VUS=100 nas-mixed-test.js
 *
 * [Cloudflare 경유 페이지 테스트]
 *   k6 run --env TARGET_ENV=cloudflare nas-mixed-test.js
 *
 * 시나리오 구성:
 *   dart_query  : DART API 조회 사용자 (constant-vus, 항상 N명 유지)
 *   page_browse : 일반 페이지 접속 사용자 (ramping-vus, 단계적 증가)
 *
 * 임계값:
 *   page_browse P95 < 1000ms  ← DART 조회 중에도 페이지는 1초 이내
 *   dart_query  P95 < 8000ms  ← DART 조회는 8초 이내
 */

import http             from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend }  from 'k6/metrics';

// ── 설정 ─────────────────────────────────────────────────────────────
const DART_BASE  = 'https://dart-api-worker.worksfree.workers.dev';

const ENV_PRESETS = {
  'internal':       'http://192.168.100.38:8082',
  'internal-test':  'http://192.168.100.38:8081',
  'cloudflare':     'https://portal.worksfree.kr',
  'cloudflare-stg': 'https://staging.worksfree.kr',
};

const TARGET_ENV = __ENV.TARGET_ENV  || 'internal';
const TARGET_URL = __ENV.TARGET_URL  || ENV_PRESETS[TARGET_ENV] || ENV_PRESETS.internal;

// DART 동시 조회 사용자 수
const DART_VUS      = parseInt(__ENV.DART_VUS      || '5');
// DART 조회 후 결과를 읽는 시간(초) — 최소/최대
// 실 사용자는 결과를 보고 분석하는 데 수십 초 소요
const DART_MIN_SLEEP = parseInt(__ENV.DART_MIN_SLEEP || '20');
const DART_MAX_SLEEP = parseInt(__ENV.DART_MAX_SLEEP || '40');
// 페이지 접속 최대 VU (단계적으로 증가)
const PAGE_MAX_VUS  = parseInt(__ENV.PAGE_MAX_VUS  || '50');
const PAGE_STEP_VUS = parseInt(__ENV.PAGE_STEP     || '10');
const PAGE_HOLD_S   = parseInt(__ENV.PAGE_HOLD     || '60');
// 전체 테스트 시간 (DART는 이 시간 내내 일정하게 유지)
const DURATION_MIN  = parseInt(__ENV.DURATION_MIN  || '10');

// ── DART 조회 대상 기업 목록 ──────────────────────────────────────────
// 실제 사용 케이스를 반영한 다양한 업종·규모의 기업
const DART_COMPANIES = [
  // 대기업 (조회 결과 많음 → 응답 상대적으로 느림)
  '삼성전자', '현대자동차', 'SK하이닉스', 'LG전자', '포스코홀딩스',
  // 중견기업
  '한화솔루션', '롯데케미칼', '현대건설', 'GS건설', 'LS일렉트릭',
  // IT·플랫폼
  '카카오', '네이버', '크래프톤', '카카오뱅크', '토스뱅크',
  // 금융
  'KB금융', '신한지주', '하나금융지주', '우리금융지주', 'NH투자증권',
  // 중소기업 (조회 결과 적음 → 빠름)
  '워크스프리', '에코프로비엠', '씨에스윈드', '인선이엔티', '케이씨텍',
];

// ── 페이지 접속 대상 경로 ─────────────────────────────────────────────
const BROWSE_PAGES = [
  '/',
  '/gfc/',
  '/consulting/ceo/',
  '/consulting/marketing/',
  '/consulting/dart/',
  '/app-store/solidworks/bom-exporter/',
  '/consulting/gfc/',
  '/consulting/ceo/flyers/flyer-ceo.html',
  '/consulting/gfc/flyers/flyer-ceo.html',
];

// ── 스테이지 생성 (페이지 접속 시나리오) ──────────────────────────────
function buildPageStages() {
  const stages = [];
  for (let vus = PAGE_STEP_VUS; vus <= PAGE_MAX_VUS; vus += PAGE_STEP_VUS) {
    stages.push({ duration: '10s',           target: vus });
    stages.push({ duration: `${PAGE_HOLD_S}s`, target: vus });
  }
  // 마지막 단계 유지 후 종료
  stages.push({ duration: '30s', target: 0 });
  return stages;
}

// ── k6 옵션 ───────────────────────────────────────────────────────────
export const options = {
  scenarios: {
    // DART 조회 사용자: 항상 DART_VUS 명이 쉬지 않고 조회
    dart_query: {
      executor:  'constant-vus',
      vus:       DART_VUS,
      duration:  `${DURATION_MIN}m`,
      exec:      'dartScenario',
      tags:      { scenario: 'dart_query' },
    },
    // 일반 페이지 접속: 단계적으로 늘어남
    page_browse: {
      executor:  'ramping-vus',
      startVUs:  0,
      stages:    buildPageStages(),
      exec:      'browseScenario',
      tags:      { scenario: 'page_browse' },
      startTime: '5s',  // DART 조회가 먼저 시작된 뒤 페이지 접속 시작
    },
  },
  thresholds: {
    // 페이지 접속: DART 조회 중에도 1초 이내
    'http_req_duration{scenario:page_browse}': ['p(95)<1000'],
    // DART API: 8초 이내
    'http_req_duration{scenario:dart_query}':  ['p(95)<8000'],
    // 페이지 접속 오류율 1% 이하
    'http_req_failed{scenario:page_browse}':   ['rate<0.01'],
    // DART API 오류율 10% 이하 (rate limit 등 허용)
    'http_req_failed{scenario:dart_query}':    ['rate<0.10'],
  },
  summaryTrendStats: ['min', 'med', 'avg', 'p(90)', 'p(95)', 'p(99)', 'max', 'count'],
};

// ── 커스텀 메트릭 ─────────────────────────────────────────────────────
const dartDuration    = new Trend('dart_response_ms', true);
const pageDuration    = new Trend('page_response_ms', true);
const dartErrorRate   = new Rate('dart_error_rate');
const pageErrorRate   = new Rate('page_error_rate');
const dartRateLimit   = new Rate('dart_rate_limit');   // 429 rate limit 비율
const dartApiError    = new Rate('dart_api_error');    // DART API 자체 오류 비율

// ── [dart_query] DART API 조회 시나리오 ──────────────────────────────
export function dartScenario() {
  const company = DART_COMPANIES[Math.floor(Math.random() * DART_COMPANIES.length)];
  const url = `${DART_BASE}/?ep=company.json` +
              `&corp_name=${encodeURIComponent(company)}` +
              `&page_no=1&page_count=10`;

  const res = http.get(url, {
    timeout: '15s',
    tags: { corp: company },
    headers: { 'Accept': 'application/json' },
  });

  const dur        = res.timings.duration;
  const isHttp2xx  = res.status >= 200 && res.status < 300;
  const is429      = res.status === 429;

  // JSON body 파싱해서 DART API 자체 오류 코드 확인
  let dartStatus = null;
  try {
    const body = JSON.parse(res.body);
    dartStatus = body?.status;   // DART API: '000'=성공, '020'=한도초과 등
  } catch (_) {}

  const isApiError   = dartStatus !== null && dartStatus !== '000';
  const isRateLimit  = is429 || dartStatus === '020';   // 020 = 일일 한도초과
  const hasError     = !isHttp2xx || isApiError;

  check(res, {
    'dart: HTTP 2xx':       () => isHttp2xx,
    'dart: API 성공(000)':  () => dartStatus === '000' || dartStatus === null,
    'dart: rate limit 없음':() => !isRateLimit,
    'dart: 8초 이내':       (r) => r.timings.duration < 8000,
  });

  dartDuration.add(dur);
  dartErrorRate.add(hasError);
  dartRateLimit.add(isRateLimit);
  dartApiError.add(isApiError);

  if (__ENV.VERBOSE === 'true') {
    const tag = isRateLimit ? '[RATE]' : hasError ? '[ERR] ' : '[OK]  ';
    console.log(`  DART ${tag} ${company.padEnd(10)} → ${Math.round(dur)}ms  status=${dartStatus ?? res.status}`);
  }

  // 실 사용자는 결과를 받은 후 수십 초 동안 분석 (rate limit 방지 겸 현실 반영)
  sleep(DART_MIN_SLEEP + Math.random() * (DART_MAX_SLEEP - DART_MIN_SLEEP));
}

// ── [page_browse] 일반 페이지 접속 시나리오 ──────────────────────────
export function browseScenario() {
  const path = BROWSE_PAGES[Math.floor(Math.random() * BROWSE_PAGES.length)];
  const url  = TARGET_URL + path;

  const res = http.get(url, {
    timeout: '10s',
    tags: { path },
    redirects: 5,
  });

  const ok  = res.status >= 200 && res.status < 400;
  const dur = res.timings.duration;

  check(res, {
    'page: status 2xx/3xx':  (r) => r.status >= 200 && r.status < 400,
    'page: 1초 이내':        (r) => r.timings.duration < 1000,
    'page: 3초 이내':        (r) => r.timings.duration < 3000,
  });

  pageDuration.add(dur);
  pageErrorRate.add(!ok);

  // 페이지를 읽는 시간 (2~6초)
  sleep(2 + Math.random() * 4);
}

// ── 최종 보고서 ───────────────────────────────────────────────────────
export function handleSummary(data) {
  const m = data.metrics;

  function vals(key) { return m[key]?.values || {}; }

  const dartMs    = vals('dart_response_ms');
  const pageMs    = vals('page_response_ms');
  const dartErr   = vals('dart_error_rate');
  const pageErr   = vals('page_error_rate');
  const dartRl    = vals('dart_rate_limit');
  const dartAe    = vals('dart_api_error');
  const reqs      = vals('http_reqs');

  const ts  = new Date().toLocaleString('ko-KR', { timeZone: 'Asia/Seoul' });
  const sep = '═'.repeat(64);
  const div = '─'.repeat(64);

  function bar(ratio, width) {
    const filled = Math.round(Math.min(ratio, 1) * width);
    return '[' + '█'.repeat(filled) + '░'.repeat(width - filled) + ']';
  }

  function ms(v) { return v != null ? v.toFixed(0) + ' ms' : '-'; }

  const pageP95    = pageMs['p(95)'] || 0;
  const dartP95    = dartMs['p(95)'] || 0;
  const pageResult = pageP95 < 1000 ? 'PASS ✓' : 'FAIL ✗';
  const dartResult = dartP95 < 8000 ? 'PASS ✓' : 'FAIL ✗';

  const lines = [
    '',
    sep,
    '  WorksFree Hub 혼합 부하 테스트 결과',
    sep,
    `  일시    : ${ts}`,
    `  페이지  : ${TARGET_URL}`,
    `  DART    : ${DART_BASE}`,
    `  구성    : DART 조회 ${DART_VUS}명 (간격 ${DART_MIN_SLEEP}~${DART_MAX_SLEEP}초) + 페이지 접속 최대 ${PAGE_MAX_VUS}명`,
    '',
    div,
    '  [ 핵심 결과 ]',
    div,
    `  페이지 접속 P95 : ${String(Math.round(pageP95)).padStart(5)} ms   기준 1000ms → ${pageResult}`,
    `  DART 조회  P95  : ${String(Math.round(dartP95)).padStart(5)} ms   기준 8000ms → ${dartResult}`,
    '',
    pageP95 < 1000
      ? '  → DART 조회가 진행 중에도 페이지 접속 성능은 영향받지 않았습니다.'
      : '  → DART 조회 부하가 페이지 접속 성능에 영향을 주었습니다.',
    '',
    div,
    '  [ 페이지 접속 (page_browse) ]',
    div,
    `  Med   ${ms(pageMs.med).padStart(8)}`,
    `  P90   ${ms(pageMs['p(90)']).padStart(8)}`,
    `  P95   ${ms(pageMs['p(95)']).padStart(8)}  ← 기준 1000ms`,
    `  P99   ${ms(pageMs['p(99)']).padStart(8)}`,
    `  Max   ${ms(pageMs.max).padStart(8)}`,
    `  오류율 ${((pageErr.rate || 0) * 100).toFixed(2)} %`,
    `  요청수 ${(pageMs.count || 0).toLocaleString()} 건`,
    '',
    div,
    '  [ DART API 조회 (dart_query) ]',
    div,
    `  Med   ${ms(dartMs.med).padStart(8)}`,
    `  P90   ${ms(dartMs['p(90)']).padStart(8)}`,
    `  P95   ${ms(dartMs['p(95)']).padStart(8)}  ← 기준 8000ms`,
    `  P99   ${ms(dartMs['p(99)']).padStart(8)}`,
    `  Max   ${ms(dartMs.max).padStart(8)}`,
    `  오류율      ${((dartErr.rate || 0) * 100).toFixed(2)} %`,
    `  rate limit  ${((dartRl.rate  || 0) * 100).toFixed(2)} %  (429 또는 DART 한도초과)`,
    `  API 오류    ${((dartAe.rate  || 0) * 100).toFixed(2)} %  (DART status != 000)`,
    `  요청수 ${(dartMs.count || 0).toLocaleString()} 건`,
    `  실효 RPS  ${((dartMs.count || 0) / (DURATION_MIN * 60)).toFixed(2)} req/s (${DART_VUS}명 × 1/${Math.round((DART_MIN_SLEEP + DART_MAX_SLEEP) / 2)}s)`,
    '',
    div,
    '  [ 전체 ]',
    div,
    `  총 요청수 : ${(reqs.count || 0).toLocaleString()} 건`,
    `  평균 RPS  : ${(reqs.rate || 0).toFixed(1)} req/s`,
    '',
    sep,
    '',
  ];

  const jsonReport = {
    meta: { timestamp: ts, target_url: TARGET_URL, dart_base: DART_BASE },
    config: { dart_vus: DART_VUS, page_max_vus: PAGE_MAX_VUS, duration_min: DURATION_MIN },
    page_browse: {
      p95_ms: parseFloat((pageMs['p(95)'] || 0).toFixed(1)),
      p99_ms: parseFloat((pageMs['p(99)'] || 0).toFixed(1)),
      error_rate: parseFloat(((pageErr.rate || 0) * 100).toFixed(2)),
      count: pageMs.count || 0,
      result: pageP95 < 1000 ? 'PASS' : 'FAIL',
    },
    dart_query: {
      p95_ms: parseFloat((dartMs['p(95)'] || 0).toFixed(1)),
      p99_ms: parseFloat((dartMs['p(99)'] || 0).toFixed(1)),
      error_rate: parseFloat(((dartErr.rate || 0) * 100).toFixed(2)),
      count: dartMs.count || 0,
      result: dartP95 < 8000 ? 'PASS' : 'FAIL',
    },
  };

  return {
    'nas-mixed-test-report.json': JSON.stringify(jsonReport, null, 2),
    stdout: lines.join('\n'),
  };
}
