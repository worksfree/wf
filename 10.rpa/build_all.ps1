# build_all.ps1 - sequential build helper (Windows)
<#
.SYNOPSIS
    6개 RPA 앱 순차 빌드 스크립트

.DESCRIPTION
    BOM Exporter, Batch Print, Attribute Reset, DWG Classifier, Conversion Verifier, Korean Filename Normalizer를 순차적으로 빌드합니다.
    stdin 리다이렉션으로 "Aborted by user request" 문제 해결

.PARAMETER BuildType
    빌드 출력 형식 (run_mode와 구분하기 위해 BuildType 사용):
    - BuildType 1: onedir만 (1개 아웃풋)
    - BuildType 2: onedir + zip (2개 아웃풋) - 기본값
    - BuildType 3: onedir + zip + installer (3개 아웃풋)
    - BuildType 4: zip만 (1개 아웃풋)
    - BuildType 5: installer만 (1개 아웃풋)

.EXAMPLE
    .\build_all.ps1 -BuildType 3
    # 6개 앱을 순차적으로 onedir + ZIP + installer로 빌드

.EXAMPLE
    .\build_all.ps1 -BuildType 2
    # 6개 앱을 순차적으로 onedir + ZIP로 빌드
#>

param(
    [int]$BuildType = 2,  # 1=onedir, 2=onedir+zip, 3=onedir+zip+installer, 4=zip만, 5=installer만
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
        Name = 'Batch Print'
        Dir = 'D:\drive_files\10.worksfree\10.rpa\30.apps\batch_print'
        Script = 'D:\drive_files\10.worksfree\10.rpa\30.apps\batch_print\build_batch_print.ps1'
    },
    @{
        Name = 'Attribute Reset'
        Dir = 'D:\drive_files\10.worksfree\10.rpa\30.apps\attribute_reset'
        Script = 'D:\drive_files\10.worksfree\10.rpa\30.apps\attribute_reset\build_attribute_reset.ps1'
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
    },
    @{
        Name = 'QRCode Generator'
        Dir = 'D:\drive_files\10.worksfree\10.rpa\50.data\qrcode_generator'
        Script = 'D:\drive_files\10.worksfree\10.rpa\50.data\qrcode_generator\build_qrcode_generator.ps1'
    }
)

$Results = @()
$StartTime = Get-Date

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "7개 RPA 앱 순차 빌드 (BuildType $BuildType)" -ForegroundColor Cyan
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
        
        # 빌드 실행 (stdin을 지속적인 스트림으로 유지하여 PyInstaller "Aborted by user request" 문제 방지)
        # $null은 즉시 EOF를 보내므로 사용하지 않음. 대신 /dev/null 같은 무한 스트림 사용
        & $App.Script -BuildType $BuildType
        $ExitCode = $LASTEXITCODE
        
        if ($ExitCode -eq 0) {
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
