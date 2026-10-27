"""PI ANIMALS — "A mouse, a cat and a truck": the colliding-blocks π trick (Galperin 2003) with real objects.

Owner (2026-10-20): the blocks part 2 was bad; take the idea, new masses, new video. The mass ratios are real-world
and exactly 100^n, so the hit counts still spell π:
  mouse 30 g vs cat 3 kg (×100) → 31 · cat 3 kg vs truck 30 t (×10,000) → 314 · mouse 30 g vs truck 30 t (×10^6) → 3,141
Every collision plays a NOTE (a rising pentatonic run — round 1 is a little melody, round 2 a glassy rush, round 3 a
buzz); wall hits are a lower note. Cute drawn objects, a neon floor, impact sparks, a "how many?" question until the
count is final, then the π digits. Exact event-driven simulation; cross-fade into frame 0 (seamless loop).
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

SCENE = "pi_animals"
GOLD, CYAN, PINK, WHITE = (1.0, 0.8, 0.3), (0.35, 0.85, 1.0), (1.0, 0.45, 0.6), (1, 1, 1)
# (small, big, small kg, big kg, seconds on screen)
ROUNDS = [("mouse", "cat", 0.03, 3.0, 4.6), ("cat", "truck", 3.0, 30000.0, 5.0), ("mouse", "truck", 0.03, 30000.0, 5.6)]
SIZE = {"mouse": 0.11, "cat": 0.22, "truck": 0.44}             # object widths (track units)
LABEL = {"mouse": "mouse 30 g", "cat": "cat 3 kg", "truck": "truck 30 t"}


def simulate_round(m, M, s1):
    x1, v1, x2, v2 = 0.22, 0.0, 0.22 + s1 + 0.04, -1.0
    t = 0.0
    T, A1, B1, A2, B2, K = [0.0], [x1], [v1], [x2], [v2], [0]
    while True:
        ct, kind = None, None
        if v1 < 0:
            ct, kind = -x1 / v1, 0
        if v2 < v1:
            d = (x2 - (x1 + s1)) / (v1 - v2)
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
            x2 = x1 + s1
            v1, v2 = ((m - M) * v1 + 2 * M * v2) / (m + M), ((M - m) * v2 + 2 * m * v1) / (m + M)
        T.append(t)
        A1.append(x1)
        B1.append(v1)
        A2.append(x2)
        B2.append(v2)
        K.append(kind)
    return dict(t=np.array(T), x1=np.array(A1), v1=np.array(B1), x2=np.array(A2), v2=np.array(B2), k=np.array(K))


SIMS = [simulate_round(r[2], r[3], SIZE[r[0]]) for r in ROUNDS]
COUNTS = [len(s["t"]) - 1 for s in SIMS]
R_START = np.concatenate([[0.0], np.cumsum([r[4] for r in ROUNDS])])
T_LOOP = float(R_START[-1])
LEAD = 0.25                                                   # a beat of motion before the first hit


def warp(i, u):
    """Video seconds in round i → sim time: round 1 runs in real sim time (each hit audible), rounds 2-3 follow the
    collision count so the run accelerates into a rush; everything done at 65 % of the round."""
    s = SIMS[i]
    D = ROUNDS[i][4] * 0.65
    if u <= LEAD:
        return s["t"][1] * u / LEAD
    if u >= D:
        return s["t"][-1] + (u - D) * 0.6
    q = (u - LEAD) / (D - LEAD)
    if i == 0:
        return s["t"][1] + (s["t"][-1] - s["t"][1]) * q
    N = len(s["t"]) - 1
    return float(np.interp(1 + (N - 1) * q ** 1.3, np.arange(N + 1), s["t"]))


def hit_times(i):
    s = SIMS[i]
    D = ROUNDS[i][4] * 0.65
    N = len(s["t"]) - 1
    if i == 0:
        q = (s["t"][1:] - s["t"][1]) / (s["t"][-1] - s["t"][1])
    else:
        q = ((np.arange(1, N + 1) - 1) / (N - 1)) ** (1 / 1.3)
    return R_START[i] + LEAD + q * (D - LEAD)


def state(i, ts):
    s = SIMS[i]
    k = int(np.searchsorted(s["t"], ts, side="right") - 1)
    d = ts - s["t"][k]
    return s["x1"][k] + s["v1"][k] * d, s["x2"][k] + s["v2"][k] * d, k


def simulate():
    return {"nf": int(round(T_LOOP * FPS))}


# ---------------------------------------------------------------- the objects
def draw_obj(c, kind, x0, gy, wpx, t, face=1, squash=0.0):
    ctx = c.ctx
    hgt = wpx * (0.62 if kind == "mouse" else (0.75 if kind == "cat" else 0.55))
    x1 = x0 + wpx
    if kind == "mouse":
        g = (0.72, 0.74, 0.8)
        ctx.save()
        ctx.translate(x0 + wpx * 0.5, gy - hgt * 0.42)
        ctx.scale(1.0 - 0.15 * squash, 1.0 + 0.1 * squash)
        ctx.arc(0, 0, wpx * 0.5, 0, 2 * math.pi)
        ctx.restore()
        ctx.set_source_rgb(*g)
        ctx.fill()
        c.circle(x1 - wpx * 0.08, gy - hgt * 0.62, wpx * 0.2, g)                      # head
        c.circle(x1 - wpx * 0.18, gy - hgt * 0.95, wpx * 0.17, (0.95, 0.7, 0.75))    # ear
        c.circle(x1 + wpx * 0.03, gy - hgt * 0.68, wpx * 0.05, (0.05, 0.05, 0.08))   # eye
        c.circle(x1 + wpx * 0.12, gy - hgt * 0.55, wpx * 0.05, (1, 0.5, 0.6))        # nose
        tail = [(x0 + wpx * 0.05 - wpx * 0.5 * u, gy - hgt * 0.3 - wpx * 0.25 * math.sin(u * 5 + t * 6)) for u in np.linspace(0, 1, 10)]
        c.polylines([tail], (0.95, 0.7, 0.75), width=max(2.0, wpx * 0.06))
    elif kind == "cat":
        o = (1.0, 0.62, 0.25)
        ctx.save()
        ctx.translate(x0 + wpx * 0.45, gy - hgt * 0.4)
        ctx.scale(1.0, 0.62)
        ctx.arc(0, 0, wpx * 0.45, 0, 2 * math.pi)
        ctx.restore()
        ctx.set_source_rgb(*o)
        ctx.fill()
        for k in range(3):                                                         # stripes
            c.lines([(x0 + wpx * (0.25 + 0.15 * k), gy - hgt * 0.6, x0 + wpx * (0.3 + 0.15 * k), gy - hgt * 0.3)],
                    (0.8, 0.42, 0.12), width=max(2.0, wpx * 0.04))
        hx, hy = x1 - wpx * 0.12, gy - hgt * 0.72
        c.circle(hx, hy, wpx * 0.2, o)
        for dx in (-0.14, 0.08):
            c.poly([(hx + wpx * dx, hy - wpx * 0.12), (hx + wpx * (dx + 0.06), hy - wpx * 0.32), (hx + wpx * (dx + 0.12), hy - wpx * 0.12)], o)
        for dx in (-0.06, 0.08):
            c.circle(hx + wpx * dx, hy - wpx * 0.02, wpx * 0.035, (0.1, 0.3, 0.1))
        c.lines([(hx + wpx * 0.1, hy + wpx * 0.06, hx + wpx * 0.28, hy + wpx * 0.03),
                 (hx + wpx * 0.1, hy + wpx * 0.08, hx + wpx * 0.28, hy + wpx * 0.11)], (1, 1, 1), width=1.5)
        for lx in (0.15, 0.32, 0.55, 0.72):
            c.lines([(x0 + wpx * lx, gy - hgt * 0.15, x0 + wpx * lx, gy)], o, width=max(3.0, wpx * 0.07))
        tail = [(x0 + wpx * 0.02 - wpx * 0.25 * math.sin(u * 2.5), gy - hgt * (0.45 + 0.6 * u) + 6 * math.sin(t * 4 + u * 3))
                for u in np.linspace(0, 1, 10)]
        c.polylines([tail], o, width=max(3.0, wpx * 0.07))
    else:                                                                          # the truck (cab on the LEFT)
        ctx.rectangle(x0 + wpx * 0.28, gy - hgt * 0.95, wpx * 0.72, hgt * 0.78)    # cargo box
        ctx.set_source_rgb(0.85, 0.85, 0.9)
        ctx.fill()
        c.text_centered("30 t", gy - hgt * 0.48, size=hgt * 0.3, color=(0.2, 0.2, 0.3), cx=x0 + wpx * 0.64)
        ctx.new_path()                                                              # cab
        ctx.move_to(x0, gy - hgt * 0.17)
        ctx.line_to(x0, gy - hgt * 0.55)
        ctx.line_to(x0 + wpx * 0.06, gy - hgt * 0.75)
        ctx.line_to(x0 + wpx * 0.27, gy - hgt * 0.75)
        ctx.line_to(x0 + wpx * 0.27, gy - hgt * 0.17)
        ctx.close_path()
        ctx.set_source_rgb(0.9, 0.25, 0.25)
        ctx.fill()
        ctx.rectangle(x0 + wpx * 0.05, gy - hgt * 0.68, wpx * 0.16, hgt * 0.2)    # windscreen
        ctx.set_source_rgb(0.55, 0.8, 1.0)
        ctx.fill()
        c.circle(x0 + wpx * 0.02, gy - hgt * 0.3, wpx * 0.02, (1, 1, 0.7))
        for wx in (0.14, 0.55, 0.82):
            c.circle(x0 + wpx * wx, gy - hgt * 0.12, hgt * 0.13, (0.12, 0.12, 0.15))
            c.circle(x0 + wpx * wx, gy - hgt * 0.12, hgt * 0.06, (0.6, 0.6, 0.65))
    return hgt


class Scene:
    def __init__(self, layout, sim):
        self.L, self.sim = layout, sim
        self.canvas = Canvas(layout.w, layout.h, studio.render_scale())

    def frame(self, t):
        L, c = self.L, self.canvas
        w, h = L.w, L.h
        ctx = c.ctx
        g = cairo.LinearGradient(0, 0, 0, h)
        g.add_color_stop_rgb(0, 0.03, 0.03, 0.08)
        g.add_color_stop_rgb(1, 0.01, 0.01, 0.02)
        ctx.set_source(g)
        ctx.paint()
        i = min(len(ROUNDS) - 1, int(np.searchsorted(R_START, t, side="right") - 1))
        tr = t - R_START[i]
        small, big, ms, Mb, dur = ROUNDS[i]
        ts = warp(i, tr)
        x1, x2, k = state(i, ts)
        done = k == COUNTS[i]
        sim = SIMS[i]
        wx, gy, TW = w * 0.07, h * 0.47, w * 0.88
        # neon floor + wall
        for j in range(14):
            yy = gy + (j + 1) ** 1.6 * h * 0.0035
            c.lines([(0, yy, w, yy)], (0.5, 0.35, 1.0), width=1.5, alpha=0.25 * (1 - j / 14))
        c.lines([(wx, gy, w, gy)], (0.75, 0.6, 1.0), width=4, alpha=0.9)
        c.lines([(wx, gy, w, gy)], (0.75, 0.6, 1.0), width=14, alpha=0.15)
        ctx.rectangle(0, h * 0.3, wx, gy - h * 0.3)
        ctx.set_source_rgb(0.12, 0.12, 0.2)
        ctx.fill()
        c.lines([(wx, h * 0.3, wx, gy)], CYAN, width=4)
        c.lines([(wx, h * 0.3, wx, gy)], CYAN, width=14, alpha=0.18)
        # impact sparks on the latest hit
        squash = 0.0
        if k >= 1:
            age = (tr - (hit_times(i)[k - 1] - R_START[i])) if i == 0 else 0.03
            if age < 0.18:
                squash = 1 - age / 0.18
                hx = wx if sim["k"][k] == 0 else wx + (x1 + SIZE[small]) * TW
                c.glow(hx, gy - h * 0.03, w * 0.05, WHITE, strength=0.7 * squash, reach=2)
                for j in range(8):
                    a = math.pi * (0.1 + 0.8 * j / 7)
                    r0, r1 = w * 0.02, w * (0.02 + 0.05 * (1 - squash))
                    c.lines([(hx + r0 * math.cos(a), gy - h * 0.03 - r0 * math.sin(a), hx + r1 * math.cos(a),
                              gy - h * 0.03 - r1 * math.sin(a))], GOLD, width=3, alpha=squash)
        buzz = i > 0 and not done and tr > LEAD
        if buzz:
            c.glow(wx + SIZE[small] * TW * 0.6, gy - h * 0.03, w * 0.07, WHITE, strength=0.35, reach=2)
        bx2 = wx + x2 * TW
        if bx2 < w * 1.1:
            hb = draw_obj(c, big, bx2, gy, SIZE[big] * TW, t)
            c.text_centered(LABEL[big], gy - hb * 1.15 - h * 0.012, size=w * 0.036, color=PINK, cx=min(w * 0.82, bx2 + SIZE[big] * TW / 2))
        draw_obj(c, small, wx + x1 * TW, gy, SIZE[small] * TW, t, squash=squash)
        c.text_centered(LABEL[small], gy + h * 0.04, size=w * 0.034, color=CYAN, cx=max(w * 0.13, wx + (x1 + SIZE[small] / 2) * TW))
        # the title of the round
        pop = math.exp(-tr / 0.2)
        c.text_centered(f"{small.upper()}  vs  {big.upper()}", h * 0.215, size=w * 0.07 * (1 + 0.3 * pop), color=WHITE)
        c.text_centered(f"{Mb / ms:,.0f}× heavier", h * 0.252, size=w * 0.042, color=GOLD)
        # the count
        c.text_centered("collisions", h * 0.56, size=w * 0.038, color=(0.75, 0.78, 0.9), bold=False)
        dp = math.exp(-max(0.0, tr - dur * 0.65) / 0.2) if done else 0.0
        c.text_centered(f"{k:,}", h * 0.635, size=w * 0.15 * (1 + 0.2 * dp), color=GOLD if done else WHITE)
        if done:
            nd = len(str(COUNTS[i]))
            c.text_centered(f"π = {'3.14159265'[:nd + 1]}…", h * 0.69, size=w * 0.06, color=GOLD,
                            alpha=smooth((tr - dur * 0.65) / 0.3))
        else:
            c.text_centered("how many? guess!", h * 0.69, size=w * 0.045, color=PINK)
        c.text_centered("every ×100 heavier = one more digit of π", h * 0.765, size=w * 0.036,
                        color=(0.85, 0.87, 0.95), bold=False)

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
    """A note per collision (rising pentatonic; wall = lower octave), merging into a glassy rush, then a buzz."""
    sr = audio.SR
    n = int(round(T_LOOP * sr))
    out = np.zeros(n)
    penta = [0, 2, 4, 7, 9]
    for i in range(len(ROUNDS)):
        times = hit_times(i)
        kinds = SIMS[i]["k"][1:]
        N = len(times)
        idx = np.clip((times * sr).astype(int), 0, n - 1)
        if i == 0:                                                   # round 1: a little melody, one note per hit
            for j, (i0, kd) in enumerate(zip(idx, kinds)):
                step = j // 2
                m = 64 + 12 * (step // 5) + penta[step % 5] - (12 if kd == 0 else 0)
                m = min(m, 100)
                tv = np.arange(int(0.35 * sr)) / sr
                f0 = 440 * 2 ** ((m - 69) / 12)
                sig = (np.sin(2 * np.pi * f0 * tv) + 0.35 * np.sin(2 * np.pi * 2.76 * f0 * tv)) * np.exp(-tv / 0.12)
                out[i0:i0 + len(sig)] += 0.22 * sig[: n - i0]
        else:                                                        # rounds 2-3: pitched impulse trains
            dens = np.bincount(idx // int(sr * 0.05), minlength=n // int(sr * 0.05) + 1)
            g = 0.30 / np.sqrt(np.maximum(1.0, dens[idx // int(sr * 0.05)] / 3.0))
            for kind, f0 in ((0, 1200.0 if i == 1 else 1600.0), (1, 1800.0 if i == 1 else 2600.0)):
                train = np.zeros(n)
                sel = kinds == kind
                np.add.at(train, idx[sel], g[sel])
                tv = np.arange(int(0.03 * sr)) / sr
                kern = np.sin(2 * np.pi * f0 * tv) * np.exp(-tv / (0.008 if i == 1 else 0.0025))
                out += np.convolve(train, kern)[:n]
        tc = R_START[i] + ROUNDS[i][4] * 0.65 + 0.05                # the chime: the count is final
        tvc = np.arange(int(1.2 * sr)) / sr
        ch = sum(np.sin(2 * np.pi * 440 * 2 ** ((mm - 69) / 12) * tvc) for mm in (76 + 2 * i, 81 + 2 * i, 84 + 2 * i))
        ch *= np.exp(-tvc / 0.4) / 3
        i0 = int(tc * sr)
        out[i0:i0 + len(ch)] += 0.12 * ch[: max(0, n - i0)]
    pad = kit.loop_pad(T_LOOP, ((45, 1.0), (52, 0.6), (57, 0.4), (64, 0.25)), gain=0.012)
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
