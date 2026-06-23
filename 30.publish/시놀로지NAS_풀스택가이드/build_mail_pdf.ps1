param([switch]$Open)
$ErrorActionPreference = "Stop"

$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $SCRIPT_DIR) { $SCRIPT_DIR = $PSScriptRoot }
if (-not $SCRIPT_DIR) { $SCRIPT_DIR = (Get-Location).Path }
$env:NAS_SCRIPT_DIR = $SCRIPT_DIR

$EDGE = "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
$TMP  = "D:\tmp\nas_mail"
$OUT_TMP = "$TMP\mail_out.pdf"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  NAS Mail Guide -- PDF Build" -ForegroundColor Cyan
Write-Host "  Method: HTML->PDF + pymupdf merge" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Script dir: $SCRIPT_DIR" -ForegroundColor DarkGray

if (-not (Test-Path $TMP)) { New-Item -ItemType Directory -Force $TMP | Out-Null }

function ConvertHtmlToPdf($htmlFile, $pdfOut, $label) {
    Write-Host "  [$label] $(Split-Path -Leaf $htmlFile) -> PDF" -ForegroundColor Yellow
    $fileUrl = "file:///" + $htmlFile.Replace('\', '/')
    & $EDGE --headless --disable-gpu --no-sandbox `
            "--print-to-pdf=$pdfOut" "--print-to-pdf-no-header" $fileUrl 2>$null
    Start-Sleep -Seconds 5
    $deadline = (Get-Date).AddSeconds(60)
    $prevSz = -1
    while ((Get-Date) -lt $deadline) {
        Start-Sleep -Seconds 1
        if (Test-Path $pdfOut) {
            $sz = (Get-Item $pdfOut).Length
            if ($sz -gt 1024 -and $sz -eq $prevSz) { break }
            $prevSz = $sz
        }
    }
    if (-not (Test-Path $pdfOut) -or (Get-Item $pdfOut).Length -lt 1024) {
        Write-Host "    ERROR: PDF conversion failed" -ForegroundColor Red; exit 1
    }
    $kb = [int]((Get-Item $pdfOut).Length / 1024)
    Write-Host "    done: $kb KB" -ForegroundColor Green
}

# ── Step 1: Design HTML pages -> individual PDFs ──────────────────
Write-Host ""
Write-Host "[1/3] HTML design pages -> PDF" -ForegroundColor Cyan

Remove-Item "$TMP\01_cover.pdf"    -ErrorAction SilentlyContinue
Remove-Item "$TMP\02_author.pdf"   -ErrorAction SilentlyContinue
Remove-Item "$TMP\03_book.pdf"     -ErrorAction SilentlyContinue
Remove-Item "$TMP\04_copyright.pdf" -ErrorAction SilentlyContinue

ConvertHtmlToPdf "$SCRIPT_DIR\cover_mail.html"       "$TMP\01_cover.pdf"      "cover    1/4"
ConvertHtmlToPdf "$SCRIPT_DIR\author_intro.html"      "$TMP\02_author.pdf"    "author   2/4"
ConvertHtmlToPdf "$SCRIPT_DIR\book_intro_mail.html"   "$TMP\03_book.pdf"      "book     3/4"
ConvertHtmlToPdf "$SCRIPT_DIR\copyright_mail.html"    "$TMP\04_copyright.pdf" "copyright 4/4"

# ── Step 2: Body MD -> HTML -> PDF ───────────────────────────────
Write-Host ""
Write-Host "[2/3] Body MD -> HTML -> PDF" -ForegroundColor Cyan

$guideHtml = "$TMP\guide_body.html"
$guidePdf  = "$TMP\05_guide.pdf"
$cssSrc    = "$SCRIPT_DIR\guide_print.css"

$mdSrcPS = "$SCRIPT_DIR\NAS메일서비스_구축가이드.md"
if (-not (Test-Path $mdSrcPS)) {
    Write-Host "ERROR: NAS메일서비스_구축가이드.md not found in $SCRIPT_DIR" -ForegroundColor Red; exit 1
}
Write-Host "  MD source: $(Split-Path -Leaf $mdSrcPS)" -ForegroundColor DarkGray

$mdCopy = "$TMP\mail_source.md"
Copy-Item -Path $mdSrcPS -Destination $mdCopy -Force

# 본문 추출: 첫 번째 ## 헤딩부터 시작
$pyExtract = "$TMP\extract_mail.py"
$pyCode = @'
import sys, re
from pathlib import Path
src, dst = Path(sys.argv[1]), Path(sys.argv[2])
text = src.read_text(encoding="utf-8")
# 첫 ## 헤딩부터 본문 시작
m = re.search(r'^##\s+', text, re.MULTILINE)
body = text[m.start():] if m else text
dst.write_text(body, encoding="utf-8")
print(f"extracted: {len(body)} chars")
'@
[System.IO.File]::WriteAllText($pyExtract, $pyCode, [System.Text.Encoding]::UTF8)

$bodyMd = "$TMP\mail_body.md"
python $pyExtract $mdCopy $bodyMd
if ($LASTEXITCODE -ne 0) { Write-Host "ERROR: MD extract failed" -ForegroundColor Red; exit 1 }

Write-Host "  pandoc: MD -> HTML..." -ForegroundColor Yellow
$pandocArgs = @(
    $bodyMd,
    "--from=markdown+raw_html+smart+markdown_in_html_blocks",
    "--to=html5",
    "--standalone",
    "--embed-resources",
    "--toc", "--toc-depth=2",
    "--syntax-highlighting=tango",
    "--wrap=none",
    "--metadata", "title=시놀로지 NAS 메일 서버 구축 완전 가이드",
    "-o", $guideHtml
)
if (Test-Path $cssSrc) {
    $pandocArgs += "--css=$cssSrc"
    Write-Host "  guide_print.css applied" -ForegroundColor DarkGray
}
& pandoc @pandocArgs
if ($LASTEXITCODE -ne 0) { Write-Host "  ERROR: pandoc failed" -ForegroundColor Red; exit 1 }
Write-Host "  HTML done" -ForegroundColor Green

# Post-process
$pyPost = "$TMP\postprocess_mail.py"
$pyPostCode = @'
import re, sys
from pathlib import Path
html_path = Path(sys.argv[1])
html = html_path.read_text(encoding="utf-8")

# TOC 한글 제목 주입
toc_kr = '목차'
html = re.sub(
    r'<nav id="TOC"[^>]*>\s*<ul>',
    f'<nav id="TOC" role="doc-toc">\n<h2 id="toc-title">{toc_kr}</h2>\n<ul>',
    html, count=1
)

# 장·부록 h2에만 페이지 구분 삽입
_CH_STYLE = (
    'page-break-before:always;break-before:page;'
    'padding-top:14mm;margin-top:0;'
)
def _chapter_break(m):
    tag, content, close = m.group(1), m.group(2), m.group(3)
    text = re.sub(r'<[^>]+>', '', content)
    if re.search(r'\d+장\.|부록\s*[A-Z]\.', text):
        tag = tag[:-1] + ' style="' + _CH_STYLE + '">'
    return tag + content + close
html = re.sub(r'(<h2[^>]*>)(.*?)(</h2>)', _chapter_break, html, flags=re.DOTALL)

# 첫 컬럼이 좁은 표에 colgroup 주입
def _colgroup(m):
    tbl = m.group(0)
    th_m = re.search(r'<th[^>]*>(.*?)</th>', tbl, re.DOTALL)
    if not th_m:
        return tbl
    first_th = re.sub(r'<[^>]+>', '', th_m.group(1)).strip()
    thead_m = re.search(r'<thead[^>]*>.*?</thead>', tbl, re.DOTALL)
    if not thead_m:
        return tbl
    ncols = len(re.findall(r'<th(?!e)', thead_m.group(0)))
    if first_th == '섹션' and ncols == 2:
        cg = '<colgroup><col style="width:12%"><col style="width:88%"></colgroup>\n'
    elif first_th == '#' and ncols >= 2:
        cg = ('<colgroup><col style="width:8%">'
              + '<col>' * (ncols - 1) + '</colgroup>\n')
    else:
        return tbl
    tbl = re.sub(r'<colgroup>.*?</colgroup>\s*', '', tbl, count=1, flags=re.DOTALL)
    return tbl.replace('<thead>', cg + '<thead>', 1)
html = re.sub(r'<table[^>]*>.*?</table>', _colgroup, html, flags=re.DOTALL)

# @page 여백 오버라이드
html = re.sub(
    r'@page\s*\{\s*size:[^}]+\}',
    '@page { size: 148mm 210mm; margin: 6mm 14mm 6mm 16mm; }',
    html
)
html = html.replace(
    '</style>',
    'h1 { padding-top: 15mm !important; }\n</style>',
    1
)

# MD의 \pagebreak 마커 → CSS 페이지 구분 div
html = re.sub(r'<p>\\pagebreak</p>', '<div class="pagebreak"></div>', html)

html_path.write_text(html, encoding="utf-8")
print("post-process complete")
'@
[System.IO.File]::WriteAllText($pyPost, $pyPostCode, [System.Text.Encoding]::UTF8)
python $pyPost $guideHtml
Write-Host "  post-processed" -ForegroundColor DarkGray

Remove-Item $guidePdf -ErrorAction SilentlyContinue
ConvertHtmlToPdf $guideHtml $guidePdf "body"

# ── Step 3: pymupdf merge ────────────────────────────────────────
Write-Host ""
Write-Host "[3/3] Merging PDFs (pymupdf)..." -ForegroundColor Cyan

$mergePyFile = "$TMP\merge_mail.py"
$mergePyCode = @'
import sys, os, re, fitz, shutil
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')

*parts, tmp_out = sys.argv[1:]

# Cover: solid bottom strip
cover_pdf_path = parts[0]
cover_doc = fitz.open(cover_pdf_path)
cover_page = cover_doc[0]
pw, ph = cover_page.rect.width, cover_page.rect.height
DARK = (4/255, 12/255, 28/255)
cover_page.draw_rect(fitz.Rect(0, ph - 42, pw, ph), color=None, fill=DARK, fill_opacity=1.0)
cover_doc.save(cover_pdf_path, incremental=True, encryption=fitz.PDF_ENCRYPT_KEEP)
cover_doc.close()
print('  cover: dark strip applied')

# Merge
doc = fitz.open()
total = 0
for p in parts:
    src = fitz.open(p)
    cnt = src.page_count
    doc.insert_pdf(src)
    src.close()
    total += cnt
    print(f'  + {Path(p).name}  ({cnt} pages)')

SKIP_START = 3  # cover, author, book
SKIP_END   = 1  # copyright
guide_count = total - SKIP_START - SKIP_END

# Predefined chapter markers for mail guide (pandoc h2 headings)
MAIL_TOC_DEFS = [
    (1, "이 가이드를 읽기 전에"),
    (1, "전체 구성도"),
    (1, "사전 준비물"),
    (1, "1장."),
    (1, "2장."),
    (1, "3장."),
    (1, "4장."),
    (1, "5장."),
    (1, "6장."),
    (1, "7장."),
    (1, "8장."),
    (1, "부록 A."),
    (1, "부록 B."),
    (1, "부록 C."),
    (1, "부록 D."),
]

# TOC page detection: pandoc generates "목차" heading + chapter names on same page
def is_toc_page(page):
    text = page.get_text("text")
    if "목차" in text and sum(1 for k in ["1장", "2장", "3장", "4장", "5장"] if k in text) >= 3:
        return True
    return False

toc_pages = []
for page_idx in range(SKIP_START, total - SKIP_END):
    if is_toc_page(doc[page_idx]):
        toc_pages.append(page_idx)
print(f'TOC pages: {toc_pages}')

# Search each page (top 40%) for predefined chapter markers
# Korean text is rendered as per-character spans — concatenate spans per line
toc_entries = []
found_markers = set()

for page_idx in range(SKIP_START, total - SKIP_END):
    if page_idx in toc_pages:
        continue
    page = doc[page_idx]
    page_h = page.rect.height
    top_limit = page_h * 0.40
    blocks = page.get_text("dict")["blocks"]
    for blk in blocks:
        if blk.get("type") != 0:
            continue
        # only look in top 40% of page
        if blk["bbox"][1] > top_limit:
            continue
        for line in blk.get("lines", []):
            spans = line.get("spans", [])
            if not spans:
                continue
            # Concatenate all spans in this line (handles per-char Korean rendering)
            line_text = "".join(s["text"] for s in spans).strip()
            sz = spans[0]["size"]
            if sz < 9 or not line_text:
                continue
            for level, marker in MAIL_TOC_DEFS:
                if marker not in found_markers and line_text.startswith(marker):
                    toc_entries.append([level, line_text[:80], page_idx + 1])
                    found_markers.add(marker)
                    break

doc.set_toc(toc_entries)
print(f'PDF TOC: {len(toc_entries)} entries set')

# Page numbers on body pages
font_color = (0.45, 0.45, 0.45)
for i, page_idx in enumerate(range(SKIP_START, total - SKIP_END)):
    page = doc[page_idx]
    pw2, ph2 = page.rect.width, page.rect.height
    page.insert_text(
        fitz.Point(pw2 / 2 - 5, ph2 - 8),
        str(i + 1),
        fontsize=8, color=font_color
    )
print(f'page numbers added: 1-{guide_count}')

doc.save(tmp_out)
doc.close()
print(f'merged: {total} pages -> {tmp_out}')

script_dir = os.environ.get('NAS_SCRIPT_DIR', '')
if script_dir:
    latest = Path(script_dir) / 'NAS메일서비스_구축가이드.pdf'
    shutil.copy2(tmp_out, str(latest))
    sz_kb = int(latest.stat().st_size / 1024)
    print(f'saved: NAS메일서비스_구축가이드.pdf  ({total} pages, {sz_kb} KB)')
'@
[System.IO.File]::WriteAllText($mergePyFile, $mergePyCode, [System.Text.Encoding]::UTF8)

python $mergePyFile `
    "$TMP\01_cover.pdf" `
    "$TMP\02_author.pdf" `
    "$TMP\03_book.pdf" `
    "$TMP\05_guide.pdf" `
    "$TMP\04_copyright.pdf" `
    $OUT_TMP
if ($LASTEXITCODE -ne 0) { Write-Host "ERROR: merge failed" -ForegroundColor Red; exit 1 }

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Mail Guide PDF complete!" -ForegroundColor Cyan
Write-Host "  Temp output: $OUT_TMP" -ForegroundColor DarkGray
Write-Host "  Final: $SCRIPT_DIR\NAS메일서비스_구축가이드.pdf" -ForegroundColor Green
$sz = [int]((Get-Item "$SCRIPT_DIR\NAS메일서비스_구축가이드.pdf").Length / 1024)
Write-Host "  Size: $sz KB" -ForegroundColor DarkGray
Write-Host "========================================" -ForegroundColor Cyan

if ($Open) {
    Start-Process "$SCRIPT_DIR\NAS메일서비스_구축가이드.pdf"
}
