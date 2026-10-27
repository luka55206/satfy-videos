"""RICE — "Rice doubled on each chessboard square" (owner brief 2026-10-23; idea #8 in ideas/2026-10-22_short_ideas.txt).

Square k holds 2^(k-1) grains. Physical model (honest, stated in the docs): 25 mg per grain, bulk density 0.75 t/m³,
a cone pile at a 35° angle of repose -> height h = (V / 2.14)^(1/3). So square 32 is a 3 m heap, square 50 ~200 m,
square 56 ~820 m (Burj Khalifa), square 60 ~2 km, square 64 ~5.2 km (taller than Mont Blanc).
Whole board: 2^64 - 1 = 18,446,744,073,709,551,615 grains ≈ 461 billion tonnes ≈ 600 years of the world's rice
harvest (~780 Mt/yr). (The brief said "1,000 years"; the honest figure is ~600.)
  0-8 s   a glowing 3-D chessboard; the camera sweeps square to square: grains as grains, then a cup, a bag, a sack
  8-14 s  side view at true scale: the pile of each square grows (cube root of the volume), the camera rises,
          a person, a house, the Eiffel Tower, the Burj Khalifa and Mont Blanc appear for scale; shake + rumble
  14-18 s square 64: one flash, the total, the tonnes and the years — hard cut to the start
Audio (original synthesis): one note per square climbing the scale, turning into a rising rumble, a boom at 64.
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

SCENE = "rice"
GOLD, CREAM, CYAN, MAGENTA, WHITE = (1.0, 0.80, 0.35), (1.0, 0.95, 0.82), (0.30, 0.85, 1.0), (0.9, 0.4, 1.0), (1, 1, 1)
NAVY = (0.02, 0.025, 0.06)
FONT = "Consolas"
T_A, T_B, T_END = 8.0, 14.0, 18.0
GRAIN_G, BULK, K_CONE = 0.025, 0.75, 2.14

# when each square is reached: phase A squares 1..24 (slowing at first), phase B 25..63 accelerating, 64 at T_B
_dA = np.array([0.62 * 0.935 ** k for k in range(1, 24)])
_dA = _dA / _dA.sum() * (T_A - 1.2)
_dB = np.array([0.30 * 0.965 ** k for k in range(39)])
_dB = _dB / _dB.sum() * (T_B - T_A)
T_SQ = np.concatenate([[0.0, 1.2], 1.2 + np.cumsum(_dA)[:-1], [T_A], T_A + np.cumsum(_dB)[:-1], [T_B]])
assert len(T_SQ) == 64


def square_at(t):
    return int(np.searchsorted(T_SQ, t, side="right"))          # 1..64


def grains(k):
    return 2 ** (k - 1)


def tonnes(n):
    return n * GRAIN_G / 1e6


def pile_h(n):
    v = tonnes(n) / BULK
    return (v / K_CONE) ** (1 / 3)


UNITS = [(1, "1 grain"), (2, "2 grains"), (64, "a pinch"), (512, "a spoonful"), (8192, "a cup of rice"),
         (32768, "a bag (0.8 kg)"), (1048576, "a big sack (26 kg)"), (2 ** 26, "a car's weight"), (2 ** 30, "a truck"),
         (2 ** 37, "a freight train"), (2 ** 44, "a supertanker"), (2 ** 52, "a city's rice for 10 years"),
         (2 ** 58, "a whole country's harvest"), (2 ** 61, "the WORLD's harvest, 4 years")]


def unit_label(n):
    if n < 64:
        return "1 grain" if n == 1 else f"{n} grains"
    lab = UNITS[0][1]
    for th, s in UNITS:
        if n >= th:
            lab = s
    return lab


# scale references for the side view: (name, height m, x offset in pile heights, kind)
REFS = [("car", 1.5, "car"), ("person", 1.75, "person"), ("elephant", 3.3, "elephant"),
        ("giraffe", 5.5, "giraffe"), ("house", 10.0, "house"), ("10-storey building", 32.0, "building"),
        ("Statue of Liberty", 93.0, "statue"), ("Eiffel Tower", 330.0, "tower"), ("Burj Khalifa", 828.0, "spire"),
        ("Mount Fuji", 3776.0, "fuji"), ("Mont Blanc", 4808.0, "mountain")]
REF_W = {"car": 1.6, "person": 0.15, "elephant": 0.75, "giraffe": 0.45, "house": 0.5, "building": 0.3,
         "statue": 0.2, "tower": 0.22, "spire": 0.06, "fuji": 1.4, "mountain": 1.1}


class Scene:
    def __init__(self, layout):
        self.L = layout
        self.canvas = Canvas(layout.w, layout.h, studio.render_scale())
        rng = np.random.default_rng(9)
        self.gp = [rng.uniform(-0.38, 0.38, (min(grains(k), 300), 2)) for k in range(1, 12)]
        self.ga = [rng.uniform(0, math.pi, min(grains(k), 300)) for k in range(1, 12)]

    def mono(self, s, x, y, size, col, alpha=1.0, align="center", bold=True):
        ctx = self.canvas.ctx
        ctx.select_font_face(FONT, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD if bold else cairo.FONT_WEIGHT_NORMAL)
        ctx.set_font_size(size)
        ext = ctx.text_extents(s)
        if ext.x_advance > self.L.w * 0.94:
            ctx.set_font_size(size * self.L.w * 0.94 / ext.x_advance)
            ext = ctx.text_extents(s)
        if align == "center":
            x -= ext.x_advance / 2
        elif align == "right":
            x -= ext.x_advance
        ctx.set_source_rgba(0, 0, 0, 0.5 * alpha)
        ctx.move_to(x + 3, y + 3)
        ctx.show_text(s)
        ctx.set_source_rgba(*col, alpha)
        ctx.move_to(x, y)
        ctx.show_text(s)

    # --- phase A: the 3-D board --------------------------------------------------------------------
    @staticmethod
    def sq_xy(k):
        i = k - 1
        row, col = i // 8, i % 8
        if row % 2:
            col = 7 - col                                   # serpentine: the sweep never jumps
        return col - 3.5, row - 3.5

    def cam(self, t):
        k = square_at(t)
        u = 0.0
        if k < 64:
            t0, t1 = T_SQ[k - 1], T_SQ[k]
            u = smooth((t - t0) / max(t1 - t0, 1e-6))
        ax, az = self.sq_xy(k)
        bx, bz = self.sq_xy(min(64, k + 1))
        tx, tz = ax + (bx - ax) * u * 0.6, az + (bz - az) * u * 0.6
        pull = smooth(t / T_A)
        tx, tz = tx * (1 - 0.7 * pull), tz * (1 - 0.7 * pull)           # drift toward the board centre
        D = 1.6 + 9.5 * pull ** 1.3                                  # pulls back: from one grain to the board
        return tx, tz, D, math.radians(52 + 6 * pull), math.radians(-18 + 30 * pull)

    def proj(self, X, Y, Z, cam):
        w, h = self.L.w, self.L.h
        tx, tz, D, tilt, yaw = cam
        x, z = X - tx, Z - tz
        x, z = x * math.cos(yaw) - z * math.sin(yaw), x * math.sin(yaw) + z * math.cos(yaw)
        y = Y
        yc = y * math.cos(tilt) + z * math.sin(tilt)
        zc = -y * math.sin(tilt) + z * math.cos(tilt) + D
        f = w * 0.95
        zc = np.maximum(zc, 0.05)
        return w / 2 + f * x / zc, h * 0.47 - f * yc / zc, f / zc

    def board(self, t):
        c = self.canvas
        ctx = c.ctx
        cam = self.cam(t)
        kcur = square_at(t)
        for k in range(1, 65):
            sx, sz = self.sq_xy(k)
            xs = np.array([sx - 0.5, sx + 0.5, sx + 0.5, sx - 0.5])
            zs = np.array([sz - 0.5, sz - 0.5, sz + 0.5, sz + 0.5])
            px, py, _ = self.proj(xs, np.zeros(4), zs, cam)
            dark = (int(sx + 3.5) + int(sz + 3.5)) % 2 == 0
            col = (0.10, 0.12, 0.30) if dark else (0.22, 0.26, 0.55)
            pts = list(zip(px, py))
            c.poly(pts, col, alpha=0.95)
            lit = k == kcur
            c.polylines([pts + [pts[0]]], GOLD if lit else CYAN, width=4 if lit else 1.5, alpha=0.95 if lit else 0.35)
        # contents of every square reached so far
        for k in range(1, kcur + 1):
            sx, sz = self.sq_xy(k)
            n = grains(k)
            age = t - T_SQ[k - 1]
            pop = 1 + 0.4 * math.exp(-age / 0.12)
            cx, cy, sc = self.proj(np.array([sx]), np.array([0.0]), np.array([sz]), cam)
            cx, cy, sc = float(cx[0]), float(cy[0]), float(sc[0])
            if k <= 11:                                          # real grains (up to 1,024, max 300 drawn)
                gp, ga = self.gp[k - 1], self.ga[k - 1]
                gx, gy, gs = self.proj(sx + gp[:, 0], np.zeros(len(gp)), sz + gp[:, 1], cam)
                L_ = 0.11 if k == 1 else (0.06 if k < 6 else 0.035)
                for j in range(len(gp)):
                    ctx.save()
                    ctx.translate(gx[j], gy[j])
                    ctx.rotate(ga[j])
                    ctx.scale(1.0, 0.42)
                    ctx.new_sub_path()
                    ctx.arc(0, 0, max(1.0, gs[j] * L_ * pop), 0, 2 * math.pi)
                    ctx.restore()
                    ctx.set_source_rgba(*CREAM, 0.98)
                    ctx.fill()
                if k == 1:
                    c.glow(float(gx[0]), float(gy[0]), sc * 0.12, GOLD, strength=0.5, reach=2.2)
            else:                                                # a glowing heap, growing with the square
                hh = sc * (0.10 + 0.05 * (k - 11)) * pop
                ww = sc * 0.42
                c.glow(cx, cy - hh * 0.4, ww * 0.6, GOLD, strength=0.35, reach=1.8)
                c.poly([(cx - ww, cy), (cx, cy - hh), (cx + ww, cy)], GOLD, alpha=0.95)
                c.poly([(cx - ww * 0.35, cy - hh * 0.65), (cx, cy - hh), (cx + ww * 0.1, cy - hh * 0.7)], CREAM, alpha=0.8)

    # --- phase B/C: the side view at true scale ---------------------------------------------------
    def side(self, t):
        L, c = self.L, self.canvas
        w, h = L.w, L.h
        ctx = c.ctx
        k = min(64, square_at(t))
        kf = k
        if k < 64:
            u = (t - T_SQ[k - 1]) / max(T_SQ[k] - T_SQ[k - 1], 1e-6)
            kf = k - 1 + smooth(min(1.0, u * 1.6))
        H = pile_h(2 ** (kf - 1))                                  # metres, current square
        gy = h * 0.68
        ppm = (h * 0.15) / max(H, 0.05)                            # pixels per metre: the camera rises
        # sky glow by height
        g = cairo.LinearGradient(0, 0, 0, gy)
        alt = min(1.0, math.log10(max(H, 1)) / 4)
        g.add_color_stop_rgba(0, 0.02, 0.03, 0.10 + 0.1 * alt, 1)
        g.add_color_stop_rgba(1, 0.10 + 0.15 * alt, 0.12, 0.30, 1)
        ctx.rectangle(0, 0, w, gy)
        ctx.set_source(g)
        ctx.fill()
        ctx.rectangle(0, gy, w, h - gy)
        ctx.set_source_rgb(0.04, 0.05, 0.10)
        ctx.fill()
        c.lines([(0, gy, w, gy)], CYAN, width=3, alpha=0.6)
        px = w * 0.67
        # scale references on the left
        best = [r for r in REFS if r[1] <= H * 1.15] or REFS[:1]
        name_, hm_, kind_ = best[-1]                                # the biggest thing the pile has reached
        for name, hm, kind in [(name_, hm_, kind_)]:
            ph = hm * ppm
            hp_ = H * ppm
            wid = REF_W[kind] * ph
            rx = max(w * 0.13, px - hp_ * 1.43 - wid - w * 0.03)
            age = t - T_SQ[min(63, square_at(t)) - 1]
            a = 1.0
            col = (0.75, 0.82, 1.0)
            self.ref_icon(kind, rx, gy, ph, col, a)
            self.mono(f"{name} {hm:,.0f} m" if hm >= 10 else f"{name} {hm} m", max(rx, w * 0.29),
                      gy - ph - h * 0.012, h * 0.019, col, alpha=a)
        # previous squares' piles (each half the volume) to the right, then the current pile
        for j in range(3, 0, -1):
            hj = pile_h(2 ** max(0, kf - 1 - j)) * ppm
            xj = px + w * 0.06 * j + hj * 0.9
            c.poly([(xj - hj * 1.43, gy), (xj, gy - hj), (xj + hj * 1.43, gy)], GOLD, alpha=0.45)
        hp = H * ppm
        g2 = cairo.LinearGradient(0, gy - hp, 0, gy)
        g2.add_color_stop_rgba(0, 1.0, 0.92, 0.70, 1)
        g2.add_color_stop_rgba(1, 0.85, 0.62, 0.22, 1)
        ctx.new_path()
        ctx.move_to(px - hp * 1.43, gy)
        ctx.line_to(px, gy - hp)
        ctx.line_to(px + hp * 1.43, gy)
        ctx.close_path()
        ctx.set_source(g2)
        ctx.fill()
        c.glow(px, gy - hp * 0.5, hp * 0.5, GOLD, strength=0.25, reach=1.8)
        rng = np.random.default_rng(int(kf * 10))
        for _ in range(120):                                       # grain texture
            u, v = rng.random(), rng.random()
            yy = gy - hp * u
            half = (hp - (gy - yy)) * 1.43 * (1 - u) / max(1 - u, 1e-6) if u < 1 else 0
            xx = px + (v * 2 - 1) * hp * 1.43 * (1 - u)
            c.circle(xx, yy, 2.0, CREAM, alpha=0.5)
        self.mono(f"{H:,.0f} m tall" if H >= 10 else f"{H:,.1f} m tall", px, gy - hp - h * 0.015, h * 0.022, GOLD)

    def ref_icon(self, kind, x, gy, ph, col, a):
        """simple flat silhouettes, ph = height in pixels, standing on gy, centred on x"""
        c = self.canvas
        ctx = c.ctx
        P = lambda pts: c.poly([(x + u * ph, gy - v * ph) for u, v in pts], col, alpha=0.8 * a)   # noqa: E731
        if kind == "car":
            P([(-1.5, 0.25), (-1.5, 0.55), (-0.6, 0.62), (-0.3, 1.0), (0.6, 1.0), (0.95, 0.62), (1.5, 0.55), (1.5, 0.25)])
            for u in (-0.95, 0.95):
                c.circle(x + u * ph, gy - 0.22 * ph, 0.24 * ph, (0.25, 0.28, 0.4), alpha=a)
                c.circle(x + u * ph, gy - 0.22 * ph, 0.10 * ph, col, alpha=a)
        elif kind == "person":
            c.circle(x, gy - ph * 0.9, ph * 0.1, col, alpha=a)
            c.lines([(x, gy - ph * 0.8, x, gy - ph * 0.4), (x, gy - ph * 0.4, x - ph * 0.12, gy),
                     (x, gy - ph * 0.4, x + ph * 0.12, gy), (x, gy - ph * 0.72, x - ph * 0.15, gy - ph * 0.5),
                     (x, gy - ph * 0.72, x + ph * 0.15, gy - ph * 0.5)], col, width=max(1.5, ph * 0.05), alpha=a)
        elif kind == "elephant":
            ctx.save()
            ctx.translate(x, gy - ph * 0.55)
            ctx.scale(ph * 0.62, ph * 0.36)
            ctx.arc(0, 0, 1, 0, 2 * math.pi)
            ctx.restore()
            ctx.set_source_rgba(*col, 0.8 * a)
            ctx.fill()
            c.circle(x - ph * 0.62, gy - ph * 0.70, ph * 0.26, col, alpha=0.8 * a)                 # head
            c.lines([(x - ph * 0.82, gy - ph * 0.62, x - ph * 0.86, gy - ph * 0.05)], col, width=ph * 0.09, alpha=0.8 * a)
            for u in (-0.38, -0.12, 0.18, 0.42):
                ctx.rectangle(x + u * ph - ph * 0.07, gy - ph * 0.3, ph * 0.14, ph * 0.3)
                ctx.fill()
            c.circle(x - ph * 0.45, gy - ph * 0.72, ph * 0.16, (0.55, 0.6, 0.8), alpha=0.8 * a)       # ear
        elif kind == "giraffe":
            ctx.save()
            ctx.translate(x + ph * 0.1, gy - ph * 0.5)
            ctx.scale(ph * 0.26, ph * 0.12)
            ctx.arc(0, 0, 1, 0, 2 * math.pi)
            ctx.restore()
            ctx.set_source_rgba(*col, 0.8 * a)
            ctx.fill()
            c.lines([(x - ph * 0.08, gy - ph * 0.55, x - ph * 0.28, gy - ph * 0.95)], col, width=ph * 0.07, alpha=0.8 * a)
            c.poly([(x - ph * 0.40, gy - ph * 0.93), (x - ph * 0.22, gy - ph * 1.0), (x - ph * 0.22, gy - ph * 0.9)],
                   col, alpha=0.8 * a)
            for u in (-0.08, 0.02, 0.2, 0.3):
                c.lines([(x + u * ph, gy - ph * 0.45, x + u * ph, gy)], col, width=ph * 0.035, alpha=0.8 * a)
        elif kind == "house":
            P([(-0.5, 0), (-0.5, 0.6), (0, 1), (0.5, 0.6), (0.5, 0)])
        elif kind == "building":
            P([(-0.3, 0), (-0.3, 1), (0.3, 1), (0.3, 0)])
            for r in range(10):
                for cc in range(3):
                    ctx.rectangle(x + (-0.22 + 0.16 * cc) * ph, gy - (0.08 + 0.09 * r) * ph, 0.1 * ph, 0.05 * ph)
            ctx.set_source_rgba(1.0, 0.85, 0.45, 0.7 * a)
            ctx.fill()
        elif kind == "statue":
            P([(-0.2, 0), (-0.2, 0.32), (-0.12, 0.38), (0.12, 0.38), (0.2, 0.32), (0.2, 0)])           # pedestal
            P([(-0.07, 0.38), (-0.06, 0.82), (0.0, 0.88), (0.06, 0.82), (0.07, 0.38)])                   # figure
            c.lines([(x + 0.04 * ph, gy - 0.78 * ph, x + 0.08 * ph, gy - 0.98 * ph)], col, width=ph * 0.03, alpha=0.8 * a)
            c.circle(x + 0.08 * ph, gy - 1.0 * ph, ph * 0.03, (1.0, 0.85, 0.45), alpha=a)              # torch
        elif kind == "tower":
            P([(-0.22, 0), (0, 1), (0.22, 0), (0.12, 0), (0, 0.35), (-0.12, 0)])
        elif kind == "spire":
            P([(-0.06, 0), (-0.03, 0.7), (0, 1), (0.03, 0.7), (0.06, 0)])
        elif kind == "fuji":
            P([(-1.4, 0), (-0.25, 0.97), (0.25, 0.97), (1.4, 0)])
            c.poly([(x - 0.25 * ph, gy - 0.97 * ph), (x + 0.25 * ph, gy - 0.97 * ph), (x + 0.45 * ph, gy - 0.78 * ph),
                    (x + 0.2 * ph, gy - 0.84 * ph), (x, gy - 0.76 * ph), (x - 0.2 * ph, gy - 0.84 * ph),
                    (x - 0.45 * ph, gy - 0.78 * ph)], WHITE, alpha=0.9 * a)
        else:
            c.poly([(x - ph * 0.9, gy), (x - ph * 0.2, gy - ph * 0.85), (x, gy - ph), (x + ph * 0.5, gy - ph * 0.6),
                    (x + ph * 1.1, gy)], (0.45, 0.5, 0.65), alpha=0.85 * a)
            c.poly([(x - ph * 0.2, gy - ph * 0.85), (x, gy - ph), (x + ph * 0.2, gy - ph * 0.88), (x, gy - ph * 0.8)],
                   WHITE, alpha=0.9 * a)

    def header(self, t):
        c, L = self.canvas, self.L
        w, h = L.w, L.h
        k = min(64, square_at(t))
        n = grains(k)
        pop = 1 + 0.25 * math.exp(-(t - T_SQ[k - 1]) / 0.1)
        self.mono(f"SQUARE {k}", w / 2, h * 0.095, h * 0.030, (0.8, 0.85, 1.0))
        txt = f"{n:,}"
        self.mono(txt, w / 2, h * 0.16, h * (0.075 if len(txt) < 12 else (0.05 if len(txt) < 20 else 0.038)) * pop, GOLD)
        self.mono("GRAIN" if n == 1 else "GRAINS", w / 2, h * 0.195, h * 0.024, (0.8, 0.85, 1.0), bold=False)
        self.mono(unit_label(n), w / 2, h * 0.735, h * 0.030, CREAM)

    def draw(self, f):
        L, c = self.L, self.canvas
        w, h = L.w, L.h
        t = f * DT
        ctx = c.ctx
        ctx.set_source_rgb(*NAVY)
        ctx.paint()
        shake = 0.0
        if t > 9.0:
            shake = 3 + 22 * smooth((t - 9.0) / 5.0)
        if t >= T_B:
            shake = 40 * math.exp(-(t - T_B) / 0.5)
        ctx.save()
        ctx.translate(shake * math.sin(t * 57), shake * math.sin(t * 43 + 1))
        if t < T_A + 0.5:
            self.board(min(t, T_A))
        if t >= T_A:
            a = smooth((t - T_A) / 0.5)
            ctx.push_group()
            self.side(t)
            ctx.pop_group_to_source()
            ctx.paint_with_alpha(a)
        ctx.restore()
        if t < T_B:
            self.header(t)
        else:                                                    # square 64: the total
            fl = max(0.0, 1 - (t - T_B) / 0.35)
            ctx.set_source_rgba(1, 1, 1, fl)
            ctx.paint()
            a = smooth((t - T_B - 0.25) / 0.4)
            ctx.set_source_rgba(0, 0, 0, 0.55 * a)
            ctx.rectangle(0, h * 0.06, w, h * 0.24)
            ctx.fill()
            self.mono("SQUARE 64 · THE WHOLE BOARD", w / 2, h * 0.10, h * 0.024, (0.85, 0.9, 1.0), alpha=a)
            self.mono("18,446,744,073,709,551,615", w / 2, h * 0.16, h * 0.042, GOLD, alpha=a)
            self.mono("GRAINS OF RICE", w / 2, h * 0.195, h * 0.024, (0.85, 0.9, 1.0), alpha=a, bold=False)
            b = smooth((t - T_B - 1.0) / 0.5)
            self.mono("≈ 461 billion tonnes", w / 2, h * 0.245, h * 0.030, CREAM, alpha=b)
            self.mono("≈ 600 years of the WORLD's rice harvest", w / 2, h * 0.28, h * 0.024, CREAM, alpha=b)
        c.watermark(L)


def render(layout, out_path, still_frame=None):
    sc = Scene(layout)
    writer = None if still_frame is not None else VideoWriter(out_path, sc.canvas, FPS)
    nf = int(round(T_END * FPS))
    for f in range(nf):
        if still_frame is not None and f != still_frame:
            continue
        sc.draw(f)
        if writer is None:
            studio.save_still(sc.canvas, out_path)
            return f / FPS
        writer.write_frame()
    writer.close()
    return nf / FPS


SR = audio.SR


def build_bed():
    n = int(round(T_END * SR))
    t = np.arange(n) / SR
    buf = np.zeros(n + 2 * SR)
    major = [0, 2, 4, 5, 7, 9, 11]
    for k in range(1, 64):                                       # one note per square, climbing the scale
        deg = k - 1
        m = 48 + 12 * (deg // 7) + major[deg % 7]
        m = 48 + (m - 48) % 48                                   # wrap after 4 octaves (stays musical)
        f0 = audio.midi_to_hz(m)
        dur = 0.6
        tv = np.arange(int(dur * SR)) / SR
        s = (np.sin(2 * np.pi * f0 * tv) + 0.4 * np.sin(4 * np.pi * f0 * tv) + 0.15 * np.sin(6 * np.pi * f0 * tv))
        s *= np.exp(-tv / (0.25 if k < 25 else 0.12))
        g = 0.22 if k < 25 else 0.16
        j = int(T_SQ[k - 1] * SR)
        buf[j:j + len(s)] += g * s
    rng = np.random.default_rng(5)                               # the rumble: low filtered noise, rising
    noise = rng.standard_normal(n)
    from scipy.signal import butter, sosfilt
    rum = sosfilt(butter(2, 90, fs=SR, output="sos"), noise)
    rum = rum / (np.max(np.abs(rum)) or 1) * 3.0
    env = np.clip((t - 9.0) / 5.0, 0, 1) ** 1.6 * (t < T_B)
    buf[:n] += 0.5 * rum * env + 0.15 * np.sin(2 * np.pi * 41 * t) * env
    j = int(T_B * SR)                                            # square 64: boom + a wide chord
    tb = np.arange(int(3.5 * SR)) / SR
    boom = np.sin(2 * np.pi * np.cumsum(30 + 120 * np.exp(-tb / 0.08)) / SR) * np.exp(-tb / 0.9)
    buf[j:j + len(tb)] += 1.0 * boom
    for m in (36, 48, 55, 60, 64, 67, 72):
        s = np.sin(2 * np.pi * audio.midi_to_hz(m) * tb) * np.exp(-tb / 1.6) * np.minimum(1, tb / 0.05)
        buf[j:j + len(tb)] += 0.08 * s
    out = buf[:n]
    out[-int(0.08 * SR):] *= np.linspace(1, 0, int(0.08 * SR))   # quiet at the hard cut
    return (0.6 * out).astype(np.float32)


def main():
    label = arg("--label", "v1")
    studio.OUT_DIR.mkdir(exist_ok=True)
    layout = get_layout("vertical")
    print(f"[{SCENE}] piles: sq32 {pile_h(grains(32)):.1f} m, sq50 {pile_h(grains(50)):.0f} m, "
          f"sq56 {pile_h(grains(56)):.0f} m, sq60 {pile_h(grains(60)):.0f} m, sq64 {pile_h(grains(64)):.0f} m; "
          f"total {tonnes(2 ** 64 - 1) / 1e9:.0f} Gt")
    if kit.has("--still"):
        f = int(arg("--frame", "0"))
        png = studio.OUT_DIR / f"{SCENE}_{label}_f{f}_{layout.tag}.png"
        render(layout, png, still_frame=f)
        print(f"[{SCENE}] -> {png}")
        return
    name = f"{SCENE}_{label}_{layout.tag}"
    video = studio.OUT_DIR / f"{name}_silent.mp4"
    d = render(layout, video)
    kit.deliver_loop(SCENE, name, layout, video, [], d, voice="glassharp", bed=build_bed(), peak_db=-6.0)


if __name__ == "__main__":
    main()
