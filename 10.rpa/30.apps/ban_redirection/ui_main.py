# -*- coding: utf-8 -*-
"""
Ban Redirection Main UI Module
"""
import sys
import os
import json
import time

# Windows 콘솔 UTF-8 강제 설정
if sys.platform == "win32":
    import io
    if sys.stdout is not None and hasattr(sys.stdout, "buffer"):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    if sys.stderr is not None and hasattr(sys.stderr, "buffer"):
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from pathlib import Path


def _detect_run_mode():
    env_mode = (os.environ.get("WF_RPA_MODE") or "").strip().lower()
    if env_mode in ("dev", "demo", "release"):
        return env_mode
    if sys.argv[0].endswith(".py"):
        return "dev"
    return "release"


# ==================== 싱글 인스턴스 락 ====================
_instance_mutex_handle = None


def _acquire_single_instance(mutex_name=r"Global\\WF_BAN_REDIRECTION"):
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
        if kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
            kernel32.CloseHandle(handle)
            return False, None
        return True, handle
    except Exception:
        return True, None


def _set_cross_app_running(app_name: str):
    try:
        import json as _json
        import datetime as _dt
        cfg_dir = Path.home() / ".wf_rpa"
        cfg_dir.mkdir(parents=True, exist_ok=True)
        cfg = cfg_dir / "wf_rpa_config.json"
        data = {}
        if cfg.exists():
            try:
                with open(cfg, "r", encoding="utf-8") as f:
                    data = _json.load(f) or {}
            except Exception:
                data = {}
        es = data.get("execution_status", {})
        es["is_running"] = True
        es["current_app"] = app_name
        es["pid"] = os.getpid()
        es["start_time"] = _dt.datetime.now().isoformat()
        data["execution_status"] = es
        with open(cfg, "w", encoding="utf-8") as f:
            _json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False


def _clear_cross_app_running():
    try:
        import json as _json
        cfg = Path.home() / ".wf_rpa" / "wf_rpa_config.json"
        if not cfg.exists():
            return True
        with open(cfg, "r", encoding="utf-8") as f:
            data = _json.load(f) or {}
        if "execution_status" in data:
            data["execution_status"]["is_running"] = False
            data["execution_status"]["current_app"] = None
            data["execution_status"]["pid"] = None
            data["execution_status"]["start_time"] = None
            with open(cfg, "w", encoding="utf-8") as f:
                _json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False


