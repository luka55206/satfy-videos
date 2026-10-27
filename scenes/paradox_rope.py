"""PARADOX: THE ROPE AROUND THE EARTH — add 1 m to a rope around the Earth and it lifts 16 cm, all the way round.

2π(r + h) = 2πr + 1 m  ->  h = 1/(2π) m ≈ 15.9 cm, for ANY size: the same 1 m around a basketball also lifts 16 cm.
Shots: a neon dot-matrix Earth with a gold rope on the equator (+1 m, "16 cm" lands at 1.2 s) -> a dive to the
ground: the rope floats 16 cm up and a cat crawls under it -> a basketball: tight rope, +1 m, the same 16 cm ->
the formula over both -> back to the Earth (loop). Recipe: shock first, moving camera, real objects, one line of
text at a time, hits on the numbers.
Audio (original, lib/sfx): a pluck pulse, a chime on "+1 m", hits on "16 cm", whooshes on every camera move.
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

SCENE = "paradox_rope"
T_LOOP = 16.0
GOLD, WHITE, CYAN = (1.0, 0.82, 0.35), (0.96, 0.97, 1.0), (0.35, 0.9, 1.0)
T_ADD, T_16 = 0.5, 1.2
T_DIVE0, T_DIVE1 = 2.2, 3.2
T_GROUND1, T_BALL0, T_BALL_ADD, T_BALL16 = 6.4, 7.2, 7.8, 8.6
T_FORM0, T_BACK0, T_BACK1 = 10.4, 13.4, 14.4


def seg(t, a, b):
    return min(1.0, max(0.0, (t - a) / (b - a)))


def _land():
    """a lat/lon dot grid of 'continents' (seeded blobs)."""
    rng = np.random.default_rng(12)
    blobs = [(rng.uniform(0, 2 * math.pi), rng.uniform(-0.9, 0.9), rng.uniform(0.25, 0.6)) for _ in range(9)]
    pts = []
    for lat in np.arange(-1.35, 1.36, 0.06):
        n = max(8, int(110 * math.cos(lat)))
        for lon in np.linspace(0, 2 * math.pi, n, endpoint=False):
            v = np.array([math.cos(lat) * math.cos(lon), math.sin(lat), math.cos(lat) * math.sin(lon)])
            for bl, bt, br in blobs:
                c = np.array([math.cos(bt) * math.cos(bl), math.sin(bt), math.cos(bt) * math.sin(bl)])
                wob = 1 + 0.25 * math.sin(5 * lon + 3 * lat + bl)
                if math.acos(max(-1.0, min(1.0, float(v @ c)))) < br * wob:
                    pts.append((lat, lon))
                    break
    return pts


LAND = _land()


class Scene:
    def __init__(self, layout):
        self.L = layout
        self.canvas = Canvas(layout.w, layout.h, studio.render_scale())

    def bg(self, ctx, top=(0.03, 0.04, 0.10), bot=(0.0, 0.0, 0.02)):
        w, h = self.L.w, self.L.h
        g = cairo.LinearGradient(0, 0, 0, h)
        g.add_color_stop_rgb(0, *top)
        g.add_color_stop_rgb(1, *bot)
        ctx.set_source(g)
        ctx.paint()
        rng = np.random.default_rng(5)
        for k in range(120):
            x, y, s = rng.random() * w, rng.random() * h, rng.random()
            self.canvas.circle(x, y, 0.8 + 1.4 * s, (1, 1, 1), alpha=0.15 + 0.35 * s)

    def earth(self, t, cx, cy, R, lift, alpha=1.0):
        """dot-matrix Earth; the rope rides at R·(1 + lift) (lift is exaggerated only by the glow, see text)."""
        c = self.canvas
        ctx = c.ctx
        rot = 2 * math.pi * t / T_LOOP
        tilt = 0.38
        ct, st = math.cos(tilt), math.sin(tilt)

        def P(x, y, z):
            y2, z2 = y * ct - z * st, y * st + z * ct
            return cx + x * R, cy - y2 * R, z2

        rope = []
        for a in np.linspace(0, 2 * math.pi, 181):
            rr = 1 + lift
            rope.append(P(rr * math.cos(a + rot), 0.0, rr * math.sin(a + rot)))
        back = [(x, y) for x, y, z in rope if z < 0]
        c.glow(cx, cy, R * 1.08, (0.25, 0.55, 1.0), strength=0.45 * alpha, reach=1.5)
        for (x0, y0, z0), (x1, y1, z1) in zip(rope, rope[1:]):         # rope, back half
            if z0 < 0 and z1 < 0:
                c.lines([(x0, y0, x1, y1)], GOLD, width=3, alpha=0.35 * alpha)
        g = cairo.RadialGradient(cx - R * 0.35, cy - R * 0.35, R * 0.1, cx, cy, R)
        g.add_color_stop_rgba(0, 0.10, 0.25, 0.55, alpha)
        g.add_color_stop_rgba(1, 0.02, 0.05, 0.16, alpha)
        ctx.new_path()
        ctx.arc(cx, cy, R, 0, 2 * math.pi)
        ctx.set_source(g)
        ctx.fill()
        for lat, lon in LAND:
            x, y, z = P(math.cos(lat) * math.cos(lon + rot), math.sin(lat), math.cos(lat) * math.sin(lon + rot))
            if z > 0:
                c.circle(x, y, R * 0.010 * (0.5 + 0.5 * z), (0.35, 1.0, 0.6), alpha=alpha * (0.3 + 0.7 * z))
        c.ring(cx, cy, R, (0.4, 0.75, 1.0), width=2, alpha=0.6 * alpha)
        for (x0, y0, z0), (x1, y1, z1) in zip(rope, rope[1:]):         # rope, front half
            if z0 >= 0 and z1 >= 0:
                c.lines([(x0, y0, x1, y1)], GOLD, width=10, alpha=0.18 * alpha)
                c.lines([(x0, y0, x1, y1)], GOLD, width=4, alpha=alpha)

    def ball(self, cx, cy, R, rope_r, alpha):
        c = self.canvas
        ctx = c.ctx
        g = cairo.RadialGradient(cx - R * 0.35, cy - R * 0.35, R * 0.1, cx, cy, R)
        g.add_color_stop_rgba(0, 1.0, 0.62, 0.28, alpha)
        g.add_color_stop_rgba(1, 0.70, 0.30, 0.08, alpha)
        ctx.new_path()
        ctx.arc(cx, cy, R, 0, 2 * math.pi)
        ctx.set_source(g)
        ctx.fill()
        ctx.save()
        ctx.new_path()
        ctx.arc(cx, cy, R, 0, 2 * math.pi)
        ctx.clip()
        for path in ([(cx - R, cy), (cx + R, cy)], [(cx, cy - R), (cx, cy + R)]):
            c.lines([(*path[0], *path[1])], (0.15, 0.06, 0.02), width=R * 0.05, alpha=alpha)
        for sgn in (-1, 1):
            ctx.new_path()
            ctx.arc(cx + sgn * R * 1.25, cy, R * 0.95, 0, 2 * math.pi)
            ctx.set_source_rgba(0.15, 0.06, 0.02, alpha)
            ctx.set_line_width(R * 0.05)
            ctx.stroke()
        ctx.restore()
        c.ring(cx, cy, rope_r, GOLD, width=12, alpha=0.18 * alpha)
        c.ring(cx, cy, rope_r, GOLD, width=5, alpha=alpha)

    def ground(self, t):
        """close-up at the equator: the rope 16 cm above the ground, a ruler, a cat crawling under."""
        c, w, h = self.canvas, self.L.w, self.L.h
        ctx = c.ctx
        self.bg(ctx, (0.04, 0.06, 0.16), (0.02, 0.03, 0.08))
        gy = h * 0.62
        ppc = h * 0.0075                                         # pixels per cm
        ctx.new_path()                                           # the ground: a whisper of curvature
        ctx.move_to(0, gy + h * 0.01)
        ctx.curve_to(w * 0.3, gy - h * 0.004, w * 0.7, gy - h * 0.004, w, gy + h * 0.01)
        ctx.line_to(w, h)
        ctx.line_to(0, h)
        ctx.close_path()
        g = cairo.LinearGradient(0, gy, 0, h)
        g.add_color_stop_rgb(0, 0.10, 0.28, 0.14)
        g.add_color_stop_rgb(1, 0.03, 0.08, 0.04)
        ctx.set_source(g)
        ctx.fill()
        rng = np.random.default_rng(9)
        for k in range(160):                                     # grass
            x = rng.random() * w
            hh = ppc * (2 + 3 * rng.random())
            sway = math.sin(t * 2 + k) * 2
            c.lines([(x, gy + 2, x + sway, gy - hh)], (0.35, 0.75, 0.35), width=2, alpha=0.6)
        ry = gy - 16 * ppc                                       # the rope at 16 cm
        c.lines([(0, ry, w, ry)], GOLD, width=26, alpha=0.18)
        c.lines([(0, ry, w, ry)], GOLD, width=9, alpha=1.0)
        rx = w * 0.12                                            # the ruler
        ctx.rectangle(rx - w * 0.03, ry - ppc * 2, w * 0.06, 18 * ppc)
        ctx.set_source_rgb(0.95, 0.85, 0.40)
        ctx.fill()
        for cm in range(0, 19):
            y = gy - cm * ppc
            ln = w * (0.03 if cm % 5 == 0 else 0.015)
            c.lines([(rx - w * 0.03, y, rx - w * 0.03 + ln, y)], (0.15, 0.1, 0.05), width=2)
        c.text_centered("16 cm", ry - h * 0.03, size=w * 0.06, color=GOLD, cx=rx + w * 0.02)
        # the cat crawls under, right to left
        u = seg(t, T_DIVE1 + 0.2, T_GROUND1 - 0.2)
        cxp = w * (1.15 - 1.3 * u)
        s = ppc * 8.5
        col = (0.95, 0.62, 0.28)
        ctx.save()
        ctx.translate(cxp, gy - s * 0.55)
        ctx.scale(1, 0.42)
        ctx.arc(0, 0, s * 1.05, 0, 2 * math.pi)
        ctx.restore()
        ctx.set_source_rgb(*col)
        ctx.fill()
        hx, hy = cxp - s * 1.0, gy - s * 0.62
        c.circle(hx, hy, s * 0.4, col)
        for dx in (-0.22, 0.18):
            c.poly([(hx + dx * s, hy - s * 0.22), (hx + (dx - 0.08) * s, hy - s * 0.62), (hx + (dx + 0.12) * s, hy - s * 0.28)],
                   col)
        c.circle(hx - s * 0.14, hy - s * 0.05, s * 0.06, (0.1, 0.1, 0.1))
        step = math.sin(t * 12)
        for lx in (-0.6, -0.25, 0.3, 0.65):
            c.lines([(cxp + lx * s, gy - s * 0.35, cxp + lx * s + step * s * 0.12 * (1 if lx > 0 else -1), gy)], col,
                    width=s * 0.16)
        c.lines([(cxp + s * 1.0, gy - s * 0.6, cxp + s * 1.6, gy - s * 1.0 + s * 0.15 * math.sin(t * 5))], col,
                width=s * 0.15)

    def draw(self, f, rule):
        L, c = self.L, self.canvas
        w, h = L.w, L.h
        t = f * DT
        ctx = c.ctx
        cx, cy, R = w * 0.5, h * 0.45, w * 0.36
        big, line, big_col, pop_t = None, None, WHITE, None
        if t < T_DIVE1 or t >= T_BACK0:
            self.bg(ctx)
            z, a = 1.0, 1.0
            if T_DIVE0 <= t < T_DIVE1:                           # dive in
                u = smooth(seg(t, T_DIVE0, T_DIVE1))
                z, a = 1 + 25 * u ** 2, 1 - u
            if t >= T_BACK0:                                     # come back out
                u = smooth(seg(t, T_BACK0, T_BACK1))
                z, a = 1 + 6 * (1 - u) ** 2, u
            lift = 0.015 * smooth(seg(t, T_ADD, T_16)) if t < T_BACK0 else 0.015 * (1 - smooth(seg(t, T_BACK1, T_LOOP - 0.3)))
            self.earth(t, cx, cy + R * (z - 1) * 0.9, R * z, lift, a)
            if t < T_DIVE1:
                if t < T_ADD:
                    big, line = "40,075 km", "A rope around the Earth"
                elif t < T_16:
                    big, line, big_col, pop_t = "+ 1 m", "add just 1 metre…", GOLD, T_ADD
                else:
                    big, line, big_col, pop_t = "16 cm", "it lifts 16 cm ALL the way round", GOLD, T_16
            else:
                big, line = "40,075 km", "A rope around the Earth"
        elif t < T_GROUND1 + 0.4:
            self.ground(t)
            a = smooth(seg(t, T_DIVE1, T_DIVE1 + 0.3)) * (1 - smooth(seg(t, T_GROUND1, T_GROUND1 + 0.4)))
            if a < 1:
                ctx.rectangle(0, 0, w, h)
                ctx.set_source_rgba(0.01, 0.01, 0.03, 1 - a)
                ctx.fill()
            big, line, big_col = "16 cm", "a cat can crawl under it", GOLD
        else:
            self.bg(ctx)
            a = smooth(seg(t, T_GROUND1 + 0.4, T_BALL0))
            Rb = w * 0.15
            gap = smooth(seg(t, T_BALL_ADD, T_BALL16))
            rope_r = Rb * (1 + (16 / 12) * gap)                   # basketball r = 12 cm, +16 cm
            if t < T_FORM0:
                self.ball(cx, cy, Rb, rope_r, a)
                if gap > 0.5:
                    c.lines([(cx + Rb, cy, cx + rope_r, cy)], WHITE, width=3, alpha=gap)
                    c.text_centered("16 cm", cy - h * 0.012, size=w * 0.05, color=WHITE, cx=cx + (Rb + rope_r) / 2,
                                    alpha=gap)
                big = "16 cm" if t >= T_BALL16 else "+ 1 m"
                big_col, pop_t = GOLD, (T_BALL16 if t >= T_BALL16 else T_BALL_ADD)
                line = "same 1 m around a basketball…" if t < T_BALL16 else "…ALSO 16 cm"
                if t < T_BALL_ADD:
                    big, big_col, pop_t = None, WHITE, None
            else:                                                # the formula over both
                fa = smooth(seg(t, T_FORM0, T_FORM0 + 0.4))
                self.earth(t, w * 0.28, h * 0.43, w * 0.18, 0.015, fa)
                self.ball(w * 0.76, h * 0.43, w * 0.065, w * 0.065 * (1 + 16 / 12), fa)
                c.text_centered("+16 cm", h * 0.56, size=w * 0.05, color=GOLD, cx=w * 0.28, alpha=fa)
                c.text_centered("+16 cm", h * 0.56, size=w * 0.05, color=GOLD, cx=w * 0.76, alpha=fa)
                big, big_col = "h = 1 m ÷ 2π ≈ 16 cm", GOLD
                line = "for ANY size: the extra length is all that counts"
                if t >= T_BACK0 - 0.6:
                    line = None
        if big:
            pop = 1 + 0.35 * math.exp(-max(0.0, t - pop_t) / 0.12) if pop_t is not None else 1.0
            c.text_centered(big, h * 0.235, size=w * (0.12 if len(big) < 10 else 0.07) * pop, color=big_col,
                            max_w=w * 0.94)
        if line:
            c.text_centered(line, h * 0.75, size=w * 0.052, color=WHITE, max_w=w * 0.94)
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
    b = sfx.Bed(T_LOOP, seed=7)
    beat = 60 / 100
    b.pad([(0.0, (45, 52, 57, 64)), (T_DIVE1, (41, 48, 57, 60)), (T_BALL0, (43, 50, 55, 62)),
           (T_FORM0, (45, 52, 57, 64))], beat, g=0.05)
    b.pulse(0.0, T_LOOP, beat, [69, 76, 72, 76], 0.025)
    b.chime(T_ADD, (84, 88), 0.08)
    b.hit(T_16, 0.5)
    b.chime(T_16 + 0.02, (79, 84, 88, 91), 0.07)
    b.whoosh(T_DIVE0, 1.0, 0.14)
    b.hit(T_DIVE1, 0.25, low=40)
    b.whoosh(T_GROUND1, 0.8, 0.10, up=False)
    b.chime(T_BALL_ADD, (84, 88), 0.07)
    b.hit(T_BALL16, 0.5)
    b.chime(T_BALL16 + 0.02, (79, 84, 88, 91), 0.07)
    b.riser(T_FORM0 - 0.6, 0.6, 0.05)
    b.chime(T_FORM0, (72, 76, 79, 84, 88), 0.06)
    b.whoosh(T_BACK0, 1.0, 0.10, up=False)
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
