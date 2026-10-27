"""PI PLAY — "π blocks play π": the two blocks again, and every collision plays the NEXT DIGIT OF π as a note.

Owner (2026-10-25): the π blocks went wild because they are simple, they are π, and the sound was satisfying; later
comments said the dense clicks sounded "like an alarm". So: the same simple stage (wall, frictionless floor, m = 1 kg,
M = 1 → 100 → 10,000 kg = 3 → 31 → 314 collisions, Galperin 2003, exact event-driven simulation) and a new sound:
collision k plays digit k of π (3 1 4 1 5 9 2 6 …) on a soft marimba, digits 0-9 on a C-major pentatonic scale (it can
never clash), a soft wooden "tok" under every wall hit. Video time is warped so the collisions land on a musical
grid: 3 slow notes, 31 as a steady melody, 314 accelerating into a sparkling harp-like run (never a buzz). The blocks
still move exactly along the simulated paths, only the playback speed between collisions changes.
On screen: the masses, the collision counter, a ticker of the π digits being played (the newest one glows),
"π = 3.14…" when a round is done. Loop: round 3 drifts out, round 1 starts again.
"""
import bisect
import math
import sys
from pathlib import Path

import cairo
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib import kit, sfx, studio  # noqa: E402
from lib.kit import DT, FPS, arg, smooth  # noqa: E402
from lib.layouts import get_layout  # noqa: E402
from lib.studio import Canvas, VideoWriter  # noqa: E402
from scenes.pi_blocks import S1, simulate_round  # noqa: E402  (the same exact simulation)

SCENE = "pi_play"
CYAN, GOLD, WHITE, SOFT = (0.35, 0.85, 1.0), (1.0, 0.8, 0.3), (1, 1, 1), (0.75, 0.78, 0.9)
PI_DIGITS = ("31415926535897932384626433832795028841971693993751058209749445923078164062862089986280348253421170679"
             "82148086513282306647093844609550582231725359408128481117450284102701938521105559644622948954930381964"
             "42881097566593344612847564823378678316527120190914564856692346034861045432664821339360726024914127372"
             "4587006606315588174881520920962829254091715364367892590360011330530548820466521384146951941511609")
SCALE = [60, 62, 64, 67, 69, 72, 74, 76, 79, 81]          # digit 0..9 -> C-major pentatonic, two octaves
# (M, intro, music length, tail, warp exponent)
ROUNDS = [(1.0, 0.45, 1.5, 0.95, 1.0), (100.0, 0.45, 5.0, 1.05, 1.0), (1e4, 0.45, 5.0, 1.9, 1.0)]
# round 3 (owner v2: "314 is too long, monotonous, not satisfying"): the 314 digits fly onto a RING of 314 slots and are
# heard as 20 STRUMS of 16 notes (a harp strum per beat), the chord changing every 4 strums (Am F C G …)
STRUM_N, STRUM_BEAT, STRUM_SPREAD = 16, 0.25, 0.0115
STRUM_CHORDS = [(57, 60, 64), (53, 57, 60), (55, 60, 64), (55, 59, 62), (57, 60, 64)]   # Am F C G Am
SIMS = [simulate_round(M) for M, *_ in ROUNDS]
COUNTS = [len(s) - 1 for s in SIMS]
assert COUNTS == [3, 31, 314], COUNTS
DUR = [a + b + c for _, a, b, c, _ in ROUNDS]
R_START = np.concatenate([[0.0], np.cumsum(DUR)])
T_LOOP = float(R_START[-1])


