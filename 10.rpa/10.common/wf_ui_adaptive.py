# -*- coding: utf-8 -*-
"""
wf_ui_adaptive.py - WorksFree Adaptive UI 통합 모듈

모든 앱에서 사용하는 DPI/해상도 기반 적응형 UI 설정을 제공합니다.
연속적 스케일링 방식으로 모든 DPI 배율을 지원합니다.

지원 범위:
- DPI: 100%, 125%, 150%, 175%, 200%, 225%, 250%, 300%
- 해상도: FHD (1920x1080), QHD (2560x1440), UHD (3840x2160)
- Windows 텍스트 스케일 팩터 (접근성 설정)

사용법:
    from wf_ui_adaptive import get_adaptive_ui_settings, apply_global_fonts

    ui = get_adaptive_ui_settings(window_type="main")
    apply_global_fonts(root, ui)
"""

import logging
import sys

# 모듈 레벨 로거
logger: logging.Logger = logging.getLogger("wf_ui_adaptive")
if not logger.handlers:
    logger.addHandler(logging.NullHandler())


def set_logger(external_logger: logging.Logger):
    """외부 로거 주입"""
    global logger
    logger = external_logger


def apply_equal_vertical_pack(container):
    """Pack 레이아웃에서 상하 등간(균등) 확장 적용"""
    try:
        children = [w for w in container.winfo_children() if hasattr(w, "pack_configure")]
        if not children:
            return
        for w in children:
            try:
                w.pack_configure(fill="x", expand=True)
            except Exception:
                continue
    except Exception:
        return


# =============================================================================
# 기본 UI 스키마 (100% DPI, FHD 기준)
# =============================================================================
_UI_BASE_SCHEMA = {
    # 폰트 크기 (포인트)
    "font_size": 9,
    "font_size_bold": 9,
    "font_size_title": 9,

    # 메인 창 크기 (4행 레이아웃: 폴더선택, 진행률, 상태, 버튼)
    "main_window": {"width": 520, "height": 200},

    # 서브 창 크기 (설정/등록 다이얼로그)
    "sub_window": {"width": 500, "height": 450},

    # 위젯 크기
    "tree_rowheight": 22,
    "tree_height": 4,
    "entry_width": 30,
    "button_width": 8,

    # 여백
    "padding": 10,
}

# 창 크기 최소/최대 제한
_WINDOW_LIMITS = {
    "main": {"min_width": 480, "max_width": 900, "min_height": 180, "max_height": 400},
    "sub": {"min_width": 450, "max_width": 800, "min_height": 400, "max_height": 700},
}

# 폰트 크기 제한 (접근성 고려)
# 최소값은 Windows 타이틀바 폰트 픽셀 높이 기준 (동적으로 감지, 계수 1.0)
# 예: 100% DPI → 12pt, 125% DPI → 15pt, 150% DPI → 18pt
_FONT_LIMITS = {"min": 9, "max": 20}  # min은 _get_titlebar_font_size()로 동적 업데이트


# =============================================================================
# DPI 및 텍스트 스케일 감지
# =============================================================================
def _get_dpi_scale() -> float:
    """
    Windows DPI 배율 감지.

    Returns:
        float: DPI 배율 (1.0 = 100%, 1.25 = 125%, ..., 3.0 = 300%)
    """
    if sys.platform != "win32":
        return 1.0

    try:
        import ctypes

        # DPI Awareness 설정 시도 (Per-Monitor V2)
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            try:
                ctypes.windll.shcore.SetProcessDpiAwareness(1)
            except Exception:
                pass

        # 주 모니터 DPI 가져오기
        hdc = ctypes.windll.user32.GetDC(0)
        dpi = ctypes.windll.gdi32.GetDeviceCaps(hdc, 88)  # LOGPIXELSX
        ctypes.windll.user32.ReleaseDC(0, hdc)

        dpi_scale = dpi / 96.0  # 96 DPI = 100%
        return dpi_scale
    except Exception as e:
        logger.debug(f"DPI 감지 실패: {e}")
        return 1.0


def _get_text_scale_factor() -> float:
    """
    Windows 텍스트 스케일 팩터 감지 (설정 > 접근성 > 텍스트 크기).

    Returns:
        float: 텍스트 스케일 (1.0 = 100%, 1.5 = 150%, 2.25 = 225%)
    """
    if sys.platform != "win32":
        return 1.0

    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Accessibility"
        )
        value, _ = winreg.QueryValueEx(key, "TextScaleFactor")
        winreg.CloseKey(key)
        return value / 100.0  # 100 = 1.0, 150 = 1.5
    except Exception:
        return 1.0


