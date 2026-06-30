# 자산 통합 관리 — 개발 스펙 (spec.md)

> 범위: 여러 계좌의 주식·ETF를 **통합 등록**하고 **시세·수익률을 조회**하는 것까지.
> **연금 수령·세금·건강보험료 시뮬레이션은 본 앱 범위 밖**(별도 앱 `spec_연금시뮬레이션.md`).
> 기존 인프라 재사용: `synology-web` 프로젝트의 Cloudflare Worker + KV + Supabase + PowerShell 배포 패턴.

---

## 1. 목적·범위

### 1.1 목적
증권 계좌가 여러 개로 흩어져 있어 전체 평가액·수익률을 한눈에 보기 어렵다. 종목을 통합 등록하고, **종목명만 입력하면 종목코드를 찾아 시세를 가져와** 평가손익·수익률·월배당률을 보여준다.

### 1.2 범위 (In)
- 종목 검색·등록 (종목명 → 종목코드 자동 조회)
- 계좌·보유종목·평단 등록
- 시세 조회 (지연 피드, Cloudflare Worker 경유)
- 평가손익·수익률·월배당률·통합 뷰·추세 그래프
- (옵션) 부동산·부채를 포함한 순자산 현황

### 1.3 범위 밖 (Out)
- 연금 수령 시뮬레이션, 과세(분리/분류/종합), 건강보험료·피부양자 판정 → 별도 앱.
- 증권사 계좌 API 잔고 자동 동기화 → 하지 않음(보유는 사용자 입력).

### 1.4 설계 원칙
- **폐회로**: 시세는 인증된 본인에게만 표출(공개 대시보드 금지). NAS reverse proxy + 인증.
- **보유는 입력값, 시세는 피드**: 시세 데이터만 무료 지연 소스에서 가져온다.
- 금액은 원(KRW) 정수.

---

## 2. 아키텍처

```
[React 프론트엔드]  ──(인증)──>  [Supabase: 보유·계좌·스냅샷]
       │
       └──(HTTPS)──> [Cloudflare Worker: 시세/종목코드 프록시]
                              │  KV: 종목마스터·시세 캐시
                              ├──> 네이버 차트 endpoint (1차)
                              └──> Yahoo Finance chart API (2차 폴백)

[Synology cron + Python] ──(일 1회)──> 종목 마스터 생성 → Supabase/KV 적재

[Cloudflare Cron Worker] ──(평일 09:30 KST)──> 휴일판정 → 시세조회 → 메일(Resend) + 스냅샷 기록
```

- 프론트는 정적 호스팅(Cloudflare Pages 또는 NAS) + 인증 게이트.
- **시세·종목코드는 브라우저에서 직접 호출하지 않는다**(CORS·차단 회피). Cloudflare Worker가 서버사이드로 대신 가져온다 — `send-mail` Worker와 동일한 패턴.
- 종목 마스터(코드↔이름)는 Worker가 Python으로 못 만들므로, Synology에서 Python 잡(FinanceDataReader/pykrx)으로 생성해 Supabase 또는 KV에 적재하고 Worker는 조회만 한다.

---

## 3. Cloudflare Worker 명세

### 3.1 배포·시크릿 (기존 패턴 준수)
- Worker 이름(예): `quote-api.worksfree.workers.dev`
- 배포: 기존 `deploy.ps1` 패턴 재사용(캐시 퍼지 토큰은 `CF_CACHE_PURGE_TOKEN` 사용 — 과거 `CF_API_TOKEN` 혼선 주의).
- 시크릿: `secrets.ps1`로 Worker secret 주입 (`SUPABASE_URL`, `SUPABASE_SERVICE_KEY` 등). 키는 코드/프론트에 노출 금지.
- KV 네임스페이스: `QUOTE_CACHE`(시세 캐시 TTL 단기), `INSTRUMENT_MASTER`(종목 마스터).

### 3.2 엔드포인트 계약
| 메서드/경로 | 요청 | 응답 | 비고 |
|---|---|---|---|
| `GET /search?q=삼성` | q=검색어 | `[{code,name,market,kind}]` | 자동완성용, 부분일치 |
| `GET /resolve?name=KODEX200` | name=종목명 | `{code,name,market}` | 단일 해석(가장 근접) |
| `GET /quote?code=069500` | code=6자리 | `{code,price,asOf,source,delayedMinutes,change}` | 단일 시세 |
| `GET /quotes?codes=069500,229200` | codes=콤마구분 | `[{code,price,...}]` | 배치(통합뷰 갱신용) |

