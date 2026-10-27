"""MATH TRACK v2 — a full ~2.5-minute original beat where every instrument is a math graph (long-form, 16:9).

v2 (owner notes on v1): natural scratches (an original synthesised "ahh" vocal scrubbed back and forth like a
record, instead of a chirp), a calm right panel (a slowly rotating Lissajous curve x = sin(a t), y = sin(b t + d)
whose ratio a:b changes per section, a dot tracing it once per bar, gently breathing with the kick) instead of the
oscilloscope, and a song that moves: groove A → break with a riser → Groove B = the busy peak (16th hats, open hats,
ghost notes, octave-jumping bass, extra stabs, a running lead) → boom-bap bridge → a half-time outro that slows down
and lets instruments go one by one. Original music in the 90s West Coast / boom-bap STYLE only (no songs, samples,
artist names). v1 is kept at output/_superseded/math_track_v1_scene.py.

    NF_FAST=1 NF_ORIENT=horizontal python scenes/math_track.py
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

SCENE = "math_track"
BPM = 92.0
BEAT = 60.0 / BPM
STEP = BEAT / 4
BAR = 4 * BEAT
SR = audio.SR
T0 = 0.9
GOLD = (1.0, 0.80, 0.38)
GREY = (0.70, 0.72, 0.80)

# name, bars, swing, flags, Lissajous (a, b), colour
SECTIONS = [
    ("Intro", 4, 0.12, {"keys", "bass", "vinyl", "hats_late"}, (1, 1), (0.60, 0.72, 1.00)),
    ("Groove A", 14, 0.12, {"kick", "clap", "hats", "bass", "keys", "leadA"}, (3, 2), GOLD),
    ("Break", 6, 0.12, {"keys", "bass", "leadB", "kick_sparse", "riser"}, (2, 1), (0.35, 0.90, 0.85)),
    ("Groove B", 16, 0.12, {"kick", "ghost", "clap", "hats2", "openhat", "bassB", "keys_busy", "leadC",
                            "scratch2"}, (5, 4), (1.00, 0.50, 0.70)),
    ("Boom-bap bridge", 8, 0.08, {"kickbb", "snare", "hats", "bassbb", "keysbb", "scratch"}, (4, 3),
     (0.70, 0.55, 1.00)),
    ("Outro", 10, 0.10, {"outro"}, (1, 1), (0.55, 0.75, 1.00)),
]
LANES = [
    ("KICK", "y = e^(−6x)·sin(40x)", (1.00, 0.45, 0.35)),
    ("CLAP", "y = e^(−12x)·noise(x)", (1.00, 0.85, 0.40)),
    ("HATS", "y = e^(−30x)·sin(400x)", (0.45, 0.90, 0.95)),
    ("BASS", "y = sin(f·x), sliding", (0.65, 0.55, 1.00)),
    ("KEYS", "y = Σ sin(fₖ·x)", (1.00, 0.62, 0.30)),
    ("LEAD", "y = sin(2π·f(t)·x)", (0.55, 1.00, 0.65)),
    ("SCRATCH", "y = ah(p(t)), p = sin(πt)", (1.00, 0.45, 0.80)),
]
ROOTS = [38, 34, 31, 33]                                   # D Bb G A
CHORDS = [(62, 65, 69, 72, 76), (58, 62, 65, 69, 72), (55, 58, 62, 65, 69), (57, 61, 64, 67, 70)]
CHORDS_BB = [(50, 53, 57, 60, 64), (55, 58, 62, 65, 69)]
BASS_PAT = [(0, 0, 5), (6, 0, 2), (10, 12, 2), (12, 0, 4)]
BASSB_PAT = [(0, 0, 3), (3, 12, 1), (4, 0, 2), (6, 0, 2), (8, 12, 2), (10, 10, 2), (12, 7, 2), (14, 0, 2)]
BASS_BB = [[(0, 38, 3), (3, 38, 1), (7, 41, 2), (10, 36, 3), (14, 33, 2)],
           [(0, 43, 3), (3, 43, 1), (7, 46, 2), (10, 41, 3), (14, 38, 2)]]
LEAD_A = [[(0, 81, 4), (4, 84, 2), (6, 86, 6), (12, 84, 4)],
          [(0, 82, 4), (4, 81, 4), (8, 79, 6), (14, 77, 2)],
          [(0, 81, 4), (4, 84, 2), (6, 86, 4), (10, 89, 6)],
          [(0, 88, 4), (4, 86, 4), (8, 84, 4), (12, 81, 4)]]
LEAD_B = [[(0, 86, 2), (2, 84, 2), (4, 81, 4), (8, 84, 2), (10, 86, 6)],
          [(0, 89, 4), (4, 86, 2), (6, 84, 6), (12, 82, 4)],
          [(0, 81, 2), (2, 84, 2), (4, 86, 2), (6, 89, 4), (10, 91, 6)],
          [(0, 89, 4), (4, 88, 2), (6, 86, 2), (8, 85, 4), (12, 81, 4)]]
LEAD_C = [[(0, 81, 2), (2, 84, 2), (4, 86, 2), (6, 88, 2), (8, 89, 4), (12, 88, 2), (14, 86, 2)],
          [(0, 84, 2), (2, 82, 2), (4, 81, 4), (8, 79, 2), (10, 81, 2), (12, 82, 4)],
          [(0, 79, 2), (2, 81, 2), (4, 82, 2), (6, 84, 2), (8, 86, 4), (12, 89, 2), (14, 91, 2)],
          [(0, 93, 4), (4, 91, 2), (6, 89, 2), (8, 88, 4), (12, 85, 4)]]
LEAD_O = [[(0, 81, 8), (8, 77, 8)], [(0, 77, 8), (8, 74, 8)], [(0, 74, 16)], [(0, 73, 16)]]
SCRATCH = [(8, 2, 1.0), (10, 1, 0.6), (11, 1, 0.6), (14, 2, 1.0)]


def arrangement():
    bars, t = [], T0
    for si, sec in enumerate(SECTIONS):
        for b in range(sec[1]):
            bars.append((t, si, b))
            t += BAR
    return bars, t + 1.0


BARS, T_END = arrangement()
SEC_START = [(t, SECTIONS[si][0], si) for (t, si, b) in BARS if b == 0]


def st(bt, step, sw):
    return bt + step * STEP + (sw * BEAT if step % 2 == 1 else 0.0)


def outro_flags(b):
    if b < 4:
        return {"half_kick", "half_clap", "half_hats", "bass_long", "keys_long", "leadO"}
    if b < 7:
        return {"half_hats", "bass_long", "keys_long", "leadO"}
    return {"keys_long", "leadO"}


def build():
    D = {"kick": [], "clap": [], "snare": [], "hat": [], "ohat": [], "bass": [], "lead": [], "keys": [],
         "scratch": [], "roll": [], "riser": []}
    for (bt, si, b) in BARS:
        name, nb, sw, flags, _, _ = SECTIONS[si]
        if "outro" in flags:
            flags = outro_flags(b)
        r = b % 4
        if "kick" in flags or "kickbb" in flags:
            for s in (0, 7, 10):
                D["kick"].append((st(bt, s, sw), 1.0))
        if "ghost" in flags:
            D["kick"].append((st(bt, 13, sw), 0.5))
        if "kick_sparse" in flags and b % 2 == 0:
            D["kick"].append((st(bt, 0, sw), 0.9))
        if "half_kick" in flags:
            D["kick"].append((st(bt, 0, sw), 1.0))
            if b % 2 == 1:
                D["kick"].append((st(bt, 10, sw), 0.7))
        if "clap" in flags:
            for s in (4, 12):
                D["clap"].append((st(bt, s, sw), 1.0))
            if "ghost" in flags and b % 2 == 1:
                D["clap"].append((st(bt, 15, sw), 0.35))
        if "half_clap" in flags:
            D["clap"].append((st(bt, 8, sw), 1.0))
        if "snare" in flags:
            for s in (4, 12):
                D["snare"].append((st(bt, s, sw), 1.0))
        if "hats" in flags or ("hats_late" in flags and b >= 2):
            for s in range(0, 16, 2):
                D["hat"].append((st(bt, s, sw), 1.0))
        if "hats2" in flags:
            for s in range(16):
                D["hat"].append((st(bt, s, sw), 1.0 if s % 2 == 0 else 0.55))
        if "half_hats" in flags:
            for s in (0, 4, 8, 12):
                D["hat"].append((st(bt, s, sw), 0.8))
        if "openhat" in flags:
            for s in (2, 6, 10, 14):
                D["ohat"].append((st(bt, s, sw), 1.0))
        if "bass" in flags:
            for s, iv, ln in BASS_PAT:
                D["bass"].append((st(bt, s, sw), ROOTS[r] + iv, ln * STEP))
        if "bassB" in flags:
            for s, iv, ln in BASSB_PAT:
                D["bass"].append((st(bt, s, sw), ROOTS[r] + iv, ln * STEP))
        if "bassbb" in flags:
            for s, m, ln in BASS_BB[b % 2]:
                D["bass"].append((st(bt, s, sw), m, ln * STEP))
        if "bass_long" in flags:
            D["bass"].append((st(bt, 0, sw), ROOTS[r], 15 * STEP))
        if "keys" in flags:
            for s, g in ((0, 0.9), (6, 0.6)):
                D["keys"].append((st(bt, s, sw), CHORDS[r], g, 1.2))
        if "keys_busy" in flags:
            for s, g in ((0, 0.9), (3, 0.5), (6, 0.7), (10, 0.6)):
                D["keys"].append((st(bt, s, sw), CHORDS[r], g, 0.8))
        if "keysbb" in flags:
            for s, g in ((0, 0.9), (8, 0.6)):
                D["keys"].append((st(bt, s, sw), CHORDS_BB[b % 2], g, 1.0))
        if "keys_long" in flags:
            D["keys"].append((st(bt, 0, sw), CHORDS[r], 0.9, 2.6))
        for key, mel in (("leadA", LEAD_A), ("leadB", LEAD_B), ("leadC", LEAD_C), ("leadO", LEAD_O)):
            if key in flags:
                for s, m, ln in mel[r]:
                    D["lead"].append((st(bt, s, sw), m, ln * STEP))
        if ("scratch" in flags or "scratch2" in flags) and b % 2 == 1:
            for s, ln, depth in SCRATCH:
                D["scratch"].append((st(bt, s, sw), ln * STEP, depth))
        if "riser" in flags and b == nb - 1:
            D["riser"].append(bt)
            for j in range(12):
                D["roll"].append((bt + j * BAR / 12, 0.1 + 0.4 * j / 11))
    H = {"KICK": [x for x, g in D["kick"]],
         "CLAP": [x for x, g in D["clap"]] + [x for x, g in D["snare"]],
         "HATS": [x for x, g in D["hat"]] + [x for x, g in D["ohat"]],
         "BASS": [x[0] for x in D["bass"]], "KEYS": [x[0] for x in D["keys"]],
         "LEAD": [x[0] for x in D["lead"]], "SCRATCH": [x[0] for x in D["scratch"]]}
    return {k: np.sort(np.array(v, dtype=float)) for k, v in H.items()}, D


HITS, NOTES = build()


def movavg(x, k):
    k = max(1, int(k))
    c = np.cumsum(np.concatenate([[0.0], x]))
    pad = k // 2
    lo = np.clip(np.arange(len(x)) - pad, 0, len(x))
    hi = np.clip(np.arange(len(x)) - pad + k, 0, len(x))
    return (c[hi] - c[lo]) / np.maximum(hi - lo, 1)


def vowel_ah(dur=0.8):
    """An original synthetic 'ahh' vocal: a glottal pulse train through three formant resonators."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    f0 = 150 * (1 + 0.01 * np.sin(2 * np.pi * 5 * t))
    ph = np.cumsum(f0) / SR
    src = (ph % 1.0) ** 3 - 0.25
    out = np.zeros(n)
    for fc, bw, g in ((700, 90, 1.0), (1220, 110, 0.6), (2600, 160, 0.3)):
        r = math.exp(-math.pi * bw / SR)
        a1, a2 = -2 * r * math.cos(2 * math.pi * fc / SR), r * r
        y = np.zeros(n)
        y1 = y2 = 0.0
        for i in range(n):
            y0 = src[i] - a1 * y1 - a2 * y2
            y[i] = y0
            y2, y1 = y1, y0
        out += g * y / (np.abs(y).max() + 1e-9)
    env = np.clip(t / 0.02, 0, 1) * np.clip((dur - t) / 0.1, 0, 1)
    return out * env / (np.abs(out).max() + 1e-9)


