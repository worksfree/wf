# -*- coding: utf-8 -*-
"""
DWG 도형(LINE/ARC/CIRCLE/LWPOLYLINE) 좌표만 뽑아 텍스트 없는 와이어프레임 SVG
썸네일을 만든다. 표제란·BOM 등 MTEXT는 전혀 포함하지 않는다 — 축소된 썸네일
크기에서는 어차피 글자를 읽을 수 없으므로(2026-07-26 요청 배경), 애초에
구체적인 정보(설계정보·부품표 내용)를 포함하지 않고 도면의 대략적인 형상
(윤곽선)만 보여주는 용도. dwg_extract.py(텍스트/BOM 추출)와 독립된 모듈이며,
같은 dwgread.exe JSON 덤프를 그대로 재사용한다(파싱 두 번 안 함).

SPLINE·ELLIPSE는 다루지 않는다 — NURBS 평가 없이 좌표만으로 근사하기 어렵고,
실측(sample_top_assembly.DWG, 12만개 엔티티 중 SPLINE 3.4만개)해 보니 LINE/ARC/
CIRCLE만으로도 실루엣은 충분히 알아볼 수 있는 수준이라 생략해도 목적(그림자
수준의 형상 확인)에는 지장 없다.

대형 조립도(실측: LINE 7만개 이상)는 전부 그리면 SVG가 비대해지고 브라우저에서
느려지므로 MAX_ENTITIES로 균등 샘플링한다 — 원본 개수 순서를 그대로 등간격
추출(entities[::stride])하므로 도면 전체에 걸쳐 고르게 솎아진다.
"""
import math
from dwg_extract import run_dwgread_json, _iter_entities

MAX_ENTITIES = 4000
THUMB_W, THUMB_H = 320, 320
PAD = 8
ARC_SEGMENTS = 12  # 호 하나를 몇 개의 직선 조각으로 근사할지


def _collect_geometry(objs):
    """(kind, coords) 튜플 리스트. coords는 [(x,y), ...] — LINE/LWPOLYLINE은
    선분들, CIRCLE은 중심+반지름 그대로, ARC는 각도 구간을 직선으로 샘플링."""
    ops = []
    for o in objs:
        et = o.get("entity")
        if et == "LINE":
            s, e = o.get("start"), o.get("end")
            if s and e:
                ops.append(("poly", [(s[0], s[1]), (e[0], e[1])]))
        elif et == "CIRCLE":
            c, r = o.get("center"), o.get("radius")
            if c and r:
                ops.append(("circle", (c[0], c[1], r)))
        elif et == "ARC":
            c, r = o.get("center"), o.get("radius")
            a0, a1 = o.get("start_angle"), o.get("end_angle")
            if c and r and a0 is not None and a1 is not None:
                if a1 < a0:
                    a1 += 2 * math.pi
                pts = [
                    (c[0] + r * math.cos(a0 + (a1 - a0) * i / ARC_SEGMENTS),
                     c[1] + r * math.sin(a0 + (a1 - a0) * i / ARC_SEGMENTS))
                    for i in range(ARC_SEGMENTS + 1)
                ]
                ops.append(("poly", pts))
        elif et == "LWPOLYLINE":
            pts = o.get("points") or []
            if len(pts) >= 2:
                ops.append(("poly", [(p[0], p[1]) for p in pts]))
    return ops


def _bounds(ops, trim_pct=0.01):
    """상하위 trim_pct(기본 1%)를 제외한 범위로 맞춘다 — 단품 도면에 흔한
    인출선(리더선)이나 치수 보조선 하나가 본체 형상에서 훨씬 멀리 떨어진
    점까지 뻗어 있어서, 전체 min/max로 맞추면 진짜 형상이 캔버스 구석의
    점 하나로 쪼그라드는 사례가 실측 확인됨(sample_singlepart2.DWG — 99
    퍼센타일 X=1985인데 최댓값은 4000까지 튐). 범위 밖으로 나가는 선은
    viewBox 밖이라 자동으로 잘려 보이지 않는다(SVG 루트 기본 overflow:hidden)."""
    xs, ys = [], []
    for kind, data in ops:
        if kind == "poly":
            xs += [p[0] for p in data]
            ys += [p[1] for p in data]
        else:  # circle
            cx, cy, r = data
            xs += [cx - r, cx + r]
            ys += [cy - r, cy + r]
    if not xs:
        return None
    xs.sort(); ys.sort()
    n = len(xs)
    lo, hi = int(n * trim_pct), n - 1 - int(n * trim_pct)
    return xs[lo], xs[hi], ys[lo], ys[hi]


def build_thumbnail_svg(dwg_path: str, dwgread_exe: str) -> str:
    """DWG 파일 하나에서 도형만 뽑아 텍스트 없는 SVG 문자열을 반환.
    그릴 도형이 하나도 없으면(도면 파싱 실패 등) 빈 사각형만 있는 SVG를 반환."""
    data = run_dwgread_json(dwg_path, dwgread_exe)
    objs = data.get("OBJECTS", [])
    ops = _collect_geometry(objs)

    if len(ops) > MAX_ENTITIES:
        stride = len(ops) // MAX_ENTITIES + 1
        ops = ops[::stride]

    b = _bounds(ops)
    body = []
    if b:
        minx, maxx, miny, maxy = b
        w, h = max(maxx - minx, 1e-6), max(maxy - miny, 1e-6)
        scale = min((THUMB_W - 2 * PAD) / w, (THUMB_H - 2 * PAD) / h)
        offx = (THUMB_W - w * scale) / 2
        offy = (THUMB_H - h * scale) / 2

        def to_svg(x, y):
            # CAD는 Y가 위로 증가, SVG는 아래로 증가 — Y를 뒤집어서 눈에 보이는
            # 방향을 자연스럽게 맞춘다.
            return (x - minx) * scale + offx, (maxy - y) * scale + offy

        for kind, geom in ops:
            if kind == "poly":
                svg_pts = [to_svg(x, y) for x, y in geom]
                pts_attr = " ".join(f"{px:.1f},{py:.1f}" for px, py in svg_pts)
                body.append(f'<polyline points="{pts_attr}" />')
            else:
                cx, cy, r = geom
                scx, scy = to_svg(cx, cy)
                body.append(f'<circle cx="{scx:.1f}" cy="{scy:.1f}" r="{r * scale:.1f}" />')

    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {THUMB_W} {THUMB_H}" '
        f'width="{THUMB_W}" height="{THUMB_H}">'
        f'<rect width="{THUMB_W}" height="{THUMB_H}" fill="#1c2333"/>'
        f'<g fill="none" stroke="#7e9ab5" stroke-width="1">{"".join(body)}</g>'
        f'</svg>'
    )
    return svg
