# ============================================================
# 빌드 전 환경 검증 스크립트
# ============================================================

Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host "빌드 환경 검증 시작" -ForegroundColor Cyan
Write-Host "============================================================`n" -ForegroundColor Cyan

$issues = @()

# 1. 실행 중인 앱 프로세스 확인
Write-Host "1. 실행 중인 앱 프로세스 확인..." -ForegroundColor Yellow
$runningApps = Get-Process | Where-Object { 
    $_.Name -like "*bom2excel*" -or 
    $_.Name -like "*dwg_classifier*" -or 
    $_.Name -like "*conversion_verifier*" -or 
    $_.Name -like "*korean_filename_normalizer*" 
}

if ($runningApps) {
    Write-Host "   ⚠ 실행 중인 앱 발견:" -ForegroundColor Yellow
    $runningApps | ForEach-Object {
        Write-Host "     - $($_.Name) (PID: $($_.Id))" -ForegroundColor Yellow
    }
    $issues += "실행 중인 앱 프로세스"
    
    # 자동 종료 옵션
    $response = Read-Host "`n   종료하시겠습니까? (Y/N)"
    if ($response -eq 'Y' -or $response -eq 'y') {
        $runningApps | Stop-Process -Force
        Write-Host "   ✓ 프로세스 종료 완료" -ForegroundColor Green
    }
} else {
    Write-Host "   ✓ 실행 중인 앱 없음" -ForegroundColor Green
}

# 2. dist/build 폴더 확인
Write-Host "`n2. 기존 빌드 폴더 확인..." -ForegroundColor Yellow
$buildDirs = @(
    "D:\drive_files\10.worksfree\10.rpa\30.apps\bom_exporter\dist",
    "D:\drive_files\10.worksfree\10.rpa\30.apps\bom_exporter\build",
    "D:\drive_files\10.worksfree\10.rpa\50.data\Dwg_Classifier\dist",
    "D:\drive_files\10.worksfree\10.rpa\50.data\Dwg_Classifier\build",
    "D:\drive_files\10.worksfree\10.rpa\50.data\Conversion_Verifier\dist",
    "D:\drive_files\10.worksfree\10.rpa\50.data\Conversion_Verifier\build",
    "D:\drive_files\10.worksfree\10.rpa\50.data\Korean_Filename_Normalizer\dist",
    "D:\drive_files\10.worksfree\10.rpa\50.data\Korean_Filename_Normalizer\build"
)

$existingDirs = $buildDirs | Where-Object { Test-Path $_ }
if ($existingDirs) {
    Write-Host "   ⚠ 기존 빌드 폴더 발견:" -ForegroundColor Yellow
    $existingDirs | ForEach-Object {
        Write-Host "     - $_" -ForegroundColor Yellow
    }
    $issues += "기존 빌드 폴더"
    Write-Host "   (빌드 스크립트가 자동으로 정리합니다)" -ForegroundColor Cyan
} else {
    Write-Host "   ✓ 빌드 폴더 깨끗함" -ForegroundColor Green
}

# 3. Python 환경 확인
Write-Host "`n3. Python 환경 확인..." -ForegroundColor Yellow
try {
    $pythonVersion = & C:/Python313/python.exe --version 2>&1
    Write-Host "   ✓ Python: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "   ✗ Python을 찾을 수 없습니다" -ForegroundColor Red
    $issues += "Python 환경"
}

# 4. PyInstaller 확인
Write-Host "`n4. PyInstaller 확인..." -ForegroundColor Yellow
try {
    $pyinstallerVersion = & C:/Python313/python.exe -m PyInstaller --version 2>&1
    Write-Host "   ✓ PyInstaller: $pyinstallerVersion" -ForegroundColor Green
} catch {
    Write-Host "   ✗ PyInstaller를 찾을 수 없습니다" -ForegroundColor Red
    $issues += "PyInstaller"
}

# 5. 디스크 공간 확인
Write-Host "`n5. 디스크 공간 확인..." -ForegroundColor Yellow
$drive = Get-PSDrive D
$freeGB = [math]::Round($drive.Free / 1GB, 2)
if ($freeGB -lt 5) {
    Write-Host "   ⚠ 여유 공간: $freeGB GB (5GB 미만)" -ForegroundColor Yellow
    $issues += "디스크 공간 부족"
} else {
    Write-Host "   ✓ 여유 공간: $freeGB GB" -ForegroundColor Green
}

# 6. 릴리즈 폴더 확인
Write-Host "`n6. 릴리즈 폴더 확인..." -ForegroundColor Yellow
if (Test-Path "D:\release\candidates") {
    $candidateCount = (Get-ChildItem "D:\release\candidates" -Directory).Count
    Write-Host "   ✓ 기존 빌드: $candidateCount 개" -ForegroundColor Green
} else {
    Write-Host "   ⚠ 릴리즈 폴더가 없습니다 (자동 생성됨)" -ForegroundColor Yellow
}

# 결과 요약
Write-Host "`n============================================================" -ForegroundColor Cyan
if ($issues.Count -eq 0) {
    Write-Host "✓ 빌드 환경 검증 완료 - 문제 없음" -ForegroundColor Green
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host "`n빌드를 시작할 수 있습니다!" -ForegroundColor Green
    exit 0
} else {
    Write-Host "⚠ 빌드 환경 검증 완료 - 주의사항 $($issues.Count)개" -ForegroundColor Yellow
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host "`n주의사항:" -ForegroundColor Yellow
    $issues | ForEach-Object {
        Write-Host "  - $_" -ForegroundColor Yellow
    }
    Write-Host "`n대부분의 문제는 빌드 스크립트가 자동으로 처리합니다." -ForegroundColor Cyan
    Write-Host "빌드를 계속 진행하세요." -ForegroundColor Cyan
    exit 0
}
