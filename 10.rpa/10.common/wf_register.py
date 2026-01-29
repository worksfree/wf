import logging

# 모듈 레벨 로거 (부모에서 주입 가능). 기본은 NullHandler로 안전하게 무시
logger: logging.Logger = logging.getLogger("wf_register")
if not logger.handlers:
    logger.addHandler(logging.NullHandler())


def set_logger(external_logger: logging.Logger):
    global logger
    logger = external_logger


# =============================================================================
# Adaptive UI 함수 - wf_ui_adaptive 모듈에서 통합 관리
# =============================================================================
try:
    from wf_ui_adaptive import get_adaptive_ui_settings, apply_global_fonts as _apply_global_fonts
except ImportError:
    # Fallback: 기본값 반환
    def get_adaptive_ui_settings(window_type: str = "main", saved_ui: dict = None):
        return {"window_width": 520, "window_height": 200, "font_size": 9, "padding": 10}
    def _apply_global_fonts(root, ui): pass


def center_window_on_screen(window, width, height):
    """창을 부모 창 중앙에 배치, 부모가 없으면 화면 중앙에 배치"""
    x = y = None

    # 1. 부모 창이 있으면 부모 중앙에 배치
    try:
        parent = window.master
        if parent and parent.winfo_exists():
            parent.update_idletasks()
            px, py = parent.winfo_rootx(), parent.winfo_rooty()
            pw, ph = parent.winfo_width(), parent.winfo_height()
            if pw > 0 and ph > 0:
                x = px + (pw - width) // 2
                y = py + (ph - height) // 2
    except Exception:
        x = y = None

    # 2. 부모가 없거나 좌표 계산 실패 시 화면 중앙에 배치
    if x is None or y is None:
        try:
            import pyautogui
            screen_width, screen_height = pyautogui.size()
            x = (screen_width - width) // 2
            y = (screen_height - height) // 2
        except Exception:
            x, y = 300, 200  # 기본 위치

    window.geometry(f"{width}x{height}+{x}+{y}")


def _bind_tooltip(widget, text: str, topmost: bool = False):
    """Bind a simple tooltip to a Tk widget.
    - Yellow background, compact paddings
    - Optionally set as topmost for modal dialogs
    """
    tip = {"win": None}

    def show_tip(_event=None):
        try:
            if tip["win"] and tip["win"].winfo_exists():
                return
            tw = tk.Toplevel(widget)
            tip["win"] = tw
            tw.wm_overrideredirect(True)
            if topmost:
                try:
                    tw.attributes("-topmost", True)
                except Exception:
                    pass
            # Position near cursor
            try:
                x = widget.winfo_pointerx() + 12
                y = widget.winfo_pointery() + 12
            except Exception:
                x = widget.winfo_rootx() + 12
                y = widget.winfo_rooty() + 12
            tw.wm_geometry(f"+{x}+{y}")
            label = tk.Label(
                tw,
                text=text,
                background="#ffffcc",
                relief="solid",
                borderwidth=1,
                justify="left",
                padx=6,
                pady=4,
            )
            label.pack()
        except Exception:
            pass

    def hide_tip(_event=None):
        try:
            if tip["win"] and tip["win"].winfo_exists():
                tip["win"].destroy()
            tip["win"] = None
        except Exception:
            pass

    try:
        widget.bind("<Enter>", show_tip)
        widget.bind("<Leave>", hide_tip)
        widget.bind("<ButtonPress>", hide_tip)
    except Exception:
        pass

# -*- coding: utf-8 -*-
"""
공통 사용자 등록/라이선스 관리 모듈 (UI)
기준: bom2excel/ui_register.py
"""
import sys
import os
from pathlib import Path
import tkinter as tk
import tkinter.ttk as ttk
import tkinter.messagebox
import datetime

# pyautogui는 필요한 함수 내부에서 lazy import (화면 크기 측정용)

# 공통 모듈 경로 추가
current_dir = Path(__file__).resolve().parent
utils_path = current_dir
if str(utils_path) not in sys.path:
    sys.path.append(str(utils_path))

# WorksFree 전역 매니저 import (올바른 모듈명 사용)
try:
    from wf_credit_manager import WorksFreeManager

    WFM_AVAILABLE = True
