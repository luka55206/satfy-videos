"""STANDARD DEVIATION scene: exactly 100 balls fall through the peg board and the
pile teaches what a standard deviation is.

Same real 2D physics as scenes/pegdrop.py (reused, not copied). The change a
viewer can NAME: "100 balls, and a band that shows the standard deviation".

NAMING (legal): see docs/compliance.md. No trademarked game name anywhere, no
money / prizes / multipliers / "win" wording, no casino styling.

The rule:        100 balls, one drop point, the board is real physics.
The teaching:    mean line + a +-1 sigma band that tracks the balls already landed,
                 a live sigma readout, and at the end how many balls fell inside it.
The escalation:  the drop interval eases 0.5 s -> 0.1 s; "Balls left" counts 100 -> 0.
The loop:        the piles drain back, "Balls left" counts 0 -> 100, the last frame
                 is the first frame (empty board, one ball breathing at the top).

Audio (100% original synthesis, no samples, no melody bank):
  * 0 - 2.2 s  a continuous warm vocal-style hum (formant-filtered additive synth,
               NOT a recorded or AI voice) swelling in time with the waiting ball.
  * the first peg hit INTERRUPTS the hum; from then on every hit is the next note
    of a pentatonic run, so the falling balls play a tune that speeds up.

    ./run.ps1 -Scene stddev -Fast -Still -Frame 900
    ./run.ps1 -Scene stddev -Fast
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
import scenes.galton as gl  # noqa: E402

SCENE = "stddev"
PULSE_HZ = 1.1
START_S = 2.0 / PULSE_HZ          # two full pulses: the waiting ball is back to size 1
HOLD_S = 1.6
DRAIN_S = 1.2
I0, I1 = 0.28, 0.06
SIGMA_COL = (0.0, 0.90, 1.0)
BIN_H_BIG = 4.6                   # same, for runs above BIG balls
BIN_H = 3.4                       # bin height below the last peg row
PITCH = 0.38                      # ball spacing inside the pusher tube
MAG = 4                           # balls visible in the tube
TUBE_H = 2.2                      # tube height above the release point
PUSH_S = 0.10                     # the stack steps down this fast after each release
FALL_S = gl.T_FALL                # a landed ball settles onto its pile over this long
ROWS_FOR = {100: 10, 500: 14, 1000: 16, 2000: 18, 5000: 20}   # more rows = a finer bell
BIG = 150                         # above this many balls: stripes piles, schedule by --drop-s


def default_rows(n):
    if n in ROWS_FOR:
        return ROWS_FOR[n]
    return int(min(20, max(10, round(10 + 7.7 * math.log10(max(n, 100) / 100.0)))))


def gaps(n, drop_s):
    """Seconds between releases. 100 balls: the original 0.28 -> 0.06 s ease. Bigger runs:
    ease from 0.2 s down to a floor over the first 40% of the balls, then hold it; the
    floor is solved so the whole drop lasts `drop_s` seconds."""
    if n <= BIG:
        return [I0 * (I1 / I0) ** (i / n) for i in range(n)]
    ramp = max(1, min(int(0.4 * n), 250))

    def sched(i1):
        return [0.2 * (i1 / 0.2) ** min(1.0, i / ramp) for i in range(n)]
    lo, hi = 1e-7, 0.2
    for _ in range(80):
        mid = math.sqrt(lo * hi)
        if sum(sched(mid)) > drop_s:
            hi = mid
        else:
            lo = mid
    return sched(lo)


# --- pass 1: simulate ---------------------------------------------------------

def simulate(seed, n, rows, drop_s=17.0, skew=0.0, skew_rows=4, kx=1.0):
    """n balls, each deciding left/right at every peg (a Galton board: the counts are
    binomial, i.e. a REAL bell curve with honest sampling noise). Fixed timetable."""
    rng = random.Random(seed)
    nbin = rows + 1
    bin_h = BIN_H if n <= BIG else BIN_H_BIG          # taller cups: a bigger bell
    path_t = gl.T_FIRST + rows * gl.HOP
    balls, t = [], START_S
    gp = gaps(n, drop_s)
    for i in range(n):
        dirs = [1 if rng.random() < 0.5 else 0 for _ in range(rows)]
        if skew > 0.0 and rng.random() < skew:
            dirs[-skew_rows:] = [1] * skew_rows                  # this ball is shoved right at the bottom
        balls.append({"t0": t, "dirs": dirs, "k": sum(dirs), "bin": sum(dirs), "y_land": 0.0,
                      "hue": (i * 0.031) % 1.0, "t_land": t + path_t})
        t += gp[i]
    counts = [0] * nbin
    for b in balls:                                  # equal path times: landing order == drop order
        b["rank"] = counts[b["bin"]]
        counts[b["bin"]] += 1
    y_div = (rows - 1) * gl.DY + 0.2
    floor_y = rows * gl.DY + bin_h
    row_h = min(2 * gl.RB * 0.92, (bin_h - 0.8) / max(1, math.ceil(max(counts) / 2.0)))
    stripes = n > BIG or kx > 1.0                     # big runs / stretched board: balls hex-packed in the cup
    unit = 0.0
    br = gl.RB if not stripes else gl.RB * (100.0 / n) ** 0.25
    pr, hb, kc = gl.RB, 0.0, 2
    if stripes:
        avail_h = bin_h - 0.55
        pr = min(gl.RB, math.sqrt(0.80 * avail_h * kx / (3.4 * max(counts))))
        while True:
            kc = max(2, int(0.84 * kx // (2 * pr * 1.02)))
            hb = pr * math.sqrt(3.0) / (kc - 0.5)        # pile height added per ball
            if max(counts) * hb + pr <= avail_h or pr < 0.01:
                break
            pr *= 0.97
    for b in balls:
        b["xc"], b["yc"] = b["bin"] - rows / 2.0, rows * gl.DY - gl.OFF
        if stripes:
            cyc, rem = divmod(b["rank"], 2 * kc - 1)
            row, col, m = (2 * cyc, rem, kc) if rem < kc else (2 * cyc + 1, rem - kc, kc - 1)
            b["sx"] = b["xc"] + (col - (m - 1) / 2.0) * 2 * pr * 1.02 / kx    # kx: bin units are stretched
            b["sy"] = floor_y - 0.05 - pr - row * pr * math.sqrt(3.0)
        else:
            b["sx"] = b["xc"] + ((b["rank"] % 2) - 0.5) * 2 * gl.RB * 1.02
            b["sy"] = floor_y - gl.RB - (b["rank"] // 2) * row_h

    nf = int(round((balls[-1]["t_land"] + FALL_S) * FPS)) + 1
    pegs = [(c - r / 2.0, r * gl.DY) for r in range(rows) for c in range(r + 1)]
    frames, landed_f, lo, hi = [], [], 0, 0
    t_lands = np.array([b["t_land"] for b in balls])
    for f in range(nf):
        t = f * DT
        while hi < n and balls[hi]["t0"] <= t:
            hi += 1
        while lo < hi and balls[lo]["t_land"] <= t:
            lo += 1
        frames.append([(*gl._pos(balls[i], t - balls[i]["t0"], rows)[:2], balls[i]["hue"])
                       for i in range(lo, hi)])
        landed_f.append(int(np.searchsorted(t_lands, t, side="right")))
    flash = np.zeros((nf, len(pegs)), dtype=np.float32)
    decay = np.exp(-np.arange(16) / (0.10 * FPS)).astype(np.float32)
    hits = []
    for b in balls:
        c = 0
        for r in range(rows):
            th = b["t0"] + gl.T_FIRST + r * gl.HOP
            hits.append((round(th, 5), "peg", r * (r + 1) // 2 + c, c - r / 2.0, 0.6))
            fh = int(round(th * FPS))
            if fh < nf:
                seg = flash[fh:fh + 16, r * (r + 1) // 2 + c]
                flash[fh:fh + len(seg), r * (r + 1) // 2 + c] = np.maximum(seg, decay[:len(seg)])
            c += b["dirs"][r]
    hits.sort()
    return {"frames": frames, "flash": flash, "landed_f": landed_f, "balls": balls, "hits": hits,
            "counts": counts, "rows": rows, "cols": nbin, "nf": nf, "pegs": pegs,
            "y_div": y_div, "floor_y": floor_y, "row_h": row_h, "total": n,
            "stripes": stripes, "unit": unit, "br": br, "pr": pr, "hb": hb, "t_lands": t_lands, "mag": 4 if n <= BIG else 6,
            "kx": kx}


# --- statistics of the balls landed so far ------------------------------------

def running_stats(sim):
    xmax = sim["cols"] / 2.0
    xs = np.array([b["bin"] - xmax + 0.5 for b in sim["balls"]], dtype=np.float64)
    n = np.arange(1, len(xs) + 1)
    mu = np.cumsum(xs) / n
    var = np.maximum(np.cumsum(xs * xs) / n - mu * mu, 0.0)
    return xs, mu, np.sqrt(var)


# --- pass 2: render -----------------------------------------------------------

HW_FILL = 0.60                    # 16:9: share of the frame width the (stretched) board fills


def auto_kx(layout, n, rows):
    """Horizontal stretch of the board so a 16:9 frame is not mostly empty (1.0 for 9:16)."""
    if layout.tag == "9x16":
        return 1.0
    bin_h = BIN_H if n <= BIG else BIN_H_BIG
    h_u = gl.DROP_H + TUBE_H + rows * gl.DY + bin_h + 0.3
    s_h = layout.h * 0.86 / h_u
    return max(1.0, min(2.0, HW_FILL * layout.w / ((rows + 1 + 1.4) * s_h)))


def _geometry(layout, sim):
    kx = sim["kx"]
    h_u = gl.DROP_H + TUBE_H + sim["floor_y"] + 0.3
    w_u = sim["cols"] + 1.4
    top_u = gl.DROP_H + TUBE_H
    if layout.tag == "9x16":
        x0, x1, y0, y1 = layout.w * 0.03, layout.w * 0.97, layout.h * 0.20, layout.h * 0.735
    else:
        x0, x1 = layout.w * (0.5 - HW_FILL / 2), layout.w * (0.5 + HW_FILL / 2)
        y0, y1 = layout.h * 0.07, layout.h * 0.93
    s = min((x1 - x0) / (w_u * kx), (y1 - y0) / h_u)
    return (x0 + x1) / 2, y0 + (y1 - y0 - h_u * s) / 2 + top_u * s, s


def _pulse(t):
    return 0.5 - 0.5 * math.cos(2 * math.pi * PULSE_HZ * t)


def _cup(canvas, x0, y0, x1, y1, s, color, lit):
    """An open glass cup: round bottom, a gradient that pools colour at the base,
    a lit rim in the bin's colour and a soft glow when a ball has just landed."""
    ctx = canvas.ctx
    r = (x1 - x0) * 0.30

    def path():
        ctx.new_path()
        ctx.move_to(x0, y0)
        ctx.line_to(x0, y1 - r)
        ctx.arc_negative(x0 + r, y1 - r, r, math.pi, math.pi * 0.5)
        ctx.line_to(x1 - r, y1)
        ctx.arc_negative(x1 - r, y1 - r, r, math.pi * 0.5, 0.0)
        ctx.line_to(x1, y0)

    light = tuple(min(1.0, c * 0.45 + 0.55) for c in color)
    path()
    ctx.line_to(x0, y0)
    g = cairo.LinearGradient(0, y0, 0, y1)
    g.add_color_stop_rgba(0.0, *color, 0.03)
    g.add_color_stop_rgba(1.0, *color, 0.34 + 0.40 * lit)
    ctx.set_source(g)
    ctx.fill()
    if lit > 0.02:
        path()
        ctx.set_source_rgba(*light, 0.45 * lit)
        ctx.set_line_width(max(2.0, s * 0.16))
        ctx.stroke()
    path()
    ctx.set_source_rgba(*light, 0.80)
    ctx.set_line_width(max(2.0, s * 0.05))
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.stroke()
    ctx.set_line_cap(cairo.LINE_CAP_BUTT)
    ctx.set_source_rgba(1, 1, 1, 0.22)                 # glass sheen on the left wall
    ctx.set_line_width(max(1.5, s * 0.03))
    ctx.move_to(x0 + (x1 - x0) * 0.16, y0 + (y1 - y0) * 0.12)
    ctx.line_to(x0 + (x1 - x0) * 0.16, y1 - (y1 - y0) * 0.30)
    ctx.stroke()


