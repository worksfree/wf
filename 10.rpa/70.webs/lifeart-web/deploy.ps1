# ================================================================
#  deploy.ps1 — LifeArt 웹 배포 스크립트 (WorksFree 자체 사이트와 완전 분리된
#  독립 클라이언트 프로젝트. synology-web과 무관)
#
#  사용법:
#    PowerShell: .\deploy.ps1              (대화형)
#    비대화형:   .\deploy.ps1 -Target 1    (1=test-lifeart, 2=production, 9=pre-test-lifeart)
#    단계적 배포: .\deploy.ps1 -Target 1 -Day 3   (git tag lifeart-day3 시점 스냅샷만 전송)
# ================================================================
param([string]$Target = "", [string]$Day = "")

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding          = [System.Text.Encoding]::UTF8
chcp 65001 | Out-Null

# ── ✏️  여기만 수정하면 됩니다 ──────────────────────────────────
$NAS_USER = "wfadmin"
$NAS_IP   = "192.168.100.38"
$VERSION  = "0.7.0.4"   # 배포 시 자동 증가 (pre-test=BUILD↑, test=PATCH↑, production=MINOR↑)

$TARGETS = @{
    "1" = @{ Name="test-lifeart";     Path="/volume1/web/test-lifeart";     URL="https://test-lifeart.lifeart.ai.kr";     Color="Yellow"  }
    "2" = @{ Name="production";       Path="/volume1/web/lifeart";          URL="https://www.lifeart.ai.kr";              Color="Green"   }
    "9" = @{ Name="pre-test-lifeart"; Path="/volume1/web/pre-test-lifeart"; URL="https://pre-test-lifeart.lifeart.ai.kr"; Color="Magenta" }
}

# 배포 제외: worker/supabase/tests/.git/node_modules/.wrangler/deploy.ps1 등
# (스테이징 복사 단계에서 rm 처리 — 아래 전송부 참고)
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

# ── 버전 자동 증가 (확인 통과 후) ──────────────────────────────
#   pre-test(9)=BUILD(4번째)↑ · test(1)=PATCH(3번째)↑+BUILD리셋 · production(2)=MINOR(2번째)↑+PATCH·BUILD리셋
#   -Day 스테이징 배포 시에는 태그에 커밋된 버전을 그대로 사용(증가 안 함).
if (-not $Day -and $VERSION -match '^(\d+)\.(\d+)\.(\d+)\.(\d+)$') {
    $p = @([int]$Matches[1], [int]$Matches[2], [int]$Matches[3], [int]$Matches[4])
    switch ($choice) {
        "2" { $p[1]++; $p[2] = 0; $p[3] = 0 }   # production: MINOR↑
        "1" { $p[2]++; $p[3] = 0 }              # test: PATCH↑
        default { $p[3]++ }                      # pre-test: BUILD↑
    }
    $newVer  = "$($p[0]).$($p[1]).$($p[2]).$($p[3])"
    # deploy.ps1 자기 자신의 $VERSION 갱신 (UTF-8 BOM 유지 — 한글 포함)
    $selfTxt = [System.IO.File]::ReadAllText($PSCommandPath, [System.Text.Encoding]::UTF8)
    $selfTxt = $selfTxt -replace '(\$VERSION\s*=\s*")[\d.]+"', ('${1}' + $newVer + '"')
    [System.IO.File]::WriteAllText($PSCommandPath, $selfTxt, (New-Object System.Text.UTF8Encoding($true)))
    # 공통 푸터 파트셜의 버전 문자열 갱신 (전 페이지가 이 파트셜을 로드)
    $footer = Join-Path $LOCAL_PATH 'assets\footer.html'
    if (Test-Path $footer) {
        $fTxt = [System.IO.File]::ReadAllText($footer, [System.Text.Encoding]::UTF8)
        $fTxt = $fTxt -replace 'v\d+\.\d+\.\d+\.\d+', "v$newVer"
        [System.IO.File]::WriteAllText($footer, $fTxt, [System.Text.Encoding]::UTF8)
    }
    $VERSION = $newVer
}

Write-Host ""
Write-Host "  ▶ 배포 환경 : $($T.Name)" -ForegroundColor $T.Color
Write-Host "  ▶ 대상 경로 : ${NAS_IP}:$($T.Path)" -ForegroundColor White
Write-Host "  ▶ 공개 URL  : $($T.URL)" -ForegroundColor White
Write-Host "  ▶ 버전      : v$VERSION" -ForegroundColor White
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

$SOURCE_PATH = $LOCAL_PATH
$tempArchiveDir = $null

