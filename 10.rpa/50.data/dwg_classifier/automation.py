# -*- coding: utf-8 -*-
"""
DWG Classifier Automation Module
DWG 파일을 분류하고 정리하는 자동화 모듈
"""

import os
import sys
import logging
import datetime
import threading
import time
import queue
import hashlib
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable
import pandas as pd
import shutil

# 10.common 모듈 경로 추가
common_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "10.common"))
if common_path not in sys.path:
    sys.path.insert(0, common_path)

from wf_log import get_app_logger

# 이메일 모듈 import
try:
    import wf_email as wfm
except ImportError:
    wfm = None

# 현재 스크립트 디렉토리
current_dir = os.path.dirname(os.path.abspath(__file__))


class DwgClassifierAutomation:
    """DWG 파일 분류 자동화 클래스"""

    def __init__(self, folder_path: Optional[str] = None, console_mode: bool = False):
        self.folder_path = folder_path
        self.console_mode = console_mode
        self.logger = get_app_logger("dwg_classifier", console_level=logging.DEBUG)

        # 이메일 설정 (에러/완료 알림용)
        self.itself_dir = current_dir
        self.user_email = ""
        self.report_email = ""

        # 로그 디렉토리 설정
        run_mode = os.environ.get("WF_RPA_MODE", "release")
        if run_mode in ("dev", "demo"):
            log_dir_path = Path(current_dir) / "logs"
        else:
            log_dir_path = Path.home() / ".wf_rpa" / "dwg_classifier" / "logs"
        log_dir_path.mkdir(parents=True, exist_ok=True)
        self.log_dir = str(log_dir_path).replace("\\", "/")
        self.logfile = str(log_dir_path / f"{time.strftime('%Y%m%d')}.txt").replace("\\", "/")

        # 이메일 설정 초기화
        self._init_email_settings()

        # 설정 로드 (config 속성 초기화)
        try:
            from app_setting_data import get_config as _get_config
            self.config = _get_config()
            self.run_mode = getattr(self.config, "run_mode", "release")
        except Exception:
            self.config = None
            self.run_mode = "release"
        # 데모 캡처 비활성화 (사용하지 않음)
        self.demo_capture_enabled = False
        self.demo_capture_dir = None
        self.demo_capture_size = (1920, 1040)
        self._last_demo_capture_ts = 0.0
        # Demo capture scheduler (single cadence)
        self.demo_fps = 2              # captures per second (scheduler pacing)
        self._demo_queue: Optional[queue.Queue] = None
        self._demo_worker: Optional[threading.Thread] = None
        self._demo_stop_event: Optional[threading.Event] = None
        self._last_demo_worker_ts: float = 0.0

        # UI 콜백 함수들
        self.progress_callback = None
        self.credit_update_callback = None
        self.file_processing_start_callback = None
        self.capture_callback = None

        # 크레딧 관리자
        self.credit_manager = None

        # 처리 통계
        self.total_count = 0
        self.processed_count = 0
        self.failed_files = []
        self.excel_files = []  # 선택된 엑셀 파일 목록

        # 분류 결과
        self.classification_results = []

        # 크레딧 관련 설정
        self.credit_per_work = 50  # 1개 DWG 파일당 50 크레딧
        self.credit_shortage_stop = False
        
        # 설정 파일에서 컬럼명 로드
        # 기본값을 UI 기본과 일치시켜 사용자 혼동 감소
        self.drawing_column = "도번/규격"  # 기본값 (settings.json 없을 때)
        self.category_column = "제조사/가공분류"  # 기본값 (settings.json 없을 때)
        self.excel_sheet_name = "구매요청"  # 기본값 (settings.json에 있을 경우 덮어씀)
        self.case_sensitive = False  # 기본값
        self.file_operation_mode = "copy"  # 기본값: 복사 모드
        self._load_settings()
        
        # 크레딧 제한으로 인한 파일 제한
        self.limited_file_list = None  # 처리할 파일 목록 (제한 있을 때)

        # 재실행 관련 플래그 (UI에서 제어)
        self.ignore_processed_for_rerun = False  # 완료된 폴더 재실행 시 처리된 파일 필터링 무시
        self.only_count_new_duplicates = False   # 이번 실행에서 생성된 중복 파일만 통계 집계

        # 데모 모드 캡처 초기화
        if self.demo_capture_enabled:
            self._init_demo_capture()

        # 크레딧 부족 시 계속 진행 여부 (글로벌 설정)
        self.allow_continue_on_credit_shortage = self._load_allow_continue_flag()

        # 처리된 파일 추적 (settings.json에서 로드)
        self.processed_files_cache = self._load_processed_files()

        self.logger.info("DWG Classifier 자동화 모듈이 초기화되었습니다.")


    def set_progress_callback(self, callback: Callable):
        """진행률 업데이트 콜백 설정"""
        self.progress_callback = callback

    def _init_email_settings(self):
        """이메일 설정 초기화 (wf_rpa_config.json에서 로드)"""
        try:
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

        except Exception as e:
            self.logger.warning(f"이메일 설정 로드 실패: {e}")

        self.logger.debug(f"이메일 설정: user={self.user_email}, report={self.report_email}")

    def handle_error(self, error, context="", mail_title_prefix="[DC] [Error]", send_email=True):
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
            import pyautogui
            screenshot = pyautogui.screenshot()
            screenshot_path = Path(self.log_dir) / f"{timestamp4img}.png"
            screenshot.save(str(screenshot_path))
            self.logger.debug(f"스크린샷 저장: {screenshot_path}")
        except Exception as e:
            self.logger.warning(f"스크린샷 캡처 실패: {e}")

        # 이메일 전송
        if send_email and wfm and self.report_email and hasattr(wfm, 'mail_send_attach'):
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

    def send_completion_email(self, total_count: int, classified_count: int, failed_count: int):
        """작업 완료 이메일 전송

        Args:
            total_count: 전체 파일 수
            classified_count: 분류된 파일 수
            failed_count: 실패 파일 수
        """
        if not wfm or not self.report_email or not hasattr(wfm, 'mail_send_attach'):
            self.logger.debug("이메일 전송 건너뜀 (설정 없음)")
            return

        try:
            wfm.init(self.itself_dir)
            mail_title = f"[DC] [Complete] {self.user_email}"
            content = (
                f"DWG 분류 완료\n\n"
                f"• 전체: {total_count}개\n"
                f"• 분류 성공: {classified_count}개\n"
                f"• 실패: {failed_count}개\n"
            )
            attach = [self.logfile]
            wfm.mail_send_attach(mail_title, self.report_email, content, attach)
            self.logger.info("완료 이메일 전송 완료")
        except Exception as e:
            self.logger.error(f"완료 이메일 전송 실패: {e}")

    def _get_file_hash(self, file_path: str) -> str:
        """SHA256 파일 해시 계산 (첫 1MB만 사용하여 속도 향상)"""
        try:
            sha256 = hashlib.sha256()
            with open(file_path, 'rb') as f:
                # 대용량 파일의 경우 첫 1MB만 읽어서 해시 계산 (성능 최적화)
                chunk = f.read(1024 * 1024)  # 1MB
                if chunk:
                    sha256.update(chunk)
            return sha256.hexdigest()
        except Exception as e:
            self.logger.warning(f"파일 해시 계산 실패 {file_path}: {e}")
            return ""

    def _load_processed_files(self) -> Dict[str, Any]:
        """settings.json에서 처리된 파일 목록 로드"""
        try:
            from app_setting_data import get_config
            config = get_config()
            settings_file = config.settings_file
            
            if settings_file.exists():
                with open(settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    return settings.get('processed_files', {})
        except Exception as e:
            self.logger.warning(f"처리된 파일 목록 로드 실패: {e}")
        return {}

    def _load_allow_continue_flag(self) -> bool:
        """wf_rpa_config.json에서 크레딧 부족 시 계속 진행 플래그 로드"""
        try:
            cfg_path = Path(__file__).parent / "config" / "wf_rpa_config.json"
            if cfg_path.exists():
                with open(cfg_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return bool(data.get("system_settings", {}).get("allow_continue_on_credit_shortage", False))
        except Exception as e:
            self.logger.warning(f"글로벌 설정 로드 실패(continue on credit shortage): {e}")
        return False

    def _save_processed_file(self, file_path: str, file_hash: str):
        """파일을 처리된 목록에 저장"""
        try:
            from app_setting_data import get_config
            config = get_config()
            settings_file = config.settings_file
            
            if settings_file.exists():
                with open(settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                
                if 'processed_files' not in settings:
                    settings['processed_files'] = {}
                
                # 절대경로 저장
                abs_path = os.path.abspath(file_path)
                settings['processed_files'][abs_path] = {
                    'hash': file_hash,
                    'timestamp': datetime.datetime.now().isoformat()
                }

                # 인메모리 캐시도 즉시 반영하여 이후 스캔에서 바로 제외되도록 함
                self.processed_files_cache[abs_path] = {
                    'hash': file_hash,
                    'timestamp': datetime.datetime.now().isoformat()
                }
                
                with open(settings_file, 'w', encoding='utf-8') as f:
                    json.dump(settings, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.warning(f"파일 처리 저장 실패 {file_path}: {e}")

    def _is_file_already_processed(self, file_path: str) -> bool:
        """파일이 이미 처리되었는지 확인 (해시 기반)"""
        try:
            abs_path = os.path.abspath(file_path)
            if abs_path in self.processed_files_cache:
                stored_item = self.processed_files_cache[abs_path]
                stored_hash = stored_item if isinstance(stored_item, str) else stored_item.get('hash', '')
                
                current_hash = self._get_file_hash(file_path)
                if current_hash and stored_hash == current_hash:
                    return True
        except Exception as e:
            self.logger.debug(f"처리 확인 실패 {file_path}: {e}")
        return False

    def _clear_processed_files(self):
        """처리된 파일 리스트 초기화 (작업 완료 시)"""
        try:
            from app_setting_data import get_config
            config = get_config()
            settings_file = config.settings_file
            
            if settings_file.exists():
                with open(settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                
                # processed_files 초기화
                settings['processed_files'] = {}
                
                with open(settings_file, 'w', encoding='utf-8') as f:
                    json.dump(settings, f, ensure_ascii=False, indent=2)
                
                # 캐시도 초기화
                self.processed_files_cache = {}
                self.logger.info("처리된 파일 목록 초기화 완료")
            
            # 세션 상태 파일 삭제
            if self.folder_path:
                session_file = Path(self.folder_path) / ".dwg_session.json"
                if session_file.exists():
                    session_file.unlink()
                    self.logger.info(f"세션 상태 파일 삭제: {session_file}")
        except Exception as e:
            self.logger.warning(f"처리 파일 목록 초기화 실패: {e}")

    def has_credit_shortage_interruption(self) -> bool:
        """크레딧 부족으로 중단된 기록이 있는지 확인
        wf_pending_list.txt 파일이 존재하면 크레딧 부족으로 중단된 상태"""
        if not self.folder_path:
            return False
        try:
            pending_path = Path(self.folder_path) / "wf_pending_list.txt"
            return pending_path.exists()
        except Exception:
            return False

    def count_classified_files(self) -> int:
        """classified_dwg 폴더의 DWG 파일 개수 반환 (copy 모드)"""
        if not self.folder_path or self.file_operation_mode != "copy":
            return 0
        try:
            classified_folder = Path(self.folder_path) / "classified_dwg"
            if classified_folder.exists() and classified_folder.is_dir():
                return sum(1 for _ in classified_folder.rglob("*.dwg"))
            return 0
        except Exception:
            return 0

    def set_credit_manager(self, credit_manager):
        """크레딧 매니저 설정"""
        self.credit_manager = credit_manager
        if credit_manager:
            # 크레딧 매니저에서 설정 읽기
            status = credit_manager.get_credit_status()
            self.credit_per_work = status.get("credit_per_work", 50)
            self.logger.info(f"크레딧 설정: 1개 작업당 {self.credit_per_work} 크레딧")

    def set_credit_update_callback(self, callback: Callable):
        """크레딧 업데이트 콜백 설정"""
        self.credit_update_callback = callback

    def set_file_processing_start_callback(self, callback: Callable):
        """파일 처리 시작 콜백 설정"""
        self.file_processing_start_callback = callback

    # ===== 데모 캡처 헬퍼 =====
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

    def _start_demo_capture_worker(self):
        """데모 캡처 워커 시작 (페이싱된 캡처)"""
        if not self.demo_capture_enabled or not self.demo_capture_dir:
            return

        if self._demo_worker and self._demo_worker.is_alive():
            return

        self._demo_queue = queue.Queue()
        self._demo_stop_event = threading.Event()
        self._last_demo_worker_ts = 0.0

        def _worker():
            interval = 1.0 / max(1, int(self.demo_fps))
            last_reason = None
            while self._demo_stop_event and not self._demo_stop_event.is_set():
                try:
                    # 수집 (최신 이벤트로 치환)
                    if self._demo_queue:
                        try:
                            reason = self._demo_queue.get(timeout=0.1)
                            last_reason = reason
                        except Exception:
                            pass

                    now = time.perf_counter()
                    if last_reason and (now - self._last_demo_worker_ts) >= interval:
                        # 페이싱된 캡처 실행
                        try:
                            self._capture_demo_now(last_reason, throttle_sec=0.0)
                        except Exception as e:
                            self.logger.debug(f"[DEMO] 워커 캡처 실패(무시): {e}")
                        self._last_demo_worker_ts = now
                        last_reason = None
                except Exception:
                    pass

        self._demo_worker = threading.Thread(target=_worker, name="demo-capture-worker", daemon=True)
        self._demo_worker.start()

    def _stop_demo_capture_worker(self):
        """데모 캡처 워커 중지"""
        try:
            if self._demo_stop_event:
                self._demo_stop_event.set()
            if self._demo_worker and self._demo_worker.is_alive():
                self._demo_worker.join(timeout=1.0)
        except Exception:
            pass
        finally:
            self._demo_worker = None
            self._demo_queue = None
            self._demo_stop_event = None

    def _enqueue_demo_capture(self, reason: str):
        """데모 캡처 이벤트 큐에 적재 (워커가 페이싱하여 저장)"""
        if not self.demo_capture_enabled or not self._demo_queue:
            return
        try:
            self._demo_queue.put_nowait(str(reason))
        except Exception:
            pass

    def _demo_pause_on_folder_created(self, folder_path: str):
        """데모 모드에서 폴더 생성 시 처리 (동영상 녹화용으로 사용자 입력 대기 비활성화)"""
        try:
            # 캡처 이벤트 큐잉
            self._enqueue_demo_capture(f"folder_created_{os.path.basename(folder_path)}")

            # 데모 모드: 폴더를 미리 만들어놓고 녹화하므로 사용자 입력 대기 비활성화
            # 콘솔 모드이고 데모가 아닐 때만 사용자 입력 대기
            run_mode = getattr(self.config, "run_mode", "release")
            if self.console_mode and run_mode != "demo":
                # 콘솔에서 사용자 확인 대기
                print(f"\n[DEMO] 폴더 생성됨: {folder_path}")
                print("폴더를 확인하세요. 계속하려면 콘솔에 'y'를 입력하세요.")
                while True:
                    try:
                        resp = input("계속(y): ").strip().lower()
                    except EOFError:
                        # 콘솔 입력 불가 환경이면 즉시 계속
                        break
                    if resp == "y":
                        break
        except Exception as e:
            self.logger.debug(f"[DEMO] 폴더 생성 컨펌 처리 중 경고(무시): {e}")

    def _resolve_demo_capture_dir(self):
        """캡처 디렉터리 해결 (앱 개발 폴더에만 생성)"""
        try:
            demo_dir = Path(__file__).resolve().parent / "demo_captures"
            demo_dir.mkdir(parents=True, exist_ok=True)
            if os.access(demo_dir, os.W_OK):
                return demo_dir
        except Exception as e:
            self.logger.debug(f"[DEMO] 캡처 경로 생성 실패: {e}")
        return None

    def _capture_demo(self, reason: str, delay_ms: int = 0, throttle_sec: float = 0.0):
        """데모 모드 캡처 트리거 (매 이벤트마다 즉시 캡처)"""
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

        # 워커 사용 안 함 - 모든 이벤트 즉시 캡처 (throttle_sec=0.0으로 스로틀링도 비활성화)
        self._capture_demo_now(reason, throttle_sec=0.0)

    def _draw_cursor_on_image(self, img, screen_width: int, screen_height: int):
        """캡처 이미지 위에 커서 PNG를 합성한다"""
        try:
            import ctypes
            from pathlib import Path
            from PIL import Image

            class POINT(ctypes.Structure):
                _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

            pt = POINT()
            ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))

            cursor_x, cursor_y = pt.x, pt.y
            self.logger.debug(f"[DEMO] 마우스 절대 좌표: ({cursor_x}, {cursor_y}), 캡처 영역: {screen_width}x{screen_height}")

            if cursor_x < 0 or cursor_y < 0 or cursor_x >= screen_width or cursor_y >= screen_height:
                self.logger.debug(f"[DEMO] 마우스가 캡처 영역 밖 ({cursor_x}, {cursor_y}) vs ({screen_width}x{screen_height})")
                return img

            if not hasattr(self, "_cursor_img") or self._cursor_img is None:
                base_dir = Path(__file__).resolve().parent
                candidates = [
                    base_dir / "small_arrow.png",
                    base_dir / "cursor_arrow.png",
                ]
                cursor_img = None
                for cand in candidates:
                    try:
                        if cand.exists():
                            cursor_img = Image.open(cand).convert("RGBA")
                            self.logger.debug(f"[DEMO] 커서 이미지 로드: {cand}")
                            break
                    except Exception:
                        continue
                self._cursor_img = cursor_img
                if cursor_img:
                    self._cursor_hotspot = (cursor_img.width // 2, max(0, cursor_img.height - 2))

            cursor_img = getattr(self, "_cursor_img", None)
            hotspot = getattr(self, "_cursor_hotspot", (0, 0))

            if not cursor_img:
                return img

            paste_x = cursor_x - hotspot[0]
            paste_y = cursor_y - hotspot[1]

            if paste_x >= screen_width or paste_y >= screen_height or paste_x + cursor_img.width <= 0 or paste_y + cursor_img.height <= 0:
                return img

            img.paste(cursor_img, (paste_x, paste_y), cursor_img)
            self.logger.debug(f"[DEMO] 마우스 커서 이미지 합성: ({cursor_x}, {cursor_y})")
            return img
        except Exception as e:
            self.logger.warning(f"[DEMO] 커서 그리기 실패: {e}", exc_info=True)
            return img

    def _capture_demo_now(self, reason: str, throttle_sec: float = 0.8):
        """데모 모드 캡처 즉시 실행 (스로틀링 적용)"""
        if not self.demo_capture_enabled or not self.demo_capture_dir:
            return
        try:
            import time as _t
            from PIL import ImageGrab
        except Exception as e:
            self.logger.warning(f"[DEMO] 캡처 불가 (필수 모듈 없음): {e}")
            self.demo_capture_enabled = False
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
            screen_width, screen_height = img.size
            w, h = self.demo_capture_size
            cropped = img.crop((0, 0, w, h))
            
            # 마우스 커서 그리기 (절대 좌표로)
            cropped = self._draw_cursor_on_image(cropped, w, h)
            
            cropped.save(path, "PNG")
            self.logger.debug(f"[DEMO] capture saved ({safe_reason}): {path}")
        except Exception as e:
            self.logger.warning(f"[DEMO] capture failed ({safe_reason}): {e}")

    def _load_settings(self):
        """설정 파일에서 컬럼명 로드"""
        try:
            # 사용자 홈 설정을 우선 사용, 없으면 로컬 번들 설정으로 폴백
            candidates = [
                Path.home() / ".wf_rpa" / "dwg_classifier" / "settings.json",
                Path(__file__).parent / "config" / "dwg_classifier" / "settings.json",
            ]
            # 동결(배포) 환경에서는 실행 파일 인접 경로도 후보에 추가
            try:
                if getattr(sys, "frozen", False):
                    exe_dir = Path(sys.executable).parent
                    candidates.extend(
                        [
                            exe_dir / ".wf_rpa" / "dwg_classifier" / "settings.json",
                            exe_dir / "_internal" / ".wf_rpa" / "dwg_classifier" / "settings.json",
                        ]
                    )
            except Exception:
                pass

            settings_path = next((p for p in candidates if p.exists()), None)
            if not settings_path:
                self.logger.debug("설정 파일을 찾지 못해 기본값을 사용합니다.")
                return

            import json
            with open(settings_path, "r", encoding="utf-8") as f:
                settings = json.load(f)

            classifier_settings = settings.get("classifier_settings", {})
            # Fallback을 영어 내부값 대신 현재 인스턴스 기본값(이미 한글 기본 적용)으로 유지
            self.drawing_column = classifier_settings.get("drawing_column", self.drawing_column)
            self.category_column = classifier_settings.get("category_column", self.category_column)
            # 추가: 시트명 및 옵션 로드
            self.excel_sheet_name = classifier_settings.get("excel_sheet_name", self.excel_sheet_name)
            self.case_sensitive = classifier_settings.get("case_sensitive", self.case_sensitive)
            self.file_operation_mode = classifier_settings.get("file_operation_mode", self.file_operation_mode)

            self.logger.info(
                f"설정 로드({settings_path}): 도번={self.drawing_column}, 분류={self.category_column}, 시트={self.excel_sheet_name}, 대소문자구분={self.case_sensitive}"
            )
        except Exception as e:
            self.logger.warning(f"설정 파일 로드 실패(기본값 사용): {e}")

    def apply_runtime_settings(
        self,
        drawing_column: Optional[str] = None,
        category_column: Optional[str] = None,
        excel_sheet_name: Optional[str] = None,
        case_sensitive: Optional[bool] = None,
        file_operation_mode: Optional[str] = None,
    ):
        """UI에서 갱신된 설정을 런타임 인스턴스에 반영 (재시작 없이 적용)."""
        if drawing_column:
            self.drawing_column = str(drawing_column).strip()
        if category_column:
            self.category_column = str(category_column).strip()
        if excel_sheet_name:
            self.excel_sheet_name = str(excel_sheet_name).strip()
        if case_sensitive is not None:
            self.case_sensitive = bool(case_sensitive)
        if file_operation_mode:
            self.file_operation_mode = str(file_operation_mode).strip()
        self.logger.info(
            f"런타임 설정 적용: 도번={self.drawing_column}, 분류={self.category_column}, 시트={self.excel_sheet_name}, 대소문자구분={self.case_sensitive}, 작업모드={self.file_operation_mode}"
        )
    
    def validate_excel_columns(self) -> Optional[str]:
        """엑셀 파일의 컬럼명 검증. 오류 메시지 반환 (정상이면 None)"""
        if not self.excel_files:
            return "엑셀 파일이 선택되지 않았습니다."
        
        for excel_file in self.excel_files:
            try:
                if not os.path.exists(excel_file):
                    return f"엑셀 파일을 찾을 수 없습니다:\n{excel_file}"
                
                # 지정된 시트명 사용 (기본은 첫번째 시트). 시트명 없으면 인덱스 fallback
                try:
                    df = pd.read_excel(excel_file, sheet_name=self.excel_sheet_name)
                except Exception:
                    df = pd.read_excel(excel_file, sheet_name=0)

                # 컬럼 정규화: 공백/비가시문자 제거
                raw_columns = list(df.columns)
                cleaned_columns = []
                for c in raw_columns:
                    cc = str(c).replace('\u00A0', ' ').strip()
                    cleaned_columns.append(cc)
                df.columns = cleaned_columns

                # 비교 방식 (대소문자 무시 설정 지원)
                def matches(col_name: str, columns: List[str]) -> bool:
                    target = col_name.strip()
                    target = target.replace('\u00A0', ' ')
                    if not self.case_sensitive:
                        target_lower = target.lower()
                        return any(c.lower() == target_lower for c in columns)
                    return target in columns

                cols_list = list(df.columns)
                has_drawing = matches(self.drawing_column, cols_list)
                has_category = matches(self.category_column, cols_list)
                
                if not has_drawing or not has_category:
                    return (
                        f"엑셀 파일에 필요한 컬럼이 없습니다.\n\n"
                        f"파일: {os.path.basename(excel_file)}\n"
                        f"필요한 컬럼: '{self.drawing_column}', '{self.category_column}'\n\n"
                        f"현재 컬럼: {', '.join(df.columns.tolist())}\n\n"
                        f"설정 창에서 컬럼명을 확인하고 수정해주세요."
                    )
            except Exception as e:
                return f"엑셀 파일 읽기 오류:\n{excel_file}\n\n{str(e)}"
        
        return None  # 정상

    def set_file_limit(self, file_list: List[str]):
        """크레딧 제한으로 인한 파일 제한 설정"""
        self.limited_file_list = file_list
        self.logger.info(f"파일 제한 설정: {len(file_list)}개 파일만 처리")
    
    def set_excel_files(self, excel_files: List[str]):
        """분류 규칙이 있는 엑셀 파일 설정"""
        self.excel_files = excel_files or []
        self.logger.info(f"엑셀 파일 {len(self.excel_files)}개 설정됨")

    def scan_dwg_files(self, folder_path: Optional[str] = None) -> List[str]:
        """DWG 파일 스캔 (wf_pending_list.txt 우선 반영)"""
        if folder_path:
            self.folder_path = folder_path

        if not self.folder_path or not os.path.exists(self.folder_path):
            self.logger.error("유효하지 않은 폴더 경로입니다.")
            return []

        # 우선 pending 목록(wf_pending_list.txt) 확인
        folder_base = Path(self.folder_path)
        pending_path = folder_base / "wf_pending_list.txt"
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

        dwg_files = []
        try:
            if pending_names:
                # pending 목록에 있는 파일만 대상 (존재하는 것만)
                for name in pending_names:
                    p = folder_base / name
                    if p.exists() and p.suffix.lower() == ".dwg":
                        dwg_files.append(str(p))
            else:
                # 전체 스캔
                for root, dirs, files in os.walk(self.folder_path):
                    # 분류 결과 폴더(classified_dwg)는 스캔 대상에서 제외 (copy 모드 중복 방지)
                    dirs[:] = [d for d in dirs if d != "classified_dwg"]
                    for file in files:
                        if file.lower().endswith(".dwg"):
                            dwg_files.append(os.path.join(root, file))

            self.total_count = len(dwg_files)
            self.logger.info(f"DWG 파일 {self.total_count}개 발견됨")
            return dwg_files

        except Exception as e:
            self.logger.error(f"DWG 파일 스캔 중 오류: {e}")
            return []

    def load_classification_rules(self) -> Dict[str, Any]:
        """엑셀 파일에서 분류 규칙 로드"""
        rules = {}

        if not self.excel_files:
            self.logger.warning("분류 규칙 엑셀 파일이 지정되지 않았습니다.")
            return rules

        for excel_file in self.excel_files:
            try:
                if not os.path.exists(excel_file):
                    self.logger.warning(f"엑셀 파일을 찾을 수 없습니다: {excel_file}")
                    continue

                # 엑셀 파일 읽기 (시트명 우선)
                try:
                    df = pd.read_excel(excel_file, sheet_name=self.excel_sheet_name)
                except Exception:
                    df = pd.read_excel(excel_file, sheet_name=0)

                # 컬럼 정규화 동일 적용
                df.columns = [str(c).replace('\u00A0', ' ').strip() for c in df.columns]

                def matches(col_name: str, columns: List[str]) -> bool:
                    target = col_name.strip().replace('\u00A0', ' ')
                    if not self.case_sensitive:
                        t = target.lower()
                        return any(c.lower() == t for c in columns)
                    return target in columns

                cols_list = list(df.columns)
                if not matches(self.drawing_column, cols_list) or not matches(self.category_column, cols_list):
                    self.logger.warning(
                        f"필수 컬럼이 없습니다 ({excel_file}): "
                        f"'{self.drawing_column}', '{self.category_column}' 컬럼을 찾을 수 없습니다."
                    )
                    continue

                # 실제 컬럼명 찾기 (case-insensitive 매칭 지원)
                def find_actual_column(target: str, columns: List[str]) -> str:
                    """설정된 컬럼명과 매칭되는 실제 컬럼명 반환"""
                    target_norm = target.strip().replace('\u00A0', ' ')
                    if not self.case_sensitive:
                        t = target_norm.lower()
                        for c in columns:
                            if c.lower() == t:
                                return c
                    return target_norm if target_norm in columns else target

                actual_drawing_col = find_actual_column(self.drawing_column, cols_list)
                actual_category_col = find_actual_column(self.category_column, cols_list)

                # 분류 규칙 추가 (실제 컬럼명 사용)
                for _, row in df.iterrows():
                    pattern = str(row.get(actual_drawing_col, "")).strip()
                    category = str(row.get(actual_category_col, "")).strip()
                    # 줄바꿈/탭 문자를 공백으로 변환 (폴더명에 사용 불가)
                    category = category.replace('\n', ' ').replace('\r', '').replace('\t', ' ')
                    # 연속 공백을 단일 공백으로 정리
                    while '  ' in category:
                        category = category.replace('  ', ' ')
                    folder = str(row.get("folder", category)).strip()
                    # folder도 동일하게 처리
                    folder = folder.replace('\n', ' ').replace('\r', '').replace('\t', ' ')
                    while '  ' in folder:
                        folder = folder.replace('  ', ' ')

                    if pattern and category:
                        if category not in rules:
                            rules[category] = []
                        rules[category].append(
                            {"pattern": pattern, "folder": folder, "source_file": excel_file}
                        )

                self.logger.info(f"분류 규칙 로드 완료: {excel_file}")

            except Exception as e:
                self.logger.error(f"엑셀 파일 읽기 오류 ({excel_file}): {e}")

        self.logger.info(f"총 {len(rules)}개 카테고리의 분류 규칙이 로드되었습니다.")
        return rules

    def classify_file(self, file_path: str, rules: Dict[str, Any]) -> Dict[str, str]:
        """단일 파일 분류"""
        filename = os.path.basename(file_path)
        filename_lower = filename.lower()

        # 공백 정규화 함수 (연속 공백을 단일 공백으로)
        def normalize_spaces(s: str) -> str:
            import re
            return re.sub(r'\s+', ' ', s).strip()

        filename_normalized = normalize_spaces(filename_lower)

        # 기본 분류 결과
        result = {
            "file_path": file_path,
            "filename": filename,
            "category": "_미분류",
            "target_folder": "_미분류",
            "matched_pattern": None,
        }

        # 분류 규칙 적용
        for category, pattern_list in rules.items():
            for rule in pattern_list:
                pattern = rule["pattern"].lower()
                pattern_normalized = normalize_spaces(pattern)

                # 패턴 매칭 (공백 정규화 후 포함 검사)
                if pattern_normalized in filename_normalized:
                    result["category"] = category
                    result["target_folder"] = rule["folder"]
                    result["matched_pattern"] = pattern
                    break

            if result["category"] != "_미분류":
                break

        return result

    def create_target_folders(self, base_path: str, categories: set):
        """대상 폴더 생성"""
        created_folders = []

        for category in categories:
            folder_path = os.path.join(base_path, category)
            try:
                if not os.path.exists(folder_path):
                    os.makedirs(folder_path, exist_ok=True)
                    created_folders.append(folder_path)
                    self.logger.info(f"폴더 생성: {folder_path}")
                    # 데모 모드: 폴더 생성 시 캡처 및 컨펌 처리
                    if self.demo_capture_enabled:
                        self._demo_pause_on_folder_created(folder_path)
            except Exception as e:
                self.logger.error(f"폴더 생성 실패 ({folder_path}): {e}")

        return created_folders

    def move_or_copy_file(self, source_path: str, target_folder: str, use_copy: bool = False) -> Optional[str]:
        """파일 이동 또는 복사
        
        Args:
            source_path: 원본 파일 경로
            target_folder: 대상 폴더 경로
            use_copy: True면 복사, False면 이동 (기본값: False)
            
        Returns:
            성공 시 target_path (str), 실패 시 None
        """
        try:
            created = False
            if not os.path.exists(target_folder):
                os.makedirs(target_folder, exist_ok=True)
                created = True

            filename = os.path.basename(source_path)
            target_path = os.path.join(target_folder, filename)

            # 데모 모드: 새 폴더가 생성된 경우 Explorer 표시 및 콘솔 컨펌
            if created and self.demo_capture_enabled:
                self._demo_pause_on_folder_created(target_folder)

            # 동일한 이름의 파일이 있는 경우 처리
            if os.path.exists(target_path):
                base, ext = os.path.splitext(filename)
                counter = 1
                while os.path.exists(target_path):
                    new_filename = f"{base}_{counter}{ext}"
                    target_path = os.path.join(target_folder, new_filename)
                    counter += 1

            if use_copy:
                shutil.copy2(source_path, target_path)
            else:
                shutil.move(source_path, target_path)
            
            # 데모 모드: 파일 복사/이동 완료 시 즉시 캡처
            if self.demo_capture_enabled:
                action = "copied" if use_copy else "moved"
                self._capture_demo(f"file_{action}_{filename}", delay_ms=50)
            
            return target_path
        except Exception as e:
            action = "복사" if use_copy else "이동"
            self.logger.error(f"파일 {action} 실패 ({source_path}): {e}")
            return None

    def update_progress(self, current: int, total: int, status: str = ""):
        """진행률 업데이트"""
        # 데모 모드: 진행률 업데이트 시 즉시 캡처 (UI 변경 이벤트)
        if self.demo_capture_enabled:
            self._capture_demo(f"progress_{current}of{total}", delay_ms=80)
        
        if self.progress_callback:
            try:
                self.progress_callback(current, total, status)
            except Exception as e:
                self.logger.error(f"진행률 콜백 오류: {e}")

    def deduct_credits(self, file_count: int) -> bool:
        """크레딧 차감 (더 이상 사용되지 않음 - classify_dwg_files에서 직접 처리)"""
        # 이 메서드는 하위 호환성을 위해 유지하지만 실제로는 사용되지 않음
        self.logger.warning("deduct_credits() 호출됨 - 이 메서드는 더 이상 사용되지 않습니다.")
        return True

    def classify_dwg_files(
        self, folder_path: Optional[str] = None, dry_run: bool = False
    ) -> Dict[str, Any]:
        """DWG 파일 분류 실행"""
        if folder_path:
            self.folder_path = folder_path

        start_time = datetime.datetime.now()
        self.logger.info("DWG 파일 분류 시작")
        
        # 데모 모드: 워커 시작 + 시작 캡처
        if self.demo_capture_enabled:
            self._start_demo_capture_worker()
            self._capture_demo("classify_start", delay_ms=100, throttle_sec=0.0)

        # 1. DWG 파일 스캔
        dwg_files = self.scan_dwg_files()
        if not dwg_files:
            return {
                "success": False,
                "message": "DWG 파일을 찾을 수 없습니다.",
                "processed": 0,
                "failed": 0,
            }
        
        # 크레딧 제한이 있으면 해당 파일만 처리
        original_count = len(dwg_files)
        if self.limited_file_list:
            # 파일명 기준으로 필터링
            limited_names = [os.path.basename(f) for f in self.limited_file_list]
            dwg_files = [f for f in dwg_files if os.path.basename(f) in limited_names]
            self.logger.info(f"크레딧 제한 적용: {original_count}개 중 {len(dwg_files)}개 처리")

        # 이미 처리된 파일 필터링 (해시 기반 추적)
        before_filter = len(dwg_files)
        if not self.ignore_processed_for_rerun:
            dwg_files = [f for f in dwg_files if not self._is_file_already_processed(f)]
            if before_filter > len(dwg_files):
                self.logger.info(f"이미 처리된 파일 제외: {before_filter - len(dwg_files)}개 스킵")
        else:
            self.logger.info("완료된 폴더 재실행: 처리 기록을 무시하고 모든 파일을 다시 처리합니다.")

        # 2. 컬럼명 검증
        column_error = self.validate_excel_columns()
        if column_error:
            self.logger.error(f"컬럼 검증 실패: {column_error}")
            return {
                "success": False,
                "message": column_error,
                "processed": 0,
                "failed": 0,
            }
        
        # 3. 분류 규칙 로드
        rules = self.load_classification_rules()
        if not rules:
            self.logger.warning("분류 규칙이 없어 기본 분류를 수행합니다.")

            # 4. 재개 상태 로드 및 per-file 차감 준비
            # 동일 입력 폴더에서 재실행 시 이미 처리된 파일은 건너뜀
            processed_state_path = None
            processed_stems: set = set()
            try:
                if self.folder_path:
                    processed_state_path = Path(self.folder_path) / ".dwg_session.json"
                    if processed_state_path.exists():
                        import json as _json
                        with open(processed_state_path, "r", encoding="utf-8") as _f:
                            _data = _json.load(_f)
                            if _data.get("app") == "dwg_classifier" and _data.get("folder") == str(Path(self.folder_path)):
                                processed_stems = set(_data.get("processed", []))
            except Exception as _e:
                self.logger.warning(f"재개 상태 로드 실패(무시하고 진행): {_e}")

            # 이미 처리된 파일 제외
            if processed_stems:
                before = len(dwg_files)
                dwg_files = [f for f in dwg_files if Path(f).stem not in processed_stems]
                after = len(dwg_files)
                self.logger.info(f"재개 적용: 기존 {before}개 중 {after}개만 처리 (스킵 {before-after}개)")

        # 5. 파일 분류 및 이동
        self.processed_count = 0
        self.failed_files = []
        self.classification_results = []

        # 파일 처리 시작 알림
        if self.file_processing_start_callback:
            try:
                self.file_processing_start_callback()
            except Exception:
                pass

        # 기본 출력 폴더 생성
        if not self.folder_path:
            return {
                "success": False,
                "message": "폴더 경로가 설정되지 않았습니다.",
                "processed": 0,
                "failed": 0,
            }

        output_base = os.path.join(self.folder_path, "classified_dwg")
        
        # 데모 모드: 기존 폴더 재사용 (탐색기를 미리 열어놓고 결과물 저장 모습 보여주기 용)
        # 일반 모드: 폴더가 없을 때만 생성
        run_mode = getattr(self.config, "run_mode", "release")
        if not dry_run:
            if not os.path.exists(output_base):
                os.makedirs(output_base, exist_ok=True)
                # 데모 모드에서만 폴더 생성 시 pause
                if run_mode == "demo" and self.demo_capture_enabled:
                    self._demo_pause_on_folder_created(output_base)
            # 데모 모드: 폴더가 이미 있어도 재사용 (pause 없음)

        # per-file 차감: 각 파일 성공 시 1건 차감 및 상태 저장
        import json as _json
        
        # 세션 상태 파일 경로 초기화
        processed_state_path = None
        processed_stems = set()
        try:
            processed_state_path = Path(self.folder_path) / ".dwg_classifier_session.json"
            if processed_state_path.exists():
                with open(processed_state_path, "r", encoding="utf-8") as _pf:
                    state_data = _json.load(_pf)
                    processed_stems = set(state_data.get("processed", []))
        except Exception as _pe:
            self.logger.debug(f"세션 상태 로드 실패(무시): {_pe}")
        
        for i, dwg_file in enumerate(dwg_files):
            try:
                # 분류 수행
                classification = self.classify_file(dwg_file, rules)
                self.classification_results.append(classification)

                if not dry_run:
                    # 실제 파일 이동 또는 복사
                    use_copy = (self.file_operation_mode == "copy")
                    target_folder = os.path.join(output_base, classification["target_folder"])
                    target_path = self.move_or_copy_file(dwg_file, target_folder, use_copy=use_copy)
                    if target_path:
                        # 파일 처리 성공 시 크레딧 차감 (1건) 먼저 확인
                        if self.credit_manager:
                            try:
                                credit_result = self.credit_manager.deduct_credits_by_policy(
                                    1, f"DWG 분류: {Path(dwg_file).name}"
                                )
                                if credit_result.get("success"):
                                    # 차감 성공: 처리 카운트 증가 및 상태 저장
                                    self.processed_count += 1
                                    if self.credit_update_callback:
                                        self.credit_update_callback()

                                    # 파일 처리 성공 시 해시 저장 (재개 감지용)
                                    file_hash = self._get_file_hash(dwg_file)
                                    if file_hash:
                                        self._save_processed_file(dwg_file, file_hash)

                                    # 세션 상태 파일에 처리 기록 저장
                                    try:
                                        if processed_state_path:
                                            new_processed = set(processed_stems)
                                            new_processed.add(Path(dwg_file).stem)
                                            state_obj = {
                                                "app": "dwg_classifier",
                                                "folder": str(Path(self.folder_path)),
                                                "processed": list(new_processed),
                                                "last_updated": datetime.datetime.now().isoformat(),
                                                "version": "1",
                                            }
                                            with open(processed_state_path, "w", encoding="utf-8") as _sf:
                                                _json.dump(state_obj, _sf, ensure_ascii=False, indent=2)
                                            processed_stems.add(Path(dwg_file).stem)
                                    except Exception as _se:
                                        self.logger.debug(f"세션 상태 저장 실패(무시): {_se}")
                                else:
                                    # 크레딧 부족: 파일 되돌리기 (복사면 삭제, 이동이면 원위치 이동)
                                    self.logger.error(f"크레딧 차감 실패: {credit_result.get('message')}")
                                    try:
                                        if target_path and os.path.exists(target_path):
                                            if use_copy:
                                                os.remove(target_path)
                                            else:
                                                shutil.move(target_path, dwg_file)
                                    except Exception as _rb:
                                        self.logger.warning(f"크레딧 실패 롤백 오류: {_rb}")
                                    self.credit_shortage_stop = True
                                    break
                            except Exception as _ce:
                                self.logger.warning(f"크레딧 차감 오류(무시): {_ce}")
                        else:
                            # 크레딧 관리자가 없으면 처리로 간주
                            self.processed_count += 1
                            file_hash = self._get_file_hash(dwg_file)
                            if file_hash:
                                self._save_processed_file(dwg_file, file_hash)
                            try:
                                if processed_state_path:
                                    new_processed = set(processed_stems)
                                    new_processed.add(Path(dwg_file).stem)
                                    state_obj = {
                                        "app": "dwg_classifier",
                                        "folder": str(Path(self.folder_path)),
                                        "processed": list(new_processed),
                                        "last_updated": datetime.datetime.now().isoformat(),
                                        "version": "1",
                                    }
                                    with open(processed_state_path, "w", encoding="utf-8") as _sf:
                                        _json.dump(state_obj, _sf, ensure_ascii=False, indent=2)
                                    processed_stems.add(Path(dwg_file).stem)
                            except Exception as _se:
                                self.logger.debug(f"세션 상태 저장 실패(무시): {_se}")
                    else:
                        action = "복사" if use_copy else "이동"
                        self.failed_files.append({"file": dwg_file, "error": f"파일 {action} 실패"})
                else:
                    self.processed_count += 1

                # 진행률 업데이트 (매 파일마다)
                self.update_progress(i + 1, len(dwg_files))
                
                # 데모 모드: 파일 분류마다 0.5초 슬립 (파일 생성 과정이 보이도록)
                if run_mode == "demo":
                    import time
                    time.sleep(0.5)

            except Exception as e:
                self.logger.error(f"파일 처리 오류 ({dwg_file}): {e}")
                self.failed_files.append({"file": dwg_file, "error": str(e)})

        # 7. 결과 정리
        end_time = datetime.datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # 데모 모드: 완료 캡처 및 워커 중지
        if self.demo_capture_enabled:
            self._capture_demo("classify_complete", delay_ms=150, throttle_sec=0.0)
            self._stop_demo_capture_worker()
        
        # 폴더별 분류 통계 생성 - 이번 실행에서 처리한 결과만 카운트
        folder_stats = {}
        unclassified_count = 0
        unmatched_files = []
        
        # classification_results를 기반으로 통계 계산 (이번 실행 결과만)
        import re
        def _is_new_duplicate(path: str) -> bool:
            name = os.path.basename(path).lower()
            return bool(re.search(r"_\d+\.dwg$", name)) or bool(re.search(r"\(\d+\)\.dwg$", name))

        for classification in self.classification_results:
            dest = classification.get("destination", "")
            if self.only_count_new_duplicates and dest:
                if not _is_new_duplicate(dest):
                    continue
            folder_name = classification.get("target_folder", "")
            if folder_name == "_미분류" or not folder_name:
                # 미분류 파일 경로 추가
                unclassified_count += 1
                if dest:
                    unmatched_files.append(dest)
            else:
                folder_stats[folder_name] = folder_stats.get(folder_name, 0) + 1

        result = {
            "success": True,
            "processed": self.processed_count,
            "failed": len(self.failed_files),
            "total": len(dwg_files),
            "duration": duration,
            "failed_files": self.failed_files,
            "classification_results": self.classification_results,
            "folder_stats": folder_stats,  # 현재 실제 분류 현황 (크레딧 부족 시에도 포함)
            "unclassified_count": unclassified_count,
            "unmatched_files": unmatched_files,  # 미분류 파일 목록 추가
            "dry_run": dry_run,
            "credit_shortage_stop": self.credit_shortage_stop,  # 크레딧 부족으로 인한 중단 여부
        }

        # 모든 파일 처리 완료 시 처리 목록 초기화 (다음 실행을 위해)
        if not self.credit_shortage_stop and not dry_run and len(self.failed_files) == 0:
            # 전체 파일 수 = 이번 처리 + 이미 처리됨
            # 모두 성공하면 리셋
            self.logger.info("모든 파일 처리 완료 - 처리 목록 초기화")
            self._clear_processed_files()

        if unmatched_files:
            self.logger.info(
                f"DWG 분류 완료: 성공 {self.processed_count}개, 실패 {len(self.failed_files)}개, 미분류 {len(unmatched_files)}개"
            )
        else:
            self.logger.info(
                f"DWG 분류 완료: 성공 {self.processed_count}개, 실패 {len(self.failed_files)}개"
            )

        # 8. 세션 재개 파일 목록 저장/정리
        try:
            if self.folder_path:
                folder_base = Path(self.folder_path)
                pending_path = folder_base / "wf_pending_list.txt"
                if self.credit_shortage_stop and self.failed_files:
                    # 실패한 파일 목록 저장
                    names = [Path(f["file"]).name for f in self.failed_files if "file" in f]
                    if names:
                        tmp = pending_path.with_suffix(".tmp")
                        with open(tmp, "w", encoding="utf-8") as pf:
                            for n in names:
                                pf.write(n + "\n")
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

        return result

    def run_console_mode(
        self, folder_path: str, excel_files: Optional[List[str]] = None, dry_run: bool = False
    ):
        """콘솔 모드 실행"""
        self.console_mode = True
        self.logger.info("=== DWG Classifier 콘솔 모드 ===")

        if excel_files:
            self.set_excel_files(excel_files)

        result = self.classify_dwg_files(folder_path, dry_run)

        print("\n=== 처리 결과 ===")
        print(f"전체 파일: {result['total']}개")
        print(f"성공: {result['processed']}개")
        print(f"실패: {result['failed']}개")
        print(f"처리 시간: {result['duration']:.2f}초")

        if result["failed_files"]:
            print("\n=== 실패한 파일 ===")
            for failed in result["failed_files"]:
                print(f"- {failed['file']}: {failed['error']}")

        if dry_run:
            print("\n=== 분류 미리보기 ===")
            categories = {}
            for classification in result["classification_results"]:
                category = classification["category"]
                if category not in categories:
                    categories[category] = 0
                categories[category] += 1

            for category, count in categories.items():
                print(f"- {category}: {count}개")

        return result


def main():
    """메인 함수 - 콘솔 모드 테스트"""
    import argparse

    parser = argparse.ArgumentParser(description="DWG Classifier Automation")
    parser.add_argument("folder", help="DWG 파일이 있는 폴더 경로")
    parser.add_argument("--excel", nargs="+", help="분류 규칙 엑셀 파일 경로")
    parser.add_argument("--dry-run", action="store_true", help="실제 이동 없이 분류만 테스트")

    args = parser.parse_args()

    automation = DwgClassifierAutomation(console_mode=True)
    automation.run_console_mode(args.folder, args.excel, args.dry_run)


if __name__ == "__main__":
    main()
