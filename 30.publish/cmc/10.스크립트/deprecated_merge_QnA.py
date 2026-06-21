#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
경영지도사 문제+예시답안 통합 스크립트 (pandoc + LaTeX 버전)
문제와 예시답안을 페어로 구성하여 PDF 자동 생성

사용법:
    python merge_QnA.py all                # 모든 회차 처리
    python merge_QnA.py 36                 # 특정 회차만 처리
    python merge_QnA.py 36 40              # 여러 회차 처리
"""

import os
import sys
import io
import re
import subprocess
from pathlib import Path
from datetime import datetime

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


def convert_latex_delimiters(content: str) -> str:
    r"""LaTeX 수식 구분자 변환: \[...\] -> $$...$$, \(...\) -> $...$"""
    # \[...\] -> $$...$$ (display math)
    content = content.replace('\\[\n', '$$\n')
    content = content.replace('\\[', '$$')
    content = content.replace('\n\\]', '\n$$')
    content = content.replace('\\]', '$$')
    # \(...\) -> $...$ (inline math)
    content = content.replace('\\(', '$')
    content = content.replace('\\)', '$')
    return content


def convert_image_paths(content: str, session: int) -> str:
    """이미지 경로를 절대 경로로 변환하고 HTML img를 마크다운으로 변환"""
    # 예시답안의 res 폴더 경로
    answer_res_dir = ANSWERS_DIR / f"{session}회" / "res"
    # 기출문제의 res 폴더 경로
    question_res_dir = QUESTIONS_DIR / f"{session}회" / "res"

    def get_absolute_path(src):
        """상대 경로를 절대 경로로 변환"""
        if src.startswith('./res/') or src.startswith('res/'):
            filename = src.replace('./res/', '').replace('res/', '')
            # 예시답안 res 폴더에서 먼저 찾기
            abs_path = answer_res_dir / filename
            if abs_path.exists():
                return str(abs_path).replace('\\', '/')
            # 기출문제 res 폴더에서 찾기
            abs_path = question_res_dir / filename
            if abs_path.exists():
                return str(abs_path).replace('\\', '/')
        return src

    def replace_html_img(match):
        """HTML <img> 태그를 마크다운 이미지로 변환"""
        full_tag = match.group(0)

        # src 속성 추출
        src_match = re.search(r'src=["\']([^"\']+)["\']', full_tag)
        if not src_match:
            return full_tag
        src = src_match.group(1)

        # alt 속성 추출 (없으면 빈 문자열)
        alt_match = re.search(r'alt=["\']([^"\']*)["\']', full_tag)
        alt = alt_match.group(1) if alt_match else ""

        # 절대 경로로 변환
        abs_path = get_absolute_path(src)

        # 마크다운 이미지 문법으로 변환
        return f'![{alt}]({abs_path})'

    # <img ...> 태그를 마크다운으로 변환 (주석 내부 제외)
    # 주석이 아닌 <img> 태그만 처리
    content = re.sub(r'(?<!<!--\s)<img[^>]+>', replace_html_img, content)

    # ![alt](path) 마크다운 이미지의 상대 경로를 절대 경로로 변환
    def replace_md_img(match):
        alt = match.group(1)
        src = match.group(2)
        abs_path = get_absolute_path(src)
        return f'![{alt}]({abs_path})'

    content = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', replace_md_img, content)

    return content


def convert_html_table_to_markdown(content: str) -> str:
    """HTML 테이블을 마크다운 테이블로 변환"""

    def parse_html_table(table_html):
        """HTML 테이블을 파싱하여 마크다운으로 변환"""
        rows = []

        # 행 추출
        row_pattern = re.compile(r'<tr[^>]*>(.*?)</tr>', re.DOTALL | re.IGNORECASE)
        cell_pattern = re.compile(r'<(th|td)[^>]*>(.*?)</\1>', re.DOTALL | re.IGNORECASE)

        for row_match in row_pattern.finditer(table_html):
            row_content = row_match.group(1)
            cells = []
            for cell_match in cell_pattern.finditer(row_content):
                cell_text = cell_match.group(2)
                # HTML 태그 제거 및 정리
                cell_text = re.sub(r'<[^>]+>', '', cell_text)
                cell_text = cell_text.strip()
                cell_text = ' '.join(cell_text.split())  # 연속 공백 정리
                cells.append(cell_text)
            if cells:
                rows.append(cells)

        if not rows:
            return ""

        # 마크다운 테이블 생성
        max_cols = max(len(row) for row in rows)

        # 모든 행의 열 수 맞추기
        for row in rows:
            while len(row) < max_cols:
                row.append("")

        md_lines = []
        for i, row in enumerate(rows):
            md_lines.append("| " + " | ".join(row) + " |")
            if i == 0:  # 헤더 구분선
                md_lines.append("|" + "|".join(["------"] * max_cols) + "|")

        return "\n".join(md_lines)

    # <table>...</table> 패턴 찾아서 변환
    table_pattern = re.compile(r'<table[^>]*>.*?</table>', re.DOTALL | re.IGNORECASE)

    def replace_table(match):
        table_html = match.group(0)
        md_table = parse_html_table(table_html)
        return md_table if md_table else table_html

    content = table_pattern.sub(replace_table, content)

    return content


def build_author_section() -> str:
    """저자소개 섹션 생성 (마크다운 형식)"""
    return """# 저자 소개

