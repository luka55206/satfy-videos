"""PI BLOCKS — two blocks, a wall, no friction: the number of collisions spells π (3, 31, 314, 3141).

Owner-supplied brief (2026-10-18) after a reference video; the result itself is public mathematics (G. Galperin,
"Playing pool with π", 2003). Ours: the presentation, colours, sound, words, and the IMPROVEMENT — a "why" panel: the
velocities live on a circle (√M·V, √m·v); every collision is a chord that turns the dot by the same angle
θ = arctan(√(m/M)), so about π/θ chords fit → with M = 100ⁿ·m that is the first n+1 digits of π.
Exact event-driven simulation (elastic, frictionless): every collision is computed, nothing is faked.
Rounds: M = 1, 100, 10 000, 1 000 000 kg (m = 1 kg) → 3, 31, 314, 3141 collisions.
Audio (original): a click per collision (wall / block pitched differently; dense runs merge into a buzz), a soft
chime when a round's count is final, a quiet pad.
"""
import bisect
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

SCENE = "pi_blocks"
CYAN, GOLD, PINK, WHITE = (0.35, 0.85, 1.0), (1.0, 0.8, 0.3), (1.0, 0.45, 0.6), (1, 1, 1)
ROUNDS = [(1.0, 2.8), (100.0, 3.2), (1e4, 3.9), (1e6, 5.1)]          # (M in kg, seconds on screen)
S1 = 0.07                                                          # small block size (track units)
X1, X2 = 0.30, 0.55                                                # start: small block, big block (left edges)


def simulate_round(M, m=1.0):
    """Exact elastic collisions. Returns events [(t, x1, v1, x2, v2, kind)] AFTER each collision, + the start."""
    x1, v1, x2, v2 = X1, 0.0, X2, -1.0
    t = 0.0
    ev = [(0.0, x1, v1, x2, v2, "start")]
    for _ in range(100000):
        cand = []
        if v1 < 0:
            cand.append((-x1 / v1, "wall"))                       # small block reaches the wall
        if v2 < v1:
            gap = x2 - (x1 + S1)
            cand.append((gap / (v1 - v2), "block"))
        if not cand:
            break
        dt_, kind = min(cand)
        t += dt_
        x1 += v1 * dt_
        x2 += v2 * dt_
        if kind == "wall":
            x1, v1 = 0.0, -v1
        else:
            x2 = x1 + S1
            v1n = ((m - M) * v1 + 2 * M * v2) / (m + M)
            v2n = ((M - m) * v2 + 2 * m * v1) / (m + M)
            v1, v2 = v1n, v2n
        ev.append((t, x1, v1, x2, v2, kind))
    return ev


SIMS = [simulate_round(M) for M, _ in ROUNDS]
COUNTS = [len(s) - 1 for s in SIMS]


def round_speed(i):
    """Track units per second so the round's collisions finish ~0.75 of the way through its screen time."""
    t_last = SIMS[i][-1][0]                                       # in sim time units (v0 = 1)
    return max(t_last / (ROUNDS[i][1] * 0.62), 0.25)


SPEED = [round_speed(i) for i in range(len(ROUNDS))]
R_START = np.concatenate([[0.0], np.cumsum([d for _, d in ROUNDS])])
T_LOOP = float(R_START[-1])


def state(i, ts):
    """Block positions/velocities and the collision count at sim time ts in round i."""
    ev = SIMS[i]
    times = [e[0] for e in ev]
    k = bisect.bisect_right(times, ts) - 1
    t0, x1, v1, x2, v2, _ = ev[k]
    d = ts - t0
    return x1 + v1 * d, x2 + v2 * d, k, v1, v2


def simulate():
    return {"nf": int(round(T_LOOP * FPS))}


