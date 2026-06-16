-- ═══════════════════════════════════════════════════════════════════
-- WorksFree Hub — Phase 1 DB Setup
-- 실행 전: phase1_check_before_run.sql 먼저 실행하여 현재 상태 확인
-- 멱등성 보장: 여러 번 실행해도 동일한 결과
-- ═══════════════════════════════════════════════════════════════════


-- ────────────────────────────────────────────────────────────────
-- 0. profiles 테이블 보완
--    이미 존재할 가능성이 높으므로 CREATE TABLE IF NOT EXISTS 사용
--    누락 컬럼은 ALTER TABLE ADD COLUMN IF NOT EXISTS 로 추가
-- ────────────────────────────────────────────────────────────────

-- 기존 테이블이 없을 때만 생성 (이미 있으면 무시)
-- role 기본값은 기존 데이터와 동일하게 'general' 사용
CREATE TABLE IF NOT EXISTS profiles (
  id               uuid REFERENCES auth.users PRIMARY KEY,
  agreed_at        timestamptz,
  marketing_agreed boolean     DEFAULT false,
  role             text        DEFAULT 'general',   -- 기존 DB 기본값 유지
  created_at       timestamptz DEFAULT now()
);

-- 기존 테이블에 컬럼이 없으면 추가 (이미 있으면 무시)
-- role_set_at 등 기존에 있는 미지 컬럼은 건드리지 않음
ALTER TABLE profiles
  ADD COLUMN IF NOT EXISTS role             text        DEFAULT 'general',
  ADD COLUMN IF NOT EXISTS marketing_agreed boolean     DEFAULT false,
  ADD COLUMN IF NOT EXISTS agreed_at        timestamptz,
  ADD COLUMN IF NOT EXISTS created_at       timestamptz DEFAULT now();

ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;

-- ── 기존 정책명이 무엇이든 전부 정리 후 통일된 이름으로 재생성 ──
-- (이전 스크립트에서 "본인만 조회·수정" 등 다른 이름으로 만들었을 수 있음)
DO $$ DECLARE r record;
BEGIN
  FOR r IN SELECT policyname FROM pg_policies WHERE tablename = 'profiles' LOOP
    EXECUTE format('DROP POLICY IF EXISTS %I ON profiles', r.policyname);
  END LOOP;
END $$;

CREATE POLICY "profiles_self"
  ON profiles FOR ALL
  USING      (auth.uid() = id)
  WITH CHECK (auth.uid() = id);


-- ── 신규 가입 시 profiles 행 자동 생성 트리거 ────────────────────
CREATE OR REPLACE FUNCTION handle_new_user()
RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
BEGIN
  INSERT INTO public.profiles (id)
  VALUES (NEW.id)
  ON CONFLICT (id) DO NOTHING;
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION handle_new_user();

-- ── 기존 가입자 중 profiles 행이 없는 사용자 소급 처리 ──────────
-- (이미 가입된 사용자가 있지만 트리거가 없던 시절에 가입한 경우)
INSERT INTO public.profiles (id)
SELECT id FROM auth.users
ON CONFLICT (id) DO NOTHING;


