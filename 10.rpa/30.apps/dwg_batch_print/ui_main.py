import os
import sys
from pathlib import Path
import logging
from typing import Any, Callable, Optional, TYPE_CHECKING

# Windows 콘솔 UTF-8 강제 설정 (GUI 모드에서는 stdout/stderr가 None일 수 있음)
if sys.platform == "win32":
    import io
    if sys.stdout is not None and hasattr(sys.stdout, 'buffer'):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    if sys.stderr is not None and hasattr(sys.stderr, 'buffer'):
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# ==================== STARTUP PROFILER ====================
_STARTUP_LOG = []
_STARTUP_ENABLED = True  # 프로파일링 활성화 - 로딩 시간 측정
_STARTUP_FLUSHED = False


def _detect_run_mode():
    """
    실행 모드 감지 (환경변수 + sys.argv 기반 통일 방식)
    - 1순위: WF_RPA_MODE 환경변수 (demo 모드 명시적 지정용)
    - 2순위: .py 파일 직접 실행 → dev
    - 3순위: 기본값 release (exe 실행)
    """
    env_mode = (os.environ.get("WF_RPA_MODE") or "").strip().lower()
    if env_mode in ("dev", "demo", "release"):
        return env_mode
    if sys.argv[0].endswith(".py"):
        return "dev"
    return "release"


def _get_startup_log_path():
    mode = _detect_run_mode()
    if mode in ("dev", "demo"):
        path = Path.cwd() / "startup_profile.log"
    else:
        path = Path.home() / ".wf_rpa" / "dwg_batch_print" / "startup_profile.log"
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    return path


def _log_startup(msg):
    """Startup 타이밍 로그 수집 (버퍼 방식)"""
    if not _STARTUP_ENABLED:
        return
    import time
    _STARTUP_LOG.append((time.perf_counter(), msg))


def _flush_startup_log():
    """수집한 startup 로그를 파일로 출력 (콘솔 출력 제거 - GUI 앱)"""
    global _STARTUP_FLUSHED
    if _STARTUP_FLUSHED:
        return
    if not _STARTUP_ENABLED or not _STARTUP_LOG:
        return
    base_time = _STARTUP_LOG[0][0]
    total_ms = (_STARTUP_LOG[-1][0] - base_time) * 1000

    try:
        log_path = _get_startup_log_path()
        with open(log_path, "w", encoding="utf-8") as f:
            f.write(f"Total: {total_ms:.1f}ms\n")
            for t, msg in _STARTUP_LOG:
                elapsed_ms = (t - base_time) * 1000
                f.write(f"[{elapsed_ms:7.1f}ms] {msg}\n")
    except Exception:
        pass

    _STARTUP_FLUSHED = True


_log_startup("Script start")


