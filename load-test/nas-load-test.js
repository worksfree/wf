/**
 * WorksFree Hub — NAS / Cloudflare 동접자 부하 테스트
 * =====================================================
 *
 * [내부망 직접] NAS 하드웨어 한계 측정 (Cloudflare CDN 우회)
 *   k6 run --env TARGET_ENV=internal nas-load-test.js
 *
 * [Cloudflare 경유] 실 사용자 경험 측정 (CDN 캐시 포함)
 *   k6 run --env TARGET_ENV=cloudflare nas-load-test.js
 *
 * [Cloudflare 경유 + 캐시 무효화] Origin까지 도달하는 실 부하 측정
 *   k6 run --env TARGET_ENV=cloudflare --env CACHE_BUST=true nas-load-test.js
 *
 * [직접 URL 지정]
 *   k6 run --env TARGET_URL=http://192.168.100.38:8081 nas-load-test.js
 *
 * [전체 옵션]
 *   k6 run \
 *     --env TARGET_ENV=cloudflare \
 *     --env CACHE_BUST=true \
 *     --env STEP_VUS=10 \
 *     --env STEP_HOLD=60 \
 *     --env MAX_VUS=200 \
 *     --env P95_LIMIT=3000 \
 *     nas-load-test.js
 */

import http         from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Counter, Gauge } from 'k6/metrics';
import exec         from 'k6/execution';

// ── 환경 프리셋 ───────────────────────────────────────────────────────
const ENV_PRESETS = {
  'internal':      'http://192.168.100.38:8082',   // www (NAS 직접, 내부망)
  'internal-test': 'http://192.168.100.38:8081',   // test (NAS 직접, 내부망)
  'internal-stg':  'http://192.168.100.38:8080',   // staging (NAS 직접, 내부망)
  'cloudflare':    'https://portal.worksfree.kr',  // www (Cloudflare 경유)
  'cloudflare-stg':'https://staging.worksfree.kr', // staging (Cloudflare 경유)
  'cloudflare-test':'https://test.worksfree.kr',   // test (Cloudflare 경유)
};

const TARGET_ENV   = __ENV.TARGET_ENV  || 'internal';
const TARGET_URL   = __ENV.TARGET_URL  || ENV_PRESETS[TARGET_ENV] || ENV_PRESETS.internal;
const CACHE_BUST   = (__ENV.CACHE_BUST || 'false') === 'true'; // ?_=ts 쿼리로 캐시 무효화
const STEP_VUS     = parseInt(__ENV.STEP_VUS   || '10');
const STEP_HOLD_S  = parseInt(__ENV.STEP_HOLD  || '60');
const MAX_VUS      = parseInt(__ENV.MAX_VUS    || '200');
const P95_LIMIT_MS = parseInt(__ENV.P95_LIMIT  || '3000');
// STRESS=true: sleep 제거 → VU수 = 실제 동시 연결수 (서버 한계 탐색)
// 기본(false): sleep 1~2s → 실 사용자 패턴 시뮬레이션
const STRESS_MODE  = (__ENV.STRESS || 'false') === 'true';

// Cloudflare 경유 여부 자동 감지
const VIA_CF = TARGET_URL.startsWith('https://') && !TARGET_URL.includes('192.168');

