# -*- coding: utf-8 -*-
"""
K-Startup Web Automation Configuration Loader
통합 사용자 설정(settings.json)을 로드하고 기본값을 제공하는 모듈
BE/DC 패턴 통일
"""

import json
import logging
from pathlib import Path
import os
import datetime
import sys

# 글로벌 로거 import
common_path = Path(__file__).resolve().parents[2] / "10.common"
if str(common_path) not in sys.path:
    sys.path.insert(0, str(common_path))

import importlib

try:
    wflog = importlib.import_module("wf_log")
except Exception:
    # 폴백 로거 팩토리
    _fallback_logger = logging.getLogger(__name__)
    if not _fallback_logger.handlers:
        _handler = logging.StreamHandler()
        _handler.setLevel(logging.INFO)
        _fallback_logger.addHandler(_handler)
        _fallback_logger.setLevel(logging.INFO)

    class _DummyLog:
        def get_app_logger(self, name, console_level=logging.INFO):
            lg = logging.getLogger(name)
            if not lg.handlers:
                h = logging.StreamHandler()
                h.setLevel(console_level)
                lg.addHandler(h)
                lg.setLevel(console_level)
            return lg

    wflog = _DummyLog()


class Config:
    """설정 관리 클래스"""

    # 클래스 레벨 캐시
    _policy_cache = None
    _policy_cache_mtime = None

    def __init__(self):
        self.base_dir = str(Path(__file__).resolve().parent)
        self.user_home = Path.home()

        # 런모드 감지
        self.run_mode = self._detect_run_mode()

        app_root = Path(self.base_dir)
        local_config_dir = app_root / "config"
        
        # PyInstaller frozen 환경에서는 사용자 홈 경로 사용
        is_frozen = getattr(sys, 'frozen', False)
        
        if is_frozen:
            self.app_config_dir = self.user_home / ".wf_rpa" / "kstartup_web"
        else:
            self.app_config_dir = local_config_dir / "kstartup_web"
        
        # PyInstaller frozen 환경에서 번들 리소스 경로
        if is_frozen:
            self.bundle_dir = Path(getattr(sys, '_MEIPASS', self.base_dir))
        else:
            self.bundle_dir = app_root

        # Lazy loading 로거
        self._logger = None

        # 로그 레벨 상수
        self.SHOW_DEBUG = 10
        self.SHOW_INFO = 20
        self.SHOW_WARNING = 30
        self.SHOW_ERROR = 40

        # 통합 설정 파일
        self.settings_file = self.app_config_dir / "settings.json"
        
        # 설정 파일 초기화
        self._ensure_settings_file()

        # 경로 설정
        if self.run_mode in ("dev", "demo"):
            self.log_dir = Path(self.base_dir) / "logs"
            self.res_dir = Path(self.base_dir) / "res"
        else:
            base = Path.home() / ".wf_rpa" / "KStartup_Web"
            self.log_dir = base / "logs"
            self.res_dir = base / "res"

        # 디렉토리 생성
        self._ensure_directories()

        # 설정 로드
        self._load_config()

    def _detect_run_mode(self) -> str:
        """settings.json에서 실행 모드 감지"""
        settings_path = Path(__file__).resolve().parent / "config" / "kstartup_web" / "settings.json"
        try:
            with open(settings_path, "r", encoding="utf-8") as f:
                data = json.load(f) or {}
            cfg_mode = str(data.get("runtime_config", {}).get("run_mode", "") or "").strip().lower()
            return cfg_mode if cfg_mode in ("dev", "demo", "release") else "release"
        except Exception:
            return "release"

    @property
    def logger(self):
        """Lazy loading logger"""
        if self._logger is None:
            self._logger = wflog.get_app_logger("KStartup_Web", console_level=logging.DEBUG)
        return self._logger

    def _ensure_directories(self):
        """필요한 디렉토리 생성"""
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.res_dir.mkdir(parents=True, exist_ok=True)
        self.app_config_dir.mkdir(parents=True, exist_ok=True)
    
    def _ensure_settings_file(self):
        """통합 설정 파일 초기화"""
        if not self.settings_file.exists():
            # exe 환경: 번들된 설정 파일 복사
            import shutil
            is_frozen = getattr(sys, 'frozen', False)
            if is_frozen:
                bundled_config = self.bundle_dir / "config" / "kstartup_web" / "settings.json"
                if bundled_config.exists():
                    try:
                        self.app_config_dir.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(bundled_config, self.settings_file)
                        return
                    except Exception as e:
                        try:
                            self.logger.warning(f"[CONFIG] 번들 설정 복사 실패: {e}")
                        except Exception:
                            pass
            
            # 기본 설정 생성
            unified_settings = {
                "runtime_config": {
                    "run_mode": "release",
                    "full_version": "v1.0.0.0",
                    "admin_mode": False,
                    "ui_scale": 1.0,
                    "last_updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                },
                "ui_config": {
                    "last_excel_path": "",
                    "last_excel_dir": "",
                    "show_log": False,
                    "auto_scroll": True,
                    "topmost": True,
                    "window_width": 600,
                    "window_height": 200,
                    "window_geometry_override": ""
                },
                "logging_config": {
                    "log_level": "INFO",
                    "max_log_size_mb": 10,
                    "rotate_logs": True
                },
                "automation_config": {
                    "chrome_driver_path": "chromedriver",
                    "headless_mode": False,
                    "wait_timeout": 10,
                    "screenshot_enabled": True,
                    "save_cookies": True
                }
            }
            
            try:
                with open(self.settings_file, "w", encoding="utf-8") as f:
                    json.dump(unified_settings, f, ensure_ascii=False, indent=2)
            except Exception as e:
                try:
                    self.logger.error(f"[CONFIG] 설정 파일 생성 실패: {e}")
                except Exception:
                    pass

    def _load_config(self):
        """설정 파일 로드"""
        try:
            if self.settings_file.exists():
                with open(self.settings_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                # 각 섹션 로드
                self.runtime_config = data.get("runtime_config", {})
                self.ui_config = data.get("ui_config", {})
                self.logging_config = data.get("logging_config", {})
                self.automation_config = data.get("automation_config", {})
                
                # 편의 속성
                self.topmost = self.ui_config.get("topmost", True)
                self.window_geometry_override = self.ui_config.get("window_geometry_override", "")
                
            else:
                # 기본값 사용
                self.runtime_config = {}
                self.ui_config = {}
                self.logging_config = {}
                self.automation_config = {}
                self.topmost = True
                self.window_geometry_override = ""
                
        except Exception as e:
            try:
                self.logger.error(f"[CONFIG] 설정 로드 실패: {e}")
            except Exception:
                pass
            # 기본값
            self.runtime_config = {}
            self.ui_config = {}
            self.logging_config = {}
            self.automation_config = {}
            self.topmost = True
            self.window_geometry_override = ""

    def get(self, key: str, default=None):
        """설정값 조회 (모든 섹션 검색)"""
        for section in [self.ui_config, self.runtime_config, self.logging_config, self.automation_config]:
            if key in section:
                return section[key]
        return default

    def set(self, key: str, value):
        """설정값 저장 (ui_config에 저장)"""
        self.ui_config[key] = value

    def save_settings(self):
        """설정 파일 저장"""
        try:
            data = {
                "runtime_config": self.runtime_config,
                "ui_config": self.ui_config,
                "logging_config": self.logging_config,
                "automation_config": self.automation_config
            }
            
            # 업데이트 시간 갱신
            data["runtime_config"]["last_updated"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            with open(self.settings_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            try:
                self.logger.error(f"[CONFIG] 설정 저장 실패: {e}")
            except Exception:
                pass


# 싱글톤 패턴
_config_instance = None


def get_config():
    """설정 인스턴스 반환 (싱글톤)"""
    global _config_instance
    if _config_instance is None:
        _config_instance = Config()
    return _config_instance
