# ============================================================================
# WorksFree Deployment Package Test Suite v1.0
# ============================================================================
# Purpose: Comprehensive testing of deployment packages before release
# Usage: .\test_deployment_package.ps1 [-App <app_name>] [-All] [-Quick] [-Verbose]
# ============================================================================

param(
    [string]$App = "",                    # 특정 앱만 테스트 (예: bom_exporter)
    [switch]$All,                         # 모든 6개 앱 테스트
    [switch]$Quick,                       # 빠른 테스트 (실행 테스트 생략)
    [string]$BuildRoot = "D:\release\candidates",
    [switch]$Verbose
)

$ErrorActionPreference = "Continue"

# ============================================================================
# Configuration
# ============================================================================
$script:AllApps = @(
    @{ Name = "bom_exporter"; DisplayName = "Bom Exporter"; Category = "30.apps" },
    @{ Name = "dwg_batch_print"; DisplayName = "DWG Batch Print"; Category = "30.apps" },
    @{ Name = "attribute_reset"; DisplayName = "Attribute Reset"; Category = "30.apps" },
    @{ Name = "conversion_verifier"; DisplayName = "Conversion Verifier"; Category = "50.data" },
    @{ Name = "dwg_classifier"; DisplayName = "DWG Classifier"; Category = "50.data" },
    @{ Name = "korean_filename_normalizer"; DisplayName = "Korean Filename Normalizer"; Category = "50.data" }
)

$script:Results = @{
    Total = 0
    Passed = 0
    Failed = 0
    Warnings = 0
    Skipped = 0
}

$script:AppResults = @{}

# ============================================================================
# Helper Functions
# ============================================================================
function Write-TestHeader {
    param([string]$Title)
    Write-Host "`n" -NoNewline
    Write-Host ("=" * 80) -ForegroundColor Magenta
    Write-Host "  $Title" -ForegroundColor Magenta
    Write-Host ("=" * 80) -ForegroundColor Magenta
}

function Write-SectionHeader {
    param([string]$Title)
    Write-Host "`n[$Title]" -ForegroundColor Cyan
    Write-Host ("-" * 60) -ForegroundColor DarkGray
}

function Write-TestResult {
    param(
        [string]$TestName,
        [string]$Status,  # PASS, FAIL, WARN, SKIP
        [string]$Message = ""
    )

    $script:Results.Total++

    $icon = switch ($Status) {
        "PASS" { "[PASS]"; $script:Results.Passed++ }
        "FAIL" { "[FAIL]"; $script:Results.Failed++ }
        "WARN" { "[WARN]"; $script:Results.Warnings++ }
        "SKIP" { "[SKIP]"; $script:Results.Skipped++ }
        default { "[????]" }
    }

    $color = switch ($Status) {
        "PASS" { "Green" }
        "FAIL" { "Red" }
        "WARN" { "Yellow" }
        "SKIP" { "DarkGray" }
        default { "White" }
    }

    Write-Host "  $icon " -ForegroundColor $color -NoNewline
    Write-Host $TestName -NoNewline
    if ($Message) {
        Write-Host " - $Message" -ForegroundColor Gray
    } else {
        Write-Host ""
    }
}

function Get-LatestPackage {
    param([string]$AppName)

    $folders = Get-ChildItem -Path $BuildRoot -Directory -Filter "${AppName}_*" -ErrorAction SilentlyContinue |
               Sort-Object LastWriteTime -Descending

    if ($folders.Count -eq 0) { return $null }

    $latestFolder = $folders[0]
    $portableFolder = Get-ChildItem -Path $latestFolder.FullName -Directory -Filter "*_portable" -ErrorAction SilentlyContinue |
                      Select-Object -First 1

    if ($portableFolder) {
        return @{
            Base = $latestFolder.FullName
            Portable = $portableFolder.FullName
            Version = if ($latestFolder.Name -match "v?(\d+\.\d+\.\d+\.\d+)") { $matches[1] } else { "unknown" }
        }
    }
    return $null
}

