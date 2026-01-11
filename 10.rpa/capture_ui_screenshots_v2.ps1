# 개선된 UI 스크린샷 캡처 스크립트 v2
# - 앱 실행 확인 후 안정화 대기
# - 개별 캡처

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$timestamp = Get-Date -Format "yyyy-MM-dd_HHmmss"
$screenshotDir = "C:\Temp\RPA_Screenshots"
if (-not (Test-Path $screenshotDir)) {
    New-Item -ItemType Directory -Path $screenshotDir | Out-Null
}

$apps = @(
    @{name='Bom Exporter'; exe='./30.apps/bom_exporter/dist/bom_exporter/bom_exporter.exe'; title='Bom Exporter'},
    @{name='DWG Batch Print'; exe='./30.apps/dwg_batch_print/dist/dwg_batch_print/dwg_batch_print.exe'; title='DWG Batch Print'},
    @{name='DWG Classifier'; exe='./50.data/dwg_classifier/dist/dwg_classifier/dwg_classifier.exe'; title='DWG Classifier'},
    @{name='Conversion Verifier'; exe='./50.data/conversion_verifier/dist/conversion_verifier/conversion_verifier.exe'; title='Conversion Verifier'},
    @{name='Korean Filename Normalizer'; exe='./50.data/korean_filename_normalizer/dist/korean_filename_normalizer/korean_filename_normalizer.exe'; title='Korean Filename Normalizer'}
)

Write-Host "========================================" -ForegroundColor Green
Write-Host "UI 스크린샷 캡처 v2 시작"
Write-Host "저장 위치: $screenshotDir"
Write-Host "========================================`n"

foreach ($app in $apps) {
    Write-Host "[$($app.name)] 시작..." -ForegroundColor Yellow
    
    # 앱 실행
    try {
        $resolved = Resolve-Path $app.exe -ErrorAction Stop
        $distDir = Split-Path $resolved -Parent
        $process = Start-Process -FilePath $resolved -WorkingDirectory $distDir -PassThru -WindowStyle Normal
        
        # 앱 로드 대기 (더 긴 시간)
        Start-Sleep -Seconds 5
        if ($process.HasExited) {
            Write-Host "  ✗ 프로세스가 즉시 종료됨 (ExitCode: $($process.ExitCode))" -ForegroundColor Red
            continue
        }
        
        # 창 활성화 확인
        $window = Get-Process $process.ProcessName | Select-Object -First 1
        if ($window) {
            Write-Host "  ✓ 프로세스 실행됨 (PID: $($process.Id))" -ForegroundColor Green
        }
        
        # 안정화 대기
        Start-Sleep -Seconds 2
        
        # 스크린샷 캡처
        $bitmap = New-Object System.Drawing.Bitmap([System.Windows.Forms.Screen]::PrimaryScreen.Bounds.Width, [System.Windows.Forms.Screen]::PrimaryScreen.Bounds.Height)
        $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
        $graphics.CopyFromScreen([System.Windows.Forms.Screen]::PrimaryScreen.Bounds.Location, [System.Drawing.Point]::Empty, [System.Windows.Forms.Screen]::PrimaryScreen.Bounds.Size)
        
        $filename = "$screenshotDir\${timestamp}_$($app.name -replace ' ', '_').png"
        $bitmap.Save($filename)
        $graphics.Dispose()
        $bitmap.Dispose()
        
        Write-Host "  ✓ 스크린샷 저장: $(Split-Path $filename -Leaf)" -ForegroundColor Green
        
        # 프로세스 종료
        Stop-Process -Id $process.Id -Force
        Start-Sleep -Seconds 1
        
    } catch {
        Write-Host "  ✗ 오류: $_" -ForegroundColor Red
    }
}

Write-Host "`n========================================" -ForegroundColor Green
Write-Host "캡처 완료. 이미지 폴더 열기..."
explorer.exe $screenshotDir
Write-Host "========================================"
