"""MATH ART — long-form (≈9 min, 16:9): 65 animated equations in 8 chapters, each with its live equation on screen.

Format after an owner-supplied reference ("Math is Art", a run of animated equations on a dark grid); every equation
choice, the look (neon glow on a dark grid), the order, the chapters and the soundtrack are ours.

Chapters: 1 Circles & Multiplication · 2 Spirographs · 3 Lissajous & Harmonographs · 4 Waves · 5 Hidden Curves
(implicit F(x, y) = c) · 6 Spirals & Sunflowers · 7 Famous Curves · 8 Fractals. Hook first: the times-table circle.
Soundtrack (original, synthesised): a slow 3/4 piano waltz on alternating maj7/m7 chords (one pair per chapter);
the right-hand melody is generated from each piece's motion (probe(u) → pentatonic note), plus a soft pad and a bell
at every new equation.

Render in parallel chunks, then assemble:
  python scenes/math_art.py -- --part k --parts N      (k = 0..N-1)   → output/math_art_<label>_seg<k>.mp4
  python scenes/math_art.py -- --assemble --parts N                   → output/math_art_<label>_16x9.mp4 (+ audio)
"""
import math
import subprocess
import sys
from pathlib import Path

import cairo
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib import audio, kit, studio  # noqa: E402
from lib.kit import FPS, arg  # noqa: E402
from lib.layouts import get_layout  # noqa: E402
from lib.studio import Canvas, VideoWriter  # noqa: E402

SCENE = "math_art"
W_, H_ = 1920, 1080
CX, CY = 960.0, 575.0
GOLD = (1.0, 0.82, 0.40)
BG = (0.035, 0.045, 0.085)
PHI = (1 + 5 ** 0.5) / 2


def hsv(h, s=0.65, v=1.0):
    h = h % 1.0
    i = int(h * 6)
    f = h * 6 - i
    p, q, t = v * (1 - s), v * (1 - s * f), v * (1 - s * (1 - f))
    return [(v, t, p), (q, v, p), (p, v, t), (p, q, v), (t, p, v), (v, p, q)][i % 6]


def ease(u):
    return 0.5 - 0.5 * math.cos(math.pi * min(1.0, max(0.0, u)))


def lerp(a, b, u):
    return a + (b - a) * u


def neon(c, paths, col, width=3.0, alpha=0.95, glow=True):
    if glow:
        c.polylines(paths, col, width=width * 4.5, alpha=0.10 * alpha)
    c.polylines(paths, col, width=width, alpha=alpha)


# ======================================================================== pieces
PIECES = []          # dicts: dur, draw(sc, u), eq(u) -> str, title, probe(u), chapter


def piece(chapter, dur, eq, draw, probe=None, title=None):
    PIECES.append(dict(chapter=chapter, dur=dur, eq=eq, draw=draw, title=title,
                       probe=probe or (lambda u, s=len(PIECES): 0.5 + 0.45 * math.sin(2 * math.pi * 1.3 * u + s))))


# ---------- 1. circles & multiplication
def times_table(ch, N, k0, k1, hue0, dur=8.2):
    R = 430.0
    pts = [(CX + R * math.cos(2 * math.pi * i / N - math.pi / 2), CY + R * math.sin(2 * math.pi * i / N - math.pi / 2))
           for i in range(N)]

    def P(v):
        a = 2 * math.pi * v / N - math.pi / 2
        return CX + R * math.cos(a), CY + R * math.sin(a)

    def draw(sc, u):
        k = lerp(k0, k1, ease(u))
        bins = {}
        for i in range(N):
            x1, y1 = P((k * i) % N)
            bins.setdefault(int(12 * i / N), []).append((pts[i][0], pts[i][1], x1, y1))
        for b, segs in bins.items():
            col = hsv(hue0 + b / 12 * 0.6, 0.55)
            sc.c.lines(segs, col, width=1.6, alpha=0.75)
        sc.c.ring(CX, CY, R, (0.8, 0.85, 1.0), width=2.5, alpha=0.5)

    piece(ch, dur, lambda u: f"connect  n → {lerp(k0, k1, ease(u)):.2f} · n     (mod {N})", draw,
          probe=lambda u: (lerp(k0, k1, ease(u)) % 1.0))


def rose(ch, k0, k1, col, dur=8.2):
    th = np.linspace(0, 2 * math.pi * 12, 3000)

    def draw(sc, u):
        k = lerp(k0, k1, ease(u))
        r = 420 * np.cos(k * th)
        neon(sc.c, [list(zip(CX + r * np.cos(th), CY - r * np.sin(th)))], col, width=2.0, alpha=0.85)

    piece(ch, dur, lambda u: f"r = cos({lerp(k0, k1, ease(u)):.3f} θ)", draw, probe=lambda u: lerp(k0, k1, ease(u)) % 1.0)


def maurer(ch, n, d0, d1, col, dur=8.2):
    thf = np.linspace(0, 2 * math.pi, 1200)

    def draw(sc, u):
        d = lerp(d0, d1, ease(u))
        i = np.arange(361)
        th = np.radians(i * d)
        r = 420 * np.sin(n * th)
        sc.c.polylines([list(zip(CX + r * np.cos(th), CY - r * np.sin(th)))], col, width=1.4, alpha=0.8)
        rf = 420 * np.sin(n * thf)
        neon(sc.c, [list(zip(CX + rf * np.cos(thf), CY - rf * np.sin(thf)))], GOLD, width=2.5, alpha=0.6)

    piece(ch, dur, lambda u: f"r = sin({n}θ),   θ = k · {lerp(d0, d1, ease(u)):.2f}°", draw,
          probe=lambda u: (lerp(d0, d1, ease(u)) / 3) % 1.0, title="Maurer rose")


