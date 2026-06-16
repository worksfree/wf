-- ═══════════════════════════════════════════════════════════════════════
-- schema.sql
-- WorksFree Hub — 완전 마스터 스키마 (현행 버전 기준)
--
-- 목적  : 신규 Supabase 프로젝트에서 DB를 처음부터 완전히 재현
-- 버전  : 0.8.2 (2026-06-05 기준)
-- 실행  : Supabase 대시보드 → SQL Editor → 전체 붙여넣기 → Run
--
-- 실행 순서 (이 파일 단독 실행으로 전체 커버):
--   1. 확장 + 테이블       (구 10_extensions_tables.sql)
--   2. 보안 함수 + RLS     (구 20_security_rls.sql)
--   3. 트리거              (구 30_triggers.sql)
--   4. 함수               (구 40_functions.sql)
--   5. 뷰                  (구 50_views.sql)
--   6. 외부 서비스 DB       (구 60_external_dbs.sql + migration_bizdb_v2)
--   7. 사이트 설정          (migration_site_config.sql)
--
-- 멱등성 : CREATE TABLE IF NOT EXISTS / CREATE OR REPLACE / DROP IF EXISTS
--          → 기존 DB에서도 안전하게 재실행 가능
--
-- 개발용 시드 데이터: 70_seed_dev.sql 별도 실행 (프로덕션 금지)
-- ═══════════════════════════════════════════════════════════════════════


-- ════════════════════════════════════════════════════════════════════════
-- §1. 확장
-- ════════════════════════════════════════════════════════════════════════
CREATE EXTENSION IF NOT EXISTS pgcrypto;


-- ════════════════════════════════════════════════════════════════════════
-- §2. 핵심 테이블
-- ════════════════════════════════════════════════════════════════════════

