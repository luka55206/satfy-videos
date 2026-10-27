"""PI BLOCKS — NEXT GENERATION: 4 rounds (100 kg → 100,000,000 kg: 31 → 31,415 collisions) and you SEE the process.

Owner (2026-10-20): keep the blocks, pure math, more weights, show how they bang many times and change direction.
Every collision flips the small block's velocity arrow; the live velocity graph under the stage shows the small
block's velocity zig-zagging + / − with every bang while the big block's velocity sinks through ZERO — at that
moment "M stops… and turns back!" — then both drift right until the small one can no longer catch up. The count
spells π: 31, 314, 3,141, 31,415 (Galperin 2003; exact event-driven simulation, every collision computed).
Round 1 runs in real (simulation) time, every hit a clear click; rounds 2-4 follow the collision count (a rush, then
a buzz). Cross-fades into frame 0 (seamless loop).
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

SCENE = "pi_blocks3"
CYAN, GOLD, PINK, WHITE, LIME = (0.35, 0.85, 1.0), (1.0, 0.8, 0.3), (1.0, 0.45, 0.6), (1, 1, 1), (0.55, 1.0, 0.55)
ROUNDS = [(1e2, 3.4), (1e4, 3.6), (1e6, 3.9), (1e8, 4.5)]          # (M kg, seconds on screen); m = 1 kg
S1 = 0.065
LEAD = 0.2
DONE_AT = 0.66


def simulate_round(M, m=1.0):
    x1, v1, x2, v2 = 0.2, 0.0, 0.2 + S1 + 0.03, -1.0
    t = 0.0
    T, A1, B1, A2, B2, K = [0.0], [x1], [v1], [x2], [v2], [0]
    while True:
        ct, kind = None, None
        if v1 < 0:
            ct, kind = -x1 / v1, 0
        if v2 < v1:
            d = (x2 - (x1 + S1)) / (v1 - v2)
            if ct is None or d < ct:
                ct, kind = d, 1
        if ct is None:
            break
        t += ct
        x1 += v1 * ct
        x2 += v2 * ct
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
    s = dict(t=np.array(T), x1=np.array(A1), v1=np.array(B1), x2=np.array(A2), v2=np.array(B2), k=np.array(K))
    s["kz"] = int(np.argmax(s["v2"] >= 0))                              # the turnaround: M's velocity crosses 0
    s["vmax"] = float(np.max(np.abs(s["v1"])))
    return s


SIMS = [simulate_round(M) for M, _ in ROUNDS]
COUNTS = [len(s["t"]) - 1 for s in SIMS]
R_START = np.concatenate([[0.0], np.cumsum([d for _, d in ROUNDS])])
T_LOOP = float(R_START[-1])


def k_of_u(i, u):
    """Fractional collision index at video seconds u into round i."""
    s = SIMS[i]
    N = COUNTS[i]
    D = ROUNDS[i][1] * DONE_AT
    if u <= LEAD:
        return u / LEAD
    if u >= D:
        return float(N)
    q = (u - LEAD) / (D - LEAD)
    if i == 0:                                                         # real sim time: every bang readable
        ts = s["t"][1] + (s["t"][-1] - s["t"][1]) * q
        return float(np.interp(ts, s["t"], np.arange(N + 1)))
    return 1 + (N - 1) * q ** 1.25


def sim_time(i, u):
    s = SIMS[i]
    N = COUNTS[i]
    D = ROUNDS[i][1] * DONE_AT
    if u >= D:
        return s["t"][-1] + (u - D) * 0.5
    return float(np.interp(k_of_u(i, u), np.arange(N + 1), s["t"]))


def hit_video_times(i):
    N = COUNTS[i]
    D = ROUNDS[i][1] * DONE_AT
    s = SIMS[i]
    ks = np.arange(1, N + 1)
    if i == 0:
        q = (s["t"][1:] - s["t"][1]) / (s["t"][-1] - s["t"][1])
    else:
        q = ((ks - 1) / (N - 1)) ** (1 / 1.25)
    return R_START[i] + LEAD + q * (D - LEAD)


def state(i, ts):
    s = SIMS[i]
    k = int(np.searchsorted(s["t"], ts, side="right") - 1)
    d = ts - s["t"][k]
    return s["x1"][k] + s["v1"][k] * d, s["x2"][k] + s["v2"][k] * d, k


def simulate():
    return {"nf": int(round(T_LOOP * FPS))}


def arrow(c, x, y, length, col, width):
    if abs(length) < 3:
        return
    sgn = 1 if length > 0 else -1
    x1 = x + length
    c.lines([(x, y, x1, y)], col, width=width * 3, alpha=0.2)
    c.lines([(x, y, x1 - sgn * width * 1.6, y)], col, width=width)
    c.poly([(x1, y), (x1 - sgn * width * 2.6, y - width * 1.6), (x1 - sgn * width * 2.6, y + width * 1.6)], col)


class Scene:
    def __init__(self, layout, sim):
        self.L, self.sim = layout, sim
        self.canvas = Canvas(layout.w, layout.h, studio.render_scale())

    def frame(self, t):
        L, c = self.L, self.canvas
        w, h = L.w, L.h
        ctx = c.ctx
        ctx.set_source_rgb(0, 0, 0)
        ctx.paint()
        i = min(len(ROUNDS) - 1, int(np.searchsorted(R_START, t, side="right") - 1))
        tr = t - R_START[i]
        M = ROUNDS[i][0]
        s = SIMS[i]
        N = COUNTS[i]
        ts = sim_time(i, tr)
        x1, x2, k = state(i, ts)
        done = k == N
        # ---- the stage
        wx, gy, TW = w * 0.07, h * 0.43, w * 0.9
        c.lines([(wx, h * 0.29, wx, gy)], (0.85, 0.88, 1.0), width=4)
        c.lines([(wx - w * 0.025, h * 0.29 + j * h * 0.012, wx, h * 0.29 + j * h * 0.012 - h * 0.01) for j in range(12)],
                (0.6, 0.65, 0.8), width=1.5, alpha=0.6)
        c.lines([(wx, gy, w * 0.98, gy)], (0.85, 0.88, 1.0), width=3)
        sb = min(h * 0.12, w * (0.07 + 0.033 * math.log10(M)))
        s1 = S1 * TW
        bx1, bx2 = wx + x1 * TW, wx + x2 * TW
        if bx2 < w * 1.02:
            ctx.rectangle(bx2, gy - sb, sb, sb)
            ctx.set_source_rgb(*GOLD)
            ctx.fill()
            c.text_centered("M", gy - sb * 0.38, size=sb * 0.42, color=(0.12, 0.08, 0.0), cx=bx2 + sb / 2)
        ctx.rectangle(bx1, gy - s1, s1, s1)
        ctx.set_source_rgb(*CYAN)
        ctx.fill()
        c.text_centered("m", gy - s1 * 0.33, size=s1 * 0.55, color=(0.02, 0.05, 0.1), cx=bx1 + s1 / 2)
        # flash on the latest bang (round 1: every hit visible)
        hv = hit_video_times(i)
        if k >= 1 and not done:
            age = tr + R_START[i] - hv[k - 1]
            if age < 0.15:
                hx = wx if s["k"][k] == 0 else bx1 + s1
                c.glow(hx, gy - s1 / 2, w * 0.045, WHITE, strength=0.8 * (1 - age / 0.15), reach=2)
        # ---- velocity arrows (direction flips on every bang)
        v1, v2 = s["v1"][k], s["v2"][k]
        L1 = math.copysign(w * 0.15 * math.log10(1 + 9 * abs(v1) / s["vmax"]), v1) if v1 else 0.0
        L2 = math.copysign(w * 0.15 * abs(v2), v2) if v2 else 0.0
        arrow(c, bx1 + s1 / 2, gy - s1 - h * 0.025, L1, CYAN, max(3.0, w * 0.006))
        if bx2 < w * 1.0:
            arrow(c, bx2 + sb / 2, gy - sb - h * 0.025, L2, GOLD, max(3.0, w * 0.007))
        # ---- titles
        pop = math.exp(-tr / 0.18)
        c.text_centered(f"M = {M:,.0f} kg", h * 0.215, size=w * 0.065 * (1 + 0.35 * pop), color=GOLD)
        c.text_centered("m = 1 kg  ·  no friction  ·  a wall", h * 0.25, size=w * 0.032, color=CYAN, bold=False)
        # ---- the counter
        dp = math.exp(-max(0.0, tr - ROUNDS[i][1] * DONE_AT) / 0.2) if done else 0.0
        c.text_centered(f"{k:,}", h * 0.515, size=w * 0.12 * (1 + 0.2 * dp), color=GOLD if done else WHITE)
        if done:
            nd = len(str(N))
            c.text_centered(f"collisions  →  π = {'3.14159265'[:nd + 1]}…", h * 0.552, size=w * 0.042, color=GOLD,
                            alpha=smooth((tr - ROUNDS[i][1] * DONE_AT) / 0.3))
        else:
            c.text_centered("collisions", h * 0.552, size=w * 0.038, color=(0.75, 0.78, 0.9), bold=False)
        # ---- the live velocity graph: x = collision number, y = velocity
        gx0, gx1, gyc, gh = w * 0.08, w * 0.92, h * 0.655, h * 0.06
        c.lines([(gx0, gyc, gx1, gyc)], (0.7, 0.72, 0.85), width=1.5, alpha=0.6)
        c.text_centered("+ →", gyc - gh - h * 0.004, size=w * 0.026, color=(0.7, 0.72, 0.85), bold=False, cx=gx0 - w * 0.02)
        c.text_centered("− ←", gyc + gh + h * 0.016, size=w * 0.026, color=(0.7, 0.72, 0.85), bold=False, cx=gx0 - w * 0.02)
        kk = min(k, N)
        nsmp = min(kk, 700)
        if nsmp >= 1:
            idx = np.unique(np.linspace(0, kk, nsmp + 1).astype(int))
            xs = gx0 + (gx1 - gx0) * idx / max(1, N)
            y1 = s["v1"][idx] / s["vmax"]
            if N <= 400:                                                      # every bang as a bar: + − + −
                segs = [(x, gyc, x, gyc - gh * yy) for x, yy in zip(xs, y1)]
                c.lines(segs, CYAN, width=max(1.5, (gx1 - gx0) / max(60, nsmp) * 0.6), alpha=0.75)
            else:                                                             # too many to draw: the ± band they fill
                env = np.abs(y1)
                top = [(x, gyc - gh * e) for x, e in zip(xs, env)]
                bot = [(x, gyc + gh * e) for x, e in zip(xs, env)][::-1]
                c.poly(top + bot, CYAN, alpha=0.45)
                c.polylines([top, bot[::-1]], CYAN, width=2, alpha=0.9)
            pts = [(x, gyc - gh * v) for x, v in zip(xs, s["v2"][idx])]       # M slows down through zero
            if len(pts) > 1:
                c.polylines([pts], GOLD, width=10, alpha=0.2)
                c.polylines([pts], GOLD, width=3.5, alpha=1.0)
        c.text_centered("velocity of m", gyc + gh + h * 0.035, size=w * 0.03, color=CYAN, bold=False, cx=w * 0.3)
        c.text_centered("velocity of M", gyc + gh + h * 0.035, size=w * 0.03, color=GOLD, bold=False, cx=w * 0.72)
        # ---- the turnaround callout
        kz = s["kz"]
        if k >= kz:
            xz = gx0 + (gx1 - gx0) * kz / max(1, N)
            c.circle(xz, gyc, w * 0.012, WHITE)
            c.glow(xz, gyc, w * 0.03, WHITE, strength=0.6, reach=2)
        tz = hv[kz - 1] - R_START[i] if kz >= 1 else 99
        if tz <= tr < tz + 1.1 and not done:
            a = smooth((tr - tz) / 0.15) * (1 - smooth((tr - tz - 0.85) / 0.25))
            c.text_centered("M stops… and turns back!", h * 0.795, size=w * 0.05, color=LIME, alpha=a)
        else:
            c.text_centered("×100 mass → one more digit of π", h * 0.795, size=w * 0.04, color=GOLD, bold=False)

    def draw(self, f, rule):
        c, L = self.canvas, self.L
        t = f * DT
        self.frame(t)
        k_ = smooth((t - (T_LOOP - 0.45)) / 0.43)
        if k_ > 0:
            c.ctx.push_group()
            self.frame(0.0)
            c.ctx.pop_group_to_source()
            c.ctx.paint_with_alpha(k_)
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
    if writer is not None:
        writer.close()
    return sim["nf"] / FPS


def track():
    sr = audio.SR
    n = int(round(T_LOOP * sr))
    out = np.zeros(n)
    for i in range(len(ROUNDS)):
        times = hit_video_times(i)
        kinds = SIMS[i]["k"][1:]
        idx = np.clip((times * sr).astype(int), 0, n - 1)
        bins = int(sr * 0.05)
        dens = np.bincount(idx // bins, minlength=n // bins + 1)
        g = 0.32 / np.sqrt(np.maximum(1.0, dens[idx // bins] / 3.0))
        for kind, f0 in ((0, 1500.0), (1, 2400.0)):                        # wall / block: two pitches
            train = np.zeros(n)
            sel = kinds == kind
            np.add.at(train, idx[sel], g[sel])
            tv = np.arange(int(0.03 * sr)) / sr
            kern = np.sin(2 * np.pi * f0 * tv) * np.exp(-tv / (0.006 if i == 0 else 0.0025))
            out += np.convolve(train, kern)[:n]
        kz = SIMS[i]["kz"]                                                  # the turnaround: a soft low "whomp"
        if kz >= 1:
            tz = times[kz - 1]
            tv = np.arange(int(0.5 * sr)) / sr
            wh = np.sin(2 * np.pi * np.cumsum(220 * np.exp(-tv / 0.15) + 60) / sr) * np.sin(np.pi * tv / 0.5)
            i0 = int(tz * sr)
            out[i0:i0 + len(wh)] += 0.12 * wh[: max(0, n - i0)]
        tc = R_START[i] + ROUNDS[i][1] * DONE_AT + 0.05                    # the count is final: a chime
        tvc = np.arange(int(1.1 * sr)) / sr
        ch = sum(np.sin(2 * np.pi * 440 * 2 ** ((mm - 69) / 12) * tvc) for mm in (76 + 2 * i, 81 + 2 * i, 84 + 2 * i))
        ch *= np.exp(-tvc / 0.4) / 3
        i0 = int(tc * sr)
        out[i0:i0 + len(ch)] += 0.12 * ch[: max(0, n - i0)]
    out = 0.22 * np.tanh(out / 0.22)                                   # soft-limit the click transients (no clipping)
    pad = kit.loop_pad(T_LOOP, ((45, 1.0), (52, 0.6), (57, 0.4), (64, 0.25)), gain=0.035)
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
        print("counts", COUNTS, "turnaround at", [s["kz"] for s in SIMS], f"T={T_LOOP:.1f}s")
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
