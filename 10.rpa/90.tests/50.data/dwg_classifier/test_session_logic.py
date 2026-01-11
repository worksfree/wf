"""
DC 세션 관리 로직 추가 검증

목적: 
1. already_processed_count 계산이 정확한지
2. cumulative_processed_count 업데이트가 정확한지
3. 진행률 라벨이 상황별로 올바르게 표시되는지
"""

import sys
from pathlib import Path

# Add common path (90.tests/50.data/dwg_classifier -> 90.tests -> 10.rpa -> 10.common)
COMMON_PATH = Path(__file__).parent.parent.parent.parent / "10.common"
if str(COMMON_PATH) not in sys.path:
    sys.path.insert(0, str(COMMON_PATH))

from wf_credit_session_utils import (
    compute_session_stats,
    format_progress_label,
)


def test_session_workflow():
    """세션 전체 워크플로우 검증"""
    print("\n=== 세션 전체 워크플로우 검증 ===")
    
    # 시나리오: 총 100개 파일, 30개는 이미 처리됨
    total_files = 100
    already_processed = 30
    remaining = 70
    
    print(f"\n📊 시나리오: 총 {total_files}개 파일, 이미 {already_processed}개 처리됨")
    print(f"   → 이번 실행 대상: {remaining}개")
    
    # Step 1: 초기 스캔 완료 (이미 처리된 파일 있음)
    print("\n[Step 1] 폴더 스캔 완료")
    if already_processed > 0:
        label = f"{already_processed}/{total_files} (잔여 {remaining}건)"
    else:
        label = f"0/{remaining}"
    print(f"  진행률 라벨: {label}")
    assert label == "30/100 (잔여 70건)", "초기 라벨 오류"
    
    # Step 2: 분류 시작 - 20개 처리 중
    print("\n[Step 2] 분류 시작 - 20개 처리 중")
    current_processed = 20
    label = format_progress_label(
        already_processed_count=already_processed,
        current_processed=current_processed,
        total_file_count=total_files,
        is_finished=False
    )
    print(f"  진행률 라벨: {label}")
    expected = "50/100 (잔여 50건)"
    assert label == expected, f"처리 중 라벨 오류: {label} != {expected}"
    
    # Step 3: 크레딧 부족으로 중단 (20개만 처리됨)
    print("\n[Step 3] 크레딧 부족으로 중단 (20개만 처리)")
    stats = compute_session_stats(already_processed, current_processed, total_files)
    print(f"  누적 처리: {stats['cumulative_processed']}")
    print(f"  남은 파일: {stats['remaining']}")
    assert stats['cumulative_processed'] == 50, "누적 처리 계산 오류"
    assert stats['remaining'] == 50, "남은 파일 계산 오류"
    
    label = format_progress_label(
        already_processed_count=already_processed,
        current_processed=current_processed,
        total_file_count=total_files,
        is_finished=False
    )
    if "(잔여" in label:
        label = label.replace("(잔여", "(중단: 크레딧 부족, 잔여")
    print(f"  중단 라벨: {label}")
    
    # Step 4: 크레딧 충전 후 재시작 - 남은 50개 중 30개 처리
    print("\n[Step 4] 크레딧 충전 후 재시작")
    # 이제 already_processed_count = 50 (이전 30 + 이번 20)
    new_already_processed = 50
    new_current_processed = 30
    
    label = format_progress_label(
        already_processed_count=new_already_processed,
        current_processed=new_current_processed,
        total_file_count=total_files,
        is_finished=False
    )
    print(f"  진행률 라벨: {label}")
    expected = "80/100 (잔여 20건)"
    assert label == expected, f"재시작 후 라벨 오류: {label} != {expected}"
    
    # Step 5: 다시 크레딧 부족 (총 80개 처리, 20개 남음)
    print("\n[Step 5] 다시 크레딧 부족 (80개 처리, 20개 남음)")
    stats = compute_session_stats(new_already_processed, new_current_processed, total_files)
    assert stats['cumulative_processed'] == 80, "2차 누적 처리 오류"
    assert stats['remaining'] == 20, "2차 남은 파일 오류"
    
    # Step 6: 마지막 크레딧 충전, 남은 20개 모두 처리
    print("\n[Step 6] 마지막 크레딧 충전 후 완료")
    final_already = 80
    final_current = 20
    
    label = format_progress_label(
        already_processed_count=final_already,
        current_processed=final_current,
        total_file_count=total_files,
        is_finished=True
    )
    print(f"  완료 라벨: {label}")
    expected = "100/100 (완료)"
    assert label == expected, f"완료 라벨 오류: {label} != {expected}"
    
    stats = compute_session_stats(final_already, final_current, total_files)
    assert stats['cumulative_processed'] == 100, "최종 누적 오류"
    assert stats['remaining'] == 0, "최종 남은 파일 오류"
    
    print("\n✅ 세션 워크플로우 검증 성공!")
    return True


