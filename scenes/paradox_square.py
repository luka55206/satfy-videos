"""PARADOX: THE MISSING SQUARE — 4 pieces make a 13 × 5 "triangle"; slide them around and a square goes missing.

Pieces (cells on a 13 × 5 grid, translations only, nothing rotates):
  red triangle  (0,0)(8,0)(8,3)     area 12      ->  moved by (+5, +2)
  blue triangle (8,3)(13,3)(13,5)   area 5       ->  moved by (−8, −3)
  yellow L      8 cells                          ->  (8,0) → (5,0)
  green L       7 cells                          ->  (8,1) → (8,0)
Total 32 cells both times. The trick: the slopes are 3/8 = 0.375 and 2/5 = 0.4, so neither shape is a triangle. The
long edge bends in (first) or out (second), and the sliver between the two bent edges, (0,0)(8,3)(13,5)(5,2), has
area exactly 1: the missing square. The reveal draws the true straight line, fills the sliver and magnifies the bend.
Loop: the pieces slide back to frame 0.
Audio (original): a rising glass-harp note per piece move, a low knock when the hole appears, a chord on the reveal,
falling notes as they slide back, a loop pad.
"""
import math
import sys
from pathlib import Path

import cairo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib import kit, studio  # noqa: E402
from lib.kit import DT, FPS, arg, smooth  # noqa: E402
from lib.layouts import get_layout  # noqa: E402
from lib.studio import Canvas, VideoWriter  # noqa: E402

SCENE = "paradox_square"
T_LOOP = 16.0
RED, BLUE, YEL, GRN = (1.0, 0.36, 0.42), (0.32, 0.65, 1.0), (1.0, 0.80, 0.30), (0.40, 0.88, 0.50)
GOLD, WHITE = (1.0, 0.82, 0.40), (0.95, 0.96, 1.0)
YEL_CELLS = [(x, 0) for x in range(5)] + [(x, 1) for x in range(3)]
GRN_CELLS = [(3, 0), (4, 0)] + [(x, 1) for x in range(5)]
# piece: (kind, colour, shape, offset A, offset B)
PIECES = [
    ("tri", RED, [(0, 0), (8, 0), (8, 3)], (0, 0), (5, 2)),
    ("tri", BLUE, [(8, 3), (13, 3), (13, 5)], (0, 0), (-8, -3)),
    ("cells", YEL, YEL_CELLS, (8, 0), (5, 0)),
    ("cells", GRN, GRN_CELLS, (8, 1), (8, 0)),
]
MOVE_GO = [0.6, 1.4, 2.2, 3.0]               # A -> B, one piece after another
MOVE_BACK = [11.6, 12.4, 13.2, 14.0]         # B -> A (reverse order)
MOVE_D = 0.85
T_HOLE = MOVE_GO[-1] + MOVE_D
T_REV0, T_REV1 = 6.6, 11.3


def piece_u(i, t):
    """0 = position A, 1 = position B."""
    a = smooth(min(1.0, max(0.0, (t - MOVE_GO[i]) / MOVE_D)))
    j = 3 - i                                   # back in reverse order
    b = smooth(min(1.0, max(0.0, (t - MOVE_BACK[j]) / MOVE_D)))
    return a * (1 - b)


