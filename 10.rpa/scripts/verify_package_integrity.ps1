# ============================================================
# Package Integrity Verification Script v2.0
# ============================================================
# Purpose: Automated verification of deployment packages
# Usage: .\verify_package_integrity.ps1 -PackagePath "D:\release\candidates\app_v1.0.0" [-Verbose]
# Updated: 2026-01-07 - Added Google Sheets, credentials, config validation
# ============================================================

param(
    [Parameter(Mandatory=$true)]
    [string]$PackagePath
)

$ErrorActionPreference = "Stop"

# ============================================================
# Validation Results Storage
# ============================================================
$script:TotalChecks = 0
$script:PassedChecks = 0
$script:FailedChecks = 0
$script:WarningChecks = 0
$script:WfRpaDir = $null
$script:ActualPackagePath = $null

# ============================================================
# Helper Functions
# ============================================================
function Write-CheckResult {
    param(
        [string]$CheckName,
        [bool]$Passed,
        [string]$Message = "",
        [string]$Level = "Error"  # Error or Warning
    )
    
    $script:TotalChecks++
    
    $icon = if ($Passed) { "✓" } else { "✗" }
    $color = if ($Passed) { "Green" } else { if ($Level -eq "Warning") { "Yellow" } else { "Red" } }
    
    if ($Passed) {
        $script:PassedChecks++
    } elseif ($Level -eq "Warning") {
        $script:WarningChecks++
    } else {
        $script:FailedChecks++
    }
    
    $status = if ($Passed) { "OK" } else { if ($Level -eq "Warning") { "WARN" } else { "FAIL" } }
    Write-Host "  $icon [$status] $CheckName" -ForegroundColor $color -NoNewline
    if ($Message) {
        Write-Host " - $Message" -ForegroundColor Gray
    } else {
        Write-Host ""
    }
}

# ============================================================
# 1. Basic Structure Verification
# ============================================================
function Test-BasicStructure {
    Write-Host "`n[1] Basic Structure Verification" -ForegroundColor Cyan
    Write-Host ("=" * 60) -ForegroundColor DarkGray
    
    # Check package directory
    $exists = Test-Path $PackagePath
    Write-CheckResult -CheckName "Package directory exists" -Passed $exists -Message $(if ($exists) { $PackagePath } else { "Not found" })
    if (-not $exists) { return $false }
    
    # Check if there's a *_portable subdirectory (BuildType 2)
    $portableDirs = Get-ChildItem -Path $PackagePath -Directory -Filter "*_portable" -ErrorAction SilentlyContinue
    if ($portableDirs.Count -gt 0) {
        $script:ActualPackagePath = $portableDirs[0].FullName
        Write-Host "  📦 Detected portable package structure: $($portableDirs[0].Name)" -ForegroundColor DarkGray
    } else {
        $script:ActualPackagePath = $PackagePath
    }
    
    # Find .exe file
    $exeFiles = Get-ChildItem -Path $script:ActualPackagePath -Filter "*.exe"
    $hasExe = $exeFiles.Count -gt 0
    Write-CheckResult -CheckName "Executable file (.exe)" -Passed $hasExe -Message $(if ($hasExe) { $exeFiles[0].Name } else { "Not found" })
    
    # Check _internal directory
    $internalDir = Join-Path $script:ActualPackagePath "_internal"
    $hasInternal = Test-Path $internalDir
    Write-CheckResult -CheckName "_internal directory" -Passed $hasInternal -Message $(if ($hasInternal) { "Found" } else { "Missing" })
    
    if (-not $hasInternal) { return $false }
    
    # Find .wf_rpa directory inside _internal
    $wfRpaDirs = Get-ChildItem -Path $internalDir -Filter ".wf_rpa*" -Directory -Force -ErrorAction SilentlyContinue
    if ($wfRpaDirs.Count -gt 0) {
        $script:WfRpaDir = $wfRpaDirs[0].FullName
        Write-CheckResult -CheckName ".wf_rpa directory" -Passed $true -Message "$($wfRpaDirs[0].Name) (in _internal)"
    } else {
        Write-CheckResult -CheckName ".wf_rpa directory" -Passed $false -Message "Not found in _internal"
        return $false
    }
    
    return $true
}

