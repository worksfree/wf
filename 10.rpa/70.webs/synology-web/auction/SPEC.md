# 전국 경매정보 지도 서비스 — 구현 현황 문서

> 버전: 0.7.4.12 | 최종 업데이트: 2026-07-09 | 담당: insung.lee@worksfree.co.kr
> 
> ⚠️ 이 문서는 최초 기획 스펙이 아닌 **현재 구현 상태**를 반영합니다.

---

## 1. 서비스 개요

### 1.1 목적
전국 법원경매 물건 정보를 지도 위에 시각화하여, 투자자 및 실수요자가 **지역별 낙찰 시세 + 공경매 정보**를 한눈에 파악하고 투자 판단에 활용할 수 있는 웹 서비스.

**현황**: MVP 구현 완료, 실데이터 11,000건 이상 서비스 중.

### 1.2 접속 정보
- **도메인**: https://auction.worksfree.kr
- **테넌트**: worksfree
- **버전**: v0.7.4.12

---

## 2. 현재 아키텍처

```
[법원경매 사이트]
  www.courtauction.go.kr
        │ HTTPS (엣지 IP 경유)
        ▼
[Cloudflare Worker]
  auction-proxy.worksfree.workers.dev
  - 크롤 실행 (/crawl)
  - 데이터 서비스 (/data)
  - 지오코딩 (/geocode, /geocode-data)
        │ KV 저장
        ▼
[Cloudflare KV]
  data:worksfree      ← 경매 물건 JSON (11,000건+)
  meta:worksfree      ← 크롤 상태/진행 메타
  geocode:worksfree   ← 좌표 오버레이 (Worker geocode 전용)
        │
        ▼
[NAS (192.168.100.38)]
  /volume1/web/auction/
  - index.html        ← 프론트엔드 단일 파일
  - data/geocode.json ← 카카오 지오코딩 오버레이 (현재 1,600건+)
  - data/auctions.json← Python 크롤러 내보내기 (미사용)
        │ Nginx
        ▼
[브라우저] auction.worksfree.kr
```

---

## 3. 기술 스택 (실제 구현)

### 3.1 프론트엔드

| 항목 | 기술 | 비고 |
|------|------|------|
| 빌드 | 단일 HTML 파일 | 프레임워크 없음, vanilla JS |
| 지도 | **Leaflet.js 1.9.4** | OpenStreetMap 타일 사용 (카카오맵 아님) |
| 클러스터 | **Leaflet.markercluster 1.5.3** | 줌인 시 개별 마커로 분리 |
| 차트 | **Chart.js 4.4.0** | 지역 낙찰가율 추이 라인 차트 |
| 상태 | 전역 변수 (ALL, filtered, selItem 등) | |
| 인증 | **Supabase JS v2** | 구글/이메일 로그인 |
| 다국어 | 한/영 내장 (t() 함수) | |

### 3.2 백엔드 (Cloudflare Worker)

| 엔드포인트 | 설명 |
|-----------|------|
| `GET /health` | 동작 확인 |
| `GET /data?tenant=X` | 경매 데이터 조회 (공개) |
| `GET /status?tenant=X` | 크롤 상태 조회 |
| `POST /crawl?tenant=X&max=N` | 데이터 수집 실행 |
| `POST /reset?tenant=X` | 데이터 초기화 (PROXY_SECRET 필요) |
| `GET /geocode-data?tenant=X` | 지오코딩 오버레이 조회 |
| `POST /geocode?tenant=X&max=N` | 카카오 API 지오코딩 배치 (KAKAO_API_KEY 필요) |
| `POST /search` | 법원 API 프록시 (Python 크롤러용) |

### 3.3 크롤링 파이프라인

#### A. Worker 자체 크롤 (주력)
- Cloudflare 엣지 IP로 법원 API 직접 호출 → IP 차단 우회
- 매시간 크론 (`0 * * * *`) + 매주 월요일 리셋 (`0 18 * * SUN`)
- KV `data:worksfree`에 JSON 저장
- 최대 500건/실행, 이어서 수집 (next_page 기록)

#### B. Python 크롤러 (로컬 보조)
- 위치: `auction/crawler/`
- 법원 경매 + MOLIT 실거래가 + 카카오 지오코딩
- SQLite (`auction.db`) → `auctions.json` 내보내기
- 현재는 Worker 크롤이 주력이므로 보조 역할

### 3.4 지오코딩 시스템

**좌표 우선순위**:
```
1순위: geocode.json 오버레이 (카카오 API 정밀 좌표)
2순위: 법원 API 제공 좌표 (소수점 4자리 이상 + 비정수값)
3순위: 행정구역 중심점 + 결정론적 지터 (반경 ±1.6km)
```

**오버레이 적용 흐름**:
1. Worker KV (`geocode:worksfree`) 우선 시도
2. NAS `/data/geocode.json` 폴백
3. `applyGeoOverlay()` → `item.lat/lng` 덮어쓰기 → `rebuildMarkers()`

