#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
5개 앱의 실제 폰트 크기 확인 스크립트
"""
import sys
import os
from pathlib import Path

apps = [
    ("Bom Exporter", "d:\\drive_files\\10.worksfree\\10.rpa\\30.apps\\bom_exporter"),
    ("DWG Batch Print", "d:\\drive_files\\10.worksfree\\10.rpa\\30.apps\\dwg_batch_print"),
    ("DWG Classifier", "d:\\drive_files\\10.worksfree\\10.rpa\\50.data\\dwg_classifier"),
    ("Conversion Verifier", "d:\\drive_files\\10.worksfree\\10.rpa\\50.data\\conversion_verifier"),
    ("Korean Filename Normalizer", "d:\\drive_files\\10.worksfree\\10.rpa\\50.data\\korean_filename_normalizer"),
]

print("=" * 80)
print("5개 RPA 앱 폰트 크기 검증")
print("=" * 80)

for app_name, app_path in apps:
    print(f"\n【{app_name}】")
    sys.path.insert(0, app_path)
    
    try:
        # ui_setting 모듈 임포트
        if "ui_setting" in sys.modules:
            del sys.modules["ui_setting"]
        if "app_setting_data" in sys.modules:
            del sys.modules["app_setting_data"]
            
        from ui_setting import get_adaptive_ui_settings
        
        ui = get_adaptive_ui_settings()
        print(f"  font_size: {ui.get('font_size', 'N/A')}")
        print(f"  font_size_bold: {ui.get('font_size_bold', 'N/A')}")
        print(f"  font_size_title: {ui.get('font_size_title', 'N/A')}")
        print(f"  window_width: {ui.get('window_width', 'N/A')}")
        print(f"  window_height: {ui.get('window_height', 'N/A')}")
        print(f"  padding: {ui.get('padding', 'N/A')}")
        
    except Exception as e:
        print(f"  ❌ 오류: {e}")
    finally:
        sys.path.pop(0)

print("\n" + "=" * 80)
print("검증 완료")
print("=" * 80)
