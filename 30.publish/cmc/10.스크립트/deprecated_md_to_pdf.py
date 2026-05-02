from pathlib import Path
import argparse
import subprocess
import markdown


DEFAULT_MD = "input.md"

HTML_TEMPLATE = """<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8" />
  <style>
    @page {{ size: A4; margin: 18mm; }}

    body {{
      font-family: "Noto Sans KR", Arial, sans-serif;
      line-height: 1.5;
      color: #222;
    }}

    h1, h2, h3, h4 {{
      break-after: avoid;
      page-break-after: avoid;
    }}

    table {{
      width: 100%;
      border-collapse: collapse;
      margin: 12px 0;
    }}

    th, td {{
      border: 1px solid #999;
      padding: 6px 8px;
      vertical-align: top;
    }}

    thead {{
      display: table-header-group;
    }}

    tr, table, figure, blockquote {{
      break-inside: avoid;
      page-break-inside: avoid;
    }}

    .page-break {{
      break-before: page;
      page-break-before: always;
    }}
  </style>
</head>
<body>
{body}
</body>
</html>
""" # NOTE: This template is for wkhtmltopdf/playwright, not used by pandoc directly.

def build_paths(md_path: Path):
    pdf_path = md_path.with_suffix(".pdf")
    return pdf_path

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("md_path", nargs="?", default=DEFAULT_MD)
    parser.add_argument("--engine", choices=['pandoc', 'wkhtmltopdf'], default='pandoc',
                        help="PDF conversion engine to use.")
    args = parser.parse_args()

    md_path = Path(args.md_path).expanduser().resolve()
    if not md_path.exists():
        raise FileNotFoundError(f"Markdown file not found: {md_path}")

    pdf_path = build_paths(md_path)

    if args.engine == 'pandoc':
        print(f"Using pandoc to convert {md_path.name} to {pdf_path.name}")
        subprocess.run([
            "pandoc",
            str(md_path),
            "--resource-path", str(md_path.parent),  # 이미지 등 리소스의 기본 경로 설정
            "-o", str(pdf_path),
            "--pdf-engine=xelatex",
            "-V", "mainfont=Malgun Gothic",
            "-V", "monofont=Malgun Gothic",  # 코드 블록용 한글 폰트 설정
            "-V", "geometry:margin=1.8cm",
            "--toc",
            # 한글 앵커 및 내부 링크 지원을 위한 확장 기능 추가
            "--from=markdown-auto_identifiers+smart+autolink_bare_uris+tex_math_dollars+raw_html+markdown_in_html_blocks+native_divs+native_spans+fenced_divs+bracketed_spans"
        ], check=True)
    else:  # wkhtmltopdf
        print(f"Using wkhtmltopdf to convert {md_path.name} to {pdf_path.name}")
        html_path = md_path.with_suffix(".html")
        md_text = md_path.read_text(encoding="utf-8")

        body = markdown.markdown(
            md_text,
            extensions=["extra", "tables", "fenced_code", "attr_list"]
        )

        # Escape curly braces for format
        html = HTML_TEMPLATE.format(body=body)
        html_path.write_text(html, encoding="utf-8")

        subprocess.run([
            "wkhtmltopdf",
            "--enable-local-file-access",
            "--outline",
            "--print-media-type",
            str(html_path),
            str(pdf_path)
        ], check=True)

        print(f"HTML saved: {html_path}")

    print(f"PDF saved : {pdf_path}")

if __name__ == "__main__":
    main()