# ---------- 2. spirographs
def spiro(ch, R0, r0, d0, epi, col, dur=8.4, start=0.0, speed=0.88, layers=1):
    g = math.gcd(R0, r0)
    T = 2 * math.pi * r0 / g
    if epi:
        ext = R0 + r0 + d0
        fx = lambda t: (R0 + r0) * np.cos(t) - d0 * np.cos((R0 + r0) / r0 * t)    # noqa: E731
        fy = lambda t: (R0 + r0) * np.sin(t) - d0 * np.sin((R0 + r0) / r0 * t)    # noqa: E731
        eq = f"x = {R0 + r0}cos t − {d0}cos({(R0 + r0) / r0:.3g}t),   y = {R0 + r0}sin t − {d0}sin({(R0 + r0) / r0:.3g}t)"
    else:
        ext = R0 - r0 + d0
        fx = lambda t: (R0 - r0) * np.cos(t) + d0 * np.cos((R0 - r0) / r0 * t)    # noqa: E731
        fy = lambda t: (R0 - r0) * np.sin(t) - d0 * np.sin((R0 - r0) / r0 * t)    # noqa: E731
        eq = f"x = {R0 - r0}cos t + {d0}cos({(R0 - r0) / r0:.3g}t),   y = {R0 - r0}sin t − {d0}sin({(R0 - r0) / r0:.3g}t)"
    S = 430.0 / max(ext, R0)

    def draw(sc, u):
        tt = T * min(1.0, start + (1 - start) * u / speed)
        t = np.linspace(0, max(tt, 1e-3), max(2, int(2400 * tt / T)))
        for j in range(layers - 1, 0, -1):                     # extra nested copies (smaller pen arm)
            q = 1 - 0.28 * j
            cr_ = (R0 + r0) if epi else (R0 - r0)
            sg = -1 if epi else 1
            fr_ = ((R0 + r0) if epi else (R0 - r0)) / r0
            xj = CX + S * (cr_ * np.cos(t) + sg * d0 * q * np.cos(fr_ * t))
            yj = CY - S * (cr_ * np.sin(t) - d0 * q * np.sin(fr_ * t))
            neon(sc.c, [list(zip(xj, yj))], hsv(0.55 + 0.17 * j, 0.55), width=2.6)
        xs, ys = CX + S * fx(t), CY - S * fy(t)
        neon(sc.c, [list(zip(xs, ys))], col, width=2.2 if layers == 1 else 3.0)
        sc.c.ring(CX, CY, S * R0, (0.75, 0.8, 0.95), width=2, alpha=0.30)
        if tt < T * 0.999:                                   # the rolling circle + arm
            cr = (R0 + r0) if epi else (R0 - r0)
            ox, oy = CX + S * cr * math.cos(tt), CY - S * cr * math.sin(tt)
            sc.c.ring(ox, oy, S * r0, (0.75, 0.8, 0.95), width=2, alpha=0.45)
            sc.c.line(ox, oy, xs[-1], ys[-1], (0.9, 0.9, 1.0), width=2, alpha=0.6)
            sc.c.glow(xs[-1], ys[-1], 8, col, strength=0.8)
            sc.c.circle(xs[-1], ys[-1], 6, (1, 1, 1))

    piece(ch, dur, lambda u: eq, draw,
          probe=lambda u: 0.5 - 0.5 * float(fy(np.array([T * min(1.0, start + (1 - start) * u / speed)]))[0]) / ext,
          title=("epitrochoid" if epi else "hypotrochoid") + f"   R = {R0},  r = {r0},  d = {d0}")


# ---------- 3. lissajous & harmonographs
def lissajous(ch, a, b, col, dur=8.0):
    t = np.linspace(0, 2 * math.pi, 1600)

    def draw(sc, u):
        dl = math.pi * ease(u)
        xs, ys = CX + 430 * np.sin(a * t + dl), CY - 400 * np.sin(b * t)
        neon(sc.c, [list(zip(xs, ys))], col, width=2.6)
        tp = 2 * math.pi * 2 * u
        px, py = CX + 430 * math.sin(a * tp + dl), CY - 400 * math.sin(b * tp)
        sc.c.glow(px, py, 9, col, strength=0.8)
        sc.c.circle(px, py, 6, (1, 1, 1))

    piece(ch, dur, lambda u: f"x = sin({a}t + {math.pi * ease(u):.2f}),   y = sin({b}t)", draw,
          probe=lambda u: 0.5 + 0.5 * math.sin(b * 2 * math.pi * 2 * u))


def harmonograph(ch, f, p, d, col, dur=9.0):
    f1, f2, f3, f4 = f
    p1, p2, p3, p4 = p

    def xy(t):
        e = np.exp(-d * t)
        return (e * (np.sin(f1 * t + p1) + np.sin(f2 * t + p2)), e * (np.sin(f3 * t + p3) + np.sin(f4 * t + p4)))

    def draw(sc, u):
        tt = 80 * min(1.0, u / 0.9)
        t = np.linspace(0, max(tt, 1e-3), max(2, int(9000 * tt / 80)))
        x, y = xy(t)
        xs, ys = CX + 215 * x, CY - 215 * y
        sc.c.polylines([list(zip(xs, ys))], col, width=1.3, alpha=0.75)
        sc.c.glow(xs[-1], ys[-1], 8, col, strength=0.8)
        sc.c.circle(xs[-1], ys[-1], 5, (1, 1, 1))

    piece(ch, dur, lambda u: f"x = e^(−{d}t)[sin({f1}t) + sin({f2}t + {p2:.1f})],   y = e^(−{d}t)[sin({f3}t) + sin({f4}t + {p4:.1f})]",
          draw, probe=lambda u: 0.5 + 0.25 * float(xy(np.array([80 * min(1.0, u / 0.9)]))[1][0]), title="harmonograph")


# ---------- 4. waves
def wave(ch, eqf, fn, layers, col0, dur=8.0, xr=8.0, ys=110.0, title=None, probe=None):
    x = np.linspace(-xr, xr, 1400)

    def draw(sc, u):
        for j, (off, a) in enumerate(layers):
            y = fn(x, u, off)
            col = hsv(col0 + 0.05 * j, 0.6)
            neon(sc.c, [list(zip(CX + x * (900 / xr), CY - ys * y))], col, width=2.4, alpha=a, glow=(j == 0))

    piece(ch, dur, eqf, draw, title=title, probe=probe)


# ---------- 5. hidden curves (implicit)
def implicit(ch, F, c0, c1, ext, col, eqf, dur=8.4, title=None):
    def draw(sc, u):
        sc.implicit(lambda X, Y: F(X, Y) - lerp(c0, c1, ease(u)), ext, col)

    piece(ch, dur, lambda u: eqf(lerp(c0, c1, ease(u))), draw, title=title,
          probe=lambda u: ease(u))


# ---------- 6. spirals & sunflowers
def spiral_arms(ch, kind, arms, col0, dur=8.2):
    th = np.linspace(0, 6 * math.pi, 900)

    def draw(sc, u):
        rot = 2 * math.pi * 0.5 * u
        for j in range(arms):
            a0 = rot + 2 * math.pi * j / arms
            if kind == "arch":
                r = 22 * th
            elif kind == "log":
                r = 8 * np.exp(0.2 * th)
            else:
                r = 150 * np.sqrt(th)
            r = np.minimum(r, 470)
            col = hsv(col0 + j / arms * 0.5, 0.6)
            neon(sc.c, [list(zip(CX + r * np.cos(th + a0), CY - r * np.sin(th + a0)))], col, width=2.2,
                 glow=(j % 2 == 0))
            if kind == "fermat":
                neon(sc.c, [list(zip(CX - r * np.cos(th + a0), CY + r * np.sin(th + a0)))], col, width=2.2, glow=False)

    eqs = {"arch": "r = θ", "log": "r = e^(0.2θ)", "fermat": "r = ±√θ"}
    piece(ch, dur, lambda u: f"{eqs[kind]}    ({arms} arms, turning)", draw,
          title={"arch": "Archimedean spiral", "log": "logarithmic spiral", "fermat": "Fermat's spiral"}[kind])


