"""LINEAR REGRESSION held by springs.

A dropper slides along a rail and releases balls one by one; each lands on a chart and
stays as a point. A glowing line starts in the wrong place, every point is tied to it
by a coil spring, and the line swings and settles where the total spring stretch is
smallest. That spot is exactly the least-squares fit (no formula on screen).
Loop: everything fades back to the empty chart and the dropper glides home.

Audio (original synthesis only): the channel's voice-like hum while the first ball
waits in the dropper, interrupted by its release; then one pentatonic note per landed
ball (pitch = x), a soft knock per release, a chord when the line locks.

    ./run.ps1 -Scene regress -Fast            # low-res test
    python scenes/regress.py -- --points 30   # NF_SCALE=2 = 4K
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
import scenes.stddev as sd  # noqa: E402  (the shared voice-like hum)

SCENE = "regress"
PULSE_HZ = 1.1
START_S = 2.0 / PULSE_HZ          # the first ball waits (and breathes) for two pulses
FALL_S = 0.5
SETTLE_S = 3.2
HOLD_S = 1.6
FADE_S = 1.1
R = 24.0                          # ball radius (logical px)
LINE_COL = (1.0, 1.0, 1.0)


def simulate(seed, n):
    rng = random.Random(seed)
    t, pts = START_S, []
    for i in range(n):
        x = rng.uniform(0.05, 0.95)
        y = min(0.96, max(0.04, 0.12 + 0.74 * x + rng.gauss(0.0, 0.085)))
        pts.append({"t": t, "x": x, "y": y, "hue": (i * 0.031) % 1.0})
        t += 0.50 * (0.24 / 0.50) ** (i / n)
    xs, ys = np.array([p["x"] for p in pts]), np.array([p["y"] for p in pts])
    m_ls, b_ls = np.polyfit(xs, ys, 1)
    t_line = pts[-1]["t"] + FALL_S + 0.5            # the wrong line fades in
    t_set = t_line + 0.6                            # ...then the springs let go
    m, b, vm, vb = -0.35, 0.78, 0.0, 0.0
    path, h = [], DT
    n_set = int(SETTLE_S * FPS)
    for k in range(n_set):
        r = ys - (m * xs + b)
        gm, gb = float((r * xs).mean()), float(r.mean())
        vm += (250.0 * gm - 12.0 * vm) * h
        vb += (250.0 * gb - 12.0 * vb) * h
        m, b = m + vm * h, b + vb * h
        w = smooth((k - n_set * 0.8) / (n_set * 0.2))     # exact lock-in over the last 20%
        path.append((m + (m_ls - m) * w, b + (b_ls - b) * w))
    t_end = t_set + SETTLE_S
    nf = int(round((t_end + HOLD_S + FADE_S) * FPS))
    return {"pts": pts, "path": path, "init": (-0.35, 0.78), "ls": (m_ls, b_ls), "t_line": t_line,
            "t_set": t_set, "t_end": t_end, "nf": nf, "n": n}


# --- drawing helpers ----------------------------------------------------------

def _sphere(canvas, x, y, r, col, alpha=1.0):
    """A shaded ball: soft glow, a lit gradient body and a small specular dot."""
    canvas.glow(x, y, r, col, strength=0.42 * alpha, reach=2.3)
    ctx = canvas.ctx
    g = cairo.RadialGradient(x - 0.32 * r, y - 0.36 * r, 0.05 * r, x, y, 1.15 * r)
    light = tuple(min(1.0, c * 0.35 + 0.65) for c in col)
    g.add_color_stop_rgba(0.0, *light, alpha)
    g.add_color_stop_rgba(0.45, *col, alpha)
    g.add_color_stop_rgba(1.0, *(c * 0.50 for c in col), alpha)
    ctx.set_source(g)
    ctx.new_sub_path()
    ctx.arc(x, y, r, 0, 2 * math.pi)
    ctx.fill()
    canvas.circle(x - 0.34 * r, y - 0.38 * r, 0.16 * r, (1, 1, 1), alpha=0.75 * alpha)


def _round_rect(ctx, x0, y0, x1, y1, r):
    ctx.new_path()
    ctx.arc(x1 - r, y0 + r, r, -math.pi / 2, 0)
    ctx.arc(x1 - r, y1 - r, r, 0, math.pi / 2)
    ctx.arc(x0 + r, y1 - r, r, math.pi / 2, math.pi)
    ctx.arc(x0 + r, y0 + r, r, math.pi, 1.5 * math.pi)
    ctx.close_path()


def _carriage_x(sim, t):
    """Dropper position (chart units 0..1): glides to each ball's x between releases,
    waits over the first x, and glides home to it in the fade-out (loop)."""
    pts = sim["pts"]
    if t < pts[0]["t"]:
        return pts[0]["x"]
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]
        if a["t"] <= t < b["t"]:
            gap = b["t"] - a["t"]
            return a["x"] + (b["x"] - a["x"]) * smooth((t - a["t"] - 0.10) / max(gap - 0.18, 0.05))
    last = pts[-1]
    t_home = sim["t_end"] + HOLD_S
    return last["x"] + (pts[0]["x"] - last["x"]) * smooth((t - t_home) / FADE_S)


def draw(canvas, layout, sim, f, rule):
    w, h = layout.w, layout.h
    X0, X1, Y0, Y1 = w * 0.12, w * 0.88, h * 0.30, h * 0.72
    Y_RAIL, Y_NZ = h * 0.222, h * 0.262
    PX = lambda x: X0 + x * (X1 - X0)      # noqa: E731
    PY = lambda y: Y1 - y * (Y1 - Y0)      # noqa: E731
    t = f * DT
    t_home = sim["t_end"] + HOLD_S
    keep = 1.0 - smooth((t - t_home) / FADE_S)
    ctx = canvas.ctx
    canvas.clear()
    bg = cairo.RadialGradient(w / 2, h * 0.52, 0, w / 2, h * 0.52, h * 0.72)
    bg.add_color_stop_rgba(0.0, 0.05, 0.07, 0.15, 1.0)
    bg.add_color_stop_rgba(1.0, 0.0, 0.0, 0.0, 1.0)
    ctx.set_source(bg)
    ctx.paint()

    # chart card, grid, axes
    _round_rect(ctx, X0 - 34, Y0 - 34, X1 + 34, Y1 + 34, 34)
    ctx.set_source_rgba(1, 1, 1, 0.035)
    ctx.fill_preserve()
    ctx.set_source_rgba(0.62, 0.72, 0.95, 0.20)
    ctx.set_line_width(3)
    ctx.stroke()
    canvas.lines([(X0, PY(g), X1, PY(g)) for g in (0.25, 0.5, 0.75)], (0.62, 0.68, 0.80), width=2, alpha=0.10)
    canvas.lines([(PX(g), Y0, PX(g), Y1) for g in (0.25, 0.5, 0.75)], (0.62, 0.68, 0.80), width=2, alpha=0.06)
    canvas.lines([(X0, Y0, X0, Y1), (X0, Y1, X1, Y1)], (0.62, 0.68, 0.80), width=4, alpha=0.55)

    # the line at this moment (and how fast it is moving)
    speed = 0.0
    if t < sim["t_set"]:
        m, b = sim["init"]
    else:
        k = min(int((t - sim["t_set"]) * FPS), len(sim["path"]) - 1)
        m, b = sim["path"][k]
        m0, b0 = sim["path"][max(k - 1, 0)]
        speed = min(1.0, (abs(m - m0) + abs(b - b0)) * 60 * 0.7)
    la = smooth((t - sim["t_line"]) / 0.5) * keep
    landed = [p for p in sim["pts"] if t >= p["t"] + FALL_S]

    stretch = 0.0
    if la > 0.0:
        for p in landed:
            ly = m * p["x"] + b
            r = p["y"] - ly
            stretch += abs(r)
            if abs(r) < 0.004:
                continue
            x, y0, y1 = PX(p["x"]), PY(p["y"]), PY(ly)
            turns, amp = 7, 20.0
            ring = 0.0
            if t > sim["t_end"]:
                ring = 8.0 * math.exp(-4.0 * (t - sim["t_end"])) * math.sin(38.0 * (t - sim["t_end"]) + p["x"] * 9.0)
            sway = 7.0 * speed * math.sin(18.0 * t + p["x"] * 9.0) + ring
            pts = [(x, y0)]
            for q in range(1, 2 * turns):
                fq = math.sin(math.pi * q / (2 * turns))          # the middle of the coil swings most
                pts.append((x + (amp if q % 2 else -amp) + sway * fq, y0 + (y1 - y0) * q / (2 * turns)))
            pts.append((x, y1))
            u = min(1.0, abs(r) / 0.25)
            col = (0.0 + 1.0 * u, 0.9 - 0.6 * u, 1.0 - 0.45 * u)
            canvas.polylines([pts], (0, 0, 0), width=11.0, alpha=0.45 * la)      # dark under-stroke
            canvas.polylines([pts], col, width=7.0, alpha=0.95 * la)
            canvas.polylines([pts], (1, 1, 1), width=2.0, alpha=0.30 * la)       # metallic glint
            canvas.circle(x, y1, 9, LINE_COL, alpha=0.9 * la)
        xa, xb = PX(0.0), PX(1.0)
        seg = [(xa, PY(b)), (xb, PY(m + b))]
        pulse = max(0.0, 1.0 - abs(t - sim["t_end"]) / 0.45) if sim["t_end"] - 0.45 < t else 0.0
        canvas.polylines([seg], LINE_COL, width=44.0 + 40.0 * pulse, alpha=(0.05 + 0.12 * pulse) * la)
        canvas.polylines([seg], LINE_COL, width=18.0 + 34.0 * pulse, alpha=(0.12 + 0.28 * pulse) * la)
        canvas.polylines([seg], LINE_COL, width=6.0, alpha=0.97 * la)
        canvas.circle(xa, PY(b), 7, LINE_COL, alpha=0.95 * la)
        canvas.circle(xb, PY(m + b), 7, LINE_COL, alpha=0.95 * la)

    # balls: falling from the dropper (ghost trail), a hop and ripple on landing, a swell wave at lock-in
    nz_x = PX(_carriage_x(sim, t))
    for p in sim["pts"]:
        age = t - p["t"]
        if age < 0:
            continue
        u = min(1.0, age / FALL_S)
        tx, ty = PX(p["x"]), PY(p["y"])
        x, y = tx, Y_NZ + (ty - Y_NZ) * u * u
        col = kit.wheel(p["hue"])
        a = keep if u >= 1.0 else 1.0
        if u < 1.0:
            for g in (1, 2, 3):
                ug = max(0.0, u - 0.05 * g)
                canvas.circle(tx, Y_NZ + (ty - Y_NZ) * ug * ug, R * (1 - 0.12 * g), col, alpha=0.20 / g)
        else:
            tl = age - FALL_S
            if tl < 0.4:
                y -= 26.0 * abs(math.sin(math.pi * tl / 0.4)) * (1.0 - tl / 0.4)
            if tl < 0.3:
                canvas.ring(tx, ty, R + 62 * tl / 0.3, col, width=4.0, alpha=0.55 * (1 - tl / 0.3) * keep)
        wave = 1.0 + 0.30 * max(0.0, 1.0 - abs(t - sim["t_end"] - 0.5 * p["x"] + 0.15) / 0.22)
        _sphere(canvas, x, y, R * wave, col, a)

    # the dropper: rail, carriage, nozzle, and the next ball waiting inside it
    canvas.lines([(X0 - 34, Y_RAIL, X1 + 34, Y_RAIL)], (0.62, 0.68, 0.80), width=5, alpha=0.55)
    cxp = nz_x
    _round_rect(ctx, cxp - 62, Y_RAIL - 28, cxp + 62, Y_RAIL + 28, 14)
    ctx.set_source_rgba(0.18, 0.22, 0.32, 0.98)
    ctx.fill_preserve()
    ctx.set_source_rgba(0.75, 0.82, 0.95, 0.85)
    ctx.set_line_width(3)
    ctx.stroke()
    canvas.lines([(cxp, Y_RAIL + 28, cxp, Y_NZ + R * 0.4)], (0.75, 0.82, 0.95), width=22, alpha=0.9)
    canvas.rect(cxp - 8, Y_RAIL - 8, cxp + 8, Y_RAIL + 8, (1.0, 0.85, 0.30), alpha=0.95)
    nxt = next((p for p in sim["pts"] if p["t"] > t), None)
    if keep < 1.0 or nxt is not None:
        wait = nxt if nxt is not None else sim["pts"][0]
        a_w = 1.0 if nxt is not None else smooth((1.0 - keep) * 2.0)
        k = 1.0 + 0.12 * (0.5 - 0.5 * math.cos(2 * math.pi * PULSE_HZ * t)) if t < START_S else 1.0
        _sphere(canvas, cxp, Y_NZ + R * 0.9, R * k, kit.wheel(wait["hue"]), a_w)
    for p in sim["pts"]:                                    # a flash at the nozzle on release
        age = t - p["t"]
        if 0 <= age < 0.18:
            canvas.ring(PX(p["x"]), Y_NZ, R * (1.0 + 2.2 * age / 0.18), kit.wheel(p["hue"]), width=4.0,
                        alpha=0.7 * (1 - age / 0.18))

    if rule:
        canvas.caption(rule, alpha=min(1.0, t / 0.4) * keep, layout=layout)
    msg = (f"Spring stretch: {int(round(stretch * 100))}" if la > 0.03
           else f"Points: {int(round(len(landed) * (keep if keep < 0.03 else 1.0)))}")
    canvas.counter(msg, alpha=1.0, layout=layout, size_f=0.04)
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
    out = []
    for p in sim["pts"]:
        out.append({"t": round(p["t"], 4), "note": 48, "note_gain": 0.0, "pok": 0.5, "pok_gain": 0.45,
                    "gain": 0.5, "x": round(layout.w * (0.12 + 0.76 * p["x"]), 1)})
        out.append({"t": round(p["t"] + FALL_S, 4),
                    "note": kit.penta_note(p["x"], root=57, scale=audio.PENTA_MAJOR, span=12),
                    "gain": 0.55, "x": round(layout.w * (0.12 + 0.76 * p["x"]), 1)})
    for j, note in enumerate((48, 60, 67, 76)):
        out.append({"t": round(sim["t_end"] - 0.35 + 0.07 * j, 4), "note": note, "gain": 0.7, "x": layout.w / 2})
    return sorted(out, key=lambda e: e["t"])


def main():
    seed, n = int(arg("--seed", 7)), int(arg("--points", 30))
    label, rule = arg("--label", f"n{n}s{seed}"), arg("--rule", "")
    studio.OUT_DIR.mkdir(exist_ok=True)
    layout = get_layout("vertical")
    sim = simulate(seed, n)
    if kit.has("--still"):
        f = int(arg("--frame", str(sim["nf"] // 2)))
        png = studio.OUT_DIR / f"{SCENE}_{label}_f{f}_{layout.tag}.png"
        render(layout, sim, png, rule, still_frame=f)
        print(f"[{SCENE}] -> {png}")
        return
    name = f"{SCENE}_{label}_{layout.tag}"
    video = studio.OUT_DIR / f"{name}_silent.mp4"
    d = render(layout, sim, video, rule)
    events = build_events(sim, layout)
    bed = sd.synth_hum(sim["pts"][0]["t"] + 0.25)          # the hum is cut by the first release
    kit.deliver(SCENE, name, layout, video, events, d, True, bed=bed)


if __name__ == "__main__":
    main()
