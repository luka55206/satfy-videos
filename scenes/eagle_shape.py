"""An ORIGINAL bald-eagle drawing built from code (no traced or borrowed artwork).

Pose: wings raised and fanned out of the wrist like fingers, head turned left with a hard brow and a
deeply hooked beak, collar of neck feathers, scaled chest, strong legs with talons, seven-feather tail.
Every feather is a procedural blade (root, direction, length, width, curl).

    silhouette_coords()  the union outline (what the epicycles draw)
    paint(ctx, P, S)     the finished, inked, flag-coloured eagle (painter's order, dark outlines)
    python scenes/eagle_shape.py     -> output/eagle_shape_preview.png
"""
import math

import numpy as np
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union

RED, WHITE, BLUE = (0.86, 0.12, 0.20), (0.97, 0.97, 1.0), (0.13, 0.28, 0.72)
GOLD, DARK = (1.0, 0.78, 0.25), (0.05, 0.05, 0.08)


def _catmull(pts, per=12, closed=False):
    P = [np.array(p, float) for p in pts]
    P = ([P[-1]] + P + [P[0], P[1]]) if closed else ([P[0]] + P + [P[-1]])
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for k in range(per):
            u = k / per
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * u + (2 * p0 - 5 * p1 + 4 * p2 - p3) * u * u
                              + (-p0 + 3 * p1 - 3 * p2 + p3) * u ** 3))
    if not closed:
        out.append(P[-2])
    return [tuple(p) for p in out]


_SPINE = {}                                  # id(feather polygon) -> centre line (the quill)


def feather(root, ang, L, W, curl=0.0, steps=14):
    """A pointed blade from `root` along `ang` (deg, y up), bending `curl` degrees over its length."""
    pos = np.array(root, float)
    left, right, spine = [], [], []
    a = math.radians(ang)
    for i in range(steps + 1):
        s = i / steps
        hw = 0.5 * W * (0.72 + 0.28 * math.sin(math.pi * min(1.0, s * 1.05))) * (1 - s ** 2.6)
        d = np.array([math.cos(a), math.sin(a)])
        n = np.array([-d[1], d[0]])
        left.append(tuple(pos + n * hw))
        right.append(tuple(pos - n * hw))
        spine.append(tuple(pos))
        a += math.radians(curl) / steps
        pos = pos + d * (L / steps)
    poly = Polygon(left + right[::-1])
    _SPINE[id(poly)] = spine
    return poly


SHOULDER, ELBOW, WRIST = np.array((0.14, 0.30)), np.array((0.40, 0.50)), np.array((0.62, 0.64))


def _arm(u):
    if u < 0.5:
        return SHOULDER + (ELBOW - SHOULDER) * (u / 0.5)
    return ELBOW + (WRIST - ELBOW) * ((u - 0.5) / 0.5)


def _mir(poly):
    m = Polygon([(-x, y) for x, y in poly.exterior.coords])
    if id(poly) in _SPINE:
        _SPINE[id(m)] = [(-x, y) for x, y in _SPINE[id(poly)]]
    return m


def _wing():
    """Right wing parts: [(polygon, role, index)] in painter's order, back -> front."""
    parts = []
    for i in range(9):                                        # primaries fan out of the wrist
        j = i / 8
        root = WRIST + np.array((0.015, 0.0)) + j * np.array((0.10, 0.07))
        parts.append((feather(root, -58 + 92 * j ** 0.9, 0.44 + 0.05 * math.sin(math.pi * j), 0.105, curl=-9 * j),
                      "flight", i))
    for i in range(9):                                        # secondaries hang from the arm
        u = i / 8
        parts.append((feather(_arm(u * 0.97), -104 + 44 * u, 0.52 + 0.07 * u, 0.13, curl=-6 * u), "flight", i + 1))
    for i in range(9):                                        # greater coverts
        u = i / 8
        parts.append((feather(_arm(u * 0.97) + np.array((0.0, 0.012)), -104 + 44 * u + 3, 0.32 + 0.03 * u, 0.125,
                              curl=-5 * u), "covert", i))
    for i in range(6):                                        # primary coverts
        j = i / 5
        root = WRIST + np.array((0.0, 0.02)) + j * np.array((0.09, 0.05))
        parts.append((feather(root, -52 + 80 * j, 0.23, 0.10, curl=-6 * j), "covert", i + 1))
    for i in range(10):                                       # lesser coverts: the blue shoulder
        u = i / 9
        parts.append((feather(_arm(u * 0.99) + np.array((0.0, 0.03)), -100 + 40 * u + 4, 0.17, 0.11, curl=-4 * u),
                      "lesser", i))
    parts.append((LineString([tuple(SHOULDER), tuple(ELBOW), tuple(WRIST)]).buffer(0.05), "arm", 0))
    return parts


