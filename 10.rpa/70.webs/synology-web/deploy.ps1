# ================================================================
#  deploy.ps1  —  WorksFree 웹 배포 스크립트
#  위치: D:\drive_files\10.worksfree\10.rpa\70.webs\synology-web\
#
#  사용법:
#    ① deploy.bat 더블클릭         (가장 쉬움)
#    ② PowerShell: .\deploy.ps1    (대화형)
#    ③ VS Code:    Ctrl+Shift+B
#    ④ 비대화형:   .\deploy.ps1 -Target 1   (1=test, 2=staging, 3=portal, 4=g1)
# ================================================================
param([string]$Target = "")

# 한글 콘솔 출력 (UTF-8)
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding          = [System.Text.Encoding]::UTF8
chcp 65001 | Out-Null

# bat 래퍼(deploy.bat)로 실행됐는지 감지 — bat는 cmd.exe가 새 powershell.exe를 생성하므로 부모 프로세스가 cmd
$fromBat = try {
    $parentId = (Get-CimInstance -ClassName Win32_Process -Filter "ProcessId = $PID").ParentProcessId
    (Get-Process -Id $parentId -ErrorAction Stop).Name -like 'cmd'
} catch { $false }

# ── ✏️  여기만 수정하면 됩니다 ──────────────────────────────────
$NAS_USER = "wfadmin"             # NAS SSH 계정
$NAS_IP   = "192.168.100.38"      # NAS 로컬 IP (공유기에서 고정 권장)
$VERSION  = "0.8.5.59"            # 현재 배포 버전 (test=4번째↑, staging=3번째↑, portal=2번째↑)

# 배포 대상 환경
$TARGETS = @{
    "1" = @{ Name="test";             Path="/volume1/web/test";         URL="https://test.worksfree.kr";          Color="Yellow"; SubDir=$null }
    "2" = @{ Name="staging";          Path="/volume1/web/staging";      URL="https://staging.worksfree.kr";       Color="Cyan";   SubDir=$null }
    "3" = @{ Name="www (prod)";        Path="/volume1/web/portal";       URL="https://www.worksfree.kr";           Color="Green";  SubDir=$null }
    "4" = @{ Name="g1consulting";     Path="/volume1/web/g1consulting"; URL="https://g1consulting.worksfree.kr";  Color="Magenta"; SubDir="consulting/g1" }
    "5" = @{ Name="el";              Path="/volume1/web/el";           URL="https://el.worksfree.kr";           Color="Cyan";   SubDir="consulting/tacomanager" }
}

# 배포 제외 목록
$EXCLUDE = @("deploy.ps1","deploy.bat","deploy.log",".vscode","*.log","*.bak",".git","node_modules","*.sh",".claude","test-results","playwright-report")
# ────────────────────────────────────────────────────────────────

# 배포 환경 선택 후 증가하므로, 여기서는 현재값 저장만
$OLD_VERSION   = $VERSION
$scriptContent = [System.IO.File]::ReadAllText($PSCommandPath, [System.Text.Encoding]::UTF8)

$LOCAL_PATH = $PSScriptRoot
$TIMESTAMP  = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
$LOG_FILE   = "$LOCAL_PATH\deploy.log"

# ── 헤더 ────────────────────────────────────────────────────────
Clear-Host
Write-Host ""
Write-Host "  ╔════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "  ║    WorksFree  Web  Deploy  v$VERSION    ║" -ForegroundColor Cyan
Write-Host "  ║    $TIMESTAMP           ║" -ForegroundColor Gray
Write-Host "  ╚════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# ── OpenSSH 확인 ────────────────────────────────────────────────
if (-not (Get-Command scp -ErrorAction SilentlyContinue)) {
    Write-Host "  [오류] OpenSSH 클라이언트가 없습니다." -ForegroundColor Red
    Write-Host "  Windows 설정 → 앱 → 선택적 기능 → OpenSSH 클라이언트 추가" -ForegroundColor Yellow
    Write-Host ""
    if ($fromBat) { Read-Host "  Enter 키로 종료" }
    exit 1
}

