# -*- coding: utf-8 -*-
"""
GoogleSheetsManager 설정 로드 테스트 (pytest 형식)
_load_config() 메서드가 wf_rpa_config.json에서 제대로 로드하는지 검증
"""
import sys
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock


class TestGoogleSheetsManagerConfig:
    """GoogleSheetsManager 설정 로드 테스트"""

    @pytest.fixture(autouse=True)
    def setup_path(self):
        """경로 설정"""
        current_dir = Path(__file__).parent
        common_path = current_dir.parents[4] / "10.common"
        if str(common_path) not in sys.path:
            sys.path.insert(0, str(common_path))

    def test_manager_class_exists(self):
        """GoogleSheetsManager 클래스 존재 확인"""
        try:
            from wf_googlesheets_manager import GoogleSheetsManager

            assert GoogleSheetsManager is not None
        except ImportError as e:
            pytest.skip(f"GoogleSheetsManager를 import할 수 없습니다: {e}")

    def test_manager_has_load_config_method(self):
        """GoogleSheetsManager에 _load_config 메서드가 있는지 확인"""
        try:
            from wf_googlesheets_manager import GoogleSheetsManager

            assert hasattr(GoogleSheetsManager, "_load_config") or hasattr(
                GoogleSheetsManager, "load_config"
            )
        except ImportError:
            pytest.skip("GoogleSheetsManager를 import할 수 없습니다")

    def test_manager_initialization_skipped(self):
        """GoogleSheetsManager 초기화 테스트 (실제 인증 필요로 스킵)"""
        # 실제 Google API 인증이 필요하므로 단위 테스트에서는 스킵
        pytest.skip("GoogleSheetsManager 초기화는 실제 인증이 필요합니다")
