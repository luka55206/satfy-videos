"""FOURIER DRAW — "200 spinning circles draw one word" (series: the next word comes from the comments).

The word's outline (font glyph contours, joined into ONE closed path, resampled by arc length) is turned into a
Fourier series z(t) = Σ c_k e^{2πikt}, k = −100…100. Each term is a circle spinning k times per drawing; chained tip
to tail (largest first), the last tip is a pen that traces the word. Contour-to-contour connectors are drawn faint.
Timeline: 0–T_DRAW draw · hold (the finished word glows) · fast rewind to the empty start = frame 0 (loop).
Audio (original): 16th notes whose pitch follows the pen's height (pentatonic), a chord each time a contour closes,
a falling run on the rewind, soft pad.
"""
import math
import sys
from pathlib import Path

import cairo
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib import kit, studio  # noqa: E402
from lib.kit import DT, FPS, arg, smooth  # noqa: E402
from lib.layouts import get_layout  # noqa: E402
from lib.studio import Canvas, VideoWriter  # noqa: E402

SCENE = "fourier_draw"
WORD = arg("--word", "LOVE")
K = int(arg("--k", "100"))
N = 4096
T_DRAW = float(arg("--tdraw", "12.0"))
T_HOLD = 1.6
T_REW = 1.0
T_LOOP = T_DRAW + T_HOLD + T_REW
GOLD = (1.0, 0.82, 0.40)


