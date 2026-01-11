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

        # 첫 번째 행(헤더) 가져오기
        headers = purchase_ws.row_values(1)

        print("=" * 60)
        print("credit_purchase_log 시트의 실제 헤더:")
        print("=" * 60)
        for idx, header in enumerate(headers, 1):
            print(f"{idx}. [{header}] (길이: {len(header)})")
        print("=" * 60)

        # 모든 레코드 미리보기 (첫 3개)
        print("\n데이터 미리보기 (첫 3개 행):")
        all_values = purchase_ws.get_all_values()
        for idx, row in enumerate(all_values[:4], 1):  # 헤더 + 3개 행
            print(f"행 {idx}: {row}")

    except Exception as e:
        print(f"에러: {e}")
else:
    print("Google Sheets 연결 실패")
