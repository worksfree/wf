#!/usr/bin/env pwsh
<#
.SYNOPSIS
    각 RPA 앱의 메인 UI를 자동으로 실행하고 스크린샷을 캡처

.DESCRIPTION
    5개 앱을 순차적으로 실행하여 메인 창을 띄우고 스크린샷을 찍습니다.
#>

param(
    [switch]$NoWait
)

$ErrorActionPreference = 'SilentlyContinue'
$ScreenshotDir = "D:\drive_files\10.worksfree\ui_screenshots_$(Get-Date -Format 'yyyyMMdd_HHmmss')"

# 스크린샷 디렉토리 생성
New-Item -ItemType Directory -Path $ScreenshotDir -Force | Out-Null
Write-Host "`n📸 스크린샷 저장 위치: $ScreenshotDir`n" -ForegroundColor Cyan

# 각 앱 정보
$apps = @(
    @{name="Bom Exporter"; exe="d:/drive_files/10.worksfree/10.rpa/30.apps/bom_exporter/dist/bom_exporter/bom_exporter.exe"},
    @{name="Batch Print"; exe="d:/drive_files/10.worksfree/10.rpa/30.apps/batch_print/dist/batch_print/batch_print.exe"},
    @{name="DWG Classifier"; exe="d:/drive_files/10.worksfree/10.rpa/50.data/dwg_classifier/dist/dwg_classifier/dwg_classifier.exe"},
    @{name="Conversion Verifier"; exe="d:/drive_files/10.worksfree/10.rpa/50.data/conversion_verifier/dist/conversion_verifier/conversion_verifier.exe"},
    @{name="Korean Filename Normalizer"; exe="d:/drive_files/10.worksfree/10.rpa/50.data/korean_filename_normalizer/dist/korean_filename_normalizer/korean_filename_normalizer.exe"}
)

# PowerShell에서 스크린샷 캡처 함수
Add-Type -AssemblyName System.Windows.Forms
[System.Windows.Forms.Screen]::AllScreens | Out-Null

function Capture-Screenshot {
    param([string]$OutputPath)
    try {
        $screen = [System.Windows.Forms.Screen]::PrimaryScreen
        $bitmap = New-Object System.Drawing.Bitmap($screen.Bounds.Width, $screen.Bounds.Height)
        $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
        $graphics.CopyFromScreen($screen.Bounds.Location, [System.Drawing.Point]::Empty, $screen.Bounds.Size)
        $graphics.Dispose()
        $bitmap.Save($OutputPath, [System.Drawing.Imaging.ImageFormat]::Png)
        $bitmap.Dispose()
        return $true
    } catch {
        Write-Host "스크린샷 저장 실패: $_" -ForegroundColor Red
        return $false
    }
}

Write-Host "=== RPA 앱 UI 자동 캡처 시작 ===" -ForegroundColor Cyan
Write-Host "각 앱이 2초 후 종료됩니다`n" -ForegroundColor Yellow

foreach ($app in $apps) {
    Write-Host "🚀 실행 중: $($app.name)" -ForegroundColor Green
    
    if (-not (Test-Path $app.exe)) {
        Write-Host "  ✗ EXE 파일 없음: $($app.exe)" -ForegroundColor Red
        continue
    }
    
    try {
        # 앱 실행
        $process = Start-Process -FilePath $app.exe -PassThru -WindowStyle Normal
        
        # UI가 뜰 때까지 대기 (1.5초)
        Start-Sleep -Milliseconds 1500
        
        # 스크린샷 캡처
        $screenshot = Join-Path $ScreenshotDir "$($app.name)_$(Get-Date -Format 'HHmmss').png"
        if (Capture-Screenshot -OutputPath $screenshot) {
            Write-Host "  ✓ 스크린샷 저장: $(Split-Path $screenshot -Leaf)" -ForegroundColor Green
        }
        
        # 앱 종료
        if ($process -and -not $process.HasExited) {
            $process | Stop-Process -Force -ErrorAction SilentlyContinue
            Start-Sleep -Milliseconds 500
        }
        
    } catch {
        Write-Host "  ✗ 오류: $_" -ForegroundColor Red
    }
}

Write-Host "`n=== 캡처 완료 ===" -ForegroundColor Cyan
Write-Host "저장 경로: $ScreenshotDir`n" -ForegroundColor Green

# 저장된 스크린샷 목록
$screenshots = Get-ChildItem $ScreenshotDir -Filter "*.png" -ErrorAction SilentlyContinue
if ($screenshots) {
    Write-Host "📋 캡처된 파일 목록:" -ForegroundColor Cyan
    $screenshots | ForEach-Object {
        Write-Host "  • $($_.Name) ($('{0:N0}' -f ($_.Length / 1KB)) KB)" -ForegroundColor Gray
    }
    Write-Host "`n✅ 스크린샷 캡처 완료! ($($screenshots.Count)개)`n" -ForegroundColor Green
} else {
    Write-Host "⚠️  캡처된 파일이 없습니다`n" -ForegroundColor Yellow
}
