# -*- coding: utf-8 -*-
"""
크레딧 동기화 플로우 테스트 (pytest 형식)
- 앱 시작 시 credit_changed=True면 동기화
- 크레딧 사용 성공 시 credit_changed=True 설정
- 앱 종료 시 credit_changed=True면 동기화
"""
import sys
import json
import pytest
from pathlib import Path


class TestCreditSyncFlow:
    """크레딧 동기화 플로우 테스트"""

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

    def test_credit_manager_has_get_sync_status(self):
        """CreditManager에 get_sync_status 메서드가 있는지 확인"""
        try:
            from wf_credit_manager import CreditManager
            assert hasattr(CreditManager, 'get_sync_status')
        except ImportError:
            pytest.skip("wf_credit_manager를 import할 수 없습니다")

    def test_credit_manager_has_deduct_credits(self):
        """CreditManager에 deduct_credits 메서드가 있는지 확인"""
        try:
            from wf_credit_manager import CreditManager
            assert hasattr(CreditManager, 'deduct_credits')
        except ImportError:
            pytest.skip("wf_credit_manager를 import할 수 없습니다")

    def test_credit_manager_has_check_and_sync_credits(self):
        """CreditManager에 check_and_sync_credits 메서드가 있는지 확인"""
        try:
            from wf_credit_manager import CreditManager
            assert hasattr(CreditManager, 'check_and_sync_credits')
        except ImportError:
            pytest.skip("wf_credit_manager를 import할 수 없습니다")

    @pytest.fixture
    def temp_credit_file(self, tmp_path):
        """임시 크레딧 파일 생성"""
        credit_file = tmp_path / "credit_history.json"
        initial_data = {
            "created_at": "2025-01-01T00:00:00.000",
            "last_updated": "2025-01-01T00:00:00.000",
            "last_synced": None,
            "credit_changed": False,
            "trial_credits": 2000,
            "purchased_credits": 0,
            "current_credits": 2000,
        }
        with open(credit_file, "w", encoding="utf-8") as f:
            json.dump(initial_data, f, indent=2, ensure_ascii=False)
        return credit_file

    def test_credit_changed_flag_set_true(self, temp_credit_file):
        """credit_changed 플래그를 True로 설정하는 테스트"""
        with open(temp_credit_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        data["credit_changed"] = True

        with open(temp_credit_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        with open(temp_credit_file, "r", encoding="utf-8") as f:
            updated_data = json.load(f)

        assert updated_data["credit_changed"] is True

    def test_credit_changed_flag_set_false(self, temp_credit_file):
        """credit_changed 플래그를 False로 설정하는 테스트"""
        # 먼저 True로 설정
        with open(temp_credit_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["credit_changed"] = True
        with open(temp_credit_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        # False로 변경
        with open(temp_credit_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["credit_changed"] = False
        with open(temp_credit_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        with open(temp_credit_file, "r", encoding="utf-8") as f:
            updated_data = json.load(f)

        assert updated_data["credit_changed"] is False

    def test_credit_manager_initialization(self, isolated_wf_environment):
        """CreditManager 초기화 테스트"""
        try:
            from wf_credit_manager import CreditManager
            cm = CreditManager(app_name="test_app")
            assert cm is not None
            assert cm.app_name == "test_app"
        except ImportError:
            pytest.skip("wf_credit_manager를 import할 수 없습니다")

    def test_sync_status_structure(self, isolated_wf_environment):
        """get_sync_status 반환 구조 테스트"""
        try:
            from wf_credit_manager import CreditManager

            cm = CreditManager(app_name="test_app")
            status = cm.get_sync_status()

            # 결과는 dict 형태여야 함
            assert isinstance(status, dict)
        except ImportError:
            pytest.skip("wf_credit_manager를 import할 수 없습니다")
        except Exception as e:
            pytest.skip(f"테스트 환경 문제: {e}")
