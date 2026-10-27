"""MANDEL DIVE — fall into the Mandelbrot set and land on a perfect copy of it.

z -> z^2 + c. Frame 0 is the whole Mandelbrot set, stood upright. The camera dives,
ever faster, into Elephant Valley, turning slowly as it goes, until after a ~3.3
million-fold zoom a tiny copy of the whole set (the period-38 "minibrot" at
c = 0.28500379756598 + 0.01060078045573 i) fills the frame exactly as the full set did
at frame 0. Camera path solved analytically: the copy sits at T + S*c for the main
set's c, with S its complex size (|S| = scale, arg S = rotation), so the last frame's
centre/scale/rotation are T + S*C0, |S|*scale0, R0 + arg S. Loop: a short dissolve
from that copy to frame 0 (the copy is almost, not exactly, the same shape).

Reference: youtube.com/shorts/0L13yN_zFak (a Mandelbrot zoom out of Seahorse Valley).
Taken: only the maths (the Mandelbrot set is public). Ours: the destination (a minibrot
in Elephant Valley, zooming IN), the self-similar loop, the palette, rotation, HUD,
caption and the synthesised sound.

Audio (original synthesis only): a glass-harp note per quarter-decade of zoom (they
speed up as the dive accelerates), a soft chord on arrival, a slow sine pad.

    ./run.ps1 -Scene mandel_dive -Fast -Still -Frame 600
    ./run.ps1 -Scene mandel_dive -Fast
"""
import cmath
import math
import sys
from pathlib import Path

import numpy as np
from numba import njit, prange

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib import audio, kit, studio  # noqa: E402
from lib.kit import DT, FPS, arg, smooth  # noqa: E402
from lib.layouts import get_layout  # noqa: E402
from lib.studio import Canvas, VideoWriter  # noqa: E402

SCENE = "mandel_dive"
NUCLEUS = complex(0.2850037975659808, 0.01060078045573048)
PERIOD = 38
C0 = complex(-0.62, 0.0)         # frame-0 centre (middle of the whole set)
R0 = math.pi / 2                 # stand the set upright: the antenna points up
DIVE_S = 18.0
HOLD_S = 0.5
FADE_S = 2.0
GAMMA = 1.35                     # how fast the target slides to screen centre
STEPS = 4                        # notes per decade of zoom
INSIDE = (0.035, 0.012, 0.045)
# exterior palette: deep -> rose -> violet -> teal -> gold -> deep (cycles)
PAL = np.array([(0.05, 0.02, 0.09), (0.55, 0.12, 0.35), (1.00, 0.42, 0.62), (0.70, 0.40, 1.00),
                (0.25, 0.85, 0.88), (1.00, 0.82, 0.48), (0.30, 0.10, 0.30), (0.05, 0.02, 0.09)])


def mini_size(c, p):
    z, l, b = 0j, 1 + 0j, 1 + 0j
    for _ in range(1, p):
        z = z * z + c
        l = 2 * z * l
        b = b + 1 / l
    return 1 / (b * l * l)


S = mini_size(NUCLEUS, PERIOD)
TARGET = NUCLEUS + S * C0        # where frame 0's centre lands inside the copy
ZOOM = 1.0 / abs(S)
ROT = cmath.phase(S)


def progress():
    """Dive progress 0..1 per frame: accelerating, easing onto the copy at the end."""
    n = int(round(DIVE_S * FPS))
    u = (np.arange(n) + 0.5) / n
    v = (0.35 + u ** 1.5) * (1.0 - 0.9 * np.clip((u - 0.82) / 0.18, 0, 1) ** 2)
    p = np.concatenate([[0.0], np.cumsum(v)])
    return p / p[-1]


def simulate():
    p = progress()
    nd = len(p)
    nh = int(round(HOLD_S * FPS))
    nf = nd + nh + int(round(FADE_S * FPS))
    return {"p": p, "nd": nd, "nf": nf, "nh": nh}


def camera(p, scale0):
    """p in 0..1 -> (centre, units-per-pixel, rotation)."""
    k = math.exp(-math.log(ZOOM) * p)               # scale / scale0
    centre = TARGET + (C0 - TARGET) * k ** GAMMA
    return centre, scale0 * k, R0 + ROT * p


@njit(parallel=True, cache=True)
def _mandel(out, w, h, ycen, cre, cim, scale, cr, sr, maxit):
    for j in prange(h):
        for i in range(w):
            dx = i + 0.5 - w * 0.5
            dy = ycen - (j + 0.5)
            re = cre + scale * (dx * cr - dy * sr)
            im = cim + scale * (dx * sr + dy * cr)
            q = (re - 0.25) ** 2 + im * im             # main cardioid / period-2 bulb
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


def colour(v, phase):
    """Smooth iteration count -> RGB (float 0..1), palette cycled on log(n)."""
    inside = v < 0
    x = (np.log1p(np.maximum(v, 0.0)) * 0.38 + phase) % 1.0
    m = len(PAL) - 1
    f = x * m
    i = np.minimum(f.astype(np.int32), m - 1)
    t = (f - i)[..., None]
    rgb = PAL[i] * (1 - t) + PAL[i + 1] * t
    # the open sky stays dark: light rises only as the count climbs above this frame's floor,
    # so every zoom depth reads as glowing filaments on night (and the loop frames match)
    out = v[~inside]
    if out.size:
        lo = math.log(max(float(np.percentile(out, 35)), 1.0))   # most of the sky stays night
        b = np.clip((np.log(np.maximum(v, 1.0)) - lo) / 1.4, 0.0, 1.0)
        b = (b * b * (3 - 2 * b))[..., None]
        rgb = INSIDE + (rgb - INSIDE) * (0.08 + 0.92 * b)
    rgb[inside] = INSIDE
    return rgb


