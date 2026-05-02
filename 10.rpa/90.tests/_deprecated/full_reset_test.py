import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "10.common"))

from wf_credit_manager import CreditManager, WorksFreeManager
from pathlib import Path

# 사용자 정보 가져오기
wf_manager = WorksFreeManager()
user_info = wf_manager.get_user_info()
user_email = user_info.get("user_email")

print("=" * 80)
print(f"전체 테스트: credit_history.json 초기화 및 재동기화")
print(f"사용자: {user_email}")
print("=" * 80)

# CreditManager 초기화
credit_manager = CreditManager("conversion_verifier", user_email)
credit_file = credit_manager.credit_file

# 기존 파일 백업
if credit_file.exists():
    backup_file = credit_file.parent / f"{credit_file.stem}_backup_{os.getpid()}.json"
    import shutil

    shutil.copy(credit_file, backup_file)
    print(f"\n✅ 기존 파일 백업: {backup_file}")

    # 파일 삭제
    credit_file.unlink()
    print(f"✅ 기존 파일 삭제: {credit_file}")
else:
    print(f"\n파일이 존재하지 않음: {credit_file}")

# 새로운 CreditManager 초기화 (파일 재생성)
print("\n" + "=" * 80)
print("CreditManager 재초기화...")
print("=" * 80)

credit_manager = CreditManager("conversion_verifier", user_email)

# 구매 이력 동기화
print("\n구매 이력 동기화 실행 중...")
result = credit_manager.pull_and_apply_purchases()

print("\n동기화 결과:")
print(f"  Success: {result.get('success')}")
print(f"  Message: {result.get('message')}")
print(f"  Added: {result.get('added', 0)} 크레딧")
print(f"  Applied IDs: {result.get('applied_ids', [])}")

# 최종 상태 확인
print("\n" + "=" * 80)
print("최종 credit_history.json 상태")
print("=" * 80)

import json

if credit_file.exists():
    with open(credit_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    print(f"\n현재 크레딧: {data.get('current_credits', 0)}")
    print(f"Trial 크레딧: {data.get('trial_credits', 0)}")
    print(f"Purchased 크레딧: {data.get('purchased_credits', 0)}")

    purchase_history = data.get("purchase_history", [])
    print(f"\n구매 이력 개수: {len(purchase_history)}")

    if purchase_history:
        print("\n모든 구매 이력:")
        for idx, purchase in enumerate(purchase_history, 1):
            print(f"\n  [{idx}] transaction_id: {purchase.get('transaction_id', 'N/A')}")
            print(f"      amount: {purchase.get('amount', 0)}")
            print(f"      purchased_credit: {purchase.get('purchased_credit', 'N/A')}")
            print(f"      bonus_credit: {purchase.get('bonus_credit', 'N/A')}")
            print(f"      total_credit: {purchase.get('total_credit', 'N/A')}")
            print(f"      promo_code: {purchase.get('promo_code', 'N/A')}")
