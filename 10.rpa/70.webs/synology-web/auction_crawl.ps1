# ================================================================
#  auction_crawl.ps1  --  경매지도 데이터 수집 & NAS 업로드
#
#  사용법:
#    1) auction_crawl.bat 더블클릭   (가장 쉬움)
#    2) PowerShell: .\auction_crawl.ps1
#    3) 자동 (Task Scheduler): .\auction_crawl.ps1 -Auto
#
#  사전 조건:
#    - Cloudflare Worker 배포 후 WORKER_URL 환경변수 설정
#    - pip install requests  (playwright 불필요)
# ================================================================
param([switch]$Auto)

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding          = [System.Text.Encoding]::UTF8
chcp 65001 | Out-Null

$SCRIPT_DIR  = $PSScriptRoot
$CRAWLER_DIR = Join-Path $SCRIPT_DIR "auction\crawler"
$PYTHON      = "python"
$TIMESTAMP   = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

Clear-Host
Write-Host ""
Write-Host "  ============================================" -ForegroundColor Cyan
Write-Host "   경매지도 데이터 수집 & NAS 업로드" -ForegroundColor Cyan
Write-Host "   $TIMESTAMP" -ForegroundColor Gray
Write-Host "  ============================================" -ForegroundColor Cyan
Write-Host ""

# Python 확인
if (-not (Get-Command $PYTHON -ErrorAction SilentlyContinue)) {
    Write-Host "  [오류] Python을 찾을 수 없습니다." -ForegroundColor Red
    if (-not $Auto) { Read-Host "  Enter 키로 종료" }
    exit 1
}
$pyVer = & $PYTHON --version 2>&1
Write-Host "  Python: $pyVer" -ForegroundColor DarkGray

# WORKER_URL 확인
$workerUrl = $env:WORKER_URL
if (-not $workerUrl) {
    # config.py 에서 읽기 시도
    $workerUrl = & $PYTHON -c "import sys; sys.path.insert(0,'$CRAWLER_DIR'); from config import WORKER_URL; print(WORKER_URL)" 2>&1
}
if (-not $workerUrl -or $workerUrl -eq "") {
    Write-Host ""
    Write-Host "  [주의] WORKER_URL 이 설정되지 않았습니다." -ForegroundColor Yellow
    Write-Host "         Cloudflare Worker 배포 후 환경변수를 설정하세요." -ForegroundColor Yellow
    Write-Host "         설정 방법:" -ForegroundColor DarkGray
    Write-Host "           [시스템 환경변수] WORKER_URL = https://xxx.workers.dev" -ForegroundColor DarkGray
    Write-Host "           [선택] WORKER_SECRET = 비밀키" -ForegroundColor DarkGray
    Write-Host ""
} else {
    Write-Host "  Worker: $workerUrl" -ForegroundColor DarkGray
}

# 작업 선택
Write-Host "  작업을 선택하세요:" -ForegroundColor White
Write-Host ""
Write-Host "    [1]  법원경매 수집 + JSON + NAS 업로드  (권장)" -ForegroundColor Green
Write-Host "    [2]  JSON 생성 + NAS 업로드  (기존 DB 재사용)" -ForegroundColor Cyan
Write-Host "    [3]  NAS 업로드만  (기존 JSON 재사용)" -ForegroundColor DarkCyan
Write-Host "    [Q]  취소" -ForegroundColor Gray
Write-Host ""

if ($Auto) {
    $choice = "1"
    Write-Host "  (자동 모드 -- [1] 전체 수집)" -ForegroundColor DarkGray
} else {
    $choice = Read-Host "  선택"
}

if ($choice -match "^[Qq]$") { Write-Host "`n  취소됨." -ForegroundColor Gray; exit 0 }
if ($choice -notin @("1","2","3")) { Write-Host "`n  잘못된 선택." -ForegroundColor Red; exit 1 }

Write-Host ""
$startTime = Get-Date

if ($choice -eq "1") {
    Write-Host "  >> [1/2] 법원경매 수집 + JSON 생성 중..." -ForegroundColor Yellow
    Write-Host "           (Cloudflare Worker 경유, 약 1~2분 소요)" -ForegroundColor DarkGray
    $result = & $PYTHON -X utf8 "$CRAWLER_DIR\run.py" --court --upload 2>&1
    $result | ForEach-Object { Write-Host "           $_" -ForegroundColor DarkGray }

    if ($result -match "IP 차단됨|WORKER_URL 미설정") {
        Write-Host ""
        Write-Host "  [실패] 위 오류를 확인하세요." -ForegroundColor Red
        if (-not $Auto) { Read-Host "  Enter 키로 종료" }
        exit 1
    }
} elseif ($choice -eq "2") {
    Write-Host "  >> JSON 생성 + NAS 업로드 중..." -ForegroundColor Yellow
    $result = & $PYTHON -X utf8 "$CRAWLER_DIR\run.py" --upload 2>&1
    $result | ForEach-Object { Write-Host "           $_" -ForegroundColor DarkGray }
} else {
    Write-Host "  >> NAS 업로드 중..." -ForegroundColor Yellow
    $result = & $PYTHON -X utf8 "$CRAWLER_DIR\run.py" --upload 2>&1
    $result | ForEach-Object { Write-Host "           $_" -ForegroundColor DarkGray }
}

# 결과
$jsonPath = Join-Path $SCRIPT_DIR "auction\data\auctions.json"
if (Test-Path $jsonPath) {
    $sizeKB  = [Math]::Round((Get-Item $jsonPath).Length / 1KB, 1)
    $genTime = (Get-Item $jsonPath).LastWriteTime.ToString("HH:mm:ss")
    Write-Host "  JSON: $sizeKB KB (갱신: $genTime)" -ForegroundColor Green
}

if ($result -match "업로드 완료") {
    Write-Host "  NAS 업로드: 완료" -ForegroundColor Green
} elseif ($result -match "업로드 실패") {
    Write-Host "  NAS 업로드 실패 -- SSH/SCP 연결을 확인하세요." -ForegroundColor Red
    if (-not $Auto) { Read-Host "  Enter 키로 종료" }
    exit 1
}

$elapsed = [Math]::Round(((Get-Date) - $startTime).TotalSeconds)
Write-Host ""
Write-Host "  ============================================" -ForegroundColor Green
Write-Host "   완료  (${elapsed}초 소요)" -ForegroundColor Green
Write-Host "   https://auction.worksfree.kr" -ForegroundColor Green
Write-Host "  ============================================" -ForegroundColor Green
Write-Host ""

if (-not $Auto) { Read-Host "  Enter 키로 종료" }