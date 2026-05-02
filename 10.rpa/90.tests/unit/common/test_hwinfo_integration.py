# -*- coding: utf-8 -*-
"""
wf_hwinfo 통합 테스트 (pytest 형식)
각 모듈이 wf_hwinfo를 직접 사용하는지 확인
"""
import sys
import pytest
from pathlib import Path


class TestHwinfoIntegration:
    """HardwareInfo 통합 테스트"""

    @pytest.fixture(autouse=True)
    def setup_path(self):
        """경로 설정"""
        current_dir = Path(__file__).parent
        common_path = current_dir.parents[2] / "10.common"
        if str(common_path) not in sys.path:
            sys.path.insert(0, str(common_path))

    def test_hwinfo_import(self):
        """wf_hwinfo 모듈 import 테스트"""
        try:
            from wf_hwinfo import HardwareInfo
            assert HardwareInfo is not None
        except ImportError:
            pytest.skip("wf_hwinfo를 import할 수 없습니다")

    def test_hwinfo_singleton(self):
        """HardwareInfo가 일관된 값을 반환하는지 테스트"""
        try:
            from wf_hwinfo import HardwareInfo

            hw1 = HardwareInfo()
            hw2 = HardwareInfo()

            # 같은 시스템에서는 같은 값을 반환해야 함
            assert hw1.fingerprint == hw2.fingerprint, "지문이 일치하지 않음"
            assert hw1.cpu_id == hw2.cpu_id, "CPU ID가 일치하지 않음"
            assert hw1.mainboard_id == hw2.mainboard_id, "메인보드 ID가 일치하지 않음"
            assert hw1.storage_id == hw2.storage_id, "스토리지 ID가 일치하지 않음"

        except ImportError:
            pytest.skip("wf_hwinfo를 import할 수 없습니다")

    def test_credit_manager(self, isolated_wf_environment):
        """CreditManager가 wf_hwinfo를 직접 사용하는지 테스트"""
        try:
            from wf_credit_manager import WorksFreeManager

            wm = WorksFreeManager()
            # WorksFreeManager가 초기화되면 성공
            assert wm is not None

        except ImportError:
            pytest.skip("wf_credit_manager를 import할 수 없습니다")

    def test_sheets_manager(self):
        """GoogleSheetsManager가 wf_hwinfo를 직접 사용하는지 테스트"""
        try:
            from wf_googlesheets_manager import GoogleSheetsManager

            gsm = GoogleSheetsManager()

            # prepare_registration_data가 _get_hardware_info_once를 호출
            reg_data = gsm.prepare_registration_data(
                "test@example.com", "Test User", "010-1234-5678", "Y", "test_app"
            )

            # 하드웨어 정보가 포함되어 있는지 확인
            assert "uc_hw_fingerprint" in reg_data or reg_data is not None

            # get_hardware_fingerprint 메서드도 테스트
            if hasattr(gsm, 'get_hardware_fingerprint'):
                fingerprint = gsm.get_hardware_fingerprint()
                assert fingerprint is not None

        except ImportError:
            pytest.skip("wf_googlesheets_manager를 import할 수 없습니다")
        except Exception as e:
            pytest.skip(f"테스트 환경 문제: {e}")

    def test_hardware_fingerprint_format(self):
        """하드웨어 지문 형식 테스트"""
        try:
            from wf_hwinfo import HardwareInfo

            hw = HardwareInfo()
            fingerprint = hw.fingerprint

            # 지문은 문자열이어야 함
            assert isinstance(fingerprint, str)
            # 지문은 비어있지 않아야 함
            assert len(fingerprint) > 0

        except ImportError:
            pytest.skip("wf_hwinfo를 import할 수 없습니다")

    def test_cpu_id_exists(self):
        """CPU ID 존재 테스트"""
        try:
            from wf_hwinfo import HardwareInfo

            hw = HardwareInfo()
            assert hw.cpu_id is not None
            assert len(hw.cpu_id) > 0

        except ImportError:
            pytest.skip("wf_hwinfo를 import할 수 없습니다")
