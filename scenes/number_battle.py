"""NUMBER BATTLE — "π vs φ vs e: which plays the best song?" (famous-numbers-play-famous-songs series).

Each number gets 8 beats over Pachelbel's Canon chords (PD; our own synthesis): its digits play in 8th notes,
digit d → note d of the current chord's two-octave voicing. A piano-roll lane shows every note (row = digit), so you
SEE each number's melody. π (rounds 1), φ (2), e (3); then all three symbols side by side: "Which one won?".
Audio (original): glass notes for the digits, cello-like Canon bass + string pad, a final D chord.
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
import pi_canon as PC  # noqa: E402  (digit generators)

SCENE = "number_battle"
BPM = 100.0
B = 60.0 / BPM
ROUND = 8 * B                                                       # 4.8 s per number
T0 = 0.15
T_END_ROUND = T0 + 3 * ROUND
T_LOOP = T_END_ROUND + 1.9
GOLD = (1.0, 0.82, 0.40)
NUMS = [("π", "pi", (1.0, 0.55, 0.35)), ("φ", "phi", (1.0, 0.82, 0.40)), ("e", "e", (0.45, 0.80, 1.0))]
DIGITS = [PC.pi_digits(20), PC.const_digits("phi", 20), PC.const_digits("e", 20)]
CHORDS = [(62, 66, 69), (61, 64, 69), (62, 66, 71), (61, 66, 69), (62, 67, 71), (62, 66, 69), (62, 67, 71), (61, 64, 69)]
ROOTS = [38, 33, 35, 30, 31, 26, 31, 33]
NAMES = ["D", "A", "Bm", "F#m", "G", "D", "G", "A"]


def chord_idx(t):
    """Canon chords, 2 beats each, continuing across the rounds (cycle of 8)."""
    return int(max(0.0, t - T0) // (2 * B)) % 8


def voicing(ci):
    tri = CHORDS[ci]
    v = [m - 12 for m in tri] + list(tri) + [m + 12 for m in tri] + [tri[0] + 24]
    return sorted(v)[:10]


def notes():
    out = []
    for r in range(3):
        for k in range(16):
            t = T0 + r * ROUND + k * B / 2
            d = DIGITS[r][k]
            out.append((t, r, k, d, voicing(chord_idx(t))[d]))
    return out


NOTES = notes()


def simulate():
    return {"nf": int(round(T_LOOP * FPS))}


class Scene:
    def __init__(self, layout, sim):
        self.L, self.sim = layout, sim
        self.canvas = Canvas(layout.w, layout.h, studio.render_scale())

    def draw(self, f, rule):
        L, c = self.L, self.canvas
        t = f * DT
        self.state(t)
        k = smooth((t - (T_LOOP - 0.5)) / 0.45)              # cross-fade into frame 0: a seamless loop
        if k > 0:
            c.ctx.push_group()
            self.state(0.0)
            c.ctx.pop_group_to_source()
            c.ctx.paint_with_alpha(k)
        if rule:
            c.caption(rule, alpha=1.0, layout=L)
        c.watermark(L)

    def state(self, t):
        L, c = self.L, self.canvas
        w, h = L.w, L.h
        ctx = c.ctx
        g = cairo.RadialGradient(w / 2, h * 0.45, 0, w / 2, h * 0.45, max(w, h) * 0.7)
        g.add_color_stop_rgb(0.0, 0.08, 0.06, 0.12)
        g.add_color_stop_rgb(1.0, 0.01, 0.01, 0.02)
        ctx.set_source(g)
        ctx.paint()
        r_now = min(2, int(max(0.0, t - T0) // ROUND))
        final = t >= T_END_ROUND
        # the three contenders across the top; the active one is big and lit
        for r, (sym, _, col) in enumerate(NUMS):
            x = w * (0.22 + 0.28 * r)
            active = (r == r_now and not final)
            sz = w * (0.16 if active else 0.10)
            if final:
                sz = w * 0.15 * (1 + 0.06 * math.sin(t * 6 + r * 2))
            a = 1.0 if (active or final) else 0.35
            if active or final:
                c.glow(x, h * 0.245, w * 0.07, col, strength=0.5, reach=3)
            c.text_centered(sym, h * 0.27, size=sz, color=col, alpha=a, cx=x)
        # the piano-roll lane: row = digit (0 bottom … 9 top)
        x0, x1, y0, y1 = w * 0.08, w * 0.92, h * 0.33, h * 0.62
        rowh = (y1 - y0) / 10
        for d in range(10):
            yy = y1 - (d + 0.5) * rowh
            c.lines([(x0, yy, x1, yy)], (0.7, 0.72, 0.85), width=1, alpha=0.12)
            c.text_centered(str(d), yy + rowh * 0.3, size=rowh * 0.7, color=(0.7, 0.72, 0.85), alpha=0.5, cx=x0 - w * 0.03)
        xp = w * 0.80                                              # playhead
        speed = (xp - x0) / (ROUND * 0.95)
        c.lines([(xp, y0, xp, y1)], (1, 1, 1), width=2, alpha=0.4)
        for (tn, r, k, d, m) in NOTES:
            if final or r != r_now or tn > t:
                continue
            x = xp - (t - tn) * speed
            if x < x0:
                continue
            yy = y1 - (d + 0.5) * rowh
            col = NUMS[r][2]
            age = t - tn
            pop = math.exp(-age / 0.12)
            ctx.rectangle(x - w * 0.018, yy - rowh * 0.38, w * 0.036 + speed * B / 2 * 0.8 * 0, rowh * 0.76)
            ctx.set_source_rgba(*col, 0.55 + 0.45 * pop)
            ctx.fill()
            if pop > 0.05:
                c.glow(x, yy, rowh * 0.6, col, strength=0.8 * pop, reach=2.5)
        # digit ribbon of the active number + the chord
        if not final:
            sym, _, col = NUMS[r_now]
            played = [n for n in NOTES if n[1] == r_now and n[0] <= t]
            digs = DIGITS[r_now][: len(played)]
            txt = f"{sym} = " + (str(digs[0]) + "." + "".join(map(str, digs[1:])) if digs else "")
            c.text_centered(txt, h * 0.685, size=w * 0.058, color=col, max_w=w * 0.94)
            c.text_centered(f"round {r_now + 1} of 3  ·  chord {NAMES[chord_idx(t)]}", h * 0.73, size=w * 0.034,
                            color=(0.8, 0.82, 0.9), alpha=0.85, bold=False)
        else:
            a = smooth((t - T_END_ROUND) / 0.3)
            c.text_centered("Which one won?", h * 0.52, size=w * 0.09, color=(1, 1, 1), alpha=a)
            c.text_centered("comment  π,  φ  or  e", h * 0.585, size=w * 0.05, color=GOLD, alpha=a)
        c.text_centered("Pachelbel's Canon chords · each digit = one note", h * 0.205, size=h * 0.0145, color=GOLD,
                        alpha=0.85)


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
    out = []
    for (tn, r, k, d, m) in NOTES:
        out.append({"t": round(tn + 0.004, 4), "note": m + 12, "gain": 0.40, "x": layout.w * (0.25 + 0.25 * r)})
    for j, m in enumerate((50, 57, 62, 66, 69, 74)):
        out.append({"t": round(T_END_ROUND + 0.04 * j, 4), "note": m, "gain": 0.36, "x": layout.w / 2})
    return sorted(out, key=lambda e: e["t"])


def bed():
    sr = audio.SR
    n = int(round(T_LOOP * sr))
    out = np.zeros(n)
    for k in range(13):
        t0 = T0 + k * 2 * B
        if t0 >= T_LOOP:
            break
        ci = k % 8 if t0 < T_END_ROUND else 0
        L = 2 * B if t0 < T_END_ROUND else T_LOOP - t0
        tt = np.arange(int(L * sr)) / sr
        ph = 2 * np.pi * audio.midi_to_hz(ROOTS[ci]) * tt
        cello = (np.sin(ph) + 0.5 * np.sin(2 * ph) + 0.25 * np.sin(3 * ph)) * np.clip(tt / 0.05, 0, 1) * np.exp(-tt * 0.6)
        pad = sum(np.sin(2 * np.pi * audio.midi_to_hz(m - 12) * tt) for m in CHORDS[ci]) / 3
        pad *= np.clip(tt / 0.2, 0, 1) * np.clip((L - tt) / 0.25, 0, 1)
        seg = 0.32 * cello + 0.16 * pad
        i0 = int(t0 * sr)
        i1 = min(n, i0 + len(seg))
        out[i0:i1] += seg[: i1 - i0]
    return (0.06 * out).astype(np.float32)


def _worker(o, sim, label, rule):
    layout = get_layout(o)
    name = f"{SCENE}_{label}_{layout.tag}"
    video = studio.OUT_DIR / f"{name}_silent.mp4"
    d = render(layout, sim, video, rule)
    kit.deliver_loop(SCENE, name, layout, video, build_events(sim, layout), d, voice="glassharp", bed=bed())


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