// 테스트 대상 경로
const PATHS = [
  '/',
  '/index.html',
  '/assets/role-content.js',
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

// ── 실시간 로그 헬퍼 ──────────────────────────────────────────────────
function speedIcon(ms) {
  if (ms <  500) return 'FAST  ';
  if (ms < 1500) return 'OK    ';
  if (ms < 2500) return 'SLOW  ';
  return             'DANGER';
}

// ── 메인 테스트 로직 ──────────────────────────────────────────────────
export default function () {
  const vusNow   = exec.instance.vusActive;
  const stepVUs  = Math.ceil(vusNow / STEP_VUS) * STEP_VUS;
  const pathIdx  = Math.floor(Math.random() * PATHS.length);
  const path     = PATHS[pathIdx];

  // 캐시 버스팅: Cloudflare CDN을 건너뛰고 Origin까지 요청 전달
  const cacheBustParam = CACHE_BUST ? `?_=${Date.now()}` : '';
  const url = TARGET_URL + path + cacheBustParam;

  peakVUs.add(vusNow);

  const res    = http.get(url, { timeout: '12s', tags: { path, vu_bucket: String(stepVUs) }, redirects: 5 });
  const dur    = res.timings.duration;
  const ok     = res.status >= 200 && res.status < 400;
  const isSlow = dur > P95_LIMIT_MS;

  check(res, {
    'status 2xx/3xx':        (r) => r.status >= 200 && r.status < 400,
    'response < 1s':         (r) => r.timings.duration < 1000,
    `response < ${P95_LIMIT_MS}ms`: (r) => r.timings.duration < P95_LIMIT_MS,
  });

  slowRate.add(isSlow);
  if (isSlow) slowCount.add(1);
  under1s.add(dur < 1000);

  // ── 실시간 진행 로그 (VU 1 전담, 매 이터레이션) ──────────────────
  if (exec.vu.idInTest === 1) {
    const icon   = ok ? 'OK' : 'ERR';
    const speed  = speedIcon(dur);
    const vuStr  = String(vusNow).padStart(3);
    const stepNo = Math.ceil(vusNow / STEP_VUS);
    const durStr = String(Math.round(dur)).padStart(5);
    console.log(
      `[Step ${String(stepNo).padStart(2)}/${MAX_VUS / STEP_VUS}] ` +
      `VU: ${vuStr}명 | ` +
      `응답: ${durStr}ms [${speed}] | ` +
      `${icon} ${path}`
    );
  }

  // 일반 모드: 실 사용자처럼 1~2초 대기 (VU수 ≠ 동시연결수)
  // 스트레스 모드(STRESS=true): sleep 없음 → VU수 = 동시연결수
  if (!STRESS_MODE) sleep(1 + Math.random());
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

  // ── 응답속도 시각화 바 ────────────────────────────────────────────
  function bar(ratio, width) {
    const filled = Math.round(ratio * width);
    return '[' + '█'.repeat(filled) + '░'.repeat(width - filled) + ']';
  }

  // 단계별 통과/실패 시각화
  const totalSteps = MAX_VUS / STEP_VUS;
  const passedSteps = aborted ? stagesPassed : totalSteps;
  const stepsBar = Array.from({ length: totalSteps }, (_, i) => {
    const vus = (i + 1) * STEP_VUS;
    if (aborted && vus > breakingVUs) return '·';
    if (aborted && vus === breakingVUs) return '✗';
    return '✓';
  }).join('');

  // 결과 판정
  const resultLine = aborted
    ? `FAIL  P95 ${P95_LIMIT_MS}ms 초과 → ${breakingVUs}명에서 중단`
    : `PASS  ${MAX_VUS}명 동접까지 P95 < ${P95_LIMIT_MS}ms 모두 통과`;

  const p95val   = (dur['p(95)'] || 0).toFixed(0);
  const p95pct   = Math.min((dur['p(95)'] || 0) / P95_LIMIT_MS, 1);
  const p95bar   = bar(p95pct, 30);

  const modeNote = STRESS_MODE
    ? '  ※ STRESS 모드: sleep 없음 — VU수 = 실제 동시 연결수'
    : '  ※ 일반 모드: sleep 1~2s — 실 사용자 패턴 (VU수 ≠ 동시 연결수)';
  const cfNote = VIA_CF
    ? (CACHE_BUST
        ? '  ※ Cloudflare 경유 + 캐시 무효화 (Origin 부하 측정)'
        : '  ※ Cloudflare 경유 (CDN 캐시 포함 — 실 사용자 경험 측정)')
    : '  ※ NAS 직접 연결 (Cloudflare 우회 — 하드웨어 한계 측정)';

  const lines = [
    '',
    sep,
    '  WorksFree Hub 부하 테스트 결과',
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
    `  단계별 결과  (각 ${STEP_VUS}명씩 / ${STEP_HOLD_S}초 유지)`,
    `  ${stepsBar}  ← ${MAX_VUS}명`,
    `  ${Array.from({ length: totalSteps }, (_, i) => (i + 1) % 5 === 0 ? String((i + 1) * STEP_VUS).padStart(3) : '   ').join('')}`,
    '',
    ...(aborted ? [
      `  ✓ 안정 구간  : ~${stableVUs}명  (P95 기준 이내)`,
      `  ✗ 임계점     : ${breakingVUs}명  (P95 ${p95val}ms → ${P95_LIMIT_MS}ms 초과)`,
    ] : [
      `  ✓ 전 구간 통과 : ${MAX_VUS}명까지 P95 ${p95val}ms (기준 ${P95_LIMIT_MS}ms)`,
    ]),
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
    ...(aborted ? [
      div,
      '  [ 성능 개선 제안 ]',
      div,
      `  · NAS nginx: worker_processes auto; worker_connections 4096;`,
      `  · Cloudflare 캐시 TTL 연장으로 Origin 요청 비율 낮추기`,
      `  · gzip/brotli 압축 활성화 (HTML/JS/CSS 전송량 감소)`,
      `  · DSM 리소스 모니터에서 테스트 중 CPU/RAM/Network 확인`,
      '',
    ] : [
      `  → MAX_VUS를 늘려 상한을 탐색하세요:`,
      `    k6 run --env MAX_VUS=500 --env TARGET_URL=${TARGET_URL} nas-load-test.js`,
      '',
    ]),
    sep,
    '',
  ];

  const report = lines.join('\n');

  const jsonReport = {
    meta:     { timestamp: ts, target_url: TARGET_URL, via_cloudflare: VIA_CF, cache_bust: CACHE_BUST },
    config:   { step_vus: STEP_VUS, hold_seconds: STEP_HOLD_S, max_vus: MAX_VUS, p95_limit_ms: P95_LIMIT_MS },
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
