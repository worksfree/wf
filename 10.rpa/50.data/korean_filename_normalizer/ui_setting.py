# -*- coding: utf-8 -*-
"""Unified Settings UI for Korean Filename Normalizer matching bom2excel style."""

import os
import sys

# Windows DPI awareness 설정 (스케일링 통일)
if sys.platform == 'win32':
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass  # Already set or not supported

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json

# Adaptive UI 통합 모듈
try:
    from wf_ui_adaptive import get_adaptive_ui_settings, apply_global_fonts
except ImportError:
    import os
    _common_dir = os.path.join(os.path.dirname(__file__), "..", "..", "10.common")
    if _common_dir not in sys.path:
        sys.path.insert(0, _common_dir)
    from wf_ui_adaptive import get_adaptive_ui_settings, apply_global_fonts
import logging
from pathlib import Path


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


# 버전 정보: ui_main.py와 동일한 소스 사용 (중복 로직 제거)
# ⚠️ 중요: 버전 정보는 반드시 ui_main.py의 APP_VERSION_FULL을 참조해야 함
APP_VERSION_FULL = None  # 지연 로드
APP_VERSION_DISPLAY = None  # 지연 로드


def _get_version_from_main():
    """ui_main.py에서 버전 정보 가져오기 (단일 소스 원칙)"""
    global APP_VERSION_FULL, APP_VERSION_DISPLAY
    if APP_VERSION_FULL is not None:
        return APP_VERSION_FULL, APP_VERSION_DISPLAY

    try:
        from ui_main import APP_VERSION_FULL as main_full, APP_VERSION_DISPLAY as main_display
        APP_VERSION_FULL = main_full
        APP_VERSION_DISPLAY = main_display
    except ImportError:
        APP_VERSION_FULL = _load_version_fallback()
        parts = APP_VERSION_FULL.lstrip("v").split(".")
        APP_VERSION_DISPLAY = "v" + ".".join(parts[:2])

    return APP_VERSION_FULL, APP_VERSION_DISPLAY


