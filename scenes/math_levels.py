"""MATH LEVELS — math from "1 + 1" to LEVEL MAX in ~15 s: a level-up ladder with a difficulty meter.

Idea after youtube.com/shorts/yFxdJ_n2Ja8 (a fast "math is easy?" montage). Taken: only the generic
idea of an easy-to-impossible ladder (topics and formulas belong to nobody). Ours: the LEVEL / meter
structure and wording, every visual (coded here), the sound, and the payoff (the channel's own
never-closing golden curve e^(iθ) + e^(iφθ), from phi_spin).

Built to the 2026-10-10 report formula: frame 0 states the game (LEVEL 1, "1 + 1 = 2", empty meter),
something new every ~0.6 s (getting faster), a visible finish line (the meter filling to MAX), a big
satisfying result, ~15 s, loop.

Audio (original synthesis only): a pluck per level climbing the scale (faster with the levels),
a chord + shimmer on LEVEL MAX, a quiet periodic pad.
"""
import math
import sys
from pathlib import Path

import cairo
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib import audio, kit, studio  # noqa: E402
from lib.kit import DT, FPS, arg, smooth  # noqa: E402
from lib.layouts import get_layout  # noqa: E402
from lib.studio import Canvas, VideoWriter  # noqa: E402

SCENE = "math_levels"
PHI = (1 + 5 ** 0.5) / 2
GOLD = (1.0, 0.82, 0.40)
GREY = (0.75, 0.78, 0.88)
WHITE = (1, 1, 1)
T_MAX = 3.6                                     # the final level (the payoff)


def level_col(u):
    """Green → yellow → red with difficulty u in [0, 1]."""
    if u < 0.5:
        k = u / 0.5
        return (0.35 + 0.65 * k, 0.95, 0.45 - 0.2 * k)
    k = (u - 0.5) / 0.5
    return (1.0, 0.95 - 0.6 * k, 0.25 - 0.05 * k)


# ---- level visuals: draw(c, cx, cy, S, p, col), p = progress 0..1 inside the level ------------------
def v_count(c, cx, cy, S, p, col):
    d = S * 0.5 * (1 - smooth(p / 0.6))
    for sx in (-1, 1):
        c.circle(cx + sx * (d + S * 0.12 * (1 - smooth(p / 0.6))), cy, S * 0.12, col, alpha=0.95)
    if p > 0.6:
        c.circle(cx, cy, S * 0.17 * smooth((p - 0.6) / 0.2), col, alpha=0.95)


def v_frac(c, cx, cy, S, p, col):
    ctx = c.ctx
    c.ring(cx, cy, S * 0.55, WHITE, width=3, alpha=0.6)
    for a0, a1, k in ((0, math.pi, 0.0), (math.pi, 1.5 * math.pi, 0.45)):
        q = smooth((p - k) / 0.45)
        if q <= 0:
            continue
        ctx.move_to(cx, cy)
        ctx.arc(cx, cy, S * 0.55, a0 - math.pi / 2, a0 - math.pi / 2 + (a1 - a0) * q)
        ctx.close_path()
        ctx.set_source_rgba(*col, 0.85)
        ctx.fill()


def v_neg(c, cx, cy, S, p, col):
    c.lines([(cx - S, cy, cx + S, cy)], WHITE, width=3, alpha=0.7)
    for i in range(-5, 6):
        x = cx + i * S / 5.5
        c.lines([(x, cy - 10, x, cy + 10)], WHITE, width=2, alpha=0.6)
    x0 = cx - 3 * S / 5.5
    x1 = x0 + 5 * S / 5.5 * smooth(p)
    c.lines([(x0, cy - S * 0.15, x1, cy - S * 0.15)], col, width=8)
    c.circle(x1, cy - S * 0.15, 12, col)


def _plot(c, cx, cy, S, f, xa, xb, ya, yb, p, col, width=7):
    xs = np.linspace(xa, xa + (xb - xa) * max(p, 0.01), 120)
    pts = [(cx - S + 2 * S * (x - xa) / (xb - xa), cy + S * 0.6 - 1.2 * S * (f(x) - ya) / (yb - ya)) for x in xs]
    c.polylines([pts], col, width=width * 3, alpha=0.15)
    c.polylines([pts], col, width=width, alpha=0.95)
    return pts


def v_alg(c, cx, cy, S, p, col):
    yz = cy + S * 0.6 - 1.2 * S * (0 + 0.5) / 6.5
    c.lines([(cx - S, yz, cx + S, yz)], WHITE, width=2, alpha=0.5)
    _plot(c, cx, cy, S, lambda x: x * x - 5 * x + 6, 0, 5, -0.5, 6, p, col)
    for r in (2, 3):
        if p > r / 5:
            c.circle(cx - S + 2 * S * r / 5, yz, 13, WHITE)


def v_pyth(c, cx, cy, S, p, col):
    ctx = c.ctx
    a, b = S * 0.45, S * 0.6
    A = (cx - a * 0.6, cy + b * 0.35)
    B = (A[0] + a, A[1])
    C = (A[0], A[1] - b)
    q = smooth(p / 0.7)
    for (P1, P2) in ((A, B), (A, C), (C, B)):
        dx, dy = P2[0] - P1[0], P2[1] - P1[1]
        nx, ny = dy, -dx
        if (P1, P2) == (A, C):
            nx, ny = -nx, -ny
        if (P1, P2) == (C, B):
            nx, ny = -nx, -ny
        ctx.move_to(*P1)
        ctx.line_to(*P2)
        ctx.line_to(P2[0] + nx * q, P2[1] + ny * q)
        ctx.line_to(P1[0] + nx * q, P1[1] + ny * q)
        ctx.close_path()
        ctx.set_source_rgba(*col, 0.35)
        ctx.fill_preserve()
        ctx.set_source_rgba(*col, 0.95)
        ctx.set_line_width(3)
        ctx.stroke()
    c.polylines([[A, B, C, A]], WHITE, width=5)


def v_trig(c, cx, cy, S, p, col):
    r = S * 0.35
    ox = cx - S * 0.55
    c.ring(ox, cy, r, WHITE, width=3, alpha=0.6)
    th = 2 * math.pi * 1.2 * p
    px, py = ox + r * math.cos(th), cy - r * math.sin(th)
    c.lines([(ox, cy, px, py)], col, width=4)
    pts = [(ox + r * 1.3 + (S * 0.9) * (k / 80) * (th / (2.4 * math.pi)),
            cy - r * math.sin(th * k / 80)) for k in range(81)]
    c.polylines([pts], col, width=6)
    c.circle(px, py, 10, WHITE)


def v_exp(c, cx, cy, S, p, col):
    n = int(1 + 6 * smooth(p))
    bw = 2 * S / 7
    for i in range(n):
        hgt = S * 1.1 * (2 ** i) / 64
        x = cx - S + i * bw
        c.ctx.rectangle(x + 4, cy + S * 0.55 - hgt, bw - 8, hgt)
        c.ctx.set_source_rgba(*col, 0.9)
        c.ctx.fill()


def v_euler(c, cx, cy, S, p, col):
    r = S * 0.5
    c.ring(cx, cy, r, WHITE, width=3, alpha=0.6)
    c.lines([(cx - r * 1.3, cy, cx + r * 1.3, cy), (cx, cy - r * 1.3, cx, cy + r * 1.3)], WHITE, width=2, alpha=0.4)
    th = math.pi * smooth(p)
    c.ctx.arc_negative(cx, cy, r * 0.25, 0, -th)
    c.ctx.set_source_rgba(*col, 0.9)
    c.ctx.set_line_width(4)
    c.ctx.stroke()
    px, py = cx + r * math.cos(th), cy - r * math.sin(th)
    c.lines([(cx, cy, px, py)], col, width=7)
    c.circle(px, py, 12, WHITE)


def v_integral(c, cx, cy, S, p, col):
    ctx = c.ctx
    q = smooth(p)
    xs = np.linspace(0, 2 * q, 60)
    base = cy + S * 0.6
    ctx.move_to(cx - S, base)
    for x in xs:
        ctx.line_to(cx - S + S * x, base - 1.2 * S * x * x / 4)
    ctx.line_to(cx - S + S * 2 * q, base)
    ctx.close_path()
    ctx.set_source_rgba(*col, 0.45)
    ctx.fill()
    _plot(c, cx, cy, S, lambda x: x * x, 0, 2, 0, 4, 1.0, col, width=5)


def v_series(c, cx, cy, S, p, col):
    ctx = c.ctx
    x0, wbar, hb = cx - S, 2 * S, S * 0.35
    ctx.rectangle(x0, cy - hb / 2, wbar, hb)
    ctx.set_source_rgba(*WHITE, 0.6)
    ctx.set_line_width(3)
    ctx.stroke()
    n = int(1 + 8 * smooth(p))
    x = x0
    for k in range(n):
        seg = wbar / 2 ** (k + 1)
        ctx.rectangle(x + 2, cy - hb / 2 + 2, seg - 4, hb - 4)
        ctx.set_source_rgba(*level_col(k / 8), 0.9)
        ctx.fill()
        x += seg


def v_matrix(c, cx, cy, S, p, col):
    sh = smooth(p)
    segs = []
    for i in range(-3, 4):
        u = i * S / 3.2
        segs.append((cx + u - sh * S * 0.9, cy - S * 0.9, cx + u + sh * S * 0.9, cy + S * 0.9))
        segs.append((cx - S + sh * u * 0, cy + u, cx + S, cy + u))
    c.lines(segs, col, width=3, alpha=0.85)
    c.lines([(cx, cy, cx + S * 0.6 + sh * 0, cy), (cx, cy, cx - sh * S * 0.55, cy - S * 0.55)], WHITE, width=6)


def v_prob(c, cx, cy, S, p, col):
    ctx = c.ctx
    q = smooth(p)
    base = cy + S * 0.55
    xs = np.linspace(-3, 3, 80)
    ctx.move_to(cx - S, base)
    for x in xs:
        ctx.line_to(cx + S * x / 3, base - S * 1.1 * math.exp(-x * x / 2) * q)
    ctx.line_to(cx + S, base)
    ctx.close_path()
    ctx.set_source_rgba(*col, 0.45)
    ctx.fill_preserve()
    ctx.set_source_rgba(*col, 0.95)
    ctx.set_line_width(5)
    ctx.stroke()


