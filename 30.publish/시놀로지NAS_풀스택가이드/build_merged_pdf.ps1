param([switch]$Open)
$ErrorActionPreference = "Stop"

# $PSScriptRoot is null in some invocation contexts; use MyInvocation as primary
$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $SCRIPT_DIR) { $SCRIPT_DIR = $PSScriptRoot }
if (-not $SCRIPT_DIR) { $SCRIPT_DIR = (Get-Location).Path }
$env:NAS_SCRIPT_DIR = $SCRIPT_DIR  # Python passes Korean paths via env var

$EDGE = "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
$TMP  = "D:\tmp\nas_trackb"   # ASCII-only path (safe for Python args)
$OUT_TMP = "$TMP\trackb_out.pdf"  # ASCII temp before Korean rename

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  NAS Guide -- Track B PDF Build" -ForegroundColor Cyan
Write-Host "  Method: HTML->PDF + pymupdf merge" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Script dir: $SCRIPT_DIR" -ForegroundColor DarkGray

if (-not (Test-Path $TMP)) { New-Item -ItemType Directory -Force $TMP | Out-Null }

function ConvertHtmlToPdf($htmlFile, $pdfOut, $label) {
    Write-Host "  [$label] $(Split-Path -Leaf $htmlFile) -> PDF" -ForegroundColor Yellow
    $fileUrl = "file:///" + $htmlFile.Replace('\', '/')
    & $EDGE --headless --disable-gpu --no-sandbox `
            "--print-to-pdf=$pdfOut" "--print-to-pdf-no-header" $fileUrl 2>$null
    # Wait min 5s for web fonts to load, then up to 60s for size to stabilize
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

# Delete cached PDFs so we get fresh output
Remove-Item "$TMP\01_cover.pdf"    -ErrorAction SilentlyContinue
Remove-Item "$TMP\02_author.pdf"   -ErrorAction SilentlyContinue
Remove-Item "$TMP\03_book.pdf"     -ErrorAction SilentlyContinue
Remove-Item "$TMP\04_copyright.pdf" -ErrorAction SilentlyContinue

ConvertHtmlToPdf "$SCRIPT_DIR\cover.html"        "$TMP\01_cover.pdf"      "cover    1/4"
ConvertHtmlToPdf "$SCRIPT_DIR\author_intro.html"  "$TMP\02_author.pdf"    "author   2/4"
ConvertHtmlToPdf "$SCRIPT_DIR\book_intro.html"    "$TMP\03_book.pdf"      "book     3/4"
ConvertHtmlToPdf "$SCRIPT_DIR\copyright.html"     "$TMP\04_copyright.pdf" "copyright 4/4"

# ── Step 2: Body MD -> HTML -> PDF ───────────────────────────────
Write-Host ""
Write-Host "[2/3] Body MD -> HTML -> PDF" -ForegroundColor Cyan

$guideHtml = "$TMP\guide_body.html"
$guidePdf  = "$TMP\05_guide.pdf"
$cssSrc    = "$SCRIPT_DIR\guide_print.css"

# Find MD file with ASCII-only wildcard (avoids Korean literal in PS script)
$mdSrcPS = (Get-ChildItem -Path $SCRIPT_DIR -Filter "NAS*.md" | Select-Object -First 1).FullName
if (-not $mdSrcPS) {
    Write-Host "ERROR: NAS*.md not found in $SCRIPT_DIR" -ForegroundColor Red; exit 1
}
Write-Host "  MD source: $(Split-Path -Leaf $mdSrcPS)" -ForegroundColor DarkGray

# Copy Korean-named MD to ASCII temp path
$mdCopy = "$TMP\guide_source.md"
Copy-Item -Path $mdSrcPS -Destination $mdCopy -Force

# Strip YAML frontmatter via Python (all paths ASCII)
$pyExtract = "$TMP\extract_md.py"
$pyCode = @'
import sys
from pathlib import Path
src, dst = Path(sys.argv[1]), Path(sys.argv[2])
text = src.read_text(encoding="utf-8")
sep = "\n---\n\n"
idx = text.find(sep)
body = text[idx + len(sep):] if idx >= 0 else text
dst.write_text(body, encoding="utf-8")
print(f"extracted: {len(body)} chars")
'@
[System.IO.File]::WriteAllText($pyExtract, $pyCode, [System.Text.Encoding]::UTF8)

$bodyMd = "$TMP\guide_body.md"
python $pyExtract $mdCopy $bodyMd
if ($LASTEXITCODE -ne 0) { Write-Host "ERROR: MD extract failed" -ForegroundColor Red; exit 1 }

Write-Host "  pandoc: MD -> HTML..." -ForegroundColor Yellow
$pandocArgs = @(
    $bodyMd,
    "--from=markdown+raw_html+smart+markdown_in_html_blocks",
    "--to=html5",
    "--standalone",
    "--embed-resources",
    "--toc", "--toc-depth=3",
    "--syntax-highlighting=tango",
    "--wrap=none",
    "-o", $guideHtml
)
if (Test-Path $cssSrc) {
    $pandocArgs += "--css=$cssSrc"
    Write-Host "  guide_print.css applied" -ForegroundColor DarkGray
}
& pandoc @pandocArgs
if ($LASTEXITCODE -ne 0) { Write-Host "  ERROR: pandoc failed" -ForegroundColor Red; exit 1 }
Write-Host "  HTML done" -ForegroundColor Green

# Post-process: mermaid code blocks -> div + inject mermaid.js CDN
$pyPost = "$TMP\postprocess.py"
$pyPostCode = @'
import re, sys
from pathlib import Path
html_path = Path(sys.argv[1])
html = html_path.read_text(encoding="utf-8")

# Inject Korean TOC title (pandoc 3.9 does not generate h2#toc-title)
# Using unicode escapes: 목=목 차=차
toc_kr = '목차'
html = re.sub(
    r'<nav id="TOC"[^>]*>\s*<ul>',
    f'<nav id="TOC" role="doc-toc">\n<h2 id="toc-title">{toc_kr}</h2>\n<ul>',
    html, count=1
)

# Replace mermaid code blocks with 3-step setup workflow (no CDN, guaranteed rendering)
BOX_P = 'border:1.5px solid #8E5CE0;border-radius:5px;background:#F0EAFF;padding:8px 8px;text-align:center;font-size:12.5px;font-weight:700;min-width:88px;line-height:1.55;color:#222;'
BOX_B = 'border:1.5px solid #1A9FD4;border-radius:5px;background:#E8F6FB;padding:8px 8px;text-align:center;font-size:12.5px;font-weight:700;min-width:88px;line-height:1.55;color:#222;'
SUB_P = 'font-size:10px;font-weight:400;color:#666;'
ARR   = 'font-size:10px;color:#555;padding:0 4px;white-space:nowrap;'
FLOW_HTML = (
    '<div style="margin:18px 0 12px;font-family:\'Noto Sans KR\',\'Malgun Gothic\',sans-serif;">'

    # 준비① 라벨
    '<div style="font-size:9.5px;font-weight:700;color:#8E5CE0;margin-bottom:5px;">'
    '◆ 준비① — 도메인 &amp; Cloudflare 설정</div>'

    # 준비① 행 (보라)
    '<div style="display:flex;align-items:center;justify-content:center;gap:0;">'
    f'<div style="{BOX_P}">자가 보유 도메인<br><span style="{SUB_P}">가비아</span></div>'
    f'<div style="{ARR}">→ NS위임 →</div>'
    f'<div style="{BOX_P}">네임서버 설정<br><span style="{SUB_P}">Cloudflare DNS</span></div>'
    f'<div style="{ARR}">→ 터널 생성 →</div>'
    f'<div style="{BOX_P}">Cloudflare Tunnel<br><span style="{SUB_P}">도메인 연결</span></div>'
    '</div>'

    # 준비② 라벨
    '<div style="font-size:9.5px;font-weight:700;color:#1A9FD4;margin-top:10px;margin-bottom:5px;">'
    '◆ 준비② — NAS &amp; 웹 콘텐츠 설정</div>'

    # 준비② 행 (파랑)
    '<div style="display:flex;align-items:center;justify-content:center;gap:0;">'
    f'<div style="{BOX_B}">시놀로지 NAS<br><span style="{SUB_P}">DSM 7.x</span></div>'
    f'<div style="{ARR}">→ 웹스테이션 →</div>'
    f'<div style="{BOX_B}">가상 호스트 설정<br><span style="{SUB_P}">웹 스테이션</span></div>'
    f'<div style="{ARR}">→ 업로드 →</div>'
    f'<div style="{BOX_B}">웹 콘텐츠<br><span style="{SUB_P}">HTML\xb7CSS\xb7JS</span></div>'
    '</div>'

    # 수렴 구분선 + 결과
    '<div style="text-align:center;font-size:10.5px;color:#999;margin:9px 0 7px;'
    'border-top:1px solid #e0e0e0;padding-top:7px;">'
    '↓ ① + ② 준비 완료 시 ↓</div>'
    '<div style="display:flex;justify-content:center;">'
    '<div style="border:2px solid #2E7D32;border-radius:7px;background:#E8F5E9;'
    'padding:10px 22px;text-align:center;font-size:13.5px;font-weight:700;color:#1B5E20;line-height:1.5;">'
    '자가 도메인으로 웹 서비스(홈페이지) 구동 가능'
    '</div>'
    '</div>'

    '</div>'
)
html = re.sub(
    r'<pre[^>]*class="[^"]*mermaid[^"]*"[^>]*>\s*<code[^>]*>.*?</code>\s*</pre>',
    FLOW_HTML,
    html, flags=re.DOTALL
)

# Override @page margins: 5mm top/bottom eliminates space for Edge browser headers
html = re.sub(
    r'@page\s*\{\s*size:[^}]+\}',
    '@page { size: 148mm 210mm; margin: 6mm 14mm 6mm 16mm; }',
    html
)
# Compensate h1 padding-top so chapter starts appear ~22mm from page top (5+17=22)
html = html.replace(
    '</style>',
    'h1 { padding-top: 15mm !important; }\n</style>',
    1
)
html_path.write_text(html, encoding="utf-8")
print("post-process: TOC title + mermaid ready")
'@
[System.IO.File]::WriteAllText($pyPost, $pyPostCode, [System.Text.Encoding]::UTF8)
python $pyPost $guideHtml
Write-Host "  mermaid post-processed" -ForegroundColor DarkGray

Remove-Item $guidePdf -ErrorAction SilentlyContinue
ConvertHtmlToPdf $guideHtml $guidePdf "body"

# ── Step 3: pymupdf merge + copy to Korean-named final output ────
Write-Host ""
Write-Host "[3/3] Merging PDFs (pymupdf)..." -ForegroundColor Cyan

$mergePyFile = "$TMP\merge_pdfs.py"
$mergePyCode = @'
import sys, os, re, fitz, shutil
from pathlib import Path
from datetime import datetime
sys.stdout.reconfigure(encoding='utf-8')

*parts, tmp_out = sys.argv[1:]

# ── 0. Cover post-process: draw dark gradient + solid bottom strip
cover_pdf_path = parts[0]
cover_doc = fitz.open(cover_pdf_path)
cover_page = cover_doc[0]
pw, ph = cover_page.rect.width, cover_page.rect.height
# 그라디언트 구역 (상단부 페이드)
gradient_h = 130
steps = 14
DARK = (4/255, 12/255, 28/255)
for s in range(steps):
    y0 = ph - gradient_h + s * (gradient_h / steps)
    y1 = ph - gradient_h + (s + 1) * (gradient_h / steps)
    t = (s + 1) / steps
    alpha = min(0.96, 0.08 + 0.88 * (t ** 1.1))
    cover_page.draw_rect(fitz.Rect(0, y0, pw, y1), color=None, fill=DARK, fill_opacity=alpha)
# 최하단 42pt: 완전 불투명 — 핑크/보라 완전 차단 (텍스트 배경 보장)
cover_page.draw_rect(fitz.Rect(0, ph - 42, pw, ph), color=None, fill=DARK, fill_opacity=1.0)
cover_doc.save(cover_pdf_path, incremental=True, encryption=fitz.PDF_ENCRYPT_KEEP)
cover_doc.close()
print('  cover: dark gradient + solid bottom applied')

# ── 1. Merge PDFs ────────────────────────────────────────────────────
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

# ── 2. Collect section-number words per guide page ────────────────────
page_sn_data = {}
for page_idx in range(SKIP_START, total - SKIP_END):
    page = doc[page_idx]
    sns = []
    for w in page.get_text("words"):
        word = w[4].strip()
        if re.match(r'^\d{1,2}(?:\.\d{1,2}){0,2}$', word):
            parts_n = [int(x) for x in word.split('.')]
            if all(1 <= x <= 25 for x in parts_n):
                sns.append((word, w[3]))  # (section_num, y_bottom)
    page_sn_data[page_idx] = sns

# ── 3. Identify TOC pages (many section numbers = TOC) ───────────────
toc_pages = []
for page_idx in range(SKIP_START, total - SKIP_END):
    if len(page_sn_data.get(page_idx, [])) > 12:
        toc_pages.append(page_idx)
    elif toc_pages:
        break
print(f'TOC pages (merged idx): {toc_pages}  guide pp {[i-SKIP_START+1 for i in toc_pages]}')

# ── 4. Section positions from body pages ─────────────────────────────
section_pages = {}
for page_idx in range(SKIP_START, total - SKIP_END):
    if page_idx in toc_pages:
        continue
    for sn, _ in page_sn_data.get(page_idx, []):
        if sn not in section_pages:
            section_pages[sn] = page_idx - SKIP_START + 1  # 1-indexed guide page
print(f'sections found: {len(section_pages)}')

# ── 5. Overlay page numbers on TOC pages (right-aligned) ─────────────
for toc_idx in toc_pages:
    page = doc[toc_idx]
    pw = page.rect.width
    drawn = set()
    for w in page.get_text("words"):
        word = w[4].strip()
        if word in section_pages and word not in drawn:
            pg_str = str(section_pages[word])
            tw = fitz.get_text_length(pg_str, fontname="helv", fontsize=7.5)
            page.insert_text(
                fitz.Point(pw - 12 - tw, w[3]),
                pg_str, fontname="helv", fontsize=7.5,
                color=(0.35, 0.35, 0.35)
            )
            drawn.add(word)
print(f'TOC page numbers overlaid on {len(toc_pages)} page(s)')

# ── 6. Add centered page numbers to all guide pages ───────────────────
for i in range(total):
    if i < SKIP_START or i >= total - SKIP_END:
        continue
    page_num = i - SKIP_START + 1
    page = doc[i]
    pw = page.rect.width
    ph = page.rect.height
    txt = f'{page_num}/{guide_count}'
    tw = fitz.get_text_length(txt, fontname="helv", fontsize=7.5)
    # Erase bottom strip (6mm CSS margin + page number zone)
    page.draw_rect(fitz.Rect(0, ph - 15, pw, ph), color=(1,1,1), fill=(1,1,1))
    page.insert_text(
        fitz.Point((pw - tw) / 2, ph - 7), txt,
        fontname="helv", fontsize=7.5,
        color=(0.45, 0.45, 0.45)
    )
print(f'page numbers added: 1-{guide_count}')

# ── 6.5 PDF metadata TOC (bookmarks) ─────────────────────────────────
# Search body pages for chapter heading markers; skip first body page (TOC table)
TOC_DEFS = [
    (1, "이 가이드를 읽기 전에",                                    "이 가이드를 읽기 전에"),
    (2, "전체 구성도",                                                               "전체 구성도 —"),
    (2, "사전 준비물",                                                               "사전 준비물"),
    (1, "1장. 가비아 — 도메인 구입 및 네임서버 변경",  "1장."),
    (1, "2장. Cloudflare — 계정 설정 및 도메인 등록",  "2장."),
    (1, "3장. Synology NAS — DSM 7.x 웹 서비스 설정",                  "3장."),
    (1, "4장. Cloudflare Tunnel — 공유기 설정 없이 NAS 연결","4장."),
    (1, "5장. 서브도메인 DNS 설정",                                      "5장."),
    (1, "6장. Cloudflare Worker — 외부 API 호출",                               "6장."),
    (1, "7장. Supabase — 회원 로그인 시스템 구축",     "7장."),
    (1, "8장. Supabase 데이터베이스 — 회원 정보·결제·크레딧 저장", "8장."),
    (1, "9장. 온라인 결제 연동 — 토스페이먼츠 (국내)",  "9장."),
    (1, "10장. 웹사이트 코드와 Supabase 연결",                   "10장."),
    (1, "11장. 배포 자동화 스크립트 (Windows PowerShell)",       "11장."),
    (1, "12장. 역할 기반 접근 제어 (RBAC)",                          "12장."),
    (1, "13장. 테스트 환경 구축 — Playwright + Supabase 분리", "13장."),
    (1, "부록 A. 전체 설정 순서 요약",                           "부록 A."),
    (1, "부록 B. 트러블슈팅",                                               "부록 B."),
    (1, "부록 C. 포트 구성 참고표",                                  "부록 C."),
    (1, "부록 D. 파일 위치 참고 (WorksFree Hub 기준)",            "부록 D."),
]
found_toc = {}
for i in range(SKIP_START + 1, total - SKIP_END):
    try:
        pg_text = doc[i].get_text("text")
    except Exception:
        continue
    for lvl, title, marker in TOC_DEFS:
        if title not in found_toc and marker in pg_text:
            found_toc[title] = i + 1  # 1-based PDF page
pdf_toc = [[lvl, title, found_toc[title]] for lvl, title, _ in TOC_DEFS if title in found_toc]
for entry in pdf_toc:
    print(f'  TOC[{entry[0]}] p{entry[2]}: {entry[1]}')
not_found = [title for _, title, _ in TOC_DEFS if title not in found_toc]
if not_found:
    print(f'  TOC NOT FOUND: {not_found}')
if pdf_toc:
    doc.set_toc(pdf_toc)
    print(f'PDF TOC: {len(pdf_toc)} entries set')

# ── 7. Save ──────────────────────────────────────────────────────────
doc.save(tmp_out)
doc.close()
print(f'merged: {total} pages -> {tmp_out}')

script_dir = os.environ.get('NAS_SCRIPT_DIR', '')
if script_dir:
    ts = datetime.now().strftime('%y%m%d%H%M')
    final = Path(script_dir) / f'NAS웹서비스_통합_{ts}.pdf'
    shutil.copy2(tmp_out, str(final))
    latest = Path(script_dir) / 'NAS웹서비스_통합.pdf'
    shutil.copy2(tmp_out, str(latest))
    print(f'saved: NAS웹서비스_통합_{ts}.pdf  ({total} pages)')
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

$kb = [int]((Get-Item $OUT_TMP).Length / 1024)
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  Track B complete!" -ForegroundColor Green
Write-Host "  Temp output: $OUT_TMP" -ForegroundColor Cyan
Write-Host "  Final (Korean name) copied to script dir" -ForegroundColor Cyan
Write-Host "  Size: $kb KB" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Green

if ($Open) { Start-Process $OUT_TMP }
