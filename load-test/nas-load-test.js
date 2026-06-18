/**
 * WorksFree Hub — NAS 동접자 부하 테스트
 * =========================================
 * 목적: Synology NAS nginx가 몇 명 동접까지 처리 가능한지 측정
 *       (Supabase / Cloudflare Worker 와 무관한 순수 정적 파일 서빙 테스트)
 *
 * 실행:
 *   k6 run --env TARGET_URL=http://192.168.x.x nas-load-test.js
 *
 * 고급 옵션:
 *   k6 run \
 *     --env TARGET_URL=http://192.168.1.100 \
 *     --env STEP_VUS=10 \
 *     --env STEP_HOLD=60 \
 *     --env MAX_VUS=200 \
 *     --env P95_LIMIT=3000 \
 *     nas-load-test.js
 */

import http       from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Counter, Trend, Gauge } from 'k6/metrics';
import exec       from 'k6/execution';

// ── 설정 ──────────────────────────────────────────────────────────────
// 내부망: http://192.168.100.38  (포트 80 → 443 리다이렉트 자동 추적)
// 외부망: https://hub.worksfree.co.kr
const TARGET_URL   = __ENV.TARGET_URL  || 'http://192.168.100.38';
const STEP_VUS     = parseInt(__ENV.STEP_VUS   || '10');   // 단계별 증가 인원
const STEP_HOLD_S  = parseInt(__ENV.STEP_HOLD  || '60');   // 각 단계 유지(초)
const MAX_VUS      = parseInt(__ENV.MAX_VUS    || '200');  // 최대 가상 유저
const P95_LIMIT_MS = parseInt(__ENV.P95_LIMIT  || '3000'); // 중단 기준 (ms)

// 테스트 대상 경로 (정적 파일 — JS 실행 없음, Supabase 호출 없음)
const PATHS = [
  '/',
  '/index.html',
  '/assets/role-content.js',
];

// ── 스테이지 자동 생성 ─────────────────────────────────────────────────
// 10→20→30→...→MAX_VUS, 각 단계 10초 램프업 + STEP_HOLD_S 유지
function buildStages() {
  const stages = [];
  for (let vus = STEP_VUS; vus <= MAX_VUS; vus += STEP_VUS) {
    stages.push({ duration: '10s',            target: vus }); // 램프업
    stages.push({ duration: `${STEP_HOLD_S}s`, target: vus }); // 유지
  }
  return stages;
}

const ALL_STAGES       = buildStages();
const STAGE_DURATION_S = 10 + STEP_HOLD_S; // 단계당 총 시간(초)

// ── k6 옵션 ───────────────────────────────────────────────────────────
export const options = {
  scenarios: {
    nas_ramp: {
      executor:          'ramping-vus',
      startVUs:          0,
      stages:            ALL_STAGES,
      gracefulRampDown:  '10s',
    },
  },
  thresholds: {
    // P95 응답 시간이 기준 초과하면 15초 후 테스트 중단
    http_req_duration: [{
      threshold:      `p(95)<${P95_LIMIT_MS}`,
      abortOnFail:    true,
      delayAbortEval: '15s',
    }],
    // 오류율 10% 초과해도 중단
    http_req_failed: [{
      threshold:      'rate<0.10',
      abortOnFail:    true,
      delayAbortEval: '10s',
    }],
  },
  summaryTrendStats: ['min', 'med', 'avg', 'p(75)', 'p(90)', 'p(95)', 'p(99)', 'max', 'count'],
};

// ── 커스텀 메트릭 ─────────────────────────────────────────────────────
const slowRate    = new Rate('req_slow_rate');     // 3초 초과 비율
const slowCount   = new Counter('req_slow_count'); // 3초 초과 건수
const under1s     = new Rate('req_under_1s');      // 1초 미만 비율
const peakVUs     = new Gauge('peak_active_vus');  // 최대 동접자 스냅샷
const stageMetric = new Gauge('current_stage_vus'); // 현재 단계 VU 수

