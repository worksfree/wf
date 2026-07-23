-- ================================================================
-- LifeArt 데이터 재삽입 (import) — 신규 v2 (2026-07-22 작성)
--
-- 전제: schema_standalone.sql 을 새(빈) Supabase 프로젝트에 먼저 실행한 상태.
--       export_lifeart_data.sql 의 각 쿼리 결과를 CSV로 받아둔 상태.
--
-- 절차 개요 (반드시 이 순서 — FK 의존성 때문에 순서 바뀌면 실패함):
--   1) auth.users        (staging 테이블 경유 COPY)
--   2) auth.identities    (소셜 로그인 회원이 있을 때만)
--   3) profiles           (트리거가 만든 기본행을 실제 값으로 덮어씀 — UPSERT)
--   4) lifeart_products
--   5) lifeart_orders     (product_id/user_id 참조 — 3·4 이후)
--   6) lifeart_payments   (order_id 참조 — 5 이후)
--   7) lifeart_inquiries / notices / faqs / press / hero_slides (독립적, 순서 무관)
--
-- 사용법: 각 STEP 의 "STAGING 테이블 생성" 후, Supabase SQL Editor 좌측 상단
--   또는 psql 의 \copy 명령으로 해당 CSV 를 STAGING 테이블에 넣은 뒤,
--   바로 아래 INSERT 문을 실행하면 됩니다. (psql 예시 주석으로 포함)
-- ================================================================

-- ══════════════════════════════════════════════════════════════
-- STEP 1. auth.users
-- ══════════════════════════════════════════════════════════════
CREATE TEMP TABLE stg_users (
  id                 uuid,
  email              text,
  encrypted_password text,
  email_confirmed_at timestamptz,
  raw_user_meta_data jsonb,
  raw_app_meta_data  jsonb,
  created_at         timestamptz,
  updated_at         timestamptz
);

-- psql 사용 시: \copy stg_users FROM 'auth_users_export.csv' WITH (FORMAT csv, HEADER true)
-- SQL Editor 사용 시: Table Editor 로 stg_users 를 만든 뒤 "Import data from CSV"

INSERT INTO auth.users (
  instance_id, id, aud, role, email, encrypted_password,
  email_confirmed_at, raw_app_meta_data, raw_user_meta_data,
  created_at, updated_at, confirmation_token, recovery_token,
  email_change_token_new, email_change
)
SELECT
  '00000000-0000-0000-0000-000000000000', s.id, 'authenticated', 'authenticated',
  s.email, s.encrypted_password, s.email_confirmed_at,
  COALESCE(s.raw_app_meta_data, '{"provider":"email","providers":["email"]}'::jsonb),
  s.raw_user_meta_data, s.created_at, s.updated_at, '', '', '', ''
FROM stg_users s
ON CONFLICT (id) DO NOTHING;   -- 재실행 안전(이미 있으면 스킵)

-- ══════════════════════════════════════════════════════════════
-- STEP 2. auth.identities (소셜 로그인 회원이 있을 때만 — 없으면 이 STEP 스킵)
-- ══════════════════════════════════════════════════════════════
CREATE TEMP TABLE stg_identities (
  id              uuid,
  user_id         uuid,
  identity_data   jsonb,
  provider        text,
  provider_id     text,
  last_sign_in_at timestamptz,
  created_at      timestamptz,
  updated_at      timestamptz
);
-- \copy stg_identities FROM 'auth_identities_export.csv' WITH (FORMAT csv, HEADER true)

INSERT INTO auth.identities (id, user_id, identity_data, provider, provider_id, last_sign_in_at, created_at, updated_at)
SELECT id, user_id, identity_data, provider, provider_id, last_sign_in_at, created_at, updated_at
FROM stg_identities
ON CONFLICT (id) DO NOTHING;

-- ══════════════════════════════════════════════════════════════
-- STEP 3. profiles — on_auth_user_created 트리거가 STEP1에서 기본행을 이미
--   만들었으므로, 여기서는 UPSERT 로 실제 값(role·name·phone 등)을 덮어씀.
-- ══════════════════════════════════════════════════════════════
CREATE TEMP TABLE stg_profiles (
  id         uuid,
  name       text,
  phone      text,
  email      text,
  role       text,
  agreed_at  timestamptz,
  created_at timestamptz
);
-- \copy stg_profiles FROM 'profiles_export.csv' WITH (FORMAT csv, HEADER true)

