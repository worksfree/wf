-- ================================================================
--  경매지도 북마크 테이블
--  실행: Supabase Dashboard → SQL Editor
-- ================================================================

CREATE TABLE IF NOT EXISTS public.auction_bookmarks (
  id           uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id      uuid        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  case_number  text        NOT NULL,

  -- bookmark 시점 스냅샷 (원본 경매 정보가 사라져도 보존)
  court_name   text,
  item_type    text,
  address      text,
  appraise     bigint,
  min_price    bigint,
  bid_date     text,
  fail_count   int         DEFAULT 0,

  note         text,       -- 사용자 개인 메모
  created_at   timestamptz DEFAULT now(),

  UNIQUE (user_id, case_number)
);

-- RLS 활성화
ALTER TABLE public.auction_bookmarks ENABLE ROW LEVEL SECURITY;

-- 사용자는 자신의 북마크만 조회/추가/삭제 가능
CREATE POLICY "users own bookmarks"
  ON public.auction_bookmarks
  FOR ALL
  USING  (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_auction_bookmarks_user
  ON public.auction_bookmarks (user_id, created_at DESC);
