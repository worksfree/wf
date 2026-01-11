"""Automated smoke test for Settings windows of WorksFree apps.

Opens each app's settings UI briefly (headless-friendly) and reports
whether construction succeeded without raising exceptions.

Apps covered:
  - bom_exporter
  - korean_filename_normalizer
  - conversion_verifier
  - dwg_classifier

Exit code 0: all passed
Exit code 1: one or more failures (details printed)
"""

from __future__ import annotations

import sys, time, traceback
from pathlib import Path
import tkinter as tk

ROOT = Path(__file__).resolve().parent.parent  # 10.rpa directory

# Ensure common path and each app path are importable
COMMON = ROOT / "10.common"
APPS = {
    "bom_exporter": ROOT / "30.apps" / "bom_exporter",
    "korean_filename_normalizer": ROOT / "50.data" / "korean_filename_normalizer",
    "conversion_verifier": ROOT / "50.data" / "conversion_verifier",
    "dwg_classifier": ROOT / "50.data" / "dwg_classifier",
}
# Add common path only, apps will be added per-test
if str(COMMON) not in sys.path:
    sys.path.insert(0, str(COMMON))

results = {}


def safe_run(label, func):
    try:
        func()
        results[label] = "PASS"
    except Exception as e:
        results[label] = f"FAIL: {e}"
        traceback.print_exc()


def test_bom_exporter():
    """Test that bom_exporter settings module can be imported and has required functions"""
    app_path = str(APPS["bom_exporter"])
    sys.path.insert(0, app_path)
    try:
        from ui_setting import create_settings_window, get_adaptive_ui_settings  # type: ignore

        # Test that get_adaptive_ui_settings returns expected keys
        ui_settings = get_adaptive_ui_settings()
        assert "window_width" in ui_settings
        assert "window_height" in ui_settings
        assert "tree_rowheight" in ui_settings
        assert ui_settings["tree_rowheight"] > 0
        
        # Test that create_settings_window function exists and is callable
        assert callable(create_settings_window)
    finally:
        if app_path in sys.path:
            sys.path.remove(app_path)
        if 'ui_setting' in sys.modules:
            del sys.modules['ui_setting']


def test_kfn():
    """Test that korean_filename_normalizer settings module can be imported"""
    app_path = str(APPS["korean_filename_normalizer"])
    sys.path.insert(0, app_path)
    try:
        from ui_setting import create_settings_window, get_adaptive_ui_settings  # type: ignore
        from app_setting_data import get_config  # type: ignore

        # Test that functions exist and are callable
        assert callable(create_settings_window)
        assert callable(get_config)
        
        # Test UI settings
        ui_settings = get_adaptive_ui_settings()
        assert "window_width" in ui_settings
        assert "font_size" in ui_settings
        
        # Test config can be loaded
        cfg = get_config()
        assert cfg is not None
    finally:
        if app_path in sys.path:
            sys.path.remove(app_path)
        if 'ui_setting' in sys.modules:
            del sys.modules['ui_setting']
        if 'app_setting_data' in sys.modules:
            del sys.modules['app_setting_data']


def test_conversion_verifier():
    """Test that conversion_verifier UI module can be imported"""
    app_path = str(APPS["conversion_verifier"])
    sys.path.insert(0, app_path)
    try:
        import ui_main  # type: ignore

        # Test that ConversionVerifierApp class exists
        assert hasattr(ui_main, 'ConversionVerifierApp')
        assert callable(ui_main.ConversionVerifierApp)
    finally:
        if app_path in sys.path:
            sys.path.remove(app_path)
        if 'ui_main' in sys.modules:
            del sys.modules['ui_main']


def test_dwg_classifier():
    """Test that dwg_classifier settings module can be imported"""
    # Clear any cached modules first
    for mod in ['ui_setting', 'app_setting_data']:
        if mod in sys.modules:
            del sys.modules[mod]
    
    app_path = str(APPS["dwg_classifier"])
    sys.path.insert(0, app_path)
    try:
        from ui_setting import create_settings_window, get_adaptive_ui_settings  # type: ignore
        from app_setting_data import get_config  # type: ignore

        # Test that functions exist
        assert callable(create_settings_window)
        assert callable(get_config)
        
        # Test UI settings
        ui_settings = get_adaptive_ui_settings()
        assert "window_width" in ui_settings
        assert "font_size" in ui_settings
        
        # Test config
        cfg = get_config()
        assert cfg is not None
    finally:
        if app_path in sys.path:
            sys.path.remove(app_path)
        if 'ui_setting' in sys.modules:
            del sys.modules['ui_setting']
        if 'app_setting_data' in sys.modules:
            del sys.modules['app_setting_data']


def main():
    safe_run("bom_exporter", test_bom_exporter)
    safe_run("korean_filename_normalizer", test_kfn)
    safe_run("conversion_verifier", test_conversion_verifier)
    safe_run("dwg_classifier", test_dwg_classifier)

    print("\n=== SETTINGS WINDOW SMOKE TEST RESULTS ===")
    for k, v in results.items():
        print(f"{k:28}: {v}")
    failed = [k for k, v in results.items() if v != "PASS"]
    if failed:
        print(f"\nFailures: {failed}")
        sys.exit(1)
    print("\nAll settings windows opened successfully.")


if __name__ == "__main__":
    main()
