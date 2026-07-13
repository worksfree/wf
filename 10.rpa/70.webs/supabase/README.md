# 70.webs/supabase — 공유 Supabase DB 정본(canonical)

이 폴더가 **하나의 공유 Supabase 프로젝트**에 대한 모든 스키마·마이그레이션의 단일 소스입니다.
`synology-web`(허브·경매·이메일·자산관리)과 `lifeart-web`(클라이언트 사이트)이 **같은 DB를 공유**하며,
데이터는 `tenant_id`로 격리됩니다 (비용 절감 목적의 멀티테넌시 — [[project_multitenant]]).

## 폴더 구조

```
supabase/
├── core/                            # 기존 스키마 정본 (14개). 이 DB의 "현재 모습"
│   ├── complete_db_setup.sql        #   허브 profiles/credits/payments/email_log/page_views + admin RPC
│   ├── supabase-multitenant-migration.sql  # tenants + 자산관리 tenant_id
│   ├── auction_setup.sql / auction-bookmarks-migration.sql
│   ├── campaign_v2_setup.sql / email_campaign_setup.sql / gov_contacts_setup.sql
│   └── ...
├── migration/2026-07_multitenant/   # 전면 멀티테넌트 정비 (순서 적용) — README 참조
│   ├── 00_baseline.sql ~ 07_email_tenant.sql   # 공유 DB 정비
│   ├── 08_lifeart_tables.sql / 09_lifeart_seed.sql  # lifeart_* 테이블 (공유 DB에 생성)
│   └── README.md
└── tenant-handoff/lifeart/          # 고객사 인수인계용 산출물
    ├── schema_standalone.sql        #   독립 Supabase에 LifeArt만 재생성 (tenant_id 제거본)
    └── export_lifeart_data.sql      #   tenant='lifeart' 데이터만 export (Auth 계정 포함)
```

## 테넌트 규약 (3종 혼재 — 의도된 것)

| 규약 | 컬럼 | 사용 테이블 |
|------|------|------------|
| uuid FK | `tenant_id uuid REFERENCES tenants(id)` | profiles, portfolios 계열, lifeart_* |
| bare text | `tenant_id text DEFAULT 'worksfree'` | auction_*, email/campaign 계열 |
| env(배포단계) | `env text` | credits, payments, page_views (테넌트 아님, dev/test/staging/portal) |

신규 사용자 대면 테이블은 **uuid FK 규약**을 따르세요. `env`는 배포 단계 구분이지 테넌트가 아닙니다.

## 신규 테넌트 추가 절차

1. `INSERT INTO tenants (domain, name) VALUES (...)`.
2. 테넌트 전용 테이블은 `<tenant>_` 접두사 + `tenant_id uuid NOT NULL REFERENCES tenants(id)`.
3. RLS 정책 **모든 절에 tenant 조건 포함** (portfolios처럼 컬럼만 두고 RLS에서 무시하지 말 것).
4. 관리자 판별 함수는 `is_<tenant>_admin()`로 테넌트 스코핑 (허브 `is_admin()`은 worksfree 전용).
