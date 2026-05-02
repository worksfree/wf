# -*- coding: utf-8 -*-
"""Unified simplified settings window for QR Code Generator (dwg_classifier-style)."""

import os
import sys

# Windows DPI awareness 설정 (스케일링 통일)
if sys.platform == 'win32':
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json

# Adaptive UI 통합 모듈
try:
    from wf_ui_adaptive import get_adaptive_ui_settings, apply_global_fonts
except ImportError:
    # fallback: 공통 모듈 경로 추가
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


current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

APP_VERSION_FULL = None
APP_VERSION_DISPLAY = None


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
    """fallback: settings.json에서 직접 버전 읽기"""
    default_full = "v0.7.0.0"

    try:
        if getattr(sys, "frozen", False):
            settings_file = Path.home() / ".wf_rpa" / "qrcode_generator" / "settings.json"
            if not settings_file.exists():
                base_path = Path(sys._MEIPASS) if hasattr(sys, '_MEIPASS') else Path(sys.executable).parent
                settings_file = base_path / ".wf_rpa" / "qrcode_generator" / "settings.json"
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
            return full_version
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


try:
    from wf_settings_common import get_user_hardware_info, format_info_for_tree, sync_policies_from_sheets
except Exception:

    def get_user_hardware_info():
        return {}

    def format_info_for_tree(info):
        return {}

    def sync_policies_from_sheets(app_name, logger=None):
        return {"success": False, "message": "sync_policies_from_sheets not available"}


