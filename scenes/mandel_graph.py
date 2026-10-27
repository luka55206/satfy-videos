"""MANDEL GRAPH — zoom OUT of a tiny Mandelbrot copy until the real set appears (graph style).

z -> z^2 + c, drawn like a maths plot, not an ornament: dark paper, a live coordinate grid
with tick labels (Im(c) across, Re(c) up), the set filled flat with a bright boundary, and
the escape-time field drawn as thin CONTOUR LINES (iso-lines of log n, like a topographic
plot). Frame 0 looks like the whole Mandelbrot set, but the axes read 0.28504...: it is
the period-22 copy in Elephant Valley at c = 0.28504024 + 0.01068357i, ~518,000 times
smaller and tilted only 6° (so the plot needs no rotation). The camera pulls out through
the valley's spirals at a constant speed until the true set fills the frame (axes -2 ... 0.5).
NONSTOP LOOP (v2, owner): the pull-out never stops; in the last 1.2 s the full set melts,
still moving, into the copy one level up, which is exactly the view that leads into frame 0.
(v0 used the real-axis period-7 copy: exactly upright, but the antenna is empty black for
most of the zoom.)

Reference: youtube.com/shorts/0L13yN_zFak. Taken: only the maths (the Mandelbrot set is
public). Ours: graph styling (grid, ticks, contour lines), the Elephant Valley copy, the
self-similar nonstop loop, HUD, caption and synthesised sound.

Audio (original synthesis only): 54 evenly spaced glass-harp notes (3 whole walker periods,
so the tune loops), a soft chord as each level begins, an exactly periodic sine pad;
kit.deliver_loop folds note tails across the seam (no fade anywhere).

    ./run.ps1 -Scene mandel_graph -Fast -Still -Frame 600
    ./run.ps1 -Scene mandel_graph -Fast
"""
import cmath
import math
import sys
from pathlib import Path

import cairo
import numpy as np
from numba import njit, prange

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib import audio, kit, studio  # noqa: E402
from lib.kit import DT, FPS, arg, smooth  # noqa: E402
from lib.layouts import get_layout  # noqa: E402
from lib.studio import Canvas, VideoWriter  # noqa: E402

SCENE = "mandel_graph"
NUCLEUS = complex(0.2850402395146864, 0.010683574973382196)   # period-22 copy, Elephant Valley (6° tilt)
PERIOD = 22
C0 = complex(-0.76, 0.0)             # the whole set's centre on screen
LOOP_S = 20.0                        # one full pull-out = one loop; constant speed, never stops
XF_S = 1.2                           # last stretch: the full set melts into the copy, still moving
N_NOTES = 54                         # 3 whole periods of the 18-note walker -> the tune loops too
PAPER = np.array([0.025, 0.030, 0.060])
FILL = np.array([0.075, 0.105, 0.165])
EDGE = np.array([0.95, 0.97, 1.00])
LINES = np.array([(1.00, 0.42, 0.62), (0.72, 0.45, 1.00), (0.30, 0.85, 0.90), (1.00, 0.80, 0.45)])
CONTOUR_K = 3.2                      # contour lines per unit of log(n)


def mini_size(c, p):
    z, l, b = 0j, 1 + 0j, 1 + 0j
    for _ in range(1, p):
        z = z * z + c
        l = 2 * z * l
        b = b + 1 / l
    return 1 / (b * l * l)


S = mini_size(NUCLEUS, PERIOD)
TARGET = NUCLEUS + S * C0            # frame-0 centre: where the whole set's centre lands in the copy
ZOOM = 1.0 / abs(S)


def simulate():
    """Depth falls 1 -> 0 at a CONSTANT log-zoom speed, so frame N (depth 0, the full set) is
    the copy view one level up: depth d and d+1 look the same. The last XF frames blend the
    view at depth d into the view at depth d+1, which is exactly the path that leads into frame 0."""
    n = int(round(LOOP_S * FPS))
    d = 1.0 - np.arange(n) / n
    return {"d": d, "nd": n, "nf": n, "xf": int(round(XF_S * FPS))}


FIX = NUCLEUS / (1 - S)              # fixed point of c -> NUCLEUS + S*c (the copy map)
LOG_S = cmath.log(S)


def camera(d, scale0):
    """Self-similar path: camera(d + 1) is exactly the copy map applied to camera(d)
    (centre FIX + (C0 - FIX) S^d, scale |S|^d), so the view one level deeper is the same
    picture, which is what lets the end flow straight into frame 0. (The copy's 6° tilt is
    the one thing a non-rotating graph can't follow; it only shows inside the 1.2 s blend.)"""
    sd = cmath.exp(d * LOG_S)
    return FIX + (C0 - FIX) * sd, scale0 * abs(sd)


