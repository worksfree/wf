# -*- coding: utf-8 -*-
"""
Pytest 공통 Fixture 설정
모든 테스트에서 공유하는 fixture와 설정
"""

import os
import sys
import pytest
import tempfile
import shutil
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

# ============================================================================
# UTF-8 TextIOWrapper 충돌 방지
# pytest의 capture 시스템과 TextIOWrapper가 충돌하는 문제 해결
# ============================================================================
_original_stdout = sys.stdout
_original_stderr = sys.stderr

def _restore_stdio():
    """원래 stdout/stderr 복원 (pytest cleanup 전에 호출)"""
    import sys
    import io
    # TextIOWrapper가 적용된 경우 원래 스트림으로 복원
    if hasattr(sys.stdout, 'buffer') and isinstance(sys.stdout, io.TextIOWrapper):
        try:
            if not sys.stdout.closed:
                sys.stdout.flush()
        except:
            pass
    if hasattr(sys.stderr, 'buffer') and isinstance(sys.stderr, io.TextIOWrapper):
        try:
            if not sys.stderr.closed:
                sys.stderr.flush()
        except:
            pass

# Python 경로에 10.common 추가
project_root = Path(__file__).parent.parent
common_path = project_root / "10.common"
if str(common_path) not in sys.path:
    sys.path.insert(0, str(common_path))


# ============================================================================
# 환경 설정 Fixtures
# ============================================================================


@pytest.fixture(scope="session")
def project_root_path():
    """프로젝트 루트 경로 반환"""
    return Path(__file__).parent.parent


@pytest.fixture(scope="function")
def temp_wf_rpa_home(tmp_path):
    """
    테스트용 임시 WF_RPA_HOME 디렉토리 생성
    각 테스트마다 독립된 환경 제공

    Usage:
        def test_something(temp_wf_rpa_home):
            # temp_wf_rpa_home은 Path 객체
            credit_file = temp_wf_rpa_home / "bom2excel" / ".bom2excel_credits.json"
    """
    wf_home = tmp_path / ".wf_rpa"
    wf_home.mkdir()

    # 환경변수 설정
    original_home = os.environ.get("WF_RPA_HOME")
    os.environ["WF_RPA_HOME"] = str(wf_home)

    yield wf_home

    # 정리
    if original_home:
        os.environ["WF_RPA_HOME"] = original_home
    else:
        os.environ.pop("WF_RPA_HOME", None)


@pytest.fixture(scope="function")
def isolated_wf_environment(temp_wf_rpa_home):
    """
    완전히 격리된 WorksFree 환경
    WF_RPA_HOME 설정 + 싱글톤 초기화

    Usage:
        def test_credit_manager(isolated_wf_environment):
            from wf_credit_manager import WorksFreeManager
            wf_manager = WorksFreeManager()  # 독립된 인스턴스
    """
    # WorksFreeManager 싱글톤 초기화 (lazy import)
    try:
        from wf_credit_manager import WorksFreeManager

        WorksFreeManager._instance = None
        if hasattr(WorksFreeManager, "_initialized"):
            delattr(WorksFreeManager, "_initialized")
    except ImportError:
        pass

    yield temp_wf_rpa_home

    # 정리: 싱글톤 리셋
    try:
        from wf_credit_manager import WorksFreeManager

        WorksFreeManager._instance = None
    except ImportError:
        pass


@pytest.fixture(scope="function")
def auto_registered_user(isolated_wf_environment):
    """
    테스트용 기본 사용자 자동 등록
    - WorksFreeManager를 사용해 테스트 환경의 설정에 사용자 이메일/하드웨어 지문을 기록합니다.
    - 등록이 필요한 크레딧 차감 테스트에서 사용합니다.
    """
    try:
        from wf_credit_manager import WorksFreeManager

        wm = WorksFreeManager()
        # 고정값 사용 (테스트 전용)
        wm.register_user("test@example.com", "TEST_HW_FP")
        return wm
    except ImportError:
        return None


@pytest.fixture(autouse=True)
def isolated_wf_home(tmp_path, monkeypatch):
    wf_home = tmp_path / "wf_home"
    (wf_home / ".wf_rpa").mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("WF_RPA_HOME", str(wf_home))
    yield
    try:
        shutil.rmtree(wf_home, ignore_errors=True)
    except Exception:
        pass


# ============================================================================
# Mock Fixtures
# ============================================================================