# ── 배포 대상 선택 ───────────────────────────────────────────────
Write-Host "  배포 대상을 선택하세요:" -ForegroundColor White
Write-Host ""
Write-Host "    [1]  test          — 기능 검증용     (test.worksfree.kr)"          -ForegroundColor Yellow
Write-Host "    [2]  staging       — 최종 점검용    (staging.worksfree.kr)"       -ForegroundColor Cyan
Write-Host "    [3]  www (prod)   — 실 서비스 배포  (www.worksfree.kr)"       -ForegroundColor Green
Write-Host "    [4]  g1consulting  — 현장클리닉 전용 (g1consulting.worksfree.kr)"    -ForegroundColor Magenta
Write-Host "    [5]  el           — 타코매니저 AI 전용 (el.worksfree.kr)"           -ForegroundColor Cyan
Write-Host "    [6]  test + el   — 같은 버전으로 동시 배포 (test + el)"              -ForegroundColor Yellow
Write-Host "    [Q]  취소"                                                            -ForegroundColor Gray
Write-Host "    [R]  롤백          — 이전 배포 버전 복원"                             -ForegroundColor DarkYellow
Write-Host ""
if ($Target) {
    $choice = $Target
    Write-Host "  (비대화형 모드 — Target: $Target)" -ForegroundColor DarkGray
} else {
    $choice = Read-Host "  선택"
}

if ($choice -match "^[Qq]$") {
    Write-Host "`n  취소됨." -ForegroundColor Gray; Start-Sleep 1; exit 0
}

# ── 롤백 플로우 ─────────────────────────────────────────────────
if ($choice -match "^[Rr]$") {
    $BACKUP_ROOT = "/volume1/web/_backups"
    Write-Host "`n  롤백할 환경을 선택하세요:" -ForegroundColor White
    Write-Host ""
    Write-Host "    [1]  test" -ForegroundColor Yellow
    Write-Host "    [2]  staging" -ForegroundColor Cyan
    Write-Host "    [3]  www (prod) " -ForegroundColor Green
    Write-Host "    [4]  g1consulting" -ForegroundColor Magenta
    Write-Host "    [5]  el" -ForegroundColor Cyan
    Write-Host ""
    $envChoice = Read-Host "  선택"
    if (-not $TARGETS.ContainsKey($envChoice)) {
        Write-Host "  [오류] 잘못된 선택." -ForegroundColor Red
        if ($fromBat) { Read-Host "  Enter 키로 종료" }; exit 1
    }
    $T = $TARGETS[$envChoice]
    $listCmd = "ls -t '${BACKUP_ROOT}/$($T.Name)' 2>/dev/null"
    $backups = & $gitBash -c "ssh -o StrictHostKeyChecking=no ${NAS_USER}@${NAS_IP} `"$listCmd`"" 2>&1
    $backupList = @($backups | Where-Object { $_ -match '\S' })
    if ($backupList.Count -eq 0) {
        Write-Host "`n  백업이 없습니다. 한 번이라도 배포해야 백업이 생성됩니다." -ForegroundColor Red
        if ($fromBat) { Read-Host "  Enter 키로 종료" }; exit 1
    }
    Write-Host "`n  복원 가능한 백업 ($($T.Name)):" -ForegroundColor White
    for ($i = 0; $i -lt $backupList.Count; $i++) {
        $tag = if ($i -eq 0) { "  ← 최신" } else { "" }
        Write-Host "    [$($i+1)] $($backupList[$i])$tag" -ForegroundColor $(if($i -eq 0){"Yellow"}else{"Gray"})
    }
    Write-Host ""
    $pick = Read-Host "  복원할 번호 (Enter = 최신)"
    if ([string]::IsNullOrWhiteSpace($pick)) { $pick = "1" }
    $idx = [int]$pick - 1
    if ($idx -lt 0 -or $idx -ge $backupList.Count) {
        Write-Host "  잘못된 번호." -ForegroundColor Red; if ($fromBat) { Read-Host "  Enter 키로 종료" }; exit 1
    }
    $selected    = $backupList[$idx]
    $restoreSrc  = "${BACKUP_ROOT}/$($T.Name)/${selected}"
    Write-Host "`n  ⚠️  [$($T.Name)] 을(를) 아래 버전으로 복원합니다:" -ForegroundColor Yellow
    Write-Host "     $selected" -ForegroundColor White
    $confirm = Read-Host "  계속하려면 'yes' 입력"
    if ($confirm -ne "yes") { Write-Host "`n  취소됨." -ForegroundColor Gray; if ($fromBat) { Read-Host "  Enter 키로 종료" }; exit 0 }
    Write-Host "`n  ▶ 복원 중..." -ForegroundColor Yellow
    $restoreCmd = "rm -rf '$($T.Path)' && cp -r '${restoreSrc}' '$($T.Path)' && echo OK"
    $restoreResult = & $gitBash -c "ssh -o StrictHostKeyChecking=no ${NAS_USER}@${NAS_IP} `"$restoreCmd`"" 2>&1
    if ($LASTEXITCODE -eq 0 -and $restoreResult -match "OK") {
        Write-Host "  ✅ 롤백 완료 → $($T.URL)" -ForegroundColor Green
    } else {
        Write-Host "  ❌ 롤백 실패" -ForegroundColor Red
        Write-Host $restoreResult -ForegroundColor DarkRed
    }
    if ($fromBat) { Read-Host "`n  Enter 키로 종료" }; exit 0
}
# ─────────────────────────────────────────────────────────────────

