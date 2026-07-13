# 2026-07 통합 멀티테넌트 마이그레이션 — 실행 안내

공유 Supabase DB 전체를 tenant_id 기반 멀티테넌트로 정비 + LifeArt 테넌트 활성화 + 보안 수정.
정본 위치: `70.webs/supabase/` (이 마이그레이션은 그 하위).

Supabase Dashboard → SQL Editor 에서 **번호 순서대로** 실행하세요.
각 스크립트 맨 아래 `-- 검증` 쿼리 결과를 확인하고, 문제 없으면 다음으로 진행합니다.

| # | 파일 | 내용 | 위험도 | 롤백 |
|---|------|------|--------|------|
| 00 | `00_baseline.sql` | 읽기 전용 스냅샷 (변경 없음) | 없음 | — |
| 01 | `01_fix_role_default.sql` | **신규 가입 500 버그 수정** (최우선) | 낮음 | DEFAULT 되돌리기 |
| 02 | `02_lockdown_exposed.sql` | 미보호 PII/RPC 잠금 | 낮음 | RLS disable / GRANT 복구 |
| 03 | `03_tenants_hardening.sql` | tenants RLS + LifeArt 등록 | 낮음 | — |
| 04 | `04_profiles_tenant.sql` | **profiles.tenant_id + 관리자 승격 차단** (핵심) | 중간 | 컬럼 drop |
| 05 | `05_asset_tenant_rls.sql` | 자산관리 테넌트 격리 | 중간 | 정책 원복 |
| 06 | `06_auction_tenant.sql` | 경매 북마크 tenant_id | 낮음 | 컬럼 drop |
| 07 | `07_email_tenant.sql` | 이메일/캠페인 tenant_id 추가 | 낮음 | 컬럼 drop |
| 08 | `08_lifeart_tables.sql` | LifeArt 전용 4테이블 | 낮음(신규) | DROP TABLE |
| 09 | `09_lifeart_seed.sql` | 액자 44종 시딩 | 없음 | DELETE |

## 중요

- **03 실행 후**: 검증 (a)에서 나온 `lifeart.ai.kr` 의 **id(UUID)를 저(Claude)에게 알려주세요.** 사이트 코드의 `TENANT_UUID` 상수에 넣어야 합니다.
- **01만 먼저 실행해도** 신규 가입 버그는 즉시 해소됩니다. 나머지는 이어서 진행 가능.
- 04 검증 (d) 승격 차단 테스트를 꼭 확인하세요 — 여기서 허브 데이터가 보이면 멈추고 알려주세요.
- 각 단계 실행 후 회귀 테스트 매트릭스(계획 문서)의 해당 항목을 브라우저에서 확인하는 것을 권장합니다.

## service_role 키 (08 이후 결제 흐름용)

LifeArt 결제 확정은 Cloudflare Worker(`lifeart-toss-verify`)가 service_role 키로
`lifeart_orders`/`lifeart_payments` 를 갱신합니다. Supabase → Settings → API →
`service_role` 키를 저에게 주시거나, 직접 아래로 등록해 주세요:

```
cd lifeart-web/worker/lifeart-toss-verify
wrangler secret put SUPABASE_SERVICE_ROLE_KEY
```
