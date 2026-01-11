import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "10.common"))

from wf_credit_manager import WorksFreeManager

# 현재 등록된 사용자 정보 확인
wf_manager = WorksFreeManager()
user_info = wf_manager.get_user_info()

print("=" * 60)
print("현재 등록된 사용자 정보:")
print("=" * 60)
for key, value in user_info.items():
    print(f"{key}: {value}")
print("=" * 60)

# 이메일 확인
user_email = user_info.get("user_email") or user_info.get("email") or user_info.get("user_mail")
print(f"\n사용 중인 이메일: {user_email}")
