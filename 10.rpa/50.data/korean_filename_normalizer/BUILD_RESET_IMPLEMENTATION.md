# Build-Time Credit & User State Reset Implementation

## Overview
Implemented automated reset logic in the build script to ensure every packaged release starts with clean credit and registration state, providing a fresh trial experience for new installations.

## Implementation Date
2025-11-20

## Changes Made

### 1. Template Files Created
Created two JSON template files in `.build_templates/` directory:

#### `credit_history.template.json`
```json
{
  "credit_changed": false,
  "trial_credits": 2000,
  "purchased_credits": 0,
  "created_at": "2025-01-01T00:00:00.000",
  "last_updated": "2025-01-01T00:00:00.000",
  "purchase_history": [],
  "usage_history": []
}
```

**Purpose**: Provides fresh trial credit state (2000 credits) with no usage history.

#### `wf_rpa_config.template.json`
```json
{
  "user_info": {
    "registration_id": "",
    "hardware_fingerprint": "",
    "is_registered": false,
    "registration_date": null,
    "last_sync": null
  },
  "app_execution": {
    "last_run": null,
    "run_count": 0
  },
  "auto_update": {
    "enabled": true,
    "last_check": null,
    "update_channel": "stable"
  }
}
```

**Purpose**: Manages user info, execution status, and auto-update settings. Contains no credit-related data.

### 2. Build Script Modification
Modified `build_korean_filename_normalizer.ps1` to add post-PyInstaller reset logic in the `Build-Onedir` function:

#### Reset Process
1. **Create directory structure**: `.wf_rpa/korean_filename_normalizer/`
2. **Copy templates**:
   - `credit_history.template.json` → `credit_history.json` (in app directory)
   - `wf_rpa_config.template.json` → `wf_rpa_config.json` (in root .wf_rpa)
3. **Remove runtime files**:
   - `credit_policy.json`
   - `app_policy.json`
   - `admin_config.json`
   - `credit_purchase_log_sync_state.json`
   - `credit_usage_log.json`

#### Console Output
```
==> 배포용 초기 상태 설정 중...
   ✓ credit_history.json 초기화 완료
   ✓ wf_rpa_config.json 초기화 완료
   ✓ 제거: credit_policy.json
   배포 초기화 완료!
```

## Data Separation

### Credit Management (`credit_history.json`)
Located in: `.wf_rpa/{app_name}/credit_history.json`

**Managed Fields**:
- `trial_credits` - Free trial credit balance
- `purchased_credits` - Paid credit balance
- `current_credits` - Legacy field (deprecated in new format)
- `applied_purchase_ids` - List of applied purchase record IDs
- `credit_per_work` - Cost per work unit (from policy)
- `purchase_history` - List of purchase transactions
- `usage_history` - List of credit usage records
- `credit_changed` - Flag for sync trigger

### User & System Config (`wf_rpa_config.json`)
Located in: `.wf_rpa/wf_rpa_config.json`

**Managed Fields**:
- `user_info` - Registration ID, hardware fingerprint, registration status
- `app_execution` - Last run time, run count
- `auto_update` - Update settings and last check time
- `email_setting` - Admin email configuration (if present)

## Build Verification

### Test Build Results
Build executed successfully with Mode 1 (onedir):
```
완료: D:\release\candidates\korean_filename_normalizer_20251120_101148
```

### Verification Checks
✅ Templates correctly copied to dist folder  
✅ `credit_history.json` contains fresh trial state (2000 credits)  
✅ `wf_rpa_config.json` contains empty user_info  
✅ Runtime policy/config files successfully removed  
✅ Directory structure created properly  

### File Structure in Dist
```
korean_filename_normalizer_v0.7.0.3_portable/
├── korean_filename_normalizer.exe
├── _internal/
└── .wf_rpa/
    ├── wf_rpa_config.json          # User & system settings
    └── korean_filename_normalizer/
        └── credit_history.json      # Credit state
```

## Migration Safety

### Existing User Upgrades
The runtime code already contains migration logic to handle:
- Legacy format credit files
- Missing fields in config files
- Version upgrades

### Fresh Installs
New installations will:
1. Start with 2000 trial credits
2. Generate hardware fingerprint on first run
3. Create policy files from Google Sheets sync
4. Populate user_info upon registration

## Build Modes
The reset logic applies to all build modes:
- Mode 1: onedir only
- Mode 2: onedir + zip
- Mode 3: onedir + zip + installer
- Mode 4: zip only
- Mode 5: installer only

## Future Enhancements

### Potential Improvements
1. **Version-Gated Reset**: Compare app version in dist vs user's config, trigger selective reset on major version changes
2. **Conditional Reset**: Add build parameter `-PreserveUserInfo` to skip reset for hotfix builds
3. **First-Run Flag**: Add `FIRST_RUN` marker file for runtime detection and one-time setup
4. **Audit Logging**: Log reset actions to `migration_audit.log` for compliance tracking

### Multi-App Rollout
Apply same pattern to other apps:
- `bom2excel`
- `conversion_verifier`
- `dwg_classifier`

Each app will need:
- `.build_templates/` directory with templates
- Modified build script with reset logic
- Verification of app-specific credit settings

## Notes

### Free/Permanent Apps
For apps with `trial_credits: -1` (free/permanent):
- Modify template `trial_credits` to `-1`
- Set `purchased_credits` to `0`
- Runtime code skips credit deduction

### Credit Per Work
The `credit_per_work` field is stored in `credit_history.json` but sourced from:
1. Google Sheets `app_policy` (primary)
2. Local `credit_policy.json` (fallback)
3. Repo default `app_policies.json` (last resort)

The template does not include this field; it's populated on first sync.

## Testing Checklist

- [x] Build script executes without errors
- [x] Templates copied to correct locations
- [x] wf_rpa_config.json contains only user/system fields
- [x] credit_history.json contains fresh trial state
- [x] Runtime policy files removed from dist
- [ ] Test first-run on clean Windows machine
- [ ] Verify migration from old version preserves user data
- [ ] Test credit deduction and sync after reset
- [ ] Verify registration flow with fresh config

## Related Files
- `build_korean_filename_normalizer.ps1` - Build script with reset logic
- `.build_templates/credit_history.template.json` - Credit state template
- `.build_templates/wf_rpa_config.template.json` - User config template
- `10.common/wf_credit_manager.py` - Credit initialization and migration
- `10.common/wf_googlesheets_manager.py` - Config file management
