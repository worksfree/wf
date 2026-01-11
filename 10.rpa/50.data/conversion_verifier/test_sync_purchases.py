import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "10.common"))

from wf_credit_manager import CreditManager, WorksFreeManager

# 사용자 정보 가져오기
wf_manager = WorksFreeManager()
user_info = wf_manager.get_user_info()
user_email = user_info.get("user_email")

print("=" * 80)
print(f"구매 이력 동기화 테스트")
print(f"사용자: {user_email}")
print("=" * 80)

# CreditManager 초기화
credit_manager = CreditManager("conversion_verifier", user_email)

print("\n구매 이력 동기화 실행 중...")
result = credit_manager.pull_and_apply_purchases()

print("\n결과:")
print(f"  Success: {result.get('success')}")
print(f"  Message: {result.get('message')}")
print(f"  Added: {result.get('added', 0)} 크레딧")
print(f"  Applied IDs: {result.get('applied_ids', [])}")

if result.get("error"):
    print(f"  Error: {result.get('error')}")

# 업데이트 후 credit_history 확인
print("\n" + "=" * 80)
print("업데이트 후 credit_history.json 확인")
print("=" * 80)

import json

credit_file = credit_manager.credit_file
if credit_file.exists():
    with open(credit_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    print(f"\n현재 크레딧: {data.get('current_credits', 0)}")
    print(f"Trial 크레딧: {data.get('trial_credits', 0)}")
    print(f"Purchased 크레딧: {data.get('purchased_credits', 0)}")

    purchase_history = data.get("purchase_history", [])
    print(f"\n구매 이력 개수: {len(purchase_history)}")

    if purchase_history:
        print("\n최신 구매 이력 (최대 3개):")
        for idx, purchase in enumerate(purchase_history[-3:], 1):
            print(f"\n  [{idx}] transaction_id: {purchase.get('transaction_id', 'N/A')}")
            print(f"      amount: {purchase.get('amount', 0)}")
            print(f"      purchased_credit: {purchase.get('purchased_credit', 'N/A')}")
            print(f"      bonus_credit: {purchase.get('bonus_credit', 'N/A')}")
            print(f"      total_credit: {purchase.get('total_credit', 'N/A')}")
            print(f"      promo_code: {purchase.get('promo_code', 'N/A')}")
            print(f"      applied_date: {purchase.get('applied_date', 'N/A')}")
