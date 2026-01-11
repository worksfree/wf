# -*- coding: utf-8 -*-
"""
숨김 처리 테스트 스크립트
개발 모드 vs 배포 모드에서 숨김 속성 확인
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path

# 10.common 경로 추가
current_dir = Path(__file__).parent
common_path = current_dir / "10.common"
sys.path.insert(0, str(common_path))

from wf_credit_manager import WorksFreeManager, CreditManager
from wf_log import get_app_logger, set_logger
import logging


def check_hidden_attribute(path: Path) -> bool:
    """Windows에서 숨김 속성 확인"""
    try:
        import platform

        if platform.system() == "Windows":
            import ctypes

            FILE_ATTRIBUTE_HIDDEN = 0x02
            attrs = ctypes.windll.kernel32.GetFileAttributesW(str(path))
            return (attrs & FILE_ATTRIBUTE_HIDDEN) != 0
        else:
            # Linux/Mac: . 으로 시작하면 숨김
            return path.name.startswith(".")
    except Exception as e:
        print(f"숨김 속성 확인 오류: {e}")
        return False


def test_dev_mode():
    """개발 모드 테스트 - 숨김 처리 안 됨"""
    print("\n" + "=" * 60)
    print("🔧 개발 모드 테스트 (WF_RPA_HOME 설정)")
    print("=" * 60)

    # 임시 디렉토리 생성
    temp_dir = Path(tempfile.mkdtemp(prefix="wf_dev_"))
    os.environ["WF_RPA_HOME"] = str(temp_dir)

    try:
        # 로거 초기화
        logger = get_app_logger("test_hidden", console_level=logging.DEBUG)
        set_logger(logger)

        # WorksFreeManager 생성 (싱글톤 초기화)
        wf_manager = WorksFreeManager()
        print(f"✓ WF_RPA_HOME: {temp_dir}")
        print(f"✓ is_dev_mode: {wf_manager.is_dev_mode}")

        # CreditManager 생성
        credit_manager = CreditManager("test_app", "test@example.com")

        # 파일/폴더 생성 확인
        wf_rpa_dir = temp_dir
        config_file = wf_rpa_dir / ".wf_rpa_config.json"
        app_dir = wf_rpa_dir / "test_app"
        credit_file = app_dir / ".test_app_credits.json"

        print(f"\n📂 생성된 구조:")
        print(f"  {wf_rpa_dir}")
        print(f"  ├── {config_file.name} {'✓' if config_file.exists() else '✗'}")
        print(f"  └── test_app/")
        print(f"      └── {credit_file.name} {'✓' if credit_file.exists() else '✗'}")

        # 숨김 속성 확인
        print(f"\n🔍 숨김 속성 확인 (개발 모드: 모두 False여야 함):")

        results = []
        if wf_rpa_dir.exists():
            is_hidden = check_hidden_attribute(wf_rpa_dir)
            results.append(("wf_rpa_dir", is_hidden, False))
            print(
                f"  폴더 {wf_rpa_dir.name}: {'🔒 숨김' if is_hidden else '👁️ 보임'} {'❌ 실패!' if is_hidden else '✅'}"
            )

        if config_file.exists():
            is_hidden = check_hidden_attribute(config_file)
            results.append(("config_file", is_hidden, False))
            print(
                f"  파일 {config_file.name}: {'🔒 숨김' if is_hidden else '👁️ 보임'} {'❌ 실패!' if is_hidden else '✅'}"
            )

        if app_dir.exists():
            is_hidden = check_hidden_attribute(app_dir)
            results.append(("app_dir", is_hidden, False))
            print(
                f"  폴더 {app_dir.name}: {'🔒 숨김' if is_hidden else '👁️ 보임'} {'❌ 실패!' if is_hidden else '✅'}"
            )

        if credit_file.exists():
            is_hidden = check_hidden_attribute(credit_file)
            results.append(("credit_file", is_hidden, False))
            print(
                f"  파일 {credit_file.name}: {'🔒 숨김' if is_hidden else '👁️ 보임'} {'❌ 실패!' if is_hidden else '✅'}"
            )

        # 결과 판정
        all_passed = all(actual == expected for _, actual, expected in results)
        if all_passed:
            print(f"\n✅ 개발 모드 테스트 성공: 모든 항목이 보임 상태!")
        else:
            print(f"\n❌ 개발 모드 테스트 실패: 일부 항목이 숨김 처리됨!")

        return all_passed

    finally:
        # 정리
        del os.environ["WF_RPA_HOME"]
        shutil.rmtree(temp_dir, ignore_errors=True)
        print(f"\n🧹 임시 폴더 삭제: {temp_dir}")


def test_release_mode():
    """배포 모드 테스트 - 숨김 처리됨"""
    print("\n" + "=" * 60)
    print("📦 배포 모드 테스트 (WF_RPA_HOME 없음)")
    print("=" * 60)

    # 임시 홈 디렉토리 생성
    temp_home = Path(tempfile.mkdtemp(prefix="wf_release_"))
    original_home = os.environ.get("HOME") or os.environ.get("USERPROFILE")

    # USERPROFILE을 임시 경로로 변경 (실제 홈 오염 방지)
    os.environ["USERPROFILE"] = str(temp_home)

    # WF_RPA_HOME 삭제 (배포 모드)
    if "WF_RPA_HOME" in os.environ:
        del os.environ["WF_RPA_HOME"]

    try:
        # WorksFreeManager 싱글톤 초기화 상태 리셋 (새로운 인스턴스 생성을 위해)
        WorksFreeManager._instance = None
        if hasattr(WorksFreeManager._instance, "_initialized"):
            delattr(WorksFreeManager._instance, "_initialized")

        # 로거 초기화
        logger = get_app_logger("test_hidden", console_level=logging.DEBUG)
        set_logger(logger)

        # WorksFreeManager 생성
        wf_manager = WorksFreeManager()
        print(f"✓ USERPROFILE: {temp_home}")
        print(f"✓ is_dev_mode: {wf_manager.is_dev_mode}")

        # CreditManager 생성
        credit_manager = CreditManager("test_app", "test@example.com")

        # 파일/폴더 생성 확인
        wf_rpa_dir = temp_home / ".wf_rpa"
        config_file = wf_rpa_dir / ".wf_rpa_config.json"
        app_dir = wf_rpa_dir / "test_app"
        credit_file = app_dir / ".test_app_credits.json"

        print(f"\n📂 생성된 구조:")
        print(f"  {wf_rpa_dir}")
        print(f"  ├── {config_file.name} {'✓' if config_file.exists() else '✗'}")
        print(f"  └── test_app/")
        print(f"      └── {credit_file.name} {'✓' if credit_file.exists() else '✗'}")

        # 숨김 속성 확인
        print(f"\n🔍 숨김 속성 확인 (배포 모드: 모두 True여야 함):")

        results = []
        if wf_rpa_dir.exists():
            is_hidden = check_hidden_attribute(wf_rpa_dir)
            results.append(("wf_rpa_dir", is_hidden, True))
            print(
                f"  폴더 {wf_rpa_dir.name}: {'🔒 숨김' if is_hidden else '👁️ 보임'} {'✅' if is_hidden else '❌ 실패!'}"
            )

        if config_file.exists():
            is_hidden = check_hidden_attribute(config_file)
            results.append(("config_file", is_hidden, True))
            print(
                f"  파일 {config_file.name}: {'🔒 숨김' if is_hidden else '👁️ 보임'} {'✅' if is_hidden else '❌ 실패!'}"
            )

        if app_dir.exists():
            is_hidden = check_hidden_attribute(app_dir)
            results.append(("app_dir", is_hidden, True))
            print(
                f"  폴더 {app_dir.name}: {'🔒 숨김' if is_hidden else '👁️ 보임'} {'✅' if is_hidden else '❌ 실패!'}"
            )

        if credit_file.exists():
            is_hidden = check_hidden_attribute(credit_file)
            results.append(("credit_file", is_hidden, True))
            print(
                f"  파일 {credit_file.name}: {'🔒 숨김' if is_hidden else '👁️ 보임'} {'✅' if is_hidden else '❌ 실패!'}"
            )

        # 결과 판정
        all_passed = all(actual == expected for _, actual, expected in results)
        if all_passed:
            print(f"\n✅ 배포 모드 테스트 성공: 모든 항목이 숨김 처리됨!")
        else:
            print(f"\n❌ 배포 모드 테스트 실패: 일부 항목이 보임 상태!")

        return all_passed

    finally:
        # 정리
        os.environ["USERPROFILE"] = original_home
        shutil.rmtree(temp_home, ignore_errors=True)
        print(f"\n🧹 임시 홈 폴더 삭제: {temp_home}")

        # 싱글톤 리셋
        WorksFreeManager._instance = None


def main():
    """메인 테스트 실행"""
    print("🧪 숨김 처리 자동 테스트 시작")
    print("=" * 60)

    results = []

    # 개발 모드 테스트
    try:
        dev_passed = test_dev_mode()
        results.append(("개발 모드", dev_passed))
    except Exception as e:
        print(f"\n❌ 개발 모드 테스트 오류: {e}")
        import traceback

        traceback.print_exc()
        results.append(("개발 모드", False))

    # 배포 모드 테스트
    try:
        release_passed = test_release_mode()
        results.append(("배포 모드", release_passed))
    except Exception as e:
        print(f"\n❌ 배포 모드 테스트 오류: {e}")
        import traceback

        traceback.print_exc()
        results.append(("배포 모드", False))

    # 최종 결과
    print("\n" + "=" * 60)
    print("📊 테스트 결과 요약")
    print("=" * 60)
    for name, passed in results:
        status = "✅ 성공" if passed else "❌ 실패"
        print(f"  {name}: {status}")

    all_passed = all(passed for _, passed in results)
    if all_passed:
        print("\n🎉 모든 테스트 통과!")
    else:
        print("\n⚠️ 일부 테스트 실패!")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
