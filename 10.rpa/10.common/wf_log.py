# -*- coding: utf-8 -*-
"""
글로벌 싱글톤 로거 패턴
각 앱별로 독립적인 로그 파일 관리, 30일 경과 로그 자동 삭제
"""
import logging
import os
import time
import threading
from datetime import datetime, timedelta
from pathlib import Path


def _detect_run_mode():
    """Detect run mode: dev/demo stay in cwd; release goes to user home."""
    env_mode = (os.environ.get("WF_RPA_MODE") or "").strip().lower()
    if env_mode:
        return env_mode
    if os.environ.get("WF_RPA_DEV") == "1":
        return "dev"
    import sys

    if sys.argv[0].endswith(".py"):
        return "dev"
    return "release"


class GlobalLoggerManager:
    """글로벌 싱글톤 로거 매니저"""

    _instance = None
    _lock = threading.Lock()
    _loggers = {}

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def get_logger(self, app_name, console_level=logging.INFO):
        """
        앱별 로거 반환 (싱글톤)
        Args:
            app_name: 앱 이름 (예: 'bom2excel')
            console_level: 콘솔 출력 레벨 (기본: INFO, 배포본은 INFO로 설정)
        Returns:
            logging.Logger: 설정된 로거
        """
        if app_name not in self._loggers:
            with self._lock:
                if app_name not in self._loggers:
                    self._loggers[app_name] = self._create_logger(app_name, console_level)
        return self._loggers[app_name]

    def _create_logger(self, app_name, console_level):
        """실제 로거 생성"""
        # 로거 생성
        logger = logging.getLogger(f"wf_rpa.{app_name}")
        logger.setLevel(logging.DEBUG)  # 로거 자체는 모든 레벨 허용
        logger.propagate = False  # 부모 로거로 전파 방지 (중복 출력 방지)

        # 기존 핸들러 제거 (중복 방지)
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)

        # 콘솔은 간결하게, 파일은 자세하게 (모듈/라인/로거명 포함)
        console_formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - [%(name)s] - %(message)s"
        )
        file_formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - [%(name)s] %(module)s:%(lineno)d - %(message)s"
        )

        # 1. 콘솔 핸들러 (레벨 설정 가능)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(console_level)
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

        # 2. 파일 핸들러 (항상 DEBUG, 전량 출력)
        mode = _detect_run_mode()
        if mode in ("dev", "demo"):
            log_dir = Path.cwd() / "logs"
        else:
            log_dir = Path.home() / ".wf_rpa" / app_name / "logs"

        log_dir.mkdir(parents=True, exist_ok=True)

        log_file = log_dir / f"{time.strftime('%Y%m%d')}.txt"
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)  # 파일은 전량 출력
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

        # 3. 30일 경과 로그 파일 정리
        self._clean_old_logs(log_dir, days=30)

        # 4. 시작 배너 + 하드웨어 지문 로그 (안전하게 시도)
        self._log_startup_banner(logger, app_name)

        return logger

    def _log_startup_banner(self, logger: logging.Logger, app_name: str):
        """앱 시작 시 간단한 배너와 하드웨어 지문을 로그로 남김 (예외는 무시하지 않고 기록)"""
        try:
            logger.info("===== WorksFree Logger Initialized =====")
            logger.info(f"App: {app_name}")
            # 하드웨어 정보 시도
            try:
                import wf_hwinfo  # 10.common 경로가 sys.path에 있어야 함

                hw = wf_hwinfo.HardwareInfo()
                logger.info(
                    f"HW Fingerprint: {hw.fingerprint} | CPU: {hw.cpu_id} | MainBoard: {hw.mainboard_id}"
                )
            except Exception as hw_err:
                logger.warning(f"HW fingerprint logging failed: {hw_err}", exc_info=True)
        except Exception as e:
            # 배너 로깅 자체에서 문제가 생겨도, 로거 동작은 계속되어야 함
            try:
                logger.warning(f"Startup banner logging failed: {e}", exc_info=True)
            except Exception:
                # 마지막 방어: 아무 것도 못 쓰는 상황이면 조용히 패스
                pass

    def _clean_old_logs(self, log_dir, days=30):
        """30일 경과한 로그 파일 삭제"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)

            for log_file in log_dir.glob("*.txt"):
                try:
                    # 파일명에서 날짜 추출 (YYYYMMDD.txt)
                    file_stem = log_file.stem
                    if len(file_stem) == 8 and file_stem.isdigit():
                        file_date = datetime.strptime(file_stem, "%Y%m%d")
                        if file_date < cutoff_date:
                            log_file.unlink()
                            print(f"[로그 정리] 오래된 로그 파일 삭제: {log_file}")
                    else:
                        # 날짜 형식이 아닌 경우 파일 수정 시간으로 판단
                        file_mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
                        if file_mtime < cutoff_date:
                            log_file.unlink()
                            print(f"[로그 정리] 오래된 로그 파일 삭제: {log_file}")
                except (ValueError, OSError) as e:
                    print(f"[로그 정리] 파일 처리 중 오류: {log_file}, {e}")
                    continue
        except Exception as e:
            print(f"[로그 정리] 로그 파일 정리 중 오류: {e}")


# 전역 매니저 인스턴스
_logger_manager = GlobalLoggerManager()


def get_app_logger(app_name, console_level=logging.INFO):
    """
    앱별 글로벌 싱글톤 로거 반환
    Args:
        app_name: 앱 이름
        console_level: 콘솔 출력 레벨 (기본: INFO, 파일은 항상 DEBUG로 전량 기록)
    Returns:
        logging.Logger: 설정된 로거
    """
    return _logger_manager.get_logger(app_name, console_level)


# 호환성을 위한 기존 함수들
def set_logger(filepath=None, level=logging.DEBUG, file_extension="txt"):
    """기존 호환성을 위한 함수 (deprecated)"""
    # 기본 앱 이름으로 처리
    logger = get_app_logger("default", console_level=level)
    return logger, None


def get_logger(name="default", filepath=None, level=logging.INFO, file_extension="txt"):
    """기존 호환성을 위한 함수 (deprecated)"""
    return get_app_logger(name, console_level=level)


# 테스트 코드
if __name__ == "__main__":
    # 다양한 레벨로 테스트
    logger1 = get_app_logger("test_app", console_level=logging.INFO)
    logger1.debug("이 DEBUG 로그는 파일에만 저장됨")
    logger1.info("이 INFO 로그는 콘솔과 파일 모두 출력")
    logger1.warning("이 WARNING 로그는 콘솔과 파일 모두 출력")

    # 같은 앱 이름으로 다시 요청 (싱글톤 확인)
    logger2 = get_app_logger("test_app", console_level=logging.INFO)
    logger2.error("같은 로거 인스턴스 확인용 로그")

    print(f"logger1 == logger2: {logger1 is logger2}")  # True여야 함
    print("글로벌 싱글톤 로거 테스트 완료!")
