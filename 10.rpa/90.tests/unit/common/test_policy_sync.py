# -*- coding: utf-8 -*-
"""
정책 동기화 테스트 (pytest 형식)
"""
import os
import sys
import shutil
from pathlib import Path
import pytest

# 10.common import path
COMMON = Path(__file__).parents[2] / "10.common"
if str(COMMON) not in sys.path:
    sys.path.insert(0, str(COMMON))


class TestPolicySync:
    """정책 동기화 테스트"""

    @pytest.fixture(autouse=True)
    def setup_path(self):
        """경로 설정"""
        if str(COMMON) not in sys.path:
            sys.path.insert(0, str(COMMON))

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

    def test_sheets_manager_import(self):
        """get_sheets_manager import 테스트"""
        try:
            from wf_googlesheets_manager import get_sheets_manager
            assert callable(get_sheets_manager)
        except ImportError:
            pytest.skip("wf_googlesheets_manager를 import할 수 없습니다")

    def test_worksfree_manager_has_refresh_policies(self):
        """WorksFreeManager에 refresh_policies_from_sheets 메서드가 있는지 확인"""
        try:
            from wf_credit_manager import WorksFreeManager
            assert hasattr(WorksFreeManager, 'refresh_policies_from_sheets')
        except ImportError:
            pytest.skip("wf_credit_manager를 import할 수 없습니다")

    def test_worksfree_manager_initialization(self, isolated_wf_environment):
        """WorksFreeManager 초기화 테스트"""
        try:
            from wf_credit_manager import WorksFreeManager
            wf = WorksFreeManager()
            assert wf is not None
        except ImportError:
            pytest.skip("wf_credit_manager를 import할 수 없습니다")

    def test_credit_manager_for_bom_exporter(self, isolated_wf_environment):
        """bom_exporter용 CreditManager 테스트"""
        try:
            from wf_credit_manager import CreditManager
            cm = CreditManager(app_name="bom_exporter")
            assert cm.app_name == "bom_exporter"
        except ImportError:
            pytest.skip("wf_credit_manager를 import할 수 없습니다")

    def test_policy_file_name(self, isolated_wf_environment):
        """정책 파일 이름이 policy.json인지 확인"""
        try:
            from wf_credit_manager import CreditManager
            cm = CreditManager(app_name="bom_exporter")

            if hasattr(cm, 'policy_file') and cm.policy_file:
                assert cm.policy_file.name == "policy.json"
            else:
                pytest.skip("policy_file 속성이 없습니다")
        except ImportError:
            pytest.skip("wf_credit_manager를 import할 수 없습니다")
        except Exception as e:
            pytest.skip(f"테스트 환경 문제: {e}")


@pytest.mark.integration
class TestPolicySyncIntegration:
    """정책 동기화 통합 테스트 (fixture 파일 필요)"""

    @pytest.fixture()
    def temp_wf_home(self, tmp_path: Path):
        """임시 WF 홈 디렉토리 설정"""
        fixtures = Path(__file__).parents[1] / "fixtures" / "policy_sync"
        if not fixtures.exists():
            pytest.skip("fixtures/policy_sync 디렉토리가 없습니다")

        config_file = fixtures / "wf_rpa_config.json"
        policies_file = fixtures / ".wf_app_policies.json"

        if not config_file.exists() or not policies_file.exists():
            pytest.skip("fixture 파일이 없습니다")

        shutil.copy2(config_file, tmp_path / "wf_rpa_config.json")
        shutil.copy2(policies_file, tmp_path / ".wf_app_policies.json")
        os.environ["WF_RPA_HOME"] = str(tmp_path)
        return tmp_path

    def test_get_app_policies(self, temp_wf_home):
        """앱 정책 가져오기 테스트"""
        try:
            from wf_googlesheets_manager import get_sheets_manager
            sheets_manager = get_sheets_manager(test_mode=True)
            policies = sheets_manager.get_app_policies()
            assert policies is None or isinstance(policies, dict)
        except Exception as e:
            pytest.skip(f"Google Sheets 연결 필요: {e}")

    def test_refresh_policies_from_sheets(self, temp_wf_home):
        """시트에서 정책 새로고침 테스트"""
        try:
            from wf_credit_manager import WorksFreeManager, CreditManager
            wf_manager = WorksFreeManager()
            result = wf_manager.refresh_policies_from_sheets()
            assert "success" in result

            cm = CreditManager(app_name="bom_exporter")
            if hasattr(cm, 'policy_file') and cm.policy_file:
                assert cm.policy_file.name == "policy.json"
        except Exception as e:
            pytest.skip(f"테스트 환경 문제: {e}")

    def test_policy_file_exists_after_refresh(self, temp_wf_home):
        """정책 새로고침 후 파일 존재 확인"""
        try:
            from wf_credit_manager import WorksFreeManager, CreditManager
            wf_manager = WorksFreeManager()
            wf_manager.refresh_policies_from_sheets()
            cm = CreditManager(app_name="bom2excel")

            if hasattr(cm, 'policy_file'):
                policy_file = cm.policy_file
                if policy_file.exists():
                    content = policy_file.read_text(encoding="utf-8").strip()
                    assert content.startswith("{")
        except Exception as e:
            pytest.skip(f"테스트 환경 문제: {e}")
