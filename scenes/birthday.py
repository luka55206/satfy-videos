"""BIRTHDAY — the birthday paradox: people walk into a room one by one; a line joins every PAIR. With 23 people there
are 253 pairs and the chance that two of them share a birthday is 50.7 %. With 70 people: 99.9 %.

Paradox recipe: something moving in the first second (people already arriving), one number that explodes (the pairs:
n(n−1)/2), one line of text at a time, a hit on the reveal. The web of lines is the visual: 23 people = 253 lines,
70 people = 2,415 lines (a mandala).
P(n) = 1 − (365 × 364 × … × (365 − n + 1)) / 365ⁿ (365 equally likely days, no leap day): P(23) = 50.73 %, P(70) = 99.92 %.
Loop: everyone leaves in reverse, back to one person (frame 0).
Audio (original, lib/sfx): light marimba bed, a rising pluck per person, soft ticks in the fast part, a hit + chime at
50.7 %, a chord at 99.9 %, a falling sweep on the rewind.
"""
import math
import sys
from pathlib import Path

import cairo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib import kit, sfx, studio  # noqa: E402
from lib.kit import DT, FPS, arg, smooth  # noqa: E402
from lib.layouts import get_layout  # noqa: E402
from lib.studio import Canvas, VideoWriter, hsv  # noqa: E402
from scenes.pi_long import marimba  # noqa: E402

SCENE = "birthday"
GOLD, WHITE, SOFT, CYAN, LIME = (1.0, 0.8, 0.3), (0.96, 0.97, 1.0), (0.75, 0.78, 0.92), (0.35, 0.85, 1.0), (0.55, 1.0, 0.55)
ENTER = {}
for _k in range(2, 24):
    _u = (_k - 2) / 21
    ENTER[_k] = 0.3 + 5.9 * (1 - (1 - _u) ** 1.7)
T_HOLD = ENTER[23] + 0.35                 # "50.7 %"
for _k in range(24, 71):
    ENTER[_k] = 9.0 + 2.4 * (_k - 24) / 46
T_FULL = ENTER[70] + 0.35
T_RW0, T_RW1 = 13.9, 15.1
T_LOOP = 15.4
N_MAX = 70


def clamp(v, a=0.0, b=1.0):
    return max(a, min(b, v))


def prob(n):
    p = 1.0
    for k in range(n):
        p *= (365 - k) / 365
    return 1 - p


def count(t):
    """(people in the room, continuous count for the spacing, time since the last arrival)."""
    if t >= T_RW0:
        u = smooth(clamp((t - T_RW0) / (T_RW1 - T_RW0)))
        x = N_MAX - (N_MAX - 1) * u
        return max(1, int(math.ceil(x - 1e-6))), x, 9.0
    n, last = 1, -9.0
    for k in range(2, N_MAX + 1):
        if t >= ENTER[k]:
            n, last = k, ENTER[k]
    since = t - last
    return n, n - 1 + smooth(clamp(since / 0.25)) if n > 1 else 1.0, since