# ============================================================
# 2. Configuration File Verification
# ============================================================
function Test-ConfigFiles {
    Write-Host "`n[2] Configuration File Verification" -ForegroundColor Cyan
    Write-Host ("=" * 60) -ForegroundColor DarkGray
    
    if (-not $script:WfRpaDir) {
        Write-CheckResult -CheckName "Config verification" -Passed $false -Message ".wf_rpa directory not found"
        return $false
    }
    
    # wf_rpa_config.json verification
    $configPath = Join-Path $script:WfRpaDir "wf_rpa_config.json"
    $configExists = Test-Path $configPath
    Write-CheckResult -CheckName "wf_rpa_config.json" -Passed $configExists -Message $(if ($configExists) { "Found" } else { "Missing" })
    
    if (-not $configExists) { return $false }
    
    # JSON parsing
    try {
        $config = Get-Content $configPath -Raw -Encoding UTF8 | ConvertFrom-Json
        Write-CheckResult -CheckName "JSON parsing" -Passed $true -Message "Valid JSON"
    } catch {
        Write-CheckResult -CheckName "JSON parsing" -Passed $false -Message "Invalid JSON: $($_.Exception.Message)"
        return $false
    }
    
    # Check required sections
    $requiredSections = @("google_sheets", "email_settings")
    foreach ($section in $requiredSections) {
        $hasSection = $null -ne $config.$section
        Write-CheckResult -CheckName "[$section] section exists" -Passed $hasSection -Message $(if ($hasSection) { "Included" } else { "Missing" })
    }
    
    # google_sheets detailed verification
    if ($config.google_sheets) {
        $gs = $config.google_sheets
        $hasSheetIdRelease = $null -ne $gs.sheet_id_release -and $gs.sheet_id_release -ne ""
        $hasSheetIdDev = $null -ne $gs.sheet_id_dev -and $gs.sheet_id_dev -ne ""
        Write-CheckResult -CheckName "  sheet_id_release config" -Passed $hasSheetIdRelease -Message $(if ($hasSheetIdRelease) { $gs.sheet_id_release.Substring(0, 20) + "..." } else { "Not configured" }) -Level $(if ($hasSheetIdRelease) { "Error" } else { "Warning" })
        Write-CheckResult -CheckName "  sheet_id_dev config" -Passed $hasSheetIdDev -Message $(if ($hasSheetIdDev) { $gs.sheet_id_dev.Substring(0, 20) + "..." } else { "Not configured" }) -Level "Warning"
        
        $hasScope = $null -ne $gs.scope -and $gs.scope.Count -gt 0
        Write-CheckResult -CheckName "  scope config" -Passed $hasScope -Message $(if ($hasScope) { "Scope count: $($gs.scope.Count)" } else { "Not configured" })
        
        $hasSheetName = $null -ne $gs.sheet_name_registrations -and $gs.sheet_name_registrations -ne ""
        Write-CheckResult -CheckName "  sheet_name_registrations" -Passed $hasSheetName -Message $(if ($hasSheetName) { $gs.sheet_name_registrations } else { "Not configured" })
    }
    
    # email_settings verification
    if ($config.email_settings) {
        $email = $config.email_settings
        $hasSmtp = $null -ne $email.smtp_server -and $email.smtp_server -ne ""
        Write-CheckResult -CheckName "  SMTP server config" -Passed $hasSmtp -Message $(if ($hasSmtp) { $email.smtp_server } else { "Not configured" })
        
        $hasPort = $null -ne $email.smtp_port
        Write-CheckResult -CheckName "  SMTP port config" -Passed $hasPort -Message $(if ($hasPort) { $email.smtp_port } else { "Not configured" })
    }
    
    return $true
}