def _pusher(canvas, X, Y, s, t0s, t, N, live, e, br=gl.RB, mag=MAG):
    """Tube above the drop point: MAG waiting balls and a piston on top of them."""
    rw = br + 0.07
    pitch = PITCH * br / gl.RB
    y_rel = -gl.DROP_H                              # release point (centre of the lowest ball)
    y_top = y_rel - (mag - 1) * pitch - br - 0.55
    d = int(np.searchsorted(t0s, t, side="right")) - 1 if live else -1
    if d < 0:
        p = 1.0
    else:
        gap = (t0s[d + 1] - t0s[d]) if d + 1 < len(t0s) else 9.0
        p = smooth((t - t0s[d]) / min(PUSH_S, gap * 0.9))
    fade = 1.0 if live else smooth(e * 2.0)
    wall = (0.62, 0.68, 0.80)
    w = max(2.0, s * 0.04)
    canvas.lines([(X(-rw), Y(y_top), X(-rw), Y(y_rel + br + 0.08)),
                  (X(rw), Y(y_top), X(rw), Y(y_rel + br + 0.08)),
                  (X(-rw), Y(y_rel + br + 0.08), X(-0.62), Y(y_rel + br + 0.30)),
                  (X(rw), Y(y_rel + br + 0.08), X(0.62), Y(y_rel + br + 0.30))],
                 wall, width=w, alpha=0.75)
    canvas.rect(X(-rw - 0.12), Y(y_top - 0.26), X(rw + 0.12), Y(y_top), (0.35, 0.40, 0.52), alpha=0.95)
    ys = []
    for j in range(mag):
        i = d + 1 + j
        if i >= N:
            break
        y = y_rel - j * pitch - (pitch * (1.0 - p) if d >= 0 else 0.0)
        ys.append(y)
        k = 1.0 + 0.12 * _pulse(t) if (j == 0 and live and t < START_S) else 1.0
        col = kit.wheel((i * 0.031) % 1.0)
        a = fade if not live else 1.0
        if k > 1.0:
            canvas.circle(X(0), Y(y), br * s * 2.4 * k, col, alpha=0.14 + 0.10 * _pulse(t))
        canvas.circle(X(0), Y(y), br * s * k, col, alpha=a)
    y_pis = (ys[-1] if ys else y_rel) - br - 0.14
    y_pis = max(y_pis, y_top + 0.3)
    canvas.lines([(X(0), Y(y_top), X(0), Y(y_pis))], (0.8, 0.85, 0.95), width=w * 1.6, alpha=0.9)
    canvas.rect(X(-br - 0.04), Y(y_pis - 0.07), X(br + 0.04), Y(y_pis + 0.07), (1.0, 0.85, 0.30), alpha=0.95)


