"""HEART BEAT — the heart-curve heart, beating, with a heart-rate monitor; bpm climbs 72 -> ~190.

Episode of the channel's best stay-to-watch format (heart_eq, 56%): the classic heart curve
x = 16 sin^3 t, y = 13 cos t - 5 cos 2t - 2 cos 3t - cos 4t, already glowing and beating at frame 0.
Under it a heart-rate monitor trace scrolls with a QRS spike per beat. The heart rate climbs,
faster and faster, to ~190 bpm (the escalation rule): the beats hit harder, the glow brightens,
small hearts float up on every beat. Then it calms back to 72 bpm. NONSTOP LOOP: the beat
times are periodic over the clip (whole number of beats, bpm(T) = bpm(0)), the monitor trace
and the floating hearts are computed from that periodic beat list, so the last frame flows
straight into frame 0.

v4 (owner): her REPLY arrives at 2 s, after two calm beats-worth of 72 bpm. A phone-style banner
("Message · now / Love you too ♥") slides in with a soft original two-tone ding, and the bpm starts
climbing exactly as it lands (the curve is solved so the climb starts at MSG_T0 + MSG_IN); the loop
now tells the story calm -> message -> racing -> calm -> next message.

Audio (original synthesis only): a soft low two-part heartbeat thump per beat, and an
ORIGINAL classical-style piece (Mozart/Vivaldi manner, not any existing tune): piano Alberti
bass + a composed lyrical melody + a bowed-string chord pad, one quarter note per heartbeat,
so the music accelerates and calms with the heart. 32 beats = the 8-bar phrase, which loops.

    ./run.ps1 -Scene heart_beat -Fast -Still -Frame 600
    ./run.ps1 -Scene heart_beat -Fast
"""
import math
import random
import sys
from pathlib import Path

import cairo
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib import audio, kit, studio  # noqa: E402
from lib.kit import DT, FPS, arg, smooth  # noqa: E402
from lib.layouts import get_layout  # noqa: E402
from lib.studio import Canvas, VideoWriter  # noqa: E402

SCENE = "heart_beat"
BPM0, BPM1 = 72.0, 190.0
N_BEATS = 32                     # 8 bars of 4: the music's 8-bar phrase loops exactly with the clip
ECG_WIN = 2.4                    # seconds of trace on the monitor
SPAWN_BPM = 95.0                 # floating hearts only above this (so none cross the seam)
LIFE = 1.8
MSG_T0, MSG_IN, MSG_HOLD, MSG_OUT = 2.00, 0.28, 4.5, 0.45   # her reply: lands at 2 s, the race starts
MSG_TEXT = "Love you too ♥"                                    # owner: a positive answer, <= 3 words
ROSE = (1.00, 0.30, 0.48)
PINK = (1.00, 0.55, 0.70)
WARM = (1.00, 0.80, 0.55)


def bpm_u(u, u0):
    """Calm 72 until the reply lands (u0), then an accelerating climb to the peak at ~83%."""
    jolt = smooth((u - u0) * T_GUESS / 0.6)          # instant reaction: ~+30 bpm in 0.6 s
    rise = 0.25 * jolt + 0.75 * smooth((u - u0) / (0.83 - u0)) ** 1.4
    fall = 1.0 - smooth((u - 0.86) / 0.13)           # calm back down by the seam
    return BPM0 + (BPM1 - BPM0) * rise * fall


T_GUESS = 16.0                   # refined by _solve_loop (only the jolt's 0.6 s uses it)


def _solve_loop():
    """Loop length that holds exactly N_BEATS beats while the climb starts at MSG_T0 + MSG_IN
    (absolute seconds), found by fixed-point iteration (T and u0 depend on each other)."""
    T = 16.0
    for _ in range(30):
        u0 = (MSG_T0 + MSG_IN) / T
        T = N_BEATS * 60.0 / float(np.mean([bpm_u((i + 0.5) / 4000, u0) for i in range(4000)]))
        globals()["T_GUESS"] = T
    return T, (MSG_T0 + MSG_IN) / T