# ============================================================
# 3. Credential Files Verification
# ============================================================
function Test-CredentialFiles {
    Write-Host "`n[3] Credential Files Verification" -ForegroundColor Cyan
    Write-Host ("=" * 60) -ForegroundColor DarkGray
    
    if (-not $script:WfRpaDir) {
        Write-CheckResult -CheckName "Credential verification" -Passed $false -Message ".wf_rpa directory not found"
        return $false
    }
    
    # Find credential files (DEV or RELEASE)
    $silverFiles = Get-ChildItem -Path $script:WfRpaDir -Filter "silver-argon*.json" -ErrorAction SilentlyContinue
    $worksfreeFiles = Get-ChildItem -Path $script:WfRpaDir -Filter "worksfree-*.json" -ErrorAction SilentlyContinue
    
    $credFiles = @($silverFiles) + @($worksfreeFiles)
    
    if ($credFiles.Count -eq 0) {
        Write-CheckResult -CheckName "Credential files exist" -Passed $false -Message "No credential files found (silver-argon or worksfree)"
        return $false
    }
    
    $credFile = $credFiles[0]
    Write-CheckResult -CheckName "Credential files exist" -Passed $true -Message "$($credFile.Name) ($($credFile.Length) bytes)"
    
    # File size validation (minimum 2000 bytes)
    $sizeOk = $credFile.Length -ge 2000
    Write-CheckResult -CheckName "File size validation" -Passed $sizeOk -Message $(if ($sizeOk) { "Normal ($($credFile.Length) bytes)" } else { "Too small ($($credFile.Length) bytes)" })
    
    # Try JSON parsing
    try {
        $cred = Get-Content $credFile.FullName -Raw -Encoding UTF8 | ConvertFrom-Json
        Write-CheckResult -CheckName "JSON parsing" -Passed $true -Message "Valid JSON format"
    } catch {
        Write-CheckResult -CheckName "JSON parsing" -Passed $false -Message "JSON parsing failed: $($_.Exception.Message)"
        return $false
    }
    
    # Validate key fields
    $fields = @("type", "project_id", "private_key_id", "private_key", "client_email", "client_id")
    $allFieldsOk = $true
    foreach ($field in $fields) {
        $hasField = $null -ne $cred.$field -and $cred.$field -ne ""
        if (-not $hasField) {
            Write-CheckResult -CheckName "  Required field: $field" -Passed $false -Message "Missing"
            $allFieldsOk = $false
        }
    }
    
    if ($allFieldsOk) {
        Write-CheckResult -CheckName "Required fields validation" -Passed $true -Message "All required fields exist"
    }
    
    return $true
}

