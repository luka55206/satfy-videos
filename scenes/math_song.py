"""MATH SONG — 5 functions build one song (math sounds, "building a song"), countdown #6 → #1 THE DROP.

A "math DAW": one lane per function, all pens on one playhead (one bar per window). Each layer joins in turn and the
sound IS the function (x = beats):
  #6 The Melody    y = floor(5 + 2.5 sin(πx/4) + 1.2 sin(3πx/2))   → note y of the A-minor pentatonic (8th notes)
  #5 The Kick      y = 1 + 2.5 e^(−20·(x mod 1))                   → kick pitch follows y (a fast pitch drop = a drum)
  #4 The Bassline  y = r[floor(x/4) mod 4], r = 0, −4, 3, −2        → Am F C G, pulsing 8ths
  #3 The Arpeggio  y = r + t[|(floor(4x) mod 6) − 3|]               → bounces up and down the chord (16ths)
  #2 The Riser     y = floor(x²/4)                                   → x² makes the notes come faster and faster
  #1 THE DROP      everything at once (+ clap, melody doubled an octave up)
124 BPM, 10 bars: melody 1–2, +kick 3, +bass 4, +arp 5–6, riser 7–8 (kick/bass out in 8), drop 9–10.
Audio: everything synthesised here from the functions (original; no samples).
Format after an owner-supplied reference (a "sound of functions" beat build); functions, melody, look and sound are ours.
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

SCENE = "math_song"
BPM = 124.0
BEAT = 60.0 / BPM
BAR = 4 * BEAT
NBARS = 10
T_LOOP = NBARS * BAR
GOLD = (1.0, 0.82, 0.40)

PENTA = [57, 60, 62, 64, 67, 69, 72, 74, 76, 79, 81, 84, 86, 88, 91, 93, 96]   # A minor pentatonic from A3
R = [0, -4, 3, -2]                                                              # Am F C G (semitones from A)
CHORD_T = [(0, 3, 7, 12), (0, 4, 7, 12), (0, 4, 7, 12), (0, 4, 7, 12)]
CHORD_NAMES = ["Am", "F", "C", "G"]
RISER_X0 = 24.0                                                                 # riser starts at bar 7 (beat 24)

# lanes: key, countdown label, colour, active bars, (ymin, ymax), equation, subtitle, intro bar
LANES = [
    ("mel", "#6  The Melody", (0.45, 0.75, 1.00), set(range(10)), (2, 9),
     "y = floor(5 + 2.5 sin(πx/4) + 1.2 sin(3πx/2))", "rounding down puts every note on the scale", 0),
    ("kick", "#5  The Kick", (1.00, 0.45, 0.45), {2, 3, 4, 5, 6, 8, 9}, (1, 3.5),
     "y = 1 + 2.5 e^(−20 · (x mod 1))", "a fast pitch drop sounds like a drum", 2),
    ("bass", "#4  The Bassline", (0.72, 0.55, 1.00), {3, 4, 5, 6, 8, 9}, (-4, 3),
     "y = r[ floor(x/4) mod 4 ],   r = 0, −4, 3, −2", "4 steps = 4 chords:  Am  F  C  G", 3),
    ("arp", "#3  The Arpeggio", (0.45, 1.00, 0.65), {4, 5, 6, 7, 8, 9}, (-4, 15),
     "y = r + t[ |(floor(4x) mod 6) − 3| ]", "| | makes it bounce up and down the chord", 4),
    ("rise", "#2  The Riser", GOLD, {6, 7}, (0, 15),
     "y = floor(x² / 4)", "x² makes the notes come faster and faster", 6),
]
DROP_BAR = 8


def mel_raw(x):
    return 5 + 2.5 * math.sin(math.pi * x / 4) + 1.2 * math.sin(3 * math.pi * x / 2)


def mel_y(x):
    return max(0, min(10, math.floor(mel_raw(math.floor(2 * x) / 2))))


def kick_y(x):
    return 1 + 2.5 * math.exp(-20 * (x % 1.0))


def bass_y(x):
    return R[int(math.floor(x / 4)) % 4]


def arp_y(x):
    c = int(math.floor(x / 4)) % 4
    return R[c] + CHORD_T[c][abs(int(math.floor(4 * x)) % 6 - 3)]


def rise_y(x):
    u = x - RISER_X0
    return math.floor(u * u / 4) if 0 <= u < 8 else 0


FUNC = {"mel": mel_y, "kick": kick_y, "bass": bass_y, "arp": arp_y, "rise": rise_y}


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
        g = cairo.RadialGradient(w / 2, h * 0.45, 0, w / 2, h * 0.45, max(w, h) * 0.7)
        g.add_color_stop_rgb(0.0, 0.07, 0.06, 0.11)
        g.add_color_stop_rgb(1.0, 0.01, 0.01, 0.02)
        ctx.set_source(g)
        ctx.paint()
        xb = t / BEAT                                      # global beat
        bar = min(int(xb // 4), NBARS - 1)
        x0b = 4 * bar
        drop = bar >= DROP_BAR
        kick_pulse = math.exp(-((xb % 1.0) * BEAT) / 0.10) if bar in LANES[1][3] else 0.0
        gx0, gx1 = w * 0.10, w * 0.92
        apps = [0.0 if bar < ln[7] else (smooth((t - ln[7] * BAR) / 0.35) if bar == ln[7] else 1.0) for ln in LANES]
        gap = h * 0.012
        n_eff = max(1.0, sum(apps))
        lh = min(h * 0.16, (h * 0.44 - gap * (n_eff - 1)) / n_eff)     # few lanes = tall lanes; they shrink as layers join
        total = n_eff * lh + (n_eff - 1) * gap
        y_cur = max(h * 0.232, h * 0.452 - total / 2)
        newest = max((ln for ln in LANES if ln[7] <= bar), key=lambda ln: ln[7])
        for li, (key, label, col, active, (ymin, ymax), _, _, intro) in enumerate(LANES):
            if bar < intro:
                continue
            app = apps[li]
            y0 = y_cur
            y_cur += app * (lh + gap)
            on = bar in active
            hl = (key == newest[0] and not drop) or (drop and on)
            a_box = (0.10 + 0.08 * (kick_pulse if drop else 0.0)) * app
            ctx.new_path()
            ctx.rectangle(gx0, y0, gx1 - gx0, lh)
            ctx.set_source_rgba(*col, a_box if hl else 0.04 * app)
            ctx.fill_preserve()
            ctx.set_source_rgba(*col, (0.75 if hl else 0.25) * app)
            ctx.set_line_width(2.5 if hl else 1.2)
            ctx.stroke()
            c.text_centered(label.split("  ")[1], y0 + min(lh * 0.24, h * 0.03), size=min(h * 0.018, lh * 0.17), color=col,
                            alpha=(0.95 if on else 0.45) * app, cx=gx0 + w * 0.10)
            for k in range(1, 4):                          # beat ticks
                xx = gx0 + (gx1 - gx0) * k / 4
                c.lines([(xx, y0 + 3, xx, y0 + lh - 3)], (0.8, 0.8, 0.9), width=1, alpha=0.08 * app)
            if not on:
                c.text_centered("· · ·", y0 + lh * 0.62, size=h * 0.02, color=col, alpha=0.35 * app)
                continue
            fn = FUNC[key]

            def P(x, fn=fn, y0=y0, ymin=ymin, ymax=ymax):
                v = fn(x)
                return (gx0 + (gx1 - gx0) * (x - x0b) / 4,
                        y0 + lh * 0.88 - lh * 0.72 * (v - ymin) / (ymax - ymin))

            npts = 260 if key == "kick" else 160
            xs = [x0b + (xb - x0b) * j / npts for j in range(npts + 1)]
            pts = [P(x) for x in xs]
            c.polylines([pts], col, width=10, alpha=0.12 * app)
            c.polylines([pts], col, width=3, alpha=0.95 * app)
            px, py = pts[-1]
            c.glow(px, py, 9, col, strength=0.6, reach=3)
            c.circle(px, py, 7, (1, 1, 1), alpha=0.95 * app)
        # countdown title + equation of the newest layer (or THE DROP)
        if drop:
            pop = math.exp(-(t - DROP_BAR * BAR) / 0.25)
            c.text_centered("#1  THE DROP", h * 0.72, size=w * 0.085 * (1 + 0.25 * pop), color=GOLD, alpha=1.0)
            c.text_centered("everything at once", h * 0.76, size=w * 0.04, color=(0.95, 0.95, 1.0), alpha=0.9)
            c.text_centered(f"chord: {CHORD_NAMES[bar % 4]}", h * 0.79, size=w * 0.032, color=(0.75, 0.78, 0.88),
                            alpha=0.8, bold=False)
        else:
            key, label, col, _, _, eq, sub, intro = newest
            pop = math.exp(-(t - intro * BAR) / 0.2)
            c.text_centered(label, h * 0.715, size=w * 0.062 * (1 + 0.15 * pop), color=col, alpha=1.0)
            c.text_centered(eq, h * 0.752, size=w * 0.038, color=(0.96, 0.96, 1.0), alpha=0.92, bold=False)
            c.text_centered(sub, h * 0.785, size=w * 0.031, color=(0.75, 0.78, 0.88), alpha=0.85, bold=False)
        c.text_centered("MATH YOU CAN HEAR · BUILDING A SONG", h * 0.205, size=h * 0.0145, color=GOLD, alpha=0.85)
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


# ------------------------------------------------------------------ audio: every part synthesised from its function
SR = audio.SR


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def saw(f, tv, nh=10, bright=6.0):
    out = np.zeros_like(tv)
    for k in range(1, nh + 1):
        if f * k > SR / 2.2:
            break
        out += np.sin(2 * np.pi * f * k * tv) / k * math.exp(-k / bright)
    return out


def song_bed():
    n = int(round(T_LOOP * SR))
    out = np.zeros(n + SR)
    rng = np.random.default_rng(3)

    def add(i0, sig):
        out[i0:i0 + len(sig)] += sig

    def bar_of(x):
        return int(x // 4)

    gate_end = (DROP_BAR * 4 - 0.5)                   # half a beat of silence before the drop
    # melody: 8th notes, repeated notes merged
    notes, x = [], 0.0
    while x < NBARS * 4 - 1e-9:
        m = PENTA[mel_y(x)]
        if notes and notes[-1][2] == m and abs(notes[-1][0] + notes[-1][1] - x) < 1e-9:
            notes[-1][1] += 0.5
        else:
            notes.append([x, 0.5, m])
        x += 0.5
    for xs, d, m in notes:
        if gate_end <= xs < DROP_BAR * 4:
            continue
        dur = d * BEAT
        tv = np.arange(int((dur + 0.12) * SR)) / SR
        env = np.clip(tv / 0.006, 0, 1) * (0.65 + 0.35 * np.exp(-tv / 0.09)) * np.clip((dur + 0.10 - tv) / 0.10, 0, 1)
        sig = 0.5 * (saw(hz(m) * 1.004, tv) + saw(hz(m) * 0.996, tv)) * env
        g = 0.20 if bar_of(xs) < 7 else 0.16
        if bar_of(xs) >= DROP_BAR:
            sig = sig + 0.45 * saw(hz(m + 12), tv, nh=6) * env
            g = 0.21
        add(int(xs * BEAT * SR), g * sig)
    # kick: pitch literally follows y = 1 + 2.5 e^(−20 (x mod 1))
    L = int(BEAT * SR)
    tb = np.arange(L) / SR
    yk = 1 + 2.5 * np.exp(-20 * tb / BEAT)
    fk = 48 * 2 ** ((yk - 1) * 1.15)
    kick = np.sin(2 * np.pi * np.cumsum(fk) / SR) * np.exp(-tb / 0.16)
    for b in range(NBARS * 4):
        if bar_of(b) in LANES[1][3]:
            add(int(b * BEAT * SR), (0.72 if bar_of(b) >= DROP_BAR else 0.46) * kick)
    # bass: 8th pulses on r[floor(x/4) mod 4]
    for k in range(NBARS * 8):
        xs = k / 2
        if bar_of(xs) not in LANES[2][3]:
            continue
        m = 33 + bass_y(xs)
        dur = 0.5 * BEAT
        tv = np.arange(int(dur * SR)) / SR
        env = np.clip(tv / 0.005, 0, 1) * np.exp(-tv / 0.18) * np.clip((dur - tv) / 0.02, 0, 1)
        sig = (0.7 * np.sin(2 * np.pi * hz(m) * tv) + 0.5 * saw(hz(m), tv, nh=6, bright=3)) * env
        add(int(xs * BEAT * SR), (0.34 if bar_of(xs) >= DROP_BAR else 0.21) * sig)
    # arpeggio: 16ths
    for k in range(NBARS * 16):
        xs = k / 4
        if bar_of(xs) not in LANES[3][3] or gate_end <= xs < DROP_BAR * 4:
            continue
        m = 57 + 12 + arp_y(xs)
        tv = np.arange(int(0.22 * SR)) / SR
        sig = (np.sin(2 * np.pi * hz(m) * tv) + 0.35 * np.sin(4 * np.pi * hz(m) * tv)) * np.exp(-tv / 0.07)
        add(int(xs * BEAT * SR), (0.10 if bar_of(xs) >= DROP_BAR else 0.06) * sig)
    # riser: a note every time floor(x²/4) steps, + a noise sweep
    for mstep in range(16):
        xs = RISER_X0 + 2 * math.sqrt(mstep)
        if xs >= gate_end:
            break
        mm = PENTA[min(mstep, len(PENTA) - 1)] + 12
        tv = np.arange(int(0.18 * SR)) / SR
        sig = (np.sin(2 * np.pi * hz(mm) * tv) + 0.3 * np.sin(6 * np.pi * hz(mm) * tv)) * np.exp(-tv / 0.08)
        add(int(xs * BEAT * SR), (0.10 + 0.010 * mstep) * sig)
    i0, i1 = int(RISER_X0 * BEAT * SR), int(gate_end * BEAT * SR)
    nz = rng.uniform(-1, 1, i1 - i0)
    nz = np.diff(np.concatenate([[0], nz]))
    out[i0:i1] += 0.05 * nz * np.linspace(0, 1, i1 - i0) ** 2
    # drop: crash + claps on 2 and 4
    tv = np.arange(int(1.6 * SR)) / SR
    crash = np.diff(np.concatenate([[0], rng.uniform(-1, 1, len(tv))])) * np.exp(-tv / 0.5)
    add(int(DROP_BAR * BAR * SR), 0.10 * crash)
    tv = np.arange(int(0.15 * SR)) / SR
    for b in range(DROP_BAR * 4, NBARS * 4):
        if b % 2 == 1:
            cl = np.diff(np.concatenate([[0], rng.uniform(-1, 1, len(tv))])) * np.exp(-tv / 0.045)
            add(int(b * BEAT * SR), 0.22 * cl)
    # soft pad on the chords
    for b in range(NBARS):
        c = b % 4
        tv = np.arange(int(BAR * SR)) / SR
        env = np.clip(tv / 0.15, 0, 1) * np.clip((BAR - tv) / 0.15, 0, 1)
        pad = sum(np.sin(2 * np.pi * hz(45 + 12 + R[c] + t_) * tv) for t_ in CHORD_T[c][:3]) / 3
        add(int(b * BAR * SR), (0.05 if b < DROP_BAR else 0.07) * env * pad)
    tail = out[n:]
    out = out[:n]
    out[: len(tail)] += tail
    return out.astype(np.float32)


def _worker(o, sim, label, rule):
    layout = get_layout(o)
    name = f"{SCENE}_{label}_{layout.tag}"
    video = studio.OUT_DIR / f"{name}_silent.mp4"
    d = render(layout, sim, video, rule)
    kit.deliver_loop(SCENE, name, layout, video, [], d, voice="piano", bed=song_bed())


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