def _packed_piles(canvas, X, Y, s, sim, t, f, L, live, keep, br):
    """Big runs: every settled ball is drawn ONCE onto a cached layer (thousands of
    circles per frame would be minutes of render); only balls still sinking are drawn live."""
    ca_ = sim.setdefault("_cache", {})
    if ca_.get("surf") is None or f < ca_.get("last_f", -1) or ca_.get("size") != (canvas.pw, canvas.ph):
        surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, canvas.pw, canvas.ph)
        c2 = cairo.Context(surf)
        c2.scale(canvas.pw / canvas.w, canvas.ph / canvas.h)
        ca_.update(surf=surf, ctx=c2, drawn=0, size=(canvas.pw, canvas.ph))
    ca_["last_f"] = f
    balls, pr = sim["balls"], sim["pr"]
    n_set = int(np.searchsorted(sim["t_lands"], t - FALL_S, side="right")) if live else sim["total"]
    c2 = ca_["ctx"]
    shine = pr * s > 1.8
    for b in balls[ca_["drawn"]:n_set]:
        c2.set_source_rgba(*kit.wheel(b["hue"]), 0.95)
        c2.new_sub_path()
        c2.arc(X(b["sx"]), Y(b["sy"]), max(pr * s, 0.1), 0, 2 * math.pi)
        c2.fill()
        if shine:
            c2.set_source_rgba(1, 1, 1, 0.38)
            c2.new_sub_path()
            c2.arc(X(b["sx"]) - pr * 0.3 * s, Y(b["sy"] - pr * 0.3), pr * s * 0.28, 0, 2 * math.pi)
            c2.fill()
    ca_["drawn"] = max(ca_["drawn"], n_set)
    ca_["surf"].flush()
    ctx = canvas.ctx
    ctx.save()
    ctx.identity_matrix()
    ctx.set_source_surface(ca_["surf"], 0, 0)
    ctx.paint_with_alpha(keep)
    ctx.restore()
    for b in balls[n_set:L]:                          # still sinking into the pile
        u = smooth((t - b["t_land"]) / FALL_S)
        x = b["xc"] + (b["sx"] - b["xc"]) * u
        y = b["yc"] + (b["sy"] - b["yc"]) * u * u
        rr = br + (pr - br) * u
        canvas.circle(X(x), Y(y), rr * s, kit.wheel(b["hue"]), alpha=0.95 * keep)


