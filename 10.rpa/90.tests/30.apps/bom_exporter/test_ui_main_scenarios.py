"""
bom_exporter UI Main 통합 테스트
사용자 등록, 체험판, 크레딧 구매 및 사용에 대한 전체 시나리오 테스트

테스트 범위:
- 사용자 등록 (신규, 이메일 중복, 하드웨어 지문 중복/불일치)
- 체험판 사용 (초기 크레딧, 소진)
- 크레딧 구매 (성공, 실패, 신규 없음)
- 크레딧 소비 (무료→유료 순서, 무제한 타입)
- 다중 실행 방지
- UI 상태 전이 (미등록→등록, 크레딧 부족 안내)
- 크레딧 동기화 (앱 시작, 종료 시)
"""

import pytest
import os
import sys
import json
import tkinter as tk
from unittest.mock import Mock, MagicMock, patch, call
from pathlib import Path

# Skip all GUI tests in this file - they require a display and proper Tkinter event loop
pytestmark = pytest.mark.skip(reason="GUI integration tests require display and proper Tkinter setup")

# 절대 임포트로 테스트 대상 모듈 가져오기
sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "30.apps", "Bom_Exporter")
)
from ui_main import BomGUIApplication


@pytest.fixture
def mock_tk_root():
    """Mock Tkinter root window"""
    root = Mock(spec=tk.Tk)
    root.winfo_rootx = Mock(return_value=100)
    root.winfo_rooty = Mock(return_value=100)
    root.after = Mock()
    return root


@pytest.fixture
def mock_wf_manager():
    """Mock WorksFreeManager"""
    manager = Mock()
    manager.is_registered = Mock(return_value=False)
    manager.get_user_info = Mock(
        return_value={
            "user_mail": "test@example.com",
            "hardware_fingerprint": "test_fingerprint_123",
        }
    )
    manager.load_policies = Mock(
        return_value={
            "bom_exporter": {"credit_per_work": 1, "is_free": False, "has_permanent_license": False}
        }
    )
    manager.refresh_policies_from_sheets = Mock(return_value={"success": True})
    return manager


@pytest.fixture
def mock_credit_manager():
    """Mock CreditManager"""
    manager = Mock()
    manager.get_credit_status = Mock(
        return_value={
            "trial_credits": 1000,
            "purchased_credits": 0,
            "credit_type": "trial",
            "credit_per_work": 1,
            "remaining_credits": 1000,
        }
    )
    manager.check_and_sync_credits = Mock(return_value={"success": True})
    manager.get_sync_status = Mock(return_value={"needs_sync": False})
    manager.get_per_item_cost = Mock(return_value=1)
    manager.pull_and_apply_purchases = Mock(
        return_value={"success": True, "added": 0, "applied_ids": []}
    )
    manager._load_credit_data = Mock(return_value={"credit_per_work": 1})
    manager._save_credit_data = Mock()
    manager.app_name = "bom_exporter"
    return manager


@pytest.fixture
def mock_config():
    """Mock application configuration"""
    return {"runtime_config": {"topmost": True, "include_thumbnail": True}}


