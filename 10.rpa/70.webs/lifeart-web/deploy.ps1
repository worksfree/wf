# ================================================================
#  deploy.ps1 — LifeArt 웹 배포 스크립트 (WorksFree 자체 사이트와 완전 분리된
#  독립 클라이언트 프로젝트. synology-web과 무관)
#
#  사용법:
#    PowerShell: .\deploy.ps1              (대화형)
#    비대화형:   .\deploy.ps1 -Target 1    (1=pre-test, 2=test-lifeart, 3=production · Enter=1 pre-test)
#    단계 배포: .\deploy.ps1 -Target 2 -Stage N   (N=1~5, 누적 공개 · 완전 가역 · 보통 test=2 에 적용)
#       1=소개·상품·제작과정  2=+비즈니스·소셜  3=+고객지원·결제  4=+O&M  5=+Dev툴킷
#       └ 배포 사본의 config.js RELEASE_STAGE 만 치환. 소스는 항상 5(full) → pre-test 검수는 전체.
#       └ 값만 바꿔 재배포하면 1→5→다시 1 어느 단계로든 복원됨(소스 불변).
#       └ 배포 시 header/footer 를 각 페이지에 인라인 주입 → 링크 이동 시 헤더 깜빡임 없음.
#    (구) -Day N: git tag lifeart-dayN 스냅샷 배포 / -Menus: 폐지(-Stage 로 대체)
# ================================================================
param([string]$Target = "", [string]$Day = "", [string]$Menus = "", [string]$Stage = "")

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding          = [System.Text.Encoding]::UTF8
chcp 65001 | Out-Null

# ── ✏️  여기만 수정하면 됩니다 ──────────────────────────────────
$NAS_USER = "wfadmin"
$NAS_IP   = "192.168.100.38"
$VERSION  = "0.7.5.2"   # 배포 시 자동 증가 (pre-test=BUILD↑, test=PATCH↑, production=MINOR↑)

