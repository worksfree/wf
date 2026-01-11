"""
credit_changed 플래그 수동 설정 유틸리티
실제 앱 테스트를 위해 플래그를 강제로 설정합니다.
"""

import sys
import os
from pathlib import Path

# 경로 설정
sys.path.insert(0, str(Path(__file__).parent))

from wf_credit_manager import WorksFreeManager
import json


def set_credit_changed(app_name, value=True):
    """credit_changed 플래그 설정"""
    try:
        wf_manager = WorksFreeManager()
        credit_file = wf_manager.wf_rpa_dir / app_name / "credit_history.json"

        if not credit_file.exists():
            print(f"❌ 크레딧 파일이 존재하지 않습니다: {credit_file}")
            print(f"   앱을 먼저 한 번 실행해주세요.")
            return False

        # 파일이 숨김 속성이면 임시로 해제
        try:
            wf_manager._remove_hidden_attribute(credit_file)
        except:
            pass

        # 파일 읽기
        with open(credit_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        old_value = data.get("credit_changed", False)
        data["credit_changed"] = value

        # 파일 쓰기
        with open(credit_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"✅ {app_name} credit_changed 플래그 변경 완료")
        print(f"   {old_value} → {value}")
        print(f"\n📍 파일 위치: {credit_file}")

        return True

    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback

        traceback.print_exc()
        return False


def show_status(app_name):
    """현재 상태 표시"""
    try:
        wf_manager = WorksFreeManager()
        credit_file = wf_manager.wf_rpa_dir / app_name / "credit_history.json"

        if not credit_file.exists():
            print(f"❌ 크레딧 파일이 존재하지 않습니다: {credit_file}")
            return

        with open(credit_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        print(f"\n📊 {app_name} 현재 상태:")
        print(f"   credit_changed: {data.get('credit_changed', False)}")
        print(
            f"   current_credits: {data.get('trial_credits', 0) + data.get('purchased_credits', 0)}"
        )
        print(f"   last_synced: {data.get('last_synced', 'N/A')}")
        print(f"   last_updated: {data.get('last_updated', 'N/A')}")

    except Exception as e:
        print(f"❌ 오류 발생: {e}")


if __name__ == "__main__":
    print("=" * 60)
    print("🔧 credit_changed 플래그 수동 설정 유틸리티")
    print("=" * 60)

    apps = ["bom_exporter", "dwg_classifier", "conversion_verifier", "korean_filename_normalizer"]

    print("\n사용 가능한 앱:")
    for i, app in enumerate(apps, 1):
        print(f"  {i}. {app}")

    try:
        choice = input("\n앱 번호 선택 (1-4): ").strip()
        app_name = apps[int(choice) - 1]

        print("\n작업 선택:")
        print("  1. credit_changed = True 설정")
        print("  2. credit_changed = False 설정")
        print("  3. 현재 상태만 확인")

        action = input("\n작업 번호 (1-3): ").strip()

        if action == "1":
            set_credit_changed(app_name, True)
        elif action == "2":
            set_credit_changed(app_name, False)
        elif action == "3":
            pass

        show_status(app_name)

    except (ValueError, IndexError):
        print("❌ 잘못된 입력입니다.")
    except KeyboardInterrupt:
        print("\n\n👋 취소됨")

    print("\n" + "=" * 60)
