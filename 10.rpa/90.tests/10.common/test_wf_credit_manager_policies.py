#!/usr/bin/env python3
"""
다중 앱 정책 테스트: 실제 크레딧 단위 확인
"""

import sys
import os
import json
from pathlib import Path
import pytest

# Add the common directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
common_dir = os.path.join(current_dir, "10.common")
sys.path.insert(0, common_dir)

# Import modules
from wf_log import GlobalLoggerManager
from wf_credit_manager import CreditManager, WorksFreeManager


def test_app_policy_verification():
    """실제 앱 정책 검증 테스트"""

    logger_manager = GlobalLoggerManager()
    logger = logger_manager.get_logger("policy_verification")

    logger.info("=== 실제 앱 정책 검증 테스트 ===")

    # 실제 앱 정책 테스트
    apps_to_test = [
        {"app": "bom2excel", "expected_cost": 100, "files": 2},
        {"app": "DWG_Classifier", "expected_cost": 50, "files": 3},
        {"app": "file_list_check", "expected_cost": 10, "files": 5},
    ]

    for test_data in apps_to_test:
        logger.info(f"\n--- {test_data['app']} 정책 확인 ---")

        try:
            credit_manager = CreditManager(test_data["app"])
            policy_info = credit_manager.get_policy_info()

            actual_cost = policy_info.get("per_item_cost", 0)
            expected_cost = test_data["expected_cost"]

            logger.info(f"예상 비용: {expected_cost}크레딧/파일")
            logger.info(f"실제 비용: {actual_cost}크레딧/파일")
            logger.info(f"정책 일치: {'✅' if actual_cost == expected_cost else '❌'}")

            if actual_cost == expected_cost:
                # 정책이 맞다면 실제 차감 테스트
                file_count = test_data["files"]
                total_expected = file_count * expected_cost

                logger.info(f"{file_count}개 파일 처리 예상 비용: {total_expected}크레딧")

                status_before = credit_manager.get_credit_status()
                credits_before = status_before.get("remaining_credits", 0)

                result = credit_manager.deduct_credits_by_policy(
                    item_count=file_count,
                    description=f"{test_data['app']} 테스트 - {file_count}개 파일",
                )

                if result.get("success"):
                    credits_after = result.get("remaining_credits", 0)
                    actual_deducted = credits_before - credits_after

                    logger.info(f"차감 전: {credits_before}크레딧")
                    logger.info(f"차감 후: {credits_after}크레딧")
                    logger.info(f"실제 차감: {actual_deducted}크레딧")
                    logger.info(
                        f"차감 정확성: {'✅' if actual_deducted == total_expected else '❌'}"
                    )
                else:
                    logger.error(f"차감 실패: {result.get('message', 'Unknown error')}")

        except Exception as e:
            logger.error(f"{test_data['app']} 테스트 중 오류: {e}")

    logger.info("\n=== 정책 검증 테스트 완료 ===")


@pytest.mark.unit
def test_deduct_uses_credit_per_work(seed_policy):
    wf = WorksFreeManager()
    cm = CreditManager(app_name="unit_app", user_email="t@e.st")
    # Measure before/after and validate deduction equals cpw * items
    before = cm.get_credit_status()
    cpw = cm.get_per_item_cost()
    items = 3
    res = cm.deduct_credits_by_policy(item_count=items, description="unit run")
    assert res["success"] is True
    after = cm.get_credit_status()
    assert before["trial_credits"] - after["trial_credits"] == cpw * items


if __name__ == "__main__":
    test_app_policy_verification()
    print("정책 검증 테스트 완료!")
