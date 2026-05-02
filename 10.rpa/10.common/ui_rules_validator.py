# -*- coding: utf-8 -*-
"""
UI Rules Validator
BASIC_RULES.md에 정의된 규칙을 자동으로 검증하는 스크립트

사용법:
    python ui_rules_validator.py [app_path]
    python ui_rules_validator.py --all  # 모든 앱 검증
"""

import os
import sys
import re
from pathlib import Path
from typing import List, Dict, Tuple


# 앱별 예상 설정 (BASIC_RULES.md 기반)
APP_CONFIGS = {
    "bom_exporter": {"input_count": 1, "min_height": 160, "max_height": 190},
    "dwg_classifier": {"input_count": 2, "min_height": 260, "max_height": 280},  # 기준: 270
    "conversion_verifier": {"input_count": 1, "min_height": 160, "max_height": 190},  # 폴더만 선택
    "dwg_batch_print": {"input_count": 1, "min_height": 160, "max_height": 190},
    "attribute_reset": {"input_count": 1, "min_height": 160, "max_height": 190},
    "korean_filename_normalizer": {"input_count": 1, "min_height": 160, "max_height": 190},
    "qrcode_generator": {"input_count": 1, "min_height": 160, "max_height": 190},
}


def find_app_dirs() -> List[Path]:
    """모든 앱 디렉토리 찾기"""
    base_path = Path(__file__).parent.parent
    app_dirs = []

    # 30.apps 폴더
    apps_30 = base_path / "30.apps"
    if apps_30.exists():
        for d in apps_30.iterdir():
            if d.is_dir() and (d / "ui_main.py").exists():
                app_dirs.append(d)

    # 50.data 폴더
    data_50 = base_path / "50.data"
    if data_50.exists():
        for d in data_50.iterdir():
            if d.is_dir() and (d / "ui_main.py").exists():
                app_dirs.append(d)

    return app_dirs


def check_base_original_height(content: str, app_name: str) -> List[str]:
    """base_original_height 값 검증"""
    violations = []
    config = APP_CONFIGS.get(app_name, {})

    if not config:
        return violations

    # base_original_height 찾기
    match = re.search(r'base_original_height\s*=\s*(\d+)', content)
    if match:
        height = int(match.group(1))
        min_h = config.get("min_height", 180)
        max_h = config.get("max_height", 400)

        if height < min_h:
            violations.append(f"base_original_height={height} < 최소값({min_h})")
        elif height > max_h:
            violations.append(f"base_original_height={height} > 최대값({max_h})")
    else:
        # base_original_height가 없으면 input_count가 2 이상인 앱에서 문제
        if config.get("input_count", 1) >= 2:
            violations.append("base_original_height가 정의되지 않음 (2개 입력 앱)")

    return violations


def check_apply_global_fonts(content: str) -> List[str]:
    """apply_global_fonts 사용 검증"""
    violations = []

    # _apply_global_fonts 사용 확인 (import alias 제외)
    # 잘못된 패턴: _apply_global_fonts(xxx, yyy) 호출
    wrong_calls = re.findall(r'[^a-zA-Z_]_apply_global_fonts\s*\(', content)

    # import 문에서 alias로 사용하는 경우 제외
    has_alias_import = re.search(r'apply_global_fonts\s+as\s+_apply_global_fonts', content)

    if wrong_calls and not has_alias_import:
        violations.append(f"_apply_global_fonts 직접 호출 발견 ({len(wrong_calls)}곳) - apply_global_fonts 사용 필요")

    return violations


def check_init_ui_window_height(content: str, app_name: str) -> List[str]:
    """init_ui에서 window_height 사용 방식 검증"""
    violations = []
    config = APP_CONFIGS.get(app_name, {})

    if config.get("input_count", 1) >= 2:
        # 2개 입력 앱은 self.ui.get("window_height")가 아닌 self.original_window_height 사용해야 함
        # init_ui 함수 내부에서 self.ui.get("window_height") 사용 확인
        init_ui_match = re.search(r'def init_ui\(self\):(.*?)(?=\n    def |\Z)', content, re.DOTALL)
        if init_ui_match:
            init_ui_content = init_ui_match.group(1)
            if 'self.ui.get("window_height"' in init_ui_content or "self.ui.get('window_height'" in init_ui_content:
                # original_window_height도 사용하는지 확인
                if 'self.original_window_height' not in init_ui_content:
                    violations.append("2개 입력 앱에서 self.ui.get('window_height') 대신 self.original_window_height 사용 필요")

    return violations


