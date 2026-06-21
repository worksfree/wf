import gspread
from google.oauth2.service_account import Credentials

import smtplib

# pandas는 init() 함수에서 필요할 때만 import (lazy loading)
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import os
import argparse
from pathlib import Path
import logging

# 모듈 레벨 로거 (부모에서 주입 가능). 기본은 NullHandler로 안전하게 무시
logger: logging.Logger = logging.getLogger("wf_email")
if not logger.handlers:
    logger.addHandler(logging.NullHandler())


def set_logger(external_logger: logging.Logger):
    global logger
    logger = external_logger


# 구글 시트 접근은 공통 모듈의 인증/설정을 재사용
try:
    from wf_googlesheets_manager import (
        get_sheets_manager,
        get_sheets_config,
        get_credentials_helper,
        CREDENTIALS_FILENAME,
    )

    SHEETS_AUTH_AVAILABLE = True
except Exception:
    SHEETS_AUTH_AVAILABLE = False
    CREDENTIALS_FILENAME = "silver-argon-445712-a0-7092493258f3.json"

now = datetime.now()

email_from = ""
login_key = ""
email_to = ""  # 수신자도 전역 변수로 관리
smtp_server = ""
smtp_port = ""
sheet_name = "admin_config"


def init(dir_to_find_creds=None):
    """관리자 메일 설정을 로컬 파일 또는 구글 시트에서 로드"""
    global email_from, login_key, smtp_server, smtp_port, email_to

    # 0단계: 모든 설정 초기화
    email_from, login_key, smtp_server, smtp_port, email_to = "", "", "", "", ""

    # 1단계: 로컬 설정 파일에서 우선적으로 설정 로드
    try:
        import json

        # 환경별 설정 파일 경로: 개발=앱/config, 배포=사용자 홈/.wf_rpa
        try:
            from wf_credit_manager import WorksFreeManager

            config_file = WorksFreeManager().config_file
        except Exception:
            # 폴백: 사용자 홈
            config_file = Path.home() / ".wf_rpa" / "wf_rpa_config.json"
        logger.debug(f"로컬 설정 파일 확인: {config_file}")

        if config_file.exists():
            with open(config_file, "r", encoding="utf-8") as f:
                config = json.load(f)

            email_settings = config.get("email_settings", {})
            if email_settings:  # email_settings 객체가 존재하면 로컬 설정 시도
                logger.debug("로컬 이메일 설정 로드를 시도합니다.")
                # 빈 문자열도 "없음"으로 처리하여 구글 시트 폴백 가능하게 함
                email_from_local = email_settings.get("email_from", "").strip()
                email_to_local = email_settings.get("email_to", "").strip()
                smtp_server_local = email_settings.get("smtp_server", "").strip()
                smtp_port_val = email_settings.get("smtp_port")
                smtp_port_local = int(smtp_port_val) if smtp_port_val else ""
                login_key_local = email_settings.get("login_key", "").strip()

                # 값이 실제로 있을 때만 전역 변수에 할당 (빈 문자열 무시)
                if email_from_local:
                    email_from = email_from_local
                if email_to_local:
                    email_to = email_to_local
                if smtp_server_local:
                    smtp_server = smtp_server_local
                if smtp_port_local:
                    smtp_port = smtp_port_local
                if login_key_local:
                    login_key = login_key_local

                logger.debug("로컬 파일에서 로드된 설정:")
                logger.debug(f"  email_from: {email_from}")
                logger.debug(f"  email_to: {email_to}")
                logger.debug(f"  smtp_server: {smtp_server}:{smtp_port}")
                logger.debug(f"  login_key 설정됨: {'예' if login_key else '아니오'}")
    except Exception as local_error:
        logger.warning(f"로컬 설정 파일 처리 중 오류 발생: {local_error}")

    # 2단계: 부족한 설정을 구글 시트에서 로드 (새로운 방식)
    # 모든 필수 정보가 로컬에서 로드되지 않았을 경우에만 시도
    settings_loaded_from_sheets = False
    if not all([email_from, login_key, smtp_server, smtp_port, email_to]):
        logger.debug("구글 시트에서 나머지 이메일 설정 로드...")
        if SHEETS_AUTH_AVAILABLE:
            try:
                manager = get_sheets_manager(test_mode=False)
                email_config = manager.get_email_config()

                if email_config:
                    # 로컬 설정에서 설정되지 않은 값들만 구글 시트에서 가져오기
                    if not email_from:
                        email_from = email_config.get("email_from", "").strip()
                    if not email_to:
                        email_to = email_config.get("email_to", "").strip()
                    if not login_key:
                        login_key = email_config.get(
                            "email_login", ""
                        ).strip()  # email_password -> email_login으로 변경
                    if not smtp_server:
                        smtp_server = email_config.get("smtp_server", "smtp.gmail.com").strip()
                    if not smtp_port:
                        smtp_port = int(email_config.get("smtp_port", 587))

                    settings_loaded_from_sheets = True
                    logger.info("✅ 구글 시트에서 이메일 설정 로드 성공")
                else:
                    logger.warning("구글 시트에서 이메일 설정을 가져올 수 없습니다.")
            except Exception as e:
                logger.warning(f"구글 시트 이메일 설정 로드 실패: {e}")

    # 3단계: 여전히 설정이 부족하면 기존 방식으로 폴백 (중앙 설정 사용)
    if not all([email_from, login_key, smtp_server, smtp_port, email_to]):
        logger.debug("기존 방식으로 구글 시트 설정 로드...")
        try:
            import pandas as pd  # 이 경로에서만 pandas 사용 (lazy loading)

            # 구글 시트 설정은 wf_rpa_config.json에서만 로드
            cfg = get_sheets_config()

            # 중앙 자격증명 헬퍼 사용
            creds_helper = get_credentials_helper() if SHEETS_AUTH_AVAILABLE else None
            creds_path = (
                creds_helper.get_google_credentials_path()
                if creds_helper
                else (Path.home() / ".wf_rpa" / CREDENTIALS_FILENAME)
            )

            if not creds_path or not Path(creds_path).exists():
                raise FileNotFoundError(f"자격증명 파일을 찾을 수 없습니다: {creds_path}")

            credentials = Credentials.from_service_account_file(
                str(creds_path), scopes=cfg["SCOPE"]
            )
            client = gspread.authorize(credentials)

            # 폴백 경로에서는 개발 시트를 기본으로 사용
            sheet_id = cfg["SHEET_ID_DEV"]
            sheet = client.open_by_key(sheet_id).worksheet(sheet_name)
            df = pd.DataFrame(sheet.get_all_records())

            enabled_admin = df[df["enabled"] == "TRUE"]

            if len(enabled_admin) == 1:
                if not email_from:
                    email_from = str(enabled_admin.iloc[0]["email_from"]).strip()
                if not email_to:
                    email_to = str(enabled_admin.iloc[0]["email_to"]).strip()
                if not login_key:
                    login_key = str(enabled_admin.iloc[0]["email_login"]).strip()
                if not smtp_server:
                    smtp_server = str(enabled_admin.iloc[0]["smtp_server"]).strip()
                if not smtp_port:
                    smtp_port = int(enabled_admin.iloc[0]["smtp_port"])
                logger.debug(f"기존 방식으로 로드된 설정: {email_from} -> {email_to}")
            elif len(enabled_admin) < 1:
                raise ValueError("어드민으로 설정된 이메일 계정이 없습니다.")
            else:
                raise ValueError("어드민으로 설정된 이메일 계정이 복수입니다.")
        except Exception as e:
            logger.error(f"기존 방식의 구글 시트 설정 로드 실패: {e}")

    # 4단계: 구글 시트에서 로드한 설정을 로컬 파일에 저장 (다음 실행 시 빠른 로드)
    if settings_loaded_from_sheets and all(
        [email_from, login_key, smtp_server, smtp_port, email_to]
    ):
        try:
            import json

            # 환경별 설정 파일 경로: 개발=앱/config, 배포=사용자 홈/.wf_rpa
            try:
                from wf_credit_manager import WorksFreeManager

                config_file = WorksFreeManager().config_file
            except Exception:
                config_file = Path.home() / ".wf_rpa" / "wf_rpa_config.json"

            # 기존 설정 파일 로드 또는 새로 생성
            if config_file.exists():
                with open(config_file, "r", encoding="utf-8") as f:
                    config = json.load(f)
            else:
                config = {}

            # 이메일 설정 업데이트
            config["email_settings"] = {
                "use_local_email_config": True,
                "email_from": email_from,
                "email_to": email_to,
                "smtp_server": smtp_server,
                "smtp_port": smtp_port,
                "login_key": login_key,
            }
            config["last_updated"] = datetime.now().isoformat()

            # 디렉토리 생성 (없는 경우)
            config_file.parent.mkdir(parents=True, exist_ok=True)

            # 설정 파일 저장
            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=2)

            logger.info(f"✅ 이메일 설정을 로컬 파일에 저장했습니다: {config_file}")
            logger.info("   다음 실행부터는 구글 시트 조회 없이 빠르게 로드됩니다.")
        except Exception as save_error:
            logger.warning(f"이메일 설정 로컬 저장 실패 (계속 진행): {save_error}")

    # 5단계: 최종 검증 및 명확한 오류 메시지
    logger.debug("최종 이메일 설정 완료:")
    logger.debug(f"  email_from: {email_from}")
    logger.debug(f"  email_to: {email_to}")
    logger.debug(f"  smtp_server: {smtp_server}:{smtp_port}")
    logger.debug(f"  login_key 설정됨: {'예' if login_key else '아니오'}")

    # 필수 설정 누락 시 명확한 오류 메시지
    if not all([email_from, login_key, smtp_server, smtp_port, email_to]):
        missing = []
        if not email_from:
            missing.append("email_from")
        if not login_key:
            missing.append("login_key")
        if not smtp_server:
            missing.append("smtp_server")
        if not smtp_port:
            missing.append("smtp_port")
        if not email_to:
            missing.append("email_to")

        logger.error("❌ 이메일 설정이 완전하지 않습니다.")
        logger.error(f"   누락된 항목: {', '.join(missing)}")
        logger.error("   해결 방법:")
        logger.error("   1. 구글 시트 'admin_config' 워크시트에 enabled=TRUE인 설정 추가")
        logger.error("   2. 또는 wf_rpa_config.json 파일에 직접 설정 입력")
        logger.error(f"   3. 또는 환경변수 설정: WF_EMAIL_FROM, WF_EMAIL_TO, WF_EMAIL_LOGIN_KEY 등")


