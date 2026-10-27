"""PUMPKIN — "This pumpkin is 100% math" (Halloween). A jack-o'-lantern drawn by 6 equations, lit by a 7th.

Timeline (seamless: the end is the lit pumpkin of frame 0):
  0.0–1.0   cold open: the lit jack-o'-lantern, "THIS PUMPKIN IS 100% MATH"; the Toccata mordent on frame 0
  1.0–2.0   the light goes out, the drawing un-draws
  2.2–10.6  equations draw it, one part at a time (pen traces each curve; the equation is on screen):
            body = 5 ellipses (x − c)²/0.55² + y² = 1 · stem x = 0.12 sin(2.2(y − 0.9)) · eyes y = 0.45 − 1.8|x ± 0.4|
            · nose y = 0.08 − 2|x| · mouth y = −0.4 + 0.25x² − 0.09|sin 4x| and y = −0.62 + 0.64x²
  11.0      "light it up": brightness = e^(−r²), on the big D-minor organ chord; lit to the end
Music: Bach, Toccata and Fugue in D minor (public domain) — the opening phrase three times, an octave lower each time,
then the pedal D, the rolling diminished chord and the D-minor chord. Organ synthesised here (original recording).
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

SCENE = "pumpkin"
T_LOOP = 14.0
T_COLD, T_OUT, T_UNDRAW = 1.0, 1.2, 2.0
T_LIGHT0, T_LIGHT1 = 11.0, 11.6
T_TEXT = 12.3
ORANGE = (1.0, 0.55, 0.15)
STEM = (0.55, 0.85, 0.30)
FACE = (1.0, 0.85, 0.35)
PURPLE = (0.70, 0.55, 1.0)
RIB_C = [-0.75, -0.38, 0.0, 0.38, 0.75]


def ellipse(c, a, b, n=140):
    return [(c + a * math.cos(-math.pi / 2 + 2 * math.pi * j / n), b * math.sin(-math.pi / 2 + 2 * math.pi * j / n))
            for j in range(n + 1)]


def stem_curve():
    ys = np.linspace(0.86, 1.32, 40)
    xc = 0.12 * np.sin(2.2 * (ys - 0.9))
    hw = 0.09 - 0.03 * (ys - 0.86) / 0.46
    left = [(float(x - w), float(y)) for x, y, w in zip(xc, ys, hw)]
    right = [(float(x + w), float(y)) for x, y, w in zip(xc[::-1], ys[::-1], hw[::-1])]
    return left + right + [left[0]]


def eye(sign):
    cx = 0.4 * sign
    return [(cx - 0.222, 0.05), (cx, 0.45), (cx + 0.222, 0.05), (cx - 0.222, 0.05)]


NOSE = [(-0.10, -0.12), (0.0, 0.08), (0.10, -0.12), (-0.10, -0.12)]


def mouth():
    xs = np.linspace(-0.75, 0.75, 120)
    up = [(float(x), float(-0.40 + 0.25 * x * x - 0.09 * abs(math.sin(4 * x)))) for x in xs]
    lo = [(float(x), float(-0.62 + 0.64 * x * x)) for x in xs[::-1]]
    return up, lo


MU, ML = mouth()
# stages: (t0, t1, curves, colour, label, equation)
STAGES = [
    (2.2, 4.6, [ellipse(c, 0.55 if c else 0.50, 1.0 if abs(c) < 0.5 else 0.93) for c in [0.0, -0.38, 0.38, -0.75, 0.75]],
     ORANGE, "the body: 5 ellipses", "(x − c)² / 0.55² + y² = 1"),
    (4.6, 5.6, [stem_curve()], STEM, "the stem: a sine wave", "x = 0.12 sin(2.2(y − 0.9))"),
    (5.8, 7.4, [eye(-1), eye(1)], FACE, "the eyes: |x| makes a triangle", "y = 0.45 − 1.8 |x ± 0.4|"),
    (7.6, 8.4, [NOSE], FACE, "the nose", "y = 0.08 − 2 |x|"),
    (8.6, 10.6, [MU, ML], FACE, "the mouth: x² smile, |sin| teeth", "y = −0.4 + 0.25x² − 0.09|sin 4x|"),
]
HOLES = [eye(-1), eye(1), NOSE, MU + ML]


def simulate():
    return {"nf": int(round(T_LOOP * FPS))}


def lit_amount(t):
    if t < T_OUT:
        return 1.0 - smooth((t - T_COLD) / (T_OUT - T_COLD))
    return smooth((t - T_LIGHT0) / (T_LIGHT1 - T_LIGHT0))


def stage_prog(si, t):
    t0, t1 = STAGES[si][0], STAGES[si][1]
    if t < T_OUT:
        return 1.0
    if t < T_UNDRAW:
        return 1.0 - smooth((t - T_OUT) / (T_UNDRAW - T_OUT))
    return min(1.0, max(0.0, (t - t0) / (t1 - t0)))


class Scene:
    def __init__(self, layout, sim):
        self.L, self.sim = layout, sim
        self.canvas = Canvas(layout.w, layout.h, studio.render_scale())
        rng = np.random.default_rng(31)
        self.stars = [(float(rng.uniform(0, 1)), float(rng.uniform(0.17, 0.70)), float(rng.uniform(0.6, 1.8)),
                       float(rng.uniform(0, 6.28))) for _ in range(70)]

    def W(self, x, y):
        L = self.L
        s = L.w * 0.33
        return L.w / 2 + s * x, L.h * 0.46 - s * y

    def path(self, ctx, pts):
        ctx.new_path()
        x, y = self.W(*pts[0])
        ctx.move_to(x, y)
        for p in pts[1:]:
            ctx.line_to(*self.W(*p))

    def draw(self, f, rule):
        L, c = self.L, self.canvas
        w, h = L.w, L.h
        t = f * DT
        ctx = c.ctx
        g = cairo.LinearGradient(0, 0, 0, h)
        g.add_color_stop_rgb(0.0, 0.10, 0.05, 0.17)
        g.add_color_stop_rgb(0.6, 0.04, 0.02, 0.07)
        g.add_color_stop_rgb(1.0, 0.01, 0.01, 0.02)
        ctx.set_source(g)
        ctx.paint()
        for sx, sy, r, ph in self.stars:                      # gentle twinkle (smooth, small)
            c.circle(sx * w, sy * h, r, (0.9, 0.88, 1.0), alpha=0.25 + 0.15 * math.sin(1.3 * t + ph))
        cx, cy = self.W(0, 0)
        for xx in range(-1, 2):                               # faint maths grid
            X, _ = self.W(xx, 0)
            c.lines([(X, h * 0.24, X, h * 0.68)], (0.7, 0.65, 0.9), width=1, alpha=0.07)
        for yy in range(-1, 2):
            _, Y = self.W(0, yy)
            c.lines([(w * 0.05, Y, w * 0.95, Y)], (0.7, 0.65, 0.9), width=1, alpha=0.07)
        lit = lit_amount(t)
        flick = 1 + 0.05 * math.sin(9.1 * t) + 0.035 * math.sin(23.0 * t + 1.0)
        if lit > 0.005:
            halo = cairo.RadialGradient(cx, cy, 0, cx, cy, w * 0.62)
            halo.add_color_stop_rgba(0.0, 1.0, 0.55, 0.15, 0.30 * lit * flick)
            halo.add_color_stop_rgba(1.0, 1.0, 0.45, 0.10, 0.0)
            ctx.set_source(halo)
            ctx.paint()
            # body fill: union of the 5 rib ellipses, lit from inside
            for el in STAGES[0][2]:
                self.path(ctx, el)
                ctx.close_path()
                gx, gy = self.W(0, -0.2)
                body = cairo.RadialGradient(gx, gy, 0, gx, gy, w * 0.48)
                body.add_color_stop_rgba(0.0, 1.0, 0.62, 0.20, lit)
                body.add_color_stop_rgba(1.0, 0.75, 0.30, 0.05, lit)
                ctx.set_source(body)
                ctx.fill()
            self.path(ctx, STAGES[1][2][0])
            ctx.close_path()
            ctx.set_source_rgba(0.30, 0.50, 0.15, lit)
            ctx.fill()
        # strokes, traced by a pen
        pen = None
        for si, (t0, t1, curves, col, _, _) in enumerate(STAGES):
            p = stage_prog(si, t)
            if p <= 0:
                continue
            ncur = len(curves)
            for ci, cv in enumerate(curves):
                q = min(1.0, max(0.0, p * ncur - ci))
                if q <= 0:
                    continue
                k = max(2, int(len(cv) * q))
                pts = [self.W(*pp) for pp in cv[:k]]
                lc = tuple(a * (1 - 0.65 * lit) + b * 0.65 * lit for a, b in zip(col, (0.35, 0.15, 0.03)))
                c.polylines([pts], col, width=14, alpha=0.16 * (1 - lit))
                c.polylines([pts], lc, width=4.5, alpha=0.95)
                if 0 < q < 1 and t >= T_UNDRAW:
                    pen = (pts[-1], col)
        if lit > 0.005:                                       # the face holes glow
            for hole in HOLES:
                self.path(ctx, hole)
                ctx.close_path()
                hx, hy = self.W(*hole[1]) if len(hole) < 10 else self.W(0, -0.45)
                gl = cairo.RadialGradient(hx, hy, 0, hx, hy, w * 0.25)
                gl.add_color_stop_rgba(0.0, 1.0, 0.98, 0.75, lit)
                gl.add_color_stop_rgba(1.0, 1.0, 0.70, 0.15, lit)
                ctx.set_source(gl)
                ctx.fill()
            for hole in HOLES:
                hx, hy = self.W(*hole[1]) if len(hole) < 10 else self.W(0, -0.48)
                c.glow(hx, hy, w * 0.06, (1.0, 0.8, 0.3), strength=0.5 * lit * flick, reach=3)
        if pen:
            (px, py), col = pen
            c.glow(px, py, 10, col, strength=0.8, reach=4)
            c.circle(px, py, 7, (1, 1, 1), alpha=0.95)
        # text
        if t < T_OUT + 0.3 or t >= T_TEXT:
            a = 1.0 if t < T_COLD else (max(0.0, 1 - (t - T_COLD) / 0.4) if t < T_TEXT else smooth((t - T_TEXT) / 0.4))
            c.text_centered("THIS PUMPKIN IS 100% MATH", h * 0.745, size=w * 0.068, color=ORANGE, alpha=a)
            c.text_centered("happy Halloween", h * 0.785, size=w * 0.040, color=PURPLE, alpha=0.9 * a, bold=False)
        elif t >= T_UNDRAW:
            if t >= T_LIGHT0 - 0.3:
                a = smooth((t - T_LIGHT0 + 0.3) / 0.3) * (1 - smooth((t - T_TEXT + 0.4) / 0.4))
                c.text_centered("light it up", h * 0.735, size=w * 0.055, color=FACE, alpha=a)
                c.text_centered("brightness = e^(−r²)", h * 0.772, size=w * 0.046, color=(0.97, 0.96, 1.0),
                                alpha=0.92 * a, bold=False)
            else:
                si = max(i for i, s in enumerate(STAGES) if t >= s[0] - 0.2)
                t0, t1, _, col, label, eq = STAGES[si]
                a = smooth((t - t0 + 0.2) / 0.25)
                c.text_centered(f"{si + 1}/6   {label}", h * 0.735, size=w * 0.045, color=col, alpha=a)
                c.text_centered(eq, h * 0.772, size=w * 0.046, color=(0.97, 0.96, 1.0), alpha=0.92 * a, bold=False)
        c.text_centered("HALLOWEEN · MATH ART", h * 0.185, size=h * 0.0145, color=ORANGE, alpha=0.85)
        if rule:
            c.caption(rule, alpha=1.0, layout=L)
        c.watermark(L)


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


# ------------------------------------------------------------------ organ (Toccata and Fugue in D minor, Bach — PD)
SR = audio.SR


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def organ(m, dur, g):
    tv = np.arange(int((dur + 0.25) * SR)) / SR
    f = hz(m)
    sig = np.zeros_like(tv)
    for mult, a in ((1, 1.0), (2, 0.55), (3, 0.30), (4, 0.22), (6, 0.10), (0.5, 0.35 if m < 60 else 0.12)):
        if f * mult < SR / 2.3:
            sig += a * (np.sin(2 * np.pi * f * mult * tv) + 0.5 * np.sin(2 * np.pi * f * mult * 1.002 * tv + 1.0))
    env = np.clip(tv / 0.012, 0, 1) * np.clip((dur + 0.08 - tv) / 0.08, 0, 1)
    return g * sig * env / 3.0


def phrase(t0, shift):
    """Mordent A–G–A, held; then G F E D C# … D."""
    A, G_, F_, E_, D_, Cs = 81, 79, 77, 76, 74, 73
    notes = [(0.00, A, 0.07), (0.07, G_, 0.07), (0.14, A, 0.80),
             (1.10, G_, 0.12), (1.22, F_, 0.12), (1.34, E_, 0.12), (1.46, D_, 0.20), (1.66, Cs, 0.36), (2.05, D_, 0.75)]
    return [(t0 + dt, m + shift, d) for dt, m, d in notes]


