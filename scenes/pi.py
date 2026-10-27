"""BALLS MEASURE PI (test version).

A dropper sweeps back and forth over a square and drops balls; each lands somewhere in
the square. Balls that land inside the quarter circle turn gold, the rest turn blue.
Four times the share of gold balls is an estimate of pi, shown live. As the balls pile
up the gold ones fill a quarter circle and the estimate settles near 3.14.
Loop: everything fades back to the empty square and the dropper glides home.

Audio (original synthesis only): the channel's voice-like hum while the first ball waits
in the dropper, cut by its release; a bright note per gold landing, a low one per blue
landing, a soft knock per release, a chord at the end.

    ./run.ps1 -Scene pi -Fast
"""
import math
import random
import sys
from pathlib import Path

import cairo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib import audio, kit, studio  # noqa: E402
from lib.kit import DT, FPS, arg, smooth  # noqa: E402
from lib.layouts import get_layout  # noqa: E402
from lib.studio import Canvas, VideoWriter  # noqa: E402
import scenes.regress as rg  # noqa: E402  (shared ball/glass-card drawing + hum)

SCENE = "pi"
START_S, FALL_S, HOLD_S, FADE_S = rg.START_S, 0.5, 1.8, 1.1
R = 13.0
HUE_IN, HUE_OUT = 0.06, 0.60


def _tri(p):
    p = p % 1.0
    return 2 * p if p < 0.5 else 2 - 2 * p


def simulate(seed, n):
    rng = random.Random(seed)
    t, phase, pts, last = START_S, 0.0, [], START_S
    for i in range(n):
        gap = 0.25 * (0.02 / 0.25) ** (i / n)
        amp = smooth((t - START_S) / 0.6)
        phase += (0.40 + 1.5 * (i / n)) * (t - last) if i else 0.0
        last = t
        x = 0.5 + (0.04 + 0.92 * _tri(phase) - 0.5) * amp
        y = rng.random()
        inside = x * x + y * y <= 1.0
        hue = HUE_IN + 0.14 * rng.random() if inside else HUE_OUT + 0.12 * rng.random()
        pts.append({"t": t, "x": x, "y": y, "in": inside, "hue": hue})
        t += gap
    t_last = pts[-1]["t"] + FALL_S
    return {"pts": pts, "n": n, "t_last": t_last, "nf": int(round((t_last + HOLD_S + FADE_S) * FPS))}


def carriage_x(sim, t):
    pts = sim["pts"]
    if t < pts[0]["t"]:
        return 0.5
    if t < sim["t_last"] - FALL_S + 0.02:
        j = max(i for i, p in enumerate(pts) if p["t"] <= t)
        a, b = pts[j], pts[min(j + 1, len(pts) - 1)]
        return a["x"] + (b["x"] - a["x"]) * (0.0 if b["t"] <= a["t"] else (t - a["t"]) / (b["t"] - a["t"]))
    home = sim["t_last"] + HOLD_S
    return pts[-1]["x"] + (0.5 - pts[-1]["x"]) * smooth((t - home) / FADE_S)


