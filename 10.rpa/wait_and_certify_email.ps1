# wait_and_certify_email.ps1
# 빌드 완료 대기 -> EXE 인증 -> 이메일

param([string]$EmailTo = "insung.lee@worksfree.co.kr")

$StartTime = Get-Date
Write-Host "`n==== 빌드 완료 대기 및 인증 ====" -ForegroundColor Cyan

# 빌드 프로세스 대기 (최대 20분)
$waited = 0
while ($waited -lt 20) {
    $buildProcs = Get-Process | Where-Object { $_.ProcessName -like "*pwsh*" -or $_.ProcessName -like "*python*" }
    if ($buildProcs.Count -le 2) {
        Write-Host "빌드 프로세스 종료 감지" -ForegroundColor Green
        Start-Sleep -Seconds 10
        break
    }
    Start-Sleep -Seconds 30
    $waited += 0.5
    Write-Host "  대기 중... $waited / 20분" -ForegroundColor Gray
}

# EXE 인증
Write-Host "`nEXE 인증 시작..." -ForegroundColor Yellow
Set-Location "D:\drive_files\10.worksfree\10.rpa\90.tests\ui_lifecycle_test"

$ts = Get-Date -Format "yyyyMMdd_HHmmss"
$outDir = "test_results\certification_${ts}_exe_auto"

python run_certification.py --exe -o $outDir
$certOK = $LASTEXITCODE -eq 0

$reportPath = Join-Path (Get-Location) "$outDir\index.html"
$EndTime = Get-Date
$Duration = $EndTime - $StartTime

# 리포트 요약
$summary = "리포트 확인"
if (Test-Path $reportPath) {
    try {
        $html = Get-Content $reportPath -Raw -Encoding UTF8
        if ($html -match '통과:\s*(\d+).*스킵:\s*(\d+).*실패:\s*(\d+)') {
            $summary = "통과:$($matches[1]) 스킵:$($matches[2]) 실패:$($matches[3])"
        }
    } catch {}
}

# 이메일 발송
Write-Host "`n이메일 발송..." -ForegroundColor Yellow

$body = "WorksFree RPA 인증 완료`n`n" +
        "시작: $($StartTime.ToString('yyyy-MM-dd HH:mm:ss'))`n" +
        "종료: $($EndTime.ToString('yyyy-MM-dd HH:mm:ss'))`n" +
        "소요: $([math]::Round($Duration.TotalMinutes, 1))분`n`n" +
        "인증: $(if($certOK){'통과'}else{'실패'})`n" +
        "결과: $summary`n`n" +
        "리포트: $reportPath"

$subject = if($certOK) { '[WF-RPA] 인증 완료' } else { '[WF-RPA] 인증 완료(일부실패)' }

$tf = Join-Path $env:TEMP "email.py"
"import sys
sys.path.insert(0, r'D:\drive_files\10.worksfree\10.rpa\10.common')
from wf_email import send_email
send_email(subject='$subject', body='''$body''', to_email='$EmailTo')
print('Email sent to $EmailTo')" | Out-File -FilePath $tf -Encoding UTF8

python $tf
Remove-Item $tf -Force -ErrorAction SilentlyContinue

Write-Host "`n==== 완료 ====" -ForegroundColor Cyan
Write-Host "  Report: $reportPath" -ForegroundColor Gray