def hit_times(i):
    """video time (from the round start) of every collision: evenly spaced (rounds 1-2), accelerating (round 3)."""
    _, intro, music, _, p = ROUNDS[i]
    n = COUNTS[i]
    if i == 2:                                                    # strums: 16 quick notes on every beat
        return [intro + (k // STRUM_N) * STRUM_BEAT + (k % STRUM_N) * STRUM_SPREAD for k in range(n)]
    return [intro + music * (k / n) ** p for k in range(1, n + 1)]


HITS = [hit_times(i) for i in range(len(ROUNDS))]


def sim_time(i, tr):
    """video time in round -> simulation time (piecewise linear through the collisions)."""
    ev = SIMS[i]
    hv = [0.0] + HITS[i]
    hs = [0.0] + [e[0] for e in ev[1:]]
    intro = ROUNDS[i][1]
    if tr < intro:
        return 0.0
    if tr < hv[1]:
        return hs[1] * (tr - intro) / (hv[1] - intro)
    k = bisect.bisect_right(hv, tr) - 1
    if k + 1 < len(hv):
        return hs[k] + (hs[k + 1] - hs[k]) * (tr - hv[k]) / (hv[k + 1] - hv[k])
    rate = (hs[-1] - hs[1]) / max(1e-6, hv[-1] - hv[1]) * 1.4 + 0.3
    return hs[-1] + (tr - hv[-1]) * rate


def state(i, ts):
    ev = SIMS[i]
    times = [e[0] for e in ev]
    k = bisect.bisect_right(times, ts) - 1
    t0, x1, v1, x2, v2, _ = ev[k]
    d = ts - t0
    return x1 + v1 * d, x2 + v2 * d, k


class Scene:
    def __init__(self, layout):
        self.L = layout
        self.canvas = Canvas(layout.w, layout.h, studio.render_scale())

    def draw(self, f, rule):
        L, c = self.L, self.canvas
        w, h = L.w, L.h
        t = f * DT
        ctx = c.ctx
        g = cairo.RadialGradient(w / 2, h * 0.42, 0, w / 2, h * 0.42, h * 0.7)
        g.add_color_stop_rgb(0, 0.05, 0.05, 0.09)
        g.add_color_stop_rgb(1, 0.0, 0.0, 0.0)
        ctx.set_source(g)
        ctx.paint()
        i = min(len(ROUNDS) - 1, int(np.searchsorted(R_START, t, side="right") - 1))
        tr = t - R_START[i]
        M = ROUNDS[i][0]
        ts = sim_time(i, tr)
        x1, x2, k = state(i, ts)
        hv = HITS[i]
        n_played = bisect.bisect_right(hv, tr)                     # collisions heard so far
        # the stage
        wx, fy, TW = w * 0.08, h * 0.45, w * 0.86
        c.lines([(wx, h * 0.31, wx, fy)], (0.85, 0.88, 1.0), width=4)
        hatch = [(wx - w * 0.025, h * 0.31 + j * h * 0.012, wx, h * 0.31 + j * h * 0.012 - h * 0.01) for j in range(12)]
        c.lines(hatch, (0.6, 0.65, 0.8), width=1.5, alpha=0.6)
        c.lines([(wx, fy, w * 0.97, fy)], (0.85, 0.88, 1.0), width=3)
        s_small = S1 * TW
        s_big = w * (0.075 + 0.028 * math.log10(M)) if M > 1 else s_small
        bx1, bx2 = wx + x1 * TW, wx + x2 * TW
        ctx.rectangle(bx1, fy - s_small, s_small, s_small)
        ctx.set_source_rgb(*CYAN)
        ctx.fill()
        c.text_centered("m", fy - s_small * 0.35, size=s_small * 0.55, color=(0.02, 0.05, 0.1), cx=bx1 + s_small / 2)
        if bx2 < w * 1.05:
            ctx.rectangle(bx2, fy - s_big, s_big, s_big)
            ctx.set_source_rgb(*GOLD)
            ctx.fill()
            c.text_centered("M", fy - s_big * 0.38, size=s_big * 0.45, color=(0.1, 0.07, 0.0), cx=bx2 + s_big / 2)
        if n_played >= 1:                                          # a soft glow where the last note came from
            age = tr - hv[n_played - 1]
            if age < 0.25:
                kind = SIMS[i][n_played][5]
                xx = wx if kind == "wall" else bx1 + s_small
                d = int(PI_DIGITS[(n_played - 1) % len(PI_DIGITS)])
                col = [(1.0, 0.5, 0.5), (1.0, 0.7, 0.4), GOLD, (0.6, 1.0, 0.5), CYAN][d % 5]
                c.glow(xx, fy - s_small / 2, w * 0.04, col, strength=0.8 * (1 - age / 0.25), reach=2.2)
        # masses
        c.text_centered(f"M = {M:,.0f} kg", h * 0.215, size=w * 0.07, color=GOLD)
        c.text_centered("m = 1 kg", h * 0.252, size=w * 0.042, color=CYAN, bold=False)
        # the counter
        done = n_played == COUNTS[i]
        pop = math.exp(-(tr - hv[-1]) / 0.15) if done else 0.0
        if i < 2:
            c.text_centered(f"{n_played:,}", h * 0.56, size=w * 0.16 * (1 + 0.25 * pop), color=GOLD if done else WHITE)
            c.text_centered("collisions", h * 0.595, size=w * 0.04, color=SOFT, bold=False)
        if i == 2:
            self.ring(t, tr, n_played, done, wx, fy, bx1, s_small, hv)
        # the ticker: the digits of π being played, the newest one big
        if n_played >= 1 and not done and i < 2:
            shown = PI_DIGITS[max(0, n_played - 12):n_played]
            ctx_x = w / 2
            fs = w * 0.06
            c._font(fs, True)
            adv = ctx.text_extents("0").x_advance * 1.15
            x_end = ctx_x + adv * len(shown) / 2                          # the whole window centred
            for j, ch in enumerate(reversed(shown)):
                x = x_end - (j + 1) * adv
                a = 1.0 if j == 0 else max(0.0, 0.75 - 0.06 * j)
                size = fs * (1.35 if j == 0 else 1.0)
                c.text_centered(ch, h * 0.66, size=size, color=GOLD if j == 0 else WHITE, alpha=a, cx=x + adv / 2)
        if done and i < 2:
            k2 = smooth(min(1.0, (tr - hv[-1]) / 0.3))
            pis = ["3", "3.1", "3.14"][i]
            c.text_centered(f"π = {pis}…", h * 0.665, size=w * 0.08, color=GOLD, alpha=k2)
        line = ["equal masses", "100× heavier", "10,000× heavier"][i]
        if i == 2 and done:
            c.text_centered("π = 3.14…", h * 0.75, size=w * 0.075 * (1 + 0.25 * pop), color=GOLD)
        else:
            c.text_centered(line, h * 0.75, size=w * 0.055, color=WHITE)
        c.text_centered("every hit plays the next digit of π", h * 0.785, size=w * 0.04, color=GOLD, bold=False)
        if rule:
            c.caption(rule, alpha=1.0, layout=L)
        c.watermark(L)


RING_COLS = [(1.0, 0.45, 0.5), (1.0, 0.62, 0.35), (1.0, 0.82, 0.35), (0.75, 1.0, 0.45), (0.4, 1.0, 0.6),
             (0.35, 0.9, 1.0), (0.45, 0.65, 1.0), (0.65, 0.5, 1.0), (0.9, 0.5, 1.0), (1.0, 0.5, 0.8)]


def _ring(self, t, tr, n_played, done, wx, fy, bx1, s_small, hv):
    """314 slots on a circle; each collision's digit flies from the impact point to its slot."""
    c, w, h = self.canvas, self.L.w, self.L.h
    cx, cy, R = w * 0.5, h * 0.585, h * 0.115
    full = smooth(min(1.0, (tr - hv[-1]) / 0.6)) if done else 0.0
    shrink = 1.0 - smooth(min(1.0, max(0.0, (tr - (DUR[2] - 0.6)) / 0.6)))   # the ring collapses before the loop
    R *= max(0.001, shrink)
    full *= shrink
    c.ring(cx, cy, R, (0.5, 0.55, 0.8), width=2, alpha=0.25 + 0.5 * full)
    if full > 0:
        c.glow(cx, cy, R * 1.1, GOLD, strength=0.45 * full * (0.8 + 0.2 * math.sin(tr * 6)), reach=1.6)
        c.ring(cx, cy, R, GOLD, width=6, alpha=full)
    FLY = 0.32
    for k in range(min(n_played + 16, 314)):
        if k >= len(hv):
            break
        age = tr - hv[k]
        if age < 0:
            continue
        a = -math.pi / 2 + 2 * math.pi * k / 314
        tx, ty = cx + R * math.cos(a), cy + R * math.sin(a)
        d = int(PI_DIGITS[k])
        col = RING_COLS[d]
        if age < FLY:                                             # flying from the impact point
            u = smooth(age / FLY)
            kind = SIMS[2][k + 1][5]
            sx = wx if kind == "wall" else bx1 + s_small
            sy = fy - s_small / 2
            x = sx + (tx - sx) * u
            y = sy + (ty - sy) * u - math.sin(math.pi * u) * h * 0.06
            c.circle(x, y, w * 0.007, col, alpha=0.9)
        else:
            pop = math.exp(-(age - FLY) / 0.15)
            c.circle(tx, ty, w * (0.0055 + 0.006 * pop) * min(1.0, shrink * 3), col, alpha=0.95)
            if pop > 0.05:
                c.glow(tx, ty, w * 0.02, col, strength=0.6 * pop, reach=2)
    pop = math.exp(-(tr - hv[-1]) / 0.15) if done else 0.0
    if shrink > 0.02:
        c.text_centered(f"{n_played:,}", cy + h * 0.02, size=w * 0.13 * (1 + 0.25 * pop) * shrink,
                        color=GOLD if done else WHITE, alpha=shrink)
        c.text_centered("collisions", cy + h * 0.05, size=w * 0.035, color=SOFT, bold=False, alpha=shrink)



Scene.ring = _ring


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


def marimba(b, t0, m, g):
    tv = np.arange(int(0.9 * sfx.SR)) / sfx.SR
    f = sfx.hz(m)
    sig = (np.sin(2 * np.pi * f * tv) * np.exp(-tv / 0.45)
           + 0.35 * np.sin(2 * np.pi * f * 3.93 * tv) * np.exp(-tv / 0.05)
           + 0.12 * np.sin(2 * np.pi * f * 9.2 * tv) * np.exp(-tv / 0.012))
    b.add(t0, sig * np.clip(tv / 0.002, 0, 1), g)


def wood(b, t0, g):
    tv = np.arange(int(0.12 * sfx.SR)) / sfx.SR
    sig = np.sin(2 * np.pi * np.cumsum(180 + 120 * np.exp(-tv / 0.01)) / sfx.SR) * np.exp(-tv / 0.035)
    b.add(t0, sig, g)


def sound():
    b = sfx.Bed(T_LOOP, seed=31)
    chords = [(45, 52, 57, 64), (41, 48, 57, 60), (43, 50, 55, 62)]
    for i in range(len(ROUNDS)):
        r0 = R_START[i]
        b.pad([(r0, chords[i])], 0.6, g=0.035)
        hv = HITS[i]
        if i == 2:
            for j, tt in enumerate(hv):
                beat = j // STRUM_N
                ch = STRUM_CHORDS[min(len(STRUM_CHORDS) - 1, beat // 4)]
                d = int(PI_DIGITS[j])
                m = ch[d % 3] + 12 * (d // 4)                       # the digit picks a chord tone and an octave
                marimba(b, r0 + tt, m, 0.085 * (0.8 + 0.4 * (j % STRUM_N == 0)))
                if j % STRUM_N == 0:
                    wood(b, r0 + tt, 0.12)
                    b.add(r0 + tt, np.sin(2 * np.pi * sfx.hz(ch[0] - 24) *
                                          np.arange(int(0.3 * sfx.SR)) / sfx.SR) *
                          np.exp(-np.arange(int(0.3 * sfx.SR)) / sfx.SR / 0.12), 0.10)
            for q in range(len(STRUM_CHORDS)):
                b.pad([(r0 + ROUNDS[i][1] + q * 4 * STRUM_BEAT, STRUM_CHORDS[q])], 0.6, g=0.03)
            tend = r0 + hv[-1] + 0.06
            b.hit(tend, 0.3)
            b.chime(tend, (69, 72, 76, 81, 84), 0.07, decay=1.2)
            continue
        for j, tt in enumerate(hv):
            gap = (hv[j] - hv[j - 1]) if j > 0 else 0.5
            g = 0.22 * min(1.0, math.sqrt(max(gap, 0.004) / 0.12))   # fast runs get softer, never louder
            d = int(PI_DIGITS[j % len(PI_DIGITS)])
            marimba(b, r0 + tt, SCALE[d], g)
            if SIMS[i][j + 1][5] == "wall":
                wood(b, r0 + tt, 0.10 * min(1.0, math.sqrt(max(gap, 0.004) / 0.12)))
        tend = r0 + hv[-1] + 0.08                                     # the count is final: a warm chord
        b.chime(tend, (72, 76, 79, 84)[: 2 + i], 0.06, decay=0.9)
    return b.get()


def main():
    label, rule = arg("--label", "v1"), arg("--rule", "")
    studio.OUT_DIR.mkdir(exist_ok=True)
    layout = get_layout(kit.orients()[0])
    if kit.has("--still"):
        f = int(round(float(arg("--at")) * FPS)) if arg("--at") else int(arg("--frame", "0"))
        png = studio.OUT_DIR / f"{SCENE}_{label}_f{f}_{layout.tag}.png"
        render(layout, png, rule, still_frame=f)
        print(f"[{SCENE}] -> {png}")
        return
    print(f"[{SCENE}] {T_LOOP:.2f}s  collisions {COUNTS}")
    name = f"{SCENE}_{label}_{layout.tag}"
    video = studio.OUT_DIR / f"{name}_silent.mp4"
    d = render(layout, video, rule)
    kit.deliver_loop(SCENE, name, layout, video, [], d, voice="piano", bed=sound(), peak_db=-6.0)


if __name__ == "__main__":
    main()