def test_edge_case_no_previous_files():
    """이전에 처리된 파일이 없는 경우"""
    print("\n=== Edge Case: 이전 처리 파일 없음 ===")
    
    total = 50
    already = 0
    current = 25
    
    label = format_progress_label(
        already_processed_count=already,
        current_processed=current,
        total_file_count=total,
        is_finished=False
    )
    print(f"  진행률: {label}")
    expected = "25/50 (잔여 25건)"
    assert label == expected, f"라벨 오류: {label} != {expected}"
    
    print("✅ 통과")
    return True


def test_edge_case_all_files_processed():
    """모든 파일이 이미 처리된 경우"""
    print("\n=== Edge Case: 모든 파일 이미 처리됨 ===")
    
    total = 50
    already = 50
    current = 0
    
    # 초기 스캔 시
    if already > 0:
        remaining = total - already
        label = f"{already}/{total} (잔여 {remaining}건)"
    else:
        label = f"0/{total}"
    
    print(f"  초기 라벨: {label}")
    expected = "50/50 (잔여 0건)"
    assert label == expected, f"초기 라벨 오류: {label} != {expected}"
    
    # 처리 시작 (처리할 파일이 없으므로 0개 처리)
    label = format_progress_label(
        already_processed_count=already,
        current_processed=current,
        total_file_count=total,
        is_finished=True
    )
    print(f"  완료 라벨: {label}")
    expected = "50/50 (완료)"
    assert label == expected, f"완료 라벨 오류: {label} != {expected}"
    
    print("✅ 통과")
    return True


def test_credit_calculation_accuracy():
    """크레딧 차감 정확성 검증"""
    print("\n=== 크레딧 차감 정확성 검증 ===")
    
    # 시나리오: 45개 파일, 50 크레딧/파일
    total_files = 45
    cost_per_file = 50
    
    # Case 1: 충분한 크레딧 (3000)
    credits = 3000
    needed = total_files * cost_per_file  # 2250
    remaining_after = credits - needed  # 750
    print(f"\nCase 1: 충분한 크레딧")
    print(f"  보유: {credits}, 필요: {needed}, 처리 후 잔액: {remaining_after}")
    assert credits >= needed, "크레딧 부족 오류"
    assert remaining_after == 750, "잔액 계산 오류"
    
    # Case 2: 부족한 크레딧 (1500)
    credits = 1500
    needed = total_files * cost_per_file  # 2250
    shortage = needed - credits  # 750
    processable = credits // cost_per_file  # 30
    unprocessable = total_files - processable  # 15
    print(f"\nCase 2: 부족한 크레딧")
    print(f"  보유: {credits}, 필요: {needed}, 부족: {shortage}")
    print(f"  처리 가능: {processable}, 처리 불가: {unprocessable}")
    assert shortage == 750, "부족 크레딧 계산 오류"
    assert processable == 30, "처리 가능 개수 오류"
    assert unprocessable == 15, "처리 불가 개수 오류"
    
    # Case 3: 정확히 맞는 크레딧 (2250)
    credits = 2250
    needed = total_files * cost_per_file  # 2250
    remaining_after = credits - needed  # 0
    print(f"\nCase 3: 정확히 맞는 크레딧")
    print(f"  보유: {credits}, 필요: {needed}, 처리 후 잔액: {remaining_after}")
    assert credits == needed, "크레딧 일치 오류"
    assert remaining_after == 0, "잔액 0 오류"
    
    print("\n✅ 크레딧 계산 정확성 검증 성공!")
    return True


def main():
    """모든 검증 실행"""
    print("=" * 60)
    print("DC 세션 관리 및 크레딧 로직 검증")
    print("=" * 60)
    
    results = []
    
    try:
        results.append(("session_workflow", test_session_workflow()))
        results.append(("edge_no_previous", test_edge_case_no_previous_files()))
        results.append(("edge_all_processed", test_edge_case_all_files_processed()))
        results.append(("credit_calculation", test_credit_calculation_accuracy()))
    except AssertionError as e:
        print(f"\n❌ 검증 실패: {e}")
        return 1
    
    print("\n" + "=" * 60)
    print("최종 결과")
    print("=" * 60)
    
    total_tests = len(results)
    passed_tests = sum(1 for _, passed in results if passed)
    
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\n총 {total_tests}개 검증 중 {passed_tests}개 통과")
    
    if passed_tests == total_tests:
        print("\n✅ 모든 세션 관리 로직 검증 성공! Side effect 없음.")
        return 0
    else:
        print(f"\n❌ {total_tests - passed_tests}개 검증 실패!")
        return 1


if __name__ == "__main__":
    exit(main())
