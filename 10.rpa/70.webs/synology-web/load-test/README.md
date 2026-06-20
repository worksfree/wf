# WorksFree Hub 부하 테스트

WorksFree Hub(synology-web) 전용 k6 부하 테스트 스크립트 모음.

## 사전 준비

```powershell
# k6 설치 확인
k6 version

# 없으면: https://github.com/grafana/k6/releases 에서 ZIP 다운로드 후
# C:\tools\k6\k6.exe 에 배치하고 PATH 추가
```

---

## 빠른 실행 — `run-load-test.ps1`

모든 테스트는 이 단일 스크립트로 실행합니다. k6 자동 탐색, 로그 저장, JSON 리포트 이름 변경까지 처리합니다.

```powershell
cd 10.rpa/70.webs/synology-web/load-test

.\run-load-test.ps1 stress                            # NAS 한계 탐색 (기본값)
.\run-load-test.ps1 stress  -MaxVUs 500 -StepVUs 50  # VU 규모 조정
.\run-load-test.ps1 stress  -Target cloudflare -CacheBust
.\run-load-test.ps1 journey -MaxVUs 300 -StepVUs 30  # 실 사용자 시뮬레이션
.\run-load-test.ps1 mixed                             # DART + 페이지 혼합 (기본값)
.\run-load-test.ps1 mixed   -DartVUs 5 -PageVUs 100 -Duration 15 -Verbose
```

인자 없이 실행하면 전체 usage가 출력됩니다:
```powershell
.\run-load-test.ps1
```

**파라미터 요약**

| 파라미터 | 모드 | 기본값 | 설명 |
|---------|------|--------|------|
| `-Target` | 공통 | `internal` | `internal` / `internal-stg` / `internal-test` / `cloudflare` / `cloudflare-stg` |
| `-Url` | 공통 | — | 직접 URL 지정 |
| `-CacheBust` | 공통 | — | CDN 캐시 우회 |
| `-MaxVUs` | stress/journey | stress:1000 / journey:300 | 최대 VU |
| `-StepVUs` | stress/journey | stress:100 / journey:30 | VU 증가 단위 |
| `-HoldSec` | stress/journey | 60 | 단계 유지(초) |
| `-P95` | stress/journey | 3000 | P95 중단 기준(ms) |
| `-DartVUs` | mixed | 5 | DART 동시 조회 VU |
| `-PageVUs` | mixed | 50 | 페이지 접속 최대 VU |
| `-Duration` | mixed | 10 | 총 테스트 시간(분) |
| `-Verbose` | mixed | — | DART 요청별 로그 |

---

## 테스트 파일

### `nas-load-test.js` — NAS 성능 한계 탐색

| 모드 | 설명 | 명령 |
|------|------|------|
| stress | VU수 = 실제 동시 연결수. NAS 하드웨어 한계 탐색 | `--env STRESS=true` |
| journey | 실 사용자 탐색 패턴 시뮬레이션 (think time 포함) | `--env TEST_MODE=journey` |

```powershell
cd load-test

# [stress] NAS 한계 탐색 — 1000명 동시 연결, 100명씩 증가 (~12분)
k6 run --env STRESS=true --env TARGET_ENV=internal --env MAX_VUS=1000 --env STEP_VUS=100 nas-load-test.js

# [journey] 실 사용자 시뮬레이션 — Flow A~E 5가지 시나리오 랜덤 실행
k6 run --env TEST_MODE=journey --env TARGET_ENV=internal --env MAX_VUS=300 --env STEP_VUS=30 nas-load-test.js

# Cloudflare 경유 테스트
k6 run --env STRESS=true --env TARGET_ENV=cloudflare --env CACHE_BUST=true nas-load-test.js
```

**journey 시나리오 (Flow A~E)**

| 시나리오 | 동선 |
|---------|------|
| Flow-A 일반방문 | 메인 → GFC 소개 |
| Flow-B CEO리드 | 메인 → CEO 컨설팅 → CEO 플라이어 |
| Flow-C GFC고객 | 메인 → GFC → GFC 컨설팅 → GFC 플라이어 |
| Flow-D 앱탐색 | 메인 → BOM Exporter → 변환 검증기 |
| Flow-E 마케팅 | 메인 → 마케팅 컨설팅 → 케이스스터디 플라이어 |