VOX = vowel_ah()


def scratch_sig(L, depth):
    """A 'baby scratch': the record moves forward then back over the vowel; pitch follows the hand speed."""
    n = int(L * SR)
    u = np.arange(n) / n
    pos = depth * 0.35 * np.sin(np.pi * u)
    sig = np.interp((0.05 + pos) * SR, np.arange(len(VOX)), VOX)
    speed = np.abs(np.gradient(pos)) * n
    sig *= np.clip(speed / (speed.max() + 1e-9) * 1.6, 0, 1)
    return movavg(sig, 3) * np.sin(np.pi * u) ** 0.5


def synth():
    n = int(round(T_END * SR))
    out = np.zeros(n)
    rng = np.random.default_rng(21)

    def put(sig, t0, g):
        i0 = int(round(t0 * SR))
        i1 = min(n, i0 + len(sig))
        if i1 > i0 >= 0:
            out[i0:i1] += g * sig[: i1 - i0]

    def tt(L):
        return np.arange(int(L * SR)) / SR

    tk = tt(0.45)
    kick = np.tanh(1.6 * np.exp(-tk * 9) * np.sin(2 * np.pi * np.cumsum(46 + 80 * np.exp(-tk * 26)) / SR))
    tc = tt(0.22)
    clap = np.zeros(len(tc))
    for d in (0.0, 0.012, 0.024):
        i0 = int(d * SR)
        clap[i0:] += rng.uniform(-1, 1, len(tc) - i0) * np.exp(-tc[: len(tc) - i0] * 22)
    clap = movavg(clap, 3)
    ts = tt(0.25)
    snare = np.exp(-ts * 14) * (0.8 * rng.uniform(-1, 1, len(ts)) + 0.6 * np.sin(2 * np.pi * 185 * ts))
    th = tt(0.05)
    hat = np.exp(-th * 70) * np.diff(rng.standard_normal(len(th) + 1))
    to = tt(0.28)
    ohat = np.exp(-to * 12) * np.diff(rng.standard_normal(len(to) + 1)) * 0.7
    for x, g in NOTES["kick"]:
        put(kick, x, 1.05 * g)
    for x, g in NOTES["clap"]:
        put(clap, x, 0.8 * g)
    for x, g in NOTES["snare"]:
        put(snare, x, 0.85 * g)
    for x, g in NOTES["hat"]:
        put(hat, x, 0.17 * g)
    for x, g in NOTES["ohat"]:
        put(ohat, x, 0.12 * g)
    for x, g in NOTES["roll"]:
        put(snare, x, g)
    for bt in NOTES["riser"]:
        tr = tt(BAR)
        u = tr / BAR
        sig = np.sin(2 * np.pi * np.cumsum(180 + 1100 * u ** 2) / SR) * u ** 2 * 0.25
        sig += movavg(rng.standard_normal(len(tr)), 5) * u ** 3 * 0.2
        put(sig, bt, 1.0)

    def track(note_list, glide_s):
        p = np.zeros(n)
        a = np.zeros(n)
        for t0, m, L in note_list:
            i0, i1 = int(t0 * SR), min(n, int((t0 + L * 0.95) * SR))
            p[i0:i1] = m
            seg = np.arange(i1 - i0) / SR
            a[i0:i1] = np.clip(seg / 0.02, 0, 1) * np.clip((L * 0.95 - seg) / 0.05, 0, 1)
        idx = np.where(p > 0, np.arange(n), 0)
        np.maximum.accumulate(idx, out=idx)
        p = p[idx]
        p[p == 0] = 40
        return movavg(p, glide_s * SR), a

    bp, ba = track(NOTES["bass"], 0.05)
    ph = 2 * np.pi * np.cumsum(440 * 2 ** ((bp - 69) / 12)) / SR
    out += 0.50 * ba * np.tanh(1.3 * (np.sin(ph) + 0.25 * np.sin(2 * ph)))
    lp, la = track(NOTES["lead"], 0.07)
    tv = np.arange(n) / SR
    vib = 0.35 * movavg(la, 0.3 * SR) * np.sin(2 * np.pi * 5.5 * tv)
    phl = 2 * np.pi * np.cumsum(440 * 2 ** ((lp + vib - 69) / 12)) / SR
    out += 0.15 * la * (np.sin(phl) + 0.08 * np.sin(2 * phl))
    for t0, ch, g, L in NOTES["keys"]:
        te = tt(L)
        dec = 2.2 if L < 2 else 1.0
        sig = np.zeros(len(te))
        for m in ch:
            f0 = audio.midi_to_hz(m)
            sig += np.sin(2 * np.pi * f0 * te) * np.exp(-te * dec) + 0.25 * np.sin(4 * np.pi * f0 * te) * np.exp(-te * 9)
        put(sig * (0.8 + 0.2 * np.sin(2 * np.pi * 5 * te)) / len(ch), t0, 0.5 * g)
    for t0, L, depth in NOTES["scratch"]:
        put(scratch_sig(L, depth), t0, 0.32)
    ti = tt(T0 * 0.55)
    rew = np.sin(2 * np.pi * np.cumsum(2600 - 2200 * (ti / ti[-1]) ** 0.7) / SR) * (0.5 + 0.5 * np.sin(2 * np.pi * 22 * ti))
    put(0.45 * rew + 0.2 * movavg(rng.standard_normal(len(ti)), 6), 0.0, 0.9)
    for t0 in (T0 * 0.55, T_END - 1.05):
        tsp = tt(0.5)
        f = audio.midi_to_hz(62) * (1 - tsp / tsp[-1]) ** 1.6
        put(np.sin(2 * np.pi * np.cumsum(f) / SR) * (1 - tsp / tsp[-1]) * 0.55, t0, 0.9)
    crackle = np.zeros(n)
    pos = rng.integers(0, n, int(T_END * 14))
    crackle[pos] = rng.uniform(-1, 1, len(pos))
    out += np.convolve(crackle, np.exp(-np.arange(40) / 6), "same") * 0.04 / 0.45
    return (0.45 * out).astype(np.float32)


