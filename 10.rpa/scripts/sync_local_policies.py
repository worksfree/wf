# -*- coding: utf-8 -*-
"""
Sync local app policies/configs from Google Sheets app_policy and admin_config.

Uses wf_settings_common.sync_policies_from_sheets for each app.

Usage:
    python scripts/sync_local_policies.py            # sync all known apps
    python scripts/sync_local_policies.py bom_exporter  # sync specific app(s)

Writes:
  - %USERPROFILE%\.wf_rpa\<app_name>\credit_policy.json (dev: app/config/<app_name>/credit_policy.json)
  - %USERPROFILE%\.wf_rpa\wf_rpa_config.json (email/google_sheets settings)
"""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
COMMON = ROOT / "10.common"
if str(COMMON) not in sys.path:
    sys.path.insert(0, str(COMMON))

from wf_settings_common import sync_policies_from_sheets  # type: ignore

# Default app list (keys as used by apps when calling sync)
DEFAULT_APPS = [
    "bom_exporter",
    "dwg_classifier",
    "conversion_verifier",
    "korean_filename_normalizer",
]


def main():
    args = sys.argv[1:]
    apps = args or DEFAULT_APPS
    any_fail = False

    for app in apps:
        print(f"[SYNC] {app} ...", flush=True)
        try:
            result = sync_policies_from_sheets(app_name=app, logger=None)
            ok = bool(result.get("success"))
            msg = result.get("message", "")
            if ok:
                print(f"  ✅ {app}: {msg}")
            else:
                print(f"  ❌ {app}: {msg}")
                any_fail = True
        except Exception as e:
            print(f"  ❌ {app}: exception {e}")
            any_fail = True

    sys.exit(1 if any_fail else 0)


if __name__ == "__main__":
    main()
