"""TIMES-TABLE CIRCLE - "×2 to ×12 on a circle: every table draws a new shape, and plays a chord".

360 points on a circle; for a multiplier k a chord joins point i to point k·i (mod 360). k = 2 is a heart-shaped
cardioid (1 cusp), k = 3 a nephroid (2 cusps) ... the table of k draws an epicycloid with k − 1 cusps. The multiplier
climbs 2 → 12 in a stepping rhythm (hold, sweep to the next; fractional k just slides the endpoints) and then sweeps
back down to 2 = frame 0 (ping-pong: a nonstop loop, the motion is continuous at both turns).
Audio (original): every integer multiplier lands on a chord (C G Am F, repeating), the sweeps between them play
rising / falling pentatonic arpeggios, a soft pulse on each landing; the way back down plays the arpeggios in reverse.
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

SCENE = "times_circle"
N = 360
K0, K1 = 2, 12
HOLD, SWEEP = 0.55, 0.5                 # seconds at each integer / sweeping to the next
T_TOP = 0.9                             # extra hold at the top
T_DOWN = 4.6                            # the way back down
STEP = HOLD + SWEEP
T_UP = (K1 - K0) * STEP + HOLD
T_LOOP = T_UP + T_TOP + T_DOWN
GOLD = (1.0, 0.82, 0.40)
CUSPS = {2: "cardioid", 3: "nephroid"}
CHORDS = [(48, (60, 64, 67)), (43, (59, 62, 67)), (45, (60, 64, 69)), (41, (60, 65, 69))]      # C G Am F


def k_of_t(t):
    if t < T_UP:
        j = int(t // STEP)
        u = (t - j * STEP - HOLD) / SWEEP
        return K0 + j + smooth(u) if j < K1 - K0 else float(K1)
    if t < T_UP + T_TOP:
        return float(K1)
    u = min(1.0, (t - T_UP - T_TOP) / (T_DOWN - 0.25))                    # lands EXACTLY on 2 a moment before the end
    return K1 - (K1 - K0) * smooth(u)


class Scene:
    def __init__(self, layout):
        self.L = layout
        self.canvas = Canvas(layout.w, layout.h, studio.render_scale())

    def draw(self, f, rule):
        L, c = self.L, self.canvas
        w, h = L.w, L.h
        t = f * DT
        ctx = c.ctx
        k = k_of_t(t)
        g = cairo.RadialGradient(w / 2, h * 0.46, 0, w / 2, h * 0.46, max(w, h) * 0.7)
        g.add_color_stop_rgb(0.0, 0.06, 0.05, 0.11)
        g.add_color_stop_rgb(1.0, 0.005, 0.005, 0.015)
        ctx.set_source(g)
        ctx.paint()
        cx, cy, R = w / 2, h * 0.455, w * 0.415
        idx = np.arange(N)
        a0 = 2 * np.pi * idx / N - np.pi / 2
        a1 = 2 * np.pi * (k * idx % N) / N - np.pi / 2
        # the rim
        c.ring(cx, cy, R, (0.55, 0.6, 0.85), width=3, alpha=0.5)
        # the chords: additive glow, hue runs round the circle
        ctx.save()
        ctx.set_operator(cairo.OPERATOR_ADD)
        ctx.set_line_width(max(1.5, w * 0.0018))
        for i in range(N):
            col = kit.wheel(i / N)
            ctx.set_source_rgba(col[0], col[1], col[2], 0.30)
            ctx.move_to(cx + R * math.cos(a0[i]), cy + R * math.sin(a0[i]))
            ctx.line_to(cx + R * math.cos(a1[i]), cy + R * math.sin(a1[i]))
            ctx.stroke()
        ctx.restore()
        for i in range(0, N, 6):
            col = kit.wheel(i / N)
            c.circle(cx + R * math.cos(a0[i]), cy + R * math.sin(a0[i]), 4.5, col, alpha=0.95)
        # the multiplier + what it draws
        kk = int(round(k))
        near = abs(k - kk) < 0.06
        c.text_centered(f"× {k:.1f}" if not near else f"× {kk}", h * 0.745, size=w * 0.12, color=GOLD)
        if near:
            nm = CUSPS.get(kk, "")
            c.text_centered(f"{kk - 1} cusp" + ("" if kk == 2 else "s") + (f"  ·  {nm}" if nm else ""),
                            h * 0.790, size=w * 0.045, color=(0.8, 0.85, 1.0), bold=False)
        else:
            c.text_centered("point i  →  point k·i", h * 0.790, size=w * 0.04, color=(0.7, 0.75, 0.9), bold=False)
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
    ev, P = [], audio.PENTA_MAJOR
    def penta(i):
        return 60 + 12 * (i // 5) + P[i % 5]
    for j in range(K0, K1 + 1):                                   # landings: a chord + a soft pulse
        t = (j - K0) * STEP if j < K1 else T_UP - HOLD + SWEEP
        t = (j - K0) * STEP + (0.0 if j == K0 else SWEEP * 0.0)
        root, ch = CHORDS[(j - K0) % 4]
        ev.append({"t": round(t, 4), "note": root, "gain": 0.55, "x": layout.w * 0.5})
        for n_i, n in enumerate(ch):
            ev.append({"t": round(t + 0.03 * n_i, 4), "note": n, "gain": 0.5 - 0.05 * n_i, "x": layout.w * (0.4 + 0.1 * n_i)})
        ev.append({"t": round(t, 4), "note": 36, "note_gain": 0.0, "pok": 0.6, "pok_gain": 0.5, "gain": 0.5, "x": layout.w / 2})
    for j in range(K1 - K0):                                      # the sweeps up: a rising arpeggio
        t0 = j * STEP + HOLD
        for q in range(4):
            ev.append({"t": round(t0 + q * SWEEP / 4, 4), "note": penta(j + q * 2), "gain": 0.36,
                       "x": layout.w * (0.3 + 0.12 * q)})
    n_dn = 4 * (K1 - K0)                                           # the way down: a falling run
    for q in range(n_dn):
        u = q / n_dn
        t = T_UP + T_TOP + T_DOWN * (1 - (1 - u) ** 0.8) if False else T_UP + T_TOP + T_DOWN * u * 0.96
        ev.append({"t": round(t, 4), "note": penta(max(0, (K1 - K0) * 2 + 8 - q)), "gain": 0.30,
                   "x": layout.w * (0.7 - 0.4 * u)})
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
