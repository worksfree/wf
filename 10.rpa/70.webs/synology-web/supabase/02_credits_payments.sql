-- ═══════════════════════════════════════════════════════════════════
-- 02_credits_payments.sql
-- WorksFree Hub — [Stage 2] 크레딧 · 결제 시스템
--
-- 책 참조: 8장(크레딧 설계), 9장(결제 연동 — Toss·Stripe)
-- 사전 조건: 01_auth_profiles.sql 실행 완료
--
-- 포함 내용:
--   - public.credits         (크레딧 충전/차감 원장)
--   - public.payments        (결제 내역)
--   - credits · payments RLS 정책
--   - credit_balance 뷰      (사용자별 잔액 요약)
--   - get_user_credit_balance (잔액 조회 함수)
--   - deduct_credits          (크레딧 차감 — 서버 측 전용)
--   - admin_grant_credits     (관리자 크레딧 수동 지급)
--
-- 환경 격리: credits · payments 모두 env 컬럼으로 dev/test/staging/portal 분리
-- 멱등성: 반복 실행 안전
-- ═══════════════════════════════════════════════════════════════════


-- ══════════════════════════════════════════════════════════════════════
-- 1. credits — 크레딧 충전/차감 원장 (env 컬럼으로 환경 격리)
-- ══════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS public.credits (
  id           BIGINT      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  user_id      UUID        NOT NULL REFERENCES auth.users ON DELETE CASCADE,
  delta        INTEGER     NOT NULL,
  reason       TEXT        NOT NULL
               CHECK (reason IN ('purchase', 'use_app', 'admin_grant', 'refund')),
  app_id       TEXT,
  ref_order_id TEXT,
  note         TEXT,
  env          TEXT        NOT NULL DEFAULT 'portal',
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE public.credits ADD COLUMN IF NOT EXISTS env TEXT NOT NULL DEFAULT 'portal';

CREATE INDEX IF NOT EXISTS credits_user_created ON public.credits (user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS credits_env_idx      ON public.credits (env, created_at DESC);

ALTER TABLE public.credits ENABLE ROW LEVEL SECURITY;


-- ══════════════════════════════════════════════════════════════════════
-- 2. payments — 결제 내역 (Toss · Stripe)
-- ══════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS public.payments (
  id           BIGINT        GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  user_id      UUID          NOT NULL REFERENCES auth.users ON DELETE CASCADE,
  order_id     TEXT          NOT NULL UNIQUE,
  pg           TEXT          NOT NULL CHECK (pg IN ('toss', 'stripe')),
  amount_krw   INTEGER       NOT NULL DEFAULT 0,
  amount_usd   NUMERIC(10,2) NOT NULL DEFAULT 0,
  credits      INTEGER       NOT NULL,
  status       TEXT          NOT NULL DEFAULT 'paid'
               CHECK (status IN ('paid', 'cancelled', 'refunded')),
  env          TEXT          NOT NULL DEFAULT 'portal',
  created_at   TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

ALTER TABLE public.payments ADD COLUMN IF NOT EXISTS env TEXT NOT NULL DEFAULT 'portal';

CREATE INDEX IF NOT EXISTS payments_user_created ON public.payments (user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS payments_env_idx      ON public.payments (env, created_at DESC);

ALTER TABLE public.payments ENABLE ROW LEVEL SECURITY;


-- ══════════════════════════════════════════════════════════════════════
-- 3. RLS 정책
-- ══════════════════════════════════════════════════════════════════════

-- credits
DROP POLICY IF EXISTS "credits_select_own"      ON public.credits;
DROP POLICY IF EXISTS "credits_insert_purchase" ON public.credits;

CREATE POLICY "credits_select_own"
  ON public.credits FOR SELECT
  USING (auth.uid() = user_id);

-- 충전(purchase)만 직접 INSERT 허용 — 차감은 deduct_credits() SECURITY DEFINER 경유
CREATE POLICY "credits_insert_purchase"
  ON public.credits FOR INSERT
  WITH CHECK (auth.uid() = user_id AND delta > 0 AND reason = 'purchase');

-- payments
DROP POLICY IF EXISTS "payments_select_own" ON public.payments;
DROP POLICY IF EXISTS "payments_insert_own" ON public.payments;

CREATE POLICY "payments_select_own"
  ON public.payments FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "payments_insert_own"
  ON public.payments FOR INSERT
  WITH CHECK (auth.uid() = user_id);


-- ══════════════════════════════════════════════════════════════════════
-- 4. credit_balance 뷰 — 사용자별 크레딧 잔액 요약
-- ══════════════════════════════════════════════════════════════════════
CREATE OR REPLACE VIEW public.credit_balance
  WITH (security_invoker = true) AS
SELECT
  user_id,
  COALESCE(SUM(delta), 0)::INT                             AS balance,
  COALESCE(SUM(delta)  FILTER (WHERE delta > 0), 0)::INT   AS total_charged,
  COALESCE(SUM(-delta) FILTER (WHERE delta < 0), 0)::INT   AS total_used
FROM public.credits
GROUP BY user_id;


-- ══════════════════════════════════════════════════════════════════════
-- 5. 함수
-- ══════════════════════════════════════════════════════════════════════

-- ── get_user_credit_balance — 크레딧 잔액 조회 ────────────────────────
CREATE OR REPLACE FUNCTION public.get_user_credit_balance(p_user_id UUID)
RETURNS INTEGER
LANGUAGE SQL STABLE SECURITY DEFINER SET search_path = public AS $$
  SELECT COALESCE(SUM(delta), 0)::INT FROM public.credits WHERE user_id = p_user_id;
$$;


-- ── deduct_credits — 앱 사용 크레딧 차감 (서버 측 전용) ───────────────
CREATE OR REPLACE FUNCTION public.deduct_credits(
  p_user_id UUID,
  p_amount  INTEGER,
  p_app_id  TEXT,
  p_note    TEXT DEFAULT NULL
)
RETURNS INTEGER
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE v_balance INTEGER;
BEGIN
  SELECT get_user_credit_balance(p_user_id) INTO v_balance;
  IF v_balance < p_amount THEN
    RAISE EXCEPTION 'insufficient_credits: balance=%, required=%', v_balance, p_amount;
  END IF;
  INSERT INTO public.credits (user_id, delta, reason, app_id, note)
  VALUES (p_user_id, -p_amount, 'use_app', p_app_id, p_note);
  RETURN v_balance - p_amount;
END;
$$;


-- ── admin_grant_credits — 관리자 크레딧 수동 지급 ─────────────────────
DROP FUNCTION IF EXISTS public.admin_grant_credits(UUID, INT, TEXT);
DROP FUNCTION IF EXISTS public.admin_grant_credits(UUID, INTEGER, TEXT);
CREATE OR REPLACE FUNCTION public.admin_grant_credits(
  target_id UUID,
  amount    INT,
  env_name  TEXT DEFAULT 'portal'
)
RETURNS TEXT
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE _caller_role TEXT;
BEGIN
  SELECT role INTO _caller_role FROM public.profiles WHERE id = auth.uid();
  IF _caller_role IS DISTINCT FROM 'admin' THEN RETURN 'error: not_admin'; END IF;
  IF amount < 1 THEN RETURN 'error: invalid_amount'; END IF;
  INSERT INTO public.credits (user_id, delta, reason, note, env, created_at)
  VALUES (target_id, amount, 'admin_grant', '관리자 수동 지급', env_name, NOW());
  RETURN 'ok';
END;
$$;
REVOKE ALL    ON FUNCTION public.admin_grant_credits(UUID, INT, TEXT) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.admin_grant_credits(UUID, INT, TEXT) TO anon, authenticated;


-- ══════════════════════════════════════════════════════════════════════
-- 검증
-- ══════════════════════════════════════════════════════════════════════
SELECT table_name
FROM   information_schema.tables
WHERE  table_schema = 'public'
  AND  table_name IN ('credits', 'payments')
ORDER  BY table_name;

SELECT table_name AS view_name
FROM   information_schema.views
WHERE  table_schema = 'public'
  AND  table_name   = 'credit_balance';
