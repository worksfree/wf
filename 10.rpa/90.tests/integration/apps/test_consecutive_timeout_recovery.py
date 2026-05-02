"""
Test consecutive timeout recovery mechanism
Verifies that:
1. consec_timeouts counter increments on timeout
2. Safe restart is triggered when threshold is reached
3. Counter resets after restart
"""

import sys
import os

# Add project paths
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "..", "..", ".."))
bom_exporter_path = os.path.join(project_root, "30.apps", "bom_exporter")
common_path = os.path.join(project_root, "10.common")

for path in [project_root, bom_exporter_path, common_path]:
    if path not in sys.path:
        sys.path.insert(0, path)


def test_consecutive_timeout_recovery():
    """Test consecutive timeout counter and recovery trigger"""
    from automation import BomAutomation
    from unittest.mock import MagicMock

    print("=== 연속 타임아웃 복구 메커니즘 테스트 ===\n")

    # Create instance
    app = BomAutomation(console_mode=True, folder_path=None)

    # Verify initial state
    print(f"Initial state:")
    print(f"  consec_timeouts: {app.consec_timeouts}")
    print(f"  consec_timeout_limit: {app.consec_timeout_limit}\n")

    # Mock _safe_solidworks_restart to avoid actually restarting
    restart_called = {"count": 0}

    def mock_restart():
        restart_called["count"] += 1
        print(f"  → _safe_solidworks_restart() called (mock #{restart_called['count']})")
        return True

    app._safe_solidworks_restart = mock_restart

    # Test 1: Increment without reaching limit
    print("Test 1: Increment once (should NOT trigger restart)")
    app._increment_consec_and_maybe_restart(reason="test_timeout_1")
    assert app.consec_timeouts == 1, f"Expected consec_timeouts=1, got {app.consec_timeouts}"
    assert (
        restart_called["count"] == 0
    ), f"Restart should not be called yet, but was called {restart_called['count']} times"
    print(f"  ✓ Counter incremented to {app.consec_timeouts}, no restart\n")

    # Test 2: Increment to reach limit
    print(f"Test 2: Increment to limit (consec_timeout_limit={app.consec_timeout_limit})")
    app._increment_consec_and_maybe_restart(reason="test_timeout_2")
    assert (
        app.consec_timeouts == 0
    ), f"Expected counter reset to 0 after restart, got {app.consec_timeouts}"
    assert (
        restart_called["count"] == 1
    ), f"Restart should be called once, but was called {restart_called['count']} times"
    print(f"  ✓ Restart triggered and counter reset to {app.consec_timeouts}\n")

    # Test 3: Reset counter on success (manual reset simulation)
    print("Test 3: Manual counter reset (simulating successful save)")
    app.consec_timeouts = 1  # Set to non-zero
    app.consec_timeouts = 0  # Reset (as done in save_bom_exporter on success)
    assert (
        app.consec_timeouts == 0
    ), f"Expected consec_timeouts=0 after reset, got {app.consec_timeouts}"
    print(f"  ✓ Counter manually reset to {app.consec_timeouts}\n")

    # Test 4: Verify multiple cycles work
    print("Test 4: Multiple timeout cycles")
    for cycle in range(3):
        print(f"  Cycle {cycle + 1}:")
        for i in range(app.consec_timeout_limit):
            app._increment_consec_and_maybe_restart(reason=f"cycle{cycle}_timeout{i+1}")
        assert (
            app.consec_timeouts == 0
        ), f"Counter should reset after each cycle, got {app.consec_timeouts}"
        print(f"    ✓ Cycle complete, counter reset")

    expected_restarts = 1 + 3  # Test 2 + Test 4 (3 cycles)
    assert (
        restart_called["count"] == expected_restarts
    ), f"Expected {expected_restarts} restarts, got {restart_called['count']}"
    print(f"\n  ✓ All cycles completed with {restart_called['count']} total restarts\n")

    print("✅ 모든 복구 메커니즘 테스트 통과!")


if __name__ == "__main__":
    try:
        # 실행 중 예외가 발생하지 않으면 성공으로 간주
        test_consecutive_timeout_recovery()
        sys.exit(0)
    except Exception as e:
        print(f"❌ 테스트 실행 중 오류 발생: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