if ($choice -ne "6" -and -not $TARGETS.ContainsKey($choice)) {
    Write-Host "`n  [오류] 잘못된 선택." -ForegroundColor Red
    if ($fromBat) { Read-Host "  Enter 키로 종료" }; exit 1
}

$T = if ($choice -eq "6") { $TARGETS["1"] } else { $TARGETS[$choice] }

# ── portal / g1consulting 이중 확인 (버전 증가보다 먼저 실행) ────
# 버전은 확인 이후에만 증가해야 취소/실패 시 중복 bump 방지
if ($choice -eq "3") {
    Write-Host ""
    Write-Host "  ⚠️  www(production) 배포 — 실 서비스에 즉시 반영됩니다." -ForegroundColor Red
    if ($Target) {
        Write-Host "  (비대화형 모드 — -Target 3 지정 시 자동 승인)" -ForegroundColor DarkGray
    } else {
        $confirm = Read-Host "  계속하려면 'yes' 입력"
        if ($confirm -ne "yes") {
            Write-Host "`n  취소됨." -ForegroundColor Gray; Start-Sleep 1; exit 0
        }
    }
}
if ($choice -eq "4") {
    Write-Host ""
    Write-Host "  ℹ️  g1consulting 전용 배포: consulting/g1/ → /volume1/web/g1consulting/" -ForegroundColor Magenta
    Write-Host "     (NAS 디렉터리가 없으면 자동 생성됩니다)" -ForegroundColor Gray
    if (-not $Target) {
        $confirm = Read-Host "  계속하려면 Enter, 취소는 Q"
        if ($confirm -match "^[Qq]$") {
            Write-Host "`n  취소됨." -ForegroundColor Gray; Start-Sleep 1; exit 0
        }
    }
}
if ($choice -eq "5") {
    Write-Host ""
    Write-Host "  ℹ️  el 전용 배포: consulting/tacomanager/ → /volume1/web/el/" -ForegroundColor Cyan
    Write-Host "     (타코매니저 AI 로그인 없는 단독 사이트 — el.worksfree.kr)" -ForegroundColor Gray
    if (-not $Target) {
        $confirm = Read-Host "  계속하려면 Enter, 취소는 Q"
        if ($confirm -match "^[Qq]$") {
            Write-Host "`n  취소됨." -ForegroundColor Gray; Start-Sleep 1; exit 0
        }
    }
}
if ($choice -eq "6") {
    Write-Host ""
    Write-Host "  ℹ️  test + el 동시 배포 — 같은 버전으로 순차 전송" -ForegroundColor Yellow
    Write-Host "     test.worksfree.kr (전체) + el.worksfree.kr (tacomanager)" -ForegroundColor Gray
    if (-not $Target) {
        $confirm = Read-Host "  계속하려면 Enter, 취소는 Q"
        if ($confirm -match "^[Qq]$") {
            Write-Host "`n  취소됨." -ForegroundColor Gray; Start-Sleep 1; exit 0
        }
    }
}