### 3.3 시세 조회 로직 (폴백·캐싱)
1. KV `QUOTE_CACHE`에 신선한 값(예: 60초 이내)이 있으면 반환.
2. 없으면 **네이버 차트 endpoint**를 서버사이드 fetch → 파싱.
3. 실패 시 **Yahoo chart API**(`.KS`/`.KQ` 접미사)로 폴백.
4. 둘 다 실패 시 마지막 정상값(stale) 반환 + `stale:true` 플래그.
5. 정상 응답은 KV 캐시에 기록.
- 응답에 `source`(NAVER/YFINANCE)와 `delayedMinutes`를 포함해 프론트에 지연 표기.

### 3.4 종목 마스터 조회
- `INSTRUMENT_MASTER` KV(또는 Supabase 테이블)에서 코드↔이름 매핑을 읽어 `search`/`resolve` 처리.
- 마스터 갱신은 §4 잡이 담당. Worker는 읽기 전용.

---

## 4. 종목 마스터 갱신 잡 (Synology)
- 실행: Synology cron, 일 1회(장 시작 전).
- 내용: Python(FinanceDataReader 또는 pykrx)으로 KRX 상장 주식·ETF 목록(코드·이름·시장·종류·월배당 여부 추정)을 수집.
- 출력: JSON을 Supabase `instruments` upsert 또는 Worker KV `INSTRUMENT_MASTER`에 적재.
- 월배당 여부·분배주기는 자동 추정 후 사용자가 등록 시 보정 가능.

---

## 5. 데이터 모델 (Supabase)

> Claude Code는 아래 명세로 스키마·타입을 생성한다. 금액 bigint(원), 수량 numeric.

**accounts**: id, ownerName, name(예: "삼성증권 일반"), broker, type(`TAXABLE`/`PENSION`/`ISA` — 본 앱은 표시·분류용으로만 사용, 과세 계산 없음)

**instruments**: code(6자리 PK), name, kind(`STOCK`/`ETF`), market(KOSPI/KOSDAQ), isMonthlyDividend, distributionCycle, etfTaxType(표시용)

**holdings**: id, accountId(FK), instrumentCode(FK), quantity, avgBuyPrice(평단·제비용 포함), feesIncluded, extraFees, acquiredAt

**dividend_history**: instrumentCode(FK), payDate, amountPerShare(1주당 세전 분배금)

**quote_snapshots**: instrumentCode(FK), price, asOf, source(NAVER/YFINANCE), delayedMinutes

**portfolio_snapshots**: ownerName, asOf(date), totalValue, totalCost, cumulativeDividend — 추세 그래프용

**(옵션) real_estate / liabilities**: 순자산 현황 표시용. label, amount/balance. ※ 본 앱에서는 단순 합산만(건보료 계산 없음).

---

## 6. 기능 요구사항

- **FR-1 종목 검색·등록**: 종목명 입력 → Worker `/search` 자동완성 → 선택 시 `/resolve`로 코드 확정 → `instruments` 등록. 코드 직접 입력도 지원.
- **FR-2 보유·평단 입력**: 계좌별 종목·수량·평단 입력. 제비용 별도 입력 시 평단 자동 반영.
- **FR-3 월배당률(두 지표)**: ① 시가 배당률 = 연환산 분배금 ÷ 현재가, ② **평단 대비 배당률(YoC)** = 연환산 분배금 ÷ 평단. 월 단위 표시(예: 평단 10,000원·월 100원 → 월 1.0%, 연 12.0%).
- **FR-4 수익률**: 평가손익=(현재가−평단)×수량, 누적수익률=(평가손익+누적분배금)÷매입원가. 자본수익/인컴(배당) 분리 표기.
- **FR-5 계좌 통합 뷰**: 여러 계좌 합산 총평가액·총수익률·종목별 비중. 계좌·명의자 필터.
- **FR-6 추세 그래프**: `portfolio_snapshots` 기반 총평가액·수익률 시계열.
- **FR-7 (옵션) 순자산**: 금융자산+부동산−부채 단순 합산 표시.
- **FR-8 월배당 캘린더**: 분배주기 기반 월별 예상 배당 수령 일정.
- **FR-9 일일 현황 메일**: 평일 09:30(KST), 공휴일 제외, 그날 시세로 "오늘의 현황"을 `insung.lee@worksfree.kr`로 발송(§9 상세).

---

## 7. 화면 구성
- 대시보드: 총평가액·총수익률·일간 변동·종목별 수익률 표·월배당 캘린더.
- 종목 등록: 종목명 자동완성 검색 + 계좌·수량·평단 입력 폼.
- 종목 상세: 시가배당률/YoC, 평가손익, 분배 이력, 시세 추이.
- (옵션) 순자산 현황.

---

## 8. 비기능 요구사항
- **인증·폐회로**: 로그인 필수, 비로그인 시 시세 미표출. Supabase RLS로 본인 데이터만.
- **시세 갱신**: 통합뷰는 Worker `/quotes` 배치로 폴링(예: 1~5분), 장 마감 후 중단.
- **폴백·캐싱**: §3.3 로직. 한 소스가 깨져도 화면이 죽지 않게 stale 값 표기.
- **소스 격리**: 네이버 endpoint 변경에 대비해 Worker 내부에서 파서를 한 곳에 모아 교체 쉽게.

