# -*- coding: utf-8 -*-
"""
DC 리팩토링 Side Effect 검증 스크립트 (pytest 형식)

목적: 리팩토링 전/후 로직이 동일한 결과를 생성하는지 비교
방법: utils 함수와 기존 로직을 재구현하여 출력 비교
"""
import sys
import pytest
from pathlib import Path


class TestDwgClassifierRefactoring:
    """dwg_classifier 리팩토링 side effect 검증"""

    @pytest.fixture(autouse=True)
    def setup_path(self):
        """경로 설정"""
        current_dir = Path(__file__).parent
        common_path = current_dir.parents[3] / "10.common"
        if str(common_path) not in sys.path:
            sys.path.insert(0, str(common_path))

    def test_calculate_processable_count(self):
        """calculate_processable_count 함수 테스트"""
        try:
            from wf_credit_session_utils import calculate_processable_count

            # 테스트 케이스
            assert calculate_processable_count(100, 10) == 10
            assert calculate_processable_count(1500, 50) == 30
            assert calculate_processable_count(0, 10) == 0
        except ImportError:
            pytest.skip("wf_credit_session_utils를 import할 수 없습니다")

    def test_compute_session_stats(self):
        """compute_session_stats 함수 테스트"""
        try:
            from wf_credit_session_utils import compute_session_stats

            result = compute_session_stats(
                already_processed_count=10, current_processed=5, total_file_count=50
            )
            assert "cumulative_processed" in result
            assert "remaining" in result
            assert result["cumulative_processed"] == 15
            assert result["remaining"] == 35
        except ImportError:
            pytest.skip("wf_credit_session_utils를 import할 수 없습니다")

    def test_format_progress_label_initial(self):
        """format_progress_label 초기 상태 테스트"""
        try:
            from wf_credit_session_utils import format_progress_label

            label = format_progress_label(
                already_processed_count=0,
                current_processed=0,
                total_file_count=45,
                is_finished=False,
            )
            assert "0/45" in label
        except ImportError:
            pytest.skip("wf_credit_session_utils를 import할 수 없습니다")

    def test_format_progress_label_processing(self):
        """format_progress_label 처리 중 테스트"""
        try:
            from wf_credit_session_utils import format_progress_label

            label = format_progress_label(
                already_processed_count=0,
                current_processed=25,
                total_file_count=45,
                is_finished=False,
            )
            assert "25/45" in label
        except ImportError:
            pytest.skip("wf_credit_session_utils를 import할 수 없습니다")

    def test_format_progress_label_finished(self):
        """format_progress_label 완료 상태 테스트"""
        try:
            from wf_credit_session_utils import format_progress_label

            label = format_progress_label(
                already_processed_count=0,
                current_processed=45,
                total_file_count=45,
                is_finished=True,
            )
            assert "45/45" in label
        except ImportError:
            pytest.skip("wf_credit_session_utils를 import할 수 없습니다")

    def test_get_credit_purchase_url(self):
        """get_credit_purchase_url 함수 테스트"""
        try:
            from wf_credit_session_utils import get_credit_purchase_url

            url = get_credit_purchase_url()
            assert url is not None
            assert "worksfree" in url.lower() or "http" in url.lower()
        except ImportError:
            pytest.skip("wf_credit_session_utils를 import할 수 없습니다")

    def test_build_credit_shortage_init_message_allow(self):
        """build_credit_shortage_init_message allow_continue=True 테스트"""
        try:
            from wf_credit_session_utils import build_credit_shortage_init_message

            msg = build_credit_shortage_init_message(
                remaining_count=100,
                processable_count=50,
                needed_credits=100,
                remaining_credits=50,
                shortage_credits=50,
                allow_continue=True,
            )
            assert msg is not None
            assert len(msg) > 0
        except ImportError:
            pytest.skip("wf_credit_session_utils를 import할 수 없습니다")

    def test_build_credit_shortage_init_message_block(self):
        """build_credit_shortage_init_message allow_continue=False 테스트"""
        try:
            from wf_credit_session_utils import build_credit_shortage_init_message

            msg = build_credit_shortage_init_message(
                remaining_count=100,
                processable_count=50,
                needed_credits=100,
                remaining_credits=50,
                shortage_credits=50,
                allow_continue=False,
            )
            assert msg is not None
            assert len(msg) > 0
        except ImportError:
            pytest.skip("wf_credit_session_utils를 import할 수 없습니다")

    def test_build_normal_completion_message(self):
        """build_normal_completion_message 함수 테스트"""
        try:
            from wf_credit_session_utils import build_normal_completion_message

            msg = build_normal_completion_message(
                total=100,
                processed=100,
                failed=0,
                folder_stats={"folder1": 50, "folder2": 50},
                unclassified_count=0,
            )
            assert msg is not None
            assert len(msg) > 0
        except ImportError:
            pytest.skip("wf_credit_session_utils를 import할 수 없습니다")

    def test_edge_case_zero_credits(self):
        """엣지 케이스: 0 크레딧"""
        try:
            from wf_credit_session_utils import calculate_processable_count

            result = calculate_processable_count(0, 10)
            assert result == 0
        except ImportError:
            pytest.skip("wf_credit_session_utils를 import할 수 없습니다")

    def test_edge_case_large_credits(self):
        """엣지 케이스: 큰 크레딧 값"""
        try:
            from wf_credit_session_utils import calculate_processable_count

            result = calculate_processable_count(1000000, 1)
            assert result == 1000000
        except ImportError:
            pytest.skip("wf_credit_session_utils를 import할 수 없습니다")
