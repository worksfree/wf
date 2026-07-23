-- ================================================================
--  lifeart_seed_testdata.sql — LifeArt 테스트/데모 데이터 일괄 재시딩
--  실행 위치: Supabase Dashboard → SQL Editor
--  선행 조건:
--   1) migration/2026-07_multitenant/20_profiles_phone_column.sql 먼저 실행
--      (profiles.phone 컬럼이 없으면 아래 UPDATE 에서 에러남)
--   2) lifeart_wipe_all.sql 로 먼저 비운 상태에서 실행 권장(중복 실행 시
--      회원 부분은 이메일 UNIQUE 제약으로 에러 남 — 재실행 전 wipe 먼저).
--
--  이 스크립트가 다시 채우는 것:
--   ① 테스트 회원 계정 2개 (auth.users + auth.identities + profiles 클레임)
--        - lifeart.tester@worksfree.kr      / LifeArt!test2026   (일반회원)
--        - lifeart.admin.tester@worksfree.kr  / LifeArt!admin2026  (LifeArt 관리자)
--      → dev-toolkit.js·tests/smoke.spec.js·payment.spec.js 가 이 정확한
--        이메일/비밀번호에 고정 의존하므로 반드시 동일하게 재생성한다.
--   ② 공지 2건(실제 오픈 공지 1 + 테스트 표기 공지 1) · FAQ 3건 · 보도자료 1건
--   ③ 데모 주문 6건 + 결제 6건(상태 다양하게, 그중 2건은 위 회원 계정에 연결)
--   ④ 데모 문의 1건(답변완료 상태)
--
--  날짜는 전부 NOW()/CURRENT_DATE 상대값 — 언제 실행해도 "최근"으로 현행화됨.
--  히어로 슬라이드(첫화면)는 건드리지 않음(위 wipe 스크립트와 동일하게 제외).
-- ================================================================

CREATE EXTENSION IF NOT EXISTS pgcrypto;

DO $$
DECLARE
  v_tenant     uuid := public.lifeart_tenant_id();
  v_tester_id  uuid := gen_random_uuid();
  v_admin_id   uuid := gen_random_uuid();
