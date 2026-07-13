-- ================================================================
-- 06_auction_tenant.sql — 경매 북마크 tenant_id 갭 메우기 (독립, 저위험)
--
-- auction_items / auction_meta 는 이미 tenant_id TEXT DEFAULT 'worksfree' 사용.
-- auction_bookmarks 만 누락되어 있어 동일 규약으로 맞춤.
-- NOT NULL DEFAULT 이므로 기존 행은 ALTER 시 자동 백필됨.
-- ================================================================

ALTER TABLE public.auction_bookmarks
  ADD COLUMN IF NOT EXISTS tenant_id TEXT NOT NULL DEFAULT 'worksfree';

-- RLS 는 기존 "본인(user_id) 소유" 정책 유지.
-- 현재 tenant 값이 'worksfree' 하나뿐이라 테넌트 필터는 사변적 → 보류.
-- 두 번째 경매 테넌트가 실제로 생기면 그때 user_id + tenant_id 로 강화할 것.

-- ── 검증 ──
SELECT COUNT(*) AS null_tenant FROM public.auction_bookmarks WHERE tenant_id IS NULL; -- 0
SELECT table_name, column_name, data_type, column_default
FROM information_schema.columns
WHERE table_schema='public'
  AND table_name IN ('auction_items','auction_meta','auction_bookmarks')
  AND column_name='tenant_id'
ORDER BY table_name;
-- 회귀: auction.worksfree.kr 목록 표시 + 로그인 후 북마크 추가/삭제 정상.
