#!/usr/bin/env python3
"""
크레딧 차감 기능 테스트
"""
import sys
import os
from pathlib import Path

# Setup paths
project_root = Path(__file__).parent.parent
common_dir = project_root / "10.common"
sys.path.insert(0, str(common_dir))

from wf_credit_manager import CreditManager

def test_credit_deduction():
    """크레딧 차감 테스트"""
    
    apps = ["bom_exporter", "dwg_classifier", "conversion_verifier", "korean_filename_normalizer"]
    
    print("=" * 80)
    print("4개 앱 크레딧 차감 기능 테스트")
    print("=" * 80)
    
    all_passed = True
    
    for app_name in apps:
        print(f"\n[{app_name}]")
        try:
            # Initialize CreditManager
            cm = CreditManager(app_name)
            
            # Get initial status
            initial_status = cm.get_credit_status()
            initial_credits = initial_status.get("remaining_credits", 0)
            per_item_cost = cm.get_per_item_cost()
            
            print(f"  초기 크레딧: {initial_credits}")
            print(f"  아이템당 비용: {per_item_cost}")
            
            # Test deduct_credits_by_policy with 3 items
            print(f"  테스트: 3개 아이템 처리 ({per_item_cost * 3} 크레딧 차감)")
            result = cm.deduct_credits_by_policy(
                item_count=3,
                description=f"[테스트] {app_name} 3개 아이템 처리"
            )
            
            if result.get("success"):
                print(f"  ✅ 차감 성공")
                print(f"     - 차감량: {result.get('deducted_amount')}")
                print(f"     - 잔여: {result.get('remaining_credits')}")
                
                # Verify deduction amount
                expected_deduction = per_item_cost * 3
                actual_deduction = result.get("deducted_amount", 0)
                
                if actual_deduction == expected_deduction:
                    print(f"  ✅ 차감량 검증 통과 (예상: {expected_deduction}, 실제: {actual_deduction})")
                else:
                    print(f"  ❌ 차감량 불일치 (예상: {expected_deduction}, 실제: {actual_deduction})")
                    all_passed = False
                    
                # Check sync status
                sync_status = cm.get_sync_status()
                needs_sync = sync_status.get("needs_sync", False)
                print(f"  ℹ️  동기화 필요: {needs_sync}")
                
            else:
                print(f"  ❌ 차감 실패: {result.get('message')}")
                all_passed = False
                
        except Exception as e:
            print(f"  ❌ 오류: {e}")
            all_passed = False
    
    print("\n" + "=" * 80)
    print(f"최종 결과: {'✅ 모든 테스트 통과' if all_passed else '❌ 일부 테스트 실패'}")
    print("=" * 80 + "\n")
    
    return all_passed

if __name__ == "__main__":
    success = test_credit_deduction()
    sys.exit(0 if success else 1)