def v_fractal(c, cx, cy, S, p, col):
    ctx = c.ctx
    depth = int(smooth(p) * 5)
    tris = [((cx, cy - S * 0.75), (cx - S * 0.87, cy + S * 0.6), (cx + S * 0.87, cy + S * 0.6))]
    for _ in range(depth):
        nt = []
        for a, b, d in tris:
            ab = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
            bd = ((b[0] + d[0]) / 2, (b[1] + d[1]) / 2)
            ad = ((a[0] + d[0]) / 2, (a[1] + d[1]) / 2)
            nt += [(a, ab, ad), (ab, b, bd), (ad, bd, d)]
        tris = nt
    for a, b, d in tris:
        ctx.move_to(*a)
        ctx.line_to(*b)
        ctx.line_to(*d)
        ctx.close_path()
    ctx.set_source_rgba(*col, 0.9)
    ctx.fill()


def v_fourier(c, cx, cy, S, p, col):
    n = 1 + int(smooth(p) * 9)
    _plot(c, cx, cy, S * 0.95,
          lambda x: sum(math.sin((2 * k + 1) * x) / (2 * k + 1) for k in range(n)),
          -math.pi, math.pi, -1.3, 1.3, 1.0, col, width=5)


def _primes(n):
    s = [True] * (n + 1)
    s[0] = s[1] = False
    for i in range(2, int(n ** 0.5) + 1):
        if s[i]:
            for j in range(i * i, n + 1, i):
                s[j] = False
    return s


PRIME = _primes(100)


def v_primes(c, cx, cy, S, p, col):
    shown = int(100 * smooth(p))
    g = 2 * S / 10
    for k in range(1, 101):
        i, j = (k - 1) % 10, (k - 1) // 10
        x, y = cx - S + g * (i + 0.5), cy - S * 0.9 + g * 0.9 * (j + 0.5)
        on = PRIME[k] and k <= shown
        c.circle(x, y, g * (0.30 if on else 0.12), col if on else GREY, alpha=0.95 if on else 0.35)


LORENZ = None


def v_chaos(c, cx, cy, S, p, col):
    global LORENZ
    if LORENZ is None:
        x, y, z, pts = 0.1, 0.0, 0.0, []
        for _ in range(6000):
            dx, dy, dz = 10 * (y - x), x * (28 - z) - y, x * y - 8 / 3 * z
            x, y, z = x + dx * 0.006, y + dy * 0.006, z + dz * 0.006
            pts.append((x, z))
        LORENZ = pts
    n = max(2, int(len(LORENZ) * smooth(p)))
    pts = [(cx + S * x / 22, cy + S * 0.65 - S * 1.35 * z / 50) for x, z in LORENZ[:n]]
    c.polylines([pts], col, width=3, alpha=0.9)


# (topic, formula, visual)
LEVELS = [
    ("counting", "1 + 1 = 2", v_count),
    ("fractions", "½ + ¼ = ¾", v_frac),
    ("negative numbers", "−3 + 5 = 2", v_neg),
    ("algebra", "x² − 5x + 6 = 0", v_alg),
    ("geometry", "a² + b² = c²", v_pyth),
    ("trigonometry", "y = sin θ", v_trig),
    ("exponents", "2⁰, 2¹, 2², … 2⁶", v_exp),
    ("complex numbers", "e^(iπ) + 1 = 0", v_euler),
    ("calculus", "∫ x² dx = x³/3", v_integral),
    ("infinite series", "1 + ½ + ¼ + … = 2", v_series),
    ("linear algebra", "[1 1; 0 1] · v", v_matrix),
    ("probability", "e^(−x²/2) / √(2π)", v_prob),
    ("fractals", "dimension = log 3 / log 2", v_fractal),
    ("Fourier series", "Σ sin((2k+1)x) / (2k+1)", v_fourier),
    ("prime numbers", "2, 3, 5, 7, 11, 13 …", v_primes),
    ("chaos", "ẋ = σ(y − x), ż = xy − βz", v_chaos),
]

# ---------------------------------------------------------------------------------------------------- level sets
# --set fib : "16 levels of Fibonacci"     --set p2 : "16 levels of math, part 2"     (default: the shipped set)
FIBS = [1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233]


def _fib_tiles(n):
    sq, box = [(0, 0, 1)], [0, 0, 1, 1]
    for k in range(1, n):
        s, d = FIBS[k], (k - 1) % 4
        if d == 0:
            sq.append((box[2], box[1], s)); box[2] += s
        elif d == 1:
            sq.append((box[0], box[3], s)); box[3] += s
        elif d == 2:
            sq.append((box[0] - s, box[1], s)); box[0] -= s
        else:
            sq.append((box[0], box[1] - s, s)); box[1] -= s
    return sq, box


def _tile_draw(c, cx, cy, S, n, col, arcs=False, arc_p=1.0):
    sq, box = _fib_tiles(n)
    bw, bh = box[2] - box[0], box[3] - box[1]
    k = 1.8 * S / max(bw, bh * 1.2)
    ox, oy = cx - k * (box[0] + bw / 2), cy + k * (box[1] + bh / 2)
    ctx = c.ctx
    for i, (x, y, s) in enumerate(sq):
        ctx.rectangle(ox + k * x, oy - k * (y + s), k * s, k * s)
        ctx.set_source_rgba(*level_col(i / 12), 0.35)
        ctx.fill_preserve()
        ctx.set_source_rgba(1, 1, 1, 0.8)
        ctx.set_line_width(2)
        ctx.stroke()
        if k * s > 26 and not arcs:
            c.text_centered(str(s), oy - k * (y + s / 2) + k * s * 0.12, size=min(k * s * 0.4, S * 0.25), color=WHITE,
                            cx=ox + k * (x + s / 2))
    if arcs:
        pts, P = [], (0.0, 1.0)
        centers = []
        for i, (x, y, s) in enumerate(sq):
            d = (i - 1) % 4 if i > 0 else 3
            corner = {0: (x, y + s), 1: (x, y), 2: (x + s, y), 3: (x + s, y + s)}[d] if i > 0 else (1, 1)
            centers.append((corner, s, d))
        for i, ((ccx, ccy), s, d) in enumerate(centers):
            a0 = {3: math.pi, 0: -math.pi / 2, 1: 0.0, 2: math.pi / 2}[d] if i > 0 else math.pi
            for j in range(13):
                a = a0 + (math.pi / 2) * j / 12 * (1 if i > 0 else 1)
                pts.append((ox + k * (ccx + s * math.cos(a)), oy - k * (ccy + s * math.sin(a))))
        m = max(2, int(len(pts) * arc_p))
        c.polylines([pts[:m]], GOLD, width=12, alpha=0.2)
        c.polylines([pts[:m]], GOLD, width=5)


def v_fseq(c, cx, cy, S, p, col):
    n = 1 + int(6 * smooth(p))
    bw = 2 * S / 7
    for i in range(n):
        hgt = S * 1.2 * FIBS[i] / 13
        x = cx - S + i * bw
        c.ctx.rectangle(x + 4, cy + S * 0.6 - hgt, bw - 8, hgt)
        c.ctx.set_source_rgba(*col, 0.9)
        c.ctx.fill()
        c.text_centered(str(FIBS[i]), cy + S * 0.6 - hgt - 12, size=S * 0.16, color=WHITE, cx=x + bw / 2)


def v_frule(c, cx, cy, S, p, col):
    u = smooth(p / 0.7)
    base = cy + S * 0.55
    hs = [S * 1.1 * 3 / 8, S * 1.1 * 5 / 8]
    xs = [cx - S * 0.7 + u * S * 0.45, cx - S * 0.25 + u * S * 0.0]
    for hgt, x in zip(hs, xs):
        c.ctx.rectangle(x, base - hgt, S * 0.3, hgt)
        c.ctx.set_source_rgba(*col, 0.85)
        c.ctx.fill()
    c.ctx.rectangle(cx + S * 0.45, base - S * 1.1, S * 0.3, S * 1.1)
    c.ctx.set_source_rgba(*GOLD, 0.25 + 0.65 * smooth((p - 0.6) / 0.3))
    c.ctx.fill()


def v_fsquares(c, cx, cy, S, p, col):
    _tile_draw(c, cx, cy, S * 0.95, 1 + int(5 * smooth(p)), col)


def v_fspiral(c, cx, cy, S, p, col):
    _tile_draw(c, cx, cy, S * 0.95, 8, col, arcs=True, arc_p=smooth(p))


def v_fratio(c, cx, cy, S, p, col):
    yl = lambda r: cy + S * 0.6 - 1.2 * S * (r - 0.9) / 1.2       # noqa: E731
    PHIY = yl(PHI)
    c.lines([(cx - S, PHIY, cx + S, PHIY)], GOLD, width=2, alpha=0.6)
    n = 1 + int(11 * smooth(p))
    pts = []
    for i in range(n):
        r = FIBS[i + 1] / FIBS[i]
        pts.append((cx - S + 2 * S * i / 11, yl(r)))
    c.polylines([pts], col, width=5)
    for x, y in pts:
        c.circle(x, y, 8, WHITE)


def v_fphi(c, cx, cy, S, p, col):
    u = smooth(p)
    x0, x1 = cx - S, cx + S
    xs = x0 + (x1 - x0) * (0.5 + (1 / PHI - 0.5) * u)
    c.lines([(x0, cy, xs, cy)], col, width=14)
    c.lines([(xs, cy, x1, cy)], GOLD, width=14)
    c.text_centered("a", cy - 30, size=S * 0.18, color=col, cx=(x0 + xs) / 2)
    c.text_centered("b", cy - 30, size=S * 0.18, color=GOLD, cx=(xs + x1) / 2)


