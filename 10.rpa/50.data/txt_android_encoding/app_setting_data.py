# -*- coding: utf-8 -*-
"""
Text Encoding Fixer App Settings
"""

import os
import json
from pathlib import Path

# --- 이 앱의 고유 정보 ---
APP_NAME = "txt_android_encoding"
APP_DISPLAY_NAME = "텍스트 인코딩 변환기"
FULL_VERSION = "v1.0.0.0"

class AppConfig:
    def __init__(self, settings_file_path):
        self.settings_file = Path(settings_file_path)
        self.settings = {
            "last_folder": str(Path.home()),
            "ui_config": {},
        }
        self.load_settings()

    def load_settings(self):
        if self.settings_file.exists():
            try:
                with open(self.settings_file, "r", encoding="utf-8") as f:
                    self.settings.update(json.load(f))
            except (json.JSONDecodeError, TypeError):
                self._save_defaults() # 파일이 손상되었으면 기본값으로 덮어씀
        else:
            self._save_defaults()

    def _save_defaults(self):
        """기본 설정 파일 생성"""
        try:
            self.settings_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.settings_file, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=2, ensure_ascii=False)
        except Exception:
            pass # 파일 저장 실패는 치명적이지 않음

    def save_settings(self):
        """현재 설정을 파일에 저장"""
        self._save_defaults()

    def get(self, key, default=None):
        return self.settings.get(key, default)

    def set(self, key, value):
        self.settings[key] = value

# --- 설정 파일 경로 결정 ---
def get_settings_path():
    # 개발 모드: 앱 폴더 내 config
    if os.path.basename(sys.argv[0]).endswith(".py"):
        return Path(__file__).parent / "config" / "settings.json"
    # 릴리스 모드: 사용자 홈 디렉토리
    else:
        return Path.home() / ".wf_rpa" / APP_NAME / "settings.json"

_config_instance = None

def get_config(reload=False):
    """설정 인스턴스를 반환 (싱글턴)"""
    global _config_instance
    if _config_instance is None or reload:
        _config_instance = AppConfig(get_settings_path())
    return _config_instance

if __name__ == "__main__":
    import sys
    # 테스트
    config = get_config()
    print(f"설정 파일 위치: {config.settings_file}")
    print(f"마지막 폴더: {config.get('last_folder')}")
    config.set("last_folder", "C:/test")
    config.save_settings()
    print(f"변경된 마지막 폴더: {config.get('last_folder')}")
