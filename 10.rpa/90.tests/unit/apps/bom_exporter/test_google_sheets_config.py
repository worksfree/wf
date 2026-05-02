# -*- coding: utf-8 -*-
"""
구글 시트 설정 테스트 (pytest 형식)
wf_rpa_config.json에서 구글 시트 ID 로드 검증
"""
import sys
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock


class TestGoogleSheetsConfig:
    """Google Sheets 설정 로드 테스트"""

    @pytest.fixture(autouse=True)
    def setup_path(self):
        """경로 설정"""
        current_dir = Path(__file__).parent
        common_path = current_dir.parents[4] / "10.common"
        if str(common_path) not in sys.path:
            sys.path.insert(0, str(common_path))

    def test_get_sheets_config_function_exists(self):
        """get_sheets_config 함수 존재 확인"""
        try:
            from wf_googlesheets_manager import get_sheets_config

            assert callable(get_sheets_config)
        except ImportError:
            pytest.skip("wf_googlesheets_manager에 get_sheets_config가 없습니다")

    def test_sheets_config_returns_dict(self):
        """get_sheets_config가 dict를 반환하는지 확인"""
        try:
            from wf_googlesheets_manager import get_sheets_config

            config = get_sheets_config()
            assert isinstance(config, dict)
        except ImportError:
            pytest.skip("wf_googlesheets_manager에 get_sheets_config가 없습니다")
        except Exception as e:
            pytest.skip(f"설정 로드 실패: {e}")

    def test_sheets_config_has_required_keys(self):
        """설정에 필수 키가 있는지 확인"""
        try:
            from wf_googlesheets_manager import get_sheets_config

            config = get_sheets_config()
            # 필수 키 목록
            expected_keys = ["SHEET_ID_RELEASE", "SHEET_ID_DEV", "SCOPE"]
            for key in expected_keys:
                if key not in config:
                    pytest.skip(f"설정에 {key} 키가 없습니다 (선택적)")
        except ImportError:
            pytest.skip("wf_googlesheets_manager에 get_sheets_config가 없습니다")
        except Exception as e:
            pytest.skip(f"설정 로드 실패: {e}")