T_LOOP, U_RISE = _solve_loop()


def bpm_raw(t):
    return bpm_u(t / T_LOOP, U_RISE)


def simulate():
    """Beat times on [0, T): phase integrated from bpm, rescaled to a whole number of beats."""
    n = int(round(T_LOOP * FPS))
    ts = np.arange(n * 8 + 1) * (T_LOOP / (n * 8))
    rate = np.array([bpm_raw(t) for t in ts]) / 60.0
    ph = np.concatenate([[0.0], np.cumsum((rate[1:] + rate[:-1]) * 0.5 * np.diff(ts))])
    k = round(ph[-1]) / ph[-1]
    ph *= k
    beats = [float(np.interp(i, ph, ts)) for i in range(int(round(ph[-1])))]
    return {"nf": n, "beats": beats, "k": k, "ph_t": ts, "ph": ph}


def bpm_at(sim, t):
    return bpm_raw(t % T_LOOP) * sim["k"]


def beats_around(sim, t0, t1):
    """Beat times in [t0, t1], using the periodic extension (wraps across the seam)."""
    out = []
    for b in sim["beats"]:
        for off in (-T_LOOP, 0.0, T_LOOP):
            x = b + off
            if t0 <= x <= t1:
                out.append(x)
    return sorted(out)


def pulse(sim, t):
    """Heart scale offset: lub at the beat, dub 0.3 beat later."""
    v = 0.0
    for b in beats_around(sim, t - 0.6, t + 0.1):
        per = 60.0 / bpm_at(sim, b)
        gain = 0.045 + 0.05 * (bpm_at(sim, b) - BPM0) / (BPM1 - BPM0)
        for d, a in ((0.0, 1.0), (0.30 * per, 0.55)):
            x = (t - b - d) / 0.055
            if -3 < x < 6:
                v += gain * a * (math.exp(-x * x) if x < 0 else math.exp(-x * 0.9))
    return v


def ecg(sim, t):
    """Monitor trace value at time t (P, QRS, T shape around each beat)."""
    v = 0.0
    for b in beats_around(sim, t - 0.5, t + 0.3):
        x = t - b
        v += 0.12 * math.exp(-((x + 0.12) / 0.025) ** 2)            # P
        v -= 0.18 * math.exp(-((x + 0.02) / 0.008) ** 2)            # Q
        v += 1.00 * math.exp(-(x / 0.010) ** 2)                     # R
        v -= 0.28 * math.exp(-((x - 0.022) / 0.010) ** 2)           # S
        v += 0.22 * math.exp(-((x - 0.20) / 0.045) ** 2)            # T
    return v


def heart_path(n=240):
    ts = np.linspace(0, 2 * math.pi, n)
    s = np.sin(ts)
    return 16 * s ** 3, 13 * np.cos(ts) - 5 * np.cos(2 * ts) - 2 * np.cos(3 * ts) - np.cos(4 * ts)


HX, HY = heart_path()


def small_heart(ctx, x, y, r):
    xs, ys = heart_path(40)
    k = r / 17.0
    ctx.move_to(x + xs[0] * k, y - (ys[0] + 2.5) * k)
    for a, b in zip(xs[1:], ys[1:]):
        ctx.line_to(x + a * k, y - (b + 2.5) * k)
    ctx.close_path()


