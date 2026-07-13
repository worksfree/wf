-- ================================================================
-- 07_email_tenant.sql — 이메일/캠페인 계열 tenant_id 부여 (추가 컬럼만, 저위험)
--
-- 이 계열 테이블은 전부 Worker(service_role) 전용 접근이라 컬럼 추가는 무영향.
-- auction 계열과 동일한 TEXT DEFAULT 'worksfree' 규약 사용
-- (이 계열은 Worker 가 문자열 식별자로 다룸 — uuid FK 불필요).
-- Worker 코드는 수정 불필요: INSERT 시 컬럼 미지정 → DEFAULT 적용.
-- ================================================================

DO $$
DECLARE t TEXT;
BEGIN
  FOREACH t IN ARRAY ARRAY[
    'email_log','email_unsubscribes','campaigns','campaign_emails',
    'campaign_runs','gov_contacts','biz_contacts'
  ]
  LOOP
    IF EXISTS (SELECT 1 FROM pg_tables WHERE schemaname='public' AND tablename=t) THEN
      EXECUTE format(
        'ALTER TABLE public.%I ADD COLUMN IF NOT EXISTS tenant_id TEXT NOT NULL DEFAULT ''worksfree''', t);
    END IF;
  END LOOP;
END $$;

-- ── 검증 ──
SELECT table_name, column_default
FROM information_schema.columns
WHERE table_schema='public' AND column_name='tenant_id'
  AND table_name IN ('email_log','email_unsubscribes','campaigns','campaign_emails',
                     'campaign_runs','gov_contacts','biz_contacts')
ORDER BY table_name;
-- 각 테이블 tenant_id NULL 0건이어야 함 (NOT NULL DEFAULT 라 자동):
SELECT 'email_log' AS t, COUNT(*) AS null_cnt FROM public.email_log WHERE tenant_id IS NULL
UNION ALL SELECT 'email_unsubscribes', COUNT(*) FROM public.email_unsubscribes WHERE tenant_id IS NULL
UNION ALL SELECT 'campaigns', COUNT(*) FROM public.campaigns WHERE tenant_id IS NULL;
-- 회귀: send-mail Worker 다음 cron(매일 KST 09:00) 발송 정상.
