# ============================================================================
# WorksFree App Consistency Checker v1.0
# ============================================================================
# Purpose: Verify all 6 apps have consistent lifecycle components
# Usage: .\check_app_consistency.ps1
# ============================================================================

$ErrorActionPreference = "Continue"

$script:SourceRoot = "D:\drive_files\10.worksfree\10.rpa"

$script:Apps = @(
    @{ Name = "bom_exporter"; Path = "30.apps\bom_exporter" },
    @{ Name = "dwg_batch_print"; Path = "30.apps\dwg_batch_print" },
    @{ Name = "attribute_reset"; Path = "30.apps\attribute_reset" },
    @{ Name = "conversion_verifier"; Path = "50.data\conversion_verifier" },
    @{ Name = "dwg_classifier"; Path = "50.data\dwg_classifier" },
    @{ Name = "korean_filename_normalizer"; Path = "50.data\korean_filename_normalizer" }
)

# ============================================================================
# Helper Functions
# ============================================================================
function Write-Header {
    param([string]$Title)
    Write-Host "`n" -NoNewline
    Write-Host ("=" * 80) -ForegroundColor Cyan
    Write-Host "  $Title" -ForegroundColor Cyan
    Write-Host ("=" * 80) -ForegroundColor Cyan
}

function Write-AppRow {
    param(
        [string]$AppName,
        [hashtable]$Checks
    )

    $row = "  {0,-28}" -f $AppName
    foreach ($check in $Checks.GetEnumerator()) {
        $symbol = if ($check.Value) { "O" } else { "X" }
        $color = if ($check.Value) { "Green" } else { "Red" }
        Write-Host $row -NoNewline -ForegroundColor White
        Write-Host " $symbol " -NoNewline -ForegroundColor $color
        $row = ""
    }
    Write-Host ""
}

# ============================================================================
# Check Functions
# ============================================================================

# 1. Build Script Checks
function Check-BuildScripts {
    Write-Header "1. Build Script Consistency"

    $results = @{}

    foreach ($app in $script:Apps) {
        $buildScript = Join-Path $script:SourceRoot "$($app.Path)\build_$($app.Name).ps1"

        $checks = @{
            "Exists" = $false
            "Workaround" = $false
            "6 BATs" = $false
            "ReleasePath=Base" = $false
            "VerifyScript" = $false
        }

        if (Test-Path $buildScript) {
            $checks["Exists"] = $true
            $content = Get-Content $buildScript -Raw -Encoding UTF8

            # $BuildType array workaround
            $checks["Workaround"] = $content -match '\$BuildType\s+-is\s+\[System\.Object\[\]\]'

            # 6 BAT files in Copy-Portable (check for setup_worksfree.bat and batFiles variable)
            $hasSetup = $content -match "setup_worksfree\.bat"
            $hasBatFiles = $content -match '\$batFiles'
            $checks["6 BATs"] = $hasSetup -and $hasBatFiles

            # ReleasePath = $paths.Base (not $paths.Portable)
            $checks["ReleasePath=Base"] = $content -match '\$script:ReleasePath\s*=\s*\$paths\.Base'

            # VerifyScript variable
            $checks["VerifyScript"] = $content -match '\$script:VerifyScript'
        }

        $results[$app.Name] = $checks
    }

    # Print table header
    Write-Host "`n  App Name                     Exists Workaround 6BATs RelBase Verify" -ForegroundColor Yellow
    Write-Host "  " + ("-" * 70) -ForegroundColor DarkGray

    foreach ($app in $script:Apps) {
        $checks = $results[$app.Name]
        $row = "  {0,-28}" -f $app.Name

        foreach ($key in @("Exists", "Workaround", "6 BATs", "ReleasePath=Base", "VerifyScript")) {
            $val = $checks[$key]
            $symbol = if ($val) { "  O   " } else { "  X   " }
            $color = if ($val) { "Green" } else { "Red" }
            Write-Host $row -NoNewline -ForegroundColor White
            Write-Host $symbol -NoNewline -ForegroundColor $color
            $row = ""
        }
        Write-Host ""
    }

    return $results
}