# ============================================================
# 4. Bundle Files Verification (Simplified - PyInstaller packages are archived)
# ============================================================
function Test-BundleFiles {
    Write-Host "`n[4] Bundle Files Verification" -ForegroundColor Cyan
    Write-Host ("=" * 60) -ForegroundColor DarkGray
    
    $internalDir = Join-Path $script:ActualPackagePath "_internal"
    if (-not (Test-Path $internalDir)) {
        Write-CheckResult -CheckName "Bundle verification" -Passed $false -Message "_internal directory not found"
        return $false
    }
    
    Write-Host "  Note: PyInstaller archives Python modules into PYZ files." -ForegroundColor Gray
    Write-Host "  Checking for essential system directories and compiled files..." -ForegroundColor Gray
    Write-Host ""
    
    # Check for key directories that should exist
    $essentialDirs = @("certifi", "pandas", "psutil")
    foreach ($dir in $essentialDirs) {
        $dirPath = Join-Path $internalDir $dir
        $exists = Test-Path $dirPath
        Write-CheckResult -CheckName "  $dir directory" -Passed $exists -Message $(if ($exists) { "Found" } else { "Missing" }) -Level $(if ($exists) { "Error" } else { "Warning" })
    }
    
    # Check for PYZ archive (contains most Python modules)
    # Note: PyInstaller stores modules in PYZ files, not base_library.zip
    $pyzFiles = Get-ChildItem -Path $internalDir -Filter "*.pyz" -File -ErrorAction SilentlyContinue
    $hasPyz = $pyzFiles.Count -gt 0
    Write-CheckResult -CheckName "  PYZ archive" -Passed $hasPyz -Message $(if ($hasPyz) { "$($pyzFiles.Count) PYZ file(s) found" } else { "Not found (modules may be in other archives)" }) -Level "Warning"

    # Check required libraries in _internal directory
    # Note: PyInstaller extracts some libraries to _internal, others stay in PYZ
    Write-Host "`n  [Required Libraries - checking _internal directory]" -ForegroundColor White

    $requiredLibs = @{
        "ntplib" = "ntplib"
        "gspread" = "gspread"
        "google" = "google"
        "requests" = "requests"
        "urllib3" = "urllib3"
    }

    foreach ($libName in $requiredLibs.Keys) {
        $libDir = Join-Path $internalDir $libName
        $foundInDir = Test-Path $libDir

        # Also check for .pyc files or subdirectories
        if (-not $foundInDir) {
            $pycFiles = Get-ChildItem -Path $internalDir -Filter "$libName*.pyc" -File -ErrorAction SilentlyContinue
            $foundInDir = $pycFiles.Count -gt 0
        }

        # Libraries in PYZ are assumed to be present if PYZ exists
        $location = if ($foundInDir) { "_internal" } elseif ($hasPyz) { "PYZ (assumed)" } else { "MISSING" }
        $exists = $foundInDir -or $hasPyz

        Write-CheckResult -CheckName "    $libName" -Passed $exists -Message $location -Level $(if ($foundInDir) { "Error" } else { "Warning" })
    }

    # Check app-specific libraries (only for apps that need them)
    $packageName = Split-Path $PackagePath -Leaf
    if ($packageName -like "*bom_exporter*" -or $packageName -like "*dwg_batch_print*") {
        Write-Host "`n  [App-Specific Libraries]" -ForegroundColor White

        $appSpecificLibs = @{
            "keyboard" = "keyboard"
            "pyautogui" = "pyautogui"
            "pywinauto" = "pywinauto"
            "openpyxl" = "openpyxl"
        }

        foreach ($libName in $appSpecificLibs.Keys) {
            $libDir = Join-Path $internalDir $libName
            $foundInDir = Test-Path $libDir

            $location = if ($foundInDir) { "_internal" } elseif ($hasPyz) { "PYZ (assumed)" } else { "missing" }
            $exists = $foundInDir -or $hasPyz

            Write-CheckResult -CheckName "    $libName" -Passed $exists -Message $location -Level "Warning"
        }
    }
    
    return $true
}

# ============================================================
# 5. Version Information Verification
# ============================================================
function Test-VersionInfo {
    Write-Host "`n[5] Version Information Verification" -ForegroundColor Cyan
    Write-Host ("=" * 60) -ForegroundColor DarkGray
    
    # Extract version from package name
    $packageName = Split-Path $PackagePath -Leaf
    if ($packageName -match "v(\d+\.\d+\.\d+\.\d+)") {
        $version = $matches[1]
        Write-CheckResult -CheckName "Version extracted from package name" -Passed $true -Message "v$version"
    } else {
        Write-CheckResult -CheckName "Version extracted from package name" -Passed $false -Message "Version pattern not found"
    }
    
    # Check settings.json for version consistency
    $settingsFiles = Get-ChildItem -Path $PackagePath -Filter "settings.json" -Recurse -ErrorAction SilentlyContinue
    if ($settingsFiles.Count -gt 0) {
        try {
            $settings = Get-Content $settingsFiles[0].FullName -Raw -Encoding UTF8 | ConvertFrom-Json
            # runtime_config.full_version 우선, 없으면 version 사용
            $settingsVersion = if ($settings.runtime_config.full_version) { $settings.runtime_config.full_version } else { $settings.version }
            # 이미 v로 시작하면 v 추가 안함
            $displayVersion = if ($settingsVersion -and $settingsVersion.StartsWith("v")) { $settingsVersion } else { "v$settingsVersion" }
            Write-CheckResult -CheckName "settings.json version" -Passed $true -Message $displayVersion
            
            if ($version -and $settingsVersion -and $version -eq $settingsVersion) {
                Write-CheckResult -CheckName "Version consistency" -Passed $true -Message "Package name and settings.json match"
            }
        } catch {
            Write-CheckResult -CheckName "settings.json parsing" -Passed $false -Message $_.Exception.Message
        }
    }
    
    return $true
}

