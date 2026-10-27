"""SPIN WAVE — 15 spinning pendulums, each does ONE more lap than the one inside it (pendulum wave v3).

Bob k (k = 1..15) orbits the centre at radius ∝ k and makes exactly k laps in T seconds: θ_k = 2π k t / T.
A glowing chain joins the bobs in order, so the relative angles draw the pattern: a straight line at t = 0, a
spiral, then at t = (p/m)·T every bob sits on one of m directions → m arms (1/2 → one straight line through the
centre), and at t = T all are back in line: an exact loop. Top: the same motion in 3D (bobs hanging lower the
further out they orbit); bottom: the view from above.
Mechanic inspired by a reference clip (rotating pendulum wave); look, sound and explanations are ours.
Audio (original): each bob plays its own pentatonic note every time it crosses the start line.
"""
import math
import sys
from math import gcd
from pathlib import Path

import cairo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib import kit, studio  # noqa: E402
from lib.kit import DT, FPS, arg  # noqa: E402
from lib.layouts import get_layout  # noqa: E402
from lib.studio import Canvas, VideoWriter  # noqa: E402

SCENE = "spin_wave"
N = 15
T = 15.0
GOLD = (1.0, 0.82, 0.40)
PENTA = [0, 2, 4, 7, 9]
NOTES = [50 + 12 * ((k - 1) // 5) + PENTA[(k - 1) % 5] for k in range(1, N + 1)]   # inner low → outer high
MOMENTS = sorted({(p // gcd(p, m), m // gcd(p, m)) for m in range(2, 6) for p in range(1, m)},
                 key=lambda pm: pm[0] / pm[1])


def col(k):
    hue = 0.0 + 0.70 * (k - 1) / (N - 1)                 # red (inner) → violet (outer)
    h6 = hue * 6
    kk = [(5 + h6) % 6, (3 + h6) % 6, (1 + h6) % 6]
    return tuple(1 - 0.78 * max(0, min(1, min(x, 4 - x))) for x in kk)


def theta(k, t):
    return 2 * math.pi * k * t / T


def simulate():
    return {"nf": int(round(T * FPS))}


class Scene:
    def __init__(self, layout, sim):
        self.L, self.sim = layout, sim
        self.canvas = Canvas(layout.w, layout.h, studio.render_scale())

    def top_xy(self, k, t):
        L = self.L
        r = L.w * 0.30 * k / N
        a = theta(k, t)
        return L.w / 2 + r * math.sin(a), L.h * 0.535 - r * math.cos(a)

    def side_xy(self, k, t):
        L = self.L
        r = L.w * 0.26 * k / N
        a = theta(k, t)
        y = L.h * 0.205 + L.h * 0.105 * k / N
        return L.w / 2 + r * math.sin(a), y - r * 0.30 * math.cos(a)

    def draw(self, f, rule):
        L, c = self.L, self.canvas
        w, h = L.w, L.h
        t = f * DT
        ctx = c.ctx
        g = cairo.RadialGradient(w / 2, h * 0.47, 0, w / 2, h * 0.47, max(w, h) * 0.7)
        g.add_color_stop_rgb(0.0, 0.07, 0.06, 0.11)
        g.add_color_stop_rgb(1.0, 0.01, 0.01, 0.02)
        ctx.set_source(g)
        ctx.paint()
        cx, cy, R = w / 2, h * 0.535, w * 0.30
        # ---- 3D view (top panel)
        y_top, y_bot = h * 0.195, h * 0.205 + h * 0.105
        rs = w * 0.26
        ctx.save()
        ctx.new_path()
        ctx.translate(cx, y_bot)
        ctx.scale(1.0, 0.30)
        ctx.arc(0, 0, rs, 0, 2 * math.pi)
        ctx.restore()
        ctx.set_source_rgba(0.75, 0.78, 0.88, 0.22)
        ctx.set_line_width(2)
        ctx.stroke()
        c.lines([(cx, y_top, cx, y_bot)], (0.75, 0.78, 0.88), width=2, alpha=0.35)
        sp = [(cx, y_top)] + [self.side_xy(k, t) for k in range(1, N + 1)]
        c.polylines([sp], (1, 1, 1), width=2, alpha=0.55)
        for k in range(1, N + 1):
            x, y = sp[k]
            c.circle(x, y, 7, col(k), alpha=1.0)
        c.circle(cx, y_top, 6, (0.9, 0.9, 0.95), alpha=0.9)
        # ---- top view
        ctx.new_path()
        ctx.arc(cx, cy, R + 14, 0, 2 * math.pi)
        ctx.set_source_rgba(0.75, 0.78, 0.88, 0.18)
        ctx.set_line_width(2)
        ctx.stroke()
        c.lines([(cx, cy, cx, cy - R - 14)], GOLD, width=2, alpha=0.30)                # the start line
        for k in range(1, N + 1):                                                       # trails
            col_k = col(k)
            prev = self.top_xy(k, t)
            for j in range(1, 16):
                q = self.top_xy(k, t - j * 0.022)
                c.lines([(prev[0], prev[1], q[0], q[1])], col_k, width=4, alpha=0.40 * (1 - j / 16))
                prev = q
        pts = [(cx, cy)] + [self.top_xy(k, t) for k in range(1, N + 1)]
        c.polylines([pts], (1, 1, 1), width=12, alpha=0.08)
        c.polylines([pts], (1, 1, 1), width=2.5, alpha=0.75)
        for k in range(1, N + 1):
            x, y = pts[k]
            ph = (k * t / T) % 1.0
            hit = math.exp(-ph * T / k / 0.08)                                          # flash after the start line
            c.glow(x, y, 12, col(k), strength=0.45 + 0.6 * hit, reach=3)
            c.circle(x, y, 12, col(k), alpha=1.0)
            c.circle(x - 3.5, y - 3.5, 3.5, (1, 1, 1), alpha=0.6)
        c.circle(cx, cy, 6, (0.9, 0.9, 0.95), alpha=0.9)
        # ---- explanation
        pop = None
        for p, m in MOMENTS:
            tm = T * p / m
            if abs(t - tm) < 0.38:
                pop = (p, m, abs(t - tm))
        if pop:
            p, m, d = pop
            arms = {2: "a straight line", 3: "a triangle", 4: "a square"}.get(m) or                 ("a pentagon" if p in (1, 4) else "a star")             # step = p/m of a turn between bobs
            a = min(1.0, (0.38 - d) / 0.12)
            c.text_centered(f"{p}/{m} of the way  →  {arms}", h * 0.75, size=w * 0.052, color=GOLD, alpha=a)
        else:
            c.text_centered("laps in 15 s:  1, 2, 3 … 15  (inside → outside)", h * 0.75, size=w * 0.033,
                            color=(0.88, 0.89, 0.95), alpha=0.9, bold=False)
        left = T - t
        msg = "back in line!" if (left < 0.3 or t < 0.6) else f"back in line in {left:4.1f} s"
        c.text_centered(msg, h * 0.79, size=w * 0.048, color=(0.95, 0.94, 0.98), alpha=0.95)
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
    """Bob k plays its note each time it crosses the start line (k times per loop); all 15 together at t = 0."""
    out = []
    for k in range(1, N + 1):
        for j in range(k):
            t = j * T / k
            out.append({"t": round(t + 0.004, 4), "note": NOTES[k - 1] + 12, "gain": 0.24 if j else 0.30,
                        "x": layout.w * (0.5 + 0.35 * math.sin(theta(k, t)) * k / N)})
    return sorted(out, key=lambda e: e["t"])


def _worker(o, sim, label, rule):
    layout = get_layout(o)
    name = f"{SCENE}_{label}_{layout.tag}"
    video = studio.OUT_DIR / f"{name}_silent.mp4"
    d = render(layout, sim, video, rule)
    pad = kit.loop_pad(T, ((38, 1.0), (45, 0.7), (50, 0.45), (54, 0.3)), gain=0.014)
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
    print(f"[{SCENE}] {T:.1f}s, moments {MOMENTS}")
    kit.fan_out(_worker, (sim, label, rule), SCENE)


if __name__ == "__main__":
    main()
