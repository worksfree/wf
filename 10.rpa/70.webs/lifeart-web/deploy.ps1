# ================================================================
#  deploy.ps1 — LifeArt 웹 배포 스크립트 (WorksFree 자체 사이트와 완전 분리된
#  독립 클라이언트 프로젝트. synology-web과 무관)
#
#  사용법:
#    PowerShell: .\deploy.ps1              (대화형)
#    비대화형:   .\deploy.ps1 -Target 1    (1=test-lifeart, 2=production, 9=pre-test-lifeart)
# ================================================================
param([string]$Target = "")

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding          = [System.Text.Encoding]::UTF8
chcp 65001 | Out-Null

# ── ✏️  여기만 수정하면 됩니다 ──────────────────────────────────
$NAS_USER = "wfadmin"
$NAS_IP   = "192.168.100.38"

$TARGETS = @{
    "1" = @{ Name="test-lifeart";     Path="/volume1/web/test-lifeart";     URL="https://test-lifeart.lifeart.ai.kr";     Color="Yellow"  }
    "2" = @{ Name="production";       Path="/volume1/web/lifeart";          URL="https://www.lifeart.ai.kr";              Color="Green"   }
    "9" = @{ Name="pre-test-lifeart"; Path="/volume1/web/pre-test-lifeart"; URL="https://pre-test-lifeart.lifeart.ai.kr"; Color="Magenta" }
}

$EXCLUDE = @("deploy.ps1","deploy.log",".git","node_modules","*.bak")
# ────────────────────────────────────────────────────────────────

$LOCAL_PATH = $PSScriptRoot
$TIMESTAMP  = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
$LOG_FILE   = "$LOCAL_PATH\deploy.log"

Write-Host ""
Write-Host "  ╔════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "  ║   LifeArt  Web  Deploy                  ║" -ForegroundColor Cyan
Write-Host "  ║   $TIMESTAMP           ║" -ForegroundColor Gray
Write-Host "  ╚════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

if (-not (Get-Command scp -ErrorAction SilentlyContinue)) {
    Write-Host "  [오류] OpenSSH 클라이언트가 없습니다." -ForegroundColor Red
    exit 1
}

Write-Host "  배포 대상을 선택하세요:" -ForegroundColor White
Write-Host ""
Write-Host "    [1]  test-lifeart      — 고객사 공개용(단계적 공개)  (test-lifeart.lifeart.ai.kr)"     -ForegroundColor Yellow
Write-Host "    [2]  production        — 실 서비스               (www.lifeart.ai.kr)"                  -ForegroundColor Green
Write-Host "    [9]  pre-test-lifeart  — 비공개 검수용             (pre-test-lifeart.lifeart.ai.kr)"    -ForegroundColor Magenta
Write-Host "    [Q]  취소"                                                    -ForegroundColor Gray
Write-Host ""
if ($Target) {
    $choice = $Target
    Write-Host "  (비대화형 모드 — Target: $Target)" -ForegroundColor DarkGray
} else {
    $choice = Read-Host "  선택"
}

if ($choice -match "^[Qq]$") { Write-Host "`n  취소됨." -ForegroundColor Gray; exit 0 }
if (-not $TARGETS.ContainsKey($choice)) {
    Write-Host "`n  [오류] 잘못된 선택." -ForegroundColor Red; exit 1
}

$T = $TARGETS[$choice]

if ($choice -eq "2") {
    Write-Host ""
    Write-Host "  ⚠️  production 배포 — 실 서비스(www.lifeart.ai.kr)에 즉시 반영됩니다." -ForegroundColor Red
    if (-not $Target) {
        $confirm = Read-Host "  계속하려면 'yes' 입력"
        if ($confirm -ne "yes") { Write-Host "`n  취소됨." -ForegroundColor Gray; exit 0 }
    }
}

Write-Host ""
Write-Host "  ▶ 배포 환경 : $($T.Name)" -ForegroundColor $T.Color
Write-Host "  ▶ 대상 경로 : ${NAS_IP}:$($T.Path)" -ForegroundColor White
Write-Host "  ▶ 공개 URL  : $($T.URL)" -ForegroundColor White
Write-Host ""

$gitBash = "C:\Program Files\Git\bin\bash.exe"
if (-not (Test-Path $gitBash)) { $gitBash = "$env:ProgramFiles\Git\bin\bash.exe" }

