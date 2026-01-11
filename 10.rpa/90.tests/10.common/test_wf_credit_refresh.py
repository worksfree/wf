#!/usr/bin/env python3
"""크레딧 갱신 테스트"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "10.common"))

from wf_credit_manager import CreditManager


def main():
    print("🔄 크레딧 갱신 테스트...")

    # CreditManager 초기화
    manager = CreditManager(app_name="bom_exporter")

    # 현재 크레딧 상태 확인
    current_status = manager.get_credit_status()
    print(f"현재 크레딧 상태:")
    print(f"  구매 크레딧: {current_status.get('purchased_credits', 0)}")
    print(f"  총 크레딧: {current_status.get('remaining_credits', 0)}")
    print()

    # 구매 이력 갱신 시도
    result = manager.pull_and_apply_purchases()

    print(f"갱신 결과: {result}")

    if result.get("success"):
        if result.get("added", 0) > 0:
            print(f"✅ {result.get('added')} 크레딧이 추가되었습니다!")
            print(f"적용된 구매 ID: {result.get('applied_ids', [])}")
        else:
            print("ℹ️ 신규 구매 이력이 없습니다.")
    else:
        print(f"❌ 갱신 실패: {result.get('message')}")

    # 갱신 후 크레딧 상태 확인
    updated_status = manager.get_credit_status()
    print(f"\n갱신 후 크레딧 상태:")
    print(f"  구매 크레딧: {updated_status.get('purchased_credits', 0)}")
    print(f"  총 크레딧: {updated_status.get('remaining_credits', 0)}")


if __name__ == "__main__":
    main()
