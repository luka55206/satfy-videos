"""PI POLYGON — Archimedes' way to pi: double the sides of a polygon inside a circle.

Built from the channel's winner formula (fib_spiral, 69.5% stayed-to-watch): a famous constant,
frame 0 states the game ("6 sides", "pi ~ 3.0000000000"), the sides double every step (6, 12, 24 ...
393,216), the estimate n * sin(180deg / n) turns gold digit by digit up to 3.1415926535, ~16 s,
and a smooth rewind loop.

SELF-SIMILAR DIVE: the camera zooms x(n/6) sideways and x(n/6)^2 vertically (labelled "stretched"),
so every doubling looks identical on screen: an arc, a chord under it, the new corner pops out onto
the circle, and the view dives again. The picture never goes flat while the digits lock.
New corners slide out from the middle of each edge to the circle. Circle and polygon are drawn as
local polylines (never a huge cairo arc), so a zoom of x65,536 stays exact.

v3 (--hook 1): payoff-first. The video opens on 0.8 s of the finished result (glowing gold circle,
big π, all digits gold), snaps back to the hexagon, builds faster (first doubling ~0.7 s after the
tease), reveals, and ENDS exactly where the tease began, so the loop seam is invisible. ~12 s.

Audio (original synthesis only): a glass-harp note per doubling (rising, faster), a chime per new
gold digit, a chord when all ten decimals are gold, falling notes on the rewind, a periodic pad.
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

SCENE = "pi_polygon"
PI_STR = "3.1415926536"                   # pi rounded to 10 decimals (3.14159265358...)
K_MAX = 16                       # 6 * 2^16 = 393,216 sides
HOOK = arg("--hook", "0") == "1"              # v3: payoff-first cold open + seamless loop (default off = v2)
T_RUN, T_HOLD, T_BACK = (10.0 if HOOK else 11.0), 2.6, 1.6   # hold = zoom-out reveal + π bloom
T_REVEAL = 1.0                                  # zoom-out duration
T_BLOOM = T_RUN + 0.9                           # the big π + rings
T_LOOP = T_RUN + T_HOLD + T_BACK
# v3 timeline (video time v -> scene time t): a TEASE of the finished π bloom first, then the full build,
# ending exactly where the tease began (scene T_A), so the loop seam is invisible.
T_TEASE = 0.8
T_A = T_BLOOM + 0.5
V_LEN = T_TEASE + T_A if HOOK else T_LOOP


def scene_t(v):
    if not HOOK:
        return v
    return T_A + v if v < T_TEASE else v - T_TEASE
GOLD = (1.0, 0.82, 0.40)
TEAL = (0.35, 0.85, 0.95)
GREY = (0.75, 0.78, 0.88)


def k_at(t):
    """Fractional doubling count: slow first, faster and faster; rewind after a hold."""
    if t < T_RUN:
        u = t / T_RUN
        if HOOK:
            return K_MAX * (0.88 * u + 0.12 * u ** 1.8)  # v3: first doubling at ~0.7 s after the tease
        return K_MAX * (0.75 * u + 0.25 * u ** 1.8)      # first doubling at ~0.9 s
    if t < T_RUN + T_HOLD:
        return float(K_MAX)
    return K_MAX * (1.0 - smooth((t - T_RUN - T_HOLD) / T_BACK))


def estimate(n):
    return n * math.sin(math.pi / n)


def digits(v):
    s = f"{v:.10f}"
    m = 0
    while m < len(s) and s[m] == PI_STR[m]:
        m += 1
    return s, m


def zoom_log2(t):
    """Camera zoom (log2): dives with the doublings, then a fast zoom-out reveal; 1x on the rewind."""
    if t < T_RUN:
        return k_at(t)
    if t < T_RUN + T_HOLD:
        return K_MAX * (1.0 - smooth((t - T_RUN) / T_REVEAL))
    return 0.0


def lock_times():
    """Time each character of PI_STR first turns gold (for the digit pop)."""
    out, m_prev = {}, 0
    for f in range(int(T_RUN * FPS) + 1):
        t = f * DT
        _, m = digits(estimate(6 * 2 ** min(int(k_at(t)), K_MAX)))
        for i in range(m_prev, m):
            out[i] = t
        m_prev = max(m_prev, m)
    return out


LOCK_T = lock_times()


def simulate():
    return {"nf": int(round(V_LEN * FPS))}


class Scene:
    def __init__(self, layout, sim):
        self.L, self.sim = layout, sim
        self.canvas = Canvas(layout.w, layout.h, studio.render_scale())
        w, h = layout.w, layout.h
        self.vert = h > w
        if self.vert:
            self.c, self.R = (w / 2, h * 0.43), w * 0.36
            self.clip = (0, h * 0.22, w, h * 0.46)
            self.hud = (w / 2, h * 0.208, h * 0.715, h * 0.765, h * 0.800, w * 0.05)
        else:                                          # 16:9 (long-form): circle left, numbers right
            self.c, self.R = (w * 0.31, h * 0.56), h * 0.36
            self.clip = (0, h * 0.06, w * 0.60, h * 0.92)
            self.hud = (w * 0.79, h * 0.33, h * 0.45, h * 0.55, h * 0.62, h * 0.058)

    def draw(self, f, rule):
        L, c = self.L, self.canvas
        w, h = L.w, L.h
        t = scene_t(f * DT)
        kf = k_at(t)
        k = min(int(kf), K_MAX)
        fr = kf - k if k < K_MAX else 0.0
        fr = smooth(fr / 0.7) if fr < 0.7 else 1.0          # new corners slide out, then rest
        n0 = 6 * 2 ** k
        zl = zoom_log2(t)
        zoom = 2 ** zl                                        # sideways zoom (= n / 6 while diving)
        zv = zoom                                             # extra vertical stretch
        top = (self.c[1] - self.R) + min(1.0, zl / 1.5) * h * 0.075

        def P(x, d):
            # self-similar dive: x * n, (1 - y) * n^2, so every doubling looks identical.
            # d = 1 - y is passed in directly (computed without cancellation near the top).
            return self.c[0] + x * self.R * zoom, top + d * self.R * zoom * zv

        def on_circle(delta, r=1.0, one_minus_r=0.0):
            """Point at angle 90deg + delta, radius r: (x, 1 - y) computed precisely."""
            sd = math.sin(delta / 2)
            return P(-r * math.sin(delta), one_minus_r + r * 2 * sd * sd)

        ctx = c.ctx
        g = cairo.RadialGradient(self.c[0], self.c[1], 0, self.c[0], self.c[1], max(w, h) * 0.7)
        g.add_color_stop_rgb(0.0, 0.06, 0.05, 0.10)
        g.add_color_stop_rgb(1.0, 0.01, 0.01, 0.02)
        ctx.set_source(g)
        ctx.paint()

        xv = (w / 2) / (self.R * zoom)                       # visible |x| in world units
        half = math.pi if xv >= 0.999 else min(math.pi, math.asin(xv) * 1.15)
        ctx.save()
        ctx.rectangle(*self.clip)
        ctx.clip()
        # the circle (local polyline)
        circ = [on_circle(dl) for dl in np.linspace(-half, half, 900)]
        c.polylines([circ], (1, 1, 1), width=10, alpha=0.06)
        c.polylines([circ], (0.92, 0.93, 1.0), width=3, alpha=0.85)
        # the polygon: n0 fixed corners + (while doubling) n0 new corners sliding out
        n_draw = 2 * n0 if k < K_MAX else n0
        step = 2 * math.pi / n_draw
        J = min(int(half / step) + 2, n_draw // 2)
        sh = math.sin(math.pi / (2 * n0))
        omr_new = 2 * sh * sh * (1 - fr)                    # 1 - r for a sliding corner, precise
        verts = []
        dense = J > 1500                                      # e.g. the 393,216-gon at zoom 1: it IS a circle
        for j in ([] if dense else range(-J, J + 1)):
            if j % 2 == 0 or k >= K_MAX:
                verts.append(on_circle(j * step))
            else:
                verts.append(on_circle(j * step, 1.0 - omr_new, omr_new))
        if dense:
            verts = circ
        elif n_draw <= 2 * J + 1:
            verts.append(verts[0])
        bloom = smooth((t - T_BLOOM + 0.3) / 0.4) * (1.0 - smooth((t - T_RUN - T_HOLD) / 0.6))
        c.polylines([verts], GOLD, width=14 + 30 * bloom, alpha=0.10 + 0.12 * bloom)
        c.polylines([verts], GOLD, width=4 + 3 * bloom, alpha=0.95)
        if not dense and len(verts) < 400:
            for q in verts:
                c.circle(*q, 6, GOLD, alpha=0.95)
        ctx.restore()
        if bloom > 0.01:                                     # the satisfying result: π blooms
            cc = (self.c[0], top + self.R)
            age = t - T_BLOOM
            for kk in range(3):
                a_r = age - 0.12 * kk
                if 0 < a_r < 1.2:
                    c.ring(*cc, self.R * (0.3 + 1.1 * smooth(a_r / 1.2)), GOLD, width=4,
                           alpha=0.7 * (1 - a_r / 1.2))
            c.glow(*cc, self.R * 0.25, GOLD, strength=0.35 * bloom, reach=3.0)
            c.text_centered("π", cc[1] + self.R * 0.22, size=self.R * 0.75 * (0.8 + 0.2 * bloom),
                            color=GOLD, alpha=bloom, cx=cc[0])

        # HUD
        n_show = n0
        est = estimate(n_show)
        s, m = digits(est)
        fs = w * 0.05
        hx, y_tag, y_n, y_pi, y_f, fs = self.hud
        c.text_centered("FAMOUS NUMBERS · π", y_tag, size=h * 0.015 * (1 if self.vert else 1.6), color=GOLD,
                        alpha=0.75, cx=hx)
        c.text_centered(f"{n_show:,} sides", y_n, size=fs * 1.0, color=(1, 1, 1), cx=hx)
        self.pi_text(s, m, hx, y_pi, fs * 1.05, t)
        c.text_centered("π ≈ n · sin(180° / n)", y_f, size=fs * 0.50, color=GREY, alpha=0.8, bold=False, cx=hx)
        if zoom >= 1.5 and t < T_RUN:
            c.text_centered(f"zoom ×{zoom:,.0f} (stretched ×{zoom * zv:,.0f} up)",
                            h * 0.235 if self.vert else h * 0.70, size=h * (0.013 if self.vert else 0.022),
                            color=GREY, alpha=0.8, bold=False, cx=w * 0.74 if self.vert else self.hud[0], max_w=w * (0.5 if self.vert else 0.36))
        if rule:
            c.caption(rule, alpha=1.0, layout=L)
        c.watermark(L)

    def pi_text(self, s, m, cx, y, size, t):
        """'π ≈ 3.14…' drawn per character; each digit POPS (scale bounce + glow) as it turns gold."""
        c = self.canvas
        ctx = c.ctx
        lab = "π ≈ "
        c._font(size, True)
        wl, ws = ctx.text_extents(lab).x_advance, ctx.text_extents(s).x_advance
        x = cx - (wl + ws) / 2
        ctx.set_source_rgba(0.85, 0.85, 0.92, 1.0)
        ctx.move_to(x, y)
        ctx.show_text(lab)
        x += wl
        for i, ch in enumerate(s):
            c._font(size, True)
            adv = ctx.text_extents(ch).x_advance
            gold = i < m
            tl = LOCK_T.get(i)
            pop = 0.0
            if gold and tl is not None and t >= tl and t < T_RUN + T_HOLD:
                pop = math.exp(-(t - tl) / 0.12)
            sc = 1.0 + 0.55 * pop
            if pop > 0.02:
                c.glow(x + adv / 2, y - size * 0.35, size * 0.35, GOLD, strength=0.5 * pop, reach=2.5)
            c._font(size * sc, True)
            e2 = ctx.text_extents(ch)
            px = x + adv / 2 - e2.x_advance / 2
            ctx.set_source_rgba(0, 0, 0, 0.5)
            ctx.move_to(px + 2, y + 2)
            ctx.show_text(ch)
            ctx.set_source_rgba(*(GOLD if gold else (1, 1, 1)), 1.0)
            ctx.move_to(px, y)
            ctx.show_text(ch)
            x += adv


def render(layout, sim, out_path, rule, still_frame=None):
    sc = Scene(layout, sim)
    writer = None if still_frame is not None else VideoWriter(out_path, sc.canvas, FPS)
    for f in range(sim["nf"]):
        if still_frame is not None and f != still_frame:
            continue
        sc.draw(f, rule)
        if writer is None:
            studio.save_still(sc.canvas, out_path)
            return f / FPS
        writer.write_frame()
    writer.close()
    return sim["nf"] / FPS


def build_events(sim, layout):
    walker = audio.ScaleWalker(root_midi=60, scale=audio.PENTA_MAJOR, span=14, pattern="up")
    out, locked, gold_t = [], 1, None
    k_prev = 0
    for f in range(int(T_RUN * FPS) + 1):
        t = f * DT
        k = int(k_at(t))
        if k > k_prev:
            out.append({"t": round(t, 4), "note": walker.next(), "gain": round(0.38 + 0.16 * k / K_MAX, 3),
                        "x": layout.w / 2})
            _, m = digits(estimate(6 * 2 ** k))
            if m > locked and m >= 3:
                out.append({"t": round(t + 0.07, 4), "note": 86 if m % 2 else 88, "gain": 0.26, "x": layout.w / 2})
            locked = max(locked, m)
            if gold_t is None and locked >= len(PI_STR):
                gold_t = t
            k_prev = k
    t_end = T_BLOOM - 0.12
    for j, note in enumerate((48, 55, 60, 64, 67, 72)):
        out.append({"t": round(t_end + 0.12 + 0.06 * j, 4), "note": note, "gain": 0.42, "x": layout.w / 2})
    for j, note in enumerate((79, 76, 72, 69, 67)):
        out.append({"t": round(T_RUN + T_HOLD + 0.05 + 0.28 * j, 4), "note": note, "gain": 0.22, "x": layout.w / 2})
    if HOOK:                                              # remap to video time, drop the old rewind
        mapped = []
        for e in out:
            if e["t"] < T_A:
                e = dict(e, t=round(e["t"] + T_TEASE, 4))
                mapped.append(e)
        for j, note in enumerate((84, 79, 76, 72)):       # the snap from the tease back to the hexagon
            mapped.append({"t": round(T_TEASE - 0.12 + 0.04 * j, 4), "note": note, "gain": 0.22, "x": layout.w / 2})
        out = mapped
    return sorted(out, key=lambda e: e["t"])


def pad(sim):
    return kit.loop_pad(V_LEN, ((48, 1.0), (55, 0.7), (60, 0.45), (64, 0.3)), gain=0.015)


def _worker(o, sim, label, rule):
    layout = get_layout(o)
    name = f"{SCENE}_{label}_{layout.tag}"
    video = studio.OUT_DIR / f"{name}_silent.mp4"
    d = render(layout, sim, video, rule)
    kit.deliver_loop(SCENE, name, layout, video, build_events(sim, layout), d,
                     voice="glassharp", bed=pad(sim))


def main():
    label, rule = arg("--label", "v1"), arg("--rule", "")
    studio.OUT_DIR.mkdir(exist_ok=True)
    sim = simulate()
    if kit.has("--still"):
        layout = get_layout(kit.orients()[0])
        f = int(arg("--frame", "300"))
        png = studio.OUT_DIR / f"{SCENE}_{label}_f{f}_{layout.tag}.png"
        render(layout, sim, png, rule, still_frame=f)
        print(f"[{SCENE}] -> {png}")
        return
    for k in range(K_MAX + 1):
        n = 6 * 2 ** k
        print(f"  k={k:2d} n={n:>7,} est={estimate(n):.12f} gold={digits(estimate(n))[1]}")
    kit.fan_out(_worker, (sim, label, rule), SCENE)


if __name__ == "__main__":
    main()
