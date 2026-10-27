"""FIB SPIRAL — Fibonacci squares build the golden spiral; the ratio locks onto phi.

Each new square's side is the sum of the two before it (1, 1, 2, 3, 5, 8, ...). Squares are
added around the growing rectangle (down, right, up, left, ...), each carrying its number
and a quarter of the golden spiral. The camera zooms OUT about the spiral's eye (the fixed
point of "rotate 90°, scale by phi"), so every new square lands at the same screen size
and the build looks endless. Squares arrive faster and faster (the escalation rule). The
HUD shows F(n) and the ratio F(n)/F(n-1); its digits turn gold as they lock onto
phi = 1.6180339887... NONSTOP LOOP (v2, owner): after the last square the camera dives back
into the eye while the squares unbuild in a fast smooth rewind, landing exactly on frame 0.

Reference: youtube.com/shorts/8onsyBwyVHw (Recamán's sequence as arcs on a number line).
Taken: only the FORMAT idea (a number sequence drawing itself under a rule caption).
Different maths (Fibonacci), different picture (square tiling + golden spiral + ratio),
our palette, HUD, caption and synthesised sound.

Audio (original synthesis only): one glass-harp note per new square (pentatonic, rising),
a soft chime each time another digit of phi locks, a chord at the end, a quiet pad.

    ./run.ps1 -Scene fib_spiral -Fast -Still -Frame 600
    ./run.ps1 -Scene fib_spiral -Fast
"""
import math
import sys
from pathlib import Path

import cairo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib import audio, kit, studio  # noqa: E402
from lib.kit import DT, FPS, arg, smooth  # noqa: E402
from lib.layouts import get_layout  # noqa: E402
from lib.studio import Canvas, VideoWriter  # noqa: E402
import numpy as np  # noqa: E402

SCENE = "fib_spiral"
PHI = (1 + 5 ** 0.5) / 2
PHI_STR = "1.6180339887"
N = 40                                   # squares (F(40) = 102,334,155)
D0, DK, DMIN = 1.25, 0.88, 0.22          # step length: first, decay per step, floor
HOLD_S, REW_S = 0.5, 3.0                 # nonstop loop: brief hold, then dive back to square 1
FILLS = [(1.00, 0.40, 0.60), (0.70, 0.45, 1.00), (0.25, 0.85, 0.90), (1.00, 0.80, 0.45)]
GOLD = (1.0, 0.82, 0.45)
DIRS = ["down", "right", "up", "left"]
ARC0 = {"down": 180, "right": 270, "up": 0, "left": 90}   # start angle (deg, y up), CCW 90°


def fib(n):
    a, b = 1, 1
    out = [1, 1]
    while len(out) < n:
        a, b = b, a + b
        out.append(b)
    return out[:n]


def tiling(n):
    """World squares (x0, y0, size, dir, arc centre, arc start angle), y up."""
    F = fib(n)
    sq = []
    x0, y0, x1, y1 = 0, 0, 1, 1
    sq.append((0, 0, 1, "down", (1, 1), (0, 0, 1, 1)))
    for k in range(1, n):
        s, d = F[k], DIRS[k % 4]
        if d == "right":
            q = (x1, y0); x1 += s
            c = (q[0], q[1] + s)
        elif d == "up":
            q = (x0, y1); y1 += s
            c = (q[0], q[1])
        elif d == "left":
            q = (x0 - s, y0); x0 -= s
            c = (q[0] + s, q[1])
        else:
            q = (x0, y0 - s); y0 -= s
            c = (q[0] + s, q[1] + s)
        sq.append((q[0], q[1], s, d, c, (x0, y0, x1, y1)))
    return F, sq


def eye(sq):
    """Fixed point of the similarity square k -> k+1 (rotate 90° CCW, scale phi)."""
    k = len(sq) - 6
    a = complex(*sq[k][4])
    b = complex(*sq[k + 1][4])
    return (b - PHI * 1j * a) / (1 - PHI * 1j)


def simulate():
    F, sq = tiling(N)
    starts, t = [], 0.0
    for k in range(N):
        starts.append(t)
        t += max(DMIN, D0 * DK ** k)
    t_draw = t
    nf = int(round((t_draw + HOLD_S + REW_S) * FPS))
    return {"F": F, "sq": sq, "starts": starts, "t_draw": t_draw, "nf": nf, "eye": eye(sq)}


