#!/usr/bin/env python3
"""자격증명 파일 경로 테스트 스크립트"""

import sys
from pathlib import Path

# 현재 디렉토리를 Python 경로에 추가
sys.path.append(str(Path(__file__).parent / "10.common"))

from wf_googlesheets_manager import CredentialsHelper


def test_credentials():
    print("=== 자격증명 파일 경로 테스트 ===")

    helper = CredentialsHelper()

    # 환경 정보 출력
    print(f"번들 환경: {helper._is_bundled()}")
    print(f"자격증명 디렉토리: {helper.credentials_dir}")

    # 개발 환경 경로 확인
    dev_dir = helper._get_dev_credentials_dir()
    print(f"개발환경 경로: {dev_dir}")
    if dev_dir:
        silver_files = list(dev_dir.glob(".silver-argon-*.json"))
        print(f"개발환경 silver 파일들: {silver_files}")

    # 번들 환경 경로 확인
    bundled_dir = helper._get_bundled_credentials_dir()
    print(f"번들환경 경로: {bundled_dir}")
    if bundled_dir:
        silver_files = list(bundled_dir.glob(".silver-argon-*.json"))
        print(f"번들환경 silver 파일들: {silver_files}")

    # 자격증명 확인 시도
    print(f"\n자격증명 확인 시도...")
    success = helper.ensure_user_credentials()
    print(f"자격증명 확인 결과: {success}")

    # 최종 경로 반환
    cred_path = helper.get_google_credentials_path()
    print(f"최종 자격증명 경로: {cred_path}")


if __name__ == "__main__":
    test_credentials()
