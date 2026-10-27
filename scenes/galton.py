"""GALTON BOARD scene: balls fall through a peg triangle into bins and the pile
grows into a bell curve.

NAMING (legal): never put "Plinko" in a title, description, tag, file name or
on screen. PLINKO is a registered trademark of FremantleMedia (The Price Is
Right). The mechanic itself is a Galton board / bean machine (1870s, public
domain science). Also: no money, prizes, multipliers or casino styling.

The ONE visible rule:   every ball goes left or right at random at every peg.
The escalation:         the drop rate climbs from ~2 balls/s to ~20 balls/s.
The payoff:             the pile traces the theoretical normal curve (fades in).
The loop:               the pile drains to nothing -> frame 0 is an empty board.

Audio: 100% synthesized (marimba voice). Pitch = landing bin on a pentatonic
scale (low bins left, high bins right), so you hear the bell curve. NO
melodies and NO samples, so there is nothing for Content ID to match.

    ./run.ps1 -Scene galton -Fast -Still -Frame 600
    ./run.ps1 -Scene galton -Fast
    ./run.ps1 -Scene galton -Orient both -SceneArgs @('--seed','3','--rows','12')

Variant knobs (YouTube needs each upload to differ in a way a viewer can name):
    --rows N     peg rows (bins = N+1)       --bias P  P(right) per peg, 0..1
    --dur S      main phase seconds          --rule "caption text"
"""
import math
import random
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib import audio, kit, studio  # noqa: E402
from lib.kit import DT, FPS, arg, smooth  # noqa: E402
from lib.layouts import get_layout  # noqa: E402
from lib.studio import Canvas, VideoWriter  # noqa: E402

SCENE = "galton"

# board geometry, in "units" (1 unit = horizontal peg spacing)
DY = 0.80          # row spacing
RB = 0.17          # ball radius
RP = 0.08          # peg radius
OFF = RB + RP      # ball centre sits this far above the peg it hits
DROP_H = 1.9       # drop zone above the first peg
BIN_H = 5.6        # bin height
HOP = 0.17         # seconds per peg-to-peg hop
T_FIRST = 0.30     # first drop onto the top peg
T_FALL = 0.35      # last hop -> pile
GROW_S = 0.12      # pile growth smoothing after a landing
HOLD_S = 1.0       # curve fully shown
DRAIN_S = 1.4      # pile drains back to the empty frame 0
START_S = 0.4      # first ball drops here (frame 0 stays empty)


# --- pass 1: simulate ---------------------------------------------------------

def simulate(seed, dur, rows, bias, i0=0.45, i1=0.05):
    rng = random.Random(seed)
    path_t = T_FIRST + rows * HOP + T_FALL
    spawn_end = dur - path_t - 1.0
    nbin = rows + 1

    balls, t = [], START_S
    while t < spawn_end:
        dirs = [1 if rng.random() < bias else 0 for _ in range(rows)]
        balls.append({"t": t, "dirs": dirs, "k": sum(dirs)})
        t += i0 * (i1 / i0) ** ((t - START_S) / max(spawn_end - START_S, 1e-6))

    counts = [0] * nbin
    for b in balls:                      # landing order == drop order
        b["n_before"] = counts[b["k"]]
        counts[b["k"]] += 1
        b["t_land"] = b["t"] + path_t
    unit = BIN_H * 0.85 / max(counts)
    floor_y = rows * DY + BIN_H
    for b in balls:
        b["y_land"] = floor_y - b["n_before"] * unit - RB * 0.5

    nf = int(round(dur * FPS))
    tt = np.arange(nf) * DT

    # per-frame falling balls
    frames, lo, hi = [], 0, 0
    for f in range(nf):
        t = f * DT
        while hi < len(balls) and balls[hi]["t"] <= t:
            hi += 1
        while lo < hi and balls[lo]["t_land"] <= t:
            lo += 1
        frames.append([_pos(balls[i], t - balls[i]["t"], rows) for i in range(lo, hi)])

    # peg flashes
    npeg = rows * (rows + 1) // 2
    flash = np.zeros((nf, npeg), dtype=np.float32)
    decay = np.exp(-np.arange(16) / (0.10 * FPS)).astype(np.float32)
    for b in balls:
        c = 0
        for r in range(rows):
            fh = int(round((b["t"] + T_FIRST + r * HOP) * FPS))
            if fh >= nf:
                break
            idx = r * (r + 1) // 2 + c
            seg = flash[fh:fh + 16, idx]
            flash[fh:fh + len(seg), idx] = np.maximum(seg, decay[:len(seg)])
            c += b["dirs"][r]

    # pile heights + landed counter
    tl = np.array([b["t_land"] for b in balls])
    heights = np.zeros((nf, nbin), dtype=np.float32)
    for k in range(nbin):
        tk = np.array([b["t_land"] for b in balls if b["k"] == k])
        if len(tk):
            x = np.clip((tt[:, None] - tk[None, :]) / GROW_S, 0.0, 1.0)
            heights[:, k] = unit * (x * x * (3.0 - 2.0 * x)).sum(1)
    landed = np.searchsorted(np.sort(tl), tt, side="right")

    events = [{"t": round(b["t_land"], 5), "k": b["k"], "n": i}
              for i, b in enumerate(balls) if b["t_land"] < dur]
    return {"frames": frames, "flash": flash, "heights": heights, "landed": landed,
            "events": events, "counts": counts, "unit": unit, "total": len(balls),
            "rows": rows, "bias": bias, "nf": nf}


