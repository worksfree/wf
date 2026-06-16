-- ═══════════════════════════════════════════════════════════════════
-- complete_db_setup.sql
-- WorksFree Hub — Supabase 완전 DB 구축 스크립트  v3.0  (2026-05-30)
--
-- ✅ 멱등성: 기존 DB에 여러 번 실행해도 안전
-- ✅ 신규 DB: 처음부터 완전한 스키마 생성
-- ✅ 기존 DB: 누락 컬럼·정책·함수 자동 보완
--
-- 실행 방법 ─────────────────────────────────────────────────────────
--   Supabase Dashboard → SQL Editor → New query
--   → 이 파일 전체 붙여넣기 → Run (Ctrl+Enter)
--   → 하단 최종 검증 쿼리 결과 확인
--
-- 포함 내용 ─────────────────────────────────────────────────────────
--   섹션 1  확장
--   섹션 2  테이블: profiles · credits · payments
--                   email_log · email_unsubscribes · page_views
--   섹션 3  헬퍼 함수: is_admin (RLS 정책이 참조)
--   섹션 4  RLS 정책 (전부 정리 후 재생성)
--   섹션 5  트리거 함수: handle_new_user · sync_profile_name
--   섹션 6  관리자 전용 함수 (SECURITY DEFINER)
--             admin_set_user_role · admin_grant_credits
--             admin_set_user_name · admin_get_all_profiles
--             admin_get_user_logins · admin_page_view_stats
--   섹션 7  일반 함수: get_user_credit_balance · deduct_credits
--                       get_email_history
--   섹션 8  뷰: credit_balance · page_view_stats
--   섹션 9  기존 사용자 소급 동기화
--   섹션 10 개발 테스트 사용자 4명
--   섹션 11 최종 검증 쿼리
-- ═══════════════════════════════════════════════════════════════════


-- ══════════════════════════════════════════════════════════════════════
-- 1. 확장
-- ══════════════════════════════════════════════════════════════════════

CREATE EXTENSION IF NOT EXISTS pgcrypto;


-- ══════════════════════════════════════════════════════════════════════
-- 2. 테이블 생성 / 컬럼 보완
--    CREATE TABLE IF NOT EXISTS → 신규 DB: 테이블 생성
--    ALTER TABLE ADD COLUMN IF NOT EXISTS → 기존 DB: 누락 컬럼 추가
-- ══════════════════════════════════════════════════════════════════════