# ── 버전 자동 증가 (확인 통과 후 실행) ──────────────────────────
# 규칙: test·g1=4번째 자연 증가, staging=3번째↑+4번째 리셋, portal=2번째↑+3·4번째 리셋
if ($scriptContent -match '\$VERSION\s*=\s*"(\d+)\.(\d+)\.(\d+)\.(\d+)"') {
    $p = @([int]$Matches[1], [int]$Matches[2], [int]$Matches[3], [int]$Matches[4])
    switch ($choice) {
        "2" {        # staging: 3번째↑, 4번째 리셋, 자릿수 올림
            $p[2]++; $p[3] = 0
            for ($i = 2; $i -gt 0; $i--) { if ($p[$i] -ge 10) { $p[$i] = 0; $p[$i-1]++ } }
        }
        "3" {        # portal: 2번째↑, 3·4번째 리셋
            $p[1]++; $p[2] = 0; $p[3] = 0
            if ($p[1] -ge 10) { $p[1] = 0; $p[0]++ }
        }
        default {    # test(1) · g1consulting(4): 4번째 자연 증가 (상한 없음)
            $p[3]++
        }
    }
    $newVer  = "$($p[0]).$($p[1]).$($p[2]).$($p[3])"
    $updated = $scriptContent -replace '(\$VERSION\s*=\s*")[\d.]+"', ('${1}' + $newVer + '"')
    [System.IO.File]::WriteAllText($PSCommandPath, $updated, [System.Text.Encoding]::UTF8)
    $VERSION = $newVer
    $indexPath = Join-Path $PSScriptRoot 'index.html'
    if (Test-Path $indexPath) {
        $html = [System.IO.File]::ReadAllText($indexPath, [System.Text.Encoding]::UTF8)
        $html = $html -replace "(const HUB_VERSION\s*=\s*')[\d.]+'", ('${1}' + $newVer + "'")
        [System.IO.File]::WriteAllText($indexPath, $html, [System.Text.Encoding]::UTF8)
    }
}
# ─────────────────────────────────────────────────────────────────

# 배포 대상 목록 — "6"이면 test(1) + el(5) 순서로 순차 실행
$deployList = if ($choice -eq "6") { @("1","5") } else { @($choice) }
$allOk      = $true

