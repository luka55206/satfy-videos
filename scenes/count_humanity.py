"""COUNT HUMANITY — counting engine episode: what if ALL 8 billion people count together, each saying a different
number every second (8,000,000,000 numbers per second)?
A million: 0.0001 s · a billion: 0.125 s · a trillion: 2 minutes · a quadrillion: 35 hours · a quintillion: 4 years ·
a sextillion: 4,000 years · a googol: 4 × 10⁸² years (the universe is 1.4 × 10¹⁰ years old).
Each rung also shows how long ONE person alone would take (1 number per second).

Nameable change vs the shipped counting Shorts (million / billion / trillion / googol / infinity, one counter): the
whole planet counts at once, and even that cannot reach a googol.
Loop: the counter rolls back to 0 (frame 0).
Audio (original, lib/sfx): light marimba bed, a rising roll (ticks) per rung, a chime when each number lands, a low hit
+ chord on the googol, a falling sweep on the rewind.
"""
import math
import sys
from pathlib import Path

import cairo
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib import kit, sfx, studio  # noqa: E402
from lib.kit import DT, FPS, arg, smooth  # noqa: E402
from lib.layouts import get_layout  # noqa: E402
from lib.studio import Canvas, VideoWriter  # noqa: E402
from scenes.pi_long import Scene as Art, marimba, sup  # noqa: E402

SCENE = "count_humanity"
GOLD, WHITE, SOFT, CYAN, LIME = (1.0, 0.8, 0.3), (0.96, 0.97, 1.0), (0.75, 0.78, 0.92), (0.35, 0.85, 1.0), (0.55, 1.0, 0.55)
PEOPLE = 8e9
# (exponent, name, time with everyone, one person alone)
RUNGS = [(6, "A MILLION", "0.0001 seconds", "alone: 11.6 days"),
         (9, "A BILLION", "0.125 seconds", "alone: 31.7 years"),
         (12, "A TRILLION", "2 minutes", "alone: 31,700 years"),
         (15, "A QUADRILLION", "35 hours", "alone: 31.7 million years"),
         (18, "A QUINTILLION", "4 years", "alone: 31.7 billion years"),
         (21, "A SEXTILLION", "4,000 years", "alone: 31.7 trillion years"),
         (100, "A GOOGOL", "4 × 10⁸² years", "the universe is only 1.4 × 10¹⁰ years old")]
T0_R, RUNG = 0.7, 1.9
T_R = [T0_R + i * RUNG for i in range(len(RUNGS))]
ROLL = 0.9
T_GOOGOL_END = T_R[-1] + RUNG + 1.8
T_RW0, T_RW1 = T_GOOGOL_END, T_GOOGOL_END + 1.0
T_LOOP = T_RW1 + 0.3


def clamp(v, a=0.0, b=1.0):
    return max(a, min(b, v))


def check():
    for e, name, *_ in RUNGS:
        s = 10.0 ** e / PEOPLE
        print(f"  {name}: {s:.4g} s = {s / 3600:.4g} h = {s / 3.156e7:.4g} y   alone {10.0 ** e / 3.156e7:.4g} y")


def log_value(t):
    """log10 of the counter value at time t (-inf = 0)."""
    if t >= T_RW0:
        return RUNGS[-1][0] * (1 - smooth(clamp((t - T_RW0) / (T_RW1 - T_RW0)))) - 0.01
    lv = -1.0
    prev = 0.0
    for i, (e, *_r) in enumerate(RUNGS):
        if t >= T_R[i]:
            lv = prev + (e - prev) * smooth(clamp((t - T_R[i]) / ROLL))
        prev = e
    return lv


def fmt(lv):
    if lv < 0:
        return "0"
    if lv > 23.5:
        return f"10{sup(int(round(lv)))}"
    return f"{int(round(10 ** lv)):,}"


