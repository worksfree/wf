#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
사용자 홈 (~/.wf_rpa/) 하의 인증 테스트 데이터 정리 스크립트

인증 실행 전에 사용자 홈의 모든 앱 설정을 제거하여
순수한 DEV 설정만으로 테스트를 진행합니다.
"""

import os
import shutil
from pathlib import Path
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# 7개 앱 리스트
APPS = [
    "bom_exporter",
    "dwg_batch_print",
    "attribute_reset",
    "dwg_classifier",
    "conversion_verifier",
    "korean_filename_normalizer",
    "qrcode_generator",
]


def cleanup_user_home():
    """
    사용자 홈의 ~/.wf_rpa/{app_name}/ 디렉토리를 모두 제거합니다.
    인증 테스트 전에 호출하여 순수한 상태로 시작합니다.
    """
    user_home = Path.home()
    wf_rpa_dir = user_home / ".wf_rpa"
    
    logger.info(f"[CLEANUP] 사용자 홈 정리 시작: {wf_rpa_dir}")
    
    if not wf_rpa_dir.exists():
        logger.info(f"[CLEANUP] {wf_rpa_dir}가 존재하지 않으므로 스킵")
        return True
    
    try:
        for app_name in APPS:
            app_dir = wf_rpa_dir / app_name
            if app_dir.exists():
                logger.info(f"[CLEANUP] 제거 중: {app_dir}")
                shutil.rmtree(app_dir, ignore_errors=True)
                logger.info(f"✅ 제거 완료: {app_name}")
            else:
                logger.debug(f"[CLEANUP] {app_dir}가 없으므로 스킵")
        
        logger.info(f"[CLEANUP] ✅ 사용자 홈 정리 완료")
        return True
    
    except Exception as e:
        logger.error(f"[CLEANUP] ❌ 정리 중 오류: {e}")
        return False


if __name__ == "__main__":
    success = cleanup_user_home()
    exit(0 if success else 1)
