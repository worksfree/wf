#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
경영지도사 예시답안 통합 스크립트 v2 (다중 PDF 엔진 지원)

사용법:
    python merge_qqaa2.py <회차|all> --date <YYYY-MM-DD> [옵션]

옵션:
    --pdf-engine <engine> : PDF 생성 엔진을 선택합니다.
        - w, l : playwright (디자인/레이아웃 최적화, 북마크 없음, playwright 설치 필요)
                 ('l'은 legacy 호환용 옵션이며 'w'와 동일하게 동작합니다)
        - d    : pandoc (기본, 북마크 자동 생성, pandoc/latex 설치 필요)
        - wd : pandoc-hybrid (북마크 생성 + 내부 링크 보존)
    --init-toc            : 목차.md 초안 생성

예시:
    # 40회, 2026-04-10 발행일, playwright로 PDF 생성
    python merge_qqaa2.py 40 --date 2026-04-10 --pdf-engine w

    # 39회, 2026-04-10 발행일, pandoc으로 북마크 포함 PDF 생성
    python merge_qqaa2.py 39 --date 2026-04-10 --pdf-engine d

    # 모든 회차, 2026-04-10 발행일, pandoc 하이브리드 모드로 PDF 생성
    python merge_qqaa2.py all --date 2026-04-10 --pdf-engine wd
