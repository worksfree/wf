#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
경영지도사 기출문제 PDF 텍스트 추출 스크립트

PDF 파일에서 텍스트를 추출하여 마크다운 파일로 저장합니다.
스캔된 PDF의 경우 OCR이 필요합니다.

필요 라이브러리:
    pip install pymupdf      # PDF 텍스트 추출 (fitz)
    pip install pytesseract  # OCR (선택사항)
    pip install pdf2image    # PDF를 이미지로 변환 (OCR용)

OCR 사용 시 Tesseract 설치 필요:
    https://github.com/UB-Mannheim/tesseract/wiki
    설치 후 PATH에 추가하거나 pytesseract.pytesseract.tesseract_cmd 설정

사용법:
    python extract_questions_from_pdf.py                # 모든 PDF 처리
    python extract_questions_from_pdf.py 36             # 특정 회차만 처리
    python extract_questions_from_pdf.py --ocr          # OCR 모드로 처리
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
BASE_DIR = Path(r"D:\drive_files\10.worksfree\70.publish\cmc")
PDF_DIR = BASE_DIR / "20_기출문제"
OUTPUT_DIR = PDF_DIR  # 각 회차 폴더에 문제 파일 생성

# 과목 정보
SUBJECTS = {
    "생산관리": 1,
    "품질경영": 2,
    "경영과학": 3
}

# OCR 사용 여부
USE_OCR = "--ocr" in sys.argv


def check_dependencies():
    """필요 라이브러리 확인"""
    missing = []

    try:
        import fitz  # pymupdf
    except ImportError:
        missing.append("pymupdf (pip install pymupdf)")

    if USE_OCR:
        try:
            import pytesseract
        except ImportError:
            missing.append("pytesseract (pip install pytesseract)")

        try:
            from pdf2image import convert_from_path
        except ImportError:
            missing.append("pdf2image (pip install pdf2image)")

    if missing:
        print("다음 라이브러리를 설치해주세요:")
        for lib in missing:
            print(f"  - {lib}")
        return False

    return True


def extract_text_from_pdf(pdf_path: Path) -> str:
    """PDF에서 텍스트 추출"""
    import fitz

    text = ""
    doc = fitz.open(pdf_path)

    for page_num, page in enumerate(doc):
        page_text = page.get_text()
        if page_text.strip():
            text += f"\n--- 페이지 {page_num + 1} ---\n"
            text += page_text

    doc.close()
    return text


def extract_text_with_ocr(pdf_path: Path) -> str:
    """OCR을 사용하여 PDF에서 텍스트 추출"""
    import pytesseract
    from pdf2image import convert_from_path

    # Tesseract 경로 설정 (필요시 수정)
    # pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

    text = ""

    # PDF를 이미지로 변환
    print(f"  PDF를 이미지로 변환 중...")
    images = convert_from_path(pdf_path, dpi=300)

    for i, image in enumerate(images):
        print(f"  페이지 {i + 1}/{len(images)} OCR 처리 중...")
        page_text = pytesseract.image_to_string(image, lang='kor+eng')
        if page_text.strip():
            text += f"\n--- 페이지 {i + 1} ---\n"
            text += page_text

    return text


def parse_questions(text: str, session: int) -> dict:
    """
    추출된 텍스트에서 과목별/문제별로 분리

    반환 형식:
    {
        "생산관리": {1: "문제내용", 2: "문제내용", ...},
        "품질경영": {...},
        "경영과학": {...}
    }
    """
    result = {subject: {} for subject in SUBJECTS}

    # 텍스트 패턴 분석 (실제 PDF 구조에 따라 조정 필요)
    # 일반적인 패턴: "【문제 1】" 또는 "문제 1." 등

    # 과목 구분 패턴 (예시)
    subject_patterns = {
        "생산관리": r"생산관리|생산\s*관리",
        "품질경영": r"품질경영|품질\s*경영",
        "경영과학": r"경영과학|경영\s*과학|OR"
    }

    # 문제 구분 패턴
    question_pattern = r"【문제\s*(\d+)】|문제\s*(\d+)[.\s]|\[문제\s*(\d+)\]"

    # 현재 과목 추적
    current_subject = None
    current_question = None
    current_content = []

    lines = text.split('\n')

    for line in lines:
        # 과목 확인
        for subject, pattern in subject_patterns.items():
            if re.search(pattern, line, re.IGNORECASE):
                # 이전 내용 저장
                if current_subject and current_question and current_content:
                    result[current_subject][current_question] = '\n'.join(current_content)

                current_subject = subject
                current_question = None
                current_content = []
                break

        # 문제 번호 확인
        match = re.search(question_pattern, line)
        if match:
            # 이전 문제 저장
            if current_subject and current_question and current_content:
                result[current_subject][current_question] = '\n'.join(current_content)

            # 새 문제 시작
            question_num = match.group(1) or match.group(2) or match.group(3)
            current_question = int(question_num)
            current_content = [line]
        elif current_question:
            current_content.append(line)

    # 마지막 문제 저장
    if current_subject and current_question and current_content:
        result[current_subject][current_question] = '\n'.join(current_content)

    return result


