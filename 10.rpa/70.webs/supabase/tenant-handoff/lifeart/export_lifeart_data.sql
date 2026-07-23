-- ================================================================
-- LifeArt 테넌트 데이터 export (자기 테넌트 데이터만) — v2 (2026-07-22 전면 재작성)
--
-- 용도: 공유 DB에서 tenant='lifeart' 데이터만 추출.
--       다른 고객사/허브 데이터는 절대 포함되지 않음.
-- 실행: Supabase SQL Editor(관리자/service_role 세션) 또는 psql.
--       각 쿼리를 개별 실행 후 "Export to CSV"로 받거나, psql \copy 사용.
--       그대로 재삽입하려면 import_lifeart_data.sql 참고(컬럼 순서 일치).
--
-- v1(구버전) 대비 변경: notices/faqs/press/hero_slides 4개 테이블이
--   export 대상에서 누락돼 있었음(당시 관리자 콘솔에 해당 기능이 없었음).
--   지금은 8개 lifeart_ 테이블 전부 + profiles + auth.users/identities 포함.
--   전부 SELECT * 대신 명시적 컬럼 나열 — 나중에 컬럼 순서가 바뀌어도
--   import 스크립트와 어긋나지 않도록 함(안전을 위한 의도적 설계).
--
-- 두 부분으로 나뉨:
--   [A] public 테이블 데이터 — 단순 SELECT, CSV export 가능
--   [B] auth.users / auth.identities — service_role 필수,
--       비밀번호 bcrypt 해시 포함 → 독립 Supabase로 재import 가능
-- ================================================================

-- ─────────────────────────────────────────────────────────────
-- [A] public 테이블 — LifeArt 데이터만 (8개 lifeart_ 테이블 + profiles)
-- ─────────────────────────────────────────────────────────────

-- A-0. 회원 프로필 (이름/전화/역할) — auth.users 와 1:1, import 시 반드시 회원 먼저 넣은 후 이걸로 갱신
SELECT p.id, p.name, p.phone, p.email, p.role, p.agreed_at, p.created_at
FROM public.profiles p
WHERE p.tenant_id = (SELECT id FROM public.tenants WHERE domain = 'lifeart.ai.kr')
ORDER BY p.created_at;

-- A-1. 상품 (카탈로그, 옵션상품 포함)
SELECT id, category, name, description, price, options, images, is_active, is_addon, created_at, updated_at
FROM public.lifeart_products
WHERE tenant_id = (SELECT id FROM public.tenants WHERE domain = 'lifeart.ai.kr')
ORDER BY created_at;

-- A-2. 주문 (판매 데이터 — 반드시 완전해야 함)
SELECT id, user_id, product_id, options, quantity, amount, status,
       shipping_address, shipping_status, env, created_at, updated_at
FROM public.lifeart_orders
WHERE tenant_id = (SELECT id FROM public.tenants WHERE domain = 'lifeart.ai.kr')
ORDER BY created_at;

-- A-3. 결제 (판매 데이터 — 반드시 완전해야 함)
SELECT id, order_id, pg_provider, pg_tid, amount, status, env, approved_at, created_at
FROM public.lifeart_payments
WHERE tenant_id = (SELECT id FROM public.tenants WHERE domain = 'lifeart.ai.kr')
ORDER BY created_at;

-- A-4. 문의 (관리자 답변 포함)
SELECT id, type, env, user_id, name, phone, email, message, status,
       answer, answered_at, answered_by, email_sent_at, created_at
FROM public.lifeart_inquiries
WHERE tenant_id = (SELECT id FROM public.tenants WHERE domain = 'lifeart.ai.kr')
ORDER BY created_at;

-- A-5. 공지사항 ★v1에서 누락됐던 것
SELECT id, title, body, is_published, pinned, created_at, updated_at
FROM public.lifeart_notices
WHERE tenant_id = (SELECT id FROM public.tenants WHERE domain = 'lifeart.ai.kr')
ORDER BY created_at;

-- A-6. FAQ ★v1에서 누락됐던 것
SELECT id, question, answer, sort_order, is_published, created_at, updated_at
FROM public.lifeart_faqs
WHERE tenant_id = (SELECT id FROM public.tenants WHERE domain = 'lifeart.ai.kr')
ORDER BY sort_order;

-- A-7. 보도자료 ★v1에서 누락됐던 것
SELECT id, title, outlet, summary, link_url, published_on, is_published, pinned, created_at, updated_at
FROM public.lifeart_press
WHERE tenant_id = (SELECT id FROM public.tenants WHERE domain = 'lifeart.ai.kr')
ORDER BY created_at;

