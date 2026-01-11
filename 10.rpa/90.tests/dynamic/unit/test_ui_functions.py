"""
UI 주요 함수 유닛 테스트
각 앱의 핵심 UI 함수들을 테스트합니다.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# 프로젝트 루트 경로 추가
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "10.common"))


@pytest.mark.unit
class TestDWGClassifierFunctions:
    """DWG Classifier UI 함수 테스트"""

    def test_check_user_registration_exists(self):
        """check_user_registration 함수가 존재하는지 확인"""
        sys.path.insert(0, str(PROJECT_ROOT / "50.data" / "dwg_classifier"))

        # 모듈 임포트 시도
        try:
            from ui_main import DwgClassifierApp

            assert hasattr(DwgClassifierApp, "check_user_registration")
        except ImportError as e:
            pytest.skip(f"모듈 임포트 실패: {e}")

    def test_update_credit_display_exists(self):
        """update_credit_display 함수가 존재하는지 확인"""
        sys.path.insert(0, str(PROJECT_ROOT / "50.data" / "dwg_classifier"))

        try:
            from ui_main import DwgClassifierApp

            assert hasattr(DwgClassifierApp, "update_credit_display")
        except ImportError as e:
            pytest.skip(f"모듈 임포트 실패: {e}")

    def test_post_registration_update_exists(self):
        """post_registration_update 함수가 존재하는지 확인"""
        sys.path.insert(0, str(PROJECT_ROOT / "50.data" / "dwg_classifier"))

        try:
            from ui_main import DwgClassifierApp

            assert hasattr(DwgClassifierApp, "post_registration_update")
        except ImportError as e:
            pytest.skip(f"모듈 임포트 실패: {e}")

    def test_open_settings_window_exists(self):
        """open_settings_window 함수가 존재하는지 확인"""
        sys.path.insert(0, str(PROJECT_ROOT / "50.data" / "dwg_classifier"))

        try:
            from ui_main import DwgClassifierApp

            assert hasattr(DwgClassifierApp, "open_settings_window")
        except ImportError as e:
            pytest.skip(f"모듈 임포트 실패: {e}")

    def test_open_registration_window_exists(self):
        """open_registration_window 함수가 존재하는지 확인"""
        sys.path.insert(0, str(PROJECT_ROOT / "50.data" / "dwg_classifier"))

        try:
            from ui_main import DwgClassifierApp

            assert hasattr(DwgClassifierApp, "open_registration_window")
        except ImportError as e:
            pytest.skip(f"모듈 임포트 실패: {e}")


@pytest.mark.unit
class TestBOM2ExcelFunctions:
    """BOM2Excel UI 함수 테스트"""

    def test_function_naming_consistency(self):
        """함수명 일관성 확인"""
        # 기존 ui_main 모듈 캐시 제거
        if "ui_main" in sys.modules:
            del sys.modules["ui_main"]

        sys.path.insert(0, str(PROJECT_ROOT / "30.apps" / "bom_exporter"))

        try:
            from ui_main import BomGUIApplication

            # 필수 함수들이 존재하는지 확인
            required_functions = [
                "check_user_registration",
                "update_credit_display",
                "post_registration_update",
                "open_settings_window",
                "open_registration_window",
                "on_refresh_credit",
            ]

            for func_name in required_functions:
                assert hasattr(BomGUIApplication, func_name), f"{func_name} 함수가 없습니다"

        except ImportError as e:
            pytest.skip(f"모듈 임포트 실패: {e}")


@pytest.mark.unit
class TestConversionVerifierFunctions:
    """Conversion Verifier UI 함수 테스트"""

    def test_function_naming_consistency(self):
        """함수명 일관성 확인"""
        # 기존 ui_main 모듈 캐시 제거
        if "ui_main" in sys.modules:
            del sys.modules["ui_main"]

        sys.path.insert(0, str(PROJECT_ROOT / "50.data" / "conversion_verifier"))

        try:
            from ui_main import ConversionVerifierApp

            required_functions = [
                "check_user_registration",
                "update_credit_display",
                "post_registration_update",
                "open_settings_window",
                "open_registration_window",
                "on_refresh_credit",
            ]

            for func_name in required_functions:
                assert hasattr(ConversionVerifierApp, func_name), f"{func_name} 함수가 없습니다"

        except ImportError as e:
            pytest.skip(f"모듈 임포트 실패: {e}")


@pytest.mark.unit
class TestKoreanFilenameNormalizerFunctions:
    """Korean Filename Normalizer UI 함수 테스트"""

    def test_function_naming_consistency(self):
        """함수명 일관성 확인"""
        # 기존 ui_main 모듈 캐시 제거
        if "ui_main" in sys.modules:
            del sys.modules["ui_main"]

        sys.path.insert(0, str(PROJECT_ROOT / "50.data" / "korean_filename_normalizer"))

        try:
            from ui_main import KoreanFilenameNormalizerApp

            required_functions = [
                "check_user_registration",
                "update_credit_display",
                "post_registration_update",
                "open_settings_window",
                "open_registration_window",
                "on_refresh_credit",
            ]

            for func_name in required_functions:
                assert hasattr(
                    KoreanFilenameNormalizerApp, func_name
                ), f"{func_name} 함수가 없습니다"

        except ImportError as e:
            pytest.skip(f"모듈 임포트 실패: {e}")


@pytest.mark.unit
class TestFunctionNamingConvention:
    """모든 앱의 함수명 컨벤션 통일성 테스트"""

    def test_all_apps_have_consistent_functions(self):
        """4개 앱 모두 동일한 함수명을 사용하는지 확인"""
        apps = [
            ("50.data/dwg_classifier", "DwgClassifierApp"),
            ("30.apps/bom_exporter", "BomGUIApplication"),
            ("50.data/conversion_verifier", "ConversionVerifierApp"),
            ("50.data/korean_filename_normalizer", "KoreanFilenameNormalizerApp"),
        ]

        # 모든 앱에 있어야 하는 핵심 함수들
        core_functions = [
            "check_user_registration",
            "verify_hardware_fingerprint",
            "post_registration_update",
            "open_settings_window",
            "open_registration_window",
            "update_credit_display",
            "on_refresh_credit",
            "_enter_admin_mode",
            "_exit_admin_mode",
            "create_log_frame",
            "setup_log_handler",
            "remove_log_handler",
        ]

        missing_functions = {}

        for app_path, class_name in apps:
            # 기존 ui_main 모듈 캐시 제거
            if "ui_main" in sys.modules:
                del sys.modules["ui_main"]

            sys.path.insert(0, str(PROJECT_ROOT / app_path))

            try:
                module = __import__("ui_main")
                ui_class = getattr(module, class_name)

                # sys.path 정리
                sys.path.remove(str(PROJECT_ROOT / app_path))

                app_missing = []
                for func_name in core_functions:
                    if not hasattr(ui_class, func_name):
                        app_missing.append(func_name)

                if app_missing:
                    missing_functions[class_name] = app_missing

            except ImportError:
                pytest.skip(f"{class_name} 임포트 실패")

        # 누락된 함수가 있으면 실패
        if missing_functions:
            error_msg = "\n함수명 불일치 발견:\n"
            for app, funcs in missing_functions.items():
                error_msg += f"  {app}: {', '.join(funcs)}\n"
            pytest.fail(error_msg)


@pytest.mark.unit
class TestAdminModeFunctions:
    """관리자 모드 함수 테스트"""

    def test_admin_mode_functions_exist(self):
        """모든 앱에 관리자 모드 함수가 있는지 확인"""
        apps = [
            ("50.data/dwg_classifier", "DwgClassifierApp"),
            ("30.apps/bom_exporter", "BomGUIApplication"),
            ("50.data/conversion_verifier", "ConversionVerifierApp"),
            ("50.data/korean_filename_normalizer", "KoreanFilenameNormalizerApp"),
        ]

        admin_functions = [
            "_enter_admin_mode",
            "_exit_admin_mode",
            "create_log_frame",
            "destroy_log_frame",
            "setup_log_handler",
            "remove_log_handler",
        ]

        for app_path, class_name in apps:
            # 기존 ui_main 모듈 캐시 제거
            if "ui_main" in sys.modules:
                del sys.modules["ui_main"]

            sys.path.insert(0, str(PROJECT_ROOT / app_path))

            try:
                module = __import__("ui_main")
                ui_class = getattr(module, class_name)

                # sys.path 정리
                sys.path.remove(str(PROJECT_ROOT / app_path))

                for func_name in admin_functions:
                    assert hasattr(
                        ui_class, func_name
                    ), f"{class_name}에 {func_name} 함수가 없습니다"

            except ImportError:
                pytest.skip(f"{class_name} 임포트 실패")


@pytest.mark.unit
class TestStartFunctionPattern:
    """start_* 패턴 함수 테스트"""

    def test_main_action_functions(self):
        """각 앱의 메인 실행 함수가 start_* 패턴을 따르는지 확인"""
        expected_functions = {
            "DwgClassifierApp": "start_classification",
            "BomGUIApplication": "start_bom_extraction",
            "ConversionVerifierApp": "start_conversion_check",
            "KoreanFilenameNormalizerApp": "start_normalization",
        }

        apps = [
            ("50.data/dwg_classifier", "DwgClassifierApp"),
            ("30.apps/bom_exporter", "BomGUIApplication"),
            ("50.data/conversion_verifier", "ConversionVerifierApp"),
            ("50.data/korean_filename_normalizer", "KoreanFilenameNormalizerApp"),
        ]

        for app_path, class_name in apps:
            # 기존 ui_main 모듈 캐시 제거
            if "ui_main" in sys.modules:
                del sys.modules["ui_main"]

            sys.path.insert(0, str(PROJECT_ROOT / app_path))

            try:
                module = __import__("ui_main")
                ui_class = getattr(module, class_name)

                # sys.path 정리
                sys.path.remove(str(PROJECT_ROOT / app_path))

                expected_func = expected_functions[class_name]
                assert hasattr(
                    ui_class, expected_func
                ), f"{class_name}에 {expected_func} 함수가 없습니다"

            except ImportError:
                pytest.skip(f"{class_name} 임포트 실패")
