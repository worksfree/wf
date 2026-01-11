import sys, os
import logging
import re
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from uuid import getnode
from datetime import datetime, timedelta
import psutil
# import getmac  # MAC 주소 사용 안 함
import random
import platform
import socket
import wmi
import json
from pathlib import Path

# 모듈 레벨 로거 (부모에서 주입 가능). 기본은 NullHandler로 안전하게 무시
logger: logging.Logger = logging.getLogger("wf_license")
if not logger.handlers:
    logger.addHandler(logging.NullHandler())


def set_logger(external_logger: logging.Logger):
    """부모 애플리케이션에서 로거를 주입할 때 사용"""
    global logger
    logger = external_logger


def _get_timestamp() -> str:
    """표준화된 타임스탬프 반환: 2025-10-14T12:15:20.492 (밀리초 3자리)"""
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]


sheet_name = ""


def check_admin(sheet_name="admin"):
    """관리자 정보 확인 (중앙 설정/자격증명 사용)"""
    try:
        from wf_googlesheets_manager import get_sheets_config, get_credentials_helper

        cfg = get_sheets_config()
        creds_path = get_credentials_helper().get_google_credentials_path()
        if not creds_path or not creds_path.exists():
            raise FileNotFoundError(f"자격증명 파일을 찾을 수 없습니다: {creds_path}")
        creds = Credentials.from_service_account_file(str(creds_path), scopes=cfg["SCOPE"])
        client = gspread.authorize(creds)
        sheet_id = cfg["SHEET_ID_PROD"]
        sheet = client.open_by_key(sheet_id).worksheet(sheet_name)
    except Exception as e:
        logger.error(f"관리자 시트 접근 실패: {e}")
        raise
    df = pd.DataFrame(sheet.get_all_records())
    logger.info("관리자 시트 로드 완료")
    logger.debug(df.to_string())
    return df


def register_trial_license_with_hwid(user_email, verification_code, hw_info):
    """하드웨어 정보 기반 체험판 라이선스 등록 (로컬 저장)"""
    try:
        logger.info("체험판 라이선스 등록 시작")
        logger.debug(f"  이메일: {user_email}")
        logger.debug(f"  인증코드: {verification_code}")
        logger.debug(f"  CPU ID: {hw_info.get('cpu_id', 'N/A')}")
        logger.debug(f"  메인보드 ID: {hw_info.get('mainboard_id', 'N/A')}")
        logger.debug(f"  하드웨어 지문: {hw_info.get('fingerprint', 'N/A')[:16]}...")

        # 홈 디렉토리 설정 파일 경로
        config_file = Path.home() / ".wf_rpa" / "wf_rpa_config.json"

        # 기존 설정 로드 또는 새로 생성
        if config_file.exists():
            with open(config_file, "r", encoding="utf-8") as f:
                config = json.load(f)
        else:
            config = {}

        # 체험판 크레딧은 설정에서 로드 (기본값 10000)
        # 주의: 이 함수는 app_name을 모르므로 기본값만 사용
        # 실제 크레딧은 각 앱의 WorksFreeManager가 policy.json에서 로드
        trial_credits = 10000  # 기본값 (각 앱은 자체 policy.json 참조)

        # 사용자 정보 저장
        config["user_info"] = {
            "email": user_email,
            "verification_code": verification_code,
            "cpu_id": hw_info.get("cpu_id", ""),
            "mainboard_id": hw_info.get("mainboard_id", ""),
            "hardware_fingerprint": hw_info.get("fingerprint", ""),
            "registration_date": _get_timestamp(),
            "license_type": "trial",
                "trial_credits": trial_credits,  # 각 앱은 policy.json에서 실제 값 로드
            "used_credits": 0,
        }

        # 실행 상태 초기화
        config["execution_status"] = {
            "is_running": False,
            "current_app": None,
            "pid": None,
            "start_time": None,
        }

        # 설정 파일 저장
        config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

        logger.info(f"설정 파일 저장 완료: {config_file}")
        return True

    except Exception as e:
        logger.exception(f"라이선스 등록 실패: {e}")
        return False


