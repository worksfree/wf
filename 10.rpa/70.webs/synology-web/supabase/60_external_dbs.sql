-- ═══════════════════════════════════════════════════════════════════
-- 60_external_dbs.sql
-- WorksFree Hub — [6단계] 외부 서비스 전용 DB 스키마
--
-- 실행 순서: 6/7  (50_views.sql 이후)
-- 다음 단계: 70_seed_dev.sql
--
-- 포함 내용:
--   [A] B2B 이메일 DB (biz-db Cloudflare Worker 전용)
--       - biz_contacts  : 기업 이메일 DB (DART·웹 스크래핑 수집)
--       - biz_send_log  : 마케팅 발송 이력 (월별 로테이션 추적)
--
--   [B] 잡코리아 채용 자동화
--       - jobkorea_proposals : 입사제안 발송 이력 (중복 방지)
--
-- 참고:
--   - biz_contacts / biz_send_log는 Worker service_role 키로 RLS 우회
--   - jobkorea_proposals는 Python 스크립트가 직접 삽입
-- ═══════════════════════════════════════════════════════════════════

-- ══════════════════════════════════════════════════════════════════════
-- A. B2B 이메일 DB
-- ══════════════════════════════════════════════════════════════════════

-- ── A-1. biz_contacts — 기업 이메일 DB ────────────────────────────────
CREATE TABLE IF NOT EXISTS biz_contacts (
  id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  corp_code     TEXT        UNIQUE,              -- DART 고유번호
  corp_name     TEXT        NOT NULL,
  ceo_nm        TEXT,
  induty_code   TEXT,                            -- KSIC 업종코드 (C=제조, I=요식...)
  induty_name   TEXT,
  adres         TEXT,
  hm_url        TEXT,
  email         TEXT,
  email_source  TEXT        DEFAULT 'homepage'
                CHECK (email_source IN ('homepage', 'contact-page', 'manual')),
  email_status  TEXT        DEFAULT 'active'
                CHECK (email_status IN ('active', 'bounced', 'unsubscribed')),
  scrape_status TEXT        DEFAULT 'pending'
                CHECK (scrape_status IN ('pending', 'done', 'no_url', 'no_email', 'error')),
  notes         TEXT,
  created_at    TIMESTAMPTZ DEFAULT NOW(),
  updated_at    TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS biz_contacts_corp_name_idx    ON biz_contacts (corp_name);
CREATE INDEX IF NOT EXISTS biz_contacts_email_idx        ON biz_contacts (email);
CREATE INDEX IF NOT EXISTS biz_contacts_email_status_idx ON biz_contacts (email_status);
CREATE INDEX IF NOT EXISTS biz_contacts_induty_name_idx  ON biz_contacts (induty_name);
CREATE INDEX IF NOT EXISTS biz_contacts_scrape_idx       ON biz_contacts (scrape_status);
CREATE INDEX IF NOT EXISTS biz_contacts_created_idx      ON biz_contacts (created_at DESC);

ALTER TABLE biz_contacts ENABLE ROW LEVEL SECURITY;


-- ── A-2. biz_send_log — 발송 이력 (월별 로테이션 추적) ────────────────
CREATE TABLE IF NOT EXISTS biz_send_log (
  id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  contact_id   UUID        REFERENCES biz_contacts(id) ON DELETE SET NULL,
  email        TEXT        NOT NULL,
  corp_name    TEXT,
  batch_month  TEXT        NOT NULL,             -- 'YYYY-MM' 형식
  sent_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS biz_send_log_email_month ON biz_send_log (email, batch_month);
CREATE INDEX IF NOT EXISTS biz_send_log_month_idx   ON biz_send_log (batch_month DESC);

ALTER TABLE biz_send_log ENABLE ROW LEVEL SECURITY;


-- ══════════════════════════════════════════════════════════════════════
-- B. 잡코리아 채용 자동화
-- ══════════════════════════════════════════════════════════════════════

-- ── B-1. jobkorea_proposals — 입사제안 발송 이력 ──────────────────────
CREATE TABLE IF NOT EXISTS jobkorea_proposals (
  id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  candidate_id TEXT        UNIQUE NOT NULL,      -- 잡코리아 후보자 고유 ID
  name         TEXT,
  career       TEXT,
  keyword      TEXT,
  status       TEXT        NOT NULL DEFAULT 'sent'
               CHECK (status IN ('sent', 'error', 'skipped')),
  sent_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  message_used TEXT,
  notes        TEXT
);

CREATE INDEX IF NOT EXISTS jobkorea_proposals_sent_at ON jobkorea_proposals (sent_at DESC);
CREATE INDEX IF NOT EXISTS jobkorea_proposals_keyword ON jobkorea_proposals (keyword);
CREATE INDEX IF NOT EXISTS jobkorea_proposals_status  ON jobkorea_proposals (status);

ALTER TABLE jobkorea_proposals ENABLE ROW LEVEL SECURITY;


-- ══════════════════════════════════════════════════════════════════════
-- 검증
-- ══════════════════════════════════════════════════════════════════════
SELECT table_name
FROM   information_schema.tables
WHERE  table_schema = 'public'
  AND  table_name   IN ('biz_contacts', 'biz_send_log', 'jobkorea_proposals')
ORDER  BY table_name;