def _pos(b, tau, rows):
    """Ball centre (x, y, bin) in board units, tau seconds after its drop."""
    d, k = b["dirs"], b["k"]
    if tau < T_FIRST:
        u = tau / T_FIRST
        return (0.0, -DROP_H + (DROP_H - OFF) * u * u, k)
    s = (tau - T_FIRST) / HOP
    if s < rows:
        r = int(s)
        u = s - r
        xr = sum(d[:r]) - r / 2.0
        x = xr + (d[r] - 0.5) * u
        y = r * DY - OFF + DY * (0.3 * u + 0.7 * u * u) - 0.10 * math.sin(math.pi * u)
        return (x, y, k)
    u = min(1.0, (tau - T_FIRST - rows * HOP) / T_FALL)
    y0 = rows * DY - OFF
    return (k - rows / 2.0, y0 + (b["y_land"] - y0) * u * u, k)


# --- pass 2: render -----------------------------------------------------------

def _geometry(layout, rows):
    """Board rectangle per orientation -> (cx, y_origin, px_per_unit)."""
    h_u = DROP_H + rows * DY + BIN_H
    w_u = rows + 1.6
    if layout.tag == "9x16":
        x0, x1, y0, y1 = layout.w * 0.04, layout.w * 0.96, layout.h * 0.185, layout.h * 0.745
    else:
        x0, x1, y0, y1 = layout.w / 2 - layout.h * 0.4, layout.w / 2 + layout.h * 0.4, layout.h * 0.07, layout.h * 0.93
    s = min((x1 - x0) / w_u, (y1 - y0) / h_u)
    return (x0 + x1) / 2, y0 + (y1 - y0 - h_u * s) / 2 + DROP_H * s, s


