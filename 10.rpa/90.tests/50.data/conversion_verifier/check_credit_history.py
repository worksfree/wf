import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "10.common"))

from wf_credit_manager import CreditManager, WorksFreeManager

# 사용자 정보 가져오기
wf_manager = WorksFreeManager()
user_info = wf_manager.get_user_info()
user_email = user_info.get("user_email")

print("=" * 80)
print(f"사용자: {user_email}")
print("=" * 80)

# CreditManager 초기화
credit_manager = CreditManager("conversion_verifier", user_email)

# credit_history.json 파일 경로
credit_file = credit_manager.credit_file
print(f"\n크레딧 파일 경로: {credit_file}")

if credit_file.exists():
    with open(credit_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    print(f"\n파일 존재: Yes")
    print(f"현재 크레딧: {data.get('current_credits', 0)}")
    print(f"Trial 크레딧: {data.get('trial_credits', 0)}")
    print(f"Purchased 크레딧: {data.get('purchased_credits', 0)}")

    purchase_history = data.get("purchase_history", [])
    print(f"\n구매 이력 개수: {len(purchase_history)}")

    if purchase_history:
        print("\n구매 이력 상세:")
        for idx, purchase in enumerate(purchase_history, 1):
            print(f"\n  [{idx}] transaction_id: {purchase.get('transaction_id', 'N/A')}")
            print(f"      amount: {purchase.get('amount', 0)}")
            print(f"      purchased_credit: {purchase.get('purchased_credit', 'N/A')}")
            print(f"      bonus_credit: {purchase.get('bonus_credit', 'N/A')}")
            print(f"      total_credit: {purchase.get('total_credit', 'N/A')}")
            print(f"      applied_date: {purchase.get('applied_date', 'N/A')}")
    else:
        print("\n⚠️ purchase_history가 비어있습니다!")

    applied_ids = data.get("applied_purchase_ids", [])
    print(f"\n적용된 구매 ID 개수: {len(applied_ids)}")
    if applied_ids:
        print(f"적용된 ID 목록: {applied_ids}")
else:
    print(f"\n파일 존재: No")