@njit(parallel=True, cache=True)
def _mandel(out, w, h, ycen, cre, cim, scale, maxit):
    """Im(c) across, Re(c) up."""
    for j in prange(h):
        for i in range(w):
            im = cim + scale * (i + 0.5 - w * 0.5)
            re = cre + scale * (ycen - (j + 0.5))
            q = (re - 0.25) ** 2 + im * im
            if q * (q + (re - 0.25)) <= 0.25 * im * im or (re + 1.0) ** 2 + im * im <= 0.0625:
                out[j, i] = -1.0
                continue
            zr = 0.0
            zi = 0.0
            n = 0
            while n < maxit:
                zr2 = zr * zr
                zi2 = zi * zi
                if zr2 + zi2 > 65536.0:
                    break
                zi = 2.0 * zr * zi + im
                zr = zr2 - zi2 + re
                n += 1
            if n >= maxit:
                out[j, i] = -1.0
            else:
                mod = math.sqrt(zr * zr + zi * zi)
                out[j, i] = n + 1.0 - math.log(math.log(mod)) / math.log(2.0)


def shade(v, line_px):
    """Escape field -> RGB plot: paper, contour lines, flat-filled set with a bright edge."""
    inside = v < 0
    lv = np.log(np.maximum(v, 1.0)) * CONTOUR_K
    gy, gx = np.gradient(lv)
    grad = np.hypot(gx, gy) + 1e-9
    dist = np.abs(((lv + 0.5) % 1.0) - 0.5) / grad        # px to the nearest contour
    a = np.clip(1.0 - dist / line_px, 0.0, 1.0)
    a[grad > 0.45] *= np.clip(0.45 / grad[grad > 0.45], 0, 1) ** 2   # fade where lines crowd
    idx = np.floor(lv + 0.5).astype(np.int64) % len(LINES)
    rgb = PAPER + (LINES[idx] - PAPER) * (0.85 * a)[..., None]
    rgb[inside] = FILL
    edge = np.zeros_like(inside)
    edge[1:, :] |= inside[1:, :] != inside[:-1, :]
    edge[:, 1:] |= inside[:, 1:] != inside[:, :-1]
    rgb[edge] = EDGE
    return rgb


def nice_step(span):
    raw = span / 5.0
    e = math.floor(math.log10(raw))
    for m in (1, 2, 5, 10):
        if m * 10 ** e >= raw:
            return m * 10 ** e, e


def fmt(v, e):
    dec = max(0, -e)
    s = f"{v:.{dec}f}"
    if s.startswith("-0") and float(s) == 0:
        s = s[1:]
    return s.replace("-", "−")


