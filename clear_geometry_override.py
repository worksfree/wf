#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Clear window_geometry_override from all settings.json files
"""

import json
from pathlib import Path

config_dir = Path("d:\\drive_files\\10.worksfree\\10.rpa\\10.common\\config")
apps = ["bom_exporter", "dwg_batch_print", "attribute_reset", "dwg_classifier", 
        "conversion_verifier", "korean_filename_normalizer", "qrcode_generator"]

print("=" * 60)
print("Clearing window_geometry_override in all settings.json")
print("=" * 60)

for app in apps:
    settings_file = config_dir / app / "settings.json"
    if settings_file.exists():
        with open(settings_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        old_value = data.get('ui_config', {}).get('window_geometry_override', '')
        data['ui_config']['window_geometry_override'] = ""
        
        with open(settings_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"✓ {app:30s}: '{old_value}' → ''")

print("=" * 60)
print("✓ All window_geometry_override cleared\n")
