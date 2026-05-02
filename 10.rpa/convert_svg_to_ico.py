#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
SVG to ICO 변환 스크립트
- 타이틀창, 작업표시줄, 바탕화면 바로가기용 아이콘 생성
- 기존 ICO 파일 백업 후 새로 생성
"""

import os
import shutil
from datetime import datetime
from pathlib import Path
import cairosvg
from PIL import Image
import io

# ICO에 포함할 크기들 (Windows 표준)
ICO_SIZES = [
    16,   # 타이틀바, 작은 아이콘
    24,   # 일부 UI 요소
    32,   # 작업표시줄 (기본)
    48,   # 바탕화면 아이콘
    64,   # 큰 아이콘 보기
    128,  # 매우 큰 아이콘
    256,  # Windows Vista+ 고해상도
]

# 앱 폴더와 SVG 파일 매핑
APPS_30 = [
    {
        "name": "bom_exporter",
        "svg": "01_BOM_Exporter.svg",
        "ico": "01_BOM_Exporter.ico",
    },
    {
        "name": "dwg_batch_print",
        "svg": "02_DWG_Batch_Print.svg",
        "ico": "02_DWG_Batch_Print.ico",
    },
    {
        "name": "attribute_reset",
        "svg": "05_Attribute_Reset.svg",
        "ico": "05_Attribute_Reset.ico",
    },
]

APPS_50 = [
    {
        "name": "dwg_classifier",
        "svg": "03_DWG_Classifier.svg",
        "ico": "03_DWG_Classifier.ico",
    },
    {
        "name": "conversion_verifier",
        "svg": "04_Conversion_Verifier.svg",
        "ico": "04_Conversion_Verifier.ico",
    },
    {
        "name": "korean_filename_normalizer",
        "svg": "06_Korean_Filename_Normalizer.svg",
        "ico": "06_Korean_Filename_Normalizer.ico",
    },
    {
        "name": "qrcode_generator",
        "svg": "07_QRCode_Generator.svg",
        "ico": "07_QRCode_Generator.ico",
    },
]

BASE_DIR_30 = Path(__file__).parent / "30.apps"
BASE_DIR_50 = Path(__file__).parent / "50.data"


def backup_existing_ico(ico_path: Path) -> Path | None:
    """기존 ICO 파일을 백업합니다."""
    if not ico_path.exists():
        return None

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"{ico_path.stem}_backup_{timestamp}{ico_path.suffix}"
    backup_path = ico_path.parent / backup_name

    shutil.copy2(ico_path, backup_path)
    print(f"  [백업] {ico_path.name} -> {backup_name}")
    return backup_path


def svg_to_ico(svg_path: Path, ico_path: Path) -> bool:
    """SVG 파일을 다중 해상도 ICO 파일로 변환합니다."""
    try:
        # 가장 큰 크기로 먼저 렌더링
        max_size = max(ICO_SIZES)
        png_data = cairosvg.svg2png(
            url=str(svg_path),
            output_width=max_size,
            output_height=max_size,
        )

        # 기본 이미지 로드
        base_img = Image.open(io.BytesIO(png_data))
        if base_img.mode != 'RGBA':
            base_img = base_img.convert('RGBA')

        # 각 크기별 이미지 생성
        images = []
        for size in sorted(ICO_SIZES, reverse=True):  # 큰 것부터
            if size == max_size:
                img = base_img.copy()
            else:
                # 고품질 리사이즈
                img = base_img.resize((size, size), Image.Resampling.LANCZOS)
            images.append(img)
            print(f"    - {size}x{size} 생성")

        # ICO 파일로 저장 (다중 해상도)
        # Pillow에서 다중 해상도 ICO는 append_images로 추가 이미지 전달 필요
        images[0].save(
            ico_path,
            format='ICO',
            append_images=images[1:],  # 나머지 크기 이미지들 추가
        )

        return True
    except Exception as e:
        print(f"  [오류] {e}")
        import traceback
        traceback.print_exc()
        return False


def process_apps(apps, base_dir, folder_name):
    """앱 목록을 처리하고 결과를 반환합니다."""
    success_count = 0
    fail_count = 0

    print(f"\n{'=' * 60}")
    print(f"  {folder_name} 폴더 처리")
    print(f"{'=' * 60}")

    for app in apps:
        app_dir = base_dir / app["name"] / "res"
        svg_path = app_dir / app["svg"]
        ico_path = app_dir / app["ico"]

        print(f"\n[{app['name']}]")
        print(f"  SVG: {svg_path}")

        if not svg_path.exists():
            print(f"  [건너뜀] SVG 파일이 없습니다.")
            fail_count += 1
            continue

        # 기존 ICO 백업
        backup_existing_ico(ico_path)

        # SVG -> ICO 변환
        print(f"  ICO 생성 중...")
        if svg_to_ico(svg_path, ico_path):
            file_size = ico_path.stat().st_size
            print(f"  [완료] {ico_path.name} ({file_size:,} bytes)")
            success_count += 1
        else:
            fail_count += 1

    return success_count, fail_count


def main():
    print("=" * 60)
    print("SVG to ICO 변환기")
    print("타이틀창, 작업표시줄, 바탕화면용 다중 해상도 아이콘 생성")
    print("=" * 60)

    total_success = 0
    total_fail = 0

    # 30.apps 처리
    s, f = process_apps(APPS_30, BASE_DIR_30, "30.apps")
    total_success += s
    total_fail += f

    # 50.data 처리
    s, f = process_apps(APPS_50, BASE_DIR_50, "50.data")
    total_success += s
    total_fail += f

    print("\n" + "=" * 60)
    print(f"완료: 성공 {total_success}개, 실패 {total_fail}개")
    print("=" * 60)

    # 생성된 ICO 파일 정보 출력
    print("\n생성된 ICO 파일에 포함된 크기:")
    print(f"  - 16x16:   타이틀바, 작은 아이콘")
    print(f"  - 24x24:   일부 UI 요소")
    print(f"  - 32x32:   작업표시줄 (기본)")
    print(f"  - 48x48:   바탕화면 아이콘")
    print(f"  - 64x64:   큰 아이콘 보기")
    print(f"  - 128x128: 매우 큰 아이콘")
    print(f"  - 256x256: Windows Vista+ 고해상도")


if __name__ == "__main__":
    main()
