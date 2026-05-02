"""
Inkscape를 사용한 고품질 멀티사이즈 ICO 아이콘 생성 v4
PNG를 직접 ICO에 포함 (PIL 재인코딩 없음)
"""

import subprocess
import struct
from pathlib import Path

ICONS = [
    # ("01", "BOM_Exporter", "30.apps/bom_exporter/res"),
    # ("02", "DWG_Batch_Print", "30.apps/dwg_batch_print/res"),
    # ("03", "DWG_Classifier", "50.data/dwg_classifier/res"),
    # ("04", "Conversion_Verifier", "50.data/conversion_verifier/res"),
    ("05", "Attribute_Reset", "30.apps/attribute_reset/res"),
    # ("06", "Korean_Filename_Normalizer", "50.data/korean_filename_normalizer/res"),
    # ("07", "QRCode_Generator", "50.data/qrcode_generator/res"),
]

SIZES = [16, 32, 48, 256]
INKSCAPE = r"C:\Program Files\Inkscape\bin\inkscape.exe"


def svg_to_png_inkscape(svg_path: Path, png_path: Path, size: int) -> bool:
    """Inkscape로 SVG를 PNG로 변환"""
    cmd = [
        INKSCAPE,
        str(svg_path),
        "--export-type=png",
        f"--export-filename={png_path}",
        f"--export-width={size}",
        f"--export-height={size}",
    ]
    try:
        subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return png_path.exists()
    except Exception as e:
        print(f"    ! Inkscape 오류: {e}")
        return False


def create_ico_from_pngs(png_paths: list, sizes: list, ico_path: Path) -> bool:
    """
    PNG 파일들을 직접 ICO로 패키징 (재인코딩 없음)
    """
    try:
        # PNG 바이트 직접 읽기
        png_blobs = []
        for png_path in png_paths:
            with open(png_path, 'rb') as f:
                png_blobs.append(f.read())

        # ICO 헤더
        header = struct.pack('<HHH', 0, 1, len(png_blobs))

        # 디렉토리 엔트리
        data_offset = 6 + (16 * len(png_blobs))
        entries = []

        for i, (size, blob) in enumerate(zip(sizes, png_blobs)):
            w = size if size < 256 else 0
            h = size if size < 256 else 0

            entry = struct.pack('<BBBBHHII',
                w,           # Width
                h,           # Height
                0,           # Color count
                0,           # Reserved
                0,           # Planes (0 like working icon)
                32,          # Bits per pixel
                len(blob),   # Size
                data_offset  # Offset
            )
            entries.append(entry)
            data_offset += len(blob)

        # ICO 파일 작성
        with open(ico_path, 'wb') as f:
            f.write(header)
            for entry in entries:
                f.write(entry)
            for blob in png_blobs:
                f.write(blob)

        return True
    except Exception as e:
        print(f"    ! ICO 생성 오류: {e}")
        return False


def main():
    project_root = Path(__file__).parent.parent

    print("=" * 60)
    print("Inkscape + 직접 PNG ICO 생성 v4")
    print(f"사이즈: {SIZES}")
    print("=" * 60)

    success = 0

    for num, name, res_rel in ICONS:
        res_dir = project_root / res_rel
        svg_path = res_dir / f"{num}_{name}.svg"
        ico_path = res_dir / f"{num}_{name}.ico"

        if not svg_path.exists():
            print(f"  X {name}: SVG 없음")
            continue

        print(f"  {name}:")

        png_paths = []
        all_ok = True

        for size in SIZES:
            png_path = res_dir / f"_temp_{size}.png"
            png_paths.append(png_path)
            print(f"    - {size}x{size}...", end=" ")

            if svg_to_png_inkscape(svg_path, png_path, size):
                png_size = png_path.stat().st_size
                print(f"OK ({png_size} bytes)")
            else:
                print("FAIL")
                all_ok = False

        if all_ok:
            if create_ico_from_pngs(png_paths, SIZES, ico_path):
                size_kb = ico_path.stat().st_size / 1024
                print(f"    -> {ico_path.name} ({size_kb:.1f} KB)")
                success += 1

        # 임시 PNG 삭제
        for png_path in png_paths:
            try:
                if png_path.exists():
                    png_path.unlink()
            except:
                pass

    print("=" * 60)
    print(f"완료: {success}/7 성공")
    print("=" * 60)


if __name__ == "__main__":
    main()
