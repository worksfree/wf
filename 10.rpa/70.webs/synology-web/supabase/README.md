# Supabase DB 구축 가이드

> **프로젝트**: WorksFree Hub — `portal.worksfree.kr`  
> **마지막 업데이트**: 2026-06-05

---

## 파일 구조

```
supabase/
├── 10_extensions_tables.sql  ← [1단계] 확장 + 핵심 테이블 + 인덱스
├── 20_security_rls.sql       ← [2단계] RLS 정책
├── 30_triggers.sql           ← [3단계] 트리거
├── 40_functions.sql          ← [4단계] DB 함수
├── 50_views.sql              ← [5단계] 뷰
├── 60_external_dbs.sql       ← [6단계] 외부 서비스 DB (BizDB + 잡코리아 + 사이트설정)
├── 70_seed_dev.sql           ← [7단계] 개발용 시드 데이터 (프로덕션 실행 금지)
│
├── schema.sql                ← 전체 마스터 스키마 (신규 DB 단독 생성용, 1~7 통합본)
├── README.md                 ← 이 파일
│
├── migration/                ← 증분 마이그레이션 이력 (기존 DB 패치용)
│   ├── migration_bizdb_v2.sql       biz_send_batches 추가 + email_source CHECK 확장
│   └── migration_site_config.sql   site_config 테이블 추가
│
└── archive/                  ← 레거시 파일 (이미 10~60에 통합됨, 재실행 불필요)
    ├── bizdb_setup.sql              → 60_external_dbs.sql (A절)로 대체
    ├── jobkorea_setup.sql           → 60_external_dbs.sql (B절)로 대체
    ├── create_early_adopters.ps1    일회용 스크립트
    ├── early_adopters_result_*.csv  실행 결과 데이터
    └── temp_*.sql                   레거시 패치 (이미 schema.sql에 반영됨)
```

---

## DB 테이블 목록

| 단계 | 파일 | 테이블 / 객체 |
|------|------|--------------|
| 1 | 10_extensions_tables.sql | `profiles`, `credits`, `payments`, `email_log`, `email_unsubscribes`, `page_views` |
| 2 | 20_security_rls.sql | 위 테이블 RLS 정책 |
| 3 | 30_triggers.sql | `on_auth_user_created`, `sync_profile_name` |
| 4 | 40_functions.sql | `handle_new_user`, `deduct_credits`, `refund_credits`, `admin_*` (5개), `log_page_view`, `get_credit_balance` 등 |
| 5 | 50_views.sql | `credit_balance` |
| 6 | 60_external_dbs.sql | `biz_contacts`, `biz_send_log`, `biz_send_batches`, `jobkorea_proposals`, `jobkorea_stats`, `site_config` |
| 7 | 70_seed_dev.sql | dev 테스트 계정 4개 (auth.users · profiles) |

---

## 처음부터 DB 재구축 방법

**Supabase 대시보드 → SQL Editor에서 순서대로 실행**

```
1) 10_extensions_tables.sql
2) 20_security_rls.sql
3) 30_triggers.sql
4) 40_functions.sql
5) 50_views.sql
6) 60_external_dbs.sql
7) 70_seed_dev.sql   ← dev 환경만. 프로덕션 실행 금지
```

> **단축**: `schema.sql` 한 파일이 1~6을 모두 포함합니다.  
> 신규 DB라면 `schema.sql` → `70_seed_dev.sql` (dev만) 순서로만 실행해도 됩니다.

---

## 기존 DB에 패치 적용 (마이그레이션)

이미 운영 중인 DB에 부분 변경을 적용할 때만 사용합니다.

| 파일 | 적용 내용 | 실행 여부 확인 방법 |
|------|----------|-------------------|
| `migration/migration_bizdb_v2.sql` | `biz_send_batches` 테이블 신규 + `biz_send_log` 컬럼 추가 + `email_source` CHECK 확장 | `SELECT * FROM biz_send_batches LIMIT 1;` 오류 없으면 이미 적용됨 |
| `migration/migration_site_config.sql` | `site_config` 테이블 신규 + RLS + 기본값 | `SELECT * FROM site_config;` 결과 있으면 이미 적용됨 |

> 모든 파일은 멱등성(idempotent)으로 작성되어 있어 **중복 실행해도 안전**합니다.

---

## Dev 테스트 계정

`70_seed_dev.sql` 실행 시 자동 생성됩니다.

| 이메일 | 역할 | UUID |
|--------|------|------|
| `test@worksfree.co.kr` | general | `d0000001-0000-4000-8000-000000000000` |
| `consultant@worksfree.co.kr` | consultant | `d0000002-0000-4000-8000-000000000000` |
| `gfc@worksfree.co.kr` | gfc | `d0000003-0000-4000-8000-000000000000` |
| `admin@worksfree.co.kr` | admin | `d0000004-0000-4000-8000-000000000000` |

비밀번호: Hub Dev 툴바에서 로그인 시 자동 입력 (`DEV_CREDS` 상수 참고).

---

## Supabase 환경 변수

`index.html` 상단 하드코딩:
```javascript
const SUPABASE_URL  = 'https://rkycwfpkzorfpcxfvaqt.supabase.co';
const SUPABASE_ANON = 'eyJ...';  // anon 키 (RLS 보호, 브라우저 노출 의도적)
```

Cloudflare Workers Secrets (브라우저 비노출):
```bash
# biz-db Worker
wrangler secret put SUPABASE_URL         --config consulting/bizdb/wrangler.toml
wrangler secret put SUPABASE_SERVICE_KEY --config consulting/bizdb/wrangler.toml

# send-mail Worker
wrangler secret put SUPABASE_URL         --config service/payment/wrangler-mail.toml
wrangler secret put SUPABASE_SERVICE_KEY --config service/payment/wrangler-mail.toml
```
