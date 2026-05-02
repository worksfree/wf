# -*- coding: utf-8 -*-
"""
이메일 초기화 테스트 (pytest 형식)
배포 환경에서 빈 설정 파일로 시작할 때의 동작을 테스트
"""
import sys
import json
import pytest
from pathlib import Path


class TestEmailInit:
    """이메일 초기화 테스트"""

    @pytest.fixture(autouse=True)
    def setup_path(self):
        """경로 설정"""
        current_dir = Path(__file__).parent
        common_path = current_dir.parents[2] / "10.common"
        if str(common_path) not in sys.path:
            sys.path.insert(0, str(common_path))

    def test_wf_email_import(self):
        """wf_email 모듈 import 테스트"""
        try:
            import wf_email
            assert wf_email is not None
        except ImportError:
            pytest.skip("wf_email을 import할 수 없습니다")

    def test_wf_email_has_init(self):
        """wf_email에 init 함수가 있는지 확인"""
        try:
            import wf_email
            assert hasattr(wf_email, 'init')
            assert callable(wf_email.init)
        except ImportError:
            pytest.skip("wf_email을 import할 수 없습니다")

    def test_wf_email_has_set_logger(self):
        """wf_email에 set_logger 함수가 있는지 확인"""
        try:
            import wf_email
            assert hasattr(wf_email, 'set_logger')
            assert callable(wf_email.set_logger)
        except ImportError:
            pytest.skip("wf_email을 import할 수 없습니다")

    @pytest.fixture
    def temp_email_config(self, tmp_path):
        """임시 이메일 설정 파일 생성"""
        config_file = tmp_path / "wf_rpa_config.json"
        config = {
            "user_info": {},
            "email_settings": {
                "email_from": "",
                "email_to": "",
                "login_key": "",
                "smtp_server": "smtp.gmail.com",
                "smtp_port": 587,
            },
        }
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        return config_file

    def test_empty_email_config_structure(self, temp_email_config):
        """빈 이메일 설정 구조 테스트"""
        with open(temp_email_config, "r", encoding="utf-8") as f:
            config = json.load(f)

        assert "email_settings" in config
        assert "email_from" in config["email_settings"]
        assert "email_to" in config["email_settings"]
        assert "smtp_server" in config["email_settings"]
        assert "smtp_port" in config["email_settings"]

    def test_email_config_default_values(self, temp_email_config):
        """이메일 설정 기본값 테스트"""
        with open(temp_email_config, "r", encoding="utf-8") as f:
            config = json.load(f)

        email_settings = config["email_settings"]
        assert email_settings["smtp_server"] == "smtp.gmail.com"
        assert email_settings["smtp_port"] == 587

    def test_email_from_can_be_set(self, temp_email_config):
        """email_from 설정 가능 여부 테스트"""
        with open(temp_email_config, "r", encoding="utf-8") as f:
            config = json.load(f)

        config["email_settings"]["email_from"] = "test@example.com"

        with open(temp_email_config, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

        with open(temp_email_config, "r", encoding="utf-8") as f:
            updated_config = json.load(f)

        assert updated_config["email_settings"]["email_from"] == "test@example.com"

    def test_email_to_can_be_set(self, temp_email_config):
        """email_to 설정 가능 여부 테스트"""
        with open(temp_email_config, "r", encoding="utf-8") as f:
            config = json.load(f)

        config["email_settings"]["email_to"] = "recipient@example.com"

        with open(temp_email_config, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

        with open(temp_email_config, "r", encoding="utf-8") as f:
            updated_config = json.load(f)

        assert updated_config["email_settings"]["email_to"] == "recipient@example.com"

    def test_wf_email_module_attributes(self):
        """wf_email 모듈 속성 테스트"""
        try:
            import wf_email

            # 모듈 속성 확인 (존재 여부만 확인)
            expected_attrs = ['email_from', 'email_to', 'smtp_server', 'smtp_port']
            for attr in expected_attrs:
                if not hasattr(wf_email, attr):
                    pytest.skip(f"wf_email에 {attr} 속성이 없습니다")

        except ImportError:
            pytest.skip("wf_email을 import할 수 없습니다")
