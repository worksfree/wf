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
_STARTUP_ENABLED = True  # 프로파일링 활성화
_STARTUP_FLUSHED = False


def _detect_run_mode():
    """
    실행 모드 감지 (BASIC_RULES 준수: settings.json 우선)
    - 1순위: 10.common/config/{app}/settings.json의 runtime_config.run_mode
    - 2순위: WF_RPA_MODE 환경변수
    - 3순위: .py 파일 직접 실행 → dev
    - 4순위: 기본값 release (exe 실행)
    """
    # 1순위: settings.json 읽기 (BASIC_RULES 준수)
    try:
        import json
        from pathlib import Path
        app_root = Path(__file__).resolve().parent
        settings_path = app_root.parents[1] / "10.common" / "config" / "korean_filename_normalizer" / "settings.json"
        if settings_path.exists():
            with open(settings_path, "r", encoding="utf-8-sig") as f:
                data = json.load(f) or {}
            cfg_mode = str(data.get("runtime_config", {}).get("run_mode", "") or "").strip().lower()
            if cfg_mode in ("dev", "demo", "release"):
                return cfg_mode
    except Exception:
        pass
    
    # 2순위: 환경변수
    env_mode = (os.environ.get("WF_RPA_MODE") or "").strip().lower()
    if env_mode in ("dev", "demo", "release"):
        return env_mode
    
    # 3순위: .py 직접 실행
    if sys.argv[0].endswith(".py"):
        return "dev"
    
    # 4순위: 기본값
    return "release"


def _get_startup_log_path():
    mode = _detect_run_mode()
    if mode in ("dev", "demo"):
        path = Path.cwd() / "startup_profile.log"
    else:
        path = Path.home() / ".wf_rpa" / "korean_filename_normalizer" / "startup_profile.log"
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
            settings_file = base_path / ".wf_rpa" / "korean_filename_normalizer" / "settings.json"
            if not settings_file.exists():
                settings_file = Path.home() / ".wf_rpa" / "korean_filename_normalizer" / "settings.json"
        else:
            # 개발 모드: 10.common/config/korean_filename_normalizer/settings.json (통합 경로)
            app_root = Path(__file__).parent
            settings_file = app_root.parent.parent / "10.common" / "config" / "korean_filename_normalizer" / "settings.json"
            # fallback: 앱 폴더의 config
            if not settings_file.exists():
                settings_file = app_root / "config" / "korean_filename_normalizer" / "settings.json"

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

    # display_version은 앞 2자리만 (v0.7.0.0 → v0.7)
    parts = full_version.lstrip("v").split(".")
    display_version = "v" + ".".join(parts[:2])

    return full_version, display_version


APP_VERSION_FULL, APP_VERSION_DISPLAY = _load_version_info()

# Windows frozen executables (PyInstaller) can recursively spawn child processes
try:
    import multiprocessing

    multiprocessing.freeze_support()
    _log_startup("multiprocessing.freeze_support()")
except Exception:
    pass


# --- Single instance guard (Windows named mutex) ---
_instance_mutex_handle = None


def _acquire_single_instance(mutex_name: str = r"Global\\WF_KOREAN_FILENAME_NORMALIZER"):
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
common_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "10.common"))
if common_path not in sys.path:
    sys.path.insert(0, common_path)
_log_startup("sys.path setup complete")

# -*- coding: utf-8 -*-
"""
Korean Filename Normalizer Main UI Module
메인 GUI 인터페이스를 담당하는 모듈
"""

import tkinter as tk

_log_startup("import tkinter")
import tkinter.ttk as ttk
from tkinter import messagebox

_log_startup("import tkinter.ttk, messagebox")
import datetime

_log_startup("import datetime")
from tkinter import filedialog
from pathlib import Path

_log_startup("import filedialog, Path")
import logging
import threading

_log_startup("import logging, threading")

# 현재 스크립트의 디렉토리를 Python 경로에 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# 앱 상수 정의
APP_NAME = "korean_filename_normalizer"
_log_startup("APP_NAME defined")

# 로컬 모듈 import
from automation import FilenameProcessor

_log_startup("import automation.FilenameProcessor")
from ui_setting import create_settings_window
from wf_ui_adaptive import get_adaptive_ui_settings, apply_global_fonts, apply_equal_vertical_pack

_log_startup("import ui_setting")

# 글로벌 로거 import
from wf_log import get_app_logger

_log_startup("import wf_log")
from app_setting_data import get_config

_log_startup("import config.get_config")

# 크레딧 및 등록 관리 모듈 import
try:
    from wf_credit_manager import WorksFreeManager, CreditManager
    from wf_app_init_helpers import init_credit_and_policy_managers, check_cross_app_running_and_exit, seed_res_if_missing

    _log_startup("import wf_credit_manager")
    WFM_AVAILABLE = True
except ImportError as e:
    print(f"WorksFree 관리자 모듈 import 실패: {e}")
    WorksFreeManager = None
    CreditManager = None
    check_cross_app_running_and_exit = None
    WFM_AVAILABLE = False

_log_startup("All imports complete")


