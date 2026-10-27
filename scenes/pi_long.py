"""PI LONG — "Two blocks that compute π": the π blocks long-form (16:9, ~8:15).

Brief: ideas/2026-10-26_pi_blocks_LONGFORM_PROMPT.txt. Owner: 8-10 min, and NO long counting: every dense burst of
collisions lasts 2-4 s (fast counter, a ring of dots that fills, a harp strum); the minutes go into the setup, the WHY
and an escalation of real objects.
Chapters: cold open (10⁶ kg: 3,141) · setup + equal masses (3) · 100 kg (31, a π melody) · 10,000 kg (314) ·
WHY π (energy circle, momentum lines, equal angles 2θ, 180° ÷ θ) · the pizza slice (unfolded path crossing π/θ wedges) ·
other masses are not π (16 kg: 12, 1,000 kg: 99) · the ladder of real objects up to 10²⁴ kg (⅙ of the Earth) ·
the punch: 10⁵² kg (a tenth of the universe's matter) = 27 digits; computers know 100+ trillion · recap.
Counts: exact event-driven simulation up to 10⁶ kg (scenes/pi_blocks.simulate_round); above, the exact formula
N = ⌈π/θ⌉ − 1, θ = arctan(√(m/M)) (mpmath; it matches every simulated count). Galperin 2003 credited.
Audio (original, lib/sfx): marimba π digits on slow rounds, harp strums on bursts, a pad per chapter, whooshes and hits.
"""
import bisect
import math
import sys
from pathlib import Path

import cairo
import mpmath
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib import kit, sfx, studio  # noqa: E402
from lib.kit import DT, FPS, arg, smooth  # noqa: E402
from lib.layouts import get_layout  # noqa: E402
from lib.studio import Canvas, VideoWriter  # noqa: E402
from scenes.pi_blocks import S1, simulate_round  # noqa: E402

SCENE = "pi_long"
CYAN, GOLD, PINK, WHITE, SOFT = (0.35, 0.85, 1.0), (1.0, 0.8, 0.3), (1.0, 0.45, 0.6), (0.96, 0.97, 1.0), (0.75, 0.78, 0.92)
LIME, RED = (0.55, 1.0, 0.55), (1.0, 0.4, 0.4)
PI_STR = "3.14159265358979323846264338327950288419716939937510"
PI_DIG = PI_STR.replace(".", "")
mpmath.mp.dps = 80


def n_hits(M):
    Mm = mpmath.mpf(repr(M)) if isinstance(M, float) else mpmath.mpf(M)     # exact decimal, not the float
    th = mpmath.atan(mpmath.sqrt(mpmath.mpf(1) / Mm))
    return int(mpmath.ceil(mpmath.pi / th)) - 1


def lbs(M):
    """US first: a mass in kg written in pounds (2 significant figures), e.g. 220 lb, 2.2 million lb, 2.2 × 10²⁴ lb."""
    v = float(f"{M * 2.20462:.2g}")
    if v < 10:
        return f"{v:.1f} lb"
    if v < 1e6:
        return f"{v:,.0f} lb"
    for div, word in ((1e12, "trillion"), (1e9, "billion"), (1e6, "million")):
        if v >= div and v < 1e15:
            return f"{v / div:.3g} {word} lb"
    e = int(math.floor(math.log10(v)))
    return f"{v / 10 ** e:.2g} × 10{sup(e)} lb"


def kgs(M):
    return f"{M:,.0f} kg" if M < 1e7 else f"10{sup(int(round(math.log10(M))))} kg"


def us(M):
    """'220 lb (100 kg)': pounds for the US audience, kg in parentheses for everyone else."""
    return f"{lbs(M)} ({kgs(M)})"


def theta(M):
    return math.atan(1 / math.sqrt(M))


CHAPTERS = [("intro", 16), ("setup", 38), ("c100", 22), ("c1e4", 20), ("ladder", 3 * 25), ("why", 66),
            ("other", 16), ("ladder2", 7 * 25), ("punch", 36), ("recap", 26)]
RING_COLS = [(1.0, 0.8, 0.3), (0.45, 0.85, 1.0), (1.0, 0.6, 0.35), (0.55, 1.0, 0.6), (0.75, 0.6, 1.0),
             (0.35, 0.75, 1.0), (1.0, 0.85, 0.7), (0.5, 0.85, 1.0), (1.0, 0.7, 0.3), (0.95, 0.6, 0.95)]
T0, _acc = {}, 0.0
for _k, _d in CHAPTERS:
    T0[_k] = _acc
    _acc += _d
T_END = _acc
ORDER = [k for k, _ in CHAPTERS]
OBJ_T = 25.0                                                    # seconds per object in the ladder
# (M kg, drawing, NAME, mass line, quote before the burst, quote after)
LADDER = [
    (1e6, "train", "A FREIGHT TRAIN", "2.2 million lb (1,000 t)", "As heavy as 700 cars.",
     "From here on, the count comes from an exact formula."),
    (1e8, "ship", "AN AIRCRAFT CARRIER", "220 million lb (100,000 t)", "The biggest warships ever built.",
     "Every ×100 heavier adds exactly one digit."),
    (1e10, "pyramid", "TWO GREAT PYRAMIDS", "22 billion lb (10 million t)", "Each one is about 6.6 million tons of stone.",
     "Built in about 20 years. Counted here in 3 seconds."),
    (1e12, "crowd", "EVERY HUMAN ON EARTH, TWICE", "2.2 trillion lb (10¹² kg)", "8 billion people weigh about half of this.",
     "All of us, twice, against one 2.2 lb block."),
    (1e14, "mountain", "MOUNT EVEREST", "≈ 220 trillion lb (10¹⁴ kg)", "The whole mountain: rock, ice and snow.",
     "Eight digits of π from a mountain."),
    (1e16, "lake", "LAKE SUPERIOR", "≈ 2.2 × 10¹⁶ lb of water (10¹⁶ kg)", "The largest freshwater lake on Earth by area.",
     "Over 300 million collisions."),
    (1e22, "pluto", "PLUTO", "≈ 2.2 × 10²² lb (10²² kg)", "A whole dwarf planet: 2.9 × 10²² lb.",
     "A whole world, pushing a 2.2 lb block."),
    (1e24, "earth", "1/6 OF THE EARTH", "2.2 × 10²⁴ lb (10²⁴ kg)", "The Earth weighs 1.3 × 10²⁵ lb (6 × 10²⁴ kg).",
     "Three trillion collisions."),
    (1e30, "sun", "HALF THE SUN", "2.2 × 10³⁰ lb (10³⁰ kg)", "The Sun weighs as much as 333,000 Earths.",
     "Sixteen digits of π from half a star."),
    (1e42, "galaxy", "A THIRD OF THE MILKY WAY", "≈ 2.2 × 10⁴² lb (10⁴² kg)", "Our galaxy: ≈ 6.6 × 10⁴² lb, dark matter included.",
     "Twenty-two digits… and still not a whole galaxy."),
]
LADDER_N = [n_hits(M) for M, *_ in LADDER]
UNIVERSE_N = n_hits(mpmath.mpf(10) ** 52)
SIMS = {M: simulate_round(M) for M in (1.0, 16.0, 100.0, 1e4)}


def sup(n):
    return "".join("⁰¹²³⁴⁵⁶⁷⁸⁹"[int(d)] for d in str(n))


def clamp(v, a=0.0, b=1.0):
    return max(a, min(b, v))


def seg(u, a, b):
    return clamp((u - a) / (b - a))


