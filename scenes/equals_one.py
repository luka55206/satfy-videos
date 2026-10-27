"""EQUALS ONE — "Everything here equals 1": 30 identities that each equal 1 build a heart (improved take on a viral
"what you can make with 1" Short: readable, verified, payoff-first, a familiar tune, a perfect loop).

Timeline: 0–0.9 s the finished heart ("ALL OF THESE = 1") · 0.9–1.5 everything collapses into one "1" · then the
identities fly out of the 1 one at a time, each landing on the next note of Ode to Joy (Beethoven, PD), the newest
shown big with "= 1 ✓" · the heart completes, glows, holds → identical to frame 0 (seamless).
Every identity is checked numerically at import (assert).
"""
import cmath
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

SCENE = "equals_one"
PHI = (1 + 5 ** 0.5) / 2
X = 0.7                                                   # any x works for the x-identities
IDS = [  # (shown text, numeric check)
    ("sin²x + cos²x", math.sin(X) ** 2 + math.cos(X) ** 2),
    ("e^(iπ) + 2", (cmath.exp(1j * math.pi) + 2).real),
    ("0!", math.factorial(0)),
    ("(−1)²", (-1) ** 2),
    ("log(10)", math.log10(10)),
    ("ln(e)", math.log(math.e)),
    ("2⁰", 2 ** 0),
    ("cos(0)", math.cos(0)),
    ("tan(π/4)", math.tan(math.pi / 4)),
    ("sin(π/2)", math.sin(math.pi / 2)),
    ("√1", math.sqrt(1)),
    ("7 / 7", 7 / 7),
    ("|−1|", abs(-1)),
    ("½ + ¼ + ⅛ + …", sum(0.5 ** k for k in range(1, 60))),
    ("φ² − φ", PHI ** 2 - PHI),
    ("cosh²x − sinh²x", math.cosh(X) ** 2 - math.sinh(X) ** 2),
    ("sec²x − tan²x", 1 / math.cos(X) ** 2 - math.tan(X) ** 2),
    ("e⁰", math.exp(0)),
    ("3² − 2³", 3 ** 2 - 2 ** 3),
    ("0.1 + 0.9", 0.1 + 0.9),
    ("|e^(iθ)|", abs(cmath.exp(1j * X))),
    ("gcd(8, 9)", math.gcd(8, 9)),
    ("(e^(iπ))²", (cmath.exp(1j * math.pi) ** 2).real),
    ("5! / 120", math.factorial(5) / 120),
    ("π⁰", math.pi ** 0),
    ("2 × 0.5", 2 * 0.5),
    ("d/dx (x)", 1.0),
    ("φ − 1/φ", PHI - 1 / PHI),
    ("sin(x)/x, x → 0", math.sin(1e-8) / 1e-8),
    ("0.999…", 1 - 10 ** -15),
]
for _s, _v in IDS:
    assert abs(_v - 1) < 1e-9, (_s, _v)

E4, F4, G4, D4, C4 = 64, 65, 67, 62, 60
ODE = [(E4, 1), (E4, 1), (F4, 1), (G4, 1), (G4, 1), (F4, 1), (E4, 1), (D4, 1), (C4, 1), (C4, 1), (D4, 1), (E4, 1),
       (E4, 1.5), (D4, 0.5), (D4, 2),
       (E4, 1), (E4, 1), (F4, 1), (G4, 1), (G4, 1), (F4, 1), (E4, 1), (D4, 1), (C4, 1), (C4, 1), (D4, 1), (E4, 1),
       (D4, 1.5), (C4, 0.5), (C4, 2)]
BEAT = 0.40
T_COLD, T_COLL, T_BUILD = 0.9, 1.5, 1.6
ARR = [T_BUILD + BEAT * sum(d for _, d in ODE[:i]) for i in range(len(ODE))]
T_DONE = ARR[-1] + 0.3
T_LOOP = T_DONE + 1.6
GOLD = (1.0, 0.82, 0.40)
PINK = (1.0, 0.45, 0.62)


def heart(n, scale):
    t = np.linspace(0, 2 * math.pi, 4000)
    x = 16 * np.sin(t) ** 3
    y = 13 * np.cos(t) - 5 * np.cos(2 * t) - 2 * np.cos(3 * t) - np.cos(4 * t)
    seg = np.hypot(np.diff(x), np.diff(y))
    cum = np.concatenate([[0], np.cumsum(seg)])
    u = (np.arange(n) + 0.5) / n * cum[-1]
    idx = np.searchsorted(cum, u)
    return [(float(x[i] * scale), float(y[i] * scale)) for i in idx], (x * scale, y * scale)


