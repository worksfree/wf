-- ================================================================
-- LifeArt 테넌트 데이터 export (자기 테넌트 데이터만)
--
-- 용도: 공유 DB에서 tenant='lifeart' 데이터만 추출.
--       다른 고객사/허브 데이터는 절대 포함되지 않음.
-- 실행: Supabase SQL Editor(service_role 세션) 또는 psql.
--       각 쿼리 결과를 CSV로 내려받거나, INSERT 문으로 변환해 보관.
--
-- 두 부분으로 나뉨:
--   [A] public 테이블 데이터 — 단순 SELECT, CSV export 가능
--   [B] auth.users 계정 — auth 스키마 접근(service_role 필수),
--       비밀번호 bcrypt 해시 포함 → 독립 Supabase로 재import 가능
--       (Supabase 사용자 가져오기: encrypted_password 그대로 삽입 지원)
-- ================================================================

-- lifeart 테넌트 uuid (아래 쿼리들에서 재사용)
-- SELECT id FROM public.tenants WHERE domain = 'lifeart.ai.kr';

-- ─────────────────────────────────────────────────────────────
-- [A] public 테이블 — LifeArt 데이터만
-- ─────────────────────────────────────────────────────────────

-- A-1. 회원 프로필 (이름/전화/역할) — "회원정보"의 본체
SELECT p.*
FROM public.profiles p
WHERE p.tenant_id = (SELECT id FROM public.tenants WHERE domain = 'lifeart.ai.kr');

-- A-2. 상품
SELECT * FROM public.lifeart_products
WHERE tenant_id = (SELECT id FROM public.tenants WHERE domain = 'lifeart.ai.kr');

-- A-3. 주문
SELECT * FROM public.lifeart_orders
WHERE tenant_id = (SELECT id FROM public.tenants WHERE domain = 'lifeart.ai.kr');

-- A-4. 결제
SELECT * FROM public.lifeart_payments
WHERE tenant_id = (SELECT id FROM public.tenants WHERE domain = 'lifeart.ai.kr');

-- A-5. 문의
SELECT * FROM public.lifeart_inquiries
WHERE tenant_id = (SELECT id FROM public.tenants WHERE domain = 'lifeart.ai.kr');

-- ─────────────────────────────────────────────────────────────
-- [B] auth.users 계정 — LifeArt 소속만 (profiles.tenant_id 로 식별)
--     ★ service_role 권한 필요. 비밀번호 해시 포함 → 재import 시
--       고객들이 기존 비밀번호로 그대로 로그인 가능.
--     ★ 이관 시 auth.identities 도 함께 export 권장(소셜 로그인 사용 시).
-- ─────────────────────────────────────────────────────────────

SELECT au.id, au.email, au.encrypted_password,
       au.email_confirmed_at, au.raw_user_meta_data, au.raw_app_meta_data,
       au.created_at
FROM auth.users au
JOIN public.profiles p ON p.id = au.id
WHERE p.tenant_id = (SELECT id FROM public.tenants WHERE domain = 'lifeart.ai.kr');

-- (선택) 소셜 로그인 identity
SELECT i.*
FROM auth.identities i
JOIN public.profiles p ON p.id = i.user_id
WHERE p.tenant_id = (SELECT id FROM public.tenants WHERE domain = 'lifeart.ai.kr');

-- ─────────────────────────────────────────────────────────────
-- 재import 참고 (독립 프로젝트에서)
--   1) schema_standalone.sql 실행으로 빈 스키마 생성
--   2) [B] 결과를 auth.users / auth.identities 에 삽입(encrypted_password 유지)
--   3) [A] 결과를 각 테이블에 삽입 (tenant_id 컬럼은 standalone 스키마에 없으므로 제외)
-- ─────────────────────────────────────────────────────────────
