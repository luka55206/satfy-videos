"""PARADOX: GABRIEL'S HORN — y = 1/x (x ≥ 1) spun around its axis: you can FILL it with paint, but never PAINT it.

The horn stands like a funnel (mouth on top, endless tube downward), a neon wireframe spinning slowly. Paint flows
down to depth X, which grows exponentially. Two counters:
  VOLUME   V(X) = π(1 − 1/X)                          → π   (digits turn gold as they lock, like the fib winner)
  SURFACE  A(X) = 2π ∫₁^X (1/x)·√(1 + 1/x⁴) dx  ≥ 2π ln X → ∞   (keeps climbing, red)
Verdict, then the paint drains back up to frame 0 (loop). All numbers computed here.
Audio (original): a soft flowing pad + a glass-harp chime per locked digit of π, a low rising tone under the surface
counter, a chord on the verdict, falling notes on the drain.
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

SCENE = "paradox_horn"
T_LOOP = 18.0
T_FILL0, T_FILL1 = 1.5, 11.0
T_VERD = 11.4
T_DRAIN0, T_DRAIN1 = 15.6, 17.4
LOGX_MAX = 12.0                                  # X goes to 10^12
CYAN, GOLD, RED, WHITE = (0.35, 0.85, 1.0), (1.0, 0.80, 0.35), (1.0, 0.40, 0.42), (0.95, 0.96, 1.0)
PI_STR = f"{math.pi:.10f}"
X_VIS = 8.0                                      # the drawn part of the horn: 1 <= x <= 8


def _surface_table():
    """A(X) on a log grid (numeric integral in u = ln x)."""
    u = np.linspace(0.0, LOGX_MAX * math.log(10), 20001)
    integrand = np.sqrt(1 + np.exp(-4 * u))                      # (1/x)·√(1+x⁻⁴) dx = √(1+e^(−4u)) du
    cum = np.concatenate([[0.0], np.cumsum((integrand[1:] + integrand[:-1]) / 2 * np.diff(u))])
    return u, 2 * math.pi * cum


U_TAB, A_TAB = _surface_table()


def logx_at(t):
    if t < T_FILL0:
        return 0.0
    if t < T_FILL1:
        return LOGX_MAX * ((t - T_FILL0) / (T_FILL1 - T_FILL0)) ** 1.6
    if t < T_DRAIN0:
        return LOGX_MAX
    return LOGX_MAX * (1 - smooth(min(1.0, (t - T_DRAIN0) / (T_DRAIN1 - T_DRAIN0))))


def volume(lx):
    return math.pi * (1 - 10 ** (-lx))


def surface(lx):
    return float(np.interp(lx * math.log(10), U_TAB, A_TAB))


def pi_match(v):
    s = f"{v:.10f}"
    m = 0
    while m < len(s) and s[m] == PI_STR[m]:
        m += 1
    return s, m


LOCKS = {}
_prev = 0
for _f in range(int(T_FILL1 * FPS) + 2):
    _s, _m = pi_match(volume(logx_at(_f * DT)))
    for _c in range(_prev, _m):
        LOCKS[_c] = _f * DT
    _prev = max(_prev, _m)


class Scene:
    def __init__(self, layout):
        self.L = layout
        self.canvas = Canvas(layout.w, layout.h, studio.render_scale())
        w, h = layout.w, layout.h
        self.cx, self.top, self.bot = w * 0.5, h * 0.25, h * 0.635
        self.S = w * 0.36                               # radius 1 in px
        self.tilt = 0.32                                # ellipse squash of the rings (view from slightly above)

    def ay(self, x):
        """axis position (x = 1 .. X_VIS) -> screen y (log-ish so the tube stays long)."""
        return self.top + (self.bot - self.top) * (x - 1) / (X_VIS - 1)

    def ring_pts(self, x, phi=0.0, n=72):
        r = self.S / x
        return [(self.cx + r * math.cos(a + phi), self.ay(x) + r * self.tilt * math.sin(a + phi), math.sin(a + phi))
                for a in np.linspace(0, 2 * math.pi, n + 1)]

    def draw(self, f, rule):
        L, c = self.L, self.canvas
        w, h = L.w, L.h
        t = f * DT
        ctx = c.ctx
        g = cairo.RadialGradient(w / 2, h * 0.45, 0, w / 2, h * 0.45, h * 0.75)
        g.add_color_stop_rgb(0, 0.06, 0.05, 0.12)
        g.add_color_stop_rgb(1, 0.005, 0.005, 0.015)
        ctx.set_source(g)
        ctx.paint()
        lx = logx_at(t)
        X = 10 ** lx
        spin = 2 * math.pi * t / T_LOOP
        xs = np.linspace(1, X_VIS, 120)
        # the paint inside: everything from the mouth down to depth X (gold, glowing)
        xp = min(X, X_VIS)
        if xp > 1.001:
            px = np.linspace(1, xp, 80)
            ctx.new_path()
            ctx.move_to(self.cx - self.S, self.ay(1))
            for x in px:
                ctx.line_to(self.cx - self.S / x, self.ay(x))
            for x in px[::-1]:
                ctx.line_to(self.cx + self.S / x, self.ay(x))
            ctx.close_path()
            gr = cairo.LinearGradient(self.cx - self.S, 0, self.cx + self.S, 0)
            gr.add_color_stop_rgba(0, 0.75, 0.45, 0.10, 0.85)
            gr.add_color_stop_rgba(0.45, 1.0, 0.85, 0.40, 0.95)
            gr.add_color_stop_rgba(1, 0.70, 0.40, 0.08, 0.85)
            ctx.set_source(gr)
            ctx.fill()
            # the surface of the paint in the mouth (an ellipse), and the paint's leading front
            c.glow(self.cx, self.ay(xp), self.S / xp * 1.2, GOLD, strength=0.5, reach=1.8)
        # the paint going on past the drawn part: a glowing stream off the bottom
        if X > X_VIS:
            a = min(1.0, (lx - math.log10(X_VIS)) / 0.4)
            c.lines([(self.cx, self.ay(X_VIS), self.cx, h * 0.685)], GOLD, width=self.S / X_VIS * 1.6, alpha=0.8 * a)
            c.text_centered("the horn never ends  ↓", h * 0.665, size=w * 0.036, color=(0.8, 0.82, 0.95), alpha=a, cx=w * 0.76)
        # wireframe: rings (back halves dim) + spinning meridians
        for x in [1, 1.15, 1.35, 1.6, 1.9, 2.3, 2.8, 3.4, 4.2, 5.2, 6.4, 8.0]:
            pts = self.ring_pts(x)
            for (x0, y0, z0), (x1, y1, z1) in zip(pts, pts[1:]):
                front = 0.5 + 0.5 * (z0 + z1) / 2
                c.lines([(x0, y0, x1, y1)], CYAN, width=2.2 if front > 0.5 else 1.2, alpha=0.25 + 0.6 * front)
        for k in range(10):
            th = spin + k * 2 * math.pi / 10
            pts = [(self.cx + self.S / x * math.cos(th), self.ay(x) + self.S / x * self.tilt * math.sin(th)) for x in xs]
            front = 0.5 + 0.5 * math.sin(th)
            c.polylines([pts], CYAN, width=2.0 if front > 0.5 else 1.0, alpha=0.18 + 0.5 * front)
        sil_l = [(self.cx - self.S / x, self.ay(x)) for x in xs]
        sil_r = [(self.cx + self.S / x, self.ay(x)) for x in xs]
        c.polylines([sil_l, sil_r], CYAN, width=10, alpha=0.12)
        c.polylines([sil_l, sil_r], CYAN, width=3.2, alpha=0.95)
        c.text_centered("y = 1/x, spun around", self.top - h * 0.035, size=w * 0.04, color=(0.75, 0.88, 1.0),
                        bold=False)
        # the counters
        verdict = T_VERD <= t < T_DRAIN0 + 0.4
        y1, y2 = h * 0.765, h * 0.805
        vs, m = pi_match(volume(lx))
        self.digits("PAINT TO FILL IT:  ", vs, m, y1, w * 0.052, t)
        A = surface(lx)
        rise = 1 + 0.1 * math.sin(t * 8) if T_FILL0 <= t < T_FILL1 else 1.0
        c.text_centered(f"PAINT TO COVER ITS INSIDE:  {A:,.1f}", y2, size=w * 0.046 * rise, color=RED, max_w=w * 0.94)
        if T_FILL0 <= t < T_DRAIN0:
            c.text_centered(f"depth x = 10{self.sup(int(lx))}" if lx >= 1 else "depth x = 1", h * 0.72,
                            size=w * 0.036, color=(0.75, 0.78, 0.9), bold=False)
        if verdict:
            k = smooth(min(1.0, (t - T_VERD) / 0.4))
            c.glow(w / 2, h * 0.50, w * 0.42, (0.02, 0.02, 0.05), strength=0.0, reach=1.0)
            ctx.rectangle(w * 0.06, h * 0.40, w * 0.88, h * 0.20)
            ctx.set_source_rgba(0.03, 0.03, 0.07, 0.86 * k)
            ctx.fill()
            c.text_centered("FILL it:  π  (easy)", h * 0.465, size=w * 0.075, color=GOLD, alpha=k)
            c.text_centered("PAINT it:  ∞  (never)", h * 0.555, size=w * 0.075, color=RED, alpha=k)
        if rule:
            c.caption(rule, alpha=1.0, layout=L)
        c.watermark(L)

    @staticmethod
    def sup(n):
        return "".join("⁰¹²³⁴⁵⁶⁷⁸⁹"[int(d)] for d in str(n))

    def digits(self, head, s, m, y, size, t):
        """'PAINT TO FILL IT: 3.1415926535' — digits that match π are gold and pop as they lock."""
        c = self.canvas
        ctx = c.ctx
        c._font(size, True)
        wh, ws = ctx.text_extents(head).x_advance, ctx.text_extents(s).x_advance
        sc = min(1.0, self.L.w * 0.94 / (wh + ws))
        size *= sc
        c._font(size, True)
        wh, ws = ctx.text_extents(head).x_advance, ctx.text_extents(s).x_advance
        x = self.L.w / 2 - (wh + ws) / 2
        ctx.set_source_rgba(0.85, 0.87, 0.95, 1)
        ctx.move_to(x, y)
        ctx.show_text(head)
        x += wh
        for i, ch in enumerate(s):
            c._font(size, True)
            adv = ctx.text_extents(ch).x_advance
            tl = LOCKS.get(i)
            gold = i < m
            pop = math.exp(-(t - tl) / 0.12) if (gold and tl is not None and tl <= t < T_FILL1 + 0.3) else 0.0
            if pop > 0.05:
                c.glow(x + adv / 2, y - size * 0.35, size * 0.35, GOLD, strength=0.5 * pop, reach=2.4)
            c._font(size * (1 + 0.5 * pop), True)
            ctx.set_source_rgba(*(GOLD if gold else WHITE), 1)
            ctx.move_to(x + adv / 2 - ctx.text_extents(ch).x_advance / 2, y)
            ctx.show_text(ch)
            x += adv


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
    for i, (cpos, t) in enumerate(sorted(LOCKS.items(), key=lambda kv: kv[1])):
        if cpos >= 2:
            ev.append({"t": round(t, 4), "note": 72 + [0, 2, 4, 7, 9, 12, 14, 16, 19, 21, 24][min(10, i)], "gain": 0.3,
                       "x": w * 0.5})
    for j in range(16):                                        # the surface counter: low steps that never resolve
        ev.append({"t": round(T_FILL0 + j * (T_FILL1 - T_FILL0) / 16, 4), "note": 41 + (j % 4) * 2, "gain": 0.22,
                   "x": w * 0.4})
    for j, n in enumerate((48, 55, 60, 64, 67)):
        ev.append({"t": round(T_VERD + 0.05 * j, 4), "note": n, "gain": 0.42, "x": w / 2})
    ev.append({"t": round(T_VERD + 0.9, 4), "note": 46, "gain": 0.35, "x": w / 2})
    ev.append({"t": round(T_VERD + 0.92, 4), "note": 58, "gain": 0.3, "x": w / 2})
    for j, n in enumerate((79, 76, 72, 67, 64)):
        ev.append({"t": round(T_DRAIN0 + 0.3 * j, 4), "note": n, "gain": 0.22, "x": w / 2})
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
