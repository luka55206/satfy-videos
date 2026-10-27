"""PARADOX: THE COASTLINE v2 — dive into a coast with a shrinking ruler: 2,400 km … 160,000 km.

An endless fractal coastline (recursive midpoint displacement, refined on demand so every zoom level has new
detail). The camera dives from the whole island to a bay, a beach, rocks and pebbles, into one point of the coast;
at each level a ruler walks the local coast and the measured length jumps. Numbers: Britain's coast behaves like a
fractal of dimension D ≈ 1.25 (Richardson / Mandelbrot), so L(r) = 2,400 km × (200 km / r)^0.25:
200 km -> 2,400 · 50 km -> 3,394 (Britain's real 3,400) · 1 km -> 9,025 · 10 m -> 28,540 · 1 cm -> 160,500 km
(4 times around the Earth). Then a fast zoom back out to the island (loop).
Audio (original, lib/sfx): a deepening whoosh on every dive, a hit on every new number, ruler ticks, a pad.
"""
import math
import sys
from pathlib import Path

import cairo
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib import kit, sfx, studio  # noqa: E402
from lib.kit import DT, FPS, arg, smooth  # noqa: E402
from lib.layouts import get_layout  # noqa: E402
from lib.studio import Canvas, VideoWriter  # noqa: E402

SCENE = "paradox_coast2"
T_LOOP = 17.0
GOLD, WHITE, CYAN = (1.0, 0.82, 0.35), (0.96, 0.97, 1.0), (0.35, 0.88, 1.0)
AMP = 0.24
LEVELS = [(200.0, "200 km"), (50.0, "50 km"), (1.0, "1 km"), (0.01, "10 m"), (1e-5, "1 cm")]
LEN = [2400.0 * (200.0 / r) ** 0.25 for r, _ in LEVELS]
T_LV = [0.0, 2.4, 5.0, 7.6, 10.2]            # each level starts (zoom 0.9 s, then the ruler walks)
ZOOM_D = 0.9
T_PUNCH, T_OUT0, T_OUT1 = 12.8, 15.0, 16.4
COLS = [(1.0, 0.82, 0.35), (1.0, 0.55, 0.30), (1.0, 0.40, 0.65), (0.70, 0.50, 1.0), (0.40, 1.0, 0.6)]


def hrand(i, salt=0):
    h = (i * 2654435761 + salt * 40503 + 12345) & 0xFFFFFFFF
    h ^= h >> 15
    h = (h * 2246822519) & 0xFFFFFFFF
    h ^= h >> 13
    return (h / 4294967295.0) * 2 - 1


rng0 = np.random.default_rng(21)
_n = 14
_ang = np.linspace(0, 2 * math.pi, _n, endpoint=False)
_rad = 340 * (1 + 0.28 * rng0.standard_normal(_n))
BASE = [(float(r * math.cos(a) * 1.15), float(r * math.sin(a))) for r, a in zip(_rad, _ang)]


def child(a, b, sid):
    L = math.hypot(b[0] - a[0], b[1] - a[1])
    nx, ny = -(b[1] - a[1]) / (L + 1e-30), (b[0] - a[0]) / (L + 1e-30)
    d = AMP * L * hrand(sid)
    return ((a[0] + b[0]) / 2 + nx * d, (a[1] + b[1]) / 2 + ny * d)


def focus_point():
    """a point exactly on the limit curve: descend 60 levels along a fixed path from base segment 4."""
    a, b, sid = BASE[4], BASE[5], 5
    for k in range(60):
        m = child(a, b, sid)
        if (k * 7 + 3) % 5 < 2:
            a, b, sid = a, m, 2 * sid
        else:
            a, b, sid = m, b, 2 * sid + 1
    return ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)


Q = focus_point()
C0 = (sum(p[0] for p in BASE) / _n, sum(p[1] for p in BASE) / _n)


def scale_at(t, w):
    """px per km: the island, then each level's zoom, then back out."""
    S0 = w * 0.85 / 800.0
    targets = [S0] + [w * 0.16 / r for r, _ in LEVELS[1:]]
    if t >= T_OUT0:
        u = smooth(min(1.0, (t - T_OUT0) / (T_OUT1 - T_OUT0)))
        return math.exp(math.log(targets[-1]) + (math.log(S0) - math.log(targets[-1])) * u)
    k = max(i for i in range(len(T_LV)) if t >= T_LV[i])
    if k == 0:
        return S0
    u = smooth(min(1.0, (t - T_LV[k]) / ZOOM_D))
    return math.exp(math.log(targets[k - 1]) + (math.log(targets[k]) - math.log(targets[k - 1])) * u)