def organ_bed():
    n = int(round(T_LOOP * SR))
    out = np.zeros(n + 2 * SR)

    def add(t0, sig):
        i0 = int(t0 * SR)
        out[i0:i0 + len(sig)] += sig

    for t0, m, d in phrase(0.0, 0):
        add(t0, organ(m, d, 0.30))
    for t0, m, d in phrase(2.3, -12):
        add(t0, organ(m, d, 0.34))
    for t0, m, d in phrase(5.3, -24):
        add(t0, organ(m, d, 0.34))
        add(t0, organ(m + 12, d, 0.18))
    add(8.4, organ(38, 2.8, 0.36))                       # pedal D
    add(8.4, organ(26, 2.8, 0.22))
    roll = [61, 64, 67, 70, 73, 76, 79, 82]               # C# dim7 rolling up
    for j, m in enumerate(roll):
        add(10.6 + j * 0.075, organ(m, 11.25 - (10.6 + j * 0.075), 0.16))
    for j, m in enumerate((38, 50, 53, 57, 62, 65, 69, 74)):   # D minor, held while it lights up
        add(11.3 + 0.015 * j, organ(m, 2.45, 0.15))
    # cathedral-ish reverb: noise IR with exponential decay
    rng = np.random.default_rng(5)
    L = int(1.1 * SR)
    ir = rng.standard_normal(L) * np.exp(-np.arange(L) / SR / 0.32)
    ir[0] = 0
    ir *= 0.035 / np.sqrt((ir ** 2).sum()) * 30
    m_ = len(out) + L
    nfft = 1 << (m_ - 1).bit_length()
    wet = np.fft.irfft(np.fft.rfft(out, nfft) * np.fft.rfft(ir, nfft), nfft)[:len(out)]
    mix = out + 0.35 * wet
    tail = mix[n:]
    mix = mix[:n]
    mix[: len(tail)] += tail
    return mix.astype(np.float32)


def _worker(o, sim, label, rule):
    layout = get_layout(o)
    name = f"{SCENE}_{label}_{layout.tag}"
    video = studio.OUT_DIR / f"{name}_silent.mp4"
    d = render(layout, sim, video, rule)
    kit.deliver_loop(SCENE, name, layout, video, [], d, voice="piano", bed=organ_bed())


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
