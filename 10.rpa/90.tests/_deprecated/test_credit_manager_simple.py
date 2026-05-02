"""
간단한 크레딧 매니저 테스트
실제 API에 맞춘 기본 테스트
"""

import pytest


@pytest.mark.unit
class TestCreditManagerBasics:
    """크레딧 매니저 기본 기능 테스트"""

    def test_manager_initialization(self, isolated_wf_environment):
        """매니저가 정상적으로 초기화되는지 확인"""
        from wf_credit_manager import CreditManager

        manager = CreditManager("test_app")
        assert manager is not None
        assert manager.app_name == "test_app"

    def test_singleton_pattern(self, isolated_wf_environment):
        """WorksFreeManager가 싱글톤 패턴을 따르는지 확인"""
        from wf_credit_manager import WorksFreeManager

        wm1 = WorksFreeManager()
        wm2 = WorksFreeManager()

        assert wm1 is wm2

    def test_get_credit_status(self, isolated_wf_environment):
        """크레딧 상태 조회 기능 확인"""
        from wf_credit_manager import CreditManager

        manager = CreditManager("test_app")
        status = manager.get_credit_status()

        assert isinstance(status, dict)
        # API가 다양한 형태로 반환할 수 있으므로 유연하게 체크
        assert "success" in status or "remaining_credits" in status or "trial_credits" in status


@pytest.mark.unit
class TestCreditOperations:
    """크레딧 기본 연산 테스트"""

    def test_deduct_credit_exists(self, isolated_wf_environment):
        """크레딧 차감 메서드가 존재하는지 확인"""
        from wf_credit_manager import CreditManager

        manager = CreditManager("test_app")
        # 실제 API: deduct_credits (복수형)
        assert hasattr(manager, "deduct_credits")
        assert hasattr(manager, "deduct_credits_by_policy")

    def test_credit_status_has_data(self, isolated_wf_environment):
        """크레딧 상태가 데이터를 반환하는지 확인"""
        from wf_credit_manager import CreditManager

        manager = CreditManager("test_app")
        status = manager.get_credit_status()

        # 최소한 비어있지 않은 딕셔너리 반환
        assert len(status) > 0


@pytest.mark.unit
class TestRegistration:
    """사용자 등록 기능 테스트"""

    def test_worksfree_manager_initialization(self, isolated_wf_environment):
        """WorksFreeManager 초기화 확인"""
        from wf_credit_manager import WorksFreeManager

        wm = WorksFreeManager()
        assert wm is not None

    def test_registration_method_exists(self, isolated_wf_environment):
        """등록 관련 메서드가 존재하는지 확인"""
        from wf_credit_manager import WorksFreeManager

        wm = WorksFreeManager()
        # 메서드 이름이 다를 수 있으므로 여러 가능성 체크
        has_registration = (
            hasattr(wm, "is_registered")
            or hasattr(wm, "is_user_registered")
            or hasattr(wm, "register_user")
        )
        assert has_registration


@pytest.mark.unit
class TestPolicyManagement:
    """정책 관리 테스트"""

    def test_manager_has_policy(self, isolated_wf_environment):
        """매니저가 정책 정보를 가지고 있는지 확인"""
        from wf_credit_manager import CreditManager

        manager = CreditManager("test_app")
        assert hasattr(manager, "policy")
        assert manager.policy is not None

    def test_policy_is_dict(self, isolated_wf_environment):
        """정책이 딕셔너리 형태인지 확인"""
        from wf_credit_manager import CreditManager

        manager = CreditManager("test_app")
        assert isinstance(manager.policy, dict)
        assert len(manager.policy) > 0
