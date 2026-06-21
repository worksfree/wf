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

# ── Cover: dark gradient + solid bottom
cover_pdf_path = parts[0]
cover_doc = fitz.open(cover_pdf_path)
cover_page = cover_doc[0]
pw, ph = cover_page.rect.width, cover_page.rect.height
gradient_h = 130
steps = 14
DARK = (4/255, 12/255, 28/255)
for s in range(steps):
    y0 = ph - gradient_h + s * (gradient_h / steps)
    y1 = ph - gradient_h + (s + 1) * (gradient_h / steps)
    t = (s + 1) / steps
    alpha = min(0.96, 0.08 + 0.88 * (t ** 1.1))
    cover_page.draw_rect(fitz.Rect(0, y0, pw, y1), color=None, fill=DARK, fill_opacity=alpha)
cover_page.draw_rect(fitz.Rect(0, ph - 42, pw, ph), color=None, fill=DARK, fill_opacity=1.0)
cover_doc.save(cover_pdf_path, incremental=True, encryption=fitz.PDF_ENCRYPT_KEEP)
cover_doc.close()
print('  cover: dark gradient + solid bottom applied')

# ── Merge
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

# ── TOC 페이지 검출 (섹션번호가 많은 페이지)
page_sn_data = {}
for page_idx in range(SKIP_START, total - SKIP_END):
    page = doc[page_idx]
    sns = []
    for w in page.get_text("words"):
        word = w[4].strip()
        if re.match(r'^\d{1,2}(?:\.\d{1,2}){0,2}$', word):
            parts_n = [int(x) for x in word.split('.')]
            if all(1 <= x <= 25 for x in parts_n):
                sns.append((word, w[3]))
    page_sn_data[page_idx] = sns

toc_pages = []
for page_idx in range(SKIP_START, total - SKIP_END):
    if len(page_sn_data.get(page_idx, [])) > 12:
        toc_pages.append(page_idx)
    elif toc_pages:
        break
print(f'TOC pages: {toc_pages}')

# ── 섹션 위치 수집
section_pages = {}
for page_idx in range(SKIP_START, total - SKIP_END):
    if page_idx in toc_pages:
        continue
    for sn, _ in page_sn_data.get(page_idx, []):
        if sn not in section_pages:
            section_pages[sn] = page_idx - SKIP_START + 1
print(f'sections found: {len(section_pages)}')

# ── TOC 페이지에 페이지번호 오버레이
for toc_idx in toc_pages:
    page = doc[toc_idx]
    pw = page.rect.width
    drawn = set()
    for w in page.get_text("words"):
        word = w[4].strip()
        if re.match(r'^\d{1,2}(?:\.\d{1,2}){0,2}$', word) and word in section_pages:
            x1, y0, x2, y1 = w[0], w[1], w[2], w[3]
            if word not in drawn:
                pg_num = str(section_pages[word])
                page.draw_rect(fitz.Rect(x1 - 1, y0 - 1, x2 + 50, y1 + 1),
                               color=None, fill=(1, 1, 1), fill_opacity=1.0)
                page.insert_text(
                    fitz.Point(pw - 52, y1),
                    pg_num,
                    fontsize=9, color=(0.4, 0.4, 0.4)
                )
                drawn.add(word)
print(f'TOC page numbers overlaid on {len(toc_pages)} page(s)')

# ── 본문 페이지 번호 추가
font_color = (0.45, 0.45, 0.45)
for i, page_idx in enumerate(range(SKIP_START, total - SKIP_END)):
    page = doc[page_idx]
    pw, ph = page.rect.width, page.rect.height
    pg_num = str(i + 1)
    page.insert_text(
        fitz.Point(pw / 2 - 5, ph - 8),
        pg_num,
        fontsize=8, color=font_color
    )
print(f'page numbers added: 1-{guide_count}')

# ── TOC 항목 설정
toc_entries = []
for page_idx in range(SKIP_START, total - SKIP_END):
    if page_idx in toc_pages:
        continue
    page = doc[page_idx]
    blocks = page.get_text("dict")["blocks"]
    for blk in blocks:
        for line in blk.get("lines", []):
            for span in line.get("spans", []):
                txt = span["text"].strip()
                sz  = span["size"]
                if sz >= 11 and re.match(r'^(\d+장\.|부록\s*[A-Z]\.|이 가이드|전체 구성도|사전 준비물)', txt):
                    level = 1 if sz >= 13 else 2
                    toc_entries.append([level, txt[:60], page_idx + 1])
                    break

doc.set_toc(toc_entries)
print(f'PDF TOC: {len(toc_entries)} entries set')

doc.save(tmp_out)
doc.close()
print(f'merged: {total} pages -> {tmp_out}')

script_dir = os.environ.get('NAS_SCRIPT_DIR', '')
if script_dir:
    latest = Path(script_dir) / 'NAS메일서비스_구축가이드.pdf'
    shutil.copy2(tmp_out, str(latest))
    print(f'saved: NAS메일서비스_구축가이드.pdf  ({total} pages)')
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
