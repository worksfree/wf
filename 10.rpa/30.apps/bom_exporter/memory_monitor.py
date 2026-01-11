# -*- coding: utf-8 -*-
"""
메모리 모니터링 유틸리티
SolidWorks 메모리 문제 해결을 위한 시스템 메모리 감시
"""

import psutil
import logging


class MemoryMonitor:
    """시스템 메모리 모니터"""

    def __init__(self, threshold_percent=20, logger=None):
        """
        Args:
            threshold_percent: 가용 메모리 임계치 (%)
                               이 값 이하로 떨어지면 경고
            logger: 로거 인스턴스 (없으면 기본 로거 사용)
        """
        self.threshold_percent = threshold_percent
        self.logger = logger or logging.getLogger(__name__)

    def get_memory_info(self):
        """
        현재 시스템 메모리 정보 반환

        Returns:
            dict: {
                'total': 전체 메모리 (GB),
                'available': 가용 메모리 (GB),
                'used': 사용중 메모리 (GB),
                'percent': 사용률 (%),
                'available_percent': 가용률 (%)
            }
        """
        mem = psutil.virtual_memory()
        return {
            "total": round(mem.total / (1024**3), 2),
            "available": round(mem.available / (1024**3), 2),
            "used": round(mem.used / (1024**3), 2),
            "percent": mem.percent,
            "available_percent": round(100 - mem.percent, 2),
        }

    def is_memory_low(self):
        """
        메모리가 부족한지 체크

        Returns:
            bool: True if 가용 메모리 < threshold_percent
        """
        info = self.get_memory_info()
        is_low = info["available_percent"] < self.threshold_percent

        if is_low:
            self.logger.warning(
                f"⚠️ 메모리 부족 감지! "
                f'가용: {info["available"]}GB ({info["available_percent"]}%), '
                f"임계치: {self.threshold_percent}%"
            )
        else:
            self.logger.debug(
                f"메모리 상태 정상: " f'가용 {info["available"]}GB ({info["available_percent"]}%)'
            )

        return is_low

    def get_process_memory(self, process_name="SLDWORKS.exe"):
        """
        특정 프로세스의 메모리 사용량 조회

        Args:
            process_name: 프로세스 이름 (기본: SLDWORKS.exe)

        Returns:
            float: 메모리 사용량 (GB), 프로세스 없으면 0.0
        """
        try:
            for proc in psutil.process_iter(["name", "memory_info"]):
                if proc.info["name"] == process_name:
                    mem_bytes = proc.info["memory_info"].rss
                    mem_gb = round(mem_bytes / (1024**3), 2)
                    return mem_gb
        except Exception as e:
            self.logger.error(f"프로세스 메모리 조회 실패: {e}")

        return 0.0

    def log_memory_status(self):
        """메모리 상태를 로그에 기록"""
        info = self.get_memory_info()
        sw_mem = self.get_process_memory("SLDWORKS.exe")

        self.logger.info(
            f"📊 메모리 상태: "
            f'전체 {info["total"]}GB | '
            f'사용중 {info["used"]}GB ({info["percent"]}%) | '
            f'가용 {info["available"]}GB ({info["available_percent"]}%) | '
            f"SolidWorks {sw_mem}GB"
        )

        return info
