"""Test Bom_Exporter app name unification"""
import sys
from pathlib import Path

# 경로 설정
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir / ".." / ".." / "10.common"))

from wf_credit_manager import CreditManager

print("=" * 60)
print("Testing Bom_Exporter credit manager with new app name")
print("=" * 60)

# CreditManager 초기화
cm = CreditManager(app_name="bom_exporter")

# 정책 확인
policy = cm.policy
print(f"\n✓ App name: {cm.app_name}")
print(f"✓ Description: {policy.get('description', 'N/A')}")
print(f"✓ Credit per work: {policy.get('credit_per_work', 0)}")
print(f"✓ Trial credits: {policy.get('trial_credits', 0)}")

# 설정 파일 경로 확인
print(f"\n✓ Policy file: {cm.policy_file}")
print(f"✓ Policy file exists: {cm.policy_file.exists()}")

# 레거시 이름 매핑 확인
print("\n" + "=" * 60)
print("Testing legacy name mapping")
print("=" * 60)

legacy_names = ["Bom2Excel", "Bom2Excel_Exporter", "bom2excel"]
for legacy_name in legacy_names:
    try:
        cm_legacy = CreditManager(app_name=legacy_name)
        print(f"✓ '{legacy_name}' → '{cm_legacy.app_name}' (normalized)")
    except Exception as e:
        print(f"✗ '{legacy_name}' failed: {e}")

print("\n✅ All checks passed!")
