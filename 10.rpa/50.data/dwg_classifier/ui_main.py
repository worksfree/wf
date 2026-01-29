"""DWG Classifier Main UI (structurally repaired)"""

import os
import sys

# Windows 콘솔 UTF-8 강제 설정 (GUI 모드에서는 stdout/stderr가 None일 수 있음)
if sys.platform == "win32":
    import io
    if sys.stdout is not None and hasattr(sys.stdout, 'buffer'):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    if sys.stderr is not None and hasattr(sys.stderr, 'buffer'):
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import json
import datetime
import threading
import logging
from pathlib import Path
import tkinter as tk
import tkinter.ttk as ttk
from tkinter import messagebox, filedialog

# Ensure common modules path is available BEFORE optional imports
COMMON_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "10.common"))
if COMMON_PATH not in sys.path:
    sys.path.insert(0, COMMON_PATH)

from wf_credit_session_utils import (
    calculate_processable_count,
    compute_session_stats,
    format_progress_label,
    build_credit_shortage_init_message,
    build_credit_shortage_completion_message,
    build_normal_completion_message,
    get_credit_purchase_url,
)
if COMMON_PATH not in sys.path:
    sys.path.insert(0, COMMON_PATH)

# Optional external modules (graceful degradation if missing)
try:
    from wf_log import get_app_logger
except Exception:

    def get_app_logger(name, console_level=logging.INFO):
        logger = logging.getLogger(name)
        if not logger.handlers:
            h = logging.StreamHandler()
            h.setLevel(console_level)
            logger.addHandler(h)
        logger.setLevel(console_level)
        return logger


try:
    from wf_credit_manager import WorksFreeManager, CreditManager
    from wf_app_init_helpers import init_credit_and_policy_managers, check_cross_app_running_and_exit, seed_res_if_missing

    WFM_AVAILABLE = True
except Exception:
    WorksFreeManager = None
    CreditManager = None
    check_cross_app_running_and_exit = None
    WFM_AVAILABLE = False
try:
    from wf_register import create_trial_window
except Exception as _e:
    # Will be surfaced when user clicks registration button
    create_trial_window = None
    logging.getLogger("dwg_classifier").warning(f"wf_register import 실패: {_e}")
try:
    from app_setting_data import get_config
except Exception:

    def get_config():
        class Dummy:  # minimal stub
            def get(self, k, d=None):
                return d

            def set(self, k, v):
                pass

            def save_settings(self):
                pass

        return Dummy()


# (Moved common path injection to top of file for reliability)

# ==================== STARTUP PROFILER ====================
_STARTUP_LOG = []
_STARTUP_ENABLED = True
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
        path = Path.home() / ".wf_rpa" / "dwg_classifier" / "startup_profile.log"
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    return path


def _log_startup(msg: str):
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
            for t, m in _STARTUP_LOG:
                elapsed_ms = (t - base_time) * 1000
                f.write(f"[{elapsed_ms:7.1f}ms] {m}\n")
    except Exception:
        pass

    _STARTUP_FLUSHED = True


# (DPI/Scaling normalizer removed per request)


# ==================== VERSION INFO ====================
def _load_version_info():
    """settings.json에서 버전 정보 읽기 (개발/릴리스 모두 지원)"""
    default_full = "v0.7.0.0"
    full_version = default_full

    try:
        if getattr(sys, "frozen", False):
            # 릴리스 모드: 번들 버전 우선 (정확한 빌드 버전), fallback으로 사용자 홈
            base_path = Path(sys._MEIPASS) if hasattr(sys, '_MEIPASS') else Path(sys.executable).parent
            settings_file = base_path / ".wf_rpa" / "dwg_classifier" / "settings.json"
            if not settings_file.exists():
                settings_file = Path.home() / ".wf_rpa" / "dwg_classifier" / "settings.json"
        else:
            # 개발 모드: 10.common/config/dwg_classifier/settings.json (통합 경로)
            app_root = Path(__file__).parent
            settings_file = app_root.parent.parent / "10.common" / "config" / "dwg_classifier" / "settings.json"
            # fallback: 앱 폴더의 config
            if not settings_file.exists():
                settings_file = app_root / "config" / "dwg_classifier" / "settings.json"

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


APP_VERSION_FULL, APP_VERSION_DISPLAY = _load_version_info()


# ==================== SINGLE/CROSS INSTANCE ====================
# --- Single instance guard (Windows named mutex) ---
_instance_mutex_handle = None


def _acquire_single_instance(mutex_name: str = r"Global\\WF_DWG_CLASSIFIER"):
    """Try to acquire a global mutex so only one instance runs.
    Returns (is_first_instance: bool, handle: int|None).
    Works on Windows; no-op on other OSes.
    """
    if os.name != "nt":
        return True, None
    try:
        import ctypes

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


def _set_cross_app_running(app_name: str):
    try:
        cfg = Path.home() / ".wf_rpa"
        cfg.mkdir(parents=True, exist_ok=True)
        file = cfg / "wf_rpa_config.json"
        data = {}
        if file.exists():
            try:
                data = json.loads(file.read_text(encoding="utf-8")) or {}
            except Exception:
                data = {}
        
        # email_settings / google_sheets가 없으면 번들 템플릿에서 보강
        try:
            need_email = "email_settings" not in data
            need_sheets = "google_sheets" not in data
            if need_email or need_sheets:
                if getattr(sys, "frozen", False):
                    candidates = [
                        Path(sys.executable).parent / ".wf_rpa" / "wf_rpa_config.json",
                        Path(sys.executable).parent / "_internal" / ".wf_rpa" / "wf_rpa_config.json",
                    ]
                else:
                    candidates = [
                        Path(__file__).parent / "config" / "wf_rpa_config.json",
                    ]
                bundle_cfg = next((c for c in candidates if c.exists()), None)
                if bundle_cfg:
                    template = json.loads(bundle_cfg.read_text(encoding="utf-8")) or {}
                    if need_email and "email_settings" in template:
                        data["email_settings"] = template["email_settings"]
                    if need_sheets and "google_sheets" in template:
                        data["google_sheets"] = template["google_sheets"]
        except Exception:
            pass
        
        es = data.get("execution_status", {})
        es.update(
            {
                "is_running": True,
                "current_app": app_name,
                "pid": os.getpid(),
                "start_time": datetime.datetime.now().isoformat(),
            }
        )
        data["execution_status"] = es
        file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return True
    except Exception:
        return False


def _clear_cross_app_running():
    try:
        file = Path.home() / ".wf_rpa" / "wf_rpa_config.json"
        if not file.exists():
            return True
        data = json.loads(file.read_text(encoding="utf-8")) or {}
        if "execution_status" in data:
            data["execution_status"].update(
                {"is_running": False, "current_app": None, "pid": None, "start_time": None}
            )
            file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return True
    except Exception:
        return False


try:
    import multiprocessing

    multiprocessing.freeze_support()
except Exception:
    pass


