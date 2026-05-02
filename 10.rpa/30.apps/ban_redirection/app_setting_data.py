# -*- coding: utf-8 -*-
"""
Ban Redirection Configuration Loader
- Dev:  10.common/config/ban_redirection/
- Prod: ~/.wf_rpa/ban_redirection/
"""

import json
import logging
import sys
import importlib
from pathlib import Path

common_path = Path(__file__).resolve().parents[2] / "10.common"
if str(common_path) not in sys.path:
    sys.path.insert(0, str(common_path))

try:
    wflog = importlib.import_module("wf_log")
except Exception:
    wflog = None

APP_NAME = "ban_redirection"
_DEFAULT_PRIMARY_DNS = "8.8.8.8"
_DEFAULT_SECONDARY_DNS = "8.8.4.4"


class Config:
    def __init__(self):
        self.base_dir = Path(__file__).resolve().parent
        self.user_home = Path.home()

        self.run_mode = self._detect_run_mode()

        common_config_dir = self.base_dir.parents[1] / "10.common" / "config"
        if self.run_mode == "dev":
            self.app_config_dir = common_config_dir / APP_NAME
        else:
            self.app_config_dir = self.user_home / ".wf_rpa" / APP_NAME
        self.app_config_dir.mkdir(parents=True, exist_ok=True)

        self.settings_file = self.app_config_dir / "settings.json"
        self.credit_policy_file = self.app_config_dir / "policy.json"
        self.credit_history_file = self.app_config_dir / "credit_history.json"

        if wflog:
            self._logger = wflog.get_app_logger(APP_NAME)
        else:
            lg = logging.getLogger(APP_NAME)
            if not lg.handlers:
                h = logging.StreamHandler()
                lg.addHandler(h)
                lg.setLevel(logging.INFO)
            self._logger = lg

        if self.run_mode in ("dev", "demo"):
            self.log_dir = self.base_dir / "logs"
            self.res_dir = self.base_dir / "res"
        else:
            base = self.user_home / ".wf_rpa" / APP_NAME
            self.log_dir = base / "logs"
            self.res_dir = base / "res"
        self.log_dir.mkdir(parents=True, exist_ok=True)

        self._ensure_settings_file()
        self._load_settings()

    def _detect_run_mode(self) -> str:
        app_root = Path(__file__).resolve().parent
        settings_path = (
            app_root.parents[1] / "10.common" / "config" / APP_NAME / "settings.json"
        )
        try:
            with open(settings_path, "r", encoding="utf-8") as f:
                data = json.load(f) or {}
            cfg_mode = str(
                data.get("runtime_config", {}).get("run_mode", "") or ""
            ).strip().lower()
            return cfg_mode if cfg_mode in ("dev", "demo", "release") else "release"
        except Exception:
            return "release"

    @property
    def logger(self):
        return self._logger

    def _load_json(self, path: Path, default=None):
        try:
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            self.logger.warning(f"Failed to read {path}: {e}")
        return default if default is not None else {}

    def _save_json(self, path: Path, data) -> bool:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            self.logger.error(f"Failed to write {path}: {e}")
            return False

    def _ensure_settings_file(self):
        if self.settings_file.exists():
            return
        import shutil, datetime
        is_frozen = getattr(sys, "frozen", False)
        if is_frozen:
            bundled = Path(self.base_dir) / "config" / APP_NAME / "settings.json"
            if bundled.exists():
                try:
                    shutil.copy2(bundled, self.settings_file)
                    return
                except Exception:
                    pass
        defaults = {
            "runtime_config": {
                "run_mode": "release",
                "full_version": "v0.7.0.0",
                "last_updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            },
            "app_config": {
                "primary_dns": _DEFAULT_PRIMARY_DNS,
                "secondary_dns": _DEFAULT_SECONDARY_DNS,
            },
            "ui_config": {
                "window_height": 280,
                "topmost": True,
                "window_geometry_override": "",
            },
        }
        self._save_json(self.settings_file, defaults)

    def _load_settings(self):
        data = self._load_json(self.settings_file, default={})
        if not isinstance(data, dict):
            data = {}

        runtime = data.get("runtime_config", {}) or {}
        app_cfg = data.get("app_config", {}) or {}
        ui_cfg = data.get("ui_config", {}) or {}

        cfg_mode = str(runtime.get("run_mode", "") or "").strip().lower()
        self.run_mode = cfg_mode if cfg_mode in ("dev", "demo", "release") else self.run_mode

        self.full_version = str(runtime.get("full_version", "v0.7.0.0") or "v0.7.0.0")

        self.primary_dns = str(app_cfg.get("primary_dns", _DEFAULT_PRIMARY_DNS) or _DEFAULT_PRIMARY_DNS)
        self.secondary_dns = str(app_cfg.get("secondary_dns", _DEFAULT_SECONDARY_DNS) or _DEFAULT_SECONDARY_DNS)

        self.window_height = int(ui_cfg.get("window_height", 280))
        self.topmost = bool(ui_cfg.get("topmost", True))
        self.window_geometry_override = str(ui_cfg.get("window_geometry_override", "") or "")

        self.settings = data
        self.ui_config = type("UIConfig", (), {
            "window_height": self.window_height,
            "topmost": self.topmost,
            "window_geometry_override": self.window_geometry_override,
        })()
        self.runtime_config = type("RuntimeConfig", (), {
            "run_mode": self.run_mode,
            "full_version": self.full_version,
        })()

    def save_dns_settings(self, primary: str, secondary: str) -> bool:
        """Persist DNS addresses to settings.json."""
        try:
            data = self._load_json(self.settings_file, default={})
            data.setdefault("app_config", {})["primary_dns"] = primary
            data["app_config"]["secondary_dns"] = secondary
            ok = self._save_json(self.settings_file, data)
            if ok:
                self.primary_dns = primary
                self.secondary_dns = secondary
            return ok
        except Exception as e:
            self.logger.warning(f"DNS 설정 저장 실패: {e}")
            return False

    def update_window_geometry_override(self, geometry) -> bool:
        try:
            data = self._load_json(self.settings_file, default={})
            data.setdefault("ui_config", {})["window_geometry_override"] = geometry or ""
            ok = self._save_json(self.settings_file, data)
            if ok:
                self.window_geometry_override = geometry or ""
            return ok
        except Exception as e:
            self.logger.warning(f"geometry 저장 실패: {e}")
            return False

    def load_credit_policy(self) -> dict:
        return self._load_json(self.credit_policy_file, default={})

    def load_credit_history(self) -> dict:
        return self._load_json(self.credit_history_file, default={})


_singleton = None


def get_config(reload=False) -> Config:
    global _singleton
    if _singleton is None or reload:
        _singleton = Config()
    return _singleton


def get_config_path() -> Path:
    return get_config().settings_file
