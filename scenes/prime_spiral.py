"""PRIME SPIRAL - "Write 1, 2, 3 … in a spiral and light up the primes: they line up on diagonals" (the Ulam spiral).

The numbers 1 … 14,641 spiral outwards (right, up, left, down; 1 in the middle). Each prime lights up and plays a
note the moment the counter reaches it; the camera pulls back as the spiral grows, the counting speeds up. At the end
the six richest diagonals glow: primes love certain diagonal lines (they are values of quadratic polynomials).
Cross-fades into frame 0 (loop).
Audio (original): a prime plays a pentatonic note chosen by p mod 10 (octaves by p mod 3), so you hear them thin out
as the numbers grow; a chord swells when the spiral passes 100, 1,000 and 10,000; a quiet loop pad.
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

SCENE = "prime_spiral"
SIDE = 121
NMAX = SIDE * SIDE
T_RUN, T_HOLD = 13.0, 1.7
T_LOOP = T_RUN + T_HOLD
GOLD = (1.0, 0.82, 0.40)
A_RATE = 7.0


def sieve(n):
    s = np.ones(n + 1, bool)
    s[:2] = False
    for i in range(2, int(n ** 0.5) + 1):
        if s[i]:
            s[i * i::i] = False
    return s


IS_P = sieve(NMAX)


def spiral_xy(n_max):
    xs, ys = np.zeros(n_max + 1, int), np.zeros(n_max + 1, int)
    x = y = 0
    n, step, d = 1, 1, 0
    dirs = [(1, 0), (0, 1), (-1, 0), (0, -1)]
    while n < n_max:
        for _ in range(2):
            for _ in range(step):
                if n >= n_max:
                    break
                n += 1
                x, y = x + dirs[d][0], y + dirs[d][1]
                xs[n], ys[n] = x, y
            d = (d + 1) % 4
        step += 1
    return xs, ys


XS, YS = spiral_xy(NMAX)
RING = np.maximum(np.abs(XS), np.abs(YS))


def n_of_t(t):
    if t >= T_RUN:
        return NMAX
    x = t / T_RUN
    return max(1, int(NMAX * (math.exp(A_RATE * x) - 1) / (math.exp(A_RATE) - 1)) + 1)


def diagonals():
    """the six richest diagonals (x - y = c or x + y = c) over the primes in the whole spiral"""
    best = []
    for kind in (0, 1):
        key = (XS - YS) if kind == 0 else (XS + YS)
        for cval in range(-SIDE, SIDE):
            sel = (key[2:] == cval) & IS_P[2:]
            tot = (key[2:] == cval).sum()
            if tot > 40:
                best.append((sel.sum() / tot, kind, cval))
    best.sort(reverse=True)
    return best[:6]


DIAG = diagonals()


class Scene:
    def __init__(self, layout):
        self.L = layout
        self.canvas = Canvas(layout.w, layout.h, studio.render_scale())

    def frame(self, t):
        L, c = self.L, self.canvas
        w, h = L.w, L.h
        ctx = c.ctx
        g = cairo.RadialGradient(w / 2, h * 0.47, 0, w / 2, h * 0.47, max(w, h) * 0.7)
        g.add_color_stop_rgb(0.0, 0.06, 0.05, 0.11)
        g.add_color_stop_rgb(1.0, 0.005, 0.005, 0.015)
        ctx.set_source(g)
        ctx.paint()
        n = n_of_t(t)
        ext = max(4.0, float(RING[n]) + 2.5)
        if t >= T_RUN:
            ext = SIDE / 2 + 0.5
        cell = (w * 0.92) / (2 * ext)
        cx, cy = w / 2, h * 0.47
        P = lambda x, y: (cx + x * cell, cy - y * cell)                  # noqa: E731
        # a faint grid of every cell
        if cell > 14:
            for k in range(1, min(n, NMAX) + 1):
                px, py = P(XS[k], YS[k])
                ctx.rectangle(px - cell / 2 + 1, py - cell / 2 + 1, cell - 2, cell - 2)
                ctx.set_source_rgba(1, 1, 1, 0.04)
                ctx.fill()
        ks = np.arange(2, min(n, NMAX) + 1)
        ps = ks[IS_P[ks]]
        ctx.save()
        ctx.set_operator(cairo.OPERATOR_ADD)
        rad = max(1.8, min(cell * 0.38, w * 0.03))
        for p in ps:
            px, py = P(XS[p], YS[p])
            col = kit.wheel((p / NMAX) ** 0.5)
            age = n - p
            if cell > 12 and age < 60:
                c.glow(px, py, rad, col, strength=0.5, reach=2.4)
            ctx.set_source_rgba(col[0], col[1], col[2], 0.95)
            ctx.new_sub_path()
            ctx.arc(px, py, rad, 0, 2 * math.pi)
            ctx.fill()
        ctx.restore()
        if cell > 38:                                                     # early on: the numbers themselves
            for k in range(1, n + 1):
                px, py = P(XS[k], YS[k])
                isp = IS_P[k]
                c.text_centered(str(k), py + cell * 0.12, size=cell * 0.34, color=(0.1, 0.05, 0.0) if isp else (0.75, 0.78, 0.9),
                                alpha=0.95 if isp else 0.55, cx=px, bold=isp)
        if t < T_RUN:                                                      # the counter's cursor
            px, py = P(XS[n], YS[n])
            c.ring(px, py, max(cell * 0.62, 6), WHITE_, width=max(2.0, cell * 0.08), alpha=0.9)
        # the diagonals light up at the end
        da = smooth((t - T_RUN - 0.2) / 0.6) * (1.0 - smooth((t - T_LOOP + 0.6) / 0.5))
        if da > 0:
            for _, kind, cval in DIAG:
                hs = SIDE // 2
                if kind == 0:
                    x0, x1 = max(-hs, -hs + cval), min(hs, hs + cval)
                    a, b = (x0, x0 - cval), (x1, x1 - cval)
                else:
                    x0, x1 = max(-hs, cval - hs), min(hs, cval + hs)
                    a, b = (x0, cval - x0), (x1, cval - x1)
                (ax, ay), (bx, by) = P(*a), P(*b)
                c.lines([(ax, ay, bx, by)], (1, 1, 1), width=10, alpha=0.10 * da)
                c.lines([(ax, ay, bx, by)], (1, 1, 1), width=2.2, alpha=0.65 * da)
        np_found = int(IS_P[2:min(n, NMAX) + 1].sum())
        c.text_centered(f"n = {n:,}", h * 0.752, size=w * 0.085, color=(1, 1, 1))
        c.text_centered(f"{np_found:,} primes found", h * 0.795, size=w * 0.045, color=GOLD, bold=False)
        if t >= T_RUN:
            c.text_centered("primes love diagonals", h * 0.835, size=w * 0.052, color=(1, 1, 1), alpha=da)

    def draw(self, f, rule):
        c, L = self.canvas, self.L
        t = f * DT
        self.frame(t)
        k_ = smooth((t - (T_LOOP - 0.45)) / 0.43)
        if k_ > 0:
            c.ctx.push_group()
            self.frame(0.0)
            c.ctx.pop_group_to_source()
            c.ctx.paint_with_alpha(k_)
        if rule:
            c.caption(rule, alpha=1.0, layout=L)
        c.watermark(L)


WHITE_ = (1.0, 1.0, 1.0)


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
    P5 = audio.PENTA_MAJOR
    # video time of every number
    tt = np.linspace(0.0, T_RUN, 20001)
    nn = np.array([n_of_t(x) for x in tt])
    ev, last = [], -1e9
    for p in np.nonzero(IS_P)[0]:
        t = float(tt[min(np.searchsorted(nn, p, side="left"), len(tt) - 1)])
        gap = 0.20 - 0.15 * smooth(t / T_RUN)
        if t - last < gap:
            continue
        last = t
        d = int(p % 10)
        note = 55 + 12 * (int(p % 3)) // 1 * 0 + 60 - 5 + 12 * (d // 5) + P5[d % 5] + (12 if p % 3 == 2 else 0)
        ev.append({"t": round(t, 4), "note": int(note), "gain": 0.5, "x": layout.w * (0.5 + 0.3 * math.cos(p))})
    for n_sw, (root, ch) in zip((100, 1000, 10000), ((48, (60, 64, 67)), (43, (59, 62, 67)), (45, (60, 64, 69)))):
        t = float(tt[np.searchsorted(nn, n_sw)])
        ev.append({"t": round(t, 4), "note": root, "gain": 0.7, "x": layout.w / 2})
        for k_, nt in enumerate(ch):
            ev.append({"t": round(t + 0.04 * k_, 4), "note": nt, "gain": 0.55, "x": layout.w / 2})
    for k_, nt in enumerate((48, 60, 64, 67, 72)):
        ev.append({"t": round(T_RUN + 0.1 + 0.05 * k_, 4), "note": nt, "gain": 0.7, "x": layout.w / 2})
    return sorted(ev, key=lambda e: e["t"])


def main():
    label, rule = arg("--label", "v1"), arg("--rule", "")
    studio.OUT_DIR.mkdir(exist_ok=True)
    layout = get_layout(kit.orients()[0])
    if kit.has("--still"):
        f = int(arg("--frame", "0"))
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