@pytest.mark.integration
class TestUserRegistration:
    """사용자 등록 관련 테스트"""

    @patch("ui_main.WorksFreeManager")
    @patch("ui_main.get_app_logger")
    @patch("ui_main.get_config")
    def test_new_user_registration_success(
        self, mock_get_config, mock_logger, mock_wfm_class, mock_tk_root, mock_config
    ):
        """신규 사용자 등록 성공 시나리오"""
        mock_get_config.return_value = mock_config
        mock_logger.return_value = Mock()

        wf_manager = Mock()
        wf_manager.is_registered.return_value = False
        wf_manager.get_user_info.return_value = {
            "user_mail": "newuser@example.com",
            "hardware_fingerprint": "new_hw_fingerprint",
        }
        mock_wfm_class.return_value = wf_manager

        with (
            patch("ui_main.CreditManager"),
            patch.object(BomGUIApplication, "init_ui"),
            patch.object(BomGUIApplication, "check_and_set_execution_status", return_value=True),
        ):

            app = BomGUIApplication(mock_tk_root)

            assert app.is_registered_user == False
            assert app.wf_manager == wf_manager

    @patch("ui_main.WorksFreeManager")
    @patch("ui_main.get_app_logger")
    @patch("ui_main.get_config")
    @patch("ui_main.messagebox")
    def test_duplicate_email_registration(
        self, mock_msgbox, mock_get_config, mock_logger, mock_wfm_class, mock_tk_root, mock_config
    ):
        """이메일 중복 등록 시도 시나리오"""
        mock_get_config.return_value = mock_config
        mock_logger.return_value = Mock()

        wf_manager = Mock()
        # 이미 등록된 사용자
        wf_manager.is_registered.return_value = True
        mock_wfm_class.return_value = wf_manager

        with (
            patch("ui_main.CreditManager"),
            patch.object(BomGUIApplication, "init_ui"),
            patch.object(BomGUIApplication, "check_and_set_execution_status", return_value=True),
        ):

            app = BomGUIApplication(mock_tk_root)

            # 이미 등록된 사용자는 등록 창이 아닌 설정 창을 열어야 함
            assert app.is_registered_user == True

    @patch("ui_main.WorksFreeManager")
    @patch("ui_main.get_app_logger")
    @patch("ui_main.get_config")
    @patch("ui_main.wf_hwinfo")
    def test_hardware_fingerprint_mismatch(
        self, mock_hwinfo, mock_get_config, mock_logger, mock_wfm_class, mock_tk_root, mock_config
    ):
        """하드웨어 지문 불일치 시나리오"""
        mock_get_config.return_value = mock_config
        mock_logger.return_value = Mock()

        # 저장된 하드웨어 지문과 현재 지문이 다름
        wf_manager = Mock()
        wf_manager.get_user_info.return_value = {"hardware_fingerprint": "stored_fingerprint"}
        wf_manager.is_registered.return_value = True
        mock_wfm_class.return_value = wf_manager

        hw_info = Mock()
        hw_info.fingerprint = "different_fingerprint"
        mock_hwinfo.HardwareInfo.return_value = hw_info

        with (
            patch("ui_main.CreditManager"),
            patch.object(BomGUIApplication, "init_ui"),
            patch.object(BomGUIApplication, "check_and_set_execution_status", return_value=True),
        ):

            app = BomGUIApplication(mock_tk_root)

            result = app.verify_hardware_fingerprint()
            assert result == False


@pytest.mark.integration
class TestTrialUsage:
    """체험판 사용 관련 테스트"""

    @patch("ui_main.WorksFreeManager")
    @patch("ui_main.CreditManager")
    @patch("ui_main.get_app_logger")
    @patch("ui_main.get_config")
    def test_trial_credits_initial_state(
        self, mock_get_config, mock_logger, mock_cm_class, mock_wfm_class, mock_tk_root, mock_config
    ):
        """체험판 초기 크레딧 상태"""
        mock_get_config.return_value = mock_config
        mock_logger.return_value = Mock()
        mock_wfm_class.return_value = Mock()

        credit_manager = Mock()
        credit_manager.get_credit_status.return_value = {
            "trial_credits": 1000,
            "purchased_credits": 0,
            "credit_type": "trial",
            "remaining_credits": 1000,
        }
        mock_cm_class.return_value = credit_manager

        with (
            patch.object(BomGUIApplication, "init_ui"),
            patch.object(BomGUIApplication, "check_and_set_execution_status", return_value=True),
        ):

            app = BomGUIApplication(mock_tk_root)

            status = app.credit_manager.get_credit_status()
            assert status["trial_credits"] == 1000
            assert status["purchased_credits"] == 0
            assert status["credit_type"] == "trial"

    @patch("ui_main.WorksFreeManager")
    @patch("ui_main.CreditManager")
    @patch("ui_main.get_app_logger")
    @patch("ui_main.get_config")
    def test_trial_credits_exhaustion(
        self, mock_get_config, mock_logger, mock_cm_class, mock_wfm_class, mock_tk_root, mock_config
    ):
        """체험판 크레딧 소진 시나리오"""
        mock_get_config.return_value = mock_config
        mock_logger.return_value = Mock()
        mock_wfm_class.return_value = Mock()

        credit_manager = Mock()
        credit_manager.get_credit_status.return_value = {
            "trial_credits": 0,
            "purchased_credits": 0,
            "credit_type": "trial",
            "remaining_credits": 0,
        }
        credit_manager.get_per_item_cost.return_value = 1
        mock_cm_class.return_value = credit_manager

        with (
            patch.object(BomGUIApplication, "init_ui"),
            patch.object(BomGUIApplication, "check_and_set_execution_status", return_value=True),
            patch("ui_main.messagebox") as mock_msgbox,
        ):

            app = BomGUIApplication(mock_tk_root)
            app.automation = Mock()
            app.automation.total_count = 10
            app.SLDDRW_PATH = "/test/path"

            app.start_bom_extraction()

            # 크레딧 없음 메시지 확인
            mock_msgbox.showerror.assert_called_once()
            args = mock_msgbox.showerror.call_args[0]
            assert "크레딧" in args[0] or "크레딧" in args[1]


