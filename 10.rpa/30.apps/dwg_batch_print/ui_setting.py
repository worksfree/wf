# -*- coding: utf-8 -*-
"""
DWG Batch Print Settings Dialog
DWG 일괄 인쇄 설정 창
"""

import os
import sys

# Windows DPI awareness 설정 (스케일링 통일)
if sys.platform == 'win32':
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass  # Already set or not supported

import json
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path

# Adaptive UI 통합 모듈
try:
    from wf_ui_adaptive import get_adaptive_ui_settings, apply_global_fonts
except ImportError:
    _common_dir = os.path.join(os.path.dirname(__file__), "..", "..", "10.common")
    if _common_dir not in sys.path:
        sys.path.insert(0, _common_dir)
    from wf_ui_adaptive import get_adaptive_ui_settings, apply_global_fonts


class Tooltip:
    """간단한 툴팁 구현: 위젯에 마우스 오버 시 설명 표시"""

    def __init__(self, widget, text: str):
        self.widget = widget
        self.text = text
        self.tipwindow = None
        self._after_show = None
        self._after_hide = None
        # 지연 표시/숨김으로 깜빡임 최소화
        self.widget.bind("<Enter>", self._schedule_show)
        self.widget.bind("<Leave>", self._schedule_hide)

    def _schedule_show(self, event=None):
        if self._after_hide:
            self.widget.after_cancel(self._after_hide)
            self._after_hide = None
        if self._after_show:
            return
        self._after_show = self.widget.after(250, self._show)

    def _schedule_hide(self, event=None):
        if self._after_show:
            self.widget.after_cancel(self._after_show)
            self._after_show = None
        # 약간의 지연 후 숨김
        self._after_hide = self.widget.after(200, self._hide)

    def _show(self, event=None):
        if self.tipwindow or not self.text:
            return
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 10
        self.tipwindow = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        try:
            tw.wm_attributes("-topmost", True)
        except Exception:
            pass
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(
            tw,
            text=self.text,
            justify=tk.LEFT,
            background="#ffffe0",
            relief=tk.SOLID,
            borderwidth=1,
            padx=8,
            pady=4,
        )
        label.pack()

    def _hide(self, event=None):
        if self.tipwindow:
            self.tipwindow.destroy()
            self.tipwindow = None
        if self._after_hide:
            self.widget.after_cancel(self._after_hide)
            self._after_hide = None


def attach_tooltip(widget, text: str):
    if text:
        Tooltip(widget, text)
    return widget


def _get_ui_scale() -> float:
    """settings.json에서 ui_scale 값 읽기"""
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
    
    for k in ("window_width", "window_height", "font_size", "font_size_bold", "font_size_title", "padding"):
        if k in settings and isinstance(settings[k], (int, float)):
            settings[k] = _s(settings[k])
    return settings


def _get_saved_ui_config() -> dict:
    """앱 설정에서 저장된 UI 설정 로드"""
    try:
        from app_setting_data import get_config
        cfg = get_config()
        return getattr(cfg, "ui_config", {}) or {}
    except Exception:
        return {}


