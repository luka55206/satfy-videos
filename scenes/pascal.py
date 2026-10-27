"""PASCAL — "Colour only the odd numbers in Pascal's triangle…" → a Sierpinski triangle appears.

Row r, position k holds C(r, k); it is odd exactly when k & (r − k) == 0 (Lucas). Odd cells glow gold, even cells stay
dim. Timeline: 0–0.9 s the finished 64-row triangle (payoff first) · 0.9–1.5 zoom into the top "1" · the rows
rebuild, the first ones slowly with their numbers written in, the camera pulling out as the rows add up · the full
Sierpinski triangle holds = frame 0 (loop).
Audio (original): one note per new row (pitch climbs; the number of odd cells, 2^popcount(r), sets the chord size),
a reveal chord.
"""
import math
import sys
from pathlib import Path

import cairo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib import kit, studio  # noqa: E402
from lib.kit import DT, FPS, arg, smooth  # noqa: E402
from lib.layouts import get_layout  # noqa: E402
from lib.studio import Canvas, VideoWriter  # noqa: E402

SCENE = "pascal"
ROWS = 64
T_COLD, T_ZIN, T_START = 0.9, 1.5, 1.6
T_SLOW = 6.4                              # rows 1..9 one by one (numbers readable)
N_SLOW = 9
T_FULL = 13.4
T_LOOP = 15.0
GOLD = (1.0, 0.80, 0.35)


