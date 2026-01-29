import os
import sys
from pathlib import Path

# Windows 콘솔 UTF-8 강제 설정 (GUI 모드에서는 stdout/stderr가 None일 수 있음)
if sys.platform == "win32":
    import io
    if sys.stdout is not None and hasattr(sys.stdout, 'buffer'):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    if sys.stderr is not None and hasattr(sys.stderr, 'buffer'):
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# ==================== STARTUP PROFILER ====================
_STARTUP_LOG = []
_STARTUP_ENABLED = True  # 릴리스 모드에서도 경량 로깅 활성화
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
        path = Path.home() / ".wf_rpa" / "conversion_verifier" / "startup_profile.log"
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
    from pathlib import Path

    default_full = "v0.7.0.0"
    full_version = default_full

    try:
        if getattr(sys, "frozen", False):
            # 릴리스 모드: 번들 버전 우선 (정확한 빌드 버전), fallback으로 사용자 홈
            base_path = Path(sys._MEIPASS) if hasattr(sys, '_MEIPASS') else Path(sys.executable).parent
            settings_file = base_path / ".wf_rpa" / "conversion_verifier" / "settings.json"

            # fallback: 사용자 홈 (버전 정보가 없을 수 있음)
            if not settings_file.exists():
                settings_file = Path.home() / ".wf_rpa" / "conversion_verifier" / "settings.json"
        else:
            # 개발 모드: 10.common/config/conversion_verifier/settings.json (통합 경로)
            app_root = Path(__file__).parent
            settings_file = app_root.parent.parent / "10.common" / "config" / "conversion_verifier" / "settings.json"
            # fallback: 앱 폴더의 config
            if not settings_file.exists():
                settings_file = app_root / "config" / "conversion_verifier" / "settings.json"

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

    # display_version은 앞 2자리만 (v0.7.0.2 → v0.7)
    parts = full_version.lstrip("v").split(".")
    display_version = "v" + ".".join(parts[:2])

    return full_version, display_version


APP_VERSION_FULL, APP_VERSION_DISPLAY = _load_version_info()

# Windows frozen executables (PyInstaller) can recursively spawn child processes
try:
    import multiprocessing  # noqa: F401

    multiprocessing.freeze_support()
    _log_startup("multiprocessing.freeze_support()")
except Exception:
    pass

# --- Single instance guard (Windows named mutex) ---
_instance_mutex_handle = None


def _acquire_single_instance(mutex_name: str = r"Global\\WF_CONVERSION_VERIFIER"):
    """단일 인스턴스 실행 보장 (Windows mutex)"""
    if os.name != "nt":
        return True, None
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        handle = kernel32.CreateMutexW(
            ctypes.c_void_p(None), ctypes.c_bool(False), ctypes.c_wchar_p(mutex_name)
        )
        if not handle:
            return True, None
        ERROR_ALREADY_EXISTS = 183
        existed = kernel32.GetLastError() == ERROR_ALREADY_EXISTS
        if existed:
            kernel32.CloseHandle(handle)
            return False, None
        return True, handle
    except Exception:
        return True, None


# --- Cross-app execution status helpers (unified skeleton) ---
def _set_cross_app_running(app_name: str):
    try:
        import json as _json
        from pathlib import Path as _Path
        import datetime as _dt

        cfg_dir = _Path.home() / ".wf_rpa"
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
common_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "10.common")
)
if common_path not in sys.path:
    sys.path.insert(0, common_path)
_log_startup("sys.path setup complete")