class Scene:
    def __init__(self, layout):
        self.L = layout
        self.canvas = Canvas(layout.w, layout.h, studio.render_scale())

    def person(self, x, y, s, col, a=1.0, pop=0.0):
        c = self.canvas
        s = s * (1 + 0.5 * pop)
        if pop > 0.05:
            c.glow(x, y, s * 1.6, col, strength=0.5 * pop, reach=1.6)
        c.circle(x, y - s * 0.35, s * 0.38, col, alpha=a)
        ctx = c.ctx
        ctx.new_path()
        ctx.arc(x, y + s * 0.55, s * 0.6, math.pi, 2 * math.pi)
        ctx.close_path()
        ctx.set_source_rgba(*col, a)
        ctx.fill()

    def draw(self, f, rule):
        L, c = self.L, self.canvas
        w, h = L.w, L.h
        t = f * DT
        ctx = c.ctx
        g = cairo.RadialGradient(w / 2, h * 0.48, 0, w / 2, h * 0.48, h * 0.7)
        g.add_color_stop_rgb(0, 0.07, 0.06, 0.13)
        g.add_color_stop_rgb(1, 0.005, 0.005, 0.015)
        ctx.set_source(g)
        ctx.paint()
        n, ne, since = count(t)
        cx, cy, R = w * 0.5, h * 0.535, w * 0.32
        pos = []
        for i in range(n):
            a = -math.pi / 2 + 2 * math.pi * i / max(1.0, ne)
            if i == n - 1 and n > 1 and since < 0.25:          # the newcomer walks in from outside
                k = smooth(clamp(since / 0.25))
                rr = R * (1.35 - 0.35 * k)
            else:
                rr = R
            pos.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
        # the pairs: every two people, one line
        base_a = 0.42 if n <= 23 else 0.42 - 0.26 * (n - 23) / 47
        lw = 1.8 if n <= 23 else 1.8 - 0.9 * (n - 23) / 47
        segs = [(pos[i][0], pos[i][1], pos[j][0], pos[j][1]) for j in range(n) for i in range(j)
                if not (j == n - 1 and since < 0.5)]
        if segs:
            c.lines(segs, (0.5, 0.7, 1.0), width=lw, alpha=base_a)
        if n > 1 and since < 0.5:                                # the newcomer's lines flash
            fl = 1 - since / 0.5
            j = n - 1
            c.lines([(pos[i][0], pos[i][1], pos[j][0], pos[j][1]) for i in range(j)], GOLD, width=2.2,
                    alpha=0.25 + 0.6 * fl)
        s = w * (0.034 if n <= 23 else 0.034 - 0.014 * (n - 23) / 47)
        for i, (x, y) in enumerate(pos):
            pop = math.exp(-since / 0.15) if (i == n - 1 and n > 1) else 0.0
            self.person(x, y, s, hsv((i * 0.137) % 1.0, 0.55, 1.0), pop=pop)
        # HUD: the chance, big
        p = prob(n)
        hot = (T_HOLD <= t < ENTER[24]) or (T_FULL <= t < T_RW0)
        pk = math.exp(-(t - (T_HOLD if t < ENTER[24] else T_FULL)) / 0.2) if hot else 0.0
        col = GOLD if hot else WHITE
        txt = f"{p * 100:.1f} %" if p < 0.999 or n < N_MAX else "99.9 %"
        c.text_centered(txt, h * 0.275, size=w * 0.14 * (1 + 0.15 * pk), color=col)
        c.text_centered("chance two share a birthday", h * 0.31, size=w * 0.045, color=SOFT, bold=False)
        # bottom: people and pairs
        pairs = n * (n - 1) // 2
        c.text_centered(f"{n} {'person' if n == 1 else 'people'}", h * 0.765, size=w * 0.07, color=WHITE)
        c.text_centered(f"{pairs:,} pairs", h * 0.80, size=w * 0.055, color=GOLD if n >= 23 else (0.55, 0.65, 1.0))
        if T_HOLD + 0.5 <= t < ENTER[24]:
            a = clamp((t - T_HOLD - 0.5) / 0.3)
            c.text_centered("23 people, but 253 chances to match", h * 0.835, size=w * 0.042, color=LIME, alpha=a,
                            max_w=w * 0.94)
        if T_FULL + 0.4 <= t < T_RW0:
            a = clamp((t - T_FULL - 0.4) / 0.3)
            c.text_centered("almost certain", h * 0.835, size=w * 0.05, color=LIME, alpha=a)
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
    b = sfx.Bed(T_LOOP, seed=23)
    arp = [(69, 72, 76, 81), (65, 69, 72, 77), (64, 67, 72, 76), (67, 71, 74, 79)]
    pat = [0, 2, 1, 3, 2, 1, 3, 2]
    t, q = 0.0, 0
    while t < T_LOOP - 0.2:
        marimba(b, t, arp[int(t // 3.2) % 4][pat[q % 8]], 0.018 if q % 4 else 0.024)
        t += 0.4
        q += 1
    scale = [60, 62, 64, 67, 69, 72, 74, 76, 79, 81]
    for k in range(2, 24):
        i = k - 2
        b.pluck(ENTER[k], scale[i % 10] + 12 * (i // 10), 0.08, d=0.4)
    b.hit(T_HOLD, 0.22, low=85)
    b.chime(T_HOLD + 0.02, (72, 76, 79, 84), 0.07, decay=1.0)
    for k in range(24, N_MAX + 1):
        b.tick(ENTER[k], 2400 + 25 * (k - 24), 0.035)
    b.hit(T_FULL, 0.25, low=75)
    b.chime(T_FULL + 0.02, (69, 72, 76, 81, 84, 88), 0.07, decay=1.2)
    b.drop(T_RW0, T_RW1 - T_RW0, 0.05, 1400, 220)
    return b.get()


def main():
    label, rule = arg("--label", "v1"), arg("--rule", "")
    studio.OUT_DIR.mkdir(exist_ok=True)
    layout = get_layout(kit.orients()[0])
    print(f"[{SCENE}] {T_LOOP:.2f}s  P(23) = {prob(23) * 100:.2f} %  P(70) = {prob(70) * 100:.2f} %")
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
