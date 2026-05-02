# -*- coding: utf-8 -*-
"""
BOM Exporter Build Verification Test
빌드 전 종합 검증 테스트 (pytest 형식)

테스트 항목:
1. 하드웨어 정보: CPU, Board, Storage
2. 주요 모듈 임포트 확인
"""
import sys
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock


class TestBomExporterBuildVerification:
    """bom_exporter 빌드 검증 테스트"""

    @pytest.fixture(autouse=True)
    def setup_path(self):
        """경로 설정"""
        current_dir = Path(__file__).parent
        common_path = current_dir.parents[4] / "10.common"
        if str(common_path) not in sys.path:
            sys.path.insert(0, str(common_path))

    def test_hardware_info_has_required_attributes(self):
        """하드웨어 정보가 필수 속성을 가지는지 확인"""
        from wf_hwinfo import HardwareInfo

        hw = HardwareInfo()

        # 필수 속성 존재 확인
        assert hasattr(hw, 'cpu_id'), "cpu_id 속성이 없습니다"
        assert hasattr(hw, 'mainboard_id'), "mainboard_id 속성이 없습니다"
        assert hasattr(hw, 'storage_id'), "storage_id 속성이 없습니다"
        assert hasattr(hw, 'fingerprint'), "fingerprint 속성이 없습니다"

    def test_hardware_fingerprint_generated(self):
        """하드웨어 지문이 생성되는지 확인"""
        from wf_hwinfo import HardwareInfo

        hw = HardwareInfo()
        assert hw.fingerprint is not None
        assert len(hw.fingerprint) > 0

    def test_module_imports(self):
        """주요 모듈 임포트 확인"""
        modules_to_test = [
            "wf_hwinfo",
            "wf_credit_manager",
            "wf_log",
            "wf_settings_common",
        ]

        for module_name in modules_to_test:
            try:
                __import__(module_name)
            except ImportError as e:
                pytest.fail(f"{module_name} 임포트 실패: {e}")

    def test_credit_manager_initialization(self, isolated_wf_environment):
        """CreditManager 초기화 확인"""
        from wf_credit_manager import CreditManager

        cm = CreditManager(app_name="bom_exporter")
        assert cm is not None
        assert cm.app_name == "bom_exporter"

    def test_credit_manager_policy_dict(self, isolated_wf_environment):
        """CreditManager의 policy가 dict 형태인지 확인"""
        from wf_credit_manager import CreditManager

        cm = CreditManager(app_name="bom_exporter")
        assert isinstance(cm.policy, dict)