# ============================================================================
# Test Categories
# ============================================================================

# 1. Structure Tests
function Test-PackageStructure {
    param([string]$AppName, [hashtable]$Package)

    Write-SectionHeader "1. Package Structure"

    $portablePath = $Package.Portable

    # EXE 파일
    $exePath = Join-Path $portablePath "$AppName.exe"
    if (Test-Path $exePath) {
        $exeSize = (Get-Item $exePath).Length / 1MB
        Write-TestResult "Main executable" "PASS" "$AppName.exe ($([math]::Round($exeSize, 2)) MB)"
    } else {
        Write-TestResult "Main executable" "FAIL" "$AppName.exe not found"
    }

    # _internal 폴더
    $internalPath = Join-Path $portablePath "_internal"
    if (Test-Path $internalPath) {
        $fileCount = (Get-ChildItem $internalPath -Recurse -File).Count
        Write-TestResult "_internal directory" "PASS" "$fileCount files"
    } else {
        Write-TestResult "_internal directory" "FAIL" "Missing"
    }

    # .wf_rpa 폴더
    $wfRpaPath = Join-Path $internalPath ".wf_rpa"
    if (Test-Path $wfRpaPath) {
        Write-TestResult ".wf_rpa directory" "PASS" "Found"
    } else {
        Write-TestResult ".wf_rpa directory" "FAIL" "Missing"
        return
    }

    # 앱별 설정 폴더
    $appConfigPath = Join-Path $wfRpaPath $AppName
    if (Test-Path $appConfigPath) {
        Write-TestResult "App config directory" "PASS" ".wf_rpa\$AppName"
    } else {
        Write-TestResult "App config directory" "FAIL" "Missing .wf_rpa\$AppName"
    }
}

# 2. Configuration Tests
function Test-ConfigurationFiles {
    param([string]$AppName, [hashtable]$Package)

    Write-SectionHeader "2. Configuration Files"

    $wfRpaPath = Join-Path $Package.Portable "_internal\.wf_rpa"

    # wf_rpa_config.json
    $configPath = Join-Path $wfRpaPath "wf_rpa_config.json"
    if (Test-Path $configPath) {
        try {
            $config = Get-Content $configPath -Raw -Encoding UTF8 | ConvertFrom-Json
            Write-TestResult "wf_rpa_config.json" "PASS" "Valid JSON"

            # google_sheets 섹션
            if ($config.google_sheets -and ($config.google_sheets.sheet_id_release -or $config.google_sheets.sheet_id_dev)) {
                Write-TestResult "  google_sheets config" "PASS" "sheet_id configured"
            } else {
                Write-TestResult "  google_sheets config" "WARN" "Not configured"
            }

            # email_settings 섹션
            if ($config.email_settings -and $config.email_settings.smtp_server) {
                Write-TestResult "  email_settings config" "PASS" "SMTP configured"
            } else {
                Write-TestResult "  email_settings config" "WARN" "Not configured"
            }
        } catch {
            Write-TestResult "wf_rpa_config.json" "FAIL" "Invalid JSON: $($_.Exception.Message)"
        }
    } else {
        Write-TestResult "wf_rpa_config.json" "FAIL" "Not found"
    }

    # settings.json (앱별)
    $settingsPath = Join-Path $wfRpaPath "$AppName\settings.json"
    if (Test-Path $settingsPath) {
        try {
            $settings = Get-Content $settingsPath -Raw -Encoding UTF8 | ConvertFrom-Json
            $version = $settings.runtime_config.full_version
            Write-TestResult "settings.json" "PASS" "Version: $version"
        } catch {
            Write-TestResult "settings.json" "FAIL" "Invalid JSON"
        }
    } else {
        Write-TestResult "settings.json" "FAIL" "Not found"
    }

    # policy.json
    $policyPath = Join-Path $wfRpaPath "$AppName\policy.json"
    if (Test-Path $policyPath) {
        try {
            $policy = Get-Content $policyPath -Raw -Encoding UTF8 | ConvertFrom-Json
            $trialCredits = $policy.trial_credits
            Write-TestResult "policy.json" "PASS" "Trial credits: $trialCredits"
        } catch {
            Write-TestResult "policy.json" "WARN" "Invalid JSON"
        }
    } else {
        Write-TestResult "policy.json" "WARN" "Not found (optional)"
    }
}