def draw(canvas, layout, sim, f, rule):
    w, h = layout.w, layout.h
    S = w * 0.76
    X0, Y0 = w * 0.12, h * 0.268
    X1, Y1 = X0 + S, Y0 + S
    PX = lambda x: X0 + x * S             # noqa: E731
    PY = lambda y: Y1 - y * S             # noqa: E731
    Y_RAIL, Y_NZ = h * 0.222, h * 0.262
    t = f * DT
    home = sim["t_last"] + HOLD_S
    keep = 1.0 - smooth((t - home) / FADE_S)
    ctx = canvas.ctx
    canvas.clear()
    bg = cairo.RadialGradient(w / 2, h * 0.52, 0, w / 2, h * 0.52, h * 0.72)
    bg.add_color_stop_rgba(0.0, 0.05, 0.07, 0.15, 1.0)
    bg.add_color_stop_rgba(1.0, 0.0, 0.0, 0.0, 1.0)
    ctx.set_source(bg)
    ctx.paint()
    rg._round_rect(ctx, X0 - 34, Y0 - 34, X1 + 34, Y1 + 34, 34)
    ctx.set_source_rgba(1, 1, 1, 0.035)
    ctx.fill_preserve()
    ctx.set_source_rgba(0.62, 0.72, 0.95, 0.20)
    ctx.set_line_width(3)
    ctx.stroke()

    # the quarter circle (centre = bottom-left corner)
    glow = max(0.0, 1.0 - abs(t - sim["t_last"] - 0.4) / 0.5)
    ctx.new_path()
    ctx.move_to(X0, Y1)
    ctx.arc(X0, Y1, S, -math.pi / 2, 0)
    ctx.close_path()
    ctx.set_source_rgba(1.0, 0.8, 0.25, 0.05)
    ctx.fill()
    ctx.new_path()
    ctx.arc(X0, Y1, S, -math.pi / 2, 0)
    ctx.set_source_rgba(1.0, 0.85, 0.35, 0.18 + 0.4 * glow)
    ctx.set_line_width(14 + 20 * glow)
    ctx.stroke()
    ctx.new_path()
    ctx.arc(X0, Y1, S, -math.pi / 2, 0)
    ctx.set_source_rgba(1.0, 0.92, 0.55, 0.85)
    ctx.set_line_width(4)
    ctx.stroke()
    canvas.lines([(X0, Y0, X0, Y1), (X0, Y1, X1, Y1)], (0.62, 0.68, 0.80), width=4, alpha=0.5)

    # balls
    n_in = n_all = 0
    for p in sim["pts"]:
        age = t - p["t"]
        if age < 0:
            continue
        u = min(1.0, age / FALL_S)
        tx, ty = PX(p["x"]), PY(p["y"])
        y = Y_NZ + (ty - Y_NZ) * u * u
        if u < 1.0:
            for g in (1, 2):
                ug = max(0.0, u - 0.05 * g)
                canvas.circle(tx, Y_NZ + (ty - Y_NZ) * ug * ug, R * (1 - 0.15 * g), (0.8, 0.88, 1.0), alpha=0.18 / g)
            rg._sphere(canvas, tx, y, R, (0.82, 0.9, 1.0), 1.0)
            continue
        tl = age - FALL_S
        n_all += 1
        n_in += 1 if p["in"] else 0
        col = kit.wheel(p["hue"])
        if tl < 0.3:
            y -= 14.0 * abs(math.sin(math.pi * tl / 0.3)) * (1.0 - tl / 0.3)
            canvas.ring(tx, ty, R + 40 * tl / 0.3, col, width=3.0, alpha=0.6 * (1 - tl / 0.3) * keep)
        rg._sphere(canvas, tx, y, R, col, keep)

    # the dropper
    cx = PX(carriage_x(sim, t))
    canvas.lines([(X0 - 34, Y_RAIL, X1 + 34, Y_RAIL)], (0.62, 0.68, 0.80), width=5, alpha=0.55)
    rg._round_rect(ctx, cx - 62, Y_RAIL - 28, cx + 62, Y_RAIL + 28, 14)
    ctx.set_source_rgba(0.18, 0.22, 0.32, 0.98)
    ctx.fill_preserve()
    ctx.set_source_rgba(0.75, 0.82, 0.95, 0.85)
    ctx.set_line_width(3)
    ctx.stroke()
    canvas.lines([(cx, Y_RAIL + 28, cx, Y_NZ + R * 0.4)], (0.75, 0.82, 0.95), width=22, alpha=0.9)
    canvas.rect(cx - 8, Y_RAIL - 8, cx + 8, Y_RAIL + 8, (1.0, 0.85, 0.30), alpha=0.95)
    waiting = t < sim["t_last"] - FALL_S - 0.01 or keep < 1.0
    if waiting:
        a_w = 1.0 if t < home else smooth((1.0 - keep) * 2.0)
        k = 1.0 + 0.12 * (0.5 - 0.5 * math.cos(2 * math.pi * rg.PULSE_HZ * t)) if t < START_S else 1.0
        rg._sphere(canvas, cx, Y_NZ + R * 0.9, R * 1.5 * k, (0.82, 0.9, 1.0), a_w)

    if rule:
        canvas.caption(rule, alpha=min(1.0, t / 0.4) * keep, layout=layout)
    est = 4.0 * n_in / n_all if n_all else 0.0
    if keep < 0.03:                      # the faded-out end state == frame 0
        n_in = n_all = 0
    done = t > sim["t_last"] + 0.2
    pulse = 1.0 + 0.10 * max(0.0, 1.0 - abs(t - sim["t_last"] - 0.4) / 0.4)
    canvas.text_centered(f"Inside the circle: {n_in} / {n_all}", h * 0.742, size=h * 0.023,
                         color=(1.0, 0.85, 0.35), alpha=0.9 * (1.0 if n_all else 0.0) * keep,
                         cx=layout.cnt_x, max_w=layout.cnt_maxw)
    canvas.counter(f"π ≈ {est:.2f}" if n_all else "π ≈ ?", layout=layout, size_f=0.05 * pulse)
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
    out, last_k = [], -1e9
    for p in sim["pts"]:
        x_px = round(layout.w * (0.12 + 0.76 * p["x"]), 1)
        if p["t"] - last_k >= 0.08:
            last_k = p["t"]
            out.append({"t": round(p["t"], 4), "note": 48, "note_gain": 0.0, "pok": 0.5, "pok_gain": 0.4,
                        "gain": 0.5, "x": x_px})
    last_n = -1e9
    for p in sim["pts"]:
        tl = p["t"] + FALL_S
        if tl - last_n < 0.045:
            continue
        last_n = tl
        root, g = (60, 0.6) if p["in"] else (48, 0.4)
        out.append({"t": round(tl, 4), "note": kit.penta_note(p["x"], root=root, scale=audio.PENTA_MAJOR, span=10),
                    "gain": g, "x": round(layout.w * (0.12 + 0.76 * p["x"]), 1)})
    for j, note in enumerate((48, 60, 67, 76)):
        out.append({"t": round(sim["t_last"] + 0.1 + 0.07 * j, 4), "note": note, "gain": 0.7, "x": layout.w / 2})
    return sorted(out, key=lambda e: e["t"])


def main():
    seed, n = int(arg("--seed", 1)), int(arg("--balls", 200))
    label, rule = arg("--label", f"n{n}s{seed}"), arg("--rule", "")
    studio.OUT_DIR.mkdir(exist_ok=True)
    layout = get_layout("vertical")
    sim = simulate(seed, n)
    n_in = sum(1 for p in sim["pts"] if p["in"])
    print(f"[{SCENE}] seed={seed} balls={n} inside={n_in} pi~{4.0 * n_in / n:.4f} main={sim['t_last']:.1f}s "
          f"total={sim['nf'] * DT:.1f}s")
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
    bed = rg.sd.synth_hum(sim["pts"][0]["t"] + 0.25)
    kit.deliver(SCENE, name, layout, video, events, d, True, bed=bed)


if __name__ == "__main__":
    main()