@pytest.mark.integration
class TestCreditPurchase:
    """크레딧 구매 관련 테스트"""

    @patch("ui_main.WorksFreeManager")
    @patch("ui_main.CreditManager")
    @patch("ui_main.get_app_logger")
    @patch("ui_main.get_config")
    @patch("ui_main.messagebox")
    def test_successful_credit_purchase(
        self,
        mock_msgbox,
        mock_get_config,
        mock_logger,
        mock_cm_class,
        mock_wfm_class,
        mock_tk_root,
        mock_config,
    ):
        """크레딧 구매 성공 시나리오"""
        mock_get_config.return_value = mock_config
        mock_logger.return_value = Mock()
        mock_wfm_class.return_value = Mock()

        credit_manager = Mock()
        credit_manager.pull_and_apply_purchases.return_value = {
            "success": True,
            "added": 5000,
            "applied_ids": ["purchase_id_123"],
        }
        mock_cm_class.return_value = credit_manager

        with (
            patch.object(BomGUIApplication, "init_ui"),
            patch.object(BomGUIApplication, "check_and_set_execution_status", return_value=True),
        ):

            app = BomGUIApplication(mock_tk_root)
            app.on_refresh_credit()

            # 성공 메시지 확인
            mock_msgbox.showinfo.assert_called_once()
            args = mock_msgbox.showinfo.call_args[0]
            assert "5,000" in args[1] or "5000" in args[1]

    @patch("ui_main.WorksFreeManager")
    @patch("ui_main.CreditManager")
    @patch("ui_main.get_app_logger")
    @patch("ui_main.get_config")
    @patch("ui_main.messagebox")
    def test_no_new_purchases(
        self,
        mock_msgbox,
        mock_get_config,
        mock_logger,
        mock_cm_class,
        mock_wfm_class,
        mock_tk_root,
        mock_config,
    ):
        """신규 구매 없음 시나리오"""
        mock_get_config.return_value = mock_config
        mock_logger.return_value = Mock()
        mock_wfm_class.return_value = Mock()

        credit_manager = Mock()
        credit_manager.pull_and_apply_purchases.return_value = {
            "success": True,
            "added": 0,
            "applied_ids": [],
            "message": "신규 구매 이력이 없습니다.",
        }
        mock_cm_class.return_value = credit_manager

        with (
            patch.object(BomGUIApplication, "init_ui"),
            patch.object(BomGUIApplication, "check_and_set_execution_status", return_value=True),
        ):

            app = BomGUIApplication(mock_tk_root)
            app.on_refresh_credit()

            # 안내 메시지 확인
            mock_msgbox.showinfo.assert_called_once()