# ==================== 버전 정보 로드 ====================
def _load_version_info():
    default_full = "v0.7.0.0"
    full_version = default_full
    try:
        if getattr(sys, "frozen", False):
            base_path = Path(sys._MEIPASS) if hasattr(sys, "_MEIPASS") else Path(sys.executable).parent
            settings_file = base_path / ".wf_rpa" / "ban_redirection" / "settings.json"
            if not settings_file.exists():
                settings_file = Path.home() / ".wf_rpa" / "ban_redirection" / "settings.json"
        else:
            app_root = Path(__file__).parent
            settings_file = app_root.parent.parent / "10.common" / "config" / "ban_redirection" / "settings.json"
        if settings_file.exists():
            with open(settings_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            full_version = (
                data.get("runtime_config", {}).get("full_version")
                or data.get("app_config", {}).get("full_version")
                or default_full
            )
            if not full_version.startswith("v"):
                full_version = "v" + full_version
    except Exception:
        pass
    parts = full_version.lstrip("v").split(".")
    display_version = "v" + ".".join(parts[:2])
    return full_version, display_version


APP_VERSION_FULL, APP_VERSION_DISPLAY = _load_version_info()

import threading
import ctypes
import tkinter as tk
import tkinter.ttk as ttk
from tkinter import messagebox, simpledialog

current_dir = Path(__file__).resolve().parent
common_path = current_dir.parent.parent / "10.common"
if common_path.exists() and str(common_path) not in sys.path:
    sys.path.insert(0, str(common_path))

from app_setting_data import get_config, get_config_path

try:
    from wf_log import get_app_logger
    from wf_credit_manager import WorksFreeManager, CreditManager
    from wf_app_init_helpers import init_credit_and_policy_managers
    from wf_register import create_trial_window
    from wf_ui_adaptive import get_adaptive_ui_settings, apply_global_fonts
    from wf_i18n import t, register_app, get_app_locale_dir
    register_app("br", get_app_locale_dir(__file__, "br"))
    WFM_AVAILABLE = True
except ImportError as e:
    import logging
    logging.basicConfig(level=logging.DEBUG)
    get_app_logger = lambda name, **kw: logging.getLogger(name)
    def t(key: str, **kwargs) -> str: return key  # noqa: E704
    messagebox.showerror("Critical Error", f"공통 모듈 로드 실패: {e}")
    WFM_AVAILABLE = False
    sys.exit(1)


class BanRedirectionGUI:
    APP_VERSION_FULL = APP_VERSION_FULL
    APP_VERSION_DISPLAY = APP_VERSION_DISPLAY

    def __init__(self, master):
        self.master = master
        self.config = get_config()
        self.logger = get_app_logger("ban_redirection")

        self.icon_path = self._find_icon_path()
        self.ui = get_adaptive_ui_settings(window_type="main")

        self.wf_manager = None
        self.credit_manager = None
        self.is_registered_user = False
        self._admin_password = None
        self.is_admin_mode = False
        self.admin_mode_timer = None
        self._running = False

        self.original_window_height = 280
        self.expanded_window_height = self.original_window_height + 300

        if WFM_AVAILABLE:
            self.wf_manager = WorksFreeManager()
            self.is_registered_user = self.wf_manager.is_registered()

        self.master.title(t("br.title", ver=APP_VERSION_DISPLAY))
        self.master.protocol("WM_DELETE_WINDOW", self.on_closing)
        if self.config.topmost:
            self.master.wm_attributes("-topmost", 1)

        self.init_ui()
        self._finalize_window_and_show()
        self.master.after(100, self._lazy_init_managers)
        self._bind_keyboard_shortcuts()

    def _find_icon_path(self):
        try:
            if getattr(sys, "frozen", False):
                base_paths = [
                    Path(sys.executable).parent / "res",
                    Path(sys.executable).parent / "_internal" / "res",
                ]
            else:
                base_paths = [Path(__file__).parent / "res"]
            candidates = [bp / "BR.ico" for bp in base_paths]
            return next((p for p in candidates if p.exists()), None)
        except Exception:
            return None

    def init_ui(self):
        master = self.master
        apply_global_fonts(master, self.ui)

        master.grid_rowconfigure(0, weight=1)
        master.grid_columnconfigure(0, weight=1)

        main_frame = tk.Frame(master, padx=12, pady=0)
        main_frame.grid(row=0, column=0, sticky="nsew")
        self._main_frame = main_frame

        font = ("맑은 고딕", self.ui["font_size"])
        lbl_width = 14

        # Primary DNS row
        dns1_frame = tk.Frame(main_frame)
        dns1_frame.pack(fill="x", pady=(8, 4))
        tk.Label(dns1_frame, text=t("br.primary_dns"), width=lbl_width, anchor="w", font=font).pack(side="left")
        self.primary_dns_var = tk.StringVar(value=self.config.primary_dns)
        tk.Entry(dns1_frame, textvariable=self.primary_dns_var, font=font).pack(
            side="left", fill="x", expand=True, padx=(10, 0)
        )

        # Secondary DNS row
        dns2_frame = tk.Frame(main_frame)
        dns2_frame.pack(fill="x", pady=(0, 8))
        tk.Label(dns2_frame, text=t("br.secondary_dns"), width=lbl_width, anchor="w", font=font).pack(side="left")
        self.secondary_dns_var = tk.StringVar(value=self.config.secondary_dns)
        tk.Entry(dns2_frame, textvariable=self.secondary_dns_var, font=font).pack(
            side="left", fill="x", expand=True, padx=(10, 0)
        )

        # Status row: [관리자권한] [인터페이스 수] [크레딧]
        status_frame = tk.Frame(main_frame)
        status_frame.pack(fill="x", pady=(0, 4))
        status_frame.columnconfigure(0, weight=1)
        status_frame.columnconfigure(1, weight=1)
        status_frame.columnconfigure(2, weight=1)

        try:
            is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception:
            is_admin = False
        admin_text = t("br.admin_ok") if is_admin else t("br.admin_fail")
        admin_color = "green" if is_admin else "red"
        self.admin_status_label = tk.Label(
            status_frame, text=admin_text, fg=admin_color,
            font=font, cursor="hand2"
        )
        self.admin_status_label.grid(row=0, column=0, sticky="w")
        self.admin_status_label.bind("<Button-1>", self.on_status_label_click)

        self.interface_label = tk.Label(
            status_frame, text=t("br.interface_checking"), font=font
        )
        self.interface_label.grid(row=0, column=1)

        self.credit_label = tk.Label(
            status_frame, text=t("credits_checking"), fg="blue", font=font, cursor="hand2"
        )
        self.credit_label.grid(row=0, column=2, sticky="e")
        self.credit_label.bind("<Button-1>", self.on_status_label_click)

        # Buttons
        button_frame = tk.Frame(main_frame)
        button_frame.pack(fill="x", pady=(8, 8))
        button_frame.columnconfigure(0, weight=1)
        button_frame.columnconfigure(1, weight=1)

        self.run_button = tk.Button(
            button_frame, text=t("br.run_button"), command=self.start_fix,
            width=14, height=1, font=font,
        )
        self.run_button.grid(row=0, column=0, padx=5, sticky="ew")

        self.exit_button = tk.Button(
            button_frame, text=t("exit_button"), command=self.on_closing,
            width=14, height=1, font=font,
        )
        self.exit_button.grid(row=0, column=1, padx=5, sticky="ew")

        # Separator
        ttk.Separator(main_frame, orient="horizontal").pack(fill="x", pady=(0, 6))

        # Log area (always visible)
        log_header = tk.Frame(main_frame)
        log_header.pack(fill="x", pady=(0, 4))
        tk.Label(log_header, text=t("br.log_section"), font=("맑은 고딕", self.ui["font_size"], "bold")).pack(side="left")
        self.auto_scroll_var = tk.BooleanVar(value=True)
        tk.Checkbutton(
            log_header, text=t("auto_scroll"), variable=self.auto_scroll_var,
            font=("맑은 고딕", self.ui["font_size"] - 2)
        ).pack(side="right")

        log_container = tk.Frame(main_frame)
        log_container.pack(fill="both", expand=True, pady=(0, 6))

        scrollbar = tk.Scrollbar(log_container)
        scrollbar.pack(side="right", fill="y")

        self.log_text = tk.Text(
            log_container, height=7, wrap="word", state="disabled",
            font=("Consolas", self.ui["font_size"] - 2),
            yscrollcommand=scrollbar.set,
        )
        self.log_text.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.log_text.yview)

        # 인터페이스 수 백그라운드 조회
        self.master.after(200, self._refresh_interface_count)

    def _finalize_window_and_show(self):
        self.master.update_idletasks()
        req_w = self.master.winfo_reqwidth()
        req_h = self.master.winfo_reqheight()
        final_w = max(580, req_w)
        final_h = max(self.original_window_height, req_h)
        sw = self.master.winfo_screenwidth()
        sh = self.master.winfo_screenheight()
        x = int((sw - final_w) / 2)
        y = int((sh - final_h) / 2)
        self.master.geometry(f"{final_w}x{final_h}+{x}+{y}")
        self.master.minsize(req_w, req_h)
        self.master.deiconify()

    def _refresh_interface_count(self):
        def _worker():
            try:
                import automation as _auto
                adapters = _auto.get_active_adapters()
                count = len(adapters)
            except Exception:
                count = 0
            if self.master.winfo_exists():
                self.master.after(0, lambda: self.interface_label.config(
                    text=t("br.interface_count", n=count)
                ))
        threading.Thread(target=_worker, daemon=True).start()

    @property
    def admin_password(self) -> str:
        if self._admin_password is None:
            try:
                from wf_settings_common import get_admin_password
                self._admin_password = get_admin_password(self.logger)
            except Exception:
                self._admin_password = "admin2024"
        return self._admin_password

    def _lazy_init_managers(self):
        def _worker():
            if self.wf_manager and CreditManager:
                self.credit_manager = init_credit_and_policy_managers(
                    app_name="ban_redirection",
                    wf_manager=self.wf_manager,
                    master=self.master,
                    logger=self.logger,
                )
                self.master.after(0, self.update_credit_display)
        threading.Thread(target=_worker, daemon=True).start()

    def update_credit_display(self):
        if not self.credit_manager:
            self.credit_label.config(text=t("credits_checking"), fg="gray")
            return
        status = self.credit_manager.get_credit_status()
        trial_raw = status.get("remaining_trial", -1)
        purchased_raw = status.get("remaining_purchased", 0)
        if trial_raw == -1 or purchased_raw == -1:
            self.credit_label.config(text=t("free_app"), fg="green")
        else:
            total = max(0, trial_raw) + max(0, purchased_raw)
            self.credit_label.config(text=t("credits_display", n=total), fg="blue")

    # ==================== 실행 ====================
    def start_fix(self):
        if self._running:
            return

        primary = self.primary_dns_var.get().strip()
        secondary = self.secondary_dns_var.get().strip()

        if not primary or not secondary:
            self._show_messagebox("showerror", t("br.input_error_title"), t("br.input_error_msg"))
            return

        self.config.save_dns_settings(primary, secondary)

        self._running = True
        self.run_button.config(state="disabled")
        self._clear_log()
        self._append_log(f"DNS 설정 시작: Primary={primary}, Secondary={secondary}")

        def _worker():
            import automation as _auto
            result = _auto.run_fix(primary, secondary, self._on_progress)
            self.master.after(0, lambda: self._on_complete(result))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_progress(self, message: str, is_error: bool = False):
        if self.master.winfo_exists():
            self.master.after(0, lambda: self._append_log(message, is_error))

    def _on_complete(self, result: dict):
        self._running = False
        self.run_button.config(state="normal")
        if result.get("success"):
            self._show_messagebox("showinfo", t("complete_title"), t("br.complete_msg"))
        else:
            errors = result.get("errors", [])
            msg = t("br.fail_msg")
            if errors:
                msg += f"\n실패: {', '.join(errors)}"
            self._show_messagebox("showerror", t("error_title"), msg)

    def _clear_log(self):
        try:
            self.log_text.config(state="normal")
            self.log_text.delete("1.0", "end")
            self.log_text.config(state="disabled")
        except Exception:
            pass

    def _append_log(self, message: str, is_error: bool = False):
        try:
            self.log_text.config(state="normal")
            tag = "error" if is_error else "normal"
            self.log_text.insert("end", message + "\n", tag)
            self.log_text.tag_config("error", foreground="red")
            self.log_text.config(state="disabled")
            if self.auto_scroll_var.get():
                self.log_text.see("end")
        except Exception:
            pass

    # ==================== 키보드 단축키 ====================
    def _bind_keyboard_shortcuts(self):
        try:
            self.master.bind_all("<Alt-g>", self._on_debug_geometry_capture)
            run_mode = getattr(self.config, "run_mode", "release")
            if run_mode == "demo":
                self.master.bind_all("<Alt-c>", self._on_manual_capture)
        except Exception as e:
            self.logger.debug(f"Alt hotkey bind 실패: {e}")

    def _on_debug_geometry_capture(self, _event=None):
        try:
            geo = self.master.geometry()
            ok = self.config.update_window_geometry_override(geo)
            self._show_toast(f"geometry {'저장됨' if ok else '저장 실패'}: {geo}", 1400)
        except Exception:
            pass

    def _on_manual_capture(self, _event=None):
        run_mode = getattr(self.config, "run_mode", "release")
        if run_mode != "demo":
            return
        try:
            from PIL import ImageGrab
            import datetime as dt
            capture_dir = Path.home() / ".wf_rpa" / "ban_redirection" / "demo_captures"
            capture_dir.mkdir(parents=True, exist_ok=True)
            ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
            path = capture_dir / f"demo_{ts}_manual_capture.png"
            ImageGrab.grab().save(path, "PNG")
            self._show_toast("화면 캡처 완료", 1200)
        except Exception as e:
            self._show_toast(f"캡처 실패: {e}", 1500)

    def _show_toast(self, message: str, duration_ms: int = 1500):
        try:
            toast = tk.Toplevel(self.master)
            toast.overrideredirect(True)
            toast.attributes("-topmost", True)
            tk.Label(
                toast, text=message, bg="#333333", fg="white",
                font=("맑은 고딕", 10), padx=15, pady=8
            ).pack()
            self.master.update_idletasks()
            x = self.master.winfo_x() + (self.master.winfo_width() - toast.winfo_reqwidth()) // 2
            y = self.master.winfo_y() + self.master.winfo_height() - 60
            toast.geometry(f"+{x}+{y}")
            toast.after(duration_ms, lambda: toast.destroy() if toast.winfo_exists() else None)
        except Exception:
            pass

    def _show_messagebox(self, msg_type: str, title: str, message: str, **kwargs):
        try:
            is_topmost = self.config.topmost
            if is_topmost:
                self.master.wm_attributes("-topmost", 0)
                self.master.update_idletasks()
            result = getattr(messagebox, msg_type, messagebox.showinfo)(
                title, message, parent=self.master, **kwargs
            )
            if is_topmost:
                self.master.wm_attributes("-topmost", 1)
            return result
        except Exception:
            return getattr(messagebox, msg_type, messagebox.showinfo)(title, message, **kwargs)

    # ==================== 관리자 모드 (WF 패턴) ====================
    def on_status_label_click(self, event=None):
        try:
            if self.is_admin_mode:
                self._exit_admin_mode()
            else:
                run_mode = getattr(self.config, "run_mode", "release")
                if run_mode == "dev":
                    self._enter_admin_mode()
                else:
                    pw = simpledialog.askstring(
                        t("admin_auth_dialog"), t("admin_auth_prompt"), show="*", parent=self.master
                    )
                    if pw is None:
                        return
                    if pw == self.admin_password:
                        self._enter_admin_mode()
                    else:
                        self._show_messagebox("showwarning", t("admin_auth_fail_title"), t("admin_auth_fail_msg"))
        except Exception as e:
            self.logger.error(f"관리자 모드 토글 오류: {e}")

    def _enter_admin_mode(self):
        self.is_admin_mode = True
        self.admin_mode_timer = self.master.after(1800000, self._auto_exit_admin_mode)
        self.master.title(f"{t('br.title', ver=APP_VERSION_FULL)} {t('admin_mode_title')}")
        self.admin_status_label.config(bg="#ffe6e6")
        self._append_log(t("admin_mode_log_enter"))

    def _exit_admin_mode(self):
        self.is_admin_mode = False
        if self.admin_mode_timer:
            self.master.after_cancel(self.admin_mode_timer)
            self.admin_mode_timer = None
        self.master.title(t("br.title", ver=APP_VERSION_DISPLAY))
        self.admin_status_label.config(bg=self.master.cget("bg"))

    def _auto_exit_admin_mode(self):
        self._exit_admin_mode()
        self._show_messagebox("showinfo", t("admin_auto_exit_title"), t("admin_auto_exit_msg"))

    # ==================== WF-ACT Test Mode ====================
    def init_test_server(self):
        try:
            from test_server import TestServer
            self.test_server = TestServer(app_name="ban_redirection")
            self.test_server.register_handlers({
                "get_credits": self._test_get_credits,
                "set_credits": self._test_set_credits,
                "add_credits": self._test_add_credits,
                "get_credit_status": self._test_get_credit_status,
                "get_trial_info": self._test_get_trial_info,
                "get_registration_status": self._test_get_registration_status,
                "register": self._test_register,
                "clear_registration": self._test_clear_registration,
                "sync_registration": self._test_sync_registration,
                "simulate_work": self._test_simulate_work,
                "get_state": self._test_get_state,
                "get_ui_state": self._test_get_state,
                "get_policy": self._test_get_policy,
                "get_settings": self._test_get_settings,
                "save_settings": self._test_save_settings,
                "load_settings": self._test_load_settings,
                "reload_config": self._test_reload_config,
                "get_button_state": self._test_get_button_state,
                "click_button": self._test_click_button,
            })
            self.test_server.start()
            self.logger.info("[WF-ACT] Test server started on port " + str(self.test_server.port))
        except Exception as e:
            self.logger.error(f"[WF-ACT] Failed to initialize test server: {e}")
            raise

    def _ensure_credit_manager(self):
        for _ in range(50):
            if self.credit_manager:
                return
            time.sleep(0.1)

    def _test_get_credits(self) -> int:
        self._ensure_credit_manager()
        if not self.credit_manager:
            return -1
        try:
            data = self.credit_manager._load_credit_data()
            rt, rp = data.get("remaining_trial", -1), data.get("remaining_purchased", 0)
            return -1 if rt == -1 or rp == -1 else rt + rp
        except Exception:
            return -1

    def _test_set_credits(self, amount: int, credit_type: str = "trial") -> bool:
        self._ensure_credit_manager()
        if not self.credit_manager or amount is None or amount < 0:
            return False
        try:
            data = self.credit_manager._load_credit_data()
            if credit_type == "purchased":
                data["remaining_purchased"], data["remaining_trial"] = amount, 0
            else:
                data["remaining_trial"], data["remaining_purchased"] = amount, 0
            self.credit_manager._save_credit_data(data)
            self.master.after(0, self.update_credit_display)
            return True
        except Exception:
            return False

    def _test_add_credits(self, amount: int) -> bool:
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
        self._ensure_credit_manager()
        return self.credit_manager.get_credit_status() if self.credit_manager else {"error": "not_initialized"}

    def _test_get_trial_info(self) -> dict:
        self._ensure_credit_manager()
        if not self.credit_manager:
            return {"error": "not_initialized"}
        policy = self.credit_manager.policy or {}
        data = self.credit_manager._load_credit_data()
        return {
            "initial_credits": policy.get("trial_credits", -1),
            "remaining_trial": data.get("remaining_trial", -1),
            "trial_credits": policy.get("trial_credits", -1),
        }

    def _test_get_registration_status(self) -> dict:
        if not self.wf_manager:
            return {"is_registered": False, "email": None}
        ui = self.wf_manager.get_user_info()
        return {
            "is_registered": self.wf_manager.is_registered(),
            "email": ui.get("user_email") or ui.get("email"),
            "registered_at": ui.get("reg_time_local"),
            "app_version": APP_VERSION_FULL,
        }

    def _test_register(self, email: str) -> dict:
        if not self.wf_manager:
            return {"success": False, "error": "not_initialized"}
        try:
            try:
                from wf_hwinfo import HardwareInfo
                hw_fp = HardwareInfo().fingerprint
            except Exception:
                hw_fp = "test_" + email.split("@")[0]
            success = self.wf_manager.register_user(
                user_email=email, hw_fingerprint=hw_fp,
                user_name="Test", user_phone="", user_email_consent="Y"
            )
            if success:
                self.is_registered_user = True
            return {"success": success}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _test_clear_registration(self) -> bool:
        if not self.wf_manager:
            return False
        try:
            config = self.wf_manager.load_config()
            config["user_info"] = {
                "is_registered": False, "user_email": None,
                "reg_time_local": None, "reg_time_utc": None,
            }
            self.wf_manager.save_config(config)
            self.is_registered_user = False
            return True
        except Exception:
            return False

    def _test_sync_registration(self) -> dict:
        return (
            {"success": True, "message": "sync_attempted"}
            if self.wf_manager
            else {"success": False, "error": "not_initialized"}
        )

    def _test_simulate_work(self, file_count: int = 1) -> dict:
        """무료 앱이므로 항상 success 반환."""
        return {
            "success": True,
            "processed_count": file_count,
            "blocked": False,
            "interrupted": False,
            "remaining_credits": -1,
        }

    def _test_get_state(self) -> dict:
        credits_display = None
        try:
            if hasattr(self, "credit_label") and self.credit_label:
                credits_display = self.credit_label.cget("text")
        except Exception:
            pass
        return {
            "is_registered": self.is_registered_user,
            "has_credit_manager": self.credit_manager is not None,
            "is_admin_mode": self.is_admin_mode,
            "credits_display": credits_display,
        }

    def _test_get_policy(self) -> dict:
        p = dict(self.credit_manager.policy) if self.credit_manager else {}
        return {
            "identity": {"app_name": "ban_redirection", "display_name": "리다이렉션 차단"},
            "policy": {"credit_per_work": 0, "trial_credits": -1},
            "app_name": "ban_redirection",
            **p,
        }

    def _test_get_settings(self) -> dict:
        return {
            "app_name": "ban_redirection",
            "run_mode": getattr(self.config, "run_mode", "release"),
            "full_version": APP_VERSION_FULL,
            "version": APP_VERSION_FULL,
        }

    def _test_reload_config(self) -> bool:
        try:
            if self.credit_manager:
                self.credit_manager._reload_policy()
            return True
        except Exception:
            return False

    def _test_save_settings(self, settings: dict) -> dict:
        try:
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
            sf = get_config_path()
            data = json.load(open(sf, "r", encoding="utf-8")) if sf.exists() else {}
            return {"app_config": data.get("app_config", {}), "test_config": data.get("test_config", {})}
        except Exception as e:
            return {"error": str(e)}

    def _test_get_button_state(self, button_name: str) -> dict:
        bmap = {
            "work": getattr(self, "run_button", None),
            "register": None,
            "settings": None,
        }
        btn = bmap.get(button_name)
        if btn:
            return {"exists": True, "state": str(btn.cget("state")), "text": str(btn.cget("text"))}
        return {"exists": False}

    def _test_click_button(self, button_name: str) -> bool:
        bmap = {"work": getattr(self, "run_button", None)}
        btn = bmap.get(button_name)
        if btn and str(btn.cget("state")) != "disabled":
            btn.invoke()
            return True
        return False

    def on_closing(self):
        try:
            if hasattr(self, "test_server") and self.test_server:
                self.test_server.stop()
        except Exception:
            pass
        self.master.quit()
        self.master.destroy()


