<#
.SYNOPSIS
WorksFree RPA 번들 구조 검증 스크립트

.DESCRIPTION
D:\release\candidates 폴더의 배포 번들을 검증합니다.
- RELEASE 크리덴셜 (worksfree-*.json)
- DEV 크리덴셜 (silver-argon-*.json)
- policy.json 및 settings.json
- 숨김 파일 속성 확인

.EXAMPLE
.\verify_bundle_structure.ps1
#>

param(
    [switch]$Verbose
)

$ErrorActionPreference = "Stop"

# 앱 정보 (버전은 자동 감지)
$apps = @(
    @{App='attribute_reset'; Short='AR'},
    @{App='bom_exporter'; Short='BE'},
    @{App='conversion_verifier'; Short='CV'},
    @{App='dwg_batch_print'; Short='DBP'},
    @{App='dwg_classifier'; Short='DC'},
    @{App='korean_filename_normalizer'; Short='KFN'},
    @{App='qrcode_generator'; Short='QR'}
)

$basePath = "D:\release\candidates"

Write-Host "`n=== 📦 WorksFree RPA 번들 구조 검증 ===" -ForegroundColor Cyan
Write-Host "검증 대상: $basePath`n" -ForegroundColor Gray

# 통계 변수
$totalApps = $apps.Count
$passedApps = 0
$issues = @()

