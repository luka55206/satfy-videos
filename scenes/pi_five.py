"""PI FIVE — π blocks episode: FIVE lanes at once. A 1 kg block against 1 kg, 100 kg, 10,000 kg, 1,000,000 kg and
100,000,000 kg. All five are pushed at the same moment; the counts land one after another, 3 · 31 · 314 · 3,141 ·
31,415, and stack into π = 3.1415.

Nameable change vs the shipped π blocks Shorts: five races side by side (the digits build up as a staircase).
Counts: exact event-driven simulation for every lane (scenes/pi_blocks.simulate_round), played on a time grid so each
lane finishes 1.4 s after the previous one (no long count: the biggest burst is 1.5 s).
Loop: every lane rewinds to its start position (frame 0).
Audio (original, lib/sfx): a light marimba bed; lane 1-2 one marimba note per collision (π digits), lanes 3-5 a harp
strum over their bursts, a chime when each count lands, a falling sweep on the rewind.
"""
import bisect
import math
import sys
from pathlib import Path

import cairo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib import kit, sfx, studio  # noqa: E402
from lib.kit import DT, FPS, arg, smooth  # noqa: E402
from lib.layouts import get_layout  # noqa: E402
from lib.studio import Canvas, VideoWriter  # noqa: E402
from scenes.pi_blocks import S1, simulate_round  # noqa: E402
from scenes.pi_long import PI_DIG, marimba, strum_burst, sup  # noqa: E402

SCENE = "pi_five"
CYAN, GOLD, WHITE, SOFT = (0.35, 0.85, 1.0), (1.0, 0.8, 0.3), (0.96, 0.97, 1.0), (0.75, 0.78, 0.92)
LANE_COLS = [(1.0, 0.55, 0.45), (1.0, 0.75, 0.3), (0.6, 1.0, 0.5), (0.45, 0.8, 1.0), (0.8, 0.6, 1.0)]
MASSES = [1.0, 100.0, 1e4, 1e6, 1e8]
T_GO, T_FIRST = 0.25, 0.9
T_END = [1.7, 3.1, 4.5, 5.9, 7.4]                    # each lane's last collision (video s)
T_RW0, T_RW1 = 11.4, 12.8
T_LOOP = 13.1
FLOORS = [0.37, 0.46, 0.55, 0.64, 0.73]
AREA = (0.07, 0.64)
RATE_AFTER = 0.22                                     # sim units per video second after the last hit


def clamp(v, a=0.0, b=1.0):
    return max(a, min(b, v))


class Lane:
    def __init__(self, M, t_end):
        self.ev = simulate_round(M)
        self.M, self.N = M, len(self.ev) - 1
        self.hs = [e[0] for e in self.ev]
        n = self.N
        if n <= 31:
            self.hv = [T_FIRST + (t_end - T_FIRST) * k / max(1, n - 1) for k in range(n)]
        else:                                          # a burst: dense in the middle, every collision real
            self.hv = [T_FIRST + (t_end - T_FIRST) * (0.5 - 0.5 * math.cos(math.pi * k / (n - 1))) for k in range(n)]

    def sim_t(self, t):
        if t >= T_RW0:                                 # the rewind: back to sim time 0
            ts_end = self.sim_t(T_RW0 - 1e-6)
            return ts_end * (1 - smooth(clamp((t - T_RW0) / (T_RW1 - T_RW0))))
        hs, hv = self.hs, self.hv
        if t < T_GO:
            return 0.0
        if t < hv[0]:
            return hs[1] * (t - T_GO) / (hv[0] - T_GO)
        k = bisect.bisect_right(hv, t) - 1             # hv[k] <= t: collision k+1 done
        if k + 1 < len(hv):
            return hs[k + 1] + (hs[k + 2] - hs[k + 1]) * (t - hv[k]) / (hv[k + 1] - hv[k])
        return hs[-1] + (t - hv[-1]) * RATE_AFTER

    def at(self, t):
        ts = self.sim_t(t)
        j = max(0, bisect.bisect_right(self.hs, ts) - 1)
        t0, x1, v1, x2, v2, _ = self.ev[j]
        d = ts - t0
        return x1 + v1 * d, x2 + v2 * d, j