# 3. Credential Tests
function Test-Credentials {
    param([string]$AppName, [hashtable]$Package)

    Write-SectionHeader "3. Credentials"

    $wfRpaPath = Join-Path $Package.Portable "_internal\.wf_rpa"

    # Google Sheets credentials
    $credFiles = Get-ChildItem -Path $wfRpaPath -Filter "*silver-argon*.json" -ErrorAction SilentlyContinue
    if ($credFiles.Count -gt 0) {
        $credFile = $credFiles[0]
        try {
            $cred = Get-Content $credFile.FullName -Raw -Encoding UTF8 | ConvertFrom-Json

            # 필수 필드 확인
            $requiredFields = @("type", "project_id", "private_key", "client_email")
            $missingFields = $requiredFields | Where-Object { -not $cred.$_ }

            if ($missingFields.Count -eq 0) {
                Write-TestResult "Google credentials" "PASS" "$($credFile.Name) ($($credFile.Length) bytes)"
            } else {
                Write-TestResult "Google credentials" "FAIL" "Missing fields: $($missingFields -join ', ')"
            }
        } catch {
            Write-TestResult "Google credentials" "FAIL" "Invalid JSON"
        }
    } else {
        Write-TestResult "Google credentials" "FAIL" "Not found"
    }
}

# 4. BAT Scripts Tests
function Test-BatScripts {
    param([string]$AppName, [hashtable]$Package)

    Write-SectionHeader "4. BAT Scripts (User Tools)"

    $portablePath = $Package.Portable

    $expectedBats = @(
        "setup_worksfree.bat",
        "바로가기_생성.bat",
        "설정_초기화.bat",
        "전체_초기화.bat",
        "등록정보_동기화.bat",
        "제거.bat"
    )

    $foundCount = 0
    foreach ($bat in $expectedBats) {
        $batPath = Join-Path $portablePath $bat
        if (Test-Path $batPath) {
            $foundCount++
            if ($Verbose) {
                Write-TestResult $bat "PASS" "Found"
            }
        } else {
            Write-TestResult $bat "FAIL" "Missing"
        }
    }

    if (-not $Verbose -and $foundCount -eq $expectedBats.Count) {
        Write-TestResult "All BAT scripts" "PASS" "$foundCount / $($expectedBats.Count) scripts"
    } elseif (-not $Verbose -and $foundCount -gt 0) {
        Write-TestResult "BAT scripts" "WARN" "$foundCount / $($expectedBats.Count) scripts found"
    }
}

# 5. Python Modules Test
function Test-PythonModules {
    param([string]$AppName, [hashtable]$Package)

    Write-SectionHeader "5. Python Modules"

    $internalPath = Join-Path $Package.Portable "_internal"

    # 공통 필수 모듈
    $commonModules = @("gspread", "google", "requests", "urllib3")

    foreach ($module in $commonModules) {
        $modulePath = Join-Path $internalPath $module
        if (Test-Path $modulePath) {
            Write-TestResult $module "PASS" "Found in _internal"
        } else {
            # PYZ 파일 확인
            $pyzFiles = Get-ChildItem -Path $internalPath -Filter "*.pyz" -ErrorAction SilentlyContinue
            if ($pyzFiles.Count -gt 0) {
                Write-TestResult $module "WARN" "Not in _internal (may be in PYZ)"
            } else {
                Write-TestResult $module "FAIL" "Not found"
            }
        }
    }
}