class Playback:
    """an exact simulated round, with the collisions put on a chosen time grid (video seconds from the round start)."""

    def __init__(self, M, hit_times, intro=0.4):
        self.ev = SIMS[M]
        self.hv = list(hit_times)
        self.intro = intro
        self.hs = [e[0] for e in self.ev]

    def at(self, tr):
        hv = [0.0] + self.hv
        hs = self.hs
        if tr < self.intro:
            ts = 0.0
        elif tr < hv[1]:
            ts = hs[1] * (tr - self.intro) / (hv[1] - self.intro)
        else:
            k = bisect.bisect_right(hv, tr) - 1
            if k + 1 < len(hv):
                ts = hs[k] + (hs[k + 1] - hs[k]) * (tr - hv[k]) / (hv[k + 1] - hv[k])
            else:
                rate = (hs[-1] - hs[1]) / max(1e-6, hv[-1] - hv[1]) * 1.4 + 0.4
                ts = hs[-1] + (tr - hv[-1]) * rate
        j = bisect.bisect_right(hs, ts) - 1
        t0, x1, v1, x2, v2, _ = self.ev[j]
        d = ts - t0
        played = bisect.bisect_right(self.hv, tr)
        return x1 + v1 * d, x2 + v2 * d, played, (v1, v2, j)


def even_hits(n, start, dur):
    return [start + dur * (k + 1) / n for k in range(n)]


PB_SETUP = Playback(1.0, [11.0, 14.5, 18.0], intro=8.5)
PB_100 = Playback(100.0, even_hits(31, 2.2, 6.4), intro=1.6)
PB_WHY = Playback(100.0, even_hits(31, 25.0, 11.0), intro=24.0)
PB_16 = Playback(16.0, even_hits(12, 3.0, 3.6), intro=2.2)


