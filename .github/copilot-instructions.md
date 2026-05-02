# WorksFree RPA Project - AI Agent Instructions

## Project Overview

**WorksFree RPA** is a Python-based desktop automation suite for mechanical engineers, focused on SolidWorks and CAD file processing. The project delivers **7 commercial RPA applications** with integrated credit management, Google Sheets synchronization, and hardware fingerprinting.

### Core Architecture

```
10.rpa/
├── 10.common/          # Shared modules (credit, config, logging, UI)
├── 30.apps/            # SolidWorks-dependent apps (BE, DP, AR)
├── 50.data/            # Pure Python data apps (DC, CV, KFN, QR)
└── 90.tests/           # WF-ACT certification toolkit
```

**App Aliases**: `be` (BOM Exporter), `dp` (DWG Batch Print), `ar` (Attribute Reset), `dc` (DWG Classifier), `cv` (Conversion Verifier), `kfn` (Korean Filename Normalizer), `qr` (QRCode Generator)

---

## Critical Execution Modes (WF_RPA_MODE)

All apps detect runtime mode via `_detect_run_mode()` in [10.rpa/30.apps/bom_exporter/ui_main.py](10.rpa/30.apps/bom_exporter/ui_main.py#L21-L38):

| Mode | Trigger | Config Path | Use Case |
|------|---------|-------------|----------|
| **dev** | `python ui_main.py` (auto-detect `.py`) | `10.common/config/{app}/` | Development/debugging |
| **demo** | `WF_RPA_MODE=demo python ui_main.py` | `10.common/config/{app}/` | Screen recording/demos |
| **release** | `{app}.exe` (PyInstaller frozen) | `~/.wf_rpa/{app}/` | User deployment |

**Never hardcode paths** - mode detection determines all file locations (logs, settings, credentials).

---

## Configuration Fallback Chain

**Critical**: Settings have a **3-layer fallback** (see [10.rpa/10.common/BASIC_RULES.md](10.rpa/10.common/BASIC_RULES.md#L1-L50)):

```python
# 1st priority: JSON config (mode-dependent path)
value = ui.get("window_height", ...)  # from settings.json

# 2nd priority: app_setting_data.py
value = getattr(config, "window_height", ...)

# 3rd priority: ui_main.py constants
value = DEFAULT_HEIGHT  # hardcoded fallback
```

**Do NOT** bulk-change values across apps - each app has optimized settings. Only modify the requested app.

---

## Build System (PyInstaller 6.16.0)

### Build Types

Build scripts accept `-BuildType` parameter:
- `1` = onedir only
- `2` = onedir + ZIP (default)
- `3` = onedir + ZIP + NSIS installer
- `4` = ZIP only
- `5` = installer only

**Sequential build**: Use [10.rpa/build_all.ps1](10.rpa/build_all.ps1) for all 7 apps.  
**Parallel build**: Use [10.rpa/build_all_parallel.ps1](10.rpa/build_all_parallel.ps1) (faster, requires more RAM).

### Key Build Files

Each app has:
- `build_{app}.ps1` - Main build orchestrator
- `{app}.spec` - PyInstaller config (generated from [10.rpa/enhanced_app.spec.template](10.rpa/enhanced_app.spec.template))
- `prepare_user_configs()` - Bundle config files into `_internal/.wf_rpa/`

**Critical**: All apps bundle both DEV and RELEASE Google credentials (`silver-argon*.json`, `worksfree-*.json`).

---

## Credit System Architecture

Credits are managed per-app in [10.rpa/10.common/wf_credit_manager.py](10.rpa/10.common/wf_credit_manager.py):

### Credit Policies (from [10.rpa/10.common/BASIC_RULES.md](10.rpa/10.common/BASIC_RULES.md#L113-L127))

| App | trial_credits | credit_per_work | Type |
|-----|---------------|-----------------|------|
| BE | 10,000 | 100 | per_file |
| DC | 5,000 | 50 | per_file |
| DP | 4,000 | 40 | per_file |
| AR | 20,000 | 200 | per_file |
| **CV, KFN, QR** | **-1** | **0** | **free** |

**Free apps** (`trial_credits = -1`) skip credit deduction but still log usage to Google Sheets for analytics.

### File Structure

```
~/.wf_rpa/
├── wf_rpa_config.json       # Global: user email, HW fingerprint
└── {app_name}/
    ├── policy.json           # App identity + credit policy
    ├── credit_history.json   # Usage log, remaining credits
    └── settings.json         # UI preferences
```

**Never modify** `wf_rpa_config.json` user registration data directly - use [10.rpa/10.common/wf_register.py](10.rpa/10.common/wf_register.py).

---

## Testing with WF-ACT

The **WF-ACT (App Certification Toolkit)** in [10.rpa/90.tests/ui_lifecycle_test/](10.rpa/90.tests/ui_lifecycle_test/) validates app lifecycles:

### Certification Levels

| Level | Badge | Tests | Criteria |
|-------|-------|-------|----------|
| **FULL** | 🥇 | 76+ | All tests pass (edge cases) |
| **STANDARD** | 🥈 | 60 | Normal scenarios pass |
| **BASIC** | 🥉 | 40 | Core features work |

**Run certification**:
```powershell
# DEV mode (source code)
python 90.tests/ui_lifecycle_test/run_certification.py

# EXE mode (packaged builds)
python 90.tests/ui_lifecycle_test/run_certification.py --exe
```

Reports generate at `90.tests/ui_lifecycle_test/test_results/certification_{timestamp}/index.html`.

---

## Common Development Patterns

### 1. Adding a New Setting

```python
# 1. Add to app_setting_data.py (fallback)
class BomExporterConfigData:
    window_height = 200  # 2nd priority

# 2. Update settings.json template (10.common/config/{app}/)
{
  "ui_config": {
    "window_height": 200  # 1st priority
  }
}

# 3. Read in ui_main.py
self.original_window_height = self.ui.get(
    "window_height", 
    getattr(self.config, "window_height", 200)  # fallback chain
)
```

### 2. Logging Pattern

All modules use [10.rpa/10.common/wf_log.py](10.rpa/10.common/wf_log.py) with **30-day auto-deletion**:

```python
from wf_log import WFLogger

logger = WFLogger.getLogger("bom_exporter", run_mode="dev", app_folder="./")
logger.debug("Detailed debug info")
logger.info("User-facing info")
logger.error("Error with traceback", exc_info=True)
```

**Mode-specific log levels**:
- DEV: Console=DEBUG, File=DEBUG
- DEMO: Console=DEBUG, File=DEBUG
- RELEASE: Console=INFO, File=DEBUG

### 3. Google Sheets Integration

Use [10.rpa/10.common/wf_googlesheets_manager.py](10.rpa/10.common/wf_googlesheets_manager.py) for sync:

```python
from wf_googlesheets_manager import WorksFreeGoogleSheetsManager

gs_mgr = WorksFreeGoogleSheetsManager(run_mode="release", app_folder="./")
gs_mgr.sync_user_credits(app_name="be", user_email="user@example.com", ...)
```

**Credentials**: DEV uses `silver-argon*.json`, RELEASE uses `worksfree-*.json` (both bundled in builds).

---

## Common Gotchas

1. **Never use `&&` in PowerShell** - Use `;` for command chaining or pipes `|` for data flow.
2. **PyInstaller "Aborted by user request"** - Fixed in [10.rpa/build_all.ps1](10.rpa/build_all.ps1#L93) by avoiding `$null |` stdin redirection.
3. **Free vs Unlimited apps** - Free apps have `trial_credits=-1`, unlimited users have `charged_credits=-1` (different concepts, see [10.rpa/10.common/BASIC_RULES.md](10.rpa/10.common/BASIC_RULES.md#L128-L154)).
4. **Window height customization** - Each app has optimized `window_height` in settings.json (1-input apps: 200px, 2-input apps: 320px) - don't standardize blindly.
5. **Demo mode video capture** - Only DEMO mode enables 3-second pauses for screen recording ([10.rpa/10.common/ReadMe.md](10.rpa/10.common/ReadMe.md#L90-L110)).

---

## Quick Reference

### Run App in Different Modes
```powershell
# DEV (uses 10.common/config/)
python ui_main.py

# DEMO (uses 10.common/config/ but adds video pauses)
$env:WF_RPA_MODE = "demo"; python ui_main.py

# RELEASE (uses ~/.wf_rpa/)
.\bom_exporter.exe  # or set WF_RPA_MODE=release
```

### Build Single App
```powershell
cd 10.rpa/30.apps/bom_exporter
.\build_bom_exporter.ps1 -BuildType 2  # onedir + ZIP
```

### Run Tests
```powershell
# Pytest unit/integration tests
pytest 90.tests/ -v -m unit

# Full certification (all 7 apps)
python 90.tests/ui_lifecycle_test/run_certification.py
```

### Sync Settings to Home Directory
```powershell
# Copy dev configs to user home for testing
python sync_settings_to_home.py
```

---

## Key Files to Reference

- [10.rpa/README.md](10.rpa/README.md) - Full project documentation
- [10.rpa/10.common/BASIC_RULES.md](10.rpa/10.common/BASIC_RULES.md) - Window sizes, credit policies, fallback chains
- [10.rpa/10.common/ReadMe.md](10.rpa/10.common/ReadMe.md) - Mode detection, logging system
- [10.rpa/DEVLOG.md](10.rpa/DEVLOG.md) - Historical context on architecture decisions
- [10.rpa/pytest.ini](10.rpa/pytest.ini) - Test markers and configuration

When modifying UI, validate against [10.rpa/10.common/ui_rules_validator.py](10.rpa/10.common/ui_rules_validator.py) to ensure DPI scaling compliance.
