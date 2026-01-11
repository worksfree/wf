"""
이메일 초기화 테스트 스크립트
배포 환경에서 빈 설정 파일로 시작할 때의 동작을 시뮬레이션
"""

import sys
from pathlib import Path
import json
import logging

# 로깅 설정
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# 공통 모듈 경로 추가
current_dir = Path(__file__).resolve().parent
if str(current_dir) not in sys.path:
    sys.path.append(str(current_dir))


def create_empty_config():
    """빈 이메일 설정으로 config 파일 생성 (배포 환경 시뮬레이션)"""
    test_config_path = Path.home() / ".wf_rpa" / "test_wf_rpa_config.json"
    test_config_path.parent.mkdir(parents=True, exist_ok=True)

    config = {
        "user_info": {},
        "email_settings": {
            "email_from": "",
            "email_to": "",
            "login_key": "",
            "smtp_server": "smtp.gmail.com",
            "smtp_port": 587,
        },
    }

    with open(test_config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

    print(f"✅ 테스트용 빈 설정 파일 생성: {test_config_path}")
    return test_config_path


def test_email_init_with_empty_config():
    """빈 설정으로 이메일 초기화 테스트"""
    print("\n" + "=" * 60)
    print("테스트: 빈 이메일 설정으로 init() 호출")
    print("=" * 60)

    # 테스트용 빈 설정 파일 생성
    test_config = create_empty_config()

    try:
        import wf_email

        # 로거 설정
        wf_email.set_logger(logging.getLogger("wf_email"))

        # 초기화 시도
        print("\n📧 wf_email.init() 호출 중...")
        wf_email.init()

        # 결과 확인
        print("\n결과:")
        print(f"  email_from: '{wf_email.email_from}'")
        print(f"  email_to: '{wf_email.email_to}'")
        print(f"  login_key: {'설정됨' if wf_email.login_key else '없음'}")
        print(f"  smtp_server: '{wf_email.smtp_server}'")
        print(f"  smtp_port: '{wf_email.smtp_port}'")

        # 검증
        all_set = all(
            [
                wf_email.email_from,
                wf_email.email_to,
                wf_email.login_key,
                wf_email.smtp_server,
                wf_email.smtp_port,
            ]
        )

        if all_set:
            print("\n✅ 성공: 모든 필수 설정이 로드되었습니다.")
            print("   → 구글 시트에서 폴백 로드가 정상 작동했습니다.")
        else:
            print("\n⚠️  경고: 일부 설정이 누락되었습니다.")
            print("   → 구글 시트 접근이 불가능하거나 설정이 없습니다.")
            missing = []
            if not wf_email.email_from:
                missing.append("email_from")
            if not wf_email.email_to:
                missing.append("email_to")
            if not wf_email.login_key:
                missing.append("login_key")
            if not wf_email.smtp_server:
                missing.append("smtp_server")
            if not wf_email.smtp_port:
                missing.append("smtp_port")
            print(f"   누락: {', '.join(missing)}")

    except Exception as e:
        print(f"\n❌ 오류: {e}")
        import traceback

        traceback.print_exc()
    finally:
        # 테스트 파일 정리
        if test_config.exists():
            test_config.unlink()
            print(f"\n🧹 테스트 파일 삭제: {test_config}")


if __name__ == "__main__":
    test_email_init_with_empty_config()