class Scene:
    def __init__(self, layout, sim):
        self.L, self.sim = layout, sim
        self.canvas = Canvas(layout.w, layout.h, studio.render_scale())
        self.vertical = layout.h > layout.w
        w, h = layout.w, layout.h
        self.hc = (w / 2, h * (0.355 if self.vertical else 0.40))
        self.unit = (w * 0.50 / 32.0) if self.vertical else (h * 0.40 / 29.0)

    def draw(self, f, rule):
        sim, L, c = self.sim, self.L, self.canvas
        w, h = L.w, L.h
        t = f * DT
        bpm = bpm_at(sim, t)
        heat = (bpm - BPM0) / (BPM1 - BPM0)
        ctx = c.ctx
        g = cairo.RadialGradient(w / 2, self.hc[1], 0, w / 2, self.hc[1], max(w, h) * 0.7)
        g.add_color_stop_rgb(0.0, 0.10 + 0.06 * heat, 0.02, 0.06 + 0.02 * heat)
        g.add_color_stop_rgb(1.0, 0.015, 0.0, 0.02)
        ctx.set_source(g)
        ctx.paint()

        # floating hearts (spawned per beat above SPAWN_BPM, deterministic per beat)
        for b in beats_around(sim, t - LIFE, t):
            bb = bpm_at(sim, b)
            if bb < SPAWN_BPM or (b % T_LOOP) > T_LOOP - LIFE - 0.2:   # calm, empty seam
                continue
            idx = int(round((b % T_LOOP) * 1000))
            rng = random.Random(idx)
            for _ in range(1 + int((bb - SPAWN_BPM) / 30)):
                age = (t - b) / LIFE
                ang = rng.uniform(-math.pi, math.pi)
                r0 = self.unit * rng.uniform(8, 15)
                x = self.hc[0] + math.cos(ang) * r0 + rng.uniform(-30, 30) * age
                y = self.hc[1] - math.sin(ang) * r0 * 0.8 - self.unit * 14 * age
                a = math.sin(math.pi * min(1.0, age)) * 0.75
                small_heart(ctx, x, y, rng.uniform(10, 22))
                ctx.set_source_rgba(*(PINK if rng.random() < 0.5 else ROSE), a)
                ctx.fill()

        # the heart
        p = pulse(sim, t)
        k = self.unit * (1.0 + p)
        pts = [(self.hc[0] + x * k, self.hc[1] - (y + 2.5) * k) for x, y in zip(HX, HY)]
        gr = cairo.RadialGradient(self.hc[0], self.hc[1], 0, self.hc[0], self.hc[1], 17 * k)
        gr.add_color_stop_rgba(0.0, *PINK, 0.30 + 0.25 * heat + 2.0 * p)
        gr.add_color_stop_rgba(1.0, *ROSE, 0.10 + 0.10 * heat)
        ctx.move_to(*pts[0])
        for q in pts[1:]:
            ctx.line_to(*q)
        ctx.close_path()
        ctx.set_source(gr)
        ctx.fill()
        glow = 0.10 + 0.10 * heat + 1.5 * p
        c.polylines([pts], ROSE, width=34, alpha=min(0.35, glow * 0.5))
        c.polylines([pts], ROSE, width=14, alpha=min(0.6, glow))
        c.polylines([pts], (1.0, 0.75, 0.82), width=4.5, alpha=0.95)

        # monitor: a graph-paper panel (bigger, the second star of the clip)
        x0, x1 = w * 0.05, w * 0.95
        yc, amp = (h * 0.625, h * 0.068) if self.vertical else (h * 0.82, h * 0.09)
        top, bot = yc - amp * 1.25, yc + amp * 0.55
        ctx.rectangle(x0 - 10, top, x1 - x0 + 20, bot - top)
        ctx.set_source_rgba(0.12, 0.02, 0.06, 0.55)
        ctx.fill_preserve()
        ctx.set_source_rgba(*ROSE, 0.35)
        ctx.set_line_width(2)
        ctx.stroke()
        step = (bot - top) / 8.0
        grid = [(x, top, x, bot) for x in np.arange(x0, x1 + 1, step)]
        grid += [(x0 - 10, y, x1 + 10, y) for y in np.arange(top + step, bot, step)]
        c.lines(grid, ROSE, width=1, alpha=0.12)
        n = 420
        tr = []
        for i in range(n + 1):
            tt = t - ECG_WIN * (1 - i / n)
            tr.append((x0 + (x1 - x0) * i / n, yc - amp * ecg(sim, tt)))
        c.polylines([tr], ROSE, width=14, alpha=0.15)
        c.polylines([tr], (1.0, 0.55, 0.65), width=4, alpha=0.95)
        c.glow(*tr[-1], 6, PINK, strength=0.7, reach=4)
        c.circle(*tr[-1], 5, (1, 1, 1), alpha=0.95)

        self.message(t)

        # HUD
        fs = w * (0.05 if self.vertical else 0.026)
        eq_y, bpm_y = (h * 0.185, h * 0.765) if self.vertical else (h * 0.07, h * 0.96)
        c.text_centered("x = 16 sin³t     y = 13 cos t − 5 cos 2t − 2 cos 3t − cos 4t", eq_y,
                        size=fs * 0.55, color=(0.95, 0.90, 0.95), alpha=0.85, bold=False, max_w=w * 0.9)
        col = tuple(a + (b - a) * heat for a, b in zip((1, 1, 1), WARM))
        c.text_centered(f"♥ {bpm:.0f} bpm", bpm_y, size=fs * (1.15 + 0.25 * heat), color=col, alpha=1.0)
        if rule:
            c.caption(rule, alpha=1.0, layout=L)
        c.watermark(L)


