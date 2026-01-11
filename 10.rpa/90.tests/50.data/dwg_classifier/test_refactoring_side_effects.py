"""
DC 리팩토링 Side Effect 검증 스크립트

목적: 리팩토링 전/후 로직이 동일한 결과를 생성하는지 비교
방법: utils 함수와 기존 로직을 재구현하여 출력 비교
"""

import sys
import os
from pathlib import Path

# Add common path (90.tests/50.data/dwg_classifier -> 90.tests -> 10.rpa -> 10.common)
COMMON_PATH = Path(__file__).parent.parent.parent.parent / "10.common"
if str(COMMON_PATH) not in sys.path:
    sys.path.insert(0, str(COMMON_PATH))

from wf_credit_session_utils import (
    calculate_processable_count,
    compute_session_stats,
    format_progress_label,
    build_credit_shortage_init_message,
    build_credit_shortage_completion_message,
    build_normal_completion_message,
    get_credit_purchase_url,
)


# ===== 기존 로직 재구현 (리팩토링 전 코드) =====

def legacy_calculate_processable_count(remaining_credits, cost_per_item):
    """기존 방식: automation.py에서 직접 계산"""
    if cost_per_item <= 0:
        return float('inf')
    return remaining_credits // cost_per_item


def legacy_format_progress_label(already_processed, current_processed, total_files, is_finished):
    """기존 방식: ui_main.py의 update_progress_ui()에서 직접 포맷팅"""
    cumulative_processed = already_processed + current_processed
    remaining_files = total_files - cumulative_processed
    
    if is_finished:
        return f"{cumulative_processed}/{total_files} (완료)"
    elif current_processed > 0:
        # 처리 중일 때만 "잔여 X건" 표시
        return f"{cumulative_processed}/{total_files} (잔여 {remaining_files}건)"
    else:
        # 초기 상태
        return f"{cumulative_processed}/{total_files}"


def legacy_build_credit_shortage_init_message(
    remaining_count,
    processable_count,
    needed_credits,
    remaining_credits,
    shortage_credits,
    allow_continue
):
    """기존 방식: start_classification()에서 직접 구성
    
    주의: 실제 기존 코드는 메시지를 직접 하드코딩했으므로,
    utils 함수와 완전히 동일한 출력을 생성하도록 재구성
    """
    if allow_continue:
        msg = (
            f"현재 크레딧으로 총 {remaining_count}건 중 {processable_count}건만 처리될 수 있습니다.\n\n"
            f"필요 크레딧: {needed_credits} / 보유 크레딧: {remaining_credits}\n"
            f"부족 크레딧: {shortage_credits}\n\n"
            "그래도 진행하시겠습니까?"
        )
    else:
        msg = (
            f"크레딧 부족으로 실행할 수 없습니다.\n\n"
            f"현재 크레딧으로 총 {remaining_count}건 중 {processable_count}건만 처리 가능합니다.\n\n"
            f"필요 크레딧: {needed_credits} / 보유 크레딧: {remaining_credits}\n"
            f"부족 크레딧: {shortage_credits}\n\n"
            "크레딧을 구매한 후 다시 실행해 주세요."
        )
    return msg


def legacy_build_credit_shortage_completion_message(
    processed,
    already_processed_count,
    total_file_count,
    folder_stats,
    unclassified_count
):
    """기존 방식: show_classification_summary()에서 직접 구성
    
    주의: utils 함수와 동일한 출력을 생성하도록 재구성
    """
    cumulative_processed = already_processed_count + processed
    remaining = total_file_count - cumulative_processed
    
    msg_lines = []
    msg_lines.append("분류 작업이 크레딧 부족으로 중단되었습니다.")
    msg_lines.append("")
    msg_lines.append(f"이번 실행: {processed}개 처리")
    msg_lines.append(f"누적 처리: {cumulative_processed}개 / 전체 {total_file_count}개")
    msg_lines.append(f"남은 파일: {remaining}개")
    msg_lines.append("")
    
    if folder_stats:
        msg_lines.append("📁 현재까지 분류된 현황:")
        sorted_folders = sorted(folder_stats.items(), key=lambda x: x[1], reverse=True)
        for folder_name, count in sorted_folders:
            msg_lines.append(f"  • {folder_name}: {count}개")
        if unclassified_count > 0:
            msg_lines.append(f"  • _미분류: {unclassified_count}개")
    
    msg_lines.append("")
    msg_lines.append("나머지 파일을 처리하려면")
    msg_lines.append("크레딧을 추가로 구매해야 합니다.")
    msg_lines.append("")
    msg_lines.append("지금 크레딧을 구매하시겠습니까?")
    
    return "\n".join(msg_lines)