**주요 환경변수**

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `TARGET_ENV` | `internal` | `internal` / `cloudflare` / `cloudflare-stg` |
| `TARGET_URL` | — | 직접 URL 지정 시 사용 |
| `MAX_VUS` | `200` | 최대 VU 수 |
| `STEP_VUS` | `10` | VU 증가 단위 |
| `STEP_HOLD` | `60` | 각 단계 유지 시간(초) |
| `P95_LIMIT` | `3000` | P95 중단 기준(ms) |
| `STRESS` | `false` | `true` 시 sleep 제거 |
| `CACHE_BUST` | `false` | `true` 시 쿼리스트링으로 CDN 캐시 우회 |

---

### `nas-mixed-test.js` — DART 조회 + 페이지 접속 혼합 테스트

DART API 조회 사용자(5명)와 일반 페이지 접속 사용자를 동시에 실행.  
"API 조회가 진행 중일 때 페이지 접속 성능이 영향받는가?" 검증.

```powershell
cd load-test

# 기본 실행 (DART 5명 + 페이지 최대 50명, 10분)
k6 run nas-mixed-test.js

# DART 오류 상세 확인
k6 run --env VERBOSE=true nas-mixed-test.js

# 규모 조정
k6 run --env DART_VUS=5 --env PAGE_MAX_VUS=100 --env DURATION_MIN=15 nas-mixed-test.js
```

**임계값**

| 시나리오 | 기준 |
|---------|------|
| 페이지 접속 P95 | 1,000ms 이하 |
| DART 조회 P95 | 8,000ms 이하 |
| 페이지 오류율 | 1% 이하 |

**주요 환경변수**

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `DART_VUS` | `5` | DART 동시 조회 사용자 수 |
| `DART_MIN_SLEEP` | `30` | 조회 후 최소 대기(초) |
| `DART_MAX_SLEEP` | `60` | 조회 후 최대 대기(초) |
| `PAGE_MAX_VUS` | `50` | 페이지 접속 최대 VU |
| `DURATION_MIN` | `10` | 전체 테스트 시간(분) |
| `VERBOSE` | `false` | `true` 시 DART 요청별 로그 출력 |

---

### `schedule-loadtest.ps1` — 야간 자동 예약

```powershell
# 관리자 권한 PowerShell에서 실행
cd load-test

# 기본 새벽 2시 stress 테스트 예약
.\schedule-loadtest.ps1

# 시간·모드·규모 지정
.\schedule-loadtest.ps1 -RunAt 03:00 -MaxVUs 1000 -StepVUs 100
.\schedule-loadtest.ps1 -Mode mixed -RunAt 23:00 -DartVUs 5 -PageVUs 100

# 예약 취소
Unregister-ScheduledTask -TaskName 'WF-NAS-LoadTest' -Confirm:$false
```

`run-load-test.ps1`에 위임하므로, 예약 실행 시에도 동일한 로그/리포트 파일이 생성됩니다.

---

## 테스트 결과 확인

실행 후 자동 생성 (`.gitignore` 처리됨):

| 파일 | 내용 |
|------|------|
| `report-YYYYMMDD-HHmm.txt` | 전체 실행 로그 (schedule 실행 시) |
| `nas-load-test-report.json` | stress/journey 결과 JSON |
| `nas-mixed-test-report.json` | 혼합 테스트 결과 JSON |

---

## NAS 포트 매핑

| 포트 | 환경 |
|------|------|
| `:8082` | www (production) |
| `:8080` | staging |
| `:8081` | test |

## 테스트 결과 이력

| 일자 | 테스트 | 결과 |
|------|--------|------|
| 2026-06-19 | stress 1000VU | 안정 700명 / 임계 800명 (P95 3,007ms) |
| 2026-06-21 | mixed (DART 5명 + 페이지 50명) | 페이지 P95 3ms PASS / DART P95 508ms PASS |