LANES = [Lane(M, te) for M, te in zip(MASSES, T_END)]


def m_label(M):
    return f"{M:,.0f} kg" if M < 1e7 else f"10{sup(int(round(math.log10(M))))} kg"


class Scene:
    def __init__(self, layout):
        self.L = layout
        self.canvas = Canvas(layout.w, layout.h, studio.render_scale())

    def lane(self, i, t):
        c, w, h = self.canvas, self.L.w, self.L.h
        ctx = c.ctx
        ln = LANES[i]
        fy = h * FLOORS[i]
        wx, xe = w * AREA[0], w * AREA[1]
        TW = xe - wx
        col = LANE_COLS[i]
        c.lines([(wx, fy - h * 0.075, wx, fy)], (0.85, 0.88, 1.0), width=4)
        c.lines([(wx - w * 0.012, fy - h * 0.075 + j * h * 0.015, wx, fy - h * 0.075 + j * h * 0.015 - h * 0.012)
                 for j in range(5)], (0.6, 0.65, 0.8), width=2, alpha=0.6)
        c.lines([(wx, fy, xe, fy)], (0.85, 0.88, 1.0), width=3)
        x1, x2, j = ln.at(t)
        s_small = S1 * TW
        s_big = s_small * (1 + 0.33 * math.log10(ln.M))
        ctx.save()
        ctx.rectangle(wx, fy - h * 0.088, TW, h * 0.088)
        ctx.clip()
        bx1, bx2 = wx + x1 * TW, wx + x2 * TW
        ctx.rectangle(bx1, fy - s_small, s_small, s_small)
        ctx.set_source_rgb(*CYAN)
        ctx.fill()
        ctx.rectangle(bx2, fy - s_big, s_big, s_big)
        ctx.set_source_rgb(*col)
        ctx.fill()
        busy = ln.hv[0] <= t <= ln.hv[-1] + 0.05 and ln.N > 31 and t < T_RW0
        if busy:
            c.glow(bx1 + s_small, fy - s_small / 2, w * 0.018, WHITE, strength=0.5 + 0.3 * math.sin(t * 90), reach=2)
        ctx.restore()
        c.text_centered(m_label(ln.M), fy - s_big * 0.45, size=min(h * 0.018, s_big * 0.28), color=(0.08, 0.06, 0.1),
                        cx=min(bx2 + s_big / 2, w * 2), max_w=s_big * 0.92) if bx2 + s_big / 2 < xe else None
        # the count, right
        if t >= T_RW0:
            n = min(ln.N, max(0, j))
        else:
            n = bisect.bisect_right(ln.hv, t)
        done = n >= ln.N and t < T_RW0
        pop = math.exp(-(t - ln.hv[-1]) / 0.18) if done else 0.0
        cx = w * 0.82
        if done:
            c.glow(cx, fy - h * 0.035, w * 0.08, col, strength=0.25 * (0.5 + pop), reach=1.6)
        c.text_centered(f"{n:,}", fy - h * 0.02, size=h * 0.04 * (1 + 0.25 * pop), color=col if done else WHITE, cx=cx,
                        max_w=w * 0.3)
        c.text_centered("collisions", fy + h * 0.012, size=h * 0.014, color=SOFT, bold=False, cx=cx)

    def draw(self, f, rule):
        L, c = self.L, self.canvas
        w, h = L.w, L.h
        t = f * DT
        ctx = c.ctx
        g = cairo.RadialGradient(w / 2, h * 0.5, 0, w / 2, h * 0.5, h * 0.7)
        g.add_color_stop_rgb(0, 0.06, 0.06, 0.12)
        g.add_color_stop_rgb(1, 0.005, 0.005, 0.015)
        ctx.set_source(g)
        ctx.paint()
        for i in range(len(LANES)):
            self.lane(i, t)
        # the head: the question, then π builds from the finished lanes
        k = sum(1 for ln in LANES if t >= ln.hv[-1]) if t < T_RW0 else 0
        if k == 0:
            c.text_centered("1 kg vs 5 heavier blocks", h * 0.245, size=w * 0.07, color=WHITE, max_w=w * 0.92)
            c.text_centered("each one 100× heavier than the last", h * 0.278, size=w * 0.04, color=SOFT, bold=False)
        else:
            s = PI_DIG[0] + ("." + PI_DIG[1:k] if k > 1 else "")
            pop = math.exp(-(t - LANES[k - 1].hv[-1]) / 0.2)
            c.text_centered(f"π = {s}…", h * 0.26, size=w * 0.11 * (1 + 0.12 * pop), color=GOLD, max_w=w * 0.92)
        if T_END[-1] + 0.8 <= t < T_RW0:
            a = clamp((t - T_END[-1] - 0.8) / 0.4)
            c.text_centered("every 100× heavier", h * 0.795, size=w * 0.055, color=WHITE, alpha=a)
            c.text_centered("adds ONE more digit of π", h * 0.83, size=w * 0.055, color=GOLD, alpha=a)
        if rule:
            c.caption(rule, alpha=1.0, layout=L)
        c.watermark(L)