def register_license(email, hw_info=None, verification_code=None, trial=False):
    """하드웨어 정보 기반 라이선스 등록 함수

    Args:
        email: 사용자 이메일
        hw_info: 하드웨어 정보 딕셔너리 (cpu_id, mainboard_id, fingerprint)
        verification_code: 인증코드 (체험판용)
        trial: 체험판 여부
    """
    logger.info(f"라이선스 등록 시도: 이메일={email}, 체험판={trial}")

    if not hw_info:
        return "[오류] 하드웨어 정보가 제공되지 않았습니다."

    logger.debug(f"  CPU ID: {hw_info.get('cpu_id', 'N/A')}")
    logger.debug(f"  메인보드 ID: {hw_info.get('mainboard_id', 'N/A')}")
    logger.debug(f"  하드웨어 지문: {hw_info.get('fingerprint', 'N/A')[:16]}...")

    if trial:
        try:
            from pathlib import Path

            # 수정된 경로: .wf_rpa 폴더 내의 wf_rpa_config.json
            config_file = Path.home() / ".wf_rpa" / "wf_rpa_config.json"

            logger.debug(f"설정 파일 경로: {config_file}")

            # 기존 설정 로드 또는 새로 생성
            if config_file.exists():
                with open(config_file, "r", encoding="utf-8") as f:
                    config = json.load(f)
            else:
                config = {}

            # 중복 확인 (기존 등록된 하드웨어 정보와 비교)
            existing_user = config.get("user_info", {})
            if existing_user and existing_user.get("status") == "active":
                # 이메일 중복 확인
                if existing_user.get("email") == email:
                    return f"[중복] {email}은 이미 등록되어 있어 체험판 사용이 불가합니다."

                # 하드웨어 정보 중복 확인
                if (
                    existing_user.get("cpu_id") == hw_info.get("cpu_id")
                    or existing_user.get("mainboard_id") == hw_info.get("mainboard_id")
                    or existing_user.get("hardware_fingerprint") == hw_info.get("fingerprint")
                ):
                    return f"[중복] 이 컴퓨터는 이미 등록되어 있어 체험판 사용이 불가합니다."

            today = datetime.now()

            # 체험판 크레딧은 설정에서 로드 (기본값 10000)
            # 실제 크레딧은 각 앱의 policy.json에서 로드됨
            trial_credits = 10000  # 기본값 (각 앱은 자체 policy.json 참조)

            # 사용자 정보 저장
            config["user_info"] = {
                "email": email,
                "verification_code": verification_code or "LOCAL_TRIAL",
                "cpu_id": hw_info.get("cpu_id", ""),
                "mainboard_id": hw_info.get("mainboard_id", ""),
                "hardware_fingerprint": hw_info.get("fingerprint", ""),
                "registration_date": _get_timestamp(),
                "license_type": "trial",
                "trial_credits": trial_credits,  # 각 앱은 policy.json에서 실제 값 로드
                "used_credits": 0,
                "status": "active",
            }

            # 실행 상태 초기화
            config["execution_status"] = {
                "is_running": False,
                "current_app": None,
                "pid": None,
                "start_time": None,
            }

            # 설정 파일 저장
            config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=2)

            logger.info(f"설정 파일 저장 완료: {config_file}")
            return f"[신규] {email}의 체험판 라이선스가 등록되었습니다."

        except Exception as e:
            logger.exception(f"라이선스 등록 실패: {e}")
            return f"[오류] 라이선스 등록 중 오류가 발생했습니다: {str(e)}"

    else:
        # 정식 라이선스 - 구글 시트에서 확인/등록 (중앙 설정/자격증명 사용)
        try:
            from wf_googlesheets_manager import get_sheets_config, get_credentials_helper

            cfg = get_sheets_config()
            creds_path = get_credentials_helper().get_google_credentials_path()
            if not creds_path or not creds_path.exists():
                raise FileNotFoundError(f"자격증명 파일을 찾을 수 없습니다: {creds_path}")
            creds = Credentials.from_service_account_file(str(creds_path), scopes=cfg["SCOPE"])
            client = gspread.authorize(creds)
            sheet_id = cfg["SHEET_ID_PROD"]
            sheet_name = "hwinfo"  # 하드웨어 정보용 새 시트

            try:
                sheet = client.open_by_key(sheet_id).worksheet(sheet_name)
            except:
                # 시트가 없으면 생성
                spreadsheet = client.open_by_key(sheet_id)
                sheet = spreadsheet.add_worksheet(title=sheet_name, rows=1000, cols=10)
                # 헤더 추가
                headers = [
                    "email",
                    "cpu_id",
                    "mainboard_id",
                    "hardware_fingerprint",
                    "사용권한",
                    "라이선스유형",
                    "등록일",
                    "상태",
                    "비고",
                ]
                sheet.append_row(headers)

            df = pd.DataFrame(sheet.get_all_records())

            # 이메일 또는 하드웨어 정보로 기존 라이선스 확인
            matched_rows = df[
                (df["email"] == email)
                | (df["cpu_id"] == hw_info.get("cpu_id", ""))
                | (df["mainboard_id"] == hw_info.get("mainboard_id", ""))
                | (df["hardware_fingerprint"] == hw_info.get("fingerprint", ""))
            ]

            if not matched_rows.empty:
                row = matched_rows.iloc[0]

                if row["사용권한"] != "Y":
                    return f"[차단] 등록은 되었으나 사용권한이 없습니다: {email}"

                return f"[유효] {email} 의 라이선스가 확인되었습니다."

            return f"[거부] 등록되지 않은 사용자입니다. 정식 라이선스를 발급받아야 합니다: {email}"

        except Exception as e:
            logger.error(f"정식 라이선스 확인 실패: {e}")
            return f"[오류] 라이선스 확인 중 오류가 발생했습니다: {str(e)}"


