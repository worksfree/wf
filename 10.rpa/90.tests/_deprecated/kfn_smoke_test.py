import sys, os

# Ensure KFN app folder is importable
sys.path.insert(0, r"d:\drive_files\10.worksfree\10.rpa\50.data\korean_filename_normalizer")

# Prefer dev mode to keep writes under app/config
os.environ["WF_RPA_DEV"] = "1"

import tkinter as tk

# KFN main may declare the app class under various names; try to import factory
try:
    import ui_main as kfn
except Exception as e:
    print("IMPORT_FAIL", e)
    raise

root = tk.Tk()
root.withdraw()
# Try to locate an application class by common names
app_obj = None
for name in ("KoreanFilenameNormalizerApp", "KoreanFileNameNormalizerApp", "MainApp", "App"):
    if hasattr(kfn, name):
        app_cls = getattr(kfn, name)
        try:
            app_obj = app_cls(root)
            break
        except Exception:
            continue

if app_obj is None:
    # Fallback: try a factory function
    for fname in ("create_app", "main", "launch_app"):
        if hasattr(kfn, fname):
            fn = getattr(kfn, fname)
            try:
                app_obj = fn(root)
                break
            except Exception:
                continue

if app_obj is None:
    print("NO_APP_CLASS")
else:
    # If class exposes on_closing, call it; else destroy root
    if hasattr(app_obj, "on_closing"):
        try:
            app_obj.on_closing()
        except Exception:
            pass
    root.update_idletasks()
    print("SMOKE_OK")