MIX = synth()


def simulate():
    return {"nf": int(round(T_END * FPS))}


def lane_fn(name, x, k):
    if name == "KICK":
        return np.exp(-6 * x) * np.sin(40 * x)
    if name == "CLAP":
        r = np.random.default_rng(k % 97)
        return np.exp(-12 * x) * r.uniform(-1, 1, len(x))
    if name == "HATS":
        return np.exp(-30 * x) * np.sin(400 * x)
    if name == "KEYS":
        return (np.sin(2 * math.pi * 3 * x) + np.sin(2 * math.pi * 3.78 * x) + np.sin(2 * math.pi * 4.49 * x)) / 2.6
    if name == "SCRATCH":
        return np.interp((0.05 + 0.35 * np.sin(np.pi * x)) * SR, np.arange(len(VOX)), VOX) * 0.9
    f = 1.5 + (k % 7) * 0.45 if name == "BASS" else 3.0 + (k % 9) * 0.55
    return np.sin(2 * math.pi * f * x) * 0.9


DECAY = {"KICK": 0.28, "CLAP": 0.2, "HATS": 0.10, "BASS": 0.45, "KEYS": 0.6, "LEAD": 0.5, "SCRATCH": 0.3}


def section_at(t):
    cur = SEC_START[0]
    for s in SEC_START:
        if s[0] <= t:
            cur = s
    return cur