def phyllo(ch, a0, a1, grow, dur=8.6):
    def draw(sc, u):
        n = int(1400 * min(1.0, u / 0.85)) if grow else 1100
        alpha = lerp(a0, a1, ease(u))
        i = np.arange(1, n + 1)
        r = 13.5 * np.sqrt(i)
        th = np.radians(alpha) * i
        xs, ys = CX + r * np.cos(th), CY - r * np.sin(th)
        for b in range(8):
            sel = (i % 8) == b
            col = hsv(0.08 + 0.05 * b, 0.65)
            for x_, y_ in zip(xs[sel], ys[sel]):
                sc.c.circle(float(x_), float(y_), 4.2, col, alpha=0.9)

    piece(ch, dur, lambda u: f"seed n:  r = √n,   θ = n × {lerp(a0, a1, ease(u)):.3f}°", draw,
          title="the golden angle  137.508°" if not grow else "a sunflower, seed by seed",
          probe=lambda u: (lerp(a0, a1, ease(u)) % 1.0))


def superformula(ch, m0, m1, n1, n2, n3, col, dur=8.2):
    th = np.linspace(0, 2 * math.pi * 4, 4000)

    def draw(sc, u):
        m = lerp(m0, m1, ease(u))
        r = (np.abs(np.cos(m * th / 4)) ** n2 + np.abs(np.sin(m * th / 4)) ** n3) ** (-1 / n1)
        r = r / np.max(r)
        for j, s in enumerate((430, 300, 180)):
            neon(sc.c, [list(zip(CX + s * r * np.cos(th), CY - s * r * np.sin(th)))], hsv(col + 0.08 * j, 0.6),
                 width=2.0, glow=(j == 0))

    piece(ch, dur, lambda u: f"r = (|cos({lerp(m0, m1, ease(u)):.2f}θ/4)|^{n2} + |sin({lerp(m0, m1, ease(u)):.2f}θ/4)|^{n3})^(−1/{n1})",
          draw, title="Gielis superformula", probe=lambda u: lerp(m0, m1, ease(u)) % 1.0)


# ---------- 7. famous curves
def pen_curve(ch, fx, fy, t1, S, col, eq, title, dur=8.6, oy=0.0):
    def draw(sc, u):
        tt = t1 * min(1.0, u / 0.85)
        t = np.linspace(0, max(tt, 1e-3), max(2, int(5000 * tt / t1)))
        xs, ys = CX + S * fx(t), CY - S * (fy(t) + oy)
        neon(sc.c, [list(zip(xs, ys))], col, width=2.4)
        if u < 0.86:
            sc.c.glow(xs[-1], ys[-1], 9, col, strength=0.8)
            sc.c.circle(xs[-1], ys[-1], 6, (1, 1, 1))

    piece(ch, dur, lambda u: eq, draw, title=title,
          probe=lambda u: 0.5 + 0.08 * float(fy(np.array([t1 * min(1.0, u / 0.85)]))[0]))


def cardioid_circles(ch, dur=8.6):
    R = 150.0

    def draw(sc, u):
        n = int(60 * min(1.0, u / 0.8))
        fx_, fy_ = CX - 2 * R * 0.35, CY                   # the fixed point on the base circle
        bx = fx_ + R
        sc.c.ring(bx, CY, R, GOLD, width=2.5, alpha=0.6)
        for i in range(n):
            a = 2 * math.pi * i / 60
            ox, oy = bx + R * math.cos(a), CY - R * math.sin(a)
            rr = math.hypot(ox - fx_, oy - fy_)
            sc.c.ring(ox, oy, rr, hsv(0.9 + i / 60 * 0.4, 0.55), width=1.5, alpha=0.55)

    piece(ch, dur, lambda u: "circles centred on a circle, all through one point", draw,
          title="a cardioid from 60 circles")


def ladder(ch, dur=8.4):
    L = 430.0

    def draw(sc, u):
        n = int(90 * min(1.0, u / 0.8))
        segs = []
        for i in range(n):
            a = 2 * math.pi * i / 90
            segs.append((CX + L * math.cos(a), CY, CX, CY - L * math.sin(a)))
        sc.c.lines(segs, (0.55, 0.85, 1.0), width=1.4, alpha=0.6)
        t = np.linspace(0, 2 * math.pi, 600)
        if u > 0.82:
            neon(sc.c, [list(zip(CX + L * np.cos(t) ** 3, CY - L * np.sin(t) ** 3))], GOLD, width=3,
                 alpha=min(1.0, (u - 0.82) / 0.1))

    piece(ch, dur, lambda u: "x^(2/3) + y^(2/3) = 1", draw, title="an astroid from a sliding ladder")


def parabola_lines(ch, dur=8.0):
    def draw(sc, u):
        n = int(30 * min(1.0, u / 0.8))
        segs = []
        for qx, qy in ((1, 1), (-1, 1), (-1, -1), (1, -1)):
            for i in range(n + 1):
                a = 430 * i / 30
                segs.append((CX + qx * a, CY, CX, CY - qy * (430 - a)))
        sc.c.lines(segs, (1.0, 0.55, 0.75), width=1.5, alpha=0.75)

    piece(ch, dur, lambda u: "only straight lines:  (k, 0) → (0, 30 − k)", draw, title="straight lines, curved edges")


def epicycloid_sweep(ch, dur=8.6):
    t = np.linspace(0, 2 * math.pi * 7, 5000)

    def draw(sc, u):
        k = lerp(1.0, 7.0, ease(u))
        x = (k + 1) * np.cos(t) - np.cos((k + 1) * t)
        y = (k + 1) * np.sin(t) - np.sin((k + 1) * t)
        S = 420 / (k + 2)
        neon(sc.c, [list(zip(CX + S * x, CY - S * y))], hsv(0.55 + 0.05 * k), width=2.2)

    piece(ch, dur, lambda u: f"x = {lerp(1, 7, ease(u)) + 1:.2f}cos t − cos({lerp(1, 7, ease(u)) + 1:.2f}t),   y = {lerp(1, 7, ease(u)) + 1:.2f}sin t − sin({lerp(1, 7, ease(u)) + 1:.2f}t)",
          draw, title="epicycloid: cardioid → nephroid → …", probe=lambda u: lerp(1, 7, ease(u)) % 1.0)


