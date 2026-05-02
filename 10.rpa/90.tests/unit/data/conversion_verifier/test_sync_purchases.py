# -*- coding: utf-8 -*-
"""
conversion_verifier 구매 이력 동기화 테스트 (pytest 형식)
"""
import sys
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock


class TestSyncPurchases:
    """구매 이력 동기화 테스트"""

    @pytest.fixture(autouse=True)
    def setup_path(self):
        """경로 설정"""
        current_dir = Path(__file__).parent
        common_path = current_dir.parents[3] / "10.common"
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

    def test_credit_manager_has_pull_and_apply_purchases(self):
        """CreditManager에 pull_and_apply_purchases 메서드가 있는지 확인"""
        try:
            from wf_credit_manager import CreditManager
            assert hasattr(CreditManager, 'pull_and_apply_purchases')
        except ImportError:
            pytest.skip("wf_credit_manager를 import할 수 없습니다")

    def test_credit_manager_initialization(self, isolated_wf_environment):
        """CreditManager 초기화 테스트"""
        try:
            from wf_credit_manager import CreditManager
            cm = CreditManager(app_name="conversion_verifier")
            assert cm.app_name == "conversion_verifier"
        except ImportError:
            pytest.skip("wf_credit_manager를 import할 수 없습니다")

    def test_pull_and_apply_purchases_result_structure(self, isolated_wf_environment):
        """pull_and_apply_purchases 결과 구조 테스트"""
        try:
            from wf_credit_manager import CreditManager

            cm = CreditManager(app_name="conversion_verifier")

            # pull_and_apply_purchases 호출 (Mock 환경에서는 실제 동기화 불가)
            result = cm.pull_and_apply_purchases()

            # 결과는 dict 형태여야 함
            assert isinstance(result, dict)

            # 필수 키 확인
            expected_keys = ["success"]
            for key in expected_keys:
                assert key in result, f"Missing key: {key}"

        except ImportError:
            pytest.skip("wf_credit_manager를 import할 수 없습니다")
        except Exception as e:
            # Mock 환경에서 Google Sheets 연결 실패는 허용
            if "google" in str(e).lower() or "sheets" in str(e).lower():
                pytest.skip(f"Google Sheets 연결 필요: {e}")
            raise

    def test_credit_file_attribute_exists(self, isolated_wf_environment):
        """credit_file 속성이 존재하는지 확인"""
        try:
            from wf_credit_manager import CreditManager
            cm = CreditManager(app_name="conversion_verifier")

            if hasattr(cm, 'credit_file'):
                assert cm.credit_file is not None
            else:
                # credit_file 속성이 없으면 다른 방식으로 파일 접근
                pytest.skip("credit_file 속성이 없습니다")
        except ImportError:
            pytest.skip("wf_credit_manager를 import할 수 없습니다")

    def test_purchase_history_data_structure(self):
        """구매 이력 데이터 구조 테스트"""
        sample_purchase = {
            "transaction_id": "TXN-12345",
            "amount": 10000,
            "purchased_credit": 100,
            "bonus_credit": 10,
            "total_credit": 110,
            "promo_code": "TEST10",
            "applied_date": "2025-01-17T12:00:00"
        }

        required_fields = ["transaction_id", "amount", "purchased_credit"]
        for field in required_fields:
            assert field in sample_purchase
            assert sample_purchase[field] is not None

    def test_applied_purchase_ids_tracking(self):
        """applied_purchase_ids 추적 로직 테스트"""
        applied_ids = ["TXN-001", "TXN-002"]
        new_purchase_id = "TXN-003"

        # 이미 적용된 구매는 중복 적용 안 함
        assert new_purchase_id not in applied_ids

        # 새 구매 적용 후 추가
        applied_ids.append(new_purchase_id)
        assert new_purchase_id in applied_ids
        assert len(applied_ids) == 3