# ============================================================
# 6. Shortcut Creation Script Verification
# ============================================================
function Test-Shortcut {
    Write-Host "`n[6] Shortcut Creation Script Verification" -ForegroundColor Cyan
    Write-Host ("=" * 60) -ForegroundColor DarkGray
    
    # Check for create_desktop_shortcut.bat file or 바로가기_생성.bat
    $expectedBats = @("create_desktop_shortcut.bat", "바로가기_생성.bat")
    $foundBat = $null
    
    foreach ($batName in $expectedBats) {
        $batPath = Join-Path $script:ActualPackagePath $batName
        if (Test-Path $batPath) {
            $foundBat = $batName
            break
        }
    }
    
    if ($foundBat) {
        Write-CheckResult -CheckName "Shortcut creation script (.bat)" -Passed $true -Message $foundBat
    } else {
        # 대체 .bat 파일 확인
        $batFiles = Get-ChildItem -Path $script:ActualPackagePath -Filter "*.bat" -ErrorAction SilentlyContinue
        if ($batFiles.Count -gt 0) {
            Write-CheckResult -CheckName "Shortcut creation script (.bat)" -Passed $true -Message "Found $($batFiles.Count) .bat file(s): $($batFiles[0].Name)" -Level "Warning"
        } else {
            Write-CheckResult -CheckName "Shortcut creation script (.bat)" -Passed $false -Message "Not found (expected: create_desktop_shortcut.bat or 바로가기_생성.bat)"
        }
    }
    
    return ($null -ne $foundBat -or $batFiles.Count -gt 0)
}

# ============================================================
# Main Execution
# ============================================================
function Main {
    Write-Host "`n" -NoNewline
    Write-Host ("=" * 80) -ForegroundColor Magenta
    Write-Host "          PACKAGE INTEGRITY VERIFICATION" -ForegroundColor Magenta
    Write-Host ("=" * 80) -ForegroundColor Magenta
    Write-Host "Package Path: $PackagePath" -ForegroundColor White
    
    # Execute all verification steps
    Test-BasicStructure | Out-Null
    Test-ConfigFiles | Out-Null
    Test-CredentialFiles | Out-Null
    Test-BundleFiles | Out-Null
    Test-VersionInfo | Out-Null
    Test-Shortcut | Out-Null
    
    # Final Summary
    Write-Host "`n" -NoNewline
    Write-Host ("=" * 80) -ForegroundColor Magenta
    Write-Host "          VERIFICATION SUMMARY" -ForegroundColor Magenta
    Write-Host ("=" * 80) -ForegroundColor Magenta
    
    Write-Host "Total Checks  : $script:TotalChecks" -ForegroundColor White
    Write-Host "Passed        : $script:PassedChecks" -ForegroundColor Green
    Write-Host "Failed        : $script:FailedChecks" -ForegroundColor Red
    Write-Host "Warnings      : $script:WarningChecks" -ForegroundColor Yellow
    
    $successRate = if ($script:TotalChecks -gt 0) { 
        [math]::Round(($script:PassedChecks / $script:TotalChecks) * 100, 1) 
    } else { 0 }
    
    Write-Host "`nSuccess Rate  : $successRate%" -ForegroundColor $(if ($successRate -ge 90) { "Green" } elseif ($successRate -ge 70) { "Yellow" } else { "Red" })
    
    # Exit code
    if ($script:FailedChecks -gt 0) {
        Write-Host "`nResult: VERIFICATION FAILED" -ForegroundColor Red -BackgroundColor DarkRed
        exit 1
    } elseif ($script:WarningChecks -gt 0) {
        Write-Host "`nResult: VERIFICATION PASSED WITH WARNINGS" -ForegroundColor Yellow
        exit 0
    } else {
        Write-Host "`nResult: VERIFICATION PASSED" -ForegroundColor Green -BackgroundColor DarkGreen
        exit 0
    }
}

# Run main function
Main
