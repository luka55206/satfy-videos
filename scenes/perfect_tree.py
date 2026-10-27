"""PERFECT TREE — "Only ONE angle makes a perfect tree": too narrow = overlap, too wide = gaps, 60° = perfect.

A fully grown branching tree (each branch 62 % (= 1/phi) of the one before) whose branch angle sweeps
live. Below 60deg the two halves cross into each other (the crossing branches turn red: OVERLAP);
above 60deg a gap opens in the middle (highlighted: GAPS); at exactly 60deg the halves meet without
crossing and the tree snaps gold and blossoms (PERFECT). Facts verified in golden_tree.py's notes:
58deg overlaps, 62deg keeps a gap, 60deg meets.

Payoff-first + seamless loop: the video opens on the perfect blossomed tree and ends on it.
Audio (original synthesis only): a soft glide that follows the angle, a gentle low cluster on OVERLAP,
a hollow note on GAPS, a click + bright chord + shimmer on the snap to PERFECT, a periodic pad.
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

SCENE = "perfect_tree"
PHI = (1 + 5 ** 0.5) / 2
RATIO = 1 / PHI
DEPTH = 12
GOLD = (1.0, 0.80, 0.38)
RED = (1.0, 0.30, 0.30)
BLOSSOM = (1.0, 0.62, 0.78)
# angle keyframes (time s, degrees); smooth between them
BEAT = 0.5                               # 120 BPM grid: every key moment lands on a beat
KEYS = [(0.0, 60), (0.5, 60), (2.0, 46), (3.0, 46), (5.0, 78), (6.0, 78), (7.5, 57.5), (8.25, 61.5),
        (9.0, 60), (12.5, 60)]
T_LOOP = KEYS[-1][0]
T_SNAP = 9.0
T_OPEN = 0.5                             # payoff-first: the perfect tree for one beat


def _sparks(n=150, seed=7):
    rng = np.random.default_rng(seed)
    ang = rng.uniform(0, 2 * np.pi, n)
    spd = rng.uniform(0.35, 1.25, n)
    return np.stack([np.cos(ang) * spd, np.sin(ang) * spd + 0.35, rng.uniform(0, 6.28, n),
                     rng.uniform(2.0, 5.0, n)], 1)


SPARKS = _sparks()


def angle_at(t):
    for (t0, a0), (t1, a1) in zip(KEYS, KEYS[1:]):
        if t <= t1:
            return a0 + (a1 - a0) * smooth((t - t0) / max(t1 - t0, 1e-6))
    return KEYS[-1][1]


def phase(t):
    a = angle_at(t)
    if abs(a - 60) < 0.25 and (t < T_OPEN or t >= T_SNAP):
        return "PERFECT"
    return "OVERLAP" if a < 59.5 else ("GAPS" if a > 60.5 else "")


def tree(theta_deg):
    """All segments as arrays: x0, y0, x1, y1, level, side (0 left half, 1 right half, -1 trunk)."""
    th = math.radians(theta_deg)
    xs0, ys0, xs1, ys1, lv, sd = [0.0], [0.0], [0.0], [1.0], [0], [-1]
    x, y = np.array([0.0]), np.array([1.0])
    ang, L = np.array([math.pi / 2]), 1.0
    side = np.array([-1])
    for k in range(1, DEPTH):
        ang = np.repeat(ang, 2) + np.tile([th, -th], len(ang))
        x, y = np.repeat(x, 2), np.repeat(y, 2)
        side = np.tile([0, 1], 1) if k == 1 else np.repeat(side, 2)
        L *= RATIO
        x1, y1 = x + L * np.cos(ang), y + L * np.sin(ang)
        xs0 += list(x); ys0 += list(y); xs1 += list(x1); ys1 += list(y1)
        lv += [k] * len(x); sd += list(side)
        x, y = x1, y1
    return (np.array(xs0), np.array(ys0), np.array(xs1), np.array(ys1), np.array(lv), np.array(sd))


def level_col(k):
    u = k / (DEPTH - 1)
    stops = [(0.0, (0.55, 0.36, 0.22)), (0.35, (0.45, 0.62, 0.30)), (0.7, (0.35, 0.85, 0.50)), (1.0, GOLD)]
    for (u0, c0), (u1, c1) in zip(stops, stops[1:]):
        if u <= u1:
            q = (u - u0) / (u1 - u0)
            return tuple(a + (b - a) * q for a, b in zip(c0, c1))
    return GOLD


def simulate():
    return {"nf": int(round(T_LOOP * FPS))}


class Scene:
    def __init__(self, layout, sim):
        self.L, self.sim = layout, sim
        self.canvas = Canvas(layout.w, layout.h, studio.render_scale())
        w, h = layout.w, layout.h
        xmax, ymax = 0.0, 0.0
        for a in (46, 60, 78):
            x0, y0, x1, y1, _, _ = tree(a)
            xmax = max(xmax, np.abs(x1).max())
            ymax = max(ymax, y1.max())
        self.S = min(w * 0.46 / xmax, h * 0.40 / ymax)
        self.ox, self.oy = w / 2, h * 0.635

    def draw(self, f, rule):
        L, c = self.L, self.canvas
        w, h = L.w, L.h
        t = f * DT
        ctx = c.ctx
        g = cairo.RadialGradient(w / 2, h * 0.45, 0, w / 2, h * 0.45, max(w, h) * 0.7)
        g.add_color_stop_rgb(0.0, 0.07, 0.06, 0.11)
        g.add_color_stop_rgb(1.0, 0.01, 0.01, 0.02)
        ctx.set_source(g)
        ctx.paint()
        a = angle_at(t)
        ph = phase(t)
        perfect_k = 0.0
        if t < T_OPEN + 0.3:
            perfect_k = 1.0 - smooth((t - T_OPEN) / 0.3)
        elif t >= T_SNAP:
            perfect_k = smooth((t - T_SNAP) / 0.25)
        x0, y0, x1, y1, lv, sd = tree(a)
        S, ox, oy = self.S, self.ox, self.oy
        age = t - T_SNAP
        punch = 0.06 * math.exp(-age / 0.18) if age >= 0 else 0.0     # the "gift" zoom punch
        S = S * (1 + punch)
        cy_tree = oy - 0.62 * y1.max() * S
        # GIFT: slowly rotating golden rays behind the tree (rotation completes whole turns over the loop)
        if perfect_k > 0.01:
            rot = 2 * math.pi * 2 * t / T_LOOP
            R = w * 0.75
            for k in range(16):
                a0 = rot + k * 2 * math.pi / 16
                ctx.move_to(ox, cy_tree)
                ctx.arc(ox, cy_tree, R, a0, a0 + math.pi / 30)
                ctx.close_path()
            rg = cairo.RadialGradient(ox, cy_tree, 0, ox, cy_tree, R)
            rg.add_color_stop_rgba(0.0, *GOLD, 0.26 * perfect_k)
            rg.add_color_stop_rgba(1.0, *GOLD, 0.0)
            ctx.set_source(rg)
            ctx.fill()
            c.glow(ox, cy_tree, w * 0.12, GOLD, strength=0.22 * perfect_k, reach=3.0)
        # crossing = a branch from one half reaching into the other half (x on the wrong side)
        cross = ((sd == 0) & (np.maximum(x0, x1) > 1e-9)) | ((sd == 1) & (np.minimum(x0, x1) < -1e-9))
        bad = 1.0 - min(1.0, abs(a - 60) / 4.0)
        bad = 1.0 - bad                                       # 0 at 60deg, 1 when clearly wrong
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        for k in range(DEPTH):
            m = lv == k
            col = level_col(k)
            if perfect_k > 0:
                col = tuple(p + (q - p) * 0.55 * perfect_k for p, q in zip(col, GOLD))
            ctx.set_line_width(max(1.3, 20 * RATIO ** k))
            for normal in (True, False):
                sel = m & (~cross if normal else cross)
                if not sel.any():
                    continue
                cc = col if normal else tuple(p + (q - p) * bad for p, q in zip(col, RED))
                ctx.set_source_rgb(*cc)
                for i in np.nonzero(sel)[0]:
                    ctx.move_to(ox + x0[i] * S, oy - y0[i] * S)
                    ctx.line_to(ox + x1[i] * S, oy - y1[i] * S)
                ctx.stroke()
        # the middle band: where the halves OVERLAP (left reaches past right) or the GAP between them
        if ph in ("OVERLAP", "GAPS") and bad > 0.05:
            lx = np.maximum(x0, x1)[(sd == 0) & (lv >= 2)].max()   # furthest right the LEFT half reaches (past the fork)
            rx = np.minimum(x0, x1)[(sd == 1) & (lv >= 2)].min()   # furthest left the RIGHT half reaches
            lo, hi = min(lx, rx), max(lx, rx)
            if hi - lo > 1e-3:
                upper = y1[(sd >= 0) & (np.abs(x1) < (hi - lo) + 0.25)]
                ytop = upper.max() if upper.size else y1.max()
                gy0, gy1 = oy - (ytop + 0.04) * S, oy - (ytop * 0.55) * S
                bx0, bw = ox + lo * S, (hi - lo) * S
                ctx.rectangle(bx0, gy0, bw, gy1 - gy0)
                ctx.set_source_rgba(*RED, 0.32 * bad)
                ctx.fill()
                ctx.set_line_width(4)
                ctx.set_source_rgba(*RED, 0.9 * bad)
                for xx in (bx0, bx0 + bw):
                    ctx.move_to(xx, gy0)
                    ctx.line_to(xx, gy1)
                ctx.stroke()

        # PERFECT: blossoms pop in a wave from the centre (the gift opening), sparks, rings
        if perfect_k > 0.01:
            tips = np.nonzero(lv == DEPTH - 1)[0][::2]
            mx, my = 0.0, y1.max() * 0.92
            for i in tips:
                d = math.hypot(x1[i] - mx, y1[i] - my)
                if age >= 0:
                    q = min(1.0, max(0.0, (age - d * 0.35) / 0.18))
                    sz = 4.5 * (1 + 0.6 * math.exp(-max(age - d * 0.35, 0) / 0.08)) * q
                else:
                    q, sz = perfect_k, 4.5 * perfect_k
                if q > 0.01:
                    c.circle(ox + x1[i] * S, oy - y1[i] * S, sz, BLOSSOM, alpha=0.88 * q)
            if 0 <= age < 3.2:                                          # golden sparks burst + fall
                for vx, vy, ph0, size in SPARKS:
                    px = ox + vx * age * w * 0.55
                    py = cy_tree - (vy * age - 0.45 * age * age) * w * 0.55
                    tw = 0.6 + 0.4 * math.sin(ph0 + age * 14)
                    al = max(0.0, 1 - age / 3.2) * tw
                    if al > 0.02:
                        r = size * 2.2 * (1 - age / 4.5)
                        c.glow(px, py, r, GOLD, strength=0.35 * al, reach=2.6)
                        c.circle(px, py, r, (1.0, 0.93, 0.70), alpha=al)
            if age >= 0:
                for kk in range(3):
                    ar = age - 0.12 * kk
                    if 0 < ar < 1.0:
                        c.ring(ox, cy_tree, w * (0.05 + 0.40 * smooth(ar)), GOLD, width=5, alpha=0.7 * (1 - ar))
        # HUD
        fs = w * 0.05
        c.text_centered("FAMOUS SHAPES · THE PERFECT TREE", h * 0.205, size=h * 0.015, color=GOLD, alpha=0.8)
        acol = GOLD if ph == "PERFECT" else (RED if ph in ("OVERLAP", "GAPS") else (1, 1, 1))
        c.text_centered(f"angle {a:.0f}°", h * 0.672, size=fs * 1.05, color=acol)
        if ph:
            lab = {"PERFECT": "PERFECT", "OVERLAP": "OVERLAP", "GAPS": "GAPS"}[ph]
            col = GOLD if ph == "PERFECT" else RED
            pop = 1.0
            c.text_centered(lab, h * 0.727, size=fs * 1.25 * pop, color=col)
        if perfect_k > 0.01:
            c.text_centered("no gaps · no overlap · each branch 62% of the last", h * 0.765, size=fs * 0.50,
                            color=(0.92, 0.90, 0.85), alpha=perfect_k, bold=False, max_w=w * 0.94)
        if rule:
            c.caption(rule, alpha=1.0, layout=L)
        c.watermark(L)


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


def build_events(sim, layout):
    out = [{"t": 0.005 + 0.01 * j, "note": n, "gain": 0.46, "x": layout.w / 2} for j, n in enumerate((55, 62, 67, 71))]
    for j, note in enumerate((79, 76, 74, 71)):                      # leaving perfect: a quick descending run
        out.append({"t": round(T_OPEN + 0.06 * j, 4), "note": note, "gain": 0.24, "x": layout.w / 2})
    for t0, n in ((7.5, 60), (8.25, 62)):                             # hunting for the angle
        out.append({"t": t0, "note": n, "gain": 0.26, "x": layout.w / 2})
    for j, note in enumerate((43, 55, 62, 67, 71, 74, 79)):           # THE DROP: the gift opens
        out.append({"t": round(T_SNAP + 0.01 * j, 4), "note": note, "gain": 0.50, "x": layout.w / 2})
    for j, note in enumerate((79, 83, 86, 91, 95, 91, 86, 83)):       # sparkle arpeggio over the sparks
        out.append({"t": round(T_SNAP + 0.25 + 0.125 * j, 4), "note": note, "gain": 0.20, "x": layout.w / 2})
    return sorted(out, key=lambda e: e["t"])


def bed():
    """ORIGINAL beat (synthesised): 120 BPM kick + offbeat hats under the sweep, a wobble-bass hit on
    OVERLAP and GAPS, a riser + snare roll while the angle hunts, a sub boom + soft cymbal on the drop,
    the groove continuing lighter under the gift, and a quiet pad. Periodic over the loop."""
    sr = audio.SR
    n = int(round(T_LOOP * sr))
    out = np.zeros(n)
    rng = np.random.default_rng(5)

    def put(sig, t0, g):
        idx = (np.arange(len(sig)) + int(round(t0 * sr))) % n
        np.add.at(out, idx, g * sig)

    def tt(L):
        return np.arange(int(L * sr)) / sr

    t1 = tt(0.35)
    kick = np.sin(2 * np.pi * np.cumsum(50 + 120 * np.exp(-t1 * 30)) / sr) * np.exp(-t1 * 10)
    kick = np.tanh(2.2 * kick) / np.tanh(2.2)
    th = tt(0.06)
    hat = np.diff(rng.standard_normal(len(th) + 1)) * np.exp(-th * 80)
    tc = tt(0.15)
    snare = rng.standard_normal(len(tc)) * np.exp(-tc * 28) + 0.5 * np.sin(2 * np.pi * 190 * tc) * np.exp(-tc * 30)
    tw = tt(0.5)
    wob = (2 * ((55 * tw) % 1.0) - 1) * (0.6 + 0.4 * np.sin(2 * np.pi * 8 * tw)) * np.exp(-tw * 3)
    wob = np.tanh(2 * np.convolve(wob, np.ones(8) / 8, "same"))
    tb = tt(1.6)
    boom = np.sin(2 * np.pi * np.cumsum(38 + 60 * np.exp(-tb * 12)) / sr) * np.exp(-tb * 2.5)
    tcy = tt(2.0)
    cym = np.convolve(rng.standard_normal(len(tcy)), [1, -1], "same") * np.exp(-tcy * 2.2) * 0.35
    n_beats = int(round(T_LOOP / BEAT))
    for k in range(n_beats):
        t0 = k * BEAT
        in_hunt = 7.5 <= t0 < T_SNAP
        put(kick, t0, 0.80 if not in_hunt else 0.55)
        put(hat, t0 + BEAT / 2, 0.22)
        if t0 >= T_SNAP:
            put(hat, t0 + BEAT * 0.75, 0.12)
    for t0 in (2.0, 5.0):                                            # the "wrong" wobble hits
        put(wob, t0, 0.55)
    for j in range(12):                                              # snare roll into the drop
        put(snare, 7.5 + j * (1.5 / 12), 0.10 + 0.35 * j / 11)
    tr = tt(1.5)                                                     # riser
    riser = np.sin(2 * np.pi * np.cumsum(200 + 900 * (tr / 1.5) ** 2) / sr) * (tr / 1.5) ** 2 * 0.25
    riser += np.convolve(rng.standard_normal(len(tr)), np.ones(4) / 4, "same") * (tr / 1.5) ** 3 * 0.15
    put(riser, 7.5, 1.0)
    put(boom, T_SNAP, 0.9)
    put(cym, T_SNAP, 0.8)
    pad = kit.loop_pad(T_LOOP, ((43, 1.0), (50, 0.7), (55, 0.45), (59, 0.3)), gain=0.012)
    return (0.38 * out + pad[:n]).astype(np.float32)


def _worker(o, sim, label, rule):
    layout = get_layout(o)
    name = f"{SCENE}_{label}_{layout.tag}"
    video = studio.OUT_DIR / f"{name}_silent.mp4"
    d = render(layout, sim, video, rule)
    kit.deliver_loop(SCENE, name, layout, video, build_events(sim, layout), d, voice="glassharp", bed=bed(),
                     peak_db=-6.0)


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
    print(f"[{SCENE}] {T_LOOP:.1f}s")
    kit.fan_out(_worker, (sim, label, rule), SCENE)


if __name__ == "__main__":
    main()