# 2. ui_main.py Checks
function Check-UiMain {
    Write-Header "2. UI Main Consistency (--sync-registration)"

    $results = @{}

    foreach ($app in $script:Apps) {
        $uiMain = Join-Path $script:SourceRoot "$($app.Path)\ui_main.py"

        $checks = @{
            "Exists" = $false
            "SyncHandler" = $false
            "ArgvCheck" = $false
            "SheetsImport" = $false
        }

        if (Test-Path $uiMain) {
            $checks["Exists"] = $true
            $content = Get-Content $uiMain -Raw -Encoding UTF8

            # _handle_sync_registration function
            $checks["SyncHandler"] = $content -match 'def\s+_handle_sync_registration'

            # --sync-registration in sys.argv
            $checks["ArgvCheck"] = $content -match '--sync-registration.*sys\.argv' -or $content -match 'sys\.argv.*--sync-registration'

            # wf_googlesheets_manager import
            $checks["SheetsImport"] = $content -match 'from\s+wf_googlesheets_manager\s+import' -or $content -match 'import\s+wf_googlesheets_manager'
        }

        $results[$app.Name] = $checks
    }

    # Print table
    Write-Host "`n  App Name                     Exists Handler ArgvChk Sheets" -ForegroundColor Yellow
    Write-Host "  " + ("-" * 60) -ForegroundColor DarkGray

    foreach ($app in $script:Apps) {
        $checks = $results[$app.Name]
        $row = "  {0,-28}" -f $app.Name

        foreach ($key in @("Exists", "SyncHandler", "ArgvCheck", "SheetsImport")) {
            $val = $checks[$key]
            $symbol = if ($val) { "  O   " } else { "  X   " }
            $color = if ($val) { "Green" } else { "Red" }
            Write-Host $row -NoNewline -ForegroundColor White
            Write-Host $symbol -NoNewline -ForegroundColor $color
            $row = ""
        }
        Write-Host ""
    }

    return $results
}

# 3. app_setting_data.py Checks
function Check-AppSettings {
    Write-Header "3. App Setting Data Consistency"

    $results = @{}

    foreach ($app in $script:Apps) {
        $settingFile = Join-Path $script:SourceRoot "$($app.Path)\app_setting_data.py"

        $checks = @{
            "Exists" = $false
            "ConfigClass" = $false
            "PathLogic" = $false
            "Singleton" = $false
        }

        if (Test-Path $settingFile) {
            $checks["Exists"] = $true
            $content = Get-Content $settingFile -Raw -Encoding UTF8
            $lineCount = (Get-Content $settingFile).Count

            # Config class
            $checks["ConfigClass"] = $content -match 'class\s+Config' -or $content -match 'class\s+AppConfig'

            # Frozen path logic
            $checks["PathLogic"] = $content -match 'sys\.frozen' -or $content -match 'getattr\s*\(\s*sys\s*,\s*.frozen'

            # Singleton pattern
            $checks["Singleton"] = $content -match '_config_instance' -or $content -match 'get_config'
        }

        $results[$app.Name] = $checks
    }

    # Print table
    Write-Host "`n  App Name                     Exists Config PathLogic Singleton" -ForegroundColor Yellow
    Write-Host "  " + ("-" * 65) -ForegroundColor DarkGray

    foreach ($app in $script:Apps) {
        $checks = $results[$app.Name]
        $row = "  {0,-28}" -f $app.Name

        foreach ($key in @("Exists", "ConfigClass", "PathLogic", "Singleton")) {
            $val = $checks[$key]
            $symbol = if ($val) { "  O   " } else { "  X   " }
            $color = if ($val) { "Green" } else { "Red" }
            Write-Host $row -NoNewline -ForegroundColor White
            Write-Host $symbol -NoNewline -ForegroundColor $color
            $row = ""
        }
        Write-Host ""
    }

    return $results
}