// ── 메인 테스트 로직 ──────────────────────────────────────────────────
export default function () {
  const vusNow   = exec.instance.vusActive;
  const stageVUs = Math.ceil(vusNow / STEP_VUS) * STEP_VUS;
  const path     = PATHS[Math.floor(Math.random() * PATHS.length)];
  const url      = TARGET_URL + path;

  peakVUs.add(vusNow);
  stageMetric.add(stageVUs);

  const res = http.get(url, {
    timeout: '12s',
    tags: {
      path:      path,
      vu_bucket: String(stageVUs), // 10단위 버킷 태그
    },
    redirects: 5,
  });

  const dur    = res.timings.duration;
  const ok     = res.status >= 200 && res.status < 400;
  const isSlow = dur > P95_LIMIT_MS;

  check(res, {
    '✓ 상태코드 2xx/3xx':   (r) => r.status >= 200 && r.status < 400,
    '✓ 응답 < 1초':          (r) => r.timings.duration < 1000,
    '✓ 응답 < 3초 (기준선)': (r) => r.timings.duration < P95_LIMIT_MS,
  });

  slowRate.add(isSlow);
  if (isSlow) slowCount.add(1);
  under1s.add(dur < 1000);

  // 실제 사용자 패턴: 1~2초 사이 랜덤 대기 (페이지 읽는 시간)
  sleep(1 + Math.random());
}