def _get_titlebar_font_size() -> int:
    """
    Windows 타이틀바(캡션) 폰트 크기 감지.

    NONCLIENTMETRICS의 lfCaptionFont 정보를 사용합니다.
    실패 시 기본값 9pt 반환.

    Returns:
        int: 타이틀바 폰트 크기 (포인트)
    """
    if sys.platform != "win32":
        return 9

    try:
        import ctypes
        from ctypes import wintypes, byref, sizeof

        # LOGFONT 구조체 (simplified)
        class LOGFONT(ctypes.Structure):
            _fields_ = [
                ("lfHeight", ctypes.c_long),
                ("lfWidth", ctypes.c_long),
                ("lfEscapement", ctypes.c_long),
                ("lfOrientation", ctypes.c_long),
                ("lfWeight", ctypes.c_long),
                ("lfItalic", ctypes.c_byte),
                ("lfUnderline", ctypes.c_byte),
                ("lfStrikeOut", ctypes.c_byte),
                ("lfCharSet", ctypes.c_byte),
                ("lfOutPrecision", ctypes.c_byte),
                ("lfClipPrecision", ctypes.c_byte),
                ("lfQuality", ctypes.c_byte),
                ("lfPitchAndFamily", ctypes.c_byte),
                ("lfFaceName", ctypes.c_wchar * 32),
            ]

        # NONCLIENTMETRICS 구조체
        class NONCLIENTMETRICS(ctypes.Structure):
            _fields_ = [
                ("cbSize", wintypes.UINT),
                ("iBorderWidth", ctypes.c_int),
                ("iScrollWidth", ctypes.c_int),
                ("iScrollHeight", ctypes.c_int),
                ("iCaptionWidth", ctypes.c_int),
                ("iCaptionHeight", ctypes.c_int),
                ("lfCaptionFont", LOGFONT),
                ("iSmCaptionWidth", ctypes.c_int),
                ("iSmCaptionHeight", ctypes.c_int),
                ("lfSmCaptionFont", LOGFONT),
                ("iMenuWidth", ctypes.c_int),
                ("iMenuHeight", ctypes.c_int),
                ("lfMenuFont", LOGFONT),
                ("lfStatusFont", LOGFONT),
                ("lfMessageFont", LOGFONT),
                ("iPaddedBorderWidth", ctypes.c_int),
            ]

        SPI_GETNONCLIENTMETRICS = 0x0029
        ncm = NONCLIENTMETRICS()
        ncm.cbSize = sizeof(NONCLIENTMETRICS)

        result = ctypes.windll.user32.SystemParametersInfoW(
            SPI_GETNONCLIENTMETRICS, sizeof(NONCLIENTMETRICS), byref(ncm), 0
        )

        if result:
            # lfHeight는 음수일 수 있음 (문자 셀 높이)
            # 양수면 셀 높이, 음수면 문자 높이
            height = ncm.lfCaptionFont.lfHeight
            if height < 0:
                height = -height

            # Tkinter는 tk scaling 1.0 설정 시 DPI를 무시함
            # 따라서 픽셀 높이를 직접 포인트로 사용해야 타이틀바와 일치
            # lfHeight가 픽셀 단위이므로 그대로 사용 (Tkinter scaling 1.0 기준)
            # 계수 1.0: 타이틀바 폰트 픽셀 높이를 그대로 최소 폰트 크기로 사용
            # 예: 125% DPI → lfHeight=15px → 15pt (다른 DPI에서는 자동 조정)
            font_pt = height  # 1.0 계수

            # 합리적인 범위 내에서만 반환 (9~20pt)
            # 100% DPI: ~12pt, 125%: ~15pt, 150%: ~18pt, 175%+: 20pt 상한
            if 9 <= font_pt <= 20:
                return font_pt
            elif font_pt < 9:
                return 9
            else:
                return 20

        return 9  # 기본값
    except Exception as e:
        logger.debug(f"타이틀바 폰트 감지 실패: {e}")
        return 9


def _get_screen_info() -> tuple:
    """
    화면 해상도 정보 감지.

    Returns:
        tuple: (scaled_width, scaled_height, physical_width, physical_height)
    """
    scaled_width, scaled_height = 1920, 1080

    try:
        import pyautogui
        scaled_width, scaled_height = pyautogui.size()
    except Exception:
        pass

    dpi_scale = _get_dpi_scale()
    physical_width = int(scaled_width * dpi_scale)
    physical_height = int(scaled_height * dpi_scale)

    return scaled_width, scaled_height, physical_width, physical_height


# =============================================================================
# 연속적 스케일링 계산
# =============================================================================
def _clamp(value: float, min_val: float, max_val: float) -> float:
    """값을 min/max 범위로 제한"""
    return max(min_val, min(value, max_val))


