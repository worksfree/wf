#!/usr/bin/env python3
"""
통합 테스트: 크레딧 사용량 로깅 시스템
"""

import sys
import os

# Add the common directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
common_dir = os.path.join(current_dir, "10.common")
sys.path.insert(0, common_dir)

# Import modules
from wf_log import GlobalLoggerManager
from wf_credit_manager import CreditManager


def test_credit_logging():
    """크레딧 사용량 로깅 테스트"""

    # Initialize logger
    logger_manager = GlobalLoggerManager()
    logger = logger_manager.get_logger("Bom2Excel_test")

    logger.info("=== Bom2Excel 크레딧 사용량 로깅 통합 테스트 시작 ===")

    try:
        # Initialize credit manager for bom2excel app (100 credits per work)
        credit_manager = CreditManager("bom2excel")  # Check current status
        status = credit_manager.get_credit_status()
        logger.info(f"현재 크레딧 상태: {status}")

        # Test policy-based deduction with file count (100 credits per file)
        logger.info("정책 기반 크레딧 차감 테스트 (도면 파일 2개 - 200크레딧)")
        result = credit_manager.deduct_credits_by_policy(
            item_count=2, description="BOM 도면 파일 처리"
        )
        logger.info(f"차감 결과: {result}")

        # Test manual deduction with file count (50 credits per file for comparison)
        logger.info("수동 크레딧 차감 테스트 (추가 도면 1개 - 100크레딧)")
        result2 = credit_manager.deduct_credits(
            amount=100, description="추가 BOM 도면 처리", file_count=1
        )
        logger.info(f"수동 차감 결과: {result2}")

        # Check status after deductions
        status_after = credit_manager.get_credit_status()
        logger.info(f"차감 후 크레딧 상태: {status_after}")

        # Test sync with usage logging
        logger.info("구글 시트 동기화 및 사용량 로깅 테스트")

        # Check current session data before sync
        policy_info = credit_manager.get_policy_info()
        logger.info(f"앱 정책 정보: {policy_info}")

        sync_result = credit_manager.check_and_sync_credits()
        logger.info(f"동기화 결과: {sync_result}")

        # Check if session was reset after sync
        final_status = credit_manager.get_credit_status()
        logger.info(f"동기화 후 최종 상태: {final_status}")

        logger.info("=== 통합 테스트 완료 ===")
        return True

    except Exception as e:
        logger.error(f"테스트 실행 중 오류 발생: {e}")
        import traceback

        logger.error(f"스택 트레이스: {traceback.format_exc()}")
        return False


if __name__ == "__main__":
    # Run both tests
    test1 = test_credit_usage_logging()

    test_result = test1
    exit_code = 0 if test_result else 1
    print(f"테스트 {'성공' if test_result else '실패'} (exit code: {exit_code})")
    sys.exit(exit_code)
