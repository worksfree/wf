# -*- coding: utf-8 -*-
"""
DC 세션 관리 로직 추가 검증 (pytest 형식)

목적:
1. already_processed_count 계산이 정확한지
2. cumulative_processed_count 업데이트가 정확한지
3. 진행률 라벨이 상황별로 올바르게 표시되는지
"""
import sys
import pytest
from pathlib import Path


class TestDwgClassifierSessionLogic:
    """dwg_classifier 세션 로직 검증"""

    @pytest.fixture(autouse=True)
    def setup_path(self):
        """경로 설정"""
        current_dir = Path(__file__).parent
        common_path = current_dir.parents[3] / "10.common"
        if str(common_path) not in sys.path:
            sys.path.insert(0, str(common_path))

    def test_session_workflow(self):
        """세션 전체 워크플로우 검증"""
        try:
            from wf_credit_session_utils import compute_session_stats, format_progress_label

            total_files = 100
            already_processed = 30

            # Step 2: 분류 시작 - 20개 처리 중
            current_processed = 20
            label = format_progress_label(
                already_processed_count=already_processed,
                current_processed=current_processed,
                total_file_count=total_files,
                is_finished=False,
            )
            assert "50/100" in label

            # Step 3: 통계 확인
            stats = compute_session_stats(already_processed, current_processed, total_files)
            assert stats["cumulative_processed"] == 50
            assert stats["remaining"] == 50
        except ImportError:
            pytest.skip("wf_credit_session_utils를 import할 수 없습니다")

    def test_edge_case_no_previous_files(self):
        """엣지 케이스: 이전 처리 없음"""
        try:
            from wf_credit_session_utils import compute_session_stats, format_progress_label

            total_files = 100
            already_processed = 0
            current_processed = 50

            stats = compute_session_stats(already_processed, current_processed, total_files)
            assert stats["cumulative_processed"] == 50
            assert stats["remaining"] == 50

            label = format_progress_label(
                already_processed_count=0,
                current_processed=50,
                total_file_count=100,
                is_finished=False,
            )
            assert "50/100" in label
        except ImportError:
            pytest.skip("wf_credit_session_utils를 import할 수 없습니다")

    def test_edge_case_all_files_processed(self):
        """엣지 케이스: 모든 파일 처리 완료"""
        try:
            from wf_credit_session_utils import compute_session_stats, format_progress_label

            total_files = 100
            already_processed = 80
            current_processed = 20

            stats = compute_session_stats(already_processed, current_processed, total_files)
            assert stats["cumulative_processed"] == 100
            assert stats["remaining"] == 0

            label = format_progress_label(
                already_processed_count=80,
                current_processed=20,
                total_file_count=100,
                is_finished=True,
            )
            assert "100/100" in label
        except ImportError:
            pytest.skip("wf_credit_session_utils를 import할 수 없습니다")

    def test_credit_calculation_accuracy(self):
        """크레딧 계산 정확성 검증"""
        try:
            from wf_credit_session_utils import calculate_processable_count

            test_cases = [
                (100, 1, 100),
                (100, 2, 50),
                (100, 3, 33),
                (99, 10, 9),
                (0, 10, 0),
            ]

            for credits, cost, expected in test_cases:
                result = calculate_processable_count(credits, cost)
                assert result == expected, f"{credits}//{cost} = {result}, expected {expected}"
        except ImportError:
            pytest.skip("wf_credit_session_utils를 import할 수 없습니다")
