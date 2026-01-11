"""
동적 테스트 실행 스크립트
코드를 실행하여 기능을 검증합니다.
"""

import subprocess
import sys
from pathlib import Path
from datetime import datetime
import json

# 프로젝트 루트
PROJECT_ROOT = Path(__file__).parent.parent.parent
RESULTS_DIR = Path(__file__).parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)

# 테스트 카테고리
TEST_CATEGORIES = {
    "unit": {
        "description": "단위 테스트 (개별 함수/메서드)",
        "markers": "-m unit",
        "paths": [
            "90.tests/10.common/",
            "90.tests/30.apps/",
        ],
    },
    "integration": {
        "description": "통합 테스트 (모듈 간 상호작용)",
        "markers": "-m integration",
        "paths": [],
    },
    "smoke": {
        "description": "스모크 테스트 (기본 실행 가능 여부)",
        "markers": "",
        "paths": [
            "90.tests/dwg_smoke_test.py",
            "90.tests/kfn_smoke_test.py",
        ],
    },
}


def run_pytest_tests(category: str, verbose: bool = False) -> dict:
    """Pytest 테스트 실행"""
    config = TEST_CATEGORIES.get(category)
    if not config:
        return {"status": "ERROR", "details": f"알 수 없는 카테고리: {category}"}

    print(f"\n{'=' * 60}")
    print(f"{config['description']}")
    print(f"{'=' * 60}")

    # pytest 명령 구성
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        str(PROJECT_ROOT / "90.tests"),
        "-v" if verbose else "-q",
        "--tb=short",
        f"--rootdir={PROJECT_ROOT}",
    ]

    # 마커가 있으면 추가
    if config["markers"]:
        cmd.append(config["markers"])

    # 특정 경로가 지정되어 있으면 사용
    if config["paths"]:
        cmd = [
            sys.executable,
            "-m",
            "pytest",
            "-v" if verbose else "-q",
            "--tb=short",
            f"--rootdir={PROJECT_ROOT}",
        ]
        for path in config["paths"]:
            test_path = PROJECT_ROOT / path
            if test_path.exists():
                cmd.append(str(test_path))

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=300, cwd=str(PROJECT_ROOT)  # 5분 타임아웃
        )

        # 결과 파싱
        output = result.stdout + result.stderr

        # 통계 추출
        stats = parse_pytest_output(output)

        status = "PASS" if result.returncode == 0 else "FAIL"

        return {"status": status, "stats": stats, "output": output, "returncode": result.returncode}

    except subprocess.TimeoutExpired:
        return {
            "status": "TIMEOUT",
            "stats": {},
            "output": "테스트 실행 시간 초과 (5분)",
            "returncode": -1,
        }
    except Exception as e:
        return {"status": "ERROR", "stats": {}, "output": str(e), "returncode": -1}


def parse_pytest_output(output: str) -> dict:
    """Pytest 출력에서 통계 추출"""
    stats = {"passed": 0, "failed": 0, "skipped": 0, "errors": 0, "warnings": 0, "duration": 0.0}

    # 예: "5 passed, 2 warnings in 1.23s"
    for line in output.split("\n"):
        line = line.strip()

        if "passed" in line.lower():
            parts = line.split()
            for i, part in enumerate(parts):
                if part.lower() == "passed" and i > 0:
                    try:
                        stats["passed"] = int(parts[i - 1])
                    except (ValueError, IndexError):
                        pass

        if "failed" in line.lower():
            parts = line.split()
            for i, part in enumerate(parts):
                if part.lower() == "failed" and i > 0:
                    try:
                        stats["failed"] = int(parts[i - 1])
                    except (ValueError, IndexError):
                        pass

        if "skipped" in line.lower():
            parts = line.split()
            for i, part in enumerate(parts):
                if part.lower() == "skipped" and i > 0:
                    try:
                        stats["skipped"] = int(parts[i - 1])
                    except (ValueError, IndexError):
                        pass

        if "error" in line.lower():
            parts = line.split()
            for i, part in enumerate(parts):
                if part.lower() == "error" and i > 0:
                    try:
                        stats["errors"] = int(parts[i - 1])
                    except (ValueError, IndexError):
                        pass

        # 실행 시간 추출
        if " in " in line and "s" in line:
            try:
                # "in 1.23s" 형태 찾기
                time_part = line.split(" in ")[-1]
                time_str = time_part.split("s")[0].strip()
                stats["duration"] = float(time_str)
            except (ValueError, IndexError):
                pass

    return stats


def generate_report(results: dict) -> str:
    """테스트 결과 리포트 생성"""
    report_lines = [
        "=" * 80,
        "동적 테스트 결과 리포트",
        f"실행 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "=" * 80,
        "",
    ]

    total_passed = 0
    total_failed = 0
    total_skipped = 0
    total_duration = 0.0

    for category, result in results.items():
        config = TEST_CATEGORIES.get(category, {})
        description = config.get("description", category)

        report_lines.append(f"\n[{description}]")
        report_lines.append("-" * 60)

        status = result.get("status", "UNKNOWN")
        stats = result.get("stats", {})

        status_icon = {"PASS": "✓", "FAIL": "✗", "TIMEOUT": "⏱", "ERROR": "✗", "SKIP": "-"}.get(
            status, "?"
        )

        report_lines.append(f"  상태: {status_icon} {status}")

        if stats:
            passed = stats.get("passed", 0)
            failed = stats.get("failed", 0)
            skipped = stats.get("skipped", 0)
            duration = stats.get("duration", 0.0)

            report_lines.append(f"  통과: {passed}")
            report_lines.append(f"  실패: {failed}")
            if skipped > 0:
                report_lines.append(f"  건너뜀: {skipped}")
            report_lines.append(f"  실행 시간: {duration:.2f}초")

            total_passed += passed
            total_failed += failed
            total_skipped += skipped
            total_duration += duration

    # 요약
    report_lines.append("\n" + "=" * 80)
    report_lines.append("요약")
    report_lines.append("=" * 80)

    total_tests = total_passed + total_failed + total_skipped

    report_lines.append(f"총 테스트: {total_tests}")
    report_lines.append(f"통과: {total_passed}")
    report_lines.append(f"실패: {total_failed}")
    if total_skipped > 0:
        report_lines.append(f"건너뜀: {total_skipped}")
    report_lines.append(f"총 실행 시간: {total_duration:.2f}초")

    if total_tests > 0:
        pass_rate = (total_passed / total_tests) * 100
        report_lines.append(f"통과율: {pass_rate:.1f}%")

    report_lines.append("")

    return "\n".join(report_lines)


def main():
    """메인 실행 함수"""
    print("=" * 80)
    print("동적 테스트 시작")
    print("=" * 80)

    results = {}

    # 각 카테고리별 테스트 실행
    for category in TEST_CATEGORIES.keys():
        results[category] = run_pytest_tests(category, verbose=False)

    # 리포트 생성
    report = generate_report(results)
    print("\n" + report)

    # 파일로 저장
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = RESULTS_DIR / f"dynamic_test_report_{timestamp}.txt"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)

    # JSON 결과도 저장
    json_path = RESULTS_DIR / f"dynamic_test_results_{timestamp}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n리포트 저장: {report_path}")
    print(f"JSON 결과 저장: {json_path}")

    # 실패가 있으면 exit code 1
    has_failure = any(result["status"] in ["FAIL", "ERROR"] for result in results.values())

    return 1 if has_failure else 0


if __name__ == "__main__":
    sys.exit(main())
