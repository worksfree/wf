"""Common settings utilities for WorksFree apps.

Provides unified retrieval of user registration and hardware information
for display in each app's Settings window. This centralizes logic so UI
modules don't duplicate file parsing and hardware probing code.

Data source: ~/.wf_rpa/wf_rpa_config.json (user_info block)
Fallback: Live hardware info via wf_hwinfo.HardwareInfo()

Returned dictionary keys (all optional – missing values become empty strings):
  email                Registered user email
  name                 Registered user name
  registration_date    ISO date/time string
  hardware_fingerprint Full fingerprint (may be truncated in UI)
  cpu_id               CPU identifier string
  mainboard_id         Mainboard identifier string
  is_registered        Boolean registration flag (best effort)

NOTE: UI code is responsible for truncating long values for display.
"""

from __future__ import annotations

from pathlib import Path
import json
from typing import Dict, Any


def _safe_read_json(path: Path) -> Dict[str, Any]:
    try:
        if path.exists():
            with path.open("r", encoding="utf-8") as f:
                return json.load(f) or {}
    except Exception:
        pass
    return {}


def get_user_hardware_info() -> Dict[str, Any]:
    """Return consolidated user & hardware info from wf_rpa_config.json.

    Falls back gracefully; never raises. Missing fields become ''.
    """
    wf_root = Path.home() / ".wf_rpa"
    info: Dict[str, Any] = {}

    # wf_rpa_config.json의 user_info 블록에서 읽기
    config_path = wf_root / "wf_rpa_config.json"
    config = _safe_read_json(config_path)
    src = config.get("user_info", {}) if isinstance(config.get("user_info"), dict) else {}

    # Live hardware fallback
    cpu_id = ""
    mainboard_id = ""
    storage_id = ""
    fingerprint = ""
    try:
        import wf_hwinfo  # type: ignore

        hw = wf_hwinfo.HardwareInfo()
        cpu_id = hw.cpu_id or ""
        mainboard_id = getattr(hw, "mainboard_id", "") or ""
        storage_id = getattr(hw, "storage_id", "") or ""
        fingerprint = hw.fingerprint or ""
    except Exception:
        pass

    info["email"] = src.get("user_email", src.get("email", ""))
    info["name"] = src.get("user_name", src.get("name", ""))
    info["registration_date"] = src.get("reg_time_local", src.get("registration_date", ""))
    info["hardware_fingerprint"] = (
        src.get("client_hw_fingerprint") or src.get("hardware_fingerprint") or fingerprint or ""
    )
    info["cpu_id"] = src.get("cpu_id", cpu_id)
    info["mainboard_id"] = src.get("mainboard_id", mainboard_id)
    info["storage_id"] = src.get("storage_id", storage_id)
    info["is_registered"] = bool(
        src.get("is_registered")
        or src.get("user_email")
        or src.get("email")
    )
    return info


def format_info_for_tree(info: Dict[str, Any]) -> Dict[str, str]:
    """Return a mapping of display label -> value for Tree/Table rendering."""
    fp = info.get("hardware_fingerprint", "")
    short_fp = fp[:16] + "..." if len(fp) > 16 else fp
    return {
        "등록 이메일": info.get("email", "") or "등록 정보 없음",
        "사용자 이름": info.get("name", "") or "",
        "등록 일시": info.get("registration_date", "") or "",
        "CPU ID": info.get("cpu_id", "") or "",
        "메인보드 ID": info.get("mainboard_id", "") or "",
        "스토리지 ID": info.get("storage_id", "") or "",
        "하드웨어 지문": short_fp or "",
    }


