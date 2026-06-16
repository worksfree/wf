import sys
from pathlib import Path
src, dst = Path(sys.argv[1]), Path(sys.argv[2])
text = src.read_text(encoding='utf-8')
sep = '\n---\n\n'
idx = text.find(sep)
body = text[idx + len(sep):] if idx >= 0 else text
dst.write_text(body, encoding='utf-8')
print(f'異붿텧: {len(body)} chars')