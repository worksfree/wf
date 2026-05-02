# -*- coding: utf-8 -*-
import os
import sys
import json
import logging
from pathlib import Path

class AppConfig:
    """Simple class to hold config values and allow dot notation access."""
    def __init__(self, **entries):
        self.__dict__.update(entries)
        for key, value in entries.items():
            if isinstance(value, dict):
                setattr(self, key, AppConfig(**value))

class Config:
    """설정 관리 클래스 (다른 앱과 일관성 유지)"""
    
    _policy_cache = None
    _policy_cache_mtime = None
    
    def __init__(self):
        self.base_dir = str(Path(__file__).resolve().parent)
        self.user_home = Path.home()
        
        # 런모드 판별
        self.run_mode = self._detect_run_mode()
        
        app_root = Path(self.base_dir)
        common_config_dir = app_root.parents[1] / "10.common" / "config"
        
        # dev: 소스트리, demo/release: 홈폴더
        if self.run_mode == "dev":
            self.app_config_dir = common_config_dir / "attribute_reset"
        else:
            self.app_config_dir = self.user_home / ".wf_rpa" / "attribute_reset"
        
        # 설정 파일
        self.settings_file = self.app_config_dir / "settings.json"
        
        # 설정 파일 초기화
        self._ensure_settings_file()
    
    def _detect_run_mode(self) -> str:
        """settings.json(runtime_config.run_mode)에서 실행 모드 감지"""
        app_root = Path(__file__).resolve().parent
        settings_path = app_root.parents[1] / "10.common" / "config" / "attribute_reset" / "settings.json"
        
        try:
            if settings_path.exists():
                with open(settings_path, "r", encoding="utf-8") as f:
                    data = json.load(f) or {}
                cfg_mode = str(data.get("runtime_config", {}).get("run_mode", "") or "").strip().lower()
                return cfg_mode if cfg_mode in ("dev", "demo", "release") else "release"
        except Exception:
            pass
        
        return "release"
    
    def _ensure_settings_file(self):
        """설정 파일이 없으면 기본값으로 생성"""
        if not self.settings_file.exists():
            self.app_config_dir.mkdir(parents=True, exist_ok=True)
            default_settings = {
                "solidworks": {
                    "program_path": "C:\\Program Files\\SOLIDWORKS Corp\\SOLIDWORKS\\SLDWORKS.exe",
                    "application_title": "SOLIDWORKS"
                },
                "runtime_config": {
                    "run_mode": "release",
                    "short_sleep": 0.2,
                    "mid_sleep": 1.0,
                    "long_sleep": 5.0,
                    "confidence": 0.9,
                    "full_version": "v0.7.0.0"
                },
                "ui_config": {
                    "topmost": True,
                    "last_selected_excel": "",
                    "window_geometry_override": "",
                    "window_width": 580,
                    "window_height": 320
                }
            }
            with open(self.settings_file, "w", encoding="utf-8") as f:
                json.dump(default_settings, f, indent=2, ensure_ascii=False)
    
    def load(self) -> AppConfig:
        """설정 파일을 로드하여 AppConfig 반환"""
        try:
            with open(self.settings_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return AppConfig(**data)
        except Exception:
            # 오류 시 기본값 사용
            default_settings = {
                "solidworks": {
                    "program_path": "C:\\Program Files\\SOLIDWORKS Corp\\SOLIDWORKS\\SLDWORKS.exe",
                    "application_title": "SOLIDWORKS"
                },
                "runtime_config": {
                    "run_mode": "release",
                    "short_sleep": 0.2,
                    "mid_sleep": 1.0,
                    "long_sleep": 5.0,
                    "confidence": 0.9,
                    "full_version": "v0.7.0.0"
                },
                "ui_config": {
                    "topmost": True,
                    "last_selected_excel": "",
                    "window_geometry_override": "",
                    "window_width": 580,
                    "window_height": 320
                }
            }
            return AppConfig(**default_settings)

# 싱글톤 인스턴스
_config_instance = None

def load_config():
    """하위 호환성을 위한 함수 (클래스 기반으로 변경)"""
    config = Config()
    return config.load()

def get_config_path():
    """하위 호환성을 위한 함수"""
    config = Config()
    return config.settings_file

def create_default_config():
    """하위 호환성을 위한 함수"""
    config = Config()
    config._ensure_settings_file()
    return config.load()

# Singleton config instance
_config_instance = None
_settings_file_path = None


def get_config(reload=False):
    """
    Returns a singleton configuration object, loading it from JSON.
    """
    global _config_instance, _settings_file_path
    if _config_instance is None or reload:
        _config_instance = load_config()
        _settings_file_path = get_config_path()
        # geometry 저장 메서드 동적 추가
        _config_instance.update_window_geometry_override = _update_window_geometry_override
        _config_instance.update_settings_window_geometry = _update_settings_window_geometry
        _config_instance.update_registration_window_geometry = _update_registration_window_geometry
    return _config_instance


def _update_window_geometry_override(geometry: str) -> bool:
    """창 geometry 오버라이드를 settings.json에 반영한다."""
    import datetime
    try:
        settings_file = get_config_path()
        data = {}
        if settings_file.exists():
            with open(settings_file, "r", encoding="utf-8") as f:
                data = json.load(f) or {}

        if "ui_config" not in data:
            data["ui_config"] = {}

        data["ui_config"]["window_geometry_override"] = geometry or ""

        # app_info 업데이트
        if "app_info" not in data:
            data["app_info"] = {}
        data["app_info"]["last_updated"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with open(settings_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return True
    except Exception:
        return False


def _update_settings_window_geometry(geometry: str) -> bool:
    """세팅창 geometry를 settings.json에 반영한다."""
    import datetime
    try:
        settings_file = get_config_path()
        data = {}
        if settings_file.exists():
            with open(settings_file, "r", encoding="utf-8") as f:
                data = json.load(f) or {}

        if "ui_config" not in data:
            data["ui_config"] = {}

        data["ui_config"]["settings_window_geometry"] = geometry or ""

        # app_info 업데이트
        if "app_info" not in data:
            data["app_info"] = {}
        data["app_info"]["last_updated"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with open(settings_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return True
    except Exception:
        return False


def _update_registration_window_geometry(geometry: str) -> bool:
    """등록창 geometry를 settings.json에 반영한다."""
    import datetime
    try:
        settings_file = get_config_path()
        data = {}
        if settings_file.exists():
            with open(settings_file, "r", encoding="utf-8") as f:
                data = json.load(f) or {}

        if "ui_config" not in data:
            data["ui_config"] = {}

        data["ui_config"]["registration_window_geometry"] = geometry or ""

        # app_info 업데이트
        if "app_info" not in data:
            data["app_info"] = {}
        data["app_info"]["last_updated"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with open(settings_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return True
    except Exception:
        return False


if __name__ == '__main__':
    # For testing the config
    config = get_config()
    print(f"App Name: attribute_reset") # App name is now implicit
    print(f"SolidWorks Path: {config.solidworks.program_path}")
    print(f"Run Mode: {config.runtime_config.run_mode}")
    print(f"Last Excel: {config.ui_config.last_selected_excel}")

