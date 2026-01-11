# -*- coding: utf-8 -*-
"""
K-Startup Web Automation Settings UI
설정 창 및 UI 헬퍼 함수 (BE/DC 패턴 통일)
"""

import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox
import json
import logging
from pathlib import Path

# Windows DPI awareness
if sys.platform == 'win32':
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

import pyautogui


def _get_ui_scale() -> float:
    """UI 스케일 가져오기"""
    try:
        from app_setting_data import get_config
        cfg = get_config()
        return float(getattr(cfg, "ui_scale", getattr(cfg, "get", lambda *_: 1.0)("ui_scale", 1.0)))
    except Exception:
        return 1.0


def _apply_ui_scale(settings: dict) -> dict:
    """UI 스케일 적용"""
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
    """전역 폰트 적용"""
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


def _load_version_from_settings():
    """settings.json에서 버전 정보 읽기"""
    default_full = "v1.0.0.0"

    def _ensure_prefix(v: str) -> str:
        v = (v or "").strip()
        if not v:
            return default_full
        return v if v.startswith("v") else "v" + v

    source_full = default_full
    try:
        src_settings = Path(__file__).parent / "config" / "kstartup_web" / "settings.json"
        if src_settings.exists():
            with open(src_settings, "r", encoding="utf-8") as f:
                src_data = json.load(f)
            src_runtime_cfg = src_data.get("runtime_config", {}) or {}
            source_full = _ensure_prefix(src_runtime_cfg.get("full_version", default_full))
    except Exception:
        source_full = default_full

    try:
        if getattr(sys, "frozen", False):
            base_path = Path(sys._MEIPASS) if hasattr(sys, '_MEIPASS') else Path(sys.executable).parent
            settings_file = base_path / ".wf_rpa" / "kstartup_web" / "settings.json"
            if not settings_file.exists():
                settings_file = Path.home() / ".wf_rpa" / "kstartup_web" / "settings.json"
        else:
            settings_file = Path(__file__).parent / "config" / "kstartup_web" / "settings.json"

        if settings_file.exists():
            with open(settings_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            runtime_config = data.get("runtime_config", {}) or {}
            runtime_full = runtime_config.get("full_version")
            if runtime_full:
                return _ensure_prefix(runtime_full)
    except Exception:
        pass

    return source_full


APP_VERSION_FULL = _load_version_from_settings()
APP_VERSION_DISPLAY = "v" + ".".join(APP_VERSION_FULL.lstrip("v").split(".")[:2])


def get_adaptive_ui_settings():
    """화면 해상도에 따른 적응형 UI 설정"""
    screen_width, _ = pyautogui.size()

    # 해상도별 scale factor
    if screen_width >= 3840:  # UHD (4K)
        resolution_scale = 1.5
    elif screen_width >= 2560:  # QHD (1440p)
        resolution_scale = 1.2
    else:  # FHD (1080p)
        resolution_scale = 1.0

    # 저장된 ui_config 불러오기
    saved_ui = {}
    try:
        from app_setting_data import get_config
        cfg = get_config()
        saved_ui = getattr(cfg, "ui_config", {}) or {}
    except Exception:
        saved_ui = {}

    # geometry 문자열에서 폭/높이 추출
    parsed_w = None
    parsed_h = None
    try:
        geo_str = saved_ui.get("window_geometry_override", "")
        if not geo_str:
            geo_str = saved_ui.get("window_geometry", "")
        if geo_str:
            size_part = geo_str.split("+", 1)[0]
            if "x" in size_part:
                w_str, h_str = size_part.split("x", 1)
                parsed_w = int(w_str)
                parsed_h = int(h_str)
    except Exception:
        parsed_w = None
        parsed_h = None

    try:
        default_width = parsed_w if parsed_w is not None else saved_ui.get("window_width", 600)
        default_width = int(default_width)
    except Exception:
        default_width = 600

    try:
        default_height = parsed_h if parsed_h is not None else saved_ui.get("window_height", 200)
        default_height = int(default_height)
    except Exception:
        default_height = 200

    # 기본 설정
    base_settings = {
        "window_width": default_width,
        "window_height": default_height,
        "font_size": 14,
        "font_size_bold": 14,
        "font_size_title": 14,
        "font_family": "맑은 고딕",
        "padding": 12,
        "button_width": 10,
    }

    use_saved_width = (parsed_w is not None) or (isinstance(saved_ui, dict) and "window_width" in saved_ui)
    use_saved_height = (parsed_h is not None) or (isinstance(saved_ui, dict) and "window_height" in saved_ui)

    # resolution scale 적용
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

    # 사용자 지정 크기는 원본 유지
    if use_saved_width:
        result["window_width"] = base_settings["window_width"]
    if use_saved_height:
        result["window_height"] = base_settings["window_height"]

    return result


def load_custom_settings():
    """커스텀 설정 로드"""
    try:
        from app_setting_data import get_config
        cfg = get_config()
        return cfg.ui_config
    except Exception:
        return {}


def apply_custom_settings_to_config(config, custom_settings):
    """커스텀 설정을 config에 적용"""
    if not custom_settings:
        return
    
    try:
        for key, value in custom_settings.items():
            setattr(config, key, value)
    except Exception:
        pass


def create_settings_window(parent, config, app_version_full):
    """설정 창 생성"""
    ui_settings = get_adaptive_ui_settings()

    # 전역 폰트 적용
    _apply_global_fonts(parent, ui_settings)

    win = tk.Toplevel(parent)
    win.title(f"K-Startup 웹 자동화 {app_version_full} - 설정")

    base_font = ("맑은 고딕", ui_settings["font_size"])
    title_font = ("맑은 고딕", ui_settings["font_size_title"], "bold")

    # 스타일 설정
    style = ttk.Style(win)
    for name in (
        "TLabel",
        "TButton",
        "TCheckbutton",
        "TRadiobutton",
        "TEntry",
        "TSpinbox",
        "TCombobox",
        "TNotebook.Tab",
    ):
        try:
            style.configure(name, font=base_font)
        except Exception:
            pass

    # 창 크기 및 위치
    win_width = 600
    win_height = 400

    # 부모 창 중앙에 배치
    x = y = None
    try:
        if parent and parent.winfo_exists():
            parent.update_idletasks()
            px, py = parent.winfo_rootx(), parent.winfo_rooty()
            pw, ph = parent.winfo_width(), parent.winfo_height()
            if pw > 0 and ph > 0:
                x = px + (pw - win_width) // 2
                y = py + (ph - win_height) // 2
    except Exception:
        x = y = None

    if x is None or y is None:
        try:
            screen_w, screen_h = pyautogui.size()
        except Exception:
            screen_w, screen_h = 1920, 1080
        x = (screen_w - win_width) // 2
        y = (screen_h - win_height) // 2

    win.geometry(f"{win_width}x{win_height}+{x}+{y}")
    win.resizable(False, False)
    win.wm_attributes("-topmost", 1)
    win.transient(parent)
    win.grab_set()
    win.focus_set()

    # 메인 프레임
    main = tk.Frame(win, padx=ui_settings["padding"], pady=ui_settings["padding"])
    main.pack(fill="both", expand=True)

    # 제목
    title_label = tk.Label(
        main,
        text="설정",
        font=title_font,
        fg="#333333"
    )
    title_label.pack(pady=(0, 20))

    # 설정 프레임
    settings_frame = tk.LabelFrame(
        main,
        text="자동화 설정",
        font=base_font,
        padx=12,
        pady=10
    )
    settings_frame.pack(fill="x", pady=(0, 10))

    # Chrome Driver 경로
    row = 0
    tk.Label(
        settings_frame,
        text="Chrome Driver:",
        font=base_font
    ).grid(row=row, column=0, sticky="w", padx=5, pady=5)
    
    chrome_driver_var = tk.StringVar(value=config.get("chrome_driver_path", "chromedriver"))
    chrome_entry = ttk.Entry(settings_frame, textvariable=chrome_driver_var, width=40)
    chrome_entry.grid(row=row, column=1, sticky="ew", padx=5, pady=5)

    # Headless 모드
    row += 1
    headless_var = tk.BooleanVar(value=config.get("headless_mode", False))
    headless_check = ttk.Checkbutton(
        settings_frame,
        text="Headless 모드 (백그라운드 실행)",
        variable=headless_var
    )
    headless_check.grid(row=row, column=0, columnspan=2, sticky="w", padx=5, pady=5)

    # 대기 시간
    row += 1
    tk.Label(
        settings_frame,
        text="대기 시간 (초):",
        font=base_font
    ).grid(row=row, column=0, sticky="w", padx=5, pady=5)
    
    wait_timeout_var = tk.IntVar(value=config.get("wait_timeout", 10))
    wait_spinner = ttk.Spinbox(settings_frame, from_=5, to=60, textvariable=wait_timeout_var, width=10)
    wait_spinner.grid(row=row, column=1, sticky="w", padx=5, pady=5)

    # 스크린샷 활성화
    row += 1
    screenshot_var = tk.BooleanVar(value=config.get("screenshot_enabled", True))
    screenshot_check = ttk.Checkbutton(
        settings_frame,
        text="스크린샷 저장 활성화",
        variable=screenshot_var
    )
    screenshot_check.grid(row=row, column=0, columnspan=2, sticky="w", padx=5, pady=5)

    # 쿠키 저장
    row += 1
    cookie_var = tk.BooleanVar(value=config.get("save_cookies", True))
    cookie_check = ttk.Checkbutton(
        settings_frame,
        text="세션 쿠키 저장",
        variable=cookie_var
    )
    cookie_check.grid(row=row, column=0, columnspan=2, sticky="w", padx=5, pady=5)

    settings_frame.columnconfigure(1, weight=1)

    # 버튼 프레임
    button_frame = tk.Frame(main)
    button_frame.pack(fill="x", pady=(20, 0))

    def save_settings():
        """설정 저장"""
        try:
            # automation_config 업데이트
            if hasattr(config, 'automation_config'):
                config.automation_config["chrome_driver_path"] = chrome_driver_var.get()
                config.automation_config["headless_mode"] = headless_var.get()
                config.automation_config["wait_timeout"] = wait_timeout_var.get()
                config.automation_config["screenshot_enabled"] = screenshot_var.get()
                config.automation_config["save_cookies"] = cookie_var.get()
            
            config.save_settings()
            messagebox.showinfo("저장 완료", "설정이 저장되었습니다.", parent=win)
            win.destroy()
        except Exception as e:
            messagebox.showerror("오류", f"설정 저장 중 오류 발생:\n{str(e)}", parent=win)

    # 저장 버튼
    ttk.Button(
        button_frame,
        text="저장",
        command=save_settings,
        width=12
    ).pack(side="right", padx=5)

    # 취소 버튼
    ttk.Button(
        button_frame,
        text="취소",
        command=win.destroy,
        width=12
    ).pack(side="right", padx=5)

    # 버전 정보
    version_label = tk.Label(
        main,
        text=f"버전: {app_version_full}",
        font=("맑은 고딕", ui_settings["font_size"] - 2),
        fg="#999999"
    )
    version_label.pack(side="bottom", pady=(10, 0))
