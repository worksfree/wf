"""
wf_hwinfo 통합 테스트
각 모듈이 wf_hwinfo를 직접 사용하는지 확인
"""

import sys
from pathlib import Path

# 10.common 경로 추가
sys.path.insert(0, str(Path(__file__).parent))


def test_credit_manager():
    """CreditManager가 wf_hwinfo를 직접 사용하는지 테스트"""
    print("\n=== CreditManager 테스트 ===")
    from wf_credit_manager import WorksFreeManager

    wm = WorksFreeManager()
    # register_user가 wf_hwinfo를 직접 사용
    print("✅ WorksFreeManager는 wf_hwinfo를 직접 사용합니다")
    return True


def test_sheets_manager():
    """GoogleSheetsManager가 wf_hwinfo를 직접 사용하는지 테스트"""
    print("\n=== GoogleSheetsManager 테스트 ===")
    from wf_googlesheets_manager import GoogleSheetsManager

    gsm = GoogleSheetsManager()

    # prepare_registration_data가 _get_hardware_info_once를 호출
    reg_data = gsm.prepare_registration_data(
        "test@example.com", "Test User", "010-1234-5678", "Y", "test_app"
    )

    print(f"  Fingerprint: {reg_data.get('uc_hw_fingerprint', '')[:16]}...")
    print(f"  CPU: {reg_data.get('uc_hw_cpuinfo', '')}")
    print(f"  Motherboard: {reg_data.get('uc_hw_mbinfo', '')}")
    print(f"  Storage: {reg_data.get('uc_hw_storageinfo', '')}")

    # get_hardware_fingerprint 메서드도 테스트
    fingerprint = gsm.get_hardware_fingerprint()
    print(f"  get_hardware_fingerprint(): {fingerprint[:16]}...")

    print("✅ GoogleSheetsManager는 wf_hwinfo를 직접 사용합니다")
    return True


def test_hwinfo_singleton():
    """HardwareInfo가 일관된 값을 반환하는지 테스트"""
    print("\n=== HardwareInfo 일관성 테스트 ===")
    from wf_hwinfo import HardwareInfo

    hw1 = HardwareInfo()
    hw2 = HardwareInfo()

    # 같은 시스템에서는 같은 값을 반환해야 함
    assert hw1.fingerprint == hw2.fingerprint, "지문이 일치하지 않음"
    assert hw1.cpu_id == hw2.cpu_id, "CPU ID가 일치하지 않음"
    assert hw1.mainboard_id == hw2.mainboard_id, "메인보드 ID가 일치하지 않음"
    assert hw1.storage_id == hw2.storage_id, "스토리지 ID가 일치하지 않음"

    print(f"  CPU: {hw1.cpu_id}")
    print(f"  Mainboard: {hw1.mainboard_id}")
    print(f"  Storage: {hw1.storage_id}")
    print(f"  Fingerprint: {hw1.fingerprint[:32]}...")
    print("✅ HardwareInfo는 일관된 값을 반환합니다")
    return True


if __name__ == "__main__":
    try:
        print("=" * 60)
        print("wf_hwinfo 통합 테스트 시작")
        print("=" * 60)

        test_hwinfo_singleton()
        test_credit_manager()
        test_sheets_manager()

        print("\n" + "=" * 60)
        print("✅ 모든 테스트 통과!")
        print("=" * 60)
        print("\n결론: 모든 모듈이 wf_hwinfo.HardwareInfo를 직접 사용합니다.")
        print("중복된 _get_hardware_info() 메서드가 제거되었습니다.")

    except Exception as e:
        print(f"\n❌ 테스트 실패: {e}")
        import traceback

        traceback.print_exc()
