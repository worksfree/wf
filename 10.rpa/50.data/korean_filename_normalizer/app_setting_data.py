# -*- coding: utf-8 -*-
"""
Korean Filename Normalizer Configuration Loader
사용자 정의 설정을 로드하고, 기본값을 제공하는 모듈.
"""

import json
import logging
from pathlib import Path
import os
import sys

# 글로벌 로거 import
import sys

common_path = Path(__file__).resolve().parents[2] / "10.common"
if str(common_path) not in sys.path:
    sys.path.insert(0, str(common_path))
# 동적 import로 Pylance 경고 회피 + 런타임 안전 처리
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
    """설정 관리 클래스 (canonical sections)"""

    # 🚀 클래스 레벨 캐시 (파일 수정 시간 기반)
    _policy_cache = None
    _policy_cache_mtime = None

    def __init__(self):
        self.base_dir = str(Path(__file__).resolve().parent)
        self.user_home = Path.home()

        # 런모드 판별: settings.json(app_config.run_mode)만 사용
        self.run_mode = self._detect_run_mode()

        app_root = Path(self.base_dir)
        # 통합 config 경로: 10.common/config/ (개발), ~/.wf_rpa/ (배포)
        common_config_dir = app_root.parents[1] / "10.common" / "config"

        # PyInstaller frozen 환경(exe)에서는 항상 사용자 홈 경로 사용 (번들 파일은 읽기 전용)
        import sys
        is_frozen = getattr(sys, 'frozen', False)

        if is_frozen or self.run_mode == "release":
            self.app_config_dir = self.user_home / ".wf_rpa" / "korean_filename_normalizer"
        else:
            self.app_config_dir = common_config_dir / "korean_filename_normalizer"

        # Lazy logger
        self._logger = None

        # Files
        self.settings_file = self.app_config_dir / "settings.json"
        try:
            self.logger.info(f"[CONFIG] run_mode={self.run_mode}, settings_file={self.settings_file}")
        except Exception:
            pass
        
        # 설정 파일 초기화 (처음 설치 시 기본 구조 생성)
        self._ensure_settings_file()

        # Paths
        if self.run_mode in ("dev", "demo"):
            self.log_dir = Path(self.base_dir) / "logs"
            self.res_dir = Path(self.base_dir) / "res"
        else:
            base = Path.home() / ".wf_rpa" / "korean_filename_normalizer"
            self.log_dir = base / "logs"
            self.res_dir = base / "res"

        self._ensure_directories()

        # Load settings
        self.settings = self._load_json(self.settings_file, default={})

        # Apply canonical sections
        self._apply_config(self.settings)

    def _detect_run_mode(self) -> str:
        """settings.json(runtime_config.run_mode)만 사용하여 실행 모드 결정"""
        # 통합 config 경로 사용: 10.common/config/korean_filename_normalizer/settings.json
        app_root = Path(__file__).resolve().parent
        settings_path = app_root.parents[1] / "10.common" / "config" / "korean_filename_normalizer" / "settings.json"
        try:
            with open(settings_path, "r", encoding="utf-8") as f:
                data = json.load(f) or {}
            cfg_mode = str(data.get("runtime_config", {}).get("run_mode", "") or "").strip().lower()
            return cfg_mode if cfg_mode in ("dev", "demo", "release") else "release"
        except Exception:
            return "release"

    @property
    def logger(self):
        """🚀 Lazy loading logger"""
        if self._logger is None:
            self._logger = wflog.get_app_logger(
                "Korean_Filename_Normalizer", console_level=logging.DEBUG
            )
        return self._logger

    def _ensure_directories(self):
        """필요한 디렉토리들을 생성"""
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.res_dir.mkdir(parents=True, exist_ok=True)
        self.app_config_dir.mkdir(parents=True, exist_ok=True)
    
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
            "logging_config": {...},
            "normalizer_settings": {...}
        }
        """
        if not self.settings_file.exists():
            # exe 환경: 번들된 설정 파일이 있으면 복사
            import sys
            import shutil
            is_frozen = getattr(sys, 'frozen', False)
            if is_frozen:
                bundled_config = Path(self.base_dir) / "config" / "korean_filename_normalizer" / "settings.json"
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
                    "full_version": "unknown",
                    "build_count": 0,
                    "ui_scale": 1.0,
                    "language": "ko",
                    "last_updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                },
                "ui_config": {
                    "last_selected_folder": "",
                    "window_geometry": "700x400",
                    "admin_window_geometry": "700x800",
                    "show_admin_mode": False
                },
                "logging_config": {
                    "log_level": "INFO",
                    "max_log_size_mb": 10,
                    "rotate_logs": True
                },
                "normalizer_settings": {
                    "default_folder_path": "",
                    "backup_enabled": True,
                    "recursive_scan": True,
                    "include_hidden_files": False,
                    "auto_backup": True,
                    "supported_extensions": [".txt", ".docx", ".xlsx", ".pptx", ".pdf", ".jpg", ".png", ".mp4", ".avi", ".zip", ".rar"],
                    "skip_system_files": True,
                    "conflict_resolution": "auto_rename",
                    "save_to_new_folder": True,
                    "normalization_method": "nfc_plus_manual",
                    "preserve_extension_case": True,
                    "log_changes": True
                }
            }
            
            # 새 통합 설정 파일 저장
            try:
                with open(self.settings_file, "w", encoding="utf-8") as f:
                    json.dump(unified_settings, f, ensure_ascii=False, indent=2)
                self.logger.info(f"✅ 통합 설정 파일 생성: {self.settings_file}")
            except Exception as e:
                self.logger.error(f"⚠️ 설정 파일 생성 실패: {e}")

    def _load_json(self, path: Path, default=None):
        try:
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            self.logger.error(f"JSON 로드 실패({path}): {e}")
        return default if default is not None else {}

    def _apply_config(self, config_data):
        """설정 데이터 적용 (canonical sections)"""
        app_config = config_data.get("runtime_config", {})
        ui_config = config_data.get("ui_config", {}) or {}
        logging_config = config_data.get("logging_config", {})
        normalizer = config_data.get("normalizer_settings", {})

        # ui_config를 메모리에 유지하여 창 크기/geometry 오버라이드를 설정파일 그대로 사용
        self.ui_config = ui_config
        self.window_geometry_override = ui_config.get("window_geometry_override", "")

        # Versions & UI scale
        self.version = app_config.get("full_version", "unknown")
        self.build_count = app_config.get("build_count", 0)
        self.ui_scale = float(app_config.get("ui_scale", 1.0))

        # UI
        self.window_geometry = ui_config.get("window_geometry", "700x400")
        self.admin_window_geometry = ui_config.get("admin_window_geometry", "700x800")
        self.show_admin_mode = ui_config.get("show_admin_mode", False)
        # 선택적으로 저장된 폭/높이 사용 (없으면 기존 로직 유지)
        self.window_width = ui_config.get("window_width")
        self.window_height = ui_config.get("window_height")

        # Logging
        self.log_level = logging_config.get("log_level", "INFO")
        self.max_log_size_mb = logging_config.get("max_log_size_mb", 10)
        self.rotate_logs = logging_config.get("rotate_logs", True)

        # Domain settings
        self.default_folder_path = normalizer.get("default_folder_path", "")
        self.backup_enabled = normalizer.get("backup_enabled", True)
        self.recursive_scan = normalizer.get("recursive_scan", True)
        self.include_hidden_files = normalizer.get("include_hidden_files", False)
        self.auto_backup = normalizer.get("auto_backup", True)
        self.supported_extensions = normalizer.get(
            "supported_extensions",
            [
                ".txt",
                ".docx",
                ".xlsx",
                ".pptx",
                ".pdf",
                ".jpg",
                ".png",
                ".mp4",
                ".avi",
                ".zip",
                ".rar",
            ],
        )
        self.skip_system_files = normalizer.get("skip_system_files", True)
        self.conflict_resolution = normalizer.get("conflict_resolution", "auto_rename")
        self.save_to_new_folder = normalizer.get("save_to_new_folder", True)
        self.normalization_method = normalizer.get("normalization_method", "nfc_plus_manual")
        self.preserve_extension_case = normalizer.get("preserve_extension_case", True)
        self.log_changes = normalizer.get("log_changes", True)

    def get(self, key, default=None):
        """설정값 가져오기 (config.get() 호환)"""
        return getattr(self, key, default)

    def set(self, key, value):
        """설정값 설정하기"""
        setattr(self, key, value)

    def update_config(self, config_dict):
        """설정 일괄 업데이트"""
        for key, value in config_dict.items():
            setattr(self, key, value)

    def save_settings(self) -> bool:
        """현재 설정을 canonical sections로 저장"""
        try:
            data = {}
            if self.settings_file.exists():
                try:
                    with open(self.settings_file, "r", encoding="utf-8") as f:
                        data = json.load(f) or {}
                except Exception:
                    data = {}

            data["runtime_config"] = {
                "full_version": self.version,
                "build_count": self.build_count,
                "ui_scale": self.ui_scale,
                "language": getattr(self, "language", "ko"),
            }

            data["ui_config"] = {
                "window_geometry": self.window_geometry,
                "admin_window_geometry": self.admin_window_geometry,
                "show_admin_mode": self.show_admin_mode,
            }

            data["logging_config"] = {
                "log_level": self.log_level,
                "max_log_size_mb": self.max_log_size_mb,
                "rotate_logs": self.rotate_logs,
            }

            data["normalizer_settings"] = {
                "default_folder_path": self.default_folder_path,
                "backup_enabled": self.backup_enabled,
                "recursive_scan": self.recursive_scan,
                "include_hidden_files": self.include_hidden_files,
                "auto_backup": self.auto_backup,
                "supported_extensions": self.supported_extensions,
                "skip_system_files": self.skip_system_files,
                "conflict_resolution": self.conflict_resolution,
                "save_to_new_folder": self.save_to_new_folder,
                "normalization_method": self.normalization_method,
                "preserve_extension_case": self.preserve_extension_case,
                "log_changes": self.log_changes,
            }

            self.settings_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.settings_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            self.logger.error(f"설정 저장 실패: {e}")
            return False

    def load_settings(self):
        """레거시: 유지 필요 없음 (canonical로 일원화)"""
        return self._load_json(self.settings_file, default={})

    def increment_usage(self):
        """사용 횟수 증가 - 이제 wf_rpa_config.json의 app_execution.run_count를 통해 관리됨"""
        # This is now handled by WFRPAManager in wf_rpa_config.json
        # Kept as no-op for backward compatibility
        pass

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
            if hasattr(self, "logger"):
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
            self.settings = data
        except Exception as e:
            if hasattr(self, "logger"):
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
                if hasattr(self, "logger"):
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
                if hasattr(self, "logger"):
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
                if hasattr(self, "logger"):
                    self.logger.warning(f"registration_window geometry 저장 실패: {e}")
            except Exception:
                pass
            return False


# 전역 설정 인스턴스
_config = None


def get_config(reload=False):
    """설정 인스턴스 반환 (싱글턴 패턴)"""
    global _config
    if _config is None or reload:
        _config = Config()
    return _config