**지오코딩 방법**:
- Python `geocode_overlay.py --max N`: 로컬 실행 후 `deploy.ps1 -Target 8`으로 배포
- Admin 패널 "지오코딩 50건 실행": Worker `/geocode` 엔드포인트 호출 (KAKAO_API_KEY 설정 필요)

**현재 커버리지** (2026-07-09 기준):
- 전체: 11,000건
- 정밀 좌표 확보: ~1,600건 (진행 중)
- 산지(山地) 주소: 카카오 API 결과 없음 → 행정구역 폴백

---

## 4. 데이터 모델

### 4.1 Worker KV 저장 구조

**`data:worksfree`** (경매 물건 JSON):
```json
{
  "generated_at": "2026-07-09T12:00:00Z",
  "count": 11000,
  "total_available": 29687,
  "items": [
    {
      "id": "2025타경5171",
      "case_number": "2025타경5171",
      "court": "성남지원",
      "type": "other",
      "sido": "경기도",
      "gu": "하남시",
      "dong": "풍산동",
      "address": "경기도 하남시 풍산동 489 (미사테스타워...)",
      "lat": null,
      "lng": null,
      "area": null,
      "floor": null,
      "yr": null,
      "app": 427000000,
      "minP": 427000000,
      "avgT": 491000000,
      "fc": 1,
      "bid_date": "2026-07-20",
      "pred": 95,
      "detail_url": "https://www.courtauction.go.kr/pgj/...",
      "is_real": true
    }
  ]
}
```

**`geocode:worksfree`** (Worker 지오코딩 오버레이):
```json
{ "2025타경5171": { "lat": 37.5526, "lng": 127.1822 }, ... }
```

### 4.2 NAS 파일 구조

```
/volume1/web/auction/
├── index.html          ← 전체 앱 (단일 파일)
├── data/
│   ├── geocode.json    ← 지오코딩 오버레이 (Python 생성)
│   └── auctions.json   ← Python 크롤러 내보내기 (미사용)
```

### 4.3 로컬 SQLite (Python 크롤러용)

```sql
auction_items      -- 경매 물건 (case_number UNIQUE)
real_estate_trades -- 실거래가
geocode_cache      -- 주소→좌표 캐시
```

---

## 5. 구현된 기능

### 5.1 지도 뷰
- Leaflet + MarkerCluster 클러스터링
- 마커 클릭 → `selectItem()` → 상세 패널 열기 + 지도 줌인
- `cluster.zoomToShowLayer(marker, callback)` → 개별 마커 레벨까지 줌인
- `_markerLookup` 딕셔너리로 O(1) 마커 접근
- 근사 좌표 마커: 점선 원형 아이콘 (isApprox=true)
- 지도 이동/줌 → `applyFilter()` → `renderList()` 재정렬 (지도 중심 거리순)

### 5.2 필터
- 물건 종류: 아파트 / 단독·다가구 / 상가·업무 / 토지
- 지역: 시도 선택 (전체 지역 포함)
- 유찰횟수: 전체 / 신건(0) / 1회 이상 / 2회 이상
- 입찰기일: 전체 / 이번 주 / 이번 달
- 샘플 데이터 표시 토글 (142건 목업)

### 5.3 물건 목록
- 클러스터 모드: 입찰기일 오름차순
- 지도 모드: 지도 중심 거리 가까운 순
- 항목 클릭 → 상세 패널 + 지도 줌인

### 5.4 상세 패널
| 섹션 | 내용 |
|------|------|
| 주소/사건번호 | 원문 주소 + 법원명 |
| 기본 정보 | 면적(미제공 표시), 입찰기일, 유찰횟수, 관할법원 |
| 가격 비교 | 평균매매가 / 감정가 / 최저입찰가 수평 바 |
| 낙찰 예측 | 지역 낙찰가율 기준 % |
| 지역 낙찰가율 추이 | 최근 6개월 라인 차트 |
| 최근 실거래 | 동일 동 실거래 내역 |
| 법원경매 원문 보기 | 법원 검색 폼으로 이동 (사건번호 자동 입력) |

### 5.5 관리자 패널 (관리자 로그인 후)
- 데이터 업데이트: Worker `/crawl` 트리거
- 크롤 상태 폴링: 실시간 진행률 표시
- 지오코딩 50건 실행: Worker `/geocode` 트리거 (KAKAO_API_KEY 필요)
- 샘플 데이터 보기 토글

### 5.6 인증
- Supabase Auth (구글 OAuth)
- 로그인한 사용자만 관심 물건 북마크 가능
- 관리자(`insung.lee@worksfree.co.kr`): 관리 패널 접근

---

## 6. 알려진 제한사항 및 미구현 사항

### 6.1 면적 데이터 없음
- **원인**: 법원 API 목록 응답(`dlt_srchResult`)에 면적 필드가 없거나 미확인
  - Worker `parseItem()`에 `objctAr` / `objctArDts` 추출 코드 추가했으나 실제 반환 여부 미확인
  - 정확한 면적은 상세 페이지(`PGJ151F02.xml`) 크롤 필요
- **현재 표시**: "면적 미제공"
- **해결책**: 상세 페이지 개별 크롤러 구현 (추후 과제)