def v_fphisq(c, cx, cy, S, p, col):
    u = smooth(p)
    k = S * 0.68
    c.ctx.rectangle(cx - S, cy - S * 0.35, k * PHI * PHI * u, S * 0.22)
    c.ctx.set_source_rgba(*col, 0.9)
    c.ctx.fill()
    c.ctx.rectangle(cx - S, cy + S * 0.1, k * PHI * u, S * 0.22)
    c.ctx.set_source_rgba(*GOLD, 0.9)
    c.ctx.fill()
    c.ctx.rectangle(cx - S + k * PHI * u, cy + S * 0.1, k * 1 * u, S * 0.22)
    c.ctx.set_source_rgba(1, 1, 1, 0.85)
    c.ctx.fill()


def _seeds(c, cx, cy, S, n, col, mark=0):
    for i in range(1, n):
        r = S * 0.9 * math.sqrt(i / 260)
        th = i * math.radians(137.508)
        cc = col if not mark or i % mark else GOLD
        c.circle(cx + r * math.cos(th), cy + r * math.sin(th), 5 + 4 * i / 260, cc, alpha=0.9)


def v_fsunflower(c, cx, cy, S, p, col):
    _seeds(c, cx, cy, S, 2 + int(258 * smooth(p)), col)


def v_fparastichy(c, cx, cy, S, p, col):
    _seeds(c, cx, cy, S, 260, col, mark=13 if p < 0.5 else 8)


def v_fpenta(c, cx, cy, S, p, col):
    pts = [(cx + S * 0.8 * math.cos(-math.pi / 2 + 2 * math.pi * i / 5), cy + S * 0.8 * math.sin(-math.pi / 2 + 2 * math.pi * i / 5))
           for i in range(5)]
    star = [pts[(2 * i) % 5] for i in range(6)]
    n = max(2, int(6 * smooth(p) + 0.999))
    c.polylines([pts + [pts[0]]], WHITE, width=3, alpha=0.5)
    c.polylines([star[:n]], col, width=7)


def v_fpascal(c, cx, cy, S, p, col):
    rows = 9
    g = 2 * S / 10
    shown = int(rows * smooth(p / 0.6)) + 1
    diag = int(9 * smooth((p - 0.55) / 0.45))
    for r in range(min(rows, shown)):
        for k in range(r + 1):
            x = cx + (k - r / 2) * g
            y = cy - S * 0.75 + r * g * 0.85
            d = r + k                                        # shallow diagonal index: r + k = const
            on = d < diag and (r + k) % 1 == 0 and r >= k
            cc = level_col((r + k) / 12) if (d < diag) else GREY
            c.circle(x, y, g * 0.28, cc, alpha=0.95 if d < diag else 0.4)


def v_flucas(c, cx, cy, S, p, col):
    L = [2, 1, 3, 4, 7, 11, 18]
    n = 1 + int(6 * smooth(p))
    bw = 2 * S / 7
    for i in range(n):
        for j, (seq, cc) in enumerate(((FIBS[1:], col), (L, GOLD))):
            hgt = S * 1.2 * seq[i] / 18
            x = cx - S + i * bw + j * bw * 0.45
            c.ctx.rectangle(x + 3, cy + S * 0.6 - hgt, bw * 0.42, hgt)
            c.ctx.set_source_rgba(*cc, 0.9)
            c.ctx.fill()


def v_fzeck(c, cx, cy, S, p, col):
    parts = [89, 8, 3]
    x = cx - S
    u = smooth(p)
    for i, v in enumerate(parts):
        wv = 2 * S * v / 100 * min(1.0, max(0.0, u * 3 - i))
        c.ctx.rectangle(x, cy - S * 0.15, wv, S * 0.3)
        c.ctx.set_source_rgba(*level_col(i / 3 + 0.2), 0.9)
        c.ctx.fill()
        x += 2 * S * v / 100
    c.ctx.rectangle(cx - S, cy - S * 0.15, 2 * S, S * 0.3)
    c.ctx.set_source_rgba(1, 1, 1, 0.7)
    c.ctx.set_line_width(2)
    c.ctx.stroke()


def v_fcontfrac(c, cx, cy, S, p, col):
    n = 1 + int(7 * smooth(p))
    w0, h0 = 2 * S, 2 * S / PHI
    x, y, wv, hv = cx - S, cy - h0 / 2, w0, h0
    for i in range(n):
        c.ctx.rectangle(x, y, wv, hv)
        c.ctx.set_source_rgba(*level_col(i / 8), 0.85)
        c.ctx.set_line_width(4)
        c.ctx.stroke()
        if i % 2 == 0:
            x, wv = x + hv, wv - hv
        else:
            y, hv = y + wv, hv - wv


def v_fmod10(c, cx, cy, S, p, col):
    R = S * 0.8
    P = [(cx + R * math.sin(2 * math.pi * d / 10), cy - R * math.cos(2 * math.pi * d / 10)) for d in range(10)]
    for d in range(10):
        c.text_centered(str(d), P[d][1] + 10, size=S * 0.14, color=GREY, cx=cx + (R + 34) * math.sin(2 * math.pi * d / 10),
                        alpha=0.8)
    seq, a, b = [], 0, 1
    for _ in range(61):
        seq.append(a % 10)
        a, b = b, a + b
    n = max(2, int(60 * smooth(p)))
    pts = [P[seq[i]] for i in range(n)]
    c.polylines([pts], col, width=3, alpha=0.9)


def v_fbinet(c, cx, cy, S, p, col):
    f = lambda x: (PHI ** x) / 5 ** 0.5                            # noqa: E731
    _plot(c, cx, cy, S, f, 0, 10, 0, 60, p, col, width=5)
    for i in range(int(11 * smooth(p))):
        x = cx - S + 2 * S * i / 10
        c.circle(x, cy + S * 0.6 - 1.2 * S * FIBS[i] / 60 if i else cy + S * 0.6, 8, WHITE)


FIB_LEVELS = [
    ("the sequence", "1, 1, 2, 3, 5, 8, 13", v_fseq),
    ("the rule", "3 + 5 = 8", v_frule),
    ("Fibonacci squares", "1, 1, 2, 3, 5, 8", v_fsquares),
    ("the golden spiral", "a quarter circle in each square", v_fspiral),
    ("the ratio", "13 ÷ 8 = 1.625 → 1.618…", v_fratio),
    ("the golden ratio", "φ = (1 + √5) / 2", v_fphi),
    ("φ squared", "φ² = φ + 1", v_fphisq),
    ("the golden angle", "360° ÷ φ² = 137.5°", v_fsunflower),
    ("sunflower spirals", "13 one way, 8 the other", v_fparastichy),
    ("the pentagram", "diagonal ÷ side = φ", v_fpenta),
    ("Pascal's triangle", "its diagonals add to Fibonacci", v_fpascal),
    ("Lucas numbers", "2, 1, 3, 4, 7, 11, 18", v_flucas),
    ("Zeckendorf", "100 = 89 + 8 + 3", v_fzeck),
    ("continued fraction", "φ = 1 + 1/(1 + 1/(1 + …))", v_fcontfrac),
    ("Pisano period", "last digits repeat every 60", v_fmod10),
    ("Binet's formula", "F(n) = (φⁿ − (−1/φ)ⁿ) / √5", v_fbinet),
]


# ---- part 2 visuals
def v_mult(c, cx, cy, S, p, col):
    n = int(12 * smooth(p)) + 1
    for i in range(min(n, 12)):
        r, k = i // 4, i % 4
        c.circle(cx - S * 0.6 + k * S * 0.4, cy - S * 0.4 + r * S * 0.4, S * 0.13, col)


def v_pct(c, cx, cy, S, p, col):
    c.ctx.rectangle(cx - S, cy - S * 0.15, 2 * S, S * 0.3)
    c.ctx.set_source_rgba(1, 1, 1, 0.7)
    c.ctx.set_line_width(3)
    c.ctx.stroke()
    c.ctx.rectangle(cx - S, cy - S * 0.15, 2 * S * 0.25 * smooth(p), S * 0.3)
    c.ctx.set_source_rgba(*col, 0.9)
    c.ctx.fill()


def v_sqrt2(c, cx, cy, S, p, col):
    a = S * 0.7
    x0, y0 = cx - a * 0.8, cy + a * 0.5
    c.ctx.rectangle(x0, y0 - a, a, a)
    c.ctx.set_source_rgba(1, 1, 1, 0.7)
    c.ctx.set_line_width(3)
    c.ctx.stroke()
    th = -math.pi / 4 * (1 - smooth((p - 0.4) / 0.6))
    d = a * 2 ** 0.5
    c.lines([(x0, y0, x0 + d * math.cos(th), y0 + d * math.sin(th))], col, width=7)


def v_circ(c, cx, cy, S, p, col):
    r = S * 0.28
    u = smooth(p)
    c.ring(cx - S + r, cy - r * 1.2, r, WHITE, width=3, alpha=0.6)
    c.lines([(cx - S, cy + r * 0.6, cx - S + 2 * math.pi * r * u, cy + r * 0.6)], col, width=8)


def v_log(c, cx, cy, S, p, col):
    _plot(c, cx, cy, S, lambda x: math.log10(x), 0.05, 1000, -1.4, 3.2, p, col)


def v_vec(c, cx, cy, S, p, col):
    u = smooth(p)
    o = (cx - S * 0.7, cy + S * 0.5)
    a = (o[0] + S * 0.9, o[1] - S * 0.3)
    b = (a[0] + S * 0.4 * u, a[1] - S * 0.8 * u)
    c.lines([(*o, *a)], WHITE, width=6)
    c.lines([(*a, *b)], GREY, width=6)
    if u > 0.5:
        c.lines([(*o, *b)], col, width=8, alpha=smooth((p - 0.5) / 0.3))


def v_deriv(c, cx, cy, S, p, col):
    _plot(c, cx, cy, S, lambda x: x * x, -2, 2, 0, 4, 1.0, WHITE, width=4)
    x0 = -1.8 + 3.6 * smooth(p)
    X = lambda x: cx - S + 2 * S * (x + 2) / 4                  # noqa: E731
    Yv = lambda y: cy + S * 0.6 - 1.2 * S * y / 4               # noqa: E731
    sl = 2 * x0
    c.lines([(X(x0 - 1), Yv(x0 * x0 - sl), X(x0 + 1), Yv(x0 * x0 + sl))], col, width=5)
    c.circle(X(x0), Yv(x0 * x0), 10, GOLD)


