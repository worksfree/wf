import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "10.common"))

from wf_googlesheets_manager import get_sheets_manager

print("=" * 80)
print("conversion_verifier 구매 이력의 applied_date 초기화")
print("=" * 80)

# Google Sheets 매니저 초기화
sheets_manager = get_sheets_manager(test_mode=True)

if sheets_manager and sheets_manager.gc:
    config = sheets_manager._load_config()
    sheet_id = config["SHEET_ID_TEST"]

    try:
        purchase_ws = sheets_manager.gc.open_by_key(sheet_id).worksheet("credit_purchase_log")

        # 헤더 정보
        headers = purchase_ws.row_values(1)
        actual_headers = [h for h in headers if h.strip()]

        # applied_date 컬럼 찾기
        applied_date_col = None
        for i, header in enumerate(headers, 1):
            if header == "applied_date":
                applied_date_col = i
                break

        if not applied_date_col:
            print("❌ applied_date 컬럼을 찾을 수 없습니다.")
            sys.exit(1)

        print(f"applied_date 컬럼 위치: {applied_date_col}")

        # 모든 레코드 가져오기
        records = purchase_ws.get_all_records(expected_headers=actual_headers)

        # conversion_verifier 행 찾기
        cleared_count = 0
        for row_num, rec in enumerate(records, 2):  # 2부터 시작 (헤더 제외)
            app_name = str(rec.get("app_name", "")).strip()
            applied_date = str(rec.get("applied_date", "")).strip()

            if "conversion" in app_name.lower() and applied_date:
                transaction_id = rec.get("transaction_id", "")
                print(f"\n행 {row_num}: {transaction_id}")
                print(f"  applied_date 지우기: [{applied_date}] → []")

                # applied_date 지우기
                purchase_ws.update_cell(row_num, applied_date_col, "")
                cleared_count += 1

        print(f"\n✅ {cleared_count}개 행의 applied_date를 초기화했습니다.")

    except Exception as e:
        print(f"❌ 에러: {e}")
        import traceback

        traceback.print_exc()
else:
    print("❌ Google Sheets 연결 실패")
