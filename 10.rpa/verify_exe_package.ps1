# ============================================================================
# verify_exe_package.ps1
# ============================================================================
# 배포 패키지 완전성 검증 스크립트
# - 7개 앱의 exe 패키지 구조 검증
# - 크리덴셜 파일 포함 여부 확인
# - 버전 정보 정확성 검증
# - NSIS 설치 파일 존재 확인
#
# Usage:
#   .\verify_exe_package.ps1
#   .\verify_exe_package.ps1 -AppName bom_exporter
# ============================================================================

param(
    [string]$AppName = "",
    [string]$ReleaseDir = "D:\release"
)

$ErrorActionPreference = 'Continue'
$WarningPreference = 'Continue'

# 앱 목록 (BASIC_RULES.md 기준)
$ALL_APPS = @(
    @{Name='bom_exporter'; Display='BOM Exporter'},
    @{Name='dwg_batch_print'; Display='DWG Batch Print'},
    @{Name='attribute_reset'; Display='Attribute Reset'},
    @{Name='dwg_classifier'; Display='DWG Classifier'},
    @{Name='conversion_verifier'; Display='Conversion Verifier'},
    @{Name='korean_filename_normalizer'; Display='Korean Filename Normalizer'},
    @{Name='qrcode_generator'; Display='QR Code Generator'}
)

# Color codes
$COLOR_PASS = "Green"
$COLOR_FAIL = "Red"
$COLOR_WARN = "Yellow"
$COLOR_INFO = "Cyan"

# Results tracking
$script:TotalChecks = 0
$script:PassedChecks = 0
$script:FailedChecks = 0
$script:WarningChecks = 0

function Write-Result {
    param(
        [bool]$Passed,
        [string]$Message,
        [bool]$IsWarning = $false
    )
    
    $script:TotalChecks++
    
    if ($Passed) {
        $script:PassedChecks++
        Write-Host "  ✓ " -ForegroundColor $COLOR_PASS -NoNewline
        Write-Host $Message
    } elseif ($IsWarning) {
        $script:WarningChecks++
        Write-Host "  ⚠ " -ForegroundColor $COLOR_WARN -NoNewline
        Write-Host $Message
    } else {
        $script:FailedChecks++
        Write-Host "  ✗ " -ForegroundColor $COLOR_FAIL -NoNewline
        Write-Host $Message
    }
}

function Test-PackageStructure {
    param(
        [string]$AppName,
        [string]$VersionDir
    )
    
    Write-Host "`n[1] 패키지 구조 검증" -ForegroundColor $COLOR_INFO
    Write-Host "─────────────────────────────────────────" -ForegroundColor DarkGray
    
    # Check portable directory
    $portableDir = Get-ChildItem -Path $VersionDir -Directory -Filter "*_portable" | Select-Object -First 1
    
    if ($portableDir) {
        Write-Result $true "Portable 디렉토리 존재: $($portableDir.Name)"
        $exeDir = $portableDir.FullName
    } else {
        Write-Result $false "Portable 디렉토리 없음 (빌드 실패 가능성)" $true
        $exeDir = $VersionDir
    }
    
    # Check exe file
    $exePath = Join-Path $exeDir "$AppName.exe"
    $exeExists = Test-Path $exePath
    Write-Result $exeExists "실행 파일 존재: $AppName.exe"
    
    if ($exeExists) {
        $exeSize = (Get-Item $exePath).Length / 1MB
        Write-Result ($exeSize -gt 5) "실행 파일 크기: $($exeSize.ToString('F1'))MB (최소 5MB)"
    }
    
    # Check _internal directory
    $internalDir = Join-Path $exeDir "_internal"
    $internalExists = Test-Path $internalDir
    Write-Result $internalExists "_internal 디렉토리 존재 (PyInstaller 번들)"
    
    return @{
        ExeDir = $exeDir
        InternalDir = $internalDir
        Success = $exeExists -and $internalExists
    }
}