def superellipse(ch, dur=8.2):
    t = np.linspace(0, 2 * math.pi, 900)

    def draw(sc, u):
        for j in range(10):
            p = lerp(0.35, 6.0, ease(max(0.0, u - 0.035 * j)))
            c_, s_ = np.cos(t), np.sin(t)
            x = np.sign(c_) * np.abs(c_) ** (2 / p)
            y = np.sign(s_) * np.abs(s_) ** (2 / p)
            neon(sc.c, [list(zip(CX + 400 * x, CY - 400 * y))], hsv(0.75 - 0.04 * j, 0.6), width=2.2,
                 alpha=1.0 - 0.08 * j, glow=(j == 0))

    piece(ch, dur, lambda u: f"|x|^{lerp(0.35, 6.0, ease(u)):.2f} + |y|^{lerp(0.35, 6.0, ease(u)):.2f} = 1", draw,
          title="superellipse: star → circle → square")


# ---------- 8. fractals
def koch(ch, dur=10.0):
    def level(n):
        a = np.array([[0, 1], [math.sqrt(3) / 2, -0.5], [-math.sqrt(3) / 2, -0.5], [0, 1]]) * 1.0
        pts = [tuple(p) for p in a]
        for _ in range(n):
            new = []
            for (x0, y0), (x1, y1) in zip(pts[:-1], pts[1:]):
                dx, dy = (x1 - x0) / 3, (y1 - y0) / 3
                p1 = (x0 + dx, y0 + dy)
                p3 = (x0 + 2 * dx, y0 + 2 * dy)
                p2 = (p1[0] + dx * 0.5 + dy * math.sqrt(3) / 2, p1[1] + dy * 0.5 - dx * math.sqrt(3) / 2)
                new += [(x0, y0), p1, p2, p3]
            new.append(pts[-1])
            pts = new
        return pts

    LV = [level(n) for n in range(6)]

    def draw(sc, u):
        n = min(5, int(u * 6))
        pts = LV[n]
        neon(sc.c, [[(CX + 430 * x, CY - 430 * y + 60) for x, y in pts]], (0.6, 0.85, 1.0), width=2.2)

    piece(ch, dur, lambda u: f"Koch snowflake, level {min(5, int(u * 6))}:  every edge → 4 edges × 1/3", draw,
          title="infinite edge, finite area", probe=lambda u: min(5, int(u * 6)) / 5)


def dragon(ch, dur=10.0):
    turns = [1]
    for _ in range(12):
        turns = turns + [1] + [-t for t in turns[::-1]]
    dirs = [(1, 0), (0, 1), (-1, 0), (0, -1)]
    x, y, d = 0, 0, 0
    pts = [(0, 0)]
    for tr in [0] + turns:
        d = (d + tr) % 4
        x, y = x + dirs[d][0], y + dirs[d][1]
        pts.append((x, y))
    P = np.array(pts, float)
    mn, mx = P.min(0), P.max(0)
    S = min(1500 / (mx[0] - mn[0]), 820 / (mx[1] - mn[1]))
    P = (P - (mn + mx) / 2) * S
    n_all = len(P)

    def draw(sc, u):
        k = max(2, int(n_all * min(1.0, u / 0.88)))
        for b in range(8):
            i0, i1 = n_all * b // 8, min(k, n_all * (b + 1) // 8 + 1)
            if i1 - i0 < 2:
                continue
            seg = P[i0:i1]
            sc.c.polylines([list(zip(CX + seg[:, 0], CY - seg[:, 1]))], hsv(0.55 + b * 0.06, 0.6), width=1.8,
                           alpha=0.9)

    piece(ch, dur, lambda u: "fold a strip in half 12 times, unfold at 90°", draw, title="the dragon curve")


def sierpinski(ch, dur=10.0):
    rng = np.random.default_rng(7)
    V = np.array([[0, 1], [-math.sqrt(3) / 2, -0.5], [math.sqrt(3) / 2, -0.5]])
    p = np.array([0.1, 0.1])
    pts = np.zeros((60000, 2))
    idx = rng.integers(0, 3, 60000)
    for i in range(60000):
        p = (p + V[idx[i]]) / 2
        pts[i] = p

    def draw(sc, u):
        n = int(60000 * min(1.0, (u / 0.85) ** 2))
        sc.dots(pts[:max(n, 1)], 470, 60, (1.0, 0.6, 0.85))

    piece(ch, dur, lambda u: f"jump halfway to a random corner, {int(60000 * min(1.0, (u / 0.85) ** 2)):,} times", draw,
          title="the chaos game → Sierpinski triangle", probe=lambda u: min(1.0, u))


def pythagoras_tree(ch, dur=10.0):
    def draw(sc, u):
        depth = min(11, int(u * 13))
        ctx = sc.c.ctx
        stack = [((CX - 70, 1000), (CX + 70, 1000), 0)]
        while stack:
            (x0, y0), (x1, y1), dd = stack.pop()
            dx, dy = x1 - x0, y1 - y0
            p2 = (x1 + dy, y1 - dx)
            p3 = (x0 + dy, y0 - dx)
            col = hsv(0.08 + dd * 0.045, 0.6)
            ctx.new_path()
            ctx.move_to(x0, y0)
            for q in ((x1, y1), p2, p3):
                ctx.line_to(*q)
            ctx.close_path()
            ctx.set_source_rgba(*col, 0.85)
            ctx.fill()
            if dd < depth:
                a = math.radians(40)
                ex, ey = p3[0] + (p2[0] - p3[0]) * math.cos(a) ** 2 + (p2[1] - p3[1]) * math.cos(a) * math.sin(a), \
                    p3[1] + (p2[1] - p3[1]) * math.cos(a) ** 2 - (p2[0] - p3[0]) * math.cos(a) * math.sin(a)
                stack.append((p3, (ex, ey), dd + 1))
                stack.append(((ex, ey), p2, dd + 1))

    piece(ch, dur, lambda u: f"Pythagoras tree, depth {min(11, int(u * 13))}:  a² + b² = c², again and again", draw,
          title="a tree from right triangles", probe=lambda u: min(11, int(u * 13)) / 11)


CHAPTERS = ["Spirographs", "Lissajous & Harmonographs", "Waves", "Hidden Curves", "Spirals & Sunflowers",
            "Famous Curves", "Fractals", "Circles & Multiplication"]


