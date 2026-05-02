# -*- coding: utf-8 -*-
"""QR Code Generator Main UI (dwg_classifier-style structure)"""

import os
import sys

# Windows 콘솔 UTF-8 강제 설정
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
from tkinter import messagebox

# 10.common 모듈 경로
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

try:
    from wf_log import get_app_logger
except Exception:
    def get_app_logger(name, console_level=logging.DEBUG):
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
    create_trial_window = None
    logging.getLogger("qrcode_generator").warning(f"wf_register import 실패: {_e}")

# Adaptive UI 통합 모듈
try:
    from wf_ui_adaptive import get_adaptive_ui_settings, apply_global_fonts
except ImportError:
    def get_adaptive_ui_settings(window_type="main", saved_ui=None):
        return {"window_width": 760, "window_height": 200, "font_size": 9, "padding": 10}
    def apply_global_fonts(root, ui): pass

try:
    from app_setting_data import get_config
except Exception:
    def get_config():
        class Dummy:
            def get(self, k, d=None):
                return d
            def set(self, k, v):
                pass
            def save_settings(self):
                pass
        return Dummy()


# ==================== STARTUP PROFILER ====================
_STARTUP_LOG = []
_STARTUP_ENABLED = True
_STARTUP_FLUSHED = False


def _detect_run_mode():
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
        path = Path.home() / ".wf_rpa" / "qrcode_generator" / "startup_profile.log"
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    return path


def _log_startup(msg: str):
    if not _STARTUP_ENABLED:
        return
    import time
    _STARTUP_LOG.append((time.perf_counter(), msg))


def _flush_startup_log():
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


