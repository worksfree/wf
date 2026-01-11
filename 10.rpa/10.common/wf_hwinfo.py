import logging

# 모듈 레벨 로거 (부모에서 주입 가능). 기본은 NullHandler로 안전하게 무시
logger: logging.Logger = logging.getLogger("wf_hwinfo")
if not logger.handlers:
    logger.addHandler(logging.NullHandler())


def set_logger(external_logger: logging.Logger):
    global logger
    logger = external_logger


"""
WorksFree Hardware Information Module
하드웨어 정보 수집 모듈

기능:
1. CPU 정보 수집
2. 메인보드 정보 수집  
3. 하드웨어 고유 식별자 생성

Author: WorksFree
Version: 2.1
Changes:
- v2.1: cpuinfo 라이브러리 제거 (subprocess로 콘솔 창 발생), Windows Registry 사용
- v2.0: 싱글톤 패턴 적용
"""

import wmi
import sys
import argparse
import hashlib
import json
import subprocess
import winreg
from typing import Dict, Optional
from pathlib import Path


class HardwareInfo:
    """하드웨어 정보 수집 클래스 (싱글톤 패턴)"""

    _instance = None
    _lock = None  # Thread lock for singleton

    def __new__(cls):
        """싱글톤 패턴: 앱 전체에서 하드웨어 정보를 단 한 번만 수집"""
        if cls._instance is None:
            # 스레드 안전성을 위한 lock 초기화
            if cls._lock is None:
                import threading

                cls._lock = threading.Lock()

            with cls._lock:
                # Double-checked locking
                if cls._instance is None:
                    cls._instance = super(HardwareInfo, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """초기화는 최초 1회만 실행"""
        if self._initialized:
            return

        try:
            self.cpu_id = self._get_cpu_id()
        except Exception as e:
            logger.error(f"CPU 정보 수집 오류: {e}")
            self.cpu_id = "UNKNOWN_CPU"
        try:
            self.mainboard_id = self._get_mainboard_id()
        except Exception as e:
            logger.error(f"메인보드 정보 수집 오류: {e}")
            self.mainboard_id = "UNKNOWN_MB"

        try:
            self.storage_id = self._get_storage_id()
        except Exception as e:
            logger.error(f"하드디스크 정보 수집 오류: {e}")
            self.storage_id = "UNKNOWN_HD"

        try:
            components = [self.cpu_id, self.mainboard_id, self.storage_id]
            hardware_data = "|".join(components)
            self.fingerprint = hashlib.sha256(hardware_data.encode()).hexdigest()
        except Exception as e:
            logger.error(f"하드웨어 지문 생성 오류: {e}")
            self.fingerprint = "0" * 64

        self._initialized = True

    def _get_cpu_id(self) -> str:
        """CPU 정보를 Windows Registry에서 직접 읽기 (subprocess 없음)"""
        try:
            # Windows Registry에서 CPU 정보 읽기
            # HKEY_LOCAL_MACHINE\HARDWARE\DESCRIPTION\System\CentralProcessor\0
            reg_path = r"HARDWARE\DESCRIPTION\System\CentralProcessor\0"
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_path, 0, winreg.KEY_READ)

            try:
                cpu_name, _ = winreg.QueryValueEx(key, "ProcessorNameString")
                cpu_id, _ = winreg.QueryValueEx(key, "Identifier")
                winreg.CloseKey(key)

                # CPU 이름과 식별자 결합
                cpu_info = f"{cpu_name.strip()} [{cpu_id}]"
                logger.info(f"CPU Info: {cpu_info}")
                return cpu_info
            except Exception:
                # Identifier가 없으면 이름만 사용
                winreg.CloseKey(key)
                return cpu_name.strip() if cpu_name else "UNKNOWN_CPU"

        except Exception as e:
            logger.error(f"CPU 정보 읽기 오류: {e}")
            return "UNKNOWN_CPU"

    def _get_mainboard_id(self) -> str:
        try:
            c = wmi.WMI()
            for board in c.Win32_BaseBoard():
                if hasattr(board, "SerialNumber"):
                    return str(board.SerialNumber).strip()
            return "UNKNOWN_MB"
        except Exception:
            return "UNKNOWN_MB"

    def _get_storage_id(self) -> str:
        """C 드라이브의 볼륨 시리얼 번호를 가져옴 (안정적)
        - C 드라이브는 순서가 변경되지 않으며, OS 재설치 전까지 동일한 값 유지
        - Win32_DiskDrive의 SerialNumber는 디스크 순서 변경 시 불안정
        """
        try:
            c = wmi.WMI()
            # C: 드라이브의 볼륨 시리얼 번호 가져오기
            for logical_disk in c.Win32_LogicalDisk(DeviceID="C:"):
                if hasattr(logical_disk, "VolumeSerialNumber") and logical_disk.VolumeSerialNumber:
                    volume_serial = str(logical_disk.VolumeSerialNumber).strip()
                    logger.info(f"Storage ID (C: Volume Serial): {volume_serial}")
                    return volume_serial
            
            # 폴백: C 드라이브를 찾을 수 없는 경우
            logger.warning("C: 드라이브를 찾을 수 없음, PHYSICALDRIVE0 사용")
            for disk in c.Win32_DiskDrive(DeviceID=r"\\.\PHYSICALDRIVE0"):
                if hasattr(disk, "SerialNumber") and disk.SerialNumber:
                    return str(disk.SerialNumber).strip()
            
            return "UNKNOWN_HD"
        except Exception as e:
            logger.error(f"Storage ID 가져오기 실패: {e}")
            return "UNKNOWN_HD"

    def save_hardware_fingerprint(self, fingerprint: str) -> bool:
        """하드웨어 지문을 wf_rpa_config.json 파일의 user_fingerprint 키에 저장"""
        try:
            config_path = Path(__file__).parent / "wf_rpa_config.json"
            if config_path.exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
            else:
                config = {}

            config["user_fingerprint"] = fingerprint

            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"지문 저장 오류: {e}")
            return False


# ===== 메인 실행 =====
def _run_test():
    """안전한 테스트: 정보 출력만 수행"""
    hi = HardwareInfo()
    logger.info(f"[HWINFO] 메인보드 정보: {hi.mainboard_id}")
    logger.info(f"[HWINFO] CPU 정보: {hi.cpu_id}")
    logger.info(f"[HWINFO] 저장장치 정보: {hi.storage_id}")
    logger.info(f"[HWINFO] 하드웨어 지문: {hi.fingerprint}")
    return True


if __name__ == "__main__":
    try:
        from wf_log import get_app_logger

        set_logger(get_app_logger("wf_hwinfo", console_level=logging.INFO))
    except Exception:
        pass
    parser = argparse.ArgumentParser(description="WorksFree 하드웨어 정보 모듈")
    parser.add_argument("--test", action="store_true", help="하드웨어 정보 출력 테스트")
    args = parser.parse_args()

    if args.test:
        _run_test()
    else:
        # 기본 동작: 정보 출력
        _run_test()