def draw(canvas, layout, sim, st, f, e, rule, geo):
    cols, N = sim["cols"], sim["total"]
    xs, mus, sgs, _t0 = st
    cx, oy, s = geo
    kx = sim["kx"]
    X = lambda u: cx + u * s * kx     # noqa: E731
    Xs = lambda u: cx + u * s         # noqa: E731  (the pusher is not stretched)
    Y = lambda u: oy + u * s     # noqa: E731
    fi = min(f, sim["nf"] - 1)
    t = f * DT
    keep = 1.0 - e
    xmax, y_div, floor_y = cols / 2.0, sim["y_div"], sim["floor_y"]
    live = f < sim["nf"]
    L = sim["landed_f"][fi] if live else N
    canvas.clear()
    br = sim["br"]

    t_end = sim["nf"] * DT
    ca = smooth((t - t_end - 0.1) / 0.6) * keep
    mu_f, sg_f = float(mus[-1]), float(sgs[-1])

    # coloured containers: a tinted bin per column that lights up when a ball lands in it
    lit = [0.0] * cols
    i_lit = int(np.searchsorted(sim["t_lands"], t - 0.45, side="right"))
    for b in sim["balls"][i_lit:L]:
        if live:
            lit[b["bin"]] = max(lit[b["bin"]], max(0.0, 1.0 - (t - b["t_land"]) / 0.45))
    for k in range(cols):
        _cup(canvas, X(k - xmax + 0.07), Y(y_div), X(k - xmax + 0.93), Y(floor_y + 0.10), s,
             kit.wheel(0.9 * k / max(cols - 1, 1)), lit[k])

    # piles
    if sim["stripes"]:
        _packed_piles(canvas, X, Y, s, sim, t, f, L, live, keep, br)
    else:
        for b in sim["balls"][:L]:
            u = smooth((t - b["t_land"]) / FALL_S) if live else 1.0
            x = b["xc"] + (b["sx"] - b["xc"]) * u
            y = b["yc"] + (b["sy"] - b["yc"]) * u * u
            canvas.circle(X(x), Y(y), gl.RB * s, kit.wheel(b["hue"]), alpha=0.95 * keep)
            canvas.circle(X(x - gl.RB * 0.3), Y(y - gl.RB * 0.3), gl.RB * s * 0.28, (1, 1, 1), alpha=0.38 * keep)

    # pegs: a slow shimmer while the hum plays, a flash on every hit
    fl = sim["flash"][fi]
    shim_amp = smooth(t / 0.5) * (1.0 - smooth((t - START_S) / 0.25)) if t < START_S + 0.3 else 0.0
    for idx, (px, py) in enumerate(sim["pegs"]):
        v = float(fl[idx])
        w = shim_amp * 0.30 * (0.5 + 0.5 * math.sin(2 * math.pi * (PULSE_HZ * t - 0.09 * (px + 0.6 * py))))
        v = max(v, w)
        col = (0.55 + 0.45 * v, 0.62 + 0.38 * v, 0.76 + 0.24 * v)
        if v > 0.05:
            canvas.circle(X(px), Y(py), gl.RP * s * 2.6, (1, 1, 1), alpha=0.22 * v)
        canvas.circle(X(px), Y(py), gl.RP * s, col, alpha=0.55 + 0.45 * v)

    # the ball pusher: a tube holding the next balls, a piston that steps them down
    _pusher(canvas, Xs, Y, s, st[3], t, N, live, e, br, sim["mag"])

    if live:
        for x, y, hue in sim["frames"][fi]:
            col = kit.wheel(hue)
            canvas.circle(X(x), Y(y), br * s * 1.7, col, alpha=0.16)
            canvas.circle(X(x), Y(y), br * s, col, alpha=1.0)
            canvas.circle(X(x - br * 0.3), Y(y - br * 0.3), br * s * 0.28, (1, 1, 1), alpha=0.4)

    # the bell curve with the textbook spread: 68% of the area within 1 sigma, 95% within 2
    if ca > 0.0 and sg_f > 0.0:
        def cy(xu):
            pdf = math.exp(-((xu - mu_f) ** 2) / (2 * sg_f * sg_f)) / (sg_f * math.sqrt(2 * math.pi))
            if sim["stripes"]:
                y = floor_y - 0.05 - sim["pr"] - pdf * N * sim["hb"]
            else:
                y = floor_y - pdf * N * 0.5 * sim["row_h"] - gl.RB * 0.5
            return max(y_div - 0.2, y)

        base = floor_y - 0.03

        def xs_between(a, b, n=40):
            a, b = max(a, -xmax), min(b, xmax)
            return [a + (b - a) * i / n for i in range(n + 1)]
        for k2, a_f in ((2, 0.14), (1, 0.34)):
            xr = xs_between(mu_f - k2 * sg_f, mu_f + k2 * sg_f)
            poly = [(X(xr[0]), Y(base))] + [(X(x_), Y(cy(x_))) for x_ in xr] + [(X(xr[-1]), Y(base))]
            canvas.poly(poly, SIGMA_COL, alpha=a_f * ca)
        for k2, a_e in ((2, 0.45), (1, 0.95)):
            for sign in (-1, 1):
                xe = mu_f + sign * k2 * sg_f
                if -xmax < xe < xmax:
                    canvas.lines([(X(xe), Y(-0.6), X(xe), Y(base))], SIGMA_COL,
                                 width=max(2.0, s * 0.04), alpha=0.6 * a_e * ca)
                    canvas.lines([(X(xe), Y(cy(xe)), X(xe), Y(base))], SIGMA_COL,
                                 width=max(2.0, s * 0.05), alpha=a_e * ca)
        pts = [(X(x_), Y(cy(x_))) for x_ in xs_between(-xmax, xmax, 160)]
        canvas.polylines([pts], (1, 1, 1), width=max(8.0, s * 0.20), alpha=0.16 * ca)
        canvas.polylines([pts], (1, 1, 1), width=max(3.0, s * 0.07), alpha=0.95 * ca)
        for sign in (-1, 1):                              # the curve's inflection points
            xe = mu_f + sign * sg_f
            if -xmax < xe < xmax:
                canvas.circle(X(xe), Y(cy(xe)), max(4.0, s * 0.11), (1, 1, 1), alpha=0.95 * ca)

    cap_a = min(1.0, t / 0.4) * keep
    if rule:
        canvas.caption(rule, alpha=cap_a, layout=layout)

    if live:
        dropped = int(np.searchsorted(st[3], t, side="right"))
        left = N - dropped
    else:
        left = int(round(N * e))
    canvas.counter(f"Balls left: {left}", layout=layout, size_f=0.04)
    canvas.text_centered(studio.WATERMARK, layout.cnt_y + layout.h * 0.045, size=layout.wm_size,
                         alpha=0.22, bold=False, cx=layout.cnt_x, max_w=layout.cnt_maxw)