foreach ($deployKey in $deployList) {
$T = $TARGETS[$deployKey]

# ── 배포 항목 목록 ───────────────────────────────────────────────
Write-Host ""
Write-Host "  ▶ 배포 환경 : $($T.Name)" -ForegroundColor $T.Color
Write-Host "  ▶ 대상 경로 : ${NAS_IP}:$($T.Path)" -ForegroundColor White
Write-Host "  ▶ 공개 URL  : $($T.URL)" -ForegroundColor White
Write-Host ""

# SubDir 여부에 따라 배포 소스 경로 결정
$isSubDir   = ($null -ne $T.SubDir)
$sourcePath = if ($isSubDir) { Join-Path $LOCAL_PATH $T.SubDir } else { $LOCAL_PATH }

if ($isSubDir) {
    Write-Host "  배포 항목: $($T.SubDir)/" -ForegroundColor Gray
} else {
    $items = Get-ChildItem -Path $LOCAL_PATH -Exclude $EXCLUDE | ForEach-Object { $_.FullName }
    Write-Host "  배포 항목:" -ForegroundColor Gray
    $items | ForEach-Object { Write-Host "    ✦ $(Split-Path $_ -Leaf)" -ForegroundColor Gray }
}
Write-Host ""

# ── 전송 (Git Bash tar+SSH) ─────────────────────────────────────
# D:\drive_files\ 는 Google Drive for Desktop 클라우드 마운트.
# SCP -r 은 cloud-only 디렉터리를 readdir()로 순회하는데,
# POSIX 레이어에서도 cloud placeholder 폴더는 빈 목록을 반환해 파일 누락 발생.
# tar 는 파일 내용을 직접 읽어(read() syscall) Google Drive 강제 다운로드를 유발하므로
# tar+SSH 파이프라인이 cloud-only 파일까지 완전히 전송하는 유일한 방법.
$gitBash = "C:\Program Files\Git\bin\bash.exe"
if (-not (Test-Path $gitBash)) { $gitBash = "$env:ProgramFiles\Git\bin\bash.exe" }

# ── 배포 전 NAS 현재 버전 백업 ──────────────────────────────────
$BACKUP_ROOT = "/volume1/web/_backups"
$BACKUP_TS   = Get-Date -Format "yyyyMMdd_HHmmss"
$BACKUP_NAME = "${BACKUP_TS}_v${OLD_VERSION}"
$BACKUP_PATH = "${BACKUP_ROOT}/$($T.Name)/${BACKUP_NAME}"
$KEEP_N      = 5  # 환경별 최대 보관 개수
Write-Host "  ▶ 현재 NAS 파일 백업 중..." -ForegroundColor Gray
$backupCmd = "mkdir -p '${BACKUP_ROOT}/$($T.Name)' && " +
             "cp -r '$($T.Path)' '${BACKUP_PATH}' 2>/dev/null; " +
             "ls '${BACKUP_ROOT}/$($T.Name)' | sort | head -n -${KEEP_N} | " +
             "xargs -I{} rm -rf '${BACKUP_ROOT}/$($T.Name)/{}'; echo done"
& $gitBash -c "ssh -o StrictHostKeyChecking=no ${NAS_USER}@${NAS_IP} `"$backupCmd`"" 2>&1 | Out-Null
Write-Host "    백업: ${BACKUP_PATH}" -ForegroundColor DarkGray
Write-Host ""
# ─────────────────────────────────────────────────────────────────

Write-Host "  ▶ NAS 전송 중..." -ForegroundColor Yellow

if (Test-Path $gitBash) {
    $dl         = $sourcePath.Substring(0,1).ToLower()
    $posixLocal = '/' + $dl + ($sourcePath.Substring(2) -replace '\\', '/')
    $remotePath = $T.Path

    # g1consulting 는 NAS 디렉터리 먼저 생성
    if ($isSubDir) {
        & $gitBash -c "ssh -o StrictHostKeyChecking=no ${NAS_USER}@${NAS_IP} 'mkdir -p ${remotePath}'" | Out-Null
    }

    # tar로 묶기(cloud-only 파일 포함) → SSH 파이프 → NAS에서 풀기
    $excludeFlags = if ($isSubDir) { "" } else {
        "--exclude='deploy.ps1' --exclude='deploy.bat' " +
        "--exclude='*.log' --exclude='*.sh' " +
        "--exclude='.git' --exclude='node_modules' --exclude='.vscode' " +
        "--exclude='.claude' --exclude='test-results' --exclude='playwright-report' "
    }
    # set -o pipefail: local tar 실패(클라우드 파일 읽기 오류 등)를 exit code로 전파
    # echo TAR_EXIT:$?: remote tar 결과를 명시적으로 출력 (exit 0 마스킹 제거)
    $bashCmd = "set -o pipefail; cd '$posixLocal' && tar -czf - ${excludeFlags}" +
               ". | ssh -o StrictHostKeyChecking=no -o LogLevel=ERROR ${NAS_USER}@${NAS_IP} " +
               "'tar -xzf - -C ${remotePath}/ --no-same-permissions --no-same-owner 2>&1; echo TAR_EXIT:`$?'"

    Write-Host "  (Git Bash tar+SSH — cloud-only 파일 포함 전체 전송)" -ForegroundColor Gray
    $result    = & $gitBash -c $bashCmd 2>&1
    $resultStr = ($result -join "`n")
    # "Cannot change mode" / "Exiting with failure": NAS 웹 루트 디렉터리 소유자가
    # wfadmin이 아닐 때 발생하는 무해한 권한 복원 실패 — 파일 추출은 정상 완료됨
    # PS 쪽에서 필터링 (bash 쪽 grep "..." 사용 시 PS→bash 인자 전달 quoting 파괴됨)
    $meaningfulLines = $result | Where-Object { $_ -notmatch 'Cannot change mode|Exiting with failure' }
    $hasTarErrors    = ($meaningfulLines | Where-Object { $_ -match '^tar:' }).Count -gt 0
    $ok = ($LASTEXITCODE -eq 0) -and ($resultStr -match 'TAR_EXIT:[012]') -and -not $hasTarErrors
} else {
    Write-Host "  ⚠ Git Bash 미설치 — Windows scp 사용 (클라우드 파일 누락 위험)" -ForegroundColor DarkYellow
    $scpArgs = @("-r", "-O", "-o", "StrictHostKeyChecking=no", $sourcePath, "${NAS_USER}@${NAS_IP}:$($T.Path)/")
    $result  = & scp @scpArgs 2>&1
    $ok      = ($LASTEXITCODE -eq 0)
}