def _round_rect(ctx, x, y, w, h, r):
    ctx.new_sub_path()
    ctx.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    ctx.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    ctx.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    ctx.arc(x + r, y + r, r, math.pi, 1.5 * math.pi)
    ctx.close_path()


def _message(self, t):
    """Phone-style message banner: slides in at MSG_T0, holds, fades. Invisible at the seam."""
    u = t - MSG_T0
    if u <= 0 or u > MSG_IN + MSG_HOLD + MSG_OUT:
        return
    a = smooth(u / MSG_IN) * (1.0 - smooth((u - MSG_IN - MSG_HOLD) / MSG_OUT))
    slide = (1.0 - smooth(u / MSG_IN)) * 40.0
    L, c = self.L, self.canvas
    ctx = c.ctx
    w, h = L.w, L.h
    bw, bh = w * 0.80, h * 0.068
    x = (w - bw) / 2
    y = (h * 0.215 if self.vertical else h * 0.16) - slide
    _round_rect(ctx, x + 4, y + 6, bw, bh, bh * 0.28)                 # soft shadow
    ctx.set_source_rgba(0, 0, 0, 0.35 * a)
    ctx.fill()
    _round_rect(ctx, x, y, bw, bh, bh * 0.28)
    ctx.set_source_rgba(0.16, 0.13, 0.18, 0.93 * a)
    ctx.fill_preserve()
    ctx.set_source_rgba(1, 1, 1, 0.12 * a)
    ctx.set_line_width(1.5)
    ctx.stroke()
    ic = bh * 0.30                                                    # avatar: a pink disc with a heart
    icx, icy = x + bh * 0.52, y + bh / 2
    ctx.arc(icx, icy, ic, 0, 2 * math.pi)
    ctx.set_source_rgba(*ROSE, a)
    ctx.fill()
    small_heart(ctx, icx, icy + ic * 0.05, ic * 0.62)
    ctx.set_source_rgba(1, 1, 1, a)
    ctx.fill()
    tx = x + bh * 1.02
    c._font(bh * 0.28, True)
    ctx.set_source_rgba(1, 1, 1, 0.95 * a)
    ctx.move_to(tx, y + bh * 0.42)
    ctx.show_text("Message")
    c._font(bh * 0.24, False)
    ext = ctx.text_extents("now")
    ctx.set_source_rgba(0.75, 0.72, 0.80, a)
    ctx.move_to(x + bw - bh * 0.35 - ext.x_advance, y + bh * 0.42)
    ctx.show_text("now")
    c._font(bh * 0.28, False)
    ctx.set_source_rgba(0.92, 0.90, 0.95, a)
    ctx.move_to(tx, y + bh * 0.78)
    ctx.show_text(MSG_TEXT)