def step_at(sim, t):
    """Fractional step: k + progress through square k. After the build (and a short hold) it
    runs back from N to 0, so the camera dives into the eye while the squares unbuild, landing
    exactly on frame 0's state: the loop never stops moving."""
    st = sim["starts"]
    t_rew = sim["t_draw"] + HOLD_S
    if t >= t_rew:
        return N * (1.0 - smooth((t - t_rew) / REW_S))
    if t >= sim["t_draw"]:
        return float(N)
    k = max(i for i in range(N) if st[i] <= t)
    end = st[k + 1] if k + 1 < N else sim["t_draw"]
    return k + (t - st[k]) / (end - st[k])


def ratio_digits(F, k):
    """How many characters of F(k)/F(k-1), printed to 10 decimals, match phi."""
    if k < 1:
        return "1.0000000000", 1
    r = f"{F[k] / F[k - 1]:.10f}"
    m = 0
    while m < len(r) and r[m] == PHI_STR[m]:
        m += 1
    return r, m


class Scene:
    def __init__(self, layout, sim):
        self.L, self.sim = layout, sim
        self.canvas = Canvas(layout.w, layout.h, studio.render_scale())
        self.vertical = layout.h > layout.w
        self.cy = layout.h * (0.47 if self.vertical else 0.5)
        # the whole rectangle must fit, seen from the eye: half-extents available on screen
        self.half_w = layout.w * (0.46 if self.vertical else 0.30)
        self.half_h = layout.h * (0.235 if self.vertical else 0.36)

    def fit(self, k):
        """px per world unit that fits rectangle k around the eye."""
        x0, y0, x1, y1 = self.sim["sq"][k][5]
        E = self.sim["eye"]
        dx = max(E.real - x0, x1 - E.real)
        dy = max(E.imag - y0, y1 - E.imag)
        return min(self.half_w / dx, self.half_h / dy)

    def draw(self, f, rule):
        sim, L, c = self.sim, self.L, self.canvas
        t = f * DT
        F, sq, E = sim["F"], sim["sq"], sim["eye"]
        s = step_at(sim, t)
        k_now = min(int(s), N - 1)
        # camera: newest square ~fitw px; scale eases between steps (log-interpolated)
        kk = min(k_now, N - 1)
        frac = smooth(min(1.0, (s - k_now) / 0.6)) if s < N else 1.0
        l0 = math.log(self.fit(max(kk - 1, 0)))
        l1 = math.log(self.fit(kk))
        k_px = math.exp(l0 + (l1 - l0) * frac)

        w, h = L.w, L.h
        g = cairo.RadialGradient(w / 2, self.cy, 0, w / 2, self.cy, max(w, h) * 0.75)
        g.add_color_stop_rgb(0.0, 0.05, 0.04, 0.10)
        g.add_color_stop_rgb(1.0, 0.01, 0.01, 0.03)
        c.ctx.set_source(g)
        c.ctx.paint()

        def P(x, y):
            return w / 2 + (x - E.real) * k_px, self.cy - (y - E.imag) * k_px

        ctx = c.ctx
        arc_pts = []
        for k in range(min(k_now + 1, N)):
            x0, y0, side, d, cen, _ = sq[k]
            side_px = side * k_px
            if side_px < 0.6:
                continue
            p = 1.0 if k < k_now else min(1.0, s - k_now)
            pa = smooth(p / 0.55)                       # square fades in
            col = FILLS[k % 4]
            ax, ay = P(x0, y0 + side)                   # top-left in screen
            alpha = 1.0
            ctx.rectangle(ax, ay, side_px, side_px)
            ctx.set_source_rgba(*col, 0.13 * pa * alpha)
            ctx.fill_preserve()
            ctx.set_source_rgba(*col, 0.75 * pa * alpha)
            ctx.set_line_width(2.0)
            ctx.stroke()
            # spiral quarter arc, drawn progressively
            pa_arc = smooth(min(1.0, p / 0.9))
            a0 = math.radians(ARC0[d])
            n_s = 24
            pts = []
            for i in range(n_s + 1):
                a = a0 + math.pi / 2 * pa_arc * i / n_s
                pts.append(P(cen[0] + side * math.cos(a), cen[1] + side * math.sin(a)))
            arc_pts.append((pts, alpha))
            # number label
            if side_px > 34:
                fs = min(side_px * 0.30, h * 0.06)
                txt = f"{F[k]:,}"
                c.text_centered(txt, ay + side_px * 0.5 + fs * 0.35, size=fs, color=(1, 1, 1),
                                alpha=0.85 * pa * alpha * min(1.0, (side_px - 34) / 40),
                                bold=True, cx=ax + side_px * 0.5, max_w=side_px * 0.86)
        for pts, alpha in arc_pts:
            c.polylines([pts], GOLD, width=12, alpha=0.10 * alpha)
            c.polylines([pts], GOLD, width=4, alpha=0.95 * alpha)
        if arc_pts and s < N:
            tip = arc_pts[-1][0][-1]
            c.glow(*tip, 7, GOLD, strength=0.6, reach=4.0)
            c.circle(*tip, 6, (1, 1, 1), alpha=0.95)

        # HUD
        hud = 1.0                                       # same at frame 0 and at the seam
        kh = min(k_now, N - 1)
        fs = w * (0.050 if self.vertical else 0.024)
        y_f, y_r = (h * 0.200, h * 0.775) if self.vertical else (h * 0.08, h * 0.94)
        c.text_centered(f"F({kh + 1}) = {F[kh]:,}", y_f, size=fs, color=(1, 1, 1), alpha=hud, bold=True)
        r, m = ratio_digits(F, kh)
        self.ratio_line(r, m, y_r, fs * 0.95, hud)
        if rule:
            c.caption(rule, alpha=hud, layout=L)
        c.watermark(L)

    def ratio_line(self, r, m, y, size, alpha):
        """'ratio = 1.6180339887' with the digits that match phi in gold."""
        c = self.canvas
        ctx = c.ctx
        label = "ratio = "
        c._font(size, True)
        wl = ctx.text_extents(label).x_advance
        wr = ctx.text_extents(r).x_advance
        x = self.L.w / 2 - (wl + wr) / 2
        for txt, col in ((label, (0.85, 0.85, 0.92)), (r[:m], GOLD), (r[m:], (1, 1, 1))):
            if not txt:
                continue
            ctx.set_source_rgba(0, 0, 0, 0.5 * alpha)
            ctx.move_to(x + 2, y + 2)
            ctx.show_text(txt)
            ctx.set_source_rgba(*col, alpha)
            ctx.move_to(x, y)
            ctx.show_text(txt)
            x += ctx.text_extents(txt).x_advance


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
    walker = audio.ScaleWalker(root_midi=60, scale=audio.PENTA_MAJOR, span=12, pattern="updown")
    F = sim["F"]
    out, locked = [], 1
    for k, t in enumerate(sim["starts"]):
        out.append({"t": round(t + 0.02, 4), "note": walker.next(), "gain": round(0.40 + 0.2 * k / N, 3),
                    "x": round(layout.w * (0.5 + 0.25 * math.sin(k * math.pi / 2)), 1)})
        _, m = ratio_digits(F, k)
        if m > locked and m >= 3:                      # another digit of phi locked: high chime
            out.append({"t": round(t + 0.09, 4), "note": 86 if m % 2 else 88, "gain": 0.32,
                        "x": layout.w / 2})
        locked = max(locked, m)
    t_end = sim["t_draw"]
    for j, note in enumerate((48, 55, 60, 64, 67)):
        out.append({"t": round(t_end + 0.06 * j, 4), "note": note, "gain": 0.45, "x": layout.w / 2})
    # the dive back: one soft falling note each time a square unbuilds (thinned to ~16/s)
    fwd = [e["note"] for e in out if e["note"] < 80][:N]
    t_rew = sim["t_draw"] + HOLD_S
    last = -1e9
    for f in range(int(t_rew * FPS), sim["nf"]):
        t = f * DT
        s0, s1 = step_at(sim, t), step_at(sim, t + DT)
        for k in range(int(s0), int(s1), -1):
            if 0 < k <= len(fwd) and t - last >= 0.06:
                last = t
                out.append({"t": round(t, 4), "note": fwd[k - 1], "gain": 0.30, "x": layout.w / 2})
    return sorted(out, key=lambda e: e["t"])


def pad(sim):
    return kit.loop_pad(sim["nf"] / FPS, ((48, 1.0), (55, 0.7), (60, 0.45), (64, 0.3)), gain=0.016)


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
        f = int(arg("--frame", "600"))
        png = studio.OUT_DIR / f"{SCENE}_{label}_f{f}_{layout.tag}.png"
        render(layout, sim, png, rule, still_frame=f)
        print(f"[{SCENE}] -> {png}")
        return
    ev = build_events(sim, get_layout("vertical"))
    print(f"[{SCENE}] {sim['nf'] / FPS:.2f}s draw={sim['t_draw']:.2f}s "
          f"per5s={kit.density_report(ev, sim['t_draw'])}")
    kit.fan_out(_worker, (sim, label, rule), SCENE)


if __name__ == "__main__":
    main()
