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
import pyautogui
import json
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


current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# 버전 정보 로드 (settings.json에서 직접 읽기)
def _load_version_from_settings():
    """settings.json에서 버전 정보 읽기 (소스 설정 버전을 폴백으로 사용)"""
    import json
    import sys
    from pathlib import Path

    default_full = "v0.7.0.0"

    def _ensure_prefix(v: str) -> str:
        v = (v or "").strip()
        if not v:
            return default_full
        return v if v.startswith("v") else "v" + v

    source_full = default_full
    try:
        src_settings = Path(__file__).parent / "config" / "dwg_classifier" / "settings.json"
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
            settings_file = base_path / ".wf_rpa" / "dwg_classifier" / "settings.json"
            if not settings_file.exists():
                settings_file = Path.home() / ".wf_rpa" / "dwg_classifier" / "settings.json"
        else:
            settings_file = Path(__file__).parent / "config" / "dwg_classifier" / "settings.json"

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
APP_VERSION_DISPLAY = "알파 v" + ".".join(APP_VERSION_FULL.lstrip("v").split(".")[:2])


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

    # geometry 문자열(예: 580x320+990+480)에서 폭/높이 추출
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
        parsed_w = parsed_w if parsed_w is not None else None
        parsed_h = parsed_h if parsed_h is not None else None

    try:
        default_width = parsed_w if parsed_w is not None else saved_ui.get("window_width", 580)
        default_width = int(default_width)
    except Exception:
        default_width = 580

    try:
        default_height = parsed_h if parsed_h is not None else saved_ui.get("window_height", 320)
        default_height = int(default_height)
    except Exception:
        default_height = 320

    # 단일 base settings (DC는 2-input app이라 height 더 높음) - 모든 폰트 크기 통일
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
    _apply_global_fonts(parent, ui_settings)

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
    win.title(f"DWG Classifier 알파 {APP_VERSION_FULL} - 설정")

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

    log_level_default = "DEBUG"
    try:
        config_file = Path.home() / ".wf_rpa" / "wf_rpa_config.json"
        if config_file.exists():
            with open(config_file, "r", encoding="utf-8") as f:
                global_config = json.load(f)
                system_settings = global_config.get("system_settings", {})
                log_level_default = system_settings.get("log_level", "DEBUG")
    except Exception:
        pass

    log_level_frame = tk.Frame(app_frame)
    log_level_frame.grid(row=5, column=2, sticky="e", pady=4)
    lbl_log = tk.Label(log_level_frame, text="로그 레벨", font=("맑은 고딕", ui_settings["font_size"]))
    lbl_log.pack(side="left", padx=(0, 5))
    log_level_var = tk.StringVar(value=log_level_default)
    log_level_combo = ttk.Combobox(
        log_level_frame,
        textvariable=log_level_var,
        values=["DEBUG", "INFO", "WARNING", "ERROR"],
        state="readonly",
        width=8,
    )
    log_level_combo.pack(side="left")
    _bind_tooltip(lbl_mode, "분류 결과 처리 방식입니다: 원본 유지(복사) 또는 이동")
    _bind_tooltip(operation_mode_combo, "복사: 원본 유지 / 이동: 원본을 지정 폴더로 이동")
    _bind_tooltip(lbl_log, "로그 상세 정도를 선택합니다: DEBUG가 가장 자세합니다.")
    _bind_tooltip(log_level_combo, "DEBUG/INFO/WARNING/ERROR 중 선택하세요.")

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
                try:
                    config_file = Path.home() / ".wf_rpa" / "wf_rpa_config.json"
                    if config_file.exists():
                        with open(config_file, "r", encoding="utf-8") as f:
                            global_config = json.load(f)
                        if "system_settings" not in global_config:
                            global_config["system_settings"] = {}
                        global_config["system_settings"]["log_level"] = log_level_var.get()
                        with open(config_file, "w", encoding="utf-8") as f:
                            json.dump(global_config, f, ensure_ascii=False, indent=2)
                except Exception as e:
                    print(f"⚠️ 로그 레벨 저장 실패: {e}")
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