- 경영지도사 생산관리분야
- 자동화 장비 제조업 프로세스 개선 내부 컨설팅 경력
- 제조업 설계 및 MCT 단순 반복 업무 자동화(RPA) 프로그램 개발
  - 어셈블리 BOM 엑셀 저장 자동화 프로그램
  - 8만 여개 구매품 속성 2주만에 정리하기
  - 이드로잉스 뷰어 대량 출력 자동화 프로그램
  - 구글 드라이브 기반 인터넷 정보 자동 업데이트
  - 자동화(RPA) 프로그램은 아래 URL 참고: https://www.worksfree.com
- 소프트웨어 분야 개발 및 PM 경력
- 프로젝트 관리 전문가(PMP from PMI)
- IITP 평가위원, NIPA 평가위원

# 교재 소개

- 본 교재는 필자가 경영지도사 2차 수험 생활을 하며 기출문제를 풀고 아래 명시된 수험 교재 학습 및 인터넷 정보를 참조하여 정리한 내용입니다.
  - 생산관리 : 생산운영관리 [법문사]
  - 품질경영 : 품질경영론 [KSAM]
  - 경영과학 : 4차 산업혁명 시대의 EXCEL 경영과학 [박영사]
- 목차는 3 페이지에 제공되며 본문 내의 파랑색으로 보이는 모든 문구는 문서 내부 링크로서 클릭하면 문제, 예시답안, 목차로 이동합니다.
- 예시답안은 설명을 위해 단계별로 내용이 작성되어 불필요하게 긴 예시답안이 있는데 실제 답안 작성시에는 꼭 필요한 경우만 풀이 과정을 단계별로 작성해도 됩니다.
- 예시답안의 내용에 대한 개정 의견이나 시험 관련된 문의 사항은 아래 이메일로 보내주시기 바라며 수험생들의 고득점을 기원합니다.
- 이메일 : insung.lee@worksfree.kr

"""


def build_copyright_section(session: int) -> str:
    """판권 섹션 생성 (마크다운 테이블 형식)"""
    publish_date = datetime.now().strftime("%Y년 %m월 %d일")
    return f"""# 판권

| 항목 | 내용 |
|------|------|
| 저자 | 이인성 |
| 펴낸이 | 웍스프리 |
| 펴낸곳 | 웍스프리 |
| 발행일 | {publish_date} |
| 이메일 | insung.lee@worksfree.kr |
| 가격 | 6,600원 |

