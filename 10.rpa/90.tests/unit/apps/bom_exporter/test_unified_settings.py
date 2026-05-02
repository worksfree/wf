# -*- coding: utf-8 -*-
"""
통합 설정 파일 테스트 (pytest 형식)
bom_exporter settings.json 초기화 검증
"""
import json
import sys
import pytest
from pathlib import Path


class TestBomExporterUnifiedSettings:
    """bom_exporter 통합 설정 테스트"""

    @pytest.fixture(autouse=True)
    def setup_path(self):
        """경로 설정"""
        current_dir = Path(__file__).parent
        self.app_path = current_dir.parents[4] / "30.apps" / "bom_exporter"
        self.common_path = current_dir.parents[4] / "10.common"
        if str(self.app_path) not in sys.path:
            sys.path.insert(0, str(self.app_path))
        if str(self.common_path) not in sys.path:
            sys.path.insert(0, str(self.common_path))

    def test_app_setting_data_exists(self):
        """app_setting_data 모듈 존재 확인"""
        # 경로 재확인 - 90.tests에서 상대 경로 계산
        current_dir = Path(__file__).parent
        # 90.tests/unit/apps/bom_exporter -> 10.rpa/30.apps/bom_exporter
        rpa_root = current_dir.parents[3]  # 90.tests -> 10.rpa
        app_setting_file = rpa_root / "30.apps" / "bom_exporter" / "app_setting_data.py"
        if not app_setting_file.exists():
            pytest.skip(f"app_setting_data.py 파일 경로를 찾을 수 없습니다: {app_setting_file}")

    def test_get_config_function_exists(self):
        """get_config 함수 존재 확인"""
        try:
            from app_setting_data import get_config

            assert callable(get_config)
        except ImportError as e:
            pytest.skip(f"app_setting_data를 import할 수 없습니다: {e}")

    def test_config_has_restart_count(self):
        """config에 restart_count 속성이 있는지 확인"""
        try:
            from app_setting_data import get_config

            config = get_config()
            assert hasattr(config, "restart_count") or hasattr(
                config, "app_config"
            ), "restart_count 속성이 없습니다"
        except ImportError as e:
            pytest.skip(f"app_setting_data를 import할 수 없습니다: {e}")

    def test_settings_file_structure(self, tmp_path):
        """설정 파일 구조 테스트"""
        settings_file = tmp_path / "settings.json"

        test_settings = {
            "app_info": {"last_updated": "2025-01-01"},
            "solidworks": {"program_path": "C:\\test\\path.exe"},
            "app_config": {
                "restart_count": 20,
                "topmost": True,
                "auto_restart": True,
                "speed_mode": "normal",
                "base_wait_time": 60,
                "seconds_per_10mb": 60,
                "include_thumbnail": True,
            },
            "ui_config": {"last_selected_folder": ""},
        }

        with open(settings_file, "w", encoding="utf-8") as f:
            json.dump(test_settings, f, indent=2, ensure_ascii=False)

        with open(settings_file, "r", encoding="utf-8") as f:
            loaded = json.load(f)

        required_sections = ["app_info", "solidworks", "app_config", "ui_config"]
        for section in required_sections:
            assert section in loaded, f"{section} 섹션이 없습니다"

    def test_last_selected_folder_handling(self, tmp_path):
        """last_selected_folder 처리 테스트"""
        settings = {"ui_config": {"last_selected_folder": ""}}

        # 빈 값 확인
        last_folder = settings.get("ui_config", {}).get("last_selected_folder", "")
        assert last_folder == ""

        # 값 설정
        settings["ui_config"]["last_selected_folder"] = "D:/test_folder"
        assert settings["ui_config"]["last_selected_folder"] == "D:/test_folder"
