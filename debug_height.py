#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Debug height settings for DC, CV, KFN"""

import sys
import os
from pathlib import Path

# Add common path
common_path = Path(__file__).resolve().parent / "10.rpa" / "10.common"
sys.path.insert(0, str(common_path))

from wf_ui_adaptive import get_adaptive_ui_settings

# Test DC
print("=" * 60)
print("DWG Classifier (DC)")
print("=" * 60)
dc_path = Path(__file__).resolve().parent / "10.rpa" / "50.data" / "dwg_classifier"
sys.path.insert(0, str(dc_path))
from app_setting_data import Config as DCConfig
dc_config = DCConfig()
dc_saved_ui = getattr(dc_config, 'ui_config', None)
print(f"DC config.window_height: {getattr(dc_config, 'window_height', 'NOT FOUND')}")
print(f"DC config.ui_config: {dc_saved_ui}")
dc_ui = get_adaptive_ui_settings(window_type='main', saved_ui=dc_saved_ui)
print(f"DC get_adaptive_ui_settings result window_height: {dc_ui.get('window_height')}")
print()

# Test CV
print("=" * 60)
print("Conversion Verifier (CV)")
print("=" * 60)
sys.path.remove(str(dc_path))
cv_path = Path(__file__).resolve().parent / "10.rpa" / "50.data" / "conversion_verifier"
sys.path.insert(0, str(cv_path))
from app_setting_data import Config as CVConfig
cv_config = CVConfig()
cv_saved_ui = getattr(cv_config, 'ui_config', None)
print(f"CV config.window_height: {getattr(cv_config, 'window_height', 'NOT FOUND')}")
print(f"CV config.ui_config: {cv_saved_ui}")
cv_ui = get_adaptive_ui_settings(window_type='main', saved_ui=cv_saved_ui)
print(f"CV get_adaptive_ui_settings result window_height: {cv_ui.get('window_height')}")
print()

# Test KFN
print("=" * 60)
print("Korean Filename Normalizer (KFN)")
print("=" * 60)
sys.path.remove(str(cv_path))
kfn_path = Path(__file__).resolve().parent / "10.rpa" / "50.data" / "korean_filename_normalizer"
sys.path.insert(0, str(kfn_path))
from app_setting_data import Config as KFNConfig
kfn_config = KFNConfig()
kfn_saved_ui = getattr(kfn_config, 'ui_config', None)
print(f"KFN config.window_height: {getattr(kfn_config, 'window_height', 'NOT FOUND')}")
print(f"KFN config.ui_config: {kfn_saved_ui}")
kfn_ui = get_adaptive_ui_settings(window_type='main', saved_ui=kfn_saved_ui)
print(f"KFN get_adaptive_ui_settings result window_height: {kfn_ui.get('window_height')}")
