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
    
    # Find .exe file
    $exeFiles = Get-ChildItem -Path $PackagePath -Filter "*.exe"
    $hasExe = $exeFiles.Count -gt 0
    Write-CheckResult -CheckName "Executable file (.exe)" -Passed $hasExe -Message $(if ($hasExe) { $exeFiles[0].Name } else { "Not found" })
    
    # Check _internal directory
    $internalDir = Join-Path $PackagePath "_internal"
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
        $hasSheetId = $null -ne $gs.sheet_id_prod -and $gs.sheet_id_prod -ne ""
        Write-CheckResult -CheckName "  sheet_id_prod config" -Passed $hasSheetId -Message $(if ($hasSheetId) { $gs.sheet_id_prod.Substring(0, 20) + "..." } else { "Not configured" })
        
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
    
    # Find .silver-argon file
    $silverFiles = Get-ChildItem -Path $script:WfRpaDir -Filter ".silver-argon*.json"
    
    if ($silverFiles.Count -eq 0) {
        Write-CheckResult -CheckName ".silver-argon file exists" -Passed $false -Message "Credential file not found"
        return $false
    }
    
    $silverFile = $silverFiles[0]
    Write-CheckResult -CheckName ".silver-argon file exists" -Passed $true -Message "$($silverFile.Name) ($($silverFile.Length) bytes)"
    
    # File size validation (minimum 2000 bytes)
    $sizeOk = $silverFile.Length -ge 2000
    Write-CheckResult -CheckName "File size validation" -Passed $sizeOk -Message $(if ($sizeOk) { "Normal ($($silverFile.Length) bytes)" } else { "Too small ($($silverFile.Length) bytes)" })
    
    # Try JSON parsing
    try {
        $cred = Get-Content $silverFile.FullName -Raw -Encoding UTF8 | ConvertFrom-Json
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
    
    $internalDir = Join-Path $PackagePath "_internal"
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
    $archiveFiles = Get-ChildItem -Path $internalDir -File -ErrorAction SilentlyContinue | 
        Where-Object { $_.Extension -in @('.pyz', '.zip', '.pkg') -and ($_.Name -like "*library*" -or $_.Name -like "*.pyz") }
    $hasArchive = $archiveFiles.Count -gt 0
    Write-CheckResult -CheckName "  Python archive" -Passed $hasArchive -Message $(if ($hasArchive) { "$($archiveFiles.Count) archive(s) found" } else { "Not found" })
    
    if ($hasArchive) {
        Write-Host "`n  [Inspecting Archive Contents]" -ForegroundColor Cyan
        
        # Load System.IO.Compression for ZIP inspection
        Add-Type -AssemblyName System.IO.Compression.FileSystem
        
        foreach ($archive in $archiveFiles) {
            Write-Host "  File: $($archive.Name) ($([math]::Round($archive.Length / 1MB, 2)) MB)" -ForegroundColor Gray
            
            try {
                $zip = [System.IO.Compression.ZipFile]::OpenRead($archive.FullName)
                $entries = $zip.Entries | ForEach-Object { $_.FullName }
                
                # Check for essential libraries in the archive AND _internal directories
                $requiredLibs = @{
                    "ntplib" = "ntplib"
                    "gspread" = "gspread"
                    "google.auth" = "google/auth"
                    "requests" = "requests"
                    "urllib3" = "urllib3"
                }
                
                $appSpecificLibs = @{
                    "keyboard" = "keyboard"
                    "pyautogui" = "pyautogui"
                    "pywinauto" = "pywinauto"
                    "openpyxl" = "openpyxl"
                }
                
                Write-Host "`n  [Required Libraries]" -ForegroundColor White
                foreach ($libName in $requiredLibs.Keys) {
                    $pattern = $requiredLibs[$libName]
                    # Check in archive
                    $foundInArchive = $entries | Where-Object { $_ -like "*$pattern*" }
                    # Check in _internal directory
                    $dirName = $libName -replace '\..*', ''  # Remove everything after first dot (e.g., google.auth -> google)
                    $libDir = Join-Path $internalDir $dirName
                    $foundInDir = Test-Path $libDir
                    
                    $exists = ($foundInArchive.Count -gt 0) -or $foundInDir
                    $location = if ($foundInArchive.Count -gt 0 -and $foundInDir) { "archive + _internal" }
                               elseif ($foundInArchive.Count -gt 0) { "archive" }
                               elseif ($foundInDir) { "_internal" }
                               else { "MISSING" }
                    
                    Write-CheckResult -CheckName "    $libName" -Passed $exists -Message $location -Level "Error"
                }
                
                # Check app-specific libraries (only for BOM Exporter)
                $packageName = Split-Path $PackagePath -Leaf
                if ($packageName -like "*bom_exporter*") {
                    Write-Host "`n  [App-Specific Libraries]" -ForegroundColor White
                    foreach ($libName in $appSpecificLibs.Keys) {
                        $pattern = $appSpecificLibs[$libName]
                        # Check in archive
                        $foundInArchive = $entries | Where-Object { $_ -like "*$pattern*" }
                        # Check in _internal directory
                        $libDir = Join-Path $internalDir $libName
                        $foundInDir = Test-Path $libDir
                        
                        $exists = ($foundInArchive.Count -gt 0) -or $foundInDir
                        $location = if ($foundInArchive.Count -gt 0 -and $foundInDir) { "archive + _internal" }
                                   elseif ($foundInArchive.Count -gt 0) { "archive" }
                                   elseif ($foundInDir) { "_internal" }
                                   else { "missing" }
                        
                        Write-CheckResult -CheckName "    $libName" -Passed $exists -Message $location -Level "Warning"
                    }
                }
                
                $zip.Dispose()
            } catch {
                Write-Host "    ⚠️  Failed to inspect archive: $($_.Exception.Message)" -ForegroundColor Yellow
            }
        }
    } else {
        Write-Host "`n  💡 To verify all dependencies, check the PyInstaller build warnings." -ForegroundColor Yellow
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
            $settingsVersion = $settings.version
            Write-CheckResult -CheckName "settings.json version" -Passed $true -Message "v$settingsVersion"
            
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
    
    # Check for create_desktop_shortcut.bat file (표준 바로가기 생성 스크립트)
    $expectedBat = "create_desktop_shortcut.bat"
    $batPath = Join-Path $PackagePath $expectedBat
    $batExists = Test-Path $batPath
    
    # Shortcut script should exist
    if ($batExists) {
        Write-CheckResult -CheckName "Shortcut creation script (.bat)" -Passed $true -Message $expectedBat
    } else {
        # 대체 .bat 파일 확인
        $batFiles = Get-ChildItem -Path $PackagePath -Filter "*.bat" -ErrorAction SilentlyContinue
        if ($batFiles.Count -gt 0) {
            Write-CheckResult -CheckName "Shortcut creation script (.bat)" -Passed $false -Message "Found $($batFiles[0].Name) but expected $expectedBat" -Level "Warning"
        } else {
            Write-CheckResult -CheckName "Shortcut creation script (.bat)" -Passed $false -Message "Not found (expected: $expectedBat)"
        }
    }
    
    return $batExists
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
