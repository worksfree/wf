import sys
from pathlib import Path

# BOM Exporter 경로
bom_path = Path(r"D:\drive_files\10.worksfree\10.rpa\30.apps\bom_exporter")
sys.path.insert(0, str(bom_path))
sys.path.insert(0, str(bom_path.parent.parent / "10.common"))

from app_setting_data import get_config

cfg = get_config()
print(f'run_mode: {cfg.run_mode}')
print(f'settings_file: {cfg.settings_file}')
print(f'window_height: {cfg.ui_config["window_height"]}')
print(f'window_width: {cfg.ui_config["window_width"]}')