if ($Day) {
    $tag = "lifeart-day$Day"
    $dl0         = $LOCAL_PATH.Substring(0,1).ToLower()
    $posixLocal0 = '/' + $dl0 + ($LOCAL_PATH.Substring(2) -replace '\\', '/')

    & $gitBash -c "cd '$posixLocal0' && git rev-parse -q --verify refs/tags/$tag" | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  [오류] git 태그 '$tag' 를 찾을 수 없습니다." -ForegroundColor Red
        exit 1
    }

    $tempArchiveDir = Join-Path $env:TEMP "lifeart-deploy-day$Day-$(Get-Random)"
    New-Item -ItemType Directory -Path $tempArchiveDir -Force | Out-Null
    $tempPosix = '/' + $tempArchiveDir.Substring(0,1).ToLower() + ($tempArchiveDir.Substring(2) -replace '\\', '/')

    & $gitBash -c "cd '$posixLocal0' && git archive '$tag' -- 10.rpa/70.webs/lifeart-web | tar -x -C '$tempPosix'" 2>&1 | Out-Null

    $SOURCE_PATH = Join-Path $tempArchiveDir "10.rpa\70.webs\lifeart-web"
    if (-not (Test-Path (Join-Path $SOURCE_PATH "index.html"))) {
        Write-Host "  [오류] '$tag' 스냅샷 추출에 실패했습니다." -ForegroundColor Red
        exit 1
    }
    Write-Host "  ▶ 단계적 배포: $tag 시점 스냅샷 사용 (임시: $SOURCE_PATH)" -ForegroundColor Magenta
}

$srcDl      = $SOURCE_PATH.Substring(0,1).ToLower()
$srcPosix   = '/' + $srcDl + ($SOURCE_PATH.Substring(2) -replace '\\', '/')
$remotePath = $T.Path

# ── 스테이징 복사본 생성 (작업트리 오염 없이 캐시버스팅 적용) ──────
# Cloudflare 퍼지 권한이 없어 버전 쿼리(?v=)로 CDN·브라우저 캐시를 무력화.
$stageWin   = Join-Path $env:TEMP "lifeart-stage-$BACKUP_TS"
$stagePosix = '/' + $stageWin.Substring(0,1).ToLower() + ($stageWin.Substring(2) -replace '\\', '/')
$BUST       = if ($Day) { "d$Day-$BACKUP_TS" } else { $VERSION }

# 소스 → 스테이지 복사 후 불필요 폴더 제거 (배포 대상만 남김)
& $gitBash -c "rm -rf '$stagePosix'; mkdir -p '$stagePosix'; cp -r '$srcPosix'/. '$stagePosix'/; cd '$stagePosix'; rm -rf worker supabase tests .git node_modules .wrangler; rm -f deploy.ps1 deploy.log *.bak *.log" 2>&1 | Out-Null

# 캐시버스팅: 모든 *.html 과 layout.js 의 /assets/*.js|css|html 참조에 ?v=$BUST 부착
$bustRe = [regex]'(/assets/[A-Za-z0-9_./-]+\.(?:js|css|html))'
Get-ChildItem -Path $stageWin -Recurse -File | Where-Object { $_.Extension -eq '.html' -or $_.Name -eq 'layout.js' } | ForEach-Object {
    $c = [System.IO.File]::ReadAllText($_.FullName, [System.Text.Encoding]::UTF8)
    $c = $bustRe.Replace($c, "`$1?v=$BUST")
    [System.IO.File]::WriteAllText($_.FullName, $c, [System.Text.Encoding]::UTF8)
}

& $gitBash -c "ssh -o StrictHostKeyChecking=no ${NAS_USER}@${NAS_IP} 'mkdir -p ${remotePath}'" | Out-Null

# tar+SSH: D:\drive_files\ 는 Google Drive 클라우드 마운트라 scp -r 은 파일 누락 위험 (synology-web/deploy.ps1과 동일 이유)
$bashCmd = "set -o pipefail; cd '$stagePosix' && tar -czf - . | " +
           "ssh -o StrictHostKeyChecking=no -o LogLevel=ERROR ${NAS_USER}@${NAS_IP} " +
           "'tar -xzf - -C ${remotePath}/ --no-same-permissions --no-same-owner 2>&1; echo TAR_EXIT:`$?'"

$result    = & $gitBash -c $bashCmd 2>&1
$resultStr = ($result -join "`n")
& $gitBash -c "rm -rf '$stagePosix'" 2>&1 | Out-Null
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

if ($tempArchiveDir -and (Test-Path $tempArchiveDir)) {
    Remove-Item -Recurse -Force $tempArchiveDir
}

Write-Host ""
