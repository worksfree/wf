/**
 * WorksFree Hub — NAS / Cloudflare 부하 테스트
 * =====================================================
 *
 * ┌─ [stress 모드] NAS 하드웨어 한계 탐색 ─────────────────────────┐
 * │  VU수 = 실제 동시 HTTP 연결수 (STRESS=true 시 sleep 없음)      │
 * │                                                                │
 * │  k6 run --env STRESS=true \                                    │
 * │         --env TARGET_ENV=internal \                            │
 * │         --env MAX_VUS=1000 --env STEP_VUS=100 \               │
 * │         nas-load-test.js                                       │
 * └────────────────────────────────────────────────────────────────┘
 *
 * ┌─ [journey 모드] 실 사용자 행동 패턴 검증 ──────────────────────┐
 * │  실제 방문자가 여러 페이지를 탐색하는 흐름 시뮬레이션          │
 * │  VU수 ≠ 동시 연결수 (think time 포함)                          │
 * │                                                                │
 * │  k6 run --env TEST_MODE=journey \                              │
 * │         --env TARGET_ENV=internal \                            │
 * │         --env MAX_VUS=300 --env STEP_VUS=30 \                  │
 * │         nas-load-test.js                                       │
 * └────────────────────────────────────────────────────────────────┘
 *
 * [Cloudflare 경유 + 캐시 무효화]
 *   k6 run --env TEST_MODE=journey --env TARGET_ENV=cloudflare \
 *          --env CACHE_BUST=true nas-load-test.js
 */

import http             from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Counter, Gauge } from 'k6/metrics';
import exec             from 'k6/execution';

// ── 환경 프리셋 ───────────────────────────────────────────────────────
const ENV_PRESETS = {
  'internal':       'http://192.168.100.38:8082',
  'internal-test':  'http://192.168.100.38:8081',
  'internal-stg':   'http://192.168.100.38:8080',
  'cloudflare':     'https://portal.worksfree.kr',
  'cloudflare-stg': 'https://staging.worksfree.kr',
  'cloudflare-test':'https://test.worksfree.kr',
};

// ── 모드 선택 ─────────────────────────────────────────────────────────
// TEST_MODE=stress   : 랜덤 URL 반복 요청 (기본값)
//                      + STRESS=true 조합 시 sleep 없이 최대 부하
// TEST_MODE=journey  : 실 사용자 탐색 시뮬레이션 (think time 포함)
const TEST_MODE   = (__ENV.TEST_MODE || 'stress').toLowerCase();
const IS_JOURNEY  = TEST_MODE === 'journey';
const STRESS_MODE = (__ENV.STRESS   || 'false') === 'true';

const TARGET_ENV   = __ENV.TARGET_ENV || 'internal';
const TARGET_URL   = __ENV.TARGET_URL || ENV_PRESETS[TARGET_ENV] || ENV_PRESETS.internal;
const CACHE_BUST   = (__ENV.CACHE_BUST || 'false') === 'true';
const STEP_VUS     = parseInt(__ENV.STEP_VUS  || '10');
const STEP_HOLD_S  = parseInt(__ENV.STEP_HOLD || '60');
const MAX_VUS      = parseInt(__ENV.MAX_VUS   || '200');
const P95_LIMIT_MS = parseInt(__ENV.P95_LIMIT || '3000');

const VIA_CF = TARGET_URL.startsWith('https://') && !TARGET_URL.includes('192.168');

// ── [stress] 무작위 요청 대상 경로 ────────────────────────────────────
const STRESS_PATHS = [
  '/',
  '/index.html',
  '/gfc/',
  '/assets/role-content.js',
];

