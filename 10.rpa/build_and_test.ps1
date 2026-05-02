# build_and_test.ps1 - 빌드 + 배포 테스트 통합 스크립트
# 사용법:
#   .\build_and_test.ps1 -App be              # BE 빌드 + 퀵 테스트
#   .\build_and_test.ps1 -App be -Register    # BE 빌드 + 등록 테스트
#   .\build_and_test.ps1 -App dc -TestOnly    # DC 테스트만 (빌드 스킵)
#   .\build_and_test.ps1 -App all             # 모든 앱 빌드 + 테스트

param(
    [ValidateSet('be', 'bom_exporter', 'dc', 'dwg_classifier', 'cv', 'conversion_verifier',
                 'bp', 'batch_print', 'ar', 'attribute_reset', 'kfn', 'korean_filename_normalizer',
                 'qg', 'qrcode_generator', 'all')]
    [string]$App = 'be',

    [switch]$TestOnly,      # 빌드 스킵, 테스트만
    [switch]$BuildOnly,     # 빌드만, 테스트 스킵
    [switch]$Register,      # 등록 테스트 포함
    [switch]$Reset,         # 테스트 전 설정 초기화
    [switch]$Quick,         # 퀵 테스트만 (기본)
    [switch]$NoShortcut,    # 바탕화면 바로가기 생성 안함
    [int]$BuildType = 1     # PyInstaller 빌드 타입 (1=onedir)
)

$ErrorActionPreference = 'Stop'
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = 'C:\Python313\python.exe'
$TesterScript = Join-Path $ScriptDir '90.tests\e2e\deployed_app_tester.py'

# 앱 이름 정규화
$AppMap = @{
    'be' = 'bom_exporter'
    'bom_exporter' = 'bom_exporter'
    'dc' = 'dwg_classifier'
    'dwg_classifier' = 'dwg_classifier'
    'cv' = 'conversion_verifier'
    'conversion_verifier' = 'conversion_verifier'
    'bp' = 'batch_print'
    'batch_print' = 'batch_print'
    'ar' = 'attribute_reset'
    'attribute_reset' = 'attribute_reset'
    'kfn' = 'korean_filename_normalizer'
    'korean_filename_normalizer' = 'korean_filename_normalizer'
    'qg' = 'qrcode_generator'
    'qrcode_generator' = 'qrcode_generator'
}

# 앱별 빌드 스크립트 경로
$BuildScripts = @{
    'bom_exporter' = '30.apps\bom_exporter\build_bom_exporter.ps1'
    'dwg_classifier' = '50.data\dwg_classifier\build_dwg_classifier.ps1'
    'conversion_verifier' = '50.data\conversion_verifier\build_conversion_verifier.ps1'
    'batch_print' = '30.apps\batch_print\build_batch_print.ps1'
    'attribute_reset' = '30.apps\attribute_reset\build_attribute_reset.ps1'
    'korean_filename_normalizer' = '50.data\korean_filename_normalizer\build_korean_filename_normalizer.ps1'
    'qrcode_generator' = '50.data\qrcode_generator\build_qrcode_generator.ps1'
}

function Write-Banner($text) {
    Write-Host ""
    Write-Host ("=" * 60) -ForegroundColor Cyan
    Write-Host "  $text" -ForegroundColor Cyan
    Write-Host ("=" * 60) -ForegroundColor Cyan
    Write-Host ""
}

function Build-App($appName) {
    $buildScript = Join-Path $ScriptDir $BuildScripts[$appName]

    if (!(Test-Path $buildScript)) {
        Write-Host "❌ Build script not found: $buildScript" -ForegroundColor Red
        return $false
    }

    Write-Banner "Building $appName"
    Write-Host "Script: $buildScript" -ForegroundColor Gray
    Write-Host "BuildType: $BuildType" -ForegroundColor Gray
    Write-Host ""

    try {
        Push-Location (Split-Path $buildScript -Parent)
        & $buildScript -BuildType $BuildType
        $exitCode = $LASTEXITCODE
        Pop-Location

        if ($exitCode -ne 0) {
            Write-Host "❌ Build failed with exit code $exitCode" -ForegroundColor Red
            return $false
        }

        Write-Host "✅ Build completed successfully" -ForegroundColor Green
        return $true
    }
    catch {
        Pop-Location
        Write-Host "❌ Build error: $_" -ForegroundColor Red
        return $false
    }
}