def render(layout, sim, out_path, rule, still_frame=None):
    canvas = Canvas(layout.w, layout.h, studio.render_scale())
    writer = None if still_frame is not None else VideoWriter(out_path, canvas, FPS)
    geo = _geometry(layout, sim)
    xs, mu, sg = running_stats(sim)
    t0 = np.array(sorted(b["t0"] for b in sim["balls"]))
    st = (xs, mu, sg, t0)
    nf, hold, drain = sim["nf"], int(HOLD_S * FPS), int(DRAIN_S * FPS)
    for f in range(nf + hold + drain):
        if still_frame is not None and f != still_frame:
            continue
        e = smooth((f - nf - hold + 1) / drain) if f >= nf + hold else 0.0
        draw(canvas, layout, sim, st, f, e, rule, geo)
        if writer is None:
            studio.save_still(canvas, out_path)
            return f / FPS
        writer.write_frame()
    writer.close()
    return (nf + hold + drain) / FPS


# --- pass 3: soundtrack -------------------------------------------------------

def build_events(sim, layout, dur):
    """Every sounded peg hit is the NEXT note of a pentatonic run (a tune, not a
    random scatter); the sounded gap shrinks 0.16 s -> 0.045 s so the tune speeds up.
    A landing is a low chime on its bin."""
    cols = sim["cols"]
    cx, _oy, s = _geometry(layout, sim)
    xmax = cols / 2.0
    t_end = sim["nf"] * DT
    walker = audio.ScaleWalker(root_midi=60, scale=audio.PENTA_MAJOR, span=10, pattern="updown")
    out, last, last_peg = [], -1e9, {}
    for t, kind, idx, px, imp in sim["hits"]:
        if kind != "peg" or imp < 0.12:
            continue
        gap = 0.16 - 0.115 * kit.smooth((t - START_S) / max(t_end - START_S, 1e-6))
        if t - last < gap or t - last_peg.get(idx, -1e9) < 0.07:
            continue
        last, last_peg[idx] = t, idx
        gain = min(0.85, 0.30 + 0.40 * imp + 0.15 * min(1.0, t / max(t_end, 1e-6)))
        out.append({"t": t, "note": walker.next(), "gain": round(gain, 3),
                    "x": round(cx + px * s * sim["kx"], 1)})
    big = sim["total"] > BIG
    last_land, last_bin = -1e9, {}
    for b in sim["balls"]:
        tl = b["t_land"] + FALL_S
        if big and (tl - last_land < 0.035 or tl - last_bin.get(b["bin"], -1e9) < 0.09):
            continue                                  # a chime per ball would be a buzz
        last_land, last_bin[b["bin"]] = tl, tl
        note = kit.penta_note((b["bin"] + 0.5) / cols, root=48, scale=audio.PENTA_MAJOR, span=cols)
        out.append({"t": round(tl, 5), "note": note, "gain": 0.8,
                    "x": round(cx + (b["bin"] - xmax + 0.5) * s * sim["kx"], 1)})
    t_first = min(e["t"] for e in out)
    last_k = -1e9
    for b in sim["balls"]:                 # the pusher's soft knock on every release
        if big and b["t0"] - last_k < 0.09:
            continue
        last_k = b["t0"]
        out.append({"t": round(b["t0"], 5), "note": 48, "note_gain": 0.0, "pok": 0.55, "pok_gain": 0.5,
                    "gain": 0.5, "x": round(cx, 1)})
    out.sort(key=lambda e: e["t"])
    return out