"""

import os
import sys
import io
import re
import json
import asyncio
import subprocess
from pathlib import Path
from datetime import datetime

try:
    import markdown
    MARKDOWN_AVAILABLE = True
except ImportError:
    MARKDOWN_AVAILABLE = False

try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

# Windows 콘솔 인코딩 설정
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 경로 설정
BASE_DIR = Path(r"D:\drive_files\10.worksfree\30.publish\cmc")
ANSWERS_DIR = BASE_DIR / "30.예시답안"
QUESTIONS_DIR = BASE_DIR / "20.기출문제"
OUTPUT_DIR = BASE_DIR / "40.출판물" / "개별회차"
TEMPLATE_DIR = BASE_DIR / "40.출판물" / "서식"

# 과목 순서
SUBJECTS = ["생산관리", "품질경영", "경영과학"]


def question_total_points(question_num: int) -> int:
    """대문항 총점 반환: 1~2번 30점, 3~6번 10점"""
    return 30 if question_num in (1, 2) else 10


def extract_keyword_from_title(title: str) -> str:
    """제목에서 핵심 키워드만 추출 (문장형 → 키워드형)"""
    title = re.sub(r'\s*\(\d+점\)\s*$', '', title).strip()
    title = re.sub(r'\s*다음\s*물음에\s*답하시오\.?\s*', '', title).strip()

    if ' - ' in title:
        parts = title.split(' - ', 1)
        keyword_part = parts[0].strip()
        subtitle_part = parts[1].strip() if len(parts) > 1 else ""
        keyword_clean = re.sub(r'\s*\([A-Za-z\s,]+\)\s*', '', keyword_part).strip()
        if len(keyword_part) <= 15 and len(subtitle_part) <= 20:
            return f"{keyword_part} - {subtitle_part}"
        return keyword_clean if keyword_clean else keyword_part

    match = re.match(r'^(.+?)\s*(?:에\s*관하여|에\s*대하여|와\s*관련하여)', title)
    if match:
        return match.group(1).strip()

    keywords_map = [
        (r'입지선정|입지\s*선정|중심모형|요인평점법', '입지선정'),
        (r'작업\s*순서|납기지연|EDD|긴급률|CR|최소여유시간|일정계획|우선순위\s*규칙', '작업일정계획(우선순위규칙)'),
        (r'EOQ|경제적\s*주문량', '경제적 주문량(EOQ)'),
        (r'EPQ|경제적\s*생산량', '경제적 생산량(EPQ)'),
        (r'MRP|자재소요계획', '자재소요계획(MRP)'),
        (r'재고의\s*목적|재고의\s*유형|재고\s*유형|안전재고', '재고관리'),
        (r'예측생산|make-to-stock|주문생산|make-to-order|MTS|MTO', '생산전략(MTS/MTO)'),
        (r'공급사슬|SCM|협력\s*전략|VMI|CPFR', '공급사슬관리'),
        (r'아웃소싱|외주', '아웃소싱'),
        (r'생산능력|capacity', '생산능력'),
        (r'TOC|제약이론|병목', '제약이론(TOC)'),
        (r'생산성|물적생산성|가치생산성|부가가치생산성|총요소생산성|종합생산성', '생산성'),
        (r'설비배치|공정별\s*배치|제품별\s*배치|셀룰러\s*배치|배치유형|레이아웃', '설비배치'),
        (r'JIT|just-in-time|적시생산|도요타|칸반|간판|린생산|Lean', 'JIT(적시생산시스템)'),
        (r'관리도|control\s*chart|x-bar|R관리도|p관리도', '관리도'),
        (r'품질비용|품질코스트|Q-cost|예방비용|평가비용|실패비용', '품질비용'),
        (r'신뢰성|고장률|MTBF|MTTF|신뢰도함수', '신뢰성'),
        (r'MSA|측정시스템', '측정시스템(MSA)'),
        (r'실험계획|분산분석|ANOVA|요인배치', '실험계획법'),
        (r'제조물책임|PL법', '제조물책임법'),
        (r'표준화', '표준화'),
        (r'ISO\s*9000|품질경영시스템', 'ISO 9000'),
        (r'다구찌|품질손실함수|손실함수', '다구찌 품질손실함수'),
        (r'6시그마|식스시그마|DMAIC', '6시그마'),
        (r'TQM|전사적\s*품질', 'TQM'),
        (r'QFD|품질기능전개|품질의\s*집|HOQ', '품질기능전개(QFD)'),
        (r'말콤볼드리지|볼드리지|MBNQA', '말콤볼드리지'),
        (r'샘플링|표본추출|층화추출|집락추출|계통추출', '샘플링'),
        (r'선형계획|LP|심플렉스|쌍대|도해법', '선형계획법'),
        (r'수송문제|운송문제|북서코너|VAM|보겔추정|수송비용|수송계획', '수송문제'),
        (r'할당문제|헝가리안|헝가리법|Hungarian|작업.*할당|할당.*기계', '할당문제'),
        (r'마코프|Markov|전이확률', '마코프 체인'),
        (r'대기행렬|큐잉|M/M/1|대기시간', '대기행렬이론'),
        (r'PERT|CPM|네트워크|주공정|크리티컬|프로젝트.*활동|활동.*프로젝트', 'PERT/CPM'),
        (r'손익분기|BEP|break-even', '손익분기점 분석'),
        (r'의사결정|의사결정나무|기대값|EMV|불확실성|미니맥스|minimax|기대화폐|완전정보|후회표', '의사결정론'),
        (r'게임이론|영합게임|내쉬균형|게임값|game\s*value|시장점유율.*전략', '게임이론'),
        (r'시뮬레이션|몬테카를로|Monte\s*Carlo|난수', '시뮬레이션'),
        (r'AHP|계층분석', 'AHP'),
        (r'정수계획|혼합정수|MIP', '정수계획법'),
        (r'동적계획|DP', '동적계획법'),
        (r'목표계획', '목표계획법'),
        (r'예측|지수평활|이동평균|회귀분석|시계열', '수요예측'),
    ]

    for pattern, keyword in keywords_map:
        if re.search(pattern, title, re.IGNORECASE):
            return keyword

    if len(title) <= 30:
        return title

    return f"[편집필요] {title[:20]}..."


def load_toc_titles(session: int) -> dict:
    """목차.md 파일에서 제목 로드"""
    toc_file = ANSWERS_DIR / f"{session}회" / "목차.md"
    if not toc_file.exists():
        return {}

    toc_data = {}
    current_subject = None
    with open(toc_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            subject_match = re.match(r'^##\s*\[\d+회\s+(.+?)\s*목차\]', line)
            if subject_match:
                current_subject = subject_match.group(1)
                if current_subject not in toc_data:
                    toc_data[current_subject] = {}
                continue

            item_match = re.match(r'^-\s*\[\[문제(\d+)\]\s*(.+?)\]\(#(.+?)\)', line)
            if item_match and current_subject:
                q_num = item_match.group(1)
                title = item_match.group(2).strip()
                link = f"#{item_match.group(3)}"
                toc_data[current_subject][q_num] = {"title": title, "link": link}
    return toc_data


def get_question_title(session: int, subject: str, question_num: int, toc_titles: dict) -> str:
    """목차용 제목 반환"""
    if subject in toc_titles and str(question_num) in toc_titles[subject]:
        entry = toc_titles[subject][str(question_num)]
        return entry.get("title", f"문제{question_num}")

    question_file = QUESTIONS_DIR / f"{session}회" / subject / f"문제{question_num}.md"
    if not question_file.exists():
        return f"문제{question_num}"

    with open(question_file, "r", encoding="utf-8") as f:
        content = f.read()

    match = re.search(r'###\s*【문제\s*\d+】\s*(.+?)(?:\n|$)', content)
    if match:
        raw_title = match.group(1).strip()
        return extract_keyword_from_title(raw_title)
    return f"문제{question_num}"


def generate_toc_template(session: int) -> bool:
    """목차.md 초안 생성"""
    session_dir = ANSWERS_DIR / f"{session}회"
    toc_file = session_dir / "목차.md"
    if not session_dir.exists():
        print(f"오류: {session}회 폴더가 존재하지 않습니다.")
        return False

    lines = [f'# <div align="center"> {session}회 목차 </div>', ""]
    for subject in SUBJECTS:
        lines.append(f"## [{session}회 {subject} 목차](#{session}회-{subject})")
        for q_num in range(1, 7):
            anchor = f"{session}회-{subject}-문제-{q_num}"
            keyword = get_question_title(session, subject, q_num, {})
            lines.append(f"- [[문제{q_num}] {keyword}](#{anchor})")
        lines.append("")

    with open(toc_file, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"  목차 템플릿 생성: {toc_file}")
    return True


CSS_STYLE = """<style>
body  { margin-left: 40px; margin-right: 40px; padding: 20px; font-size: 12pt; line-height: 150%; }
h1    { font-size: 16pt; text-align: center; color: black; border-bottom: 6px solid #333; padding-bottom: 10px; }
h2    { font-size: 14pt; text-align: left; border-left: 4px solid #0d47a1; padding-left: 10px; }
h3    { font-size: 13pt; text-align: left; color:rgb(37, 37, 37); border-left: 4px solid green; padding-left: 10px; }
table { margin-left :auto; margin-right:auto; border: 1px solid; width: 100%; }
th    { text-align: center; border: 1px solid; background-color: #D3D3D3;}
td    { text-align: center; border: 1px solid; }
.qa-pair, table, pre, figure, blockquote { page-break-inside: avoid; }
h2, h3 { break-after: avoid; page-break-after: avoid; }
.nav-bar { display: flex; justify-content: space-between; margin-bottom: 0.6em; padding-bottom: 0.4em; border-bottom: 1px solid #ccc; font-size: 10pt; page-break-inside: avoid; page-break-after: avoid; }
img { page-break-inside: avoid; max-width: 100%; }
</style>
<script type="module">
  import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@9/dist/mermaid.esm.min.mjs';
  mermaid.initialize({ startOnLoad: true });
</script>
"""

MATHJAX_SCRIPT = """
<script>
MathJax = {
    tex: { inlineMath: [['$', '$']], displayMath: [['$$', '$$']], processEscapes: true },
    options: { skipHtmlTags: ['script', 'noscript', 'style', 'textarea', 'pre'] }
};
</script>
<script type="text/javascript" id="MathJax-script" async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-chtml.js"></script>
"""

HTML_TEMPLATE = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>{title}</title>
<style>
    @page {{ size: A4; margin: 20mm 15mm 20mm 15mm; }}
    @media print {{ .page {{ page-break-after: always; }} }}
</style></head><body>{content}</body></html>
"""

def protect_math_blocks(content: str) -> tuple[str, dict]:
    """수식 블록을 마크다운 처리 전에 보호"""
    placeholders = {}
    counter = [0]
    def replace(match, prefix):
        key = f"__{prefix}_{counter[0]}__"
        placeholders[key] = match.group(0)
        counter[0] += 1
        return key
    content = re.sub(r'\$\$[\s\S]*?\$\$', lambda m: replace(m, "MATH_BLOCK"), content)
    content = re.sub(r'\$[^\$\n]+\$', lambda m: replace(m, "MATH_INLINE"), content)
    return content, placeholders

def restore_math_blocks(content: str, placeholders: dict) -> str:
    """보호된 수식 블록 복원"""
    for key, value in placeholders.items():
        content = content.replace(key, value)
    return content

def convert_md_to_html_for_playwright(md_content: str, base_path: Path) -> str:
    """Playwright용 MD to HTML 변환 (이미지 경로 처리 포함)"""
    if not MARKDOWN_AVAILABLE: return md_content
    md_content, math_placeholders = protect_math_blocks(md_content)
    def fix_image_path(match):
        src = match.group(1)
        if src.startswith('../../'):
            abs_path = (base_path / src).resolve()
            return f'src="file:///{str(abs_path).replace(chr(92), "/")}"'
        return match.group(0)
    md_content = re.sub(r'src="([^"]+)"', fix_image_path, md_content)
    html_body = markdown.markdown(md_content, extensions=['tables', 'fenced_code'])
    html_body = restore_math_blocks(html_body, math_placeholders)
    return html_body

async def generate_pdf_playwright(html_content: str, pdf_path: Path) -> bool:
    """Playwright를 사용하여 HTML을 PDF로 변환"""
    if not PLAYWRIGHT_AVAILABLE:
        print("  오류: playwright가 설치되지 않았습니다. (pip install playwright && playwright install chromium)")
        return False
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            await page.set_content(html_content, wait_until='networkidle')
            try:
                await page.wait_for_function("typeof MathJax !== 'undefined' && MathJax.typesetPromise !== undefined", timeout=10000)
                await page.evaluate("MathJax.typesetPromise()")
            except Exception:
                await page.wait_for_timeout(3000)
            await page.pdf(path=str(pdf_path), format='A4', margin={'top': '20mm', 'bottom': '20mm', 'left': '15mm', 'right': '15mm'}, print_background=True)
            await browser.close()
            return True
    except Exception as e:
        print(f"  Playwright PDF 변환 오류: {e}")
        return False

def generate_pdf_pandoc(md_file: Path, pdf_file: Path) -> bool:
    """Pandoc을 사용하여 MD를 PDF로 변환"""
    cmd = [
        'pandoc', str(md_file), '-o', str(pdf_file),
        '--pdf-engine=xelatex',
        '-V', 'documentclass=article', '-V', 'papersize=a4',
        '-V', 'geometry:top=2.5cm,bottom=2.5cm,left=2cm,right=2cm',
        '-V', 'mainfont=Malgun Gothic', '-V', 'monofont=Malgun Gothic',
        '-V', 'fontsize=11pt', '-V', 'lang=ko', '-V', 'linestretch=1.3',
        '-V', 'toc-title=목 차', '--toc', '--toc-depth=3',
        f'--template={TEMPLATE_DIR / "custom_template.latex"}', # 사용자 정의 LaTeX 템플릿 사용
        '-V', 'toc=false', # 북마크는 생성하되, 본문에는 목차를 넣지 않음 (구버전 pandoc 호환)
        '--from=markdown+smart+autolink_bare_uris+tex_math_dollars+raw_html+markdown_in_html_blocks+native_divs+native_spans+fenced_divs+bracketed_spans'
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
        if result.returncode == 0:
            return True
        else:
            print(f"  Pandoc PDF 생성 실패:\n{result.stderr}")
            return False
    except FileNotFoundError:
        print("  오류: 'pandoc' 또는 'xelatex'를 찾을 수 없습니다. Pandoc과 MiKTeX(또는 TeX Live)가 설치 및 PATH에 등록되었는지 확인하세요.")
        return False
    except Exception as e:
        print(f"  Pandoc PDF 생성 오류: {e}")
        return False

def run_pdf_generation(md_file: Path, pdf_file: Path, engine: str) -> bool:
    """지정된 엔진으로 PDF 생성 실행"""
    print(f"  PDF 생성 중 ({engine} 엔진): {pdf_file.name}")
    success = False
    if engine in ['w', 'l']:
        with open(md_file, 'r', encoding='utf-8') as f:
            md_content = f.read()
        html_body = convert_md_to_html_for_playwright(md_content, md_file.parent)
        html_content = HTML_TEMPLATE.format(title=md_file.stem, content=html_body)
        if PLAYWRIGHT_AVAILABLE:
            success = asyncio.run(generate_pdf_playwright(html_content, pdf_file))
        else:
            print("\n  [오류] Playwright 엔진을 사용하려면 라이브러리 설치가 필요합니다.")
            print("  명령어: pip install playwright && playwright install chromium")
    elif engine in ['d', 'wd']:
        success = generate_pdf_pandoc(md_file, pdf_file)

    if success:
        print(f"  PDF 완료: {pdf_file} ({pdf_file.stat().st_size:,} bytes)")
    return success

def get_available_sessions():
    """사용 가능한 회차 목록 조회"""
    sessions = []
    if ANSWERS_DIR.exists():
        for item in ANSWERS_DIR.iterdir():
            if item.is_dir() and item.name.endswith("회"):
                session_num = item.name.replace("회", "")
                if session_num.isdigit():
                    sessions.append(int(session_num))
    return sorted(sessions)

def get_res_path(session: int) -> str:
    """회차별 리소스 경로 반환 (출력 파일 기준 상대 경로)"""
    return f"../../30.예시답안/{session}회/res"

def convert_image_paths(content: str, session: int, pdf_engine: str) -> str:
    """이미지 경로 변환"""
    if pdf_engine in ['d', 'wd']: # Pandoc
        answer_res_dir = ANSWERS_DIR / f"{session}회" / "res"
        question_res_dir = QUESTIONS_DIR / f"{session}회" / "res"
        def get_abs_path(src):
            filename = src.replace('./res/', '').replace('res/', '')
            for base_dir in [answer_res_dir, question_res_dir]:
                abs_path = base_dir / filename
                if abs_path.exists():
                    return str(abs_path).replace('\\', '/')
            return src
        def replace_img(match):
            alt, src = match.group(1), match.group(2)
            return f'![{alt}]({get_abs_path(src)})'
        content = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', replace_img, content)
        content = re.sub(r'<img src="([^"]+)"[^>]*>', lambda m: f"![]({get_abs_path(m.group(1))})", content)
    else: # Playwright
        res_path = get_res_path(session)
        content = re.sub(r'src="\.\/res\/', f'src="{res_path}/', content)
        content = re.sub(r'src="\.\.\/res\/', f'src="{res_path}/', content)
    return content

def read_source_file(file_path: Path, session: int, pdf_engine: str) -> str:
    """소스 파일 읽기 및 전처리"""
    if not file_path.exists():
        print(f"  경고: {file_path} 파일을 찾을 수 없습니다.")
        return None

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read().strip()

    content = convert_image_paths(content, session, pdf_engine)
    content = re.sub(r'^## \d+회 .+ (문제|예시답안).*\n?', '', content)
    content = re.sub(r'\[(문제|목차) 바로가기\]\([^)]+\)\s*\n?', '', content)
    content = re.sub(r'[\s\n]*-{3,}[\s\n]*(<div class="page"></div>|<!--\s*pagebreak\s*-->)[\s\n]*(-{3,})?[\s\n]*$', '', content)
    content = re.sub(r'[\s\n]*-{3,}[\s\n]*$', '', content)

    pagebreak_marker = "\\newpage" if pdf_engine in ['d', 'wd'] else '<div class="page"></div>'
    content = content.replace('<!-- pagebreak -->', pagebreak_marker)

    return content

def read_template_file(template_name: str) -> str:
    """서식 파일 읽기"""
    template_file = TEMPLATE_DIR / template_name
    if not template_file.exists():
        print(f"  경고: {template_file} 파일을 찾을 수 없습니다.")
        return ""
    with open(template_file, "r", encoding="utf-8") as f:
        return f.read().strip()

def create_merged_content(session: int, publication_date: str, pdf_engine: str) -> str:
    """통합 마크다운 내용 생성"""
    lines = []
    pagebreak = "\\newpage" if pdf_engine in ['d', 'wd'] else '<div class="page"></div>'

    # 1. 스타일 및 표지
    if pdf_engine in ['w', 'l']:
        lines.append(CSS_STYLE)
        lines.append(f'<img src="../../40.출판물/서식/표지_{session}.jpg">')
    else: # pandoc (d, wd)
        # pandoc은 템플릿에서 스타일을 처리하므로 CSS_STYLE 불필요
        lines.append(f'# 제{session}회 경영지도사 2차 실기시험')
        lines.append(f'![표지](../../40.출판물/서식/표지_{session}.jpg){width=100%}') # pandoc용 이미지 삽입
        lines.append(f'# 생산관리분야 문제 및 예시답안')
    lines.extend(["", pagebreak, ""])

    # 2. 저자소개 및 교재소개
    author_intro = read_template_file("저자소개.md")
    if author_intro:
        if pdf_engine == 'w':
            qr_image_path = TEMPLATE_DIR / "worksfree.com-QR.png"
            author_intro = author_intro.replace('src="./worksfree.com-QR.png"', f'src="file:///{str(qr_image_path).replace("\\", "/")}"')
        else:
            author_intro = re.sub(r'<img[^>]+>', '', author_intro) # pandoc에서는 이미지 제거
        lines.append(author_intro)
    lines.extend(["", pagebreak, ""])

    # 3. 목차 생성
    toc_titles = load_toc_titles(session)
    if pdf_engine in ['w', 'l', 'wd']: # pandoc (d, wd)도 본문 목차는 직접 생성
        lines.append(f'# <div align="center"> {session}회 목차 </div>')
        for subject in SUBJECTS:
            subject_anchor = f"#{session}회-{subject}"
            if pdf_engine == 'wd':
                subject_anchor += f"{{#{session}회-{subject}}}"
            lines.append(f"## [{session}회 {subject} 목차]({subject_anchor})")
            for i in range(1, 7):
                anchor = f"#{session}회-{subject}-문제-{i}"
                title = get_question_title(session, subject, i, toc_titles)
                lines.append(f"- [[문제{i}] {title}](#{anchor})")
    lines.extend(["", pagebreak, ""])

    # 4. 본문 (문제 -> 답안 순)
    for subject in SUBJECTS:
        # 문제 섹션
        q_section_anchor = f"{{{f'#{session}회-{subject}'}}}" if pdf_engine == 'wd' else ''
        lines.append(f"# {session}회 {subject} 문제 {q_section_anchor}")
        lines.append("")
        for q_num in range(1, 7):
            q_anchor = f"{{{f'#{session}회-{subject}-문제-{q_num}'}}}" if pdf_engine == 'wd' else ''
            lines.append(f"## {session}회 {subject} 문제 {q_num} {q_anchor}")
            
            q_path = QUESTIONS_DIR / f"{session}회" / subject / f"문제{q_num}.md"
            q_content = read_source_file(q_path, session, pdf_engine)
            pb_after_nav = False
            if q_content:
                if q_content.endswith(pagebreak):
                    q_content = q_content[:-len(pagebreak)].rstrip()
                    pb_after_nav = True
                lines.append(f"<!-- SRC:{subject}/문제{q_num}.md -->")
                lines.append(q_content)
                lines.append(f"<!-- /SRC:{subject}/문제{q_num}.md -->")
            
            lines.append("")
            answer_total = question_total_points(q_num)
            ans_anchor = f"#{session}회-{subject}-문제-{q_num}-예시답안-{answer_total}점"
            if pdf_engine == 'w':
                lines.append(f'<div class="nav-bar"><a href="{ans_anchor}">예시답안 바로가기</a><a href="{subject_anchor}">목차 바로가기</a></div>')
            else:
                lines.append(f'[예시답안 바로가기]({ans_anchor})')
            lines.append("")
            if pb_after_nav: lines.extend([pagebreak, ""])

        lines.extend([pagebreak, ""])

        # 예시답안 섹션
        lines.append(f"# {session}회 {subject} 예시답안")
        lines.append("")
        for a_num in range(1, 7):
            answer_total = question_total_points(a_num)
            ans_anchor_id = f"{{{f'#{session}회-{subject}-문제-{a_num}-예시답안-{answer_total}점'}}}" if pdf_engine == 'wd' else ''
            lines.append(f"## {session}회 {subject} 문제 {a_num} 예시답안 ({answer_total}점) {ans_anchor_id}")
            
            a_path = ANSWERS_DIR / f"{session}회" / subject / f"예시답안{a_num}.md"
            a_content = read_source_file(a_path, session, pdf_engine)
            pb_after_nav = False
            if a_content:
                if a_content.endswith(pagebreak):
                    a_content = a_content[:-len(pagebreak)].rstrip()
                    pb_after_nav = True
                lines.append(f"<!-- SRC:{subject}/예시답안{a_num}.md -->")
                lines.append(a_content)
                lines.append(f"<!-- /SRC:{subject}/예시답안{a_num}.md -->")
            
            lines.append("")
            q_anchor = f"#{session}회-{subject}-문제-{a_num}"
            if pdf_engine == 'w':
                lines.append(f'<div class="nav-bar"><a href="{q_anchor}">문제 바로가기</a><a href="{subject_anchor}">목차 바로가기</a></div>')
            else:
                lines.append(f'[문제 바로가기]({q_anchor})')
            lines.append("")
            if pb_after_nav: lines.extend([pagebreak, ""])

        if subject != SUBJECTS[-1]:
            lines.extend([pagebreak, ""])

    # 5. 판권 정보
    lines.extend([pagebreak, ""])
    copyright_info = read_template_file("판권.md")
    if copyright_info:
        copyright_info = copyright_info.replace("{발행일}", publication_date)
        copyright_info = copyright_info.replace("{nth}", str(session))
        if pdf_engine == 'w':
            res_path_for_html = get_res_path(session)
            copyright_info = copyright_info.replace('src="./res/{nth}_barcode.svg"', f'src="{res_path_for_html}/{session}_barcode.svg"')
        else:
            copyright_info = re.sub(r'<img[^>]+>', '', copyright_info) # pandoc에서는 HTML img 태그 제거
        lines.append(copyright_info)
    lines.append("")

    # 6. MathJax 스크립트 (pandoc은 자체적으로 LaTeX 수식 처리)
    if pdf_engine in ['w', 'l']:
        lines.append(MATHJAX_SCRIPT)

    return "\n".join(lines)


def merge_session(session: int, publication_date: str, pdf_engine: str) -> bool:
    """특정 회차의 답안을 통합"""
    print(f"\n{session}회 예시답안 통합 중...")

    # 통합 내용 생성
    merged_content = create_merged_content(session, publication_date, pdf_engine)

    # 출력 폴더 생성
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 통합 파일 저장
    output_file = OUTPUT_DIR / f"{session}회_경영지도사_생산관리분야_예시답안.md"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(merged_content)
    print(f"  MD 완료: {output_file} ({output_file.stat().st_size:,} bytes)")

    # PDF 생성 (옵션)
    if pdf_engine:
        pdf_file = OUTPUT_DIR / f"{session}회_경영지도사_생산관리분야_예시답안.pdf"
        return run_pdf_generation(output_file, pdf_file, pdf_engine)

    return True


def main():
    """메인 실행 함수"""
    print("=" * 60)
    print("경영지도사 예시답안 통합 스크립트 v2 (다중 PDF 엔진 지원)")
    print("=" * 60)

    available_sessions = sorted(get_available_sessions())

    # 인자 파싱
    args = sys.argv[1:]
    init_toc_flag = '--init-toc' in args
    
    pdf_engine = None
    if '--pdf-engine' in args:
        try:
            idx = args.index('--pdf-engine')
            pdf_engine = args[idx + 1]
            if pdf_engine not in ['w', 'l', 'd', 'wd']:
                raise ValueError
        except (IndexError, ValueError):
            print("\n오류: --pdf-engine 값은 'w', 'l', 'd', 'wd' 중 하나여야 합니다.")
            return

    publication_date = None
    if '--date' in args:
        try:
            idx = args.index('--date')
            publication_date = args[idx + 1]
            datetime.strptime(publication_date, "%Y-%m-%d")
        except (IndexError, ValueError):
            print("\n오류: --date 값은 YYYY-MM-DD 형식이어야 합니다.")
            return

    # 처리된 인자 제거
    processed_indices = set()
    if init_toc_flag: processed_indices.add(args.index('--init-toc'))
    if pdf_engine:
        idx = args.index('--pdf-engine')
        processed_indices.add(idx)
        processed_indices.add(idx + 1)
    if publication_date:
        idx = args.index('--date')
        processed_indices.add(idx)
        processed_indices.add(idx + 1)
    
    sessions_to_process_str = [arg for i, arg in enumerate(args) if i not in processed_indices]

    # 처리할 회차 결정
    sessions_to_process = []
    if sessions_to_process_str:
        for arg in sessions_to_process_str:
            if arg.lower() == 'all':
                sessions_to_process = available_sessions
                break
            elif arg.isdigit() and int(arg) in available_sessions:
                sessions_to_process.append(int(arg))
            else:
                print(f"경고: '{arg}'는 유효한 회차가 아니거나 사용할 수 없습니다.")
    
    # 필수 인자 확인
    if not sessions_to_process or (not publication_date and not init_toc_flag):
        print(f"\n사용 가능한 회차: {available_sessions}")
        print("\n사용법: python merge_qqaa2.py <회차|all> --date <YYYY-MM-DD> [옵션]")
        print("\n옵션:")
        print("  --pdf-engine <w|l|d|wd>  PDF 생성 엔진 선택 (w/l: playwright, d/wd: pandoc)")
        print("  --init-toc             목차.md 초안 생성")
        print("\n예시:")
        print("  python merge_qqaa2.py 40 --date 2026-04-10 --pdf-engine w")
        print("  python merge_qqaa2.py all --date 2026-04-10 --pdf-engine wd")
        print("  python merge_qqaa2.py 39 --init-toc")
        return

    print(f"\n처리할 회차: {sessions_to_process}")
    if publication_date: print(f"발행일: {publication_date}")
    if pdf_engine: print(f"PDF 엔진: {pdf_engine}")

    # --init-toc 모드
    if init_toc_flag:
        print("\n모드: 목차.md 초안 생성")
        count = sum(1 for session in sessions_to_process if generate_toc_template(session))
        print(f"\n완료: {count}/{len(sessions_to_process)} 회차 목차 템플릿 생성")
        return

    # 날짜 형식 변환
    formatted_date = datetime.strptime(publication_date, "%Y-%m-%d").strftime("%Y년 %m월 %d일")

    # 각 회차 처리
    success_count = 0
    for session in sessions_to_process:
        if merge_session(session, formatted_date, pdf_engine):
            success_count += 1

    print("\n" + "=" * 60)
    print(f"완료: {success_count}/{len(sessions_to_process)} 회차 통합 성공")
    print("=" * 60)


if __name__ == "__main__":
    main()
