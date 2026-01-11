# Policy Loading System - Implementation Report

## 📋 Overview
Implemented a hierarchical policy loading system with repo JSON fallback, local storage, and Google Sheets sync capability.

## ✅ Completed Features

### 1. Repository Policy JSON (Base Layer)
- **File**: `10.common/app_policies.json`
- **Purpose**: Default policies distributed with the source code
- **Content**: All app credit policies (bom2excel, DWG_Classifier, etc.)
- **Usage**: Fallback when no local policies exist

### 2. WorksFreeManager Policy Methods
- [Deprecated] `load_policies()` (전역 파일)는 더 이상 사용하지 않습니다.
  - 정책은 앱별 `~/.wf_rpa/{app}/credit_policy.json`에서 로드됩니다.
- **`save_policies(policies, source)`**: Save policies with source tracking
- **`refresh_policies_from_sheets()`**: Sync from Google Sheets (stub for future)

### 3. Policy Merge Priority
```
Priority (highest to lowest):
1. Local policies (`{app}/credit_policy.json`) - from Sheets sync
2. Repo policies (app_policies.json) - distributed with code
3. Built-in policies (APP_CREDIT_POLICIES) - hardcoded fallback
```

### 4. Dev vs Release Mode Enhancements
- **Dev Mode**: Detected by `WF_RPA_HOME` environment variable
  - Policy files remain visible
  - `.wf_rpa` directory visible
  - App subdirectories visible

- **Release Mode**: No environment variable
  - Policy files hidden on Windows
  - `.wf_rpa` directory hidden
  - App subdirectories hidden

### 5. CreditManager Policy Loading
- **`__init__`** now loads policies in priority order:
  1. Checks built-in policies for app
  2. Loads repo policies from JSON if available
  3. Merges local policies if available
  4. Uses merged result

- **`_load_repo_policies()`**: Helper to load from `app_policies.json`
- **`_update_policy_file()`**: Uses repo policies as base

### 6. Hidden Attribute Support
- **`WorksFreeManager._set_hidden_attribute()`**: Windows hidden file attribute
- Applied to:
  - `.wf_rpa` directory (release mode only)
  - App subdirectories (release mode only)
  - Policy files (release mode only)
  - Credit files (release mode only)

### 7. Release Packaging
- **Updated**: `build_bom2excel_release.py`
- **Added**: `app_policies.json` to common_files list
- Policy JSON now distributed with releases

### 8. Test Infrastructure
- **Fixture**: `auto_registered_user` - auto-registers test users
- **Tests**: All integration tests use policy-based deductions
- **Coverage**: Tests verify `credit_per_work` is respected
- **Results**: ✅ All 5 integration tests pass

### 9. PowerShell Test Runner
- **Fixed**: Parameter conflict (`Verbose` → `Detail`)
- **Status**: ✅ Script runs successfully
- **Usage**: `.\run_tests.ps1 -Scope integration -Module bom2excel -Detail`

## 📊 Test Results

### Policy Loading Test
```
✓ Dev mode: False
✓ WF_RPA_DIR: C:\Users\HP\.wf_rpa
✓ Loaded 8 policies
✓ Available apps: bom2excel, DWG_Classifier, file_list_check, etc.
✓ Repo policies loaded: 6 apps
✓ bom2excel from repo: credit_per_work = 100
```

### Integration Tests
```
test_credit_manager_initialization       PASSED [ 20%]
test_credit_deduction_flow              PASSED [ 40%]
test_unlimited_credit_behavior          PASSED [ 60%]
test_credit_sync_integration            PASSED [ 80%]
test_full_workflow_simulation           PASSED [100%]
```

## 🎯 Benefits

1. **Flexibility**: Policies can be updated without code changes
2. **Distribution**: Base policies packaged with releases
3. **Sync Ready**: Infrastructure for Sheets sync in place
4. **Testing**: Isolated test environments with policy control
5. **Security**: Hidden files in release, visible in dev mode

## 📝 Next Steps (Remaining)

### UI Async Policy Sync + Toast
- Add toast widget to show "정책 동기화 중…"
- Schedule background sync on startup
- Update credit display after sync completes
- Non-blocking user experience

## 🔧 Technical Details

### File Structure
```
10.rpa/
├── 10.common/
│   ├── app_policies.json         # ✅ New: Repo base policies
│   └── wf_credit_manager.py      # ✅ Updated: Policy loading
├── 90.tests/
│   ├── conftest.py               # ✅ Updated: auto_registered_user
│   └── 30.apps/bom2excel/
│       └── test_integration.py   # ✅ Updated: Policy-based tests
└── scripts/
    └── run_tests.ps1             # ✅ Fixed: Verbose → Detail

User Home:
~/.wf_rpa/
├── {app}/credit_policy.json      # Local policies (from Sheets)
└── [app_name]/
    └── .[app_name]_credits.json  # Credit data
```

### Code Changes Summary
- **WorksFreeManager**: +100 lines (dev mode, policies, hidden attr)
- **CreditManager**: +60 lines (policy loading, repo fallback)
- **Tests**: +20 lines (fixtures, policy-based deductions)
- **Build**: +1 line (app_policies.json packaging)
- **Scripts**: +2 lines (parameter rename)

## ✅ Verification

All changes verified through:
1. Unit test: `test_policy_loading.py` ✅
2. Integration tests: 5/5 passing ✅
3. UI launch: Successful ✅
4. Test runner: Working ✅

---
**Status**: 5 out of 6 tasks completed (83%)
**Remaining**: UI async policy sync + toast
**Next**: Implement toast notification and background policy refresh
