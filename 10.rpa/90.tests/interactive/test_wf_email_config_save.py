"""
이메일 설정이 로컬에 저장되는지 테스트

위치: 90.tests/10.common/test_wf_email_config_save.py
테스트 대상: 10.common/wf_email.py - init() 함수의 로컬 저장 기능
"""

import sys
import os
import json
from pathlib import Path

# 경로 설정 (90.tests/10.common -> 10.common)
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
common_dir = os.path.join(project_root, "10.common")
sys.path.insert(0, common_dir)

import wf_email as wfm
import wf_log as wflog
import logging

# 로거 설정
logger = wflog.get_app_logger("test_email_config", console_level=logging.DEBUG)
wfm.set_logger(logger)


def test_email_config_save():
    """이메일 설정 저장 테스트"""
    logger.info("=" * 60)
    logger.info("이메일 설정 로컬 저장 테스트")
    logger.info("=" * 60)

    config_file = Path.home() / ".wf_rpa" / ".wf_rpa_config.json"

    # 기존 설정 파일 백업
    logger.info(f"\n1. 설정 파일 위치: {config_file}")
    if config_file.exists():
        logger.info("   설정 파일 존재함")
        with open(config_file, "r", encoding="utf-8") as f:
            before_config = json.load(f)
        logger.info(f'   기존 email_settings: {before_config.get("email_settings", {})}')
    else:
        logger.info("   설정 파일 없음 (새로 생성됨)")
        before_config = {}

    # 이메일 설정을 초기화 (로컬 설정 제거)
    logger.info("\n2. 로컬 이메일 설정 초기화...")
    if config_file.exists():
        with open(config_file, "r", encoding="utf-8") as f:
            config = json.load(f)
        config["email_settings"] = {
            "use_local_email_config": False,
            "email_from": "",
            "email_to": "",
            "smtp_server": "smtp.gmail.com",
            "smtp_port": 587,
            "login_key": "",
        }
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        logger.info("   ✅ 로컬 설정 초기화 완료")

    # wfm.init() 실행 (구글 시트에서 로드 → 로컬 저장)
    logger.info("\n3. wfm.init() 실행 (구글 시트 → 로컬 저장)...")
    try:
        wfm.init(common_dir)
        logger.info("   ✅ wfm.init() 완료")
    except Exception as e:
        logger.error(f"   ❌ wfm.init() 실패: {e}")
        return False

    # 저장된 설정 확인
    logger.info("\n4. 저장된 설정 확인...")
    if config_file.exists():
        with open(config_file, "r", encoding="utf-8") as f:
            after_config = json.load(f)

        email_settings = after_config.get("email_settings", {})
        logger.info(f'   email_from: {email_settings.get("email_from", "없음")}')
        logger.info(f'   email_to: {email_settings.get("email_to", "없음")}')
        logger.info(f'   smtp_server: {email_settings.get("smtp_server", "없음")}')
        logger.info(f'   smtp_port: {email_settings.get("smtp_port", "없음")}')
        logger.info(f'   login_key 저장됨: {"예" if email_settings.get("login_key") else "아니오"}')

        # 검증
        if all(
            [
                email_settings.get("email_from"),
                email_settings.get("email_to"),
                email_settings.get("smtp_server"),
                email_settings.get("smtp_port"),
                email_settings.get("login_key"),
            ]
        ):
            logger.info("\n" + "=" * 60)
            logger.info("✅✅✅ 테스트 성공! 이메일 설정이 로컬에 저장되었습니다.")
            logger.info("=" * 60)
            logger.info("다음 실행부터는 구글 시트 조회 없이 빠르게 로드됩니다.")
            return True
        else:
            logger.error("\n" + "=" * 60)
            logger.error("❌ 테스트 실패! 일부 설정이 저장되지 않았습니다.")
            logger.error("=" * 60)
            return False
    else:
        logger.error("   ❌ 설정 파일이 생성되지 않았습니다.")
        return False


if __name__ == "__main__":
    success = test_email_config_save()
    sys.exit(0 if success else 1)
