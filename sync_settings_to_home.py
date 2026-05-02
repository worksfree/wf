#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sync settings.json from 10.common/config to home/.wf_rpa with run_mode=release
"""

import json
import os
from pathlib import Path

source_base = Path("d:\\drive_files\\10.worksfree\\10.rpa\\10.common\\config")
dest_base = Path.home() / ".wf_rpa"

apps = [
    ("bom_exporter", "Bom_Exporter"),
    ("batch_print", "batch_print"),
    ("attribute_reset", "attribute_reset"),
    ("dwg_classifier", "dwg_classifier"),
    ("conversion_verifier", "conversion_verifier"),
    ("korean_filename_normalizer", "korean_filename_normalizer"),
    ("qrcode_generator", "qrcode_generator"),
]

print("=" * 80)
print("SYNCING SETTINGS.JSON TO HOME FOLDER (.wf_rpa)")
print("=" * 80)

for src_name, dst_name in apps:
    src_file = source_base / src_name / "settings.json"
    dst_dir = dest_base / dst_name
    dst_file = dst_dir / "settings.json"
    
    if not src_file.exists():
        print(f"✗ {src_name}: source file not found")
        continue
    
    dst_dir.mkdir(parents=True, exist_ok=True)
    
    with open(src_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Change run_mode to release
    if 'runtime_config' in data:
        data['runtime_config']['run_mode'] = 'release'
    
    # Clear geometry_override
    if 'ui_config' in data:
        data['ui_config']['window_geometry_override'] = ""
    
    with open(dst_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    w = data.get('ui_config', {}).get('window_width', '?')
    h = data.get('ui_config', {}).get('window_height', '?')
    print(f"✓ {src_name:30s}: {w}x{h} (release mode)")

print("\n" + "=" * 80)
print("✓ All settings.json files synchronized to home folder (.wf_rpa)")
print("=" * 80)
