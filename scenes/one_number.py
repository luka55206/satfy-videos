"""ONE NUMBER — "Change ONE number": z(t) = e^(it) + ½e^(i·a·t) + ⅓e^(−2i·a·t), a slides 1 → 9.

Between whole numbers the curve never closes (a dense, swirling mesh); at every whole number it snaps into one clean
closed shape. The slider eases so it lingers on each integer (the "snap") and rushes through the chaos in between.
Loop: after 9 the slider rewinds fast to 1 = frame 0.
Audio (original): per unit a rising pentatonic run (tension) that resolves on the integer with a chord + bass
(I V vi IV …), a soft pad, a falling run on the rewind.
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

SCENE = "one_number"
A0, A1 = 1, 9
UNIT = 2.1                                    # seconds per whole step of a
T_UP = (A1 - A0) * UNIT
T_HOLD = 0.5
T_REW = 1.2
T_LOOP = T_UP + T_HOLD + T_REW
GOLD = (1.0, 0.82, 0.40)
TT = np.linspace(0, 2 * math.pi * 40, 26000)


def a_of(t):
    if t < T_UP:
        x = t / UNIT
        n, u = int(x), x - int(x)
        return A0 + n + u - math.sin(2 * math.pi * u) / (2 * math.pi)   # zero speed at every integer
    if t < T_UP + T_HOLD:
        return float(A1)
    return A1 - (A1 - A0) * smooth((t - T_UP - T_HOLD) / (T_REW - 0.25))   # lands exactly on a = 1 (= frame 0)


TT_R = np.linspace(0, 2 * math.pi * 10, 9000)
EQ = arg("--eq", "jewel")                         # jewel | rose  (episode change: the equation)
EQ_TXT = {"jewel": "z(t) = e^(it) + 1/2 e^(i·a·t) + 1/3 e^(−2i·a·t)", "rose": "r = cos(a·θ)"}[EQ]
EQ_R = {"jewel": 1.83, "rose": 1.0}[EQ]


def curve(a):
    if EQ == "rose":                               # fewer turns: a lighter mesh, so the snaps don't flash
        return np.cos(a * TT_R) * np.exp(1j * TT_R)
    return np.exp(1j * TT) + 0.5 * np.exp(1j * a * TT) + (1 / 3) * np.exp(-2j * a * TT)


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
        g = cairo.RadialGradient(w / 2, h * 0.44, 0, w / 2, h * 0.44, max(w, h) * 0.7)
        g.add_color_stop_rgb(0.0, 0.07, 0.06, 0.12)
        g.add_color_stop_rgb(1.0, 0.01, 0.01, 0.02)
        ctx.set_source(g)
        ctx.paint()
        a = a_of(t)
        near = abs(a - round(a))
        snap = math.exp(-(near / 0.012) ** 2)                  # 1 exactly on an integer
        z = curve(a)
        S = w * 0.40 / EQ_R
        cx, cy = w / 2, h * 0.435
        xs, ys = cx + S * z.real, cy - S * z.imag
        hue = (0.55 + 0.07 * a) % 1.0
        col = studio.hsv(hue, 0.55 - 0.25 * snap, 1.0)
        pts = list(zip(xs, ys))
        c.polylines([pts], col, width=14 + 10 * snap, alpha=0.05 + 0.13 * snap)
        c.polylines([pts], col, width=1.3 + 2.6 * snap, alpha=0.55 + 0.4 * snap)
        # the ONE number + its slider
        sy = h * 0.735
        x0, x1 = w * 0.12, w * 0.88
        X = lambda v: x0 + (x1 - x0) * (v - A0) / (A1 - A0)       # noqa: E731
        c.lines([(x0, sy, x1, sy)], (0.75, 0.78, 0.9), width=6, alpha=0.35)
        c.lines([(x0, sy, X(a), sy)], GOLD, width=6, alpha=0.95)
        for v in range(A0, A1 + 1):
            passed = a >= v - 1e-6
            c.text_centered(str(v), sy + h * 0.035, size=h * 0.016, color=GOLD if passed else (0.7, 0.72, 0.82),
                            alpha=0.95 if passed else 0.6, cx=X(v))
        c.glow(X(a), sy, 16, GOLD, strength=0.6 + 0.6 * snap, reach=3)
        c.circle(X(a), sy, 15, (1, 1, 1), alpha=1.0)
        c.text_centered(f"a = {a:.2f}", h * 0.685, size=w * (0.085 + 0.02 * snap), color=GOLD, alpha=1.0)
        c.text_centered(EQ_TXT, h * 0.80, size=w * (0.036 if EQ == "jewel" else 0.05),
                        color=(0.95, 0.95, 1.0), alpha=0.9, bold=False)
        c.text_centered("CHANGE ONE NUMBER", h * 0.205, size=h * 0.015, color=GOLD, alpha=0.85)
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


PROG = [(60, (60, 64, 67)), (55, (59, 62, 67)), (57, (60, 64, 69)), (53, (60, 65, 69))]   # C G Am F
PENTA = [0, 2, 4, 7, 9]


def build_events(sim, layout):
    x = layout.w / 2
    out = []
    for n in range(A1 - A0 + 1):                              # the snap on each integer (t = n·UNIT)
        tn = n * UNIT if n < A1 - A0 else T_UP
        root, ch = PROG[n % 4]
        for j, m in enumerate(ch):
            out.append({"t": round(tn + 0.015 * j, 4), "note": m + 12, "gain": 0.30, "x": x})
        out.append({"t": round(tn, 4), "note": root - 12, "gain": 0.24, "x": x})
        if n < A1 - A0:                                       # rising run through the chaos
            nroot = PROG[(n + 1) % 4][0]
            for k in range(7):
                tk = tn + UNIT * (0.18 + 0.1 * k)
                m = nroot + 12 + 12 * (k // 5) + PENTA[k % 5]
                out.append({"t": round(tk, 4), "note": m, "gain": 0.10 + 0.02 * k, "x": layout.w * (0.3 + 0.06 * k)})
    for j in range(9):                                        # rewind run
        out.append({"t": round(T_UP + T_HOLD + j * T_REW / 10, 4), "note": 91 - 3 * j, "gain": 0.12, "x": x})
    return sorted(out, key=lambda e: e["t"])


def _worker(o, sim, label, rule):
    layout = get_layout(o)
    name = f"{SCENE}_{label}_{layout.tag}"
    video = studio.OUT_DIR / f"{name}_silent.mp4"
    d = render(layout, sim, video, rule)
    pad = kit.loop_pad(T_LOOP, ((48, 1.0), (55, 0.7), (60, 0.45), (64, 0.3)), gain=0.015)
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
    print(f"[{SCENE}] {T_LOOP:.1f}s")
    kit.fan_out(_worker, (sim, label, rule), SCENE)


if __name__ == "__main__":
    main()