class Scene:
    def __init__(self, layout, sim):
        self.L, self.sim = layout, sim
        self.canvas = Canvas(layout.w, layout.h, studio.render_scale())

    def liss(self, cx, cy, R, a, b, delta, col, alpha, t, pump):
        s = np.linspace(0, 2 * math.pi, 900)
        x = np.sin(a * s)
        y = np.sin(b * s + delta)
        k = R * (1 + 0.02 * pump)
        pts = [(cx + k * u, cy - k * v) for u, v in zip(x, y)]
        c = self.canvas
        c.polylines([pts], col, width=14, alpha=0.08 * alpha)
        c.polylines([pts], col, width=3.0, alpha=0.75 * alpha)
        ph = ((t - T0) / BAR) % 1.0
        i = int(ph * (len(s) - 1))
        tail = [pts[(i - j) % len(pts)] for j in range(0, 130)]
        c.polylines([tail[::-1]], (1, 1, 1), width=4, alpha=0.55 * alpha)
        c.glow(*pts[i], 8, col, strength=0.8 * alpha, reach=4)
        c.circle(*pts[i], 7, (1, 1, 1), alpha=0.95 * alpha)

    def draw(self, f, rule):
        L, c = self.L, self.canvas
        w, h = L.w, L.h
        t = f * DT
        ctx = c.ctx
        kp = HITS["KICK"][HITS["KICK"] <= t]
        pump = math.exp(-(t - kp[-1]) / 0.2) if kp.size else 0.0
        g = cairo.RadialGradient(w * 0.5, h * 0.5, 0, w * 0.5, h * 0.5, w * 0.7)
        g.add_color_stop_rgb(0.0, 0.07, 0.06, 0.10)
        g.add_color_stop_rgb(1.0, 0.01, 0.01, 0.02)
        ctx.set_source(g)
        ctx.paint()
        x0, x1 = w * 0.04, w * 0.50
        top, lh = h * 0.09, h * 0.108
        for i, (name, eq, col) in enumerate(LANES):
            ym = top + lh * (i + 0.5)
            arr = HITS[name]
            past = arr[arr <= t]
            on = bool(((arr > t - 2 * BAR) & (arr <= t + 0.05)).any())
            vis = 1.0 if on else 0.25
            env = math.exp(-(t - past[-1]) / DECAY[name]) if past.size else 0.0
            ctx.rectangle(x0, ym - lh * 0.43, x1 - x0, lh * 0.86)
            ctx.set_source_rgba(*col, (0.04 + 0.10 * env) * vis)
            ctx.fill_preserve()
            ctx.set_source_rgba(*col, 0.25 * vis)
            ctx.set_line_width(1.5)
            ctx.stroke()
            c.text_centered(name, ym - lh * 0.02, size=h * 0.032, color=col, alpha=vis, cx=x0 + (x1 - x0) * 0.17,
                            max_w=(x1 - x0) * 0.32)
            c.text_centered(eq, ym + lh * 0.28, size=h * 0.018, color=(0.9, 0.9, 0.95), alpha=0.8 * vis, bold=False,
                            cx=x0 + (x1 - x0) * 0.17, max_w=(x1 - x0) * 0.34)
            xs = np.linspace(0, 1, 200)
            ys = lane_fn(name, xs, len(past))
            amp = lh * 0.36 * (0.12 + 0.88 * env) * vis
            gx = x0 + (x1 - x0) * 0.36
            pts = [(gx + (x1 - gx - 8) * x, ym - amp * y) for x, y in zip(xs, ys)]
            c.polylines([pts], col, width=6, alpha=0.12 * env * vis)
            c.polylines([pts], col, width=2.2, alpha=(0.4 + 0.6 * env) * vis)
        cx, cy, R = w * 0.75, h * 0.47, h * 0.27
        s0, sname, si = section_at(t)
        a, b = SECTIONS[si][4]
        col = SECTIONS[si][5]
        delta = 2 * math.pi * t / 24.0
        fade = smooth((t - s0) / BAR) if si > 0 else 1.0
        if fade < 1.0:
            pa, pb = SECTIONS[si - 1][4]
            self.liss(cx, cy, R, pa, pb, delta, SECTIONS[si - 1][5], 1 - fade, t, pump)
        self.liss(cx, cy, R, a, b, delta, col, fade, t, pump)
        c.text_centered(sname.upper(), h * 0.10, size=h * 0.045, color=col, cx=cx)
        c.text_centered(f"x = sin({a}t)    y = sin({b}t + δ)", h * 0.80, size=h * 0.026, color=(0.92, 0.92, 0.96),
                        alpha=0.85, bold=False, cx=cx)
        bi = int((t - T0) / BEAT) % 4 if t >= T0 else -1
        for k in range(4):
            c.circle(cx + (k - 1.5) * w * 0.03, h * 0.15, h * (0.011 if k == bi else 0.007),
                     col if k == bi else (0.5, 0.5, 0.55), alpha=0.9)
        tx0, tx1, ty = w * 0.04, w * 0.96, h * 0.93
        c.lines([(tx0, ty, tx1, ty)], GREY, width=3, alpha=0.3)
        c.lines([(tx0, ty, tx0 + (tx1 - tx0) * min(t / T_END, 1), ty)], GOLD, width=4, alpha=0.9)
        for st0, nm, _ in SEC_START:
            xx = tx0 + (tx1 - tx0) * st0 / T_END
            c.lines([(xx, ty - 8, xx, ty + 8)], GREY, width=2, alpha=0.7)
            c.text_centered(nm, ty - h * 0.022, size=h * 0.016, color=GREY, alpha=0.8, bold=False,
                            cx=xx + (tx1 - tx0) * 0.05, max_w=w * 0.12)
        mm, ss = divmod(int(t), 60)
        c.text_centered(f"{mm}:{ss:02d}", ty + h * 0.045, size=h * 0.018, color=GREY, alpha=0.8, bold=False,
                        cx=tx1 - w * 0.02)
        ta = 1 - smooth((t - 4.5) / 0.8)
        if ta > 0.01:
            c.text_centered("MATH IS VIBIN'", h * 0.86, size=h * 0.05, color=(1, 1, 1), alpha=ta, cx=cx)
            c.text_centered("a full beat made only of graphs", h * 0.895, size=h * 0.022, color=GOLD, alpha=ta,
                            bold=False, cx=cx)
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


def main():
    label = arg("--label", "v2")
    studio.OUT_DIR.mkdir(exist_ok=True)
    sim = simulate()
    layout = get_layout(kit.orients()[0])
    if kit.has("--still"):
        f = int(arg("--frame", "600"))
        png = studio.OUT_DIR / f"{SCENE}_{label}_f{f}_{layout.tag}.png"
        render(layout, sim, png, "", still_frame=f)
        print(f"[{SCENE}] -> {png}")
        return
    print(f"[{SCENE}] {T_END:.1f}s, chapters: " + ", ".join(f"{int(s0 // 60)}:{int(s0 % 60):02d} {n}"
                                                            for s0, n, _ in SEC_START))
    name = f"{SCENE}_{label}_{layout.tag}"
    video = studio.OUT_DIR / f"{name}_silent.mp4"
    d = render(layout, sim, video, "")
    kit.deliver(SCENE, name, layout, video, [{"t": 0.02, "note": 62, "gain": 0.05, "x": layout.w / 2}], d, True,
                voice="glassharp", bed=MIX, peak_db=-6.0)


if __name__ == "__main__":
    main()