def sync_policies_from_sheets(app_name: str, logger=None) -> Dict[str, Any]:
    """구글 시트에서 app_policy와 admin_config를 가져와 로컬 JSON 파일에 저장

    Args:
        app_name: 앱 이름 (bom2excel, dwg_classifier, etc.)
        logger: 로거 객체 (선택사항)

    Returns:
        Dict with 'success' (bool), 'message' (str), and optional 'errors' (list)
    """
    import json
    import sys
    from datetime import datetime
    import platform
    import ctypes

    try:
        # 구글 시트 매니저 가져오기
        try:
            from wf_googlesheets_manager import get_sheets_manager
        except ImportError as e:
            return {
                "success": False,
                "message": "Google Sheets Manager를 불러올 수 없습니다.",
                "error": str(e),
            }

        # 경로 결정: dev vs release
        if getattr(sys, "frozen", False):
            # 릴리스 모드: %USERPROFILE%\.wf_rpa
            base_dir = Path.home() / ".wf_rpa"
        else:
            # 개발 모드: 앱별 config 폴더 사용
            app_root = Path(sys.argv[0]).resolve().parent
            # 10.rpa 폴더에서 직접 실행되는 경우 사용자 홈폴더 사용
            if app_root.name == "10.rpa" or (app_root.parent.name == "10.rpa" and app_root.name not in ["30.apps", "50.data"]):
                base_dir = Path.home() / ".wf_rpa"
            else:
                # 앱 폴더에서 실행: 앱별 config 폴더 사용
                base_dir = app_root / "config"

        # policy 저장 경로: {base_dir}/{app_name}/policy.json (identity + policy)
        app_policy_path = base_dir / app_name / "policy.json"
        app_policy_path.parent.mkdir(parents=True, exist_ok=True)

        # admin_config 저장 경로: {base_dir}/wf_rpa_config.json
        admin_config_path = base_dir / "wf_rpa_config.json"

        # 구글 시트에서 데이터 가져오기
        sheets_manager = get_sheets_manager(test_mode=False)

        app_policies = sheets_manager.get_app_policies()
        admin_config_data = sheets_manager.get_admin_config_full()

        # 방어적 정규화: None 또는 잘못된 타입 방지
        if not isinstance(app_policies, dict):
            app_policies = {}
        if not isinstance(admin_config_data, dict):
            admin_config_data = {}

        errors = []
        updates = []

        # 1. app_policy 업데이트 (키 정규화/별칭 처리)
        # 시트 키들을 소문자로 정규화하여 조회 안정성 향상
        policies_norm = {}
        try:
            for k, v in (app_policies or {}).items():
                policies_norm[str(k).strip().lower()] = v
        except Exception:
            policies_norm = {}

        # 별칭 정규화 맵 (좌: 들어오는 값, 우: 표준 키)
        # Normalize requested app name to sheet key (lowercase)
        # New canonical mapping: Bom_Exporter, Conversion_Verifier → lower to bom_exporter, conversion_verifier
        alias_norm = {
            "bom2excel": "bom_exporter",
            "bom2excel_exporter": "bom_exporter",
            "bom_exporter": "bom_exporter",
            "bom exporter": "bom_exporter",
            "file_list_check": "conversion_verifier",
        }
        target_key = str(app_name).strip().lower()
        target_key = alias_norm.get(target_key, target_key)

        if isinstance(app_name, str) and target_key in policies_norm:
            try:
                # 기존 파일 읽기 (있으면)
                existing_data = {}
                if app_policy_path.exists():
                    with open(app_policy_path, "r", encoding="utf-8") as f:
                        existing_data = json.load(f)

                # 새 데이터로 업데이트 (병합 구조)
                existing_data["policy"] = policies_norm[target_key]
                existing_data["last_updated"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]
                existing_data["source"] = "google_sheets"
                # identity 섹션 보장
                identity = existing_data.get("identity") if isinstance(existing_data.get("identity"), dict) else {}
                if identity is None:
                    identity = {}
                identity["app_name"] = target_key
                existing_data["identity"] = identity
                # full_version 필드 제거 - 버전은 settings.json에서만 관리

                # 부모 디렉토리가 없으면 생성 (Permission error 방지)
                app_policy_path.parent.mkdir(parents=True, exist_ok=True)

                # 배포 환경: 파일이 숨김 처리되어 있다면 임시로 해제 (Permission denied 방지)
                is_hidden_before = False
                if getattr(sys, "frozen", False) and app_policy_path.exists():
                    try:
                        if platform.system() == "Windows":
                            FILE_ATTRIBUTE_HIDDEN = 0x02
                            attrs = ctypes.windll.kernel32.GetFileAttributesW(str(app_policy_path))
                            if attrs != -1 and (attrs & FILE_ATTRIBUTE_HIDDEN):
                                is_hidden_before = True
                                # 숨김 해제
                                ctypes.windll.kernel32.SetFileAttributesW(
                                    str(app_policy_path), attrs & ~FILE_ATTRIBUTE_HIDDEN
                                )
                                if logger:
                                    logger.debug(f"숨김 파일 쓰기 위해 임시 해제: {app_policy_path}")
                    except Exception as hide_err:
                        if logger:
                            logger.warning(f"숨김 해제 실패 (무시): {hide_err}")

                # 저장
                with open(app_policy_path, "w", encoding="utf-8") as f:
                    json.dump(existing_data, f, ensure_ascii=False, indent=2)

                # 배포 환경: 원래 숨김 파일이었다면 다시 숨김 처리
                if is_hidden_before:
                    try:
                        if platform.system() == "Windows":
                            FILE_ATTRIBUTE_HIDDEN = 0x02
                            attrs = ctypes.windll.kernel32.GetFileAttributesW(str(app_policy_path))
                            if attrs != -1:
                                ctypes.windll.kernel32.SetFileAttributesW(
                                    str(app_policy_path), attrs | FILE_ATTRIBUTE_HIDDEN
                                )
                                if logger:
                                    logger.debug(f"쓰기 완료 후 다시 숨김 처리: {app_policy_path}")
                    except Exception as hide_err:
                        if logger:
                            logger.warning(f"숨김 재설정 실패 (무시): {hide_err}")

                updates.append(f"✅ {target_key} 앱 정책(app_config) 업데이트 완료")
                if logger:
                    logger.info(f"✅ {target_key} 앱 정책(policy.json) 업데이트: {app_policy_path}")
            except Exception as e:
                errors.append(f"❌ {target_key} 앱 정책 저장 실패: {str(e)}")
                if logger:
                    logger.error(f"❌ {target_key} 앱 정책 저장 실패: {e}")
        else:
            errors.append(f"⚠️ 구글 시트에 {target_key} 정책이 없습니다")
            if logger:
                logger.warning(f"⚠️ 구글 시트에 {target_key} 정책이 없습니다")

        # 2. admin_config 업데이트 (email_settings 섹션)
        if admin_config_data:
            try:
                # 기존 설정 읽기
                existing_config = {}
                if admin_config_path.exists():
                    with open(admin_config_path, "r", encoding="utf-8") as f:
                        existing_config = json.load(f)

                # email_settings 업데이트
                # smtp_port 안전 변환
                raw_smtp_port = admin_config_data.get("smtp_port", 587)
                try:
                    smtp_port_val = int(raw_smtp_port)
                except Exception:
                    smtp_port_val = 587

                email_settings = {
                    "email_from": str(admin_config_data.get("email_from", "") or ""),
                    "email_to": str(admin_config_data.get("email_to", "") or ""),
                    "login_key": str(admin_config_data.get("email_login", "") or ""),
                    "smtp_server": str(
                        admin_config_data.get("smtp_server", "smtp.gmail.com") or "smtp.gmail.com"
                    ),
                    "smtp_port": smtp_port_val,
                    "use_local_email_config": True,
                    "enabled": True
                }

                existing_config["email_settings"] = email_settings
                
                # google_sheets 설정도 업데이트 (Sheet ID 등이 변경될 수 있음)
                if "sheet_id_release" in admin_config_data or "sheet_id_dev" in admin_config_data:
                    google_sheets_config = {
                        "sheet_id_release": admin_config_data.get("sheet_id_release", "1bUqpV1vSGwsVeWav-6enZUzaKBTJdxX5eZ737lNh6Ww"),
                        "sheet_id_dev": admin_config_data.get("sheet_id_dev", "1bUqpV1vSGwsVeWav-6enZUzaKBTJdxX5eZ737lNh6Ww"),
                        "sheet_name_registrations": admin_config_data.get("sheet_name_registrations", "registrations"),
                        "scope": [
                            "https://spreadsheets.google.com/feeds",
                            "https://www.googleapis.com/auth/drive"
                        ]
                    }
                    existing_config["google_sheets"] = google_sheets_config
                    
                existing_config["last_updated"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f")[
                    :-3
                ]

                # 저장
                with open(admin_config_path, "w", encoding="utf-8") as f:
                    json.dump(existing_config, f, ensure_ascii=False, indent=2)

                updates.append("✅ 관리자 설정(이메일, Google Sheets) 업데이트 완료")
                if logger:
                    logger.info(f"✅ 관리자 설정 업데이트: {admin_config_path}")
            except Exception as e:
                errors.append(f"❌ 관리자 설정 저장 실패: {str(e)}")
                if logger:
                    logger.error(f"❌ 관리자 설정 저장 실패: {e}")
        else:
            errors.append("⚠️ 구글 시트에 관리자 설정이 없습니다")
            if logger:
                logger.warning("⚠️ 구글 시트에 관리자 설정이 없습니다")

        # 결과 반환
        if errors and not updates:
            return {"success": False, "message": "\n".join(errors), "errors": errors}
        elif errors:
            return {
                "success": True,
                "message": "\n".join(updates + errors),
                "updates": updates,
                "errors": errors,
            }
        else:
            return {"success": True, "message": "\n".join(updates), "updates": updates}

    except Exception as e:
        error_msg = f"정책 동기화 중 오류 발생: {str(e)}"
        if logger:
            logger.error(error_msg)
            import traceback

            logger.error(traceback.format_exc())
        return {"success": False, "message": error_msg, "error": str(e)}


