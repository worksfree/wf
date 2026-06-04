-- ================================================================
-- email_log.sql
-- 이메일 발송 이력 + 수신거부 테이블
--
-- 데이터 흐름:
--   마케팅 자료 페이지 → Cloudflare Worker (send-mail.worksfree.workers.dev)
--     → Resend API (실제 발송)
--     → Supabase email_log (service_role 키로 INSERT — RLS 우회)
--
--   관리자 패널(O&M) → email_log SELECT (admin 역할 사용자만 허용)
--
-- Supabase Dashboard > SQL Editor 에서 실행
-- ================================================================


-- ── 1. email_log — 발송 이력 ─────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.email_log (
  id              BIGSERIAL PRIMARY KEY,
  sent_at         TIMESTAMPTZ DEFAULT NOW(),
  recipient_email TEXT        NOT NULL,
  sender_email    TEXT,
  sender_name     TEXT,
  flyer_src       TEXT,                     -- 전단지 파일 경로
  flyer_name      TEXT,                     -- 전단지 표시 이름
  subject         TEXT,
  env             TEXT        DEFAULT 'portal',  -- 'portal' | 'staging' | 'test'
  status          TEXT        DEFAULT 'sent'     -- 'sent' | 'filtered'
);

-- 조회 성능용 인덱스
CREATE INDEX IF NOT EXISTS email_log_sent_at_idx   ON public.email_log(sent_at DESC);
CREATE INDEX IF NOT EXISTS email_log_env_idx        ON public.email_log(env, sent_at DESC);
CREATE INDEX IF NOT EXISTS email_log_recipient_idx  ON public.email_log(recipient_email, sent_at DESC);
CREATE INDEX IF NOT EXISTS email_log_sender_idx     ON public.email_log(sender_email, sent_at DESC);
CREATE INDEX IF NOT EXISTS email_log_flyer_idx      ON public.email_log(flyer_name, sent_at DESC);

-- RLS
ALTER TABLE public.email_log ENABLE ROW LEVEL SECURITY;

-- 관리자만 조회 가능 (INSERT는 Worker의 service_role 키로 RLS 우회)
CREATE POLICY "el_admin_select" ON public.email_log
  FOR SELECT USING (
    EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role = 'admin')
  );


-- ── 2. email_unsubscribes — 수신거부 목록 ─────────────────────────
CREATE TABLE IF NOT EXISTS public.email_unsubscribes (
  id              BIGSERIAL PRIMARY KEY,
  email           TEXT        UNIQUE NOT NULL,
  source          TEXT        DEFAULT 'link',  -- 'link' | 'manual'
  note            TEXT,
  unsubscribed_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS email_unsub_email_idx ON public.email_unsubscribes(email);
CREATE INDEX IF NOT EXISTS email_unsub_at_idx    ON public.email_unsubscribes(unsubscribed_at DESC);

-- RLS
ALTER TABLE public.email_unsubscribes ENABLE ROW LEVEL SECURITY;

-- 관리자: 전체 읽기 + INSERT(수동 등록) + DELETE(해제)
CREATE POLICY "eu_admin_all" ON public.email_unsubscribes
  FOR ALL USING (
    EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role = 'admin')
  );

-- Worker가 POST /unsubscribe 로 INSERT할 때는 service_role 키 사용 (RLS 우회)
-- 수신거부 링크 처리: consulting/unsubscribe/?e=... 페이지가 Worker POST /unsubscribe 호출


-- ── 3. 확인 쿼리 ─────────────────────────────────────────────────
SELECT 'email_log'         AS table_name, COUNT(*) AS rows FROM public.email_log
UNION ALL
SELECT 'email_unsubscribes', COUNT(*) FROM public.email_unsubscribes;
