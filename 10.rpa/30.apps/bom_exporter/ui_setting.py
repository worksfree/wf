# -*- coding: utf-8 -*-

import sys

# Windows DPI awareness 설정 (스케일링 통일)
if sys.platform == 'win32':
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass  # Already set or not supported

import json
import datetime
import tkinter as tk
import tkinter.ttk as ttk
import tkinter.messagebox
import pyautogui
import platform
from pathlib import Path

# 현재 스크립트의 디렉토리를 Python 경로에 추가
current_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(current_dir))

# 기존 utils 경로 추가 (원본 코드와 호환성 유지)
utils_path = current_dir.parent.parent / "10.common"
if utils_path.exists():
    sys.path.append(str(utils_path))

# 공용 설정 경로(소스 트리 기본)
SETTINGS_FILE_SOURCE = current_dir / "config" / "bom_exporter" / "settings.json"
GLOBAL_CONFIG_FILE_SOURCE = current_dir / "config" / "wf_rpa_config.json"


def _resolve_settings_file():
    try:
        cfg = get_config()
        run_mode = getattr(cfg, "run_mode", "release")
    except Exception:
        run_mode = "release"

    if run_mode == "release":
        return Path.home() / ".wf_rpa" / "bom_exporter" / "settings.json"
    return SETTINGS_FILE_SOURCE


def _resolve_global_config_file():
    try:
        cfg = get_config()
        run_mode = getattr(cfg, "run_mode", "release")
    except Exception:
        run_mode = "release"

    if run_mode == "release":
        return Path.home() / ".wf_rpa" / "wf_rpa_config.json"
    return GLOBAL_CONFIG_FILE_SOURCE


# 버전 정보 로드 (settings.json에서 직접 읽기)
def _load_version_from_settings():
    """settings.json에서 버전 정보 읽기 (없으면 소스 설정값으로 폴백)"""
    default_full = "v0.7.0.0"

    def _ensure_prefix(v: str) -> str:
        v = (v or "").strip()
        if not v:
            return default_full
        return v if v.startswith("v") else "v" + v

    # 소스 설정의 full_version을 우선 확보 (빌드 시점 기준 버전)
    source_full = default_full
    try:
        if SETTINGS_FILE_SOURCE.exists():
            with open(SETTINGS_FILE_SOURCE, "r", encoding="utf-8") as f:
                src_data = json.load(f)
            src_runtime_cfg = src_data.get("runtime_config", {}) or {}
            source_full = _ensure_prefix(src_runtime_cfg.get("full_version", default_full))
    except Exception:
        source_full = default_full

    # 런타임 설정 파일에서 읽기 (사용자/배포 설정 우선)
    try:
        settings_path = _resolve_settings_file()
        if settings_path.exists():
            with open(settings_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            runtime_config = data.get("runtime_config", {}) or {}
            runtime_full = runtime_config.get("full_version")
            if runtime_full:
                return _ensure_prefix(runtime_full)
    except Exception:
        pass

    # 런타임에 없으면 소스 설정의 full_version 사용
    return source_full

APP_VERSION_FULL = _load_version_from_settings()

from app_setting_data import get_config
import wf_hwinfo

try:
    from wf_settings_common import get_user_hardware_info, format_info_for_tree
except ImportError:  # 안전한 폴백 (빌드/경로 문제 시)

    def get_user_hardware_info():
        return {}

    def format_info_for_tree(_info):
        return {}


import logging

# 글로벌 로거 import
import wf_log as wflog


def _get_ui_scale() -> float:
    try:
        cfg = get_config()
        # app_setting_data.Config may expose attribute or dict
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
        "tree_rowheight",
        "padding",
    ):
        if k in settings and isinstance(settings[k], (int, float)):
            settings[k] = _s(settings[k])
    return settings


