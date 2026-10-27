"""STANDARD DEVIATION outro: every board from the mixed video drawn on ONE axis.

Each pile is rescaled to its own mean and spread (z = distance from the middle in
units of its spread), so a 100-ball pile and a 5000-ball pile can sit on the same
chart. They appear one by one in the story order; at the end the ideal bell curve is
drawn over all of them, and the piles that were wrong are visibly off it.

Audio: original synthesis only. One marimba note per pile as it appears, a resolved
chord when the ideal curve lands, and the same voice-like hum from the opening of
each board returning under it.

    python scenes/stddev_outro.py -- --order 1000,100,2000,500,5000
"""
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib import audio, kit, studio  # noqa: E402
from lib.kit import DT, FPS, arg, smooth  # noqa: E402
from lib.layouts import get_layout  # noqa: E402
from lib.studio import Canvas, VideoWriter  # noqa: E402
import scenes.stddev as sd  # noqa: E402

SCENE = "stddev_outro"
# n -> (seed, skew, skew_rows): the exact boards of the five clips
CFG = {100: (3, 0.0, 4), 500: (8, 0.0, 4), 1000: (2, 0.25, 7), 2000: (2, 0.12, 4), 5000: (2, 0.0, 4)}
T_TITLE = 0.9          # title + axis fade in
T_STEP = 1.7           # seconds per pile
T_GROW = 1.1           # a pile grows over this long
T_CURVE = 1.4          # the ideal curve draws in
T_HOLD = 2.4
T_OUT = 0.9
ZMAX = 4.0
YMAX = 0.46


def histogram(n):
    """z-space density bars of the pile of the n-ball board: [(z_lo, z_hi, density)]."""
    seed, skew, skew_rows = CFG[n]
    sim = sd.simulate(seed, n, sd.default_rows(n), 17.0, skew, skew_rows)
    xs, mu, sg = sd.running_stats(sim)
    m, sig, xmax = float(mu[-1]), float(sg[-1]), sim["cols"] / 2.0
    bars = []
    for k, c in enumerate(sim["counts"]):
        lo, hi = (k - xmax - m) / sig, (k + 1 - xmax - m) / sig
        bars.append((lo, hi, c / n * sig))              # probability mass / bin width in z
    return bars


def phi(z):
    return math.exp(-0.5 * z * z) / math.sqrt(2 * math.pi)


def timeline(k):
    t_first = T_TITLE
    t_curve = t_first + k * T_STEP + 0.4
    return t_first, t_curve, t_curve + T_CURVE + T_HOLD + T_OUT


def draw(canvas, layout, order, bars, f):
    t = f * DT
    t_first, t_curve, t_total = timeline(len(order))
    w, h = layout.w, layout.h
    cx0, cx1 = w * 0.16, w * 0.84
    cy0, cy1 = h * 0.80, h * 0.20                        # baseline, top
    Zx = lambda z: cx0 + (z + ZMAX) / (2 * ZMAX) * (cx1 - cx0)      # noqa: E731
    Dy = lambda d: cy0 + (cy1 - cy0) * min(d / YMAX, 1.05)           # noqa: E731
    out = 1.0 - smooth((t - (t_total - T_OUT)) / T_OUT)
    a_ui = smooth(t / T_TITLE) * out
    canvas.clear()

    canvas.text_centered("How close to the ideal bell curve?", h * 0.115, size=h * 0.05,
                         alpha=a_ui, cx=w / 2, max_w=w * 0.8)
    # axis + faint spread lines
    canvas.lines([(Zx(-ZMAX), cy0, Zx(ZMAX), cy0)], (0.62, 0.68, 0.80), width=2.5, alpha=0.5 * a_ui)
    for z in range(-3, 4):
        canvas.lines([(Zx(z), cy0, Zx(z), cy0 + h * 0.012)], (0.62, 0.68, 0.80), width=2.5, alpha=0.5 * a_ui)
        canvas.text_centered(str(z), cy0 + h * 0.055, size=h * 0.028, alpha=0.45 * a_ui, bold=False, cx=Zx(z))
    for z, a_l in ((-2, 0.18), (-1, 0.35), (1, 0.35), (2, 0.18)):
        canvas.lines([(Zx(z), cy0, Zx(z), Dy(YMAX))], sd.SIGMA_COL, width=2.0, alpha=a_l * a_ui)

    for i, n in enumerate(order):
        ti = t_first + i * T_STEP
        if t < ti:
            break
        p = smooth((t - ti) / T_GROW)
        d = smooth((t - (ti + T_STEP)) / 0.6) if i + 1 < len(order) else smooth((t - t_curve) / 0.8)
        col = kit.wheel(0.9 * i / max(len(order) - 1, 1))
        fill_a = (0.42 * (1 - 0.88 * d)) * out
        line_a = (0.95 - 0.45 * d) * out
        pts = []
        for lo, hi, dens in bars[n]:
            y = Dy(dens * p)
            canvas.rect(Zx(lo), y, Zx(hi), cy0, col, alpha=fill_a)
            pts += [(Zx(lo), y), (Zx(hi), y)]
        canvas.polylines([pts], col, width=3.5, alpha=line_a)
        # legend (left panel): appears with its pile
        ly = h * (0.30 + 0.085 * i)
        la = smooth((t - ti) / 0.5) * out
        canvas.circle(w * 0.045, ly - h * 0.012, h * 0.013, col, alpha=la)
        canvas.text_centered(f"{n} balls", ly, size=h * 0.034, color=col, alpha=la, cx=w * 0.115, max_w=w * 0.12)

    if t >= t_curve:
        pc = smooth((t - t_curve) / T_CURVE)
        zs = [-ZMAX + 2 * ZMAX * j / 240 for j in range(241)]
        zs = [z for z in zs if z <= -ZMAX + 2 * ZMAX * pc]
        if len(zs) > 1:
            pts = [(Zx(z), Dy(phi(z))) for z in zs]
            canvas.polylines([pts], (1, 1, 1), width=14.0, alpha=0.16 * out)
            canvas.polylines([pts], (1, 1, 1), width=5.0, alpha=0.95 * out)
    canvas.text_centered(studio.WATERMARK, h * 0.955, size=layout.wm_size, alpha=0.22 * out, bold=False,
                         cx=w / 2, max_w=w * 0.4)