def _head_xf():
    """local head coords (eye at the origin, beak to the left) -> eagle space"""
    k, ex, ey = 1.22, -0.05, 0.60
    return lambda x, y: (ex + x * k, ey + y * k)


def build():
    """-> dict(parts=[(Polygon, role, idx)] painter's order, lines, eye, brow, silhouette)"""
    wing = _wing()
    parts = []
    # tail behind everything
    for i, (ang, L) in enumerate(zip(np.linspace(-124, -56, 7), (0.60, 0.67, 0.72, 0.75, 0.72, 0.67, 0.60))):
        parts.append((feather((0.0, -0.26), ang, L, 0.135, curl=(-6 if ang > -90 else 6)), "tail", i))
    for p, role, idx in wing:
        parts.append((_mir(p), role, idx))
    for p, role, idx in wing:
        parts.append((p, role, idx))
    body = Polygon(_catmull([(0.0, 0.38), (0.15, 0.32), (0.205, 0.08), (0.185, -0.18), (0.11, -0.34), (0.0, -0.38),
                             (-0.11, -0.34), (-0.185, -0.18), (-0.205, 0.08), (-0.15, 0.32)], 10, closed=True))
    parts.append((body, "body", 0))
    for sx in (-1, 1):                                        # feathered thighs, legs, talons
        parts.append((Polygon([(sx * (0.15 + 0.08 * math.cos(t)), -0.32 + 0.12 * math.sin(t))
                               for t in np.linspace(0, 2 * math.pi, 24, endpoint=False)]), "pants", 0))
        parts.append((LineString([(sx * 0.15, -0.40), (sx * 0.19, -0.54), (sx * 0.22, -0.66)]).buffer(0.058), "leg", 0))
        for ang, L in ((-96, 0.23), (-121, 0.21), (-71, 0.21), (-40, 0.15)):
            a = ang if sx > 0 else -180 - ang
            parts.append((feather((sx * 0.22, -0.66), a, L, 0.085, curl=(30 if sx > 0 else -30)), "claw", 0))
    # head, turned left; collar of neck feathers behind it
    for i in range(8):
        parts.append((feather((0.08 - 0.012 * i, 0.50 - 0.025 * i), -30 - 13 * i, 0.22, 0.10, curl=8), "collar", i))
    H = _head_xf()
    head_pts = [(0.13, -0.26), (0.155, -0.15), (0.17, -0.03), (0.16, 0.08), (0.10, 0.17), (0.00, 0.20), (-0.07, 0.185),
                (-0.125, 0.145), (-0.165, 0.10), (-0.225, 0.075), (-0.285, 0.035), (-0.325, -0.03),
                (-0.345, -0.11), (-0.34, -0.19), (-0.305, -0.165), (-0.285, -0.125), (-0.245, -0.105),
                (-0.175, -0.10), (-0.14, -0.13), (-0.115, -0.19), (-0.10, -0.27)]
    parts.append((Polygon([H(x, y) for x, y in _catmull(head_pts, 6, closed=True)]), "head", 0))
    beak_pts = [(-0.165, 0.10), (-0.225, 0.075), (-0.285, 0.035), (-0.325, -0.03), (-0.345, -0.11), (-0.34, -0.19),
                (-0.305, -0.165), (-0.285, -0.125), (-0.245, -0.105), (-0.175, -0.10)]
    parts.append((Polygon([H(x, y) for x, y in _catmull(beak_pts, 6, closed=True)]), "beak", 0))
    sil = unary_union([p for p, _, _ in parts if _ != "beak"]).buffer(0.004).buffer(-0.004)
    sil = unary_union([sil] + [p for p, r, _ in parts if r == "beak"]).buffer(0.002).buffer(-0.002)
    if sil.geom_type == "MultiPolygon":
        sil = max(sil.geoms, key=lambda g: g.area)
    sil = Polygon(sil.exterior.coords)
    # chest scales
    lines = []
    for r, y in enumerate(np.arange(0.24, -0.26, -0.068)):
        half = max(0.05, 0.165 - 0.05 * abs(y - 0.03) * 1.5)
        for x in np.arange(-half, half + 1e-6, 0.07) + (0.035 if r % 2 else 0.0):
            if abs(x) <= half:
                lines.append([(x + 0.035 * math.cos(t), y + 0.045 * math.sin(t)) for t in np.linspace(math.pi, 2 * math.pi, 12)])
    eye = H(-0.075, 0.03)
    brow = [H(-0.17, 0.062), H(-0.115, 0.085), H(-0.05, 0.118)]
    mouth = [H(-0.30, -0.065), H(-0.22, -0.075), H(-0.15, -0.085)]
    return {"parts": parts, "lines": lines, "eye": (eye[0], eye[1], 0.030), "brow": brow, "mouth": mouth,
            "silhouette": sil}