# ── 배포 전 NAS 현재 버전 백업 ──────────────────────────────────
$BACKUP_ROOT = "/volume1/web/_backups"
$BACKUP_TS   = Get-Date -Format "yyyyMMdd_HHmmss"
$BACKUP_PATH = "${BACKUP_ROOT}/$($T.Name)/${BACKUP_TS}"
Write-Host "  ▶ 현재 NAS 파일 백업 중..." -ForegroundColor Gray
$backupCmd = "mkdir -p '${BACKUP_ROOT}/$($T.Name)' && cp -r '$($T.Path)' '${BACKUP_PATH}' 2>/dev/null; " +
             "ls '${BACKUP_ROOT}/$($T.Name)' | sort | head -n -5 | xargs -I{} rm -rf '${BACKUP_ROOT}/$($T.Name)/{}'; echo done"
& $gitBash -c "ssh -o StrictHostKeyChecking=no ${NAS_USER}@${NAS_IP} `"$backupCmd`"" 2>&1 | Out-Null
Write-Host "    백업: ${BACKUP_PATH}" -ForegroundColor DarkGray
Write-Host ""

Write-Host "  ▶ NAS 전송 중..." -ForegroundColor Yellow

$dl         = $LOCAL_PATH.Substring(0,1).ToLower()
$posixLocal = '/' + $dl + ($LOCAL_PATH.Substring(2) -replace '\\', '/')
$remotePath = $T.Path

& $gitBash -c "ssh -o StrictHostKeyChecking=no ${NAS_USER}@${NAS_IP} 'mkdir -p ${remotePath}'" | Out-Null

$excludeFlags = ($EXCLUDE | ForEach-Object { "--exclude='$_'" }) -join ' '

# tar+SSH: D:\drive_files\ 는 Google Drive 클라우드 마운트라 scp -r 은 파일 누락 위험 (synology-web/deploy.ps1과 동일 이유)
$bashCmd = "set -o pipefail; cd '$posixLocal' && tar -czf - $excludeFlags . | " +
           "ssh -o StrictHostKeyChecking=no -o LogLevel=ERROR ${NAS_USER}@${NAS_IP} " +
           "'tar -xzf - -C ${remotePath}/ --no-same-permissions --no-same-owner 2>&1; echo TAR_EXIT:`$?'"

$result    = & $gitBash -c $bashCmd 2>&1
$resultStr = ($result -join "`n")
$meaningfulLines = $result | Where-Object { $_ -notmatch 'Cannot change mode|Exiting with failure' }
$hasTarErrors    = ($meaningfulLines | Where-Object { $_ -match '^tar:' }).Count -gt 0
$ok = ($LASTEXITCODE -eq 0) -and ($resultStr -match 'TAR_EXIT:[012]') -and -not $hasTarErrors

"[$TIMESTAMP] → $($T.Name) : $(if ($ok){'SUCCESS'}else{'FAILED'})" | Add-Content $LOG_FILE

Write-Host ""
if ($ok) {
    Write-Host "  ╔════════════════════════════════════════╗" -ForegroundColor $T.Color
    Write-Host "  ║  ✅ 배포 완료                           ║" -ForegroundColor $T.Color
    Write-Host "  ║  → $($T.Name.PadRight(36))║" -ForegroundColor $T.Color
    Write-Host "  ║  $($T.URL.PadRight(40))║" -ForegroundColor $T.Color
    Write-Host "  ╚════════════════════════════════════════╝" -ForegroundColor $T.Color

    Write-Host ""
    Write-Host "  ▶ NAS 파일 검증 중..." -ForegroundColor Gray
    $tPath = $T.Path
    $verifyResult = & $gitBash -c "ssh -o StrictHostKeyChecking=no -o LogLevel=ERROR ${NAS_USER}@${NAS_IP} ls -la ${tPath}/index.html ${tPath}/about/story/index.html" 2>&1
    Write-Host $verifyResult -ForegroundColor DarkCyan
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  ⚠️  일부 파일 전송 실패." -ForegroundColor Red
    }
} else {
    Write-Host "  ╔════════════════════════════════════════╗" -ForegroundColor Red
    Write-Host "  ║  ❌ 배포 실패                           ║" -ForegroundColor Red
    Write-Host "  ╚════════════════════════════════════════╝" -ForegroundColor Red
    Write-Host $result -ForegroundColor DarkRed
}

Write-Host ""
