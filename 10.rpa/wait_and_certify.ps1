# ============================================================================
# wait_and_certify.ps1
# ============================================================================
# 현재 실행 중인 빌드 완료를 대기한 후 자동으로 인증 실행
# ============================================================================

Write-Host "`n╔═══════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  빌드 완료 대기 & 자동 인증                                    ║" -ForegroundColor Cyan
Write-Host "╚═══════════════════════════════════════════════════════════════╝`n" -ForegroundColor Cyan

# 빌드 프로세스 대기
Write-Host "[1/3] 빌드 완료 대기 중..." -ForegroundColor Yellow
$maxWait = 15  # 최대 15분
$startTime = Get-Date

while (((Get-Date) - $startTime).TotalMinutes -lt $maxWait) {
    $buildProcesses = Get-Process -Name "pwsh","python" -ErrorAction SilentlyContinue | 
                      Where-Object { $_.MainWindowTitle -like "*build*" -or $_.CommandLine -like "*build*" }
    
    if ($buildProcesses.Count -eq 0) {
        Write-Host "  ✓ 빌드 프로세스 종료 확인" -ForegroundColor Green
        Start-Sleep -Seconds 10  # 파일 정리 대기
        break
    }
    
    $elapsed = [math]::Round(((Get-Date) - $startTime).TotalMinutes, 1)
    Write-Host "  ⏳ 대기 중... ($elapsed / $maxWait 분)" -ForegroundColor Gray
    Start-Sleep -Seconds 30
}

# candidates 복사
Write-Host "`n[2/3] 최신 빌드 복사..." -ForegroundColor Yellow

$candidatesDir = "D:\release\candidates"
if (Test-Path $candidatesDir) {
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    Rename-Item $candidatesDir "D:\release\candidates_old_$timestamp" -Force
}
New-Item -Path $candidatesDir -ItemType Directory -Force | Out-Null

$apps = @('bom_exporter', 'dwg_batch_print', 'attribute_reset', 'dwg_classifier', 
          'conversion_verifier', 'korean_filename_normalizer', 'qrcode_generator')
$copied = 0

foreach ($app in $apps) {
    $latest = Get-ChildItem "D:\release" -Directory -Filter "${app}_v*" -ErrorAction SilentlyContinue |
              Where-Object { $_.Name -notlike "*old*" -and $_.Name -notlike "*backup*" } |
              Sort-Object LastWriteTime -Descending | Select-Object -First 1
    
    if ($latest) {
        Copy-Item $latest.FullName -Destination $candidatesDir -Recurse -Force
        Write-Host "  ✓ $($latest.Name)" -ForegroundColor Green
        $copied++
    }
}

Write-Host "  📦 $copied / 7 앱 준비 완료`n" -ForegroundColor Cyan

# WF-ACT 인증 실행
Write-Host "[3/3] WF-ACT 인증 실행..." -ForegroundColor Yellow

cd D:\drive_files\10.worksfree\10.rpa\90.tests\ui_lifecycle_test

python run_certification.py --app be dp ar dc cv kfn qr -l full

Write-Host "`n✓ 완료!" -ForegroundColor Green
Write-Host "리포트 위치: test_results\certification_*\index.html" -ForegroundColor Cyan
