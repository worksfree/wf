import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "10.common"))

from wf_googlesheets_manager import get_sheets_manager

# Google Sheets 매니저 초기화
sheets_manager = get_sheets_manager(test_mode=True)

if sheets_manager and sheets_manager.gc:
    config = sheets_manager._load_config()
    sheet_id = config["SHEET_ID_TEST"]

    try:
        purchase_ws = sheets_manager.gc.open_by_key(sheet_id).worksheet("credit_purchase_log")

        # 실제 헤더
        header_row = purchase_ws.row_values(1)
        actual_headers = [h for h in header_row if h.strip()]

        print("=" * 80)
        print("새로운 헤더 구조:")
        print("=" * 80)
        for idx, header in enumerate(actual_headers, 1):
            print(f"{idx:2d}. {header}")
        print("=" * 80)

        # 모든 레코드 가져오기
        records = purchase_ws.get_all_records(expected_headers=actual_headers)

        print(f"\n총 레코드 수: {len(records)}")

        # conversion_verifier 데이터 찾기
        print("\nconversion_verifier 관련 구매 이력:")
        print("=" * 80)

        for idx, rec in enumerate(records, 1):
            app_name = str(rec.get("app_name", "")).strip()

            if "conversion" in app_name.lower():
                print(f"\n행 {idx}:")
                print(f"  transaction_id: {rec.get('transaction_id', '')}")
                print(f"  email: {rec.get('email', '')}")
                print(f"  app_name: {app_name}")
                print(f"  purchase_date: {rec.get('purchase_date', '')}")
                print(f"  base_credit: {rec.get('base_credit', 'N/A')}")
                print(f"  bonus_credit: {rec.get('bonus_credit', 'N/A')}")
                print(f"  total_credit: {rec.get('total_credit', 'N/A')}")
                print(f"  promo_code: {rec.get('promo_code', '')}")
                print(f"  applied_date: [{rec.get('applied_date', '')}]")
                print(f"  status: {rec.get('status', '')}")

    except Exception as e:
        print(f"에러: {e}")
        import traceback

        traceback.print_exc()
else:
    print("Google Sheets 연결 실패")
