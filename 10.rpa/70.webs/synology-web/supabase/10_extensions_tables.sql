-- ═══════════════════════════════════════════════════════════════════
-- 10_extensions_tables.sql
-- WorksFree Hub — [1단계] 확장 + 전체 테이블 + 인덱스 + RLS 활성화
--
-- 실행 순서: 1/7
-- 다음 단계: 20_security.sql
--
-- 포함 내용:
--   - pgcrypto 확장
--   - public.profiles        (사용자 프로필 · 역할)
--   - public.credits         (크레딧 충전/차감 원장)
--   - public.payments        (결제 내역)
--   - public.email_log       (마케팅 이메일 발송 이력)
--   - public.email_unsubscribes (수신거부 목록)
--   - public.page_views      (페이지 조회 추적)
--
-- 멱등성: CREATE TABLE IF NOT EXISTS + ADD COLUMN IF NOT EXISTS
--         → 신규 DB · 기존 DB 모두 안전하게 실행 가능
-- ═══════════════════════════════════════════════════════════════════

-- ── 0. 확장 ──────────────────────────────────────────────────────────
CREATE EXTENSION IF NOT EXISTS pgcrypto;


-- ══════════════════════════════════════════════════════════════════════
-- 1. profiles — 사용자 프로필 · 역할
-- ══════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS public.profiles (
  id               UUID        REFERENCES auth.users ON DELETE CASCADE PRIMARY KEY,
  name             TEXT,
  email            TEXT,
  agreed_at        TIMESTAMPTZ,
  marketing_agreed BOOLEAN     DEFAULT false,
  role             TEXT        DEFAULT 'general',
  created_at       TIMESTAMPTZ DEFAULT NOW()
);

-- 기존 테이블에 누락 컬럼 보완
ALTER TABLE public.profiles
  ADD COLUMN IF NOT EXISTS name             TEXT,
  ADD COLUMN IF NOT EXISTS email            TEXT,
  ADD COLUMN IF NOT EXISTS agreed_at        TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS marketing_agreed BOOLEAN     DEFAULT false,
  ADD COLUMN IF NOT EXISTS role             TEXT        DEFAULT 'general',
  ADD COLUMN IF NOT EXISTS created_at       TIMESTAMPTZ DEFAULT NOW();

-- role 값 제약 — admin은 DB 직접 설정만 가능
ALTER TABLE public.profiles DROP CONSTRAINT IF EXISTS profiles_role_check;
ALTER TABLE public.profiles
  ADD CONSTRAINT profiles_role_check
  CHECK (role IN ('general', 'consultant', 'gfc', 'ceo', 'staff', 'admin'));

ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;


-- ══════════════════════════════════════════════════════════════════════
-- 2. credits — 크레딧 충전/차감 원장 (env 컬럼으로 환경 격리)
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
-- 3. payments — 결제 내역 (Toss · Stripe)
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
-- 4. email_log — 마케팅 이메일 발송 이력
--    INSERT: Cloudflare Worker(service_role)가 RLS 우회하여 직접 삽입
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
-- 5. email_unsubscribes — 수신거부 목록
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
-- 6. page_views — 페이지 조회 추적 (체류시간 포함)
-- ══════════════════════════════════════════════════════════════════════
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
-- 검증
-- ══════════════════════════════════════════════════════════════════════
SELECT table_name
FROM   information_schema.tables
WHERE  table_schema = 'public'
  AND  table_name IN ('profiles','credits','payments',
                      'email_log','email_unsubscribes','page_views')
ORDER  BY table_name;