BEGIN
  IF v_tenant IS NULL THEN
    RAISE EXCEPTION 'lifeart 테넌트를 찾을 수 없습니다 — 03 마이그레이션을 먼저 확인하세요';
  END IF;

  -- ── ① 테스트 회원 계정 2개 재생성 ──────────────────────────────
  INSERT INTO auth.users (
    instance_id, id, aud, role, email, encrypted_password,
    email_confirmed_at, raw_app_meta_data, raw_user_meta_data,
    created_at, updated_at, confirmation_token, recovery_token,
    email_change_token_new, email_change
  ) VALUES
  ('00000000-0000-0000-0000-000000000000', v_tester_id, 'authenticated', 'authenticated',
   'lifeart.tester@worksfree.kr', crypt('LifeArt!test2026', gen_salt('bf')),
   NOW(), '{"provider":"email","providers":["email"]}'::jsonb,
   jsonb_build_object('email','lifeart.tester@worksfree.kr','email_verified',true,
     'name','테스트 회원','phone','010-0000-0001','phone_verified',false,
     'sub', v_tester_id::text, 'tenant','lifeart'),
   NOW(), NOW(), '', '', '', ''),
  ('00000000-0000-0000-0000-000000000000', v_admin_id, 'authenticated', 'authenticated',
   'lifeart.admin.tester@worksfree.kr', crypt('LifeArt!admin2026', gen_salt('bf')),
   NOW(), '{"provider":"email","providers":["email"]}'::jsonb,
   jsonb_build_object('email','lifeart.admin.tester@worksfree.kr','email_verified',true,
     'name','테스트 관리자','phone','010-0000-0002','phone_verified',false,
     'sub', v_admin_id::text, 'tenant','lifeart'),
   NOW(), NOW(), '', '', '', '');

  INSERT INTO auth.identities (id, user_id, provider_id, identity_data, provider, last_sign_in_at, created_at, updated_at)
  VALUES
  (gen_random_uuid(), v_tester_id, v_tester_id::text,
   jsonb_build_object('sub', v_tester_id::text, 'email','lifeart.tester@worksfree.kr','email_verified',true,'phone_verified',false),
   'email', NOW(), NOW(), NOW()),
  (gen_random_uuid(), v_admin_id, v_admin_id::text,
   jsonb_build_object('sub', v_admin_id::text, 'email','lifeart.admin.tester@worksfree.kr','email_verified',true,'phone_verified',false),
   'email', NOW(), NOW(), NOW());

  -- handle_new_user 트리거가 만든 기본 profiles 행(tenant=worksfree, role=member)을
  -- LifeArt 테넌트로 클레임 + 관리자 계정은 role='admin' 지정.
  -- (phone 컬럼은 20_profiles_phone_column.sql 로 추가됨 — 먼저 실행 필요)
  UPDATE public.profiles SET tenant_id = v_tenant, role = 'member', name = '테스트 회원',   email = 'lifeart.tester@worksfree.kr',       phone = '010-0000-0001' WHERE id = v_tester_id;
  UPDATE public.profiles SET tenant_id = v_tenant, role = 'admin',  name = '테스트 관리자', email = 'lifeart.admin.tester@worksfree.kr', phone = '010-0000-0002' WHERE id = v_admin_id;

  -- ── ② 공지 · FAQ · 보도자료 ──────────────────────────────────
  INSERT INTO public.lifeart_notices (tenant_id, title, body, pinned) VALUES
  (v_tenant, 'LifeArt 홈페이지가 새롭게 오픈했습니다', 'LifeArt 온라인 서비스를 시작합니다. 포토북·삽입식앨범·VIP앨범·액자를 온라인에서 만나보세요.', true),
  (v_tenant, '공지 사항 테스트임', '공지 사항 테스트', false);

  INSERT INTO public.lifeart_faqs (tenant_id, question, answer, sort_order) VALUES
  (v_tenant, '주문 후 제작 기간은 얼마나 걸리나요?', '상품 종류와 수량에 따라 다르며, 삽입식 앨범은 현장 즉석 제작도 가능합니다. 정확한 기간은 견적 문의 시 안내드립니다.', 1),
  (v_tenant, '대량 주문 시 할인이 있나요?', '액자 등 일부 상품은 수량에 따라 할인이 적용됩니다. 견적 문의를 통해 안내드립니다.', 2),
  (v_tenant, '기업 단체 행사도 진행하나요?', '네, 26년간 다양한 기업 행사(진수식, 워크숍, 해외 출장 등)의 VIP 앨범과 삽입식 앨범을 제작해왔습니다.', 3);

  INSERT INTO public.lifeart_press (tenant_id, title, outlet, summary, published_on, is_published, pinned)
  VALUES (v_tenant, 'LifeArt, 26년 포토 시스템 노하우로 프리미엄 앨범 서비스 확대', '보도자료',
    '한화오션 VIP 앨범 납품 등 26년간 축적한 포토 시스템 기술을 바탕으로 온라인 프리미엄 포토 서비스를 시작합니다.',
    CURRENT_DATE, true, true);

  -- ── ③ 데모 주문 + 결제 (2건은 위 회원 계정에 연결, 나머지는 게스트) ──
  WITH prod AS (SELECT id, name FROM public.lifeart_products),
  seed AS (
    SELECT * FROM (VALUES
      ('VIP 앨범 Tier A/B/C (상담형)', v_admin_id,  1, 0::bigint,     'done',     'delivered', 45),
      ('삽입식 기념앨범 (상담형)',       NULL::uuid,   2, 0::bigint,     'shipping', 'shipping',  20),
      ('슬림 크리스탈 24x30',           v_tester_id, 1, 61600::bigint, 'done',     'delivered', 15),
      ('삼각 소 다크 8x10',             NULL::uuid,   2, 14400::bigint, 'paid',     'ready',      7),
      ('삼각 소 다크 11x14',            v_tester_id, 1, 11600::bigint, 'paid',     'ready',      3),
      ('삼각 소 다크 20x30',            NULL::uuid,   1, 33000::bigint, 'pending',  'ready',      1)
    ) AS v(prod_name, uid, qty, amount, status, ship_status, days_ago)
  ),
  new_orders AS (
    INSERT INTO public.lifeart_orders
      (tenant_id, user_id, product_id, quantity, amount, status, shipping_address, shipping_status, env, created_at, updated_at)
    SELECT
      v_tenant, s.uid, p.id, s.qty, s.amount, s.status, 'DEMO', s.ship_status, 'pre-test',
      NOW() - (s.days_ago || ' days')::interval,
      NOW() - (s.days_ago || ' days')::interval
    FROM seed s JOIN prod p ON p.name = s.prod_name
    RETURNING id, status, amount, created_at
  )
  INSERT INTO public.lifeart_payments (tenant_id, order_id, pg_provider, pg_tid, amount, status, env, approved_at, created_at)
  SELECT v_tenant, id, 'toss', 'DEMO_' || substr(id::text, 1, 8), amount, 'approved', 'pre-test', created_at, created_at
  FROM new_orders
  WHERE status IN ('paid', 'shipping', 'done');

  -- ── ④ 데모 문의 1건 ──────────────────────────────────────────
  INSERT INTO public.lifeart_inquiries
    (tenant_id, type, env, user_id, name, phone, email, message, status, answer, answered_at, created_at)
  VALUES
    (v_tenant, 'estimate', 'pre-test', NULL,
     '홍길동', '010-1234-5678', 'demo@example.com',
     '기업 워크숍 50명 기념앨범 견적 부탁드립니다.',
     'answered',
     '문의 주셔서 감사합니다. 상세 견적은 이메일로 안내드렸습니다.',
     NOW() - interval '2 days',
     NOW() - interval '3 days');
END $$;

-- ── 검증 ──
SELECT 'orders' AS t, COUNT(*) FROM public.lifeart_orders WHERE tenant_id = public.lifeart_tenant_id()
UNION ALL SELECT 'payments',    COUNT(*) FROM public.lifeart_payments    WHERE tenant_id = public.lifeart_tenant_id()
UNION ALL SELECT 'inquiries',   COUNT(*) FROM public.lifeart_inquiries   WHERE tenant_id = public.lifeart_tenant_id()
UNION ALL SELECT 'notices',     COUNT(*) FROM public.lifeart_notices     WHERE tenant_id = public.lifeart_tenant_id()
UNION ALL SELECT 'faqs',        COUNT(*) FROM public.lifeart_faqs        WHERE tenant_id = public.lifeart_tenant_id()
UNION ALL SELECT 'press',       COUNT(*) FROM public.lifeart_press       WHERE tenant_id = public.lifeart_tenant_id()
UNION ALL SELECT 'members',     COUNT(*) FROM auth.users WHERE email IN ('lifeart.tester@worksfree.kr','lifeart.admin.tester@worksfree.kr');

-- 재생성된 회원의 테넌트 클레임·역할 확인 (member/admin 정확히 나와야 함)
SELECT u.email, p.role, p.tenant_id = public.lifeart_tenant_id() AS is_lifeart_tenant
FROM auth.users u JOIN public.profiles p ON p.id = u.id
WHERE u.email IN ('lifeart.tester@worksfree.kr', 'lifeart.admin.tester@worksfree.kr');
