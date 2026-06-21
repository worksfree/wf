# Supabase DB 구축 가이드

> **프로젝트**: WorksFree Hub — `portal.worksfree.kr`  
> **마지막 업데이트**: 2026-06-16  
> **책 참조**: 8장. Supabase 데이터베이스 — 회원 정보·결제·크레딧 저장

---

## 파일 구조 (현행)

```
supabase/
├── complete_db_setup.sql     ← [8장 필수] 코어 DB 전체 (v3.0) — 1회 실행
├── seed_dev.sql              ← [개발 전용] 테스트 계정 4개 (프로덕션 실행 금지)
│
├── README.md                 ← 이 파일
│
├── deprecate_01_auth_profiles.sql    ← (구버전) Stage 분리 파일 → complete로 통합됨
├── deprecate_02_credits_payments.sql
├── deprecate_03_email_marketing.sql
├── deprecate_04_admin_analytics.sql
├── deprecate_schema.sql              ← (구버전) 통합 마스터 스키마
├── deprecate_10_extensions_tables.sql
├── deprecate_20_security_rls.sql
├── deprecate_30_triggers.sql
├── deprecate_40_functions.sql
├── deprecate_50_views.sql
├── deprecate_60_external_dbs.sql
├── deprecate_70_seed_dev.sql
│
├── deprecate_archive/        ← 레거시 패치 파일 (이미 반영됨, 재실행 불필요)
└── deprecate_migration/      ← 구버전 마이그레이션 이력
```

---

## complete_db_setup.sql 포함 내용 (8장)

| 섹션 | 내용 |
|------|------|
| 1 | 확장: `pgcrypto` |
| 2 | 테이블 6개: `profiles` · `credits` · `payments` · `email_log` · `email_unsubscribes` · `page_views` |
| 3 | `is_admin()` 헬퍼 함수 (RLS 정책 전체에서 사용) |
| 4 | RLS 정책 전체 (기존 정책 정리 후 통일된 이름으로 재생성) |
| 5 | 트리거: `on_auth_user_created` · `on_auth_user_updated` |
| 6 | 관리자 함수 6개: `admin_set_user_role` · `admin_grant_credits` · `admin_set_user_name` · `admin_get_all_profiles` · `admin_get_user_logins` · `admin_page_view_stats` |
| 7 | 일반 함수 3개: `get_user_credit_balance` · `deduct_credits` · `get_email_history` |
| 8 | 뷰 2개: `credit_balance` · `page_view_stats` |
| 9 | 기존 사용자 소급 동기화 (name/email 백필) |
| 10 | 최종 검증 SELECT 쿼리 |

---

## 실행 방법

**Supabase 대시보드 → SQL Editor에서 순서대로 실행**

```
# Step 1 — 코어 DB 구축 (8장)
complete_db_setup.sql

# Step 2 — 개발 테스트 계정 생성 (dev 환경만, 프로덕션 실행 금지)
seed_dev.sql
```

**메뉴 경로**: Supabase → SQL Editor → New query → `.sql` 전체 내용 붙여넣기 → Run

> **멱등성**: 모든 파일은 반복 실행해도 안전합니다 (`CREATE ... IF NOT EXISTS`, `OR REPLACE`).

---

## 실행 후 검증 포인트

`complete_db_setup.sql` 실행 후 Results 패널에서 확인:

| 섹션 | 기대 결과 |
|------|-----------|
| `=== 1. 테이블 목록 ===` | 6개 테이블 모두 표시 |
| `=== 2. email_log 컬럼 ===` | `sender_user_id` 포함 전체 컬럼 목록 |
| `=== 3. RLS 정책 ===` | 각 테이블의 정책 목록 확인 |
| `=== 4. 함수 목록 ===` | 12개 함수 모두 표시 |
| `=== 5. 트리거 ===` | `on_auth_user_created`, `on_auth_user_updated` 2개 |
| `=== 7. 뷰 목록 ===` | `credit_balance`, `page_view_stats` 2개 |

`seed_dev.sql` 실행 후:

| 항목 | 기대 결과 |
|------|-----------|
| `=== 6. 개발 테스트 사용자 ===` | 4명 (member/consultant/partner/admin) roles 확인 |

---

## Dev 테스트 계정 (`seed_dev.sql` 실행 후)

| 이메일 | 이름 | 역할 | UUID |
|--------|------|------|------|
| `test@worksfree.co.kr` | 홍길동 | member | `d0000001-0000-4000-8000-000000000000` |
| `consultant@worksfree.co.kr` | 이경영 | consultant | `d0000002-0000-4000-8000-000000000000` |
| `partner@worksfree.co.kr` | 박동훈 | partner | `d0000003-0000-4000-8000-000000000000` |
| `admin@worksfree.co.kr` | 관리자 | admin | `d0000004-0000-4000-8000-000000000000` |

비밀번호: `TestPassword123!` (관리자: `AdminPassword123!`)

---

## 테이블 스키마 요약

```
profiles          → id, name, email, role, agreed_at, marketing_agreed, created_at
credits           → id, user_id, delta, reason, app_id, ref_order_id, note, env, created_at
payments          → id, user_id, order_id, pg, amount_krw, amount_usd, credits, status, env, created_at
email_log         → id, sent_at, recipient_email, sender_email, sender_name,
                    sender_user_id (FK→profiles), flyer_src, flyer_name, subject, env, status, extra
email_unsubscribes → id, email, source, note, unsubscribed_at
page_views        → id, user_id, page, duration_s, env, viewed_at
```

---

## RLS 정책 요약

| 테이블 | 정책 | 대상 |
|--------|------|------|
| profiles | `profiles_self` (ALL) | 본인 행 |
| profiles | `profiles_admin_select_all` (SELECT) | 관리자 전체 조회 |
| credits | `credits_select_own` (SELECT) | 본인 행 |
| credits | `credits_insert_purchase` (INSERT) | 본인 충전만 허용 |
| payments | `payments_select_own`, `payments_insert_own` | 본인 행 |
| email_log | `email_log_admin_select` (SELECT) | 관리자만, INSERT는 Worker service_role |
| email_unsubscribes | `email_unsubscribes_admin` (ALL) | 관리자만 |
| page_views | `pv_insert_own` · `pv_select_own` · `pv_update_own` | 본인 행 |
| page_views | `pv_admin_select` (SELECT) | 관리자 전체 조회 |

> `credits`·`payments` env 컬럼: test/staging/portal 환경이 동일 DB를 공유할 때 결제·크레딧 데이터를 환경별로 분리하는 컬럼.

---

## 환경 변수 설정

`index.html` 상단:
```javascript
const SUPABASE_URL  = 'https://<your-project>.supabase.co';
const SUPABASE_ANON = 'eyJ...';  // anon 키 (RLS 보호, 브라우저 노출 의도적)
```

Cloudflare Workers Secrets (브라우저 비노출):
```bash
# send-mail Worker (이메일 발송)
wrangler secret put SUPABASE_URL         --config service/payment/wrangler-mail.toml
wrangler secret put SUPABASE_SERVICE_KEY --config service/payment/wrangler-mail.toml

# biz-db Worker (DART 조회)
wrangler secret put SUPABASE_URL         --config consulting/bizdb/wrangler.toml
wrangler secret put SUPABASE_SERVICE_KEY --config consulting/bizdb/wrangler.toml
```
