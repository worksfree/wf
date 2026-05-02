import sys
from pathlib import Path

apps = [
    'attribute_reset',
    'batch_print',
    'bom_exporter',
    'conversion_verifier',
    'dwg_classifier',
    'korean_filename_normalizer',
    'qrcode_generator'
]

for app in apps:
    try:
        app_path = Path(r"D:\drive_files\10.worksfree\10.rpa\30.apps") / app
        sys.path.insert(0, str(app_path))
        sys.path.insert(0, str(app_path.parent.parent / "10.common"))
        
        # Clear previous imports
        for mod in list(sys.modules.keys()):
            if 'app_setting_data' in mod or 'config' in mod.lower():
                del sys.modules[mod]
        
        from app_setting_data import get_config
        cfg = get_config()
        height = cfg.ui_config.get("window_height", "?")
        print(f'{app:30} → DEV height={height}')
        
    except Exception as e:
        print(f'{app:30} → ERROR: {e}')
