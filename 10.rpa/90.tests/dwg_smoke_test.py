import sys, os

# Ensure DWG app folder is importable
sys.path.insert(0, r"d:\drive_files\10.worksfree\10.rpa\50.data\dwg_classifier")

# Prefer dev mode to keep writes under app/config
os.environ["WF_RPA_DEV"] = "1"

import tkinter as tk
from ui_main import DwgClassifierApp

# Create minimal Tk context and immediately close
root = tk.Tk()
root.withdraw()
app = DwgClassifierApp(root)
root.update_idletasks()
# Trigger graceful close
app.on_closing()
print("SMOKE_OK")
