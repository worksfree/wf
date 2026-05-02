"""
40회 예시답안 파일의 수식 형식 변환
\(...\) → $...$
\[...\] → $$...$$
"""
import re
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
ANSWER_DIR = BASE_DIR / "30.예시답안" / "40회"

def convert_math_format(content: str) -> str:
    """수식 형식 변환"""
    # \[...\] 블록 수식 (여러 줄) → $$...$$
    # \[ 로 시작하는 라인부터 \] 로 끝나는 라인까지
    content = re.sub(
        r'^\s*\\\[\s*$\n(.*?)\n^\s*\\\]\s*$',
        r'$$\n\1\n$$',
        content,
        flags=re.MULTILINE | re.DOTALL
    )

    # 단일 라인 \[...\] → $$...$$
    content = re.sub(r'\\\[([^\n]+?)\\\]', r'$$\1$$', content)

    # \(...\) 인라인 수식 → $...$
    content = re.sub(r'\\\((.+?)\\\)', r'$\1$', content)

    return content

def main():
    files = list(ANSWER_DIR.glob("**/예시답안*.md"))
    converted_count = 0

    for file_path in files:
        content = file_path.read_text(encoding='utf-8')
        original = content

        content = convert_math_format(content)

        if content != original:
            file_path.write_text(content, encoding='utf-8')
            print(f"변환: {file_path.relative_to(BASE_DIR)}")
            converted_count += 1
        else:
            print(f"변경없음: {file_path.relative_to(BASE_DIR)}")

    print(f"\n총 {converted_count}개 파일 변환 완료")

if __name__ == "__main__":
    main()