# 6. Execution Test
function Test-Execution {
    param([string]$AppName, [hashtable]$Package)

    Write-SectionHeader "6. Execution Test"

    $exePath = Join-Path $Package.Portable "$AppName.exe"

    if (-not (Test-Path $exePath)) {
        Write-TestResult "Execution test" "SKIP" "EXE not found"
        return
    }

    Write-Host "  Starting $AppName.exe with --help..." -ForegroundColor Gray

    try {
        $psi = New-Object System.Diagnostics.ProcessStartInfo
        $psi.FileName = $exePath
        $psi.Arguments = "--help"
        $psi.UseShellExecute = $false
        $psi.RedirectStandardOutput = $true
        $psi.RedirectStandardError = $true
        $psi.CreateNoWindow = $true
        $psi.WorkingDirectory = $Package.Portable

        $process = [System.Diagnostics.Process]::Start($psi)
        $exited = $process.WaitForExit(10000)  # 10초 타임아웃

        if (-not $exited) {
            $process.Kill()
            Write-TestResult "Execution test" "WARN" "Timeout (app may need GUI)"
        } elseif ($process.ExitCode -eq 0) {
            Write-TestResult "Execution test" "PASS" "Exited normally"
        } else {
            $stderr = $process.StandardError.ReadToEnd()
            if ($stderr -like "*import*" -or $stderr -like "*ModuleNotFoundError*") {
                Write-TestResult "Execution test" "FAIL" "Module import error"
                if ($Verbose) { Write-Host "    Error: $stderr" -ForegroundColor Red }
            } else {
                Write-TestResult "Execution test" "WARN" "Exit code: $($process.ExitCode)"
            }
        }
    } catch {
        Write-TestResult "Execution test" "FAIL" $_.Exception.Message
    }
}

# 7. Sync Registration Test
function Test-SyncRegistration {
    param([string]$AppName, [hashtable]$Package)

    Write-SectionHeader "7. Sync Registration Test"

    $exePath = Join-Path $Package.Portable "$AppName.exe"

    if (-not (Test-Path $exePath)) {
        Write-TestResult "Sync registration" "SKIP" "EXE not found"
        return
    }

    Write-Host "  Testing --sync-registration argument..." -ForegroundColor Gray

    try {
        $psi = New-Object System.Diagnostics.ProcessStartInfo
        $psi.FileName = $exePath
        $psi.Arguments = "--sync-registration"
        $psi.UseShellExecute = $false
        $psi.RedirectStandardOutput = $true
        $psi.RedirectStandardError = $true
        $psi.CreateNoWindow = $true
        $psi.WorkingDirectory = $Package.Portable

        $process = [System.Diagnostics.Process]::Start($psi)
        $exited = $process.WaitForExit(30000)  # 30초 타임아웃

        $stdout = $process.StandardOutput.ReadToEnd()

        if (-not $exited) {
            $process.Kill()
            Write-TestResult "Sync registration" "WARN" "Timeout"
        } elseif ($stdout -like "*동기화*" -or $stdout -like "*sync*") {
            Write-TestResult "Sync registration" "PASS" "Handler responded"
        } else {
            Write-TestResult "Sync registration" "WARN" "No sync message in output"
        }
    } catch {
        Write-TestResult "Sync registration" "FAIL" $_.Exception.Message
    }
}

# ============================================================================
# Main Test Runner
# ============================================================================
function Test-SingleApp {
    param([hashtable]$AppInfo)

    $appName = $AppInfo.Name

    Write-TestHeader "Testing: $($AppInfo.DisplayName) ($appName)"

    $package = Get-LatestPackage -AppName $appName

    if (-not $package) {
        Write-Host "  ERROR: No package found for $appName in $BuildRoot" -ForegroundColor Red
        $script:Results.Failed++
        $script:Results.Total++
        return
    }

    Write-Host "Package: $($package.Base)" -ForegroundColor White
    Write-Host "Version: $($package.Version)" -ForegroundColor White

    # Run all tests
    Test-PackageStructure -AppName $appName -Package $package
    Test-ConfigurationFiles -AppName $appName -Package $package
    Test-Credentials -AppName $appName -Package $package
    Test-BatScripts -AppName $appName -Package $package
    Test-PythonModules -AppName $appName -Package $package

    if (-not $Quick) {
        Test-Execution -AppName $appName -Package $package
        Test-SyncRegistration -AppName $appName -Package $package
    }
}

