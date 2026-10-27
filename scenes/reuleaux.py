"""REULEAUX — "This drill makes SQUARE holes": a Reuleaux triangle (constant width) spinning inside a square.

The Reuleaux triangle = three circle arcs of radius W through the corners of an equilateral triangle of side W, so it
has the same width W in every direction. For each rotation angle its centre is placed EXACTLY where its support
function says (c_x = W/2 − h(+x), c_y = W/2 − h(+y)), so it always touches all four walls of a W×W square while it
turns. The swept area (the "hole") is accumulated: it covers 98.77 % of the square (only tiny rounded corners stay).
Timeline: 0–6 s carve the hole (1 full turn of the bit) · 6–9.4 s it keeps spinning in the finished square hole ·
9.4–10.8 s the block slides away and a fresh block slides in = frame 0 (loop).
Audio (original): a soft note every time a corner of the bit touches a wall (rhythm), a chord when the hole is done,
a whoosh-like falling run on the block change.
"""
import math
import sys
from pathlib import Path

import cairo
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib import kit, studio  # noqa: E402
from lib.kit import DT, FPS, arg, smooth  # noqa: E402
from lib.layouts import get_layout  # noqa: E402
from lib.studio import Canvas, VideoWriter  # noqa: E402

SCENE = "reuleaux"
T_CARVE, T_SPIN, T_SLIDE = 6.0, 9.4, 10.8
T_LOOP = T_SLIDE
OMEGA = 2 * math.pi / 3.0                       # rad/s: one full turn every 3 s
GOLD = (1.0, 0.82, 0.40)
WOOD = (0.45, 0.30, 0.20)


