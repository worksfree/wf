#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Update run_mode for all 7 apps
"""

import json
import sys
from pathlib import Path

if len(sys.argv) < 2:
    print("Usage: python set_run_mode.py <mode>")
    print("Modes: dev, demo, release")
    sys.exit(1)

mode = sys.argv[1].lower()
config_dir = Path("d:\\drive_files\\10.worksfree\\10.rpa\\10.common\\config")
apps = ["bom_exporter", "batch_print", "attribute_reset", "dwg_classifier", 
    "conversion_verifier", "korean_filename_normalizer", "qrcode_generator"]

print("=" * 60)
print(f"Setting all apps to {mode.upper()} mode")
print("=" * 60)

for app in apps:
    settings_file = config_dir / app / "settings.json"
    if settings_file.exists():
        with open(settings_file, 'r', encoding='utf-8-sig') as f:
            data = json.load(f)
        data['runtime_config']['run_mode'] = mode
        with open(settings_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"✓ {app}: run_mode = {mode}")

print("=" * 60)
print(f"✓ All apps set to {mode.upper()} mode\n")