def _apply_global_fonts(root, ui: dict) -> None:
    """Force all Tk default fonts to unified sizes."""
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
    """화면 해상도에 따른 적응형 UI 설정 (설정 파일 ui_config 값을 우선 적용)"""
    screen_width, screen_height = pyautogui.size()

    # 해상도별 scale factor
    if screen_width >= 3840:  # UHD (4K)
        resolution_scale = 1.5
    elif screen_width >= 2560:  # QHD (1440p)
        resolution_scale = 1.2
    else:  # FHD (1080p)
        resolution_scale = 1.0

    # 저장된 ui_config를 불러와 base 값에 덮어씌움 (사용자 지정값은 스케일링 제외)
    saved_ui = {}
    try:
        cfg = get_config()
        saved_ui = getattr(cfg, "ui_config", {}) or getattr(cfg, "get", lambda *_: {})("ui_config", {})
    except Exception:
        saved_ui = {}

    try:
        default_width = int(saved_ui.get("window_width", 580))
    except Exception:
        default_width = 580

    try:
        default_height = int(saved_ui.get("window_height", 180))
    except Exception:
        default_height = 180

    base_settings = {
        "window_width": default_width,
        "window_height": default_height,
        "font_size": 14,
        "font_size_bold": 14,
        "font_size_title": 14,
        "tree_rowheight": 22,
        "padding": 12,
        "button_width": 10,
    }

    use_saved_width = isinstance(saved_ui, dict) and "window_width" in saved_ui
    use_saved_height = isinstance(saved_ui, dict) and "window_height" in saved_ui

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

    # 디버깅: 최종 값 확인
    try:
        import logging
        logger = logging.getLogger("bom_exporter")
        logger.debug(
            f"[FONT-DEBUG] base font_size: {base_settings['font_size']}, resolution_scale: {resolution_scale}, final font_size: {result.get('font_size', 'N/A')}, window_height: {result.get('window_height')}, saved_ui: {bool(saved_ui)}"
        )
    except Exception:
        pass
    return result


def center_window_on_screen(window, width, height):
    """창을 부모 중앙에 배치, 실패 시 화면 중앙"""
    x = y = None
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

    if x is None or y is None:
        try:
            screen_width, screen_height = pyautogui.size()
        except Exception:
            screen_width, screen_height = 1920, 1080
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2

    window.geometry(f"{width}x{height}+{x}+{y}")


