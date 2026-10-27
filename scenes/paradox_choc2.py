"""PARADOX: 169 = 168 CHOCOLATE (sequel of paradox_choc.py: now a square VANISHES).

A 13 × 13 bar (169) is cut into 4 pieces and rebuilt as 8 × 21 = 168; the pieces secretly OVERLAP along the diagonal
by a sliver of area exactly 1 (slopes 3/8 vs 5/13). Fibonacci 5, 8, 13, 21. Same engine as paradox_choc.

ORIGINAL DOC (64 = 65): — an 8 × 8 chocolate bar (64 squares) is cut into 4 pieces and rebuilt as 5 × 13 = 65.

Lewis Carroll's dissection, made of chocolate. Pieces (grid units, y up; every move is rigid):
  trapezoid L1 (0,0)(5,0)(3,5)(0,5)  -> rotated −90°: (0,5)(0,0)(5,2)(5,5)
  trapezoid L2 (5,0)(8,0)(8,5)(3,5)  -> rotated −90°: (8,3)(8,0)(13,0)(13,5)
  triangle  U1 (0,5)(8,5)(8,8)       -> moved (0,−5)
  triangle  U2 (0,5)(8,8)(0,8)       -> moved (5,−3)
The truth: slopes 3/8 and 2/5 differ, so the long "diagonal" is two bent edges with a thin gap between them,
(0,0)(8,3)(13,5)(5,2), area exactly 1: the extra square is empty table. 5, 8, 13 are Fibonacci numbers.
Recipe (owner, 2026-10-25): the shock in the first 2.5 s, a moving camera, real-looking chocolate, one line of text
at a time, hits on the reveal. Loop: the pieces fly back to the bar.
Audio (original, lib/sfx): snaps on the cuts, whooshes on the flights, a hit + chime on "65", a riser into the
reveal, a warm pad.
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

SCENE = "paradox_choc2"
T_LOOP = 15.0
GOLD, WHITE, RED = (1.0, 0.82, 0.40), (0.97, 0.96, 0.93), (1.0, 0.35, 0.35)
SQ = {"L1": [(0, 0), (8, 0), (5, 8), (0, 8)], "L2": [(8, 0), (13, 0), (13, 8), (5, 8)],
      "U1": [(0, 8), (13, 8), (13, 13)], "U2": [(0, 8), (13, 13), (0, 13)]}
RECT = {"L1": [(0, 8), (0, 0), (8, 3), (8, 8)], "L2": [(13, 5), (13, 0), (21, 0), (21, 8)],
        "U1": [(0, 0), (13, 0), (13, 5)], "U2": [(8, 3), (21, 8), (8, 8)]}
N_SQ = 13
ANG = {"L1": -math.pi / 2, "L2": -math.pi / 2, "U1": 0.0, "U2": 0.0}
ORDER = ["U2", "U1", "L1", "L2"]
SQ_OFF = (4.0, -2.5)                         # the square sits centred on the rectangle's centre
T_CUT = (0.35, 0.6, 0.85)
T_GO = [1.0 + 0.16 * k for k in range(4)]
FLY = 0.9
T_65 = T_GO[-1] + FLY
T_REV0, T_REV1, T_OUT = 5.6, 10.2, 11.2
T_BACK = [11.5 + 0.16 * k for k in range(4)]


def centroid(pts):
    return sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)


def piece_state(name, t):
    """-> (u in [0,1] from square to rectangle, lift)."""
    k = ORDER.index(name)
    a = smooth(min(1.0, max(0.0, (t - T_GO[k]) / FLY)))
    b = smooth(min(1.0, max(0.0, (t - T_BACK[3 - k]) / FLY)))
    u = a * (1 - b)
    lift = math.sin(math.pi * min(1.0, max(0.0, (t - T_GO[k]) / FLY))) if t < T_BACK[0] else \
        math.sin(math.pi * min(1.0, max(0.0, (t - T_BACK[3 - k]) / FLY)))
    return u, max(0.0, lift)


def camera(t):
    """(focus x, focus y, zoom) in grid units; a slow drift, the dive into the gap, and back (periodic)."""
    fx, fy, z = 10.5, 4.0, 1.0
    z *= 1.0 + 0.03 * math.sin(2 * math.pi * t / T_LOOP)
    fx += 0.15 * math.sin(2 * math.pi * t / T_LOOP)
    if T_REV0 <= t < T_OUT:
        u = smooth(min(1.0, (t - T_REV0) / 1.2)) * (1 - smooth(min(1.0, max(0.0, (t - T_REV1) / (T_OUT - T_REV1)))))
        z = z * (1 + 1.6 * u)
        fx, fy = fx + (10.5 - fx) * u, fy + (4.0 - fy) * u
    return fx, fy, z


class Scene:
    def __init__(self, layout):
        self.L = layout
        self.canvas = Canvas(layout.w, layout.h, studio.render_scale())
        w, h = layout.w, layout.h
        self.cell = w * 0.86 / 21
        self.cx, self.cy = w * 0.5, h * 0.45

    def table(self, ctx, t):
        w, h = self.L.w, self.L.h
        g = cairo.LinearGradient(0, 0, 0, h)
        g.add_color_stop_rgb(0, 0.10, 0.06, 0.04)
        g.add_color_stop_rgb(1, 0.03, 0.02, 0.015)
        ctx.set_source(g)
        ctx.paint()
        for k in range(14):                                        # wood planks
            y = h * (0.05 + k * 0.07)
            ctx.rectangle(0, y, w, 2)
            ctx.set_source_rgba(0, 0, 0, 0.35)
            ctx.fill()
            for q in range(6):
                xx = (k * 173 + q * 211) % int(w)
                ctx.rectangle(xx, y + 10 + (q * 7) % 30, w * 0.18, 1.5)
                ctx.set_source_rgba(0.35, 0.22, 0.12, 0.10)
                ctx.fill()
        sp = cairo.RadialGradient(w / 2, h * 0.45, 0, w / 2, h * 0.45, h * 0.55)  # warm spotlight
        sp.add_color_stop_rgba(0, 1.0, 0.75, 0.45, 0.16)
        sp.add_color_stop_rgba(1, 0, 0, 0, 0.0)
        ctx.set_source(sp)
        ctx.paint()

    def world(self, ctx, fx, fy, z):
        S = self.cell * z
        ctx.translate(self.cx, self.cy)
        ctx.scale(S, -S)
        ctx.translate(-fx, -fy)
        return S

    def piece_xf(self, ctx, name, u):
        src = [(x + SQ_OFF[0], y + SQ_OFF[1]) for x, y in SQ[name]]
        cs, cd = centroid(src), centroid(RECT[name])
        cc = (cs[0] + (cd[0] - cs[0]) * u, cs[1] + (cd[1] - cs[1]) * u)
        ctx.translate(*cc)
        ctx.rotate(ANG[name] * u)
        ctx.translate(-cs[0], -cs[1])
        return src

    def draw_piece(self, ctx, name, src, S, lift):
        c = self.canvas
        ox, oy = SQ_OFF
        # shadow (soft: three layers)
        for k, a in ((3, 0.10), (2, 0.14), (1, 0.18)):
            ctx.save()
            ctx.translate(0.05 * k + 0.25 * lift, -0.06 * k - 0.35 * lift)
            ctx.new_path()
            for i, p in enumerate(src):
                (ctx.move_to if i == 0 else ctx.line_to)(*p)
            ctx.close_path()
            ctx.set_source_rgba(0, 0, 0, a + 0.1 * lift)
            ctx.fill()
            ctx.restore()
        ctx.save()
        ctx.translate(0, 0.25 * lift)
        ctx.new_path()
        for i, p in enumerate(src):
            (ctx.move_to if i == 0 else ctx.line_to)(*p)
        ctx.close_path()
        ctx.save()
        ctx.clip_preserve()
        g = cairo.LinearGradient(ox, oy + N_SQ, ox + N_SQ, oy)
        g.add_color_stop_rgb(0, 0.42, 0.24, 0.13)
        g.add_color_stop_rgb(1, 0.30, 0.16, 0.08)
        ctx.set_source(g)
        ctx.fill()
        for i in range(N_SQ):                                       # the squares, embossed
            for j in range(N_SQ):
                x0, y0 = ox + i + 0.09, oy + j + 0.09
                ctx.rectangle(x0, y0, 0.82, 0.82)
                ctx.set_source_rgba(0.50, 0.30, 0.17, 0.9)
                ctx.fill()
                ctx.rectangle(x0, y0 + 0.74, 0.82, 0.08)            # top light edge (y up)
                ctx.set_source_rgba(0.80, 0.55, 0.35, 0.55)
                ctx.fill()
                ctx.rectangle(x0, y0, 0.07, 0.82)
                ctx.set_source_rgba(0.75, 0.50, 0.32, 0.35)
                ctx.fill()
                ctx.rectangle(x0, y0, 0.82, 0.07)                   # bottom shade
                ctx.set_source_rgba(0.12, 0.06, 0.03, 0.55)
                ctx.fill()
        gl = cairo.LinearGradient(ox, oy + 13, ox + 6, oy + 5)      # gloss
        gl.add_color_stop_rgba(0, 1, 0.9, 0.8, 0.16)
        gl.add_color_stop_rgba(1, 1, 0.9, 0.8, 0.0)
        ctx.set_source(gl)
        ctx.paint()
        ctx.restore()
        ctx.set_source_rgba(0.12, 0.06, 0.03, 1)                    # cut edge
        ctx.set_line_width(2.6 / S)
        ctx.stroke()
        ctx.restore()

    def draw(self, f, rule):
        L, c = self.L, self.canvas
        w, h = L.w, L.h
        t = f * DT
        ctx = c.ctx
        self.table(ctx, t)
        fx, fy, z = camera(t)
        rev = smooth(min(1.0, max(0.0, (t - T_REV0 - 0.8) / 0.6))) * (1 - smooth(min(1.0, max(0.0, (t - T_REV1) / 0.6))))
        ctx.save()
        S = self.world(ctx, fx, fy, z)
        moving = sorted(ORDER, key=lambda nm: piece_state(nm, t)[1])
        for nm in moving:
            u, lift = piece_state(nm, t)
            ctx.save()
            src = self.piece_xf(ctx, nm, u)
            self.draw_piece(ctx, nm, src, S, lift)
            ctx.restore()
        # the knife: glowing cut lines on the bar just before it splits
        for k, tc in enumerate(T_CUT):
            a = math.exp(-max(0.0, t - tc) / 0.25) if tc <= t < T_GO[0] + 0.2 else 0.0
            if a > 0.02:
                ox, oy = SQ_OFF
                seg = [((ox, oy + 8), (ox + 13, oy + 8)), ((ox, oy + 8), (ox + 13, oy + 13)), ((ox + 8, oy), (ox + 5, oy + 8))][k]
                ctx.move_to(*seg[0])
                ctx.line_to(*seg[1])
                ctx.set_source_rgba(1, 0.95, 0.85, a)
                ctx.set_line_width(5 / S)
                ctx.stroke()
        # the reveal: the gap between the bent edges glows (it is the "extra" square)
        if rev > 0.01:
            ctx.new_path()
            for i, p in enumerate(((0, 0), (8, 3), (21, 8), (13, 5))):
                (ctx.move_to if i == 0 else ctx.line_to)(*p)
            ctx.close_path()
            ctx.set_source_rgba(1.0, 0.25, 0.25, 0.55 * rev)
            ctx.fill_preserve()
            ctx.set_source_rgba(1.0, 0.5, 0.45, rev)
            ctx.set_line_width(3 / S)
            ctx.stroke()
            ctx.set_dash([0.25, 0.18])
            ctx.move_to(0, 0)
            ctx.line_to(21, 8)
            ctx.set_source_rgba(1, 1, 1, 0.8 * rev)
            ctx.set_line_width(2 / S)
            ctx.stroke()
            ctx.set_dash([])
        ctx.restore()
        # the numbers: one big line at a time
        in_rect = all(piece_state(nm, t)[0] > 0.999 for nm in ORDER)
        if in_rect:
            k = t - T_65
            pop = 1 + 0.35 * math.exp(-max(0.0, k) / 0.12)
            c.glow(w / 2, h * 0.205, w * 0.25, GOLD, strength=0.35 * math.exp(-max(0.0, k) / 0.6), reach=1.8)
            c.text_centered("8 × 21 = 168", h * 0.225, size=w * 0.12 * pop, color=GOLD)
        else:
            c.text_centered("13 × 13 = 169", h * 0.225, size=w * 0.12, color=WHITE)
        if in_rect and t < T_REV0 + 0.8:
            c.text_centered("−1 square of chocolate?!", h * 0.74, size=w * 0.06, color=RED)
        elif rev > 0.01:
            line = "The pieces secretly OVERLAP…" if t < T_REV0 + 2.6 else "the overlap = exactly 1 square"
            c.text_centered(line, h * 0.74, size=w * 0.06, color=WHITE if t < T_REV0 + 2.6 else GOLD, alpha=rev)
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
    b = sfx.Bed(T_LOOP, seed=3)
    beat = 60 / 96
    b.pad([(0.0, (45, 52, 57, 60)), (T_65, (41, 48, 53, 57)), (T_REV0, (43, 50, 55, 59)),
           (T_REV1, (45, 52, 57, 60))], beat, g=0.05)
    for tc in T_CUT:
        b.snap(tc, 0.35)
    for k, tg in enumerate(T_GO):
        b.whoosh(tg + 0.1, 0.7, 0.10)
    b.hit(T_65, 0.55)
    b.chime(T_65 + 0.02, (79, 84, 88), 0.09)
    b.riser(T_REV0, 0.9, 0.06)
    b.hit(T_REV0 + 0.9, 0.3, low=40)
    b.chime(T_REV0 + 2.6, (72, 76, 79, 84), 0.07)
    for k, tg in enumerate(T_BACK):
        b.whoosh(tg + 0.1, 0.6, 0.07, up=False)
    for k in range(4):
        b.snap(T_BACK[k] + FLY - 0.05, 0.12)
    b.pulse(T_65 + 0.2, T_REV0, beat, [69, 72, 76, 72], 0.03)
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
