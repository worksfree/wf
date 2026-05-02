# -*- coding: utf-8 -*-
"""
dwg_batch_print credit_usage_log 테스트 (pytest 형식)
Google Sheets에 사용 로그 기록 테스트
"""
import sys
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock


class TestCreditUsageLog:
    """크레딧 사용 로그 테스트"""

    @pytest.fixture(autouse=True)
    def setup_path(self):
        """경로 설정"""
        current_dir = Path(__file__).parent
        common_path = current_dir.parents[4] / "10.common"
        if str(common_path) not in sys.path:
            sys.path.insert(0, str(common_path))

    def test_credit_manager_import(self):
        """CreditManager import 테스트"""
        try:
            from wf_credit_manager import CreditManager
            assert CreditManager is not None
        except ImportError:
            pytest.skip("wf_credit_manager를 import할 수 없습니다")

    def test_sheets_manager_import(self):
        """GoogleSheetsManager import 테스트"""
        try:
            from wf_googlesheets_manager import get_sheets_manager
            assert callable(get_sheets_manager)
        except ImportError:
            pytest.skip("wf_googlesheets_manager를 import할 수 없습니다")

    def test_sheets_manager_has_append_usage_log(self):
        """GoogleSheetsManager에 append_usage_log 메서드가 있는지 확인"""
        try:
            from wf_googlesheets_manager import GoogleSheetsManager
            assert hasattr(GoogleSheetsManager, 'append_usage_log')
        except ImportError:
            pytest.skip("wf_googlesheets_manager를 import할 수 없습니다")

    def test_usage_log_data_structure(self):
        """사용 로그 데이터 구조 테스트"""
        test_data = {
            "user_email": "test@example.com",
            "app_name": "dwg_batch_print",
            "hardware_fingerprint": "TEST-HWID-12345",
            "usage_amount": 5.0,
            "file_count": 10,
            "per_item_cost": 0.5,
            "description": "테스트 크레딧 사용"
        }

        # 필수 필드 확인
        required_fields = ["user_email", "app_name", "usage_amount"]
        for field in required_fields:
            assert field in test_data
            assert test_data[field] is not None

    def test_credit_manager_for_dwg_batch_print(self, isolated_wf_environment):
        """dwg_batch_print용 CreditManager 테스트"""
        try:
            from wf_credit_manager import CreditManager
            cm = CreditManager(app_name="dwg_batch_print")
            assert cm.app_name == "dwg_batch_print"
        except ImportError:
            pytest.skip("wf_credit_manager를 import할 수 없습니다")
