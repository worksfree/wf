# ================================================================
#  register_dwg_extract_task.ps1
#  dwg_extract_server.py를 콘솔 창 없이 백그라운드로 띄우고, PC 재부팅/
#  로그온 후에도 자동으로 켜지게 Windows 작업 스케줄러에 등록한다.
#  (site-rag/register_host_rewrite_task.ps1과 동일 패턴 — pc-host-rewrite-proxy
#  프록시도 같은 방식으로 콘솔 창 없이 돌고 있음)
#
#  ⚠ 반드시 "관리자 권한으로 실행"한 PowerShell에서 돌려야 한다.
#     (일반 PowerShell에서 실행하면 "Access is denied" 오류가 난다)
#
#  사용법:
#    1. 시작 메뉴에서 PowerShell 검색 → 마우스 오른쪽 클릭 → "관리자 권한으로 실행"
#    2. cd D:\drive_files\10.worksfree\10.rpa\70.webs\synology-web\workers\dwg-extract-pc
#    3. .\register_dwg_extract_task.ps1
#
#  등록 후에는 restart_server.ps1(콘솔 창 띄우는 방식) 대신 아래로 재시작한다:
#    Stop-ScheduledTask -TaskName "WorksFree-DWG-Extract-Server" 은 프로세스를 안 죽이므로,
#    포트 8767 프로세스를 taskkill한 뒤 Start-ScheduledTask로 다시 띄워야 한다(코드 수정 후 반영 시).
# ================================================================

$ErrorActionPreference = "Stop"

$TaskName   = "WorksFree-DWG-Extract-Server"
$ScriptPath = Join-Path $PSScriptRoot "dwg_extract_server.py"
$PythonPath = (Get-Command python -ErrorAction Stop).Source
$VbsPath    = Join-Path $PSScriptRoot "dwg_extract_server.vbs"

if (-not (Test-Path $ScriptPath)) {
    Write-Host "[오류] dwg_extract_server.py를 찾을 수 없습니다: $ScriptPath" -ForegroundColor Red
    exit 1
}

# python.exe를 콘솔 창 없이 백그라운드로 띄우기 위한 VBScript 래퍼 생성
# (작업 스케줄러가 python.exe를 직접 실행하면 검은 콘솔 창이 화면에 뜬다 — 이걸 숨긴다)
$vbsContent = @"
Set objShell = CreateObject("WScript.Shell")
objShell.Run """$PythonPath"" ""$ScriptPath""", 0, False
"@
Set-Content -Path $VbsPath -Value $vbsContent -Encoding ASCII

Write-Host "  ▶ 래퍼 스크립트 생성: $VbsPath" -ForegroundColor Cyan

# 기존 동일 이름 작업이 있으면 제거 후 재등록 (재실행 안전)
if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    Write-Host "  ▶ 기존 작업 제거 중..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

$Action  = New-ScheduledTaskAction -Execute "wscript.exe" -Argument "`"$VbsPath`""
# 이 PC에 로그온할 때마다 시작 — dwg-extract.worksfree.kr Tunnel이 이 서버를 상시 가정하고 있음
$Trigger = New-ScheduledTaskTrigger -AtLogOn
$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RestartCount 999 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -ExecutionTimeLimit (New-TimeSpan -Days 0)   # 무제한 실행(상시 서버라 시간 제한 없어야 함)

$Principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger `
    -Settings $Settings -Principal $Principal -Force | Out-Null

Write-Host ""
Write-Host "  ✅ 작업 스케줄러 등록 완료: $TaskName" -ForegroundColor Green
Write-Host "     다음 로그온부터 자동 시작됩니다." -ForegroundColor Green
Write-Host ""
Write-Host "  ▶ 지금 바로 테스트하려면:" -ForegroundColor Cyan
Write-Host "     Start-ScheduledTask -TaskName '$TaskName'"
Write-Host ""
Write-Host "  ▶ 정상 동작 확인 (몇 초 기다린 뒤):" -ForegroundColor Cyan
Write-Host "     curl.exe http://127.0.0.1:8767/health"
Write-Host "     ({\"ok\": true, ...}가 나오면 성공)"
Write-Host ""
Write-Host "  ▶ 작업 상태 확인: Get-ScheduledTask -TaskName '$TaskName' | Get-ScheduledTaskInfo"
Write-Host "  ▶ 제거하려면:     Unregister-ScheduledTask -TaskName '$TaskName' -Confirm:`$false"