-- ── 2-1. profiles ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.profiles (
  id               UUID        REFERENCES auth.users ON DELETE CASCADE PRIMARY KEY,
  agreed_at        TIMESTAMPTZ,
  marketing_agreed BOOLEAN     DEFAULT false,
  role             TEXT        DEFAULT 'general',
  created_at       TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE public.profiles
  ADD COLUMN IF NOT EXISTS name             TEXT,
  ADD COLUMN IF NOT EXISTS email            TEXT,
  ADD COLUMN IF NOT EXISTS agreed_at        TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS marketing_agreed BOOLEAN     DEFAULT false,
  ADD COLUMN IF NOT EXISTS role             TEXT        DEFAULT 'general',
  ADD COLUMN IF NOT EXISTS created_at       TIMESTAMPTZ DEFAULT NOW();

-- role CHECK 제약 재설정
ALTER TABLE public.profiles DROP CONSTRAINT IF EXISTS profiles_role_check;
ALTER TABLE public.profiles
  ADD CONSTRAINT profiles_role_check
  CHECK (role IN ('general', 'consultant', 'gfc', 'ceo', 'staff', 'admin'));

ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;


-- ── 2-2. credits ──────────────────────────────────────────────────────
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


-- ── 2-3. payments ─────────────────────────────────────────────────────
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


-- ── 2-4. email_log ────────────────────────────────────────────────────
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

-- 기존 테이블에 누락 컬럼 추가
ALTER TABLE public.email_log ADD COLUMN IF NOT EXISTS status         TEXT  NOT NULL DEFAULT 'sent';
ALTER TABLE public.email_log ADD COLUMN IF NOT EXISTS extra          JSONB          DEFAULT '{}'::JSONB;
ALTER TABLE public.email_log ADD COLUMN IF NOT EXISTS sender_user_id UUID
  REFERENCES public.profiles(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS email_log_sent_at_idx      ON public.email_log (sent_at DESC);
CREATE INDEX IF NOT EXISTS email_log_env_idx          ON public.email_log (env, sent_at DESC);
CREATE INDEX IF NOT EXISTS email_log_recipient_idx    ON public.email_log (recipient_email, sent_at DESC);
CREATE INDEX IF NOT EXISTS email_log_sender_idx       ON public.email_log (sender_email, sent_at DESC);
CREATE INDEX IF NOT EXISTS email_log_flyer_idx        ON public.email_log (flyer_name, sent_at DESC);
CREATE INDEX IF NOT EXISTS email_log_status_idx       ON public.email_log (status, sent_at DESC);
CREATE INDEX IF NOT EXISTS email_log_sender_user_idx  ON public.email_log (sender_user_id);

ALTER TABLE public.email_log ENABLE ROW LEVEL SECURITY;


-- ── 2-5. email_unsubscribes ───────────────────────────────────────────
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


-- ── 2-6. page_views ───────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.page_views (
  id         BIGSERIAL   PRIMARY KEY,
  user_id    UUID        REFERENCES public.profiles (id) ON DELETE SET NULL,
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
-- 3. 헬퍼 함수 (RLS 정책이 참조하므로 정책보다 먼저 생성)
-- ══════════════════════════════════════════════════════════════════════

-- is_admin(): profiles 순환 참조 방지 (SECURITY DEFINER)
CREATE OR REPLACE FUNCTION public.is_admin()
RETURNS BOOLEAN
LANGUAGE SQL STABLE SECURITY DEFINER SET search_path = public AS $$
  SELECT EXISTS (
    SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role = 'admin'
  );
$$;

GRANT EXECUTE ON FUNCTION public.is_admin() TO authenticated, anon;


-- ══════════════════════════════════════════════════════════════════════
-- 4. RLS 정책 (기존 정책 전부 정리 후 재생성)
-- ══════════════════════════════════════════════════════════════════════

-- ── 4-1. profiles ─────────────────────────────────────────────────────
DO $$ DECLARE r RECORD;
BEGIN
  FOR r IN SELECT policyname FROM pg_policies
           WHERE schemaname = 'public' AND tablename = 'profiles' LOOP
    EXECUTE format('DROP POLICY IF EXISTS %I ON public.profiles', r.policyname);
  END LOOP;
END $$;

-- 본인 행: 모든 작업 허용
CREATE POLICY "profiles_self"
  ON public.profiles FOR ALL
  USING (auth.uid() = id)
  WITH CHECK (auth.uid() = id);

-- 관리자: 전체 SELECT
CREATE POLICY "profiles_admin_select_all"
  ON public.profiles FOR SELECT
  USING (is_admin());


-- ── 4-2. credits ──────────────────────────────────────────────────────
DROP POLICY IF EXISTS "credits_select_own"      ON public.credits;
DROP POLICY IF EXISTS "credits_insert_purchase" ON public.credits;

CREATE POLICY "credits_select_own"
  ON public.credits FOR SELECT
  USING (auth.uid() = user_id);

-- 충전(purchase)만 직접 INSERT 허용; 차감은 deduct_credits() SECURITY DEFINER 경유
CREATE POLICY "credits_insert_purchase"
  ON public.credits FOR INSERT
  WITH CHECK (auth.uid() = user_id AND delta > 0 AND reason = 'purchase');


-- ── 4-3. payments ─────────────────────────────────────────────────────
DROP POLICY IF EXISTS "payments_select_own" ON public.payments;
DROP POLICY IF EXISTS "payments_insert_own" ON public.payments;

CREATE POLICY "payments_select_own"
  ON public.payments FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "payments_insert_own"
  ON public.payments FOR INSERT
  WITH CHECK (auth.uid() = user_id);


-- ── 4-4. email_log ────────────────────────────────────────────────────
-- INSERT는 Cloudflare Worker(service_role 키)가 RLS 우회
DROP POLICY IF EXISTS "el_admin_select"        ON public.email_log;
DROP POLICY IF EXISTS "email_log_admin_select" ON public.email_log;

CREATE POLICY "email_log_admin_select"
  ON public.email_log FOR SELECT
  USING (is_admin());


-- ── 4-5. email_unsubscribes ───────────────────────────────────────────
-- Worker INSERT는 service_role 키로 RLS 우회
DROP POLICY IF EXISTS "eu_admin_all"             ON public.email_unsubscribes;
DROP POLICY IF EXISTS "email_unsubscribes_admin" ON public.email_unsubscribes;

CREATE POLICY "email_unsubscribes_admin"
  ON public.email_unsubscribes FOR ALL
  USING     (is_admin())
  WITH CHECK (is_admin());


-- ── 4-6. page_views ───────────────────────────────────────────────────
DROP POLICY IF EXISTS "pv_insert_own"   ON public.page_views;
DROP POLICY IF EXISTS "pv_select_own"   ON public.page_views;
DROP POLICY IF EXISTS "pv_update_own"   ON public.page_views;
DROP POLICY IF EXISTS "pv_admin_select" ON public.page_views;

-- 사용자: 자신의 행 INSERT / SELECT(RETURNING 포함) / UPDATE(체류시간)
CREATE POLICY "pv_insert_own"   ON public.page_views
  FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "pv_select_own"   ON public.page_views
  FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "pv_update_own"   ON public.page_views
  FOR UPDATE USING (auth.uid() = user_id);

-- 관리자: 전체 SELECT
CREATE POLICY "pv_admin_select" ON public.page_views
  FOR SELECT USING (is_admin());


-- ══════════════════════════════════════════════════════════════════════
-- 5. 트리거 함수
-- ══════════════════════════════════════════════════════════════════════

-- ── 5-1. handle_new_user: 신규 가입 시 profiles 행 자동 생성 ──────────
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


-- ── 5-2. sync_profile_name: auth 업데이트 시 profiles 자동 동기화 ─────
--    auth.updateUser() → 이 트리거 → profiles.name·email 갱신
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
-- 6. 관리자 전용 함수 (SECURITY DEFINER — RLS 우회, 관리자만 결과 반환)
-- ══════════════════════════════════════════════════════════════════════

-- ── 6-1. admin_set_user_role: 역할 변경 ───────────────────────────────
DROP FUNCTION IF EXISTS public.admin_set_user_role(UUID, TEXT);
CREATE OR REPLACE FUNCTION public.admin_set_user_role(target_id UUID, new_role TEXT)
RETURNS TEXT
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE _caller_role TEXT;
BEGIN
  SELECT role INTO _caller_role FROM public.profiles WHERE id = auth.uid();
  IF _caller_role IS DISTINCT FROM 'admin' THEN RETURN 'error: not_admin'; END IF;
  IF new_role NOT IN ('general', 'consultant', 'gfc', 'ceo', 'staff') THEN
    RETURN 'error: invalid_role';  -- 'admin'은 DB 직접 수정만 허용
  END IF;
  UPDATE public.profiles SET role = new_role WHERE id = target_id;
  RETURN 'ok';
END;
$$;
REVOKE ALL    ON FUNCTION public.admin_set_user_role(UUID, TEXT) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.admin_set_user_role(UUID, TEXT) TO anon, authenticated;


-- ── 6-2. admin_grant_credits: 크레딧 수동 지급 ────────────────────────
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


-- ── 6-3. admin_set_user_name: 이름 변경 ───────────────────────────────
DROP FUNCTION IF EXISTS public.admin_set_user_name(UUID, TEXT);
CREATE OR REPLACE FUNCTION public.admin_set_user_name(target_id UUID, new_name TEXT)
RETURNS TEXT
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE _caller_role TEXT;
BEGIN
  SELECT role INTO _caller_role FROM public.profiles WHERE id = auth.uid();
  IF _caller_role IS DISTINCT FROM 'admin' THEN RETURN 'error: not_admin'; END IF;
  IF new_name IS NULL OR trim(new_name) = '' THEN RETURN 'error: empty_name'; END IF;
  UPDATE public.profiles SET name = trim(new_name) WHERE id = target_id;
  RETURN 'ok';
END;
$$;
REVOKE ALL    ON FUNCTION public.admin_set_user_name(UUID, TEXT) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.admin_set_user_name(UUID, TEXT) TO anon, authenticated;


-- ── 6-4. admin_get_all_profiles: 전체 회원 목록 ───────────────────────
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
  SELECT role INTO _r FROM public.profiles WHERE id = auth.uid();
  IF _r IS DISTINCT FROM 'admin' THEN RETURN; END IF;
  RETURN QUERY
    SELECT p.id, p.email, p.name, p.role, p.agreed_at
    FROM   public.profiles p
    ORDER  BY p.agreed_at DESC NULLS LAST;
END;
$$;
REVOKE ALL    ON FUNCTION public.admin_get_all_profiles() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.admin_get_all_profiles() TO anon, authenticated;


-- ── 6-5. admin_get_user_logins: 마지막 로그인 일시 조회 ───────────────
CREATE OR REPLACE FUNCTION public.admin_get_user_logins()
RETURNS TABLE (
  id              UUID,
  last_sign_in_at TIMESTAMPTZ
)
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE _r TEXT;
BEGIN
  SELECT role INTO _r FROM public.profiles WHERE id = auth.uid();
  IF _r IS DISTINCT FROM 'admin' THEN RETURN; END IF;
  RETURN QUERY
    SELECT au.id::UUID, au.last_sign_in_at
    FROM   auth.users au;
END;
$$;
REVOKE ALL    ON FUNCTION public.admin_get_user_logins() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.admin_get_user_logins() TO anon, authenticated;


-- ── 6-6. admin_page_view_stats: 페이지뷰 통계 (env 필터 포함) ──────────
--    env_filter = NULL → ['staging','portal'] 기본값
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
-- 7. 일반 함수
-- ══════════════════════════════════════════════════════════════════════

-- ── 7-1. get_user_credit_balance ──────────────────────────────────────
CREATE OR REPLACE FUNCTION public.get_user_credit_balance(p_user_id UUID)
RETURNS INTEGER
LANGUAGE SQL STABLE SECURITY DEFINER SET search_path = public AS $$
  SELECT COALESCE(SUM(delta), 0)::INT FROM public.credits WHERE user_id = p_user_id;
$$;


-- ── 7-2. deduct_credits: 앱 사용 크레딧 차감 ─────────────────────────
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


-- ── 7-3. get_email_history: 수신자별 발송 이력 ────────────────────────
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
-- 8. 뷰
-- ══════════════════════════════════════════════════════════════════════

-- ── 8-1. credit_balance: 사용자별 크레딧 잔액 요약 ────────────────────
CREATE OR REPLACE VIEW public.credit_balance
  WITH (security_invoker = true) AS
SELECT
  user_id,
  COALESCE(SUM(delta), 0)::INT                             AS balance,
  COALESCE(SUM(delta)  FILTER (WHERE delta > 0), 0)::INT   AS total_charged,
  COALESCE(SUM(-delta) FILTER (WHERE delta < 0), 0)::INT   AS total_used
FROM public.credits
GROUP BY user_id;


-- ── 8-2. page_view_stats: 페이지별 조회 통계 요약 ─────────────────────
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
-- 9. 기존 사용자 소급 동기화 (트리거 없던 시절 가입자 보완)
-- ══════════════════════════════════════════════════════════════════════

-- profiles 행 생성 (auth.users에 있지만 profiles에 없는 경우)
INSERT INTO public.profiles (id)
SELECT id FROM auth.users
ON CONFLICT (id) DO NOTHING;

-- name·email 백필
UPDATE public.profiles p
SET
  name  = COALESCE(u.raw_user_meta_data->>'full_name',
                   u.raw_user_meta_data->>'name', p.name),
  email = COALESCE(u.email, p.email)
FROM auth.users u
WHERE p.id = u.id
  AND (p.name IS NULL OR p.email IS NULL);


-- ══════════════════════════════════════════════════════════════════════
-- 10. 개발 테스트 사용자 4명
--     비밀번호 ────────────────────────────────────────────────────────
--     test@worksfree.co.kr         (일반회원)   TestPassword123!
--     consultant@worksfree.co.kr   (컨설턴트)   TestPassword123!
--     gfc@worksfree.co.kr          (GFC파트너)  TestPassword123!
--     admin@worksfree.co.kr        (관리자)     AdminPassword123!
--     멱등성: ON CONFLICT DO NOTHING → 이미 존재해도 안전
-- ══════════════════════════════════════════════════════════════════════

-- (1) 일반회원
INSERT INTO auth.users (
  id, aud, role, email, encrypted_password,
  email_confirmed_at, created_at, updated_at,
  raw_user_meta_data, raw_app_meta_data,
  is_super_admin, is_sso_user,
  confirmation_token, recovery_token, email_change, email_change_token_new
) VALUES (
  'd0000001-0000-4000-8000-000000000000'::UUID,
  'authenticated', 'authenticated', 'test@worksfree.co.kr',
  crypt('TestPassword123!', gen_salt('bf')),
  now(), now(), now(),
  '{"full_name":"테스트 회원"}'::JSONB,
  '{"provider":"email","providers":["email"]}'::JSONB,
  false, false, '', '', '', ''
) ON CONFLICT (id) DO NOTHING;

INSERT INTO auth.identities (provider_id, user_id, identity_data, provider, last_sign_in_at, created_at, updated_at)
VALUES (
  'test@worksfree.co.kr', 'd0000001-0000-4000-8000-000000000000'::UUID,
  jsonb_build_object('sub','d0000001-0000-4000-8000-000000000000',
    'email','test@worksfree.co.kr','email_verified',true,'phone_verified',false),
  'email', now(), now(), now()
) ON CONFLICT (provider_id, provider) DO NOTHING;

UPDATE public.profiles SET role = 'general', agreed_at = NOW()
WHERE id = 'd0000001-0000-4000-8000-000000000000'::UUID;


-- (2) 컨설턴트
INSERT INTO auth.users (
  id, aud, role, email, encrypted_password,
  email_confirmed_at, created_at, updated_at,
  raw_user_meta_data, raw_app_meta_data,
  is_super_admin, is_sso_user,
  confirmation_token, recovery_token, email_change, email_change_token_new
) VALUES (
  'd0000002-0000-4000-8000-000000000000'::UUID,
  'authenticated', 'authenticated', 'consultant@worksfree.co.kr',
  crypt('TestPassword123!', gen_salt('bf')),
  now(), now(), now(),
  '{"full_name":"컨설턴트 테스터"}'::JSONB,
  '{"provider":"email","providers":["email"]}'::JSONB,
  false, false, '', '', '', ''
) ON CONFLICT (id) DO NOTHING;

INSERT INTO auth.identities (provider_id, user_id, identity_data, provider, last_sign_in_at, created_at, updated_at)
VALUES (
  'consultant@worksfree.co.kr', 'd0000002-0000-4000-8000-000000000000'::UUID,
  jsonb_build_object('sub','d0000002-0000-4000-8000-000000000000',
    'email','consultant@worksfree.co.kr','email_verified',true,'phone_verified',false),
  'email', now(), now(), now()
) ON CONFLICT (provider_id, provider) DO NOTHING;

UPDATE public.profiles SET role = 'consultant', agreed_at = NOW()
WHERE id = 'd0000002-0000-4000-8000-000000000000'::UUID;


-- (3) GFC 파트너
INSERT INTO auth.users (
  id, aud, role, email, encrypted_password,
  email_confirmed_at, created_at, updated_at,
  raw_user_meta_data, raw_app_meta_data,
  is_super_admin, is_sso_user,
  confirmation_token, recovery_token, email_change, email_change_token_new
) VALUES (
  'd0000003-0000-4000-8000-000000000000'::UUID,
  'authenticated', 'authenticated', 'gfc@worksfree.co.kr',
  crypt('TestPassword123!', gen_salt('bf')),
  now(), now(), now(),
  '{"full_name":"gfc 파트너 테스터"}'::JSONB,
  '{"provider":"email","providers":["email"]}'::JSONB,
  false, false, '', '', '', ''
) ON CONFLICT (id) DO NOTHING;

INSERT INTO auth.identities (provider_id, user_id, identity_data, provider, last_sign_in_at, created_at, updated_at)
VALUES (
  'gfc@worksfree.co.kr', 'd0000003-0000-4000-8000-000000000000'::UUID,
  jsonb_build_object('sub','d0000003-0000-4000-8000-000000000000',
    'email','gfc@worksfree.co.kr','email_verified',true,'phone_verified',false),
  'email', now(), now(), now()
) ON CONFLICT (provider_id, provider) DO NOTHING;

UPDATE public.profiles SET role = 'gfc', agreed_at = NOW()
WHERE id = 'd0000003-0000-4000-8000-000000000000'::UUID;


-- (4) 관리자
INSERT INTO auth.users (
  id, aud, role, email, encrypted_password,
  email_confirmed_at, created_at, updated_at,
  raw_user_meta_data, raw_app_meta_data,
  is_super_admin, is_sso_user,
  confirmation_token, recovery_token, email_change, email_change_token_new
) VALUES (
  'd0000004-0000-4000-8000-000000000000'::UUID,
  'authenticated', 'authenticated', 'admin@worksfree.co.kr',
  crypt('AdminPassword123!', gen_salt('bf')),
  now(), now(), now(),
  '{"full_name":"관리자 테스터"}'::JSONB,
  '{"provider":"email","providers":["email"]}'::JSONB,
  false, false, '', '', '', ''
) ON CONFLICT (id) DO NOTHING;

INSERT INTO auth.identities (provider_id, user_id, identity_data, provider, last_sign_in_at, created_at, updated_at)
VALUES (
  'admin@worksfree.co.kr', 'd0000004-0000-4000-8000-000000000000'::UUID,
  jsonb_build_object('sub','d0000004-0000-4000-8000-000000000000',
    'email','admin@worksfree.co.kr','email_verified',true,'phone_verified',false),
  'email', now(), now(), now()
) ON CONFLICT (provider_id, provider) DO NOTHING;

UPDATE public.profiles SET role = 'admin', agreed_at = NOW()
WHERE id = 'd0000004-0000-4000-8000-000000000000'::UUID;


-- instance_id 보정 (GoTrue가 instance_id 없는 행은 로그인 불가)
UPDATE auth.users
SET instance_id = (
  SELECT instance_id FROM auth.users WHERE instance_id IS NOT NULL LIMIT 1
)
WHERE id IN (
  'd0000001-0000-4000-8000-000000000000'::UUID,
  'd0000002-0000-4000-8000-000000000000'::UUID,
  'd0000003-0000-4000-8000-000000000000'::UUID,
  'd0000004-0000-4000-8000-000000000000'::UUID
) AND instance_id IS NULL;


-- ══════════════════════════════════════════════════════════════════════
-- 11. 최종 검증 쿼리
-- ══════════════════════════════════════════════════════════════════════

SELECT '=== 1. 테이블 목록 ===' AS section;
SELECT table_name
FROM   information_schema.tables
WHERE  table_schema = 'public'
  AND  table_name   IN ('profiles','credits','payments',
                        'email_log','email_unsubscribes','page_views')
ORDER BY table_name;

SELECT '=== 2. email_log 컬럼 ===' AS section;
SELECT attname AS column_name
FROM   pg_attribute a
JOIN   pg_class c ON c.oid = a.attrelid
JOIN   pg_namespace n ON n.oid = c.relnamespace
WHERE  n.nspname = 'public' AND c.relname = 'email_log'
  AND  a.attnum > 0 AND NOT a.attisdropped
ORDER  BY a.attnum;

SELECT '=== 3. RLS 정책 ===' AS section;
SELECT tablename, policyname, cmd
FROM   pg_policies
WHERE  schemaname = 'public'
  AND  tablename  IN ('profiles','credits','payments',
                      'email_log','email_unsubscribes','page_views')
ORDER BY tablename, policyname;

SELECT '=== 4. 함수 목록 ===' AS section;
SELECT routine_name
FROM   information_schema.routines
WHERE  routine_schema = 'public'
  AND  routine_name   IN (
    'is_admin', 'handle_new_user', 'sync_profile_name',
    'admin_set_user_role', 'admin_grant_credits', 'admin_set_user_name',
    'admin_get_all_profiles', 'admin_get_user_logins', 'admin_page_view_stats',
    'get_user_credit_balance', 'deduct_credits', 'get_email_history'
  )
ORDER BY routine_name;

SELECT '=== 5. 트리거 ===' AS section;
SELECT trigger_name, event_object_table
FROM   information_schema.triggers
WHERE  trigger_name IN ('on_auth_user_created', 'on_auth_user_updated')
ORDER BY trigger_name;

SELECT '=== 6. 개발 테스트 사용자 ===' AS section;
SELECT id, email, name, role, agreed_at IS NOT NULL AS has_agreed
FROM   public.profiles
WHERE  id IN (
  'd0000001-0000-4000-8000-000000000000'::UUID,
  'd0000002-0000-4000-8000-000000000000'::UUID,
  'd0000003-0000-4000-8000-000000000000'::UUID,
  'd0000004-0000-4000-8000-000000000000'::UUID
)
ORDER BY id;

SELECT '=== 7. 뷰 목록 ===' AS section;
SELECT table_name AS view_name
FROM   information_schema.views
WHERE  table_schema = 'public'
  AND  table_name   IN ('credit_balance', 'page_view_stats')
ORDER BY table_name;