# 4. Spec File Checks
function Check-SpecFiles {
    Write-Header "4. PyInstaller Spec File Consistency"

    $results = @{}

    foreach ($app in $script:Apps) {
        $specFile = Join-Path $script:SourceRoot "$($app.Path)\$($app.Name).spec"

        $checks = @{
            "Exists" = $false
            "WfRpaBundle" = $false
            "HiddenImports" = $false
            "Console=False" = $false
        }

        if (Test-Path $specFile) {
            $checks["Exists"] = $true
            $content = Get-Content $specFile -Raw -Encoding UTF8

            # .wf_rpa bundle
            $checks["WfRpaBundle"] = $content -match '\.wf_rpa' -or $content -match 'user_home_bundle'

            # hiddenimports
            $checks["HiddenImports"] = $content -match 'hiddenimports'

            # console=False
            $checks["Console=False"] = $content -match 'console\s*=\s*False'
        }

        $results[$app.Name] = $checks
    }

    # Print table
    Write-Host "`n  App Name                     Exists WfRpa Hidden NoConsole" -ForegroundColor Yellow
    Write-Host "  " + ("-" * 62) -ForegroundColor DarkGray

    foreach ($app in $script:Apps) {
        $checks = $results[$app.Name]
        $row = "  {0,-28}" -f $app.Name

        foreach ($key in @("Exists", "WfRpaBundle", "HiddenImports", "Console=False")) {
            $val = $checks[$key]
            $symbol = if ($val) { "  O   " } else { "  X   " }
            $color = if ($val) { "Green" } else { "Red" }
            Write-Host $row -NoNewline -ForegroundColor White
            Write-Host $symbol -NoNewline -ForegroundColor $color
            $row = ""
        }
        Write-Host ""
    }

    return $results
}

# ============================================================================
# Main
# ============================================================================
function Main {
    Write-Host "`n" -NoNewline
    Write-Host ("*" * 80) -ForegroundColor Magenta
    Write-Host "          WORKSFREE APP CONSISTENCY CHECKER" -ForegroundColor Magenta
    Write-Host ("*" * 80) -ForegroundColor Magenta
    Write-Host "Source Root: $script:SourceRoot" -ForegroundColor White

    $buildResults = Check-BuildScripts
    $uiResults = Check-UiMain
    $settingResults = Check-AppSettings
    $specResults = Check-SpecFiles

    # Summary
    Write-Header "SUMMARY"

    $totalChecks = 0
    $passedChecks = 0

    foreach ($results in @($buildResults, $uiResults, $settingResults, $specResults)) {
        foreach ($appChecks in $results.Values) {
            foreach ($check in $appChecks.Values) {
                $totalChecks++
                if ($check) { $passedChecks++ }
            }
        }
    }

    $failedChecks = $totalChecks - $passedChecks
    $passRate = [math]::Round(($passedChecks / $totalChecks) * 100, 1)

    Write-Host "Total Checks : $totalChecks" -ForegroundColor White
    Write-Host "Passed       : $passedChecks" -ForegroundColor Green
    Write-Host "Failed       : $failedChecks" -ForegroundColor $(if ($failedChecks -gt 0) { "Red" } else { "Green" })
    Write-Host "Pass Rate    : $passRate%" -ForegroundColor $(if ($passRate -ge 95) { "Green" } elseif ($passRate -ge 80) { "Yellow" } else { "Red" })

    # Issues List
    if ($failedChecks -gt 0) {
        Write-Host "`nIssues Found:" -ForegroundColor Yellow

        $issueNum = 1
        $allResults = @{
            "Build Script" = $buildResults
            "UI Main" = $uiResults
            "App Settings" = $settingResults
            "Spec File" = $specResults
        }

        foreach ($category in $allResults.Keys) {
            foreach ($appName in $allResults[$category].Keys) {
                $checks = $allResults[$category][$appName]
                foreach ($checkName in $checks.Keys) {
                    if (-not $checks[$checkName]) {
                        Write-Host "  $issueNum. [$appName] $category - $checkName" -ForegroundColor Red
                        $issueNum++
                    }
                }
            }
        }
    }

    if ($failedChecks -eq 0) {
        Write-Host "`nRESULT: ALL APPS CONSISTENT" -ForegroundColor Green -BackgroundColor DarkGreen
        exit 0
    } else {
        Write-Host "`nRESULT: INCONSISTENCIES FOUND" -ForegroundColor Red -BackgroundColor DarkRed
        exit 1
    }
}

Main
