# 7개 앱을 순차적으로 10초씩 보여주는 스크립트

$python = "C:/Users/USER/AppData/Local/Python/pythoncore-3.14-64/python.exe"
$apps = @(
    @{Name="BOM Exporter"; Path="d:/drive_files/10.worksfree/10.rpa/30.apps/bom_exporter/ui_main.py"},
    @{Name="DWG Batch Print"; Path="d:/drive_files/10.worksfree/10.rpa/30.apps/dwg_batch_print/ui_main.py"},
    @{Name="Attribute Reset"; Path="d:/drive_files/10.worksfree/10.rpa/30.apps/attribute_reset/ui_main.py"},
    @{Name="DWG Classifier"; Path="d:/drive_files/10.worksfree/10.rpa/50.data/dwg_classifier/ui_main.py"},
    @{Name="Conversion Verifier"; Path="d:/drive_files/10.worksfree/10.rpa/50.data/conversion_verifier/ui_main.py"},
    @{Name="Korean Filename Normalizer"; Path="d:/drive_files/10.worksfree/10.rpa/50.data/korean_filename_normalizer/ui_main.py"},
    @{Name="QR Code Generator"; Path="d:/drive_files/10.worksfree/10.rpa/50.data/qrcode_generator/ui_main.py"}
)

foreach ($app in $apps) {
    Write-Host "`n========================================" -ForegroundColor Cyan
    Write-Host "실행 중: $($app.Name)" -ForegroundColor Yellow
    Write-Host "========================================" -ForegroundColor Cyan
    
    # 앱 실행
    $process = Start-Process -FilePath $python -ArgumentList $app.Path -PassThru
    
    # 10초 대기
    Start-Sleep -Seconds 10
    
    # 프로세스 종료
    if (-not $process.HasExited) {
        Stop-Process -Id $process.Id -Force
        Write-Host "종료: $($app.Name)" -ForegroundColor Green
    }
    
    # 다음 앱 전환을 위한 짧은 대기
    Start-Sleep -Seconds 1
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "모든 앱 시연 완료" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