class Scene:
    def __init__(self, layout):
        self.L = layout
        self.canvas = Canvas(layout.w, layout.h, studio.render_scale())
        self.art = Art.__new__(Art)
        self.art.canvas, self.art.L = self.canvas, layout
        rng = np.random.default_rng(8)
        r = np.sqrt(rng.uniform(0, 1, 420)) * 0.92
        a = rng.uniform(0, 2 * np.pi, 420)
        self.dots = list(zip(r * np.cos(a), r * np.sin(a), rng.uniform(0, 2 * np.pi, 420), rng.uniform(4, 9, 420)))

    def draw(self, f, rule):
        L, c = self.L, self.canvas
        w, h = L.w, L.h
        t = f * DT
        ctx = c.ctx
        g = cairo.RadialGradient(w / 2, h * 0.45, 0, w / 2, h * 0.45, h * 0.7)
        g.add_color_stop_rgb(0, 0.06, 0.07, 0.14)
        g.add_color_stop_rgb(1, 0.005, 0.005, 0.015)
        ctx.set_source(g)
        ctx.paint()
        ex, ey, S = w * 0.5, h * 0.50, w * 0.56
        self.art.draw_object("earth", ex, ey, S)
        rolling = any(T_R[i] <= t < T_R[i] + ROLL for i in range(len(RUNGS))) or T_RW0 <= t < T_RW1
        R = S * 0.4
        for dx, dy, ph, sp in self.dots:                          # everyone, saying a number
            k = 0.5 + 0.5 * math.sin(ph + 2 * math.pi * round(sp * T_LOOP / (2 * math.pi)) * t / T_LOOP)
            k = min(1.0, k * (1.4 if rolling else 1.0))           # whole cycles per loop: the seam is exact
            c.circle(ex + dx * R, ey + dy * R, w * (0.004 + 0.003 * k), (1.0, 0.92, 0.6), alpha=0.35 + 0.6 * k)
        # HUD: the counter
        lv = log_value(t)
        done_g = T_R[-1] + ROLL <= t < T_RW0
        c.text_centered(fmt(lv), h * 0.275, size=w * (0.11 if lv < 12.5 else 0.085 if lv <= 23.5 else 0.14), color=GOLD if done_g else WHITE,
                        max_w=w * 0.94)
        c.text_centered("8,000,000,000 numbers every second", h * 0.31, size=w * 0.04, color=SOFT, bold=False)
        # the rung
        i = max([k for k in range(len(RUNGS)) if t >= T_R[k]], default=-1) if t < T_RW0 else -1
        if i < 0:
            a = 1.0 if t < T_R[0] else clamp((t - T_RW1) / 0.25)
            c.text_centered("ALL 8 BILLION PEOPLE", h * 0.77, size=w * 0.075, color=WHITE, alpha=a)
            c.text_centered("count together, one number each per second", h * 0.805, size=w * 0.04, color=SOFT,
                            bold=False, alpha=a)
        else:
            e, name, tog, alone = RUNGS[i]
            u = t - T_R[i]
            land = u - ROLL
            a = clamp(u / 0.2)
            c.text_centered(name, h * 0.755, size=w * 0.07, color=WHITE, alpha=a)
            if land >= 0:
                pop = math.exp(-land / 0.18)
                big = i == len(RUNGS) - 1
                c.text_centered(tog, h * 0.80, size=w * (0.08 if big else 0.075) * (1 + 0.15 * pop),
                                color=GOLD, max_w=w * 0.94)
                c.text_centered(alone, h * 0.835, size=w * 0.04, color=LIME if big else SOFT, bold=big,
                                alpha=clamp(land / 0.25), max_w=w * 0.94)
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


def sound():
    b = sfx.Bed(T_LOOP, seed=31)
    arp = [(69, 72, 76, 81), (65, 69, 72, 77), (64, 67, 72, 76), (67, 71, 74, 79)]
    pat = [0, 2, 1, 3, 2, 1, 3, 2]
    t, q = 0.0, 0
    while t < T_LOOP - 0.2:
        marimba(b, t, arp[int(t // 3.2) % 4][pat[q % 8]], 0.018 if q % 4 else 0.024)
        t += 0.4
        q += 1
    for i, t0 in enumerate(T_R):
        for k in range(10):                                      # the roll: rising ticks
            b.tick(t0 + ROLL * (0.5 - 0.5 * math.cos(math.pi * k / 9)), 2000 + 60 * k + 80 * i, 0.03)
        if i < len(RUNGS) - 1:
            b.chime(t0 + ROLL + 0.01, (76 + i, 81 + i), 0.06)
    b.hit(T_R[-1] + ROLL, 0.3, low=65)
    b.chime(T_R[-1] + ROLL + 0.02, (69, 72, 76, 81, 84, 88), 0.07, decay=1.2)
    b.drop(T_RW0, T_RW1 - T_RW0, 0.05, 1400, 220)
    return b.get()


def main():
    label, rule = arg("--label", "v1"), arg("--rule", "")
    studio.OUT_DIR.mkdir(exist_ok=True)
    layout = get_layout(kit.orients()[0])
    print(f"[{SCENE}] {T_LOOP:.2f}s")
    check()
    if kit.has("--still"):
        f = int(round(float(arg("--at")) * FPS)) if arg("--at") else int(arg("--frame", "0"))
        png = studio.OUT_DIR / f"{SCENE}_{label}_f{f}_{layout.tag}.png"
        render(layout, png, rule, still_frame=f)
        print(f"[{SCENE}] -> {png}")
        return
    name = f"{SCENE}_{label}_{layout.tag}"
    video = studio.OUT_DIR / f"{name}_silent.mp4"
    d = render(layout, video, rule)
    kit.deliver_loop(SCENE, name, layout, video, [], d, voice="piano", bed=sound(), peak_db=-6.0)


if __name__ == "__main__":
    main()
