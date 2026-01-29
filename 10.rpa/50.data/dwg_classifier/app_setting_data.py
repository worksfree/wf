# -*- coding: utf-8 -*-
"""
DWG Classifier Configuration Loader
사용자 정의 설정(.dwg_classifier_settings.json)을 로드하고,
기본값을 제공하는 모듈.
"""

import os
import json
import logging
from pathlib import Path
import sys

# 글로벌 로거 import
import sys

common_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "10.common"))
if common_path not in sys.path:
    sys.path.insert(0, common_path)
import wf_log as wflog


class Config:
    """설정 관리 클래스 (단순화 버전)"""

    # 🚀 클래스 레벨 캐시 (파일 수정 시간 기반)
    _policy_cache = None
    _policy_cache_mtime = None

    def __init__(self):
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.user_home = Path.home()

        # 런모드 판별: settings.json(app_config.run_mode)만 사용
        self.run_mode = self._detect_run_mode()

        # 통합 config 경로: 10.common/config/ (개발), ~/.wf_rpa/ (배포)
        app_root = Path(self.base_dir)
        common_config_dir = app_root.parents[1] / "10.common" / "config"

        # PyInstaller frozen 환경(exe)에서는 항상 사용자 홈 경로 사용 (번들 파일은 읽기 전용)
        import sys
        is_frozen = getattr(sys, 'frozen', False)

        if is_frozen or self.run_mode == "release":
            self.app_config_dir = self.user_home / ".wf_rpa" / "dwg_classifier"
        else:
            self.app_config_dir = common_config_dir / "dwg_classifier"        
        # PyInstaller frozen 환경에서 번들 리소스 경로 저장
        if is_frozen:
            self.bundle_dir = Path(getattr(sys, '_MEIPASS', self.base_dir))
        else:
            self.bundle_dir = app_root
        # 🚀 최적화: 로거 lazy loading (첫 사용 시 초기화)
        self._logger = None

        # 로그 레벨 상수
        self.SHOW_DEBUG = 10  # 개발자 정보(디버깅 목적)
        self.SHOW_INFO = 20  # 사용자 정보
        self.SHOW_WARNING = 30  # 경고 메시지
        self.SHOW_ERROR = 40  # 오류 메시지

        # 통합 사용자 설정 파일 (배포: ~/.wf_rpa/dwg_classifier/settings.json)
        self.settings_file = self.app_config_dir / "settings.json"
        try:
            self.logger.info(f"[CONFIG] run_mode={self.run_mode}, settings_file={self.settings_file}")
        except Exception:
            pass
        
        # 설정 파일 초기화 (처음 설치 시 기본 구조 생성)
        self._ensure_settings_file()

        # 경로 설정 (로그/리소스): dev/demo는 작업 디렉터리, release는 사용자 홈
        if self.run_mode in ("dev", "demo"):
            self.log_dir = Path(self.base_dir) / "logs"
            self.res_dir = Path(self.base_dir) / "res"
        else:
            base = Path.home() / ".wf_rpa" / "Dwg_Classifier"
            self.log_dir = base / "logs"
            self.res_dir = base / "res"

        # 디렉토리 생성
        self._ensure_directories()

        # 설정 로드
        self._load_config()

    def _detect_run_mode(self) -> str:
        """settings.json(runtime_config.run_mode)만 사용하여 실행 모드 결정"""
        # 통합 config 경로 사용: 10.common/config/dwg_classifier/settings.json
        app_root = Path(__file__).resolve().parent
        settings_path = app_root.parents[1] / "10.common" / "config" / "dwg_classifier" / "settings.json"
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
            self._logger = wflog.get_app_logger("Dwg_Classifier", console_level=logging.DEBUG)
        return self._logger

    def _ensure_directories(self):
        """필요한 디렉토리들을 생성"""
        os.makedirs(self.log_dir, exist_ok=True)
        os.makedirs(self.res_dir, exist_ok=True)
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
            "classifier_settings": {...}
        }
        """
        if not self.settings_file.exists():
            # exe 환경: 번들된 설정 파일이 있으면 복사
            import sys
            import shutil
            is_frozen = getattr(sys, 'frozen', False)
            if is_frozen:
                # PyInstaller _MEIPASS 경로 사용
                bundled_config = self.bundle_dir / "config" / "dwg_classifier" / "settings.json"
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
                else:
                    try:
                        self.logger.warning(f"[CONFIG] 번들 설정 파일 없음: {bundled_config}")
                    except Exception:
                        pass
            import datetime
            # 통합 설정 파일 생성 (기본값)
            unified_settings = {
                "runtime_config": {
                    "run_mode": "release",
                    "max_workers": 4,
                    "memory_limit_mb": 2048,
                    "admin_mode": False,
                    "speed_mode": "normal",
                    "ui_scale": 1.0,
                    "last_updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                },
                "ui_config": {
                    "last_selected_folder": "",
                    "show_log": False,
                    "auto_scroll": True,
                    "show_progress": True,
                    "topmost": True,
                    "window_width": 580,
                    "window_height": 320,
                    "window_geometry_override": ""
                },
                "logging_config": {
                    "log_level": "INFO",
                    "max_log_size_mb": 10,
                    "rotate_logs": True
                },
                "classifier_settings": {
                    "drawing_column": "도번/규격",
                    "category_column": "제조사/가공분류",
                    "excel_sheet_name": "구매요청",
                    "use_exact_match": True,
                    "use_partial_match": True,
                    "case_sensitive": False,
                    "file_extensions": [".dwg", ".DWG"],
                    "create_backup": False,
                    "output_folder": "",
                    "file_operation_mode": "copy"
                },
                "processed_files": {}
            }
            
            # 새 통합 설정 파일 저장
            try:
                with open(self.settings_file, "w", encoding="utf-8") as f:
                    json.dump(unified_settings, f, ensure_ascii=False, indent=2)
                self.logger.info(f"✅ 통합 설정 파일 생성: {self.settings_file}")
            except Exception as e:
                self.logger.error(f"⚠️ 설정 파일 생성 실패: {e}")

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

        # 크레딧 정책 파일 로드
        policy_config = self._load_credit_policy()

        # 정책 설정으로 config_data 오버라이드
        if policy_config:
            if "app_config" not in config_data:
                config_data["app_config"] = {}
            config_data["app_config"].update(policy_config)
            self.logger.info(f"크레딧 정책 설정 적용: {list(policy_config.keys())}")

        self._apply_config(config_data)

    def _load_credit_policy(self):
        """크레딧 정책 파일 로드 (policy.json → policy)"""
        try:
            policy_file = self.app_config_dir / "policy.json"

            if not policy_file.exists():
                return {}

            # 🚀 캐시 체크: 파일 수정 시간 확인
            current_mtime = policy_file.stat().st_mtime
            if Config._policy_cache is not None and Config._policy_cache_mtime == current_mtime:
                self.logger.debug(f"[캐시] 정책 파일 캐시 사용: {policy_file}")
                return Config._policy_cache

            # 파일이 변경되었거나 캐시가 없으면 로드
            with open(policy_file, "r", encoding="utf-8") as f:
                raw = json.load(f)
                # 병합 구조에서 policy 섹션만 사용
                policy_data = raw.get("policy", {}) if isinstance(raw, dict) else {}

                # 🚀 캐시 업데이트
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
        app_config = config_data.get("runtime_config", {})
        ui_config = config_data.get("ui_config", {}) or {}
        logging_config = config_data.get("logging_config", {})

        # ui_config를 메모리에 보존하여 창 크기/geometry 오버라이드를 설정 파일 그대로 사용
        self.ui_config = ui_config
        self.window_geometry_override = ui_config.get("window_geometry_override", "")

        # Run Mode 처리: settings.json 값만 사용 (기본은 초기 런모드 유지)
        cfg_mode = str(app_config.get("run_mode", "")).strip().lower() if app_config else ""
        default_mode = getattr(self, "run_mode", "release")
        self.run_mode = cfg_mode if cfg_mode in ("dev", "release", "demo") else default_mode

        # 앱 버전: settings.json 내 runtime_config.full_version 사용, 없으면 'unknown'
        app_config = config_data.get("runtime_config", {})
        self.version = app_config.get("full_version", "unknown")

        # DWG Classifier 전용 설정
        classifier_settings = config_data.get("classifier_settings", {})
        self.drawing_column = classifier_settings.get("drawing_column", "도번/규격")
        self.category_column = classifier_settings.get("category_column", "제조사/가공분류")
        self.excel_sheet_name = classifier_settings.get("excel_sheet_name", "구매요청")

        # 매칭 설정
        self.use_exact_match = classifier_settings.get("use_exact_match", True)
        self.use_partial_match = classifier_settings.get("use_partial_match", True)
        self.case_sensitive = classifier_settings.get("case_sensitive", False)
        # 파일 설정
        self.file_extensions = classifier_settings.get("file_extensions", [".dwg", ".DWG"])
        self.create_backup = classifier_settings.get("create_backup", False)
        # 출력 폴더 (사용자 지정 분류 결과 저장 위치, 없으면 실행 폴더 내 classified_dwg 사용)
        self.output_folder = classifier_settings.get("output_folder", "")
        # 파일 작업 모드 설정 ('copy': 복사, 'move': 이동)
        self.file_operation_mode = classifier_settings.get("file_operation_mode", "copy")

        # UI 설정 (ui_config)
        self.show_log = ui_config.get("show_log", False)
        self.auto_scroll = ui_config.get("auto_scroll", True)
        self.show_progress = ui_config.get("show_progress", True)
        self.confirm_operations = ui_config.get("confirm_operations", True)
        self.window_width = ui_config.get("window_width")
        self.window_height = ui_config.get("window_height")
        self.ui_theme = ui_config.get("ui_theme", "기본")
        self.font_size = ui_config.get("font_size", 10)
        self.topmost = ui_config.get("topmost", True)
        # 선택적 창 위치/크기 오버라이드 (debug hotkey용)
        self.window_geometry_override = ui_config.get("window_geometry_override", "")

        # 관리자 설정
        self.admin_mode = app_config.get("admin_mode", False)

        # 경로 설정
        self.last_excel_paths = app_config.get("last_excel_paths", [])
        self.last_drawings_path = app_config.get("last_drawings_path", "")

        # 성능/표시 설정
        self.max_workers = app_config.get("max_workers", 4)
        self.memory_limit_mb = app_config.get("memory_limit_mb", 2048)
        self.ui_scale = float(app_config.get("ui_scale", 1.0))

        # 로그 설정 (logging_config)
        self.log_level = logging_config.get("log_level", "INFO")
        self.max_log_size_mb = logging_config.get("max_log_size_mb", 10)
        self.rotate_logs = logging_config.get("rotate_logs", True)

        # 오류 처리 설정
        self.stop_on_error = app_config.get("stop_on_error", False)
        self.skip_invalid_files = app_config.get("skip_invalid_files", True)
        self.retry_count = app_config.get("retry_count", 2)

        speed_mode = app_config.get("speed_mode", "normal")

        # 속도 설정
        speed_map = {"slow": 0.5, "normal": 0.3, "fast": 0.1}
        self.my_pace = speed_map.get(speed_mode, 0.3)

        # 사용자 설정
        user_settings = config_data.get("user_settings", {})
        self.user_email = user_settings.get("user_email", "")
        self.report_email = user_settings.get("report_email", self.user_email)

    # ----------------------
    # Settings mutation APIs
    # ----------------------
    def update_config(self, key_or_dict, value=None):
        """Update one or multiple config values in-memory.
        Accepts either (key, value) or a dict of key->value pairs.
        """
        if isinstance(key_or_dict, dict):
            for k, v in key_or_dict.items():
                setattr(self, k, v)
        else:
            setattr(self, key_or_dict, value)

    def save_settings(self):
        """Persist current config back to settings.json with structured sections.
        Only writes the subset of fields relevant to user customization to keep file clean.
        Returns True on success, False otherwise.
        """
        try:
            data = {}
            if self.settings_file.exists():
                try:
                    with open(self.settings_file, "r", encoding="utf-8") as f:
                        data = json.load(f) or {}
                except Exception:
                    data = {}

            # compose classifier_settings
            classifier_settings = {
                "drawing_column": self.drawing_column,
                "category_column": self.category_column,
                "excel_sheet_name": self.excel_sheet_name,
                "file_extensions": self.file_extensions,
                "create_backup": self.create_backup,
                "use_exact_match": self.use_exact_match,
                "use_partial_match": self.use_partial_match,
                "case_sensitive": self.case_sensitive,
                "output_folder": self.output_folder,
                "file_operation_mode": self.file_operation_mode,
            }
            data["classifier_settings"] = classifier_settings

            # compose runtime_config (runtime/perf subset)
            app_config = data.get("runtime_config", {})
            app_config.update(
                {
                    "max_workers": self.max_workers,
                    "memory_limit_mb": self.memory_limit_mb,
                    "admin_mode": self.admin_mode,
                }
            )
            data["runtime_config"] = app_config

            # compose ui_config
            ui_config = data.get("ui_config", {})
            ui_config.update(
                {
                    "show_log": self.show_log,
                    "auto_scroll": self.auto_scroll,
                    "show_progress": self.show_progress,
                    "ui_theme": self.ui_theme,
                    "font_size": self.font_size,
                    "topmost": self.topmost,
                    "window_geometry_override": self.window_geometry_override,
                }
            )
            data["ui_config"] = ui_config

            # compose logging_config
            logging_config = data.get("logging_config", {})
            logging_config.update(
                {
                    "log_level": self.log_level,
                    "max_log_size_mb": self.max_log_size_mb,
                    "rotate_logs": self.rotate_logs,
                }
            )
            data["logging_config"] = logging_config

            # user_settings passthrough if present
            user_settings = data.get("user_settings", {})
            if self.user_email and "user_email" not in user_settings:
                user_settings["user_email"] = self.user_email
            data["user_settings"] = user_settings

            # app_info 제거: full_version만 단일 소스로 유지 (빌드/정책 로직이 관리)

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
                self.logger.error(f"geometry 저장 실패: {e}")
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
                self.logger.error(f"settings_window geometry 저장 실패: {e}")
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
                self.logger.error(f"registration_window geometry 저장 실패: {e}")
            except Exception:
                pass
            return False

    # ---------------- UI helpers ----------------
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

    def update_ui_last_folder(self, path: str | None) -> bool:
        """마지막 선택 폴더 저장 (통합: settings.json ui_config.last_selected_folder)"""
        try:
            data = {}
            if self.settings_file.exists():
                with open(self.settings_file, "r", encoding="utf-8") as f:
                    data = json.load(f) or {}
            
            # ui_config 섹션이 없으면 생성
            if "ui_config" not in data:
                data["ui_config"] = {}
            
            data["ui_config"]["last_selected_folder"] = path or ""
            
            # runtime_config 업데이트
            import datetime
            if "runtime_config" not in data:
                data["runtime_config"] = {}
            data["runtime_config"]["last_updated"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            with open(self.settings_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            self.logger.error(f"마지막 선택 폴더 저장 실패: {e}")
            return False

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


# 전역 설정 인스턴스
_config = None


def get_config(reload=False):
    """설정 인스턴스 반환 (싱글톤 패턴)"""
    global _config
    if _config is None or reload:
        _config = Config()
    return _config