Scene.message = _message


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


# ORIGINAL classical-style piece (Mozart/Vivaldi MANNER, no existing tune): D major,
# I-vi-IV-V | I-vi-ii-V, Alberti bass in eighths, a lyrical melody, a string-like chord pad.
# One beat of the heart = one quarter note, so the music speeds up and calms with the bpm.
CHORDS = [  # (bass root, fifth, third) for the Alberti pattern, and the pad chord
    ((50, 57, 54), (62, 66, 69)),   # D
    ((47, 54, 50), (62, 66, 71)),   # Bm
    ((43, 50, 47), (62, 67, 71)),   # G
    ((45, 52, 49), (61, 64, 69)),   # A
    ((50, 57, 54), (62, 66, 69)),   # D
    ((47, 54, 50), (62, 66, 71)),   # Bm
    ((40, 47, 43), (64, 67, 71)),   # Em
    ((45, 52, 49), (61, 64, 69)),   # A
]
MELODY = [  # per bar: (beat within the bar, midi); composed for this clip
    [(0, 78), (2, 76), (3, 74)],
    [(0, 71), (1, 74), (2, 78), (3, 76)],
    [(0, 74), (2, 79), (3, 78)],
    [(0, 76), (1, 73), (2, 69)],
    [(0, 78), (1, 81), (2, 78), (3, 76)],
    [(0, 74), (1, 78), (2, 83), (3, 81)],
    [(0, 79), (1, 78), (2, 76), (3, 79)],
    [(0, 76), (1, 73), (2, 76), (3, 73)],
]
ALBERTI = (0, 1, 2, 1)          # root, fifth, third, fifth over two beats (eighths)


def beat_time(sim, i):
    """Time of beat i (any integer), using the periodic extension."""
    nb = len(sim["beats"])
    q, r = divmod(i, nb)
    return sim["beats"][r] + q * T_LOOP


def at_beat(sim, x):
    """Time at fractional beat position x (linear between beats), wrapped into the loop."""
    i = math.floor(x)
    a, b = beat_time(sim, i), beat_time(sim, i + 1)
    return (a + (b - a) * (x - i)) % T_LOOP


def build_events(sim, layout):
    out = []
    nb = len(sim["beats"])
    for i in range(nb):
        bar, pos = divmod(i, 4)
        bass, _ = CHORDS[bar % len(CHORDS)]
        heat = (bpm_at(sim, beat_time(sim, i)) - BPM0) / (BPM1 - BPM0)
        for j in range(2):                                   # Alberti eighths
            note = bass[ALBERTI[(pos % 2) * 2 + j]]
            out.append({"t": round(at_beat(sim, i + 0.5 * j), 4), "note": note,
                        "gain": round(0.20 + 0.06 * heat, 3), "x": layout.w * 0.42})
        for off, note in MELODY[bar % len(MELODY)]:
            if off == pos:
                out.append({"t": round(at_beat(sim, i) + 0.004, 4), "note": note,
                            "gain": round(0.42 + 0.12 * heat, 3), "x": layout.w * 0.58})
    return sorted(out, key=lambda e: e["t"])