// ── [journey] 실 사용자 탐색 시나리오 ────────────────────────────────
// label    : 로그에 표시할 시나리오 이름
// pages    : 방문 페이지 목록
//   path      : URL 경로
//   minSleep  : 페이지를 읽는 최소 시간(초)
//   maxSleep  : 페이지를 읽는 최대 시간(초) — 0이면 think time 없음
const JOURNEY_FLOWS = [
  {
    label: 'Flow-A 일반방문',
    pages: [
      { path: '/',     minSleep: 3, maxSleep: 8  },
      { path: '/gfc/', minSleep: 5, maxSleep: 12 },
    ],
  },
  {
    label: 'Flow-B CEO리드',
    pages: [
      { path: '/',                                       minSleep: 2, maxSleep: 5  },
      { path: '/consulting/ceo/',                        minSleep: 5, maxSleep: 10 },
      { path: '/consulting/ceo/flyers/flyer-ceo.html',  minSleep: 8, maxSleep: 20 },
    ],
  },
  {
    label: 'Flow-C GFC고객',
    pages: [
      { path: '/',                                       minSleep: 2, maxSleep: 6  },
      { path: '/gfc/',                                   minSleep: 4, maxSleep: 8  },
      { path: '/consulting/gfc/',                        minSleep: 5, maxSleep: 10 },
      { path: '/consulting/gfc/flyers/flyer-ceo.html',  minSleep: 8, maxSleep: 18 },
    ],
  },
  {
    label: 'Flow-D 앱탐색',
    pages: [
      { path: '/',                                      minSleep: 3, maxSleep: 6  },
      { path: '/app-store/solidworks/bom-exporter/',   minSleep: 5, maxSleep: 12 },
      { path: '/app-store/etc/conversion-verifier/',   minSleep: 4, maxSleep: 8  },
    ],
  },
  {
    label: 'Flow-E 마케팅',
    pages: [
      { path: '/',                      minSleep: 3, maxSleep: 6  },
      { path: '/consulting/marketing/', minSleep: 6, maxSleep: 15 },
      { path: '/consulting/ceo/flyers/flyer-case-study.html', minSleep: 8, maxSleep: 20 },
    ],
  },
];

// ── 스테이지 자동 생성 ─────────────────────────────────────────────────
function buildStages() {
  const stages = [];
  for (let vus = STEP_VUS; vus <= MAX_VUS; vus += STEP_VUS) {
    stages.push({ duration: '10s',             target: vus });
    stages.push({ duration: `${STEP_HOLD_S}s`, target: vus });
  }
  return stages;
}

const ALL_STAGES       = buildStages();
const STAGE_DURATION_S = 10 + STEP_HOLD_S;

// ── k6 옵션 ───────────────────────────────────────────────────────────
export const options = {
  scenarios: {
    nas_ramp: {
      executor:         'ramping-vus',
      startVUs:         0,
      stages:           ALL_STAGES,
      gracefulRampDown: '10s',
    },
  },
  thresholds: {
    http_req_duration: [{
      threshold:      `p(95)<${P95_LIMIT_MS}`,
      abortOnFail:    true,
      delayAbortEval: '15s',
    }],
    http_req_failed: [{
      threshold:      'rate<0.10',
      abortOnFail:    true,
      delayAbortEval: '10s',
    }],
  },
  summaryTrendStats: ['min', 'med', 'avg', 'p(75)', 'p(90)', 'p(95)', 'p(99)', 'max', 'count'],
};

// ── 커스텀 메트릭 ─────────────────────────────────────────────────────
const slowRate  = new Rate('req_slow_rate');
const slowCount = new Counter('req_slow_count');
const under1s   = new Rate('req_under_1s');
const peakVUs   = new Gauge('peak_active_vus');

// ── 헬퍼 ──────────────────────────────────────────────────────────────
function speedLabel(ms) {
  if (ms <  500) return 'FAST  ';
  if (ms < 1500) return 'OK    ';
  if (ms < 2500) return 'SLOW  ';
  return             'DANGER';
}

function url(path) {
  return TARGET_URL + path + (CACHE_BUST ? `?_=${Date.now()}` : '');
}

function record(res) {
  const dur    = res.timings.duration;
  const isSlow = dur > P95_LIMIT_MS;
  check(res, {
    'status 2xx/3xx': (r) => r.status >= 200 && r.status < 400,
    'response < 1s':  (r) => r.timings.duration < 1000,
    ['response < ' + P95_LIMIT_MS + 'ms']: (r) => r.timings.duration < P95_LIMIT_MS,
  });
  slowRate.add(isSlow);
  if (isSlow) slowCount.add(1);
  under1s.add(dur < 1000);
  peakVUs.add(exec.instance.vusActive);
  return dur;
}

