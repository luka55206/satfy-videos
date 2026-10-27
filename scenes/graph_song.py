"""GRAPH SONG — "This math graph plays Ode to Joy" (Beethoven, 1824: public domain).

A pen draws a smooth staircase graph y = Σ hₖ·σ(x − k): each step's height IS a note of the melody, and the sound
is the height under the pen (a slide-whistle voice with glides between notes), with soft piano chords underneath.
The y-axis is labelled with note names (C D E F G) like a staff, so you SEE the tune as you hear it.
Phrase 1 is drawn on the upper graph, phrase 2 on the lower one; the last frame shows the whole tune as a graph.
Original synthesis (the composition is public domain; the recording is ours).
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

SCENE = "graph_song"
BPM = 112.0
B = 60.0 / BPM
NOTE = {"C": 60, "D": 62, "E": 64, "F": 65, "G": 67}
DEG = {60: 0, 62: 1, 64: 2, 65: 3, 67: 4}             # staff height = scale step (higher = higher pitch)
P1 = [("E", 1), ("E", 1), ("F", 1), ("G", 1), ("G", 1), ("F", 1), ("E", 1), ("D", 1),
      ("C", 1), ("C", 1), ("D", 1), ("E", 1), ("E", 1.5), ("D", 0.5), ("D", 2)]
P2 = [("E", 1), ("E", 1), ("F", 1), ("G", 1), ("G", 1), ("F", 1), ("E", 1), ("D", 1),
      ("C", 1), ("C", 1), ("D", 1), ("E", 1), ("D", 1.5), ("C", 0.5), ("C", 2)]
CHORDS = [(48, 55, 64), (43, 55, 62), (48, 55, 64), (43, 55, 62), (48, 55, 64), (43, 55, 62), (48, 55, 64),
          (43, 50, 59), (48, 55, 64)]
T_PHRASE = 16 * B
T_HOLD = 1.6
T_LOOP = 2 * T_PHRASE + T_HOLD
COLS = [(1.00, 0.55, 0.40), (0.45, 0.85, 1.00)]
GOLD = (1.0, 0.82, 0.40)


def notes():
    out, t = [], 0.0
    for ph, mel in enumerate((P1, P2)):
        for nm, d in mel:
            out.append((t, d * B, NOTE[nm], nm, ph))
            t += d * B
    return out


NOTES = notes()


def height_at(t):
    """The graph: a smooth staircase through the note heights (y in semitones above C)."""
    y = None
    for t0, L, m, nm, ph in NOTES:
        if t >= t0:
            y = (DEG[m], t0)
    if y is None:
        return 2.0
    prev = [n for n in NOTES if n[0] < y[1]]
    m_prev = DEG[prev[-1][2]] if prev else y[0]
    k = smooth((t - y[1]) / 0.06)
    return m_prev + (y[0] - m_prev) * k


def simulate():
    return {"nf": int(round(T_LOOP * FPS))}


class Scene:
    def __init__(self, layout, sim):
        self.L, self.sim = layout, sim
        self.canvas = Canvas(layout.w, layout.h, studio.render_scale())

    def graph(self, ph, t, y_mid, gh):
        c, L = self.canvas, self.L
        w, h = L.w, L.h
        x0, x1 = w * 0.14, w * 0.94
        t0 = ph * T_PHRASE

        def P(tt, y):
            return x0 + (x1 - x0) * (tt - t0) / T_PHRASE, y_mid + gh / 2 - gh * y / 4.0

        for nm, m in NOTE.items():                         # staff lines with note names
            yy = P(t0, DEG[m])[1]
            c.lines([(x0, yy, x1, yy)], (0.75, 0.78, 0.88), width=1.2, alpha=0.18)
            c.text_centered(nm, yy + h * 0.008, size=h * 0.020, color=(0.80, 0.82, 0.92), alpha=0.8, cx=w * 0.08)
        c.lines([(x0, y_mid - gh * 0.62, x0, y_mid + gh * 0.62)], (0.75, 0.78, 0.88), width=2, alpha=0.4)
        te = min(max(t, t0), t0 + T_PHRASE)
        if te <= t0:
            return None
        ts = np.linspace(t0, te, max(2, int(400 * (te - t0) / T_PHRASE)))
        pts = [P(x, height_at(x)) for x in ts]
        col = COLS[ph]
        fa = 1 - smooth((t - 2 * T_PHRASE - 0.5) / 1.0)      # the finished tune fades out -> empty staff = frame 0
        c.polylines([pts], col, width=18, alpha=0.12 * fa)
        c.polylines([pts], col, width=5, alpha=0.95 * fa)
        return pts[-1] if t < t0 + T_PHRASE else None

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
        tip = None
        for ph, ym in ((0, h * 0.355), (1, h * 0.565)):
            p = self.graph(ph, t, ym, h * 0.13)
            if p is not None:
                tip = (p, ph)
        cur = [n for n in NOTES if n[0] <= t]
        if tip is not None and cur:
            (px, py), ph = tip
            n = cur[-1]
            age = t - n[0]
            c.glow(px, py, 9, COLS[ph], strength=0.8, reach=4)
            c.circle(px, py, 8, (1, 1, 1), alpha=0.95)
            pop = math.exp(-age / 0.12)
            c.text_centered(f"♪ {n[3]}", py - h * 0.035 - 20 * pop, size=h * 0.026 * (1 + 0.3 * pop), color=COLS[ph],
                            cx=px)
        c.text_centered("y = Σ h(k) · σ(x − k)", h * 0.715, size=w * 0.05, color=(0.95, 0.94, 0.98), alpha=0.9,
                        bold=False)
        c.text_centered("pitch = height of the graph", h * 0.752, size=w * 0.032, color=(0.75, 0.78, 0.88),
                        alpha=0.8, bold=False)
        c.text_centered("FAMOUS SONGS · BEETHOVEN, 1824", h * 0.205, size=h * 0.015, color=GOLD, alpha=0.85)
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
    """Soft piano chords: one per bar (4 beats), C / G alternating, final C."""
    out = []
    for k in range(9):
        t0 = k * 4 * B if k < 8 else 2 * T_PHRASE
        for j, m in enumerate(CHORDS[k]):
            out.append({"t": round(t0 + 0.01 + 0.012 * j, 4), "note": m, "gain": 0.20, "x": layout.w / 2})
    return out


def whistle_bed():
    """The melody, as the height under the pen: a slide-whistle-like sine with glides + vibrato."""
    sr = audio.SR
    n = int(round(T_LOOP * sr))
    tv = np.arange(n) / sr
    pitch = np.zeros(n)
    amp = np.zeros(n)
    for t0, L, m, nm, ph in NOTES:
        i0, i1 = int(t0 * sr), min(n, int((t0 + L) * sr))
        pitch[i0:i1] = m + 12
        seg = np.arange(i1 - i0) / sr
        amp[i0:i1] = np.clip(seg / 0.025, 0, 1) * (1 - 0.35 * np.clip((seg - (L - 0.07)) / 0.07, 0, 1))
    last = NOTES[-1]
    i_end = int((last[0] + last[1]) * sr)
    pitch[i_end:] = last[2] + 12
    amp[i_end:] = np.clip(1 - (tv[i_end:] - tv[i_end]) / 1.2, 0, 1) * 0.9
    k = int(0.035 * sr)
    c = np.cumsum(np.concatenate([[0.0], pitch]))
    idx = np.arange(n)
    lo, hi = np.clip(idx - k // 2, 0, n), np.clip(idx - k // 2 + k, 0, n)
    pitch = (c[hi] - c[lo]) / np.maximum(hi - lo, 1)
    vib = 0.18 * np.sin(2 * np.pi * 5.6 * tv)
    ph = 2 * np.pi * np.cumsum(440 * 2 ** ((pitch + vib - 69) / 12)) / sr
    sig = np.sin(ph) + 0.12 * np.sin(2 * ph) + 0.05 * np.sin(3 * ph)
    return (0.11 * amp * sig).astype(np.float32)


def _worker(o, sim, label, rule):
    layout = get_layout(o)
    name = f"{SCENE}_{label}_{layout.tag}"
    video = studio.OUT_DIR / f"{name}_silent.mp4"
    d = render(layout, sim, video, rule)
    kit.deliver_loop(SCENE, name, layout, video, build_events(sim, layout), d, voice="piano", bed=whistle_bed(),
                     peak_db=-6.0)


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
    print(f"[{SCENE}] {T_LOOP:.2f}s")
    kit.fan_out(_worker, (sim, label, rule), SCENE)


if __name__ == "__main__":
    main()
