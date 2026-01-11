import sys
import logging
from pathlib import Path

# 경로 설정
sys.path.insert(0, r"D:\drive_files\10.worksfree\10.rpa\10.common")

# 로거 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("credit_usage_log_test")

print("\n" + "="*80)
print("  credit_usage_log 테스트")
print("="*80 + "\n")

try:
    from wf_credit_manager import CreditManager
    from wf_googlesheets_manager import get_sheets_manager
    
    # 1. Google Sheets Manager 초기화
    print("[1] Google Sheets Manager 초기화...")
    sheets_manager = get_sheets_manager(test_mode=False)
    
    if not sheets_manager.gc:
        print(" Google Sheets 연결 실패!")
        sys.exit(1)
    
    print(" Google Sheets 연결 성공\n")
    
    # 2. 테스트용 사용 로그 데이터 준비
    print("[2] 테스트 사용 로그 추가 중...")
    test_email = "test_usage_log@example.com"
    test_app = "test_app"
    test_hwid = "TEST-HWID-12345"
    
    # append_usage_log 메서드 직접 호출
    result = sheets_manager.append_usage_log(
        user_email=test_email,
        app_name=test_app,
        hardware_fingerprint=test_hwid,
        usage_amount=5.0,
        file_count=10,
        per_item_cost=0.5,
        description="테스트 크레딧 사용",
        timestamp_override=None  # 현재 시각 사용
    )
    
    if result:
        print(" 사용 로그 추가 성공")
    else:
        print(" 사용 로그 추가 실패")
    
    print("\n" + "="*80)
    print("  테스트 결과")
    print("="*80)
    print("\n credit_usage_log 시트에 다음 데이터가 추가되었습니다:")
    print(f"  - 사용자: {test_email}")
    print(f"  - 앱: {test_app}")
    print(f"  - 사용량: 5.0 크레딧")
    print(f"  - 파일 수: 10개")
    print(f"  - 단가: 0.5 크레딧/파일")
    print(f"  - 설명: 테스트 크레딧 사용")
    print("\n Google Sheets의 'credit_usage_log' 시트를 확인하세요.")
    print("="*80 + "\n")
    
except Exception as e:
    print(f"\n 테스트 중 오류 발생: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