def render(layout, order, out_path, still_frame=None):
    bars = {n: histogram(n) for n in order}
    canvas = Canvas(layout.w, layout.h, studio.render_scale())
    writer = None if still_frame is not None else VideoWriter(out_path, canvas, FPS)
    nf = int(round(timeline(len(order))[2] * FPS))
    for f in range(nf):
        if still_frame is not None and f != still_frame:
            continue
        draw(canvas, layout, order, bars, f)
        if writer is None:
            studio.save_still(canvas, out_path)
            return f / FPS
        writer.write_frame()
    writer.close()
    return nf / FPS


def build_events(order, layout):
    t_first, t_curve, t_total = timeline(len(order))
    penta = audio.PENTA_MAJOR
    out = []
    for i, n in enumerate(order):
        ti = t_first + i * T_STEP
        pan = layout.w * (0.30 + 0.10 * i)
        out.append({"t": round(ti + 0.12, 4), "note": kit.penta_note(i / 5.0, root=60, scale=penta, span=6),
                    "gain": 0.62, "x": pan})
        out.append({"t": round(ti + 0.42, 4), "note": kit.penta_note(i / 5.0, root=72, scale=penta, span=6),
                    "gain": 0.40, "x": pan})
    for j, (note, g) in enumerate(((48, 0.7), (60, 0.62), (67, 0.62), (76, 0.58))):
        out.append({"t": round(t_curve + 0.9 + 0.06 * j, 4), "note": note, "gain": g, "x": layout.w / 2})
    return sorted(out, key=lambda e: e["t"])


def make_bed(order):
    t_first, t_curve, t_total = timeline(len(order))
    start = t_curve + 0.5
    hum = sd.synth_hum(max(1.0, t_total - T_OUT - start - 0.3), gain=0.30)
    return np.concatenate([np.zeros(int(start * audio.SR), dtype=np.float32), hum])


def main():
    order = [int(x) for x in arg("--order", "1000,100,2000,500,5000").split(",")]
    label = arg("--label", "mix")
    studio.OUT_DIR.mkdir(exist_ok=True)
    layout = get_layout("horizontal")
    if kit.has("--still"):
        f = int(arg("--frame", "600"))
        png = studio.OUT_DIR / f"{SCENE}_{label}_f{f}_{layout.tag}.png"
        render(layout, order, png, still_frame=f)
        print(f"[{SCENE}] -> {png}")
        return
    name = f"{SCENE}_{label}_{layout.tag}"
    video = studio.OUT_DIR / f"{name}_silent.mp4"
    d = render(layout, order, video)
    kit.deliver(SCENE, name, layout, video, build_events(order, layout), d, True, bed=make_bed(order))


if __name__ == "__main__":
    main()
