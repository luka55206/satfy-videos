"""PENDULUM WAVE (v2: 3/4 view of real pendulums, explained on screen) — 15 pendulums, 15 lengths, one exact realignment (physics test).

Pendulum i swings N_i = 12 + i times in T_CYCLE seconds, so f_i = N_i / T_CYCLE and, from T = 2π√(L/g),
L_i = g / (2π f_i)². Seen from above, the bobs start in one line, drift into travelling snakes, split into
2 rows at T/2 and 3 groups at T/3, and are back in one line at T_CYCLE: an exact, physical loop.
Sound (original): each pendulum plays its own pentatonic note at the right end of its swing (longer = lower).
"""
import math
import sys
from pathlib import Path

import cairo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib import kit, studio  # noqa: E402
from lib.kit import DT, FPS, arg  # noqa: E402
from lib.layouts import get_layout  # noqa: E402
from lib.studio import Canvas, VideoWriter  # noqa: E402

SCENE = "pendulum_wave"
N = 15
N0 = 12
T_CYCLE = 18.0
G = 9.81
FREQ = [(N0 + i) / T_CYCLE for i in range(N)]
LEN = [G / (2 * math.pi * f) ** 2 for f in FREQ]
PENTA = [0, 2, 4, 7, 9]
NOTES = [45 + 12 * (i // 5) + PENTA[i % 5] for i in range(N)]     # A minor pentatonic, low (long) → high (short)
GOLD = (1.0, 0.82, 0.40)


def col(i):
    hue = 0.62 - 0.62 * i / (N - 1)                                # blue → red
    h6 = hue * 6
    k = [(5 + h6) % 6, (3 + h6) % 6, (1 + h6) % 6]
    return tuple(1 - 0.75 * max(0, min(1, min(x, 4 - x))) for x in k)


def simulate():
    return {"nf": int(round(T_CYCLE * FPS))}


def x_of(i, t):
    return math.cos(2 * math.pi * FREQ[i] * t)


class Scene:
    def __init__(self, layout, sim):
        self.L, self.sim = layout, sim
        self.canvas = Canvas(layout.w, layout.h, studio.render_scale())

    def draw(self, f, rule):
        """3/4 view of real pendulums on a bar: long (slow) on the left, short (fast) on the right."""
        L, c = self.L, self.canvas
        w, h = L.w, L.h
        t = f * DT
        ctx = c.ctx
        g = cairo.RadialGradient(w / 2, h * 0.47, 0, w / 2, h * 0.47, max(w, h) * 0.7)
        g.add_color_stop_rgb(0.0, 0.07, 0.06, 0.11)
        g.add_color_stop_rgb(1.0, 0.01, 0.01, 0.02)
        ctx.set_source(g)
        ctx.paint()
        xa, xb, yb = w * 0.10, w * 0.80, h * 0.285          # the bar (pivots)
        Lmax = h * 0.37
        dzx, dzy = 0.42, -0.20                              # screen direction of the swing (depth, 3/4 view)
        A = w * 0.20

        def bob(i, tt):
            px = xa + (xb - xa) * i / (N - 1)
            Li = Lmax * LEN[i] / LEN[0]
            z = A * x_of(i, tt)
            return px, px + z * dzx, yb + Li + z * dzy, z

        # floor guide: each bob's swing track (faint)
        for i in range(N):
            px, _, by, _ = bob(i, 0.0)
            by0 = yb + Lmax * LEN[i] / LEN[0]
            c.lines([(px - A * dzx, by0 - A * dzy, px + A * dzx, by0 + A * dzy)], col(i), width=1.2, alpha=0.14)
        c.lines([(xa - w * 0.04, yb, xb + w * 0.04, yb)], (0.80, 0.82, 0.90), width=7, alpha=0.75)   # the bar
        order = sorted(range(N), key=lambda i: bob(i, t)[3])     # far bobs first
        for i in order:
            px, bx, by, z = bob(i, t)
            cl = col(i)
            depth = 1 + 0.18 * z / A
            for k in range(5, 0, -1):                           # motion ghosts
                _, gx, gy, _ = bob(i, t - k * 0.02)
                c.circle(gx, gy, 13 * depth, cl, alpha=0.05 * (6 - k))
            c.lines([(px, yb, bx, by)], (0.85, 0.85, 0.9), width=2, alpha=0.55)
            ph = (FREQ[i] * t) % 1.0
            hit = math.exp(-ph / FREQ[i] / 0.05 * FREQ[i] * 0 - ph * 12)
            c.glow(bx, by, 15 * depth, cl, strength=0.45 + 0.5 * hit, reach=3)
            c.circle(bx, by, 15 * depth, cl, alpha=1.0)
            c.circle(bx - 4 * depth, by - 4 * depth, 4.5 * depth, (1, 1, 1), alpha=0.55)
        # the explanation, right on the picture
        c.text_centered("swings in 18 s:", yb - h * 0.052, size=h * 0.015, color=(0.75, 0.78, 0.88), alpha=0.8,
                        cx=(xa + xb) / 2)
        for i in range(N):
            px = xa + (xb - xa) * i / (N - 1)
            c.text_centered(str(N0 + i), yb - h * 0.018, size=h * 0.0165, color=col(i), alpha=0.95, cx=px)
        c.text_centered("LONG = slow", yb + Lmax + h * 0.012, size=w * 0.04, color=col(0), alpha=0.95, cx=w * 0.36)
        c.text_centered("SHORT = fast", yb + Lmax * LEN[-1] / LEN[0] + h * 0.075, size=w * 0.04, color=col(N - 1),
                        alpha=0.95, cx=w * 0.80)
        left = T_CYCLE - t
        c.text_centered("each one swings 1 more time than its neighbour", h * 0.745, size=w * 0.033,
                        color=(0.92, 0.92, 0.96), alpha=0.9, bold=False)
        msg = "back in line!" if (left < 0.3 or t < 0.6) else f"back in line in {left:4.1f} s"
        c.text_centered(msg, h * 0.785, size=w * 0.048, color=GOLD, alpha=0.95)
        c.text_centered("PHYSICS · PENDULUM WAVE", h * 0.205, size=h * 0.015, color=GOLD, alpha=0.85)
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
    """One note per pendulum each time it reaches the right end of its swing (t = k / f_i)."""
    out = []
    for i in range(N):
        for k in range(N0 + i):
            t = k / FREQ[i]
            out.append({"t": round(t + 0.004, 4), "note": NOTES[i] + 12, "gain": 0.20 if k else 0.30,
                        "x": layout.w * (0.25 + 0.5 * i / (N - 1))})
    return sorted(out, key=lambda e: e["t"])


def _worker(o, sim, label, rule):
    layout = get_layout(o)
    name = f"{SCENE}_{label}_{layout.tag}"
    video = studio.OUT_DIR / f"{name}_silent.mp4"
    d = render(layout, sim, video, rule)
    pad = kit.loop_pad(T_CYCLE, ((45, 1.0), (52, 0.7), (57, 0.45), (60, 0.3)), gain=0.012)
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
    print(f"[{SCENE}] {T_CYCLE:.1f}s, lengths {LEN[0]:.3f}..{LEN[-1]:.3f} m")
    kit.fan_out(_worker, (sim, label, rule), SCENE)


if __name__ == "__main__":
    main()