# ==================== 버전 정보 로드 ====================
def _load_version_info():
    """settings.json에서 버전 정보 읽기 (개발/릴리스 모두 지원)
    
    ⚠️ 버전 정보 단일 소스: settings.json의 runtime_config.full_version만 사용
    - MECE 원칙: runtime_config에만 버전 정보 저장
    """
    import json

    default_full = "v0.7.0.0"
    full_version = default_full

    try:
        if getattr(sys, "frozen", False):
            # 릴리스 모드: 번들 버전 우선 (정확한 빌드 버전), fallback으로 사용자 홈
            base_path = Path(sys._MEIPASS) if hasattr(sys, '_MEIPASS') else Path(sys.executable).parent  # type: ignore[attr-defined]
            settings_file = base_path / ".wf_rpa" / "dwg_batch_print" / "settings.json"

            # fallback: 사용자 홈 (버전 정보가 없을 수 있음)
            if not settings_file.exists():
                settings_file = Path.home() / ".wf_rpa" / "dwg_batch_print" / "settings.json"
        else:
            # 개발 모드: 10.common/config/dwg_batch_print/settings.json (통합 경로)
            app_root = Path(__file__).parent
            settings_file = app_root.parent.parent / "10.common" / "config" / "dwg_batch_print" / "settings.json"
            # fallback: 앱 폴더의 config
            if not settings_file.exists():
                settings_file = app_root / "config" / "dwg_batch_print" / "settings.json"

        if settings_file.exists():
            with open(settings_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                # app_config.full_version 우선 (새 표준), 없으면 runtime_config.full_version
                app_config = data.get("app_config", {})
                runtime_config = data.get("runtime_config", {})
                full_version = app_config.get("full_version") or runtime_config.get("full_version", default_full)
                # v 접두사 보장
                if not full_version.startswith("v"):
                    full_version = "v" + full_version
    except Exception:
        pass

    # display_version은 앞 2자리만 (v0.7.0.3 → v0.7)
    parts = full_version.lstrip("v").split(".")
    display_version = "v" + ".".join(parts[:2])

    return full_version, display_version


APP_VERSION_FULL, APP_VERSION_DISPLAY = _load_version_info()  # 관리자용, 사용자용

# Windows frozen executables (PyInstaller) can recursively spawn child processes
# when any dependency uses multiprocessing. Call freeze_support early to prevent
# the child from re-running the main module on spawn.
try:
    import multiprocessing  # noqa: F401

    multiprocessing.freeze_support()
    _log_startup("multiprocessing.freeze_support()")
except Exception:
    pass

# --- Single instance guard (Windows named mutex) ---
_instance_mutex_handle = None


def _acquire_single_instance(mutex_name: str = r"Global\\WF_DWG_BATCH_PRINT"):
    """Try to acquire a global mutex so only one instance runs.
    Returns (is_first_instance: bool, handle: int|None).
    Works on Windows; no-op on other OSes.
    """
    if os.name != "nt":
        return True, None
    try:
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.windll.kernel32
        # BOOL bInitialOwner=False so we don't need to ReleaseMutex later
        handle = kernel32.CreateMutexW(
            ctypes.c_void_p(None), ctypes.c_bool(False), ctypes.c_wchar_p(mutex_name)
        )
        if not handle:
            return True, None  # fail-open to avoid blocking start
        ERROR_ALREADY_EXISTS = 183
        existed = kernel32.GetLastError() == ERROR_ALREADY_EXISTS
        if existed:
            # Another instance already created the mutex
            kernel32.CloseHandle(handle)
            return False, None
        return True, handle
    except Exception:
        # If anything goes wrong, don't block startup (fail-open)
        return True, None


# --- Cross-app execution status helpers ---
def _set_cross_app_running(app_name: str):
    try:
        import json as _json
        from pathlib import Path as _Path
        import datetime as _dt

        home = _Path.home()
        cfg_dir = home / ".wf_rpa"
        cfg_dir.mkdir(parents=True, exist_ok=True)
        cfg = cfg_dir / "wf_rpa_config.json"
        data = {}
        if cfg.exists():
            try:
                with open(cfg, "r", encoding="utf-8") as _f:
                    data = _json.load(_f) or {}
            except Exception:
                data = {}
        
        # email_settings / google_sheets가 없으면 번들 템플릿에서 보강
        try:
            need_email = "email_settings" not in data
            need_sheets = "google_sheets" not in data
            if need_email or need_sheets:
                if getattr(sys, "frozen", False):
                    candidates = [
                        _Path(sys.executable).parent / ".wf_rpa" / "wf_rpa_config.json",
                        _Path(sys.executable).parent / "_internal" / ".wf_rpa" / "wf_rpa_config.json",
                    ]
                else:
                    candidates = [
                        _Path(__file__).parent / "config" / "wf_rpa_config.json",
                    ]
                bundle_cfg = next((c for c in candidates if c.exists()), None)
                if bundle_cfg:
                    with open(bundle_cfg, "r", encoding="utf-8") as _f:
                        template = _json.load(_f) or {}
                        if need_email and "email_settings" in template:
                            data["email_settings"] = template["email_settings"]
                        if need_sheets and "google_sheets" in template:
                            data["google_sheets"] = template["google_sheets"]
        except Exception:
            pass
        
        es = data.get("execution_status", {})
        es["is_running"] = True
        es["current_app"] = app_name
        es["pid"] = os.getpid()
        es["start_time"] = _dt.datetime.now().isoformat()
        data["execution_status"] = es
        with open(cfg, "w", encoding="utf-8") as _f:
            _json.dump(data, _f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False


def _clear_cross_app_running():
    try:
        import json as _json
        from pathlib import Path as _Path

        cfg = _Path.home() / ".wf_rpa" / "wf_rpa_config.json"
        if not cfg.exists():
            return True
        with open(cfg, "r", encoding="utf-8") as _f:
            data = _json.load(_f) or {}
        if "execution_status" in data:
            data["execution_status"]["is_running"] = False
            data["execution_status"]["current_app"] = None
            data["execution_status"]["pid"] = None
            data["execution_status"]["start_time"] = None
            with open(cfg, "w", encoding="utf-8") as _f:
                _json.dump(data, _f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False


# Ensure 10.common is in sys.path for shared modules
common_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "10.common"))
if common_path not in sys.path:
    sys.path.insert(0, common_path)
_log_startup("sys.path setup complete")

# -*- coding: utf-8 -*-
"""
DWG Batch Print Main UI Module
메인 GUI 인터페이스를 담당하는 모듈
bom_exporter의 be 스키마를 완벽히 동일하게 따름
"""

import tkinter as tk

_log_startup("import tkinter")
import tkinter.ttk as ttk
from tkinter import messagebox

_log_startup("import tkinter.ttk, messagebox")
import datetime

_log_startup("import datetime")
# pyautogui는 필요시에만 lazy import (300ms 절약)
# import pyautogui
_log_startup("pyautogui deferred (lazy import)")
from tkinter import filedialog

_log_startup("import filedialog")
import threading

_log_startup("import logging, threading")

# 현재 스크립트의 디렉토리를 Python 경로에 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# 로컬 모듈 import
from app_setting_data import get_config

_log_startup("import app_setting_data")
# DwgBatchPrintAutomation은 lazy import로 변경 (필요 시점에 로드하여 startup 시간 단축)
# from automation import DwgBatchPrintAutomation
_log_startup("automation.DwgBatchPrintAutomation deferred (lazy import)")
from ui_setting import create_settings_window, load_custom_settings, apply_custom_settings_to_config
from wf_ui_adaptive import get_adaptive_ui_settings, apply_global_fonts

_log_startup("import ui_setting")

# 글로벌 로거 import (없을 때는 콘솔 전용 임시 로거)
try:
    from wf_log import get_app_logger  # type: ignore
    _log_startup("import wf_log")
except Exception as e:
    _log_startup(f"wf_log import failed: {e}")

    def get_app_logger(name: str, console_level: int = logging.INFO):  # type: ignore
        logger = logging.getLogger(name)
        if not logger.handlers:
            handler = logging.StreamHandler()
            handler.setLevel(console_level)
            logger.addHandler(handler)
        logger.setLevel(console_level)
        return logger

# 등록 창 함수는 환경에 따라 경로 분석이 달라질 수 있어 안전하게 처리
try:
    from wf_register import create_trial_window  # type: ignore
except Exception as e:
    print(f"등록 모듈(wf_register) import 실패: {e}")
    create_trial_window = None

# 크레딧 및 등록 관리 모듈 import
try:
    from wf_credit_manager import WorksFreeManager, CreditManager  # type: ignore
    from wf_app_init_helpers import (  # type: ignore
        init_credit_and_policy_managers,
        check_cross_app_running_and_exit,
        seed_res_if_missing,
    )

    WFM_AVAILABLE = True
except Exception as e:
    print(f"WorksFree 관리자 모듈 import 실패: {e}")
    WorksFreeManager = None
    CreditManager = None
    check_cross_app_running_and_exit = None
    WFM_AVAILABLE = False

if TYPE_CHECKING:
    from automation import DwgBatchPrintAutomation
    from wf_settings_common import sync_policies_from_sheets  # type: ignore
    import wf_hwinfo  # type: ignore


class DwgBatchPrintGUIApplication:
    """DWG Batch Print GUI 애플리케이션 클래스 (bom_exporter의 be 스키마 완벽 동일)"""

    def __init__(self, master):
        _log_startup("__init__ started")
        self.master = master
        self.itself_dir = os.path.dirname(os.path.abspath(__file__))

        # 아이콘 경로 저장 (등록창/설정창에서 사용)
        self.icon_path = self._find_icon_path()

        _log_startup("Master and directory initialized")

        # 적응형 UI 설정 초기화
        self.ui = get_adaptive_ui_settings()
        _log_startup("Adaptive UI settings loaded")

        # 로거 초기화
        self.logger = get_app_logger("dwg_batch_print", console_level=logging.INFO)
        self.app = None  # 호환성 유지
        self.paths = None  # 호환성 유지
        self.i18n = None  # 호환성 유지
        _log_startup("Logger initialized")

        # 등록 매니저 Early 초기화 (DWG 패턴 통일)
        self.wf_manager: Any = None
        self._wfm_available = WFM_AVAILABLE
        if not WFM_AVAILABLE:
            self.logger.error("프로그램 핵심 모듈을 찾을 수 없습니다. 프로그램을 종료합니다.")
            messagebox.showerror(
                "치명적 오류", "프로그램 핵심 모듈을 찾을 수 없습니다.\n프로그램을 종료합니다."
            )
            sys.exit(1)

        _log_startup("WFM availability checked")

        # 설정 로더는 reload 플래그만 받으므로 인자 없이 호출
        self.config = get_config()
        _log_startup("Config loaded")

        custom_settings = load_custom_settings()
        if custom_settings:
            apply_custom_settings_to_config(self.config, custom_settings)
        _log_startup("Custom settings applied")

        self.automation: Any = None  # DwgBatchPrintAutomation (lazy import)
        self.SELECTED_PATH = None  # 통합 표준 변수명
        self.DWG_PATH = None  # 하위 호환성 유지 (임시)

        self.run_mode = getattr(self.config, "run_mode", "release")
        self.demo_capture_enabled = (
            self.run_mode == "demo" or bool(os.environ.get("WF_ENABLE_DEMO_CAPTURE"))
        )
        self.demo_capture_dir = None
        self.demo_capture_size = (1920, 1040)
        self._last_demo_capture_ts = 0.0
        
        # Alt+G 데모 핫키에서 적용할 수 있는 창 위치/크기 오버라이드 (설정 파일만 사용)
        self.debug_geometry_override = getattr(self.config, "window_geometry_override", "")

        # 진행 상태 변수 초기화
        self.initial_file_count = 0
        self.cumulative_processed_count = 0
        self.is_first_run = True
        self.last_run_success_count = 0

        # 폴더 스캔 토글 상태 (False: 미스캔, True: 스캔 완료)
        self.scan_toggle_var = tk.BooleanVar(value=False)
        self.is_folder_scanned = False

        _log_startup("Basic variables initialized")
        # 스피너 관련 변수
        self.spinner_running = False
        self.spinner_index = 0
        self.spinner_chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]  # 브라유 패턴 스피너

        # 관리자 모드 변수
        self.is_admin_mode = False
        self.admin_mode_timer = None  # 30분 자동 복귀 타이머
        self.admin_mode_start_time = None
        # 🚀 최적화: admin 비밀번호 lazy 로딩 (Google Sheets 호출 지연)
        self._admin_password = None  # lazy load
        # 글로벌 핫키 스레드 ID (초기값 None으로 명시)
        self._hotkey_thread_id: Optional[int] = None

        # 로그 창 관련 변수
        self.log_frame = None
        self.log_text = None
        self.log_scrollbar = None
        self.auto_scroll_var = None
        self.auto_scroll_checkbox = None
        # 창 크기: adaptive UI 기반 (dwg_classifier 스킴)
        self.original_window_height = 160  # 1입력 앱 기본 높이
        self.expanded_window_height = self.original_window_height + 300  # 관리자 모드: +300 고정

        _log_startup("UI-related variables initialized")
        # Ensure all messageboxes/dialogs center relative to the main window
        self._bind_messagebox_parent()
        if self.demo_capture_enabled:
            self._init_demo_capture()
        # 등록 상태 체크는 UI 표출 이후 백그라운드에서 수행해 초기 로딩을 가볍게 유지
        self.is_registered_user = False
        try:
            if self._wfm_available and WorksFreeManager:
                self.logger.debug("Deferred WorksFreeManager init to background thread")
        except Exception as e:
            self.logger.warning(f"WorksFreeManager deferred init setup 실패(무시): {e}")

        # 🚀 최적화: CreditManager 초기화를 백그라운드로 지연
        self.credit_manager: Any = None

        # UI 먼저 생성
        _log_startup("About to set WM_DELETE_WINDOW protocol")
        self.master.protocol("WM_DELETE_WINDOW", self.on_closing)
        _log_startup("About to call init_ui()")
        self.init_ui()
        # 초기 등록 상태가 이미 True라면 버튼 라벨 즉시 조정
        try:
            if self.is_registered_user:
                self.update_registration_button()
        except Exception:
            pass
        _log_startup("DwgBatchPrintGUIApplication initialized - UI ready")
        _flush_startup_log()

        # 🚀 백그라운드에서 추가 초기화 수행 (크레딧/정책 등)
        self.master.after(100, self._lazy_init_managers)
        
        # 🚀 이전 작업 폴더 자동 스캔 (CV 패턴 적용)
        if self.SELECTED_PATH:
            self.master.after(300, self._restore_last_session)

    @property
    def admin_password(self) -> str:
        """🚀 Lazy 로딩: admin 비밀번호 (첫 접근 시 Google Sheets에서 로드)"""
        if self._admin_password is None:
            try:
                from wf_settings_common import get_admin_password
                self._admin_password = get_admin_password(self.logger)
            except Exception:
                self._admin_password = "admin2024"  # fallback
        return self._admin_password

    def _bind_messagebox_parent(self):
        """Route all tkinter messageboxes to use the main window as parent for centering."""
        def _wrap(func):
            def inner(*args, **kwargs):
                kwargs.setdefault("parent", self.master)
                return func(*args, **kwargs)
            return inner

        for name in (
            "showinfo",
            "showwarning",
            "showerror",
            "askyesno",
            "askquestion",
            "askokcancel",
            "askyesnocancel",
        ):
            if hasattr(messagebox, name):
                setattr(messagebox, name, _wrap(getattr(messagebox, name)))

    def _find_icon_path(self):
        """앱 아이콘 경로 찾기 (개발/릴리스 환경 모두 지원)"""
        try:
            icon_names = ["02_DWG_Batch_Print.ico", "dp.ico"]
            if getattr(sys, 'frozen', False):
                base_paths = [
                    Path(sys.executable).parent / "res",
                    Path(sys.executable).parent / "_internal" / "res",
                ]
            else:
                base_paths = [Path(__file__).parent / "res"]
            icon_candidates = [bp / name for bp in base_paths for name in icon_names]
            return next((p for p in icon_candidates if p.exists()), None)
        except Exception:
            return None

    def set_selected_path(self, path: str | None):
        """선택된 경로를 설정하고 UI를 동기화 (통합 헬퍼)"""
        self.SELECTED_PATH = path
        self.DWG_PATH = path  # 하위 호환 유지

        # folder_entry 업데이트 (B2E 방식)
        try:
            self.folder_entry.config(state="normal")
            self.folder_entry.delete(0, tk.END)
            if path:
                self.folder_entry.insert(0, path)
            self.folder_entry.config(state="readonly")
        except Exception:
            pass

        # 경로 초기화 시 버튼/진행 상태 리셋
        if not path:
            try:
                if hasattr(self, "print_button"):
                    self.print_button.config(state="disabled")
                if hasattr(self, "progress_label"):
                    self.progress_label.config(text="?/?")
            except Exception:
                pass
        else:
            # 마지막 선택 폴더 저장
            try:
                self.logger.debug(f"마지막 선택 폴더 저장 시도: {path}")
                self.config.update_ui_last_folder(path)
                self.logger.info(f"마지막 선택 폴더 저장 완료: {path}")
            except Exception as e:
                self.logger.error(f"마지막 선택 폴더 저장 실패: {e}")
                import traceback
                self.logger.error(traceback.format_exc())

    def _lazy_init_managers(self):
        """🚀 백그라운드에서 WorksFreeManager와 CreditManager 초기화"""

        def _worker():
            try:
                # 🚀 Config 정책 로딩 (백그라운드)
                if self.config and hasattr(self.config, "load_policies_async"):
                    self.config.load_policies_async()

                # WorksFree 매니저 초기화
                if self._wfm_available and WorksFreeManager and not self.wf_manager:
                    self.wf_manager = WorksFreeManager()
                    if self.wf_manager:
                        self.is_registered_user = self.wf_manager.is_registered()
                    try:
                        self.master.after(0, self.update_registration_button)
                    except Exception:
                        pass

                # CreditManager 초기화 (공통 헬퍼 사용)
                if CreditManager and self.wf_manager:
                    self.credit_manager = init_credit_and_policy_managers(
                        app_name="dwg_batch_print",
                        wf_manager=self.wf_manager,
                        master=self.master,
                        logger=self.logger,
                        recovery_delay_ms=700,
                        policy_delay_ms=400,
                    )
                    # UI 업데이트
                    self.master.after(0, self.update_credit_display)
                    # 정책 동기화는 별도 스케줄 (헬퍼에서 처리 불가)
                    self.master.after(300, self._async_refresh_policies)

            except Exception as e:
                if self.logger:
                    self.logger.warning(f"매니저 초기화 중 오류 (non-critical): {e}")

        # 백그라운드 스레드에서 실행
        threading.Thread(target=_worker, daemon=True).start()

    def _init_demo_capture(self):
        """데모 모드 자동 캡처 초기화"""
        try:
            self.demo_capture_dir = self._resolve_demo_capture_dir()
            if self.demo_capture_dir:
                self.logger.info(f"[DEMO] Capture dir: {self.demo_capture_dir}")
            else:
                self.demo_capture_enabled = False
                self.logger.warning("[DEMO] 캡처 디렉터리를 준비하지 못해 자동 캡처를 비활성화합니다.")
        except Exception as e:
            self.demo_capture_enabled = False
            self.logger.warning(f"[DEMO] 캡처 초기화 실패: {e}")

    def _resolve_demo_capture_dir(self):
        candidates = [
            Path(__file__).resolve().parent / "demo_captures",
            Path.home() / ".wf_rpa" / "dwg_batch_print" / "demo_captures",
        ]
        for cand in candidates:
            try:
                cand.mkdir(parents=True, exist_ok=True)
                if os.access(cand, os.W_OK):
                    return cand
            except Exception as e:
                self.logger.debug(f"[DEMO] 캡처 경로 생성 실패: {cand} ({e})")
        return None

    def _capture_demo(self, reason: str, delay_ms: int = 0, throttle_sec: float = 0.8):
        if not self.demo_capture_enabled or not self.demo_capture_dir:
            return

        def _fire():
            self._capture_demo_now(reason, throttle_sec=throttle_sec)

        try:
            delay = max(0, int(delay_ms))
        except Exception:
            delay = 0

        try:
            self.master.after(delay, _fire)
        except Exception:
            _fire()

    def _capture_demo_now(self, reason: str, throttle_sec: float = 0.8):
        if not self.demo_capture_enabled or not self.demo_capture_dir:
            return
        try:
            import time
            from PIL import ImageGrab
        except Exception as e:
            self.logger.warning(f"[DEMO] 캡처 불가 (필수 모듈 없음): {e}")
            self.demo_capture_enabled = False
            return

        now = time.perf_counter()
        if self._last_demo_capture_ts and (now - self._last_demo_capture_ts) < throttle_sec:
            return
        self._last_demo_capture_ts = now

        safe_reason = "".join(
            c if c.isalnum() or c in ("-", "_") else "_" for c in (reason or "event")
        )
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
        fname = f"demo_{ts}_{safe_reason}.png"
        path = self.demo_capture_dir / fname

        try:
            img = ImageGrab.grab()
            w, h = self.demo_capture_size
            cropped = img.crop((0, 0, w, h))
            cropped.save(path, "PNG")
            self.logger.debug(f"[DEMO] capture saved ({safe_reason}): {path}")
        except Exception as e:
            self.logger.warning(f"[DEMO] capture failed ({safe_reason}): {e}")

    def _on_manual_capture(self, _event=None):
        """Alt+C: 수동 화면 캡처 - dwg_classifier에서 마이그레이션"""
        if not self.demo_capture_enabled or not self.demo_capture_dir:
            self._show_toast("캡처 기능이 비활성화되어 있습니다", duration_ms=1200)
            return
        
        try:
            # 쓰로틀링 무시하고 즉시 캡처
            self._last_demo_capture_ts = 0.0
            self._capture_demo_now("manual_capture", throttle_sec=0.0)
            self._show_toast("화면 캡처 완료", duration_ms=1200)
        except Exception as e:
            self._show_toast(f"캡처 실패: {e}", duration_ms=1500)
            if self.logger:
                self.logger.error(f"수동 캡처 실패: {e}")

    def _bind_debug_geometry_hotkey(self):
        """Alt+G: geometry 저장 (모든 모드), Alt+C: 화면 캡처 (demo 전용)"""
        try:
            # Alt+G는 항상 바인딩 (geometry 저장용)
            self.master.bind_all("<Alt-g>", self._on_debug_geometry_capture)

            # Alt+C는 demo 모드에서만 바인딩 (화면 캡처용)
            if self.config and hasattr(self.config, "is_demo") and self.config.is_demo():
                self.master.bind_all("<Alt-c>", self._on_manual_capture)
                # 모달 대화상자 활성화 시에도 Alt+C가 동작하도록 전역 핫키 리스너 시작
                self._start_global_hotkey_listener()
        except Exception as e:
            try:
                self.logger.debug(f"Alt hotkey bind 실패: {e}")
            except Exception:
                pass

    def _on_debug_geometry_capture(self, _event=None):
        """Alt+G: 현재 geometry를 로그에 찍고 즉시 settings.json에 저장 - dwg_classifier에서 마이그레이션"""
        try:
            geo = self.master.geometry()
            msg = f"[DEBUG] window geometry: {geo}"
            print(msg)
            if self.logger:
                self.logger.info(msg)

            ok = False
            if self.config and hasattr(self.config, "update_window_geometry_override"):
                ok = self.config.update_window_geometry_override(geo)

            if ok:
                self.debug_geometry_override = geo
                toast_msg = f"geometry 저장됨: {geo}"
                self._show_toast(toast_msg, duration_ms=1400)
                if self.logger:
                    self.logger.info(f"[DEBUG] geometry saved to settings: {geo}")
            else:
                self._show_toast("geometry 저장 실패", duration_ms=1400)
        except Exception as e:
            try:
                if self.logger:
                    self.logger.debug(f"Alt+G 저장 실패: {e}")
            except Exception:
                pass

    def _start_global_hotkey_listener(self):
        """모달 창 활성화 중에도 Alt+C 수동 캡처가 가능하도록 전역 핫키 등록 - dwg_classifier에서 마이그레이션"""
        try:
            # 데모 모드에서만 활성화
            if not (self.config and hasattr(self.config, "is_demo") and self.config.is_demo()):
                return
        except Exception:
            return

        try:
            import threading
            import ctypes
            from ctypes import wintypes

            if getattr(self, "_hotkey_thread", None):
                return  # 이미 실행 중

            self._hotkey_thread_stop = False

            def _thread_main():
                user32 = ctypes.windll.user32
                kernel32 = ctypes.windll.kernel32

                WM_HOTKEY = 0x0312
                MOD_ALT = 0x0001
                VK_C = 0x43  # 'C'
                HOTKEY_ID = 1

                class MSG(ctypes.Structure):
                    _fields_ = [
                        ("hwnd", wintypes.HWND),
                        ("message", wintypes.UINT),
                        ("wParam", wintypes.WPARAM),
                        ("lParam", wintypes.LPARAM),
                        ("time", wintypes.DWORD),
                        ("pt", wintypes.POINT),
                    ]

                # 스레드 ID 저장 (종료 시 WM_QUIT 전송용)
                try:
                    self._hotkey_thread_id = kernel32.GetCurrentThreadId()
                except Exception:
                    self._hotkey_thread_id = None

                # 전역 핫키 등록 (현재 스레드 메시지 큐에 전달)
                if not user32.RegisterHotKey(None, HOTKEY_ID, MOD_ALT, VK_C):
                    try:
                        if self.logger:
                            self.logger.warning("전역 Alt+C 등록 실패 (RegisterHotKey)")
                    except Exception:
                        pass
                    return

                try:
                    msg = MSG()
                    while True:
                        res = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
                        if res == 0:  # WM_QUIT
                            break
                        if res == -1:
                            # 오류
                            break
                        if msg.message == WM_HOTKEY and msg.wParam == HOTKEY_ID:
                            try:
                                # Tk 메인스레드에서 안전하게 실행
                                self.master.after(0, lambda: self._on_manual_capture())
                            except Exception:
                                pass
                        # 일반 메시지는 무시
                finally:
                    try:
                        user32.UnregisterHotKey(None, HOTKEY_ID)
                    except Exception:
                        pass

            t = threading.Thread(target=_thread_main, daemon=True, name="WF-GlobalHotkey")
            t.start()
            self._hotkey_thread = t
        except Exception as e:
            try:
                if self.logger:
                    self.logger.debug(f"전역 핫키 리스너 시작 실패: {e}")
            except Exception:
                pass

    def _stop_global_hotkey_listener(self):
        """전역 핫키 리스너 종료 (앱 종료 시 호출) - dwg_classifier에서 마이그레이션"""
        try:
            import ctypes
            from ctypes import wintypes
            if getattr(self, "_hotkey_thread", None):
                # WM_QUIT을 핫키 스레드에 전송하여 GetMessageW 루프 종료
                try:
                    thread_id = getattr(self, "_hotkey_thread_id", None)
                    if thread_id:
                        ctypes.windll.user32.PostThreadMessageW(thread_id, 0x0012, 0, 0)  # WM_QUIT
                except Exception:
                    pass
                self._hotkey_thread = None
        except Exception:
            pass

    # _schedule_recovery는 이제 wf_app_init_helpers에서 처리됨 (제거 가능하나 호환성 유지)
    def _schedule_recovery(self):
        """크레딧 복구 동기화 스케줄 (deprecated - 헬퍼로 이동)"""
        pass
    
    def _restore_last_session(self):
        """이전 작업 세션 복원: 폴더 자동 스캔 (CV 패턴)"""
        try:
            # 등록된 사용자이고 폴더가 유효한 경우 자동 스캔
            if self.is_registered_user and self.SELECTED_PATH and os.path.isdir(self.SELECTED_PATH):
                try:
                    if hasattr(self, "scan_toggle_btn"):
                        self.scan_toggle_btn.config(state="disabled")
                    self.scan_toggle_var.set(True)
                    self.on_scan_toggle()
                    self.logger.info("이전 작업 폴더 자동 스캔 완료")
                finally:
                    if hasattr(self, "scan_toggle_btn"):
                        self.scan_toggle_btn.config(state="normal")
        except Exception as e:
            self.logger.warning(f"이전 세션 복원 중 오류 (무시): {e}")

    def check_user_registration(self):
        """WorksFreeManager를 통해 사용자 등록 상태 확인"""
        if self.wf_manager:
            return self.wf_manager.is_registered()
        return False

    def check_and_set_execution_status(self):
        """앱 실행 상태 확인 및 설정"""
        try:
            import json
            import os
            from pathlib import Path

            try:
                import psutil
            except ImportError:
                psutil = None

            # WorksFreeManager가 가리키는 환경별 설정 파일 사용 (DEV=앱로컬, PROD=홈폴더)
            from pathlib import Path

            config_path = None
            try:
                if self.wf_manager:
                    config_path = Path(self.wf_manager.config_file)
            except Exception:
                config_path = None

            # 폴백: 홈 폴더
            if not config_path:
                home = Path.home()
                wf_rpa_dir = home / ".wf_rpa"
                wf_rpa_dir.mkdir(exist_ok=True)
                config_path = wf_rpa_dir / "wf_rpa_config.json"

            if not config_path.exists():
                return True

            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)

            exec_status = config.get("execution_status", {})
            if exec_status.get("is_running", False):
                pid = exec_status.get("pid")
                if pid and psutil:
                    try:
                        if psutil.pid_exists(pid):
                            process = psutil.Process(pid)
                            if process.is_running():
                                return False
                    except (psutil.NoSuchProcess, Exception):
                        pass

                exec_status["is_running"] = False
                exec_status["current_app"] = None
                exec_status["pid"] = None

            exec_status["is_running"] = True
            # 통일된 app_name 사용 - 폴더명과 일치
            exec_status["current_app"] = "dwg_batch_print"
            exec_status["pid"] = os.getpid()
            exec_status["start_time"] = datetime.datetime.now().isoformat()

            config["execution_status"] = exec_status

            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=2)

            return True

        except Exception as e:
            self.logger.error(f"실행 상태 확인 오류: {e}")
            return True

    def clear_execution_status(self):
        """앱 실행 상태 해제"""
        try:
            import json
            from pathlib import Path

            from pathlib import Path

            config_path = None
            try:
                if self.wf_manager:
                    config_path = Path(self.wf_manager.config_file)
            except Exception:
                config_path = None
            if not config_path:
                home = Path.home()
                config_path = home / ".wf_rpa" / "wf_rpa_config.json"

            if config_path.exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)

                if "execution_status" in config:
                    config["execution_status"]["is_running"] = False
                    config["execution_status"]["current_app"] = None
                    config["execution_status"]["pid"] = None
                    config["execution_status"]["start_time"] = None

                    with open(config_path, "w", encoding="utf-8") as f:
                        json.dump(config, f, ensure_ascii=False, indent=2)

        except Exception as e:
            self.logger.error(f"실행 상태 해제 오류: {e}")

    def update_credit_display(self):
        if not getattr(self, "credit_label", None):
            return
        if not self.wf_manager:
            return
        if not self.credit_manager:
            self.credit_label.config(text="크레딧 확인 불가", fg="gray")
            return
        try:
            status = self.credit_manager.get_credit_status()
            ct = status.get("credit_type", "standard")
            trial_raw = status.get("remaining_trial", 0)
            purchased_raw = status.get("remaining_purchased", 0)
            trial = max(0, trial_raw)
            purchased = max(0, purchased_raw)
            cost = self.credit_manager.policy.get("credit_per_work", 1)

            # -1은 무제한을 의미
            if trial_raw == -1 or purchased_raw == -1:
                txt, color, tip = "🎁 무료 앱", "green", "무제한 사용"
            elif ct == "free":
                txt, color, tip = "🎁 무료 앱", "green", "무제한 사용"
            elif ct == "permanent":
                txt, color, tip = "✨ 무제한", "blue", "영구 라이선스"
            else:
                if trial and purchased:
                    txt = f"체험판:{trial:,}/충전:{purchased:,}(건당 {cost})"
                    color = "blue"
                elif trial:
                    txt = f"체험판:{trial:,}(건당 {cost})"
                    color = "green" if trial > 500 else "orange"
                elif purchased:
                    txt = f"충전:{purchased:,}(건당 {cost})"
                    color = "blue"
                else:
                    txt = "⚠️ 크레딧 없음"
                    color = "red"
                tip = "차감 순서: 체험판 → 충전"

            self.credit_label.config(text=txt, fg=color)
            # bind tooltip
            try:
                self._bind_tooltip(self.credit_label, tip)
            except Exception:
                pass

        except Exception as e:
            self.credit_label.config(text="표시 오류", fg="red")
            self.logger.error(f"크레딧 표시 오류: {e}")

    def _bind_tooltip(self, widget, text: str):
        if not text:
            return
        # simple tooltip
        tip: dict[str, Any] = {"win": None}

        def on_enter(_e):
            if tip["win"] is not None:
                return
            x, y, cx, cy = widget.bbox("insert") if hasattr(widget, "bbox") else (0, 0, 0, 0)
            x += widget.winfo_rootx() + 20
            y += widget.winfo_rooty() + 20
            tw = tk.Toplevel(widget)
            tw.wm_overrideredirect(True)
            tw.wm_attributes("-topmost", 1)
            tw.wm_geometry(f"+{x}+{y}")
            lbl = tk.Label(
                tw,
                text=text,
                justify="left",
                background="#ffffe0",
                relief="solid",
                borderwidth=1,
                padx=6,
                pady=3,
            )
            lbl.pack()
            tip["win"] = tw

        def on_leave(_e):
            if tip["win"] is not None:
                try:
                    tip["win"].destroy()
                except Exception:
                    pass
                tip["win"] = None

        widget.unbind("<Enter>")
        widget.unbind("<Leave>")
        widget.bind("<Enter>", on_enter)
        widget.bind("<Leave>", on_leave)

    def _async_refresh_policies(self):
        """정책 동기화 (백그라운드, 토스트 메시지 없음)"""
        if not self.wf_manager or not self.credit_manager:
            return

        def worker():
            try:
                result = self.wf_manager.refresh_policies_from_sheets()
                self.logger.info(f"정책 동기화 결과: {result}")
                # Re-init credit_per_work if needed (keep existing balances)
                if result.get("success"):
                    # Only update credit_per_work from new policy
                    try:
                        cd = self.credit_manager._load_credit_data()
                        policies = self.wf_manager.load_policies()
                        app_policy = (policies or {}).get(self.credit_manager.app_name, {})
                        cpw = app_policy.get("credit_per_work")
                        if cpw is not None:
                            cd["credit_per_work"] = cpw
                            self.credit_manager._save_credit_data(cd)
                    except Exception:
                        pass
            finally:
                self.master.after(0, self.update_credit_display)

        threading.Thread(target=worker, daemon=True).start()

    def _show_toast(self, message: str, duration_ms: int = 1800):
        try:
            toast = tk.Toplevel(self.master)
            toast.overrideredirect(True)
            toast.attributes("-topmost", True)
            x = self.master.winfo_rootx() + 20
            y = self.master.winfo_rooty() + 20
            toast.geometry(f"+{x}+{y}")
            frm = tk.Frame(toast, bg="#333")
            frm.pack(fill="both", expand=True)
            lbl = tk.Label(frm, text=message, fg="#fff", bg="#333", padx=12, pady=6)
            lbl.pack()
            self.master.after(duration_ms, toast.destroy)
        except Exception:
            pass

    # ==================== WF-ACT Test Mode ====================
    def init_test_server(self):
        """WF-ACT 인증 테스트용 TestServer 초기화"""
        try:
            # 동기 초기화 (테스트 모드에서 필요)
            self._init_credit_manager_sync()

            # TestServer import (로컬 test_server.py 사용)
            from test_server import TestServer

            self.test_server = TestServer(app_name="dwg_batch_print")

            # 핸들러 등록 (bom_exporter 표준)
            self.test_server.register_handlers({
                # 크레딧 관련
                'get_credits': self._test_get_credits,
                'set_credits': self._test_set_credits,
                'add_credits': self._test_add_credits,
                'get_credit_status': self._test_get_credit_status,
                'get_trial_info': self._test_get_trial_info,

                # 등록 관련
                'get_registration_status': self._test_get_registration_status,
                'register': self._test_register,
                'clear_registration': self._test_clear_registration,
                'sync_registration': self._test_sync_registration,

                # 작업 시뮬레이션
                'simulate_work': self._test_simulate_work,

                # 상태 관련
                'get_state': self._test_get_state,
                'get_policy': self._test_get_policy,
                'get_settings': self._test_get_settings,
                'save_settings': self._test_save_settings,
                'load_settings': self._test_load_settings,
                'reload_config': self._test_reload_config,

                # UI 관련
                'get_button_state': self._test_get_button_state,
                'click_button': self._test_click_button,
            })

            self.test_server.start()
            self.logger.info("[WF-ACT] Test server started on port " + str(self.test_server.port))
        except Exception as e:
            self.logger.error(f"[WF-ACT] Failed to initialize test server: {e}")
            raise

    def _init_credit_manager_sync(self):
        """WF-ACT 테스트 모드용: CreditManager를 동기적으로 초기화"""
        try:
            if self._wfm_available and WorksFreeManager and not self.wf_manager:
                self.wf_manager = WorksFreeManager()
                self.is_registered_user = self.wf_manager.is_registered()
            if CreditManager and self.wf_manager and not self.credit_manager:
                self.credit_manager = init_credit_and_policy_managers(
                    app_name="dwg_batch_print",
                    wf_manager=self.wf_manager,
                    master=self.master,
                    logger=self.logger,
                    recovery_delay_ms=0,
                    policy_delay_ms=0,
                )
        except Exception as e:
            if self.logger:
                self.logger.error(f"[WF-ACT] CreditManager sync init failed: {e}")

    def _ensure_credit_manager(self):
        """CreditManager가 초기화될 때까지 대기 (최대 5초)"""
        import time
        for _ in range(50):
            if self.credit_manager:
                return
            time.sleep(0.1)

    def _test_get_credits(self) -> int:
        """현재 총 크레딧 반환 (테스트용 - 등록 상태 무관)"""
        self._ensure_credit_manager()
        if not self.credit_manager:
            return 0
        try:
            data = self.credit_manager._load_credit_data()
            remaining_trial = data.get("remaining_trial", 0)
            remaining_purchased = data.get("remaining_purchased", 0)
            if remaining_trial == -1 or remaining_purchased == -1:
                return -1
            return remaining_trial + remaining_purchased
        except Exception:
            status = self.credit_manager.get_credit_status()
            return status.get("remaining_credits", 0)

    def _test_set_credits(self, amount: int, credit_type: str = "trial") -> bool:
        """크레딧 직접 설정 (테스트용)"""
        self._ensure_credit_manager()
        if not self.credit_manager:
            return False
        try:
            if amount is None or amount < 0:
                return False

            data = self.credit_manager._load_credit_data()
            if credit_type == "purchased":
                data["remaining_purchased"] = amount
                data["remaining_trial"] = 0
            else:
                data["remaining_trial"] = amount
                data["remaining_purchased"] = 0

            # WF-ACT: 크레딧을 0으로 설정할 때, usage_history가 비어있으면
            # CreditManager._load_credit_data()가 policy에서 다시 초기화함.
            # 이를 방지하기 위해 테스트 마커를 usage_history에 추가
            if amount == 0:
                if "usage_history" not in data or not data["usage_history"]:
                    data["usage_history"] = []
                data["usage_history"].append({
                    "timestamp": "2000-01-01T00:00:00",
                    "credits_used": 0,
                    "operation": "wf_act_test_marker",
                    "details": "Credits set to 0 for testing"
                })

            self.credit_manager._save_credit_data(data)
            self.master.after(0, self.update_credit_display)
            return True
        except Exception as e:
            self.logger.error(f"[WF-ACT] set_credits failed: {e}")
            return False

    def _test_add_credits(self, amount: int) -> bool:
        """크레딧 추가 (구매 시뮬레이션)"""
        self._ensure_credit_manager()
        if not self.credit_manager:
            return False
        try:
            data = self.credit_manager._load_credit_data()
            current = data.get("remaining_purchased", 0)
            if current != -1:  # 영구 라이선스가 아닌 경우만
                data["remaining_purchased"] = current + amount
            self.credit_manager._save_credit_data(data)
            self.master.after(0, self.update_credit_display)
            return True
        except Exception as e:
            self.logger.error(f"[WF-ACT] add_credits failed: {e}")
            return False

    def _test_get_credit_status(self) -> dict:
        """크레딧 상태 상세 조회"""
        if not self.credit_manager:
            return {"success": False, "error": "credit_manager_not_initialized"}
        return self.credit_manager.get_credit_status()

    def _test_get_registration_status(self) -> dict:
        """등록 상태 반환"""
        if not self.wf_manager:
            return {"is_registered": False, "email": None, "registered_at": None, "app_version": APP_VERSION_FULL}
        user_info = self.wf_manager.get_user_info()
        return {
            "is_registered": self.wf_manager.is_registered(),
            "email": user_info.get("user_email") or user_info.get("email"),
            "registered_at": user_info.get("reg_time_local"),
            "app_version": APP_VERSION_FULL,
        }

    def _test_register(self, email: str) -> dict:
        """사용자 등록 (테스트용)"""
        if not self.wf_manager:
            return {"success": False, "error": "wf_manager_not_initialized"}
        try:
            try:
                from wf_hwinfo import HardwareInfo
                hw = HardwareInfo()
                hw_fp = hw.fingerprint
            except Exception:
                hw_fp = "test_hw_fingerprint_" + email.split("@")[0]

            success = self.wf_manager.register_user(
                user_email=email,
                hw_fingerprint=hw_fp,
                user_name="Test User",
                user_phone="",
                user_email_consent="Y"
            )
            if success:
                self.is_registered_user = True
                self.master.after(0, self.update_registration_button)
                # 체험판 크레딧 부여
                self._ensure_credit_manager()
                if self.credit_manager:
                    trial_credits = self.credit_manager.policy.get("trial_credits", 4000)
                    if trial_credits > 0:
                        data = self.credit_manager._load_credit_data()
                        current = data.get("remaining_trial", 0) + data.get("remaining_purchased", 0)
                        if current < trial_credits:
                            data["remaining_trial"] = trial_credits
                            self.credit_manager._save_credit_data(data)
            return {"success": success}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _test_clear_registration(self) -> bool:
        """등록 정보 삭제 (테스트용)"""
        if not self.wf_manager:
            return False
        try:
            # WorksFreeManager.save_config()를 통해 user_info 초기화
            config = self.wf_manager.load_config()
            config["user_info"] = {
                "is_registered": False,
                "user_email": None,
                "reg_time_local": None,
                "reg_time_utc": None,
            }
            self.wf_manager.save_config(config)
            self.is_registered_user = False
            self.master.after(0, self.update_registration_button)
            return True
        except Exception as e:
            self.logger.error(f"[WF-ACT] clear_registration failed: {e}")
            return False

    def _test_simulate_work(self, file_count: int = 1) -> dict:
        """작업 시뮬레이션 (테스트용) - 크레딧 차감 포함, 등록 상태 무관"""
        self._ensure_credit_manager()
        if not self.credit_manager:
            return {"success": False, "error": "credit_manager_not_initialized"}

        cost = self.credit_manager.policy.get("credit_per_work", 40)

        # 테스트 모드: 등록 상태와 무관하게 직접 크레딧 데이터 사용
        try:
            data = self.credit_manager._load_credit_data()
            remaining_trial = data.get("remaining_trial", 0)
            remaining_purchased = data.get("remaining_purchased", 0)

            # 영구 라이선스나 무료판인 경우
            if remaining_trial == -1 or remaining_purchased == -1:
                return {
                    "success": True,
                    "processed_count": file_count,
                    "blocked": False,
                    "credit_type": "free" if remaining_trial == -1 else "permanent",
                }

            current = remaining_trial + remaining_purchased
        except Exception as e:
            return {"success": False, "error": f"credit_load_error: {e}"}

        processed = 0
        for i in range(file_count):
            if current < cost:
                return {
                    "success": False,
                    "blocked": True,
                    "processed_count": processed,
                    "interrupted": processed > 0,
                    "exhausted": True,
                    "remaining_credits": current,
                }
            # 테스트 모드: 직접 크레딧 차감 (등록 체크 우회)
            try:
                data = self.credit_manager._load_credit_data()
                trial = data.get("remaining_trial", 0)
                purchased = data.get("remaining_purchased", 0)

                # 구매 크레딧 먼저 차감, 없으면 체험판 차감
                if purchased >= cost:
                    data["remaining_purchased"] = purchased - cost
                elif trial >= cost:
                    data["remaining_trial"] = trial - cost
                elif purchased + trial >= cost:
                    # 혼합 차감
                    data["remaining_purchased"] = 0
                    data["remaining_trial"] = trial - (cost - purchased)
                else:
                    return {
                        "success": False,
                        "blocked": True,
                        "processed_count": processed,
                        "exhausted": True,
                        "remaining_credits": trial + purchased,
                    }

                self.credit_manager._save_credit_data(data)
                processed += 1
                current = data.get("remaining_trial", 0) + data.get("remaining_purchased", 0)
            except Exception as e:
                return {
                    "success": False,
                    "blocked": True,
                    "processed_count": processed,
                    "error": str(e),
                }

        # UI 업데이트
        self.master.after(0, self.update_credit_display)

        return {
            "success": True,
            "processed_count": processed,
            "blocked": False,
            "remaining_credits": current,
        }

    def _test_get_state(self) -> dict:
        """앱 상태 반환"""
        return {
            "is_registered": self.is_registered_user,
            "has_credit_manager": self.credit_manager is not None,
            "has_wf_manager": self.wf_manager is not None,
            "selected_path": getattr(self, "SELECTED_PATH", None),
            "is_admin_mode": self.is_admin_mode,
            "run_mode": self.run_mode,
        }

    def _test_get_policy(self) -> dict:
        """정책 정보 반환 (WF-ACT 테스트 포맷)"""
        policy_data = {}
        if self.credit_manager:
            policy_data = dict(self.credit_manager.policy)

        # WF-ACT 테스트에서 기대하는 포맷으로 변환
        return {
            "identity": {
                "app_name": "dwg_batch_print",
                "display_name": "DWG Batch Print",
            },
            "policy": {
                "credit_per_work": policy_data.get("credit_per_work", 40),
                "trial_credits": policy_data.get("trial_credits", 4000),
                "credit_type": policy_data.get("credit_type", "per_file"),
            },
            "app_name": "dwg_batch_print",
            "display_name": "DWG Batch Print",
            "credit_per_work": policy_data.get("credit_per_work", 40),
            "trial_credits": policy_data.get("trial_credits", 4000),
            **policy_data,  # 원본 데이터도 포함
        }

    def _test_get_settings(self) -> dict:
        """설정 정보 반환 (WF-ACT 테스트 포맷)"""
        try:
            return {
                "app_version": APP_VERSION_FULL,
                "full_version": APP_VERSION_FULL,
                "version": APP_VERSION_FULL,
                "app_config": {
                    "full_version": APP_VERSION_FULL,
                    "app_name": "dwg_batch_print",
                },
                "runtime_config": {
                    "full_version": APP_VERSION_FULL,
                },
                "run_mode": self.run_mode,
                "demo_capture_enabled": self.demo_capture_enabled,
            }
        except Exception:
            return {}

    def _test_reload_config(self) -> bool:
        """설정 및 정책 재로드 (테스트용)"""
        try:
            # CreditManager의 정책 재로드
            if self.credit_manager:
                self.credit_manager._reload_policy()
            return True
        except Exception as e:
            self.logger.error(f"[WF-ACT] reload_config failed: {e}")
            return False

    def _test_get_trial_info(self) -> dict:
        """체험판 크레딧 정보 반환 (테스트용)"""
        if not self.credit_manager:
            return {"error": "credit_manager_not_initialized"}
        try:
            policy = self.credit_manager.policy or {}
            data = self.credit_manager._load_credit_data()
            return {
                "initial_credits": policy.get("trial_credits", 4000),
                "remaining_trial": data.get("remaining_trial", 0),
                "trial_credits": policy.get("trial_credits", 4000),
            }
        except Exception as e:
            return {"error": str(e)}

    def _test_sync_registration(self) -> dict:
        """등록 정보 서버 동기화 (테스트용)"""
        if not self.wf_manager:
            return {"success": False, "error": "wf_manager_not_initialized"}
        try:
            return {"success": True, "message": "sync_attempted"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _test_save_settings(self, settings: dict) -> dict:
        """설정 저장 (테스트용)"""
        try:
            import json
            settings_file = Path.home() / ".wf_rpa" / "dwg_batch_print" / "settings.json"
            data = {}
            if settings_file.exists():
                with open(settings_file, "r", encoding="utf-8") as f:
                    data = json.load(f) or {}
            if "test_config" not in data:
                data["test_config"] = {}
            data["test_config"].update(settings)
            with open(settings_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _test_load_settings(self) -> dict:
        """설정 로드 (테스트용)"""
        try:
            import json
            settings_file = Path.home() / ".wf_rpa" / "dwg_batch_print" / "settings.json"
            if not settings_file.exists():
                return {}
            with open(settings_file, "r", encoding="utf-8") as f:
                data = json.load(f) or {}
            return {
                "app_config": data.get("app_config", {}),
                "ui_config": data.get("ui_config", {}),
                "test_config": data.get("test_config", {}),
            }
        except Exception as e:
            return {"error": str(e)}

    def _test_get_button_state(self, button_name: str) -> dict:
        """버튼 상태 반환"""
        try:
            button_map = {
                "work": getattr(self, "print_button", None),
                "register": getattr(self, "register_button", None),
                "settings": getattr(self, "settings_button", None),
            }
            btn = button_map.get(button_name)
            if btn:
                return {
                    "exists": True,
                    "state": str(btn.cget("state")),
                    "text": str(btn.cget("text")),
                }
            return {"exists": False}
        except Exception as e:
            return {"exists": False, "error": str(e)}

    def _test_click_button(self, button_name: str) -> bool:
        """버튼 클릭 시뮬레이션"""
        try:
            button_map = {
                "work": getattr(self, "print_button", None),
                "register": getattr(self, "register_button", None),
                "settings": getattr(self, "settings_button", None),
            }
            btn = button_map.get(button_name)
            if btn and str(btn.cget("state")) != "disabled":
                btn.invoke()
                return True
            return False
        except Exception:
            return False

    def on_closing(self):
        """앱 종료 처리"""
        # WF-ACT 테스트 서버 정리
        try:
            if hasattr(self, "test_server") and self.test_server:
                self.test_server.stop()
        except Exception:
            pass

        # 관리자 모드 정리
        if self.is_admin_mode:
            self.remove_log_handler()

        # 앱 종료 시: 로컬 크레딧에 변경이 있다면 마지막으로 동기화 시도 (베스트에포트)
        try:
            if self.credit_manager:
                status = self.credit_manager.get_sync_status()
                if status.get("needs_sync"):
                    self.logger.info("🔄 앱 종료 시 크레딧 동기화 시도...")
                    result = self.credit_manager.check_and_sync_credits()
                    self.logger.info(f"[SYNC-EXIT] {result}")
        except Exception as e:
            self.logger.warning(f"[SYNC-EXIT] 동기화 시도 중 오류: {e}")

        # 전역 핫키 리스너 정리 - dwg_classifier에서 마이그레이션
        try:
            self._stop_global_hotkey_listener()
        except Exception:
            pass

        try:
            _clear_cross_app_running()
        except Exception:
            pass
        self.master.destroy()

    def create_user_directories(self):
        """사용자 디렉토리 구조 생성"""
        user_home = os.path.expanduser("~")
        wf_rpa_dir = os.path.join(user_home, ".wf_rpa")
        app_dir = os.path.join(wf_rpa_dir, "dwg_batch_print")

        try:
            if not os.path.exists(wf_rpa_dir):
                os.makedirs(wf_rpa_dir)
            if not os.path.exists(app_dir):
                os.makedirs(app_dir)
            for subfolder in ["logs", "res"]:
                subfolder_path = os.path.join(app_dir, subfolder)
                if not os.path.exists(subfolder_path):
                    os.makedirs(subfolder_path)
        except Exception as e:
            self.logger.error(f"[ERROR] 디렉토리 생성 실패: {e}")
            return False
        return True

    def init_ui(self):
        # 설정 파일에서 기본/변경 값을 읽어 창 크기 결정 (코드 내 별도 기본값 없음)
        window_width = self.ui.get("window_width", 580)
        window_height = self.ui.get("window_height", 180)
        adjusted_height = window_height

        # pyautogui lazy import - 화면 크기는 tkinter로 가져오기 (300ms 절약)
        self.width = self.master.winfo_screenwidth()
        self.height = self.master.winfo_screenheight()
        x_coord = int((self.width - window_width) / 2)
        y_coord = int((self.height - adjusted_height) / 2)

        self.master.geometry(f"{window_width}x{adjusted_height}+{x_coord}+{y_coord}")
        
        # Saved/demo geometry override (설정 파일 값만 사용)
        override_geo = getattr(self.config, "window_geometry_override", "")
        if override_geo and override_geo.strip():
            try:
                self.master.geometry(override_geo.strip())
                self.logger.info(f"[DEBUG] geometry override at startup: {override_geo}")
            except Exception as e:
                self.logger.warning(f"geometry override 적용 실패(무시): {e}")
        
        self.master.title(f"DWG 일괄 인쇄 {APP_VERSION_DISPLAY}")

        topmost_setting = 1
        custom_settings = load_custom_settings()
        if custom_settings and "runtime_config" in custom_settings:
            topmost_setting = 1 if custom_settings["runtime_config"].get("topmost", True) else 0

        # 초기 Topmost 적용 (설정에서 로드)
        self.master.wm_attributes("-topmost", topmost_setting)
        self.master.resizable(True, True)
        self.master.minsize(window_width, max(120, adjusted_height))
        
        # 전역 폰트 설정 적용 (메인창 폰트 크기 일관성 보장)
        apply_global_fonts(self.master, self.ui)
        
        self.create_ui_elements()

        # 창을 앞으로 가져오고 포커스 설정
        self.master.lift()
        self.master.focus_force()
        
        # 데모 모드: Alt+G, Alt+C 핫키 바인딩 (dwg_classifier에서 마이그레이션)
        if self.demo_capture_enabled:
            self._bind_debug_geometry_hotkey()

    def create_ui_elements(self):
        master = self.master
        
        # Grid로 루트 윈도우 설정하여 상하좌우 여백 균등 분배
        master.grid_rowconfigure(0, weight=1)
        master.grid_columnconfigure(0, weight=1)
        
        main_frame = tk.Frame(master, padx=12, pady=0)
        main_frame.grid(row=0, column=0, sticky="nsew")

        folder_frame = tk.Frame(main_frame)
        folder_frame.pack(fill="x", pady=(6, 6))

        self.folder_button = tk.Button(
            folder_frame,
            text="폴더 선택",
            width=10,
            command=self.select_folder_license_check,
            font=("맑은 고딕", self.ui["font_size"]),
        )
        self.folder_button.pack(side="left")

        self.folder_entry = tk.Entry(
            folder_frame, state="readonly", font=("맑은 고딕", self.ui["font_size"])
        )
        self.folder_entry.pack(side="left", fill="x", expand=True, padx=(10, 0))
        # 이전 작업 폴더 자동 로드 (설치 직후를 제외하고 항상)
        try:
            last = (self.config.get_last_selected_folder() or "").strip()
            if last and os.path.isdir(last):
                self.set_selected_path(last)
        except Exception:
            pass

        progress_frame = tk.Frame(main_frame)
        progress_frame.pack(fill="x", pady=(0, 6))

        self.progress_bar_label = tk.Label(
            progress_frame, text="진행률:", width=11, font=("맑은 고딕", self.ui["font_size"])
        )
        self.progress_bar_label.pack(side="left")

        # 진행률 라벨 클릭 이벤트 바인딩 (관리자 모드 진입)
        self.progress_bar_label.bind("<Button-1>", self.on_progress_label_click)
        # Tooltip: progress description only
        self._bind_tooltip(self.progress_bar_label, "처리 진척률 표시")

        # 스피너 라벨 추가 (진행률 라벨과 프로그레스바 사이)
        self.spinner_label = tk.Label(
            progress_frame, text="○", font=("맑은 고딕", self.ui["font_size_title"]), width=2, fg="#cccccc"
        )
        self.spinner_label.pack(side="left", padx=(5, 0))

        self.progress_bar = ttk.Progressbar(
            progress_frame, orient="horizontal", mode="determinate", maximum=100
        )
        self.progress_bar.pack(side="left", fill="x", expand=True, padx=(10, 0))

        status_frame = tk.Frame(main_frame)
        status_frame.pack(fill="x", pady=(0, 6))
        status_frame.columnconfigure(0, weight=1)
        status_frame.columnconfigure(1, weight=1)
        status_frame.columnconfigure(2, weight=1)
        # Topmost 토글은 설정창에서만 제공 (메인창엔 없음)

        # 폴더 스캔 토글 버튼 (체크박스 스타일)
        self.scan_toggle_btn = tk.Checkbutton(
            status_frame,
            text="폴더 스캔",
            variable=self.scan_toggle_var,
            command=self.on_scan_toggle,
            font=("맑은 고딕", self.ui["font_size"]),
        )
        self.scan_toggle_btn.grid(row=0, column=0, sticky="w")

        self.progress_label = tk.Label(
            status_frame, text="0/0", font=("맑은 고딕", self.ui["font_size"])
        )
        self.progress_label.grid(row=0, column=1)

        self.credit_label = tk.Label(
            status_frame,
            text="크레딧 확인 중...",
            fg="blue",
            font=("맑은 고딕", self.ui["font_size"]),
            cursor="hand2",
        )
        self.credit_label.grid(row=0, column=2, sticky="e")

        # (removed) Topmost toggle lives in Settings window

        button_frame = tk.Frame(main_frame)
        button_frame.pack(fill="x", pady=(6, 6))
        button_frame.columnconfigure(0, weight=1)
        button_frame.columnconfigure(1, weight=1)
        button_frame.columnconfigure(2, weight=1)
        button_frame.columnconfigure(3, weight=1)

        self.print_button = tk.Button(
            button_frame,
            text="DWG 인쇄",
            command=self.start_dwg_print,
            width=12,
            height=1,
            state="disabled",
            font=("맑은 고딕", self.ui["font_size"]),
        )
        self.print_button.grid(row=0, column=0, padx=5, sticky="ew")

        # 등록 상태에 따라 버튼 텍스트와 기능 결정
        if self.is_registered_user:
            self.settings_button = tk.Button(
                button_frame,
                text="설 정",
                command=self.open_settings_window,
                width=12,
                height=1,
                font=("맑은 고딕", self.ui["font_size"]),
            )
        else:
            self.settings_button = tk.Button(
                button_frame,
                text="등 록",
                command=self.open_registration_window,
                width=12,
                height=1,
                font=("맑은 고딕", self.ui["font_size"]),
            )
        self.settings_button.grid(row=0, column=1, padx=5, sticky="ew")

        # 크레딧 갱신 버튼 추가
        self.refresh_credit_button = tk.Button(
            button_frame,
            text="업데이트",
            command=self.on_refresh_credit,
            width=12,
            height=1,
            font=("맑은 고딕", self.ui["font_size"]),
        )
        self.refresh_credit_button.grid(row=0, column=2, padx=5, sticky="ew")

        self.exit_button = tk.Button(
            button_frame,
            text="종 료",
            command=self.on_closing,
            width=12,
            height=1,
            font=("맑은 고딕", self.ui["font_size"]),
        )
        self.exit_button.grid(row=0, column=3, padx=5, sticky="ew")

        # 진행률 라벨에 툴팁 추가 (관리자 모드 접근을 위한 힌트)
        # self._bind_tooltip(self.progress_bar_label, "진행률 표시 - 클릭하면 고급 설정 접근")

        self.update_credit_display()

    # Topmost persistence and live toggle are handled by Settings window

    def create_log_frame(self):
        """관리자 모드용 로그 프레임 생성"""
        if self.log_frame:
            return

        # 메인 프레임 찾기
        main_frame = None
        for child in self.master.winfo_children():
            if isinstance(child, tk.Frame):
                main_frame = child
                break

        if not main_frame:
            return

        # 로그 프레임 생성
        self.log_frame = tk.Frame(main_frame)
        self.log_frame.pack(fill="both", expand=True, pady=(10, 0))

        # 로그 제목 및 옵션
        log_header_frame = tk.Frame(self.log_frame)
        log_header_frame.pack(fill="x", pady=(0, 5))

        log_label = tk.Label(
            log_header_frame, text="실시간 로그 (DEBUG 레벨)", font=("맑은 고딕", 13, "bold")
        )
        log_label.pack(side="left")

        # 자동 스크롤 체크박스
        self.auto_scroll_var = tk.BooleanVar(value=True)
        self.auto_scroll_checkbox = tk.Checkbutton(
            log_header_frame,
            text="자동 스크롤",
            variable=self.auto_scroll_var,
            font=("맑은 고딕", self.ui.get("font_size", 14)),
        )
        self.auto_scroll_checkbox.pack(side="right")

        # 로그 텍스트 위젯과 스크롤바
        log_text_frame = tk.Frame(self.log_frame)
        log_text_frame.pack(fill="both", expand=True)

        # 스크롤바
        self.log_scrollbar = tk.Scrollbar(log_text_frame)
        self.log_scrollbar.pack(side="right", fill="y")

        # 텍스트 위젯
        self.log_text = tk.Text(
            log_text_frame,
            wrap="word",
            yscrollcommand=self.log_scrollbar.set,
            font=("Consolas", self.ui.get("font_size", 14)),
            bg="#f8f8f8",
            fg="#333333",
            height=12,
            state="disabled",
        )
        self.log_text.pack(side="left", fill="both", expand=True)
        self.log_scrollbar.config(command=self.log_text.yview)

        # 로그 핸들러 설정
        self.setup_log_handler()

    def destroy_log_frame(self):
        """로그 프레임 제거"""
        if self.log_frame:
            # 로그 핸들러 제거
            self.remove_log_handler()

            self.log_frame.destroy()
            self.log_frame = None
            self.log_text = None
            self.log_scrollbar = None
            self.auto_scroll_var = None
            self.auto_scroll_checkbox = None

    def setup_log_handler(self):
        """실시간 로그 표시를 위한 핸들러 설정"""
        import logging

        class TextHandler(logging.Handler):
            def __init__(self, text_widget, auto_scroll_var, master):
                super().__init__()
                self.text_widget = text_widget
                self.auto_scroll_var = auto_scroll_var
                self.master = master

            def emit(self, record):
                try:
                    msg = self.format(record)
                    # 메인 스레드에서 UI 업데이트
                    self.master.after(0, lambda: self._append_log(msg))
                except Exception:
                    pass

            def _append_log(self, msg):
                try:
                    if self.text_widget and self.text_widget.winfo_exists():
                        self.text_widget.config(state="normal")
                        # 최신 로그를 하단에 추가 (콘솔과 동일하게)
                        self.text_widget.insert("end", msg + "\n")

                        # 로그가 너무 많아지면 상단 제거 (1000라인 제한)
                        lines = int(self.text_widget.index("end-1c").split(".")[0])
                        if lines > 1000:
                            self.text_widget.delete("1.0", "500.0")

                        self.text_widget.config(state="disabled")

                        # 자동 스크롤이 활성화되어 있으면 맨 아래로 스크롤
                        if self.auto_scroll_var and self.auto_scroll_var.get():
                            self.text_widget.see("end")
                except Exception:
                    pass

        # 기존 핸들러 제거
        self.remove_log_handler()

        # 새 핸들러 추가
        self.text_handler = TextHandler(self.log_text, self.auto_scroll_var, self.master)
        self.text_handler.setLevel(logging.DEBUG)

        # 포맷터 설정 (콘솔과 동일한 형식)
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        self.text_handler.setFormatter(formatter)

        # 루트 로거에 핸들러 추가 (모든 로그 캐치)
        root_logger = logging.getLogger()
        root_logger.addHandler(self.text_handler)

        # 현재 앱 로거에도 추가
        if self.logger:
            self.logger.addHandler(self.text_handler)

    def remove_log_handler(self):
        """로그 핸들러 제거"""
        if hasattr(self, "text_handler"):
            try:
                # 루트 로거에서 제거
                root_logger = logging.getLogger()
                root_logger.removeHandler(self.text_handler)

                # 현재 앱 로거에서 제거
                if self.logger:
                    self.logger.removeHandler(self.text_handler)

                delattr(self, "text_handler")
            except Exception:
                pass

    def on_refresh_credit(self):
        if not self.credit_manager:
            self.logger.error("크레딧 매니저가 초기화되지 않았습니다.")
            messagebox.showerror("오류", "크레딧 매니저가 초기화되지 않았습니다.")
            return
        try:
            # 무료 앱 체크: trial_credits가 -1이면 구매 이력 없음
            trial_credits = self.credit_manager.policy.get("trial_credits", 0)

            # 팝업에 표시할 메시지 (크레딧 관련만)
            popup_messages = []
            credentials_updated = False

            # 1. 구매 이력 동기화 (무료 앱은 스킵) - 팝업에 표시
            if trial_credits != -1:
                result = self.credit_manager.pull_and_apply_purchases()

                if result.get("success"):
                    added = result.get("added", 0)
                    applied_ids = result.get("applied_ids") or []

                    if added > 0:
                        msg = f"✅ {len(applied_ids)}건의 구매 이력을 반영했습니다."
                        msg += f"\n추가된 크레딧: {added:,}개\n"
                        msg += "\n적용된 구매 ID:\n"
                        for tid in applied_ids:
                            if "T" in tid and ":" in tid:
                                display_id = tid.replace("T", " ").replace(":", "시").replace(".", "분")
                            else:
                                display_id = tid
                            msg += f"• {display_id}\n"
                        popup_messages.append(msg)
                    else:
                        popup_messages.append("신규 구매 이력이 없습니다.")
                else:
                    popup_messages.append(f"⚠️ 크레딧 갱신 실패: {result.get('message')}")

            # 2. 앱 정책 및 관리자 설정 동기화 (백그라운드, 팝업에 표시 안함)
            try:
                from wf_settings_common import sync_policies_from_sheets  # type: ignore
                policy_result = sync_policies_from_sheets("dwg_batch_print", self.logger)
                if policy_result.get("success"):
                    self.logger.info("정책 동기화 완료")
                else:
                    self.logger.warning(f"정책 동기화 실패: {policy_result.get('message')}")
            except Exception as e:
                self.logger.warning(f"정책 동기화 중 오류 (무시): {e}")

            # 3. 크리덴셜 파일 업데이트 체크
            try:
                from wf_googlesheets_manager import get_sheets_manager  # type: ignore
                sheets_manager = get_sheets_manager(test_mode=False)
                admin_config = sheets_manager.get_admin_config_full()
                creds_file_id = admin_config.get("credentials_file_id", "").strip()

                if creds_file_id:
                    from wf_settings_common import update_credentials_from_drive  # type: ignore
                    creds_result = update_credentials_from_drive(creds_file_id, self.logger)
                    if creds_result.get("success"):
                        credentials_updated = True
                        self.logger.info(f"크리덴셜 업데이트 완료: {creds_result.get('backup_path')}")
                    else:
                        self.logger.warning(f"크리덴셜 업데이트 실패: {creds_result.get('message')}")
            except Exception as e:
                self.logger.warning(f"크리덴셜 업데이트 체크 중 오류 (무시): {e}")

            # 결과 표시 (크레딧 관련만)
            final_message = "\n".join(popup_messages)
            if credentials_updated:
                final_message += "\n\n🔄 인증 정보가 업데이트되었습니다.\n변경사항 적용을 위해 앱을 재시작해주세요."

            messagebox.showinfo("업데이트 완료", final_message)
            self.update_credit_display()

        except Exception as e:
            messagebox.showerror("업데이트 오류", str(e))
            self.logger.error(f"업데이트 오류: {e}")
            import traceback
            self.logger.error(traceback.format_exc())

    def on_progress_label_click(self, event):
        """크레딧 라벨 클릭 이벤트 - 관리자 모드 토글"""
        try:
            if self.is_admin_mode:
                # 이미 관리자 모드인 경우 → 즉시 비활성화 (비밀번호 불필요)
                self._exit_admin_mode()
                self.logger.info("관리자 모드가 비활성화되었습니다.")
                self._show_toast("관리자 모드 비활성화", 1500)
                self.update_credit_display()
            else:
                run_mode = getattr(self, "run_mode", getattr(self.config, "run_mode", "release"))
                if run_mode == "dev":  # dev 모드에서만 암호 없이 진입
                    self._enter_admin_mode()
                    self.logger.info("관리자 모드가 활성화되었습니다. (30분 후 자동 해제)")
                    self._show_toast(
                        "관리자 모드 활성화\n(30분 후 자동 해제 또는 클릭시 해제)", 2500
                    )
                    self.update_credit_display()
                else:
                    from tkinter import simpledialog

                    password = simpledialog.askstring(
                        "관리자 인증", "관리자 비밀번호를 입력하세요:", show="*", parent=self.master
                    )

                    if password is None:  # 취소 버튼
                        return

                    if password == self.admin_password:
                        self._enter_admin_mode()
                        self.logger.info("관리자 모드가 활성화되었습니다. (30분 후 자동 해제)")
                        self._show_toast(
                            "관리자 모드 활성화\n(30분 후 자동 해제 또는 클릭시 해제)", 2500
                        )
                        self.update_credit_display()
                    else:
                        self.logger.warning("관리자 인증 실패 시도")
                        self._show_toast("비밀번호가 올바르지 않습니다", 1500)

        except Exception as e:
            self.logger.error(f"관리자 모드 토글 오류: {e}")

    def _enter_admin_mode(self):
        """관리자 모드 진입"""
        self.is_admin_mode = True
        self.admin_mode_start_time = datetime.datetime.now()

        # 30분 타이머 설정 (1800000ms = 30분)
        self.admin_mode_timer = self.master.after(1800000, self._auto_exit_admin_mode)

        # UI 변경
        self.master.title(f"DWG 일괄 인쇄 {APP_VERSION_FULL} [🔧 관리자 모드]")
        self.progress_bar_label.config(bg="#ffe6e6")  # 연한 빨간 배경

        # 창 크기 조정 가능하도록 설정
        self.master.resizable(True, True)

        # 창 크기 확장
        current_geometry = self.master.geometry()
        width = current_geometry.split("x")[0]
        pos = current_geometry.split("+", 1)[1] if "+" in current_geometry else "0+0"
        new_geometry = f"{width}x{self.expanded_window_height}+{pos}"
        self.master.geometry(new_geometry)

        # 로그 창 생성
        self.create_log_frame()

        # 관리자 모드 활성화 로그 - UI 로그창에 직접 출력
        import ctypes
        import os

        def write_to_log(msg):
            """UI 로그창에 직접 출력"""
            if self.log_text and self.log_text.winfo_exists():
                self.log_text.config(state="normal")
                self.log_text.insert("end", msg + "\n")
                self.log_text.config(state="disabled")
                self.log_text.see("end")

        write_to_log("=" * 50)
        write_to_log("  관리자 모드 활성화")
        write_to_log("=" * 50)

        try:
            is_admin = ctypes.windll.shell32.IsUserAnAdmin()
            write_to_log(f"관리자 권한으로 실행 중: {is_admin}")
        except Exception:
            write_to_log("관리자 권한 확인 실패")

        write_to_log(f"현재 사용자: {os.environ.get('USERNAME', 'Unknown')}")
        write_to_log(f"현재 작업 디렉토리: {os.getcwd()}")

        # 하드웨어 정보 출력
        write_to_log("-" * 50)
        write_to_log("  하드웨어 정보")
        write_to_log("-" * 50)
        try:
            import wf_hwinfo
            hw_info = wf_hwinfo.HardwareInfo()
            write_to_log(f"하드웨어 지문: {hw_info.fingerprint}")
            write_to_log(f"CPU ID: {hw_info.cpu_id}")
            write_to_log(f"메인보드 ID: {hw_info.mainboard_id}")
            if hasattr(hw_info, "storage_id"):
                write_to_log(f"스토리지 ID: {hw_info.storage_id}")
            if hasattr(hw_info, "cpu_name"):
                write_to_log(f"CPU 이름: {hw_info.cpu_name}")
            if hasattr(hw_info, "cpu_cores"):
                write_to_log(f"CPU 코어: {hw_info.cpu_cores}")
        except Exception as e:
            write_to_log(f"하드웨어 정보 조회 실패: {e}")

        write_to_log("-" * 50)
        write_to_log("30분 후 자동 해제 또는 클릭시 해제")
        write_to_log("=" * 50)

        self._show_toast("관리자 모드 활성화", 1000)

    def _exit_admin_mode(self):
        """관리자 모드 종료"""
        self.is_admin_mode = False
        self.admin_mode_start_time = None

        # 타이머 취소
        if self.admin_mode_timer:
            self.master.after_cancel(self.admin_mode_timer)
            self.admin_mode_timer = None

        # 관리자 모드 종료 로그
        if self.is_admin_mode:
            print("관리자 모드를 종료합니다")

        # 로그 창 제거
        self.destroy_log_frame()

        # 창 크기 복원
        current_geometry = self.master.geometry()
        width = current_geometry.split("x")[0]
        pos = current_geometry.split("+", 1)[1] if "+" in current_geometry else "0+0"
        new_geometry = f"{width}x{self.original_window_height}+{pos}"
        self.master.geometry(new_geometry)

        # 창 크기 조정 비활성화
        self.master.resizable(False, False)

        # UI 원상 복구
        self.master.title(f"DWG 일괄 인쇄 {APP_VERSION_DISPLAY}")
        self.progress_bar_label.config(bg=self.master.cget("bg"))

        # 프로그레스 초기화
        self.progress_bar["value"] = 0
        self.progress_bar.config(maximum=100)
        self.progress_label.config(text="0/0")
        self.spinner_label.config(text="○", fg="#cccccc")

        self._show_toast("관리자 모드 비활성화", 1000)

    def _auto_exit_admin_mode(self):
        """30분 후 자동 관리자 모드 종료"""
        self._exit_admin_mode()
        self._show_toast("관리자 모드 자동 해제", 1500)
        self.update_credit_display()

    def exit_admin_mode(self):
        """관리자 모드 종료 - UI 복원"""
        try:
            self.is_admin_mode = False

            # 창 높이 원복
            width = 480
            height = 200
            x_coord = self.master.winfo_x()
            y_coord = self.master.winfo_y()

            self.master.geometry(f"{width}x{height}+{x_coord}+{y_coord}")

            # 타이틀 원복
            self.master.title(f"BOM 엑셀 저장 {APP_VERSION_DISPLAY}")

            # 크레딧 라벨 배경색 원복
            self.credit_label.config(bg=self.master.cget("bg"))

            pass  # 관리자 모드 종료
        except Exception as e:
            pass  # 관리자 모드 종료 오류 무시

    def on_scan_toggle(self):
        """폴더 스캔 토글 처리"""
        if self.scan_toggle_var.get():
            # 스캔 활성화 (ON)
            if not self.SELECTED_PATH:
                # 폴더 미선택 시 선택 유도
                messagebox.showwarning("폴더 미선택", "먼저 작업할 폴더를 선택해주세요.")
                self.scan_toggle_var.set(False)
                return

            # 폴더 스캔 실행
            try:
                self.logger.info(f"폴더 스캔 시작: {self.SELECTED_PATH}")
                
                # 경로 유효성 재확인
                if not self.DWG_PATH:
                    self.logger.error("DWG_PATH가 None입니다")
                    messagebox.showerror("오류", "폴더 경로가 설정되지 않았습니다.")
                    self.scan_toggle_var.set(False)
                    return

                # DWG 파일 카운트
                from pathlib import Path

                self.logger.debug(f"DWG_PATH: {self.DWG_PATH}")
                folder_path = Path(self.DWG_PATH)
                
                if not folder_path.exists():
                    self.logger.error(f"폴더가 존재하지 않습니다: {self.DWG_PATH}")
                    messagebox.showerror("오류", f"폴더를 찾을 수 없습니다:\n{self.DWG_PATH}")
                    self.scan_toggle_var.set(False)
                    return

                # DWG 파일 카운트
                file_count = 0
                for f in folder_path.iterdir():
                    if f.is_file() and f.suffix.lower() == ".dwg":
                        file_count += 1

                self.logger.debug(f"스캔 결과: {file_count}개 파일")

                if file_count > 0:
                    self.initial_file_count = file_count
                    self.cumulative_processed_count = 0
                    self.is_first_run = True
                    self.last_run_success_count = 0
                    self.progress_bar.config(maximum=self.initial_file_count, value=0)
                    self.progress_label.config(text=f"0/{self.initial_file_count}")
                    self.print_button.config(state="normal")
                    self.is_folder_scanned = True
                    self.logger.info(f"폴더 스캔 완료: {file_count}개 파일")
                else:
                    self.print_button.config(state="disabled")
                    self.progress_label.config(text="파일 없음")
                    messagebox.showinfo("스캔 완료", "작업 대상 파일이 없습니다.")
                    self.scan_toggle_var.set(False)
                    self.is_folder_scanned = False
            except Exception as e:
                self.logger.error(f"폴더 스캔 중 오류: {e}")
                self.print_button.config(state="disabled")
                self.progress_label.config(text="오류")
                messagebox.showerror("스캔 오류", f"폴더 스캔 중 오류가 발생했습니다:\n{e}")
                self.scan_toggle_var.set(False)
                self.is_folder_scanned = False
        else:
            # 스캔 비활성화 (OFF) - 초기화
            self.is_folder_scanned = False
            self.print_button.config(state="disabled")
            self.progress_label.config(text="?/?")
            self.logger.info("폴더 스캔 초기화")

    def start_spinner(self):
        """스피너 애니메이션 시작 (스레드 안전)"""

        def _start():
            if not self.spinner_running:
                self.spinner_running = True
                self.spinner_index = 0
                self._animate_spinner()

        # 메인 스레드에서 실행
        try:
            self.master.after(0, _start)
        except Exception:
            # 이미 메인 스레드인 경우
            _start()

    def stop_spinner(self):
        """스피너 애니메이션 중지 (스레드 안전)"""

        def _stop():
            self.spinner_running = False
            self.spinner_label.config(text="", fg="black")

        # 메인 스레드에서 실행
        try:
            self.master.after(0, _stop)
        except Exception:
            # 이미 메인 스레드인 경우
            _stop()

    def _animate_spinner(self):
        """스피너 애니메이션 실행 (재귀적으로 호출)"""
        if self.spinner_running:
            # 현재 스피너 문자 표시 (검은 원 ●)
            spinner_char = self.spinner_chars[self.spinner_index]
            self.spinner_label.config(text=spinner_char, fg="black")

            # 다음 인덱스로 이동
            self.spinner_index = (self.spinner_index + 1) % len(self.spinner_chars)

            # 100ms 후에 다시 호출
            self.master.after(100, self._animate_spinner)

    def update_progress_ui(self, current, total, status_text=""):
        """진행 상황 업데이트 (스레드 안전)"""

        # 백그라운드 스레드에서 호출될 수 있으므로 메인 스레드로 전달
        def _update():
            try:
                # 프로그레스 바가 업데이트될 때 스피너 정지 (파일 처리 완료 시점)
                if self.spinner_running:
                    self.stop_spinner()

                self.last_run_success_count = current
                progress_in_bar = self.cumulative_processed_count + current
                self.progress_bar["value"] = progress_in_bar

                is_retry = not self.is_first_run
                label_text = f"{progress_in_bar}/{self.initial_file_count}"
                if is_retry:
                    label_text += f" (재시도: {current}/{total})"

                self.progress_label.config(text=label_text)
                self.master.update_idletasks()
            except Exception as e:
                self.logger.error(f"Progress UI update failed: {e}")

        # 메인 스레드에서 실행
        try:
            self.master.after(0, _update)
        except Exception:
            # after() 실패 시 직접 호출 (이미 메인 스레드인 경우)
            _update()

    def select_folder_license_check(self):
        """폴더 선택 전 라이선스 및 하드웨어 검증"""
        # 1. 등록 여부 확인
        if not self.is_registered_user:
            self.logger.warning(
                "기능을 사용하려면 먼저 사용자 등록이 필요합니다. '등 록' 버튼을 눌러주세요."
            )
            messagebox.showwarning(
                "등록 필요",
                "기능을 사용하려면 먼저 사용자 등록이 필요합니다.\n'등 록' 버튼을 눌러주세요.",
            )
            return

        # 2. 하드웨어 검증
        if not self.verify_hardware_fingerprint():
            self.logger.error(
                "등록된 사용자의 하드웨어 정보와 일치하지 않습니다. 다른 컴퓨터에서는 사용할 수 없습니다."
            )
            messagebox.showerror(
                "인증 실패",
                "등록된 사용자의 하드웨어 정보와 일치하지 않습니다.\n다른 컴퓨터에서는 사용할 수 없습니다.",
            )
            return

        selected_path = filedialog.askdirectory()
        self.set_selected_path(selected_path if selected_path else None)

        if not self.SELECTED_PATH:
            self.folder_entry.config(state="normal")
            self.folder_entry.delete(0, tk.END)
            self.folder_entry.config(state="readonly")
            return

        self.folder_entry.config(state="normal")
        self.folder_entry.delete(0, tk.END)
        self.folder_entry.insert(0, self.DWG_PATH or "")
        self.folder_entry.config(state="readonly")

        # Lazy import: DwgBatchPrintAutomation은 폴더 선택 시점에 로드 (startup 시간 최적화)
        try:
            self.logger.info(f"폴더 선택됨: {self.DWG_PATH}")
            self.logger.debug("DwgBatchPrintAutomation 모듈 로딩 시작...")
            _log_startup("Loading DwgBatchPrintAutomation (lazy)")
            from automation import DwgBatchPrintAutomation
            self.logger.debug("DwgBatchPrintAutomation 모듈 로딩 완료")
            _log_startup("DwgBatchPrintAutomation loaded")

            self.logger.debug("DwgBatchPrintAutomation 인스턴스 생성 시작...")
            self.automation = DwgBatchPrintAutomation(folder_path=self.DWG_PATH, console_mode=False)
            self.logger.debug("DwgBatchPrintAutomation 인스턴스 생성 완료")

        # 설정 적용
            self.automation.set_edrawings_path(self.config.program_path)
            self.automation.set_restart_count(self.config.restart_count)
            self.automation.set_timeouts(
                self.config.wait_timeout,
                self.config.restart_sleep,
                self.config.final_sleep
            )
            
            self.logger.debug("콜백 함수 설정 중...")
            self.automation.set_progress_callback(self.update_progress_ui)
            self.automation.set_credit_update_callback(self.update_credit_display)
            self.automation.set_credit_manager(self.credit_manager)
            self.logger.debug("콜백 함수 설정 완료")
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            self.logger.error(f"DwgBatchPrintAutomation 초기화 실패:\n{error_details}")
            messagebox.showerror(
                "초기화 실패",
                f"폴더 처리 준비 중 오류가 발생했습니다:\n\n{str(e)}\n\n로그 파일을 확인해주세요."
            )
            return

        # DWG 파일 스캔
        try:
            self.logger.debug("폴더 스캔 시작...")
            dwg_files = self.automation.scan_dwg_files()
            file_count = len(dwg_files)
            self.logger.debug(f"스캔 결과: {file_count}개 파일")

            if file_count > 0:
                self.initial_file_count = file_count
                self.cumulative_processed_count = 0
                self.is_first_run = True
                self.last_run_success_count = 0
                self.progress_bar.config(maximum=self.initial_file_count, value=0)
                self.progress_label.config(text=f"0/{self.initial_file_count}")
                self.print_button.config(state="normal")
                self.logger.info(f"폴더 스캔 완료: {file_count}개 파일 발견")
            else:
                self.print_button.config(state="disabled")
                self.progress_label.config(text="파일 없음")
                self.logger.warning("처리 가능한 파일이 없습니다")
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            self.logger.error(f"폴더 스캔 중 오류:\n{error_details}")
            messagebox.showerror(
                "스캔 실패", 
                f"폴더 스캔 중 오류가 발생했습니다:\n\n{str(e)}"
            )
            self.print_button.config(state="disabled")
            self.progress_label.config(text="오류")

    def verify_hardware_fingerprint(self):
        """하드웨어 핑거프린트 검증"""
        try:
            if not self.wf_manager:
                return False
            stored_hardware = self.wf_manager.get_user_info()
            # 새 구조: client_hw_fingerprint, 구 구조: hardware_fingerprint (하위 호환)
            stored_fingerprint = stored_hardware.get(
                "client_hw_fingerprint"
            ) or stored_hardware.get("hardware_fingerprint", "")

            import wf_hwinfo  # type: ignore

            current_fingerprint = wf_hwinfo.HardwareInfo().fingerprint

            self.logger.debug(f"기존 지문: {stored_fingerprint}")
            self.logger.debug(f"현재 지문: {current_fingerprint}")
            return stored_fingerprint == current_fingerprint
        except Exception as e:
            self.logger.error(f"하드웨어 검증 실패: {e}")
            return False

    def show_failed_files_dialog(self, failed_files):
        """실패한 파일 목록을 모달 팝업으로 표시"""
        try:
            # 모달 창 생성
            dialog = tk.Toplevel(self.master)
            dialog.title("처리 실패 파일 목록")
            dialog.transient(self.master)
            dialog.grab_set()

            # 창 크기 및 위치 설정
            dialog_width = 600
            dialog_height = 400
            x = self.master.winfo_rootx() + (self.master.winfo_width() - dialog_width) // 2
            y = self.master.winfo_rooty() + (self.master.winfo_height() - dialog_height) // 2
            dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")
            dialog.resizable(True, True)

            # 최상위 설정
            dialog.wm_attributes("-topmost", 1)

            # 메인 프레임
            main_frame = tk.Frame(dialog, padx=15, pady=15)
            main_frame.pack(fill="both", expand=True)

            # 제목 라벨
            title_label = tk.Label(
                main_frame,
                text=f"⚠️ {len(failed_files)}개 파일 처리 실패",
                font=("맑은 고딕", 9, "bold"),
                fg="#d9534f",
            )
            title_label.pack(pady=(0, 10))

            # 안내 메시지
            info_label = tk.Label(
                main_frame,
                text="2차 시도까지 완료했으나 아래 파일들의 처리에 실패했습니다:",
                font=("맑은 고딕", 9),
                fg="#555",
            )
            info_label.pack(pady=(0, 10))

            # 스크롤바가 있는 리스트박스 프레임
            list_frame = tk.Frame(main_frame)
            list_frame.pack(fill="both", expand=True, pady=(0, 15))

            # 스크롤바
            scrollbar = tk.Scrollbar(list_frame)
            scrollbar.pack(side="right", fill="y")

            # 리스트박스
            listbox = tk.Listbox(
                list_frame,
                font=("Consolas", 9),
                yscrollcommand=scrollbar.set,
                selectmode="extended",
                bg="#f9f9f9",
                fg="#333",
            )
            listbox.pack(side="left", fill="both", expand=True)
            scrollbar.config(command=listbox.yview)

            # 실패한 파일 목록 추가
            for idx, file_info in enumerate(failed_files, 1):
                if isinstance(file_info, dict):
                    filename = file_info.get("file", file_info.get("filename", "Unknown"))
                    error = file_info.get("error", "")
                    if error:
                        display_text = f"{idx}. {filename} - {error}"
                    else:
                        display_text = f"{idx}. {filename}"
                elif isinstance(file_info, (tuple, list)):
                    # 튜플이나 리스트인 경우 첫 번째 요소(파일명)만 사용
                    filename = file_info[0] if len(file_info) > 0 else "Unknown"
                    display_text = f"{idx}. {filename}"
                else:
                    # 문자열인 경우
                    display_text = f"{idx}. {file_info}"

                listbox.insert(tk.END, display_text)

            # 버튼 프레임
            button_frame = tk.Frame(main_frame)
            button_frame.pack(fill="x")

            # 클립보드 복사 버튼
            def copy_to_clipboard():
                try:

                    def format_file_info(idx, f):
                        if isinstance(f, dict):
                            return f"{idx}. {f.get('file', f.get('filename', 'Unknown'))}"
                        elif isinstance(f, (tuple, list)):
                            filename = f[0] if len(f) > 0 else "Unknown"
                            return f"{idx}. {filename}"
                        else:
                            return f"{idx}. {f}"

                    file_list_text = "\n".join(
                        [format_file_info(idx, f) for idx, f in enumerate(failed_files, 1)]
                    )
                    dialog.clipboard_clear()
                    dialog.clipboard_append(file_list_text)
                    dialog.update()
                    messagebox.showinfo(
                        "복사 완료", "실패한 파일 목록이 클립보드에 복사되었습니다.", parent=dialog
                    )
                except Exception as e:
                    self.logger.error(f"클립보드 복사 실패: {e}")

            copy_button = tk.Button(
                button_frame, text="📋 목록 복사", command=copy_to_clipboard, width=15
            )
            copy_button.pack(side="left", padx=5)

            # 닫기 버튼
            close_button = tk.Button(button_frame, text="확인", command=dialog.destroy, width=15)
            close_button.pack(side="right", padx=5)

            # 엔터키로 닫기
            dialog.bind("<Return>", lambda e: dialog.destroy())
            dialog.bind("<Escape>", lambda e: dialog.destroy())

            # 포커스 설정
            dialog.focus_set()

            # 모달 대기
            self.master.wait_window(dialog)

        except Exception as e:
            self.logger.error(f"실패 파일 목록 표시 중 오류: {e}")
            # 폴백: 간단한 메시지박스로 표시
            file_names = "\n".join(
                [
                    f.get("file", f) if isinstance(f, dict) else str(f)
                    for f in failed_files[:10]  # 최대 10개만
                ]
            )
            if len(failed_files) > 10:
                file_names += f"\n... 외 {len(failed_files) - 10}개"
            messagebox.showwarning(
                "처리 실패", f"{len(failed_files)}개 파일 처리 실패:\n\n{file_names}"
            )

    def start_dwg_print(self):
        """DWG 인쇄 시작 (백그라운드 스레드에서 실행)"""
        if not self.DWG_PATH:
            return

        # DwgBatchPrintAutomation 객체가 없으면 여기서 생성 (실제 작업 시점)
        if not hasattr(self, "automation") or self.automation is None:
            try:
                self.logger.info("DwgBatchPrintAutomation 객체 생성 중...")
                from automation import DwgBatchPrintAutomation

                self.automation = DwgBatchPrintAutomation(
                    folder_path=self.DWG_PATH, console_mode=False
                )
                # 설정 적용
                self.automation.set_edrawings_path(self.config.program_path)
                self.automation.set_restart_count(self.config.restart_count)
                self.automation.set_timeouts(
                    self.config.wait_timeout,
                    self.config.restart_sleep,
                    self.config.final_sleep
                )
                self.automation.set_progress_callback(self.update_progress_ui)
                self.automation.set_credit_update_callback(self.update_credit_display)
                self.automation.set_credit_manager(self.credit_manager)
                self.logger.info("DwgBatchPrintAutomation 객체 생성 완료")
            except Exception as e:
                self.logger.error(f"DwgBatchPrintAutomation 초기화 실패: {e}")
                messagebox.showerror("초기화 실패", f"DWG 인쇄 준비 중 오류가 발생했습니다:\n{e}")
                return

        if not self.automation:
            return

        # DWG 파일 스캔
        dwg_files = self.automation.scan_dwg_files()
        files_to_process_count = len(dwg_files)

        if self.credit_manager:
            credit_status = self.credit_manager.get_credit_status()
            remaining_credits = credit_status.get("remaining_credits", 0)

            if remaining_credits != -1:  # 무제한이 아닌 경우
                cost_per_file = self.credit_manager.get_per_item_cost()
                required_credits = files_to_process_count * cost_per_file

                if remaining_credits == 0:
                    self.logger.error("사용 가능한 크레딧이 없습니다.")
                    messagebox.showerror("크레딧 부족", "사용 가능한 크레딧이 없습니다.")
                    return
                elif remaining_credits < required_credits:
                    processable_count = (
                        remaining_credits // cost_per_file
                        if cost_per_file > 0
                        else files_to_process_count
                    )
                    msg = f"크레딧이 부족하여 {processable_count}개만 처리 가능합니다. 계속하시겠습니까?"
                    if not messagebox.askyesno("크레딧 확인", msg):
                        return

        # 버튼 비활성화
        self.folder_button.config(state="disabled")
        self.print_button.config(state="disabled")
        self.exit_button.config(state="disabled")
        self.settings_button.config(state="disabled")
        self.refresh_credit_button.config(state="disabled")

        # 백그라운드 스레드에서 실행
        def worker():
            """백그라운드 작업 스레드"""
            exception_info: dict[str, Any] = {"error": None, "result": None}
            try:
                result = self.automation.print_dwg_files()
                exception_info["result"] = result
            except Exception as e:
                exception_info["error"] = e
            finally:
                # 메인 스레드에서 UI 업데이트 (스레드 안전)
                self.master.after(0, lambda: self._on_print_complete(exception_info))

        # 스레드 시작
        threading.Thread(target=worker, daemon=True, name="DWG-Print-Worker").start()

    def _on_print_complete(self, exception_info):
        """작업 완료 후 UI 업데이트 (메인 스레드에서 실행)"""
        try:
            # 예외 발생 시 사용자에게 알림
            if exception_info.get("error"):
                error = exception_info["error"]
                messagebox.showerror(
                    "작업 실패", f"DWG 인쇄 중 오류가 발생했습니다:\n\n{str(error)}"
                )
                return

            result = exception_info.get("result", {})
            if not result.get("success", False):
                messagebox.showerror("작업 실패", result.get("message", "알 수 없는 오류"))
                return

            # 진행 상태 업데이트
            printed_count = result.get("printed", 0)
            failed_count = result.get("failed", 0)
            total_count = result.get("total", 0)
            
            self.cumulative_processed_count = printed_count
            self.is_first_run = False

            # 실패 파일 확인
            failed_files = result.get("failed_files", [])

            if failed_files:
                self.progress_label.config(
                    text=f"{printed_count}/{total_count} ({len(failed_files)}개 실패)"
                )
                self.print_button.config(state="normal")

                # 🚨 핵심 기능: 실패한 파일 목록을 모달 팝업으로 표시 (메인 스레드에서 안전하게 호출)
                self.show_failed_files_dialog(failed_files)
            else:
                self.progress_label.config(
                    text=f"{printed_count}/{total_count} (완료)"
                )
                self.print_button.config(state="disabled")

            # 크레딧 표시 업데이트
            self.update_credit_display()

            # 백그라운드 동기화 (결과 표시 후)
            def background_sync():
                try:
                    if self.credit_manager:
                        sync_status = self.credit_manager.get_sync_status()
                        if sync_status.get("needs_sync"):
                            self.logger.info(
                                "🧾 처리 완료 후 사용 내역 동기화 시도 (백그라운드)..."
                            )
                            log_result = self.credit_manager.check_and_sync_credits()
                            self.logger.info(f"[SYNC-AFTER-RUN] {log_result}")
                except Exception as e:
                    self.logger.warning(f"[USAGE-LOG-AFTER-RUN] 사용 로그 기록 중 오류: {e}")

            # 백그라운드 스레드로 동기화 실행
            threading.Thread(target=background_sync, daemon=True, name="Credit-Sync-Worker").start()

        finally:
            # 항상 버튼 활성화 (예외 발생 시에도 보장)
            self.folder_button.config(state="normal")
            self.exit_button.config(state="normal")
            self.settings_button.config(state="normal")
            self.refresh_credit_button.config(state="normal")

            self.logger.info("🏁 작업 완료 처리 종료")

    def open_registration_window(self):
        """등록 창 열기 (미등록 사용자용)"""
        # 디렉토리는 __init__에서 비동기 생성됨
        
        # 등록 모듈이 없는 경우 처리
        if create_trial_window is None:
            self.logger.error(
                "등록 모듈을 찾을 수 없어 사용자 등록을 진행할 수 없습니다. 관리자에게 문의하세요."
            )
            messagebox.showerror(
                "등록 모듈 없음",
                "등록 모듈을 찾을 수 없어 사용자 등록을 진행할 수 없습니다.\n관리자에게 문의하세요.",
            )
            return

        try:
            import wf_hwinfo  # type: ignore

            hw_info = wf_hwinfo.HardwareInfo()
            hardware_info = {
                "CPU ID": hw_info.cpu_id,
                "메인보드 ID": hw_info.mainboard_id,
                "스토리지 ID": getattr(hw_info, "storage_id", ""),
                "하드웨어 지문": hw_info.fingerprint,
            }
        except Exception as e:
            hardware_info = {"오류": "하드웨어 정보를 가져올 수 없습니다"}

        # 등록 창을 모달로 열고, 닫힐 때까지 대기
        if not callable(create_trial_window):
            self.logger.error("등록 창 함수를 호출할 수 없습니다. 관리자에게 문의하세요.")
            messagebox.showerror(
                "등록 모듈 오류", "등록 창 함수를 호출할 수 없습니다. 관리자에게 문의하세요."
            )
            return

        registration_window_obj = create_trial_window(self, hardware_info, ui_settings=self.ui)
        toplevel_window = getattr(registration_window_obj, "trial_win", None)
        # TrialRegistrationWindow 객체에서 실제 Toplevel 창(trial_win)을 가져와서 모달 처리
        if toplevel_window:
            # ⚠️ 중요: 모달 창으로 확실히 설정 (리팩토링 시에도 유지할 것!)
            toplevel_window.transient(self.master)  # 부모 창과 연결
            toplevel_window.grab_set()  # 다른 창 비활성화 - 절대 제거하지 말 것
            # 메인 창이 topmost이면 모달 창도 topmost로 설정 (창 순서 유지)
            if self.master.attributes("-topmost"):
                toplevel_window.wm_attributes("-topmost", 1)
            toplevel_window.focus_set()  # 포커스 설정
            self.master.wait_window(toplevel_window)  # 창이 닫힐 때까지 대기

        # 등록 창이 닫힌 후, 상태를 다시 확인하고 UI를 업데이트
        self.post_registration_update()

    def update_registration_button(self):
        try:
            if getattr(self, "settings_button", None):
                if self.is_registered_user:
                    self.settings_button.config(text="설 정", command=self.open_settings_window)
                else:
                    self.settings_button.config(text="등 록", command=self.open_registration_window)
        except Exception:
            pass

    def post_registration_update(self):
        """등록 절차 완료 후 UI를 업데이트합니다."""
        self.is_registered_user = self.check_user_registration()
        self.update_registration_button()
        if self.is_registered_user:
            self.update_credit_display()  # 크레딧 정보도 갱신
            # messagebox.showinfo("등록 완료", "사용자 등록이 성공적으로 완료되었습니다.")

    def open_settings_window(self):
        """설정 창 열기"""
        # 폴더 선택 여부와 관계없이 설정 창을 열 수 있도록 self.automation 확인 로직을 주석 처리합니다.
        # if not self.automation:
        #     messagebox.showinfo("알림", "설정을 열기 전에 먼저 폴더를 선택해주세요.")
        #     return

        try:
            import wf_hwinfo  # type: ignore

            hw_info = wf_hwinfo.HardwareInfo()
            hardware_info = {
                "CPU ID": hw_info.cpu_id,
                "메인보드 ID": hw_info.mainboard_id,
                "스토리지 ID": getattr(hw_info, "storage_id", ""),
                "하드웨어 지문": hw_info.fingerprint,
            }
        except Exception as e:
            hardware_info = {"오류": "하드웨어 정보를 가져올 수 없습니다"}

        # 설정 창을 열고 닫힐 때까지 대기
        # 설정 변경이 메인창에 즉시 반영되도록 UI 객체(self)를 부모로 전달
        settings_window_obj = create_settings_window(self, hardware_info)
        toplevel_window = getattr(settings_window_obj, "settings_win", None)
        # SettingsWindow 객체에서 실제 Toplevel 창(settings_win)을 가져와서 대기
        if toplevel_window:
            # 모달 창 설정이 ui_setting.py에서 이미 처리되므로 wait_window만 호출
            self.master.wait_window(toplevel_window)  # 창이 닫힐 때까지 대기


def _handle_sync_registration():
    """--sync-registration 인자 처리: 로컬 등록정보를 Google Sheets에 동기화"""
    print("\n" + "=" * 50)
    print("WorksFree 등록정보 동기화")
    print("=" * 50 + "\n")

    try:
        from wf_googlesheets_manager import get_sheets_manager
        manager = get_sheets_manager()

        if not manager:
            print("[오류] Google Sheets 연결에 실패했습니다.")
            print("네트워크 연결을 확인하세요.")
            return 1

        # 앱 버전 가져오기
        try:
            from app_setting_data import SettingsData
            settings = SettingsData()
            app_version = settings.full_version
        except Exception:
            app_version = ""

        result = manager.sync_local_registration_to_sheets("dwg_batch_print", app_version)

        if result["success"]:
            if result.get("already_synced"):
                print("[정보] " + result["message"])
            else:
                print("[성공] " + result["message"])
            return 0
        else:
            print("[실패] " + result["message"])
            return 1

    except Exception as e:
        print(f"[오류] 동기화 중 예외 발생: {e}")
        return 1


def main():
    # --test-mode 인자 처리 (WF-ACT 인증 테스트 모드)
    test_mode = "--test-mode" in sys.argv

    # --sync-registration 인자 처리 (GUI 없이 동기화만 수행)
    if "--sync-registration" in sys.argv:
        sys.exit(_handle_sync_registration())

    # DWG 기준 통일: ensure_config_files 제거 (wf_rpa_config 접근 시 자동 생성)

    _log_startup("main() entry")
    # 테스트 모드에서는 single instance 및 cross-app 체크 건너뛰기
    if not test_mode:
        # Enforce single instance across the system (prevents recursive spawns)
        is_first, _handle = _acquire_single_instance()
        _log_startup("single instance check complete")
        if not is_first:
            # Avoid creating any UI if another instance is running
            try:
                print("Another dwg_batch_print instance is already running. Exiting.")
            except Exception:
                pass
            return

        # 교차 앱 실행 방지 (공통 헬퍼 사용)
        if check_cross_app_running_and_exit:
            check_cross_app_running_and_exit("dwg_batch_print")
    else:
        _log_startup("Test mode: skipping single instance and cross-app checks")

    # Mark this app as running in the shared config (for cross-app guard)
    try:
        _set_cross_app_running("dwg_batch_print")
        import atexit as _atexit

        _atexit.register(_clear_cross_app_running)
    except Exception:
        pass

    _log_startup("Creating Tk root window")
    root = tk.Tk()
    _log_startup("Tk root created")
    
    # 시작 시 플래시 방지: 초기화 전 잠시 숨김
    try:
        root.withdraw()
    except Exception:
        pass
    
    # 작업표시줄 아이콘 설정 (개발/릴리스 환경 모두 지원)
    try:
        # 아이콘 파일명 (새 아이콘: 02_DWG_Batch_Print.ico, 기존: dp.ico)
        icon_names = ["02_DWG_Batch_Print.ico", "dp.ico"]

        if getattr(sys, 'frozen', False):
            # 릴리스: 실행 파일 인접 res 폴더 또는 _internal/res
            base_paths = [
                Path(sys.executable).parent / "res",
                Path(sys.executable).parent / "_internal" / "res",
            ]
        else:
            # 개발: 앱 폴더 내 res 폴더
            base_paths = [Path(__file__).parent / "res"]

        icon_candidates = [bp / name for bp in base_paths for name in icon_names]
        icon_path = next((p for p in icon_candidates if p.exists()), None)
        if icon_path:
            root.iconbitmap(str(icon_path))
    except Exception:
        pass
    
    # 실행 모드 확인 (env/settings.json)
    try:
        from app_setting_data import get_config as _getcfg
        _cfg = _getcfg()
        _run_mode = getattr(_cfg, "run_mode", "release")
    except Exception:
        _cfg, _run_mode = None, "release"

    # Seed res assets into user home for release builds (no-op if already present or no source)
    try:
        target_res = (
            Path(__file__).parent / "res"
            if _run_mode in ("dev", "demo")
            else Path.home() / ".wf_rpa" / "dwg_batch_print" / "res"
        )
        bundle_candidates = [
            Path(__file__).parent / "res",
        ]
        if getattr(sys, "frozen", False):
            exe_dir = Path(sys.executable).parent
            bundle_candidates = [
                exe_dir / "res",
                exe_dir / "_internal" / "res",
            ] + bundle_candidates
        seed_res_if_missing(target_res, bundle_candidates, logger=None)
    except Exception:
        pass

    app = DwgBatchPrintGUIApplication(root)
    _log_startup("DwgBatchPrintGUIApplication initialized - UI ready")
    _flush_startup_log()

    # WF-ACT 테스트 모드: TestServer 초기화
    if test_mode:
        try:
            app.init_test_server()
            _log_startup("Test server initialized")
        except Exception as e:
            print(f"[WF-ACT] Failed to initialize test server: {e}")
    # 초기화가 끝난 후 창 표시 및 포커스
    try:
        root.deiconify()
        
        enable_demo_capture = (_run_mode == "demo") or bool(os.environ.get("WF_ENABLE_DEMO_CAPTURE"))
        # ===== 데모 캡처: Alt+C로 1920x1040 캡처 저장 (demo 전용) =====
        if enable_demo_capture:
            try:
                import keyboard as _kb
                from PIL import ImageGrab as _ImageGrab
                from datetime import datetime as _dt

                # 캡처 디렉터리: 실행 경로 우선, 실패 시 사용자 홈으로 폴백
                _capture_dir = None
                _capture_candidates = [
                    Path(__file__).resolve().parent / "demo_captures",
                    Path.home() / ".wf_rpa" / "dwg_batch_print" / "demo_captures",
                ]
                for _cand in _capture_candidates:
                    try:
                        _cand.mkdir(parents=True, exist_ok=True)
                        if os.access(_cand, os.W_OK):
                            _capture_dir = _cand
                            break
                    except Exception as _mkdir_err:
                        _log_startup(f"Alt+C capture dir fallback 실패: {_cand} -> {_mkdir_err}")
                if _capture_dir is None:
                    raise RuntimeError("Alt+C 캡처 디렉터리를 준비할 수 없습니다.")
                _log_startup(f"Alt+C capture dir: {_capture_dir}")

                def _capture_demo_screen():
                    try:
                        img = _ImageGrab.grab()
                        cropped = img.crop((0, 0, 1920, 1040))
                        ts = _dt.now().strftime("%Y%m%d_%H%M%S")
                        fname = f"demo_{ts}.png"
                        fpath = _capture_dir / fname
                        cropped.save(fpath, "PNG")
                        try:
                            import winsound as _ws
                            _ws.Beep(900, 120)
                        except Exception:
                            pass
                        # 콘솔 로그에도 남김
                        print(f"[CAPTURE] saved: {fpath}")
                    except Exception as _ce:
                        print(f"[CAPTURE] failed: {_ce}")
                        _log_startup(f"Alt+C capture failed: {_ce}")

                # 전역 핫키 등록
                _kb.add_hotkey('alt+c', _capture_demo_screen)
                _log_startup("Alt+C capture hotkey registered")
                
                # 종료 시 핫키 제거 연결
                try:
                    if hasattr(app, 'on_closing'):
                        _orig_close = app.on_closing
                        def _wrapped_close(*args, **kwargs):
                            try:
                                _kb.remove_hotkey('alt+c')
                            except Exception as _rm_err:
                                _log_startup(f"Alt+C hotkey remove failed: {_rm_err}")
                            return _orig_close(*args, **kwargs)
                        app.on_closing = _wrapped_close
                except Exception as _cleanup_err:
                    _log_startup(f"Alt+C hotkey cleanup hook failed: {_cleanup_err}")
            except Exception as _init_err:
                # keyboard/PIL 가용성 문제 시 실패 로그 남김
                _log_startup(f"Alt+C hotkey init failed: {_init_err}")
        else:
            _log_startup("Alt+C capture disabled for release mode")
        # ===== 데모 캡처 끝 =====
        # 데모 모드: 오른쪽 2/3 영역의 중앙에 배치 (settings.json 크기 그대로 사용)
        if _run_mode == "demo":
            try:
                w = app.ui.get("window_width", 580)
                h = app.ui.get("window_height", 180)
                sw = root.winfo_screenwidth()
                sh = root.winfo_screenheight()
                rx = sw // 3
                rw = sw - rx
                ry = 0
                rh = sh
                gx = rx + (rw - w) // 2
                gy = ry + (rh - h) // 2
                root.geometry(f"{w}x{h}+{gx}+{gy}")
                _log_startup(f"Window position set (demo, settings): ({gx}, {gy}, {w}, {h})")
            except Exception:
                pass
        # dev/release: 기본 init_ui의 중앙 배치 유지
        root.lift()
        root.focus_force()
    except Exception:
        pass
    # 자동 설정 테스트 모드: 환경변수 WF_AUTO_SETTINGS_TEST=1일 때 설정창 열고 자동 종료
    import os as _os

    if _os.getenv("WF_AUTO_SETTINGS_TEST") == "1":

        def _auto_show_and_exit():
            try:
                app.open_settings_window()
            finally:
                root.after(800, root.destroy)

        root.after(150, _auto_show_and_exit)

    # WF-ACT 테스트 모드 초기화
    if test_mode:
        try:
            app.init_test_server()
        except Exception as e:
            print(f"[WF-ACT] Failed to initialize test server: {e}")

    root.mainloop()


if __name__ == "__main__":
    main()
