#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
경영지도사 예시답안 통합 스크립트: 표지, 저자소개, 교재소개, 목차, 본문, 판권 순서
경영지도사 문제... + 예시답안... 통합 스크립트 (문문... 답답... 스타일)
문제 전체 그리고 예시답안 전체를 순서대로 구성: 문제1, 문제2, ... , 답안1, 답안2, ...

사용법:
    python merge_qqaa.py all                # 모든 회차 MD 생성
    python merge_qqaa.py 36                 # 특정 회차 MD 생성
    python merge_qqaa.py 36 40              # 여러 회차 MD 생성
    python merge_qqaa.py all --pdf          # 모든 회차 MD + PDF 생성
    python merge_qqaa.py 39 --pdf           # 특정 회차 MD + PDF 생성

    page break가 완전 자동화 되지 않아서 all은 실행하지 말것.
"""

import os
import sys
import io
import re
import json
import asyncio
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

try:
    from pypdf import PdfWriter
    PYPDF_AVAILABLE = True
except ImportError:
    PYPDF_AVAILABLE = False

# Windows 콘솔 인코딩 설정
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 경로 설정
BASE_DIR = Path(r"D:\drive_files\10.worksfree\30.publish\cmc")
ANSWERS_DIR = BASE_DIR / "30.예시답안"
QUESTIONS_DIR = BASE_DIR / "20.기출문제"
OUTPUT_DIR = BASE_DIR / "40.출판물"
TEMPLATE_DIR = BASE_DIR / "40.출판물" / "서식"

# 과목 순서
SUBJECTS = ["생산관리", "품질경영", "경영과학"]


def question_total_points(question_num: int) -> int:
    """대문항 총점 반환: 1~2번 30점, 3~6번 10점"""
    return 30 if question_num in (1, 2) else 10


def extract_keyword_from_title(title: str) -> str:
    """제목에서 핵심 키워드만 추출 (문장형 → 키워드형)"""
    # 점수 부분 제거 (30점), (25점) 등
    title = re.sub(r'\s*\(\d+점\)\s*$', '', title).strip()
    # "다음 물음에 답하시오" 제거
    title = re.sub(r'\s*다음\s*물음에\s*답하시오\.?\s*', '', title).strip()

    # " - " 패턴: 앞부분(키워드)만 추출
    if ' - ' in title:
        parts = title.split(' - ', 1)
        keyword_part = parts[0].strip()
        subtitle_part = parts[1].strip() if len(parts) > 1 else ""
        keyword_clean = re.sub(r'\s*\([A-Za-z\s,]+\)\s*', '', keyword_part).strip()
        if len(keyword_part) <= 15 and len(subtitle_part) <= 20:
            return f"{keyword_part} - {subtitle_part}"
        return keyword_clean if keyword_clean else keyword_part

    # "A에 관하여" / "A에 대하여" / "A와 관련하여" 패턴
    match = re.match(r'^(.+?)\s*(?:에\s*관하여|에\s*대하여|와\s*관련하여)', title)
    if match:
        return match.group(1).strip()

    # === 문장형 제목에서 핵심 키워드 추출 ===
    # 경영/생산관리 핵심 용어 사전
    keywords_map = [
        # 생산관리
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
        # 품질경영
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
        # 경영과학
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

    # 키워드 사전에서 매칭
    for pattern, keyword in keywords_map:
        if re.search(pattern, title, re.IGNORECASE):
            return keyword

    # 30자 이하면 그대로
    if len(title) <= 30:
        return title

    # 그 외: 키워드 추출 실패, 수동 편집 표시
    return f"[편집필요] {title[:20]}..."


def load_toc_titles(session: int) -> dict:
    """목차.md 파일에서 제목 로드 (없으면 빈 dict 반환)

    목차.md 형식:
    ## [36회 생산관리 목차](#36회-생산관리)
    - [[문제1] 수요예측 - 단순지수평활법과 계절지수](#36회-생산관리-문제-1)
    """
    toc_file = ANSWERS_DIR / f"{session}회" / "목차.md"

    if not toc_file.exists():
        # 구 형식 JSON 파일도 지원 (하위 호환성)
        json_file = ANSWERS_DIR / f"{session}회" / "목차.json"
        if json_file.exists():
            with open(json_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    toc_data = {}
    current_subject = None

    with open(toc_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            # 과목 헤더: ## [36회 생산관리 목차](#36회-생산관리)
            subject_match = re.match(r'^##\s*\[\d+회\s+(.+?)\s*목차\]', line)
            if subject_match:
                current_subject = subject_match.group(1)
                if current_subject not in toc_data:
                    toc_data[current_subject] = {}
                continue

            # 문제 항목: - [[문제N] 제목](#앵커)
            item_match = re.match(r'^-\s*\[\[문제(\d+)\]\s*(.+?)\]\(#(.+?)\)', line)
            if item_match and current_subject:
                q_num = item_match.group(1)
                title = item_match.group(2).strip()
                link = f"#{item_match.group(3)}"
                toc_data[current_subject][q_num] = {
                    "title": title,
                    "link": link
                }

    return toc_data


def get_question_title(session: int, subject: str, question_num: int, toc_titles: dict) -> str:
    """목차용 제목 반환 (목차.json 우선, 없으면 자동 추출)"""
    # 목차.json에 있으면 사용
    if subject in toc_titles and str(question_num) in toc_titles[subject]:
        entry = toc_titles[subject][str(question_num)]
        # 새 형식 (dict with 'title' key) 또는 구 형식 (string) 모두 지원
        if isinstance(entry, dict):
            return entry.get("title", f"문제{question_num}")
        return entry  # 구 형식 (string)

    # 없으면 기존 방식으로 추출
    return extract_question_title(session, subject, question_num)


def generate_toc_template(session: int) -> bool:
    """목차.md 초안 생성 (마크다운 형식)

    생성되는 형식:
    # <div align="center"> 36회 목차 </div>
    ## [36회 생산관리 목차](#36회-생산관리)
    - [[문제1] 수요예측 - 단순지수평활법과 계절지수](#36회-생산관리-문제-1)
    """
    session_dir = ANSWERS_DIR / f"{session}회"
    toc_file = session_dir / "목차.md"

    if not session_dir.exists():
        print(f"오류: {session}회 폴더가 존재하지 않습니다.")
        return False

    lines = []
    lines.append(f'# <div align="center"> {session}회 목차 </div>')
    lines.append("")

    for subject in SUBJECTS:
        lines.append(f"## [{session}회 {subject} 목차](#{session}회-{subject})")

        for q_num in range(1, 7):
            # 앵커 링크 생성
            anchor = f"{session}회-{subject}-문제-{q_num}"

            # 문제 파일에서 제목 추출
            question_file = QUESTIONS_DIR / f"{session}회" / subject / f"문제{q_num}.md"

            if question_file.exists():
                with open(question_file, "r", encoding="utf-8") as f:
                    content = f.read()

                # ### 【문제 N】 제목... 패턴에서 제목 추출
                match = re.search(r'###\s*【문제\s*\d+】\s*(.+?)(?:\n|$)', content)
                if match:
                    raw_title = match.group(1).strip()
                    # 키워드 추출
                    keyword = extract_keyword_from_title(raw_title)
                else:
                    keyword = f"문제{q_num}"
            else:
                keyword = f"문제{q_num}"

            lines.append(f"- [[문제{q_num}] {keyword}](#{anchor})")

        lines.append("")  # 과목 사이 빈 줄

    # MD 파일 저장
    with open(toc_file, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"  목차 템플릿 생성: {toc_file}")
    return True


# CSS 스타일 (39회 PDF 형식)
CSS_STYLE = """<style>
body  { margin-left: 40px; margin-right: 40px; padding: 20px; background: #00000;
        font-size: 12pt; line-height: 150%; }
h1    { font-size: 16pt; text-align: center;
        color: black; border-bottom: 6px solid #333; padding-bottom: 10px; }
h2    { font-size: 14pt; text-align: left; /* color: green; */
        border-left: 4px solid #0d47a1; padding-left: 10px; }
h3    { font-size: 13pt; text-align: left; color:rgb(37, 37, 37);
        border-left: 4px solid green; padding-left: 10px; }
blockquote { font-size: 10pt; line-height: 150%; }
pre   { font-size: 10pt; line-height: 150%; /* padding: 20px; */ }
table { margin-left :auto; margin-right:auto; border: 1px solid; width: 100%; border-collapse: collapse; }
th    { text-align: center; border: 1px solid; background-color: #D3D3D3;}
td    { text-align: center; border: 1px solid; }
.custome-body  { border: 0px solid; width: 100%; background: #900;
        font-size: 12pt; line-height: 150%; }
.custome-table { border: 1px solid; width: 50%; margin-bottom: 10px; margin-left: 10px; }
.custome-table-trans { border-collapse: collapse; border-left:none;border-right:none; border-top:none; border-bottom:none;}
.custome-td  { text-align: left; }
.custome-td-trans  { text-align: left; border-left:none;border-right:none; border-top:none; border-bottom:none;}
.slash      { background: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg"><line x1="0" y1="100%" x2="100%" y2="0" stroke="black" /></svg>');}
.backslash  { background: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg"><line x1="0%" y1="3%" x2="100%" y2="97%" stroke="black" /></svg>'); background-color: #D3D3D3 }

/* 페이지 나누기 방지 스타일 추가 */
.qa-pair, table, pre, figure, blockquote {
    page-break-inside: avoid;
}

/* h2/h3 헤딩 뒤에 페이지 브레이크 금지 → 헤딩이 페이지 하단에 고립되지 않음 */
h2 {
    break-after: avoid;
    page-break-after: avoid;
}
h3 {
    break-after: avoid;
    page-break-after: avoid;
}

/* 바로가기 네비게이션 바 */
.nav-bar {
    display: flex;
    justify-content: space-between;
    margin-bottom: 0.6em;
    padding-bottom: 0.4em;
    border-bottom: 1px solid #ccc;
    font-size: 10pt;
    page-break-inside: avoid;
    page-break-after: avoid;
}

img {
    page-break-inside: avoid;
    max-width: 100%; /* 이미지가 페이지 너비를 넘지 않도록 함 */
}

.page { page-break-after: always; }
</style>

<script type="module">
  import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@9/dist/mermaid.esm.min.mjs';
  mermaid.initialize({ startOnLoad: true });
</script>
"""

# MathJax 스크립트 (문서 끝에 추가) — MathJax v3 + HTTPS CDN
MATHJAX_SCRIPT = """
<script>
MathJax = {
    tex: {
        inlineMath: [['$', '$']],
        displayMath: [['$$', '$$']],
        processEscapes: true
    },
    options: {
        skipHtmlTags: ['script', 'noscript', 'style', 'textarea', 'pre']
    }
};
</script>
<script type="text/javascript" id="MathJax-script" async
    src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-chtml.js">
</script>
"""

# PDF 변환용 HTML 템플릿
HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{title}</title>
    <style>
        @page {{
            size: A4;
            margin: 25mm 15mm 25mm 15mm;
        }}
        @media print {{
            .page {{ page-break-after: always; }}
        }}
    </style>
</head>
<body>
{content}
</body>
</html>
"""


def protect_math_blocks(content: str) -> tuple[str, dict]:
    """수식 블록을 마크다운 처리 전에 보호 (placeholder로 대체)"""
    placeholders = {}
    counter = [0]  # mutable for closure

    def replace_block(match):
        key = f"ZZMBLN{counter[0]}ZZ"
        placeholders[key] = match.group(0)
        counter[0] += 1
        return key

    def replace_inline(match):
        key = f"ZZMINL{counter[0]}ZZ"
        placeholders[key] = match.group(0)
        counter[0] += 1
        return key

    # 인라인 수식 먼저 보호 — 연속된 $expr1$$expr2$ 패턴이 $$로 오인되는 것 방지
    content = re.sub(r'\$[^\$\n]+\$', replace_inline, content)
    # 블록 수식 보호 ($$...$$, 여러 줄 포함) — 인라인 제거 후 처리해야 오작동 없음
    content = re.sub(r'\$\$[\s\S]*?\$\$', replace_block, content)

    return content, placeholders


def restore_math_blocks(content: str, placeholders: dict) -> str:
    """보호된 수식 블록 복원"""
    for key, value in placeholders.items():
        content = content.replace(key, value)
    return content


def convert_md_to_html(md_content: str, base_path: Path) -> str:
    """마크다운을 HTML로 변환"""
    if not MARKDOWN_AVAILABLE:
        # markdown 라이브러리 없으면 그대로 반환
        return md_content

    # 수식 블록 보호 (마크다운이 _를 이탤릭으로 해석하지 않도록)
    md_content, math_placeholders = protect_math_blocks(md_content)

    # 상대 경로를 절대 경로로 변환 (이미지 로딩을 위해)
    # ../../30.예시답안/39회/res/ -> file:///D:/...
    def fix_image_path(match):
        src = match.group(1)
        if src.startswith('../../'):
            # 상대 경로를 절대 경로로 변환
            abs_path = (base_path / src).resolve()
            return f'src="file:///{str(abs_path).replace(chr(92), "/")}"'
        return match.group(0)

    md_content = re.sub(r'src="([^"]+)"', fix_image_path, md_content)

    # 마크다운 -> HTML 변환
    md = markdown.Markdown(extensions=['tables', 'fenced_code', 'toc'])
    html_body = md.convert(md_content)

    # 수식 블록 복원
    html_body = restore_math_blocks(html_body, math_placeholders)

    return html_body


# ── 내부 링크 좌표 변환 상수 (page.pdf() 마진과 일치) ──────────────────────
_MM_TO_PT     = 72.0 / 25.4
_MM_TO_PX     = 96.0 / 25.4
_PX_TO_PT     = 72.0 / 96.0                           # 0.75
_PAPER_H_PT   = 297 * _MM_TO_PT                       # 841.89 pt
_MARGIN_TOP_PT  = 25 * _MM_TO_PT                      # 70.87 pt
_MARGIN_LEFT_PT = 15 * _MM_TO_PT                      # 42.52 pt
_CONTENT_H_PX = (297 - 25 - 25) * _MM_TO_PX          # 933.54 px / page (content 높이)
_PRINT_W_PX   = int((210 - 15 - 15) * _MM_TO_PX)     # 680 px (print content 너비)


def _px_to_pdf_rect(top_px: float, left_px: float, w_px: float, h_px: float):
    """CSS px → (page_index, (x0,y0,x1,y1) in pt, origin bottom-left)"""
    page_idx      = int(top_px / _CONTENT_H_PX)
    y_top_in_page = top_px - page_idx * _CONTENT_H_PX
    x0 = _MARGIN_LEFT_PT + left_px * _PX_TO_PT
    x1 = _MARGIN_LEFT_PT + (left_px + w_px) * _PX_TO_PT
    y1 = _PAPER_H_PT - _MARGIN_TOP_PT - y_top_in_page * _PX_TO_PT
    y0 = _PAPER_H_PT - _MARGIN_TOP_PT - (y_top_in_page + h_px) * _PX_TO_PT
    return page_idx, (x0, y0, x1, y1)


def _px_to_page_y(top_px: float):
    """CSS px → (page_index, y_pt from bottom-left)"""
    page_idx   = int(top_px / _CONTENT_H_PX)
    y_in_page  = top_px - page_idx * _CONTENT_H_PX
    y_pt       = _PAPER_H_PT - _MARGIN_TOP_PT - y_in_page * _PX_TO_PT
    return page_idx, y_pt


def _inject_links(pdf_path: str, html_content: str) -> None:
    """PDF에 내부 링크 어노테이션 삽입 (pdfplumber 기반 좌표 탐색)"""
    if not PYPDF_AVAILABLE:
        return
    try:
        import pdfplumber
    except ImportError:
        print("  pdfplumber 없음 - 링크 삽입 생략")
        return

    import os
    from pypdf.generic import (
        DictionaryObject, NameObject, ArrayObject, FloatObject, NumberObject
    )

    def norm(text: str) -> str:
        """공백 정규화 + 숫자-회 사이 공백 제거"""
        text = re.sub(r'(\d)\s+(회)', r'\1\2', text)
        return re.sub(r'\s+', ' ', text).strip()

    # ── 1. HTML에서 링크 목록 추출 (문서 순서대로) ─────────────────
    link_list = []  # [(anchor_id, link_text)]
    for m in re.finditer(r'<a\s+href="#([^"]+)"[^>]*>(.*?)</a>', html_content, re.DOTALL):
        link_text = re.sub(r'<[^>]+>', '', m.group(2)).strip()
        if link_text:
            link_list.append((m.group(1), link_text))

    if not link_list:
        return

    # ── 2. HTML에서 앵커 타겟 → 바로 뒤 헤딩 텍스트 매핑 ───────────
    anchor_to_heading = {}
    for m in re.finditer(
        r'<a\s+id="([^"]+)"[^>]*/?>(?:</a>)?\s*\n?\s*<(h[123])[^>]*>(.*?)</\2>',
        html_content, re.DOTALL | re.IGNORECASE
    ):
        heading_text = re.sub(r'<[^>]+>', '', m.group(3)).strip()
        # TOC 제목 바깥 대괄호 제거: [36회 생산관리 목차] → 36회 생산관리 목차
        heading_text = re.sub(r'^\[(.+)\]$', r'\1', heading_text)
        anchor_to_heading[m.group(1)] = heading_text

    # ── 3. pdfplumber로 페이지 텍스트/단어 추출 ────────────────────
    with pdfplumber.open(pdf_path) as pdf:
        n_pages   = len(pdf.pages)
        page_h_pt = float(pdf.pages[0].height) if n_pages > 0 else 841.89
        pages_text  = [norm(p.extract_text() or '') for p in pdf.pages]
        pages_words = [p.extract_words()            for p in pdf.pages]

    # ── 4. 앵커 타겟 위치 탐색 ───────────────────────────────────
    target_pos = {}  # anchor_id → (page_idx, y_from_bottom_pt)

    for anchor_id, heading_text in anchor_to_heading.items():
        norm_kw = norm(heading_text)
        if not norm_kw:
            continue
        # 숫자로 끝나면 뒤에 숫자가 붙지 않도록 (예: "문제 1" ≠ "문제 10")
        pat = re.escape(norm_kw) + (r'(?!\d)' if norm_kw[-1].isdigit() else '')

        for page_idx, pg_text in enumerate(pages_text):
            if not re.search(pat, pg_text):
                continue
            # 헤딩의 첫 단어 y좌표 추출
            first_word_str = norm_kw.split()[0]
            matched = False
            for w in pages_words[page_idx]:
                if norm(w['text']) == first_word_str:
                    target_pos[anchor_id] = (page_idx, page_h_pt - w['top'])
                    matched = True
                    break
            if not matched:
                target_pos[anchor_id] = (page_idx, page_h_pt - 30)
            break
        else:
            print(f"  ⚠ 앵커 못 찾음: {anchor_id} ({heading_text})")

    # ── 5. 링크 소스 위치 탐색 (pdfplumber 단어 위치) ──────────────
    needed_texts = list({lt for _, lt in link_list})
    occurrences  = {}  # link_text → [(page_idx, x0, y0_bottom, x1, y1_bottom)]

    for page_idx, words in enumerate(pages_words):
        for lt in needed_texts:
            lt_norm  = norm(lt)
            lt_parts = lt_norm.split()
            n = len(lt_parts)
            if n == 0:
                continue
            for i in range(len(words) - n + 1):
                grp  = words[i:i+n]
                joined = norm(' '.join(w['text'] for w in grp))
                if lt_norm in joined or joined == lt_norm:
                    x0  = min(w['x0']     for w in grp)
                    x1  = max(w['x1']     for w in grp)
                    top = min(w['top']    for w in grp)
                    bot = max(w['bottom'] for w in grp)
                    if lt not in occurrences:
                        occurrences[lt] = []
                    occurrences[lt].append((page_idx,
                                            x0, page_h_pt - bot,
                                            x1, page_h_pt - top))
                    break

    # ── 6. link_list × occurrences 순서 매핑 ──────────────────────
    src_list  = []  # [(anchor_id, page_idx, x0, y0, x1, y1)]
    occ_idx   = {}  # link_text → 다음에 사용할 인덱스

    for anchor_id, link_text in link_list:
        occ = occurrences.get(link_text, [])
        i   = occ_idx.get(link_text, 0)
        if i < len(occ):
            src_list.append((anchor_id, *occ[i]))
        occ_idx[link_text] = i + 1

    # ── 7. pypdf로 어노테이션 삽입 ───────────────────────────────
    writer  = PdfWriter(clone_from=pdf_path)
    added   = 0

    for anchor_id, src_page, x0, y0, x1, y1 in src_list:
        if anchor_id not in target_pos:
            continue
        dst_page, dst_y = target_pos[anchor_id]
        if not (0 <= src_page < n_pages and 0 <= dst_page < n_pages):
            continue

        page_ref = writer.pages[dst_page].indirect_reference
        annot = DictionaryObject({
            NameObject('/Type'):    NameObject('/Annot'),
            NameObject('/Subtype'): NameObject('/Link'),
            NameObject('/Rect'):    ArrayObject([FloatObject(v) for v in (x0, y0, x1, y1)]),
            NameObject('/Border'):  ArrayObject([NumberObject(0)] * 3),
            NameObject('/Dest'):    ArrayObject([
                page_ref,
                NameObject('/XYZ'),
                FloatObject(0),
                FloatObject(dst_y),
                FloatObject(0),
            ]),
        })
        src_page_obj = writer.pages[src_page]
        if '/Annots' not in src_page_obj:
            src_page_obj[NameObject('/Annots')] = ArrayObject()
        src_page_obj['/Annots'].append(writer._add_object(annot))
        added += 1

    tmp_path = pdf_path + '.tmp_links'
    try:
        with open(tmp_path, 'wb') as f:
            writer.write(f)
        os.replace(tmp_path, pdf_path)
        print(f"  링크 어노테이션: {added}개 삽입")
    except Exception as e:
        print(f"  링크 삽입 오류: {e}")
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


async def convert_html_to_pdf(html_content: str, pdf_path: Path) -> bool:
    """HTML을 PDF로 변환 (playwright 사용)"""
    if not PLAYWRIGHT_AVAILABLE:
        print("  오류: playwright가 설치되지 않았습니다. pip install playwright && playwright install chromium")
        return False

    # 임시 HTML 파일을 PDF와 같은 폴더에 저장 → ../상대경로 자동 해결
    html_tmp = pdf_path.with_suffix('.tmp.html')

    try:
        html_tmp.write_text(html_content, encoding='utf-8')
        file_url = 'file:///' + str(html_tmp).replace('\\', '/')

        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()

            # 파일 URL로 로드 (이미지 등 상대 경로 자동 해결)
            await page.goto(file_url, wait_until='networkidle')

            # Mermaid 렌더링 완료 대기
            try:
                await page.wait_for_function(
                    "typeof mermaid !== 'undefined'",
                    timeout=10000
                )
                await page.wait_for_timeout(2000)
            except Exception:
                pass

            # MathJax v3 렌더링 완료 대기
            try:
                await page.wait_for_function(
                    "typeof MathJax !== 'undefined' && MathJax.typesetPromise !== undefined",
                    timeout=15000
                )
                await page.evaluate("MathJax.typesetPromise()")
                await page.wait_for_timeout(2000)
            except Exception:
                # MathJax 없거나 타임아웃 시 fallback 대기
                await page.wait_for_timeout(3000)

            # PDF 저장 (헤더/푸터 포함)
            await page.pdf(
                path=str(pdf_path),
                format='A4',
                margin={
                    'top': '25mm',
                    'bottom': '25mm',
                    'left': '15mm',
                    'right': '15mm'
                },
                print_background=True,
                display_header_footer=True,
                header_template=(
                    '<div style="font-size:10pt; color:#333; width:100%; padding:0 15mm;'
                    ' box-sizing:border-box;">'
                    'www.worksfree.com'
                    '</div>'
                ),
                footer_template=(
                    '<div style="font-size:10pt; color:#333; width:100%; padding:0 15mm;'
                    ' box-sizing:border-box; text-align:center;">'
                    '<span class="pageNumber"></span> / <span class="totalPages"></span>'
                    '</div>'
                ),
            )

            await browser.close()

        # 내부 링크 어노테이션 삽입 (pdfplumber 기반, 브라우저 종료 후)
        _inject_links(str(pdf_path), html_content)

        return True

    except Exception as e:
        print(f"  PDF 변환 오류: {e}")
        return False
    finally:
        if html_tmp.exists():
            html_tmp.unlink()


def generate_pdf(md_file: Path, pdf_file: Path) -> bool:
    """MD 파일을 PDF로 변환"""
    print(f"  PDF 생성 중: {pdf_file.name}")

    # MD 파일 읽기
    with open(md_file, 'r', encoding='utf-8') as f:
        md_content = f.read()

    # MD -> HTML 변환
    html_body = convert_md_to_html(md_content, md_file.parent)

    # HTML 템플릿에 삽입
    title = md_file.stem
    html_content = HTML_TEMPLATE.format(title=title, content=html_body)

    # HTML -> PDF 변환
    success = asyncio.run(convert_html_to_pdf(html_content, pdf_file))

    if success:
        file_size = pdf_file.stat().st_size
        print(f"  PDF 완료: {pdf_file} ({file_size:,} bytes)")

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
    return f"../30.예시답안/{session}회/res"


def convert_image_paths(content: str, session: int) -> str:
    """개별 답안 파일의 이미지 경로를 출력 파일 기준 경로로 변환

    개별 답안 파일: 30_예시답안/{session}회/{과목}/답안*.md
    이미지 폴더: 30_예시답안/{session}회/res/
    출력 파일: 40_출판물/{session}회_*.md

    답안 파일에서의 경로: ./res/ 또는 ../res/ 또는 ../../30.예시답안/{session}회/res/
    출력 파일에서의 경로: ../30_예시답안/{session}회/res/
    """
    res_path = get_res_path(session)

    # ./res/ 패턴 변환
    content = re.sub(r'src="\.\/res\/', f'src="{res_path}/', content)
    # ../res/ 패턴 변환
    content = re.sub(r'src="\.\.\/res\/', f'src="{res_path}/', content)
    # ../../30.예시답안/{session}회/res/ 패턴 변환 (절대경로 스타일로 작성된 경우)
    content = re.sub(
        r'src="\.\.\/\.\.\/30\.예시답안\/\d+회\/res\/',
        f'src="{res_path}/',
        content
    )

    return content


def read_answer_file(session: int, subject: str, answer_num: int) -> str:
    """개별 답안 파일 읽기 및 이미지 경로 변환"""
    answer_file = ANSWERS_DIR / f"{session}회" / subject / f"예시답안{answer_num}.md"

    if not answer_file.exists():
        print(f"  경고: {answer_file} 파일을 찾을 수 없습니다.")
        return None

    with open(answer_file, "r", encoding="utf-8") as f:
        content = f.read().strip()

    # 이미지 경로 변환
    content = convert_image_paths(content, session)

    # 중복 방지를 위한 헤더 및 링크 제거 (스크립트에서 별도로 추가함)
    # ## N회 과목 문제 N 예시답안 헤더 제거
    content = re.sub(r'^## \d+회 .+ 문제 \d+ 예시답안\s*\n?', '', content)
    # [문제 바로가기] 링크 제거
    content = re.sub(r'\[문제 바로가기\]\([^)]+\)\s*\n?', '', content)
    # [목차 바로가기] 링크 제거
    content = re.sub(r'\[목차 바로가기\]\([^)]+\)\s*\n?', '', content)

    # 끝 부분의 페이지 구분자 및 구분선 제거 (개별 파일에 포함된 것과 스크립트 추가분 중복 방지)
    # ----- 또는 --- 와 <div class="page"></div> 패턴 제거
    content = content.strip()
    # 수평선(3개 이상의 대시) + 페이지구분자 + 수평선 패턴 제거
    content = re.sub(r'[\s\n]*-{3,}[\s\n]*(<div class="page"></div>|<!--\s*<div class="page"></div>\s*-->)[\s\n]*(-{3,})?[\s\n]*$', '', content)
    # 끝에 남은 수평선 제거
    content = re.sub(r'[\s\n]*-{3,}[\s\n]*$', '', content)

    # 이중 주석 오염 자동 정리 (sync_back 사이클에서 발생할 수 있는 손상 복구)
    content = re.sub(r'<!--\s*<!--\s*pagebreak\s*-->\s*-->', '<!-- pagebreak -->', content)
    content = re.sub(r'<!--\s*<!--\s*pagebreak\s*-->[\s\S]*?-->', '<!-- pagebreak -->', content)

    # <!-- pagebreak --> 마커를 실제 페이지 구분자로 변환 (소스 파일에서 중간 페이지 구분 지정용)
    content = content.replace('<!-- pagebreak -->', '<div class="page"></div>')

    return content


def read_question_file(session: int, subject: str, question_num: int) -> str:
    """개별 문제 파일 읽기 (과목 포함)"""
    question_file = QUESTIONS_DIR / f"{session}회" / subject / f"문제{question_num}.md"

    if not question_file.exists():
        print(f"  경고: {question_file} 파일을 찾을 수 없습니다.")
        return None

    with open(question_file, "r", encoding="utf-8") as f:
        content = f.read().strip()

    # 이미지 경로 변환
    content = convert_image_paths(content, session)

    # <!-- pagebreak --> 마커를 실제 페이지 구분자로 변환
    content = content.replace('<!-- pagebreak -->', '<div class="page"></div>')

    return content


def extract_question_title(session: int, subject: str, question_num: int) -> str:
    """문제 파일에서 짧은 제목 추출 (목차용) - 키워드 추출 적용"""
    question_file = QUESTIONS_DIR / f"{session}회" / subject / f"문제{question_num}.md"

    if not question_file.exists():
        return f"문제{question_num}"

    with open(question_file, "r", encoding="utf-8") as f:
        content = f.read()

    # ### 【문제 N】 제목... 패턴에서 제목 추출
    match = re.search(r'###\s*【문제\s*\d+】\s*(.+?)(?:\n|$)', content)
    if match:
        raw_title = match.group(1).strip()
        # 키워드 추출 함수 사용
        return extract_keyword_from_title(raw_title)

    return f"문제{question_num}"


def read_template_file(template_name: str) -> str:
    """서식 파일 읽기"""
    template_file = TEMPLATE_DIR / template_name

    if not template_file.exists():
        print(f"  경고: {template_file} 파일을 찾을 수 없습니다.")
        return None

    with open(template_file, "r", encoding="utf-8") as f:
        content = f.read().strip()

    return content


def create_merged_content(session: int) -> str:
    """통합 마크다운 내용 생성 (39회 PDF 형식)"""

    lines = []
    res_path = get_res_path(session)

    # 1. CSS 스타일
    lines.append(CSS_STYLE)
    lines.append("")

    # 2. 표지 이미지
    lines.append(f'<img src="서식/표지_{session}.jpg">')
    lines.append("")
    lines.append('<div class="page"></div>')
    lines.append("")

    # 3. 저자소개 및 교재소개
    author_intro = read_template_file("저자소개_교재소개.md")
    if author_intro:
        # 저자소개의 RPA-profile.png 경로도 변환
        # author_intro = author_intro.replace(
        #     'src="./res/RPA-profile.png"',
        #     f'src="{res_path}/RPA-profile.png"'
        # )
        # 템플릿 내 QR 이미지 경로를 절대 경로로 변환
        qr_image_path = TEMPLATE_DIR / "worksfree.com-QR.png"
        author_intro = author_intro.replace(
            'src="./worksfree.com-QR.png"',
            f'src="file:///{str(qr_image_path).replace(chr(92), "/")}"'
        )
        lines.append(author_intro)
    lines.append("")
    lines.append('<div class="page"></div>')
    lines.append("")

    # 4. 목차 생성 (문제 제목 포함) - 목차.json 우선 사용
    toc_titles = load_toc_titles(session)
    lines.append(f'# <div align="center"> {session}회 목차 </div>')

    for subject in SUBJECTS:
        lines.append(f'<a id="{session}회-{subject}-목차"></a>')
        lines.append(f"## [{session}회 {subject} 목차](#{session}회-{subject})")
        for i in range(1, 7):
            anchor = f"{session}회-{subject}-문제-{i}"
            title = get_question_title(session, subject, i, toc_titles)
            lines.append(f"- [[문제{i}] {title}](#{anchor})")
    lines.append("")
    lines.append('<div class="page"></div>')
    lines.append("")

    # 5. 각 과목별 문제 및 답안 병합 (QQAA 방식: 문제 전체 → 답안 전체)
    for subject in SUBJECTS:
        # === 문제 섹션 (1~6번 모두) ===
        lines.append(f'<a id="{session}회-{subject}"></a>')
        lines.append(f"# {session}회 {subject} 문제")
        lines.append("")

        for question_num in range(1, 7):
            lines.append(f'<a id="{session}회-{subject}-문제-{question_num}"></a>')
            lines.append(f"## {session}회 {subject} 문제 {question_num}")

            # 문제 내용 (있으면 포함)
            question_content = read_question_file(session, subject, question_num)
            pb_after_nav = False
            if question_content:
                # ## 헤더 제거 (중복 방지)
                question_content = re.sub(r'^## \d+회 .+ 문제 \d+\s*\n', '', question_content)
                # [목차 바로가기] 링크 제거 (스크립트에서 별도로 추가)
                question_content = re.sub(r'\[목차 바로가기\]\([^)]+\)\s*', '', question_content)
                # [예시답안 바로가기] 링크 제거 (스크립트에서 별도로 추가)
                question_content = re.sub(r'\[예시답안 바로가기\]\([^)]+\)\s*', '', question_content)
                # 말미 pagebreak 감지 → nav-bar 뒤로 이동
                if re.search(r'<div class="page"></div>\s*$', question_content):
                    question_content = re.sub(r'\s*<div class="page"></div>\s*$', '', question_content).rstrip()
                    pb_after_nav = True
                lines.append(f"<!-- SRC:{subject}/문제{question_num}.md -->")
                lines.append(question_content)
                lines.append(f"<!-- /SRC:{subject}/문제{question_num}.md -->")
            else:
                lines.append(f"### 【문제 {question_num}】")
                lines.append("")

            lines.append("")
            answer_total = question_total_points(question_num)
            lines.append(f'<div class="nav-bar"><a href="#{session}회-{subject}-문제-{question_num}-예시답안-{answer_total}점">예시답안 바로가기</a><a href="#{session}회-{subject}-목차">목차 바로가기</a></div>')
            lines.append("")
            if pb_after_nav:
                lines.append('<div class="page"></div>')
                lines.append("")

        # === 문제-예시답안 사이 페이지 구분 ===
        lines.append('<div class="page"></div>')
        lines.append("")

        # === 예시답안 섹션 (1~6번 모두) ===
        lines.append(f"# {session}회 {subject} 예시답안")
        lines.append("")

        for answer_num in range(1, 7):
            answer_total = question_total_points(answer_num)
            lines.append(f'<a id="{session}회-{subject}-문제-{answer_num}-예시답안-{answer_total}점"></a>')
            lines.append(f"## {session}회 {subject} 문제 {answer_num} 예시답안 ({answer_total}점)")
            lines.append("")

            content = read_answer_file(session, subject, answer_num)
            pb_after_nav = False
            if content:
                # 말미 pagebreak 감지 → nav-bar 뒤로 이동
                if re.search(r'<div class="page"></div>\s*$', content):
                    content = re.sub(r'\s*<div class="page"></div>\s*$', '', content).rstrip()
                    pb_after_nav = True
                lines.append(f"<!-- SRC:{subject}/예시답안{answer_num}.md -->")
                lines.append(content)
                lines.append(f"<!-- /SRC:{subject}/예시답안{answer_num}.md -->")
            else:
                lines.append("> 답안 내용이 없습니다.")

            lines.append("")
            lines.append(f'<div class="nav-bar"><a href="#{session}회-{subject}-문제-{answer_num}">문제 바로가기</a><a href="#{session}회-{subject}-목차">목차 바로가기</a></div>')
            lines.append("")
            if pb_after_nav:
                lines.append('<div class="page"></div>')
                lines.append("")

        # === 과목 전환 시에만 페이지 구분 ===
        lines.append('<div class="page"></div>')
        lines.append("")

    # 6. 판권 정보
    copyright_info = read_template_file("판권.md")
    if copyright_info:
        # 템플릿 변수 치환
        today = datetime.now().strftime("%Y년 %m월 %d일")
        copyright_info = copyright_info.replace("{발행일}", today)
        # 바코드 이미지 경로 변환 (템플릿 변수 치환 전에 처리)
        copyright_info = copyright_info.replace(
            'src="./res/{nth}_barcode.svg"',
            f'src="{res_path}/{session}_barcode.svg"'
        )
        # {nth} 변수 치환
        copyright_info = copyright_info.replace("{nth}", str(session))
        lines.append(copyright_info)
    lines.append("")

    # 7. MathJax 스크립트
    lines.append(MATHJAX_SCRIPT)

    return "\n".join(lines)


def merge_session(session: int, generate_pdf_flag: bool = False, pdf_only: bool = False) -> bool:
    """특정 회차의 답안을 통합"""

    session_dir = ANSWERS_DIR / f"{session}회"
    output_file = OUTPUT_DIR / f"{session}회_경영지도사_생산관리분야_예시답안.md"
    pdf_file    = OUTPUT_DIR / f"{session}회_경영지도사_생산관리분야_예시답안.pdf"

    if not session_dir.exists():
        print(f"오류: {session}회 폴더가 존재하지 않습니다: {session_dir}")
        return False

    # --pdf-only: MD 재생성 없이 기존 MD로 PDF만 생성
    if pdf_only:
        if not output_file.exists():
            print(f"오류: {output_file.name} 없음 — 먼저 MD를 생성하세요.")
            return False
        print(f"\n{session}회 PDF만 재생성 중... (기존 MD 사용)")
        generate_pdf(output_file, pdf_file)
        return True

    print(f"\n{session}회 예시답안 통합 중...")

    # 과목별 파일 존재 여부 확인
    total_files = 0
    for subject in SUBJECTS:
        subject_dir = session_dir / subject
        if subject_dir.exists():
            answer_files = list(subject_dir.glob("예시답안*.md"))
            total_files += len(answer_files)
            print(f"  {subject}: {len(answer_files)}개 답안 파일 발견")
        else:
            print(f"  경고: {subject} 폴더 없음")

    if total_files == 0:
        print(f"  오류: 답안 파일을 찾을 수 없습니다.")
        return False

    # 통합 내용 생성
    merged_content = create_merged_content(session)

    # 출력 폴더 생성 (없으면)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(merged_content)

    file_size = output_file.stat().st_size
    print(f"  MD 완료: {output_file} ({file_size:,} bytes)")

    # PDF 생성 (옵션)
    if generate_pdf_flag:
        generate_pdf(output_file, pdf_file)

    return True


def main():
    """메인 실행 함수"""
    print("=" * 60)
    print("경영지도사 예시답안 통합 스크립트 (39회 PDF 형식)")
    print("=" * 60)

    # 사용 가능한 회차 확인
    available_sessions = get_available_sessions()
    print(f"\n사용 가능한 회차: {available_sessions}")

    # 옵션 확인
    pdf_only_flag     = '--pdf-only' in sys.argv
    generate_pdf_flag = '--pdf' in sys.argv and not pdf_only_flag
    init_toc_flag     = '--init-toc' in sys.argv
    args = [arg for arg in sys.argv[1:] if arg not in ('--pdf', '--pdf-only', '--init-toc')]

    # 처리할 회차 결정
    if len(args) > 0:
        # 명령줄 인자로 지정된 회차 처리
        sessions_to_process = []
        for arg in args:
            if arg.lower() == 'all':
                # 'all' 인자: 모든 회차 처리
                sessions_to_process = available_sessions
                break
            elif arg.isdigit():
                session = int(arg)
                if session in available_sessions:
                    sessions_to_process.append(session)
                else:
                    print(f"경고: {session}회 폴더가 존재하지 않습니다.")
    else:
        # 인자 없이 실행 시 사용법 안내
        print("\n사용법:")
        print("    python merge_qqaa.py all             # 모든 회차 MD 생성")
        print("    python merge_qqaa.py 36              # 특정 회차 MD 생성")
        print("    python merge_qqaa.py 36 40           # 여러 회차 MD 생성")
        print("    python merge_qqaa.py all --pdf          # 모든 회차 MD + PDF 생성")
        print("    python merge_qqaa.py 39 --pdf           # 특정 회차 MD + PDF 생성")
        print("    python merge_qqaa.py 39 --pdf-only      # 기존 MD로 PDF만 재생성")
        print("    python merge_qqaa.py 36 --init-toc      # 목차.md 초안 생성")
        print("    python merge_qqaa.py all --init-toc     # 모든 회차 목차.md 생성")
        return

    if not sessions_to_process:
        print("\n오류: 처리할 회차가 없습니다.")
        return

    print(f"\n처리할 회차: {sessions_to_process}")

    # --init-toc 모드: 목차.md 초안 생성
    if init_toc_flag:
        print("모드: 목차.md 초안 생성")
        success_count = 0
        for session in sessions_to_process:
            print(f"\n{session}회 목차 템플릿 생성 중...")
            if generate_toc_template(session):
                success_count += 1

        print("\n" + "=" * 60)
        print(f"완료: {success_count}/{len(sessions_to_process)} 회차 목차 템플릿 생성")
        print("목차.md 파일을 편집 후 병합 스크립트를 다시 실행하세요.")
        print("=" * 60)
        return

    if pdf_only_flag:
        print("모드: PDF만 재생성 (기존 MD 유지)")
    elif generate_pdf_flag:
        print("모드: MD + PDF 생성")

    # 각 회차 처리
    success_count = 0
    for session in sessions_to_process:
        if merge_session(session, generate_pdf_flag, pdf_only=pdf_only_flag):
            success_count += 1

    print("\n" + "=" * 60)
    print(f"완료: {success_count}/{len(sessions_to_process)} 회차 통합 성공")
    print("=" * 60)


if __name__ == "__main__":
    main()