-- ── 2-1. profiles — 사용자 프로필 · 역할 ─────────────────────────────
CREATE TABLE IF NOT EXISTS public.profiles (
  id               UUID        REFERENCES auth.users ON DELETE CASCADE PRIMARY KEY,
  name             TEXT,
  email            TEXT,
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

-- 역할 값 제약 (admin은 DB 직접 설정만 허용)
ALTER TABLE public.profiles DROP CONSTRAINT IF EXISTS profiles_role_check;
ALTER TABLE public.profiles ADD CONSTRAINT profiles_role_check
  CHECK (role IN ('general','consultant','gfc','ceo','staff','admin'));

ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;


-- ── 2-2. credits — 크레딧 충전/차감 원장 ─────────────────────────────
CREATE TABLE IF NOT EXISTS public.credits (
  id           BIGINT      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  user_id      UUID        NOT NULL REFERENCES auth.users ON DELETE CASCADE,
  delta        INTEGER     NOT NULL,
  reason       TEXT        NOT NULL
               CHECK (reason IN ('purchase','use_app','admin_grant','refund')),
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


-- ── 2-3. payments — 결제 내역 (Toss · Stripe) ────────────────────────
CREATE TABLE IF NOT EXISTS public.payments (
  id           BIGINT        GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  user_id      UUID          NOT NULL REFERENCES auth.users ON DELETE CASCADE,
  order_id     TEXT          NOT NULL UNIQUE,
  pg           TEXT          NOT NULL CHECK (pg IN ('toss','stripe')),
  amount_krw   INTEGER       NOT NULL DEFAULT 0,
  amount_usd   NUMERIC(10,2) NOT NULL DEFAULT 0,
  credits      INTEGER       NOT NULL,
  status       TEXT          NOT NULL DEFAULT 'paid'
               CHECK (status IN ('paid','cancelled','refunded')),
  env          TEXT          NOT NULL DEFAULT 'portal',
  created_at   TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

ALTER TABLE public.payments ADD COLUMN IF NOT EXISTS env TEXT NOT NULL DEFAULT 'portal';

CREATE INDEX IF NOT EXISTS payments_user_created ON public.payments (user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS payments_env_idx      ON public.payments (env, created_at DESC);
ALTER TABLE public.payments ENABLE ROW LEVEL SECURITY;


-- ── 2-4. email_log — 마케팅 이메일 발송 이력 ─────────────────────────
--    INSERT: Cloudflare Worker(service_role)가 RLS 우회하여 직접 삽입
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
                  CHECK (env IN ('dev','test','staging','portal')),
  status          TEXT        NOT NULL DEFAULT 'sent'
                  CHECK (status IN ('sent','filtered')),
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


-- ── 2-5. email_unsubscribes — 수신거부 목록 ──────────────────────────
CREATE TABLE IF NOT EXISTS public.email_unsubscribes (
  id              BIGINT      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  email           TEXT        UNIQUE NOT NULL,
  source          TEXT        DEFAULT 'link' CHECK (source IN ('link','manual')),
  note            TEXT,
  unsubscribed_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS email_unsub_email_idx ON public.email_unsubscribes (email);
CREATE INDEX IF NOT EXISTS email_unsub_at_idx    ON public.email_unsubscribes (unsubscribed_at DESC);
ALTER TABLE public.email_unsubscribes ENABLE ROW LEVEL SECURITY;


-- ── 2-6. page_views — 페이지 조회 추적 ───────────────────────────────
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


-- ════════════════════════════════════════════════════════════════════════
-- §3. 보안 함수 + RLS 정책
-- ════════════════════════════════════════════════════════════════════════

-- ── 3-1. is_admin() 헬퍼 ─────────────────────────────────────────────
CREATE OR REPLACE FUNCTION public.is_admin()
RETURNS BOOLEAN
LANGUAGE SQL STABLE SECURITY DEFINER SET search_path = public AS $$
  SELECT EXISTS (
    SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role = 'admin'
  );
$$;
GRANT EXECUTE ON FUNCTION public.is_admin() TO authenticated, anon;


-- ── 3-2. profiles RLS ────────────────────────────────────────────────
DO $$ DECLARE r RECORD;
BEGIN
  FOR r IN SELECT policyname FROM pg_policies
           WHERE schemaname = 'public' AND tablename = 'profiles' LOOP
    EXECUTE format('DROP POLICY IF EXISTS %I ON public.profiles', r.policyname);
  END LOOP;
END $$;

CREATE POLICY "profiles_self"
  ON public.profiles FOR ALL
  USING (auth.uid() = id) WITH CHECK (auth.uid() = id);

CREATE POLICY "profiles_admin_select_all"
  ON public.profiles FOR SELECT USING (is_admin());


-- ── 3-3. credits RLS ─────────────────────────────────────────────────
DROP POLICY IF EXISTS "credits_select_own"      ON public.credits;
DROP POLICY IF EXISTS "credits_insert_purchase" ON public.credits;

CREATE POLICY "credits_select_own"
  ON public.credits FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "credits_insert_purchase"
  ON public.credits FOR INSERT
  WITH CHECK (auth.uid() = user_id AND delta > 0 AND reason = 'purchase');


-- ── 3-4. payments RLS ────────────────────────────────────────────────
DROP POLICY IF EXISTS "payments_select_own" ON public.payments;
DROP POLICY IF EXISTS "payments_insert_own" ON public.payments;

CREATE POLICY "payments_select_own"
  ON public.payments FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "payments_insert_own"
  ON public.payments FOR INSERT WITH CHECK (auth.uid() = user_id);


-- ── 3-5. email_log RLS ───────────────────────────────────────────────
DROP POLICY IF EXISTS "el_admin_select"        ON public.email_log;
DROP POLICY IF EXISTS "email_log_admin_select" ON public.email_log;

CREATE POLICY "email_log_admin_select"
  ON public.email_log FOR SELECT USING (is_admin());


-- ── 3-6. email_unsubscribes RLS ──────────────────────────────────────
DROP POLICY IF EXISTS "eu_admin_all"             ON public.email_unsubscribes;
DROP POLICY IF EXISTS "email_unsubscribes_admin" ON public.email_unsubscribes;

CREATE POLICY "email_unsubscribes_admin"
  ON public.email_unsubscribes FOR ALL
  USING (is_admin()) WITH CHECK (is_admin());


-- ── 3-7. page_views RLS ──────────────────────────────────────────────
DROP POLICY IF EXISTS "pv_insert_own"   ON public.page_views;
DROP POLICY IF EXISTS "pv_select_own"   ON public.page_views;
DROP POLICY IF EXISTS "pv_update_own"   ON public.page_views;
DROP POLICY IF EXISTS "pv_admin_select" ON public.page_views;

CREATE POLICY "pv_insert_own"   ON public.page_views FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "pv_select_own"   ON public.page_views FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "pv_update_own"   ON public.page_views FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "pv_admin_select" ON public.page_views FOR SELECT USING (is_admin());


-- ════════════════════════════════════════════════════════════════════════
-- §4. 트리거
-- ════════════════════════════════════════════════════════════════════════

-- ── 4-1. handle_new_user — 신규 가입 시 profiles 자동 생성 ───────────
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


-- ── 4-2. sync_profile_name — auth 업데이트 시 profiles 자동 동기화 ───
CREATE OR REPLACE FUNCTION public.sync_profile_name()
RETURNS TRIGGER LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
BEGIN
  UPDATE public.profiles
  SET
    name  = COALESCE(
              NEW.raw_user_meta_data->>'full_name',
              NEW.raw_user_meta_data->>'name', name),
    email = COALESCE(NEW.email, email)
  WHERE id = NEW.id;
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS on_auth_user_updated ON auth.users;
CREATE TRIGGER on_auth_user_updated
  AFTER UPDATE OF raw_user_meta_data, email ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.sync_profile_name();


-- 기존 사용자 소급 동기화
INSERT INTO public.profiles (id) SELECT id FROM auth.users ON CONFLICT (id) DO NOTHING;
UPDATE public.profiles p
SET name  = COALESCE(u.raw_user_meta_data->>'full_name', u.raw_user_meta_data->>'name', p.name),
    email = COALESCE(u.email, p.email)
FROM auth.users u WHERE p.id = u.id AND (p.name IS NULL OR p.email IS NULL);


-- ════════════════════════════════════════════════════════════════════════
-- §5. 함수
-- ════════════════════════════════════════════════════════════════════════

-- ── 5-1. admin_set_user_role ──────────────────────────────────────────
DROP FUNCTION IF EXISTS public.admin_set_user_role(UUID, TEXT);
CREATE OR REPLACE FUNCTION public.admin_set_user_role(target_id UUID, new_role TEXT)
RETURNS TEXT LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE _r TEXT;
BEGIN
  SELECT role INTO _r FROM public.profiles WHERE id = auth.uid();
  IF _r IS DISTINCT FROM 'admin' THEN RETURN 'error: not_admin'; END IF;
  IF new_role NOT IN ('general','consultant','gfc','ceo','staff') THEN RETURN 'error: invalid_role'; END IF;
  UPDATE public.profiles SET role = new_role WHERE id = target_id;
  RETURN 'ok';
END;
$$;
REVOKE ALL ON FUNCTION public.admin_set_user_role(UUID, TEXT) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.admin_set_user_role(UUID, TEXT) TO anon, authenticated;


-- ── 5-2. admin_grant_credits ──────────────────────────────────────────
DROP FUNCTION IF EXISTS public.admin_grant_credits(UUID, INT, TEXT);
DROP FUNCTION IF EXISTS public.admin_grant_credits(UUID, INTEGER, TEXT);
CREATE OR REPLACE FUNCTION public.admin_grant_credits(
  target_id UUID, amount INT, env_name TEXT DEFAULT 'portal'
)
RETURNS TEXT LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE _r TEXT;
BEGIN
  SELECT role INTO _r FROM public.profiles WHERE id = auth.uid();
  IF _r IS DISTINCT FROM 'admin' THEN RETURN 'error: not_admin'; END IF;
  IF amount < 1 THEN RETURN 'error: invalid_amount'; END IF;
  INSERT INTO public.credits (user_id, delta, reason, note, env, created_at)
  VALUES (target_id, amount, 'admin_grant', '관리자 수동 지급', env_name, NOW());
  RETURN 'ok';
END;
$$;
REVOKE ALL ON FUNCTION public.admin_grant_credits(UUID, INT, TEXT) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.admin_grant_credits(UUID, INT, TEXT) TO anon, authenticated;


-- ── 5-3. admin_set_user_name ──────────────────────────────────────────
DROP FUNCTION IF EXISTS public.admin_set_user_name(UUID, TEXT);
CREATE OR REPLACE FUNCTION public.admin_set_user_name(target_id UUID, new_name TEXT)
RETURNS TEXT LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE _r TEXT;
BEGIN
  SELECT role INTO _r FROM public.profiles WHERE id = auth.uid();
  IF _r IS DISTINCT FROM 'admin' THEN RETURN 'error: not_admin'; END IF;
  IF new_name IS NULL OR trim(new_name) = '' THEN RETURN 'error: empty_name'; END IF;
  UPDATE public.profiles SET name = trim(new_name) WHERE id = target_id;
  RETURN 'ok';
END;
$$;
REVOKE ALL ON FUNCTION public.admin_set_user_name(UUID, TEXT) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.admin_set_user_name(UUID, TEXT) TO anon, authenticated;


-- ── 5-4. admin_get_all_profiles ───────────────────────────────────────
CREATE OR REPLACE FUNCTION public.admin_get_all_profiles()
RETURNS TABLE (id UUID, email TEXT, name TEXT, role TEXT, agreed_at TIMESTAMPTZ)
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE _r TEXT;
BEGIN
  SELECT role INTO _r FROM public.profiles WHERE id = auth.uid();
  IF _r IS DISTINCT FROM 'admin' THEN RETURN; END IF;
  RETURN QUERY SELECT p.id, p.email, p.name, p.role, p.agreed_at
               FROM public.profiles p ORDER BY p.agreed_at DESC NULLS LAST;
END;
$$;
REVOKE ALL ON FUNCTION public.admin_get_all_profiles() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.admin_get_all_profiles() TO anon, authenticated;


-- ── 5-5. admin_get_user_logins ────────────────────────────────────────
CREATE OR REPLACE FUNCTION public.admin_get_user_logins()
RETURNS TABLE (id UUID, last_sign_in_at TIMESTAMPTZ)
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE _r TEXT;
BEGIN
  SELECT role INTO _r FROM public.profiles WHERE id = auth.uid();
  IF _r IS DISTINCT FROM 'admin' THEN RETURN; END IF;
  RETURN QUERY SELECT au.id::UUID, au.last_sign_in_at FROM auth.users au;
END;
$$;
REVOKE ALL ON FUNCTION public.admin_get_user_logins() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.admin_get_user_logins() TO anon, authenticated;


-- ── 5-6. admin_page_view_stats ────────────────────────────────────────
DROP FUNCTION IF EXISTS public.admin_page_view_stats(INT);
CREATE OR REPLACE FUNCTION public.admin_page_view_stats(
  days       INT    DEFAULT 30,
  env_filter TEXT[] DEFAULT NULL
)
RETURNS TABLE (page TEXT, views BIGINT, unique_users BIGINT, avg_sec NUMERIC, pct_with_dur NUMERIC)
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE _r TEXT; _envs TEXT[];
BEGIN
  SELECT role INTO _r FROM public.profiles WHERE id = auth.uid();
  IF _r IS DISTINCT FROM 'admin' THEN RETURN; END IF;
  _envs := COALESCE(env_filter, ARRAY['staging','portal']::TEXT[]);
  RETURN QUERY
    SELECT pv.page, COUNT(*)::BIGINT, COUNT(DISTINCT pv.user_id)::BIGINT,
           ROUND(AVG(pv.duration_s), 1),
           ROUND(100.0 * COUNT(pv.duration_s) / NULLIF(COUNT(*), 0), 1)
    FROM public.page_views pv
    WHERE pv.viewed_at > NOW() - (days || ' days')::INTERVAL
      AND pv.env = ANY(_envs)
    GROUP BY pv.page ORDER BY COUNT(*) DESC;
END;
$$;
REVOKE ALL ON FUNCTION public.admin_page_view_stats(INT, TEXT[]) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.admin_page_view_stats(INT, TEXT[]) TO anon, authenticated;


-- ── 5-7. 일반 함수 ───────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION public.get_user_credit_balance(p_user_id UUID)
RETURNS INTEGER LANGUAGE SQL STABLE SECURITY DEFINER SET search_path = public AS $$
  SELECT COALESCE(SUM(delta), 0)::INT FROM public.credits WHERE user_id = p_user_id;
$$;

CREATE OR REPLACE FUNCTION public.deduct_credits(
  p_user_id UUID, p_amount INTEGER, p_app_id TEXT, p_note TEXT DEFAULT NULL
)
RETURNS INTEGER LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
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

CREATE OR REPLACE FUNCTION public.get_email_history(p_email TEXT, p_limit INT DEFAULT 10)
RETURNS TABLE (sent_at TIMESTAMPTZ, flyer_name TEXT, sender_name TEXT, subject TEXT, env TEXT)
LANGUAGE SQL STABLE SECURITY DEFINER SET search_path = public AS $$
  SELECT sent_at, flyer_name, sender_name, subject, env
  FROM public.email_log
  WHERE recipient_email = lower(p_email)
  ORDER BY sent_at DESC LIMIT p_limit;
$$;


-- ════════════════════════════════════════════════════════════════════════
-- §6. 뷰
-- ════════════════════════════════════════════════════════════════════════
CREATE OR REPLACE VIEW public.credit_balance WITH (security_invoker = true) AS
SELECT user_id,
  COALESCE(SUM(delta), 0)::INT                           AS balance,
  COALESCE(SUM(delta)  FILTER (WHERE delta > 0), 0)::INT AS total_charged,
  COALESCE(SUM(-delta) FILTER (WHERE delta < 0), 0)::INT AS total_used
FROM public.credits GROUP BY user_id;

CREATE OR REPLACE VIEW public.page_view_stats AS
SELECT page,
  COUNT(*)                                                       AS total_views,
  COUNT(DISTINCT user_id)                                        AS unique_users,
  ROUND(AVG(duration_s))                                         AS avg_duration_s,
  COUNT(*) FILTER (WHERE viewed_at > NOW() - INTERVAL '7 days') AS views_7d,
  COUNT(*) FILTER (WHERE viewed_at > NOW() - INTERVAL '30 days')AS views_30d,
  MAX(viewed_at)                                                 AS last_viewed
FROM public.page_views GROUP BY page ORDER BY total_views DESC;


-- ════════════════════════════════════════════════════════════════════════
-- §7. 외부 서비스 DB — B2B 이메일 · 채용 자동화
--     Cloudflare Worker(service_role)가 RLS 우회하여 직접 접근
-- ════════════════════════════════════════════════════════════════════════

-- ── 7-1. biz_contacts — 기업 이메일 DB ──────────────────────────────
CREATE TABLE IF NOT EXISTS public.biz_contacts (
  id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  corp_code     TEXT        UNIQUE,
  corp_name     TEXT        NOT NULL,
  ceo_nm        TEXT,
  induty_code   TEXT,
  induty_name   TEXT,
  adres         TEXT,
  hm_url        TEXT,
  email         TEXT,
  email_source  TEXT        DEFAULT 'homepage'
                CHECK (email_source IN ('homepage','contact-page','manual','csv','purchased','dart')),
  email_status  TEXT        DEFAULT 'active'
                CHECK (email_status IN ('active','bounced','unsubscribed')),
  scrape_status TEXT        DEFAULT 'pending'
                CHECK (scrape_status IN ('pending','done','no_url','no_email','error')),
  notes         TEXT,
  created_at    TIMESTAMPTZ DEFAULT NOW(),
  updated_at    TIMESTAMPTZ DEFAULT NOW()
);

-- CHECK 제약 최신화 (email_source에 csv/purchased/dart 포함)
ALTER TABLE public.biz_contacts
  DROP CONSTRAINT IF EXISTS biz_contacts_email_source_check;
ALTER TABLE public.biz_contacts ADD CONSTRAINT biz_contacts_email_source_check
  CHECK (email_source IN ('homepage','contact-page','manual','csv','purchased','dart'));

CREATE INDEX IF NOT EXISTS biz_contacts_corp_name_idx    ON public.biz_contacts (corp_name);
CREATE INDEX IF NOT EXISTS biz_contacts_email_idx        ON public.biz_contacts (email);
CREATE INDEX IF NOT EXISTS biz_contacts_email_status_idx ON public.biz_contacts (email_status);
CREATE INDEX IF NOT EXISTS biz_contacts_induty_name_idx  ON public.biz_contacts (induty_name);
CREATE INDEX IF NOT EXISTS biz_contacts_scrape_idx       ON public.biz_contacts (scrape_status);
CREATE INDEX IF NOT EXISTS biz_contacts_created_idx      ON public.biz_contacts (created_at DESC);
ALTER TABLE public.biz_contacts ENABLE ROW LEVEL SECURITY;


-- ── 7-2. biz_send_log — 발송 이력 (월별 로테이션 추적) ───────────────
CREATE TABLE IF NOT EXISTS public.biz_send_log (
  id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  contact_id  UUID        REFERENCES public.biz_contacts(id) ON DELETE SET NULL,
  email       TEXT        NOT NULL,
  corp_name   TEXT,
  batch_month TEXT        NOT NULL,
  sent_at     TIMESTAMPTZ DEFAULT NOW(),
  -- 발송 추적 (migration_bizdb_v2 추가)
  status      TEXT        DEFAULT 'sent'
              CHECK (status IN ('sent','failed','delivered','opened','clicked','bounced','complained')),
  resend_id   TEXT,        -- Resend API 반환 ID
  flyer_name  TEXT,        -- 발송 전단지
  subject     TEXT,        -- 이메일 제목
  opened_at   TIMESTAMPTZ, -- Resend webhook: email.opened
  clicked_at  TIMESTAMPTZ, -- Resend webhook: email.clicked
  bounced_at  TIMESTAMPTZ  -- Resend webhook: email.bounced
);

ALTER TABLE public.biz_send_log
  ADD COLUMN IF NOT EXISTS status     TEXT        DEFAULT 'sent',
  ADD COLUMN IF NOT EXISTS resend_id  TEXT,
  ADD COLUMN IF NOT EXISTS flyer_name TEXT,
  ADD COLUMN IF NOT EXISTS subject    TEXT,
  ADD COLUMN IF NOT EXISTS opened_at  TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS clicked_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS bounced_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS biz_send_log_email_month ON public.biz_send_log (email, batch_month);
CREATE INDEX IF NOT EXISTS biz_send_log_month_idx   ON public.biz_send_log (batch_month DESC);
CREATE INDEX IF NOT EXISTS biz_send_log_resend_id   ON public.biz_send_log (resend_id) WHERE resend_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS biz_send_log_status      ON public.biz_send_log (status);
ALTER TABLE public.biz_send_log ENABLE ROW LEVEL SECURITY;


-- ── 7-3. biz_send_batches — 발송 배치 관리 (신규) ────────────────────
CREATE TABLE IF NOT EXISTS public.biz_send_batches (
  id             UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  batch_name     TEXT,
  batch_month    TEXT        NOT NULL,
  flyer_name     TEXT,
  subject        TEXT,
  filter_induty  TEXT,
  total_targets  INT         DEFAULT 0,
  total_sent     INT         DEFAULT 0,
  total_failed   INT         DEFAULT 0,
  total_opened   INT         DEFAULT 0,
  created_at     TIMESTAMPTZ DEFAULT NOW(),
  completed_at   TIMESTAMPTZ,
  notes          TEXT
);

CREATE INDEX IF NOT EXISTS biz_send_batches_month ON public.biz_send_batches (batch_month DESC);
ALTER TABLE public.biz_send_batches ENABLE ROW LEVEL SECURITY;


-- ── 7-4. jobkorea_proposals — 잡코리아 입사제안 이력 ─────────────────
CREATE TABLE IF NOT EXISTS public.jobkorea_proposals (
  id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  candidate_id TEXT        UNIQUE NOT NULL,
  name         TEXT,
  career       TEXT,
  keyword      TEXT,
  status       TEXT        NOT NULL DEFAULT 'sent'
               CHECK (status IN ('sent','error','skipped')),
  sent_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  message_used TEXT,
  notes        TEXT
);

CREATE INDEX IF NOT EXISTS jobkorea_proposals_sent_at ON public.jobkorea_proposals (sent_at DESC);
CREATE INDEX IF NOT EXISTS jobkorea_proposals_keyword ON public.jobkorea_proposals (keyword);
CREATE INDEX IF NOT EXISTS jobkorea_proposals_status  ON public.jobkorea_proposals (status);
ALTER TABLE public.jobkorea_proposals ENABLE ROW LEVEL SECURITY;

-- jobkorea_proposals RLS (anon read for admin page, service_role all)
DROP POLICY IF EXISTS "jp_anon_read"     ON public.jobkorea_proposals;
DROP POLICY IF EXISTS "jp_service_write" ON public.jobkorea_proposals;
CREATE POLICY "jp_anon_read"     ON public.jobkorea_proposals FOR SELECT USING (true);
CREATE POLICY "jp_service_write" ON public.jobkorea_proposals FOR ALL  USING (true) WITH CHECK (true);

-- jobkorea_stats 뷰 (채용 관리 대시보드용)
CREATE OR REPLACE VIEW public.jobkorea_stats AS
SELECT
  COUNT(*) FILTER (WHERE status = 'sent')                                     AS total_sent,
  COUNT(*) FILTER (WHERE status = 'error')                                    AS total_error,
  COUNT(*) FILTER (WHERE status = 'skipped')                                  AS total_skipped,
  COUNT(*) FILTER (WHERE status = 'sent'
                     AND sent_at >= date_trunc('week', NOW()))                AS this_week,
  COUNT(*) FILTER (WHERE status = 'sent'
                     AND to_char(sent_at AT TIME ZONE 'Asia/Seoul','YYYY-MM')
                       = to_char(NOW() AT TIME ZONE 'Asia/Seoul','YYYY-MM'))  AS this_month,
  MAX(sent_at) FILTER (WHERE status = 'sent')                                 AS last_sent_at
FROM public.jobkorea_proposals;


-- ════════════════════════════════════════════════════════════════════════
-- §8. 사이트 설정 (site_config) — 페이지 권한 관리 등
-- ════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS public.site_config (
  key        TEXT        PRIMARY KEY,
  value      JSONB       NOT NULL DEFAULT '{}',
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE public.site_config ENABLE ROW LEVEL SECURITY;

-- 읽기: 모든 사용자 (anon 포함 — Hub가 읽어야 함)
DROP POLICY IF EXISTS "site_config_read_all"   ON public.site_config;
DROP POLICY IF EXISTS "site_config_write_admin" ON public.site_config;

CREATE POLICY "site_config_read_all"
  ON public.site_config FOR SELECT USING (true);

CREATE POLICY "site_config_write_admin"
  ON public.site_config FOR ALL
  USING (
    EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role = 'admin')
  );

-- 기본 페이지 접근 규칙
INSERT INTO public.site_config (key, value) VALUES (
  'page_access_rules',
  '{
    "consulting/gfc/index.html": {
      "general":    "hidden",
      "member":     "hidden",
      "consultant": "blur",
      "gfc":        "full",
      "admin":      "full"
    }
  }'::jsonb
) ON CONFLICT (key) DO NOTHING;


-- ════════════════════════════════════════════════════════════════════════
-- §9. 최종 검증
-- ════════════════════════════════════════════════════════════════════════
SELECT
  table_name,
  (SELECT COUNT(*) FROM information_schema.columns c
   WHERE c.table_schema = 'public' AND c.table_name = t.table_name) AS col_count
FROM information_schema.tables t
WHERE table_schema = 'public'
  AND table_type = 'BASE TABLE'
ORDER BY table_name;
