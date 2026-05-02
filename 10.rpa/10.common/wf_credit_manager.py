# -*- coding: utf-8 -*-
"""
WorksFree Simple Credit Management Module
단순화된 크레딧 관리 모듈 - 앱별 독립 관리

🎯 단순한 아키텍처:
1. 앱별 독립 크레딧 관리 (체험판/구매 구분 없이)
2. 각 앱이 자신의 크레딧만 관리
3. 크레딧 타입만 구분 (trial/purchased)
4. 로컬 파일 기반 관리

폴더 구조:
[USERHOME]/.wf_rpa/
├── wf_rpa_config.json (전역 설정 및 사용자 정보)
└── [app_name]/
    ├── policy.json (앱별 신원+정책 병합)
    ├── credit_history.json (앱별 크레딧 사용 이력)
    └── settings.json (앱별 사용자 설정)

"""

import os
import sys
import json
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
import logging

# 중앙 기본값 상수 import
try:
    from wf_googlesheets_manager import DEFAULT_TRIAL_CREDITS, DEFAULT_CREDIT_PER_ITEM
except ImportError:
    # wf_googlesheets_manager가 없는 경우 기본값
    DEFAULT_TRIAL_CREDITS = 10000
    DEFAULT_CREDIT_PER_ITEM = 100

# 모듈 레벨 로거 (부모에서 주입 가능). 기본은 NullHandler로 안전하게 무시
logger: logging.Logger = logging.getLogger("wf_creditmanager_simple")
logger.setLevel(logging.DEBUG)  # DEBUG 레벨 설정
if not logger.handlers:
    # 개발 환경: 콘솔 핸들러 추가
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(
        logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt="%H:%M:%S"
        )
    )
    logger.addHandler(console_handler)


def set_logger(external_logger: logging.Logger):
    """부모에서 로거를 주입하기 위한 훅"""
    global logger
    logger = external_logger


def _get_timestamp() -> str:
    """표준화된 타임스탬프 반환: 2025-10-14T12:15:20.492 (밀리초 3자리)"""
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]


def _normalize_timestamp_value(value: Any) -> Any:
    """임의의 타임스탬프 문자열/객체를 표준 포맷으로 정규화. 실패 시 원본 반환."""
    try:
        if value is None:
            return value
        if isinstance(value, datetime):
            return value.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]
        if isinstance(value, str):
            v = value.strip()
            if not v:
                return value
            # 간단 처리: 끝의 Z 제거, 공백 포함 형식은 T로 교체 시도
            v = v.replace("Z", "")
            v = v.replace(" ", "T") if "T" not in v and " " in v else v
            try:
                dt = datetime.fromisoformat(v)
                return dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]
            except Exception:
                return value
        return value
    except Exception:
        return value


def _normalize_credit_timestamps(data: Dict[str, Any]) -> Dict[str, Any]:
    """크레딧 데이터 내 타임스탬프 필드를 표준 포맷으로 정규화합니다."""
    try:
        if not isinstance(data, dict):
            return data
        for key in ["created_at", "last_updated", "last_synced"]:
            if key in data:
                data[key] = _normalize_timestamp_value(data.get(key))

        # usage_history, purchase_history 항목들 정규화
        if isinstance(data.get("usage_history", None), list):
            for rec in data["usage_history"]:
                if isinstance(rec, dict) and "timestamp" in rec:
                    rec["timestamp"] = _normalize_timestamp_value(rec.get("timestamp"))

        if isinstance(data.get("purchase_history", None), list):
            for rec in data["purchase_history"]:
                if isinstance(rec, dict) and "timestamp" in rec:
                    rec["timestamp"] = _normalize_timestamp_value(rec.get("timestamp"))
    except Exception:
        # 베스트 에포트
        pass
    return data


