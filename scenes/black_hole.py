"""BLACK HOLE — "A star falls into a black hole, as math 🔊" (math-sound + space story; model: the audience's
favourite overlap channel does disasters "as math" at 0.2-1.9M views).

Physics (simplified, honest): a star spirals into a black hole by losing orbital energy. The radius follows the
gravitational-wave inspiral law r(t) = r0·(1 − t/tc)^(1/4); the orbit speeds up by Kepler, ω ∝ r^(−3/2), so the
frequency rises as f ∝ (tc − t)^(−3/8): the famous "chirp". The sound IS that frequency (orbit frequency scaled up
into hearing range), plus one note per completed orbit (pentatonic, climbing) — the beat accelerates to the end.
Inside the tidal radius the star is stretched into a glowing stream (spaghettification). At the last stable orbit it
plunges: a flash, a ring-down tone, "Swallowed.", then a fresh star fades in where the first one started (loop).
Audio: original synthesis only (chirp voice, glass notes, boom, ring-down, soft chord).
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

SCENE = "black_hole"
T_IN = 14.6                    # inspiral ends (plunge)
R_END = 0.115
TC = T_IN / (1 - R_END ** 4)   # so that r(T_IN) = R_END r0
T_HOLD = 2.4
T_LOOP = T_IN + T_HOLD + 1.0
R_TIDAL = 0.40                 # stream starts inside this radius (fraction of r0)
W0 = 2 * math.pi / 1.9         # first orbit takes 1.9 s
STAR = (1.0, 0.72, 0.30)
DISK = [(0.55, 0.25, 1.0), (1.0, 0.35, 0.6), (1.0, 0.65, 0.25)]
SR = audio.SR


def r_of(t):
    return R_END ** (min(t, T_IN) / T_IN)          # the orbit shrinks by the same factor every second


def build_track():
    """phase of the orbit at every frame (integrated ω), radius, frequency"""
    n = int(round(T_IN * FPS)) + 1
    ph, r, w = np.zeros(n), np.zeros(n), np.zeros(n)
    for k in range(n):
        t = k * DT
        r[k] = r_of(t)
        w[k] = W0 * r[k] ** -1.5
        if k:
            ph[k] = ph[k - 1] + 0.5 * (w[k] + w[k - 1]) * DT
    return ph, r, w


PH, RR, WW = build_track()
N_ORB = int(PH[-1] // (2 * math.pi))


def stars_bg(w, h, n=260, seed=5):
    rng = np.random.default_rng(seed)
    return [(rng.uniform(0, w), rng.uniform(0, h), rng.uniform(0.6, 2.2), rng.uniform(0.2, 0.9), rng.uniform(0, 6.28))
            for _ in range(n)]


class Scene:
    def __init__(self, layout):
        self.L = layout
        self.canvas = Canvas(layout.w, layout.h, studio.render_scale())
        self.bg = stars_bg(layout.w, layout.h)

    def frame(self, t):
        L, c = self.L, self.canvas
        w, h = L.w, L.h
        ctx = c.ctx
        # camera: zooms in as the star falls (the hole grows), then back out for the loop
        z_end = (1.0 / R_END) ** 0.6
        if t < T_IN:
            zoom = (1.0 / r_of(t)) ** 0.6
        else:
            zoom = z_end + (1.0 - z_end) * smooth((t - (T_LOOP - 1.5)) / 1.4)
        cx, cy, R0 = w / 2, h * 0.47, w * 0.40 * zoom
        self.zs = zoom ** 0.4                                   # star / stream size grows more gently
        g = cairo.RadialGradient(cx, cy, 0, cx, cy, h * 0.75)
        g.add_color_stop_rgb(0.0, 0.07, 0.04, 0.12)
        g.add_color_stop_rgb(1.0, 0.0, 0.0, 0.01)
        ctx.set_source(g)
        ctx.paint()
        for x, y, s, a, p in self.bg:
            c.circle(x, y, s, (1, 1, 1), alpha=a * (0.7 + 0.3 * math.sin(t * 1.7 + p)))
        k = min(int(t * FPS), len(PH) - 1)
        plunged = t >= T_IN
        post = t - T_IN
        flash = max(0.0, 1.0 - post / 0.45) if plunged else 0.0
        fed = smooth(post / 0.6) if plunged else 0.0
        # accretion disk: rotating rings, brighter after the meal
        rot = t * 0.9
        for i, rr in enumerate(np.linspace(0.10, 0.34, 12)):
            col = DISK[i % 3]
            ctx.save()
            ctx.translate(cx, cy)
            ctx.rotate(rot * (1.6 - rr * 3))
            ctx.new_path()
            ctx.arc(0, 0, R0 * rr, 0, 2 * math.pi)
            ctx.set_source_rgba(*col, (0.22 + 0.16 * (1 - i / 12)) * (1 + 0.9 * fed))
            ctx.set_line_width(R0 * 0.022 * (1 + 0.6 * fed))
            ctx.stroke()
            ctx.set_dash([R0 * 0.05, R0 * 0.09])
            ctx.new_path()
            ctx.arc(0, 0, R0 * rr, 0, 2 * math.pi)
            ctx.set_source_rgba(1, 0.9, 0.8, 0.12 * (1 + fed))
            ctx.set_line_width(R0 * 0.008)
            ctx.stroke()
            ctx.set_dash([])
            ctx.restore()
        # the event horizon + photon ring
        RH = R0 * 0.085
        c.glow(cx, cy, R0 * 0.36, (0.65, 0.35, 1.0), strength=0.18 + 0.2 * fed, reach=1.6)
        c.circle(cx, cy, RH, (0, 0, 0))
        c.ring(cx, cy, RH * 1.06, (1.0, 0.9, 0.7), width=6, alpha=0.95)
        # the orbit guide (faint) and the last stable orbit
        if not plunged:
            c.ring(cx, cy, R0 * RR[k], (0.6, 0.65, 0.9), width=2, alpha=0.18)
        c.ring(cx, cy, R0 * R_END, (1.0, 0.4, 0.5), width=2, alpha=0.25 * (1 - fed))
        # the star + its stream
        if not plunged:
            ph, r = PH[k], RR[k]
            sx, sy = cx + R0 * r * math.cos(ph), cy - R0 * r * math.sin(ph)
            stretch = smooth((R_TIDAL - r) / (R_TIDAL - R_END))
            if stretch > 0:                                    # spaghettification: a stream along the orbit behind
                span = 0.4 + 3.6 * stretch                     # radians of orbit the stream covers
                pts = []
                for j in range(60):
                    u = j / 59
                    pj = ph - span * u
                    rj = r * (1 + 0.10 * stretch * u)          # slightly outside: it trails
                    pts.append((cx + R0 * rj * math.cos(pj), cy - R0 * rj * math.sin(pj), u))
                for j in range(len(pts) - 1):
                    x0, y0, u = pts[j]
                    x1, y1, _ = pts[j + 1]
                    c.lines([(x0, y0, x1, y1)], STAR, width=w * 0.02 * self.zs * (1 - u) * (0.5 + stretch), alpha=0.85 * (1 - u))
            rad = w * 0.02 * self.zs * (1 - 0.35 * stretch)
            c.glow(sx, sy, rad, STAR, strength=0.9, reach=3.0)
            c.circle(sx, sy, rad, (1.0, 0.85, 0.55))
        if flash > 0:
            c.glow(cx, cy, w * 0.16, (1.0, 0.9, 0.8), strength=0.75 * flash, reach=2.2)
        # loop: a new star fades in at the start position
        if t > T_IN + T_HOLD:
            a = smooth((t - T_IN - T_HOLD) / 1.0)
            sx, sy = cx + R0, cy
            c.glow(sx, sy, w * 0.02, STAR, strength=0.9 * a, reach=3.0)
            c.circle(sx, sy, w * 0.02, (1.0, 0.85, 0.55), alpha=a)
        # HUD
        f_orb = WW[k] / (2 * math.pi) if not plunged else 0.0
        hz = 110.0 * (WW[k] / W0) ** 0.8 if not plunged else 0.0
        orbits = int(PH[k] // (2 * math.pi)) if not plunged else N_ORB
        c.text_centered(f"orbits: {orbits}", h * 0.715, size=w * 0.05, color=(1, 1, 1), cx=w * 0.27, max_w=w * 0.45)
        c.text_centered(f"{f_orb:.2f} per second" if not plunged else "—", h * 0.715, size=w * 0.05, color=STAR,
                        cx=w * 0.73, max_w=w * 0.45)
        c.text_centered("closer = faster: every orbit speeds up", h * 0.755, size=w * 0.04, color=(0.75, 0.8, 1.0),
                        bold=False)
        if plunged and t < T_IN + T_HOLD + 0.6:
            a = smooth(post / 0.3) * (1 - smooth((t - T_IN - T_HOLD) / 0.6))
            c.text_centered("Swallowed.", h * 0.33, size=w * 0.10, color=(1, 1, 1), alpha=a)
        elif not plunged:
            c.text_centered(f"you hear: {hz:,.0f} Hz", h * 0.795, size=w * 0.036, color=(0.75, 0.8, 1.0), bold=False)

    def draw(self, f, rule):
        c, L = self.canvas, self.L
        t = f * DT
        self.frame(t)
        k_ = smooth((t - (T_LOOP - 0.4)) / 0.38)
        if k_ > 0:
            c.ctx.push_group()
            self.frame(0.0)
            c.ctx.pop_group_to_source()
            c.ctx.paint_with_alpha(k_)
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


def build_bed():
    n = int(round(T_LOOP * SR))
    buf = np.zeros(n + 3 * SR)
    t = np.arange(int(T_IN * SR)) / SR
    r = R_END ** (t / T_IN)
    w = W0 * r ** -1.5
    f = 110.0 * (w / W0) ** 0.8                                     # the chirp voice
    ph = 2 * np.pi * np.cumsum(f) / SR
    amp = 0.10 + 0.32 * (t / T_IN) ** 1.5
    orbit_wob = 0.75 + 0.25 * np.cos(np.cumsum(w) / SR)            # each orbit swells once (it comes round)
    voice = (np.sin(ph) + 0.35 * np.sin(2 * ph) + 0.15 * np.sin(3 * ph)) * amp * orbit_wob
    voice[:int(0.05 * SR)] *= np.linspace(0, 1, int(0.05 * SR))
    buf[:len(voice)] += voice
    i0 = int(T_IN * SR)                                             # plunge: boom + ring-down at the last pitch
    tv = np.arange(int(2.6 * SR)) / SR
    boom = np.sin(2 * np.pi * np.cumsum(38 + 120 * np.exp(-tv / 0.08)) / SR) * np.exp(-tv / 0.6)
    ring = np.sin(2 * np.pi * f[-1] * tv) * np.exp(-tv / 0.18) * 0.4
    buf[i0:i0 + len(tv)] += 0.9 * boom + ring
    for m in (45, 52, 57, 61, 64):                                  # a soft resolving chord after
        tv2 = np.arange(int(2.2 * SR)) / SR
        ch = np.sin(2 * np.pi * audio.midi_to_hz(m) * tv2) * np.sin(np.pi * np.minimum(1, tv2 / 2.2)) * 0.06
        j = int((T_IN + 0.5) * SR)
        buf[j:j + len(ch)] += ch
    buf[: len(buf) - n] += buf[n:]
    return buf[:n].astype(np.float32)


def build_events(layout):
    walker = audio.ScaleWalker(root_midi=60, scale=audio.PENTA_MAJOR, span=10, pattern="up")
    ev = []
    for k in range(1, N_ORB + 1):
        i = int(np.searchsorted(PH, 2 * math.pi * k))
        t = i * DT
        if t >= T_IN:
            break
        ev.append({"t": round(t, 4), "note": walker.next(), "gain": round(0.35 + 0.35 * t / T_IN, 3),
                   "x": layout.w * 0.8})
    return ev


def main():
    label, rule = arg("--label", "v1"), arg("--rule", "")
    studio.OUT_DIR.mkdir(exist_ok=True)
    layout = get_layout("vertical")
    print(f"[{SCENE}] orbits {N_ORB}, final freq {WW[-1] / 2 / math.pi:.2f}/s, loop {T_LOOP:.1f}s")
    if kit.has("--still"):
        f = int(arg("--frame", "0"))
        png = studio.OUT_DIR / f"{SCENE}_{label}_f{f}_{layout.tag}.png"
        render(layout, png, rule, still_frame=f)
        print(f"[{SCENE}] -> {png}")
        return
    name = f"{SCENE}_{label}_{layout.tag}"
    video = studio.OUT_DIR / f"{name}_silent.mp4"
    d = render(layout, video, rule)
    kit.deliver_loop(SCENE, name, layout, video, build_events(layout), d, voice="glassharp", bed=build_bed())


if __name__ == "__main__":
    main()