def v_lim(c, cx, cy, S, p, col):
    yl = lambda v: cy + S * 0.6 - 1.2 * S * (v - 1.9) / 1.0      # noqa: E731
    c.lines([(cx - S, yl(math.e), cx + S, yl(math.e))], GOLD, width=2, alpha=0.6)
    n = 1 + int(14 * smooth(p))
    pts = [(cx - S + 2 * S * i / 14, yl((1 + 1 / (i + 1)) ** (i + 1))) for i in range(n)]
    c.polylines([pts], col, width=5)


def v_imag(c, cx, cy, S, p, col):
    r = S * 0.6
    c.lines([(cx - r * 1.3, cy, cx + r * 1.3, cy), (cx, cy - r * 1.3, cx, cy + r * 1.3)], WHITE, width=2, alpha=0.4)
    th = math.pi * smooth(p)
    c.lines([(cx, cy, cx + r * math.cos(th), cy - r * math.sin(th))], col, width=8)
    c.circle(cx + r * math.cos(th), cy - r * math.sin(th), 12, WHITE)


def v_taylor(c, cx, cy, S, p, col):
    _plot(c, cx, cy, S, math.sin, -math.pi, math.pi, -1.5, 1.5, 1.0, WHITE, width=3)
    n = 1 + int(4 * smooth(p))
    f = lambda x: sum((-1) ** k * x ** (2 * k + 1) / math.factorial(2 * k + 1) for k in range(n))   # noqa: E731
    _plot(c, cx, cy, S, lambda x: max(-1.5, min(1.5, f(x))), -math.pi, math.pi, -1.5, 1.5, 1.0, col, width=5)


def v_inf(c, cx, cy, S, p, col):
    th = np.linspace(0, 2 * math.pi * smooth(p), 300)
    a = S * 0.9
    pts = [(cx + a * math.cos(t) / (1 + math.sin(t) ** 2), cy + a * math.sin(t) * math.cos(t) / (1 + math.sin(t) ** 2)) for t in th]
    if len(pts) > 1:
        c.polylines([pts], col, width=10, alpha=0.2)
        c.polylines([pts], col, width=5)


def v_zeta(c, cx, cy, S, p, col):
    n = 1 + int(11 * smooth(p))
    tot = 0.0
    yl = lambda v: cy + S * 0.6 - 1.2 * S * v / 1.75             # noqa: E731
    c.lines([(cx - S, yl(math.pi ** 2 / 6), cx + S, yl(math.pi ** 2 / 6))], GOLD, width=2, alpha=0.7)
    for i in range(n):
        v = 1 / (i + 1) ** 2
        x = cx - S + 2 * S * i / 12
        c.ctx.rectangle(x + 3, yl(tot + v), 2 * S / 12 - 6, yl(tot) - yl(tot + v))
        c.ctx.set_source_rgba(*level_col(i / 12), 0.9)
        c.ctx.fill()
        tot += v


MANDEL = None


def v_mandel(c, cx, cy, S, p, col):
    global MANDEL
    if MANDEL is None:
        pts = []
        for i in range(70):
            for j in range(60):
                x0, y0 = -2.2 + 2.8 * i / 69, -1.2 + 2.4 * j / 59
                z = 0j
                k = 0
                while k < 40 and abs(z) <= 2:
                    z = z * z + complex(x0, y0)
                    k += 1
                if k == 40:
                    pts.append((x0, y0))
        MANDEL = pts
    n = int(len(MANDEL) * smooth(p))
    for x0, y0 in MANDEL[:n]:
        c.circle(cx + S * 0.75 * (x0 + 0.7), cy + S * 0.75 * y0, 3.2, col)


def v_riemann(c, cx, cy, S, p, col):
    c.lines([(cx, cy - S, cx, cy + S)], GOLD, width=3, alpha=0.8)
    c.lines([(cx - S, cy, cx + S, cy)], WHITE, width=2, alpha=0.4)
    zeros = [14.13, 21.02, 25.01, 30.42, 32.94, 37.59, 40.92, 43.33, 48.01, 49.77]
    n = int(len(zeros) * smooth(p))
    for k in range(n):
        for s_ in (1, -1):
            c.circle(cx, cy - s_ * S * zeros[k] / 52, 9, col)


P2_LEVELS = [
    ("multiplication", "3 × 4 = 12", v_mult),
    ("percentages", "25 % of 80 = 20", v_pct),
    ("powers", "2¹⁰ = 1,024", v_exp),
    ("square roots", "√2 = 1.41421…", v_sqrt2),
    ("circles", "C = 2πr", v_circ),
    ("logarithms", "log 1000 = 3  (10³ = 1000)", v_log),
    ("vectors", "a + b", v_vec),
    ("derivatives", "d/dx x² = 2x", v_deriv),
    ("limits", "(1 + 1/n)ⁿ → e", v_lim),
    ("imaginary numbers", "i² = −1", v_imag),
    ("Taylor series", "sin x = x − x³/3! + …", v_taylor),
    ("golden ratio", "φ = 1.618…", v_fspiral),
    ("infinity", "1 + 2 + 3 + … → ∞", v_inf),
    ("Basel problem", "1 + 1/4 + 1/9 + … = π²/6", v_zeta),
    ("Mandelbrot set", "z → z² + c", v_mandel),
    ("Riemann hypothesis", "every zero on Re(s) = ½ ?", v_riemann),
]
# ---- algebra visuals (owner, 2026-10-18: "16 levels of algebra")
def _axes(c, cx, cy, S, alpha=0.5):
    c.lines([(cx - S, cy, cx + S, cy), (cx, cy - S * 0.75, cx, cy + S * 0.75)], WHITE, width=2, alpha=alpha)