// ── [stress] 스트레스 테스트 ──────────────────────────────────────────
function runStress() {
  const vusNow = exec.instance.vusActive;
  const path   = STRESS_PATHS[Math.floor(Math.random() * STRESS_PATHS.length)];
  const res    = http.get(url(path), { timeout: '12s', tags: { path, mode: 'stress' }, redirects: 5 });
  const dur    = record(res);

  if (exec.vu.idInTest === 1) {
    const stepNo = Math.ceil(vusNow / STEP_VUS);
    console.log(
      `[Step ${String(stepNo).padStart(2)}/${MAX_VUS / STEP_VUS}] ` +
      `VU: ${String(vusNow).padStart(3)}명 | ` +
      `응답: ${String(Math.round(dur)).padStart(5)}ms [${speedLabel(dur)}] | ` +
      `${res.status >= 200 && res.status < 400 ? 'OK' : 'ERR'} ${path}`
    );
  }

  if (!STRESS_MODE) sleep(1 + Math.random());
}

// ── [journey] 유저 저니 시뮬레이션 ───────────────────────────────────
function runJourney() {
  const vusNow = exec.instance.vusActive;
  const flow   = JOURNEY_FLOWS[Math.floor(Math.random() * JOURNEY_FLOWS.length)];
  const isVU1  = exec.vu.idInTest === 1;

  if (isVU1) {
    const stepNo = Math.ceil(vusNow / STEP_VUS);
    console.log(
      `[Step ${String(stepNo).padStart(2)}/${MAX_VUS / STEP_VUS}] ` +
      `VU: ${String(vusNow).padStart(3)}명 | ${flow.label} (${flow.pages.length}페이지)`
    );
  }

  for (let i = 0; i < flow.pages.length; i++) {
    const { path, minSleep, maxSleep } = flow.pages[i];
    const res = http.get(url(path), { timeout: '12s', tags: { path, mode: 'journey', flow: flow.label }, redirects: 5 });
    const dur = record(res);

    if (isVU1) {
      const icon = res.status >= 200 && res.status < 400 ? 'OK ' : 'ERR';
      console.log(
        `  └ ${i + 1}/${flow.pages.length} [${icon}] ` +
        `${String(Math.round(dur)).padStart(5)}ms [${speedLabel(dur)}] ${path}`
      );
    }

    // 마지막 페이지가 아니면 think time (사용자가 페이지를 읽는 시간)
    if (i < flow.pages.length - 1) {
      sleep(minSleep + Math.random() * (maxSleep - minSleep));
    }
  }
}

// ── 메인 진입점 ───────────────────────────────────────────────────────
export default function () {
  if (IS_JOURNEY) {
    runJourney();
  } else {
    runStress();
  }
}