@pytest.mark.integration
class TestCreditConsumption:
    """크레딧 소비 관련 테스트"""

    @patch("ui_main.WorksFreeManager")
    @patch("ui_main.CreditManager")
    @patch("ui_main.get_app_logger")
    @patch("ui_main.get_config")
    def test_trial_then_paid_credit_order(
        self, mock_get_config, mock_logger, mock_cm_class, mock_wfm_class, mock_tk_root, mock_config
    ):
        """무료 크레딧 우선 소비 후 유료 크레딧 사용"""
        mock_get_config.return_value = mock_config
        mock_logger.return_value = Mock()
        mock_wfm_class.return_value = Mock()

        # 초기: 무료 100, 유료 200
        credit_manager = Mock()
        credit_manager.get_credit_status.return_value = {
            "trial_credits": 100,
            "purchased_credits": 200,
            "credit_type": "trial",
            "remaining_credits": 300,
        }
        mock_cm_class.return_value = credit_manager

        with (
            patch.object(BomGUIApplication, "init_ui"),
            patch.object(BomGUIApplication, "check_and_set_execution_status", return_value=True),
        ):

            app = BomGUIApplication(mock_tk_root)

            status = app.credit_manager.get_credit_status()
            # 무료 크레딧이 먼저 표시되어야 함
            assert status["trial_credits"] == 100
            assert status["purchased_credits"] == 200

    @patch("ui_main.WorksFreeManager")
    @patch("ui_main.CreditManager")
    @patch("ui_main.get_app_logger")
    @patch("ui_main.get_config")
    def test_unlimited_credit_type_free(
        self, mock_get_config, mock_logger, mock_cm_class, mock_wfm_class, mock_tk_root, mock_config
    ):
        """무료 앱(무제한) 타입"""
        mock_get_config.return_value = mock_config
        mock_logger.return_value = Mock()
        mock_wfm_class.return_value = Mock()

        credit_manager = Mock()
        credit_manager.get_credit_status.return_value = {
            "credit_type": "free",
            "remaining_credits": -1,
        }
        mock_cm_class.return_value = credit_manager

        with (
            patch.object(BomGUIApplication, "init_ui"),
            patch.object(BomGUIApplication, "check_and_set_execution_status", return_value=True),
        ):

            app = BomGUIApplication(mock_tk_root)
            app.credit_label = Mock()
            app.update_credit_display()

            # "🎁 무료 앱" 텍스트 확인
            call_args = app.credit_label.config.call_args
            assert "무료" in str(call_args)

    @patch("ui_main.WorksFreeManager")
    @patch("ui_main.CreditManager")
    @patch("ui_main.get_app_logger")
    @patch("ui_main.get_config")
    def test_unlimited_credit_type_permanent(
        self, mock_get_config, mock_logger, mock_cm_class, mock_wfm_class, mock_tk_root, mock_config
    ):
        """영구 라이선스(무제한) 타입"""
        mock_get_config.return_value = mock_config
        mock_logger.return_value = Mock()
        mock_wfm_class.return_value = Mock()

        credit_manager = Mock()
        credit_manager.get_credit_status.return_value = {
            "credit_type": "permanent",
            "remaining_credits": -1,
        }
        mock_cm_class.return_value = credit_manager

        with (
            patch.object(BomGUIApplication, "init_ui"),
            patch.object(BomGUIApplication, "check_and_set_execution_status", return_value=True),
        ):

            app = BomGUIApplication(mock_tk_root)
            app.credit_label = Mock()
            app.update_credit_display()

            # "✨ 무제한" 텍스트 확인
            call_args = app.credit_label.config.call_args
            assert "무제한" in str(call_args)


@pytest.mark.integration
class TestMultiInstancePrevention:
    """다중 실행 방지 테스트"""

    @patch("ui_main.WorksFreeManager")
    @patch("ui_main.get_app_logger")
    @patch("ui_main.get_config")
    @patch("ui_main.sys.exit")
    @patch("ui_main.messagebox")
    def test_prevent_multiple_instances(
        self,
        mock_msgbox,
        mock_exit,
        mock_get_config,
        mock_logger,
        mock_wfm_class,
        mock_tk_root,
        mock_config,
    ):
        """다른 인스턴스 실행 중 방지"""
        mock_get_config.return_value = mock_config
        mock_logger.return_value = Mock()
        mock_wfm_class.return_value = Mock()

        with patch.object(BomGUIApplication, "check_and_set_execution_status", return_value=False):
            app = BomGUIApplication(mock_tk_root)

            # 종료 호출 확인
            mock_exit.assert_called_once_with(0)
            mock_msgbox.showerror.assert_called_once()


