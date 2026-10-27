"""PARADOX: THE COASTLINE — measure an island's coast with a shorter ruler and the coast gets LONGER.

A seeded fractal island (midpoint displacement, scaled to 800 km across). A ruler walks around the coast (the divider
method) with 200, 100, 50, then 25 km steps; each pass draws its polygon in its own colour, and the count × ruler is
the measured coast. The numbers are measured here, on this island. Then the real-world fact: Britain measures about
2,400 km with a 200 km ruler and about 3,400 km with a 50 km ruler (Richardson's data, made famous by Mandelbrot).
Loop: the four ruler polygons rewind off the coast back to frame 0.
Audio (original): a soft tick per ruler step (higher each pass), a chime when a pass closes, a chord on the verdict,
a falling sweep on the rewind, a loop pad.
"""
import math
import sys
from pathlib import Path

import cairo
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib import kit, studio  # noqa: E402
from lib.kit import DT, FPS, arg, smooth  # noqa: E402
from lib.layouts import get_layout  # noqa: E402
from lib.studio import Canvas, VideoWriter  # noqa: E402

SCENE = "paradox_coast"
T_LOOP = 18.0
RULERS = [200.0, 100.0, 50.0, 25.0]
PASS_T = [(0.3, 3.3), (3.5, 6.5), (6.7, 9.7), (9.9, 12.9)]
T_VERD, T_RW0, T_RW1 = 13.1, 16.4, 17.5
COLS = [(1.0, 0.82, 0.35), (1.0, 0.55, 0.30), (1.0, 0.40, 0.65), (0.70, 0.50, 1.0)]
CYAN, WHITE, GREEN = (0.35, 0.88, 1.0), (0.95, 0.96, 1.0), (0.45, 1.0, 0.6)


def island(seed=4):
    rng = np.random.default_rng(seed)
    n0 = 10
    ang = np.linspace(0, 2 * np.pi, n0, endpoint=False)
    rad = 1 + 0.35 * rng.standard_normal(n0)
    pts = np.stack([rad * np.cos(ang) * 1.25, rad * np.sin(ang)], 1)
    amp = 0.30
    for _ in range(9):                                     # midpoint displacement, normal to each edge
        nxt = np.roll(pts, -1, axis=0)
        mid = (pts + nxt) / 2
        d = nxt - pts
        nrm = np.stack([-d[:, 1], d[:, 0]], 1)
        L = np.linalg.norm(d, axis=1, keepdims=True) + 1e-12
        mid = mid + nrm / L * (rng.standard_normal((len(pts), 1)) * amp * L)
        out = np.empty((len(pts) * 2, 2))
        out[0::2], out[1::2] = pts, mid
        pts = out
        amp *= 0.92
    span = pts[:, 0].max() - pts[:, 0].min()
    pts = (pts - pts.mean(0)) / span * 800.0               # km, 800 km across
    return pts


COAST = island()


def divider(pts, r):
    """walk a ruler of length r around the closed polyline; return the vertices and the measured length."""
    n = len(pts)
    P = np.vstack([pts, pts[:1]])
    cur = P[0].copy()
    verts = [cur.copy()]
    i = 0
    while True:
        found = False
        while i < n:
            a, b = P[i], P[i + 1]
            if np.linalg.norm(b - cur) >= r:              # the circle |p - cur| = r crosses segment a-b
                d = b - a
                f = a - cur
                A, B, C = d @ d, 2 * (f @ d), f @ f - r * r
                disc = max(0.0, B * B - 4 * A * C)
                s = (-B + math.sqrt(disc)) / (2 * A)
                cur = a + d * min(1.0, max(0.0, s))
                verts.append(cur.copy())
                found = True
                break
            i += 1
        if not found:
            break
    rest = np.linalg.norm(P[0] - cur)
    verts.append(P[0].copy())
    steps = len(verts) - 2
    return np.array(verts), steps * r + rest, steps


MEAS = [divider(COAST, r) for r in RULERS]


