"""
하드웨어 정보 수집 성능 비교 테스트
Before: 4번 HardwareInfo() 생성 vs After: 1번 생성
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


def test_before_approach():
    """이전 방식: prepare_registration_data에서 4번 호출"""
    from wf_hwinfo import HardwareInfo

    start = time.perf_counter()

    # 이전 방식: 각 필드마다 HardwareInfo() 생성
    fingerprint = HardwareInfo().fingerprint
    cpu = HardwareInfo().cpu_id
    mb = HardwareInfo().mainboard_id
    storage = HardwareInfo().storage_id

    elapsed = time.perf_counter() - start
    return elapsed


def test_after_approach():
    """개선 방식: 한 번만 호출"""
    from wf_hwinfo import HardwareInfo

    start = time.perf_counter()

    # 개선 방식: 한 번만 생성
    hw = HardwareInfo()
    fingerprint = hw.fingerprint
    cpu = hw.cpu_id
    mb = hw.mainboard_id
    storage = hw.storage_id

    elapsed = time.perf_counter() - start
    return elapsed


def test_actual_sheets_manager():
    """실제 GoogleSheetsManager.prepare_registration_data() 성능"""
    from wf_googlesheets_manager import GoogleSheetsManager

    gsm = GoogleSheetsManager()

    start = time.perf_counter()
    data = gsm.prepare_registration_data(
        "test@example.com", "Test User", "010-1234-5678", "Y", "test_app"
    )
    elapsed = time.perf_counter() - start

    return elapsed, data


if __name__ == "__main__":
    print("=" * 60)
    print("하드웨어 정보 수집 성능 비교")
    print("=" * 60)

    # 워밍업
    test_after_approach()

    # Before 방식 (4번 생성)
    before_times = []
    for _ in range(5):
        before_times.append(test_before_approach())
    avg_before = sum(before_times) / len(before_times)

    # After 방식 (1번 생성)
    after_times = []
    for _ in range(5):
        after_times.append(test_after_approach())
    avg_after = sum(after_times) / len(after_times)

    print(f"\n📊 성능 비교 (5회 평균)")
    print(f"  Before (4번 생성): {avg_before*1000:.2f}ms")
    print(f"  After  (1번 생성): {avg_after*1000:.2f}ms")
    print(f"  개선율: {(avg_before - avg_after) / avg_before * 100:.1f}% 빠름")

    # 실제 사용 테스트
    print(f"\n📋 실제 prepare_registration_data() 테스트")
    actual_time, reg_data = test_actual_sheets_manager()
    print(f"  실행 시간: {actual_time*1000:.2f}ms")
    print(f"  데이터 필드: {len(reg_data)}개")
    print(f"  포함된 하드웨어 정보:")
    print(f"    - CPU: {reg_data.get('uc_hw_cpuinfo', 'N/A')[:30]}...")
    print(f"    - Mainboard: {reg_data.get('uc_hw_mbinfo', 'N/A')}")
    print(f"    - Storage: {reg_data.get('uc_hw_storageinfo', 'N/A')[:30]}...")
    print(f"    - Fingerprint: {reg_data.get('uc_hw_fingerprint', 'N/A')[:32]}...")

    print("\n" + "=" * 60)
    print("✅ 성능 테스트 완료")
    print("=" * 60)