def _balance(c, cx, cy, S, p, col, nx, a, b):
    """A balance: left = nx boxes 'x' + a dots, right = b dots. Remove a from both sides, then share b among the boxes."""
    ctx = c.ctx
    c.poly([(cx, cy + S * 0.05), (cx - S * 0.12, cy + S * 0.3), (cx + S * 0.12, cy + S * 0.3)], WHITE, alpha=0.7)
    c.lines([(cx - S * 0.95, cy, cx + S * 0.95, cy)], WHITE, width=5, alpha=0.85)
    rm = smooth(p / 0.45)
    r = S * 0.07
    for i in range(nx):
        x0 = cx - S * 0.85 + i * S * 0.28
        ctx.rectangle(x0, cy - S * 0.26, S * 0.22, S * 0.24)
        ctx.set_source_rgba(*col, 0.9)
        ctx.fill()
        c.text_centered("x", cy - S * 0.08, size=S * 0.18, color=(0.05, 0.05, 0.08), cx=x0 + S * 0.11)
    for j in range(a):
        x = cx - S * 0.85 + nx * S * 0.28 + j * S * 0.17 + r
        c.circle(x, cy - r - 2 - rm * S * 0.4, r, WHITE, alpha=1 - rm)
    k = b - a
    share = smooth((p - 0.5) / 0.4) if nx > 1 else 0.0
    for j in range(b):
        removed = j >= k
        x = cx + S * 0.15 + j * S * 0.11 + r
        y = cy - r - 2
        if not removed and share > 0:                       # dots walk under their box
            box = j % nx
            tx = cx - S * 0.85 + box * S * 0.28 + S * 0.11 + (j // nx - 1) * S * 0.08
            x, y = x + (tx - x) * share, y + (cy + S * 0.5 - y) * share
        c.circle(x, y - (rm * S * 0.4 if removed else 0), r, WHITE, alpha=(1 - rm) if removed else 1.0)


def v_bal1(c, cx, cy, S, p, col):
    _balance(c, cx, cy, S, p, col, 1, 3, 5)


def v_bal2(c, cx, cy, S, p, col):
    _balance(c, cx, cy, S, p, col, 2, 1, 7)


def v_distrib(c, cx, cy, S, p, col):
    ctx = c.ctx
    h_, wx, w2 = S * 0.6, S * 1.0, S * 0.6
    x0, y0 = cx - (wx + w2) / 2, cy - h_ / 2
    q = smooth(p / 0.5)
    ctx.rectangle(x0, y0, wx * q, h_)
    ctx.set_source_rgba(*col, 0.85)
    ctx.fill()
    ctx.rectangle(x0 + wx, y0, w2 * smooth((p - 0.4) / 0.4), h_)
    ctx.set_source_rgba(1, 1, 1, 0.75)
    ctx.fill()
    c.text_centered("3", cy + S * 0.05, size=S * 0.16, color=WHITE, cx=x0 - S * 0.1)
    if p > 0.5:
        c.text_centered("3x", cy + S * 0.06, size=S * 0.2, color=(0.05, 0.05, 0.08), cx=x0 + wx / 2)
    if p > 0.8:
        c.text_centered("6", cy + S * 0.06, size=S * 0.2, color=(0.05, 0.05, 0.08), cx=x0 + wx + w2 / 2)


def v_line(c, cx, cy, S, p, col):
    _axes(c, cx, cy, S)
    k = S * 0.25
    xs = np.linspace(-2, -2 + 4 * max(p, 0.02), 60)
    pts = [(cx + x * k, cy - (2 * x + 1) * k / 2) for x in xs]
    c.polylines([pts], col, width=7)
    if p > 0.6:
        a = smooth((p - 0.6) / 0.3)
        c.lines([(cx, cy - k / 2, cx + k, cy - k / 2), (cx + k, cy - k / 2, cx + k, cy - k * 1.5)], WHITE, width=3, alpha=a)


def v_system(c, cx, cy, S, p, col):
    _axes(c, cx, cy, S)
    k = S * 0.16

    def P(x, y):
        return cx + (x - 2.5) * k, cy - (y - 2.5) * k

    u = smooth(p / 0.7)
    c.lines([(*P(0, 5), *P(0 + 5 * u, 5 - 5 * u))], col, width=6)
    c.lines([(*P(1, 0), *P(1 + 4.5 * u, 4.5 * u))], WHITE, width=6, alpha=0.85)
    if p > 0.75:
        x, y = P(3, 2)
        c.glow(x, y, S * 0.12, col, strength=0.8, reach=2)
        c.circle(x, y, 12, WHITE)


def v_square(c, cx, cy, S, p, col):
    ctx = c.ctx
    a, b = S * 0.75, S * 0.45
    x0, y0 = cx - (a + b) / 2, cy - (a + b) / 2
    parts = [(x0, y0, a, a, col, 0.9), (x0 + a, y0, b, a, WHITE, 0.55), (x0, y0 + a, a, b, WHITE, 0.55),
             (x0 + a, y0 + a, b, b, GOLD, 0.9)]
    for i, (x, y, wd, ht, cc, al) in enumerate(parts):
        q = smooth((p - i * 0.2) / 0.2)
        if q > 0:
            ctx.rectangle(x, y, wd, ht)
            ctx.set_source_rgba(*cc, al * q)
            ctx.fill()
    ctx.rectangle(x0, y0, a + b, a + b)
    ctx.set_source_rgba(1, 1, 1, 0.8)
    ctx.set_line_width(3)
    ctx.stroke()


def v_diffsq(c, cx, cy, S, p, col):
    a, b = S * 1.0, S * 0.4
    x0, y0 = cx - a * 0.75, cy + a * 0.45                      # bottom-left of the big square (y up = minus)
    c.poly([(x0, y0), (x0 + a, y0), (x0 + a, y0 - (a - b)), (x0, y0 - (a - b))], col, alpha=0.85)   # strip a × (a−b)
    u = smooth((p - 0.3) / 0.6)                                 # the top piece (a−b) × b swings to the right
    corners = [(0, a - b), (a - b, a - b), (a - b, a), (0, a)]
    tgt = [(a + b, 0), (a + b, a - b), (a, a - b), (a, 0)]
    pts = [(x0 + (cx0 + (tx - cx0) * u), y0 - (cy0 + (ty - cy0) * u)) for (cx0, cy0), (tx, ty) in zip(corners, tgt)]
    c.poly(pts, GOLD, alpha=0.85)
    if p < 0.3:
        c.ctx.rectangle(x0 + a - b, y0 - a, b, b)
        c.ctx.set_source_rgba(1, 1, 1, 0.5 * (1 - p / 0.3))
        c.ctx.set_line_width(3)
        c.ctx.stroke()


def v_qform(c, cx, cy, S, p, col):
    _axes(c, cx, cy + S * 0.3, S, alpha=0.4)
    k = S * 0.28
    xs = np.linspace(-1.5, -1.5 + 5 * max(p, 0.02), 80)
    pts = [(cx + (x - 1) * k, cy + S * 0.3 - (-(x * x - 2 * x - 3)) * k * 0.3) for x in xs]
    c.polylines([pts], col, width=7)
    if p > 0.6:
        a = smooth((p - 0.6) / 0.3)
        y = cy + S * 0.3
        c.lines([(cx, y, cx - 2 * k * a, y), (cx, y, cx + 2 * k * a, y)], GOLD, width=5)
        c.text_centered("±", y - S * 0.12, size=S * 0.22, color=GOLD, alpha=a, cx=cx)


def v_ineq(c, cx, cy, S, p, col):
    c.lines([(cx - S, cy, cx + S, cy)], WHITE, width=3, alpha=0.7)
    for i in range(-4, 5):
        x = cx + i * S / 4.5
        c.lines([(x, cy - 10, x, cy + 10)], WHITE, width=2, alpha=0.6)
    x2 = cx + 2 * S / 4.5
    c.lines([(x2, cy - S * 0.12, x2 + (cx + S - x2) * smooth(p), cy - S * 0.12)], col, width=10)
    c.ring(x2, cy - S * 0.12, 14, col, width=4)
    c.text_centered("2", cy + S * 0.18, size=S * 0.14, color=WHITE, cx=x2)


def v_abs(c, cx, cy, S, p, col):
    _axes(c, cx, cy + S * 0.35, S, alpha=0.4)
    k = S * 0.22
    y0 = cy + S * 0.35
    xs = np.linspace(-3, -3 + 7 * max(p, 0.02), 80)
    c.polylines([[(cx + x * k, y0 - abs(x - 1) * k) for x in xs]], col, width=7)
    c.lines([(cx - S, y0 - 2 * k, cx + S, y0 - 2 * k)], WHITE, width=3, alpha=0.6)
    for r in (-1, 3):
        if p > (r + 3) / 7:
            c.circle(cx + r * k, y0 - 2 * k, 12, GOLD)


def v_cubic(c, cx, cy, S, p, col):
    _axes(c, cx, cy, S, alpha=0.4)
    _plot(c, cx, cy - S * 0.0, S, lambda x: x ** 3 - x, -1.6, 1.6, -1.6, 1.6, p, col)
    for r in (-1, 0, 1):
        if p > (r + 1.6) / 3.2:
            c.circle(cx + r * S / 1.6, cy, 12, GOLD)


def v_croots(c, cx, cy, S, p, col):
    _axes(c, cx, cy + S * 0.3, S, alpha=0.4)
    k = S * 0.3
    xs = np.linspace(-2.2, -2.2 + 4.4 * max(p, 0.02), 80)
    c.polylines([[(cx + x * k, cy + S * 0.3 - (x * x + 1) * k * 0.45) for x in xs]], col, width=7)
    if p > 0.65:
        a = smooth((p - 0.65) / 0.3)
        for s_ in (1, -1):
            c.circle(cx, cy + S * 0.3 - s_ * k * 1.4, 12, GOLD, alpha=a)
        c.text_centered("+i", cy + S * 0.3 - k * 1.4 + 8, size=S * 0.14, color=GOLD, alpha=a, cx=cx + S * 0.2)
        c.text_centered("−i", cy + S * 0.3 + k * 1.4 + 8, size=S * 0.14, color=GOLD, alpha=a, cx=cx + S * 0.2)


def v_quintic(c, cx, cy, S, p, col):
    _axes(c, cx, cy, S, alpha=0.4)
    _plot(c, cx, cy, S, lambda x: x ** 5 - 3 * x ** 3 + x + 0.3, -1.75, 1.75, -3, 3, p, col)
    if p > 0.7:
        a = smooth((p - 0.7) / 0.25)
        for r in (-1.6, -0.62, 0.3, 0.55, 1.5):
            c.text_centered("?", cy - S * 0.08, size=S * 0.2, color=GOLD, alpha=a, cx=cx + r * S / 1.75)


# ---- geometry visuals (owner, 2026-10-18: "16 levels of geometry")
def _tri(cx, cy, S):
    return [(cx - S * 0.8, cy + S * 0.45), (cx + S * 0.75, cy + S * 0.45), (cx - S * 0.1, cy - S * 0.6)]


def v_tri180(c, cx, cy, S, p, col):
    A, B, C = _tri(cx, cy - S * 0.15, S * 0.8)
    c.polylines([[A, B, C, A]], WHITE, width=4)
    angs = []
    for P_, Q, R_ in ((A, B, C), (B, C, A), (C, A, B)):
        a1 = math.atan2(Q[1] - P_[1], Q[0] - P_[0])
        a2 = math.atan2(R_[1] - P_[1], R_[0] - P_[0])
        d = (a2 - a1) % (2 * math.pi)
        if d > math.pi:
            a1, a2, d = a2, a1, 2 * math.pi - d
        angs.append(d)
    cols = [col, GOLD, (0.5, 0.8, 1.0)]
    ox, oy, r = cx, cy + S * 0.75, S * 0.35                     # the three angles placed on a straight line
    a0 = math.pi
    ctx = c.ctx
    for i, d in enumerate(angs):
        q = smooth((p - i * 0.25) / 0.25)
        if q <= 0:
            continue
        ctx.move_to(ox, oy)
        ctx.arc(ox, oy, r, a0, a0 + d * q)
        ctx.close_path()
        ctx.set_source_rgba(*cols[i], 0.85)
        ctx.fill()
        a0 += d
    c.lines([(ox - r * 1.2, oy, ox + r * 1.2, oy)], WHITE, width=3, alpha=0.7)


def v_rect(c, cx, cy, S, p, col):
    ctx = c.ctx
    n = int(12 * smooth(p)) + (1 if p > 0 else 0)
    k = S * 0.38
    x0, y0 = cx - 2 * k, cy - 1.5 * k
    for i in range(min(n, 12)):
        r, q = i // 4, i % 4
        ctx.rectangle(x0 + q * k + 3, y0 + r * k + 3, k - 6, k - 6)
        ctx.set_source_rgba(*col, 0.85)
        ctx.fill()
    ctx.rectangle(x0, y0, 4 * k, 3 * k)
    ctx.set_source_rgba(1, 1, 1, 0.8)
    ctx.set_line_width(3)
    ctx.stroke()


def v_tri_area(c, cx, cy, S, p, col):
    ctx = c.ctx
    wd, ht = S * 1.6, S * 0.9
    x0, y0 = cx - wd / 2, cy + ht / 2
    apex = (x0 + wd * 0.35, y0 - ht)
    ctx.rectangle(x0, y0 - ht, wd, ht)
    ctx.set_source_rgba(1, 1, 1, 0.6)
    ctx.set_line_width(2)
    ctx.stroke()
    c.poly([(x0, y0), (x0 + wd, y0), apex], col, alpha=0.85 * smooth(p / 0.5))
    if p > 0.5:
        a = smooth((p - 0.5) / 0.3)
        c.lines([(apex[0], apex[1], apex[0], y0)], GOLD, width=4, alpha=a)


def v_circle_area(c, cx, cy, S, p, col):
    ctx = c.ctx
    r = S * 0.6
    ctx.move_to(cx, cy)
    ctx.arc(cx, cy, r, -math.pi / 2, -math.pi / 2 + 2 * math.pi * smooth(p))
    ctx.close_path()
    ctx.set_source_rgba(*col, 0.85)
    ctx.fill()
    c.ring(cx, cy, r, WHITE, width=3, alpha=0.7)
    c.lines([(cx, cy, cx + r, cy)], GOLD, width=4)
    c.text_centered("r", cy - 10, size=S * 0.15, color=GOLD, cx=cx + r / 2)


def v_poly(c, cx, cy, S, p, col):
    n = 3 + min(5, int(6 * p))
    r = S * 0.65
    pts = [(cx + r * math.cos(-math.pi / 2 + 2 * math.pi * k / n), cy + r * math.sin(-math.pi / 2 + 2 * math.pi * k / n))
           for k in range(n)]
    c.poly(pts, col, alpha=0.35)
    c.polylines([pts + [pts[0]]], col, width=5)
    c.lines([(pts[0][0], pts[0][1], q[0], q[1]) for q in pts[2:-1]], WHITE, width=3, alpha=0.75)
    c.text_centered(f"n = {n}", cy + r + S * 0.2, size=S * 0.16, color=WHITE)


def v_similar(c, cx, cy, S, p, col):
    k = S * 0.55
    base = (cx - k, cy + k * 0.6)

    def T(ox, oy, s, up=True):
        if up:
            return [(ox, oy), (ox + s, oy), (ox + s / 2, oy - s * 0.87)]
        return [(ox, oy - s * 0.87), (ox + s, oy - s * 0.87), (ox + s / 2, oy)]

    c.poly(T(base[0], base[1], k), col, alpha=0.85)
    if p > 0.3:
        a = smooth((p - 0.3) / 0.5)
        for (ox, oy, up) in ((base[0] + k, base[1], True), (base[0] + k / 2, base[1] - k * 0.87, True),
                             (base[0] + k / 2, base[1], False)):
            c.poly(T(ox, oy, k, up), col if up else GOLD, alpha=0.85 * a)
        c.polylines([T(base[0], base[1], 2 * k) + [base]], WHITE, width=3, alpha=a)


def v_thales(c, cx, cy, S, p, col):
    r = S * 0.7
    y0 = cy + S * 0.3
    pts = [(cx + r * math.cos(a), y0 - r * math.sin(a)) for a in np.linspace(0, math.pi, 60)]
    c.polylines([pts], WHITE, width=3, alpha=0.7)
    c.lines([(cx - r, y0, cx + r, y0)], WHITE, width=3, alpha=0.7)
    a = math.pi * (0.15 + 0.7 * smooth(p))
    P_ = (cx + r * math.cos(a), y0 - r * math.sin(a))
    c.polylines([[(cx - r, y0), P_, (cx + r, y0)]], col, width=6)
    u1 = np.array([cx - r - P_[0], y0 - P_[1]])
    u2 = np.array([cx + r - P_[0], y0 - P_[1]])
    u1, u2 = u1 / np.linalg.norm(u1) * S * 0.12, u2 / np.linalg.norm(u2) * S * 0.12
    q = [(P_[0] + u1[0], P_[1] + u1[1]), (P_[0] + u1[0] + u2[0], P_[1] + u1[1] + u2[1]), (P_[0] + u2[0], P_[1] + u2[1])]
    c.polylines([q], GOLD, width=3)


def v_inscribed(c, cx, cy, S, p, col):
    r = S * 0.6
    c.ring(cx, cy, r, WHITE, width=3, alpha=0.6)
    A = (cx + r * math.cos(math.radians(210)), cy - r * math.sin(math.radians(210)))
    B = (cx + r * math.cos(math.radians(330)), cy - r * math.sin(math.radians(330)))
    t = math.radians(40 + 100 * smooth(p))
    P_ = (cx + r * math.cos(t), cy - r * math.sin(t))
    c.polylines([[A, (cx, cy), B]], GOLD, width=5)
    c.polylines([[A, P_, B]], col, width=5)
    c.circle(P_[0], P_[1], 10, WHITE)


def v_sphere(c, cx, cy, S, p, col):
    ctx = c.ctx
    r = S * 0.62
    g = cairo.RadialGradient(cx - r * 0.3, cy - r * 0.3, r * 0.1, cx, cy, r)
    g.add_color_stop_rgba(0, min(1, col[0] + 0.3), min(1, col[1] + 0.3), min(1, col[2] + 0.3), 0.95)
    g.add_color_stop_rgba(1, col[0] * 0.4, col[1] * 0.4, col[2] * 0.4, 0.95)
    ctx.arc(cx, cy, r * smooth(p / 0.5), 0, 2 * math.pi)
    ctx.set_source(g)
    ctx.fill()
    for k in range(3):
        sx = abs(math.cos(p * 3 + k * math.pi / 3))
        ctx.save()
        ctx.translate(cx, cy)
        ctx.scale(max(0.02, sx), 1)
        ctx.arc(0, 0, r, 0, 2 * math.pi)
        ctx.restore()
        ctx.set_source_rgba(1, 1, 1, 0.35)
        ctx.set_line_width(2)
        ctx.stroke()


def v_cube(c, cx, cy, S, p, col):
    a = p * 2.2 + 0.4
    b = 0.5
    V = [(x, y, z) for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)]

    def P(v):
        x, y, z = v
        x, z = x * math.cos(a) + z * math.sin(a), -x * math.sin(a) + z * math.cos(a)
        y, z = y * math.cos(b) - z * math.sin(b), y * math.sin(b) + z * math.cos(b)
        return cx + x * S * 0.42, cy + y * S * 0.42

    E = [(i, j) for i in range(8) for j in range(i + 1, 8) if sum(abs(V[i][k] - V[j][k]) for k in range(3)) == 2]
    c.lines([(*P(V[i]), *P(V[j])) for i, j in E], col, width=5)
    for v in V:
        x, y = P(v)
        c.circle(x, y, 10, WHITE)


