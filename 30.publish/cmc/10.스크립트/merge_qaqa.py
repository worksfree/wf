#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
경영지도사 문제+예시답안 통합 스크립트 (문답문답 스타일)
문제와 예시답안을 페어로 구성: 문제1-답안1, 문제2-답안2, ...

사용법:
    python merge_qaqa.py all                # 모든 회차 처리
    python merge_qaqa.py 36                 # 특정 회차만 처리
    python merge_qaqa.py 36 40              # 여러 회차 처리
"""

import os
import sys
import io
import re
from pathlib import Path
from datetime import datetime

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
table { margin-left :auto; margin-right:auto; border: 1px solid; width: 100%; }
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

.page { page-break-after: always; }
</style>

<script type="module">
  import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@9/dist/mermaid.esm.min.mjs';
  mermaid.initialize({ startOnLoad: true });
</script>
"""

# MathJax 스크립트 (문서 끝에 추가)
MATHJAX_SCRIPT = """
<script type="text/javascript" src="http://cdn.mathjax.org/mathjax/latest/MathJax.js?config=TeX-AMS-MML_HTMLorMML"></script>
<script type="text/x-mathjax-config">
    MathJax.Hub.Config({ tex2jax: {inlineMath: [['$', '$']]}, messageStyle: "none" });
</script>
"""


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
    """개별 파일의 이미지 경로를 출력 파일 기준 경로로 변환"""
    res_path = get_res_path(session)

    # ./res/ 패턴 변환
    content = re.sub(r'src="\.\/res\/', f'src="{res_path}/', content)
    # ../res/ 패턴 변환
    content = re.sub(r'src="\.\.\/res\/', f'src="{res_path}/', content)

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

    return content


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
    """통합 마크다운 내용 생성 (문답문답 스타일)"""

    lines = []
    res_path = get_res_path(session)

    # 1. CSS 스타일
    lines.append(CSS_STYLE)
    lines.append("")

    # 2. 표지 이미지
    lines.append(f'<img src="{res_path}/{session}_bookcover.png">')
    lines.append("")
    lines.append('<div class="page"></div>')
    lines.append("")

    # 3. 저자소개 및 교재소개
    author_intro = read_template_file("저자소개.md")
    if author_intro:
        # 저자소개의 RPA-profile.png 경로도 변환
        author_intro = author_intro.replace(
            'src="./res/RPA-profile.png"',
            f'src="{res_path}/RPA-profile.png"'
        )
        lines.append(author_intro)
    lines.append("")
    lines.append('<div class="page"></div>')
    lines.append("")

    # 4. 목차 생성
    lines.append(f'# <div align="center"> {session}회 목차 </div>')

    for subject in SUBJECTS:
        lines.append(f"## [{session}회 {subject} 목차](#{session}회-{subject})")
        for i in range(1, 7):
            anchor = f"{session}회-{subject}-문제-{i}"
            lines.append(f"- [[문제{i} / 예시답안{i}]](#{anchor})")
    lines.append("")
    lines.append('<div class="page"></div>')
    lines.append("")

    # 5. 각 과목별 문제+답안 페어로 병합 (문답문답 스타일)
    for subject in SUBJECTS:
        lines.append(f"# {session}회 {subject}")
        lines.append("")

        for num in range(1, 7):
            # === 문제 섹션 ===
            lines.append(f"## {session}회 {subject} 문제 {num}")

            # 문제 내용
            question_content = read_question_file(session, subject, num)
            if question_content:
                # ## 헤더 제거 (중복 방지)
                question_content = re.sub(r'^## \d+회 .+ 문제 \d+\s*\n', '', question_content)
                lines.append(question_content)
            else:
                lines.append(f"### 【문제 {num}】")
                lines.append("")

            lines.append("")

            # === 예시답안 섹션 (같은 페이지에 이어서) ===
            lines.append(f"### 예시답안")
            lines.append("")

            answer_content = read_answer_file(session, subject, num)
            if answer_content:
                # ## 헤더 제거 (중복 방지)
                answer_content = re.sub(r'^## \d+회 .+ 문제 \d+ 예시답안\s*\n', '', answer_content)
                # [문제 바로가기] 링크 제거
                answer_content = re.sub(r'\[문제 바로가기\]\([^)]+\)\s*', '', answer_content)
                lines.append(answer_content)
            else:
                lines.append("> 답안 내용이 없습니다.")

            lines.append("")
            lines.append(f"[목차 바로가기](#{session}회-{subject}-목차)")
            lines.append("")

            # 문제 간 페이지 구분
            if num < 6:
                lines.append("----")
                lines.append("")
                lines.append('<div class="page"></div>')
                lines.append("")
                lines.append("----")
                lines.append("")

        # 과목 간 페이지 구분
        lines.append('<div class="page"></div>')
        lines.append("")

    # 6. 판권 정보
    copyright_info = read_template_file("판권.md")
    if copyright_info:
        # 템플릿 변수 치환
        today = datetime.now().strftime("%Y년 %m월 %d일")
        copyright_info = copyright_info.replace("{발행일}", today)
        # 바코드 이미지 경로 변환
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


def merge_session(session: int) -> bool:
    """특정 회차의 문제+답안을 통합"""

    session_dir = ANSWERS_DIR / f"{session}회"

    if not session_dir.exists():
        print(f"오류: {session}회 폴더가 존재하지 않습니다: {session_dir}")
        return False

    print(f"\n{session}회 문제+예시답안 통합 중... (문답문답 스타일)")

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

    # 통합 파일 저장 (파일명: _QnA.md)
    output_file = OUTPUT_DIR / f"{session}회_경영지도사_생산관리분야_QnA.md"

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(merged_content)

    file_size = output_file.stat().st_size
    print(f"  완료: {output_file} ({file_size:,} bytes)")

    return True


def main():
    """메인 실행 함수"""
    print("=" * 60)
    print("경영지도사 문제+예시답안 통합 스크립트 (문답문답 스타일)")
    print("=" * 60)

    # 사용 가능한 회차 확인
    available_sessions = get_available_sessions()
    print(f"\n사용 가능한 회차: {available_sessions}")

    # 처리할 회차 결정
    if len(sys.argv) > 1:
        # 명령줄 인자로 지정된 회차 처리
        sessions_to_process = []
        for arg in sys.argv[1:]:
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
        print("    python merge_qaqa.py all          # 모든 회차 처리")
        print("    python merge_qaqa.py 36           # 특정 회차만 처리")
        print("    python merge_qaqa.py 36 40        # 여러 회차 처리")
        return

    if not sessions_to_process:
        print("\n오류: 처리할 회차가 없습니다.")
        return

    print(f"\n처리할 회차: {sessions_to_process}")

    # 각 회차 처리
    success_count = 0
    for session in sessions_to_process:
        if merge_session(session):
            success_count += 1

    print("\n" + "=" * 60)
    print(f"완료: {success_count}/{len(sessions_to_process)} 회차 통합 성공")
    print("=" * 60)


if __name__ == "__main__":
    main()
