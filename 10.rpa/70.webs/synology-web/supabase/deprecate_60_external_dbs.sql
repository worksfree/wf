-- ═══════════════════════════════════════════════════════════════════
-- 60_external_dbs.sql
-- WorksFree Hub — [6단계] 외부 서비스 전용 DB 스키마
--
-- 실행 순서: 6/7  (50_views.sql 이후)
-- 다음 단계: 70_seed_dev.sql
--
-- 포함 내용:
--   [A] B2B 이메일 DB (biz-db Cloudflare Worker 전용)
--       - biz_contacts      : 기업 이메일 DB (DART·웹 스크래핑 수집)
--       - biz_send_log      : 마케팅 발송 이력 (Resend 추적 포함)
--       - biz_send_batches  : 발송 배치 관리
--
--   [B] 잡코리아 채용 자동화
--       - jobkorea_proposals : 입사제안 발송 이력 (중복 방지)
--       - jobkorea_stats     : 통계 뷰
--
--   [C] 사이트 설정
--       - site_config        : 페이지 권한 관리 등 동적 설정
--
-- 참고:
--   - biz_contacts / biz_send_log는 Worker service_role 키로 RLS 우회
--   - jobkorea_proposals는 Python 스크립트가 service_role로 직접 삽입
--   - site_config는 anon 읽기 / admin만 쓰기
--
-- 멱등성: CREATE TABLE IF NOT EXISTS + ADD COLUMN IF NOT EXISTS
--         → 신규 DB · 기존 DB 모두 안전하게 실행 가능
-- ═══════════════════════════════════════════════════════════════════


-- ══════════════════════════════════════════════════════════════════════
-- A. B2B 이메일 DB
-- ══════════════════════════════════════════════════════════════════════

