import logging

# 모듈 레벨 로거 (부모에서 주입 가능). 기본은 NullHandler로 안전하게 무시
logger: logging.Logger = logging.getLogger("wf_googlesheets_manager")
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
    global logger
    logger = external_logger


# -*- coding: utf-8 -*-
"""
Google Sheets Manager - 운영용 버전
Production version for Google Sheets integration
자격증명 관리 기능 포함
"""

# ==================== 중앙 기본값 상수 ====================
# 구글 시트 미연결 시 사용되는 기본값 (단일 정의 지점)
DEFAULT_TRIAL_CREDITS = 10000  # 체험판 기본 크레딧
DEFAULT_CREDIT_PER_ITEM = 100  # 작업당 크레딧 소모량
DEFAULT_WARNING_THRESHOLD = 500  # 크레딧 경고 임계값
CREDENTIALS_FILENAME = "silver-argon-445712-a0-7092493258f3.json"  # 크리덴셜 파일명

import sys
import json
from datetime import datetime, timezone
from typing import Dict, Optional, Any
from pathlib import Path

# 🔧 자동 환경 감지: DEMO/RELEASE는 RELEASE 시트, DEV만 DEV 시트 사용
def _get_active_sheet_mode() -> str:
    """실행 환경에 따라 시트 모드 결정
    
    - DEMO 모드: RELEASE 시트 사용 (demo와 release 일관성)
    - RELEASE 번들: RELEASE 시트 사용
    - DEV 스크립트: DEV 시트 사용
    """
    # DEMO 모드 확인 (설정 파일에서 run_mode 읽기)
    try:
        config_file = Path.home() / ".wf_rpa" / "wf_rpa_config.json"
        if config_file.exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                is_demo = config.get("is_demo", False)
                if is_demo:
                    return "RELEASE"  # DEMO도 RELEASE 시트 사용
    except Exception:
        pass
    
    # PyInstaller로 번들된 실행파일인지 확인
    is_bundled = getattr(sys, "frozen", False) or hasattr(sys, "_MEIPASS")
    return "RELEASE" if is_bundled else "DEV"

ACTIVE_SHEET_MODE = _get_active_sheet_mode()  # "DEV" 또는 "RELEASE" (자동 감지)


