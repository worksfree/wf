# -*- coding: utf-8 -*-
"""
ConversionVerifier Settings UI
설정 관련 UI 다이얼로그를 담당하는 모듈
"""

import sys

# Windows DPI awareness 설정 (스케일링 통일)
if sys.platform == 'win32':
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass  # Already set or not supported

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import re
import pyautogui
import json
import logging
from pathlib import Path


# 버전 정보 로드 (settings.json에서 직접 읽기)
def _load_version_from_settings():
    """settings.json에서 버전 정보 읽기 (소스 설정 버전을 폴백으로 사용)"""
    default_full = "v0.7.0.0"

    def _ensure_prefix(v: str) -> str:
        v = (v or "").strip()
        if not v:
            return default_full
        return v if v.startswith("v") else "v" + v

    # 소스 설정 full_version 확보 (빌드 시 기준 버전)
    source_full = default_full
    try:
        src_settings = Path(__file__).parent / "config" / "conversion_verifier" / "settings.json"
        if src_settings.exists():
            with open(src_settings, "r", encoding="utf-8") as f:
                src_data = json.load(f)
            src_app_cfg = src_data.get("app_config", {}) or {}
            source_full = _ensure_prefix(src_app_cfg.get("full_version", default_full))
    except Exception:
        source_full = default_full

    try:
        if getattr(sys, "frozen", False):
            base_path = Path(sys._MEIPASS) if hasattr(sys, '_MEIPASS') else Path(sys.executable).parent
            settings_file = base_path / ".wf_rpa" / "conversion_verifier" / "settings.json"
            if not settings_file.exists():
                settings_file = Path.home() / ".wf_rpa" / "conversion_verifier" / "settings.json"
        else:
            settings_file = Path(__file__).parent / "config" / "conversion_verifier" / "settings.json"

        if settings_file.exists():
            with open(settings_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            app_config = data.get("app_config", {}) or {}
            runtime_full = app_config.get("full_version")
            if runtime_full:
                return _ensure_prefix(runtime_full)
    except Exception:
        pass

    return source_full

APP_VERSION_FULL = _load_version_from_settings()


def _get_ui_scale() -> float:
    try:
        from app_setting_data import get_config

        cfg = get_config()
        return float(getattr(cfg, "ui_scale", getattr(cfg, "get", lambda *_: 1.0)("ui_scale", 1.0)))
    except Exception:
        return 1.0


def _apply_ui_scale(settings: dict) -> dict:
    scale = _get_ui_scale()
    if abs(scale - 1.0) < 1e-6:
        return settings

    def _s(v):
        try:
            return int(round(v * scale))
        except Exception:
            return v

    for k in (
        "window_width",
        "window_height",
        "font_size",
        "font_size_bold",
        "font_size_title",
        "padding",
    ):
        if k in settings and isinstance(settings[k], (int, float)):
            settings[k] = _s(settings[k])
    return settings


def _apply_global_fonts(root, ui: dict) -> None:
    """Force all Tk default fonts to match the unified sizes."""
    try:
        root.tk.call("tk", "scaling", 1.0)
        import tkinter.font as tkfont

        for name in (
            "TkDefaultFont",
            "TkTextFont",
            "TkFixedFont",
            "TkMenuFont",
            "TkIconFont",
            "TkTooltipFont",
        ):
            tkfont.nametofont(name).configure(size=ui.get("font_size", 10), weight="normal")

        for name in ("TkHeadingFont", "TkCaptionFont"):
            tkfont.nametofont(name).configure(size=ui.get("font_size_title", 10), weight="bold")

        try:
            tkfont.nametofont("TkSmallCaptionFont").configure(
                size=ui.get("font_size_bold", 10), weight="bold"
            )
        except Exception:
            pass
    except Exception:
        pass


def get_adaptive_ui_settings():
    """화면 해상도에 따른 적응형 UI 설정 (설정 파일 값을 우선 사용)"""
    screen_width, _ = pyautogui.size()

    # 해상도별 scale factor
    if screen_width >= 3840:  # UHD (4K)
        resolution_scale = 1.5
    elif screen_width >= 2560:  # QHD (1440p)
        resolution_scale = 1.2
    else:  # FHD (1080p)
        resolution_scale = 1.0

    # 저장된 ui_config를 불러와 base 값에 덮어씌움 (사용자 지정값은 스케일 제외)
    saved_ui = {}
    try:
        from app_setting_data import get_config

        cfg = get_config()
        saved_ui = getattr(cfg, "ui_config", {}) or {}
    except Exception:
        saved_ui = {}

    # geometry 문자열(예: 580x230+990+480)에서 폭/높이 추출
    parsed_w = None
    parsed_h = None
    try:
        geo_str = saved_ui.get("window_geometry_override", "") or saved_ui.get("window_geometry", "")
        if geo_str:
            size_part = geo_str.split("+", 1)[0]
            if "x" in size_part:
                w_str, h_str = size_part.split("x", 1)
                parsed_w = int(w_str)
                parsed_h = int(h_str)
    except Exception:
        parsed_w = parsed_w if parsed_w is not None else None
        parsed_h = parsed_h if parsed_h is not None else None

    try:
        default_width = parsed_w if parsed_w is not None else saved_ui.get("window_width", 580)
        default_width = int(default_width)
    except Exception:
        default_width = 580

    try:
        default_height = parsed_h if parsed_h is not None else saved_ui.get("window_height", 230)
        default_height = int(default_height)
    except Exception:
        default_height = 230

    base_settings = {
        "window_width": default_width,
        "window_height": default_height,
        "font_size": 14,
        "font_size_bold": 14,
        "font_size_title": 14,
        "padding": 12,
        "button_width": 10,
    }

    use_saved_width = (parsed_w is not None) or (isinstance(saved_ui, dict) and "window_width" in saved_ui)
    use_saved_height = (parsed_h is not None) or (isinstance(saved_ui, dict) and "window_height" in saved_ui)

    # resolution scale 적용 (사용자 지정 width/height는 스케일 제외)
    scaled = {}
    for key, value in base_settings.items():
        if isinstance(value, (int, float)) and key != "window_width":
            if key == "window_height" and use_saved_height:
                scaled[key] = value
            else:
                scaled[key] = int(round(value * resolution_scale))
        else:
            scaled[key] = value

    result = _apply_ui_scale(scaled)

    # ui_scale 적용 이후에도 사용자 지정 크기는 원본 유지
    if use_saved_width:
        result["window_width"] = base_settings["window_width"]
    if use_saved_height:
        result["window_height"] = base_settings["window_height"]

    return result


def _bind_tooltip(widget, text: str):
    """Bind a simple tooltip to a Tk widget (topmost for dialogs)."""
    if not text:
        return
    tip = {"win": None}

    def show_tip(_event=None):
        try:
            if tip["win"] and tip["win"].winfo_exists():
                return
            tw = tk.Toplevel(widget)
            tip["win"] = tw
            tw.wm_overrideredirect(True)
            try:
                tw.attributes("-topmost", True)
            except Exception:
                pass
            # Position near widget
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


def create_admin_dialog(parent, admin_password):
    """관리자 모드 진입 다이얼로그"""
    password = simpledialog.askstring(
        "관리자 모드", "관리자 비밀번호를 입력하세요:", show="*", parent=parent
    )

    if password == admin_password:
        messagebox.showinfo("성공", "관리자 모드에 진입했습니다!")
        return True
    elif password is not None:  # 사용자가 취소하지 않은 경우
        messagebox.showerror("오류", "잘못된 비밀번호입니다.")

    return False


def create_license_registration_dialog(parent, config, license_password):
    """라이선스 등록 다이얼로그"""

    class LicenseDialog:
        def __init__(self, parent, config, license_password):
            self.parent = parent
            self.config = config
            self.license_password = license_password
            self.result = False
            self.ui_settings = get_adaptive_ui_settings()

            self.dialog = tk.Toplevel(parent)
            self.dialog.title(f"Conversion Verifier 알파 {APP_VERSION_FULL} - 영구 라이선스 등록")
            # Center over parent; fallback to default placement
            dialog_w = self.ui_settings['window_width']
            dialog_h = self.ui_settings['window_height']
            try:
                if parent and parent.winfo_exists():
                    parent.update_idletasks()
                    px, py = parent.winfo_rootx(), parent.winfo_rooty()
                    pw, ph = parent.winfo_width(), parent.winfo_height()
                    if pw > 0 and ph > 0:
                        x = px + (pw - dialog_w) // 2
                        y = py + (ph - dialog_h) // 2
                        self.dialog.geometry(f"{dialog_w}x{dialog_h}+{x}+{y}")
                    else:
                        self.dialog.geometry(f"{dialog_w}x{dialog_h}")
                else:
                    self.dialog.geometry(f"{dialog_w}x{dialog_h}")
            except Exception:
                self.dialog.geometry(f"{dialog_w}x{dialog_h}")
            self.dialog.resizable(False, False)
            self.dialog.grab_set()

            _apply_global_fonts(self.dialog, self.ui_settings)

            # 창을 화면 중앙에 배치
            self.dialog.transient(parent)
            self.dialog.focus_set()

            self.create_widgets()

        def create_widgets(self):
            # 메인 프레임
            main_frame = ttk.Frame(self.dialog, padding=str(self.ui_settings["padding"]))
            main_frame.pack(fill="both", expand=True)

            # 제목
            title_label = ttk.Label(
                main_frame,
                text="🔐 영구 라이선스 등록",
                font=("맑은 고딕", self.ui_settings["font_size_title"], "bold"),
            )
            title_label.pack(pady=(0, 20))

            # 설명
            desc_text = (
                "영구 라이선스를 등록하시면 크레딧 제한 없이\n"
                "무제한으로 프로그램을 사용하실 수 있습니다."
            )
            desc_label = ttk.Label(
                main_frame,
                text=desc_text,
                justify="center",
                font=("맑은 고딕", self.ui_settings["font_size"]),
            )
            desc_label.pack(pady=(0, 20))

            # 이메일 입력
            email_frame = ttk.LabelFrame(
                main_frame, text="사용자 이메일", padding="10", style="TLabelframe"
            )
            email_frame.pack(fill="x", pady=(0, 10))

            self.email_var = tk.StringVar()
            self.email_entry = ttk.Entry(
                email_frame,
                textvariable=self.email_var,
                width=40,
                font=("맑은 고딕", self.ui_settings["font_size"]),
            )
            self.email_entry.pack(fill="x")

            # 라이선스 키 입력
            license_frame = ttk.LabelFrame(main_frame, text="라이선스 키", padding="10")
            license_frame.pack(fill="x", pady=(0, 20))

            self.license_var = tk.StringVar()
            self.license_entry = ttk.Entry(
                license_frame,
                textvariable=self.license_var,
                width=40,
                show="*",
                font=("맑은 고딕", self.ui_settings["font_size"]),
            )
            self.license_entry.pack(fill="x")

            # 버튼 프레임
            button_frame = ttk.Frame(main_frame)
            button_frame.pack(fill="x")

            register_btn = ttk.Button(
                button_frame, text="등록", command=self.register_license, style="Accent.TButton"
            )
            register_btn.pack(side="right", padx=(5, 0))

            cancel_btn = ttk.Button(button_frame, text="취소", command=self.cancel)
            cancel_btn.pack(side="right")

        def validate_email(self, email):
            """이메일 유효성 검사"""
            pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
            return re.match(pattern, email) is not None

        def register_license(self):
            """라이선스 등록"""
            email = self.email_var.get().strip()
            license_key = self.license_var.get().strip()

            # 유효성 검사
            if not email:
                messagebox.showerror("오류", "이메일을 입력해주세요.", parent=self.dialog)
                return

            if not self.validate_email(email):
                messagebox.showerror("오류", "올바른 이메일 형식이 아닙니다.", parent=self.dialog)
                return

            if not license_key:
                messagebox.showerror("오류", "라이선스 키를 입력해주세요.", parent=self.dialog)
                return

            # 라이선스 키 확인
            if license_key != self.license_password:
                messagebox.showerror("오류", "잘못된 라이선스 키입니다.", parent=self.dialog)
                return

            # 라이선스 등록
            try:
                self.config.save_license_data(email)
                messagebox.showinfo(
                    "성공",
                    f"라이선스가 성공적으로 등록되었습니다!\n\n"
                    f"등록 이메일: {email}\n"
                    f"이제 무제한으로 프로그램을 사용하실 수 있습니다.",
                    parent=self.dialog,
                )
                self.result = True
                self.dialog.destroy()

            except Exception as e:
                messagebox.showerror(
                    "오류", f"라이선스 등록 중 오류가 발생했습니다:\n{str(e)}", parent=self.dialog
                )

        def cancel(self):
            """취소"""
            self.dialog.destroy()

    # 다이얼로그 실행
    dialog = LicenseDialog(parent, config, license_password)
    parent.wait_window(dialog.dialog)

    return dialog.result


def create_credits_management_dialog(parent, config):
    """크레딧 관리 다이얼로그 (관리자용)"""

    class CreditsDialog:
        def __init__(self, parent, config):
            self.parent = parent
            self.config = config
            self.ui_settings = get_adaptive_ui_settings()

            self.dialog = tk.Toplevel(parent)
            self.dialog.title(f"Conversion Verifier 알파 {APP_VERSION_FULL} - 크레딧 관리")
            dialog_w = int(self.ui_settings['window_width']*0.875)
            dialog_h = int(self.ui_settings['window_height']*0.833)
            try:
                if parent and parent.winfo_exists():
                    parent.update_idletasks()
                    px, py = parent.winfo_rootx(), parent.winfo_rooty()
                    pw, ph = parent.winfo_width(), parent.winfo_height()
                    if pw > 0 and ph > 0:
                        x = px + (pw - dialog_w) // 2
                        y = py + (ph - dialog_h) // 2
                        self.dialog.geometry(f"{dialog_w}x{dialog_h}+{x}+{y}")
                    else:
                        self.dialog.geometry(f"{dialog_w}x{dialog_h}")
                else:
                    self.dialog.geometry(f"{dialog_w}x{dialog_h}")
            except Exception:
                self.dialog.geometry(f"{dialog_w}x{dialog_h}")
            self.dialog.resizable(False, False)
            self.dialog.grab_set()

            _apply_global_fonts(self.dialog, self.ui_settings)

            # 창을 화면 중앙에 배치
            self.dialog.transient(parent)
            self.dialog.focus_set()

            self.create_widgets()

        def create_widgets(self):
            # 메인 프레임
            main_frame = ttk.Frame(self.dialog, padding=str(self.ui_settings["padding"]))
            main_frame.pack(fill="both", expand=True)

            # 제목
            title_label = ttk.Label(
                main_frame,
                text="💰 크레딧 관리",
                font=("맑은 고딕", self.ui_settings["font_size_title"], "bold"),
            )
            title_label.pack(pady=(0, 20))

            # 현재 크레딧 표시
            current_frame = ttk.LabelFrame(main_frame, text="현재 상태", padding="10")
            current_frame.pack(fill="x", pady=(0, 15))

            if self.config.license_email:
                status_text = f"라이선스 이메일: {self.config.license_email}\n크레딧: 무제한"
            else:
                status_text = f"현재 크레딧: {self.config.credits}개"

            self.status_label = ttk.Label(
                current_frame, text=status_text, font=("맑은 고딕", self.ui_settings["font_size"])
            )
            self.status_label.pack()

            # 크레딧 추가/차감
            if not self.config.license_email:  # 영구 라이선스가 없는 경우만
                action_frame = ttk.LabelFrame(main_frame, text="크레딧 조정", padding="10")
                action_frame.pack(fill="x", pady=(0, 15))

                # 금액 입력
                amount_frame = ttk.Frame(action_frame)
                amount_frame.pack(fill="x", pady=(0, 10))

                ttk.Label(
                    amount_frame, text="크레딧:", font=("맑은 고딕", self.ui_settings["font_size"])
                ).pack(side="left")

                self.amount_var = tk.StringVar(value="10")
                amount_spinbox = ttk.Spinbox(
                    amount_frame, from_=1, to=1000, textvariable=self.amount_var, width=10
                )
                amount_spinbox.pack(side="left", padx=(10, 0))

                # 버튼들
                btn_frame = ttk.Frame(action_frame)
                btn_frame.pack(fill="x")

                add_btn = ttk.Button(btn_frame, text="➕ 추가", command=self.add_credits)
                add_btn.pack(side="left", padx=(0, 5))

                subtract_btn = ttk.Button(btn_frame, text="➖ 차감", command=self.subtract_credits)
                subtract_btn.pack(side="left")

            # 닫기 버튼
            close_btn = ttk.Button(main_frame, text="닫기", command=self.dialog.destroy)
            close_btn.pack(pady=(10, 0))

        def add_credits(self):
            """크레딧 추가"""
            try:
                amount = int(self.amount_var.get())
                if self.config.update_credits(amount):
                    self.update_status()
                    messagebox.showinfo(
                        "성공", f"{amount} 크레딧이 추가되었습니다.", parent=self.dialog
                    )
                else:
                    messagebox.showerror("오류", "크레딧 추가에 실패했습니다.", parent=self.dialog)
            except ValueError:
                messagebox.showerror("오류", "올바른 숫자를 입력해주세요.", parent=self.dialog)

        def subtract_credits(self):
            """크레딧 차감"""
            try:
                amount = int(self.amount_var.get())
                if self.config.update_credits(-amount):
                    self.update_status()
                    messagebox.showinfo(
                        "성공", f"{amount} 크레딧이 차감되었습니다.", parent=self.dialog
                    )
                else:
                    messagebox.showerror(
                        "오류", "크레딧이 부족하거나 차감에 실패했습니다.", parent=self.dialog
                    )
            except ValueError:
                messagebox.showerror("오류", "올바른 숫자를 입력해주세요.", parent=self.dialog)

        def update_status(self):
            """상태 업데이트"""
            if self.config.license_email:
                status_text = f"라이선스 이메일: {self.config.license_email}\n크레딧: 무제한"
            else:
                status_text = f"현재 크레딧: {self.config.credits}개"

            self.status_label.config(text=status_text)

    # 다이얼로그 실행
    dialog = CreditsDialog(parent, config)


def create_admin_tab_content(parent, config):
    """관리자 탭 내용 생성"""
    ui_settings = get_adaptive_ui_settings()

    _apply_global_fonts(parent, ui_settings)

    # 스크롤 가능한 프레임 설정
    canvas = tk.Canvas(parent, bg="#f0f0f0")
    scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
    scrollable_frame = ttk.Frame(canvas)

    scrollable_frame.bind(
        "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )

    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    # 1. 라이선스 관리 섹션
    license_frame = ttk.LabelFrame(scrollable_frame, text="🔐 라이선스 관리", padding="15")
    license_frame.pack(fill="x", padx=10, pady=(10, 5))

    if config.license_email:
        license_info = (
            f"등록된 라이선스: {config.license_email}\n상태: 영구 라이선스 (무제한 사용 가능)"
        )
        license_color = "green"
    else:
        license_info = "등록된 라이선스가 없습니다.\n상태: 체험판 (크레딧 제한)"
        license_color = "orange"

    license_status = ttk.Label(
        license_frame,
        text=license_info,
        foreground=license_color,
        font=("맑은 고딕", ui_settings["font_size"]),
    )
    license_status.pack(anchor="w", pady=(0, 10))
    _bind_tooltip(license_status, "영구 라이선스: 무제한 사용 가능 / 체험판: 크레딧 제한")

    license_btn_frame = ttk.Frame(license_frame)
    license_btn_frame.pack(fill="x")

    register_license_btn = ttk.Button(
        license_btn_frame,
        text="새 라이선스 등록",
        command=lambda: create_license_registration_dialog(parent, config, config.license_password),
    )
    register_license_btn.pack(side="left", padx=(0, 5))
    _bind_tooltip(register_license_btn, "영구 라이선스 키를 등록하여 크레딧 제한을 제거합니다.")

    if config.license_email:
        remove_license_btn = ttk.Button(
            license_btn_frame, text="라이선스 제거", command=lambda: remove_license(parent, config)
        )
        remove_license_btn.pack(side="left")
        _bind_tooltip(remove_license_btn, "현재 등록된 라이선스를 제거합니다.")

    # 2. 크레딧 관리 섹션
    credits_frame = ttk.LabelFrame(scrollable_frame, text="💰 크레딧 관리", padding="15")
    credits_frame.pack(fill="x", padx=10, pady=5)

    if config.license_email:
        credits_info = "영구 라이선스 - 무제한 크레딧"
    else:
        credits_info = f"현재 크레딧: {config.credits}개"

    credits_status = ttk.Label(
        credits_frame, text=credits_info, font=("맑은 고딕", ui_settings["font_size"])
    )
    credits_status.pack(anchor="w", pady=(0, 10))
    _bind_tooltip(credits_status, "영구 라이선스 상태이거나 남은 크레딧 수를 표시합니다.")

    manage_credits_btn = ttk.Button(
        credits_frame,
        text="크레딧 관리",
        command=lambda: create_credits_management_dialog(parent, config),
    )
    manage_credits_btn.pack(anchor="w")
    _bind_tooltip(manage_credits_btn, "크레딧을 추가하거나 차감할 수 있습니다.")

    # 3. 시스템 정보 섹션
    system_frame = ttk.LabelFrame(scrollable_frame, text="🖥️ 시스템 정보", padding="15")
    system_frame.pack(fill="x", padx=10, pady=5)

    # MAC 주소 정보 (automation에서 가져오기)
    try:
        from automation import ConversionAnalyzer

        analyzer = ConversionAnalyzer()
        mac_address = analyzer.mac_address
    except:
        mac_address = "알 수 없음"

    system_info = f"MAC 주소: {mac_address}\n프로그램 버전: v1.0\n설정 파일: {config.data_file}"
    system_label = ttk.Label(
        system_frame, text=system_info, font=("맑은 고딕", ui_settings["font_size"])
    )
    system_label.pack(anchor="w")

    return scrollable_frame


def remove_license(parent, config):
    """라이선스 제거"""
    if messagebox.askyesno(
        "확인",
        "정말로 라이선스를 제거하시겠습니까?\n\n"
        "라이선스를 제거하면 크레딧 기반 체험판으로 전환됩니다.",
        parent=parent,
    ):
        try:
            config.save_license_data("")  # 빈 문자열로 라이선스 제거
            messagebox.showinfo("완료", "라이선스가 제거되었습니다.", parent=parent)
        except Exception as e:
            messagebox.showerror(
                "오류", f"라이선스 제거 중 오류가 발생했습니다:\n{str(e)}", parent=parent
            )