@pytest.fixture
def mock_google_sheets():
    """
    Google Sheets Manager 모킹
    실제 API 호출 없이 테스트 가능

    Usage:
        def test_sync(mock_google_sheets):
            mock_google_sheets.read_sheet.return_value = [['header'], ['data']]
            # 테스트 진행...
    """
    with patch("wf_googlesheets_manager.GoogleSheetsManager") as mock:
        mock_instance = MagicMock()
        mock.return_value = mock_instance

        # 기본 반환값 설정
        mock_instance.read_sheet.return_value = []
        mock_instance.append_to_sheet.return_value = True
        mock_instance.update_cell.return_value = True

        yield mock_instance


@pytest.fixture
def mock_credit_manager_sheets(monkeypatch):
    """
    CreditManager의 Google Sheets 호출을 모킹
    실제 시트 접근이 필요한 메서드를 모킹하여 테스트 격리

    Usage:
        def test_flush_log(mock_credit_manager_sheets):
            # flush_usage_log 호출 시 실제 시트에 기록되지 않음
    """

    def mock_append(*args, **kwargs):
        """모킹된 append 함수 - 아무것도 하지 않음"""
        return True

    # CreditManager에 _append_to_usage_log_sheet 메서드가 있으면 패치
    try:
        from wf_credit_manager import CreditManager

        if hasattr(CreditManager, "_append_to_usage_log_sheet"):
            monkeypatch.setattr(CreditManager, "_append_to_usage_log_sheet", mock_append)
    except (ImportError, AttributeError):
        pass

    yield mock_append


@pytest.fixture
def mock_hardware_info():
    """
    하드웨어 정보 모킹
    실제 하드웨어 정보 수집 없이 테스트

    Usage:
        def test_registration(mock_hardware_info):
            # wf_hwinfo.HardwareInfo() 호출 시 모킹된 값 반환
    """
    with patch("wf_hwinfo.HardwareInfo") as mock:
        mock_instance = MagicMock()
        mock_instance.cpu_id = "MOCK_CPU_ID"
        mock_instance.mainboard_id = "MOCK_MB_ID"
        mock_instance.fingerprint = "mock_fingerprint_hash"
        # 신규 필드: storage_id 모킹
        mock_instance.storage_id = "MOCK_STORAGE_ID"
        mock.return_value = mock_instance

        yield mock_instance


# ============================================================================
# 데이터 Fixtures
# ============================================================================


@pytest.fixture
def sample_credit_data():
    """테스트용 샘플 크레딧 데이터"""
    return {
        "app_policy": {
            "description": "테스트 앱",
            "trial_credits": 1000,
            "credit_per_work": 1,
            "credit_type": "per_item",
        },
        "credit_changed": False,
        "trial_credits": 500,
        "purchased_credits": 2000,
        "created_at": "2025-10-18T10:00:00.000",
        "last_updated": "2025-10-18T10:00:00.000",
        "purchase_history": [],
        "usage_history": [],
    }


@pytest.fixture
def sample_unlimited_credit_data():
    """무제한 크레딧 데이터"""
    return {
        "app_policy": {
            "description": "무료 앱",
            "trial_credits": -1,
            "credit_per_work": 0,
            "credit_type": "free",
        },
        "credit_changed": False,
        "trial_credits": -1,
        "purchased_credits": 0,
        "created_at": "2025-10-18T10:00:00.000",
        "last_updated": "2025-10-18T10:00:00.000",
        "purchase_history": [],
        "usage_history": [],
    }


@pytest.fixture
def sample_user_config():
    """테스트용 샘플 사용자 설정"""
    return {
        "user_info": {
            "user_mail": "test@example.com",
            "is_registered": True,
            "registration_date": "2025-10-18T10:00:00.000",
            "hardware_fingerprint": "test_fingerprint",
        },
        "app_settings": {"theme": "light", "language": "ko"},
        "email_settings": {
            "use_local_email_config": False,
            "email_from": "",
            "email_to": "",
            "smtp_server": "smtp.gmail.com",
            "smtp_port": 587,
            "login_key": "",
        },
        "last_updated": "2025-10-18T10:00:00.000",
    }