def get_windows_dpi_scale() -> float:
    """Windows DPI 스케일 반환 (100% = 1.0, 150% = 1.5)
    
    tkinter의 실제 화면 크기를 사용하여 DPI 스케일을 계산합니다.
    이 방식은 ctypes보다 안전하고 크로스 플랫폼 호환성이 좋습니다.
    
    Returns:
        float: DPI 스케일 비율 (1.0 = 100%, 1.5 = 150%)
    """
    try:
        import tkinter as tk
        # 임시 숨김 윈도우 생성
        temp_root = tk.Tk()
        temp_root.withdraw()
        
        # 화면의 실제 픽셀 크기
        screen_width_px = temp_root.winfo_screenwidth()
        # 화면의 물리적 크기 (mm)
        screen_width_mm = temp_root.winfo_screenmmwidth()
        
        temp_root.destroy()
        
        # DPI 계산 (mm를 inch로 변환: 1 inch = 25.4 mm)
        if screen_width_mm > 0:
            dpi = screen_width_px / (screen_width_mm / 25.4)
            # 96 DPI가 100% 스케일 (Windows 기본)
            scale = dpi / 96.0
            # 합리적인 범위로 제한 (0.5 ~ 3.0)
            return max(0.5, min(3.0, scale))
    except Exception:
        pass
    
    return 1.0