function Test-CredentialFiles {
    param(
        [string]$InternalDir
    )
    
    Write-Host "`n[2] 크리덴셜 파일 검증" -ForegroundColor $COLOR_INFO
    Write-Host "─────────────────────────────────────────" -ForegroundColor DarkGray
    
    # RELEASE credential (worksfree-*.json)
    $releaseCredFiles = Get-ChildItem -Path $InternalDir -Filter "worksfree-*.json" -ErrorAction SilentlyContinue
    
    if ($releaseCredFiles) {
        Write-Result $true "RELEASE 크리덴셜 포함: $($releaseCredFiles[0].Name)"
        
        # Check file size
        $size = $releaseCredFiles[0].Length
        Write-Result ($size -gt 1KB) "크리덴셜 파일 크기: $size bytes (최소 1KB)"
        
        # Validate JSON
        try {
            $credData = Get-Content $releaseCredFiles[0].FullName -Raw | ConvertFrom-Json
            Write-Result ($credData.type -eq 'service_account') "크리덴셜 타입: $($credData.type)"
            Write-Result ($null -ne $credData.project_id) "프로젝트 ID: $($credData.project_id)"
            Write-Result ($null -ne $credData.private_key) "Private Key 존재"
        } catch {
            Write-Result $false "JSON 파싱 실패: $_"
        }
    } else {
        Write-Result $false "RELEASE 크리덴셜 누락 (worksfree-*.json)"
    }
    
    # DEV credential (silver-argon-*.json)
    $devCredFiles = Get-ChildItem -Path $InternalDir -Filter "silver-argon-*.json" -ErrorAction SilentlyContinue
    
    if ($devCredFiles) {
        Write-Result $true "DEV 크리덴셜 포함: $($devCredFiles[0].Name)"
    } else {
        Write-Result $false "DEV 크리덴셜 누락 (silver-argon-*.json)" $true
    }
}

function Test-BundleSettings {
    param(
        [string]$InternalDir,
        [string]$AppName,
        [string]$ExpectedVersion
    )
    
    Write-Host "`n[3] 번들 설정 검증" -ForegroundColor $COLOR_INFO
    Write-Host "─────────────────────────────────────────" -ForegroundColor DarkGray
    
    # Check .wf_rpa bundle directory
    $wfRpaDir = Join-Path $InternalDir ".wf_rpa"
    Write-Result (Test-Path $wfRpaDir) "번들 설정 디렉토리 존재: .wf_rpa"
    
    # Check app settings.json
    $settingsPath = Join-Path $wfRpaDir "$AppName\settings.json"
    $settingsExists = Test-Path $settingsPath
    Write-Result $settingsExists "앱 설정 파일 존재: $AppName\settings.json"
    
    if ($settingsExists) {
        try {
            $settings = Get-Content $settingsPath -Raw | ConvertFrom-Json
            $runtimeConfig = $settings.runtime_config
            $fullVersion = $runtimeConfig.full_version
            
            Write-Result ($null -ne $fullVersion) "버전 정보 존재: $fullVersion"
            
            if ($fullVersion -and $ExpectedVersion) {
                $match = $fullVersion -eq $ExpectedVersion
                Write-Result $match "버전 일치: 예상=$ExpectedVersion, 실제=$fullVersion"
            }
            
            # Check version format (vX.Y.Z.B)
            if ($fullVersion -match '^v\d+\.\d+\.\d+\.\d+$') {
                Write-Result $true "버전 형식 유효: $fullVersion"
            } else {
                Write-Result $false "버전 형식 오류: $fullVersion (예상: v1.0.0.1)"
            }
            
        } catch {
            Write-Result $false "설정 파일 파싱 실패: $_"
        }
    }
    
    # Check wf_rpa_config.json
    $configPath = Join-Path $wfRpaDir "wf_rpa_config.json"
    $configExists = Test-Path $configPath
    Write-Result $configExists "공통 설정 파일 존재: wf_rpa_config.json"
    
    if ($configExists) {
        try {
            $config = Get-Content $configPath -Raw | ConvertFrom-Json
            $gsConfig = $config.google_sheets
            
            Write-Result ($null -ne $gsConfig.sheet_id_release) "sheet_id_release 설정됨"
            Write-Result ($null -ne $gsConfig.sheet_id_dev) "sheet_id_dev 설정됨"
            Write-Result ($null -ne $gsConfig.credentials_file_release) "credentials_file_release 설정됨"
            Write-Result ($null -ne $gsConfig.credentials_file_dev) "credentials_file_dev 설정됨"
            
        } catch {
            Write-Result $false "공통 설정 파일 파싱 실패: $_"
        }
    }
}

