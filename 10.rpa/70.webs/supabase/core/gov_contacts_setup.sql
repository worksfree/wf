-- ═══════════════════════════════════════════════════════════════════
-- gov_contacts_setup.sql
-- WorksFree Hub — 지자체·공공기관 이메일 캠페인 (biz_contacts와 완전 분리)
--   테이블: gov_contacts
--   RPC   : get_gov_campaign_stats · get_gov_campaign_pending · get_gov_campaign_list
--   변경  : campaign_emails.contact_id의 biz_contacts FK 제거 (gov 스냅샷도 저장 가능하도록)
--
-- 전제 조건: complete_db_setup.sql (email_log, email_unsubscribes), campaign_v2_setup.sql
-- 실행: Supabase → SQL Editor → 전체 붙여넣기 → Run
-- 멱등성: IF NOT EXISTS, OR REPLACE → 반복 실행 안전
-- ═══════════════════════════════════════════════════════════════════


-- ══════════════════════════════════════════════════════════════════════
-- 1. gov_contacts — 지자체·복지관·주민센터·문화시설 연락처
-- ══════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS public.gov_contacts (
  id            uuid        DEFAULT gen_random_uuid() PRIMARY KEY,
  org_type      text        NOT NULL
                CHECK (org_type IN ('welfare_center','community_center','local_gov','culture_center')),
  org_name      text        NOT NULL,
  dept_name     text,                    -- 담당 부서명 (확인된 경우만)
  sido          text,
  sigungu       text,
  address       text,
  phone         text,
  homepage_url  text,
  email         text,
  email_source  text,                    -- 'homepage' | 'contact-page' | 'manual'
  email_status  text        NOT NULL DEFAULT 'active'
                CHECK (email_status IN ('active','unsubscribed')),
  scrape_status text,                    -- 'done' | 'no_email' | 'no_url' | 'error'
  created_at    timestamptz NOT NULL DEFAULT now(),
  updated_at    timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE public.gov_contacts ENABLE ROW LEVEL SECURITY;
-- Worker는 service_role 키로 RLS를 우회하므로 별도 정책 불필요

CREATE INDEX IF NOT EXISTS gov_contacts_org_type_idx ON public.gov_contacts (org_type);
CREATE INDEX IF NOT EXISTS gov_contacts_email_idx     ON public.gov_contacts (email);
CREATE INDEX IF NOT EXISTS gov_contacts_created_idx   ON public.gov_contacts (created_at DESC);
CREATE UNIQUE INDEX IF NOT EXISTS gov_contacts_email_uniq_idx
  ON public.gov_contacts (lower(email)) WHERE email IS NOT NULL AND email != '';


-- ══════════════════════════════════════════════════════════════════════
-- 2. campaign_emails.contact_id — biz_contacts 전용 FK 제거
--    gov 캠페인 스냅샷은 gov_contacts.id를 넣으므로 biz_contacts를 가리키는
--    기존 FK 제약이 있으면 INSERT가 실패한다. 참조 무결성은 애플리케이션에서
--    관리하고, contact_id는 순수 uuid(정보용 lineage)로 둔다.
-- ══════════════════════════════════════════════════════════════════════
DO $$
DECLARE
  v_conname text;
BEGIN
  SELECT conname INTO v_conname
  FROM pg_constraint
  WHERE conrelid = 'public.campaign_emails'::regclass
    AND contype = 'f'
    AND confrelid = 'public.biz_contacts'::regclass;

  IF v_conname IS NOT NULL THEN
    EXECUTE format('ALTER TABLE public.campaign_emails DROP CONSTRAINT %I', v_conname);
  END IF;
END $$;

-- 어느 소스 테이블에서 스냅샷됐는지 표시 (선택적 lineage)
ALTER TABLE public.campaign_emails
  ADD COLUMN IF NOT EXISTS contact_source text NOT NULL DEFAULT 'biz'
  CHECK (contact_source IN ('biz','gov'));


-- ══════════════════════════════════════════════════════════════════════
-- 3. get_gov_campaign_stats() — email_campaign_setup.sql의 biz 버전과 동일 패턴
-- ══════════════════════════════════════════════════════════════════════
CREATE OR REPLACE FUNCTION public.get_gov_campaign_stats()
RETURNS JSON
LANGUAGE SQL SECURITY DEFINER
SET search_path = public AS $$
  SELECT json_build_object(
    'total', (
      SELECT count(*)
      FROM public.gov_contacts
      WHERE email IS NOT NULL AND email != ''
    ),
    'active', (
      SELECT count(*)
      FROM public.gov_contacts
      WHERE email_status = 'active'
        AND email IS NOT NULL AND email != ''
    ),
    'sent', (
      SELECT count(DISTINCT recipient_email)
      FROM public.email_log
      WHERE status = 'sent'
        AND recipient_email IN (SELECT lower(email) FROM public.gov_contacts WHERE email IS NOT NULL)
    ),
    'unsubscribed', (
      SELECT count(*) FROM public.gov_contacts WHERE email_status = 'unsubscribed'
    ),
    'pending', (
      SELECT count(*)
      FROM public.gov_contacts gc
      WHERE gc.email_status = 'active'
        AND gc.email IS NOT NULL AND gc.email != ''
        AND NOT EXISTS (
          SELECT 1 FROM public.email_log el
          WHERE el.recipient_email = lower(gc.email)
            AND el.status = 'sent'
        )
        AND NOT EXISTS (
          SELECT 1 FROM public.email_unsubscribes eu
          WHERE eu.email = lower(gc.email)
        )
    )
  );
$$;

GRANT EXECUTE ON FUNCTION public.get_gov_campaign_stats() TO authenticated, anon;


-- ══════════════════════════════════════════════════════════════════════
-- 4. get_gov_campaign_pending(p_limit) — 다음 발송 대상 배치 반환
-- ══════════════════════════════════════════════════════════════════════
CREATE OR REPLACE FUNCTION public.get_gov_campaign_pending(p_limit INT DEFAULT 100)
RETURNS TABLE(contact_id UUID, org_name TEXT, dept_name TEXT, email TEXT)
LANGUAGE SQL SECURITY DEFINER
SET search_path = public AS $$
  SELECT gc.id, gc.org_name, gc.dept_name, gc.email
  FROM public.gov_contacts gc
  WHERE gc.email_status = 'active'
    AND gc.email IS NOT NULL AND gc.email != ''
    AND NOT EXISTS (
      SELECT 1 FROM public.email_log el
      WHERE el.recipient_email = lower(gc.email)
        AND el.status = 'sent'
    )
    AND NOT EXISTS (
      SELECT 1 FROM public.email_unsubscribes eu
      WHERE eu.email = lower(gc.email)
    )
  ORDER BY gc.created_at ASC
  LIMIT p_limit;
$$;

GRANT EXECUTE ON FUNCTION public.get_gov_campaign_pending(INT) TO authenticated, anon;


-- ══════════════════════════════════════════════════════════════════════
-- 5. get_gov_campaign_list() — 전체 연락처 + 발송 이력 JOIN (목록 조회용)
-- ══════════════════════════════════════════════════════════════════════
CREATE OR REPLACE FUNCTION public.get_gov_campaign_list()
RETURNS JSON
LANGUAGE SQL SECURITY DEFINER
SET search_path = public AS $$
  SELECT json_build_object(
    'total', (
      SELECT count(*) FROM public.gov_contacts
      WHERE email_status = 'active' AND email IS NOT NULL AND email != ''
    ),
    'rows', COALESCE((
      SELECT json_agg(row_to_json(t))
      FROM (
        SELECT
          gc.org_name,
          gc.dept_name,
          gc.org_type,
          gc.email,
          gc.email_status,
          CASE
            WHEN eu.email IS NOT NULL THEN 'unsubscribed'
            WHEN el.sent_at IS NOT NULL THEN 'sent'
            ELSE 'pending'
          END AS send_status,
          to_char(el.sent_at AT TIME ZONE 'Asia/Seoul', 'YYYY-MM-DD HH24:MI') AS sent_at_kst,
          el.subject,
          el.flyer_name
        FROM public.gov_contacts gc
        LEFT JOIN LATERAL (
          SELECT sent_at, subject, flyer_name
          FROM public.email_log
          WHERE recipient_email = lower(gc.email)
            AND status = 'sent'
          ORDER BY sent_at DESC
          LIMIT 1
        ) el ON true
        LEFT JOIN public.email_unsubscribes eu
          ON eu.email = lower(gc.email)
        WHERE gc.email_status = 'active'
          AND gc.email IS NOT NULL AND gc.email != ''
        ORDER BY
          CASE
            WHEN eu.email IS NOT NULL THEN 2
            WHEN el.sent_at IS NOT NULL THEN 1
            ELSE 0
          END ASC,
          gc.org_name ASC
      ) t
    ), '[]'::json)
  );
$$;

GRANT EXECUTE ON FUNCTION public.get_gov_campaign_list() TO authenticated, anon;


-- ══════════════════════════════════════════════════════════════════════
-- 검증
-- ══════════════════════════════════════════════════════════════════════
SELECT get_gov_campaign_stats();