def create_question_md(session: int, subject: str, question_num: int, content: str) -> str:
    """39회 형식에 맞는 마크다운 생성"""

    md_lines = [
        f"## {session}회 {subject} 문제 {question_num}",
        "",
        content,
        "",
        "---",
        "",
        f"[예시답안 바로가기](#{session}회-{subject}-문제-{question_num}-예시답안)",
        "",
        f"[목차 바로가기](#{session}회-{subject}-목차)",
        ""
    ]

    return '\n'.join(md_lines)


def save_question_files(session: int, questions: dict):
    """문제 파일 저장"""
    session_dir = OUTPUT_DIR / f"{session}회"

    for subject, subject_questions in questions.items():
        if not subject_questions:
            continue

        subject_dir = session_dir / subject
        subject_dir.mkdir(parents=True, exist_ok=True)

        for q_num, content in subject_questions.items():
            if not content.strip():
                continue

            md_content = create_question_md(session, subject, q_num, content)
            output_file = subject_dir / f"문제{q_num}.md"

            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(md_content)

            print(f"    생성: {output_file.name}")


def find_pdf_files():
    """PDF 파일 탐색"""
    pdf_files = {}

    if not PDF_DIR.exists():
        print(f"폴더가 존재하지 않습니다: {PDF_DIR}")
        return pdf_files

    # 회차별 PDF 파일 찾기
    for item in PDF_DIR.iterdir():
        if item.is_dir() and item.name.endswith("회"):
            session_str = item.name.replace("회", "")
            if session_str.isdigit():
                session = int(session_str)
                # 해당 폴더 내 PDF 파일 찾기
                for pdf_file in item.glob("*.pdf"):
                    if session not in pdf_files:
                        pdf_files[session] = []
                    pdf_files[session].append(pdf_file)

    return pdf_files


def process_session(session: int, pdf_files: list):
    """특정 회차 처리"""
    print(f"\n📄 {session}회 기출문제 처리 중...")

    for pdf_file in pdf_files:
        print(f"  파일: {pdf_file.name}")

        try:
            if USE_OCR:
                text = extract_text_with_ocr(pdf_file)
            else:
                text = extract_text_from_pdf(pdf_file)

            if not text.strip():
                print(f"    ⚠️  텍스트 추출 실패 (스캔 PDF일 수 있음, --ocr 옵션 사용)")
                continue

            # 추출된 텍스트를 raw 파일로 저장 (디버깅용)
            raw_output = PDF_DIR / f"{session}회" / f"extracted_text.txt"
            with open(raw_output, 'w', encoding='utf-8') as f:
                f.write(text)
            print(f"    추출 텍스트 저장: {raw_output.name}")

            # 문제 파싱
            questions = parse_questions(text, session)

            # 문제 파일 저장
            save_question_files(session, questions)

            # 결과 요약
            total = sum(len(q) for q in questions.values())
            print(f"    ✅ 총 {total}개 문제 추출")

        except Exception as e:
            print(f"    ❌ 오류 발생: {e}")


def main():
    """메인 실행 함수"""
    print("=" * 60)
    print("경영지도사 기출문제 PDF 추출 스크립트")
    print("=" * 60)

    if USE_OCR:
        print("\n🔍 OCR 모드 활성화")

    # 라이브러리 확인
    if not check_dependencies():
        print("\n❌ 필요한 라이브러리가 설치되지 않았습니다.")
        return

    # PDF 파일 탐색
    pdf_files = find_pdf_files()

    if not pdf_files:
        print("\n❌ PDF 파일을 찾을 수 없습니다.")
        return

    print(f"\n📋 발견된 회차: {sorted(pdf_files.keys())}")

    # 처리할 회차 결정
    sessions_to_process = []

    for arg in sys.argv[1:]:
        if arg.isdigit():
            session = int(arg)
            if session in pdf_files:
                sessions_to_process.append(session)
            else:
                print(f"⚠️  {session}회 PDF를 찾을 수 없습니다.")

    if not sessions_to_process:
        sessions_to_process = sorted(pdf_files.keys())

    print(f"\n🎯 처리할 회차: {sessions_to_process}")

    # 각 회차 처리
    for session in sessions_to_process:
        process_session(session, pdf_files[session])

    print("\n" + "=" * 60)
    print("✅ 처리 완료")
    print("=" * 60)
    print("\n💡 참고:")
    print("  - 텍스트가 제대로 추출되지 않으면 --ocr 옵션을 사용하세요")
    print("  - OCR 사용 시 Tesseract 설치가 필요합니다")
    print("  - 추출된 텍스트는 extracted_text.txt 파일에서 확인할 수 있습니다")
    print("  - 문제 분리가 정확하지 않을 수 있으며, 수동 검토가 필요합니다")


if __name__ == "__main__":
    main()