def binom_row(r):
    row = [1]
    for k in range(r):
        row.append(row[-1] * (r - k) // (k + 1))
    return row


def rows_at(t):
    """How many rows (1..ROWS) are built at time t."""
    if t < T_START or t >= T_FULL:
        return ROWS
    if t < T_SLOW:
        return 1 + int((t - T_START) / (T_SLOW - T_START) * N_SLOW)
    u = (t - T_SLOW) / (T_FULL - T_SLOW)
    return min(ROWS, N_SLOW + 1 + int((ROWS - N_SLOW - 1) * u ** 1.5))


def row_time(r):
    """When row r (0-based) appears during the rebuild."""
    if r <= N_SLOW:
        return T_START + r * (T_SLOW - T_START) / N_SLOW
    lo, hi = T_SLOW, T_FULL
    for _ in range(40):
        mid = (lo + hi) / 2
        if rows_at(mid) > r:
            hi = mid
        else:
            lo = mid
    return hi


def simulate():
    return {"nf": int(round(T_LOOP * FPS))}


class Scene:
    def __init__(self, layout, sim):
        self.L, self.sim = layout, sim
        self.canvas = Canvas(layout.w, layout.h, studio.render_scale())

    def view(self, t):
        """Visible rows (zoom): 64 in the cold open, ~4 right after the zoom-in, then follows the build."""
        if t < T_COLD:
            return ROWS
        if t < T_START:
            u = smooth((t - T_COLD) / (T_ZIN - T_COLD))
            return math.exp(math.log(ROWS) + (math.log(4.5) - math.log(ROWS)) * u)
        if t >= T_FULL:
            return ROWS
        return max(4.5, min(ROWS, rows_at(t) + 1.5 + 0.0))

    def draw(self, f, rule):
        L, c = self.L, self.canvas
        w, h = L.w, L.h
        t = f * DT
        ctx = c.ctx
        g = cairo.RadialGradient(w / 2, h * 0.45, 0, w / 2, h * 0.45, max(w, h) * 0.7)
        g.add_color_stop_rgb(0.0, 0.07, 0.06, 0.12)
        g.add_color_stop_rgb(1.0, 0.01, 0.01, 0.02)
        ctx.set_source(g)
        ctx.paint()
        V = self.view(t)
        top, hgt = h * 0.235, h * 0.46
        d = min(hgt / (V * 0.866), w * 0.92 / V)                 # cell pitch
        cx = w / 2
        nrow = rows_at(t) if T_START <= t < T_FULL else (ROWS if t < T_COLD or t >= T_FULL else 1)
        show_num = d > w * 0.055
        for r in range(nrow):
            y = top + (r + 0.5) * d * 0.866
            if y > h * 0.72:
                break
            age = t - row_time(r) if T_START <= t < T_FULL + 0.5 else 9.0
            pop = math.exp(-max(0.0, age) / 0.15) if age < 1 else 0.0
            vals = binom_row(r) if show_num and r < 20 else None
            for k in range(r + 1):
                x = cx + (k - r / 2) * d
                if x < -d or x > w + d:
                    continue
                odd = (k & (r - k)) == 0
                rad = d * 0.46 * (1 + 0.25 * pop)
                if odd:
                    if d > 6:
                        c.glow(x, y, rad, GOLD, strength=0.35, reach=2.2)
                    c.circle(x, y, rad, GOLD, alpha=0.95)
                else:
                    c.circle(x, y, rad, (0.22, 0.22, 0.32), alpha=0.8)
                if vals is not None:
                    txt = str(vals[k])
                    fs = min(d * 0.42, d * 0.95 / max(1, len(txt)) * 1.6)
                    c.text_centered(txt, y + fs * 0.36, size=fs, color=(0.08, 0.06, 0.02) if odd else (0.85, 0.86, 0.95),
                                    alpha=0.95, cx=x)
        # text
        if t < T_START or t >= T_FULL:
            a = 1.0 if t < T_COLD else (max(0.0, 1 - (t - T_COLD) / 0.4) if t < T_START else smooth((t - T_FULL) / 0.4))
            c.text_centered("ONLY THE ODD NUMBERS", h * 0.765, size=w * 0.075, color=GOLD, alpha=a)
            c.text_centered(f"{ROWS} rows of Pascal's triangle → a Sierpinski triangle", h * 0.80, size=w * 0.031,
                            color=(0.88, 0.89, 0.95), alpha=0.9 * a, bold=False)
        elif t < T_SLOW + 0.3:
            r = min(nrow - 1, N_SLOW)
            vals = binom_row(r)
            c.text_centered(f"row {r}:", h * 0.75, size=w * 0.05, color=GOLD, alpha=1.0)
            c.text_centered("   ".join(map(str, vals)), h * 0.79, size=w * 0.04, color=(0.95, 0.95, 1.0), alpha=0.95,
                            bold=False, max_w=w * 0.94)
        else:
            c.text_centered(f"rows: {nrow}", h * 0.765, size=w * 0.07, color=(0.95, 0.95, 1.0), alpha=1.0)
            c.text_centered("gold = odd · dark = even", h * 0.80, size=w * 0.034, color=(0.75, 0.78, 0.88), alpha=0.85,
                            bold=False)
        c.text_centered("each number = the two above it added", h * 0.205, size=h * 0.016, color=GOLD, alpha=0.9)
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


PENTA = [0, 2, 4, 7, 9]


def build_events(sim, layout):
    x = layout.w / 2
    out = [{"t": 0.012 * j, "note": m, "gain": 0.26, "x": x} for j, m in enumerate((48, 55, 60, 64, 67))]
    for j in range(6):
        out.append({"t": round(T_COLD + 0.09 * j, 4), "note": 91 - 3 * j, "gain": 0.12, "x": x})
    for r in range(ROWS):
        tr = row_time(r)
        if tr >= T_FULL:
            break
        odd = bin(r).count("1")
        k = min(14, r // 3 if r > N_SLOW else r)
        base = 60 + 12 * (k // 5) + PENTA[k % 5]
        n_notes = min(3, odd) if r <= N_SLOW else 1
        for j in range(n_notes):
            out.append({"t": round(tr + 0.02 * j, 4), "note": base + (0, 4, 7)[j], "gain": 0.24 if r <= N_SLOW else 0.12,
                        "x": layout.w * (0.3 + 0.4 * (r % 2))})
    for j, m in enumerate((48, 55, 60, 64, 67, 72)):
        out.append({"t": round(T_FULL + 0.05 * j, 4), "note": m, "gain": 0.28, "x": x})
    return sorted(out, key=lambda e: e["t"])


def _worker(o, sim, label, rule):
    layout = get_layout(o)
    name = f"{SCENE}_{label}_{layout.tag}"
    video = studio.OUT_DIR / f"{name}_silent.mp4"
    d = render(layout, sim, video, rule)
    pad = kit.loop_pad(T_LOOP, ((48, 1.0), (55, 0.7), (60, 0.45), (64, 0.3)), gain=0.013)
    kit.deliver_loop(SCENE, name, layout, video, build_events(sim, layout), d, voice="glassharp", bed=pad,
                     peak_db=-6.0)


def main():
    label, rule = arg("--label", "v1"), arg("--rule", "")
    studio.OUT_DIR.mkdir(exist_ok=True)
    sim = simulate()
    if kit.has("--still"):
        layout = get_layout(kit.orients()[0])
        f = int(arg("--frame", "0"))
        png = studio.OUT_DIR / f"{SCENE}_{label}_f{f}_{layout.tag}.png"
        render(layout, sim, png, rule, still_frame=f)
        print(f"[{SCENE}] -> {png}")
        return
    print(f"[{SCENE}] {T_LOOP:.1f}s")
    kit.fan_out(_worker, (sim, label, rule), SCENE)


if __name__ == "__main__":
    main()
