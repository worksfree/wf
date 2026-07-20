# -*- coding: utf-8 -*-
"""학습자료 PDF에서 텍스트를 추출해 extracted/ 폴더에 .txt로 저장한다.

- pypdf 우선 (빠름), 텍스트가 거의 없으면 pdfplumber로 재시도
- 페이지당 추출 문자 수가 극히 적으면 스캔본(이미지 PDF)으로 판정하고 SKIP 표기
- 갱신 시 동일 스크립트 재실행 (이미 추출된 파일은 --force 없으면 건너뜀)
"""
import sys
import io
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

SOURCE_DIR = Path(r"D:\drive_files\30.사업자 및 지도사\학습자료")
OUT_DIR = Path(__file__).resolve().parent.parent / "extracted"

# 1단계 우선순위: 지원제도 원천자료 (강의교재 Part1~6, 서식류 제외)
PRIORITY = [
    "2026년도 중소기업 조세지원.pdf",
    r"런인베스트\노무관리, 고용지원금\2026 고용장려금 지원제도.pdf",
    r"런인베스트\노무관리, 고용지원금\니즈환기시리즈8_2026년 CEO가 알아야할 주요 고용지원금.pdf",
    r"런인베스트\노무관리, 고용지원금\251231 (보도참고) 2026년부터 이렇게 달라집니다(고용노동부).pdf",
    r"런인베스트\연구소, 인징, 정책자금\2024년도 중소벤처기업 지원사업(유관기관).pdf",
    r"런인베스트\연구소, 인징, 정책자금\2024년도 중소벤처기업 지원사업(중소벤처기업부).pdf",
    r"런인베스트\연구소, 인징, 정책자금\기업부설연구소 및 연구개발전담부서 신고에 관한 업무편람(2024년).pdf",
    r"런인베스트\연구소, 인징, 정책자금\벤처기업확인제도 가이드북('24년 개정판).pdf",
    r"런인베스트\연구소, 인징, 정책자금\벤처확인기업 우대지원제도 세부내용.pdf",
    r"런인베스트\법인전환 컨설팅\니즈환기시리즈5_ 법인전환을_고민하고 있다면.pdf",
    r"런인베스트\법인전환 컨설팅\4. 법인전환컨설팅 안내 리플릿.pdf",
    r"런인베스트\법인전환 컨설팅\5. 법인전환여부 결정 진단표.pdf",
    r"런인베스트\가지급금, 가수금\가지급금 컨설팅(원본).pdf",
    r"런인베스트\가지급금, 가수금\가수금 컨설팅(원본).pdf",
]

MIN_CHARS_PER_PAGE = 30  # 이 미만이면 스캔본으로 판정


def extract_pypdf(path: Path) -> tuple[str, int]:
    from pypdf import PdfReader
    reader = PdfReader(str(path))
    pages = [p.extract_text() or "" for p in reader.pages]
    return "\n\n".join(pages), len(pages)


def extract_pdfplumber(path: Path) -> tuple[str, int]:
    import pdfplumber
    texts = []
    with pdfplumber.open(str(path)) as pdf:
        for p in pdf.pages:
            texts.append(p.extract_text() or "")
    return "\n\n".join(texts), len(texts)


def main():
    force = "--force" in sys.argv
    OUT_DIR.mkdir(exist_ok=True)
    results = []
    for rel in PRIORITY:
        src = SOURCE_DIR / rel
        if not src.exists():
            results.append((rel, "MISSING", 0, 0))
            continue
        out = OUT_DIR / (src.stem + ".txt")
        if out.exists() and not force:
            results.append((rel, "CACHED", out.stat().st_size, 0))
            continue
        try:
            text, n_pages = extract_pypdf(src)
            if n_pages and len(text) / n_pages < MIN_CHARS_PER_PAGE:
                text, n_pages = extract_pdfplumber(src)
            if n_pages and len(text) / n_pages < MIN_CHARS_PER_PAGE:
                results.append((rel, "SCANNED(스캔본-추출불가)", len(text), n_pages))
                continue
            out.write_text(text, encoding="utf-8")
            results.append((rel, "OK", len(text), n_pages))
        except Exception as e:
            results.append((rel, f"ERROR: {e}", 0, 0))

    print(f"{'상태':<24} {'문자수':>10} {'페이지':>6}  파일")
    for rel, status, chars, pages in results:
        print(f"{status:<24} {chars:>10,} {pages:>6}  {rel}")


if __name__ == "__main__":
    main()