-- ── A-1. biz_contacts — 기업 이메일 DB ────────────────────────────────
CREATE TABLE IF NOT EXISTS public.biz_contacts (
  id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  corp_code     TEXT        UNIQUE,              -- DART 고유번호
  corp_name     TEXT        NOT NULL,
  ceo_nm        TEXT,
  induty_code   TEXT,                            -- KSIC 업종코드
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

-- email_source CHECK 최신화 (기존 DB에 구버전 제약이 있을 때 자동 갱신)
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


-- ── A-2. biz_send_log — 발송 이력 ─────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.biz_send_log (
  id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  contact_id  UUID        REFERENCES public.biz_contacts(id) ON DELETE SET NULL,
  email       TEXT        NOT NULL,
  corp_name   TEXT,
  batch_month TEXT        NOT NULL,             -- 'YYYY-MM' 형식
  sent_at     TIMESTAMPTZ DEFAULT NOW(),
  status      TEXT        DEFAULT 'sent'
              CHECK (status IN ('sent','failed','delivered','opened','clicked','bounced','complained')),
  resend_id   TEXT,        -- Resend API 반환 ID
  flyer_name  TEXT,        -- 발송 전단지명
  subject     TEXT,        -- 이메일 제목
  opened_at   TIMESTAMPTZ, -- Resend webhook: email.opened
  clicked_at  TIMESTAMPTZ, -- Resend webhook: email.clicked
  bounced_at  TIMESTAMPTZ  -- Resend webhook: email.bounced
);

-- 기존 DB에 컬럼이 없을 때 추가 (멱등성)
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


-- ── A-3. biz_send_batches — 발송 배치 관리 ────────────────────────────
CREATE TABLE IF NOT EXISTS public.biz_send_batches (
  id             UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  batch_name     TEXT,                          -- "2026-06 제조업 1차"
  batch_month    TEXT        NOT NULL,          -- 'YYYY-MM'
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


-- ══════════════════════════════════════════════════════════════════════
-- B. 잡코리아 채용 자동화
-- ══════════════════════════════════════════════════════════════════════

-- ── B-1. jobkorea_proposals — 입사제안 발송 이력 ──────────────────────
CREATE TABLE IF NOT EXISTS public.jobkorea_proposals (
  id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  candidate_id TEXT        UNIQUE NOT NULL,      -- 잡코리아 후보자 고유 ID (URL에서 추출)
  name         TEXT,
  career       TEXT,                             -- 경력 요약
  keyword      TEXT,                             -- 검색 키워드
  status       TEXT        NOT NULL DEFAULT 'sent'
               CHECK (status IN ('sent','error','skipped')),
  sent_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  message_used TEXT,                             -- 실제 발송된 메시지 전문
  notes        TEXT
);

CREATE INDEX IF NOT EXISTS jobkorea_proposals_sent_at ON public.jobkorea_proposals (sent_at DESC);
CREATE INDEX IF NOT EXISTS jobkorea_proposals_keyword ON public.jobkorea_proposals (keyword);
CREATE INDEX IF NOT EXISTS jobkorea_proposals_status  ON public.jobkorea_proposals (status);

ALTER TABLE public.jobkorea_proposals ENABLE ROW LEVEL SECURITY;

-- anon 읽기 (Hub 관리자 페이지), service_role 전체 (Python 스크립트)
DROP POLICY IF EXISTS "jp_anon_read"     ON public.jobkorea_proposals;
DROP POLICY IF EXISTS "jp_service_write" ON public.jobkorea_proposals;
CREATE POLICY "jp_anon_read"
  ON public.jobkorea_proposals FOR SELECT USING (true);
CREATE POLICY "jp_service_write"
  ON public.jobkorea_proposals FOR ALL USING (true) WITH CHECK (true);


-- ── B-2. jobkorea_stats — 통계 뷰 ─────────────────────────────────────
CREATE OR REPLACE VIEW public.jobkorea_stats AS
SELECT
  COUNT(*) FILTER (WHERE status = 'sent')                                     AS total_sent,
  COUNT(*) FILTER (WHERE status = 'error')                                    AS total_error,
  COUNT(*) FILTER (WHERE status = 'skipped')                                  AS total_skipped,
  COUNT(*) FILTER (WHERE status = 'sent'
                     AND sent_at >= date_trunc('week', NOW()))                AS this_week,
  COUNT(*) FILTER (WHERE status = 'sent'
                     AND to_char(sent_at AT TIME ZONE 'Asia/Seoul','YYYY-MM')
                       = to_char(NOW()     AT TIME ZONE 'Asia/Seoul','YYYY-MM')) AS this_month,
  MAX(sent_at) FILTER (WHERE status = 'sent')                                  AS last_sent_at
FROM public.jobkorea_proposals;

GRANT SELECT ON public.jobkorea_stats TO anon;


-- ══════════════════════════════════════════════════════════════════════
-- C. 사이트 설정
-- ══════════════════════════════════════════════════════════════════════

-- ── C-1. site_config — 동적 설정 저장소 ──────────────────────────────
-- 현재 사용 키: 'page_access_rules' — 역할별 페이지 접근 레벨 관리
-- 레벨: full | blur | readonly | hidden
-- 관리 UI: admin/permissions/index.html
CREATE TABLE IF NOT EXISTS public.site_config (
  key        TEXT        PRIMARY KEY,
  value      JSONB       NOT NULL DEFAULT '{}',
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE public.site_config ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "site_config_read_all"    ON public.site_config;
DROP POLICY IF EXISTS "site_config_write_admin" ON public.site_config;

-- 읽기: 모든 사용자 (anon 포함 — Hub가 읽어야 함)
CREATE POLICY "site_config_read_all"
  ON public.site_config FOR SELECT USING (true);

-- 쓰기: admin 역할만
CREATE POLICY "site_config_write_admin"
  ON public.site_config FOR ALL
  USING (
    EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role = 'admin')
  );

-- 기본값 삽입 (이미 있으면 스킵)
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


-- ══════════════════════════════════════════════════════════════════════
-- 검증
-- ══════════════════════════════════════════════════════════════════════
SELECT table_name
FROM   information_schema.tables
WHERE  table_schema = 'public'
  AND  table_name IN (
    'biz_contacts', 'biz_send_log', 'biz_send_batches',
    'jobkorea_proposals', 'site_config'
  )
ORDER BY table_name;