@pytest.fixture
def seed_policy(tmp_path):
    """Seed a local policy for unit_app using the new per-app file.

    Writes both the new standard file and a legacy root file to maximize compatibility:
    - New:   {WF_RPA_HOME}/.wf_rpa/unit_app/credit_policy.json
    - Legacy:{WF_RPA_HOME}/.wf_rpa/wf_app_policies.json and .wf_app_policies.json
    """
    # Force release-mode path usage so WorksFreeManager respects WF_RPA_HOME
    os.environ["WF_RPA_DEV"] = "0"
    wf_home = Path(os.environ["WF_RPA_HOME"])  # release mode uses this exact path
    wf_home.mkdir(parents=True, exist_ok=True)

    # New standard per-app policy (merged policy.json format)
    app_dir = wf_home / "unit_app"
    app_dir.mkdir(parents=True, exist_ok=True)
    new_policy = {
        "identity": {"app_name": "unit_app"},
        "last_updated": "2025-10-18T10:00:00.000",
        "source": "test_fixture",
        "policy": {"trial_credits": 100, "credit_per_work": 7, "requires_registration": False},
    }
    with open(app_dir / "policy.json", "w", encoding="utf-8") as f:
        json.dump(new_policy, f, ensure_ascii=False, indent=2)

    # Legacy aggregate policies (root) for back-compat
    legacy_policies_wrapper = {
        "source": "test_fixture",
        "policies": {
            "unit_app": {
                "default_credit": 100,
                "credit_per_work": 7,
                "requires_registration": False,
            }
        },
    }
    # Non-hidden (current manager uses this name)
    with open(wf_home / "wf_app_policies.json", "w", encoding="utf-8") as f:
        json.dump(legacy_policies_wrapper, f, ensure_ascii=False, indent=2)
    # Hidden legacy file (some legacy tests/readers look for this)
    with open(wf_home / ".wf_app_policies.json", "w", encoding="utf-8") as f:
        json.dump(legacy_policies_wrapper["policies"], f, ensure_ascii=False, indent=2)

    return legacy_policies_wrapper["policies"]


# ============================================================================
# 로거 Fixtures
# ============================================================================


@pytest.fixture(scope="function")
def test_logger():
    """테스트용 로거 (콘솔 출력)"""
    from wf_log import get_app_logger
    import logging

    logger = get_app_logger("pytest", console_level=logging.DEBUG)
    return logger


@pytest.fixture(scope="function", autouse=True)
def reset_logger():
    """각 테스트 후 로거 초기화"""
    yield

    # 로거 정리
    import logging

    logger = logging.getLogger("wf_credit_manager")
    logger.handlers.clear()
    logger.setLevel(logging.NOTSET)


# ============================================================================
# Pytest 설정 Hook
# ============================================================================


def pytest_configure(config):
    """Pytest 설정 초기화"""
    # 커스텀 마커 등록 (pytest.ini와 중복되지만 명시적으로)
    config.addinivalue_line("markers", "unit: 단위 테스트")
    config.addinivalue_line("markers", "integration: 통합 테스트")
    config.addinivalue_line("markers", "staging: 스테이징 테스트")

    # 원래 stdout/stderr 저장 (pytest가 캡처하기 전)
    config._original_stdout = sys.stdout
    config._original_stderr = sys.stderr


def pytest_unconfigure(config):
    """Pytest 종료 시 cleanup - UTF-8 TextIOWrapper 충돌 방지"""
    import sys
    import io

    # TextIOWrapper로 감싸진 경우 flush하고 원래 스트림 복원
    try:
        if hasattr(sys.stdout, 'buffer') and isinstance(sys.stdout, io.TextIOWrapper):
            if not sys.stdout.closed:
                sys.stdout.flush()
        if hasattr(sys.stderr, 'buffer') and isinstance(sys.stderr, io.TextIOWrapper):
            if not sys.stderr.closed:
                sys.stderr.flush()
    except (ValueError, OSError):
        pass  # "I/O operation on closed file" 무시

    # 원래 스트림 복원
    if hasattr(config, '_original_stdout'):
        sys.stdout = config._original_stdout
    if hasattr(config, '_original_stderr'):
        sys.stderr = config._original_stderr


def pytest_collection_modifyitems(config, items):
    """테스트 수집 후 자동 마커 추가"""
    for item in items:
        # 파일명으로 자동 마커 추가
        if "integration" in item.nodeid:
            item.add_marker(pytest.mark.integration)
        elif "staging" in item.nodeid:
            item.add_marker(pytest.mark.staging)
        else:
            # 기본적으로 unit 마커 추가
            if not any(
                marker.name in ["unit", "integration", "staging"] for marker in item.iter_markers()
            ):
                item.add_marker(pytest.mark.unit)