class SettingsWindow:
    def __init__(self, parent_app, hardware_info=None):
        self.parent_app = parent_app
        self.hardware_info = hardware_info or self._get_hardware_info()

        # 글로벌 싱글톤 로거 초기화
        self.logger = wflog.get_app_logger("bom_exporter", console_level=logging.DEBUG)
        self.config = get_config()
        self.settings_win = None
        self.custom_settings = self._load_custom_settings()

    def _get_hardware_info(self):
        try:
            hw_info = wf_hwinfo.HardwareInfo()
            return {
                "CPU ID": hw_info.cpu_id,
                "메인보드 ID": hw_info.mainboard_id,
                "스토리지 ID": getattr(hw_info, "storage_id", ""),
                "하드웨어 지문": hw_info.fingerprint,
            }
        except Exception as e:
            return {"오류": "하드웨어 정보를 가져올 수 없습니다"}

    def _load_custom_settings(self):
        """통합 설정 파일 로드 (settings.json)"""
        try:
            settings_path = _resolve_settings_file()
            if settings_path.exists():
                with open(settings_path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            self.logger.error(f"설정 로드 실패: {e}")
        return None

    def _get_user_info_from_global_config(self):
        """전역 설정에서 사용자/하드웨어 정보 가져오기"""
        try:
            config_path = _resolve_global_config_file()
            if config_path.exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    global_config = json.load(f)
                    user_info = global_config.get("user_info", {})
                    return {
                        "email": user_info.get("user_email", ""),
                        "name": user_info.get("user_name", ""),
                        "phone": user_info.get("user_phone", ""),
                        "hardware_fingerprint": user_info.get("hardware_fingerprint", ""),
                        "cpu_id": user_info.get("cpu_id", ""),
                        "mainboard_id": user_info.get("mainboard_id", ""),
                        "storage_id": user_info.get("storage_id", ""),
                        "registration_date": user_info.get("registration_date", ""),
                    }
        except Exception as e:
            self.logger.error(f"전역 설정 읽기 실패: {e}")
        return {}

    def _populate_info_table(self):
        """공통 모듈을 통해 사용자/하드웨어 정보 테이블 채우기"""
        for item in self.info_tree.get_children():
            self.info_tree.delete(item)
        info = get_user_hardware_info()
        rows = format_info_for_tree(info)
        for label, value in rows.items():
            # 빈 값은 건너뛰기
            if value and str(value).strip():
                self.info_tree.insert("", "end", values=(label, value))

    def open_settings_window(self):
        """설정 창 열기"""
        if self.settings_win and self.settings_win.winfo_exists():
            self.settings_win.lift()
            return
        
        # 툴팁 헬퍼 함수
        def _bind_tooltip(widget, text):
            """위젯에 툴팁을 바인딩하는 헬퍼 함수"""
            def on_enter(event):
                tooltip = tk.Toplevel()
                tooltip.wm_overrideredirect(True)
                tooltip.wm_attributes("-topmost", 1)
                x = event.x_root + 15
                y = event.y_root + 10
                tooltip.wm_geometry(f"+{x}+{y}")
                label = tk.Label(tooltip, text=text, background="#ffffe0", relief="solid", borderwidth=1, padx=5, pady=3)
                label.pack()
                widget._tooltip = tooltip
            
            def on_leave(event):
                if hasattr(widget, '_tooltip'):
                    widget._tooltip.destroy()
                    del widget._tooltip
            
            widget.bind("<Enter>", on_enter)
            widget.bind("<Leave>", on_leave)

        # 부모 앱이 없거나 master가 없는 경우 독립 실행 모드
        parent_master = None
        if hasattr(self.parent_app, "master"):
            parent_master = self.parent_app.master

        # 적응형 UI 설정 가져오기
        ui_settings = get_adaptive_ui_settings()

        self.settings_win = tk.Toplevel(parent_master)
        # parent_app에서 버전 정보 가져오기 (ui_main.APP_VERSION_FULL)
        version_str = getattr(self.parent_app, 'APP_VERSION_FULL', APP_VERSION_FULL)
        self.settings_win.title(f"Bom Exporter 알파 {version_str} - 설정")
        self.settings_win.resizable(True, True)
        _apply_global_fonts(self.settings_win, ui_settings)
        # 설정창은 항상 기본값(비-최상위) 유지: 메인창만 설정에 따라 변경
        try:
            self.settings_win.wm_attributes("-topmost", 0)
        except Exception:
            pass

        if parent_master:
            self.settings_win.transient(parent_master)

        # ttk 스타일을 메인 UI 폰트에 맞춤
        base_font = ("맑은 고딕", ui_settings["font_size"])
        title_font = ("맑은 고딕", ui_settings["font_size_title"], "bold")
        style = ttk.Style(self.settings_win)
        for name in (
            "TLabel",
            "TButton",
            "TCheckbutton",
            "TRadiobutton",
            "TEntry",
            "TSpinbox",
            "TCombobox",
        ):
            try:
                style.configure(name, font=base_font)
            except Exception:
                pass
        try:
            style.configure("Heading.TLabel", font=title_font)
        except Exception:
            pass

        # 적응형 창 크기와 위치 설정 (설정창은 더 큰 기본값을 사용해 내용이 모두 보이도록 조정)
        win_width = max(ui_settings["window_width"], 600)
        # Increased default height so all sections fit without clipping
        win_height = max(ui_settings["window_height"], 580)
        center_window_on_screen(self.settings_win, win_width, win_height)

        # ⚠️ 중요: 모달 창으로 설정 (리팩토링 시에도 유지할 것!)
        # 이 설정은 사용자 경험을 위해 반드시 유지되어야 합니다.
        if parent_master:
            self.settings_win.transient(parent_master)
        self.settings_win.grab_set()  # 항상 모달로 설정 - 절대 제거하지 말 것
        self.settings_win.focus_set()  # 포커스 설정

        # 메인 프레임 생성 (적응형 패딩)
        main_frame = tk.Frame(
            self.settings_win, padx=ui_settings["padding"], pady=ui_settings["padding"] // 2
        )
        main_frame.pack(fill="both", expand=True)

        # 사용자 및 하드웨어 정보 섹션 (적응형 폰트)
        user_info_frame = tk.LabelFrame(
            main_frame,
            text="사용자 및 하드웨어 정보",
            font=("맑은 고딕", ui_settings["font_size_bold"], "bold"),
            padx=ui_settings["padding"],
            pady=ui_settings["padding"],
        )
        user_info_frame.pack(fill="x", pady=(0, 20))

        # TreeView 프레임 생성 (스크롤바 포함)
        tree_frame = tk.Frame(user_info_frame)
        tree_frame.pack(fill="x", pady=(5, 0))

        # TreeView 생성 (적응형 행 높이)
        style = ttk.Style()
        # 기본 Treeview 스타일을 복사해서 새 스타일 생성
        style.layout("Custom.Treeview", style.layout("Treeview"))
        style.configure(
            "Custom.Treeview",
            rowheight=ui_settings.get("tree_rowheight", 24),
            font=("맑은 고딕", ui_settings["font_size"]),
        )
        # 헤더 스타일은 기본값 유지 (최적화 모드)

        self.info_tree = ttk.Treeview(
            tree_frame, height=6, show="headings", style="Custom.Treeview"
        )

        # 스크롤바 추가
        tree_scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.info_tree.yview)
        self.info_tree.configure(yscrollcommand=tree_scrollbar.set)

        # TreeView와 스크롤바 배치
        self.info_tree.pack(side="left", fill="both", expand=True)
        tree_scrollbar.pack(side="right", fill="y")

        # TreeView 컬럼 설정 (폭 조정)
        self.info_tree["columns"] = ("항목", "정보")
        self.info_tree.column("항목", width=140, minwidth=120, anchor="w")
        self.info_tree.column("정보", width=350, minwidth=250, anchor="w")

        # TreeView 헤더 설정 (폰트 크기 조정)
        self.info_tree.heading("항목", text="항목", anchor="w")
        self.info_tree.heading("정보", text="정보", anchor="w")

        # 사용자 정보 테이블 생성
        self._populate_info_table()

        # # 경로 섹션
        # path_frame = tk.LabelFrame(main_frame, text='경로', font=('맑은 고딕', 10, 'bold'), padx=10, pady=10)
        # path_frame.pack(fill='x', pady=(0, 15))

        # # 실행 앱 경로
        # tk.Label(path_frame, text='실행 앱 경로').grid(row=0, column=0, sticky='w', pady=(0, 10))
        # default_path = self.config.program_path if self.config else 'C:\\Program Files\\SOLIDWORKS Corp\\SOLIDWORKS\\SLDWORKS.exe'
        # self.app_path_var = tk.StringVar(value=default_path)
        # app_path_entry = tk.Entry(path_frame, textvariable=self.app_path_var, width=35)
        # app_path_entry.grid(row=0, column=1, sticky='ew', padx=(10, 5), pady=(0, 10))

        # browse_app_btn = tk.Button(path_frame, text='선택', command=self.browse_app_path, width=8)
        # browse_app_btn.grid(row=0, column=2, pady=(0, 10))

        # # 결과 저장 경로
        # tk.Label(path_frame, text='결과 저장 경로').grid(row=1, column=0, sticky='w')
        # default_result_path = getattr(self.config, 'result_path', 'D:\\#design_folder\\#asm01\\bom')
        # self.result_path_var = tk.StringVar(value=default_result_path)
        # result_path_entry = tk.Entry(path_frame, textvariable=self.result_path_var, width=35)
        # result_path_entry.grid(row=1, column=1, sticky='ew', padx=(10, 5))

        # browse_result_btn = tk.Button(path_frame, text='선택', command=self.browse_result_path, width=8)
        # browse_result_btn.grid(row=1, column=2)

        # path_frame.columnconfigure(1, weight=1)

        # 설정 섹션 (적응형 레이아웃)
        settings_frame = tk.LabelFrame(
            main_frame,
            text="설정",
            font=("맑은 고딕", ui_settings["font_size_bold"], "bold"),
            padx=ui_settings["padding"],
            pady=ui_settings["padding"],
        )
        settings_frame.pack(fill="x", pady=(0, 20))

        # 실행 앱 경로 (적응형 버튼과 엔트리)
        path_row_frame = tk.Frame(settings_frame)
        path_row_frame.pack(fill="x", pady=(0, 15))

        browse_app_btn = tk.Button(
            path_row_frame,
            text="앱 선택",
            command=self.browse_app_path,
            width=ui_settings["button_width"],
            font=("맑은 고딕", ui_settings["font_size"]),
        )
        browse_app_btn.pack(side="left", padx=(0, 10))

        # 커스텀 설정이 있으면 우선 사용
        default_path = "C:\\Program Files\\SOLIDWORKS Corp\\SOLIDWORKS\\SLDWORKS.exe"
        if self.custom_settings and "solidworks" in self.custom_settings:
            default_path = self.custom_settings["solidworks"].get("program_path", default_path)
        elif self.config:
            default_path = self.config.program_path
        self.app_path_var = tk.StringVar(value=default_path)

        app_path_entry = tk.Entry(
            path_row_frame,
            textvariable=self.app_path_var,
            font=("맑은 고딕", ui_settings["font_size"]),
        )
        app_path_entry.pack(side="left", fill="x", expand=True)
        _bind_tooltip(app_path_entry, "SolidWorks 실행 파일 경로 (SLDWORKS.exe)")

        # 첫 번째 줄: 최상위 고정 + 속도 설정
        row1_frame = tk.Frame(settings_frame)
        row1_frame.pack(fill="x", pady=(0, 10))

        # 화면 최상위 고정 체크박스 (적응형 폰트)
        topmost_default = False
        if self.custom_settings and "runtime_config" in self.custom_settings:
            topmost_default = self.custom_settings["runtime_config"].get("topmost", False)
        else:
            topmost_default = getattr(self.config, "topmost", False)
        self.topmost_var = tk.BooleanVar(value=topmost_default)
        topmost_check = tk.Checkbutton(
            row1_frame,
            text="최상위 고정",
            variable=self.topmost_var,
            font=("맑은 고딕", ui_settings["font_size"]),
            # 저장 버튼 클릭 시에만 적용되도록 즉시 적용 콜백 제거
        )
        topmost_check.pack(side="left")
        _bind_tooltip(topmost_check, "앱 창을 항상 다른 창 위에 표시")

        # 진행 속도 설정 (적응형 폰트)
        speed_frame = tk.Frame(row1_frame)
        speed_frame.pack(side="right")
        speed_label = tk.Label(speed_frame, text="속도", font=("맑은 고딕", ui_settings["font_size"]))
        speed_label.pack(side="left", padx=(0, 5))
        _bind_tooltip(speed_label, "작업 진행 속도 (slow: 안정, fast: 빠름)")
        speed_default = "normal"
        if self.custom_settings and "runtime_config" in self.custom_settings:
            speed_default = self.custom_settings["runtime_config"].get("speed_mode", "normal")
        else:
            speed_default = getattr(self.config, "speed_mode", "normal")
        self.speed_var = tk.StringVar(value=speed_default)
        speed_combo = ttk.Combobox(
            speed_frame,
            textvariable=self.speed_var,
            values=["slow", "normal", "fast"],
            state="readonly",
            width=12,
        )
        speed_combo.pack(side="left")

        # 두 번째 줄: 재시작 여부 + 재시작 카운트
        row2_frame = tk.Frame(settings_frame)
        row2_frame.pack(fill="x", pady=(0, 10))

        # 재시작 여부 체크박스 (왼쪽)
        auto_restart_default = True
        if self.custom_settings and "runtime_config" in self.custom_settings:
            auto_restart_default = self.custom_settings["runtime_config"].get("auto_restart", True)
        else:
            auto_restart_default = getattr(self.config, "auto_restart", True)
        self.restart_var = tk.BooleanVar(value=auto_restart_default)
        restart_check = tk.Checkbutton(
            row2_frame,
            text="재시작 여부",
            variable=self.restart_var,
            font=("맑은 고딕", ui_settings["font_size"]),
        )
        _bind_tooltip(restart_check, "SolidWorks를 주기적으로 재시작하여 안정성 향상")
        restart_check.pack(side="left")

        # 재시작 카운트 설정 (오른쪽)
        restart_frame = tk.Frame(row2_frame)
        restart_frame.pack(side="right")
        restart_label = tk.Label(
            restart_frame, text="재시작", font=("맑은 고딕", ui_settings["font_size"])
        )
        restart_label.pack(side="left", padx=(0, 5))
        _bind_tooltip(restart_label, "몇 개 파일 처리 후 재시작할지 설정 (기본 20개)")
        restart_default = 20
        if self.custom_settings and "runtime_config" in self.custom_settings:
            restart_default = self.custom_settings["runtime_config"].get("restart_count", 20)
        elif self.config:
            restart_default = self.config.restart_count
        self.restart_count_var = tk.StringVar(value=str(restart_default))
        restart_entry = tk.Entry(restart_frame, textvariable=self.restart_count_var, width=15)
        restart_entry.pack(side="left")

        # 세 번째 줄: 썸네일 포함 체크박스 + 로그 레벨 설정
        row3_frame = tk.Frame(settings_frame)
        row3_frame.pack(fill="x", pady=(0, 10))

        # 썸네일 포함 체크박스 (왼쪽)
        thumbnail_default = True
        if self.custom_settings and "runtime_config" in self.custom_settings:
            thumbnail_default = self.custom_settings["runtime_config"].get("include_thumbnail", True)
        else:
            thumbnail_default = getattr(self.config, "include_thumbnail", True)
        self.thumbnail_var = tk.BooleanVar(value=thumbnail_default)
        thumbnail_check = tk.Checkbutton(
            row3_frame,
            text="썸네일 포함",
            variable=self.thumbnail_var,
            font=("맑은 고딕", ui_settings["font_size"]),
        )
        _bind_tooltip(thumbnail_check, "BOM 엑셀 파일에 도면 썸네일 이미지 포함")
        thumbnail_check.pack(side="left")

        # 로그 레벨 설정 (오른쪽)
        log_level_frame = tk.Frame(row3_frame)
        log_level_frame.pack(side="right")
        log_level_label = tk.Label(log_level_frame, text="로그 레벨", font=("맑은 고딕", ui_settings["font_size"]))
        log_level_label.pack(side="left", padx=(0, 5))
        _bind_tooltip(log_level_label, "로그 상세 수준 (DEBUG: 모든 정보, ERROR: 오류만)")

        log_level_default = "DEBUG"
        try:
            lvl = logging.getLevelName(self.logger.level) if self.logger else "DEBUG"
            log_level_default = lvl if isinstance(lvl, str) else "DEBUG"
        except Exception:
            log_level_default = "DEBUG"

        self.log_level_var = tk.StringVar(value=log_level_default)
        log_level_combo = ttk.Combobox(
            log_level_frame,
            textvariable=self.log_level_var,
            values=["DEBUG", "INFO", "WARNING", "ERROR"],
            state="readonly",
            width=12,
        )
        log_level_combo.pack(side="left")

        # 타임아웃 설정은 UI에서 제거 (설정 파일에서만 관리)
        # base_wait_time: 60초, seconds_per_10mb: 60초가 기본값으로 사용됨

        # 버튼 프레임 (여백 감소하여 버튼 위치 올림)
        button_frame = tk.Frame(main_frame)
        button_frame.pack(side="bottom", pady=(10, 10), fill="x")

        # 버튼을 프레임 중앙에 배치
        button_container = tk.Frame(button_frame)
        button_container.pack(expand=True)

        save_btn = tk.Button(
            button_container,
            text="저장",
            command=self.save_settings,
            width=12,
            height=2,
            font=("맑은 고딕", ui_settings["font_size"]),
        )
        save_btn.pack(side="left", padx=20)

        cancel_btn = tk.Button(
            button_container,
            text="취소",
            command=self.close_settings_window,
            width=12,
            height=2,
            font=("맑은 고딕", ui_settings["font_size"]),
        )
        cancel_btn.pack(side="left", padx=20)

        # 창 닫기 이벤트 처리
        self.settings_win.protocol("WM_DELETE_WINDOW", self.close_settings_window)

    def browse_app_path(self):
        """실행 앱 경로 찾기"""
        from tkinter import filedialog

        # 설정 창이 없으면 일반 대화상자 열기
        if not self.settings_win:
            file_path = filedialog.askopenfilename(
                title="SolidWorks 실행 파일 선택",
                filetypes=[("실행 파일", "*.exe"), ("모든 파일", "*.*")],
                initialdir="C:\\Program Files\\SOLIDWORKS Corp\\SOLIDWORKS\\",
            )
            if file_path:
                self.app_path_var.set(file_path)
            return

        # 원래 topmost 상태 저장
        original_settings_topmost = self.settings_win.attributes("-topmost")
        parent_topmost = None
        if hasattr(self.parent_app, "master") and self.parent_app.master:
            try:
                parent_topmost = self.parent_app.master.attributes("-topmost")
                # 메인창의 topmost만 임시 해제 (설정창은 유지)
                self.parent_app.master.attributes("-topmost", 0)
            except Exception:
                parent_topmost = None

        # 모달 임시 해제
        self.settings_win.grab_release()
        self.settings_win.update()

        # 파일다이얼로그 열기 (블로킹 - 사용자가 선택/취소할 때까지 대기)
        file_path = filedialog.askopenfilename(
            title="SolidWorks 실행 파일 선택",
            filetypes=[("실행 파일", "*.exe"), ("모든 파일", "*.*")],
            initialdir="C:\\Program Files\\SOLIDWORKS Corp\\SOLIDWORKS\\",
            parent=self.settings_win,
        )

        # 파일다이얼로그가 닫힌 후 설정창 복원
        if self.settings_win and self.settings_win.winfo_exists():
            self.settings_win.lift()  # 설정창을 맨 앞으로
            self.settings_win.attributes("-topmost", original_settings_topmost)
            self.settings_win.grab_set()  # 모달 다시 설정
            self.settings_win.focus_set()  # 포커스 복원

        # 메인창 topmost 복원 (설정창 복원 후 즉시)
        if (
            parent_topmost is not None
            and hasattr(self.parent_app, "master")
            and self.parent_app.master
        ):
            try:
                self.parent_app.master.attributes("-topmost", parent_topmost)
            except Exception:
                pass

        if file_path:
            self.app_path_var.set(file_path)

    def browse_solidworks_path(self):
        """SolidWorks 실행 파일 경로 찾기 (호환성 유지)"""
        self.browse_app_path()

    def save_settings(self):
        """설정 저장"""
        try:
            # 앱 실행 경로 검증
            app_path = self.app_path_var.get().strip()
            if app_path and not Path(app_path).exists():
                tkinter.messagebox.showerror("오류", "실행 파일이 존재하지 않습니다.")
                return

            # 재시작 카운트 검증
            restart_count = int(self.restart_count_var.get())
            if restart_count <= 0:
                tkinter.messagebox.showerror("오류", "재시작 카운트는 1 이상이어야 합니다.")
                return

            # 타임아웃 설정은 기본값 사용 (UI에서 제거됨)
            base_wait_time_sec = 60  # 기본값: 60초
            seconds_per_10mb = 60  # 기본값: 60초

            # 통합 설정 파일 경로 (run_mode별)
            settings_file = _resolve_settings_file()
            settings_dir = settings_file.parent

            # 디렉토리 생성
            settings_dir.mkdir(parents=True, exist_ok=True)

            # 기존 설정 로드 (ui_config.last_selected_folder 보존)
            existing_data = {}
            if settings_file.exists():
                try:
                    with open(settings_file, "r", encoding="utf-8") as f:
                        existing_data = json.load(f)
                except Exception:
                    pass

            # 설정 데이터 준비 (기존 ui_config 보존)
            settings_data = {
                "app_info": {"last_updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")},
                "solidworks": {"program_path": app_path},
                "app_config": {
                    "restart_count": restart_count,
                    "topmost": self.topmost_var.get(),
                    "auto_restart": self.restart_var.get(),
                    "speed_mode": self.speed_var.get(),
                    "base_wait_time": base_wait_time_sec,
                    "seconds_per_10mb": seconds_per_10mb,
                    "include_thumbnail": self.thumbnail_var.get(),
                },
                "ui_config": existing_data.get("ui_config", {"last_selected_folder": ""})
            }

            # JSON 파일로 저장
            with open(settings_file, "w", encoding="utf-8") as f:
                json.dump(settings_data, f, ensure_ascii=False, indent=2)

            # 전역 설정에 로그 레벨 저장 (run_mode별 경로)
            try:
                config_file = _resolve_global_config_file()
                global_config = {}
                if config_file.exists():
                    with open(config_file, "r", encoding="utf-8") as f:
                        global_config = json.load(f) or {}
                if "system_settings" not in global_config:
                    global_config["system_settings"] = {}
                global_config["system_settings"]["log_level"] = self.log_level_var.get()
                config_file.parent.mkdir(parents=True, exist_ok=True)
                with open(config_file, "w", encoding="utf-8") as f:
                    json.dump(global_config, f, ensure_ascii=False, indent=2)
                
                # 로그 레벨 즉시 적용
                log_level_str = self.log_level_var.get()
                log_level_map = {
                    "DEBUG": logging.DEBUG,
                    "INFO": logging.INFO,
                    "WARNING": logging.WARNING,
                    "ERROR": logging.ERROR,
                }
                if log_level_str in log_level_map:
                    self.logger.setLevel(log_level_map[log_level_str])
                    for handler in self.logger.handlers:
                        handler.setLevel(log_level_map[log_level_str])
                    self.logger.info(f"✅ 로그 레벨 변경: {log_level_str}")
            except Exception as e:
                self.logger.warning(f"⚠️ 로그 레벨 저장 실패: {e}")

            # 기존 config 시스템도 업데이트 (호환성을 위해)
            if self.config:
                self.config.program_path = app_path
                # user_email은 config에 없으므로 건너뜀
                self.config.restart_count = restart_count

            # 부모 앱의 설정도 업데이트
            if hasattr(self.parent_app, "restart_count"):
                self.parent_app.restart_count = restart_count

            # 최상위 고정 적용은 확인 버튼 클릭 이후로 지연 처리 (아래에서 적용)

            # 부모 앱의 다른 설정들도 업데이트
            if hasattr(self.parent_app, "config"):
                self.parent_app.config.program_path = app_path
                self.parent_app.config.restart_count = restart_count

            # 변경된 설정값들만 표시하는 메시지 생성
            changed_settings = []

            if self.custom_settings:
                # 이전 설정이 있는 경우 비교
                old_settings = self.custom_settings
                old_app_config = old_settings.get("app_config", {})

                # SolidWorks 경로 비교
                if app_path != old_settings.get("solidworks", {}).get("program_path", ""):
                    changed_settings.append(f"실행 경로: {Path(app_path).name}")

                # 재시작 카운트 비교
                if restart_count != old_app_config.get("restart_count", 20):
                    changed_settings.append(f"재시작 카운트: {restart_count}")

                # 최상위 고정 비교
                if self.topmost_var.get() != old_app_config.get("topmost", False):
                    changed_settings.append(
                        f"최상위 고정: {'켜짐' if self.topmost_var.get() else '꺼짐'}"
                    )

                # 자동 재시작 비교
                if self.restart_var.get() != old_app_config.get("auto_restart", True):
                    changed_settings.append(
                        f"재시작 여부: {'켜짐' if self.restart_var.get() else '꺼짐'}"
                    )

                # 속도 모드 비교
                if self.speed_var.get() != old_app_config.get("speed_mode", "normal"):
                    speed_names = {"slow": "느림", "normal": "보통", "fast": "빠름"}
                    changed_settings.append(
                        f"속도: {speed_names.get(self.speed_var.get(), self.speed_var.get())}"
                    )

                # 타임아웃 설정 변경 알림 제거 (UI에서 숨김)
                
                # 로그 레벨 비교
                try:
                    config_file = _resolve_global_config_file()
                    if config_file.exists():
                        with open(config_file, "r", encoding="utf-8") as f:
                            global_config = json.load(f) or {}
                        old_log_level = global_config.get("system_settings", {}).get("log_level", "DEBUG")
                        if self.log_level_var.get() != old_log_level:
                            changed_settings.append(f"로그 레벨: {self.log_level_var.get()}")
                except Exception:
                    pass
            else:
                # 첫 저장인 경우 현재 설정값들 표시
                changed_settings.append(f"실행 경로: {Path(app_path).name}")
                changed_settings.append(f"재시작 카운트: {restart_count}")
                changed_settings.append(
                    f"최상위 고정: {'켜짐' if self.topmost_var.get() else '꺼짐'}"
                )
                changed_settings.append(
                    f"재시작 여부: {'켜짐' if self.restart_var.get() else '꺼짐'}"
                )
                speed_names = {"slow": "느림", "normal": "보통", "fast": "빠름"}
                changed_settings.append(
                    f"속도: {speed_names.get(self.speed_var.get(), self.speed_var.get())}"
                )
                changed_settings.append(f"로그 레벨: {self.log_level_var.get()}")
                # 타임아웃 설정은 UI에서 제거됨 (설정 파일에서만 관리)

            # 메시지 생성
            if changed_settings:
                message = "다음 설정이 저장되었습니다:\n\n" + "\n".join(
                    f"• {setting}" for setting in changed_settings
                )
            else:
                message = "설정이 저장되었습니다."

            if self.settings_win:
                # 메시지 박스가 닫힐 때까지 대기 (확인 버튼 클릭)
                tkinter.messagebox.showinfo("저장 완료", message, parent=self.settings_win)

            # 확인 클릭 후 메인창에만 최상위 적용
            try:
                if hasattr(self.parent_app, "master") and self.parent_app.master:
                    self.parent_app.master.wm_attributes("-topmost", self.topmost_var.get())
            except Exception:
                pass

            self.close_settings_window()

        except ValueError:
            tkinter.messagebox.showerror("오류", "올바른 숫자를 입력해주세요.")
        except Exception as e:
            tkinter.messagebox.showerror("오류", f"설정 저장 실패: {e}")

    def close_settings_window(self):
        """설정 창 닫기"""
        if self.settings_win:
            # ⚠️ 중요: 모달 설정 해제 (리팩토링 시에도 유지할 것!)
            try:
                self.settings_win.grab_release()  # 모달 해제 - 절대 제거하지 말 것
            except:
                pass

            self.settings_win.destroy()
            self.settings_win = None

    def on_topmost_changed(self):
        """최상위 고정 즉시 적용 비활성화: 저장 시에만 적용"""
        # 요구사항: 체크박스 변경 시에는 아무 동작도 하지 않음.
        # 실제 적용은 save_settings()에서 메인창(master)에만 수행.
        try:
            pass
        except Exception:
            pass


