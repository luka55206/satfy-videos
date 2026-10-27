"""SINE AND COSINE from one spinning ball (test version).

A ball spins around a circle. Its shadow on the horizontal axis (the cosine, pink) and on
the vertical axis (the sine, cyan) fly back and forth through the centre, closer and
further, joined to the ball by dashed lines. Their positions are drawn out as two waves
scrolling over time. Live parameters: the angle, cos, sin, the amplitude A and the
frequency f. Then the spin speeds up (f rises), the circle breathes (A changes), and the
cosine wave slides a quarter turn until it lies exactly on the sine wave.
Loop: the spin eases to a stop on the starting angle, the waves fade out.

Audio (original synthesis only): the channel's voice-like hum while the ball waits, cut
by the start of the spin; a pentatonic note every 45 degrees (so the tune speeds up with
the spin); a chord when the two waves coincide.

    ./run.ps1 -Scene trig -Fast
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
import scenes.regress as rg  # noqa: E402  (shared sphere / glass-card drawing + hum)

SCENE = "trig"
START_S = rg.START_S
T_SLIDE0, T_SLIDE1 = 14.0, 17.0     # the cosine slides onto the sine
T_FADE = 19.4                       # hold the merged waves, then ease out
T_END = T_FADE + 1.3
WIN_S = 3.2                         # seconds of history shown in the wave panel
COS_C, SIN_C, BALL_C = (1.0, 0.30, 0.65), (0.0, 0.90, 1.0), (1.0, 0.88, 0.45)


def freq(t):
    if t < START_S:
        return 0.0
    f = 0.30 + 0.55 * smooth((t - 6.0) / 8.0) + 0.15 * smooth((t - 14.0) / 3.0)
    return f * smooth((t - START_S) / 0.8)


def amp(t):
    return 1.0 - 0.45 * smooth((t - 8.0) / 2.0) + 0.45 * smooth((t - 10.0) / 2.0)


def simulate():
    nf = int(round(T_END * FPS))
    th = np.zeros(nf + 1)
    for k in range(1, nf + 1):
        th[k] = th[k - 1] + 2 * math.pi * freq(k * DT) * DT
    kf = int(T_FADE * FPS)
    target = 2 * math.pi * math.ceil(th[kf] / (2 * math.pi) + 0.25)
    for k in range(kf, nf + 1):
        w = smooth((k - kf) / (nf - kf))
        th[k] = th[kf] + (th[k] - th[kf]) * (1 - w) + (target - th[kf]) * w if k > kf else th[k]
    th[nf] = target
    return {"th": th, "nf": nf}


def theta_at(sim, t):
    x = min(max(t * FPS, 0.0), len(sim["th"]) - 1.001)
    i = int(x)
    return sim["th"][i] + (sim["th"][i + 1] - sim["th"][i]) * (x - i)


def _dashed(canvas, x0, y0, x1, y1, col, alpha, width):
    ctx = canvas.ctx
    ctx.set_source_rgba(*col, alpha)
    ctx.set_line_width(width)
    ctx.set_dash([14, 12])
    ctx.move_to(x0, y0)
    ctx.line_to(x1, y1)
    ctx.stroke()
    ctx.set_dash([])


def draw(canvas, layout, sim, f, rule):
    w, h = layout.w, layout.h
    t = f * DT
    ctx = canvas.ctx
    keep = 1.0 - smooth((t - T_FADE) / (T_END - T_FADE))
    th = theta_at(sim, t)
    A = amp(t)
    s_sl = smooth((t - T_SLIDE0) / (T_SLIDE1 - T_SLIDE0))
    cxm, cym, Rc = w / 2, h * 0.355, w * 0.30
    Ra = Rc * A
    canvas.clear()
    bg = cairo.RadialGradient(w / 2, h * 0.45, 0, w / 2, h * 0.45, h * 0.7)
    bg.add_color_stop_rgba(0.0, 0.05, 0.07, 0.15, 1.0)
    bg.add_color_stop_rgba(1.0, 0.0, 0.0, 0.0, 1.0)
    ctx.set_source(bg)
    ctx.paint()

    # axes + circle (a ghost of the full-size circle while the amplitude changes)
    ax = (0.62, 0.68, 0.80)
    canvas.lines([(cxm - Rc * 1.28, cym, cxm + Rc * 1.28, cym), (cxm, cym - Rc * 1.28, cxm, cym + Rc * 1.28)],
                 ax, width=3, alpha=0.40)
    canvas.ring(cxm, cym, Rc, ax, width=3, alpha=0.18)
    canvas.ring(cxm, cym, Ra, (1, 1, 1), width=14, alpha=0.06)
    canvas.ring(cxm, cym, Ra, (1, 1, 1), width=4, alpha=0.65)
    px, py = cxm + Ra * math.cos(th), cym - Ra * math.sin(th)
    cx_ball = (cxm + Ra * math.cos(th), cym)                    # cosine shadow on the horizontal axis
    sy_ball = (cxm, cym - Ra * math.sin(th))                    # sine shadow on the vertical axis

    # angle arc + radius
    ctx.new_path()
    ctx.arc_negative(cxm, cym, Rc * 0.18, 0, -(th % (2 * math.pi)))
    ctx.set_source_rgba(1, 1, 1, 0.55)
    ctx.set_line_width(5)
    ctx.stroke()
    canvas.lines([(cxm, cym, px, py)], BALL_C, width=14, alpha=0.18)
    canvas.lines([(cxm, cym, px, py)], BALL_C, width=5, alpha=0.9)

    # dashed perpendicular lines: the "opposite" sides of the right triangle
    _dashed(canvas, px, py, cx_ball[0], cx_ball[1], COS_C, 0.75, 4)
    _dashed(canvas, px, py, sy_ball[0], sy_ball[1], SIN_C, 0.75, 4)

    # flying shadows with ghost trails
    for k in range(1, 9):
        tt = t - k * 0.035
        thk = theta_at(sim, tt)
        Ak = amp(tt)
        a = 0.30 * (1 - k / 9.0)
        canvas.circle(cxm + Rc * Ak * math.cos(thk), cym, 20 * (1 - k * 0.06), COS_C, alpha=a)
        canvas.circle(cxm, cym - Rc * Ak * math.sin(thk), 20 * (1 - k * 0.06), SIN_C, alpha=a)
    rg._sphere(canvas, cx_ball[0], cx_ball[1], 24, COS_C, 1.0)
    rg._sphere(canvas, sy_ball[0], sy_ball[1], 24, SIN_C, 1.0)
    kb = 1.0 + 0.12 * (0.5 - 0.5 * math.cos(2 * math.pi * rg.PULSE_HZ * t)) if t < START_S else 1.0
    rg._sphere(canvas, px, py, 28 * kb, BALL_C, 1.0)

    # wave panel
    Px0, Px1, Py0, Py1 = w * 0.08, w * 0.92, h * 0.575, h * 0.715
    ycen, yamp = (Py0 + Py1) / 2, (Py1 - Py0) * 0.40
    rg._round_rect(ctx, Px0 - 20, Py0 - 12, Px1 + 20, Py1 + 12, 26)
    ctx.set_source_rgba(1, 1, 1, 0.035)
    ctx.fill_preserve()
    ctx.set_source_rgba(0.62, 0.72, 0.95, 0.20)
    ctx.set_line_width(3)
    ctx.stroke()
    xc_cur = w * 0.86
    pps = (xc_cur - Px0 - 20) / WIN_S
    canvas.lines([(Px0, ycen, Px1, ycen)], ax, width=2, alpha=0.30)
    canvas.lines([(Px0, ycen - yamp, Px1, ycen - yamp), (Px0, ycen + yamp, Px1, ycen + yamp)], ax, width=2, alpha=0.10)
    if t > START_S:
        n_pts = 220
        for col, fn in ((COS_C, lambda tt: math.cos(theta_at(sim, tt) - (math.pi / 2) * s_sl) * amp(tt)),
                        (SIN_C, lambda tt: math.sin(theta_at(sim, tt)) * amp(tt))):
            pts = []
            for i in range(n_pts + 1):
                tt = t - WIN_S * (1 - i / n_pts)
                if tt < START_S:
                    continue
                pts.append((xc_cur - (t - tt) * pps, ycen - yamp * fn(tt)))
            if len(pts) > 1:
                merged = s_sl >= 0.999
                wd = (11 if col == COS_C else 4) if merged else 6          # merged: pink rim around the cyan core
                canvas.polylines([pts], col, width=16 if merged else 10, alpha=0.10 * keep)
                canvas.polylines([pts], col, width=wd, alpha=0.95 * keep)
        yc = ycen - yamp * math.cos(th - (math.pi / 2) * s_sl) * A
        ys = ycen - yamp * math.sin(th) * A
        rg._sphere(canvas, xc_cur, yc, 16, COS_C, keep)
        rg._sphere(canvas, xc_cur, ys, 16, SIN_C, keep)
    canvas.lines([(xc_cur, Py0, xc_cur, Py1)], (1, 1, 1), width=2, alpha=0.18)
    if s_sl > 0.01:
        canvas.text_centered(f"cos slid {int(round(90 * s_sl))}°" if s_sl < 0.999 else "cos slid 90° = sin",
                             Py0 - h * 0.013, size=h * 0.021, color=COS_C, alpha=0.9 * keep,
                             cx=Px0 + w * 0.17, max_w=w * 0.3)

    # live parameters
    deg = int(round(math.degrees(th) % 360.0)) % 360
    f_now = freq(t)
    cv, sv = math.cos(th), math.sin(th)
    sgn = lambda v: f"{v:.2f}".replace("-", "−")        # noqa: E731
    canvas.text_centered(f"cos θ = {sgn(cv)}", h * 0.755, size=h * 0.033, color=COS_C, cx=w * 0.28, max_w=w * 0.44)
    canvas.text_centered(f"sin θ = {sgn(sv)}", h * 0.755, size=h * 0.033, color=SIN_C, cx=w * 0.72, max_w=w * 0.44)
    canvas.text_centered(f"θ = {deg}°", h * 0.800, size=h * 0.026, color=(1, 1, 1), alpha=0.85, cx=w * 0.17,
                         max_w=w * 0.3)
    canvas.text_centered(f"amplitude {A:.2f}", h * 0.800, size=h * 0.026, color=(0.8, 0.85, 0.95), alpha=0.85,
                         cx=w * 0.5, max_w=w * 0.34)
    canvas.text_centered(f"speed {f_now:.2f} Hz", h * 0.800, size=h * 0.026, color=(0.8, 0.85, 0.95), alpha=0.85,
                         cx=w * 0.83, max_w=w * 0.3)
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
    th = sim["th"]
    step = math.pi / 4
    walker = audio.ScaleWalker(root_midi=60, scale=audio.PENTA_MAJOR, span=10, pattern="updown")
    out, last, k_next = [], -1e9, 1
    for k in range(1, len(th)):
        if th[k] >= k_next * step and k * DT < T_FADE - 0.7:
            t = k * DT
            while th[k] >= k_next * step:
                k_next += 1
            if t - last < 0.05:
                continue
            last = t
            ang = th[k] % (2 * math.pi)
            out.append({"t": round(t, 4), "note": walker.next(), "gain": 0.62 if k_next % 2 == 0 else 0.5,
                        "x": round(layout.w * (0.5 + 0.30 * math.cos(ang)), 1)})
    for j, note in enumerate((48, 60, 67, 76)):
        out.append({"t": round(T_SLIDE1 + 0.07 * j, 4), "note": note, "gain": 0.7, "x": layout.w / 2})
    return sorted(out, key=lambda e: e["t"])


def main():
    label, rule = arg("--label", "v1"), arg("--rule", "")
    studio.OUT_DIR.mkdir(exist_ok=True)
    layout = get_layout("vertical")
    sim = simulate()
    if kit.has("--still"):
        f = int(arg("--frame", "600"))
        png = studio.OUT_DIR / f"{SCENE}_{label}_f{f}_{layout.tag}.png"
        render(layout, sim, png, rule, still_frame=f)
        print(f"[{SCENE}] -> {png}")
        return
    name = f"{SCENE}_{label}_{layout.tag}"
    video = studio.OUT_DIR / f"{name}_silent.mp4"
    d = render(layout, sim, video, rule)
    events = build_events(sim, layout)
    bed = rg.sd.synth_hum(START_S + 0.25)
    kit.deliver(SCENE, name, layout, video, events, d, True, bed=bed)


if __name__ == "__main__":
    main()
