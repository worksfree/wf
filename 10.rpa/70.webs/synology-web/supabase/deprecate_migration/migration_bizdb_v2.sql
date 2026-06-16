-- ═══════════════════════════════════════════════════════════════════
-- migration_bizdb_v2.sql
-- WorksFree Hub — BizDB 스키마 확장 마이그레이션
--
-- 실행: Supabase 대시보드 → SQL Editor → 전체 붙여넣기 → Run
--
-- 변경 내용:
--   1. biz_contacts.email_source CHECK 제약 확장
--      ('csv', 'purchased', 'dart' 추가)
--   2. biz_send_log 컬럼 추가
--      (status, resend_id, flyer_name, subject, opened_at, clicked_at, bounced_at)
--   3. biz_send_batches 신규 테이블 생성
-- ═══════════════════════════════════════════════════════════════════

-- ────────────────────────────────────────────────────────────────────
-- 1. biz_contacts.email_source — CHECK 제약 확장
--    기존: ('homepage', 'contact-page', 'manual')
--    신규: + ('csv', 'purchased', 'dart')
-- ────────────────────────────────────────────────────────────────────
ALTER TABLE biz_contacts
  DROP CONSTRAINT IF EXISTS biz_contacts_email_source_check;

ALTER TABLE biz_contacts
  ADD CONSTRAINT biz_contacts_email_source_check
  CHECK (email_source IN ('homepage', 'contact-page', 'manual', 'csv', 'purchased', 'dart'));

-- ────────────────────────────────────────────────────────────────────
-- 2. biz_send_log — 발송 추적 컬럼 추가
-- ────────────────────────────────────────────────────────────────────
ALTER TABLE biz_send_log
  ADD COLUMN IF NOT EXISTS status      TEXT    DEFAULT 'sent'
    CHECK (status IN ('sent','failed','delivered','opened','clicked','bounced','complained')),
  ADD COLUMN IF NOT EXISTS resend_id   TEXT,        -- Resend API 반환 ID (이벤트 매칭용)
  ADD COLUMN IF NOT EXISTS flyer_name  TEXT,        -- 발송 전단지 식별자
  ADD COLUMN IF NOT EXISTS subject     TEXT,        -- 이메일 제목
  ADD COLUMN IF NOT EXISTS opened_at   TIMESTAMPTZ, -- Resend webhook: email.opened
  ADD COLUMN IF NOT EXISTS clicked_at  TIMESTAMPTZ, -- Resend webhook: email.clicked
  ADD COLUMN IF NOT EXISTS bounced_at  TIMESTAMPTZ; -- Resend webhook: email.bounced

CREATE INDEX IF NOT EXISTS biz_send_log_resend_id ON biz_send_log (resend_id) WHERE resend_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS biz_send_log_status    ON biz_send_log (status);

-- ────────────────────────────────────────────────────────────────────
-- 3. biz_send_batches — 발송 배치 관리 (신규)
-- ────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS biz_send_batches (
  id             UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  batch_name     TEXT,                         -- "2026-06 제조업 1차" 등
  batch_month    TEXT        NOT NULL,         -- YYYY-MM
  flyer_name     TEXT,
  subject        TEXT,
  filter_induty  TEXT,                         -- 발송 시 업종 조건
  total_targets  INT         DEFAULT 0,
  total_sent     INT         DEFAULT 0,
  total_failed   INT         DEFAULT 0,
  total_opened   INT         DEFAULT 0,
  created_at     TIMESTAMPTZ DEFAULT NOW(),
  completed_at   TIMESTAMPTZ,
  notes          TEXT
);

CREATE INDEX IF NOT EXISTS biz_send_batches_month ON biz_send_batches (batch_month DESC);

ALTER TABLE biz_send_batches ENABLE ROW LEVEL SECURITY;

-- Worker service_role 키로 RLS 우회 (기존 패턴과 동일)
-- biz_send_batches RLS 정책: 접근 없음 (Worker가 service_role로 직접 접근)

-- ────────────────────────────────────────────────────────────────────
-- 검증
-- ────────────────────────────────────────────────────────────────────
SELECT
  table_name,
  column_name,
  data_type,
  column_default
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name IN ('biz_contacts', 'biz_send_log', 'biz_send_batches')
ORDER BY table_name, ordinal_position;