---

## 9. 일일 현황 메일 (스케줄 발송)

### 9.1 요구사항
- 매일 **09:30(KST)**, **월~금**, **공휴일(증시 휴장일) 제외**.
- 그날 시세를 조회해 "오늘의 현황"을 `insung.lee@worksfree.kr`로 발송.
- 발신: Resend(기존 `send-mail` Worker 패턴 재사용). 발신(from) 도메인은 **`worksfree.kr`**(먼저 설정·검증된 도메인)을 사용한다. `worksfree.com`은 현재 동작 미확인 상태이므로 Resend 도메인 검증(SPF/DKIM)이 확인되기 전까지 발신 도메인으로 쓰지 않는다.
  - 예: `from: "자산현황 <report@worksfree.kr>"`, `to: insung.lee@worksfree.kr`

### 9.2 스케줄 방식 — Cloudflare Worker Cron Trigger (권장)
- 별도 스케줄 Worker(예: `daily-report.worksfree.workers.dev`)에 Cron Trigger 설정.
- Cron은 UTC 기준 → 09:30 KST = **00:30 UTC**, 평일: `30 0 * * 1-5`.
- 동작 순서: ① 휴일 판정(§9.4) → 휴장일이면 종료 ② Supabase에서 보유·계좌 로드 ③ Worker `/quotes`로 시세 조회 ④ 평가·수익률 계산 ⑤ HTML 메일 작성 ⑥ Resend 발송 ⑦ `portfolio_snapshots`에 당일 스냅샷 기록.
- 장점: 기존 시세·메일 Worker와 같은 생태계, NAS 가동 의존 없음(서버리스).
- 대안: Synology Task Scheduler + Python(휴일 라이브러리 사용이 쉬움). NAS 상시 가동 전제면 이쪽도 가능.

### 9.3 메일 내용 (오늘의 현황)
- 총평가액 + 전일 대비 증감액·증감률
- 총수익률(매입원가 대비) + 누적 배당 포함 수익률
- 종목별 평가손익·수익률(상위/하위 변동 강조)
- 당월 예상 월배당 수령 일정(해당 시)
- 데이터 출처·지연(source/delayedMinutes) 푸터 표기

### 9.4 공휴일·휴장일 판정 (핵심)
주말은 Cron(`1-5`)으로 1차 제외. 공휴일은 코드에서 판정:
- **권장**: 공공데이터포털 "한국천문연구원_특일 정보" API로 당일 공휴일 여부 조회 → 결과를 KV에 연 단위 캐싱. 대체공휴일·임시공휴일까지 반영.
- **대안**: 정적 공휴일 JSON(연초 1회 갱신). 임시공휴일은 수동 추가 필요.
- **가장 정확(증시 기준)**: KRX 거래일 여부 확인 — 12/31 연말 휴장 등 증시만 쉬는 날까지 반영. 휴장일이면 시세도 갱신되지 않으므로 메일 생략이 자연스럽다.
- 판정이 "휴일/휴장"이면 발송하지 않고 종료.

### 9.5 시점 관련 참고
09:30은 개장(09:00) 직후 30분이라, 지연 피드(yfinance 15~20분) 기준이면 사실상 개장 무렵 시세다. 안정적인 "전일 마감 기준 아침 브리핑"을 원하면 전일 종가 요약으로 바꾸는 옵션도 설정값으로 둘 수 있다.

---

## 10. 연금 시뮬레이션 앱과의 연계점 (느슨한 결합)
- 본 앱은 **계좌별·재원별 평가액**을 산출·보관한다.
- 연금 시뮬 앱은 이 평가액(특히 연금계좌 적립금·재원 구성)을 **인풋으로 가져간다**.
- 연계 방식: 같은 Supabase를 공유하거나, 본 앱이 "연금 시뮬용 스냅샷(JSON)"을 export.
- 본 앱은 과세·건보료를 계산하지 않는다 — 그 책임은 연금 시뮬 앱.

---

## 11. 구현 우선순위
1. Supabase 스키마 + 인증 + 종목 등록 폼
2. Cloudflare Worker(`/search` `/resolve` `/quote` `/quotes`) + KV 캐시 + 폴백 (deploy.ps1/secrets.ps1 패턴)
3. 종목 마스터 갱신 잡(Synology cron + Python)
4. 평가·수익률·월배당률(FR-3,4) + 통합 뷰(FR-5)
5. 추세 그래프·월배당 캘린더 + (옵션) 순자산
6. 일일 현황 메일(Cron Worker + Resend + 휴일 판정, FR-9 / §9)