INSERT INTO public.profiles (id, name, phone, email, role, agreed_at, created_at)
SELECT id, name, phone, email, role, agreed_at, created_at FROM stg_profiles
ON CONFLICT (id) DO UPDATE SET
  name = EXCLUDED.name, phone = EXCLUDED.phone, email = EXCLUDED.email,
  role = EXCLUDED.role, agreed_at = EXCLUDED.agreed_at;

-- ══════════════════════════════════════════════════════════════
-- STEP 4. lifeart_products
-- ══════════════════════════════════════════════════════════════
CREATE TEMP TABLE stg_products (
  id uuid, category text, name text, description text, price bigint,
  options jsonb, images jsonb, is_active boolean, is_addon boolean, created_at timestamptz, updated_at timestamptz
);
-- \copy stg_products FROM 'products_export.csv' WITH (FORMAT csv, HEADER true)

INSERT INTO public.lifeart_products (id, category, name, description, price, options, images, is_active, is_addon, created_at, updated_at)
SELECT id, category, name, description, price, options, images, is_active, COALESCE(is_addon, false), created_at, updated_at FROM stg_products
ON CONFLICT (id) DO NOTHING;

-- ══════════════════════════════════════════════════════════════
-- STEP 5. lifeart_orders (판매 데이터 — 반드시 완전하게)
-- ══════════════════════════════════════════════════════════════
CREATE TEMP TABLE stg_orders (
  id uuid, user_id uuid, product_id uuid, options jsonb, quantity int, amount bigint,
  status text, shipping_address text, shipping_status text, env text,
  created_at timestamptz, updated_at timestamptz
);
-- \copy stg_orders FROM 'orders_export.csv' WITH (FORMAT csv, HEADER true)

INSERT INTO public.lifeart_orders (id, user_id, product_id, options, quantity, amount, status, shipping_address, shipping_status, env, created_at, updated_at)
SELECT id, user_id, product_id, options, quantity, amount, status, shipping_address, shipping_status, env, created_at, updated_at FROM stg_orders
ON CONFLICT (id) DO NOTHING;

-- ══════════════════════════════════════════════════════════════
-- STEP 6. lifeart_payments (판매 데이터 — 반드시 완전하게)
-- ══════════════════════════════════════════════════════════════
CREATE TEMP TABLE stg_payments (
  id uuid, order_id uuid, pg_provider text, pg_tid text, amount bigint,
  status text, env text, approved_at timestamptz, created_at timestamptz
);
-- \copy stg_payments FROM 'payments_export.csv' WITH (FORMAT csv, HEADER true)

INSERT INTO public.lifeart_payments (id, order_id, pg_provider, pg_tid, amount, status, env, approved_at, created_at)
SELECT id, order_id, pg_provider, pg_tid, amount, status, env, approved_at, created_at FROM stg_payments
ON CONFLICT (id) DO NOTHING;

-- ══════════════════════════════════════════════════════════════
-- STEP 7. lifeart_inquiries
-- ══════════════════════════════════════════════════════════════
CREATE TEMP TABLE stg_inquiries (
  id uuid, type text, env text, user_id uuid, name text, phone text, email text,
  message text, status text, answer text, answered_at timestamptz,
  answered_by uuid, email_sent_at timestamptz, created_at timestamptz
);
-- \copy stg_inquiries FROM 'inquiries_export.csv' WITH (FORMAT csv, HEADER true)

INSERT INTO public.lifeart_inquiries (id, type, env, user_id, name, phone, email, message, status, answer, answered_at, answered_by, email_sent_at, created_at)
SELECT id, type, env, user_id, name, phone, email, message, status, answer, answered_at, answered_by, email_sent_at, created_at FROM stg_inquiries
ON CONFLICT (id) DO NOTHING;

