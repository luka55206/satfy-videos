"""GOLDEN TREE — every branch is 1/phi of the one before; at 60 degrees the tips touch perfectly.

The "golden 60" self-contacting tree (Mandelbrot & Frame): a trunk splits into two branches 60deg
either side of its direction, each 1/phi as long, again and again. With exactly this ratio and angle,
the left and right halves close in on the centre line and MEET there without ever crossing (checked
numerically: the closest gap shrinks 0.060 -> 0.023 -> 0.009 of the trunk at depth 8/10/12, about
1/phi^2 per two levels, touching in the limit; 58deg and below overlap, 62deg and above keep a gap).

Built to the channel's formula: frame 0 = the trunk already growing + a chord; each level grows a bit
faster; the branch counter climbs 1 -> 8,191; the MEETING POINT in the middle glows brighter, with a chime, each
time a level closes the gap (the reward); payoff = the full tree, a gold pulse, blossoms at every tip, and the fact. Then the tree
retracts into the trunk (loop to frame 0). Audio: original synthesis only.
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

SCENE = "golden_tree"
PHI = (1 + 5 ** 0.5) / 2
RATIO = 1 / PHI
THETA = math.radians(60)
DEPTH = 13
D0, DK = 1.15, 0.88                      # seconds for level 0, then each level x0.88
T_BLOOM, T_HOLD, T_BACK = 1.6, 0.8, 0.7
P_START = 0.18                           # frame 0: the trunk is already 18 % grown
GOLD = (1.0, 0.80, 0.38)
BLOSSOM = (1.0, 0.62, 0.78)


def level_col(k):
    u = k / (DEPTH - 1)
    stops = [(0.0, (0.55, 0.36, 0.22)), (0.35, (0.45, 0.62, 0.30)), (0.7, (0.35, 0.85, 0.50)), (1.0, GOLD)]
    for (u0, c0), (u1, c1) in zip(stops, stops[1:]):
        if u <= u1:
            k2 = (u - u0) / (u1 - u0)
            return tuple(a + (b - a) * k2 for a, b in zip(c0, c1))
    return GOLD


def build_tree():
    """Segments per level: list of (x0, y0, x1, y1). Trunk (0,0)->(0,1)."""
    levels = [[(0.0, 0.0, 0.0, 1.0, math.pi / 2, 1.0)]]
    for _ in range(1, DEPTH):
        nxt = []
        for x0, y0, x1, y1, a, L in levels[-1]:
            for da in (THETA, -THETA):
                b = a + da
                l2 = L * RATIO
                nxt.append((x1, y1, x1 + l2 * math.cos(b), y1 + l2 * math.sin(b), b, l2))
        levels.append(nxt)
    return levels


LEVELS = build_tree()
DUR = [D0 * DK ** k for k in range(DEPTH)]
STARTS = list(np.concatenate([[0.0], np.cumsum(DUR)[:-1]]))
T_GROW = float(sum(DUR))
T_LOOP = T_GROW + T_BLOOM + T_HOLD + T_BACK
# payoff-first: the video OPENS inside the bloom (scene T_A), retracts, regrows, and ends at T_A (seamless)
T_A = T_GROW + T_BLOOM + T_HOLD - 0.6              # opens on 0.6 s of full bloom, then retracts


def scene_t(v):
    return T_A + v if v < T_LOOP - T_A else v - (T_LOOP - T_A)


def meeting_point():
    """Where the left and right halves come closest (excluding the split point): they approach the
    centre line from both sides and meet there in the limit (gap shrinks ~1/phi^2 per two levels)."""
    pts = {0: [], 1: []}
    for k, segs in enumerate(LEVELS[1:], start=1):
        half = len(segs) // 2
        for i, sg in enumerate(segs):
            side = 0 if i < half else 1
            for q in range(5):
                x = sg[0] + (sg[2] - sg[0]) * q / 4
                y = sg[1] + (sg[3] - sg[1]) * q / 4
                if math.hypot(x, y - 1) > 0.08 and abs(x) < 0.15:
                    pts[side].append((x, y))
    A, Bp = np.array(pts[0]), np.array(pts[1])
    D = np.sqrt(((A[:, None, :] - Bp[None, :, :]) ** 2).sum(-1))
    i, j = np.unravel_index(D.argmin(), D.shape)
    return (A[i] + Bp[j]) / 2, D[i, j]


MEET, MEET_GAP = meeting_point()
CONTACTS = []


def simulate():
    return {"nf": int(round(T_LOOP * FPS))}


def grow_state(t):
    """(level index k, progress p in [0,1]) — fractional growth; rewinds at the end."""
    tb = T_GROW + T_BLOOM + T_HOLD
    if t >= tb:                                              # retract back to the frame-0 state
        g = 1.0 - smooth((t - tb) / T_BACK)
        total = P_START + (DEPTH - P_START) * g
        k = min(int(total), DEPTH - 1)
        return k, total - k if total < DEPTH else 1.0
    if t >= T_GROW:
        return DEPTH - 1, 1.0
    k = max(j for j in range(DEPTH) if STARTS[j] <= t)
    p = (t - STARTS[k]) / DUR[k]
    if k == 0:
        p = P_START + (1 - P_START) * p
    return k, p


class Scene:
    def __init__(self, layout, sim):
        self.L, self.sim = layout, sim
        self.canvas = Canvas(layout.w, layout.h, studio.render_scale())
        w, h = layout.w, layout.h
        xs = [v for segs in LEVELS for s in segs for v in (s[0], s[2])]
        ys = [v for segs in LEVELS for s in segs for v in (s[1], s[3])]
        self.bx = (min(xs), max(xs))
        self.by = (min(ys), max(ys))
        box_w, box_h = w * 0.92, h * 0.40
        self.S = min(box_w / (self.bx[1] - self.bx[0]), box_h / (self.by[1] - self.by[0]))
        self.ox = w / 2 - (self.bx[0] + self.bx[1]) / 2 * self.S
        self.oy = h * 0.625 + self.by[0] * self.S             # ground line

    def P(self, x, y):
        return self.ox + x * self.S, self.oy - y * self.S

    def draw(self, f, rule):
        L, c = self.L, self.canvas
        w, h = L.w, L.h
        t = scene_t(f * DT)
        ctx = c.ctx
        g = cairo.RadialGradient(w / 2, h * 0.45, 0, w / 2, h * 0.45, max(w, h) * 0.7)
        g.add_color_stop_rgb(0.0, 0.07, 0.06, 0.11)
        g.add_color_stop_rgb(1.0, 0.01, 0.01, 0.02)
        ctx.set_source(g)
        ctx.paint()
        k_now, p = grow_state(t)
        pe = smooth(p)
        pulse = smooth((t - T_GROW) / 0.5) * (1 - smooth((t - T_GROW - T_BLOOM - T_HOLD) / 0.5)) if t >= T_GROW else 0
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        for k in range(k_now + 1):
            segs = LEVELS[k]
            col = level_col(k)
            if pulse > 0:
                col = tuple(a + (b - a) * 0.6 * pulse for a, b in zip(col, GOLD))
            width = max(1.3, 20 * RATIO ** k)
            ctx.set_line_width(width)
            ctx.set_source_rgb(*col)
            frac = 1.0 if k < k_now else pe
            for x0, y0, x1, y1, _, _ in segs:
                a = self.P(x0, y0)
                b = self.P(x0 + (x1 - x0) * frac, y0 + (y1 - y0) * frac)
                ctx.move_to(*a)
                ctx.line_to(*b)
            ctx.stroke()
        # the meeting point in the middle: brighter with every level that closes the gap
        if k_now >= 3:
            q = self.P(*MEET)
            lev = (k_now - 3 + pe) / (DEPTH - 4)
            flash = 0.0
            for kk in range(4, k_now + 1):
                age = t - (STARTS[kk] + DUR[kk])
                if 0 <= age < 0.5 and t < T_GROW + 0.1:
                    flash = max(flash, 1 - age / 0.5)
            c.glow(*q, 10, GOLD, strength=min(0.9, 0.2 + 0.5 * lev + 0.4 * flash + 0.4 * pulse), reach=3.5 + 2 * flash)
        # blossoms at the tips (the payoff)
        if pulse > 0.01:
            bl = smooth((t - T_GROW - 0.25) / 0.8) * (1 - smooth((t - T_GROW - T_BLOOM - T_HOLD) / 0.4))
            for x0, y0, x1, y1, _, _ in LEVELS[-1][::2]:
                q = self.P(x1, y1)
                c.circle(*q, 4.5 * bl, BLOSSOM, alpha=0.85 * bl)
        # HUD
        n_br = 2 ** (k_now + 1) - 1 if (k_now < DEPTH - 1 or pe > 0.99) else 2 ** (DEPTH - 1) - 1
        fs = w * 0.05
        c.text_centered("FAMOUS SHAPES · GOLDEN TREE", h * 0.205, size=h * 0.015, color=GOLD, alpha=0.8)
        c.text_centered(f"{n_br:,} branch" + ("" if n_br == 1 else "es"), h * 0.668, size=fs, color=(1, 1, 1))
        if pulse > 0.01:
            c.text_centered("1/φ + 60° → the halves meet, never cross", h * 0.712, size=fs * 0.62, color=GOLD,
                            alpha=pulse, max_w=w * 0.94)
        else:
            c.text_centered("each branch = 1/φ of the last · 60°", h * 0.712, size=fs * 0.62,
                            color=(0.80, 0.82, 0.92), alpha=0.9, bold=False, max_w=w * 0.94)
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
    walker = audio.ScaleWalker(root_midi=55, scale=audio.PENTA_MAJOR, span=14, pattern="up")
    out = [{"t": 0.02, "note": n, "gain": 0.40, "x": layout.w / 2} for n in (43, 55, 62)]
    for k in range(1, DEPTH):
        out.append({"t": round(STARTS[k] + 0.005, 4), "note": walker.next(), "gain": round(0.36 + 0.14 * k / DEPTH, 3),
                    "x": layout.w / 2})
        if k >= 4:                                                    # the halves close in again
            out.append({"t": round(STARTS[k] + DUR[k], 4), "note": 88, "gain": 0.26, "x": layout.w / 2})
    for j, note in enumerate((43, 50, 55, 59, 62, 67, 71)):
        out.append({"t": round(T_GROW + 0.06 * j, 4), "note": note, "gain": 0.44, "x": layout.w / 2})
    for j, note in enumerate((83, 88, 91, 88)):
        out.append({"t": round(T_GROW + 0.6 + 0.28 * j, 4), "note": note, "gain": 0.20, "x": layout.w / 2})
    tb = T_GROW + T_BLOOM + T_HOLD
    for j, note in enumerate((83, 79, 76, 71, 67, 62)):
        out.append({"t": round(tb + 0.05 + 0.18 * j, 4), "note": note, "gain": 0.22, "x": layout.w / 2})
    shift = T_LOOP - T_A                                   # scene time -> video time
    out = [dict(e, t=round((e["t"] - T_A) % T_LOOP, 4)) for e in out if e["t"] > 0.05]
    out += [{"t": 0.02, "note": n, "gain": 0.42, "x": layout.w / 2} for n in (43, 55, 62, 67)]
    _ = shift
    return sorted(out, key=lambda e: e["t"])


def _worker(o, sim, label, rule):
    layout = get_layout(o)
    name = f"{SCENE}_{label}_{layout.tag}"
    video = studio.OUT_DIR / f"{name}_silent.mp4"
    d = render(layout, sim, video, rule)
    pad = kit.loop_pad(T_LOOP, ((43, 1.0), (50, 0.7), (55, 0.45), (59, 0.3)), gain=0.015)
    kit.deliver_loop(SCENE, name, layout, video, build_events(sim, layout), d, voice="glassharp", bed=pad)


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
    print(f"[{SCENE}] {T_LOOP:.2f}s grow={T_GROW:.2f}s meet at {MEET} gap {MEET_GAP:.5f}")
    kit.fan_out(_worker, (sim, label, rule), SCENE)


if __name__ == "__main__":
    main()