def synth_hum(t_cut, sr=audio.SR, gain=0.34):
    """Continuous vocal-style hum, mono, 0 .. t_cut seconds, then a 60 ms cut-off.

    Original DSP: a detuned 3-voice chord (C3 G3 C4 E4) of harmonic stacks, shaped
    by two formant bumps that morph 'oo' -> 'ah' with the same 0.9 Hz swell that
    drives the waiting ball. Vibrato eases in. No recording, no model."""
    n = int((t_cut + 0.5) * sr)
    t = np.arange(n) / sr
    swell = 0.5 - 0.5 * np.cos(2 * np.pi * PULSE_HZ * t)
    vib = 0.0035 * np.sin(2 * np.pi * 5.1 * t) * np.minimum(1.0, t / 1.0)
    f1 = 330.0 + 480.0 * swell                     # oo -> ah
    f2 = 870.0 + 330.0 * swell
    out = np.zeros(n)
    for midi in (48, 55, 60, 64):
        f0 = audio.midi_to_hz(midi)
        for cents in (-7.0, 0.0, 7.0):
            fr = f0 * 2 ** (cents / 1200.0)
            ph = 2 * np.pi * np.cumsum(fr * (1.0 + vib)) / sr
            for h in range(1, 15):
                fh = fr * h
                if fh > 5000:
                    break
                amp = (1.0 / h) * (0.15 + np.exp(-((fh - f1) / 260.0) ** 2)
                                   + 0.6 * np.exp(-((fh - f2) / 330.0) ** 2))
                out += amp * np.sin(h * ph)
    env = (0.55 + 0.45 * swell) * np.minimum(1.0, t / 0.08)
    cut = np.clip(1.0 - (t - t_cut) / 0.06, 0.0, 1.0)
    out = out * env * cut
    out = out / (np.max(np.abs(out)) or 1.0) * gain
    return out.astype(np.float32)


