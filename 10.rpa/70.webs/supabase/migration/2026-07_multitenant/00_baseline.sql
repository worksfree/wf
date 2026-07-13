-- ================================================================
-- 00_baseline.sql — 읽기 전용 스냅샷 (스키마 변경 없음)
-- 실행: Supabase Dashboard → SQL Editor
-- 각 결과를 복사해 보관하세요. 이후 모든 단계의 회귀 기준입니다.
-- ================================================================

-- (1) profiles.role 라이브 DEFAULT — 'general'이면 01번 스크립트가 필요한 상태
SELECT column_name, column_default
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'profiles' AND column_name = 'role';

-- (2) role 분포 — 'general' 잔존 행 확인
SELECT role, COUNT(*) FROM public.profiles GROUP BY role ORDER BY role;

-- (3) 주요 테이블 RLS 활성화 상태
SELECT tablename, rowsecurity
FROM pg_tables
WHERE schemaname = 'public'
  AND tablename IN ('tenants','profiles','profiles_backup_20260630','portfolios',
                    'auction_bookmarks','biz_contacts','biz_send_log',
                    'stock_snapshots','portfolio_daily','dividends')
ORDER BY tablename;

-- (4) admin RPC 목록과 시그니처
SELECT p.oid::regprocedure AS signature
FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
WHERE n.nspname = 'public' AND p.proname LIKE 'admin_%'
ORDER BY 1;

-- (5) 캠페인 RPC의 현재 권한 (revoke 전 상태 기록)
SELECT p.oid::regprocedure AS signature, p.proacl
FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
WHERE n.nspname = 'public'
  AND p.proname IN ('activate_campaign','get_campaign_batch','complete_campaign_batch',
                    'get_campaigns_list','get_campaign_runs','get_campaign_stats_v2',
                    'get_campaign_stats','get_campaign_list')
ORDER BY 1;

-- (6) 회귀 기준: 허브 관리자 계정(wfadmin@worksfree.kr)으로 로그인한 상태에서
--     admin/users 페이지가 정상 표시되는지 브라우저에서 확인하고,
--     아래 카운트를 기록해 두세요.
SELECT COUNT(*) AS total_profiles FROM public.profiles;
SELECT COUNT(*) AS total_payments FROM public.payments;
SELECT COUNT(*) AS total_credits  FROM public.credits;
