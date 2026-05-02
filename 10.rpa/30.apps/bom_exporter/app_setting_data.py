# -*- coding: utf-8 -*-
"""
Bom Exporter Configuration Loader
통합 사용자 설정(settings.json)을 로드하고,
기본값을 제공하는 모듈.
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
# 동적 import로 Pylance 경고 회피 + 런타임 안전 처리
import importlib

try:
    wflog = importlib.import_module("wf_log")
except Exception:
    # 폴백 로거 팩토리
    _fallback_logger = logging.getLogger(__name__)
    if not _fallback_logger.handlers:
        _handler = logging.StreamHandler()
        _handler.setLevel(logging.DEBUG)
        _fallback_logger.addHandler(_handler)
        _fallback_logger.setLevel(logging.DEBUG)

    class _DummyLog:
        def get_app_logger(self, name, console_level=logging.DEBUG):
            lg = logging.getLogger(name)
            if not lg.handlers:
                h = logging.StreamHandler()
                h.setLevel(console_level)
                lg.addHandler(h)
                lg.setLevel(console_level)
            return lg

    wflog = _DummyLog()


class Config:
    """설정 관리 클래스 (단순화 버전)"""

    # 🚀 클래스 레벨 캐시 (파일 수정 시간 기반)
    _policy_cache = None
    _policy_cache_mtime = None

    def __init__(self):
        self.base_dir = str(Path(__file__).resolve().parent)
        self.user_home = Path.home()

        # 런모드는 settings.json 기준, 경로는 모드별 분기
        self.run_mode = self._detect_run_mode()

        app_root = Path(self.base_dir)
        # 통합 config 경로: 10.common/config/ (개발), ~/.wf_rpa/ (배포)
        common_config_dir = app_root.parents[1] / "10.common" / "config"

        # PyInstaller frozen 환경(exe)에서는 항상 사용자 홈 경로 사용 (번들 파일은 읽기 전용)
        import sys
        is_frozen = getattr(sys, 'frozen', False)

        # dev: 소스트리, demo/release: 홈폴더
        if self.run_mode == "dev":
            self.app_config_dir = common_config_dir / "bom_exporter"
        else:
            self.app_config_dir = self.user_home / ".wf_rpa" / "bom_exporter"
        
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

        # 통합 사용자 설정 파일 (소스 트리만 사용)
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
            base = Path.home() / ".wf_rpa" / "Bom_Exporter"
            self.log_dir = base / "logs"
            self.res_dir = base / "res"

        # 디렉토리 생성
        self._ensure_directories()

        # 🚀 최적화: 정책 로딩을 나중으로 지연 (백그라운드)
        # 설정 로드 (사용자 설정만, 정책은 제외)
        self._load_config_fast()

    def _detect_run_mode(self) -> str:
        # 통합 config 경로 사용: 10.common/config/bom_exporter/settings.json
        app_root = Path(__file__).resolve().parent
        settings_path = app_root.parents[1] / "10.common" / "config" / "bom_exporter" / "settings.json"
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
            self._logger = wflog.get_app_logger("Bom_Exporter", console_level=logging.DEBUG)
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
            "solidworks": {"program_path": "C:\\Program Files\\"},
            "app_config": {
                "restart_count": 20,
                "topmost": true,
                "auto_restart": true,
                "speed_mode": "normal",
                "base_wait_time": 60,
                "seconds_per_10mb": 60,
                "include_thumbnail": true
            },
            "ui_config": {"last_selected_folder": ""}
        }
        """
        if not self.settings_file.exists():
            # exe 환경: 번들된 설정 파일이 있으면 복사
            import sys
            import shutil
            is_frozen = getattr(sys, 'frozen', False)
            if is_frozen:
                # PyInstaller에서 settings.json은 .wf_rpa/bom_exporter/ 경로에 번들됨
                bundled_config = self.bundle_dir / ".wf_rpa" / "bom_exporter" / "settings.json"
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
            # 통합 설정 파일 생성 (기본값)
            unified_settings = {
                "solidworks": {
                    "program_path": "C:\\Program Files\\SOLIDWORKS Corp\\SOLIDWORKS\\SLDWORKS.exe"
                },
                "runtime_config": {
                    "run_mode": "release",  # dev | release | demo (env WF_RPA_MODE로도 설정 가능)
                    "restart_count": 20,
                    "auto_restart": True,
                    "speed_mode": "normal",
                    "base_wait_time": 60,
                    "seconds_per_10mb": 60,
                    "include_thumbnail": True,
                    "ui_scale": 1.0,
                    "last_updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                },
                "ui_config": {
                    "topmost": True,
                    "last_selected_folder": "",
                    "window_geometry_override": "",
                    "window_width": 580,
                    "window_height": 200
                }
            }
            
            # 새 통합 설정 파일 저장
            try:
                with open(self.settings_file, "w", encoding="utf-8") as f:
                    json.dump(unified_settings, f, ensure_ascii=False, indent=2)
                self.logger.info(f"✅ 통합 설정 파일 생성: {self.settings_file}")
            except Exception as e:
                self.logger.error(f"⚠️ 설정 파일 생성 실패: {e}")

    def _load_config_fast(self):
        """🚀 빠른 설정 로드 (사용자 설정만, 정책은 나중에 백그라운드로)"""
        config_data = {}
        try:
            if self.settings_file.exists():
                with open(self.settings_file, "r", encoding="utf-8") as f:
                    config_data = json.load(f)
                self.logger.info(f"사용자 설정 로드 완료: {self.settings_file}")
        except Exception as e:
            self.logger.error(f"사용자 설정 파일 로드 실패: {e}")

        # 정책은 로드하지 않고 기본값으로 시작
        self._apply_config(config_data)

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
            if "runtime_config" not in data:
                data["runtime_config"] = {}
            data["runtime_config"]["last_updated"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            with open(self.settings_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            self.logger.error(f"마지막 선택 폴더 저장 실패: {e}")
            return False

    def load_policies_async(self):
        """🚀 백그라운드에서 정책 로드 및 적용 (UI 표시 후 호출)"""
        policy_config = self._load_app_policy_cached()

        if policy_config:
            # 기존 설정을 읽어서 정책으로 오버라이드
            config_data = {}
            try:
                if self.settings_file.exists():
                    with open(self.settings_file, "r", encoding="utf-8") as f:
                        config_data = json.load(f)
            except Exception:
                pass

            if "runtime_config" not in config_data:
                config_data["runtime_config"] = {}
            config_data["runtime_config"].update(policy_config)
            self.logger.info(f"[백그라운드] 앱밸 정책 설정 적용: {list(policy_config.keys())}")

            # 설정 재적용
            self._apply_config(config_data)

    def _load_config(self):
        """설정 파일 로드 (레거시 - 동기 방식)"""
        config_data = {}
        try:
            if self.settings_file.exists():
                with open(self.settings_file, "r", encoding="utf-8") as f:
                    config_data = json.load(f)
                self.logger.info(f"사용자 설정 로드 완료: {self.settings_file}")
        except Exception as e:
            self.logger.error(f"사용자 설정 파일 로드 실패: {e}")

        # 앱밸 정책 파일 로드 (구글 시트 동기화된 정책)
        policy_config = self._load_app_policy_cached()

        # 정책 설정으로 config_data 오버라이드
        if policy_config:
            if "runtime_config" not in config_data:
                config_data["runtime_config"] = {}
            config_data["runtime_config"].update(policy_config)
            self.logger.info(f"앱밸 정책 설정 적용: {list(policy_config.keys())}")

        self._apply_config(config_data)

    def _load_app_policy_cached(self):
        """🚀 캐시된 정책 로드 (파일 수정 시간 체크)"""
        try:
            # 통합 config 경로: 10.common/config/ (개발), ~/.wf_rpa/ (배포)
            app_root = Path(self.base_dir)
            common_config_dir = app_root.parents[1] / "10.common" / "config"
            is_dev_mode = self.run_mode in ("dev", "demo")

            if is_dev_mode:
                # 개발: 10.common/config/bom_exporter/credit_policy.json
                policy_file = common_config_dir / "bom_exporter" / "credit_policy.json"
            else:
                # 배포: ~/.wf_rpa/bom_exporter/credit_policy.json
                policy_file = self.app_config_dir / "credit_policy.json"

            if not policy_file.exists():
                return {}

            # 🚀 캐시 체크: 파일 수정 시간 확인
            current_mtime = policy_file.stat().st_mtime
            if Config._policy_cache is not None and Config._policy_cache_mtime == current_mtime:
                self.logger.debug(f"[캐시] 정책 파일 캐시 사용: {policy_file}")
                return Config._policy_cache

            # 파일이 변경되었거나 캐시가 없으면 로드
            with open(policy_file, "r", encoding="utf-8") as f:
                policy_data = json.load(f)

                # credit_policy.json 구조에 맞게 수정
                # 직접 정책 데이터를 읽음 (policies.bom_exporter 구조가 아님)

                # 앱 설정에 영향을 주는 필드만 추출
                app_config_fields = [
                    "memory_threshold_percent",
                    "enable_memory_monitor",
                    "base_wait_time",
                    "seconds_per_10mb",
                    "restart_count",
                    "consec_timeout_limit",
                ]

                extracted_config = {}
                for field in app_config_fields:
                    if field in policy_data:
                        extracted_config[field] = policy_data[field]

                # 🚀 캐시 업데이트
                Config._policy_cache = extracted_config
                Config._policy_cache_mtime = current_mtime

                if extracted_config:
                    self.logger.debug(f"[새로 로드] 앱밸 정책에서 설정 로드: {extracted_config}")
                    return extracted_config
        except Exception as e:
            self.logger.warning(f"크레딧 정책 파일 로드 실패: {e}")

        return {}

    def _load_app_policy(self):
        """크레딧 정책 파일에서 bom_exporter 설정 로드 (credit_policy.json)"""
        return self._load_app_policy_cached()

    def _apply_config(self, config_data):
        """설정 데이터 적용"""
        app_config = config_data.get("runtime_config", {})  # 사용자 정의 설정 우선

        # ui_config 섹션을 메모리에 유지하여 설정창/메인창이 실제 저장값을 읽도록 한다.
        ui_config = config_data.get("ui_config", {}) or {}
        self.ui_config = ui_config
        self.window_geometry_override = ui_config.get("window_geometry_override", "")

        # 창 크기 (settings.json 우선, 없으면 코드 기본값)
        self.window_width = ui_config.get("window_width", 580)  # bom_exporter 기본 너비
        self.window_height = ui_config.get("window_height", 200)  # bom_exporter 기본 높이

        # 실행 모드 결정: settings.json 값만 사용, 없으면 초기 런모드 유지
        cfg_mode = str(app_config.get("run_mode", "")).strip().lower() if app_config else ""
        default_mode = getattr(self, "run_mode", "release")
        self.run_mode = cfg_mode if cfg_mode in ("dev", "release", "demo") else default_mode

        # 동적 타임아웃 설정 (기본값: 120초 base + 60초 per 10MB)
        self.base_wait_time = int(app_config.get("base_wait_time", 120))
        self.seconds_per_10mb = int(app_config.get("seconds_per_10mb", 60))

        # 파일 저장 대기 시간 multiplier (현재 사용 안함, 하위호환을 위해 유지)
        self.file_save_wait_multiplier = int(app_config.get("file_save_wait_multiplier", 2))

        # wait_time 속성을 base_wait_time으로 유지하여 기존 코드에 미치는 영향 최소화
        self.wait_time = self.base_wait_time

        self.restart_count = app_config.get("restart_count", 20)
        speed_mode = app_config.get("speed_mode", "normal")

        # 메모리 모니터링 설정 (기본값: 활성화, 가용 메모리 20% 이하면 재시작)
        self.enable_memory_monitor = app_config.get("enable_memory_monitor", True)
        self.memory_threshold_percent = int(app_config.get("memory_threshold_percent", 20))

        # 연속 타임아웃 임계치 (기본값: 2회)
        self.consec_timeout_limit = int(app_config.get("consec_timeout_limit", 2))

        # 속도 설정
        speed_map = {"slow": 2, "normal": 0.3, "fast": 0.1}
        self.my_pace = speed_map.get(speed_mode, 0.3)

        # 앱 버전 (full_version 없으면 'unknown')
        app_config = config_data.get("app_config", {})
        self.version = app_config.get("full_version", "unknown")

        # SolidWorks 설정
        solidworks = config_data.get("solidworks", {})
        self.program_path = solidworks.get(
            "program_path", "C:\\Program Files\\SOLIDWORKS Corp\\SOLIDWORKS\\SLDWORKS.exe"
        )
        self.application_title = "SOLIDWORKS.*"  # 고정값

        # 이메일 설정은 .wf_rpa_config.json에서 로드하므로 여기서는 제거됨
        # automation.py의 init_console_mode()에서 .wf_rpa_config.json 로드

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

            # app_info 업데이트
            if "app_info" not in data:
                data["app_info"] = {}
            data["app_info"]["last_updated"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

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

            # app_info 업데이트
            if "app_info" not in data:
                data["app_info"] = {}
            data["app_info"]["last_updated"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

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

            # app_info 업데이트
            if "app_info" not in data:
                data["app_info"] = {}
            data["app_info"]["last_updated"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            with open(self.settings_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            return True
        except Exception as e:
            try:
                self.logger.error(f"registration_window geometry 저장 실패: {e}")
            except Exception:
                pass
            return False

    def get_solidworks_settings(self):
        """SolidWorks 관련 설정을 딕셔너리로 반환"""
        return {"program_path": self.program_path, "application_title": self.application_title}

    def check_resolution(self, width):
        """화면 해상도 확인"""
        if width >= 3840:
            return "uhd"
        if width >= 2560:
            return "qhd"
        return "fhd"  # 기본값


# 전역 설정 인스턴스
_config = None


def get_config(reload=False):
    """설정 인스턴스 반환 (싱글톤 패턴)"""
    global _config
    if _config is None or reload:
        _config = Config()
    return _config