def check_license_with_hwid(email, hardware_fingerprint, logger=None):
    """하드웨어 지문 기반 라이선스 확인 (MAC 주소 대신 fingerprint 사용)"""
    sheet_id = "13OuY3j6nzUxOfIT07LiU264OImtkxrdPDEdRW8eRTv8"
    url = "https://docs.google.com/spreadsheets/d/"
    post_pix = "/export?format=csv"

    msg = ""
    df = pd.read_csv(f"{url}{sheet_id}{post_pix}")
    logger_to_use = logger if hasattr(logger, "debug") else globals().get("logger")
    
    if logger_to_use:
        logger_to_use.debug(f"사용자 정보: 이메일={email}, HWID={hardware_fingerprint[:16]}...")
    
    user_row = df[df["email"] == email]
    
    if logger_to_use:
        logger_to_use.debug(f"사용자 행: {user_row}")

    if not user_row.empty:
        if user_row["사용권한"].iloc[0] == "Y":
            # hardware_fingerprint 컬럼이 있는지 확인
            if "hardware_fingerprint" in user_row.columns:
                registered_hwid = user_row["hardware_fingerprint"].iloc[0]
                if str(registered_hwid).strip() == hardware_fingerprint:
                    msg = "Y"
                else:
                    msg = f"사용자({email})의 하드웨어 지문({hardware_fingerprint[:16]}...)이 등록된 지문({str(registered_hwid)[:16]}...)과 다릅니다."
            else:
                # 새 컬럼이 없으면 승인 (마이그레이션 기간)
                if logger_to_use:
                    logger_to_use.warning("hardware_fingerprint 컬럼이 없습니다. 임시로 승인합니다.")
                msg = "Y"
        else:
            msg = f"유효한 라이선스가 없어 사용할 수 없습니다."
    else:
        msg = f"사용자 정보: 이메일={email}은 존재하지 않는 이메일입니다."

    return msg


# ===== DEPRECATED: MAC 주소 기반 라이선스 체크 (사용 안 함) =====
# def check_license(email, mac, logger=None):
#     """라이선스 확인 (기존 함수 - DEPRECATED: check_license_with_hwid 사용)"""
#     sheet_id = "13OuY3j6nzUxOfIT07LiU264OImtkxrdPDEdRW8eRTv8"
#     url = "https://docs.google.com/spreadsheets/d/"
#     post_pix = "/export?format=csv"
#
#     msg = ""
#     df = pd.read_csv(f"{url}{sheet_id}{post_pix}")
#     # 기존 서명 호환을 위해 logger 매개변수는 유지하지만 모듈 로거 사용
#     logger_to_use = logger if hasattr(logger, "debug") else globals().get("logger")
#     if logger_to_use:
#         logger_to_use.debug(f"사용자 정보: 이메일={email}, MAC={mac}")
#     user_row = df[df["email"] == email]
#     if logger_to_use:
#         logger_to_use.debug(f"사용자 행: {user_row}")
#
#     if not user_row.empty:
#         if user_row["사용권한"].iloc[0] == "Y":
#             wired_mac = user_row["mac(wired)"].iloc[0] if "mac(wired)" in user_row.columns else ""
#             wireless_mac = (
#                 user_row["mac(wireless)"].iloc[0] if "mac(wireless)" in user_row.columns else ""
#             )
#
#             if (
#                 str(wired_mac).upper() == mac["mac(wired)"]
#                 or str(wireless_mac).upper() == mac["mac(wireless)"]
#             ):
#                 msg = "Y"
#             else:
#                 msg = f"사용자({email})의 컴퓨터 맥주소({mac})가 승인된 맥주소(유선: {wired_mac}, 무선: {wireless_mac})와 다릅니다."
#         else:
#             msg = f"유효한 라이선스가 없어 사용할 수 없습니다."
#     else:
#         msg = f"사용자 정보: 이메일={email}은 존재하지 않는 이메일입니다."
#
#     return msg


