-- ============================================================
-- jobkorea_setup.sql
-- 잡코리아 입사제안 자동화 - Supabase 테이블 초기화
-- ============================================================

-- 1. 테이블 생성
CREATE TABLE IF NOT EXISTS jobkorea_proposals (
  id           uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  candidate_id text        UNIQUE NOT NULL,   -- 잡코리아 후보자 고유 ID (URL에서 추출)
  name         text,
  career       text,                          -- 경력 요약
  keyword      text,                          -- 검색에 사용한 키워드
  status       text        NOT NULL DEFAULT 'sent',  -- 'sent' | 'error' | 'skipped'
  sent_at      timestamptz NOT NULL DEFAULT now(),
  message_used text,                          -- 실제 발송된 메시지 전문
  notes        text                           -- 기타 메모 (오류 메시지 등)
);

-- 2. 인덱스
CREATE INDEX IF NOT EXISTS idx_jobkorea_proposals_sent_at
  ON jobkorea_proposals (sent_at DESC);

CREATE INDEX IF NOT EXISTS idx_jobkorea_proposals_keyword
  ON jobkorea_proposals (keyword);

CREATE INDEX IF NOT EXISTS idx_jobkorea_proposals_status
  ON jobkorea_proposals (status);

-- 3. RLS 활성화
ALTER TABLE jobkorea_proposals ENABLE ROW LEVEL SECURITY;

-- 4. anon 읽기 허용 (Hub UI에서 조회)
CREATE POLICY "anon_read_proposals"
  ON jobkorea_proposals
  FOR SELECT
  TO anon
  USING (true);

-- 5. service_role 쓰기 허용 (Python 스크립트만 사용)
CREATE POLICY "service_write_proposals"
  ON jobkorea_proposals
  FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

-- 6. 통계용 뷰: 주간/월간 요약
CREATE OR REPLACE VIEW jobkorea_stats AS
SELECT
  COUNT(*) FILTER (WHERE status = 'sent')                                         AS total_sent,
  COUNT(*) FILTER (WHERE status = 'error')                                        AS total_error,
  COUNT(*) FILTER (WHERE status = 'skipped')                                      AS total_skipped,
  COUNT(*) FILTER (WHERE status = 'sent'
                     AND sent_at >= date_trunc('week',  now()))                   AS this_week,
  COUNT(*) FILTER (WHERE status = 'sent'
                     AND sent_at >= date_trunc('month', now()))                   AS this_month,
  MAX(sent_at)                                                                     AS last_sent_at
FROM jobkorea_proposals;

-- 7. anon 뷰 읽기 허용
GRANT SELECT ON jobkorea_stats TO anon;
