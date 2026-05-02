"""
정적 테스트 실행 스크립트
코드를 실행하지 않고 구문, 스타일, 보안 문제를 검사합니다.
"""

import subprocess
import sys
from pathlib import Path
from datetime import datetime
import json

# 테스트 대상 앱들
APPS = {
    "DWG_Classifier": "50.data/dwg_classifier/ui_main.py",
    "BOM2Excel": "30.apps/bom2excel/ui_main.py",
    "Conversion_Verifier": "50.data/conversion_verifier/ui_main.py",
    "Korean_Filename_Normalizer": "50.data/korean_filename_normalizer/ui_main.py",
}

# 프로젝트 루트 (10.rpa)
PROJECT_ROOT = Path(__file__).parent.parent.parent
RESULTS_DIR = Path(__file__).parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)


def run_syntax_check(app_name: str, file_path: Path) -> dict:
    """Python 구문 오류 검사"""
    print(f"\n[구문 검사] {app_name}...", end=" ")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "py_compile", str(file_path)],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            print("✓ 통과")
            return {"status": "PASS", "errors": 0, "details": "구문 오류 없음"}
        else:
            print("✗ 실패")
            return {"status": "FAIL", "errors": 1, "details": result.stderr}
    except Exception as e:
        print(f"✗ 예외: {e}")
        return {"status": "ERROR", "errors": 1, "details": str(e)}


def run_flake8_check(app_name: str, file_path: Path) -> dict:
    """Flake8 코드 스타일 검사"""
    print(f"[Flake8 검사] {app_name}...", end=" ")
    try:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "flake8",
                str(file_path),
                "--max-line-length=120",
                "--count",
                "--statistics",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        # 통계 추출
        output_lines = result.stdout.strip().split("\n")
        total_errors = 0
        stats = {}

        for line in output_lines[-20:]:  # 마지막 20줄에서 통계 찾기
            if line and not line.startswith("d:"):
                parts = line.split()
                if len(parts) >= 2 and parts[0].isdigit():
                    count = int(parts[0])
                    error_code = " ".join(parts[1:])
                    stats[error_code] = count
                    total_errors += count

        if total_errors == 0:
            print("✓ 통과 (0개 이슈)")
            return {"status": "PASS", "errors": 0, "details": stats}
        else:
            print(f"⚠ {total_errors}개 이슈 발견")
            return {"status": "WARNING", "errors": total_errors, "details": stats}
    except subprocess.TimeoutExpired:
        print("✗ 타임아웃")
        return {"status": "ERROR", "errors": -1, "details": "실행 타임아웃"}
    except Exception as e:
        print(f"✗ 예외: {e}")
        return {"status": "ERROR", "errors": -1, "details": str(e)}


def run_bandit_check(app_name: str, file_path: Path) -> dict:
    """Bandit 보안 취약점 검사"""
    print(f"[보안 검사] {app_name}...", end=" ")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "bandit", "-r", str(file_path), "-f", "json"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        try:
            bandit_output = json.loads(result.stdout)
            issues = bandit_output.get("results", [])
            high_severity = [i for i in issues if i.get("issue_severity") == "HIGH"]
            medium_severity = [i for i in issues if i.get("issue_severity") == "MEDIUM"]

            total_issues = len(issues)

            if total_issues == 0:
                print("✓ 통과 (취약점 없음)")
                return {"status": "PASS", "errors": 0, "details": "보안 취약점 없음"}
            else:
                print(
                    f"⚠ {total_issues}개 이슈 (HIGH: {len(high_severity)}, MEDIUM: {len(medium_severity)})"
                )
                return {
                    "status": "WARNING" if len(high_severity) == 0 else "FAIL",
                    "errors": total_issues,
                    "details": {
                        "high": len(high_severity),
                        "medium": len(medium_severity),
                        "low": total_issues - len(high_severity) - len(medium_severity),
                    },
                }
        except json.JSONDecodeError:
            print("⚠ 출력 파싱 실패")
            return {"status": "ERROR", "errors": -1, "details": "JSON 파싱 오류"}
    except subprocess.TimeoutExpired:
        print("✗ 타임아웃")
        return {"status": "ERROR", "errors": -1, "details": "실행 타임아웃"}
    except FileNotFoundError:
        print("⚠ Bandit 미설치")
        return {"status": "SKIP", "errors": 0, "details": "Bandit이 설치되지 않음"}
    except Exception as e:
        print(f"✗ 예외: {e}")
        return {"status": "ERROR", "errors": -1, "details": str(e)}


def generate_report(results: dict) -> str:
    """테스트 결과 리포트 생성"""
    report_lines = [
        "=" * 80,
        "정적 테스트 결과 리포트",
        f"실행 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "=" * 80,
        "",
    ]

    for app_name, tests in results.items():
        report_lines.append(f"\n[{app_name}]")
        report_lines.append("-" * 60)

        for test_type, result in tests.items():
            status = result["status"]
            errors = result["errors"]

            status_icon = {"PASS": "✓", "WARNING": "⚠", "FAIL": "✗", "ERROR": "✗", "SKIP": "-"}.get(
                status, "?"
            )

            report_lines.append(f"  {status_icon} {test_type:20s} : {status:10s} ({errors} 이슈)")

    # 요약
    report_lines.append("\n" + "=" * 80)
    report_lines.append("요약")
    report_lines.append("=" * 80)

    total_pass = sum(
        1 for app in results.values() for test in app.values() if test["status"] == "PASS"
    )
    total_warning = sum(
        1 for app in results.values() for test in app.values() if test["status"] == "WARNING"
    )
    total_fail = sum(
        1 for app in results.values() for test in app.values() if test["status"] == "FAIL"
    )
    total_tests = sum(len(app) for app in results.values())

    report_lines.append(f"총 테스트: {total_tests}")
    report_lines.append(f"통과: {total_pass}")
    report_lines.append(f"경고: {total_warning}")
    report_lines.append(f"실패: {total_fail}")
    report_lines.append("")

    return "\n".join(report_lines)


def main():
    """메인 실행 함수"""
    print("=" * 80)
    print("정적 테스트 시작")
    print("=" * 80)

    results = {}

    for app_name, rel_path in APPS.items():
        file_path = PROJECT_ROOT / rel_path

        if not file_path.exists():
            print(f"\n⚠ {app_name}: 파일을 찾을 수 없음 ({file_path})")
            results[app_name] = {
                "구문검사": {"status": "ERROR", "errors": -1, "details": "파일 없음"},
                "스타일검사": {"status": "ERROR", "errors": -1, "details": "파일 없음"},
                "보안검사": {"status": "ERROR", "errors": -1, "details": "파일 없음"},
            }
            continue

        print(f"\n{'=' * 60}")
        print(f"{app_name}")
        print(f"{'=' * 60}")

        results[app_name] = {
            "구문검사": run_syntax_check(app_name, file_path),
            "스타일검사": run_flake8_check(app_name, file_path),
            "보안검사": run_bandit_check(app_name, file_path),
        }

    # 리포트 생성 및 저장
    report = generate_report(results)
    print("\n" + report)

    # 파일로 저장
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = RESULTS_DIR / f"static_test_report_{timestamp}.txt"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)

    # JSON 결과도 저장
    json_path = RESULTS_DIR / f"static_test_results_{timestamp}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n리포트 저장: {report_path}")
    print(f"JSON 결과 저장: {json_path}")

    # 실패가 있으면 exit code 1
    has_failure = any(test["status"] == "FAIL" for app in results.values() for test in app.values())

    return 1 if has_failure else 0


if __name__ == "__main__":
    sys.exit(main())