def strings_bed(sim):
    """Soft string-like chord per bar (bowed: slow attack, vibrato), periodic over the loop."""
    sr = audio.SR
    n = int(round(T_LOOP * sr))
    out = np.zeros(n, dtype=np.float64)
    nb = len(sim["beats"])
    for bar in range(nb // 4):
        t0, t1 = beat_time(sim, bar * 4), beat_time(sim, bar * 4 + 4)
        L = int((t1 - t0 + 0.25) * sr)
        tt = np.arange(L) / sr
        env = np.clip(tt / 0.18, 0, 1) * np.clip((t1 - t0 + 0.25 - tt) / 0.30, 0, 1)
        sig = np.zeros(L)
        for m in CHORDS[bar % len(CHORDS)][1]:
            f0 = audio.midi_to_hz(m)
            vib = 1 + 0.004 * np.sin(2 * np.pi * 5.2 * tt + m)
            ph = 2 * np.pi * np.cumsum(f0 * vib) / sr
            for h_, a in ((1, 1.0), (2, 0.45), (3, 0.25), (4, 0.12), (5, 0.06)):
                sig += a * np.sin(h_ * ph)
        idx = (np.arange(L) + int(round(t0 * sr))) % n
        np.add.at(out, idx, sig * env)
    return out


def heartbeat_bed(sim):
    """Soft low lub-dub per beat, periodic over the loop (beats near the end wrap to the head)."""
    sr = audio.SR
    n = int(round(T_LOOP * sr))
    out = np.zeros(n, dtype=np.float64)
    L = int(0.22 * sr)
    tt = np.arange(L) / sr

    def thump(f0, a):
        f = f0 * (1 + 0.6 * np.exp(-tt * 40))
        ph = 2 * np.pi * np.cumsum(f) / sr
        env = (1 - np.exp(-tt * 400)) * np.exp(-tt * 18)
        return a * env * (np.sin(ph) + 0.25 * np.sin(2 * ph))

    lub, dub = thump(58, 1.0), thump(66, 0.6)
    for b in sim["beats"]:
        per = 60.0 / bpm_at(sim, b)
        for d, s in ((0.0, lub), (0.30 * per, dub)):
            i0 = int(round((b + d) * sr))
            idx = (np.arange(L) + i0) % n
            np.add.at(out, idx, s)
    return (0.30 * out + 0.010 * strings_bed(sim) + 0.45 * message_ding(n)).astype(np.float32)


def message_ding(n):
    """An ORIGINAL soft two-tone notification (not any phone maker's sound): two bell-like
    sines a fifth apart, short and round, at the moment the banner lands."""
    sr = audio.SR
    out = np.zeros(n)
    for t0, f0 in ((MSG_T0 + 0.02, 1318.5), (MSG_T0 + 0.15, 1975.5)):
        L = int(0.55 * sr)
        tt = np.arange(L) / sr
        env = (1 - np.exp(-tt * 900)) * np.exp(-tt * 7.5)
        sig = env * (np.sin(2 * np.pi * f0 * tt) + 0.25 * np.sin(2 * np.pi * 2.0 * f0 * tt) * np.exp(-tt * 12))
        i0 = int(round(t0 * sr))
        out[i0:i0 + L] += sig[: max(0, n - i0)]
    return out


def _worker(o, sim, label, rule):
    layout = get_layout(o)
    name = f"{SCENE}_{label}_{layout.tag}"
    video = studio.OUT_DIR / f"{name}_silent.mp4"
    d = render(layout, sim, video, rule)
    kit.deliver_loop(SCENE, name, layout, video, build_events(sim, layout), d,
                     voice="piano", bed=heartbeat_bed(sim), peak_db=-6.0)


def main():
    label, rule = arg("--label", "v1"), arg("--rule", "")
    studio.OUT_DIR.mkdir(exist_ok=True)
    sim = simulate()
    if kit.has("--still"):
        layout = get_layout(kit.orients()[0])
        f = int(arg("--frame", "600"))
        png = studio.OUT_DIR / f"{SCENE}_{label}_f{f}_{layout.tag}.png"
        render(layout, sim, png, rule, still_frame=f)
        print(f"[{SCENE}] -> {png}")
        return
    print(f"[{SCENE}] {T_LOOP:.1f}s beats={len(sim['beats'])} k={sim['k']:.4f} "
          f"per5s={kit.density_report([{'t': b} for b in sim['beats']], T_LOOP)}")
    kit.fan_out(_worker, (sim, label, rule), SCENE)


if __name__ == "__main__":
    main()
