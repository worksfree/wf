-- ═══════════════════════════════════════════════════════════════════
-- campaign_v2_setup.sql
-- WorksFree Hub — 이메일 캠페인 v2
--   테이블 3개: campaigns · campaign_emails · campaign_runs
--   RPC  6개: activate_campaign · get_campaign_batch
--             complete_campaign_batch · get_campaigns_list
--             get_campaign_runs · get_campaign_stats_v2
--
-- 전제 조건:
--   1. complete_db_setup.sql  (email_log, email_unsubscribes)
--   2. bizdb_setup.sql        (biz_contacts)
--
-- 실행: Supabase → SQL Editor → 전체 붙여넣기 → Run
-- 멱등성: IF NOT EXISTS, OR REPLACE → 반복 실행 안전
-- ═══════════════════════════════════════════════════════════════════


-- ══════════════════════════════════════════════════════════════════════
-- 1. campaigns — 캠페인 원장
-- ══════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS public.campaigns (
  id           uuid         DEFAULT gen_random_uuid() PRIMARY KEY,
  env          text         NOT NULL DEFAULT 'portal'
               CHECK (env IN ('dev','test','staging','portal')),
  name         text         NOT NULL,
  subject      text         NOT NULL,
  flyer_src    text,
  flyer_name   text,
  html_body    text,                    -- 미리 렌더링된 이메일 HTML (캠페인 저장 시 확정)
  status       text         NOT NULL DEFAULT 'draft'
               CHECK (status IN ('draft','active','paused','completed','cancelled')),
  target_count int          NOT NULL DEFAULT 0,
  sent_count   int          NOT NULL DEFAULT 0,
  daily_limit  int          NOT NULL DEFAULT 100,
  created_by   uuid         REFERENCES auth.users ON DELETE SET NULL,
  created_at   timestamptz  NOT NULL DEFAULT now(),
  activated_at timestamptz,
  completed_at timestamptz
);

ALTER TABLE public.campaigns ENABLE ROW LEVEL SECURITY;
-- Worker는 service_role 키로 RLS를 우회하므로 별도 정책 불필요

CREATE INDEX IF NOT EXISTS campaigns_status_idx    ON public.campaigns (status);
CREATE INDEX IF NOT EXISTS campaigns_created_idx   ON public.campaigns (created_at DESC);


-- ══════════════════════════════════════════════════════════════════════
-- 2. campaign_emails — 캠페인별 발송 대상 + 상태 (캠페인 활성화 시 스냅샷)
-- ══════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS public.campaign_emails (
  id          bigint       GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  campaign_id uuid         NOT NULL REFERENCES public.campaigns ON DELETE CASCADE,
  contact_id  uuid         REFERENCES public.biz_contacts ON DELETE SET NULL,
  email       text         NOT NULL,
  corp_name   text,
  ceo_nm      text,
  status      text         NOT NULL DEFAULT 'pending'
              CHECK (status IN ('pending','sent','failed','unsubscribed')),
  sent_at     timestamptz,
  error_msg   text,
  created_at  timestamptz  NOT NULL DEFAULT now()
);

ALTER TABLE public.campaign_emails ENABLE ROW LEVEL SECURITY;

CREATE INDEX IF NOT EXISTS ce_campaign_status_idx ON public.campaign_emails (campaign_id, status);
CREATE INDEX IF NOT EXISTS ce_campaign_id_asc     ON public.campaign_emails (campaign_id, id ASC);
CREATE INDEX IF NOT EXISTS ce_email_idx           ON public.campaign_emails (email);


-- ══════════════════════════════════════════════════════════════════════
-- 3. campaign_runs — 일별 배치 실행 이력
-- ══════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS public.campaign_runs (
  id            bigint       GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  campaign_id   uuid         NOT NULL REFERENCES public.campaigns ON DELETE CASCADE,
  run_date      date         NOT NULL,
  sent_count    int          NOT NULL DEFAULT 0,
  skipped_count int          NOT NULL DEFAULT 0,  -- 수신거부·실패
  error_msg     text,
  triggered_by  text         NOT NULL DEFAULT 'cron'
                CHECK (triggered_by IN ('cron','manual')),
  started_at    timestamptz  NOT NULL DEFAULT now(),
  finished_at   timestamptz
);

ALTER TABLE public.campaign_runs ENABLE ROW LEVEL SECURITY;

CREATE INDEX IF NOT EXISTS cr_campaign_date_idx ON public.campaign_runs (campaign_id, run_date DESC);


