"""REULEAUX HOWTO — "How to drill a perfect SQUARE hole" (tutorial-style take on scenes/reuleaux.py; that file is untouched).

0.0–1.2   HOOK: the finished square hole with the bit spinning in it, "HOW TO DRILL A SQUARE HOLE"
1.2–1.5   reset to a fresh block
1.5–3.3   STEP 1: draw a triangle (equal sides)
3.3–5.7   STEP 2: round each side with a compass (pivot on a corner, arc between the other two) → Reuleaux triangle
5.7–6.3   STEP 3: put it in a square
6.3–12.3  drill: it spins touching all 4 walls; the carved hole grows into a square (same motion as scenes/reuleaux.py)
12.3–15.0 "a SQUARE hole" — the bit keeps spinning; the end pose = the frame-0 pose (seamless loop).
Audio (original): pencil/compass scratches, pops, a drill hum during the carve, corner-touch notes, a ding.
"""
import math
import sys
from pathlib import Path

import cairo
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib import audio, kit, studio  # noqa: E402
from lib.kit import DT, FPS, arg, smooth  # noqa: E402
from lib.layouts import get_layout  # noqa: E402
from lib.studio import Canvas, VideoWriter  # noqa: E402
import reuleaux as R0  # noqa: E402  (shape, pose and the carve motion are shared, unchanged)

SCENE = "reuleaux_howto"
T_HOOK, T_RESET = 1.2, 1.5
T_S1, T_S2, T_S3 = 1.5, 3.3, 5.7
T_C0 = 6.3
T_C1 = T_C0 + R0.T_CARVE
T_LOOP = 15.0
OMEGA = R0.OMEGA
GOLD = (1.0, 0.82, 0.40)
A_C1 = R0.angle_at(R0.T_CARVE)
A_END = A_C1 + OMEGA * (T_LOOP - T_C1)
SR = audio.SR


