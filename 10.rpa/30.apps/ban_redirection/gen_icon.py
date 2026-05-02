# -*- coding: utf-8 -*-
"""Generate BR.ico matching the WorksFree app icon style."""
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter

OUT = Path(__file__).parent / "res" / "BR.ico"
OUT.parent.mkdir(exist_ok=True)

SIZES = [256, 128, 64, 48, 32, 16]


def draw_icon(size: int) -> Image.Image:
    s = size
    pad = s // 16

    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))

    # --- gradient background ---
    bg = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    bgd = ImageDraw.Draw(bg)
    top_col    = (52, 120, 220)
    bottom_col = (22,  68, 170)
    for y in range(s):
        t = y / (s - 1)
        c = tuple(int(top_col[i] + (bottom_col[i] - top_col[i]) * t) for i in range(3))
        bgd.line([(0, y), (s, y)], fill=(*c, 255))

    mask = Image.new("L", (s, s), 0)
    md = ImageDraw.Draw(mask)
    r = s // 6
    md.rounded_rectangle([0, 0, s - 1, s - 1], radius=r, fill=255)
    img.paste(bg, mask=mask)

    d = ImageDraw.Draw(img)
    white = (255, 255, 255, 255)

    cx, cy = s / 2, s / 2

    # --- Shield ---
    sw = s * 0.50          # shield width
    sh = s * 0.58          # shield height
    sx = cx - sw / 2
    sy = cy - sh / 2 - s * 0.03

    # shield polygon: top-left, top-right arc → bottom point
    top_y   = sy
    mid_y   = sy + sh * 0.42
    bot_y   = sy + sh
    pts = [
        (sx,         top_y + sh * 0.10),   # top-left corner
        (cx,         top_y),               # top-center
        (sx + sw,    top_y + sh * 0.10),   # top-right corner
        (sx + sw,    mid_y),               # right mid
        (cx,         bot_y),               # bottom point
        (sx,         mid_y),               # left mid
    ]
    lw = max(2, s // 26)

    # filled shield (semi-transparent white)
    d.polygon(pts, fill=(255, 255, 255, 200))
    # outline
    d.line(pts + [pts[0]], fill=white, width=lw)

    # --- Ban circle slash (red/orange) ---
    ban_r  = sw * 0.46
    ban_lw = max(3, s // 18)
    ban_col = (255, 65, 55, 255)   # vivid red

    # circle
    d.ellipse(
        [cx - ban_r, cy - ban_r + s*0.02,
         cx + ban_r, cy + ban_r + s*0.02],
        outline=ban_col, width=ban_lw
    )

    # diagonal slash (top-right to bottom-left, 45°)
    ang = math.radians(45)
    lx1 = cx + ban_r * math.cos(ang + math.pi)
    ly1 = (cy + s*0.02) + ban_r * math.sin(ang + math.pi)
    lx2 = cx + ban_r * math.cos(ang)
    ly2 = (cy + s*0.02) + ban_r * math.sin(ang)
    d.line([(lx1, ly1), (lx2, ly2)], fill=ban_col, width=ban_lw)

    return img


def main():
    frames = [draw_icon(sz) for sz in SIZES]
    frames[0].save(
        OUT,
        format="ICO",
        sizes=[(sz, sz) for sz in SIZES],
        append_images=frames[1:],
    )
    # preview
    frames[0].save(str(OUT.parent / "BR_preview.png"))
    print(f"Saved: {OUT}")


if __name__ == "__main__":
    main()
