"""PHI ANY — pick ANY two numbers, keep adding the last two: the ratio still becomes phi.

Built from the channel's winner (fib_spiral, 69.5% stayed-to-watch): a famous constant, frame 0
states the game (three different starts, three different ratios), a counter that changes every
step, a visible finish line (digits turning gold until 1.6180339887), ~16 s, a smooth rewind loop.
Nameable change vs fib_spiral: it is not just Fibonacci; ANY start converges to phi.

Three sequences: (1, 1) the classic, (7, 2) a random start, (100, 3) a silly start. Each step adds
the next term to all three; a live graph plots each ratio a(n+1)/a(n) against the step, with the
dashed gold line y = phi. The graph ZOOMS in on phi as the error shrinks (live "zoom xN"),
so the newest zig-zag always fills the box and something moves until the last digit; the ratios their readouts turn gold
digit by digit. Hold, then a quick rewind to step 0 (nonstop loop).

Audio (original synthesis only): a glass-harp note per step (rising, faster), a chime whenever a
sequence locks another digit, a chord when all three are gold, falling notes on the rewind, a pad.
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

SCENE = "phi_any"
PHI = (1 + 5 ** 0.5) / 2
PHI_STR = "1.6180339887"
STARTS = [((1, 1), (1.00, 0.80, 0.35)), ((7, 2), (0.30, 0.85, 0.95)), ((100, 3), (1.00, 0.45, 0.65))]
N_STEPS = 30
T_RUN, T_HOLD, T_BACK = 10.5, 2.6, 1.4        # v2: faster start; hold = the merge finale
T_MERGE = T_RUN + 0.2
T_LOOP = T_RUN + T_HOLD + T_BACK
GOLD = (1.0, 0.82, 0.40)
GREY = (0.75, 0.78, 0.88)


def sequences():
    out = []
    for (a, b), _ in STARTS:
        s = [a, b]
        while len(s) < N_STEPS + 2:
            s.append(s[-1] + s[-2])
        out.append(s)
    return out


SEQ = sequences()


def ratio(seq, k):
    return seq[k + 1] / seq[k]


def step_at(t):
    """Fractional step 0..N: slow first, then faster and faster; rewind at the end."""
    if t < T_RUN:
        u = t / T_RUN
        return N_STEPS * (0.75 * u + 0.25 * u ** 2.0)    # first step at ~0.5 s
    if t < T_RUN + T_HOLD:
        return float(N_STEPS)
    return N_STEPS * (1.0 - smooth((t - T_RUN - T_HOLD) / T_BACK))


def digits(r):
    s = f"{r:.10f}"
    m = 0
    while m < len(s) and s[m] == PHI_STR[m]:
        m += 1
    return s, m


def lock_times():
    """[seq][char index] -> time that character first turns gold (for the digit pop)."""
    out = [dict() for _ in SEQ]
    prev = [0] * len(SEQ)
    for f in range(int(T_RUN * FPS) + 1):
        t = f * DT
        k = min(int(step_at(t)), N_STEPS)
        for j, seq in enumerate(SEQ):
            _, m = digits(ratio(seq, k))
            for i in range(prev[j], m):
                out[j][i] = t
            prev[j] = max(prev[j], m)
    return out


LOCK_T = lock_times()


def simulate():
    return {"nf": int(round(T_LOOP * FPS))}


class Scene:
    def __init__(self, layout, sim):
        self.L, self.sim = layout, sim
        self.canvas = Canvas(layout.w, layout.h, studio.render_scale())
        w, h = layout.w, layout.h
        self.box = (w * 0.12, h * 0.25, w * 0.93, h * 0.565)

    def draw(self, f, rule):
        L, c = self.L, self.canvas
        w, h = L.w, L.h
        t = f * DT
        s = step_at(t)
        k_now = int(s)
        ctx = c.ctx
        g = cairo.RadialGradient(w / 2, h * 0.45, 0, w / 2, h * 0.45, max(w, h) * 0.7)
        g.add_color_stop_rgb(0.0, 0.06, 0.05, 0.10)
        g.add_color_stop_rgb(1.0, 0.01, 0.01, 0.02)
        ctx.set_source(g)
        ctx.paint()
        x0, y0, x1, y1 = self.box
        # ZOOMING graph: x shows the last X_WIN steps, y is a window around phi that shrinks with the
        # current error, so the newest zig-zag always fills the box (older swings run off the edges)
        X_WIN = 2.6
        xs0 = max(0.0, s - X_WIN)
        xs1 = xs0 + X_WIN
        half = self.half_span(s)

        def P(n, r):
            return (x0 + (x1 - x0) * (n - xs0) / (xs1 - xs0),
                    (y0 + y1) / 2 - (y1 - y0) / 2 * (r - PHI) / half)

        ctx.save()
        ctx.rectangle(x0, y0, x1 - x0, y1 - y0)
        ctx.clip()
        grid = [(P(n, PHI)[0], y0, P(n, PHI)[0], y1) for n in range(int(xs0), int(xs1) + 2)]
        c.lines(grid, GREY, width=1, alpha=0.07)
        py = P(0, PHI)[1]
        ctx.set_dash([14, 10])
        c.lines([(x0, py, x1, py)], GOLD, width=2.5, alpha=0.8)
        ctx.set_dash([])
        mg = smooth((t - T_MERGE) / 0.6) * (1.0 - smooth((t - T_RUN - T_HOLD) / 0.5))
        for seq, (_, col) in zip(SEQ, STARTS):
            if mg > 0.98:
                continue
            k_hi = min(k_now, N_STEPS)
            pts = [P(k, ratio(seq, k)) for k in range(max(0, int(xs0)), k_hi + 1)]
            if k_now < N_STEPS:
                fr = s - k_now
                a, b = P(k_now, ratio(seq, k_now)), P(k_now + 1, ratio(seq, k_now + 1))
                pts.append((a[0] + (b[0] - a[0]) * fr, a[1] + (b[1] - a[1]) * fr))
            pts = [(x, min(max(y, y0 - 4000), y1 + 4000)) for x, y in pts]
            if len(pts) == 1:
                pts.append((pts[0][0] + 0.1, pts[0][1]))
            c.polylines([pts], col, width=16, alpha=0.10 * (1 - mg))
            c.polylines([pts], col, width=4.5, alpha=0.95 * (1 - mg))
            for q in pts[:-1]:
                c.circle(*q, 4, col, alpha=0.9 * (1 - mg))
            c.glow(*pts[-1], 7, col, strength=0.6 * (1 - mg), reach=4)
            c.circle(*pts[-1], 6.5, (1, 1, 1), alpha=0.95 * (1 - mg))
        if mg > 0.01:                                         # the three lines become ONE golden line
            c.lines([(x0, py, x1, py)], GOLD, width=40, alpha=0.12 * mg)
            c.lines([(x0, py, x1, py)], GOLD, width=9, alpha=0.95 * mg)
        ctx.restore()
        if mg > 0.01:                                         # burst rings from the line's centre
            age = t - T_MERGE - 0.3
            for kk in range(3):
                a_r = age - 0.12 * kk
                if 0 < a_r < 1.2:
                    c.ring((x0 + x1) / 2, py, w * (0.06 + 0.45 * smooth(a_r / 1.2)), GOLD, width=4,
                           alpha=0.7 * (1 - a_r / 1.2))
        c.lines([(x0, y0, x1, y0), (x0, y1, x1, y1), (x0, y0, x0, y1), (x1, y0, x1, y1)], GREY,
                width=1.5, alpha=0.35)
        c.text_centered("φ", py + h * 0.006, size=h * 0.022, color=GOLD, cx=x0 - w * 0.04)
        zoom = 1.6 / half
        c.text_centered(f"zoom ×{zoom:,.0f}" if zoom >= 2 else "zoom ×1", y0 - h * 0.012, size=h * 0.015,
                        color=GREY, alpha=0.85, bold=False, cx=x1 - w * 0.12)

        # readouts: start, latest term, ratio with gold digits
        kk = min(k_now, N_STEPS)
        fs = h * 0.024
        for j, (seq, ((a, b), col)) in enumerate(zip(SEQ, STARTS)):
            y = h * (0.640 + 0.050 * j) + (h * 0.050 * (1 - j)) * mg      # the rows slide together
            c.text_centered(f"{a}, {b} →", y, size=fs * 0.85, color=col, alpha=1 - mg, cx=w * 0.17,
                            max_w=w * 0.26)
            r, m = digits(ratio(seq, kk))
            if mg < 0.99:
                self.ratio_text(r, m, w * 0.62 - w * 0.12 * mg, y, fs, t, j, 1 - mg)
        if mg > 0.01:                                        # ...into one big result
            c.glow(w / 2, h * 0.690, h * 0.03, GOLD, strength=0.18 * mg, reach=2.6)
            c.text_centered("φ = 1.6180339887", h * 0.700, size=fs * (1.0 + 0.7 * mg), color=GOLD, alpha=mg)
        c.text_centered(f"step {kk}", h * 0.795, size=h * 0.020, color=GREY, alpha=0.85 * (1 - mg), bold=False)
        c.text_centered("FAMOUS NUMBERS · φ", h * 0.208, size=h * 0.015, color=GOLD, alpha=0.75, bold=True)
        if rule:
            c.caption(rule, alpha=1.0, layout=L)
        c.watermark(L)

    @staticmethod
    def half_span(s):
        """Half-height of the y-window around phi: 2.6x the largest error at the current step,
        log-interpolated between steps; floor 4e-11 (all ten decimals gold = the zoom stops)."""
        def err(k):
            k = min(max(k, 0), N_STEPS)
            return max(abs(ratio(seq, k) - PHI) for seq in SEQ)
        k = int(s)
        fr = s - k
        e = math.exp(math.log(max(err(k), 1e-16)) * (1 - fr) + math.log(max(err(k + 1), 1e-16)) * fr)
        return min(max(2.6 * e, 4e-11), 1.7)

    def ratio_text(self, r, m, cx, y, size, t, j, alpha=1.0):
        """Ratio drawn per character; each digit POPS (scale bounce + glow) as it turns gold."""
        c = self.canvas
        ctx = c.ctx
        c._font(size, True)
        x = cx - ctx.text_extents(r).x_advance / 2
        for i, ch in enumerate(r):
            c._font(size, True)
            adv = ctx.text_extents(ch).x_advance
            gold = i < m
            tl = LOCK_T[j].get(i)
            pop = math.exp(-(t - tl) / 0.12) if (gold and tl is not None and tl <= t < T_RUN + T_HOLD) else 0.0
            if pop > 0.02:
                c.glow(x + adv / 2, y - size * 0.35, size * 0.32, GOLD, strength=0.5 * pop * alpha, reach=2.5)
            c._font(size * (1 + 0.55 * pop), True)
            px = x + adv / 2 - ctx.text_extents(ch).x_advance / 2
            ctx.set_source_rgba(0, 0, 0, 0.5 * alpha)
            ctx.move_to(px + 2, y + 2)
            ctx.show_text(ch)
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
    walker = audio.ScaleWalker(root_midi=62, scale=audio.PENTA_MAJOR, span=12, pattern="updown")
    out, locked = [], [1, 1, 1]
    ts = np.arange(int(T_RUN * FPS) + 1) * DT
    k_prev = 0
    all_gold_t = None
    for t in ts:
        k = int(step_at(t))
        if k > k_prev:
            out.append({"t": round(float(t), 4), "note": walker.next(), "gain": round(0.36 + 0.18 * k / N_STEPS, 3),
                        "x": layout.w / 2})
            for j, seq in enumerate(SEQ):
                _, m = digits(ratio(seq, k))
                if m > locked[j] and m >= 3:
                    out.append({"t": round(float(t) + 0.06 + 0.03 * j, 4), "note": 86 + 2 * j, "gain": 0.22,
                                "x": layout.w / 2})
                locked[j] = max(locked[j], m)
            if all_gold_t is None and min(locked) >= len(PHI_STR):
                all_gold_t = float(t)
            k_prev = k
    t_end = T_MERGE + 0.15
    for j, note in enumerate((50, 57, 62, 66, 69, 74)):
        out.append({"t": round(t_end + 0.12 + 0.06 * j, 4), "note": note, "gain": 0.42, "x": layout.w / 2})
    for j, note in enumerate((78, 74, 71, 69, 66)):
        out.append({"t": round(T_RUN + T_HOLD + 0.05 + 0.28 * j, 4), "note": note, "gain": 0.22, "x": layout.w / 2})
    return sorted(out, key=lambda e: e["t"])


def pad(sim):
    return kit.loop_pad(T_LOOP, ((50, 1.0), (57, 0.7), (62, 0.45), (66, 0.3)), gain=0.015)


def _worker(o, sim, label, rule):
    layout = get_layout(o)
    name = f"{SCENE}_{label}_{layout.tag}"
    video = studio.OUT_DIR / f"{name}_silent.mp4"
    d = render(layout, sim, video, rule)
    kit.deliver_loop(SCENE, name, layout, video, build_events(sim, layout), d,
                     voice="glassharp", bed=pad(sim))


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
    for seq in SEQ:
        k = next((k for k in range(N_STEPS + 1) if digits(ratio(seq, k))[1] >= len(PHI_STR)), None)
        print(f"  start {seq[:2]} all digits at step {k}")
    kit.fan_out(_worker, (sim, label, rule), SCENE)


if __name__ == "__main__":
    main()