def _scale_value(base_value: float, scale: float,
                 min_val: float = None, max_val: float = None) -> int:
    """
    기본값에 스케일을 적용하고 정수로 반환.

    Args:
        base_value: 기준값 (100% DPI 기준)
        scale: 적용할 스케일 배율
        min_val: 최소값 (옵션)
        max_val: 최대값 (옵션)

    Returns:
        int: 스케일 적용된 정수값
    """
    scaled = base_value * scale
    if min_val is not None and max_val is not None:
        scaled = _clamp(scaled, min_val, max_val)
    return int(round(scaled))


def _calculate_window_scale(dpi_scale: float) -> float:
    """
    창 크기용 스케일 계산.

    DPI가 높아지면 창도 커져야 하지만, 너무 커지면 안 됨.
    100% → 1.0, 200% → 1.15, 300% → 1.25 (로그 스케일 느낌)
    """
    if dpi_scale <= 1.0:
        return 1.0

    # 점진적 증가: sqrt 기반으로 완만하게
    import math
    return 1.0 + (math.sqrt(dpi_scale) - 1.0) * 0.3


def _calculate_font_scale(dpi_scale: float, text_scale: float) -> float:
    """
    폰트 크기용 스케일 계산.

    - DPI 자체는 폰트에 영향 주지 않음 (Tkinter가 자동 처리)
    - 텍스트 스케일 팩터만 적용
    - 단, 매우 높은 DPI (200%+)에서는 약간 키움
    """
    font_scale = text_scale

    # 200% 이상에서는 폰트를 약간 키움 (가독성)
    if dpi_scale >= 2.0:
        font_scale *= 1.0 + (dpi_scale - 2.0) * 0.1

    return font_scale


def _calculate_widget_scale(dpi_scale: float) -> float:
    """
    위젯(트리뷰 행 높이, 여백 등) 스케일 계산.

    DPI가 높아지면 터치 타겟도 커져야 함.
    """
    if dpi_scale <= 1.0:
        return 1.0

    # 선형에 가깝게 증가
    return 1.0 + (dpi_scale - 1.0) * 0.4


# =============================================================================
# 메인 API
# =============================================================================
def get_adaptive_ui_settings(window_type: str = "main",
                              saved_ui: dict = None) -> dict:
    """
    화면 DPI 및 텍스트 스케일에 따른 적응형 UI 설정을 반환.

    연속적 스케일링으로 모든 DPI 배율을 자연스럽게 지원합니다.

    Args:
        window_type: "main" (메인 창) 또는 "sub" (설정/등록 다이얼로그)
        saved_ui: 저장된 UI 설정 (창 크기 오버라이드용)

    Returns:
        dict: UI 설정값
            - window_width, window_height: 창 크기
            - font_size, font_size_bold, font_size_title: 폰트 크기
            - tree_rowheight, tree_height: 트리뷰 설정
            - entry_width, button_width: 위젯 크기
            - padding: 여백
            - dpi_scale: 현재 DPI 배율
            - text_scale: 텍스트 스케일 팩터
    """
    # 스케일 팩터 감지
    dpi_scale = _get_dpi_scale()
    text_scale = _get_text_scale_factor()
    scaled_w, scaled_h, physical_w, physical_h = _get_screen_info()

    # 각 항목별 스케일 계산
    window_scale = _calculate_window_scale(dpi_scale)
    font_scale = _calculate_font_scale(dpi_scale, text_scale)
    widget_scale = _calculate_widget_scale(dpi_scale)

    # 창 타입에 따른 기본 크기 선택
    if window_type == "sub":
        base_win = _UI_BASE_SCHEMA["sub_window"]
        limits = _WINDOW_LIMITS["sub"]
    else:
        base_win = _UI_BASE_SCHEMA["main_window"]
        limits = _WINDOW_LIMITS["main"]

    # 창 크기 계산
    window_width = _scale_value(
        base_win["width"], window_scale,
        limits["min_width"], limits["max_width"]
    )
    window_height = _scale_value(
        base_win["height"], window_scale,
        limits["min_height"], limits["max_height"]
    )

    # 저장된 창 크기가 있으면 사용 (사용자 설정 우선)
    if saved_ui:
        if "window_width" in saved_ui:
            window_width = int(saved_ui["window_width"])
        if "window_height" in saved_ui:
            window_height = int(saved_ui["window_height"])
        # geometry_override 처리
        geo_str = saved_ui.get("window_geometry_override") or saved_ui.get("window_geometry", "")
        if geo_str:
            try:
                size_part = geo_str.split("+", 1)[0]
                if "x" in size_part:
                    w_str, h_str = size_part.split("x", 1)
                    window_width = int(w_str)
                    window_height = int(h_str)
            except Exception:
                pass

    # 타이틀바 폰트 크기를 최소값으로 사용
    titlebar_font = _get_titlebar_font_size()
    font_min = max(_FONT_LIMITS["min"], titlebar_font)

    # 폰트 크기 계산 (텍스트 스케일 적용)
    # 최소값은 타이틀바 폰트 크기와 동일하게 유지
    font_size = _scale_value(
        _UI_BASE_SCHEMA["font_size"], font_scale,
        font_min, _FONT_LIMITS["max"]
    )
    font_size_bold = _scale_value(
        _UI_BASE_SCHEMA["font_size_bold"], font_scale,
        font_min, _FONT_LIMITS["max"]
    )
    font_size_title = _scale_value(
        _UI_BASE_SCHEMA["font_size_title"], font_scale,
        font_min, _FONT_LIMITS["max"]
    )

    # 위젯 크기 계산
    tree_rowheight = _scale_value(
        _UI_BASE_SCHEMA["tree_rowheight"], widget_scale,
        18, 40
    )
    padding = _scale_value(
        _UI_BASE_SCHEMA["padding"], widget_scale,
        8, 20
    )

    # 고정값 (스케일 미적용)
    tree_height = _UI_BASE_SCHEMA["tree_height"]
    entry_width = _UI_BASE_SCHEMA["entry_width"]
    button_width = _UI_BASE_SCHEMA["button_width"]

    # 결과 반환
    result = {
        "window_width": window_width,
        "window_height": window_height,
        "font_size": font_size,
        "font_size_bold": font_size_bold,
        "font_size_title": font_size_title,
        "tree_rowheight": tree_rowheight,
        "tree_height": tree_height,
        "entry_width": entry_width,
        "button_width": button_width,
        "padding": padding,
        # 디버깅용 메타정보
        "dpi_scale": round(dpi_scale, 2),
        "text_scale": round(text_scale, 2),
        "_physical_resolution": f"{physical_w}x{physical_h}",
        "_scaled_resolution": f"{scaled_w}x{scaled_h}",
        "_titlebar_font": titlebar_font,
        "_font_min": font_min,
    }

    logger.debug(f"Adaptive UI: dpi={dpi_scale:.0%}, text={text_scale:.0%}, "
                 f"font={font_size}pt (min={font_min}pt, titlebar={titlebar_font}pt), "
                 f"window={window_width}x{window_height}")

    return result


