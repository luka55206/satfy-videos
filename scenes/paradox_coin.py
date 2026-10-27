"""PARADOX: THE COIN ROTATION — roll a coin once around an equal coin: it turns TWICE, not once.

turns = 1 + R/r (rolling outside a circle of radius R). Shots: equal coins, a full trip, the counter lands on 2 (hit) ->
the fixed coin grows to 3× (camera pulls out): 4 turns -> the reveal: the big coin's edge unrolls into a straight
track and the coin rolls along it: only 3 turns; the extra 1 comes from going AROUND -> back to equal coins (loop).
Real-looking coins: metallic gradient, a ridged rim, an embossed π that shows which way is up; ghost copies mark
every quarter turn of travel.
Audio (original, lib/sfx): a metallic tick on every quarter turn, a hit + chime on each whole-number landing,
whooshes on the camera moves, a pad + pulse.
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

SCENE = "paradox_coin"
T_LOOP = 16.0
GOLD, WHITE, RED, SILVER = (1.0, 0.82, 0.35), (0.96, 0.97, 1.0), (1.0, 0.38, 0.38), (0.78, 0.82, 0.90)
A0, A1 = 0.3, 4.3            # equal coins: one trip
G0, G1 = 4.9, 5.9            # the fixed coin grows to 3×
B0, B1 = 6.0, 10.0           # around the big coin
U0, U1, U2 = 10.4, 11.2, 13.4   # unroll, roll along the track
K0, K1 = 13.8, 15.2          # back to equal coins


def seg(t, a, b):
    return min(1.0, max(0.0, (t - a) / (b - a)))


def state(t):
    """-> dict(R, scale, mode, a (angle travelled), x (track distance), turns)."""
    if t < G0:
        a = 2 * math.pi * smooth(seg(t, A0, A1))
        return dict(R=1.0, S=1.0, mode="around", a=a, turns=a / (2 * math.pi) * 2)
    if t < B0:
        u = smooth(seg(t, G0, G1))
        return dict(R=1 + 2 * u, S=1 - 0.62 * u, mode="around", a=0.0, turns=2.0 if t < G0 + 0.4 else 0.0)
    if t < U0:
        a = 2 * math.pi * smooth(seg(t, B0, B1))
        return dict(R=3.0, S=0.38, mode="around", a=a, turns=a / (2 * math.pi) * 4)
    if t < K0:
        x = 2 * math.pi * 3 * smooth(seg(t, U1, U2))
        return dict(R=3.0, S=0.38, mode="track", a=0.0, x=x, un=smooth(seg(t, U0, U1)), turns=x / (2 * math.pi))
    u = smooth(seg(t, K0, K1))
    return dict(R=3 - 2 * u, S=0.38 + 0.62 * u, mode="around", a=0.0, turns=0.0)


class Scene:
    def __init__(self, layout):
        self.L = layout
        self.canvas = Canvas(layout.w, layout.h, studio.render_scale())

    def coin(self, x, y, r, ang, col=GOLD, face="π", alpha=1.0, ghost=False):
        """ang = rotation (radians, counter-clockwise on screen)."""
        c = self.canvas
        ctx = c.ctx
        if ghost:
            c.ring(x, y, r, col, width=2, alpha=0.25 * alpha)
            ex, ey = x + r * 0.7 * math.sin(ang), y - r * 0.7 * math.cos(ang)
            c.lines([(x, y, ex, ey)], RED, width=3, alpha=0.35 * alpha)
            return
        ctx.save()
        ctx.translate(x, y)
        g = cairo.RadialGradient(-r * 0.35, -r * 0.4, r * 0.05, 0, 0, r)
        g.add_color_stop_rgba(0, min(1, col[0] + 0.25), min(1, col[1] + 0.25), min(1, col[2] + 0.3), alpha)
        g.add_color_stop_rgba(0.7, *col, alpha)
        g.add_color_stop_rgba(1, col[0] * 0.55, col[1] * 0.5, col[2] * 0.4, alpha)
        ctx.new_path()
        ctx.arc(0, 0, r, 0, 2 * math.pi)
        ctx.set_source(g)
        ctx.fill()
        ctx.rotate(-ang)
        for k in range(72):                                      # ridged rim
            a = k / 72 * 2 * math.pi
            c.lines([(math.cos(a) * r * 0.9, math.sin(a) * r * 0.9, math.cos(a) * r * 0.99, math.sin(a) * r * 0.99)],
                    (col[0] * 0.5, col[1] * 0.45, col[2] * 0.35), width=max(1.0, r * 0.02), alpha=0.8 * alpha)
        c.ring(0, 0, r * 0.84, (col[0] * 0.6, col[1] * 0.55, col[2] * 0.4), width=max(1.0, r * 0.03), alpha=alpha)
        c.text_centered(face, r * 0.22 + 2, size=r * 0.95, color=(col[0] * 0.45, col[1] * 0.38, col[2] * 0.25),
                        alpha=alpha, cx=1.5)                          # embossed: shadow + light
        c.text_centered(face, r * 0.22, size=r * 0.95, color=(min(1, col[0] + 0.1), min(1, col[1] + 0.1), col[2]),
                        alpha=alpha, cx=0)
        c.lines([(0, -r * 0.62, 0, -r * 0.98)], RED, width=max(2.0, r * 0.06), alpha=alpha)   # "up" mark
        ctx.restore()

    def draw(self, f, rule):
        L, c = self.L, self.canvas
        w, h = L.w, L.h
        t = f * DT
        ctx = c.ctx
        g = cairo.RadialGradient(w / 2, h * 0.45, 0, w / 2, h * 0.45, h * 0.7)
        g.add_color_stop_rgb(0, 0.08, 0.07, 0.12)
        g.add_color_stop_rgb(1, 0.01, 0.01, 0.02)
        ctx.set_source(g)
        ctx.paint()
        s = state(t)
        unit = w * 0.13 * s["S"]                                   # px per small-coin radius
        cx, cy = w * 0.5, h * 0.47
        r = unit
        R = s["R"] * unit
        turns = s["turns"]
        if s["mode"] == "around":
            self.coin(cx, cy, R, 0.0, SILVER, face="")
            a = s["a"]
            k_ = s["R"]                                            # turns per trip = 1 + R/r
            nghost = int(a / (math.pi / 2))
            for gk in range(1, nghost + 1):                        # a ghost every quarter of the trip
                ag = gk * math.pi / 2
                gx, gy = cx + (R + r) * math.sin(ag), cy - (R + r) * math.cos(ag)
                self.coin(gx, gy, r, -ag * (1 + k_), ghost=True)
            px, py = cx + (R + r) * math.sin(a), cy - (R + r) * math.cos(a)
            self.coin(px, py, r, -a * (1 + k_))
        else:                                                      # the unrolled track
            un = s["un"]
            circ = 2 * math.pi * R
            ty = h * 0.60
            x0 = cx - circ / 2
            if un < 1:                                             # the big coin's edge peels off into a line
                self.coin(cx, ty - R, R, 0.0, SILVER, face="", alpha=1 - un)
            c.lines([(x0 + circ / 2 - circ / 2 * un, ty, x0 + circ / 2 + circ / 2 * un, ty)], SILVER, width=6)
            for k in range(4):
                xx = x0 + circ * k / 3
                c.lines([(xx, ty - 8, xx, ty + 8)], WHITE, width=2, alpha=un)
            x = s["x"]
            self.coin(x0 + x * unit, ty - r, r, -x)
            c.text_centered("= the big coin's edge, unrolled", ty + h * 0.04, size=w * 0.04, color=SILVER, alpha=un)
        # the counter
        n_int = int(turns + 1e-6)
        last_int_t = None
        if turns < 0.02:
            big = "0 turns"
        elif abs(turns - round(turns)) > 0.02:
            big = f"{turns:.1f} turns"
        else:
            big = f"{round(turns)} turn" + ("" if round(turns) == 1 else "s")
        for tl, val in ((A1, 2), (B1, 4), (U2, 3)):
            if tl <= t < tl + 0.6 and abs(turns - val) < 0.01:
                last_int_t = tl
        pop = 1 + 0.35 * math.exp(-(t - last_int_t) / 0.12) if last_int_t is not None else 1.0
        col = GOLD if (last_int_t is not None or (turns > 0.5 and abs(turns - round(turns)) < 0.02)) else WHITE
        if t >= K0 or (G0 + 0.4 <= t < B0):
            big = "0 turns" if t >= K0 else "now around a 3× bigger coin"
        c.text_centered(big, h * 0.235, size=w * (0.12 if "turn" in big else 0.06) * pop, color=col, max_w=w * 0.94)
        line = None
        if t < A0 + 0.5 or t >= K1 + 0.2:
            line = "Roll it once around…"
        elif t < G0 + 0.4:
            line = "1 trip around = 2 FULL turns?!" if t >= A1 - 0.2 else "…how many times does it turn?"
        elif B0 <= t < U0:
            line = "1 trip around = 4 turns" if t >= B1 - 0.2 else "3× bigger coin…"
        elif U0 <= t < K0:
            line = "flat: 3 turns. Going AROUND adds +1" if t >= U2 - 0.2 else "unroll its edge…"
        elif t >= K0:
            line = "turns = 1 + R/r"
        if line:
            c.text_centered(line, h * 0.76, size=w * 0.05, color=WHITE, max_w=w * 0.94)
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
    b = sfx.Bed(T_LOOP, seed=11)
    beat = 60 / 104
    b.pad([(0.0, (45, 52, 57, 64)), (G0, (41, 48, 57, 60)), (U0, (43, 50, 55, 62)), (K0, (45, 52, 57, 64))], beat,
          g=0.05)
    b.pulse(0.0, T_LOOP, beat, [69, 72, 76, 79], 0.022)
    prev = 0
    for fr in range(int(T_LOOP * FPS)):                        # a metallic tick per quarter turn
        tt = fr * DT
        q = int(state(tt)["turns"] * 4 + 1e-6)
        if q > prev:
            b.tick(tt, 3200 + 200 * (q % 4), 0.06)
        prev = q
    for tl in (A1, B1, U2):
        b.hit(tl, 0.45)
        b.chime(tl + 0.02, (79, 84, 88), 0.07)
    b.whoosh(G0, 1.0, 0.09, up=False)
    b.whoosh(U0, 0.8, 0.08)
    b.whoosh(K0, 1.2, 0.09)
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
