"""PEG DROP scene: balls fall through a staggered field of pegs and pile up in bins.

The channel's core format (a physics ball-drop board, the same mechanic people
call by a trademarked name; see docs/compliance.md). Every frame is code: a real
2D rigid-circle simulation (ball-peg and ball-ball collisions, gravity, walls),
seeded and fixed-dt, so it is deterministic and reproducible.

NAMING (legal): never put the trademarked game name in a title, description,
tag, hashtag, file name or on screen. Scene/file name here is "pegdrop". No
money, prizes, multipliers, "win" language or casino styling: the bins are
counters, never payouts.

The ONE visible rule:   every ball drops from the same spot (or the drop mode).
The escalation:         the drop rate climbs, ~1 ball/s -> ~14 balls/s.
The payoff:             the piles trace a bell curve (a normal curve fades in).
The loop:               the piles drain to nothing -> frame 0 is the empty board.

Audio: 100% original synthesis. Pitch = where a ball hit (low pegs left, high
right, pentatonic = a gravity harp); a lower chime when a ball reaches its bin.
NO melodies, NO samples, NO music bed: nothing for Content ID to match.

    ./run.ps1 -Scene pegdrop -Fast -Still -Frame 600
    ./run.ps1 -Scene pegdrop -Fast
    ./run.ps1 -Scene pegdrop -Orient both -SceneArgs @('--seed','3','--rows','12')

Variant knobs (every upload needs ONE change a viewer can name):
    --rows N    peg rows, even, 6..16        --cols N   bins, even, 6..14
    --bounce E  peg restitution 0.2..0.85    --drop MODE center | sweep | random
    --lane center   open the middle lane (no pegs within 0.6 of the centre)
    --dur S     seconds of dropping          --rule "caption" (post-render pass)
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

SCENE = "pegdrop"

# board geometry in "units" (1 unit = horizontal peg spacing)
DY = 0.80          # row spacing
RB = 0.21          # ball radius
RP = 0.09          # peg radius
DROP_H = 1.9       # empty drop zone above the first peg row
BIN_H = 4.2        # bin height below the divider tips
CATCH = 0.9        # a ball counts as landed this far below the divider tips
G = 14.0           # gravity, units/s^2
VY0 = 6.0          # launch speed: keeps back-to-back drops from overlapping
SUB = 4            # physics substeps per frame
E_BALL = 0.45      # ball-ball restitution
E_WALL = 0.40
FALL_S = 0.22      # a caught ball settles onto its pile over this long
START_S = 0.30     # first drop (frame 0 stays an empty board)
TAIL_S = 2.8       # no new drops this long before dur ends (fall time)
I0, I1 = 0.90, 0.07    # drop interval, start -> end (the escalation)
HOLD_S = 1.0
DRAIN_S = 1.4


# --- pass 1: simulate ---------------------------------------------------------

def _n_row(r, cols):
    return cols if r % 2 == 0 else cols - 1


def simulate(seed, dur, rows, cols, bounce, drop, lane):
    rng = random.Random(seed)
    y_div = (rows - 1) * DY + 0.9          # divider tips, under the last peg row
    floor_y = y_div + BIN_H
    xmax = cols / 2.0

    pegs, row_pegs = [], []                # row_pegs[r] = {i: (x, y, idx)}
    for r in range(rows):
        n, d = _n_row(r, cols), {}
        for i in range(n):
            x = i - (n - 1) / 2.0
            if lane == "center" and abs(x) < 0.6:
                continue
            d[i] = (x, r * DY, len(pegs))
            pegs.append((x, r * DY))
        row_pegs.append(d)
    npeg = len(pegs)

    spawn_end = dur - TAIL_S
    balls = []                              # every ball ever dropped
    live = []                               # indices of balls still in play
    landed_order = []                       # indices, in landing order
    counts = [0] * cols
    hits = []                               # (t, kind, peg_idx, x, impulse)
    frames, flash_f, landed_f = [], [], []
    flash = np.zeros(max(npeg, 1), dtype=np.float32)
    decay = float(np.exp(-DT / 0.10))
    next_drop, n_drop = START_S, 0
    t_cap = dur + 12.0
    f = 0
    h = DT / SUB

    def drop_x(n):
        if drop == "sweep":
            return 0.8 * (xmax - 1.0) * math.sin(n * 0.7)
        if drop == "random":
            return rng.uniform(-(xmax - 1.0), xmax - 1.0)
        return rng.uniform(-0.03, 0.03)     # center: the same spot, +-0.03

    def collide(b, px, py, rr, t, idx, kind):
        dx, dy = b["x"] - px, b["y"] - py
        d2 = dx * dx + dy * dy
        lim = RB + rr
        if d2 >= lim * lim or d2 < 1e-12:
            return
        d = math.sqrt(d2)
        nx, ny = dx / d, dy / d
        b["x"], b["y"] = px + nx * lim, py + ny * lim
        vn = b["vx"] * nx + b["vy"] * ny
        if vn < 0.0:
            b["vx"] -= (1.0 + bounce) * vn * nx
            b["vy"] -= (1.0 + bounce) * vn * ny
            j = rng.uniform(-1.0, 1.0) * 0.12 * (-vn)     # symmetry breaker
            b["vx"] += -ny * j
            b["vy"] += nx * j
            hits.append((round(t, 5), kind, idx, round(px, 3), min(1.0, -vn / 12.0)))
            if kind == "peg":
                flash[idx] = 1.0

    while True:
        t = f * DT
        # --- spawn (deterministic; waits a frame if the drop spot is busy)
        if t >= next_drop and t < spawn_end:
            x0 = drop_x(n_drop)
            y0 = -DROP_H * 0.6
            if all((balls[i]["x"] - x0) ** 2 + (balls[i]["y"] - y0) ** 2
                   > (2.3 * RB) ** 2 for i in live):
                balls.append({"x": x0, "y": y0, "vx": 0.0, "vy": VY0, "hue": (n_drop * 0.031) % 1.0,
                              "bin": None, "age": 0.0})
                live.append(len(balls) - 1)
                n_drop += 1
                u = (t - START_S) / max(spawn_end - START_S, 1e-6)
                next_drop = t + I0 * (I1 / I0) ** min(1.0, max(0.0, u))
        # --- physics
        for _ in range(SUB):
            ts = t
            for bi in live:
                b = balls[bi]
                b["vy"] += G * h
                b["x"] += b["vx"] * h
                b["y"] += b["vy"] * h
                if b["bin"] is None:
                    rr = int(round(b["y"] / DY))
                    for r in (rr - 1, rr, rr + 1):
                        if 0 <= r < rows:
                            n = _n_row(r, cols)
                            i0 = int(round(b["x"] + (n - 1) / 2.0))
                            for i in (i0 - 1, i0, i0 + 1):
                                p = row_pegs[r].get(i)
                                if p is not None:
                                    collide(b, p[0], p[1], RP, ts, p[2], "peg")
                    if b["y"] > y_div - 0.5:       # divider tips
                        k0 = int(round(b["x"] + xmax))
                        for k in (k0 - 1, k0, k0 + 1):
                            if 1 <= k <= cols - 1:
                                collide(b, k - xmax, y_div, RP, ts, -1, "tip")
                    if b["x"] < -xmax + RB:
                        b["x"], b["vx"] = -xmax + RB, abs(b["vx"]) * E_WALL
                    elif b["x"] > xmax - RB:
                        b["x"], b["vx"] = xmax - RB, -abs(b["vx"]) * E_WALL
                    if b["y"] > y_div + RB:
                        b["bin"] = min(cols - 1, max(0, int(b["x"] + xmax)))
                if b["bin"] is not None:
                    lo = b["bin"] - xmax + RB
                    hi = b["bin"] - xmax + 1.0 - RB
                    if b["x"] < lo:
                        b["x"], b["vx"] = lo, abs(b["vx"]) * E_WALL
                    elif b["x"] > hi:
                        b["x"], b["vx"] = hi, -abs(b["vx"]) * E_WALL
                b["age"] += h
                if b["age"] > 8.0 and b["bin"] is None and int(b["age"] / h) % 240 == 0:
                    b["vx"] += rng.uniform(-1.5, 1.5)   # unstick a perched ball
            # ball-ball
            for a in range(len(live)):
                A = balls[live[a]]
                for c in range(a + 1, len(live)):
                    B = balls[live[c]]
                    dy = B["y"] - A["y"]
                    if dy > 2 * RB or dy < -2 * RB:
                        continue
                    dx = B["x"] - A["x"]
                    d2 = dx * dx + dy * dy
                    if d2 >= 4 * RB * RB or d2 < 1e-12:
                        continue
                    d = math.sqrt(d2)
                    nx, ny = dx / d, dy / d
                    push = (2 * RB - d) / 2.0
                    A["x"] -= nx * push; A["y"] -= ny * push
                    B["x"] += nx * push; B["y"] += ny * push
                    vn = (B["vx"] - A["vx"]) * nx + (B["vy"] - A["vy"]) * ny
                    if vn < 0.0:
                        j = -(1.0 + E_BALL) * vn / 2.0
                        A["vx"] -= j * nx; A["vy"] -= j * ny
                        B["vx"] += j * nx; B["vy"] += j * ny
        # --- catch: a ball deep enough in a bin has landed
        for bi in list(live):
            b = balls[bi]
            if b["bin"] is not None and b["y"] >= y_div + CATCH:
                b["t_land"] = t
                b["xc"], b["yc"] = b["x"], b["y"]
                b["rank"] = counts[b["bin"]]
                counts[b["bin"]] += 1
                live.remove(bi)
                landed_order.append(bi)
        frames.append([(balls[i]["x"], balls[i]["y"], balls[i]["hue"]) for i in live])
        flash_f.append(flash.copy())
        landed_f.append(len(landed_order))
        flash *= decay
        f += 1
        if (t >= spawn_end and not live) or t > t_cap:
            break
    if live:
        sys.exit(f"[{SCENE}] {len(live)} balls still falling at the time cap; "
                 f"lower --rows or raise --dur")

    nf = f
    maxc = max(counts)
    row_h = min(2 * RB * 0.92, (BIN_H - CATCH - 0.3) / max(1, math.ceil(maxc / 2.0)))
    for bi in landed_order:
        b = balls[bi]
        n = b["rank"]
        b["sx"] = b["bin"] - xmax + 0.5 + ((n % 2) - 0.5) * 2 * RB * 1.02
        b["sy"] = floor_y - RB - (n // 2) * row_h
    return {"frames": frames, "flash": flash_f, "landed_f": landed_f,
            "balls": [balls[i] for i in landed_order], "hits": hits, "counts": counts,
            "rows": rows, "cols": cols, "nf": nf, "npeg": npeg, "pegs": pegs,
            "y_div": y_div, "floor_y": floor_y, "row_h": row_h, "total": len(landed_order)}


# --- pass 2: render -----------------------------------------------------------

def _geometry(layout, sim):
    """Board rectangle per orientation -> (cx, y_origin, px_per_unit)."""
    h_u = DROP_H + sim["floor_y"] + 0.3
    w_u = sim["cols"] + 1.4
    if layout.tag == "9x16":
        x0, x1, y0, y1 = layout.w * 0.04, layout.w * 0.96, layout.h * 0.185, layout.h * 0.745
    else:
        x0, x1 = layout.w / 2 - layout.h * 0.4, layout.w / 2 + layout.h * 0.4
        y0, y1 = layout.h * 0.07, layout.h * 0.93
    s = min((x1 - x0) / w_u, (y1 - y0) / h_u)
    return (x0 + x1) / 2, y0 + (y1 - y0 - h_u * s) / 2 + DROP_H * s, s


def draw(canvas, layout, sim, f, e, rule, geo):
    cols = sim["cols"]
    cx, oy, s = geo
    X = lambda u: cx + u * s     # noqa: E731
    Y = lambda u: oy + u * s     # noqa: E731
    fi = min(f, sim["nf"] - 1)
    t = f * DT
    keep = 1.0 - e                                   # 1 -> 0 while draining
    xmax, y_div, floor_y = cols / 2.0, sim["y_div"], sim["floor_y"]
    canvas.clear()

    # board frame: bin dividers, side walls, floor
    segs = [(X(k - xmax), Y(y_div), X(k - xmax), Y(floor_y)) for k in range(cols + 1)]
    segs.append((X(-xmax), Y(floor_y), X(xmax), Y(floor_y)))
    segs += [(X(-xmax), Y(-DROP_H), X(-xmax), Y(y_div)), (X(xmax), Y(-DROP_H), X(xmax), Y(y_div))]
    canvas.lines(segs, (0.62, 0.68, 0.80), width=max(2.0, s * 0.04), alpha=0.35)

    # piles (settled balls), tinted by their own drop hue; the newest ease in
    L = sim["landed_f"][fi] if f < sim["nf"] else sim["total"]
    for b in sim["balls"][:L]:
        u = smooth((t - b["t_land"]) / FALL_S) if f < sim["nf"] else 1.0
        x = b["xc"] + (b["sx"] - b["xc"]) * u
        y = b["yc"] + (b["sy"] - b["yc"]) * u * u
        canvas.circle(X(x), Y(y), RB * s, kit.wheel(b["hue"]), alpha=0.95 * keep)

    # pegs, flashing on a hit
    fl = sim["flash"][fi]
    for idx, (px, py) in enumerate(sim["pegs"]):
        v = float(fl[idx])
        col = (0.55 + 0.45 * v, 0.62 + 0.38 * v, 0.76 + 0.24 * v)
        if v > 0.05:
            canvas.circle(X(px), Y(py), RP * s * 2.6, (1, 1, 1), alpha=0.22 * v)
        canvas.circle(X(px), Y(py), RP * s, col, alpha=0.55 + 0.45 * v)

    # falling balls (none while draining: everything has landed)
    if f < sim["nf"]:
        for x, y, hue in sim["frames"][fi]:
            col = kit.wheel(hue)
            canvas.circle(X(x), Y(y), RB * s * 1.7, col, alpha=0.16)
            canvas.circle(X(x), Y(y), RB * s, col, alpha=1.0)

    cap_a = min(1.0, t / 0.4) * keep                  # 0 at frame 0 AND at the seam
    if rule:
        canvas.caption(rule, alpha=cap_a, layout=layout)
    n = int(round((L if f < sim["nf"] else sim["total"]) * keep))
    canvas.counter(f"Balls: {n:,}", layout=layout, size_f=0.032)
    canvas.watermark(layout)


def render(layout, sim, out_path, rule, still_frame=None):
    canvas = Canvas(layout.w, layout.h, studio.render_scale())
    writer = None if still_frame is not None else VideoWriter(out_path, canvas, FPS)
    geo = _geometry(layout, sim)
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
    """Peg hits play the pentatonic scale by x position; a landing is a low chime.
    Sounded-rate ceiling lives HERE (the mixer ducks by density, so unthinned
    hits would not get louder): per-peg cooldown + a global minimum gap."""
    cols = sim["cols"]
    cx, _oy, s = _geometry(layout, sim)
    xmax = cols / 2.0
    t_end = sim["nf"] * DT
    out, last, last_peg = [], -1e9, {}
    for t, kind, idx, px, imp in sim["hits"]:
        if kind != "peg" or imp < 0.12:
            continue
        if t - last < 0.018 or t - last_peg.get(idx, -1e9) < 0.07:
            continue
        last, last_peg[idx] = t, idx
        note = kit.penta_note((px + xmax) / cols, root=57, scale=audio.PENTA_MAJOR, span=cols)
        gain = min(0.85, 0.22 + 0.45 * imp + 0.18 * min(1.0, t / max(t_end, 1e-6)))
        out.append({"t": t, "note": note, "gain": round(gain, 3), "x": round(cx + px * s, 1)})
    for b in sim["balls"]:
        note = kit.penta_note((b["bin"] + 0.5) / cols, root=45, scale=audio.PENTA_MAJOR, span=cols)
        out.append({"t": round(b["t_land"] + FALL_S, 5), "note": note, "gain": 0.9,
                    "x": round(cx + (b["bin"] - xmax + 0.5) * s, 1)})
    out.sort(key=lambda e: e["t"])
    return out


# --- orchestration ------------------------------------------------------------

def _worker(o, sim, dur, label, rule, sound):
    layout = get_layout(o)
    name = f"{SCENE}_{label}_{layout.tag}"
    video = studio.OUT_DIR / f"{name}_silent.mp4"
    d = render(layout, sim, video, rule)
    kit.deliver(SCENE, name, layout, video, build_events(sim, layout, dur), d, sound)


def main():
    seed = int(arg("--seed", 0))
    dur = float(arg("--dur", 30.0))
    rows = int(arg("--rows", 12))
    cols = int(arg("--cols", 10))
    bounce = float(arg("--bounce", 0.55))
    drop = arg("--drop", "center")
    lane = arg("--lane", "none")
    label = arg("--label", f"s{seed}")
    rule = arg("--rule", "")                  # captions are a POST-RENDER pass
    sound = arg("--sound", "1") != "0"
    if rows % 2 or not 6 <= rows <= 16:
        sys.exit("--rows must be even, 6..16")
    if cols % 2 or not 6 <= cols <= 14:
        sys.exit("--cols must be even, 6..14")
    if not 0.2 <= bounce <= 0.85:
        sys.exit("--bounce must be 0.2..0.85")
    if drop not in ("center", "sweep", "random") or lane not in ("none", "center"):
        sys.exit("--drop center|sweep|random ; --lane none|center")
    studio.OUT_DIR.mkdir(exist_ok=True)

    sim = simulate(seed, dur, rows, cols, bounce, drop, lane)   # ONCE, shared by layouts
    if kit.has("--still"):
        layout = get_layout(kit.orients()[0])
        f = int(arg("--frame", str(sim["nf"] - 1)))
        png = studio.OUT_DIR / f"{SCENE}_{label}_f{f}_{layout.tag}.png"
        render(layout, sim, png, rule, still_frame=f)
        print(f"[{SCENE}] -> {png}")
        return
    peg_hits = [{"t": h[0]} for h in sim["hits"] if h[1] == "peg"]
    print(f"[{SCENE}] seed={seed} rows={rows} cols={cols} drop={drop} lane={lane} "
          f"balls={sim['total']} max_bin={max(sim['counts'])} "
          f"hits_per5s={kit.density_report(peg_hits, sim['nf'] * DT)}")
    kit.fan_out(_worker, (sim, dur, label, rule, sound), SCENE)


if __name__ == "__main__":
    main()