def build():
    # 1 spirographs — the hook: a hypotrochoid already being drawn on frame 0, drawn fast
    spiro(0, 13, 8, 11, False, (1.0, 0.6, 0.85), dur=9.5, start=0.30, speed=0.62, layers=3)
    for R0, r0, d0, epi, col in ((5, 3, 5, False, (1.0, 0.5, 0.6)), (7, 4, 6, False, (0.5, 0.85, 1.0)),
                                 (9, 5, 7, False, (0.7, 1.0, 0.55)), (5, 3, 4, True, (1.0, 0.75, 0.35)),
                                 (7, 2, 5, True, (0.8, 0.6, 1.0)), (8, 5, 3, True, (0.45, 1.0, 0.85))):
        spiro(0, R0, r0, d0, epi, col)
    # 2 lissajous & harmonographs
    for (a, b), col in zip(((3, 2), (5, 4), (3, 4), (5, 6), (7, 6)),
                           ((1.0, 0.55, 0.6), (0.5, 0.85, 1.0), (0.7, 1.0, 0.6), (1.0, 0.75, 0.35), (0.85, 0.6, 1.0))):
        lissajous(1, a, b, col)
    harmonograph(1, (2.0, 3.0, 3.0, 2.0), (0, 0.5, 1.6, 0.0), 0.02, (1.0, 0.6, 0.8))
    harmonograph(1, (3.0, 2.01, 2.0, 3.01), (0, 1.0, 0.3, 2.0), 0.015, (0.55, 0.85, 1.0))
    harmonograph(1, (2.0, 6.02, 3.0, 2.0), (0, 0.7, 1.2, 0.4), 0.018, (0.75, 1.0, 0.6))
    harmonograph(1, (4.0, 3.0, 4.01, 1.0), (1.0, 0.0, 0.0, 1.5), 0.016, (1.0, 0.8, 0.4))
    # 3 waves
    wave(2, lambda u: f"y = sin({lerp(1, 6, ease(u)):.2f}x) · cos(x)",
         lambda x, u, o: 2 * np.sin(lerp(1, 6, ease(u)) * x) * np.cos(x), [(0, 1.0)], 0.55)
    wave(2, lambda u: "y = 3 sin(x + c) · e^(−x²/20),   12 values of c",
         lambda x, u, o: 3 * np.sin(x + 2 * math.pi * u + o) * np.exp(-x * x / 20),
         [(j * 0.26, 1.0 - 0.06 * j) for j in range(12)], 0.85)
    wave(2, lambda u: f"y = 2 cos({lerp(0, 12, ease(u)):.2f} · sin(x/2))",
         lambda x, u, o: 2 * np.cos(lerp(0, 12, ease(u)) * np.sin(x / 2)), [(0, 1.0)], 0.1)
    wave(2, lambda u: f"y = sin({lerp(1, 8, ease(u)):.2f}x) / x",
         lambda x, u, o: 3.5 * np.sin(lerp(1, 8, ease(u)) * x) / np.where(np.abs(x) < 1e-6, 1e-6, x) / lerp(1, 8, ease(u)),
         [(0, 1.0)], 0.3)
    wave(2, lambda u: f"y = Σ sin((2k−1)x) / (2k−1),   k = 1 … {1 + int(ease(u) * 24)}",
         lambda x, u, o: 3.2 * sum(np.sin((2 * k - 1) * x) / (2 * k - 1) for k in range(1, 2 + int(ease(u) * 24))),
         [(0, 1.0)], 0.6, title="a square wave from sines (Fourier)", probe=lambda u: ease(u))
    wave(2, lambda u: f"y = Σ sin(kx) / k,   k = 1 … {1 + int(ease(u) * 24)}",
         lambda x, u, o: 2.4 * sum(np.sin(k * x) / k for k in range(1, 2 + int(ease(u) * 24))),
         [(0, 1.0)], 0.95, title="a sawtooth from sines (Fourier)", probe=lambda u: ease(u))
    wave(2, lambda u: "y = sin(kx) · cos(ωt),   k = 1 … 6",
         lambda x, u, o: 3 * np.sin((o + 1) * x / 2.5) * np.cos(2 * math.pi * 2 * u * (o + 1) / 3),
         [(j, 1.0 - 0.1 * j) for j in range(6)], 0.0, title="standing waves")
    # 4 hidden curves: F(x, y) = c
    implicit(3, lambda X, Y: np.sin(X * X) + np.sin(Y * Y), -0.4, 1.0, 6.0, (0.45, 1.0, 0.6),
             lambda c: f"sin(x²) + sin(y²) = {c:.2f}")
    implicit(3, lambda X, Y: np.cos(X) * np.cos(Y), -0.9, 0.9, 11.0, (0.55, 0.75, 1.0),
             lambda c: f"cos(x) · cos(y) = {c:.2f}")
    implicit(3, lambda X, Y: np.cos(X) + np.cos(Y) + np.cos(X + Y), -1.4, 2.9, 13.0, (1.0, 0.75, 0.35),
             lambda c: f"cos(x) + cos(y) + cos(x + y) = {c:.2f}", title="a hexagon lattice")
    implicit(3, lambda X, Y: (X * X + Y * Y) ** 2 - 2 * (X * X - Y * Y), -0.95, 1.6, 2.1, (1.0, 0.55, 0.75),
             lambda c: f"(x² + y²)² − 2(x² − y²) = {c:.2f}", title="Cassini ovals")
    implicit(3, lambda X, Y: np.sin(X * Y), -0.95, 0.95, 6.5, (0.75, 0.6, 1.0), lambda c: f"sin(x · y) = {c:.2f}")
    implicit(3, lambda X, Y: np.sin(X + np.sin(Y)) - np.cos(Y + np.cos(X)), -1.5, 1.5, 11.0, (0.45, 0.9, 1.0),
             lambda c: f"sin(x + sin y) − cos(y + cos x) = {c:.2f}")
    implicit(3, lambda X, Y: np.cos(3 * math.pi * X) * np.cos(5 * math.pi * Y) - np.cos(5 * math.pi * X) * np.cos(3 * math.pi * Y),
             -0.6, 0.6, 1.25, (1.0, 0.85, 0.5), lambda c: f"cos 3πx · cos 5πy − cos 5πx · cos 3πy = {c:.2f}",
             title="a Chladni pattern")
    implicit(3, lambda X, Y: X ** 3 - 3 * X * Y * Y, -1.5, 1.5, 2.2, (0.6, 1.0, 0.75), lambda c: f"x³ − 3xy² = {c:.2f}",
             title="the monkey saddle, from above")
    implicit(3, lambda X, Y: np.abs(np.sin(X)) + np.abs(np.sin(Y)), 0.15, 1.85, 9.0, (1.0, 0.6, 0.6),
             lambda c: f"|sin x| + |sin y| = {c:.2f}")
    implicit(3, lambda X, Y: np.sin(X * X - Y * Y), -0.9, 0.9, 5.0, (0.6, 0.75, 1.0), lambda c: f"sin(x² − y²) = {c:.2f}")
    # 5 spirals & sunflowers
    spiral_arms(4, "arch", 6, 0.55)
    spiral_arms(4, "log", 10, 0.85)
    spiral_arms(4, "fermat", 4, 0.3)
    phyllo(4, 135.5, 139.5, False)
    phyllo(4, 137.508, 137.508, True)
    superformula(4, 3.0, 9.0, 1.0, 1.0, 1.0, 0.55)
    superformula(4, 5.0, 12.0, 0.4, 1.7, 1.7, 0.9)
    superformula(4, 2.0, 7.0, 0.3, 0.3, 0.3, 0.3)
    superformula(4, 6.0, 16.0, 1.5, 7.0, 7.0, 0.75)
    rose(4, 2.5, 3.5, (0.5, 1.0, 0.8))
    # 6 famous curves
    pen_curve(5, lambda t: np.sin(t) * (np.exp(np.cos(t)) - 2 * np.cos(4 * t) - np.sin(t / 12) ** 5),
              lambda t: np.cos(t) * (np.exp(np.cos(t)) - 2 * np.cos(4 * t) - np.sin(t / 12) ** 5),
              24 * math.pi, 105, (1.0, 0.5, 0.75), "r = e^(sin θ) − 2cos(4θ) + sin⁵((2θ − π)/24)",
              "the butterfly curve", oy=-0.6)
    pen_curve(5, lambda t: 16 * np.sin(t) ** 3, lambda t: 13 * np.cos(t) - 5 * np.cos(2 * t) - 2 * np.cos(3 * t) - np.cos(4 * t),
              2 * math.pi, 24, (1.0, 0.35, 0.5), "x = 16sin³t,   y = 13cos t − 5cos 2t − 2cos 3t − cos 4t",
              "the heart curve", oy=1.5)
    cardioid_circles(5)
    ladder(5)
    parabola_lines(5)
    epicycloid_sweep(5)
    superellipse(5)
    # 7 fractals
    koch(6)
    dragon(6)
    sierpinski(6)
    pythagoras_tree(6)
    # 8 circles & multiplication (moved to the end)
    times_table(7, 300, 2.0, 7.0, 0.55, dur=10.0)
    times_table(7, 200, 33.0, 35.0, 0.0)
    times_table(7, 360, 50.5, 52.0, 0.75)
    times_table(7, 240, 98.8, 100.2, 0.3)
    maurer(7, 6, 70.0, 72.0, (0.55, 0.75, 1.0))
    maurer(7, 2, 38.5, 39.8, (1.0, 0.55, 0.75))
    maurer(7, 7, 18.5, 19.6, (0.6, 1.0, 0.7))
    maurer(7, 5, 96.5, 97.6, (0.85, 0.6, 1.0))
    rose(7, 1.0, 4.0, (1.0, 0.5, 0.65))
    rose(7, 0.2, 1.4, (0.5, 0.8, 1.0))
    rose(7, 5.0, 7.0, (1.0, 0.75, 0.35))