def apply_dpi_scale_to_ui_settings(
    ui_settings: Dict[str, Any],
    dpi_scale: float | None = None,
    max_height_ratio: float = 0.85
) -> Dict[str, Any]:
    """UI 설정 딕셔너리에 DPI 스케일 적용
    
    Args:
        ui_settings: 기본 UI 설정 딕셔너리 (font_size, window_width 등)
        dpi_scale: DPI 스케일 비율 (None이면 자동 감지)
        max_height_ratio: 화면 높이의 최대 사용 비율 (기본: 0.85)
    
    Returns:
        DPI가 적용된 UI 설정 딕셔너리
    """
    if dpi_scale is None:
        dpi_scale = get_windows_dpi_scale()
    
    # DPI 스케일이 거의 1.0이면 그대로 반환 (성능 최적화)
    if abs(dpi_scale - 1.0) < 0.01:
        return ui_settings.copy()
    
    # 새 딕셔너리 생성 (원본 보존)
    scaled_settings = ui_settings.copy()
    
    # 스케일 적용할 키 목록
    scale_keys = [
        "window_width",
        "window_height",
        "font_size",
        "font_size_bold",
        "font_size_title",
        "padding",
        "button_width",
    ]
    
    for key in scale_keys:
        if key in scaled_settings:
            original_value = scaled_settings[key]
            if isinstance(original_value, (int, float)):
                scaled_settings[key] = int(round(original_value * dpi_scale))
    
    # 화면 높이 제한 적용 (창이 화면을 벗어나지 않도록)
    if "window_height" in scaled_settings:
        try:
            import tkinter as tk
            temp_root = tk.Tk()
            temp_root.withdraw()
            screen_height = temp_root.winfo_screenheight()
            temp_root.destroy()
            
            max_height = int(screen_height * max_height_ratio)
            if scaled_settings["window_height"] > max_height:
                scaled_settings["window_height"] = max_height
        except Exception:
            pass
    
    return scaled_settings