_BUILT = None


def _b():
    global _BUILT
    if _BUILT is None:
        _BUILT = build()
    return _BUILT


def silhouette_coords():
    return list(_b()["silhouette"].exterior.coords)


def _color(role, idx):
    if role in ("flight", "tail"):
        return RED if idx % 2 == 0 else WHITE
    if role == "covert":
        return WHITE if idx % 2 == 0 else RED
    if role in ("lesser", "arm", "body"):
        return BLUE
    if role in ("head", "collar"):
        return WHITE
    return GOLD                                              # beak, claws, legs, pants


def paint(ctx, P, S, alpha=1.0):
    """Draw the finished eagle. P(x, y) -> screen; S = pixels per unit (for line widths)."""
    E = _b()

    def path(pts, close=True):
        ctx.new_path()
        ctx.move_to(*P(*pts[0]))
        for p in pts[1:]:
            ctx.line_to(*P(*p))
        if close:
            ctx.close_path()
    lw = max(1.5, S * 0.0075)
    for poly, role, idx in E["parts"]:
        col = _color(role, idx)
        if role == "pants":
            col = WHITE
        path(list(poly.exterior.coords))
        ctx.set_source_rgba(*col, alpha)
        ctx.fill_preserve()
        ctx.set_source_rgba(*DARK, 0.95 * alpha)
        ctx.set_line_width(lw)
        ctx.set_line_join(1)
        ctx.stroke()
        if role == "lesser":                                  # a star on every blue shoulder feather
            c = poly.centroid
            x, y = P(c.x, c.y)
            ctx.set_source_rgba(1, 1, 1, 0.95 * alpha)
            r = S * 0.016
            ctx.new_path()
            for k in range(10):
                rr = r if k % 2 == 0 else r * 0.42
                a = -math.pi / 2 + k * math.pi / 5
                (ctx.move_to if k == 0 else ctx.line_to)(x + rr * math.cos(a), y + rr * math.sin(a))
            ctx.close_path()
            ctx.fill()
    for ln in E["lines"]:                                     # chest scales
        path(ln, close=False)
        ctx.set_source_rgba(*WHITE, 0.75 * alpha)
        ctx.set_line_width(lw)
        ctx.stroke()
    for ln, w in ((E["brow"], 2.6), (E["mouth"], 1.4)):
        path(ln, close=False)
        ctx.set_source_rgba(*DARK, alpha)
        ctx.set_line_width(lw * w)
        ctx.set_line_cap(1)
        ctx.stroke()
    ex, ey, er = E["eye"]
    x, y = P(ex, ey)
    ctx.set_source_rgba(1.0, 0.85, 0.3, alpha)                # amber iris, dark pupil, glint
    ctx.new_sub_path()
    ctx.arc(x, y, er * S, 0, 2 * math.pi)
    ctx.fill()
    ctx.set_source_rgba(*DARK, alpha)
    ctx.new_sub_path()
    ctx.arc(x, y, er * S * 0.55, 0, 2 * math.pi)
    ctx.fill()
    ctx.set_source_rgba(1, 1, 1, alpha)
    ctx.new_sub_path()
    ctx.arc(x - er * S * 0.22, y - er * S * 0.25, er * S * 0.16, 0, 2 * math.pi)
    ctx.fill()


