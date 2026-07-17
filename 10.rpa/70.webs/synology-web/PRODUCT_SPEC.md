# WorksFree Hub — 제품 명세서 (GS인증 대응)

**버전**: 0.8.5.32 · **작성일**: 2026-07-01  
**제품명**: WorksFree Hub — B2B 마케팅 자동화 플랫폼  
**개발사**: WorksFree · **문의**: support@worksfree.kr

---

## 목차

1. [서비스 개요](#1-서비스-개요)
2. [시스템 아키텍처](#2-시스템-아키텍처)
3. [주요 기능 명세](#3-주요-기능-명세)
4. [기술 스택](#4-기술-스택)
5. [API 명세](#5-api-명세)
6. [보안 설계](#6-보안-설계)
7. [데이터베이스 스키마](#7-데이터베이스-스키마)
8. [배포 가이드](#8-배포-가이드)
9. [사용자 가이드](#9-사용자-가이드)
10. [테스트 가이드](#10-테스트-가이드)
11. [벤치마크 및 차별화](#11-벤치마크-및-차별화)
12. [알려진 제한사항](#12-알려진-제한사항)
13. [변경 이력](#13-변경-이력)

---

## 1. 서비스 개요

WorksFree Hub는 **한국 중소기업 대상 B2B 마케팅 자동화** 플랫폼입니다.  
DART(금융감독원 전자공시) 공개 데이터 기반 기업 이메일 DB 구축 →  
마케팅 자료 대량 이메일 발송의 전체 파이프라인을 단일 웹앱으로 제공합니다.

### 핵심 가치 제안

| 기존 방식 | WorksFree Hub |
|---------|-------------|
| 이메일 DB 별도 구매 (수백만원) | DART 공시 기반 자동 수집 (무료) |
| 발송 도구 별도 가입·관리 | 수집 + 발송 통합 워크플로우 |
| 수동 중복 제거·수신거부 관리 | DB 자동 중복 처리 + 수신거부 자동 필터 |
| CSV 파일 수동 교환 | 완전 DB 기반 관리 (CSV는 부가 기능) |

### 대상 사용자 (역할 체계)

| 역할 | 코드 (`profiles.role`) | 접근 범위 |
|------|------|---------|
| 비회원 | `non-member` | 공개 서비스 (QR, 파일명 복원 등) |
| 일반 회원 | `member` | 앱스토어 (솔리드웍스·기타 앱) |
| 컨설턴트 | `consultant` | 컨설팅·재무·파일럿 전체 |
| 파트너 | `partner` | 컨설턴트 전체 + 보험 중심 콘텐츠 (GFC) |
| 관리자 | `admin` | 전체 기능 + O&M 관리 (사용자·채용·시스템) |

> `canConsult()` = consultant ∨ partner ∨ admin  
> `IS_PARTNER` = partner ∨ admin (GFC 보험 콘텐츠 활성화)

---

## 2. 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────┐
│                  사용자 브라우저 (SPA)                      │
│  index.html (WorksFree Hub — Vanilla JS SPA)            │
│  ├── consulting/bizdb/index.html   (B2B 이메일 DB)       │
│  ├── consulting/marketing/index.html  (마케팅 자료)       │
│  ├── consulting/gfc/index.html     (GFC 진단 도구)       │
│  └── admin/recruit/index.html      (채용 관리)           │
└────────────────┬────────────────────────────────────────┘
                 │ HTTPS (Cloudflare Tunnel)
┌────────────────▼────────────────────────────────────────┐
│  Cloudflare Workers (서버리스 Edge, 전세계 CDN)            │
│  ├── dart-api-worker.worksfree.workers.dev              │
│  │     DART 공시 API 프록시 (기업 목록·정보 조회)           │
│  ├── biz-db.worksfree.workers.dev                       │
│  │     B2B 연락처 DB 관리 (Supabase REST 래퍼)            │
│  └── send-mail.worksfree.workers.dev                    │
│        이메일 발송 (Resend API) + KV 월별 카운터           │
└────────────────┬────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────┐
│  외부 서비스 (관리형 SaaS)                                  │
│  ├── Supabase  (PostgreSQL 15 + Auth + RLS)             │
│  ├── Resend    (이메일 발송 API, 월 3,000건 무료)          │
│  ├── DART API  (금감원 전자공시, 일일 10,000건 무료)        │
│  └── Cloudflare KV  (발송 월별 카운터)                    │
└─────────────────────────────────────────────────────────┘

배포 환경:
  시놀로지 NAS ←→ Cloudflare Tunnel ←→ 인터넷
  포트: test(8081) · staging(8082) · www(8080)
```

### 인증 흐름

```
브라우저 → Supabase Auth (OAuth/Email)
  → profiles 테이블 role 확인
  → Hub 역할 적용 (메뉴 표시·콘텐츠 분기)
  → onAuthComplete() 실행
      ├─ URL hash 존재 → navigateToHash(hash)  (딥링크 복원)
      └─ hash 없음    → showHome()             (섹션 타일 홈)
  → iframe postMessage { type:'wf_role', role } 전달
  → 각 iframe 페이지에서 역할별 UI 렌더
```

### Hub-and-Spoke 네비게이션 아키텍처

v0.8.5에서 도입한 **허브 앤 스포크(Hub-and-Spoke)** 구조:

```
홈 (Hub)
  → 섹션 타일 6개 (서비스/컨설팅/재무관리/파일럿/앱스토어/O&M)
      → 섹션 대시 (Spoke)
          → 사이드바: 해당 섹션 메뉴만 표시
          → 기능 카드 → iframe (Leaf)
```

- **홈**: `showHome()` — 전체 사이드바 복원 + 섹션 타일 화면
- **섹션 진입**: `showSectionDash(node)` — 사이드바를 해당 섹션 메뉴로 필터링
- **리프 페이지**: `loadIframe()` — `_activateSectionForIframe()`로 자동 섹션 감지
- **URL 복원**: 새로고침 시 `location.hash`로 상태 복원 (sessionStorage 불사용)

### Hash 기반 URL 라우팅

```
URL 형식:  https://www.worksfree.kr/#섹션slug/서브path
예시:       #consulting/ceo    →  컨설팅 > CEO 플랜
           #finance           →  재무관리 섹션 대시
           #service/qr        →  서비스 > QR 생성기

iframeToSlug(src)  :  iframe 경로 → URL slug 변환
navigateToHash(h)  :  hash → 섹션 대시 또는 리프 iframe 라우팅
```

---

## 3. 주요 기능 명세

### 3.1 B2B 이메일 DB 수집 (`consulting/bizdb`)

| 기능 ID | 기능명 | 설명 | 역할 |
|---------|------|------|------|
| BDB-01 | DART 기업 목록 조회 | 분기·업종·상장구분 필터, 페이지별 100개사 | admin |
| BDB-02 | 홈페이지 이메일 스크래핑 | 메인 + contact/about 페이지 2단계 탐색 | admin |
| BDB-03 | 전체 자동 수집 | 300페이지 순차 자동 처리, 3개 병렬 | admin |
| BDB-04 | 사전 API 확인 | 수집 전 DART 한도 1건 시험 조회 | admin |
| BDB-05 | 한도 초과 감지 | DART status 010/013 → 자동 중지 + 자정 재시작 | admin |
| BDB-06 | 이어받기 | localStorage 기반 마지막 페이지 저장 | admin |
| BDB-07 | DB 현황 조회 | 업종·상태 필터, 페이지네이션, 검색 | admin |
| BDB-08 | CSV 내보내기 | 필터 조건 기반 전체 내보내기 | admin |
| BDB-09 | 이번달 발송 목록 | 미발송 기업 필터링 후 CSV 생성 | admin |
| BDB-10 | Worker 진단 | DART·BizDB Worker 연결 상태 확인 | admin |

### 3.2 마케팅 이메일 발송 (`consulting/marketing`)

| 기능 ID | 기능명 | 설명 | 역할 |
|---------|------|------|------|
| MKT-01 | 전단지 5종 | HTML 이메일 템플릿 (법인세·중대재해 등) | gfc+ |
| MKT-02 | 단건 발송 | 즉시 단일 수신처 발송 | gfc+ |
| MKT-03 | 대량 발송 | CSV 업로드, 월 한도 내 제한 없음 | gfc+ |
| MKT-04 | 청크 자동 분할 | 100건 초과 시 100건씩 순차 발송 | — |
| MKT-05 | 관리자 확인 사본 | 대량 발송 시 `support@worksfree.kr` 자동 추가 | — |
| MKT-06 | 수신거부 자동 필터 | `email_unsubscribes` DB 조회 → 자동 제외 | — |
| MKT-07 | 발송 이력 표시 | CSV 미리보기에서 과거 발송 배지 표시 | gfc+ |
| MKT-08 | 발송 현황 | 월별 발송건·잔여 한도 게이지 표시 | gfc+ |
| MKT-09 | 법적 필수 항목 | `(광고)` 접두어, 발신자 정보, 수신거부 링크 | — |
| MKT-10 | 본문 프리셋 | 4종 메시지 프리셋 제공 | gfc+ |

### 3.3 GFC 컨설팅 진단 (`consulting/gfc`)

| 기능 ID | 기능명 | 설명 | 역할 |
|---------|------|------|------|
| GFC-01 | 17문항 기업 진단 | 법인세·이익잉여금·승계 등 종합 분석 | consultant+ |
| GFC-02 | 역할 기반 콘텐츠 | gfc/admin: 보험 중심, 기타: 파트너 상담 언어 | — |
| GFC-03 | 절세 포인트 발굴 | 최대 14개 포인트 자동 식별 | — |
| GFC-04 | 3단계 로드맵 | 1~3개월·2~6개월·6~24개월 실행 계획 | — |
| GFC-05 | 원클릭 사례 | 8개 대표 케이스 자동 채우기 | — |
| GFC-06 | 인쇄/PDF | 결과 페이지 직접 인쇄 | — |
| GFC-07 | 다국어 | KO/EN 전환 (Hub 언어 설정 연동) | — |

### 3.4 섹션별 TREE 구조 및 접근 권한

| 섹션 slug | 섹션명 | 아이콘 | 접근 조건 | 주요 메뉴 |
|-----------|------|------|---------|---------|
| `service` | 서비스 | 🛠 | 전체 공개 | QR 생성기, 파일명 자소복원, 변환 검증, 게시판, 전자책 미리보기 |
| `consulting` | 컨설팅 | ◈ | `canConsult()` | 마인드맵, 예비창업, 소상공인, 현장클리닉, 중대재해, ESG, DART, B2B DB, 마케팅, 상속·증여, 비상장주식, 경영진단, CEO 플랜 |
| `finance` | 재무관리 | 💰 | `canConsult()` | 연금 시뮬레이터(v1/v2), 자산 통합 관리 |
| `pilot` | 파일럿 | 🧪 | 혼합 | 타코 매니저(v1/v2/v3, consultantOnly), Naver Blog Commenter |
| `app-store` | 앱스토어 | 📦 | `member+` | SolidWorks BOM 추출/속성 초기화, 도면 출력 자동화 |
| `admin` | O&M 관리 | ⚙ | `adminOnly` | 사용자 관리, 이메일 캠페인, 시스템 모니터, 콘텐츠 관리, 페이지 권한, 채용 관리 |

### 3.5 프라이버시 블러 (자산 통합 관리)

`consulting/asset/index.html` 내 **숨김처리** 토글:
- 위치: 대시보드 헤더 좌측 (타이틀과 탭 버튼 사이)
- 적용 대상: 금액 필드 (`#totalAsset`, `#totalInvest`, `#realEstateAmt`, `#otherAmt`), 테이블 금액 컬럼 (`td:nth-child(3/5/6)`), 가격 스팬 (`.amt-price`)
- 비율 필드는 블러 제외 (운용 현황 파악 허용)

---

## 4. 기술 스택

| 계층 | 기술 | 버전 | 비고 |
|------|------|------|------|
| 프론트엔드 | Vanilla HTML/CSS/JS | ES2022 | 빌드 없음, CDN 최소화 |
| 인증 | Supabase Auth | 2.x | OAuth·Email 지원 |
| DB | Supabase PostgreSQL | 15 | RLS 설정, Service Key via Worker |
| Edge 함수 | Cloudflare Workers | Wrangler 4.x | 3개 Worker |
| KV 스토어 | Cloudflare KV | — | 월별 발송 카운터 |
| 이메일 발송 | Resend | v1 | Batch API, 월 3,000건 무료 |
| 공시 데이터 | DART Open API | 4.x | 일일 10,000건 무료 |
| 웹서버 | Nginx (시놀로지 NAS) | 1.x | 3환경(test/staging/portal) |
| CDN/터널 | Cloudflare Tunnel | — | SSL 자동, DDoS 보호 |
| 테스트 | Playwright | 1.x | Mock + RealDB 2-layer |

---

## 5. API 명세

### 5.1 BizDB Worker

Base URL: `https://biz-db.worksfree.workers.dev`

| Method | Path | 파라미터 | 응답 | 설명 |
|--------|------|---------|------|------|
| GET | /stats | — | `{total, with_email, no_email, unsubscribed}` | 수집 통계 |
| GET | /contacts | `page, limit, status, induty, q` | `{data[], page, limit, total}` | 목록 조회 |
| POST | /contacts | body: 배열 | `{ok, count}` | upsert (corp_code 기준) |
| PATCH | /contacts/:id | body: 필드 | `{ok}` | 개별 수정 |
| DELETE | /contacts | body: `{ids[]}` | `{deleted}` | 다수 삭제 |
| GET | /contacts/export | `status, induty, q` | `{data[], total}` | 전체 내보내기 |
| GET | /scrape | `url=` | `{emails[], source, ok}` | 이메일 스크래핑 |
| GET | /sendlist | `month=YYYY-MM, limit` | `{contacts[], month, total, already_sent}` | 발송 대상 |
| POST | /sendlog | body: 배열 | `{ok, logged}` | 발송 이력 기록 |
| GET | /sent-emails | `since=YYYY-MM` | `{emails[{email,sent_at}], count}` | 발송 이메일 조회 |

### 5.2 Send-Mail Worker

Base URL: `https://send-mail.worksfree.workers.dev`

| Method | Path | 설명 |
|--------|------|------|
| GET | / | `{sent, limit, remaining, period}` — 발송 현황 |
| POST | / | 이메일 발송 (단건·대량, 100건씩 청크 자동 처리) |
| POST | /unsubscribe | `{email}` — 수신거부 등록 |

#### POST / 요청 예시

```json
{
  "emails": [
    {
      "to": "ceo@company.co.kr",
      "subject": "(광고) 법인세 절세 전략",
      "html": "<html>...</html>"
    }
  ],
  "meta": {
    "senderEmail": "consulting@worksfree.co.kr",
    "senderName":  "WorksFree 컨설팅",
    "flyerName":   "아는 대표는 이미 다했다",
    "env":         "portal"
  }
}
```

#### POST / 응답 예시

```json
{
  "success":  true,
  "sent":     5,
  "filtered": [{ "email": "unsub@corp.co.kr", "reason": "수신거부" }],
  "totalSent": 14,
  "remaining": 2986
}
```

---

## 6. 보안 설계

### 6.1 접근 제어 (2-layer)

```
Layer 1 — Hub 사이드바:
  adminOnly:true     → admin만 노출
  gfcOnly:true       → gfc+admin만 노출
  consultantOnly:true → consultant+gfc+admin만 노출
  roleOnly:'gfc'     → 지정 역할+admin만 노출

Layer 2 — 페이지 내부:
  Supabase profiles.role 직접 확인
  → admin이 아니면 #admin-gate 표시
  (URL 직접 접근 우회 차단)
```

### 6.2 SSRF 방지

`/scrape` 엔드포인트 URL 검증:

```javascript
// 허용되지 않는 패턴
- 비HTTP 프로토콜: javascript:, file:, data:, ftp:
- 루프백: localhost, 127.0.0.1
- 사설 IP: 10.x.x.x, 192.168.x.x, 172.16-31.x.x
```

### 6.3 광고 이메일 법적 준수 (정보통신망법 제50조)

| 요구사항 | 구현 방식 |
|---------|---------|
| 제목 `(광고)` 표시 | 자동 추가, UI 비활성화 불가 |
| 발신자 명칭·연락처 | 필수 입력 필드 |
| 수신거부 링크 | 모든 발송 이메일 HTML에 포함 |
| 수신거부 처리 | 클릭 → Worker `/unsubscribe` → DB 자동 등록 |
| 이후 발송 차단 | 발송 전 `email_unsubscribes` 조회 → 자동 필터 |

### 6.4 API Key 보안

| 키 | 보관 위치 | 브라우저 노출 |
|----|---------|------------|
| Resend API Key | CF Worker Secret | ❌ 없음 |
| Supabase Service Key | CF Worker Secret | ❌ 없음 |
| Supabase Anon Key | index.html 공개 | ✅ 의도적 (RLS 보호) |
| Cloudflare API Token | secrets.ps1 (gitignore) | ❌ 없음 |

### 6.5 페이지 접근 제어 (3-layer)

v0.8.3에서 추가된 **동적 페이지 권한 관리** 시스템.

```
Layer 3 — 런타임 접근 레벨 (Supabase site_config):
  full      → 정상 사용
  blur      → iframe blur(8px) + "파트너 전용" 오버레이
  readonly  → pointer-events:none + 읽기 전용 배너
  hidden    → 잠금 오버레이 (기존 방식)
```

**관리 방법**: O&M → 페이지 권한 (`admin/permissions/index.html`)

**기본 설정**:
```json
{
  "consulting/gfc/index.html": {
    "general":    "hidden",
    "member":     "hidden",
    "consultant": "blur",
    "gfc":        "full",
    "admin":      "full"
  }
}
```

**적용 흐름**:
1. 로그인 완료 시 `site_config.page_access_rules` Supabase에서 로드
2. 페이지 이동 시 `getAccessLevel(src)` 확인
3. 레벨에 따라 `applyAccessOverlay()` CSS 적용
4. iframe에 `postMessage { type:'wf_access', level }` 전달

---

## 7. 데이터베이스 스키마

### biz_contacts (B2B 연락처 DB)

```sql
CREATE TABLE biz_contacts (
  id            uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  corp_code     text        UNIQUE NOT NULL,  -- DART 기업 고유코드
  corp_name     text        NOT NULL,
  ceo_nm        text,
  induty_code   text,                         -- KSIC 코드 또는 알파벳 단일코드
  induty_name   text,
  email         text,
  email_status  text        DEFAULT 'active', -- active | unsubscribed | bounced
  email_source  text        DEFAULT 'homepage',  -- homepage | contact-page | csv | purchased | dart | manual
  scrape_status text        DEFAULT 'pending',-- pending | done | no_email | no_url | error
  hm_url        text,
  adres         text,
  created_at    timestamptz DEFAULT now(),
  updated_at    timestamptz DEFAULT now()
);
CREATE INDEX idx_biz_contacts_corp_code ON biz_contacts(corp_code);
CREATE INDEX idx_biz_contacts_email     ON biz_contacts(email);
CREATE INDEX idx_biz_contacts_status    ON biz_contacts(email_status, scrape_status);
```

### biz_send_log (발송 이력)

```sql
CREATE TABLE biz_send_log (
  id          uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  email       text        NOT NULL,
  batch_month text        NOT NULL,            -- YYYY-MM (KST 기준)
  sent_at     timestamptz DEFAULT now(),
  status      text        DEFAULT 'sent',      -- sent | failed | opened | clicked | bounced
  resend_id   text,                            -- Resend API 반환 ID
  flyer_name  text,
  subject     text,
  opened_at   timestamptz,
  clicked_at  timestamptz,
  bounced_at  timestamptz
);
CREATE INDEX idx_biz_send_log_email       ON biz_send_log(email);
CREATE INDEX idx_biz_send_log_batch_month ON biz_send_log(batch_month);
```

### biz_send_batches (발송 배치)

```sql
CREATE TABLE biz_send_batches (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  batch_name    text,          -- "2026-06 제조업 1차"
  batch_month   text NOT NULL, -- YYYY-MM
  flyer_name    text,
  subject       text,
  filter_induty text,
  total_targets int  DEFAULT 0,
  total_sent    int  DEFAULT 0,
  total_failed  int  DEFAULT 0,
  total_opened  int  DEFAULT 0,
  created_at    timestamptz DEFAULT now(),
  completed_at  timestamptz,
  notes         text
);
```

### site_config (사이트 설정 — 페이지 권한 등)

```sql
CREATE TABLE site_config (
  key        text PRIMARY KEY,  -- 'page_access_rules' 등
  value      jsonb NOT NULL DEFAULT '{}',
  updated_at timestamptz DEFAULT now()
);
-- 기본값: page_access_rules (각 페이지별 역할 접근 레벨)
-- 관리: O&M → 페이지 권한 (admin/permissions/index.html)
-- 레벨: full | blur | readonly | hidden
```

### email_unsubscribes (수신거부)

```sql
CREATE TABLE email_unsubscribes (
  id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  email           text UNIQUE NOT NULL,
  source          text DEFAULT 'link', -- link | manual
  note            text,
  unsubscribed_at timestamptz DEFAULT now()
);
```

### email_log (마케팅 이메일 발송 로그)

```sql
CREATE TABLE email_log (
  id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  sent_at         timestamptz NOT NULL DEFAULT now(),
  recipient_email text NOT NULL,
  sender_email    text,
  sender_name     text,
  sender_user_id  uuid REFERENCES profiles(id),
  flyer_src       text,
  flyer_name      text,
  subject         text,
  env             text NOT NULL DEFAULT 'portal', -- dev | test | staging | portal
  status          text NOT NULL DEFAULT 'sent',   -- sent | filtered
  extra           jsonb DEFAULT '{}'
);
```

### SQL 파일 구조

```
supabase/
├── schema.sql          ← ✅ 완전 마스터 (신규 DB 단독 생성용)
├── seed_dev.sql        ← 개발 시드 (프로덕션 금지)
├── migration_*.sql     ← 증분 이력 (schema.sql에 통합됨)
└── archive/            ← 레거시 temp_ 파일 (참고용)
```

---

## 8. 배포 가이드

### 8.1 사전 요구사항

- Node.js 18+, npm
- Wrangler CLI 4.x (`npm i -g wrangler`)
- Cloudflare 계정 (무료 플랜)
- Supabase 프로젝트 (무료 플랜)
- Resend 계정 (무료 플랜, 월 3,000건)
- 시놀로지 NAS (DSM 7.x) + Cloudflare Tunnel

### 8.2 최초 설치 순서

```
1. Supabase 프로젝트 생성
2. supabase/ 폴더 SQL 파일 실행 (스키마 초기화)
3. Cloudflare 계정 연결: wrangler login
4. Worker 배포 (아래 참조)
5. Worker Secrets 설정
6. 웹 파일 NAS 배포
7. Cloudflare Tunnel 도메인 연결
```

### 8.3 Worker 배포

```bash
# BizDB Worker
wrangler deploy --config consulting/bizdb/wrangler.toml

# Send-Mail Worker
cd service/payment
wrangler deploy --config wrangler-mail.toml
```

### 8.4 Secrets 설정

```bash
# BizDB Worker
wrangler secret put SUPABASE_URL         --config consulting/bizdb/wrangler.toml
wrangler secret put SUPABASE_SERVICE_KEY --config consulting/bizdb/wrangler.toml

# Send-Mail Worker
wrangler secret put RESEND_API_KEY       --config service/payment/wrangler-mail.toml
wrangler secret put SUPABASE_URL         --config service/payment/wrangler-mail.toml
wrangler secret put SUPABASE_SERVICE_KEY --config service/payment/wrangler-mail.toml
wrangler secret put MAIL_FROM            --config service/payment/wrangler-mail.toml
# 값: "WorksFree 컨설팅 <consulting@worksfree.co.kr>"
```

### 8.5 웹 파일 배포

```powershell
# PowerShell — synology-web 폴더에서 실행
.\deploy.ps1
# 메뉴 선택:
# [1] test     → test.worksfree.kr     (버전 BUILD 증가)
# [2] staging  → staging.worksfree.kr  (버전 PATCH 증가)
# [3] www      → www.worksfree.kr      (버전 MINOR 증가)
```

**배포 제외 파일** (`$EXCLUDE`):  
`deploy.ps1`, `deploy.bat`, `deploy.log`, `.vscode`, `*.log`, `*.bak`, `.git`, `node_modules`, `*.sh`, `.claude`, `test-results`, `playwright-report`

### 8.6 환경별 URL

| 환경 | URL | NAS 경로 | 포트 |
|------|-----|----------|------|
| 개발 | `http://localhost:3001` | — | — |
| 테스트 | `https://test.worksfree.kr` | `/volume1/web/test` | 8081 |
| 스테이징 | `https://staging.worksfree.kr` | `/volume1/web/staging` | 8082 |
| 프로덕션 | `https://www.worksfree.kr` | `/volume1/web/portal` | 8080 |

---

## 9. 사용자 가이드

### 9.1 이메일 DB 구축 (관리자)

```
[B2B 이메일 DB] → [기업 수집] 탭
  1. 수집 조건 선택: 분기, 상장구분, 업종
  2. "이미 수집한 기업 건너뛰기" 체크 유지
  3. [⚡ 전체 자동 수집] 클릭
     → DART API 사전 확인 (한도 소진 즉시 감지)
     → 300페이지 순차 처리
  4. 수집 중단: [■ 중지] — 다음 실행 시 이어받기 제안
```

> **DART API 한도**: 일일 약 10,000건 (311페이지 전체 ≈ 4일 소요)  
> **한도 초과 시**: 배너 표시 + 자동 자정 예약 → 탭 열어두면 자동 재시작

### 9.2 마케팅 이메일 발송

```
[마케팅 자료] 페이지
  1. 전단지 선택 (5종 중 택1)
  2. 제목·본문 입력 (또는 프리셋 활용)
  3. 발신자 정보 확인 (법적 필수)

  [단건 발송]
    - 이메일 주소 직접 입력 → [발송 →]

  [대량 발송 CSV]
    - CSV 파일 업로드 (기업명, 이메일 컬럼)
    - 미리보기 확인 (과거 발송 배지 확인)
    - [대량 발송 →] 클릭
```

> **월 한도**: 3,000건 (Resend 무료 플랜)  
> **관리자 확인 사본**: 모든 대량 발송 시 `support@worksfree.kr`로 자동 발송

### 9.3 CSV 파일 형식

```csv
기업명,이메일
삼성전자,ir@samsung.com
LG전자,contact@lg.com
```

- 헤더 없어도 자동 인식 (이메일 포함 컬럼 자동 탐지)
- UTF-8 BOM 권장 (Excel 한글 호환)
- 최대 3,000행 (월 한도 기준)

---

## 10. 테스트 가이드

### 10.1 자동화 테스트 실행

```bash
# 의존성 설치
npm install

# 기본 테스트 (Mock, ~2분)
npx playwright test

# 특정 모듈
npx playwright test tests/bizdb.spec.js       # B2B DB 수집
npx playwright test tests/marketing.spec.js   # 마케팅 발송
npx playwright test tests/smoke.spec.js       # 기본 페이지 로드

# 실제 DB 연동 (~10분, .env.test 필요)
PLAYWRIGHT_PROJECT=realdb npx playwright test --project=realdb

# 보고서 보기
npx playwright show-report
```

### 10.2 테스트 커버리지

| 파일 | 테스트 수 | 커버 영역 |
|------|---------|---------|
| smoke.spec.js | 10 | 페이지 로드, 기본 구조, 버전 표시 |
| navigation.spec.js | 18 | Hub-and-Spoke 섹션 네비게이션, 해시 라우팅, 딥링크, 백 버튼, 로고 홈 이동 |
| auth.spec.js | 20 | 로그인·로그아웃·동의·세션 복원·해시 기반 페이지 복원·역할별 메뉴 분기 |
| permissions.spec.js | 22 | 역할별 접근 제어 (member/consultant/partner/admin), adminOnly/consultantOnly 메뉴 가시성, getAccessLevel 블러/숨김/readonly |
| bizdb.spec.js | 16 | 수집, DB 현황, 발송, 보안 |
| marketing.spec.js | 15 | 발송 현황, 단건, 대량, 법적 항목 |
| privacy.spec.js | 8 | 자산 숨김처리 블러 토글, 금액 필드 선택적 블러 |

### 10.3 수동 인증 체크리스트 (GS인증 대응)

#### ✅ 기능 검증

- [ ] 비로그인 → 컨설팅 페이지 잠금 표시 확인
- [ ] 일반 회원 → Admin 메뉴 비노출 확인
- [ ] GFC 로그인 → 보험 용어 표시 확인
- [ ] 컨설턴트 로그인 → "파트너 상담" 언어로 전환 확인
- [ ] DART 한도 초과 시 배너 표시 + 자정 예약 설정 확인
- [ ] 대량 발송 후 Resend 대시보드에서 수신 확인
- [ ] 수신거부 이메일 발송 시 자동 필터링 동작 확인
- [ ] CSV 업로드 → 미리보기 → 발송 완료 전체 흐름
- [ ] 관리자 계정으로 확인 사본 수신 확인

#### ✅ 보안 검증

- [ ] `/scrape?url=javascript:alert(1)` → 400 응답
- [ ] `/scrape?url=http://localhost` → 403 응답
- [ ] 직접 URL로 admin 페이지 접근 시 admin-gate 표시
- [ ] Supabase Service Key 브라우저 노출 없음 (DevTools 확인)

#### ✅ 성능 검증

- [ ] 페이지 초기 로드 2초 이내
- [ ] DB 현황 1,000건 응답 1초 이내
- [ ] 100건 대량 발송 완료 15초 이내

#### ✅ 법적 준수 검증

- [ ] 발송 이메일 제목에 `(광고)` 포함 확인
- [ ] 이메일 본문 수신거부 링크 포함 확인
- [ ] 수신거부 클릭 시 DB 자동 등록 확인
- [ ] 등록된 수신거부 주소 재발송 시 필터링 확인

---

## 11. 벤치마크 및 차별화

### 경쟁 서비스 비교

| 항목 | WorksFree Hub | Apollo.io | Hunter.io | Brevo (Sendinblue) |
|------|-------------|-----------|-----------|-------------------|
| 이메일 수집 | DART 공시(무료) | 유료 DB | 도메인 검색 | — |
| 한국 중소기업 특화 | ★★★★★ | ★★☆☆☆ | ★★☆☆☆ | ★☆☆☆☆ |
| 마케팅 발송 통합 | ✅ | 별도 도구 | 별도 도구 | ✅ |
| 컨설팅 진단 도구 | ✅ | ❌ | ❌ | ❌ |
| 월 비용 | 사실상 무료 | $49+/월 | $49+/월 | $9+/월 |
| 수신거부 자동 관리 | ✅ | ✅ | ✅ | ✅ |
| 자체 서버 운영 | ✅ (NAS) | SaaS | SaaS | SaaS |
| 역할 기반 콘텐츠 | ✅ | ❌ | ❌ | ❌ |

### 핵심 차별화

1. **DART 공시 데이터 직접 통합**: 33만+ 한국 기업 데이터, 무료
2. **완전 서버리스**: CF Workers + Supabase — 별도 서버 없음, 운영비 $0
3. **수집 + 발송 통합**: 단일 플랫폼에서 DB 구축부터 발송까지
4. **역할 기반 이원화 콘텐츠**: 같은 플랫폼, 역할에 따른 다른 메시지
5. **법적 완전 준수**: 정보통신망법 요건 자동 충족

---

## 12. 알려진 제한사항

| 제한 | 현재 상태 | 해결 계획 |
|------|---------|---------|
| Resend 월 3,000건 | 무료 플랜 한도 | 유료 전환($20/월) 시 100,000건 |
| DART 일일 10,000건 | 전체 수집 약 4일 | 유료 API($) 시 무제한 |
| 이메일 오픈/클릭 추적 없음 | 구현 예정 | Resend webhook 연동 |
| 채용 관리 미구현 | 향후 개발 예정 | v0.9 로드맵 |
| 수집 이메일 정확도 ~60% | 홈페이지 파싱 한계 | AI 파싱 고도화 예정 |
| 모바일 bizdb 수집 탭 | 반응형 미지원 | v0.9 개선 |
| 발송 이력 수신확인 없음 | pixel tracking 미구현 | v1.0 |

---

## 13. 변경 이력

| 버전 | 날짜 | 변경 유형 | 주요 내용 |
|------|------|---------|---------|
| 0.8.5.32 | 2026-07-01 | 문서 | PRODUCT_SPEC.md v0.8.5 반영 (Hub-and-Spoke, 해시 라우팅, TREE 재구성, 역할 체계 정확화) |
| 0.8.5.x | 2026-06-30 | 기능 | Hub-and-Spoke 네비게이션 (홈→섹션→리프), 섹션별 사이드바 필터링, 해시 기반 URL 라우팅 (#section/slug), TREE 6섹션 재구성 (finance·pilot 분리), sessionStorage 제거·hash 복원 |
| 0.8.4.x | 2026-06-30 | 기능·버그 | 자산 통합 관리 숨김처리 버튼 헤더 좌측 재배치, portal → www URL 전체 수정, *.bak 배포 제외 추가, 로고 클릭 시 showHome() 연결 |
| 0.8.3.0 | 2026-06-05 | 기능·문서 | 페이지 권한 관리(3-layer) 추가, site_config DB 테이블, admin/permissions UI, schema.sql 통합, temp SQL 아카이브, PRODUCT_SPEC.md GS인증 수준 개정 |
| 0.8.2.0 | 2026-06-05 | 보안·버그 | SSRF 취약점 수정, DART 한도 조기 감지, monthKey KST 수정, 자정 날짜 계산 수정, 발송 버튼 중복 방지 |
| 0.8.1.x | 2026-06-04 | 기능 | 채용 관리 향후개발 오버레이, GFC 보험 이원화, 발송 현황 UI, CSV 발송 이력 배지 |
| 0.8.0.x | 2026-06-03 | 기능 | 대량 발송 100건 제한 해제, 청크 분할, 관리자 확인 사본 |
| 0.7.5.x | 2026-05-29 | 기능 | DB 수집 자동화, DART 자정 예약, 이어받기 |
| 0.7.4.x | 2026-05-22 | 기능 | 마케팅 자료, 수신거부 관리 |
| 0.7.0.x | 2026-05-12 | 기능 | GFC 컨설팅 진단 도구 |
| 0.6.0.x | 2026-04-xx | 기능 | B2B 이메일 DB 수집 기반 |