class Scene:
    def __init__(self, layout, sim):
        self.L, self.sim = layout, sim
        self.canvas = Canvas(layout.w, layout.h, studio.render_scale())
        c = self.canvas
        self.vertical = layout.h > layout.w
        self.ycen_f = 0.47 if self.vertical else 0.5
        # whole set, Re up: Re spans ~2.5, Im ~2.3
        self.scale0 = (2.30 / (0.90 * c.pw)) if self.vertical else (2.75 / (0.92 * c.ph))
        self.buf = np.zeros((c.ph, c.pw), dtype=np.float64)
        self.px = c.pw / layout.w                  # device px per logical px

    def field(self, d):
        c = self.canvas
        centre, scale = camera(d, self.scale0)
        maxit = int(300 + 500 * d * math.log10(ZOOM))
        _mandel(self.buf, c.pw, c.ph, c.ph * self.ycen_f, centre.real, centre.imag, scale, maxit)
        return shade(self.buf, 1.1 * self.px), centre, scale

    def blit(self, rgb):
        c = self.canvas
        c.surf.flush()
        arr = np.ndarray((c.ph, c.surf.get_stride() // 4, 4), dtype=np.uint8, buffer=c.surf.get_data())
        u8 = np.clip(rgb * 255.0 + 0.5, 0, 255).astype(np.uint8)
        arr[:, :c.pw, 0] = u8[..., 2]
        arr[:, :c.pw, 1] = u8[..., 1]
        arr[:, :c.pw, 2] = u8[..., 0]
        arr[:, :c.pw, 3] = 255
        c.surf.mark_dirty()

    def grid(self, centre, scale, alpha):
        """Graph-paper grid + tick labels in logical coords (Im across, Re up)."""
        L, c = self.L, self.canvas
        w, h = L.w, L.h
        s = scale * self.px                          # c-units per logical px
        ycen = h * self.ycen_f
        im0, im1 = centre.imag - s * w / 2, centre.imag + s * w / 2
        re0, re1 = centre.real - s * (h - ycen), centre.real + s * ycen
        top, bot = (h * 0.235, h * 0.735) if self.vertical else (h * 0.15, h * 0.88)
        st, e = nice_step(im1 - im0)
        segs, labs = [], []
        k = math.ceil(im0 / st)
        while k * st <= im1:
            x = w / 2 + (k * st - centre.imag) / s
            segs.append((x, top, x, bot))
            labs.append((x, fmt(k * st, e)))
            k += 1
        c.lines(segs, (0.75, 0.80, 1.0), width=1.0, alpha=0.10 * alpha)
        for x, t in labs:
            if 50 < x < w - 50:
                c.text_centered(t, bot + h * 0.018, size=h * 0.0105, color=(0.80, 0.84, 0.95),
                                alpha=0.75 * alpha, bold=False, cx=x)
        st, e = nice_step(re1 - re0)
        segs = []
        k = math.ceil(re0 / st)
        while k * st <= re1:
            y = ycen - (k * st - centre.real) / s
            if top <= y <= bot:
                segs.append((0, y, w, y))
                c.text_centered(fmt(k * st, e), y - 6, size=h * 0.0105, color=(0.80, 0.84, 0.95),
                                alpha=0.75 * alpha, bold=False, cx=w * 0.105, max_w=w * 0.2)
            k += 1
        c.lines(segs, (0.75, 0.80, 1.0), width=1.0, alpha=0.10 * alpha)
        c.text_centered("Re(c) ↑", top + h * 0.012, size=h * 0.012, color=(1, 1, 1), alpha=0.7 * alpha,
                        bold=False, cx=w * 0.92, max_w=w * 0.15)
        c.text_centered("Im(c) →", bot + h * 0.040, size=h * 0.012, color=(1, 1, 1), alpha=0.7 * alpha,
                        bold=False, cx=w * 0.88, max_w=w * 0.2)

    def draw(self, f, rule):
        sim, L, c = self.sim, self.L, self.canvas
        nf, xf = sim["nf"], sim["xf"]
        d = sim["d"][f]
        rgb, centre, scale = self.field(d)
        e = 0.0
        if f >= nf - xf:                     # still moving: melt into the next level's copy
            e = smooth((f - (nf - xf) + 1) / xf)
            rgb_b, cen_b, sc_b = self.field(d + 1.0)
            rgb = rgb * (1 - e) + rgb_b * e
        self.blit(rgb)
        # grid, equation and counter are ON from frame 0 (the coordinates are the hook)
        # HUD text hands over in SEQUENCE (out, then in), never overlapping: two sets of tick
        # labels / counters drawn at once read as garbled text at 4K
        ea, eb = max(0.0, 1.0 - 2.0 * e), max(0.0, 2.0 * e - 1.0)
        if ea > 0:
            self.grid(centre, scale, ea)
        if eb > 0:
            self.grid(cen_b, sc_b, eb)
        w, h = L.w, L.h
        mag = ZOOM ** (1.0 - d)
        sz = w * (0.050 if self.vertical else 0.024)
        eq_y, cnt_y = (h * 0.185, h * 0.80) if self.vertical else (h * 0.07, h * 0.965)
        c.text_centered("z → z² + c", eq_y, size=sz, color=(0.97, 0.94, 0.98), alpha=1.0, bold=False)
        for txt, a in ((f"zoomed out ×{mag:,.0f}", ea), ("zoomed out ×1", eb)):
            if a > 0.001:
                c.text_centered(txt, cnt_y, size=sz * 0.85, color=(1.0, 0.85, 0.55), alpha=a)
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
    """Evenly spaced notes (the zoom speed is constant), a whole number of walker periods per
    loop so the melody joins itself; a soft chord as each new level (frame 0) begins."""
    walker = audio.ScaleWalker(root_midi=62, scale=audio.PENTA_MAJOR, span=10, pattern="updown")
    dur = sim["nf"] * DT
    out = []
    for k in range(N_NOTES):
        out.append({"t": round((k + 0.5) * dur / N_NOTES, 4), "note": walker.next(), "gain": 0.42,
                    "x": round(layout.w * (0.5 + 0.25 * math.sin(k * 1.3)), 1)})
    for j, note in enumerate((50, 57, 62, 66)):
        out.append({"t": round(0.02 + 0.06 * j, 4), "note": note, "gain": 0.40, "x": layout.w / 2})
    return sorted(out, key=lambda e: e["t"])


def pad(sim):
    return kit.loop_pad(sim["nf"] / FPS, ((38, 0.8), (50, 1.0), (57, 0.7), (62, 0.45), (66, 0.3)),
                        gain=0.017)


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
    print(f"[{SCENE}] {sim['nf'] / FPS:.2f}s zoom x{ZOOM:,.0f} per5s={kit.density_report(ev, sim['nf'] * DT)}")
    kit.fan_out(_worker, (sim, label, rule), SCENE)


if __name__ == "__main__":
    main()
