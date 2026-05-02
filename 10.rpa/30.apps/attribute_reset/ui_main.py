# -*- coding: utf-8 -*-
"""
Attribute Reset Main UI Module
"""
import sys
import os
import json
import time

# Windows 콘솔 UTF-8 강제 설정 (GUI 모드에서는 stdout/stderr가 None일 수 있음)
if sys.platform == "win32":
    import io
    if sys.stdout is not None and hasattr(sys.stdout, 'buffer'):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    if sys.stderr is not None and hasattr(sys.stderr, 'buffer'):
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from pathlib import Path


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
        path = Path.home() / ".wf_rpa" / "attribute_reset" / "startup_profile.log"
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    return path


def _log_startup(msg: str):
    if not _STARTUP_ENABLED:
        return
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
                f.write(f"[{(t-base_time)*1000:7.1f}ms] {m}\n")
    except Exception:
        pass

    _STARTUP_FLUSHED = True


_log_startup("module_start")


_log_startup("pathlib_imported")


# ==================== 싱글 인스턴스 락 ====================
_instance_mutex_handle = None


def _acquire_single_instance(mutex_name: str = r"Global\\WF_ATTRIBUTE_RESET"):
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
    """Mark this app as running in shared config (cross-app guard)"""
    try:
        import json as _json
        import datetime as _dt

        cfg_dir = Path.home() / ".wf_rpa"
        cfg_dir.mkdir(parents=True, exist_ok=True)
        cfg = cfg_dir / "wf_rpa_config.json"
        data = {}
        if cfg.exists():
            try:
                with open(cfg, "r", encoding="utf-8") as _f:
                    data = _json.load(_f) or {}
            except Exception:
                data = {}

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
    """Clear cross-app running status on exit"""
    try:
        import json as _json

        cfg = Path.home() / ".wf_rpa" / "wf_rpa_config.json"
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


