"""
Enhanced .spec 파일 생성 스크립트
기존 build_apps.py 기능을 .spec 파일로 완전 통합
"""

import os
import sys
from pathlib import Path

# 앱 정의
APPS = {
    "bom_exporter": {
        "display_name": "Bom Exporter",
        "description": "BOM Excel 변환 도구",
            "path": "30.apps/bom_exporter",
    },
    "dwg_classifier": {
        "display_name": "DWG Classifier",
        "description": "DWG 파일 분류 및 정리 도구",
        "path": "50.data/dwg_classifier",
    },
    "conversion_verifier": {
        "display_name": "Conversion Verifier",
        "description": "파일 변환 검증 도구",
        # NOTE: conversion_verifier는 데이터 처리 앱이므로 50.data 아래에 위치
        "path": "50.data/conversion_verifier",
    },
    "korean_filename_normalizer": {
        "display_name": "Korean Filename Normalizer",
        "description": "한글 파일명 정규화 도구",
        "path": "50.data/korean_filename_normalizer",
    },
    "file_list_check": {
        "display_name": "File List Checker",
        "description": "파일 목록 검증 도구",
        "path": "30.apps/file_list_check",
    },
    "spreadsheet_manager": {
        "display_name": "Spreadsheet Manager",
        "description": "스프레드시트 관리 도구",
        "path": "30.apps/spreadsheet_manager",
    },
}


def generate_spec_file(app_name):
    """특정 앱의 .spec 파일 생성"""
    if app_name not in APPS:
        print(f"❌ 지원하지 않는 앱: {app_name}")
        return False

    app_info = APPS[app_name]
    template_path = Path(__file__).parent / "enhanced_app.spec.template"

    if not template_path.exists():
        print(f"❌ 템플릿 파일을 찾을 수 없습니다: {template_path}")
        return False

    # 템플릿 읽기
    with open(template_path, "r", encoding="utf-8") as f:
        template_content = f.read()

    # 플레이스홀더 치환
    spec_content = template_content.replace("{APP_NAME}", app_name)
    spec_content = spec_content.replace("{APP_DISPLAY_NAME}", app_info["display_name"])
    spec_content = spec_content.replace("{APP_DESCRIPTION}", app_info["description"])

    # 앱 디렉토리에 .spec 파일 생성
    workspace_root = Path(__file__).parent
    app_dir = workspace_root / app_info["path"]
    spec_file = app_dir / f"{app_name}.spec"

    app_dir.mkdir(parents=True, exist_ok=True)

    with open(spec_file, "w", encoding="utf-8") as f:
        f.write(spec_content)

    print(f"✅ {app_name}.spec 파일 생성: {spec_file}")
    return spec_file


def main():
    """메인 실행"""
    if len(sys.argv) < 2:
        print("사용법: python generate_specs.py <app_name> [all]")
        print(f"지원 앱: {', '.join(APPS.keys())}")
        print("예시: python generate_specs.py dwg_classifier")
        print("예시: python generate_specs.py all  # 모든 앱")
        return

    target = sys.argv[1]

    if target == "all":
        print("🔧 모든 앱의 .spec 파일 생성...")
        for app_name in APPS.keys():
            generate_spec_file(app_name)
        print("✅ 모든 .spec 파일 생성 완료!")
    else:
        generate_spec_file(target)


if __name__ == "__main__":
    main()