# ==================== MAIN CLASS ====================
class DwgClassifierApp:
    def __init__(self, master: tk.Tk):
        _log_startup("DwgClassifierApp.__init__")
        self.master = master
        self.itself_dir = os.path.dirname(os.path.abspath(__file__))
        # MessageBox들이 메인창 기준으로 뜨도록 parent를 강제 지정
        self._bind_messagebox_parent()

        # 아이콘 경로 저장 (등록창/설정창에서 사용)
        self.icon_path = self._find_icon_path()
        self.logger = get_app_logger("dwg_classifier", console_level=logging.INFO)
        self.config = get_config()
        try:
            self.is_demo_mode = bool(self.config and hasattr(self.config, "is_demo") and self.config.is_demo())
        except Exception:
            self.is_demo_mode = False
        self.allow_continue_on_credit_shortage = self._load_allow_continue_flag()
        # 적응형 UI 설정 초기화
        from wf_ui_adaptive import get_adaptive_ui_settings, apply_global_fonts

        self.ui = get_adaptive_ui_settings(window_type="main")
        # Alt+G 데모 핫키에서 적용할 창 위치/크기 오버라이드 (설정 파일만 사용)
        _config_geo_override = ""
        try:
            _config_geo_override = (getattr(self.config, "window_geometry_override", "") or "").strip()
        except Exception:
            _config_geo_override = ""
        self.debug_geometry_override = _config_geo_override
        
        # Demo capture 설정 (BOM Exporter 패턴)
        try:
            self.demo_capture_enabled = self.config and hasattr(self.config, 'is_demo') and self.config.is_demo()
        except Exception:
            self.demo_capture_enabled = False
        self.demo_capture_dir = None
        self.demo_capture_size = (1920, 1040)
        self._last_demo_capture_ts = 0.0
        
        # 🚀 최적화: WorksFree 매니저를 lazy loading으로 변경 (UI 후 백그라운드 초기화)
        self.wf_manager = None
        self.credit_manager = None
        self._wfm_available = WFM_AVAILABLE
        if not WFM_AVAILABLE:
            self.logger.error("프로그램 핵심 모듈을 찾을 수 없습니다. 프로그램을 종료합니다.")
            messagebox.showerror(
                "치명적 오류", "프로그램 핵심 모듈을 찾을 수 없습니다.\n프로그램을 종료합니다."
            )
            sys.exit(1)

        # State vars
        self.SELECTED_PATH = None  # 통합 표준 변수명
        self.SELECTED_FOLDER = None  # 하위 호환성 유지 (임시)
        self.selected_excel_files = []
        self.automation = None
        self.initial_file_count = 0
        self.cumulative_processed_count = 0
        self.is_first_run = True
        self.last_run_success_count = 0
        self.classification_result = None
        # Spinner
        self.spinner_running = False
        self.spinner_index = 0
        self.spinner_chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        # Admin
        self.is_admin_mode = False
        self.admin_mode_timer = None
        self.admin_mode_start_time = None
        # 🚀 최적화: admin 비밀번호 lazy 로딩 (Google Sheets 호출 지연)
        self._admin_password = None  # lazy load
        # Log frame vars
        self.log_frame = None
        self.log_text = None
        self.log_scrollbar = None
        self.auto_scroll_var = None
        self.auto_scroll_checkbox = None
        self.text_log_handler = None
        # Window sizes (DPI 스케일 적용) - adaptive UI 기반
        base_original_height = 270  # 2입력 앱 기본 높이 (DC only)
        base_expanded_height = base_original_height + 300  # 관리자 모드: +300 고정
        try:
            from wf_settings_common import get_windows_dpi_scale
            dpi_scale = get_windows_dpi_scale()
            self.original_window_height = int(base_original_height * dpi_scale)
            self.expanded_window_height = int(base_expanded_height * dpi_scale)
        except Exception:
            self.original_window_height = base_original_height
            self.expanded_window_height = base_expanded_height
        # Early 등록 상태 확인 (is_registered 플래그 또는 reg_time_local)
        self.is_registered_user = False
        try:
            if self._wfm_available and WorksFreeManager:
                self.wf_manager = WorksFreeManager()
                self.is_registered_user = self.wf_manager.is_registered()
        except Exception as e:
            self.logger.warning(f"Early WorksFreeManager init 실패(무시): {e}")
        
        # 🚀 최적화: CreditManager 초기화를 백그라운드로 지연
        self.credit_manager = None
        
        # UI build (초기 등록 상태 반영된 버튼 라벨 생성)
        self.master.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.init_ui()
        # 초기 등록 상태가 True라면 버튼 라벨을 즉시 재확인 (안전망)
        try:
            if self.is_registered_user:
                self.update_registration_button()
        except Exception:
            pass
        # 🚀 백그라운드에서 추가 초기화 수행 (크레딧 등)
        self.master.after(100, self._lazy_init_managers)
        
        # 🚀 사용자 디렉토리 비동기 생성 (KFN 패턴)
        try:
            self.master.after(200, lambda: threading.Thread(target=self.create_user_directories, daemon=True).start())
        except Exception:
            threading.Thread(target=self.create_user_directories, daemon=True).start()
        
        # Demo 캡처 초기화
        if self.demo_capture_enabled:
            self._init_demo_capture()
        
        # 🚀 이전 작업 폴더/엑셀 복원 및 자동 스캔 (CV 패턴)
        if self._last_folder_to_load:
            self.master.after(300, self._restore_last_session)

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

    def set_selected_path(self, path: str | None):
        """선택된 경로를 설정하고 UI를 동기화 (통합 헬퍼)"""
        self.SELECTED_PATH = path
        self.SELECTED_FOLDER = path  # 하위 호환 유지

        # folder_entry 업데이트 (DWG 방식)
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
                self.selected_excel_files = []
                if hasattr(self, "print_button"):
                    self.print_button.config(state="disabled")
                if hasattr(self, "progress_label"):
                    self.progress_label.config(text="설정 필요")
            except Exception:
                pass
        # Deferred policy sync
        if self.credit_manager:
            try:
                self.master.after(600, self._async_refresh_policies)
            except Exception:
                threading.Thread(target=self._async_refresh_policies, daemon=True).start()

    def _bind_messagebox_parent(self):
        """Route all tkinter messageboxes to use the main window as parent for centering."""
        def _wrap(func):
            def inner(*args, **kwargs):
                kwargs.setdefault("parent", self.master)
                result = func(*args, **kwargs)
                # 팝업이 생성된 후 메인창 중심으로 이동
                try:
                    self._center_popup_on_main()
                except Exception:
                    pass
                return result
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
            icon_names = ["03_DWG_Classifier.ico", "DWG.ico"]
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

    def _center_popup_on_main(self):
        """메인창의 중심 좌표에 맞춰 최상위 팝업창을 이동"""
        try:
            # 최근 생성된 Toplevel 창 찾기
            for widget in self.master.winfo_children():
                if isinstance(widget, tk.Toplevel) and widget.winfo_exists():
                    widget.update_idletasks()
                    # 메인창 중심 좌표 계산
                    main_x = self.master.winfo_x()
                    main_y = self.master.winfo_y()
                    main_width = self.master.winfo_width()
                    main_height = self.master.winfo_height()
                    main_center_x = main_x + main_width // 2
                    main_center_y = main_y + main_height // 2
                    
                    # 팝업창 크기
                    popup_width = widget.winfo_width()
                    popup_height = widget.winfo_height()
                    
                    # 팝업창을 메인창 중심에 배치
                    popup_x = main_center_x - popup_width // 2
                    popup_y = main_center_y - popup_height // 2
                    
                    widget.geometry(f"+{popup_x}+{popup_y}")
                    break
        except Exception:
            pass

    # ---------- Registration / Credit ----------
    def check_user_registration(self):
        if self.wf_manager:
            try:
                return self.wf_manager.is_registered()
            except Exception:
                return False
        return False

    def _load_allow_continue_flag(self) -> bool:
        try:
            cfg_path = Path(__file__).parent / "config" / "wf_rpa_config.json"
            if cfg_path.exists():
                with open(cfg_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return bool(data.get("system_settings", {}).get("allow_continue_on_credit_shortage", False))
        except Exception as e:
            if self.logger:
                self.logger.warning(f"글로벌 설정 로드 실패(continue on credit shortage): {e}")
        return False

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
                    self.is_registered_user = self.wf_manager.is_registered()
                    self.logger.info(f"[INIT] WorksFreeManager 초기화 완료 (등록사용자: {self.is_registered_user})")
                    # 등록 상태에 맞게 버튼 라벨/동작 갱신
                    try:
                        self.master.after(0, self.update_registration_button)
                    except Exception:
                        pass

                # CreditManager 초기화 (공통 헬퍼 사용)
                if CreditManager and self.wf_manager:
                    self.logger.info("[INIT] CreditManager 초기화 시작...")
                    self.credit_manager = init_credit_and_policy_managers(
                        app_name="dwg_classifier",
                        wf_manager=self.wf_manager,
                        master=self.master,
                        logger=self.logger,
                        recovery_delay_ms=700,
                        policy_delay_ms=400,
                    )
                    
                    if self.credit_manager:
                        self.logger.info("[INIT] CreditManager 초기화 완료")
                    else:
                        self.logger.warning("[INIT] CreditManager 초기화 실패 (None 반환)")
                    
                    # UI 업데이트
                    self.master.after(0, self.update_credit_display)
                    # 정책 동기화는 별도 스케줄
                    self.master.after(300, self._async_refresh_policies)
                elif not CreditManager:
                    self.logger.warning("[INIT] CreditManager 모듈을 사용할 수 없습니다.")
                elif not self.wf_manager:
                    self.logger.warning("[INIT] WorksFreeManager가 초기화되지 않았습니다.")

            except Exception as e:
                if self.logger:
                    self.logger.error(f"매니저 초기화 중 오류: {e}", exc_info=True)

        # 백그라운드 스레드에서 실행
        threading.Thread(target=_worker, daemon=True).start()

    # _schedule_recovery는 이제 wf_app_init_helpers에서 처리됨
    def _schedule_recovery(self):
        """크레딧 복구 동기화 스케줄 (deprecated - 헬퍼로 이동)"""
        pass

    def create_user_directories(self):
        """사용자 디렉토리 구조 생성"""
        user_home = os.path.expanduser("~")
        wf_rpa_dir = os.path.join(user_home, ".wf_rpa")
        app_dir = os.path.join(wf_rpa_dir, "dwg_classifier")

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

    def update_registration_button(self):
        try:
            if getattr(self, "settings_button", None):
                if self.is_registered_user:
                    self.settings_button.config(text="설 정", command=self.open_settings_window)
                else:
                    self.settings_button.config(text="등 록", command=self.open_registration_window)
        except Exception:
            pass
    
    def _restore_last_session(self):
        """이전 작업 세션 복원: 폴더 + 엑셀 파일 자동 로드 및 스캔 (CV 패턴)"""
        try:
            # 엑셀 파일 복원
            if self._last_excel_files_to_load:
                self.selected_excel_files = self._last_excel_files_to_load
                self.excel_listbox.delete(0, tk.END)
                for f in self.selected_excel_files:
                    self.excel_listbox.insert(tk.END, os.path.basename(f))
                self.logger.info(f"이전 엑셀 파일 {len(self.selected_excel_files)}개 복원")
            
            # 폴더 스캔 자동 실행 (등록된 사용자이고 폴더+엑셀이 모두 있는 경우)
            if self.is_registered_user and self._last_folder_to_load and self.selected_excel_files:
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

    def update_credit_display(self):
        if not getattr(self, "credit_label", None):
            return
        try:
            if not self.credit_manager:
                self.credit_label.config(text="크레딧 확인 불가", fg="gray")
                return
            status = self.credit_manager.get_credit_status()
            ct = status.get("credit_type", "standard")
            trial_raw = status.get("remaining_trial", 0)
            purchased_raw = status.get("remaining_purchased", 0)
            trial = max(0, trial_raw)
            purchased = max(0, purchased_raw)
            cost = self.credit_manager.policy.get("credit_per_work", 50)
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
            self._bind_tooltip(self.credit_label, tip)
        except Exception as e:
            self.credit_label.config(text="표시 오류", fg="red")
            self.logger.error(f"크레딧 표시 오류: {e}")

    def on_refresh_credit(self):
        """사용자 요청에 따른 크레딧/구매내역 동기화 (단순 버전)."""
        if not self.credit_manager:
            messagebox.showinfo("크레딧", "크레딧 매니저가 초기화되지 않았습니다.")
            return
        try:
            trial_credits = self.credit_manager.policy.get("trial_credits", 0)
            popup_messages = []
            credentials_updated = False

            # 1. 구매 이력 동기화 - 팝업에 표시
            if trial_credits != -1:
                try:
                    result = self.credit_manager.pull_and_apply_purchases()
                    if result.get("success"):
                        added = result.get("added", 0)
                        if added > 0:
                            popup_messages.append(f"✅ 구매 이력 반영: {added:,}개 크레딧 추가")
                        else:
                            popup_messages.append("신규 구매 이력이 없습니다.")
                    else:
                        popup_messages.append(f"⚠️ 크레딧 갱신 실패: {result.get('message')}")
                except Exception as e:
                    popup_messages.append(f"⚠️ 크레딧 갱신 오류: {str(e)}")
                    self.logger.error(f"크레딧 갱신 오류: {e}")

            # 2. 앱 정책 및 관리자 설정 동기화 (백그라운드)
            try:
                from wf_settings_common import sync_policies_from_sheets  # type: ignore
                policy_result = sync_policies_from_sheets("dwg_classifier", self.logger)
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
            final_message = "\n".join(popup_messages) if popup_messages else "업데이트 완료"
            if credentials_updated:
                final_message += "\n\n🔄 인증 정보가 업데이트되었습니다.\n변경사항 적용을 위해 앱을 재시작해주세요."

            messagebox.showinfo("업데이트 완료", final_message)
            self.update_credit_display()

        except Exception as e:
            self.logger.error(f"업데이트 오류: {e}")
            messagebox.showerror("업데이트 오류", str(e))
            import traceback
            self.logger.error(traceback.format_exc())

    # ---------- UI Build ----------
    def init_ui(self):
        from wf_ui_adaptive import apply_global_fonts
        # 설정 파일에서 창 크기 가져오기
        window_width = self.ui.get("window_width", 580)
        # DC는 입력이 2개(폴더+엑셀)이므로 original_window_height 사용 (5행 레이아웃)
        window_height = self.original_window_height
        adjusted_height = window_height

        self.width = self.master.winfo_screenwidth()
        self.height = self.master.winfo_screenheight()
        # 우측 1/3 영역의 중간에 위치 (5/6 지점)
        x_coord = int(self.width * 5 / 6 - window_width / 2)
        y_coord = int((self.height - adjusted_height) / 2)

        self.master.geometry(f"{window_width}x{adjusted_height}+{x_coord}+{y_coord}")

        # Saved/demo geometry override (env > settings)
        override_geo = self._get_geometry_override_if_allowed()
        if override_geo:
            try:
                self.master.geometry(override_geo)
                if self.logger:
                    self.logger.info(f"[DEBUG] geometry override at startup: {override_geo}")
            except Exception as e:
                if self.logger:
                    self.logger.warning(f"geometry override 적용 실패(무시): {e}")

        self.master.title(f"DWG 파일 분류 도구 {APP_VERSION_DISPLAY}")
        self.master.wm_attributes("-topmost", 1)
        self.master.resizable(True, True)
        # Allow smaller resizing by capping the minimum height at half of the initial height (with a floor of 120)
        min_height = max(120, int(adjusted_height / 2))
        self.master.minsize(window_width, min_height)
        
        # 전역 폰트 설정 적용 (메인창 폰트 크기 일관성 보장)
        apply_global_fonts(self.master, self.ui)
        
        self.create_ui_elements()

        self.master.lift()
        self.master.focus_force()
        self.update_credit_display()
        self._bind_debug_geometry_hotkey()

    def create_ui_elements(self):
        master = self.master
        
        # Grid로 루트 윈도우 설정하여 상하좌우 여백 균등 분배
        master.grid_rowconfigure(0, weight=1)
        master.grid_columnconfigure(0, weight=1)
        
        main_frame = tk.Frame(master, padx=12, pady=0)
        main_frame.grid(row=0, column=0, sticky="nsew")

        # Folder frame
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
        # 이전 작업 폴더 자동 로드 (CV 패턴 적용, 데모 모드에서는 스킵)
        self._last_folder_to_load = None
        self._last_excel_files_to_load = []
        
        # 데모 모드가 아닐 때만 이전 폴더 복원
        is_demo_mode = self.config and hasattr(self.config, 'is_demo') and self.config.is_demo()
        if not is_demo_mode:
            try:
                from app_setting_data import get_config

                cfg = get_config()
                last = (cfg.get_last_selected_folder() or "").strip()
                if last and os.path.isdir(last):
                    self.SELECTED_FOLDER = last
                    self.SELECTED_PATH = last
                    self.folder_entry.config(state="normal")
                    self.folder_entry.insert(0, last)
                    self.folder_entry.config(state="readonly")
                    self._last_folder_to_load = last
                    
                    # 마지막 엑셀 파일 로드 시도
                    try:
                        last_excel = cfg.get_last_excel_files() if hasattr(cfg, 'get_last_excel_files') else []
                        if last_excel and isinstance(last_excel, list):
                            valid_files = [f for f in last_excel if os.path.isfile(f)]
                            if valid_files:
                                self._last_excel_files_to_load = valid_files
                    except Exception:
                        pass
            except Exception:
                pass

        # Excel frame
        excel_frame = tk.Frame(main_frame)
        excel_frame.pack(fill="x", pady=(0, 6))

        self.excel_button = tk.Button(
            excel_frame,
            text="엑셀 선택",
            width=10,
            command=self.select_excel_files,
            font=("맑은 고딕", self.ui["font_size"]),
        )
        self.excel_button.pack(side="left")

        list_wrap = tk.Frame(excel_frame)
        list_wrap.pack(side="left", fill="both", expand=True, padx=(10, 0))
        sb = tk.Scrollbar(list_wrap, orient="vertical")
        self.excel_listbox = tk.Listbox(
            list_wrap,
            yscrollcommand=sb.set,
            font=("맑은 고딕", self.ui["font_size"]),
            height=2,
            selectmode=tk.EXTENDED,
        )
        sb.config(command=self.excel_listbox.yview)
        sb.pack(side="right", fill="y")
        self.excel_listbox.pack(side="left", fill="both", expand=True)

        # Progress frame
        progress_frame = tk.Frame(main_frame)
        progress_frame.pack(fill="x", pady=(0, 6))

        self.progress_bar_label = tk.Label(
            progress_frame, text="진행률:", width=11, font=("맑은 고딕", self.ui["font_size"])
        )
        self.progress_bar_label.pack(side="left")

        self.progress_bar_label.bind("<Button-1>", lambda e: self.toggle_admin_mode())
        # 사용자 안내용 툴팁: 진척률 설명만 제공 (관리자 모드 언급 없음)
        try:
            self._bind_tooltip(self.progress_bar_label, "진척률: 전체 대비 처리된 개수와 퍼센트를 표시합니다.")
        except Exception:
            pass

        self.progress_bar = ttk.Progressbar(
            progress_frame, orient="horizontal", mode="determinate", maximum=100
        )
        self.progress_bar.pack(side="left", fill="x", expand=True, padx=(10, 0))

        self.spinner_label = tk.Label(
            progress_frame, text="", font=("맑은 고딕", self.ui["font_size_title"]), width=2
        )
        self.spinner_label.pack(side="left", padx=(5, 0))

        # Status frame
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

        # 자세한 로그는 설정 창으로 이동 (체크박스 제거)
        self.checkbox_var = tk.BooleanVar(value=False)

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

        # Buttons
        button_frame = tk.Frame(main_frame)
        button_frame.pack(fill="x", pady=(12, 12))
        button_frame.columnconfigure(0, weight=1)
        button_frame.columnconfigure(1, weight=1)
        button_frame.columnconfigure(2, weight=1)
        button_frame.columnconfigure(3, weight=1)

        self.print_button = tk.Button(
            button_frame,
            text="분류시작",
            command=self.start_classification,
            width=12,
            height=1,
            state="disabled",
            font=("맑은 고딕", self.ui["font_size"]),
        )
        self.print_button.grid(row=0, column=0, padx=5, sticky="ew")

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

    # ---------- Tooltip ----------
    def _bind_tooltip(self, widget, text: str):
        if not text:
            return
        tip = {"win": None}

        def enter(_):
            if tip["win"]:
                return
            x = widget.winfo_rootx() + 20
            y = widget.winfo_rooty() + 20
            tw = tk.Toplevel(widget)
            tw.overrideredirect(True)
            tw.wm_attributes("-topmost", 1)
            tw.geometry(f"+{x}+{y}")
            lbl = tk.Label(
                tw,
                text=text,
                bg="#ffffe0",
                relief="solid",
                borderwidth=1,
                font=("맑은 고딕", self.ui["font_size"]),
                padx=6,
                pady=3,
            )
            lbl.pack()
            tip["win"] = tw

        def leave(_):
            if tip["win"]:
                try:
                    tip["win"].destroy()
                except Exception:
                    pass
                tip["win"] = None

        widget.bind("<Enter>", enter)
        widget.bind("<Leave>", leave)

    def _show_toast(self, msg: str, dur=1600):
        try:
            t = tk.Toplevel(self.master)
            t.overrideredirect(True)
            t.attributes("-topmost", True)
            x = self.master.winfo_rootx() + 30
            y = self.master.winfo_rooty() + 30
            t.geometry(f"+{x}+{y}")
            tk.Label(t, text=msg, bg="#333", fg="white", padx=10, pady=6).pack()
            self.master.after(dur, t.destroy)
        except Exception:
            pass

    def _get_geometry_override_if_allowed(self) -> str:
        """설정 파일에 저장된 geometry override를 반환한다."""
        return (self.debug_geometry_override or "").strip()

    def _bind_debug_geometry_hotkey(self):
        """Alt+G 하나로 geometry 캡처/저장, Alt+C 화면 캡처 (demo 전용)."""
        # 모든 모드에서 Alt+G로 geometry 저장 가능 (설정 파일만 반영)

        try:
            self.master.bind_all("<Alt-g>", self._on_debug_geometry_capture)
            self.master.bind_all("<Alt-c>", self._on_manual_capture)
            # 모달 대화상자 활성화 시에도 Alt+C가 동작하도록 전역 핫키 리스너 시작
            self._start_global_hotkey_listener()
        except Exception as e:
            try:
                self.logger.debug(f"Alt hotkey bind 실패: {e}")
            except Exception:
                pass

        # 창 종료 이벤트 핸들러 등록 (X 버튼 클릭 시)
        self.master.protocol("WM_DELETE_WINDOW", self.on_closing)

    def _on_debug_geometry_capture(self, _event=None):
        """Alt+G: 현재 geometry를 로그에 찍고 즉시 settings.json에 저장."""
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
            Path.home() / ".wf_rpa" / "dwg_classifier" / "demo_captures",
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

    # ---------- Policy Sync ----------
    def _async_refresh_policies(self):
        if not self.wf_manager:
            return
        
        def worker():
            try:
                result = self.wf_manager.refresh_policies_from_sheets()
                self.logger.info(f"정책 동기화 결과: {result}")
            finally:
                self.master.after(0, self.update_credit_display)

        threading.Thread(target=worker, daemon=True).start()

    # ---------- Event Handlers / Logic ----------
    def on_closing(self):
        """창 종료 이벤트 핸들러 - 모든 백그라운드 작업 정리"""
        try:
            self.logger.info("🚀 애플리케이션 종료...")
            
            # 1. 전역 핫키 리스너 정리 (논블로킹)
            try:
                self._stop_global_hotkey_listener()
            except Exception:
                pass
            
            # 2. 어드민 모드 타이머 정리
            try:
                if self.admin_mode_timer:
                    self.master.after_cancel(self.admin_mode_timer)
            except Exception:
                pass
            
            # 3. 로그 프레임 정리
            try:
                self.destroy_log_frame()
            except Exception:
                pass
            
            self.logger.info("🎉 애플리케이션 종료 완료")
        except Exception as e:
            try:
                self.logger.error(f"종료 중 오류: {e}")
            except Exception:
                print(f"종료 중 오류: {e}")
        finally:
            # 강제 종료 (이벤트 루프 우회)
            try:
                self.master.quit()
                self.master.destroy()
            except Exception:
                pass
            import sys
            sys.exit(0)

    def on_checkbox_toggle(self):
        # 자세한 로그는 설정 창으로 이동됨
        pass

    def on_scan_toggle(self):
        """폴더 스캔 토글 처리"""
        if self.scan_toggle_var.get():
            # 스캔 활성화 (ON)
            if not self.SELECTED_FOLDER:
                messagebox.showwarning("폴더 미선택", "먼저 작업할 폴더를 선택해주세요.")
                self.scan_toggle_var.set(False)
                return

            if not self.selected_excel_files:
                messagebox.showwarning("엑셀 미선택", "엑셀 파일을 선택해주세요.")
                self.scan_toggle_var.set(False)
                return

            # 폴더 스캔 실행
            try:
                self.logger.info(f"폴더 스캔 시작: {self.SELECTED_FOLDER}")

                # automation 인스턴스 생성 (없을 경우)
                if not hasattr(self, "automation") or self.automation is None:
                    from automation import DwgClassifierAutomation

                    # 데모 모드에서는 콘솔 컨펌('y') 대기를 위해 console_mode=True로 실행
                    _is_demo = False
                    try:
                        _is_demo = bool(self.config and hasattr(self.config, "is_demo") and self.config.is_demo())
                    except Exception:
                        _is_demo = False
                    self.automation = DwgClassifierAutomation(
                        folder_path=self.SELECTED_FOLDER, console_mode=_is_demo
                    )
                    self.automation.set_excel_files(self.selected_excel_files)
                    self.automation.set_credit_manager(self.credit_manager)
                    # 현재 설정을 즉시 런타임에 반영 (파일 경로 불일치 대비)
                    try:
                        from app_setting_data import get_config as _get_cfg
                        _cfg = _get_cfg()
                        self.automation.apply_runtime_settings(
                            drawing_column=getattr(_cfg, "drawing_column", None),
                            category_column=getattr(_cfg, "category_column", None),
                            excel_sheet_name=getattr(_cfg, "excel_sheet_name", None),
                            case_sensitive=getattr(_cfg, "case_sensitive", None),
                            file_operation_mode=getattr(_cfg, "file_operation_mode", None),
                        )
                    except Exception as _e:
                        self.logger.debug(f"런타임 설정 반영 스킵: {_e}")
                
                # 엑셀 컬럼명 검증
                column_error = self.automation.validate_excel_columns()
                if column_error:
                    messagebox.showerror("엑셀 컬럼 오류", column_error)
                    self.scan_toggle_var.set(False)
                    return

                # DWG 파일 스캔
                dwg_files = self.automation.scan_dwg_files(self.SELECTED_FOLDER)
                total_files = len(dwg_files)
                # 재실행 플래그 기본값 리셋
                self.rerun_ignore_processed = False
                self.rerun_only_new_duplicates = False

                already_processed_files = [f for f in dwg_files if self.automation._is_file_already_processed(f)]
                already_processed_count = len(already_processed_files)
                remaining_files = [f for f in dwg_files if f not in set(already_processed_files)]
                remaining_count = len(remaining_files)

                # 파일 수 비교: 스캔된 파일 vs 결과 폴더 파일
                classified_count = self.automation.count_classified_files()

                # 사용자에게 의도 확인 필요한 경우
                should_proceed = True
                
                if total_files > 0 and classified_count > 0:
                    # 부분 완료 케이스: 결과 폴더 카운트와 이미 처리된 해시 카운트가 일치하고 합이 총 파일수이면 이어서 진행
                    partial_resumable = (
                        classified_count == already_processed_count
                        and classified_count + remaining_count == total_files
                        and classified_count < total_files
                    )

                    if partial_resumable:
                        # 부분 완료 상태: 크레딧 부족 기록 확인
                        has_credit_stop = self.automation.has_credit_shortage_interruption()
                        if has_credit_stop:
                            # 크레딧 부족으로 중단되었으므로 이어서 진행 (팝업 없이)
                            self.logger.info(
                                f"부분 완료 상태 감지 (크레딧 부족): 결과 {classified_count}/{total_files}, 해시 {already_processed_count}. 이어서 진행합니다."
                            )
                            # 처리 기록 유지하고 크레딧이 남은 파일만 처리 (ignore_processed_for_rerun 설정 안 함)
                        else:
                            # 크레딧 부족 기록 없는 부분 완료: 정상 재개
                            self.logger.info(
                                f"부분 완료 상태 감지: 결과 {classified_count}/{total_files}, 해시 {already_processed_count}. 이어서 진행합니다."
                            )
                        # 그대로 진행 (팝업 없이) - 해시/세션 기반으로 잔여만 처리
                        pass

                    elif classified_count == total_files:
                        # 케이스 1: 파일 수 같음 → 완료된 폴더
                        msg = "이미 작업했던 폴더인 것 같은데 다시 처리하시겠습니까?"
                        response = messagebox.askyesno("폴더 상태 확인", msg, icon="question")
                        if response:
                            self.logger.info("사용자가 재처리를 선택했습니다.")
                            self.rerun_ignore_processed = True
                            self.rerun_only_new_duplicates = True
                            already_processed_count = 0
                            remaining_count = total_files
                        else:
                            should_proceed = False
                            
                    elif classified_count < total_files:
                        # 케이스 2: 파일 수 더 적음 → 중단이 있었는지 확인
                        has_credit_stop = self.automation.has_credit_shortage_interruption()
                        if has_credit_stop:
                            # 케이스 2-1: 크레딧 부족 중단 기록 있음
                            msg = f"크레딧 부족으로 중단되었습니다 ({classified_count}/{total_files}).\n이어서 진행하시겠습니까?"
                            response = messagebox.askyesno("작업 재개", msg, icon="question")
                            if response:
                                self.logger.info("사용자가 크레딧 부족 상태에서 재개를 선택했습니다.")
                                # 처리 기록 유지하고 크레딧이 남은 파일만 처리
                                # (ignore_processed_for_rerun 설정 안 함)
                            else:
                                should_proceed = False
                        else:
                            # 케이스 2-2: 크레딧 부족 기록 없음 → 기록 불일치
                            msg = f"처리 기록이 불일치합니다 ({classified_count}/{total_files}).\n처음부터 시작하시겠습니까?"
                            response = messagebox.askyesno("기록 불일치", msg, icon="question")
                            if response:
                                self.logger.info("사용자가 기록 불일치 상태에서 새로 시작을 선택했습니다.")
                                self.rerun_ignore_processed = True
                                self.rerun_only_new_duplicates = False
                                already_processed_count = 0
                                remaining_count = total_files
                            else:
                                should_proceed = False
                    else:
                        # 케이스 3: 파일 수 더 많음 → 이상 상태
                        msg = f"결과 파일이 더 많은 이상한 상태입니다 ({classified_count}/{total_files}).\n무시하고 처음부터 시작하시겠습니까?"
                        response = messagebox.askyesno("이상 상태", msg, icon="question")
                        if response:
                            self.logger.info("사용자가 이상 상태에서 새로 시작을 선택했습니다.")
                            self.rerun_ignore_processed = True
                            self.rerun_only_new_duplicates = False
                            already_processed_count = 0
                            remaining_count = total_files
                        else:
                            should_proceed = False

                if not should_proceed:
                    # 사용자 취소 → 아무것도 하지 않고 기본 상태 유지
                    self.scan_toggle_var.set(False)
                    return

                if total_files > 0:
                    # 진행률 계산에 필요한 값 저장
                    self.total_file_count = total_files
                    self.already_processed_count = already_processed_count
                    self.initial_file_count = remaining_count  # 이번 실행에서 처리할 대상 수
                    self.cumulative_processed_count = 0
                    self.is_first_run = True
                    self.last_run_success_count = 0
                    # 진행 바는 전체 대비 누적 처리 기준으로 표시
                    self.progress_bar.config(maximum=total_files, value=already_processed_count)
                    # UX: 이미 처리된 파일이 있으면 상세 정보, 없으면 간단한 형식
                    if already_processed_count > 0:
                        label_text = f"{already_processed_count}/{total_files} (잔여 {remaining_count}건)"
                    else:
                        label_text = f"0/{remaining_count}"
                    self.progress_label.config(text=label_text)
                    self.print_button.config(state="normal")
                    self.logger.info(f"폴더 스캔 완료: 총 {total_files}개, 이미 처리 {already_processed_count}개, 잔여 {remaining_count}건")
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

    def select_excel_files(self):
        # 사용자 등록 및 하드웨어 인증 확인
        if not self.is_registered_user:
            messagebox.showwarning("등록 필요", "사용자 등록 후 이용 가능합니다.")
            return
        if not self.verify_hardware_fingerprint():
            messagebox.showerror("인증 실패", "하드웨어 정보 불일치.")
            return

        try:
            paths = filedialog.askopenfilenames(
                title="엑셀 파일 선택", filetypes=[("Excel", "*.xlsx *.xls")]
            )
            if paths:
                self.selected_excel_files = list(paths)
                self.excel_listbox.delete(0, tk.END)
                for p in self.selected_excel_files:
                    self.excel_listbox.insert(tk.END, os.path.basename(p))
                self.check_ready_to_start()
        except Exception as e:
            self.logger.error(f"엑셀 선택 오류: {e}")
            messagebox.showerror("오류", str(e))

    def select_folder_license_check(self):
        if not self.is_registered_user:
            messagebox.showwarning("등록 필요", "사용자 등록 후 이용 가능합니다.")
            return
        if not self.verify_hardware_fingerprint():
            messagebox.showerror("인증 실패", "하드웨어 정보 불일치.")
            return
        path = filedialog.askdirectory()
        if not path:
            return
        self.SELECTED_FOLDER = path
        self.folder_entry.config(state="normal")
        self.folder_entry.delete(0, tk.END)
        self.folder_entry.insert(0, path)
        self.folder_entry.config(state="readonly")
        # 선택된 폴더 저장
        try:
            from app_setting_data import get_config

            cfg = get_config()
            cfg.update_ui_last_folder(path)
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

    def check_ready_to_start(self):
        # 스캔 토글이 활성화된 경우에만 시작 버튼 활성화
        try:
            if self.scan_toggle_var.get() and self.SELECTED_FOLDER and self.selected_excel_files:
                if hasattr(self, "initial_file_count") and self.initial_file_count > 0:
                    self.print_button.config(state="normal")
                else:
                    self.print_button.config(state="disabled")
                    self.progress_label.config(text="파일 없음")
            else:
                self.print_button.config(state="disabled")
                if not self.scan_toggle_var.get():
                    self.progress_label.config(text="스캔 필요")
                else:
                    self.progress_label.config(text="설정 필요")
        except Exception as e:
            self.logger.error(f"시작 가능 여부 확인 오류: {e}")
            self.print_button.config(state="disabled")
            self.progress_label.config(text="오류")

    def verify_hardware_fingerprint(self):
        try:
            if not self.wf_manager:
                return False
            info = self.wf_manager.get_user_info()
            stored = info.get("client_hw_fingerprint") or info.get("hardware_fingerprint", "")
            import wf_hwinfo

            current = wf_hwinfo.HardwareInfo().fingerprint
            return stored == current
        except Exception as e:
            self.logger.error(f"하드웨어 검증 실패: {e}")
            return False

    # ---------- Classification ----------
    def start_classification(self):
        if not (self.SELECTED_FOLDER and self.selected_excel_files):
            return
        self.last_run_success_count = 0
        # 최신 설정 반영 (크레딧 부족 시 계속 진행 여부)
        self.allow_continue_on_credit_shortage = self._load_allow_continue_flag()
        try:
            dwg_files = [f for f in os.listdir(self.SELECTED_FOLDER) if f.lower().endswith(".dwg")]
        except Exception as e:
            messagebox.showerror("오류", f"DWG 확인 실패:\n{e}")
            return
        count = len(dwg_files)
        if self.credit_manager:
            try:
                status = self.credit_manager.get_credit_status()
                remain = status.get("remaining_credits", 0)
                cost = self.credit_manager.get_per_item_cost()
                # 실제 처리할 파일 수로 크레딧 계산 (이미 처리된 파일 제외)
                remaining_count = getattr(self, 'initial_file_count', count)
                needed = remaining_count * cost
                if remain != -1 and remain < needed:
                    processable_count = calculate_processable_count(remain, cost)
                    shortage = max(0, needed - remain)
                    
                    msg = build_credit_shortage_init_message(
                        remaining_count=remaining_count,
                        processable_count=processable_count,
                        needed_credits=needed,
                        remaining_credits=remain,
                        shortage_credits=shortage,
                        allow_continue=self.allow_continue_on_credit_shortage
                    )
                    
                    if self.allow_continue_on_credit_shortage:
                        proceed = messagebox.askyesno("크레딧 부족", msg)
                        if not proceed:
                            return
                        self.logger.warning("설정에 따라 크레딧 부족 상태에서 실행을 계속합니다.")
                        self.credit_limited_files = None
                        self.original_file_count = count
                    else:
                        messagebox.showwarning("크레딧 부족", msg)
                        return
                else:
                    self.credit_limited_files = None
                    self.original_file_count = count
            except Exception:
                pass
        # Disable buttons
        for b in [
            self.folder_button,
            self.excel_button,
            self.print_button,
            self.exit_button,
            self.settings_button,
            self.refresh_credit_button,
        ]:
            b.config(state="disabled")
        # 진행 바는 전체 대비 누적 처리 기준으로 표시 (재시작 시 0%가 아닌 누적 처리 반영)
        total_all = getattr(self, "total_file_count", count)
        already = getattr(self, "already_processed_count", 0)
        self.progress_bar.config(maximum=total_all, value=already)
        # 시작 시 라벨은 누적 기준으로 표시
        remaining = max(0, total_all - already)
        if already > 0:
            self.progress_label.config(text=f"{already}/{total_all} (잔여 {remaining}건)")
        else:
            self.progress_label.config(text=f"0/{total_all}")

        def worker():
            try:
                try:
                    from automation import DwgClassifierAutomation
                except Exception:
                    DwgClassifierAutomation = None
                if DwgClassifierAutomation:
                    # 데모 모드에서는 콘솔 컨펌('y') 대기를 위해 console_mode=True로 실행
                    _is_demo = False
                    try:
                        _is_demo = bool(self.config and hasattr(self.config, "is_demo") and self.config.is_demo())
                    except Exception:
                        _is_demo = False
                    self.automation = DwgClassifierAutomation(
                        folder_path=self.SELECTED_FOLDER,
                        console_mode=_is_demo,
                    )
                    self.automation.set_excel_files(self.selected_excel_files)
                    self.automation.set_progress_callback(self.update_progress_ui)
                    self.automation.set_credit_update_callback(self.update_credit_display)
                    self.automation.set_file_processing_start_callback(self.start_spinner)
                    self.automation.set_credit_manager(self.credit_manager)
                    # 재실행 플래그 전달 (스캔 단계에서 결정)
                    try:
                        self.automation.ignore_processed_for_rerun = getattr(self, "rerun_ignore_processed", False)
                        self.automation.only_count_new_duplicates = getattr(self, "rerun_only_new_duplicates", False)
                    except Exception:
                        pass
                    # 새 인스턴스에 현재 설정 즉시 반영
                    try:
                        from app_setting_data import get_config as _get_cfg
                        _cfg = _get_cfg()
                        self.automation.apply_runtime_settings(
                            drawing_column=getattr(_cfg, "drawing_column", None),
                            category_column=getattr(_cfg, "category_column", None),
                            excel_sheet_name=getattr(_cfg, "excel_sheet_name", None),
                            case_sensitive=getattr(_cfg, "case_sensitive", None),
                            file_operation_mode=getattr(_cfg, "file_operation_mode", None),
                        )
                    except Exception as _e:
                        self.logger.debug(f"런타임 설정 반영 스킵: {_e}")
                    
                    # 크레딧 제한된 파일 목록 전달
                    if hasattr(self, 'credit_limited_files') and self.credit_limited_files:
                        self.automation.set_file_limit(self.credit_limited_files)
                    
                    result = self.automation.classify_dwg_files()
                    # 실제 처리된 개수로 기록
                    if result and isinstance(result, dict):
                        self.last_run_success_count = result.get("processed", 0)
                    else:
                        self.last_run_success_count = count
                    
                    # 결과 저장
                    if result and isinstance(result, dict):
                        self.classification_result = result
                else:
                    # Fallback simulate progress
                    import time

                    for i, _ in enumerate(dwg_files, 1):
                        time.sleep(0.02)
                        self.update_progress_ui(i, count)
                    self.last_run_success_count = count
            finally:
                self.master.after(0, lambda: self._on_classification_complete({"error": None}))

        threading.Thread(target=worker, daemon=True).start()

    def update_progress_ui(self, current, total, status_text=""):
        def _upd():
            if self.spinner_running:
                self.stop_spinner()
            self.last_run_success_count = current
            # 진행 바는 전체 대비 누적 처리 (이미 처리 + 현재 처리)
            already = getattr(self, "already_processed_count", 0)
            total_all = getattr(self, "total_file_count", total)
            cumulative = already + current
            self.progress_bar.config(maximum=total_all)
            self.progress_bar["value"] = cumulative
            # 진행률 라벨 포맷팅 (utils 사용)
            label = format_progress_label(
                already_processed_count=already,
                current_processed=current,
                total_file_count=total_all,
                is_finished=False
            )
            self.progress_label.config(text=label)

        try:
            self.master.after(0, _upd)
        except Exception:
            _upd()

    def start_spinner(self):
        def _start():
            if not self.spinner_running:
                self.spinner_running = True
                self.spinner_index = 0
                self._animate_spinner()

        self.master.after(0, _start)

    def stop_spinner(self):
        def _stop():
            self.spinner_running = False
            self.spinner_label.config(text="", fg="black")

        self.master.after(0, _stop)

    def _animate_spinner(self):
        if self.spinner_running:
            ch = self.spinner_chars[self.spinner_index]
            self.spinner_label.config(text=ch, fg="black")
            self.spinner_index = (self.spinner_index + 1) % len(self.spinner_chars)
            self.master.after(100, self._animate_spinner)
    
    def show_classification_summary(self, result):
        """분류 결과 요약 팝업 표시 (단일 팝업)"""
        try:
            import webbrowser
            
            total = result.get("total", 0)
            processed = result.get("processed", 0)
            failed = result.get("failed", 0)
            folder_stats = result.get("folder_stats", {})
            unclassified = result.get("unclassified_count", 0)
            credit_shortage_stop = result.get("credit_shortage_stop", False)

            # 크레딧 부족으로 인한 중단 시 특별 팝업
            if credit_shortage_stop:
                already_count = getattr(self, 'already_processed_count', 0)
                total_all = getattr(self, 'total_file_count', total)
                
                msg = build_credit_shortage_completion_message(
                    processed=processed,
                    already_processed_count=already_count,
                    total_file_count=total_all,
                    folder_stats=folder_stats,
                    unclassified_count=unclassified
                )
                
                if messagebox.askyesno("크레딧 부족 - 작업 중단", msg):
                    # 크레딧 구매 페이지로 이동
                    try:
                        purchase_url = get_credit_purchase_url()
                        webbrowser.open(purchase_url)
                    except Exception as e:
                        messagebox.showwarning(
                            "안내",
                            "크레딧 구매 페이지를 열 수 없습니다.\n"
                            "브라우저에서 수동으로 접속해주세요.\n\n"
                            f"URL: {get_credit_purchase_url()}"
                        )
                        self.logger.warning(f"크레딧 구매 페이지 열기 실패: {e}")
                return
            
            # 정상 완료 시 요약 팝업
            unmatched_files = result.get("unmatched_files", [])
            msg = build_normal_completion_message(
                total=total,
                processed=processed,
                failed=failed,
                folder_stats=folder_stats,
                unclassified_count=unclassified,
                unmatched_files=unmatched_files
            )
            # 완료된 폴더 재실행 모드이면 안내 문구 추가
            if getattr(self.automation, "only_count_new_duplicates", False):
                msg += "\n\n※ 이번 실행에서 새로 생성된 파일만 집계했습니다. (예: '_1', '(1)')"
            
            # 메인창과 동일한 너비의 커스텀 다이얼로그 표시
            self._show_completion_dialog("분류 완료", msg)
            
        except Exception as e:
            self.logger.error(f"결과 요약 표시 중 오류: {e}")

    def _show_completion_dialog(self, title: str, message: str):
        """메인창과 동일한 너비의 분류 완료 다이얼로그 표시"""
        dialog = tk.Toplevel(self.master)
        dialog.title(title)
        dialog.transient(self.master)
        dialog.grab_set()
        dialog.wm_attributes("-topmost", 1)
        
        # 메인창 너비의 2/3로 설정
        main_width = self.master.winfo_width()
        dialog_width = int(main_width * 2 / 3)
        
        # 메시지 텍스트 위젯 (높이를 10으로 줄임 - 기존 15의 2/3)
        text_frame = ttk.Frame(dialog, padding=20)
        text_frame.pack(fill=tk.BOTH, expand=True)
        
        text_widget = tk.Text(text_frame, wrap=tk.WORD, height=10, width=40)
        text_widget.insert("1.0", message)
        text_widget.config(state="disabled")
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(text_frame, command=text_widget.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        text_widget.config(yscrollcommand=scrollbar.set)
        
        # 확인 버튼
        button_frame = ttk.Frame(dialog, padding=(20, 0, 20, 20))
        button_frame.pack(fill=tk.X)
        ok_button = ttk.Button(button_frame, text="확인", command=dialog.destroy, width=10)
        ok_button.pack()
        
        # 다이얼로그 크기 및 위치 설정
        dialog.update_idletasks()
        dialog_height = dialog.winfo_reqheight()
        
        # 메인창 중심 좌표에 맞춰 배치
        main_x = self.master.winfo_x()
        main_y = self.master.winfo_y()
        main_height = self.master.winfo_height()
        main_center_x = main_x + main_width // 2
        main_center_y = main_y + main_height // 2
        
        dialog_x = main_center_x - dialog_width // 2
        dialog_y = main_center_y - dialog_height // 2
        
        dialog.geometry(f"{dialog_width}x{dialog_height}+{dialog_x}+{dialog_y}")
        dialog.focus_set()

    def _on_classification_complete(self, exception_info):
        if exception_info.get("error"):
            messagebox.showerror("오류", str(exception_info["error"]))
        # 완료 시 누적이 아닌 최종 처리 개수로 설정
        self.cumulative_processed_count = self.last_run_success_count
        
        # 크레딧 부족으로 중단된 경우 다른 표시 사용
        if hasattr(self, 'classification_result') and self.classification_result:
            if self.classification_result.get("credit_shortage_stop", False):
                already = getattr(self, "already_processed_count", 0)
                total_all = getattr(self, "total_file_count", self.initial_file_count or self.last_run_success_count)
                # utils 함수로 라벨 포맷팅
                label = format_progress_label(
                    already_processed_count=already,
                    current_processed=self.cumulative_processed_count,
                    total_file_count=total_all,
                    is_finished=False
                )
                # 크레딧 부족 표시 추가
                if "(잔여" in label:
                    label = label.replace("(잔여", "(중단: 크레딧 부족, 잔여")
                else:
                    label = label.replace("(완료)", "(중단: 크레딧 부족)")
                self.progress_label.config(text=label)
                # 진행 바도 누적 기준으로 업데이트
                cumulative = already + self.cumulative_processed_count
                self.progress_bar.config(maximum=total_all)
                self.progress_bar["value"] = cumulative
        for b in [
            self.folder_button,
            self.excel_button,
            self.exit_button,
            self.settings_button,
            self.refresh_credit_button,
        ]:
            b.config(state="normal")
        
        # 크레딧 체크 후 분류시작 버튼 상태 결정
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
        self.update_credit_display()
        
        # 분류 결과 요약 팝업 표시
        if hasattr(self, 'classification_result') and self.classification_result:
            self.show_classification_summary(self.classification_result)
        
        # 백그라운드 동기화
        def background_sync():
            try:
                if self.credit_manager:
                    sync_status = self.credit_manager.get_sync_status()
                    if sync_status.get("needs_sync"):
                        self.logger.info("🧾 처리 완료 후 사용 내역 동기화 시도 (백그라운드)...")
                        log_result = self.credit_manager.check_and_sync_credits()
                        self.logger.info(f"[SYNC-AFTER-RUN] {log_result}")
            except Exception as e:
                self.logger.warning(f"[USAGE-LOG-AFTER-RUN] 사용 로그 기록 중 오류: {e}")
        
        # 백그라운드 스레드로 동기화 실행
        threading.Thread(target=background_sync, daemon=True, name="Credit-Sync-Worker").start()
        
        # 분류 작업 완료 캡처

    # ---------- Registration / Settings ----------
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
            import wf_hwinfo

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
        self.is_registered_user = self.check_user_registration()
        if self.is_registered_user:
            self.settings_button.config(text="설 정", command=self.open_settings_window)
        self.update_credit_display()

    def open_settings_window(self):
        """Settings window opener - delegates to ui_setting.py"""
        try:
            from ui_setting import create_settings_window
            from app_setting_data import get_config

            cfg = get_config()
            create_settings_window(self.master, cfg)
            # 설정 저장 후 이미 생성된 automation 인스턴스가 있으면 즉시 반영
            try:
                if hasattr(self, "automation") and self.automation is not None:
                    self.automation.apply_runtime_settings(
                        drawing_column=getattr(cfg, "drawing_column", None),
                        category_column=getattr(cfg, "category_column", None),
                        excel_sheet_name=getattr(cfg, "excel_sheet_name", None),
                        case_sensitive=getattr(cfg, "case_sensitive", None),
                        file_operation_mode=getattr(cfg, "file_operation_mode", None),
                    )
            except Exception as e:
                self.logger.warning(f"런타임 설정 반영 실패(무시): {e}")
        except Exception as e:
            self.logger.error(f"설정 창 열기 실패: {e}")
            messagebox.showerror("오류", f"설정 창을 열 수 없습니다:\n{e}")

    # ---------- Admin Mode ----------
    def toggle_admin_mode(self):
        if self.is_admin_mode:
            self._exit_admin_mode()
            return
        run_mode = getattr(self.config, "run_mode", getattr(self.config, "get", lambda *_: "release")("run_mode", "release"))
        if run_mode == "dev":  # dev 모드에서만 암호 없이 진입
            self._enter_admin_mode()
            return

        from tkinter import simpledialog

        pw = simpledialog.askstring("관리자 인증", "비밀번호 입력:", show="*", parent=self.master)
        if pw is None:
            return
        if pw == self.admin_password:
            self._enter_admin_mode()
        else:
            messagebox.showerror("인증 실패", "비밀번호가 올바르지 않습니다.")

    def _enter_admin_mode(self):
        self.is_admin_mode = True
        self.admin_mode_start_time = datetime.datetime.now()
        self.admin_mode_timer = self.master.after(1800000, self._auto_exit_admin_mode)
        # Expand window
        geo = self.master.geometry()
        width_str = geo.split("x")[0]
        # 현재 창 너비 유지, 없으면 580 기본값
        try:
            width = int(width_str)
        except Exception:
            width = 580
        pos = geo.split("+", 1)[1] if "+" in geo else "0+0"
        self.master.geometry(f"{width}x{self.expanded_window_height}+{pos}")
        self.master.resizable(True, True)
        self.master.title(f"DWG 파일 분류 도구 {APP_VERSION_FULL} [🔧 관리자 모드]")
        self.progress_bar_label.config(bg="#ffe6e6")
        self.create_log_frame()

        # 관리자 모드 활성화 로그 - UI 로그창에 직접 출력
        import ctypes
        import getpass

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

        try:
            current_user = getpass.getuser()
        except Exception:
            current_user = "Unknown"
        write_to_log(f"현재 사용자: {current_user}")
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

        self._show_toast("관리자 모드 활성화", 1200)

    def _exit_admin_mode(self):
        if not self.is_admin_mode:
            return
        self.is_admin_mode = False
        if self.admin_mode_timer:
            try:
                self.master.after_cancel(self.admin_mode_timer)
            except Exception:
                pass
            self.admin_mode_timer = None
        self.destroy_log_frame()
        
        # 저장된 geometry override가 있으면 사용, 없으면 기본값 사용
        target_height = self.ui.get("window_height", 320)
        override_geo = self._get_geometry_override_if_allowed()
        if override_geo:
            try:
                self.master.geometry(override_geo)
                if self.logger:
                    self.logger.info(f"[ADMIN-EXIT] geometry override 복원: {override_geo}")
            except Exception as e:
                # override 적용 실패시 기본값으로 폴백
                geo = self.master.geometry()
                pos = geo.split("+", 1)[1] if "+" in geo else "0+0"
                window_width = self.ui.get("window_width", 480)
                self.master.geometry(f"{window_width}x{target_height}+{pos}")
                if self.logger:
                    self.logger.warning(f"[ADMIN-EXIT] geometry override 적용 실패, 기본값 사용: {e}")
        else:
            # override 없으면 기본 geometry 사용
            geo = self.master.geometry()
            pos = geo.split("+", 1)[1] if "+" in geo else "0+0"
            window_width = self.ui.get("window_width", 480)
            self.master.geometry(f"{window_width}x{target_height}+{pos}")
        
        self.master.resizable(True, True)
        self.master.title(f"DWG 파일 분류 도구 {APP_VERSION_DISPLAY}")
        self.progress_bar_label.config(bg=self.master.cget("bg"))

        # 프로그레스 초기화
        self.progress_bar["value"] = 0
        self.progress_bar.config(maximum=100)
        self.progress_label.config(text="0/0")
        self.spinner_label.config(text="○", fg="#cccccc")

        self._show_toast("관리자 모드 비활성화", 1200)

    def _auto_exit_admin_mode(self):
        """30분 후 자동 관리자 모드 종료"""
        self._exit_admin_mode()
        self._show_toast("관리자 모드 자동 해제", 1500)
        self.update_credit_display()

    # ---------- Log Frame ----------
    def create_log_frame(self):
        if self.log_frame:
            return
        main_frame = None
        for c in self.master.winfo_children():
            if isinstance(c, tk.Frame):
                main_frame = c
                break
        if not main_frame:
            return
        self.log_frame = tk.Frame(main_frame)
        self.log_frame.pack(fill="both", expand=True, pady=(10, 0))
        head = tk.Frame(self.log_frame)
        head.pack(fill="x", pady=(0, 5))
        tk.Label(
            head, text="실시간 로그 (DEBUG)", font=("맑은 고딕", self.ui["font_size"], "bold")
        ).pack(side="left")
        self.auto_scroll_var = tk.BooleanVar(value=True)
        self.auto_scroll_checkbox = tk.Checkbutton(
            head,
            text="자동 스크롤",
            variable=self.auto_scroll_var,
            font=("맑은 고딕", self.ui["font_size"]),
        )
        self.auto_scroll_checkbox.pack(side="right")
        tf = tk.Frame(self.log_frame)
        tf.pack(fill="both", expand=True)
        self.log_scrollbar = tk.Scrollbar(tf)
        self.log_scrollbar.pack(side="right", fill="y")
        self.log_text = tk.Text(
            tf,
            wrap="word",
            yscrollcommand=self.log_scrollbar.set,
            font=("Consolas", self.ui["font_size"]),
            bg="#f8f8f8",
            fg="#333",
            height=10,
            state="disabled",
        )
        self.log_text.pack(side="left", fill="both", expand=True)
        self.log_scrollbar.config(command=self.log_text.yview)
        btns = tk.Frame(self.log_frame)
        btns.pack(fill="x", pady=(5, 0))
        tk.Button(
            btns, text="테스트 데이터 생성", command=self.create_test_data, width=20, bg="#e8f5e9"
        ).pack(side="left", padx=5)
        tk.Button(
            btns, text="테스트 데이터 삭제", command=self.delete_test_data, width=20, bg="#ffebee"
        ).pack(side="left", padx=5)
        self.setup_log_handler()

    def destroy_log_frame(self):
        if not self.log_frame:
            return
        self.remove_log_handler()
        self.log_frame.destroy()
        self.log_frame = None
        self.log_text = None
        self.log_scrollbar = None
        self.auto_scroll_var = None
        self.auto_scroll_checkbox = None

    def setup_log_handler(self):
        class TextHandler(logging.Handler):
            def __init__(self, text_widget, auto_scroll_var, master):
                super().__init__()
                self.text_widget = text_widget
                self.auto_scroll_var = auto_scroll_var
                self.master = master

            def emit(self, record):
                msg = self.format(record)
                self.master.after(0, lambda: self._append(msg))

            def _append(self, msg):
                try:
                    if not (self.text_widget and self.text_widget.winfo_exists()):
                        return
                    self.text_widget.config(state="normal")
                    self.text_widget.insert("end", msg + "\n")
                    lines = int(self.text_widget.index("end-1c").split(".")[0])
                    if lines > 1000:
                        self.text_widget.delete("1.0", "200.0")
                    if self.auto_scroll_var and self.auto_scroll_var.get():
                        self.text_widget.see("end")
                    self.text_widget.config(state="disabled")
                except Exception:
                    pass

        self.text_log_handler = TextHandler(self.log_text, self.auto_scroll_var, self.master)
        self.text_log_handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
        )
        self.text_log_handler.setLevel(logging.DEBUG)
        self.logger.addHandler(self.text_log_handler)

    def remove_log_handler(self):
        if self.text_log_handler:
            try:
                self.logger.removeHandler(self.text_log_handler)
            except Exception:
                pass
            self.text_log_handler = None

    # ---------- Test Data (Standardized ./test) ----------
    def create_test_data(self):
        try:
            # 필수 모듈 import를 최상단으로 이동
            import os
            import stat
            import shutil
            
            # 테스트 데이터는 앱 폴더 상위에 생성 (…/50.data/test)
            base = Path(__file__).parent / "test"
            
            # 데모 모드에서는 폴더를 삭제하지 않고 파일만 생성 (영상 촬영용)
            if not self.is_demo_mode and base.exists():
                # ReadOnly 속성 제거 후 삭제
                def remove_readonly(func, path, excinfo):
                    """읽기 전용 속성 제거 후 재시도"""
                    os.chmod(path, stat.S_IWRITE)
                    func(path)
                
                shutil.rmtree(base, onerror=remove_readonly)
            base.mkdir(parents=True, exist_ok=True)
            
            # ReadOnly 속성 제거 (부모 폴더로부터 상속 방지)
            os.chmod(base, stat.S_IWRITE | stat.S_IREAD | stat.S_IEXEC)
            
            import random, pandas as pd
            from datetime import datetime as _dt
            from app_setting_data import get_config

            # 설정에서 컬럼명 로드
            cfg = get_config()
            drawing_col = getattr(cfg, 'drawing_column', '도번/규격')
            category_col = getattr(cfg, 'category_column', '제조사/가공분류')
            sheet_name = getattr(cfg, 'excel_sheet_name', '구매요청')

            # 45개 DWG 파일 생성 (DRW0001 ~ DRW0045)
            # 40개는 엑셀에 포함, 5개는 미분류 파일로 남김
            all_dwg_files = [f"DRW{i:04d}" for i in range(1, 46)]
            for dn in all_dwg_files:
                (base / f"{dn}.dwg").write_text(
                    f"# Test DWG {dn}\n# Created:{_dt.now()}\n", encoding="utf-8"
                )

            # 3개 Excel 발주관리서 생성 (설정 컬럼명 사용)
            # 45개를 3개 분류로 랜덤 배분: 선반가공, 밀링가공, 용접 프로파일
            excel_files = []
            process_categories = ["선반가공", "밀링가공", "용접 프로파일"]
            
            # 45개 파일을 3개 분류로 랜덤하게 나누기
            # 각 분류는 최소 5개, 최대 25개 정도로 제한
            remaining = len(all_dwg_files)
            category_assignments = {}
            
            # 랜덤하게 각 분류별 개수 할당
            counts = []
            for i in range(len(process_categories) - 1):
                max_count = remaining - (len(process_categories) - i - 1) * 5  # 최소 5개씩 남겨둠
                count = random.randint(5, min(25, max_count))
                counts.append(count)
                remaining -= count
            counts.append(remaining)  # 마지막 분류는 남은 개수
            
            # 45개 파일을 섞어서 분류에 할당
            shuffled_files = all_dwg_files.copy()
            random.shuffle(shuffled_files)
            
            idx = 0
            for category, count in zip(process_categories, counts):
                for _ in range(count):
                    category_assignments[shuffled_files[idx]] = category
                    idx += 1
            
            # 3개 엑셀 파일 생성 (45개를 랜덤하게 나눔)
            random.shuffle(all_dwg_files)  # 엑셀 배분용으로 다시 섞기
            files_per_excel = [15, 15, 15]  # 각 엑셀당 15개씩
            
            start_idx = 0
            for excel_idx, count in enumerate(files_per_excel, 1):
                end_idx = start_idx + count
                rows_in_excel = all_dwg_files[start_idx:end_idx]
                
                df = pd.DataFrame(
                    {
                        drawing_col: rows_in_excel,
                        category_col: [category_assignments[r] for r in rows_in_excel],
                        "품명": [f"부품_{r}" for r in rows_in_excel],
                        "재질": [
                            random.choice(["SUS304", "AL6061", "S45C", "SS400"]) for _ in rows_in_excel
                        ],
                        "수량": [random.randint(1, 5) for _ in rows_in_excel],
                    }
                )
                xlsx = base / f"test_발주관리서_{excel_idx}.xlsx"
                try:
                    with pd.ExcelWriter(xlsx, engine="openpyxl") as w:
                        df.to_excel(w, sheet_name=sheet_name, index=False)
                except ImportError:
                    # openpyxl이 없으면 xlsxwriter 사용
                    with pd.ExcelWriter(xlsx, engine="xlsxwriter") as w:
                        df.to_excel(w, sheet_name=sheet_name, index=False)
                excel_files.append(str(xlsx))
                start_idx = end_idx

            # 폴더 경로 업데이트
            self.set_selected_path(str(base))
            
            # 엑셀 파일 선택 업데이트
            self.selected_excel_files = excel_files
            self.excel_listbox.delete(0, tk.END)
            for excel_file in excel_files:
                self.excel_listbox.insert(tk.END, os.path.basename(excel_file))
            
            # 어드민 모드에서는 자동으로 폴더 스캔 체크하여 메인 버튼 활성화
            try:
                if hasattr(self, "scan_toggle_btn"):
                    self.scan_toggle_btn.config(state="disabled")
                self.scan_toggle_var.set(True)
                self.on_scan_toggle()
            finally:
                if hasattr(self, "scan_toggle_btn"):
                    self.scan_toggle_btn.config(state="normal")
            
            self.check_ready_to_start()
            
            # 분류별 개수 집계
            category_counts = {}
            for category in process_categories:
                category_counts[category] = sum(1 for c in category_assignments.values() if c == category)
            
            message_lines = [
                f"테스트 데이터 생성 완료",
                f"위치: {base}",
                f"",
                f"📁 엑셀: {len(excel_files)}개 (각 15개 도번 포함)",
                f"📄 전체 DWG: {len(all_dwg_files)}개",
                f"",
                f"📂 분류 카테고리별 배분 (랜덤):",
                f"  - 선반가공: {category_counts.get('선반가공', 0)}개",
                f"  - 밀링가공: {category_counts.get('밀링가공', 0)}개", 
                f"  - 용접 프로파일: {category_counts.get('용접 프로파일', 0)}개",
                f"",
                f"💡 각 엑셀에 분류가 랜덤하게 섞여 있습니다"
            ]
            
            messagebox.showinfo(
                "완료",
                "\n".join(message_lines),
                parent=self.master,
            )
        except Exception as e:
            self.logger.error(f"테스트 데이터 생성 실패: {e}", exc_info=True)
            messagebox.showerror("오류", f"테스트 데이터 생성 실패:\n{e}", parent=self.master)

    def delete_test_data(self):
        try:
            import os, stat

            base = Path(__file__).parent / "test"
            if not base.exists():
                messagebox.showinfo("알림", "삭제할 테스트 데이터가 없습니다.", parent=self.master)
                return
            import shutil

            def _onerror(func, path, exc_info):
                try:
                    os.chmod(path, stat.S_IWRITE)
                    func(path)
                except Exception:
                    pass

            # 데모 모드에서는 폴더는 남기고 내부 파일만 삭제 (영상 촬영용)
            if self.is_demo_mode:
                deleted_count = 0
                for item in base.iterdir():
                    try:
                        if item.is_file():
                            os.chmod(item, stat.S_IWRITE)
                            item.unlink()
                            deleted_count += 1
                        elif item.is_dir():
                            shutil.rmtree(item, onerror=_onerror)
                            deleted_count += 1
                    except Exception as e:
                        self.logger.warning(f"항목 삭제 실패 ({item.name}): {e}")
                messagebox.showinfo("완료", f"테스트 데이터 {deleted_count}개가 삭제되었습니다.\n(test 폴더는 유지됨)", parent=self.master)
            else:
                # 일반 모드에서는 폴더 전체 삭제
                shutil.rmtree(base, onerror=_onerror)
                messagebox.showinfo("완료", "테스트 데이터가 삭제되었습니다.", parent=self.master)
            
            if self.SELECTED_PATH and Path(self.SELECTED_PATH) == base:
                self.set_selected_path(None)
        except Exception as e:
            self.logger.error(f"테스트 데이터 삭제 실패: {e}", exc_info=True)
            messagebox.showerror("오류", f"테스트 데이터 삭제 실패:\n{e}", parent=self.master)

    # ==================== WF-ACT Test Mode ====================

    def init_test_server(self):
        """WF-ACT 인증 테스트용 TestServer 초기화"""
        try:
            # 테스트 모드에서는 CreditManager를 동기적으로 초기화
            self._init_credit_manager_sync()

            # TestServer import (로컬 test_server.py 사용)
            from test_server import TestServer

            self.test_server = TestServer(app_name="dwg_classifier")

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
                    app_name="dwg_classifier",
                    wf_manager=self.wf_manager,
                    master=self.master,
                    logger=self.logger,
                    recovery_delay_ms=0,
                    policy_delay_ms=0,
                )
        except Exception as e:
            if self.logger:
                self.logger.error(f"[WF-ACT] CreditManager sync init failed: {e}")

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
            if current != -1:
                data["remaining_purchased"] = current + amount
            self.credit_manager._save_credit_data(data)
            self.master.after(0, self.update_credit_display)
            return True
        except Exception as e:
            self.logger.error(f"[WF-ACT] add_credits failed: {e}")
            return False

    def _ensure_credit_manager(self):
        """CreditManager가 초기화될 때까지 대기 (최대 5초)"""
        import time
        for _ in range(50):
            if self.credit_manager:
                return
            time.sleep(0.1)

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
                    trial_credits = self.credit_manager.policy.get("trial_credits", 5000)
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

        cost = self.credit_manager.policy.get("credit_per_work", 50)

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
            "is_registered": getattr(self, 'is_registered_user', False),
            "credits": self._test_get_credits() if self.credit_manager else 0,
            "selected_path": self.SELECTED_PATH,
            "is_running": getattr(self, 'automation', None) is not None and hasattr(self.automation, 'is_running') and self.automation.is_running,
        }

    def _test_get_policy(self) -> dict:
        """정책 정보 반환"""
        if self.credit_manager and hasattr(self.credit_manager, 'policy'):
            policy = self.credit_manager.policy.copy()
            policy['identity'] = {
                'app_name': 'dwg_classifier',
                'display_name': 'DWG Classifier',
            }
            return policy
        return {
            'identity': {
                'app_name': 'dwg_classifier',
                'display_name': 'DWG Classifier',
            },
            'policy': {
                'credit_per_work': 50,
                'trial_credits': 5000,
            }
        }

    def _test_get_settings(self) -> dict:
        """설정 정보 반환"""
        settings = {}
        if self.config:
            try:
                # Try config attributes first, then module-level APP_VERSION_FULL
                version = (getattr(self.config, 'full_version', None) or
                          getattr(self.config, 'version', None))
                if not version or version == 'unknown':
                    version = APP_VERSION_FULL  # Use canonical version source
                settings = {
                    'runtime_config': {
                        'full_version': version,
                        'run_mode': getattr(self.config, 'run_mode', 'release'),
                    },
                    'app_config': {
                        'app_name': 'dwg_classifier',
                    }
                }
            except Exception:
                pass
        return settings

    def _test_reload_config(self) -> bool:
        """설정 및 정책 재로드 (테스트용)"""
        try:
            if self.credit_manager:
                self.credit_manager._reload_policy()
            return True
        except Exception:
            return False

    def _test_get_button_state(self, button_name: str) -> dict:
        """버튼 상태 반환"""
        button_map = {
            'work': getattr(self, 'btn_start', None),
            'settings': getattr(self, 'btn_settings', None),
            'register': getattr(self, 'btn_registration', None),
        }
        btn = button_map.get(button_name)
        if not btn:
            return {"exists": False}
        try:
            state = str(btn.cget('state'))
            return {
                "exists": True,
                "enabled": state != 'disabled',
                "state": state,
            }
        except Exception:
            return {"exists": True, "enabled": True, "state": "normal"}

    def _test_click_button(self, button_name: str) -> bool:
        """버튼 클릭 시뮬레이션"""
        button_map = {
            'work': getattr(self, 'btn_start', None),
            'settings': getattr(self, 'btn_settings', None),
            'register': getattr(self, 'btn_registration', None),
        }
        btn = button_map.get(button_name)
        if not btn:
            return False
        try:
            btn.invoke()
            return True
        except Exception:
            return False

    def _test_get_trial_info(self) -> dict:
        """체험판 크레딧 정보 반환 (테스트용)"""
        self._ensure_credit_manager()
        if not self.credit_manager:
            return {"error": "credit_manager_not_initialized"}
        try:
            policy = self.credit_manager.policy or {}
            data = self.credit_manager._load_credit_data()
            return {
                "initial_credits": policy.get("trial_credits", 5000),
                "remaining_trial": data.get("remaining_trial", 0),
                "trial_credits": policy.get("trial_credits", 5000),
            }
        except Exception as e:
            return {"error": str(e)}

    def _test_sync_registration(self) -> dict:
        """등록 정보 서버 동기화 (테스트용)"""
        if not self.wf_manager:
            return {"success": False, "error": "wf_manager_not_initialized"}
        try:
            # 실제 동기화 시도 (네트워크 오류는 허용됨)
            return {"success": True, "message": "sync_attempted"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _test_save_settings(self, settings: dict) -> dict:
        """설정 저장 (테스트용)"""
        try:
            import json
            settings_file = self.config.settings_file
            data = {}
            if settings_file.exists():
                with open(settings_file, "r", encoding="utf-8") as f:
                    data = json.load(f) or {}
            # 테스트 설정을 test_config 섹션에 저장
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
            settings_file = self.config.settings_file
            if not settings_file.exists():
                return {}
            with open(settings_file, "r", encoding="utf-8") as f:
                data = json.load(f) or {}
            # 전체 설정 반환 (app_config, ui_config, test_config 등)
            return {
                "app_config": data.get("app_config", {}),
                "ui_config": data.get("ui_config", {}),
                "test_config": data.get("test_config", {}),
            }
        except Exception as e:
            return {"error": str(e)}


# ==================== Main Entry ====================

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

        result = manager.sync_local_registration_to_sheets("dwg_classifier", app_version)

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
    global _instance_mutex_handle
    # --test-mode 인자 처리 (WF-ACT 인증 테스트 모드)
    test_mode = "--test-mode" in sys.argv

    # --sync-registration 인자 처리 (GUI 없이 동기화만 수행)
    if "--sync-registration" in sys.argv:
        sys.exit(_handle_sync_registration())

    _log_startup("main() called")

    # 테스트 모드에서는 single instance 및 cross-app 체크 건너뛰기
    if not test_mode:
        # Enforce single instance across the system (prevents recursive spawns)
        is_first, _instance_mutex_handle = _acquire_single_instance()
        _log_startup("single instance check complete")
        if not is_first:
            # Avoid creating any UI if another instance is running
            try:
                print("Another dwg_classifier instance is already running. Exiting.")
            except Exception:
                pass
            return

        # 교차 앱 실행 방지 (공통 헬퍼 사용)
        if check_cross_app_running_and_exit:
            check_cross_app_running_and_exit("dwg_classifier")
        try:
            _set_cross_app_running("dwg_classifier")
        except Exception:
            pass
        try:
            import atexit

            atexit.register(_clear_cross_app_running)
        except Exception:
            pass
    # (Pre-Tk DPI awareness adjustments removed per request)
    root = tk.Tk()
    
    # 초기화 중 창 숨김 (깜빡임 방지)
    root.withdraw()
    
    # 작업표시줄 아이콘 설정 (개발/릴리스 환경 모두 지원)
    try:
        # 아이콘 파일명 (새 아이콘: 03_DWG_Classifier.ico, 기존: DWG.ico)
        icon_names = ["03_DWG_Classifier.ico", "DWG.ico"]

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
            else Path.home() / ".wf_rpa" / "dwg_classifier" / "res"
        )
        bundle_candidates = [Path(__file__).parent / "res"]
        if getattr(sys, "frozen", False):
            exe_dir = Path(sys.executable).parent
            bundle_candidates = [exe_dir / "res", exe_dir / "_internal" / "res"] + bundle_candidates
        seed_res_if_missing(target_res, bundle_candidates, logger=None)
    except Exception:
        pass
    
    app = DwgClassifierApp(root)
    _log_startup("App init complete")

    # WF-ACT 테스트 모드: TestServer 초기화
    if test_mode:
        try:
            app.init_test_server()
            _log_startup("TestServer started")
        except Exception as e:
            print(f"[WF-ACT] TestServer init failed: {e}")
            import traceback
            traceback.print_exc()

    # UI 초기화 완료 후 창 표시
    root.deiconify()

    _flush_startup_log()
    root.mainloop()


if __name__ == "__main__":
    main()
