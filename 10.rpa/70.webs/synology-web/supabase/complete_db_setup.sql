-- ═══════════════════════════════════════════════════════════════════
-- complete_db_setup.sql
-- WorksFree Hub — 코어 DB 전체 (v3.0)
--
-- 책 참조: 8장. Supabase 데이터베이스 — 회원 정보·결제·크레딧 저장
--
-- 포함 내용:
--   섹션 1 : pgcrypto 확장
--   섹션 2 : 테이블 6개
--             profiles · credits · payments · email_log · email_unsubscribes · page_views
--   섹션 3 : is_admin() 헬퍼 함수 (RLS 정책 전체에서 사용)
--   섹션 4 : RLS 정책 전체
--   섹션 5 : 트리거: on_auth_user_created · on_auth_user_updated
--   섹션 6 : 관리자 함수 6개
--             admin_set_user_role · admin_grant_credits · admin_set_user_name
--             admin_get_all_profiles · admin_get_user_logins · admin_page_view_stats
--   섹션 7 : 일반 함수 3개
--             get_user_credit_balance · deduct_credits · get_email_history
--   섹션 8 : 뷰 2개: credit_balance · page_view_stats
--   섹션 9 : 기존 사용자 소급 동기화 (name/email 백필)
--   섹션 10: 최종 검증 SELECT 쿼리
--
-- 실행 방법: Supabase → SQL Editor → New query → 전체 붙여넣기 → Run
-- 멱등성: 반복 실행 안전 (CREATE ... IF NOT EXISTS, OR REPLACE)
--
-- ⚠ 개발 테스트 계정이 필요한 경우 별도로 seed_dev.sql 실행
-- ═══════════════════════════════════════════════════════════════════


-- ══════════════════════════════════════════════════════════════════════
-- 섹션 1. 확장
-- ══════════════════════════════════════════════════════════════════════
CREATE EXTENSION IF NOT EXISTS pgcrypto;


-- ══════════════════════════════════════════════════════════════════════
-- 섹션 2. 테이블 6개
-- ══════════════════════════════════════════════════════════════════════

