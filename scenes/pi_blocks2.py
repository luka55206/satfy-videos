"""PI BLOCKS PART 2 — the sequel the pinned comment promised: 100,000,000 kg → 31,415 collisions, then
10,000,000,000 kg → 314,159. (Part 1 = scenes/pi_blocks.py, unchanged.)

HOOK (owner: "more hooker for the first view, use sound and visual"): no slow start — the 100-million-kg block is
already touching the small one on frame 0, so the very first second is a machine-gun of clicks that rises into a buzz
(the click RATE is the pitch you hear), the mass slams in big, a live "collisions per second" meter races.
Exact event-driven simulation as in part 1 (Galperin 2003): every collision is computed. The "why π?" circle: each
collision is a chord turning the velocity dot by θ = arctan(√(m/M)); π/θ chords fit → 314,159 chords fill the disc.
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

SCENE = "pi_blocks2"
CYAN, GOLD, PINK, WHITE = (0.35, 0.85, 1.0), (1.0, 0.8, 0.3), (1.0, 0.45, 0.6), (1, 1, 1)
ROUNDS = [(1e8, 6.6), (1e10, 8.0)]                       # (M in kg, seconds on screen)
S1 = 0.07
X1, X2 = 0.025, 0.097                                    # both start at the wall, touching: clicks from frame 0
DIGITS = "3.14159265"


def simulate_round(M, m=1.0):
    x1, v1, x2, v2 = X1, 0.0, X2, -1.0
    t = 0.0
    T, A1, B1, A2, B2, K = [0.0], [x1], [v1], [x2], [v2], [0]
    while True:
        cand_t, kind = None, None
        if v1 < 0:
            cand_t, kind = -x1 / v1, 0                          # 0 = wall
        if v2 < v1:
            dt_ = (x2 - (x1 + S1)) / (v1 - v2)
            if cand_t is None or dt_ < cand_t:
                cand_t, kind = dt_, 1                           # 1 = block
        if cand_t is None:
            break
        t += cand_t
        x1 += v1 * cand_t
        x2 += v2 * cand_t
        if kind == 0:
            x1, v1 = 0.0, -v1
        else:
            x2 = x1 + S1
            v1, v2 = ((m - M) * v1 + 2 * M * v2) / (m + M), ((M - m) * v2 + 2 * m * v1) / (m + M)
        T.append(t)
        A1.append(x1)
        B1.append(v1)
        A2.append(x2)
        B2.append(v2)
        K.append(kind)
    return dict(t=np.array(T), x1=np.array(A1), v1=np.array(B1), x2=np.array(A2), v2=np.array(B2), k=np.array(K))


SIMS = [simulate_round(M) for M, _ in ROUNDS]
COUNTS = [len(s["t"]) - 1 for s in SIMS]


def time_warp(i):
    """Video seconds in the round → sim time, driven by the COLLISION COUNT: the counter races from frame 0
    (≈7,000 hits per second → a buzz right away), slightly accelerating; all collisions done at 62 % of the round."""
    T = SIMS[i]["t"]
    N = len(T) - 1
    D = ROUNDS[i][1] * 0.62
    ks = np.arange(N + 1)

    def f(u):
        if u >= D:
            return T[-1] + (u - D) * 0.3
        return float(np.interp(N * (u / D) ** 1.2, ks, T))
    return f


WARPS = [time_warp(i) for i in range(len(ROUNDS))]
R_START = np.concatenate([[0.0], np.cumsum([d for _, d in ROUNDS])])
T_LOOP = float(R_START[-1])


def state(i, ts):
    s = SIMS[i]
    k = int(np.searchsorted(s["t"], ts, side="right") - 1)
    d = ts - s["t"][k]
    return s["x1"][k] + s["v1"][k] * d, s["x2"][k] + s["v2"][k] * d, k


def simulate():
    return {"nf": int(round(T_LOOP * FPS))}


class Scene:
    def __init__(self, layout, sim):
        self.L, self.sim = layout, sim
        self.canvas = Canvas(layout.w, layout.h, studio.render_scale())

    def draw(self, f, rule):
        L, c = self.L, self.canvas
        t = f * DT
        self.frame(t)
        k_ = smooth((t - (T_LOOP - 0.5)) / 0.48)                  # cross-fade into frame 0: a seamless loop
        if k_ > 0:
            c.ctx.push_group()
            self.frame(0.0)
            c.ctx.pop_group_to_source()
            c.ctx.paint_with_alpha(k_)
        if rule:
            c.caption(rule, alpha=1.0, layout=L)
        c.watermark(L)

    def frame(self, t):
        L, c = self.L, self.canvas
        w, h = L.w, L.h
        ctx = c.ctx
        ctx.set_source_rgb(0, 0, 0)
        ctx.paint()
        i = min(len(ROUNDS) - 1, int(np.searchsorted(R_START, t, side="right") - 1))
        tr = t - R_START[i]
        M = ROUNDS[i][0]
        ts = WARPS[i](tr)
        x1, x2, k = state(i, ts)
        sim = SIMS[i]
        done = k == COUNTS[i]
        # collisions per (real) second right now
        dt_w = 1 / 30
        k_prev = state(i, WARPS[i](max(0.0, tr - dt_w)))[2]
        rate = (k - k_prev) / dt_w
        buzz = min(1.0, rate / 6000.0)
        # the stage (a slight shake with the buzz)
        sh = buzz * 3.0 * math.sin(t * 173)
        wx, fy, TW = w * 0.08 + sh, h * 0.45, w * 0.86
        c.lines([(wx, h * 0.31, wx, fy)], (0.85, 0.88, 1.0), width=4)
        c.lines([(wx - w * 0.025, h * 0.31 + j * h * 0.012, wx, h * 0.31 + j * h * 0.012 - h * 0.01) for j in range(12)],
                (0.6, 0.65, 0.8), width=1.5, alpha=0.6)
        c.lines([(wx, fy, w * 0.97, fy)], (0.85, 0.88, 1.0), width=3)
        s_small = S1 * TW
        s_big = min(w * 0.42, w * (0.075 + 0.028 * math.log10(M)))
        bx1, bx2 = wx + x1 * TW, wx + x2 * TW
        if bx2 < w * 1.05:
            ctx.rectangle(bx2, fy - s_big, s_big, s_big)
            ctx.set_source_rgb(*GOLD)
            ctx.fill()
            c.text_centered("M", fy - s_big * 0.4, size=s_big * 0.42, color=(0.1, 0.07, 0.0), cx=bx2 + s_big / 2)
        ctx.rectangle(bx1, fy - s_small, s_small, s_small)
        ctx.set_source_rgb(*CYAN)
        ctx.fill()
        c.text_centered("m", fy - s_small * 0.35, size=s_small * 0.55, color=(0.02, 0.05, 0.1), cx=bx1 + s_small / 2)
        if buzz > 0.02 and not done:                              # the small block is a blur of impacts
            c.glow(wx + s_small * 0.6, fy - s_small / 2, w * 0.05, WHITE, strength=0.5 * buzz, reach=2)
        # the mass, slammed in big on each round (the visual hook)
        pop = math.exp(-tr / 0.18)
        c.text_centered(f"M = {M:,.0f} kg", h * 0.215, size=w * 0.06 * (1 + 0.5 * pop), color=GOLD)
        c.text_centered("m = 1 kg  ·  part 2", h * 0.248, size=w * 0.036, color=CYAN, bold=False)
        # the counter + the live rate meter
        c.text_centered("collisions", h * 0.5, size=w * 0.035, color=(0.75, 0.78, 0.9), bold=False, cx=w * 0.3)
        dpop = math.exp(-max(0.0, tr - ROUNDS[i][1] * 0.62) / 0.2) if done else 0.0
        c.text_centered(f"{k:,}", h * 0.565, size=w * 0.11 * (1 + 0.2 * dpop), color=GOLD if done else WHITE, cx=w * 0.3)
        if not done and rate > 0:
            c.text_centered(f"{rate:,.0f} per second", h * 0.605, size=w * 0.034, color=PINK, cx=w * 0.3)
        else:
            nd = len(str(COUNTS[i]))
            c.text_centered(f"π = {DIGITS[:nd + 1]}…", h * 0.61, size=w * 0.05, color=GOLD,
                            alpha=smooth((tr - ROUNDS[i][1] * 0.62) / 0.3), cx=w * 0.3)
        # the why-π circle: last chords + the disc filling up
        cx_, cy_, R = w * 0.72, h * 0.57, h * 0.085
        frac = k / max(1, COUNTS[i])
        ctx.new_path()
        ctx.arc(cx_, cy_, R, 0, 2 * math.pi)
        ctx.set_source_rgba(*PINK, 0.55 * frac)
        ctx.fill_preserve()
        ctx.set_source_rgba(0.6, 0.65, 0.85, 0.6)
        ctx.set_line_width(1.5)
        ctx.stroke()
        sM = math.sqrt(M)
        a0 = max(0, k - 400)
        if k - a0 >= 1:
            V = sim["v2"][a0:k + 1]
            v = sim["v1"][a0:k + 1]
            pts = list(zip(cx_ + R * V, cy_ - R * v / sM))
            c.polylines([pts], (1, 0.75, 0.85), width=1.0, alpha=0.8)
        c.circle(cx_ + R * sim["v2"][k], cy_ - R * sim["v1"][k] / sM, w * 0.009, WHITE)
        th = math.degrees(math.atan(math.sqrt(1 / M)))
        c.text_centered("each bounce turns the dot by", h * 0.68, size=w * 0.028, color=(0.8, 0.82, 0.92), bold=False, cx=cx_)
        c.text_centered(f"θ = {th:.3g}°", h * 0.705, size=w * 0.03, color=(0.9, 0.9, 1.0), cx=cx_)
        head = "100,000,000× heavier" if i == 0 else "10,000,000,000× heavier"
        c.text_centered(f"{head}: {COUNTS[i]:,}" if done else f"{head}: how many?", h * 0.765, size=w * 0.046, color=WHITE)
        c.text_centered("×100 mass → one more digit of π", h * 0.80, size=w * 0.036, color=GOLD, bold=False)


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
    if writer is not None:
        writer.close()
    return sim["nf"] / FPS


def track():
    """Clicks as an impulse train (the rate becomes the pitch of the buzz), a chime per final count, a pad."""
    sr = audio.SR
    n = int(round(T_LOOP * sr))
    out = np.zeros(n)
    for i in range(len(ROUNDS)):
        T_last = SIMS[i]["t"][-1]
        D = ROUNDS[i][1] * 0.62
        u = D * (np.arange(1, len(SIMS[i]["t"])) / (len(SIMS[i]["t"]) - 1)) ** (1 / 1.2)   # collision k → video s
        vt = R_START[i] + u
        kinds = SIMS[i]["k"][1:]
        idx = np.clip((vt * sr).astype(int), 0, n - 1)
        dens = np.bincount(idx // int(sr * 0.05), minlength=n // int(sr * 0.05) + 1)
        g = 0.30 / np.sqrt(np.maximum(1.0, dens[idx // int(sr * 0.05)] / 4.0))
        for kind, f0 in ((0, 1700.0), (1, 2600.0)):
            train = np.zeros(n)
            sel = kinds == kind
            np.add.at(train, idx[sel], g[sel])
            tv = np.arange(int(0.012 * sr)) / sr
            kern = np.sin(2 * np.pi * f0 * tv) * np.exp(-tv / 0.0025)
            out += np.convolve(train, kern)[:n]
        tc = R_START[i] + D + 0.05
        tvc = np.arange(int(1.2 * sr)) / sr
        ch = sum(np.sin(2 * np.pi * 440 * 2 ** ((mm - 69) / 12) * tvc) for mm in (79 + 2 * i, 84 + 2 * i, 88 + 2 * i))
        ch *= np.exp(-tvc / 0.4) / 3
        i0 = int(tc * sr)
        out[i0:i0 + len(ch)] += 0.12 * ch[: max(0, n - i0)]
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
        print("counts", COUNTS, f"T={T_LOOP:.1f}s")
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
