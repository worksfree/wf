# ============================================================================
# auto_build_and_certify.ps1
# ============================================================================
# 빌드 완료 대기 → candidates 복사 → WF-ACT 인증 → 결과 리포트
# ============================================================================

param(
    [int]$BuildType = 2,
    [int]$MaxWaitMinutes = 15
)

$ErrorActionPreference = 'Continue'

Write-Host "`n╔═══════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  자동 빌드 & 인증 프로세스                                     ║" -ForegroundColor Cyan
Write-Host "╚═══════════════════════════════════════════════════════════════╝`n" -ForegroundColor Cyan

# ============================================================================
# Step 1: 빌드 완료 대기
# ============================================================================

Write-Host "[1/4] 빌드 완료 대기 중..." -ForegroundColor Yellow

$startTime = Get-Date
$buildComplete = $false
$candidatesDir = "D:\release\candidates"

# 빌드 프로세스 확인 (pwsh.exe가 build_all_parallel.ps1 실행 중)
while (((Get-Date) - $startTime).TotalMinutes -lt $MaxWaitMinutes) {
    $buildProcesses = Get-Process | Where-Object {
        $_.ProcessName -like "*pwsh*" -or $_.ProcessName -like "*python*"
    }
    
    if ($buildProcesses.Count -eq 0) {
        Write-Host "  빌드 프로세스 종료 확인" -ForegroundColor Green
        Start-Sleep -Seconds 5  # 파일 정리 대기
        $buildComplete = $true
        break
    }
    
    $elapsed = [math]::Round(((Get-Date) - $startTime).TotalMinutes, 1)
    Write-Host "  대기 중... ($elapsed / $MaxWaitMinutes 분)" -ForegroundColor Gray
    Start-Sleep -Seconds 30
}

if (-not $buildComplete) {
    Write-Host "✗ 시간 초과 - 빌드가 완료되지 않았습니다." -ForegroundColor Red
    exit 1
}

# ============================================================================
# Step 2: 최신 빌드 결과를 candidates로 복사
# ============================================================================

Write-Host "`n[2/4] 빌드 결과물 정리..." -ForegroundColor Yellow

# candidates 폴더 초기화
if (Test-Path $candidatesDir) {
    Write-Host "  기존 candidates 폴더 백업 중..." -ForegroundColor Gray
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $backupDir = "D:\release\candidates_backup_$timestamp"
    Rename-Item $candidatesDir $backupDir -Force
}

New-Item -Path $candidatesDir -ItemType Directory -Force | Out-Null

# 7개 앱의 최신 빌드 복사
$apps = @('bom_exporter', 'dwg_batch_print', 'attribute_reset', 'dwg_classifier', 'conversion_verifier', 'korean_filename_normalizer', 'qrcode_generator')
$copiedCount = 0

foreach ($app in $apps) {
    $versionDirs = Get-ChildItem -Path "D:\release" -Directory -Filter "${app}_v*" -ErrorAction SilentlyContinue | 
                   Where-Object { $_.Name -notlike "*backup*" -and $_.Name -notlike "*old*" }
    
    if ($versionDirs) {
        # 최신 버전 찾기 (LastWriteTime 기준)
        $latest = $versionDirs | Sort-Object LastWriteTime -Descending | Select-Object -First 1
        
        Copy-Item $latest.FullName -Destination $candidatesDir -Recurse -Force
        Write-Host "  ✓ $($latest.Name)" -ForegroundColor Green
        $copiedCount++
    } else {
        Write-Host "  ✗ $app - 빌드 결과 없음" -ForegroundColor Yellow
    }
}

if ($copiedCount -eq 0) {
    Write-Host "`n✗ 복사된 앱이 없습니다. 빌드 실패 가능성." -ForegroundColor Red
    exit 1
}

Write-Host "`n  총 $copiedCount 개 앱 준비 완료" -ForegroundColor Cyan

# ============================================================================
# Step 3: verify_exe_package.ps1 실행 (빠른 검증)
# ============================================================================

Write-Host "`n[3/4] 배포 패키지 완전성 검증..." -ForegroundColor Yellow

$verifyScript = "D:\drive_files\10.worksfree\10.rpa\verify_exe_package.ps1"
& $verifyScript -ReleaseDir $candidatesDir

$quickCheckPassed = $LASTEXITCODE -eq 0

# ============================================================================
# Step 4: WF-ACT 인증 (DEV 모드 - 소스 코드)
# ============================================================================

Write-Host "`n[4/4] WF-ACT 인증 실행..." -ForegroundColor Yellow

cd "D:\drive_files\10.worksfree\10.rpa\90.tests\ui_lifecycle_test"

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$outputDir = "test_results\certification_${timestamp}_auto"

Write-Host "  모드: DEV (소스 코드 테스트)" -ForegroundColor Cyan
Write-Host "  레벨: FULL (134개 테스트 × 7개 앱 = 938개)" -ForegroundColor Cyan
Write-Host "  출력: $outputDir`n" -ForegroundColor Cyan

python run_certification.py --app be dp ar dc cv kfn qr -l full -o $outputDir

$certPassed = $LASTEXITCODE -eq 0

# ============================================================================
# 최종 결과 요약
# ============================================================================

Write-Host "`n╔═══════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  최종 결과 요약                                                ║" -ForegroundColor Cyan
Write-Host "╚═══════════════════════════════════════════════════════════════╝`n" -ForegroundColor Cyan

Write-Host "  빌드 완료: " -NoNewline
Write-Host "✓" -ForegroundColor Green

Write-Host "  패키지 복사: " -NoNewline
Write-Host "$copiedCount / 7 앱" -ForegroundColor $(if ($copiedCount -eq 7) { "Green" } else { "Yellow" })

Write-Host "  빠른 검증: " -NoNewline
Write-Host $(if ($quickCheckPassed) { "✓ 통과" } else { "✗ 실패" }) -ForegroundColor $(if ($quickCheckPassed) { "Green" } else { "Red" })

Write-Host "  WF-ACT 인증: " -NoNewline
Write-Host $(if ($certPassed) { "✓ 통과" } else { "✗ 실패" }) -ForegroundColor $(if ($certPassed) { "Green" } else { "Red" })

Write-Host "`n  리포트 위치:" -ForegroundColor Cyan
Write-Host "    $outputDir\index.html`n" -ForegroundColor Gray

if ($certPassed -and $copiedCount -eq 7) {
    Write-Host "✓ 모든 검증 통과 - 배포 준비 완료!" -ForegroundColor Green
    exit 0
} else {
    Write-Host "✗ 일부 검증 실패 - 리포트를 확인하세요." -ForegroundColor Yellow
    exit 1
}