-- ══════════════════════════════════════════════════════════════════════
-- 4. activate_campaign(p_campaign_id)
--    draft → active, biz_contacts에서 campaign_emails 스냅샷 생성
-- ══════════════════════════════════════════════════════════════════════
CREATE OR REPLACE FUNCTION public.activate_campaign(p_campaign_id uuid)
RETURNS json
LANGUAGE plpgsql SECURITY DEFINER
SET search_path = public AS $$
DECLARE
  v_count int;
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM campaigns WHERE id = p_campaign_id AND status = 'draft'
  ) THEN
    RETURN json_build_object('error', '활성화 불가 — draft 상태인 캠페인만 활성화할 수 있습니다.');
  END IF;

  -- 수신거부 제외, 활성 연락처만 복사
  INSERT INTO campaign_emails (campaign_id, contact_id, email, corp_name, ceo_nm)
  SELECT
    p_campaign_id,
    bc.id,
    lower(bc.email),
    bc.corp_name,
    bc.ceo_nm
  FROM biz_contacts bc
  WHERE bc.email_status = 'active'
    AND bc.email IS NOT NULL AND bc.email != ''
    AND NOT EXISTS (
      SELECT 1 FROM email_unsubscribes eu WHERE eu.email = lower(bc.email)
    );

  GET DIAGNOSTICS v_count = ROW_COUNT;

  UPDATE campaigns
  SET
    status       = 'active',
    activated_at = NOW(),
    target_count = v_count
  WHERE id = p_campaign_id;

  RETURN json_build_object('success', true, 'target_count', v_count);
END;
$$;

GRANT EXECUTE ON FUNCTION public.activate_campaign(uuid) TO authenticated, anon;


-- ══════════════════════════════════════════════════════════════════════
-- 5. get_campaign_batch(p_campaign_id, p_limit)
--    다음 발송 배치 반환 (id 오름차순, pending만)
-- ══════════════════════════════════════════════════════════════════════
CREATE OR REPLACE FUNCTION public.get_campaign_batch(
  p_campaign_id uuid,
  p_limit       int DEFAULT 100
)
RETURNS TABLE (id bigint, email text, corp_name text, ceo_nm text)
LANGUAGE SQL SECURITY DEFINER
SET search_path = public AS $$
  SELECT id, email, corp_name, ceo_nm
  FROM public.campaign_emails
  WHERE campaign_id = p_campaign_id
    AND status = 'pending'
  ORDER BY id ASC
  LIMIT p_limit;
$$;

GRANT EXECUTE ON FUNCTION public.get_campaign_batch(uuid, int) TO authenticated, anon;


-- ══════════════════════════════════════════════════════════════════════
-- 6. complete_campaign_batch(p_campaign_id, p_sent_ids, p_failed_ids,
--                             p_run_date, p_triggered_by)
--    배치 완료 후 한 번에: campaign_emails 상태 갱신 + sent_count 업데이트
--    + campaign_runs 기록 + 완료 여부 체크
-- ══════════════════════════════════════════════════════════════════════
CREATE OR REPLACE FUNCTION public.complete_campaign_batch(
  p_campaign_id  uuid,
  p_sent_ids     bigint[],
  p_failed_ids   bigint[],
  p_run_date     date,
  p_triggered_by text DEFAULT 'cron'
)
RETURNS json
LANGUAGE plpgsql SECURITY DEFINER
SET search_path = public AS $$
DECLARE
  v_sent_count   int := COALESCE(array_length(p_sent_ids,  1), 0);
  v_failed_count int := COALESCE(array_length(p_failed_ids, 1), 0);
  v_pending      int;
  v_total_sent   int;
