"""MATH HIP HOP — an old-school boom-bap beat where every instrument is a math graph.

Five lanes, one per instrument, each showing its equation; the graph punches every time the
instrument hits, and the SOUND is synthesised from that same shape:
  KICK    y = e^(-6x) sin(40x)      a decaying wave (literally what a kick is)
  SNARE   y = e^(-9x) noise(x)      decaying noise
  HATS    y = e^(-30x) sin(400x)    a tiny fast tick (swung 8ths)
  BASS    y = sin(f x)              f follows the bassline
  SCRATCH y = sin(9x^2)             a chirp: the old-school record-scratch sweep
Kick, snare and bass from frame 0, then +hats, +dusty chord stabs, +scratch; vinyl crackle
underneath. 90 BPM, 4 bars = the loop. Original beat, bassline and chords (no samples, no breakbeats).
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

SCENE = "math_hiphop"
STYLE = arg("--style", "boombap")        # "gfunk": an ORIGINAL 90s West Coast style beat (style only)
GF = STYLE == "gfunk"
BPM = 92.0 if GF else 90.0
BEAT = 60.0 / BPM
STEP = BEAT / 4                           # 16th note
SWING = (0.12 if GF else 0.08) * BEAT     # swing on the off-16ths (G-funk: heavier, laid back)
BARS = int(arg("--bars", "4"))           # 8 = two 4-bar phrases (~21.8 s with the intro)
HOOK = arg("--hook", "0") == "1" and GF       # needle-drop intro: rewind + tape stop, then the beat drops
T_INTRO = 0.9 if HOOK else 0.0
T_LOOP = T_INTRO + BARS * 4 * BEAT
GOLD = (1.0, 0.80, 0.38)

LANES = [  # name, equation, colour, decay (s) for the visual punch, bar it joins
    ("KICK", "y = e^(−6x)·sin(40x)", (1.00, 0.45, 0.35), 0.28, 0),
    ("SNARE", "y = e^(−9x)·noise(x)", (1.00, 0.85, 0.40), 0.22, 0),
    ("HATS", "y = e^(−30x)·sin(400x)", (0.45, 0.90, 0.95), 0.10, 1),
    ("BASS", "y = sin(f·x)", (0.65, 0.55, 1.00), 0.45, 0),
    ("SCRATCH", "y = sin(9x²)", (1.00, 0.45, 0.80), 0.30, 3),
]
if GF:
    LANES = [
        ("KICK", "y = e^(−6x)·sin(40x)", (1.00, 0.45, 0.35), 0.28, 0),
        ("CLAP", "y = e^(−12x)·noise(x)", (1.00, 0.85, 0.40), 0.20, 0),
        ("HATS", "y = e^(−30x)·sin(400x)", (0.45, 0.90, 0.95), 0.10, 1),
        ("BASS", "y = sin(f·x), sliding", (0.65, 0.55, 1.00), 0.55, 0),
        ("LEAD", "y = sin(2π·f(t)·x)", (0.55, 1.00, 0.65), 0.60, 0),
    ]
KICK_STEPS = [0, 7, 10]                   # 1, the "a" of 2, the "and" of 3
SNARE_STEPS = [4, 12]
BASSLINE = [(0, 45, 3), (3, 45, 1), (7, 48, 2), (10, 43, 3), (14, 40, 2)]   # (step, midi, length in steps)
SCRATCH_HITS = [(8, 2, +1), (10, 1, -1), (11, 1, +1), (14, 2, -1)]          # (step, len, direction) in bar 4
# ---- G-funk (original): Dm9 | Bbmaj7 | Gm9 | A7, sliding sub bass, a high gliding whistle lead
GF_CHORDS = [(62, 65, 69, 72, 76), (58, 62, 65, 69, 72), (55, 58, 62, 65, 69), (57, 61, 64, 67, 70)]
GF_BASS = [[(0, 38, 5), (6, 38, 2), (10, 50, 2), (12, 38, 4)],
           [(0, 34, 5), (6, 34, 2), (10, 46, 2), (12, 36, 4)],
           [(0, 31, 5), (6, 31, 2), (10, 43, 2), (12, 33, 4)],
           [(0, 33, 5), (6, 33, 2), (10, 45, 2), (12, 37, 4)]]
GF_LEAD = [[(0, 81, 4), (4, 84, 2), (6, 86, 6), (12, 84, 4)],
           [(0, 82, 4), (4, 81, 4), (8, 79, 6), (14, 77, 2)],
           [(0, 81, 4), (4, 84, 2), (6, 86, 4), (10, 89, 6)],
           [(0, 88, 4), (4, 86, 4), (8, 84, 4), (12, 81, 4)]]
# second phrase (bars 5-8): same chords and bass, an answering lead line (original), ending on a turnaround
GF_LEAD_B = [[(0, 86, 2), (2, 84, 2), (4, 81, 4), (8, 84, 2), (10, 86, 6)],
             [(0, 89, 4), (4, 86, 2), (6, 84, 6), (12, 82, 4)],
             [(0, 81, 2), (2, 84, 2), (4, 86, 2), (6, 89, 4), (10, 91, 6)],
             [(0, 89, 4), (4, 88, 2), (6, 86, 2), (8, 85, 4), (12, 81, 4)]]
if BARS > 4:
    GF_CHORDS = [GF_CHORDS[b % 4] for b in range(BARS)]
    GF_BASS = [GF_BASS[b % 4] for b in range(BARS)]
    GF_LEAD = [(GF_LEAD if b < 4 else GF_LEAD_B)[b % 4] for b in range(BARS)]


def step_time(bar, step):
    t = T_INTRO + (bar * 16 + step) * STEP
    return t + (SWING if step % 2 == 1 else 0.0)


def hits():
    h = {name: [] for name, *_ in LANES}
    if GF:
        for bar in range(BARS):
            for st in KICK_STEPS:
                h["KICK"].append(step_time(bar, st))
            for st in SNARE_STEPS:
                h["CLAP"].append(step_time(bar, st))
            if bar >= 1:
                for st in range(0, 16, 2):
                    h["HATS"].append(step_time(bar, st))
            for st, m, ln in GF_BASS[bar]:
                h["BASS"].append(step_time(bar, st))
            for st, m, ln in GF_LEAD[bar]:
                h["LEAD"].append(step_time(bar, st))
        return h
    for bar in range(BARS):
        for s in KICK_STEPS:
            h["KICK"].append(step_time(bar, s))
        for s in SNARE_STEPS:
            h["SNARE"].append(step_time(bar, s))
        if bar >= 1:
            for s in range(0, 16, 2):
                h["HATS"].append(step_time(bar, s))
        if bar >= 0:
            for s, m, ln in BASSLINE:
                h["BASS"].append(step_time(bar, s))
        if bar >= 3:
            for s, ln, d in SCRATCH_HITS:
                h["SCRATCH"].append(step_time(bar, s))
    return h


HITS = hits()


def simulate():
    return {"nf": int(round(T_LOOP * FPS))}


def lane_fn(name, x, t_since, bass_f=2.0):
    if name == "CLAP":
        rng = np.random.default_rng(int(t_since * 1000) % 89)
        return np.exp(-12 * x) * rng.uniform(-1, 1, len(x))
    if name == "LEAD":
        return np.sin(2 * math.pi * bass_f * x) * 0.9
    if name == "KICK":
        return np.exp(-6 * x) * np.sin(40 * x)
    if name == "SNARE":
        rng = np.random.default_rng(int(t_since * 1000) % 97)
        return np.exp(-9 * x) * rng.uniform(-1, 1, len(x))
    if name == "HATS":
        return np.exp(-30 * x) * np.sin(400 * x)
    if name == "BASS":
        return np.sin(2 * math.pi * bass_f * x) * 0.9
    return np.sin(9 * (x * 3) ** 2) * 0.9


class Scene:
    def __init__(self, layout, sim):
        self.L, self.sim = layout, sim
        self.canvas = Canvas(layout.w, layout.h, studio.render_scale())

    def draw(self, f, rule):
        L, c = self.L, self.canvas
        w, h = L.w, L.h
        t = f * DT
        if HOOK and t < T_INTRO:
            return self.intro(t, rule)
        ctx = c.ctx
        punch = 0.07 * math.exp(-(t - T_INTRO) / 0.15) if HOOK else 0.0
        ctx.save()
        ctx.translate(w / 2, h * 0.47)
        ctx.scale(1 + punch, 1 + punch)
        ctx.translate(-w / 2, -h * 0.47)
        bar = min(int(max(t - T_INTRO, 0) / (4 * BEAT)), BARS - 1)
        # the room pumps a little on every kick
        last_k = max([x for x in HITS["KICK"] if x <= t] or [-9])
        pump = math.exp(-(t - last_k) / 0.18)
        g = cairo.RadialGradient(w / 2, h * 0.47, 0, w / 2, h * 0.47, max(w, h) * 0.7)
        g.add_color_stop_rgb(0.0, 0.08 + 0.05 * pump, 0.06, 0.10)
        g.add_color_stop_rgb(1.0, 0.01, 0.01, 0.02)
        ctx.set_source(g)
        ctx.paint()
        top, lane_h = h * 0.235, h * 0.098
        x0, x1 = w * 0.06, w * 0.94
        for i, (name, eq, col, decay, join) in enumerate(LANES):
            y_mid = top + lane_h * (i + 0.5)
            enter = smooth((t - join * 4 * BEAT + 0.15) / 0.35) if join > 0 else 1.0
            if enter <= 0.01:
                c.text_centered(f"{name} joins in bar {join + 1}", y_mid + h * 0.006, size=h * 0.013,
                                color=(0.55, 0.55, 0.62), alpha=0.6, bold=False)
                continue
            past = [x for x in HITS[name] if x <= t]
            since = t - past[-1] if past else 9.0
            env = math.exp(-since / decay) if past else 0.0
            ctx.rectangle(x0, y_mid - lane_h * 0.44, x1 - x0, lane_h * 0.88)
            ctx.set_source_rgba(*col, 0.05 + 0.10 * env * enter)
            ctx.fill_preserve()
            ctx.set_source_rgba(*col, 0.25 * enter)
            ctx.set_line_width(2)
            ctx.stroke()
            bass_f = 2.0
            if GF and name in ("BASS", "LEAD") and past:
                seq = [nt for b in range(BARS) for nt in (GF_BASS if name == "BASS" else GF_LEAD)[b]]
                midi = seq[(len(past) - 1) % len(seq)][1]
                bass_f = 1.0 + (midi - (26 if name == "BASS" else 74)) / (3.0 if name == "BASS" else 1.6)
            elif name == "BASS" and past:
                k = len(past) - 1
                bass_f = 1.0 + (BASSLINE[k % len(BASSLINE)][1] - 38) / 4.0
            xs = np.linspace(0, 1, 260)
            ys = lane_fn(name, xs, past[-1] if past else 0.0, bass_f)
            amp = lane_h * 0.36 * (0.12 + 0.88 * env) * enter
            gx0 = x0 + (x1 - x0) * 0.40
            pts = [(gx0 + (x1 - gx0 - 12) * x, y_mid - amp * y) for x, y in zip(xs, ys)]
            c.polylines([pts], col, width=10, alpha=0.18 * env * enter)
            c.polylines([pts], col, width=3.5, alpha=(0.45 + 0.55 * env) * enter)
            sz = h * 0.022 * (1 + 0.25 * env)
            c.text_centered(name, y_mid - lane_h * 0.06, size=sz, color=col, alpha=enter,
                            cx=x0 + (x1 - x0) * 0.20, max_w=(x1 - x0) * 0.36)
            c.text_centered(eq, y_mid + lane_h * 0.28, size=h * 0.0125, color=(0.92, 0.92, 0.96), alpha=0.85 * enter,
                            bold=False, cx=x0 + (x1 - x0) * 0.20, max_w=(x1 - x0) * 0.38)
        # bar counter + beat dots
        beat_i = int(max(t - T_INTRO, 0) / BEAT) % 4
        y_b = top + lane_h * 5 + h * 0.035
        c.text_centered(f"BAR {bar + 1}", y_b, size=h * 0.026, color=GOLD, cx=w * 0.30)
        for k in range(4):
            on = k == beat_i
            c.circle(w * (0.55 + 0.08 * k), y_b - h * 0.008, h * (0.011 if on else 0.007), GOLD if on else (0.5, 0.5, 0.55),
                     alpha=0.95 if on else 0.6)
        ctx.restore()
        c.text_centered(("FAMOUS SOUNDS · WEST COAST MATH" if HOOK else "FAMOUS SOUNDS · MATH G-FUNK") if GF
                        else "FAMOUS SOUNDS · MATH BOOM BAP", h * 0.205, size=h * 0.015, color=GOLD, alpha=0.8)
        if rule:
            c.caption(rule, alpha=1.0, layout=L)
        c.watermark(L)


def _intro(self, t, rule):
    """Needle drop: the LEAD lane shows y = sin(9x^2) running BACKWARDS (the rewind), then a tape-stop."""
    L, c = self.L, self.canvas
    w, h = L.w, L.h
    ctx = c.ctx
    g = cairo.RadialGradient(w / 2, h * 0.47, 0, w / 2, h * 0.47, max(w, h) * 0.7)
    g.add_color_stop_rgb(0.0, 0.10, 0.05, 0.10)
    g.add_color_stop_rgb(1.0, 0.01, 0.01, 0.02)
    ctx.set_source(g)
    ctx.paint()
    u = t / T_INTRO
    col = (0.55, 1.00, 0.65)
    xs = np.linspace(0, 1, 400)
    speed = 1.0 - smooth((u - 0.55) / 0.45)                 # tape stop: the wave slows down
    ys = np.sin(9 * (3 * (1 - xs) + 6 * u) ** 2 * 0.25) * 0.9 * (0.3 + 0.7 * speed)
    y_mid, amp = h * 0.45, h * 0.11
    pts = [(w * 0.08 + w * 0.84 * x, y_mid - amp * y) for x, y in zip(xs, ys)]
    c.polylines([pts], col, width=18, alpha=0.18)
    c.polylines([pts], col, width=5, alpha=0.95)
    c.text_centered("<< REWIND" if u < 0.55 else "STOP…", h * 0.33, size=w * 0.08, color=col)
    c.text_centered("y = sin(9x²)  backwards", h * 0.58, size=w * 0.04, color=(0.92, 0.92, 0.96), alpha=0.9,
                    bold=False)
    c.text_centered("FAMOUS SOUNDS · WEST COAST MATH", h * 0.205, size=h * 0.015, color=GOLD, alpha=0.8)
    if rule:
        c.caption(rule, alpha=1.0, layout=L)
    c.watermark(L)


Scene.intro = _intro


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
    if GF:                                       # a soft bell on beat 1 of each bar (the rest is the bed)
        return [{"t": round(step_time(b, 0) + 0.004, 4), "note": GF_CHORDS[b][-1] + 12, "gain": 0.08,
                 "x": layout.w / 2} for b in range(BARS)]
    return _build_events_bb(sim, layout)


def _build_events_bb(sim, layout):
    """Dusty chord stabs (Am7, Dm7) in bars 3-4 on the glass voice, soft."""
    out = []
    for bar in (2, 3):
        for s, chord in ((0, (57, 60, 64, 67)), (8, (50, 53, 57, 60))):
            for j, n in enumerate(chord):
                out.append({"t": round(step_time(bar, s) + 0.006 * j, 4), "note": n, "gain": 0.09, "x": layout.w / 2})
    return out


def beat_bed():
    """ORIGINAL boom-bap beat, synthesised from the lane equations; periodic over the 4 bars."""
    sr = audio.SR
    n = int(round(T_LOOP * sr))
    out = np.zeros(n)
    rng = np.random.default_rng(3)

    def put(sig, t0, g):
        idx = (np.arange(len(sig)) + int(round(t0 * sr))) % n
        np.add.at(out, idx, g * sig)

    def tt(L):
        return np.arange(int(L * sr)) / sr

    tk = tt(0.45)
    kick = np.exp(-6 * tk / 0.45 * 2.2) * np.sin(2 * np.pi * np.cumsum(48 + 90 * np.exp(-tk * 28)) / sr)
    kick = np.tanh(1.8 * kick)
    ts = tt(0.25)
    snare = np.exp(-9 * ts / 0.25 * 1.4) * (0.8 * rng.uniform(-1, 1, len(ts)) + 0.6 * np.sin(2 * np.pi * 185 * ts))
    snare = np.convolve(snare, np.ones(3) / 3, "same")                   # a little dust
    th = tt(0.05)
    hat = np.exp(-30 * th / 0.05 * 0.5) * np.diff(rng.standard_normal(len(th) + 1))
    for name, lst in HITS.items():
        for x in lst:
            if name == "KICK":
                put(kick, x, 1.15)
            elif name == "SNARE":
                put(snare, x, 0.95)
            elif name == "HATS":
                put(hat, x, 0.22)
    for bar in range(0, BARS):                                          # bass (from frame 0)
        for s, m, ln in BASSLINE:
            L = ln * STEP * 0.95
            tb = tt(L)
            f0 = audio.midi_to_hz(m)
            sig = (np.sin(2 * np.pi * f0 * tb) + 0.3 * np.sin(4 * np.pi * f0 * tb)) * np.clip(tb / 0.01, 0, 1) * np.exp(-tb * 2.5)
            put(np.tanh(1.5 * sig), step_time(bar, s), 0.42)
    for s, ln, d in SCRATCH_HITS:                                        # scratches: sin(9x^2) chirps
        L = ln * STEP
        tc = tt(L)
        u = tc / L if d > 0 else 1 - tc / L
        fr = 300 + 1800 * u ** 2
        ph = 2 * np.pi * np.cumsum(fr) / sr
        sig = (np.sin(ph) + 0.6 * rng.uniform(-1, 1, len(tc))) * np.sin(np.pi * tc / L) ** 0.7
        sig = np.convolve(sig, np.ones(5) / 5, "same")
        put(sig, step_time(BARS - 1, s), 0.40)
    crackle = np.zeros(n)                                                # vinyl crackle
    pos = rng.integers(0, n, int(T_LOOP * 22))
    crackle[pos] = rng.uniform(-1, 1, len(pos))
    crackle = np.convolve(crackle, np.exp(-np.arange(40) / 6), "same") * 0.06
    return (0.42 * out + crackle).astype(np.float32)


def gfunk_bed():
    """ORIGINAL 90s West-Coast-style beat (style only; no song, melody or sample copied): heavy swung
    hats, kick + layered claps, sliding sub bass, electric-piano chords with tremolo, a high gliding
    whistle-synth lead (sine with portamento + vibrato). Periodic over the 4 bars."""
    sr = audio.SR
    n = int(round(T_LOOP * sr))
    out = np.zeros(n)
    rng = np.random.default_rng(9)

    def put(sig, t0, g):
        idx = (np.arange(len(sig)) + int(round(t0 * sr))) % n
        np.add.at(out, idx, g * sig)

    def tt(L):
        return np.arange(int(L * sr)) / sr

    tk = tt(0.45)
    kick = np.tanh(1.6 * np.exp(-tk * 9) * np.sin(2 * np.pi * np.cumsum(46 + 80 * np.exp(-tk * 26)) / sr))
    tc = tt(0.22)
    clap = np.zeros(len(tc))
    for d in (0.0, 0.012, 0.024):
        i0 = int(d * sr)
        clap[i0:] += rng.uniform(-1, 1, len(tc) - i0) * np.exp(-tc[: len(tc) - i0] * 22)
    clap = np.convolve(clap, np.ones(3) / 3, "same")
    th = tt(0.05)
    hat = np.exp(-th * 70) * np.diff(rng.standard_normal(len(th) + 1))
    for x in HITS["KICK"]:
        put(kick, x, 1.05)
    for x in HITS["CLAP"]:
        put(clap, x, 0.75)
    for x in HITS["HATS"]:
        put(hat, x, 0.20)
    # sliding sub bass: one continuous pitch track with short glides between notes
    pitch = np.full(n, np.nan)
    amp = np.zeros(n)
    for b in range(BARS):
        for st, m, ln in GF_BASS[b]:
            i0 = int(step_time(b, st) * sr)
            i1 = min(n, i0 + int(ln * STEP * sr * 0.95))
            pitch[i0:i1] = audio.midi_to_hz(m)
            amp[i0:i1] = np.exp(-np.arange(i1 - i0) / sr * 1.2)
    pitch = np.where(np.isnan(pitch), 0, pitch)
    k = int(0.05 * sr)
    pitch = np.convolve(np.where(pitch > 0, pitch, np.nan_to_num(pitch)), np.ones(k) / k, "same")
    amp = np.convolve(amp, np.ones(int(0.008 * sr)) / int(0.008 * sr), "same")
    ph = 2 * np.pi * np.cumsum(np.maximum(pitch, 20)) / sr
    out += 0.55 * amp * np.tanh(1.3 * (np.sin(ph) + 0.25 * np.sin(2 * ph)))
    # electric-piano chords: beat 1 and the "and" of 2 in each bar
    for b in range(BARS):
        for st, g in ((0, 0.9), (6, 0.6)):
            L = 1.2 if st == 0 else 0.7
            te = tt(L)
            sig = np.zeros(len(te))
            for m in GF_CHORDS[b]:
                f0 = audio.midi_to_hz(m)
                sig += np.sin(2 * np.pi * f0 * te) * np.exp(-te * 2.2) + 0.25 * np.sin(2 * np.pi * 2 * f0 * te) * np.exp(-te * 9)
            sig *= (0.8 + 0.2 * np.sin(2 * np.pi * 5.0 * te)) / len(GF_CHORDS[b])
            put(sig, step_time(b, st), 0.55 * g)
    # the whistle lead: high sine, portamento between notes, vibrato that blooms on long notes
    lp = np.zeros(n)
    la = np.zeros(n)
    for b in range(BARS):
        for st, m, ln in GF_LEAD[b]:
            i0 = int(step_time(b, st) * sr)
            i1 = min(n, i0 + int(ln * STEP * sr))
            lp[i0:i1] = m
            seg = np.arange(i1 - i0) / sr
            la[i0:i1] = np.clip(seg / 0.03, 0, 1) * np.clip((ln * STEP - seg) / 0.05, 0, 1)
    for i in range(1, n):                                     # hold the last pitch through rests
        if lp[i] == 0:
            lp[i] = lp[i - 1]
    if lp[0] == 0:
        lp[lp == 0] = GF_LEAD[-1][-1][1]
    kg = int(0.07 * sr)                                       # portamento
    lp = np.convolve(np.concatenate([lp[-kg:], lp]), np.ones(kg) / kg, "valid")[: n]
    tvec = np.arange(n) / sr
    vib = 0.35 * np.clip(np.convolve(la, np.ones(int(0.3 * sr)) / int(0.3 * sr), "same"), 0, 1) * np.sin(2 * np.pi * 5.5 * tvec)
    fr = 440 * 2 ** ((lp + vib - 69) / 12)
    phl = 2 * np.pi * np.cumsum(fr) / sr
    out += 0.16 * la * (np.sin(phl) + 0.08 * np.sin(2 * phl))
    crackle = np.zeros(n)
    pos = rng.integers(0, n, int(T_LOOP * 14))
    crackle[pos] = rng.uniform(-1, 1, len(pos))
    crackle = np.convolve(crackle, np.exp(-np.arange(40) / 6), "same") * 0.04
    if HOOK:                                                  # the needle-drop intro
        ti = tt(T_INTRO * 0.55)
        fr = 2600 - 2200 * (ti / ti[-1]) ** 0.7               # rewind: a falling chirp, fast
        rew = np.sin(2 * np.pi * np.cumsum(fr) / sr) * (0.5 + 0.5 * np.sin(2 * np.pi * 22 * ti)) * 0.5
        rew += np.convolve(rng.standard_normal(len(ti)), np.ones(6) / 6, "same") * 0.25
        put(rew * np.clip(ti / 0.02, 0, 1), 0.0, 0.9)
        ts = tt(T_INTRO * 0.45)                               # tape stop: the chord pitches down to nothing
        fts = audio.midi_to_hz(62) * (1 - ts / ts[-1]) ** 1.6
        stop = np.sin(2 * np.pi * np.cumsum(fts) / sr) * (1 - ts / ts[-1]) * 0.6
        put(stop, T_INTRO * 0.55, 0.9)
    return (0.45 * out + crackle).astype(np.float32)


def _worker(o, sim, label, rule):
    layout = get_layout(o)
    name = f"{SCENE}_{label}_{layout.tag}"
    video = studio.OUT_DIR / f"{name}_silent.mp4"
    d = render(layout, sim, video, rule)
    kit.deliver_loop(SCENE, name, layout, video, build_events(sim, layout), d, voice="piano", bed=gfunk_bed() if GF else beat_bed(),
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
    print(f"[{SCENE}] {T_LOOP:.2f}s @ {BPM:.0f} BPM")
    kit.fan_out(_worker, (sim, label, rule), SCENE)


if __name__ == "__main__":
    main()
