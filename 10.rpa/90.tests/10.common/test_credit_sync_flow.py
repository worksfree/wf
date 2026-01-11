"""
크레딧 동기화 플로우 테스트 스크립트
- 앱 시작 시 credit_changed=True면 동기화
- 크레딧 사용 성공 시 credit_changed=True 설정
- 앱 종료 시 credit_changed=True면 동기화
"""

import sys
import os
from pathlib import Path

# 경로 설정
sys.path.insert(0, str(Path(__file__).parent))
os.chdir(Path(__file__).parent)

from wf_credit_manager import CreditManager, WorksFreeManager
import json


def print_section(title):
    """섹션 구분선 출력"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def get_credit_data(app_name):
    """크레딧 데이터 직접 읽기"""
    wf_manager = WorksFreeManager()
    credit_file = wf_manager.wf_rpa_dir / app_name / "credit_history.json"

    if credit_file.exists():
        with open(credit_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def set_credit_changed_flag(app_name, value=True):
    """credit_changed 플래그 강제 설정 (테스트용)"""
    wf_manager = WorksFreeManager()
    credit_file = wf_manager.wf_rpa_dir / app_name / "credit_history.json"

    if credit_file.exists():
        try:
            # 숨김 속성 임시 해제 (Windows)
            try:
                wf_manager._remove_hidden_attribute(credit_file)
            except:
                pass

            with open(credit_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            data["credit_changed"] = value

            with open(credit_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            print(f"✅ credit_changed = {value} 설정 완료")
            return True

        except PermissionError as e:
            print(f"❌ 권한 오류: {e}")
            print(f"   VSCode를 관리자 권한으로 실행하거나,")
            print(f"   수동으로 파일을 편집하세요: {credit_file}")
            return False

    print(f"❌ 크레딧 파일 없음: {credit_file}")
    return False


def test_startup_sync(app_name="bom2excel"):
    """시나리오 1: 앱 시작 시 동기화 테스트"""
    print_section(f"시나리오 1: {app_name} 시작 시 동기화")

    # 1. credit_changed=True로 설정 (이전 세션에서 사용했지만 동기화 안 된 상황 시뮬레이션)
    print("\n[준비] credit_changed=True 설정 (이전 세션 시뮬레이션)...")
    set_credit_changed_flag(app_name, True)

    # 2. CreditManager 초기화 (앱 시작 시뮬레이션)
    print(f"\n[실행] {app_name} CreditManager 초기화...")
    print("  → __init__() 실행 → _sync_on_startup() 자동 호출됨")

    credit_manager = CreditManager(app_name)

    # 3. 결과 확인
    print("\n[결과] credit_changed 플래그 확인...")
    data = get_credit_data(app_name)
    if data:
        flag = data.get("credit_changed", False)
        last_synced = data.get("last_synced", "N/A")
        print(f"  credit_changed: {flag}")
        print(f"  last_synced: {last_synced}")

        if flag:
            print("  ⚠️ 동기화 실패 또는 변경사항 없음 (flag 여전히 True)")
        else:
            print("  ✅ 동기화 성공! (flag가 False로 변경됨)")


def test_usage_and_exit_sync(app_name="bom2excel"):
    """시나리오 2: 크레딧 사용 → 종료 시 동기화 테스트"""
    print_section(f"시나리오 2: {app_name} 사용 후 종료 시 동기화")

    # 1. CreditManager 초기화
    print(f"\n[실행] {app_name} CreditManager 초기화...")
    credit_manager = CreditManager(app_name)

    # 2. 초기 상태 확인
    print("\n[초기 상태]")
    status = credit_manager.get_sync_status()
    print(f"  needs_sync: {status.get('needs_sync')}")
    print(f"  credit_changed: {status.get('credit_changed')}")
    print(f"  current_credits: {status.get('current_credits')}")

    # 3. 크레딧 사용 시뮬레이션 (50크레딧)
    print("\n[크레딧 사용] 50크레딧 사용 시도...")
    result = credit_manager.deduct_credits(50, description="테스트 작업")

    if result["success"]:
        print(f"  ✅ 크레딧 사용 성공")
        print(f"  remaining: {result.get('remaining_credits')}")
    else:
        print(f"  ❌ 크레딧 사용 실패: {result.get('message')}")

    # 4. 사용 후 상태 확인
    print("\n[사용 후 상태]")
    status = credit_manager.get_sync_status()
    print(f"  needs_sync: {status.get('needs_sync')}")
    print(f"  credit_changed: {status.get('credit_changed')}")
    print(f"  current_credits: {status.get('current_credits')}")

    # 5. 종료 시 동기화 시뮬레이션
    print("\n[종료 시 동기화] check_and_sync_credits() 호출...")
    if status.get("needs_sync"):
        sync_result = credit_manager.check_and_sync_credits()
        print(f"  동기화 결과: {sync_result}")
    else:
        print("  ℹ️ 동기화 필요 없음 (credit_changed=False)")

    # 6. 최종 상태 확인
    print("\n[최종 상태]")
    data = get_credit_data(app_name)
    if data:
        print(f"  credit_changed: {data.get('credit_changed')}")
        print(f"  last_synced: {data.get('last_synced', 'N/A')}")


def test_no_usage_exit(app_name="bom2excel"):
    """시나리오 3: 크레딧 사용 없이 종료 (동기화 불필요)"""
    print_section(f"시나리오 3: {app_name} 사용 없이 종료")

    # 1. credit_changed=False로 초기화
    print("\n[준비] credit_changed=False 설정...")
    set_credit_changed_flag(app_name, False)

    # 2. CreditManager 초기화
    print(f"\n[실행] {app_name} CreditManager 초기화...")
    credit_manager = CreditManager(app_name)

    # 3. 상태 확인
    print("\n[상태 확인]")
    status = credit_manager.get_sync_status()
    print(f"  needs_sync: {status.get('needs_sync')}")
    print(f"  credit_changed: {status.get('credit_changed')}")

    # 4. 종료 시 동기화 체크
    print("\n[종료 시 동기화 체크]")
    if status.get("needs_sync"):
        print("  ⚠️ 동기화 필요 (예상치 못함)")
    else:
        print("  ✅ 동기화 불필요 (정상)")


if __name__ == "__main__":
    print("\n" + "🧪 크레딧 동기화 플로우 테스트".center(60, "="))

    app_name = "bom2excel"  # 테스트할 앱

    # 시나리오 선택
    print("\n테스트 시나리오:")
    print("  1. 앱 시작 시 동기화 (credit_changed=True인 경우)")
    print("  2. 크레딧 사용 → 종료 시 동기화")
    print("  3. 크레딧 사용 없이 종료 (동기화 불필요)")
    print("  4. 전체 시나리오 실행")

    choice = input("\n실행할 시나리오 번호 (1-4): ").strip()

    if choice == "1":
        test_startup_sync(app_name)
    elif choice == "2":
        test_usage_and_exit_sync(app_name)
    elif choice == "3":
        test_no_usage_exit(app_name)
    elif choice == "4":
        test_startup_sync(app_name)
        input("\n[Enter]를 눌러 다음 시나리오로...")
        test_usage_and_exit_sync(app_name)
        input("\n[Enter]를 눌러 다음 시나리오로...")
        test_no_usage_exit(app_name)
    else:
        print("❌ 잘못된 선택")

    print("\n" + "=" * 60)
    print("테스트 완료")
    print("=" * 60)
