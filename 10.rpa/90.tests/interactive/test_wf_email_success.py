"""
성공 메일 전송 테스트 스크립트
automation.py의 성공 메일 전송 로직을 독립적으로 테스트

위치: 90.tests/10.common/test_wf_email_success.py
테스트 대상: 10.common/wf_email.py
"""

import sys
import os

# 경로 설정 (90.tests/10.common -> 10.common)
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
common_dir = os.path.join(project_root, "10.common")
sys.path.insert(0, common_dir)

import wf_email as wfm
import wf_log as wflog
import logging

# 로거 설정
logger = wflog.get_app_logger("test_email_success", console_level=logging.DEBUG)
wfm.set_logger(logger)


def test_success_email():
    """성공 메일 전송 테스트"""
    logger.info("=" * 60)
    logger.info("성공 메일 전송 테스트 시작")
    logger.info("=" * 60)

    # 테스트 데이터
    test_email = "insung.lee@worksfree.kr"
    title = "[B2E] [TEST] Success First Try - 테스트 메일"
    content = """사용자: test@example.com\r\n
총 처리 대상 파일: 5개\r\n\r\n
=== 처리 결과 ===\r\n
• 1차 시도 성공: 5개 (100%)\r\n
• 재시도 필요 없음\r\n\r\n
=== 시간 정보 ===\r\n
총 소요 시간: 00:05:30\r\n\r\n
모든 파일이 1차 시도에서 성공적으로 처리되었습니다."""

    try:
        logger.info("Step 1: wfm.init() 호출")
        wfm.init(common_dir)
        logger.info("✅ wfm.init() 완료")

        logger.info("\nStep 2: 메일 전송 파라미터 확인")
        logger.info(f"  제목: {title}")
        logger.info(f"  수신자: {test_email}")
        logger.info(f"  첨부파일: None")

        logger.info("\nStep 3: wfm.mail_send_attach() 호출")
        wfm.mail_send_attach(title, test_email, content, None)

        logger.info("\n" + "=" * 60)
        logger.info("✅✅✅ 성공 메일 전송 테스트 성공! ✅✅✅")
        logger.info("=" * 60)
        logger.info(f"수신 메일함 확인: {test_email}")

        return True

    except Exception as e:
        logger.error("\n" + "=" * 60)
        logger.error("❌❌❌ 성공 메일 전송 테스트 실패! ❌❌❌")
        logger.error("=" * 60)
        logger.error(f"오류: {e}")

        import traceback

        logger.error(f"\n상세 오류:\n{traceback.format_exc()}")

        return False


if __name__ == "__main__":
    success = test_success_email()
    sys.exit(0 if success else 1)
