"""PARADOX PI4 — "π = 4?!": the staircase paradox. A circle of diameter 1 inside a square (perimeter 4). Fold the
corners in, again and again: the perimeter stays exactly 4 and the shape hugs the circle… so π = 4?!
Then the camera zooms into the edge: it is STILL a staircase, at every zoom. The length never approaches the circle's
(the steps are never tangent to it), so the limit of the lengths is not the length of the limit: π = 3.14159…

Paradox recipe (docs/scenes/paradox.md): shock in 2 s (the corners already folding), one line of text at a time,
moving camera, a hit on the reveal; the loop unfolds back to the square (frame 0).
Geometry: level n has 2ⁿ points per quadrant on the circle; consecutive points are joined by the OUTSIDE corner
(the larger |x|, the larger |y|). Every level's perimeter is exactly 4 × diameter.
Audio (original, lib/sfx): light marimba bed, a rising pluck per fold, a whoosh on the zoom, a hit + chime on π.
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
from scenes.pi_long import marimba  # noqa: E402

SCENE = "paradox_pi4"
GOLD, WHITE, SOFT, CYAN, PINK = (1.0, 0.8, 0.3), (0.96, 0.97, 1.0), (0.75, 0.78, 0.92), (0.35, 0.85, 1.0), (1.0, 0.45, 0.6)
FOLDS = [(0.3, 0.6), (1.05, 0.55), (1.75, 0.5), (2.35, 0.45), (2.9, 0.4), (3.35, 0.38), (3.78, 0.35), (4.18, 0.35)]
T_FOLDED = 4.55
T_Q = 5.2                       # "so π = 4 ?!"
T_Z0, T_Z1 = 7.2, 8.5           # zoom in
T_ZO0, T_ZO1 = 11.4, 12.4       # zoom out
T_PI = 12.4
T_RW0, T_RW1 = 14.4, 15.6       # unfold back to the square
T_LOOP = 15.9
ZMAX = 40.0
LEVELS = len(FOLDS)


def clamp(v, a=0.0, b=1.0):
    return max(a, min(b, v))


def lev(t):
    if t >= T_RW0:
        return LEVELS * (1 - smooth(clamp((t - T_RW0) / (T_RW1 - T_RW0))))
    n = 0.0
    for k, (t0, d) in enumerate(FOLDS):
        if t >= t0:
            n = k + smooth(clamp((t - t0) / d))
    return n


def corner(a, b):
    return (a[0] if abs(a[0]) >= abs(b[0]) else b[0], a[1] if abs(a[1]) >= abs(b[1]) else b[1])


def staircase(L):
    """the closed path (unit radius, centre 0) at continuous level L."""
    n = int(math.floor(L + 1e-9))
    u = L - n
    M = 4 * 2 ** n
    pts = [(math.cos(2 * math.pi * i / M), math.sin(2 * math.pi * i / M)) for i in range(M)]
    if u > 1e-6 and n < LEVELS:
        new = []
        for i in range(M):
            p, q = pts[i], pts[(i + 1) % M]
            c0 = corner(p, q)
            a = 2 * math.pi * (i + 0.5) / M
            tg = (math.cos(a), math.sin(a))
            new += [p, (c0[0] + (tg[0] - c0[0]) * u, c0[1] + (tg[1] - c0[1]) * u)]
        pts = new
    path = []
    for i in range(len(pts)):
        p, q = pts[i], pts[(i + 1) % len(pts)]
        path += [p, corner(p, q)]
    return path


class Scene:
    def __init__(self, layout):
        self.L = layout
        self.canvas = Canvas(layout.w, layout.h, studio.render_scale())

    def draw(self, f, rule):
        L, c = self.L, self.canvas
        w, h = L.w, L.h
        t = f * DT
        ctx = c.ctx
        g = cairo.RadialGradient(w / 2, h * 0.50, 0, w / 2, h * 0.50, h * 0.7)
        g.add_color_stop_rgb(0, 0.07, 0.06, 0.13)
        g.add_color_stop_rgb(1, 0.005, 0.005, 0.015)
        ctx.set_source(g)
        ctx.paint()
        R = w * 0.34
        ox, oy = w * 0.5, h * 0.50
        # camera: zoom onto the 45° point of the edge (it moves to the screen centre)
        if t < T_Z0 or t >= T_ZO1:
            v = 0.0
        elif t < T_Z1:
            v = smooth((t - T_Z0) / (T_Z1 - T_Z0))
        elif t < T_ZO0:
            v = 1.0
        else:
            v = 1 - smooth((t - T_ZO0) / (T_ZO1 - T_ZO0))
        zoom = math.exp(math.log(ZMAX) * v)
        fx, fy = R * math.cos(math.pi / 4), -R * math.sin(math.pi / 4)

        def S(p):
            px, py = p[0] * R, -p[1] * R
            return ox + fx * (1 - v) + (px - fx) * zoom, oy + fy * (1 - v) + (py - fy) * zoom

        ccx, ccy = S((0.0, 0.0))
        ctx.new_path()
        ctx.arc(ccx, ccy, R * zoom, 0, 2 * math.pi)
        ctx.set_source_rgba(*CYAN, 0.12)
        ctx.fill_preserve()
        ctx.set_source_rgba(*CYAN, 0.95)
        ctx.set_line_width(4 if v < 0.5 else 5)
        ctx.stroke()
        L_ = lev(t)
        path = [S(p) for p in staircase(L_)]
        ctx.new_path()
        ctx.move_to(*path[0])
        for p in path[1:]:
            ctx.line_to(*p)
        ctx.close_path()
        ctx.set_source_rgb(*GOLD)
        ctx.set_line_width(3.5 if v < 0.5 else 4.5)
        ctx.set_line_join(cairo.LINE_JOIN_MITER)
        ctx.stroke()
        if v < 0.05 and t < T_Q:                                    # the diameter
            c.lines([(ox - R, oy, ox + R, oy)], WHITE, width=2, alpha=0.5)
            c.text_centered("1", oy - h * 0.008, size=w * 0.045, color=WHITE, cx=ox, alpha=0.8)
        # text: one line at a time
        top = h * 0.255
        if t < T_FOLDED:
            c.text_centered("Fold the corners in…", top, size=w * 0.07, color=WHITE)
            k = int(min(LEVELS, math.floor(L_ + 1e-6)))
            c.text_centered(f"fold {k}", top + h * 0.035, size=w * 0.042, color=SOFT, bold=False)
        elif t < T_Q:
            c.text_centered("…it becomes the circle", top, size=w * 0.07, color=WHITE)
        elif t < T_Z0:
            pop = math.exp(-(t - T_Q) / 0.2)
            c.text_centered("so π = 4 ?!", top + h * 0.01, size=w * 0.13 * (1 + 0.15 * pop), color=PINK)
        elif t < T_Z1 + 0.3:
            c.text_centered("Zoom in…", top, size=w * 0.07, color=WHITE)
        elif t < T_ZO0:
            c.text_centered("STILL a staircase.", top, size=w * 0.075, color=WHITE)
            a = clamp((t - T_Z1 - 1.4) / 0.4)
            c.text_centered("at every zoom, forever", top + h * 0.037, size=w * 0.045, color=SOFT, bold=False, alpha=a)
        elif t < T_RW0:
            a = clamp((t - T_PI) / 0.3)
            pop = math.exp(-(t - T_PI) / 0.2) if t >= T_PI else 0.0
            c.text_centered("π = 3.14159…", top + h * 0.01, size=w * 0.12 * (1 + 0.12 * pop), color=GOLD, alpha=a)
        else:
            c.text_centered("Fold the corners in…", top, size=w * 0.07, color=WHITE, alpha=clamp((t - T_RW1) / 0.25))
        # bottom: the perimeter never changes
        bot = h * 0.765
        if t < T_Z0 or t >= T_RW0:
            pk = 0.0
            for t0, d in FOLDS:
                if t0 + d <= t:
                    pk = max(pk, math.exp(-(t - t0 - d) / 0.15))
            c.text_centered("perimeter = 4", bot, size=w * 0.075 * (1 + 0.12 * pk), color=GOLD)
            if T_FOLDED <= t < T_Z0:
                c.text_centered("circle = π", bot + h * 0.045, size=w * 0.055, color=CYAN)
        elif t < T_ZO0:
            a = clamp((t - T_Z1 - 2.2) / 0.4)
            c.text_centered("the steps shrink, but there are more of them:", bot, size=w * 0.042, color=WHITE,
                            alpha=a, max_w=w * 0.94)
            c.text_centered("the length stays 4. The circle's is π.", bot + h * 0.035, size=w * 0.042, color=GOLD,
                            alpha=a, max_w=w * 0.94)
        else:
            a = clamp((t - T_PI - 0.4) / 0.4)
            c.text_centered("looking the same is not", bot, size=w * 0.05, color=WHITE, alpha=a)
            c.text_centered("being the same length", bot + h * 0.04, size=w * 0.05, color=GOLD, alpha=a)
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
    b = sfx.Bed(T_LOOP, seed=4)
    arp = [(69, 72, 76, 81), (65, 69, 72, 77), (64, 67, 72, 76), (67, 71, 74, 79)]
    pat = [0, 2, 1, 3, 2, 1, 3, 2]
    t, q = 0.0, 0
    while t < T_LOOP - 0.2:
        marimba(b, t, arp[int(t // 3.2) % 4][pat[q % 8]], 0.018 if q % 4 else 0.024)
        t += 0.4
        q += 1
    scale = [60, 62, 64, 67, 69, 72, 74, 76, 79, 81]
    for k, (t0, d) in enumerate(FOLDS):
        b.pluck(t0 + d, scale[(k + 3) % 10] + 12, 0.1, d=0.5)
        b.tick(t0 + d, 2600 + 120 * k, 0.03)
    b.chime(T_FOLDED + 0.05, (76, 79, 84), 0.05)
    b.hit(T_Q, 0.22, low=80)
    b.chime(T_Q + 0.02, (73, 77, 80), 0.05, decay=0.8)
    b.whoosh(T_Z0, T_Z1 - T_Z0, 0.06)
    b.pluck(T_Z1 + 0.3, 76, 0.08, d=0.6)
    b.whoosh(T_ZO0, T_ZO1 - T_ZO0, 0.05, up=False)
    b.hit(T_PI, 0.22, low=90)
    b.chime(T_PI + 0.02, (72, 76, 79, 84, 88), 0.07, decay=1.1)
    for k in range(LEVELS):                                       # the unfold: falling plucks
        b.pluck(T_RW0 + (T_RW1 - T_RW0) * k / LEVELS, scale[(LEVELS - k + 2) % 10] + 12, 0.05, d=0.3)
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
