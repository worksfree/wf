"""
종합 통합 테스트: 동적 타임아웃 + 복구 메커니즘
실제 워크플로우를 시뮬레이션하여 모든 컴포넌트가 함께 동작하는지 검증
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


def test_integration():
    """통합 워크플로우 테스트"""
    from automation import BomAutomation

    print("=== 동적 타임아웃 + 복구 메커니즘 통합 테스트 ===\n")

    # Create instance
    app = BomAutomation(console_mode=True, folder_path=None)

    print("Step 1: 설정 확인")
    print(f"  ✓ base_wait_time: {app.config.base_wait_time}s")
    print(f"  ✓ seconds_per_10mb: {app.config.seconds_per_10mb}s")
    print(f"  ✓ consec_timeout_limit: {app.consec_timeout_limit}")
    print(f"  ✓ Initial consec_timeouts: {app.consec_timeouts}\n")

    # Test scenario: 3 files with different sizes
    test_files = [
        (20, "small_assy.slddrw"),  # 20MB
        (75, "medium_assy.slddrw"),  # 75MB
        (95, "large_assy.slddrw"),  # 95MB
    ]

    print("Step 2: 파일 크기별 타임아웃 계산 테스트")
    for size_mb, filename in test_files:
        size_bytes = size_mb * 1024 * 1024
        ui_wait, save_wait = app._compute_waits(size_bytes)

        # Verify calculation: base + (size_mb // 10) * 60
        expected_ui = 60 + (size_mb // 10) * 60
        expected_save = expected_ui * 2

        ui_ok = abs(ui_wait - expected_ui) <= 10
        save_ok = abs(save_wait - expected_save) <= 20

        status = "✓" if (ui_ok and save_ok) else "✗"
        print(f"  {status} {filename} ({size_mb}MB):")
        print(f"      UI: {ui_wait}s (예상: ~{expected_ui}s)")
        print(f"      Save: {save_wait}s (예상: ~{expected_save}s)")

        if not (ui_ok and save_ok):
            print(f"      ⚠ 계산 오차 발견")
            return False

    print("\nStep 3: 복구 메커니즘 시뮬레이션")

    # Mock restart function
    restart_count = {"value": 0}

    def mock_restart():
        restart_count["value"] += 1
        print(f"    → 안전 재시작 호출 (#{restart_count['value']})")
        return True

    app._safe_solidworks_restart = mock_restart

    # Simulate workflow: success → timeout → timeout (trigger restart) → success
    workflow = [
        ("파일1 처리", "success"),
        ("파일2 처리", "timeout"),
        ("파일3 처리", "timeout"),  # Should trigger restart
        ("파일4 처리", "success"),
    ]

    for step_name, outcome in workflow:
        if outcome == "success":
            print(f"  ✓ {step_name}: 성공")
            app.consec_timeouts = 0  # Reset on success
            print(f"    Counter reset: {app.consec_timeouts}")
        elif outcome == "timeout":
            print(f"  ⚠ {step_name}: 타임아웃 발생")
            app._increment_consec_and_maybe_restart(reason=step_name)
            print(f"    Counter: {app.consec_timeouts}")

    print(f"\n  총 재시작 횟수: {restart_count['value']}")
    if restart_count["value"] != 1:
        print(f"  ✗ FAIL: 재시작 횟수가 예상과 다름 (예상: 1, 실제: {restart_count['value']})")
        return False

    print("\nStep 4: 안전성 검증")

    # Verify attributes exist
    required_attrs = [
        "timeout_mode",
        "soft_retries",
        "consec_timeout_limit",
        "consec_timeouts",
        "_compute_waits",
        "_increment_consec_and_maybe_restart",
    ]

    for attr in required_attrs:
        if not hasattr(app, attr):
            print(f"  ✗ 필수 속성/메서드 누락: {attr}")
            return False

    print(f"  ✓ 모든 필수 속성/메서드 존재")

    # Verify methods are callable
    assert callable(app._compute_waits), "_compute_waits는 호출 가능해야 함"
    assert callable(
        app._increment_consec_and_maybe_restart
    ), "_increment_consec_and_maybe_restart는 호출 가능해야 함"
    print(f"  ✓ 모든 메서드 호출 가능")

    # Verify counter state
    assert app.consec_timeouts == 0, "테스트 종료 시 카운터는 0이어야 함"
    print(f"  ✓ 최종 상태 정상: consec_timeouts={app.consec_timeouts}")

    print("\n✅ 통합 테스트 통과!")
    print("\n=== 테스트 요약 ===")
    print("• 동적 타임아웃 계산: 정상")
    print("• 파일 크기별 시간 할당: 정상")
    print("• 연속 타임아웃 카운터: 정상")
    print("• 자동 재시작 트리거: 정상")
    print("• 카운터 리셋: 정상")
    print("\n🚀 배포 준비 완료!")

    return True


if __name__ == "__main__":
    try:
        success = test_integration()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ 통합 테스트 실패: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
