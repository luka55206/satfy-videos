"""GRAPH DANCE — math graphs dancing to an original beat. Every move is a parameter of the equation, changed on the beat.

Episode (--ep):
  1 "The function dance-off": y = A·sin(Bx + C), parabola, |x|, x³, sin(x)/x take turns on stage; each dance move = one
    parameter (A bounces on the kick, C slides on the hi-hat, B wiggles on the snare); the equation on screen changes
    live; a "move name" pops on each new move ("THE WAVE", "THE BOUNCE", "THE V", "THE DROP"…). Ends on all 5 together.
  2 "The polar disco": r = 1 + a·cos(kθ) — the shape breathes on the kick, spins on the beat, k changes every bar
    (3 → 4 → 5 → 6 → 8 petals); a mirror ball of dots; ends where it started (k = 3).
Beat: 120 BPM, 8 bars = 16 s, 4-on-the-floor kick, off-beat hats, clap on 2 and 4, bass and a catchy 4-note hook
(all synthesised). Seamless loop (16 s = exactly 8 bars).
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

SCENE = "graph_dance"
EP = int(arg("--ep", "1"))
BPM = 120.0
BEAT = 60.0 / BPM
BAR = 4 * BEAT
NBARS = 8
T_LOOP = NBARS * BAR
GOLD = (1.0, 0.82, 0.40)
SR = audio.SR


def kick_env(t):
    return math.exp(-((t % BEAT) / 0.11))


def snare_env(t):
    b = int(t // BEAT) % 4
    return math.exp(-((t % BEAT) / 0.14)) if b in (1, 3) else 0.0


# ------------------------------------------------------------- episode 1: the function dance-off
DANCERS = [  # name, colour, f(x, t, bar) -> y, equation text(t), move name
    ("THE WAVE", (0.45, 0.85, 1.00)),
    ("THE BOUNCE", (1.00, 0.55, 0.70)),
    ("THE V", (0.60, 1.00, 0.55)),
    ("THE SNAKE", (1.00, 0.75, 0.30)),
    ("THE DROP", (0.80, 0.60, 1.00)),
]


def dancer(i, x, t):
    k, s = kick_env(t), snare_env(t)
    ph = 2 * math.pi * t / BEAT
    if i == 0:
        A = 1.3 + 0.8 * k
        C = ph / 2
        return A * np.sin(1.3 * x + C), f"y = {A:.1f}·sin(1.3x + {C % 6.283:.1f})"
    if i == 1:
        a = 0.18 * (1 + 1.4 * k) * (1 if int(t // BEAT) % 2 == 0 else -1)
        return a * x * x - 1.5 * np.sign(a) + 0 * x, f"y = {a:.2f}·x² {'−' if a > 0 else '+'} 1.5"
    if i == 2:
        sh = 1.6 * math.sin(ph / 4)
        return 2.2 - 0.9 * (1 + 0.5 * k) * np.abs(x - sh), f"y = 2.2 − {0.9 * (1 + 0.5 * k):.1f}·|x − {sh:.1f}|"
    if i == 3:
        a = 0.035 * (1 + 0.8 * s) * math.cos(ph / 4)
        return a * x ** 3 - 0.5 * x * math.sin(ph / 4), f"y = {a:.3f}x³ − {0.5 * math.sin(ph / 4):.2f}x"
    w = 2.0 + 1.5 * k
    xx = np.where(np.abs(x) < 1e-6, 1e-6, x)
    return 3.0 * np.sin(w * xx) / (w * xx) - 0.6, f"y = 3·sin({w:.1f}x) / ({w:.1f}x)"


def ep1_who(bar):
    """Bars 0–5: one dancer per bar (with the previous one as a faint partner), bars 6–7: all together."""
    return [bar % 5] if bar < 6 else list(range(5))


# ------------------------------------------------------------- episode 2: polar disco
K_SEQ = [3, 4, 5, 6, 8, 5, 4, 3]


def simulate():
    return {"nf": int(round(T_LOOP * FPS))}


class Scene:
    def __init__(self, layout, sim):
        self.L, self.sim = layout, sim
        self.canvas = Canvas(layout.w, layout.h, studio.render_scale())

    def stage(self, t):
        """Disco floor: pulsing spotlights + grid that throbs on the kick."""
        L, c = self.L, self.canvas
        w, h = L.w, L.h
        ctx = c.ctx
        k = kick_env(t)
        g = cairo.RadialGradient(w / 2, h * 0.45, 0, w / 2, h * 0.45, max(w, h) * 0.7)
        g.add_color_stop_rgb(0.0, 0.10 + 0.05 * k, 0.05, 0.16 + 0.05 * k)
        g.add_color_stop_rgb(1.0, 0.01, 0.01, 0.03)
        ctx.set_source(g)
        ctx.paint()
        bar = int(t // BAR)
        for j in range(3):                                         # sweeping spotlights
            ang = math.sin(2 * math.pi * t / (2 * BAR) + j * 2.1) * 0.5
            x0 = w * (0.2 + 0.3 * j)
            col = studio.hsv((0.75 + 0.12 * j + 0.05 * bar) % 1, 0.6, 1.0)
            ctx.move_to(x0, 0)
            ctx.line_to(x0 + math.tan(ang - 0.12) * h * 0.75, h * 0.75)
            ctx.line_to(x0 + math.tan(ang + 0.12) * h * 0.75, h * 0.75)
            ctx.close_path()
            sp = cairo.LinearGradient(0, 0, 0, h * 0.75)
            sp.add_color_stop_rgba(0, *col, 0.10 + 0.06 * k)
            sp.add_color_stop_rgba(1, *col, 0.0)
            ctx.set_source(sp)
            ctx.fill()
        for i in range(-8, 9):                                     # floor grid
            c.lines([(w / 2 + i * w * 0.03, h * 0.66, w / 2 + i * w * 0.14, h * 0.74)], (0.8, 0.5, 1.0), width=1.5,
                    alpha=0.12 + 0.18 * k)

    def draw(self, f, rule):
        L, c = self.L, self.canvas
        w, h = L.w, L.h
        t = f * DT
        self.stage(t)
        bar = int(t // BAR) % NBARS
        k = kick_env(t)
        cx, cy = w / 2, h * 0.44
        if EP == 1:
            S = w * 0.085
            x = np.linspace(-5.2, 5.2, 700)
            c.lines([(w * 0.04, cy, w * 0.96, cy)], (0.8, 0.8, 0.95), width=2, alpha=0.25)
            c.lines([(cx, h * 0.25, cx, h * 0.64)], (0.8, 0.8, 0.95), width=2, alpha=0.25)
            who = ep1_who(bar)
            c.ctx.save()
            c.ctx.rectangle(0, h * 0.235, w, h * 0.415)              # the stage: graphs leave it instead of flattening
            c.ctx.clip()
            if bar < 6 and bar > 0:                                # last bar's dancer stays as a faint partner
                y, _ = dancer((bar - 1) % 5, x, t)
                c.polylines([list(zip(cx + S * x, cy - S * np.clip(y, -9, 9)))], DANCERS[(bar - 1) % 5][1],
                            width=3, alpha=0.22)
            eqs = []
            for i in who:
                y, eq = dancer(i, x, t)
                col = DANCERS[i][1]
                pts = list(zip(cx + S * x, cy - S * np.clip(y, -9, 9)))
                c.polylines([pts], col, width=18 + 10 * k, alpha=0.12)
                c.polylines([pts], col, width=5, alpha=0.95)
                eqs.append((eq, col))
            c.ctx.restore()
            tb = t - (t // BAR) * BAR
            pop = math.exp(-tb / 0.18)
            if bar < 6:
                name, col = DANCERS[who[0]]
                c.text_centered(name, h * 0.70, size=w * 0.085 * (1 + 0.25 * pop), color=col, alpha=1.0)
                c.text_centered(eqs[0][0], h * 0.755, size=w * 0.05, color=(0.97, 0.97, 1.0), alpha=0.95, bold=False)
                c.text_centered("every move = one number changing", h * 0.79, size=w * 0.032, color=(0.75, 0.78, 0.88),
                                alpha=0.85, bold=False)
            else:
                c.text_centered("ALL TOGETHER NOW", h * 0.70, size=w * 0.085 * (1 + 0.15 * k), color=GOLD, alpha=1.0)
                c.text_centered("5 functions · 1 beat", h * 0.755, size=w * 0.05, color=(0.97, 0.97, 1.0), alpha=0.95,
                                bold=False)
            c.text_centered("THE FUNCTION DANCE-OFF", h * 0.205, size=h * 0.015, color=GOLD, alpha=0.85)
        else:
            kk = K_SEQ[bar]
            kprev = K_SEQ[(bar - 1) % NBARS]
            tb = t % BAR
            m = smooth(tb / (BEAT * 0.5))                          # morph k at the bar line
            a = 0.55 + 0.35 * k
            spin = 2 * math.pi * (t / (4 * BAR)) + 0.25 * math.sin(2 * math.pi * t / BEAT)
            th = np.linspace(0, 2 * math.pi, 1200)
            r = 1 + a * ((1 - m) * np.cos(kprev * th) + m * np.cos(kk * th))
            R = w * 0.19
            for lay, (sc, col, al) in enumerate(((1.0, studio.hsv(0.85 + 0.04 * bar, 0.55), 0.95),
                                                 (0.62, studio.hsv(0.55 + 0.04 * bar, 0.55), 0.75),
                                                 (0.34, GOLD, 0.7))):
                rot = spin * (1 if lay % 2 == 0 else -1.3)
                pts = list(zip(cx + R * sc * r * np.cos(th + rot), cy - R * sc * r * np.sin(th + rot)))
                c.polylines([pts], col, width=20 + 12 * k, alpha=0.10 * al)
                c.polylines([pts], col, width=4.5, alpha=al)
            for j in range(kk * 2):                                 # mirror-ball sparkles on the petal tips
                ang = 2 * math.pi * j / (kk * 2) + spin
                rr = R * (1 + a) * (1.08 + 0.05 * math.sin(7 * t + j))
                c.circle(cx + rr * math.cos(ang), cy - rr * math.sin(ang), 4 + 4 * k, (1, 1, 1), alpha=0.5 + 0.4 * k)
            pop = math.exp(-tb / 0.18)
            c.text_centered(f"k = {kk}", h * 0.70, size=w * 0.09 * (1 + 0.25 * pop), color=GOLD, alpha=1.0)
            c.text_centered(f"r = 1 + {a:.2f}·cos({kk}θ)", h * 0.755, size=w * 0.05, color=(0.97, 0.97, 1.0),
                            alpha=0.95, bold=False)
            c.text_centered("k petals · a breathes on the kick", h * 0.79, size=w * 0.032, color=(0.75, 0.78, 0.88),
                            alpha=0.85, bold=False)
            c.text_centered("THE POLAR DISCO", h * 0.205, size=h * 0.015, color=GOLD, alpha=0.85)
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


# ------------------------------------------------------------- the beat (original)
def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def beat_bed():
    n = int(round(T_LOOP * SR))
    out = np.zeros(n + SR)
    rng = np.random.default_rng(4)

    def add(t0, sig):
        i0 = int(t0 * SR)
        out[i0:i0 + len(sig)] += sig

    tk = np.arange(int(0.35 * SR)) / SR
    kick = np.sin(2 * np.pi * np.cumsum(48 + 110 * np.exp(-tk / 0.03)) / SR) * np.exp(-tk / 0.15)
    th = np.arange(int(0.06 * SR)) / SR
    tc = np.arange(int(0.18 * SR)) / SR
    # root per bar (A minor pop loop: Am F C G) and the hook (4 notes, 8ths, answered every other bar)
    roots = [45, 41, 48, 43] * 2
    hook = [[69, 72, 76, 74], [72, 69, 67, 69], [76, 74, 72, 71], [74, 71, 67, 71]]
    for b in range(NBARS):
        t0 = b * BAR
        for q in range(4):
            add(t0 + q * BEAT, 0.75 * kick)
            hat = np.diff(np.concatenate([[0], rng.standard_normal(len(th))])) * np.exp(-th / 0.015)
            add(t0 + q * BEAT + BEAT / 2, 0.10 * hat)
            if q in (1, 3):
                cl = np.diff(np.concatenate([[0], rng.standard_normal(len(tc))])) * np.exp(-tc / 0.05)
                add(t0 + q * BEAT, 0.28 * cl)
        for e in range(8):                                     # bass: 8ths, octave jumps
            m = roots[b] - 12 + (12 if e % 2 else 0)
            tb = np.arange(int(BEAT / 2 * SR)) / SR
            sig = (np.sin(2 * np.pi * hz(m) * tb) + 0.4 * np.sin(4 * np.pi * hz(m) * tb)) * np.exp(-tb / 0.12)
            add(t0 + e * BEAT / 2, 0.30 * sig)
        for e, m in enumerate(hook[b % 4]):                     # the hook (plucky square-ish lead), 8ths on beats 1-2
            tl = np.arange(int(0.28 * SR)) / SR
            ph = 2 * np.pi * hz(m) * tl
            sig = (np.sin(ph) + 0.33 * np.sin(3 * ph) + 0.2 * np.sin(5 * ph)) * np.exp(-tl / 0.12)
            add(t0 + e * BEAT / 2 + (2 * BEAT if b % 2 else 0), 0.13 * sig)
        if b >= 6:                                              # stab chords in the last 2 bars (all-together)
            for q in range(4):
                for iv in (12, 16, 19):
                    ts = np.arange(int(0.15 * SR)) / SR
                    add(t0 + q * BEAT + BEAT / 2, 0.045 * np.sin(2 * np.pi * hz(roots[b] + iv) * ts) * np.exp(-ts / 0.06))
    tail = out[n:]
    out = out[:n]
    out[: len(tail)] += tail
    return out.astype(np.float32)


def _worker(o, sim, label, rule):
    layout = get_layout(o)
    name = f"{SCENE}_{label}_{layout.tag}"
    video = studio.OUT_DIR / f"{name}_silent.mp4"
    d = render(layout, sim, video, rule)
    kit.deliver_loop(SCENE, name, layout, video, [], d, voice="piano", bed=beat_bed(), peak_db=-6.0)


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
    print(f"[{SCENE}] ep {EP}, {T_LOOP:.1f}s")
    kit.fan_out(_worker, (sim, label, rule), SCENE)


if __name__ == "__main__":
    main()