def _load_version_fallback():
    """fallback: settings.json에서 직접 버전 읽기 (ui_main.py와 동일 로직)"""
    default_full = "v0.7.0.0"

    def _ensure_prefix(v: str) -> str:
        v = (v or "").strip()
        if not v:
            return default_full
        return v if v.startswith("v") else "v" + v

    try:
        if getattr(sys, "frozen", False):
            # 릴리스 모드: 사용자 홈 우선 (사용자 설정 반영), 없으면 번들 폴더로 fallback
            settings_file = Path.home() / ".wf_rpa" / "korean_filename_normalizer" / "settings.json"
            if not settings_file.exists():
                base_path = Path(sys._MEIPASS) if hasattr(sys, '_MEIPASS') else Path(sys.executable).parent
                settings_file = base_path / ".wf_rpa" / "korean_filename_normalizer" / "settings.json"
        else:
            # ⚠️ 개발 모드: 10.common/config가 표준 경로
            app_root = Path(__file__).parent
            settings_file = app_root.parent.parent / "10.common" / "config" / "korean_filename_normalizer" / "settings.json"
            if not settings_file.exists():
                settings_file = app_root / "config" / "korean_filename_normalizer" / "settings.json"

        if settings_file.exists():
            with open(settings_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            app_config = data.get("app_config", {}) or {}
            runtime_full = app_config.get("full_version")
            if runtime_full:
                return _ensure_prefix(runtime_full)
    except Exception:
        pass

    return default_full


def _get_saved_ui_config() -> dict:
    """앱 설정에서 저장된 UI 설정 로드"""
    try:
        from app_setting_data import get_config
        cfg = get_config()
        return getattr(cfg, "ui_config", {}) or {}
    except Exception:
        return {}


# Graceful import of common settings info provider with fallbacks for lint/static analysis
try:  # runtime import
    from wf_settings_common import get_user_hardware_info, format_info_for_tree  # type: ignore
except Exception:  # broad: if path not yet set during static scan or runtime

    def get_user_hardware_info():  # fallback minimal stub
        return {}

    def format_info_for_tree(info):
        return {}


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


def create_settings_window(parent, config, icon_path=None):
    ui_settings = get_adaptive_ui_settings()

    # Force all Tk default fonts to unified sizes
    apply_global_fonts(parent, ui_settings)

    win = tk.Toplevel(parent)
    win.withdraw()  # 깜빡임 방지: geometry 설정 전까지 숨김
    version_full, _ = _get_version_from_main()
    win.title(f"Korean Filename Normalizer 알파 {version_full} - 설정")

    # 앱별 아이콘 적용
    try:
        if icon_path:
            win.iconbitmap(str(icon_path))
    except Exception:
        pass

    # ttk 기본 폰트를 메인 UI와 동일하게 적용
    base_font = ("맑은 고딕", ui_settings["font_size"])
    title_font = ("맑은 고딕", ui_settings["font_size_title"], "bold")
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
    try:
        style.configure("Heading.TLabel", font=title_font)
        style.configure("Section.TLabel", font=title_font)
    except Exception:
        pass

    # 설정창 크기를 충분히 확보하고 중앙 정렬
    win_width = max(ui_settings["window_width"], 660)
    # Raised default height to keep all fields visible
    win_height = max(ui_settings["window_height"], 640)

    # Center over parent if available; fallback to screen center
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
    win.resizable(True, True)
    win.wm_attributes("-topmost", 1)
    win.transient(parent)
    win.grab_set()
    win.focus_set()
    win.deiconify()  # 모든 설정 완료 후 표시

    main_frame = tk.Frame(win, padx=ui_settings["padding"], pady=ui_settings["padding"] - 4)
    main_frame.pack(fill="both", expand=True)

    # 사용자 / 하드웨어 정보 섹션
    info_frame = tk.LabelFrame(
        main_frame,
        text="사용자 및 하드웨어 정보",
        font=("맑은 고딕", ui_settings["font_size_bold"], "bold"),
        padx=12,
        pady=10,
    )
    info_frame.pack(fill="x", pady=(0, 16))
    rows = format_info_for_tree(get_user_hardware_info()) if callable(format_info_for_tree) else {}
    if rows:
        tree = ttk.Treeview(info_frame, columns=("항목", "정보"), show="headings", height=6)
        tree.column("항목", width=140, anchor="w")
        tree.heading("항목", text="항목")
        tree.column("정보", width=360, anchor="w")
        tree.heading("정보", text="정보")
        vsb = ttk.Scrollbar(info_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)
        tree.pack(side="left", fill="x", expand=True)
        vsb.pack(side="right", fill="y")
        for label, value in rows.items():
            if value and str(value).strip():
                tree.insert("", "end", values=(label, value))
    else:
        tk.Label(info_frame, text="정보를 가져올 수 없습니다", fg="red").pack(anchor="w")

    # 앱별 설정 섹션
    app_frame = tk.LabelFrame(
        main_frame,
        text="설정",
        font=("맑은 고딕", ui_settings["font_size_bold"], "bold"),
        padx=12,
        pady=10,
    )
    app_frame.pack(fill="x", pady=(0, 16))

    default_folder_path = tk.StringVar(value=config.get("default_folder_path", ""))
    same_folder = tk.BooleanVar(value=not config.get("save_to_new_folder", True))
    conflict_policy = tk.StringVar(
        value=(
            "overwrite"
            if config.get("conflict_resolution", "auto_rename") == "overwrite"
            else "skip"
        )
    )

    # 기본 대상 폴더
    default_folder_label = tk.Label(app_frame, text="기본 대상 폴더", font=("맑은 고딕", ui_settings["font_size"]))
    default_folder_label.grid(row=0, column=0, sticky="w", pady=4)
    _bind_tooltip(default_folder_label, "결과를 저장할 기본 폴더 위치입니다.")
    folder_entry = tk.Entry(
        app_frame, textvariable=default_folder_path, font=("맑은 고딕", ui_settings["font_size"])
    )
    folder_entry.grid(row=0, column=1, sticky="ew", padx=(8, 6))
    _bind_tooltip(folder_entry, "폴더 경로를 입력하거나 '찾기' 버튼으로 선택하세요.")

    def browse_folder():
        original_win_topmost = win.attributes("-topmost")
        parent_topmost = None
        if parent:
            try:
                parent_topmost = parent.attributes("-topmost")
                parent.attributes("-topmost", 0)
            except Exception:
                parent_topmost = None
        win.grab_release()
        win.update()
        cur = default_folder_path.get() or os.path.dirname(os.path.abspath(__file__))
        sel = filedialog.askdirectory(initialdir=cur, title="기본 대상 폴더 선택", parent=win)
        if win.winfo_exists():
            win.lift()
            win.attributes("-topmost", original_win_topmost)
            win.grab_set()
            win.focus_set()
        if parent_topmost is not None and parent:
            try:
                parent.attributes("-topmost", parent_topmost)
            except Exception:
                pass
        if win.winfo_exists():
            win.lift()
            win.focus_set()
        if sel:
            default_folder_path.set(sel)

    tk.Button(
        app_frame,
        text="찾기",
        command=browse_folder,
        width=8,
        font=("맑은 고딕", ui_settings["font_size"]),
    ).grid(row=0, column=2, pady=4)
    app_frame.columnconfigure(1, weight=1)

    # 출력 위치 전략
    save_loc_label = tk.Label(app_frame, text="결과 저장 위치", font=("맑은 고딕", ui_settings["font_size"]))
    save_loc_label.grid(row=1, column=0, sticky="w", pady=4)
    _bind_tooltip(save_loc_label, "처리된 파일을 저장할 위치를 선택합니다.")
    loc_frame = tk.Frame(app_frame)
    loc_frame.grid(row=1, column=1, columnspan=2, sticky="w")
    same_folder_btn = tk.Radiobutton(
        loc_frame,
        text="원본 폴더에 저장",
        variable=same_folder,
        value=True,
        font=("맑은 고딕", ui_settings["font_size"]),
    )
    same_folder_btn.pack(anchor="w")
    _bind_tooltip(same_folder_btn, "복원된 파일을 원본 폴더에 저장합니다.")
    new_folder_btn = tk.Radiobutton(
        loc_frame,
        text="새 폴더에 저장",
        variable=same_folder,
        value=False,
        font=("맑은 고딕", ui_settings["font_size"]),
    )
    new_folder_btn.pack(anchor="w")
    _bind_tooltip(new_folder_btn, "복원된 파일을 새 폴더에 저장합니다.")

    # 파일 처리 방식
    file_mode_label = tk.Label(
        app_frame, text="파일 처리 방식", font=("맑은 고딕", ui_settings["font_size"])
    )
    file_mode_label.grid(row=2, column=0, sticky="w", pady=4)
    _bind_tooltip(file_mode_label, "원본 파일을 변경할지 별도 복사본을 만들지 선택합니다.")
    file_operation_mode = tk.StringVar(value=config.get("file_operation_mode", "copy"))
    operation_frame = tk.Frame(app_frame)
    operation_frame.grid(row=2, column=1, columnspan=2, sticky="w")
    rename_btn = tk.Radiobutton(
        operation_frame,
        text="원본 파일명 변경",
        variable=file_operation_mode,
        value="rename",
        font=("맑은 고딕", ui_settings["font_size"]),
    )
    rename_btn.pack(anchor="w")
    _bind_tooltip(rename_btn, "원본 파일명을 직접 변경합니다.")
    copy_btn = tk.Radiobutton(
        operation_frame,
        text="복원본 별도 생성",
        variable=file_operation_mode,
        value="copy",
        font=("맑은 고딕", ui_settings["font_size"]),
    )
    copy_btn.pack(anchor="w")
    _bind_tooltip(copy_btn, "원본은 유지하고 복원된 파일을 별도로 생성합니다.")

    # 충돌 정책
    conflict_label = tk.Label(
        app_frame, text="파일명 충돌 시 처리", font=("맑은 고딕", ui_settings["font_size"])
    )
    conflict_label.grid(row=3, column=0, sticky="w", pady=4)
    _bind_tooltip(conflict_label, "같은 파일명이 이미 있을 때 어떻게 처리할지 선택합니다.")
    pol_frame = tk.Frame(app_frame)
    pol_frame.grid(row=3, column=1, columnspan=2, sticky="w")
    overwrite_btn = tk.Radiobutton(
        pol_frame,
        text="덮어쓰기",
        variable=conflict_policy,
        value="overwrite",
        font=("맑은 고딕", ui_settings["font_size"]),
    )
    overwrite_btn.pack(anchor="w")
    _bind_tooltip(overwrite_btn, "기존 파일을 새 파일로 덮어씁니다.")
    skip_btn = tk.Radiobutton(
        pol_frame,
        text="건너뛰기",
        variable=conflict_policy,
        value="skip",
        font=("맑은 고딕", ui_settings["font_size"]),
    )
    skip_btn.pack(anchor="w")
    _bind_tooltip(skip_btn, "기존 파일은 유지하고 처리를 건너뜁니다.")

    # 버튼 프레임
    btn_frame = tk.Frame(main_frame)
    btn_frame.pack(side="bottom", pady=(20, 15), fill="x")
    button_container = tk.Frame(btn_frame)
    button_container.pack(expand=True)

    def save():
        settings_update = {
            "default_folder_path": default_folder_path.get().strip(),
            "save_to_new_folder": (not same_folder.get()),
            "file_operation_mode": file_operation_mode.get(),
            "conflict_resolution": conflict_policy.get(),
        }
        try:
            config.update_config(settings_update)
            if config.save_settings():
                messagebox.showinfo("저장 완료", "설정이 저장되었습니다.", parent=win)
                win.grab_release()
                win.destroy()
            else:
                messagebox.showerror("오류", "설정 저장에 실패했습니다.", parent=win)
        except Exception as e:
            messagebox.showerror("오류", f"설정 저장 중 오류: {e}", parent=win)

    save_btn = tk.Button(
        button_container,
        text="저장",
        command=save,
        width=ui_settings["button_width"],
        height=2,
        font=("맑은 고딕", ui_settings["font_size"]),
    )
    save_btn.pack(side="left", padx=20)

    cancel_btn = tk.Button(
        button_container,
        text="취소",
        command=lambda: (win.grab_release(), win.destroy()),
        width=ui_settings["button_width"],
        height=2,
        font=("맑은 고딕", ui_settings["font_size"]),
    )
    cancel_btn.pack(side="left", padx=20)

    # Alt+G: geometry 저장 (디버깅용)
    def _on_debug_geometry_capture(_event=None):
        try:
            geo = win.geometry()
            msg = f"[DEBUG] SettingsWindow geometry: {geo}"
            print(msg)
            # settings.json에 저장 시도
            ok = False
            if config and hasattr(config, "update_settings_window_geometry"):
                ok = config.update_settings_window_geometry(geo)
            # 토스트 메시지 표시
            toast = tk.Toplevel(win)
            toast.overrideredirect(True)
            toast.attributes("-topmost", True)
            toast_msg = f"geometry 저장됨: {geo}" if ok else f"geometry: {geo}"
            lbl = tk.Label(
                toast, text=toast_msg, bg="#333333", fg="white",
                font=("맑은 고딕", 9), padx=10, pady=5
            )
            lbl.pack()
            toast.update_idletasks()
            x = win.winfo_x() + (win.winfo_width() - toast.winfo_reqwidth()) // 2
            y = win.winfo_y() + win.winfo_height() - toast.winfo_reqheight() - 10
            toast.geometry(f"+{x}+{y}")
            toast.after(1400, toast.destroy)
        except Exception:
            pass

    win.bind_all("<Alt-g>", _on_debug_geometry_capture)

    win.protocol("WM_DELETE_WINDOW", lambda: (win.grab_release(), win.destroy()))
    parent.wait_window(win)
    return True