def word_path(word):
    """Glyph contours of the word → one closed path (list of complex points) + connector mask + contour ends."""
    s = cairo.ImageSurface(cairo.FORMAT_ARGB32, 10, 10)
    c = cairo.Context(s)
    c.select_font_face("Arial", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    c.set_font_size(100)
    c.move_to(0, 0)
    c.text_path(word)
    contours, cur = [], []
    for kind, pts in c.copy_path_flat():
        if kind == cairo.PATH_MOVE_TO:
            if len(cur) > 2:
                contours.append(cur)
            cur = [complex(pts[0], -pts[1])]
        elif kind == cairo.PATH_LINE_TO:
            cur.append(complex(pts[0], -pts[1]))
        elif kind == cairo.PATH_CLOSE_PATH and cur:
            cur.append(cur[0])
    if len(cur) > 2:
        contours.append(cur)
    pts, conn = [], []
    for i, ct in enumerate(contours):
        pts += ct
        conn += [False] * len(ct)
        nxt = contours[(i + 1) % len(contours)][0]
        pts.append(nxt)                                   # connector to the next contour (wraps to close the loop)
        conn.append(True)
    P = np.array(pts)
    seg = np.abs(np.diff(P))
    cum = np.concatenate([[0], np.cumsum(seg)])
    L = cum[-1]
    u = np.linspace(0, L, N, endpoint=False)
    idx = np.clip(np.searchsorted(cum, u, side="right") - 1, 0, len(seg) - 1)
    f = (u - cum[idx]) / np.maximum(seg[idx], 1e-9)
    Z = P[idx] + (P[idx + 1] - P[idx]) * f
    mask = np.array([conn[i + 1] for i in idx])          # sample lies on a connector segment
    ends, acc = [], 0
    for ct in contours:                                   # parameter (0..1) where each contour closes
        acc += sum(abs(ct[j + 1] - ct[j]) for j in range(len(ct) - 1))
        ends.append(acc / L)
        acc += 0                                          # connector length is added below
    ends, acc = [], 0.0
    for i, ct in enumerate(contours):
        acc += sum(abs(ct[j + 1] - ct[j]) for j in range(len(ct) - 1))
        ends.append(acc / L)
        acc += abs(contours[(i + 1) % len(contours)][0] - ct[-1])
    Z = Z - Z.mean()
    return Z, mask, ends


Z, MASK, ENDS = word_path(WORD)
KS = np.arange(-K, K + 1)
_n = np.arange(N)
COEF = np.array([(Z * np.exp(-2j * np.pi * k * _n / N)).mean() for k in KS])
ORDER = [int(np.where(KS == 0)[0][0])] + [int(i) for i in np.argsort(-np.abs(COEF)) if KS[i] != 0]
FINE = 3000
SF = np.arange(FINE) / FINE
CURVE = (COEF[None, :] * np.exp(2j * np.pi * SF[:, None] * KS[None, :])).sum(1)
FMASK = MASK[(SF * N).astype(int)]


def s_of(t):
    if t < T_DRAW:
        return t / T_DRAW
    if t < T_DRAW + T_HOLD:
        return 1.0
    return 1.0 - smooth((t - T_DRAW - T_HOLD) / T_REW)


def simulate():
    return {"nf": int(round(T_LOOP * FPS))}


class Scene:
    def __init__(self, layout, sim):
        self.L, self.sim = layout, sim
        self.canvas = Canvas(layout.w, layout.h, studio.render_scale())
        w, h = layout.w, layout.h
        span = max(np.ptp(Z.real), 1e-6)
        self.S = w * 0.84 / span
        self.cx, self.cy = w / 2, h * 0.47

    def P(self, z):
        return self.cx + self.S * z.real, self.cy - self.S * z.imag

    def draw(self, f, rule):
        L, c = self.L, self.canvas
        w, h = L.w, L.h
        t = f * DT
        ctx = c.ctx
        g = cairo.RadialGradient(w / 2, h * 0.46, 0, w / 2, h * 0.46, max(w, h) * 0.7)
        g.add_color_stop_rgb(0.0, 0.07, 0.06, 0.12)
        g.add_color_stop_rgb(1.0, 0.01, 0.01, 0.02)
        ctx.set_source(g)
        ctx.paint()
        s = s_of(t)
        n = int(s * FINE)
        done = t >= T_DRAW and t < T_DRAW + T_HOLD
        glow = smooth((t - T_DRAW) / 0.4) if done else 0.0
        # trail: bright on the letters (hue runs along the drawing), faint on the connectors
        if n >= 2:
            pts = [self.P(z) for z in CURVE[:n]]
            runs, start = [], 0
            for i in range(1, n):
                if FMASK[i] != FMASK[start] or i - start > 60 or i == n - 1:
                    runs.append((start, i, FMASK[start]))
                    start = i
            letters = [pts[a:b + 1] for a, b, con in runs if not con]
            if letters:                                       # one stroke for the glow: no bright beads at joins
                c.polylines(letters, (1.0, 0.75, 0.85), width=16 + 10 * glow, alpha=0.10 + 0.12 * glow)
            for a, b, con in runs:
                seg = pts[a:b + 1]
                if con:
                    c.polylines([seg], (0.8, 0.8, 0.9), width=2, alpha=0.10)
                else:
                    col = studio.hsv((0.93 + 0.55 * a / FINE) % 1.0, 0.55, 1.0)
                    c.polylines([seg], col, width=5, alpha=0.95)
        # the epicycles
        if not done:
            z = COEF[ORDER[0]]
            ang = 2 * np.pi * s
            centres = [self.P(z)]
            for j in ORDER[1:]:
                z = z + COEF[j] * np.exp(1j * KS[j] * ang)
                centres.append(self.P(z))
            segs = []
            for i, j in enumerate(ORDER[1:]):
                r = abs(COEF[j]) * self.S
                if r < 1.2:
                    continue
                (x0, y0), (x1, y1) = centres[i], centres[i + 1]
                ctx.new_path()
                ctx.arc(x0, y0, r, 0, 2 * math.pi)
                ctx.set_source_rgba(0.75, 0.80, 1.0, 0.16 if i < 6 else 0.10)
                ctx.set_line_width(1.6)
                ctx.stroke()
                segs.append((x0, y0, x1, y1))
            c.lines(segs, (0.92, 0.94, 1.0), width=1.8, alpha=0.55)
            px, py = centres[-1]
            c.glow(px, py, 10, GOLD, strength=0.9, reach=4)
            c.circle(px, py, 7, (1, 1, 1), alpha=1.0)
        # text
        c.text_centered("z(t) = Σ cₖ · e^(i·k·t)".replace("ₖ", "k"), h * 0.715, size=w * 0.05,
                        color=(0.96, 0.96, 1.0), alpha=0.9, bold=False)
        c.text_centered(f"{2 * K} spinning circles · one pen", h * 0.752, size=w * 0.034, color=(0.75, 0.78, 0.88),
                        alpha=0.85, bold=False)
        c.text_centered("DRAWING WITH MATH", h * 0.205, size=h * 0.015, color=GOLD, alpha=0.85)
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


def build_events(sim, layout):
    penta = [0, 2, 4, 7, 9]
    ymin, ymax = Z.imag.min(), Z.imag.max()
    out, last = [], None
    step = 60.0 / 104 / 4                                        # 16ths at 104 BPM
    t = 0.0
    while t < T_DRAW:
        i = int(t / T_DRAW * FINE)
        z = CURVE[i]
        if not FMASK[i]:
            v = (z.imag - ymin) / (ymax - ymin + 1e-9)
            k = int(min(0.999, max(0.0, v)) * 10)
            m = 57 + 12 * (k // 5) + penta[k % 5] + 12
            if m != last:
                out.append({"t": round(t + 0.004, 4), "note": m, "gain": 0.26,
                            "x": layout.w * (0.5 + 0.4 * float(z.real / (np.ptp(Z.real) / 2 + 1e-9)))})
                last = m
        t += step
    for e in ENDS:                                               # a chord each time a contour closes
        te = e * T_DRAW
        for j, m in enumerate((57, 64, 69, 73)):
            out.append({"t": round(te + 0.02 * j, 4), "note": m + 12, "gain": 0.22, "x": layout.w / 2})
    for j, m in enumerate((57, 64, 69, 73, 76, 81)):            # finished
        out.append({"t": round(T_DRAW + 0.05 * j, 4), "note": m, "gain": 0.30, "x": layout.w / 2})
    for j in range(8):                                           # rewind run
        out.append({"t": round(T_DRAW + T_HOLD + j * T_REW / 9, 4), "note": 93 - 3 * j, "gain": 0.12,
                    "x": layout.w / 2})
    return sorted(out, key=lambda e: e["t"])


def _worker(o, sim, label, rule):
    layout = get_layout(o)
    name = f"{SCENE}_{label}_{layout.tag}"
    video = studio.OUT_DIR / f"{name}_silent.mp4"
    d = render(layout, sim, video, rule)
    pad = kit.loop_pad(T_LOOP, ((45, 1.0), (52, 0.7), (57, 0.45), (61, 0.3)), gain=0.015)
    kit.deliver_loop(SCENE, name, layout, video, build_events(sim, layout), d, voice="glassharp", bed=pad,
                     peak_db=-6.0)


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
    print(f"[{SCENE}] '{WORD}' {T_LOOP:.1f}s, {len(ENDS)} contours, max err "
          f"{np.abs(CURVE[::max(1, FINE // N)] - Z[::max(1, N // FINE)][:len(CURVE[::max(1, FINE // N)])]).max():.2f}")
    kit.fan_out(_worker, (sim, label, rule), SCENE)


if __name__ == "__main__":
    main()