// ── 결과 요약 보고서 ──────────────────────────────────────────────────
export function handleSummary(data) {
  const m   = data.metrics;
  const dur = m.http_req_duration?.values  || {};
  const req = m.http_reqs?.values          || {};
  const err = m.http_req_failed?.values    || {};
  const slw = m.req_slow_count?.values     || {};
  const slr = m.req_slow_rate?.values      || {};
  const u1s = m.req_under_1s?.values       || {};

  // 테스트 실행 시간으로 임계점 VU 수 계산
  const elapsedS    = (data.state.testRunDurationMs || 0) / 1000;
  const stagesPassed = Math.floor(elapsedS / STAGE_DURATION_S);
  const breakingVUs  = Math.min((stagesPassed + 1) * STEP_VUS, MAX_VUS);
  const stableVUs    = Math.max(0, breakingVUs - STEP_VUS);

  // 테스트가 최대 VU에 도달하기 전에 중단됐는지
  const totalDurationS = ALL_STAGES.reduce((s, st) => s + parseFloat(st.duration), 0);
  const aborted        = elapsedS < totalDurationS - 5;

  const ts  = new Date().toLocaleString('ko-KR', { timeZone: 'Asia/Seoul' });
  const sep = '═'.repeat(62);
  const div = '─'.repeat(62);

  // ── 텍스트 보고서 ──────────────────────────────────────────────────
  const lines = [
    sep,
    '  WorksFree Hub — NAS 동접자 부하 테스트 결과 보고서',
    sep,
    `  실행 일시    : ${ts}`,
    `  대상 URL    : ${TARGET_URL}`,
    `  결과        : ${aborted ? '⚡ 임계점 도달 — 조기 중단' : '✅ 최대 VU까지 기준 통과'}`,
    '',
    div,
    '  [ 핵심 결과 ]',
    div,
    aborted
      ? [
          `  ⚡ 임계점 동접자   : ${breakingVUs}명`,
          `     (P95 응답 ${P95_LIMIT_MS}ms 초과 시점)`,
          `  ✅ 안정 동접자     : ${stableVUs}명 이하에서 기준 충족`,
        ].join('\n')
      : `  ✅ ${MAX_VUS}명 동접까지 P95 < ${P95_LIMIT_MS}ms 기준 모두 통과`,
    '',
    div,
    '  [ 테스트 설정 ]',
    div,
    `  가상 유저 증가 단위 : ${STEP_VUS}명`,
    `  단계별 유지 시간   : ${STEP_HOLD_S}초 (+ 10초 램프업)`,
    `  최대 가상 유저     : ${MAX_VUS}명`,
    `  응답시간 기준(P95) : ${P95_LIMIT_MS}ms`,
    `  총 테스트 시간     : ${elapsedS.toFixed(1)}초`,
    '',
    div,
    '  [ 응답 시간 분포 (ms) ]',
    div,
    `  최솟값  (min) : ${(dur.min   || 0).toFixed(1)} ms`,
    `  중앙값  (med) : ${(dur.med   || 0).toFixed(1)} ms`,
    `  평균    (avg) : ${(dur.avg   || 0).toFixed(1)} ms`,
    `  P75          : ${(dur['p(75)'] || 0).toFixed(1)} ms`,
    `  P90          : ${(dur['p(90)'] || 0).toFixed(1)} ms`,
    `  P95  ← 기준  : ${(dur['p(95)'] || 0).toFixed(1)} ms  (기준: ${P95_LIMIT_MS}ms)`,
    `  P99          : ${(dur['p(99)'] || 0).toFixed(1)} ms`,
    `  최댓값  (max) : ${(dur.max   || 0).toFixed(1)} ms`,
    '',
    div,
    '  [ 요청 통계 ]',
    div,
    `  총 요청 수         : ${(req.count || 0).toLocaleString()} 건`,
    `  초당 요청 (RPS)    : ${(req.rate  || 0).toFixed(2)} req/s`,
    `  오류율             : ${((err.rate || 0) * 100).toFixed(2)} %`,
    `  3초 초과 요청      : ${(slw.count || 0).toLocaleString()} 건 (${((slr.rate || 0) * 100).toFixed(1)}%)`,
    `  1초 미만 요청      : ${((u1s.rate || 0) * 100).toFixed(1)} %`,
    '',
    div,
    '  [ 단계별 진행 계획 ]',
    div,
    ...Array.from({ length: MAX_VUS / STEP_VUS }, (_, i) => {
      const vus     = (i + 1) * STEP_VUS;
      const isBreak = aborted && vus === breakingVUs;
      const passed  = !aborted || vus < breakingVUs;
      const marker  = isBreak ? '  ← ⚡ 임계점' : (passed ? '  ✓' : '  ·');
      return `    ${String(vus).padStart(4)}명 × ${STEP_HOLD_S}초${marker}`;
    }),
    '',
    div,
    '  [ 권장 사항 ]',
    div,
    ...(aborted ? [
      `  현재 NAS는 약 ${stableVUs}명까지 안정적으로 처리 가능합니다.`,
      `  ${breakingVUs}명에서 P95 응답이 ${P95_LIMIT_MS}ms를 초과했습니다.`,
      '',
      '  성능 개선 방안:',
      '  1. nginx.conf → worker_processes auto; worker_connections 4096;',
      '  2. 정적 파일 Cloudflare CDN 캐시 설정으로 NAS 직접 요청 감소',
      '  3. gzip/brotli 압축 활성화 (텍스트 파일 전송량 감소)',
      '  4. Synology 리소스 모니터에서 테스트 중 CPU/RAM 확인',
      '  5. nginx access_log off; 설정으로 디스크 I/O 감소',
    ] : [
      `  ${MAX_VUS}명 동접에서도 P95 응답이 ${P95_LIMIT_MS}ms 이내입니다.`,
      '  MAX_VUS 값을 늘려 더 높은 동접을 테스트해보세요.',
      `  예: k6 run --env MAX_VUS=500 --env TARGET_URL=${TARGET_URL} nas-load-test.js`,
    ]),
    '',
    sep,
    `  보고서 파일: nas-load-test-report.json`,
    sep,
  ];

  const report = lines.join('\n');

  // JSON 데이터
  const jsonReport = {
    meta: {
      timestamp:    ts,
      target_url:   TARGET_URL,
      test_aborted: aborted,
    },
    config: {
      step_vus:     STEP_VUS,
      hold_seconds: STEP_HOLD_S,
      max_vus:      MAX_VUS,
      p95_limit_ms: P95_LIMIT_MS,
    },
    result: {
      status:           aborted ? 'ABORTED_AT_THRESHOLD' : 'PASSED',
      breaking_vus:     aborted ? breakingVUs : null,
      stable_vus:       aborted ? stableVUs   : MAX_VUS,
      test_duration_s:  parseFloat(elapsedS.toFixed(1)),
    },
    response_time_ms: {
      min:  parseFloat((dur.min          || 0).toFixed(1)),
      med:  parseFloat((dur.med          || 0).toFixed(1)),
      avg:  parseFloat((dur.avg          || 0).toFixed(1)),
      p75:  parseFloat((dur['p(75)']     || 0).toFixed(1)),
      p90:  parseFloat((dur['p(90)']     || 0).toFixed(1)),
      p95:  parseFloat((dur['p(95)']     || 0).toFixed(1)),
      p99:  parseFloat((dur['p(99)']     || 0).toFixed(1)),
      max:  parseFloat((dur.max          || 0).toFixed(1)),
    },
    requests: {
      total:       req.count || 0,
      rps:         parseFloat((req.rate || 0).toFixed(2)),
      error_rate:  parseFloat(((err.rate || 0) * 100).toFixed(2)),
      slow_count:  slw.count || 0,
      slow_rate:   parseFloat(((slr.rate || 0) * 100).toFixed(1)),
      under_1s:    parseFloat(((u1s.rate || 0) * 100).toFixed(1)),
    },
  };

  return {
    'nas-load-test-report.json': JSON.stringify(jsonReport, null, 2),
    stdout: report,
  };
}