def send_email(email_to, subject, body, attachments=None):
    """간단한 이메일 발송 함수 (wf_register.py 호환용)"""
    try:
        # 설정이 아직 로드되지 않았다면 로드
        if not email_from:
            init()

        # mail_send_attach 함수 호출
        mail_send_attach(subject, email_to, body, attachments)
        return True
    except Exception as e:
        logger.error(f"send_email 호출 실패: {e}")
        return False


def test_email_sending(test_email=None):
    """이메일 발송 기능 테스트"""
    try:
        logger.info("📧 이메일 발송 테스트 시작...")

        # 설정 초기화
        init()
        logger.info(f"✅ 이메일 설정 로드 완료")
        logger.info(f"   발신자: {email_from}")
        logger.info(f"   SMTP: {smtp_server}:{smtp_port}")
        logger.info(f"   수신자: {test_email}")

        # 테스트 이메일 주소 설정 (기본값은 관리자 자신)
        test_to = test_email or email_from

        # 테스트 이메일 발송
        result = mail_send_attach(
            title="[WF] 이메일 발송 테스트",
            email_to=test_to,
            body_array="<h3>이메일 발송 테스트</h3><p>이 메일이 정상적으로 수신되었다면 이메일 설정이 올바릅니다.</p><p>테스트 시간: "
            + str(now)
            + "</p>",
        )

        if result:
            logger.info(f"✅ 테스트 이메일 발송 성공: {test_to}")
        else:
            logger.error(f"❌ 테스트 이메일 발송 실패: {test_to}")

        return result

    except Exception as e:
        logger.error(f"❌ 이메일 테스트 실패: {e}")
        import traceback

        traceback.print_exc()
        return False


