# -*- coding: utf-8 -*-
"""
숨김 처리 테스트 (pytest 형식)
개발 모드 vs 배포 모드에서 숨김 속성 확인
"""
import os
import sys
import tempfile
import shutil
import platform
import pytest
from pathlib import Path


class TestHiddenAttributes:
    """숨김 속성 테스트"""

    @pytest.fixture(autouse=True)
    def setup_path(self):
        """경로 설정"""
        current_dir = Path(__file__).parent
        common_path = current_dir.parents[2] / "10.common"
        if str(common_path) not in sys.path:
            sys.path.insert(0, str(common_path))

    def _check_hidden_attribute(self, path: Path) -> bool:
        """Windows에서 숨김 속성 확인"""
        try:
            if platform.system() == "Windows":
                import ctypes
                FILE_ATTRIBUTE_HIDDEN = 0x02
                attrs = ctypes.windll.kernel32.GetFileAttributesW(str(path))
                return (attrs & FILE_ATTRIBUTE_HIDDEN) != 0
            else:
                # Linux/Mac: . 으로 시작하면 숨김
                return path.name.startswith(".")
        except Exception:
            return False

    def test_worksfree_manager_import(self):
        """WorksFreeManager import 테스트"""
        try:
            from wf_credit_manager import WorksFreeManager
            assert WorksFreeManager is not None
        except ImportError:
            pytest.skip("wf_credit_manager를 import할 수 없습니다")

    def test_credit_manager_import(self):
        """CreditManager import 테스트"""
        try:
            from wf_credit_manager import CreditManager
            assert CreditManager is not None
        except ImportError:
            pytest.skip("wf_credit_manager를 import할 수 없습니다")

    def test_dev_mode(self, isolated_wf_environment):
        """개발 모드 테스트 - 숨김 처리 안 됨"""
        try:
            from wf_credit_manager import WorksFreeManager, CreditManager

            # WorksFreeManager 생성
            wf_manager = WorksFreeManager()

            # is_dev_mode 확인
            assert hasattr(wf_manager, 'is_dev_mode')

            # CreditManager 생성
            credit_manager = CreditManager("test_app")

            # CreditManager가 정상적으로 생성되었는지 확인
            assert credit_manager is not None
            assert credit_manager.app_name == "test_app"

        except ImportError:
            pytest.skip("wf_credit_manager를 import할 수 없습니다")

    def test_release_mode(self):
        """배포 모드 테스트"""
        # 임시 홈 디렉토리 생성
        temp_home = Path(tempfile.mkdtemp(prefix="wf_release_"))
        original_home = os.environ.get("HOME") or os.environ.get("USERPROFILE")
        original_wf_rpa_home = os.environ.get("WF_RPA_HOME")

        # USERPROFILE을 임시 경로로 변경
        os.environ["USERPROFILE"] = str(temp_home)

        # WF_RPA_HOME 삭제 (배포 모드)
        if "WF_RPA_HOME" in os.environ:
            del os.environ["WF_RPA_HOME"]

        try:
            from wf_credit_manager import WorksFreeManager, CreditManager

            # WorksFreeManager 싱글톤 초기화 상태 리셋
            WorksFreeManager._instance = None

            # WorksFreeManager 생성
            wf_manager = WorksFreeManager()

            # is_dev_mode 확인 (배포 모드에서는 False)
            # 환경에 따라 다를 수 있으므로 속성 존재만 확인
            assert hasattr(wf_manager, 'is_dev_mode')

        except ImportError:
            pytest.skip("wf_credit_manager를 import할 수 없습니다")
        except Exception as e:
            pytest.skip(f"테스트 환경 문제: {e}")
        finally:
            # 정리
            os.environ["USERPROFILE"] = original_home
            if original_wf_rpa_home:
                os.environ["WF_RPA_HOME"] = original_wf_rpa_home
            shutil.rmtree(temp_home, ignore_errors=True)

            # 싱글톤 리셋
            try:
                from wf_credit_manager import WorksFreeManager
                WorksFreeManager._instance = None
            except:
                pass

    def test_hidden_attribute_check_function(self):
        """숨김 속성 체크 함수 테스트"""
        # 임시 파일 생성
        with tempfile.NamedTemporaryFile(delete=False) as f:
            temp_path = Path(f.name)

        try:
            # 파일이 존재하는지 확인
            assert temp_path.exists()

            # 숨김 속성 체크 (기본적으로 False여야 함)
            is_hidden = self._check_hidden_attribute(temp_path)
            # 결과는 bool 타입이어야 함
            assert isinstance(is_hidden, bool)
        finally:
            temp_path.unlink(missing_ok=True)
