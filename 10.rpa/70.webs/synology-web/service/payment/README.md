# Payment Workers

두 개의 Cloudflare Worker — Toss Payments 검증 + Stripe 세션 생성/검증.

## 배포 방법

### 방법 1: Cloudflare 대시보드 (간단)

1. [Cloudflare 대시보드](https://dash.cloudflare.com/) → **Workers & Pages**
2. **Create application** → **Create Worker**
3. Worker 이름 설정 후 JS 코드 붙여넣기
4. **Settings → Variables** 에서 환경 변수 추가 (아래 참조)
5. **Save and Deploy**

### 방법 2: Wrangler CLI

```bash
npm install -g wrangler
wrangler login

# toss-verify 배포
wrangler deploy toss-verify.js --name toss-verify --compatibility-date 2024-01-01

# stripe-session 배포
wrangler deploy stripe-session.js --name stripe-session --compatibility-date 2024-01-01
```

## 환경 변수 설정

Worker마다 **Settings → Variables** 에서 설정.

| Worker | 변수명 | 값 |
|--------|--------|----|
| toss-verify | `TOSS_SECRET_KEY` | Toss 대시보드 → API 키 → 테스트 시크릿 키 (`test_sk_...`) |
| stripe-session | `STRIPE_SECRET_KEY` | Stripe 대시보드 → Developers → API keys → Secret key (`sk_test_...`) |

> **중요**: 시크릿 키는 반드시 **Encrypt** 체크 후 저장.

## index.html 설정

Worker 배포 후 `index.html`의 상수 업데이트:

```javascript
const TOSS_VERIFY_URL    = 'https://toss-verify.YOUR_SUBDOMAIN.workers.dev';
const STRIPE_SESSION_URL = 'https://stripe-session.YOUR_SUBDOMAIN.workers.dev';
const TOSS_CLIENT_KEY    = 'test_ck_YOUR_TOSS_CLIENT_KEY'; // Toss 대시보드 → 클라이언트 키
```

## Supabase DB 테이블 생성

Supabase → **SQL Editor** 에서 실행:

```sql
-- 결제 이력
CREATE TABLE payments (
  id          uuid DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id     uuid REFERENCES auth.users(id) ON DELETE CASCADE,
  order_id    text UNIQUE NOT NULL,
  pg          text NOT NULL,          -- 'toss' | 'stripe'
  amount_krw  integer DEFAULT 0,
  amount_usd  numeric(10,2) DEFAULT 0,
  credits     integer NOT NULL,
  status      text DEFAULT 'paid',
  created_at  timestamptz DEFAULT now()
);

-- 크레딧 원장 (delta 패턴)
CREATE TABLE credits (
  id           uuid DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id      uuid REFERENCES auth.users(id) ON DELETE CASCADE,
  delta        integer NOT NULL,       -- 양수: 충전, 음수: 차감
  reason       text NOT NULL,          -- 'purchase' | 'usage' | 'refund'
  ref_order_id text,
  created_at   timestamptz DEFAULT now()
);

-- RLS 활성화
ALTER TABLE payments ENABLE ROW LEVEL SECURITY;
ALTER TABLE credits  ENABLE ROW LEVEL SECURITY;

-- 본인 데이터만 접근
CREATE POLICY "payments_self" ON payments USING (auth.uid() = user_id);
CREATE POLICY "credits_self"  ON credits  USING (auth.uid() = user_id);

-- 잔여 크레딧 계산 뷰
CREATE VIEW credit_balance AS
  SELECT user_id, SUM(delta) AS balance
  FROM credits
  GROUP BY user_id;
```

## 테스트 카드 번호

### Toss Payments (테스트 모드)
- 카드번호: `4242 4242 4242 4242`
- 만료일: 아무 미래 날짜
- CVC: 아무 3자리

### Stripe (테스트 모드)
- 카드번호: `4242 4242 4242 4242`
- 만료일: 아무 미래 날짜
- CVC: `424`
