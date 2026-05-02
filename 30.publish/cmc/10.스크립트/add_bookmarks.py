import re
import sys
import io
from pathlib import Path
import pdfplumber
from pypdf import PdfWriter, PdfReader

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

BASE_DIR   = Path(r"D:\drive_files\10.worksfree\30.publish\cmc")
OUTPUT_DIR = BASE_DIR / "40.출판물"
TOC_BASE   = BASE_DIR / "30.예시답안"

SESSIONS = [36, 37, 38, 39, 40]

# 5개년통합본 PDF 파일명 패턴
COMBINED_PDF_PATTERN = "36-40회_경영지도사_생산관리분야_예시답안.pdf"
# 개별회차 PDF 파일명 패턴
SESSION_PDF_PATTERN  = "{n}회_경영지도사_생산관리분야_예시답안.pdf"


def parse_toc(toc_path: str) -> list:
    """목차.md에서 북마크 구조 추출
    Returns: [(level, display_title, search_keyword), ...]
      level 1 = ## 헤딩
      level 2 = - 리스트 항목
    """
    entries = []
    with open(toc_path, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip()

            # ## [title](#anchor) 형태
            m = re.match(r'^##\s+\[([^\]]+)\]\(#([^)]+)\)', line)
            if m:
                display = m.group(1).strip().replace(' 목차', '').strip()
                anchor  = m.group(2).strip()
                base    = anchor.replace('-', ' ')   # "40회 생산관리"
                keyword = base + " 문제"              # "40회 생산관리 문제"
                entries.append((1, display, keyword))
                continue

            # - [text](#anchor) 또는 - [[text]](#anchor) 형태
            m = re.match(r'^\s*-\s+\[(.+)\]\(#([^)]+)\)', line)
            if m:
                display = m.group(1).strip()
                anchor  = m.group(2).strip()
                keyword = anchor.replace('-', ' ')
                entries.append((2, display, keyword))
                continue

    return entries


def normalize(text: str) -> str:
    """공백·줄바꿈을 단일 공백으로 정규화 + 숫자-회 사이 공백 제거 (비교용)
    예: "36 회 생산관리" → "36회 생산관리"
    """
    # 숫자와 '회' 사이 공백 제거 (PDF 추출 시 분리되는 패턴)
    text = re.sub(r'(\d)\s+(회)', r'\1\2', text)
    return re.sub(r'\s+', ' ', text).strip()


def extract_pages_text(pdf_path: str) -> list:
    """pdfplumber + pypdf 두 엔진으로 텍스트 추출 후 합산
    한 엔진이 특정 페이지를 놓쳐도 다른 엔진이 보완"""
    n = None

    # 1) pdfplumber
    plumber_texts = []
    with pdfplumber.open(pdf_path) as pdf:
        n = len(pdf.pages)
        for page in pdf.pages:
            plumber_texts.append(normalize(page.extract_text() or ""))

    # 2) pypdf
    reader = PdfReader(pdf_path)
    pypdf_texts = []
    for page in reader.pages:
        try:
            pypdf_texts.append(normalize(page.extract_text() or ""))
        except Exception:
            pypdf_texts.append("")

    # 3) 두 결과 합산
    combined = [plumber_texts[i] + " " + pypdf_texts[i] for i in range(n)]
    return combined


def find_pages(pdf_path: str, entries: list, debug: bool = False) -> list:
    """각 항목이 PDF 몇 페이지에 있는지 검색"""
    pages_norm = extract_pages_text(pdf_path)

    if debug:
        print("\n  [DEBUG] 페이지별 추출 텍스트 앞 80자:")
        for i, t in enumerate(pages_norm):
            print(f"    p.{i+1:02d}: {t[:80]}")

    results = []
    for level, display, keyword in entries:
        norm_kw = normalize(keyword)
        # 키워드 끝이 숫자로 끝나는 경우 (?!\d) lookahead 추가
        # 예: "문제 3" 이 "문제 38회" 에 false-match 되는 것 방지
        pattern = re.escape(norm_kw) + (r'(?!\d)' if norm_kw[-1].isdigit() else '')
        found = False
        for i, norm_text in enumerate(pages_norm):
            if re.search(pattern, norm_text):
                results.append((level, display, i))
                found = True
                break
        if not found:
            print(f"  ⚠ 페이지 못 찾음: {display}  (검색어: {keyword})")
    return results


def add_bookmarks(pdf_path: str, bookmark_pages: list, out_path: str):
    """PDF에 북마크 삽입 (내부 링크·어노테이션 보존)"""
    writer = PdfWriter(clone_from=pdf_path)

    parent_map = {}
    for level, title, page_num in bookmark_pages:
        parent = parent_map.get(level - 1)
        ref = writer.add_outline_item(title, page_num, parent=parent)
        parent_map[level] = ref
        for l in range(level + 1, 4):
            parent_map.pop(l, None)

    with open(out_path, "wb") as f:
        writer.write(f)
    print(f"\n완료: {out_path}")


def get_session_pdf(n: int) -> Path:
    return OUTPUT_DIR / SESSION_PDF_PATTERN.format(n=n)


def get_session_toc(n: int) -> Path:
    return TOC_BASE / f"{n}회" / "목차.md"


def bookmarked_path(pdf_path: Path) -> Path:
    return pdf_path.with_name(pdf_path.stem + "_bookmarked.pdf")


# ─────────────────────────────────────────────────────────────
# 처리 함수
# ─────────────────────────────────────────────────────────────

def process_session(n: int, debug: bool = False):
    """단일 회차 북마크 삽입"""
    pdf_in  = get_session_pdf(n)
    toc_md  = get_session_toc(n)
    pdf_out = bookmarked_path(pdf_in)

    if not pdf_in.exists():
        print(f"  ⚠ PDF 없음: {pdf_in}")
        return
    if not toc_md.exists():
        print(f"  ⚠ 목차.md 없음: {toc_md}")
        return

    print(f"\n{'='*60}")
    print(f"  {n}회 처리 중...")
    print(f"  PDF : {pdf_in.name}")
    print(f"  TOC : {toc_md}")

    print("\n1. 목차.md 파싱 중...")
    entries = parse_toc(str(toc_md))
    print(f"   → {len(entries)}개 항목 발견")
    for level, display, keyword in entries:
        print(f"   {'  '*(level-1)}{'##' if level==1 else '-'} {display}  (검색어: {keyword})")

    print("\n2. PDF 페이지 매칭 중...")
    bookmark_pages = find_pages(str(pdf_in), entries, debug=debug)
    for level, title, page in bookmark_pages:
        print(f"   {'  '*(level-1)}p.{page+1:02d}  {title}")

    print("\n3. 북마크 삽입 중...")
    add_bookmarks(str(pdf_in), bookmark_pages, str(pdf_out))


def process_combined(debug: bool = False):
    """5개년통합본 북마크 삽입"""
    pdf_in  = OUTPUT_DIR / COMBINED_PDF_PATTERN
    pdf_out = bookmarked_path(pdf_in)

    if not pdf_in.exists():
        print(f"  ⚠ 통합본 PDF 없음: {pdf_in}")
        return

    print(f"\n{'='*60}")
    print(f"  5개년통합본 처리 중...")
    print(f"  PDF : {pdf_in.name}")

    # 모든 회차 목차.md 합산
    print("\n1. 목차.md 파싱 중...")
    all_entries = []
    for n in SESSIONS:
        toc_md = get_session_toc(n)
        if not toc_md.exists():
            print(f"   ⚠ {n}회 목차.md 없음, 스킵")
            continue
        entries = parse_toc(str(toc_md))
        all_entries.extend(entries)
        print(f"   {n}회: {len(entries)}개 항목")

    print(f"   → 총 {len(all_entries)}개 항목")

    print("\n2. PDF 페이지 매칭 중...")
    bookmark_pages = find_pages(str(pdf_in), all_entries, debug=debug)
    for level, title, page in bookmark_pages:
        print(f"   {'  '*(level-1)}p.{page+1:02d}  {title}")

    print("\n3. 북마크 삽입 중...")
    add_bookmarks(str(pdf_in), bookmark_pages, str(pdf_out))


# ─────────────────────────────────────────────────────────────
# 진입점
# ─────────────────────────────────────────────────────────────

def main():
    debug = "--debug" in sys.argv
    args  = [a for a in sys.argv[1:] if a != "--debug"]

    if not args:
        print("사용법:")
        print("  python add_bookmarks.py <N>        # 특정 회차 (예: 40)")
        print("  python add_bookmarks.py all        # 모든 회차 개별 처리")
        print("  python add_bookmarks.py combined   # 5개년통합본")
        print("  python add_bookmarks.py all combined   # 전부")
        print("  --debug : 페이지 텍스트 미리보기")
        return

    do_all      = "all"      in args
    do_combined = "combined" in args
    sessions    = [int(a) for a in args if a.isdigit()]

    if do_all:
        sessions = SESSIONS

    for n in sessions:
        process_session(n, debug=debug)

    if do_combined:
        process_combined(debug=debug)


if __name__ == "__main__":
    main()