# -*- coding: utf-8 -*-
"""
Conversion Verifier Main UI Module
메인 GUI 인터페이스를 담당하는 모듈
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
from pathlib import Path

_log_startup("import filedialog, Path")
import logging
import threading
import json

_log_startup("import logging, threading, json")

# 현재 스크립트의 디렉토리를 Python 경로에 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# 앱 설정 로더
from app_setting_data import get_config  # type: ignore
from wf_ui_adaptive import get_adaptive_ui_settings, apply_global_fonts  # type: ignore

# 글로벌 로거 import
from wf_log import get_app_logger  # type: ignore

_log_startup("import wf_log")

try:
    from wf_register import create_trial_window  # type: ignore

    _log_startup("import wf_register")
except ImportError as e:
    print(f"등록 모듈(wf_register) import 실패: {e}")
    create_trial_window = None

try:
    from wf_credit_manager import WorksFreeManager, CreditManager  # type: ignore
    from wf_app_init_helpers import init_credit_and_policy_managers, check_cross_app_running_and_exit, seed_res_if_missing

    WFM_AVAILABLE = True
    _log_startup("import wf_credit_manager")
except ImportError as e:
    print(f"WorksFree 관리자 모듈 import 실패: {e}")
    WorksFreeManager = None
    CreditManager = None
    check_cross_app_running_and_exit = None
    WFM_AVAILABLE = False


class ConversionVerifierApp:
    """Conversion Verifier GUI 애플리케이션 클래스"""

    def __init__(self, master):
        self.master = master
        self.itself_dir = os.path.dirname(os.path.abspath(__file__))
        # MessageBox들이 메인창 기준으로 뜨도록 parent를 강제 지정
        self._bind_messagebox_parent()

        # 아이콘 경로 저장 (등록창/설정창에서 사용)
        self.icon_path = self._find_icon_path()

        # 설정 로더 초기화 (canonical sections + state)
        self.config = get_config()

        # 로거 초기화 (logging_config 적용)
        _lvl_map = {
            "CRITICAL": logging.CRITICAL,
            "ERROR": logging.ERROR,
            "WARNING": logging.WARNING,
            "INFO": logging.INFO,
            "DEBUG": logging.DEBUG,
            "NOTSET": logging.NOTSET,
        }
        try:
            log_level_str = (self.config.get_logging_config().get("log_level") or "INFO").upper()
            log_level = _lvl_map.get(log_level_str, logging.INFO)
        except Exception:
            log_level = logging.INFO
        self.logger = get_app_logger("conversion_verifier", console_level=log_level)
        self.app = None  # 호환성 유지
        self.paths = None  # 호환성 유지
        self.i18n = None  # 호환성 유지

        # WorksFree 전역 매니저 초기화 (기존 방식 유지)
        if WFM_AVAILABLE:
            self.wf_manager = WorksFreeManager()
        else:
            self.wf_manager = None
            self.logger.error("프로그램 핵심 모듈을 찾을 수 없습니다. 프로그램을 종료합니다.")
            messagebox.showerror(
                "치명적 오류", "프로그램 핵심 모듈을 찾을 수 없습니다.\n프로그램을 종료합니다."
            )
            sys.exit(1)

        # 앱 실행 상태 체크 (모듈 전역 헬퍼로 대체)
        # 기존 class-level check_and_set_execution_status는 더 이상 호출하지 않습니다.

        # 앱 설정 데이터는 위에서 초기화됨

        self.automation = None
        self.SELECTED_PATH = None
        self.checkbox_var = tk.BooleanVar(value=True)

        self.initial_file_count = 0
        self.cumulative_processed_count = 0
        self.is_first_run = True
        self.last_run_success_count = 0

        # Demo capture 설정 (DC 패턴)
        try:
            self.demo_capture_enabled = self.config and hasattr(self.config, 'is_demo') and self.config.is_demo()
        except Exception:
            self.demo_capture_enabled = False
        self.demo_capture_dir = None
        self.demo_capture_size = (1920, 1040)
        self._last_demo_capture_ts = 0.0

        # 스피너 관련 변수
        self.spinner_running = False
        self.spinner_index = 0
        self.spinner_chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]  # 브라유 패턴 스피너

        # 관리자 모드 변수
        self.is_admin_mode = False
        self.admin_mode_timer = None
        self.admin_mode_start_time = None
        # 🚀 최적화: admin 비밀번호 lazy 로딩 (Google Sheets 호출 지연)
        self._admin_password = None  # lazy load
        # Adaptive UI settings (font sizes, padding)
        self.ui = get_adaptive_ui_settings()

        # 로그 프레임 관련 변수
        self.log_frame = None
        self.log_text = None
        self.log_scrollbar = None
        self.auto_scroll_var = None
        self.auto_scroll_checkbox = None
        self.text_log_handler = None

        # 창 크기 관련
        self.original_window_height = 160  # 1입력 앱 기본 높이
        self.expanded_window_height = self.original_window_height + 300  # 관리자 모드: +300 고정

        # 사용자 등록 상태 초기 동기 확인 (플래그/reg_time_local)
        self.is_registered_user = False
        try:
            if self.wf_manager:
                self.is_registered_user = self.wf_manager.is_registered()
        except Exception:
            pass

        if CreditManager:
            # 공통 헬퍼로 크레딧/정책 초기화
            self.credit_manager = init_credit_and_policy_managers(
                app_name="conversion_verifier",
                wf_manager=self.wf_manager,
                master=self.master,
                logger=self.logger,
                recovery_delay_ms=800,
                policy_delay_ms=400,
            )
            # UI 업데이트
            try:
                self.master.after(0, self.update_credit_display)
            except Exception:
                pass
            # 정책 동기화 별도 스케줄
            try:
                self.master.after(400, self._async_refresh_policies)
            except Exception:
                threading.Thread(target=self._async_refresh_policies, daemon=True).start()
        else:
            self.credit_manager = None

        self.master.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.init_ui()
        
        # Demo capture 초기화
        if self.demo_capture_enabled:
            self._init_demo_capture()
            self._bind_debug_geometry_hotkey()
        
        # 🚀 사용자 디렉토리 비동기 생성 (KFN 패턴)
        try:
            self.master.after(200, lambda: threading.Thread(target=self.create_user_directories, daemon=True).start())
        except Exception:
            threading.Thread(target=self.create_user_directories, daemon=True).start()

    @property
    def admin_password(self) -> str:
        """🚀 Lazy 로딩: admin 비밀번호 (첫 접근 시 Google Sheets에서 로드)"""
        if self._admin_password is None:
            try:
                from wf_settings_common import get_admin_password  # type: ignore
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
            icon_names = ["04_Conversion_Verifier.ico", "CV.ico"]
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

    def create_user_directories(self):
        """사용자 디렉토리 구조 생성"""
        user_home = os.path.expanduser("~")
        wf_rpa_dir = os.path.join(user_home, ".wf_rpa")
        app_dir = os.path.join(wf_rpa_dir, "conversion_verifier")

        try:
            if not os.path.exists(wf_rpa_dir):
                os.makedirs(wf_rpa_dir)
            if not os.path.exists(app_dir):
                os.makedirs(app_dir)
            for subfolder in ["logs", "res"]:
                subfolder_path = os.path.join(app_dir, subfolder)
                if not os.path.exists(subfolder_path):
                    os.makedirs(subfolder_path)
            if self.logger:
                self.logger.info(f"사용자 디렉토리 구조 생성 완료: {wf_rpa_dir}")
        except Exception as e:
            if self.logger:
                self.logger.error(f"[ERROR] 디렉토리 생성 실패: {e}")
            return False
        return True

    def check_user_registration(self):
        """WorksFreeManager를 통해 사용자 등록 상태 확인"""
        if self.wf_manager:
            return self.wf_manager.is_registered()
        return False

    def set_selected_path(self, path: str | None):
        """선택된 경로를 설정하고 UI를 동기화 (통합 헬퍼)"""
        self.SELECTED_PATH = path

        # folder_entry 업데이트 (CV 방식)
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

            # WorksFreeManager가 가리키는 환경별 설정 파일 사용
            from pathlib import Path

            config_path = None
            try:
                if getattr(self, "wf_manager", None):
                    config_path = Path(self.wf_manager.config_file)
            except Exception:
                config_path = None

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
            exec_status["current_app"] = "conversion_verifier"
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
        """앱 실행 상태 해제 (WorksFreeManager 경로 우선)"""
        try:
            import json
            from pathlib import Path

            config_path = None
            try:
                if getattr(self, "wf_manager", None):
                    config_path = Path(self.wf_manager.config_file)
            except Exception:
                config_path = None
            if not config_path:
                home = Path.home()
                config_path = home / ".wf_rpa" / "wf_rpa_config.json"
            if not config_path.exists():
                return
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

    def update_registration_button(self):
        """등록 상태에 따라 설정/등록 버튼 텍스트 업데이트"""
        try:
            if getattr(self, "settings_button", None):
                if self.is_registered_user:
                    self.settings_button.config(text="설 정", command=self.open_settings_window)
                else:
                    self.settings_button.config(text="등 록", command=self.open_registration_window)
        except Exception:
            pass

    def update_credit_display(self):
        if not getattr(self, "credit_label", None) or not getattr(self, "wf_manager", None):
            return
        try:
            if not getattr(self, "credit_manager", None):
                self.credit_label.config(text="크레딧 확인 불가", fg="gray")
                return

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
            self.logger.error(f"크레딧 표시 업데이트 오류: {e}")

    def _bind_tooltip(self, widget, text: str):
        if not text:
            return
        # simple tooltip
        tip = {"win": None}

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
                font=("맑은 고딕", self.ui["font_size"]),
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

    def _async_refresh_policies(self):
        """정책 동기화 (백그라운드, 토스트 메시지 없음)"""

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

    # ---------- Demo Capture ----------
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
        """캡처 디렉터리 경로 확인 및 생성"""
        candidates = [
            Path(__file__).resolve().parent / "demo_captures",
            Path.home() / ".wf_rpa" / "conversion_verifier" / "demo_captures",
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
        """자동 캡처 (이벤트 발생 시 호출)"""
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
        """실제 화면 캡처 실행"""
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

    def _bind_debug_geometry_hotkey(self):
        """Alt+G: geometry 저장 (모든 모드), Alt+C: 화면 캡처 (demo 전용)"""
        try:
            # Alt+G는 항상 바인딩 (geometry 저장용)
            self.master.bind_all("<Alt-g>", self._on_debug_geometry_capture)

            # Alt+C는 demo 모드에서만 바인딩 (화면 캡처용)
            if self.config and hasattr(self.config, "is_demo") and self.config.is_demo():
                self.master.bind_all("<Alt-c>", self._on_manual_capture)
        except Exception as e:
            try:
                self.logger.debug(f"Alt hotkey bind 실패: {e}")
            except Exception:
                pass

    def _on_debug_geometry_capture(self, _event=None):
        """Alt+G: 현재 geometry를 로그에 찍고 즉시 settings.json에 저장"""
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
                toast_msg = f"geometry 저장됨: {geo}"
                self._show_toast(toast_msg, dur=1400)
                if self.logger:
                    self.logger.info(f"[DEBUG] geometry saved to settings: {geo}")
            else:
                self._show_toast("geometry 저장 실패", dur=1400)
        except Exception as e:
            try:
                if self.logger:
                    self.logger.debug(f"Alt+G 저장 실패: {e}")
            except Exception:
                pass

    def _on_manual_capture(self, _event=None):
        """Alt+C: 수동 화면 캡처"""
        if not self.demo_capture_enabled or not self.demo_capture_dir:
            self._show_toast("캡처 기능이 비활성화되어 있습니다", dur=1200)
            return
        
        try:
            # 쓰로틀링 무시하고 즉시 캡처
            self._last_demo_capture_ts = 0.0
            self._capture_demo_now("manual_capture", throttle_sec=0.0)
            self._show_toast("화면 캡처 완료", dur=1200)
        except Exception as e:
            self._show_toast(f"캡처 실패: {e}", dur=1500)
            if self.logger:
                self.logger.error(f"수동 캡처 실패: {e}")

    # ---------- Global Hotkey (Alt+C) for Modal Dialogs ----------
    def _start_global_hotkey_listener(self):
        """모달 창 활성화 중에도 Alt+C 수동 캡처가 가능하도록 전역 핫키 등록.

        Windows RegisterHotKey를 별도 스레드에서 사용하여 WM_HOTKEY 메시지를 수신.
        수신 시 Tk 메인스레드에서 _on_manual_capture를 안전하게 호출한다.
        """
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
        """전역 핫키 리스너 종료 (앱 종료 시 호출)."""
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

    # ==================== WF-ACT Test Mode ====================
    def init_test_server(self):
        """WF-ACT 인증 테스트용 TestServer 초기화"""
        try:
            # WF-ACT: 동기적으로 CreditManager 초기화 (테스트용)
            self._init_credit_manager_sync()

            # TestServer import (로컬 test_server.py 사용)
            from test_server import TestServer

            self.test_server = TestServer(app_name="conversion_verifier")

            # 핸들러 등록
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
                    app_name="conversion_verifier",
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
        """현재 총 크레딧 반환"""
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
        """크레딧 직접 설정"""
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
        """크레딧 추가"""
        self._ensure_credit_manager()
        if not self.credit_manager:
            return False
        try:
            data = self.credit_manager._load_credit_data()
            current = data.get("remaining_purchased", 0)
            if current != -1:
                data["remaining_purchased"] = current + amount
            self.credit_manager._save_credit_data(data)
            self.master.after(0, self.update_credit_display)
            return True
        except Exception as e:
            self.logger.error(f"[WF-ACT] add_credits failed: {e}")
            return False

    def _test_get_credit_status(self) -> dict:
        """크레딧 상태 상세 조회"""
        self._ensure_credit_manager()
        if not self.credit_manager:
            return {"success": False, "error": "credit_manager_not_initialized"}
        return self.credit_manager.get_credit_status()

    def _test_get_trial_info(self) -> dict:
        """체험판 크레딧 정보 반환"""
        self._ensure_credit_manager()
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

    def _test_get_registration_status(self) -> dict:
        """등록 상태 반환"""
        if not self.wf_manager:
            return {"is_registered": False, "email": None, "registered_at": None}
        user_info = self.wf_manager.get_user_info()
        return {
            "is_registered": self.wf_manager.is_registered(),
            "email": user_info.get("user_email") or user_info.get("email"),
            "registered_at": user_info.get("reg_time_local"),
            "app_version": APP_VERSION_FULL,
        }

    def _test_register(self, email: str) -> dict:
        """사용자 등록"""
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
                # WF-ACT: Grant trial credits on registration
                if self.credit_manager:
                    trial = self.credit_manager.policy.get("trial_credits", 4000)
                    data = self.credit_manager._load_credit_data()
                    data["remaining_trial"] = trial
                    self.credit_manager._save_credit_data(data)
            return {"success": success}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _test_clear_registration(self) -> bool:
        """등록 초기화"""
        if not self.wf_manager:
            return False
        try:
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

    def _test_sync_registration(self) -> dict:
        """등록 정보 서버 동기화"""
        if not self.wf_manager:
            return {"success": False, "error": "wf_manager_not_initialized"}
        return {"success": True, "message": "sync_attempted"}

    def _test_simulate_work(self, file_count: int = 1) -> dict:
        """작업 시뮬레이션 - 크레딧 차감 포함"""
        self._ensure_credit_manager()
        if not self.credit_manager:
            return {"success": False, "error": "credit_manager_not_initialized"}
        cost = self.credit_manager.policy.get("credit_per_work", 40)
        try:
            data = self.credit_manager._load_credit_data()
            remaining_trial = data.get("remaining_trial", 0)
            remaining_purchased = data.get("remaining_purchased", 0)
            if remaining_trial == -1 or remaining_purchased == -1:
                return {"success": True, "processed_count": file_count, "blocked": False}
            current = remaining_trial + remaining_purchased
        except Exception as e:
            return {"success": False, "error": f"credit_load_error: {e}"}
        processed = 0
        for i in range(file_count):
            if current < cost:
                return {"success": False, "blocked": True, "processed_count": processed,
                        "exhausted": True, "remaining_credits": current}
            try:
                data = self.credit_manager._load_credit_data()
                trial = data.get("remaining_trial", 0)
                purchased = data.get("remaining_purchased", 0)
                if purchased >= cost:
                    data["remaining_purchased"] = purchased - cost
                elif trial >= cost:
                    data["remaining_trial"] = trial - cost
                elif purchased + trial >= cost:
                    data["remaining_purchased"] = 0
                    data["remaining_trial"] = trial - (cost - purchased)
                else:
                    return {"success": False, "blocked": True, "processed_count": processed,
                            "exhausted": True, "remaining_credits": trial + purchased}
                self.credit_manager._save_credit_data(data)
                processed += 1
                current = data.get("remaining_trial", 0) + data.get("remaining_purchased", 0)
            except Exception as e:
                return {"success": False, "blocked": True, "processed_count": processed, "error": str(e)}
        self.master.after(0, self.update_credit_display)
        return {"success": True, "processed_count": processed, "blocked": False, "remaining_credits": current}

    def _test_get_state(self) -> dict:
        """앱 상태 반환"""
        return {
            "is_registered": self.is_registered_user,
            "has_credit_manager": self.credit_manager is not None,
            "has_wf_manager": self.wf_manager is not None,
            "selected_path": self.SELECTED_PATH,
            "is_admin_mode": self.is_admin_mode,
        }

    def _test_get_policy(self) -> dict:
        """정책 정보 반환"""
        policy_data = {}
        if self.credit_manager:
            policy_data = dict(self.credit_manager.policy)
        return {
            "identity": {"app_name": "conversion_verifier", "display_name": "Conversion Verifier"},
            "policy": {
                "credit_per_work": policy_data.get("credit_per_work", 40),
                "trial_credits": policy_data.get("trial_credits", 4000),
                "credit_type": policy_data.get("credit_type", "per_file"),
            },
            "app_name": "conversion_verifier",
            "credit_per_work": policy_data.get("credit_per_work", 40),
            "trial_credits": policy_data.get("trial_credits", 4000),
            **policy_data,
        }

    def _test_get_settings(self) -> dict:
        """설정 정보 반환"""
        try:
            return {"app_name": "conversion_verifier", "run_mode": getattr(self.config, "run_mode", "release"), "full_version": APP_VERSION_FULL, "version": APP_VERSION_FULL}
        except Exception:
            return {}

    def _test_reload_config(self) -> bool:
        """설정 및 정책 재로드 (테스트용)"""
        try:
            if self.credit_manager:
                self.credit_manager._reload_policy()
            return True
        except Exception:
            return False

    def _test_save_settings(self, settings: dict) -> dict:
        """설정 저장"""
        try:
            import json
            settings_file = self.config.settings_file
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
        """설정 로드"""
        try:
            import json
            settings_file = self.config.settings_file
            if not settings_file.exists():
                return {}
            with open(settings_file, "r", encoding="utf-8") as f:
                data = json.load(f) or {}
            return {"app_config": data.get("app_config", {}), "test_config": data.get("test_config", {})}
        except Exception as e:
            return {"error": str(e)}

    def _test_get_button_state(self, button_name: str) -> dict:
        """버튼 상태 반환"""
        try:
            button_map = {
                "work": getattr(self, "start_button", None),
                "register": getattr(self, "register_button", None),
                "settings": getattr(self, "settings_button", None),
            }
            btn = button_map.get(button_name)
            if btn:
                return {"exists": True, "state": str(btn.cget("state")), "text": str(btn.cget("text"))}
            return {"exists": False}
        except Exception as e:
            return {"exists": False, "error": str(e)}

    def _test_click_button(self, button_name: str) -> bool:
        """버튼 클릭 시뮬레이션"""
        try:
            button_map = {
                "work": getattr(self, "start_button", None),
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

        # 전역 핫키 리스너 정리 (DC 패턴)
        try:
            self._stop_global_hotkey_listener()
        except Exception:
            pass

        # 앱 종료 시: 로컬 크레딧에 변경이 있다면 마지막으로 동기화 시도 (베스트에포트)
        try:
            if getattr(self, "credit_manager", None):
                status = self.credit_manager.get_sync_status()
                if status.get("needs_sync"):
                    self.logger.info("🔄 앱 종료 시 크레딧 동기화 시도...")
                    result = self.credit_manager.check_and_sync_credits()
                    self.logger.info(f"[SYNC-EXIT] {result}")
        except Exception as e:
            self.logger.warning(f"[SYNC-EXIT] 동기화 시도 중 오류: {e}")

        # cross-app 상태 정리는 atexit/모듈 헬퍼에서 처리
        self.master.destroy()

    # create_user_directories, deploy_config_files, deploy_from_dev_config
    # are removed in favor of app_setting_data loader which ensures dirs
    # and migrates any legacy files as needed.

    def init_ui(self):
        # 설정 파일에서 기본/변경 값을 읽어 창 크기 결정 (코드 내 별도 기본값 없음)
        window_width = self.ui.get("window_width", 580)
        window_height = self.ui.get("window_height", 180)
        adjusted_height = window_height

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
                if self.logger:
                    self.logger.info(f"[DEBUG] geometry override at startup: {override_geo}")
            except Exception as e:
                if self.logger:
                    self.logger.warning(f"geometry override 적용 실패(무시): {e}")
        self.master.title(f"변환 확인 도구 {APP_VERSION_DISPLAY}")

        try:
            topmost_setting = bool(self.config.get_ui_config().get("window_topmost", True))
        except Exception:
            topmost_setting = True
        self.master.wm_attributes("-topmost", 1 if topmost_setting else 0)
        self.master.resizable(True, True)
        self.master.minsize(window_width, max(120, adjusted_height))
        
        # 전역 폰트 설정 적용 (메인창 폰트 크기 일관성 보장)
        apply_global_fonts(self.master, self.ui)
        
        self.create_ui_elements()

        # 창을 앞으로 가져오고 포커스 설정
        self.master.lift()
        self.master.focus_force()

    def create_ui_elements(self):
        """BOM2Excel과 완전히 동일한 UI 레이아웃"""
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
        # 이전 작업 폴더 자동 로드
        try:
            _last = (self.config.get_last_selected_folder() or "").strip()
            if _last and os.path.isdir(_last):
                self.SELECTED_PATH = _last
                self.folder_entry.config(state="normal")
                self.folder_entry.insert(0, _last)
                self.folder_entry.config(state="readonly")
        except Exception:
            pass

        progress_frame = tk.Frame(main_frame)
        progress_frame.pack(fill="x", pady=(0, 6))

        self.progress_bar_label = tk.Label(
            progress_frame, text="진행률:", width=11, font=("맑은 고딕", self.ui["font_size"])
        )
        self.progress_bar_label.pack(side="left")
        # 관리자 모드 진입 토글 바인딩
        self.progress_bar_label.bind("<Button-1>", lambda e: self.toggle_admin_mode())
        # Tooltip: progress description only
        self._bind_tooltip(self.progress_bar_label, "처리 진척률 표시")

        # 스피너 라벨 (진행률 라벨과 프로그레스바 사이)
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

        # 폴더 스캔 토글 버튼
        self.scan_toggle_var = tk.BooleanVar(value=False)
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

        button_frame = tk.Frame(main_frame)
        button_frame.pack(fill="x", pady=(6, 6))
        button_frame.columnconfigure(0, weight=1)
        button_frame.columnconfigure(1, weight=1)
        button_frame.columnconfigure(2, weight=1)
        button_frame.columnconfigure(3, weight=1)

        self.print_button = tk.Button(
            button_frame,
            text="변환확인",
            command=self.start_conversion_check,
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

        # 초기 데이터 상태 저장
        self.comparison_data = []

        self.update_credit_display()

    def on_checkbox_toggle(self):
        pass

    def on_scan_toggle(self):
        """폴더 스캔 토글 처리"""
        if self.scan_toggle_var.get():
            # 스캔 활성화 (ON)
            if not self.SELECTED_PATH:
                messagebox.showwarning("폴더 미선택", "먼저 작업할 폴더를 선택해주세요.")
                self.scan_toggle_var.set(False)
                return

            # 폴더 스캔 실행
            try:
                self.logger.info(f"폴더 스캔 시작: {self.SELECTED_PATH}")

                # SLDDRW 파일 카운트
                from pathlib import Path

                unique_paths = set()
                try:
                    root_path = Path(self.SELECTED_PATH)
                    for file_path in root_path.rglob("*"):
                        if file_path.is_file() and file_path.suffix.lower() == ".slddrw":
                            unique_paths.add(str(file_path.resolve()).lower())
                except Exception:
                    pass

                file_count = len(unique_paths)

                if file_count > 0:
                    self.initial_file_count = file_count
                    self.cumulative_processed_count = 0
                    self.is_first_run = True
                    self.last_run_success_count = 0
                    self.progress_bar.config(maximum=self.initial_file_count, value=0)
                    self.progress_label.config(text=f"0/{self.initial_file_count}")
                    self.print_button.config(state="normal")
                    self.logger.info(f"폴더 스캔 완료: {file_count}개 파일")
                else:
                    self.print_button.config(state="disabled")
                    self.progress_label.config(text="파일 없음")
                    messagebox.showinfo("스캔 완료", "작업 대상 파일이 없습니다.")
                    self.scan_toggle_var.set(False)
            except Exception as e:
                self.logger.error(f"폴더 스캔 중 오류: {e}")
                self.print_button.config(state="disabled")
                self.progress_label.config(text="오류")
                messagebox.showerror("스캔 오류", f"폴더 스캔 중 오류가 발생했습니다:\n{e}")
                self.scan_toggle_var.set(False)
        else:
            # 스캔 비활성화 (OFF)
            self.print_button.config(state="disabled")
            self.progress_label.config(text="?/?")
            self.logger.info("폴더 스캔 초기화")

    def on_refresh_credit(self):
        if not self.credit_manager:
            self.logger.error("크레딧 매니저가 초기화되지 않았습니다.")
            messagebox.showerror("오류", "크레딧 매니저가 초기화되지 않았습니다.")
            return
        try:
            trial_credits = self.credit_manager.policy.get("trial_credits", 0)
            popup_messages = []
            credentials_updated = False

            # 1. 구매 이력 동기화 - 팝업에 표시
            if trial_credits != -1:
                result = self.credit_manager.pull_and_apply_purchases()

                if result.get("success"):
                    added = result.get("added", 0)
                    applied_ids = result.get("applied_ids", [])

                    if added > 0:
                        msg = f"✅ {len(applied_ids)}건의 구매 이력을 반영했습니다."
                        msg += f"\n추가된 크레딧: {added:,}개"
                        popup_messages.append(msg)
                    else:
                        popup_messages.append("신규 구매 이력이 없습니다.")
                else:
                    popup_messages.append(f"⚠️ 크레딧 갱신 실패: {result.get('message')}")

            # 2. 앱 정책 및 관리자 설정 동기화 (백그라운드)
            try:
                from wf_settings_common import sync_policies_from_sheets  # type: ignore
                policy_result = sync_policies_from_sheets("conversion_verifier", self.logger)
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

            # 결과 표시
            final_message = "\n".join(popup_messages)
            if credentials_updated:
                final_message += "\n\n🔄 인증 정보가 업데이트되었습니다.\n변경사항 적용을 위해 앱을 재시작해주세요."

            messagebox.showinfo("업데이트 완료", final_message)
            self.update_credit_display()

        except Exception as e:
            self.logger.error(f"업데이트 오류: {e}")
            messagebox.showerror("업데이트 오류", str(e))

    def start_spinner(self):
        """스피너 애니메이션 시작 (스레드 안전)"""

        def _start():
            if not self.spinner_running:
                self.spinner_running = True
                self.spinner_index = 0
                self._animate_spinner()

        try:
            self.master.after(0, _start)
        except Exception:
            _start()

    # =============================
    # 관리자 모드 & 로그 프레임 기능
    # =============================
    def toggle_admin_mode(self):
        """진행률 라벨 클릭으로 관리자 모드 토글"""
        try:
            if not self.is_admin_mode:
                run_mode = getattr(self.config, "run_mode", getattr(self.config, "get", lambda *_: "release")("run_mode", "release"))
                if run_mode == "dev":  # dev 모드에서만 암호 없이 진입
                    self._enter_admin_mode()
                    if self.logger:
                        self.logger.info("관리자 모드 활성화")
                else:
                    from tkinter import simpledialog

                    password = simpledialog.askstring(
                        "관리자 인증", "관리자 비밀번호를 입력하세요:", show="*", parent=self.master
                    )
                    if password is None:
                        return
                    if password == self.admin_password:
                        self._enter_admin_mode()
                        if self.logger:
                            self.logger.info("관리자 모드 활성화")
                    else:
                        messagebox.showerror("인증 실패", "비밀번호가 올바르지 않습니다.")
            else:
                self._exit_admin_mode()
                if self.logger:
                    self.logger.info("관리자 모드 비활성화")
        except Exception as e:
            if self.logger:
                self.logger.error(f"관리자 모드 토글 오류: {e}")

    def _enter_admin_mode(self):
        self.is_admin_mode = True
        self.admin_mode_start_time = datetime.datetime.now()
        self.admin_mode_timer = self.master.after(1800000, self._auto_exit_admin_mode)

        # 창 확장
        current_geometry = self.master.geometry()
        width = current_geometry.split("x")[0]
        pos = current_geometry.split("+", 1)[1] if "+" in current_geometry else "0+0"
        new_geometry = f"{width}x{self.expanded_window_height}+{pos}"
        self.master.geometry(new_geometry)
        self.master.resizable(True, True)
        self.master.title(f"SLDDRW→DWG 변환 검증 {APP_VERSION_FULL} [🔧 관리자 모드]")
        self.progress_bar_label.config(bg="#ffe6e6")
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
        self.is_admin_mode = False
        self.admin_mode_start_time = None
        if self.admin_mode_timer:
            self.master.after_cancel(self.admin_mode_timer)
            self.admin_mode_timer = None
        self.destroy_log_frame()
        current_geometry = self.master.geometry()
        width = current_geometry.split("x")[0]
        pos = current_geometry.split("+", 1)[1] if "+" in current_geometry else "0+0"
        new_geometry = f"{width}x{self.original_window_height}+{pos}"
        self.master.geometry(new_geometry)
        self.master.resizable(False, False)
        self.master.title(f"변환 확인 도구 {APP_VERSION_DISPLAY}")
        self.progress_bar_label.config(bg=self.master.cget("bg"))

        # 프로그레스 초기화
        self.progress_bar["value"] = 0
        self.progress_bar.config(maximum=100)
        self.progress_label.config(text="0/0")
        self.spinner_label.config(text="○", fg="#cccccc")

    def _auto_exit_admin_mode(self):
        """30분 후 자동 관리자 모드 종료"""
        self._exit_admin_mode()
        self._show_toast("관리자 모드 자동 해제", 1500)
        self.update_credit_display()

    def create_log_frame(self):
        if self.log_frame:
            return
        main_frame = None
        for child in self.master.winfo_children():
            if isinstance(child, tk.Frame):
                main_frame = child
                break
        if not main_frame:
            return
        self.log_frame = tk.Frame(main_frame)
        self.log_frame.pack(fill="both", expand=True, pady=(10, 0))
        header = tk.Frame(self.log_frame)
        header.pack(fill="x", pady=(0, 5))
        tk.Label(
            header,
            text="실시간 로그 (DEBUG)",
            font=("맑은 고딕", self.ui["font_size_bold"], "bold"),
        ).pack(side="left")
        try:
            _auto = bool(self.config.get_ui_config().get("auto_scroll", True))
        except Exception:
            _auto = True
        self.auto_scroll_var = tk.BooleanVar(value=_auto)
        self.auto_scroll_checkbox = tk.Checkbutton(
            header,
            text="자동 스크롤",
            variable=self.auto_scroll_var,
            font=("맑은 고딕", self.ui["font_size"]),
        )
        self.auto_scroll_checkbox.pack(side="right")
        text_frame = tk.Frame(self.log_frame)
        text_frame.pack(fill="both", expand=True)
        self.log_scrollbar = tk.Scrollbar(text_frame)
        self.log_scrollbar.pack(side="right", fill="y")
        self.log_text = tk.Text(
            text_frame,
            wrap="word",
            yscrollcommand=self.log_scrollbar.set,
            font=("Consolas", self.ui["font_size"]),
            bg="#f8f8f8",
            fg="#333333",
            height=10,
            state="disabled",
        )
        self.log_text.pack(side="left", fill="both", expand=True)
        self.log_scrollbar.config(command=self.log_text.yview)

        # 테스트 데이터 버튼들
        test_btn_frame = tk.Frame(self.log_frame)
        test_btn_frame.pack(fill="x", pady=(6, 0))
        tk.Button(
            test_btn_frame,
            text="테스트 데이터 생성",
            command=self.create_test_data,
            width=18,
            bg="#e8f5e9",
        ).pack(side="left", padx=5)
        tk.Button(
            test_btn_frame,
            text="테스트 데이터 삭제",
            command=self.delete_test_data,
            width=18,
            bg="#ffebee",
        ).pack(side="left", padx=5)

        self.setup_log_handler()

    def destroy_log_frame(self):
        if self.log_frame:
            self.remove_log_handler()
            self.log_frame.destroy()
            self.log_frame = None
            self.log_text = None
            self.log_scrollbar = None
            self.auto_scroll_var = None
            self.auto_scroll_checkbox = None

    def setup_log_handler(self):
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
                    self.master.after(0, lambda: self._append(msg))
                except Exception:
                    pass

            def _append(self, msg):
                if self.text_widget and self.text_widget.winfo_exists():
                    self.text_widget.config(state="normal")
                    self.text_widget.insert("end", msg + "\n")
                    lines = int(self.text_widget.index("end-1c").split(".")[0])
                    if lines > 1200:
                        self.text_widget.delete("1.0", "200.0")
                    if self.auto_scroll_var and self.auto_scroll_var.get():
                        self.text_widget.see("end")
                    self.text_widget.config(state="disabled")

        self.text_log_handler = TextHandler(self.log_text, self.auto_scroll_var, self.master)
        fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
        self.text_log_handler.setFormatter(fmt)
        self.text_log_handler.setLevel(logging.DEBUG)
        if self.logger:
            self.logger.addHandler(self.text_log_handler)

    def remove_log_handler(self):
        if self.text_log_handler and self.logger:
            self.logger.removeHandler(self.text_log_handler)
            self.text_log_handler = None

    # =============================
    # 테스트 데이터 생성 / 삭제
    # =============================
    def create_test_data(self):
        try:
            from pathlib import Path
            import shutil
            from datetime import datetime

            # 테스트 데이터는 앱 상위 폴더에 생성 (50.data/test)
            base = Path(__file__).parent / "test"
            if base.exists():
                try:
                    shutil.rmtree(base)
                except Exception:
                    pass
            base.mkdir(parents=True, exist_ok=True)

            # 50개의 도면 이름 생성
            names = [
                "Drawing001",
                "Assembly_Main",
                "Part_Detail",
                "Section_View",
                "Exploded_View",
                "Front_Panel",
                "Side_View",
                "Top_View",
                "Bottom_Plate",
                "Cover_Assembly",
                "Motor_Mount",
                "Bearing_Housing",
                "Shaft_Detail",
                "Gear_Assembly",
                "Frame_Structure",
                "Base_Plate",
                "Support_Bracket",
                "Drive_Shaft",
                "Connector_Housing",
                "End_Cap",
                "Bracket_001",
                "Spacer_002",
                "Pin_003",
                "Washer_004",
                "Spring_005",
                "Coupling_006",
                "Flange_007",
                "Bushing_008",
                "Retainer_009",
                "Clip_010",
                "Gasket_011",
                "Seal_012",
                "Shim_013",
                "Stud_014",
                "Nut_015",
                "Bolt_016",
                "Screw_017",
                "Rivet_018",
                "Insert_019",
                "Anchor_020",
                "Hinge_021",
                "Latch_022",
                "Handle_023",
                "Knob_024",
                "Lever_025",
                "Rod_026",
                "Tube_027",
                "Pipe_028",
                "Fitting_029",
                "Adapter_030",
            ]

            # 1. SLDDRW 20개 생성
            for i, name in enumerate(names[:20]):
                p = base / f"{name}_{i+1:03d}.slddrw"
                p.write_text(
                    f"# SOLIDWORKS Drawing File - {name}\n# Created: {datetime.now()}\n",
                    encoding="utf-8",
                )

            # 2. DWG 16개 생성 (변환 성공 케이스) - 처음 16개에 대응
            for i, name in enumerate(names[:16]):
                p = base / f"{name}_{i+1:03d}.dwg"
                p.write_text(
                    f"# AutoCAD Drawing File - {name}\n# Converted: {datetime.now()}\n",
                    encoding="utf-8",
                )

            # 3. 나머지 4개는 SLDDRW만 있고 DWG 없음 (변환 실패 케이스)
            # names[16:20]은 이미 SLDDRW만 생성되어 있음

            # UI 연결: 선택 경로를 ./test 로 설정 및 파일 카운트 후 버튼 활성화
            self.set_selected_path(str(base))

            # SLDDRW 카운트 및 좌측 버튼 활성화
            try:
                unique_paths = set()
                root_path = Path(self.SELECTED_PATH)
                for file_path in root_path.rglob("*"):
                    if file_path.is_file() and file_path.suffix.lower() == ".slddrw":
                        unique_paths.add(str(file_path.resolve()).lower())
                file_count = len(unique_paths)
                if file_count > 0:
                    self.initial_file_count = file_count
                    self.cumulative_processed_count = 0
                    self.is_first_run = True
                    self.last_run_success_count = 0
                    self.progress_bar.config(maximum=self.initial_file_count, value=0)
                    self.progress_label.config(text=f"0/{self.initial_file_count}")
                    self.print_button.config(state="normal")
                else:
                    self.print_button.config(state="disabled")
                    self.progress_label.config(text="파일 없음")
            except Exception:
                pass

            messagebox.showinfo(
                "완료",
                f"테스트 데이터가 생성되었습니다!\n경로: {base}\n\nSLDDRW: 20개\nDWG: 16개 (변환 성공)\n변환 실패: 4개",
                parent=self.master,
            )
            if self.logger:
                self.logger.info(f"테스트 데이터 생성 완료: {base} (SLDDRW: 20, DWG: 16, 실패: 4)")
        except Exception as e:
            messagebox.showerror(
                "오류", f"테스트 데이터 생성 중 오류 발생:\n{e}", parent=self.master
            )
            if self.logger:
                self.logger.error(f"테스트 데이터 생성 실패: {e}")

    def delete_test_data(self):
        try:
            from pathlib import Path
            import shutil
            import os, stat

            # 생성 경로와 동일하게 앱 상위 폴더의 test를 대상으로 삭제 (50.data/test)
            target = Path(__file__).parent / "test"
            if not target.exists():
                messagebox.showinfo("알림", "삭제할 테스트 데이터가 없습니다.")
                return

            # Windows에서 읽기 전용 파일로 인해 삭제 실패하는 경우 대비
            def _onerror(func, path, exc_info):
                try:
                    os.chmod(path, stat.S_IWRITE)
                    func(path)
                except Exception:
                    pass

            shutil.rmtree(target, onerror=_onerror)
            # 선택 경로가 test였다면 UI 초기화
            try:
                if (self.SELECTED_PATH or "").strip().lower() == str(target).lower():
                    self.set_selected_path(None)
            except Exception:
                pass
            messagebox.showinfo("완료", "테스트 데이터가 삭제되었습니다.")
            if self.logger:
                self.logger.info("테스트 데이터 삭제 완료")
        except Exception as e:
            messagebox.showerror("오류", f"삭제 중 오류 발생:\n{e}")
            if self.logger:
                self.logger.error(f"테스트 데이터 삭제 실패: {e}")
                self.spinner_index = 0
                self._animate_spinner()

        # (불필요한 미정의 콜백 제거)

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
            # 현재 스피너 문자 표시 (회전하는 원형)
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

                # 진행바와 라벨은 '현재 처리 수/총 수'로 단순 표기 (누적 미포함)
                self.last_run_success_count = current
                shown = min(max(int(current), 0), int(self.initial_file_count or 0))
                self.progress_bar["value"] = shown
                label_text = f"{shown}/{self.initial_file_count}"

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
        self.SELECTED_PATH = selected_path if selected_path else None

        if not self.SELECTED_PATH:
            self.folder_entry.config(state="normal")
            self.folder_entry.delete(0, tk.END)
            self.folder_entry.config(state="readonly")
            return

        self.folder_entry.config(state="normal")
        self.folder_entry.delete(0, tk.END)
        self.folder_entry.insert(0, self.SELECTED_PATH)
        self.folder_entry.config(state="readonly")

        # 선택된 폴더 저장
        try:
            self.config.update_ui_last_folder(self.SELECTED_PATH)
        except Exception as e:
            self.logger.warning(f"폴더 경로 저장 실패(무시): {e}")

        # 폴더 선택 시 자동 스캔: 스캔 토글을 임시 비활성화하고 실행
        try:
            if hasattr(self, "scan_toggle_btn"):
                self.scan_toggle_btn.config(state="disabled")
            self.scan_toggle_var.set(True)
            self.on_scan_toggle()
        finally:
            if hasattr(self, "scan_toggle_btn"):
                self.scan_toggle_btn.config(state="normal")

        # 여기서 실제 변환 확인 로직을 위한 automation 객체 생성
        # self.automation = ConversionAutomation(folder_path=self.SELECTED_PATH, console_mode=False)
        # self.automation.set_progress_callback(self.update_progress_ui)
        # self.automation.set_credit_update_callback(self.update_credit_display)
        # self.automation.set_file_processing_start_callback(self.start_spinner)
        # self.automation.set_credit_manager(self.credit_manager)

        try:
            # SLDDRW 파일 카운트 (재귀적으로 전체 탐색, 경로 기준 중복 제거)
            unique_paths = set()
            try:
                root_path = Path(self.SELECTED_PATH)
                for file_path in root_path.rglob("*"):
                    if file_path.is_file() and file_path.suffix.lower() == ".slddrw":
                        # Windows는 대소문자 무시이므로 경로를 소문자로 정규화하여 중복 방지
                        unique_paths.add(str(file_path.resolve()).lower())
            except Exception:
                pass

            file_count = len(unique_paths)

            if file_count > 0:
                self.initial_file_count = file_count
                self.cumulative_processed_count = 0
                self.is_first_run = True
                self.last_run_success_count = 0
                self.progress_bar.config(maximum=self.initial_file_count, value=0)
                self.progress_label.config(text=f"0/{self.initial_file_count}")
                self.print_button.config(state="normal")
            else:
                self.print_button.config(state="disabled")
                self.progress_label.config(text="파일 없음")
        except Exception as e:
            self.logger.error(f"폴더 확인 중 오류: {e}")
            self.print_button.config(state="disabled")
            self.progress_label.config(text="오류")

    def verify_hardware_fingerprint(self):
        """하드웨어 핑거프린트 검증"""
        try:
            stored_hardware = self.wf_manager.get_user_info()
            # 새 구조: client_hw_fingerprint, 구 구조: hardware_fingerprint (하위 호환)
            stored_fingerprint = stored_hardware.get(
                "client_hw_fingerprint"
            ) or stored_hardware.get("hardware_fingerprint", "")

            import wf_hwinfo as wf_hwinfo

            current_fingerprint = wf_hwinfo.HardwareInfo().fingerprint

            self.logger.debug(f"기존 지문: {stored_fingerprint}")
            self.logger.debug(f"현재 지문: {current_fingerprint}")
            return stored_fingerprint == current_fingerprint
        except Exception as e:
            self.logger.error(f"하드웨어 검증 실패: {e}")
            return False

    def start_conversion_check(self):
        """변환 확인 시작 (백그라운드 스레드에서 실행)"""
        if not self.SELECTED_PATH:
            return

        self.last_run_success_count = 0

        # 임시로 파일 개수 계산 (실제 automation 구현 시 변경)
        files_to_process_count = self.initial_file_count

        # 크레딧 기반 처리 제한 계산
        processable_limit = files_to_process_count
        skipped_due_to_credit = 0
        if self.credit_manager:
            credit_status = self.credit_manager.get_credit_status()
            remaining_credits = credit_status.get("remaining_credits", 0)
            try:
                cost_per_file = self.credit_manager.get_per_item_cost()
            except Exception:
                cost_per_file = credit_status.get("credit_per_work", 1)

            if remaining_credits != -1:  # -1은 무제한
                needed = files_to_process_count * (cost_per_file if cost_per_file > 0 else 1)
                if remaining_credits < needed:
                    shortage = max(0, needed - remaining_credits)
                    self.logger.error("크레딧 부족으로 실행을 시작할 수 없습니다.")
                    messagebox.showwarning(
                        "크레딧 부족",
                        (
                            "크레딧 부족으로 실행할 수 없습니다.\n\n"
                            f"필요 크레딧: {needed} / 보유 크레딧: {remaining_credits}\n"
                            f"부족 크레딧: {shortage}\n\n"
                            "크레딧을 구매한 후 다시 실행해 주세요."
                        ),
                    )
                    return

        # 제한 정보를 저장하고 진행바를 제한 개수로 설정
        self.original_total_files = files_to_process_count
        self.processable_limit = processable_limit
        self.skipped_due_to_credit = skipped_due_to_credit
        self.initial_file_count = processable_limit
        self.progress_bar.config(maximum=self.initial_file_count, value=0)
        self.progress_label.config(text=f"0/{self.initial_file_count}")

        # 버튼 비활성화
        self.folder_button.config(state="disabled")
        self.print_button.config(state="disabled")
        self.exit_button.config(state="disabled")
        self.settings_button.config(state="disabled")
        self.refresh_credit_button.config(state="disabled")

        # 스피너 시작
        self.start_spinner()

        # 백그라운드 스레드에서 실행
        def worker():
            """백그라운드 작업 스레드"""
            exception_info = {"error": None}
            try:
                import time
                from pathlib import Path

                # SLDDRW 파일 검색 (중복 제거 - 대소문자 무시)
                self.update_progress_ui(0, 100, "SLDDRW 파일 검색 중...")
                slddrw_files_dict = {}  # 중복 제거용 딕셔너리
                folder_path = Path(self.SELECTED_PATH)

                for file_path in folder_path.rglob("*"):
                    if file_path.is_file() and file_path.suffix.lower() == ".slddrw":
                        stat = file_path.stat()
                        # 소문자 키로 중복 제거
                        key = file_path.name.lower()
                        if key not in slddrw_files_dict:
                            slddrw_files_dict[key] = {
                                "name": file_path.name,
                                "path": str(file_path),
                                "size": stat.st_size,
                            }

                slddrw_files = list(slddrw_files_dict.values())
                # 재개 상태 로드: 동일 폴더에서 이미 확인한 파일이면 스킵
                session_path = Path(folder_path) / ".cv_session.json"
                processed_names = set()
                try:
                    if session_path.exists():
                        import json as _json
                        with open(session_path, "r", encoding="utf-8") as _sf:
                            _data = _json.load(_sf)
                            if _data.get("app") == "conversion_verifier" and _data.get("folder") == str(Path(folder_path)):
                                processed_names = set(_data.get("processed", []))
                except Exception:
                    processed_names = set()
                if processed_names:
                    before = len(slddrw_files)
                    slddrw_files = [f for f in slddrw_files if f["name"].lower() not in {n.lower() for n in processed_names}]
                    after = len(slddrw_files)
                    self.logger.info(f"재개 적용: 기존 {before}개 중 {after}개만 처리 (스킵 {before-after}개)")
                # 크레딧 제한에 따라 처리 대상 슬라이스
                if hasattr(self, "processable_limit") and self.processable_limit < len(
                    slddrw_files
                ):
                    slddrw_files = slddrw_files[: self.processable_limit]
                    self.logger.info(
                        f"크레딧 제한 적용: {len(slddrw_files)}/{self.original_total_files} 파일 처리"
                    )

                if not slddrw_files:
                    self.master.after(
                        0, lambda: messagebox.showerror("오류", "SLDDRW 파일을 찾을 수 없습니다.")
                    )
                    return

                # DWG 파일 검색 (중복 제거 - 대소문자 무시)
                self.update_progress_ui(0, 100, "DWG 파일 검색 중...")
                dwg_files_dict = {}  # 중복 제거용 딕셔너리
                for file_path in folder_path.rglob("*"):
                    if file_path.is_file() and file_path.suffix.lower() == ".dwg":
                        stat = file_path.stat()
                        # 소문자 키로 중복 제거
                        key = file_path.name.lower()
                        if key not in dwg_files_dict:
                            dwg_files_dict[key] = {
                                "name": file_path.name,
                                "path": str(file_path),
                                "size": stat.st_size,
                            }

                dwg_files = list(dwg_files_dict.values())

                # 파일 비교 및 매칭
                self.update_progress_ui(0, 100, "파일 비교 중...")
                comparison_data = []

                import json as _json
                for i, slddrw in enumerate(slddrw_files):
                    # 확장자 제거 (대소문자 무시)
                    base_name = slddrw["name"].lower().replace(".slddrw", "")

                    # 매칭되는 DWG 파일 찾기 (대소문자 무시)
                    dwg_match = None
                    for dwg in dwg_files:
                        dwg_base = dwg["name"].lower().replace(".dwg", "")
                        if dwg_base == base_name:
                            dwg_match = dwg
                            break

                    comparison_data.append(
                        {
                            "index": i + 1,
                            "slddrw_file": slddrw["name"],
                            "slddrw_path": slddrw["path"],
                            "dwg_file": dwg_match["name"] if dwg_match else "",
                            "dwg_path": dwg_match["path"] if dwg_match else "",
                            "status": "converted" if dwg_match else "missing",
                            "slddrw_size": slddrw["size"],
                            "dwg_size": dwg_match["size"] if dwg_match else 0,
                        }
                    )

                    # 진행률 업데이트 (처리 한도 기준)
                    self.update_progress_ui(
                        i + 1, len(slddrw_files), f"비교 중... {i+1}/{len(slddrw_files)}"
                    )
                    time.sleep(0.05)  # UI 업데이트 시간

                    # 파일 처리 성공 시 크레딧 차감 (bom2excel 방식)
                    if self.credit_manager:
                        try:
                            credit_result = self.credit_manager.deduct_credits_by_policy(
                                1, f'변환 확인: {slddrw["name"]}'
                            )
                            if credit_result["success"]:
                                self.logger.info(
                                    f"크레딧 차감 완료 - 파일 {i+1}/{len(slddrw_files)}, 남은 크레딧: {credit_result.get('remaining_credits', 0)}"
                                )
                            else:
                                self.logger.error(
                                    f"크레딧 차감 실패: {credit_result.get('message')}"
                                )
                            # UI 크레딧 표시 업데이트
                            self.master.after(0, self.update_credit_display)
                        except Exception as e:
                            self.logger.warning(f"크레딧 차감 중 오류: {e}")

                    # 세션 상태 저장 (성공 처리 기준으로 목록 추가)
                    try:
                        state_obj = {
                            "app": "conversion_verifier",
                            "folder": str(Path(folder_path)),
                            "processed": list(processed_names | {slddrw["name"]}),
                            "last_updated": datetime.datetime.now().isoformat(),
                            "version": "1",
                        }
                        with open(session_path, "w", encoding="utf-8") as _sf:
                            _json.dump(state_obj, _sf, ensure_ascii=False, indent=2)
                        processed_names.add(slddrw["name"])
                    except Exception:
                        pass

                # 결과 저장
                self.comparison_data = comparison_data
                self.last_run_success_count = len(comparison_data)

            except Exception as e:
                exception_info["error"] = e
            finally:
                # 메인 스레드에서 UI 업데이트 (스레드 안전)
                self.master.after(0, lambda: self._on_conversion_complete(exception_info))

        # 스레드 시작
        threading.Thread(target=worker, daemon=True, name="Conversion-Check-Worker").start()

    def _on_conversion_complete(self, exception_info):
        """작업 완료 후 UI 업데이트 (메인 스레드에서 실행)"""
        try:
            # 예외 발생 시 사용자에게 알림
            if exception_info.get("error"):
                error = exception_info["error"]
                messagebox.showerror(
                    "작업 실패", f"변환 확인 중 오류가 발생했습니다:\n\n{str(error)}"
                )

            # 진행 상태 업데이트 (누적 제거, 이번 실행 건수로 고정)
            self.is_first_run = False
            final_count = min(
                max(int(self.last_run_success_count), 0), int(self.initial_file_count or 0)
            )
            self.progress_bar["value"] = final_count
            suffix = "(완료)"
            if getattr(self, "skipped_due_to_credit", 0) > 0:
                # 총 파일 대비 처리된 파일 수를 안내
                suffix = f"(크레딧 제한: 총 {getattr(self,'original_total_files',final_count)} 중 {final_count} 처리)"
            self.progress_label.config(text=f"{final_count}/{self.initial_file_count} {suffix}")
            
            # 크레딧 체크 후 변환확인 버튼 상태 결정
            can_start = False
            if self.credit_manager:
                try:
                    status = self.credit_manager.get_credit_status()
                    remain = status.get("remaining_credits", 0)
                    if remain == -1 or remain > 0:  # 무제한 또는 크레딧 있음
                        can_start = True
                except Exception:
                    pass
            self.print_button.config(state="normal" if can_start else "disabled")

            # 크레딧 표시 업데이트
            self.update_credit_display()

            # 결과 팝업창 표시 (먼저!)
            if self.comparison_data:
                self.show_results_popup()

            # 백그라운드 동기화 (결과 표시 후)
            def background_sync():
                try:
                    if getattr(self, "credit_manager", None):
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
            # 스피너 정지
            self.stop_spinner()

            # 항상 버튼 활성화 (예외 발생 시에도 보장)
            self.folder_button.config(state="normal")
            self.exit_button.config(state="normal")
            self.settings_button.config(state="normal")
            self.refresh_credit_button.config(state="normal")

            self.logger.info("🏁 작업 완료 처리 종료")

    def open_registration_window(self):
        """등록 창 열기 (미등록 사용자용)"""
        # 디렉토리 준비는 설정 로더에서 보장함
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
            import wf_hwinfo as wf_hwinfo

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
        # TrialRegistrationWindow 객체에서 실제 Toplevel 창(trial_win)을 가져와서 모달 처리
        if (
            registration_window_obj
            and hasattr(registration_window_obj, "trial_win")
            and registration_window_obj.trial_win
        ):
            toplevel_window = registration_window_obj.trial_win
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

    def post_registration_update(self):
        """등록 절차 완료 후 UI를 업데이트합니다."""
        self.is_registered_user = self.check_user_registration()
        if self.is_registered_user:
            self.settings_button.config(text="설 정", command=self.open_settings_window)
            self.update_credit_display()  # 크레딧 정보도 갱신

    def open_settings_window(self):
        """설정 창 열기"""
        # 공통 모듈을 통한 사용자 / 하드웨어 정보 수집
        try:
            from wf_settings_common import get_user_hardware_info, format_info_for_tree  # type: ignore

            info = get_user_hardware_info()
            rows = format_info_for_tree(info)
        except Exception:
            rows = {}

        # 설정 창 생성
        settings_window = tk.Toplevel(self.master)
        settings_window.title(f"Conversion Verifier {APP_VERSION_FULL} - 설정")

        # 앱별 아이콘 적용
        try:
            if self.icon_path:
                settings_window.iconbitmap(str(self.icon_path))
        except Exception:
            pass

        # Slightly shorter; content fits comfortably with current sections
        settings_window.geometry("500x500")
        settings_window.wm_attributes("-topmost", 1)
        settings_window.transient(self.master)
        settings_window.grab_set()

        # 메인 프레임
        main_frame = tk.Frame(settings_window, padx=20, pady=20)
        main_frame.pack(fill="both", expand=True)

        # 사용자 및 하드웨어 정보 (통합 TreeView)
        info_frame = tk.LabelFrame(
            main_frame,
            text="사용자 및 하드웨어 정보",
            padx=10,
            pady=10,
            font=("맑은 고딕", self.ui["font_size_bold"]),
        )
        info_frame.pack(fill="x", pady=(0, 10))
        tree = ttk.Treeview(info_frame, columns=("항목", "정보"), show="headings", height=6)
        tree.column("항목", width=130, anchor="w")
        tree.heading("항목", text="항목")
        tree.column("정보", width=320, anchor="w")
        tree.heading("정보", text="정보")
        vsb = ttk.Scrollbar(info_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)
        tree.pack(side="left", fill="x", expand=True)
        vsb.pack(side="right", fill="y")
        for label, value in rows.items():
            if value and str(value).strip():
                tree.insert("", "end", values=(label, value))

        # 설정 섹션 (기존 유지)
        # 설정 섹션 (기존 유지)
        credit_frame = tk.LabelFrame(
            main_frame, text="설정", padx=10, pady=10, font=("맑은 고딕", self.ui["font_size_bold"])
        )
        credit_frame.pack(fill="x", pady=(0, 10))

        # 파일 형식 설정 (한 줄 레이아웃)
        format_frame = tk.Frame(credit_frame)
        format_frame.pack(anchor="w", pady=5)

        tk.Label(format_frame, text="원본 형식:", font=("맑은 고딕", self.ui["font_size"])).pack(
            side="left", padx=(0, 5)
        )
        source_ext_var = tk.StringVar(value="SLDDRW")
        source_ext_entry = tk.Entry(
            format_frame,
            textvariable=source_ext_var,
            width=10,
            font=("맑은 고딕", self.ui["font_size"]),
        )
        source_ext_entry.pack(side="left", padx=(0, 15))

        tk.Label(format_frame, text="⇒  결과 형식:", font=("맑은 고딕", self.ui["font_size"])).pack(
            side="left", padx=(0, 5)
        )
        dest_ext_var = tk.StringVar(value="DWG")
        dest_ext_entry = tk.Entry(
            format_frame,
            textvariable=dest_ext_var,
            width=10,
            font=("맑은 고딕", self.ui["font_size"]),
        )
        dest_ext_entry.pack(side="left")

        # 로그 레벨 설정
        log_level_frame = tk.Frame(credit_frame)
        log_level_frame.pack(anchor="w", pady=5)
        tk.Label(log_level_frame, text="로그 레벨:", font=("맑은 고딕", self.ui["font_size"])).pack(
            side="left", padx=(0, 5)
        )

        # 전역 설정에서 로그 레벨 가져오기
        log_level_default = "DEBUG"
        try:
            from pathlib import Path
            config_file = Path.home() / ".wf_rpa" / "wf_rpa_config.json"
            if config_file.exists():
                with open(config_file, "r", encoding="utf-8") as f:
                    global_config = json.load(f)
                    system_settings = global_config.get("system_settings", {})
                    log_level_default = system_settings.get("log_level", "DEBUG")
        except Exception:
            pass

        log_level_var = tk.StringVar(value=log_level_default)
        log_level_combo = ttk.Combobox(
            log_level_frame,
            textvariable=log_level_var,
            values=["DEBUG", "INFO", "WARNING", "ERROR"],
            state="readonly",
            width=12,
        )
        log_level_combo.pack(side="left")

        # 개별 하드웨어 섹션 제거 (TreeView에 통합됨)
        # 앱 정보 섹션 제거 (설정 영역으로 통합됨)

        # 버튼 프레임 (B2E 패턴: 중앙 정렬)
        button_frame = tk.Frame(main_frame)
        button_frame.pack(side="bottom", pady=(20, 15), fill="x")

        # 버튼을 프레임 중앙에 배치
        button_container = tk.Frame(button_frame)
        button_container.pack(expand=True)

        # 저장 버튼
        save_btn = tk.Button(
            button_container,
            text="저장",
            command=lambda: self._save_cv_settings(settings_window, source_ext_var, dest_ext_var, log_level_var),
            width=12,
            height=2,
            font=("맑은 고딕", self.ui["font_size"]),
        )
        save_btn.pack(side="left", padx=20)

        # 취소 버튼
        cancel_btn = tk.Button(
            button_container,
            text="취소",
            command=settings_window.destroy,
            width=12,
            height=2,
            font=("맑은 고딕", self.ui["font_size"]),
        )
        cancel_btn.pack(side="left", padx=20)

        # 창 중앙 배치
        settings_window.update_idletasks()
        x = self.master.winfo_x() + (self.master.winfo_width() - settings_window.winfo_width()) // 2
        y = (
            self.master.winfo_y()
            + (self.master.winfo_height() - settings_window.winfo_height()) // 2
        )
        settings_window.geometry(f"+{x}+{y}")

    def _save_cv_settings(self, settings_window, source_ext_var, dest_ext_var, log_level_var):
        """CV 설정 저장"""
        try:
            source_ext = source_ext_var.get().strip().upper()
            dest_ext = dest_ext_var.get().strip().upper()
            
            if not source_ext or not dest_ext:
                messagebox.showerror("오류", "원본 형식과 결과 형식을 모두 입력해주세요.", parent=settings_window)
                return
            
            # settings.json에 저장
            settings_path = Path(__file__).parent / "settings.json"
            if settings_path.exists():
                with open(settings_path, "r", encoding="utf-8") as f:
                    settings = json.load(f)
            else:
                settings = {}
            
            # 설정 업데이트
            if "conversion_formats" not in settings:
                settings["conversion_formats"] = {}
            
            settings["conversion_formats"]["source"] = source_ext
            settings["conversion_formats"]["target"] = dest_ext
            
            # 파일에 저장
            with open(settings_path, "w", encoding="utf-8") as f:
                json.dump(settings, f, indent=2, ensure_ascii=False)
            
            # 전역 설정에 로그 레벨 저장
            try:
                config_file = Path.home() / ".wf_rpa" / "wf_rpa_config.json"
                if config_file.exists():
                    with open(config_file, "r", encoding="utf-8") as f:
                        global_config = json.load(f)
                    
                    if "system_settings" not in global_config:
                        global_config["system_settings"] = {}
                    
                    global_config["system_settings"]["log_level"] = log_level_var.get()
                    
                    with open(config_file, "w", encoding="utf-8") as f:
                        json.dump(global_config, f, ensure_ascii=False, indent=2)
                    
                    # 로그 레벨 즉시 적용
                    log_level_str = log_level_var.get()
                    log_level_map = {
                        "DEBUG": logging.DEBUG,
                        "INFO": logging.INFO,
                        "WARNING": logging.WARNING,
                        "ERROR": logging.ERROR,
                    }
                    if log_level_str in log_level_map and hasattr(self, 'logger'):
                        self.logger.setLevel(log_level_map[log_level_str])
                        for handler in self.logger.handlers:
                            handler.setLevel(log_level_map[log_level_str])
                        self.logger.info(f"✅ 로그 레벨 변경: {log_level_str}")
            except Exception as e:
                print(f"⚠️ 로그 레벨 저장 실패: {e}")
            
            messagebox.showinfo("저장 완료", f"설정이 저장되었습니다.\n\n원본: {source_ext}\n결과: {dest_ext}", parent=settings_window)
            settings_window.destroy()
            
        except Exception as e:
            messagebox.showerror("오류", f"설정 저장 실패: {e}", parent=settings_window)

    def show_results_popup(self):
        """결과를 팝업창으로 표시"""
        if not self.comparison_data:
            return

        # 디버그 로깅 (관리자 모드이거나 환경 변수로 활성화)
        def _popup_debug(msg: str):
            try:
                import os, datetime
                admin_mode = getattr(self, 'is_admin_mode', False)
                if admin_mode or os.environ.get("WF_CV_DEBUG_POPUP") == "1":
                    log_dir = os.path.join(os.path.expanduser("~"), ".wf_rpa", "conversion_verifier", "logs")
                    os.makedirs(log_dir, exist_ok=True)
                    with open(os.path.join(log_dir, "ui_popup_debug.log"), "a", encoding="utf-8") as f:
                        f.write(f"{datetime.datetime.now().isoformat()} {msg}\n")
            except Exception:
                pass

        # 통계 계산
        converted = len([x for x in self.comparison_data if x["status"] == "converted"])
        missing = len([x for x in self.comparison_data if x["status"] == "missing"])
        total = len(self.comparison_data)
        rate = (converted / total * 100) if total > 0 else 0
        skipped = getattr(self, "skipped_due_to_credit", 0)

        # 부모 창의 topmost 상태 저장 및 일시 해제
        parent_topmost = False
        try:
            parent_topmost = bool(self.master.attributes("-topmost"))
            if parent_topmost:
                self.master.attributes("-topmost", 0)
                _popup_debug("parent topmost disabled temporarily")
        except Exception as e:
            _popup_debug(f"parent topmost check error: {e}")
        
        # 팝업 창 생성 (항상 보이도록 안전 처리)
        popup = tk.Toplevel(self.master)
        popup.title("📋 변환 결과 상세")
        _popup_debug("popup created")
        
        # 즉시 보이도록 설정
        popup.deiconify()
        _popup_debug("popup deiconified")

        # 먼저 레이아웃 계산 후 중앙 배치
        try:
            self.master.update_idletasks()
        except Exception:
            pass

        # 기본 크기
        width, height = 900, 600
        try:
            # 마스터 기준 중앙 위치 계산 (멀티모니터에서도 안전)
            mx = self.master.winfo_rootx()
            my = self.master.winfo_rooty()
            mw = self.master.winfo_width()
            mh = self.master.winfo_height()
            if mw <= 1 or mh <= 1:
                # 초기 렌더링 전이면 geometry에서 폭/높이를 파싱
                try:
                    g = self.master.geometry()
                    mw = int(g.split("x")[0])
                    mh = int(g.split("x")[1].split("+")[0])
                except Exception:
                    mw, mh = 480, 250
            x = mx + max(0, (mw - width) // 2)
            y = my + max(0, (mh - height) // 2)
        except Exception:
            x, y = 100, 100

        # 1차 배치: 부모 기준 중앙
        popup.geometry(f"{width}x{height}+{x}+{y}")
        _popup_debug(f"geometry set to {width}x{height}+{x}+{y}")

        # 부모와 연계
        popup.transient(self.master)
        
        # 즉시 최상위로 올리고 포커스 설정
        popup.lift()
        popup.focus_force()
        _popup_debug("popup lifted and focused")

        # 메인 프레임
        main_frame = ttk.Frame(popup, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 통계 프레임
        stats_frame = ttk.Frame(main_frame)
        stats_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(
            stats_frame,
            text=f"SLDDRW: {total}개",
            font=("맑은 고딕", self.ui["font_size_bold"], "bold"),
        ).pack(side=tk.LEFT, padx=10)
        ttk.Label(
            stats_frame,
            text=f"변환완료: {converted}개",
            font=("맑은 고딕", self.ui["font_size_bold"], "bold"),
            foreground="green",
        ).pack(side=tk.LEFT, padx=10)
        ttk.Label(
            stats_frame,
            text=f"변환누락: {missing}개",
            font=("맑은 고딕", self.ui["font_size_bold"], "bold"),
            foreground="red",
        ).pack(side=tk.LEFT, padx=10)
        ttk.Label(
            stats_frame,
            text=f"변환율: {rate:.1f}% (처리 대상 {total}개 기준)",
            font=("맑은 고딕", self.ui["font_size_bold"], "bold"),
            foreground="blue",
        ).pack(side=tk.LEFT, padx=10)
        if skipped > 0:
            ttk.Label(
                stats_frame,
                text=f"크레딧 부족으로 미처리: {skipped}개",
                font=("맑은 고딕", self.ui["font_size_bold"], "bold"),
                foreground="orange",
            ).pack(side=tk.LEFT, padx=10)

        # 필터 프레임
        filter_frame = ttk.Frame(main_frame)
        filter_frame.pack(fill=tk.X, pady=(0, 5))

        ttk.Label(filter_frame, text="필터:").pack(side=tk.LEFT, padx=(0, 5))
        filter_var = tk.StringVar(value="all")

        def apply_filter():
            # 기존 데이터 삭제
            for item in results_tree.get_children():
                results_tree.delete(item)

            # 필터에 따라 데이터 선택
            filter_value = filter_var.get()
            if filter_value == "all":
                filtered_data = self.comparison_data
            elif filter_value == "converted":
                filtered_data = [d for d in self.comparison_data if d["status"] == "converted"]
            elif filter_value == "missing":
                filtered_data = [d for d in self.comparison_data if d["status"] == "missing"]
            else:
                filtered_data = self.comparison_data

            # 비동기 배치 처리로 UI 응답성 보장 (UI 블로킹 방지)
            total = len(filtered_data)
            batch_size = 25  # 배포 환경 안전성: 배치 크기 축소
            current_index = [0]  # 리스트로 감싸서 클로저에서 변경 가능하게
            _popup_debug(f"Starting batch processing: {total} items")

            def process_batch():
                """배치 단위로 데이터 삽입 (UI 블로킹 방지)"""
                try:
                    start_idx = current_index[0]
                    end_idx = min(start_idx + batch_size, total)
                    
                    for idx in range(start_idx, end_idx):
                        data = filtered_data[idx]
                        size_text = self.format_file_size(data["slddrw_size"])
                        if data["dwg_size"] > 0:
                            size_text += f" → {self.format_file_size(data['dwg_size'])}"

                        if data["status"] == "missing":
                            tag = "missing"
                            status_display = "⚠️ 변환누락"
                        else:
                            tag = "converted"
                            status_display = "✅ 변환완료"

                        results_tree.insert(
                            "",
                            "end",
                            values=(
                                data["index"],
                                data["slddrw_file"],
                                data["dwg_file"] or "-",
                                status_display,
                                size_text,
                            ),
                            tags=(tag,),
                        )
                    
                    current_index[0] = end_idx
                    
                    # 진행률 로그
                    if end_idx % 100 == 0 or end_idx == total:
                        _popup_debug(f"Batch progress: {end_idx}/{total}")
                    
                    # 아직 처리할 데이터가 남았으면 다음 배치 스케줄링
                    if end_idx < total:
                        popup.after(10, process_batch)  # 10ms 후 다음 배치 (UI 응답성 보장)
                    else:
                        # 모든 데이터 로딩 완료
                        try:
                            popup.update_idletasks()
                            _popup_debug(f"All {total} items loaded successfully")
                        except Exception as e:
                            _popup_debug(f"Final update error: {e}")
                except Exception as e:
                    _popup_debug(f"Batch processing error: {e}")
                    # 오류 발생 시에도 계속 진행
                    if current_index[0] < total:
                        popup.after(20, process_batch)
            
            # 첫 배치 처리 시작
            if total > 0:
                process_batch()
            else:
                _popup_debug("No data to display")

        ttk.Radiobutton(
            filter_frame, text="전체", variable=filter_var, value="all", command=apply_filter
        ).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(
            filter_frame,
            text="✅ 변환완료",
            variable=filter_var,
            value="converted",
            command=apply_filter,
        ).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(
            filter_frame,
            text="⚠️ 변환누락",
            variable=filter_var,
            value="missing",
            command=apply_filter,
        ).pack(side=tk.LEFT, padx=5)

        # 트리뷰 (테이블)
        table_frame = ttk.Frame(main_frame)
        table_frame.pack(fill=tk.BOTH, expand=True)

        columns = ("번호", "SLDDRW파일", "DWG파일", "상태", "크기")
        results_tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=20)

        # 컬럼 설정
        results_tree.heading("번호", text="번호")
        results_tree.heading("SLDDRW파일", text="SLDDRW 파일")
        results_tree.heading("DWG파일", text="DWG 파일")
        results_tree.heading("상태", text="상태")
        results_tree.heading("크기", text="크기")

        results_tree.column("번호", width=50, anchor=tk.CENTER)
        results_tree.column("SLDDRW파일", width=250, anchor=tk.W)
        results_tree.column("DWG파일", width=250, anchor=tk.W)
        results_tree.column("상태", width=100, anchor=tk.CENTER)
        results_tree.column("크기", width=150, anchor=tk.E)

        # 스크롤바
        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=results_tree.yview)
        results_tree.configure(yscrollcommand=scrollbar.set)

        results_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 태그 스타일 설정
        results_tree.tag_configure("converted", background="#e8f5e8", foreground="#2e7d32")
        results_tree.tag_configure("missing", background="#ffebee", foreground="#c62828")

        # 닫기 버튼
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        def close_popup():
            """Restore parent topmost and close popup"""
            try:
                if parent_topmost:
                    self.master.attributes("-topmost", 1)
                    _popup_debug("parent topmost restored")
            except Exception as e:
                _popup_debug(f"parent topmost restore error: {e}")
            popup.destroy()
        
        # X 버튼 클릭 시에도 close_popup 호출
        popup.protocol("WM_DELETE_WINDOW", close_popup)
        
        ttk.Button(button_frame, text="닫기", command=close_popup, width=15).pack(side=tk.RIGHT)

        # 팝업 UI 먼저 업데이트하여 화면에 표시
        try:
            popup.update_idletasks()
        except Exception:
            pass

        # 화면 밖 배치 방지 및 보이기 보정 로직 (멀티 모니터 고려)
        def _ensure_visible(attempt=0):
            try:
                popup.update_idletasks()
                # 현재 좌표/크기
                g = popup.geometry()
                wh, xy = g.split("+", 1)
                w, h = map(int, wh.split("x"))
                x0, y0 = map(int, xy.split("+"))
                
                # 멀티 모니터 환경 고려: 메인 창 위치 기준으로 유효성 검증
                # screenwidth/screenheight는 주 모니터만 반환하므로 사용 안 함
                # 대신 메인 창 근처에 있으면 유효한 것으로 간주
                try:
                    mx = self.master.winfo_rootx()
                    my = self.master.winfo_rooty()
                    # 메인 창으로부터 너무 멀리 떨어져 있는지만 체크 (5000픽셀 이상)
                    dx = abs(x0 - mx)
                    dy = abs(y0 - my)
                    too_far = (dx > 5000) or (dy > 5000)
                    
                    if too_far:
                        # 메인 창 중앙으로 재배치
                        mw = self.master.winfo_width()
                        mh = self.master.winfo_height()
                        if mw <= 1 or mh <= 1:
                            try:
                                g = self.master.geometry()
                                mw = int(g.split("x")[0])
                                mh = int(g.split("x")[1].split("+")[0])
                            except Exception:
                                mw, mh = 480, 250
                        nx = mx + max(0, (mw - w) // 2)
                        ny = my + max(0, (mh - h) // 2)
                        popup.geometry(f"{w}x{h}+{nx}+{ny}")
                        _popup_debug(f"repositioned to master center {w}x{h}+{nx}+{ny}")
                        popup.deiconify(); popup.lift(); popup.focus_force()
                except Exception as e:
                    _popup_debug(f"position check error: {e}")
                
                # 가끔 포커스가 안 잡히는 환경에 대비하여 재시도
                if attempt < 3:
                    popup.after(150, lambda: _ensure_visible(attempt + 1))
            except Exception as e:
                _popup_debug(f"ensure_visible error: {e}")

        # 데이터 로딩 및 창 표시를 다음 이벤트 루프에서 실행
        def load_data_and_show():
            try:
                _popup_debug("Starting load_data_and_show")
                
                # 데이터 표시 (비동기 배치 처리 시작)
                apply_filter()
                _popup_debug("apply_filter called (batch processing started)")
                
                # 모달 동작 설정 (데이터 로딩 시작 후)
                try:
                    popup.grab_set()
                    _popup_debug("grab_set applied for modal behavior")
                except Exception as e:
                    _popup_debug(f"grab_set error: {e}")
                
                # 위치 확인
                popup.after(200, lambda: _ensure_visible(0))
            except Exception as e:
                self.logger.warning(f"팝업 데이터 로딩 중 경고(무시): {e}")
                _popup_debug(f"data load warning: {e}")
        
        # UI 렌더링 후 데이터 로딩 시작
        popup.after(50, load_data_and_show)

    def format_file_size(self, bytes_size):
        """파일 크기 포맷팅"""
        for unit in ["B", "KB", "MB", "GB"]:
            if bytes_size < 1024.0:
                return f"{bytes_size:.1f}{unit}"
            bytes_size /= 1024.0
        return f"{bytes_size:.1f}TB"


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

        result = manager.sync_local_registration_to_sheets("conversion_verifier", app_version)

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

    # 테스트 모드에서는 single instance 및 cross-app 체크 건너뛰기
    if not test_mode:
        # 단일 인스턴스 체크 (동일 앱) - 조용히 종료
        is_first, handle = _acquire_single_instance()
        if not is_first:
            try:
                print("Another conversion_verifier instance is already running. Exiting.")
            except Exception:
                pass
            return

        # 교차 앱 실행 방지 (공통 헬퍼 사용)
        if check_cross_app_running_and_exit:
            check_cross_app_running_and_exit("conversion_verifier")

        global _instance_mutex_handle
        _instance_mutex_handle = handle
    else:
        _log_startup("Test mode: skipping single instance and cross-app checks")

    # Mark running for cross-app guard and ensure cleanup on exit
    try:
        _set_cross_app_running("conversion_verifier")
        import atexit as _atexit

        _atexit.register(_clear_cross_app_running)
    except Exception:
        pass

    _log_startup("Creating Tk root")
    root = tk.Tk()
    # 시작 시 플래시 방지: 초기화 전 잠시 숨김
    try:
        root.withdraw()
    except Exception:
        pass
    
    # 작업표시줄 아이콘 설정 (개발/릴리스 환경 모두 지원)
    try:
        # 아이콘 파일명 (새 아이콘: 04_Conversion_Verifier.ico, 기존: CV.ico)
        icon_names = ["04_Conversion_Verifier.ico", "CV.ico"]

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
    
    # Run mode 결정 및 res 시드 (release에서 사용자 홈으로 복사, 없으면 스킵)
    try:
        try:
            cfg = get_config()
            run_mode = getattr(cfg, "run_mode", "release")
        except Exception:
            cfg, run_mode = None, "release"
        target_res = (
            Path(__file__).parent / "res"
            if run_mode in ("dev", "demo")
            else Path.home() / ".wf_rpa" / "conversion_verifier" / "res"
        )
        bundle_candidates = [Path(__file__).parent / "res"]
        if getattr(sys, "frozen", False):
            exe_dir = Path(sys.executable).parent
            bundle_candidates = [exe_dir / "res", exe_dir / "_internal" / "res"] + bundle_candidates
        seed_res_if_missing(target_res, bundle_candidates, logger=None)
    except Exception:
        pass

    _log_startup("Creating ConversionVerifierApp")
    app = ConversionVerifierApp(root)

    # WF-ACT 테스트 모드 초기화
    if test_mode:
        try:
            app.init_test_server()
        except Exception as e:
            print(f"[WF-ACT] Failed to initialize test server: {e}")

    _log_startup("Starting mainloop")
    # 초기화가 끝난 후 창 표시 및 포커스
    try:
        root.deiconify(); root.lift(); root.focus_force()
    except Exception:
        pass
    _flush_startup_log()
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
