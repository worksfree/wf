# -*- coding: utf-8 -*-
"""
배포 전 종합 검증 테스트
인터랙티브 테스트 제외, 자동화된 검증만 수행

테스트 카테고리:
1. Spec 파일 및 번들 구조 검증
2. 경로 해석 로직 검증
3. 설정 파일 로드/저장 검증
4. 필수 모듈 Import 검증
5. 초기화 순서 검증
6. 숨김 속성 검증
"""

import os
import sys
import json
import tempfile
import shutil
import importlib
import ast
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

# 프로젝트 루트 설정
PROJECT_ROOT = Path(__file__).parent.parent.parent
COMMON_PATH = PROJECT_ROOT / "10.common"
if str(COMMON_PATH) not in sys.path:
    sys.path.insert(0, str(COMMON_PATH))

# 앱 정보
APPS = {
    "bom_exporter": PROJECT_ROOT / "30.apps" / "bom_exporter",
    "dwg_batch_print": PROJECT_ROOT / "30.apps" / "dwg_batch_print",
    "dwg_classifier": PROJECT_ROOT / "50.data" / "dwg_classifier",
    "conversion_verifier": PROJECT_ROOT / "50.data" / "conversion_verifier",
    "korean_filename_normalizer": PROJECT_ROOT / "50.data" / "korean_filename_normalizer",
    "attribute_reset": PROJECT_ROOT / "30.apps" / "attribute_reset",
}


# ============================================================================
# 1. Spec 파일 및 번들 구조 검증
# ============================================================================
class TestSpecFileValidation:
    """PyInstaller spec 파일 검증"""

    @pytest.mark.parametrize("app_name,app_path", list(APPS.items()))
    def test_spec_file_exists(self, app_name, app_path):
        """각 앱에 spec 파일이 존재하는지 확인"""
        spec_file = app_path / f"{app_name}.spec"
        assert spec_file.exists(), f"{app_name}.spec 파일이 없습니다: {spec_file}"

    @pytest.mark.parametrize("app_name,app_path", list(APPS.items()))
    def test_spec_has_wf_rpa_bundle(self, app_name, app_path):
        """spec 파일에 .wf_rpa 번들 설정이 있는지 확인"""
        spec_file = app_path / f"{app_name}.spec"
        if not spec_file.exists():
            pytest.skip(f"spec 파일 없음: {spec_file}")

        content = spec_file.read_text(encoding="utf-8")
        # datas에 .wf_rpa 관련 설정 확인
        assert ".wf_rpa" in content or "wf_rpa" in content, \
            f"{app_name}.spec에 .wf_rpa 번들 설정이 없습니다"

    @pytest.mark.parametrize("app_name,app_path", list(APPS.items()))
    def test_spec_has_policy_json(self, app_name, app_path):
        """spec 파일에 policy.json 번들 설정이 있는지 확인"""
        spec_file = app_path / f"{app_name}.spec"
        if not spec_file.exists():
            pytest.skip(f"spec 파일 없음: {spec_file}")

        content = spec_file.read_text(encoding="utf-8")
        assert "policy.json" in content or "policy" in content.lower(), \
            f"{app_name}.spec에 policy.json 번들 설정이 없습니다"

    @pytest.mark.parametrize("app_name,app_path", list(APPS.items()))
    def test_spec_has_settings_json(self, app_name, app_path):
        """spec 파일에 settings.json 번들 설정이 있는지 확인"""
        spec_file = app_path / f"{app_name}.spec"
        if not spec_file.exists():
            pytest.skip(f"spec 파일 없음: {spec_file}")

        content = spec_file.read_text(encoding="utf-8")
        assert "settings.json" in content or "settings" in content.lower(), \
            f"{app_name}.spec에 settings.json 번들 설정이 없습니다"


