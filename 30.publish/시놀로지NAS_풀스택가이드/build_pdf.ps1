param([switch]$SkipToc, [switch]$Open)
$ErrorActionPreference = "Stop"
$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$MD_FILE = Join-Path $SCRIPT_DIR "NAS웹서비스_구축가이드.md"
$PDF_OUT = Join-Path $SCRIPT_DIR "NAS웹서비스_구축가이드.pdf"
$TEMP_MD = Join-Path $SCRIPT_DIR "_temp_content.md"
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  NAS 풀스택 가이드 PDF 빌드" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "[1/3] 본문 추출 중..." -ForegroundColor Yellow
$raw = [System.IO.File]::ReadAllText($MD_FILE, [System.Text.Encoding]::UTF8)
$sep = "`n---`n`n"
$idx = $raw.IndexOf($sep)
if ($idx -ge 0) { $body = $raw.Substring($idx + $sep.Length) } else { $body = $raw }
[System.IO.File]::WriteAllText($TEMP_MD, $body, [System.Text.Encoding]::UTF8)
Write-Host "   완료 ($([int]($body.Length / 1024)) KB)" -ForegroundColor Green
Write-Host "[2/3] pandoc 변환 중..." -ForegroundColor Yellow
$pandocArgs = @($TEMP_MD, "-o", $PDF_OUT, "--pdf-engine=xelatex",
    "-V", "mainfont=Malgun Gothic", "-V", "monofont=Consolas",
    "-V", "fontsize=11pt", "-V", "geometry:top=2cm,bottom=2cm,left=2.5cm,right=2cm",
    "-V", "linestretch=1.4", "--highlight-style=tango",
    "--from=markdown+raw_html+smart")
if (-not $SkipToc) {
    $pandocArgs += "--toc"; $pandocArgs += "--toc-depth=3"
    $pandocArgs += "-V"; $pandocArgs += "toc-title=목  차"
    Write-Host "   목차 포함 (depth=3)" -ForegroundColor DarkGray
} else { Write-Host "   목차 생략" -ForegroundColor DarkGray }
& pandoc @pandocArgs
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: pandoc 실패 (exit $LASTEXITCODE)" -ForegroundColor Red
    exit 1
}
if (Test-Path $TEMP_MD) { [System.IO.File]::Delete($TEMP_MD) }
Write-Host "[3/3] 완료!" -ForegroundColor Green
Write-Host "  출력: $PDF_OUT" -ForegroundColor Cyan
Write-Host "  크기: $([int]((Get-Item $PDF_OUT).Length / 1024)) KB" -ForegroundColor Cyan
if ($Open) { Start-Process $PDF_OUT }
