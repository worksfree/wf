# Supabase DB 구축 가이드

> **프로젝트**: WorksFree Hub — `portal.worksfree.kr`  
> **마지막 업데이트**: 2026-06-03

---

## 최종 DB 구조

허브 DB는 세 개의 독립 영역으로 구성됩니다.

| 영역 | 테이블 | 설명 |
|------|--------|------|
| **허브 코어** | profiles, credits, payments, email_log, email_unsubscribes, page_views | 회원 인증·크레딧·결제·이메일·방문 추적 |
| **B2B 이메일** | biz_contacts, biz_send_log | 기업 이메일 수집 및 발송 이력 |
| **잡코리아** | jobkorea_proposals | 채용 포지션 제안 자동화 |

---

## 처음부터 DB 재구축 순서

**Supabase 대시보드 → SQL Editor에서 아래 순서대로 실행**

### Step 1 — 사전 진단 (선택)
```
phase1_check_before_run.sql
```
기존 DB 상태 확인 (테이블·RLS·함수 존재 여부). 실행 후 결과만 확인, 아무것도 변경하지 않음.

### Step 2 — 허브 코어 DB 전체 구축
```
complete_db_setup.sql
```
v3.0 (2026-05-30 기준) 최신 통합본. 아래 내용을 **모두 포함**:
- `profiles`, `credits`, `payments`, `email_log`, `email_unsubscribes`, `page_views` 테이블
- 모든 RLS 정책
- 트리거: `on_auth_user_created`, `sync_profile_name`
- 함수 12개: `handle_new_user`, `deduct_credits`, `refund_credits`, `admin_set_user_role`, `admin_set_user_name`, `admin_grant_credits`, `admin_get_all_profiles`, `admin_get_user_logins`, `admin_page_view_stats`, `log_page_view`, `get_credit_balance`, `check_credit_balance`
- 뷰: `credit_balance`
- Dev 테스트 계정 4개 (auth.users + auth.identities + profiles 전체)

### Step 3 — B2B 이메일 DB
```
bizdb_setup.sql
```
`biz_contacts`, `biz_send_log` 테이블. 허브 인증과 독립적으로 동작 (Cloudflare Worker에서 service_role 키로 직접 접근).

### Step 4 — 잡코리아 DB (선택)
```
jobkorea_setup.sql
```
`jobkorea_proposals`, `jobkorea_stats` 뷰.

---

## Dev 테스트 계정

`complete_db_setup.sql` 실행 시 자동 생성됩니다.

| 이메일 | 역할 | UUID |
|--------|------|------|
| `test@worksfree.co.kr` | general | `d0000001-0000-4000-8000-000000000000` |
| `consultant@worksfree.co.kr` | consultant | `d0000002-0000-4000-8000-000000000000` |
| `gfc@worksfree.co.kr` | gfc | `d0000003-0000-4000-8000-000000000000` |
| `admin@worksfree.co.kr` | admin | `d0000004-0000-4000-8000-000000000000` |

비밀번호: 허브 Dev 툴바에서 로그인 시 자동 입력됨 (`DEV_CREDS` 참고).

---

## 파일 구조

```
supabase/
├── complete_db_setup.sql        ← 허브 코어 DB (최종, Step 2)
├── bizdb_setup.sql              ← B2B 이메일 DB (Step 3)
├── jobkorea_setup.sql           ← 잡코리아 DB (Step 4)
├── phase1_check_before_run.sql  ← 사전 진단 (선택)
│
└── tmp_*.sql                    ← 구버전·일회용 파일 (참고용만, 재실행 불필요)
    ├── tmp_master_db_setup.sql           (v2.0 구버전 — complete_db_setup.sql로 대체)
    ├── tmp_phase1_db_setup.sql           (구버전 phase 1)
    ├── tmp_phase2_email_management.sql   (구버전 phase 2)
    ├── tmp_phase3_dev_users_and_email_mgmt.sql (구버전 phase 3)
    ├── tmp_phase2_and_3_combined.sql     (phase 2+3 중간 통합본)
    ├── tmp_phase3_fix_identities.sql     (일회용: identities 누락 수정)
    ├── tmp_phase3_fix_instance_id.sql    (일회용: instance_id 누락 수정)
    ├── tmp_email_log.sql                 (중복: complete_db_setup.sql에 포함)
    ├── tmp_tracking_tables.sql           (중복: complete_db_setup.sql에 포함)
    ├── tmp_fix_profiles_name_sync.sql    (중복: complete_db_setup.sql에 포함)
    ├── tmp_admin_functions.sql           (중복: complete_db_setup.sql에 포함)
    ├── tmp_quick_fix_stats.sql           (일회용: status 컬럼·page_views 누락 패치)
    ├── tmp_update_env_filter.sql         (일회용: 함수 파라미터 변경)
    ├── tmp_fix_pageviews_rls.sql         (일회용: RLS 정책 누락 패치)
    ├── tmp_setup_page_views_complete.sql (중복: complete_db_setup.sql에 포함)
    ├── tmp_add_sender_user_id.sql        (일회용: 컬럼 추가)
    ├── tmp_fix_dev_account_names.sql     (일회용: dev 계정 이름 보정)
    ├── tmp_fix_pageview_stats_env.sql    (일회용: 함수 기본값 변경)
    └── tmp_fix_dev_profiles_roles.sql    (일회용: dev profiles UPSERT 보정)
```

---

## Supabase 환경 변수 (필수)

`index.html` 상단에 하드코딩:
```javascript
const SUPABASE_URL  = 'https://rkycwfpkzorfpcxfvaqt.supabase.co';
const SUPABASE_ANON = 'eyJ...';  // anon 키
```

Cloudflare Workers Secrets:
```bash
# biz-db Worker
wrangler secret put SUPABASE_URL        --config wrangler.toml
wrangler secret put SUPABASE_SERVICE_KEY --config wrangler.toml
```