본 책은 저작자의 지적 재산으로서 무단 전제와 복제를 금합니다.
"""


def remove_page_breaks(content: str) -> str:
    """기존 페이지 구분 표시 제거"""
    # <div class="page"></div> 제거
    content = re.sub(r'<div class="page"></div>\s*', '', content)
    # ---- 수평선 제거 (목차 바로가기 주변)
    content = re.sub(r'\n----\n', '\n', content)
    # [목차 바로가기] 링크 제거
    content = re.sub(r'\[목차 바로가기\]\([^)]+\)\s*', '', content)
    # [예시답안 바로가기] 링크 제거
    content = re.sub(r'\[예시답안 바로가기\]\([^)]+\)\s*', '', content)
    # [문제 바로가기] 링크 제거
    content = re.sub(r'\[문제 바로가기\]\([^)]+\)\s*', '', content)
    # 연속된 빈 줄 정리 (3개 이상 -> 2개)
    content = re.sub(r'\n{3,}', '\n\n', content)
    return content.strip()


def read_file_safe(filepath: Path) -> str:
    """파일 안전하게 읽기"""
    if filepath.exists():
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    else:
        print(f"  경고: {filepath} 파일을 찾을 수 없습니다.")
        return ""


def get_available_sessions() -> list:
    """사용 가능한 회차 목록 반환"""
    sessions = []
    if ANSWERS_DIR.exists():
        for folder in ANSWERS_DIR.iterdir():
            if folder.is_dir() and folder.name.endswith('회'):
                try:
                    session_num = int(folder.name.replace('회', ''))
                    sessions.append(session_num)
                except ValueError:
                    pass
    return sorted(sessions)


def read_question(session: int, subject: str, num: int) -> str:
    """문제 파일 읽기"""
    question_file = QUESTIONS_DIR / f"{session}회" / subject / f"문제{num}.md"
    content = read_file_safe(question_file)
    if content:
        content = remove_page_breaks(content)
        content = convert_latex_delimiters(content)
        content = convert_image_paths(content, session)
        content = convert_html_table_to_markdown(content)
    return content


def read_answer(session: int, subject: str, num: int) -> str:
    """예시답안 파일 읽기"""
    answer_file = ANSWERS_DIR / f"{session}회" / subject / f"예시답안{num}.md"
    content = read_file_safe(answer_file)
    if content:
        content = remove_page_breaks(content)
        content = convert_latex_delimiters(content)
        content = convert_image_paths(content, session)
        content = convert_html_table_to_markdown(content)
        # ## N회 과목 문제 N 예시답안 헤더 제거 (문제와 중복 방지)
        content = re.sub(r'^## \d+회 .+ 문제 \d+ 예시답안\s*\n', '', content)
    return content


def build_toc(session: int) -> str:
    """목차 생성"""
    toc = f"# {session}회 경영지도사 생산관리분야 목차\n\n"

    for subject in SUBJECTS:
        toc += f"## {subject}\n\n"
        for num in range(1, 7):
            toc += f"- 문제 {num} / 예시답안 {num}\n"
        toc += "\n"

    return toc


def build_subject_content(session: int, subject: str) -> str:
    """과목별 콘텐츠 생성 (문제+답안 페어)"""
    content = f"# {session}회 {subject}\n\n"

    for num in range(1, 7):
        # 문제
        question = read_question(session, subject, num)
        if question:
            content += f"{question}\n\n"

        # 예시답안
        answer = read_answer(session, subject, num)
        if answer:
            content += f"### 예시답안\n\n{answer}\n\n"

        # 문제 간 구분선
        if num < 6:
            content += "---\n\n"

    return content


def build_document(session: int) -> str:
    """전체 문서 생성"""
    doc = ""

    # 표지
    doc += f"# 제{session}회 경영지도사 2차 실기시험\n\n"
    doc += "# 생산관리분야 문제 및 예시답안\n\n"
    doc += "\\newpage\n\n"

    # 저자소개 (마크다운 형식 사용)
    doc += build_author_section()
    doc += "\\newpage\n\n"

    # 목차 (pandoc --toc 사용하므로 수동 목차 생략)

    # 과목별 내용
    for i, subject in enumerate(SUBJECTS):
        if i > 0:
            doc += "\\newpage\n\n"
        doc += build_subject_content(session, subject)

    # 판권 (마크다운 테이블 형식 사용)
    doc += "\\newpage\n\n"
    doc += build_copyright_section(session)

    return doc


def generate_pdf(md_file: Path, pdf_file: Path) -> bool:
    """pandoc으로 PDF 생성"""
    cmd = [
        'pandoc',
        str(md_file),
        '-o', str(pdf_file),
        '--pdf-engine=xelatex',
        '-V', 'documentclass=article',
        '-V', 'papersize=a4',
        '-V', 'geometry:top=2.5cm,bottom=2.5cm,left=2cm,right=2cm',
        '-V', 'mainfont=Malgun Gothic',
        '-V', 'monofont=Malgun Gothic',
        '-V', 'fontsize=11pt',
        '-V', 'lang=ko',
        '-V', 'linestretch=1.3',
        '-V', 'toc-title=목 차',
        '--toc',
        '--toc-depth=2',
    ]

    try:
        print(f"  PDF 생성 중: {pdf_file.name}")
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
        if result.returncode == 0:
            print(f"  PDF 생성 완료: {pdf_file} ({pdf_file.stat().st_size:,} bytes)")
            return True
        else:
            print(f"  PDF 생성 실패: {result.stderr[:500]}")
            return False
    except FileNotFoundError:
        print("  PDF 생성 오류: 'pandoc' 또는 'xelatex'를 찾을 수 없습니다.")
        print("  Pandoc과 MiKTeX (또는 TeX Live)가 설치되어 있고 시스템 PATH에 추가되었는지 확인하세요.")
        return False
    except Exception as e:
        print(f"  PDF 생성 오류: {e}")
        return False


def process_session(session: int) -> bool:
    """회차 처리"""
    print(f"\n{session}회 처리 중...")

    # 문서 생성
    doc = build_document(session)

    # MD 파일 저장
    md_filename = f"{session}회_경영지도사_생산관리분야_QnA.md"
    md_file = OUTPUT_DIR / md_filename

    with open(md_file, 'w', encoding='utf-8') as f:
        f.write(doc)
    print(f"  MD 저장: {md_file} ({md_file.stat().st_size:,} bytes)")

    # PDF 생성
    pdf_filename = f"{session}회_경영지도사_생산관리분야_QnA.pdf"
    pdf_file = OUTPUT_DIR / pdf_filename

    return generate_pdf(md_file, pdf_file)


def main():
    """메인 함수"""
    print("=" * 60)
    print("경영지도사 문제+예시답안 통합 (pandoc + LaTeX)")
    print("=" * 60)

    # 사용 가능한 회차 확인
    available_sessions = get_available_sessions()
    print(f"\n사용 가능한 회차: {available_sessions}")

    # 처리할 회차 결정
    if len(sys.argv) > 1:
        sessions_to_process = []
        for arg in sys.argv[1:]:
            if arg.lower() == 'all':
                sessions_to_process = available_sessions
                break
            elif arg.isdigit():
                session = int(arg)
                if session in available_sessions:
                    sessions_to_process.append(session)
                else:
                    print(f"경고: {session}회 폴더가 존재하지 않습니다.")
    else:
        print("\n사용법:")
        print("    python merge_QnA.py all          # 모든 회차 처리")
        print("    python merge_QnA.py 36           # 특정 회차만 처리")
        print("    python merge_QnA.py 36 40        # 여러 회차 처리")
        return

    if not sessions_to_process:
        print("\n오류: 처리할 회차가 없습니다.")
        return

    print(f"\n처리할 회차: {sessions_to_process}")

    # 출력 디렉토리 확인
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 각 회차 처리
    success_count = 0
    for session in sessions_to_process:
        if process_session(session):
            success_count += 1

    print("\n" + "=" * 60)
    print(f"완료: {success_count}/{len(sessions_to_process)} 회차 처리 성공")
    print("=" * 60)


if __name__ == "__main__":
    main()