except ImportError as e:
    WFM_AVAILABLE = False
    logger.error(f"WorksFreeManager import 실패: {e}")

# 구글 시트 관리자 import
try:
    from wf_googlesheets_manager import get_sheets_manager

    SHEETS_AVAILABLE = True
except ImportError:
    SHEETS_AVAILABLE = False
    logger.error("구글 시트 관리자를 찾을 수 없습니다.")

# 하드웨어 정보 모듈
try:
    import wf_hwinfo

    HWINFO_AVAILABLE = True
except ImportError:
    HWINFO_AVAILABLE = False
    logger.warning("wf_hwinfo 모듈을 찾을 수 없습니다. 테스트 모드로 실행됩니다.")

# 이메일 모듈
try:
    import wf_email as wfm

    EMAIL_AVAILABLE = True
except ImportError:
    EMAIL_AVAILABLE = False
    logger.warning("wf_email 모듈을 찾을 수 없습니다. 테스트 모드로 실행됩니다.")

# 인증코드 생성 모듈
try:
    import wf_gen_code as wfgc

    GENCODE_AVAILABLE = True
except ImportError:
    GENCODE_AVAILABLE = False
    logger.warning("wf_gen_code 모듈을 찾을 수 없습니다. 테스트 모드로 실행됩니다.")


