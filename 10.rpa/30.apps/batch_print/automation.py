# -*- coding: utf-8 -*-
"""
Batch Print Automation Module
DWG 파일 일괄 인쇄 자동화 모듈
원본 print_DWG_with_tkinter.py의 로직을 be 스키마에 맞춰 재작성
"""

import os
import sys
import logging
import datetime
import threading
import time
import queue
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable
import ctypes
from ctypes import wintypes
from time import ctime

# COM 초기화 (pywinauto와 tkinter.filedialog의 COM 충돌 방지)
# pywinauto는 eDrawings 자동화를 위해 COM을 사용하며,
# tkinter.filedialog도 Windows 파일 다이얼로그를 위해 COM 필요.
# 두 라이브러리가 같은 스레드 모드로 COM을 초기화하도록 설정.
# 2 = COINIT_APARTMENTTHREADED (단일 스레드 아파트먼트 모드)
try:
    import pythoncom
    pythoncom.CoInitializeEx(pythoncom.COINIT_APARTMENTTHREADED)
except Exception:
    pass

common_path = Path(__file__).resolve().parents[2] / "10.common"
if str(common_path) not in sys.path:
    sys.path.insert(0, str(common_path))

from wf_log import get_app_logger

try:
    import wf_email as wfm
except ImportError:
    wfm = None

try:
    from pywinauto.application import Application
    import pyautogui as pgui
except ImportError:
    Application = None
    pgui = None

# 로컬 모듈 import
from app_setting_data import get_config