$TARGETS = @{
    "1" = @{ Name="pre-test-lifeart"; Path="/volume1/web/pre-test-lifeart"; URL="https://pre-test-lifeart.lifeart.ai.kr"; Color="Magenta" }
    "2" = @{ Name="test-lifeart";     Path="/volume1/web/test-lifeart";     URL="https://test-lifeart.lifeart.ai.kr";     Color="Yellow"  }
    "3" = @{ Name="production";       Path="/volume1/web/lifeart";          URL="https://www.lifeart.ai.kr";              Color="Green"   }
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
Write-Host "    [1]  pre-test-lifeart  — 비공개 검수용(기본)         (pre-test-lifeart.lifeart.ai.kr)"    -ForegroundColor Magenta
Write-Host "    [2]  test-lifeart      — 고객사 공개용(단계적 공개)  (test-lifeart.lifeart.ai.kr)"     -ForegroundColor Yellow
Write-Host "    [3]  production        — 실 서비스               (www.lifeart.ai.kr)"                  -ForegroundColor Green
Write-Host "    [Q]  취소"                                                    -ForegroundColor Gray
Write-Host ""
if ($Target) {
    $choice = $Target
    Write-Host "  (비대화형 모드 — Target: $Target)" -ForegroundColor DarkGray
} else {
    $choice = Read-Host "  선택 (Enter=1 pre-test)"
    if ([string]::IsNullOrWhiteSpace($choice)) { $choice = "1" }
}

if ($choice -match "^[Qq]$") { Write-Host "`n  취소됨." -ForegroundColor Gray; exit 0 }
if (-not $TARGETS.ContainsKey($choice)) {
    Write-Host "`n  [오류] 잘못된 선택." -ForegroundColor Red; exit 1
}

$T = $TARGETS[$choice]

if ($choice -eq "3") {
    Write-Host ""
    Write-Host "  ⚠️  production 배포 — 실 서비스(www.lifeart.ai.kr)에 즉시 반영됩니다." -ForegroundColor Red
    if (-not $Target) {
        $confirm = Read-Host "  계속하려면 'yes' 입력"
        if ($confirm -ne "yes") { Write-Host "`n  취소됨." -ForegroundColor Gray; exit 0 }
    }
}

# ── 버전 자동 증가 (확인 통과 후) ──────────────────────────────
#   pre-test(1)=BUILD(4번째)↑ · test(2)=PATCH(3번째)↑+BUILD리셋 · production(3)=MINOR(2번째)↑+PATCH·BUILD리셋
#   버전은 "릴리스 횟수" 카운터라 -Day 스테이징 배포에서도 대상별로 증가한다.
#   (콘텐츠는 태그 시점 고정, 버전은 릴리스 시점 기준 → 스테이지 푸터에 주입)
if ($VERSION -match '^(\d+)\.(\d+)\.(\d+)\.(\d+)$') {
    $p = @([int]$Matches[1], [int]$Matches[2], [int]$Matches[3], [int]$Matches[4])
    switch ($choice) {
        "3" { $p[1]++; $p[2] = 0; $p[3] = 0 }   # production: MINOR↑
        "2" { $p[2]++; $p[3] = 0 }              # test: PATCH↑
        default { $p[3]++ }                      # pre-test(1): BUILD↑
    }
    $newVer  = "$($p[0]).$($p[1]).$($p[2]).$($p[3])"
    # deploy.ps1 자기 자신의 $VERSION 갱신 (UTF-8 BOM 유지 — 한글 포함)
    $selfTxt = [System.IO.File]::ReadAllText($PSCommandPath, [System.Text.Encoding]::UTF8)
    $selfTxt = $selfTxt -replace '(\$VERSION\s*=\s*")[\d.]+"', ('${1}' + $newVer + '"')
    [System.IO.File]::WriteAllText($PSCommandPath, $selfTxt, (New-Object System.Text.UTF8Encoding($true)))
    # 일반 배포(비 -Day)만 로컬 공통 푸터를 갱신(정본). -Day 는 스테이지 푸터에만 주입(아래).
    if (-not $Day) {
        $footer = Join-Path $LOCAL_PATH 'assets\footer.html'
        if (Test-Path $footer) {
            $fTxt = [System.IO.File]::ReadAllText($footer, [System.Text.Encoding]::UTF8)
            $fTxt = $fTxt -replace 'v\d+\.\d+\.\d+\.\d+', "v$newVer"
            [System.IO.File]::WriteAllText($footer, $fTxt, [System.Text.Encoding]::UTF8)
        }
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

    # ':/경로' 매직 pathspec = repo 루트 기준(cwd 무관). 아카이브는 lifeart-web 하위만 담김.
    & $gitBash -c "cd '$posixLocal0' && git archive '$tag' -- ':/10.rpa/70.webs/lifeart-web' | tar -x -C '$tempPosix'" 2>&1 | Out-Null

    $SOURCE_PATH = $tempArchiveDir
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
$BUST       = $VERSION   # 캐시버스트 토큰 = 릴리스 버전

# 소스 → 스테이지 복사 후 불필요 폴더 제거 (배포 대상만 남김)
& $gitBash -c "rm -rf '$stagePosix'; mkdir -p '$stagePosix'; cp -r '$srcPosix'/. '$stagePosix'/; cd '$stagePosix'; rm -rf worker supabase tests .git node_modules .wrangler; rm -f deploy.ps1 deploy.log *.bak *.log" 2>&1 | Out-Null

# ── 단계 배포 플래그(-Stage N, 1~5): 배포 사본의 config.js RELEASE_STAGE 만 치환 ──
#   1=소개·상품·제작과정 · 2=+비즈니스·소셜 · 3=+고객지원·결제 · 4=+O&M · 5=+Dev툴킷
#   소스는 항상 5(full) 유지 → pre-test 검수는 전체 공개. test/www 만 -Stage 로 단계 노출.
#   -Stage 미지정 시 소스 기본값(5) 그대로 배포. 값만 바꿔 재배포하면 어느 단계로든 복원(가역).
if ($Stage -ne "") {
    if ($Stage -notmatch '^[1-5]$') {
        Write-Host "  [오류] -Stage 는 1~5 만 허용." -ForegroundColor Red; exit 1
    }
    $cfg = Join-Path $stageWin 'assets\config.js'
    if (Test-Path $cfg) {
        $cTxt = [System.IO.File]::ReadAllText($cfg, [System.Text.Encoding]::UTF8)
        $cTxt = [regex]::Replace($cTxt, 'const RELEASE_STAGE = \d+;\s*/\* deploy:stage \*/',
                                 "const RELEASE_STAGE = $Stage;   /* deploy:stage */")
        [System.IO.File]::WriteAllText($cfg, $cTxt, [System.Text.Encoding]::UTF8)
        Write-Host "  ▶ 단계 배포: RELEASE_STAGE=$Stage (1=기본 2=+비즈/소셜 3=+지원/결제 4=+O&M 5=+Dev)" -ForegroundColor DarkYellow
    } else {
        Write-Host "  [오류] 스테이지 사본에 assets/config.js 가 없습니다." -ForegroundColor Red; exit 1
    }
}
if ($Menus) { Write-Host "  ▶ [안내] -Menus 는 폐지됨(단계는 -Stage 로 관리)." -ForegroundColor DarkGray }

# ── 헤더/푸터 인라인 주입 (링크 이동 시 헤더 깜빡임 FOUC 제거) ──────
#   layout.js 의 fetch 대신 배포 시점에 각 페이지의 자리표시자에 파트셜을 직접 삽입.
#   layout.js 는 이미 채워진 경우 fetch 를 건너뛰고 layout:ready 만 발화한다.
$hdrFile = Join-Path $stageWin 'assets\header.html'
$ftrFile = Join-Path $stageWin 'assets\footer.html'
if ((Test-Path $hdrFile) -and (Test-Path $ftrFile)) {
    $hdr = [System.IO.File]::ReadAllText($hdrFile, [System.Text.Encoding]::UTF8)
    $ftr = [System.IO.File]::ReadAllText($ftrFile, [System.Text.Encoding]::UTF8)
    Get-ChildItem -Path $stageWin -Recurse -File -Filter *.html | ForEach-Object {
        $c = [System.IO.File]::ReadAllText($_.FullName, [System.Text.Encoding]::UTF8)
        if ($c -match '<div id="site-header"></div>' -or $c -match '<div id="site-footer"></div>') {
            $c = $c.Replace('<div id="site-header"></div>', '<div id="site-header">' + $hdr + '</div>')
            $c = $c.Replace('<div id="site-footer"></div>', '<div id="site-footer">' + $ftr + '</div>')
            [System.IO.File]::WriteAllText($_.FullName, $c, [System.Text.Encoding]::UTF8)
        }
    }
    Write-Host "  ▶ 헤더/푸터 인라인 주입 완료 (헤더 깜빡임 제거)" -ForegroundColor DarkGray
}

# 스테이지 처리: (1) 모든 html의 버전 문자열을 릴리스 버전으로 치환
#   — 인라인 푸터(초기 페이지)와 공통 파트셜 footer.html 을 모두 포함
#   (2) 모든 html·layout.js 의 /assets/*.js|css|html 참조에 ?v=$BUST 캐시버스팅
$verRe  = [regex]'v\d+\.\d+\.\d+\.\d+'
$bustRe = [regex]'(/assets/[A-Za-z0-9_./-]+\.(?:js|css|html))'
Get-ChildItem -Path $stageWin -Recurse -File | Where-Object { $_.Extension -eq '.html' -or $_.Name -eq 'layout.js' } | ForEach-Object {
    $c = [System.IO.File]::ReadAllText($_.FullName, [System.Text.Encoding]::UTF8)
    if ($_.Extension -eq '.html') { $c = $verRe.Replace($c, "v$VERSION") }
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
