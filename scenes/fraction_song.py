"""FRACTION SONG — "Twinkle Twinkle, played with fractions" (melody: 18th-c. French tune, public domain).

Pythagoras' rule, the one thing to understand: a SHORTER string plays a HIGHER note. The whole string (1) is C;
2/3 of it is G, 3/5 is A, 3/4 is F, 4/5 is E, 8/9 is D (just intonation). Notes rise from below as bars whose
length IS the fraction (like a rhythm game); when a bar reaches the string the gold slider snaps to that
fraction, the string vibrates and you hear it plucked. The tune ends on 1 = C, where it started: the melody
itself is the loop. Two passes: the second adds soft chords.
Audio: original synthesis (Karplus-Strong plucked string + piano chords).
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

SCENE = "fraction_song"
BPM = 116.0
B = 60.0 / BPM
FRAC = {"C": (1, 1), "D": (8, 9), "E": (4, 5), "F": (3, 4), "G": (2, 3), "A": (3, 5)}
MEL = [("C", 1), ("C", 1), ("G", 1), ("G", 1), ("A", 1), ("A", 1), ("G", 2),
       ("F", 1), ("F", 1), ("E", 1), ("E", 1), ("D", 1), ("D", 1), ("C", 2)]
T_PASS = 16 * B
PASSES = 2
T_LOOP = PASSES * T_PASS
F_C = 261.63
GOLD = (1.0, 0.82, 0.40)
NCOL = {"C": (1.0, 0.45, 0.45), "D": (1.0, 0.68, 0.35), "E": (1.0, 0.90, 0.40), "F": (0.50, 0.90, 0.50),
        "G": (0.40, 0.80, 1.00), "A": (0.70, 0.55, 1.00)}
CHORDS = [(48, 52, 55), (48, 52, 55), (53, 57, 60), (48, 52, 55), (53, 57, 60), (48, 52, 55), (55, 59, 62),
          (48, 52, 55)]                       # C C F C | F C G C, two beats each


def notes():
    out, t = [], 0.0
    for p in range(-1, PASSES + 1):
        tt = p * T_PASS
        for nm, d in MEL:
            out.append((tt, d * B, nm))
            tt += d * B
    return out


NOTES = notes()


def frac(nm):
    a, b = FRAC[nm]
    return a / b


def simulate():
    return {"nf": int(round(T_LOOP * FPS))}


class Scene:
    def __init__(self, layout, sim):
        self.L, self.sim = layout, sim
        self.canvas = Canvas(layout.w, layout.h, studio.render_scale())

    def draw(self, f, rule):
        L, c = self.L, self.canvas
        w, h = L.w, L.h
        t = f * DT
        ctx = c.ctx
        g = cairo.RadialGradient(w / 2, h * 0.47, 0, w / 2, h * 0.47, max(w, h) * 0.7)
        g.add_color_stop_rgb(0.0, 0.07, 0.06, 0.11)
        g.add_color_stop_rgb(1.0, 0.01, 0.01, 0.02)
        ctx.set_source(g)
        ctx.paint()
        x0, x1 = w * 0.08, w * 0.92
        Ls = x1 - x0
        ys = h * 0.395                                       # the string
        cur = max((n for n in NOTES if n[0] <= t + 1e-9), key=lambda n: n[0])
        nxt = min((n for n in NOTES if n[0] > t + 1e-9), key=lambda n: n[0])
        age = t - cur[0]
        # slider: holds the current fraction, glides to the next one in the last 0.09 s
        fc, fn = frac(cur[2]), frac(nxt[2])
        k = smooth((t - (nxt[0] - 0.09)) / 0.09)
        fs_pos = fc + (fn - fc) * k
        # ---- the rising note bars (rhythm-game roll): bar length = the fraction
        speed = h * 0.30 / (4 * B)                           # px per second: 4 beats visible
        y_roll_bot = h * 0.70
        ctx.save()
        ctx.rectangle(0, ys + 6, w, y_roll_bot - ys - 6)
        ctx.clip()
        for t0, dur, nm in NOTES:
            yt = ys + (t0 - t) * speed                       # top edge reaches the string at t0
            yb = yt + dur * speed - 8
            if yb < ys - 40 or yt > y_roll_bot:
                continue
            fr = frac(nm)
            played = t0 <= t
            col = NCOL[nm]
            a = 0.22 if played else 0.85
            ctx.rectangle(x0, yt + 4, Ls * fr, max(4.0, yb - yt - 4))
            ctx.set_source_rgba(*col, a * 0.55)
            ctx.fill_preserve()
            ctx.set_source_rgba(*col, a)
            ctx.set_line_width(2.5)
            ctx.stroke()
            a_, b_ = FRAC[nm]
            lab = "1" if a_ == b_ else f"{a_}/{b_}"
            c.text_centered(f"{lab}  {nm}", yt + (yb - yt) / 2 + h * 0.011, size=h * 0.022, color=(1, 1, 1),
                            alpha=0.25 if played else 0.95, cx=x0 + Ls * fr - w * 0.075)
        ctx.restore()
        grad = cairo.LinearGradient(0, y_roll_bot - h * 0.06, 0, y_roll_bot)
        grad.add_color_stop_rgba(0, 0.02, 0.02, 0.03, 0.0)
        grad.add_color_stop_rgba(1, 0.02, 0.02, 0.03, 1.0)
        ctx.rectangle(0, y_roll_bot - h * 0.06, w, h * 0.06)
        ctx.set_source(grad)
        ctx.fill()
        # ---- the string: vibrating part (left of the slider) + dead part
        xs = x0 + Ls * fs_pos
        amp = h * 0.022 * math.exp(-age / 0.45)
        fvis = 7.0 / fs_pos
        pts = []
        for j in range(121):
            u = j / 120
            x = x0 + (xs - x0) * u
            y = ys + amp * math.sin(math.pi * u) * math.cos(2 * math.pi * fvis * t)
            pts.append((x, y))
        col = NCOL[cur[2]]
        c.polylines([pts], col, width=16, alpha=0.18 + 0.3 * math.exp(-age / 0.3))
        c.polylines([pts], (1.0, 0.97, 0.92), width=4, alpha=0.95)
        c.lines([(xs, ys, x1, ys)], (0.6, 0.6, 0.66), width=3, alpha=0.35)
        for xe in (x0, x1):                                  # the two fixed ends
            c.lines([(xe, ys - h * 0.025, xe, ys + h * 0.025)], (0.85, 0.86, 0.92), width=6, alpha=0.8)
        c.lines([(xs, ys - h * 0.034, xs, ys + h * 0.034)], GOLD, width=8, alpha=0.95)      # the slider
        c.glow(xs, ys, 10, GOLD, strength=0.4 + 0.5 * math.exp(-age / 0.15), reach=3)
        # ruler ticks: 0 … 1 of the string
        for q, lab in ((0.5, "1/2"), (1.0, "1")):
            xq = x0 + Ls * q
            c.text_centered(lab, ys - h * 0.045, size=h * 0.016, color=(0.75, 0.78, 0.88), alpha=0.55, cx=xq)
        # ---- the big fraction = note
        a_, b_ = FRAC[cur[2]]
        lab = "1" if a_ == b_ else f"{a_}/{b_}"
        pop = math.exp(-age / 0.10)
        c.text_centered(f"{lab}  =  {cur[2]}", h * 0.315, size=w * 0.11 * (1 + 0.12 * pop), color=col, alpha=1.0)
        c.text_centered("PYTHAGORAS · ~500 BC", h * 0.205, size=h * 0.015, color=GOLD, alpha=0.85)
        c.text_centered("shorter string = higher note", h * 0.755, size=w * 0.048, color=(0.95, 0.94, 0.98),
                        alpha=0.92)
        c.text_centered("whole string = C · 2/3 = G · 3/5 = A", h * 0.79, size=w * 0.033, color=(0.75, 0.78, 0.88),
                        alpha=0.85, bold=False)
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
    """Piano: a soft bass note per bar on pass 1, full chords (2 beats each) on pass 2."""
    out = []
    for p in range(PASSES):
        for k, ch in enumerate(CHORDS):
            t0 = p * T_PASS + k * 2 * B
            if p == 0:
                out.append({"t": round(t0 + 0.01, 4), "note": ch[0] - 12, "gain": 0.16, "x": layout.w / 2})
            else:
                for j, m in enumerate(ch):
                    out.append({"t": round(t0 + 0.01 + 0.015 * j, 4), "note": m, "gain": 0.15, "x": layout.w / 2})
                out.append({"t": round(t0 + 0.01, 4), "note": ch[0] - 12, "gain": 0.18, "x": layout.w / 2})
    return out


def pluck_bed():
    """Karplus-Strong plucked string: frequency = F_C / fraction (shorter string, higher note)."""
    sr = audio.SR
    n = int(round(T_LOOP * sr))
    out = np.zeros(n + sr * 2)
    rng = np.random.default_rng(7)
    for t0, dur, nm in NOTES:
        if t0 < 0 or t0 >= T_LOOP:
            continue
        f = F_C / frac(nm)
        p = max(2, int(round(sr / f - 0.5)))
        L = int((dur + 1.2) * sr)
        y = np.zeros(L + p + 1)
        burst = rng.uniform(-1, 1, p)
        burst = np.convolve(burst, np.ones(3) / 3, mode="same")     # softer pick
        y[:p] = burst
        decay = 0.996
        for s in range(p, L, p):
            e = min(L, s + p)
            seg = y[s - p:e - p]
            seg1 = y[s - p + 1:e - p + 1]
            y[s:e] = decay * 0.5 * (seg + seg1[: len(seg)])
        y = y[:L]
        tt = np.arange(L) / sr
        y *= np.clip((dur + 0.05 - tt) / 0.15, 0.25, 1.0)          # damp a little at the next note
        i0 = int(t0 * sr)
        out[i0:i0 + L] += y
    tail = out[n:]
    out = out[:n]
    out[: len(tail)] += tail                                         # ring-out folds over the loop seam
    return (0.09 * out).astype(np.float32)


def _worker(o, sim, label, rule):
    layout = get_layout(o)
    name = f"{SCENE}_{label}_{layout.tag}"
    video = studio.OUT_DIR / f"{name}_silent.mp4"
    d = render(layout, sim, video, rule)
    kit.deliver_loop(SCENE, name, layout, video, build_events(sim, layout), d, voice="piano", bed=pluck_bed(),
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
    print(f"[{SCENE}] {T_LOOP:.2f}s")
    kit.fan_out(_worker, (sim, label, rule), SCENE)


if __name__ == "__main__":
    main()