class KoreanFilenameNormalizerApp:
    """Korean Filename Normalizer GUI 애플리케이션 클래스"""

    def __init__(self, master):
        _log_startup("KoreanFilenameNormalizerApp.__init__ start")
        self.master = master
        self.itself_dir = os.path.dirname(os.path.abspath(__file__))
        # MessageBox들이 메인창 기준으로 뜨도록 parent를 강제 지정
        self._bind_messagebox_parent()

        # 아이콘 경로 저장 (등록창/설정창에서 사용)
        self.icon_path = self._find_icon_path()

        # 앱 설정 로드
        self.config = get_config()

        # 적응형 UI 설정 초기화 (config 로드 후 호출 - saved_ui 적용)
        saved_ui = getattr(self.config, "ui_config", None)
        self.ui = get_adaptive_ui_settings(saved_ui=saved_ui)

        # 로거 초기화
        self.logger = get_app_logger("korean_filename_normalizer", console_level=logging.DEBUG)
        self.app = None  # 호환성 유지
        self.paths = None  # 호환성 유지
        self.i18n = None  # 호환성 유지

        # WorksFree 전역 매니저 초기화
        if WFM_AVAILABLE:
            self.wf_manager = WorksFreeManager()
        else:
            self.wf_manager = None
            if self.logger:
                self.logger.error("프로그램 핵심 모듈을 찾을 수 없습니다. 프로그램을 종료합니다.")
            messagebox.showerror("치명적 오류", "프로그램 핵심 모듈을 찾을 수 없습니다.")
            sys.exit(1)

        # 앱 실행 상태 체크는 모듈 전역 헬퍼로 대체 (class-level 호출 제거)

        self.automation = None
        self.SELECTED_PATH = None  # 통합 표준 변수명 (로직용)
        self.folder_path = tk.StringVar()  # UI 전용 (Entry 바인딩)
        self.auto_scan_var = tk.BooleanVar(value=False)  # "현재 폴더 스캔" 체크박스

        self.initial_file_count = 0
        self.cumulative_processed_count = 0
        self.is_first_run = True
        self.last_run_success_count = 0

        # 스피너 관련 변수
        self.spinner_running = False
        self.spinner_index = 0
        self.spinner_chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

        # 관리자 모드 변수
        self.is_admin_mode = False
        self.admin_mode_timer = None
        self.admin_mode_start_time = None
        # 🚀 최적화: admin 비밀번호 lazy 로딩 (Google Sheets 호출 지연)
        self._admin_password = None  # lazy load

        # 로그 창 관련 변수
        self.log_frame = None
        self.log_text = None
        self.log_scrollbar = None
        self.auto_scroll_var = None
        self.auto_scroll_checkbox = None

        # 매니저 및 UI 초기화 (모든 변수 초기화 후 호출)
        self._init_managers_and_ui()

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
            icon_names = ["06_Korean_Filename_Normalizer.ico", "KFN.ico"]
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

    def _init_managers_and_ui(self):
        """wf_manager 초기화 후 호출되는 매니저 및 UI 초기화"""
        self.original_window_height = self.ui.get("window_height", getattr(self.config, "window_height", 200))
        self.expanded_window_height = self.original_window_height + getattr(self.config, "admin_window_height", 300)  # 관리자 모드: settings.json에서 로드

        # 사용자 등록 상태 Early 확인 (플래그/reg_time_local)
        self.is_registered_user = False
        try:
            if self.wf_manager:
                self.is_registered_user = self.wf_manager.is_registered()
        except Exception:
            pass

        # 크레딧 관리자 초기화 (무료 앱 - 공통 헬퍼 사용)
        if CreditManager:
            self.credit_manager = init_credit_and_policy_managers(
                app_name="korean_filename_normalizer",
                wf_manager=self.wf_manager,
                master=self.master,
                logger=self.logger,
                recovery_delay_ms=700,
                policy_delay_ms=400,
            )
            # 정책 동기화 별도 스케줄 (무료 앱이므로 구매 이력 없음)
            try:
                self.master.after(400, self._async_refresh_policies)
            except Exception:
                threading.Thread(target=self._async_refresh_policies, daemon=True).start()
        else:
            self.credit_manager = None

        # 데모 모드 자동 캡처 변수 초기화
        self.demo_capture_enabled = self.config.is_demo() if self.config and hasattr(self.config, "is_demo") else False
        self.demo_capture_dir = None
        self.demo_capture_size = (1920, 1040)
        self._last_demo_capture_ts = 0.0

        # 기본 폴더 경로 초기화: 최초 실행 시 Downloads로 설정, 설정값 있으면 그 값 사용
        try:
            default_folder = (self.config.get("default_folder_path", "") or "").strip()
            if not default_folder:
                default_folder = self._get_downloads_folder()
                if default_folder and os.path.isdir(default_folder):
                    self.config.set("default_folder_path", default_folder)
                    try:
                        self.config.save_settings()
                    except Exception:
                        pass
            if default_folder:
                self.folder_path.set(default_folder)
        except Exception:
            pass

        # UI 생성 (빠르게 띄우고)
        self.init_ui()

        # 데모 모드 캡처 초기화
        if self.demo_capture_enabled:
            self._init_demo_capture()
            self._bind_debug_geometry_hotkey()

        # 사용자 디렉토리 및 설정 파일 초기화는 UI 표시 이후 백그라운드로 지연 실행
        try:
            self.master.after(
                200,
                lambda: threading.Thread(target=self.create_user_directories, daemon=True).start(),
            )
        except Exception:
            # after 사용 불가 시 동기 실행 (개발 환경 등)
            threading.Thread(target=self.create_user_directories, daemon=True).start()
        
        # 🚀 이전 작업 폴더 자동 스캔 (CV 패턴 적용)
        if self.folder_path.get().strip():
            self.master.after(300, self._restore_last_session)

    def set_selected_path(self, path: str | None):
        """선택된 경로를 설정하고 UI를 동기화 (통합 헬퍼)"""
        self.SELECTED_PATH = path

        # folder_path StringVar 미러링 (KFN UI 전용)
        try:
            self.folder_path.set(path or "")
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
     
    def _restore_last_session(self):
        """이전 작업 세션 복원: 폴더 경로만 복원, 스캔은 사용자가 체크박스 선택 시에만"""
        try:
            folder = self.folder_path.get().strip()
            # 등록된 사용자이고 폴더가 유효한 경우에만 경로 복원
            # 스캔은 scan_toggle_var가 True인 경우에만 on_scan_toggle에서 자동 실행됨
            if self.is_registered_user and folder and os.path.isdir(folder):
                self.logger.info(f"이전 작업 폴더 경로 복원: {folder}")
                # scan_toggle_var는 이미 False로 초기화되어 있으므로 스캔하지 않음
        except Exception as e:
            self.logger.warning(f"이전 세션 복원 중 오류 (무시): {e}")

    def create_user_directories(self):
        """사용자 디렉토리 구조 생성 및 설정 파일 배포"""
        user_home = os.path.expanduser("~")
        wf_rpa_dir = os.path.join(user_home, ".wf_rpa")
        # 표준: 앱 폴더는 점(.) 없이 사용
        app_dir = os.path.join(wf_rpa_dir, f"{APP_NAME}")

        try:
            # 디렉토리 생성
            if not os.path.exists(wf_rpa_dir):
                os.makedirs(wf_rpa_dir)
            if not os.path.exists(app_dir):
                os.makedirs(app_dir)

            # 로그 디렉토리 생성
            for subfolder in ["logs", "res"]:
                sub_dir = os.path.join(app_dir, subfolder)
                if not os.path.exists(sub_dir):
                    os.makedirs(sub_dir)

            # 배포된 설정 파일들을 사용자 홈으로 복사
            self.deploy_config_files(wf_rpa_dir, app_dir)

            if self.logger:
                self.logger.info(f"사용자 디렉토리 구조 생성 완료: {wf_rpa_dir}")

        except Exception as e:
            if self.logger:
                self.logger.error(f"[ERROR] 디렉토리 생성 실패: {e}")
            return False
        return True

    def deploy_config_files(self, wf_rpa_dir, app_dir):
        """배포된 config 파일들을 사용자 홈 디렉토리에 복사 (정책 병합)"""
        import shutil

        # PyInstaller로 패키징된 경우 내장된 .wf_rpa 폴더에서 복사
        if getattr(sys, "_MEIPASS", None):
            # 패키징된 실행파일
            source_wf_rpa = os.path.join(sys._MEIPASS, ".wf_rpa")
        else:
            # 개발 환경: config 폴더에서 직접 읽기
            config_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config")
            return self.deploy_from_dev_config(config_dir, wf_rpa_dir, app_dir)

        if not os.path.exists(source_wf_rpa):
            if self.logger:
                self.logger.warning("배포된 설정 파일을 찾을 수 없습니다.")
            return

        try:
            # 1. 전역 설정 파일들 처리 (표준: wf_rpa_config.json)
            global_files = ["wf_rpa_config.json"]
            for filename in global_files:
                source_file = os.path.join(source_wf_rpa, filename)
                target_file = os.path.join(wf_rpa_dir, filename)

                if os.path.exists(source_file):
                    if not os.path.exists(target_file):
                        shutil.copy2(source_file, target_file)
                        if self.logger:
                            self.logger.info(f"전역 설정 파일 생성: {filename}")

            # 2. 앱 정책 파일 병합
            self.merge_app_policies(source_wf_rpa, wf_rpa_dir)

            # 3. 앱별 설정 파일들
            source_app_dir = os.path.join(source_wf_rpa, f".korean_filename_normalizer")
            if os.path.exists(source_app_dir):
                for filename in os.listdir(source_app_dir):
                    source_file = os.path.join(source_app_dir, filename)
                    target_file = os.path.join(app_dir, filename)

                    if os.path.isfile(source_file) and not os.path.exists(target_file):
                        shutil.copy2(source_file, target_file)
                        if self.logger:
                            self.logger.info(f"앱 설정 파일 생성: {filename}")

        except Exception as e:
            if self.logger:
                self.logger.error(f"설정 파일 배포 중 오류: {e}")

    def deploy_from_dev_config(self, config_dir, wf_rpa_dir, app_dir):
        """개발 환경: config 폴더의 JSON 파일들을 사용자 홈으로 복사"""
        import shutil
        import json

        try:
            # 1. 전역 설정 파일
            dev_wf_config = os.path.join(config_dir, "dev_wf_rpa_config.json")
            target_wf_config = os.path.join(wf_rpa_dir, "wf_rpa_config.json")

            if os.path.exists(dev_wf_config) and not os.path.exists(target_wf_config):
                shutil.copy2(dev_wf_config, target_wf_config)
                if self.logger:
                    self.logger.info("전역 설정 파일 생성 (개발 환경)")

            # 2. (Removed) 레거시 전역 정책 파일 병합은 더 이상 수행하지 않습니다.
            #    정책은 각 앱 폴더의 credit_policy.json로 관리됩니다.

            # 3. 앱 설정 파일 (표준: settings.json)
            dev_app_settings = os.path.join(
                config_dir, "dev_korean_filename_normalizer_settings.json"
            )
            target_app_settings = os.path.join(app_dir, "settings.json")

            if os.path.exists(dev_app_settings) and not os.path.exists(target_app_settings):
                shutil.copy2(dev_app_settings, target_app_settings)
                if self.logger:
                    self.logger.info("앱 설정 파일 생성 (개발 환경, settings.json)")

        except Exception as e:
            if self.logger:
                self.logger.error(f"개발 환경 설정 파일 배포 중 오류: {e}")

    def merge_app_policies(self, source_wf_rpa, wf_rpa_dir):
        """[Deprecated] 전역 정책 파일(.wf_app_policies.json) 병합은 지원하지 않습니다."""
        if self.logger:
            self.logger.debug(
                "merge_app_policies() deprecated: skip legacy .wf_app_policies.json handling"
            )

    def merge_app_policies_from_file(self, dev_policies_file, wf_rpa_dir):
        """[Deprecated] 개발 환경 전역 정책 병합 비활성화."""
        if self.logger:
            self.logger.debug(
                "merge_app_policies_from_file() deprecated: skip legacy .wf_app_policies.json handling"
            )

    def check_and_set_execution_status(self):
        """실행 상태 확인 및 설정 (다중 실행 방지)"""
        try:
            # 실행 상태 확인 로직 구현
            return True
        except Exception as e:
            if self.logger:
                self.logger.error(f"실행 상태 확인 오류: {e}")
            return True

    def clear_execution_status(self):
        """실행 상태 해제"""
        try:
            pass
        except Exception as e:
            if self.logger:
                self.logger.error(f"실행 상태 해제 오류: {e}")

    def _async_refresh_policies(self):
        """정책 동기화 (백그라운드, 토스트 메시지 없음)"""

        def worker():
            try:
                result = self.credit_manager.refresh_policies_from_sheets()
                self.logger.info(f"정책 동기화 결과: {result}")
                # 정책 업데이트 성공 시 credit_per_work 갱신
                if result.get("success"):
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
        """크레딧 표시 업데이트"""
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
            # bind tooltip
            try:
                self._bind_tooltip(self.credit_label, tip)
            except Exception:
                pass
        except Exception as e:
            self.credit_label.config(text="표시 오류", fg="red")
            if self.logger:
                self.logger.error(f"크레딧 표시 오류: {e}")

    def _bind_tooltip(self, widget, text: str):
        """Simple tooltip implementation"""
        if not text:
            return
        tip = {"win": None}

        def on_enter(_e):
            if tip["win"] is not None:
                return
            x = widget.winfo_rootx() + 20
            y = widget.winfo_rooty() + 20
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

        widget.bind("<Enter>", on_enter)
        widget.bind("<Leave>", on_leave)

    def init_ui(self):
        """창 초기화 - settings.json 우선 적용"""
        # 생성자에서 이미 설정한 self.original_window_height 사용 (settings.json 우선)
        window_width = self.config.window_width
        window_height = self.original_window_height  # ← settings.json ui_config에서 먼저 로드됨
        adjusted_height = window_height

        # 화면 중앙 배치 (Tk 자체 기능 사용하여 외부 의존성 제거)
        try:
            screen_width = self.master.winfo_screenwidth()
            screen_height = self.master.winfo_screenheight()
            x_coord = int((screen_width - window_width) / 2)
            y_coord = int((screen_height - adjusted_height) / 2)
        except Exception:
            x_coord = 300
            y_coord = 200

        self.master.geometry(f"{window_width}x{adjusted_height}+{x_coord}+{y_coord}")

        # settings.json의 geometry override 적용 (설정 파일 값만 사용)
        try:
            override_geo = (getattr(self.config, "window_geometry_override", "") or "").strip()
            if override_geo:
                self.master.geometry(override_geo)
                if self.logger:
                    self.logger.info(f"[DEBUG] geometry override at startup: {override_geo}")
        except Exception as e:
            try:
                if self.logger:
                    self.logger.warning(f"geometry override 적용 실패(무시): {e}")
            except Exception:
                pass

        # 개발 시에는 리사이즈 가능
        self.master.resizable(True, True)
        # 최소 크기를 기본 크기로 설정
        self.master.minsize(window_width, adjusted_height)

        # 최상위 설정 (설정 파일에서 추후 확장 가능)
        self.master.wm_attributes("-topmost", 1)

        # 전역 폰트 설정 적용 (메인창 폰트 크기 일관성 보장)
        apply_global_fonts(self.master, self.ui)

        # 창 제목 설정
        self.master.title(f"한글 파일명 복원 {APP_VERSION_DISPLAY}")

        # UI 요소 생성
        self.create_ui_elements()

        # 창을 앞으로 가져오고 포커스 설정
        self.master.lift()
        self.master.focus_force()

        # 초기 크레딧 표시 업데이트
        self.update_credit_display()
        self.update_file_count_display()

    def create_widgets(self):
        """위젯 생성 - init_ui()로 이동됨 (하위 호환성 유지)"""
        # 하위 호환성을 위해 남겨둠 (사용되지 않음)
        pass

    def create_ui_elements(self):
        """BOM2Excel과 동일한 UI 요소 생성"""
        master = self.master
        
        # Grid로 루트 윈도우 설정하여 상하좌우 여백 균등 분배
        master.grid_rowconfigure(0, weight=1)
        master.grid_columnconfigure(0, weight=1)
        
        main_frame = tk.Frame(master, padx=12, pady=0)
        main_frame.grid(row=0, column=0, sticky="nsew")

        # 1. 폴더 선택 프레임 (BOM2Excel과 동일)
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
            folder_frame,
            textvariable=self.folder_path,
            state="readonly",
            font=("맑은 고딕", self.ui["font_size"]),
        )
        self.folder_entry.pack(side="left", fill="x", expand=True, padx=(10, 0))
        # 이전 작업 폴더 자동 로드
        try:
            _last = (self.config.get_last_selected_folder() or "").strip()
            if _last and os.path.isdir(_last):
                self.folder_path.set(_last)
        except Exception:
            pass

        # 2. 진행률 프레임 (BOM2Excel과 동일)
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

        # BOM2Excel과 동일한 진행률 바 (ttk.Progressbar 사용)
        import tkinter.ttk as ttk

        self.progress_bar = ttk.Progressbar(
            progress_frame, orient="horizontal", mode="determinate", maximum=100
        )
        self.progress_bar.pack(side="left", fill="x", expand=True, padx=(10, 0))

        # 스피너 라벨 추가 (진행률 바 오른쪽)
        self.spinner_label = tk.Label(
            progress_frame, text="", font=("맑은 고딕", self.ui["font_size_title"]), width=2
        )
        self.spinner_label.pack(side="left", padx=(5, 0))

        # 3. 상태 프레임 (BOM2Excel과 동일)
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

        # 자동 스캔 변수 유지 (호환성)
        self.auto_scan_var = self.scan_toggle_var

        # 진행 상황 라벨 (?/? 형태)
        self.progress_label = tk.Label(
            status_frame, text="0/0", font=("맑은 고딕", self.ui["font_size"])
        )
        self.progress_label.grid(row=0, column=1)

        # 크레딧 라벨
        self.credit_label = tk.Label(
            status_frame,
            text="크레딧 확인 중...",
            fg="blue",
            font=("맑은 고딕", self.ui["font_size"]),
            cursor="hand2",
        )
        self.credit_label.grid(row=0, column=2, sticky="e")

        # 4. 버튼 프레임 (BOM2Excel과 동일)
        button_frame = tk.Frame(main_frame)
        button_frame.pack(fill="x", pady=(6, 6))
        button_frame.columnconfigure(0, weight=1)
        button_frame.columnconfigure(1, weight=1)
        button_frame.columnconfigure(2, weight=1)
        button_frame.columnconfigure(3, weight=1)

        # 자소분리 복원 버튼 (BOM 저장 대신)
        self.print_button = tk.Button(
            button_frame,
            text="자소분리 복원",
            command=self.start_normalization,
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

        # 크레딧 갱신 버튼 (업데이트)
        self.refresh_credit_button = tk.Button(
            button_frame,
            text="업데이트",
            command=self.on_refresh_credit,
            width=12,
            height=1,
            font=("맑은 고딕", self.ui["font_size"]),
        )
        self.refresh_credit_button.grid(row=0, column=2, padx=5, sticky="ew")

        # 종료 버튼
        self.exit_button = tk.Button(
            button_frame,
            text="종 료",
            command=self.on_closing,
            width=12,
            height=1,
            font=("맑은 고딕", self.ui["font_size"]),
        )
        self.exit_button.grid(row=0, column=3, padx=5, sticky="ew")
        
        # Apply adaptive equal vertical spacing
        apply_equal_vertical_pack(main_frame)

        # 초기 크레딧 표시 업데이트
        self.update_credit_display()

    def on_auto_scan_toggle(self):
        """현재 폴더 스캔 체크박스 토글 - 체크되면 자동으로 폴더 스캔"""
        if self.auto_scan_var.get():
            # 체크박스가 켜졌을 때 폴더 경로가 있으면 자동 스캔
            folder = self.folder_path.get().strip()
            if folder and os.path.isdir(folder):
                self.scan_current_folder()
        else:
            # 체크박스가 꺼졌을 때는 카운트 초기화
            self.progress_label.config(text="?/?")
            self.print_button.config(state="disabled")

    def scan_current_folder(self):
        """현재 선택된 폴더를 스캔해서 자소분리 파일 수를 업데이트"""
        folder = self.folder_path.get().strip()
        if not folder or not os.path.isdir(folder):
            self.progress_label.config(text="?/?")
            return

        try:
            # FilenameProcessor를 사용하여 자소 분리 파일 검색
            from automation import FilenameProcessor

            processor = FilenameProcessor(log_callback=self.log_message)

            # 자소 분리된 파일만 찾기
            target_files = processor.find_decomposed_files(folder)
            file_count = len(target_files)

            if file_count > 0:
                self.initial_file_count = file_count
                self.cumulative_processed_count = 0
                self.is_first_run = True
                self.last_run_success_count = 0
                self.progress_bar.config(maximum=self.initial_file_count)
                self.progress_bar["value"] = 0
                self.progress_label.config(text=f"0/{self.initial_file_count}")
                self.print_button.config(state="normal")
            else:
                self.initial_file_count = 0
                self.print_button.config(state="disabled")
                self.progress_label.config(text="0/0")

        except Exception as e:
            if self.logger:
                self.logger.error(f"폴더 스캔 중 오류: {e}")
            self.progress_label.config(text="오류")
            self.print_button.config(state="disabled")

    def on_checkbox_toggle(self):
        """체크박스 토글 (BOM2Excel과 동일)"""
        pass

    def on_scan_toggle(self):
        """폴더 스캔 토글 처리 (자소 분리 파일만 카운트, 보류 목록/필터 동일 적용)"""
        if self.scan_toggle_var.get():
            folder_path = self.folder_path.get().strip()
            if not folder_path:
                messagebox.showwarning("폴더 미선택", "먼저 작업할 폴더를 선택해주세요.")
                self.scan_toggle_var.set(False)
                return

            try:
                if self.logger:
                    self.logger.info(f"폴더 스캔 시작: {folder_path}")

                # FilenameProcessor 로직을 그대로 사용하여 대상 산정
                from automation import FilenameProcessor

                processor = FilenameProcessor(log_callback=self.log_message)
                decomposed_list = processor.find_decomposed_files(folder_path)
                file_count = len(decomposed_list)

                if file_count > 0:
                    self.initial_file_count = file_count
                    self.cumulative_processed_count = 0
                    self.is_first_run = True
                    self.last_run_success_count = 0
                    self.progress_bar.config(maximum=self.initial_file_count)
                    self.progress_bar["value"] = 0
                    self.progress_label.config(text=f"0/{self.initial_file_count}")
                    self.print_button.config(state="normal")
                    if self.logger:
                        self.logger.info(f"폴더 스캔 완료: {file_count}개 파일")
                    # 폴더 스캔 완료 캡처
                else:
                    self.print_button.config(state="disabled")
                    self.progress_label.config(text="파일 없음")
                    messagebox.showinfo("스캔 완료", "작업 대상 파일이 없습니다.")
                    self.scan_toggle_var.set(False)
            except Exception as e:
                if self.logger:
                    self.logger.error(f"폴더 스캔 중 오류: {e}")
                self.print_button.config(state="disabled")
                self.progress_label.config(text="오류")
                messagebox.showerror("스캔 오류", f"폴더 스캔 중 오류가 발생했습니다:\n{e}")
                self.scan_toggle_var.set(False)
        else:
            # 스캔 비활성화 (OFF)
            self.print_button.config(state="disabled")
            self.progress_label.config(text="?/?")
            if self.logger:
                self.logger.info("폴더 스캔 초기화")

    def on_refresh_credit(self):
        """크레딧 갱신 버튼 클릭 시 호출 (구매 이력 + 정책 동기화)"""
        if not self.credit_manager:
            self.logger.error("크레딧 매니저가 초기화되지 않았습니다.")
            messagebox.showerror("오류", "크레딧 매니저가 초기화되지 않았습니다.")
            return

        try:
            popup_messages = []
            credentials_updated = False

            # 1. 앱 정책 및 관리자 설정 동기화 (백그라운드)
            try:
                from wf_settings_common import sync_policies_from_sheets  # type: ignore
                policy_result = sync_policies_from_sheets("korean_filename_normalizer", self.logger)
                if policy_result.get("success"):
                    self.logger.info("정책 동기화 완료")
                else:
                    self.logger.warning(f"정책 동기화 실패: {policy_result.get('message')}")
            except Exception as e:
                self.logger.warning(f"정책 동기화 중 오류 (무시): {e}")

            # 정책 동기화 후 최신 크레딧 데이터 로드
            status = self.credit_manager.get_credit_status()
            trial_credits = status.get("remaining_trial", 0)
            purchased_credits = status.get("remaining_purchased", 0)

            # 2. 구매 이력 반영 - 팝업에 표시
            if trial_credits == -1:
                popup_messages.append("무료 앱 - 구매 이력 동기화 건너뜀")
            elif purchased_credits == -1:
                popup_messages.append("영구 라이선스 - 구매 이력 동기화 불필요")
            else:
                try:
                    result = self.credit_manager.pull_and_apply_purchases()
                    if result.get("success"):
                        added = result.get("added", 0)
                        if added > 0:
                            popup_messages.append(f"✅ 구매 이력 반영: {added:,}개 크레딧 추가")
                        else:
                            popup_messages.append("신규 구매 이력이 없습니다.")
                    else:
                        popup_messages.append(f"⚠️ 구매 이력 갱신 실패: {result.get('message')}")
                except Exception as e:
                    popup_messages.append(f"⚠️ 구매 이력 갱신 오류: {str(e)}")
                    self.logger.error(f"크레딧 갱신 오류: {e}")

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
            messagebox.showerror("업데이트 오류", str(e))
            self.logger.error(f"업데이트 오류: {e}")
            import traceback
            self.logger.error(traceback.format_exc())

    def start_normalization(self):
        """자소 분리 파일 정규화 실행"""
        # 등록 + 하드웨어 검증 (무료 앱이지만 등록은 필수)
        if not self.is_registered_user:
            messagebox.showwarning(
                "사용자 등록 필요",
                "무료 앱이라도 사용자 등록이 필요합니다. '등 록' 버튼을 눌러주세요.",
            )
            return
        if not self.verify_hardware_fingerprint():
            messagebox.showerror("인증 실패", "등록된 사용자의 하드웨어 정보와 일치하지 않습니다.")
            return

        folder = (self.folder_path.get() if hasattr(self, "folder_path") else "").strip()
        if not folder:
            messagebox.showwarning("폴더 미선택", "먼저 작업할 폴더를 선택해주세요.")
            return

        try:
            # 버튼 비활성화 (메인 버튼만)
            self.print_button.config(state="disabled")
            if hasattr(self, "settings_button"):
                self.settings_button.config(state="disabled")

            def worker():
                exception_info = {
                    "error": None,
                    "total_files": 0,
                    "success_count": 0,
                    "file_list": [],
                }
                try:
                    # 백업 비활성화 설정
                    config = get_config()
                    try:
                        config.set("backup_enabled", False)
                    except Exception:
                        pass

                    processor = FilenameProcessor(config=config, log_callback=self.log_message)

                    # 1. 자소 분리 파일 찾기
                    target_files = processor.find_decomposed_files(folder)
                    exception_info["total_files"] = len(target_files)

                    if len(target_files) > 0:
                        # 파일 목록 저장 (변환 전/후)
                        exception_info["file_list"] = [
                            {
                                "original": file_info["original_name"],
                                "normalized": file_info["normalized_name"],
                                "path": str(file_info["original_path"]),
                            }
                            for file_info in target_files
                        ]

                        # 2. 변환 실행
                        processor.execute_conversion(folder)
                        exception_info["success_count"] = len(target_files)
                        
                        # 3. 크레딧 사용 로그 기록 (무료 앱이지만 로그는 남김)
                        if self.credit_manager:
                            try:
                                # deduct_credits_by_policy는 무료 앱이면 로그만 기록하고 실제 차감은 하지 않음
                                # 일괄 처리로 file_count 정보를 정확히 전달
                                file_count = len(target_files)
                                self.credit_manager.deduct_credits_by_policy(
                                    item_count=file_count,
                                    description=f'자소분리 복원: {file_count}개 파일'
                                )
                                self.logger.info(
                                    f"크레딧 사용 로그 기록 완료: {file_count}개 파일"
                                )
                            except Exception as e:
                                self.logger.warning(f"크레딧 로그 기록 실패(무시): {e}")

                except Exception as e:
                    exception_info["error"] = e
                finally:
                    self.master.after(0, lambda: self.on_normalization_complete(exception_info))

            threading.Thread(target=worker, daemon=True, name="Normalization-Worker").start()

        except Exception as e:
            messagebox.showerror("작업 실패", f"정규화 작업 중 오류가 발생했습니다:\n\n{str(e)}")

    def on_normalization_complete(self, exception_info):
        """정규화 완료 후 UI 업데이트"""
        try:
            # 크레딧 표시 업데이트 (로그 기록 후)
            if hasattr(self, 'update_credit_display'):
                self.update_credit_display()
                
            # 정규화 완료 캡처
                
            # 기존 완료 처리 로직
            if exception_info.get("error"):
                messagebox.showerror(
                    "작업 실패", f"정규화 작업 중 오류가 발생했습니다:\n\n{str(exception_info['error'])}"
                )
            elif exception_info.get("success_count", 0) > 0:
                messagebox.showinfo(
                    "완료",
                    f"{exception_info['success_count']}개 파일명이 정규화되었습니다."
                )
            else:
                messagebox.showinfo("안내", "자소 분리된 파일을 찾을 수 없습니다.")
        finally:
            # 버튼 활성화
            self.print_button.config(state="normal")
            if hasattr(self, "settings_button"):
                self.settings_button.config(state="normal")

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
            Path.home() / ".wf_rpa" / "korean_filename_normalizer" / "demo_captures",
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

    def _on_manual_capture(self, _event=None):
        """Alt+C: 수동 화면 캡처"""
        if not self.demo_capture_enabled or not self.demo_capture_dir:
            return
        
        try:
            # 쓰로틀링 무시하고 즉시 캡처
            self._last_demo_capture_ts = 0.0
            self._capture_demo_now("manual_capture", throttle_sec=0.0)
        except Exception as e:
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

    def _bind_debug_geometry_hotkey(self):
        """Alt+C를 위한 디버그 핫키 바인딩"""
        try:
            self._start_global_hotkey_listener()
        except Exception:
            pass
    
    # ==================== WF-ACT Test Mode ====================
    def init_test_server(self):
        """WF-ACT 인증 테스트용 TestServer 초기화"""
        try:
            # TestServer import (로컬 test_server.py 사용)
            from test_server import TestServer
            self.test_server = TestServer(app_name="korean_filename_normalizer")
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
        return {"initial_credits": policy.get("trial_credits", 0), "remaining_trial": data.get("remaining_trial", 0), "trial_credits": policy.get("trial_credits", 0)}

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
        cost = self.credit_manager.policy.get("credit_per_work", 0)
        if cost == 0:
            return {"success": True, "processed_count": file_count, "blocked": False, "free_app": True}
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
            "selected_path": self.SELECTED_PATH,
            "is_admin_mode": self.is_admin_mode,
            "credits_display": credits_display
        }

    def _test_get_policy(self) -> dict:
        p = dict(self.credit_manager.policy) if self.credit_manager else {}
        return {"identity": {"app_name": "korean_filename_normalizer", "display_name": "Korean Filename Normalizer"}, "policy": {"credit_per_work": p.get("credit_per_work", 0), "trial_credits": p.get("trial_credits", 0)}, "app_name": "korean_filename_normalizer", **p}

    def _test_get_settings(self) -> dict:
        return {"app_name": "korean_filename_normalizer", "run_mode": getattr(self.config, "run_mode", "release"), "full_version": APP_VERSION_FULL, "version": APP_VERSION_FULL}

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
        bmap = {"work": getattr(self, "start_button", None), "register": getattr(self, "register_button", None), "settings": getattr(self, "settings_button", None)}
        btn = bmap.get(button_name)
        return {"exists": True, "state": str(btn.cget("state")), "text": str(btn.cget("text"))} if btn else {"exists": False}

    def _test_click_button(self, button_name: str) -> bool:
        bmap = {"work": getattr(self, "start_button", None), "register": getattr(self, "register_button", None), "settings": getattr(self, "settings_button", None)}
        btn = bmap.get(button_name)
        if btn and str(btn.cget("state")) != "disabled":
            btn.invoke()
            return True
        return False

    def on_closing(self):
        """앱 종료 처리 (BOM2Excel에서 복사)"""
        # WF-ACT 테스트 서버 정리
        try:
            if hasattr(self, "test_server") and self.test_server:
                self.test_server.stop()
        except Exception:
            pass

        # 전역 핫키 리스너 정리
        try:
            self._stop_global_hotkey_listener()
        except Exception:
            pass

        # 관리자 모드 정리
        if self.is_admin_mode:
            self.remove_log_handler()

        # 앱 종료 시: 로컬 크레딧에 변경이 있다면 마지막으로 동기화 시도 (베스트에포트)
        try:
            if getattr(self, "credit_manager", None):
                # 무료앱이지만 사용 로그 동기화
                sync_status = self.credit_manager.get_sync_status()
                if sync_status.get("needs_sync"):
                    self.logger.info("크레딧 사용 로그 동기화 시도...")
                    self.credit_manager.check_and_sync_credits()
        except Exception as e:
            if self.logger:
                self.logger.warning(f"[SYNC-EXIT] 동기화 시도 중 오류: {e}")

        self.clear_execution_status()
        self.master.destroy()

    def select_folder_license_check(self):
        """폴더 선택 전 라이선스 및 하드웨어 검증 (BOM2Excel에서 복사)"""
        # 1. 등록 여부 확인
        if not self.is_registered_user:
            if self.logger:
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
            if self.logger:
                self.logger.error(
                    "등록된 사용자의 하드웨어 정보와 일치하지 않습니다. 다른 컴퓨터에서는 사용할 수 없습니다."
                )
            messagebox.showerror(
                "인증 실패",
                "등록된 사용자의 하드웨어 정보와 일치하지 않습니다.\n다른 컴퓨터에서는 사용할 수 없습니다.",
            )
            return

        # 폴더 선택
        current_dir = self.folder_path.get().strip() or self.config.get("default_folder_path", "")
        selected_path = filedialog.askdirectory(initialdir=current_dir if current_dir else None)
        if not selected_path:
            return

        self.folder_path.set(selected_path)

        # 선택된 폴더 저장
        try:
            self.config.update_ui_last_folder(selected_path)
        except Exception as e:
            if self.logger:
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

    def update_file_count_display(self):
        """파일 카운트 표시 업데이트 (progress_label로 표시)"""
        try:
            if hasattr(self, "progress_label"):
                if self.initial_file_count > 0:
                    self.progress_label.config(
                        text=f"{self.cumulative_processed_count}/{self.initial_file_count}"
                    )
                else:
                    self.progress_label.config(text="?/?")
        except Exception as e:
            if self.logger:
                self.logger.error(f"파일 카운트 표시 업데이트 오류: {e}")

    def update_progress_ui(self, current, total, status_text=""):
        """진행 상황 업데이트 (BOM2Excel에서 복사)"""

        def _update():
            try:
                # 프로그레스 바가 업데이트될 때 스피너 정지
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
                if self.logger:
                    self.logger.error(f"Progress UI update failed: {e}")

        # 메인 스레드에서 실행
        try:
            self.master.after(0, _update)
        except Exception:
            _update()

    def start_spinner(self):
        """스피너 애니메이션 시작 (BOM2Excel에서 복사)"""

        def _start():
            if not self.spinner_running:
                self.spinner_running = True
                self.spinner_index = 0
                self._animate_spinner()

        try:
            self.master.after(0, _start)
        except Exception:
            _start()

    def stop_spinner(self):
        """스피너 애니메이션 중지 (BOM2Excel에서 복사)"""

        def _stop():
            self.spinner_running = False
            self.spinner_label.config(text="", fg="black")

        try:
            self.master.after(0, _stop)
        except Exception:
            _stop()

    def _animate_spinner(self):
        """스피너 애니메이션 실행 (BOM2Excel에서 복사)"""
        if self.spinner_running:
            spinner_char = self.spinner_chars[self.spinner_index]
            self.spinner_label.config(text=spinner_char, fg="black")

            self.spinner_index = (self.spinner_index + 1) % len(self.spinner_chars)
            self.master.after(100, self._animate_spinner)

    def check_update(self):
        """업데이트 확인"""
        try:
            messagebox.showinfo("업데이트", "현재 최신 버전입니다.")
        except Exception as e:
            if self.logger:
                self.logger.error(f"업데이트 확인 오류: {e}")

    def on_exit(self):
        """종료 처리"""
        try:
            self.clear_execution_status()
        except:
            pass
        self.master.destroy()

    def browse_folder(self):
        """폴더 선택 다이얼로그"""
        folder = filedialog.askdirectory()
        if folder:
            self.folder_path.set(folder)

    def check_target_files(self):
        """대상 파일 확인"""
        folder = self.folder_path.get()

        def on_scan_toggle(self):
            """폴더 스캔 토글 처리 (자소 분리 파일만 카운트, 보류 목록 지원)"""
            if self.scan_toggle_var.get():
                folder_path = self.folder_path.get().strip()
                if not folder_path:
                    messagebox.showwarning("폴더 미선택", "먼저 작업할 폴더를 선택해주세요.")
                    self.scan_toggle_var.set(False)
                    return

                try:
                    if self.logger:
                        self.logger.info(f"폴더 스캔 시작: {folder_path}")

                    # 보류 목록 로드 (있으면 해당 파일만 대상으로 제한)
                    from pathlib import Path

                    folder = Path(folder_path)
                    pending_path = folder / "wf_pending_list.txt"
                    pending_names = set()
                    if pending_path.exists():
                        try:
                            with open(pending_path, "r", encoding="utf-8") as pf:
                                for line in pf:
                                    name = line.strip()
                                    if name:
                                        pending_names.add(name.lower())
                        except Exception as pe:
                            if self.logger:
                                self.logger.warning(f"보류 목록 읽기 실패(무시): {pe}")

                    # 자소 분리 여부로 필터링
                    from automation import KoreanNormalizer

                    normalizer = KoreanNormalizer()
                    count = 0
                    for root, dirs, files in os.walk(folder_path):
                        for file in files:
                            if pending_names and file.lower() not in pending_names:
                                continue
                            if normalizer.is_korean_decomposed(file):
                                count += 1

                    file_count = count
                    if file_count > 0:
                        self.initial_file_count = file_count
                        self.cumulative_processed_count = 0
                        self.is_first_run = True
                        self.last_run_success_count = 0
                        self.progress_bar.config(maximum=self.initial_file_count)
                        self.progress_bar["value"] = 0
                        self.progress_label.config(text=f"0/{self.initial_file_count}")
                        self.print_button.config(state="normal")
                        if self.logger:
                            self.logger.info(f"폴더 스캔 완료: {file_count}개 파일")
                    else:
                        self.print_button.config(state="disabled")
                        self.progress_label.config(text="파일 없음")
                        messagebox.showinfo("스캔 완료", "작업 대상 파일이 없습니다.")
                        self.scan_toggle_var.set(False)
                except Exception as e:
                    if self.logger:
                        self.logger.error(f"폴더 스캔 중 오류: {e}")
                    self.print_button.config(state="disabled")
                    self.progress_label.config(text="오류")
                    messagebox.showerror("스캔 오류", f"폴더 스캔 중 오류가 발생했습니다:\n{e}")
                    self.scan_toggle_var.set(False)
            else:
                self.print_button.config(state="disabled")
                self.progress_label.config(text="?/?")
                if self.logger:
                    self.logger.info("폴더 스캔 초기화")
            return

        # 등록 + 하드웨어 검증 (무료 앱이지만 등록은 필수)
        if not self.is_registered_user:
            messagebox.showwarning(
                "사용자 등록 필요",
                "무료 앱이라도 사용자 등록이 필요합니다. '등 록' 버튼을 눌러주세요.",
            )
            return

        if not self.verify_hardware_fingerprint():
            messagebox.showerror("인증 실패", "등록된 사용자의 하드웨어 정보와 일치하지 않습니다.")
            return

        try:
            # 버튼 비활성화 (메인 버튼만)
            self.print_button.config(state="disabled")
            self.settings_button.config(state="disabled")

            def worker():
                exception_info = {
                    "error": None,
                    "total_files": 0,
                    "success_count": 0,
                    "file_list": [],
                }

                try:
                    # 백업 비활성화 설정
                    config = get_config()
                    config.set("backup_enabled", False)

                    processor = FilenameProcessor(config=config, log_callback=self.log_message)

                    # 1. 자소 분리 파일 찾기
                    target_files = processor.find_decomposed_files(folder)
                    exception_info["total_files"] = len(target_files)

                    if len(target_files) > 0:
                        # 파일 목록 저장 (변환 전/후)
                        exception_info["file_list"] = [
                            {
                                "original": file_info["original_name"],
                                "normalized": file_info["normalized_name"],
                                "path": str(file_info["original_path"]),
                            }
                            for file_info in target_files
                        ]

                        # 2. 변환 실행
                        processor.execute_conversion(folder)
                        exception_info["success_count"] = len(target_files)
                        
                        # 3. 크레딧 사용 로그 기록 (무료 앱이지만 로그는 남김)
                        if self.credit_manager:
                            try:
                                # deduct_credits_by_policy는 무료 앱이면 로그만 기록하고 실제 차감은 하지 않음
                                # 일괄 처리로 file_count 정보를 정확히 전달
                                file_count = len(target_files)
                                self.credit_manager.deduct_credits_by_policy(
                                    item_count=file_count,
                                    description=f'자소분리 복원: {file_count}개 파일'
                                )
                                self.logger.info(
                                    f"크레딧 사용 로그 기록 완료: {file_count}개 파일"
                                )
                            except Exception as e:
                                self.logger.warning(f"크레딧 로그 기록 실패(무시): {e}")

                except Exception as e:
                    exception_info["error"] = e
                finally:
                    self.master.after(0, lambda: self.on_normalization_complete(exception_info))

            threading.Thread(target=worker, daemon=True, name="Normalization-Worker").start()

        except Exception as e:
            messagebox.showerror("작업 실패", f"정규화 작업 중 오류가 발생했습니다:\n\n{str(e)}")

    def _shorten_filename(self, filename, max_length=40):
        """파일명을 축약하여 표시 (앞부분 위주)"""
        if len(filename) <= max_length:
            return filename

        # 확장자 분리
        name_parts = filename.rsplit(".", 1)
        if len(name_parts) == 2:
            name, ext = name_parts
            # 확장자 포함해서 max_length 내로 축약
            available = max_length - len(ext) - 4  # "..." + "."
            if available > 0:
                return f"{name[:available]}...{ext}"

        # 확장자 없거나 너무 긴 경우
        return f"{filename[:max_length-3]}..."

    def show_results_popup(self, file_list, total_count, success_count):
        """결과를 팝업창으로 표시 (테이블 형태)"""
        # 팝업 창 생성
        popup = tk.Toplevel(self.master)
        popup.title("📋 파일명 정규화 결과")
        popup.geometry("900x600")
        popup.transient(self.master)
        popup.grab_set()
        popup.wm_attributes("-topmost", 1)

        # 메인 프레임
        main_frame = ttk.Frame(popup, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 통계 프레임
        stats_frame = ttk.Frame(main_frame)
        stats_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(
            stats_frame, text=f"자소분리 대상: {total_count}개", font=("Arial", 13, "bold")
        ).pack(side=tk.LEFT, padx=10)
        ttk.Label(
            stats_frame,
            text=f"복원완료: {success_count}개",
            font=("Arial", 13, "bold"),
            foreground="green",
        ).pack(side=tk.LEFT, padx=10)

        # 트리뷰 (테이블)
        table_frame = ttk.Frame(main_frame)
        table_frame.pack(fill=tk.BOTH, expand=True)

        columns = ("번호", "자소분리파일", "복원파일")
        results_tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=20)

        # 컬럼 설정
        results_tree.heading("번호", text="번호")
        results_tree.heading("자소분리파일", text="자소분리 파일")
        results_tree.heading("복원파일", text="복원 파일")

        results_tree.column("번호", width=50, anchor=tk.CENTER)
        results_tree.column("자소분리파일", width=400, anchor=tk.W)
        results_tree.column("복원파일", width=400, anchor=tk.W)

        # 스크롤바
        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=results_tree.yview)
        results_tree.configure(yscrollcommand=scrollbar.set)

        results_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 데이터 추가
        for i, file_info in enumerate(file_list, 1):
            original = self._shorten_filename(file_info["original"])
            normalized = self._shorten_filename(file_info["normalized"])

            results_tree.insert("", "end", values=(i, original, normalized))

        # 닫기 버튼
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Button(button_frame, text="닫기", command=popup.destroy).pack(side=tk.RIGHT)

        # 메인 앱 중심에 배치
        popup.update_idletasks()
        popup_width = popup.winfo_width()
        popup_height = popup.winfo_height()
        main_x = self.master.winfo_rootx()
        main_y = self.master.winfo_rooty()
        main_width = self.master.winfo_width()
        main_height = self.master.winfo_height()
        x = main_x + (main_width - popup_width) // 2
        y = main_y + (main_height - popup_height) // 2
        popup.geometry(f"+{x}+{y}")

    def on_normalization_complete(self, exception_info):
        """정규화 완료 처리"""
        try:
            # 버튼 활성화
            self.print_button.config(state="normal")
            self.settings_button.config(state="normal")

            if exception_info.get("error"):
                error = exception_info["error"]
                messagebox.showerror("작업 실패", f"정규화 중 오류가 발생했습니다:\n\n{str(error)}")
            else:
                total = exception_info.get("total_files", 0)
                success = exception_info.get("success_count", 0)
                file_list = exception_info.get("file_list", [])

                if total == 0:
                    self.progress_label.config(text="자소 분리 파일이 없습니다.")
                    messagebox.showinfo("완료", "자소 분리가 필요한 파일이 없습니다.")
                else:
                    self.progress_label.config(text=f"({success}/{total})")

                    # 테이블 형태의 결과 팝업 표시
                    self.show_results_popup(file_list, total, success)

                # 백그라운드 동기화
                def background_sync():
                    try:
                        if getattr(self, "credit_manager", None):
                            sync_status = self.credit_manager.get_sync_status()
                            if sync_status.get("needs_sync"):
                                if self.logger:
                                    self.logger.info("🧾 처리 완료 후 사용 내역 동기화 시도 (백그라운드)...")
                                log_result = self.credit_manager.check_and_sync_credits()
                                if self.logger:
                                    self.logger.info(f"[SYNC-AFTER-RUN] {log_result}")
                    except Exception as e:
                        if self.logger:
                            self.logger.warning(f"[USAGE-LOG-AFTER-RUN] 사용 로그 기록 중 오류: {e}")
                
                # 백그라운드 스레드로 동기화 실행
                threading.Thread(target=background_sync, daemon=True, name="Credit-Sync-Worker").start()

        except Exception as e:
            if self.logger:
                self.logger.error(f"Progress UI update failed: {e}")

    def log_message(self, message):
        """로그 메시지 출력"""
        if self.logger:
            self.logger.info(message)
        print(f"[LOG] {message}")

    def _schedule_recovery(self):
        """정책 동기화 스케줄 (무료 앱이므로 구매 이력 없이 정책만 동기화)"""

        def _worker():
            try:
                if self.credit_manager and self.logger:
                    self.logger.info("🔄 백그라운드 정책 동기화 실행...")
                    result = self.credit_manager.check_and_sync_credits()
                    self.logger.info(f"[STARTUP-RECOVERY] {result}")
                    # UI 업데이트
                    self.master.after(0, self.update_credit_display)
            except Exception as e:
                if self.logger:
                    self.logger.warning(f"[STARTUP-RECOVERY] 오류: {e}")

        threading.Thread(target=_worker, daemon=True).start()

    def check_user_registration(self):
        """사용자 등록 상태 확인"""
        # 테스트 편의: 환경변수로 강제 등록 처리
        try:
            if os.environ.get("WF_FORCE_REGISTERED") == "1":
                return True
        except Exception:
            pass

        if not self.wf_manager:
            return False

        user_info = self.wf_manager.get_user_info()
        # 표준 키: user_email (wf_credit_manager.register_user에서 저장). 하위호환 user_mail 지원
        reg_email = user_info.get("user_email") or user_info.get("user_mail")
        is_registered = bool(reg_email)

        try:
            if is_registered:
                import wf_hwinfo

                # wf_credit_manager는 client_hw_fingerprint 키를 사용
                stored_fingerprint = user_info.get("client_hw_fingerprint") or user_info.get(
                    "hardware_fingerprint", ""
                )
                current_fingerprint = wf_hwinfo.HardwareInfo().fingerprint
                if self.logger:
                    self.logger.debug(f"기존 지문: {stored_fingerprint}")
                    self.logger.debug(f"현재 지문: {current_fingerprint}")
                return stored_fingerprint == current_fingerprint
        except Exception as e:
            if self.logger:
                self.logger.error(f"하드웨어 검증 실패: {e}")
            return False
        return is_registered

    def verify_hardware_fingerprint(self):
        """하드웨어 핑거프린트 검증"""
        # 테스트 편의: 환경변수로 강제 통과
        try:
            if os.environ.get("WF_FORCE_REGISTERED") == "1":
                return True
        except Exception:
            pass
        try:
            stored_hardware = self.wf_manager.get_user_info()
            stored_fingerprint = stored_hardware.get(
                "client_hw_fingerprint"
            ) or stored_hardware.get("hardware_fingerprint", "")

            import wf_hwinfo

            current_fingerprint = wf_hwinfo.HardwareInfo().fingerprint

            return stored_fingerprint == current_fingerprint
        except Exception as e:
            if self.logger:
                self.logger.error(f"하드웨어 검증 실패: {e}")
            return False

    def open_settings_window(self):
        """설정 창 표시"""
        try:
            result = create_settings_window(self.master, self.config, self.icon_path)
            # 설정이 저장되었다면 기본 폴더 값을 반영
            if result:
                try:
                    new_default = (self.config.get("default_folder_path", "") or "").strip()
                    if new_default:
                        self.folder_path.set(new_default)
                except Exception:
                    pass
        except Exception as e:
            messagebox.showerror("설정 오류", f"설정 창을 열 수 없습니다:\\n{e}")

    def _get_downloads_folder(self) -> str:
        """사용자 Downloads 폴더 경로를 반환 (Windows 우선, 크로스플랫폼 폴백)."""
        try:
            # 1) 일반적인 경로 시도
            home = os.path.expanduser("~")
            candidate = os.path.join(home, "Downloads")
            if os.path.isdir(candidate):
                return candidate
            # 2) Windows Known Folder API 시도
            if os.name == "nt":
                try:
                    import ctypes, ctypes.wintypes as wt
                    from uuid import UUID

                    # FOLDERID_Downloads
                    downloads_guid = UUID("{374DE290-123F-4565-9164-39C4925E467B}")
                    _SHGetKnownFolderPath = ctypes.windll.shell32.SHGetKnownFolderPath

                    class GUID(ctypes.Structure):
                        _fields_ = [
                            ("Data1", ctypes.c_uint32),
                            ("Data2", ctypes.c_uint16),
                            ("Data3", ctypes.c_uint16),
                            ("Data4", ctypes.c_ubyte * 8),
                        ]

                    _SHGetKnownFolderPath.argtypes = [
                        ctypes.POINTER(GUID),
                        ctypes.c_uint32,
                        wt.HANDLE,
                        ctypes.POINTER(ctypes.c_wchar_p),
                    ]
                    _SHGetKnownFolderPath.restype = ctypes.c_long

                    def uuid_to_guid(u: UUID) -> GUID:
                        data4 = (ctypes.c_ubyte * 8)(*u.bytes[8:])
                        return GUID(u.time_low, u.time_mid, u.time_hi_version, data4)

                    guid = uuid_to_guid(downloads_guid)
                    pPath = ctypes.c_wchar_p()
                    # Flags: 0 -> default
                    hr = _SHGetKnownFolderPath(ctypes.byref(guid), 0, None, ctypes.byref(pPath))
                    if hr == 0 and pPath.value and os.path.isdir(pPath.value):
                        return pPath.value
                except Exception:
                    pass
            # 3) 폴백: 홈 디렉터리
            return home
        except Exception:
            return os.path.expanduser("~")

    def open_registration_window(self):
        """등록 창 표시 (지연 임포트)"""
        try:
            try:
                from wf_register import create_trial_window  # lazy import
            except Exception as e:
                messagebox.showerror("등록 오류", f"등록 모듈을 찾을 수 없습니다.\n{e}")
                return

            # 공통 등록 창 생성 (모달로 동작하며 open_trial_window 내부에서 grab_set)
            reg = create_trial_window(self, ui_settings=self.ui)

            # 창이 닫힐 때까지 대기 후 등록 상태 재평가
            if reg and hasattr(reg, "trial_win") and reg.trial_win:
                self.master.wait_window(reg.trial_win)
                # 창 닫힌 후 등록 성공 여부 재확인
                if self.check_user_registration():
                    self.post_registration_update()

        except Exception as e:
            if self.logger:
                self.logger.error("등록 창 함수를 호출할 수 없습니다.")
            messagebox.showerror("등록 오류", "등록 창을 표시할 수 없습니다.")

    def post_registration_update(self):
        """등록 절차 완료 후 UI를 업데이트합니다."""
        self.is_registered_user = self.check_user_registration()
        try:
            if getattr(self, "settings_button", None):
                if self.is_registered_user:
                    self.settings_button.config(text="설 정", command=self.open_settings_window)
                else:
                    self.settings_button.config(text="등 록", command=self.open_registration_window)
        except Exception:
            pass
        self.update_credit_display()
        messagebox.showinfo("등록 완료", "사용자 등록이 완료되었습니다!")

    def on_progress_label_click(self, event):
        """크레딧 라벨 클릭 이벤트 - 관리자 모드 토글"""
        try:
            if self.is_admin_mode:
                self._exit_admin_mode()
                self._show_toast("관리자 모드 비활성화", 1500)
                self.update_credit_display()
            else:
                run_mode = getattr(self.config, "run_mode", getattr(self.config, "get", lambda *_: "release")("run_mode", "release"))
                if run_mode == "dev":  # dev 모드에서만 암호 없이 진입
                    self._enter_admin_mode()
                else:
                    from tkinter import simpledialog

                    password = simpledialog.askstring(
                        "관리자 인증", "관리자 비밀번호를 입력하세요:", show="*", parent=self.master
                    )

                    if password == self.admin_password:
                        self._enter_admin_mode()
                    else:
                        if password is not None:
                            messagebox.showerror("인증 실패", "관리자 비밀번호가 올바르지 않습니다.")
        except Exception as e:
            if self.logger:
                self.logger.error(f"관리자 모드 토글 오류: {e}")

    def _enter_admin_mode(self):
        """관리자 모드 진입"""
        self.is_admin_mode = True
        self.admin_mode_start_time = datetime.datetime.now()

        # 30분 후 자동 해제 타이머 설정
        self.admin_mode_timer = self.master.after(1800000, self._auto_exit_admin_mode)

        # 창 크기 확장
        current_geometry = self.master.geometry()
        width = current_geometry.split("x")[0]
        pos = current_geometry.split("+", 1)[1] if "+" in current_geometry else "0+0"
        new_geometry = f"{width}x{self.expanded_window_height}+{pos}"
        self.master.geometry(new_geometry)

        # 창 타이틀 변경
        self.master.title(f"한글 파일명 복원 {APP_VERSION_FULL} [🔧 관리자 모드]")

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
        if self.is_admin_mode:
            print("관리자 모드를 종료합니다")

        self.destroy_log_frame()

        # 창 크기 복원
        current_geometry = self.master.geometry()
        width = current_geometry.split("x")[0]
        pos = current_geometry.split("+", 1)[1] if "+" in current_geometry else "0+0"
        new_geometry = f"{width}x{self.original_window_height}+{pos}"
        self.master.geometry(new_geometry)

        self.master.title(f"한글 파일명 복원 {APP_VERSION_DISPLAY}")

        # 프로그레스 초기화
        self.progress_bar["value"] = 0
        self.progress_bar.config(maximum=100)
        self.progress_label.config(text="0/0")
        self.spinner_label.config(text="○", fg="#cccccc")

        self.is_admin_mode = False
        self.admin_mode_start_time = None

        if self.admin_mode_timer:
            self.master.after_cancel(self.admin_mode_timer)
            self.admin_mode_timer = None

        self._show_toast("관리자 모드 비활성화", 1000)

    def _auto_exit_admin_mode(self):
        """30분 후 자동 관리자 모드 종료"""
        self._exit_admin_mode()
        self._show_toast("관리자 모드 자동 해제", 1500)
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
        self.log_frame.pack(fill="both", expand=True, pady=(10, 0))

        # 로그 제목 및 옵션
        log_header_frame = tk.Frame(self.log_frame)
        log_header_frame.pack(fill="x", pady=(0, 5))

        log_label = tk.Label(
            log_header_frame,
            text="실시간 로그 (DEBUG 레벨)",
            font=("맑은 고딕", self.ui["font_size"], "bold"),
        )
        log_label.pack(side="left")

        # 자동 스크롤 체크박스
        self.auto_scroll_var = tk.BooleanVar(value=True)
        self.auto_scroll_checkbox = tk.Checkbutton(
            log_header_frame,
            text="자동 스크롤",
            variable=self.auto_scroll_var,
            font=("맑은 고딕", self.ui["font_size"]),
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

        # 테스트 버튼 프레임 추가
        test_button_frame = tk.Frame(self.log_frame)
        test_button_frame.pack(fill="x", pady=(5, 0))

        tk.Button(
            test_button_frame,
            text="테스트 데이터 생성",
            command=self.create_test_data,
            width=20,
            bg="#e8f5e9",
        ).pack(side="left", padx=5)
        tk.Button(
            test_button_frame,
            text="테스트 데이터 삭제",
            command=self.delete_test_data,
            width=20,
            bg="#ffebee",
        ).pack(side="left", padx=5)

        # 로그 핸들러 설정
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
                        self.text_widget.insert("end", msg + "\\n")

                        lines = int(self.text_widget.index("end-1c").split(".")[0])
                        if lines > 1000:
                            self.text_widget.delete("1.0", "500.0")

                        self.text_widget.config(state="disabled")

                        if self.auto_scroll_var and self.auto_scroll_var.get():
                            self.text_widget.see("end")
                except Exception:
                    pass

        self.remove_log_handler()

        self.text_handler = TextHandler(self.log_text, self.auto_scroll_var, self.master)
        self.text_handler.setLevel(logging.DEBUG)

        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        self.text_handler.setFormatter(formatter)

        # 루트 로거에 핸들러 추가
        root_logger = logging.getLogger()
        root_logger.addHandler(self.text_handler)

        if self.logger:
            self.logger.addHandler(self.text_handler)

    def remove_log_handler(self):
        """로그 핸들러 제거"""
        if hasattr(self, "text_handler"):
            try:
                root_logger = logging.getLogger()
                root_logger.removeHandler(self.text_handler)

                if self.logger:
                    self.logger.removeHandler(self.text_handler)

                delattr(self, "text_handler")
            except Exception:
                pass

    def _show_toast(self, message, duration=2000):
        """토스트 메시지 표시"""
        toast = tk.Toplevel(self.master)
        toast.wm_overrideredirect(True)
        toast.configure(bg="black")

        toast_width = 300
        toast_height = 50
        x = (toast.winfo_screenwidth() // 2) - (toast_width // 2)
        y = toast.winfo_screenheight() - 100
        toast.geometry(f"{toast_width}x{toast_height}+{x}+{y}")

        label = tk.Label(
            toast,
            text=message,
            fg="white",
            bg="black",
            font=("맑은 고딕", self.ui["font_size_bold"]),
        )
        label.pack(expand=True)

        toast.after(duration, toast.destroy)

    def create_test_data(self):
        """테스트 데이터 생성: 현재 작업 폴더의 ./test 에 샘플 파일 생성 후 UI 자동 연결"""
        try:
            from pathlib import Path
            import shutil
            import random
            import unicodedata

            # 테스트 데이터는 앱 상위 폴더에 생성 (50.data/test)
            base = Path(__file__).parent / "test"
            if base.exists():
                try:
                    shutil.rmtree(base)
                except Exception:
                    pass
            base.mkdir(parents=True, exist_ok=True)

            names = [
                "한글문서",
                "업무자료",
                "설계도면",
                "프로젝트계획서",
                "회의록",
                "한글_파일",
                "기술_문서",
                "데모_자소분리",
                "테스트_파일",
                "샘플_데이터",
                "설계도면",
                "분석_결과",
                "도면_자료",
                "공장_처리",
                "샘플_A",
                "테스트_B",
                "결과_C",
                "혼합_D",
                "영어File",
                "자소_F",
            ]
            exts = [".txt", ".docx", ".xlsx", ".pdf", ".dwg"]
            created = 0

            # 1. 순수 한글 (NFC 정규화 - 정상)
            pure_korean = ["한글문서", "업무자료", "설계도면", "프로젝트", "회의록"]
            for name in pure_korean:
                p = base / f"{name}{exts[created % len(exts)]}"
                p.write_text("순수 한글 테스트", encoding="utf-8")
                created += 1

            # 2. 한글-영어 혼합
            korean_english = [
                "한글File",
                "Report한글",
                "설계Drawing",
                "Project프로젝트",
                "Data자료",
            ]
            for name in korean_english:
                p = base / f"{name}{exts[created % len(exts)]}"
                p.write_text("한영 혼합 테스트", encoding="utf-8")
                created += 1

            # 3. 한글-숫자 혼합
            korean_number = ["문서2024", "파일123", "도면001", "자료999", "보고서2025"]
            for name in korean_number:
                p = base / f"{name}{exts[created % len(exts)]}"
                p.write_text("한글숫자 혼합 테스트", encoding="utf-8")
                created += 1

            # 4. NFD 분해 (자소분리 문제 케이스)
            nfd_decomposed = ["한글문서NFD", "설계자료NFD", "업무파일NFD", "테스트NFD", "샘플NFD"]
            for name in nfd_decomposed:
                # NFD로 분해하여 자소분리 발생시킴
                nfd_name = unicodedata.normalize("NFD", name)
                p = base / f"{nfd_name}{exts[created % len(exts)]}"
                p.write_text("NFD 분해 테스트", encoding="utf-8")
                created += 1

            # 5. 종성(받침) 케이스 - Unicode Jamo 영역 사용
            # ㄱ(U+3131), ㄴ(U+3134), ㄷ(U+3137), ㄹ(U+3139), ㅁ(U+3141), ㅂ(U+3142), ㅅ(U+3145), ㅇ(U+3147)
            jongseong_cases = [
                "ㄱ받침테스트",
                "ㄴ받침자료",
                "ㄷ받침문서",
                "ㄹ받침파일",
                "ㅁ받침도면",
                "ㅂ받침데이터",
                "ㅅ받침샘플",
                "ㅇ받침업무",
            ]
            for name in jongseong_cases:
                p = base / f"{name}{exts[created % len(exts)]}"
                p.write_text("종성(받침) 테스트", encoding="utf-8")
                created += 1

            # 6. 중성(모음) 케이스
            # ㅏ(U+314F), ㅓ(U+3153), ㅗ(U+3157), ㅜ(U+315C), ㅡ(U+3161), ㅣ(U+3163)
            jungseong_cases = [
                "ㅏ모음테스트",
                "ㅓ모음자료",
                "ㅗ모음문서",
                "ㅜ모음파일",
                "ㅡ모음도면",
                "ㅣ모음데이터",
            ]
            for name in jungseong_cases:
                p = base / f"{name}{exts[created % len(exts)]}"
                p.write_text("중성(모음) 테스트", encoding="utf-8")
                created += 1

            # 7. 복합 케이스: 자모 + NFD + 일반 혼합
            mixed_cases = [
                unicodedata.normalize("NFD", "혼합케이스ㄱ"),
                unicodedata.normalize("NFD", "ㅏㅓㅗ자소분리"),
                "ㄱㄴㄷㄹㅁ자모만",
                unicodedata.normalize("NFD", "한글") + "File123",
                "ㅎㅏㄴㄱㅡㄹ자모문자열",
            ]
            for name in mixed_cases:
                p = base / f"{name}{exts[created % len(exts)]}"
                p.write_text("복합 케이스 테스트", encoding="utf-8")
                created += 1

            # UI에 test 폴더 지정 및 스캔 실행해 좌측 버튼 활성화
            try:
                self.set_selected_path(str(base))
                self.scan_current_folder()
            except Exception:
                pass

            if self.logger:
                self.logger.info(f"테스트 데이터 생성 완료: {created}개 -> {base}")
            messagebox.showinfo(
                "완료",
                f"테스트 데이터가 생성되었습니다!\n위치: {base}\n파일: {created}개\n\n케이스:\n- 순수 한글: 5개\n- 한영 혼합: 5개\n- 한숫자 혼합: 5개\n- NFD 분해: 5개\n- 종성(받침): 8개\n- 중성(모음): 6개\n- 복합: 5개",
                parent=self.master,
            )
        except Exception as e:
            if self.logger:
                self.logger.error(f"테스트 데이터 생성 실패: {e}", exc_info=True)
            messagebox.showerror("오류", f"테스트 데이터 생성 실패:\n{e}", parent=self.master)

    def delete_test_data(self):
        """테스트 데이터 삭제: 상위 폴더의 ./test 제거 및 UI 정리"""
        try:
            from pathlib import Path
            import shutil
            import os, stat

            # 생성 경로와 동일하게 앱 상위 폴더의 test를 대상으로 삭제 (50.data/test)
            target = Path(__file__).parent / "test"
            if not target.exists():
                messagebox.showinfo("알림", "삭제할 테스트 데이터가 없습니다.", parent=self.master)
                return

            def _onerror(func, path, exc_info):
                try:
                    os.chmod(path, stat.S_IWRITE)
                    func(path)
                except Exception:
                    pass

            shutil.rmtree(target, onerror=_onerror)

            # 선택된 폴더가 test였다면 UI 초기화
            try:
                if self.SELECTED_PATH and Path(self.SELECTED_PATH) == target:
                    self.set_selected_path(None)
            except Exception:
                pass

            if self.logger:
                self.logger.info(f"테스트 데이터 삭제 완료: {target}")
            messagebox.showinfo("완료", "테스트 데이터가 삭제되었습니다.", parent=self.master)
        except Exception as e:
            if self.logger:
                self.logger.error(f"테스트 데이터 삭제 실패: {e}", exc_info=True)
            messagebox.showerror("오류", f"테스트 데이터 삭제 실패:\n{e}", parent=self.master)


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

        result = manager.sync_local_registration_to_sheets("korean_filename_normalizer", app_version)

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
    """메인 함수"""
    global _instance_mutex_handle
    # --test-mode 인자 처리 (WF-ACT 인증 테스트 모드)
    test_mode = "--test-mode" in sys.argv

    # --sync-registration 인자 처리 (GUI 없이 동기화만 수행)
    if "--sync-registration" in sys.argv:
        sys.exit(_handle_sync_registration())

    # 3중 안전망: 필수 설정 파일 자동 생성
    # DWG 기준: 별도 ensure_config_files 호출 제거 (wf_rpa_config 접근 시 지연 생성)

    _log_startup("main() called")

    # 테스트 모드에서는 single instance 및 cross-app 체크 건너뛰기
    if not test_mode:
        # Enforce single instance across the system (prevents recursive spawns)
        is_first, _instance_mutex_handle = _acquire_single_instance()
        _log_startup("single instance check complete")
        if not is_first:
            # Avoid creating any UI if another instance is running
            try:
                print("Another korean_filename_normalizer instance is already running. Exiting.")
            except Exception:
                pass
            return

        # 교차 앱 실행 방지 (공통 헬퍼 사용)
        if check_cross_app_running_and_exit:
            check_cross_app_running_and_exit("korean_filename_normalizer")

        _log_startup("single instance guard passed")
    else:
        _log_startup("Test mode: skipping single instance and cross-app checks")

    # Mark running for cross-app guard and ensure cleanup on exit
    try:
        _set_cross_app_running("korean_filename_normalizer")
        import atexit as _atexit

        _atexit.register(_clear_cross_app_running)
    except Exception:
        pass

    root = tk.Tk()
    # 시작 시 플래시 방지: 초기화 전 잠시 숨김
    try:
        root.withdraw()
    except Exception:
        pass
    _log_startup("Tk() created")
    
    # 작업표시줄 아이콘 설정 (개발/릴리스 환경 모두 지원)
    try:
        # 아이콘 파일명 (새 아이콘: 06_Korean_Filename_Normalizer.ico, 기존: KFN.ico)
        icon_names = ["06_Korean_Filename_Normalizer.ico", "KFN.ico"]

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
            else Path.home() / ".wf_rpa" / "korean_filename_normalizer" / "res"
        )
        bundle_candidates = [Path(__file__).parent / "res"]
        if getattr(sys, "frozen", False):
            exe_dir = Path(sys.executable).parent
            bundle_candidates = [exe_dir / "res", exe_dir / "_internal" / "res"] + bundle_candidates
        seed_res_if_missing(target_res, bundle_candidates, logger=None)
    except Exception:
        pass

    app = KoreanFilenameNormalizerApp(root)
    _log_startup("KoreanFilenameNormalizerApp initialized")

    # WF-ACT 테스트 모드 초기화
    if test_mode:
        try:
            app.init_test_server()
        except Exception as e:
            print(f"[WF-ACT] Failed to initialize test server: {e}")

    # Startup profiling 완료
    _flush_startup_log()

    # 프로파일링 전용 모드: 환경변수로 지정 시 메인루프 진입 없이 종료하여 빠른 측정 가능
    if os.environ.get("WF_PROFILE_ONLY") == "1":
        try:
            root.destroy()
        except Exception:
            pass
        return

    def on_closing():
        try:
            # cross-app 상태 정리는 atexit/모듈 헬퍼에서 처리
            _clear_cross_app_running()
        except Exception:
            pass
        root.destroy()

    # Automated settings window smoke test mode
    if os.environ.get("WF_AUTO_SETTINGS_TEST") == "1":
        try:
            print("[AUTO-TEST] WF_AUTO_SETTINGS_TEST=1 detected; scheduling settings window open.")
            # 등록 우회 제거 - 실제 등록 상태만 사용 (통일된 패턴)
            # WorksFreeManager.is_registered()를 신뢰하도록 변경

            def _auto_show():
                try:
                    print("[AUTO-TEST] Opening settings window...")
                    app.open_settings_window()
                except Exception as e:
                    print(f"[AUTO-TEST] Failed to open settings window: {e}")
                finally:
                    root.after(
                        1200, lambda: (print("[AUTO-TEST] Closing application."), on_closing())
                    )

            root.after(400, _auto_show)
        except Exception as e:
            print(f"[AUTO-TEST] Setup failure: {e}")

    # WF-ACT 테스트 모드 초기화
    if test_mode:
        try:
            app.init_test_server()
        except Exception as e:
            print(f"[WF-ACT] Failed to initialize test server: {e}")

    # 초기화가 끝난 후 창 표시 및 포커스
    try:
        root.deiconify(); root.lift(); root.focus_force()
    except Exception:
        pass
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()