# ===== DEPRECATED: MAC 주소 기반 테스트 함수들 (사용 안 함) =====
# # 테스트를 반복하기 위해 테스트 시트의 원본을 백업하는 함수
# def backup_sheet(sheet):
#     """현재 시트의 전체 데이터를 백업합니다."""
#     data = sheet.get_all_values()  # 헤더 포함 전체 데이터
#     return data
#
#
# # 테스트를 반복하기 위해 테스트 시트의 원본을 복원하는 함수들
# def restore_sheet(sheet, backup_data):
#     if sheet.title != "test":
#         raise ValueError("복원할 시트는 'test' 시트여야 합니다.")
#     """백업된 데이터를 시트에 복원합니다."""
#     # 기존 데이터를 모두 삭제
#     sheet.clear()
#     # 백업 데이터로 전체를 덮어쓰기
#     sheet.update("A1", backup_data)
#
#
# def setup_test_data(sheet):
#     """테스트용 원본 데이터를 시트에 설정합니다."""
#     # 헤더 설정
#     headers = [
#         "이메일",
#         "맥 주소(유선)",
#         "맥 주소(무선)",
#         "사용권한",
#         "라이선스 유형",
#         "라이선스 종류",
#         "등록일",
#         "만료일",
#     ]
#
#     # 테스트 데이터 설정
#     test_data = [
#         headers,
#         [
#             "alice@test.com",
#             "AA:BB:CC:11:22:33",
#             "AA:BB:CC:11:22:44",
#             "Y",
#             "정식",
#             "12개월",
#             "2025-01-01",
#             "2026-01-01",
#         ],
#         [
#             "bob@test.com",
#             "BB:CC:DD:22:33:44",
#             "AA:BB:CC:11:22:66",
#             "Y",
#             "체험판",
#             "체험판",
#             "2025-07-09",
#             "2025-07-16",
#         ],
#         [
#             "charlie@test.com",
#             "CC:DD:EE:33:44:55",
#             "CC:DD:EE:33:44:56",
#             "N",
#             "정식",
#             "1개월",
#             "2024-12-31",
#             "2025-01-31",
#         ],
#         [
#             "dave@test.com",
#             "DD:EE:FF:44:55:66",
#             "DD:EE:FF:44:55:67",
#             "Y",
#             "정식",
#             "0.25개월",
#             "2023-12-31",
#             "2023-12-31",
#         ],
#         [
#             "eve@test.com",
#             "EE:FF:00:55:66:77",
#             "AA:BB:CC:11:22:99",
#             "Y",
#             "체험판",
#             "체험판",
#             "2025-07-01",
#             "2025-07-08",
#         ],
#         [
#             "newuser2@test.com",
#             "11:22:33:44:55:66",
#             "AA:BB:CC:11:22:00",
#             "Y",
#             "체험판",
#             "체험판",
#             "2025-06-30",
#             "2025-07-07",
#         ],
#     ]
#
#     # 시트 초기화 및 데이터 설정
#     sheet.clear()
#     sheet.update("A1", test_data)
#
#     return test_data


# # wf_mac.py 활용할 것. 이건 사용하지 말고...
# def get_mac():
#     """현재 컴퓨터의 MAC 주소를 가져옵니다."""
#     mac_address = '-'.join(re.findall('..', '%012x' % getnode())).upper()   # MAC 주소를 12자리 16진수로 변환하여 하이픈(-)으로 구분
#     return mac_address

