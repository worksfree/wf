# ================================================================
#  restart_server.ps1 — dwg_extract_server.py 재시작
#  위치: D:\drive_files\10.worksfree\10.rpa\70.webs\synology-web\workers\dwg-extract-pc\
#
#  dwg_extract.py를 수정한 뒤 이미 떠 있는 서버는 옛날 코드를 메모리에
#  올려둔 채로 계속 돌기 때문에, 코드를 바꿀 때마다 재시작이 필요하다.
#  이 스크립트는 포트 8767을 쓰는 기존 프로세스를 종료하고 새 창에서
#  다시 띄운다.
#
#  사용법: restart_server.ps1 더블클릭 (또는 PowerShell에서 .\restart_server.ps1)
# ================================================================
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
chcp 65001 | Out-Null

$PORT       = 8767
$ScriptPath = Join-Path $PSScriptRoot "dwg_extract_server.py"

Write-Host ""
Write-Host "  ▶ 포트 $PORT 사용 중인 기존 프로세스 확인 중..." -ForegroundColor Yellow

$conn = Get-NetTCPConnection -LocalPort $PORT -State Listen -ErrorAction SilentlyContinue
if ($conn) {
    foreach ($c in $conn) {
        try {
            Stop-Process -Id $c.OwningProcess -Force -ErrorAction Stop
            Write-Host "    기존 프로세스 종료: PID $($c.OwningProcess)" -ForegroundColor Gray
        } catch {
            Write-Host "    ⚠️  PID $($c.OwningProcess) 종료 실패 — 관리자 권한이 필요할 수 있습니다: $_" -ForegroundColor Red
        }
    }
    Start-Sleep -Milliseconds 500
} else {
    Write-Host "    실행 중인 서버 없음 — 새로 시작합니다." -ForegroundColor Gray
}

Write-Host "  ▶ dwg_extract_server.py 새 창에서 시작 중..." -ForegroundColor Yellow
Start-Process -FilePath "python" -ArgumentList "`"$ScriptPath`"" -WorkingDirectory $PSScriptRoot

Start-Sleep -Seconds 2
try {
    $health = Invoke-RestMethod -Uri "http://localhost:$PORT/health" -TimeoutSec 5
    if ($health.ok) {
        Write-Host ""
        Write-Host "  ✅ 재시작 완료 — http://localhost:$PORT ($($health.engine))" -ForegroundColor Green
    }
} catch {
    Write-Host ""
    Write-Host "  ⚠️  health 체크 실패 — 새로 열린 창에서 에러 메시지를 확인하세요." -ForegroundColor Red
}
Write-Host ""
Read-Host "  Enter 키로 이 창 닫기"
