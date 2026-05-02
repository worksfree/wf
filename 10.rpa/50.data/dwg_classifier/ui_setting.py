"""Unified simplified settings window for DWG Classifier (bom2excel-style)."""

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
        from app_setting_data import get_config  # local app config

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

# 버전 정보: ui_main.py와 동일한 소스 사용 (중복 로직 제거)
# ⚠️ 중요: 버전 정보는 반드시 ui_main.py의 APP_VERSION_FULL을 참조해야 함
# 직접 settings.json을 읽으면 경로 불일치로 잘못된 버전이 표시될 수 있음
APP_VERSION_FULL = None  # 지연 로드
APP_VERSION_DISPLAY = None  # 지연 로드


def _get_version_from_main():
    """ui_main.py에서 버전 정보 가져오기 (단일 소스 원칙)"""
    global APP_VERSION_FULL, APP_VERSION_DISPLAY
    if APP_VERSION_FULL is not None:
        return APP_VERSION_FULL, APP_VERSION_DISPLAY

    try:
        # ui_main.py에서 이미 로드된 버전 정보 사용
        from ui_main import APP_VERSION_FULL as main_full, APP_VERSION_DISPLAY as main_display
        APP_VERSION_FULL = main_full
        APP_VERSION_DISPLAY = main_display
    except ImportError:
        # ui_main.py를 import 할 수 없는 경우 (독립 실행 등) 직접 로드
        APP_VERSION_FULL = _load_version_fallback()
        parts = APP_VERSION_FULL.lstrip("v").split(".")
        APP_VERSION_DISPLAY = "v" + ".".join(parts[:2])

    return APP_VERSION_FULL, APP_VERSION_DISPLAY