class CredentialsHelper:
    """Google Service Account 자격증명 관리 헬퍼 클래스"""

    def __init__(self):
        self.home_dir = Path.home()
        self.wf_rpa_dir = self.home_dir / ".wf_rpa"
        # 배포 환경에서는 .wf_rpa 루트에 자격증명 파일 위치 (wf_rpa_config와 동일 위치)
        self.credentials_dir = self.wf_rpa_dir
        self.google_service_account_file = "google-service-account.json"

        # 3중 안전망: 필수 설정 파일 자동 생성 (파일 함수 정의 후 호출되도록 지연)
        # ensure_config_files()는 모듈 끝에 정의되므로 여기서는 호출하지 않음

    def _set_hidden_attribute(self, path: Path):
        """Windows에서 파일/폴더를 숨김 처리합니다 (배포 환경에서만 적용)."""
        try:
            import platform
            if platform.system() == "Windows" and self._is_bundled():
                import ctypes
                FILE_ATTRIBUTE_HIDDEN = 0x02
                attrs = ctypes.windll.kernel32.GetFileAttributesW(str(path))
                if attrs != -1:
                    ctypes.windll.kernel32.SetFileAttributesW(
                        str(path), attrs | FILE_ATTRIBUTE_HIDDEN
                    )
                else:
                    ctypes.windll.kernel32.SetFileAttributesW(str(path), FILE_ATTRIBUTE_HIDDEN)
        except Exception as e:
            logger.warning(f"크리덴셜 파일 숨김 처리 실패: {path} - {e}")

    def _get_dev_credentials_dir(self) -> Optional[Path]:
        """개발 환경의 silver-argon-*.json 파일 디렉토리 경로 찾기

        탐색 순서:
        1. 10.common/config/ (공통 폴더 - 최우선)
        2. 앱별 config/ 폴더 (fallback)
        """
        try:
            # 1. 공통 config 폴더 우선 탐색 (10.common/config/)
            common_config = self._get_common_config_dir()
            if common_config:
                silver_files = list(common_config.glob("silver-argon-*.json"))
                if silver_files:
                    logger.debug(f"[DEV-CREDS] 공통 config 폴더에서 크리덴셜 발견: {common_config}")
                    return common_config

            # 2. sys.argv[0] 기반 앱별 config 폴더 탐색 (fallback)
            import inspect
            app_root = Path(sys.argv[0]).resolve().parent

            # sys.argv[0]이 유효하지 않은 경우 (예: -c, Untitled 등), 호출 스택에서 찾기
            if not app_root.exists() or app_root.name == "10.worksfree" or "-c" in str(app_root):
                for frame_info in inspect.stack():
                    frame_path = Path(frame_info.filename).resolve()
                    if "30.apps" in frame_path.parts or "50.data" in frame_path.parts:
                        potential_app_root = frame_path.parent
                        potential_config = potential_app_root / "config"
                        if potential_config.exists():
                            silver_files = list(potential_config.glob("silver-argon-*.json"))
                            if silver_files:
                                logger.debug(f"[DEV-CREDS] 호출 스택에서 앱 경로 발견: {potential_app_root}")
                                return potential_config
                return None

            # 10.rpa 폴더에서 직접 실행되는 경우는 공통 폴더만 사용
            if app_root.name == "10.rpa" or (app_root.parent.name == "10.rpa" and app_root.name not in ["30.apps", "50.data"]):
                return common_config

            # 앱별 config 폴더 확인 (fallback)
            app_config_dir = app_root / "config"
            if app_config_dir.exists() and app_config_dir.is_dir():
                silver_files = list(app_config_dir.glob("silver-argon-*.json"))
                if silver_files:
                    return app_config_dir

            return common_config  # 앱별 폴더에 없으면 공통 폴더 반환
        except Exception as e:
            logger.debug(f"[DEV-CREDS] 개발 자격증명 경로 찾기 실패: {e}")
            return None

    def _get_common_config_dir(self) -> Optional[Path]:
        """10.common/config/ 공통 설정 폴더 경로 반환"""
        try:
            # 현재 파일(wf_googlesheets_manager.py)이 10.common에 있으므로
            current_file = Path(__file__).resolve()
            common_dir = current_file.parent  # 10.common
            common_config = common_dir / "config"

            if common_config.exists() and common_config.is_dir():
                return common_config
            return None
        except Exception:
            return None

    def _is_bundled(self) -> bool:
        """번들된 실행파일인지 확인"""
        return getattr(sys, "frozen", False) or hasattr(sys, "_MEIPASS")

    def _get_bundled_credentials_dir(self) -> Optional[Path]:
        """번들된 실행파일의 credentials 디렉토리 경로"""
        try:
            if hasattr(sys, "_MEIPASS"):
                # PyInstaller 번들: _internal/.wf_rpa (config 폴더 구조 직접 사용)
                bundled_path = Path(getattr(sys, "_MEIPASS")) / ".wf_rpa"
                logger.info(f"[DEBUG] 번들 크리덴셜 경로 시도: {bundled_path}, 존재={bundled_path.exists()}")
                if bundled_path.exists():
                    silver_files = list(bundled_path.glob("silver-argon-*.json"))
                    logger.info(f"[DEBUG] silver-argon 파일 검색: {len(silver_files)}개 발견")
                    logger.debug(f"번들 크리덴셜 경로 (_MEIPASS): {bundled_path}")
                    return bundled_path
                else:
                    logger.warning(f"[DEBUG] 번들 경로 존재하지 않음: {bundled_path}")

            exe_dir = (
                Path(sys.executable).parent
                if getattr(sys, "frozen", False)
                else Path(__file__).parent
            )
            res_path = exe_dir / "res"
            if res_path.exists():
                return res_path

            logger.warning(f"[DEBUG] 번들 크리덴셜 디렉토리를 찾을 수 없습니다")
            return None
        except Exception as e:
            logger.error(f"번들 크리덴셜 경로 검색 실패: {e}")
            return None

    def _validate_credentials_file(self, file_path: Path) -> bool:
        """credentials 파일 유효성 검증"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            required_fields = ["type", "project_id", "private_key", "client_email"]
            return (
                all(field in data and data[field] for field in required_fields)
                and data["type"] == "service_account"
            )
        except Exception:
            return False

    def ensure_user_credentials(self) -> bool:
        """환경에 따라 다른 위치에서 silver-argon-*.json 파일 확인"""
        try:
            logger.info(f"[DEBUG] ensure_user_credentials 시작 (번들={self._is_bundled()})")
            
            # 배포 환경: _internal/.wf_rpa/silver-argon-*.json 직접 참조
            if self._is_bundled():
                bundled_dir = self._get_bundled_credentials_dir()
                logger.info(f"[DEBUG] 번들 디렉토리: {bundled_dir}")
                
                if bundled_dir:
                    silver_files = list(bundled_dir.glob("silver-argon-*.json"))
                    logger.info(f"[DEBUG] silver-argon 파일 검색 결과: {len(silver_files)}개")
                    
                    if silver_files:
                        logger.info(f"[DEBUG] 첫 번째 파일: {silver_files[0]}")
                        if self._validate_credentials_file(silver_files[0]):
                            logger.info(f"번들 자격증명 파일 사용: {silver_files[0]}")
                            return True
                        else:
                            logger.warning(f"[DEBUG] 자격증명 파일 유효성 검증 실패")
                    else:
                        logger.warning(f"번들에서 silver-argon 파일을 찾을 수 없음: {bundled_dir}")
                        return False

            # 개발 환경: 앱 폴더 아래 config에서 silver-argon-*.json 직접 사용
            else:
                dev_dir = self._get_dev_credentials_dir()
                logger.info(f"[DEBUG] 개발 디렉토리: {dev_dir}")
                
                if dev_dir:
                    silver_files = list(dev_dir.glob("silver-argon-*.json"))
                    if silver_files and self._validate_credentials_file(silver_files[0]):
                        logger.info(f"개발환경 자격증명 파일 사용: {silver_files[0]}")
                        return True

            logger.warning(f"[DEBUG] 자격증명 파일을 찾을 수 없음")
            return False
        except Exception as e:
            logger.error(f"사용자 credentials 설정 오류: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    def _get_configured_credentials_filename(self) -> Optional[str]:
        """wf_rpa_config.json에서 환경별 크리덴셜 파일명 조회"""
        try:
            config_dir = self._get_common_config_dir()
            if not config_dir:
                config_dir = self.wf_rpa_dir

            config_file = config_dir / "wf_rpa_config.json"
            if not config_file.exists():
                config_file = self.wf_rpa_dir / "wf_rpa_config.json"

            if config_file.exists():
                with open(config_file, "r", encoding="utf-8") as f:
                    config = json.load(f)
                gs_config = config.get("google_sheets", {})

                # ACTIVE_SHEET_MODE에 따라 크리덴셜 파일 선택
                if ACTIVE_SHEET_MODE == "RELEASE":
                    return gs_config.get("credentials_file_release")
                else:  # DEV
                    return gs_config.get("credentials_file_dev")
        except Exception as e:
            logger.debug(f"크리덴셜 파일명 설정 조회 실패: {e}")
        return None

    def get_google_credentials_path(self) -> Optional[Path]:
        """환경별 크리덴셜 파일 경로 반환 (RELEASE/DEV에 따라 다른 파일 사용)"""
        # 1. 설정에서 지정된 크리덴셜 파일명 조회
        configured_filename = self._get_configured_credentials_filename()

        if configured_filename:
            # 배포 환경: _internal/.wf_rpa/ 또는 ~/.wf_rpa/
            if self._is_bundled():
                bundled_dir = self._get_bundled_credentials_dir()
                if bundled_dir:
                    creds_file = bundled_dir / configured_filename
                    if creds_file.exists() and self._validate_credentials_file(creds_file):
                        self._set_hidden_attribute(creds_file)
                        logger.info(f"배포환경 자격증명 파일 반환 (설정): {creds_file}")
                        return creds_file
                # 사용자 홈 폴더에서도 탐색
                home_creds = self.wf_rpa_dir / configured_filename
                if home_creds.exists() and self._validate_credentials_file(home_creds):
                    logger.info(f"배포환경 자격증명 파일 반환 (홈): {home_creds}")
                    return home_creds
            # 개발 환경: 10.common/config/
            else:
                dev_dir = self._get_dev_credentials_dir()
                if dev_dir:
                    creds_file = dev_dir / configured_filename
                    if creds_file.exists() and self._validate_credentials_file(creds_file):
                        logger.info(f"개발환경 자격증명 파일 반환 (설정): {creds_file}")
                        return creds_file

        # 2. 폴백: 기존 silver-argon-*.json 패턴으로 탐색
        if self.ensure_user_credentials():
            if self._is_bundled():
                bundled_dir = self._get_bundled_credentials_dir()
                if bundled_dir:
                    silver_files = list(bundled_dir.glob("*.json"))
                    for sf in silver_files:
                        if self._validate_credentials_file(sf):
                            self._set_hidden_attribute(sf)
                            logger.info(f"배포환경 자격증명 파일 반환 (폴백): {sf}")
                            return sf
            else:
                dev_dir = self._get_dev_credentials_dir()
                if dev_dir:
                    silver_files = list(dev_dir.glob("silver-argon-*.json"))
                    if silver_files:
                        return silver_files[0]
        return None
    
    # def get_google_credentials_path(self) -> Optional[Path]:
    #     """silver-argon-*.json 파일 경로 반환"""
    #     if self.ensure_user_credentials():
    #         if self._is_bundled():
    #             # 배포 환경 로직...
    #             pass
    #         else:
    #             # 개발 환경
    #             dev_dir = self._get_dev_credentials_dir()
    #             if dev_dir:
    #                 # _load_config()에서 지정한 파일명 사용
    #                 config = self._load_config()
    #                 target_file = dev_dir / config["CREDENTIALS_FILE"]
                    
    #                 if target_file.exists():
    #                     return target_file
    #                 else:
    #                     # 지정된 파일이 없으면 기존 방식 (glob) 사용
    #                     silver_files = list(dev_dir.glob("silver-argon-*.json"))
    #                     if silver_files:
    #                         return silver_files[0]
    #     return None

    def update_credentials_from_drive(self, drive_file_id: str) -> Dict[str, Any]:
        """
        구글 드라이브에서 새 크리덴셜 파일을 다운로드하여 기존 파일을 교체합니다.

        Args:
            drive_file_id: 구글 드라이브의 크리덴셜 파일 ID

        Returns:
            Dict with 'success' (bool), 'message' (str), 'backup_path' (str, optional)
        """
        import shutil
        from datetime import datetime

        try:
            # 현재 크리덴셜 파일 경로 가져오기
            current_creds_path = self.get_google_credentials_path()
            if not current_creds_path or not current_creds_path.exists():
                return {
                    "success": False,
                    "message": "현재 크리덴셜 파일을 찾을 수 없습니다. 수동으로 설치해주세요."
                }

            # 기존 크리덴셜로 드라이브 접근
            try:
                from google.oauth2.service_account import Credentials
                from googleapiclient.discovery import build
                from googleapiclient.http import MediaIoBaseDownload
                import io

                SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
                credentials = Credentials.from_service_account_file(
                    str(current_creds_path), scopes=SCOPES
                )
                drive_service = build('drive', 'v3', credentials=credentials)

            except ImportError as e:
                return {
                    "success": False,
                    "message": f"Google Drive API 라이브러리가 없습니다: {e}"
                }
            except Exception as e:
                return {
                    "success": False,
                    "message": f"크리덴셜 인증 실패: {e}"
                }

            # 드라이브에서 파일 다운로드
            try:
                request = drive_service.files().get_media(fileId=drive_file_id)
                file_content = io.BytesIO()
                downloader = MediaIoBaseDownload(file_content, request)

                done = False
                while not done:
                    _, done = downloader.next_chunk()

                file_content.seek(0)
                new_creds_data = file_content.read()

            except Exception as e:
                return {
                    "success": False,
                    "message": f"드라이브에서 파일 다운로드 실패: {e}"
                }

            # JSON 유효성 검사
            try:
                import json
                json.loads(new_creds_data.decode('utf-8'))
            except json.JSONDecodeError:
                return {
                    "success": False,
                    "message": "다운로드된 파일이 유효한 JSON 형식이 아닙니다."
                }

            # 기존 파일 백업
            backup_suffix = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = current_creds_path.with_suffix(f".backup_{backup_suffix}.json")

            try:
                shutil.copy2(current_creds_path, backup_path)
                logger.info(f"기존 크리덴셜 파일 백업: {backup_path}")
            except Exception as e:
                return {
                    "success": False,
                    "message": f"기존 파일 백업 실패: {e}"
                }

            # 새 파일 저장 (기존 파일명 유지)
            try:
                # 배포 환경에서 숨김 속성 임시 해제
                if self._is_bundled():
                    self._remove_hidden_for_write(current_creds_path)

                with open(current_creds_path, 'wb') as f:
                    f.write(new_creds_data)

                # 배포 환경에서 숨김 속성 재적용
                if self._is_bundled():
                    self._set_hidden_attribute(current_creds_path)

                logger.info(f"새 크리덴셜 파일 저장 완료: {current_creds_path}")

            except Exception as e:
                # 저장 실패 시 백업 복원
                try:
                    shutil.copy2(backup_path, current_creds_path)
                except:
                    pass
                return {
                    "success": False,
                    "message": f"새 파일 저장 실패 (백업 복원됨): {e}"
                }

            return {
                "success": True,
                "message": "크리덴셜 파일이 성공적으로 업데이트되었습니다.",
                "backup_path": str(backup_path)
            }

        except Exception as e:
            logger.error(f"크리덴셜 업데이트 중 예외 발생: {e}")
            return {
                "success": False,
                "message": f"크리덴셜 업데이트 실패: {e}"
            }

    def _remove_hidden_for_write(self, path: Path):
        """Windows에서 파일의 숨김 속성을 임시 제거합니다 (쓰기 위해)."""
        try:
            import platform
            if platform.system() == "Windows":
                import ctypes
                FILE_ATTRIBUTE_HIDDEN = 0x02
                attrs = ctypes.windll.kernel32.GetFileAttributesW(str(path))
                if attrs != -1 and (attrs & FILE_ATTRIBUTE_HIDDEN):
                    ctypes.windll.kernel32.SetFileAttributesW(
                        str(path), attrs & ~FILE_ATTRIBUTE_HIDDEN
                    )
        except Exception as e:
            logger.warning(f"숨김 해제 실패: {path} - {e}")



class GoogleSheetsManager:
    # 기존 hwid 기반 초기화 메서드 제거 (중복 __init__ 정리)

    def _normalize_app_name(self, app_name: str) -> str:
        """앱 이름을 표준 형식(Title_Underscore)으로 정규화

        규칙:
        - 하이픈("-")은 언더바("_")로 치환
        - 언더바로 분리 후 각 토큰의 첫 글자만 대문자
        - 예) "conversion_verifier" → "Conversion_Verifier"
             "dwg-batch-print" → "Dwg_Batch_Print"
        """
        try:
            key = str(app_name or "").strip()
            key = key.replace("-", "_")
            parts = [p for p in key.split("_") if p]
            if not parts:
                return ""
            return "_".join(p[:1].upper() + p[1:] for p in parts)
        except Exception:
            return str(app_name or "").strip()

    def _get_timestamp(self) -> str:
        """[Deprecated soon] 기존 로컬 타임스탬프 (ms 3자리, tz 미포함)"""
        return datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]

    def _now_local_iso_ms(self) -> str:
        """로컬 타임존 포함 ISO (ms) 예: 2025-10-14T15:00:00.123+09:00"""
        return datetime.now().astimezone().isoformat(timespec="milliseconds")

    def _now_utc_iso_ms_z(self) -> str:
        """UTC ISO (ms) Z 표기 예: 2025-10-14T06:00:00.123Z"""
        return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")

    def _ensure_credit_sync_headers(self, ws) -> None:
        """credit_sync 워크시트의 헤더를 최신 스키마로 정렬/업데이트"""
        desired = [
            "user_email",
            "app_name",
            "app_version",
            "hardware_fingerprint",
            "trial_credits",
            "purchased_credits",
            "last_usage",
            "last_usage_time_local",
            "last_usage_time_utc",
            "last_usage_tz_name",
            "last_sync_utc",
        ]
        try:
            values = ws.row_values(1)
            if values != desired:
                # 헤더 업데이트 (부족한 컬럼은 자동 확장됨)
                ws.update("A1", [desired])
        except Exception as e:
            logger.warning(f"credit_sync 헤더 정렬 실패: {e}")

    def _ensure_credit_usage_headers(self, ws) -> None:
        """credit_usage_log 워크시트의 헤더를 최신 스키마로 정렬/업데이트"""
        desired = [
            "event_time_local",
            "event_time_utc",
            "event_tz_name",
            "user_email",
            "app_name",
            "app_version",
            "hardware_fingerprint",
            "usage_amount",
            "file_count",
            "per_item_cost",
            "description",
        ]
        try:
            values = ws.row_values(1)
            if values != desired:
                ws.update("A1", [desired])
        except Exception as e:
            logger.warning(f"credit_usage_log 헤더 정렬 실패: {e}")

    def _ensure_registrations_headers(self, ws) -> None:
        """registrations 워크시트의 헤더를 최신 스키마로 정렬/업데이트"""
        desired = [
            "user_email",
            "user_name",
            "user_phone",
            "user_email_consent",
            "uc_hw_fingerprint",
            "uc_hw_cpuinfo",
            "uc_hw_mbinfo",
            "uc_hw_storageinfo",
            "uc_first_app",
            "uc_first_app_version",
            "reg_time_local",
            "reg_time_utc",
            "reg_tz_name",
        ]
        try:
            values = ws.row_values(1)
            if values != desired:
                ws.update("A1", [desired])
        except Exception as e:
            logger.warning(f"registrations 헤더 정렬 실패: {e}")

    def get_purchase_records(
        self, user_email: str, app_name: str
    ) -> list:
        """credit_purchase_log 시트에서 해당 유저/앱의 미적용 구매 이력 반환 (transaction_id 기준, timestamp 최신순)"""
        try:
            if not self.gc:
                logger.warning("⚠️ 구글 시트 연결이 없어 구매 이력을 가져올 수 없습니다.")
                return []

            sheet_id = self._load_config()[f"SHEET_ID_{ACTIVE_SHEET_MODE}"]
            try:
                purchase_ws = self.gc.open_by_key(sheet_id).worksheet("credit_purchase_log")
            except Exception:
                logger.warning("⚠️ credit_purchase_log 시트가 존재하지 않습니다.")
                return []

            # 앱 이름 정규화 (별칭 지원)
            app_name_normalized = self._normalize_app_name(app_name)

            # 실제 헤더 가져오기 (빈 컬럼 제외)
            header_row = purchase_ws.row_values(1)
            # 빈 문자열 제거
            actual_headers = [h for h in header_row if h.strip()]
            logger.debug(f"📋 실제 헤더: {actual_headers}")

            try:
                records = purchase_ws.get_all_records(expected_headers=actual_headers)
                logger.debug(f"📥 구매 이력 {len(records)}건 조회 성공")
            except Exception as e:
                logger.error(f"❌ get_all_records 실패: {e}")
                return []

            filtered = []
            for rec in records:
                # 필수 필드 체크
                rec_id = str(rec.get("transaction_id", "")).strip()
                rec_email = str(rec.get("email", "")).strip().lower()
                rec_app = str(rec.get("app_name", "")).strip()
                applied_date = str(rec.get("applied_date", "")).strip()
                purchase_date = str(rec.get("purchase_date", "")).strip()

                # 필수 필드가 없으면 건너뛰기
                if not rec_id or not rec_email or not rec_app:
                    logger.debug(
                        f"❌ 필수 필드 누락: id={rec_id}, email={rec_email}, app={rec_app}"
                    )
                    continue

                # 사용자 이메일 매칭
                if rec_email != user_email.strip().lower():
                    logger.debug(f"⏭️ 이메일 불일치: {rec_email} != {user_email.strip().lower()}")
                    continue

                # 앱 이름 매칭 (별칭 정규화 적용)
                rec_app_normalized = self._normalize_app_name(rec_app)
                logger.debug(
                    f"🔍 앱 이름 정규화: {rec_app} → {rec_app_normalized} (찾는 앱: {app_name_normalized})"
                )
                if rec_app_normalized != app_name_normalized:
                    logger.debug(f"⏭️ 앱 이름 불일치: {rec_app_normalized} != {app_name_normalized}")
                    continue

                # 이미 반영된 건(applied_date가 있는 건)은 건너뛰기
                if applied_date:
                    logger.debug(f"⏭️ 이미 반영됨: {rec_id} (applied_date={applied_date})")
                    continue

                logger.debug(
                    f"✅ 미반영 구매 발견: {rec_id} | {rec.get('purchased_credit', 0)}크레딧"
                )

                # 미반영된 구매만 추가 (purchase_date 포함)
                rec["_sort_key"] = purchase_date if purchase_date else rec_id
                filtered.append(rec)

            # timestamp(purchase_date) 기준 내림차순 정렬 (최신 것이 앞으로)
            filtered.sort(key=lambda x: x.get("_sort_key", ""), reverse=True)

            # 디버그 로그 (확장 구조 대응)
            if filtered:
                logger.info(
                    f"📥 {user_email}/{app_name} 미적용 구매 {len(filtered)}건 조회 (최신순)"
                )
                for idx, rec in enumerate(filtered[:3]):  # 최대 3건만 로그
                    # 신규 구조: purchased_credit + bonus_credit
                    purchased = rec.get("purchased_credit", 0)
                    bonus = rec.get("bonus_credit", 0)
                    total = rec.get("total_credit", 0)

                    # total_credit이 없으면 계산
                    if not total and (purchased or bonus):
                        total = purchased + bonus

                    promo = rec.get("promo_code", "")

                    # 상세 정보 포맷
                    if purchased and bonus:
                        detail = f"{purchased}+{bonus}={total}크레딧"
                    else:
                        detail = f"{total}크레딧"

                    if promo:
                        detail += f" 🎁{promo}"

                    logger.debug(
                        f"  [{idx+1}] {rec.get('transaction_id')} | {rec.get('purchase_date', 'N/A')} | {detail}"
                    )

            return filtered
        except Exception as e:
            logger.error(f"❌ 구매 이력 조회 오류: {e}")
            return []

    """구글 시트 관리 클래스 (gspread 방식)"""

    def __init__(self, test_mode: bool = False):
        """
        초기화

        Args:
            test_mode: 테스트 모드 여부 (기본값: False - 운영 모드)
        """
        self.test_mode = test_mode
        self.gc = None  # gspread client
        self.worksheet = None
        self.admin_worksheet = None  # admin_config 워크시트 추가
        self._setup_service()

    def _setup_service(self):
        """구글 시트 서비스 설정 (gspread 방식)"""
        try:
            is_bundled = getattr(sys, "frozen", False) or hasattr(sys, "_MEIPASS")
            logger.info(f"[DEBUG] 구글 시트 서비스 초기화 시작 (번들={is_bundled})")
            
            # gspread와 구글 인증 라이브러리 import
            import gspread
            from google.oauth2.service_account import Credentials

            # 설정 파일 시도
            config = self._load_config()

            # 시트 ID 선택
            # sheet_id = (config[f"SHEET_ID_{ACTIVE_SHEET_MODE}"] if self.test_mode
            #            else config["SHEET_ID_RELEASE"])
            sheet_id = config[f"SHEET_ID_{ACTIVE_SHEET_MODE}"]

            # CredentialsHelper 직접 사용
            credentials_manager = CredentialsHelper()
            logger.info(f"[DEBUG] CredentialsHelper 생성 완료")
            
            creds_file = credentials_manager.get_google_credentials_path()
            logger.info(f"자격증명 파일 경로: {creds_file}")

            if creds_file and creds_file.exists():
                logger.info(f"[DEBUG] 자격증명 파일 존재 확인: {creds_file}")
                # 서비스 계정 인증
                credentials = Credentials.from_service_account_file(
                    str(creds_file), scopes=config["SCOPE"]
                )

                # gspread 클라이언트 생성
                self.gc = gspread.authorize(credentials)

                # 스프레드시트 열기
                spreadsheet = self.gc.open_by_key(sheet_id)
                self.worksheet = spreadsheet.worksheet(config["SHEET_NAME_REGISTRATIONS"])

                # admin_config 워크시트도 열기
                try:
                    self.admin_worksheet = spreadsheet.worksheet("admin_config")
                except Exception as e:
                    logger.warning(f"⚠️ admin_config 워크시트를 찾을 수 없습니다: {e}")
                    self.admin_worksheet = None

                # credit_usage_log 워크시트도 초기화 시 열어두기 (registrations와 동일한 방식)
                try:
                    self.usage_worksheet = spreadsheet.worksheet("credit_usage_log")
                    self._ensure_credit_usage_headers(self.usage_worksheet)
                except Exception:
                    # 없으면 생성
                    try:
                        self.usage_worksheet = spreadsheet.add_worksheet(title="credit_usage_log", rows=1000, cols=12)
                        self._ensure_credit_usage_headers(self.usage_worksheet)
                        logger.info("📋 credit_usage_log 워크시트 생성 완료")
                    except Exception as e:
                        logger.warning(f"⚠️ credit_usage_log 워크시트를 생성할 수 없습니다: {e}")
                        self.usage_worksheet = None

                logger.info(
                    f"✅ 구글 시트 연결 성공 ({'테스트' if self.test_mode else '운영'} 모드)"
                )

            else:
                logger.warning(
                    f"⚠️ Google Service Account 인증서 파일을 찾을 수 없거나 설정할 수 없습니다"
                )
                logger.warning(
                    f"   예상 위치: {Path.home() / '.wf_rpa' / 'silver-argon-*.json'} (배포) 또는 앱의 config 폴더 (개발)"
                )
                self.gc = None
                self.worksheet = None
                self.admin_worksheet = None
                self.usage_worksheet = None

        except ImportError as e:
            logger.error("❌ gspread 라이브러리가 설치되지 않았습니다.")
            logger.error("설치 명령: pip install gspread google-auth")
            self.gc = None
            self.worksheet = None
            self.admin_worksheet = None
            self.usage_worksheet = None
        except Exception as e:
            error_str = str(e).lower()
            if 'invalid_grant' in error_str or 'invalid jwt' in error_str:
                user_friendly_error = (
                    "❌ 구글 시트 인증 실패: 서비스 계정 키(.json) 파일이 유효하지 않습니다.\n"
                    "   ▶ 해결 방법: 구글 클라우드 콘솔(GCP)에서 새 키를 발급받아 기존 파일을 교체해주세요."
                )
                logger.error(user_friendly_error)
            
            logger.error(f"❌ 구글 시트 서비스 설정 중 예기치 않은 오류 발생: {e}")
            import traceback
            logger.error(traceback.format_exc())
            self.gc = None
            self.worksheet = None
            self.admin_worksheet = None
            self.usage_worksheet = None

    def get_email_config(self) -> Dict[str, str]:
        """admin_config 시트에서 이메일 설정 가져오기 (enabled=TRUE인 레코드만)"""
        try:
            if not self.admin_worksheet:
                logger.error("❌ 'admin_config' 워크시트가 없어 이메일 설정을 로드할 수 없습니다.")
                logger.error(
                    "   솔루션: 구글 시트에 'admin_config' 워크시트를 생성하고 아래와 같이 설정해주세요."
                )
                logger.error(
                    "   - A열(key): email_from, email_to, email_login, smtp_server, smtp_port"
                )
                logger.error("   - B열(value): 각 키에 해당하는 값")
                logger.error("   - C열(enabled): TRUE 또는 FALSE")
                return {}

            records = self.admin_worksheet.get_all_records()
            # print(f"[DEBUG] admin_config 전체 레코드: {records}")

            # enabled=TRUE인 레코드만 필터링
            enabled_records = [
                record for record in records if str(record.get("enabled", "")).upper() == "TRUE"
            ]

            if not enabled_records:
                logger.warning("⚠️ 'admin_config' 워크시트에 enabled=TRUE인 레코드가 없습니다.")
                return {}

            if len(enabled_records) > 1:
                logger.warning(
                    f"⚠️ 'admin_config' 워크시트에 enabled=TRUE인 레코드가 {len(enabled_records)}개 있습니다. 첫 번째 레코드를 사용합니다."
                )

            # 첫 번째 enabled=TRUE 레코드 사용
            enabled_record = enabled_records[0]
            logger.debug(f"[DEBUG] 선택된 enabled 레코드: {enabled_record}")

            email_config = {}

            # 레코드가 key-value 형식인 경우 (세로 형태)
            if "key" in enabled_record and "value" in enabled_record:
                # 모든 레코드를 다시 확인해서 enabled=TRUE이면서 필요한 키들만 수집
                for record in enabled_records:
                    key = str(record.get("key", "")).strip()
                    value = record.get("value", "")

                    # 값이 None이거나 빈 문자열이면 건너뜀
                    if value is None or (isinstance(value, str) and not value.strip()):
                        continue

                    if key in ["email_from", "email_to", "email_login", "smtp_server", "smtp_port"]:
                        # smtp_port는 문자열로 변환하되, 숫자는 그대로 유지
                        if key == "smtp_port":
                            email_config[key] = (
                                str(value).strip() if isinstance(value, str) else str(value)
                            )
                        else:
                            email_config[key] = (
                                str(value).strip() if isinstance(value, str) else str(value)
                            )
            else:
                # 레코드가 직접 컬럼 형식인 경우 (가로 형태)
                for key in ["email_from", "email_to", "email_login", "smtp_server", "smtp_port"]:
                    value = enabled_record.get(key, "")

                    # 값이 None이거나 빈 문자열이면 건너뜀
                    if value is None or (isinstance(value, str) and not value.strip()):
                        continue

                    # smtp_port는 문자열로 변환하되, 숫자는 그대로 유지
                    if key == "smtp_port":
                        email_config[key] = (
                            str(value).strip() if isinstance(value, str) else str(value)
                        )
                    else:
                        email_config[key] = (
                            str(value).strip() if isinstance(value, str) else str(value)
                        )

            # 필수 키 확인
            required_keys = ["email_from", "email_to", "email_login", "smtp_server", "smtp_port"]
            missing_keys = [
                key for key in required_keys if key not in email_config or not email_config[key]
            ]

            if missing_keys:
                logger.warning(
                    f"⚠️ 'admin_config' 워크시트에 이메일 설정이 누락되었습니다. (누락된 키: {', '.join(missing_keys)})"
                )
                logger.debug(f"[DEBUG] 현재 로드된 설정: {email_config}")
                return {}

            logger.info(f"📧 이메일 설정이 'admin_config' 시트에서 로드되었습니다.")
            logger.info(f"   - email_from: {email_config.get('email_from', '')}")
            logger.info(f"   - email_to: {email_config.get('email_to', '')}")
            logger.info(
                f"   - smtp_server: {email_config.get('smtp_server', '')}:{email_config.get('smtp_port', '')}"
            )

            return email_config

        except Exception as e:
            logger.error(f"❌ 'admin_config' 시트에서 이메일 설정 로드 중 오류 발생: {e}")
            import traceback

            traceback.print_exc()
            return {}

    def get_app_policies(self) -> Dict[str, Any]:
        """app_policy 시트에서 앱별 정책 데이터 가져오기 (유연한 컬럼/별칭/활성화 처리)"""
        try:
            if not self.gc:
                logger.error("❌ 구글 시트 연결이 없어 app_policy를 로드할 수 없습니다.")
                return {}

            config = self._load_config()
            sheet_id = config[f"SHEET_ID_{ACTIVE_SHEET_MODE}"]

            try:
                spreadsheet = self.gc.open_by_key(sheet_id)
                app_policy_worksheet = spreadsheet.worksheet("app_policy")
            except Exception as e:
                logger.error(f"❌ 'app_policy' 워크시트를 찾을 수 없습니다: {e}")
                return {}

            records = app_policy_worksheet.get_all_records()
            logger.debug(f"[DEBUG] app_policy 레코드 개수: {len(records)}")

            def _enabled_val(v: Any) -> bool:
                try:
                    if isinstance(v, bool):
                        return v
                    s = str(v).strip().upper()
                    return s in ("TRUE", "Y", "YES", "1")
                except Exception:
                    return False

            policies: Dict[str, Any] = {}
            for record in records:
                # 활성화 컬럼이 없으면 전체 허용, 있으면 참값만
                if "enabled" in record and not _enabled_val(record.get("enabled")):
                    continue

                raw_name = str(record.get("app_name", "")).strip()
                if not raw_name:
                    continue
                norm_name = self._normalize_app_name(raw_name)

                # 컬럼 이름 유연성: trial_credits or default_credit 등
                def _to_int(x, default=0):
                    try:
                        return int(x)
                    except Exception:
                        return default

                trial_credits = record.get("trial_credits")
                if trial_credits is None:
                    trial_credits = record.get("default_credit")

                credit_per_work = record.get("credit_per_work")
                if credit_per_work is None:
                    credit_per_work = record.get("per_item_cost")

                policy = {
                    "icon_text": record.get("icon_text", ""),
                    "description": record.get("description", ""),
                    "trial_credits": _to_int(trial_credits, 0),
                    "credit_per_work": _to_int(credit_per_work, 0),
                    "credit_type": record.get("credit_type", "per_file"),
                }

                policies[norm_name] = policy

            logger.info(f"✅ app_policy 시트에서 {len(policies)}개 앱 정책을 로드했습니다.")
            return policies

        except Exception as e:
            logger.error(f"❌ app_policy 로드 오류: {e}")
            import traceback

            logger.error(traceback.format_exc())
            return {}

    def get_admin_config_full(self) -> Dict[str, Any]:
        """admin_config 시트에서 전체 관리자 설정 가져오기 (엄격 모드)
        - enabled 값이 TRUE/Y/YES/1 인 행이 정확히 1개여야 함
        - 해당 '단일' 행의 값들만 사용
        - 행이 0개 또는 2개 이상이면 빈 dict 반환 및 경고 로그
        - 세로형(key/value)일 경우 단일 행의 key/value만 반영
        """
        try:
            if not self.admin_worksheet:
                logger.error("❌ 'admin_config' 워크시트가 없어 관리자 설정을 로드할 수 없습니다.")
                return {}

            records = self.admin_worksheet.get_all_records()
            if not records:
                logger.warning("⚠️ 'admin_config' 워크시트에 레코드가 없습니다.")
                return {}

            def _enabled_val(v: Any) -> bool:
                try:
                    if isinstance(v, bool):
                        return v
                    s = str(v).strip().upper()
                    return s in ("TRUE", "Y", "YES", "1")
                except Exception:
                    return False

            enabled_rows = [r for r in records if _enabled_val(r.get("enabled"))]
            if len(enabled_rows) != 1:
                logger.warning(
                    f"⚠️ admin_config는 enabled=TRUE 행이 정확히 1개여야 합니다. 현재 {len(enabled_rows)}개"
                )
                return {}

            row = enabled_rows[0]

            # 세로형(key/value) 단일 행 처리
            if "key" in row and "value" in row:
                key = str(row.get("key", "")).strip()
                value = row.get("value", "")
                if not key:
                    logger.warning("⚠️ admin_config 세로형 단일 행의 key가 비어 있습니다.")
                    return {}
                config = {key: value}
            else:
                # 가로형: 해당 행의 컬럼들을 그대로 사용 (enabled 제외)
                config = {k: v for k, v in row.items() if k and k != "enabled"}

            logger.info(f"✅ admin_config 시트에서 {len(config)}개 설정을 로드했습니다.")
            return config

        except Exception as e:
            logger.error(f"❌ admin_config 로드 오류: {e}")
            import traceback

            logger.error(traceback.format_exc())
            return {}

    def _load_config(self):
        """설정 로드 (wf_rpa_config.json에서만 로드)"""
        # get_sheets_config()를 사용하여 중앙화된 설정 로드
        config = get_sheets_config()
        # config["CREDENTIALS_FILE"] = "silver-argon-445712-a0-4ce021aa64be.json"
        config["CREDENTIALS_FILE"] = "silver-argon-445712-a0-7092493258f3.json"
        # silver-argon-445712-a0-7092493258f3

        return config

    def _get_hardware_info_once(self) -> Dict[str, str]:
        """하드웨어 정보를 한 번만 수집하여 딕셔너리로 반환"""
        try:
            import wf_hwinfo

            hw = wf_hwinfo.HardwareInfo()
            return {
                "fingerprint": hw.fingerprint or "",
                "cpu_id": hw.cpu_id or "",
                "mainboard_id": hw.mainboard_id or "",
                "storage_id": hw.storage_id or "",
            }
        except Exception as e:
            logger.warning(f"⚠️ 하드웨어 정보 수집 실패: {e}")
            return {"fingerprint": "", "cpu_id": "", "mainboard_id": "", "storage_id": ""}

    def get_hardware_fingerprint(self) -> str:
        """하드웨어 지문 반환 (sync_credit_data, get_synced_credit_data에서 사용)"""
        return self._get_hardware_info_once()["fingerprint"]

    def prepare_registration_data(
        self,
        user_email: str,
        user_name: str,
        user_phone: str,
        user_email_consent: str,
        app_name: str,
        app_version: str = "",
    ) -> Dict[str, Any]:
        """등록 데이터 준비"""
        # 타임존 포함 타임스탬프 구성
        reg_time_local = self._now_local_iso_ms()
        reg_time_utc = self._now_utc_iso_ms_z()
        tz_name = datetime.now().astimezone().tzname() or ""

        # 하드웨어 정보 수집 (한 번만 생성)
        hw_info = self._get_hardware_info_once()

        # Canonicalize app name for storage
        canonical_app = self._normalize_app_name(app_name)

        registration_data = {
            "user_email": user_email,
            "user_name": user_name,
            "user_phone": user_phone,
            "user_email_consent": user_email_consent,
            "uc_hw_fingerprint": hw_info["fingerprint"],
            "uc_hw_cpuinfo": hw_info["cpu_id"],
            "uc_hw_mbinfo": hw_info["mainboard_id"],
            "uc_hw_storageinfo": hw_info["storage_id"],
            "uc_first_app": canonical_app,
            "uc_first_app_version": app_version,
            "reg_time_local": reg_time_local,
            "reg_time_utc": reg_time_utc,
            "reg_tz_name": tz_name,
        }

        return registration_data

    def add_registration_to_sheet(self, registration_data: Dict[str, Any]) -> bool:
        """구글 시트에 등록 정보 추가 (gspread 방식)"""
        try:
            if not self.worksheet:
                logger.warning("⚠️ 구글 시트가 초기화되지 않았습니다.")
                return False

            # 헤더 정렬: registrations 시트 스키마 보장
            try:
                self._ensure_registrations_headers(self.worksheet)
            except Exception as e:
                logger.warning(f"registrations 헤더 정렬 실패: {e}")

            # 새 행 데이터 준비
            row_data = [
                registration_data.get("user_email", ""),
                registration_data.get("user_name", ""),
                registration_data.get("user_phone", ""),
                registration_data.get("user_email_consent", ""),
                registration_data.get("uc_hw_fingerprint", ""),
                registration_data.get("uc_hw_cpuinfo", ""),
                registration_data.get("uc_hw_mbinfo", ""),
                registration_data.get("uc_hw_storageinfo", ""),
                registration_data.get("uc_first_app", ""),
                registration_data.get("uc_first_app_version", ""),
                registration_data.get("reg_time_local", ""),
                registration_data.get("reg_time_utc", ""),
                registration_data.get("reg_tz_name", ""),
            ]

            # gspread로 행 추가 (매우 간단!)
            self.worksheet.append_row(row_data)

            logger.info(
                f"✅ 등록 정보가 구글 시트에 추가되었습니다: {registration_data['user_email']}"
            )
            return True

        except Exception as e:
            logger.error(f"❌ 구글 시트 등록 오류: {e}")
            return False

    def register_user(
        self,
        user_email: str,
        user_name: str,
        user_phone: str,
        user_email_consent: str,
        app_name: str,
        app_version: str = "",
    ) -> bool:
        """사용자 등록 (전체 프로세스) - gspread 방식

        사용자 정보는 wf_rpa_config.json의 user_info에 저장되므로
        여기서는 Google Sheets에 등록 로그만 기록합니다.
        """
        try:
            # 등록 데이터 준비
            registration_data = self.prepare_registration_data(
                user_email, user_name, user_phone, user_email_consent, app_name, app_version
            )

            # 구글 시트에 추가
            if self.worksheet:
                return self.add_registration_to_sheet(registration_data)
            else:
                logger.warning("⚠️ 구글 시트를 사용할 수 없습니다.")
                return False

        except Exception as e:
            logger.error(f"❌ 사용자 등록 오류: {e}")
            return False

    def sync_local_registration_to_sheets(self, app_name: str, app_version: str = "") -> dict:
        """로컬에 저장된 등록정보를 Google Sheets에 동기화

        네트워크 문제로 등록이 완료되지 않은 경우, wf_rpa_config.json의
        user_info 블록에서 등록 정보를 읽어 Google Sheets에 업로드합니다.

        Args:
            app_name: 앱 이름 (bom_exporter, dwg_batch_print 등)
            app_version: 앱 버전 (선택)

        Returns:
            dict: {
                "success": bool,
                "message": str,
                "already_synced": bool  # 이미 동기화되어 있는 경우 True
            }
        """
        result = {"success": False, "message": "", "already_synced": False}

        try:
            # wf_rpa_config.json에서 사용자 정보 읽기
            config_path = Path.home() / ".wf_rpa" / "wf_rpa_config.json"
            if not config_path.exists():
                result["message"] = "설정 파일이 없습니다. 먼저 앱에서 등록을 완료하세요."
                return result

            with open(config_path, "r", encoding="utf-8") as f:
                config_data = json.load(f)

            user_block = config_data.get("user_info", {})
            if not isinstance(user_block, dict):
                user_block = {}

            if not user_block.get("is_registered"):
                result["message"] = "로컬에 등록 정보가 없습니다. 먼저 앱에서 등록을 완료하세요."
                return result

            user_email = user_block.get("user_email", "")
            user_name = user_block.get("user_name", "")
            hardware_fingerprint = user_block.get("client_hw_fingerprint", "")

            if not user_email or not hardware_fingerprint:
                result["message"] = "등록 정보가 불완전합니다 (이메일 또는 하드웨어 지문 누락)."
                return result

            # Google Sheets 연결 확인
            if not self.gc or not self.worksheet:
                result["message"] = "Google Sheets에 연결할 수 없습니다. 네트워크 연결을 확인하세요."
                return result

            # 이미 등록되어 있는지 확인 (하드웨어 지문 기준)
            if self.is_fingerprint_registered(hardware_fingerprint):
                result["success"] = True
                result["already_synced"] = True
                result["message"] = f"이미 Google Sheets에 등록되어 있습니다 ({user_email})."
                return result

            # 등록 데이터 준비 및 업로드
            registration_data = self.prepare_registration_data(
                user_email=user_email,
                user_name=user_name,
                user_phone=user_block.get("user_phone", ""),
                user_email_consent=user_block.get("user_email_consent", "동의"),
                app_name=app_name,
                app_version=app_version
            )

            # Google Sheets에 등록
            if self.add_registration_to_sheet(registration_data):
                result["success"] = True
                result["message"] = f"등록 정보가 Google Sheets에 동기화되었습니다 ({user_email})."
                logger.info(f"✅ 로컬 등록정보 동기화 완료: {user_email}")
            else:
                result["message"] = "Google Sheets 등록 중 오류가 발생했습니다."

        except Exception as e:
            result["message"] = f"동기화 중 오류 발생: {e}"
            logger.error(f"❌ 로컬 등록정보 동기화 오류: {e}")

        return result

    def sync_credit_data(self, user_email: str, app_name: str, credit_data: Dict[str, Any]) -> bool:
        """크레딧 데이터를 구글 시트에 동기화 (테스트 모드 강제, json 필드 제외)"""
        try:
            if not self.gc:
                logger.warning("⚠️ 구글 시트 연결이 없어 크레딧 동기화를 할 수 없습니다.")
                logger.error("[SYNC-FAIL] gc is None - Google Sheets 클라이언트가 초기화되지 않음")
                return False

            # 테스트 모드 시트만 사용
            sheet_id = self._load_config()[f"SHEET_ID_{ACTIVE_SHEET_MODE}"]
            logger.debug(f"[SYNC-DEBUG] sheet_id: {sheet_id}, ACTIVE_SHEET_MODE: {ACTIVE_SHEET_MODE}")

            try:
                credit_worksheet = self.gc.open_by_key(sheet_id).worksheet("credit_sync")
                logger.debug(f"[SYNC-DEBUG] credit_sync 워크시트 열기 성공")
            except Exception as ws_err:
                logger.warning(f"[SYNC-DEBUG] credit_sync 워크시트 없음, 새로 생성 시도: {ws_err}")
                spreadsheet = self.gc.open_by_key(sheet_id)
                credit_worksheet = spreadsheet.add_worksheet(
                    title="credit_sync", rows=1000, cols=30
                )
                # 새로운 헤더 (타임존 포함)
                self._ensure_credit_sync_headers(credit_worksheet)
                logger.info(f"[SYNC-DEBUG] credit_sync 워크시트 생성 완료")
            else:
                # 기존 시트도 최신 헤더로 정렬
                self._ensure_credit_sync_headers(credit_worksheet)

            # 기존 데이터 찾기
            existing_records = credit_worksheet.get_all_records()
            hardware_fingerprint = self.get_hardware_fingerprint()

            existing_row = None
            for i, record in enumerate(existing_records):
                if (
                    record.get("user_email") == user_email
                    and record.get("app_name") == app_name
                    and record.get("hardware_fingerprint") == hardware_fingerprint
                ):
                    existing_row = i + 2  # 헤더 행 제외
                    break

            # 동기화할 데이터 준비 (last_usage: 최근 사용량)
            last_usage = credit_data.get("last_usage_amount", 0)
            # 이벤트 시각 소스(로컬 기준으로 들어온 값으로 간주)
            raw_event_ts = credit_data.get("last_usage_timestamp")  # naive 또는 포맷 문자열
            # 파싱 및 로컬/UTC 계산
            event_time_local = None
            event_time_utc = None
            tz_name = datetime.now().astimezone().tzname() or ""
            try:
                if raw_event_ts:
                    # naive 문자열이면 로컬로 간주
                    try:
                        dt = datetime.fromisoformat(str(raw_event_ts))
                        if dt.tzinfo is None:
                            dt = dt.replace(tzinfo=datetime.now().astimezone().tzinfo)
                        event_time_local = dt.astimezone().isoformat(timespec="milliseconds")
                        event_time_utc = (
                            dt.astimezone(timezone.utc)
                            .isoformat(timespec="milliseconds")
                            .replace("+00:00", "Z")
                        )
                        tz_name = dt.astimezone().tzname() or tz_name
                    except Exception:
                        # 파싱 실패 시 현재 시각 사용
                        event_time_local = self._now_local_iso_ms()
                        event_time_utc = self._now_utc_iso_ms_z()
                else:
                    event_time_local = self._now_local_iso_ms()
                    event_time_utc = self._now_utc_iso_ms_z()
            except Exception:
                event_time_local = self._now_local_iso_ms()
                event_time_utc = self._now_utc_iso_ms_z()

            last_sync_utc = self._now_utc_iso_ms_z()
            app_version = credit_data.get("app_version", "")
            sync_data = [
                user_email,
                app_name,
                app_version,
                hardware_fingerprint,
                credit_data.get("trial_credits", 0),
                credit_data.get("purchased_credits", 0),
                last_usage,
                event_time_local,
                event_time_utc,
                tz_name,
                last_sync_utc,
            ]

            if existing_row:
                for col, value in enumerate(sync_data, 1):
                    credit_worksheet.update_cell(existing_row, col, value)
                logger.info(
                    f"✅ 크레딧 데이터 업데이트 완료: {user_email} ({app_name}) [테스트 모드]"
                )
            else:
                credit_worksheet.append_row(sync_data)
                logger.info(f"✅ 크레딧 데이터 추가 완료: {user_email} ({app_name}) [테스트 모드]")

            # 사용 로그 적재는 필요 시점에 별도로 수행 가능하며, 동기화 시에는 생략할 수 있다
            suppress_usage_log = bool(credit_data.get("suppress_usage_log", False))
            logger.info(
                f"[DEBUG-SYNC] suppress_usage_log={suppress_usage_log}, last_usage={last_usage}"
            )
            if not suppress_usage_log:
                # 사용 로그 적재 (사용량이 있는 경우에만)
                logger.info(
                    f"[DEBUG-SYNC] last_usage 체크: {last_usage}, float로 변환: {float(last_usage) if last_usage else 0}"
                )
                if last_usage and float(last_usage) != 0:
                    try:
                        # 메타데이터 추출 (credit_data에서 가져오기)
                        file_count = credit_data.get("usage_file_count", 0)
                        per_item_cost = credit_data.get("usage_per_item_cost", 0.0)
                        description = credit_data.get(
                            "usage_description", f"{app_name} 크레딧 사용"
                        )
                        # 사용 이벤트 발생 시각 (가능하면 이벤트 시각 사용, 없으면 현재 시각)
                        usage_event_ts = str(credit_data.get("last_usage_timestamp") or "")

                        logger.info(
                            f"[DEBUG-SYNC] 사용 로그 추가 시도: amount={last_usage}, files={file_count}, cost={per_item_cost}"
                        )

                        # 앱 버전 정보 추출
                        app_version = str(credit_data.get("app_version", ""))

                        self._append_credit_usage_log(
                            user_email=user_email,
                            app_name=app_name,
                            hardware_fingerprint=hardware_fingerprint,
                            usage_amount=float(last_usage),
                            file_count=int(file_count),
                            per_item_cost=float(per_item_cost),
                            description=str(description),
                            timestamp_override=usage_event_ts,
                            app_version=app_version,
                        )
                        logger.info(f"[DEBUG-SYNC] 사용 로그 추가 완료")
                    except Exception as log_err:
                        logger.error(f"크레딧 사용 로그 적재 실패: {log_err}")
                        import traceback

                        traceback.print_exc()
                else:
                    logger.warning(f"[DEBUG-SYNC] 사용 로그 건너뜀: last_usage={last_usage}")

            return True

        except Exception as e:
            logger.error(f"❌ 크레딧 동기화 오류: {e}")
            import traceback

            traceback.print_exc()
            return False

    def _append_credit_usage_log(
        self,
        user_email: str,
        app_name: str,
        hardware_fingerprint: str,
        usage_amount: float,
        file_count: int = 0,
        per_item_cost: float = 0.0,
        description: str = "",
        timestamp_override: Optional[str] = None,
        app_version: str = "",
    ):
        """credit_usage_log 워크시트에 사용 기록을 한 줄 추가합니다."""
        logger.info(
            f"[DEBUG-USAGE-LOG] 호출됨: user={user_email}, app={app_name} ({app_version}), amount={usage_amount}, files={file_count}"
        )

        # 가드: 클라이언트 또는 워크시트 없음
        if not self.gc:
            logger.error("❌ [USAGE-LOG-FAIL] 구글 시트 클라이언트가 없음 (self.gc is None)")
            return
            
        if not self.usage_worksheet:
            logger.error("❌ [USAGE-LOG-FAIL] usage_worksheet가 없음 (self.usage_worksheet is None)")
            logger.error("   → 해결: GoogleSheetsManager 초기화 시 usage_worksheet가 None으로 설정됨")
            logger.error("   → 원인: credit_usage_log 시트가 없거나 초기화 실패")
            return

        # 이벤트 시각 파싱(가능하면 timestamp_override 사용)
        try:
            if timestamp_override:
                dt = datetime.fromisoformat(str(timestamp_override))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=datetime.now().astimezone().tzinfo)
                event_time_local = dt.astimezone().isoformat(timespec="milliseconds")
                event_time_utc = (
                    dt.astimezone(timezone.utc)
                    .isoformat(timespec="milliseconds")
                    .replace("+00:00", "Z")
                )
                tz_name = dt.astimezone().tzname() or ""
            else:
                event_time_local = self._now_local_iso_ms()
                event_time_utc = self._now_utc_iso_ms_z()
                tz_name = datetime.now().astimezone().tzname() or ""
        except Exception:
            event_time_local = self._now_local_iso_ms()
            event_time_utc = self._now_utc_iso_ms_z()
            tz_name = datetime.now().astimezone().tzname() or ""

        # 레코드 추가 (확장된 메타데이터 포함)
        row = [
            event_time_local,
            event_time_utc,
            tz_name,
            user_email,
            app_name,
            app_version,
            hardware_fingerprint,
            usage_amount,
            file_count,
            per_item_cost,
            description,
        ]

        logger.info(f"[DEBUG-USAGE-LOG] 시트에 추가할 row: {row}")
        # registrations와 동일하게 self.usage_worksheet 사용
        self.usage_worksheet.append_row(row)
        logger.info(
            f"🧾 크레딧 사용 로그 기록: {user_email} {app_name} ({app_version}) {usage_amount} (파일:{file_count}, 단가:{per_item_cost})"
        )

    def append_usage_log(
        self,
        user_email: str,
        app_name: str,
        hardware_fingerprint: str,
        usage_amount: float,
        file_count: int = 0,
        per_item_cost: float = 0.0,
        description: str = "",
        timestamp_override: Optional[str] = None,
        app_version: str = "",
    ) -> bool:
        """외부에서 호출 가능한 공개 메서드: 사용 로그만 적재"""
        try:
            if not self.gc:
                logger.warning("⚠️ 구글 시트 클라이언트가 없어 사용 로그를 적재할 수 없습니다.")
                return False
            self._append_credit_usage_log(
                user_email=user_email,
                app_name=app_name,
                hardware_fingerprint=hardware_fingerprint,
                usage_amount=usage_amount,
                file_count=file_count,
                per_item_cost=per_item_cost,
                description=description,
                timestamp_override=timestamp_override,
                app_version=app_version,
            )
            return True
        except Exception as e:
            logger.error(f"❌ append_usage_log 실패: {e}")
            return False

    def get_synced_credit_data(self, user_email: str, app_name: str) -> Optional[Dict[str, Any]]:
        """구글 시트에서 동기화된 크레딧 데이터 가져오기"""
        try:
            if not self.gc:
                logger.warning("⚠️ 구글 시트 연결이 없어 크레딧 데이터를 가져올 수 없습니다.")
                return None

            # 개발 중에는 테스트 시트만 사용 (배포 시 변경)
            try:
                credit_worksheet = self.gc.open_by_key(
                    self._load_config()[f"SHEET_ID_{ACTIVE_SHEET_MODE}"]
                ).worksheet("credit_sync")
            except Exception:
                logger.warning("⚠️ credit_sync 시트가 존재하지 않습니다.")
                return None

            # 데이터 찾기
            records = credit_worksheet.get_all_records()
            hardware_fingerprint = self.get_hardware_fingerprint()

            for record in records:
                if (
                    record.get("user_email") == user_email
                    and record.get("app_name") == app_name
                    and record.get("hardware_fingerprint") == hardware_fingerprint
                ):

                    # JSON 문자열을 다시 파싱
                    return {
                        "trial_credits": int(record.get("trial_credits", 0)),
                        "purchased_credits": int(record.get("purchased_credits", 0)),
                        "last_sync_utc": record.get("last_sync_utc", ""),
                        "last_usage_time_local": record.get("last_usage_time_local", ""),
                        "last_usage_time_utc": record.get("last_usage_time_utc", ""),
                        "last_usage_tz_name": record.get("last_usage_tz_name", ""),
                    }

            return None

        except Exception as e:
            logger.error(f"❌ 크레딧 데이터 가져오기 오류: {e}")
            return None

    def is_fingerprint_registered(self, fingerprint: str) -> bool:
        """하드웨어 지문이 이미 등록되어 있는지 확인"""
        try:
            if not self.worksheet:
                logger.warning("⚠️ 구글 시트가 초기화되지 않았습니다.")
                return False

            # 모든 레코드 가져오기
            records = self.worksheet.get_all_records()

            # 하드웨어 지문 확인
            for record in records:
                if record.get("uc_hw_fingerprint") == fingerprint:
                    return True

            return False

        except Exception as e:
            logger.error(f"❌ 하드웨어 지문 확인 오류: {e}")
            return False

    # 중복된 get_app_policies 정의 제거 (위의 유연한 구현 사용)


# 싱글톤 인스턴스 생성 함수
_manager_instance = None


def get_sheets_manager(test_mode: Optional[bool] = None) -> GoogleSheetsManager:
    """구글 시트 매니저 싱글톤 인스턴스 반환"""
    global _manager_instance

    if _manager_instance is None:
        # 테스트 모드 설정
        if test_mode is None:
            test_mode = False  # 기본값을 False로 변경 (운영 모드)

        _manager_instance = GoogleSheetsManager(test_mode=test_mode)

    return _manager_instance


# 하위 호환성을 위한 별칭
GoogleSheetsClient = GoogleSheetsManager
get_client = get_sheets_manager


# 중앙화된 시트 설정 제공자 (외부 모듈에서 직접 접근용)
def get_sheets_config() -> Dict[str, Any]:
    """Google Sheets 사용을 위한 공통 설정을 wf_rpa_config.json에서 반환합니다.
    google_sheets 섹션이 없으면 자동으로 추가합니다.

    Returns:
        Dict: {
          'SHEET_ID_RELEASE': str,
          'SHEET_ID_DEV': str,
          'SHEET_NAME_REGISTRATIONS': str,
          'SCOPE': list[str]
        }
    
    Raises:
        FileNotFoundError: wf_rpa_config.json 파일이 없는 경우
    """
    config_file = Path.home() / ".wf_rpa" / "wf_rpa_config.json"
    
    if not config_file.exists():
        raise FileNotFoundError(
            f"설정 파일을 찾을 수 없습니다: {config_file}\n"
            "ensure_config_files()를 먼저 호출하세요."
        )
    
    with open(config_file, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    # google_sheets 섹션이 없으면 자동으로 추가
    if "google_sheets" not in config:
        logger.warning("⚠️ google_sheets 섹션이 없어 기본값으로 생성합니다.")
        config["google_sheets"] = {
            "sheet_id_release": "1bUqpV1vSGwsVeWav-6enZUzaKBTJdxX5eZ737lNh6Ww",
            "sheet_id_dev": "1bUqpV1vSGwsVeWav-6enZUzaKBTJdxX5eZ737lNh6Ww",
            "credentials_file_release": "worksfree-b33a6b8f366b.json",
            "credentials_file_dev": "silver-argon-445712-a0-7092493258f3.json",
            "sheet_name_registrations": "registrations",
            "scope": [
                "https://spreadsheets.google.com/feeds",
                "https://www.googleapis.com/auth/drive"
            ]
        }
        # 업데이트된 config를 파일에 저장
        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            logger.info(f"✅ google_sheets 섹션이 설정 파일에 추가되었습니다: {config_file}")
        except Exception as e:
            logger.warning(f"⚠️ 설정 파일 저장 실패: {e}")
    
    gs_config = config["google_sheets"]
    
    return {
        "SHEET_ID_RELEASE": gs_config["sheet_id_release"],
        "SHEET_ID_DEV": gs_config["sheet_id_dev"],
        "SHEET_NAME_REGISTRATIONS": gs_config["sheet_name_registrations"],
        "SCOPE": gs_config["scope"],
    }


def get_credentials_helper() -> CredentialsHelper:
    """중앙화된 자격증명 헬퍼 인스턴스를 반환합니다."""
    return CredentialsHelper()


# ==================== 3중 안전망: 필수 설정 파일 자동 생성 ====================
def ensure_config_files(app_name: Optional[str] = None):
    """필수 설정 파일 보장 (단일화: wf_rpa_config.json)

    DWG Classifier 기준으로 글로벌 구성 파일을 하나로 축소.
    기존 `.wf_global_config.json`가 있으면 내용(installation_info, user_info)을
    `wf_rpa_config.json`에 병합 후 더 이상 새 파일을 생성하지 않음.
    """
    wf_rpa_dir = Path.home() / ".wf_rpa"
    wf_rpa_dir.mkdir(parents=True, exist_ok=True)

    config_file = wf_rpa_dir / "wf_rpa_config.json"
    if not config_file.exists():
        bundled_config = _try_copy_from_bundle("wf_rpa_config.json", config_file)
        if not bundled_config:
            _create_default_wf_rpa_config(config_file)

    # 기존 글로벌 파일 마이그레이션 (존재 시 1회 병합)
    global_config_file = wf_rpa_dir / ".wf_global_config.json"
    if global_config_file.exists():
        try:
            with open(global_config_file, "r", encoding="utf-8") as f:
                gdata = json.load(f) or {}
        except Exception:
            gdata = {}
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                cdata = json.load(f) or {}
        except Exception:
            cdata = {}

        # 병합: installation_info / user_info (존재하지 않는 키만 추가)
        inst = gdata.get("installation_info", {})
        if inst:
            if "installation_info" not in cdata:
                cdata["installation_info"] = inst
            else:
                for k, v in inst.items():
                    cdata["installation_info"].setdefault(k, v)
        g_user = gdata.get("user_info", {})
        if g_user:
            # user_info로 직접 병합 (기존 값 우선, 누락 키만 채움)
            if "user_info" not in cdata or not isinstance(cdata.get("user_info"), dict):
                cdata["user_info"] = {}
            for k, v in g_user.items():
                cdata["user_info"].setdefault(k, v)
            # 과거 global_user_info 키가 있다면 제거
            if "global_user_info" in cdata:
                try:
                    del cdata["global_user_info"]
                except Exception:
                    pass

        # 저장 후 글로벌 파일 이름 변경(보존) 또는 삭제
        try:
            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(cdata, f, ensure_ascii=False, indent=2)
            # 파일 처리: 안전하게 이름 변경, 실패 시 그대로 둠
            deprecated = global_config_file.with_name(".wf_global_config.deprecated.json")
            try:
                global_config_file.rename(deprecated)
                logger.info(f"✓ 글로벌 설정 병합 완료 (deprecated로 변경): {deprecated}")
            except Exception:
                logger.info("✓ 글로벌 설정 병합 완료 (원본 유지)")
        except Exception as e:
            logger.warning(f"글로벌 설정 병합 실패: {e}")

    # 앱별 정책 파일(policy.json: identity+policy) 보장
    if app_name:
        app_dir = wf_rpa_dir / app_name
        app_dir.mkdir(exist_ok=True)
        policy_file = app_dir / "policy.json"
        if not policy_file.exists():
            _create_default_policy(policy_file, app_name)


def _try_copy_from_bundle(filename: str, dest: Path) -> bool:
    """번들된 설정 파일을 사용자 디렉토리로 복사 시도

    Returns:
        bool: 복사 성공 여부
    """
    try:
        if hasattr(sys, "_MEIPASS"):
            # PyInstaller 번들: _internal/.wf_rpa/파일명
            from shutil import copy2
            bundled = Path(getattr(sys, "_MEIPASS")) / ".wf_rpa" / filename
            if bundled.exists():
                copy2(bundled, dest)
                logger.info(f"✓ 번들에서 설정 파일 복사: {filename}")
                return True
        return False
    except Exception as e:
        logger.debug(f"번들 복사 실패 ({filename}): {e}")
        return False


def _create_default_wf_rpa_config(config_file: Path):
    """기본 wf_rpa_config.json 생성 (v2 통일 구조)"""
    default_config = {
        "schema_version": 2,
        "user_info": {
            "is_registered": False,
            "user_email": "",
            "user_name": "",
            "user_phone": "",
            "user_email_consent": "",
            "client_hw_fingerprint": "",
            "client_hw_cpuinfo": "",
            "client_hw_mbinfo": "",
            "client_hw_storageinfo": "",
            "reg_time_local": "",
            "reg_time_utc": "",
            "reg_tz_name": "",
            "last_login": "",
            "note": "첫 실행 시 하드웨어 정보가 자동으로 수집됩니다"
        },
        "email_settings": {
            "version": 2,
            "use_local_email_config": True,
            "email_from": "insung.lee1973@gmail.com",
            "email_to": "insung.lee@worksfree.kr",
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
            "admin_email_sheet_name": "email_settings"
        },
        "app_settings": {"language": "ko"},
        "system_settings": {"auto_update": True, "send_usage_stats": False, "log_level": "DEBUG"},
        "google_sheets": {
            "sheet_id_release": "1bUqpV1vSGwsVeWav-6enZUzaKBTJdxX5eZ737lNh6Ww",
            "sheet_id_dev": "1bUqpV1vSGwsVeWav-6enZUzaKBTJdxX5eZ737lNh6Ww",
            "credentials_file_release": "worksfree-b33a6b8f366b.json",
            "credentials_file_dev": "silver-argon-445712-a0-7092493258f3.json",
            "sheet_name_registrations": "registrations",
            "scope": [
                "https://spreadsheets.google.com/feeds",
                "https://www.googleapis.com/auth/drive"
            ]
        },
        "execution_status": {
            "is_running": False,
            "current_app": None,
            "pid": None,
            "started_at": None,
        },
        "last_updated": datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3],
    }

    with open(config_file, "w", encoding="utf-8") as f:
        json.dump(default_config, f, ensure_ascii=False, indent=2)
    logger.info(f"✓ 기본 wf_rpa_config.json 생성: {config_file}")


def _create_default_policy(config_file: Path, app_name: str):
    """기본 policy.json 생성 (앱별: identity + policy)"""
    default_config = {
        "version": "1.0",
        "identity": {"app_name": app_name},
        "policy": {
            "trial_credits": DEFAULT_TRIAL_CREDITS,
            "credit_per_item": DEFAULT_CREDIT_PER_ITEM,
            "warning_threshold": DEFAULT_WARNING_THRESHOLD,
        },
        "last_updated": datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3],
        "source": "local_default",
    }

    with open(config_file, "w", encoding="utf-8") as f:
        json.dump(default_config, f, ensure_ascii=False, indent=2)
    logger.info(f"✓ 기본 policy.json 생성: {config_file}")


# ==================== 테스트 코드 ====================
if __name__ == "__main__":
    import sys
    import os
    from datetime import datetime, timezone
    
    print("\n" + "="*60)
    print("구글 시트 사용자 등록 테스트")
    print("="*60 + "\n")
    
    # 개발 환경 설정: sys.argv[0]을 앱의 ui_main.py로 변경
    original_argv = sys.argv[0]
    sys.argv[0] = str(Path(__file__).parent.parent / "30.apps" / "bom_exporter" / "ui_main.py")
    print(f"[0] 테스트용 sys.argv[0]: {sys.argv[0]}\n")
    
    try:
        # GoogleSheetsManager 초기화
        print("[1] GoogleSheetsManager 초기화 중...")
        manager = get_sheets_manager(test_mode=False)
        
        if not manager.worksheet:
            print("❌ 구글 시트 초기화 실패!")
            sys.exit(1)
        
        print("✅ 구글 시트 연결 성공\n")
        
        # 테스트 데이터 생성
        print("[2] 테스트 사용자 등록 데이터 생성 중...")
        test_data = {
            "user_email": "test@example.com",
            "user_name": "테스트사용자",
            "user_phone": "010-1234-5678",
            "user_email_consent": "동의",
            "uc_hw_fingerprint": "TEST-FINGERPRINT-12345",
            "uc_hw_cpuinfo": "TEST-CPU-ID",
            "uc_hw_mbinfo": "TEST-MB-ID",
            "uc_hw_storageinfo": "TEST-STORAGE-ID",
            "uc_first_app": "Bom_Exporter",
            "reg_time_local": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "reg_time_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
            "reg_tz_name": "Asia/Seoul"
        }
        
        print(f"  이메일: {test_data['user_email']}")
        print(f"  이름: {test_data['user_name']}")
        print(f"  지문: {test_data['uc_hw_fingerprint']}\n")
        
        # 구글 시트에 등록
        print("[3] 구글 시트에 데이터 추가 중...")
        result = manager.add_registration_to_sheet(test_data)
        
        if result:
            print("✅ 구글 시트 등록 성공!\n")
            print(f"등록 시각: {test_data['reg_time_local']}")
        else:
            print("❌ 구글 시트 등록 실패!\n")
            sys.exit(1)
        
        print("\n" + "="*60)
        print("테스트 완료")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ 테스트 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        # 원래 값 복원
        sys.argv[0] = original_argv
