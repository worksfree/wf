-- ══════════════════════════════════════════════════════════════════
--  B2B 이메일 DB — Supabase 초기화 SQL
--  Supabase 대시보드 → SQL Editor에서 실행
-- ══════════════════════════════════════════════════════════════════

-- 1. 기업 이메일 DB (핵심 테이블)
CREATE TABLE IF NOT EXISTS biz_contacts (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  corp_code     text UNIQUE,               -- DART 고유번호 (중복 방지)
  corp_name     text NOT NULL,
  ceo_nm        text,
  induty_code   text,                      -- KSIC 업종코드 (C=제조, F=건설, I=요식)
  induty_name   text,
  adres         text,
  hm_url        text,                      -- 홈페이지 URL (이메일 수집 대상)
  email         text,                      -- 수집된 이메일
  email_source  text DEFAULT 'homepage',   -- 'homepage' | 'contact-page' | 'manual'
  email_status  text DEFAULT 'active',     -- 'active' | 'bounced' | 'unsubscribed'
  scrape_status text DEFAULT 'pending',    -- 'pending' | 'done' | 'no_url' | 'no_email' | 'error'
  notes         text,
  created_at    timestamptz DEFAULT now(),
  updated_at    timestamptz DEFAULT now()
);

-- 2. 발송 이력 (월별 로테이션 추적)
CREATE TABLE IF NOT EXISTS biz_send_log (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  contact_id    uuid REFERENCES biz_contacts(id) ON DELETE SET NULL,
  email         text NOT NULL,
  corp_name     text,
  flyer_key     text NOT NULL,             -- 전단지 식별자 (flyer-ceo 등)
  flyer_name    text,
  batch_month   text NOT NULL,             -- '2025-01' 형식 (월별 배치)
  resend_msg_id text,                      -- Resend API 반환 메시지 ID
  status        text DEFAULT 'sent',       -- 'sent' | 'bounced' | 'error'
  sent_at       timestamptz DEFAULT now()
);

-- ── 인덱스 ──────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_biz_contacts_email_status  ON biz_contacts(email_status);
CREATE INDEX IF NOT EXISTS idx_biz_contacts_scrape_status ON biz_contacts(scrape_status);
CREATE INDEX IF NOT EXISTS idx_biz_contacts_induty        ON biz_contacts(induty_code);
CREATE INDEX IF NOT EXISTS idx_biz_send_log_month         ON biz_send_log(batch_month);
CREATE INDEX IF NOT EXISTS idx_biz_send_log_email         ON biz_send_log(email);

-- ── RLS (Row Level Security) ─────────────────────────────────────
-- 모든 접근은 CF Worker의 service_role 키를 통해 이루어짐 (RLS 우회)
-- anon 키로는 접근 불가 (보안)
ALTER TABLE biz_contacts ENABLE ROW LEVEL SECURITY;
ALTER TABLE biz_send_log ENABLE ROW LEVEL SECURITY;

-- 확인
SELECT 'biz_contacts' AS table_name, count(*) FROM biz_contacts
UNION ALL
SELECT 'biz_send_log', count(*) FROM biz_send_log;