if __name__ == "__main__" and "--lines" not in __import__("sys").argv:
    import cairo
    from pathlib import Path
    W, H = 1400, 1000
    s = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    c = cairo.Context(s)
    c.set_source_rgb(0.07, 0.075, 0.09)
    c.paint()
    S = 430
    paint(c, lambda x, y: (W / 2 + S * x, H / 2 + 60 - S * y), S)
    out = Path(__file__).resolve().parent.parent / "output" / "eagle_shape_preview.png"
    out.parent.mkdir(exist_ok=True)
    s.write_to_png(str(out))
    print("bounds", [round(v, 2) for v in _b()["silhouette"].bounds], "->", out)


def lineart():
    """The inked drawing as LINES: (silhouette ring, [strokes]) - every visible feather edge, quill, chest scale,
    talon, beak, eye and brow, hidden parts removed (painter's order), strokes ordered to keep the pen's
    travel short. Strokes are coordinate lists in eagle space."""
    from shapely.ops import linemerge
    E = _b()
    parts, sil = E["parts"], E["silhouette"]
    polys = [p for p, _, _ in parts]
    n = len(polys)
    visible, acc = [None] * n, None
    for i in range(n - 1, -1, -1):
        visible[i] = polys[i] if acc is None else polys[i].difference(acc)
        acc = polys[i] if acc is None else unary_union([acc, polys[i]])
    segs = []
    for v in visible:
        if not v.is_empty:
            segs.append(v.boundary)
    for i, (poly, role, idx) in enumerate(parts):                      # quills of the long feathers
        if role in ("flight", "tail", "covert") and id(poly) in _SPINE and not visible[i].is_empty:
            sp = _SPINE[id(poly)]
            q = LineString(sp[2:int(len(sp) * 0.82)])
            segs.append(q.intersection(visible[i].buffer(-0.012)))
    body_i = [i for i, (_, r, _) in enumerate(parts) if r == "body"][0]
    for ln in E["lines"]:                                              # chest scales
        segs.append(LineString(ln).intersection(visible[body_i].buffer(-0.008)))
    ex, ey, er = E["eye"]
    segs.append(Point(ex, ey).buffer(er, 12).exterior)
    segs.append(Point(ex, ey).buffer(er * 0.5, 8).exterior)
    segs.append(LineString(E["brow"]))
    segs.append(LineString(E["mouth"]))
    lines = unary_union(segs).difference(sil.exterior.buffer(0.007))
    merged = linemerge(lines) if lines.geom_type != "LineString" else lines
    geoms = [merged] if merged.geom_type == "LineString" else list(merged.geoms)
    strokes = [list(g.coords) for g in geoms if g.length > 0.03]
    ring = list(sil.exterior.coords)[:-1]
    # greedy order, starting near the end of the silhouette ring; strokes may be reversed
    cur = np.array(ring[0])
    left_ = [np.array(s_) for s_ in strokes]
    ordered = []
    while left_:
        best, bi, brev = 1e9, 0, False
        for k, st in enumerate(left_):
            d0, d1 = np.linalg.norm(st[0] - cur), np.linalg.norm(st[-1] - cur)
            if min(d0, d1) < best:
                best, bi, brev = min(d0, d1), k, d1 < d0
        st = left_.pop(bi)
        st = st[::-1] if brev else st
        ordered.append([tuple(p) for p in st])
        cur = st[-1]
    return ring, ordered


if __name__ == "__main__" and "--lines" in __import__("sys").argv:
    import cairo
    from pathlib import Path
    ring, strokes = lineart()
    W, H = 1400, 1000
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    c = cairo.Context(surf)
    c.set_source_rgb(0.07, 0.075, 0.09)
    c.paint()
    S = 430

    def Pp(x, y):
        return W / 2 + S * x, H / 2 + 60 - S * y
    c.set_source_rgb(1, 1, 1)
    c.set_line_width(3)
    c.move_to(*Pp(*ring[0]))
    for pt in ring[1:]:
        c.line_to(*Pp(*pt))
    c.close_path()
    c.stroke()
    c.set_line_width(2)
    for st in strokes:
        c.move_to(*Pp(*st[0]))
        for pt in st[1:]:
            c.line_to(*Pp(*pt))
        c.stroke()
    out = Path(__file__).resolve().parent.parent / "output" / "eagle_lineart_preview.png"
    surf.write_to_png(str(out))
    L = sum(np.linalg.norm(np.diff(np.array(st), axis=0), axis=1).sum() for st in strokes)
    print("strokes", len(strokes), "inline length", round(L, 1), "ring length",
          round(float(np.linalg.norm(np.diff(np.array(ring + [ring[0]]), axis=0), axis=1).sum()), 1), "->", out)
