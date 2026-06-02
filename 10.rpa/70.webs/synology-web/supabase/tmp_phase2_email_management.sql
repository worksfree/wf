-- ═══════════════════════════════════════════════════════════════════
-- WorksFree Hub — Phase 2: 이메일 발송 관리 (Email Management)
-- 실행 방법: Supabase Dashboard → SQL Editor → 이 파일 붙여넣기 → Run
-- 멱등성 보장: 여러 번 실행해도 동일한 결과
--
-- 신규 테이블:
--   email_log          — 발송 이력 (Cloudflare Worker service key로만 INSERT)
--   email_unsubscribes — 수신거부 목록 (Cloudflare Worker service key로만 INSERT)
--
-- ⚠ Worker 시크릿 추가 필요 (service/payment/ 폴더에서 실행):
--   wrangler secret put SUPABASE_URL         --config wrangler-mail.toml
--   wrangler secret put SUPABASE_SERVICE_KEY --config wrangler-mail.toml
--
-- SUPABASE_URL         = https://rkycwfpkzorfpcxfvaqt.supabase.co  (TEST DB)
-- SUPABASE_SERVICE_KEY = .env.test 파일의 TEST_SUPABASE_SERVICE_KEY 값
-- ═══════════════════════════════════════════════════════════════════


-- ────────────────────────────────────────────────────────────────
-- 1. email_log — 발송 이력
--    INSERT는 Worker(service_role)만 수행 — RLS로 anon 차단
-- ────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS email_log (
  id              bigint       GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  sent_at         timestamptz  NOT NULL DEFAULT now(),
  recipient_email text         NOT NULL,   -- 수신자 이메일 (소문자 정규화)
  sender_email    text,                    -- 컨설턴트 이메일
  sender_name     text,                    -- 컨설턴트 이름
  flyer_src       text,                    -- 전단지 파일 경로 (예: consulting/ceo/flyers/flyer-ceo.html)
  flyer_name      text,                    -- 전단지 표시 이름
  subject         text,                    -- 발송 제목
  env             text         NOT NULL DEFAULT 'portal'  -- test | staging | portal
                  CHECK (env IN ('dev', 'test', 'staging', 'portal')),
  extra           jsonb        DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS email_log_recipient_idx
  ON email_log (recipient_email, sent_at DESC);

CREATE INDEX IF NOT EXISTS email_log_sender_idx
  ON email_log (sender_email, sent_at DESC);

CREATE INDEX IF NOT EXISTS email_log_env_idx
  ON email_log (env, sent_at DESC);

ALTER TABLE email_log ENABLE ROW LEVEL SECURITY;

-- service_role(Worker)은 RLS 무시 → 항상 접근 가능
-- anon/authenticated 정책 없음 = 프론트엔드 직접 접근 불가


-- ────────────────────────────────────────────────────────────────
-- 2. email_unsubscribes — 수신거부 목록
--    INSERT/DELETE는 Worker(service_role)만 — RLS로 anon 차단
-- ────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS email_unsubscribes (
  id               bigint       GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  email            text         NOT NULL UNIQUE,              -- 소문자 정규화
  unsubscribed_at  timestamptz  NOT NULL DEFAULT now(),
  source           text         NOT NULL DEFAULT 'link'
                   CHECK (source IN ('link', 'manual')),
  note             text
);

CREATE INDEX IF NOT EXISTS email_unsubscribes_email_idx
  ON email_unsubscribes (email);

ALTER TABLE email_unsubscribes ENABLE ROW LEVEL SECURITY;

-- service_role(Worker)은 RLS 무시 → 항상 접근 가능
-- anon/authenticated 정책 없음 = 프론트엔드 직접 접근 불가


-- ────────────────────────────────────────────────────────────────
-- 3. 헬퍼 함수 — 발송 이력 조회
--    (선택적 — 향후 관리 대시보드용)
-- ────────────────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION get_email_history(p_email text, p_limit int DEFAULT 10)
RETURNS TABLE (
  sent_at         timestamptz,
  flyer_name      text,
  sender_name     text,
  subject         text,
  env             text
)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public AS $$
  SELECT sent_at, flyer_name, sender_name, subject, env
  FROM email_log
  WHERE recipient_email = lower(p_email)
  ORDER BY sent_at DESC
  LIMIT p_limit;
$$;


-- ────────────────────────────────────────────────────────────────
-- 4. 최종 검증
-- ────────────────────────────────────────────────────────────────

SELECT '=== Phase 2 테이블 ===' AS section;
SELECT table_name, table_type
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name IN ('email_log', 'email_unsubscribes')
ORDER BY table_name;

SELECT '=== RLS 상태 ===' AS section;
SELECT relname AS table_name, relrowsecurity AS rls_enabled
FROM pg_class
WHERE relname IN ('email_log', 'email_unsubscribes')
  AND relkind = 'r';

SELECT '=== RLS 정책 (없어야 정상) ===' AS section;
SELECT tablename, policyname, cmd
FROM pg_policies
WHERE tablename IN ('email_log', 'email_unsubscribes')
ORDER BY tablename, policyname;

SELECT '=== 인덱스 ===' AS section;
SELECT indexname, tablename
FROM pg_indexes
WHERE tablename IN ('email_log', 'email_unsubscribes')
ORDER BY tablename, indexname;