def draw(canvas, layout, sim, f, e, rule, geo):
    rows, nbin = sim["rows"], sim["rows"] + 1
    cx, oy, s = geo
    X = lambda u: cx + u * s     # noqa: E731
    Y = lambda u: oy + u * s     # noqa: E731
    fi = min(f, sim["nf"] - 1)
    t = f * DT
    t_main = sim["nf"] * DT
    keep = 1.0 - e                                   # 1 -> 0 while draining
    floor_y = rows * DY + BIN_H
    canvas.clear()

    # pile (bars), tinted by bin
    for k in range(nbin):
        h = float(sim["heights"][fi, k]) * keep
        if h <= 0.0:
            continue
        xc = k - rows / 2.0
        canvas.rect(X(xc - 0.45), Y(floor_y - h), X(xc + 0.45), Y(floor_y),
                    kit.wheel(0.9 * k / nbin), alpha=0.92)

    # dividers + floor
    y_div = (rows - 1) * DY + 0.2
    segs = [(X(k - rows / 2.0 - 0.5), Y(y_div), X(k - rows / 2.0 - 0.5), Y(floor_y))
            for k in range(nbin + 1)]
    segs.append((X(-rows / 2.0 - 0.5), Y(floor_y), X(rows / 2.0 + 0.5), Y(floor_y)))
    canvas.lines(segs, (0.62, 0.68, 0.80), width=max(2.0, s * 0.04), alpha=0.35)

    # pegs
    fl = sim["flash"][fi]
    for r in range(rows):
        for c in range(r + 1):
            v = float(fl[r * (r + 1) // 2 + c])
            px, py = X(c - r / 2.0), Y(r * DY)
            col = (0.55 + 0.45 * v, 0.62 + 0.38 * v, 0.76 + 0.24 * v)
            if v > 0.05:
                canvas.circle(px, py, RP * s * 2.4, (1, 1, 1), alpha=0.22 * v)
            canvas.circle(px, py, RP * s, col, alpha=0.55 + 0.45 * v)

    # balls (empty while draining, because everything has landed by then)
    if f < sim["nf"]:
        for x, y, k in sim["frames"][fi]:
            col = kit.wheel(0.9 * k / nbin)
            canvas.circle(X(x), Y(y), RB * s * 1.7, col, alpha=0.16)
            canvas.circle(X(x), Y(y), RB * s, col, alpha=1.0)

    # theoretical normal curve fades in at the end
    ca = smooth((t - (t_main - 1.0)) / 1.0) * keep
    if ca > 0.0:
        p, N = sim["bias"], sim["total"]
        mu, sg = rows * p - rows / 2.0, max(math.sqrt(rows * p * (1 - p)), 1e-6)
        top = floor_y - BIN_H
        pts = []
        for i in range(81):
            xu = -rows / 2.0 - 0.5 + (rows + 1) * i / 80
            pdf = math.exp(-((xu - mu) ** 2) / (2 * sg * sg)) / (sg * math.sqrt(2 * math.pi))
            pts.append((X(xu), Y(max(top, floor_y - N * pdf * sim["unit"]))))
        canvas.polylines([pts], (1, 1, 1), width=max(3.0, s * 0.07), alpha=0.9 * ca)

    cap_a = min(1.0, t / 0.4) * keep                  # 0 at frame 0 AND at the seam
    if rule:
        canvas.caption(rule, alpha=cap_a, layout=layout)
    n = int(round(sim["landed"][fi] * keep)) if f < sim["nf"] else int(round(sim["total"] * keep))
    canvas.counter(f"Balls: {n:,}", layout=layout, size_f=0.032)
    canvas.text_centered(studio.WATERMARK, layout.cnt_y + layout.h * 0.04, size=layout.wm_size,
                         alpha=0.22, bold=False, cx=layout.cnt_x, max_w=layout.cnt_maxw)


def render(layout, sim, out_path, rule, still_frame=None):
    canvas = Canvas(layout.w, layout.h, studio.render_scale())
    writer = None if still_frame is not None else VideoWriter(out_path, canvas, FPS)
    geo = _geometry(layout, sim["rows"])
    nf, hold, drain = sim["nf"], int(HOLD_S * FPS), int(DRAIN_S * FPS)
    for f in range(nf + hold + drain):
        if still_frame is not None and f != still_frame:
            continue
        e = smooth((f - nf - hold + 1) / drain) if f >= nf + hold else 0.0
        draw(canvas, layout, sim, f, e, rule, geo)
        if writer is None:
            studio.save_still(canvas, out_path)
            return f / FPS
        writer.write_frame()
    writer.close()
    return (nf + hold + drain) / FPS


# --- pass 3: soundtrack -------------------------------------------------------

def build_events(sim, layout, dur):
    rows, nbin, p = sim["rows"], sim["rows"] + 1, sim["bias"]
    geo = _geometry(layout, rows)
    pmf = [math.comb(rows, k) * p ** k * (1 - p) ** (rows - k) for k in range(nbin)]
    pmax = max(pmf)
    out = []
    for ev in sim["events"]:
        k = ev["k"]
        note = kit.penta_note(k / rows, root=52, scale=audio.PENTA_MAJOR, span=nbin)
        rare = 1.0 - pmf[k] / pmax                    # edge bins are rare -> brighter
        gain = min(0.95, 0.40 + 0.30 * min(1.0, ev["t"] / max(dur, 1e-6)) + 0.20 * rare)
        out.append({"t": ev["t"], "note": note, "gain": round(gain, 3),
                    "x": round(geo[0] + (k - rows / 2.0) * geo[2], 1)})
    return out


# --- orchestration ------------------------------------------------------------

def _worker(o, seed, dur, rows, bias, label, rule, sound):
    layout = get_layout(o)
    sim = simulate(seed, dur, rows, bias)
    name = f"{SCENE}_{label}_{layout.tag}"
    video = studio.OUT_DIR / f"{name}_silent.mp4"
    d = render(layout, sim, video, rule)
    kit.deliver(SCENE, name, layout, video, build_events(sim, layout, dur), d, sound)


def main():
    seed = int(arg("--seed", 0))
    dur = float(arg("--dur", 30.0))
    rows = int(arg("--rows", 14))
    bias = float(arg("--bias", 0.5))
    label = arg("--label", f"s{seed}")
    rule = arg("--rule", "")                  # captions are a POST-RENDER pass
    sound = arg("--sound", "1") != "0"
    if not 4 <= rows <= 20:
        sys.exit("--rows must be 4..20")
    if not 0.05 <= bias <= 0.95:
        sys.exit("--bias must be 0.05..0.95")
    studio.OUT_DIR.mkdir(exist_ok=True)

    sim = simulate(seed, dur, rows, bias)
    if kit.has("--still"):
        layout = get_layout(kit.orients()[0])
        f = int(arg("--frame", str(sim["nf"] - 1)))
        png = studio.OUT_DIR / f"{SCENE}_{label}_f{f}_{layout.tag}.png"
        render(layout, sim, png, rule, still_frame=f)
        print(f"[{SCENE}] -> {png}")
        return
    ev5 = kit.density_report([{"t": e["t"]} for e in sim["events"]], dur)
    print(f"[{SCENE}] seed={seed} rows={rows} bias={bias} balls={sim['total']} "
          f"max_bin={max(sim['counts'])} per5s={ev5}")
    kit.fan_out(_worker, (seed, dur, rows, bias, label, rule, sound), SCENE)


if __name__ == "__main__":
    main()