class Scene:
    def __init__(self, layout):
        self.L = layout
        self.canvas = Canvas(layout.w, layout.h, studio.render_scale())
        w, h = layout.w, layout.h
        span_y = COAST[:, 1].max() - COAST[:, 1].min()
        self.k = min(w * 0.88 / 800.0, h * 0.40 / span_y)
        self.cx, self.cy = w * 0.5, h * 0.43

    def S(self, p):
        return self.cx + p[0] * self.k, self.cy - p[1] * self.k

    def draw(self, f, rule):
        L, c = self.L, self.canvas
        w, h = L.w, L.h
        t = f * DT
        ctx = c.ctx
        g = cairo.RadialGradient(w / 2, h * 0.43, 0, w / 2, h * 0.43, h * 0.7)
        g.add_color_stop_rgb(0, 0.04, 0.08, 0.16)
        g.add_color_stop_rgb(1, 0.005, 0.01, 0.03)
        ctx.set_source(g)
        ctx.paint()
        for k in range(5):                                  # soft sea rings (periodic over the loop)
            rr = ((t / T_LOOP * 3 + k / 5) % 1.0)
            c.ring(self.cx, self.cy, w * (0.45 + 0.35 * rr), (0.3, 0.5, 0.9), width=2, alpha=0.10 * (1 - rr))
        # the island
        sp = [self.S(p) for p in COAST]
        ctx.new_path()
        ctx.move_to(*sp[0])
        for p in sp[1:]:
            ctx.line_to(*p)
        ctx.close_path()
        gi = cairo.RadialGradient(self.cx, self.cy, 0, self.cx, self.cy, w * 0.45)
        gi.add_color_stop_rgb(0, 0.10, 0.30, 0.22)
        gi.add_color_stop_rgb(1, 0.05, 0.16, 0.14)
        ctx.set_source(gi)
        ctx.fill()
        c.polylines([sp + [sp[0]]], CYAN, width=7, alpha=0.18)
        c.polylines([sp + [sp[0]]], CYAN, width=1.6, alpha=0.9)
        # the ruler passes
        rw = 0.0 if t < T_RW0 else smooth(min(1.0, (t - T_RW0) / (T_RW1 - T_RW0)))
        cur_pass, shown_txt = None, None
        for j, ((t0, t1), (verts, length, steps), r) in enumerate(zip(PASS_T, MEAS, RULERS)):
            if t < t0:
                continue
            prog = min(1.0, (t - t0) / (t1 - t0)) * (1 - rw)
            nv = prog * (len(verts) - 1)
            k = int(nv)
            if k < 1 and nv <= 0:
                continue
            pts = [self.S(v) for v in verts[:k + 1]]
            if k < len(verts) - 1:
                a, b = verts[k], verts[k + 1]
                fr = nv - k
                pts.append(self.S(a + (b - a) * fr))
            active = t0 <= t < t1 + 0.3 and rw == 0
            al = 1.0 if active else 0.45
            c.polylines([pts], COLS[j], width=9 if active else 4, alpha=0.18 * al)
            c.polylines([pts], COLS[j], width=3.2 if active else 2.0, alpha=0.95 * al)
            if active:
                for p in pts[:-1]:
                    c.circle(p[0], p[1], 3.5, COLS[j], alpha=0.9)
                ex, ey = pts[-1]                             # the ruler itself, glowing
                if len(pts) >= 2:
                    sx, sy = pts[-2]
                    c.lines([(sx, sy, ex, ey)], WHITE, width=5, alpha=0.9)
                c.glow(ex, ey, w * 0.02, COLS[j], strength=0.7, reach=2.2)
                cur_pass = j
                done = min(steps, int(prog * (len(verts) - 1)))
                shown_txt = (r, done, done * r if prog < 1 else length)
        # the HUD
        y0 = h * 0.655
        if cur_pass is not None:
            r, n_, tot = shown_txt
            c.text_centered(f"RULER: {r:.0f} km", y0, size=w * 0.07, color=COLS[cur_pass])
            c.text_centered(f"coast ≈ {tot:,.0f} km", y0 + h * 0.045, size=w * 0.06, color=WHITE)
        # the results so far, small, left to right
        for j, ((t0, t1), (verts, length, steps), r) in enumerate(zip(PASS_T, MEAS, RULERS)):
            if t >= t1 and rw < 0.5:
                x = w * (0.14 + 0.24 * j)
                bar = length / MEAS[-1][1]
                yb = h * 0.795
                ctx.rectangle(x - w * 0.06, yb - h * 0.07 * bar, w * 0.12, h * 0.07 * bar)
                ctx.set_source_rgba(*COLS[j], 0.85)
                ctx.fill()
                c.text_centered(f"{length:,.0f}", yb - h * 0.07 * bar - h * 0.008, size=w * 0.036, color=WHITE, cx=x)
                c.text_centered(f"{r:.0f} km", yb + h * 0.022, size=w * 0.032, color=COLS[j], cx=x, bold=False)
        if T_VERD <= t < T_RW0 + 0.3:
            k = smooth(min(1.0, (t - T_VERD) / 0.4)) * (1 - rw)
            c.text_centered("Shorter ruler → LONGER coast", y0, size=w * 0.066, color=GREEN, alpha=k)
            k2 = smooth(min(1.0, (t - T_VERD - 1.2) / 0.4)) * (1 - rw) if t >= T_VERD + 1.2 else 0.0
            c.text_centered("It never settles on one number.", y0 + h * 0.04, size=w * 0.045, color=WHITE,
                            alpha=k * (1 - k2), bold=False)
            c.text_centered("Real Britain: 2,400 km (200 km ruler) → 3,400 km (50 km)", y0 + h * 0.04,
                            size=w * 0.04, color=(1.0, 0.82, 0.4), alpha=k2, max_w=w * 0.94)
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