### 6.2 산지·미등록 주소 좌표 부정확
- **원인**: 카카오 API가 "산38-1" 같은 임야 지번 좌표를 반환하지 못함
- **현재 처리**: 행정구역 중심점 + ±1.6km 지터 (근사 위치)
- **마커 표시**: 점선 원형 아이콘으로 근사 좌표임을 시각적 구분

### 6.3 실거래가 데이터 미연동
- Python `molit_api.py`로 수집 가능하나 아직 Worker KV에 미포함
- 상세 패널 "최근 실거래" 섹션: 목업 데이터 사용 중

### 6.4 법원 좌표 신뢰도
- 법원 API의 `wgs84Ycordi`/`wgs84Xcordi`가 동(洞) 중심점이거나 "37.0000" 같은 기본값인 경우 있음
- `preciseCoord()` 함수로 소수점 4자리 미만 + 정수값 좌표 null 처리

### 6.5 Worker KAKAO_API_KEY 미설정
- Cloudflare Dashboard에서 수동 등록 필요
- 미등록 시 Admin 패널 "지오코딩 실행" 버튼 동작 안 함
- **설정 위치**: Cloudflare → Workers & Pages → auction-proxy → Settings → Variables → `KAKAO_API_KEY`

---

## 7. 배포 방법

### 7.1 프론트엔드 (NAS)
```powershell
.\deploy.ps1 -Target 8
```
- `auction/` 디렉토리 전체 tar+SSH로 NAS 전송
- `geocode.json` 자동 추가 업로드
- Cloudflare 캐시 자동 퍼지

### 7.2 Worker 배포
```bash
cd auction/worker
npx wrangler deploy
```

### 7.3 지오코딩 실행 (로컬)
```bash
cd auction/crawler
$env:KAKAO_API_KEY = "키값"
python geocode_overlay.py --max 2000   # 2000건 처리 후 자동 저장
python geocode_overlay.py --stats      # 현황 확인
python geocode_overlay.py --test       # API 키 확인
```
지오코딩 완료 후 `deploy.ps1 -Target 8`으로 geocode.json 배포.

### 7.4 버전 관리
- `deploy.ps1`: `$AUC_VER` 자동 증가 (배포마다 4번째 자리 +1)
- `index.html`: 배포 스크립트가 `AUC_VER` 동기화
- Worker: `wrangler deploy` 독립적으로 버전 관리

---

## 8. 환경 변수 / 설정

| 위치 | 변수명 | 값 | 용도 |
|------|--------|-----|------|
| 로컬 환경변수 | `KAKAO_API_KEY` | REST API 키 | Python 지오코딩 |
| Cloudflare Worker | `KAKAO_API_KEY` | REST API 키 | 웹 지오코딩 버튼 |
| Cloudflare Worker | `PROXY_SECRET` | 임의 문자열 | /reset 인증 |
| index.html 코드 | `SUPABASE_URL` | Supabase 프로젝트 URL | 인증/북마크 |
| index.html 코드 | `SUPABASE_ANON_KEY` | anon 키 | Supabase 접근 |
| index.html 코드 | `WORKER_URL` | Worker URL | 데이터 소스 |
| index.html 코드 | `TENANT_ID` | `worksfree` | 멀티테넌트 |

---

## 9. 로드맵

### 완료 ✅
- [x] Cloudflare Worker 크롤러 (법원 IP 우회, 전국 수집)
- [x] KV 기반 데이터 서비스
- [x] Leaflet 지도 뷰 + MarkerCluster
- [x] 물건 필터 (종류/지역/유찰/기일)
- [x] 상세 패널 (기본정보, 가격비교, 낙찰가율 차트)
- [x] 지오코딩 오버레이 (NAS fallback 포함)
- [x] 중복 제거 (Worker + 프론트엔드 dedup)
- [x] 마커 줌인 (`zoomToShowLayer`)
- [x] 목록 지도 중심 거리순 정렬
- [x] 관리자 패널 (크롤/지오코딩)
- [x] Supabase 인증 + 북마크
- [x] 다국어 한/영
- [x] 법원경매 원문 보기 (검색 폼 연동 방식으로 수정)

### 진행 중 🔄
- [ ] 지오코딩 커버리지 확대 (1,600건 → 11,000건)
- [ ] 면적 데이터 수집 방법 검토

### 미구현 ❌
- [ ] 실거래가 데이터 연동 (Worker KV에 포함)
- [ ] 면적 데이터 (상세 페이지 크롤 필요)
- [ ] 온비드 공매 데이터
- [ ] 모바일 최적화 (하단 시트 UI)
- [ ] 관심 물건 입찰기일 알림
- [ ] 낙찰가율 ML 예측 모델

---

## 10. 법적 고려사항

- 법원경매 정보: 대법원 공개 데이터, 상업적 재배포 시 이용약관 확인 필요
- 실거래가: 공공데이터 포털 이용약관 (비상업적 포함 허용)
- 크롤링: robots.txt 확인 및 서버 부하 최소화 (딜레이 적용, Cloudflare 엣지 IP 경유)
- 개인정보: 낙찰자 정보 등 개인 식별 정보 수집/저장 금지