# ── 로그 기록 ───────────────────────────────────────────────────
"[$TIMESTAMP] v$VERSION → $($T.Name) : $(if ($ok){'SUCCESS'}else{'FAILED'})" | Add-Content $LOG_FILE

# ── 결과 출력 ───────────────────────────────────────────────────
Write-Host ""
if ($ok) {
    Write-Host "  ╔════════════════════════════════════════╗" -ForegroundColor $T.Color
    Write-Host "  ║  ✅ 배포 완료  v$VERSION                 ║" -ForegroundColor $T.Color
    Write-Host "  ║  → $($T.Name.PadRight(36))║" -ForegroundColor $T.Color
    Write-Host "  ║  $($T.URL.PadRight(40))║" -ForegroundColor $T.Color
    Write-Host "  ╚════════════════════════════════════════╝" -ForegroundColor $T.Color

    # ── NAS 파일 검증 ─────────────────────────────────────────────
    Write-Host ""
    Write-Host "  ▶ NAS 파일 검증 중..." -ForegroundColor Gray
    $tPath = $T.Path
    if ($isSubDir) {
        $f1 = "$tPath/index.html"
        $remoteCheck = "test -f '$f1' && echo 'OK: $f1' || echo 'FAIL: $f1'; " +
                       "test -d '$tPath/.claude' && echo 'WARN: .claude_exists' || echo 'OK: no_claude'"
    } else {
        $f1 = "$tPath/index.html"
        $f2 = "$tPath/consulting/dart/index.html"
        $f3 = "$tPath/consulting/ceo/flyers/flyer-ceo.html"
        $remoteCheck = "test -f '$f1' && echo 'OK: $f1' || echo 'FAIL: $f1'; " +
                       "test -f '$f2' && echo 'OK: $f2' || echo 'FAIL: $f2'; " +
                       "test -f '$f3' && echo 'OK: $f3' || echo 'FAIL: $f3'; " +
                       "test -d '$tPath/.claude' && echo 'WARN: .claude_exists' || echo 'OK: no_claude'"
    }
    $verifyResult = & $gitBash -c "ssh -o StrictHostKeyChecking=no -o LogLevel=ERROR ${NAS_USER}@${NAS_IP} ""$remoteCheck""" 2>&1
    Write-Host $verifyResult -ForegroundColor DarkCyan
    if ($verifyResult -match 'FAIL:') {
        Write-Host "  ⚠️  일부 파일 전송 실패. 배포를 다시 시도하세요." -ForegroundColor Red
        $allOk = $false
    }
    if ($verifyResult -match 'WARN:') {
        Write-Host "  ⚠️  .claude 폴더가 NAS에 남아있습니다. 수동으로 삭제하세요." -ForegroundColor Yellow
    }
} else {
    $allOk = $false
    Write-Host "  ╔════════════════════════════════════════╗" -ForegroundColor Red
    Write-Host "  ║  ❌ 배포 실패                           ║" -ForegroundColor Red
    Write-Host "  ╚════════════════════════════════════════╝" -ForegroundColor Red
    Write-Host ""
    Write-Host $result -ForegroundColor DarkRed
    Write-Host ""
    Write-Host "  체크리스트:" -ForegroundColor Yellow
    Write-Host "    1. NAS IP 확인          : $NAS_IP"           -ForegroundColor Yellow
    Write-Host "    2. SSH 활성화 확인       : DSM → 제어판 → 터미널 및 SNMP" -ForegroundColor Yellow
    Write-Host "    3. 최초 1회 SSH 키 등록 :" -ForegroundColor Yellow
    Write-Host "       > ssh-keygen -t ed25519" -ForegroundColor Gray
    Write-Host "       > ssh-copy-id ${NAS_USER}@${NAS_IP}" -ForegroundColor Gray
}

} # end foreach deployList