def build_events(layout):
    w = layout.w
    ev = []
    PENT = [0, 2, 4, 7, 9]
    for j, ((t0, t1), (verts, length, steps)) in enumerate(zip(PASS_T, MEAS)):
        n = len(verts) - 1
        last = -1.0
        for s in range(n):
            t = t0 + (t1 - t0) * (s + 1) / n
            if t - last < 0.09:                               # cap the tick rate
                continue
            last = t
            ev.append({"t": round(t, 4), "note": 60 + 12 * (j // 2) + PENT[(s + 2 * j) % 5], "gain": 0.18 + 0.03 * j,
                       "x": w * (0.3 + 0.4 * (s % 7) / 7)})
        for q, m in enumerate((79, 84)):
            ev.append({"t": round(t1 + 0.04 * q, 4), "note": m + j, "gain": 0.3, "x": w / 2})
    for q, m in enumerate((48, 55, 60, 64, 67, 72)):
        ev.append({"t": round(T_VERD + 0.05 * q, 4), "note": m, "gain": 0.38, "x": w / 2})
    for q, m in enumerate((84, 79, 76, 72, 67)):
        ev.append({"t": round(T_RW0 + 0.2 * q, 4), "note": m, "gain": 0.2, "x": w / 2})
    return sorted(ev, key=lambda e: e["t"])


def main():
    label, rule = arg("--label", "v1"), arg("--rule", "")
    studio.OUT_DIR.mkdir(exist_ok=True)
    layout = get_layout(kit.orients()[0])
    print(f"[{SCENE}] measured: " + ", ".join(f"{r:.0f} km -> {m[1]:,.0f} km ({m[2]} steps)" for r, m in zip(RULERS, MEAS)))
    if kit.has("--still"):
        f = int(round(float(arg("--at")) * FPS)) if arg("--at") else int(arg("--frame", "0"))
        png = studio.OUT_DIR / f"{SCENE}_{label}_f{f}_{layout.tag}.png"
        render(layout, png, rule, still_frame=f)
        print(f"[{SCENE}] -> {png}")
        return
    name = f"{SCENE}_{label}_{layout.tag}"
    video = studio.OUT_DIR / f"{name}_silent.mp4"
    d = render(layout, video, rule)
    pad = kit.loop_pad(d, ((45, 1.0), (52, 0.6), (57, 0.4), (64, 0.25)), gain=0.03)
    kit.deliver_loop(SCENE, name, layout, video, build_events(layout), d, voice="glassharp", bed=pad)


if __name__ == "__main__":
    main()