-- ══════════════════════════════════════════════════════════════
-- STEP 8. lifeart_notices
-- ══════════════════════════════════════════════════════════════
CREATE TEMP TABLE stg_notices (
  id uuid, title text, body text, is_published boolean, pinned boolean,
  created_at timestamptz, updated_at timestamptz
);
-- \copy stg_notices FROM 'notices_export.csv' WITH (FORMAT csv, HEADER true)

INSERT INTO public.lifeart_notices (id, title, body, is_published, pinned, created_at, updated_at)
SELECT id, title, body, is_published, pinned, created_at, updated_at FROM stg_notices
ON CONFLICT (id) DO NOTHING;

-- ══════════════════════════════════════════════════════════════
-- STEP 9. lifeart_faqs
-- ══════════════════════════════════════════════════════════════
CREATE TEMP TABLE stg_faqs (
  id uuid, question text, answer text, sort_order int, is_published boolean,
  created_at timestamptz, updated_at timestamptz
);
-- \copy stg_faqs FROM 'faqs_export.csv' WITH (FORMAT csv, HEADER true)

INSERT INTO public.lifeart_faqs (id, question, answer, sort_order, is_published, created_at, updated_at)
SELECT id, question, answer, sort_order, is_published, created_at, updated_at FROM stg_faqs
ON CONFLICT (id) DO NOTHING;

-- ══════════════════════════════════════════════════════════════
-- STEP 10. lifeart_press
-- ══════════════════════════════════════════════════════════════
CREATE TEMP TABLE stg_press (
  id uuid, title text, outlet text, summary text, link_url text, published_on date,
  is_published boolean, pinned boolean, created_at timestamptz, updated_at timestamptz
);
-- \copy stg_press FROM 'press_export.csv' WITH (FORMAT csv, HEADER true)

INSERT INTO public.lifeart_press (id, title, outlet, summary, link_url, published_on, is_published, pinned, created_at, updated_at)
SELECT id, title, outlet, summary, link_url, published_on, is_published, pinned, created_at, updated_at FROM stg_press
ON CONFLICT (id) DO NOTHING;

-- ══════════════════════════════════════════════════════════════
-- STEP 11. lifeart_hero_slides
-- ══════════════════════════════════════════════════════════════
CREATE TEMP TABLE stg_hero (
  id uuid, image_url text, caption text, sort_order int, is_active boolean,
  created_at timestamptz, updated_at timestamptz
);
-- \copy stg_hero FROM 'hero_slides_export.csv' WITH (FORMAT csv, HEADER true)

INSERT INTO public.lifeart_hero_slides (id, image_url, caption, sort_order, is_active, created_at, updated_at)
SELECT id, image_url, caption, sort_order, is_active, created_at, updated_at FROM stg_hero
ON CONFLICT (id) DO NOTHING;

-- ══════════════════════════════════════════════════════════════
-- 최종 검증 — export_lifeart_data.sql 맨 아래 스냅샷과 숫자가 정확히 같아야 함
-- ══════════════════════════════════════════════════════════════
SELECT 'profiles'      AS t, COUNT(*) FROM public.profiles
UNION ALL SELECT 'products',    COUNT(*) FROM public.lifeart_products
UNION ALL SELECT 'orders',      COUNT(*) FROM public.lifeart_orders
UNION ALL SELECT 'payments',    COUNT(*) FROM public.lifeart_payments
UNION ALL SELECT 'inquiries',   COUNT(*) FROM public.lifeart_inquiries
UNION ALL SELECT 'notices',     COUNT(*) FROM public.lifeart_notices
UNION ALL SELECT 'faqs',        COUNT(*) FROM public.lifeart_faqs
UNION ALL SELECT 'press',       COUNT(*) FROM public.lifeart_press
UNION ALL SELECT 'hero_slides', COUNT(*) FROM public.lifeart_hero_slides
UNION ALL SELECT 'auth_users',  COUNT(*) FROM auth.users
UNION ALL SELECT 'identities',  COUNT(*) FROM auth.identities
ORDER BY t;

-- 추가 정합성 체크: orders.amount 합계가 원본과 같은지(판매 데이터 무결성 최종 확인)
SELECT COALESCE(SUM(amount) FILTER (WHERE status IN ('paid','shipping','done')), 0) AS total_sales_krw
FROM public.lifeart_orders;
