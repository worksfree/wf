# -*- coding: utf-8 -*-
"""
Bom Exporter Automation
솔리드웍스 자동화 핵심 로직과 Non-UI 모드 실행 담당
"""

import sys
import os
import argparse
import gc
import time
import logging
import math
from pathlib import Path

# D:\drive_files\10.worksfree\10.rpa\10.common\wf_log.py
# 현재 스크립트의 디렉토리를 Python 경로에 추가
current_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(current_dir))

# 기존 utils 경로 추가 (원본 코드와 호환성 유지)
utils_path = current_dir.parent.parent / "10.common"
# Debug: Uncomment for development debugging
# print(f'utils_path: {utils_path}')
if utils_path.exists():
    sys.path.append(str(utils_path))
    # Debug: Uncomment for development debugging
    # print(f'utils 경로 추가 성공: {utils_path}')
else:
    # Debug: Uncomment for development debugging
    # print(f'utils 경로를 찾을 수 없습니다: {utils_path}')
    pass

# COM 초기화 (pywinauto와 tkinter.filedialog의 COM 충돌 방지)
# pywinauto는 SolidWorks 자동화를 위해 COM을 사용하며,
# tkinter.filedialog도 Windows 파일 다이얼로그를 위해 COM 필요.
# 두 라이브러리가 같은 스레드 모드로 COM을 초기화하도록 설정.
# 2 = COINIT_APARTMENTTHREADED (단일 스레드 아파트먼트 모드)
sys.coinit_flags = 2

# 필요한 모듈들 import
import json
import time
import ctypes
import keyboard
import openpyxl
import pyperclip
import pyautogui
import logging
import psutil  # 메모리 모니터링용
import datetime
from tqdm import trange
from pywinauto.application import Application
from pywinauto import findwindows
from collections import deque

# 로컬 모듈 import
from app_setting_data import get_config
# 파일 리스트업 로직은 안정성을 위해 로컬에서 처리 (헬퍼 미사용)

# utils 모듈들 (기존 경로에서 import)
try:
    import wf_log as wflog
    import wf_license as wflic
    import wf_email as wfm
    import wf_gen_code as wfgc
    import wf_hwinfo
except ImportError as e:
    # Import error will be handled by logger after initialization
    import sys

    # 모듈 로딩 시점에는 아직 logger가 없으므로 print 사용
    print(f"common 모듈 import 실패: {e}", file=sys.stderr)
    print("기존 common 경로가 올바른지 확인해주세요.", file=sys.stderr)
    sys.exit(1)


class LicenseManager:
    """라이선스 관리 클래스"""

    def __init__(self, app_instance):
        self.app = app_instance
        self.config = get_config()

    def check_trial_status(self):
        """체험판 상태 확인"""
        # wf_rpa_config.json 파일의 존재 여부로 등록 상태를 판단.
        # 파일이 있으면 등록된 사용자(체험판 아님), 없으면 미등록 사용자(체험판)
        try:
            from pathlib import Path, PurePath
            import json

            config_file = Path.home() / ".wf_rpa" / "wf_rpa_config.json"
            trial_mode = True  # 기본은 체험판
            if config_file.exists():
                try:
                    with open(config_file, "r", encoding="utf-8") as f:
                        data = json.load(f) or {}
                    user_info = data.get("user_info", {})
                    # 통합 정책: is_registered True 이거나 reg_time_local 값 존재 시 등록으로 간주
                    if user_info.get("is_registered") is True or user_info.get("reg_time_local"):
                        trial_mode = False
                except Exception as ie:
                    self.app.logger.warning(f"wf_rpa_config.json 파싱 실패(무시): {ie}")
            self.app.logger.debug(f"사용자 trial_mode 여부: {trial_mode}")
            return trial_mode
        except Exception as e:
            self.app.logger.error(f"등록 상태 확인 중 오류 발생: {e}")
            return True  # 오류 시 안전하게 체험판 처리


