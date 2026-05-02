# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk, messagebox
import json

from app_setting_data import get_config, get_config_path

# Adaptive UI 통합 모듈
try:
    from wf_ui_adaptive import get_adaptive_ui_settings, apply_global_fonts
except ImportError:
    try:
        import sys
        import os
        _common_dir = os.path.join(os.path.dirname(__file__), "..", "..", "10.common")
        if _common_dir not in sys.path:
            sys.path.insert(0, _common_dir)
        from wf_ui_adaptive import get_adaptive_ui_settings, apply_global_fonts
    except ImportError:
        def get_adaptive_ui_settings(window_type="main", saved_ui=None):
            return {"window_width": 350, "window_height": 200, "font_size": 9, "padding": 10}
        def apply_global_fonts(root, ui): pass


def create_settings_window(master, app_instance):
    """
    Creates the settings window.
    """
    # DPI 기반 적응형 UI 설정 (서브 창용)
    ui = get_adaptive_ui_settings(window_type="sub")

    settings_window = tk.Toplevel(master)
    settings_window.withdraw()  # 깜빡임 방지: geometry 설정 전까지 숨김

    # 버전 정보 가져오기 (app_instance에서 또는 ui_main 모듈에서)
    version_str = getattr(app_instance, 'APP_VERSION_FULL', None)
    if not version_str:
        try:
            import ui_main
            version_str = getattr(ui_main, 'APP_VERSION_FULL', 'v0.7.0')
        except Exception:
            version_str = 'v0.7.0'

    settings_window.title(f"속성 리셋 {version_str} - 설정")

    # 앱별 아이콘 적용 (app_instance에서 icon_path 가져오기)
    try:
        icon_path = getattr(app_instance, "icon_path", None)
        if icon_path:
            settings_window.iconbitmap(str(icon_path))
    except Exception:
        pass

    # config 먼저 가져오기 (topmost 확인에 필요)
    config = app_instance.config
    font = ("맑은 고딕", ui["font_size"])

    # 설정 창은 간단하므로 서브 창 크기의 축소 버전 사용
    win_width = min(ui["window_width"], 400)
    win_height = min(ui["window_height"], 250)
    settings_window.transient(master)
    settings_window.grab_set()
    # 메인 창이 topmost이면 설정 창도 topmost로 설정 (창 순서 유지)
    if config.ui_config.topmost:
        settings_window.wm_attributes("-topmost", 1)

    # 부모 창 중앙에 배치
    settings_window.update_idletasks()
    parent_x = master.winfo_rootx()
    parent_y = master.winfo_rooty()
    parent_w = master.winfo_width()
    parent_h = master.winfo_height()
    x = parent_x + (parent_w - win_width) // 2
    y = parent_y + (parent_h - win_height) // 2
    settings_window.geometry(f"{win_width}x{win_height}+{x}+{y}")
    settings_window.deiconify()  # 위치 설정 완료 후 표시

    # --- UI Elements ---
    main_frame = ttk.Frame(settings_window, padding=str(ui["padding"]))
    main_frame.pack(fill="both", expand=True)

    # Topmost option
    topmost_var = tk.BooleanVar(value=config.ui_config.topmost)
    topmost_check = tk.Checkbutton(
        main_frame, text="프로그램을 항상 위에 표시",
        variable=topmost_var, font=font
    )
    topmost_check.pack(anchor="w", pady=5)

    # --- Save and Close Buttons ---
    button_frame = ttk.Frame(main_frame)
    button_frame.pack(side="bottom", fill="x", pady=(10, 0))

    def save_settings():
        try:
            # Update config object
            config.ui_config.topmost = topmost_var.get()

            # Read the whole JSON, update it, and write it back
            config_path = get_config_path()
            with open(config_path, 'r', encoding='utf-8') as f:
                settings_data = json.load(f)

            settings_data['ui_config']['topmost'] = topmost_var.get()

            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(settings_data, f, indent=2)

            # Apply settings to the main app instance
            app_instance.master.wm_attributes("-topmost", config.ui_config.topmost)

            messagebox.showinfo("저장 완료", "설정이 저장되었습니다.", parent=settings_window)
            settings_window.destroy()

        except Exception as e:
            messagebox.showerror("저장 실패", f"설정을 저장하는 중 오류가 발생했습니다:\n{e}", parent=settings_window)

    save_button = tk.Button(button_frame, text="저장", command=save_settings, font=font, width=8)
    save_button.pack(side="right")

    close_button = tk.Button(button_frame, text="취소", command=settings_window.destroy, font=font, width=8)
    close_button.pack(side="right", padx=(0, 5))

    # Alt+G: geometry 저장 (디버깅용)
    def _on_debug_geometry_capture(_event=None):
        try:
            geo = settings_window.geometry()
            msg = f"[DEBUG] SettingsWindow geometry: {geo}"
            print(msg)
            # settings.json에 저장 시도
            ok = False
            if config and hasattr(config, "update_settings_window_geometry"):
                ok = config.update_settings_window_geometry(geo)
            # 토스트 메시지 표시
            toast = tk.Toplevel(settings_window)
            toast.overrideredirect(True)
            toast.attributes("-topmost", True)
            toast_msg = f"geometry 저장됨: {geo}" if ok else f"geometry: {geo}"
            lbl = tk.Label(
                toast, text=toast_msg, bg="#333333", fg="white",
                font=("맑은 고딕", 9), padx=10, pady=5
            )
            lbl.pack()
            toast.update_idletasks()
            x = settings_window.winfo_x() + (settings_window.winfo_width() - toast.winfo_reqwidth()) // 2
            y = settings_window.winfo_y() + settings_window.winfo_height() - toast.winfo_reqheight() - 10
            toast.geometry(f"+{x}+{y}")
            toast.after(1400, toast.destroy)
        except Exception:
            pass

    settings_window.bind_all("<Alt-g>", _on_debug_geometry_capture)

