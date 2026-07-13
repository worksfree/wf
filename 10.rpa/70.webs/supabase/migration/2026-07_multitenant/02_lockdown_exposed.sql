-- ================================================================
-- 02_lockdown_exposed.sql — 노출 테이블/RPC 잠금 (독립, 저위험)
--
-- 안전 근거 (코드 전수 조사 완료):
--  · 캠페인 RPC 8종의 유일한 호출자 = send-mail Worker(service_role 키)
--    → anon/authenticated 권한 회수해도 Worker는 영향 없음 (service_role은 별도)
--  · biz_contacts/biz_send_log 의 유일한 접근 주체 = bizdb Worker(service_role)
--    → RLS 활성화(정책 0개 = 기본 거부)해도 Worker 무영향, anon PII 노출만 차단
--  · profiles_backup_20260630 은 RLS 없는 전체 PII 사본 → 즉시 잠금
-- ================================================================

-- ① 미보호 PII 백업 테이블 잠금 (정책 없이 RLS만 켜면 anon/authenticated 기본 거부)
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_tables WHERE schemaname='public' AND tablename='profiles_backup_20260630') THEN
    EXECUTE 'ALTER TABLE public.profiles_backup_20260630 ENABLE ROW LEVEL SECURITY';
  END IF;
END $$;

-- ② biz_contacts / biz_send_log 잠금 (존재할 때만)
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_tables WHERE schemaname='public' AND tablename='biz_contacts') THEN
    EXECUTE 'ALTER TABLE public.biz_contacts ENABLE ROW LEVEL SECURITY';
  END IF;
  IF EXISTS (SELECT 1 FROM pg_tables WHERE schemaname='public' AND tablename='biz_send_log') THEN
    EXECUTE 'ALTER TABLE public.biz_send_log ENABLE ROW LEVEL SECURITY';
  END IF;
END $$;

-- ③ 캠페인 RPC 익명/로그인 사용자 실행 권한 회수 (시그니처 무관하게 이름으로 전부)
DO $$
DECLARE fn RECORD;
BEGIN
  FOR fn IN
    SELECT p.oid::regprocedure AS sig
    FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'public'
      AND p.proname IN ('activate_campaign','get_campaign_batch','complete_campaign_batch',
                        'get_campaigns_list','get_campaign_runs','get_campaign_stats_v2',
                        'get_campaign_stats','get_campaign_list')
  LOOP
    EXECUTE format('REVOKE EXECUTE ON FUNCTION %s FROM anon, authenticated', fn.sig);
  END LOOP;
END $$;

-- ── 검증 ──
-- (a) 세 테이블 모두 rowsecurity = true
SELECT tablename, rowsecurity FROM pg_tables
WHERE schemaname='public'
  AND tablename IN ('profiles_backup_20260630','biz_contacts','biz_send_log');

-- (b) 캠페인 RPC 권한에서 anon/authenticated 가 사라졌는지 (proacl에 anon= 없어야 함)
SELECT p.oid::regprocedure AS signature, p.proacl
FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
WHERE n.nspname='public'
  AND p.proname IN ('activate_campaign','get_campaign_batch','complete_campaign_batch',
                    'get_campaigns_list','get_campaign_runs','get_campaign_stats_v2',
                    'get_campaign_stats','get_campaign_list');

-- (c) 브라우저 회귀: admin/email-campaign 페이지 통계/목록이 여전히 표시되는지
--     (Worker 경유라 정상이어야 함). 다음 cron(매일 KST 09:00) 발송도 정상이어야 함.