def _load_version_fallback():
    """fallback: settings.json에서 직접 버전 읽기 (ui_main.py와 동일 로직)"""
    import json
    import sys
    from pathlib import Path

    default_full = "v0.7.0.0"

    try:
        if getattr(sys, "frozen", False):
            # 릴리스 모드: 사용자 홈 우선 (사용자 설정 반영), 없으면 번들 폴더로 fallback
            settings_file = Path.home() / ".wf_rpa" / "dwg_classifier" / "settings.json"
            if not settings_file.exists():
                base_path = Path(sys._MEIPASS) if hasattr(sys, '_MEIPASS') else Path(sys.executable).parent
                settings_file = base_path / ".wf_rpa" / "dwg_classifier" / "settings.json"
        else:
            # ⚠️ 개발 모드: 10.common/config가 표준 경로
            app_root = Path(__file__).parent
            settings_file = app_root.parent.parent / "10.common" / "config" / "dwg_classifier" / "settings.json"
            if not settings_file.exists():
                settings_file = app_root / "config" / "dwg_classifier" / "settings.json"

        if settings_file.exists():
            with open(settings_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            app_config = data.get("app_config", {}) or {}
            runtime_config = data.get("runtime_config", {})
            full_version = app_config.get("full_version") or runtime_config.get("full_version", default_full)
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
    from wf_settings_common import get_user_hardware_info, format_info_for_tree, sync_policies_from_sheets  # type: ignore
except Exception:

    def get_user_hardware_info():
        return {}

    def format_info_for_tree(info):
        return {}

    def sync_policies_from_sheets(app_name, logger=None):
        return {"success": False, "message": "sync_policies_from_sheets not available"}


def create_settings_window(parent, config):
    ui_settings = get_adaptive_ui_settings()

    # Force all Tk default fonts to unified sizes
    apply_global_fonts(parent, ui_settings)

    # lightweight tooltip helper (bom2excel-style)
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
    win.title(f"DWG Classifier 알파 {version_full} - 설정")

    # 앱별 아이콘 적용 (parent_app에서 icon_path 가져오기)
    try:
        icon_path = getattr(parent_app, "icon_path", None)
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
    # DPI 스케일 고려하여 최소 높이 설정 (125% DPI에서 버튼이 잘리지 않도록)
    dpi_scale = ui_settings.get("dpi_scale", 1.0)
    min_height = int(560 * max(1.0, dpi_scale))  # 하단 여백 최소화
    win_height = max(ui_settings["window_height"], min_height)

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

    style = ttk.Style(win)
    style.configure("TCombobox", font=("맑은 고딕", ui_settings["font_size"]))
    style.configure("Treeview", font=("맑은 고딕", ui_settings["font_size"]), rowheight=int(ui_settings["font_size"] * 2.2))
    style.configure("Treeview.Heading", font=("맑은 고딕", ui_settings["font_size"], "bold"))
    win.option_add("*TCombobox*Listbox.font", ("맑은 고딕", ui_settings["font_size"]))

    main = tk.Frame(win, padx=ui_settings["padding"], pady=ui_settings["padding"] - 4)
    main.pack(fill="both", expand=True)

    info_frame = tk.LabelFrame(
        main,
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

    app_frame = tk.LabelFrame(
        main,
        text="설정",
        font=("맑은 고딕", ui_settings["font_size_bold"], "bold"),
        padx=12,
        pady=10,
    )
    app_frame.pack(fill="x", pady=(0, 16))

    drawing_column = tk.StringVar(value=getattr(config, "drawing_column", "도번/규격"))
    category_column = tk.StringVar(value=getattr(config, "category_column", "제조사/가공분류"))
    excel_sheet_name = tk.StringVar(value=getattr(config, "excel_sheet_name", "구매요청"))
    output_folder = tk.StringVar(value=getattr(config, "output_folder", ""))

    info_box = tk.Frame(app_frame, bg="#e3f2fd", relief="solid", borderwidth=1)
    info_box.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, 10), padx=2)
    info_label = tk.Label(
        info_box,
        text="💡 엑셀 파일에 아래 컬럼명이 있어야 합니다.\n   컬럼명이 다르면 설정에서 수정 후 작업하세요.",
        font=("맑은 고딕", ui_settings["font_size"]),
        bg="#e3f2fd",
        fg="#1565c0",
        justify="left",
        anchor="w",
    )
    info_label.pack(padx=8, pady=6)

    lbl_drawing = tk.Label(app_frame, text="도번 컬럼명", font=("맑은 고딕", ui_settings["font_size"]))
    lbl_drawing.grid(row=1, column=0, sticky="w", pady=4)
    ent_drawing = tk.Entry(app_frame, textvariable=drawing_column, font=("맑은 고딕", ui_settings["font_size"]))
    ent_drawing.grid(row=1, column=1, sticky="ew", padx=(8, 6))
    _bind_tooltip(lbl_drawing, "엑셀에서 도면 번호/규격을 담은 컬럼명입니다.")
    _bind_tooltip(ent_drawing, "예: 도번, 도번/규격 등 실제 컬럼명을 입력하세요.")

    lbl_category = tk.Label(app_frame, text="가공분류 컬럼명", font=("맑은 고딕", ui_settings["font_size"]))
    lbl_category.grid(row=2, column=0, sticky="w", pady=4)
    ent_category = tk.Entry(app_frame, textvariable=category_column, font=("맑은 고딕", ui_settings["font_size"]))
    ent_category.grid(row=2, column=1, sticky="ew", padx=(8, 6))
    _bind_tooltip(lbl_category, "엑셀에서 제조사/가공 분류 정보를 담은 컬럼명입니다.")
    _bind_tooltip(ent_category, "예: 제조사, 가공분류 등 실제 컬럼명을 입력하세요.")

    lbl_sheet = tk.Label(app_frame, text="엑셀 시트명", font=("맑은 고딕", ui_settings["font_size"]))
    lbl_sheet.grid(row=3, column=0, sticky="w", pady=4)
    ent_sheet = tk.Entry(app_frame, textvariable=excel_sheet_name, font=("맑은 고딕", ui_settings["font_size"]))
    ent_sheet.grid(row=3, column=1, sticky="ew", padx=(8, 6))
    _bind_tooltip(lbl_sheet, "분류 대상 데이터가 있는 시트 이름입니다.")
    _bind_tooltip(ent_sheet, "예: 구매요청, Sheet1 등 실제 시트명을 입력하세요.")

    lbl_output = tk.Label(app_frame, text="결과 저장 경로", font=("맑은 고딕", ui_settings["font_size"]))
    lbl_output.grid(row=4, column=0, sticky="w", pady=4)
    out_entry = tk.Entry(app_frame, textvariable=output_folder, font=("맑은 고딕", ui_settings["font_size"]))
    out_entry.grid(row=4, column=1, sticky="ew", padx=(8, 6))
    _bind_tooltip(lbl_output, "분류 결과 파일을 저장할 폴더 위치입니다.")
    _bind_tooltip(out_entry, "폴더를 직접 입력하거나 ‘찾기’ 버튼으로 선택하세요.")

    lbl_mode = tk.Label(app_frame, text="파일 작업 모드", font=("맑은 고딕", ui_settings["font_size"]))
    lbl_mode.grid(row=5, column=0, sticky="ew", pady=4)
    current_mode_en = getattr(config, "file_operation_mode", "copy")
    current_mode_ko = "복사" if current_mode_en == "copy" else "이동"
    file_operation_mode_var = tk.StringVar(value=current_mode_ko)
    operation_mode_combo = ttk.Combobox(
        app_frame,
        textvariable=file_operation_mode_var,
        values=["복사", "이동"],
        state="readonly",
        width=12,
    )
    operation_mode_combo.grid(row=5, column=1, sticky="w", padx=(8, 6), pady=4)

    _bind_tooltip(lbl_mode, "분류 결과 처리 방식입니다: 원본 유지(복사) 또는 이동")
    _bind_tooltip(operation_mode_combo, "복사: 원본 유지 / 이동: 원본을 지정 폴더로 이동")

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
        sel = filedialog.askdirectory(initialdir=cur, title="결과 저장 경로 선택", parent=win)

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
        app_frame,
        text="찾기",
        command=browse_out,
        width=8,
        font=("맑은 고딕", ui_settings["font_size"]),
    ).grid(row=4, column=2, pady=4)
    app_frame.columnconfigure(1, weight=1)

    btn_frame = tk.Frame(main)
    btn_frame.pack(side="bottom", pady=(20, 15), fill="x")
    button_container = tk.Frame(btn_frame)
    button_container.pack(expand=True)

    def save():
        mode_ko = file_operation_mode_var.get()
        file_op_mode = "copy" if mode_ko == "복사" else "move"
        settings_update = {
            "drawing_column": drawing_column.get().strip() or "도번/규격",
            "category_column": category_column.get().strip() or "제조사/가공분류",
            "excel_sheet_name": excel_sheet_name.get().strip() or "구매요청",
            "output_folder": output_folder.get().strip(),
            "file_operation_mode": file_op_mode,
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


if __name__ == "__main__":
    # Simple manual test
    from app_setting_data import get_config

    rt = tk.Tk()
    rt.withdraw()
    cfg = get_config()
    create_settings_window(rt, cfg)
    rt.destroy()  # 설정창이 닫히면 루트도 종료