class MockParentApp:
    """독립 실행을 위한 더미 부모 앱"""

    def __init__(self):
        self.restart_count = 20
        self.master = None  # 독립 실행임을 표시


def load_custom_settings():
    """통합 설정 파일 로드하는 유틸리티 함수 (settings.json)"""
    try:
        settings_path = _resolve_settings_file()
        if settings_path.exists():
            with open(settings_path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        print(f"설정 로드 실패: {e}")
    return None


def apply_custom_settings_to_config(config, custom_settings):
    """커스텀 설정을 기존 config 객체에 적용하는 유틸리티 함수"""
    if not custom_settings or not config:
        return

    try:
        # SolidWorks 경로 설정
        if "solidworks" in custom_settings:
            sw_settings = custom_settings["solidworks"]
            if "program_path" in sw_settings:
                config.program_path = sw_settings["program_path"]

        # 앱 설정
        if "app_config" in custom_settings:
            app_config = custom_settings["app_config"]
            if "restart_count" in app_config:
                config.restart_count = app_config["restart_count"]

        # 사용자 설정(user_settings)은 더 이상 사용하지 않음 (전역 설정 파일 사용)
        print("커스텀 설정이 config 객체에 적용되었습니다.")
    except Exception as e:
        print(f"커스텀 설정 적용 실패: {e}")


def create_settings_window(parent_app, hardware_info=None):
    settings = SettingsWindow(parent_app, hardware_info)
    settings.open_settings_window()
    return settings


if __name__ == "__main__":
    """독립 실행"""
    print("=== ui_setting.py 독립 실행 모드 ===")

    # 적응형 UI 설정 가져오기
    ui_settings = get_adaptive_ui_settings()

    # 더미 부모 앱 생성
    mock_app = MockParentApp()

    # 메인 윈도우 생성 (적응형 크기)
    root = tk.Tk()
    root.title("설정 테스트")
    center_window_on_screen(root, ui_settings["window_width"], ui_settings["window_height"])
    root.withdraw()  # 메인 윈도우 숨김

    # 설정 창 생성 및 열기
    settings_window = SettingsWindow(mock_app)
    settings_window.open_settings_window()

    print("설정 창이 열렸습니다. 창을 닫으면 프로그램이 종료됩니다.")

    # GUI 루프 실행
    root.mainloop()