class BatchPrintAutomation:
    """Batch Print 자동화 클래스 (원본 print_DWG_with_tkinter.py 로직 기반)"""

    def __init__(self, folder_path: Optional[str] = None, console_mode: bool = False):
        self.folder_path = folder_path
        self.console_mode = console_mode
        
        # 설정 로드
        self.config = get_config()
        self.run_mode = getattr(self.config, "run_mode", "release")
        
        # 로거 초기화
        console_level = logging.DEBUG if self.config.SHOW_DEBUG else logging.INFO
        self.logger = get_app_logger("batch_print", console_level=console_level)

        # 데모 모드 캡처 초기화
        self.demo_capture_enabled = self.run_mode == "demo"
        self.demo_capture_dir = None
        self.demo_capture_size = (1920, 1040)
        self._last_demo_capture_ts = 0.0
        self._cursor_img = None
        self._cursor_hotspot = None

        # 원본 코드의 변수들
        self.stop_progress_flag = False
        self.restart_count = getattr(self.config, "restart_count", 30)
        self.max_count = 0
        
        # eDrawings 설정
        self.edrawings_path = getattr(self.config, "program_path", 
            r"C:\Program Files\SOLIDWORKS Corp\eDrawings\eDrawings.exe")
        self.wait_timeout = getattr(self.config, "wait_timeout", 300)
        self.restart_sleep = getattr(self.config, "restart_sleep", 5)
        self.final_sleep = getattr(self.config, "final_sleep", 3)

        # 상태 변수
        self.current_file_index = 0
        self.total_files = 0

        # UI 콜백
        self.progress_callback = None
        self.credit_update_callback = None
        self.capture_callback = None

        # 크레딧 관리자
        self.credit_manager = None

        # 이메일 설정 (에러/완료 알림용)
        self.itself_dir = str(Path(__file__).resolve().parent)
        self.user_email = ""
        self.report_email = ""

        # 로그 디렉토리 설정
        if self.run_mode in ("dev", "demo"):
            log_dir_path = Path(self.itself_dir) / "logs"
        else:
            log_dir_path = Path.home() / ".wf_rpa" / "batch_print" / "logs"
        log_dir_path.mkdir(parents=True, exist_ok=True)
        self.log_dir = str(log_dir_path).replace("\\", "/")
        self.logfile = str(log_dir_path / f"{time.strftime('%Y%m%d')}.txt").replace("\\", "/")

        # 이메일 설정 초기화
        self._init_email_settings()

        # 데모 캡처 초기화
        if self.demo_capture_enabled:
            self._init_demo_capture()

    def set_progress_callback(self, callback: Callable):
        """진행률 콜백 설정"""
        self.progress_callback = callback

    def set_credit_update_callback(self, callback: Callable):
        """크레딧 업데이트 콜백 설정"""
        self.credit_update_callback = callback

    def set_credit_manager(self, credit_manager):
        """크레딧 관리자 설정"""
        self.credit_manager = credit_manager

    def _init_email_settings(self):
        """이메일 설정 초기화 (wf_rpa_config.json에서 로드)"""
        try:
            import json
            config_file = Path.home() / ".wf_rpa" / "wf_rpa_config.json"

            if config_file.exists():
                with open(config_file, "r", encoding="utf-8") as f:
                    config = json.load(f)

                # 사용자 이메일
                self.user_email = config.get("user_info", {}).get("user_email", "")

                # 리포트 수신 이메일
                email_settings = config.get("email_settings", {})
                self.report_email = email_settings.get("email_to", "")

                # report_email이 없으면 user_email로 폴백
                if not self.report_email:
                    self.report_email = self.user_email
            else:
                self.logger.debug(f"설정 파일 없음: {config_file}")

        except Exception as e:
            self.logger.warning(f"이메일 설정 로드 실패: {e}")

        self.logger.debug(f"이메일 설정: user={self.user_email}, report={self.report_email}")

    def handle_error(self, error, context="", mail_title_prefix="[DBP] [Error]", send_email=True):
        """공통 에러 처리: 스크린샷 저장 및 이메일 전송

        Args:
            error: 발생한 예외 또는 에러 메시지
            context: 에러 발생 컨텍스트 (파일명, 단계 등)
            mail_title_prefix: 이메일 제목 접두사
            send_email: 이메일 전송 여부 (기본값: True)

        Returns:
            tuple: (screenshot_path, timestamp) - 스크린샷 경로와 타임스탬프
        """
        timestamp4img = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

        # 스크린샷 캡처
        screenshot_path = None
        try:
            if pgui:
                screenshot = pgui.screenshot()
                screenshot_path = Path(self.log_dir) / f"{timestamp4img}.png"
                screenshot.save(str(screenshot_path))
                self.logger.debug(f"스크린샷 저장: {screenshot_path}")
        except Exception as e:
            self.logger.warning(f"스크린샷 캡처 실패: {e}")

        # 이메일 전송
        if send_email and wfm and self.report_email:
            error_content = f"{str(error)}"
            if context:
                error_content = f"{error_content}\n{context}"

            attach = []
            if screenshot_path:
                attach.append(str(screenshot_path).replace("\\", "/"))
            attach.append(self.logfile)

            try:
                wfm.init(self.itself_dir)
                mail_title = f"{mail_title_prefix} {self.user_email}"
                wfm.mail_send_attach(mail_title, self.report_email, error_content, attach)
                self.logger.debug("에러 이메일 전송 완료")
            except Exception as mail_e:
                self.logger.error(f"에러 이메일 전송 실패: {mail_e}")

        return str(screenshot_path) if screenshot_path else None, timestamp4img

    def send_completion_email(self, total_count: int, success_count: int, fail_count: int):
        """작업 완료 이메일 전송

        Args:
            total_count: 전체 파일 수
            success_count: 성공 파일 수
            fail_count: 실패 파일 수
        """
        if not wfm or not self.report_email:
            self.logger.debug("이메일 전송 건너뜀 (설정 없음)")
            return

        try:
            wfm.init(self.itself_dir)
            mail_title = f"[DBP] [Complete] {self.user_email}"
            content = (
                f"DWG 일괄 인쇄 완료\n\n"
                f"• 전체: {total_count}개\n"
                f"• 성공: {success_count}개\n"
                f"• 실패: {fail_count}개\n"
            )
            attach = [self.logfile]
            wfm.mail_send_attach(mail_title, self.report_email, content, attach)
            self.logger.info("완료 이메일 전송 완료")
        except Exception as e:
            self.logger.error(f"완료 이메일 전송 실패: {e}")

    def stop(self):
        """중지 신호 전송"""
        self.stop_progress_flag = True
        self.logger.info("중지 신호 전송")

    # ===== Demo Capture Logic (dwg_classifier에서 마이그레이션) =====
    def _init_demo_capture(self):
        """데모 모드 자동 캡처 초기화"""
        try:
            self.demo_capture_dir = self._resolve_demo_capture_dir()
            if self.demo_capture_dir:
                self.logger.info(f"[DEMO] Capture dir: {self.demo_capture_dir}")
            else:
                self.demo_capture_enabled = False
                self.logger.warning("[DEMO] 캡처 디렉터리를 준비하지 못해 자동 캡처를 비활성화합니다.")
        except Exception as e:
            self.demo_capture_enabled = False
            self.logger.warning(f"[DEMO] 캡처 초기화 실패: {e}")

    def _resolve_demo_capture_dir(self):
        """캡처 디렉터리 경로 확인 및 생성"""
        candidates = [
            Path(__file__).resolve().parent / "demo_captures",
            Path.home() / ".wf_rpa" / "batch_print" / "demo_captures",
        ]
        for cand in candidates:
            try:
                cand.mkdir(parents=True, exist_ok=True)
                if os.access(cand, os.W_OK):
                    return cand
            except Exception as e:
                self.logger.debug(f"[DEMO] 캡처 경로 생성 실패: {cand} ({e})")
        return None

    def _capture_demo(self, reason: str, delay_ms: int = 0, throttle_sec: float = 0.8):
        """데모 모드 캡처 트리거"""
        if not self.demo_capture_enabled or not self.demo_capture_dir:
            return

        def _fire():
            self._capture_demo_now(reason, throttle_sec=throttle_sec)

        try:
            delay = max(0, int(delay_ms))
        except Exception:
            delay = 0

        if delay > 0:
            try:
                threading.Timer(delay / 1000.0, _fire).start()
            except Exception:
                _fire()
        else:
            _fire()

    def _draw_cursor_on_image(self, img, screen_width: int, screen_height: int):
        """캡처 이미지 위에 커서 이미지를 합성한다"""
        try:
            from PIL import Image

            class POINT(ctypes.Structure):
                _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

            pt = POINT()
            ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))

            cursor_x, cursor_y = pt.x, pt.y

            if cursor_x < 0 or cursor_y < 0 or cursor_x >= screen_width or cursor_y >= screen_height:
                return img

            if not self._cursor_img:
                base_dir = Path(__file__).resolve().parent
                candidates = [
                    base_dir / "small_arrow.png",
                    base_dir / "cursor_arrow.png",
                ]
                for cand in candidates:
                    try:
                        if cand.exists():
                            self._cursor_img = Image.open(cand).convert("RGBA")
                            self._cursor_hotspot = (self._cursor_img.width // 2, max(0, self._cursor_img.height - 2))
                            self.logger.debug(f"[DEMO] 커서 로드: {cand}")
                            break
                    except Exception:
                        continue

            if not self._cursor_img:
                return img

            paste_x = cursor_x - self._cursor_hotspot[0]
            paste_y = cursor_y - self._cursor_hotspot[1]

            if paste_x >= screen_width or paste_y >= screen_height or paste_x + self._cursor_img.width <= 0 or paste_y + self._cursor_img.height <= 0:
                return img

            img.paste(self._cursor_img, (paste_x, paste_y), self._cursor_img)
            return img
        except Exception as e:
            self.logger.warning(f"[DEMO] 커서 그리기 실패: {e}")
            return img

    def _capture_demo_now(self, reason: str, throttle_sec: float = 0.8):
        """화면 캡처 실행"""
        if not self.demo_capture_enabled or not self.demo_capture_dir:
            return
        try:
            from PIL import ImageGrab
        except Exception as e:
            self.logger.warning(f"[DEMO] 캡처 불가 (필수 모듈 없음): {e}")
            self.demo_capture_enabled = False
            return

        now = time.perf_counter()
        if self._last_demo_capture_ts and (now - self._last_demo_capture_ts) < throttle_sec:
            return
        self._last_demo_capture_ts = now

        safe_reason = "".join(
            c if c.isalnum() or c in ("-", "_") else "_" for c in (reason or "event")
        )
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
        fname = f"demo_{ts}_{safe_reason}.png"
        path = self.demo_capture_dir / fname

        try:
            img = ImageGrab.grab()
            w, h = self.demo_capture_size
            cropped = img.crop((0, 0, w, h))
            cropped = self._draw_cursor_on_image(cropped, w, h)
            cropped.save(path, "PNG")
            self.logger.debug(f"[DEMO] capture saved ({safe_reason}): {path}")
        except Exception as e:
            self.logger.warning(f"[DEMO] capture failed ({safe_reason}): {e}")

    # ===== Print Logic (원본 print_DWG_with_tkinter.py 로직) =====
    def scan_dwg_files(self) -> List[str]:
        """DWG 파일 스캔"""
        if not self.folder_path or not os.path.isdir(self.folder_path):
            self.logger.error("폴더 경로가 유효하지 않습니다.")
            return []
        
        dwg_files = []
        try:
            for f in os.listdir(self.folder_path):
                if f.lower().endswith('.dwg'):
                    full_path = os.path.join(self.folder_path, f)
                    if os.path.isfile(full_path):
                        dwg_files.append(full_path)
            
            dwg_files.sort()
            self.logger.info(f"DWG 파일 {len(dwg_files)}개 발견")
            return dwg_files
        except Exception as e:
            self.logger.error(f"DWG 파일 스캔 실패: {e}")
            return []

    def print_dwg_files(self) -> Dict[str, Any]:
        """DWG 파일 일괄 인쇄 (원본 로직 기반)"""
        start_time = datetime.datetime.now()
        self.logger.info("DWG 일괄 인쇄 시작")

        if self.demo_capture_enabled:
            self._capture_demo("print_start", delay_ms=100, throttle_sec=0.0)

        dwg_files = self.scan_dwg_files()
        if not dwg_files:
            return {
                "success": False,
                "message": "DWG 파일을 찾을 수 없습니다.",
                "printed": 0,
                "failed": 0,
                "total": 0,
            }

        self.total_files = len(dwg_files)
        self.max_count = self.total_files
        self.current_file_index = 0
        printed_count = 0
        failed_files = []

        if not Application or not pgui:
            self.logger.error("필수 모듈 부재")
            return {
                "success": False,
                "message": "필수 모듈이 설치되지 않았습니다.",
                "printed": 0,
                "failed": len(dwg_files),
                "total": len(dwg_files),
            }

        if not os.path.exists(self.edrawings_path):
            self.logger.error(f"eDrawings를 찾을 수 없습니다: {self.edrawings_path}")
            return {
                "success": False,
                "message": "eDrawings 실행 파일을 찾을 수 없습니다.",
                "printed": 0,
                "failed": len(dwg_files),
                "total": len(dwg_files),
            }

        app_instance = None
        try:
            for i, dwg_file in enumerate(dwg_files):
                if self.stop_progress_flag:
                    self.logger.info("사용자 중단")
                    break

                self.current_file_index = i
                file_name = os.path.basename(dwg_file)
                self.logger.info(f"[{i+1}/{self.total_files}] {file_name} 인쇄 중...")

                if self.demo_capture_enabled:
                    self._capture_demo(f"print_file_{i+1}_{file_name}", delay_ms=50)

                try:
                    success = self._print_single_file(app_instance, i, dwg_file)

                    if success:
                        printed_count += 1

                        # 크레딧 차감
                        if self.credit_manager:
                            try:
                                credits = getattr(self.config, 'credits_per_print', 1)
                                result = self.credit_manager.deduct_credits_by_policy(
                                    credits, f"DWG 인쇄: {file_name}"
                                )
                                if result.get("success"):
                                    if self.credit_update_callback:
                                        self.credit_update_callback()
                                else:
                                    if getattr(self.config, 'check_shortage_stop', True):
                                        self.logger.error(f"크레딧 부족")
                                        break
                            except Exception as e:
                                self.logger.warning(f"크레딧 처리 오류: {e}")

                        if self.demo_capture_enabled:
                            self._capture_demo(f"print_done_{i+1}", delay_ms=80)

                        # 원본 로직: restart_count마다 eDrawings 재시작
                        if (i != 0 and (i + 1) % self.restart_count == 0):
                            self.logger.info(f"eDrawings 재시작 ({i+1}/{self.total_files})")
                            if app_instance:
                                try:
                                    app_instance.kill()
                                except Exception:
                                    pass
                            app_instance = None
                            time.sleep(self.restart_sleep)

                    else:
                        failed_files.append(file_name)
                        self.logger.error(f"인쇄 실패: {dwg_file}")

                    # 진행률 업데이트
                    self.update_progress(i + 1, self.total_files)

                except Exception as e:
                    self.logger.error(f"파일 처리 오류 ({dwg_file}): {e}")
                    failed_files.append(file_name)

        finally:
            # 마지막 파일 처리 후 eDrawings 종료 (원본 로직)
            if app_instance:
                try:
                    time.sleep(self.final_sleep)
                    app_instance.kill()
                except Exception:
                    pass
            
            if self.demo_capture_enabled:
                self._capture_demo("print_complete", delay_ms=150, throttle_sec=0.0)

        end_time = datetime.datetime.now()
        duration = (end_time - start_time).total_seconds()

        self.logger.info(f"DWG 인쇄 완료: 성공 {printed_count}개, 실패 {len(failed_files)}개")

        return {
            "success": True,
            "printed": printed_count,
            "failed": len(failed_files),
            "total": self.total_files,
            "duration": duration,
            "failed_files": failed_files,
        }

    def _print_single_file(self, app_instance, idx: int, dwg_file: str) -> bool:
        """단일 파일 인쇄 (원본 print_dwg_file 로직)"""
        try:
            file_path = os.path.join(str(self.folder_path), os.path.basename(dwg_file))
            self.logger.debug(f'{ctime()} {idx+1}/{self.max_count} {file_path}')

            # eDrawings 시작 (원본 로직)
            if not app_instance:
                app_instance = Application(backend='uia').start(
                    f'"{self.edrawings_path}" "{file_path}"'
                )
                self.logger.debug('eDrawings started')
                app_instance = app_instance.connect(title_re='eDrawings', timeout=10, found_index=0)
                self.logger.debug('eDrawings connected')

            # Ctrl+P로 인쇄 대화상자 열기
            pgui.hotkey('ctrl', 'p')
            dlg = app_instance.top_window()
            dlg.wait('enabled')

            # 취소 버튼 클릭 (원본 로직: 취소 버튼을 클릭하면 인쇄가 완료됨)
            try:
                cancel_btn = dlg.child_window(title='취소', control_type='Button')
                cancel_btn.wait('enabled', timeout=self.wait_timeout)
                cancel_btn.click()
                self.logger.debug(f'인쇄 완료: {os.path.basename(dwg_file)}')
            except Exception as e:
                self.logger.warning(f"취소 버튼 클릭 실패: {e}")

            # 인쇄 대화상자가 사라질 때까지 대기
            dlg.wait('enabled', timeout=5)

            # 마지막 파일인 경우 eDrawings 종료 (원본 로직)
            if idx == self.max_count - 1:
                self.logger.debug('마지막 파일 처리 완료')
                time.sleep(self.final_sleep)
                app_instance.kill()
                app_instance = None

            return True

        except Exception as e:
            self.logger.error(f"인쇄 실패 ({dwg_file}): {e}")
            return False

    def update_progress(self, current: int, total: int):
        """진행률 업데이트"""
        if self.demo_capture_enabled:
            self._capture_demo(f"progress_{current}of{total}", delay_ms=80)
        
        if self.progress_callback:
            try:
                self.progress_callback(current, total)
            except Exception as e:
                self.logger.error(f"진행률 콜백 오류: {e}")
