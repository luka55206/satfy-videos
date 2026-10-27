"""SPLIT ×3 — every bounce splits a ball into 3: 1 → 3 → 9 → … → 3⁸ = 6,561. Satisfying chaos, run by the math.

Math-first (owner: "math domination"):
- every ball of a generation reaches the circle's wall at the SAME instant (each child gets the speed that carries it
  along its own chord in exactly the generation's time), so the splits are synchronized bursts on the beat and the
  count is exactly 3ⁿ (big on screen: "3⁵ = 243");
- each split shrinks the radius by √3, so 3 × (r/√3)² = r²: the total area NEVER changes (on screen, with a live
  "total area = 100%" meter);
- the children fly off at −ψ, 0, +ψ from the wall's inward normal (ψ ≈ 30°, a seeded jitter per ball so no two paths
  coincide).
After 3⁸ = 6,561 the clock stops, then time runs BACKWARDS: every 3 balls merge into 1 at the wall until the single
ball is back at the centre (loop).
Audio (original, lib/sfx): one burst per generation (a chord pluck that climbs a pentatonic scale + a sparkle whose
density grows with the count, level kept constant), a soft kick, a pad; the rewind plays the bursts falling.
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

SCENE = "split3"
GENS = 8
T_SPLIT = [0.9, 2.3, 3.6, 4.8, 5.9, 6.9, 7.8, 8.6]          # the 8 splits (3⁸ = 6,561 after the last)
T_FLY8 = 10.8                                               # the 6,561 would reach the wall here (frozen before)
T_FREEZE, T_RW0, T_RW1, T_LOOP = 10.0, 11.7, 16.6, 17.0
PSI = 0.52                                                  # ≈ 30°
GOLD, WHITE, SOFT = (1.0, 0.82, 0.35), (0.96, 0.97, 1.0), (0.75, 0.78, 0.92)
SUP = "⁰¹²³⁴⁵⁶⁷⁸⁹"


def gen_color(g):
    h = (0.55 + g * 0.11) % 1.0
    return studio.hsv(h, 0.65, 1.0)


def build():
    """per generation: arrays of start (x,y), end (x,y) on the unit circle."""
    rng = np.random.default_rng(3)
    a0 = rng.uniform(0, 2 * math.pi)
    starts = [np.array([[0.0, 0.0]])]
    ends = [np.array([[math.cos(a0), math.sin(a0)]])]
    ang = np.array([a0])                                    # wall angle of each ball's end point
    for g in range(1, GENS + 1):
        n = len(ang)
        choice = np.tile(np.array([-1.0, 0.0, 1.0]), n)
        par = np.repeat(ang, 3)
        psi = choice * PSI + rng.uniform(-0.16, 0.16, 3 * n)
        new = par + math.pi + 2 * psi                       # chord at angle psi from the inward normal
        starts.append(np.stack([np.cos(par), np.sin(par)], 1))
        ends.append(np.stack([np.cos(new), np.sin(new)], 1))
        ang = new
    return starts, ends


STARTS, ENDS = build()


def sim_t(t):
    """video time -> simulation time (forward, frozen, rewind)."""
    if t < T_FREEZE:
        return t
    if t < T_RW0:
        return T_FREEZE
    if t < T_RW1:
        u = (t - T_RW0) / (T_RW1 - T_RW0)
        return T_FREEZE * (1 - smooth(u))
    return 0.0


def gen_at(ts):
    g = 0
    for k in range(GENS):
        if ts >= T_SPLIT[k]:
            g = k + 1
    return g


class Scene:
    def __init__(self, layout):
        self.L = layout
        self.canvas = Canvas(layout.w, layout.h, studio.render_scale())

    def draw(self, f, rule):
        L, c = self.L, self.canvas
        w, h = L.w, L.h
        t = f * DT
        ctx = c.ctx
        g_ = cairo.RadialGradient(w / 2, h * 0.45, 0, w / 2, h * 0.45, h * 0.7)
        g_.add_color_stop_rgb(0, 0.06, 0.05, 0.12)
        g_.add_color_stop_rgb(1, 0.005, 0.005, 0.015)
        ctx.set_source(g_)
        ctx.paint()
        ts = sim_t(t)
        g = gen_at(ts)
        t0 = 0.0 if g == 0 else T_SPLIT[g - 1]
        t1 = T_SPLIT[g] if g < len(T_SPLIT) else T_FLY8
        u = min(1.0, max(0.0, (ts - t0) / (t1 - t0)))
        cx, cy, R = w / 2, h * 0.47, w * 0.36
        r0 = R * 0.11
        col = gen_color(g)
        # the arena
        c.glow(cx, cy, R * 1.04, col, strength=0.12, reach=1.25)
        c.ring(cx, cy, R, col, width=5, alpha=0.9)
        # the balls of generation g, moving along their chords
        P = STARTS[g] + (ENDS[g] - STARTS[g]) * u
        xs, ys = cx + P[:, 0] * R, cy - P[:, 1] * R
        rad = max(1.4, r0 / math.sqrt(3) ** g)
        if g <= 4:
            for x, y in zip(xs, ys):
                c.glow(x, y, rad * 2.2, col, strength=0.35, reach=1.8)
        ctx.set_source_rgba(*col, 0.95)
        for x, y in zip(xs, ys):
            ctx.new_sub_path()
            ctx.arc(x, y, rad, 0, 2 * math.pi)
        ctx.fill()
        # split flashes on the wall (forward: a ring burst; rewind: merging)
        for k in range(GENS):
            age = ts - T_SPLIT[k]
            if 0 <= age < 0.25:
                E = ENDS[k]
                a = 1 - age / 0.25
                for x, y in zip(cx + E[:, 0] * R, cy - E[:, 1] * R):
                    c.ring(x, y, r0 / math.sqrt(3) ** k * (1 + 3 * age / 0.25), WHITE, width=2, alpha=0.6 * a)
        # MATH, big: the count, the rule, the area
        n = 3 ** g
        pop = 0.0
        if g >= 1:
            pop = math.exp(-max(0.0, ts - T_SPLIT[g - 1]) / 0.12) if t < T_FREEZE else 0.0
        frozen = T_FREEZE <= t < T_RW0
        c.text_centered(f"3{SUP[g]} = {n:,}", h * 0.215, size=w * 0.13 * (1 + 0.25 * pop), color=GOLD if frozen else WHITE)
        c.text_centered("balls", h * 0.25, size=w * 0.04, color=SOFT, bold=False)
        if T_RW0 <= t < T_RW1:
            line, sub = "time runs backwards: 3 → 1", "every 3 balls merge into one"
        elif frozen:
            line, sub = "3 × (r ÷ √3)² = r²", "6,561 balls… and the total area never changed"
        else:
            line, sub = "every bounce: 1 ball → 3", "each new ball: radius ÷ √3"
        c.text_centered(line, h * 0.76, size=w * 0.06, color=GOLD if frozen else WHITE, max_w=w * 0.94)
        c.text_centered(sub, h * 0.795, size=w * 0.038, color=SOFT, bold=False, max_w=w * 0.94)
        # the area meter: n × r² stays 100% (drawn as a bar that never moves, the count racing next to it)
        bx0, bx1, by = w * 0.2, w * 0.8, h * 0.71
        c.lines([(bx0, by, bx1, by)], col, width=12, alpha=0.9)
        c.text_centered(f"total area: {n} × (r/√3{SUP[g] if g > 1 else ''})² = 100%" if g >= 1 else "total area: 100%",
                        by - h * 0.012, size=w * 0.032, color=SOFT, bold=False, max_w=w * 0.9)
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


def burst(b, t0, g, up=True):
    """one split: a plucked chord climbing the scale + a sparkle that gets denser with the count."""
    penta = [0, 2, 4, 7, 9]
    root = 57 + 12 * ((2 * g) // 5) + penta[(2 * g) % 5]
    for k, iv in enumerate((0, 4, 7, 12)):
        b.pluck(t0 + 0.012 * k, root + iv, 0.10, d=0.6)
    nsp = min(40, 3 ** min(g + 1, 4))
    rng = np.random.default_rng(g + (0 if up else 99))
    for q in range(nsp):
        tt = t0 + rng.uniform(0, 0.12)
        b.tick(tt, rng.uniform(3500, 7500), 0.03 / math.sqrt(nsp / 3))
    tv = np.arange(int(0.25 * sfx.SR)) / sfx.SR
    b.add(t0, np.sin(2 * np.pi * np.cumsum(55 + 90 * np.exp(-tv / 0.03)) / sfx.SR) * np.exp(-tv / 0.12), 0.25)


def sound():
    b = sfx.Bed(T_LOOP, seed=29)
    b.pad([(0.0, (45, 52, 57, 64)), (T_SPLIT[3], (41, 48, 57, 60)), (T_SPLIT[6], (43, 50, 55, 62)),
           (T_FREEZE, (45, 52, 57, 64, 69))], 0.6, g=0.05)
    for g in range(GENS):
        burst(b, T_SPLIT[g], g)
    b.hit(T_SPLIT[-1], 0.4)
    b.chime(T_FREEZE, (72, 76, 79, 84, 88), 0.07, decay=1.0)
    for g in range(GENS - 1, -1, -1):                        # the rewind passes every split again, backwards
        u = 1 - T_SPLIT[g] / T_FREEZE                        # sim_t falls with smooth(u); find when it crosses
        lo, hi = 0.0, 1.0
        for _ in range(40):
            mid = (lo + hi) / 2
            if T_FREEZE * (1 - smooth(mid)) > T_SPLIT[g]:
                lo = mid
            else:
                hi = mid
        tt = T_RW0 + hi * (T_RW1 - T_RW0)
        b.pluck(tt, 57 + 12 * ((2 * g) // 5) + [0, 2, 4, 7, 9][(2 * g) % 5], 0.08, d=0.5)
    b.drop(T_RW0, T_RW1 - T_RW0, 0.05, 1600, 200)
    return b.get()


def main():
    label, rule = arg("--label", "v1"), arg("--rule", "")
    studio.OUT_DIR.mkdir(exist_ok=True)
    layout = get_layout(kit.orients()[0])
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
