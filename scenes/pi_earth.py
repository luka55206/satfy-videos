"""PI EARTH — π blocks episode: the big block is 1/6 of the EARTH (10²⁴ kg) against a 1 kg block:
3,141,592,653,589 collisions = 13 digits of π.

Nameable change vs the shipped π blocks Shorts: the block is (a sixth of) a planet. Count: the exact formula
N = ceil(π/θ) − 1, θ = arctan(√(m/M)) (scenes/pi_long.n_hits; it matches every simulated count). The burst lasts 3 s.
Then the ladder: 1 kg → 3, 100 kg → 31, 10,000 kg → 314, … 10²⁴ kg → 13 digits ("every ×100 adds a digit").
Loop: the card grows back into the big Earth (frame 0). Set its Related video to the π blocks long-form.
"""
import math
import sys
from pathlib import Path

import cairo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib import kit, sfx, studio  # noqa: E402
from lib.kit import DT, FPS, arg, smooth  # noqa: E402
from lib.layouts import get_layout  # noqa: E402
from lib.studio import Canvas, VideoWriter  # noqa: E402
from scenes import pi_long  # noqa: E402

SCENE = "pi_earth"
M = 1e24
N = pi_long.n_hits(M)
GOLD, WHITE, SOFT, CYAN = pi_long.GOLD, pi_long.WHITE, pi_long.SOFT, pi_long.CYAN
T_SHRINK0, T_SHRINK1 = 1.6, 2.6
T_B0, T_B1 = 3.0, 6.0
T_LAD = 8.6
T_BACK0, T_BACK1, T_LOOP = 14.0, 15.4, 16.0
FLOOR = 0.62
LADDER = [("1 kg", "3"), ("100 kg", "31"), ("10,000 kg", "314"), ("1,000,000 kg", "3,141"), ("…", ""),
          ("10²⁴ kg", "3,141,592,653,589")]


def clamp(v, a=0.0, b=1.0):
    return max(a, min(b, v))


class Stage(pi_long.Scene):
    def stage(self, x1, x2, M_, icon="M", flash=0.0, flash_x=None, area=(0.06, 0.94), fy=FLOOR, label=True):
        return super().stage(x1, x2, M_, icon, flash, flash_x, area=(0.06, 0.94), fy=FLOOR, label=label)