class SettingsDialog:
    """설정 대화상자"""

    def __init__(self, parent, config, logger):
        self.parent = parent
        self.config = config
        self.logger = logger

        # 부모 앱에서 버전 정보 가져오기
        try:
            from ui_main import APP_VERSION_FULL
            version_str = APP_VERSION_FULL
        except:
            version_str = "v0.7"

        self.top = tk.Toplevel(parent)
        self.top.withdraw()  # 깜빡임 방지: geometry 설정 전까지 숨김
        self.top.title(f"DWG Batch Print 알파 {version_str} - 설정")

        # 앱별 아이콘 적용 (parent_app에서 icon_path 가져오기)
        try:
            icon_path = getattr(self.parent_app, "icon_path", None)
            if icon_path:
                self.top.iconbitmap(str(icon_path))
        except Exception:
            pass

        self.top.transient(parent)
        self.top.grab_set()
        # 메인 창이 topmost이면 설정 창도 topmost로 설정 (창 순서 유지)
        if parent.attributes("-topmost"):
            self.top.wm_attributes("-topmost", 1)

        saved_ui = _get_saved_ui_config()
        ui_settings = get_adaptive_ui_settings(window_type="sub", saved_ui=saved_ui)
        apply_global_fonts(self.top, ui_settings)

        base_font = ("맑은 고딕", ui_settings["font_size"])
        title_font = ("맑은 고딕", ui_settings["font_size_title"], "bold")
        style = ttk.Style(self.top)
        for name in (
            "TLabel",
            "TButton",
            "TCheckbutton",
            "TRadiobutton",
            "TEntry",
            "TSpinbox",
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

        # 센터링 + 충분한 기본 크기 (콘텐츠가 잘리지 않도록 최소 크기 보장)
        win_width = max(ui_settings["window_width"], 700)
        # DBP 설정창 최적 높이: 500px (항목 수에 맞춤)
        win_height = max(ui_settings["window_height"], 500)

        # Center over parent if available; fallback to screen center
        x = y = None
        parent = self.parent.master if hasattr(self.parent, "master") else None
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

        self.top.geometry(f"{win_width}x{win_height}+{x}+{y}")
        self.top.deiconify()  # 모든 설정 완료 후 표시

        # UI
        self._build_ui()

    def _build_ui(self):
        main_frame = ttk.Frame(self.top, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 스크롤 가능한 컨테이너
        canvas = tk.Canvas(main_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # 그리드 컬럼 비율 설정 (라벨 / 값)
        scrollable_frame.columnconfigure(0, weight=0)
        scrollable_frame.columnconfigure(1, weight=1)

        # ===== 일반 설정 =====
        row = 0

        section_label = ttk.Label(scrollable_frame, text="일반 설정", style="Section.TLabel")
        section_label.grid(row=row, column=0, sticky=tk.W, pady=(0, 10))
        row += 1

        # eDrawings 경로
        lbl_ed = ttk.Label(scrollable_frame, text="eDrawings 경로:")
        lbl_ed.grid(row=row, column=0, sticky=tk.W, pady=(5, 0), padx=(0, 8))
        attach_tooltip(lbl_ed, "eDrawings 실행 파일 경로를 설정합니다.")
        row += 1

        # 라벨 아래로 입력/버튼 배치 (전체 폭)
        path_frame = ttk.Frame(scrollable_frame)
        path_frame.grid(row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(2, 10))
        scrollable_frame.columnconfigure(0, weight=0)
        scrollable_frame.columnconfigure(1, weight=1)

        self.edrawings_path_var = tk.StringVar(value=getattr(self.config, 'edrawings_path', ''))
        path_btn = ttk.Button(path_frame, text="폴더 선택", command=self._browse_edrawings)
        path_btn.pack(side=tk.LEFT)
        path_entry = ttk.Entry(path_frame, textvariable=self.edrawings_path_var, width=50)
        path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(8, 0))
        row += 1

        # 상단 고정
        lbl_top = ttk.Label(scrollable_frame, text="창을 항상 위에 표시")
        lbl_top.grid(row=row, column=0, sticky=tk.W, pady=10, padx=(0, 8))
        attach_tooltip(lbl_top, "창을 다른 창 위에 항상 표시합니다.")
        self.topmost_var = tk.BooleanVar(value=getattr(self.config, 'topmost', False))
        topmost_check = ttk.Checkbutton(scrollable_frame, variable=self.topmost_var)
        topmost_check.grid(row=row, column=1, sticky=tk.W, pady=10)
        row += 1

        # 구분선
        ttk.Separator(scrollable_frame, orient=tk.HORIZONTAL).grid(row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=15)
        row += 1

        # ===== 인쇄 설정 =====
        section_label2 = ttk.Label(scrollable_frame, text="인쇄 설정", style="Section.TLabel")
        section_label2.grid(row=row, column=0, sticky=tk.W, pady=(0, 10))
        row += 1

        # 재시작 주기
        lbl_rc = ttk.Label(scrollable_frame, text="재시작 주기 (파일 개수):")
        lbl_rc.grid(row=row, column=0, sticky=tk.W, pady=5, padx=(0, 8))
        attach_tooltip(lbl_rc, "일정 개수의 파일을 인쇄한 후 eDrawings를 재시작합니다.")
        self.restart_count_var = tk.IntVar(value=getattr(self.config, 'restart_count', 30))
        restart_spin = ttk.Spinbox(scrollable_frame, from_=1, to=1000, textvariable=self.restart_count_var, width=15)
        restart_spin.grid(row=row, column=1, sticky=tk.W, pady=2)
        row += 1

        # 대기 시간
        lbl_wt = ttk.Label(scrollable_frame, text="인쇄 대기 시간 (초):")
        lbl_wt.grid(row=row, column=0, sticky=tk.W, pady=5, padx=(0, 8))
        attach_tooltip(lbl_wt, "인쇄 대화상자를 기다리는 최대 시간입니다.")
        self.wait_timeout_var = tk.IntVar(value=getattr(self.config, 'wait_timeout', 300))
        wait_spin = ttk.Spinbox(scrollable_frame, from_=10, to=3600, textvariable=self.wait_timeout_var, width=15)
        wait_spin.grid(row=row, column=1, sticky=tk.W, pady=2)
        row += 1

        # 재시작 대기
        lbl_rs = ttk.Label(scrollable_frame, text="재시작 대기 시간 (초):")
        lbl_rs.grid(row=row, column=0, sticky=tk.W, pady=5, padx=(0, 8))
        attach_tooltip(lbl_rs, "eDrawings 재시작 후 대기 시간입니다.")
        self.restart_sleep_var = tk.IntVar(value=getattr(self.config, 'restart_sleep', 5))
        restart_sleep_spin = ttk.Spinbox(scrollable_frame, from_=1, to=60, textvariable=self.restart_sleep_var, width=15)
        restart_sleep_spin.grid(row=row, column=1, sticky=tk.W, pady=2)
        row += 1

        # 구분선
        ttk.Separator(scrollable_frame, orient=tk.HORIZONTAL).grid(row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=15)
        row += 1

        # (크레딧 설정 제거)

        # 버튼 (가운데 정렬: 저장 좌측, 취소 우측)
        btn_frame = ttk.Frame(self.top, padding="10")
        btn_frame.pack(fill=tk.X, side=tk.BOTTOM)
        btn_frame.columnconfigure(0, weight=1)
        btn_frame.columnconfigure(1, weight=0)
        btn_frame.columnconfigure(2, weight=0)
        btn_frame.columnconfigure(3, weight=1)

        save_btn = ttk.Button(btn_frame, text="저장", command=self.on_save, width=10)
        save_btn.grid(row=0, column=1, padx=8, pady=5)

        cancel_btn = ttk.Button(btn_frame, text="취소", command=self.on_cancel, width=10)
        cancel_btn.grid(row=0, column=2, padx=8, pady=5)

        # 마우스 휠 스크롤
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        # ESC
        self.top.bind('<Escape>', lambda e: self.on_cancel())

        # Alt+G: geometry 저장 (디버깅용)
        self.top.bind_all("<Alt-g>", self._on_debug_geometry_capture)

        # 마우스 휠 스크롤
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

    def _browse_edrawings(self):
        """eDrawings 찾아보기"""
        initial_dir = os.path.dirname(self.edrawings_path_var.get()) if self.edrawings_path_var.get() else "C:\\Program Files"
        
        filename = filedialog.askopenfilename(
            title="eDrawings 실행 파일 선택",
            initialdir=initial_dir,
            filetypes=[("실행 파일", "*.exe"), ("모든 파일", "*.*")]
        )
        if filename:
            self.edrawings_path_var.set(filename)

    def on_save(self):
        """저장"""
        try:
            # 검증
            edrawings_path = self.edrawings_path_var.get().strip()
            if edrawings_path and not os.path.exists(edrawings_path):
                messagebox.showerror("오류", "유효한 eDrawings 경로를 입력해주세요.")
                return

            restart_count = self.restart_count_var.get()
            if restart_count < 1:
                messagebox.showerror("오류", "재시작 주기는 1 이상이어야 합니다.")
                return

            wait_timeout = self.wait_timeout_var.get()
            if wait_timeout < 10:
                messagebox.showerror("오류", "대기 시간은 10초 이상이어야 합니다.")
                return

            # 설정 저장
            self.config.edrawings_path = edrawings_path
            self.config.restart_count = restart_count
            self.config.wait_timeout = wait_timeout
            self.config.restart_sleep = self.restart_sleep_var.get()
            self.config.topmost = self.topmost_var.get()
            # (크레딧 설정 제거: check_shortage_stop 저장 생략)

            self.config.save_settings()

            self.logger.info("설정 저장 완료")
            messagebox.showinfo("완료", "설정이 저장되었습니다.\n일부 설정은 재시작 후 적용됩니다.")
            self.top.destroy()

        except Exception as e:
            self.logger.error(f"설정 저장 오류: {e}")
            messagebox.showerror("오류", f"설정 저장 중 오류 발생:\n{e}")

    def on_cancel(self):
        """취소"""
        self.top.destroy()

    def _on_debug_geometry_capture(self, _event=None):
        """Alt+G: 현재 geometry를 로그에 출력하고 settings.json에 저장"""
        if not self.top or not self.top.winfo_exists():
            return
        try:
            geo = self.top.geometry()
            msg = f"[DEBUG] SettingsDialog geometry: {geo}"
            print(msg)
            self.logger.info(msg)
            # settings.json에 저장
            ok = False
            if self.config and hasattr(self.config, "update_settings_window_geometry"):
                ok = self.config.update_settings_window_geometry(geo)
            # 토스트 메시지 표시
            if ok:
                self._show_geometry_toast(f"geometry 저장됨: {geo}")
            else:
                self._show_geometry_toast(f"geometry: {geo}")
        except Exception as e:
            self.logger.debug(f"Alt+G 실패: {e}")

    def _show_geometry_toast(self, message: str, duration_ms: int = 1400):
        """간단한 토스트 메시지 표시"""
        if not self.top or not self.top.winfo_exists():
            return
        try:
            toast = tk.Toplevel(self.top)
            toast.overrideredirect(True)
            toast.attributes("-topmost", True)
            lbl = tk.Label(
                toast, text=message, bg="#333333", fg="white",
                font=("맑은 고딕", 9), padx=10, pady=5
            )
            lbl.pack()
            toast.update_idletasks()
            x = self.top.winfo_x() + (self.top.winfo_width() - toast.winfo_reqwidth()) // 2
            y = self.top.winfo_y() + self.top.winfo_height() - toast.winfo_reqheight() - 10
            toast.geometry(f"+{x}+{y}")
            toast.after(duration_ms, toast.destroy)
        except Exception:
            pass


# ==================== 유틸리티 함수들 (bom_exporter에서 마이그레이션) ====================

def load_custom_settings():
    """통합 설정 파일 로드하는 유틸리티 함수 (settings.json)"""
    settings_file = Path.home() / ".wf_rpa" / "dwg_batch_print" / "settings.json"
    try:
        if settings_file.exists():
            with open(settings_file, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        print(f"설정 로드 실패: {e}")
    return None


def apply_custom_settings_to_config(config, custom_settings):
    """커스텀 설정을 기존 config 객체에 적용하는 유틸리티 함수"""
    if not custom_settings or not config:
        return

    try:
        # eDrawings 경로 설정
        if "edrawings_path" in custom_settings:
            config.edrawings_path = custom_settings["edrawings_path"]

        # 앱 설정
        if "app_config" in custom_settings:
            app_config = custom_settings["app_config"]
            if "restart_count" in app_config:
                config.restart_count = app_config["restart_count"]
            if "wait_timeout" in app_config:
                config.wait_timeout = app_config["wait_timeout"]
            if "restart_sleep" in app_config:
                config.restart_sleep = app_config["restart_sleep"]
            if "final_sleep" in app_config:
                config.final_sleep = app_config["final_sleep"]

        print("커스텀 설정이 config 객체에 적용되었습니다.")
    except Exception as e:
        print(f"커스텀 설정 적용 실패: {e}")


def create_settings_window(parent_app, hardware_info=None):
    """설정 창 생성 함수 (bom_exporter 호환성)"""
    # parent_app에서 config와 logger 가져오기
    config = getattr(parent_app, "config", None)
    logger = getattr(parent_app, "logger", None)
    
    if config is None or logger is None:
        # config나 logger가 없으면 기본값 사용
        from app_setting_data import get_config
        config = get_config()
        import logging
        logger = logging.getLogger("dwg_batch_print")
    
    # SettingsDialog 사용 (기존 구현)
    dialog = SettingsDialog(parent_app.master, config, logger)
    return dialog
