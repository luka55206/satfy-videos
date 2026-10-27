"""GOLDEN ZOOM — an endless, seamless dive into the golden spiral.

Exact golden squares: S0 = the unit square, S(k+1) = T(S(k)) with T(z) = -i z / phi + (1 + i), the map that
takes a golden rectangle onto the smaller golden rectangle left after removing its square. The spiral's eye is
the fixed point E = (1 + i) / (1 + i/phi). The camera zooms x phi and turns 90 deg per step, so after 4 steps
(colours repeat every 4) the picture is IDENTICAL: a perfect loop. Each square carries a quarter-circle of the
golden spiral. Audio (original): a 4-note motif, one note per square passed, + a periodic pad.
"""
import cmath
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

SCENE = "golden_zoom"
PHI = (1 + 5 ** 0.5) / 2
A = -1j / PHI                                  # T(z) = A z + B
B = 1 + 1j
E = B / (1 - A)                                # the eye (fixed point)
TAU = 1.15                                     # seconds per square (zoom x phi, turn 90 deg)
LOOPS = 3
T_LOOP = 4 * TAU * LOOPS                       # 13.8 s, a whole number of 4-step cycles
COLS = [(1.00, 0.42, 0.55), (1.00, 0.70, 0.30), (0.40, 0.85, 0.55), (0.30, 0.70, 1.00)]
GOLD = (1.0, 0.85, 0.45)
SQ0 = [0, 1, 1 + 1j, 1j]
ARC0 = (1 + 0j, 1.0, math.pi, math.pi / 2)    # centre, radius, from angle, to angle (unit square arc)


def simulate():
    return {"nf": int(round(T_LOOP * FPS))}


class Scene:
    def __init__(self, layout, sim):
        self.L, self.sim = layout, sim
        self.canvas = Canvas(layout.w, layout.h, studio.render_scale())
        w, h = layout.w, layout.h
        self.cx, self.cy = w / 2, h * 0.45
        self.M0 = w * 0.34                     # px per world unit at t = 0 (square 0 ~ 62 % of the width)

    def draw(self, f, rule):
        L, c = self.L, self.canvas
        w, h = L.w, L.h
        t = f * DT
        ctx = c.ctx
        g = cairo.RadialGradient(w / 2, h * 0.45, 0, w / 2, h * 0.45, max(w, h) * 0.7)
        g.add_color_stop_rgb(0.0, 0.07, 0.06, 0.11)
        g.add_color_stop_rgb(1.0, 0.01, 0.01, 0.02)
        ctx.set_source(g)
        ctx.paint()
        u = t / TAU
        M = self.M0 * cmath.exp(u * cmath.log(1j * PHI))   # |M| grows x phi per step, arg +90 deg per step

        def P(z):
            q = M * (z - E)
            return self.cx + q.real, self.cy - q.imag

        # visible squares: on-screen size |M| * phi^-k between ~1.5 px and ~4x the screen
        mag = abs(M)
        k_lo = max(-6, int(math.floor(math.log(mag / (4 * h)) / math.log(PHI))))
        k_hi = int(math.ceil(math.log(mag / 1.5) / math.log(PHI)))
        ctx.set_line_join(cairo.LINE_JOIN_ROUND)
        arcs = []
        for k in range(k_lo, k_hi + 1):
            ak = A ** k if k >= 0 else (1 / A) ** (-k)
            Tk = lambda z, ak=ak: E + ak * (z - E)        # noqa: E731  T^k
            pts = [P(Tk(z)) for z in SQ0]
            ctx.move_to(*pts[0])
            for q in pts[1:]:
                ctx.line_to(*q)
            ctx.close_path()
            side = mag * PHI ** (-k)                     # on-screen size of this square
            fa = 0.85 * (1 - smooth((side - w * 0.30) / (w * 0.9)))   # big squares fade into the dark
            ctx.set_source_rgba(*COLS[k % 4], fa)
            ctx.fill_preserve()
            ctx.set_source_rgba(*COLS[k % 4], 0.35 + 0.6 * fa) if fa < 0.3 else ctx.set_source_rgba(0.04, 0.03, 0.07, 0.95)
            ctx.set_line_width(max(1.0, min(4.0, mag * PHI ** (-k) * 0.012)))
            ctx.stroke()
            cen, r, a0, a1 = ARC0
            arc = [P(Tk(cen + r * cmath.exp(1j * (a0 + (a1 - a0) * j / 24)))) for j in range(25)]
            arcs.append(arc)
        c.polylines(arcs, GOLD, width=16, alpha=0.18)
        c.polylines(arcs, (1.0, 0.95, 0.80), width=5, alpha=0.95)
        ex, ey = P(E)
        c.glow(ex, ey, 10, GOLD, strength=0.5, reach=4)
        c.text_centered("FAMOUS NUMBERS · GOLDEN RATIO", h * 0.205, size=h * 0.015, color=GOLD, alpha=0.85)
        c.text_centered("every square = the last one ÷ φ", h * 0.765, size=w * 0.042, color=(1, 1, 1), alpha=0.9)
        c.text_centered("φ = 1.6180339887…", h * 0.805, size=w * 0.040, color=GOLD, alpha=0.9)
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
    motif = [69, 72, 76, 74]                       # a calm 4-note motif, one note per square (repeats every 4)
    out = []
    n = int(round(T_LOOP / TAU))
    for k in range(n):
        out.append({"t": round(k * TAU + 0.01, 4), "note": motif[k % 4], "gain": 0.40, "x": layout.w / 2})
        out.append({"t": round(k * TAU + 0.01, 4), "note": motif[k % 4] - 24, "gain": 0.20, "x": layout.w / 2})
        out.append({"t": round(k * TAU + TAU / 2, 4), "note": motif[(k + 2) % 4] + 12, "gain": 0.14,
                    "x": layout.w / 2})
    return out


def _worker(o, sim, label, rule):
    layout = get_layout(o)
    name = f"{SCENE}_{label}_{layout.tag}"
    video = studio.OUT_DIR / f"{name}_silent.mp4"
    d = render(layout, sim, video, rule)
    pad = kit.loop_pad(T_LOOP, ((45, 1.0), (52, 0.7), (57, 0.45), (61, 0.3)), gain=0.016)
    kit.deliver_loop(SCENE, name, layout, video, build_events(sim, layout), d, voice="glassharp", bed=pad)


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
    print(f"[{SCENE}] {T_LOOP:.2f}s, eye {E}")
    kit.fan_out(_worker, (sim, label, rule), SCENE)


if __name__ == "__main__":
    main()
