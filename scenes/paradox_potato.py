"""PARADOX: THE POTATO v2 — 100 kg of potatoes at 99% water dry to 98% water… and weigh 50 kg.

Recipe remake (no dialogue): a kitchen scale with a dial and a needle, a pile of real-looking potatoes, the sun and
steam. 0-3 s: they dry, the needle crashes 100 -> 50 kg while the water reading barely moves (99.0% -> 98.0%);
"50 kg?!" lands with a hit. Reveal: 1-kg cubes. Before: 100 cubes, 1 dry (brown) = 1%. After: 50 cubes, the same
1 dry cube = 2%. Then the water comes back (loop).
Audio (original, lib/sfx): a sizzle while drying, a falling tone with the needle, a hit on 50 kg, plucks as the
cubes appear, a chime on the answer, a rising rewind.
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

SCENE = "paradox_potato"
T_LOOP = 15.0
GOLD, WHITE, RED, BLUE, BROWN = (1.0, 0.82, 0.35), (0.96, 0.97, 1.0), (1.0, 0.38, 0.38), (0.32, 0.62, 1.0), (0.62, 0.40, 0.22)
D0, D1 = 0.3, 3.0                 # drying
T_REV0, T_REV1, T_REV2 = 5.0, 5.6, 8.3   # the cubes: before, after, the answer
T_BACK0, T_BACK1 = 11.2, 13.4


def seg(t, a, b):
    return min(1.0, max(0.0, (t - a) / (b - a)))


def kg_at(t):
    if t < T_BACK0:
        return 100 - 50 * smooth(seg(t, D0, D1))
    return 50 + 50 * smooth(seg(t, T_BACK0, T_BACK1))


_rng = np.random.default_rng(4)
POTS = [(float(_rng.uniform(-0.8, 0.8)), float(_rng.uniform(0, 1)) ** 0.7, float(_rng.uniform(0.75, 1.15)),
         float(_rng.uniform(-0.6, 0.6))) for _ in range(16)]
POTS.sort(key=lambda p: -p[1])


class Scene:
    def __init__(self, layout):
        self.L = layout
        self.canvas = Canvas(layout.w, layout.h, studio.render_scale())

    def potato(self, x, y, s, rot, shrink):
        c = self.canvas
        ctx = c.ctx
        ctx.save()
        ctx.translate(x, y)
        ctx.rotate(rot)
        ctx.scale(1.0, 0.7)
        g = cairo.RadialGradient(-s * 0.3, -s * 0.35, s * 0.1, 0, 0, s)
        dark = 0.25 * shrink
        g.add_color_stop_rgb(0, 0.86 - dark, 0.68 - dark, 0.44 - dark * 0.6)
        g.add_color_stop_rgb(1, 0.52 - dark, 0.36 - dark, 0.20 - dark * 0.5)
        ctx.new_path()
        for k in range(24):                                       # a slightly lumpy outline (wrinkles as it dries)
            a = k / 24 * 2 * math.pi
            rr = s * (1 + 0.05 * math.sin(3 * a + rot * 5) + 0.06 * shrink * math.sin(9 * a))
            (ctx.move_to if k == 0 else ctx.line_to)(rr * math.cos(a), rr * math.sin(a))
        ctx.close_path()
        ctx.set_source(g)
        ctx.fill()
        for k in range(4):                                        # eyes
            a = k * 1.7 + rot
            c.circle(math.cos(a) * s * 0.5, math.sin(a) * s * 0.4, s * 0.06, (0.35, 0.22, 0.12), alpha=0.8)
        ctx.restore()

    def scale(self, t, cx, cy, kg):
        c, w, h = self.canvas, self.L.w, self.L.h
        ctx = c.ctx
        bw, bh = w * 0.62, h * 0.20
        x0, y0 = cx - bw / 2, cy
        g = cairo.LinearGradient(0, y0, 0, y0 + bh)
        g.add_color_stop_rgb(0, 0.85, 0.87, 0.92)
        g.add_color_stop_rgb(1, 0.45, 0.48, 0.55)
        ctx.new_path()
        r = w * 0.04
        ctx.arc(x0 + bw - r, y0 + r, r, -math.pi / 2, 0)
        ctx.arc(x0 + bw - r, y0 + bh - r, r, 0, math.pi / 2)
        ctx.arc(x0 + r, y0 + bh - r, r, math.pi / 2, math.pi)
        ctx.arc(x0 + r, y0 + r, r, math.pi, 1.5 * math.pi)
        ctx.close_path()
        ctx.set_source(g)
        ctx.fill()
        dx, dy, dr = cx, y0 + bh * 0.52, bh * 0.40                 # the dial
        c.circle(dx, dy, dr * 1.06, (0.25, 0.27, 0.32))
        c.circle(dx, dy, dr, (0.97, 0.97, 0.95))
        for v in range(0, 101, 10):
            a = math.pi * (0.8 + 1.4 * v / 100)
            c.lines([(dx + math.cos(a) * dr * 0.82, dy + math.sin(a) * dr * 0.82, dx + math.cos(a) * dr * 0.95,
                      dy + math.sin(a) * dr * 0.95)], (0.2, 0.2, 0.25), width=3)
            if v % 50 == 0:
                c.text_centered(str(v), dy + math.sin(a) * dr * 0.62 + dr * 0.07, size=dr * 0.2, color=(0.2, 0.2, 0.25),
                                cx=dx + math.cos(a) * dr * 0.62)
        a = math.pi * (0.8 + 1.4 * kg / 100)
        c.lines([(dx, dy, dx + math.cos(a) * dr * 0.85, dy + math.sin(a) * dr * 0.85)], RED, width=6)
        c.circle(dx, dy, dr * 0.08, (0.2, 0.2, 0.25))
        ctx.save()                                               # the plate
        ctx.translate(cx, y0 - h * 0.006)
        ctx.scale(1, 0.16)
        ctx.arc(0, 0, bw * 0.55, 0, 2 * math.pi)
        ctx.restore()
        gp = cairo.LinearGradient(cx - bw * 0.55, 0, cx + bw * 0.55, 0)
        gp.add_color_stop_rgb(0, 0.55, 0.58, 0.65)
        gp.add_color_stop_rgb(0.5, 0.95, 0.96, 1.0)
        gp.add_color_stop_rgb(1, 0.55, 0.58, 0.65)
        ctx.set_source(gp)
        ctx.fill()

    def cubes(self, cx, cy, n, cs, cols, alpha, pop_t, t):
        """n one-kilo cubes, 10 per row, the last one dry (brown)."""
        c = self.canvas
        ctx = c.ctx
        rows = (n + 9) // 10
        for i in range(n):
            r, q = divmod(i, 10)
            x = cx + (q - 5) * cs
            y = cy - (rows / 2 - r) * cs
            dry = i == n - 1
            k = 1.0 if pop_t is None else min(1.0, max(0.0, (t - pop_t - i * 0.012) / 0.15))
            if k <= 0:
                continue
            col = BROWN if dry else BLUE
            ctx.rectangle(x + 2, y + 2, cs - 4, cs - 4)
            ctx.set_source_rgba(*col, alpha * k)
            ctx.fill()
            ctx.rectangle(x + 2, y + 2, cs - 4, (cs - 4) * 0.22)
            ctx.set_source_rgba(1, 1, 1, 0.22 * alpha * k)
            ctx.fill()
            if dry:
                c.glow(x + cs / 2, y + cs / 2, cs * 1.1, GOLD, strength=0.45 * alpha * k, reach=2.0)

    def draw(self, f, rule):
        L, c = self.L, self.canvas
        w, h = L.w, L.h
        t = f * DT
        ctx = c.ctx
        g = cairo.LinearGradient(0, 0, 0, h)
        g.add_color_stop_rgb(0, 0.10, 0.08, 0.16)
        g.add_color_stop_rgb(1, 0.02, 0.02, 0.04)
        ctx.set_source(g)
        ctx.paint()
        kg = kg_at(t)
        dry = (100 - kg) / 50                                    # 0 fresh .. 1 dried
        water = (kg - 1) / kg * 100
        rev = smooth(seg(t, T_REV0, T_REV0 + 0.5)) * (1 - smooth(seg(t, T_BACK0 - 0.6, T_BACK0)))
        # the sun (drying) and the steam
        sun = 0.3 + 0.7 * math.sin(math.pi * seg(t, 0.0, 3.4)) ** 2      # 0.3 at frame 0 and at the end
        c.glow(w * 0.84, h * 0.16, w * 0.12, (1.0, 0.75, 0.3), strength=0.6 * sun * (1 - rev), reach=2.6)
        c.circle(w * 0.84, h * 0.16, w * 0.055, (1.0, 0.85, 0.4), alpha=1 - rev)
        cam = 1 + 0.08 * dry * (1 - rev)                                    # push in as they dry
        ctx.save()
        ctx.translate(w / 2, h * 0.5)
        ctx.scale(cam, cam)
        ctx.translate(-w / 2, -h * 0.5)
        sa = 1 - rev
        if sa > 0.01:
            ctx.push_group()
            self.scale(t, w / 2, h * 0.53, kg)
            ps = 1 - 0.21 * dry                                   # (½)^(1/3): half the volume
            base_y = h * 0.52
            for px, py, sz, rot in POTS:
                self.potato(w / 2 + px * w * 0.26 * (0.75 + 0.25 * ps), base_y - py * h * 0.13 * ps,
                            w * 0.07 * sz * ps, rot, dry)
            if D0 <= t < D1 + 0.4 or T_BACK0 <= t < T_BACK1:
                for k in range(26):                                # steam / returning water
                    ph = (t * 0.8 + k / 26) % 1.0
                    up = t < D1 + 0.4
                    yy = base_y - h * 0.05 - (ph if up else 1 - ph) * h * 0.25
                    xx = w / 2 + w * 0.25 * math.sin(k * 2.3) + 10 * math.sin(t * 3 + k)
                    col = (0.9, 0.92, 1.0) if up else BLUE
                    c.circle(xx, yy, w * 0.012 * (1 + ph), col, alpha=0.45 * (1 - ph if up else ph))
            ctx.pop_group_to_source()
            ctx.paint_with_alpha(sa)
        ctx.restore()
        # the cubes: before and after
        if rev > 0.01:
            cs = w * 0.068
            self.cubes(w / 2, h * 0.37, 100, cs * 0.62, None, rev, T_REV0, t)
            c.text_centered("BEFORE: 100 kg, 1 kg dry = 1%", h * 0.215, size=w * 0.045, color=WHITE, alpha=rev)
            a2 = rev * smooth(seg(t, T_REV1, T_REV1 + 0.4))
            if a2 > 0.01:
                self.cubes(w / 2, h * 0.62, 50, cs * 0.62, None, a2, T_REV1, t)
                c.text_centered("AFTER: 50 kg, the same 1 kg = 2%", h * 0.53, size=w * 0.045, color=GOLD, alpha=a2)
        # the numbers: one big line at a time
        if rev < 0.5:
            pop = 1 + 0.35 * math.exp(-(t - D1) / 0.12) if D1 <= t < T_REV0 else 1.0
            big = f"{kg:.0f} kg" + ("?!" if D1 <= t < T_REV0 else "")
            c.text_centered(big, h * 0.235, size=w * 0.14 * pop, color=RED if D1 <= t < T_REV0 else WHITE)
            c.text_centered(f"water: {water:.1f}%", h * 0.29, size=w * 0.05, color=BLUE)
            line = "100 kg of potatoes, 99% water" if t < D0 + 0.4 or t >= T_BACK1 else (
                "dry them to 98% water…" if t < D1 else "1% less water = HALF the weight")
            c.text_centered(line, h * 0.80, size=w * 0.05, color=WHITE, max_w=w * 0.94)
        elif t >= T_REV2:
            c.text_centered("The dry part never changes.", h * 0.80, size=w * 0.05, color=WHITE,
                            alpha=smooth(seg(t, T_REV2, T_REV2 + 0.3)) * rev)
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
    b = sfx.Bed(T_LOOP, seed=17)
    beat = 60 / 100
    b.pad([(0.0, (45, 52, 57, 64)), (D1, (41, 48, 57, 60)), (T_REV0, (43, 50, 55, 62)), (T_BACK0, (45, 52, 57, 64))],
          beat, g=0.05)
    tv = np.arange(int((D1 - D0) * sfx.SR)) / sfx.SR             # sizzle
    nz = b.noise(D1 - D0)
    nz = nz - np.convolve(nz, np.ones(5) / 5, mode="same")
    b.add(D0, nz * (0.5 + 0.5 * np.sin(np.pi * tv / (D1 - D0))) * (1 + 0.5 * np.sin(2 * np.pi * 23 * tv)), 0.05)
    b.drop(D0 + 0.3, D1 - D0 - 0.3, 0.08, 900, 160)
    b.hit(D1, 0.55)
    b.chime(D1 + 0.02, (76, 79, 84), 0.07)
    for k in range(10):
        b.pluck(T_REV0 + 0.12 * k, 72 + (k % 5) * 2, 0.04)
        b.pluck(T_REV1 + 0.06 * k, 79 + (k % 4) * 2, 0.04)
    b.chime(T_REV1 + 0.6, (84, 88, 91), 0.07)
    b.chime(T_REV2, (72, 76, 79, 84), 0.06)
    b.riser(T_BACK0, T_BACK1 - T_BACK0, 0.06, 300, 1200)
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