-- ────────────────────────────────────────────────────────────────
-- 1. credits 테이블
-- ────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS credits (
  id           bigint       GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  user_id      uuid         NOT NULL REFERENCES auth.users ON DELETE CASCADE,
  delta        integer      NOT NULL,
  reason       text         NOT NULL
               CHECK (reason IN ('purchase', 'use_app', 'admin_grant', 'refund')),
  app_id       text,
  ref_order_id text,
  note         text,
  created_at   timestamptz  NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS credits_user_created
  ON credits (user_id, created_at DESC);

ALTER TABLE credits ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "credits_select_own"      ON credits;
DROP POLICY IF EXISTS "credits_insert_purchase" ON credits;

CREATE POLICY "credits_select_own"
  ON credits FOR SELECT
  USING (auth.uid() = user_id);

-- 프론트엔드: 충전(purchase, delta>0)만 직접 INSERT 허용
-- 차감(use_app)은 서버 측 deduct_credits() 함수(service_role)에서만
CREATE POLICY "credits_insert_purchase"
  ON credits FOR INSERT
  WITH CHECK (
    auth.uid() = user_id
    AND delta  > 0
    AND reason = 'purchase'
  );


-- ────────────────────────────────────────────────────────────────
-- 2. payments 테이블
-- ────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS payments (
  id           bigint        GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  user_id      uuid          NOT NULL REFERENCES auth.users ON DELETE CASCADE,
  order_id     text          NOT NULL UNIQUE,
  pg           text          NOT NULL CHECK (pg IN ('toss', 'stripe')),
  amount_krw   integer       NOT NULL DEFAULT 0,
  amount_usd   numeric(10,2) NOT NULL DEFAULT 0,
  credits      integer       NOT NULL,
  status       text          NOT NULL DEFAULT 'paid'
               CHECK (status IN ('paid', 'cancelled', 'refunded')),
  created_at   timestamptz   NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS payments_user_created
  ON payments (user_id, created_at DESC);

ALTER TABLE payments ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "payments_select_own" ON payments;
DROP POLICY IF EXISTS "payments_insert_own" ON payments;

CREATE POLICY "payments_select_own"
  ON payments FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "payments_insert_own"
  ON payments FOR INSERT
  WITH CHECK (auth.uid() = user_id);


-- ────────────────────────────────────────────────────────────────
-- 3. credit_balance 뷰
-- ────────────────────────────────────────────────────────────────

CREATE OR REPLACE VIEW credit_balance
  WITH (security_invoker = true) AS
SELECT
  user_id,
  COALESCE(SUM(delta), 0)::int                           AS balance,
  COALESCE(SUM(delta)  FILTER (WHERE delta > 0), 0)::int AS total_charged,
  COALESCE(SUM(-delta) FILTER (WHERE delta < 0), 0)::int AS total_used
FROM credits
GROUP BY user_id;


-- ────────────────────────────────────────────────────────────────
-- 4. 서버 측 헬퍼 함수 (SECURITY DEFINER)
-- ────────────────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION get_user_credit_balance(p_user_id uuid)
RETURNS integer
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public AS $$
  SELECT COALESCE(SUM(delta), 0)::int FROM credits WHERE user_id = p_user_id;
$$;

CREATE OR REPLACE FUNCTION deduct_credits(
  p_user_id uuid,
  p_amount  integer,
  p_app_id  text,
  p_note    text DEFAULT NULL
)
RETURNS integer
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE v_balance integer;
BEGIN
  SELECT get_user_credit_balance(p_user_id) INTO v_balance;
  IF v_balance < p_amount THEN
    RAISE EXCEPTION 'insufficient_credits: balance=%, required=%', v_balance, p_amount;
  END IF;
  INSERT INTO credits (user_id, delta, reason, app_id, note)
  VALUES (p_user_id, -p_amount, 'use_app', p_app_id, p_note);
  RETURN v_balance - p_amount;
END;
$$;

CREATE OR REPLACE FUNCTION admin_grant_credits(
  p_user_id uuid,
  p_amount  integer,
  p_note    text DEFAULT '관리자 지급'
)
RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
BEGIN
  INSERT INTO credits (user_id, delta, reason, note)
  VALUES (p_user_id, p_amount, 'admin_grant', p_note);
END;
$$;


-- ────────────────────────────────────────────────────────────────
-- 5. 테스트 데이터 시딩
--    아래 주석을 해제하고 UUID 교체 후 실행
-- ────────────────────────────────────────────────────────────────

-- 기존 role 값: general(기본) | gfc | ceo | staff | consultant
-- 'admin'은 코드에 없으므로 사용 금지
/*
UPDATE profiles SET role = 'gfc'     WHERE id = '<GFC_ADMIN_USER_UUID>';
UPDATE profiles SET role = 'general' WHERE id = '<PAID_USER_UUID>';

SELECT admin_grant_credits('<GFC_ADMIN_USER_UUID>', 9999, '관리자 계정 초기 지급');
SELECT admin_grant_credits('<PAID_USER_UUID>',      500,  '유료 테스트 계정 초기 지급');
*/


-- ────────────────────────────────────────────────────────────────
-- 6. 최종 검증 (실행 결과 확인용)
-- ────────────────────────────────────────────────────────────────

SELECT '=== 테이블 및 뷰 ===' AS section;
SELECT table_name, table_type
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name IN ('profiles', 'credits', 'payments', 'credit_balance')
ORDER BY table_name;

SELECT '=== RLS 정책 ===' AS section;
SELECT tablename, policyname, cmd
FROM pg_policies
WHERE tablename IN ('profiles', 'credits', 'payments')
ORDER BY tablename, policyname;

SELECT '=== 트리거 ===' AS section;
SELECT trigger_name, event_object_table
FROM information_schema.triggers
WHERE trigger_name = 'on_auth_user_created';

SELECT '=== 함수 ===' AS section;
SELECT routine_name
FROM information_schema.routines
WHERE routine_schema = 'public'
  AND routine_name IN ('handle_new_user','get_user_credit_balance','deduct_credits','admin_grant_credits')
ORDER BY routine_name;

SELECT '=== profiles 컬럼 ===' AS section;
SELECT column_name, data_type, column_default, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'profiles'
ORDER BY ordinal_position;
