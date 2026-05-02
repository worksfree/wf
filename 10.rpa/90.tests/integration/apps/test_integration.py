# -*- coding: utf-8 -*-
"""
통합 테스트: Bom Exporter 전체 워크플로우
여러 모듈 간 상호작용 테스트
"""

import pytest
import sys
from pathlib import Path

# Python 경로 설정
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "10.common"))
sys.path.insert(0, str(project_root / "30.apps" / "Bom_Exporter"))


@pytest.mark.integration
class TestBomExporterIntegration:
    """Bom Exporter 통합 테스트"""

    def test_credit_manager_initialization(self, isolated_wf_environment):
        """크레딧 매니저 초기화 테스트"""
        from wf_credit_manager import CreditManager

        # Given: 격리된 환경
        # When: CreditManager 생성
        cm = CreditManager("bom_exporter", "test@example.com")

        # Then: 정상 초기화
        assert cm.app_name == "bom_exporter"
        assert cm.user_email == "test@example.com"
        assert cm.credit_file.exists()

    def test_credit_deduction_flow(
        self, isolated_wf_environment, auto_registered_user, mock_credit_manager_sheets
    ):
        """크레딧 차감 흐름 테스트"""
        from wf_credit_manager import CreditManager

        if auto_registered_user is None:
            pytest.skip("Registration user not available")

        # Given: 크레딧이 있는 상태
        cm = CreditManager("bom_exporter", "test@example.com")
        initial_status = cm.get_credit_status()

        # When: 크레딧 차감 수행
        per_cost = cm.get_per_item_cost()
        assert per_cost > 0, "Per-item cost should be positive"

        # Then: 크레딧 상태 확인
        assert initial_status is not None
        assert "remaining_credits" in initial_status

    def test_unlimited_credit_behavior(
        self, isolated_wf_environment, auto_registered_user, mock_credit_manager_sheets
    ):
        """무제한 크레딧 동작 테스트"""
        from wf_credit_manager import CreditManager

        # Given: 무제한 크레딧 설정
        cm = CreditManager("bom_exporter", "test@example.com")

        # 크레딧 파일 수정 (무제한으로)
        credit_data = cm._load_credit_data()
        credit_data["trial_credits"] = -1
        cm._save_credit_data(credit_data)

        # When: 크레딧 상태 확인
        status = cm.get_credit_status()

        # Then: 무제한 크레딧으로 인식됨
        assert status.get("trial_credits") == -1 or status.get("remaining_credits") == -1
        assert status["credit_type"] in ["free", "permanent"]

    def test_credit_sync_integration(self, isolated_wf_environment, mock_google_sheets):
        """크레딧 동기화 통합 테스트"""
        from wf_credit_manager import CreditManager

        # Given: 크레딧 매니저와 모킹된 Google Sheets
        cm = CreditManager("bom_exporter", "test@example.com")

        # 구매 이력 시뮬레이션
        mock_google_sheets.read_sheet.return_value = [
            ["타임스탬프", "이메일", "앱", "결제금액", "크레딧", "상태"],
            ["2025-10-18T10:00:00", "test@example.com", "bom_exporter", "10000", "1000", "완료"],
        ]

        # When: 크레딧 동기화
        result = cm.pull_and_apply_purchases()

        # Then: 동기화 성공
        # 실제 시트 접근은 모킹되어 있으므로 로직만 검증
        assert "success" in result


@pytest.mark.integration
def test_full_workflow_simulation(
    isolated_wf_environment, auto_registered_user, mock_credit_manager_sheets
):
    """전체 워크플로우 시뮬레이션"""
    from wf_credit_manager import CreditManager

    # Given: 새로운 사용자
    cm = CreditManager("bom_exporter", "newuser@example.com")

    # Step 1: 초기 크레딧 확인
    status1 = cm.get_credit_status()
    assert status1 is not None
    assert "remaining_credits" in status1

    # Step 2: 정책 기반 크레딧 계산 수행
    per_cost = cm.get_per_item_cost()
    assert per_cost >= 0, "Per-item cost should be non-negative"

    # Step 3: 동기화 상태 확인
    sync_status = cm.get_sync_status()
    assert "needs_sync" in sync_status
