-- ═══════════════════════════════════════════════════════════════════
-- 03_email_marketing.sql
-- WorksFree Hub — [Stage 3] 이메일 마케팅 · 수신거부
--
-- 책 참조: 14장(Resend + Cloudflare Worker 이메일 발송)
-- 사전 조건: 01_auth_profiles.sql 실행 완료 (02는 선택)
--
-- 포함 내용:
--   - public.email_log          (마케팅 이메일 발송 이력)
--   - public.email_unsubscribes (수신거부 목록)
--   - email_log RLS             (INSERT: Worker service_role 우회)
--   - email_unsubscribes RLS    (관리자 ALL)
--   - get_email_history          (수신자별 발송 이력 조회)
--
-- 주의: email_log INSERT는 Cloudflare Worker가 service_role 키로
--       RLS를 우회하여 직접 삽입합니다 (별도 RLS 정책 불필요).
-- 멱등성: 반복 실행 안전
-- ═══════════════════════════════════════════════════════════════════


-- ══════════════════════════════════════════════════════════════════════
-- 1. email_log — 마케팅 이메일 발송 이력
-- ══════════════════════════════════════════════════════════════════════
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

-- 기존 테이블 컬럼 보완 (멱등성)
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


-- ══════════════════════════════════════════════════════════════════════
-- 2. email_unsubscribes — 수신거부 목록
-- ══════════════════════════════════════════════════════════════════════
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


-- ══════════════════════════════════════════════════════════════════════
-- 3. RLS 정책
-- ══════════════════════════════════════════════════════════════════════

-- email_log: 관리자만 SELECT (INSERT는 Worker가 service_role로 우회)
DROP POLICY IF EXISTS "el_admin_select"        ON public.email_log;
DROP POLICY IF EXISTS "email_log_admin_select" ON public.email_log;

CREATE POLICY "email_log_admin_select"
  ON public.email_log FOR SELECT
  USING (is_admin());

-- email_unsubscribes: 관리자 ALL
DROP POLICY IF EXISTS "eu_admin_all"             ON public.email_unsubscribes;
DROP POLICY IF EXISTS "email_unsubscribes_admin" ON public.email_unsubscribes;

CREATE POLICY "email_unsubscribes_admin"
  ON public.email_unsubscribes FOR ALL
  USING     (is_admin())
  WITH CHECK (is_admin());


-- ══════════════════════════════════════════════════════════════════════
-- 4. get_email_history — 수신자별 발송 이력 조회
-- ══════════════════════════════════════════════════════════════════════
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
-- 검증
-- ══════════════════════════════════════════════════════════════════════
SELECT table_name
FROM   information_schema.tables
WHERE  table_schema = 'public'
  AND  table_name IN ('email_log', 'email_unsubscribes')
ORDER  BY table_name;
