#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Google Sheets Header Update Script

This script updates Google Sheets headers to add app_version column.

Affected sheets:
- registrations: add uc_first_app_version column
- credit_sync: add app_version column
- credit_usage_log: add app_version column

Usage:
    python update_sheets_headers.py
"""

import sys
from pathlib import Path

# Add common module path
common_path = Path(__file__).resolve().parent.parent / "10.common"
sys.path.insert(0, str(common_path))

from wf_googlesheets_manager import get_sheets_manager


def update_headers():
    """Update Google Sheets headers"""
    print("=" * 60)
    print("Google Sheets Header Update Script")
    print("=" * 60)

    try:
        print("\n[INFO] Connecting to Google Sheets...")
        sheets_manager = get_sheets_manager(test_mode=True)

        if not sheets_manager or not sheets_manager.gc:
            print("[ERROR] Failed to connect to Google Sheets")
            return False

        print("[OK] Connected to Google Sheets")

        config = sheets_manager._load_config()
        sheet_id = config.get("SHEET_ID_DEV") or config.get("SHEET_ID_RELEASE")

        if not sheet_id:
            print("[ERROR] Sheet ID not found")
            return False

        spreadsheet = sheets_manager.gc.open_by_key(sheet_id)
        print(f"[OK] Opened spreadsheet: {spreadsheet.title}")

        # 1. registrations sheet
        print("\n" + "-" * 40)
        print("1. registrations sheet header update")
        print("-" * 40)
        try:
            reg_ws = spreadsheet.worksheet("registrations")
            current_headers = reg_ws.row_values(1)
            print(f"   Current: {current_headers}")

            new_headers = [
                "user_email",
                "user_name",
                "user_phone",
                "user_email_consent",
                "uc_hw_fingerprint",
                "uc_hw_cpuinfo",
                "uc_hw_mbinfo",
                "uc_hw_storageinfo",
                "uc_first_app",
                "uc_first_app_version",
                "reg_time_local",
                "reg_time_utc",
                "reg_tz_name",
            ]

            if current_headers != new_headers:
                reg_ws.update("A1", [new_headers])
                print("   [OK] registrations header updated")
            else:
                print("   [INFO] registrations header already up to date")
        except Exception as e:
            print(f"   [WARN] registrations update failed: {e}")

        # 2. credit_sync sheet
        print("\n" + "-" * 40)
        print("2. credit_sync sheet header update")
        print("-" * 40)
        try:
            sync_ws = spreadsheet.worksheet("credit_sync")
            current_headers = sync_ws.row_values(1)
            print(f"   Current: {current_headers}")

            new_headers = [
                "user_email",
                "app_name",
                "app_version",
                "hardware_fingerprint",
                "trial_credits",
                "purchased_credits",
                "last_usage",
                "last_usage_time_local",
                "last_usage_time_utc",
                "last_usage_tz_name",
                "last_sync_utc",
            ]

            if current_headers != new_headers:
                sync_ws.update("A1", [new_headers])
                print("   [OK] credit_sync header updated")
            else:
                print("   [INFO] credit_sync header already up to date")
        except Exception as e:
            print(f"   [WARN] credit_sync update failed: {e}")

        # 3. credit_usage_log sheet
        print("\n" + "-" * 40)
        print("3. credit_usage_log sheet header update")
        print("-" * 40)
        try:
            usage_ws = spreadsheet.worksheet("credit_usage_log")
            current_headers = usage_ws.row_values(1)
            print(f"   Current: {current_headers}")

            new_headers = [
                "event_time_local",
                "event_time_utc",
                "event_tz_name",
                "user_email",
                "app_name",
                "app_version",
                "hardware_fingerprint",
                "usage_amount",
                "file_count",
                "per_item_cost",
                "description",
            ]

            if current_headers != new_headers:
                usage_ws.update("A1", [new_headers])
                print("   [OK] credit_usage_log header updated")
            else:
                print("   [INFO] credit_usage_log header already up to date")
        except Exception as e:
            print(f"   [WARN] credit_usage_log update failed: {e}")

        print("\n" + "=" * 60)
        print("[DONE] All header updates completed")
        print("=" * 60)
        print("\n[NOTE] Existing data column positions may need manual adjustment.")

        return True

    except Exception as e:
        print(f"\n[ERROR] Exception: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = update_headers()
    sys.exit(0 if success else 1)