def v_tess(c, cx, cy, S, p, col):
    r = S * 0.2
    cells = []
    for q in range(-3, 4):
        for s_ in range(-3, 4):
            x = cx + r * 1.5 * q
            y = cy + r * math.sqrt(3) * (s_ + q / 2)
            d = math.hypot(x - cx, y - cy)
            if d < S * 0.85:
                cells.append((d, x, y))
    cells.sort()
    n = int(len(cells) * smooth(p)) + 1
    for i, (d, x, y) in enumerate(cells[:n]):
        pts = [(x + r * math.cos(math.pi / 3 * k), y + r * math.sin(math.pi / 3 * k)) for k in range(6)]
        c.poly(pts, col if i % 3 else GOLD, alpha=0.8)
        c.polylines([pts + [pts[0]]], (0.05, 0.05, 0.08), width=3)


def v_sphere_tri(c, cx, cy, S, p, col):
    ctx = c.ctx
    r = S * 0.65
    c.ring(cx, cy, r, WHITE, width=3, alpha=0.6)
    ctx.save()
    ctx.translate(cx, cy)
    ctx.scale(1, 0.32)
    ctx.arc(0, 0, r, 0, math.pi)
    ctx.restore()
    ctx.set_source_rgba(1, 1, 1, 0.4)
    ctx.set_line_width(2)
    ctx.stroke()
    N = (cx, cy - r)
    E1 = (cx - r * 0.7, cy + r * 0.32 * 0.71)
    E2 = (cx + r * 0.7, cy + r * 0.32 * 0.71)
    q = smooth(p / 0.6)
    arc1 = [(cx + (E1[0] - cx) * math.sin(t * math.pi / 2), N[1] + (E1[1] - N[1]) * (1 - math.cos(t * math.pi / 2)))
            for t in np.linspace(0, q, 30)]
    arc2 = [(cx + (E2[0] - cx) * math.sin(t * math.pi / 2), N[1] + (E2[1] - N[1]) * (1 - math.cos(t * math.pi / 2)))
            for t in np.linspace(0, q, 30)]
    c.polylines([arc1, arc2], col, width=6)
    if p > 0.6:
        ctx.save()
        ctx.translate(cx, cy)
        ctx.scale(1, 0.32)
        a0, a1 = math.radians(135), math.radians(45)
        ctx.arc_negative(0, 0, r, a0, a0 + (a1 - a0) * smooth((p - 0.6) / 0.3))
        ctx.restore()
        ctx.set_source_rgba(*col, 0.95)
        ctx.set_line_width(6)
        ctx.stroke()
        for P_ in (N, E1, E2):
            c.text_centered("90°", P_[1] + (S * 0.2 if P_ is N else -S * 0.05), size=S * 0.12, color=GOLD, cx=P_[0])


def v_pack(c, cx, cy, S, p, col):
    r = S * 0.13
    cells = []
    for j in range(-4, 5):
        for i in range(-5, 6):
            x = cx + (i + 0.5 * (j % 2)) * 2 * r
            y = cy + j * r * math.sqrt(3)
            d = math.hypot(x - cx, y - cy)
            if d < S * 0.8:
                cells.append((d, x, y))
    cells.sort()
    n = int(len(cells) * smooth(p)) + 1
    for i, (d, x, y) in enumerate(cells[:n]):
        c.circle(x, y, r * 0.97, col if i % 2 else GOLD, alpha=0.9)


ALG_LEVELS = [
    ("solving for x", "x + 3 = 5  →  x = 2", v_bal1),
    ("two steps", "2x + 1 = 7  →  x = 3", v_bal2),
    ("brackets", "3(x + 2) = 3x + 6", v_distrib),
    ("lines", "y = 2x + 1", v_line),
    ("systems", "x + y = 5,  x − y = 1  →  (3, 2)", v_system),
    ("perfect squares", "(a + b)² = a² + 2ab + b²", v_square),
    ("difference of squares", "a² − b² = (a + b)(a − b)", v_diffsq),
    ("quadratics", "x² − 5x + 6 = 0  →  x = 2, 3", v_alg),
    ("the quadratic formula", "x = (−b ± √(b² − 4ac)) / 2a", v_qform),
    ("inequalities", "2x − 1 > 3  →  x > 2", v_ineq),
    ("absolute value", "|x − 1| = 2  →  x = −1, 3", v_abs),
    ("exponents", "2³ · 2⁴ = 2⁷ = 128", v_exp),
    ("logarithms", "2^x = 8  →  x = log 8 / log 2 = 3", v_log),
    ("cubics", "x³ − x = 0  →  x = −1, 0, 1", v_cubic),
    ("complex roots", "x² + 1 = 0  →  x = ±i", v_croots),
    ("the impossible one", "degree 5: NO general formula (Abel, 1824)", v_quintic),
]
GEO_LEVELS = [
    ("triangle angles", "a + b + c = 180°", v_tri180),
    ("rectangle area", "A = 4 × 3 = 12", v_rect),
    ("triangle area", "A = ½ × base × height", v_tri_area),
    ("circle area", "A = πr²", v_circle_area),
    ("Pythagoras", "a² + b² = c²", v_pyth),
    ("polygon angles", "sum = (n − 2) × 180°", v_poly),
    ("similar shapes", "2× the size → 4× the area", v_similar),
    ("Thales' theorem", "any angle in a semicircle = 90°", v_thales),
    ("π", "circumference ÷ diameter = 3.14159…", v_circ),
    ("inscribed angles", "centre angle = 2 × inscribed angle", v_inscribed),
    ("sphere volume", "V = 4/3 · πr³", v_sphere),
    ("Euler's formula", "V − E + F = 8 − 12 + 6 = 2", v_cube),
    ("tilings", "only 3 regular shapes tile the plane", v_tess),
    ("golden ratio", "φ = 1.618…", v_fspiral),
    ("curved space", "a triangle on a sphere: 90° + 90° + 90° = 270°", v_sphere_tri),
    ("Kepler's conjecture", "densest packing = π/√18 ≈ 74% (proved 2014)", v_pack),
]
SET = arg("--set", "math")
if SET == "fib":
    LEVELS = FIB_LEVELS