def set_argv(args_string: str):
    """테스트용 하드코딩된 sys.argv 설정"""
    import sys

    sys.argv = ["wf_email.py"] + args_string.split()


def mail_send_attach(title, email_to, body_array, attachments=None):
    """제목/본문/첨부로 메일 전송"""
    # 수신자 주소가 파라미터로 전달되지 않은 경우, init()으로 로드된 전역 email_to 사용
    recipient = email_to or globals().get("email_to")

    logger.info(f"메일 전송 시작: {title} to {recipient}")
    try:
        logger.debug(f"메일 내용: {body_array}")

        # 이메일 주소 검증
        if not recipient or "@" not in recipient:
            raise ValueError(f"잘못된 받는 사람 이메일 주소: {recipient}")

        if not email_from or "@" not in email_from:
            raise ValueError(f"잘못된 보내는 사람 이메일 주소: {email_from}")

        logger.info(f"SMTP 연결 시도: {smtp_server}:{smtp_port}")
        s = smtplib.SMTP(smtp_server, int(smtp_port))  # 세션 생성 (포트 정수화)
        s.starttls()  # TLS 보안 시작

        logger.info(f"SMTP 로그인 시도: {email_from}")
        s.login(email_from, login_key)  # 로그인 인증

        # Create multipart message
        msg = MIMEMultipart()
        msg["Subject"] = title
        msg["To"] = recipient
        msg["From"] = email_from  # From 헤더 명시적 추가

        # Add body text - UTF-8 인코딩 명시
        email_html = MIMEText(body_array, "html", "utf-8")
        msg.attach(email_html)

        # Add attachments if provided
        if attachments:
            # Convert single attachment to list for consistent handling
            if isinstance(attachments, str):
                attachments = [attachments]

            logger.debug(f"첨부파일 개수: {len(attachments)}")
            for attachment in attachments:
                attachment_path = Path(attachment)
                if attachment_path.exists():
                    logger.debug(f"첨부파일 추가: {attachment}")
                    with open(attachment, "rb") as f:
                        part = MIMEBase("application", "octet-stream")
                        part.set_payload(f.read())
                        encoders.encode_base64(part)
                        part.add_header(
                            "Content-Disposition", f'attachment; filename="{attachment_path.name}"'
                        )
                        msg.attach(part)
                else:
                    logger.warning(f"첨부파일을 찾을 수 없음: {attachment}")
        else:
            logger.debug("첨부파일 없음 (본문만 전송)")

        logger.debug(f'메일 제목: {msg["Subject"]}')
        logger.debug(f"받는 사람: {recipient}")

        # 메일 전송 시도
        s.sendmail(email_from, recipient, msg.as_string())
        s.quit()
        logger.info("메일 전송 성공")
        return True

    except Exception as e:
        logger.error(f"메일 전송 중 오류 발생: {e}")
        logger.error(f"SMTP 서버: {smtp_server}:{smtp_port}")
        logger.error(f"보내는 사람: {email_from}")
        logger.error(f"받는 사람: {recipient}")
        raise