def bit_angle(t):
    if t < T_HOOK:
        return A_END + OMEGA * t
    if t < T_C0:
        return 0.0
    if t < T_C1:
        return R0.angle_at(t - T_C0)
    return A_C1 + OMEGA * (t - T_C1)


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

        def surf():
            s = cairo.ImageSurface(cairo.FORMAT_ARGB32, c.pw, c.ph)
            x = cairo.Context(s)
            x.scale(c.pw / w, c.ph / h)
            return s, x

        self.hole, self.hctx = surf()
        self.full, fctx = surf()
        for k in range(400):                                    # the complete hole (any 120° of rotation sweeps it)
            self.fill_pose(fctx, 2 * math.pi / 3 * k / 400)
        self.last = -1.0

    def P(self, z):
        return self.cx + self.W * z.real, self.cy - self.W * z.imag

    def fill_pose(self, ctx, a):
        pts, _ = R0.pose(a)
        ctx.move_to(*self.P(pts[0]))
        for z in pts[1:]:
            ctx.line_to(*self.P(z))
        ctx.close_path()
        ctx.set_source_rgba(0.03, 0.03, 0.05, 1.0)
        ctx.fill()

    def carve_to(self, tc):
        tc = min(tc, R0.T_CARVE)
        while self.last < tc:
            self.last = self.last + 1 / 240 if self.last >= 0 else 0.0
            self.fill_pose(self.hctx, R0.angle_at(self.last))

    def block(self, hole_surf, alpha=1.0):
        c, w, h = self.canvas, self.L.w, self.L.h
        ctx = c.ctx
        Wp = self.W
        x0, y0 = self.cx - Wp * 0.85, self.cy - Wp * 0.85
        grd = cairo.LinearGradient(x0, y0, x0 + Wp * 1.7, y0 + Wp * 1.7)
        grd.add_color_stop_rgb(0, 0.55, 0.38, 0.24)
        grd.add_color_stop_rgb(1, 0.36, 0.23, 0.14)
        ctx.rectangle(x0, y0, Wp * 1.7, Wp * 1.7)
        ctx.set_source(grd)
        ctx.fill()
        ctx.set_source_rgba(0.25, 0.16, 0.10, 0.35)
        ctx.set_line_width(2)
        for i in range(14):
            yy = y0 + Wp * 1.7 * (i + 0.5) / 14
            ctx.move_to(x0, yy)
            ctx.curve_to(x0 + Wp * 0.6, yy + 8, x0 + Wp * 1.1, yy - 8, x0 + Wp * 1.7, yy)
        ctx.stroke()
        if hole_surf is not None and alpha > 0.01:
            ctx.save()
            ctx.scale(w / c.pw, h / c.ph)
            ctx.set_source_surface(hole_surf, 0, 0)
            ctx.paint_with_alpha(alpha)
            ctx.restore()

    def bit(self, a, alpha=1.0, outline_only=False):
        c = self.canvas
        ctx = c.ctx
        pts, cen = R0.pose(a)
        poly = [self.P(z) for z in pts]
        ctx.move_to(*poly[0])
        for q in poly[1:]:
            ctx.line_to(*q)
        ctx.close_path()
        if not outline_only:
            gb = cairo.RadialGradient(*self.P(cen), 0, *self.P(cen), self.W * 0.6)
            gb.add_color_stop_rgba(0, 0.85, 0.90, 1.0, 0.95 * alpha)
            gb.add_color_stop_rgba(1, 0.45, 0.55, 0.75, 0.95 * alpha)
            ctx.set_source(gb)
            ctx.fill_preserve()
        ctx.set_source_rgba(1, 1, 1, 0.9 * alpha)
        ctx.set_line_width(3)
        ctx.stroke()
        for v in R0.VERTS:
            z = v * complex(math.cos(a), math.sin(a)) + cen
            c.glow(*self.P(z), 8, GOLD, strength=0.6 * alpha, reach=3)
        c.circle(*self.P(cen), 7, (0.2, 0.2, 0.3), alpha=alpha)

    def square(self, alpha):
        sq = [complex(-0.5, -0.5), complex(0.5, -0.5), complex(0.5, 0.5), complex(-0.5, 0.5), complex(-0.5, -0.5)]
        self.canvas.polylines([[self.P(z) for z in sq]], GOLD, width=4, alpha=0.8 * alpha)

    def construction(self, t):
        """Steps 1–2 drawn at the centred, unrotated pose (centroid at the origin)."""
        c = self.canvas
        _, cen0 = R0.pose(0.0)
        shift = cen0 * smooth((t - T_S3) / (T_C0 - T_S3)) if t >= T_S3 else 0j   # step 3: slide into the square
        V = [v + shift for v in R0.VERTS]
        # step 1: the triangle, side by side
        u1 = min(1.0, max(0.0, (t - T_S1) / (T_S2 - T_S1 - 0.3)))
        side_fade = 1.0 - smooth((t - (T_S2 + 1.8)) / 0.6)
        segs = []
        for i in range(3):
            q = min(1.0, max(0.0, u1 * 3 - i))
            if q > 0:
                a, b = V[i], V[(i + 1) % 3]
                e = a + (b - a) * q
                segs.append((*self.P(a), *self.P(e)))
                if 0 < q < 1:
                    c.glow(*self.P(e), 9, (1, 1, 1), strength=0.8, reach=3)
        c.lines(segs, (0.95, 0.95, 1.0), width=4, alpha=0.9 * side_fade)
        for v in V:
            if t >= T_S1:
                c.circle(*self.P(v), 7, GOLD, alpha=1.0)
        # step 2: three compass arcs (pivot on corner i, from corner i+1 to corner i+2)
        arcs = []
        for i in range(3):
            t0 = T_S2 + 0.8 * i
            q = min(1.0, max(0.0, (t - t0) / 0.7))
            if q <= 0:
                continue
            piv, a, b = V[i], V[(i + 1) % 3], V[(i + 2) % 3]
            a0 = math.atan2((a - piv).imag, (a - piv).real)
            a1 = math.atan2((b - piv).imag, (b - piv).real)
            da = (a1 - a0 + math.pi) % (2 * math.pi) - math.pi
            pts = [self.P(piv + complex(math.cos(a0 + da * q * j / 40), math.sin(a0 + da * q * j / 40)))
                   for j in range(41)]
            arcs.append(pts)
            if q < 1 and t < T_S3:                               # the compass: pivot leg + pencil leg
                pen = pts[-1]
                pv = self.P(piv)
                top = ((pv[0] + pen[0]) / 2, (pv[1] + pen[1]) / 2 - self.W * 0.25)
                c.lines([(*pv, *top), (*top, *pen)], (0.85, 0.87, 0.95), width=5, alpha=0.95)
                c.circle(*top, 8, (0.85, 0.87, 0.95))
                c.glow(*pen, 9, GOLD, strength=0.9, reach=3)
        if arcs:
            fill = smooth((t - (T_S2 + 2.2)) / 0.4)
            if fill > 0:
                ctx = c.ctx
                ctx.move_to(*arcs[0][0])
                for arc in arcs:
                    for p in arc:
                        ctx.line_to(*p)
                ctx.close_path()
                ctx.set_source_rgba(0.65, 0.75, 0.95, 0.85 * fill)
                ctx.fill()
            c.polylines(arcs, GOLD, width=16, alpha=0.15)
            c.polylines(arcs, GOLD, width=4.5, alpha=0.95)

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
        if t < T_RESET:                                          # hook: the finished hole, fading to a fresh block
            fade = 1.0 - smooth((t - T_HOOK) / (T_RESET - T_HOOK))
            self.block(self.full, fade)
            self.square(fade)
            self.bit(bit_angle(min(t, T_HOOK)), alpha=fade)
        elif t < T_C0:
            self.block(None)
            if t >= T_S3:
                self.square(smooth((t - T_S3) / 0.4))
            self.construction(t)
        else:
            if t < T_C1:
                self.carve_to(t - T_C0)
                self.block(self.hole)
            else:
                self.block(self.full)
            self.square(1.0)
            self.bit(bit_angle(t))
        # text: step cards
        def card(big, small, col=GOLD, t_on=0.0):
            pop = math.exp(-max(0.0, t - t_on) / 0.15)
            c.text_centered(big, h * 0.765, size=w * 0.072 * (1 + 0.15 * pop), color=col, alpha=1.0)
            c.text_centered(small, h * 0.805, size=w * 0.042, color=(0.92, 0.92, 0.97), alpha=0.95, bold=False)

        if t < T_RESET:
            card("HOW TO DRILL", "a perfect SQUARE hole")
        elif t < T_S2:
            card("STEP 1", "draw a triangle with equal sides", t_on=T_S1)
        elif t < T_S3:
            card("STEP 2", "round each side with a compass", t_on=T_S2)
        elif t < T_C0 + 2.0:
            card("STEP 3", "spin it inside a square", t_on=T_S3)
        elif t < T_C1:
            card("DRILLING…", "it touches all 4 walls the whole time", col=(0.95, 0.95, 1.0), t_on=T_C0 + 2.0)
        else:
            card("A SQUARE HOLE", "98.8 % square (only the corners are round)", t_on=T_C1)
        if rule:
            c.caption(rule, alpha=1.0, layout=L)
        c.watermark(L)


