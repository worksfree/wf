-- ═══════════════════════════════════════════════════════════════════
-- add_campaign_indexes.sql
-- 이메일 캠페인 쿼리 성능 최적화 인덱스
--
-- 실행 전: 아래 STEP 1 쿼리로 현재 인덱스 먼저 확인
-- 실행 방법: Supabase → SQL Editor → 붙여넣기 → Run
-- 멱등성: IF NOT EXISTS → 반복 실행 안전
-- ═══════════════════════════════════════════════════════════════════


-- ══════════════════════════════════════════════════════════════════════
-- STEP 1: 현재 인덱스 현황 확인 (실행 후 결과 검토)
-- ══════════════════════════════════════════════════════════════════════
SELECT
  t.relname                                    AS 테이블,
  i.relname                                    AS 인덱스명,
  ix.indisunique                               AS 유니크,
  ix.indisprimary                              AS PK,
  array_to_string(array_agg(a.attname), ', ') AS 컬럼목록
FROM pg_class t
JOIN pg_index ix    ON t.oid = ix.indrelid
JOIN pg_class i     ON i.oid = ix.indexrelid
JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = ANY(ix.indkey)
WHERE t.relname IN ('biz_contacts', 'email_log', 'email_unsubscribes')
  AND t.relkind = 'r'
GROUP BY t.relname, i.relname, ix.indisunique, ix.indisprimary
ORDER BY t.relname, ix.indisprimary DESC, i.relname;


-- ══════════════════════════════════════════════════════════════════════
-- STEP 2: 테이블별 행 수 확인
-- ══════════════════════════════════════════════════════════════════════
SELECT
  relname   AS 테이블,
  n_live_tup AS 행수_추정,
  n_dead_tup AS 죽은행수
FROM pg_stat_user_tables
WHERE relname IN ('biz_contacts', 'email_log', 'email_unsubscribes')
ORDER BY n_live_tup DESC;


-- ══════════════════════════════════════════════════════════════════════
-- STEP 3: 누락 인덱스 생성
-- 대상 쿼리 패턴:
--   get_campaign_pending: WHERE email_status='active' AND email!=''
--   get_campaign_list:    LEFT JOIN ON lower(bc.email)=lower(el.recipient_email)
--   get_campaign_list:    LEFT JOIN ON lower(bc.email)=eu.email
-- ══════════════════════════════════════════════════════════════════════

-- [1] biz_contacts.email_status 필터 (가장 빈번한 WHERE 조건)
CREATE INDEX IF NOT EXISTS idx_biz_contacts_email_status
  ON public.biz_contacts (email_status)
  WHERE email IS NOT NULL AND email != '';

-- [2] biz_contacts.email lower() JOIN 최적화
--     get_campaign_list의 LATERAL JOIN에서 lower(bc.email) 사용
CREATE INDEX IF NOT EXISTS idx_biz_contacts_email_lower
  ON public.biz_contacts (lower(email))
  WHERE email_status = 'active' AND email IS NOT NULL AND email != '';

-- [3] biz_contacts.created_at — get_campaign_pending ORDER BY created_at ASC
CREATE INDEX IF NOT EXISTS idx_biz_contacts_created_at
  ON public.biz_contacts (created_at ASC)
  WHERE email_status = 'active' AND email IS NOT NULL AND email != '';

-- [4] email_log.recipient_email + status — NOT EXISTS 서브쿼리 핵심 인덱스
--     이것이 없으면 매 연락처마다 email_log 풀스캔 발생 (가장 중요)
CREATE INDEX IF NOT EXISTS idx_email_log_recipient_status
  ON public.email_log (recipient_email, status);

-- [5] email_log.sent_at — get_campaign_list LATERAL의 ORDER BY sent_at DESC
CREATE INDEX IF NOT EXISTS idx_email_log_sent_at
  ON public.email_log (recipient_email, sent_at DESC)
  WHERE status = 'sent';

-- [6] email_unsubscribes.email — NOT EXISTS 서브쿼리
CREATE UNIQUE INDEX IF NOT EXISTS idx_email_unsubscribes_email
  ON public.email_unsubscribes (email);


-- ══════════════════════════════════════════════════════════════════════
-- STEP 4: 핵심 쿼리 실행 계획 확인 (인덱스 적용 여부 검증)
-- ══════════════════════════════════════════════════════════════════════

-- pending 조회 실행 계획 (Seq Scan이 없어야 함)
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT bc.id, bc.corp_name, bc.ceo_nm, bc.email
FROM public.biz_contacts bc
WHERE bc.email_status = 'active'
  AND bc.email IS NOT NULL AND bc.email != ''
  AND NOT EXISTS (
    SELECT 1 FROM public.email_log el
    WHERE el.recipient_email = lower(bc.email) AND el.status = 'sent'
  )
  AND NOT EXISTS (
    SELECT 1 FROM public.email_unsubscribes eu
    WHERE eu.email = lower(bc.email)
  )
ORDER BY bc.created_at ASC
LIMIT 100;
