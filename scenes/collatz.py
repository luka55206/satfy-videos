"""COLLATZ — "Every number falls to 1 … and nobody can prove why" (the Collatz coral).

Rule: even → n/2, odd → 3n + 1. Every number tried so far reaches 1 (unproven in general). Each number's path to 1 is
drawn BACKWARDS from a common root: one fixed-length step per value, turning left on even values and right on odd
ones, so shared tails merge into one trunk and the 1,500 paths grow into a coral.
Timeline: 0–0.9 s the finished coral (payoff first) · 0.9–1.5 it shrinks into its root · 1.6–6.0 numbers 2…30 one by
one, each path highlighted with its journey on screen (27 takes 111 steps) · 6.0–15.0 all 1,500, accelerating ·
hold the full coral = frame 0 (loop).
Audio (original): every featured number plays its own journey as a falling run of notes (pitch ∝ log of the value),
always landing on the same note: 1. Then a shimmer while the coral fills, and a chord when it is complete.
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

SCENE = "collatz"
NMAX = 1500
AE, AO = 0.11, 0.21                     # turn on even / odd values (radians)
T_COLD, T_SHRINK, T_START = 0.9, 1.5, 1.6
T_SLOW_END = 6.0                         # numbers 2..N_SLOW one by one
N_SLOW = 30
T_ZOOM_END = 7.0                         # zoom out from the first 30 numbers to the whole coral
T_FULL = 15.0
T_LOOP = 16.6
GOLD = (1.0, 0.82, 0.40)


def seq(n):
    s = [n]
    while n != 1:
        n = n // 2 if n % 2 == 0 else 3 * n + 1
        s.append(n)
    return s


SEQ = {n: seq(n) for n in range(2, NMAX + 1)}


def raw_path(n, a0):
    s = SEQ[n][::-1]
    x, y, a = 0.0, 0.0, a0
    pts = [(x, y)]
    for v in s[1:]:
        a += AE if v % 2 == 0 else -AO
        x += math.cos(a)
        y += math.sin(a)
        pts.append((x, y))
    return pts


def best_start():
    best = None
    for a0 in np.linspace(0.4, 2.8, 25):                    # pick the start angle that makes the coral most upright
        xs, ys = [], []
        for n in range(2, NMAX + 1, 7):
            p = raw_path(n, a0)
            xs += [q[0] for q in p]
            ys += [q[1] for q in p]
        wdt, hgt = max(xs) - min(xs), max(ys) - min(ys)
        score = abs(wdt / max(hgt, 1e-9) - 0.95) + (1.0 if min(ys) < -0.04 * hgt else 0)   # fill the frame, root at the bottom
        if best is None or score < best[0]:
            best = (score, a0)
    return best[1]


A0 = best_start()
PATHS = {n: raw_path(n, A0) for n in range(2, NMAX + 1)}
_all = np.array([q for p in PATHS.values() for q in p])
BB = (_all[:, 0].min(), _all[:, 0].max(), _all[:, 1].min(), _all[:, 1].max())


def count_at(t):
    """How many numbers (from 2 upward) are drawn at time t."""
    if t < T_START:
        return NMAX - 1
    if t < T_SLOW_END:
        return 1 + int((t - T_START) / (T_SLOW_END - T_START) * (N_SLOW - 1))
    if t < T_FULL:
        u = (t - T_SLOW_END) / (T_FULL - T_SLOW_END)
        return min(NMAX - 1, N_SLOW - 1 + int((NMAX - N_SLOW) * u ** 1.8))
    return NMAX - 1


def slow_times():
    return {n: T_START + (n - 2) * (T_SLOW_END - T_START) / (N_SLOW - 1) for n in range(2, N_SLOW + 1)}


SLOW_T = slow_times()


def col(n):
    return studio.hsv(0.50 + 0.45 * math.log(n) / math.log(NMAX), 0.55, 1.0)


def simulate():
    return {"nf": int(round(T_LOOP * FPS))}


class Scene:
    def __init__(self, layout, sim):
        self.L, self.sim = layout, sim
        self.canvas = Canvas(layout.w, layout.h, studio.render_scale())
        w, h = layout.w, layout.h
        x0, x1, y0, y1 = BB
        self.S = min(w * 0.88 / (x1 - x0), h * 0.50 / (y1 - y0))
        self.ox = w / 2 - self.S * (x0 + x1) / 2
        self.oy = h * 0.67 + self.S * y0                     # root near the bottom of the art area
        c = self.canvas
        self.art = cairo.ImageSurface(cairo.FORMAT_ARGB32, c.pw, c.ph)
        self.actx = cairo.Context(self.art)
        self.actx.scale(c.pw / w, c.ph / h)
        self.actx.set_operator(cairo.OPERATOR_ADD)
        self.full = cairo.ImageSurface(cairo.FORMAT_ARGB32, c.pw, c.ph)
        fctx = cairo.Context(self.full)
        fctx.scale(c.pw / w, c.ph / h)
        fctx.set_operator(cairo.OPERATOR_ADD)
        for n in range(2, NMAX + 1):
            self.stroke(fctx, n, 0.07)
        self.done = 1
        self.rx, self.ry = self.P(0, 0)
        pts = np.array([q for n in range(2, N_SLOW + 1) for q in PATHS[n]])
        lim = []                                              # biggest zoom that keeps paths 2..30 on screen
        if pts[:, 0].min() < 0:
            lim.append((self.rx - w * 0.06) / -pts[:, 0].min())
        if pts[:, 0].max() > 0:
            lim.append((w * 0.94 - self.rx) / pts[:, 0].max())
        if pts[:, 1].max() > 0:
            lim.append((self.ry - h * 0.24) / pts[:, 1].max())
        self.S_slow = max(self.S, min(lim))

    def zoom(self, t):
        """(scale, x-shift) of the vector view: close on the first 30 numbers, then out to the full coral."""
        u = smooth((t - T_SLOW_END) / (T_ZOOM_END - T_SLOW_END))
        return math.exp(math.log(self.S_slow) + (math.log(self.S) - math.log(self.S_slow)) * u), 0.0

    def stroke_z(self, ctx, n, alpha, sc, dx, upto=None, width=2.4, colr=None):
        p = PATHS[n] if upto is None else PATHS[n][:upto]
        if len(p) < 2:
            return
        X = lambda q: (self.rx + sc * q[0], self.ry - sc * q[1])  # noqa: E731  zoom about the root
        ctx.move_to(*X(p[0]))
        for q in p[1:]:
            ctx.line_to(*X(q))
        ctx.set_source_rgba(*(colr or col(n)), alpha)
        ctx.set_line_width(width)
        ctx.stroke()

    def P(self, x, y):
        return self.ox + self.S * x, self.oy - self.S * y

    def stroke(self, ctx, n, alpha, upto=None, width=1.6, colr=None):
        p = PATHS[n] if upto is None else PATHS[n][:upto]
        if len(p) < 2:
            return
        ctx.move_to(*self.P(*p[0]))
        for q in p[1:]:
            ctx.line_to(*self.P(*q))
        ctx.set_source_rgba(*(colr or col(n)), alpha)
        ctx.set_line_width(width)
        ctx.stroke()

    def catch_up(self, k):
        while self.done < k:
            self.done += 1
            self.stroke(self.actx, self.done + 0, 0.07)

    def draw(self, f, rule):
        L, c = self.L, self.canvas
        w, h = L.w, L.h
        t = f * DT
        ctx = c.ctx
        g = cairo.RadialGradient(w / 2, h * 0.45, 0, w / 2, h * 0.45, max(w, h) * 0.7)
        g.add_color_stop_rgb(0.0, 0.06, 0.06, 0.12)
        g.add_color_stop_rgb(1.0, 0.01, 0.01, 0.02)
        ctx.set_source(g)
        ctx.paint()
        rx, ry = self.P(0, 0)
        if t < T_START:                                       # cold open + shrink into the root
            s = 1.0 - smooth((t - T_COLD) / (T_SHRINK - T_COLD))
            if s > 0.003:
                ctx.save()
                ctx.translate(rx, ry)
                ctx.scale(s, s)
                ctx.translate(-rx, -ry)
                ctx.scale(w / c.pw, h / c.ph)
                ctx.set_source_surface(self.full, 0, 0)
                ctx.paint()
                ctx.restore()
        elif t >= T_FULL:
            ctx.save()
            ctx.scale(w / c.pw, h / c.ph)
            ctx.set_source_surface(self.full, 0, 0)
            ctx.paint()
            ctx.restore()
        elif t < T_ZOOM_END:                                  # vector view, zoomed on the first numbers
            k = count_at(t) + 1
            self.catch_up(k)
            sc, dx = self.zoom(t)
            for n in range(2, k + 1):
                self.stroke_z(ctx, n, 0.55, sc, dx, width=2.2)
            if t < T_SLOW_END + 0.5:                          # the newest featured path, gold, growing from the root
                n = max(m for m, tm in SLOW_T.items() if tm <= t)
                age = t - SLOW_T[n]
                upto = max(2, int(len(PATHS[n]) * min(1.0, age / 0.35)))
                self.stroke_z(ctx, n, 0.98, sc, dx, upto=upto, width=5, colr=GOLD)
                q = PATHS[n][upto - 1]
                px, py = self.rx + sc * q[0], self.ry - sc * q[1]
                c.glow(px, py, 10, GOLD, strength=0.8, reach=3)
                c.text_centered(str(n), py - 18, size=h * 0.02, color=GOLD, alpha=0.95, cx=px)
        else:
            k = count_at(t) + 1                               # numbers 2..k are drawn
            self.catch_up(k)
            ctx.save()
            ctx.scale(w / c.pw, h / c.ph)
            ctx.set_source_surface(self.art, 0, 0)
            ctx.paint()
            ctx.restore()
        c.circle(rx, ry, 7, (1, 1, 1), alpha=0.9)
        c.text_centered("1", ry + h * 0.035, size=h * 0.022, color=GOLD, alpha=0.95, cx=rx)
        # HUD
        if t < T_START + 0.1 or t >= T_FULL:
            a = 1.0 if t < T_FULL else smooth((t - T_FULL) / 0.4)
            if t < T_START:
                a = 1.0 if t < T_COLD else max(0.0, 1 - (t - T_COLD) / 0.4)
            c.text_centered("EVERY NUMBER FALLS TO 1", h * 0.745, size=w * 0.072, color=GOLD, alpha=a)
            c.text_centered(f"all {NMAX:,} numbers tested here", h * 0.785, size=w * 0.036,
                            color=(0.88, 0.89, 0.95), alpha=0.9 * a, bold=False)
        elif t < T_SLOW_END + 0.6:
            n = max(m for m, tm in SLOW_T.items() if tm <= t)
            s = SEQ[n]
            txt = " → ".join(map(str, s)) if len(s) <= 9 else " → ".join(map(str, s[:5])) + " → … → " + " → ".join(map(str, s[-3:]))
            c.text_centered(f"n = {n}", h * 0.735, size=w * 0.07, color=GOLD, alpha=1.0)
            c.text_centered(txt, h * 0.772, size=w * 0.034, color=(0.95, 0.95, 1.0), alpha=0.95, bold=False,
                            max_w=w * 0.94)
            c.text_centered(f"{len(s) - 1} steps to 1", h * 0.805, size=w * 0.036, color=(0.75, 0.78, 0.88),
                            alpha=0.85, bold=False)
        else:
            k = count_at(t) + 1
            c.text_centered(f"numbers: {k:,}", h * 0.745, size=w * 0.07, color=(0.95, 0.95, 1.0), alpha=1.0)
            c.text_centered("all of them reach 1", h * 0.785, size=w * 0.036, color=(0.75, 0.78, 0.88), alpha=0.85,
                            bold=False)
        c.text_centered("even → ÷2      odd → ×3 + 1", h * 0.205, size=h * 0.016, color=GOLD, alpha=0.9)
        if rule:
            c.caption(rule, alpha=1.0, layout=L)
        c.watermark(L)


def render(layout, sim, out_path, rule, still_frame=None):
    sc = Scene(layout, sim)
    writer = None if still_frame is not None else VideoWriter(out_path, sc.canvas, FPS)
    for f in range(sim["nf"]):
        if still_frame is not None and f != still_frame:
            t = f * DT
            if T_START <= t < T_FULL:
                sc.catch_up(count_at(t) + 1)
            continue
        sc.draw(f, rule)
        if writer is None:
            studio.save_still(sc.canvas, out_path)
            return f / FPS
        writer.write_frame()
    writer.close()
    return sim["nf"] / FPS


PENTA = [0, 2, 4, 7, 9]


def note_of(v):
    k = min(19, int(math.log2(v) * 1.6))                       # 1 → the root note; bigger values → higher
    return 60 + 12 * (k // 5) + PENTA[k % 5]


def build_events(sim, layout):
    x = layout.w / 2
    out = [{"t": 0.0 + 0.012 * j, "note": m, "gain": 0.26, "x": x} for j, m in enumerate((48, 55, 60, 64, 67))]
    for j in range(7):                                         # shrink
        out.append({"t": round(T_COLD + 0.08 * j, 4), "note": 91 - 3 * j, "gain": 0.12, "x": x})
    for n, t0 in SLOW_T.items():                               # each featured number plays its fall to 1
        s = SEQ[n]
        dt = min(0.03, 0.30 / len(s))
        for i, v in enumerate(s):
            out.append({"t": round(t0 + i * dt, 4), "note": note_of(v), "gain": 0.16 if v != 1 else 0.30,
                        "x": layout.w * (0.3 + 0.4 * (i / len(s)))})
    t = T_SLOW_END
    while t < T_FULL:                                          # shimmer while the coral fills (gets faster)
        k = count_at(t) + 1
        out.append({"t": round(t, 4), "note": note_of(len(SEQ[min(k, NMAX)]) + 1) + 12, "gain": 0.10, "x": x})
        u = (t - T_SLOW_END) / (T_FULL - T_SLOW_END)
        t += 0.22 - 0.15 * u
    for j, m in enumerate((48, 55, 60, 64, 67, 72)):
        out.append({"t": round(T_FULL + 0.05 * j, 4), "note": m, "gain": 0.28, "x": x})
    return sorted(out, key=lambda e: e["t"])


def _worker(o, sim, label, rule):
    layout = get_layout(o)
    name = f"{SCENE}_{label}_{layout.tag}"
    video = studio.OUT_DIR / f"{name}_silent.mp4"
    d = render(layout, sim, video, rule)
    pad = kit.loop_pad(T_LOOP, ((48, 1.0), (55, 0.7), (60, 0.45), (64, 0.3)), gain=0.013)
    kit.deliver_loop(SCENE, name, layout, video, build_events(sim, layout), d, voice="glassharp", bed=pad,
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
    print(f"[{SCENE}] {T_LOOP:.1f}s, 27 takes {len(SEQ[27]) - 1} steps, start angle {A0:.2f}")
    kit.fan_out(_worker, (sim, label, rule), SCENE)


if __name__ == "__main__":
    main()