elif SET == "p2":
    LEVELS = P2_LEVELS
elif SET == "alg":
    LEVELS = ALG_LEVELS
elif SET == "geo":
    LEVELS = GEO_LEVELS
N_LV = len(LEVELS)
DUR = [0.90 * 0.955 ** i for i in range(N_LV)]          # each level a bit faster than the last
BEAT = arg("--beat", "")                                # "hardtekk": original 170 BPM beat, levels on the grid
BPM = 170.0
B = 60.0 / BPM
if BEAT == "hardtekk":
    SLOW_END = float(arg("--slowend", "1"))             # beats per level for levels 9-16 (owner: algebra = 1.5)
    DUR = [2 * B] * 8 + [SLOW_END * B] * 8              # 2 beats per level, then 1 (twice as fast)
LV_BEATS = int(round(sum(DUR) / B)) if BEAT == "hardtekk" else 24
STARTS = list(np.concatenate([[0.0], np.cumsum(DUR)[:-1]]))
T_RUN = float(sum(DUR))
T_LOOP = T_RUN + T_MAX
# --hook 1: payoff-first + beat. The video opens on the finished LEVEL MAX (scene time T_A..), snaps back to
# LEVEL 1 at T_TEASE, plays the ladder on a kick drum, and ends exactly at T_A (seamless loop).
HOOK = arg("--hook", "0") == "1"
T_TEASE = 2 * B if BEAT == "hardtekk" else 0.7
# --question 1: a "STILL EASY?" break of 2 beats before level 9 (where the levels double speed).
QUESTION = arg("--question", "0") == "1" and BEAT == "hardtekk"
Q_IDX = 8
QD = 2 * B if QUESTION else 0.0
Q_T0 = STARTS[Q_IDX]                                   # in level time (== scene time before the break)


def lvl_t(t):
    """Scene time -> level time (None during the question break)."""
    if not QUESTION or t < Q_T0:
        return t
    if t < Q_T0 + QD:
        return None
    return t - QD


def to_scene(t):
    return t + QD if (QUESTION and t >= Q_T0) else t


T_A = T_RUN + QD + (8 * B if BEAT == "hardtekk" else 2.9)  # hardtekk: the loop = 34 beats (+2 with the question)
V_LEN = T_TEASE + T_A if HOOK else T_LOOP


def scene_t(v):
    if not HOOK:
        return v
    return T_A + v if v < T_TEASE else v - T_TEASE


def simulate():
    return {"nf": int(round(V_LEN * FPS))}


def level_at(t):
    if t >= T_RUN:
        return N_LV, (t - T_RUN) / T_MAX
    i = max(j for j in range(N_LV) if STARTS[j] <= t)
    return i, (t - STARTS[i]) / DUR[i]


class Scene:
    def __init__(self, layout, sim):
        self.L, self.sim = layout, sim
        self.canvas = Canvas(layout.w, layout.h, studio.render_scale())
        th = np.linspace(0, 260, 26000)
        self.phi_pts = np.stack([np.cos(th) + np.cos(PHI * th), np.sin(th) + np.sin(PHI * th)], 1)

    def draw(self, f, rule):
        L, c = self.L, self.canvas
        w, h = L.w, L.h
        t = scene_t(f * DT)
        lt = lvl_t(t)
        if lt is None:
            return self.question(t - Q_T0, rule)
        t = lt
        i, p = level_at(t)
        ctx = c.ctx
        u = min(i, N_LV) / N_LV
        col = level_col(min(u, 1.0))
        g = cairo.RadialGradient(w / 2, h * 0.47, 0, w / 2, h * 0.47, max(w, h) * 0.7)
        g.add_color_stop_rgb(0.0, 0.07, 0.06, 0.11)
        g.add_color_stop_rgb(1.0, 0.01, 0.01, 0.02)
        ctx.set_source(g)
        ctx.paint()
        cx, cy, S = w / 2, h * 0.47, w * 0.30
        if i < N_LV:
            name, formula, vis = LEVELS[i]
            age = p * DUR[i]
            pop = 1.0 + (0.6 if HOOK else 0.25) * math.exp(-age / (0.07 if HOOK else 0.08))
            if HOOK and age < 0.35:                           # level-up ring burst behind the number
                c.ring(w / 2, h * 0.205, w * (0.10 + 0.32 * smooth(age / 0.35)), col, width=5,
                       alpha=0.7 * (1 - age / 0.35))
            ctx.save()
            ctx.translate(cx, cy)
            ctx.scale(min(1.0, 0.85 + 1.5 * p), min(1.0, 0.85 + 1.5 * p))
            ctx.translate(-cx, -cy)
            vis(c, cx, cy, S, p, col)
            ctx.restore()
            c.text_centered(f"LEVEL {i + 1}", h * 0.222, size=w * 0.085 * pop, color=col)
            c.text_centered(name, h * 0.262, size=w * 0.045, color=WHITE, alpha=0.9, bold=False)
            c.text_centered(formula, h * 0.690, size=w * 0.060, color=WHITE, max_w=w * 0.92)
        else:                                              # LEVEL MAX: the never-closing golden curve
            q = smooth(p / 0.75)
            n = max(2, int(len(self.phi_pts) * q))
            pts = self.phi_pts[:n]
            R = S * 0.44
            chunks = 24
            for k in range(chunks):
                a, b = k * n // chunks, (k + 1) * n // chunks + 1
                if b - a < 2:
                    continue
                seg = [(cx + R * x, cy - R * y) for x, y in pts[a:b]]
                cc = kit.wheel(k / chunks * 0.9)
                c.polylines([seg], cc, width=2.2, alpha=0.75)
            tip = pts[-1]
            if q < 1:
                c.glow(cx + R * tip[0], cy - R * tip[1], 8, GOLD, strength=0.7, reach=4)
            bl = smooth((p - 0.05) / 0.15)
            c.glow(cx, h * 0.222, w * 0.06, (1.0, 0.35, 0.25), strength=0.25 * bl, reach=3)
            c.text_centered("LEVEL MAX", h * 0.222, size=w * 0.10 * (1 + 0.15 * math.exp(-p * T_MAX / 0.12)),
                            color=(1.0, 0.40, 0.30))
            c.text_centered("the golden ratio, forever", h * 0.262, size=w * 0.045, color=WHITE, alpha=0.9, bold=False)
            c.text_centered("e^(iθ) + e^(iφθ)", h * 0.690, size=w * 0.065, color=GOLD)
        # difficulty meter
        mx0, mx1, my, mh = w * 0.12, w * 0.88, h * 0.290, h * 0.012
        ctx.rectangle(mx0, my, mx1 - mx0, mh)
        ctx.set_source_rgba(1, 1, 1, 0.12)
        ctx.fill()
        fill = (min(i, N_LV) + (min(p, 1.0) if i < N_LV else 0)) / N_LV
        grad = cairo.LinearGradient(mx0, 0, mx1, 0)
        for k in range(5):
            grad.add_color_stop_rgb(k / 4, *level_col(k / 4))
        ctx.rectangle(mx0, my, (mx1 - mx0) * min(fill, 1.0), mh)
        ctx.set_source(grad)
        ctx.fill()
        c.text_centered("difficulty", my - h * 0.004, size=h * 0.011, color=GREY, alpha=0.8, bold=False,
                        cx=mx0 + w * 0.06)
        if rule:
            c.caption(rule, alpha=1.0, layout=L)
        c.watermark(L)


def _question(self, a, rule):
    """The break: 'STILL EASY?' slams in, alone, in red; the meter waits at level 8."""
    L, c = self.L, self.canvas
    w, h = L.w, L.h
    ctx = c.ctx
    g = cairo.RadialGradient(w / 2, h * 0.47, 0, w / 2, h * 0.47, max(w, h) * 0.7)
    g.add_color_stop_rgb(0.0, 0.10, 0.03, 0.04)
    g.add_color_stop_rgb(1.0, 0.01, 0.01, 0.02)
    ctx.set_source(g)
    ctx.paint()
    slam = 1.0 + 0.9 * math.exp(-a / 0.07)
    shake = 6 * math.exp(-a / 0.12) * math.sin(a * 90)
    red = (1.0, 0.25, 0.22)
    c.glow(w / 2, h * 0.45, w * 0.10, red, strength=0.25, reach=3)
    c.text_centered("STILL", h * 0.43, size=w * 0.13 * slam, color=WHITE, cx=w / 2 + shake)
    c.text_centered("EASY?", h * 0.53, size=w * 0.20 * slam, color=red, cx=w / 2 - shake)
    mx0, mx1, my, mh = w * 0.12, w * 0.88, h * 0.290, h * 0.012
    ctx.rectangle(mx0, my, mx1 - mx0, mh)
    ctx.set_source_rgba(1, 1, 1, 0.12)
    ctx.fill()
    grad = cairo.LinearGradient(mx0, 0, mx1, 0)
    for k in range(5):
        grad.add_color_stop_rgb(k / 4, *level_col(k / 4))
    ctx.rectangle(mx0, my, (mx1 - mx0) * Q_IDX / N_LV, mh)
    ctx.set_source(grad)
    ctx.fill()
    if rule:
        c.caption(rule, alpha=1.0, layout=L)
    c.watermark(L)


