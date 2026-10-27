"""HEART EQUATION — y = x^(2/3) + 0.9 sin(a*pi*x) sqrt(3.3 - x^2), a grows (test version).

The equation sits on screen with a live readout of a. At a = 0 the graph is two soft
humps; as a rises the sine packs ever more waves under the envelope, and the
oscillation fills in until the graph IS a solid heart (a = 20). a grows faster and
faster (the escalation rule). Loop: a glides back down to 0, the exact frame-0 graph.

Audio (original synthesis only): a glass-harp note every time a passes another 0.5
(so the notes speed up as a accelerates), a soft chord at a = 20, a quiet sine pad.

    ./run.ps1 -Scene heart_eq -Fast -Still -Frame 900
    ./run.ps1 -Scene heart_eq -Fast
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

SCENE = "heart_eq"
A_MAX = 20.0
GROW_S = 22.0                  # a: 0 -> A_MAX, accelerating
HOLD_S = 0.7                   # the full heart, chord ringing
BACK_S = 2.2                   # a glides back to 0 (loop)
XR = math.sqrt(3.3)            # domain |x| <= sqrt(3.3)
N_PTS = 4200                   # enough for ~37 waves at a = 20
TOP_C, MID_C, BOT_C = (1.00, 0.55, 0.70), (1.00, 0.27, 0.48), (0.72, 0.30, 0.95)
STEP = 0.5                     # one note per +0.5 of a


def a_grow(t):
    u = min(max(t / GROW_S, 0.0), 1.0)
    return A_MAX * (0.55 * u + 0.45 * u * u)       # speed climbs 2.6x over the clip


def simulate():
    nf = int(round((GROW_S + HOLD_S + BACK_S) * FPS))
    a = np.zeros(nf)
    for f in range(nf):
        t = f * DT
        if t <= GROW_S:
            a[f] = a_grow(t)
        elif t <= GROW_S + HOLD_S:
            a[f] = A_MAX
        else:
            a[f] = A_MAX * (1.0 - smooth((t - GROW_S - HOLD_S) / BACK_S))
    a[-1] = 0.0
    return {"a": a, "nf": nf}


def curve(a):
    x = np.linspace(-XR, XR, N_PTS)
    y = np.cbrt(x * x) + 0.9 * np.sin(a * math.pi * x) * np.sqrt(np.maximum(3.3 - x * x, 0.0))
    return x, y


def _bg(canvas, w, h):
    g = cairo.RadialGradient(w / 2, h * 0.46, 0, w / 2, h * 0.46, max(w, h) * 0.75)
    g.add_color_stop_rgb(0.0, 0.09, 0.03, 0.08)
    g.add_color_stop_rgb(1.0, 0.01, 0.00, 0.02)
    canvas.ctx.set_source(g)
    canvas.ctx.paint()


def _equation(canvas, cx, y, size, alpha):
    """y = x^(2/3) + 0.9 sin(aπx) √(3.3 − x²), with a real raised 2/3."""
    ctx = canvas.ctx
    segs = [("y = x", 1.0, 0.0), ("2/3", 0.55, -0.42), (" + 0.9 sin(", 1.0, 0.0),
            ("a", 1.0, 0.0), ("πx) √(3.3 − x²)", 1.0, 0.0)]
    widths = []
    for s, k, _ in segs:
        canvas._font(size * k, bold=False)
        widths.append(ctx.text_extents(s).x_advance)
    x = cx - sum(widths) / 2
    for (s, k, dy), wd in zip(segs, widths):
        canvas._font(size * k, bold=False)
        col = (1.0, 0.80, 0.45) if s == "a" else (0.97, 0.93, 0.96)
        ctx.set_source_rgba(0, 0, 0, 0.5 * alpha)
        ctx.move_to(x + 2, y + dy * size + 2)
        ctx.show_text(s)
        ctx.set_source_rgba(*col, alpha)
        ctx.move_to(x, y + dy * size)
        ctx.show_text(s)
        x += wd


def draw(canvas, layout, sim, f, rule):
    w, h = layout.w, layout.h
    vertical = h > w
    a = float(sim["a"][f])
    # 9:16 leaves the top band (to ~0.16h) free for the post-pass quote caption
    unit = (w * 0.76 / 4.0) if vertical else (h * 0.74 / 4.6)
    cx = w / 2
    cy0 = (h * 0.25 + 2.3 * unit) if vertical else h * 0.56   # screen y of graph y = 0.5

    def X(v):
        return cx + v * unit

    def Y(v):
        return cy0 - (v - 0.5) * unit

    _bg(canvas, w, h)
    # faint grid + axes
    grid = [(X(i * 0.5), Y(-1.8), X(i * 0.5), Y(2.8)) for i in range(-4, 5)]
    grid += [(X(-2.0), Y(j * 0.5), X(2.0), Y(j * 0.5)) for j in range(-3, 6)]
    canvas.lines(grid, (0.85, 0.75, 0.95), width=1.0, alpha=0.06)
    canvas.lines([(X(-2.05), Y(0), X(2.05), Y(0)), (X(0), Y(-1.85), X(0), Y(2.85))],
                 (0.85, 0.80, 0.95), width=2.0, alpha=0.30)

    xs, ys = curve(a)
    pts = list(zip((cx + xs * unit).tolist(), (cy0 - (ys - 0.5) * unit).tolist()))
    y0, y1 = Y(2.7), Y(-1.7)
    canvas.polylines_vgrad([pts], y0, y1, [TOP_C, MID_C, BOT_C], width=16, alpha=0.08)
    canvas.polylines_vgrad([pts], y0, y1, [TOP_C, MID_C, BOT_C], width=3.2, alpha=0.95)
    canvas.polylines([pts], (1, 1, 1), width=0.9, alpha=0.30)

    eq_y, a_y = (h * 0.196, h * 0.233) if vertical else (h * 0.075, h * 0.145)
    size = w * (0.042 if vertical else 0.026)
    _equation(canvas, cx, eq_y, size, 1.0)
    canvas.text_centered(f"a = {a:.2f}", a_y, size=size * 1.15, color=(1.0, 0.80, 0.45),
                         alpha=0.95, bold=True)
    if rule:
        canvas.caption(rule, alpha=1.0, layout=layout)
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
    a, k = sim["a"], 1
    out = [{"t": 0.02, "note": 50, "gain": 0.45, "x": layout.w / 2},     # soft opening pair
           {"t": 0.02, "note": 62, "gain": 0.40, "x": layout.w / 2}]
    for f in range(1, int(GROW_S * FPS) + 1):
        while a[f] >= k * STEP and k * STEP < A_MAX:
            t = f * DT
            x = layout.w * (0.5 + 0.30 * math.sin(k * 1.7))
            out.append({"t": round(t, 4), "note": walker.next(),
                        "gain": round(0.40 + 0.20 * a[f] / A_MAX, 3), "x": round(x, 1)})
            k += 1
    for j, note in enumerate((50, 57, 62, 66, 69)):          # D major chord at the full heart
        out.append({"t": round(GROW_S + 0.05 * j, 4), "note": note, "gain": 0.5, "x": layout.w / 2})
    return out


def pad(sim):
    """Quiet sustained sine pad on D, fades to silence before the loop seam."""
    sr = audio.SR
    dur = sim["nf"] / FPS
    t = np.arange(int(dur * sr)) / sr
    sig = np.zeros_like(t)
    for m, amp in ((50, 1.0), (57, 0.7), (62, 0.5), (66, 0.35)):
        f0 = audio.midi_to_hz(m)
        sig += amp * (np.sin(2 * np.pi * f0 * t) + 0.5 * np.sin(2 * np.pi * f0 * 1.003 * t))
    lfo = 0.85 + 0.15 * np.sin(2 * np.pi * 0.12 * t)
    env = np.clip(t / 0.5, 0, 1) * np.clip((dur - 0.6 - t) / 2.0, 0, 1) ** 2
    return (0.018 * sig * lfo * env).astype(np.float32)


def _worker(o, sim, label, rule):
    layout = get_layout(o)
    name = f"{SCENE}_{label}_{layout.tag}"
    video = studio.OUT_DIR / f"{name}_silent.mp4"
    d = render(layout, sim, video, rule)
    kit.deliver(SCENE, name, layout, video, build_events(sim, layout), d, True,
                voice="glassharp", bed=pad(sim))


def main():
    label, rule = arg("--label", "v1"), arg("--rule", "")
    studio.OUT_DIR.mkdir(exist_ok=True)
    sim = simulate()
    if kit.has("--still"):
        layout = get_layout(kit.orients()[0])
        f = int(arg("--frame", "900"))
        png = studio.OUT_DIR / f"{SCENE}_{label}_f{f}_{layout.tag}.png"
        render(layout, sim, png, rule, still_frame=f)
        print(f"[{SCENE}] -> {png}")
        return
    print(f"[{SCENE}] {sim['nf'] / FPS:.2f}s")
    kit.fan_out(_worker, (sim, label, rule), SCENE)


if __name__ == "__main__":
    main()
