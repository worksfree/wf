# -*- coding: utf-8 -*-
"""
Conversion Verifier Configuration Loader
- Unified loader for settings.json, credit_policy.json, credit_history.json
- Dev:   50.data/conversion_verifier/config/conversion_verifier/
- Prod:  ~/.wf_rpa/conversion_verifier/
- Backward compatibility: migrate legacy files from ~/.wf_rpa root

Key changes:
- Do NOT store transient app state (credits/admin/license email) in settings.json.
- Persist transient state into app_state.json to avoid clobbering canonical settings schema.
- Expose canonical sections: app_config, ui_config, logging_config.
"""

import json
import logging
from pathlib import Path
import os
import sys
import importlib

# logger (lazy importable wf_log)
common_path = Path(__file__).resolve().parents[2] / "10.common"
if str(common_path) not in sys.path:
    sys.path.insert(0, str(common_path))
try:
    wflog = importlib.import_module("wf_log")
except Exception:
    wflog = None

APP_NAME = "conversion_verifier"


class Config:
    """Unified app settings/credit loader"""

    def __init__(self):
        self.base_dir = Path(__file__).resolve().parent
        self.user_home = Path.home()

        # 런모드 판별: settings.json(app_config.run_mode)만 사용
        self.run_mode = self._detect_run_mode()

        # 통합 config 경로: 10.common/config/ (개발), ~/.wf_rpa/ (배포)
        common_config_dir = self.base_dir.parents[1] / "10.common" / "config"

        # PyInstaller frozen 환경(exe)에서는 항상 사용자 홈 경로 사용 (번들 파일은 읽기 전용)
        import sys
        is_frozen = getattr(sys, 'frozen', False)

        if self.run_mode == "dev":
            self.app_config_dir = common_config_dir / APP_NAME
        else:
            self.app_config_dir = self.user_home / ".wf_rpa" / APP_NAME
        self.app_config_dir.mkdir(parents=True, exist_ok=True)

        # Files
        self.settings_file = (
            self.app_config_dir / "settings.json"
        )  # canonical settings (read/write structured)
        try:
            self.logger.info(f"[CONFIG] run_mode={self.run_mode}, settings_file={self.settings_file}")
        except Exception:
            pass
        self.state_file = (
            self.app_config_dir / "app_state.json"
        )  # transient app state (credits, admin, license)
        self.credit_policy_file = self.app_config_dir / "credit_policy.json"
        self.credit_history_file = self.app_config_dir / "credit_history.json"
        
        # 설정 파일 초기화 (처음 설치 시 기본 구조 생성)
        self._ensure_settings_file()

        # Legacy files (root of ~/.wf_rpa)
        self.legacy_root = self.user_home / ".wf_rpa"
        self.legacy_settings = self.legacy_root / ".conversion_verifier_settings.json"
        self.legacy_credits = self.legacy_root / ".conversion_verifier_credits.json"

        # Logger
        if wflog:
            self._logger = wflog.get_app_logger(APP_NAME, console_level=logging.DEBUG)
        else:
            lg = logging.getLogger(APP_NAME)
            if not lg.handlers:
                h = logging.StreamHandler()
                h.setLevel(logging.INFO)
                lg.addHandler(h)
                lg.setLevel(logging.INFO)
            self._logger = lg

        # Canonical app settings (sections)
        self.settings: dict = {}
        self.app_config: dict = {}
        self.ui_config: dict = {}
        self.logging_config: dict = {}

        # 앱 상태 초기화 (transient)
        self.credits = 10
        self.license_email = ""
        self.is_admin_mode = False
        self.ui_scale = 1.0

        # 비밀번호 설정
        self.admin_password = "admin123"  # 관리자 모드 진입
        self.license_password = "license2024"  # 영구 라이선스 등록

        # 로그/리소스 경로: dev/demo는 작업 디렉터리, release는 사용자 홈
        if self.run_mode in ("dev", "demo"):
            self.log_dir = self.base_dir / "logs"
            self.res_dir = self.base_dir / "res"
        else:
            base = self.user_home / ".wf_rpa" / APP_NAME
            self.log_dir = base / "logs"
            self.res_dir = base / "res"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.res_dir.mkdir(parents=True, exist_ok=True)

        # Load canonical settings + transient app state
        self._load_settings()
        self.load_app_data()

    def _detect_run_mode(self) -> str:
        """settings.json의 runtime_config.run_mode만 사용하여 실행 모드 결정"""
        # 통합 config 경로 사용: 10.common/config/conversion_verifier/settings.json
        app_root = Path(__file__).resolve().parent
        settings_path = app_root.parents[1] / "10.common" / "config" / APP_NAME / "settings.json"
        try:
            with open(settings_path, "r", encoding="utf-8") as f:
                data = json.load(f) or {}
            cfg_mode = str(data.get("runtime_config", {}).get("run_mode", "") or "").strip().lower()
            return cfg_mode if cfg_mode in ("dev", "demo", "release") else "release"
        except Exception:
            return "release"

    # --------------- utils ---------------
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
        """통합 설정 파일 초기화 (처음 설치 시 기본 구조 생성)
        
        [중요] exe 실행 시 번들된 설정을 사용자 홈으로 복사하여 초기값 활용
        - 소스 실행: 소스 트리 config 직접 사용 (dev/demo)
        - exe 실행: 번들 config → 사용자 홈으로 복사 (읽기 전용 → 쓰기 가능)
        
        settings.json 구조:
        {
            "app_info": {"last_updated": "2025-11-25 05:17:31"},
            "app_config": {...},
            "ui_config": {"last_selected_folder": ""},
            "logging_config": {...}
        }
        """
        if not self.settings_file.exists():
            # exe 환경: 번들된 설정 파일이 있으면 복사
            import sys
            import shutil
            is_frozen = getattr(sys, 'frozen', False)
            if is_frozen:
                bundled_config = Path(self.base_dir) / "config" / APP_NAME / "settings.json"
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
            import datetime
            # 통합 설정 파일 생성 (기본값)
            unified_settings = {
                "runtime_config": {
                    "run_mode": "release",
                    "ui_scale": 1.0,
                    "last_updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                },
                "ui_config": {
                    "last_selected_folder": "",
                    "window_geometry_override": "",
                    "window_width": 580,
                    "window_height": 200
                },
                "logging_config": {
                    "log_level": "INFO",
                    "max_log_size_mb": 10,
                    "rotate_logs": True
                }
            }
            
            # 새 통합 설정 파일 저장
            try:
                with open(self.settings_file, "w", encoding="utf-8") as f:
                    json.dump(unified_settings, f, ensure_ascii=False, indent=2)
                self.logger.info(f"✅ 통합 설정 파일 생성: {self.settings_file}")
            except Exception as e:
                self.logger.error(f"⚠️ 설정 파일 생성 실패: {e}")

    def _migrate_legacy_if_needed(self):
        """Migrate legacy root files into app folder if present."""
        try:
            migrated = False
            if self.legacy_settings.exists() and not self.settings_file.exists():
                data = self._load_json(self.legacy_settings, {})
                self._save_json(self.settings_file, data)
                migrated = True
            if self.legacy_credits.exists() and not self.credit_history_file.exists():
                data = self._load_json(self.legacy_credits, {})
                self._save_json(self.credit_history_file, data)
                migrated = True
            if migrated:
                self.logger.info("Migrated legacy conversion_verifier files to app folder.")
        except Exception as e:
            self.logger.warning(f"Legacy migration failed: {e}")

    # --------------- settings API ---------------
    def _load_settings(self):
        """Load canonical settings.json into structured sections with defaults."""
        data = self._load_json(self.settings_file, default={})
        if not isinstance(data, dict):
            data = {}
        self.settings = data
        self.app_config = data.get("runtime_config", {}) or {}
        self.ui_config = data.get("ui_config", {}) or {}
        self.logging_config = data.get("logging_config", {}) or {}
        # Commonly used convenience props
        try:
            self.ui_scale = float(self.app_config.get("ui_scale", 1.0))
        except Exception:
            self.ui_scale = 1.0

        # 실행 모드 재결정: settings.json 값 우선, 없으면 초기 런모드 유지
        cfg_mode = str(self.app_config.get("run_mode", "") or "").strip().lower()
        default_mode = getattr(self, "run_mode", "release")
        self.run_mode = cfg_mode if cfg_mode in ("dev", "demo", "release") else default_mode

        # 창 크기/geometry 오버라이드 캐시
        self.window_geometry_override = self.ui_config.get("window_geometry_override", "")

        # 창 크기 (settings.json 우선, 없으면 코드 기본값)
        self.window_width = self.ui_config.get("window_width", 580)  # conversion_verifier 기본 너비
        self.window_height = self.ui_config.get("window_height", 200)  # conversion_verifier 기본 높이

    def get_app_config(self) -> dict:
        return dict(self.app_config)

    def get_ui_config(self) -> dict:
        return dict(self.ui_config)

    def get_logging_config(self) -> dict:
        return dict(self.logging_config)

    def update_ui_config(self, updates: dict) -> bool:
        if not isinstance(updates, dict):
            return False
        data = self._load_json(self.settings_file, default={})
        if not isinstance(data, dict):
            data = {}
        ui_cfg = data.get("ui_config", {}) or {}
        ui_cfg.update(updates)
        data["ui_config"] = ui_cfg
        ok = self._save_json(self.settings_file, data)
        if ok:
            self.ui_config = ui_cfg
            self.settings = data
        return ok

    # --------------- credit policy/history ---------------
    def load_credit_policy(self) -> dict:
        return self._load_json(self.credit_policy_file, default={})

    def load_credit_history(self) -> dict:
        return self._load_json(self.credit_history_file, default={})

    def load_app_data(self):
        """앱 데이터 로드 (app_state.json)"""
        try:
            data = self._load_json(self.state_file, {})
            self.credits = int(data.get("credits", 10))
            self.is_admin_mode = bool(data.get("is_admin_mode", False))
            self.license_email = str(data.get("license_email", "") or "")
        except Exception as e:
            self.logger.warning(f"앱 데이터 로드 오류: {e}")

    def save_app_data(self):
        """앱 데이터 저장 (app_state.json)"""
        try:
            data = {
                "credits": self.credits,
                "is_admin_mode": self.is_admin_mode,
                "license_email": self.license_email,
            }
            self._save_json(self.state_file, data)
        except Exception as e:
            self.logger.warning(f"앱 데이터 저장 오류: {e}")

    def update_credits(self, amount):
        """크레딧 업데이트"""
        if self.license_email:  # 라이선스가 있으면 크레딧 무제한
            return True

        if self.credits + amount >= 0:
            self.credits += amount
            self.save_app_data()
            return True
        return False

    def get_config(self):
        """현재 설정 반환"""
        return {
            "credits": self.credits,
            "license_email": self.license_email,
            "is_admin_mode": self.is_admin_mode,
            "admin_password": self.admin_password,
            "license_password": self.license_password,
            "data_file": self.state_file,
            "license_file": self.credit_history_file,
        }

    # --------------- license helpers ---------------
    def save_license_data(self, email: str) -> bool:
        """Persist license email into app_state.json and reset credits semantics."""
        try:
            self.license_email = str(email or "").strip()
            # If license provided, credits semantics become unlimited (-1 optional). Keep existing structure.
            self.save_app_data()
            return True
        except Exception as e:
            self.logger.warning(f"라이선스 저장 오류: {e}")
            return False

    # UI 헬퍼 메서드 (BOM2Excel/DWG 패턴)
    def get_last_selected_folder(self) -> str:
        """마지막 선택 폴더 경로 반환 (통합: settings.json ui_config.last_selected_folder)"""
        try:
            data = {}
            if self.settings_file.exists():
                with open(self.settings_file, "r", encoding="utf-8") as f:
                    data = json.load(f) or {}
            
            ui_cfg = data.get("ui_config", {}) or {}
            val = ui_cfg.get("last_selected_folder", "")
            return val if val else ""
        except Exception as e:
            self.logger.debug(f"마지막 선택 폴더 로드 실패: {e}")
            return ""

    def update_ui_last_folder(self, folder_path: str):
        """마지막 선택 폴더 경로 저장 (통합: settings.json ui_config.last_selected_folder)"""
        try:
            data = {}
            if self.settings_file.exists():
                with open(self.settings_file, "r", encoding="utf-8") as f:
                    data = json.load(f) or {}
            
            # ui_config 섹션이 없으면 생성
            if "ui_config" not in data:
                data["ui_config"] = {}
            
            data["ui_config"]["last_selected_folder"] = folder_path or ""
            
            # runtime_config 업데이트
            import datetime
            if "runtime_config" not in data:
                data["runtime_config"] = {}
            data["runtime_config"]["last_updated"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            with open(self.settings_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            # in-memory 반영
            self.ui_config = data.get("ui_config", {})
            self.settings = data
        except Exception as e:
            self.logger.warning(f"폴더 경로 저장 실패: {e}")

    # ===== 모드 헬퍼 =====
    def is_demo(self) -> bool:
        """데모 모드 여부 반환"""
        try:
            return getattr(self, "run_mode", "release") == "demo"
        except Exception:
            return False

    def is_dev(self) -> bool:
        """개발 모드 여부 반환"""
        try:
            return getattr(self, "run_mode", "release") == "dev"
        except Exception:
            return False

    def is_release(self) -> bool:
        """릴리스 모드 여부 반환"""
        try:
            return getattr(self, "run_mode", "release") == "release"
        except Exception:
            return True

    # ===== UI 헬퍼 =====
    def update_window_geometry_override(self, geometry: str | None) -> bool:
        """창 geometry 오버라이드를 settings.json에 반영한다."""
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

            # in-memory 반영
            self.window_geometry_override = geometry or ""
            return True
        except Exception as e:
            try:
                self.logger.warning(f"geometry 저장 실패: {e}")
            except Exception:
                pass
            return False

    def update_settings_window_geometry(self, geometry: str | None) -> bool:
        """세팅창 geometry를 settings.json에 반영한다."""
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
                self.logger.warning(f"settings_window geometry 저장 실패: {e}")
            except Exception:
                pass
            return False

    def update_registration_window_geometry(self, geometry: str | None) -> bool:
        """등록창 geometry를 settings.json에 반영한다."""
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
                self.logger.warning(f"registration_window geometry 저장 실패: {e}")
            except Exception:
                pass
            return False


# singleton
_singleton = None


def get_config(reload=False) -> Config:
    global _singleton
    if _singleton is None or reload:
        _singleton = Config()
    return _singleton
