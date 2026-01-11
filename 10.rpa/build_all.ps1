# build_all.ps1 - sequential build helper (Windows)
<#
.SYNOPSIS
    5개 RPA 앱 순차 빌드 스크립트

.DESCRIPTION
    BOM2Excel, DWG Batch Print, DWG Classifier, Conversion Verifier, Korean Filename Normalizer를 순차적으로 빌드합니다.
    stdin 리다이렉션으로 "Aborted by user request" 문제 해결

.PARAMETER Mode
    빌드 모드:
    - Mode 1: onedir만 (1개 아웃풋)
    - Mode 2: onedir + zip (2개 아웃풋)
    - Mode 3: onedir + zip + installer (3개 아웃풋)
    - Mode 4: zip만 (1개 아웃풋)
    - Mode 5: installer만 (1개 아웃풋)

.EXAMPLE
    .\build_all.ps1 -Mode 3
    # 5개 앱을 순차적으로 onedir + ZIP + installer로 빌드
    
.EXAMPLE
    .\build_all.ps1 -Mode 2
    # 5개 앱을 순차적으로 onedir + ZIP로 빌드
#>

param(
    [int]$Mode = 2,
    [switch]$PostClean
)

$ErrorActionPreference = 'Stop'

# 앱 정보
$Apps = @(
    @{
        Name = 'Bom Exporter'
        Dir = 'D:\drive_files\10.worksfree\10.rpa\30.apps\bom_exporter'
        Script = 'D:\drive_files\10.worksfree\10.rpa\30.apps\bom_exporter\build_bom_exporter.ps1'
    },
    @{
        Name = 'DWG Batch Print'
        Dir = 'D:\drive_files\10.worksfree\10.rpa\30.apps\dwg_batch_print'
        Script = 'D:\drive_files\10.worksfree\10.rpa\30.apps\dwg_batch_print\build_dwg_batch_print.ps1'
    },
    @{
        Name = 'DWG Classifier'
        Dir = 'D:\drive_files\10.worksfree\10.rpa\50.data\dwg_classifier'
        Script = 'D:\drive_files\10.worksfree\10.rpa\50.data\dwg_classifier\build_dwg_classifier.ps1'
    },
    @{
        Name = 'Conversion Verifier'
        Dir = 'D:\drive_files\10.worksfree\10.rpa\50.data\conversion_verifier'
        Script = 'D:\drive_files\10.worksfree\10.rpa\50.data\conversion_verifier\build_conversion_verifier.ps1'
    },
    @{
        Name = 'Korean Filename Normalizer'
        Dir = 'D:\drive_files\10.worksfree\10.rpa\50.data\korean_filename_normalizer'
        Script = 'D:\drive_files\10.worksfree\10.rpa\50.data\korean_filename_normalizer\build_korean_filename_normalizer.ps1'
    }
)

$Results = @()
$StartTime = Get-Date

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "5개 RPA 앱 순차 빌드 (Mode $Mode)" -ForegroundColor Cyan
Write-Host "시작 시간: $($StartTime.ToString('yyyy-MM-dd HH:mm:ss'))" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

foreach ($App in $Apps) {
    $AppStartTime = Get-Date
    Write-Host "----------------------------------------" -ForegroundColor Yellow
    Write-Host "[$($App.Name)] 빌드 시작..." -ForegroundColor Yellow
    Write-Host "----------------------------------------" -ForegroundColor Yellow
    
    try {
        # 경로 검증
        if (!(Test-Path $App.Script)) {
            throw "빌드 스크립트를 찾을 수 없습니다: $($App.Script)"
        }
        
        # 빌드 실행 (stdin을 $null로 리다이렉트하여 PyInstaller "Aborted by user request" 문제 방지)
        $null | & $App.Script -Mode $Mode
        
        if ($LASTEXITCODE -eq 0) {
            $Duration = (Get-Date) - $AppStartTime
            Write-Host "`n✓ [$($App.Name)] 빌드 성공 (소요시간: $($Duration.TotalMinutes.ToString('0.0'))분)" -ForegroundColor Green
            $Results += @{
                App = $App.Name
                Status = '성공'
                Duration = $Duration.TotalMinutes
            }
        } else {
            throw "빌드 스크립트가 종료 코드 $LASTEXITCODE 를 반환했습니다"
        }
    }
    catch {
        $Duration = (Get-Date) - $AppStartTime
        Write-Host "`n✗ [$($App.Name)] 빌드 실패: $($_.Exception.Message)" -ForegroundColor Red
        $Results += @{
            App = $App.Name
            Status = '실패'
            Duration = $Duration.TotalMinutes
            Error = $_.Exception.Message
        }
    }
    
    Write-Host ""
}

# 최종 결과 요약
$EndTime = Get-Date
$TotalDuration = $EndTime - $StartTime

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "빌드 완료 - 최종 결과" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "종료 시간: $($EndTime.ToString('yyyy-MM-dd HH:mm:ss'))" -ForegroundColor Gray
Write-Host "총 소요시간: $($TotalDuration.TotalMinutes.ToString('0.0'))분`n" -ForegroundColor Gray

$SuccessCount = @($Results | Where-Object { $_.Status -eq '성공' }).Count
$FailCount = @($Results | Where-Object { $_.Status -eq '실패' }).Count

foreach ($Result in $Results) {
    $StatusColor = if ($Result.Status -eq '성공') { 'Green' } else { 'Red' }
    $StatusIcon = if ($Result.Status -eq '성공') { '✓' } else { '✗' }
    
    Write-Host "$StatusIcon $($Result.App): $($Result.Status) ($($Result.Duration.ToString('0.0'))분)" -ForegroundColor $StatusColor
    if ($Result.Error) {
        Write-Host "  오류: $($Result.Error)" -ForegroundColor Red
    }
}

Write-Host "`n성공: $SuccessCount / 실패: $FailCount / 전체: $($Results.Count)" -ForegroundColor Cyan

# 생성된 패키지 목록
Write-Host "`n생성된 패키지:" -ForegroundColor Cyan
$RecentPackages = Get-ChildItem "D:\release\candidates\*_portable.zip" -Recurse -ErrorAction SilentlyContinue | 
    Where-Object { $_.LastWriteTime -gt $StartTime } | 
    Sort-Object LastWriteTime

if ($RecentPackages.Count -gt 0) {
    $RecentPackages | ForEach-Object {
        $SizeMB = [math]::Round($_.Length / 1MB, 1)
        Write-Host "  • $($_.Name) ($SizeMB MB)" -ForegroundColor Green
    }
} else {
    Write-Host "  (패키지가 생성되지 않았습니다)" -ForegroundColor Yellow
}

Write-Host "`n========================================`n" -ForegroundColor Cyan

exit $(if ($FailCount -eq 0) { 0 } else { 1 })

# Optional post-build cleanup
if ($PostClean.IsPresent -and $FailCount -eq 0) {
    Write-Host "\n빌드 아티팩트 정리 실행(PostClean)" -ForegroundColor Cyan
    $cleanup = Join-Path $PSScriptRoot 'cleanup_build_artifacts.ps1'
    if (Test-Path $cleanup) {
        & $cleanup
        Write-Host "정리 완료" -ForegroundColor Green
    } else {
        Write-Host "정리 스크립트를 찾을 수 없습니다: $cleanup" -ForegroundColor Yellow
    }
}