function Test-NSISInstaller {
    param(
        [string]$VersionDir,
        [string]$AppName
    )
    
    Write-Host "`n[4] NSIS 설치 파일 검증" -ForegroundColor $COLOR_INFO
    Write-Host "─────────────────────────────────────────" -ForegroundColor DarkGray
    
    $installerName = "${AppName}_installer.exe"
    $installerPath = Join-Path $VersionDir $installerName
    $installerExists = Test-Path $installerPath
    
    Write-Result $installerExists "설치 파일 존재: $installerName"
    
    if ($installerExists) {
        $installerSize = (Get-Item $installerPath).Length / 1MB
        Write-Result ($installerSize -gt 10) "설치 파일 크기: $($installerSize.ToString('F1'))MB (최소 10MB)"
    }
}

function Test-AppPackage {
    param(
        [hashtable]$App
    )
    
    $appName = $App.Name
    $displayName = $App.Display
    
    Write-Host "`n╔═══════════════════════════════════════════════════════════════╗" -ForegroundColor $COLOR_INFO
    Write-Host "║  Testing: $displayName ($appName)" -ForegroundColor $COLOR_INFO
    Write-Host "╚═══════════════════════════════════════════════════════════════╝" -ForegroundColor $COLOR_INFO
    
    # Find latest version directory
    $pattern = "${appName}_v*"
    $versionDirs = Get-ChildItem -Path $ReleaseDir -Directory -Filter $pattern -ErrorAction SilentlyContinue
    
    if (-not $versionDirs) {
        Write-Result $false "빌드 결과물 없음: $ReleaseDir\${pattern}"
        return
    }
    
    # Get latest version
    $latestDir = $versionDirs | Sort-Object Name -Descending | Select-Object -First 1
    $expectedVersion = $latestDir.Name -replace "${appName}_", ""
    
    Write-Host "`nVersion: $expectedVersion" -ForegroundColor $COLOR_INFO
    Write-Host "Path: $($latestDir.FullName)" -ForegroundColor DarkGray
    
    # Run all checks
    $structureResult = Test-PackageStructure -AppName $appName -VersionDir $latestDir.FullName
    
    if ($structureResult.Success) {
        Test-CredentialFiles -InternalDir $structureResult.InternalDir
        Test-BundleSettings -InternalDir $structureResult.InternalDir -AppName $appName -ExpectedVersion $expectedVersion
        Test-NSISInstaller -VersionDir $latestDir.FullName -AppName $appName
    }
}

# ============================================================================
# Main Execution
# ============================================================================

Write-Host "`n╔═══════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║       WF-RPA 배포 패키지 완전성 검증                          ║" -ForegroundColor Cyan
Write-Host "╚═══════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan

Write-Host "`nRelease Directory: $ReleaseDir" -ForegroundColor $COLOR_INFO

# Filter apps if specific app requested
$appsToTest = $ALL_APPS
if ($AppName) {
    $appsToTest = $ALL_APPS | Where-Object { $_.Name -eq $AppName }
    if (-not $appsToTest) {
        Write-Host "Error: Unknown app '$AppName'" -ForegroundColor Red
        exit 1
    }
}

# Run tests for each app
foreach ($app in $appsToTest) {
    Test-AppPackage -App $app
}

# ============================================================================
# Summary
# ============================================================================

Write-Host "`n╔═══════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  검증 요약                                                     ║" -ForegroundColor Cyan
Write-Host "╚═══════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan

Write-Host "`n  총 검사 항목: $script:TotalChecks"
Write-Host "  통과: " -NoNewline
Write-Host "$script:PassedChecks" -ForegroundColor $COLOR_PASS
Write-Host "  실패: " -NoNewline
Write-Host "$script:FailedChecks" -ForegroundColor $COLOR_FAIL
Write-Host "  경고: " -NoNewline
Write-Host "$script:WarningChecks" -ForegroundColor $COLOR_WARN

$successRate = if ($script:TotalChecks -gt 0) { 
    [math]::Round(($script:PassedChecks / $script:TotalChecks) * 100, 1) 
} else { 
    0 
}

Write-Host "`n  성공률: $successRate%" -ForegroundColor $(if ($successRate -ge 90) { $COLOR_PASS } elseif ($successRate -ge 70) { $COLOR_WARN } else { $COLOR_FAIL })

if ($script:FailedChecks -eq 0) {
    Write-Host "`n✓ 모든 검증 통과!" -ForegroundColor $COLOR_PASS
    exit 0
} else {
    Write-Host "`n✗ 검증 실패 - 위 항목들을 확인하세요." -ForegroundColor $COLOR_FAIL
    exit 1
}