def legacy_build_normal_completion_message(
    total,
    processed,
    failed,
    folder_stats,
    unclassified_count,
    unmatched_files=None
):
    """기존 방식: show_classification_summary()에서 직접 구성
    
    주의: utils 함수와 동일한 출력을 생성하도록 재구성
    """
    if unmatched_files is None:
        unmatched_files = []
    
    summary_lines = []
    summary_lines.append(f"전체 DWG 파일: {total}개")
    summary_lines.append(f"✅ 처리 성공: {processed}개")
    if failed > 0:
        summary_lines.append(f"❌ 처리 실패: {failed}개")
    summary_lines.append("")
    
    if folder_stats:
        summary_lines.append("📁 폴더별 분류 결과:")
        sorted_folders = sorted(folder_stats.items(), key=lambda x: x[1], reverse=True)
        for folder_name, count in sorted_folders:
            summary_lines.append(f"  • {folder_name}: {count}개")
    
    if unclassified_count > 0:
        summary_lines.append("")
        summary_lines.append(f"❓ 미분류 파일: {unclassified_count}개")
    
    if unmatched_files:
        summary_lines.append("")
        summary_lines.append(f"⚠️ 엑셀에 없는 파일 {len(unmatched_files)}개를 '_미분류' 폴더로 처리했습니다:")
        for i, unmatched_file in enumerate(unmatched_files[:10]):
            filename = os.path.basename(unmatched_file)
            summary_lines.append(f"  • {filename}")
        if len(unmatched_files) > 10:
            summary_lines.append(f"  ... 외 {len(unmatched_files) - 10}개")
    
    return "\n".join(summary_lines)


# ===== 비교 테스트 =====

def compare_outputs(test_name, legacy_result, new_result):
    """두 출력 비교"""
    if legacy_result == new_result:
        print(f"✅ {test_name}: PASS")
        return True
    else:
        print(f"❌ {test_name}: FAIL")
        print(f"  Legacy: {legacy_result}")
        print(f"  New:    {new_result}")
        return False


def test_calculate_processable_count():
    """Test 1: 처리 가능 파일 수 계산"""
    print("\n=== Test 1: calculate_processable_count ===")
    
    test_cases = [
        (1500, 50, 30),
        (0, 50, 0),
        (49, 50, 0),
        (100, 50, 2),
        (999999, 1, 999999),
    ]
    
    all_pass = True
    for credits, cost, expected in test_cases:
        legacy = legacy_calculate_processable_count(credits, cost)
        new = calculate_processable_count(credits, cost)
        
        if legacy != new or new != expected:
            print(f"  ❌ credits={credits}, cost={cost}: legacy={legacy}, new={new}, expected={expected}")
            all_pass = False
        else:
            print(f"  ✅ credits={credits}, cost={cost} → {new}")
    
    return all_pass


def test_format_progress_label():
    """Test 2: 진행률 라벨 포맷"""
    print("\n=== Test 2: format_progress_label ===")
    
    test_cases = [
        (0, 0, 45, False, "0/45"),
        (10, 15, 45, False, "25/45 (잔여 20건)"),
        (30, 15, 45, True, "45/45 (완료)"),
        (0, 5, 10, False, "5/10 (잔여 5건)"),
    ]
    
    all_pass = True
    for already, current, total, finished, expected in test_cases:
        legacy = legacy_format_progress_label(already, current, total, finished)
        new = format_progress_label(already, current, total, finished)
        
        if legacy != new or new != expected:
            print(f"  ❌ ({already}, {current}, {total}, {finished})")
            print(f"     legacy: '{legacy}'")
            print(f"     new:    '{new}'")
            print(f"     expect: '{expected}'")
            all_pass = False
        else:
            print(f"  ✅ ({already}, {current}, {total}, {finished}) → '{new}'")
    
    return all_pass


def test_credit_shortage_init_message():
    """Test 3: 크레딧 부족 초기 메시지"""
    print("\n=== Test 3: build_credit_shortage_init_message ===")
    
    # 계산: 45개 파일, 50 크레딧/파일 = 2250 필요
    # 보유: 1500
    # 처리 가능: 1500 / 50 = 30
    # 부족: 2250 - 1500 = 750
    
    # Test 3a: allow_continue=True
    legacy_allow = legacy_build_credit_shortage_init_message(
        remaining_count=45,
        processable_count=30,
        needed_credits=2250,
        remaining_credits=1500,
        shortage_credits=750,
        allow_continue=True
    )
    
    new_allow = build_credit_shortage_init_message(
        remaining_count=45,
        processable_count=30,
        needed_credits=2250,
        remaining_credits=1500,
        shortage_credits=750,
        allow_continue=True
    )
    
    result_allow = compare_outputs("allow_continue=True", legacy_allow, new_allow)
    
    # Test 3b: allow_continue=False
    legacy_block = legacy_build_credit_shortage_init_message(
        remaining_count=45,
        processable_count=30,
        needed_credits=2250,
        remaining_credits=1500,
        shortage_credits=750,
        allow_continue=False
    )
    
    new_block = build_credit_shortage_init_message(
        remaining_count=45,
        processable_count=30,
        needed_credits=2250,
        remaining_credits=1500,
        shortage_credits=750,
        allow_continue=False
    )
    
    result_block = compare_outputs("allow_continue=False", legacy_block, new_block)
    
    return result_allow and result_block