class WorksFreeManager:
    """
    WorksFree 전역 설정을 관리하는 클래스.
    사용자 등록 정보, 기본 설정 등을 관리합니다.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super(WorksFreeManager, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        # 초기화가 여러 번 실행되는 것을 방지
        if hasattr(self, "_initialized") and self._initialized:
            return

        # 개발/배포 환경 자동 감지
        env_home = os.environ.get("WF_RPA_HOME") or os.environ.get("WF_RPA_DIR")
        dev_flag_env = os.environ.get("WF_RPA_DEV")
        
        # WF_RPA_DEV가 명시적으로 "0"이면 강제 배포 모드
        if dev_flag_env == "0":
            self.is_dev_mode = False
        else:
            # 자동 감지: 실행 파일이 .py로 끝나면 개발 환경
            is_python_script = sys.argv[0].endswith(".py")
            dev_flag_on = dev_flag_env == "1"
            
            # 개발 모드 판단 (환경변수 또는 Python 스크립트 실행)
            # env_home이 설정되어도 .py 실행이면 개발 모드
            self.is_dev_mode = bool(dev_flag_on or is_python_script)

        # 기본 사용자 홈 디렉토리 설정
        self.user_home = Path(env_home).expanduser() if env_home else Path.home()

        # 기본 루트 경로 설정
        if self.is_dev_mode:
            # 개발 모드: 10.common/config 폴더 사용 (공통 설정)
            try:
                app_exec = Path(sys.argv[0]).resolve()
                app_root = app_exec.parent

                # 10.common/config 폴더 찾기 (앱 위치에서 상위로 탐색)
                common_config_dir = None
                search_root = app_root
                for _ in range(5):  # 최대 5단계 상위까지 탐색
                    candidate = search_root / "10.common" / "config"
                    if candidate.exists():
                        common_config_dir = candidate
                        break
                    search_root = search_root.parent

                if common_config_dir:
                    self.wf_rpa_dir = common_config_dir
                    logger.debug(f"[DEV] 개발 환경 - 10.common/config 사용: {self.wf_rpa_dir}")
                else:
                    # 10.common/config를 찾지 못하면 사용자 홈폴더 사용
                    self.wf_rpa_dir = self.user_home / ".wf_rpa"
                    logger.debug(f"[DEV] 10.common/config 없음 - 사용자 홈폴더 사용: {self.wf_rpa_dir}")
            except Exception as e:
                logger.warning(f"DEV 로컬 config 경로 설정 실패 - 기본 경로 사용: {e}")
                # Fallback: 사용자 홈 폴더
                self.wf_rpa_dir = self.user_home / ".wf_rpa"
        else:
            # 배포 모드: 사용자 홈 폴더의 .wf_rpa
            self.wf_rpa_dir = Path(env_home) if env_home else self.user_home / ".wf_rpa"
            if env_home and not self.wf_rpa_dir.is_absolute():
                self.wf_rpa_dir = self.user_home / ".wf_rpa"
            logger.debug(f"[RELEASE] 배포 환경: {self.wf_rpa_dir}")

        # 전역 설정 파일 (환경에 상관없이 동일, 경로만 다름)
        self.config_file = self.wf_rpa_dir / "wf_rpa_config.json"
        # DEPRECATED: 더 이상 전역 정책 파일을 사용하지 않습니다.
        # self.policy_file = self.wf_rpa_dir / 'wf_app_policies.json'

        # 과거 dev_ 접두어 및 숨김 파일 마이그레이션 지원
        try:
            # dev_wf_rpa_config.json -> wf_rpa_config.json
            legacy_dev_cfg = self.wf_rpa_dir / "dev_wf_rpa_config.json"
            if legacy_dev_cfg.exists() and not self.config_file.exists():
                legacy_dev_cfg.rename(self.config_file)

            # .wf_rpa_config.json -> wf_rpa_config.json (숨김 파일 마이그레이션)
            legacy_hidden_cfg = self.wf_rpa_dir / ".wf_rpa_config.json"
            if legacy_hidden_cfg.exists() and not self.config_file.exists():
                legacy_hidden_cfg.rename(self.config_file)
        except Exception:
            pass

        self._ensure_directories()
        self._initialize_config()

        self._initialized = True

    def _ensure_directories(self):
        """필요한 디렉토리를 생성하고, 배포 모드에서는 숨김 처리합니다."""
        try:
            self.wf_rpa_dir.mkdir(exist_ok=True)

            # 배포 모드(비개발 환경)에서만 숨김 처리
            if not self.is_dev_mode:
                self._set_hidden_attribute(self.wf_rpa_dir)
                logger.debug(f"[RELEASE] 폴더 숨김 처리: {self.wf_rpa_dir}")
            else:
                logger.debug(f"[DEV] 개발 모드 - 숨김 처리 생략: {self.wf_rpa_dir}")

        except Exception as e:
            logger.error(f"전역 설정 디렉토리 생성 오류: {e}")

    def _set_hidden_attribute(self, path: Path):
        """Windows에서 파일/폴더를 숨김 처리합니다."""
        try:
            import platform

            if platform.system() == "Windows":
                import ctypes

                FILE_ATTRIBUTE_HIDDEN = 0x02
                # 기존 속성 가져오기
                attrs = ctypes.windll.kernel32.GetFileAttributesW(str(path))
                if attrs != -1:  # 유효한 속성인 경우
                    # 기존 속성에 HIDDEN 추가
                    ctypes.windll.kernel32.SetFileAttributesW(
                        str(path), attrs | FILE_ATTRIBUTE_HIDDEN
                    )
                else:
                    # 파일이 없거나 오류인 경우 HIDDEN만 설정
                    ctypes.windll.kernel32.SetFileAttributesW(str(path), FILE_ATTRIBUTE_HIDDEN)
            # Linux/Mac은 이름이 .으로 시작하면 자동으로 숨김
        except Exception as e:
            logger.warning(f"숨김 처리 실패: {path} - {e}")

    def _remove_hidden_attribute(self, path: Path):
        """Windows에서 파일/폴더의 숨김 속성을 제거합니다."""
        try:
            import platform

            if platform.system() == "Windows":
                import ctypes

                FILE_ATTRIBUTE_HIDDEN = 0x02
                # 기존 속성 가져오기
                attrs = ctypes.windll.kernel32.GetFileAttributesW(str(path))
                if attrs != -1:  # 유효한 속성인 경우
                    # 기존 속성에서 HIDDEN 제거
                    ctypes.windll.kernel32.SetFileAttributesW(
                        str(path), attrs & ~FILE_ATTRIBUTE_HIDDEN
                    )
        except Exception as e:
            logger.warning(f"숨김 해제 실패: {path} - {e}")

    def _initialize_config(self):
        """설정 파일이 없을 경우 기본값으로 초기화합니다."""
        if not self.config_file.exists():
            # ✅ 최초 설치 시 Google Sheets에서 이메일 설정 로드
            email_config = self._load_email_from_sheets_or_default()

            # 최신 기본 스키마 (v2) - 배포판 순서 기준
            # 배포 전 상태: 사용자 등록 정보 비어있음 (reg_time_* 없음)
            # email_settings: 관리자 메일(발신/수신) + 알림 이벤트 + 확장 필드
            default_config = {
                "user_info": {
                    "is_registered": False,  # 등록 여부 플래그
                    "user_email": "",  # 등록 후 채워짐
                    "user_name": "",  # 선택
                    "user_phone": "",  # 선택
                    "user_email_consent": "",  # 등록 시 Y/N
                    "client_hw_fingerprint": "",  # 등록 시 하드웨어 식별자
                    "client_hw_cpuinfo": "",  # CPU 정보
                    "client_hw_mbinfo": "",  # 메인보드 정보
                    "client_hw_storageinfo": "",  # 스토리지 정보
                    "reg_time_local": None,  # 등록 시 로컬 시각 (naive ISO)
                    "reg_time_utc": None,  # 등록 시 UTC 시각
                    "reg_tz_name": None,  # Asia/Seoul 등
                    "last_login": None,  # 앱 실행 후 업데이트
                },
                "execution_status": {
                    "is_running": False,
                    "current_app": None,
                    "pid": None,
                    "start_time": None,
                },
                "google_sheets": {
                    "sheet_id_release": "1bUqpV1vSGwsVeWav-6enZUzaKBTJdxX5eZ737lNh6Ww",
                    "sheet_id_dev": "1bUqpV1vSGwsVeWav-6enZUzaKBTJdxX5eZ737lNh6Ww",
                    "credentials_file_release": "worksfree-b33a6b8f366b.json",
                    "credentials_file_dev": "silver-argon-445712-a0-7092493258f3.json",
                    "scope": [
                        "https://spreadsheets.google.com/feeds",
                        "https://www.googleapis.com/auth/drive",
                    ],
                    "sheet_name_registrations": "registrations",
                },
                "email_settings": email_config,
                "app_settings": {"language": "ko"},  # 다국어 지원
                "system_settings": {
                    "auto_update": True,
                    "send_usage_stats": False,
                    "log_level": "DEBUG",  # 배포 형상 기본값
                },
                "last_updated": _get_timestamp(),
            }
            self.save_config(default_config)

    def _load_email_from_sheets_or_default(self) -> Dict[str, Any]:
        """✅ 최초 설치 시 Google Sheets에서 이메일 설정 로드 (실패 시 하드코딩 기본값 사용)"""
        try:
            logger.info("🔄 최초 설치: Google Sheets에서 이메일 설정 로드 중...")
            from wf_googlesheets_manager import WFGoogleSheetsManager

            gsm = WFGoogleSheetsManager(
                app_name=self.app_name,
                service_name="credit_manager_init",
                version="1.0",
                user_email=self.user_email,
            )

            email_config_raw = gsm.get_email_config()
            if email_config_raw and "email_from" in email_config_raw:
                email_config = {
                    "use_local_email_config": False,
                    "email_from": email_config_raw.get("email_from", "insung.lee1973@gmail.com"),
                    "email_to": email_config_raw.get("email_to", "insung.lee@worksfree.co.kr"),
                    "smtp_server": email_config_raw.get("smtp_server", "smtp.gmail.com"),
                    "smtp_port": int(email_config_raw.get("smtp_port", 587)),
                    "smtp_security": "starttls",
                    "login_key": email_config_raw.get("login_key", "yxvn ebai aori lytb"),
                    "notification_events": {
                        "send_on_completion": True,
                        "send_on_error": True,
                        "send_on_purchase_applied": True,
                        "send_on_expiry_warning": True,
                    },
                    "enabled": email_config_raw.get("enabled", True),
                    "last_loaded_source": "google_sheets",
                    "last_loaded_time": _get_timestamp(),
                }
                logger.info("✅ Google Sheets에서 이메일 설정 로드 성공")
                return email_config
            else:
                raise ValueError("Google Sheets에서 이메일 설정을 찾을 수 없습니다")

        except Exception as e:
            logger.warning(f"⚠️ Google Sheets 로드 실패 (하드코딩 기본값 사용): {e}")
            return self._load_initial_email_config()

    def _load_initial_email_config(self) -> Dict[str, Any]:
        """하드코딩된 기본 이메일 설정 (Google Sheets 로드 실패 시 폴백)"""
        email_config = {
            "use_local_email_config": False,
            "email_from": "insung.lee1973@gmail.com",
            "email_to": "insung.lee@worksfree.co.kr",
            "smtp_server": "smtp.gmail.com",
            "smtp_port": 587,
            "smtp_security": "starttls",
            "login_key": "yxvn ebai aori lytb",
            "notification_events": {
                "send_on_completion": True,
                "send_on_error": True,
                "send_on_purchase_applied": True,
            },
            "enabled": True,
            "last_loaded_source": None,
        }

        logger.info("📧 기본 이메일 설정으로 초기화")
        logger.info("   → 구글 시트 동기화는 '설정 업데이트' 버튼으로 수동 실행")

        return email_config

    def load_config(self) -> Dict[str, Any]:
        """설정 파일을 로드합니다."""
        try:
            if self.config_file.exists():
                with open(self.config_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            else:
                # Legacy 파일명 마이그레이션 지원
                for legacy_name in ["dev_wf_rpa_config.json", ".wf_rpa_config.json"]:
                    legacy_path = self.wf_rpa_dir / legacy_name
                    if legacy_path.exists():
                        try:
                            with open(legacy_path, "r", encoding="utf-8") as f:
                                data = json.load(f)
                            # 새 파일로 마이그레이션
                            self.save_config(data)
                            legacy_path.unlink()  # 구 파일 삭제
                            return data
                        except Exception:
                            pass

                self._initialize_config()
                return self.load_config()
        except Exception as e:
            logger.error(f"설정 파일 로드 오류: {e}")
            return {}

    def save_config(self, data: Dict[str, Any]):
        """설정 파일을 저장합니다."""
        try:
            data["last_updated"] = _get_timestamp()
            # v2 스키마: reg_time_local / reg_time_utc / last_login 정규화 (존재할 때만)
            if isinstance(data.get("user_info", None), dict):
                for ts_key in ["reg_time_local", "reg_time_utc", "last_login"]:
                    if ts_key in data["user_info"]:
                        data["user_info"][ts_key] = _normalize_timestamp_value(
                            data["user_info"][ts_key]
                        )
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"설정 파일 저장 오류: {e}")

    def is_registered(self) -> bool:
        """사용자 등록 여부 확인.
        
        우선순위:
        1. is_registered 값이 True이면 등록됨
        2. is_registered가 False여도 reg_time_local이 있으면 등록된 것으로 간주 (폴백)
        """
        config = self.load_config()
        user_info = config.get("user_info", {})
        
        # 주 플래그 확인
        if user_info.get("is_registered") is True:
            return True
        
        # 폴백: 타임스탐프가 있으면 등록된 것으로 간주
        if user_info.get("reg_time_local"):
            return True
        
        return False

    def register_user(
        self,
        user_email: str,
        hw_fingerprint: str,
        user_name: str = "",
        user_phone: str = "",
        user_email_consent: str = "Y",
    ) -> bool:
        """사용자를 등록하고 wf_rpa_config.json 업데이트 (registrations 시트 구조 매핑)"""
        try:
            # 하드웨어 정보 수집 (wf_hwinfo 모듈 직접 사용)
            try:
                import wf_hwinfo

                hw = wf_hwinfo.HardwareInfo()
                hw_info = {
                    "cpu_info": hw.cpu_id or "",
                    "mainboard_info": hw.mainboard_id or "",
                    "storage_id": hw.storage_id or "",
                    "fingerprint": hw.fingerprint or "",
                }
            except Exception as e:
                logger.warning(f"⚠️ 하드웨어 정보 수집 실패: {e}")
                hw_info = {
                    "cpu_info": "",
                    "mainboard_info": "",
                    "storage_id": "",
                    "fingerprint": "",
                }

            # 타임스탬프 생성 (문자열로 변환)
            from datetime import datetime, timezone
            import pytz

            # 로컬 시간대 (한국)
            tz = pytz.timezone("Asia/Seoul")
            now_local = datetime.now(tz)
            now_utc = datetime.now(timezone.utc)

            # 타임존 이름 먼저 추출 (aware datetime에서)
            tz_name = now_local.tzname()

            # 타임존 정보 제거 (Google Sheets는 naive datetime만 허용)
            reg_time_local_str = now_local.replace(tzinfo=None).isoformat()
            reg_time_utc_str = now_utc.replace(tzinfo=None).isoformat()
            last_login_str = now_local.replace(tzinfo=None).isoformat()

            config = self.load_config()

            # user_info 업데이트 (registrations 시트 컬럼과 매핑)
            user_info = {
                "is_registered": True,
                "user_email": user_email,
                "user_name": user_name,
                "user_phone": user_phone,
                "user_email_consent": user_email_consent,
                "client_hw_fingerprint": hw_fingerprint,
                "client_hw_cpuinfo": hw_info.get("cpu_info", ""),
                "client_hw_mbinfo": hw_info.get("mainboard_info", ""),
                "client_hw_storageinfo": hw_info.get("storage_id", ""),
                "reg_time_local": reg_time_local_str,
                "reg_time_utc": reg_time_utc_str,
                "reg_tz_name": tz_name,
                "last_login": last_login_str,
            }

            config["user_info"] = user_info
            self.save_config(config)

            logger.info(f"✅ 사용자 등록 완료: {user_email}")
            return True

        except Exception as e:
            import traceback

            logger.error(f"❌ 사용자 등록 실패: {e}")
            logger.debug(traceback.format_exc())
            return False

    def get_user_info(self) -> Dict[str, Any]:
        """user_email만 반환 (user_mail은 폐기)"""
        config = self.load_config()
        user_info = config.get("user_info", {})
        # user_mail 키가 있으면 무시
        if "user_mail" in user_info:
            user_info.pop("user_mail")
        return user_info

    def get_email_settings(self) -> Dict[str, Any]:
        """이메일 설정을 반환합니다."""
        config = self.load_config()
        settings = config.get("email_settings", {})
        if not isinstance(settings, dict):
            return {}
        # 환경 변수 오버라이드 (배포용 비밀 주입 지원)
        # WF_EMAIL_FROM / WF_EMAIL_TO / WF_SMTP_SERVER / WF_SMTP_PORT / WF_EMAIL_LOGIN_KEY
        # 레거시 호환: WF_ADMIN_EMAIL_FROM 등도 지원
        env_map = {
            "WF_EMAIL_FROM": ["email_from"],
            "WF_ADMIN_EMAIL_FROM": ["email_from"],  # 레거시 호환
            "WF_EMAIL_TO": ["email_to"],
            "WF_ADMIN_EMAIL_TO": ["email_to"],  # 레거시 호환
            "WF_SMTP_SERVER": ["smtp_server"],
            "WF_ADMIN_SMTP_SERVER": ["smtp_server"],  # 레거시 호환
            "WF_SMTP_PORT": ["smtp_port"],
            "WF_ADMIN_SMTP_PORT": ["smtp_port"],  # 레거시 호환
            "WF_EMAIL_LOGIN_KEY": ["login_key"],
            "WF_ADMIN_EMAIL_LOGIN_KEY": ["login_key"],  # 레거시 호환
        }
        import os

        overridden = False
        for env_key, target_keys in env_map.items():
            val = os.environ.get(env_key)
            if val:
                for tk in target_keys:
                    if tk == "smtp_port":
                        try:
                            settings[tk] = int(val)
                        except ValueError:
                            settings[tk] = val
                    else:
                        settings[tk] = val.strip()
                overridden = True
                break  # 첫 번째 매칭되는 환경변수 사용 (WF_EMAIL_FROM 우선, 없으면 WF_ADMIN_EMAIL_FROM)
        return settings

    def save_email_settings(self, settings: Dict[str, Any]):
        """이메일 설정을 저장합니다."""
        config = self.load_config()
        config["email_settings"] = settings
        self.save_config(config)

    def load_policies(self) -> Dict[str, Any]:
        """[Deprecated] 전역 정책 파일 로드는 더 이상 제공하지 않습니다.
        호환성 유지를 위해 빈 dict를 반환합니다.
        """
        logger.debug(
            "load_policies() is deprecated and returns {}. Use per-app credit_policy.json instead."
        )
        return {}

    def save_policies(self, policies: Dict[str, Any], source: str = "manual") -> bool:
        """[Deprecated] 전역 정책 저장은 더 이상 사용하지 않습니다. 항상 True 반환."""
        logger.debug(
            "save_policies() is deprecated. Skipping write of legacy wf_app_policies.json."
        )
        return True

    def _normalize_app_name(self, app_name: str) -> str:
        """앱 이름을 표준 형식으로 정규화"""
        # 별칭 매핑 테이블에서 확인
        alias_mapping = {
            "Bom2Excel": "bom_exporter",
            "Bom2Excel_Exporter": "bom_exporter",
            "file_list_check": "conversion_verifier",  # 구 이름 → 신 이름
            "Conversion_Verifier": "conversion_verifier",
            "DWG_Classifier": "dwg_classifier",
            "Korean_FileName_Normalizer": "korean_filename_normalizer",
            "DWG_Batch_Print": "DWG_Batch_Print",  # 이미 표준 이름
            "Drawing_Attribute_Reset": "Drawing_Attribute_Reset",  # 이미 표준 이름
        }

        # 별칭이 있으면 표준 이름으로 변환
        return alias_mapping.get(app_name, app_name)

    def _merge_policies_safely(
        self, local_policies: Dict[str, Any], remote_policies: Dict[str, Any]
    ) -> Dict[str, Any]:
        """정책을 안전하게 병합하고 중복 키를 제거"""
        # 결과 딕셔너리
        merged = {}

        # 1. 로컬 정책을 먼저 표준화된 키로 복사
        for app_name, policy in local_policies.items():
            normalized_name = self._normalize_app_name(app_name)
            if normalized_name not in merged:
                merged[normalized_name] = policy.copy()

        # 2. 원격 정책을 병합 (기존 키와 중복되면 업데이트)
        for app_name, policy in remote_policies.items():
            normalized_name = self._normalize_app_name(app_name)

            if normalized_name in merged:
                # 기존 정책과 병합 (원격 정책이 우선)
                merged_policy = merged[normalized_name].copy()
                merged_policy.update(policy)
                merged[normalized_name] = merged_policy
            else:
                # 새로운 정책 추가
                merged[normalized_name] = policy.copy()

        logger.debug(f"정책 병합 완료: {len(merged)}개의 고유한 앱 정책")
        return merged


class CreditManager:
    def refresh_policies_from_sheets(self) -> Dict[str, Any]:
        """Google Sheets로부터 정책을 동기화합니다.
        동기화 결과는 전역 파일이 아니라 각 앱의 `~/.wf_rpa/{app}/policy.json`에 반영됩니다.

        개발 모드: 현재 앱의 정책만 config 폴더에 저장 (다른 앱 폴더 생성하지 않음)
        배포 모드: 현재 앱의 정책만 사용자 홈의 .wf_rpa/{app} 폴더에 저장
        """
        try:
            from wf_googlesheets_manager import get_sheets_manager

            sheets_manager = get_sheets_manager(test_mode=True)

            remote_policies = sheets_manager.get_app_policies()
            if remote_policies is None:
                return {
                    "success": False,
                    "error": "fetch_failed",
                    "message": "Google Sheets에서 정책을 가져오는데 실패했습니다.",
                }
            if not remote_policies:
                return {
                    "success": False,
                    "error": "empty_policies",
                    "message": "Google Sheets에 정책 데이터가 없습니다.",
                }

            # 현재 앱 이름 감지
            current_app_policy_name = None
            try:
                app_exec = Path(sys.argv[0]).resolve()
                current_app_folder = app_exec.parent.name

                # 앱 이름 매핑 (폴더명 → 정책 키)
                folder_to_policy = {
                    "bom2excel": "bom_exporter",
                    "bom_exporter": "bom_exporter",
                    "conversion_verifier": "conversion_verifier",
                    "dwg_classifier": "dwg_classifier",
                    "korean_filename_normalizer": "korean_filename_normalizer",
                    "dwg_batch_print": "DWG_Batch_Print",
                    "drawing_attribute_reset": "Drawing_Attribute_Reset",
                }

                current_app_policy_name = folder_to_policy.get(
                    current_app_folder, current_app_folder
                )
                logger.debug(
                    f"현재 앱 감지: {current_app_policy_name} (폴더: {current_app_folder})"
                )
            except Exception as e:
                logger.warning(f"현재 앱 감지 실패: {e}")

            updated = 0
            for app_name, policy in remote_policies.items():
                try:
                    # 현재 앱의 정책만 저장 (개발/배포 모드 공통)
                    if current_app_policy_name and app_name != current_app_policy_name:
                        # 다른 앱 정책 건너뛰기 (로그 제거로 출력 정리)
                        continue

                    # 앱 폴더 및 파일 경로
                    app_dir = self.wf_rpa_dir / app_name
                    policy_file = app_dir / "policy.json"
                    app_dir.mkdir(parents=True, exist_ok=True)

                    # 기존 정책 로드 후 병합
                    existing_policy: Dict[str, Any] = {}
                    if policy_file.exists():
                        try:
                            with open(policy_file, "r", encoding="utf-8") as f:
                                existing = json.load(f)
                                if isinstance(existing, dict):
                                    # 병합 구조(policy 키)에서 정책만 추출
                                    existing_policy = existing.get("policy", {}) if isinstance(existing.get("policy"), dict) else {}
                        except Exception:
                            existing_policy = {}

                    merged = existing_policy.copy()
                    if isinstance(policy, dict):
                        merged.update(policy)

                    # 파일이 이미 존재하고 숨김 처리되어 있다면 임시로 숨김 해제
                    if not self.wf_manager.is_dev_mode and policy_file.exists():
                        self._remove_hidden_attribute(policy_file)

                    # 저장
                    payload = {
                        "identity": {"app_name": app_name},
                        "policy": merged,
                    }
                    with open(policy_file, "w", encoding="utf-8") as f:
                        json.dump(payload, f, ensure_ascii=False, indent=2)

                    if not self.wf_manager.is_dev_mode:
                        self._set_hidden_attribute(policy_file)

                    updated += 1
                except Exception as e:
                    logger.warning(f"⚠️ {app_name} 정책 저장 실패: {e}")

            logger.info(
                f"✅ Google Sheets에서 {updated}개의 앱 정책을 동기화했습니다. (전역 파일 미사용)"
            )

            # 이메일 설정도 함께 동기화
            email_sync_result = self.refresh_email_settings_from_sheets()
            result: Dict[str, Any] = {
                "success": True,
                "message": f"{updated}개의 앱 정책이 동기화되었습니다.",
                "count": updated,
            }
            result["email_refreshed"] = bool(email_sync_result.get("success"))
            if not result["email_refreshed"]:
                result["email_error"] = email_sync_result.get("message")
            return result

        except ImportError as e:
            return {
                "success": False,
                "error": "import_error",
                "message": f"Google Sheets 모듈을 사용할 수 없습니다: {e}",
            }
        except Exception as e:
            logger.error(f"정책 동기화 오류: {e}")
            return {"success": False, "error": "sync_error", "message": f"정책 동기화 중 오류: {e}"}

    def refresh_email_settings_from_sheets(self) -> Dict[str, Any]:
        """Google Sheets의 admin_config에서 이메일 설정을 동기화하여 로컬 설정 파일에 저장합니다.
        개발 환경: 앱 폴더의 config/wf_rpa_config.json
        배포 환경: 사용자 홈 폴더의 .wf_rpa/wf_rpa_config.json
        """
        try:
            from wf_googlesheets_manager import get_sheets_manager

            sheets_manager = get_sheets_manager(test_mode=True)
            email_config = sheets_manager.get_email_config()
            if not email_config:
                return {"success": False, "message": "이메일 설정을 시트에서 가져오지 못했습니다."}

            # WorksFreeManager를 통해 설정 로드
            if not hasattr(self, "wf_manager"):
                return {"success": False, "message": "WorksFreeManager 인스턴스가 없습니다."}

            config = self.wf_manager.load_config()
            es = (
                config.get("email_settings", {})
                if isinstance(config.get("email_settings"), dict)
                else {}
            )

            # 시트 키 → 로컬 설정 매핑
            # email_login → login_key로 매핑, smtp_port는 정수화 시도
            def _coerce_port(v):
                try:
                    return int(v)
                except Exception:
                    return v

            mapping = {
                "email_from": "email_from",
                "email_to": "email_to",
                "email_login": "login_key",
                "smtp_server": "smtp_server",
                "smtp_port": "smtp_port",
            }

            for k_sheet, k_local in mapping.items():
                if k_sheet in email_config and str(email_config[k_sheet]).strip():
                    if k_local == "smtp_port":
                        es[k_local] = _coerce_port(email_config[k_sheet])
                    else:
                        es[k_local] = str(email_config[k_sheet]).strip()

            # 플래그/메타 업데이트
            es["use_local_email_config"] = True
            es["enabled"] = True
            config["email_settings"] = es

            self.wf_manager.save_config(config)
            logger.info("✅ 이메일 설정 동기화 완료 (Sheets → 로컬)")
            logger.debug(
                f"   email_from={es.get('email_from')} smtp={es.get('smtp_server')}:{es.get('smtp_port')}"
            )

            return {"success": True, "message": "이메일 설정 동기화 완료"}

        except Exception as e:
            logger.warning(f"⚠️ 이메일 설정 동기화 실패: {e}")
            return {"success": False, "message": f"이메일 설정 동기화 실패: {e}"}

    def pull_and_apply_purchases(self) -> Dict[str, Any]:
        """구글 시트에서 새로운 구매 이력을 가져와서 로컬 크레딧에 반영 (idempotent)"""
        with self.lock:
            data = self._load_credit_data()
            user_info = self.wf_manager.get_user_info() if hasattr(self, "wf_manager") else {}
            user_email = user_info.get("user_email") or user_info.get("email")
            app_name = self.app_name
            if not user_email:
                return {
                    "success": False,
                    "error": "no_user_email",
                    "message": "사용자 이메일이 없습니다.",
                }
            try:
                from wf_googlesheets_manager import get_sheets_manager

                sheets_manager = get_sheets_manager(test_mode=True)
                purchase_records = sheets_manager.get_purchase_records(user_email, app_name)
            except Exception as e:
                return {
                    "success": False,
                    "error": "sheets_error",
                    "message": f"구매 이력 조회 실패: {e}",
                }

            applied_ids = set(data.get("applied_purchase_ids", []))
            purchase_history = data.get("purchase_history", [])
            new_applied = []
            total_added = 0
            for rec in purchase_records:
                tid = str(rec.get("transaction_id", "")).strip()
                if not tid:
                    continue

                # Google Sheets에서 applied_date가 없는 건만 가져오므로 추가 검증 불필요
                # 하지만 로컬 중복 방지를 위해 applied_ids도 확인
                if tid in applied_ids:
                    continue

                # 크레딧 금액 계산 (확장 구조)
                try:
                    amt = 0
                    # 우선순위 1: total_credit (명시적 총합)
                    if "total_credit" in rec and rec["total_credit"]:
                        total_val = rec["total_credit"]
                        # 빈 문자열 체크
                        if isinstance(total_val, str) and total_val.strip():
                            amt = int(total_val)
                        elif isinstance(total_val, (int, float)):
                            amt = int(total_val)

                    # 우선순위 2: purchased_credit + bonus_credit (분리된 구조)
                    if not amt and "purchased_credit" in rec and rec["purchased_credit"]:
                        purchased_val = rec["purchased_credit"]
                        bonus_val = rec.get("bonus_credit", 0)

                        # purchased_credit 변환
                        if isinstance(purchased_val, str) and purchased_val.strip():
                            purchased_credit = int(purchased_val)
                        elif isinstance(purchased_val, (int, float)):
                            purchased_credit = int(purchased_val)
                        else:
                            purchased_credit = 0

                        # bonus_credit 변환 (빈 문자열 처리)
                        if isinstance(bonus_val, str) and bonus_val.strip():
                            bonus_credit = int(bonus_val)
                        elif isinstance(bonus_val, (int, float)):
                            bonus_credit = int(bonus_val)
                        else:
                            bonus_credit = 0

                        amt = purchased_credit + bonus_credit

                except (ValueError, TypeError) as e:
                    logger.error(f"❌ 크레딧 변환 오류: {e}, rec={rec}")
                    amt = 0

                if not amt:
                    continue
                
                # Apply: -1은 영구 라이선스로 처리
                if amt == -1:
                    # 영구 라이선스: remaining_purchased를 -1로 설정
                    data["remaining_purchased"] = -1
                    logger.info(f"✨ 영구 라이선스 적용: {tid}")
                else:
                    # 일반 크레딧: 기존 remaining_purchased에 더하기
                    current_purchased = data.get("remaining_purchased", 0)
                    # 이미 영구 라이선스(-1)인 경우 유지
                    if current_purchased != -1:
                        data["remaining_purchased"] = current_purchased + amt

                # 상세 구매 정보 저장 (확장 구조)
                purchase_detail = {
                    "transaction_id": tid,
                    "amount": amt,
                    "purchase_date": rec.get("purchase_date", "") or tid,  # 없으면 tid 사용
                    "channel": rec.get("channel", ""),
                    "payment_method": rec.get("payment_method", ""),
                    "price": rec.get("price", ""),
                    "status": rec.get("status", "paid"),
                    "applied_date": _get_timestamp(),  # 로컬 적용 시각
                }

                # 크레딧 세부 정보 (purchased_credit + bonus_credit 구조) - 안전한 변환
                try:
                    if "purchased_credit" in rec and rec["purchased_credit"]:
                        val = rec["purchased_credit"]
                        if isinstance(val, str) and val.strip():
                            purchase_detail["purchased_credit"] = int(val)
                        elif isinstance(val, (int, float)):
                            purchase_detail["purchased_credit"] = int(val)
                except (ValueError, TypeError):
                    pass

                try:
                    if "bonus_credit" in rec and rec["bonus_credit"]:
                        val = rec["bonus_credit"]
                        if isinstance(val, str) and val.strip():
                            purchase_detail["bonus_credit"] = int(val)
                        elif isinstance(val, (int, float)):
                            purchase_detail["bonus_credit"] = int(val)
                except (ValueError, TypeError):
                    pass

                try:
                    if "total_credit" in rec and rec["total_credit"]:
                        val = rec["total_credit"]
                        if isinstance(val, str) and val.strip():
                            purchase_detail["total_credit"] = int(val)
                        elif isinstance(val, (int, float)):
                            purchase_detail["total_credit"] = int(val)
                except (ValueError, TypeError):
                    pass

                # 프로모션 정보
                if "promo_code" in rec and rec["promo_code"]:
                    purchase_detail["promo_code"] = rec["promo_code"]
                if "discount_rate" in rec and rec["discount_rate"]:
                    purchase_detail["discount_rate"] = rec["discount_rate"]

                purchase_history.append(purchase_detail)
                applied_ids.add(tid)
                new_applied.append(tid)
                total_added += amt
            if new_applied:
                data["applied_purchase_ids"] = list(applied_ids)
                data["purchase_history"] = purchase_history
                data["credit_changed"] = True

                # current_credits 자동 계산 (remaining_trial + remaining_purchased)
                remaining_trial = data.get("remaining_trial", 0)
                remaining_purchased = data.get("remaining_purchased", 0)

                # -1은 무제한을 의미
                if remaining_trial == -1 or remaining_purchased == -1:
                    data["current_credits"] = -1
                else:
                    data["current_credits"] = remaining_trial + remaining_purchased

                # 마지막 동기화 시각 업데이트
                data["last_synced"] = _get_timestamp()
                data["last_updated"] = _get_timestamp()

                self._save_credit_data(data)

                # Google Sheets의 구매 기록 상태를 'applied'로 업데이트 시도
                try:
                    self._update_purchase_status(sheets_manager, new_applied, "applied")
                except Exception as e:
                    # 상태 업데이트 실패해도 크레딧 적용은 성공으로 처리
                    logger.warning(f"⚠️ 구글 시트 applied_date 업데이트 실패: {e}")
                    pass

                logger.info(
                    f"✅ {len(new_applied)}건 구매 이력 반영 완료 (총 +{total_added} 크레딧, 현재 잔액: {data['current_credits']})"
                )
                return {
                    "success": True,
                    "added": total_added,
                    "applied_ids": new_applied,
                    "message": f"{len(new_applied)}건의 구매 이력을 반영했습니다. (총 {total_added} 크레딧 추가)",
                }
            else:
                logger.info(f"ℹ️ 신규 구매 이력 없음 ({user_email}/{app_name})")
                return {
                    "success": True,
                    "added": 0,
                    "applied_ids": [],
                    "message": "신규 구매 이력이 없습니다.",
                }

    def _update_purchase_status(self, sheets_manager, transaction_ids: list, status: str):
        """Google Sheets의 구매 기록에 applied_date를 업데이트"""
        try:
            from datetime import datetime, timezone

            # 현재 시간을 applied_date로 사용
            current_time = datetime.now().astimezone().isoformat(timespec="milliseconds")

            # Google Sheets에서 해당 transaction_id 행을 찾아서 applied_date 업데이트
            config = sheets_manager._load_config()
            sheet_id = config["SHEET_ID_DEV"]
            purchase_ws = sheets_manager.gc.open_by_key(sheet_id).worksheet("credit_purchase_log")

            # 헤더 정보 가져오기
            headers = purchase_ws.row_values(1)
            # 빈 문자열 제거한 실제 헤더
            actual_headers = [h for h in headers if h.strip()]

            applied_date_col = None
            transaction_id_col = None

            for i, header in enumerate(headers, 1):
                if header == "applied_date":
                    applied_date_col = i
                elif header == "transaction_id":
                    transaction_id_col = i

            if not applied_date_col:
                logger.warning("⚠️ applied_date 컬럼을 찾을 수 없습니다.")
                return

            # 모든 레코드 가져오기 (헤더 명시)
            try:
                all_records = purchase_ws.get_all_records(expected_headers=actual_headers)
            except Exception as e:
                logger.error(f"❌ get_all_records 실패 (applied_date 업데이트): {e}")
                return

            # 각 transaction_id에 대해 applied_date 업데이트
            updated_count = 0
            for row_num, record in enumerate(all_records, 2):  # 2부터 시작 (헤더 제외)
                record_id = str(record.get("transaction_id", "")).strip()
                if record_id in transaction_ids:
                    # 해당 행의 applied_date 컬럼 업데이트
                    purchase_ws.update_cell(row_num, applied_date_col, current_time)
                    updated_count += 1
                    logger.debug(f"✅ applied_date 업데이트: {record_id} → {current_time}")

            if updated_count > 0:
                logger.info(f"✅ {updated_count}건의 applied_date 업데이트 완료")

        except Exception as e:
            # 에러가 발생해도 크레딧 적용에는 영향 없도록 처리
            logger.warning(f"⚠️ applied_date 업데이트 실패: {e}")
            import traceback

            logger.debug(traceback.format_exc())
            pass

    """단순화된 크레딧 매니저 - 앱별 독립 관리"""

    def __init__(self, app_name: str, user_email: Optional[str] = None):
        self.app_name = app_name
        self.user_email = user_email
        self.lock = threading.RLock()

        # 환경이 바뀌었으면 WorksFreeManager를 새로 생성해 WF_RPA_HOME 변경을 반영
        current_env_home = os.environ.get("WF_RPA_HOME") or os.environ.get("WF_RPA_DIR")
        existing_manager = getattr(WorksFreeManager, "_instance", None)
        if existing_manager and current_env_home:
            try:
                existing_home = Path(existing_manager.wf_rpa_dir).resolve()
                desired_home = Path(current_env_home).expanduser().resolve()
                if existing_home != desired_home:
                    WorksFreeManager._instance = None
            except Exception:
                WorksFreeManager._instance = None

        # 전역 매니저 인스턴스
        self.wf_manager = WorksFreeManager()

        # 앱 이름 정규화 (JSON에서 canonical name 찾기)
        canonical_name, identity_data = self._resolve_canonical_name(app_name)
        self.app_name = canonical_name  # 정규화된 이름 저장
        self.short_name = identity_data.get("short_name", canonical_name.lower())
        self.display_name = identity_data.get("display_name", canonical_name)

        # 사용자 홈/앱 디렉토리 경로를 먼저 설정 (로컬 정책 로드에서 필요)
        self.user_home = self.wf_manager.user_home
        self.wf_rpa_dir = self.wf_manager.wf_rpa_dir
        self.app_dir = self.wf_rpa_dir / canonical_name

        # 앱별 정책 로드 (우선순위: 로컬 정책 > 번들 정책)
        # 1) 번들 정책 JSON 로드 (config/<app>/policy.json)
        base_policy = self._load_bundled_policy(canonical_name)
        
        if not base_policy:
            # 번들 정책이 없으면 최소 기본값 (앱 추가 시 JSON 필수)
            logger.warning(f"⚠️ {canonical_name}: 번들 정책 JSON이 없습니다. 기본값 사용")
            logger.error(f"❌ CRITICAL: 번들 정책 로드 실패 - trial_credits가 0으로 설정됩니다!")
            base_policy = {
                "description": f"{canonical_name} - 정책 미설정",
                "trial_credits": 0,
                "credit_per_work": 1,
                "credit_type": "per_item",
            }
        else:
            logger.info(f"✅ 번들 정책 로드 성공: trial_credits={base_policy.get('trial_credits')}, credit_per_work={base_policy.get('credit_per_work')}")

        # 2) 로컬 앱별 정책 로드 (Sheets에서 동기화된 정책, 있으면 덮어쓰기)
        local_policy = self._load_app_policy_file(canonical_name)
        if local_policy:
            logger.info(f"✅ 로컬 정책 발견 - 번들 정책 위에 덮어쓰기")
            base_policy = {**base_policy, **local_policy}

        self.policy = base_policy

        # 디버그: 정책 로드 확인
        if isinstance(base_policy, dict):
            logger.info(
                f"🔧 CreditManager 정책 로드 완료: app={canonical_name} (short={self.short_name}), trial_credits={base_policy.get('trial_credits')}, credit_per_work={base_policy.get('credit_per_work', 'N/A')}"
            )
        else:
            logger.error(f"❌ 정책이 딕셔너리가 아닙니다: {type(base_policy)} = {base_policy}")

        # 크레딧 파일 경로 (앱별 단일 파일) - 새 명명 규칙
        self.credit_file = self.app_dir / "credit_history.json"

        # 정책 파일 경로 (앱별 정책 파일) - 새 명명 규칙 (병합)
        self.policy_file = self.app_dir / "policy.json"

        # 디렉토리 생성
        self._ensure_directories()

        # 정책 파일 초기화/업데이트
        self._update_policy_file()

        # 크레딧 초기화 (파일이 없거나 포맷이 다른 경우)
        self._initialize_credits()

        # 🔄 앱 시작 시: credit_changed=True이면 구글 시트 동기화
        self._sync_on_startup()

    def _resolve_canonical_name(self, input_name: str) -> tuple[str, Dict[str, Any]]:
        """입력된 앱 이름(별칭 포함)을 정규 이름으로 변환
        
        Returns:
            (canonical_name, identity_data): 정규 이름과 identity 정보
        """
        # 1. 먼저 입력 이름으로 직접 찾기
        bundled = self._load_bundled_policy_full(input_name)
        if bundled and "identity" in bundled:
            identity = bundled["identity"]
            canonical = identity.get("app_name", input_name)
            return canonical, identity
        
        # 2. 가능한 모든 앱의 JSON을 검색하여 aliases 매칭
        possible_apps = ["dwg_classifier", "conversion_verifier", "korean_filename_normalizer", "bom_exporter"]
        for app in possible_apps:
            bundled = self._load_bundled_policy_full(app)
            if bundled and "identity" in bundled:
                identity = bundled["identity"]
                # aliases 배열에서 매칭 확인
                aliases = identity.get("aliases", [])
                if input_name in aliases or input_name == identity.get("app_name"):
                    canonical = identity.get("app_name", app)
                    logger.debug(f"✅ 별칭 '{input_name}' → 정규 이름 '{canonical}'")
                    return canonical, identity
        
        # 3. 찾지 못하면 입력 이름 그대로 사용
        logger.warning(f"⚠️ '{input_name}': 번들 JSON을 찾지 못했습니다. 입력 이름 사용")
        return input_name, {"app_name": input_name, "short_name": input_name.lower()}

    def _load_bundled_policy_full(self, app_name: str) -> Optional[Dict[str, Any]]:
        """번들된 정책 파일 전체 로드 (identity + policy 포함)"""
        try:
            # 개발 모드: 앱 폴더의 config 디렉토리 탐색
            if self.wf_manager.is_dev_mode:
                app_exec = Path(sys.argv[0]).resolve()
                app_root = app_exec.parent

                # 개발 모드 경로 우선순위:
                # 1. 앱 폴더/config/{app_name}/policy.json
                # 2. 10.common/config/{app_name}/policy.json (fallback)
                # app_root에서 상위로 올라가서 10.common 찾기
                common_config = app_root.parent.parent / "10.common" / "config" / app_name / "policy.json"
                dev_candidate_paths = [
                    app_root / "config" / app_name / "policy.json",
                    common_config,
                ]

                for bundled_file in dev_candidate_paths:
                    logger.debug(f"[DEV] 번들 정책 경로 확인: {bundled_file}")
                    if bundled_file.exists():
                        logger.debug(f"✅ 번들 정책 파일 존재: {bundled_file}")
                        with open(bundled_file, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            if isinstance(data, dict):
                                logger.debug(f"✅ 번들 정책 파싱 성공: {app_name}")
                                return data
                            else:
                                logger.error(f"❌ 번들 정책이 딕셔너리가 아님: {type(data)}")

                logger.debug(f"[DEV] 번들 정책 파일 없음 (시도한 경로: {dev_candidate_paths})")
            else:
                # 배포 모드: _MEIPASS (PyInstaller 임시 폴더) 또는 실행 파일 옆
                if hasattr(sys, '_MEIPASS'):
                    base_path = Path(sys._MEIPASS)
                    logger.debug(f"[RELEASE] _MEIPASS 경로 사용: {base_path}")
                else:
                    base_path = Path(sys.executable).parent
                    logger.debug(f"[RELEASE] 실행 파일 경로 사용: {base_path}")

                # 배포 모드 경로 우선순위: .wf_rpa/ > config/
                candidate_paths = [
                    base_path / ".wf_rpa" / app_name / "policy.json",
                    base_path / "config" / app_name / "policy.json",
                ]

                for bundled_file in candidate_paths:
                    logger.debug(f"[RELEASE] 번들 정책 경로 확인: {bundled_file}")
                    if bundled_file.exists():
                        logger.info(f"✅ 번들 정책 파일 존재: {bundled_file}")
                        with open(bundled_file, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            if isinstance(data, dict):
                                logger.info(f"✅ 번들 정책 파싱 성공: {app_name}")
                                return data
                            else:
                                logger.error(f"❌ 번들 정책이 딕셔너리가 아님: {type(data)}")

                logger.error(f"❌ 번들 정책 파일 없음 (시도한 경로: {candidate_paths})")
        except Exception as e:
            logger.error(f"❌ 번들 정책 전체 로드 실패 ({app_name}): {e}", exc_info=True)
        return None

    def _load_bundled_policy(self, app_name: str) -> Optional[Dict[str, Any]]:
        """번들된 정책만 로드 (policy 섹션만 반환)"""
        data = self._load_bundled_policy_full(app_name)
        if data:
            policy = data.get("policy", {})
            if policy:
                logger.debug(f"✅ 번들 정책 로드: {app_name}")
                return policy
        return None

    def _load_app_policy_file(self, app_name: str) -> Optional[Dict[str, Any]]:
        """앱별 로컬 정책 파일 로드 (~/.wf_rpa/{app_name}/policy.json)"""
        try:
            app_dir = self.wf_rpa_dir / app_name
            policy_file = app_dir / "policy.json"
            if policy_file.exists():
                with open(policy_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("policy", {}) if isinstance(data, dict) else {}
        except Exception as e:
            logger.debug(f"앱별 정책 파일 로드 실패 ({app_name}): {e}")
        return None

    def _reload_policy(self) -> bool:
        """정책 재로드 (테스트/업데이트용)"""
        try:
            # 1) 번들 정책 재로드
            base_policy = self._load_bundled_policy(self.app_name)
            
            if not base_policy:
                logger.warning(f"⚠️ {self.app_name}: 번들 정책 재로드 실패. 기존 정책 유지")
                return False
            
            # 2) 로컬 정책 재로드
            local_policy = self._load_app_policy_file(self.app_name)
            if local_policy:
                logger.info(f"✅ 로컬 정책 발견 - 번들 정책 위에 덮어쓰기")
                base_policy = {**base_policy, **local_policy}
            
            # 3) self.policy 업데이트
            self.policy = base_policy
            logger.info(f"✅ 정책 재로드 완료: trial_credits={base_policy.get('trial_credits')}, credit_per_work={base_policy.get('credit_per_work')}")
            return True
        except Exception as e:
            logger.error(f"❌ 정책 재로드 실패: {e}")
            return False

    def _sync_on_startup(self):
        """앱 시작 시: credit_changed=True이면 구글 시트와 동기화 시도"""
        try:
            # 정책/이메일 동기화는 무료 앱 포함 항상 시도
            try:
                policy_result = self.refresh_policies_from_sheets()
                if policy_result.get("success"):
                    logger.info("✅ 정책 동기화 완료 (startup)")
                else:
                    logger.warning(f"⚠️ 정책 동기화 실패: {policy_result.get('message')}")
            except Exception as e:
                logger.warning(f"⚠️ 정책 동기화 중 오류 (startup): {e}")

            data = self._load_credit_data()

            # credit_changed가 False이면 동기화 불필요
            if not data.get("credit_changed", False):
                logger.debug("🔄 앱 시작: credit_changed=False, 동기화 생략")
                return

            logger.info("🔄 앱 시작: credit_changed=True 감지, 구글 시트 동기화 시도...")

            # 동기화 시도
            result = self.check_and_sync_credits()

            if result.get("success") and result.get("synced"):
                logger.info(f"✅ 시작 시 동기화 성공: {result.get('message', '')}")
            elif result.get("success") and not result.get("synced"):
                logger.debug(f"ℹ️ 동기화 불필요: {result.get('message', '')}")
            else:
                logger.warning(f"⚠️ 시작 시 동기화 실패: {result.get('message', 'Unknown error')}")

        except Exception as e:
            # 동기화 실패는 앱 시작을 막지 않음 (경고만 표시)
            logger.warning(f"⚠️ 시작 시 동기화 중 오류 (무시하고 진행): {e}")

    def _ensure_directories(self):
        """필요한 디렉토리들을 생성하고, 배포 모드에서는 숨김 처리합니다."""
        try:
            self.wf_rpa_dir.mkdir(exist_ok=True)
            self.app_dir.mkdir(exist_ok=True)

            # 배포 모드에서만 앱 폴더 숨김 처리
            if not self.wf_manager.is_dev_mode:
                self.wf_manager._set_hidden_attribute(self.app_dir)
                logger.debug(f"[RELEASE] 앱 폴더 숨김 처리: {self.app_dir}")
            else:
                logger.debug(f"[DEV] 개발 모드 - 앱 폴더 숨김 생략: {self.app_dir}")

        except Exception as e:
            logger.error(f"디렉토리 생성 오류: {e}")

    def _initialize_credits(self):
        """크레딧 파일이 없을 경우 체험판으로 초기화합니다.

        새 구조: policy.json에서 정책을 읽고, credit_history.json은 잔액만 저장
        - remaining_trial: 남은 체험판 크레딧
        - remaining_purchased: 남은 구매 크레딧
        """
        if not self.credit_file.exists():
            now = _get_timestamp()
            trial_amount = self.policy.get("trial_credits", DEFAULT_TRIAL_CREDITS)

            initial_data = {
                "remaining_trial": trial_amount,
                "remaining_purchased": 0,
                "credit_changed": False,
                "created_at": now,
                "last_updated": now,
                "purchase_history": [],
                "usage_history": [],
            }
            
            self._save_credit_data(initial_data)
            logger.info(f"✅ 크레딧 초기화: remaining_trial={trial_amount}")

    def _migrate_old_format(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """이전 크레딧 포맷을 새 포맷(remaining_trial/remaining_purchased)으로 변환합니다.

        마이그레이션 케이스:
        1. remaining_credits 형식 (아주 오래된 형식)
        2. trial_credits/purchased_credits + app_policy 형식 (이전 형식)
        3. remaining_trial/remaining_purchased 형식 (현재 형식) - 변환 불필요
        """
        migrated = False

        # 케이스 1: 아주 오래된 remaining_credits 형식
        if "remaining_credits" in data:
            logger.info("⏫ 마이그레이션: remaining_credits → remaining_trial/remaining_purchased")
            credit_type = data.get("credit_type", "trial")
            remaining = data.get("remaining_credits", 0)

            if credit_type == "trial":
                data["remaining_trial"] = remaining
                data["remaining_purchased"] = 0
            elif credit_type == "purchased":
                data["remaining_trial"] = 0
                data["remaining_purchased"] = remaining
            else:
                data["remaining_trial"] = remaining
                data["remaining_purchased"] = 0

            # 이전 필드 제거
            data.pop("remaining_credits", None)
            data.pop("credit_type", None)
            migrated = True

        # 케이스 2: trial_credits/purchased_credits 형식 (app_policy 포함)
        if "trial_credits" in data and "remaining_trial" not in data:
            logger.info("⏫ 마이그레이션: trial_credits → remaining_trial")
            data["remaining_trial"] = data.pop("trial_credits")
            data["remaining_purchased"] = data.pop("purchased_credits", 0)

            # app_policy 제거 (더 이상 사용하지 않음)
            if "app_policy" in data:
                data.pop("app_policy")
                logger.debug("  - app_policy 필드 제거됨 (policy.json으로 이관)")

            migrated = True

        # 마이그레이션이 발생했으면 저장
        if migrated:
            data["credit_changed"] = data.get("credit_changed", False)
            data["created_at"] = data.get("created_at", _get_timestamp())
            data["last_updated"] = _get_timestamp()
            data["usage_history"] = data.get("usage_history", [])
            data["purchase_history"] = data.get("purchase_history", [])
            self._save_credit_data(data)
            logger.info(f"✅ 마이그레이션 완료: remaining_trial={data.get('remaining_trial')}, remaining_purchased={data.get('remaining_purchased')}")

        return data

    def _load_credit_data(self) -> Dict[str, Any]:
        """크레딧 데이터를 로드하고, 필요시 마이그레이션합니다.

        새 구조에서는 policy.json에서 정책을 읽고, credit_history.json은 잔액만 저장합니다.
        - remaining_trial: 남은 체험판 크레딧
        - remaining_purchased: 남은 구매 크레딧
        """
        try:
            if self.credit_file.exists():
                with open(self.credit_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # 기존 포맷 마이그레이션
                data = self._migrate_old_format(data)

                # 정책 동기화: policy.json 기반으로 체험판 크레딧 초기화
                try:
                    policy_trial = self.policy.get("trial_credits", 0)
                    current_trial = data.get("remaining_trial", 0)

                    # 케이스 1: 무료(-1)로 변경된 경우
                    if policy_trial == -1 and current_trial != -1:
                        data["remaining_trial"] = -1
                        data["remaining_purchased"] = 0
                        self._save_credit_data(data)
                        logger.info(f"✅ 무료 정책으로 동기화됨 (remaining_trial: -1)")

                    # 케이스 2: 체험판 크레딧이 0인데 policy.json에 양수 값이 있는 경우
                    # (신규 설치 후 첫 실행 또는 정책 업데이트)
                    elif policy_trial > 0 and current_trial == 0:
                        # usage_history가 비어있으면 초기화 (한 번도 사용 안 한 경우)
                        if not data.get("usage_history"):
                            data["remaining_trial"] = policy_trial
                            self._save_credit_data(data)
                            logger.info(f"✅ 체험판 크레딧 초기화됨: {policy_trial}")

                except Exception as e:
                    logger.debug(f"정책 동기화 중 오류: {e}")

                return _normalize_credit_timestamps(data)
            else:
                self._initialize_credits()
                with open(self.credit_file, "r", encoding="utf-8") as f:
                    return _normalize_credit_timestamps(json.load(f))
        except Exception as e:
            logger.error(f"크레딧 데이터 로드 오류: {e}")
            trial_amount = self.policy.get("trial_credits", DEFAULT_TRIAL_CREDITS)
            return _normalize_credit_timestamps(
                {
                    "remaining_trial": trial_amount,
                    "remaining_purchased": 0,
                    "created_at": _get_timestamp(),
                    "last_updated": _get_timestamp(),
                    "usage_history": [],
                    "purchase_history": [],
                }
            )

    def _save_credit_data(self, data: Dict[str, Any]):
        """크레딧 데이터를 저장합니다."""
        try:
            # 파일이 이미 존재하고 숨김 처리되어 있다면 임시로 숨김 해제
            if not self.wf_manager.is_dev_mode and self.credit_file.exists():
                self.wf_manager._remove_hidden_attribute(self.credit_file)

            data["last_updated"] = _get_timestamp()
            data = _normalize_credit_timestamps(data)
            # 새 구조: app_policy 제거, remaining_trial/remaining_purchased 사용
            key_order = [
                "remaining_trial",
                "remaining_purchased",
                "credit_changed",
                "created_at",
                "last_updated",
                "purchase_history",
                "usage_history",
            ]
            ordered_data = {key: data[key] for key in key_order if key in data}
            ordered_data.update({k: v for k, v in data.items() if k not in ordered_data})
            with open(self.credit_file, "w", encoding="utf-8") as f:
                json.dump(ordered_data, f, ensure_ascii=False, indent=2)

            # 배포 모드에서 저장 후 다시 숨김 처리
            if not self.wf_manager.is_dev_mode:
                self.wf_manager._set_hidden_attribute(self.credit_file)
        except Exception as e:
            logger.error(f"크레딧 데이터 저장 오류: {e}")

    def _update_policy_file(self):
        """사용자 홈에 앱별 정책 파일 업데이트 (레포 정책 기반, 배포 모드에서 숨김 처리)"""
        try:
            # 파일이 이미 존재하고 숨김 처리되어 있다면 임시로 숨김 해제
            if not self.wf_manager.is_dev_mode and self.policy_file.exists():
                self.wf_manager._remove_hidden_attribute(self.policy_file)

            # 앱별 정책 파일 구조
            policy_data = {
                "identity": {"app_name": self.app_name},
                "policy": {},
            }

            # 기존 파일이 있으면 로드
            if self.policy_file.exists():
                try:
                    with open(self.policy_file, "r", encoding="utf-8") as f:
                        policy_data = json.load(f)
                except:
                    pass

            # 번들 정책이 있으면 사용 (JSON 파일 기반)
            bundled = self._load_bundled_policy(self.app_name)
            if bundled:
                policy_data["policy"] = bundled.copy()
                policy_data["source"] = "bundled"
            else:
                # 번들 정책이 없으면 현재 정책 유지 (경고만 표시)
                logger.warning(f"⚠️ {self.app_name}: 번들 정책 JSON이 없습니다.")
                if "policy" not in policy_data:
                    # 최소 기본값
                    policy_data["policy"] = {
                        "description": f"{self.app_name} - 정책 미설정",
                        "trial_credits": 0,
                        "credit_per_work": 1,
                        "credit_type": "per_item",
                    }
                policy_data["source"] = "fallback"

            policy_data["last_updated"] = _get_timestamp()

            with open(self.policy_file, "w", encoding="utf-8") as f:
                json.dump(policy_data, f, ensure_ascii=False, indent=2)

            # 배포 모드에서만 파일 숨김 처리 (저장 후 다시 숨김)
            if not self.wf_manager.is_dev_mode:
                self.wf_manager._set_hidden_attribute(self.policy_file)
                logger.debug(f"[RELEASE] 정책 파일 숨김 처리: {self.policy_file}")
            else:
                logger.debug(f"[DEV] 개발 모드 - 정책 파일 숨김 생략: {self.policy_file}")

        except Exception as e:
            logger.error(f"정책 파일 업데이트 오류: {e}")

    def get_all_policies(self) -> Dict[str, Any]:
        """모든 앱 정책 조회 (더 이상 사용하지 않음 - 각 앱이 개별 JSON 관리)"""
        logger.warning("⚠️ get_all_policies는 더 이상 지원하지 않습니다. 각 앱은 개별 JSON을 사용합니다.")
        return {}

    def get_credit_status(self) -> Dict[str, Any]:
        """현재 크레딧 상태를 상세히 조회합니다.

        새 구조에서는 remaining_trial, remaining_purchased를 사용합니다.
        """
        with self.lock:
            requires_registration = self.policy.get("requires_registration", True)
            policy_credit_type = self.policy.get("credit_type")

            if requires_registration and policy_credit_type != "free" and not self.wf_manager.is_registered():
                return {
                    "success": False,
                    "error": "not_registered",
                    "remaining_credits": 0,
                    "credit_type": "unregistered",
                    "message": "사용자 등록이 필요합니다.",
                }

            try:
                data = self._load_credit_data()
                remaining_trial = data.get("remaining_trial", 0)
                remaining_purchased = data.get("remaining_purchased", 0)

                if remaining_trial == -1:
                    credit_type, message, total_remaining = "free", "무료 배포판", -1
                elif remaining_purchased == -1:
                    credit_type, message, total_remaining = "permanent", "영구 라이선스", -1
                else:
                    total_remaining = remaining_trial + remaining_purchased
                    if remaining_purchased > 0 and remaining_trial > 0:
                        credit_type, message = (
                            "mixed",
                            f"체험판 {remaining_trial} + 구매 {remaining_purchased}",
                        )
                    elif remaining_purchased > 0:
                        credit_type, message = "purchased", f"구매 크레딧 {remaining_purchased}개"
                    elif remaining_trial > 0:
                        credit_type, message = "trial", f"체험판 크레딧 {remaining_trial}개"
                    else:
                        credit_type, message = "empty", "크레딧 없음"

                return {
                    "success": True,
                    "app_name": self.app_name,
                    "credit_type": credit_type,
                    "remaining_credits": total_remaining,
                    "remaining_trial": remaining_trial,
                    "remaining_purchased": remaining_purchased,
                    "created_at": data.get("created_at", ""),
                    "last_updated": data.get("last_updated", ""),
                    "usage_count": len(data.get("usage_history", [])),
                    "message": message,
                }
            except Exception as e:
                return {
                    "success": False,
                    "error": str(e),
                    "remaining_credits": 0,
                    "credit_type": "unknown",
                    "message": "크레딧 상태 확인 실패",
                }

    def deduct_credits(
        self, amount: int, description: str = "", file_count: int = 0
    ) -> Dict[str, Any]:
        """크레딧을 차감합니다.

        새 구조에서는 remaining_trial, remaining_purchased를 사용합니다.
        """
        with self.lock:
            requires_registration = self.policy.get("requires_registration", True)
            policy_credit_type = self.policy.get("credit_type")

            if requires_registration and policy_credit_type != "free" and not self.wf_manager.is_registered():
                return {"success": False, "error": "not_registered", "message": "사용자 등록 필요"}

            data = self._load_credit_data()
            trial = data.get("remaining_trial", 0)
            purchased = data.get("remaining_purchased", 0)

            if trial == -1 or purchased == -1:
                usage_record = {
                    "timestamp": _get_timestamp(),
                    "amount": amount,
                    "description": description,
                    "deducted_from": {"trial": 0, "purchased": 0},
                    "remaining_after": {"trial": trial, "purchased": purchased},
                }
                if "usage_history" not in data:
                    data["usage_history"] = []
                data["usage_history"].insert(0, usage_record)
                data["usage_history"] = data["usage_history"][:100]
                data["credit_changed"] = True
                # 세션 누적 사용량 기록
                data["session_usage_amount"] = data.get("session_usage_amount", 0) + amount
                data["session_file_count"] = data.get("session_file_count", 0) + file_count
                # 최근 사용 이벤트 타임스탬프 저장 (사용 로그 기준)
                data["session_last_usage_ts"] = usage_record["timestamp"]
                self._save_credit_data(data)
                return {
                    "success": True,
                    "message": "무료 앱 또는 영구 라이선스 사용",
                    "deducted_amount": 0,
                    "remaining_credits": -1,
                }

            total = trial + purchased
            if total < amount:
                return {
                    "success": False,
                    "error": "insufficient_credits",
                    "message": f"크레딧 부족. (필요: {amount}, 보유: {total})",
                    "remaining_credits": total,
                }

            deducted_from_trial = min(amount, trial)
            remaining_amount = amount - deducted_from_trial
            deducted_from_purchased = min(remaining_amount, purchased)

            new_trial = trial - deducted_from_trial
            new_purchased = purchased - deducted_from_purchased

            data["remaining_trial"] = new_trial
            data["remaining_purchased"] = new_purchased

            usage_record = {
                "timestamp": _get_timestamp(),
                "amount": amount,
                "description": description,
                "deducted_from": {
                    "trial": deducted_from_trial,
                    "purchased": deducted_from_purchased,
                },
                "remaining_after": {"trial": new_trial, "purchased": new_purchased},
            }

            if "usage_history" not in data:
                data["usage_history"] = []
            data["usage_history"].insert(0, usage_record)
            data["usage_history"] = data["usage_history"][:100]
            data["credit_changed"] = True
            # 세션 누적 사용량 기록
            data["session_usage_amount"] = data.get("session_usage_amount", 0) + amount
            data["session_file_count"] = data.get("session_file_count", 0) + file_count
            # 최근 사용 이벤트 타임스탬프 저장 (사용 로그 기준)
            data["session_last_usage_ts"] = usage_record["timestamp"]
            self._save_credit_data(data)

            return {
                "success": True,
                "message": f"{amount}크레딧 차감 완료.",
                "deducted_amount": amount,
                "remaining_credits": new_trial + new_purchased,
            }

    def get_per_item_cost(self) -> int:
        """앱별 아이템당 비용 조회"""
        cost = self.policy.get("credit_per_work", 1)
        logger.debug(
            f"🔧 get_per_item_cost() 호출: app={self.app_name}, cost={cost}, policy={self.policy}"
        )
        return cost

    def get_app_version(self) -> str:
        """앱 버전 정보 조회 (settings.json의 full_version)"""
        try:
            settings_file = self.app_dir / "settings.json"
            if settings_file.exists():
                with open(settings_file, "r", encoding="utf-8") as f:
                    settings = json.load(f)
                # runtime_config.full_version 또는 app_config.full_version
                runtime_version = settings.get("runtime_config", {}).get("full_version", "")
                if runtime_version:
                    return runtime_version
                app_version = settings.get("app_config", {}).get("full_version", "")
                if app_version:
                    return app_version
        except Exception as e:
            logger.debug(f"앱 버전 조회 실패: {e}")
        return ""

    def deduct_credits_by_policy(
        self, item_count: int = 1, description: str = ""
    ) -> Dict[str, Any]:
        """정책에 따른 크레딧 차감 (item_count 반영)"""
        cost_per_item = self.get_per_item_cost()
        total_cost = cost_per_item * item_count
        desc = description or f'{self.policy.get("description", "크레딧 차감")} - {item_count}개'
        # last_usage_amount를 정확히 반영하려면 amount=total_cost로 호출
        return self.deduct_credits(total_cost, desc, file_count=item_count)

    def get_policy_info(self) -> Dict[str, Any]:
        """현재 앱의 정책 정보 반환"""
        return {
            "app_name": self.app_name,
            "policy": self.policy.copy(),
            "per_item_cost": self.get_per_item_cost(),
        }

    def add_purchased_credits(
        self, amount: int, payment_info: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """구매 크레딧을 추가합니다."""
        with self.lock:
            try:
                data = self._load_credit_data()
                data["remaining_purchased"] = data.get("remaining_purchased", 0) + amount
                purchase_record = {
                    "timestamp": _get_timestamp(),
                    "amount": amount,
                    "payment_info": payment_info or {},
                    "new_total_purchased": data["remaining_purchased"],
                }
                if "purchase_history" not in data:
                    data["purchase_history"] = []
                data["purchase_history"].append(purchase_record)
                data["credit_changed"] = True
                self._save_credit_data(data)
                return {
                    "success": True,
                    "message": f"{amount} 구매 크레딧 추가 완료.",
                    "total_purchased_credits": data["remaining_purchased"],
                }
            except Exception as e:
                return {"success": False, "error": str(e), "message": "구매 크레딧 추가 중 오류"}

    def check_and_sync_credits(self) -> Dict[str, Any]:
        """credit_changed 플래그를 확인하고 필요시 구글 시트와 동기화 (세션 누적 사용량 동기화)"""
        with self.lock:
            try:
                data = self._load_credit_data()
                # credit_changed 플래그 확인
                if not data.get("credit_changed", False):
                    return {
                        "success": True,
                        "message": "동기화가 필요하지 않습니다.",
                        "synced": False,
                    }

                # 사용자 정보는 항상 전역 설정에서 읽음
                user_info = self.wf_manager.get_user_info()
                user_email = user_info.get("user_email", "")
                hardware_fingerprint = user_info.get("hardware_fingerprint", "")

                if not user_email:
                    return {
                        "success": False,
                        "error": "no_user_email",
                        "message": "동기화할 사용자 이메일이 없습니다.",
                    }

                # 동기화 전 session_usage_amount를 last_usage_amount로 복사하고 메타데이터 추가
                session_usage = data.get("session_usage_amount", 0)
                session_file_count = data.get("session_file_count", 0)
                session_last_ts = data.get("session_last_usage_ts")
                
                # session_usage가 0이 아닐 때만 last_usage_amount를 업데이트
                if session_usage > 0:
                    data["last_usage_amount"] = session_usage
                    # 최근 사용 이벤트 타임스탬프가 있다면 전달 (credit_usage_log에서 사용)
                    if session_last_ts:
                        data["last_usage_timestamp"] = session_last_ts

                # 사용 로그용 메타데이터 추가
                data["usage_file_count"] = session_file_count
                data["usage_per_item_cost"] = self.get_per_item_cost()
                data["usage_description"] = (
                    f"{self.app_name} 파일 처리 ({session_file_count}개)"
                )

                # 구글 시트 매니저를 통한 동기화
                try:
                    from wf_googlesheets_manager import get_sheets_manager

                    sheets_manager = get_sheets_manager(test_mode=True)

                    # 앱 버전 정보 조회
                    app_version = self.get_app_version()

                    # ✨ 동기화 전에 사용 로그 적재 (로그 누락 방지)
                    if session_usage > 0:
                        try:
                            sheets_manager.append_usage_log(
                                user_email=user_email,
                                app_name=self.app_name,
                                hardware_fingerprint=sheets_manager.get_hardware_fingerprint(),
                                usage_amount=float(session_usage),
                                file_count=int(session_file_count),
                                per_item_cost=float(self.get_per_item_cost()),
                                description=f"{self.app_name} 크레딧 사용 ({session_file_count}개 파일)",
                                timestamp_override=session_last_ts,
                                app_version=app_version,
                            )
                            logger.info(f"🧾 사용 로그 적재 완료: {session_usage} 크레딧 ({app_version})")
                        except Exception as log_err:
                            logger.warning(f"⚠️ 사용 로그 적재 실패 (무시): {log_err}")

                    # 동기화 시 중복 로그 방지를 위해 suppress_usage_log 설정
                    data["suppress_usage_log"] = True
                    data["app_version"] = app_version  # 동기화 시에도 버전 정보 전달

                    # 동기화 실행 (필요시 hardware_fingerprint도 전달)
                    sync_result = sheets_manager.sync_credit_data(
                        user_email=user_email, app_name=self.app_name, credit_data=data
                    )

                    if sync_result:
                        # 동기화 성공 시 플래그 및 세션 사용량 초기화
                        data["credit_changed"] = False
                        data["last_synced"] = _get_timestamp()
                        data["session_usage_amount"] = 0
                        data["session_file_count"] = 0
                        data["session_last_usage_ts"] = None
                        self._save_credit_data(data)

                        return {
                            "success": True,
                            "message": f"구글 시트와 동기화 완료: {user_email}",
                            "synced": True,
                            "sync_time": data["last_synced"],
                        }
                    else:
                        return {
                            "success": False,
                            "error": "sync_failed",
                            "message": "구글 시트 동기화 실패",
                        }

                except ImportError:
                    return {
                        "success": False,
                        "error": "no_sheets_manager",
                        "message": "Google Sheets Manager를 사용할 수 없습니다.",
                    }
                except Exception as e:
                    return {
                        "success": False,
                        "error": "sync_error",
                        "message": f"동기화 중 오류: {e}",
                    }

            except Exception as e:
                return {"success": False, "error": str(e), "message": f"동기화 확인 중 오류: {e}"}

    def force_sync_credits(self) -> Dict[str, Any]:
        """강제로 구글 시트와 동기화"""
        with self.lock:
            try:
                data = self._load_credit_data()
                data["credit_changed"] = True  # 강제로 플래그 설정
                self._save_credit_data(data)

                return self.check_and_sync_credits()

            except Exception as e:
                return {"success": False, "error": str(e), "message": f"강제 동기화 중 오류: {e}"}

    def get_sync_status(self) -> Dict[str, Any]:
        """동기화 상태 확인"""
        try:
            data = self._load_credit_data()
            return {
                "credit_changed": data.get("credit_changed", False),
                "last_synced": data.get("last_synced", "동기화 이력 없음"),
                "needs_sync": data.get("credit_changed", False),
            }
        except Exception as e:
            return {"error": str(e)}

    # ========== 작업 진행 상태 관리 (work_progress) ==========

    def init_work_progress(self, folder_path: str, total_files: int) -> Dict[str, Any]:
        """새 작업 시작 시 work_progress 초기화

        Args:
            folder_path: 작업 폴더 경로
            total_files: 전체 파일 개수

        Returns:
            성공 여부 및 메시지
        """
        with self.lock:
            try:
                data = self._load_credit_data()
                data["work_progress"] = {
                    "folder_path": folder_path,
                    "total_files": total_files,
                    "processed_files": [],
                    "last_updated": _get_timestamp(),
                }
                self._save_credit_data(data)
                logger.info(f"✅ 작업 진행 상태 초기화: {folder_path} ({total_files}개 파일)")
                return {"success": True, "message": "작업 진행 상태 초기화 완료"}
            except Exception as e:
                logger.error(f"작업 진행 상태 초기화 실패: {e}")
                return {"success": False, "error": str(e)}

    def add_processed_file(self, filename: str) -> Dict[str, Any]:
        """처리 완료된 파일 추가

        Args:
            filename: 처리 완료된 파일명

        Returns:
            성공 여부 및 현재 진행 상태
        """
        with self.lock:
            try:
                data = self._load_credit_data()
                if "work_progress" not in data:
                    return {"success": False, "error": "work_progress가 초기화되지 않았습니다."}

                progress = data["work_progress"]
                if filename not in progress["processed_files"]:
                    progress["processed_files"].append(filename)
                    progress["last_updated"] = _get_timestamp()
                    self._save_credit_data(data)

                processed_count = len(progress["processed_files"])
                total_files = progress["total_files"]
                return {
                    "success": True,
                    "processed_count": processed_count,
                    "total_files": total_files,
                    "remaining": total_files - processed_count,
                }
            except Exception as e:
                logger.error(f"처리 파일 추가 실패: {e}")
                return {"success": False, "error": str(e)}

    def get_work_progress(self, folder_path: str = None, result_folder: str = "bom") -> Dict[str, Any]:
        """작업 진행 상태 조회

        Args:
            folder_path: 확인할 폴더 경로 (None이면 저장된 진행 상태 반환)
            result_folder: 결과물 폴더명 (기본값: "bom")

        Returns:
            진행 상태 정보:
            - status: "new" | "in_progress" | "completed" | "different_folder"
            - total_files: 전체 파일 수
            - processed_count: 처리된 파일 수 (실제 결과 파일 기준)
            - remaining: 남은 파일 수
            - processed_files: 처리된 파일 목록
        """
        try:
            data = self._load_credit_data()

            # work_progress가 없는 경우에도 결과 폴더 확인
            if "work_progress" not in data:
                # 폴더 경로가 있으면 실제 결과 파일 확인
                if folder_path:
                    actual_count = self._count_result_files(folder_path, result_folder)
                    if actual_count > 0:
                        # 결과 파일이 있으면 완료 또는 진행중 상태
                        return {
                            "status": "completed",  # 일단 완료로 표시 (total_files 모름)
                            "total_files": actual_count,
                            "processed_count": actual_count,
                            "remaining": 0,
                            "processed_files": [],
                            "from_result_folder": True,
                        }
                return {
                    "status": "new",
                    "total_files": 0,
                    "processed_count": 0,
                    "remaining": 0,
                    "processed_files": [],
                }

            progress = data["work_progress"]
            stored_folder = progress.get("folder_path", "")
            total_files = progress.get("total_files", 0)
            processed_files = progress.get("processed_files", [])
            processed_count = len(processed_files)

            # 다른 폴더인 경우
            if folder_path and stored_folder and folder_path != stored_folder:
                # 새 폴더의 결과 파일 확인
                actual_count = self._count_result_files(folder_path, result_folder)
                if actual_count > 0:
                    return {
                        "status": "completed",
                        "stored_folder": stored_folder,
                        "total_files": actual_count,
                        "processed_count": actual_count,
                        "remaining": 0,
                        "processed_files": [],
                        "from_result_folder": True,
                    }
                return {
                    "status": "different_folder",
                    "stored_folder": stored_folder,
                    "total_files": 0,
                    "processed_count": 0,
                    "remaining": 0,
                    "processed_files": [],
                }

            # 실제 결과 파일 수 확인 (폴더 경로가 있는 경우)
            check_folder = folder_path or stored_folder
            actual_count = 0
            if check_folder:
                actual_count = self._count_result_files(check_folder, result_folder)

            # processed_count와 actual_count 중 큰 값 사용
            effective_count = max(processed_count, actual_count)

            # 상태 판단
            if effective_count == 0:
                status = "new"
            elif effective_count >= total_files and total_files > 0:
                status = "completed"
            else:
                status = "in_progress"

            return {
                "status": status,
                "folder_path": stored_folder,
                "total_files": total_files,
                "processed_count": effective_count,
                "remaining": max(0, total_files - effective_count),
                "processed_files": processed_files,
                "last_updated": progress.get("last_updated", ""),
            }
        except Exception as e:
            logger.error(f"작업 진행 상태 조회 실패: {e}")
            return {
                "status": "error",
                "error": str(e),
                "total_files": 0,
                "processed_count": 0,
                "remaining": 0,
                "processed_files": [],
            }

    def _count_result_files(self, folder_path: str, result_folder: str = "bom") -> int:
        """결과 폴더의 엑셀 파일 개수 반환

        Args:
            folder_path: 기본 폴더 경로
            result_folder: 결과물 폴더명 (기본값: "bom")

        Returns:
            엑셀 파일 개수
        """
        try:
            result_path = Path(folder_path) / result_folder
            if result_path.exists() and result_path.is_dir():
                return sum(1 for f in result_path.glob("*.xlsx") if f.is_file())
            return 0
        except Exception:
            return 0

    def clear_work_progress(self) -> Dict[str, Any]:
        """작업 진행 상태 초기화 (완료 또는 처음부터 다시 시작 시)

        Returns:
            성공 여부 및 메시지
        """
        with self.lock:
            try:
                data = self._load_credit_data()
                if "work_progress" in data:
                    del data["work_progress"]
                    self._save_credit_data(data)
                    logger.info("✅ 작업 진행 상태 초기화됨")
                return {"success": True, "message": "작업 진행 상태 초기화 완료"}
            except Exception as e:
                logger.error(f"작업 진행 상태 초기화 실패: {e}")
                return {"success": False, "error": str(e)}

    def is_file_processed(self, filename: str) -> bool:
        """특정 파일이 이미 처리되었는지 확인

        Args:
            filename: 확인할 파일명

        Returns:
            처리 여부
        """
        try:
            progress = self.get_work_progress()
            return filename in progress.get("processed_files", [])
        except Exception:
            return False


# 테스트 함수
def test_simple_credit_manager():
    """단순 크레딧 매니저 테스트"""
    logger.info("🧪 단순 크레딧 매니저 테스트 시작")
    test_app_name = "bom2excel_test"
    credit_file = Path.home() / ".wf_rpa" / test_app_name / "credit_history.json"
    if credit_file.exists():
        credit_file.unlink()

    cm = CreditManager(test_app_name, "insung.lee1973@gmail.com")

    # 0. 등록 상태 확인
    assert cm.wf_manager.is_registered() == True  # 테스트 시나리오상 등록되었다고 가정

    # 1. 초기 상태 확인 (체험판)
    status = cm.get_credit_status()
    logger.info(f"\n[1] 초기 상태: {status['message']}")
    assert status["credit_type"] == "trial"
    assert status["remaining_trial"] == cm.policy.get("trial_credits")

    # ... (기존 테스트 로직) ...

    logger.info("\n✅ 단순 크레딧 매니저 테스트 완료")
    if credit_file.exists():
        credit_file.unlink()


def test_worksfree_manager():
    """WorksFree 전역 매니저 테스트"""
    logger.info("\n🧪 WorksFree 전역 매니저 테스트 시작")

    # 테스트를 위해 기존 설정 파일 백업 및 삭제
    manager = WorksFreeManager()
    config_file = manager.config_file
    backup_file = config_file.with_suffix(".json.bak")
    if config_file.exists():
        config_file.rename(backup_file)

    # 1. 초기화 및 등록 안된 상태 확인
    manager._initialized = False  # 재초기화 강제
    manager.__init__()
    logger.info(f"[1] 설정 파일 경로: {manager.config_file}")
    assert manager.config_file.exists()
    assert manager.is_registered() == False
    logger.info("[1] 초기화 시 'is_registered'는 False입니다. (성공)")

    # 2. 사용자 등록
    test_email = "test@example.com"
    test_hwid = "testhwid12345"
    manager.register_user(test_email, test_hwid)
    assert manager.is_registered() == True
    logger.info("[2] 사용자 등록 후 'is_registered'는 True입니다. (성공)")

    # 3. 등록 정보 확인
    user_info = manager.get_user_info()
    assert user_info["email"] == test_email
    assert user_info["hardware_fingerprint"] == test_hwid
    assert user_info["is_registered"] == True
    logger.info("[3] 저장된 사용자 정보가 정확합니다. (성공)")

    # 4. 싱글톤 인스턴스 확인
    new_manager = WorksFreeManager()
    assert new_manager is manager
    logger.info("[4] WorksFreeManager는 싱글톤 인스턴스를 반환합니다. (성공)")

    # 테스트 종료 후 복원
    if backup_file.exists():
        backup_file.rename(config_file)
    else:
        if config_file.exists():
            config_file.unlink()

    logger.info("✅ 전역 매니저 테스트 완료")


# --- 구매 이력 동기화 테스트 ---
def test_purchase_sync():
    logger.info("\n🧪 구매 이력 동기화 테스트 시작")
    app_name = "bom2excel"
    # 기존 잘못된 클래스명(SimpleCreditManager) -> CreditManager로 수정
    cm = CreditManager(app_name, "perm_tracking@test.com")
    result = cm.pull_and_apply_purchases()
    logger.info(f"[구매 동기화 결과] {result}")
    status = cm.get_credit_status()
    logger.info(
        f"[최종 크레딧 상태] 구매 크레딧: {status['remaining_purchased']}, 히스토리: {status.get('purchase_history', [])}"
    )
    logger.info("🧪 구매 이력 동기화 테스트 완료\n")


if __name__ == "__main__":
    # 독립 실행 시 모듈 자체에서 로거 초기화 (부모 주입이 없는 경우)
    try:
        from wf_log import get_app_logger

        set_logger(get_app_logger("wf_creditmanager_simple", console_level=logging.INFO))
    except Exception:
        pass

    # 전역 매니저 테스트 실행
    test_worksfree_manager()

    logger.info("-" * 20)

    # 크레딧 매니저 테스트 실행
    # 테스트를 위해 등록 상태를 강제로 True로 설정
    wm = WorksFreeManager()
    if not wm.is_registered():
        logger.info("테스트를 위해 임시로 사용자를 등록합니다.")
        wm.register_user("temp_test@user.com", "temp_hwid")

    test_simple_credit_manager()

    logger.info("-" * 20)

    # 구매 이력 동기화 테스트 실행
    test_purchase_sync()