class Scene:
    def __init__(self, layout):
        self.L = layout
        self.canvas = Canvas(layout.w, layout.h, studio.render_scale())
        self.st = Stage.__new__(Stage)
        self.st.canvas, self.st.L = self.canvas, layout

    def draw(self, f, rule):
        L, c = self.L, self.canvas
        w, h = L.w, L.h
        t = f * DT
        ctx = c.ctx
        g = cairo.RadialGradient(w / 2, h * 0.42, 0, w / 2, h * 0.42, h * 0.7)
        g.add_color_stop_rgb(0, 0.06, 0.06, 0.12)
        g.add_color_stop_rgb(1, 0.005, 0.005, 0.015)
        ctx.set_source(g)
        ctx.paint()
        big = t < T_SHRINK1 or t >= T_BACK0
        if big:                                                   # the Earth, big (frame 0 and the loop)
            if t < T_SHRINK0 or t >= T_BACK1:
                v = 0.0
            elif t < T_SHRINK1:
                v = smooth((t - T_SHRINK0) / (T_SHRINK1 - T_SHRINK0))
            else:
                v = 1 - smooth((t - T_BACK0) / (T_BACK1 - T_BACK0))
            cx = w * 0.5 + (w * 0.756 - w * 0.5) * v
            cy = h * 0.42 + (h * FLOOR - w * 0.15 - h * 0.42) * v
            S = w * 0.75 + (w * 0.26 - w * 0.75) * v
            self.st.draw_object("earth", cx, cy, S)
            if v < 0.5:
                c.text_centered("1/6 OF THE EARTH", h * 0.215, size=w * 0.085, color=GOLD, alpha=1 - 2 * v)
                c.text_centered("10²⁴ kg  vs  a 1 kg block", h * 0.25, size=w * 0.045, color=SOFT, bold=False,
                                alpha=1 - 2 * v)
                c.ctx.rectangle(w * 0.12, h * 0.70, w * 0.06, w * 0.06)
                c.ctx.set_source_rgba(*CYAN, 1 - 2 * v)
                c.ctx.fill()
                c.text_centered("1 kg", h * 0.70 + w * 0.1, size=w * 0.04, color=CYAN, alpha=1 - 2 * v, cx=w * 0.15)
                c.text_centered("How many collisions?", h * 0.78, size=w * 0.055, color=WHITE, alpha=1 - 2 * v)
        else:
            bu = (t - T_B0) / (T_B1 - T_B0)
            self.st.burst_stage(clamp(bu) if bu > 0 else 0.0, M, "earth")
            frac = 0.5 - 0.5 * math.cos(math.pi * clamp(bu))
            cx, cy, R = w * 0.5, h * 0.31, h * 0.1
            done = bu >= 1
            self.st.ring(cx, cy, R, frac, N, done_glow=clamp((bu - 1) * 3) if done else 0.0)
            n = int(round(N * frac)) if not done else N
            pop = math.exp(-(t - T_B1) / 0.15) if done else 0.0
            c.text_centered(f"{n:,}", cy + R * 0.12, size=R * 0.24 * (1 + 0.2 * pop), color=GOLD if done else WHITE,
                            max_w=R * 1.75)
            c.text_centered("collisions", cy + R * 0.38, size=R * 0.14, color=SOFT, bold=False)
            if t < T_B0:
                c.text_centered("1/6 OF THE EARTH", h * 0.215, size=w * 0.07, color=GOLD)
            if done and t < T_LAD:
                a = clamp((t - T_B1) / 0.3)
                c.text_centered("π = 3.141592653589…", h * 0.72, size=w * 0.075, color=GOLD, alpha=a, max_w=w * 0.92)
                c.text_centered("13 digits of π", h * 0.765, size=w * 0.05, color=WHITE, alpha=a)
            if t >= T_LAD:                                        # the ladder: every ×100 adds a digit
                for i, (a_, b_) in enumerate(LADDER):
                    al = clamp((t - T_LAD - 0.35 * i) / 0.3)
                    y = h * (0.705 + 0.027 * i)
                    c.text_centered(a_, y, size=w * 0.036, color=SOFT, alpha=al, cx=w * 0.28, bold=False)
                    c.text_centered(b_, y, size=w * 0.036, color=GOLD if i == len(LADDER) - 1 else WHITE, alpha=al,
                                    cx=w * 0.68)
                c.text_centered("every ×100 heavier adds one digit", h * 0.85 - h * 0.0, size=w * 0.04, color=GOLD,
                                alpha=clamp((t - T_LAD - 2.4) / 0.3)) if False else None
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
    b = sfx.Bed(T_LOOP, seed=9)
    arp = [(69, 72, 76, 81), (65, 69, 72, 77), (64, 67, 72, 76), (67, 71, 74, 79)]
    pat = [0, 2, 1, 3, 2, 1, 3, 2]
    t, q = 0.0, 0
    while t < T_LOOP - 0.1:
        ch = arp[int(t // 4.0) % 4]
        pi_long.marimba(b, t, ch[pat[q % 8]], 0.022 if q % 4 else 0.03)
        t += 0.5
        q += 1
    b.chime(0.05, (84, 88), 0.05)
    b.whoosh(T_SHRINK0, 1.0, 0.05, up=False)
    pi_long.strum_burst(b, T_B0, T_B1 - T_B0, 56)
    for i in range(len(LADDER)):
        pi_long.marimba(b, T_LAD + 0.35 * i, [72, 74, 76, 79, 81, 84][i], 0.12)
    b.whoosh(T_BACK0, 1.2, 0.05)
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
    print(f"[{SCENE}] N = {N:,}")
    name = f"{SCENE}_{label}_{layout.tag}"
    video = studio.OUT_DIR / f"{name}_silent.mp4"
    d = render(layout, video, rule)
    kit.deliver_loop(SCENE, name, layout, video, [], d, voice="piano", bed=sound(), peak_db=-6.0)


if __name__ == "__main__":
    main()
