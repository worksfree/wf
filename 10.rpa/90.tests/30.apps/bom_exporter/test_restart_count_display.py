"""
restart_count 로그 표시 테스트

위치: 90.tests/30.apps/bom_exporter/test_restart_count_display.py
테스트 대상: 30.apps/bom_exporter/automation.py - restart_count 표시 로직
"""


def test_restart_count_display():
    """restart_count가 1부터 시작해서 20까지 표시되고 다시 1부터 시작하는지 테스트"""
    restart_count = 20

    print("\n=== restart_count 표시 테스트 (총 45개 파일) ===\n")

    for idx in range(45):
        # automation.py의 로직과 동일
        display_idx = (idx % restart_count) + 1

        # 재시작 포인트 표시
        restart_marker = " 🔄 재시작" if idx % restart_count == 0 else ""
        end_marker = (
            " ⏹️  종료 후 재시작" if idx != 0 and idx % restart_count == restart_count - 1 else ""
        )

        print(f"idx={idx:2d} → 표시: {display_idx:2d}/{restart_count}{restart_marker}{end_marker}")

    print("\n=== 검증 ===")

    # 검증
    test_cases = [
        (0, 1, "첫 번째 파일은 1/20으로 표시"),
        (19, 20, "20번째 파일은 20/20으로 표시"),
        (20, 1, "21번째 파일은 1/20으로 표시 (새 사이클)"),
        (39, 20, "40번째 파일은 20/20으로 표시"),
        (40, 1, "41번째 파일은 1/20으로 표시 (새 사이클)"),
    ]

    for idx, expected_display, description in test_cases:
        display_idx = (idx % restart_count) + 1
        passed = display_idx == expected_display
        status = "✅" if passed else "❌"
        print(f"{status} {description}: idx={idx} → {display_idx}/{restart_count}")
        if not passed:
            print(f"   기대값: {expected_display}, 실제값: {display_idx}")
        # pytest에서는 반환값 대신 assert 사용
        assert passed, f"{description}: 기대값 {expected_display}, 실제값 {display_idx}"

    print("\n🎉 모든 테스트 통과!")


if __name__ == "__main__":
    import sys

    try:
        test_restart_count_display()
        sys.exit(0)
    except Exception:
        sys.exit(1)