def update_credentials_from_drive(drive_file_id: str, logger=None) -> Dict[str, Any]:
    """구글 드라이브에서 새 크리덴셜 파일을 다운로드하여 교체합니다.

    Args:
        drive_file_id: 구글 드라이브의 크리덴셜 파일 ID
        logger: 로거 객체 (선택사항)

    Returns:
        Dict with 'success' (bool), 'message' (str), 'backup_path' (str, optional)
    """
    try:
        from wf_googlesheets_manager import get_credentials_helper

        creds_helper = get_credentials_helper()
        if not creds_helper:
            return {
                "success": False,
                "message": "크리덴셜 헬퍼를 초기화할 수 없습니다."
            }

        result = creds_helper.update_credentials_from_drive(drive_file_id)

        if logger:
            if result.get("success"):
                logger.info(f"크리덴셜 업데이트 성공: {result.get('message')}")
                if result.get("backup_path"):
                    logger.info(f"백업 파일: {result.get('backup_path')}")
            else:
                logger.error(f"크리덴셜 업데이트 실패: {result.get('message')}")

        return result

    except ImportError as e:
        error_msg = f"wf_googlesheets_manager 모듈을 불러올 수 없습니다: {e}"
        if logger:
            logger.error(error_msg)
        return {"success": False, "message": error_msg}
    except Exception as e:
        error_msg = f"크리덴셜 업데이트 중 오류: {e}"
        if logger:
            logger.error(error_msg)
        return {"success": False, "message": error_msg}


# ==================== 기본 admin 비밀번호 (시트 미연결 시 fallback) ====================
DEFAULT_ADMIN_PASSWORD = "admin2024"


def get_admin_password(logger=None) -> str:
    """구글 시트 admin_config에서 admin_pw를 가져옵니다.

    시트에서 가져오지 못하면 기본값(DEFAULT_ADMIN_PASSWORD)을 반환합니다.

    Args:
        logger: 로거 객체 (선택사항)

    Returns:
        str: admin 비밀번호
    """
    try:
        from wf_googlesheets_manager import get_sheets_manager

        sheets_manager = get_sheets_manager(test_mode=False)
        admin_config = sheets_manager.get_admin_config_full()

        if isinstance(admin_config, dict):
            admin_pw = admin_config.get("admin_pw", "").strip()
            if admin_pw:
                if logger:
                    logger.debug("admin_pw를 Google Sheets에서 로드했습니다.")
                return admin_pw

        if logger:
            logger.warning("admin_config에서 admin_pw를 찾을 수 없어 기본값 사용")
        return DEFAULT_ADMIN_PASSWORD

    except ImportError as e:
        if logger:
            logger.warning(f"wf_googlesheets_manager 불러오기 실패, 기본값 사용: {e}")
        return DEFAULT_ADMIN_PASSWORD
    except Exception as e:
        if logger:
            logger.warning(f"admin_pw 조회 실패, 기본값 사용: {e}")
        return DEFAULT_ADMIN_PASSWORD


__all__ = [
    "get_user_hardware_info",
    "format_info_for_tree",
    "sync_policies_from_sheets",
    "get_windows_dpi_scale",
    "apply_dpi_scale_to_ui_settings",
    "update_credentials_from_drive",
    "get_admin_password",
    "DEFAULT_ADMIN_PASSWORD",
]