def render(layout, sim, out_path, rule, still_frame=None):
    sc = Scene(layout, sim)
    writer = None if still_frame is not None else VideoWriter(out_path, sc.canvas, FPS)
    for f in range(sim["nf"]):
        if still_frame is not None and f != still_frame:
            t = f * DT
            if T_C0 <= t < T_C1:
                sc.carve_to(t - T_C0)
            continue
        sc.draw(f, rule)
        if writer is None:
            studio.save_still(sc.canvas, out_path)
            return f / FPS
        writer.write_frame()
    writer.close()
    return sim["nf"] / FPS


def build_events(sim, layout):
    x = layout.w / 2
    out = [{"t": 0.012 * j, "note": m, "gain": 0.24, "x": x} for j, m in enumerate((48, 55, 60, 64, 67))]
    for k, t0 in enumerate((T_S1, T_S2, T_S3)):                 # step pops
        out.append({"t": round(t0, 4), "note": 72 + 5 * k, "gain": 0.34, "x": x})
        out.append({"t": round(t0 + 0.08, 4), "note": 79 + 5 * k, "gain": 0.22, "x": x})
    for i in range(3):                                            # each arc closes
        out.append({"t": round(T_S2 + 0.8 * i + 0.7, 4), "note": (76, 79, 84)[i], "gain": 0.28, "x": x})
    t, k = T_C0, 0
    notes = [72, 76, 79, 84]
    while t < T_LOOP - 0.1:                                       # corner touches (as in reuleaux.py)
        out.append({"t": round(t + 0.004, 4), "note": notes[k % 4] - (12 if t > T_C1 else 0), "gain": 0.20,
                    "x": layout.w * (0.3 + 0.13 * (k % 4))})
        k += 1
        t += (2 * math.pi / OMEGA) / 6
    for j, m in enumerate((48, 55, 60, 64, 67, 72)):
        out.append({"t": round(T_C1 + 0.05 * j, 4), "note": m, "gain": 0.28, "x": x})
    return sorted(out, key=lambda e: e["t"])