class Scene:
    def __init__(self, layout):
        self.L = layout
        self.canvas = Canvas(layout.w, layout.h, studio.render_scale())

    def coast(self, S, cen):
        """closed polyline (world km), refined where it is on screen and longer than ~3 px."""
        w, h = self.L.w, self.L.h
        hw, hh = w / 2 / S * 1.2, h / 2 / S * 1.2
        x0, x1, y0, y1 = cen[0] - hw, cen[0] + hw, cen[1] - hh, cen[1] + hh
        out = []

        def rec(a, b, sid, depth):
            L = math.hypot(b[0] - a[0], b[1] - a[1])
            if L * S < 3.0 or depth > 70:
                out.append(a)
                return
            m = L * 0.7
            if max(a[0], b[0]) + m < x0 or min(a[0], b[0]) - m > x1 or max(a[1], b[1]) + m < y0 or min(a[1], b[1]) - m > y1:
                out.append(a)
                return
            c = child(a, b, sid)
            rec(a, c, 2 * sid, depth + 1)
            rec(c, b, 2 * sid + 1, depth + 1)
        for i in range(_n):
            rec(BASE[i], BASE[(i + 1) % _n], i + 1, 0)
        return out

    def draw(self, f, rule):
        L, c = self.L, self.canvas
        w, h = L.w, L.h
        t = f * DT
        ctx = c.ctx
        S = scale_at(t, w)
        S0 = w * 0.85 / 800.0
        k_ = max(0.0, 1.0 - math.log(max(1.0, S / S0)) / math.log(3.0))   # locks onto Q by the first zoom
        cen = (Q[0] + (C0[0] - Q[0]) * k_, Q[1] + (C0[1] - Q[1]) * k_)
        sx, sy = w / 2, h * 0.47

        def P(p):
            return sx + (p[0] - cen[0]) * S, sy - (p[1] - cen[1]) * S
        depth = math.log10(S / S0)                               # 0 island … ~7 pebbles
        # water
        g = cairo.LinearGradient(0, 0, 0, h)
        g.add_color_stop_rgb(0, 0.03, 0.10, 0.22)
        g.add_color_stop_rgb(1, 0.01, 0.04, 0.10)
        ctx.set_source(g)
        ctx.paint()
        for k in range(14):                                       # wave glints (screen space, periodic)
            ph = (t / T_LOOP * 4 + k / 14) % 1.0
            y = h * ((k * 0.137) % 1.0)
            c.lines([(w * ((k * 0.61) % 1.0) - 30, y, w * ((k * 0.61) % 1.0) + 30, y)], (0.5, 0.75, 1.0), width=2,
                    alpha=0.12 * math.sin(math.pi * ph))
        pts = self.coast(S, cen)
        sp = [P(p) for p in pts]
        land = [(0.10, 0.28, 0.17), (0.36, 0.31, 0.21), (0.24, 0.24, 0.27)]   # dark: no big flashes as the coast sweeps
        lk = min(2.0, max(0.0, (depth - 2.5) / 2.0))
        i0 = int(lk)
        col = tuple(land[i0][q] + (land[min(2, i0 + 1)][q] - land[i0][q]) * (lk - i0) for q in range(3))
        ctx.new_path()
        ctx.move_to(*sp[0])
        for p in sp[1:]:
            ctx.line_to(*p)
        ctx.close_path()
        ctx.set_source_rgb(*col)
        ctx.fill_preserve()
        ctx.save()
        ctx.clip()
        rng = np.random.default_rng(1)                               # texture: fixed in screen space (no flicker)
        for k in range(220):
            x, y = rng.random() * w, rng.random() * h
            rr = 2 + 6 * rng.random() * (1 + lk)
            c.circle(x, y, rr, tuple(min(1, v + 0.08 * (rng.random() - 0.3)) for v in col), alpha=0.5)
        ctx.restore()
        c.polylines([sp + [sp[0]]], (0.95, 0.92, 0.80), width=8, alpha=0.25)    # surf
        c.polylines([sp + [sp[0]]], (0.95, 0.95, 1.0), width=2.2, alpha=0.9)
        # the ruler on this level: walk the local coast around Q
        lv = max(i for i in range(len(T_LV)) if t >= T_LV[i]) if t < T_OUT0 else None
        if lv is not None:
            r_km = LEVELS[lv][0]
            walk_t0 = T_LV[lv] + (ZOOM_D if lv > 0 else 0.1)
            nseg_show = int(max(0.0, (t - walk_t0) / 0.12))
            if nseg_show > 0:
                qi = min(range(len(pts)), key=lambda i: (pts[i][0] - Q[0]) ** 2 + (pts[i][1] - Q[1]) ** 2)
                verts = [pts[qi]]
                cur, i = pts[qi], qi
                for _ in range(min(nseg_show, 40)):              # forward along the coast
                    j = i
                    while True:
                        j = (j + 1) % len(pts)
                        if j == qi or math.hypot(pts[j][0] - cur[0], pts[j][1] - cur[1]) >= r_km:
                            break
                    if j == qi:
                        break
                    cur, i = pts[j], j
                    verts.append(cur)
                    sx_, sy_ = P(cur)
                    if not (-w * 0.2 < sx_ < w * 1.2 and -h * 0.2 < sy_ < h * 1.2):
                        break
                vs = [P(v) for v in verts]
                if len(vs) > 1:
                    c.polylines([vs], COLS[lv], width=11, alpha=0.25)
                    c.polylines([vs], COLS[lv], width=4.5, alpha=1.0)
                    for p in vs:
                        c.circle(p[0], p[1], 5, WHITE, alpha=0.95)
        # numbers
        if t < T_OUT0:
            k = max(i for i in range(len(T_LV)) if t >= T_LV[i])
            land_t = T_LV[k] + (ZOOM_D if k > 0 else 0.0)
            pop = 1 + 0.35 * math.exp(-max(0.0, t - land_t) / 0.12) if (t >= land_t and k > 0) else 1.0
            shown = LEN[k] if t >= land_t else LEN[k - 1]
            if t >= T_PUNCH:
                c.text_centered(f"{LEN[-1]:,.0f} km", h * 0.235, size=w * 0.12, color=GOLD)
                c.text_centered("= 4 times around the EARTH", h * 0.75, size=w * 0.058, color=WHITE)
                c.text_centered("(a fractal coast like Britain's, D ≈ 1.25)", h * 0.79, size=w * 0.034,
                                color=(0.75, 0.8, 0.95), bold=False)
            else:
                c.text_centered(f"{shown:,.0f} km", h * 0.235, size=w * 0.12 * pop, color=COLS[k] if t >= land_t else WHITE)
                c.text_centered(f"ruler: {LEVELS[k][1]}", h * 0.75, size=w * 0.06, color=COLS[k])
                if k == 0:
                    c.text_centered("a coastline, measured with a 200 km ruler", h * 0.79, size=w * 0.036,
                                    color=(0.8, 0.85, 0.95), bold=False)
        else:
            c.text_centered(f"{LEN[0]:,.0f} km", h * 0.235, size=w * 0.12, color=COLS[0])
            c.text_centered("ruler: 200 km", h * 0.75, size=w * 0.06, color=COLS[0])
            c.text_centered("a coastline, measured with a 200 km ruler", h * 0.79, size=w * 0.036,
                            color=(0.8, 0.85, 0.95), bold=False)
        if rule:
            c.caption(rule, alpha=1.0, layout=L)
        c.watermark(L)


