# LifeArt — Supabase (포인터)

LifeArt는 **비용 절감을 위해 WorksFree 공유 Supabase 프로젝트를 사용**합니다.
데이터는 `tenant_id`(= `lifeart.ai.kr` 테넌트)로 격리됩니다.

**실제 DDL/마이그레이션은 이 폴더에 없습니다.** 공유 DB 정본을 참조하세요:

- 공유 DB 정본: `../../supabase/` ([70.webs/supabase/README.md](../../supabase/README.md))
- 멀티테넌트 마이그레이션: `../../supabase/migration/2026-07_multitenant/`
  - `08_lifeart_tables.sql` — `lifeart_products/orders/payments/inquiries`
  - `09_lifeart_seed.sql` — 액자 44종 시딩
- LifeArt 관련 테이블: `lifeart_products`, `lifeart_orders`, `lifeart_payments`,
  `lifeart_inquiries`, 그리고 공유 `profiles`(role=admin·tenant=lifeart 인 행)

## 고객사 인수인계 (독립 DB로 이전 시)

`../../supabase/tenant-handoff/lifeart/` 참조:
- `schema_standalone.sql` — 빈 Supabase에 LifeArt만 재생성 (tenant_id 제거본)
- `export_lifeart_data.sql` — `tenant='lifeart'` 데이터 + 회원 계정만 export

회원 비밀번호(bcrypt 해시)까지 이관되어 기존 계정으로 로그인 유지됩니다.