def _run_test(email_from: str | None = None, email_to: str | None = None):
    """안전한 테스트: 실제 사용자에게 메일을 보내지 않음"""
    try:
        # 홈 디렉터리 wf_rpa 경로 기준으로 테스트 수행
        creds_file = Path.home() / ".wf_rpa" / CREDENTIALS_FILENAME
        if creds_file.exists():
            init()
            # 테스트 수신자를 어드민 본인으로 설정 (유출 방지, 개인 메일 하드코딩 제거)
            to_addr = (email_to or email_from).strip()
            if not to_addr:
                raise ValueError("테스트 수신자(email_to/email_from)가 설정되지 않았습니다.")
            # 정보 표시용 로깅
            if email_from and email_from.strip() and email_from.strip() != email_from:
                logger.warning(
                    "요청된 발신자와 관리자 설정 발신자가 다릅니다. 시트의 관리자 계정으로 발송합니다."
                )
            body = f"<h3>WorksFree Mail Test</h3><p>보낸 시각: {now}</p>"
            mail_send_attach("[WF] 이메일 전송 테스트", to_addr, body)
            logger.info(f"✅ 테스트 메일 전송 완료: {to_addr}")
        else:
            # 자격증명 없으면 실제 전송은 건너뜀
            logger.info("자격증명 파일이 없어 실제 메일 전송은 건너뜁니다.")
            logger.info("wf_email 모듈 로드 및 테스트 경로 점검 완료")
        return True
    except Exception as e:
        logger.error(f"❌ 테스트 실패: {e}")
        return False


if __name__ == "__main__":
    # 독립 실행 시 모듈 로거 초기화
    try:
        from wf_log import get_app_logger

        set_logger(get_app_logger("wf_email", console_level=logging.DEBUG))
    except Exception:
        pass

    parser = argparse.ArgumentParser(description="WorksFree 이메일 모듈")
    parser.add_argument("--test", action="store_true", help="메일 전송 테스트 실행")
    parser.add_argument("--from", dest="from_addr", help="발신자 이메일(선택)")
    parser.add_argument("--to", dest="to_addr", help="수신자 이메일(선택)")

    # 기본 테스트 모드로 설정
    set_argv("--test --to insung.lee@worksfree.kr")

    args = parser.parse_args()

    if args.test:
        logger.info("=" * 50)
        logger.info("WorksFree 이메일 모듈 테스트")
        logger.info("=" * 50)

        # 간단한 이메일 발송 테스트
        success = test_email_sending(test_email=args.to_addr)

        if success:
            logger.info("\n🎉 이메일 테스트 성공! 모든 설정이 올바릅니다.")
        else:
            logger.error("\n❌ 이메일 테스트 실패! 설정을 확인해주세요.")
            logger.error("   - Google Sheets의 admin 설정 확인")
            logger.error("   - 자격증명 파일 확인")
            logger.error("   - 네트워크 연결 확인")
    else:
        logger.info("사용법: python wf_email.py --test [--to dest@example.com]")
