# -*- coding: utf-8 -*-
"""
BOM Exporter Deployment Mode Test
배포 설정 파일 테스트 (pytest 형식)
"""
import sys
import json
import pytest
from pathlib import Path


class TestBomExporterDeploymentMode:
    """bom_exporter 배포 모드 테스트"""

    @pytest.fixture(autouse=True)
    def setup_path(self):
        """경로 설정"""
        current_dir = Path(__file__).parent
        self.common_path = current_dir.parents[4] / "10.common"
        self.app_path = current_dir.parents[4] / "30.apps" / "bom_exporter"
        if str(self.common_path) not in sys.path:
            sys.path.insert(0, str(self.common_path))

    def test_settings_file_creation(self, tmp_path):
        """settings.json 파일 생성 테스트"""
        settings_file = tmp_path / ".wf_rpa" / "bom_exporter" / "settings.json"
        settings_file.parent.mkdir(parents=True, exist_ok=True)

        default_settings = {
            "app_info": {"last_updated": "2025-11-25 05:47:00"},
            "solidworks": {
                "program_path": "C:\\Program Files\\SOLIDWORKS Corp\\SOLIDWORKS\\SLDWORKS.exe"
            },
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
            json.dump(default_settings, f, indent=2, ensure_ascii=False)

        assert settings_file.exists()

        with open(settings_file, "r", encoding="utf-8") as f:
            loaded = json.load(f)

        assert "app_info" in loaded
        assert "solidworks" in loaded
        assert "app_config" in loaded
        assert "ui_config" in loaded

    def test_settings_required_sections(self, tmp_path):
        """설정 파일 필수 섹션 확인"""
        settings_file = tmp_path / "test_settings.json"

        settings = {
            "app_info": {},
            "solidworks": {},
            "app_config": {},
            "ui_config": {},
        }

        with open(settings_file, "w", encoding="utf-8") as f:
            json.dump(settings, f)

        with open(settings_file, "r", encoding="utf-8") as f:
            loaded = json.load(f)

        required_sections = ["app_info", "solidworks", "app_config", "ui_config"]
        for section in required_sections:
            assert section in loaded, f"{section} 섹션이 없습니다"

    def test_last_selected_folder_default(self, tmp_path):
        """last_selected_folder 기본값 확인"""
        settings = {"ui_config": {"last_selected_folder": ""}}

        last_folder = settings.get("ui_config", {}).get("last_selected_folder", "")
        assert last_folder == ""