# # wf_mac.py 활용할 것. 이건 사용하지 말고...
# def get_network_interfaces():
#     """네트워크 인터페이스 목록을 가져오는 함수"""
#     interfaces = psutil.net_if_addrs()
#     return interfaces
#
#
# def run_comprehensive_tests():
#     """
#     🔧 새로운 테스트 함수: 맥주소 교차 검색 테스트 포함
#     """
#     # Google Sheets 연결
#     scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
#     creds = Credentials.from_service_account_file(
#         r"D:\10.worksfree\10.rpa_script\20.common\utils\silver-argon-445712-a0-4ce021aa64be.json",
#         scopes=scope,
#     )
#     client = gspread.authorize(creds)
#     sheet_id = "13OuY3j6nzUxOfIT07LiU264OImtkxrdPDEdRW8eRTv8"
#     sheet_name = "test"
#     sheet = client.open_by_key(sheet_id).worksheet(sheet_name)
#
#     # 원본 데이터 설정 및 백업
#     original_data = setup_test_data(sheet)
#
#     # 🔧 강화된 테스트 케이스: 맥주소 교차 검색 테스트 포함
#     test_cases = [
#         # (email, mac_wired, mac_wireless, trial, expected_result_type, description)
#         (
#             "alice@test.com",
#             "AA:BB:CC:11:22:33",
#             "AA:BB:CC:11:22:55",
#             False,
#             "[유효]",
#             "정식 라이선스, 유효",
#         ),
#         ("bob@test.com", "BB:CC:DD:22:33:44", "AA:BB:CC:11:22:66", False, "[만료]", "체험판, 만료"),
#         (
#             "charlie@test.com",
#             "CC:DD:EE:33:44:55",
#             "AA:BB:CC:11:22:77",
#             False,
#             "[차단]",
#             "정식 라이선스, 사용권한 N",
#         ),
#         (
#             "dave@test.com",
#             "DD:EE:FF:44:55:66",
#             "AA:BB:CC:11:22:88",
#             False,
#             "[만료]",
#             "정식 라이선스, 만료됨",
#         ),
#         ("eve@test.com", "EE:FF:00:55:66:77", "AA:BB:CC:11:22:99", False, "[만료]", "체험판, 만료"),
#         # 🔧 맥주소 교차 검색 테스트 케이스들
#         (
#             "newuser1@test.com",
#             "AA:BB:CC:11:22:33",
#             "NEW:NEW:NEW:NEW:NEW",
#             True,
#             "[중복]",
#             "유선 MAC이 기존 alice 유선 MAC과 중복",
#         ),
#         (
#             "newuser2@test.com",
#             "NEW:NEW:NEW:NEW:NEW",
#             "AA:BB:CC:11:22:44",
#             True,
#             "[중복]",
#             "무선 MAC이 기존 alice 무선 MAC과 중복",
#         ),
#         (
#             "newuser3@test.com",
#             "AA:BB:CC:11:22:99",
#             "NEW:NEW:NEW:NEW:NEW",
#             True,
#             "[중복]",
#             "유선 MAC이 기존 eve 무선 MAC과 중복",
#         ),
#         (
#             "newuser4@test.com",
#             "NEW:NEW:NEW:NEW:NEW",
#             "BB:CC:DD:22:33:44",
#             True,
#             "[중복]",
#             "무선 MAC이 기존 bob 유선 MAC과 중복",
#         ),
#         (
#             "alice@test.com",
#             "NEW:NEW:NEW:NEW:NEW",
#             "NEW:NEW:NEW:NEW:NEW",
#             True,
#             "[중복]",
#             "이메일 중복",
#         ),
#         (
#             "newuser5@test.com",
#             "NEW:NEW:NEW:NEW:NEW",
#             "NEW:NEW:NEW:NEW:NEW",
#             True,
#             "[신규]",
#             "완전 신규 사용자",
#         ),
#         # 정식 라이선스 체크 테스트
#         (
#             "unknown@test.com",
#             "99:88:77:66:55:44",
#             "AA:BB:CC:11:22:14",
#             False,
#             "[거부]",
#             "등록되지 않은 사용자",
#         ),
#     ]
#
#     logger.info("=" * 100)
#     logger.info("🔧 강화된 라이선스 등록 시스템 테스트 (맥주소 교차 검색 포함)")
#     logger.info("=" * 100)
#
#     for i, (email, mac_wired, mac_wireless, trial, expected, description) in enumerate(
#         test_cases, 1
#     ):
#         logger.info(f"\n테스트 케이스 {i}: {description}")
#         logger.info(f"  - 이메일: {email}")
#         logger.info(f"  - MAC 유선: {mac_wired}")
#         logger.info(f"  - MAC 무선: {mac_wireless}")
#         logger.info(f"  - 체험판: {trial}")
#         logger.info(f"  - 예상 결과: {expected}")
#
#         try:
#             # 각 테스트 전에 원본 데이터 복원
#             restore_sheet(sheet, original_data)
#
#             # 테스트 실행
#             result = register_license(email, mac_wired, mac_wireless, trial)
#             logger.info(f"  - 실제 결과: {result}")
#
#             # 결과 검증
#             if expected in result:
#                 logger.info(f"  - ✅ 성공: 예상 결과와 일치")
#             else:
#                 logger.warning(f"  - ❌ 실패: 예상 결과와 다름")
#
#         except Exception as e:
#             logger.error(f"  - ❌ 에러 발생: {str(e)}")
#
#     # 테스트 완료 후 원본 데이터 복원
#     restore_sheet(sheet, original_data)
#     logger.info("\n" + "=" * 100)
#     logger.info("테스트 완료 및 원본 데이터 복원됨")
#     logger.info("=" * 100)
#
#
# # 기존 테스트 케이스들 (참고용)
# test_cases = [
#     ("alice@test.com", "AA:BB:CC:11:22:33", "AA:BB:CC:11:22:55"),  # 정식, 유효
#     ("bob@test.com", "BB:CC:DD:22:33:44", "AA:BB:CC:11:22:66"),  # 체험판, 만료
#     ("charlie@test.com", "CC:DD:EE:33:44:55", "AA:BB:CC:11:22:77"),  # 정식, 갱신 필요
#     ("dave@test.com", "DD:EE:FF:44:55:66", "AA:BB:CC:11:22:88"),  # 정식, 만료됨
#     ("eve@test.com", "EE:FF:00:55:66:77", "AA:BB:CC:11:22:99"),  # 체험판, 유효
#     ("eve@test.com", "11:22:33:44:55:66", "AA:BB:CC:11:22:11"),  # 이메일 중복 → 기존 사용자
#     ("newuser1@test.com", "EE:FF:00:55:66:77", "AA:BB:CC:11:22:12"),  # 이메일은 신규이나 MAC 중복
#     ("newuser2@test.com", "11:22:33:44:55:66", "AA:BB:CC:11:22:00"),  # 완전 신규 → 체험판 허용
# ]
#
#
# def run_original_tests():
#     """기존 테스트 (참고용)"""
#     for email, mac_wired, mac_wireless in test_cases:
#         df_license = random.choice([True, False])  # trial 값을 boolean으로 수정
#         result = register_license(email, mac_wired, mac_wireless, df_license)
#         logger.info(f"{email}, {mac_wired}, {mac_wireless}, {df_license} → {result}")