class Scene:
    def __init__(self, layout, sim):
        self.L, self.sim = layout, sim
        self.canvas = Canvas(layout.w, layout.h, studio.render_scale())
        c = self.canvas
        self.vertical = layout.h > layout.w
        self.ycen_f = 0.47 if self.vertical else 0.5
        # whole set (imag extent ~2.5 across the frame width when upright)
        fit_w = 2.55 if self.vertical else 3.1
        self.scale0 = fit_w / c.pw if self.vertical else fit_w / c.ph
        self.buf = np.zeros((c.ph, c.pw), dtype=np.float64)
        self.frame0 = None

    def fractal(self, p):
        c = self.canvas
        centre, scale, rot = camera(p, self.scale0)
        maxit = int(400 + 700 * p * math.log10(ZOOM))
        _mandel(self.buf, c.pw, c.ph, c.ph * self.ycen_f, centre.real, centre.imag, scale,
                math.cos(rot), math.sin(rot), maxit)
        return colour(self.buf, 0.0)

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

    def draw(self, f, rule):
        sim, L, c = self.sim, self.L, self.canvas
        nd, nf = sim["nd"], sim["nf"]
        t = f * DT
        p = sim["p"][min(f, nd - 1)]
        rgb = self.fractal(p)
        e = 0.0
        if f >= nd + sim["nh"]:                          # dissolve onto frame 0
            e = smooth((f - nd - sim["nh"] + 1) / (nf - nd - sim["nh"]))
            if self.frame0 is None:
                self.frame0 = self.fractal(0.0)
            rgb = rgb * (1 - e) + self.frame0 * e
        self.blit(rgb)

        mag = ZOOM ** p
        hud = smooth(t / 0.4) * (1.0 - e)
        w, h = L.w, L.h
        if self.vertical:
            eq_y, cnt_y, sz = h * 0.185, h * 0.80, w * 0.055
        else:
            eq_y, cnt_y, sz = h * 0.08, h * 0.95, w * 0.024
        c.text_centered("z → z² + c", eq_y, size=sz, color=(0.97, 0.94, 0.98), alpha=hud, bold=False)
        c.text_centered(f"zoom ×{mag:,.0f}", cnt_y, size=sz * 1.0, color=(1.0, 0.85, 0.55), alpha=hud)
        if rule:
            c.caption(rule, alpha=hud, layout=L)
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
    walker = audio.ScaleWalker(root_midi=62, scale=audio.PENTA_MAJOR, span=10, pattern="updown")
    p, nd = sim["p"], sim["nd"]
    dec = math.log10(ZOOM)
    out = [{"t": 0.02, "note": 50, "gain": 0.45, "x": layout.w / 2},
           {"t": 0.07, "note": 62, "gain": 0.40, "x": layout.w / 2}]
    k = 1
    for f in range(1, nd):
        while p[f] * dec * STEPS >= k:
            t = f * DT
            out.append({"t": round(t, 4), "note": walker.next(), "gain": round(0.38 + 0.2 * p[f], 3),
                        "x": round(layout.w * (0.5 + 0.25 * math.sin(k * 1.3)), 1)})
            k += 1
    t_end = nd * DT
    for j, note in enumerate((50, 57, 62, 66, 69)):        # arrival: D major, the copy found
        out.append({"t": round(t_end + 0.06 * j, 4), "note": note, "gain": 0.48, "x": layout.w / 2})
    return sorted(out, key=lambda e: e["t"])


def pad(sim):
    """Slow sine pad (D-A-D-F#) with a gentle swell, silent at the loop seam."""
    sr = audio.SR
    dur = sim["nf"] / FPS
    t = np.arange(int(dur * sr)) / sr
    sig = np.zeros_like(t)
    for m, amp in ((38, 0.8), (50, 1.0), (57, 0.7), (62, 0.45), (66, 0.3)):
        f0 = audio.midi_to_hz(m)
        sig += amp * (np.sin(2 * np.pi * f0 * t) + 0.5 * np.sin(2 * np.pi * f0 * 1.003 * t))
    lfo = 0.80 + 0.20 * np.sin(2 * np.pi * 0.11 * t)
    env = np.clip(t / 0.5, 0, 1) * np.clip((dur - 0.5 - t) / 2.2, 0, 1) ** 2
    return (0.017 * sig * lfo * env).astype(np.float32)


def _worker(o, sim, label, rule):
    layout = get_layout(o)
    name = f"{SCENE}_{label}_{layout.tag}"
    video = studio.OUT_DIR / f"{name}_silent.mp4"
    d = render(layout, sim, video, rule)
    kit.deliver(SCENE, name, layout, video, build_events(sim, layout), d, True,
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
    print(f"[{SCENE}] {sim['nf'] / FPS:.2f}s zoom x{ZOOM:,.0f} rot {math.degrees(ROT):.1f} deg "
          f"per5s={kit.density_report(ev, sim['nd'] * DT)}")
    kit.fan_out(_worker, (sim, label, rule), SCENE)


if __name__ == "__main__":
    main()