class TrialRegistrationWindow:
    """체험판 등록 창 관리 클래스 (공통)"""

    def __init__(self, parent_app, hardware_info=None, ui_settings=None):
        self.parent_app = parent_app
        self.hardware_info = hardware_info or self._get_hardware_info()
        self.trial_win = None
        # 메인 앱에서 전달된 ui_settings를 사용 (일관된 UI 스키마 유지)
        # 전달되지 않은 경우에만 기본 설정 사용
        self.ui_settings = ui_settings if ui_settings is not None else get_adaptive_ui_settings()
        if WFM_AVAILABLE:
            self.wf_manager = WorksFreeManager()
        else:
            self.wf_manager = None
        # 인증 타이머 상태
        self._timer_active = False
        self._countdown_end = None
        self._base_status_msg = ""

    def _get_hardware_info(self):
        info = {
            "CPU ID": "수집 실패",
            "메인보드 ID": "수집 실패",
            "스토리지 ID": "수집 실패",
            "하드웨어 지문": "수집 실패",
        }
        if not HWINFO_AVAILABLE:
            logger.error("wf_hwinfo 모듈을 사용할 수 없어 하드웨어 정보 수집이 불가능합니다.")
            return info
        try:
            hw_info = wf_hwinfo.HardwareInfo()
            # 각 속성을 개별적으로 시도하여 하나가 실패해도 다른 속성은 유지되도록 함
            try:
                info["CPU ID"] = hw_info.cpu_id or "정보 없음"
            except Exception as e:
                logger.error(f"CPU ID 수집 실패: {e}")
            try:
                info["메인보드 ID"] = hw_info.mainboard_id or "정보 없음"
            except Exception as e:
                logger.error(f"메인보드 ID 수집 실패: {e}")
            try:
                info["스토리지 ID"] = getattr(hw_info, "storage_id", "정보 없음")
            except Exception as e:
                logger.error(f"스토리지 ID 수집 실패: {e}")
            try:
                info["하드웨어 지문"] = hw_info.fingerprint or "생성 실패"
            except Exception as e:
                logger.error(f"하드웨어 지문 생성 실패: {e}")
        except Exception as e:
            logger.error(f"전체 하드웨어 정보 수집 중 치명적 오류 발생: {e}")
        return info

    def open_trial_window(self):
        if self.trial_win and self.trial_win.winfo_exists():
            self.trial_win.lift()
            return

        ui_settings = dict(self.ui_settings)
        try:
            import pyautogui
            screen_width, screen_height = pyautogui.size()
        except Exception:
            screen_width, screen_height = 1920, 1080
        
        if screen_width >= 3840:
            ui_settings["window_width"] = 650
            ui_settings["window_height"] = 600
        elif screen_width >= 2560:
            ui_settings["window_width"] = 600
            ui_settings["window_height"] = 550
        else:
            ui_settings["window_width"] = 550
            ui_settings["window_height"] = 500
        
        ui_settings.setdefault("tree_height", 4)
        ui_settings.setdefault("entry_width", 30)
        ui_settings.setdefault("button_width", 10)
        ui_settings.setdefault("tree_rowheight", ui_settings.get("tree_rowheight", 25))
        ui_settings.setdefault("padding", ui_settings.get("padding", 10))

        parent_master = getattr(self.parent_app, "master", None)
        self.trial_win = tk.Toplevel(parent_master)
        self.trial_win.withdraw()  # 깜빡임 방지: geometry 설정 전까지 숨김
        self.trial_win.title("체험판 등록")

        # 앱별 아이콘 적용 (parent_app에서 icon_path 가져오기)
        try:
            icon_path = getattr(self.parent_app, "icon_path", None)
            if icon_path:
                self.trial_win.iconbitmap(str(icon_path))
        except Exception:
            pass

        # 폰트 전역 적용 제거
        # _apply_global_fonts(self.trial_win, ui_settings)

        center_window_on_screen(
            self.trial_win, ui_settings["window_width"], ui_settings["window_height"]
        )

        # Topmost 및 Modal 설정
        self.trial_win.attributes("-topmost", True)
        if parent_master:
            self.trial_win.transient(parent_master)
        self.trial_win.grab_set()
        self.trial_win.focus_set()
        self.trial_win.deiconify()  # 모든 설정 완료 후 표시

        main_frame = tk.Frame(
            self.trial_win, padx=ui_settings["padding"], pady=ui_settings["padding"]
        )
        main_frame.pack(fill="both", expand=True)

        tk.Label(
            main_frame,
            text="하드웨어 정보:",
            font=("맑은 고딕", ui_settings.get("font_size_bold", 10), "bold"),
        ).grid(row=0, column=0, sticky="w", padx=5, pady=5)
        
        style = ttk.Style()
        style.configure("RegTreeview.Treeview", rowheight=ui_settings["tree_rowheight"])

        tree = ttk.Treeview(
            main_frame,
            columns=("value",),
            show="tree headings",
            height=ui_settings["tree_height"],
            style="RegTreeview.Treeview",
        )
        tree.grid(row=1, column=0, columnspan=3, padx=10, pady=5, sticky="ew")
        tree.heading("#0", text="항목")
        tree.heading("value", text="값")
        tree.column("#0", width=150)
        tree.column("value", width=250)
        if isinstance(self.hardware_info, dict):
            for key, value in self.hardware_info.items():
                if value and key != "하드웨어 지문":
                    display_value = value[:32] + "..." if len(str(value)) > 32 else value
                    tree.insert("", "end", text=key, values=(display_value,))
                elif key == "하드웨어 지문":
                    display_value = (
                        value[:8] + "..." + value[-8:] if len(str(value)) > 16 else value
                    )
                    tree.insert("", "end", text="하드웨어 ID", values=(display_value,))
        else:
            tree.insert("", "end", text="하드웨어 정보", values=(str(self.hardware_info),))

        # 입력 필드들 (적응형 폰트와 크기)
        tk.Label(
            main_frame, text="이름 (선택):", font=("맑은 고딕", ui_settings["font_size"])
        ).grid(row=2, column=0, sticky="w", padx=5, pady=5)
        self.name_var = tk.StringVar()
        name_entry = tk.Entry(
            main_frame,
            textvariable=self.name_var,
            width=ui_settings["entry_width"],
            font=("맑은 고딕", ui_settings["font_size"]),
        )
        name_entry.grid(row=2, column=1, columnspan=2, sticky="w", padx=5, pady=5)

        tk.Label(
            main_frame, text="연락처 (선택):", font=("맑은 고딕", ui_settings["font_size"])
        ).grid(row=3, column=0, sticky="w", padx=5, pady=5)
        self.phone_var = tk.StringVar()
        phone_entry = tk.Entry(
            main_frame,
            textvariable=self.phone_var,
            width=ui_settings["entry_width"],
            font=("맑은 고딕", ui_settings["font_size"]),
        )
        phone_entry.grid(row=3, column=1, columnspan=2, sticky="w", padx=5, pady=5)

        tk.Label(main_frame, text="이메일:", font=("맑은 고딕", ui_settings["font_size"])).grid(
            row=4, column=0, sticky="w", padx=5, pady=5
        )
        self.email_var = tk.StringVar()
        email_entry = tk.Entry(
            main_frame,
            textvariable=self.email_var,
            width=ui_settings["entry_width"],
            font=("맑은 고딕", ui_settings["font_size"]),
        )
        email_entry.grid(row=4, column=1, columnspan=2, sticky="w", padx=5, pady=5)
        
        # Placeholder 설정
        placeholder_email = "youremail@email.co.kr"
        self.email_var.set(placeholder_email)
        email_entry.config(fg="gray")
        
        def on_email_focus_in(event):
            if self.email_var.get() == placeholder_email:
                self.email_var.set("")
                email_entry.config(fg="black")
        
        def on_email_focus_out(event):
            if not self.email_var.get().strip():
                self.email_var.set(placeholder_email)
                email_entry.config(fg="gray")
        
        email_entry.bind("<FocusIn>", on_email_focus_in)
        email_entry.bind("<FocusOut>", on_email_focus_out)

        tk.Label(main_frame, text="인증코드:", font=("맑은 고딕", ui_settings["font_size"])).grid(
            row=5, column=0, sticky="w", padx=5, pady=5
        )
        self.code_var = tk.StringVar()
        self.code_entry = tk.Entry(
            main_frame,
            textvariable=self.code_var,
            width=12,
            state="disabled",
            font=("맑은 고딕", ui_settings["font_size"]),
        )
        self.code_entry.grid(row=5, column=1, sticky="w", padx=5, pady=5)
        self.send_btn = tk.Button(
            main_frame,
            text="인증코드 받기",
            command=self.send_verification_code,
            font=("맑은 고딕", ui_settings["font_size"]),
            padx=10,  # 텍스트 기반 동적 너비 + 여백
        )
        self.send_btn.grid(row=5, column=2, padx=3, pady=5)

        self.status_var = tk.StringVar()
        status_label = tk.Label(
            main_frame, textvariable=self.status_var, font=("맑은 고딕", ui_settings["font_size"])
        )
        status_label.grid(row=6, column=0, columnspan=3, pady=10)

        self.verify_btn = tk.Button(
            main_frame,
            text="등록하기",
            command=self.verify_code_and_register,
            state="disabled",
            font=("맑은 고딕", ui_settings["font_size"]),
            padx=15,  # 텍스트 기반 동적 너비 + 여백
        )
        self.verify_btn.grid(row=8, column=0, pady=20)
        cancel_btn = tk.Button(
            main_frame,
            text="취소하기",
            command=self.close_trial_window,
            font=("맑은 고딕", ui_settings["font_size"]),
            padx=15,  # 텍스트 기반 동적 너비 + 여백
        )
        cancel_btn.grid(row=8, column=2, pady=20)

        # Tooltips for inputs and actions (modal-safe, topmost)
        _bind_tooltip(tree, "하드웨어 식별정보(일부 마스킹) 확인", topmost=True)
        _bind_tooltip(name_entry, "선택 입력: 성명(등록 기록에 포함)", topmost=True)
        _bind_tooltip(phone_entry, "선택 입력: 연락처(등록 기록에 포함)", topmost=True)
        _bind_tooltip(email_entry, "필수: 인증코드를 받기 위한 이메일", topmost=True)
        _bind_tooltip(self.code_entry, "인증코드 입력(이메일 발송 후 활성화)", topmost=True)
        _bind_tooltip(self.send_btn, "입력한 이메일로 인증코드를 발송", topmost=True)
        _bind_tooltip(self.verify_btn, "인증코드를 확인하고 등록 완료", topmost=True)
        _bind_tooltip(cancel_btn, "창을 닫고 등록을 취소", topmost=True)
        _bind_tooltip(status_label, "인증 진행 상태와 남은 시간 표시", topmost=True)

        # 그리드 가중치 설정
        main_frame.columnconfigure(1, weight=1)

        # Alt+G: geometry 저장 (디버깅용)
        self.trial_win.bind_all("<Alt-g>", self._on_debug_geometry_capture)

        self.trial_win.protocol("WM_DELETE_WINDOW", self.close_trial_window)

    def send_verification_code(self):
        email_input = self.email_var.get().strip()
        # Placeholder 체크
        if not email_input or "@" not in email_input or email_input == "youremail@email.co.kr":
            self.status_var.set("유효한 이메일 주소를 입력하세요.")
            return

        try:
            if GENCODE_AVAILABLE and EMAIL_AVAILABLE:
                verification_code = wfgc.generate_code_with_limited_duplicates()

                wfm.init(self.parent_app.itself_dir)
                # 명시적으로 수신자 인자를 지정하여 전역 기본값으로의 폴백을 방지
                wfm.mail_send_attach(
                    title=f"[WorksFree] 체험판 인증코드",
                    email_to=email_input,
                    body_array=f"체험판 인증코드: {verification_code}",
                    attachments=None,
                )

                self.code_entry.config(state="normal")
                self.send_btn.config(state="disabled")
                self.verify_btn.config(state="normal")
                self.verification_code = verification_code
                self._base_status_msg = "이메일로 인증코드를 보냈습니다."
                self._start_countdown(300)
            else:
                # Fallback for testing
                self.verification_code = "TEST123"
                self.code_entry.config(state="normal")
                self.verify_btn.config(state="normal")
                self._base_status_msg = f"[테스트] 인증코드: {self.verification_code}"
                self._start_countdown(300)
        except Exception as e:
            self.status_var.set(f"오류: {e}")

    def verify_code_and_register(self):
        entered_code = self.code_var.get().strip()
        if hasattr(self, "verification_code") and entered_code == self.verification_code:
            email = self.email_var.get().strip()
            name = self.name_var.get().strip()
            phone = self.phone_var.get().strip()
            hw_fingerprint = self.hardware_info.get("하드웨어 지문", "")

            if not self.wf_manager:
                self.status_var.set("오류: 설정 관리자를 찾을 수 없습니다.")
                return

            # 1. Check for existing registration in Google Sheets
            if SHEETS_AVAILABLE:
                sheets_manager = get_sheets_manager()
                if sheets_manager.is_fingerprint_registered(hw_fingerprint):
                    self.status_var.set("이미 등록된 하드웨어입니다.")
                    return

            # 2. Register user using WorksFreeManager (로컬 저장)
            try:
                success = self.wf_manager.register_user(
                    user_email=email,
                    hw_fingerprint=hw_fingerprint,
                    user_name=name,
                    user_phone=phone,
                    user_email_consent="Y",
                )
                if success:
                    # 인증 성공: 타이머 종료
                    self._stop_countdown()
                    self.status_var.set("등록이 완료되었습니다!")

                    # 3. Log registration to Google Sheets (record actual app name)
                    if SHEETS_AVAILABLE:
                        def _format_app_name_from_folder(name: str) -> str:
                            try:
                                n = (name or "").strip().replace("-", "_")
                                parts = [p for p in n.split("_") if p]
                                return "_".join(p[:1].upper() + p[1:] for p in parts)
                            except Exception:
                                return name or "unknown_app"

                        def _detect_current_app_name() -> str:
                            # 1) parent_app에서 직접 참조 (가장 신뢰할 수 있는 소스)
                            try:
                                cm = getattr(self.parent_app, "credit_manager", None)
                                if cm and getattr(cm, "app_name", None):
                                    return _format_app_name_from_folder(cm.app_name)
                            except Exception:
                                pass
                            # 2) _internal/.wf_rpa/*/policy.json (번들 원본, 변조 불가)
                            try:
                                if getattr(sys, "frozen", False):
                                    start = Path(sys.executable).resolve().parent
                                else:
                                    start = Path(sys.argv[0]).resolve().parent
                                import json as _json
                                internal_wf = start / "_internal" / ".wf_rpa"
                                if internal_wf.is_dir():
                                    for sub in internal_wf.iterdir():
                                        if sub.is_dir() and (sub / "policy.json").exists():
                                            policy_data = _json.loads((sub / "policy.json").read_text(encoding="utf-8")) or {}
                                            ident = policy_data.get("identity", {}) if isinstance(policy_data.get("identity"), dict) else {}
                                            v = ident.get("app_name") or ident.get("name")
                                            if isinstance(v, str) and v.strip():
                                                return _format_app_name_from_folder(v)
                                            # 폴더명 자체가 앱 이름
                                            return _format_app_name_from_folder(sub.name)
                            except Exception:
                                pass
                            # 3) ~/.wf_rpa/wf_rpa_config.json의 execution_status
                            try:
                                import json as _json
                                cfg = Path.home() / ".wf_rpa" / "wf_rpa_config.json"
                                if cfg.exists():
                                    data = _json.loads(cfg.read_text(encoding="utf-8")) or {}
                                    es = data.get("execution_status", {})
                                    app = es.get("current_app")
                                    if isinstance(app, str) and app.strip():
                                        return _format_app_name_from_folder(app)
                            except Exception:
                                pass
                            # 4) 환경변수 (개발용)
                            try:
                                env_app = os.environ.get("WF_CURRENT_APP")
                                if env_app:
                                    return _format_app_name_from_folder(env_app)
                            except Exception:
                                pass
                            return "Unknown_App"

                        def _detect_current_app_version() -> str:
                            """현재 앱의 버전 정보 감지"""
                            # 1) parent_app.config.version (가장 신뢰할 수 있는 소스)
                            try:
                                cfg = getattr(self.parent_app, "config", None)
                                if cfg and getattr(cfg, "version", None) and cfg.version != "unknown":
                                    return cfg.version
                            except Exception:
                                pass
                            # 2) _internal/.wf_rpa/{app}/settings.json (번들 원본)
                            try:
                                import json as _json
                                if getattr(sys, "frozen", False):
                                    start = Path(sys.executable).resolve().parent
                                else:
                                    start = Path(sys.argv[0]).resolve().parent if sys.argv else Path.cwd()
                                internal_wf = start / "_internal" / ".wf_rpa"
                                if internal_wf.is_dir():
                                    for sub in internal_wf.iterdir():
                                        if sub.is_dir() and (sub / "settings.json").exists():
                                            data = _json.loads((sub / "settings.json").read_text(encoding="utf-8")) or {}
                                            runtime_ver = data.get("runtime_config", {}).get("full_version", "")
                                            if runtime_ver:
                                                return runtime_ver
                                            app_ver = data.get("app_config", {}).get("full_version", "")
                                            if app_ver:
                                                return app_ver
                            except Exception:
                                pass
                            # 3) ~/.wf_rpa/{app_name}/settings.json
                            try:
                                import json as _json
                                app_name = _detect_current_app_name()
                                if app_name and app_name != "Unknown_App":
                                    user_settings = Path.home() / ".wf_rpa" / app_name.lower() / "settings.json"
                                    if user_settings.exists():
                                        data = _json.loads(user_settings.read_text(encoding="utf-8")) or {}
                                        runtime_ver = data.get("runtime_config", {}).get("full_version", "")
                                        if runtime_ver:
                                            return runtime_ver
                            except Exception:
                                pass
                            return ""

                        app_name_detected = _detect_current_app_name()
                        app_version_detected = _detect_current_app_version()
                        sheets_manager.register_user(
                            user_email=email,
                            user_name=name,
                            user_phone=phone,
                            user_email_consent="Y",
                            app_name=app_name_detected,
                            app_version=app_version_detected,
                        )

                    if self.trial_win:
                        self.trial_win.after(1500, self.close_trial_window)
                else:
                    self.status_var.set("등록에 실패했습니다.")
            except Exception as e:
                self.status_var.set(f"오류: {e}")
        else:
            self.status_var.set("인증코드가 올바르지 않습니다.")

    # ---------------- 인증 타이머 ----------------
    def _start_countdown(self, seconds: int):
        try:
            self._timer_active = True
            self._countdown_end = datetime.datetime.now() + datetime.timedelta(seconds=seconds)
            self._tick_timer()
        except Exception:
            # 타이머 실패 시에도 기본 메시지만 표시
            self.status_var.set(self._base_status_msg)

    def _stop_countdown(self):
        self._timer_active = False
        self._countdown_end = None

    def _tick_timer(self):
        if not self.trial_win or not self.trial_win.winfo_exists() or not self._timer_active:
            return
        try:
            now = datetime.datetime.now()
            remaining = (
                int((self._countdown_end - now).total_seconds()) if self._countdown_end else 0
            )
            if remaining <= 0:
                self._on_code_expired()
                return
            mm = remaining // 60
            ss = remaining % 60
            self.status_var.set(f"{self._base_status_msg}\n남은 시간 {mm:02d}:{ss:02d}")
        except Exception:
            pass
        finally:
            # 1초 후 갱신
            try:
                self.trial_win.after(1000, self._tick_timer)
            except Exception:
                pass

    def _on_code_expired(self):
        # 타이머 종료 및 만료 처리
        self._stop_countdown()
        # 기존 코드 무효화
        if hasattr(self, "verification_code"):
            try:
                del self.verification_code
            except Exception:
                pass
        # 재전송 가능, 입력/등록 비활성화
        try:
            self.send_btn.config(state="normal")
            self.code_entry.config(state="disabled")
            self.verify_btn.config(state="disabled")
        except Exception:
            pass
        self.status_var.set("인증코드가 만료되었습니다. 재인증을 요청하세요.")

    def close_trial_window(self):
        if self.trial_win:
            # ⚠️ 중요: 모달 설정 해제 (리팩토링 시에도 유지할 것!)
            self.trial_win.grab_release()  # 모달 해제 - 절대 제거하지 말 것
            self.trial_win.destroy()
            self.trial_win = None

    def _on_debug_geometry_capture(self, _event=None):
        """Alt+G: 현재 geometry를 로그에 출력하고 settings.json에 저장"""
        if not self.trial_win or not self.trial_win.winfo_exists():
            return
        try:
            geo = self.trial_win.geometry()
            msg = f"[DEBUG] TrialRegistrationWindow geometry: {geo}"
            print(msg)
            logger.info(msg)
            # settings.json에 저장 시도
            ok = False
            try:
                # parent_app.config가 있으면 사용
                if hasattr(self.parent_app, 'config') and hasattr(self.parent_app.config, 'update_registration_window_geometry'):
                    ok = self.parent_app.config.update_registration_window_geometry(geo)
            except Exception as save_err:
                logger.debug(f"geometry 저장 실패: {save_err}")
            # 토스트 메시지 표시
            if ok:
                self._show_geometry_toast(f"geometry 저장됨: {geo}")
            else:
                self._show_geometry_toast(f"geometry: {geo}")
        except Exception as e:
            logger.debug(f"Alt+G 실패: {e}")

    def _show_geometry_toast(self, message: str, duration_ms: int = 1400):
        """간단한 토스트 메시지 표시"""
        if not self.trial_win or not self.trial_win.winfo_exists():
            return
        try:
            toast = tk.Toplevel(self.trial_win)
            toast.overrideredirect(True)
            toast.attributes("-topmost", True)
            lbl = tk.Label(
                toast, text=message, bg="#333333", fg="white",
                font=("맑은 고딕", 9), padx=10, pady=5
            )
            lbl.pack()
            toast.update_idletasks()
            x = self.trial_win.winfo_x() + (self.trial_win.winfo_width() - toast.winfo_reqwidth()) // 2
            y = self.trial_win.winfo_y() + self.trial_win.winfo_height() - toast.winfo_reqheight() - 10
            toast.geometry(f"+{x}+{y}")
            toast.after(duration_ms, toast.destroy)
        except Exception:
            pass


def create_trial_window(parent_app, hardware_info=None, ui_settings=None):
    trial = TrialRegistrationWindow(parent_app, hardware_info, ui_settings)
    trial.open_trial_window()
    return trial


class MockParentApp:
    def __init__(self):
        self.itself_dir = str(Path(__file__).resolve().parent)
        self.master = None


if __name__ == "__main__":
    root = tk.Tk()
    _apply_global_fonts(root, get_adaptive_ui_settings())
    root.withdraw()
    mock_app = MockParentApp()
    create_trial_window(mock_app)
    root.mainloop()