BEGIN
  IF v_sent_count > 0 THEN
    UPDATE campaign_emails
    SET status = 'sent', sent_at = NOW()
    WHERE id = ANY(p_sent_ids) AND campaign_id = p_campaign_id;
  END IF;

  IF v_failed_count > 0 THEN
    UPDATE campaign_emails
    SET status = 'failed'
    WHERE id = ANY(p_failed_ids) AND campaign_id = p_campaign_id;
  END IF;

  UPDATE campaigns
  SET sent_count = sent_count + v_sent_count
  WHERE id = p_campaign_id;

  -- 잔여 pending 확인
  SELECT count(*) INTO v_pending
  FROM campaign_emails
  WHERE campaign_id = p_campaign_id AND status = 'pending';

  IF v_pending = 0 THEN
    UPDATE campaigns
    SET status = 'completed', completed_at = NOW()
    WHERE id = p_campaign_id AND status = 'active';
  END IF;

  INSERT INTO campaign_runs
    (campaign_id, run_date, sent_count, skipped_count, triggered_by, finished_at)
  VALUES
    (p_campaign_id, p_run_date, v_sent_count, v_failed_count, p_triggered_by, NOW());

  SELECT sent_count INTO v_total_sent FROM campaigns WHERE id = p_campaign_id;

  RETURN json_build_object(
    'sent',                v_sent_count,
    'failed',              v_failed_count,
    'remaining_pending',   v_pending,
    'campaign_sent_total', v_total_sent,
    'completed',           v_pending = 0
  );
END;
$$;

GRANT EXECUTE ON FUNCTION public.complete_campaign_batch(uuid, bigint[], bigint[], date, text) TO authenticated, anon;


-- ══════════════════════════════════════════════════════════════════════
-- 7. get_campaigns_list()
--    전체 캠페인 목록 + 집계 (어드민 UI용)
-- ══════════════════════════════════════════════════════════════════════
CREATE OR REPLACE FUNCTION public.get_campaigns_list()
RETURNS json
LANGUAGE SQL SECURITY DEFINER
SET search_path = public AS $$
  SELECT COALESCE(
    json_agg(row_to_json(c) ORDER BY c.created_at DESC),
    '[]'::json
  )
  FROM (
    SELECT
      c.id, c.name, c.subject, c.flyer_src, c.flyer_name,
      c.status, c.env,
      c.target_count, c.sent_count, c.daily_limit,
      c.created_at, c.activated_at, c.completed_at,
      (SELECT count(*)
       FROM campaign_emails ce
       WHERE ce.campaign_id = c.id AND ce.status = 'pending') AS pending_count,
      (SELECT max(run_date)
       FROM campaign_runs cr
       WHERE cr.campaign_id = c.id)  AS last_run_date
    FROM campaigns c
  ) c;
$$;

GRANT EXECUTE ON FUNCTION public.get_campaigns_list() TO authenticated, anon;


-- ══════════════════════════════════════════════════════════════════════
-- 8. get_campaign_runs(p_campaign_id)
--    특정 캠페인 실행 이력 (최근 30일)
-- ══════════════════════════════════════════════════════════════════════
CREATE OR REPLACE FUNCTION public.get_campaign_runs(p_campaign_id uuid)
RETURNS json
LANGUAGE SQL SECURITY DEFINER
SET search_path = public AS $$
  SELECT COALESCE(
    json_agg(row_to_json(r) ORDER BY r.run_date DESC),
    '[]'::json
  )
  FROM (
    SELECT *
    FROM campaign_runs
    WHERE campaign_id = p_campaign_id
    ORDER BY run_date DESC
    LIMIT 30
  ) r;
$$;

GRANT EXECUTE ON FUNCTION public.get_campaign_runs(uuid) TO authenticated, anon;


-- ══════════════════════════════════════════════════════════════════════
-- 9. get_campaign_stats_v2()
--    전체 현황 통계 (대시보드 카드용)
-- ══════════════════════════════════════════════════════════════════════
CREATE OR REPLACE FUNCTION public.get_campaign_stats_v2()
RETURNS json
LANGUAGE SQL SECURITY DEFINER
SET search_path = public AS $$
  SELECT json_build_object(
    'total_contacts', (
      SELECT count(*)
      FROM biz_contacts
      WHERE email_status = 'active' AND email IS NOT NULL AND email != ''
    ),
    'unsubscribed', (
      SELECT count(*) FROM email_unsubscribes
    ),
    'campaigns_total',  (SELECT count(*) FROM campaigns),
    'campaigns_active', (SELECT count(*) FROM campaigns WHERE status = 'active'),
    'campaigns_draft',  (SELECT count(*) FROM campaigns WHERE status = 'draft'),
    'emails_sent_total',(SELECT COALESCE(sum(sent_count), 0) FROM campaigns)
  );
$$;

GRANT EXECUTE ON FUNCTION public.get_campaign_stats_v2() TO authenticated, anon;


-- ══════════════════════════════════════════════════════════════════════
-- 검증
-- ══════════════════════════════════════════════════════════════════════
SELECT get_campaigns_list();
SELECT get_campaign_stats_v2();