def render(layout, out_path, rule, still_frame=None):
    sc = Scene(layout)
    writer = None if still_frame is not None else VideoWriter(out_path, sc.canvas, FPS)
    nf = int(round(T_LOOP * FPS))
    for f in range(nf):
        if still_frame is not None and f != still_frame:
            continue
        sc.draw(f, rule)
        if writer is None:
            studio.save_still(sc.canvas, out_path)
            return f / FPS
        writer.write_frame()
    writer.close()
    return nf / FPS


def sound():
    b = sfx.Bed(T_LOOP, seed=5)
    arp = [(69, 72, 76, 81), (65, 69, 72, 77), (64, 67, 72, 76), (67, 71, 74, 79)]
    pat = [0, 2, 1, 3, 2, 1, 3, 2]
    t, q = 0.0, 0
    while t < T_LOOP - 0.2:                                     # light music-box bed
        marimba(b, t, arp[int(t // 3.2) % 4][pat[q % 8]], 0.018 if q % 4 else 0.024)
        t += 0.4
        q += 1
    scale = [60, 62, 64, 67, 69, 72, 74, 76, 79, 81]
    for k, tt in enumerate(LANES[0].hv):                         # lane 1: 3 notes
        marimba(b, tt, 72 + 4 * k, 0.11)
    for k, tt in enumerate(LANES[1].hv):                         # lane 2: the π digits, one per collision
        if tt > T_END[0] + 0.1:
            marimba(b, tt, scale[int(PI_DIG[k % len(PI_DIG)])] + 12, 0.075)
    for i in (2, 3, 4):                                          # the bursts: a strum over each lane's finish
        t0 = T_END[i - 1] + 0.05
        strum_burst(b, t0, T_END[i] - t0, 28 + 6 * i, g=0.05)
    for i in (0, 1):
        b.chime(T_END[i] + 0.02, (79 + 2 * i, 84 + 2 * i), 0.06)
    b.chime(T_END[-1] + 0.85, (72, 76, 79, 84, 88), 0.06, decay=1.0)
    b.drop(T_RW0, T_RW1 - T_RW0, 0.05, 1400, 220)
    return b.get()


def main():
    label, rule = arg("--label", "v1"), arg("--rule", "")
    studio.OUT_DIR.mkdir(exist_ok=True)
    layout = get_layout(kit.orients()[0])
    print(f"[{SCENE}] counts " + ", ".join(f"{ln.N:,}" for ln in LANES) + f"  {T_LOOP:.1f}s")
    if kit.has("--still"):
        f = int(round(float(arg("--at")) * FPS)) if arg("--at") else int(arg("--frame", "0"))
        png = studio.OUT_DIR / f"{SCENE}_{label}_f{f}_{layout.tag}.png"
        render(layout, png, rule, still_frame=f)
        print(f"[{SCENE}] -> {png}")
        return
    name = f"{SCENE}_{label}_{layout.tag}"
    video = studio.OUT_DIR / f"{name}_silent.mp4"
    d = render(layout, video, rule)
    kit.deliver_loop(SCENE, name, layout, video, [], d, voice="piano", bed=sound(), peak_db=-6.0)


if __name__ == "__main__":
    main()
