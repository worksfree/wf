# -*- coding: utf-8 -*-
"""
앱밸 정책 로딩 테스트
"""
import sys
import os
import json
from pathlib import Path

# 프로젝트 경로 추가
sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "30.apps", "Bom_Exporter")
)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "10.common"))


def test_app_policies_json():
    """app_policies.json에 bom_exporter 설정이 있는지 확인"""
    print("=" * 60)
    print("1. app_policies.json 파일 확인")
    print("=" * 60)

    repo_policy_file = Path(__file__).parents[3] / "10.common" / "app_policies.json"
    print(f"📁 파일 경로: {repo_policy_file}")
    print(f"✅ 파일 존재: {repo_policy_file.exists()}")
    print()

    if repo_policy_file.exists():
        with open(repo_policy_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            policies = data.get("policies", {})
            bom_exporter = policies.get("bom_exporter", {})

            print("📊 bom_exporter 정책:")
            print(json.dumps(bom_exporter, indent=2, ensure_ascii=False))
            print()

            # (참고) 운영 설정 필드는 레포지토리 정책에서 제외됨
            # 아래 항목들은 로컬 정책(.wf_app_policies.json) 또는 사용자 설정에서 관리됨
            required_fields = [
                "memory_threshold_percent",
                "enable_memory_monitor",
                "base_wait_time",
                "seconds_per_10mb",
                "restart_count",
                "consec_timeout_limit",
            ]

            print("ℹ️  운영 설정 필드(옵션) 존재 여부:")
            for field in required_fields:
                exists = field in bom_exporter
                value = bom_exporter.get(field, "N/A")
                status = "✓" if exists else "✗"
                print(f"   {status} {field}: {value}")
            print()

    print("=" * 60)
    print()


def test_local_policy_file():
    """로컬 per-app 정책 파일(신규 표준) 확인 + 레거시 폴백 정보 출력"""
    print("=" * 60)
    print("2. 로컬 앱별 정책 파일 확인 (신규 표준)")
    print("=" * 60)

    wf_rpa_dir = Path.home() / ".wf_rpa"
    app_policy_file = wf_rpa_dir / "bom_exporter" / "credit_policy.json"
    legacy_policy_file = wf_rpa_dir / ".wf_app_policies.json"

    print(f"📁 신규 표준 경로: {app_policy_file}")
    print(f"📁 레거시 경로:   {legacy_policy_file}")
    print(
        f"신규 파일 존재: {app_policy_file.exists()} | 레거시 파일 존재: {legacy_policy_file.exists()}"
    )
    print()

    if app_policy_file.exists():
        with open(app_policy_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            policy = data.get("policy", {}) if isinstance(data, dict) else {}
            print("📊 per-app 로컬 bom_exporter 정책 (credit_policy.json):")
            print(json.dumps(policy, indent=2, ensure_ascii=False))
            print()
            # 메모리 관련 설정만 추출
            memory_settings = {
                "memory_threshold_percent": policy.get("memory_threshold_percent"),
                "enable_memory_monitor": policy.get("enable_memory_monitor"),
                "restart_count": policy.get("restart_count"),
                "consec_timeout_limit": policy.get("consec_timeout_limit"),
            }
            print("🔧 메모리 관련 설정:")
            for key, value in memory_settings.items():
                if value is not None:
                    print(f"   • {key}: {value}")
            print()
    elif legacy_policy_file.exists():
        with open(legacy_policy_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            print(
                "ℹ️ 레거시 루트 정책 파일을 사용 중입니다 (.wf_app_policies.json). 신규 per-app 파일로 마이그레이션을 권장합니다."
            )
            print(
                json.dumps(data, indent=2, ensure_ascii=False)[:500]
                + ("..." if len(json.dumps(data)) > 500 else "")
            )
            print()
    else:
        print("ℹ️  로컬 정책 파일이 없습니다.")
        print("   첫 실행 시 앱이 per-app 정책을 생성하거나, Google Sheets 동기화 후 생성됩니다.")
        print()

    print("=" * 60)
    print()


def test_app_setting_data():
    """app_setting_data.py에서 정책 로드 테스트"""
    print("=" * 60)
    print("3. app_setting_data 정책 로딩 테스트 (현행 구조)")
    print("=" * 60)

    try:
        from app_setting_data import get_config

        print("ℹ️  Config 인스턴스 생성 중...")
        config = get_config()

        print("✅ Config 로드 성공!")
        print()

        # 메모리 관련 설정 출력
        print("📊 현재 적용된 설정:")
        print(f"   • memory_threshold_percent: {config.memory_threshold_percent}%")
        print(f"   • enable_memory_monitor: {config.enable_memory_monitor}")
        print(f"   • base_wait_time: {config.base_wait_time}초")
        print(f"   • seconds_per_10mb: {config.seconds_per_10mb}초")
        print(f"   • restart_count: {config.restart_count}")
        print(f"   • consec_timeout_limit: {config.consec_timeout_limit}")
        print()

        # 우선순위 확인
        print("📋 설정 우선순위 (업데이트):")
        print("   1순위: per-app 정책 (~/.wf_rpa/bom_exporter/credit_policy.json)")
        print("   2순위: 레포지토리 기본값 (10.common/app_policies.json)")
        print("   3순위: 코드 하드코딩 기본값")
        print()

        print("✅ 테스트 완료: 정책 로딩 시스템이 정상 작동합니다.")

    except ImportError as e:
        print(f"❌ app_setting_data import 실패: {e}")
        print("   경로 문제일 수 있습니다.")
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        import traceback

        traceback.print_exc()

    print("=" * 60)
    print()


def test_policy_priority():
    """설정 우선순위 테스트 (per-app 우선)"""
    print("=" * 60)
    print("4. 설정 우선순위 동작 확인 (per-app 정책 우선)")
    print("=" * 60)

    wf_rpa_dir = Path.home() / ".wf_rpa"
    per_app_policy = wf_rpa_dir / "bom_exporter" / "credit_policy.json"
    user_settings = wf_rpa_dir / "bom_exporter" / "settings.json"

    print("📂 설정 파일 존재 여부:")
    print(f"   • per-app 정책: {per_app_policy.exists()}")
    print(f"   • 사용자 설정: {user_settings.exists()}")
    print()

    if per_app_policy.exists():
        print("✅ per-app 정책이 우선 적용됩니다.")
        print("   구글 시트 동기화 또는 레포 기본값 기반으로 생성된 정책이 적용됩니다.")
    elif user_settings.exists():
        print("ℹ️  사용자 설정 파일이 적용됩니다.")
        print("   정책 파일이 없으므로 사용자 JSON 설정 사용.")
    else:
        print("ℹ️  기본값이 적용됩니다.")
        print("   설정 파일이 없으므로 코드 내장 기본값 사용.")

    print()
    print("=" * 60)
    print()


if __name__ == "__main__":
    print()
    print("🚀 앱밸 정책 로딩 시스템 테스트")
    print()

    # 테스트 1: 레포지토리 정책 파일 확인
    test_app_policies_json()

    # 테스트 2: 로컬 정책 파일 확인
    test_local_policy_file()

    # 테스트 3: app_setting_data 로딩 테스트
    test_app_setting_data()

    # 테스트 4: 우선순위 확인
    test_policy_priority()

    print()
    print("🎉 모든 테스트 완료!")
    print()
    print("💡 팁: 구글 시트 정책 동기화는 다음과 같이 수행됩니다:")
    print("   1. WorksFreeManager.refresh_policies_from_sheets() 호출")
    print("   2. 구글 시트에서 정책 데이터 다운로드")
    print("   3. ~/.wf_rpa/{app}/credit_policy.json(예: bom_exporter)에 저장")
    print("   4. 앱 재시작 시 자동으로 정책 적용")
    print()