build()
T_OUTRO = 5.0
STARTS = np.concatenate([[0.0], np.cumsum([p["dur"] for p in PIECES])])
T_ART = float(STARTS[-1])
T_TOTAL = T_ART + T_OUTRO
CH_START = {}
for i, p in enumerate(PIECES):
    CH_START.setdefault(p["chapter"], i)


def piece_at(t):
    i = int(np.searchsorted(STARTS, t, side="right")) - 1
    return min(i, len(PIECES) - 1)


# ======================================================================== scene
class Scene:
    def __init__(self, layout):
        self.L = layout
        self.c = Canvas(layout.w, layout.h, studio.render_scale())
        c = self.c
        self.k = c.pw / W_
        self.grid = []
        for x in range(0, W_ + 1, 60):
            self.grid.append((x, 0, x, H_))
        for y in range(-25, H_ + 1, 60):
            self.grid.append((0, y + 0.0, W_, y + 0.0))

    def implicit(self, G, ext, col):
        """Draw G(x, y) = 0 as a glowing line (distance-normalised: |G| / |∇G|)."""
        c = self.c
        pw, ph = c.pw, c.ph
        S = (W_ / 2) / ext * self.k                              # px per world unit (canvas pixels)
        xs = (np.arange(pw) - CX * self.k) / S
        ys = -(np.arange(ph) - CY * self.k) / S
        X, Y = np.meshgrid(xs, ys)
        Gv = G(X, Y)
        gy, gx = np.gradient(Gv, -1 / S, 1 / S)
        dpx = np.abs(Gv) / (np.hypot(gx, gy) + 1e-9) * S
        sc = self.k
        inten = np.exp(-(dpx / (1.5 * sc)) ** 2) + 0.30 * np.exp(-(dpx / (7.0 * sc)) ** 2)
        inten = np.clip(inten, 0, 1)
        self.blit(inten, col)

    def dots(self, pts, scale, oy, col):
        c = self.c
        pw, ph = c.pw, c.ph
        px = ((CX + scale * pts[:, 0]) * self.k).astype(int)
        py = ((CY + oy - scale * pts[:, 1]) * self.k).astype(int)
        ok = (px >= 0) & (px < pw) & (py >= 0) & (py < ph)
        img = np.zeros((ph, pw))
        np.add.at(img, (py[ok], px[ok]), 1.0)
        img = np.clip(img * 0.8, 0, 1)
        self.blit(img, col)

    def blit(self, inten, col):
        c = self.c
        ph, pw = inten.shape
        a = (inten * 255).astype(np.uint8)
        buf = np.zeros((ph, pw, 4), np.uint8)
        buf[..., 0] = (inten * col[2] * 255).astype(np.uint8)
        buf[..., 1] = (inten * col[1] * 255).astype(np.uint8)
        buf[..., 2] = (inten * col[0] * 255).astype(np.uint8)
        buf[..., 3] = a
        stride = cairo.ImageSurface.format_stride_for_width(cairo.FORMAT_ARGB32, pw)
        if stride != pw * 4:
            pad = np.zeros((ph, stride // 4, 4), np.uint8)
            pad[:, :pw] = buf
            buf = pad
        surf = cairo.ImageSurface.create_for_data(memoryview(np.ascontiguousarray(buf)), cairo.FORMAT_ARGB32, pw, ph,
                                                  stride)
        ctx = c.ctx
        ctx.save()
        ctx.identity_matrix()
        ctx.set_operator(cairo.OPERATOR_ADD)
        ctx.set_source_surface(surf, 0, 0)
        ctx.paint()
        ctx.restore()

    def pill(self, s, y, size, alpha):
        c = self.c
        ctx = c.ctx
        wdt = min(W_ * 0.94, size * 0.50 * len(s) + 70)
        x0, h = W_ / 2 - wdt / 2, size * 1.7
        y0 = y - h * 0.68
        r = h / 2
        ctx.new_path()
        ctx.arc(x0 + r, y0 + r, r, math.pi / 2, 1.5 * math.pi)
        ctx.arc(x0 + wdt - r, y0 + r, r, -math.pi / 2, math.pi / 2)
        ctx.close_path()
        ctx.set_source_rgba(0.02, 0.025, 0.05, 0.72 * alpha)
        ctx.fill_preserve()
        ctx.set_source_rgba(0.8, 0.85, 1.0, 0.18 * alpha)
        ctx.set_line_width(1.5)
        ctx.stroke()
        c.text_centered(s, y, size=size, color=(0.97, 0.97, 1.0), alpha=alpha, bold=False, max_w=W_ * 0.9)

    def draw(self, t):
        c = self.c
        ctx = c.ctx
        ctx.set_source_rgb(*BG)
        ctx.paint()
        g = cairo.RadialGradient(CX, CY, 0, CX, CY, 1100)
        g.add_color_stop_rgba(0, 0.10, 0.10, 0.20, 0.55)
        g.add_color_stop_rgba(1, 0, 0, 0, 0.0)
        ctx.set_source(g)
        ctx.paint()
        c.lines(self.grid, (0.6, 0.65, 0.9), width=1.0, alpha=0.06)
        c.lines([(0, CY, W_, CY), (CX, 0, CX, H_)], (0.7, 0.75, 1.0), width=1.5, alpha=0.10)
        if t >= T_ART:                                         # outro card
            u = (t - T_ART) / T_OUTRO
            a = min(1.0, u / 0.15)
            c.text_centered("Which one was your favourite?", 470, size=78, color=GOLD, alpha=a)
            c.text_centered("tell me the chapter in the comments", 560, size=40, color=(0.85, 0.87, 0.95), alpha=0.9 * a,
                            bold=False)
            c.text_centered("every frame and every note: generated by code", 650, size=30, color=(0.6, 0.65, 0.8),
                            alpha=0.8 * a, bold=False)
            c.watermark(self.L)
            return
        i = piece_at(t)
        p = PIECES[i]
        tl = t - STARTS[i]
        u = tl / p["dur"]
        fade = min(1.0, tl / 0.35 if i else 1.0, (p["dur"] - tl) / 0.35)   # the hook is bright from frame 0
        ctx.push_group()
        p["draw"](self, u)
        self.pill(p["eq"](u), 78, 34, 1.0)
        if p["title"]:
            c.text_centered(p["title"], 140, size=28, color=GOLD, alpha=0.9, bold=False)
        ctx.pop_group_to_source()
        ctx.paint_with_alpha(max(0.0, fade))
        # chapter card (bottom-left), first 3.2 s of each chapter
        ch = p["chapter"]
        t_ch = t - STARTS[CH_START[ch]]
        if t_ch < 3.2:
            a = min(1.0, t_ch / 0.4, (3.2 - t_ch) / 0.5)
            c.text_centered(f"CHAPTER {ch + 1}", 965, size=24, color=GOLD, alpha=a, cx=270)
            c.text_centered(CHAPTERS[ch], 1010, size=40, color=(0.97, 0.97, 1.0), alpha=a, cx=270)
        if t < 4.0:                                            # the video's title over the hook
            a = min(1.0, (4.0 - t) / 0.6)
            c.text_centered("EQUATIONS THAT LOOK LIKE ART", 1000, size=64, color=(0.97, 0.97, 1.0), alpha=a)
        c.watermark(self.L)


def render_part(layout, k, nparts, label):
    nf = int(round(T_TOTAL * FPS))
    f0, f1 = nf * k // nparts, nf * (k + 1) // nparts
    sc = Scene(layout)
    out = studio.OUT_DIR / f"{SCENE}_{label}_seg{k}.mp4"
    writer = VideoWriter(out, sc.c, FPS)
    for f in range(f0, f1):
        sc.draw(f / FPS)
        writer.write_frame()
    writer.close()
    print(f"[{SCENE}] seg {k}: frames {f0}-{f1} -> {out}")


# ======================================================================== soundtrack (original, calm cinematic: piano + strings)
BPM = 72.0
BEAT = 60.0 / BPM
BAR = 4 * BEAT
SR = audio.SR
# key (tonic, minor) + progression per chapter: the key changes at every chapter
CH_KEY = [50, 52, 53, 55, 52, 57, 55, 50]                     # Dm Em Fm Gm Em Am Gm Dm
PROGS = {"A": [(0, "m"), (8, "M"), (3, "M"), (10, "M")],      # i VI III VII
         "B": [(8, "M"), (10, "M"), (0, "m"), (0, "m")],      # VI VII i i
         "C": [(0, "m"), (10, "M"), (8, "M"), (10, "M")],     # i VII VI VII
         "D": [(0, "m"), (5, "m"), (8, "M"), (7, "M")]}       # i iv VI V
CH_PROG = ["A", "B", "A", "C", "D", "B", "A", "C"]


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def bar_info(b):
    tb = b * BAR
    i = piece_at(min(tb, T_ART - 1e-3))
    ch = PIECES[i]["chapter"]
    b0 = int(round(STARTS[CH_START[ch]] / BAR))
    k = max(0, b - b0)                                         # bar within the chapter
    off, q = PROGS[CH_PROG[ch]][k % 4]
    root = CH_KEY[ch] + off
    triad = (0, 3, 7) if q == "m" else (0, 4, 7)
    colour = (0, 3, 7, 10, 14) if q == "m" else (0, 4, 7, 11, 14)   # m9 / maj9: soft, open colour
    return tb, ch, k, root, triad, colour, i


def piano_events():
    """Soft piano: a broken-chord accompaniment (8ths, low) + a slow melody whose notes come from each curve."""
    ev = []
    nbar = int(math.ceil(T_ART / BAR))
    last_m = None
    arp = [0, 2, 4, 2, 1, 3, 4, 3]                             # index into the colour chord
    for b in range(nbar):
        tb, ch, k, root, triad, colour, pi_ = bar_info(b)
        base = root - 12 if root >= 55 else root               # keep the left hand around D3–G3
        ev.append({"t": round(tb, 4), "note": base - 12, "gain": 0.20, "x": W_ / 2})
        for s_ in range(8):
            t = tb + s_ * BEAT / 2
            ev.append({"t": round(t + 0.004, 4), "note": base + colour[arp[s_]], "gain": 0.075 if s_ % 2 else 0.095,
                       "x": W_ * (0.42 + 0.02 * s_)})
        if k == 0:                                             # a gentle high chord on every new chapter
            for j, iv in enumerate(colour[:4]):
                ev.append({"t": round(tb + 0.03 * j, 4), "note": root + 24 + iv, "gain": 0.07, "x": W_ / 2})
        rhythm = [[2, 2], [3, 1], [1, 1, 2], [4], [1.5, 0.5, 2]][pi_ % 5]
        t_rel = 0.0
        for d in rhythm:
            t = tb + t_rel * BEAT
            t_rel += d
            if t >= T_ART:
                break
            ii = piece_at(t)
            pc = PIECES[ii]
            u = (t - STARTS[ii]) / pc["dur"]
            v = min(0.999, max(0.0, float(pc["probe"](u))))
            pool = [base + 12 + iv for iv in colour] + [base + 24 + iv for iv in triad]
            m = pool[int(v * len(pool))]
            if m == last_m:
                continue
            last_m = m
            ev.append({"t": round(t + 0.008, 4), "note": m, "gain": 0.20, "x": W_ / 2})
    tf = T_ART + 0.05
    for j, m in enumerate((38, 50, 57, 62, 65, 69, 74)):        # final D minor (add9 colour on top)
        ev.append({"t": round(tf + 0.07 * j, 4), "note": m, "gain": 0.16, "x": W_ / 2})
    return sorted(ev, key=lambda e: e["t"])


def strings_bed():
    """Warm string pad (slow swells, soft partials, slight detune) + a deep soft bass + chapter swells. Stereo."""
    n = int(round(T_TOTAL * SR)) + 3 * SR
    L = np.zeros(n)
    R = np.zeros(n)
    rng = np.random.default_rng(11)

    def add(t0, sig, pan=0.0):
        i0 = int(t0 * SR)
        if i0 >= n:
            return
        sig = sig[: n - i0]
        L[i0:i0 + len(sig)] += sig * (1 - pan) ** 0.5
        R[i0:i0 + len(sig)] += sig * (1 + pan) ** 0.5

    def soft(f, tv):
        ph = 2 * np.pi * f * tv
        return np.sin(ph) + 0.30 * np.sin(2 * ph + 0.4) + 0.10 * np.sin(3 * ph + 1.1)

    nbar = int(math.ceil(T_ART / BAR))
    tv = np.arange(int((BAR + 1.6) * SR)) / SR
    env = np.clip(tv / 1.0, 0, 1) ** 1.5 * np.clip((BAR + 1.6 - tv) / 1.6, 0, 1)
    for b in range(nbar + 1):
        tb, ch, k, root, triad, colour, _ = bar_info(min(b, nbar - 1))
        tb = b * BAR
        if tb >= T_TOTAL - 1.0:
            break
        for j, iv in enumerate(colour[:4]):
            f = hz(root + iv)
            sig = 0.5 * (soft(f * 1.0015, tv) + soft(f * 0.9985, tv))
            add(tb, 0.030 * env * sig, pan=(-0.5, 0.5, -0.25, 0.25)[j])
        bass = np.sin(2 * np.pi * hz(root - 12) * tv) * env
        add(tb, 0.055 * bass)
        if k == 0 and b > 0:                                   # soft swell INTO each chapter (key change)
            tn = np.arange(int(1.2 * BAR * SR)) / SR
            nz = rng.standard_normal(len(tn))
            nz = np.convolve(nz, np.ones(24) / 24, mode="same")   # dark, airy
            add(tb - 1.2 * BAR + 0.2, 0.05 * nz * (tn / tn[-1]) ** 3)
    # spacious hall (block FFT convolution, overlap-add)
    Lir = int(2.4 * SR)
    ir = rng.standard_normal(Lir) * np.exp(-np.arange(Lir) / SR / 0.75)
    ir[:int(0.02 * SR)] = 0
    ir = np.convolve(ir, np.ones(6) / 6, mode="same")
    ir /= np.sqrt((ir ** 2).sum())
    blk = 1 << 20
    nfft = 1 << (blk + Lir - 1).bit_length()
    IR = np.fft.rfft(ir, nfft)
    out = []
    for X in (L, R):
        wet = np.zeros(n + Lir)
        for s0 in range(0, n, blk):
            seg = X[s0:s0 + blk]
            y = np.fft.irfft(np.fft.rfft(seg, nfft) * IR, nfft)[: len(seg) + Lir - 1]
            wet[s0:s0 + len(y)] += y
        out.append(X + 0.30 * wet[:n])
    return np.stack(out, axis=1)[: int(round(T_TOTAL * SR))]


def soundtrack():
    piano = audio.mix_events(piano_events(), T_TOTAL, width_px=W_, voice="piano")
    st = strings_bed()
    m = min(len(piano), len(st))
    return (piano[:m] + st[:m]).astype(np.float32)


def assemble(layout, nparts, label):
    import soundfile as sf
    segs = [studio.OUT_DIR / f"{SCENE}_{label}_seg{k}.mp4" for k in range(nparts)]
    lst = studio.OUT_DIR / f"{SCENE}_{label}_segs.txt"
    lst.write_text("".join(f"file '{s.name}'\n" for s in segs))
    silent = studio.OUT_DIR / f"{SCENE}_{label}_{layout.tag}_silent.mp4"
    if not silent.exists() or kit.has("--reconcat"):
        subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i",
                        str(lst), "-c", "copy", str(silent)], check=True)
    name = f"{SCENE}_{label}_{layout.tag}"
    wav = studio.OUT_DIR / f"{name}_audio.wav"
    buf = audio.master(soundtrack().astype(np.float64), peak_db=-6.0, reverb=0.8)
    sf.write(str(wav), buf, SR)
    studio.mux_audio(silent, wav, studio.OUT_DIR / f"{name}.mp4")
    print(f"[{SCENE}] -> {name}.mp4")


def chapters_txt():
    out = []
    for ch in range(len(CHAPTERS)):
        s = int(STARTS[CH_START[ch]])
        out.append(f"{s // 60}:{s % 60:02d} {CHAPTERS[ch]}")
    return "\n".join(out)


def main():
    label = arg("--label", "v1")
    studio.OUT_DIR.mkdir(exist_ok=True)
    layout = get_layout("horizontal")
    if kit.has("--info"):
        print(f"{len(PIECES)} pieces, art {T_ART:.1f}s, total {T_TOTAL:.1f}s ({T_TOTAL / 60:.2f} min)")
        print(chapters_txt())
        return
    if kit.has("--still"):
        t = float(arg("--t", "5"))
        sc = Scene(layout)
        sc.draw(t)
        png = studio.OUT_DIR / f"{SCENE}_{label}_t{t:.1f}.png"
        studio.save_still(sc.c, png)
        print(png)
        return
    nparts = int(arg("--parts", "4"))
    if kit.has("--assemble"):
        assemble(layout, nparts, label)
        return
    render_part(layout, int(arg("--part", "0")), nparts, label)


if __name__ == "__main__":
    main()
