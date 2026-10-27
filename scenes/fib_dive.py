"""FIB DIVE — count DOWN the golden spiral: 233, 144, 89 … 3, 2, 1, 1 (golden_zoom v2, "more information").

Real Fibonacci squares (sides 1, 1, 2, 3, 5 … 233) tiled into the spiral, each square labelled with its number.
The camera dives from the 233 rectangle into the smallest squares, turning 90° per step so the current rectangle
stays upright, and the rule line shows why: "89 = 55 + 34" (every square = the next two added). The steps speed
up; at the final 1 the sound lands on a chord, then the camera rewinds (zooms back out through every number) to 233,
which is frame 0: a continuous loop.
Audio (original): one rising pentatonic note per square passed, a bright chord at 1, a falling run on the rewind.
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

SCENE = "fib_dive"
F = [1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233]
NSQ = len(F)
N_TOP, N_END = NSQ - 1, 1                     # dive from "squares 0..12" (377x233 box) to "squares 0..1" (2x1)
COLS = [(1.00, 0.42, 0.55), (1.00, 0.70, 0.30), (0.40, 0.85, 0.55), (0.30, 0.70, 1.00)]
GOLD = (1.0, 0.85, 0.45)
STEP_T = [0.70 - 0.02 * k for k in range(N_TOP - N_END)]       # 0.70 s → 0.50 s per step (moving from frame 0, accelerating)
T_DIVE = sum(STEP_T)
T_LAND = 0.75                                  # the payoff "1"
T_BACK = 1.7                                   # rewind to 233
T_LOOP = T_DIVE + T_LAND + T_BACK
STEP_START = np.concatenate([[0.0], np.cumsum(STEP_T)])


def tiling():
    """Fibonacci squares placed right, up, left, down around a growing box; quarter arcs chained into the spiral."""
    sq = [(0.0, 0.0, 1.0)]
    box = [0.0, 0.0, 1.0, 1.0]                 # x0 y0 x1 y1 (maths coords, y up)
    boxes = [tuple(box)]
    for n in range(1, NSQ):
        s, d = F[n], (n - 1) % 4
        if d == 0:
            sq.append((box[2], box[1], s)); box[2] += s
        elif d == 1:
            sq.append((box[0], box[3], s)); box[3] += s
        elif d == 2:
            sq.append((box[0] - s, box[1], s)); box[0] -= s
        else:
            sq.append((box[0], box[1] - s, s)); box[1] -= s
        boxes.append(tuple(box))
    arcs, P = [], (0.0, 1.0)
    arcs.append(((1.0, 1.0), 1.0, (0.0, 1.0), (1.0, 0.0)))    # square 0: centre (1,1), from (0,1) to (1,0)
    P = (1.0, 0.0)
    for n in range(1, NSQ):
        x, y, s = sq[n]
        corners = [(x, y), (x + s, y), (x + s, y + s), (x, y + s)]
        bx = boxes[n - 1]
        shared = [q for q in corners if bx[0] - 1e-9 <= q[0] <= bx[2] + 1e-9 and bx[1] - 1e-9 <= q[1] <= bx[3] + 1e-9]
        C = [q for q in shared if abs(q[0] - P[0]) + abs(q[1] - P[1]) > 1e-9][0]
        Q = [q for q in corners if abs(math.hypot(q[0] - C[0], q[1] - C[1]) - s) < 1e-9 and
             abs(q[0] - P[0]) + abs(q[1] - P[1]) > 1e-9][0]
        arcs.append((C, s, P, Q))
        P = Q
    return sq, boxes, arcs


SQ, BOXES, ARCS = tiling()


def step_u(t):
    """Continuous camera index: N_TOP at t=0 → N_END at the end of the dive → back to N_TOP at T_LOOP."""
    if t < T_DIVE:
        k = int(np.searchsorted(STEP_START, t, side="right")) - 1
        k = min(k, len(STEP_T) - 1)
        p = (t - STEP_START[k]) / STEP_T[k]
        return N_TOP - k - smooth(p) * 0.85 - 0.15 * p
    if t < T_DIVE + T_LAND:
        return float(N_END)
    p = smooth((t - T_DIVE - T_LAND) / T_BACK)
    return N_END + (N_TOP - N_END) * p


def cam(u):
    """Camera for continuous index u: centre (Catmull-Rom through box centres), scale (geometric), angle."""
    i = min(max(int(math.floor(u)), 0), NSQ - 2)
    fr = u - i

    def cen(k):
        k = min(max(k, 0), NSQ - 1)
        b = BOXES[k]
        return np.array([(b[0] + b[2]) / 2, (b[1] + b[3]) / 2])

    p0, p1, p2, p3 = cen(i - 1), cen(i), cen(i + 1), cen(i + 2)
    tt = fr
    c = 0.5 * ((2 * p1) + (-p0 + p2) * tt + (2 * p0 - 5 * p1 + 4 * p2 - p3) * tt ** 2 + (-p0 + 3 * p1 - 3 * p2 + p3) * tt ** 3)
    size = F[i + 1] * (F[i + 2] / F[i + 1] if i + 2 < NSQ else 1.618) ** fr if i + 1 < NSQ else F[-1]
    return c, size, u * math.pi / 2


def simulate():
    return {"nf": int(round(T_LOOP * FPS))}


class Scene:
    def __init__(self, layout, sim):
        self.L, self.sim = layout, sim
        self.canvas = Canvas(layout.w, layout.h, studio.render_scale())

    def draw(self, f, rule):
        L, c = self.L, self.canvas
        w, h = L.w, L.h
        t = f * DT
        ctx = c.ctx
        g = cairo.RadialGradient(w / 2, h * 0.46, 0, w / 2, h * 0.46, max(w, h) * 0.7)
        g.add_color_stop_rgb(0.0, 0.07, 0.06, 0.11)
        g.add_color_stop_rgb(1.0, 0.01, 0.01, 0.02)
        ctx.set_source(g)
        ctx.paint()
        u = step_u(t)
        cen, size, ang = cam(u)
        k = h * 0.42 / size                    # long side of the current rectangle = 42 % of the height
        ca, sa = math.cos(ang), math.sin(ang)
        cx, cy = w / 2, h * 0.455

        def P(x, y):
            dx, dy = x - cen[0], y - cen[1]
            rx, ry = dx * ca - dy * sa, dx * sa + dy * ca
            return cx + k * rx, cy - k * ry

        ctx.set_line_join(cairo.LINE_JOIN_ROUND)
        labels = []
        for n in range(NSQ):
            x, y, s = SQ[n]
            side = s * k
            if side < 2:
                continue
            fa = 0.80 * (1 - smooth((side - w * 0.40) / (w * 0.6)))
            if fa <= 0.01:
                continue
            pts = [P(x, y), P(x + s, y), P(x + s, y + s), P(x, y + s)]
            ctx.move_to(*pts[0])
            for q in pts[1:]:
                ctx.line_to(*q)
            ctx.close_path()
            ctx.set_source_rgba(*COLS[n % 4], fa * 0.55)
            ctx.fill_preserve()
            ctx.set_source_rgba(0.04, 0.03, 0.07, 0.95)
            ctx.set_line_width(max(1.0, min(5.0, side * 0.012)))
            ctx.stroke()
            labels.append((n, P(x + s / 2, y + s / 2), side, fa))
        arcs = []
        for n in range(NSQ):
            (Cx, Cy), r, (Px, Py), (Qx, Qy) = ARCS[n]
            if r * k < 1.5:
                continue
            a0 = math.atan2(Py - Cy, Px - Cx)
            a1 = math.atan2(Qy - Cy, Qx - Cx)
            da = (a1 - a0 + math.pi) % (2 * math.pi) - math.pi
            arcs.append([P(Cx + r * math.cos(a0 + da * j / 24), Cy + r * math.sin(a0 + da * j / 24)) for j in range(25)])
        c.polylines(arcs, GOLD, width=14, alpha=0.18)
        c.polylines(arcs, (1.0, 0.95, 0.80), width=4.5, alpha=0.95)
        n_cur = int(round(min(max(u, N_END), N_TOP)))
        for n, (lx, ly), side, fa in labels:
            fs = min(side * 0.30, w * 0.17)
            if fs < 11:
                continue
            on = n == n_cur and (t < T_DIVE + T_LAND or t > T_LOOP - 0.4)
            c.text_centered(str(F[n]), ly + fs * 0.36, size=fs, color=(1, 1, 1) if not on else GOLD,
                            alpha=min(1.0, 0.25 + fa * 1.1), cx=lx)
        # the rule line + countdown
        if t < T_DIVE:                              # no reading in the first second: the rule fades in at 0.9 s
            n = n_cur
            ea = smooth((t - 0.9) / 0.3)
            if n >= 2:
                eq = f"{F[n]} = {F[n - 1]} + {F[n - 2]}"
            else:
                eq = "1 = 1"
            c.text_centered(eq, h * 0.765, size=w * 0.075, color=GOLD, alpha=0.95 * ea)
            c.text_centered("every square = the next two added", h * 0.80, size=w * 0.034, color=(0.85, 0.86, 0.92),
                            alpha=0.85 * ea, bold=False)
        elif t < T_DIVE + T_LAND:
            p = (t - T_DIVE) / T_LAND
            c.text_centered("1", h * 0.79, size=w * 0.14 * (1 + 0.25 * math.exp(-p * 6)), color=GOLD, alpha=1.0)
        else:
            c.text_centered("<< REWIND", h * 0.775, size=w * 0.05, color=(0.85, 0.86, 0.92),
                            alpha=0.8 * (1 - smooth((t - (T_LOOP - 0.5)) / 0.4)))   # gone by the seam = frame 0
        c.text_centered("FAMOUS NUMBERS · FIBONACCI", h * 0.205, size=h * 0.015, color=GOLD, alpha=0.85)
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
    penta = [0, 2, 4, 7, 9]
    out = []
    for j in range(len(STEP_T) + 1):           # one note per square reached (233 at t=0 … 1 at T_DIVE), rising
        t = STEP_START[j] if j < len(STEP_T) else T_DIVE
        note = 57 + 12 * (j // 5) + penta[j % 5]
        out.append({"t": round(float(t) + 0.005, 4), "note": note, "gain": 0.40, "x": layout.w / 2})
        out.append({"t": round(float(t) + 0.005, 4), "note": note - 24, "gain": 0.18, "x": layout.w / 2})
    for i, note in enumerate((69, 73, 76, 81, 85)):                 # chord at 1
        out.append({"t": round(T_DIVE + 0.03 * i, 4), "note": note, "gain": 0.34, "x": layout.w / 2})
    nb = N_TOP - N_END                                               # falling run on the rewind
    for j in range(nb):
        tb = T_DIVE + T_LAND + T_BACK * (0.08 + 0.8 * j / nb)
        out.append({"t": round(tb, 4), "note": 93 - 3 * j, "gain": 0.13, "x": layout.w / 2})
    return sorted(out, key=lambda e: e["t"])


def _worker(o, sim, label, rule):
    layout = get_layout(o)
    name = f"{SCENE}_{label}_{layout.tag}"
    video = studio.OUT_DIR / f"{name}_silent.mp4"
    d = render(layout, sim, video, rule)
    pad = kit.loop_pad(T_LOOP, ((45, 1.0), (52, 0.7), (57, 0.45), (61, 0.3)), gain=0.016)
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
    print(f"[{SCENE}] {T_LOOP:.2f}s")
    kit.fan_out(_worker, (sim, label, rule), SCENE)


if __name__ == "__main__":
    main()