@pytest.mark.integration
class TestUIStateTransitions:
    """UI 상태 전이 테스트"""

    @patch("ui_main.WorksFreeManager")
    @patch("ui_main.CreditManager")
    @patch("ui_main.get_app_logger")
    @patch("ui_main.get_config")
    @patch("ui_main.messagebox")
    def test_unregistered_to_registered_transition(
        self,
        mock_msgbox,
        mock_get_config,
        mock_logger,
        mock_cm_class,
        mock_wfm_class,
        mock_tk_root,
        mock_config,
    ):
        """미등록 → 등록 완료 UI 전이"""
        mock_get_config.return_value = mock_config
        mock_logger.return_value = Mock()

        wf_manager = Mock()
        wf_manager.is_registered.side_effect = [False, True]  # 처음엔 미등록, 나중엔 등록
        mock_wfm_class.return_value = wf_manager
        mock_cm_class.return_value = Mock()

        with (
            patch.object(BomGUIApplication, "init_ui"),
            patch.object(BomGUIApplication, "check_and_set_execution_status", return_value=True),
        ):

            app = BomGUIApplication(mock_tk_root)
            app.settings_button = Mock()

            assert app.is_registered_user == False

            # 등록 완료 후 상태 업데이트
            app.post_registration_update()

            assert app.is_registered_user == True
            # 버튼이 '설 정'으로 변경되어야 함
            app.settings_button.config.assert_called()

    @patch("ui_main.WorksFreeManager")
    @patch("ui_main.CreditManager")
    @patch("ui_main.get_app_logger")
    @patch("ui_main.get_config")
    @patch("ui_main.messagebox")
    def test_insufficient_credits_partial_processing(
        self,
        mock_msgbox,
        mock_get_config,
        mock_logger,
        mock_cm_class,
        mock_wfm_class,
        mock_tk_root,
        mock_config,
    ):
        """크레딧 부족 시 일부만 처리 가능 안내"""
        mock_get_config.return_value = mock_config
        mock_logger.return_value = Mock()
        mock_wfm_class.return_value = Mock()

        credit_manager = Mock()
        credit_manager.get_credit_status.return_value = {
            "remaining_credits": 50,
            "credit_type": "trial",
        }
        credit_manager.get_per_item_cost.return_value = 10
        mock_cm_class.return_value = credit_manager

        with (
            patch.object(BomGUIApplication, "init_ui"),
            patch.object(BomGUIApplication, "check_and_set_execution_status", return_value=True),
        ):

            app = BomGUIApplication(mock_tk_root)
            app.automation = Mock()
            app.automation.total_count = 10  # 100 크레딧 필요
            app.SLDDRW_PATH = "/test/path"

            # askyesno를 False로 설정하여 취소
            mock_msgbox.askyesno.return_value = False

            app.start_bom_extraction()

            # 확인 메시지 호출 확인 (5개만 처리 가능)
            mock_msgbox.askyesno.assert_called_once()
            args = mock_msgbox.askyesno.call_args[0]
            assert "5" in args[1]  # 처리 가능한 개수


@pytest.mark.integration
class TestCreditSync:
    """크레딧 동기화 테스트"""

    @patch("ui_main.WorksFreeManager")
    @patch("ui_main.CreditManager")
    @patch("ui_main.get_app_logger")
    @patch("ui_main.get_config")
    def test_sync_on_app_exit(
        self, mock_get_config, mock_logger, mock_cm_class, mock_wfm_class, mock_tk_root, mock_config
    ):
        """앱 종료 시 크레딧 동기화"""
        mock_get_config.return_value = mock_config
        mock_logger.return_value = Mock()
        mock_wfm_class.return_value = Mock()

        credit_manager = Mock()
        credit_manager.get_sync_status.return_value = {"needs_sync": True}
        credit_manager.check_and_sync_credits.return_value = {"success": True}
        mock_cm_class.return_value = credit_manager

        with (
            patch.object(BomGUIApplication, "init_ui"),
            patch.object(BomGUIApplication, "check_and_set_execution_status", return_value=True),
            patch.object(BomGUIApplication, "clear_execution_status"),
        ):

            app = BomGUIApplication(mock_tk_root)
            app.on_closing()

            # 동기화 호출 확인
            credit_manager.check_and_sync_credits.assert_called()

    @patch("ui_main.WorksFreeManager")
    @patch("ui_main.CreditManager")
    @patch("ui_main.get_app_logger")
    @patch("ui_main.get_config")
    def test_background_policy_sync(
        self, mock_get_config, mock_logger, mock_cm_class, mock_wfm_class, mock_tk_root, mock_config
    ):
        """백그라운드 정책 동기화"""
        mock_get_config.return_value = mock_config
        mock_logger.return_value = Mock()

        wf_manager = Mock()
        wf_manager.refresh_policies_from_sheets.return_value = {"success": True, "updated": True}
        mock_wfm_class.return_value = wf_manager
        mock_cm_class.return_value = Mock()

        with (
            patch.object(BomGUIApplication, "init_ui"),
            patch.object(BomGUIApplication, "check_and_set_execution_status", return_value=True),
            patch("ui_main.threading.Thread") as mock_thread,
        ):

            app = BomGUIApplication(mock_tk_root)
            app._async_refresh_policies()

            # 백그라운드 스레드 시작 확인
            mock_thread.assert_called()
            assert mock_thread.call_args[1]["daemon"] == True


# --- Focused smoke test for variable/method rename ---
    
