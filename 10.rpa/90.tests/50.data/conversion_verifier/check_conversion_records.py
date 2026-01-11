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

        # 모든 레코드 가져오기
        records = purchase_ws.get_all_records(expected_headers=actual_headers)

        print("=" * 80)
        print("conversion_verifier 관련 구매 이력:")
        print("=" * 80)

        found = False
        for idx, rec in enumerate(records, 1):
            app_name = str(rec.get("app_name", "")).strip()
            email = str(rec.get("email", "")).strip()

            if "conversion" in app_name.lower() or "file_list" in app_name.lower():
                found = True
                applied = str(rec.get("applied_date", "")).strip()
                credit = rec.get("purchased_credit", 0)
                trans_id = rec.get("transaction_id", "")

                print(f"\n행 {idx}:")
                print(f"  transaction_id: {trans_id}")
                print(f"  email: {email}")
                print(f"  app_name: {app_name}")
                print(f"  purchased_credit: {credit}")
                print(f"  applied_date: [{applied}] (비어있음: {not applied})")

        if not found:
            print("\n⚠️ conversion_verifier 관련 구매 이력을 찾을 수 없습니다!")
            print("\n모든 앱 목록:")
            apps = set(str(rec.get("app_name", "")).strip() for rec in records)
            for app in sorted(apps):
                if app:
                    print(f"  - {app}")

    except Exception as e:
        print(f"에러: {e}")
        import traceback

        traceback.print_exc()
else:
    print("Google Sheets 연결 실패")
