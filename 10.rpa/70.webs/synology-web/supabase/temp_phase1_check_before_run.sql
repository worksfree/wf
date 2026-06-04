-- ═══════════════════════════════════════════════════════════════════
-- Phase 1 실행 전 현재 상태 진단 (단일 결과로 통합)
-- Supabase SQL Editor는 마지막 SELECT만 표시하므로 UNION ALL 사용
-- ═══════════════════════════════════════════════════════════════════

SELECT category, item, detail
FROM (

  -- 1. 테이블 존재 여부
  SELECT
    '1_tables'   AS category,
    table_name   AS item,
    table_type   AS detail
  FROM information_schema.tables
  WHERE table_schema = 'public'
    AND table_name IN ('profiles','credits','payments','credit_balance')

  UNION ALL

  -- 2. profiles 컬럼 목록
  SELECT
    '2_profiles_cols'                        AS category,
    column_name                              AS item,
    data_type || ' | default=' ||
      COALESCE(column_default,'NULL') ||
      ' | nullable=' || is_nullable         AS detail
  FROM information_schema.columns
  WHERE table_schema = 'public'
    AND table_name   = 'profiles'

  UNION ALL

  -- 3. RLS 정책
  SELECT
    '3_policies'  AS category,
    tablename || '.' || policyname AS item,
    cmd           AS detail
  FROM pg_policies
  WHERE tablename IN ('profiles','credits','payments')

  UNION ALL

  -- 4. 트리거
  SELECT
    '4_triggers'         AS category,
    trigger_name         AS item,
    event_object_table   AS detail
  FROM information_schema.triggers
  WHERE trigger_name = 'on_auth_user_created'

  UNION ALL

  -- 5. 함수
  SELECT
    '5_functions'  AS category,
    routine_name   AS item,
    routine_type   AS detail
  FROM information_schema.routines
  WHERE routine_schema = 'public'
    AND routine_name IN (
      'handle_new_user',
      'get_user_credit_balance',
      'deduct_credits',
      'admin_grant_credits'
    )

) q
ORDER BY category, item;