class Scene:
    def __init__(self, layout, sim):
        self.L, self.sim = layout, sim
        self.canvas = Canvas(layout.w, layout.h, studio.render_scale())

    def draw(self, f, rule):
        L, c = self.L, self.canvas
        w, h = L.w, L.h
        t = f * DT
        ctx = c.ctx
        ctx.set_source_rgb(0, 0, 0)
        ctx.paint()
        i = min(len(ROUNDS) - 1, int(np.searchsorted(R_START, t, side="right") - 1))
        tr = t - R_START[i]
        M = ROUNDS[i][0]
        ts = max(0.0, tr - 0.35) * SPEED[i]                         # a short beat before the push
        x1, x2, k, v1, v2 = state(i, ts)
        # the stage: wall + floor
        wx, fy, TW = w * 0.08, h * 0.45, w * 0.86                   # wall x, floor y, track width (1 unit)
        c.lines([(wx, h * 0.31, wx, fy)], (0.85, 0.88, 1.0), width=4)
        hatch = [(wx - w * 0.025, h * 0.31 + j * h * 0.012, wx, h * 0.31 + j * h * 0.012 - h * 0.01) for j in range(12)]
        c.lines(hatch, (0.6, 0.65, 0.8), width=1.5, alpha=0.6)
        c.lines([(wx, fy, w * 0.97, fy)], (0.85, 0.88, 1.0), width=3)
        c.text_centered("frictionless", fy + h * 0.02, size=w * 0.024, color=(0.6, 0.65, 0.8), bold=False, cx=w * 0.82)
        s_small = S1 * TW
        s_big = w * (0.075 + 0.028 * math.log10(M) / 1.0) if M > 1 else s_small
        bx1 = wx + x1 * TW
        bx2 = wx + x2 * TW
        ctx.rectangle(bx1, fy - s_small, s_small, s_small)
        ctx.set_source_rgb(*CYAN)
        ctx.fill()
        c.text_centered("m", fy - s_small * 0.35, size=s_small * 0.55, color=(0.02, 0.05, 0.1), cx=bx1 + s_small / 2)
        if bx2 < w * 1.05:
            ctx.rectangle(bx2, fy - s_big, s_big, s_big)
            ctx.set_source_rgb(*GOLD)
            ctx.fill()
            c.text_centered("M", fy - s_big * 0.38, size=s_big * 0.45, color=(0.1, 0.07, 0.0), cx=bx2 + s_big / 2)
        # flash on the latest collision
        ev = SIMS[i]
        if k >= 1:
            age = (ts - ev[k][0]) / SPEED[i]
            if age < 0.12:
                xx = wx if ev[k][5] == "wall" else bx1 + s_small
                c.glow(xx, fy - s_small / 2, w * 0.03, WHITE, strength=0.7 * (1 - age / 0.12), reach=2)
        # headline: the masses
        c.text_centered(f"M = {M:,.0f} kg", h * 0.215, size=w * 0.065, color=GOLD)
        c.text_centered("m = 1 kg", h * 0.25, size=w * 0.04, color=CYAN, bold=False)
        # the counter
        c.text_centered("collisions", h * 0.505, size=w * 0.035, color=(0.75, 0.78, 0.9), bold=False, cx=w * 0.28)
        done = k == COUNTS[i]
        pop = math.exp(-max(0.0, (ts - ev[-1][0]) / SPEED[i]) / 0.2) if done else 0.0
        c.text_centered(f"{k:,}", h * 0.575, size=w * 0.13 * (1 + 0.2 * pop), color=WHITE if not done else GOLD, cx=w * 0.28)
        digits = "3.141592653"
        n_dig = i + 1
        if done:
            c.text_centered(f"π = {digits[:n_dig + (1 if n_dig > 1 else 0)]}…", h * 0.625, size=w * 0.05, color=GOLD,
                            alpha=smooth((ts - ev[-1][0]) / SPEED[i] / 0.3), cx=w * 0.28)
        # the "why" panel: velocities on a circle, every collision a chord
        cx_, cy_, R = w * 0.70, h * 0.575, h * 0.085
        ctx.new_path()
        ctx.arc(cx_, cy_, R, 0, 2 * math.pi)
        ctx.set_source_rgba(0.6, 0.65, 0.85, 0.5)
        ctx.set_line_width(1.5)
        ctx.stroke()
        c.lines([(cx_ - R * 1.15, cy_, cx_ + R * 1.15, cy_), (cx_, cy_ - R * 1.15, cx_, cy_ + R * 1.15)],
                (0.5, 0.55, 0.75), width=1, alpha=0.5)
        sM, sm = math.sqrt(M), 1.0

        def P(V, v):
            return cx_ + R * sM * V / sM, cy_ - R * sm * v / sM      # normalised: |(√M V, √m v)| = √M·1

        pts = [P(e[4], e[2]) for e in ev[:k + 1]]
        cur = P(v2, v1)
        if len(pts) > 1:
            c.polylines([pts + [cur]], PINK, width=1.6 if i < 3 else 0.9, alpha=0.85 if i < 2 else 0.55)
        c.circle(cur[0], cur[1], w * 0.009, WHITE)
        th = math.degrees(math.atan(math.sqrt(1 / M)))
        c.text_centered("why π?  each bounce turns", h * 0.68, size=w * 0.028, color=(0.8, 0.82, 0.92), bold=False, cx=cx_)
        c.text_centered(f"the dot by θ = {th:.3g}°", h * 0.705, size=w * 0.028, color=(0.8, 0.82, 0.92), bold=False,
                        cx=cx_)
        # the rule
        head = ["equal masses", "100× heavier", "10,000× heavier", "1,000,000× heavier"][i]
        l1 = f"{head}: {COUNTS[i]:,} collisions" if done else f"{head}: how many collisions?"
        c.text_centered(l1, h * 0.765, size=w * 0.05, color=WHITE)
        c.text_centered("×100 mass → one more digit of π", h * 0.80, size=w * 0.036, color=GOLD, bold=False)
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


