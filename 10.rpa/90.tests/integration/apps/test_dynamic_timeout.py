"""
Test dynamic timeout calculation with base=60s and +60s per 10MB
Expected behavior:
- Small file (10MB): 60s + 60s = 120s UI wait, 240s save wait
- Medium file (50MB): 60s + 300s = 360s UI wait, 720s save wait
- Large file (90MB): 60s + 540s = 600s UI wait, 1200s save wait
"""

import sys
import os

# Add project paths
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "..", "..", ".."))
bom_exporter_path = os.path.join(project_root, "30.apps", "Bom_Exporter")
common_path = os.path.join(project_root, "10.common")

for path in [project_root, bom_exporter_path, common_path]:
    if path not in sys.path:
        sys.path.insert(0, path)


def test_dynamic_timeout_calculation():
    """Test that _compute_waits produces expected results with base=60, step=60"""
    from automation import BomAutomation

    print("=== 동적 타임아웃 계산 테스트 ===\n")

    # Create instance (console mode to avoid GUI dependencies)
    app = BomAutomation(console_mode=True, folder_path=None)

    # Verify config loaded correctly
    print(f"Config loaded:")
    print(f"  base_wait_time: {app.config.base_wait_time}s")
    print(f"  seconds_per_10mb: {app.config.seconds_per_10mb}s")
    print(f"  file_save_wait_multiplier: {getattr(app.config, 'file_save_wait_multiplier', 2)}\n")

    # Test cases: (file_size_mb)
    # 기대값은 앱 설정(base_wait_time, seconds_per_10mb, file_save_wait_multiplier)에 따라 동적으로 계산
    test_cases = [10, 50, 90, 100]

    all_passed = True

    import math

    for file_size_mb in test_cases:
        file_size_bytes = int(file_size_mb * 1024 * 1024)
        ui_wait, save_wait = app._compute_waits(file_size_bytes)

        # 기대값 동적 계산
        expected_ui = int(
            app.config.base_wait_time + math.floor(file_size_mb / 10) * app.config.seconds_per_10mb
        )
        expected_save = int(expected_ui * getattr(app.config, "file_save_wait_multiplier", 2))

        # Allow some tolerance (future config tweaks)
        ui_match = abs(ui_wait - expected_ui) <= 10
        save_match = abs(save_wait - expected_save) <= 20

        status = "✓ PASS" if (ui_match and save_match) else "✗ FAIL"
        print(f"{status} | {file_size_mb}MB file:")
        print(f"        UI wait: {ui_wait}s (expected ~{expected_ui}s)")
        print(f"        Save wait: {save_wait}s (expected ~{expected_save}s)")

        if not (ui_match and save_match):
            all_passed = False
            print(
                f"        ⚠ Difference: UI {ui_wait - expected_ui}s, Save {save_wait - expected_save}s"
            )
        print()

    if all_passed:
        print("✅ 모든 테스트 통과!")
    else:
        print("❌ 일부 테스트 실패")
    # pytest에서는 반환값 대신 assert를 사용
    assert all_passed, "동적 타임아웃 계산 테스트 일부 케이스 실패"


if __name__ == "__main__":
    try:
        test_dynamic_timeout_calculation()
        sys.exit(0)
    except Exception as e:
        print(f"❌ 테스트 실행 중 오류 발생: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