def create_settings_window(parent, config, icon_path=None):
    saved_ui = _get_saved_ui_config()
    ui_settings = get_adaptive_ui_settings(window_type="sub", saved_ui=saved_ui)

    apply_global_fonts(parent, ui_settings)

    def _bind_tooltip(widget, text: str):
        if not text:
            return
        tip = {"win": None}

        def enter(_):
            if tip["win"]:
                return
            try:
                x = widget.winfo_rootx() + 16
                y = widget.winfo_rooty() + 16
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
                    font=("맑은 고딕", ui_settings["font_size"]),
                    padx=6,
                    pady=3,
                    justify="left",
                )
                lbl.pack()
                tip["win"] = tw
            except Exception:
                pass

        def leave(_):
            if tip["win"]:
                try:
                    tip["win"].destroy()
                except Exception:
                    pass
                tip["win"] = None

        widget.bind("<Enter>", enter)
        widget.bind("<Leave>", leave)

    win = tk.Toplevel(parent)
    win.withdraw()  # 깜빡임 방지: geometry 설정 전까지 숨김
    version_full, _ = _get_version_from_main()
    win.title(f"QR 코드 생성기 {version_full} - 설정")

    # 앱별 아이콘 적용
    try:
        if icon_path:
            win.iconbitmap(str(icon_path))
    except Exception:
        pass

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

    win_width = max(ui_settings["window_width"], 660)
    # QG 설정창 최적 높이: 580px (항목 수에 맞춤)
    win_height = max(ui_settings["window_height"], 580)

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

    style = ttk.Style(win)
    style.configure("TCombobox", font=("맑은 고딕", ui_settings["font_size"]))
    style.configure("Treeview", font=("맑은 고딕", ui_settings["font_size"]), rowheight=int(ui_settings["font_size"] * 1.6))
    style.configure("Treeview.Heading", font=("맑은 고딕", ui_settings["font_size"], "bold"))
    win.option_add("*TCombobox*Listbox.font", ("맑은 고딕", ui_settings["font_size"]))

    main = tk.Frame(win, padx=ui_settings["padding"], pady=max(0, ui_settings["padding"] - 6))
    main.pack(fill="both", expand=True)

    # Section 1: 사용자 및 하드웨어 정보
    info_frame = tk.LabelFrame(
        main,
        text="사용자 및 하드웨어 정보",
        font=("맑은 고딕", ui_settings["font_size_bold"], "bold"),
        padx=10,
        pady=8,
    )
    info_frame.pack(fill="x", pady=(0, 10))
    rows = format_info_for_tree(get_user_hardware_info()) if callable(format_info_for_tree) else {}
    if rows:
        tree = ttk.Treeview(info_frame, columns=("항목", "정보"), show="headings", height=5)
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

    # Section 2: QR 코드 설정
    app_frame = tk.LabelFrame(
        main,
        text="QR 코드 설정",
        font=("맑은 고딕", ui_settings["font_size_bold"], "bold"),
        padx=10,
        pady=8,
    )
    app_frame.pack(fill="both", expand=True, pady=(0, 10))

    output_folder = tk.StringVar(value=getattr(config, "output_folder", ""))
    title_text = tk.StringVar(value=getattr(config, "title_text", "홈페이지"))
    subtitle_text = tk.StringVar(value=getattr(config, "subtitle_text", "Scan Me!"))
    output_filename = tk.StringVar(value=getattr(config, "output_filename", "qrcode_output.png"))
    qr_version_var = tk.IntVar(value=getattr(config, "qr_version", 1))
    error_correction_var = tk.StringVar(value=getattr(config, "error_correction", "L"))
    box_size_var = tk.IntVar(value=getattr(config, "box_size", 25))
    border_var = tk.IntVar(value=getattr(config, "border", 4))

    # Row 0: 출력 폴더
    lbl_output = tk.Label(app_frame, text="출력 폴더", font=base_font)
    lbl_output.grid(row=0, column=0, sticky="w", pady=2)
    out_entry = tk.Entry(app_frame, textvariable=output_folder, font=base_font)
    out_entry.grid(row=0, column=1, columnspan=2, sticky="ew", padx=(8, 6))
    _bind_tooltip(lbl_output, "QR 코드 이미지가 저장될 폴더입니다.")
    _bind_tooltip(out_entry, "폴더를 직접 입력하거나 '찾기' 버튼으로 선택하세요.")

    def browse_out():
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

        cur = output_folder.get() or os.path.dirname(os.path.abspath(__file__))
        sel = filedialog.askdirectory(initialdir=cur, title="출력 폴더 선택", parent=win)

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
            output_folder.set(sel)

    tk.Button(
        app_frame, text="찾기", command=browse_out, width=8, font=base_font,
    ).grid(row=0, column=3, pady=2)

    # Row 1: 제목 텍스트
    lbl_title = tk.Label(app_frame, text="제목 텍스트", font=base_font)
    lbl_title.grid(row=1, column=0, sticky="w", pady=2)
    ent_title = tk.Entry(app_frame, textvariable=title_text, font=base_font)
    ent_title.grid(row=1, column=1, columnspan=3, sticky="ew", padx=(8, 6))
    _bind_tooltip(lbl_title, "QR 코드 상단에 표시될 제목입니다.")

    # Row 2: 부제목 텍스트
    lbl_subtitle = tk.Label(app_frame, text="부제목 텍스트", font=base_font)
    lbl_subtitle.grid(row=2, column=0, sticky="w", pady=2)
    ent_subtitle = tk.Entry(app_frame, textvariable=subtitle_text, font=base_font)
    ent_subtitle.grid(row=2, column=1, columnspan=3, sticky="ew", padx=(8, 6))
    _bind_tooltip(lbl_subtitle, "QR 코드 하단에 표시될 부제목입니다.")

    # Row 3: 출력 파일명
    lbl_filename = tk.Label(app_frame, text="출력 파일명", font=base_font)
    lbl_filename.grid(row=3, column=0, sticky="w", pady=2)
    ent_filename = tk.Entry(app_frame, textvariable=output_filename, font=base_font)
    ent_filename.grid(row=3, column=1, columnspan=3, sticky="ew", padx=(8, 6))
    _bind_tooltip(lbl_filename, "저장될 이미지 파일명입니다. (예: qrcode_output.png)")

    # Row 4: QR 버전 | 오류 정정 (2열 배치)
    lbl_version = tk.Label(app_frame, text="QR 버전", font=base_font)
    lbl_version.grid(row=4, column=0, sticky="w", pady=2)
    spn_version = tk.Spinbox(app_frame, from_=1, to=40, textvariable=qr_version_var, width=8, font=base_font)
    spn_version.grid(row=4, column=1, sticky="w", padx=(8, 6))
    _bind_tooltip(lbl_version, "QR 코드 버전 (1~40). 높을수록 더 많은 데이터 저장 가능.")

    lbl_ec = tk.Label(app_frame, text="오류 정정", font=base_font)
    lbl_ec.grid(row=4, column=2, sticky="w", padx=(16, 0), pady=2)
    ec_combo = ttk.Combobox(
        app_frame,
        textvariable=error_correction_var,
        values=["L", "M", "Q", "H"],
        state="readonly",
        width=8,
    )
    ec_combo.grid(row=4, column=3, sticky="w", padx=(8, 6))
    _bind_tooltip(lbl_ec, "오류 정정 레벨: L(7%) < M(15%) < Q(25%) < H(30%)")

    # Row 5: 모듈 크기 | 테두리 (2열 배치)
    lbl_box = tk.Label(app_frame, text="모듈 크기", font=base_font)
    lbl_box.grid(row=5, column=0, sticky="w", pady=2)
    spn_box = tk.Spinbox(app_frame, from_=5, to=50, textvariable=box_size_var, width=8, font=base_font)
    spn_box.grid(row=5, column=1, sticky="w", padx=(8, 6))
    _bind_tooltip(lbl_box, "각 QR 모듈(점)의 픽셀 크기입니다.")

    lbl_border = tk.Label(app_frame, text="테두리", font=base_font)
    lbl_border.grid(row=5, column=2, sticky="w", padx=(16, 0), pady=2)
    spn_border = tk.Spinbox(app_frame, from_=1, to=10, textvariable=border_var, width=8, font=base_font)
    spn_border.grid(row=5, column=3, sticky="w", padx=(8, 6))
    _bind_tooltip(lbl_border, "QR 코드 주변 여백 모듈 수입니다.")

    app_frame.columnconfigure(1, weight=1)

    # Buttons
    btn_frame = tk.Frame(main)
    btn_frame.pack(side="bottom", pady=(12, 10), fill="x")
    button_container = tk.Frame(btn_frame)
    button_container.pack(expand=True)

    def save():
        settings_update = {
            "output_folder": output_folder.get().strip(),
            "title_text": title_text.get().strip(),
            "subtitle_text": subtitle_text.get().strip(),
            "output_filename": output_filename.get().strip() or "qrcode_output.png",
            "qr_version": qr_version_var.get(),
            "error_correction": error_correction_var.get(),
            "box_size": box_size_var.get(),
            "border": border_var.get(),
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
        font=base_font,
    )
    save_btn.pack(side="left", padx=20)

    cancel_btn = tk.Button(
        button_container,
        text="취소",
        command=lambda: (win.grab_release(), win.destroy()),
        width=ui_settings["button_width"],
        height=2,
        font=base_font,
    )
    cancel_btn.pack(side="left", padx=20)

    # Alt+G: geometry 저장 (디버깅용)
    def _on_debug_geometry_capture(_event=None):
        try:
            geo = win.geometry()
            msg = f"[DEBUG] SettingsWindow geometry: {geo}"
            print(msg)
            ok = False
            if config and hasattr(config, "update_settings_window_geometry"):
                ok = config.update_settings_window_geometry(geo)
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


if __name__ == "__main__":
    from app_setting_data import get_config

    rt = tk.Tk()
    rt.withdraw()
    cfg = get_config()
    create_settings_window(rt, cfg)
    rt.destroy()