# ── PDF 에셋 동기화 (staging/portal 배포 시 NAS 내 test → 해당 환경 복사) ──
# PDF는 대용량이라 deploy.ps1 배포 대상에 포함되지 않음.
# test에 업로드된 PDF를 NAS 내부에서 복사하여 staging/portal에 반영.
if ($allOk -and ($choice -eq "2" -or $choice -eq "3")) {
    $targetEnvPath = $T.Path
    Write-Host ""
    Write-Host "  ▶ PDF 에셋 동기화 (test → $($T.Name))..." -ForegroundColor Gray
    $syncCmd = "mkdir -p '${targetEnvPath}/assets/books' && " +
               "cp -r '/volume1/web/test/assets/books/.' '${targetEnvPath}/assets/books/' 2>&1 && echo 'SYNC_OK'"
    $syncResult = & $gitBash -c "ssh -o StrictHostKeyChecking=no ${NAS_USER}@${NAS_IP} ""$syncCmd""" 2>&1
    if ($syncResult -match 'SYNC_OK') {
        Write-Host "    ✅ PDF 에셋 동기화 완료" -ForegroundColor Green
    } else {
        Write-Host "    ⚠️  PDF 동기화 실패 (test에 assets/books 가 없을 수 있음)" -ForegroundColor Yellow
        Write-Host ($syncResult -join "`n") -ForegroundColor DarkYellow
    }
}

# ── Cloudflare 캐시 퍼지 (전체 배포 완료 후 1회) ────────────────
if ($allOk) {
    $CF_ZONE_ID   = "b5e82c46532b06a2cd456cc5ff3b9234"
    $secretsFile  = Join-Path $PSScriptRoot "secrets.ps1"
    if (Test-Path $secretsFile) { . $secretsFile }
    $CF_API_TOKEN = $env:CF_CACHE_PURGE_TOKEN
    Write-Host ""
    if (-not $CF_API_TOKEN) {
        Write-Host "    ⚠️  CF_CACHE_PURGE_TOKEN이 비어 있습니다 — secrets.ps1 확인 필요" -ForegroundColor Yellow
    } else {
        Write-Host "  ▶ Cloudflare 캐시 퍼지 중..." -ForegroundColor Gray
        try {
            $cfResult = Invoke-RestMethod `
                -Uri     "https://api.cloudflare.com/client/v4/zones/$CF_ZONE_ID/purge_cache" `
                -Method  POST `
                -Headers @{ "Authorization" = "Bearer $CF_API_TOKEN"; "Content-Type" = "application/json" } `
                -Body    '{"purge_everything":true}' `
                -ErrorAction Stop
            if ($cfResult.success) {
                Write-Host "    ✅ Cloudflare 캐시 퍼지 완료 — 브라우저 새로고침 시 최신 파일 적용됨" -ForegroundColor Green
            } else {
                $errCode = ($cfResult.errors | Select-Object -First 1).code
                if ($errCode -eq 10000) {
                    Write-Host "    ⚠️  Cloudflare 인증 오류 — API 토큰이 만료되었거나 권한이 없습니다" -ForegroundColor Yellow
                    Write-Host "    → cloudflare.com > My Profile > API Tokens > 기존 토큰 삭제 후 재발급" -ForegroundColor Yellow
                    Write-Host "    → 재발급 후 secrets.ps1 의 CF_CACHE_PURGE_TOKEN 값 교체" -ForegroundColor Yellow
                } else {
                    Write-Host "    ⚠️  Cloudflare 퍼지 실패: $($cfResult.errors | ConvertTo-Json -Compress)" -ForegroundColor Yellow
                }
            }
        } catch {
            $errBody = $_.ErrorDetails.Message
            if ($errBody -match '"code":10000') {
                Write-Host "    ⚠️  Cloudflare 인증 오류 — API 토큰이 만료되었거나 권한이 없습니다" -ForegroundColor Yellow
                Write-Host "    → cloudflare.com > My Profile > API Tokens > 기존 토큰 삭제 후 재발급" -ForegroundColor Yellow
                Write-Host "    → 재발급 후 secrets.ps1 의 CF_CACHE_PURGE_TOKEN 값 교체" -ForegroundColor Yellow
            } else {
                Write-Host "    ⚠️  Cloudflare 퍼지 오류: $_" -ForegroundColor Yellow
            }
        }
    }
}
# ────────────────────────────────────────────────────────────────

Write-Host ""
if ($fromBat) { Read-Host "  Enter 키로 종료" }