OUTER, OUT_CURVE = heart(18, 1.0)
INNER, IN_CURVE = heart(12, 0.56)
SLOTS = OUTER + INNER
ORDER = list(range(len(IDS)))


def simulate():
    return {"nf": int(round(T_LOOP * FPS))}


class Scene:
    def __init__(self, layout, sim):
        self.L, self.sim = layout, sim
        self.canvas = Canvas(layout.w, layout.h, studio.render_scale())
        w, h = layout.w, layout.h
        self.S = w * 0.42 / 16
        self.cx, self.cy = w / 2, h * 0.42
        self.slots, self.size = self.pack()

    def pack(self):
        """Fill the heart with rows of identities (a heart-shaped word cloud): no overlaps, all upright."""
        w = self.L.w
        meas = cairo.Context(cairo.ImageSurface(cairo.FORMAT_ARGB32, 4, 4))
        meas.select_font_face("Arial", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        xs, ys = OUT_CURVE
        for size, rf in [(w * f, r) for f in (0.044, 0.040, 0.037, 0.034, 0.031) for r in (2.6, 2.35, 2.1, 1.9, 1.75)]:
            meas.set_font_size(size)
            widths = [meas.text_extents(t).x_advance + size * 0.9 for t, _ in IDS]
            row_h = size * rf
            top, bot = self.cy - self.S * ys.max(), self.cy - self.S * ys.min()
            slots, k = [], 0
            y = top + row_h * 0.9
            while y < bot - row_h * 0.3 and k < len(IDS):
                wy = (self.cy - y) / self.S                       # world y of this row
                cross = []
                for i in range(len(xs) - 1):
                    if (ys[i] - wy) * (ys[i + 1] - wy) < 0:
                        f = (wy - ys[i]) / (ys[i + 1] - ys[i])
                        cross.append(self.cx + self.S * (xs[i] + f * (xs[i + 1] - xs[i])))
                cross.sort()
                for a, b in zip(cross[::2], cross[1::2]):         # inside intervals of this row
                    a, b = a + size * 0.4, b - size * 0.4
                    row, used = [], 0.0
                    while k < len(IDS) and used + widths[k] <= b - a:
                        row.append(k)
                        used += widths[k]
                        k += 1
                    x = a + (b - a - used) / 2
                    for j in row:
                        slots.append((x + widths[j] / 2, y))
                        x += widths[j]
                y += row_h
            if k == len(IDS):
                return slots, size
        raise RuntimeError("identities do not fit in the heart")

    def P(self, x, y):
        return self.cx + self.S * x, self.cy - self.S * y

    def draw(self, f, rule):
        L, c = self.L, self.canvas
        w, h = L.w, L.h
        t = f * DT
        ctx = c.ctx
        g = cairo.RadialGradient(w / 2, h * 0.42, 0, w / 2, h * 0.42, max(w, h) * 0.7)
        g.add_color_stop_rgb(0.0, 0.10, 0.05, 0.10)
        g.add_color_stop_rgb(1.0, 0.01, 0.01, 0.02)
        ctx.set_source(g)
        ctx.paint()
        complete = t < T_COLD or t >= T_DONE
        coll = smooth((t - T_COLD) / (T_COLL - T_COLD)) if T_COLD <= t < T_BUILD else (1.0 if T_COLL <= t < T_BUILD else 0.0)
        glow = 1.0 if t < T_COLD else (smooth((t - T_DONE) / 0.4) if t >= T_DONE else 0.0)
        if glow > 0.01:                                    # the glowing heart behind the identities
            for cv in (OUT_CURVE,):
                pts = [self.P(x, y) for x, y in zip(cv[0][::8], cv[1][::8])]
                c.polylines([pts], PINK, width=26, alpha=0.10 * glow)
                c.polylines([pts], PINK, width=3, alpha=0.55 * glow)
        # the identities
        for i, (txt, _) in enumerate(IDS):
            sx, sy = self.slots[i]
            size = self.size
            if complete:
                a, k = 1.0, 0.0
            elif t < T_BUILD:
                a, k = 1.0 - coll, coll                    # collapsing into the centre
            else:
                if t < ARR[i] - 0.28:
                    continue
                k = 1 - smooth((t - (ARR[i] - 0.28)) / 0.28)  # flying out of the centre "1"
                a = 1.0
            x = sx + (self.cx - sx) * k
            y = sy + (self.cy - sy) * k
            fresh = math.exp(-max(0.0, t - ARR[i]) / 0.15) if (not complete and t >= ARR[i]) else 0.0
            col = tuple(p + (q - p) * fresh for p, q in zip((1.0, 0.80, 0.86), GOLD))
            c.text_centered(txt, y + size * 0.35, size=size * (1 - 0.6 * k) * (1 + 0.25 * fresh), color=col,
                            alpha=a * (0.95 if not complete else 0.95), cx=x, bold=False)
        # the centre "1"
        if not complete:
            one = smooth((t - T_COLD) / 0.6)
            c.glow(self.cx, self.cy, w * 0.05, GOLD, strength=0.4 * one, reach=3)
            c.text_centered("1", self.cy + w * 0.06, size=w * 0.17 * one, color=GOLD, alpha=one)
        # bottom: the newest identity, big and checked — or the payoff line
        if complete:
            a = 1.0 if t < T_COLD else smooth((t - T_DONE) / 0.35)
            c.text_centered("ALL OF THESE = 1", h * 0.745, size=w * 0.085, color=GOLD, alpha=a)
            c.text_centered("30 different ways to write one number", h * 0.785, size=w * 0.036,
                            color=(0.9, 0.85, 0.9), alpha=0.9 * a, bold=False)
        elif t >= ARR[0]:
            i = max(j for j in range(len(ARR)) if ARR[j] <= t)
            pop = math.exp(-(t - ARR[i]) / 0.12)
            c.text_centered(IDS[i][0], h * 0.735, size=w * 0.072 * (1 + 0.1 * pop), color=(1, 0.95, 0.97),
                            alpha=1.0, bold=False)
            c.text_centered("= 1", h * 0.785, size=w * 0.06, color=GOLD, alpha=1.0, cx=w * 0.47)
            ck = w * 0.022                                          # a drawn check mark (no font glyph needed)
            bx, by = w * 0.58, h * 0.775
            c.lines([(bx, by, bx + ck * 0.8, by + ck), (bx + ck * 0.8, by + ck, bx + ck * 2.2, by - ck * 1.1)],
                    (0.45, 1.0, 0.55), width=7, alpha=1.0)
            c.text_centered(f"{i + 1} / {len(IDS)}", h * 0.815, size=w * 0.03, color=(0.7, 0.68, 0.78), alpha=0.8,
                            bold=False)
        c.text_centered("30 WAYS TO WRITE 1", h * 0.185, size=h * 0.0145, color=GOLD, alpha=0.85)
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


def build_events(sim, layout):
    x = layout.w / 2
    out = []
    for j, m in enumerate((48, 60, 64, 67, 72)):                     # frame 0: the finished heart's chord
        out.append({"t": round(0.012 * j, 4), "note": m, "gain": 0.26, "x": x})
    for j in range(7):                                                # collapse
        out.append({"t": round(T_COLD + 0.08 * j, 4), "note": 84 - 3 * j, "gain": 0.12, "x": x})
    for i, (m, d) in enumerate(ODE):                                  # Ode to Joy, one note per identity
        out.append({"t": round(ARR[i], 4), "note": m + 12, "gain": 0.40, "x": layout.w * (0.3 + 0.4 * (i % 2))})
    bar = 4 * BEAT
    chords = [(48, 52, 55), (43, 50, 55), (48, 52, 55), (43, 50, 55), (48, 52, 55), (43, 50, 55), (48, 52, 55),
              (43, 47, 50)]
    for k, ch in enumerate(chords):                                   # soft piano-ish chords under the tune
        for j, m in enumerate(ch):
            out.append({"t": round(T_BUILD + k * bar + 0.01 * j, 4), "note": m, "gain": 0.13, "x": x})
    for j, m in enumerate((48, 60, 64, 67, 72, 76)):                  # completion
        out.append({"t": round(T_DONE + 0.05 * j, 4), "note": m, "gain": 0.28, "x": x})
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
    print(f"[{SCENE}] {T_LOOP:.1f}s, {len(IDS)} identities all verified = 1")
    kit.fan_out(_worker, (sim, label, rule), SCENE)


if __name__ == "__main__":
    main()
