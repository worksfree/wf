# -*- coding: utf-8 -*-
"""
QR Code Generator Automation Module
QR 코드 생성 핵심 로직을 담당하는 모듈
"""

import os
import sys
import logging
import time
import json
from pathlib import Path

# 현재 스크립트 디렉토리
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# 10.common 모듈 경로 추가
common_path = os.path.abspath(os.path.join(current_dir, "..", "..", "10.common"))
if common_path not in sys.path:
    sys.path.insert(0, common_path)

from wf_log import get_app_logger

# 이메일 모듈 import
try:
    import wf_email as wfm
except ImportError:
    wfm = None

# QR / PIL 모듈
try:
    import qrcode
    from qrcode.constants import ERROR_CORRECT_L, ERROR_CORRECT_M, ERROR_CORRECT_Q, ERROR_CORRECT_H
    from PIL import Image, ImageDraw, ImageFont
    QR_AVAILABLE = True
except ImportError as e:
    QR_AVAILABLE = False
    _import_error = str(e)


class QRCodeGenerator:
    """QR 코드 생성 자동화 클래스"""

    def __init__(self, config=None, log_callback=None):
        # 설정 로드
        if config is None:
            from app_setting_data import get_config
            self.config = get_config()
        else:
            self.config = config

        self.logger = get_app_logger("qrcode_generator", console_level=logging.DEBUG)
        self.log_callback = log_callback

        # 이메일 설정
        self.itself_dir = current_dir
        self.user_email = ""
        self.report_email = ""

        # 로그 디렉토리 설정
        run_mode = getattr(self.config, "run_mode", "release")
        if run_mode in ("dev", "demo"):
            log_dir_path = Path(current_dir) / "logs"
        else:
            log_dir_path = Path.home() / ".wf_rpa" / "qrcode_generator" / "logs"
        log_dir_path.mkdir(parents=True, exist_ok=True)
        self.log_dir = str(log_dir_path).replace("\\", "/")
        self.logfile = str(log_dir_path / f"{time.strftime('%Y%m%d')}.txt").replace("\\", "/")

        self._init_email_settings()

        # UI 콜백
        self.progress_callback = None
        self.credit_update_callback = None

        # 크레딧 관리자
        self.credit_manager = None

    def _init_email_settings(self):
        """이메일 설정 초기화 (wf_rpa_config.json에서 로드)"""
        try:
            config_file = Path.home() / ".wf_rpa" / "wf_rpa_config.json"
            if config_file.exists():
                with open(config_file, "r", encoding="utf-8") as f:
                    data = json.load(f) or {}
                email_settings = data.get("email_settings", {})
                self.user_email = email_settings.get("user_email", "")
                self.report_email = email_settings.get("report_email", self.user_email)
        except Exception as e:
            self.logger.debug(f"이메일 설정 로드 실패: {e}")

    def handle_error(self, error, context=""):
        """에러 처리 (로그 + 이메일)"""
        error_msg = f"[오류] {context}: {error}" if context else f"[오류] {error}"
        self.logger.error(error_msg)
        if self.log_callback:
            self.log_callback(error_msg)

        # 이메일 알림
        if wfm and self.user_email:
            try:
                wfm.send_error_email(
                    to_email=self.report_email or self.user_email,
                    subject=f"[QR Generator] 오류 발생: {context}",
                    body=error_msg,
                )
            except Exception:
                pass

    def _log(self, message):
        """로그 메시지 출력"""
        self.logger.info(message)
        if self.log_callback:
            self.log_callback(message)

    def _update_progress(self, value):
        """진행률 업데이트"""
        if self.progress_callback:
            self.progress_callback(value)

    def _resolve_font_paths(self):
        """크로스 플랫폼 폰트 경로 해석"""
        regular_font = None
        bold_font = None

        if sys.platform == "win32":
            fonts_dir = Path("C:/Windows/Fonts")
            regular_path = fonts_dir / "malgun.ttf"
            bold_path = fonts_dir / "malgunbd.ttf"
            if bold_path.exists():
                bold_font = str(bold_path)
            if regular_path.exists():
                regular_font = str(regular_path)
        else:
            # Linux / macOS
            for candidate in [
                "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
                "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
                "/usr/share/fonts/opentype/noto/NotoSansCJK-Medium.ttc",
            ]:
                if Path(candidate).exists():
                    bold_font = candidate
                    regular_font = candidate
                    break

        return regular_font, bold_font

    def _get_error_correction(self, level_str: str):
        """에러 정정 레벨 문자열을 qrcode 상수로 변환"""
        if not QR_AVAILABLE:
            return None
        mapping = {
            "L": ERROR_CORRECT_L,
            "M": ERROR_CORRECT_M,
            "Q": ERROR_CORRECT_Q,
            "H": ERROR_CORRECT_H,
        }
        return mapping.get(level_str.upper(), ERROR_CORRECT_L)

    def _build_output_path(self) -> Path:
        """출력 파일 경로 결정"""
        output_folder = self.config.output_folder
        if not output_folder or not Path(output_folder).exists():
            # Fallback: Desktop → Home
            desktop = Path.home() / "Desktop"
            if desktop.exists():
                output_folder = str(desktop)
            else:
                output_folder = str(Path.home())

        filename = self.config.output_filename or "qrcode_output.png"
        return Path(output_folder) / filename

    def generate_qr_code(self, url: str) -> str:
        """QR 코드 생성 메인 메서드

        Args:
            url: QR 코드에 인코딩할 URL 문자열

        Returns:
            생성된 이미지 파일 경로 (실패 시 빈 문자열)
        """
        if not QR_AVAILABLE:
            self.handle_error(_import_error, "모듈 로드 실패")
            return ""

        if not url or not url.strip():
            self.handle_error("URL이 비어있습니다", "입력 검증")
            return ""

        url = url.strip()
        self._log(f"QR 코드 생성 시작: {url}")
        self._update_progress(10)

        try:
            # 1. QR 코드 생성
            error_correction = self._get_error_correction(self.config.error_correction)
            qr = qrcode.QRCode(
                version=self.config.qr_version,
                error_correction=error_correction,
                box_size=self.config.box_size,
                border=self.config.border,
            )
            qr.add_data(url)
            qr.make(fit=True)
            qr_img = qr.make_image(
                fill_color=self.config.fill_color,
                back_color=self.config.back_color,
            ).convert('RGB')

            self._log(f"QR 버전: {qr.version}, 모듈 수: {qr.modules_count}x{qr.modules_count}")
            self._update_progress(30)

            # 2. 폰트 설정
            regular_font_path, bold_font_path = self._resolve_font_paths()

            try:
                font_title = ImageFont.truetype(
                    bold_font_path or regular_font_path,
                    self.config.font_size_title
                )
                font_subtitle = ImageFont.truetype(
                    regular_font_path or bold_font_path,
                    self.config.font_size_subtitle
                )
            except Exception:
                font_title = ImageFont.load_default()
                font_subtitle = ImageFont.load_default()
                self._log("시스템 폰트 로드 실패 - 기본 폰트 사용")

            # 3. 텍스트 크기 계산
            title_text = self.config.title_text
            subtitle_text = self.config.subtitle_text
            has_title = bool(title_text.strip())
            has_subtitle = bool(subtitle_text.strip())

            temp_draw = ImageDraw.Draw(qr_img)
            
            # 텍스트가 있을 때만 크기 계산
            if has_title:
                title_bbox = temp_draw.textbbox((0, 0), title_text, font=font_title)
                title_width = title_bbox[2] - title_bbox[0]
                title_height = title_bbox[3] - title_bbox[1]
            else:
                title_width = 0
                title_height = 0
            
            if has_subtitle:
                subtitle_bbox = temp_draw.textbbox((0, 0), subtitle_text, font=font_subtitle)
                subtitle_width = subtitle_bbox[2] - subtitle_bbox[0]
                subtitle_height = subtitle_bbox[3] - subtitle_bbox[1]
            else:
                subtitle_width = 0
                subtitle_height = 0

            self._update_progress(50)

            # 4. 캔버스 레이아웃 (텍스트 유무에 따라 동적 조정)
            qr_width, qr_height = qr_img.size
            
            # 텍스트가 있을 때만 패딩/갭 적용
            padding_top = 30 if has_title else 10
            padding_bottom = 30 if has_subtitle else 10
            gap_top = 25 if has_title else 0
            gap_bottom = 20 if has_subtitle else 0
            side_padding = 60 if (has_title or has_subtitle) else 10

            canvas_width = max(qr_width, title_width, subtitle_width) + side_padding * 2
            canvas_height = (padding_top + title_height + gap_top +
                             qr_height + gap_bottom + subtitle_height + padding_bottom)

            canvas = Image.new('RGB', (canvas_width, canvas_height), 'white')
            draw = ImageDraw.Draw(canvas)

            # 상단 장식선 (제목이 있을 때만)
            if has_title:
                line_y = padding_top // 2
                draw.line(
                    [(side_padding, line_y), (canvas_width - side_padding, line_y)],
                    fill="#CCCCCC", width=2
                )

            # 제목 텍스트 (있을 때만)
            if has_title:
                title_x = (canvas_width - title_width) // 2
                title_y = padding_top
                draw.text((title_x, title_y), title_text, font=font_title, fill=self.config.title_color)

            # QR 코드 배치
            qr_x = (canvas_width - qr_width) // 2
            qr_y = padding_top + title_height + gap_top
            canvas.paste(qr_img, (qr_x, qr_y))

            self._update_progress(70)

            # 부제목 텍스트 (있을 때만)
            if has_subtitle:
                subtitle_x = (canvas_width - subtitle_width) // 2
                subtitle_y = qr_y + qr_height + gap_bottom
                draw.text((subtitle_x, subtitle_y), subtitle_text, font=font_subtitle, fill=self.config.subtitle_color)

            # 하단 장식선 (부제목이 있을 때만)
            if has_subtitle:
                bottom_line_y = canvas_height - padding_bottom // 2
                draw.line(
                    [(side_padding, bottom_line_y), (canvas_width - side_padding, bottom_line_y)],
                    fill="#CCCCCC", width=2
                )

            self._update_progress(90)

            # 5. 저장
            output_path = self._build_output_path()
            output_path.parent.mkdir(parents=True, exist_ok=True)
            canvas.save(str(output_path), quality=95)

            self._log(f"QR 코드 생성 완료: {output_path}")
            self._log(f"이미지 크기: {canvas.size[0]} x {canvas.size[1]} 픽셀")
            self._update_progress(100)

            return str(output_path)

        except Exception as e:
            self.handle_error(e, "QR 코드 생성")
            return ""