class BomAutomation:
    """BOM 자동화 핵심 클래스"""

    # ===== 배포 설정 =====
    # Non-UI 모드에서 라이선스 체크 여부
    # 개발/테스트: False (라이선스 체크 비활성화)
    # 배포 버전: True (라이선스 체크 활성화)
    ENABLE_LICENSE_CHECK_IN_CONSOLE = False

    def __init__(self, folder_path=None, console_mode=True, ignore_processed_for_rerun=False, only_count_new_duplicates=False):
        # 설정 로드
        self.config = get_config()
        self.run_mode = getattr(self.config, "run_mode", "release")
        # 자동 캡처 비활성화: Alt+C, Alt+G 수동 캡처만 사용
        self.demo_capture_enabled = False
        
        # 데모 모드 동영상 녹화용 설정
        self.demo_video_mode = self.run_mode == "demo"
        self.demo_pause_after_click = 3.0  # 클릭 후 대기 시간 (초)
        self.demo_pause_after_dialog = 2.0  # 다이얼로그 후 대기 시간 (초)
        self.demo_capture_dir = None
        self.demo_capture_size = (1920, 1040)
        self._last_demo_capture_ts = 0.0
        
        # 재실행 관련 플래그 (UI에서 전달됨)
        self.ignore_processed_for_rerun = ignore_processed_for_rerun
        self.only_count_new_duplicates = only_count_new_duplicates

        # 1. 기본 경로 및 설정 초기화
        self.itself = str(Path(__file__).resolve())
        self.itself_dir = str(Path(__file__).resolve().parent)
        self.current_dir = str(Path.cwd())
        self.console_mode = console_mode

        # Console mode 진행 표시 관련 초기화
        self._console_last_print_time = 0
        self._console_print_interval = 0.5  # 0.5초마다 업데이트 (너무 빠르면 터미널이 느려짐)

        # 2. 글로벌 싱글톤 로거 초기화
        console_level = logging.DEBUG if self.config.SHOW_DEBUG else logging.INFO
        self.logger = wflog.get_app_logger("bom_exporter", console_level=console_level)
        # 공통 모듈에 로거 주입하여 동일 로거 사용
        try:
            if hasattr(wfm, "set_logger"):
                wfm.set_logger(self.logger)
        except Exception:
            pass
        try:
            if hasattr(wflic, "set_logger"):
                wflic.set_logger(self.logger)
        except Exception:
            pass

        # 로그 파일 경로 정보 저장 (기존 코드와 호환성 유지)
        # 개발/배포 모드에 따라 동적 설정
        import sys

        is_dev_mode = sys.argv[0].endswith(".py")
        if is_dev_mode:
            log_dir_path = Path(self.itself_dir) / "logs"
        else:
            log_dir_path = Path.home() / ".wf_rpa" / "bom_exporter" / "logs"
        self.log_dir = str(log_dir_path).replace("\\", "/")
        self.logfile = str(log_dir_path / f"{time.strftime('%Y%m%d')}.txt").replace("\\", "/")

        if self.demo_capture_enabled:
            self._init_demo_capture()

        # 최초 1회만 로그 출력
        if not hasattr(self.__class__, "_logger_initialized"):
            self.logger.info(f'App Started : {self.itself} \n {"="*60}')
            setattr(self.__class__, "_logger_initialized", True)

        # 클래스 초기화 로그
        self.logger.debug(
            f"BomAutomation class initialized with folder_path={folder_path}, console_mode={console_mode}"
        )

        # 3. 시스템 정보 및 하드웨어 정보 수집
        self.hw_info = wf_hwinfo.HardwareInfo()
        self.hardware_fingerprint = self.hw_info.fingerprint
        self.logger.debug(f"하드웨어 지문: {self.hardware_fingerprint[:16]}...")
        self.logger.debug(f"현재 앱 파일의 이름 : {self.itself}")
        self.logger.debug(f"현재 앱 파일이 있는 경로 : {self.itself_dir}")
        self.logger.debug(f"현재 앱 실행 경로 : {self.current_dir}")

        # 4. 라이선스 및 체험판 관리 초기화
        self.init_license_management()

        # 5. 애플리케이션 설정 초기화
        self.wait_time = self.config.wait_time
        self.my_pace = self.config.my_pace
        self.Solidworks_App = None
        # pywinauto backend 설정 (uia | win32)
        self.pywinauto_backend = getattr(self.config, "pywinauto_backend", "uia")
        # self.pywinauto_backend = getattr(self.config, 'pywinauto_backend', 'win32')

        # 6. 작업 관련 변수 초기화
        self.SLDDRW_PATH = None
        self.stop_progress_flag = False
        self.restart_count = self.config.restart_count
        self.restart_count_offset = 0  # 메모리 재시작 시 주기적 재시작 카운터 조정용
        self.total_count = 0  # 처리할 파일 개수 (남은 파일만)
        self.total_count_original = 0  # 전체 파일 개수 (처리된 파일 포함)
        self.processed_files = set()  # 이미 처리된 파일 집합 (stem 기준)
        self.remain = 0
        self.sldprt_files = []
        self.sldprt_files_to_process = []
        self.sldprt_files_missed = []
        self.credit_shortage_stop = False
        self.files_processed_before_stop = 0

        # 7. 폴더 경로 초기화 (생성자 인자 우선)
        self.folder_path = folder_path  # 생성자에서 받은 folder_path 사용
        self.logger.debug(f"BomAutomation initialized with folder_path: {self.folder_path}")

        # 8. BOM 관련 설정
        self.EXCEL2BOM_DIR = ""
        self.WORK_DIR = ""

        # 9. SolidWorks 설정 로드 (JSON에서)
        self.solidworks_settings = self.config.get_solidworks_settings()
        self.logger.debug(f"SolidWorks 설정: {self.solidworks_settings}")
        # 9.5. 타임아웃 및 복구 관련 기본값
        # timeout_mode: 'auto' | 'manual' - auto: 계산된 동적 타임아웃 사용, manual: 기존 self.wait_time 사용
        self.timeout_mode = getattr(self.config, "timeout_mode", "auto")
        # soft retry 횟수 (같은 단계에서의 빠른 재시도)
        self.soft_retries = getattr(self.config, "soft_retries", 2)
        # 연속 타임아웃 발생 시 재시작 임계치
        self.consec_timeout_limit = getattr(self.config, "consec_timeout_limit", 2)
        # 연속 타임아웃 카운터
        self.consec_timeouts = 0

        # 메모리 모니터링 설정 (기본값: 가용 메모리 20% 이하면 경고)
        self.memory_threshold_percent = getattr(self.config, "memory_threshold_percent", 20)
        self.enable_memory_monitor = getattr(self.config, "enable_memory_monitor", True)

        # 10. 콘솔 모드 초기화
        self.init_console_mode()

        # 11. UI 진행률 업데이트 콜백 초기화
        self.progress_callback = None  # UI에서 설정될 콜백 함수

        # 11.5. 크레딧 UI 업데이트 콜백 초기화
        self.credit_update_callback = None
        
        # 11.6. 데모 캡처 콜백 초기화
        self.capture_callback = None

        # 11.6. 파일 처리 시작 콜백 (스피너 시작용)
        self.file_processing_start_callback = None

        # 12. 크레딧 매니저 초기화
        self.credit_manager = None  # UI에서 설정될 크레딧 매니저

        # 전역 중단/알림 플래그
        self.abort_all = False
        self.fatal_email_sent = False

        # 13. 반복 크래시 중단 가드 설정 (짧은 시간 내 다수 크래시 시 전체 중단)
        self.crash_timestamps = deque(maxlen=20)
        self.crash_abort_threshold = getattr(
            self.config, "crash_abort_threshold", 3
        )  # 예: 120초 내 3회
        self.crash_window_seconds = getattr(self.config, "crash_window_seconds", 120)

    # 치명적 솔리드웍스 오류 예외 (필요 시 사용)
    class FatalSolidWorksError(Exception):
        pass

    def init_license_management(self):
        """라이선스 및 체험판 관리 초기화"""
        self.user_email = ""
        self.report_email = ""
        self.expiry_date = ""

        # 체험판 여부 확인
        self.license_manager = LicenseManager(self)
        self.is_trial_version = self.license_manager.check_trial_status()

    def set_progress_callback(self, callback_func):
        """UI 진행률 업데이트 콜백 설정"""
        self.progress_callback = callback_func
        # self.logger.debug(f'Progress callback function set: {callback_func}')

    def set_credit_update_callback(self, callback_func):
        """UI 크레딧 표시 업데이트 콜백 설정"""
        self.credit_update_callback = callback_func
        # self.logger.debug(f'Credit update callback function set: {callback_func}')

    def set_file_processing_start_callback(self, callback_func):
        """파일 처리 시작 콜백 설정 (스피너 시작용)"""
        self.file_processing_start_callback = callback_func
        # self.logger.debug(f'File processing start callback function set: {callback_func}')

    def set_credit_manager(self, credit_manager):
        """크레딧 매니저 설정"""
        self.credit_manager = credit_manager
        # self.logger.debug('Credit manager set for BOM automation')
    
    def set_capture_callback(self, callback_func):
        """데모 캡처 콜백 설정"""
        self.capture_callback = callback_func

    def has_credit_shortage_interruption(self) -> bool:
        """크레딧 부족으로 중단된 기록이 있는지 확인
        wf_pending_list.txt 파일이 존재하면 크레딧 부족으로 중단된 상태"""
        if not self.folder_path:
            return False
        try:
            from pathlib import Path
            pending_path = Path(self.folder_path) / "wf_pending_list.txt"
            return pending_path.exists()
        except Exception:
            return False

    def count_exported_files(self) -> int:
        """exported_bom 폴더의 엑셀 파일 개수 반환"""
        if not self.folder_path:
            return 0
        try:
            from pathlib import Path
            export_folder = Path(self.folder_path) / "exported_bom"
            if export_folder.exists() and export_folder.is_dir():
                return sum(1 for f in export_folder.rglob("*.xls*") if f.is_file())
            return 0
        except Exception:
            return 0

    # ===== 데모 캡처 헬퍼 (자동/정상 플로우용) =====
    def _init_demo_capture(self):
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
        candidates = [
            Path(__file__).resolve().parent / "demo_captures",
            Path.home() / ".wf_rpa" / "bom_exporter" / "demo_captures",
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
        if not self.demo_capture_enabled or not self.demo_capture_dir:
            return

        try:
            delay = max(0, int(delay_ms))
        except Exception:
            delay = 0

        if delay:
            try:
                time.sleep(delay / 1000)
            except Exception:
                pass

        self._capture_demo_now(reason, throttle_sec=throttle_sec)

    def _capture_demo_now(self, reason: str, throttle_sec: float = 0.8):
        """수동 캡처용 메서드 (Alt+C, Alt+G에서 호출)"""
        if not self.demo_capture_dir:
            return
        try:
            import time as _t
            from PIL import ImageGrab
        except Exception as e:
            self.logger.warning(f"[DEMO] 캡처 불가 (필수 모듈 없음): {e}")
            return

        now = _t.perf_counter()
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
            cropped.save(path, "PNG")
            self.logger.debug(f"[DEMO] capture saved ({safe_reason}): {path}")
        except Exception as e:
            self.logger.warning(f"[DEMO] capture failed ({safe_reason}): {e}")

    def update_progress(self, current, total, status_text=""):
        """진행률 업데이트 (UI 모드와 Console 모드 모두 지원)"""
        # UI 모드: 콜백 함수 호출
        if self.progress_callback:
            try:
                self.progress_callback(current, total, status_text)
            except Exception as e:
                self.logger.error(f"Progress callback 실행 중 오류: {e}")

        self._capture_demo("progress_update", throttle_sec=0.8, delay_ms=50)

        # Console 모드: 터미널에 진행 상태 출력
        if self.console_mode:
            self._print_console_progress(current, total, status_text)

    def _print_console_progress(self, current, total, status_text=""):
        """Console 모드에서 진행 상태를 터미널에 출력"""
        import sys
        import time

        # 너무 자주 출력하지 않도록 throttling (0.5초마다)
        current_time = time.time()
        if current_time - self._console_last_print_time < self._console_print_interval:
            # 단, 마지막 항목이거나 첫 번째 항목은 항상 출력
            if current != 0 and current != total:
                return

        self._console_last_print_time = current_time

        # 진행률 계산
        percentage = (current / total * 100) if total > 0 else 0

        # 프로그레스 바 생성 (40칸)
        bar_length = 40
        filled_length = int(bar_length * current / total) if total > 0 else 0
        bar = "█" * filled_length + "░" * (bar_length - filled_length)

        # 상태 텍스트 줄바꿈 없이 출력 (같은 줄 업데이트)
        # \r로 커서를 줄 처음으로 이동, end=''로 줄바꿈 방지
        output = f"\r📊 진행: [{bar}] {current}/{total} ({percentage:.1f}%)"

        if status_text:
            # 상태 텍스트가 너무 길면 자르기 (터미널 너비 고려)
            max_status_len = 50
            if len(status_text) > max_status_len:
                status_text = status_text[: max_status_len - 3] + "..."
            output += f" | {status_text}"

        # 터미널 너비보다 길면 잘라내기
        try:
            import shutil

            terminal_width = shutil.get_terminal_size().columns
            if len(output) > terminal_width:
                output = output[: terminal_width - 3] + "..."
        except:
            # 터미널 크기를 가져올 수 없는 경우 무시
            pass

        # 출력 (같은 줄에 덮어쓰기)
        sys.stdout.write(output)
        sys.stdout.flush()

        # 마지막 항목이면 줄바꿈
        if current >= total:
            sys.stdout.write("\n")
            sys.stdout.flush()

    def init_console_mode(self):
        """콘솔 모드 초기화"""
        try:
            from pathlib import Path
            import json

            # 수정된 경로: .wf_rpa 폴더 내의 wf_rpa_config.json
            config_file = Path.home() / ".wf_rpa" / "wf_rpa_config.json"

            if config_file.exists():
                with open(config_file, "r", encoding="utf-8") as f:
                    config = json.load(f)

                # 사용자 이메일 (user_info.user_email 에서 가져오기)
                self.user_email = config.get("user_info", {}).get("user_email", "")

                # 리포트 수신 이메일 (email_settings.email_to 에서 가져오기)
                # email_settings는 관리자 이메일 설정을 담고 있음
                email_settings = config.get("email_settings", {})
                self.report_email = email_settings.get("email_to", "")

                # report_email이 없으면 user_email로 폴백
                if not self.report_email:
                    self.logger.warning(
                        "email_settings.email_to가 설정되지 않아 user_email을 사용합니다."
                    )
                    self.report_email = self.user_email

            else:
                self.logger.warning(f"설정 파일이 없습니다: {config_file}")
                # 설정 파일이 없으면 wfm.init()이 자동으로 로드할 수 있도록 빈 값 설정
                self.user_email = ""
                self.report_email = ""

        except Exception as e:
            self.logger.warning(f"로컬 설정 파일 읽기 실패: {e}")
            # 에러 발생 시에도 wfm.init()이 자동으로 로드하도록 빈 값 설정
            self.user_email = ""
            self.report_email = ""

        self.logger.debug(f"최종 이메일 설정:")
        self.logger.debug(f"  user_email: {self.user_email}")
        self.logger.debug(f"  report_email: {self.report_email}")

    def handle_error(self, error, context="", mail_title_prefix="[B2E] [Error]", send_email=True):
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

        # 화면 해상도가 아직 초기화되지 않은 경우 전체 화면 캡처
        if (
            hasattr(self, "width")
            and hasattr(self, "height")
            and self.width > 0
            and self.height > 0
        ):
            self.screenshot = pyautogui.screenshot(region=(0, 0, self.width, self.height))
        else:
            self.screenshot = pyautogui.screenshot()  # 전체 화면 캡처

        self.logger.debug("스크린샷 찍기 완료")
        screenshot_path = Path(self.log_dir) / f"{timestamp4img}.png"
        self.screenshot.save(str(screenshot_path))
        self.logger.debug(f"스크린샷 png 파일 저장 완료: {screenshot_path}")

        # 이메일 전송
        if send_email:
            error_content = f"{str(error)}"
            if context:
                error_content = f"{error_content}\n{context}"

            attach = [str(screenshot_path).replace("\\", "/"), self.logfile]
            try:
                wfm.init(self.itself_dir)
                mail_title = f"{mail_title_prefix} {self.user_email}"
                wfm.mail_send_attach(mail_title, self.report_email, error_content, attach)
                self.logger.debug("에러 이메일 전송 완료")
            except Exception as mail_e:
                self.logger.error(f"에러 이메일 전송 실패 (프로그램은 계속 진행): {mail_e}")

        return str(screenshot_path), timestamp4img

    def _send_fatal_email(self, title: str, content: str):
        """치명적 오류(예: 솔리드웍스 시작/연결 실패) 단일 알림 메일 전송"""
        try:
            wfm.init(self.itself_dir)
            # 첨부: 최신 로그 파일만 전송
            attach = [self.logfile]
            wfm.mail_send_attach(title, self.report_email or "", content, attach)
            self.logger.info("치명적 오류 메일 전송 완료")
        except Exception as mail_e:
            self.logger.error(f"치명적 오류 메일 전송 실패: {mail_e}")

    def _sanity_check_solidworks(self) -> bool:
        """사전 점검: SolidWorks 시작/연결 가능 여부 확인. 실패 시 단일 메일 전송 후 전체 중단."""
        try:
            ok = self._safe_solidworks_restart()
        except Exception as e:
            self.logger.error(f"사전 점검 중 예외: {e}")
            ok = False

        if not ok:
            reason = "SolidWorks 시작/연결 사전 점검 실패 - 작업을 중단합니다."
            self.logger.error(reason)
            if not getattr(self, "fatal_email_sent", False):
                try:
                    self._send_fatal_email("[B2E] Fatal - SolidWorks sanity check failed", reason)
                except Exception:
                    pass
                self.fatal_email_sent = True
            self.abort_all = True
            return False
        return True

    def _increment_consec_and_maybe_restart(self, reason="timeout"):
        """연속 타임아웃 카운터 증가, 임계치 도달 시 안전 재시작 수행"""
        try:
            self.consec_timeouts += 1
            self.logger.warning(
                f"연속 타임아웃 증가: {self.consec_timeouts}/{self.consec_timeout_limit} (원인: {reason})"
            )
            if self.consec_timeouts >= self.consec_timeout_limit:
                self.logger.warning("연속 타임아웃 임계치 도달 - 안전한 솔리드웍스 재시작 시도")
                try:
                    self._safe_solidworks_restart()
                except Exception as e:
                    self.logger.error(f"안전 재시작 실패: {e}")
                finally:
                    # 재시작 이후 카운터 리셋
                    self.consec_timeouts = 0
        except Exception as e:
            self.logger.error(f"_increment_consec_and_maybe_restart 중 오류: {e}")

    def _compute_wait(self, file_size_bytes: int) -> int:
        """파일 크기 기반 단일 대기시간 계산기.

        계산식: base_wait_time + floor(file_size_mb/10) * seconds_per_10mb
        예) 9MB=120+0*60=120, 29MB=120+2*60=240, 91MB=120+9*60=660
        """
        try:
            base_timeout = int(getattr(self.config, "base_wait_time", 120))
            seconds_per_10mb = int(getattr(self.config, "seconds_per_10mb", 60))
            file_size_mb = file_size_bytes / (1024 * 1024)
            wait_time = int(base_timeout + math.floor(file_size_mb / 10) * seconds_per_10mb)
            self.logger.debug(
                f"Computed wait: file_size_mb={file_size_mb:.2f}, wait_time={wait_time}"
            )
            return wait_time
        except Exception as e:
            self.logger.error(f"wait 계산 중 오류: {e} - 폴백으로 base_wait_time 사용")
            return int(getattr(self.config, "base_wait_time", 120))

    def _compute_waits(self, file_size_bytes: int):
        """UI 대기와 저장 대기 시간을 함께 계산해 반환합니다.

        Returns:
            tuple[int, int]: (ui_wait_seconds, save_wait_seconds)
        """
        try:
            ui_wait = self._compute_wait(file_size_bytes)
            multiplier = int(getattr(self.config, "file_save_wait_multiplier", 2))
            save_wait = int(ui_wait * multiplier)
            self.logger.debug(
                f"Computed waits: ui={ui_wait}s, save={save_wait}s (multiplier={multiplier})"
            )
            return ui_wait, save_wait
        except Exception as e:
            self.logger.debug(f"_compute_waits 실패(폴백): {e}")
            ui_wait = int(getattr(self.config, "base_wait_time", 120))
            multiplier = int(getattr(self.config, "file_save_wait_multiplier", 2))
            return ui_wait, int(ui_wait * multiplier)

    def _record_crash_and_should_abort(self) -> bool:
        """솔리드웍스 크래시 발생을 기록하고, 단시간 내 반복 크래시이면 전체 중단 여부를 반환"""
        try:
            now = time.time()
            self.crash_timestamps.append(now)
            window_start = now - float(self.crash_window_seconds)
            recent = [t for t in self.crash_timestamps if t >= window_start]
            count = len(recent)
            self.logger.debug(
                f"최근 {self.crash_window_seconds}s 내 크래시 횟수: {count}/{self.crash_abort_threshold}"
            )
            if count >= int(self.crash_abort_threshold):
                reason = f"반복 크래시 감지: {self.crash_window_seconds}초 내 {count}회 발생 → 전체 작업 중단"
                self.logger.error(reason)
                try:
                    self._send_fatal_email("[B2E] Fatal - Repeated SolidWorks crashes", reason)
                except Exception:
                    pass
                self.abort_all = True
                return True
        except Exception as e:
            self.logger.debug(f"_record_crash_and_should_abort 처리 중 경고(무시): {e}")
        return False

    def _check_memory_and_maybe_restart(self):
        """
        메모리 상태 체크 후 필요시 선제적 SolidWorks 재시작

        Returns:
            bool: True if 재시작 수행됨, False otherwise
        """
        if not self.enable_memory_monitor:
            return False

        try:
            # 시스템 가용 메모리 체크
            mem = psutil.virtual_memory()
            available_percent = 100 - mem.percent

            if available_percent < self.memory_threshold_percent:
                # 메모리 부족 감지
                self.logger.warning(
                    f"⚠️ 메모리 부족 감지! "
                    f"가용 메모리: {round(mem.available / (1024**3), 2)}GB ({available_percent:.1f}%) "
                    f"< 임계치 {self.memory_threshold_percent}% "
                    f"→ 선제적 SolidWorks 재시작 수행"
                )

                # SolidWorks 메모리 사용량도 로그
                try:
                    for proc in psutil.process_iter(["name", "memory_info"]):
                        if proc.info["name"] == "SLDWORKS.exe":
                            sw_mem_gb = round(proc.info["memory_info"].rss / (1024**3), 2)
                            self.logger.info(f"SolidWorks 메모리 사용량: {sw_mem_gb}GB")
                            break
                except:
                    pass

                # 안전한 재시작 수행
                restart_success = self._safe_solidworks_restart()
                if restart_success:
                    self.logger.info("✅ 메모리 확보를 위한 재시작 완료")
                    # 재시작 후 메모리 상태 재확인
                    time.sleep(2)
                    gc.collect()  # 파이썬 가비지 컬렉션도 수행
                    mem_after = psutil.virtual_memory()
                    self.logger.info(
                        f"재시작 후 메모리: "
                        f"가용 {round(mem_after.available / (1024**3), 2)}GB ({100 - mem_after.percent:.1f}%)"
                    )
                else:
                    self.logger.error("❌ 메모리 확보 재시작 실패")

                return restart_success
            else:
                # 메모리 정상
                self.logger.debug(
                    f"메모리 상태 정상: "
                    f"가용 {round(mem.available / (1024**3), 2)}GB ({available_percent:.1f}%)"
                )
                return False

        except Exception as e:
            self.logger.error(f"메모리 체크 중 오류 (체크 무시): {e}")
            return False

    def check_resolution(self):
        """화면 해상도 확인"""
        self.width, self.height = pyautogui.size()
        self.logger.debug(f"Display width is {self.width} and height is {self.height}")
        return self.config.check_resolution(self.width)

    def is_caps_lock_on(self):
        """Caps Lock 상태 확인"""
        self.logger.info("CAPs lock이 On 되어 있음")
        return ctypes.windll.user32.GetKeyState(0x14) & 1

    def caps_lock_off(self):
        """CAPS LOCK 해제"""
        state = ctypes.WinDLL("User32.dll").GetKeyState(0x14)
        if not state:
            self.logger.info("CAPs lock이 ON되어 있어 OFF 처리 하였습니다.")
            keyboard.press_and_release("caps lock")
        else:
            self.logger.info("CAPs lock이 OFF되어 있습니다.")
            keyboard.press_and_release("caps lock")

    def check_license(self):
        """라이선스 체크"""
        self.logger.debug(f"하드웨어 지문: {self.hardware_fingerprint[:16]}...")
        # 설정에서 사용자 정보가 없으면 다시 로드
        if not self.user_email:
            self.user_email = self.config.user_email
        if not self.report_email:
            self.report_email = self.config.report_email

        # 새로운 하드웨어 지문 기반 라이선스 체크 시도
        try:
            check_license = wflic.check_license_with_hwid(
                self.user_email, self.hardware_fingerprint, self.logger
            )
        except AttributeError:
            # 기존 MAC 기반 시스템으로 폴백
            check_license = wflic.check_license(self.user_email, self.hw_info.cpu_id, self.logger)
        except Exception as e:
            self.logger.error(f"라이선스 체크 오류: {e}")
            check_license = "N"

        self.logger.debug(f"라이선스 체크 결과: {check_license}")

        if check_license != "Y":
            self.logger.error(
                f"라이선스가 유효하지 않습니다. 개발자(insung.lee1973@gmail.com)에게 문의하세요."
            )
            return False
        return True

    def _is_dev_mode(self) -> bool:
        try:
            if getattr(self.config, "run_mode", "release") == "dev":
                return True
        except Exception:
            pass
        try:
            return sys.argv[0].endswith(".py")
        except Exception:
            return False

    def _compute_work_dir(self, folder_path: str):
        """작업 폴더명을 결정하고 설정 (모드별)
        - dev: BOM_YYYYMMDD_HHMMSS (항상 새 폴더)
        - release/demo: 항상 bom (기존 폴더 재사용, 새 번호 미부여)
        """
        base = Path(folder_path)
        mode = getattr(self.config, "run_mode", "release")

        if mode == "dev":
            name = f'BOM_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}'
            work_dir_path = base / name
        else:  # release, demo
            name = "bom"
            work_dir_path = base / name

        self.EXCEL2BOM_DIR = name
        self.WORK_DIR = str(work_dir_path).replace("\\", "/")

    def process_folder(self, folder_path, scan_only=False):
        """폴더 처리 - 콘솔 모드 또는 스캔 전용"""
        self.logger.debug(f"{folder_path} 폴더를 대상으로 BOM 엑셀 저장을 시작합니다.")
        if not folder_path:
            self.logger.warning("폴더 경로가 None입니다.")
            return

        self.SLDDRW_PATH = folder_path
        self.logger.debug(f"선택한 폴더: {self.SLDDRW_PATH}")

        # 작업 폴더명 결정 (DEV: 타임스탬프, RELEASE: bom)
        self._compute_work_dir(folder_path)
        self.logger.debug(f"작업 폴더: {self.WORK_DIR}")

        # 우선 pending 목록(wf_pending_list.txt) 확인
        pending_path = Path(folder_path) / "wf_pending_list.txt"
        pending_names: list[str] = []
        if pending_path.exists():
            try:
                with open(pending_path, "r", encoding="utf-8") as f:
                    pending_names = [line.strip() for line in f if line.strip()]
                self.logger.info(
                    f"재개 가능한 목록 감지: {len(pending_names)}개 (wf_pending_list.txt)"
                )
            except Exception as e:
                self.logger.warning(f"wf_pending_list.txt 읽기 실패(무시): {e}")

        # Check if there are any ~00.slddrw files in the folder (또는 pending 목록 기반)
        try:
            folder_path_obj = Path(folder_path)
            found_files = []

            if pending_names:
                for name in pending_names:
                    p = folder_path_obj / name
                    if p.exists() and p.suffix.lower() == ".slddrw":
                        found_files.append(name)
            else:
                # 1) 기본 규칙: not '~', len>18, name[15:]에 '-00', 확장자 .slddrw
                primary = []
                for f in folder_path_obj.iterdir():
                    if (
                        f.is_file()
                        and not f.name.lower().startswith("~")
                        and len(f.name) > 18
                        and "-00" in f.name[15:].lower()
                        and f.suffix.lower() == ".slddrw"
                    ):
                        primary.append(f.name)

                if primary:
                    found_files = sorted(primary)
                else:
                    # 2) 폴백 규칙: 파일명이 '-00.slddrw'로 끝나고 '~'로 시작하지 않음
                    fallback = [
                        f.name
                        for f in folder_path_obj.iterdir()
                        if f.is_file()
                        and f.name.lower().endswith("-00.slddrw")
                        and not f.name.lower().startswith("~")
                    ]
                    found_files = sorted(fallback)

            self.sldprt_files = found_files
            self.logger.debug(f"폴더 내 ~00.slddrw 파일 개수: {len(self.sldprt_files)}")
        except Exception:
            error_msg = f"{folder_path}을 찾을 수 없습니다. 경로 설정을 다시 해 주세요."
            self.logger.error(error_msg)
            return

        self.logger.debug(f"전체 도면 파일은 {len(self.sldprt_files)}개 입니다.")

        if self.sldprt_files:
            # 기존 BOM 폴더가 있는 경우 처리된 파일 확인 (재실행시)
            work_dir_path = Path(self.WORK_DIR)
            if work_dir_path.exists():
                existing_excel_files = list(work_dir_path.glob("*.xlsx"))
                
                # 기존 엑셀 파일이 있으면 덮어쓰기 확인
                if existing_excel_files:
                    from tkinter import messagebox
                    response = messagebox.askyesno(
                        "기존 파일 덮어쓰기",
                        f"BOM 폴더에 {len(existing_excel_files)}개의 엑셀 파일이 이미 존재합니다.\n\n"
                        "덮어쓰기를 진행하시겠습니까?\n\n"
                        "예: 기존 파일을 덮어쓰고 BOM 추출 시작\n"
                        "아니오: 작업 취소"
                    )
                    if not response:
                        self.logger.info("사용자가 덮어쓰기를 취소했습니다.")
                        return
                    else:
                        self.logger.info("사용자가 덮어쓰기를 승인했습니다. BOM 추출을 시작합니다.")
                
                # 이미 처리된 파일 집합 저장 (재실행 감지용)
                self.processed_files = {
                    f.stem for f in work_dir_path.iterdir() if f.suffix.lower() == ".xlsx"
                }
                self.sldprt_files_to_process = [
                    f for f in self.sldprt_files if Path(f).stem not in self.processed_files
                ]
            else:
                self.processed_files = set()
                self.sldprt_files_to_process = self.sldprt_files

            # 파일 크기를 기반으로 정렬
            folder_path_obj = Path(folder_path)
            file_info = [
                (f, (folder_path_obj / f).stat().st_size) for f in self.sldprt_files_to_process
            ]
            file_info.sort(key=lambda x: x[1])
            self.sldprt_files_to_process = file_info

            self.logger.debug(
                f"작업 대상 도면 파일은 {len(self.sldprt_files_to_process)}개 입니다."
            )
            if self.sldprt_files_to_process:
                self.logger.debug(
                    f"First file: {self.sldprt_files_to_process[0][0]} "
                    f"({self.sldprt_files_to_process[0][1]:,} bytes)"
                )

            # Get file count
            self.total_count_original = len(self.sldprt_files)  # 전체 파일 개수
            self.total_count = len(self.sldprt_files_to_process)  # 처리할 파일 개수
            if self.total_count == 0:
                warning_msg = (
                    "선택한 폴더에 있는 모든 어셈블리 파일은 이미 BOM이 저장되어 있습니다."
                    "BOM을 다시 저장하려면 엑셀 파일을 모두 지우고 다시 폴더를 지정하세요."
                )
                self.logger.warning(warning_msg)
                return

            # scan_only가 False일 때만 (즉, 실제 처리 시에만) BOM 추출 시작
            if not scan_only:
                self.open_sldprt_files()

        else:
            # No files found
            error_msg = "선택한 폴더에는 ~00.slddrw 파일이 존재하지 않습니다."
            self.logger.error(error_msg)

    def open_sldprt_files(self):
        self.logger.debug(f"open_sldprt_files() 실행할 때 폴더명: {self.folder_path}")
        """sldprt 파일들을 열어서 BOM 추출 (재시도 로직 포함)"""
        
        # BOM 추출 프로세스 시작 캡처
        if self.capture_callback:
            try:
                self.capture_callback("bom_extraction_process_start", delay_ms=0)
            except Exception:
                pass

        # 전체 작업 시작 시간 기록
        overall_start_time = time.time()

        # BOM을 생성하는 위치는 한번 생성하면 잔여 파일이 있어 2차 실행해도 그대로 유지
        if not self.WORK_DIR:
            if not self.folder_path:
                self.logger.error(
                    "BOM 추출 시작 시 폴더 경로가 None입니다. UI에서 폴더를 선택했는지 확인하세요."
                )
                return
            self._compute_work_dir(self.folder_path)
            self.logger.debug(f"작업 폴더가 지정되지 않아 새로 생성합니다: {self.WORK_DIR}")
        work_dir_obj = Path(self.WORK_DIR)
        if not work_dir_obj.exists():
            work_dir_obj.mkdir(parents=True, exist_ok=True)
            self.logger.debug(f"Create BOM Folder : {self.WORK_DIR}")

        # 사전 점검: SolidWorks가 시작/연결 가능한지 확인 (실패 시 즉시 중단)
        if not self._sanity_check_solidworks():
            return

        self.sldprt_files_missed = []
        self.credit_shortage_stop = False
        self.files_processed_before_stop = 0
        self.remaining_files_after_stop = []
        self.logger.debug("크레딧 부족 상태 플래그 초기화")

        original_total_count = len(self.sldprt_files_to_process)

        # 1차 시도
        self.logger.info("1차 BOM 추출 작업을 시작합니다.")
        first_attempt_failed = self._process_files_batch(
            self.sldprt_files_to_process,
            attempt=1,
            completed_so_far=0,
            original_total=original_total_count,
        )

        self.first_attempt_failed_count = len(first_attempt_failed)
        self.first_attempt_failed_files = first_attempt_failed.copy()

        # 치명적 오류 발생 시 즉시 중단 (추가 이메일/후속 처리 없이 종료)
        if getattr(self, "abort_all", False):
            self.logger.error(
                "SolidWorks 시작/연결 치명적 실패로 전체 작업을 중단합니다. 후속 단계는 수행하지 않습니다."
            )
            return

        # 2차 시도 (1차에서 실패한 파일들만)
        if first_attempt_failed and not self.credit_shortage_stop:
            self.logger.debug(
                f"1차 시도에서 {len(first_attempt_failed)}개 파일이 실패했습니다. 2차 시도를 시작합니다."
            )

            if self.Solidworks_App:
                self.logger.info("솔리드웍스를 완전히 종료하고 재시작 준비 중...")
                self.Solidworks_App.kill(soft=False)
                time.sleep(5)
                self.Solidworks_App = None

            completed_so_far = original_total_count - self.first_attempt_failed_count
            files_for_second_attempt = first_attempt_failed

            second_attempt_failed = self._process_files_batch(
                files_for_second_attempt,
                attempt=2,
                completed_so_far=completed_so_far,
                original_total=original_total_count,
            )

            self.sldprt_files_missed = second_attempt_failed
        elif self.credit_shortage_stop:
            self.logger.info(
                "크레딧 부족으로 1차 시도에서 작업이 중단되었습니다. 2차 시도를 건너뜁니다."
            )
            self.sldprt_files_missed = first_attempt_failed
        else:
            self.logger.info("1차 시도에서 모든 파일이 성공적으로 처리되었습니다.")
            self.first_attempt_failed_count = 0
            self.first_attempt_failed_files = []
        if not self.console_mode:
            final_completed_count = original_total_count - len(self.sldprt_files_missed)
            status_text = f"완료"
            if self.credit_shortage_stop:
                final_completed_count = self.files_processed_before_stop
                status_text = f"크레딧 부족으로 중단"

            # 완료 리포트: 총/기존/이번 개수 표시
            already_completed = len(self.processed_files) if hasattr(self, 'processed_files') else 0
            newly_completed = final_completed_count - already_completed
            
            if len(self.sldprt_files_missed) > 0:
                if already_completed > 0:
                    status_text = (
                        f"완료 (총 {original_total_count}개: 기존 {already_completed}개 + "
                        f"이번 {newly_completed}개, {len(self.sldprt_files_missed)}개 실패)"
                    )
                else:
                    status_text = f"완료 ({final_completed_count}/{original_total_count} 성공, {len(self.sldprt_files_missed)}개 실패)"
            else:
                if already_completed > 0:
                    status_text = (
                        f"100% 완료 (총 {original_total_count}개: 기존 {already_completed}개 + 이번 {newly_completed}개)"
                    )
                else:
                    status_text = f"100% 완료 ({final_completed_count}/{original_total_count} 성공)"
            
            self.logger.info(f"📊 {status_text}")
            self.update_progress(final_completed_count, original_total_count, status_text)

        overall_end_time = time.time()
        total_elapsed_time = overall_end_time - overall_start_time
        hours, remainder = divmod(total_elapsed_time, 3600)
        minutes, seconds = divmod(remainder, 60)

        self.total_processing_time = f"{int(hours)}시간 {int(minutes)}분 {int(seconds)}초"
        self.logger.info(f"전체 작업 완료 - 총 소요 시간: {self.total_processing_time}")

        self._handle_final_results()

    def save_bom_exporter(self, idx, sldprt_file, file_size, app):
        """BOM을 엑셀로 저장하는 메인 로직

        동작 요약:
        - 파일 크기 기반으로 단일 대기시간(wait_time)을 계산하여 모든 대기에 일원 적용
        - UI 컨트롤 대기, CPU 안정화 대기, 파일 저장/잠금 해제 대기에 동일 wait_time 사용
        - 저장 실패/잠금 타임아웃 발생 시 연속 타임아웃 카운터를 올리고 필요 시 안전 재시작
        """
        # 단일 대기시간 계산
        wait_time = self._compute_wait(file_size)
        file_size_mb = file_size / (1024 * 1024)
        self.logger.info(
            f"파일 '{sldprt_file}' (크기: {file_size_mb:.2f}MB)에 대한 대기시간 설정: wait_time={wait_time}s"
        )

        # idx는 0부터 시작하지만 로그는 1부터 표시 (사람이 읽기 쉽게)
        # offset을 반영하여 실제 restart_count 내 위치 계산
        adjusted_idx = idx - self.restart_count_offset
        display_idx = (adjusted_idx % self.restart_count) + 1
        # 로그 포맷 보정 (중괄호로 인한 f-string 구문 오류 방지)
        self.logger.debug(f"{'='*30} restart_count : {display_idx}/{self.restart_count} {'='*30}")

        try:
            app.top_window().set_focus()
            self.logger.debug("도면 열기 전에 솔리드웍스로 포커스 설정")
            time.sleep(self.my_pace)

            # 이전 단계에서 남아있을 수 있는 모달/대화상자 정리
            self._cleanup_ui_state(app)
            self._capture_demo("sw_focused_before_open", delay_ms=80)

            pyautogui.hotkey("ctrl", "o")
            self.logger.debug('어셈블리 도면 열기 pyautogui.hotkey("ctrl+O")')
            time.sleep(self.my_pace)
            self._capture_demo("open_dialog_invoked", delay_ms=200)

            # 어셈블리 파일 full path 생성
            full_file_path = str(Path(self.SLDDRW_PATH) / sldprt_file)
            self.logger.debug(f"어셈블리 파일 full path: {full_file_path}")

            # 파일 열기 다이얼로그가 완전히 나타날 때까지 대기 (재시도 포함)
            edit_control = None
            max_dialog_attempts = 3
            for dialog_attempt in range(max_dialog_attempts):
                try:
                    # 먼저 다이얼로그 자체가 나타날 때까지 대기
                    self.logger.debug(
                        f"파일 열기 다이얼로그 대기 중... (시도 {dialog_attempt + 1}/{max_dialog_attempts})"
                    )
                    time.sleep(self.my_pace * 2)  # 다이얼로그 안정화 대기

                    # # 다이얼로그에 포커스 설정
                    # try:
                    #     app.top_window().set_focus()
                    #     self.logger.debug('다이얼로그 포커스 설정 완료')
                    # except Exception as focus_err:
                    #     self.logger.debug(f'포커스 설정 시도 중 경고(무시): {focus_err}')

                    # Edit 컨트롤 찾기 (title_re 사용으로 변경)
                    edit_control = (
                        app.top_window()
                        .child_window(title_re="파일 이름", control_type="Edit")
                        .wait("visible enabled", timeout=10)
                    )
                    self.logger.debug("어셈블리 파일 열기 컨트롤 찾기 성공")
                    self._capture_demo("open_dialog_visible", delay_ms=100)
                    break  # 성공하면 루프 탈출

                except Exception as edit_error:
                    self.logger.warning(
                        f"파일 이름 입력 컨트롤 찾기 실패 (시도 {dialog_attempt + 1}/{max_dialog_attempts}): {edit_error}"
                    )
                    if dialog_attempt < max_dialog_attempts - 1:
                        # 다음 시도 전 UI 정리
                        self.logger.debug("ESC 키로 잠재적 모달 정리 후 재시도")
                        self._press_escape_multiple(2)
                        time.sleep(self.my_pace)
                        app.top_window().set_focus()
                        self.logger.debug("다이얼로그 포커스 설정 완료")
                        continue
                    else:
                        # 마지막 시도도 실패하면 예외 발생
                        self.logger.error(
                            f"최대 재시도 횟수 초과: 파일 이름 입력 컨트롤을 찾을 수 없습니다."
                        )
                        raise RuntimeError("파일 열기 다이얼로그의 Edit 컨트롤을 찾을 수 없습니다.")
                        # handle_error로 스크린샷 저장 (이메일은 상위에서 처리)
                    #     time.sleep(self.my_pace)
                    #     # 다시 Ctrl+O로 다이얼로그 열기
                    #     pyautogui.hotkey('ctrl', 'o')
                    #     self.logger.debug('파일 열기 다이얼로그 재시도')
                    #     continue
                    # else:
                    #     # 마지막 시도도 실패하면 예외 발생
                    #     self.logger.error(f'최대 재시도 횟수 초과: 파일 이름 입력 컨트롤을 찾을 수 없습니다.')
                    #         # handle_error로 스크린샷 저장 (이메일은 상위에서 처리)
                    #     try:
                    #             self.handle_error(
                    #                 RuntimeError('파일 열기 다이얼로그의 Edit 컨트롤을 찾을 수 없습니다.'),
                    #                 context=f'어셈블리 파일 열기 다이얼로그: {sldprt_file}',
                    #                 send_email=False
                    #             )
                    #     except:
                    #         pass
                    #         # UI 정리
                    #         try:
                    #             self._cleanup_ui_state(app)
                    #         except:
                    #             pass
                    #     raise

            if edit_control is None:
                raise RuntimeError("파일 열기 다이얼로그의 Edit 컨트롤을 찾을 수 없습니다.")

            # Full path 입력 로직: 항상 전체 선택 후 한 번에 설정하여 중복/누적 입력 방지
            input_attempts = 0
            max_input_attempts = 3
            while input_attempts < max_input_attempts:
                try:
                    # edit_control.draw_outline()
                    edit_control.click_input()
                    self.logger.debug("어셈블리 파일 열기 edit_control.click_input()")
                    time.sleep(self.my_pace)

                    # 1) 전체 선택 후 삭제로 필드 초기화
                    pyautogui.hotkey("ctrl", "a")
                    time.sleep(0.05)
                    pyautogui.press("backspace")
                    time.sleep(0.05)

                    # 2) set_edit_text로 full path 설정 (가장 안정적)
                    edit_control.set_edit_text(full_file_path)
                    time.sleep(self.my_pace)

                    # 3) 검증 후 필요 시 clipboard 붙여넣기 방식으로 1회 보정
                    current_text = edit_control.get_value() or ""
                    self.logger.debug(f"현재 입력된 텍스트(1차): {current_text}")
                    if current_text == full_file_path:
                        self.logger.debug(
                            "어셈블리 파일 full path가 올바르게 입력되었습니다. (set_edit_text)"
                        )
                        break

                    # 보정 입력 (ctrl+v) - 클립보드 안전 복사
                    max_clipboard_attempts = 3
                    for clip_attempt in range(max_clipboard_attempts):
                        pyperclip.copy(full_file_path)
                        time.sleep(0.1)  # 클립보드 복사 안정화 대기
                        clipboard_value = pyperclip.paste()
                        if clipboard_value == full_file_path:
                            self.logger.debug(
                                f"어셈블리 파일 full path 클립보드 복사 성공: {full_file_path}"
                            )
                            break
                        else:
                            self.logger.warning(
                                f"클립보드 복사 검증 실패 (재시도 {clip_attempt + 1}/{max_clipboard_attempts})"
                            )
                            time.sleep(0.2)
                    else:
                        self.logger.error(
                            f"어셈블리 파일 full path 클립보드 복사 실패: {full_file_path}"
                        )

                    pyautogui.hotkey("ctrl", "a")
                    time.sleep(0.05)
                    pyautogui.hotkey("ctrl", "v")
                    self.logger.debug(f"어셈블리 파일 full path를 붙여넣기 보정 수행")
                    time.sleep(self.my_pace)
                    current_text = edit_control.get_value() or ""
                    self.logger.debug(f"현재 입력된 텍스트(보정 후): {current_text}")
                    if current_text == full_file_path:
                        self.logger.debug(
                            "어셈블리 파일 full path가 올바르게 입력되었습니다. (clipboard)"
                        )
                        break
                except Exception as input_err:
                    self.logger.warning(f"파일명 입력 중 예외 발생 (재시도): {input_err}")

                input_attempts += 1
                time.sleep(self.my_pace)

            if input_attempts >= max_input_attempts:
                self.logger.error(
                    f"파일명 입력 실패 (최대 재시도 {max_input_attempts}회 초과): {full_file_path}"
                )
                # handle_error로 스크린샷 저장 (이메일은 상위에서 처리)
                try:
                    self.handle_error(
                        TimeoutError("파일명 입력 실패"),
                        context=f"어셈블리 파일 열기: {full_file_path}",
                        send_email=False,
                    )
                except:
                    pass
                    # UI 정리
                    try:
                        self._cleanup_ui_state(app)
                    except:
                        pass
                raise TimeoutError("파일명 입력 실패")

            self._capture_demo("open_path_entered", delay_ms=60)
            pyautogui.press("enter")
            self.logger.debug("어셈블리 파일을 열기 위해 엔터키를 누릅니다.")
            time.sleep(self.my_pace)
            self._capture_demo("open_confirm_enter", delay_ms=120)

            # 파일 열기 다이얼로그가 닫혔는지 확인하고, 남아있으면 보정 동작 수행
            try:
                # 다이얼로그가 유지될 수 있으므로 사라질 때까지 짧게 대기
                edit_control.wait_not("exists", timeout=min(10, max(3, wait_time // 3)))
                self.logger.debug("파일 열기 다이얼로그가 닫혔습니다.")
            except Exception:
                self.logger.debug("파일 열기 다이얼로그가 여전히 보입니다. Enter 재입력 보정 수행")
                pyautogui.press("enter")
                time.sleep(self.my_pace)

            # CPU 사용량이 낮아질 때까지 대기 (파일 로딩 완료 확인)
            self.logger.debug("BOM 아이콘에서 우클릭하기 전 CPU 사용량이 낮아질 때까지 대기")
            app.wait_cpu_usage_lower(
                threshold=40, timeout=60
            )  # 고정 60초: 파일 크기와 무관하게 충분한 시간
            self.logger.debug("CPU 사용량이 낮아졌습니다. BOM 아이콘 찾기를 시작합니다.")
            self._capture_demo("file_loaded", delay_ms=80)

            # TreeItem에서 BOM 항목을 찾아서 우클릭하기
            try:
                bom_treeItem = (
                    app.top_window()
                    .child_window(title_re="BOM", control_type="TreeItem", found_index=0)
                    .wait("visible enabled", timeout=wait_time)
                )
                self.logger.debug("BOM으로 시작하는 TreeItem 컨트롤 찾음")
                self._capture_demo("bom_icon_found", delay_ms=60)
            except Exception as bom_error:
                self.logger.warning(f"BOM TreeItem 찾기 실패 (파일 로딩 실패 가능성): {bom_error}")
                # 연속 타임아웃 카운터 증가 및 필요시 안전 재시작
                self._increment_consec_and_maybe_restart(reason="bom_treeitem_timeout")
                # handle_error로 스크린샷 저장 (이메일은 상위에서 처리)
                try:
                    self.handle_error(
                        bom_error,
                        context=f"BOM TreeItem 찾기 실패: {sldprt_file}",
                        send_email=False,
                    )
                except:
                    pass
                    # UI 정리
                    try:
                        self._cleanup_ui_state(app)
                    except:
                        pass
                raise

            # 우클릭 및 저장 준비
            self.logger.debug("BOM 아이콘에서 우클릭하기 전 CPU 사용량이 낮아질 때까지 대기")
            app.wait_cpu_usage_lower(threshold=50, timeout=20)  # 고정 20초: 짧은 안정화 대기
            # bom_treeItem.draw_outline()
            time.sleep(self.my_pace)
            bom_treeItem.click_input()
            time.sleep(self.my_pace)
            pyautogui.rightClick()
            
            # 데모 모드: 우클릭 후 3초 슬립 (동영상 녹화용)
            if self.run_mode == "demo":
                self.logger.debug("[DEMO] 우클릭 후 3초 대기 (녹화용)")
                time.sleep(3.0)
            
            time.sleep(self.my_pace)
            self._capture_demo("bom_right_click_menu", delay_ms=80)

            # 저장 다이얼로그 열기 전 CPU 대기는 제거 (불필요)
            pyautogui.hotkey("ctrl", "B")
            self.logger.debug('다른이름으로 저장 핫키 "ctrl+B"')
            time.sleep(self.my_pace)
            
            # 데모 모드: 다이얼로그 표시 후 대기 (동영상 녹화용)
            if self.demo_video_mode:
                self.logger.debug(f"[DEMO] 저장 다이얼로그 표시 후 {self.demo_pause_after_dialog}초 대기")
                time.sleep(self.demo_pause_after_dialog)
            
            self._capture_demo("save_dialog_invoked", delay_ms=200)

            # 파일 형식 지정
            try:
                file_type = (
                    app.top_window()
                    .child_window(
                        title_re="파일 형식:",
                        auto_id="FileTypeControlHost",
                        control_type="ComboBox",
                        found_index=0,
                    )
                    .wait("visible enabled", timeout=wait_time)
                )
                # file_type.draw_outline()
                file_type.click_input()
                file_type.select(" Excel 2007 (*.xlsx)")
                time.sleep(self.my_pace)
                self._capture_demo("filetype_excel", delay_ms=80)
            except Exception as filetype_error:
                self.logger.warning(f"파일 형식 지정 중 오류: {filetype_error}")
                # handle_error로 스크린샷 저장 (이메일은 상위에서 처리)
                try:
                    self.handle_error(
                        filetype_error,
                        context=f"파일 형식 지정 실패: {sldprt_file}",
                        send_email=False,
                    )
                except:
                    pass
                    # UI 정리
                    try:
                        self._cleanup_ui_state(app)
                    except:
                        pass
                raise

            # 축소판 미리보기 CheckBox: offset을 반영하여 재시작 직후인지 확인
            if adjusted_idx % self.restart_count == 0:
                try:
                    thumbnail_check = (
                        app.top_window()
                        .child_window(auto_id="", control_type="CheckBox", found_index=0)
                        .wait("visible enabled", timeout=wait_time)
                    )
                    if not thumbnail_check.get_toggle_state():
                        # thumbnail_check.draw_outline()
                        thumbnail_check.click_input()
                        time.sleep(self.my_pace)
                        self._capture_demo("thumbnail_checked", delay_ms=60)
                except Exception as thumb_error:
                    self.logger.warning(f"축소판 체크박스 처리 중 오류 (무시): {thumb_error}")

            # BOM 엑셀 파일 full path 생성 (파일명 입력)
            excel_filename = sldprt_file[:-7]  # 확장자 제거
            excel_full_path = str(Path(self.WORK_DIR) / f"{excel_filename}.xlsx")
            self.logger.debug(f"BOM 엑셀 저장 full path: {excel_full_path}")

            # 파일 저장 다이얼로그가 완전히 나타날 때까지 대기 (재시도 포함)
            file_name = None
            max_dialog_attempts = 3
            for dialog_attempt in range(max_dialog_attempts):
                try:
                    # 먼저 다이얼로그 자체가 나타날 때까지 대기
                    self.logger.debug(
                        f"BOM 저장 다이얼로그 대기 중... (시도 {dialog_attempt + 1}/{max_dialog_attempts})"
                    )
                    time.sleep(self.my_pace * 2)  # 다이얼로그 안정화 대기

                    # 다이얼로그에 포커스 설정
                    try:
                        app.top_window().set_focus()
                        self.logger.debug("저장 다이얼로그 포커스 설정 완료")
                    except Exception as focus_err:
                        self.logger.debug(f"포커스 설정 시도 중 경고(무시): {focus_err}")

                    # Edit 컨트롤 찾기 (title_re 사용으로 변경)
                    file_name = (
                        app.top_window()
                        .child_window(title_re="파일 이름", control_type="Edit")
                        .wait("visible enabled", timeout=wait_time)
                    )
                    self.logger.debug("BOM 저장 파일명 입력 컨트롤 찾기 성공")
                    self._capture_demo("save_dialog_ready", delay_ms=120)
                    break  # 성공하면 루프 탈출

                except Exception as edit_error:
                    self.logger.warning(
                        f"BOM 저장 파일명 입력 컨트롤 찾기 실패 (시도 {dialog_attempt + 1}/{max_dialog_attempts}): {edit_error}"
                    )
                    if dialog_attempt < max_dialog_attempts - 1:
                        # 다음 시도 전 UI 정리
                        self.logger.debug("ESC 키로 잠재적 모달 정리 후 재시도")
                        self._press_escape_multiple(2)
                        time.sleep(self.my_pace)
                        # 다시 Ctrl+B로 다이얼로그 열기
                        pyautogui.hotkey("ctrl", "B")
                        self.logger.debug("BOM 저장 다이얼로그 재시도")
                        continue
                    else:
                        # 마지막 시도도 실패하면 예외 발생
                        self.logger.error(
                            f"최대 재시도 횟수 초과: BOM 저장 파일명 입력 컨트롤을 찾을 수 없습니다."
                        )
                        # handle_error로 스크린샷 저장 (이메일은 상위에서 처리)
                        try:
                            self.handle_error(
                                RuntimeError(
                                    "BOM 저장 다이얼로그의 Edit 컨트롤을 찾을 수 없습니다."
                                ),
                                context=f"BOM 저장 다이얼로그: {sldprt_file}",
                                send_email=False,
                            )
                        except:
                            pass
                            # UI 정리
                            try:
                                self._cleanup_ui_state(app)
                            except:
                                pass
                        raise

            if file_name is None:
                raise RuntimeError("BOM 저장 다이얼로그의 Edit 컨트롤을 찾을 수 없습니다.")

            # Edit 컨트롤을 찾았으면 파일명 입력 시작
            try:
                # file_name.draw_outline()
                file_name.click_input()

                # Full path 입력 로직
                input_attempts = 0
                max_input_attempts = 3
                while input_attempts < max_input_attempts:
                    try:
                        # 1) 전체 선택 후 삭제로 필드 초기화
                        pyautogui.hotkey("ctrl", "a")
                        time.sleep(0.05)
                        pyautogui.press("backspace")
                        time.sleep(0.05)

                        # 2) set_edit_text로 full path 설정
                        file_name.set_edit_text(excel_full_path)
                        time.sleep(self.my_pace)

                        # 3) 검증
                        current_text = file_name.get_value() or ""
                        self.logger.debug(f"BOM 파일명 입력(1차): {current_text}")
                        if current_text == excel_full_path:
                            self.logger.debug(
                                "BOM 파일 full path가 올바르게 입력되었습니다. (set_edit_text)"
                            )
                            break

                        # 보정 입력 (ctrl+v)
                        max_clipboard_attempts = 3
                        for clip_attempt in range(max_clipboard_attempts):
                            pyperclip.copy(excel_full_path)
                            time.sleep(0.1)
                            clipboard_value = pyperclip.paste()
                            if clipboard_value == excel_full_path:
                                self.logger.debug(
                                    f"BOM 파일 full path 클립보드 복사 성공: {excel_full_path}"
                                )
                                break
                            else:
                                self.logger.warning(
                                    f"클립보드 복사 검증 실패 (재시도 {clip_attempt + 1}/{max_clipboard_attempts})"
                                )
                                time.sleep(0.2)
                        else:
                            self.logger.error(
                                f"BOM 파일 full path 클립보드 복사 실패: {excel_full_path}"
                            )

                        pyautogui.hotkey("ctrl", "a")
                        time.sleep(self.my_pace)
                        pyautogui.hotkey("ctrl", "v")
                        self.logger.debug(f"BOM 파일 full path를 붙여넣기 보정 수행")
                        time.sleep(self.my_pace)
                        current_text = file_name.get_value() or ""
                        self.logger.debug(f"BOM 파일명 입력(보정 후): {current_text}")
                        if current_text == excel_full_path:
                            self.logger.debug(
                                "BOM 파일 full path가 올바르게 입력되었습니다. (clipboard)"
                            )
                            break
                    except Exception as input_err:
                        self.logger.warning(f"BOM 파일명 입력 중 예외 (재시도): {input_err}")

                    input_attempts += 1
                    time.sleep(self.my_pace)

                if input_attempts >= max_input_attempts:
                    self.logger.error(
                        f"BOM 파일명 입력 실패 (최대 재시도 {max_input_attempts}회 초과): {excel_full_path}"
                    )
                    # handle_error로 스크린샷 저장 (이메일은 상위에서 처리)
                    try:
                        self.handle_error(
                            TimeoutError("BOM 파일명 입력 실패"),
                            context=f"BOM 파일명 입력: {excel_full_path}",
                            send_email=False,
                        )
                    except:
                        pass
                        # UI 정리
                        try:
                            self._cleanup_ui_state(app)
                        except:
                            pass
                    raise TimeoutError("BOM 파일명 입력 실패")
            except Exception as filename_error:
                self.logger.warning(f"BOM 파일명 입력 처리 중 오류: {filename_error}")
                # handle_error로 스크린샷 저장 (이메일은 상위에서 처리)
                try:
                    self.handle_error(
                        filename_error,
                        context=f"BOM 파일명 입력 처리: {excel_full_path}",
                        send_email=False,
                    )
                except:
                    pass
                    # UI 정리
                    try:
                        self._cleanup_ui_state(app)
                    except:
                        pass
                raise

            self._capture_demo("filename_set", delay_ms=80)
            pyautogui.hotkey("enter")
            self.logger.debug(f'{sldprt_file} 어셈블리 파일의 BOM 저장을 위해서 "enter" 키를 누름')
            time.sleep(self.my_pace * 3)
            self._capture_demo("save_enter", delay_ms=160)

            # 저장될 엑셀 파일의 전체 경로
            expected_file = Path(self.WORK_DIR) / f"{sldprt_file[:-7]}.xlsx"

            # 파일이 저장될 때까지 대기 (단일 wait_time 사용)
            max_wait = wait_time
            start_time = time.time()

            while not expected_file.exists():
                if time.time() - start_time > max_wait:
                    self.logger.error(
                        f"Excel 파일 저장 시간 초과: {expected_file} (대기: {max_wait}s)"
                    )
                    try:
                        if self.Solidworks_App:
                            self.Solidworks_App.top_window().set_focus()
                            time.sleep(0.05)
                    except:
                        pass
                    self._press_escape_multiple(3)
                    # 연속 타임아웃 카운터 증가 및 필요시 재시작
                    self._increment_consec_and_maybe_restart(reason="file_save_timeout")
                    raise TimeoutError(f"Excel 파일 {expected_file}이 저장되지 않았습니다.")
                time.sleep(self.my_pace)

            # 파일이 완전히 저장될 때까지 추가 대기
            while True:
                try:
                    with open(expected_file, "rb"):
                        break
                except PermissionError:
                    if time.time() - start_time > max_wait:
                        self.logger.error(
                            f"Excel 파일 잠금 해제 시간 초과: {expected_file} (대기: {max_wait}s)"
                        )
                        try:
                            if self.Solidworks_App:
                                self.Solidworks_App.top_window().set_focus()
                                time.sleep(self.my_pace)
                        except:
                            pass
                        self._press_escape_multiple(3)
                        # 연속 타임아웃 카운터 증가 및 필요시 재시작
                        self._increment_consec_and_maybe_restart(reason="file_lock_timeout")
                        raise TimeoutError(f"Excel 파일 {expected_file}이 잠겨있습니다.")
                time.sleep(self.my_pace)

            self.logger.debug(f"Excel 파일 저장 완료: {expected_file}")
            self._capture_demo("save_done", delay_ms=120)
            # 저장 성공 시 연속 타임아웃 카운터 리셋
            try:
                self.consec_timeouts = 0
            except Exception:
                pass

            # 재시작 및 종료 로직: offset을 반영하여 재시작 시점 확인
            # 참고: 이 로직은 _process_files_batch에서 이미 재시작을 처리하므로 현재는 사용되지 않을 수 있음
            if adjusted_idx != 0 and adjusted_idx % self.restart_count == self.restart_count - 1:
                self.logger.info("솔리드웍스를 재시작하기 위해 종료합니다.")
                app.kill(soft=False)
                # 다음 루프에서 확실히 재시작 로직이 실행되도록 참조를 None 으로 초기화
                self.Solidworks_App = None
                self.logger.info("솔리드웍스를 종료하였습니다. 잠시 후 솔리드웍스를 재시작합니다.")

            if idx == self.total_count - 1:
                self.logger.info("작업이 완료되어 솔리드웍스를 종료합니다.")
                app.kill(soft=False)
                # 종료 후 앱 참조 초기화
                self.Solidworks_App = None
                self.logger.info("솔리드웍스가 종료되었습니다.")

        except Exception as main_error:
            # 예외 발생 시, 상위 핸들러에서 복구를 처리하도록 바로 전달
            self.logger.error(f"save_bom_exporter 실행 중 오류 발생: {main_error}")
            # 공통 에러 처리 (스크린샷 저장, 이메일은 상위에서 처리하므로 여기서는 생략)
            try:
                self.handle_error(
                    main_error, context=f"save_bom_exporter: {sldprt_file}", send_email=False
                )
            except Exception as handle_err:
                self.logger.warning(f"에러 처리 중 경고(무시): {handle_err}")
            # 남아 있는 모달/대화상자 정리 및 포커스 복원 (한 번만 호출)
            try:
                self._cleanup_ui_state(app)
            except Exception:
                pass
            raise  # 예외를 상위로 전달

    def _safe_solidworks_restart(self):
        """안전한 솔리드웍스 재시작 (최대 3회 재시도) - UIA/Win32 백엔드 모두 지원"""
        max_retries = 3

        for retry_attempt in range(max_retries):
            try:
                self.logger.debug(f"솔리드웍스 재시작 시도 {retry_attempt + 1}/{max_retries}...")

                # 기존 윈도우 찾기
                found_windows = findwindows.find_windows(title_re=self.config.application_title)

                if found_windows:
                    self.logger.debug(f"윈도우 찾기 성공: 핸들 {found_windows}")
                    self.Solidworks_App = Application(backend=self.pywinauto_backend).connect(
                        handle=found_windows[0]
                    )
                    self.logger.debug(f"핸들로 앱 연결 성공: {found_windows[0]}")
                else:
                    # 새로 실행
                    self.logger.debug("실행 중인 솔리드웍스를 찾지 못해 새로 실행합니다...")
                    self.Solidworks_App = Application(backend=self.pywinauto_backend).start(
                        self.config.program_path
                    )
                    self.logger.debug("솔리드웍스 실행중...")

                    try:
                        # 백엔드별 안정적인 연결 대기
                        start_ts = time.time()
                        connected = False
                        while time.time() - start_ts < self.wait_time:
                            try:
                                wins = findwindows.find_windows(
                                    title_re=self.config.application_title
                                )
                                if wins:
                                    # 여러 윈도우가 있을 경우 마지막 윈도우를 선택 (가장 최근에 열린 것)
                                    target_handle = wins[-1] if len(wins) > 1 else wins[0]
                                    if len(wins) > 1:
                                        self.logger.warning(
                                            f"여러 개의 SolidWorks 윈도우 감지됨 ({len(wins)}개), 마지막 핸들 사용: {target_handle}"
                                        )
                                    self.Solidworks_App = Application(
                                        backend=self.pywinauto_backend
                                    ).connect(handle=target_handle)
                                    connected = True
                                    break
                            except Exception:
                                pass
                            time.sleep(self.my_pace)

                        if not connected:
                            raise RuntimeError("솔리드웍스 윈도우 핸들을 찾지 못해 연결 실패")

                        try:
                            # CPU 안정화 대기 (가능한 경우)
                            self.Solidworks_App.wait_cpu_usage_lower(
                                threshold=20, timeout=self.wait_time
                            )
                        except Exception:
                            # win32 백엔드 등에서 실패할 수 있으므로 경고만 남김
                            self.logger.warning(
                                "CPU 안정화 대기 실패(무시): backend/상태 차이 가능"
                            )
                        self.logger.debug("새로 실행한 솔리드웍스에 연결 성공 및 안정화 대기 완료")
                    except Exception as e:
                        self.logger.error(f"새로 실행한 솔리드웍스에 연결 실패: {e}")
                        # 다음 재시도를 위해 앱 종료
                        try:
                            self.Solidworks_App.kill(soft=False)
                        except:
                            pass
                        time.sleep(5)
                        continue

                # Window 인터페이스 안전하게 접근
                try:
                    mode = getattr(self.config, "run_mode", "release")
                    if mode == "demo":
                        # 데모: 오른쪽 2/3 영역에 배치 (작업영역 기반 동적 계산)
                        import win32gui
                        import win32con
                        try:
                            from ctypes import wintypes
                            import ctypes
                            SPI_GETWORKAREA = 0x0030
                            rc = wintypes.RECT()
                            ctypes.windll.user32.SystemParametersInfoW(
                                SPI_GETWORKAREA, 0, ctypes.byref(rc), 0
                            )
                            work_left, work_top = rc.left, rc.top
                            work_width = rc.right - rc.left
                            work_height = rc.bottom - rc.top
                        except Exception:
                            # 폴백: 전체 화면 사용
                            work_left, work_top = 0, 0
                            import win32api
                            work_width = win32api.GetSystemMetrics(0)
                            work_height = win32api.GetSystemMetrics(1)

                        x = work_left + work_width // 3
                        w = work_width - work_width // 3
                        y = work_top
                        h = work_height

                        hwnd = self.Solidworks_App.top_window().handle
                        # 1단계: 복원
                        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                        # time.sleep(0.2)
                        # 2단계: 위치/크기 설정
                        win32gui.SetWindowPos(
                            hwnd,
                            win32con.HWND_TOP,
                            int(x), int(y), int(w), int(h),
                            win32con.SWP_SHOWWINDOW
                        )
                        self.logger.debug(f"솔리드웍스 윈도우 위치 설정 (demo): ({x}, {y}, {w}, {h})")
                    else:
                        # 개발/배포: 전체 화면 최대화 비활성화 (사용자 요청)
                        # self.Solidworks_App.top_window().maximize()
                        self.logger.debug("솔리드웍스 윈도우 최대화 비활성화")

                    self.Solidworks_App.top_window().set_focus()
                    time.sleep(self.my_pace)
                    self._capture_demo("solidworks_ready", delay_ms=120)
                    self.logger.debug("솔리드웍스 윈도우 포커스 설정 완료")
                    return True  # 성공

                except Exception as win_e:
                    self.logger.warning(
                        f"윈도우 제어 실패 (재시도 {retry_attempt + 1}/{max_retries}): {win_e}"
                    )
                    # 솔리드웍스 강제 종료 후 재시도
                    try:
                        self.Solidworks_App.kill(soft=False)
                    except:
                        pass
                    self.Solidworks_App = None
                    time.sleep(5)
                    continue

            except Exception as e:
                self.logger.error(
                    f"솔리드웍스 재시작 실패 (재시도 {retry_attempt + 1}/{max_retries}): {e}"
                )
                # 재시도 준비: 앱 객체 정리
                try:
                    if self.Solidworks_App:
                        self.Solidworks_App.kill(soft=False)
                except:
                    pass
                self.Solidworks_App = None
                time.sleep(5)

        # 모든 재시도 실패
        self.logger.error(f"솔리드웍스 재시작 {max_retries}회 시도 모두 실패")
        self.Solidworks_App = None  # 확실하게 None으로 설정
        return False

    def _process_files_batch(
        self, files_to_process, attempt=1, completed_so_far=0, original_total=0
    ):
        """파일 배치 처리 (공통 로직)"""
        failed_files = []
        # 치명적 실패 발생 시 전체 중단 플래그
        self.abort_all = False

        # Turn off Caps Lock if it is on
        if self.is_caps_lock_on():
            self.logger.info(f"CAPs lock is on, it forces CAP lock is off")
            self.set_caps_lock(False)

        timestamp_format = "%Y/%m/%d %H:%M:%S"
        start_time = time.time()
        start = time.strftime(timestamp_format)
        self.logger.info(f"{attempt}차 시도 - 엑셀 변환작업 루프의 시작 시간: {start}")
        
        # 배치 처리 시작 캡처
        if self.capture_callback:
            try:
                self.capture_callback(f"batch_start_attempt_{attempt}", delay_ms=100)
            except Exception:
                pass

        # ⭐ 배치 시작 전 솔리드웍스 상태 확인 및 실행
        if self.Solidworks_App is None:
            self.logger.info(
                f"{attempt}차 시도 시작 - 솔리드웍스가 실행되지 않았습니다. 안전한 재시작을 수행합니다."
            )
            restart_success = self._safe_solidworks_restart()
            if not restart_success:
                reason = f"{attempt}차 시도 시작 시 SolidWorks 시작 실패 - 전체 작업 중단"
                self.logger.error(reason)
                try:
                    self._send_fatal_email(
                        f"[B2E] Fatal - {attempt}차 시도 SolidWorks 시작 실패", reason
                    )
                except Exception:
                    pass
                self.abort_all = True
                # 모든 파일을 실패로 반환
                return files_to_process

        # 콘솔 모드에서는 tqdm 사용, GUI 모드에서는 progress_callback 사용
        progress_total = original_total if original_total > 0 else len(files_to_process)
        if self.console_mode:
            desc = f"{attempt}차 시도 - 전체 작업의 진척율 진행 중"
            progress_iterator = trange(
                len(files_to_process), desc=desc, unit="파일", ncols=100, leave=True
            )
        else:
            # GUI 모드에서는 단순 range 사용
            progress_iterator = range(len(files_to_process))

        # 솔리드웍스 실행 및 재실행
        for i in progress_iterator:
            # --- 사전 건강검사: 앱 객체가 없거나 메인 윈도우가 없으면 즉시 재시작 ---
            try:
                preflight_needed = False
                if self.Solidworks_App is None:
                    preflight_needed = True
                else:
                    # 메인 윈도우 접근 시도 (예: 직전 종료로 인해 핸들 유실 케이스 방지)
                    try:
                        _ = self.Solidworks_App.top_window().handle
                    except Exception:
                        self.logger.debug("사전 점검: 메인 윈도우가 없어 재시작이 필요합니다.")
                        self.Solidworks_App = None
                        preflight_needed = True

                if preflight_needed:
                    self.logger.info(
                        "파일 처리 전 사전 점검: SolidWorks가 실행되지 않아 안전 재시작을 수행합니다."
                    )
                    if not self._safe_solidworks_restart():
                        reason = f"{attempt}차 시도 중 사전 재시작 실패 - 전체 작업 중단"
                        self.logger.error(reason)
                        try:
                            self._send_fatal_email(
                                f"[B2E] Fatal - Preflight restart failed", reason
                            )
                        except Exception:
                            pass
                        self.abort_all = True
                        break
            except Exception as pre_e:
                self.logger.warning(f"사전 건강검사 중 경고(무시): {pre_e}")
            # 매 파일 처리 전 메모리 체크 (선제적 재시작)
            if self.enable_memory_monitor and i > 0:  # 첫 파일은 건너뜀
                mem_restart_triggered = self._check_memory_and_maybe_restart()
                if mem_restart_triggered:
                    # 메모리 때문에 재시작했으므로 연속 타임아웃 카운터 초기화
                    self.consec_timeouts = 0
                    # ⭐ 메모리 재시작 시 restart_count 카운터 리셋
                    # 현재 인덱스를 기준으로 다음 restart_count 배수까지 offset 조정
                    self.restart_count_offset = i
                    self.logger.info(
                        f"⭐ 메모리 재시작으로 인한 주기적 재시작 카운터 리셋 "
                        f"(offset={self.restart_count_offset}) - "
                        f"다음 주기적 재시작은 {self.restart_count}개 파일 후"
                    )

            # 주기적 재시작: offset을 반영하여 실제 재시작 시점 결정
            adjusted_index = i - self.restart_count_offset
            if adjusted_index > 0 and adjusted_index % self.restart_count == 0:
                # 안전한 재시작 메서드 사용
                restart_success = self._safe_solidworks_restart()
                if restart_success:
                    # 주기적 재시작 성공 시, 오프셋을 현재 인덱스로 업데이트하여
                    # 다음 재시작까지 정확히 restart_count 개의 파일을 처리하도록 맞춘다.
                    self.restart_count_offset = i
                    self.logger.info(
                        f"주기적 재시작 완료 - 다음 주기적 재시작은 {self.restart_count}개 파일 후 (offset={self.restart_count_offset})"
                    )
                else:
                    # 치명적 실패: 전체 작업 중단 및 단일 메일 통보
                    reason = "SolidWorks 시작/연결 실패로 전체 작업 중단"
                    self.logger.error(reason)
                    try:
                        title = f"[B2E] Fatal - SolidWorks start/connect failed"
                        content = (
                            f"{reason}\n시도: {attempt}차, 인덱스: {i+1}/{len(files_to_process)}"
                        )
                        self._send_fatal_email(title, content)
                    except Exception:
                        pass
                    # 중단 플래그 설정 후 루프 종료
                    self.abort_all = True
                    break

            # Check if stop button is clicked (콘솔 모드에서는 사용 안함)
            if self.stop_progress_flag:
                break

            sldprt_file, file_size = files_to_process[i]

            # 이전 오류로 남아있을 수 있는 모달/대화상자 선제 정리 (첫 파일이 아닐 때만)
            # 첫 파일은 방금 재시작했으므로 정리 불필요
            if i > 0:
                try:
                    self._cleanup_ui_state(self.Solidworks_App)
                except Exception:
                    pass

            # --- GUI 모드 진행률 업데이트 (처리 전) ---
            if not self.console_mode:
                current_completed = completed_so_far + (i - len(failed_files))
                if attempt == 1:
                    status_text = f"{sldprt_file} 처리 중..."
                else:  # attempt == 2
                    retry_total = len(files_to_process)
                    status_text = f"재시도 ({i + 1}/{retry_total}): {sldprt_file}"
                self.update_progress(current_completed, progress_total, status_text)

            # 크레딧 확인 (파일 처리 전, 차감은 후)
            if not self.console_mode and self.credit_manager:
                cost_per_file = self.credit_manager.get_per_item_cost()
                credit_status = self.credit_manager.get_credit_status()
                remaining_credits = credit_status.get("remaining_credits", 0)

                # 무제한 크레딧(-1)이 아닌 경우에만 잔여 크레딧 체크
                if remaining_credits != -1 and remaining_credits < cost_per_file:
                    self.logger.warning(
                        f"크레딧 부족으로 처리를 중단합니다: 다음 파일 처리에 {cost_per_file} 크레딧이 필요하지만, {remaining_credits} 크레딧만 남았습니다."
                    )
                    if not self.console_mode:
                        import tkinter.messagebox

                        tkinter.messagebox.showinfo(
                            "크레딧 소진",
                            "사용 가능한 크레딧을 모두 소진하여 작업을 중단합니다.\n크레딧을 구매한 후 다시 시도하세요.",
                        )
                    self.credit_shortage_stop = True
                    # 크레딧 부족 시 중단된 파일은 현재 파일(i)까지 포함
                    self.files_processed_before_stop = completed_so_far + (i - len(failed_files))
                    try:
                        # 남은 파일 목록 계산 (현재 i부터 끝까지)
                        self.remaining_files_after_stop = [
                            files_to_process[j][0] for j in range(i, len(files_to_process))
                        ]
                    except Exception:
                        self.remaining_files_after_stop = []
                    break  # for 루프를 중단

            try:
                # 파일 처리 시작 콜백 호출 (UI 스피너 시작)
                if self.file_processing_start_callback:
                    try:
                        self.file_processing_start_callback()
                    except Exception as cb_error:
                        self.logger.warning(f"파일 처리 시작 콜백 오류 (무시하고 계속): {cb_error}")

                # 메인 동작, 어셈블리 파일을 열고 엑셀을 저장하는 동작
                self.save_bom_exporter(i, sldprt_file, file_size, self.Solidworks_App)

                # 파일 처리 성공 시에만 크레딧 차감 및 성공 파일 기록
                # 크레딧 차감 (파일 처리 성공 후, UI/동기화 일관성)
                if not self.console_mode and self.credit_manager:
                    # 중복 파일 크레딧 차감 방지
                    should_deduct_credit = True
                    
                    # rerun_only_new_duplicates=True: 완료 후 재실행 모드
                    if getattr(self, "only_count_new_duplicates", False):
                        # exported_bom 폴더에 이미 존재하는 파일인지 확인
                        from pathlib import Path
                        export_folder = Path(self.folder_path) / "exported_bom"
                        expected_filename = Path(sldprt_file).stem + ".xlsx"
                        existing_file = export_folder / expected_filename
                        
                        if existing_file.exists():
                            should_deduct_credit = False
                            self.logger.info(
                                f"중복 파일 감지 - 크레딧 차감 제외: {sldprt_file}"
                            )
                    
                    if should_deduct_credit:
                        credit_result = self.credit_manager.deduct_credits_by_policy(
                            1, f"BOM 변환: {sldprt_file}"
                        )
                        if credit_result["success"]:
                            self.logger.info(
                                f"크레딧 차감 완료 - 파일: {sldprt_file}, 남은 크레딧: {credit_result.get('remaining_credits', 0)}"
                            )
                        else:
                            self.logger.error(
                                f"파일 처리 후 크레딧 차감 실패: {credit_result.get('message')}"
                            )
                        if self.credit_update_callback:
                            self.credit_update_callback()
                        self._capture_demo("credit_progress", delay_ms=120)
                    else:
                        self.logger.debug(f"중복 파일 - 크레딧 차감 생략: {sldprt_file}")

                # 성공 파일 기록 (세션 누적용)
                if "success_files" not in locals():
                    success_files = []
                success_files.append(files_to_process[i])

                # --- GUI 모드 진행률 업데이트 (성공) ---
                if not self.console_mode:
                    current_completed = completed_so_far + (i + 1 - len(failed_files))
                    completed_status = f"{sldprt_file} 완료"
                    self.update_progress(current_completed, progress_total, completed_status)

            except Exception as e:
                mail_title = str(e)
                timestamp4img = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                e_content = f"{mail_title} {sldprt_file}\n파일에서 발생했습니다. ({attempt}차 시도)"
                self.logger.error(e_content)

                # 치명적 중단 요청이 이미 설정된 경우: 개별 파일 메일 전송/처리 생략하고 즉시 중단
                if getattr(self, "abort_all", False):
                    break

                # === 솔리드웍스 크래시 감지: 즉시 재시작 후 1회 재시도 ===
                if "No windows for that process could be found" in str(e):
                    self.logger.warning(
                        "솔리드웍스 크래시 감지! 즉시 재시작 후 동일 파일 1회 재시도합니다."
                    )
                    self.Solidworks_App = None

                    # 반복 크래시 여부 확인 (단시간 내 다수면 전체 중단)
                    if self._record_crash_and_should_abort():
                        break

                    # 강제 재시작 시도
                    if not self._safe_solidworks_restart():
                        self.logger.error("솔리드웍스 재시작 실패. 프로그램을 중단합니다.")
                        self.abort_all = True
                        break

                    # 동일 파일 1회 재시도 (빠른 회복용)
                    try:
                        self.logger.info("크래시 복구 완료. 동일 파일 즉시 재시도 시작...")
                        self.save_bom_exporter(i, sldprt_file, file_size, self.Solidworks_App)

                        # 성공 시 실패 처리/이메일 전송 없이 다음 파일로 진행
                        if not self.console_mode:
                            current_completed = completed_so_far + (i + 1 - len(failed_files))
                            completed_status = f"{sldprt_file} (크래시 후 재시도 성공)"
                            self.update_progress(
                                current_completed, progress_total, completed_status
                            )
                        self.logger.info("크래시 후 즉시 재시도 성공. 다음 파일로 진행합니다.")
                        continue
                    except Exception as retry_err:
                        # 재시도도 실패하면 기존 에러 처리 플로우로 진행
                        self.logger.error(f"크래시 후 즉시 재시도 실패: {retry_err}")
                        # fallthrough to 공통 에러 처리

                # --- 공통 에러 처리 (스크린샷/이메일/실패 목록 추가) ---
                # handle_error 함수로 스크린샷 저장 및 이메일 전송
                try:
                    screenshot_path, timestamp = self.handle_error(
                        e,
                        context=e_content,
                        mail_title_prefix=f"[B2E] Error - File {i+1}/{len(files_to_process)} (Attempt {attempt})",
                        send_email=True,
                    )
                except Exception as handle_err:
                    self.logger.error(f"공통 에러 처리 실패: {handle_err}")

                # 일반 에러 또는 재시도 실패 시 UI 정리 시도
                try:
                    self._cleanup_ui_state(self.Solidworks_App)
                except Exception as cleanup_error:
                    self.logger.warning(
                        f"오류 복구 중 UI 정리 실패 (무시하고 계속): {cleanup_error}"
                    )

                failed_files.append(files_to_process[i])
                self.logger.debug(
                    f"실패 파일 목록에 추가: {sldprt_file}. 현재 {attempt}차 시도 실패 수: {len(failed_files)}"
                )

                # --- GUI 모드 진행률 업데이트 (실패) ---
                if not self.console_mode:
                    current_completed = completed_so_far + (i + 1 - len(failed_files))
                    failed_status = f"{sldprt_file} 실패"
                    self.update_progress(current_completed, progress_total, failed_status)

                time.sleep(self.my_pace)
                continue

        # 크레딧은 파일별로 이미 차감되었으므로 일괄 차감 제거
        # (중복 차감 방지: 각 파일 처리 성공 시 이미 deduct_credits_by_policy 호출됨)

        if self.Solidworks_App:
            self.logger.debug(f"솔리드웍스 앱 종료 ({attempt}차 시도 완료)")
            self.Solidworks_App.kill(soft=False)
            self.logger.debug(f"솔리드웍스 앱 종료 완료")
            self.Solidworks_App = None

        end_time = time.time()
        total_elapsed_time = end_time - start_time
        hours, remainder = divmod(total_elapsed_time, 3600)
        minutes, seconds = divmod(remainder, 60)
        average_time = (
            int(total_elapsed_time / len(files_to_process)) if len(files_to_process) > 0 else 0
        )

        end = datetime.datetime.fromtimestamp(end_time).strftime(timestamp_format)
        self.logger.info(f"{attempt}차 시도 완료 - Started at: {start}")
        self.logger.info(f"{attempt}차 시도 완료 - Finished at: {end}")
        self.logger.info(
            f"{attempt}차 시도 - BOM to Excel has been finished at: {end}\n"
            f"Total time taken: {int(hours)} hours, {int(minutes)} minutes, {int(seconds)} seconds\n"
            f"for {len(files_to_process)} files at average {average_time} sec.\n"
            f"Failed files: {len(failed_files)}"
        )

        return failed_files

    def _press_escape_multiple(self, count=3):
        """ESC 키를 여러 번 눌러 모달 대화상자 닫기"""
        self.logger.debug(f"다음 액션을 위해 ESC 키를 {count}회 누릅니다.")
        for _ in range(count):
            pyautogui.press("escape")
            time.sleep(self.my_pace)  # 각 ESC 입력 사이에 짧은 딜레이를 줍니다.

    def _dismiss_common_dialogs(self, app=None, attempts=2):
        """남아있는 파일 열기/저장/오류 모달을 보수적으로 닫는다.

        안전 원칙:
        - 메인 SolidWorks 창에는 절대 close/Alt+F4를 시도하지 않는다.
        - 공용 파일 대화상자(Open/Save)와 명시적 오류/경고 창만 대상으로 한다.
        - 버튼 클릭 또는 ESC만 사용(Alt+F4 금지). 파일 대화상자에 한해 close 허용.
        """
        try:
            app = app or self.Solidworks_App
            if not app:
                return

            try:
                main_handle = app.top_window().handle
            except Exception:
                main_handle = None

            open_save_keywords = [
                "Open",
                "열기",
                "파일 열기",
                "열기(O)",
                "Save As",
                "저장",
                "다른 이름으로 저장",
                "저장(S)",
            ]
            error_warn_keywords = ["경고", "오류", "오류 보고", "Error", "Warning", "확인"]

            for _ in range(max(1, attempts)):
                try:
                    wins = app.windows()
                except Exception:
                    wins = []

                closed_any = False
                for w in wins:
                    # 메인 창은 건너뛴다
                    try:
                        if main_handle and getattr(w, "handle", None) == main_handle:
                            continue
                    except Exception:
                        pass

                    try:
                        title = (w.window_text() or "").strip()
                    except Exception:
                        title = ""

                    try:
                        cls_name = ""
                        try:
                            cls_name = w.class_name()
                        except Exception:
                            cls_name = ""
                        friendly = ""
                        try:
                            friendly = w.friendly_class_name() or ""
                        except Exception:
                            friendly = ""
                    except Exception:
                        cls_name = ""
                        friendly = ""

                    is_dialogish = ("#32770" in cls_name) or ("Dialog" in friendly)
                    is_open_save = is_dialogish and any(
                        k.lower() in title.lower() for k in open_save_keywords
                    )
                    is_error_warn = is_dialogish and any(
                        k.lower() in title.lower() for k in error_warn_keywords
                    )

                    if not (is_open_save or is_error_warn):
                        continue

                    self.logger.debug(
                        f'남아있는 대화상자 감지: title="{title}", class="{cls_name}", friendly="{friendly}"'
                    )

                    # 닫기 우선: 취소/아니오/확인/닫기 버튼 → (파일대화상자만)close → ESC
                    try:
                        clicked = False
                        for btn_name in [
                            "취소",
                            "Cancel",
                            "아니오",
                            "No",
                            "확인",
                            "OK",
                            "닫기",
                            "Close",
                        ]:
                            try:
                                btn = w.child_window(title_re=btn_name, control_type="Button")
                                if btn.exists() and btn.is_enabled():
                                    w.set_focus()
                                    btn.click_input()
                                    self.logger.debug(f"버튼 클릭으로 대화상자 닫음: {btn_name}")
                                    closed_any = True
                                    clicked = True
                                    break
                            except Exception:
                                continue

                        if not clicked and is_open_save:
                            try:
                                w.close()
                                self.logger.debug("파일 대화상자 close() 호출")
                                closed_any = True
                            except Exception:
                                pass

                        if not clicked and not closed_any:
                            try:
                                w.set_focus()
                            except Exception:
                                pass
                            pyautogui.press("escape")
                            self.logger.debug("ESC로 대화상자 닫기 시도")
                            closed_any = True
                    except Exception as ce:
                        self.logger.debug(f"대화상자 닫기 중 경고(무시): {ce}")

                if not closed_any:
                    break

            # 메인 창 포커스 복원
            try:
                app.top_window().set_focus()
            except Exception:
                pass
        except Exception as e:
            self.logger.debug(f"_dismiss_common_dialogs 중 예외(무시): {e}")

    def _cleanup_ui_state(self, app=None):
        """남은 모달 정리 + 포커스 복원 (ESC는 _dismiss_common_dialogs에서만 사용)"""
        app = app or self.Solidworks_App
        if not app:
            self.logger.debug("_cleanup_ui_state: app이 None이므로 정리 생략")
            return

        try:
            # 남아있는 대화상자 정리 (내부적으로 ESC 사용)
            # dismiss_common_dialogs 함수는 필요 없을 수도 있음. esc로 충분할 수 있음.
            # 몇 번 더 테스트 해보고 문제 없으면 제거할 예정
            # self._dismiss_common_dialogs(app, attempts=2)
            pyautogui.press("escape")
            self.logger.debug("_cleanup_ui_state: 남아있는 대화상자 정리 및 ESC 입력 완료")
        finally:
            # 포커스 복원만 수행 (중복 ESC 제거)
            try:
                app.top_window().set_focus()
                self.Solidworks_App.top_window().set_focus()
                self.logger.debug("_cleanup_ui_state: 메인 창 포커스 복원 완료")
            except Exception as e:
                self.logger.debug(f"_cleanup_ui_state: 포커스 복원 실패 (무시): {e}")

    def _handle_final_results(self):
        """최종 결과 처리 - 1차/2차 시도 구분 및 상세 보고"""
        timestamp_format = "%Y/%m/%d %H:%M:%S"
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

        num_missed_files = len(self.sldprt_files_missed)
        original_total = (
            len(self.sldprt_files) if hasattr(self, "sldprt_files") else self.total_count
        )
        first_attempt_failed_count = getattr(self, "first_attempt_failed_count", 0)

        if self.credit_shortage_stop:
            num_missed_files = original_total - self.files_processed_before_stop

        self.logger.debug(f"최종 저장 못한 파일 개수: {num_missed_files}")
        self.logger.debug(f"원본 총 파일 수: {original_total}")
        self.logger.debug(f"1차 시도 실패 파일 수: {first_attempt_failed_count}")

        if num_missed_files > 0:
            # 실패한 파일 목록 저장
            bom_missed = f"{self.WORK_DIR}/missed_file_list_{timestamp}.txt"
            self.logger.debug(
                f"A list of missed files are {[f[0] for f in self.sldprt_files_missed]}"
            )
            self.logger.debug(f"Attached files are {bom_missed}")

            missed_files_content = [f"{file[0]}\n" for file in self.sldprt_files_missed]
            with open(bom_missed, "w") as file:
                file.writelines(missed_files_content)
            file.close()

            attach = [bom_missed, self.logfile]
            failed_count = len(self.sldprt_files_missed)
            total_time_info = getattr(self, "total_processing_time", "N/A")

            if self.credit_shortage_stop:
                title = f"[B2E] [Credit Stop] {self.user_email} - 크레딧 부족으로 작업 중단"
                content = f"""사용자: {self.user_email}\r\n
총 처리 대상 파일: {original_total}개\r\n\r\n
=== 처리 결과 ===\r\n
• 처리 성공: {self.files_processed_before_stop}개\r\n
• 처리 실패(크레딧 부족): {num_missed_files}개\r\n\r\n
크레딧 부족으로 작업이 중단되었습니다."""
            else:
                title = f"[B2E] [Final Failed] {self.user_email} - {failed_count}개 파일 최종 실패 (2차 시도 완료)"
                content = f"""사용자: {self.user_email}\r\n
총 처리 대상 파일: {original_total}개\r\n\r\n
=== 처리 결과 ===\r\n
• 1차 시도 성공: {original_total - first_attempt_failed_count}개\r\n
• 1차 시도 실패: {first_attempt_failed_count}개\r\n
• 2차 시도 성공: {first_attempt_failed_count - failed_count}개\r\n
• 2차 시도 실패 (최종 실패): {failed_count}개\r\n\r\n
=== 시간 정보 ===\r\n
총 소요 시간: {total_time_info}\r\n\r\n
=== 최종 실패 파일 목록 ===\r\n
{chr(10).join([f[0] for f in self.sldprt_files_missed])}\r\n
최종 실패한 {failed_count}개 파일은 수동 처리가 필요합니다."""

            sender = self.report_email

            try:
                wfm.init(self.itself_dir)
                wfm.mail_send_attach(title, sender, content, attach)
                self.logger.info(f"최종 실패 결과 이메일 전송 완료")
            except Exception as mail_e:
                self.logger.error(f"메일 전송 실패: {mail_e}")

            if self.console_mode:
                self.logger.warning(
                    f"2차 시도까지 완료했지만 BOM이 엑셀로 저장되지 않은 파일이 {num_missed_files}개 있습니다."
                )
                self.logger.warning(f"missed_file_list_{timestamp}.txt 파일을 확인하시기 바랍니다.")

        else:
            # === 성공 메일 전송 (첨부파일 없이) ===
            self.logger.info("=" * 50)
            self.logger.info("모든 파일 처리 성공 - 성공 메일 전송 시작")
            self.logger.info("=" * 50)

            total_time_info = getattr(self, "total_processing_time", "N/A")

            if first_attempt_failed_count > 0:
                title = f"[B2E] [Success with Retry] {self.user_email} - 재시도를 통한 전체 완료"
                first_failed_files = getattr(self, "first_attempt_failed_files", [])
                first_failed_list = (
                    chr(10).join([f[0] for f in first_failed_files])
                    if first_failed_files
                    else "파일 목록 정보 없음"
                )

                content = f"""사용자: {self.user_email}\r\n
총 처리 대상 파일: {original_total}개\r\n\r\n
=== 처리 결과 ===\r\n
• 1차 시도 성공: {original_total - first_attempt_failed_count}개\r\n
• 1차 시도 실패: {first_attempt_failed_count}개\r\n
• 2차 시도 성공: {first_attempt_failed_count}개\r\n
• 최종 성공: {original_total}개 (100%)\r\n\r\n
=== 시간 정보 ===\r\n
총 소요 시간: {total_time_info}\r\n\r\n
=== 1차 시도에서 실패했던 파일 목록 ===\r\n
{first_failed_list}\r\n\r\n
재시도 로직을 통해 모든 파일이 성공적으로 처리되었습니다."""

                self.logger.info(f"2차 시도를 통한 전체 작업 완료: {original_total}개 파일")
                if self.console_mode:
                    self.logger.info(f"모든 BOM 파일이 성공적으로 엑셀로 저장되었습니다.")
                    self.logger.info(
                        f"1차 시도: {original_total - first_attempt_failed_count}개 성공, 2차 시도: {first_attempt_failed_count}개 성공"
                    )

            else:
                title = f"[B2E] [Success First Try] {self.user_email} - 1차 시도 전체 완료"
                content = f"""사용자: {self.user_email}\r\n
총 처리 대상 파일: {original_total}개\r\n\r\n
=== 처리 결과 ===\r\n
• 1차 시도 성공: {original_total}개 (100%)\r\n
• 재시도 필요 없음\r\n\r\n
=== 시간 정보 ===\r\n
총 소요 시간: {total_time_info}\r\n\r\n
모든 파일이 1차 시도에서 성공적으로 처리되었습니다."""

                self.logger.info(f"1차 시도에서 전체 작업 완료: {original_total}개 파일")
                if self.console_mode:
                    self.logger.info(
                        "모든 BOM 파일이 1차 시도에서 성공적으로 엑셀로 저장되었습니다."
                    )

            sender = self.report_email

            self.logger.info(f"이메일 전송 준비:")
            self.logger.info(f"  제목: {title}")
            self.logger.info(f"  수신자: {sender}")
            self.logger.info(f"  첨부파일: 없음")

            try:
                self.logger.info("wfm.init() 호출 중...")
                wfm.init(self.itself_dir)
                self.logger.info("wfm.init() 완료")

                self.logger.info("wfm.mail_send_attach() 호출 중...")
                # 성공 시에는 첨부파일 없이 전송 (None 전달)
                wfm.mail_send_attach(title, sender, content, None)
                self.logger.info(f"✅ 성공 결과 이메일 전송 완료!")
            except Exception as mail_e:
                self.logger.error(f"❌ 메일 전송 실패: {mail_e}")
                import traceback

                self.logger.error(f"상세 오류:\n{traceback.format_exc()}")

        # 세션 재개 파일 목록 저장/정리
        try:
            folder_base = (
                Path(self.SLDDRW_PATH)
                if hasattr(self, "SLDDRW_PATH")
                else (Path(self.folder_path) if self.folder_path else None)
            )
            if folder_base is not None:
                pending_path = folder_base / "wf_pending_list.txt"
                if self.credit_shortage_stop and getattr(self, "remaining_files_after_stop", None):
                    # 파일명(베이스네임)만 저장하여 경로 이동 변화에도 견고하게
                    names = [Path(p).name for p in self.remaining_files_after_stop if p]
                    if names:
                        tmp = pending_path.with_suffix(".tmp")
                        with open(tmp, "w", encoding="utf-8") as f:
                            for n in names:
                                f.write(n + "\n")
                        # 원자적 치환
                        os.replace(tmp, pending_path)
                        self.logger.info(f"잔여 파일 목록 저장: {pending_path} ({len(names)}개)")
                else:
                    # 완료 또는 크레딧 이외 중단: 보류 목록 제거
                    if pending_path.exists():
                        try:
                            pending_path.unlink()
                            self.logger.info(f"보류 목록 삭제: {pending_path}")
                        except Exception as ue:
                            self.logger.warning(f"보류 목록 삭제 실패(무시): {ue}")
        except Exception as pe:
            self.logger.warning(f"보류 목록 처리 중 경고(무시): {pe}")

        return self.sldprt_files_missed


# ===== argv 설정 =====
def set_argv(*args):
    """argv 설정"""
    if not args:
        return

    # 단일 문자열로 전달된 경우 공백으로 분리
    if len(args) == 1 and isinstance(args[0], str) and " " in args[0]:
        args = args[0].split()

    if not args[0].endswith(".py"):
        sys.argv = [sys.argv[0]] + list(args)
    else:
        sys.argv = list(args)

    # Debug: Uncomment for development debugging
    # print(f"[argv 설정] sys.argv = {sys.argv}")


def parse_arguments():
    """명령행 인자 파싱"""
    parser = argparse.ArgumentParser(description="BOM 자동 추출 도구")
    parser.add_argument("--folders", nargs="+", help="처리할 폴더 목록 (필수)", required=True)
    parser.add_argument("--repeat", type=int, default=1, help="반복 횟수 (기본값: 1)")

    return parser.parse_args()


def main():
    """메인 함수 - Non-UI 모드 전용"""
    # 콘솔 모드 전용 로거 (간단한 print 스타일)
    console_logger = wflog.get_app_logger("bom_exporter_console", console_level=logging.INFO)
    console_logger.info("Bom Exporter Automation - Non-UI Mode")

    args = parse_arguments()

    if not args.folders:
        console_logger.error("오류: --folders 옵션으로 처리할 폴더를 지정해주세요.")
        console_logger.info('사용법: python automation.py --folders "폴더1" "폴더2" --repeat 횟수')
        return

    console_logger.info(f"처리할 폴더: {args.folders}")
    console_logger.info(f"반복 횟수: {args.repeat}")

    # 회차별로 새로운 인스턴스 생성
    for repeat_idx in range(args.repeat):
        console_logger.info(f"\n===== 반복 {repeat_idx + 1}/{args.repeat} 시작 =====")

        # 매 회차마다 새로운 인스턴스 생성
        app = None

        for folder_idx, folder_path in enumerate(args.folders):
            folder_path_obj = Path(folder_path)
            if not folder_path_obj.is_dir():
                console_logger.error(f"{folder_path} 폴더가 존재하지 않습니다.")
                continue

            console_logger.info(
                f"폴더 {folder_idx + 1}/{len(args.folders)}: {folder_path} 처리 중..."
            )

            if app is None:
                console_logger.info(f"BomAutomation 인스턴스 생성 중...")
                app = BomAutomation(folder_path=folder_path, console_mode=True)

            # 라이선스 체크 (배포 설정에 따라 조건부 실행)
            if app.ENABLE_LICENSE_CHECK_IN_CONSOLE:
                if not app.check_license():
                    console_logger.error("라이선스가 유효하지 않습니다. 프로그램을 종료합니다.")
                    return
            else:
                console_logger.info("Non-UI 모드: 라이선스 체크 비활성화됨 (테스트 모드)")

            # 각 폴더마다 새로운 타임스탬프로 BOM 폴더 생성하여 처리
            app.process_folder(folder_path)
            console_logger.info(f"process_folder({folder_path}) 실행 완료")

        # 메모리 정리
        del app
        gc.collect()
        console_logger.info(f"===== 반복 {repeat_idx + 1}/{args.repeat} 종료 =====")

    console_logger.info("모든 작업이 완료되었습니다.")


# ===== 메인 실행 =====
if __name__ == "__main__":
    # 테스트용 인자 설정 - 3개 폴더, 5회 반복
    set_argv(
        "--folders",
        r"D:\assy_samples\sample03",
        r"D:\assy_samples\sample13",
        r"D:\assy_samples\sample53",
        r"D:\assy_samples\sample61",
        "--repeat",
        "3",
    )
    # set_argv('--folders', r'D:\assy_samples\sample03', r'D:\assy_samples\sample13', r'D:\assy_samples\sample53', r'D:\assy_samples\sample61', '--repeat', '1')
    # set_argv('--folders', r'D:\assy_samples\sample13', '--repeat', '3')
    # set_argv('--folders', r'D:\assy_samples\sample53', r'D:\assy_samples\sample61', '--repeat', '3')
    # set_argv('--folders', r'D:\assy_samples\sample53', '--repeat', '1')
    # 인자 없이 실행하면 사용법 안내 (로거 초기화 전이므로 print 사용)
    if len(sys.argv) == 1:
        print(
            """
Bom Exporter Automation - 솔리드웍스 BOM 자동 추출 도구

사용법:
    python automation.py --folders "폴더1" "폴더2" ... --repeat 횟수

예시:
    python automation.py --folders "D:\\samples\\assy1" --repeat 1
    python automation.py --folders "D:\\folder1" "D:\\folder2" "D:\\folder3" --repeat 3
    
옵션:
    --folders : 처리할 폴더 목록 (필수)
    --repeat  : 반복 횟수 (기본값: 1)
        """
        )
        sys.exit(0)

    main()