# ============================================================================
# 2. 경로 해석 로직 검증
# ============================================================================
class TestPathResolution:
    """경로 해석 로직 검증"""

    def test_detect_run_mode_dev(self):
        """dev 모드 감지 테스트 - .py 파일 실행"""
        # sys.argv[0]이 .py로 끝나면 dev 모드
        original_argv = sys.argv[0]
        try:
            sys.argv[0] = "ui_main.py"
            os.environ.pop("WF_RPA_MODE", None)

            # _detect_run_mode 함수 시뮬레이션
            env_mode = (os.environ.get("WF_RPA_MODE") or "").strip().lower()
            if env_mode in ("dev", "demo", "release"):
                mode = env_mode
            elif sys.argv[0].endswith(".py"):
                mode = "dev"
            else:
                mode = "release"

            assert mode == "dev", f"Expected 'dev', got '{mode}'"
        finally:
            sys.argv[0] = original_argv

    def test_detect_run_mode_release(self):
        """release 모드 감지 테스트 - exe 실행"""
        original_argv = sys.argv[0]
        try:
            sys.argv[0] = "bom_exporter.exe"
            os.environ.pop("WF_RPA_MODE", None)

            env_mode = (os.environ.get("WF_RPA_MODE") or "").strip().lower()
            if env_mode in ("dev", "demo", "release"):
                mode = env_mode
            elif sys.argv[0].endswith(".py"):
                mode = "dev"
            else:
                mode = "release"

            assert mode == "release", f"Expected 'release', got '{mode}'"
        finally:
            sys.argv[0] = original_argv

    def test_detect_run_mode_env_override(self):
        """환경변수로 모드 오버라이드 테스트"""
        original_argv = sys.argv[0]
        original_env = os.environ.get("WF_RPA_MODE")
        try:
            sys.argv[0] = "ui_main.py"  # 원래라면 dev
            os.environ["WF_RPA_MODE"] = "demo"

            env_mode = (os.environ.get("WF_RPA_MODE") or "").strip().lower()
            if env_mode in ("dev", "demo", "release"):
                mode = env_mode
            elif sys.argv[0].endswith(".py"):
                mode = "dev"
            else:
                mode = "release"

            assert mode == "demo", f"Expected 'demo', got '{mode}'"
        finally:
            sys.argv[0] = original_argv
            if original_env:
                os.environ["WF_RPA_MODE"] = original_env
            else:
                os.environ.pop("WF_RPA_MODE", None)

    @pytest.mark.parametrize("app_name", list(APPS.keys()))
    def test_config_path_dev_mode(self, app_name):
        """dev 모드에서 설정 파일 경로 검증"""
        # 10.common/config/{app_name}/settings.json 경로가 존재해야 함
        config_path = COMMON_PATH / "config" / app_name / "settings.json"
        assert config_path.exists(), \
            f"Dev 모드 설정 파일 없음: {config_path}"

    @pytest.mark.parametrize("app_name", list(APPS.keys()))
    def test_policy_path_dev_mode(self, app_name):
        """dev 모드에서 정책 파일 경로 검증"""
        policy_path = COMMON_PATH / "config" / app_name / "policy.json"
        assert policy_path.exists(), \
            f"Dev 모드 정책 파일 없음: {policy_path}"