class Scene:
    def __init__(self, layout):
        self.L = layout
        self.canvas = Canvas(layout.w, layout.h, studio.render_scale())

    # ------------------------------------------------------------- pieces
    def bg(self):
        c, w, h = self.canvas, self.L.w, self.L.h
        g = cairo.RadialGradient(w * 0.5, h * 0.45, 0, w * 0.5, h * 0.45, w * 0.7)
        g.add_color_stop_rgb(0, 0.06, 0.06, 0.11)
        g.add_color_stop_rgb(1, 0.005, 0.005, 0.015)
        c.ctx.set_source(g)
        c.ctx.paint()

    def head(self, s, sub=None, a=1.0, col=WHITE):
        c, w, h = self.canvas, self.L.w, self.L.h
        c.text_centered(s, h * 0.135, size=h * 0.056, color=col, alpha=a, max_w=w * 0.92)
        if sub:
            c.text_centered(sub, h * 0.185, size=h * 0.03, color=SOFT, alpha=a, bold=False, max_w=w * 0.9)

    def bottom(self, s, a=1.0, col=GOLD):
        c, w, h = self.canvas, self.L.w, self.L.h
        c.text_centered(s, h * 0.935, size=h * 0.036, color=col, alpha=a, max_w=w * 0.92)

    def icon(self, kind, x, y, s, col=(0.12, 0.08, 0.02)):
        """a simple dark silhouette inside the big block (centre x, y; size s)."""
        c = self.canvas
        ctx = c.ctx
        if kind == "person":
            c.circle(x, y - s * 0.28, s * 0.1, col)
            c.lines([(x, y - s * 0.18, x, y + s * 0.1), (x, y + s * 0.1, x - s * 0.12, y + s * 0.32),
                     (x, y + s * 0.1, x + s * 0.12, y + s * 0.32), (x, y - s * 0.1, x - s * 0.14, y + s * 0.05),
                     (x, y - s * 0.1, x + s * 0.14, y + s * 0.05)], col, width=s * 0.05)
        elif kind == "truck":
            ctx.rectangle(x - s * 0.35, y - s * 0.15, s * 0.45, s * 0.3)
            ctx.rectangle(x + s * 0.12, y - s * 0.02, s * 0.22, s * 0.17)
            ctx.set_source_rgb(*col)
            ctx.fill()
            for dx in (-0.22, 0.0, 0.24):
                c.circle(x + dx * s, y + s * 0.2, s * 0.07, col)
        elif kind == "train":
            ctx.rectangle(x - s * 0.38, y - s * 0.12, s * 0.76, s * 0.24)
            ctx.rectangle(x + s * 0.12, y - s * 0.28, s * 0.18, s * 0.16)
            ctx.set_source_rgb(*col)
            ctx.fill()
            for dx in (-0.28, -0.1, 0.08, 0.26):
                c.circle(x + dx * s, y + s * 0.16, s * 0.06, col)
        elif kind == "ship":
            c.poly([(x - s * 0.42, y), (x + s * 0.42, y), (x + s * 0.32, y + s * 0.16), (x - s * 0.36, y + s * 0.16)], col)
            ctx.rectangle(x + s * 0.08, y - s * 0.22, s * 0.12, s * 0.22)
            ctx.set_source_rgb(*col)
            ctx.fill()
        elif kind == "pyramid":
            c.poly([(x - s * 0.4, y + s * 0.25), (x, y - s * 0.3), (x + s * 0.4, y + s * 0.25)], col)
        elif kind == "crowd":
            for k in range(18):
                cx_ = x + ((k % 6) - 2.5) * s * 0.13
                cy_ = y + ((k // 6) - 1) * s * 0.16
                c.circle(cx_, cy_ - s * 0.04, s * 0.04, col)
                c.lines([(cx_, cy_, cx_, cy_ + s * 0.07)], col, width=s * 0.03)
        elif kind == "mountain":
            c.poly([(x - s * 0.42, y + s * 0.28), (x - s * 0.05, y - s * 0.3), (x + s * 0.15, y - s * 0.05),
                    (x + s * 0.25, y - s * 0.18), (x + s * 0.42, y + s * 0.28)], col)
        elif kind == "planet":
            c.circle(x, y, s * 0.33, col)
            c.ring(x, y, s * 0.33, (0.3, 0.2, 0.05), width=s * 0.02)
        elif kind == "galaxy":
            for k in range(60):
                a = k * 0.5
                rr = s * 0.04 * a ** 0.8
                for arm in (0, math.pi):
                    c.circle(x + math.cos(a + arm) * rr, y + math.sin(a + arm) * rr * 0.6, s * 0.012, col)
        elif kind == "M":
            c.text_centered("M", y + s * 0.15, size=s * 0.45, color=col, cx=x)

    def progress_row(self, t):
        """10 object icons across the top: grey with '?' until that object's count lands, then lit with a gold rim."""
        c, w, h = self.canvas, self.L.w, self.L.h
        n = len(LADDER)
        x0, x1, y, S = w * 0.04, w * 0.96, h * 0.035, h * 0.045
        for i, (M_, kind, *_r) in enumerate(LADDER):
            base = T0["ladder"] + i * OBJ_T if i < 3 else T0["ladder2"] + (i - 3) * OBJ_T
            done_t = base + 10.5
            cur = base <= t < base + OBJ_T
            done = t >= done_t
            x = x0 + (x1 - x0) * (i + 0.5) / n
            if cur:
                c.glow(x, y, S * 0.9, (0.4, 0.6, 1.0), strength=0.35, reach=1.6)
            self.draw_object(kind, x, y, S, a=1.0 if done else 0.28)
            if done:
                pop = math.exp(-(t - done_t) / 0.2)
                c.ring(x, y, S * (0.62 + 0.25 * pop), GOLD, width=2.5, alpha=0.9)
            else:
                c.text_centered("?", y + S * 0.25, size=S * 0.7, color=WHITE, cx=x, alpha=0.75)

    def draw_object(self, kind, x, y, S, a=1.0):
        """a colourful flat illustration that fits a box of size S centred on (x, y)."""
        c = self.canvas
        ctx = c.ctx
        if a < 0.999:
            ctx.push_group()

        def rect(x0, y0, x1, y1, col):
            ctx.rectangle(x + x0 * S, y + y0 * S, (x1 - x0) * S, (y1 - y0) * S)
            ctx.set_source_rgb(*col)
            ctx.fill()

        def poly(pts, col):
            c.poly([(x + px * S, y + py * S) for px, py in pts], col)

        def disc(px, py, r, col, al=1.0):
            c.circle(x + px * S, y + py * S, r * S, col, alpha=al)

        def sphere(r, c0, c1):
            g = cairo.RadialGradient(x - r * S * 0.35, y - r * S * 0.35, r * S * 0.05, x, y, r * S)
            g.add_color_stop_rgb(0, *c0)
            g.add_color_stop_rgb(1, *c1)
            ctx.new_path()
            ctx.arc(x, y, r * S, 0, 2 * math.pi)
            ctx.set_source(g)
            ctx.fill()

        if kind == "person":
            disc(0, -0.3, 0.09, (0.98, 0.85, 0.7))
            rect(-0.1, -0.2, 0.1, 0.12, (0.3, 0.6, 1.0))
            rect(-0.1, 0.12, -0.02, 0.38, (0.2, 0.25, 0.45))
            rect(0.02, 0.12, 0.1, 0.38, (0.2, 0.25, 0.45))
            rect(-0.16, -0.18, -0.1, 0.08, (0.98, 0.85, 0.7))
            rect(0.1, -0.18, 0.16, 0.08, (0.98, 0.85, 0.7))
        elif kind == "truck":
            rect(-0.46, -0.2, 0.12, 0.16, (0.8, 0.82, 0.88))
            rect(0.14, -0.08, 0.44, 0.16, (0.9, 0.25, 0.25))
            rect(0.3, -0.04, 0.4, 0.04, (0.6, 0.85, 1.0))
            for px in (-0.34, -0.1, 0.3):
                disc(px, 0.2, 0.07, (0.1, 0.1, 0.12))
                disc(px, 0.2, 0.03, (0.6, 0.6, 0.65))
        elif kind == "train":
            c.lines([(x - 0.5 * S, y + 0.3 * S, x + 0.5 * S, y + 0.3 * S)], (0.6, 0.6, 0.65), width=max(1.5, S * 0.02))
            rect(-0.5, 0.0, -0.24, 0.24, (0.25, 0.55, 0.9))
            rect(-0.21, 0.0, 0.05, 0.24, (0.3, 0.75, 0.45))
            rect(0.08, -0.02, 0.48, 0.24, (0.9, 0.22, 0.22))
            rect(0.3, -0.18, 0.46, -0.02, (0.65, 0.12, 0.12))
            rect(0.34, -0.14, 0.42, -0.06, (1.0, 0.85, 0.4))
            rect(0.12, -0.12, 0.18, -0.02, (0.35, 0.35, 0.4))
            for k_ in range(3):
                disc(0.15 + 0.03 * k_, -0.18 - 0.08 * k_, 0.04 + 0.02 * k_, (0.85, 0.85, 0.9), al=0.55)
            for px in (-0.44, -0.3, -0.15, -0.01, 0.16, 0.3, 0.42):
                disc(px, 0.26, 0.045, (0.12, 0.12, 0.14))
        elif kind == "ship":
            g = cairo.LinearGradient(0, y + 0.12 * S, 0, y + 0.45 * S)
            g.add_color_stop_rgb(0, 0.15, 0.45, 0.85)
            g.add_color_stop_rgb(1, 0.05, 0.18, 0.4)
            ctx.rectangle(x - 0.5 * S, y + 0.12 * S, S, 0.33 * S)
            ctx.set_source(g)
            ctx.fill()
            poly([(-0.48, -0.02), (0.48, -0.02), (0.38, 0.16), (-0.42, 0.16)], (0.5, 0.53, 0.6))
            rect(-0.47, -0.07, 0.47, -0.01, (0.28, 0.3, 0.36))
            c.lines([(x - 0.4 * S, y - 0.04 * S, x + 0.4 * S, y - 0.04 * S)], (0.95, 0.95, 0.95), width=max(1.0, S * 0.008))
            rect(0.16, -0.26, 0.26, -0.07, (0.55, 0.58, 0.65))
            rect(0.2, -0.36, 0.215, -0.26, (0.7, 0.72, 0.78))
            for px in (-0.35, -0.2, -0.05):
                poly([(px, -0.12), (px + 0.07, -0.08), (px, -0.08)], (0.92, 0.92, 0.96))
            for k_ in range(4):
                c.lines([(x + (-0.45 + 0.25 * k_) * S, y + 0.25 * S, x + (-0.35 + 0.25 * k_) * S, y + 0.25 * S)],
                        (0.6, 0.85, 1.0), width=max(1.0, S * 0.01), alpha=0.6)
        elif kind == "pyramid":
            disc(-0.32, -0.3, 0.09, (1.0, 0.85, 0.35))
            rect(-0.5, 0.3, 0.5, 0.45, (0.85, 0.68, 0.4))
            poly([(-0.45, 0.3), (-0.2, 0.0), (0.05, 0.3)], (0.85, 0.7, 0.45))
            poly([(-0.2, 0.0), (0.05, 0.3), (-0.08, 0.3)], (0.66, 0.5, 0.28))
            poly([(-0.25, 0.3), (0.12, -0.24), (0.49, 0.3)], (0.98, 0.8, 0.48))
            poly([(0.12, -0.24), (0.49, 0.3), (0.28, 0.3)], (0.72, 0.52, 0.27))
        elif kind == "crowd":
            cols = [(0.95, 0.4, 0.4), (0.4, 0.7, 1.0), (0.5, 0.9, 0.5), (1.0, 0.8, 0.35), (0.8, 0.55, 1.0), (1.0, 0.6, 0.8)]
            for r_ in range(6):
                for q in range(9):
                    px, py = -0.4 + q * 0.1 + (0.05 if r_ % 2 else 0), -0.3 + r_ * 0.12
                    disc(px, py - 0.035, 0.022, (0.98, 0.85, 0.7))
                    rect(px - 0.022, py - 0.012, px + 0.022, py + 0.045, cols[(r_ * 9 + q) % 6])
        elif kind == "mountain":
            poly([(-0.5, 0.35), (-0.28, -0.05), (-0.1, 0.35)], (0.35, 0.42, 0.6))
            poly([(-0.4, 0.35), (0.0, -0.38), (0.22, -0.12), (0.32, -0.2), (0.5, 0.35)], (0.5, 0.55, 0.7))
            poly([(0.0, -0.38), (0.5, 0.35), (0.2, 0.35)], (0.38, 0.42, 0.58))
            poly([(-0.1, -0.2), (0.0, -0.38), (0.12, -0.22), (0.05, -0.16), (-0.02, -0.22)], (0.97, 0.98, 1.0))
            poly([(0.27, -0.13), (0.32, -0.2), (0.37, -0.12)], (0.97, 0.98, 1.0))
        elif kind == "lake":
            rect(-0.5, -0.35, 0.5, 0.35, (0.2, 0.5, 0.28))
            ctx.save()
            ctx.translate(x, y)
            ctx.scale(S * 0.42, S * 0.26)
            ctx.arc(0, 0, 1, 0, 2 * math.pi)
            ctx.restore()
            g = cairo.RadialGradient(x, y, 0, x, y, S * 0.42)
            g.add_color_stop_rgb(0, 0.3, 0.65, 1.0)
            g.add_color_stop_rgb(1, 0.1, 0.35, 0.75)
            ctx.set_source(g)
            ctx.fill()
            for k_ in range(3):
                ctx.save()
                ctx.translate(x - 0.08 * S, y)
                ctx.scale(S * (0.1 + 0.08 * k_), S * (0.05 + 0.04 * k_))
                ctx.arc(0, 0, 1, 0.3, 2.6)
                ctx.restore()
                ctx.set_source_rgba(0.8, 0.95, 1.0, 0.5)
                ctx.set_line_width(max(1.0, S * 0.008))
                ctx.stroke()
            for px, py in ((-0.42, -0.28), (-0.3, -0.3), (0.38, 0.27), (0.44, -0.27), (-0.44, 0.26)):
                poly([(px - 0.04, py + 0.05), (px, py - 0.06), (px + 0.04, py + 0.05)], (0.08, 0.32, 0.15))
        elif kind == "pluto":
            sphere(0.42, (0.92, 0.84, 0.7), (0.45, 0.36, 0.27))
            ctx.save()
            ctx.new_path()
            ctx.arc(x, y, 0.42 * S, 0, 2 * math.pi)
            ctx.clip()
            disc(0.02, 0.05, 0.11, (0.98, 0.95, 0.88))
            disc(0.2, 0.05, 0.11, (0.98, 0.95, 0.88))
            poly([(-0.08, 0.09), (0.3, 0.09), (0.11, 0.32)], (0.98, 0.95, 0.88))
            disc(-0.22, -0.18, 0.08, (0.55, 0.42, 0.32), al=0.6)
            ctx.restore()
        elif kind == "earth":
            c.glow(x, y, 0.45 * S, (0.4, 0.75, 1.0), strength=0.45, reach=1.4)
            sphere(0.42, (0.35, 0.65, 1.0), (0.05, 0.2, 0.5))
            ctx.save()
            ctx.new_path()
            ctx.arc(x, y, 0.42 * S, 0, 2 * math.pi)
            ctx.clip()
            for px, py, r_ in ((-0.15, -0.12, 0.16), (0.02, -0.2, 0.1), (0.18, 0.1, 0.13), (-0.05, 0.22, 0.08),
                               (0.26, -0.12, 0.07)):
                disc(px, py, r_, (0.3, 0.75, 0.4))
            for px, py in ((-0.25, 0.05), (0.1, -0.02), (0.05, 0.3)):
                rect(px - 0.12, py - 0.012, px + 0.12, py + 0.012, (0.95, 0.97, 1.0))
            ctx.restore()
        elif kind == "sun":
            c.glow(x, y, 0.5 * S, (1.0, 0.65, 0.2), strength=0.8, reach=1.6)
            for k_ in range(16):
                aa = k_ / 16 * 2 * math.pi
                c.lines([(x + math.cos(aa) * 0.38 * S, y + math.sin(aa) * 0.38 * S, x + math.cos(aa) * 0.5 * S,
                          y + math.sin(aa) * 0.5 * S)], (1.0, 0.75, 0.3), width=max(1.5, S * 0.02), alpha=0.8)
            sphere(0.36, (1.0, 0.97, 0.7), (1.0, 0.55, 0.12))
        elif kind == "galaxy":
            c.glow(x, y, 0.2 * S, (1.0, 0.9, 0.7), strength=0.9, reach=2.2)
            for k_ in range(220):
                tt = k_ / 220 * 3.2
                rr = 0.04 + 0.13 * tt
                for arm in (0, math.pi):
                    aa = tt * 1.9 + arm
                    jit = ((k_ * 37) % 11 - 5) * 0.006
                    px = math.cos(aa) * rr + jit
                    py = (math.sin(aa) * rr + jit) * 0.55
                    col = [(1.0, 1.0, 1.0), (0.7, 0.8, 1.0), (1.0, 0.7, 0.9)][k_ % 3]
                    disc(px, py, 0.007 + 0.006 * (1 - tt / 3.2), col, al=0.85)
        elif kind == "universe":
            rng = np.random.default_rng(4)
            pts = [(rng.uniform(-0.45, 0.45), rng.uniform(-0.45, 0.45)) for _ in range(70)]
            for i_, (px, py) in enumerate(pts):
                for qx, qy in pts[i_ + 1:i_ + 5]:
                    if math.hypot(px - qx, py - qy) < 0.2:
                        c.lines([(x + px * S, y + py * S, x + qx * S, y + qy * S)], (0.6, 0.45, 1.0),
                                width=max(1.0, S * 0.006), alpha=0.6)
                disc(px, py, 0.01, (0.9, 0.85, 1.0))
        if a < 0.999:
            ctx.pop_group_to_source()
            ctx.paint_with_alpha(a)

    def quote(self, s, y, a=1.0, col=WHITE):
        """a quote card: “…” on a dark rounded strip."""
        c, w, h = self.canvas, self.L.w, self.L.h
        ctx = c.ctx
        if a <= 0.01:
            return
        txt = f"“{s}”"
        size = h * 0.04
        c._font(size, True)
        tw = min(w * 0.9, ctx.text_extents(txt).x_advance)
        x0, y0, bw, bh = w / 2 - tw / 2 - h * 0.03, y - size * 1.05, tw + h * 0.06, size * 1.6
        r = bh * 0.3
        ctx.new_path()
        ctx.arc(x0 + bw - r, y0 + r, r, -math.pi / 2, 0)
        ctx.arc(x0 + bw - r, y0 + bh - r, r, 0, math.pi / 2)
        ctx.arc(x0 + r, y0 + bh - r, r, math.pi / 2, math.pi)
        ctx.arc(x0 + r, y0 + r, r, math.pi, 1.5 * math.pi)
        ctx.close_path()
        ctx.set_source_rgba(0.1, 0.1, 0.2, 0.85 * a)
        ctx.fill_preserve()
        ctx.set_source_rgba(*GOLD, 0.7 * a)
        ctx.set_line_width(2)
        ctx.stroke()
        c.text_centered(txt, y, size=size, color=col, alpha=a, max_w=w * 0.9)

    def stage(self, x1, x2, M, icon="M", flash=0.0, flash_x=None, area=(0.04, 0.58), fy=0.80, label=True):
        """wall + floor + the two blocks (x in track units 0..1)."""
        c, w, h = self.canvas, self.L.w, self.L.h
        ctx = c.ctx
        wx, x_end = w * area[0], w * area[1]
        TW = x_end - wx
        fy_ = h * fy
        c.lines([(wx, fy_ - h * 0.28, wx, fy_)], (0.85, 0.88, 1.0), width=5)
        hatch = [(wx - w * 0.015, fy_ - h * 0.28 + j * h * 0.022, wx, fy_ - h * 0.28 + j * h * 0.022 - h * 0.018)
                 for j in range(13)]
        c.lines(hatch, (0.6, 0.65, 0.8), width=2, alpha=0.6)
        c.lines([(wx, fy_, x_end + w * 0.02, fy_)], (0.85, 0.88, 1.0), width=4)
        s_small = S1 * TW * 0.9
        s_big = min(h * 0.24, s_small * (1 + 0.35 * math.log10(max(1.0, M)))) if M > 1 else s_small
        if icon not in ("M",) and M > 1:
            s_big = max(s_big, h * 0.17)
        s_big = min(s_big, w * 0.30)                                # vertical layouts (16:9: no change)
        bx1, bx2 = wx + x1 * TW, wx + x2 * TW
        ctx.rectangle(bx1, fy_ - s_small, s_small, s_small)
        ctx.set_source_rgb(*CYAN)
        ctx.fill()
        c.text_centered("m", fy_ - s_small * 0.32, size=s_small * 0.5, color=(0.02, 0.05, 0.1), cx=bx1 + s_small / 2)
        if bx2 < w * 1.1:
            if icon == "M":
                ctx.rectangle(bx2, fy_ - s_big, s_big, s_big)
                ctx.set_source_rgb(*GOLD)
                ctx.fill()
                self.icon(icon, bx2 + s_big / 2, fy_ - s_big / 2, s_big)
            else:
                rr = s_big * 0.08
                ctx.new_path()
                ctx.arc(bx2 + s_big - rr, fy_ - s_big + rr, rr, -math.pi / 2, 0)
                ctx.arc(bx2 + s_big - rr, fy_ - rr, rr, 0, math.pi / 2)
                ctx.arc(bx2 + rr, fy_ - rr, rr, math.pi / 2, math.pi)
                ctx.arc(bx2 + rr, fy_ - s_big + rr, rr, math.pi, 1.5 * math.pi)
                ctx.close_path()
                ctx.set_source_rgb(0.07, 0.07, 0.13)
                ctx.fill_preserve()
                ctx.set_source_rgb(*GOLD)
                ctx.set_line_width(max(2.0, s_big * 0.03))
                ctx.stroke()
                ctx.save()
                ctx.rectangle(bx2, fy_ - s_big, s_big, s_big)
                ctx.clip()
                self.draw_object(icon, bx2 + s_big / 2, fy_ - s_big / 2, s_big * 0.86)
                ctx.restore()
        if flash > 0.01:
            xx = flash_x if flash_x is not None else bx1 + s_small
            c.glow(xx, fy_ - s_small / 2, w * 0.02, WHITE, strength=0.8 * flash, reach=2)
        if label:
            c.text_centered(f"m = {us(1.0)}", fy_ + h * 0.04, size=h * 0.024, color=CYAN, bold=False, cx=wx + TW * 0.17,
                            max_w=TW * 0.36)
            c.text_centered(f"M = {us(M)}", fy_ + h * 0.04, size=h * 0.028, color=GOLD, cx=wx + TW * 0.68,
                            max_w=TW * 0.6)
        return bx1, bx2, s_small, s_big, fy_

    def burst_stage(self, u, M, icon, area=(0.04, 0.58)):
        """a stylised dense burst for heavy blocks: M slides in, pins m against the wall (m a blur), turns back."""
        x2 = 0.62 - 0.52 * math.sin(math.pi * clamp(u)) if u < 1 else 0.62
        x2 = max(x2, S1 * 1.05)
        gap = max(0.0, x2 - S1)
        x1 = gap * abs(math.sin(u * 140)) if 0.05 < u < 0.95 else (0.0 if u <= 0.05 else gap * 0.5)
        fl = 0.6 + 0.4 * math.sin(u * 90) if 0.05 < u < 0.95 else 0.0
        return self.stage(x1, x2, M, icon, flash=fl, area=area)

    def ring(self, cx, cy, R, frac, n_total, col=None, done_glow=0.0):
        c = self.canvas
        col = col or getattr(self, "ring_col", GOLD)
        nd = 300
        c.ring(cx, cy, R, (0.5, 0.55, 0.8), width=2, alpha=0.3)
        k = int(nd * clamp(frac))
        for i in range(k):
            a = -math.pi / 2 + 2 * math.pi * i / nd
            d = int(PI_DIG[i % len(PI_DIG)])
            cc = [(1.0, 0.45, 0.5), (1.0, 0.62, 0.35), GOLD, (0.75, 1.0, 0.45), LIME, CYAN, (0.45, 0.65, 1.0),
                  (0.65, 0.5, 1.0), (0.9, 0.5, 1.0), (1.0, 0.5, 0.8)][d]
            c.circle(cx + R * math.cos(a), cy + R * math.sin(a), R * 0.025, cc)
        if done_glow > 0:
            c.glow(cx, cy, R * 1.1, col, strength=0.4 * done_glow, reach=1.6)
            c.ring(cx, cy, R, col, width=5, alpha=done_glow)

    def count_text(self, n, cx, cy, size, col=WHITE, pop=0.0, max_w=None):
        c = self.canvas
        c.text_centered(f"{n:,}", cy, size=size * (1 + 0.25 * pop), color=col, cx=cx,
                        max_w=max_w if max_w else self.L.w * 0.42)

    def pi_line(self, k_digits, cx, y, size, a=1.0):
        s = PI_STR[:k_digits + (1 if k_digits > 1 else 0)]
        self.canvas.text_centered(f"π = {s}…", y, size=size, color=GOLD, alpha=a, cx=cx, max_w=self.L.w * 0.36)

    def burst_panel(self, u, N, digits, cx, cy, R, label=True):
        """ring + rolling count + the π digits once done. u: 0..1 the burst, >1 done."""
        frac = 0.5 - 0.5 * math.cos(math.pi * clamp(u))
        n = int(round(N * frac)) if u < 1 else N
        done = u >= 1
        pop = math.exp(-(u - 1) * 8) if done else 0.0
        self.ring(cx, cy, R, frac, N, done_glow=clamp((u - 1) * 3) if done else 0.0)
        self.count_text(n, cx, cy + R * 0.12, R * 0.42 if N < 1e7 else R * 0.24, GOLD if done else WHITE, pop,
                        max_w=R * 1.75)
        if label:
            self.canvas.text_centered("collisions", cy + R * 0.38, size=R * 0.14, color=SOFT, bold=False, cx=cx)
        if done:
            self.pi_line(digits, cx, cy + R * 1.38, R * 0.26, a=clamp((u - 1) * 3))

    # ------------------------------------------------------------- chapters
    def ch_intro(self, t, u):
        w, h = self.L.w, self.L.h
        if u < 2.6:                                                # the promise
            a = clamp(u / 0.4) * clamp((2.6 - u) / 0.4)
            self.draw_object("universe", w * 0.5, h * 0.55, h * 0.6, a=a)
            self.head("Before the end, this block will weigh", "a TENTH of the whole UNIVERSE", a=a, col=GOLD)
            return
        u = u - 2.4
        bu = (u - 0.8) / 3.0
        self.burst_stage(clamp(bu) if bu < 1 else 1.0, 1e6, "train")
        self.burst_panel(bu if bu > 0 else 0, 3141, 4, w * 0.78, h * 0.47, h * 0.19)
        if u < 4.4:
            self.head("A block 1,000,000× heavier hits a small block…", f"{us(1e6)} vs {us(1.0)} · no friction")
        elif u < 8.0:
            self.head("3,141 collisions.", "…3.141?", col=GOLD)
        else:
            a = clamp((u - 8.0) / 0.5)
            self.head("TWO BLOCKS THAT COMPUTE π", "the full story, from 3 collisions to a tenth of the universe", a=a,
                      col=GOLD)

    def ch_setup(self, t, u):
        c, w, h = self.canvas, self.L.w, self.L.h
        x1, x2, n, _ = PB_SETUP.at(u)
        fl = 0.0
        for ht in PB_SETUP.hv:
            if 0 <= u - ht < 0.25:
                fl = 1 - (u - ht) / 0.25
        bx1, bx2, ss, sb, fy = self.stage(x1, x2, 1.0, "M", flash=fl)
        for k, ht in enumerate(PB_SETUP.hv):                       # numbered hits
            if u >= ht:
                a = clamp(1 - (u - ht - 2.5) / 0.5) if u < 24 else clamp((26 - u) / 0.5)
                if a > 0:
                    kind = SIMS[1.0][k + 1][5]
                    xx = w * 0.04 if kind == "wall" else bx1 + ss
                    c.text_centered(str(k + 1), fy - h * 0.14 - k * h * 0.02, size=h * 0.07, color=GOLD, alpha=a,
                                    cx=xx + (k - 1) * w * 0.02)
        rules = ["no friction", "perfectly elastic: no energy lost", "the wall never moves"]
        if u < 8.0:
            self.head("Two blocks. One wall.", f"small block m = {us(1.0)} · big block M (gold), pushed toward the wall")
            for i, r in enumerate(rules):
                a = clamp((u - 1.5 - i * 1.6) / 0.4)
                c.text_centered("✓  " + r if False else "•  " + r, h * (0.30 + 0.06 * i), size=h * 0.04, color=WHITE,
                                alpha=a, cx=w * 0.77)
        elif u < 22:
            self.head(f"Equal masses: M = {us(1.0)}", "count every collision (with the wall too)")
        elif u < 30:
            self.head("3 collisions.", None, col=GOLD)
            c.text_centered("3", h * 0.52, size=h * 0.30, color=GOLD, cx=w * 0.78, alpha=clamp((u - 22) / 0.4))
        else:
            self.head("Now make the big block 100× heavier…", "and count again")
        self.bottom("Galperin's colliding blocks (2003)", a=0.6, col=SOFT) if u > 30 else None

    def ch_c100(self, t, u):
        c, w, h = self.canvas, self.L.w, self.L.h
        x1, x2, n, _ = PB_100.at(u)
        fl = 0.0
        if n >= 1 and u - PB_100.hv[n - 1] < 0.18:
            fl = 1 - (u - PB_100.hv[n - 1]) / 0.18
        self.stage(x1, x2, 100.0, "person", flash=fl)
        done = n == 31
        pop = math.exp(-(u - PB_100.hv[-1]) / 0.15) if done else 0.0
        self.count_text(n, w * 0.78, h * 0.50, h * 0.17, GOLD if done else WHITE, pop)
        c.text_centered("collisions", h * 0.56, size=h * 0.03, color=SOFT, bold=False, cx=w * 0.78)
        if 1 <= n < 31:
            c.text_centered(PI_DIG[max(0, n - 10):n], h * 0.66, size=h * 0.045, color=GOLD, cx=w * 0.78)
            c.text_centered("every hit plays the next digit of π", h * 0.71, size=h * 0.026, color=SOFT, bold=False,
                            cx=w * 0.78)
        if done:
            self.pi_line(2, w * 0.78, h * 0.66, h * 0.06, a=clamp((u - PB_100.hv[-1]) / 0.3))
        if u < 9:
            self.head(f"M = {us(100.0)}", "about a person")
        elif u < 15:
            self.head("31 collisions.", "3 … then 31 …", col=GOLD)
        else:
            self.head("3, 31… does that look familiar?", None)

    def ch_c1e4(self, t, u):
        c, w, h = self.canvas, self.L.w, self.L.h
        bu = (u - 1.5) / 3.5
        self.burst_stage(clamp(bu) if bu < 1 else 1.0, 1e4, "truck")
        self.burst_panel(bu if bu > 0 else 0, 314, 3, w * 0.78, h * 0.47, h * 0.19)
        if u < 6:
            self.head(f"M = {us(1e4)}", "about a garbage truck")
        elif u < 12:
            self.head("314 collisions.", "3 · 31 · 314 → 3.14…", col=GOLD)
        else:
            self.head("But WHY would two blocks know π?", "let's find out, in 3 steps")

    def ch_why(self, t, u):
        c, w, h = self.canvas, self.L.w, self.L.h
        ctx = c.ctx
        x1, x2, n, (v1, v2, j) = PB_WHY.at(u)
        fl = 0.0
        if n >= 1 and u - PB_WHY.hv[n - 1] < 0.2:
            fl = 1 - (u - PB_WHY.hv[n - 1]) / 0.2
        self.stage(x1, x2, 100.0, "person", flash=fl, area=(0.04, 0.50))
        # the velocity circle (axes x = √M·V, y = √m·v, normalised by √M·V0)
        cx, cy, R = w * 0.76, h * 0.52, h * 0.27
        a_c = clamp((u - 4) / 1.0)
        c.lines([(cx - R * 1.2, cy, cx + R * 1.2, cy), (cx, cy - R * 1.2, cx, cy + R * 1.2)], SOFT, width=1.5,
                alpha=0.5 * a_c)
        c.text_centered("√M · V", cy + h * 0.035, size=h * 0.024, color=GOLD, cx=cx + R * 1.1, alpha=a_c, bold=False)
        c.text_centered("√m · v", cy - R * 1.22, size=h * 0.024, color=CYAN, cx=cx + w * 0.04, alpha=a_c, bold=False)
        if u >= 5:
            k = clamp((u - 5) / 1.5)
            ctx.new_path()
            ctx.arc(cx, cy, R, -math.pi, -math.pi + 2 * math.pi * k)
            ctx.set_source_rgba(*PINK, 0.8)
            ctx.set_line_width(3)
            ctx.stroke()
        M = 100.0
        sM = math.sqrt(M)

        def P(V, v):
            return cx + R * V, cy - R * v / sM

        ev = SIMS[M]
        if u >= 9:
            pts = [P(e[4], e[2]) for e in ev[:j + 1]]
            cur = P(v2, v1)
            if len(pts) > 0:
                c.polylines([pts + [cur]], WHITE, width=2.2, alpha=0.85)
            c.glow(cur[0], cur[1], h * 0.02, WHITE, strength=0.7, reach=2)
            c.circle(cur[0], cur[1], h * 0.009, WHITE)
        if 17 <= u < 24:                                           # the momentum lines (slope −√(M/m))
            for k in range(-3, 4):
                bxx = cx + k * R * 0.35
                dy = R * 1.3
                dx = dy / math.sqrt(M) * 1.0
                c.lines([(bxx - dx, cy - dy, bxx + dx, cy + dy)], LIME, width=1.5, alpha=0.35)
        if 36 <= u < 48:                                           # equal angles 2θ
            th = theta(M)
            for k in range(0, 31, 2):
                a = math.pi + k * th
                c.lines([(cx, cy, cx + R * math.cos(a), cy - R * math.sin(a))], GOLD, width=1.2, alpha=0.35)
        steps = [
            (0, "Step 1: energy never changes", "½·m·v² + ½·M·V² = E"),
            (4, "Rename: x = √M·V,  y = √m·v", "then  x² + y² = 2E  →  every state sits on a CIRCLE"),
            (9, "The white dot = the two velocities right now", "it starts at the left: only M is moving"),
            (13, "A wall hit flips the small block: v → −v", "the dot jumps straight up or down"),
            (17, "Step 2: a block hit keeps the momentum", "m·v + M·V stays the same → the dot slides along a green line"),
            (24, "Watch all 31 hits", "the dot zig-zags around the circle"),
            (36, "Step 3: every jump turns the same angle", "2θ, with θ = arctan(√(m/M)) = 5.71°"),
            (48, "How many jumps fit in half a circle?", "180° ÷ 5.71° = 31.5  →  31 collisions"),
            (56, "And θ shrinks 10× when M grows 100×", "θ ≈ 1/10, 1/100, 1/1000 rad  →  π/θ = 31.4, 314.15, 3141.59"),
        ]
        cur_s = [s for s in steps if u >= s[0]][-1]
        k = clamp((u - cur_s[0]) / 0.4)
        self.head(cur_s[1], cur_s[2], a=k)
        if u >= 24:
            c.text_centered(f"{n} collisions", h * 0.86, size=h * 0.04, color=GOLD if n == 31 else WHITE, cx=w * 0.76)

    def ch_slice(self, t, u):
        c, w, h = self.canvas, self.L.w, self.L.h
        ctx = c.ctx
        M = 16.0 if u < 34 else 100.0
        th = theta(M)
        ox, oy, Rr = w * 0.42, h * 0.55, h * 0.36
        fan = clamp((u - 8) / 3.0) if u < 34 else clamp((u - 36) / 2.0)
        n_rays = n_hits(M)
        for k in range(0, n_rays + 1):
            if k / max(1, n_rays) > fan:
                break
            a = math.pi / 2 - k * th                                   # rays from straight up, turning clockwise
            c.lines([(ox, oy, ox + Rr * math.cos(a), oy - Rr * math.sin(a))], (0.6, 0.55, 1.0), width=1.6, alpha=0.55)
        ctx.new_path()
        ctx.arc(ox, oy, Rr, -math.pi / 2, math.pi / 2)                  # the half turn (180°)
        ctx.set_source_rgba(0.6, 0.55, 1.0, 0.3)
        ctx.set_line_width(1.5)
        ctx.stroke()
        lx = ox + Rr * 0.04
        prog = clamp((u - 12) / 14.0) if u < 34 else clamp((u - 39) / 10.0)
        y_top, y_bot = oy - Rr * 0.97, oy + Rr * 0.97
        y_cur = y_top + (y_bot - y_top) * prog
        if fan > 0 and prog > 0:
            c.lines([(lx, y_top, lx, y_cur)], WHITE, width=4, alpha=0.95)
        cross = 0
        for k in range(1, n_rays + 1):
            a = math.pi / 2 - k * th
            yk = oy - (lx - ox) * math.tan(a)
            if y_top <= yk <= y_cur:
                cross += 1
                c.circle(lx, yk, h * 0.008, GOLD)
        total = n_hits(M)
        if prog > 0:
            c.text_centered(f"{min(cross, total)} crossings", h * 0.30, size=h * 0.05, color=GOLD, cx=w * 0.83)
        steps = [
            (0, "Another way to see it: the pizza slice", "rescale the positions by √m and √M…"),
            (5, "…and the two blocks become ONE point inside a slice", f"a slice of angle θ = {math.degrees(theta(16)):.1f}° (M = 16 kg)"),
            (11, "Every collision = the point bounces off the slice's edge", "now unfold the slice like a fan, mirror after mirror"),
            (17, "The bouncing path becomes a STRAIGHT line", "each time it crosses a ray = one collision"),
            (27, "A straight line crosses half a circle (180°)", f"so it meets 180° ÷ θ rays: 12 collisions for 16 kg"),
            (34, "M = 100 kg: thinner slices, θ = 5.71°", "180° ÷ 5.71° → 31 crossings"),
            (50, "The count is always: half a turn ÷ the slice angle = π / θ", "and that is where π comes from"),
        ]
        cur_s = [s for s in steps if u >= s[0]][-1]
        self.head(cur_s[1], cur_s[2], a=clamp((u - cur_s[0]) / 0.4))

    def ch_other(self, t, u):
        """fast and clear: only ×100 steps give π."""
        c, w, h = self.canvas, self.L.w, self.L.h
        rows = [(16, 12, "3.1…?", False), (1000, 99, "3.14…?", False), (10000, 314, "3.14", True)]
        self.head("Does ANY heavier block give π?", "quick test")
        for i, (M, N, want, ok) in enumerate(rows):
            t0 = 1.5 + 3.0 * i
            if u < t0:
                continue
            k = clamp((u - t0) / 0.8)
            y = h * (0.33 + 0.17 * i)
            col = LIME if ok else RED
            c.text_centered(f"M = {lbs(M)}", y - h * 0.012, size=h * 0.045, color=GOLD, cx=w * 0.22)
            c.text_centered(f"({M:,} kg)", y + h * 0.028, size=h * 0.028, color=SOFT, bold=False, cx=w * 0.22)
            c.text_centered(f"{int(N * k):,} collisions", y, size=h * 0.055, color=WHITE, cx=w * 0.52)
            if k >= 1:
                pop = 1 + 0.3 * math.exp(-(u - t0 - 0.8) / 0.12)
                c.text_centered("YES: π" if ok else "NOT π", y, size=h * 0.055 * pop, color=col, cx=w * 0.82)
                if not ok:
                    c.lines([(w * 0.42, y - h * 0.018, w * 0.62, y - h * 0.018)], RED, width=4, alpha=0.8)
        if u >= 11:
            self.bottom("Only 100× heavier steps work: each one adds a digit of π",
                        a=clamp((u - 11) / 0.4))

    def ch_ladder(self, t, u):
        self._ladder(t, u, 0)

    def ch_ladder2(self, t, u):
        self._ladder(t, u, 3)

    def _ladder(self, t, u, off):
        c, w, h = self.canvas, self.L.w, self.L.h
        i = min(len(LADDER) - 1, off + int(u // OBJ_T))
        r = u - (i - off) * OBJ_T
        self.ring_col = RING_COLS[i]
        M, kind, name, mass, q1, q2 = LADDER[i]
        N = LADDER_N[i]
        nd = len(str(N))
        self.head(name, f"{mass}   ·   object {i + 1} of {len(LADDER)}", col=GOLD)
        if r < 7.0:                                              # the object, big, with its quote
            k_in = smooth(clamp(r / 0.7))
            if r < 6.0:
                cx_, cy_, S = w * 0.5, h * 0.5, h * 0.52 * (0.85 + 0.15 * k_in)
            else:
                v = smooth(r - 6.0)
                cx_ = w * 0.5 + (w * 0.42 - w * 0.5) * v
                cy_ = h * 0.5 + (h * 0.70 - h * 0.5) * v
                S = h * 0.52 + (h * 0.18 - h * 0.52) * v
            self.draw_object(kind, cx_, cy_, S, a=k_in * (1 - smooth(clamp((r - 6.6) / 0.4))))
            self.quote(q1, h * 0.86, a=clamp((r - 1.2) / 0.4) * clamp((6.0 - r) / 0.4))
            return
        bu = (r - 7.5) / 3.0
        self.burst_stage(clamp(bu) if bu > 0 else 0.0, M, kind)
        self.burst_panel(bu if bu > 0 else 0, N, nd, w * 0.78, h * 0.47, h * 0.19)
        if bu >= 1:
            self.quote(f"{N:,} collisions = {nd} digits of π" if nd <= 13 else f"{nd} digits of π",
                       h * 0.925, a=clamp((r - 10.8) / 0.4) * clamp((16.5 - r) / 0.4), col=GOLD)
            self.quote(q2, h * 0.925, a=clamp((r - 16.5) / 0.4))

    def ch_punch(self, t, u):
        c, w, h = self.canvas, self.L.w, self.L.h
        if u < 4.0:
            k_in = smooth(clamp(u / 0.7))
            self.draw_object("universe", w * 0.5, h * 0.5, h * 0.5, a=k_in * clamp((4.0 - u) / 0.5))
            self.head("LAST ONE: A TENTH OF THE UNIVERSE", "≈ 2.2 × 10⁵² lb (10⁵² kg): all the matter in all the galaxies ÷ 10",
                      col=GOLD)
            self.quote("The heaviest block we can imagine.", h * 0.86, a=clamp((u - 1.0) / 0.4) * clamp((4.0 - u) / 0.4))
            return
        bu = (u - 4.5) / 3.0
        self.burst_stage(clamp(bu) if bu > 0 else 0.0, 1e52, "universe")
        frac = 0.5 - 0.5 * math.cos(math.pi * clamp(bu))
        self.ring(w * 0.78, h * 0.47, h * 0.19, frac, UNIVERSE_N, done_glow=clamp((bu - 1) * 3) if bu >= 1 else 0.0)
        s_ = str(UNIVERSE_N)
        shown = s_[:max(1, int(len(s_) * frac))] if bu < 1 else s_
        c.text_centered(shown, h * 0.49, size=h * 0.035, color=GOLD if bu >= 1 else WHITE, cx=w * 0.78, max_w=w * 0.18)
        c.text_centered("collisions", h * 0.53, size=h * 0.026, color=SOFT, bold=False, cx=w * 0.78)
        if u < 11:
            self.head(f"M = {us(1e52)}", "a tenth of all the matter in the observable universe")
        elif u < 18:
            self.head("27 digits of π.", "3.14159265358979323846264338", col=GOLD)
        elif u < 26:
            self.head("Computers already know over 100 trillion digits.", None)
        else:
            self.head("The slowest way to compute π ever…", "…and the most beautiful", col=GOLD)

    def ch_recap(self, t, u):
        c, w, h = self.canvas, self.L.w, self.L.h
        ctx = c.ctx
        self.head("TWO BLOCKS, ONE WALL, π", "M ×100  →  one more digit")
        rows = [("2.2 lb (1 kg)", "3"), ("220 lb  (a person)", "31"), ("22,000 lb  (a truck)", "314"),
                ("a freight train", "3,141"), ("an aircraft carrier", "31,415"), ("two Great Pyramids", "314,159"),
                ("all of humanity ×2", "3,141,592"), ("Mount Everest", "31,415,926"), ("Lake Superior", "314,159,265"),
                ("Pluto", "12 digits"), ("1/6 of the Earth", "13 digits"), ("half the Sun", "16 digits"),
                ("1/3 of the Milky Way", "22 digits"), ("1/10 of the universe", "27 digits")]
        for i, (a_, b_) in enumerate(rows):
            col = i % 2
            rr = i // 2
            x = w * (0.06 + 0.46 * col)
            y = h * (0.22 + rr * 0.092)
            al = clamp((u - 0.3 - i * 0.15) / 0.3)
            ctx.rectangle(x, y, w * 0.42, h * 0.078)
            ctx.set_source_rgba(0.10, 0.10, 0.18, 0.9 * al)
            ctx.fill()
            c.text_centered(a_, y + h * 0.05, size=h * 0.03, color=WHITE, alpha=al, cx=x + w * 0.12, max_w=w * 0.22,
                            bold=False)
            c.text_centered(b_, y + h * 0.05, size=h * 0.034, color=GOLD, alpha=al, cx=x + w * 0.32, max_w=w * 0.18)
        if u > 4:
            self.bottom("Which object should I try next?", a=clamp((u - 4) / 0.4))

    # ------------------------------------------------------------- frame
    def draw(self, f, rule):
        L, c = self.L, self.canvas
        w, h = L.w, L.h
        t = f * DT
        ch = ORDER[0]
        for k in ORDER:
            if t >= T0[k]:
                ch = k
        u = t - T0[ch]
        self.bg()
        self.ring_col = GOLD
        getattr(self, "ch_" + ch)(t, u)
        if ch not in ("intro", "recap"):
            self.progress_row(t)
        dur = dict(CHAPTERS)[ch]
        fa = max(clamp(1 - u / 0.35) if ch != "intro" else 0.0, clamp(1 - (dur - u) / 0.35))
        if fa > 0:
            c.ctx.rectangle(0, 0, w, h)
            c.ctx.set_source_rgba(0.01, 0.01, 0.03, 0.9 * fa)
            c.ctx.fill()
        c.text_centered("SatFy", h * 0.985, size=h * 0.022, color=WHITE, alpha=0.25, cx=w * 0.955, bold=False)


def render(layout, out_path, rule, still_frame=None):
    sc = Scene(layout)
    writer = None if still_frame is not None else VideoWriter(out_path, sc.canvas, FPS)
    nf = int(round(T_END * FPS))
    for f in range(nf):
        if still_frame is not None and f != still_frame:
            continue
        sc.draw(f, rule)
        if writer is None:
            studio.save_still(sc.canvas, out_path)
            return f / FPS
        writer.write_frame()
    writer.close()
    return nf / FPS


# ---------------------------------------------------------------- sound
def marimba(b, t0, m, g):
    tv = np.arange(int(0.9 * sfx.SR)) / sfx.SR
    f = sfx.hz(m)
    sig = (np.sin(2 * np.pi * f * tv) * np.exp(-tv / 0.45) + 0.35 * np.sin(2 * np.pi * f * 3.93 * tv) * np.exp(-tv / 0.05))
    b.add(t0, sig * np.clip(tv / 0.002, 0, 1), g, wrap=False)


SCALE = [60, 62, 64, 67, 69, 72, 74, 76, 79, 81]


def strum_burst(b, t0, dur, n_notes=48, g=0.06):
    """a harp-like run over the burst: up and back down the scale, then a chord."""
    for k in range(n_notes):
        u = k / (n_notes - 1)
        pos = int((1 - abs(2 * u - 1)) * 19)
        m = SCALE[pos % 10] + 12 * (pos // 10)
        marimba(b, t0 + dur * (0.5 - 0.5 * math.cos(math.pi * u)), m, g)
    b.hit(t0 + dur, 0.2, low=95)
    b.chime(t0 + dur + 0.02, (72, 76, 79, 84), 0.07, decay=1.0)


def light_bed(b):
    """a soft music-box arpeggio (high register, no sustained low notes), the chord changing with the chapters."""
    AM, F, C, G = (69, 72, 76, 81), (65, 69, 72, 77), (64, 67, 72, 76), (67, 71, 74, 79)
    plan = {"intro": [AM], "setup": [C, G, AM, F], "c100": [AM], "c1e4": [F], "why": [G, C, AM, F],
            "other": [F], "ladder": [AM, F, C, G], "ladder2": [C, G, AM, F], "punch": [AM, F], "recap": [C, G, AM, F]}
    pat = [0, 2, 1, 3, 2, 1, 3, 2]
    step = 0.5
    for k in ORDER:
        t, end = T0[k], T0[k] + dict(CHAPTERS)[k]
        q = 0
        while t < end - 0.05:
            chs = plan[k]
            ch = chs[int((t - T0[k]) // 8.0) % len(chs)]
            obj_i = -1
            if k in ("ladder", "ladder2"):
                obj_i = int((t - T0[k]) // OBJ_T) + (0 if k == "ladder" else 3)
            if obj_i >= 0 and obj_i % 2 == 1:                      # alternate objects: a soft pluck instead
                b.pluck(t, ch[pat[q % 8]], 0.016 if q % 4 else 0.022, d=0.5)
            else:
                marimba(b, t, ch[pat[q % 8]] + (12 if obj_i in (4, 8) else 0), 0.02 if q % 4 else 0.028)
            t += step
            q += 1


def sound():
    b = sfx.Bed(T_END, seed=5)
    light_bed(b)
    for k in ORDER[1:]:
        b.whoosh(T0[k] - 0.2, 0.5, 0.04)
    b.chime(T0["intro"] + 0.2, (81, 84, 88), 0.05, decay=1.2)
    strum_burst(b, T0["intro"] + 3.2, 3.0)
    for j, ht in enumerate(PB_SETUP.hv):
        marimba(b, T0["setup"] + ht, SCALE[int(PI_DIG[j])], 0.22)
    b.chime(T0["setup"] + 22.0, (72, 76, 79), 0.07)
    for j, ht in enumerate(PB_100.hv):
        marimba(b, T0["c100"] + ht, SCALE[int(PI_DIG[j])], 0.18)
    b.chime(T0["c100"] + PB_100.hv[-1] + 0.1, (72, 76, 79, 84), 0.07)
    strum_burst(b, T0["c1e4"] + 1.5, 3.5)
    for j, ht in enumerate(PB_WHY.hv):
        marimba(b, T0["why"] + ht, SCALE[int(PI_DIG[j])], 0.12)
    for i in range(3):                                           # the quick test: "not π" twice, then "yes"
        tt = T0["other"] + 1.5 + 3.0 * i + 0.8
        if i < 2:
            marimba(b, tt, 76, 0.12)
            marimba(b, tt + 0.18, 72, 0.12)
        else:
            b.chime(tt, (72, 76, 79, 84), 0.08)
    for i in range(len(LADDER)):
        base = T0["ladder"] + i * OBJ_T if i < 3 else T0["ladder2"] + (i - 3) * OBJ_T
        b.chime(base + 0.3, (84, 88), 0.04)
        b.whoosh(base + 6.0, 1.0, 0.05, up=False)
        strum_burst(b, base + 7.5, 3.0, 40 + 2 * i)
    b.chime(T0["punch"] + 0.3, (84, 88, 91), 0.05)
    strum_burst(b, T0["punch"] + 4.5, 3.0, 60)
    b.chime(T0["punch"] + 26.0, (69, 72, 76, 81, 84), 0.07, decay=1.2)
    out = b.get()
    k = int(1.5 * sfx.SR)
    out[-k:] *= np.linspace(1, 0, k) ** 2
    return out


def main():
    label, rule = arg("--label", "v1"), arg("--rule", "")
    studio.OUT_DIR.mkdir(exist_ok=True)
    layout = get_layout(kit.orients()[0])
    print(f"[{SCENE}] {T_END:.0f}s = {int(T_END // 60)}:{int(T_END % 60):02d}  ladder {LADDER_N}  universe {UNIVERSE_N}")
    if kit.has("--still"):
        f = int(round(float(arg("--at")) * FPS)) if arg("--at") else int(arg("--frame", "0"))
        png = studio.OUT_DIR / f"{SCENE}_{label}_f{f}_{layout.tag}.png"
        render(layout, png, rule, still_frame=f)
        print(f"[{SCENE}] -> {png}")
        return
    name = f"{SCENE}_{label}_{layout.tag}"
    video = studio.OUT_DIR / f"{name}_silent.mp4"
    d = render(layout, video, rule)
    kit.deliver_loop(SCENE, name, layout, video, [], d, voice="piano", bed=sound(), peak_db=-6.0)


if __name__ == "__main__":
    main()
