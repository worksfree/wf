"""
빠른 정적 검사 스크립트
변경된 파일만 빠르게 검사합니다.
"""

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent


def check_file(file_path: Path) -> bool:
    """단일 파일 빠른 검사"""
    print(f"\n{'=' * 60}")
    print(f"검사: {file_path.name}")
    print(f"{'=' * 60}")

    all_passed = True

    # 1. 구문 검사
    print("1. 구문 검사...", end=" ")
    result = subprocess.run(
        [sys.executable, "-m", "py_compile", str(file_path)], capture_output=True
    )
    if result.returncode == 0:
        print("✓")
    else:
        print("✗")
        print(result.stderr.decode())
        all_passed = False

    # 2. Flake8 (간단 버전)
    print("2. 스타일 검사...", end=" ")
    result = subprocess.run(
        [sys.executable, "-m", "flake8", str(file_path), "--count"], capture_output=True, text=True
    )

    # 마지막 줄에서 총 개수 추출
    lines = result.stdout.strip().split("\n")
    if lines and lines[-1].isdigit():
        error_count = int(lines[-1])
        if error_count == 0:
            print("✓ (0개)")
        else:
            print(f"⚠ ({error_count}개)")
            # 처음 5개만 표시
            for line in lines[:5]:
                if line and not line.isdigit():
                    print(f"  - {line}")
            if error_count > 5:
                print(f"  ... 외 {error_count - 5}개")
    else:
        print("✓")

    return all_passed


def main():
    """메인 함수"""
    if len(sys.argv) > 1:
        # 인자로 파일 지정
        target_file = Path(sys.argv[1])
        if not target_file.exists():
            print(f"오류: 파일을 찾을 수 없음 - {target_file}")
            return 1

        files_to_check = [target_file]
    else:
        # 기본: 모든 ui_main.py 검사
        files_to_check = [
            PROJECT_ROOT / "50.data/dwg_classifier/ui_main.py",
            PROJECT_ROOT / "30.apps/bom2excel/ui_main.py",
            PROJECT_ROOT / "50.data/conversion_verifier/ui_main.py",
            PROJECT_ROOT / "50.data/korean_filename_normalizer/ui_main.py",
        ]

    print("=" * 60)
    print("빠른 정적 검사")
    print("=" * 60)

    all_passed = True
    for file_path in files_to_check:
        if file_path.exists():
            passed = check_file(file_path)
            all_passed = all_passed and passed
        else:
            print(f"\n⚠ 건너뜀: {file_path} (파일 없음)")

    print("\n" + "=" * 60)
    if all_passed:
        print("결과: ✓ 모든 검사 통과")
        return 0
    else:
        print("결과: ⚠ 일부 검사 실패")
        return 1


if __name__ == "__main__":
    sys.exit(main())