def bed():
    """Pencil + compass scratches and a soft drill hum while carving (original)."""
    n = int(round(T_LOOP * SR))
    out = np.zeros(n + SR)
    rng = np.random.default_rng(12)

    def add(t0, sig, g):
        i0 = int(t0 * SR)
        out[i0:i0 + len(sig)] += g * sig

    def scratch(t0, dur):
        tv = np.arange(int(dur * SR)) / SR
        nz = np.diff(np.concatenate([[0], rng.standard_normal(len(tv))]))
        env = np.clip(tv / 0.05, 0, 1) * np.clip((dur - tv) / 0.08, 0, 1) * (0.6 + 0.4 * np.sin(2 * np.pi * 9 * tv))
        add(t0, nz * env, 0.035)

    scratch(T_S1, T_S2 - T_S1 - 0.3)
    for i in range(3):
        scratch(T_S2 + 0.8 * i, 0.7)
    tv = np.arange(int((T_LOOP - T_C0) * SR)) / SR             # drill hum: pitch follows the spin speed
    speed = np.array([min(1.0, 0.35 + 0.65 * min(x, R0.T_RAMP) / R0.T_RAMP) for x in tv[::480]])
    speed = np.interp(tv, tv[::480], speed)
    f = 95 * speed
    ph = 2 * np.pi * np.cumsum(f) / SR
    hum = sum(np.sin(k * ph) / k for k in range(1, 7))
    env = np.clip(tv / 0.3, 0, 1) * np.clip((T_LOOP - T_C0 - tv) / 0.6, 0.15, 1)
    add(T_C0, hum * env, 0.045)
    tail = out[n:]
    out = out[:n]
    out[: len(tail)] += tail
    return out.astype(np.float32)


def _worker(o, sim, label, rule):
    layout = get_layout(o)
    name = f"{SCENE}_{label}_{layout.tag}"
    video = studio.OUT_DIR / f"{name}_silent.mp4"
    d = render(layout, sim, video, rule)
    pad = kit.loop_pad(T_LOOP, ((48, 1.0), (55, 0.7), (60, 0.45), (64, 0.3)), gain=0.010)
    kit.deliver_loop(SCENE, name, layout, video, build_events(sim, layout), d, voice="glassharp",
                     bed=bed() + pad[: int(round(T_LOOP * SR))], peak_db=-6.0)


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