-- A-8. 첫화면 히어로 슬라이드 ★v1에서 누락됐던 것
SELECT id, image_url, caption, sort_order, is_active, created_at, updated_at
FROM public.lifeart_hero_slides
WHERE tenant_id = (SELECT id FROM public.tenants WHERE domain = 'lifeart.ai.kr')
ORDER BY sort_order;

-- ─────────────────────────────────────────────────────────────
-- [B] auth.users / auth.identities — LifeArt 소속만 (profiles.tenant_id 로 식별)
--     ★ service_role 권한 필요. 비밀번호 해시 포함 → 재import 시
--       고객들이 기존 비밀번호로 그대로 로그인 가능(재발급 불필요).
-- ─────────────────────────────────────────────────────────────

-- B-1. 계정 본체 (encrypted_password 는 bcrypt 해시 — 평문 아님, 그대로 옮겨도 안전)
SELECT au.id, au.email, au.encrypted_password,
       au.email_confirmed_at, au.raw_user_meta_data, au.raw_app_meta_data,
       au.created_at, au.updated_at
FROM auth.users au
JOIN public.profiles p ON p.id = au.id
WHERE p.tenant_id = (SELECT id FROM public.tenants WHERE domain = 'lifeart.ai.kr')
ORDER BY au.created_at;

-- B-2. 소셜 로그인 identity (구글/카카오 사용 회원이 있으면 필수 — 없으면 그 회원은 소셜 로그인 재연동 필요)
SELECT i.id, i.user_id, i.identity_data, i.provider, i.provider_id,
       i.last_sign_in_at, i.created_at, i.updated_at
FROM auth.identities i
JOIN public.profiles p ON p.id = i.user_id
WHERE p.tenant_id = (SELECT id FROM public.tenants WHERE domain = 'lifeart.ai.kr')
ORDER BY i.created_at;

-- ─────────────────────────────────────────────────────────────
-- 검증: export 직전 최종 건수 스냅샷 — import 후 이 숫자와 반드시 대조할 것
-- (숫자가 다르면 이관 실패 — import_lifeart_data.sql 맨 아래 검증 쿼리와 1:1 비교)
-- ─────────────────────────────────────────────────────────────
SELECT 'profiles'      AS t, COUNT(*) FROM public.profiles      WHERE tenant_id = (SELECT id FROM public.tenants WHERE domain='lifeart.ai.kr')
UNION ALL SELECT 'products',     COUNT(*) FROM public.lifeart_products     WHERE tenant_id = (SELECT id FROM public.tenants WHERE domain='lifeart.ai.kr')
UNION ALL SELECT 'orders',       COUNT(*) FROM public.lifeart_orders       WHERE tenant_id = (SELECT id FROM public.tenants WHERE domain='lifeart.ai.kr')
UNION ALL SELECT 'payments',     COUNT(*) FROM public.lifeart_payments     WHERE tenant_id = (SELECT id FROM public.tenants WHERE domain='lifeart.ai.kr')
UNION ALL SELECT 'inquiries',    COUNT(*) FROM public.lifeart_inquiries    WHERE tenant_id = (SELECT id FROM public.tenants WHERE domain='lifeart.ai.kr')
UNION ALL SELECT 'notices',      COUNT(*) FROM public.lifeart_notices      WHERE tenant_id = (SELECT id FROM public.tenants WHERE domain='lifeart.ai.kr')
UNION ALL SELECT 'faqs',         COUNT(*) FROM public.lifeart_faqs         WHERE tenant_id = (SELECT id FROM public.tenants WHERE domain='lifeart.ai.kr')
UNION ALL SELECT 'press',        COUNT(*) FROM public.lifeart_press        WHERE tenant_id = (SELECT id FROM public.tenants WHERE domain='lifeart.ai.kr')
UNION ALL SELECT 'hero_slides',  COUNT(*) FROM public.lifeart_hero_slides  WHERE tenant_id = (SELECT id FROM public.tenants WHERE domain='lifeart.ai.kr')
UNION ALL SELECT 'auth_users',   COUNT(*) FROM auth.users au JOIN public.profiles p ON p.id=au.id WHERE p.tenant_id = (SELECT id FROM public.tenants WHERE domain='lifeart.ai.kr')
UNION ALL SELECT 'identities',   COUNT(*) FROM auth.identities i JOIN public.profiles p ON p.id=i.user_id WHERE p.tenant_id = (SELECT id FROM public.tenants WHERE domain='lifeart.ai.kr')
ORDER BY t;
