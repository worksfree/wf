"""
conversion_verifier 앱 기반 credit_changed 플래그 테스트
로컬 config 폴더의 JSON 파일 사용
"""

import sys
import os
from pathlib import Path
import json

# 경로 설정
repo_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(repo_root / "10.common"))

# conversion_verifier config 경로 (표준화된 dev 경로 사용)
CONFIG_DIR = Path(__file__).parent / "config" / "conversion_verifier"
CREDIT_FILE = CONFIG_DIR / "credit_history.json"


def print_section(title, char="="):
    """섹션 구분선"""
    print(f"\n{char*60}")
    print(f"  {title}")
    print(f"{char*60}")


def _wait_or_auto(prompt_text: str):
    """Wait for user input unless running in auto/non-interactive mode.

    Auto mode triggers when either:
    - env var `WF_TEST_AUTO` == "1"
    - stdin is not a TTY (e.g., running under pytest capture)
    """
    auto_env = os.environ.get("WF_TEST_AUTO", "0") == "1"
    non_tty = False
    try:
        non_tty = not sys.stdin.isatty()
    except Exception:
        non_tty = True
    if auto_env or non_tty:
        print(f"[AUTO] {prompt_text}")
        return
    input(prompt_text)


def read_credit_data():
    """크레딧 데이터 읽기"""
    if CREDIT_FILE.exists():
        with open(CREDIT_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def write_credit_data(data):
    """크레딧 데이터 쓰기"""
    with open(CREDIT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def show_status():
    """현재 상태 표시"""
    data = read_credit_data()
    if data:
        print(f"\n📊 현재 상태:")
        print(f"  credit_changed: {data.get('credit_changed')}")
        print(f"  current_credits: {data.get('current_credits')}")
        print(f"  trial_credits: {data.get('trial_credits')}")
        print(f"  purchased_credits: {data.get('purchased_credits')}")
        print(f"  last_synced: {data.get('last_synced')}")
        print(f"  last_updated: {data.get('last_updated')}")
        return data
    else:
        print("❌ 크레딧 파일이 없습니다.")
        return None


def set_flag(value):
    """credit_changed 플래그 설정"""
    data = read_credit_data()
    if data:
        old_value = data.get("credit_changed", False)
        data["credit_changed"] = value
        write_credit_data(data)
        print(f"✅ credit_changed: {old_value} → {value}")
        return True
    return False


def simulate_credit_usage(amount=10):
    """크레딧 사용 시뮬레이션"""
    data = read_credit_data()
    if data:
        current = data.get("current_credits", 0)
        if current >= amount:
            data["current_credits"] = current - amount
            data["credit_changed"] = True
            data["lifetime_usage"] = data.get("lifetime_usage", 0) + amount

            # usage_history 추가
            from datetime import datetime

            usage_entry = {
                "timestamp": datetime.now().isoformat(),
                "amount": amount,
                "description": "테스트 크레딧 사용",
            }
            data["usage_history"] = data.get("usage_history", [])
            data["usage_history"].append(usage_entry)

            write_credit_data(data)
            print(f"✅ 크레딧 사용: {amount} (잔액: {current} → {current - amount})")
            print(f"   credit_changed: False → True")
            return True
        else:
            print(f"❌ 크레딧 부족: 현재 {current}, 필요 {amount}")
            return False
    return False


def simulate_sync_success():
    """동기화 성공 시뮬레이션"""
    data = read_credit_data()
    if data:
        if data.get("credit_changed", False):
            from datetime import datetime

            data["credit_changed"] = False
            data["last_synced"] = datetime.now().isoformat()
            write_credit_data(data)
            print(f"✅ 동기화 성공 시뮬레이션")
            print(f"   credit_changed: True → False")
            print(f"   last_synced: {data['last_synced']}")
            return True
        else:
            print(f"ℹ️ 동기화 불필요 (credit_changed=False)")
            return False
    return False


def test_scenario_1():
    """시나리오 1: 앱 시작 시 동기화 (credit_changed=True)"""
    print_section("시나리오 1: 앱 시작 시 동기화")

    print("\n[1단계] 초기 상태 (이전 세션에서 미동기화 상태)")
    set_flag(True)
    show_status()

    _wait_or_auto("\n👉 이제 conversion_verifier 앱을 실행하세요...")
    _wait_or_auto("   앱 시작 시 로그에서 '🔄 앱 시작: credit_changed=True' 확인")
    _wait_or_auto("   앱을 종료한 후 [Enter]를 누르세요...")

    print("\n[2단계] 앱 실행 후 상태")
    data = show_status()

    if data and not data.get("credit_changed"):
        print("\n✅ 테스트 성공: 앱 시작 시 동기화가 실행되었습니다!")
        print("   - credit_changed가 False로 변경됨")
        print("   - last_synced가 업데이트됨")
    else:
        print("\n⚠️ 확인 필요: credit_changed가 여전히 True입니다.")
        print("   - 동기화 조건을 만족하지 못했거나")
        print("   - 동기화가 실패했을 수 있습니다.")


def test_scenario_2():
    """시나리오 2: 크레딧 사용 → 종료 시 동기화"""
    print_section("시나리오 2: 크레딧 사용 → 종료 시 동기화")

    print("\n[1단계] 초기 상태 (credit_changed=False)")
    set_flag(False)
    show_status()

    print("\n[2단계] 크레딧 사용 시뮬레이션")
    simulate_credit_usage(10)
    show_status()

    _wait_or_auto("\n👉 이제 conversion_verifier 앱을 실행하세요...")
    _wait_or_auto("   앱에서 작업을 수행하거나, 그냥 종료하세요...")
    _wait_or_auto("   앱 종료 시 로그에서 '🔄 앱 종료 시 크레딧 동기화' 확인")
    _wait_or_auto("   [Enter]를 눌러 결과를 확인하세요...")

    print("\n[3단계] 앱 종료 후 상태")
    data = show_status()

    if data and not data.get("credit_changed"):
        print("\n✅ 테스트 성공: 앱 종료 시 동기화가 실행되었습니다!")
    else:
        print("\n⚠️ 확인 필요: credit_changed가 여전히 True입니다.")


def test_scenario_3():
    """시나리오 3: 크레딧 사용 없이 종료"""
    print_section("시나리오 3: 크레딧 사용 없이 종료")

    print("\n[1단계] 초기 상태 (credit_changed=False)")
    set_flag(False)
    show_status()

    _wait_or_auto("\n👉 이제 conversion_verifier 앱을 실행하세요...")
    _wait_or_auto("   아무 작업도 하지 말고 바로 종료하세요...")
    _wait_or_auto("   로그에 동기화 관련 메시지가 없어야 합니다.")
    _wait_or_auto("   [Enter]를 눌러 결과를 확인하세요...")

    print("\n[2단계] 앱 종료 후 상태")
    data = show_status()

    if data and not data.get("credit_changed"):
        print("\n✅ 테스트 성공: 불필요한 동기화가 실행되지 않았습니다!")
    else:
        print("\n⚠️ 확인 필요: credit_changed가 True로 변경되었습니다.")


def reset_test_data():
    """테스트 데이터 초기화"""
    print_section("테스트 데이터 초기화")

    data = {
        "created_at": "2025-01-01T00:00:00.000",
        "last_updated": "2025-01-01T00:00:00.000",
        "last_synced": None,
        "lifetime_usage": 0,
        "credit_changed": False,
        "trial_credits": 2000,
        "purchased_credits": 0,
        "current_credits": 2000,
        "purchase_history": [],
        "usage_history": [],
        "applied_purchase_ids": [],
    }

    write_credit_data(data)
    print("✅ 테스트 데이터가 초기화되었습니다.")
    show_status()


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("🧪 conversion_verifier credit_changed 플래그 테스트")
    print("=" * 60)
    print(f"\n📍 테스트 파일: {CREDIT_FILE}")

    while True:
        print("\n" + "-" * 60)
        print("테스트 시나리오:")
        print("  1. 앱 시작 시 동기화 (credit_changed=True)")
        print("  2. 크레딧 사용 → 종료 시 동기화")
        print("  3. 크레딧 사용 없이 종료 (동기화 불필요)")
        print("  4. 현재 상태만 확인")
        print("  5. credit_changed 플래그 수동 설정")
        print("  6. 크레딧 사용 시뮬레이션")
        print("  7. 동기화 성공 시뮬레이션")
        print("  8. 테스트 데이터 초기화")
        print("  0. 종료")

        try:
            choice = input("\n선택 (0-8): ").strip()

            if choice == "0":
                print("\n👋 테스트 종료")
                break
            elif choice == "1":
                test_scenario_1()
            elif choice == "2":
                test_scenario_2()
            elif choice == "3":
                test_scenario_3()
            elif choice == "4":
                show_status()
            elif choice == "5":
                value = input("True/False? (t/f): ").strip().lower()
                set_flag(value in ["t", "true", "1"])
                show_status()
            elif choice == "6":
                amount = input("사용할 크레딧 (기본 10): ").strip()
                amount = int(amount) if amount else 10
                simulate_credit_usage(amount)
                show_status()
            elif choice == "7":
                simulate_sync_success()
                show_status()
            elif choice == "8":
                reset_test_data()
            else:
                print("❌ 잘못된 선택")

        except KeyboardInterrupt:
            print("\n\n👋 테스트 종료")
            break
        except Exception as e:
            print(f"❌ 오류 발생: {e}")
            import traceback

            traceback.print_exc()

    print("\n" + "=" * 60)
