-- ================================================================
-- 13_verify_user_tenant_sync.sql — auth.users ↔ profiles 정합성 & 테넌트 커버리지 검증
--
-- 읽기 전용(진단용). SQL Editor 에서 실행해 각 결과를 확인한다.
-- 기대값이 다르면 아래 [교정] 블록을 검토 후 개별 실행.
-- ================================================================

-- ① auth.users 와 profiles 가 1:1 인지 (양방향 고아 0 이어야 정상)
--    a. auth.users 에는 있는데 profiles 가 없는 계정 (트리거 누락/실패)
SELECT 'auth_without_profile' AS check, COUNT(*) AS must_be_zero
FROM auth.users u
LEFT JOIN public.profiles p ON p.id = u.id
WHERE p.id IS NULL;

--    b. profiles 에는 있는데 auth.users 가 없는 행 (삭제 잔존)
SELECT 'profile_without_auth' AS check, COUNT(*) AS must_be_zero
FROM public.profiles p
LEFT JOIN auth.users u ON u.id = p.id
WHERE u.id IS NULL;

-- ② 전 profiles 에 tenant_id 존재하는지 (멀티테넌트 필수 — NOT NULL 이므로 0 이어야 함)
SELECT 'profile_without_tenant' AS check, COUNT(*) AS must_be_zero
FROM public.profiles WHERE tenant_id IS NULL;

-- ③ 테넌트별 사용자 분포 (도메인 라벨과 함께)
SELECT COALESCE(t.domain, '(NULL)') AS tenant, COUNT(*) AS users
FROM public.profiles p
LEFT JOIN public.tenants t ON t.id = p.tenant_id
GROUP BY t.domain
ORDER BY users DESC;

-- ④ 소셜 로그인 계정 중 테넌트 미보정(worksfree 로 남은) 의심 건
--    LifeArt 사이트에서 소셜 가입했으나 claimOAuthProfile 실패로 worksfree 에 남은 케이스 점검.
--    (auth.users.raw_app_meta_data->>'provider' 로 가입 경로 확인)
SELECT
  u.raw_app_meta_data->>'provider' AS provider,
  COALESCE(t.domain,'(NULL)')      AS tenant,
  COUNT(*)                         AS cnt
FROM auth.users u
JOIN public.profiles p ON p.id = u.id
LEFT JOIN public.tenants t ON t.id = p.tenant_id
WHERE u.raw_app_meta_data->>'provider' IN ('google','kakao')
GROUP BY 1, 2
ORDER BY 1, 3 DESC;

-- ⑤ LifeArt 테넌트 사용자 목록 (관리자가 보게 될 "내 DB 사용자 목록")
--    auth.users 이메일/가입경로 + profiles 이름/역할/가입일 조인.
SELECT
  u.email,
  u.raw_app_meta_data->>'provider' AS provider,
  p.name,
  p.role,
  u.created_at
FROM public.profiles p
JOIN auth.users u ON u.id = p.id
WHERE p.tenant_id = (SELECT id FROM public.tenants WHERE domain = 'lifeart.ai.kr')
ORDER BY u.created_at DESC;

-- ── [교정] 필요 시에만 개별 실행 ────────────────────────────────
-- (④에서 LifeArt 로 가입한 소셜 계정이 worksfree 로 남아있고, 해당 email 이 확실히
--  LifeArt 사용자라면 아래로 수동 이관. email 을 실제 값으로 바꿔 실행.)
-- UPDATE public.profiles SET tenant_id = (SELECT id FROM public.tenants WHERE domain='lifeart.ai.kr')
-- WHERE id = (SELECT id FROM auth.users WHERE email = 'someone@example.com');
