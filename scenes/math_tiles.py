"""MATH TILES — a famous tune on falling neon tiles; the beat under it is made of equations.

v2 (owner: no finger, no white board, "the reference's visuals are way better"): dark neon board. Four melody
columns (each its own neon colour) take the tune's notes — column = pitch band, so the glowing line through the
falling tiles draws the melody as a graph. Two side lanes carry the math beat, each tile drawn as its equation's
graph: left = 808 tiles with the decay curve y = e^(−8·(x mod 1)) inside, right = hi-hat tiles with the floor(2x)
staircase. Tiles burst on the hit line (ring + sparks). Layers enter by section: 808 → hats → claps → drop
(the board pulses with the 808 envelope). Tempo: speed = e^(k·t), climbing to the last frame.
Songs (public domain, our own synthesis): --song turca (Mozart, Rondo alla Turca, 1783) | mountain (Grieg, 1875).
Loop: tiles sit at fixed scroll positions and the tune repeats, so the board at the end IS frame 0; only the tempo
drops back to ×1 (the tune starting over).
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

SCENE = "math_tiles"
GOLD = (1.0, 0.82, 0.40)
CYAN = (0.40, 0.85, 1.0)
PINK = (1.0, 0.40, 0.65)
LIME = (0.55, 1.0, 0.55)
VIOLET = (0.70, 0.55, 1.0)
COLCOL = [PINK, VIOLET, CYAN, LIME]                  # melody columns
R_ = None                                            # a rest

SONG = arg("--song", "turca")
if SONG == "mountain":
    _M = [(57, 1), (59, 1), (60, 1), (62, 1), (64, 1), (60, 1), (64, 2), (63, 1), (59, 1), (63, 2), (62, 1),
          (58, 1), (62, 2), (57, 1), (59, 1), (60, 1), (62, 1), (64, 1), (60, 1), (64, 1), (69, 1), (67, 1),
          (64, 1), (60, 1), (64, 1), (67, 4)]
    MELODY = [(m + 12, 2 * d) for m, d in _M] * 3                # in 16ths
    ROOTS = [45] * 99
    TITLE = "IN THE HALL OF THE MOUNTAIN KING · GRIEG (1875)"
    BPM0, T_DEF = 130, 15.0
else:
    _A = [(71, 1), (69, 1), (68, 1), (69, 1), (72, 2), (R_, 2),
          (74, 1), (72, 1), (71, 1), (72, 1), (76, 2), (R_, 2),
          (77, 1), (76, 1), (75, 1), (76, 1), (83, 1), (81, 1), (80, 1), (81, 1),
          (83, 1), (81, 1), (80, 1), (81, 1), (84, 4)]
    _CLOSE = _A + [(81, 2), (84, 2), (83, 1), (81, 1), (80, 1), (81, 1),
                   (76, 1), (77, 1), (74, 1), (72, 1), (71, 1), (69, 1), (68, 1), (71, 1),
                   (69, 4), (R_, 4)]
    MELODY = (_A + [(81, 2), (84, 2), (83, 1), (81, 1), (80, 1), (81, 1),
                    (83, 1), (81, 1), (80, 1), (81, 1), (83, 1), (81, 1), (80, 1), (78, 1),
                    (76, 4), (R_, 4)]
              + _CLOSE + _CLOSE)                      # the closing phrase twice: the 2nd time is the drop
    # one root per 2/4 bar (8 sixteenths): A minor, the half cadence on E
    ROOTS = [45, 45, 45, 45, 45, 40, 40] + [45, 45, 45, 45, 45, 40, 45] * 2
    TITLE = "RONDO ALLA TURCA · MOZART (1783)"
    BPM0, T_DEF = 100, 16.5

TOTAL = sum(d for _, d in MELODY)                    # sixteenths per loop
T_LOOP = float(arg("--len", str(T_DEF)))
R0 = 4 * float(arg("--bpm", str(BPM0))) / 60.0       # sixteenths per second at the start
SEC = ([0, 32, 56, 112] if SONG != "mountain"                 # 808 → +hats → +claps → drop (= the repeat)
       else [0, TOTAL * 2 // 7, TOTAL * 4 // 7, TOTAL * 11 // 14])


def _solve_k():
    lo, hi = 1e-5, 1.0
    for _ in range(80):
        k = (lo + hi) / 2
        if R0 / k * (math.exp(k * T_LOOP) - 1) > TOTAL:
            hi = k
        else:
            lo = k
    return (lo + hi) / 2


K = _solve_k()


def phase(t):
    t = t % T_LOOP
    return R0 / K * (math.exp(K * t) - 1)


def t_of(ph):
    return math.log(1 + ph * K / R0) / K


NOTES = []                                            # (start, dur, midi, col)
_p = 0
_pitches = sorted({m for m, _ in MELODY if m is not None})
for m, d in MELODY:
    if m is not None:
        NOTES.append((_p, d, m, _pitches.index(m) % 4))          # neighbouring pitches → different columns
    _p += d
KICKS = list(range(0, TOTAL, 4))                      # every beat (quarter = 4 sixteenths)
HATS = list(range(SEC[1], TOTAL, 2))                  # every eighth from section 2
CLAPS = [u for u in range(SEC[2], TOTAL, 8) if True]  # beat 2 of each 2/4 bar → offset below
CLAPS = [u + 4 for u in CLAPS if u + 4 < TOTAL]

LAYERS = [("808", "y = e^(−8·(x mod 1))", GOLD), ("hi-hats", "y = floor(2x)", CYAN),
          ("claps", "x mod 2 = 1", PINK), ("drop", "everything × e^(kt)", (1, 1, 1))]


def simulate():
    return {"nf": int(round(T_LOOP * FPS))}


PI_DIGITS = [3, 1, 4, 1, 5, 9, 2, 6, 5, 3, 5, 8, 9, 7, 9, 3, 2, 3, 8, 4, 6, 2, 6, 4, 3, 3, 8, 3]
LANES = [0.0, 0.13, 0.315, 0.5, 0.685, 0.87, 1.0]    # 808 | 4 melody columns | hi-hats
DEPTH = 6.0                                           # perspective: a tile 6 sixteenths away is half size
DMAX = 64.0                                           # the road fades out at the horizon


def _hash(a, b):
    x = (a * 73856093) ^ (b * 19349663)
    return ((x * 2654435761) & 0xFFFFFFFF) / 4294967296.0


def _mix(a, b, k):
    return tuple(a[i] + (b[i] - a[i]) * k for i in range(3))


class Scene:
    """v3 "Math City": a perspective road into a π skyline under a synthwave sun."""

    def __init__(self, layout, sim):
        self.L, self.sim = layout, sim
        self.canvas = Canvas(layout.w, layout.h, studio.render_scale())
        w, h = layout.w, layout.h
        self.hz, self.yhit, self.ybot = h * 0.405, h * 0.640, h * 0.712
        self.WH = w * 0.43                                           # road half-width at the hit line
        rng = np.random.default_rng(31)
        self.stars = [(rng.uniform(0, w), rng.uniform(h * 0.16, h * 0.36), rng.uniform(1.0, 2.6),
                       rng.uniform(0, 6.28)) for _ in range(70)]
        # the π skyline: one building per digit, height ∝ digit + 1
        self.blds = []
        nb = len(PI_DIGITS)
        bw = w / nb
        for i, dg in enumerate(PI_DIGITS):
            hh = h * (0.018 + 0.0095 * dg)
            wins = [(cx, ry) for ry in range(int((hh - h * 0.012) / (h * 0.0105)))
                    for cx in range(2)]
            self.blds.append((i * bw + bw * 0.08, bw * 0.84, hh, dg, wins))

    def P(self, u, d):
        s = DEPTH / (DEPTH + d)
        return (self.L.w / 2 + (u - 0.5) * 2 * self.WH * s, self.hz + (self.yhit - self.hz) * s)

    def quad(self, u0, u1, d0, d1):
        return [self.P(u0, d0), self.P(u1, d0), self.P(u1, d1), self.P(u0, d1)]

    def fill_poly(self, pts, src):
        ctx = self.canvas.ctx
        ctx.new_path()
        ctx.move_to(*pts[0])
        for q in pts[1:]:
            ctx.line_to(*q)
        ctx.close_path()
        if isinstance(src, tuple):
            ctx.set_source_rgba(*src)
        else:
            ctx.set_source(src)
        ctx.fill()

    # ------------------------------------------------------------------ the sky, the sun, the city
    def sky(self, t, ph, dk, env):
        c, w, h = self.canvas, self.L.w, self.L.h
        ctx = c.ctx
        top = _mix((0.05, 0.01, 0.10), (0.01, 0.02, 0.08), dk)
        mid = _mix((0.32, 0.05, 0.36), (0.10, 0.06, 0.38), dk)
        low = _mix((1.00, 0.38, 0.42), (0.95, 0.25, 0.75), dk)
        g = cairo.LinearGradient(0, 0, 0, self.hz)
        g.add_color_stop_rgb(0.0, *top)
        g.add_color_stop_rgb(0.45, *top)
        g.add_color_stop_rgb(0.78, *mid)
        g.add_color_stop_rgb(1.0, *low)
        ctx.rectangle(0, 0, w, self.hz + 2)
        ctx.set_source(g)
        ctx.fill()
        for (x, y, r, p0) in self.stars:
            a = 0.35 + 0.35 * math.sin(t * 1.3 + p0)
            c.circle(x, y, r, (1, 1, 1), alpha=a * (1 - (y - h * 0.16) / (h * 0.25)))
        # the sun: striped, gaps drifting down (synthwave), with a soft halo
        sx, sy, sr = w / 2, self.hz - h * 0.05, w * 0.215
        c.glow(sx, sy, sr * 1.15, _mix((1, 0.45, 0.4), (1, 0.3, 0.8), dk), strength=0.55 + 0.15 * env, reach=2.0)
        ctx.save()
        ctx.rectangle(0, 0, w, self.hz)                              # the sun sets behind the horizon
        ctx.clip()
        ctx.push_group()
        g = cairo.LinearGradient(0, sy - sr, 0, sy + sr * 0.2)
        g.add_color_stop_rgb(0, 1.0, 0.92, 0.45)
        g.add_color_stop_rgb(0.55, *_mix((1.0, 0.55, 0.35), (1.0, 0.45, 0.6), dk))
        g.add_color_stop_rgb(1.0, *_mix((1.0, 0.25, 0.55), (0.85, 0.2, 0.95), dk))
        ctx.arc(sx, sy, sr, 0, 2 * math.pi)
        ctx.set_source(g)
        ctx.fill()
        ctx.set_operator(cairo.OPERATOR_DEST_OUT)
        drift = (t * 0.35) % 1.0
        for k in range(9):
            yy = sy - sr * 0.42 + (k + drift) * sr * 0.11
            th = sr * 0.012 * (k + drift + 0.5)
            ctx.rectangle(sx - sr, yy, 2 * sr, th)
        ctx.set_source_rgba(0, 0, 0, 1)
        ctx.fill()
        ctx.set_operator(cairo.OPERATOR_OVER)
        ctx.pop_group_to_source()
        ctx.paint()
        ctx.restore()
        # the ground: a purple glow fading from the horizon
        g = cairo.LinearGradient(0, self.hz, 0, self.ybot + h * 0.05)
        g.add_color_stop_rgb(0, *_mix((0.30, 0.06, 0.30), (0.10, 0.08, 0.32), dk))
        g.add_color_stop_rgb(0.35, 0.08, 0.02, 0.12)
        g.add_color_stop_rgb(1, 0.02, 0.01, 0.04)
        ctx.rectangle(0, self.hz, w, self.ybot + h * 0.05 - self.hz)
        ctx.set_source(g)
        ctx.fill()
        # MATH CITY in front of the sun; windows and neon signs light up with the beat
        self.math_city(t, ph, dk, env, max(i for i in range(4) if SEC[i] <= ph))
        # horizon glow line
        c.lines([(0, self.hz, w, self.hz)], _mix((1, 0.6, 0.7), (0.6, 0.9, 1), dk), width=3, alpha=0.7 + 0.3 * env)

    # ------------------------------------------------------------------ MATH CITY: a skyline built from math
    def neon(self, paths, col, a, width=2.5):
        c = self.canvas
        c.polylines(paths, col, width=width * 3.2, alpha=0.22 * a)
        c.polylines(paths, _mix(col, (1, 1, 1), 0.35), width=width, alpha=0.95 * a)

    def neon_text(self, s, x, y, size, col, a):
        c = self.canvas
        c.glow(x, y - size * 0.35, size * 0.9, col, strength=0.35 * a, reach=2.0)
        c.text_centered(s, y, size=size, color=_mix(col, (1, 1, 1), 0.3), alpha=a, cx=x)

    def windows(self, x0, y0, x1, y1, seed, kick, lit, rule=None):
        """Window grid in a box; lit by the beat, or by a math rule (row/col pattern)."""
        ctx, h = self.canvas.ctx, self.L.h
        dx, dy = h * 0.0072, h * 0.0098
        nx, ny = max(1, int((x1 - x0) / dx)), max(1, int((y1 - y0) / dy))
        for i in range(nx):
            for j in range(ny):
                on = rule(i / max(1, nx - 1), j, ny) if rule else _hash(seed * 131 + i * 17 + j, kick) < lit
                if on:
                    col = (1.0, 0.85, 0.45) if (i + j + seed) % 4 else (0.45, 0.9, 1.0)
                    ctx.rectangle(x0 + i * dx + dx * 0.25, y0 + j * dy + dy * 0.25, dx * 0.5, dy * 0.45)
                    ctx.set_source_rgba(*col, 0.95)
                    ctx.fill()

    def glyph_building(self, ch, xc, ht, col, a, dark, seed, kick, lit):
        """A tower shaped like a math symbol: dark glyph silhouette, beat-lit windows inside, neon outline."""
        ctx = self.canvas.ctx
        ctx.select_font_face("Arial", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        ctx.set_font_size(100)
        te = ctx.text_extents(ch)
        fs = 100 * ht / te.height
        ctx.set_font_size(fs)
        te = ctx.text_extents(ch)
        x = xc - te.width / 2 - te.x_bearing
        y = self.hz - (te.y_bearing + te.height)
        ctx.new_path()
        ctx.move_to(x, y)
        ctx.text_path(ch)
        ctx.set_source_rgb(*dark)
        ctx.fill_preserve()
        ctx.save()
        ctx.clip()
        self.windows(xc - te.width / 2, self.hz - ht, xc + te.width / 2, self.hz, seed, kick, lit)
        ctx.restore()
        ctx.new_path()
        ctx.move_to(x, y)
        ctx.text_path(ch)
        ctx.set_source_rgba(*col, 0.25 * a)
        ctx.set_line_width(7)
        ctx.stroke_preserve()
        ctx.set_source_rgba(*_mix(col, (1, 1, 1), 0.35), 0.95 * a)
        ctx.set_line_width(2.2)
        ctx.stroke()

    def box(self, x0, wd, ht, dark, rim, seed, kick, lit, rule=None, win=True):
        ctx, c = self.canvas.ctx, self.canvas
        y0 = self.hz - ht
        ctx.rectangle(x0, y0, wd, ht + 1)
        ctx.set_source_rgb(*dark)
        ctx.fill()
        c.lines([(x0, y0, x0 + wd, y0)], rim, width=2, alpha=0.8)
        if win:
            self.windows(x0 + wd * 0.06, y0 + ht * 0.05, x0 + wd * 0.94, self.hz - ht * 0.03, seed, kick, lit, rule)
        return y0

    def math_city(self, t, ph, dk, env, sec):
        c, w, h = self.canvas, self.L.w, self.L.h
        ctx = c.ctx
        hz = self.hz
        kick = int(ph // 4)
        lit = [0.18, 0.35, 0.55, 0.92][sec]
        a = min(1.0, 0.55 + 0.35 * env + 0.15 * sec)                  # neon brightness pulses with the 808
        dark = _mix((0.07, 0.025, 0.11), (0.03, 0.03, 0.10), dk)
        back = _mix((0.13, 0.04, 0.17), (0.07, 0.06, 0.18), dk)
        rim = _mix((1, 0.5, 0.6), (0.5, 0.8, 1), dk)
        # back row: small buildings, heights = digits of π
        for i, (x0, bw, hh, dg, wins) in enumerate(self.blds):
            self.box(x0, bw, hh * 0.62, back, rim, i + 50, kick, lit * 0.6, win=False)
        H = h
        # 2. π tower
        self.glyph_building("π", w * 0.105, H * 0.105, PINK, a, dark, 2, kick, lit)
        # 3. tower with a scrolling sine-graph billboard + antenna
        x0, wd, ht = w * 0.215, w * 0.075, H * 0.135
        y0 = self.box(x0, wd, ht, dark, rim, 3, kick, lit)
        bx0, by0, bw_, bh = x0 + wd * 0.1, y0 + ht * 0.08, wd * 0.8, ht * 0.26
        ctx.rectangle(bx0, by0, bw_, bh)
        ctx.set_source_rgba(0.02, 0.03, 0.06, 0.95)
        ctx.fill()
        self.neon([[(bx0, by0), (bx0 + bw_, by0), (bx0 + bw_, by0 + bh), (bx0, by0 + bh), (bx0, by0)]], CYAN, a, 1.6)
        sp_ = [(bx0 + bw_ * k / 30, by0 + bh / 2 - bh * 0.36 * math.sin(2 * math.pi * (k / 30 * 1.5) - ph * 0.5))
               for k in range(31)]
        self.neon([sp_], LIME, a, 1.8)
        c.lines([(x0 + wd / 2, y0, x0 + wd / 2, y0 - H * 0.025)], rim, width=2, alpha=0.8)
        if int(t * 2) % 2:
            c.glow(x0 + wd / 2, y0 - H * 0.025, w * 0.012, (1, 0.3, 0.3), strength=0.9, reach=2)
        # 4. Δ pyramid
        self.glyph_building("Δ", w * 0.325, H * 0.075, GOLD, a, dark, 4, kick, lit)
        # 5. ∫ spire (the tallest)
        self.glyph_building("∫", w * 0.405, H * 0.15, VIOLET, a, dark, 5, kick, lit)
        # 6. Euler's identity in neon on a wide block
        x0, wd, ht = w * 0.44, w * 0.12, H * 0.10
        y0 = self.box(x0, wd, ht, dark, rim, 6, kick, lit)
        ctx.rectangle(x0 + wd * 0.05, y0 + ht * 0.07, wd * 0.9, ht * 0.24)
        ctx.set_source_rgba(0.02, 0.02, 0.05, 0.95)
        ctx.fill()
        self.neon_text("e^(iπ) + 1 = 0", x0 + wd / 2, y0 + ht * 0.25, w * 0.0165, PINK, a)
        # 7. Σ tower
        self.glyph_building("Σ", w * 0.635, H * 0.10, LIME, a, dark, 7, kick, lit)
        # 8. √ building with x under the root
        self.glyph_building("√", w * 0.725, H * 0.13, CYAN, a, dark, 8, kick, lit)
        # 9. Pythagoras tower: a neon right triangle + a² + b² = c²
        x0, wd, ht = w * 0.755, w * 0.065, H * 0.115
        y0 = self.box(x0, wd, ht, dark, rim, 9, kick, lit)
        tx0, ty0, ts = x0 + wd * 0.18, y0 + ht * 0.36, wd * 0.62
        ctx.rectangle(x0 + wd * 0.06, y0 + ht * 0.05, wd * 0.88, ht * 0.38)
        ctx.set_source_rgba(0.02, 0.02, 0.05, 0.95)
        ctx.fill()
        self.neon([[(tx0, ty0), (tx0 + ts, ty0), (tx0, ty0 - ts * 0.42), (tx0, ty0)]], GOLD, a, 1.6)
        self.neon_text("a²+b²=c²", x0 + wd / 2, y0 + ht * 0.43 + w * 0.016, w * 0.0155, GOLD, a)
        # 10. the unit-circle Ferris wheel: a radius turns with the music, its sin drops to the axis
        cx_, cy_, R = w * 0.865, hz - H * 0.058, H * 0.05
        c.lines([(cx_, cy_, cx_ - R * 0.55, hz), (cx_, cy_, cx_ + R * 0.55, hz)], rim, width=3, alpha=0.8)
        ang = 2 * math.pi * ph / 16
        spokes = [(cx_, cy_, cx_ + R * math.cos(ang + k * math.pi / 4), cy_ - R * math.sin(ang + k * math.pi / 4))
                  for k in range(8)]
        c.lines(spokes, (0.6, 0.6, 0.8), width=1.2, alpha=0.5)
        self.neon([[(cx_ + R * math.cos(2 * math.pi * k / 48), cy_ - R * math.sin(2 * math.pi * k / 48))
                    for k in range(49)]], VIOLET, a, 2.0)
        px, py = cx_ + R * math.cos(ang), cy_ - R * math.sin(ang)
        self.neon([[(cx_, cy_), (px, py)]], GOLD, a, 2.0)
        c.lines([(px, py, px, cy_)], PINK, width=2, alpha=0.9 * a)
        c.glow(px, py, w * 0.01, GOLD, strength=0.9, reach=2)
        for k in range(8):                                            # cabins
            ca = ang + k * math.pi / 4
            c.circle(cx_ + R * math.cos(ca), cy_ - R * math.sin(ca) + 4, 3.2, _mix(COLCOL[k % 4], (1, 1, 1), 0.3),
                     alpha=0.9)
        # 11. golden-spiral facade
        x0, wd, ht = w * 0.93, w * 0.07, H * 0.125
        y0 = self.box(x0, wd, ht, dark, rim, 11, kick, lit)
        gx, gy_, gs = x0 + wd * 0.1, y0 + ht * 0.06, wd * 0.8
        sq, pts = [], []
        x, y, s_, d = gx, gy_, gs / 1.618, 0
        ctx.rectangle(gx, gy_, gs, gs / 1.618)
        ctx.set_source_rgba(0.02, 0.02, 0.05, 0.95)
        ctx.fill()
        cxs, cys, r = gx + gs / 1.618, gy_ + gs / 1.618, gs / 1.618
        a0 = math.pi
        for k in range(6):                                            # quarter arcs shrinking by φ
            pts += [(cxs + r * math.cos(a0 + math.pi / 2 * j / 8), cys + r * math.sin(a0 + math.pi / 2 * j / 8))
                    for j in range(9)]
            nr = r / 1.618
            na = a0 + math.pi / 2
            cxs += (r - nr) * math.cos(na)
            cys += (r - nr) * math.sin(na)
            a0, r = na, nr
        self.neon([pts], GOLD, a, 1.8)
        self.neon([[(gx, gy_), (gx + gs, gy_), (gx + gs, gy_ + gs / 1.618), (gx, gy_ + gs / 1.618), (gx, gy_)]],
                  PINK, a * 0.7, 1.2)
        # 12. ∞ sign on a rooftop
        self.neon_text("∞", w * 0.7875, self.hz - H * 0.115 - H * 0.004, w * 0.045, CYAN, a)
        # 13. φ on the roof of the Euler block
        self.neon_text("φ", w * 0.44 + w * 0.12 * 0.8, self.hz - H * 0.10 - H * 0.004, w * 0.04, GOLD, a)

    # ------------------------------------------------------------------ the road and the tiles
    def neon_slab(self, u0, u1, d0, d1, col, fog):
        """A 3-D tile: top face (bright near edge), front face (thickness), glow, trail behind it."""
        ctx = self.canvas.ctx
        pts = self.quad(u0, u1, d0, d1)
        (xa, ya), (xb, yb) = pts[0], pts[2]
        tr = self.quad(u0 + 0.01, u1 - 0.01, d1, d1 + 3.0)            # light trail
        g = cairo.LinearGradient(0, tr[0][1], 0, tr[2][1])
        g.add_color_stop_rgba(0, *col, 0.28 * fog)
        g.add_color_stop_rgba(1, *col, 0.0)
        self.fill_poly(tr, g)
        gl = self.quad(u0 - 0.012, u1 + 0.012, d0 - 0.25, d1 + 0.25)  # glow
        self.fill_poly(gl, (*col, 0.22 * fog))
        g = cairo.LinearGradient(0, ya, 0, yb)
        hi = _mix(col, (1, 1, 1), 0.55)
        g.add_color_stop_rgba(0, *hi, 0.98 * fog)
        g.add_color_stop_rgba(1, *col, 0.80 * fog)
        self.fill_poly(pts, g)
        s = DEPTH / (DEPTH + max(d0, 0.0))
        thick = self.L.h * 0.010 * s                                  # front face
        self.fill_poly([pts[0], pts[1], (pts[1][0], pts[1][1] + thick), (pts[0][0], pts[0][1] + thick)],
                       (*_mix(col, (0, 0, 0), 0.45), 0.95 * fog))
        self.canvas.lines([(pts[0][0], pts[0][1], pts[1][0], pts[1][1])], (1, 1, 1), width=2.5 * s + 0.5,
                          alpha=0.9 * fog)

    def burst(self, x, y, age, col, seed, big=1.0, life=0.45):
        c, w = self.canvas, self.L.w
        if age < 0 or age > life:
            return
        u = age / life
        ctx = c.ctx
        ctx.save()
        ctx.translate(x, y)
        ctx.scale(1.0, 0.45)                                          # a ring lying on the road
        c.ring(0, 0, w * (0.03 + 0.10 * u) * big, col, width=6 * (1 - u) + 1, alpha=0.95 * (1 - u))
        ctx.restore()
        c.glow(x, y, w * 0.06 * big, col, strength=0.9 * (1 - u) ** 2, reach=2.4)
        segs = []
        for j in range(9):                                            # sparks fly up and out
            a = math.pi * (0.1 + 0.8 * ((seed * 0.618 + j / 9) % 1))
            r0, r1 = w * (0.01 + 0.10 * u) * big, w * (0.03 + 0.16 * u) * big
            segs.append((x + r0 * math.cos(a), y - r0 * math.sin(a) * 1.2 + w * 0.06 * u * u,
                         x + r1 * math.cos(a), y - r1 * math.sin(a) * 1.2 + w * 0.06 * u * u))
        c.lines(segs, _mix(col, (1, 1, 1), 0.4), width=3.5 * (1 - u) + 0.5, alpha=0.95 * (1 - u))

    def draw(self, f, rule):
        L, c = self.L, self.canvas
        w, h = L.w, L.h
        t = f * DT
        ctx = c.ctx
        ph = phase(t)
        sp = math.exp(K * (t % T_LOOP))
        sec = max(i for i in range(4) if SEC[i] <= ph)
        env = math.exp(-8 * ((ph / 4) % 1))                           # the 808 envelope, x in beats
        dk = (math.sin(math.pi * (ph - SEC[3]) / (TOTAL - SEC[3])) ** 0.7  # drop: sunset → neon night → sunset
              if ph >= SEC[3] else 0.0)                                 # (back to frame 0's sky at the seam)
        ctx.set_source_rgb(0.02, 0.01, 0.04)
        ctx.paint()
        ctx.save()
        if sec >= 3:                                                  # the drop: the world bumps on every 808
            zs = 1 + 0.014 * env
            ctx.translate(w / 2, self.yhit)
            ctx.scale(zs, zs)
            ctx.translate(-w / 2, -self.yhit)
        self.sky(t, ph, dk, env)
        # the road
        dbot = DEPTH * (self.yhit - self.hz) / (self.ybot - self.hz) - DEPTH
        road = self.quad(0, 1, dbot, DMAX)
        g = cairo.LinearGradient(0, self.hz, 0, self.ybot)
        g.add_color_stop_rgba(0, *_mix((0.35, 0.08, 0.30), (0.10, 0.10, 0.35), dk), 1.0)
        g.add_color_stop_rgba(0.25, 0.06, 0.03, 0.10, 1.0)
        g.add_color_stop_rgba(1, 0.03, 0.02, 0.06, 1.0)
        self.fill_poly(road, g)
        ctx.save()
        ctx.new_path()
        ctx.move_to(*road[0])
        for q in road[1:]:
            ctx.line_to(*q)
        ctx.close_path()
        ctx.clip()
        gl = []                                                       # cross lines scroll = speed
        for k in range(int(ph // 2) - 2, int(ph // 2) + 40):
            d = 2 * k - ph
            if dbot <= d <= DMAX:
                (xa, ya), (xb, yb) = self.P(0, d), self.P(1, d)
                gl.append((xa, ya, xb, yb))
        c.lines(gl, (0.9, 0.45, 1.0), width=1.6, alpha=0.16 + 0.10 * env)
        for i, u in enumerate(LANES):                                 # lane rails converge to the horizon
            (xa, ya), (xb, yb) = self.P(u, dbot), self.P(u, DMAX)
            edge = i in (0, len(LANES) - 1)
            col = (1.0, 0.45, 0.85) if edge else (0.6, 0.7, 1.0)
            c.lines([(xa, ya, xb, yb)], col, width=6 if edge else 2, alpha=0.75 if edge else 0.25)
            if edge:
                c.lines([(xa, ya, xb, yb)], col, width=18, alpha=0.12 + 0.1 * env)
        # lane flashes on hits (lane only = flash-safe)
        for wrap in (-TOTAL, 0):
            for (p0, d, m, col) in NOTES:
                age = (ph - (p0 + wrap)) / R0 / sp
                if 0 <= age < 0.3:
                    lu0, lu1 = LANES[col + 1], LANES[col + 2]
                    gq = self.quad(lu0, lu1, 0, DMAX)
                    gg = cairo.LinearGradient(0, self.yhit, 0, self.hz)
                    gg.add_color_stop_rgba(0, *COLCOL[col], 0.22 * (1 - age / 0.3))
                    gg.add_color_stop_rgba(1, *COLCOL[col], 0.0)
                    self.fill_poly(gq, gg)
        # tiles, far → near
        items = []
        for wrap in (-TOTAL, 0, TOTAL):
            for (p0, dur, m, col) in NOTES:
                d0 = p0 + wrap - ph
                if -dur < d0 < DMAX:
                    items.append((d0, "m", dur, col))
            for u in KICKS:
                d0 = u + wrap - ph
                if 0 < d0 < DMAX:
                    items.append((d0, "k", 2.6, 0))
            for u in HATS:
                d0 = u + wrap - ph
                if 0 < d0 < DMAX:
                    items.append((d0, "h", 1.4, 0))
        items.sort(key=lambda it: -it[0])
        contour = []
        for (d0, kind, dur, col) in items:
            fog = max(0.0, min(1.0, (DMAX - d0) / (DMAX * 0.55)))
            dn, df = max(0.0, d0), d0 + dur * 0.86
            if df <= dn + 0.02:
                continue
            if kind == "m":
                lu0, lu1 = LANES[col + 1] + 0.012, LANES[col + 2] - 0.012
                self.neon_slab(lu0, lu1, dn, df, COLCOL[col], fog)
                if d0 >= 0:
                    contour.append((d0, self.P((lu0 + lu1) / 2, dn)))
            elif kind == "k":                                         # 808 tile: the decay curve on its face
                lu0, lu1 = LANES[0] + 0.015, LANES[1] - 0.012
                self.fill_poly(self.quad(lu0, lu1, dn, df), (*GOLD, 0.16 * fog))
                cur = [self.P(lu0 + (lu1 - lu0) * j / 16, dn + (df - dn) * math.exp(-8 * j / 16)) for j in range(17)]
                c.polylines([cur], GOLD, width=3.5 * DEPTH / (DEPTH + dn), alpha=0.95 * fog)
            else:                                                     # hat tile: the floor(2x) staircase
                lu0, lu1 = LANES[5] + 0.012, LANES[6] - 0.015
                stp = [self.P(lu0, dn)]
                for j in range(3):
                    ua, ub = lu0 + (lu1 - lu0) * j / 3, lu0 + (lu1 - lu0) * (j + 1) / 3
                    dd = dn + (df - dn) * j / 2
                    stp += [self.P(ua, dd), self.P(ub, dd)]
                c.polylines([stp], CYAN, width=3.0 * DEPTH / (DEPTH + dn), alpha=0.95 * fog)
        if len(contour) > 1:                                          # the melody as a graph
            contour.sort()
            c.polylines([[p for _, p in contour[:24]]], (1, 1, 1), width=2.5, alpha=0.35)
        ctx.restore()
        # hit line, bursts, clap rings
        (xa, ya), (xb, yb) = self.P(0, 0), self.P(1, 0)
        c.lines([(xa, ya, xb, yb)], (0.5, 0.9, 1.0), width=16, alpha=0.18 + 0.2 * env)
        c.lines([(xa, ya, xb, yb)], (1, 1, 1), width=3.5, alpha=0.7 + 0.3 * env)
        for wrap in (-TOTAL, 0):
            for i, (p0, d, m, col) in enumerate(NOTES):
                age = (ph - (p0 + wrap)) / R0 / sp
                x, y = self.P((LANES[col + 1] + LANES[col + 2]) / 2, 0)
                self.burst(x, y, age, COLCOL[col], i)
            for u in KICKS:
                age = (ph - (u + wrap)) / R0 / sp
                x, y = self.P((LANES[0] + LANES[1]) / 2, 0)
                self.burst(x, y, age, GOLD, u, big=0.75)
            if sec >= 2 or wrap:
                for u in CLAPS:
                    age = (ph - (u + wrap)) / R0 / sp
                    if 0 <= age < 0.5:
                        ctx.save()
                        ctx.translate(w / 2, self.yhit)
                        ctx.scale(1.0, 0.4)
                        c.ring(0, 0, w * (0.08 + 0.45 * age), PINK, width=5, alpha=0.6 * (1 - age / 0.5))
                        ctx.restore()
        # the 808 graph across the road's near edge
        sy0, sy1 = self.yhit + h * 0.016, self.ybot - h * 0.008
        gp = [(w * 0.08 + w * 0.84 * j / 200,
               sy1 - (sy1 - sy0) * math.exp(-8 * ((ph / 4 - 2 + 4 * j / 200) % 1))) for j in range(201)]
        c.polylines([gp], GOLD, width=3, alpha=0.85)
        ctx.restore()
        # text: song, skyline, speed; footer = the layers, lit as they enter
        c.text_centered(TITLE, h * 0.200, size=h * 0.0135, color=GOLD, alpha=0.9)
        c.text_centered(f"speed = e^({K:.3f}·t) = ×{sp:.2f}", h * 0.226, size=w * 0.036, color=(1, 1, 1), alpha=0.95)
        for j, (name, eq, col) in enumerate(LAYERS):
            on = j <= sec
            a = 1.0 if on else 0.25
            if on and j == sec and j:
                a = 0.4 + 0.6 * smooth((ph - SEC[j]) / 3.0)
            c.text_centered(f"{name}:  {eq}", h * (0.74 + 0.026 * j), size=w * 0.031,
                            color=col if on else (0.55, 0.55, 0.65), alpha=a)
        if rule:
            c.caption(rule, alpha=1.0, layout=L)
        c.watermark(L)


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
    out = []
    for (p0, d, m, col) in NOTES:
        out.append({"t": round(t_of(p0) + 0.003, 4), "note": m, "gain": 0.40, "x": layout.w * (0.25 + 0.17 * col)})
    for u in range(4, TOTAL, 8):                                     # Mozart's left hand: a soft chord on beat 2
        r = ROOTS[(u // 8) % len(ROOTS)]
        ch = (57, 60, 64) if r == 45 else (56, 59, 64)
        for j, m in enumerate(ch):
            out.append({"t": round(t_of(u) + 0.01 * j, 4), "note": m, "gain": 0.12, "x": layout.w / 2})
    return out


def beat_bed():
    sr = audio.SR
    n = int(round(T_LOOP * sr))
    out = np.zeros(n)
    rng = np.random.default_rng(4)

    def add(t0, sig, g):
        i0 = int(t0 * sr) % n
        idx = (np.arange(len(sig)) + i0) % n
        np.add.at(out, idx, g * sig)

    tv = np.arange(int(0.42 * sr)) / sr
    for u in KICKS:
        f0 = audio.midi_to_hz(ROOTS[(u // 8) % len(ROOTS)] - 12)
        fr = f0 * (1 + 2.5 * np.exp(-tv / 0.012))
        sig = np.sin(2 * np.pi * np.cumsum(fr) / sr) * np.exp(-tv / 0.11)
        add(t_of(u), np.tanh(1.6 * sig), 0.55 if u < SEC[3] else 0.62)
    th = np.arange(int(0.05 * sr)) / sr
    for u in HATS:
        nz = np.diff(np.concatenate([[0], rng.standard_normal(len(th))]))
        add(t_of(u), nz * np.exp(-th / 0.012), 0.06 if (u // 2) % 2 else 0.04)
    tc = np.arange(int(0.18 * sr)) / sr
    for u in CLAPS:
        nz = rng.standard_normal(len(tc))
        env = np.exp(-tc / 0.05) * (1 + 0.6 * np.exp(-((tc - 0.012) / 0.004) ** 2))
        add(t_of(u), nz * env, 0.13)
    return (0.5 * out).astype(np.float32)


def _worker(o, sim, label, rule):
    layout = get_layout(o)
    name = f"{SCENE}_{label}_{layout.tag}"
    video = studio.OUT_DIR / f"{name}_silent.mp4"
    d = render(layout, sim, video, rule)
    kit.deliver_loop(SCENE, name, layout, video, build_events(sim, layout), d, voice="piano", bed=beat_bed(),
                     peak_db=-6.0)


def main():
    label, rule = arg("--label", "v1"), arg("--rule", "")
    studio.OUT_DIR.mkdir(exist_ok=True)
    sim = simulate()
    if kit.has("--still"):
        layout = get_layout(kit.orients()[0])
        f = int(arg("--frame", "0"))
        png = studio.OUT_DIR / f"{SCENE}_{label}_f{f}_{layout.tag}.png"
        render(layout, sim, png, rule, still_frame=f)
        print(f"[{SCENE}] -> {png}")
        return
    print(f"[{SCENE}] {SONG} {T_LOOP:.1f}s  {TOTAL} sixteenths  k={K:.4f}  end speed ×{math.exp(K * T_LOOP):.2f}")
    kit.fan_out(_worker, (sim, label, rule), SCENE)


if __name__ == "__main__":
    main()
