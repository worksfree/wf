# -*- coding: utf-8 -*-
"""
wf_credit_session_utils 테스트 (pytest 형식)
"""
import sys
import pytest
from pathlib import Path


class TestWfCreditSessionUtils:
    """wf_credit_session_utils 모듈 테스트"""

    @pytest.fixture(autouse=True)
    def setup_path(self):
        """경로 설정"""
        current_dir = Path(__file__).parent
        common_path = current_dir.parents[2] / "10.common"
        if str(common_path) not in sys.path:
            sys.path.insert(0, str(common_path))

    def test_calculate_processable_count(self):
        """calculate_processable_count 함수 테스트"""
        try:
            from wf_credit_session_utils import calculate_processable_count

            result = calculate_processable_count(1500, 50)
            assert result == 30, f"Expected 30, got {result}"
        except ImportError:
            pytest.skip("wf_credit_session_utils를 import할 수 없습니다")

    def test_compute_session_stats(self):
        """compute_session_stats 함수 테스트"""
        try:
            from wf_credit_session_utils import compute_session_stats

            stats = compute_session_stats(
                already_processed_count=10,
                current_processed=15,
                total_file_count=45
            )
            assert stats['cumulative_processed'] == 25
            assert stats['remaining'] == 20
        except ImportError:
            pytest.skip("wf_credit_session_utils를 import할 수 없습니다")

    def test_format_progress_label_initial(self):
        """format_progress_label 초기 상태 테스트"""
        try:
            from wf_credit_session_utils import format_progress_label

            label = format_progress_label(0, 0, 45, is_finished=False)
            assert "0/45" in label
        except ImportError:
            pytest.skip("wf_credit_session_utils를 import할 수 없습니다")

    def test_format_progress_label_processing(self):
        """format_progress_label 처리 중 테스트"""
        try:
            from wf_credit_session_utils import format_progress_label

            label = format_progress_label(10, 15, 45, is_finished=False)
            assert "25/45" in label or "잔여" in label
        except ImportError:
            pytest.skip("wf_credit_session_utils를 import할 수 없습니다")

    def test_format_progress_label_finished(self):
        """format_progress_label 완료 상태 테스트"""
        try:
            from wf_credit_session_utils import format_progress_label

            label = format_progress_label(10, 35, 45, is_finished=True)
            assert "45/45" in label or "완료" in label
        except ImportError:
            pytest.skip("wf_credit_session_utils를 import할 수 없습니다")

    def test_build_credit_shortage_init_message_allow(self):
        """build_credit_shortage_init_message allow_continue=True 테스트"""
        try:
            from wf_credit_session_utils import build_credit_shortage_init_message

            msg = build_credit_shortage_init_message(
                remaining_count=45,
                processable_count=30,
                needed_credits=2250,
                remaining_credits=1500,
                shortage_credits=750,
                allow_continue=True
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
                remaining_count=45,
                processable_count=30,
                needed_credits=2250,
                remaining_credits=1500,
                shortage_credits=750,
                allow_continue=False
            )
            assert msg is not None
            assert len(msg) > 0
        except ImportError:
            pytest.skip("wf_credit_session_utils를 import할 수 없습니다")

    def test_build_credit_shortage_completion_message(self):
        """build_credit_shortage_completion_message 함수 테스트"""
        try:
            from wf_credit_session_utils import build_credit_shortage_completion_message

            msg = build_credit_shortage_completion_message(
                processed=30,
                already_processed_count=10,
                total_file_count=45,
                folder_stats={"folder1": 13, "folder2": 12, "folder3": 15},
                unclassified_count=5
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
                total=45,
                processed=45,
                failed=0,
                folder_stats={"folder1": 13, "folder2": 12, "folder3": 15},
                unclassified_count=5,
                unmatched_files=[]
            )
            assert msg is not None
            assert len(msg) > 0
        except ImportError:
            pytest.skip("wf_credit_session_utils를 import할 수 없습니다")

    def test_get_credit_purchase_url(self):
        """get_credit_purchase_url 함수 테스트"""
        try:
            from wf_credit_session_utils import get_credit_purchase_url

            url = get_credit_purchase_url()
            assert url is not None
            assert "http" in url.lower() or "worksfree" in url.lower()
        except ImportError:
            pytest.skip("wf_credit_session_utils를 import할 수 없습니다")