# ============================================================================
# 3. 설정 파일 로드/저장 검증
# ============================================================================
class TestConfigLoadSave:
    """설정 파일 로드/저장 검증"""

    @pytest.mark.parametrize("app_name", list(APPS.keys()))
    def test_settings_json_valid(self, app_name):
        """settings.json이 유효한 JSON인지 확인"""
        settings_path = COMMON_PATH / "config" / app_name / "settings.json"
        if not settings_path.exists():
            pytest.skip(f"settings.json 없음: {settings_path}")

        try:
            with open(settings_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            assert isinstance(data, dict), "settings.json은 dict여야 합니다"
        except json.JSONDecodeError as e:
            pytest.fail(f"{app_name}/settings.json JSON 파싱 오류: {e}")

    @pytest.mark.parametrize("app_name", list(APPS.keys()))
    def test_policy_json_valid(self, app_name):
        """policy.json이 유효한 JSON인지 확인"""
        policy_path = COMMON_PATH / "config" / app_name / "policy.json"
        if not policy_path.exists():
            pytest.skip(f"policy.json 없음: {policy_path}")

        try:
            with open(policy_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            assert isinstance(data, dict), "policy.json은 dict여야 합니다"
        except json.JSONDecodeError as e:
            pytest.fail(f"{app_name}/policy.json JSON 파싱 오류: {e}")

    @pytest.mark.parametrize("app_name", list(APPS.keys()))
    def test_settings_has_required_keys(self, app_name):
        """settings.json에 필수 키가 있는지 확인"""
        settings_path = COMMON_PATH / "config" / app_name / "settings.json"
        if not settings_path.exists():
            pytest.skip(f"settings.json 없음: {settings_path}")

        with open(settings_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # 필수 섹션 확인 (최소한 하나는 있어야 함)
        expected_sections = ["app_config", "ui_config", "runtime_config"]
        has_section = any(key in data for key in expected_sections)
        assert has_section, \
            f"{app_name}/settings.json에 필수 섹션이 없습니다: {expected_sections}"

    @pytest.mark.parametrize("app_name", list(APPS.keys()))
    def test_policy_has_credit_fields(self, app_name):
        """policy.json에 크레딧 관련 필드가 있는지 확인"""
        policy_path = COMMON_PATH / "config" / app_name / "policy.json"
        if not policy_path.exists():
            pytest.skip(f"policy.json 없음: {policy_path}")

        with open(policy_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # 필수 크레딧 필드 확인 (중첩 구조 고려)
        def find_key(d, key):
            if key in d:
                return True
            for v in d.values():
                if isinstance(v, dict) and find_key(v, key):
                    return True
            return False

        assert find_key(data, "trial_credits") or find_key(data, "credit_per_work"), \
            f"{app_name}/policy.json에 크레딧 관련 필드가 없습니다"

    def test_wf_rpa_config_exists(self):
        """전역 설정 파일 존재 확인"""
        config_path = COMMON_PATH / "config" / "wf_rpa_config.json"
        assert config_path.exists(), f"전역 설정 파일 없음: {config_path}"

    def test_wf_rpa_config_valid(self):
        """전역 설정 파일이 유효한 JSON인지 확인"""
        config_path = COMMON_PATH / "config" / "wf_rpa_config.json"
        if not config_path.exists():
            pytest.skip("wf_rpa_config.json 없음")

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            assert isinstance(data, dict)
        except json.JSONDecodeError as e:
            pytest.fail(f"wf_rpa_config.json JSON 파싱 오류: {e}")


# ============================================================================
# 4. 필수 모듈 Import 검증
# ============================================================================
class TestModuleImports:
    """필수 모듈 Import 검증"""

    def test_import_wf_credit_manager(self):
        """wf_credit_manager 모듈 import 확인"""
        try:
            import wf_credit_manager
            assert hasattr(wf_credit_manager, "WorksFreeManager")
            assert hasattr(wf_credit_manager, "CreditManager")
        except ImportError as e:
            pytest.fail(f"wf_credit_manager import 실패: {e}")

    def test_import_wf_register(self):
        """wf_register 모듈 import 확인"""
        try:
            import wf_register
            assert hasattr(wf_register, "TrialRegistrationWindow")
        except ImportError as e:
            pytest.fail(f"wf_register import 실패: {e}")

    def test_import_wf_log(self):
        """wf_log 모듈 import 확인"""
        try:
            import wf_log
            assert hasattr(wf_log, "get_app_logger")
        except ImportError as e:
            pytest.fail(f"wf_log import 실패: {e}")

    def test_import_wf_googlesheets_manager(self):
        """wf_googlesheets_manager 모듈 import 확인"""
        try:
            import wf_googlesheets_manager
            assert hasattr(wf_googlesheets_manager, "GoogleSheetsManager")
        except ImportError as e:
            pytest.fail(f"wf_googlesheets_manager import 실패: {e}")

    def test_import_wf_hwinfo(self):
        """wf_hwinfo 모듈 import 확인"""
        try:
            import wf_hwinfo
            # HardwareInfo 클래스를 사용하여 fingerprint 생성
            assert hasattr(wf_hwinfo, "HardwareInfo")
        except ImportError as e:
            pytest.fail(f"wf_hwinfo import 실패: {e}")

    def test_import_wf_settings_common(self):
        """wf_settings_common 모듈 import 확인"""
        try:
            import wf_settings_common
        except ImportError as e:
            pytest.fail(f"wf_settings_common import 실패: {e}")

    @pytest.mark.parametrize("app_name,app_path", list(APPS.items()))
    def test_import_app_setting_data(self, app_name, app_path):
        """각 앱의 app_setting_data 모듈 import 확인"""
        if str(app_path) not in sys.path:
            sys.path.insert(0, str(app_path))
        try:
            # 모듈 캐시 제거 후 import
            if "app_setting_data" in sys.modules:
                del sys.modules["app_setting_data"]

            import app_setting_data
            assert hasattr(app_setting_data, "get_config"), \
                f"{app_name}/app_setting_data에 get_config 없음"
        except ImportError as e:
            pytest.fail(f"{app_name}/app_setting_data import 실패: {e}")
        finally:
            if str(app_path) in sys.path:
                sys.path.remove(str(app_path))
            if "app_setting_data" in sys.modules:
                del sys.modules["app_setting_data"]


# ============================================================================
# 5. 초기화 순서 검증
# ============================================================================
class TestInitializationSequence:
    """초기화 순서 검증"""

    @pytest.mark.parametrize("app_name,app_path", list(APPS.items()))
    def test_ui_main_has_detect_run_mode(self, app_name, app_path):
        """ui_main.py에 _detect_run_mode 함수가 있는지 확인"""
        ui_main_path = app_path / "ui_main.py"
        if not ui_main_path.exists():
            pytest.skip(f"ui_main.py 없음: {ui_main_path}")

        content = ui_main_path.read_text(encoding="utf-8")
        assert "_detect_run_mode" in content, \
            f"{app_name}/ui_main.py에 _detect_run_mode 함수가 없습니다"

    @pytest.mark.parametrize("app_name,app_path", list(APPS.items()))
    def test_ui_main_has_single_instance(self, app_name, app_path):
        """ui_main.py에 단일 인스턴스 락이 있는지 확인"""
        ui_main_path = app_path / "ui_main.py"
        if not ui_main_path.exists():
            pytest.skip(f"ui_main.py 없음: {ui_main_path}")

        content = ui_main_path.read_text(encoding="utf-8")
        # 뮤텍스 관련 키워드 확인
        has_mutex = "Mutex" in content or "mutex" in content or "_acquire_single_instance" in content
        assert has_mutex, \
            f"{app_name}/ui_main.py에 단일 인스턴스 락이 없습니다"

    @pytest.mark.parametrize("app_name,app_path", list(APPS.items()))
    def test_ui_main_has_geometry_capture(self, app_name, app_path):
        """ui_main.py에 Alt+G geometry 캡처가 있는지 확인"""
        ui_main_path = app_path / "ui_main.py"
        if not ui_main_path.exists():
            pytest.skip(f"ui_main.py 없음: {ui_main_path}")

        content = ui_main_path.read_text(encoding="utf-8")
        assert "Alt-g" in content or "Alt-G" in content or "_on_debug_geometry_capture" in content, \
            f"{app_name}/ui_main.py에 Alt+G geometry 캡처가 없습니다"

    @pytest.mark.parametrize("app_name,app_path", list(APPS.items()))
    def test_app_setting_has_geometry_methods(self, app_name, app_path):
        """app_setting_data.py에 geometry 저장 메서드가 있는지 확인"""
        setting_path = app_path / "app_setting_data.py"
        if not setting_path.exists():
            pytest.skip(f"app_setting_data.py 없음: {setting_path}")

        content = setting_path.read_text(encoding="utf-8")
        # 3개 geometry 저장 메서드 확인
        methods = [
            "update_window_geometry_override",
            "update_settings_window_geometry",
            "update_registration_window_geometry"
        ]
        for method in methods:
            assert method in content, \
                f"{app_name}/app_setting_data.py에 {method} 메서드가 없습니다"


# ============================================================================
# 6. 숨김 속성 검증
# ============================================================================
class TestHiddenAttributes:
    """숨김 속성 관련 검증"""

    def test_credit_manager_has_set_hidden(self):
        """wf_credit_manager에 _set_hidden_attribute 메서드가 있는지 확인"""
        credit_manager_path = COMMON_PATH / "wf_credit_manager.py"
        content = credit_manager_path.read_text(encoding="utf-8")
        assert "_set_hidden_attribute" in content, \
            "wf_credit_manager.py에 _set_hidden_attribute 메서드가 없습니다"

    def test_credit_manager_hides_wf_rpa_dir(self):
        """wf_credit_manager가 .wf_rpa 폴더를 숨김 처리하는지 확인"""
        credit_manager_path = COMMON_PATH / "wf_credit_manager.py"
        content = credit_manager_path.read_text(encoding="utf-8")
        # 숨김 처리 호출 확인
        assert "_set_hidden_attribute(self.wf_rpa_dir)" in content or \
               "_set_hidden_attribute(self.app_dir)" in content, \
            "wf_credit_manager.py에서 폴더 숨김 처리가 누락되었습니다"

    def test_hidden_only_in_release_mode(self):
        """숨김 처리가 release 모드에서만 적용되는지 확인"""
        credit_manager_path = COMMON_PATH / "wf_credit_manager.py"
        content = credit_manager_path.read_text(encoding="utf-8")
        # is_dev_mode 체크 확인
        assert "is_dev_mode" in content, \
            "wf_credit_manager.py에서 개발 모드 체크가 없습니다"


# ============================================================================
# 7. 크리덴셜 파일 검증
# ============================================================================
class TestCredentialsValidation:
    """Google Sheets 크리덴셜 검증"""

    def test_credentials_file_exists(self):
        """silver-argon-*.json 크리덴셜 파일 존재 확인"""
        # 10.common/config/ 에서 확인
        config_dir = COMMON_PATH / "config"
        cred_files = list(config_dir.glob("silver-argon*.json")) + \
                     list(config_dir.glob("worksfree-*.json"))
        assert len(cred_files) > 0, \
            f"크리덴셜 파일이 없습니다: {config_dir}/silver-argon-*.json or worksfree-*.json"

    def test_credentials_file_valid_json(self):
        """크리덴셜 파일이 유효한 JSON인지 확인"""
        config_dir = COMMON_PATH / "config"
        cred_files = list(config_dir.glob("silver-argon*.json")) + \
                     list(config_dir.glob("worksfree-*.json"))
        if not cred_files:
            pytest.skip("크리덴셜 파일 없음")

        for cred_file in cred_files:
            try:
                with open(cred_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                assert "type" in data and data["type"] == "service_account", \
                    f"크리덴셜 파일이 service_account 타입이 아닙니다: {cred_file}"
            except json.JSONDecodeError as e:
                pytest.fail(f"크리덴셜 파일 JSON 파싱 오류: {cred_file} - {e}")


# ============================================================================
# 8. 버전 일관성 검증
# ============================================================================
class TestVersionConsistency:
    """버전 정보 일관성 검증"""

    @pytest.mark.parametrize("app_name", list(APPS.keys()))
    def test_settings_has_version(self, app_name):
        """settings.json에 버전 정보가 있는지 확인"""
        settings_path = COMMON_PATH / "config" / app_name / "settings.json"
        if not settings_path.exists():
            pytest.skip(f"settings.json 없음: {settings_path}")

        with open(settings_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # 버전 필드 확인 (여러 위치 가능)
        def find_version(d):
            for key in ["full_version", "version", "app_version"]:
                if key in d:
                    return d[key]
            for v in d.values():
                if isinstance(v, dict):
                    result = find_version(v)
                    if result:
                        return result
            return None

        version = find_version(data)
        assert version, f"{app_name}/settings.json에 버전 정보가 없습니다"


# ============================================================================
# 9. UI 설정 파일 검증
# ============================================================================
class TestUISettingFiles:
    """ui_setting.py 파일 검증"""

    @pytest.mark.parametrize("app_name,app_path", list(APPS.items()))
    def test_ui_setting_exists(self, app_name, app_path):
        """ui_setting.py 파일 존재 확인"""
        ui_setting_path = app_path / "ui_setting.py"
        assert ui_setting_path.exists(), f"{app_name}/ui_setting.py 파일이 없습니다"

    @pytest.mark.parametrize("app_name,app_path", list(APPS.items()))
    def test_ui_setting_has_geometry_capture(self, app_name, app_path):
        """ui_setting.py에 Alt+G geometry 캡처가 있는지 확인"""
        ui_setting_path = app_path / "ui_setting.py"
        if not ui_setting_path.exists():
            pytest.skip(f"ui_setting.py 없음: {ui_setting_path}")

        content = ui_setting_path.read_text(encoding="utf-8")
        assert "Alt-g" in content or "Alt-G" in content or "_on_debug_geometry_capture" in content, \
            f"{app_name}/ui_setting.py에 Alt+G geometry 캡처가 없습니다"


# ============================================================================
# 10. wf_register.py 검증
# ============================================================================
class TestWfRegisterValidation:
    """wf_register.py 검증"""

    def test_wf_register_has_geometry_capture(self):
        """wf_register.py에 Alt+G geometry 캡처가 있는지 확인"""
        register_path = COMMON_PATH / "wf_register.py"
        content = register_path.read_text(encoding="utf-8")
        assert "_on_debug_geometry_capture" in content, \
            "wf_register.py에 _on_debug_geometry_capture 메서드가 없습니다"

    def test_wf_register_has_toast(self):
        """wf_register.py에 토스트 메시지가 있는지 확인"""
        register_path = COMMON_PATH / "wf_register.py"
        content = register_path.read_text(encoding="utf-8")
        assert "_show_geometry_toast" in content, \
            "wf_register.py에 _show_geometry_toast 메서드가 없습니다"

    def test_wf_register_saves_geometry(self):
        """wf_register.py에서 geometry를 저장하는지 확인"""
        register_path = COMMON_PATH / "wf_register.py"
        content = register_path.read_text(encoding="utf-8")
        assert "update_registration_window_geometry" in content, \
            "wf_register.py에서 registration_window_geometry 저장이 없습니다"


# ============================================================================
# 실행
# ============================================================================
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
