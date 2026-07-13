-- ═══════════════════════════════════════════════════════════════════
-- email_campaign_setup.sql
-- WorksFree Hub — 어드민 이메일 캠페인 RPC 함수
--
-- 전제 조건:
--   1. complete_db_setup.sql 실행 완료
--      (email_log, email_unsubscribes 테이블 존재)
--   2. bizdb_setup.sql 실행 완료
--      (biz_contacts 테이블 존재)
--
-- 실행 방법: Supabase → SQL Editor → 전체 붙여넣기 → Run
-- 멱등성: OR REPLACE → 반복 실행 안전
-- ═══════════════════════════════════════════════════════════════════


-- ══════════════════════════════════════════════════════════════════════
-- 1. get_campaign_stats() — 캠페인 통계 조회
--    Worker에서 GET /db-stats 호출 시 사용
-- ══════════════════════════════════════════════════════════════════════
CREATE OR REPLACE FUNCTION public.get_campaign_stats()
RETURNS JSON
LANGUAGE SQL SECURITY DEFINER
SET search_path = public AS $$
  SELECT json_build_object(
    'total', (
      SELECT count(*)
      FROM public.biz_contacts
      WHERE email IS NOT NULL AND email != ''
    ),
    'active', (
      SELECT count(*)
      FROM public.biz_contacts
      WHERE email_status = 'active'
        AND email IS NOT NULL AND email != ''
    ),
    'sent', (
      SELECT count(DISTINCT recipient_email)
      FROM public.email_log
      WHERE status = 'sent'
    ),
    'unsubscribed', (
      SELECT count(*) FROM public.email_unsubscribes
    ),
    'pending', (
      SELECT count(*)
      FROM public.biz_contacts bc
      WHERE bc.email_status = 'active'
        AND bc.email IS NOT NULL AND bc.email != ''
        AND NOT EXISTS (
          SELECT 1 FROM public.email_log el
          WHERE el.recipient_email = lower(bc.email)
            AND el.status = 'sent'
        )
        AND NOT EXISTS (
          SELECT 1 FROM public.email_unsubscribes eu
          WHERE eu.email = lower(bc.email)
        )
    )
  );
$$;

GRANT EXECUTE ON FUNCTION public.get_campaign_stats() TO authenticated, anon;


-- ══════════════════════════════════════════════════════════════════════
-- 2. get_campaign_pending(p_limit) — 다음 발송 대상 배치 반환
--    Worker에서 GET /db-pending 호출 시 사용
--    이미 발송된 이메일(email_log)과 수신거부(email_unsubscribes) 자동 제외
--    biz_contacts.created_at ASC 순서로 반환 (가장 오래된 것부터)
-- ══════════════════════════════════════════════════════════════════════
CREATE OR REPLACE FUNCTION public.get_campaign_pending(p_limit INT DEFAULT 100)
RETURNS TABLE(contact_id UUID, corp_name TEXT, ceo_nm TEXT, email TEXT)
LANGUAGE SQL SECURITY DEFINER
SET search_path = public AS $$
  SELECT bc.id, bc.corp_name, bc.ceo_nm, bc.email
  FROM public.biz_contacts bc
  WHERE bc.email_status = 'active'
    AND bc.email IS NOT NULL AND bc.email != ''
    AND NOT EXISTS (
      SELECT 1 FROM public.email_log el
      WHERE el.recipient_email = lower(bc.email)
        AND el.status = 'sent'
    )
    AND NOT EXISTS (
      SELECT 1 FROM public.email_unsubscribes eu
      WHERE eu.email = lower(bc.email)
    )
  ORDER BY bc.created_at ASC
  LIMIT p_limit;
$$;

GRANT EXECUTE ON FUNCTION public.get_campaign_pending(INT) TO authenticated, anon;


-- ══════════════════════════════════════════════════════════════════════
-- 3. get_campaign_list() — 전체 연락처 + 발송 이력 JOIN (목록 조회용)
--    Worker에서 GET /db-list 호출 시 사용
--    biz_contacts LEFT JOIN email_log (최신 sent 기준) + email_unsubscribes
--    반환: { total: N, rows: [{corp_name, ceo_nm, email, email_status,
--             send_status: sent|pending|unsubscribed,
--             sent_at_kst, subject, flyer_name}, ...] }
-- ══════════════════════════════════════════════════════════════════════
CREATE OR REPLACE FUNCTION public.get_campaign_list()
RETURNS JSON
LANGUAGE SQL SECURITY DEFINER
SET search_path = public AS $$
  SELECT json_build_object(
    'total', (
      SELECT count(*) FROM public.biz_contacts
      WHERE email_status = 'active' AND email IS NOT NULL AND email != ''
    ),
    'rows', COALESCE((
      SELECT json_agg(row_to_json(t))
      FROM (
        SELECT
          bc.corp_name,
          bc.ceo_nm,
          bc.email,
          bc.email_status,
          CASE
            WHEN eu.email IS NOT NULL THEN 'unsubscribed'
            WHEN el.sent_at IS NOT NULL THEN 'sent'
            ELSE 'pending'
          END AS send_status,
          to_char(el.sent_at AT TIME ZONE 'Asia/Seoul', 'YYYY-MM-DD HH24:MI') AS sent_at_kst,
          el.subject,
          el.flyer_name
        FROM public.biz_contacts bc
        LEFT JOIN LATERAL (
          SELECT sent_at, subject, flyer_name
          FROM public.email_log
          WHERE recipient_email = lower(bc.email)
            AND status = 'sent'
          ORDER BY sent_at DESCㅣㅑㄴ@3412
          
          LIMIT 1
        ) el ON true
        LEFT JOIN public.email_unsubscribes eu
          ON eu.email = lower(bc.email)
        WHERE bc.email_status = 'active'
          AND bc.email IS NOT NULL AND bc.email != ''
        ORDER BY
          -- 미발송(0) 먼저, 발송완료(1), 수신거부(2)
          CASE
            WHEN eu.email IS NOT NULL THEN 2
            WHEN el.sent_at IS NOT NULL THEN 1
            ELSE 0
          END ASC,
          bc.corp_name ASC
      ) t
    ), '[]'::json)
  );
$$;

GRANT EXECUTE ON FUNCTION public.get_campaign_list() TO authenticated, anon;


-- ══════════════════════════════════════════════════════════════════════
-- 검증
-- ══════════════════════════════════════════════════════════════════════
SELECT get_campaign_stats();