def track():
    sr = audio.SR
    n = int(round(T_LOOP * sr))
    out = np.zeros(n)
    rng = np.random.default_rng(1)
    tv = np.arange(int(0.012 * sr)) / sr
    for i, ev in enumerate(SIMS):
        times = np.array([R_START[i] + 0.35 + e[0] / SPEED[i] for e in ev[1:]])
        kinds = [e[5] for e in ev[1:]]
        for j, (t0, kd) in enumerate(zip(times, kinds)):
            lo, hi = np.searchsorted(times, [t0 - 0.05, t0 + 0.05])
            dens = (hi - lo) / 0.1                                  # clicks per second around this one
            g = 0.28 / math.sqrt(max(1.0, dens / 15.0))
            f0 = 2600 if kd == "block" else 1700
            sig = np.sin(2 * np.pi * f0 * tv) * np.exp(-tv / 0.0025) + 0.4 * rng.standard_normal(len(tv)) * np.exp(-tv / 0.001)
            i0 = int(t0 * sr)
            if i0 + len(sig) < n:
                out[i0:i0 + len(sig)] += g * sig
        tc = R_START[i] + 0.35 + ev[-1][0] / SPEED[i] + 0.05      # the chime: the count is final
        tvc = np.arange(int(1.0 * sr)) / sr
        ch = sum(np.sin(2 * np.pi * 440 * 2 ** ((mm - 69) / 12) * tvc) for mm in (76 + 2 * i, 81 + 2 * i, 84 + 2 * i))
        ch *= np.exp(-tvc / 0.35) / 3
        i0 = int(tc * sr)
        out[i0:i0 + len(ch)] += 0.10 * ch[: max(0, n - i0)]
    pad = kit.loop_pad(T_LOOP, ((45, 1.0), (52, 0.6), (57, 0.4)), gain=0.010)
    return (out + pad[:n]).astype(np.float32)


def _worker(o, sim, label, rule):
    layout = get_layout(o)
    name = f"{SCENE}_{label}_{layout.tag}"
    video = studio.OUT_DIR / f"{name}_silent.mp4"
    d = render(layout, sim, video, rule)
    kit.deliver_loop(SCENE, name, layout, video, [], d, voice="piano", bed=track(), peak_db=-6.0)


def main():
    label, rule = arg("--label", "v1"), arg("--rule", "")
    studio.OUT_DIR.mkdir(exist_ok=True)
    sim = simulate()
    if kit.has("--info"):
        print("counts", COUNTS, "speeds", [round(s, 3) for s in SPEED], f"T={T_LOOP:.1f}s")
        return
    if kit.has("--still"):
        layout = get_layout(kit.orients()[0])
        f = int(arg("--frame", "0"))
        png = studio.OUT_DIR / f"{SCENE}_{label}_f{f}_{layout.tag}.png"
        render(layout, sim, png, rule, still_frame=f)
        print(f"[{SCENE}] -> {png}")
        return
    print(f"[{SCENE}] {T_LOOP:.1f}s  collisions {COUNTS}")
    kit.fan_out(_worker, (sim, label, rule), SCENE)


if __name__ == "__main__":
    main()
