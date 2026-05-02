# -*- coding: utf-8 -*-
"""
QR Code Generator Configuration Loader
사용자 정의 설정을 로드하고, 기본값을 제공하는 모듈.
"""

import os
import json
import logging
from pathlib import Path
import sys
import datetime

common_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "10.common"))
if common_path not in sys.path:
    sys.path.insert(0, common_path)
import wf_log as wflog


class Config:
    """설정 관리 클래스 (dwg_classifier 패턴)"""

    _policy_cache = None
    _policy_cache_mtime = None

    def __init__(self):
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.user_home = Path.home()

        # 런모드 판별
        self.run_mode = self._detect_run_mode()

        # 통합 config 경로
        app_root = Path(self.base_dir)
        common_config_dir = app_root.parents[1] / "10.common" / "config"

        is_frozen = getattr(sys, 'frozen', False)

        if self.run_mode == "dev":
            self.app_config_dir = common_config_dir / "qrcode_generator"
        else:
            self.app_config_dir = self.user_home / ".wf_rpa" / "qrcode_generator"

        if is_frozen:
            self.bundle_dir = Path(getattr(sys, '_MEIPASS', self.base_dir))
        else:
            self.bundle_dir = app_root

        self._logger = None

        # 로그 레벨 상수
        self.SHOW_DEBUG = 10
        self.SHOW_INFO = 20
        self.SHOW_WARNING = 30
        self.SHOW_ERROR = 40

        # 설정 파일
        self.settings_file = self.app_config_dir / "settings.json"
        try:
            self.logger.info(f"[CONFIG] run_mode={self.run_mode}, settings_file={self.settings_file}")
        except Exception:
            pass

        self._ensure_settings_file()

        # 경로 설정
        if self.run_mode in ("dev", "demo"):
            self.log_dir = Path(self.base_dir) / "logs"
            self.res_dir = Path(self.base_dir) / "res"
        else:
            base = Path.home() / ".wf_rpa" / "qrcode_generator"
            self.log_dir = base / "logs"
            self.res_dir = base / "res"

        self._ensure_directories()
        self._load_config()

    def _detect_run_mode(self) -> str:
        """settings.json(runtime_config.run_mode)만 사용하여 실행 모드 결정"""
        app_root = Path(__file__).resolve().parent
        settings_path = app_root.parents[1] / "10.common" / "config" / "qrcode_generator" / "settings.json"
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
            self._logger = wflog.get_app_logger("qrcode_generator", console_level=logging.DEBUG)
        return self._logger

    def _ensure_directories(self):
        """필요한 디렉토리들을 생성"""
        os.makedirs(self.log_dir, exist_ok=True)
        os.makedirs(self.res_dir, exist_ok=True)
        self.app_config_dir.mkdir(parents=True, exist_ok=True)

    def _ensure_settings_file(self):
        """통합 설정 파일 초기화"""
        if not self.settings_file.exists():
            is_frozen = getattr(sys, 'frozen', False)
            if is_frozen:
                import shutil
                bundled_config = self.bundle_dir / "config" / "qrcode_generator" / "settings.json"
                if bundled_config.exists():
                    try:
                        self.app_config_dir.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(bundled_config, self.settings_file)
                        try:
                            self.logger.info(f"[CONFIG] 번들 설정 복사 완료: {bundled_config} → {self.settings_file}")
                        except Exception:
                            pass
                        return
                    except Exception as e:
                        try:
                            self.logger.warning(f"[CONFIG] 번들 설정 복사 실패: {e}")
                        except Exception:
                            pass

            unified_settings = {
                "runtime_config": {
                    "run_mode": "release",
                    "full_version": "v0.7.0.0",
                    "build_count": 0,
                    "ui_scale": 1.0,
                    "language": "ko",
                    "last_updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                },
                "ui_config": {
                    "last_url": "",
                    "topmost": True,
                    "window_width": 760,
                    "window_height": 200,
                    "window_geometry_override": ""
                },
                "logging_config": {
                    "log_level": "INFO",
                    "max_log_size_mb": 10,
                    "rotate_logs": True
                },
                "qrcode_settings": {
                    "output_folder": "",
                    "title_text": "홈페이지",
                    "subtitle_text": "Scan Me!",
                    "qr_version": 1,
                    "error_correction": "L",
                    "box_size": 25,
                    "border": 4,
                    "fill_color": "#000000",
                    "back_color": "#FFFFFF",
                    "title_color": "#333333",
                    "subtitle_color": "#666666",
                    "output_filename": "qrcode_output.png",
                    "font_size_title": 48,
                    "font_size_subtitle": 40
                }
            }

            try:
                self.app_config_dir.mkdir(parents=True, exist_ok=True)
                with open(self.settings_file, "w", encoding="utf-8") as f:
                    json.dump(unified_settings, f, ensure_ascii=False, indent=2)
                self.logger.info(f"통합 설정 파일 생성: {self.settings_file}")
            except Exception as e:
                self.logger.error(f"설정 파일 생성 실패: {e}")

    def _load_config(self):
        """설정 파일 로드"""
        config_data = {}
        try:
            if self.settings_file.exists():
                with open(self.settings_file, "r", encoding="utf-8") as f:
                    config_data = json.load(f)
                self.logger.info(f"사용자 설정 로드 완료: {self.settings_file}")
        except Exception as e:
            self.logger.error(f"사용자 설정 파일 로드 실패: {e}")

        policy_config = self._load_credit_policy()
        if policy_config:
            if "runtime_config" not in config_data:
                config_data["runtime_config"] = {}
            config_data["runtime_config"].update(policy_config)
            self.logger.info(f"크레딧 정책 설정 적용: {list(policy_config.keys())}")

        self._apply_config(config_data)

    def _load_credit_policy(self):
        """크레딧 정책 파일 로드 (policy.json)"""
        try:
            policy_file = self.app_config_dir / "policy.json"
            if not policy_file.exists():
                return {}

            current_mtime = policy_file.stat().st_mtime
            if Config._policy_cache is not None and Config._policy_cache_mtime == current_mtime:
                self.logger.debug(f"[캐시] 정책 파일 캐시 사용: {policy_file}")
                return Config._policy_cache

            with open(policy_file, "r", encoding="utf-8") as f:
                raw = json.load(f)
                policy_data = raw.get("policy", {}) if isinstance(raw, dict) else {}

                Config._policy_cache = policy_data
                Config._policy_cache_mtime = current_mtime

                if policy_data:
                    self.logger.debug(f"[새로 로드] 크레딧 정책 로드: {policy_data}")
                    return policy_data
        except Exception as e:
            self.logger.warning(f"크레딧 정책 파일 로드 실패: {e}")

        return {}

    def _apply_config(self, config_data):
        """설정 데이터 적용"""
        runtime_config = config_data.get("runtime_config", {})
        ui_config = config_data.get("ui_config", {}) or {}
        logging_config = config_data.get("logging_config", {})
        qrcode_settings = config_data.get("qrcode_settings", {})

        # ui_config 보존
        self.ui_config = ui_config
        self.window_geometry_override = ui_config.get("window_geometry_override", "")

        # Run Mode
        cfg_mode = str(runtime_config.get("run_mode", "")).strip().lower() if runtime_config else ""
        default_mode = getattr(self, "run_mode", "release")
        self.run_mode = cfg_mode if cfg_mode in ("dev", "release", "demo") else default_mode

        # Version
        self.version = runtime_config.get("full_version", "v0.7.0.0")
        self.ui_scale = float(runtime_config.get("ui_scale", 1.0))

        # UI config
        self.topmost = ui_config.get("topmost", True)
        # 창 크기 (settings.json 우선, 없으면 코드 기본값)
        self.window_width = ui_config.get("window_width", 760)  # QR 코드 생성기 기본 너비
        self.window_height = ui_config.get("window_height", 180)  # QR 코드 생성기 기본 높이

        # Logging
        self.log_level = logging_config.get("log_level", "INFO")
        self.max_log_size_mb = logging_config.get("max_log_size_mb", 10)
        self.rotate_logs = logging_config.get("rotate_logs", True)

        # QR Code 전용 설정
        self.output_folder = qrcode_settings.get("output_folder", "")
        self.title_text = qrcode_settings.get("title_text", "홈페이지")
        self.subtitle_text = qrcode_settings.get("subtitle_text", "Scan Me!")
        self.qr_version = qrcode_settings.get("qr_version", 1)
        self.error_correction = qrcode_settings.get("error_correction", "L")
        self.box_size = qrcode_settings.get("box_size", 25)
        self.border = qrcode_settings.get("border", 4)
        self.fill_color = qrcode_settings.get("fill_color", "#000000")
        self.back_color = qrcode_settings.get("back_color", "#FFFFFF")
        self.title_color = qrcode_settings.get("title_color", "#333333")
        self.subtitle_color = qrcode_settings.get("subtitle_color", "#666666")
        self.output_filename = qrcode_settings.get("output_filename", "qrcode_output.png")
        self.font_size_title = qrcode_settings.get("font_size_title", 48)
        self.font_size_subtitle = qrcode_settings.get("font_size_subtitle", 40)

    # ===== Settings mutation APIs =====
    def update_config(self, key_or_dict, value=None):
        """설정 업데이트 (in-memory)"""
        if isinstance(key_or_dict, dict):
            for k, v in key_or_dict.items():
                setattr(self, k, v)
        else:
            setattr(self, key_or_dict, value)

    def save_settings(self) -> bool:
        """현재 설정을 JSON으로 저장"""
        try:
            data = {}
            if self.settings_file.exists():
                try:
                    with open(self.settings_file, "r", encoding="utf-8") as f:
                        data = json.load(f) or {}
                except Exception:
                    data = {}

            # runtime_config
            rt = data.get("runtime_config", {})
            rt.update({
                "full_version": self.version,
                "ui_scale": self.ui_scale,
                "last_updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            })
            data["runtime_config"] = rt

            # ui_config
            ui = data.get("ui_config", {})
            ui.update({
                "topmost": self.topmost,
                "window_geometry_override": self.window_geometry_override,
            })
            data["ui_config"] = ui

            # logging_config
            lc = data.get("logging_config", {})
            lc.update({
                "log_level": self.log_level,
                "max_log_size_mb": self.max_log_size_mb,
                "rotate_logs": self.rotate_logs,
            })
            data["logging_config"] = lc

            # qrcode_settings
            data["qrcode_settings"] = {
                "output_folder": self.output_folder,
                "title_text": self.title_text,
                "subtitle_text": self.subtitle_text,
                "qr_version": self.qr_version,
                "error_correction": self.error_correction,
                "box_size": self.box_size,
                "border": self.border,
                "fill_color": self.fill_color,
                "back_color": self.back_color,
                "title_color": self.title_color,
                "subtitle_color": self.subtitle_color,
                "output_filename": self.output_filename,
                "font_size_title": self.font_size_title,
                "font_size_subtitle": self.font_size_subtitle,
            }

            self.settings_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.settings_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            self.logger.info(f"설정 저장 완료: {self.settings_file}")
            return True
        except Exception as e:
            try:
                self.logger.error(f"설정 저장 실패: {e}")
            except Exception:
                pass
            return False

    # ===== UI helpers =====
    def get_last_url(self) -> str:
        """마지막 입력 URL 반환"""
        try:
            if self.settings_file.exists():
                with open(self.settings_file, "r", encoding="utf-8") as f:
                    data = json.load(f) or {}
                return (data.get("ui_config", {}) or {}).get("last_url", "")
        except Exception as e:
            self.logger.debug(f"마지막 URL 로드 실패: {e}")
        return ""

    def update_last_url(self, url: str) -> bool:
        """마지막 입력 URL 저장"""
        try:
            data = {}
            if self.settings_file.exists():
                with open(self.settings_file, "r", encoding="utf-8") as f:
                    data = json.load(f) or {}

            if "ui_config" not in data:
                data["ui_config"] = {}
            data["ui_config"]["last_url"] = url or ""

            if "runtime_config" not in data:
                data["runtime_config"] = {}
            data["runtime_config"]["last_updated"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            with open(self.settings_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            self.logger.error(f"URL 저장 실패: {e}")
            return False

    def update_window_geometry_override(self, geometry: str | None) -> bool:
        """창 geometry 오버라이드를 settings.json에 반영"""
        try:
            data = {}
            if self.settings_file.exists():
                with open(self.settings_file, "r", encoding="utf-8") as f:
                    data = json.load(f) or {}
            if "ui_config" not in data:
                data["ui_config"] = {}
            data["ui_config"]["window_geometry_override"] = geometry or ""
            with open(self.settings_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            self.window_geometry_override = geometry or ""
            return True
        except Exception as e:
            try:
                self.logger.error(f"geometry 저장 실패: {e}")
            except Exception:
                pass
            return False

    def update_settings_window_geometry(self, geometry: str | None) -> bool:
        """세팅창 geometry를 settings.json에 반영"""
        try:
            data = {}
            if self.settings_file.exists():
                with open(self.settings_file, "r", encoding="utf-8") as f:
                    data = json.load(f) or {}
            if "ui_config" not in data:
                data["ui_config"] = {}
            data["ui_config"]["settings_window_geometry"] = geometry or ""
            with open(self.settings_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            try:
                self.logger.error(f"settings_window geometry 저장 실패: {e}")
            except Exception:
                pass
            return False

    def update_registration_window_geometry(self, geometry: str | None) -> bool:
        """등록창 geometry를 settings.json에 반영"""
        try:
            data = {}
            if self.settings_file.exists():
                with open(self.settings_file, "r", encoding="utf-8") as f:
                    data = json.load(f) or {}
            if "ui_config" not in data:
                data["ui_config"] = {}
            data["ui_config"]["registration_window_geometry"] = geometry or ""
            with open(self.settings_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            try:
                self.logger.error(f"registration_window geometry 저장 실패: {e}")
            except Exception:
                pass
            return False

    # ===== 모드 헬퍼 =====
    def is_demo(self) -> bool:
        try:
            return getattr(self, "run_mode", "release") == "demo"
        except Exception:
            return False

    def is_dev(self) -> bool:
        try:
            return getattr(self, "run_mode", "release") == "dev"
        except Exception:
            return False

    def is_release(self) -> bool:
        try:
            return getattr(self, "run_mode", "release") == "release"
        except Exception:
            return True


# 전역 설정 인스턴스
_config = None


def get_config(reload=False):
    """설정 인스턴스 반환 (싱글톤 패턴)"""
    global _config
    if _config is None or reload:
        _config = Config()
    return _config