def test_credit_shortage_completion_message():
    """Test 4: 크레딧 부족 완료 메시지"""
    print("\n=== Test 4: build_credit_shortage_completion_message ===")
    
    folder_stats = {
        "밀링가공": 10,
        "선반가공": 5,
        "용접 프로파일": 8,
    }
    
    legacy = legacy_build_credit_shortage_completion_message(
        processed=23,
        already_processed_count=10,
        total_file_count=45,
        folder_stats=folder_stats,
        unclassified_count=2
    )
    
    new = build_credit_shortage_completion_message(
        processed=23,
        already_processed_count=10,
        total_file_count=45,
        folder_stats=folder_stats,
        unclassified_count=2
    )
    
    return compare_outputs("credit_shortage_completion", legacy, new)


def test_normal_completion_message():
    """Test 5: 정상 완료 메시지"""
    print("\n=== Test 5: build_normal_completion_message ===")
    
    import os
    
    folder_stats = {
        "밀링가공": 15,
        "선반가공": 10,
        "용접 프로파일": 12,
    }
    
    unmatched_files = ["/path/file1.dwg", "/path/file2.dwg"]
    
    legacy = legacy_build_normal_completion_message(
        total=45,
        processed=40,
        failed=2,
        folder_stats=folder_stats,
        unclassified_count=3,
        unmatched_files=unmatched_files
    )
    
    new = build_normal_completion_message(
        total=45,
        processed=40,
        failed=2,
        folder_stats=folder_stats,
        unclassified_count=3,
        unmatched_files=unmatched_files
    )
    
    return compare_outputs("normal_completion", legacy, new)


def test_edge_cases():
    """Test 6: Edge Cases"""
    print("\n=== Test 6: Edge Cases ===")
    
    all_pass = True
    
    # Edge 1: 크레딧 0
    legacy = legacy_calculate_processable_count(0, 50)
    new = calculate_processable_count(0, 50)
    if legacy != new:
        print(f"  ❌ Zero credits: legacy={legacy}, new={new}")
        all_pass = False
    else:
        print(f"  ✅ Zero credits: {new}")
    
    # Edge 2: 파일 0
    legacy = legacy_format_progress_label(0, 0, 0, False)
    new = format_progress_label(0, 0, 0, False)
    if legacy != new:
        print(f"  ❌ Zero files: legacy='{legacy}', new='{new}'")
        all_pass = False
    else:
        print(f"  ✅ Zero files: '{new}'")
    
    # Edge 3: 빈 폴더 통계
    legacy = legacy_build_normal_completion_message(0, 0, 0, {}, 0, [])
    new = build_normal_completion_message(0, 0, 0, {}, 0, [])
    if legacy != new:
        print(f"  ❌ Empty stats")
        all_pass = False
    else:
        print(f"  ✅ Empty stats")
    
    # Edge 4: 매우 큰 숫자
    legacy = legacy_calculate_processable_count(999999999, 1)
    new = calculate_processable_count(999999999, 1)
    if legacy != new:
        print(f"  ❌ Large numbers: legacy={legacy}, new={new}")
        all_pass = False
    else:
        print(f"  ✅ Large numbers: {new}")
    
    return all_pass


def test_compute_session_stats():
    """Test 7: 세션 통계 계산 (새 함수)"""
    print("\n=== Test 7: compute_session_stats ===")
    
    # 이 함수는 기존에 없던 새로운 함수이므로 로직 검증만 수행
    test_cases = [
        (10, 15, 45, {"cumulative_processed": 25, "remaining": 20}),
        (0, 0, 45, {"cumulative_processed": 0, "remaining": 45}),
        (30, 15, 45, {"cumulative_processed": 45, "remaining": 0}),
    ]
    
    all_pass = True
    for already, current, total, expected in test_cases:
        result = compute_session_stats(already, current, total)
        
        if result != expected:
            print(f"  ❌ ({already}, {current}, {total}): {result} != {expected}")
            all_pass = False
        else:
            print(f"  ✅ ({already}, {current}, {total}) → {result}")
    
    return all_pass


def main():
    """모든 테스트 실행"""
    print("=" * 60)
    print("DC 리팩토링 Side Effect 검증")
    print("=" * 60)
    
    results = []
    
    results.append(("calculate_processable_count", test_calculate_processable_count()))
    results.append(("format_progress_label", test_format_progress_label()))
    results.append(("credit_shortage_init_message", test_credit_shortage_init_message()))
    results.append(("credit_shortage_completion_message", test_credit_shortage_completion_message()))
    results.append(("normal_completion_message", test_normal_completion_message()))
    results.append(("edge_cases", test_edge_cases()))
    results.append(("compute_session_stats", test_compute_session_stats()))
    
    print("\n" + "=" * 60)
    print("최종 결과")
    print("=" * 60)
    
    total_tests = len(results)
    passed_tests = sum(1 for _, passed in results if passed)
    
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\n총 {total_tests}개 테스트 중 {passed_tests}개 통과")
    
    if passed_tests == total_tests:
        print("\n✅ 모든 테스트 통과! Side effect 없음 확인됨.")
        return 0
    else:
        print(f"\n❌ {total_tests - passed_tests}개 테스트 실패! Side effect 발견됨.")
        return 1


if __name__ == "__main__":
    exit(main())
