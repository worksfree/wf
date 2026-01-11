# -*- coding: utf-8 -*-
"""
Sync app names into Google Sheets 'app_policy' sheet.

- Discovers canonical app names from the workspace
- Ensures each app exists as a row in app_policy (by app_name)
- Appends missing rows with minimal fields (app_name, optionally enabled)

Usage:
    python scripts/sync_app_policy_app_names.py            # production sheet
    python scripts/sync_app_policy_app_names.py --test     # test sheet

This script uses the same Google Sheets credentials/config as the apps via
wf_googlesheets_manager.get_sheets_manager().
"""
from __future__ import annotations
import argparse
import os
import sys
from pathlib import Path
from typing import Dict, List, Set

# ensure 10.common in path
ROOT = Path(__file__).resolve().parents[2]
COMMON = ROOT / "10.common"
if str(COMMON) not in sys.path:
    sys.path.insert(0, str(COMMON))

try:
    from wf_googlesheets_manager import get_sheets_manager
except Exception as e:
    print(f"Failed to import wf_googlesheets_manager: {e}")
    sys.exit(1)

# Canonical registry mapping (source of truth for IDs used across policies)
CANONICAL_APPS: Dict[str, List[str]] = {
    # canonical: aliases
    "bom_exporter": ["Bom2Excel", "Bom2Excel_Exporter", "bom2excel", "bom_exporter"],
    "conversion_verifier": ["file_list_check", "Conversion_Verifier", "conversion_verifier"],
    "dwg_classifier": ["dwg_classifier", "DWG_Classifier"],
    "korean_filename_normalizer": ["korean_filename_normalizer", "Korean_FileName_Normalizer"],
    # Optional known apps used in policies
    "DWG_Batch_Print": ["DWG_Batch_Print"],
    "Drawing_Attribute_Reset": ["Drawing_Attribute_Reset"],
}

# Map folder names to canonical IDs (for discovery)
FOLDER_TO_CANONICAL: Dict[str, str] = {
    "bom_exporter": "bom_exporter",
    "conversion_verifier": "conversion_verifier",
    "dwg_classifier": "dwg_classifier",
    "korean_filename_normalizer": "korean_filename_normalizer",
}


def discover_apps(base: Path) -> Set[str]:
    """Discover canonical app names from folder structure under 30.apps and 50.data."""
    discovered: Set[str] = set()
    # scan 30.apps
    apps_30 = base / "30.apps"
    if apps_30.exists():
        for child in apps_30.iterdir():
            if child.is_dir():
                canon = FOLDER_TO_CANONICAL.get(child.name)
                if canon:
                    discovered.add(canon)
    # scan 50.data
    apps_50 = base / "50.data"
    if apps_50.exists():
        for child in apps_50.iterdir():
            if child.is_dir():
                canon = FOLDER_TO_CANONICAL.get(child.name)
                if canon:
                    discovered.add(canon)
    # Include any canonical from registry even if not on disk (optional)
    for canon in CANONICAL_APPS.keys():
        discovered.add(canon)
    return discovered


def ensure_app_policy_rows(test_mode: bool, app_names: Set[str], set_enabled: bool = False) -> Dict[str, int]:
    """Ensure each app_name exists as a row in app_policy. Returns summary counts.
    If set_enabled is True and an 'enabled' column exists, new rows will set it to TRUE.
    """
    mgr = get_sheets_manager(test_mode=test_mode)
    cfg = mgr._load_config()  # type: ignore[attr-defined]
    sheet_id = cfg[f"SHEET_ID_{'TEST' if test_mode else 'PROD'}"]

    # Open spreadsheet and app_policy sheet
    spreadsheet = mgr.gc.open_by_key(sheet_id)  # type: ignore[attr-defined]
    ws = spreadsheet.worksheet("app_policy")

    # Read header and current records
    header: List[str] = ws.row_values(1)
    header_lc = [h.strip().lower() for h in header]
    try:
        records = ws.get_all_records()
    except Exception:
        records = []

    # Build existing names set (raw, case-insensitive)
    name_idx = header_lc.index("app_name") if "app_name" in header_lc else None
    if name_idx is None:
        raise RuntimeError("'app_policy' sheet missing 'app_name' column header")

    existing: Set[str] = set()
    for rec in records:
        val = str(rec.get("app_name", "")).strip()
        if val:
            existing.add(val)

    updates = 0
    inserts = 0
    enabled_idx = header_lc.index("enabled") if "enabled" in header_lc else None

    # Append missing ones
    for app in sorted(app_names):
        if app in existing:
            continue
        row = [""] * len(header)
        row[name_idx] = app
        if set_enabled and enabled_idx is not None:
            row[enabled_idx] = "TRUE"
        ws.append_row(row)
        inserts += 1

    return {"inserted": inserts, "updated": updates, "total": len(app_names)}


def main():
    parser = argparse.ArgumentParser(description="Sync app_name entries into app_policy sheet")
    parser.add_argument("--test", action="store_true", help="Use test Google Sheet (TEST)")
    parser.add_argument("--enable", action="store_true", help="Set enabled=TRUE for newly added rows if column exists")
    args = parser.parse_args()

    base = ROOT / "10.rpa"
    apps = discover_apps(base)

    result = ensure_app_policy_rows(test_mode=args.test, app_names=apps, set_enabled=args.enable)
    print(
        f"Sync complete: inserted={result['inserted']}, updated={result['updated']}, total_apps={result['total']}"
    )


if __name__ == "__main__":
    main()