# ==================== VERSION INFO ====================
def _load_version_info():
    default_full = "v0.7.0.0"
    full_version = default_full

    try:
        if getattr(sys, "frozen", False):
            # 릴리스 모드: 번들 버전 우선 (정확한 빌드 버전), fallback으로 사용자 홈
            base_path = Path(sys._MEIPASS) if hasattr(sys, '_MEIPASS') else Path(sys.executable).parent
            settings_file = base_path / ".wf_rpa" / "qrcode_generator" / "settings.json"
            if not settings_file.exists():
                settings_file = Path.home() / ".wf_rpa" / "qrcode_generator" / "settings.json"
        else:
            app_root = Path(__file__).parent
            settings_file = app_root.parent.parent / "10.common" / "config" / "qrcode_generator" / "settings.json"
            if not settings_file.exists():
                settings_file = app_root / "config" / "qrcode_generator" / "settings.json"

        if settings_file.exists():
            with open(settings_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                runtime_config = data.get("runtime_config", {})
                full_version = runtime_config.get("full_version", default_full)
                if not full_version.startswith("v"):
                    full_version = "v" + full_version
    except Exception:
        pass

    parts = full_version.lstrip("v").split(".")
    display_version = "v" + ".".join(parts[:2])

    return full_version, display_version


APP_VERSION_FULL, APP_VERSION_DISPLAY = _load_version_info()


# ==================== SINGLE/CROSS INSTANCE ====================
_instance_mutex_handle = None


def _acquire_single_instance(mutex_name: str = r"Global\\WF_QRCODE_GENERATOR"):
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
class QRCodeGeneratorApp:
    def __init__(self, master: tk.Tk):
        _log_startup("QRCodeGeneratorApp.__init__")
        self.master = master
        self.itself_dir = os.path.dirname(os.path.abspath(__file__))
        self.logger = get_app_logger("qrcode_generator", console_level=logging.DEBUG)
        self.config = get_config()

        # 아이콘 경로 저장 (등록창/설정창에서 사용)
        self.icon_path = self._find_icon_path()

        try:
            self.is_demo_mode = bool(self.config and hasattr(self.config, "is_demo") and self.config.is_demo())
        except Exception:
            self.is_demo_mode = False

        # 적응형 UI 설정 초기화 (config 로드 후 호출 - saved_ui 적용)
        saved_ui = getattr(self.config, "ui_config", None)
        self.ui = get_adaptive_ui_settings(window_type="main", saved_ui=saved_ui)

        # WorksFree 매니저
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
        self.automation = None
        self.is_generating = False
        self.preview_image = None  # PhotoImage reference holder

        # 관리자 모드 변수
        self.is_admin_mode = False
        self.admin_mode_timer = None  # 30분 자동 복귀 타이머
        self.admin_mode_start_time = None
        # 🚀 최적화: admin 비밀번호 lazy 로딩 (Google Sheets 호출 지연)
        self._admin_password = None  # lazy load

        # Spinner
        self.spinner_running = False
        self.spinner_index = 0
        self.spinner_chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

        # 로그 프레임 관련 변수
        self.log_frame = None
        self.log_text = None
        self.log_scrollbar = None
        self.auto_scroll_var = None
        self.auto_scroll_checkbox = None
        self.text_log_handler = None

        # 창 크기 관련
        self.original_window_height = self.ui.get("window_height", getattr(self.config, "window_height", 200))
        self.expanded_window_height = self.original_window_height + getattr(self.config, "admin_window_height", 300)  # 관리자 모드: settings.json에서 로드

        # Early 등록 상태 확인
        self.is_registered_user = False
        try:
            if self._wfm_available and WorksFreeManager:
                self.wf_manager = WorksFreeManager()
                self.is_registered_user = self.wf_manager.is_registered()
        except Exception as e:
            self.logger.warning(f"Early WorksFreeManager init 실패(무시): {e}")

        self.credit_manager = None

        # UI build
        self.master.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.init_ui()

        try:
            if self.is_registered_user:
                self.update_registration_button()
        except Exception:
            pass

        # 백그라운드 매니저 초기화
        self.master.after(100, self._lazy_init_managers)

        # 사용자 디렉토리 생성
        try:
            self.master.after(200, lambda: threading.Thread(target=self.create_user_directories, daemon=True).start())
        except Exception:
            threading.Thread(target=self.create_user_directories, daemon=True).start()

    def _find_icon_path(self):
        """앱 아이콘 경로 찾기 (개발/릴리스 환경 모두 지원)"""
        try:
            icon_names = ["07_QRCode_Generator.ico"]
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

    def init_ui(self):
        # app_setting_data.py에서 정의한 앱별 고정 창 크기 사용
        window_width = self.ui.get("window_width", getattr(self.config, "window_width", 760))
        window_height = self.ui.get("window_height", getattr(self.config, "window_height", 200))

        self.width = self.master.winfo_screenwidth()
        self.height = self.master.winfo_screenheight()
        x_coord = int(self.width * 5 / 6 - window_width / 2)
        y_coord = int((self.height - window_height) / 2)

        self.master.geometry(f"{window_width}x{window_height}+{x_coord}+{y_coord}")
        self.master.title(f"QR 코드 생성기 {APP_VERSION_DISPLAY}")
        self.master.wm_attributes("-topmost", 1)
        self.master.resizable(True, True)
        # 최소 크기를 기본 크기와 동일하게 설정
        self.master.minsize(window_width, window_height)

        apply_global_fonts(self.master, self.ui)

        self.create_ui_elements()
        
        # 창 크기 변경 시 패딩 재계산
        self.master.bind("<Configure>", self._on_window_resize)

        self.master.lift()
        self.master.focus_force()
        self.update_credit_display()

    def _calculate_adaptive_padding(self):
        """창 높이에 비례한 adaptive 패딩 계산 - 타이트하게 조정"""
        window_height = self.master.winfo_height()
        if window_height <= 1:  # 창이 아직 렌더링되지 않은 경우
            window_height = self.ui.get("window_height", 200)
        
        # 기본 높이 대비 현재 높이 비율
        base_height = self.ui.get("window_height", 200)
        height_ratio = max(0.3, min(1.5, window_height / base_height))
        
        # 패딩 계산 (더 타이트하게)
        self.adaptive_pady = {
            'outer': max(4, int(6 * height_ratio)),   # 외곽 여백
            'section': max(3, int(4 * height_ratio)), # 섹션 간 여백
            'tight': max(2, int(3 * height_ratio)),   # 밀착 여백
        }
        self.adaptive_padx = max(6, int(8 * height_ratio))

    def create_ui_elements(self):
        master = self.master

        master.grid_rowconfigure(0, weight=1)
        master.grid_columnconfigure(0, weight=1)

        # Adaptive 패딩 계산
        self._calculate_adaptive_padding()
        pad_outer = self.adaptive_pady['outer']
        pad_section = self.adaptive_pady['section']
        pad_tight = self.adaptive_pady['tight']
        pad_x = self.adaptive_padx

        # padx=0으로 설정하여 정확히 760px 너비 유지
        main_frame = tk.Frame(master, padx=0, pady=6)
        main_frame.grid(row=0, column=0, sticky="nsew")
        main_frame.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=0)

        # left_frame에 내부 패딩 추가 (padx=12)하여 UI 요소가 창 가장자리에 붙지 않도록 함
        left_frame = tk.Frame(main_frame)
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(12, pad_x))
        left_frame.columnconfigure(0, weight=1)
        left_frame.rowconfigure(0, weight=1)
        left_frame.rowconfigure(1, weight=1)
        left_frame.rowconfigure(2, weight=1)
        left_frame.rowconfigure(3, weight=1)

        right_frame = tk.Frame(main_frame)
        right_frame.grid(row=0, column=1, sticky="nsew")
        right_frame.configure(width=180)
        right_frame.grid_propagate(False)

        # URL 입력
        url_frame = tk.Frame(left_frame)
        url_frame.grid(row=0, column=0, sticky="ew", pady=(0, pad_tight))

        url_label = tk.Label(
            url_frame, text="URL 입력", width=10, anchor="w",
            font=("맑은 고딕", self.ui["font_size"]),
        )
        url_label.pack(side="left")

        self.url_var = tk.StringVar()
        try:
            last_url = self.config.get_last_url() if hasattr(self.config, 'get_last_url') else ""
            if last_url:
                self.url_var.set(last_url)
        except Exception:
            pass

        self.url_entry = tk.Entry(
            url_frame, textvariable=self.url_var,
            font=("맑은 고딕", self.ui["font_size"]),
        )
        self.url_entry.pack(side="left", fill="x", expand=True, padx=(pad_x, 0))
        self.url_entry.bind("<Return>", lambda e: self.start_generation())

        # Progress (BE 스타일)
        progress_frame = tk.Frame(left_frame)
        progress_frame.grid(row=1, column=0, sticky="ew", pady=(0, pad_tight))

        self.progress_bar_label = tk.Label(
            progress_frame, text="진행률:", width=11, font=("맑은 고딕", self.ui["font_size"])
        )
        self.progress_bar_label.pack(side="left")
        self.progress_bar_label.bind("<Button-1>", self.on_progress_label_click)

        self.spinner_label = tk.Label(
            progress_frame, text="○", font=("맑은 고딕", self.ui["font_size_title"]), width=2, fg="#cccccc"
        )
        self.spinner_label.pack(side="left", padx=(5, 0))

        self.progress_bar = ttk.Progressbar(
            progress_frame, orient="horizontal", mode="determinate", maximum=100
        )
        self.progress_bar.pack(side="left", fill="x", expand=True, padx=(pad_x, 0))

        # Status (BE 스타일 - 3컬럼)
        status_frame = tk.Frame(left_frame)
        status_frame.grid(row=2, column=0, sticky="ew", pady=(0, pad_tight))
        status_frame.columnconfigure(0, weight=1)
        status_frame.columnconfigure(1, weight=1)
        status_frame.columnconfigure(2, weight=1)

        self.scan_toggle_var = tk.BooleanVar(value=False)
        self.scan_toggle_btn = tk.Checkbutton(
            status_frame,
            text="폴더 스캔",
            variable=self.scan_toggle_var,
            state="disabled",
            font=("맑은 고딕", self.ui["font_size"]),
        )
        self.scan_toggle_btn.grid(row=0, column=0, sticky="w")

        self.status_label = tk.Label(
            status_frame, text="생성 완료", font=("맑은 고딕", self.ui["font_size"]), fg="gray"
        )
        self.status_label.grid(row=0, column=1)

        self.credit_label = tk.Label(
            status_frame,
            text="크레딧 확인 중...",
            fg="blue",
            font=("맑은 고딕", self.ui["font_size"]),
            cursor="hand2",
        )
        self.credit_label.grid(row=0, column=2, sticky="e")

        # Buttons (BE 스타일 - 4개)
        button_frame = tk.Frame(left_frame)
        button_frame.grid(row=3, column=0, sticky="ew", pady=(pad_tight, 0))
        button_frame.columnconfigure(0, weight=1)
        button_frame.columnconfigure(1, weight=1)
        button_frame.columnconfigure(2, weight=1)
        button_frame.columnconfigure(3, weight=1)

        self.generate_button = tk.Button(
            button_frame,
            text="QR 생성",
            command=self.start_generation,
            width=12,
            height=1,
            font=("맑은 고딕", self.ui["font_size"]),
        )
        self.generate_button.grid(row=0, column=0, padx=5, sticky="ew")

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

        # 미리보기 (우측) - 정사각형 고정 180px
        preview_frame = tk.LabelFrame(
            right_frame,
            text="미리보기",
            font=("맑은 고딕", self.ui["font_size_bold"], "bold"),
            padx=10,
            pady=10,
        )
        preview_frame.configure(width=180, height=180)
        preview_frame.pack(fill="both", expand=True, pady=(0, 0))
        preview_frame.pack_propagate(False)

        self.preview_label = tk.Label(
            preview_frame,
            text="QR 코드가 여기에 표시됩니다",
            bg="#f0f0f0",
            relief="sunken",
            font=("맑은 고딕", 10),
            fg="#999999",
            anchor="center",
        )
        self.preview_label.pack(fill="both", expand=True)

        # 툴팁 바인딩 (진행률 라벨)
        try:
            self._bind_tooltip(self.progress_bar_label, "진척률: 전체 대비 처리된 개수와 퍼센트를 표시합니다.")
        except Exception:
            pass

    @property
    def admin_password(self) -> str:
        """관리자 비밀번호 (lazy load)"""
        if self._admin_password is None:
            try:
                from wf_settings_common import get_admin_password
                self._admin_password = get_admin_password(self.logger)
            except Exception:
                self._admin_password = "admin2024"  # fallback
        return self._admin_password

    def on_progress_label_click(self, event):
        """진행률 라벨 클릭 이벤트 - 관리자 모드 토글"""
        try:
            if self.is_admin_mode:
                self._exit_admin_mode()
                self.logger.info("관리자 모드가 비활성화되었습니다.")
            else:
                run_mode = getattr(self.config, "run_mode", "release")
                if run_mode == "dev":
                    self._enter_admin_mode()
                    self.logger.info("관리자 모드가 활성화되었습니다. (30분 후 자동 해제)")
                else:
                    from tkinter import simpledialog
                    password = simpledialog.askstring(
                        "관리자 인증", "관리자 비밀번호를 입력하세요:", show="*", parent=self.master
                    )
                    if password is None:
                        return
                    if password == self.admin_password:
                        self._enter_admin_mode()
                        self.logger.info("관리자 모드가 활성화되었습니다. (30분 후 자동 해제)")
                    else:
                        self.logger.warning("관리자 인증 실패 시도")
                        messagebox.showerror("인증 실패", "비밀번호가 올바르지 않습니다.", parent=self.master)
        except Exception as e:
            self.logger.error(f"관리자 모드 토글 오류: {e}")

    def _enter_admin_mode(self):
        """관리자 모드 진입"""
        self.is_admin_mode = True
        self.admin_mode_start_time = datetime.datetime.now()
        self.admin_mode_timer = self.master.after(1800000, self._auto_exit_admin_mode)

        current_geometry = self.master.geometry()
        width = current_geometry.split("x")[0]
        pos = current_geometry.split("+", 1)[1] if "+" in current_geometry else "0+0"
        new_geometry = f"{width}x{self.expanded_window_height}+{pos}"
        self.master.geometry(new_geometry)
        self.master.resizable(True, True)

        self.master.title(f"QR 코드 생성기 {APP_VERSION_FULL} [🔧 관리자 모드]")
        self.progress_bar_label.config(bg="#ffe6e6")

        self.create_log_frame()

        import ctypes
        import getpass

        def write_to_log(msg):
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

    def _exit_admin_mode(self):
        """관리자 모드 종료"""
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

        self.master.resizable(True, True)
        self.master.title(f"QR 코드 생성기 {APP_VERSION_DISPLAY}")
        self.progress_bar_label.config(bg=self.master.cget("bg"))
        self.progress_bar["value"] = 0
        self.spinner_label.config(text="○", fg="#cccccc")

    def _auto_exit_admin_mode(self):
        """30분 후 자동 관리자 모드 종료"""
        self._exit_admin_mode()

    def create_log_frame(self):
        """관리자 모드용 로그 프레임 생성"""
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

        log_header_frame = tk.Frame(self.log_frame)
        log_header_frame.pack(fill="x", pady=(0, 5))

        log_label = tk.Label(
            log_header_frame, text="실시간 로그 (DEBUG 레벨)", font=("맑은 고딕", 13, "bold")
        )
        log_label.pack(side="left")

        self.auto_scroll_var = tk.BooleanVar(value=True)
        self.auto_scroll_checkbox = tk.Checkbutton(
            log_header_frame,
            text="자동 스크롤",
            variable=self.auto_scroll_var,
            font=("맑은 고딕", self.ui.get("font_size", 14)),
        )
        self.auto_scroll_checkbox.pack(side="right")

        log_text_frame = tk.Frame(self.log_frame)
        log_text_frame.pack(fill="both", expand=True)

        self.log_scrollbar = tk.Scrollbar(log_text_frame)
        self.log_scrollbar.pack(side="right", fill="y")

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

        self.setup_log_handler()

    def destroy_log_frame(self):
        """로그 프레임 제거"""
        if self.log_frame:
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
                    self.master.after(0, lambda: self._append_log(msg))
                except Exception:
                    pass

            def _append_log(self, msg):
                try:
                    if self.text_widget and self.text_widget.winfo_exists():
                        self.text_widget.config(state="normal")
                        self.text_widget.insert("end", msg + "\n")
                        lines = int(self.text_widget.index("end-1c").split(".")[0])
                        if lines > 1000:
                            self.text_widget.delete("1.0", "500.0")
                        self.text_widget.config(state="disabled")
                        if self.auto_scroll_var and self.auto_scroll_var.get():
                            self.text_widget.see("end")
                except Exception:
                    pass

        self.remove_log_handler()

        self.text_log_handler = TextHandler(self.log_text, self.auto_scroll_var, self.master)
        self.text_log_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        self.text_log_handler.setFormatter(formatter)

        root_logger = logging.getLogger()
        root_logger.addHandler(self.text_log_handler)

        if self.logger:
            self.logger.addHandler(self.text_log_handler)

    def remove_log_handler(self):
        """로그 핸들러 제거"""
        if hasattr(self, "text_log_handler"):
            try:
                import logging
                root_logger = logging.getLogger()
                root_logger.removeHandler(self.text_log_handler)
                if self.logger:
                    self.logger.removeHandler(self.text_log_handler)
                delattr(self, "text_log_handler")
            except Exception:
                pass

    def _on_window_resize(self, event):
        """창 크기 변경 시 adaptive 패딩 재계산 및 적용"""
        if event.widget != self.master:
            return
        
        # 기존 패딩 값 저장
        old_pady = getattr(self, 'adaptive_pady', None)
        
        # 새로운 패딩 계산
        self._calculate_adaptive_padding()
        
        # 패딩이 변경된 경우에만 UI 업데이트
        if old_pady and old_pady == self.adaptive_pady:
            return
        
        # 모든 pack된 위젯의 패딩 업데이트는 성능 이슈로 생략
        # 대신 다음 재생성 시 자동 적용됨

    # ---------- Generation ----------
    def start_generation(self):
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("입력 오류", "URL을 입력해주세요.", parent=self.master)
            self.url_entry.focus_set()
            return

        if self.is_generating:
            return

        # URL 저장
        try:
            if hasattr(self.config, 'update_last_url'):
                self.config.update_last_url(url)
        except Exception:
            pass

        # 크레딧 확인
        if self.credit_manager:
            try:
                status = self.credit_manager.get_credit_status()
                remaining = status.get("remaining_credits", 0)
                cost = getattr(self.config, 'credit_per_work', 1)
                if remaining != -1 and remaining < cost:
                    msg = build_credit_shortage_init_message(remaining, cost, 1)
                    messagebox.showwarning("크레딧 부족", msg, parent=self.master)
                    return
            except Exception as e:
                self.logger.warning(f"크레딧 확인 실패(계속 진행): {e}")

        self.is_generating = True
        self.generate_button.config(state="disabled")
        self.status_label.config(text="생성 중...")
        self.progress_bar["value"] = 0
        self._start_spinner()

        def _worker():
            try:
                from automation import QRCodeGenerator

                generator = QRCodeGenerator(
                    config=self.config,
                    log_callback=lambda msg: self.master.after(0, lambda m=msg: self.status_label.config(text=m))
                )
                generator.progress_callback = lambda v: self.master.after(0, self._update_progress, v)
                generator.credit_manager = self.credit_manager

                result_path = generator.generate_qr_code(url)

                self.master.after(0, self._on_generation_complete, result_path)
            except Exception as e:
                self.logger.error(f"QR 생성 스레드 오류: {e}")
                self.master.after(0, self._on_generation_complete, "")

        threading.Thread(target=_worker, daemon=True).start()

    def _update_progress(self, value):
        try:
            self.progress_bar["value"] = value
        except Exception:
            pass

    def _on_generation_complete(self, result_path: str):
        self._stop_spinner()
        self.is_generating = False
        self.generate_button.config(state="normal")

        if result_path:
            self.status_label.config(text="생성 완료")
            self.progress_bar["value"] = 100

            # 크레딧 차감
            if self.credit_manager:
                try:
                    cost = getattr(self.config, 'credit_per_work', 1)
                    self.credit_manager.deduct_credits(cost)
                    self.update_credit_display()
                except Exception as e:
                    self.logger.warning(f"크레딧 차감 실패: {e}")

            # 미리보기 업데이트
            self.update_preview(result_path)
        else:
            self.status_label.config(text="생성 실패")
            self.progress_bar["value"] = 0

    def update_preview(self, image_path: str):
        """생성된 QR 코드 이미지를 미리보기 패널에 표시"""
        try:
            from PIL import Image, ImageTk

            img = Image.open(image_path)

            # 미리보기 영역 크기에 맞게 리사이즈 (비율 유지)
            self.preview_label.update_idletasks()
            label_w = self.preview_label.winfo_width()
            label_h = self.preview_label.winfo_height()
            if label_w <= 1 or label_h <= 1:
                label_w, label_h = 200, 200
            max_size = max(80, min(label_w, label_h))
            img.thumbnail((max_size, max_size), Image.LANCZOS)

            photo = ImageTk.PhotoImage(img)
            self.preview_label.config(image=photo, text="", bg="white")
            self.preview_image = photo  # 참조 유지 (GC 방지)
        except Exception as e:
            self.logger.warning(f"미리보기 업데이트 실패: {e}")
            self.preview_label.config(text="미리보기\n로드 실패", image="")

    # ---------- Spinner ----------
    def _start_spinner(self):
        self.spinner_running = True
        self.spinner_index = 0
        self._animate_spinner()

    def _stop_spinner(self):
        self.spinner_running = False
        self.spinner_label.config(text="")

    def _animate_spinner(self):
        if not self.spinner_running:
            return
        self.spinner_label.config(text=self.spinner_chars[self.spinner_index])
        self.spinner_index = (self.spinner_index + 1) % len(self.spinner_chars)
        self.master.after(100, self._animate_spinner)

    # ---------- Registration / Credit ----------
    def update_registration_button(self):
        try:
            if getattr(self, "settings_button", None):
                if self.is_registered_user:
                    self.settings_button.config(text="설 정", command=self.open_settings_window)
                else:
                    self.settings_button.config(text="등 록", command=self.open_registration_window)
        except Exception:
            pass

    def update_credit_display(self):
        """크레딧 표시 업데이트 (BE/CV 스타일 - 무료 앱 이모지)"""
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
            try:
                self._bind_tooltip(self.credit_label, tip)
            except Exception:
                pass

        except Exception as e:
            self.credit_label.config(text="표시 오류", fg="red")
            self.logger.error(f"크레딧 표시 오류: {e}")

    def on_refresh_credit(self):
        """업데이트 버튼 클릭 시 크레딧/정책 동기화 (무료 앱 포함)"""
        if not self.credit_manager:
            messagebox.showinfo("업데이트", "크레딧 정보를 불러올 수 없습니다.")
            return
        try:
            # 유료 앱: 구매 이력 동기화
            popup_messages = []
            if hasattr(self.credit_manager, "pull_and_apply_purchases"):
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

            # 정책 동기화 (백그라운드)
            try:
                from wf_settings_common import sync_policies_from_sheets
                policy_result = sync_policies_from_sheets("qrcode_generator", self.logger)
                if not policy_result.get("success"):
                    self.logger.warning(f"정책 동기화 실패: {policy_result.get('message')}")
            except Exception as e:
                self.logger.warning(f"정책 동기화 중 오류 (무시): {e}")

            self.update_credit_display()
            
            if popup_messages:
                messagebox.showinfo("업데이트", "\n".join(popup_messages))
            else:
                messagebox.showinfo("업데이트", "크레딧/정책 정보가 갱신되었습니다.")
                
        except Exception as e:
            self.logger.error(f"크레딧 업데이트 실패: {e}")
            messagebox.showerror("오류", f"크레딧 정보를 갱신할 수 없습니다:\n{e}")

    def open_settings_window(self):
        try:
            from ui_setting import create_settings_window
            create_settings_window(self.master, self.config, self.icon_path)
            # 설정 변경 후 config 리로드
            self.config = get_config(reload=True)
        except Exception as e:
            self.logger.error(f"설정 창 열기 실패: {e}")
            messagebox.showerror("오류", f"설정 창을 열 수 없습니다: {e}", parent=self.master)

    def open_registration_window(self):
        if create_trial_window:
            try:
                create_trial_window(
                    self.master,
                    app_name="qrcode_generator",
                    wf_manager=self.wf_manager,
                    on_success=self._on_registration_success,
                )
            except Exception as e:
                self.logger.error(f"등록 창 열기 실패: {e}")
                messagebox.showerror("오류", f"등록 창을 열 수 없습니다: {e}", parent=self.master)
        else:
            messagebox.showerror("오류", "등록 모듈을 찾을 수 없습니다.", parent=self.master)

    def _on_registration_success(self):
        self.is_registered_user = True
        self.update_registration_button()
        self.master.after(500, self._lazy_init_managers)

    # ---------- Managers ----------
    def _lazy_init_managers(self):
        def _worker():
            try:
                if self._wfm_available and WorksFreeManager and not self.wf_manager:
                    self.wf_manager = WorksFreeManager()
                    self.is_registered_user = self.wf_manager.is_registered()
                    self.logger.info(f"[INIT] WorksFreeManager 초기화 완료 (등록사용자: {self.is_registered_user})")
                    try:
                        self.master.after(0, self.update_registration_button)
                    except Exception:
                        pass

                if CreditManager and self.wf_manager:
                    self.credit_manager = init_credit_and_policy_managers(
                        app_name="qrcode_generator",
                        wf_manager=self.wf_manager,
                        master=self.master,
                        logger=self.logger,
                        recovery_delay_ms=700,
                        policy_delay_ms=400,
                    )
                    self.master.after(0, self.update_credit_display)

            except Exception as e:
                if self.logger:
                    self.logger.error(f"매니저 초기화 중 오류: {e}", exc_info=True)

        threading.Thread(target=_worker, daemon=True).start()

    def create_user_directories(self):
        user_home = os.path.expanduser("~")
        wf_rpa_dir = os.path.join(user_home, ".wf_rpa")
        app_dir = os.path.join(wf_rpa_dir, "qrcode_generator")

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
            if self.logger:
                self.logger.error(f"[ERROR] 디렉토리 생성 실패: {e}")

    # ==================== WF-ACT Test Mode ====================
    def _init_credit_manager_sync(self):
        """WF-ACT 테스트 모드용: CreditManager를 동기적으로 초기화"""
        try:
            if self._wfm_available and WorksFreeManager and not self.wf_manager:
                self.wf_manager = WorksFreeManager()
                self.is_registered_user = self.wf_manager.is_registered()
            if CreditManager and self.wf_manager and not self.credit_manager:
                self.credit_manager = init_credit_and_policy_managers(
                    app_name="qrcode_generator",
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

    def init_test_server(self):
        """WF-ACT 인증 테스트용 TestServer 초기화"""
        try:
            # WF-ACT: Sync init credit manager before test server starts
            self._init_credit_manager_sync()

            # TestServer import (로커 test_server.py 사용)
            from test_server import TestServer
            self.test_server = TestServer(app_name="qrcode_generator")
            self.test_server.register_handlers({
                'get_credits': self._test_get_credits,
                'set_credits': self._test_set_credits,
                'add_credits': self._test_add_credits,
                'get_credit_status': self._test_get_credit_status,
                'get_trial_info': self._test_get_trial_info,
                'get_registration_status': self._test_get_registration_status,
                'register': self._test_register,
                'clear_registration': self._test_clear_registration,
                'sync_registration': self._test_sync_registration,
                'simulate_work': self._test_simulate_work,
                'get_state': self._test_get_state,
                'get_ui_state': self._test_get_state,  # Alias for cert tests
                'get_policy': self._test_get_policy,
                'get_settings': self._test_get_settings,
                'save_settings': self._test_save_settings,
                'load_settings': self._test_load_settings,
                'reload_config': self._test_reload_config,
                'get_button_state': self._test_get_button_state,
                'click_button': self._test_click_button,
            })
            self.test_server.start()
            self.logger.info("[WF-ACT] Test server started on port " + str(self.test_server.port))
        except Exception as e:
            self.logger.error(f"[WF-ACT] Failed to initialize test server: {e}")
            raise

    def _test_get_credits(self) -> int:
        if not self.credit_manager:
            return 0
        try:
            data = self.credit_manager._load_credit_data()
            rt, rp = data.get("remaining_trial", 0), data.get("remaining_purchased", 0)
            return -1 if rt == -1 or rp == -1 else rt + rp
        except Exception:
            return self.credit_manager.get_credit_status().get("remaining_credits", 0)

    def _test_set_credits(self, amount: int, credit_type: str = "trial") -> bool:
        if not self.credit_manager or amount is None or amount < 0:
            return False
        try:
            data = self.credit_manager._load_credit_data()
            if credit_type == "purchased":
                data["remaining_purchased"], data["remaining_trial"] = amount, 0
            else:
                data["remaining_trial"], data["remaining_purchased"] = amount, 0
            if amount == 0:
                data.setdefault("usage_history", []).append({"timestamp": "2000-01-01T00:00:00", "credits_used": 0, "operation": "wf_act_test_marker"})
            self.credit_manager._save_credit_data(data)
            self.master.after(0, self.update_credit_display)
            return True
        except Exception:
            return False

    def _test_add_credits(self, amount: int) -> bool:
        if not self.credit_manager:
            return False
        try:
            data = self.credit_manager._load_credit_data()
            if data.get("remaining_purchased", 0) != -1:
                data["remaining_purchased"] = data.get("remaining_purchased", 0) + amount
            self.credit_manager._save_credit_data(data)
            self.master.after(0, self.update_credit_display)
            return True
        except Exception:
            return False

    def _test_get_credit_status(self) -> dict:
        return self.credit_manager.get_credit_status() if self.credit_manager else {"error": "not_initialized"}

    def _test_get_trial_info(self) -> dict:
        if not self.credit_manager:
            return {"error": "not_initialized"}
        policy = self.credit_manager.policy or {}
        data = self.credit_manager._load_credit_data()
        return {"initial_credits": policy.get("trial_credits", 100), "remaining_trial": data.get("remaining_trial", 0), "trial_credits": policy.get("trial_credits", 100)}

    def _test_get_registration_status(self) -> dict:
        if not self.wf_manager:
            return {"is_registered": False, "email": None}
        ui = self.wf_manager.get_user_info()
        return {"is_registered": self.wf_manager.is_registered(), "email": ui.get("user_email") or ui.get("email"), "registered_at": ui.get("reg_time_local"), "app_version": APP_VERSION_FULL}

    def _test_register(self, email: str) -> dict:
        if not self.wf_manager:
            return {"success": False, "error": "not_initialized"}
        try:
            try:
                from wf_hwinfo import HardwareInfo
                hw_fp = HardwareInfo().fingerprint
            except Exception:
                hw_fp = "test_" + email.split("@")[0]
            success = self.wf_manager.register_user(user_email=email, hw_fingerprint=hw_fp, user_name="Test", user_phone="", user_email_consent="Y")
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
        if not self.wf_manager:
            return False
        try:
            config = self.wf_manager.load_config()
            config["user_info"] = {"is_registered": False, "user_email": None, "reg_time_local": None, "reg_time_utc": None}
            self.wf_manager.save_config(config)
            self.is_registered_user = False
            self.master.after(0, self.update_registration_button)
            return True
        except Exception:
            return False

    def _test_sync_registration(self) -> dict:
        return {"success": True, "message": "sync_attempted"} if self.wf_manager else {"success": False, "error": "not_initialized"}

    def _test_simulate_work(self, file_count: int = 1) -> dict:
        if not self.credit_manager:
            return {"success": False, "error": "not_initialized"}
        cost = self.credit_manager.policy.get("credit_per_work", 1)
        try:
            data = self.credit_manager._load_credit_data()
            rt, rp = data.get("remaining_trial", 0), data.get("remaining_purchased", 0)
            if rt == -1 or rp == -1:
                return {"success": True, "processed_count": file_count, "blocked": False}
            current = rt + rp
        except Exception as e:
            return {"success": False, "error": str(e)}
        processed = 0
        for _ in range(file_count):
            if current < cost:
                return {"success": False, "blocked": True, "processed_count": processed, "exhausted": True, "remaining_credits": current}
            data = self.credit_manager._load_credit_data()
            t, p = data.get("remaining_trial", 0), data.get("remaining_purchased", 0)
            if p >= cost:
                data["remaining_purchased"] = p - cost
            elif t >= cost:
                data["remaining_trial"] = t - cost
            else:
                data["remaining_purchased"], data["remaining_trial"] = 0, t - (cost - p)
            self.credit_manager._save_credit_data(data)
            processed += 1
            current = data.get("remaining_trial", 0) + data.get("remaining_purchased", 0)
        self.master.after(0, self.update_credit_display)
        return {"success": True, "processed_count": processed, "blocked": False, "remaining_credits": current}

    def _test_get_state(self) -> dict:
        # 크레딧 표시 텍스트 가져오기
        credits_display = None
        try:
            if hasattr(self, 'credit_label') and self.credit_label:
                credits_display = self.credit_label.cget("text")
        except Exception:
            pass

        return {
            "is_registered": self.is_registered_user,
            "has_credit_manager": self.credit_manager is not None,
            "credits_display": credits_display
        }

    def _test_get_policy(self) -> dict:
        p = dict(self.credit_manager.policy) if self.credit_manager else {}
        return {"identity": {"app_name": "qrcode_generator", "display_name": "QRCode Generator"}, "policy": {"credit_per_work": p.get("credit_per_work", 1), "trial_credits": p.get("trial_credits", 100)}, "app_name": "qrcode_generator", **p}

    def _test_get_settings(self) -> dict:
        return {"app_name": "qrcode_generator", "run_mode": getattr(self.config, "run_mode", "release"), "full_version": APP_VERSION_FULL, "version": APP_VERSION_FULL}

    def _test_reload_config(self) -> bool:
        """설정 및 정책 재로드 (테스트용)"""
        try:
            if self.credit_manager:
                self.credit_manager._reload_policy()
            return True
        except Exception:
            return False

    def _test_save_settings(self, settings: dict) -> dict:
        try:
            import json
            sf = self.config.settings_file
            data = json.load(open(sf, "r", encoding="utf-8")) if sf.exists() else {}
            data.setdefault("test_config", {}).update(settings)
            json.dump(data, open(sf, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _test_load_settings(self) -> dict:
        try:
            import json
            sf = self.config.settings_file
            data = json.load(open(sf, "r", encoding="utf-8")) if sf.exists() else {}
            return {"app_config": data.get("app_config", {}), "test_config": data.get("test_config", {})}
        except Exception as e:
            return {"error": str(e)}

    def _test_get_button_state(self, button_name: str) -> dict:
        bmap = {"work": getattr(self, "generate_button", None), "register": getattr(self, "register_button", None), "settings": getattr(self, "settings_button", None)}
        btn = bmap.get(button_name)
        return {"exists": True, "state": str(btn.cget("state")), "text": str(btn.cget("text"))} if btn else {"exists": False}

    def _test_click_button(self, button_name: str) -> bool:
        bmap = {"work": getattr(self, "generate_button", None), "register": getattr(self, "register_button", None), "settings": getattr(self, "settings_button", None)}
        btn = bmap.get(button_name)
        if btn and str(btn.cget("state")) != "disabled":
            btn.invoke()
            return True
        return False

    # ---------- Window ----------
    def on_closing(self):
        # WF-ACT 테스트 서버 정리
        try:
            if hasattr(self, "test_server") and self.test_server:
                self.test_server.stop()
        except Exception:
            pass
        try:
            _clear_cross_app_running()
        except Exception:
            pass
        try:
            self.master.destroy()
        except Exception:
            pass


def main():
    global _instance_mutex_handle
    # --test-mode 인자 처리 (WF-ACT 인증 테스트 모드)
    test_mode = "--test-mode" in sys.argv

    _log_startup("main() called")

    is_first, _instance_mutex_handle = _acquire_single_instance()
    _log_startup("single instance check complete")
    if not is_first:
        try:
            print("Another qrcode_generator instance is already running. Exiting.")
        except Exception:
            pass
        return

    if check_cross_app_running_and_exit:
        check_cross_app_running_and_exit("qrcode_generator")
    try:
        _set_cross_app_running("qrcode_generator")
    except Exception:
        pass
    try:
        import atexit
        atexit.register(_clear_cross_app_running)
    except Exception:
        pass

    root = tk.Tk()
    root.withdraw()

    # 작업표시줄 아이콘 설정 (개발/릴리스 환경 모두 지원)
    try:
        # 아이콘 파일명 (새 아이콘: 07_QRCode_Generator.ico)
        icon_names = ["07_QRCode_Generator.ico"]

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

    # res 시드
    try:
        try:
            cfg = get_config()
            run_mode = getattr(cfg, "run_mode", "release")
        except Exception:
            cfg, run_mode = None, "release"
        target_res = (
            Path(__file__).parent / "res"
            if run_mode in ("dev", "demo")
            else Path.home() / ".wf_rpa" / "qrcode_generator" / "res"
        )
        bundle_candidates = [Path(__file__).parent / "res"]
        if getattr(sys, "frozen", False):
            exe_dir = Path(sys.executable).parent
            bundle_candidates = [exe_dir / "res", exe_dir / "_internal" / "res"] + bundle_candidates
        seed_res_if_missing(target_res, bundle_candidates, logger=None)
    except Exception:
        pass

    app = QRCodeGeneratorApp(root)
    _log_startup("App init complete")

    # WF-ACT 테스트 모드 초기화
    if test_mode:
        try:
            app.init_test_server()
        except Exception as e:
            print(f"[WF-ACT] Failed to initialize test server: {e}")

    root.deiconify()

    _flush_startup_log()
    root.mainloop()


if __name__ == "__main__":
    main()