# ============================================================================
# Entry Point
# ============================================================================
function Main {
    Write-Host "`n" -NoNewline
    Write-Host ("*" * 80) -ForegroundColor Cyan
    Write-Host "          WORKSFREE DEPLOYMENT PACKAGE TEST SUITE" -ForegroundColor Cyan
    Write-Host ("*" * 80) -ForegroundColor Cyan
    Write-Host "Build Root: $BuildRoot" -ForegroundColor White
    Write-Host "Mode: $(if ($Quick) { 'Quick (no execution tests)' } else { 'Full' })" -ForegroundColor White

    $appsToTest = @()

    if ($All) {
        $appsToTest = $script:AllApps
    } elseif ($App) {
        $appInfo = $script:AllApps | Where-Object { $_.Name -eq $App }
        if ($appInfo) {
            $appsToTest = @($appInfo)
        } else {
            Write-Host "ERROR: Unknown app '$App'" -ForegroundColor Red
            Write-Host "Available apps: $($script:AllApps.Name -join ', ')" -ForegroundColor Yellow
            exit 1
        }
    } else {
        # 인자 없이 실행 시 도움말 표시
        Write-Host "`nUsage:" -ForegroundColor Yellow
        Write-Host "  .\test_deployment_package.ps1 -App bom_exporter    # 특정 앱 테스트"
        Write-Host "  .\test_deployment_package.ps1 -All                 # 전체 앱 테스트"
        Write-Host "  .\test_deployment_package.ps1 -All -Quick          # 빠른 테스트 (실행 생략)"
        Write-Host "  .\test_deployment_package.ps1 -All -Verbose        # 상세 출력"
        Write-Host "`nAvailable apps:" -ForegroundColor Yellow
        foreach ($app in $script:AllApps) {
            Write-Host "  - $($app.Name) ($($app.DisplayName))"
        }
        exit 0
    }

    foreach ($appInfo in $appsToTest) {
        Test-SingleApp -AppInfo $appInfo
    }

    # Final Summary
    Write-Host "`n" -NoNewline
    Write-Host ("=" * 80) -ForegroundColor Magenta
    Write-Host "          TEST SUMMARY" -ForegroundColor Magenta
    Write-Host ("=" * 80) -ForegroundColor Magenta

    Write-Host "Total Tests : $($script:Results.Total)" -ForegroundColor White
    Write-Host "Passed      : $($script:Results.Passed)" -ForegroundColor Green
    Write-Host "Failed      : $($script:Results.Failed)" -ForegroundColor Red
    Write-Host "Warnings    : $($script:Results.Warnings)" -ForegroundColor Yellow
    Write-Host "Skipped     : $($script:Results.Skipped)" -ForegroundColor DarkGray

    $passRate = if ($script:Results.Total -gt 0) {
        [math]::Round(($script:Results.Passed / ($script:Results.Total - $script:Results.Skipped)) * 100, 1)
    } else { 0 }

    Write-Host "`nPass Rate   : $passRate%" -ForegroundColor $(if ($passRate -ge 90) { "Green" } elseif ($passRate -ge 70) { "Yellow" } else { "Red" })

    if ($script:Results.Failed -gt 0) {
        Write-Host "`nRESULT: TESTS FAILED" -ForegroundColor Red -BackgroundColor DarkRed
        exit 1
    } elseif ($script:Results.Warnings -gt 0) {
        Write-Host "`nRESULT: PASSED WITH WARNINGS" -ForegroundColor Yellow
        exit 0
    } else {
        Write-Host "`nRESULT: ALL TESTS PASSED" -ForegroundColor Green -BackgroundColor DarkGreen
        exit 0
    }
}

# Run
Main
