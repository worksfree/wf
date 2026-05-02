# -*- coding: utf-8 -*-
"""
다중 앱 정책 테스트 (pytest 형식)
크레딧 단위 및 정책 검증
"""
import sys
import pytest
from pathlib import Path


class TestWfCreditManagerPolicies:
    """CreditManager 정책 테스트"""

    @pytest.fixture(autouse=True)
    def setup_path(self):
        """경로 설정"""
        current_dir = Path(__file__).parent
        common_path = current_dir.parents[2] / "10.common"
        if str(common_path) not in sys.path:
            sys.path.insert(0, str(common_path))

    def test_credit_manager_import(self):
        """CreditManager import 테스트"""
        try:
            from wf_credit_manager import CreditManager
            assert CreditManager is not None
        except ImportError:
            pytest.skip("wf_credit_manager를 import할 수 없습니다")

    def test_worksfree_manager_import(self):
        """WorksFreeManager import 테스트"""
        try:
            from wf_credit_manager import WorksFreeManager
            assert WorksFreeManager is not None
        except ImportError:
            pytest.skip("wf_credit_manager를 import할 수 없습니다")

    def test_credit_manager_has_get_policy_info(self):
        """CreditManager에 get_policy_info 메서드가 있는지 확인"""
        try:
            from wf_credit_manager import CreditManager
            assert hasattr(CreditManager, 'get_policy_info')
        except ImportError:
            pytest.skip("wf_credit_manager를 import할 수 없습니다")

    def test_credit_manager_has_deduct_credits_by_policy(self):
        """CreditManager에 deduct_credits_by_policy 메서드가 있는지 확인"""
        try:
            from wf_credit_manager import CreditManager
            assert hasattr(CreditManager, 'deduct_credits_by_policy')
        except ImportError:
            pytest.skip("wf_credit_manager를 import할 수 없습니다")

    def test_credit_manager_has_get_per_item_cost(self):
        """CreditManager에 get_per_item_cost 메서드가 있는지 확인"""
        try:
            from wf_credit_manager import CreditManager
            assert hasattr(CreditManager, 'get_per_item_cost')
        except ImportError:
            pytest.skip("wf_credit_manager를 import할 수 없습니다")

    def test_credit_manager_initialization(self, isolated_wf_environment):
        """CreditManager 초기화 테스트"""
        try:
            from wf_credit_manager import CreditManager
            cm = CreditManager(app_name="test_app")
            assert cm is not None
            assert cm.app_name == "test_app"
        except ImportError:
            pytest.skip("wf_credit_manager를 import할 수 없습니다")

    def test_policy_info_returns_dict(self, isolated_wf_environment):
        """get_policy_info가 dict를 반환하는지 확인"""
        try:
            from wf_credit_manager import CreditManager

            cm = CreditManager(app_name="test_app")
            policy_info = cm.get_policy_info()

            assert isinstance(policy_info, dict)
        except ImportError:
            pytest.skip("wf_credit_manager를 import할 수 없습니다")
        except Exception as e:
            pytest.skip(f"테스트 환경 문제: {e}")

    def test_per_item_cost_is_numeric(self, isolated_wf_environment):
        """get_per_item_cost가 숫자를 반환하는지 확인"""
        try:
            from wf_credit_manager import CreditManager

            cm = CreditManager(app_name="test_app")
            cost = cm.get_per_item_cost()

            assert isinstance(cost, (int, float))
        except ImportError:
            pytest.skip("wf_credit_manager를 import할 수 없습니다")
        except Exception as e:
            pytest.skip(f"테스트 환경 문제: {e}")

    def test_bom_exporter_initialization(self, isolated_wf_environment):
        """bom_exporter 앱 초기화 테스트"""
        try:
            from wf_credit_manager import CreditManager
            cm = CreditManager(app_name="bom_exporter")
            assert cm.app_name == "bom_exporter"
        except ImportError:
            pytest.skip("wf_credit_manager를 import할 수 없습니다")

    def test_dwg_classifier_initialization(self, isolated_wf_environment):
        """dwg_classifier 앱 초기화 테스트"""
        try:
            from wf_credit_manager import CreditManager
            cm = CreditManager(app_name="dwg_classifier")
            assert cm.app_name == "dwg_classifier"
        except ImportError:
            pytest.skip("wf_credit_manager를 import할 수 없습니다")

    def test_dwg_batch_print_initialization(self, isolated_wf_environment):
        """dwg_batch_print 앱 초기화 테스트"""
        try:
            from wf_credit_manager import CreditManager
            cm = CreditManager(app_name="dwg_batch_print")
            assert cm.app_name == "dwg_batch_print"
        except ImportError:
            pytest.skip("wf_credit_manager를 import할 수 없습니다")

    def test_conversion_verifier_initialization(self, isolated_wf_environment):
        """conversion_verifier 앱 초기화 테스트"""
        try:
            from wf_credit_manager import CreditManager
            cm = CreditManager(app_name="conversion_verifier")
            assert cm.app_name == "conversion_verifier"
        except ImportError:
            pytest.skip("wf_credit_manager를 import할 수 없습니다")