class Scene:
    def __init__(self, layout):
        self.L = layout
        self.canvas = Canvas(layout.w, layout.h, studio.render_scale())
        w, h = layout.w, layout.h
        self.cell = w * 0.88 / 13
        self.x0 = w * 0.06
        self.y0 = h * 0.53                      # grid bottom (y up in cells)

    def P(self, x, y):
        return self.x0 + x * self.cell, self.y0 - y * self.cell

    def path_piece(self, ctx, kind, shape, ox, oy):
        ctx.new_path()
        if kind == "tri":
            for k, (x, y) in enumerate(shape):
                px, py = self.P(x + ox, y + oy)
                (ctx.move_to if k == 0 else ctx.line_to)(px, py)
            ctx.close_path()
        else:
            for (cx, cy) in shape:
                px, py = self.P(cx + ox, cy + oy + 1)
                ctx.rectangle(px, py, self.cell, self.cell)

    def draw_piece(self, i, t, lift):
        c = self.canvas
        ctx = c.ctx
        kind, col, shape, a, b = PIECES[i]
        u = piece_u(i, t)
        ox, oy = a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u
        if lift > 0:                                          # shadow while it moves
            ctx.save()
            ctx.translate(self.cell * 0.12 * lift, self.cell * 0.18 * lift)
            self.path_piece(ctx, kind, shape, ox, oy)
            ctx.set_source_rgba(0, 0, 0, 0.45 * lift)
            ctx.fill()
            ctx.restore()
        self.path_piece(ctx, kind, shape, ox, oy - 0.12 * lift)
        ctx.set_source_rgba(*col, 0.92)
        ctx.fill_preserve()
        ctx.set_source_rgba(0.04, 0.03, 0.08, 0.9)
        ctx.set_line_width(max(2.0, self.cell * 0.05))
        ctx.stroke()
        if kind == "cells":                                   # the cells you can count
            for (cx, cy) in shape:
                px, py = self.P(cx + ox, cy + oy - 0.12 * lift + 1)
                c.text_centered("", py, size=1)
                ctx.rectangle(px + self.cell * 0.08, py + self.cell * 0.08, self.cell * 0.84, self.cell * 0.84)
                ctx.set_source_rgba(1, 1, 1, 0.10)
                ctx.fill()

    def draw(self, f, rule):
        L, c = self.L, self.canvas
        w, h = L.w, L.h
        t = f * DT
        ctx = c.ctx
        g = cairo.RadialGradient(w / 2, h * 0.43, 0, w / 2, h * 0.43, h * 0.7)
        g.add_color_stop_rgb(0, 0.07, 0.06, 0.13)
        g.add_color_stop_rgb(1, 0.005, 0.005, 0.015)
        ctx.set_source(g)
        ctx.paint()
        # the grid
        segs = [(*self.P(x, 0), *self.P(x, 5)) for x in range(14)] + [(*self.P(0, y), *self.P(13, y)) for y in range(6)]
        c.lines(segs, (0.45, 0.5, 0.75), width=1.2, alpha=0.28)
        rev = smooth(min(1.0, max(0.0, (t - T_REV0) / 0.6))) * (1 - smooth(min(1.0, max(0.0, (t - T_REV1) / 0.5))))
        # the pieces (moving ones on top)
        order = sorted(range(4), key=lambda i: 0 if piece_u(i, t) in (0.0, 1.0) else 1)
        for i in order:
            u = piece_u(i, t)
            lift = math.sin(math.pi * u) if 0 < u < 1 else 0.0
            self.draw_piece(i, t, lift)
        # the hole
        in_b = all(piece_u(i, t) > 0.999 for i in range(4))
        if in_b:
            k = t - T_HOLE
            hx, hy = self.P(10, 1)
            pulse = 0.5 + 0.5 * math.sin(k * 5)
            ctx.rectangle(hx, hy, self.cell, self.cell)
            ctx.set_source_rgba(1.0, 0.25, 0.3, 0.25 + 0.25 * pulse)
            ctx.fill()
            c.glow(hx + self.cell / 2, hy + self.cell / 2, self.cell * 1.2, (1.0, 0.3, 0.35), strength=0.4 + 0.3 * pulse,
                   reach=2.0)
            c.text_centered("?", hy + self.cell * 0.78, size=self.cell * 0.85, color=WHITE, cx=hx + self.cell / 2)
            if k < 0.8:
                c.ring(hx + self.cell / 2, hy + self.cell / 2, self.cell * (0.6 + 2.5 * k), (1.0, 0.4, 0.45), width=3,
                       alpha=1 - k / 0.8)
        # the reveal: true straight line, the bent edges, the sliver of area 1, a magnifier on the bend
        if rev > 0.01:
            ctx.new_path()
            for k, (x, y) in enumerate(((0, 0), (8, 3), (13, 5), (5, 2))):
                (ctx.move_to if k == 0 else ctx.line_to)(*self.P(x, y))
            ctx.close_path()
            ctx.set_source_rgba(1.0, 0.25, 0.3, 0.85 * rev)
            ctx.fill()
            c.lines([(*self.P(0, 0), *self.P(8, 3)), (*self.P(8, 3), *self.P(13, 5))], RED, width=3, alpha=rev)
            c.lines([(*self.P(0, 0), *self.P(5, 2)), (*self.P(5, 2), *self.P(13, 5))], BLUE, width=3, alpha=rev)
            ctx.set_dash([10, 8])
            c.lines([(*self.P(0, 0), *self.P(13, 5))], WHITE, width=2.5, alpha=0.9 * rev)
            ctx.set_dash([])
            # magnifier around the bend at (6.5, 2.5)
            mcx, mcy, mr, z = w * 0.5, h * 0.66, w * 0.17, 9.0
            fx, fy = 6.5, 2.5
            ctx.save()
            ctx.new_path()
            ctx.arc(mcx, mcy, mr, 0, 2 * math.pi)
            ctx.set_source_rgba(0.03, 0.03, 0.07, 0.95 * rev)
            ctx.fill_preserve()
            ctx.clip()

            def M(x, y):
                return mcx + (x - fx) * self.cell * z / 4, mcy - (y - fy) * self.cell * z / 4
            ctx.new_path()
            for k, (x, y) in enumerate(((0, 0), (8, 3), (13, 5), (5, 2))):
                (ctx.move_to if k == 0 else ctx.line_to)(*M(x, y))
            ctx.close_path()
            ctx.set_source_rgba(1.0, 0.25, 0.3, 0.7 * rev)
            ctx.fill()
            c.lines([(*M(0, 0), *M(8, 3)), (*M(8, 3), *M(13, 5))], RED, width=4, alpha=rev)
            c.lines([(*M(0, 0), *M(5, 2)), (*M(5, 2), *M(13, 5))], BLUE, width=4, alpha=rev)
            ctx.set_dash([10, 8])
            c.lines([(*M(0, 0), *M(13, 5))], WHITE, width=2.5, alpha=rev)
            ctx.set_dash([])
            ctx.restore()
            c.ring(mcx, mcy, mr, GOLD, width=4, alpha=rev)
            px, py = self.P(fx, fy)
            c.ring(px, py, self.cell * 0.9, GOLD, width=3, alpha=rev)
            c.lines([(px, py + self.cell * 0.9, mcx, mcy - mr)], GOLD, width=2, alpha=0.7 * rev)
            c.text_centered("slopes 3/8 = 0.375  vs  2/5 = 0.400", h * 0.80, size=w * 0.045, color=WHITE, alpha=rev)
            c.text_centered("It was never a triangle. This sliver = 1 square.", h * 0.835, size=w * 0.04, color=GOLD,
                            alpha=rev, max_w=w * 0.94)
        elif in_b:
            c.text_centered("same 4 pieces… 1 square MISSING", h * 0.66, size=w * 0.055, color=(1.0, 0.5, 0.55))
        else:
            c.text_centered("12 + 5 + 8 + 7 = 32 squares", h * 0.66, size=w * 0.05, color=(0.85, 0.88, 1.0), bold=False)
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


