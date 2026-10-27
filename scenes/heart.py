"""HEART CURVE — nested hearts drawn by two mirrored pens (simple test version).

The classic heart curve  x = 16 sin^3 t,  y = 13 cos t - 5 cos 2t - 2 cos 3t - cos 4t.
Two glowing pens start together at the top dip and trace the left and right halves
down to the tip, where they meet in a soft bloom. Then a smaller heart starts inside
it, a little faster each time (the escalation rule), the colours drifting rose ->
violet -> gold. When the smallest heart closes, the whole set beats twice like a
heart, then dissolves back to the empty frame 0 (loop).

Audio (original synthesis only): a glass-harp note each time the pens cover another
sixth of their half (so the notes speed up as the hearts get faster), a soft chord
where they meet, and a quiet sine pad under everything. No melody, no samples.

    ./run.ps1 -Scene heart -Fast -Still -Frame 300
    ./run.ps1 -Scene heart -Fast
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

SCENE = "heart"
N_HEARTS = 7
DUR0, DUR_K = 3.2, 0.86        # first heart takes 3.2 s, each next one 14% less
GAP_S = 0.25                   # breath between hearts
BEAT_S = 2.4                   # lub-dub x2 after the last heart
FADE_S = 1.6                   # dissolve to the empty frame 0
NOTES_PER_HEART = 6
Y_MID = -2.5                   # vertical centre of the curve in curve units
COLS = [(1.00, 0.36, 0.52), (1.00, 0.45, 0.66), (0.96, 0.50, 0.85), (0.80, 0.52, 1.00),
        (0.62, 0.58, 1.00), (1.00, 0.70, 0.55), (1.00, 0.84, 0.50)]


def heart_xy(t):
    """Curve units, +y UP. t=0 top dip, t=pi bottom tip, sign of t picks the side."""
    s = math.sin(t)
    return (16 * s * s * s,
            13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t))


def schedule():
    """[(t_start, t_end, scale)] per heart + the end of the drawing phase."""
    out, t = [], 0.0
    for i in range(N_HEARTS):
        d = DUR0 * DUR_K ** i
        out.append((t, t + d, 1.0 - i * 0.125))
        t += d + GAP_S
    return out, t - GAP_S


def ease(p):
    """Gentle in/out on each stroke so the pens glide, never jerk."""
    p = min(max(p, 0.0), 1.0)
    return 0.5 - 0.5 * math.cos(math.pi * p)


def simulate():
    sched, t_draw = schedule()
    t_beat = t_draw + 0.5
    t_fade = t_beat + BEAT_S
    return {"sched": sched, "t_draw": t_draw, "t_beat": t_beat, "t_fade": t_fade,
            "nf": int(round((t_fade + FADE_S) * FPS))}


def beat(sim, t):
    """Two lub-dub pulses: scale offset 0..~0.05."""
    u = t - sim["t_beat"]
    if u < 0 or u > BEAT_S:
        return 0.0
    v = 0.0
    for c, a in ((0.15, 0.05), (0.42, 0.03), (1.35, 0.05), (1.62, 0.03)):
        v += a * math.exp(-((u - c) / 0.09) ** 2)
    return v


def _bg(canvas, layout):
    w, h = layout.w, layout.h
    g = cairo.RadialGradient(w / 2, h * 0.45, 0, w / 2, h * 0.45, max(w, h) * 0.75)
    g.add_color_stop_rgb(0.0, 0.10, 0.03, 0.09)
    g.add_color_stop_rgb(1.0, 0.01, 0.00, 0.02)
    canvas.ctx.set_source(g)
    canvas.ctx.paint()


def draw(canvas, layout, sim, f, rule):
    w, h = layout.w, layout.h
    t = f * DT
    vertical = h > w
    cx, cy = w / 2, h * (0.43 if vertical else 0.50)
    unit = min(w * 0.86 / 32.0, h * (0.70 if vertical else 0.80) / 29.5)
    keep = 1.0 - smooth((t - sim["t_fade"]) / FADE_S)
    pulse = 1.0 + beat(sim, t)
    _bg(canvas, layout)

    def to_px(x, y, sc):
        k = unit * sc * pulse
        return cx + x * k, cy - (y - Y_MID) * k

    for i, (t0, t1, sc) in enumerate(sim["sched"]):
        if t < t0:
            break
        col = COLS[i % len(COLS)]
        p = ease((t - t0) / (t1 - t0))
        n = max(2, int(140 * p) + 1)
        left = [to_px(*heart_xy(-math.pi * p * k / (n - 1)), sc) for k in range(n)]
        right = [to_px(*heart_xy(math.pi * p * k / (n - 1)), sc) for k in range(n)]
        a = keep * (1.0 if t >= t1 else 0.95)
        canvas.polylines([left, right], col, width=26, alpha=0.07 * a)   # soft halo
        canvas.polylines([left, right], col, width=12, alpha=0.16 * a)
        canvas.polylines([left, right], col, width=4.5, alpha=0.95 * a)
        canvas.polylines([left, right], (1, 1, 1), width=1.4, alpha=0.45 * a)
        if t < t1:                                       # the two pens
            for pts in (left, right):
                x, y = pts[-1]
                fade_in = smooth(t / 0.35) if i == 0 else 1.0
                canvas.glow(x, y, 9, col, strength=0.55 * fade_in, reach=4.0)
                canvas.circle(x, y, 7, (1, 1, 1), alpha=0.95 * fade_in)
        dt_meet = t - t1                                  # bloom at the tip
        if 0 <= dt_meet < 0.9:
            x, y = to_px(*heart_xy(math.pi), sc)
            e = dt_meet / 0.9
            canvas.glow(x, y, 10 + 40 * e, col, strength=0.5 * (1 - e), reach=2.5)
            canvas.ring(x, y, 8 + 70 * smooth(e), col, width=3, alpha=0.6 * (1 - e))

    if t >= sim["t_beat"]:                                # warm core glow on each beat
        b = beat(sim, t) / 0.05
        x, y = to_px(0, Y_MID, 1.0)
        canvas.glow(x, y, unit * 3, COLS[0], strength=0.22 * b * keep, reach=3.0)
    if rule:
        canvas.caption(rule, alpha=min(1.0, t / 0.4) * keep, layout=layout)
    canvas.watermark(layout)


def render(layout, sim, out_path, rule, still_frame=None):
    canvas = Canvas(layout.w, layout.h, studio.render_scale())
    writer = None if still_frame is not None else VideoWriter(out_path, canvas, FPS)
    for f in range(sim["nf"]):
        if still_frame is not None and f != still_frame:
            continue
        draw(canvas, layout, sim, f, rule)
        if writer is None:
            studio.save_still(canvas, out_path)
            return f / FPS
        writer.write_frame()
    writer.close()
    return sim["nf"] / FPS


def build_events(sim, layout):
    walker = audio.ScaleWalker(root_midi=62, scale=audio.PENTA_MAJOR, span=10, pattern="updown")
    out = []
    for i, (t0, t1, sc) in enumerate(sim["sched"]):
        for k in range(NOTES_PER_HEART):
            # time at which the eased pen reaches k/NOTES of its half
            p = k / NOTES_PER_HEART
            u = math.acos(1 - 2 * p) / math.pi
            t = t0 + u * (t1 - t0)
            x = layout.w * (0.5 + 0.38 * sc * math.sin(math.pi * p) * (1 if k % 2 else -1))
            out.append({"t": round(t, 4), "note": walker.next(), "gain": 0.42 + 0.03 * i,
                        "x": round(x, 1)})
        for j, note in enumerate((50, 57, 62, 66)):       # D major chord where the pens meet
            out.append({"t": round(t1 + 0.04 * j, 4), "note": note,
                        "gain": 0.40, "x": layout.w / 2})
    for c in (0.15, 0.42, 1.35, 1.62):                     # heartbeat: soft low notes
        out.append({"t": round(sim["t_beat"] + c, 4), "note": 38 if c in (0.15, 1.35) else 45,
                    "gain": 0.55, "x": layout.w / 2})
    return sorted(out, key=lambda e: e["t"])


def pad(sim):
    """Quiet sustained sine pad (D - A - D - F#), swells in, decays to silence before the seam."""
    sr = audio.SR
    dur = sim["nf"] / FPS
    n = int(dur * sr)
    t = np.arange(n) / sr
    sig = np.zeros(n)
    for m, a in ((50, 1.0), (57, 0.7), (62, 0.5), (66, 0.35)):
        f0 = audio.midi_to_hz(m)
        sig += a * (np.sin(2 * np.pi * f0 * t) + 0.5 * np.sin(2 * np.pi * f0 * 1.003 * t))
    lfo = 0.85 + 0.15 * np.sin(2 * np.pi * 0.12 * t)
    env = np.clip(t / 0.6, 0, 1) * np.clip((dur - 0.6 - t) / 2.0, 0, 1) ** 2
    return (0.018 * sig * lfo * env).astype(np.float32)


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
    print(f"[{SCENE}] {sim['nf'] / FPS:.2f}s draw_end={sim['t_draw']:.2f}s")
    kit.fan_out(_worker, (sim, label, rule), SCENE)


def _worker(o, sim, label, rule):
    layout = get_layout(o)
    name = f"{SCENE}_{label}_{layout.tag}"
    video = studio.OUT_DIR / f"{name}_silent.mp4"
    d = render(layout, sim, video, rule)
    events = build_events(sim, layout)
    kit.deliver(SCENE, name, layout, video, events, d, True, voice="glassharp", bed=pad(sim))


if __name__ == "__main__":
    main()
