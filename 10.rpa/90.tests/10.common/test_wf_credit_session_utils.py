#!/usr/bin/env python
"""Test wf_credit_session_utils"""
import sys
from pathlib import Path

# Add common path (상위 3단계: 90.tests/10.common -> 90.tests -> 10.rpa -> 10.common)
common_path = Path(__file__).parent.parent.parent / "10.common"
if str(common_path) not in sys.path:
    sys.path.insert(0, str(common_path))

from wf_credit_session_utils import *

print("=" * 60)
print("Testing wf_credit_session_utils Functions")
print("=" * 60)

# Test 1: calculate_processable_count
result = calculate_processable_count(1500, 50)
assert result == 30, f"Expected 30, got {result}"
print("✅ Test 1: calculate_processable_count(1500, 50) = 30")

# Test 2: compute_session_stats
stats = compute_session_stats(already_processed_count=10, current_processed=15, total_file_count=45)
assert stats['cumulative_processed'] == 25
assert stats['remaining'] == 20
print("✅ Test 2: compute_session_stats - cumulative=25, remaining=20")

# Test 3a: format_progress_label - initial state
label = format_progress_label(0, 0, 45, is_finished=False)
assert label == "0/45", f"Expected '0/45', got '{label}'"
print(f"✅ Test 3a: Initial state = '{label}'")

# Test 3b: format_progress_label - processing
label = format_progress_label(10, 15, 45, is_finished=False)
assert "(잔여" in label
print(f"✅ Test 3b: Processing = '{label}'")

# Test 3c: format_progress_label - finished
label = format_progress_label(10, 35, 45, is_finished=True)
assert "(완료)" in label
print(f"✅ Test 3c: Finished = '{label}'")

# Test 4a: build_credit_shortage_init_message - allow continue
msg = build_credit_shortage_init_message(
    remaining_count=45, processable_count=30,
    needed_credits=2250, remaining_credits=1500,
    shortage_credits=750, allow_continue=True
)
assert "30건만" in msg
assert "진행하시겠습니까" in msg
print("✅ Test 4a: Credit shortage message (allow) contains correct text")

# Test 4b: build_credit_shortage_init_message - block
msg = build_credit_shortage_init_message(
    remaining_count=45, processable_count=30,
    needed_credits=2250, remaining_credits=1500,
    shortage_credits=750, allow_continue=False
)
assert "실행할 수 없습니다" in msg
print("✅ Test 4b: Credit shortage message (block) contains correct text")

# Test 5: build_credit_shortage_completion_message
msg = build_credit_shortage_completion_message(
    processed=30, already_processed_count=10, total_file_count=45,
    folder_stats={"밀링가공": 13, "선반가공": 12, "용접 프로파일": 15},
    unclassified_count=5
)
assert "이번 실행: 30개" in msg
assert "누적 처리: 40개 / 전체 45개" in msg
assert "남은 파일: 5개" in msg
assert "밀링가공: 13개" in msg
print("✅ Test 5: Credit shortage completion message formatted correctly")

# Test 6: build_normal_completion_message
msg = build_normal_completion_message(
    total=45, processed=45, failed=0,
    folder_stats={"밀링가공": 13, "선반가공": 12, "용접 프로파일": 15},
    unclassified_count=5,
    unmatched_files=[]
)
assert "전체 DWG 파일: 45개" in msg
assert "처리 성공: 45개" in msg
assert "폴더별 분류 결과" in msg
assert "미분류 파일: 5개" in msg
print("✅ Test 6: Normal completion message formatted correctly")

# Test 7: get_credit_purchase_url
url = get_credit_purchase_url()
assert url == "https://www.worksfree.co.kr/buy-credits"
print(f"✅ Test 7: Purchase URL = {url}")

print("\n" + "=" * 60)
print("🎉 All 7 Unit Tests Passed!")
print("=" * 60)