def render(layout, out_path, rule, still_frame=None):
    sc = Scene(layout)
    writer = None if still_frame is not None else VideoWriter(out_path, sc.canvas, FPS)
    nf = int(round(T_LOOP * FPS))
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


def sound():
    b = sfx.Bed(T_LOOP, seed=13)
    beat = 60 / 100
    b.pad([(0.0, (45, 52, 57, 64)), (T_LV[2], (41, 48, 57, 60)), (T_LV[4], (43, 50, 55, 62)),
           (T_PUNCH, (45, 52, 57, 64))], beat, g=0.05)
    b.pulse(0.0, T_LOOP, beat, [69, 76, 72, 79], 0.02)
    for k in range(1, len(T_LV)):
        b.whoosh(T_LV[k], ZOOM_D + 0.2, 0.10 + 0.01 * k)
        b.hit(T_LV[k] + ZOOM_D, 0.35 + 0.05 * k, low=60 - 4 * k)
        for q in range(10):
            b.tick(T_LV[k] + ZOOM_D + 0.12 * (q + 1), 2600 + 120 * k, 0.03)
    for q in range(10):
        b.tick(0.1 + 0.12 * (q + 1), 2600, 0.03)
    b.riser(T_PUNCH - 0.8, 0.8, 0.06)
    b.hit(T_PUNCH, 0.55)
    b.chime(T_PUNCH + 0.02, (79, 84, 88, 91), 0.08)
    b.whoosh(T_OUT0, T_OUT1 - T_OUT0, 0.12, up=False)
    return b.get()


def main():
    label, rule = arg("--label", "v1"), arg("--rule", "")
    studio.OUT_DIR.mkdir(exist_ok=True)
    layout = get_layout(kit.orients()[0])
    print(f"[{SCENE}] lengths: " + ", ".join(f"{n}: {v:,.0f} km" for (r, n), v in zip(LEVELS, LEN)))
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
