"""
콘솔 창 깜빡임 원인 테스트
"""

import sys
import time

print("=" * 60)
print("콘솔 창 깜빡임 원인 테스트")
print("=" * 60)

# 1. cpuinfo 테스트
print("\n[1] cpuinfo 테스트 중...")
start = time.perf_counter()
try:
    import cpuinfo

    info = cpuinfo.get_cpu_info()
    elapsed = (time.perf_counter() - start) * 1000
    print(f"   ✓ cpuinfo 완료 ({elapsed:.1f}ms)")
    print(f"   CPU: {info.get('brand_raw', 'N/A')}")
except Exception as e:
    print(f"   ✗ cpuinfo 오류: {e}")

# 2. WMI 테스트
print("\n[2] WMI 테스트 중...")
start = time.perf_counter()
try:
    import wmi

    c = wmi.WMI()
    elapsed = (time.perf_counter() - start) * 1000
    print(f"   ✓ WMI 초기화 완료 ({elapsed:.1f}ms)")

    # 메인보드 정보
    for board in c.Win32_BaseBoard():
        print(f"   메인보드: {board.SerialNumber}")
        break

    # 디스크 정보
    for disk in c.Win32_DiskDrive():
        print(f"   디스크: {disk.SerialNumber}")
        break

except Exception as e:
    print(f"   ✗ WMI 오류: {e}")

# 3. HardwareInfo 싱글톤 테스트
print("\n[3] HardwareInfo 싱글톤 테스트 중...")
sys.path.insert(0, r"d:\drive_files\10.worksfree\10.rpa\10.common")
try:
    from wf_hwinfo import HardwareInfo

    # 첫 번째 호출
    start = time.perf_counter()
    hw1 = HardwareInfo()
    elapsed1 = (time.perf_counter() - start) * 1000
    print(f"   ✓ 첫 번째 호출: {elapsed1:.1f}ms")
    print(f"   CPU ID: {hw1.cpu_id[:30]}...")
    print(f"   MB ID: {hw1.mainboard_id}")
    print(f"   Storage ID: {hw1.storage_id[:30]}...")

    # 두 번째 호출 (싱글톤이면 즉시 반환)
    start = time.perf_counter()
    hw2 = HardwareInfo()
    elapsed2 = (time.perf_counter() - start) * 1000
    print(f"   ✓ 두 번째 호출: {elapsed2:.1f}ms (싱글톤 확인: {hw1 is hw2})")

except Exception as e:
    print(f"   ✗ HardwareInfo 오류: {e}")
    import traceback

    traceback.print_exc()

print("\n" + "=" * 60)
print("테스트 완료")
print("=" * 60)