def build_events(layout):
    w = layout.w
    ev = []
    for i, t in enumerate(MOVE_GO):
        ev.append({"t": t, "note": 64 + 3 * i, "gain": 0.4, "x": w * (0.3 + 0.12 * i)})
    ev.append({"t": T_HOLE, "note": 40, "note_gain": 0.5, "pok": 0.8, "pok_gain": 0.6, "gain": 0.55, "x": w * 0.6})
    ev.append({"t": T_HOLE + 0.02, "note": 52, "gain": 0.35, "x": w * 0.6})
    for j, n in enumerate((48, 55, 60, 64, 67)):
        ev.append({"t": T_REV0 + 0.05 * j, "note": n, "gain": 0.4, "x": w / 2})
    for j, n in enumerate((79, 76)):
        ev.append({"t": T_REV0 + 1.2 + 0.4 * j, "note": n, "gain": 0.25, "x": w / 2})
    for i, t in enumerate(MOVE_BACK):
        ev.append({"t": t, "note": 73 - 3 * i, "gain": 0.32, "x": w * (0.7 - 0.12 * i)})
    return sorted(ev, key=lambda e: e["t"])


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
    pad = kit.loop_pad(d, ((45, 1.0), (52, 0.6), (57, 0.4), (64, 0.25)), gain=0.025)
    kit.deliver_loop(SCENE, name, layout, video, build_events(layout), d, voice="glassharp", bed=pad)


if __name__ == "__main__":
    main()
