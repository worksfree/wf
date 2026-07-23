-- ================================================================
-- 20_profiles_phone_column.sql — profiles.phone 컬럼 누락 수정
--
-- 발견 경위: lifeart_seed_testdata.sql 실행 중
--   "column \"phone\" of relation \"profiles\" does not exist" 에러로 발각.
--   실제로는 mypage(프로필 저장)·auth.js(ensureProfile)가 이미
--   profiles.phone 을 읽고 쓰는 코드를 갖고 있어 — 즉 회원가입 시 입력한
--   연락처가 지금껏 조용히 저장 실패해온 실제 버그.
--
-- 반드시 04(profiles.tenant_id) 이후 아무 때나 실행 가능(독립적).
-- ================================================================

ALTER TABLE public.profiles
  ADD COLUMN IF NOT EXISTS phone TEXT;

-- 기존 회원의 연락처를 auth.users(가입 시 raw_user_meta_data.phone)에서 역채움
-- (지금까지 저장이 실패해왔으므로 profiles.phone 은 전원 NULL이었을 것 — 있으면 보정)
UPDATE public.profiles p
SET phone = au.raw_user_meta_data->>'phone'
FROM auth.users au
WHERE au.id = p.id
  AND p.phone IS NULL
  AND au.raw_user_meta_data->>'phone' IS NOT NULL;

-- ── 검증 ──
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'profiles' AND column_name = 'phone';

SELECT id, email, phone FROM public.profiles WHERE phone IS NOT NULL LIMIT 20;