def main():
    test_mode = "--test-mode" in sys.argv

    # 관리자 권한 확인 및 재시작
    if not test_mode:
        try:
            import ctypes
            if not ctypes.windll.shell32.IsUserAnAdmin():
                script_path = str(Path(__file__).resolve())
                if getattr(sys, "frozen", False):
                    executable = sys.argv[0]
                    params = ""
                else:
                    executable = sys.executable
                    # 추가 인자가 있으면 포함 (예: --test-mode)
                    extra = " ".join(f'"{a}"' for a in sys.argv[1:])
                    params = f'"{script_path}"' + (f" {extra}" if extra else "")
                ret = ctypes.windll.shell32.ShellExecuteW(
                    None, "runas", executable, params, None, 1
                )
                if ret > 32:
                    sys.exit(0)
        except Exception:
            pass

    if not test_mode:
        is_first, _handle = _acquire_single_instance()
        if not is_first:
            print("Another ban_redirection instance is already running. Exiting.")
            return

    try:
        _set_cross_app_running("ban_redirection")
        import atexit
        atexit.register(_clear_cross_app_running)
    except Exception:
        pass

    root = tk.Tk()
    try:
        root.withdraw()
    except Exception:
        pass

    try:
        if getattr(sys, "frozen", False):
            base_paths = [
                Path(sys.executable).parent / "res",
                Path(sys.executable).parent / "_internal" / "res",
            ]
        else:
            base_paths = [Path(__file__).parent / "res"]
        icon_path = next((bp / "BR.ico" for bp in base_paths if (bp / "BR.ico").exists()), None)
        if icon_path:
            root.iconbitmap(str(icon_path))
    except Exception:
        pass

    app = BanRedirectionGUI(root)

    if test_mode:
        try:
            app.init_test_server()
        except Exception as e:
            print(f"[WF-ACT] Failed to initialize test server: {e}")

    root.mainloop()


if __name__ == "__main__":
    main()
