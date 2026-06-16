"""
PDF 병합 스크립트 (pymupdf 사용)
각 HTML 페이지를 개별 PDF로 변환 후 순서대로 병합
"""
import fitz  # pymupdf 1.27+

# 병합할 PDF 파일 경로 (순서 중요)
PDF_PARTS = [
    "cover_page.pdf",
    "author_page.pdf",
    "book_intro_page.pdf",
    "guide_body.pdf",       # pandoc + XeLaTeX 생성
    "copyright_page.pdf",
]

OUTPUT = "NAS웹서비스_통합.pdf"

doc = fitz.open()  # 빈 문서 생성
for path in PDF_PARTS:
    src = fitz.open(path)
    doc.insert_pdf(src)
    src.close()
    print(f"  + {path} ({src.page_count if hasattr(src, 'page_count') else '?'} pages)")

doc.save(OUTPUT)
doc.close()
print(f"\n완료: {OUTPUT}")
