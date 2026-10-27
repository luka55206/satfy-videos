"""PI MUSIC — the digits of pi, played as music and drawn as string art.

A circle split into 10 coloured arcs (digits 0-9). Each digit of pi (3.14159…) plays a note (digit -> C major
scale) and a curved string is drawn from the previous digit's arc to this digit's arc. The strings accumulate into
string art; digits come slowly at first and faster and faster (500 digits). The big current digit and a ticker of
pi's digits show what is playing. Loop: the strings fade back to the empty circle of frame 0.
Audio: original synthesis only (digit notes on the glass voice, a chord at the end, a periodic pad).
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

SCENE = "pi_music"
N_DIG = 500
CANON = arg("--canon", "0") == "1"    # v2: pi's digits write the melody over Pachelbel's Canon (PD, ~1680)
CBPM = 78.0
CB = 60.0 / CBPM
# Canon in D: D A Bm F#m G D G A, two beats each (8 chords = 16 beats = one cycle)
CANON_ROOTS = [38, 33, 35, 30, 31, 26, 31, 33]
CANON_CHORDS = [(62, 66, 69), (61, 64, 69), (62, 66, 71), (61, 66, 69), (62, 67, 71), (62, 66, 69), (62, 67, 71),
                (61, 64, 69)]
CANON_NAMES = ["D", "A", "Bm", "F#m", "G", "D", "G", "A"]
DIV = [2, 2, 2, 2, 4, 4, 4, 4, 8, 8, 8, 8, 16, 16, 32, 32]   # digits per beat, beat by beat (8ths → 16ths → 32nds → 64ths)
if CANON:
    T_RUN, T_HOLD, T_FADE = 16 * CB, 2 * CB, 1.0
else:
    T_RUN, T_HOLD, T_FADE = 13.5, 1.2, 1.0
T_LOOP = T_RUN + T_HOLD + T_FADE
SCALE = [60, 62, 64, 65, 67, 69, 71, 72, 74, 76]          # digit 0..9 -> C major, 1.5 octaves
NOTE_NAMES = ["C", "D", "E", "F", "G", "A", "B", "C", "D", "E"]
GOLD = (1.0, 0.82, 0.40)


def pi_digits(n):
    """Rabinowitz-Wagon spigot: the first n digits of pi as ints (3, 1, 4, 1, 5, …)."""
    out = []
    q, r, t, k, m, x = 1, 0, 1, 1, 3, 3
    while len(out) < n:
        if 4 * q + r - t < m * t:
            out.append(m)
            q, r, m = 10 * q, 10 * (r - m * t), (10 * (3 * q + r)) // t - 10 * m
        else:
            q, r, t, k, m, x = q * k, (2 * q + r) * x, t * x, k + 1, (q * (7 * k + 2) + r * x) // (t * x), x + 2
    return out


DIG = pi_digits(N_DIG)
DIG_COL = [(0.35 + 0.65 * (0.5 + 0.5 * math.cos(2 * math.pi * (d / 10 + o))),) for d in range(10) for o in (0,)]


def dcol(d):
    h = d / 10.0
    return tuple(0.5 + 0.5 * math.cos(2 * math.pi * (h + o)) for o in (0.0, 0.33, 0.67))


def times():
    """Digit i appears at t_i: slow first (0.42 s), accelerating to ~70 digits/s."""
    u = np.linspace(0, 1, N_DIG)
    return 0.05 + (T_RUN - 0.05) * u ** 0.55          # first gaps ~0.45 s, then faster and faster


TD = times()
if CANON:
    _td = []
    for bi, dv in enumerate(DIV):
        for j in range(dv):
            _td.append(bi * CB + j * CB / dv)
    TD = np.array(_td)
    N_DIG = len(TD)


def canon_note(i):
    """pi digit i -> a note of the current Canon chord: digit picks chord tone (d % 3) and octave (d // 3)."""
    chord = CANON_CHORDS[int(TD[i] // (2 * CB)) % 8]
    d = DIG[i]
    return chord[d % 3] + 12 * min(d // 3, 2) - 12 + 12


def simulate():
    return {"nf": int(round(T_LOOP * FPS))}


class Scene:
    def __init__(self, layout, sim):
        self.L, self.sim = layout, sim
        self.canvas = Canvas(layout.w, layout.h, studio.render_scale())
        w, h = layout.w, layout.h
        self.cx, self.cy, self.R = w / 2, h * 0.475, w * 0.34
        c = self.canvas
        self.art = cairo.ImageSurface(cairo.FORMAT_ARGB32, c.pw, c.ph)
        self.actx = cairo.Context(self.art)
        self.actx.scale(c.pw / w, c.ph / h)
        self.actx.set_operator(cairo.OPERATOR_ADD)
        self.done = 0

    def anchor(self, d, i):
        a = -math.pi / 2 + (d + 0.08 + 0.84 * ((i * 0.618) % 1.0)) * 2 * math.pi / 10
        return self.cx + self.R * math.cos(a), self.cy + self.R * math.sin(a)

    def add_string(self, i, ctx, alpha):
        d0, d1 = DIG[i - 1], DIG[i]
        x0, y0 = self.anchor(d0, i - 1)
        x1, y1 = self.anchor(d1, i)
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2
        qx, qy = mx + (self.cx - mx) * 0.45, my + (self.cy - my) * 0.45
        ctx.move_to(x0, y0)
        ctx.curve_to(qx, qy, qx, qy, x1, y1)
        col = tuple((a + b) / 2 for a, b in zip(dcol(d0), dcol(d1)))
        ctx.set_source_rgba(*col, alpha)
        ctx.set_line_width(1.6)
        ctx.stroke()

    def draw(self, f, rule):
        L, c = self.L, self.canvas
        w, h = L.w, L.h
        t = f * DT
        ctx = c.ctx
        g = cairo.RadialGradient(w / 2, self.cy, 0, w / 2, self.cy, max(w, h) * 0.7)
        g.add_color_stop_rgb(0.0, 0.07, 0.06, 0.11)
        g.add_color_stop_rgb(1.0, 0.01, 0.01, 0.02)
        ctx.set_source(g)
        ctx.paint()
        n_now = int(np.searchsorted(TD, t, side="right"))
        while self.done < n_now:
            if self.done >= 1:
                self.add_string(self.done, self.actx, 0.32)
            self.done += 1
        fade = 1.0 - smooth((t - T_RUN - T_HOLD) / T_FADE)
        ctx.save()
        ctx.identity_matrix()
        ctx.set_source_surface(self.art, 0, 0)
        ctx.paint_with_alpha(fade)
        ctx.restore()
        # the newest string, bright
        if 1 <= n_now <= N_DIG and t < T_RUN + 0.3:
            age = t - TD[n_now - 1]
            self.add_string(n_now - 1, ctx, max(0.0, 0.95 - age * 2)) if n_now >= 2 else None
        # the 10 coloured digit arcs + labels
        for d in range(10):
            a0 = -math.pi / 2 + d * 2 * math.pi / 10 + 0.02
            a1 = a0 + 2 * math.pi / 10 - 0.04
            cur = n_now >= 1 and DIG[n_now - 1] == d and t < T_RUN
            pop = math.exp(-(t - TD[n_now - 1]) / 0.12) if cur else 0.0
            ctx.new_sub_path()
            ctx.arc(self.cx, self.cy, self.R + 10, a0, a1)
            ctx.set_source_rgba(*dcol(d), 0.85)
            ctx.set_line_width(14 + 10 * pop)
            ctx.stroke()
            am = (a0 + a1) / 2
            c.text_centered(str(d), self.cy + (self.R + 52) * math.sin(am) + 14, size=w * 0.05 * (1 + 0.4 * pop),
                            color=dcol(d), cx=self.cx + (self.R + 52) * math.cos(am))
        # current digit + ticker
        fs = w * 0.05
        if n_now >= 1 and t < T_RUN + T_HOLD:
            d = DIG[n_now - 1]
            if CANON:
                ch = CANON_NAMES[int(min(t, T_RUN - 1e-6) // (2 * CB)) % 8]
                c.text_centered(f"digit #{n_now}:  {d}   ·   chord {ch}", h * 0.765, size=fs * 0.85, color=dcol(d))
            else:
                c.text_centered(f"digit #{n_now}:  {d}  →  ♪ {NOTE_NAMES[d]}", h * 0.765, size=fs * 0.85, color=dcol(d))
            s = "3." + "".join(map(str, DIG[1:n_now]))
            tail = s[-26:] if len(s) > 26 else s
            c.text_centered(tail, h * 0.800, size=fs * 0.70, color=(0.92, 0.92, 0.96), alpha=0.85, bold=False,
                            max_w=w * 0.94)
        else:
            c.text_centered("π = 3.14159…", h * 0.765, size=fs, color=GOLD, alpha=1 - fade if fade < 1 else 1.0)
        c.text_centered("FAMOUS NUMBERS · π", h * 0.205, size=h * 0.015, color=GOLD, alpha=0.85)
        if rule:
            c.caption(rule, alpha=1.0, layout=L)
        c.watermark(L)


def render(layout, sim, out_path, rule, still_frame=None):
    sc = Scene(layout, sim)
    writer = None if still_frame is not None else VideoWriter(out_path, sc.canvas, FPS)
    for f in range(sim["nf"]):
        if still_frame is not None and f != still_frame:
            t = f * DT
            n_now = int(np.searchsorted(TD, t, side="right"))
            while sc.done < n_now:
                if sc.done >= 1:
                    sc.add_string(sc.done, sc.actx, 0.32)
                sc.done += 1
            continue
        sc.draw(f, rule)
        if writer is None:
            studio.save_still(sc.canvas, out_path)
            return f / FPS
        writer.write_frame()
    writer.close()
    return sim["nf"] / FPS


def build_events(sim, layout):
    if CANON:
        out, last = [], -1.0
        for i, t in enumerate(TD):
            if t - last < 0.045:
                continue
            last = t
            out.append({"t": round(float(t) + 0.004, 4), "note": canon_note(i), "gain": 0.40,
                        "x": layout.w * (0.5 + 0.3 * math.sin(DIG[i] * 0.63))})
        for j, note in enumerate((50, 57, 62, 66, 69, 74)):          # final D chord
            out.append({"t": round(T_RUN + 0.04 * j, 4), "note": note, "gain": 0.40, "x": layout.w / 2})
        return sorted(out, key=lambda e: e["t"])
    return _build_events_plain(sim, layout)


def canon_bed():
    """Pachelbel's Canon (public domain): the famous bassline (half notes, cello-like) + soft string chords."""
    sr = audio.SR
    n = int(round(T_LOOP * sr))
    out = np.zeros(n)
    for k in range(9):                                   # 8 chords + the final D
        ci = k % 8 if k < 8 else 0
        t0 = k * 2 * CB
        L = 2 * CB * (1.0 if k < 8 else 1.6)
        i0 = int(t0 * sr)
        tt = np.arange(int(L * sr)) / sr
        f0 = audio.midi_to_hz(CANON_ROOTS[ci])
        ph = 2 * np.pi * f0 * tt
        cello = (np.sin(ph) + 0.5 * np.sin(2 * ph) + 0.25 * np.sin(3 * ph)) * np.clip(tt / 0.05, 0, 1) * np.exp(-tt * 0.6)
        pad = np.zeros(len(tt))
        for m in CANON_CHORDS[ci]:
            fp = audio.midi_to_hz(m - 12)
            pad += np.sin(2 * np.pi * fp * tt) + 0.4 * np.sin(4 * np.pi * fp * tt)
        pad *= np.clip(tt / 0.25, 0, 1) * np.clip((L - tt) / 0.3, 0, 1) / 3
        seg = 0.32 * cello + 0.16 * pad
        i1 = min(n, i0 + len(seg))
        out[i0:i1] += seg[: i1 - i0]
    return (0.06 * out).astype(np.float32)


def _build_events_plain(sim, layout):
    out, last = [], -1.0
    for i, t in enumerate(TD):
        if t - last < 0.07:                                   # keep it musical once digits fly by
            continue
        last = t
        d = DIG[i]
        out.append({"t": round(float(t) + 0.005, 4), "note": SCALE[d], "gain": 0.44,
                    "x": layout.w * (0.5 + 0.3 * math.sin(d * 0.63))})
    for j, note in enumerate((48, 55, 60, 64, 67, 72)):
        out.append({"t": round(T_RUN + 0.05 * j, 4), "note": note, "gain": 0.42, "x": layout.w / 2})
    return sorted(out, key=lambda e: e["t"])


def _worker(o, sim, label, rule):
    layout = get_layout(o)
    name = f"{SCENE}_{label}_{layout.tag}"
    video = studio.OUT_DIR / f"{name}_silent.mp4"
    d = render(layout, sim, video, rule)
    pad = canon_bed() if CANON else kit.loop_pad(T_LOOP, ((48, 1.0), (55, 0.7), (60, 0.45), (64, 0.3)), gain=0.014)
    kit.deliver_loop(SCENE, name, layout, video, build_events(sim, layout), d, voice="glassharp", bed=pad)


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
    print(f"[{SCENE}] {T_LOOP:.1f}s, digits {''.join(map(str, DIG[:12]))}…")
    kit.fan_out(_worker, (sim, label, rule), SCENE)


if __name__ == "__main__":
    main()
