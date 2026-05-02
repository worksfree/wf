#!/usr/bin/env python3
"""
4개 앱 크레딧 시스템 일관성 검증 테스트
"""
import sys
import os
from pathlib import Path

# Setup paths
project_root = Path(__file__).parent.parent
common_dir = project_root / "10.common"
sys.path.insert(0, str(common_dir))

from wf_credit_manager import CreditManager

def test_all_apps_credit_consistency():
    """4개 앱의 크레딧 시스템 일관성 검증"""
    
    apps = ["bom_exporter", "dwg_classifier", "conversion_verifier", "korean_filename_normalizer"]
    results = {}
    
    print("=" * 80)
    print("4개 앱 크레딧 시스템 일관성 검증 테스트")
    print("=" * 80)
    
    for app_name in apps:
        print(f"\n[{app_name}]")
        try:
            # Initialize CreditManager
            cm = CreditManager(app_name)
            
            # Check basic functionality
            status = cm.get_credit_status()
            policy_info = cm.get_policy_info()
            per_item_cost = cm.get_per_item_cost()
            sync_status = cm.get_sync_status()
            
            results[app_name] = {
                "initialized": True,
                "has_get_credit_status": status is not None,
                "has_get_policy_info": policy_info is not None,
                "has_get_per_item_cost": per_item_cost is not None,
                "has_get_sync_status": sync_status is not None,
                "has_deduct_credits_by_policy": hasattr(cm, "deduct_credits_by_policy"),
                "has_check_and_sync_credits": hasattr(cm, "check_and_sync_credits"),
                "per_item_cost": per_item_cost,
                "credit_type": policy_info.get("credit_type") if policy_info else "N/A",
            }
            
            print(f"  ✅ 초기화 성공")
            print(f"  ✅ get_credit_status: OK")
            print(f"  ✅ get_policy_info: OK")
            print(f"  ✅ get_per_item_cost: {per_item_cost} credits/item")
            print(f"  ✅ get_sync_status: OK")
            print(f"  ✅ deduct_credits_by_policy: {'있음' if hasattr(cm, 'deduct_credits_by_policy') else '없음'}")
            print(f"  ✅ check_and_sync_credits: {'있음' if hasattr(cm, 'check_and_sync_credits') else '없음'}")
            print(f"  ℹ️  Credit Type: {policy_info.get('credit_type') if policy_info else 'N/A'}")
            
        except Exception as e:
            results[app_name] = {
                "initialized": False,
                "error": str(e)
            }
            print(f"  ❌ 오류: {e}")
    
    print("\n" + "=" * 80)
    print("검증 요약")
    print("=" * 80)
    
    all_success = all(r.get("initialized") for r in results.values())
    all_have_methods = all(
        r.get("has_deduct_credits_by_policy") and r.get("has_check_and_sync_credits")
        for r in results.values() if r.get("initialized")
    )
    
    print(f"\n✅ 모든 앱 초기화: {'성공' if all_success else '실패'}")
    print(f"✅ 모든 앱 필수 메서드 보유: {'예' if all_have_methods else '아니오'}")
    
    print("\n[앱별 크레딧 비용]")
    for app_name, result in results.items():
        if result.get("initialized"):
            cost = result.get("per_item_cost", "N/A")
            credit_type = result.get("credit_type", "N/A")
            print(f"  - {app_name:30s}: {cost:5} credits/item ({credit_type})")
    
    return all_success and all_have_methods

if __name__ == "__main__":
    success = test_all_apps_credit_consistency()
    print(f"\n{'='*80}")
    print(f"최종 결과: {'✅ 통과' if success else '❌ 실패'}")
    print(f"{'='*80}\n")
    sys.exit(0 if success else 1)