# --- orchestration ------------------------------------------------------------

def _worker(o, sim, dur, label, rule, sound):
    layout = get_layout(o)
    name = f"{SCENE}_{label}_{layout.tag}"
    video = studio.OUT_DIR / f"{name}_silent.mp4"
    d = render(layout, sim, video, rule)
    events = build_events(sim, layout, dur)
    bed = synth_hum(min(e["t"] for e in events if e.get("note_gain", 1.0) > 0)) if events else None
    kit.deliver(SCENE, name, layout, video, events, d, sound, bed=bed)


def main():
    seed = int(arg("--seed", 3))
    n = int(arg("--balls", 100))
    rows = int(arg("--rows", default_rows(n)))
    drop_s = float(arg("--drop-s", 17.0))
    skew = float(arg("--skew", 0.0))
    skew_rows = int(arg("--skew-rows", 4))
    label = arg("--label", f"n{n}s{seed}")
    rule = arg("--rule", "")                  # captions are a POST-RENDER pass
    sound = arg("--sound", "1") != "0"
    studio.OUT_DIR.mkdir(exist_ok=True)

    if len(kit.orients()) > 1:
        sys.exit(f"[{SCENE}] render one orientation at a time (the board stretch differs)")
    kx = auto_kx(get_layout(kit.orients()[0]), n, rows)
    sim = simulate(seed, n, rows, drop_s, skew, skew_rows, kx)
    xs, mu, sg = running_stats(sim)
    print(f"[{SCENE}] seed={seed} balls={sim['total']} counts={sim['counts']} "
          f"mean={mu[-1]:.2f} sigma={sg[-1]:.2f} "
          f"inside1s={int(np.sum(np.abs(xs - mu[-1]) <= sg[-1] + 1e-9))} "
          f"main={sim['nf'] * DT:.1f}s")
    if kit.has("--still"):
        layout = get_layout(kit.orients()[0])
        f = int(arg("--frame", str(sim["nf"] - 1)))
        png = studio.OUT_DIR / f"{SCENE}_{label}_f{f}_{layout.tag}.png"
        render(layout, sim, png, rule, still_frame=f)
        print(f"[{SCENE}] -> {png}")
        return
    kit.fan_out(_worker, (sim, 60.0, label, rule, sound), SCENE)


if __name__ == "__main__":
    main()