# ==================== 버전 정보 로드 ====================
def _load_version_info():
    """settings.json에서 버전 정보 읽기 (개발/릴리스 모두 지원)

    ⚠️ 버전 정보 단일 소스: settings.json의 runtime_config.full_version만 사용
    - MECE 원칙: runtime_config에만 버전 정보 저장
    """
    default_full = "v1.0.0.0"
    full_version = default_full

    try:
        if getattr(sys, "frozen", False):
            # 릴리스 모드: 번들 버전 우선 (정확한 빌드 버전), fallback으로 사용자 홈
            base_path = Path(sys._MEIPASS) if hasattr(sys, '_MEIPASS') else Path(sys.executable).parent
            settings_file = base_path / ".wf_rpa" / "attribute_reset" / "settings.json"

            # fallback: 사용자 홈 (버전 정보가 없을 수 있음)
            if not settings_file.exists():
                settings_file = Path.home() / ".wf_rpa" / "attribute_reset" / "settings.json"
        else:
            # 개발 모드: 10.common/config/attribute_reset/settings.json (통합 경로)
            app_root = Path(__file__).parent
            settings_file = app_root.parent.parent / "10.common" / "config" / "attribute_reset" / "settings.json"
            # fallback: 앱 폴더의 config
            if not settings_file.exists():
                settings_file = app_root / "config" / "attribute_reset" / "settings.json"

        if settings_file.exists():
            with open(settings_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                app_config = data.get("app_config", {})
                runtime_config = data.get("runtime_config", {})
                full_version = app_config.get("full_version") or runtime_config.get("full_version", default_full)
                if not full_version.startswith("v"):
                    full_version = "v" + full_version
    except Exception:
        pass

    # display_version은 앞 2자리만 (v1.0.0.0 → v1.0)
    parts = full_version.lstrip("v").split(".")
    display_version = "v" + ".".join(parts[:2])

    return full_version, display_version


APP_VERSION_FULL, APP_VERSION_DISPLAY = _load_version_info()
_log_startup("version_loaded")

import threading
import datetime
import ctypes
_log_startup("stdlib_imported")
import tkinter as tk
import tkinter.ttk as ttk
from tkinter import filedialog, messagebox, simpledialog
_log_startup("tkinter_imported")

# Ensure paths are set up correctly
current_dir = Path(__file__).resolve().parent
common_path = current_dir.parent.parent / "10.common"
if common_path.exists() and str(common_path) not in sys.path:
    sys.path.insert(0, str(common_path))

# Local and common imports
from app_setting_data import get_config
_log_startup("app_setting_data_imported")
from automation import AttributeResetAutomation
_log_startup("automation_imported")
import ui_setting
_log_startup("ui_setting_imported")

try:
    from wf_log import get_app_logger
    _log_startup("wf_log_imported")
    from wf_credit_manager import WorksFreeManager, CreditManager
    _log_startup("wf_credit_manager_imported")
    from wf_app_init_helpers import init_credit_and_policy_managers
    _log_startup("wf_app_init_helpers_imported")
    from wf_register import create_trial_window
    from wf_ui_adaptive import get_adaptive_ui_settings, apply_global_fonts, apply_equal_vertical_pack
    _log_startup("wf_register_imported")
    WFM_AVAILABLE = True
except ImportError as e:
    import logging
    logging.basicConfig(level=logging.DEBUG)
    get_app_logger = lambda name, **kwargs: logging.getLogger(name)
    messagebox.showerror("Critical Error", f"Failed to import common modules: {e}")
    WFM_AVAILABLE = False
    sys.exit(1)


class AttributeResetGUI:
    # 버전 정보를 클래스 변수로도 저장 (설정창에서 접근용)
    APP_VERSION_FULL = APP_VERSION_FULL
    APP_VERSION_DISPLAY = APP_VERSION_DISPLAY

    def __init__(self, master):
        self.master = master
        self.config = get_config()
        self.logger = get_app_logger("attribute_reset")

        # 아이콘 경로 저장 (등록창/설정창에서 사용)
        self.icon_path = self._find_icon_path()

        # DPI 기반 적응형 UI 설정 로드 (메인 창용)
        self.ui = get_adaptive_ui_settings(window_type="main")

        self.automation = None
        # DC 패턴: 폴더 + 다중 엑셀 선택
        self.SELECTED_FOLDER = None
        self.selected_excel_files = []
        self.excel_path = None  # 하위 호환용 (기존 automation과 연동)
        self.is_registered_user = False
        self.wf_manager = None
        self.credit_manager = None
        # 🚀 최적화: admin 비밀번호 lazy 로딩 (Google Sheets 호출 지연)
        self._admin_password = None  # lazy load

        # 관리자 모드 변수
        self.is_admin_mode = False
        self.admin_mode_timer = None  # 30분 자동 복귀 타이머
        self.admin_mode_start_time = None

        # 로그 창 관련 변수
        self.log_frame = None
        self.log_text = None
        self.log_scrollbar = None
        self.auto_scroll_var = None
        self.auto_scroll_checkbox = None

        # 창 크기: adaptive UI 기반
        self.original_window_height = self.ui.get('window_height', getattr(self.config, 'window_height', 320))  # 2입력 앱 기본 높이
        self.expanded_window_height = self.original_window_height + getattr(self.config, "admin_window_height", 300)  # 관리자 모드: settings.json에서 로드

        if WFM_AVAILABLE:
            self.wf_manager = WorksFreeManager()
            self.is_registered_user = self.wf_manager.is_registered()

        self.master.title(f"속성 리셋 {APP_VERSION_DISPLAY}")
        self.master.protocol("WM_DELETE_WINDOW", self.on_closing)
        if self.config.ui_config.topmost:
            self.master.wm_attributes("-topmost", 1)

        self.init_ui()

        # 위젯 생성 후 최종 크기/위치 설정 및 창 표시
        self._finalize_window_and_show()

        self.master.after(100, self._lazy_init_managers)

        # 키보드 단축키 바인딩 (다른 앱과 일관성)
        self._bind_keyboard_shortcuts()

    def _find_icon_path(self):
        """앱 아이콘 경로 찾기 (개발/릴리스 환경 모두 지원)"""
        try:
            icon_names = ["05_Attribute_Reset.ico", "AR.ico"]
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
        master = self.master

        # 적응형 UI 글꼴 적용 (위젯 생성 전에 tk scaling 1.0 설정 필수)
        apply_global_fonts(self.master, self.ui)

        # Grid로 루트 윈도우 설정하여 상하좌우 여백 균등 분배
        master.grid_rowconfigure(0, weight=1)
        master.grid_columnconfigure(0, weight=1)

        main_frame = tk.Frame(master, padx=12, pady=0)
        main_frame.grid(row=0, column=0, sticky="nsew")

        # Folder frame (DC 패턴)
        folder_frame = tk.Frame(main_frame)
        folder_frame.pack(fill="x", pady=(6, 6))

        self.folder_button = tk.Button(
            folder_frame,
            text="폴더 선택",
            width=10,
            command=self.select_folder,
            font=("맑은 고딕", self.ui["font_size"]),
        )
        self.folder_button.pack(side="left")

        self.folder_entry = tk.Entry(
            folder_frame, state="readonly", font=("맑은 고딕", self.ui["font_size"])
        )
        self.folder_entry.pack(side="left", fill="x", expand=True, padx=(10, 0))

        # Excel frame (DC 패턴 - Listbox로 다중 선택)
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
            progress_frame, text="진행률:", width=11, font=("맑은 고딕", self.ui["font_size"]), cursor="hand2"
        )
        self.progress_bar_label.pack(side="left")
        self.progress_bar_label.bind("<Button-1>", self.on_progress_label_click)

        self.progress_bar = ttk.Progressbar(
            progress_frame, orient="horizontal", mode="determinate", maximum=100
        )
        self.progress_bar.pack(side="left", fill="x", expand=True, padx=(10, 0))

        # Status frame
        status_frame = tk.Frame(main_frame)
        status_frame.pack(fill="x", pady=(0, 6))
        status_frame.columnconfigure(0, weight=1)
        status_frame.columnconfigure(1, weight=1)
        status_frame.columnconfigure(2, weight=1)

        self.scan_toggle_var = tk.BooleanVar(value=False)
        self.scan_toggle_btn = tk.Checkbutton(
            status_frame,
            text="폴더 스캔",
            variable=self.scan_toggle_var,
            command=self.on_scan_toggle,
            font=("맑은 고딕", self.ui["font_size"]),
        )
        self.scan_toggle_btn.grid(row=0, column=0, sticky="w")

        self.status_label = tk.Label(
            status_frame, text="0/0", font=("맑은 고딕", self.ui["font_size"])
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

        # Buttons
        button_frame = tk.Frame(main_frame)
        button_frame.pack(fill="x", pady=(12, 12))
        button_frame.columnconfigure(0, weight=1)
        button_frame.columnconfigure(1, weight=1)
        button_frame.columnconfigure(2, weight=1)
        button_frame.columnconfigure(3, weight=1)

        self.start_button = tk.Button(
            button_frame,
            text="시작",
            command=self.start_automation,
            width=12,
            height=1,
            state="disabled",
            font=("맑은 고딕", self.ui["font_size"]),
        )
        self.start_button.grid(row=0, column=0, padx=5, sticky="ew")

        self.settings_button = tk.Button(
            button_frame,
            text="설정",
            command=self.open_settings_window,
            width=12,
            height=1,
            font=("맑은 고딕", self.ui["font_size"]),
        )
        self.settings_button.grid(row=0, column=1, padx=5, sticky="ew")
        self.update_registration_button()

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
            text="종료",
            command=self.on_closing,
            width=12,
            height=1,
            font=("맑은 고딕", self.ui["font_size"]),
        )
        self.exit_button.grid(row=0, column=3, padx=5, sticky="ew")

        # 상하 등간 배치 (adaptive)
        apply_equal_vertical_pack(main_frame)

    def _finalize_window_and_show(self):
        """위젯 생성 후 최종 크기/위치 설정 및 창 표시 (깜빡임 방지)"""
        self.master.update_idletasks()

        # 위젯이 필요로 하는 크기 계산
        req_width = self.master.winfo_reqwidth()
        req_height = self.master.winfo_reqheight()

        # 앱별 고정 창 크기 (settings.json이 아닌 코드에서 정의)
        app_width = 580  # attribute_reset 고유 너비
        app_height = 200  # attribute_reset 고유 높이
        final_width = max(app_width, req_width)
        final_height = max(app_height, req_height)

        # 화면 중앙 위치 계산
        screen_width = self.master.winfo_screenwidth()
        screen_height = self.master.winfo_screenheight()
        x_coord = int((screen_width - final_width) / 2)
        y_coord = int((screen_height - final_height) / 2)

        # 최종 geometry 설정
        self.master.geometry(f"{final_width}x{final_height}+{x_coord}+{y_coord}")

        # 최소 크기를 기본 크기로 설정 (req_width=580, req_height=200)
        self.master.minsize(req_width, req_height)

        # 창 표시
        self.master.deiconify()

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

    def _lazy_init_managers(self):
        def _worker():
            if self.wf_manager and CreditManager:
                self.credit_manager = init_credit_and_policy_managers(
                    app_name="attribute_reset",
                    wf_manager=self.wf_manager,
                    master=self.master,
                    logger=self.logger,
                )
                self.master.after(0, self.update_credit_display)
        
        threading.Thread(target=_worker, daemon=True).start()

    def update_registration_button(self):
        if self.is_registered_user:
            self.settings_button.config(text="설정", command=self.open_settings_window)
        else:
            self.settings_button.config(text="등록", command=self.open_registration_window)

    def open_settings_window(self):
        ui_setting.create_settings_window(self.master, self)

    def open_registration_window(self):
        """등록 창 열기 (미등록 사용자용)"""

        # 등록 모듈이 없는 경우 처리
        if create_trial_window is None:
            self.logger.error("등록 모듈을 찾을 수 없어 사용자 등록을 진행할 수 없습니다. 관리자에게 문의하세요.")
            self._show_messagebox(
                "showerror",
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
            self.logger.error(f"하드웨어 정보 수집 실패: {e}")
            hardware_info = {"오류": "하드웨어 정보를 가져올 수 없습니다"}

        # 등록 창을 모달로 열고, 닫힐 때까지 대기
        if not callable(create_trial_window):
            self.logger.error("등록 창 함수를 호출할 수 없습니다. 관리자에게 문의하세요.")
            self._show_messagebox(
                "showerror",
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
            if self.config.ui_config.topmost:
                toplevel_window.wm_attributes("-topmost", 1)
            toplevel_window.focus_set()  # 포커스 설정
            self.master.wait_window(toplevel_window)  # 창이 닫힐 때까지 대기

        # 등록 창이 닫힌 후, 상태를 다시 확인하고 UI를 업데이트
        self.post_registration_update()

    def post_registration_update(self):
        """등록 절차 완료 후 UI를 업데이트합니다."""
        if self.wf_manager:
            self.is_registered_user = self.wf_manager.is_registered()
            self.update_registration_button()
            if self.is_registered_user:
                self.update_credit_display()  # 크레딧 정보도 갱신

    def on_refresh_credit(self):
        if not self.credit_manager:
            self._show_messagebox("showerror", "Error", "Credit manager is not initialized.")
            return
        result = self.credit_manager.pull_and_apply_purchases()
        if result.get("success"):
            added = result.get("added", 0)
            if added > 0:
                self._show_messagebox("showinfo", "Success", f"{added} credits have been added.")
            else:
                self._show_messagebox("showinfo", "Info", "No new purchases found.")
        else:
            self._show_messagebox("showerror", "Error", f"Failed to refresh credits: {result.get('message')}")
        self.update_credit_display()
        
    def update_credit_display(self):
        if not self.credit_manager:
            self.credit_label.config(text="⚠ 크레딧 확인 불가", fg="gray")
            return
        status = self.credit_manager.get_credit_status()
        ct = status.get("credit_type", "standard")
        trial_raw = status.get("remaining_trial", 0)
        purchased_raw = status.get("remaining_purchased", 0)
        trial = max(0, trial_raw) if trial_raw != -1 else -1
        purchased = max(0, purchased_raw) if purchased_raw != -1 else -1

        # -1은 무제한을 의미
        if trial_raw == -1 or purchased_raw == -1:
            credit_text, color = "🎁 무료 앱", "green"
        elif ct == "free":
            credit_text, color = "🎁 무료 앱", "green"
        elif ct == "permanent":
            credit_text, color = "✨ 영구 라이선스", "blue"
        elif trial + purchased > 0:
            # 충전 크레딧이 0이면 체험판만 표시
            if purchased > 0:
                credit_text = f"체험판 {trial:,} / 충전 {purchased:,}"
            else:
                credit_text = f"체험판 {trial:,}"
            color = "green"
        else:
            credit_text, color = "⚠ 크레딧 없음", "red"
        self.credit_label.config(text=credit_text, fg=color)

    def select_folder(self):
        """폴더 선택 (DC 패턴)"""
        if not self.is_registered_user:
            self._show_messagebox("showwarning", "등록 필요", "사용자 등록 후 이용 가능합니다.")
            return

        path = filedialog.askdirectory(title="DWG 파일이 있는 폴더 선택")
        if not path:
            return

        self.SELECTED_FOLDER = path
        self.folder_entry.config(state="normal")
        self.folder_entry.delete(0, tk.END)
        self.folder_entry.insert(0, path)
        self.folder_entry.config(state="readonly")
        self.logger.info(f"Selected folder: {path}")

        # 폴더 선택 시 자동 스캔
        try:
            if hasattr(self, "scan_toggle_btn"):
                self.scan_toggle_btn.config(state="disabled")
            self.scan_toggle_var.set(True)
            self.on_scan_toggle()
        finally:
            if hasattr(self, "scan_toggle_btn"):
                self.scan_toggle_btn.config(state="normal")

    def select_excel_files(self):
        """엑셀 파일 다중 선택 (DC 패턴)"""
        if not self.is_registered_user:
            self._show_messagebox("showwarning", "등록 필요", "사용자 등록 후 이용 가능합니다.")
            return

        try:
            paths = filedialog.askopenfilenames(
                title="엑셀 파일 선택", filetypes=[("Excel", "*.xlsx *.xls")]
            )
            if paths:
                self.selected_excel_files = list(paths)
                # 하위 호환: 첫 번째 파일을 excel_path에도 저장
                self.excel_path = self.selected_excel_files[0] if self.selected_excel_files else None
                self.excel_listbox.delete(0, tk.END)
                for p in self.selected_excel_files:
                    self.excel_listbox.insert(tk.END, os.path.basename(p))
                self.logger.info(f"Selected Excel files: {self.selected_excel_files}")
                self.check_ready_to_start()
        except Exception as e:
            self.logger.error(f"엑셀 선택 오류: {e}")
            self._show_messagebox("showerror", "오류", str(e))

    def on_scan_toggle(self):
        """폴더 스캔 토글 (DC 패턴)"""
        if self.scan_toggle_var.get() and self.SELECTED_FOLDER:
            # TODO: 폴더 내 DWG 파일 스캔 로직 추가
            self.logger.info(f"Scanning folder: {self.SELECTED_FOLDER}")
        self.check_ready_to_start()

    def check_ready_to_start(self):
        """시작 버튼 활성화 조건 확인 (DC 패턴)"""
        try:
            # 폴더와 엑셀이 모두 선택되어야 시작 가능
            if self.SELECTED_FOLDER and self.selected_excel_files:
                self.start_button.config(state="normal")
            else:
                self.start_button.config(state="disabled")
        except Exception as e:
            self.logger.debug(f"check_ready_to_start 오류: {e}")

    def start_automation(self):
        if not self.SELECTED_FOLDER:
            self._show_messagebox("showerror", "오류", "폴더를 먼저 선택해주세요.")
            return
        if not self.selected_excel_files:
            self._show_messagebox("showerror", "오류", "엑셀 파일을 먼저 선택해주세요.")
            return

        if self.credit_manager:
            has_credit, _ = self.credit_manager.has_sufficient_credits(1)
            if not has_credit:
                self._show_messagebox("showerror", "크레딧 부족", "작업을 시작하기에 크레딧이 부족합니다.")
                return

        self.start_button.config(state="disabled")
        self.folder_button.config(state="disabled")
        self.excel_button.config(state="disabled")

        self.automation = AttributeResetAutomation(console_mode=False)
        self.automation.set_progress_callback(self.update_progress_bar)
        if self.credit_manager:
            self.automation.set_credit_manager(self.credit_manager)

        # 첫 번째 엑셀 파일 사용 (기존 로직 호환)
        self.automation_thread = threading.Thread(
            target=self.automation.process_folders_from_excel,
            args=(self.excel_path, self.master,),
            daemon=True
        )
        self.automation_thread.start()

    def update_progress_bar(self, current, total, status_text=""):
        if self.master.winfo_exists():
             if total > 0:
                percentage = (current / total) * 100
                self.progress_bar['value'] = percentage
        
             self.status_label.config(text=f"{current}/{total}")

             if current >= total and total > 0:
                self.start_button.config(state="normal")
                self.folder_button.config(state="normal")
                self.excel_button.config(state="normal")
                self._show_messagebox("showinfo", "완료", "속성 변경 작업이 완료되었습니다.")

    # ==================== 키보드 단축키 ====================
    def _bind_keyboard_shortcuts(self):
        """키보드 단축키 바인딩 (Alt+G, Alt+C)"""
        try:
            # Alt+G: Geometry 저장 (모든 모드)
            self.master.bind_all("<Alt-g>", self._on_debug_geometry_capture)

            # Alt+C: 화면 캡처 (demo 모드에서만)
            run_mode = getattr(self.config.runtime_config, "run_mode", "release")
            if run_mode == "demo":
                self.master.bind_all("<Alt-c>", self._on_manual_capture)
        except Exception as e:
            if self.logger:
                self.logger.debug(f"Alt hotkey bind 실패: {e}")

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
                self._show_toast(toast_msg, duration_ms=1400)
                if self.logger:
                    self.logger.info(f"[DEBUG] geometry saved to settings: {geo}")
            else:
                self._show_toast("geometry 저장 실패", duration_ms=1400)
        except Exception as e:
            if self.logger:
                self.logger.debug(f"Alt+G 저장 실패: {e}")

    def _on_manual_capture(self, _event=None):
        """Alt+C: 수동 화면 캡처 (데모 모드 전용)"""
        run_mode = getattr(self.config.runtime_config, "run_mode", "release")
        if run_mode != "demo":
            return

        try:
            from PIL import ImageGrab
            import datetime as dt

            # 캡처 디렉토리 준비
            capture_dir = Path(__file__).resolve().parent / "demo_captures"
            if not capture_dir.exists():
                capture_dir = Path.home() / ".wf_rpa" / "attribute_reset" / "demo_captures"
            capture_dir.mkdir(parents=True, exist_ok=True)

            # 캡처 저장
            ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
            fname = f"demo_{ts}_manual_capture.png"
            path = capture_dir / fname

            img = ImageGrab.grab()
            img.save(path, "PNG")

            self._show_toast("화면 캡처 완료", duration_ms=1200)
            if self.logger:
                self.logger.debug(f"[DEMO] capture saved: {path}")
        except Exception as e:
            self._show_toast(f"캡처 실패: {e}", duration_ms=1500)
            if self.logger:
                self.logger.error(f"수동 캡처 실패: {e}")

    def _show_toast(self, message: str, duration_ms: int = 1500):
        """임시 토스트 메시지 표시"""
        try:
            toast = tk.Toplevel(self.master)
            toast.overrideredirect(True)
            toast.attributes("-topmost", True)

            label = tk.Label(
                toast, text=message, bg="#333333", fg="white",
                font=("맑은 고딕", 10), padx=15, pady=8
            )
            label.pack()

            # 메인 창 중앙 하단에 배치
            self.master.update_idletasks()
            x = self.master.winfo_x() + (self.master.winfo_width() - toast.winfo_reqwidth()) // 2
            y = self.master.winfo_y() + self.master.winfo_height() - 60
            toast.geometry(f"+{x}+{y}")

            def _destroy():
                try:
                    toast.destroy()
                except Exception:
                    pass

            toast.after(duration_ms, _destroy)
        except Exception:
            pass

    def _show_messagebox(self, msg_type: str, title: str, message: str, **kwargs):
        """topmost 상태에서도 정상 표시되는 messagebox 헬퍼

        메인 창이 topmost일 때 messagebox가 뒤로 가는 문제를 방지합니다.
        topmost를 일시 해제 -> messagebox 표시 -> topmost 복원
        """
        try:
            # 현재 topmost 상태 저장 및 해제
            is_topmost = self.config.ui_config.topmost
            if is_topmost:
                self.master.wm_attributes("-topmost", 0)
                self.master.update_idletasks()

            # messagebox 표시
            msg_func = getattr(messagebox, msg_type, messagebox.showinfo)
            result = msg_func(title, message, parent=self.master, **kwargs)

            # topmost 복원
            if is_topmost:
                self.master.wm_attributes("-topmost", 1)

            return result
        except Exception:
            # fallback: 기본 messagebox 호출
            msg_func = getattr(messagebox, msg_type, messagebox.showinfo)
            return msg_func(title, message, **kwargs)

    # ==================== WF-ACT Test Mode ====================
    def init_test_server(self):
        """WF-ACT 인증 테스트용 TestServer 초기화"""
        try:
            # TestServer import (로컬 test_server.py 사용)
            from test_server import TestServer
            self.test_server = TestServer(app_name="attribute_reset")
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

    def _ensure_credit_manager(self):
        """CreditManager가 초기화될 때까지 대기 (최대 5초)"""
        import time
        for _ in range(50):  # 5초 대기
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
            rt, rp = data.get("remaining_trial", 0), data.get("remaining_purchased", 0)
            return -1 if rt == -1 or rp == -1 else rt + rp
        except Exception:
            return self.credit_manager.get_credit_status().get("remaining_credits", 0)

    def _test_set_credits(self, amount: int, credit_type: str = "trial") -> bool:
        """크레딧을 특정 값으로 설정 (테스트용)"""
        self._ensure_credit_manager()
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
        """크레딧 추가 (테스트용)"""
        self._ensure_credit_manager()
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
        """크레딧 상태 상세 조회 (테스트용)"""
        self._ensure_credit_manager()
        return self.credit_manager.get_credit_status() if self.credit_manager else {"error": "not_initialized"}

    def _test_get_trial_info(self) -> dict:
        """트라이얼 정보 조회 (테스트용)"""
        self._ensure_credit_manager()
        if not self.credit_manager:
            return {"error": "not_initialized"}
        policy = self.credit_manager.policy or {}
        data = self.credit_manager._load_credit_data()
        return {"initial_credits": policy.get("trial_credits", 100000), "remaining_trial": data.get("remaining_trial", 0), "trial_credits": policy.get("trial_credits", 100000)}

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
                    trial = self.credit_manager.policy.get("trial_credits", 100000)
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
        cost = self.credit_manager.policy.get("credit_per_work", 200)
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
            "selected_path": self.excel_path,
            "is_admin_mode": self.is_admin_mode,
            "credits_display": credits_display
        }

    def _test_get_policy(self) -> dict:
        p = dict(self.credit_manager.policy) if self.credit_manager else {}
        return {"identity": {"app_name": "attribute_reset", "display_name": "Attribute Reset"}, "policy": {"credit_per_work": p.get("credit_per_work", 200), "trial_credits": p.get("trial_credits", 100000)}, "app_name": "attribute_reset", **p}

    def _test_get_settings(self) -> dict:
        return {"app_name": "attribute_reset", "run_mode": getattr(self.config.runtime_config, "run_mode", "release"), "full_version": APP_VERSION_FULL, "version": APP_VERSION_FULL}

    def _test_reload_config(self) -> bool:
        """설정 및 정책 재로드 (테스트용)"""
        try:
            # CreditManager의 정책 재로드
            if self.credit_manager:
                self.credit_manager._reload_policy()
            return True
        except Exception as e:
            return False

    def _test_save_settings(self, settings: dict) -> dict:
        try:
            import json
            from app_setting_data import get_config_path
            sf = get_config_path()
            data = json.load(open(sf, "r", encoding="utf-8")) if sf.exists() else {}
            data.setdefault("test_config", {}).update(settings)
            sf.parent.mkdir(parents=True, exist_ok=True)
            json.dump(data, open(sf, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _test_load_settings(self) -> dict:
        try:
            import json
            from app_setting_data import get_config_path
            sf = get_config_path()
            data = json.load(open(sf, "r", encoding="utf-8")) if sf.exists() else {}
            return {"app_config": data.get("app_config", {}), "test_config": data.get("test_config", {})}
        except Exception as e:
            return {"error": str(e)}

    def _test_get_button_state(self, button_name: str) -> dict:
        bmap = {"work": getattr(self, "run_button", None), "register": getattr(self, "register_button", None), "settings": getattr(self, "settings_button", None)}
        btn = bmap.get(button_name)
        return {"exists": True, "state": str(btn.cget("state")), "text": str(btn.cget("text"))} if btn else {"exists": False}

    def _test_click_button(self, button_name: str) -> bool:
        bmap = {"work": getattr(self, "run_button", None), "register": getattr(self, "register_button", None), "settings": getattr(self, "settings_button", None)}
        btn = bmap.get(button_name)
        if btn and str(btn.cget("state")) != "disabled":
            btn.invoke()
            return True
        return False

    def on_closing(self):
        # WF-ACT 테스트 서버 정리
        try:
            if hasattr(self, "test_server") and self.test_server:
                self.test_server.stop()
        except Exception:
            pass
        self.master.quit()
        self.master.destroy()

    # ==================== 관리자 모드 ====================
    def on_progress_label_click(self, event):
        """진행률 라벨 클릭 이벤트 - 관리자 모드 토글"""
        try:
            if self.is_admin_mode:
                # 이미 관리자 모드인 경우 → 즉시 비활성화 (비밀번호 불필요)
                self._exit_admin_mode()
                self.logger.info("관리자 모드가 비활성화되었습니다.")
                self.update_credit_display()
            else:
                run_mode = getattr(self.config.runtime_config, "run_mode", "release")
                if run_mode == "dev":  # dev 모드에서만 암호 없이 진입
                    self._enter_admin_mode()
                    self.logger.info("관리자 모드가 활성화되었습니다. (30분 후 자동 해제)")
                    self.update_credit_display()
                else:
                    password = simpledialog.askstring(
                        "관리자 인증", "관리자 비밀번호를 입력하세요:", show="*", parent=self.master
                    )

                    if password is None:  # 취소 버튼
                        return

                    if password == self.admin_password:
                        self._enter_admin_mode()
                        self.logger.info("관리자 모드가 활성화되었습니다. (30분 후 자동 해제)")
                        self.update_credit_display()
                    else:
                        self.logger.warning("관리자 인증 실패 시도")
                        self._show_messagebox("showwarning", "인증 실패", "비밀번호가 올바르지 않습니다")

        except Exception as e:
            self.logger.error(f"관리자 모드 토글 오류: {e}")

    def _enter_admin_mode(self):
        """관리자 모드 진입"""
        self.is_admin_mode = True
        self.admin_mode_start_time = datetime.datetime.now()

        # 30분 타이머 설정 (1800000ms = 30분)
        self.admin_mode_timer = self.master.after(1800000, self._auto_exit_admin_mode)

        # UI 변경
        self.master.title(f"속성 리셋 {APP_VERSION_FULL} [🔧 관리자 모드]")
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
        except Exception as e:
            write_to_log(f"하드웨어 정보 조회 실패: {e}")

        write_to_log("-" * 50)
        write_to_log("30분 후 자동 해제 또는 클릭시 해제")
        write_to_log("=" * 50)

    def _exit_admin_mode(self):
        """관리자 모드 종료"""
        self.is_admin_mode = False
        self.admin_mode_start_time = None

        # 타이머 취소
        if self.admin_mode_timer:
            self.master.after_cancel(self.admin_mode_timer)
            self.admin_mode_timer = None

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
        self.master.title(f"속성 리셋 {APP_VERSION_DISPLAY}")
        self.progress_bar_label.config(bg=self.master.cget("bg"))

        # 프로그레스 초기화
        self.progress_bar["value"] = 0
        self.status_label.config(text="0/0")

    def _auto_exit_admin_mode(self):
        """30분 후 자동 관리자 모드 종료"""
        self._exit_admin_mode()
        self._show_messagebox("showinfo", "알림", "관리자 모드가 자동 해제되었습니다.")
        self.update_credit_display()

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
        self.log_frame.grid(row=4, column=0, columnspan=4, sticky="nsew", pady=(10, 0))

        # 로그 제목 및 옵션
        log_header_frame = tk.Frame(self.log_frame)
        log_header_frame.pack(fill="x", pady=(0, 5))

        log_label = tk.Label(
            log_header_frame, text="실시간 로그", font=("맑은 고딕", self.ui["font_size"], "bold")
        )
        log_label.pack(side="left")

        # 자동 스크롤 체크박스
        self.auto_scroll_var = tk.BooleanVar(value=True)
        self.auto_scroll_checkbox = tk.Checkbutton(
            log_header_frame, text="자동 스크롤", variable=self.auto_scroll_var,
            font=("맑은 고딕", self.ui["font_size"] - 2)
        )
        self.auto_scroll_checkbox.pack(side="right")

        # 스크롤바와 텍스트 위젯
        log_container = tk.Frame(self.log_frame)
        log_container.pack(fill="both", expand=True)

        self.log_scrollbar = tk.Scrollbar(log_container)
        self.log_scrollbar.pack(side="right", fill="y")

        self.log_text = tk.Text(
            log_container,
            height=8,
            wrap="word",
            state="disabled",
            font=("Consolas", self.ui["font_size"] - 2),
            yscrollcommand=self.log_scrollbar.set,
        )
        self.log_text.pack(side="left", fill="both", expand=True)
        self.log_scrollbar.config(command=self.log_text.yview)

    def destroy_log_frame(self):
        """로그 프레임 제거"""
        if self.log_frame:
            self.log_frame.destroy()
            self.log_frame = None
            self.log_text = None
            self.log_scrollbar = None
            self.auto_scroll_var = None
            self.auto_scroll_checkbox = None


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

        result = manager.sync_local_registration_to_sheets("attribute_reset", app_version)

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


_log_startup("module_ready")


def main():
    """Main entry point with single-instance lock"""
    # --test-mode 인자 처리 (WF-ACT 인증 테스트 모드)
    test_mode = "--test-mode" in sys.argv

    # --sync-registration 인자 처리 (GUI 없이 동기화만 수행)
    if "--sync-registration" in sys.argv:
        sys.exit(_handle_sync_registration())

    _log_startup("main() entry")

    # 테스트 모드에서는 single instance 체크 건너뛰기
    if not test_mode:
        # Enforce single instance (prevents multiple windows)
        is_first, _handle = _acquire_single_instance()
        _log_startup("single instance check complete")
        if not is_first:
            try:
                print("Another attribute_reset instance is already running. Exiting.")
            except Exception:
                pass
            return
    else:
        _log_startup("Test mode: skipping single instance check")

    # Mark this app as running in shared config (cross-app guard)
    try:
        _set_cross_app_running("attribute_reset")
        import atexit
        atexit.register(_clear_cross_app_running)
    except Exception:
        pass

    _log_startup("Creating Tk root window")
    root = tk.Tk()
    _log_startup("tk_root_created")

    # 시작 시 플래시 방지: 초기화 전 숨김 (BE 패턴)
    try:
        root.withdraw()
    except Exception:
        pass

    # 작업표시줄 아이콘 설정 (개발/릴리스 환경 모두 지원)
    try:
        # 아이콘 파일명 (새 아이콘: 05_Attribute_Reset.ico)
        icon_names = ["05_Attribute_Reset.ico"]

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

    app = AttributeResetGUI(root)
    _log_startup("gui_initialized")

    # WF-ACT 테스트 모드 초기화
    if test_mode:
        try:
            app.init_test_server()
        except Exception as e:
            print(f"[WF-ACT] Failed to initialize test server: {e}")

    _flush_startup_log()
    root.mainloop()


if __name__ == "__main__":
    main()