def reuleaux_boundary(n=360):
    """Boundary (unit width) centred on its centroid, counter-clockwise."""
    V = [complex(math.cos(a), math.sin(a)) / math.sqrt(3) for a in (math.pi / 2, math.pi / 2 + 2 * math.pi / 3,
                                                                      math.pi / 2 + 4 * math.pi / 3)]
    pts = []
    for i in range(3):
        cen = V[i]                                   # arc opposite vertex i, centred on vertex i
        a, b = V[(i + 1) % 3], V[(i + 2) % 3]
        a0, a1 = math.atan2((a - cen).imag, (a - cen).real), math.atan2((b - cen).imag, (b - cen).real)
        da = (a1 - a0 + math.pi) % (2 * math.pi) - math.pi
        for j in range(n // 3):
            th = a0 + da * j / (n // 3)
            pts.append(cen + complex(math.cos(th), math.sin(th)))
    return np.array(pts)


B = reuleaux_boundary()
VERTS = np.array([complex(math.cos(a), math.sin(a)) / math.sqrt(3) for a in (math.pi / 2, math.pi / 2 + 2 * math.pi / 3,
                                                                              math.pi / 2 + 4 * math.pi / 3)])


def pose(alpha):
    """Rotated boundary + centre so it touches all four walls of the unit square [−½, ½]²."""
    rb = B * complex(math.cos(alpha), math.sin(alpha))
    cx = 0.5 - rb.real.max()
    cy = 0.5 - rb.imag.max()
    return rb + complex(cx, cy), complex(cx, cy)


T_RAMP = 3.0                                    # slow start so the square visibly forms


def angle_at(t):
    if t < T_RAMP:
        return 0.35 * OMEGA * t + 0.65 * OMEGA * t * t / (2 * T_RAMP)
    a1 = 0.35 * OMEGA * T_RAMP + 0.65 * OMEGA * T_RAMP / 2
    if t < T_SPIN:
        return a1 + OMEGA * (t - T_RAMP)
    a2 = a1 + OMEGA * (T_SPIN - T_RAMP)
    third = 2 * math.pi / 3                        # land exactly on a multiple of 120° (3-fold symmetry) = frame 0
    end = math.ceil((a2 + 0.4 * OMEGA * (T_SLIDE - T_SPIN)) / third) * third
    u = (t - T_SPIN) / (T_SLIDE - T_SPIN)
    v0 = OMEGA * (T_SLIDE - T_SPIN)                # start speed (same as before), cubic ease to the exact end angle
    d = end - a2
    return a2 + v0 * u * (1 - u) ** 2 + d * u * u * (3 - 2 * u) + (v0 * 0) * u


def simulate():
    return {"nf": int(round(T_LOOP * FPS))}


class Scene:
    def __init__(self, layout, sim):
        self.L, self.sim = layout, sim
        self.canvas = Canvas(layout.w, layout.h, studio.render_scale())
        w, h = layout.w, layout.h
        self.W = w * 0.62
        self.cx, self.cy = w / 2, h * 0.45
        c = self.canvas
        self.hole = cairo.ImageSurface(cairo.FORMAT_ARGB32, c.pw, c.ph)
        self.hctx = cairo.Context(self.hole)
        self.hctx.scale(c.pw / w, c.ph / h)
        self.last_carve = -1.0
        self.trail = []

    def P(self, z, ox=0.0):
        return self.cx + ox + self.W * z.real, self.cy - self.W * z.imag

    def carve_to(self, t):
        """Accumulate the swept area up to time t (dense sub-steps)."""
        t = min(t, T_CARVE)
        while self.last_carve < t:
            self.last_carve = self.last_carve + 1 / 240 if self.last_carve >= 0 else 0.0
            pts, cen = pose(angle_at(self.last_carve))
            ctx = self.hctx
            ctx.move_to(*self.P(pts[0]))
            for z in pts[1:]:
                ctx.line_to(*self.P(z))
            ctx.close_path()
            ctx.set_source_rgba(0.03, 0.03, 0.05, 1.0)
            ctx.fill()
            self.trail.append(cen)

    def draw(self, f, rule):
        L, c = self.L, self.canvas
        w, h = L.w, L.h
        t = f * DT
        ctx = c.ctx
        g = cairo.RadialGradient(w / 2, h * 0.45, 0, w / 2, h * 0.45, max(w, h) * 0.7)
        g.add_color_stop_rgb(0.0, 0.08, 0.07, 0.12)
        g.add_color_stop_rgb(1.0, 0.01, 0.01, 0.02)
        ctx.set_source(g)
        ctx.paint()
        if t < T_SPIN:
            self.carve_to(t)
        slide = smooth((t - T_SPIN) / (T_SLIDE - T_SPIN)) if t >= T_SPIN else 0.0
        Wpx = self.W
        for k, off in ((0, -slide * w * 1.1), (1, (1 - slide) * w * 1.1)):      # old block leaves, new block arrives
            if k == 1 and slide <= 0:
                continue
            bx = self.cx + off
            x0, y0 = bx - Wpx * 0.85, self.cy - Wpx * 0.85
            grd = cairo.LinearGradient(x0, y0, x0 + Wpx * 1.7, y0 + Wpx * 1.7)
            grd.add_color_stop_rgb(0, 0.55, 0.38, 0.24)
            grd.add_color_stop_rgb(1, 0.36, 0.23, 0.14)
            ctx.rectangle(x0, y0, Wpx * 1.7, Wpx * 1.7)
            ctx.set_source(grd)
            ctx.fill()
            ctx.set_source_rgba(0.25, 0.16, 0.10, 0.35)                     # wood grain
            ctx.set_line_width(2)
            for i in range(14):
                yy = y0 + Wpx * 1.7 * (i + 0.5) / 14
                ctx.move_to(x0, yy)
                ctx.curve_to(x0 + Wpx * 0.6, yy + 8, x0 + Wpx * 1.1, yy - 8, x0 + Wpx * 1.7, yy)
            ctx.stroke()
            if k == 0:                                                       # the carved hole
                ctx.save()
                ctx.translate(off, 0)
                ctx.scale(w / c.pw, h / c.ph)
                ctx.set_source_surface(self.hole, 0, 0)
                ctx.paint()
                ctx.restore()
        # the target square outline (on the current block)
        ox = -slide * w * 1.1 if t >= T_SPIN else 0.0
        sq = [complex(-0.5, -0.5), complex(0.5, -0.5), complex(0.5, 0.5), complex(-0.5, 0.5), complex(-0.5, -0.5)]
        c.polylines([[self.P(z, ox) for z in sq]], GOLD, width=3, alpha=0.75)
        # the bit
        pts, cen = pose(angle_at(t))
        poly = [self.P(z, 0.0) for z in pts]
        ctx.move_to(*poly[0])
        for q in poly[1:]:
            ctx.line_to(*q)
        ctx.close_path()
        gb = cairo.RadialGradient(*self.P(cen), 0, *self.P(cen), Wpx * 0.6)
        gb.add_color_stop_rgba(0, 0.85, 0.90, 1.0, 0.95)
        gb.add_color_stop_rgba(1, 0.45, 0.55, 0.75, 0.95)
        ctx.set_source(gb)
        ctx.fill_preserve()
        ctx.set_source_rgba(1, 1, 1, 0.9)
        ctx.set_line_width(3)
        ctx.stroke()
        for v in VERTS:                                                      # the three corners
            z = v * complex(math.cos(angle_at(t)), math.sin(angle_at(t))) + cen
            c.glow(*self.P(z), 8, GOLD, strength=0.6, reach=3)
        c.circle(*self.P(cen), 7, (0.2, 0.2, 0.3), alpha=1.0)
        if len(self.trail) > 2 and t < T_SPIN:                              # the centre's path
            c.polylines([[self.P(z) for z in self.trail[-240:]]], (1.0, 0.45, 0.45), width=2.5, alpha=0.8)
        # text
        done = t >= T_CARVE
        if done and t < T_SPIN + 0.4:
            a = smooth((t - T_CARVE) / 0.3)
            c.text_centered("98.8 % of a perfect square", h * 0.765, size=w * 0.062, color=GOLD, alpha=a)
            c.text_centered("only 4 tiny rounded corners are missing", h * 0.80, size=w * 0.034,
                            color=(0.85, 0.86, 0.92), alpha=0.9 * a, bold=False)
        else:
            c.text_centered("a Reuleaux triangle", h * 0.765, size=w * 0.062, color=(0.95, 0.95, 1.0), alpha=1.0)
            c.text_centered("same width in every direction", h * 0.80, size=w * 0.036, color=(0.75, 0.78, 0.88),
                            alpha=0.9, bold=False)
        c.text_centered("SHAPES OF CONSTANT WIDTH", h * 0.205, size=h * 0.015, color=GOLD, alpha=0.85)
        if rule:
            c.caption(rule, alpha=1.0, layout=L)
        c.watermark(L)


def render(layout, sim, out_path, rule, still_frame=None):
    sc = Scene(layout, sim)
    writer = None if still_frame is not None else VideoWriter(out_path, sc.canvas, FPS)
    for f in range(sim["nf"]):
        if still_frame is not None and f != still_frame:
            sc.carve_to(min(f * DT, T_CARVE))
            continue
        sc.draw(f, rule)
        if writer is None:
            studio.save_still(sc.canvas, out_path)
            return f / FPS
        writer.write_frame()
    writer.close()
    return sim["nf"] / FPS


def build_events(sim, layout):
    out = []
    notes = [72, 76, 79, 84]
    t, k = 0.0, 0
    while t < T_SPIN:                                       # a corner meets a wall 4×(turn) … every 1/8 turn approx
        out.append({"t": round(t + 0.004, 4), "note": notes[k % 4] - (12 if t > T_CARVE else 0), "gain": 0.26,
                    "x": layout.w * (0.3 + 0.13 * (k % 4))})
        k += 1
        t += (2 * math.pi / OMEGA) / 6
    for j, m in enumerate((48, 55, 60, 64, 67, 72)):
        out.append({"t": round(T_CARVE + 0.05 * j, 4), "note": m, "gain": 0.28, "x": layout.w / 2})
    for j in range(8):
        out.append({"t": round(T_SPIN + 0.12 * j, 4), "note": 88 - 3 * j, "gain": 0.12, "x": layout.w / 2})
    return sorted(out, key=lambda e: e["t"])


def _worker(o, sim, label, rule):
    layout = get_layout(o)
    name = f"{SCENE}_{label}_{layout.tag}"
    video = studio.OUT_DIR / f"{name}_silent.mp4"
    d = render(layout, sim, video, rule)
    pad = kit.loop_pad(T_LOOP, ((48, 1.0), (55, 0.7), (60, 0.45), (64, 0.3)), gain=0.013)
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
    print(f"[{SCENE}] {T_LOOP:.1f}s")
    kit.fan_out(_worker, (sim, label, rule), SCENE)


if __name__ == "__main__":
    main()