def check_settings_min_height(content: str, app_name: str) -> List[str]:
    """설정창 높이 검증 - 앱별 최적 값 확인 (참고용)

    주의: 이 검증은 참고용이며, UI가 정상 작동하면 무시해도 됨.
    각 앱은 항목 수에 따라 다른 최적 높이를 가짐.
    """
    # 설정창 높이는 앱마다 다르므로 일괄 검증하지 않음
    # UI_RULES.md의 앱별 설정창 크기 표 참조
    return []


def validate_ui_main(app_path: Path) -> Dict[str, List[str]]:
    """ui_main.py 검증"""
    results = {}
    app_name = app_path.name
    ui_main_path = app_path / "ui_main.py"

    if not ui_main_path.exists():
        results["ui_main.py"] = ["파일 없음"]
        return results

    try:
        content = ui_main_path.read_text(encoding="utf-8")
    except Exception as e:
        results["ui_main.py"] = [f"읽기 실패: {e}"]
        return results

    violations = []
    violations.extend(check_base_original_height(content, app_name))
    violations.extend(check_apply_global_fonts(content))
    violations.extend(check_init_ui_window_height(content, app_name))

    if violations:
        results["ui_main.py"] = violations

    return results


def validate_ui_setting(app_path: Path) -> Dict[str, List[str]]:
    """ui_setting.py 검증"""
    results = {}
    app_name = app_path.name
    ui_setting_path = app_path / "ui_setting.py"

    if not ui_setting_path.exists():
        return results  # ui_setting.py는 선택적

    try:
        content = ui_setting_path.read_text(encoding="utf-8")
    except Exception as e:
        results["ui_setting.py"] = [f"읽기 실패: {e}"]
        return results

    violations = []
    violations.extend(check_apply_global_fonts(content))
    # 설정창 높이는 앱마다 다르므로 일괄 검증 제외
    # violations.extend(check_settings_min_height(content, app_name))

    if violations:
        results["ui_setting.py"] = violations

    return results


def validate_app(app_path: Path) -> Dict[str, List[str]]:
    """단일 앱 전체 검증"""
    all_results = {}
    all_results.update(validate_ui_main(app_path))
    all_results.update(validate_ui_setting(app_path))
    return all_results


def print_results(app_name: str, results: Dict[str, List[str]]) -> bool:
    """결과 출력, 위반 있으면 True 반환"""
    if not results:
        print(f"  [PASS] {app_name}")
        return False

    print(f"  [FAIL] {app_name}")
    for file_name, violations in results.items():
        for v in violations:
            print(f"         - {file_name}: {v}")
    return True


def main():
    """메인 함수"""
    print("=" * 60)
    print("WF-RPA UI 규칙 검증기")
    print("=" * 60)
    print()

    if len(sys.argv) > 1 and sys.argv[1] != "--all":
        # 단일 앱 검증
        app_path = Path(sys.argv[1])
        if not app_path.exists():
            print(f"오류: 경로를 찾을 수 없음: {app_path}")
            sys.exit(1)

        results = validate_app(app_path)
        has_violations = print_results(app_path.name, results)
        sys.exit(1 if has_violations else 0)

    # 전체 앱 검증
    app_dirs = find_app_dirs()

    if not app_dirs:
        print("검증할 앱을 찾을 수 없습니다.")
        sys.exit(1)

    print(f"검증 대상: {len(app_dirs)}개 앱")
    print("-" * 40)

    total_violations = 0
    for app_path in sorted(app_dirs):
        results = validate_app(app_path)
        if print_results(app_path.name, results):
            total_violations += 1

    print("-" * 40)
    if total_violations == 0:
        print(f"결과: 모든 앱 통과 ({len(app_dirs)}개)")
    else:
        print(f"결과: {total_violations}개 앱에서 위반 발견")

    sys.exit(1 if total_violations > 0 else 0)


if __name__ == "__main__":
    main()
