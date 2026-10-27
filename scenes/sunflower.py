"""SUNFLOWER — seeds turned by one angle; at 137.508° (360°/phi²) they become a sunflower.

Vogel's model: seed n sits at radius sqrt(n), turned n x angle. 1,500 seeds are on screen
from frame 0 while the angle sweeps from 134° toward the golden angle; every tiny change
reshuffles the whole head (spokes, curved arms, ever finer spirals: the motion is the hook).
At exactly 137.508° the seeds pack perfectly and 34 petals bloom around them: a sunflower.
NONSTOP LOOP: after the bloom the petals fold away and the angle glides back to 134°, the
exact frame-0 state, and the sweep starts again.

Audio (original synthesis only): glass-harp notes that come faster and climb as the angle
closes in, a chord and chime at the lock, soft falling notes on the way back, a periodic pad.

    ./run.ps1 -Scene sunflower -Fast -Still -Frame 600
    ./run.ps1 -Scene sunflower -Fast
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

SCENE = "sunflower"
PHI = (1 + 5 ** 0.5) / 2
GOLD_DEG = 360.0 / PHI ** 2                  # 137.5077640...
A0 = 134.0
N_SEEDS = 1500
N_PETALS = 34
T_SWEEP, T_BLOOM, T_BACK = 11.0, 3.2, 2.8
T_LOOP = T_SWEEP + T_BLOOM + T_BACK
K_NOTES = 26


def angle_at(t):
    if t < T_SWEEP:
        u = t / T_SWEEP
        return A0 + (GOLD_DEG - A0) * (1 - (1 - u) ** 1.6)
    if t < T_SWEEP + T_BLOOM:
        return GOLD_DEG
    v = smooth((t - T_SWEEP - T_BLOOM) / T_BACK)
    return GOLD_DEG + (A0 - GOLD_DEG) * v


def bloom_at(t):
    a = smooth((t - T_SWEEP) / 0.9)
    b = 1.0 - smooth((t - T_SWEEP - T_BLOOM + 0.3) / 1.2)
    return max(0.0, min(a, b))


def simulate():
    return {"nf": int(round(T_LOOP * FPS))}


def seed_colour(u):
    stops = [(0.0, (0.25, 0.12, 0.05)), (0.45, (0.55, 0.30, 0.09)), (0.8, (0.90, 0.60, 0.16)),
             (1.0, (1.00, 0.82, 0.32))]
    for (u0, c0), (u1, c1) in zip(stops, stops[1:]):
        if u <= u1:
            k = (u - u0) / (u1 - u0)
            return tuple(a + (b - a) * k for a, b in zip(c0, c1))
    return stops[-1][1]


class Scene:
    def __init__(self, layout, sim):
        self.L, self.sim = layout, sim
        self.canvas = Canvas(layout.w, layout.h, studio.render_scale())
        self.vertical = layout.h > layout.w
        w, h = layout.w, layout.h
        self.c = (w / 2, h * (0.43 if self.vertical else 0.50))
        self.R = (w * 0.30) if self.vertical else (h * 0.30)
        k = np.arange(N_SEEDS) + 0.5
        self.rad = self.R * np.sqrt(k / N_SEEDS)
        self.cols = [seed_colour(u) for u in np.sqrt(k / N_SEEDS)]
        self.size = self.R / math.sqrt(N_SEEDS) * 0.52

    def petals(self, ctx, bloom, t):
        if bloom <= 0.002:
            return
        cx, cy = self.c
        rot = 0.15 * t
        for i in range(N_PETALS):
            a = rot + 2 * math.pi * i / N_PETALS
            L = self.R * (0.22 * bloom + 0.02) * (1.0 + 0.06 * math.sin(i * 2.3))
            wdt = self.R * 0.085 * bloom
            ctx.save()
            ctx.translate(cx + math.cos(a) * self.R * 0.97, cy + math.sin(a) * self.R * 0.97)
            ctx.rotate(a)
            ctx.scale(L, wdt)
            ctx.arc(1.0, 0, 1.0, 0, 2 * math.pi)
            ctx.restore()
            g = (1.0, 0.80 - 0.08 * (i % 3) / 2, 0.18)
            ctx.set_source_rgba(*g, 0.92 * min(1.0, bloom * 1.4))
            ctx.fill_preserve()
            ctx.set_source_rgba(0.85, 0.55, 0.05, 0.6 * bloom)
            ctx.set_line_width(1.5)
            ctx.stroke()

    def draw(self, f, rule):
        L, c = self.L, self.canvas
        w, h = L.w, L.h
        t = f * DT
        ang = angle_at(t)
        bloom = bloom_at(t)
        ctx = c.ctx
        g = cairo.RadialGradient(w / 2, self.c[1], 0, w / 2, self.c[1], max(w, h) * 0.7)
        g.add_color_stop_rgb(0.0, 0.07 + 0.05 * bloom, 0.06 + 0.04 * bloom, 0.03)
        g.add_color_stop_rgb(1.0, 0.01, 0.015, 0.01)
        ctx.set_source(g)
        ctx.paint()
        self.petals(ctx, bloom, t)
        th = np.arange(N_SEEDS) * math.radians(ang)
        xs = self.c[0] + self.rad * np.cos(th)
        ys = self.c[1] - self.rad * np.sin(th)
        s = self.size * (1.0 + 0.12 * bloom)
        for i in range(N_SEEDS):
            ctx.new_sub_path()
            ctx.arc(xs[i], ys[i], s * (0.75 + 0.35 * i / N_SEEDS), 0, 2 * math.pi)
            ctx.set_source_rgb(*self.cols[i])
            ctx.fill()

        fs = w * (0.05 if self.vertical else 0.026)
        eq_y, a_y = (h * 0.165, h * 0.770) if self.vertical else (h * 0.07, h * 0.95)
        c.text_centered("seed n:   r = √n,   θ = n × angle", eq_y, size=fs * 0.62,
                        color=(0.95, 0.93, 0.88), alpha=0.85, bold=False)
        locked = abs(ang - GOLD_DEG) < 5e-4
        if locked:
            c.text_centered("angle = 137.508° = 360°/φ²", a_y, size=fs * 1.05, color=(1.0, 0.84, 0.35))
        else:
            c.text_centered(f"angle = {ang:.3f}°", a_y, size=fs * 1.05, color=(1, 1, 1))
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
    walker = audio.ScaleWalker(root_midi=62, scale=audio.PENTA_MAJOR, span=12, pattern="up")
    out = []
    for k in range(K_NOTES):                         # denser and higher as the angle closes in
        t = T_SWEEP * (1 - (1 - (k + 0.5) / K_NOTES) ** 0.55)
        out.append({"t": round(t, 4), "note": walker.next(), "gain": round(0.34 + 0.16 * k / K_NOTES, 3),
                    "x": round(layout.w * (0.5 + 0.25 * math.sin(k * 2.4)), 1)})
    for j, note in enumerate((50, 57, 62, 66, 69, 74)):
        out.append({"t": round(T_SWEEP + 0.06 * j, 4), "note": note, "gain": 0.45, "x": layout.w / 2})
    out.append({"t": round(T_SWEEP + 0.45, 4), "note": 86, "gain": 0.32, "x": layout.w / 2})
    for j, note in enumerate((81, 78, 74, 71, 69, 66)):
        out.append({"t": round(T_SWEEP + T_BLOOM + 0.2 + 0.38 * j, 4), "note": note, "gain": 0.26,
                    "x": layout.w / 2})
    return sorted(out, key=lambda e: e["t"])


def pad(sim):
    return kit.loop_pad(T_LOOP, ((50, 1.0), (57, 0.7), (62, 0.45), (66, 0.3)), gain=0.016)


def _worker(o, sim, label, rule):
    layout = get_layout(o)
    name = f"{SCENE}_{label}_{layout.tag}"
    video = studio.OUT_DIR / f"{name}_silent.mp4"
    d = render(layout, sim, video, rule)
    kit.deliver_loop(SCENE, name, layout, video, build_events(sim, layout), d,
                     voice="glassharp", bed=pad(sim))


def main():
    label, rule = arg("--label", "v1"), arg("--rule", "")
    studio.OUT_DIR.mkdir(exist_ok=True)
    sim = simulate()
    if kit.has("--still"):
        layout = get_layout(kit.orients()[0])
        f = int(arg("--frame", "600"))
        png = studio.OUT_DIR / f"{SCENE}_{label}_f{f}_{layout.tag}.png"
        render(layout, sim, png, rule, still_frame=f)
        print(f"[{SCENE}] -> {png}")
        return
    print(f"[{SCENE}] {T_LOOP:.1f}s golden={GOLD_DEG:.5f}")
    kit.fan_out(_worker, (sim, label, rule), SCENE)


if __name__ == "__main__":
    main()
