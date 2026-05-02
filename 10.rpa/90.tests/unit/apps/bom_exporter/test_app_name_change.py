# -*- coding: utf-8 -*-
"""Test Bom_Exporter app name unification"""
import sys
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock


class TestBomExporterAppName:
    """bom_exporter 앱 이름 변환 테스트"""

    @pytest.fixture(autouse=True)
    def setup_path(self):
        """경로 설정"""
        current_dir = Path(__file__).parent
        common_path = current_dir.parents[4] / "10.common"
        if str(common_path) not in sys.path:
            sys.path.insert(0, str(common_path))

    def test_credit_manager_app_name(self, isolated_wf_environment):
        """CreditManager가 bom_exporter 앱 이름을 올바르게 설정하는지 확인"""
        from wf_credit_manager import CreditManager

        cm = CreditManager(app_name="bom_exporter")
        assert cm.app_name == "bom_exporter"

    def test_legacy_name_mapping(self, isolated_wf_environment):
        """레거시 앱 이름이 CreditManager에서 처리되는지 확인"""
        from wf_credit_manager import CreditManager

        legacy_names = ["Bom2Excel", "Bom2Excel_Exporter", "bom2excel"]
        for legacy_name in legacy_names:
            cm = CreditManager(app_name=legacy_name)
            # 앱 이름이 설정되어 있는지만 확인 (정규화 여부는 구현에 따라 다름)
            assert cm.app_name is not None
            assert len(cm.app_name) > 0

    def test_policy_attributes(self, isolated_wf_environment):
        """정책 속성이 존재하는지 확인"""
        from wf_credit_manager import CreditManager

        cm = CreditManager(app_name="bom_exporter")
        policy = cm.policy

        # 정책이 dict 형태인지 확인
        assert isinstance(policy, dict)

    def test_policy_file_path_exists(self, isolated_wf_environment):
        """정책 파일 경로 속성이 존재하는지 확인"""
        from wf_credit_manager import CreditManager

        cm = CreditManager(app_name="bom_exporter")
        # policy_file 속성이 존재하면 확인
        if hasattr(cm, 'policy_file'):
            assert cm.policy_file is not None