// ── 최종 보고서 ───────────────────────────────────────────────────────
export function handleSummary(data) {
  const m   = data.metrics;
  const dur = m.http_req_duration?.values || {};
  const req = m.http_reqs?.values         || {};
  const err = m.http_req_failed?.values   || {};
  const slw = m.req_slow_count?.values    || {};
  const slr = m.req_slow_rate?.values     || {};
  const u1s = m.req_under_1s?.values      || {};

  const elapsedS     = (data.state.testRunDurationMs || 0) / 1000;
  const stagesPassed = Math.floor(elapsedS / STAGE_DURATION_S);
  const breakingVUs  = Math.min((stagesPassed + 1) * STEP_VUS, MAX_VUS);
  const stableVUs    = Math.max(0, breakingVUs - STEP_VUS);
  const totalDurS    = ALL_STAGES.reduce((s, st) => s + parseFloat(st.duration), 0);
  const aborted      = elapsedS < totalDurS - 5;

  const ts  = new Date().toLocaleString('ko-KR', { timeZone: 'Asia/Seoul' });
  const sep = '═'.repeat(64);
  const div = '─'.repeat(64);

  function bar(ratio, width) {
    const filled = Math.round(Math.min(ratio, 1) * width);
    return '[' + '█'.repeat(filled) + '░'.repeat(width - filled) + ']';
  }

  const totalSteps  = MAX_VUS / STEP_VUS;
  const stepsBar = Array.from({ length: totalSteps }, (_, i) => {
    const vus = (i + 1) * STEP_VUS;
    if (aborted && vus > breakingVUs) return '·';
    if (aborted && vus === breakingVUs) return '✗';
    return '✓';
  }).join('');

  const resultLine = aborted
    ? `FAIL  P95 ${P95_LIMIT_MS}ms 초과 → ${breakingVUs}명에서 중단`
    : `PASS  ${MAX_VUS}명까지 P95 < ${P95_LIMIT_MS}ms 모두 통과`;

  const p95val = (dur['p(95)'] || 0).toFixed(0);
  const p95pct = Math.min((dur['p(95)'] || 0) / P95_LIMIT_MS, 1);
  const p95bar = bar(p95pct, 30);

  // 모드별 주석
  const modeNote = IS_JOURNEY
    ? [
        '  ※ journey 모드: 실 사용자 탐색 시뮬레이션 (think time 포함)',
        `  ※ 시나리오 ${JOURNEY_FLOWS.length}종 (Flow A~${String.fromCharCode(64 + JOURNEY_FLOWS.length)}) 무작위 선택`,
        '  ※ VU수 ≠ 동시 HTTP 연결수 — 실 사용자 1명은 1 VU에 대응',
      ].join('\n')
    : STRESS_MODE
      ? '  ※ STRESS 모드: sleep 없음 — VU수 = 실제 동시 연결수'
      : '  ※ 일반 모드: sleep 1~2s — 실 사용자 패턴 (VU수 ≠ 동시 연결수)';

  const cfNote = VIA_CF
    ? (CACHE_BUST
        ? '  ※ Cloudflare 경유 + 캐시 무효화 (Origin 부하 측정)'
        : '  ※ Cloudflare 경유 (CDN 캐시 포함 — 실 사용자 경험 측정)')
    : '  ※ NAS 직접 연결 (Cloudflare 우회 — 하드웨어 한계 측정)';

  // journey 모드 전용 해석 주석
  const journeyNote = IS_JOURNEY && !aborted
    ? [
        '',
        div,
        '  [ journey 모드 해석 ]',
        div,
        `  ${MAX_VUS} VU = 동시에 탐색 중인 실 사용자 ${MAX_VUS}명`,
        '  think time 포함이므로 실제 동시 HTTP 연결은 VU의 수% 수준',
        '  → 이 테스트에서 통과했다면 훨씬 더 많은 동시 접속도 처리 가능',
      ].join('\n')
    : '';

  const nextStepNote = aborted
    ? [
        '  · NAS nginx: worker_processes auto; worker_connections 4096;',
        '  · Cloudflare 캐시 TTL 연장으로 Origin 요청 비율 낮추기',
        '  · DSM 리소스 모니터에서 테스트 중 CPU/RAM/Network 확인',
      ].join('\n')
    : IS_JOURNEY
      ? [
          '  → 실 사용자 시뮬레이션 전 구간 통과.',
          '     stress 모드로 NAS 하드웨어 한계를 함께 확인하세요:',
          `     k6 run --env STRESS=true --env MAX_VUS=1000 --env STEP_VUS=100 nas-load-test.js`,
        ].join('\n')
      : [
          '  → MAX_VUS를 늘려 상한을 탐색하세요:',
          `     k6 run --env STRESS=true --env MAX_VUS=1000 --env STEP_VUS=100 nas-load-test.js`,
        ].join('\n');

  const lines = [
    '',
    sep,
    `  WorksFree Hub 부하 테스트 결과  [${IS_JOURNEY ? 'JOURNEY' : 'STRESS'}]`,
    sep,
    `  일시   : ${ts}`,
    `  대상   : ${TARGET_URL}`,
    cfNote,
    modeNote,
    '',
    div,
    '  [ 결과 ]',
    div,
    `  ${resultLine}`,
    '',
    `  단계별 (${STEP_VUS}명씩 / ${STEP_HOLD_S}초)`,
    `  ${stepsBar}  ← ${MAX_VUS}명`,
    `  ${Array.from({ length: totalSteps }, (_, i) => (i + 1) % 5 === 0 ? String((i + 1) * STEP_VUS).padStart(3) : '   ').join('')}`,
    '',
    ...(aborted ? [
      `  ✓ 안정 구간  : ~${stableVUs}명  (P95 기준 이내)`,
      `  ✗ 임계점     : ${breakingVUs}명  (P95 ${p95val}ms → ${P95_LIMIT_MS}ms 초과)`,
    ] : [
      `  ✓ 전 구간 통과 : ${MAX_VUS}명까지 P95 ${p95val}ms (기준 ${P95_LIMIT_MS}ms)`,
    ]),
    journeyNote,
    '',
    div,
    '  [ 응답 시간 ]',
    div,
    `  P95 ${p95bar} ${p95val}ms / ${P95_LIMIT_MS}ms`,
    '',
    `  Min  ${(dur.min         || 0).toFixed(0).padStart(6)} ms`,
    `  Med  ${(dur.med         || 0).toFixed(0).padStart(6)} ms`,
    `  Avg  ${(dur.avg         || 0).toFixed(0).padStart(6)} ms`,
    `  P75  ${(dur['p(75)']   || 0).toFixed(0).padStart(6)} ms`,
    `  P90  ${(dur['p(90)']   || 0).toFixed(0).padStart(6)} ms`,
    `  P95  ${(dur['p(95)']   || 0).toFixed(0).padStart(6)} ms  ← 중단 기준`,
    `  P99  ${(dur['p(99)']   || 0).toFixed(0).padStart(6)} ms`,
    `  Max  ${(dur.max         || 0).toFixed(0).padStart(6)} ms`,
    '',
    div,
    '  [ 트래픽 ]',
    div,
    `  총 요청    : ${(req.count || 0).toLocaleString()} 건`,
    `  RPS        : ${(req.rate  || 0).toFixed(1)} req/s`,
    `  오류율     : ${((err.rate || 0) * 100).toFixed(2)} %`,
    `  1초 이내   : ${((u1s.rate || 0) * 100).toFixed(1)} %`,
    `  3초 초과   : ${(slw.count || 0).toLocaleString()} 건 (${((slr.rate || 0) * 100).toFixed(1)} %)`,
    '',
    div,
    '  [ 다음 단계 ]',
    div,
    nextStepNote,
    '',
    sep,
    '',
  ];

  const report = lines.join('\n');

  const jsonReport = {
    meta:     { timestamp: ts, target_url: TARGET_URL, test_mode: TEST_MODE, via_cloudflare: VIA_CF, cache_bust: CACHE_BUST },
    config:   { step_vus: STEP_VUS, hold_seconds: STEP_HOLD_S, max_vus: MAX_VUS, p95_limit_ms: P95_LIMIT_MS, stress_mode: STRESS_MODE },
    result:   { status: aborted ? 'ABORTED' : 'PASSED', breaking_vus: aborted ? breakingVUs : null, stable_vus: aborted ? stableVUs : MAX_VUS, duration_s: parseFloat(elapsedS.toFixed(1)) },
    response_ms: {
      min: parseFloat((dur.min || 0).toFixed(1)), med: parseFloat((dur.med || 0).toFixed(1)),
      avg: parseFloat((dur.avg || 0).toFixed(1)), p75: parseFloat((dur['p(75)'] || 0).toFixed(1)),
      p90: parseFloat((dur['p(90)'] || 0).toFixed(1)), p95: parseFloat((dur['p(95)'] || 0).toFixed(1)),
      p99: parseFloat((dur['p(99)'] || 0).toFixed(1)), max: parseFloat((dur.max || 0).toFixed(1)),
    },
    requests: {
      total: req.count || 0, rps: parseFloat((req.rate || 0).toFixed(2)),
      error_rate: parseFloat(((err.rate || 0) * 100).toFixed(2)),
      slow_count: slw.count || 0, slow_pct: parseFloat(((slr.rate || 0) * 100).toFixed(1)),
      under_1s_pct: parseFloat(((u1s.rate || 0) * 100).toFixed(1)),
    },
  };

  return {
    'nas-load-test-report.json': JSON.stringify(jsonReport, null, 2),
    stdout: report,
  };
}