if __name__ == "__main__":
    check_admin()
    # # 테스트를 위한 시트 이름 설정, 배포본은 "trial" sheet에 기록함
    # sheet_name = 'trial_test'
    # # 강화된 테스트 실행
    # # run_comprehensive_tests()

    # import wf_log as wfl
    # log = wfl.set_logger('wf_license', 10)

    # # lic = check_license('insung.lee1973@gmail.com', logger, get_mac())
    # register_trial_license('wf1@gmail.com', '24-FB-E3-61-80-E1', '70-15-FB-88-21-51')# 정상
    # register_trial_license('wf2@gmail.com', '24-FB-E3-61-80-22', '70-15-FB-88-21-52')# 정상
    # register_trial_license('wf3@gmail.com', '24-FB-E3-61-80-E3', '70-15-FB-88-21-53')# 정상
    # register_trial_license('wf4@gmail.com', '24-FB-E3-61-80-E3', '70-15-FB-88-21-53')# 유/무선 맥 중복
    # register_trial_license('wf5@gmail.com', '24-FB-E3-61-80-E4', '70-15-FB-88-21-53')# 무선 맥 중복
    # register_trial_license('wf6@gmail.com', '24-FB-E3-61-80-E5', '70-15-FB-88-21-54')# 정상
    # register_trial_license('wf7@gmail.com', '24-FB-E3-61-80-E5', '70-15-FB-88-21-55')# 유선 맥 중복
    # register_trial_license('wf3@gmail.com', '24-FB-E3-61-80-E7', '70-15-FB-88-21-57')# 이메일 중복
    # register_trial_license('wf9@gmail.com', '24-FB-E3-61-80-E8', '70-15-FB-88-21-58')# 정상
    # register_trial_license('wf0@gmail.com', '24-FB-E3-61-80-E9', '70-15-FB-88-21-59')# 정상
    # # 1, 2, 3, 6, 9, 0 정상
