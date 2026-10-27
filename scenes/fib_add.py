"""FIB ADD — Fibonacci part 2: "just keep adding the last two numbers" — and phi appears.

Follow-up to the channel's winner (fib_spiral: 31.5k views, 69.5% stayed-to-watch), built to the
2026-10-10 report formula, with the rule shown LITERALLY so it needs no explanation:
- Hook, frame 0: two squares "1", "1" and a big "1 + 1 = ?"; the answer pops in at ~0.5 s.
- Every step a big sum pops ("8 + 13 = 21") and the new number lands as a SOLID coloured square
  (new picture vs part 1's outlines); the camera zooms out so the build never stops.
- Under it, "21 ÷ 13 = 1.6153846154" — each digit pops gold as it matches phi.
- Result: the golden spiral sweeps through every square in one glowing stroke, rings burst from
  the spiral's eye and a big "φ = 1.6180339887" blooms. Quick rewind to "1 + 1" (loop).

Audio (original synthesis only): a glass-harp note per sum (rising, faster), a chime per new gold
digit, a rising sweep along the spiral + a chord on the reveal, falling notes on the rewind, a pad.
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
from scenes.fib_spiral import ARC0, PHI, PHI_STR, eye, tiling  # noqa: E402  (shared geometry)

SCENE = "fib_add"
MELODY = arg("--melody", "0") == "1"    # part 3: every Fibonacci number plays the note F(n) mod 7 (C major)
SCALE = [60, 62, 64, 65, 67, 69, 71]
NOTE_NAMES = ["C", "D", "E", "F", "G", "A", "B"]
N = 26                                   # squares: F(26) = 121,393 (ratio fully gold by then)
D0, DK, DMIN = 0.80, 0.88, 0.36          # seconds per sum: first, decay, floor
T_SWEEP, T_HOLD, T_BACK = 1.0, 2.0, 1.3  # spiral sweep, reveal hold, rewind
COLS = [(1.00, 0.42, 0.55), (1.00, 0.70, 0.30), (0.40, 0.85, 0.55), (0.30, 0.70, 1.00), (0.70, 0.50, 1.00)]
GOLD = (1.0, 0.82, 0.40)
GREY = (0.75, 0.78, 0.88)


def simulate():
    F, sq = tiling(N)
    starts, t = [], 0.45                 # the first sum lands at 0.45 s
    for k in range(2, N):
        starts.append(t)
        t += max(DMIN, D0 * DK ** (k - 2))
    t_run = t
    t_loop = t_run + T_SWEEP + T_HOLD + T_BACK
    sim = {"F": F, "sq": sq, "starts": starts, "t_run": t_run, "t_loop": t_loop,
           "nf": int(round(t_loop * FPS)), "eye": eye(sq)}
    sim["lock"] = lock_times(sim)
    return sim


def step_at(sim, t):
    """Fractional count of sums done (0 .. N-2); smooth rewind at the end."""
    st, tr = sim["starts"], sim["t_run"]
    t_back = tr + T_SWEEP + T_HOLD
    if t >= t_back:
        return (N - 2) * (1.0 - smooth((t - t_back) / T_BACK))
    if t >= tr:
        return float(N - 2)
    if t < st[0]:
        return 0.0
    i = max(j for j in range(len(st)) if st[j] <= t)
    end = st[i + 1] if i + 1 < len(st) else tr
    return i + min(1.0, (t - st[i]) / max(end - st[i], 1e-6))


def ratio_str(F, k):
    """Ratio of the newest two terms, as shown: F[k] / F[k-1] to 10 decimals, + matching chars."""
    r = f"{F[k] / F[k - 1]:.10f}"
    m = 0
    while m < len(r) and r[m] == PHI_STR[m]:
        m += 1
    return r, m


def lock_times(sim):
    out, prev = {}, 0
    for i, t in enumerate(sim["starts"]):
        _, m = ratio_str(sim["F"], i + 2)
        for c in range(prev, m):
            out[c] = t
        prev = max(prev, m)
    return out


def ease_back(p):
    p = min(max(p, 0.0), 1.0)
    c1 = 1.70158
    return 1 + (c1 + 1) * (p - 1) ** 3 + c1 * (p - 1) ** 2


class Scene:
    def __init__(self, layout, sim):
        self.L, self.sim = layout, sim
        self.canvas = Canvas(layout.w, layout.h, studio.render_scale())
        w, h = layout.w, layout.h
        self.cy = h * 0.425
        self.half_w, self.half_h = w * 0.44, h * 0.175

    def fit(self, k):
        x0, y0, x1, y1 = self.sim["sq"][k][5]
        E = self.sim["eye"]
        return min(self.half_w / max(E.real - x0, x1 - E.real), self.half_h / max(E.imag - y0, y1 - E.imag))

    def draw(self, f, rule):
        sim, L, c = self.sim, self.L, self.canvas
        w, h = L.w, L.h
        t = f * DT
        F, sq, E = sim["F"], sim["sq"], sim["eye"]
        s = step_at(sim, t)
        done = int(s)                                   # sums completed
        p_new = s - done                                # progress of the square popping in
        k_last = min(1 + done, N - 1)                   # index of the newest fully placed square
        # camera: fit the rectangle of the newest square (log-interpolated during the pop)
        lk0 = math.log(self.fit(k_last))
        lk1 = math.log(self.fit(min(k_last + 1, N - 1)))
        kp = math.exp(lk0 + (lk1 - lk0) * smooth(min(1.0, p_new / 0.4)))
        ctx = c.ctx
        g = cairo.RadialGradient(w / 2, self.cy, 0, w / 2, self.cy, max(w, h) * 0.7)
        g.add_color_stop_rgb(0.0, 0.07, 0.06, 0.11)
        g.add_color_stop_rgb(1.0, 0.01, 0.01, 0.02)
        ctx.set_source(g)
        ctx.paint()

        def P(x, y):
            return w / 2 + (x - E.real) * kp, self.cy - (y - E.imag) * kp

        tr = sim["t_run"]
        sweep = smooth((t - tr) / T_SWEEP) if t >= tr else 0.0
        out = 1.0 - smooth((t - tr - T_SWEEP - T_HOLD) / 0.5) if t >= tr else 1.0
        n_show = k_last + (1 if (p_new > 0 and k_last < N - 1) else 0)
        ctx.save()
        ctx.rectangle(0, h * 0.235, w, h * 0.405)                # squares never cover the text
        ctx.clip()
        for k in range(n_show + 1):
            x0, y0, side, d, cen, _ = sq[k]
            pop = 1.0 if k <= k_last else ease_back(p_new / 0.55)
            sz = side * kp * max(pop, 0.0)
            if sz < 0.8:
                continue
            cxs, cys = P(x0 + side / 2, y0 + side / 2)
            col = COLS[k % len(COLS)]
            ctx.rectangle(cxs - sz / 2, cys - sz / 2, sz, sz)
            ctx.set_source_rgba(*col, 0.88)
            ctx.fill_preserve()
            ctx.set_source_rgba(0.05, 0.04, 0.08, 0.9)
            ctx.set_line_width(3)
            ctx.stroke()
            if sz > 36:
                fs = min(sz * 0.36, h * 0.07)
                c.text_centered(f"{F[k]:,}", cys + fs * 0.36, size=fs, color=(0.06, 0.05, 0.09),
                                alpha=min(1.0, (sz - 36) / 40), cx=cxs, max_w=sz * 0.86)

        ctx.restore()

        # the result: the golden spiral sweeps through every square
        if sweep > 0:
            total = sweep * N
            arcs = []
            for k in range(N):
                part = min(1.0, max(0.0, total - k))
                if part <= 0:
                    break
                x0, y0, side, d, cen, _ = sq[k]
                a0 = math.radians(ARC0[d])
                pts = [P(cen[0] + side * math.cos(a0 + math.pi / 2 * part * i / 24),
                         cen[1] + side * math.sin(a0 + math.pi / 2 * part * i / 24)) for i in range(25)]
                arcs.append(pts)
            c.polylines(arcs, GOLD, width=26, alpha=0.18 * out)
            c.polylines(arcs, (1.0, 0.92, 0.70), width=8, alpha=0.95 * out)
            age = t - tr - T_SWEEP * 0.8
            ex, ey = P(E.real, E.imag)
            for kk in range(3):
                a_r = age - 0.12 * kk
                if 0 < a_r < 1.2:
                    c.ring(ex, ey, w * (0.05 + 0.40 * smooth(a_r / 1.2)), GOLD, width=4, alpha=0.7 * (1 - a_r / 1.2))

        # the rule, literally: a + b = c (pops each step)
        fs = w * 0.075
        k_eq = min(1 + done + (1 if p_new > 0 else 0), N - 1) if done < N - 2 else N - 1
        if s <= 0.0:
            eq = "1 + 1 = ?"
            pe = 0.0
        else:
            eq = f"{F[k_eq - 2]:,} + {F[k_eq - 1]:,} = {F[k_eq]:,}"
            pe = math.exp(-((p_new if done < N - 2 else 1.0) * 1.0) / 0.25) if t < tr else 0.0
        rev = smooth((t - tr - T_SWEEP * 0.8) / 0.4) * out if t >= tr else 0.0
        c.text_centered(eq, h * 0.700, size=fs * (1 + 0.18 * pe), color=(1, 1, 1), alpha=1 - rev, max_w=w * 0.94)
        kr = max(2, k_eq) if s > 0 else 1
        if kr >= 2:
            r, m = ratio_str(F, kr)
            self.ratio_line(f"{F[kr]:,} / {F[kr - 1]:,} = ", r, m, h * 0.760, fs * 0.55, t, 1 - rev)
        else:
            self.ratio_line("1 / 1 = ", "1.0000000000", 1, h * 0.760, fs * 0.55, t, 1.0)
        if MELODY and kr >= 2 and rev < 0.99:                 # the melody, visible: F(n) mod 7 -> a note
            deg = F[kr] % 7
            c.text_centered(f"{F[kr]:,} mod 7 = {deg}  →  ♪ {NOTE_NAMES[deg]}", h * 0.800, size=fs * 0.60,
                            color=(0.55, 1.0, 0.70), alpha=1 - rev, max_w=w * 0.94)
        if rev > 0.01:
            c.glow(w / 2, h * 0.715, h * 0.03, GOLD, strength=0.18 * rev, reach=2.6)
            c.text_centered("φ = 1.6180339887", h * 0.735, size=fs * (0.9 + 0.25 * rev), color=GOLD, alpha=rev)
        c.text_centered("FAMOUS NUMBERS · FIBONACCI", h * 0.208, size=h * 0.015, color=GOLD, alpha=0.8)
        if rule:
            c.caption(rule, alpha=1.0, layout=L)
        c.watermark(L)

    def ratio_line(self, head, r, m, y, size, t, alpha):
        """'21 ÷ 13 = 1.6153846154' — digits matching phi in gold, each POPS as it locks."""
        c = self.canvas
        ctx = c.ctx
        c._font(size, True)
        wh, wr = ctx.text_extents(head).x_advance, ctx.text_extents(r).x_advance
        scale = min(1.0, self.L.w * 0.94 / (wh + wr))
        size *= scale
        c._font(size, True)
        wh, wr = ctx.text_extents(head).x_advance, ctx.text_extents(r).x_advance
        x = self.L.w / 2 - (wh + wr) / 2
        ctx.set_source_rgba(0.80, 0.82, 0.92, alpha)
        ctx.move_to(x, y)
        ctx.show_text(head)
        x += wh
        for i, ch in enumerate(r):
            c._font(size, True)
            adv = ctx.text_extents(ch).x_advance
            gold = i < m
            tl = self.sim["lock"].get(i)
            pop = math.exp(-(t - tl) / 0.12) if (gold and tl is not None and tl <= t < self.sim["t_run"] + 0.5) else 0.0
            if pop > 0.02:
                c.glow(x + adv / 2, y - size * 0.35, size * 0.32, GOLD, strength=0.5 * pop * alpha, reach=2.5)
            c._font(size * (1 + 0.55 * pop), True)
            px = x + adv / 2 - ctx.text_extents(ch).x_advance / 2
            ctx.set_source_rgba(*(GOLD if gold else (1, 1, 1)), alpha)
            ctx.move_to(px, y)
            ctx.show_text(ch)
            x += adv


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
    walker = audio.ScaleWalker(root_midi=60, scale=audio.PENTA_MAJOR, span=14, pattern="up")
    out, locked = [], 1
    for i, t in enumerate(sim["starts"]):
        note = SCALE[sim["F"][i + 2] % 7] + 12 if MELODY else walker.next()
        out.append({"t": round(t, 4), "note": note, "gain": round(0.40 + 0.14 * i / N, 3),
                    "x": layout.w / 2})
        if MELODY:                                                    # a soft bass note under it
            out.append({"t": round(t, 4), "note": SCALE[sim["F"][i + 2] % 7] - 12, "gain": 0.22, "x": layout.w / 2})
        _, m = ratio_str(sim["F"], i + 2)
        if m > locked and m >= 3:
            out.append({"t": round(t + 0.06, 4), "note": 86 if m % 2 else 88, "gain": 0.24, "x": layout.w / 2})
        locked = max(locked, m)
    tr = sim["t_run"]
    for j, note in enumerate((60, 64, 67, 72, 76, 79, 84)):          # sweep along the spiral
        out.append({"t": round(tr + 0.11 * j, 4), "note": note, "gain": 0.30, "x": layout.w / 2})
    for j, note in enumerate((48, 55, 60, 64, 67)):                  # the reveal chord
        out.append({"t": round(tr + T_SWEEP * 0.8 + 0.05 * j, 4), "note": note, "gain": 0.44, "x": layout.w / 2})
    t_back = tr + T_SWEEP + T_HOLD
    for j, note in enumerate((79, 76, 72, 69, 67)):
        out.append({"t": round(t_back + 0.05 + 0.24 * j, 4), "note": note, "gain": 0.22, "x": layout.w / 2})
    return sorted(out, key=lambda e: e["t"])


def _worker(o, sim, label, rule):
    layout = get_layout(o)
    name = f"{SCENE}_{label}_{layout.tag}"
    video = studio.OUT_DIR / f"{name}_silent.mp4"
    d = render(layout, sim, video, rule)
    pad = kit.loop_pad(sim["nf"] / FPS, ((48, 1.0), (55, 0.7), (60, 0.45), (64, 0.3)), gain=0.015)
    kit.deliver_loop(SCENE, name, layout, video, build_events(sim, layout), d,
                     voice="piano" if MELODY else "glassharp", bed=pad, peak_db=-6.0 if MELODY else None)


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
    print(f"[{SCENE}] {sim['t_loop']:.2f}s run={sim['t_run']:.2f}s locks={ {k: round(v, 2) for k, v in sim['lock'].items()} }")
    kit.fan_out(_worker, (sim, label, rule), SCENE)


if __name__ == "__main__":
    main()