function Test-App($appName) {
    if (!(Test-Path $TesterScript)) {
        Write-Host "❌ Tester script not found: $TesterScript" -ForegroundColor Red
        return $false
    }

    Write-Banner "Testing $appName"

    $testArgs = @($TesterScript, $appName)

    if ($Quick -or (!$Register)) {
        $testArgs += '--quick'
    }

    if ($Register) {
        $testArgs += '--register'
    }

    if ($Reset) {
        $testArgs += '--reset'
    }

    Write-Host "Command: python $($testArgs -join ' ')" -ForegroundColor Gray
    Write-Host ""

    try {
        & $Python @testArgs
        $exitCode = $LASTEXITCODE

        if ($exitCode -ne 0) {
            Write-Host "❌ Tests failed" -ForegroundColor Red
            return $false
        }

        Write-Host "✅ Tests passed" -ForegroundColor Green
        return $true
    }
    catch {
        Write-Host "❌ Test error: $_" -ForegroundColor Red
        return $false
    }
}

function Process-App($appName) {
    $buildOk = $true
    $testOk = $true

    # 빌드
    if (!$TestOnly) {
        $buildOk = Build-App $appName
        if (!$buildOk) {
            return @{ App = $appName; Build = $false; Test = $false }
        }
    }

    # 테스트
    if (!$BuildOnly) {
        # 빌드 후 잠시 대기 (파일 잠금 해제)
        if (!$TestOnly) {
            Write-Host "`nWaiting 3 seconds before testing..." -ForegroundColor Gray
            Start-Sleep -Seconds 3
        }

        $testOk = Test-App $appName
    }

    return @{ App = $appName; Build = $buildOk; Test = $testOk }
}

# 메인 실행
Write-Banner "WF-RPA Build & Test Runner"
Write-Host "App: $App" -ForegroundColor White
Write-Host "Mode: $(if($TestOnly){'Test Only'}elseif($BuildOnly){'Build Only'}else{'Build + Test'})" -ForegroundColor White
Write-Host "Register Test: $Register" -ForegroundColor White
Write-Host ""

$results = @()
$startTime = Get-Date

if ($App -eq 'all') {
    # 모든 앱 처리
    foreach ($key in $AppMap.Keys | Where-Object { $_ -notmatch '_' } | Sort-Object) {
        $appName = $AppMap[$key]
        if ($BuildScripts.ContainsKey($appName)) {
            $results += Process-App $appName
        }
    }
}
else {
    # 단일 앱 처리
    $appName = $AppMap[$App]
    if (!$appName) {
        Write-Host "❌ Unknown app: $App" -ForegroundColor Red
        exit 1
    }
    $results += Process-App $appName
}

$endTime = Get-Date
$duration = $endTime - $startTime

# 결과 요약
Write-Banner "Summary"

$allPassed = $true
foreach ($r in $results) {
    $buildStatus = if ($TestOnly) { "⏭️ Skip" } elseif ($r.Build) { "✅ OK" } else { "❌ Fail"; $allPassed = $false }
    $testStatus = if ($BuildOnly) { "⏭️ Skip" } elseif ($r.Test) { "✅ OK" } else { "❌ Fail"; $allPassed = $false }

    Write-Host "$($r.App):" -ForegroundColor White -NoNewline
    Write-Host " Build=$buildStatus" -NoNewline
    Write-Host " Test=$testStatus"
}

Write-Host ""
Write-Host "Duration: $($duration.ToString('mm\:ss'))" -ForegroundColor Gray
Write-Host ""

if ($allPassed) {
    Write-Host "🎉 All tasks completed successfully!" -ForegroundColor Green
    exit 0
}
else {
    Write-Host "⚠️ Some tasks failed. Check logs above." -ForegroundColor Yellow
    exit 1
}
