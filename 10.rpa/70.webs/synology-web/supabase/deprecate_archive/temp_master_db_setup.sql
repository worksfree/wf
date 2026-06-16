-- ═══════════════════════════════════════════════════════════════════
-- WorksFree Hub — Master DB Setup  v2.0  (2026-05-29)
--
-- ✅ 멱등성: 기존 DB에 여러 번 실행해도 안전
-- ✅ 신규 DB: 처음부터 완전한 스키마 생성
-- ✅ 이메일 내역 표시 버그 수정 포함
--    → email_log.status 컬럼 + 관리자 RLS 정책
--
-- 실행 방법 ──────────────────────────────────────────────────────────
--  Supabase Dashboard (https://supabase.com)
--   → 프로젝트 선택
--   → 왼쪽 사이드바 "SQL Editor" 클릭
--   → 우상단 "New query" 클릭
--   → 이 파일 전체 내용 붙여넣기 (Ctrl+A → Ctrl+C → Ctrl+V)
--   → "Run" 버튼 클릭 (또는 Ctrl+Enter)
--   → 하단 결과 패널에서 각 섹션 결과 확인
--
-- ⚠ 일부 구간만 실행하려면: 해당 블록을 마우스로 선택 후 Ctrl+Enter
--
-- 포함 내용 ──────────────────────────────────────────────────────────
--  섹션 1  테이블: profiles · credits · payments
--          email_log · email_unsubscribes · page_views
--  섹션 2  공통 헬퍼 함수: is_admin
--  섹션 3  RLS 정책 (기존 전부 정리 후 재생성)
--  섹션 4  트리거 함수: handle_new_user · sync_profile_name
--  섹션 5  관리자 함수: admin_set_user_role · admin_grant_credits · admin_set_user_name
--  섹션 6  기타 함수: deduct_credits · get_email_history · admin_page_view_stats
--  섹션 7  뷰: credit_balance · page_view_stats
--  섹션 8  기존 사용자 데이터 소급 동기화
--  섹션 9  개발 테스트 사용자 4명 (identities + instance_id 포함)
--  섹션 10 최종 검증 쿼리
-- ═══════════════════════════════════════════════════════════════════


-- ── 0. 확장 ──────────────────────────────────────────────────────────
CREATE EXTENSION IF NOT EXISTS pgcrypto;


-- ══════════════════════════════════════════════════════════════════════
-- 1. 테이블 생성 / 컬럼 보완
--    CREATE TABLE IF NOT EXISTS → 신규 DB: 테이블 생성
--    ALTER TABLE ADD COLUMN IF NOT EXISTS → 기존 DB: 누락 컬럼 추가
-- ══════════════════════════════════════════════════════════════════════

-- ── 1-1. profiles ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.profiles (
  id               UUID        REFERENCES auth.users ON DELETE CASCADE PRIMARY KEY,
  agreed_at        TIMESTAMPTZ,
  marketing_agreed BOOLEAN     DEFAULT false,
  role             TEXT        DEFAULT 'general',
  created_at       TIMESTAMPTZ DEFAULT NOW()
);

-- 기존 테이블에 누락된 컬럼 추가
ALTER TABLE public.profiles
  ADD COLUMN IF NOT EXISTS name             TEXT,
  ADD COLUMN IF NOT EXISTS email            TEXT,
  ADD COLUMN IF NOT EXISTS agreed_at        TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS marketing_agreed BOOLEAN     DEFAULT false,
  ADD COLUMN IF NOT EXISTS role             TEXT        DEFAULT 'general',
  ADD COLUMN IF NOT EXISTS created_at       TIMESTAMPTZ DEFAULT NOW();

-- role CHECK 제약: 전체 역할 목록으로 재설정 (admin 포함)
ALTER TABLE public.profiles DROP CONSTRAINT IF EXISTS profiles_role_check;
ALTER TABLE public.profiles
  ADD CONSTRAINT profiles_role_check
  CHECK (role IN ('general', 'consultant', 'gfc', 'ceo', 'staff', 'admin'));

ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;


-- ── 1-2. credits ──────────────────────────────────────────────────────
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

-- 기존 테이블에 env 컬럼 추가 (CLAUDE.md 결제 환경 격리 정책)
ALTER TABLE public.credits ADD COLUMN IF NOT EXISTS env TEXT NOT NULL DEFAULT 'portal';

CREATE INDEX IF NOT EXISTS credits_user_created ON public.credits (user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS credits_env_idx      ON public.credits (env, created_at DESC);

ALTER TABLE public.credits ENABLE ROW LEVEL SECURITY;


-- ── 1-3. payments ─────────────────────────────────────────────────────
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


-- ── 1-4. email_log ────────────────────────────────────────────────────
-- ⚠ 이메일 내역 미표시 버그 원인:
--    이전 phase2 SQL이 status 컬럼 없이 테이블을 생성한 경우,
--    admin/content/index.html 이 status 컬럼 조회 시 오류 발생.
-- ✅ 이 파일 실행 시 status + extra 컬럼 자동 추가, 관리자 RLS 재설정.
CREATE TABLE IF NOT EXISTS public.email_log (
  id              BIGINT      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  sent_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  recipient_email TEXT        NOT NULL,
  sender_email    TEXT,
  sender_name     TEXT,
  flyer_src       TEXT,
  flyer_name      TEXT,
  subject         TEXT,
  env             TEXT        NOT NULL DEFAULT 'portal'
                  CHECK (env IN ('dev', 'test', 'staging', 'portal')),
  status          TEXT        NOT NULL DEFAULT 'sent',
  extra           JSONB       DEFAULT '{}'::JSONB
);

-- 기존 테이블(phase2로 생성)에 누락 컬럼 추가
ALTER TABLE public.email_log ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'sent';
ALTER TABLE public.email_log ADD COLUMN IF NOT EXISTS extra  JSONB DEFAULT '{}'::JSONB;

CREATE INDEX IF NOT EXISTS email_log_sent_at_idx  ON public.email_log (sent_at DESC);
CREATE INDEX IF NOT EXISTS email_log_env_idx      ON public.email_log (env, sent_at DESC);
CREATE INDEX IF NOT EXISTS email_log_recipient_idx ON public.email_log (recipient_email, sent_at DESC);
CREATE INDEX IF NOT EXISTS email_log_sender_idx   ON public.email_log (sender_email, sent_at DESC);
CREATE INDEX IF NOT EXISTS email_log_flyer_idx    ON public.email_log (flyer_name, sent_at DESC);
CREATE INDEX IF NOT EXISTS email_log_status_idx   ON public.email_log (status, sent_at DESC);

ALTER TABLE public.email_log ENABLE ROW LEVEL SECURITY;


-- ── 1-5. email_unsubscribes ───────────────────────────────────────────
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


-- ── 1-6. page_views ───────────────────────────────────────────────────
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
-- 2. 공통 헬퍼 함수 (RLS 정책이 참조하므로 정책보다 먼저 생성)
-- ══════════════════════════════════════════════════════════════════════

-- is_admin(): RLS 정책 내에서 profiles 순환 참조 방지 (SECURITY DEFINER)
CREATE OR REPLACE FUNCTION public.is_admin()
RETURNS BOOLEAN
LANGUAGE SQL STABLE SECURITY DEFINER SET search_path = public AS $$
  SELECT EXISTS (
    SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role = 'admin'
  );
$$;

GRANT EXECUTE ON FUNCTION public.is_admin() TO authenticated, anon;


-- ══════════════════════════════════════════════════════════════════════
-- 3. RLS 정책 (기존 정책 전부 정리 후 재생성 — 이름 충돌 해소)
-- ══════════════════════════════════════════════════════════════════════

-- ── 3-1. profiles ─────────────────────────────────────────────────────
-- 기존 정책 전부 삭제 (이름 불일치 방지)
DO $$ DECLARE r RECORD;
BEGIN
  FOR r IN SELECT policyname FROM pg_policies
           WHERE schemaname = 'public' AND tablename = 'profiles' LOOP
    EXECUTE format('DROP POLICY IF EXISTS %I ON public.profiles', r.policyname);
  END LOOP;
END $$;

-- 본인 행: 모든 작업 허용 (프로필 조회·수정)
CREATE POLICY "profiles_self"
  ON public.profiles FOR ALL
  USING (auth.uid() = id)
  WITH CHECK (auth.uid() = id);

-- 관리자: 전체 SELECT (사용자 목록 조회, 역할/이름 변경 대상 확인)
CREATE POLICY "profiles_admin_select_all"
  ON public.profiles FOR SELECT
  USING (is_admin());


-- ── 3-2. credits ──────────────────────────────────────────────────────
DROP POLICY IF EXISTS "credits_select_own"      ON public.credits;
DROP POLICY IF EXISTS "credits_insert_purchase" ON public.credits;

CREATE POLICY "credits_select_own"
  ON public.credits FOR SELECT
  USING (auth.uid() = user_id);

-- 프론트엔드: 충전(purchase)만 직접 INSERT 허용
-- 차감(use_app)은 deduct_credits() SECURITY DEFINER 함수만 실행
CREATE POLICY "credits_insert_purchase"
  ON public.credits FOR INSERT
  WITH CHECK (
    auth.uid() = user_id
    AND delta  > 0
    AND reason = 'purchase'
  );


-- ── 3-3. payments ─────────────────────────────────────────────────────
DROP POLICY IF EXISTS "payments_select_own" ON public.payments;
DROP POLICY IF EXISTS "payments_insert_own" ON public.payments;

CREATE POLICY "payments_select_own"
  ON public.payments FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "payments_insert_own"
  ON public.payments FOR INSERT
  WITH CHECK (auth.uid() = user_id);


-- ── 3-4. email_log ────────────────────────────────────────────────────
-- 구 정책명 포함 전부 삭제 후 통일된 이름으로 재생성
DROP POLICY IF EXISTS "el_admin_select"        ON public.email_log;
DROP POLICY IF EXISTS "email_log_admin_select" ON public.email_log;

-- 관리자만 전체 조회 가능
-- INSERT는 Cloudflare Worker(service_role 키)가 RLS 우회하여 직접 수행
CREATE POLICY "email_log_admin_select"
  ON public.email_log FOR SELECT
  USING (is_admin());


-- ── 3-5. email_unsubscribes ───────────────────────────────────────────
DROP POLICY IF EXISTS "eu_admin_all"             ON public.email_unsubscribes;
DROP POLICY IF EXISTS "email_unsubscribes_admin" ON public.email_unsubscribes;

-- 관리자: 전체 CRUD
-- Worker INSERT는 service_role 키로 RLS 우회
CREATE POLICY "email_unsubscribes_admin"
  ON public.email_unsubscribes FOR ALL
  USING     (is_admin())
  WITH CHECK (is_admin());


-- ── 3-6. page_views ───────────────────────────────────────────────────
DROP POLICY IF EXISTS "pv_insert_own"   ON public.page_views;
DROP POLICY IF EXISTS "pv_update_own"   ON public.page_views;
DROP POLICY IF EXISTS "pv_admin_select" ON public.page_views;

CREATE POLICY "pv_insert_own"   ON public.page_views
  FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "pv_update_own"   ON public.page_views
  FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "pv_admin_select" ON public.page_views
  FOR SELECT USING (is_admin());


-- ══════════════════════════════════════════════════════════════════════
-- 4. 트리거 함수
-- ══════════════════════════════════════════════════════════════════════

-- ── 4-1. handle_new_user: 신규 가입 시 profiles 행 자동 생성 ──────────
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


-- ── 4-2. sync_profile_name: auth.users 업데이트 시 profiles 자동 동기화
--    saveProfileName() → auth.updateUser() → 이 트리거 → profiles.name 갱신
--    JS에서 profiles.update() 별도 호출 불필요
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
    name  = COALESCE(_new_name,  name),   -- NULL이면 기존 값 유지
    email = COALESCE(_new_email, email)
  WHERE id = NEW.id;

  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS on_auth_user_updated ON auth.users;
CREATE TRIGGER on_auth_user_updated
  AFTER UPDATE OF raw_user_meta_data, email ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.sync_profile_name();


-- ── 4-3. 기존 가입자 소급 처리 (트리거 없던 시절 가입한 사용자) ────────
INSERT INTO public.profiles (id)
SELECT id FROM auth.users
ON CONFLICT (id) DO NOTHING;


-- ══════════════════════════════════════════════════════════════════════
-- 5. 관리자 전용 함수 (SECURITY DEFINER — RLS 우회)
-- ══════════════════════════════════════════════════════════════════════

-- ── 5-1. admin_set_user_role: 사용자 역할 변경 ────────────────────────
DROP FUNCTION IF EXISTS public.admin_set_user_role(UUID, TEXT);
CREATE OR REPLACE FUNCTION public.admin_set_user_role(
  target_id UUID,
  new_role  TEXT
)
RETURNS TEXT
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE _caller_role TEXT;
BEGIN
  SELECT role INTO _caller_role FROM public.profiles WHERE id = auth.uid();
  IF _caller_role IS DISTINCT FROM 'admin' THEN RETURN 'error: not_admin'; END IF;
  -- 'admin' 역할은 UI에서 설정 불가 (DB 직접 수정만 가능)
  IF new_role NOT IN ('general', 'consultant', 'gfc', 'ceo', 'staff') THEN
    RETURN 'error: invalid_role';
  END IF;
  UPDATE public.profiles SET role = new_role WHERE id = target_id;
  RETURN 'ok';
END;
$$;

REVOKE ALL ON FUNCTION public.admin_set_user_role(UUID, TEXT) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.admin_set_user_role(UUID, TEXT) TO anon, authenticated;


-- ── 5-2. admin_grant_credits: 크레딧 수동 지급 ────────────────────────
--    기존 phase1 버전(returns void)과 시그니처 충돌 → DROP 후 재생성
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

REVOKE ALL ON FUNCTION public.admin_grant_credits(UUID, INT, TEXT) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.admin_grant_credits(UUID, INT, TEXT) TO anon, authenticated;


-- ── 5-3. admin_set_user_name: 사용자 이름 변경 ────────────────────────
DROP FUNCTION IF EXISTS public.admin_set_user_name(UUID, TEXT);
CREATE OR REPLACE FUNCTION public.admin_set_user_name(
  target_id UUID,
  new_name  TEXT
)
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

REVOKE ALL ON FUNCTION public.admin_set_user_name(UUID, TEXT) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.admin_set_user_name(UUID, TEXT) TO anon, authenticated;


-- ── 5-4. admin_page_view_stats: 페이지뷰 통계 ─────────────────────────
CREATE OR REPLACE FUNCTION public.admin_page_view_stats(days INT DEFAULT 30)
RETURNS TABLE (
  page         TEXT,
  views        BIGINT,
  unique_users BIGINT,
  avg_sec      NUMERIC,
  pct_with_dur NUMERIC
)
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE _caller_role TEXT;
BEGIN
  SELECT role INTO _caller_role FROM public.profiles WHERE id = auth.uid();
  IF _caller_role IS DISTINCT FROM 'admin' THEN RETURN; END IF;
  RETURN QUERY
    SELECT
      pv.page,
      COUNT(*)::BIGINT,
      COUNT(DISTINCT pv.user_id)::BIGINT,
      ROUND(AVG(pv.duration_s), 1),
      ROUND(100.0 * COUNT(pv.duration_s) / NULLIF(COUNT(*), 0), 1)
    FROM public.page_views pv
    WHERE pv.viewed_at > NOW() - (days || ' days')::INTERVAL
      AND pv.env NOT IN ('dev', 'test')
    GROUP BY pv.page
    ORDER BY COUNT(*) DESC;
END;
$$;

GRANT EXECUTE ON FUNCTION public.admin_page_view_stats(INT) TO anon, authenticated;


-- ══════════════════════════════════════════════════════════════════════
-- 6. 기타 함수
-- ══════════════════════════════════════════════════════════════════════

-- ── 6-1. get_user_credit_balance ──────────────────────────────────────
CREATE OR REPLACE FUNCTION public.get_user_credit_balance(p_user_id UUID)
RETURNS INTEGER
LANGUAGE SQL STABLE SECURITY DEFINER SET search_path = public AS $$
  SELECT COALESCE(SUM(delta), 0)::INT FROM public.credits WHERE user_id = p_user_id;
$$;

-- ── 6-2. deduct_credits: 앱 사용 크레딧 차감 (서버 측 전용) ──────────
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

-- ── 6-3. get_email_history: 수신자별 발송 이력 조회 ──────────────────
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
  FROM public.email_log
  WHERE recipient_email = lower(p_email)
  ORDER BY sent_at DESC
  LIMIT p_limit;
$$;


-- ══════════════════════════════════════════════════════════════════════
-- 7. 뷰
-- ══════════════════════════════════════════════════════════════════════

-- ── 7-1. credit_balance ───────────────────────────────────────────────
CREATE OR REPLACE VIEW public.credit_balance
  WITH (security_invoker = true) AS
SELECT
  user_id,
  COALESCE(SUM(delta), 0)::INT                             AS balance,
  COALESCE(SUM(delta)  FILTER (WHERE delta > 0), 0)::INT   AS total_charged,
  COALESCE(SUM(-delta) FILTER (WHERE delta < 0), 0)::INT   AS total_used
FROM public.credits
GROUP BY user_id;

-- ── 7-2. page_view_stats ──────────────────────────────────────────────
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
-- 8. 기존 사용자 데이터 소급 동기화
-- ══════════════════════════════════════════════════════════════════════

-- profiles.name + email 백필 (auth.users에서 복사)
UPDATE public.profiles p
SET
  name  = COALESCE(
            u.raw_user_meta_data->>'full_name',
            u.raw_user_meta_data->>'name',
            p.name
          ),
  email = COALESCE(u.email, p.email)
FROM auth.users u
WHERE p.id = u.id
  AND (p.name IS NULL OR p.email IS NULL);


-- ══════════════════════════════════════════════════════════════════════
-- 9. 개발 테스트 사용자 4명
--    ── 비밀번호 ───────────────────────────────────────────────────────
--    test@worksfree.co.kr       (일반회원)   TestPassword123!
--    consultant@worksfree.co.kr (컨설턴트)  TestPassword123!
--    gfc@worksfree.co.kr        (GFC파트너)  TestPassword123!
--    admin@worksfree.co.kr      (관리자)     AdminPassword123!
--    ──────────────────────────────────────────────────────────────────
--    멱등성: ON CONFLICT DO NOTHING → 이미 존재해도 안전
-- ══════════════════════════════════════════════════════════════════════

-- (1) 일반회원 ─────────────────────────────────────────────────────────
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


-- (2) 컨설턴트 ────────────────────────────────────────────────────────
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


-- (3) GFC 파트너 ──────────────────────────────────────────────────────
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
  '{"full_name":"파트너 테스터"}'::JSONB,
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


-- (4) 관리자 ──────────────────────────────────────────────────────────
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
-- 10. 최종 검증 쿼리 (Run 후 아래 결과들을 확인)
-- ══════════════════════════════════════════════════════════════════════

SELECT '=== 테이블 목록 ===' AS section;
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name IN ('profiles','credits','payments','email_log','email_unsubscribes','page_views')
ORDER BY table_name;

SELECT '=== email_log 컬럼 (status 있어야 정상) ===' AS section;
SELECT column_name, data_type, column_default, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'email_log'
ORDER BY ordinal_position;

SELECT '=== RLS 정책 ===' AS section;
SELECT tablename, policyname, cmd
FROM pg_policies
WHERE schemaname = 'public'
  AND tablename IN ('profiles','credits','payments','email_log','email_unsubscribes','page_views')
ORDER BY tablename, policyname;

SELECT '=== 함수 목록 ===' AS section;
SELECT routine_name, security_type
FROM information_schema.routines
WHERE routine_schema = 'public'
  AND routine_name IN (
    'is_admin','handle_new_user','sync_profile_name',
    'admin_set_user_role','admin_grant_credits','admin_set_user_name',
    'admin_page_view_stats','get_user_credit_balance','deduct_credits','get_email_history'
  )
ORDER BY routine_name;

SELECT '=== 트리거 ===' AS section;
SELECT trigger_name, event_manipulation, event_object_table, action_timing
FROM information_schema.triggers
WHERE trigger_name IN ('on_auth_user_created','on_auth_user_updated')
ORDER BY trigger_name;

SELECT '=== 개발 테스트 사용자 ===' AS section;
SELECT id, email, name, role, agreed_at IS NOT NULL AS has_agreed
FROM public.profiles
WHERE id IN (
  'd0000001-0000-4000-8000-000000000000'::UUID,
  'd0000002-0000-4000-8000-000000000000'::UUID,
  'd0000003-0000-4000-8000-000000000000'::UUID,
  'd0000004-0000-4000-8000-000000000000'::UUID
)
ORDER BY id;
