"""MATH BEAT v2 — 4 equations build a DARK TRAP / PHONK beat on ONE graph (pitch vs beats), countdown #4 → #1 THE DROP.

Owner-supplied brief (2026-10-18): minimalist 2-D math UI on pitch black, a static pitch-vs-beats graph, glowing nodes
plotting each layer in real time, formulas on screen, sound pitch-mapped to the curves, ending on a drop. v2 (owner:
v1 sounded like our math_song): a different genre — 140 BPM half-time, D harmonic minor (Dm – B♭ – Gm – A, the A major
chord's C# = the "villain" tension), a cowbell-style lead on a 3-3-2 rhythm, trap hat rolls whose speed doubles, and
distorted 808s that SLIDE between notes (the slide is an exponential curve you can see).
  #4 The Cowbell Melody (cyan)  y = round(3·sin(πx/2) − 2·cos(3πx/4))  → D harmonic minor, 3-3-2 16ths
  #3 The Hat Rolls    (purple)  hits per beat = 2^(floor(x) mod 3 + 1)  → 2, 4, 8 hits per beat
  #2 The 808 Slide      (gold)  y = a + (b − a)·(1 − e^(−8t))            → each 808 glides into the next root
  #1 THE DROP          (green)  everything + clap on beat 3 + cowbell an octave up
8 bars at 140 BPM = 13.7 s: bars 1-2 melody · 3-4 +hats · 5-6 the slide (half a beat of silence) · 7-8 the drop.
Reference taken for the generic format only; equations, melody, harmony, sounds and title are ours (synthesised, no
samples); the reference's series name is never used.
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

SCENE = "math_beat"
BPM = 140.0
BEAT = 60.0 / BPM
BARS = 8
T_LOOP = BARS * 4 * BEAT                                   # 13.7 s
CYAN, PURPLE, GOLD, GREEN, WHITE = (0.3, 0.9, 1.0), (0.75, 0.5, 1.0), (1.0, 0.8, 0.3), (0.35, 1.0, 0.55), (1, 1, 1)
ROOTS = [38, 34, 31, 33]                                  # D2 B♭1 G1 A1 (808 roots, one per bar)
CHORDS = [(50, 53, 57), (46, 50, 53), (43, 46, 50), (45, 49, 52)]   # Dm B♭ Gm A (C#!)
SCALE = [62, 64, 65, 67, 69, 70, 73, 74, 76, 77, 79, 81, 82, 85, 86]  # D harmonic minor from D4
RHYTHM = [0, 3, 6, 8, 11, 14]                             # 16th positions in a bar: the 3-3-2 phonk groove
HAT_Y = 92                                                # hats sit on the top row of the graph


def bar_of(x):
    return int(x // 4) % 4


def bell_note(x):
    d = int(round(3 * math.sin(math.pi * x / 2) - 2 * math.cos(3 * math.pi * x / 4)))
    return SCALE[min(len(SCALE) - 1, max(0, 6 + d))]


def build():
    ev = []
    for bar in range(BARS):
        for k in RHYTHM:                                    # cowbell melody (silent in the half beat before the drop)
            x = bar * 4 + k / 4
            if 23.5 <= x < 24:
                continue
            m = bell_note(x)
            ev.append(("bell", x, m))
            if bar >= 6:
                ev.append(("bell8", x, m + 12))
        if 2 <= bar:                                        # hats: hits per beat = 2^(floor(x) mod 3 + 1)
            for b in range(4):
                xb = bar * 4 + b
                n = 2 ** (int(xb) % 3 + 1)
                for j in range(n):
                    x = xb + j / n
                    if 23.5 <= x < 24:
                        continue
                    ev.append(("hat", x, HAT_Y))
        if bar >= 6:
            ev.append(("clap", bar * 4 + 2.0, 0))           # half-time: the clap on beat 3
    # 808s: (onset, root, end, slide-to) — bars 5-6 simple, the drop syncopated with octave jumps
    s808 = []
    for bar in (4, 5):
        r, nxt = ROOTS[bar % 4], ROOTS[(bar + 1) % 4]
        s808.append((bar * 4 + 0.0, r, bar * 4 + 2.5, None))
        end = bar * 4 + (3.5 if bar == 5 else 4.0)
        s808.append((bar * 4 + 2.5, r + 12, end, nxt if bar == 4 else r - 5))   # an octave up, diving down
    for bar in (6, 7):
        r, nxt = ROOTS[bar % 4], ROOTS[(bar + 1) % 4]
        s808 += [(bar * 4 + 0.0, r, bar * 4 + 1.5, None), (bar * 4 + 1.5, r, bar * 4 + 2.5, None),
                 (bar * 4 + 2.5, r + 12, bar * 4 + 3.25, r), (bar * 4 + 3.25, r, bar * 4 + 4.0, nxt if bar == 6 else None)]
    for (x0, m, x1, to) in s808:
        ev.append(("808", x0, m))
    return sorted(ev, key=lambda e: e[1]), s808


EV, S808 = build()
COL = {"bell": CYAN, "bell8": CYAN, "hat": PURPLE, "808": GOLD}
LAYERS = [
    ("#4", "The Cowbell Melody", "y = round(3·sin(πx/2) − 2·cos(3πx/4))", CYAN),
    ("#3", "The Hat Rolls", "hits per beat = 2^(floor(x) mod 3 + 1)", PURPLE),
    ("#2", "The 808 Slide", "y = a + (b − a)·(1 − e^(−8t))", GOLD),
    ("#1", "THE DROP", "all four at once · clap on beat 3", GREEN),
]


def p808(x):
    """The 808's pitch at beat x (None = silent): flat, then an exponential glide into the target."""
    for (x0, m, x1, to) in S808:
        if x0 <= x < x1:
            if to is None:
                return float(m)
            gl = min(0.75, x1 - x0)
            ts = x1 - gl
            if x < ts:
                return float(m)
            u = (x - ts) / gl
            return m + (to - m) * (1 - math.exp(-8 * u)) / (1 - math.exp(-8))
    return None


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
        ctx.set_source_rgb(0, 0, 0)
        ctx.paint()
        xb = t / BEAT
        li = min(3, int(xb // 8))
        win0 = li * 8
        gx0, gx1, gy0, gy1 = w * 0.13, w * 0.95, h * 0.30, h * 0.70
        P0, P1 = 24, 96
        kick = 0.0                                          # the drop pumps the axes with the 808
        if li == 3:
            for (x0, m, x1, to) in S808:
                if x0 <= xb < x1:
                    kick = math.exp(-(xb - x0) * BEAT / 0.12)

        def X(x):
            return gx0 + (x - win0) / 8 * (gx1 - gx0)

        def Y(m):
            return gy1 - (m - P0) / (P1 - P0) * (gy1 - gy0)

        grid = [(X(win0 + b), gy0, X(win0 + b), gy1) for b in range(9)]
        grid += [(gx0, Y(m), gx1, Y(m)) for m in range(P0, P1 + 1, 12)]
        c.lines(grid, (0.35, 0.4, 0.6), width=1.2, alpha=0.35 + 0.25 * kick)
        c.lines([(gx0, gy0 - h * 0.01, gx0, gy1), (gx0, gy1, gx1 + w * 0.01, gy1)], (0.85, 0.88, 1.0), width=2.5,
                alpha=0.8)
        for m, nm in ((24, "C1"), (36, "C2"), (48, "C3"), (60, "C4"), (72, "C5"), (84, "C6"), (96, "C7")):
            c.text_centered(nm, Y(m) + h * 0.006, size=w * 0.024, color=(0.7, 0.75, 0.9), bold=False, cx=gx0 - w * 0.05)
        for b in range(0, 9, 2):
            c.text_centered(str(win0 + b), gy1 + h * 0.022, size=w * 0.024, color=(0.7, 0.75, 0.9), bold=False,
                            cx=X(win0 + b))
        c.text_centered("pitch", gy0 - h * 0.02, size=w * 0.026, color=(0.7, 0.75, 0.9), bold=False, cx=gx0)
        c.text_centered("beats", gy1 + h * 0.045, size=w * 0.026, color=(0.7, 0.75, 0.9), bold=False, cx=(gx0 + gx1) / 2)
        # the 808 pitch curve (with its slides) — gold in #2, green in the drop
        if li >= 2:
            col = GOLD if li == 2 else GREEN
            seg, segs = [], []
            for j in range(0, 801):
                x = win0 + 8 * j / 800
                if x > xb:
                    break
                p = p808(x)
                if p is None:
                    if len(seg) > 1:
                        segs.append(seg)
                    seg = []
                    continue
                seg.append((X(x), Y(p)))
            if len(seg) > 1:
                segs.append(seg)
            c.polylines(segs, col, width=12, alpha=0.16 + 0.2 * kick)
            c.polylines(segs, col, width=3.5, alpha=0.95)
        # melody line + nodes
        mel = [(X(x), Y(m)) for k_, x, m in EV if k_ == "bell" and win0 <= x < win0 + 8 and x <= xb]
        if len(mel) > 1:
            c.polylines([mel], CYAN, width=7, alpha=0.15)
            c.polylines([mel], CYAN, width=2.2, alpha=0.75)
        for kind, x, m in EV:
            if not (win0 <= x < win0 + 8) or x > xb or kind == "clap":
                continue
            age = (xb - x) * BEAT
            col = GREEN if (kind == "808" and li == 3) else COL[kind]
            px, py = X(x), Y(m)
            r = w * (0.006 if kind == "hat" else (0.014 if kind == "808" else 0.011))
            pop = math.exp(-age / 0.15)
            c.circle(px, py, r * (1 + 0.8 * pop), col, alpha=0.95 if kind != "bell8" else 0.6)
            if pop > 0.05:
                c.glow(px, py, r * 4, col, strength=0.7 * pop, reach=2.4)
                c.ring(px, py, r * (1.5 + 5 * (1 - pop)), col, width=2, alpha=0.6 * pop)
        for kind, x, m in EV:                               # the clap: a white flash ring on the beat-3 line
            if kind == "clap" and win0 <= x <= xb < x + 1.0:
                u = (xb - x) * BEAT / 0.4
                if u < 1:
                    c.ring(X(x), (gy0 + gy1) / 2, w * (0.05 + 0.25 * u), WHITE, width=3, alpha=0.5 * (1 - u))
        c.lines([(X(xb), gy0, X(xb), gy1)], (1, 1, 1), width=2, alpha=0.5)
        num, name, formula, col = LAYERS[li]
        k = smooth((xb - win0) / 1.0)
        c.text_centered(f"{num}  {name}", h * 0.215, size=w * 0.06, color=col, alpha=k)
        c.text_centered(formula, h * 0.25, size=w * 0.036, color=(0.95, 0.95, 1.0), alpha=k, bold=False, max_w=w * 0.94)
        for j, (n_, _, _, cc) in enumerate(LAYERS):
            cx_ = w * (0.32 + 0.12 * j)
            on = j <= li
            ctx.new_path()
            ctx.arc(cx_, h * 0.775, w * 0.03 * (1 + 0.15 * kick * (j == 3)), 0, 2 * math.pi)
            ctx.set_source_rgba(*(cc if on else (0.3, 0.3, 0.38)), 0.9 if j == li else (0.45 if on else 0.4))
            ctx.fill()
            c.text_centered(n_, h * 0.782, size=w * 0.026, color=(0.02, 0.02, 0.05), cx=cx_)
        c.text_centered("4 equations · 1 dark beat", h * 0.82, size=w * 0.03, color=(0.7, 0.72, 0.85), bold=False)
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


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def track():
    sr = audio.SR
    n = int(round(T_LOOP * sr))
    out = np.zeros(n)
    rng = np.random.default_rng(5)

    def add(t0, sig, g):
        i0 = int(round(t0 * sr)) % n
        idx = (np.arange(len(sig)) + i0) % n
        np.add.at(out, idx, g * sig)

    def sq(ph, harm=5):
        return sum(np.sin(k * ph) / k for k in range(1, harm + 1, 2))

    for kind, x, m in EV:
        t0 = x * BEAT
        if kind in ("bell", "bell8"):                       # cowbell-style: two square tones a 1.48 ratio apart
            tv = np.arange(int(0.3 * sr)) / sr
            f0 = hz(m)
            sig = sq(2 * np.pi * f0 * tv) + 0.8 * sq(2 * np.pi * f0 * 1.48 * tv)
            env = np.clip(tv / 0.002, 0, 1) * (0.7 * np.exp(-tv / 0.035) + 0.3 * np.exp(-tv / 0.16))
            add(t0, sig * env, 0.10 if kind == "bell" else 0.05)
        elif kind == "hat":
            tv = np.arange(int(0.05 * sr)) / sr
            nz = np.diff(np.concatenate([[0], rng.standard_normal(len(tv))]))
            nz = np.diff(np.concatenate([[0], nz]))
            add(t0, nz * np.exp(-tv / 0.012), 0.025)
        elif kind == "clap":
            tv = np.arange(int(0.25 * sr)) / sr
            nz = rng.standard_normal(len(tv))
            nz = nz - np.convolve(nz, np.ones(6) / 6, mode="same")
            body = np.sin(2 * np.pi * 190 * tv) * np.exp(-tv / 0.05)
            add(t0, nz * np.exp(-tv / 0.07) * (1 + 0.9 * np.exp(-((tv - 0.012) / 0.004) ** 2)) + 0.6 * body, 0.17)
    # 808s with their slides: one continuous phase per note, pitch from p808, distorted, a click on the onset
    for (x0, m, x1, to) in S808:
        dur = (x1 - x0) * BEAT
        tv = np.arange(int(dur * sr)) / sr
        xs = x0 + tv / BEAT
        pm = np.array([p808(min(x, x1 - 1e-6)) for x in xs[::64]])
        pm = np.interp(np.arange(len(tv)), np.arange(0, len(tv), 64)[:len(pm)], pm)
        fr = 440.0 * 2 ** ((pm - 69) / 12)
        fr = fr * (1 + 1.5 * np.exp(-tv / 0.02))
        sig = np.sin(2 * np.pi * np.cumsum(fr) / sr)
        amp = np.clip(tv / 0.003, 0, 1) * np.exp(-tv / 0.9) * np.clip((dur - tv) / 0.015, 0, 1)
        sig = np.tanh(2.6 * sig) * amp
        click = np.sin(2 * np.pi * 1800 * tv) * np.exp(-tv / 0.004)
        add(x0 * BEAT, sig + 0.3 * click, 0.42)
    # a dark pad on the chords + a reverse swell into the drop
    for bar in range(BARS):
        ch = CHORDS[bar % 4]
        tv = np.arange(int(4 * BEAT * sr)) / sr
        sig = sum(np.sin(2 * np.pi * hz(mm + 12) * tv) for mm in ch) / 3
        sig *= np.clip(tv / 0.4, 0, 1) * np.clip((4 * BEAT - tv) / 0.3, 0, 1)
        add(bar * 4 * BEAT, sig, 0.03)
    t_a, t_b = 20 * BEAT, 23.5 * BEAT
    tv = np.arange(int((t_b - t_a) * sr)) / sr
    nz = np.convolve(rng.standard_normal(len(tv)), np.ones(4) / 4, mode="same")
    add(t_a, nz * (tv / tv[-1]) ** 3, 0.10)
    return out.astype(np.float32)


def _worker(o, sim, label, rule):
    layout = get_layout(o)
    name = f"{SCENE}_{label}_{layout.tag}"
    video = studio.OUT_DIR / f"{name}_silent.mp4"
    d = render(layout, sim, video, rule)
    kit.deliver_loop(SCENE, name, layout, video, [], d, voice="piano", bed=track(), peak_db=-6.0)


def main():
    label, rule = arg("--label", "v2"), arg("--rule", "")
    studio.OUT_DIR.mkdir(exist_ok=True)
    sim = simulate()
    if kit.has("--still"):
        layout = get_layout(kit.orients()[0])
        f = int(arg("--frame", "0"))
        png = studio.OUT_DIR / f"{SCENE}_{label}_f{f}_{layout.tag}.png"
        render(layout, sim, png, rule, still_frame=f)
        print(f"[{SCENE}] -> {png}")
        return
    print(f"[{SCENE}] {T_LOOP:.2f}s  {len(EV)} events")
    kit.fan_out(_worker, (sim, label, rule), SCENE)


if __name__ == "__main__":
    main()
