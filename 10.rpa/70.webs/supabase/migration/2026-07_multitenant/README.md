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

## 적용 상태 (2026-07-18 라이브 실측 기준)

pre-test-lifeart 경유 실측(가입·테넌트 스코핑·관리자 RPC·시연데이터 동작 + anon 감사).

| # | 스크립트 | 라이브 상태 | 근거 |
|---|----------|-------------|------|
| 01 | role default 수정 | ✅ 적용됨 | 신규 가입이 500 없이 정상 성공 |
| 04 | profiles.tenant_id + 관리자 스코핑 | ✅ 적용됨 | `lifeart_admin_get_users`가 lifeart 테넌트만 반환(타 테넌트 계정 제외) |
| 08·11·12·14·15·16·17·18 | LifeArt 테이블·O&M·보도·관리자 RPC·시연데이터 | ✅ 적용됨 | 관리자 콘솔·주문/회원/매출·히어로·시연 데이터 정상 동작 |
| 10 | dev 테스트 계정 | ✅ 적용됨 | 테스트 관리자 로그인 성공 |
| **02** | **캠페인 RPC anon 잠금** | ✅ **적용됨** (2026-07-18 PUBLIC 회수 재실행) | anon 재감사 결과 전 RPC `permission denied` — proacl 에서 `=X`(PUBLIC) 제거, `service_role=X` 유지 확인 |
| 02 | biz_contacts·profiles_backup RLS | ❓ 불명확 | anon SELECT 0행 — RLS인지 빈 테이블인지 판별 불가(유출은 미관측) |
| 03·05·06·07 | tenants RLS · 자산/경매/이메일 테넌트 | ❓ 미검증 | anon으로 판별 불가(로그인·service_role 필요) |

### 🔒 캠페인 RPC 익명 잠금 — 해소 완료 (2026-07-18)

캠페인 RPC가 익명에 열려 허브 캠페인 통계·목록이 로그인 없이 조회되던 갭.

- **1차 실행**: `proacl`에 `=X/postgres`(**PUBLIC** EXECUTE)가 남아 여전히 뚫림. 원본 02가
  `FROM anon, authenticated`만 회수했는데, 이 함수들은 PUBLIC 을 통해 열려 있어 no-op이었음.
- **수정·재실행**: `FROM PUBLIC, anon, authenticated` 회수로 변경 후 재실행 →
  `proacl`이 `{postgres=X, service_role=X}`로 정리됨.
- **anon 재감사 확인**: 전 캠페인 RPC가 `permission denied for function` 반환 → **닫힘 확정.**
  service_role 명시 부여 유지로 send-mail Worker 정상(기능 영향 0).

## 남은 보안 TODO (계획 문서에서 이관 — 별도 승인/작업 필요)

- ~~02 재실행 (캠페인 RPC 잠금)~~ ✅ 2026-07-18 해소 완료
- 03·05·06·07 라이브 적용 여부 실검증 — 원하면 로그인 기반 감사 스크립트로 확인 가능
- `portfolios` PK 재설계 (변경 위험 > 실익으로 보류, 문서화만)
- `send-mail` Worker HTTP 엔드포인트 무인증 문제 (Worker 코드 수정 필요 — 후속 논의)
- `email_campaign_setup.sql` 깨진 바이트 정리
- `profiles_backup_20260630` 삭제 여부 결정 (02로 잠기면 즉시 위험은 해소)

## service_role 키 (08 이후 결제 흐름용)

LifeArt 결제 확정은 Cloudflare Worker(`lifeart-toss-verify`)가 service_role 키로
`lifeart_orders`/`lifeart_payments` 를 갱신합니다. Supabase → Settings → API →
`service_role` 키를 저에게 주시거나, 직접 아래로 등록해 주세요:

```
cd lifeart-web/worker/lifeart-toss-verify
wrangler secret put SUPABASE_SERVICE_ROLE_KEY
```
