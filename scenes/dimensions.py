"""DIMENSIONS — "turn it and it becomes the next one down": sphere -> circle -> line -> dot -> (zoom in) sphere.

A spinning wireframe sphere; seen from anywhere its outline is a circle, so its grid and shading fade and the circle is
left (3D -> 2D). The circle tilts until it is edge-on: a line (2D -> 1D). The line turns until it points at you: a dot
(1D -> 0D). Then the camera dives into the dot, and the dot is a tiny sphere: frame 0 again (a perfect loop).
Each swap happens at the exact moment the two shapes project to the same picture, so nothing jumps.
Look: neon on black, perspective depth (near parts thicker / brighter), colour per dimension.
Audio (original): a glass-harp chord on each new dimension (falling 3D -> 0D), gliding arpeggios on the turns,
a rising run on the dive back in, a periodic loop pad.
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

SCENE = "dimensions"
T_LOOP = 16.0
OMEGA = 2 * math.pi / T_LOOP                   # one spin per loop: the sphere is identical at the seam
TILT = 0.42                                    # spin axis tilted toward the viewer
DCAM = 3.2                                     # camera distance in sphere radii
# phases
T_FLAT0, T_FLAT1 = 3.2, 4.5                    # sphere grid + shading fade -> circle
T_TIP0, T_TIP1 = 5.1, 7.7                      # circle tilts edge-on -> line
T_TURN0, T_TURN1 = 8.3, 10.8                   # line turns end-on -> dot
T_DIVE0, T_DIVE1 = 11.9, 15.7                  # dive into the dot -> sphere
COL = {3: (0.35, 0.85, 1.0), 2: (0.72, 0.52, 1.0), 1: (1.0, 0.42, 0.78), 0: (1.0, 0.82, 0.40)}
NAME = {3: "SPHERE", 2: "CIRCLE", 1: "LINE", 0: "DOT"}
GOLD = (1.0, 0.82, 0.40)


def seg(t, a, b):
    return min(1.0, max(0.0, (t - a) / (b - a)))


def mix(a, b, u):
    return tuple(a[i] + (b[i] - a[i]) * u for i in range(3))


def state(t):
    """-> dict: which object, its transform params, colour, label dimension."""
    if t < T_FLAT1:
        f = smooth(seg(t, T_FLAT0, T_FLAT1))
        return dict(obj="sphere", flat=f, scale=1.0, col=mix(COL[3], COL[2], f), dim=3 if f < 0.6 else 2)
    if t < T_TIP1:
        a = smooth(seg(t, T_TIP0, T_TIP1)) * math.pi / 2
        u = seg(t, T_TIP0, T_TIP1)
        return dict(obj="circle", alpha=a, col=mix(COL[2], COL[1], smooth(seg(u, 0.6, 1.0))),
                    dim=2 if u < 0.85 else 1)
    if t < T_DIVE0:
        b = smooth(seg(t, T_TURN0, T_TURN1)) * math.pi / 2
        u = seg(t, T_TURN0, T_TURN1)
        return dict(obj="line", beta=b, col=mix(COL[1], COL[0], smooth(seg(u, 0.6, 1.0))), dim=1 if u < 0.9 else 0)
    u = seg(t, T_DIVE0, T_DIVE1)
    return dict(obj="dive", u=u, col=mix(COL[0], COL[3], smooth(seg(u, 0.35, 0.9))), dim=0 if u < 0.7 else 3)


class Scene:
    def __init__(self, layout):
        self.L = layout
        self.canvas = Canvas(layout.w, layout.h, studio.render_scale())
        rng = np.random.default_rng(3)
        self.dust = rng.random((140, 3))

    def proj(self, x, y, z, R):
        """sphere-radius units -> screen. Perspective: k = D / (D + z)."""
        k = DCAM / (DCAM + z)
        return self.cx + x * R * k, self.cy - y * R * k, k

    def bg(self, t):
        c, w, h = self.canvas, self.L.w, self.L.h
        ctx = c.ctx
        g = cairo.RadialGradient(w / 2, h * 0.42, 0, w / 2, h * 0.42, h * 0.75)
        g.add_color_stop_rgb(0, 0.07, 0.06, 0.14)
        g.add_color_stop_rgb(1, 0.005, 0.005, 0.015)
        ctx.set_source(g)
        ctx.paint()
        for i, (x, y, s) in enumerate(self.dust):              # slow drifting dust for depth
            yy = (y * h + h * (t / T_LOOP) * (1 + int(s * 2.0))) % h      # whole screens per loop: seamless
            tw = 0.5 + 0.5 * math.sin(2 * math.pi * (t / T_LOOP) * (1 + i % 3) + i)
            c.circle(x * w, yy, (0.8 + 1.6 * s) * w / 1080, (0.75, 0.8, 1.0), alpha=0.12 + 0.25 * s * tw)

    # ------------------------------------------------------------- objects
    def sphere(self, t, R, grid_a, shade_a, col, rim_w):
        c = self.canvas
        ctx = c.ctx
        rs = R * DCAM / math.sqrt(DCAM ** 2 - 1)               # silhouette radius under perspective
        cx, cy = self.cx, self.cy
        c.glow(cx, cy, rs * 1.05, col, strength=0.30, reach=1.5)
        if shade_a > 0:
            g = cairo.RadialGradient(cx - rs * 0.35, cy - rs * 0.4, rs * 0.05, cx, cy, rs)
            g.add_color_stop_rgba(0, *mix(col, (1, 1, 1), 0.55), 0.55 * shade_a)
            g.add_color_stop_rgba(0.55, *col, 0.22 * shade_a)
            g.add_color_stop_rgba(1, *mix(col, (0, 0, 0), 0.6), 0.35 * shade_a)
            ctx.new_path()
            ctx.arc(cx, cy, rs, 0, 2 * math.pi)
            ctx.set_source(g)
            ctx.fill()
        if grid_a > 0.01:
            phi = OMEGA * t
            ct, st = math.cos(TILT), math.sin(TILT)
            lines = []
            for j in range(1, 8):                               # parallels
                lat = -math.pi / 2 + j * math.pi / 8
                lines.append([(math.cos(lat) * math.cos(a), math.sin(lat), math.cos(lat) * math.sin(a))
                              for a in np.linspace(0, 2 * math.pi, 73)])
            for m in range(12):                                 # meridians (spinning)
                lon = phi + m * 2 * math.pi / 12
                lines.append([(math.cos(la) * math.cos(lon), math.sin(la), math.cos(la) * math.sin(lon))
                              for la in np.linspace(-math.pi / 2, math.pi / 2, 37)])
            ctx.set_line_cap(cairo.LINE_CAP_ROUND)
            for pts in lines:
                prev = None
                for (x, y, z) in pts:
                    y2, z2 = y * ct - z * st, y * st + z * ct   # tilt the spin axis toward us
                    p = self.proj(x, y2, z2, R) + (z2,)
                    if prev is not None:
                        zm = (prev[3] + p[3]) / 2
                        front = 0.5 - 0.5 * zm                  # 1 near, 0 far
                        ctx.move_to(prev[0], prev[1])
                        ctx.line_to(p[0], p[1])
                        ctx.set_source_rgba(*mix(col, (1, 1, 1), 0.25 * front), grid_a * (0.18 + 0.75 * front))
                        ctx.set_line_width(self.lw * (0.6 + 1.0 * front))
                        ctx.stroke()
                    prev = p
        ctx.new_path()
        ctx.arc(cx, cy, rs, 0, 2 * math.pi)
        ctx.set_source_rgba(*col, 0.95)
        ctx.set_line_width(rim_w)
        ctx.stroke()

    def circle_obj(self, alpha, col, R):
        """the circle (radius = the sphere's silhouette) tilted by alpha about the x axis (top goes away)."""
        c = self.canvas
        ctx = c.ctx
        r = DCAM / math.sqrt(DCAM ** 2 - 1)
        ca, sa = math.cos(alpha), math.sin(alpha)
        pts = []
        for th in np.linspace(0, 2 * math.pi, 181):
            x, y = r * math.cos(th), r * math.sin(th)
            pts.append(self.proj(x, y * ca, y * sa, R) + (y * sa,))
        # a faint fill so the plane reads while it tips
        ctx.new_path()
        for i, p in enumerate(pts):
            (ctx.move_to if i == 0 else ctx.line_to)(p[0], p[1])
        ctx.close_path()
        ctx.set_source_rgba(*col, 0.10 * (1 - alpha / (math.pi / 2)) + 0.02)
        ctx.fill()
        c.glow(self.cx, self.cy, R * (0.95 - 0.5 * alpha / (math.pi / 2)), col, strength=0.25, reach=1.5)
        for a_, b_ in zip(pts, pts[1:]):
            front = 0.5 - 0.5 * (a_[3] + b_[3]) / 2 / r
            ctx.move_to(a_[0], a_[1])
            ctx.line_to(b_[0], b_[1])
            ctx.set_source_rgba(*mix(col, (1, 1, 1), 0.3 * front), 0.55 + 0.45 * front)
            ctx.set_line_width(self.rim * (0.55 + 0.9 * front))
            ctx.stroke()

    def line_obj(self, beta, col, R):
        """the diameter, turned by beta about the vertical axis (right end comes toward us)."""
        c = self.canvas
        ctx = c.ctx
        r = DCAM / math.sqrt(DCAM ** 2 - 1)
        cb, sb = math.cos(beta), math.sin(beta)
        n = 120
        pts = [self.proj(x * cb, 0.0, -x * sb, R) + (-x * sb,) for x in np.linspace(-r, r, n + 1)]
        tip = beta / (math.pi / 2)
        c.glow(self.cx, self.cy, R * (0.9 - 0.75 * tip) + R * 0.08, col, strength=0.3 + 0.3 * tip, reach=1.6)
        for a_, b_ in zip(pts, pts[1:]):
            front = 0.5 - 0.5 * (a_[3] + b_[3]) / 2 / r
            ctx.move_to(a_[0], a_[1])
            ctx.line_to(b_[0], b_[1])
            ctx.set_source_rgba(*mix(col, (1, 1, 1), 0.3 * front), 0.6 + 0.4 * front)
            ctx.set_line_width(self.rim * (0.6 + 1.6 * front) * (a_[2] + b_[2]) / 2)
            ctx.stroke()
        if tip > 0.8:                                          # the dot: the near end facing us
            k = (tip - 0.8) / 0.2
            c.circle(self.cx, self.cy, self.dot_r * k, mix(col, (1, 1, 1), 0.35), alpha=k)

    # ------------------------------------------------------------- frame
    def draw(self, f, rule):
        L, c = self.L, self.canvas
        w, h = L.w, L.h
        t = f * DT
        self.cx, self.cy = w / 2, h * 0.43
        R = w * 0.34
        self.lw = max(1.2, w * 0.0026)
        self.rim = w * 0.008
        self.dot_r = w * 0.022
        self.bg(t)
        s = state(t)
        col = s["col"]
        if s["obj"] == "sphere":
            fl = s["flat"]
            self.sphere(t, R, 1 - fl, 1 - fl, col, self.rim * (0.7 + 0.3 * fl))
        elif s["obj"] == "circle":
            self.circle_obj(s["alpha"], col, R)
        elif s["obj"] == "line":
            self.line_obj(s["beta"], col, R)
        else:
            u = s["u"]
            pulse = 1 + 0.12 * math.sin(2 * math.pi * 1.5 * (t - T_TURN1)) * (1 - seg(u, 0.0, 0.15))
            rs = R * DCAM / math.sqrt(DCAM ** 2 - 1)
            k = smooth(u) ** 1.6
            rad = self.dot_r * pulse * (rs / self.dot_r) ** k        # exponential dive
            Rk = rad * math.sqrt(DCAM ** 2 - 1) / DCAM
            reveal = smooth(seg(u, 0.12, 0.85))
            rim_w = max(1.5, self.rim * 0.7 * min(1.0, rad / (rs * 0.3)) + self.rim * 0.3 * (1 - reveal))
            self.sphere(t, Rk, reveal, max(reveal, 1 - seg(u, 0, 0.1)), col, rim_w)
        # the label: big dimension + name, pop on change
        dim = s["dim"]
        t_ch = {3: 0.0, 2: T_FLAT0 + 0.6 * (T_FLAT1 - T_FLAT0), 1: T_TIP0 + 0.85 * (T_TIP1 - T_TIP0),
                0: T_TURN0 + 0.9 * (T_TURN1 - T_TURN0)}[dim]
        if s["obj"] == "dive" and dim == 3:
            t_ch = T_DIVE0 + 0.7 * (T_DIVE1 - T_DIVE0)
        pop = 1 + 0.25 * math.exp(-max(0.0, t - t_ch) / 0.12) if t >= t_ch and not (dim == 3 and t < 1.0) else 1.0
        lc = COL[dim]
        c.glow(w / 2, h * 0.675, w * 0.16, lc, strength=0.18, reach=1.6)
        c.text_centered(f"{dim}D", h * 0.705, size=w * 0.16 * pop, color=lc)
        c.text_centered(NAME[dim], h * 0.748, size=w * 0.05, color=(0.85, 0.88, 1.0), bold=False)
        # the ladder 3D 2D 1D 0D
        for i, d in enumerate((3, 2, 1, 0)):
            x = w * (0.32 + 0.12 * i)
            on = d == dim
            c.circle(x, h * 0.778, w * (0.012 if on else 0.007), COL[d], alpha=1.0 if on else 0.35)
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
    ev, P = [], audio.PENTA_MAJOR
    w = layout.w

    def penta(i):
        return 60 + 12 * (i // 5) + P[i % 5]

    # a chord on each new dimension, falling: 3D (t=0, rings across the seam) 2D 1D 0D
    for t, root, ch in ((0.0, 48, (60, 64, 67, 72)), (T_FLAT1 - 0.4, 45, (57, 60, 64, 69)),
                        (T_TIP1 - 0.2, 41, (53, 57, 60, 65)), (T_TURN1 - 0.15, 43, (55, 59, 62, 67))):
        ev.append({"t": round(t, 4), "note": root, "gain": 0.5, "x": w * 0.5})
        for i, n in enumerate(ch):
            ev.append({"t": round(t + 0.035 * i, 4), "note": n, "gain": 0.42 - 0.04 * i, "x": w * (0.35 + 0.1 * i)})
        ev.append({"t": round(t, 4), "note": 36, "note_gain": 0.0, "pok": 0.6, "pok_gain": 0.45, "gain": 0.5, "x": w / 2})
    # the sphere spinning: soft pings
    for q in range(4):
        ev.append({"t": round(0.8 + q * 0.6, 4), "note": penta(7 + q), "gain": 0.26, "x": w * (0.35 + 0.1 * q)})
    # the turns: gliding falling arpeggios
    for a, b, top in ((T_TIP0, T_TIP1, 12), (T_TURN0, T_TURN1, 9)):
        for q in range(6):
            ev.append({"t": round(a + (b - a) * q / 6, 4), "note": penta(top - q), "gain": 0.28,
                       "x": w * (0.7 - 0.07 * q)})
    # the dot waits: two soft heartbeats
    for q in range(2):
        ev.append({"t": round(T_TURN1 + 0.55 + 0.6 * q, 4), "note": 72, "gain": 0.22, "x": w * 0.5})
    # the dive: a rising run, faster and faster, landing on the 3D chord at the seam
    n = 14
    for q in range(n):
        u = (q / n) ** 0.7
        ev.append({"t": round(T_DIVE0 + (T_DIVE1 - T_DIVE0) * u, 4), "note": penta(2 + q), "gain": 0.22 + 0.012 * q,
                   "x": w * (0.3 + 0.4 * q / n)})
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
    pad = kit.loop_pad(d, ((45, 1.0), (52, 0.6), (57, 0.4), (64, 0.25)), gain=0.03)
    kit.deliver_loop(SCENE, name, layout, video, build_events(layout), d, voice="glassharp", bed=pad)


if __name__ == "__main__":
    main()