def apply_global_fonts(root, ui: dict) -> None:
    """
    Tkinter 기본 폰트를 통일된 크기로 설정.

    Args:
        root: Tk root 윈도우
        ui: get_adaptive_ui_settings()에서 반환된 설정
    """
    try:
        # Tkinter 자체 스케일링 비활성화 (우리가 직접 제어)
        root.tk.call("tk", "scaling", 1.0)

        import tkinter.font as tkfont

        font_size = ui.get("font_size", 9)
        font_size_bold = ui.get("font_size_bold", 9)
        font_size_title = ui.get("font_size_title", 9)

        # 일반 폰트
        for name in (
            "TkDefaultFont",
            "TkTextFont",
            "TkFixedFont",
            "TkMenuFont",
            "TkIconFont",
            "TkTooltipFont",
        ):
            try:
                tkfont.nametofont(name).configure(size=font_size, weight="normal")
            except Exception:
                pass

        # 볼드/타이틀 폰트
        for name in ("TkHeadingFont", "TkCaptionFont"):
            try:
                tkfont.nametofont(name).configure(size=font_size_title, weight="bold")
            except Exception:
                pass

        # 작은 캡션 폰트
        try:
            tkfont.nametofont("TkSmallCaptionFont").configure(
                size=font_size_bold, weight="bold"
            )
        except Exception:
            pass

    except Exception as e:
        logger.debug(f"폰트 설정 실패: {e}")


def get_display_info() -> dict:
    """
    현재 디스플레이 정보 반환 (디버깅/로깅용).

    Returns:
        dict: 디스플레이 정보
    """
    dpi_scale = _get_dpi_scale()
    text_scale = _get_text_scale_factor()
    titlebar_font = _get_titlebar_font_size()
    scaled_w, scaled_h, physical_w, physical_h = _get_screen_info()

    return {
        "dpi_scale": dpi_scale,
        "dpi_percent": f"{dpi_scale * 100:.0f}%",
        "text_scale": text_scale,
        "text_percent": f"{text_scale * 100:.0f}%",
        "titlebar_font_pt": titlebar_font,
        "scaled_resolution": f"{scaled_w}x{scaled_h}",
        "physical_resolution": f"{physical_w}x{physical_h}",
        "resolution_class": (
            "UHD" if physical_w >= 3840 else
            "QHD" if physical_w >= 2560 else
            "FHD"
        ),
    }


# =============================================================================
# 하위 호환성 (기존 코드 지원)
# =============================================================================
# wf_register.py의 기존 함수명과 호환
_apply_global_fonts = apply_global_fonts
_get_display_info = get_display_info