Scene.question = _question


def render(layout, sim, out_path, rule, still_frame=None):
    sc = Scene(layout, sim)
    writer = None if still_frame is not None else VideoWriter(out_path, sc.canvas, FPS)
    for f in range(sim["nf"]):
        if still_frame is not None and f != still_frame:
            continue
        sc.draw(f, rule)
        if writer is None:
            studio.save_still(sc.canvas, out_path)
            return f / FPS
        writer.write_frame()
    writer.close()
    return sim["nf"] / FPS


def build_events(sim, layout):
    scale = [0, 2, 4, 7, 9]
    out = []
    for i, t in enumerate(STARTS):
        note = 55 + 12 * (i // 5) + scale[i % 5]
        out.append({"t": round(t + 0.005, 4), "note": note, "gain": round(0.42 + 0.12 * i / N_LV, 3),
                    "x": layout.w / 2})
    for j, note in enumerate((50, 57, 62, 66, 69, 74, 78)):          # LEVEL MAX
        out.append({"t": round(T_RUN + 0.05 * j, 4), "note": note, "gain": 0.46, "x": layout.w / 2})
    for j, note in enumerate((81, 86, 90, 86, 81, 78)):              # shimmer while the curve fills
        out.append({"t": round(T_RUN + 0.6 + 0.35 * j, 4), "note": note, "gain": 0.20, "x": layout.w / 2})
    out = [dict(e, t=round(to_scene(e["t"]), 4)) for e in out]       # shift past the question break
    if QUESTION:                                                     # the break: a tense stab
        for j, note in enumerate((49, 55, 61, 67)):
            out.append({"t": round(Q_T0 + 0.01 * j, 4), "note": note, "gain": 0.5, "x": layout.w / 2})
    if HOOK:                                               # remap to video time; add the opening hit
        mapped = [dict(e, t=round(e["t"] + T_TEASE, 4)) for e in out if e["t"] < T_A]
        for j, note in enumerate((50, 57, 62, 66, 69, 74, 78)):          # instant chord on frame 0
            mapped.append({"t": round(0.005 + 0.012 * j, 4), "note": note, "gain": 0.5, "x": layout.w / 2})
        for j, note in enumerate((90, 86, 81, 78, 74, 69, 66, 62)):      # rewind whoosh into LEVEL 1
            mapped.append({"t": round(T_TEASE - 0.24 + 0.03 * j, 4), "note": note, "gain": 0.20, "x": layout.w / 2})
        for st in STARTS:                                                # level-up chime: a quick octave
            mapped.append({"t": round(to_scene(st) + T_TEASE + 0.06, 4), "note": 79, "gain": 0.22,
                           "x": layout.w / 2})
        out = mapped
    return sorted(out, key=lambda e: e["t"])


def hardtekk_bed(dur):
    """ORIGINAL hardtekk-style beat (genre conventions only: 170 BPM, distorted 4/4 kick, rolling offbeat
    bass, shuffled hats + claps, a snare roll into the drop, a rave-stab riff on the drop). No samples, no
    existing song. Laid on the video grid: beats 0-1 = the LEVEL MAX tease (drop), 2-25 = the levels (build),
    24-25 = snare roll, 26-33 = LEVEL MAX (drop). 34 beats = the loop, so it repeats seamlessly."""
    sr = audio.SR
    n = int(round(dur * sr))
    out = np.zeros(n)
    rng = np.random.default_rng(11)

    def put(sig, t0, g):
        idx = (np.arange(len(sig)) + int(round(t0 * sr))) % n
        np.add.at(out, idx, g * sig)

    def tone(L):
        return np.arange(int(L * sr)) / sr

    tt = tone(0.30)
    f = 48 + 170 * np.exp(-tt * 38)
    kick = np.sin(2 * np.pi * np.cumsum(f) / sr) * np.exp(-tt * 11)
    kick = np.tanh(4.5 * kick) / np.tanh(4.5)                       # the hardtekk distortion
    kick[: int(0.002 * sr)] *= np.linspace(0, 1, int(0.002 * sr))
    th = tone(0.07)
    hat = np.diff(rng.standard_normal(len(th) + 1)) * np.exp(-th * 70)
    tc = tone(0.18)
    clap = np.zeros(len(tc))
    for d in (0.0, 0.011, 0.022):
        i0 = int(d * sr)
        clap[i0:] += rng.standard_normal(len(tc) - i0) * np.exp(-tc[: len(tc) - i0] * 32)
    clap = np.convolve(clap, np.ones(3) / 3, "same")
    tb = tone(B / 4 * 0.9)

    def bass(midi):
        f0 = audio.midi_to_hz(midi)
        ph = (f0 * tb) % 1.0
        saw = 2 * ph - 1
        sig = np.convolve(saw, np.ones(6) / 6, "same") * np.exp(-tb * 18)
        return np.tanh(2.5 * sig)

    def stab(midis, L=B / 2 * 0.8):
        t2 = tone(L)
        sig = np.zeros(len(t2))
        for m in midis:
            for det in (0.995, 1.0, 1.005):
                ph = (audio.midi_to_hz(m) * det * t2) % 1.0
                sig += 2 * ph - 1
        sig = np.convolve(sig, np.ones(4) / 4, "same")
        return sig * np.exp(-t2 * 9) * np.clip(t2 / 0.004, 0, 1) / (3 * len(midis))

    roots = [45, 45, 41, 43]                                        # A A F G (one chord per 4 beats)
    riff = [(69, 72, 76), (69, 72, 76), (67, 72, 76), (69, 72, 76),
            (65, 69, 72), (65, 69, 72), (67, 71, 74), (67, 71, 74)]
    n_beats = int(round(dur / B))
    for k in range(n_beats):
        t0 = k * B
        qb = 2 if QUESTION else 0
        if QUESTION and k in (18, 19):                              # the break: no kick, no bass
            for j in range(4 if k == 18 else 8):
                put(clap, t0 + j * B / (4 if k == 18 else 8), 0.12 + 0.30 * ((k - 18) * 4 + j * (4 if k == 18 else 0.5)) / 8)
            continue
        drop = k < 2 or k >= 2 + LV_BEATS + qb
        build_u = 0 if drop else (k - 2) / LV_BEATS
        put(kick, t0, 0.95)
        root = roots[(k // 4) % 4]
        for q in (1, 2, 3):                                         # rolling offbeat bass (kick-bass-bass-bass)
            put(bass(root - 12 if q == 2 else root), t0 + q * B / 4, 0.32)
        put(hat, t0 + B / 2, 0.30)                                  # offbeat open hat
        if drop or k >= 10:
            put(hat, t0 + 0.78 * B, 0.16)                           # shuffle
        if (k % 2 == 1) and (drop or k >= 10):
            put(clap, t0, 0.42)
        if drop:                                                    # rave stab riff (8ths)
            for e in range(2):
                put(stab(riff[(2 * (k % 4) + e) % len(riff)]), t0 + e * B / 2, 0.55)
        if k - qb in (LV_BEATS, LV_BEATS + 1):                      # snare roll into the drop
            steps = 4 if k - qb == LV_BEATS else 8
            for j in range(steps):
                put(clap, t0 + j * B / steps, 0.15 + 0.35 * ((k - qb - LV_BEATS) * 4 + j * (4 / steps)) / 8)
        _ = build_u
    return (0.32 * out).astype(np.float32)


def beat_bed(dur):
    """Original kick drum on every level-up (and a bigger hit on MAX), plus the pad; periodic over dur."""
    sr = audio.SR
    n = int(round(dur * sr))
    out = np.zeros(n)
    L = int(0.35 * sr)
    tt = np.arange(L) / sr

    def kick(t0, g):
        f = 52 * (1 + 2.2 * np.exp(-tt * 28))
        ph = 2 * np.pi * np.cumsum(f) / sr
        env = (1 - np.exp(-tt * 600)) * np.exp(-tt * 9)
        sig = np.sin(ph) * env + 0.25 * np.sin(2 * ph) * env * np.exp(-tt * 20)
        idx = (np.arange(L) + int(round(t0 * sr))) % n
        np.add.at(out, idx, g * sig)

    for st in STARTS:
        kick(st + T_TEASE, 0.55)
    kick(0.0, 0.8)                                         # frame 0: the hook hit
    kick(T_RUN + T_TEASE, 0.8)                             # LEVEL MAX
    pad = kit.loop_pad(dur, ((50, 1.0), (57, 0.7), (62, 0.45), (66, 0.3)), gain=0.014)
    return (0.5 * out + pad[:n]).astype(np.float32)


def _worker(o, sim, label, rule):
    layout = get_layout(o)
    name = f"{SCENE}_{label}_{layout.tag}"
    video = studio.OUT_DIR / f"{name}_silent.mp4"
    d = render(layout, sim, video, rule)
    pad = hardtekk_bed(V_LEN) if BEAT == "hardtekk" else beat_bed(V_LEN) if HOOK else kit.loop_pad(T_LOOP, ((50, 1.0), (57, 0.7), (62, 0.45), (66, 0.3)), gain=0.014)
    kit.deliver_loop(SCENE, name, layout, video, build_events(sim, layout), d, voice="glassharp", bed=pad,
                     peak_db=-6.0 if HOOK else None)


def main():
    label, rule = arg("--label", "v1"), arg("--rule", "")
    studio.OUT_DIR.mkdir(exist_ok=True)
    sim = simulate()
    if kit.has("--still"):
        layout = get_layout(kit.orients()[0])
        f = int(arg("--frame", "300"))
        png = studio.OUT_DIR / f"{SCENE}_{label}_f{f}_{layout.tag}.png"
        render(layout, sim, png, rule, still_frame=f)
        print(f"[{SCENE}] -> {png}")
        return
    print(f"[{SCENE}] {T_LOOP:.2f}s, {N_LV} levels + MAX at {T_RUN:.2f}s")
    kit.fan_out(_worker, (sim, label, rule), SCENE)


if __name__ == "__main__":
    main()