foreach ($item in $apps) {
    $appName = $item.App
    $short = $item.Short
    
    # 최신 버전 폴더 찾기
    $latestFolder = Get-ChildItem "$basePath" -Directory | 
        Where-Object { $_.Name -match "^${appName}_v[\d\.]+$" } | 
        Sort-Object LastWriteTime -Descending | 
        Select-Object -First 1
    
    if (-not $latestFolder) {
        Write-Host "  ❌ 앱 폴더를 찾을 수 없음" -ForegroundColor Red
        $issues += "${appName}: 앱 폴더 없음"
        Write-Host ""
        continue
    }
    
    $bundlePath = Join-Path $latestFolder.FullName "${appName}_v*_portable\_internal\.wf_rpa"
    $bundlePath = Get-Item $bundlePath -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty FullName
    
    if (-not $bundlePath) {
        # portable 폴더 찾기
        $portableFolder = Get-ChildItem $latestFolder.FullName -Directory -Filter "*_portable" | Select-Object -First 1
        if ($portableFolder) {
            $bundlePath = Join-Path $portableFolder.FullName "_internal\.wf_rpa"
        }
    }
    
    Write-Host "[$short] $appName" -ForegroundColor Yellow
    
    if (-not (Test-Path $bundlePath)) {
        Write-Host "  ❌ 번들 폴더 없음: $bundlePath" -ForegroundColor Red
        $issues += "${appName}: 번들 폴더 없음"
        continue
    }
    
    $appPassed = $true
    $appIssues = @()
    
    # 1. RELEASE 크리덴셜 확인
    $releaseFile = Get-ChildItem $bundlePath -Filter "worksfree-*.json" -Force -ErrorAction SilentlyContinue
    if ($releaseFile) {
        $isHidden = $releaseFile.Attributes -match 'Hidden'
        if ($isHidden) {
            Write-Host "  ✅ RELEASE 크리덴셜: $($releaseFile.Name) (숨김)" -ForegroundColor Green
        } else {
            Write-Host "  ⚠️ RELEASE 크리덴셜: $($releaseFile.Name) (숨김 없음)" -ForegroundColor Yellow
            $appIssues += "RELEASE 크리덴셜 숨김 속성 없음"
        }
    } else {
        Write-Host "  ❌ RELEASE 크리덴셜 없음" -ForegroundColor Red
        $appPassed = $false
        $appIssues += "RELEASE 크리덴셜 없음"
    }
    
    # 2. DEV 크리덴셜 확인
    $devFile = Get-ChildItem $bundlePath -Filter "silver-argon-*.json" -Force -ErrorAction SilentlyContinue
    if ($devFile) {
        $isHidden = $devFile.Attributes -match 'Hidden'
        if ($isHidden) {
            Write-Host "  ✅ DEV 크리덴셜: $($devFile.Name) (숨김)" -ForegroundColor Green
        } else {
            Write-Host "  ⚠️ DEV 크리덴셜: $($devFile.Name) (숨김 없음)" -ForegroundColor Yellow
            $appIssues += "DEV 크리덴셜 숨김 속성 없음"
        }
    } else {
        Write-Host "  ❌ DEV 크리덴셜 없음" -ForegroundColor Red
        $appPassed = $false
        $appIssues += "DEV 크리덴셜 없음"
    }
    
    # 3. wf_rpa_config.json 확인
    $configFile = Join-Path $bundlePath "wf_rpa_config.json"
    if (Test-Path $configFile) {
        $file = Get-Item $configFile -Force
        $isHidden = $file.Attributes -match 'Hidden'
        if ($isHidden) {
            Write-Host "  ✅ wf_rpa_config.json (숨김)" -ForegroundColor Green
        } else {
            Write-Host "  ⚠️ wf_rpa_config.json (숨김 없음)" -ForegroundColor Yellow
            $appIssues += "wf_rpa_config.json 숨김 속성 없음"
        }
    } else {
        Write-Host "  ❌ wf_rpa_config.json 없음" -ForegroundColor Red
        $appPassed = $false
        $appIssues += "wf_rpa_config.json 없음"
    }
    
    # 4. policy.json 확인
    $policyPath = Join-Path $bundlePath "$appName\policy.json"
    if (Test-Path $policyPath) {
        $file = Get-Item $policyPath -Force
        $isHidden = $file.Attributes -match 'Hidden'
        if ($isHidden) {
            Write-Host "  ✅ policy.json (숨김)" -ForegroundColor Green
        } else {
            Write-Host "  ⚠️ policy.json (숨김 없음)" -ForegroundColor Yellow
            $appIssues += "policy.json 숨김 속성 없음"
        }
    } else {
        Write-Host "  ❌ policy.json 없음" -ForegroundColor Red
        $appPassed = $false
        $appIssues += "policy.json 없음"
    }
    
    # 5. settings.json 확인
    $settingsPath = Join-Path $bundlePath "$appName\settings.json"
    if (Test-Path $settingsPath) {
        $file = Get-Item $settingsPath -Force
        $isHidden = $file.Attributes -match 'Hidden'
        if ($isHidden) {
            Write-Host "  ✅ settings.json (숨김)" -ForegroundColor Green
        } else {
            Write-Host "  ⚠️ settings.json (숨김 없음)" -ForegroundColor Yellow
            $appIssues += "settings.json 숨김 속성 없음"
        }
    } else {
        Write-Host "  ❌ settings.json 없음" -ForegroundColor Red
        $appPassed = $false
        $appIssues += "settings.json 없음"
    }
    
    if ($appPassed) {
        $passedApps++
    }
    
    if ($appIssues.Count -gt 0) {
        $issues += "${appName}: " + ($appIssues -join ', ')
    }
    
    Write-Host ""
}

# 최종 요약
Write-Host "`n=== 📊 검증 결과 요약 ===" -ForegroundColor Cyan
Write-Host "전체 앱: $totalApps" -ForegroundColor Gray
Write-Host "통과: $passedApps" -ForegroundColor Green
Write-Host "문제: $($totalApps - $passedApps)" -ForegroundColor $(if ($passedApps -eq $totalApps) { "Green" } else { "Red" })

if ($issues.Count -gt 0) {
    Write-Host "`n⚠️ 발견된 문제:" -ForegroundColor Yellow
    foreach ($issue in $issues) {
        Write-Host "  - $issue" -ForegroundColor Gray
    }
    
    Write-Host "`n💡 조치 방법:" -ForegroundColor Cyan
    Write-Host "  1. 전체 재빌드: .\build_all_parallel.ps1 -BuildType 2" -ForegroundColor White
    Write-Host "  2. 특정 앱만: .\build_all_parallel.ps1 -BuildType 2 -Apps be,cv,kfn" -ForegroundColor White
} else {
    Write-Host "`n✅ 모든 앱의 번들 구조가 정상입니다!" -ForegroundColor Green
}

# Exit code
if ($passedApps -eq $totalApps -and $issues.Count -eq 0) {
    exit 0
} else {
    exit 1
}