-- ── profiles — 사용자 프로필 · 역할 ─────────────────────────────────
CREATE TABLE IF NOT EXISTS public.profiles (
  id               UUID        REFERENCES auth.users ON DELETE CASCADE PRIMARY KEY,
  name             TEXT,
  email            TEXT,
  agreed_at        TIMESTAMPTZ,
  marketing_agreed BOOLEAN     DEFAULT false,
  role             TEXT        DEFAULT 'member',
  created_at       TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE public.profiles
  ADD COLUMN IF NOT EXISTS name             TEXT,
  ADD COLUMN IF NOT EXISTS email            TEXT,
  ADD COLUMN IF NOT EXISTS agreed_at        TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS marketing_agreed BOOLEAN     DEFAULT false,
  ADD COLUMN IF NOT EXISTS role             TEXT        DEFAULT 'member',
  ADD COLUMN IF NOT EXISTS created_at       TIMESTAMPTZ DEFAULT NOW();

ALTER TABLE public.profiles DROP CONSTRAINT IF EXISTS profiles_role_check;
ALTER TABLE public.profiles
  ADD CONSTRAINT profiles_role_check
  CHECK (role IN ('member', 'consultant', 'partner', 'admin'));

ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;


-- ── credits — 크레딧 충전/차감 원장 (env 컬럼으로 환경 격리) ─────────
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


-- ── payments — 결제 내역 (Toss · Stripe) ─────────────────────────────
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


-- ── email_log — 마케팅 이메일 발송 이력 ─────────────────────────────
CREATE TABLE IF NOT EXISTS public.email_log (
  id              BIGINT      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  sent_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  recipient_email TEXT        NOT NULL,
  sender_email    TEXT,
  sender_name     TEXT,
  sender_user_id  UUID        REFERENCES public.profiles(id) ON DELETE SET NULL,
  flyer_src       TEXT,
  flyer_name      TEXT,
  subject         TEXT,
  env             TEXT        NOT NULL DEFAULT 'portal'
                  CHECK (env IN ('dev', 'test', 'staging', 'portal')),
  status          TEXT        NOT NULL DEFAULT 'sent'
                  CHECK (status IN ('sent', 'filtered')),
  extra           JSONB       DEFAULT '{}'::JSONB
);

ALTER TABLE public.email_log ADD COLUMN IF NOT EXISTS status         TEXT  NOT NULL DEFAULT 'sent';
ALTER TABLE public.email_log ADD COLUMN IF NOT EXISTS extra          JSONB          DEFAULT '{}'::JSONB;
ALTER TABLE public.email_log ADD COLUMN IF NOT EXISTS sender_user_id UUID
  REFERENCES public.profiles(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS email_log_sent_at_idx     ON public.email_log (sent_at DESC);
CREATE INDEX IF NOT EXISTS email_log_env_idx         ON public.email_log (env, sent_at DESC);
CREATE INDEX IF NOT EXISTS email_log_recipient_idx   ON public.email_log (recipient_email, sent_at DESC);
CREATE INDEX IF NOT EXISTS email_log_sender_idx      ON public.email_log (sender_email, sent_at DESC);
CREATE INDEX IF NOT EXISTS email_log_flyer_idx       ON public.email_log (flyer_name, sent_at DESC);
CREATE INDEX IF NOT EXISTS email_log_status_idx      ON public.email_log (status, sent_at DESC);
CREATE INDEX IF NOT EXISTS email_log_sender_user_idx ON public.email_log (sender_user_id);

ALTER TABLE public.email_log ENABLE ROW LEVEL SECURITY;


-- ── email_unsubscribes — 수신거부 목록 ───────────────────────────────
CREATE TABLE IF NOT EXISTS public.email_unsubscribes (
  id              BIGINT      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  email           TEXT        UNIQUE NOT NULL,
  source          TEXT        DEFAULT 'link' CHECK (source IN ('link', 'manual')),
  note            TEXT,
  unsubscribed_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS email_unsub_email_idx ON public.email_unsubscribes (email);
CREATE INDEX IF NOT EXISTS email_unsub_at_idx    ON public.email_unsubscribes (unsubscribed_at DESC);

ALTER TABLE public.email_unsubscribes ENABLE ROW LEVEL SECURITY;


-- ── page_views — 페이지 조회 추적 (체류시간 포함) ─────────────────────
CREATE TABLE IF NOT EXISTS public.page_views (
  id         BIGSERIAL   PRIMARY KEY,
  user_id    UUID        REFERENCES public.profiles(id) ON DELETE SET NULL,
  page       TEXT        NOT NULL,
  duration_s INT,
  env        TEXT        DEFAULT 'portal',
  viewed_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS page_views_page_viewed_at ON public.page_views (page, viewed_at DESC);
CREATE INDEX IF NOT EXISTS page_views_user_viewed_at ON public.page_views (user_id, viewed_at DESC);
CREATE INDEX IF NOT EXISTS page_views_viewed_at      ON public.page_views (viewed_at DESC);

ALTER TABLE public.page_views ENABLE ROW LEVEL SECURITY;


-- ══════════════════════════════════════════════════════════════════════
-- 섹션 3. is_admin() — RLS 정책 내 순환 참조 방지용 헬퍼
-- ══════════════════════════════════════════════════════════════════════
CREATE OR REPLACE FUNCTION public.is_admin()
RETURNS BOOLEAN
LANGUAGE SQL STABLE SECURITY DEFINER SET search_path = public AS $$
  SELECT EXISTS (
    SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role = 'admin'
  );
$$;

GRANT EXECUTE ON FUNCTION public.is_admin() TO authenticated, anon;


-- ══════════════════════════════════════════════════════════════════════
-- 섹션 4. RLS 정책 전체
-- ══════════════════════════════════════════════════════════════════════

-- ── profiles ─────────────────────────────────────────────────────────
DO $$ DECLARE r RECORD;
BEGIN
  FOR r IN SELECT policyname FROM pg_policies
           WHERE schemaname = 'public' AND tablename = 'profiles' LOOP
    EXECUTE format('DROP POLICY IF EXISTS %I ON public.profiles', r.policyname);
  END LOOP;
END $$;

CREATE POLICY "profiles_self"
  ON public.profiles FOR ALL
  USING     (auth.uid() = id)
  WITH CHECK (auth.uid() = id);

CREATE POLICY "profiles_admin_select_all"
  ON public.profiles FOR SELECT
  USING (is_admin());


-- ── credits ──────────────────────────────────────────────────────────
DROP POLICY IF EXISTS "credits_select_own"      ON public.credits;
DROP POLICY IF EXISTS "credits_insert_purchase" ON public.credits;

CREATE POLICY "credits_select_own"
  ON public.credits FOR SELECT
  USING (auth.uid() = user_id);

-- 충전(purchase)만 직접 INSERT 허용 — 차감은 deduct_credits() SECURITY DEFINER 경유
CREATE POLICY "credits_insert_purchase"
  ON public.credits FOR INSERT
  WITH CHECK (auth.uid() = user_id AND delta > 0 AND reason = 'purchase');


-- ── payments ─────────────────────────────────────────────────────────
DROP POLICY IF EXISTS "payments_select_own" ON public.payments;
DROP POLICY IF EXISTS "payments_insert_own" ON public.payments;

CREATE POLICY "payments_select_own"
  ON public.payments FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "payments_insert_own"
  ON public.payments FOR INSERT
  WITH CHECK (auth.uid() = user_id);


-- ── email_log ─────────────────────────────────────────────────────────
-- INSERT는 Cloudflare Worker가 service_role 키로 RLS 우회하여 직접 삽입
DROP POLICY IF EXISTS "el_admin_select"        ON public.email_log;
DROP POLICY IF EXISTS "email_log_admin_select" ON public.email_log;

CREATE POLICY "email_log_admin_select"
  ON public.email_log FOR SELECT
  USING (is_admin());


-- ── email_unsubscribes ────────────────────────────────────────────────
DROP POLICY IF EXISTS "eu_admin_all"             ON public.email_unsubscribes;
DROP POLICY IF EXISTS "email_unsubscribes_admin" ON public.email_unsubscribes;

CREATE POLICY "email_unsubscribes_admin"
  ON public.email_unsubscribes FOR ALL
  USING     (is_admin())
  WITH CHECK (is_admin());


-- ── page_views ────────────────────────────────────────────────────────
DROP POLICY IF EXISTS "pv_insert_own"   ON public.page_views;
DROP POLICY IF EXISTS "pv_select_own"   ON public.page_views;
DROP POLICY IF EXISTS "pv_update_own"   ON public.page_views;
DROP POLICY IF EXISTS "pv_admin_select" ON public.page_views;

CREATE POLICY "pv_insert_own"   ON public.page_views
  FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "pv_select_own"   ON public.page_views
  FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "pv_update_own"   ON public.page_views
  FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "pv_admin_select" ON public.page_views
  FOR SELECT USING (is_admin());


-- ══════════════════════════════════════════════════════════════════════
-- 섹션 5. 트리거
-- ══════════════════════════════════════════════════════════════════════

-- ── handle_new_user — 신규 가입 시 profiles 행 자동 생성 ─────────────
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
BEGIN
  INSERT INTO public.profiles (id, email, name)
  VALUES (
    NEW.id,
    NEW.email,
    COALESCE(NEW.raw_user_meta_data->>'full_name', NEW.raw_user_meta_data->>'name')
  )
  ON CONFLICT (id) DO UPDATE SET
    email = EXCLUDED.email,
    name  = COALESCE(EXCLUDED.name, public.profiles.name);
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();


-- ── sync_profile_name — auth 업데이트 시 profiles 자동 동기화 ─────────
CREATE OR REPLACE FUNCTION public.sync_profile_name()
RETURNS TRIGGER LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE
  _new_name  TEXT;
  _new_email TEXT;
BEGIN
  _new_name  := COALESCE(
                  NEW.raw_user_meta_data->>'full_name',
                  NEW.raw_user_meta_data->>'name'
                );
  _new_email := NEW.email;
  UPDATE public.profiles
  SET
    name  = COALESCE(_new_name,  name),
    email = COALESCE(_new_email, email)
  WHERE id = NEW.id;
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS on_auth_user_updated ON auth.users;
CREATE TRIGGER on_auth_user_updated
  AFTER UPDATE OF raw_user_meta_data, email ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.sync_profile_name();


-- ══════════════════════════════════════════════════════════════════════
-- 섹션 6. 관리자 함수 6개
-- ══════════════════════════════════════════════════════════════════════

-- ── admin_set_user_role ───────────────────────────────────────────────
DROP FUNCTION IF EXISTS public.admin_set_user_role(UUID, TEXT);
CREATE OR REPLACE FUNCTION public.admin_set_user_role(target_id UUID, new_role TEXT)
RETURNS TEXT
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE _caller_role TEXT;
BEGIN
  SELECT role INTO _caller_role FROM public.profiles WHERE id = auth.uid();
  IF _caller_role IS DISTINCT FROM 'admin' THEN RETURN 'error: not_admin'; END IF;
  IF new_role NOT IN ('member', 'consultant', 'partner') THEN
    RETURN 'error: invalid_role';
  END IF;
  -- profiles.role 업데이트
  UPDATE public.profiles SET role = new_role WHERE id = target_id;
  -- auth.users.raw_app_meta_data.wf_role 동기화 (Supabase 대시보드 App Metadata에서 확인 가능)
  UPDATE auth.users
  SET raw_app_meta_data = jsonb_set(
    COALESCE(raw_app_meta_data, '{}'),
    '{wf_role}',
    to_jsonb(new_role)
  )
  WHERE id = target_id;
  RETURN 'ok';
END;
$$;
REVOKE ALL    ON FUNCTION public.admin_set_user_role(UUID, TEXT) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.admin_set_user_role(UUID, TEXT) TO anon, authenticated;


-- ── admin_set_user_name ────────────────────────────────────────────────
DROP FUNCTION IF EXISTS public.admin_set_user_name(UUID, TEXT);
CREATE OR REPLACE FUNCTION public.admin_set_user_name(target_id UUID, new_name TEXT)
RETURNS TEXT
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE _caller_role TEXT;
BEGIN
  SELECT role INTO _caller_role FROM public.profiles WHERE id = auth.uid();
  IF _caller_role IS DISTINCT FROM 'admin' THEN RETURN 'error: not_admin'; END IF;
  IF new_name IS NULL OR trim(new_name) = '' THEN RETURN 'error: empty_name'; END IF;
  -- profiles.name 업데이트
  UPDATE public.profiles SET name = trim(new_name) WHERE id = target_id;
  -- auth.users.raw_user_meta_data.full_name 동기화 (Supabase 대시보드와 일치)
  UPDATE auth.users
  SET raw_user_meta_data = jsonb_set(
    COALESCE(raw_user_meta_data, '{}'),
    '{full_name}',
    to_jsonb(trim(new_name))
  )
  WHERE id = target_id;
  RETURN 'ok';
END;
$$;
REVOKE ALL    ON FUNCTION public.admin_set_user_name(UUID, TEXT) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.admin_set_user_name(UUID, TEXT) TO anon, authenticated;


-- ── admin_get_all_profiles ─────────────────────────────────────────────
-- RETURNS TABLE 컬럼명(role, id)과 내부 SELECT 컬럼명 충돌 방지 → alias p2 사용
CREATE OR REPLACE FUNCTION public.admin_get_all_profiles()
RETURNS TABLE (
  id        UUID,
  email     TEXT,
  name      TEXT,
  role      TEXT,
  agreed_at TIMESTAMPTZ
)
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE _r TEXT;
BEGIN
  SELECT p2.role INTO _r FROM public.profiles p2 WHERE p2.id = auth.uid();
  IF _r IS DISTINCT FROM 'admin' THEN RETURN; END IF;
  RETURN QUERY
    SELECT p.id, p.email, p.name, p.role, p.agreed_at
    FROM   public.profiles p
    ORDER  BY p.agreed_at DESC NULLS LAST;
END;
$$;
REVOKE ALL    ON FUNCTION public.admin_get_all_profiles() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.admin_get_all_profiles() TO anon, authenticated;


-- ── admin_get_user_logins ──────────────────────────────────────────────
-- RETURNS TABLE 컬럼명(id)과 WHERE id 충돌 방지 → alias p2 사용
CREATE OR REPLACE FUNCTION public.admin_get_user_logins()
RETURNS TABLE (
  id              UUID,
  last_sign_in_at TIMESTAMPTZ
)
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE _r TEXT;
BEGIN
  SELECT p2.role INTO _r FROM public.profiles p2 WHERE p2.id = auth.uid();
  IF _r IS DISTINCT FROM 'admin' THEN RETURN; END IF;
  RETURN QUERY
    SELECT au.id::UUID, au.last_sign_in_at
    FROM   auth.users au;
END;
$$;
REVOKE ALL    ON FUNCTION public.admin_get_user_logins() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.admin_get_user_logins() TO anon, authenticated;


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


-- ── admin_page_view_stats — 관리자 페이지뷰 통계 ─────────────────────
DROP FUNCTION IF EXISTS public.admin_page_view_stats(INT);
CREATE OR REPLACE FUNCTION public.admin_page_view_stats(
  days        INT    DEFAULT 30,
  env_filter  TEXT[] DEFAULT NULL
)
RETURNS TABLE (
  page         TEXT,
  views        BIGINT,
  unique_users BIGINT,
  avg_sec      NUMERIC,
  pct_with_dur NUMERIC
)
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE
  _r    TEXT;
  _envs TEXT[];
BEGIN
  SELECT role INTO _r FROM public.profiles WHERE id = auth.uid();
  IF _r IS DISTINCT FROM 'admin' THEN RETURN; END IF;
  _envs := COALESCE(env_filter, ARRAY['staging', 'portal']::TEXT[]);
  RETURN QUERY
    SELECT
      pv.page,
      COUNT(*)::BIGINT,
      COUNT(DISTINCT pv.user_id)::BIGINT,
      ROUND(AVG(pv.duration_s), 1),
      ROUND(100.0 * COUNT(pv.duration_s) / NULLIF(COUNT(*), 0), 1)
    FROM public.page_views pv
    WHERE pv.viewed_at > NOW() - (days || ' days')::INTERVAL
      AND pv.env = ANY(_envs)
    GROUP BY pv.page
    ORDER BY COUNT(*) DESC;
END;
$$;
REVOKE ALL    ON FUNCTION public.admin_page_view_stats(INT, TEXT[]) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.admin_page_view_stats(INT, TEXT[]) TO anon, authenticated;


-- ══════════════════════════════════════════════════════════════════════
-- 섹션 7. 일반 함수 3개
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


-- ── get_email_history — 수신자별 발송 이력 조회 ───────────────────────
CREATE OR REPLACE FUNCTION public.get_email_history(
  p_email TEXT,
  p_limit INT DEFAULT 10
)
RETURNS TABLE (
  sent_at     TIMESTAMPTZ,
  flyer_name  TEXT,
  sender_name TEXT,
  subject     TEXT,
  env         TEXT
)
LANGUAGE SQL STABLE SECURITY DEFINER SET search_path = public AS $$
  SELECT sent_at, flyer_name, sender_name, subject, env
  FROM   public.email_log
  WHERE  recipient_email = lower(p_email)
  ORDER  BY sent_at DESC
  LIMIT  p_limit;
$$;


-- ══════════════════════════════════════════════════════════════════════
-- 섹션 8. 뷰 2개
-- ══════════════════════════════════════════════════════════════════════

-- ── credit_balance — 사용자별 크레딧 잔액 요약 ────────────────────────
CREATE OR REPLACE VIEW public.credit_balance
  WITH (security_invoker = true) AS
SELECT
  user_id,
  COALESCE(SUM(delta), 0)::INT                             AS balance,
  COALESCE(SUM(delta)  FILTER (WHERE delta > 0), 0)::INT   AS total_charged,
  COALESCE(SUM(-delta) FILTER (WHERE delta < 0), 0)::INT   AS total_used
FROM public.credits
GROUP BY user_id;


-- ── page_view_stats — 페이지별 통계 요약 ─────────────────────────────
CREATE OR REPLACE VIEW public.page_view_stats AS
SELECT
  page,
  COUNT(*)                                                          AS total_views,
  COUNT(DISTINCT user_id)                                           AS unique_users,
  ROUND(AVG(duration_s))                                            AS avg_duration_s,
  COUNT(*) FILTER (WHERE viewed_at > NOW() - INTERVAL '7 days')    AS views_7d,
  COUNT(*) FILTER (WHERE viewed_at > NOW() - INTERVAL '30 days')   AS views_30d,
  MAX(viewed_at)                                                    AS last_viewed
FROM public.page_views
GROUP BY page
ORDER BY total_views DESC;


-- ══════════════════════════════════════════════════════════════════════
-- 섹션 9. 기존 사용자 소급 동기화 (트리거 없던 시절 가입자 보완)
-- ══════════════════════════════════════════════════════════════════════
INSERT INTO public.profiles (id)
SELECT id FROM auth.users
ON CONFLICT (id) DO NOTHING;

UPDATE public.profiles p
SET
  name  = COALESCE(u.raw_user_meta_data->>'full_name',
                   u.raw_user_meta_data->>'name', p.name),
  email = COALESCE(u.email, p.email)
FROM auth.users u
WHERE p.id = u.id
  AND (p.name IS NULL OR p.email IS NULL);


-- ══════════════════════════════════════════════════════════════════════
-- 섹션 10. 최종 검증 (실행 후 Results 패널에서 확인)
-- ══════════════════════════════════════════════════════════════════════

-- === 1. 테이블 목록 === → 6개 테이블 모두 표시
SELECT '=== 1. 테이블 목록 ===' AS section, table_name
FROM   information_schema.tables
WHERE  table_schema = 'public'
  AND  table_name IN ('profiles','credits','payments','email_log','email_unsubscribes','page_views')
ORDER  BY table_name;

-- === 2. email_log 컬럼 === → sender_user_id 포함 전체 컬럼 목록
SELECT '=== 2. email_log 컬럼 ===' AS section, column_name, data_type
FROM   information_schema.columns
WHERE  table_schema = 'public' AND table_name = 'email_log'
ORDER  BY ordinal_position;

-- === 3. RLS 정책 === → 각 테이블의 정책 목록 확인
SELECT '=== 3. RLS 정책 ===' AS section, tablename, policyname, cmd
FROM   pg_policies
WHERE  tablename IN ('profiles','credits','payments','email_log','email_unsubscribes','page_views')
ORDER  BY tablename, policyname;

-- === 4. 함수 목록 === → 12개 함수 모두 표시
SELECT '=== 4. 함수 목록 ===' AS section, routine_name, routine_type
FROM   information_schema.routines
WHERE  routine_schema = 'public'
  AND  routine_name IN (
         'is_admin','handle_new_user','sync_profile_name',
         'admin_set_user_role','admin_set_user_name','admin_get_all_profiles',
         'admin_get_user_logins','admin_grant_credits','admin_page_view_stats',
         'get_user_credit_balance','deduct_credits','get_email_history'
       )
ORDER  BY routine_name;

-- === 5. 트리거 === → on_auth_user_created, on_auth_user_updated 2개
SELECT '=== 5. 트리거 ===' AS section, trigger_name, event_object_table
FROM   information_schema.triggers
WHERE  trigger_name IN ('on_auth_user_created','on_auth_user_updated')
ORDER  BY trigger_name;

-- === 7. 뷰 목록 === → credit_balance, page_view_stats 2개
SELECT '=== 7. 뷰 목록 ===' AS section, table_name AS view_name
FROM   information_schema.views
WHERE  table_schema = 'public'
  AND  table_name IN ('credit_balance','page_view_stats')
ORDER  BY table_name;
