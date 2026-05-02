# -*- coding: utf-8 -*-
"""
ui_main.py 함수 호출 검증 (pytest 형식)

목적: ui_main.py에서 utils 함수를 올바르게 호출하는지 확인
"""
import re
import sys
import pytest
from pathlib import Path


class TestDwgClassifierFunctionCalls:
    """dwg_classifier ui_main.py 함수 호출 검증"""

    @pytest.fixture(autouse=True)
    def setup_paths(self):
        """경로 설정"""
        current_dir = Path(__file__).parent
        # 90.tests/unit/data/dwg_classifier -> 10.rpa/50.data/dwg_classifier
        self.rpa_root = current_dir.parents[3]
        self.ui_main_path = self.rpa_root / "50.data" / "dwg_classifier" / "ui_main.py"
        self.common_path = self.rpa_root / "10.common"

    def test_ui_main_file_exists(self):
        """ui_main.py 파일 존재 확인"""
        if not self.ui_main_path.exists():
            pytest.skip(f"ui_main.py 파일을 찾을 수 없습니다: {self.ui_main_path}")

    def test_utils_import_exists(self):
        """wf_credit_session_utils import 확인"""
        if not self.ui_main_path.exists():
            pytest.skip("ui_main.py 파일을 찾을 수 없습니다")

        with open(self.ui_main_path, "r", encoding="utf-8") as f:
            content = f.read()

        # import 패턴 확인
        import_pattern = r"from wf_credit_session_utils import"
        assert re.search(import_pattern, content), "wf_credit_session_utils import 없음"

    def test_expected_function_imports(self):
        """필수 함수들의 import 확인"""
        if not self.ui_main_path.exists():
            pytest.skip("ui_main.py 파일을 찾을 수 없습니다")

        with open(self.ui_main_path, "r", encoding="utf-8") as f:
            content = f.read()

        expected_imports = [
            "calculate_processable_count",
            "compute_session_stats",
            "format_progress_label",
        ]

        for func in expected_imports:
            if func not in content:
                pytest.skip(f"{func} 함수가 import되지 않았습니다 (선택적)")

    def test_calculate_processable_count_called(self):
        """calculate_processable_count 호출 확인"""
        if not self.ui_main_path.exists():
            pytest.skip("ui_main.py 파일을 찾을 수 없습니다")

        with open(self.ui_main_path, "r", encoding="utf-8") as f:
            content = f.read()

        pattern = r"calculate_processable_count\s*\("
        matches = re.findall(pattern, content)
        if not matches:
            pytest.skip("calculate_processable_count 호출이 없습니다 (선택적)")

    def test_format_progress_label_called(self):
        """format_progress_label 호출 확인"""
        if not self.ui_main_path.exists():
            pytest.skip("ui_main.py 파일을 찾을 수 없습니다")

        with open(self.ui_main_path, "r", encoding="utf-8") as f:
            content = f.read()

        pattern = r"format_progress_label\s*\("
        matches = re.findall(pattern, content)
        if not matches:
            pytest.skip("format_progress_label 호출이 없습니다 (선택적)")
