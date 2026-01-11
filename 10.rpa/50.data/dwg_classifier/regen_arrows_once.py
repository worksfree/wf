from pathlib import Path
from PIL import Image

def main():
    root = Path(__file__).resolve().parent
    src = root / "cursor_arrow.png"
    if not src.exists():
        raise SystemExit("cursor_arrow.png not found in current folder")
    img = Image.open(src).convert("RGBA")
    resample = getattr(Image, "Resampling", Image).LANCZOS
    variants = [
        ("big_arrow.png", 1.0),
        ("mid_arrow.png", 0.5),
        ("small_arrow.png", 0.25),
    ]
    for name, scale in variants:
        new_size = (max(1, int(img.width * scale)), max(1, int(img.height * scale)))
        out = root / name
        img.resize(new_size, resample=resample).save(out)
        print(f"saved {name} size={new_size}")

if __name__ == "__main__":
    main()
