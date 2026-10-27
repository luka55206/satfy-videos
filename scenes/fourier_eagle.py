"""FOURIER EAGLE - "Can circles draw America's bird?"  (line art: outline + inlines, no colour fill)

An original eagle drawing (scenes/eagle_shape.py: silhouette + every visible feather edge, quill, chest
scale, beak, eye and talon) is ONE continuous pen path: the outline first, then the inlines stroke by
stroke, the pen lifting between strokes (faint travel lines). The path is split into two Fourier series,
x(t) and y(t); each is a chain of rotating circles stacked tip to tip. The RED chain (above) gives the
pen's x, the BLUE chain (left) gives its y; dashed white guides from each chain tip cross at the pen.
The drawing restarts with more circles: N = 5, 20, 60, 200, 1500 (error % measured live). N = 200
only manages the outline; the inlines need N = 1500. At the finish the white line art glows, then the
circle count unwinds to 5 and the eagle melts into the opening blob = frame 0 (nonstop loop).

Audio (original synthesis only, nothing sampled, no known tune): an eagle-like cry at 0.0 s and a louder
echoing cry at the finish, a marching snare busier every round, brass-like fanfare phrases climbing a
triad each round, a mechanical tick. 120 BPM x 36 beats = the 18 s loop.

    NF_FAST=1 python scenes/fourier_eagle.py        # 540x960 preview
"""
import math
import sys
from pathlib import Path

import cairo
import numpy as np
from scipy.signal import butter, sosfilt

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib import audio, kit, studio  # noqa: E402
from lib.kit import DT, FPS, arg, smooth  # noqa: E402
from lib.layouts import get_layout  # noqa: E402
from lib.studio import Canvas, VideoWriter  # noqa: E402
import scenes.eagle_shape as es  # noqa: E402

SCENE = "fourier_eagle"
T_LOOP = 18.0
STAGES = [(5, 0.0, 1.8), (20, 2.0, 1.8), (60, 4.0, 2.0), (200, 6.2, 2.2), (1500, 8.6, 5.6)]   # circles, start, draw s
T_DONE, T_MORPH = 14.6, 16.2
KMAX = 1500
NS = 32768                                  # samples of the pen path
RED, BLUE = (1.0, 0.22, 0.28), (0.30, 0.60, 1.0)
LINE = (0.96, 0.97, 1.0)


# --- the pen path: outline, then inlines (pen lifts between strokes) ------------------------

def pen_path():
    ring, strokes = es.lineart()
    pts, conn = [complex(*p) for p in ring] + [complex(*ring[0])], [False] * (len(ring) + 1)
    for st in strokes:
        pts.append(complex(*st[0]))
        conn.append(True)
        for p in st[1:]:
            pts.append(complex(*p))
            conn.append(False)
    pts.append(complex(*ring[0]))
    conn.append(True)
    P = np.array(pts)
    seg = np.abs(np.diff(P))
    cum = np.concatenate([[0], np.cumsum(seg)])
    u = np.linspace(0, cum[-1], NS, endpoint=False)
    idx = np.clip(np.searchsorted(cum, u, side="right") - 1, 0, len(seg) - 1)
    f = (u - cum[idx]) / np.maximum(seg[idx], 1e-9)
    Z = P[idx] + (P[idx + 1] - P[idx]) * f
    mask = np.array(conn)[idx + 1]                                    # sample lies on a pen-up travel segment
    return Z - Z.mean(), Z.mean(), mask


Z, MEAN, MASK = pen_path()
CEN = complex((Z.real.min() + Z.real.max()) / 2, (Z.imag.min() + Z.imag.max()) / 2)
DIAG = float(np.hypot(np.ptp(Z.real), np.ptp(Z.imag)))
XS, YS = np.fft.rfft(Z.real), np.fft.rfft(Z.imag)                    # unnormalised spectra
_k = np.arange(1, KMAX + 1)
XR, XP = np.abs(XS[1:KMAX + 1]) * 2 / NS, -np.angle(XS[1:KMAX + 1])        # x(t) = sum XR cos(2 pi k t + phase)
YR, YP = np.abs(YS[1:KMAX + 1]) * 2 / NS, -np.angle(YS[1:KMAX + 1])
XP, YP = -XP, -YP                                                     # chain angle = 2 pi k s - PH


def weights(n):
    return np.clip(n - (_k - 1), 0.0, 1.0)


def recon(w):
    full = np.zeros(NS // 2 + 1)
    full[1:KMAX + 1] = w
    return np.fft.irfft(XS * full, NS), np.fft.irfft(YS * full, NS)


def err_pct(w):
    x, y = recon(w)
    return float(np.mean(np.abs((x + 1j * y) - Z)) / DIAG * 100.0)


ERR = {n: err_pct(weights(n)) for n, _, _ in STAGES}
CURVES = {n: recon(weights(n)) for n, _, _ in STAGES}


# --- timeline --------------------------------------------------------------------------------

def state(t):
    if t >= T_MORPH:
        u = smooth((t - T_MORPH) / (T_LOOP - T_MORPH))
        return {"n": 1500.0 * (5.0 / 1500.0) ** u, "s": 1.0, "stage": 4, "prev": None, "fade": 0.0, "done": True}
    if t >= T_DONE:
        return {"n": 1500.0, "s": 1.0, "stage": 4, "prev": None, "fade": 0.0, "done": True}
    i = max(j for j, (_, ts, _) in enumerate(STAGES) if t >= ts)
    n, ts, dur = STAGES[i]
    prev = STAGES[i - 1][0] if i else 5                      # stage 1 starts over the 5-circle blob (the loop)
    return {"n": float(n), "s": min(1.0, (t - ts) / dur), "stage": i, "prev": prev,
            "fade": smooth((t - ts) / 0.5), "done": False}


def pen_gap(n):
    """how much the pen-up travel is hidden: shown at N<=60 (the blob), hidden from N=200 on"""
    return smooth((n - 60.0) / 140.0)


# --- drawing -------------------------------------------------------------------------------

class Scene:
    def __init__(self, layout):
        self.L = layout
        self.canvas = Canvas(layout.w, layout.h, studio.render_scale())
        w, h = layout.w, layout.h
        self.S = w * 0.80 / float(np.ptp(Z.real))
        self.cx, self.cy = w / 2, h * 0.455
        self.ST = 4                                           # draw every 4th sample of the path
        self.art = cairo.ImageSurface(cairo.FORMAT_ARGB32, self.canvas.pw, self.canvas.ph)   # the inked, flag-coloured eagle
        c2 = cairo.Context(self.art)
        c2.scale(self.canvas.pw / w, self.canvas.ph / h)
        es.paint(c2, lambda x, y: self.P(x - MEAN.real, y - MEAN.imag), self.S)
        self.art.flush()

    def P(self, x, y):
        return self.cx + self.S * (x - CEN.real), self.cy - self.S * (y - CEN.imag)

    def screen(self, X, Y):
        return list(zip((self.cx + self.S * (X[::self.ST] - CEN.real)).tolist(),
                        (self.cy - self.S * (Y[::self.ST] - CEN.imag)).tolist()))

    def runs(self, pts, upto, gap, alpha, wd, glow):
        """polyline runs: bright where the pen draws, faint (or hidden) where it travels"""
        c = self.canvas
        m = MASK[::self.ST][:upto]
        a_trav = 1.0 - gap
        i = 0
        while i < upto - 1:
            j = i
            while j < upto - 1 and m[j] == m[i]:
                j += 1
            seg = pts[i:j + 2]
            if len(seg) > 1:
                a = alpha * (a_trav if m[i] else 1.0)
                if a > 0.02:
                    if glow:
                        c.polylines([seg], LINE, width=wd * 3.2, alpha=0.10 * a)
                    c.polylines([seg], LINE, width=wd, alpha=a)
            i = j + 1

    def chain(self, base, R, PH, w, s, axis, col, alpha):
        c = self.canvas
        ctx = c.ctx
        order = np.argsort(-(R * w))
        pos = np.array(base, float)
        pts = [tuple(pos)]
        for i in order:
            r = R[i] * w[i] * self.S
            if r < 0.05:
                continue
            th = 2 * np.pi * _k[i] * s - PH[i]
            if axis == "x":
                v = np.array([r * math.cos(th), -r * math.sin(th)])
            else:
                v = np.array([r * math.sin(th), -r * math.cos(th)])
            if r > 1.6:
                ctx.set_source_rgba(*col, 0.10 * alpha)
                ctx.set_line_width(7)
                ctx.new_sub_path()
                ctx.arc(pos[0], pos[1], r, 0, 2 * math.pi)
                ctx.stroke()
                ctx.set_source_rgba(*col, 0.55 * alpha)
                ctx.set_line_width(2)
                ctx.new_sub_path()
                ctx.arc(pos[0], pos[1], r, 0, 2 * math.pi)
                ctx.stroke()
            pos = pos + v
            pts.append(tuple(pos))
        if len(pts) > 1:
            c.polylines([pts], col, width=3.0, alpha=0.95 * alpha)
        return pos

    def draw(self, f):
        L, c = self.L, self.canvas
        w, h = L.w, L.h
        t = f * DT
        ctx = c.ctx
        st = state(t)
        bg = cairo.RadialGradient(w / 2, h * 0.47, 0, w / 2, h * 0.47, max(w, h) * 0.75)
        bg.add_color_stop_rgb(0.0, 0.105, 0.11, 0.135)
        bg.add_color_stop_rgb(1.0, 0.035, 0.037, 0.05)
        ctx.set_source(bg)
        ctx.paint()

        n_c = st["n"]
        wts = weights(n_c)
        s = st["s"]
        done = st["done"]
        X, Y = CURVES[int(n_c)] if n_c in CURVES else recon(wts)
        gap = pen_gap(n_c)
        pts_full = self.screen(X, Y)
        npts = len(pts_full)

        # the previous round's drawing fades as the new one is drawn
        if st["prev"] is not None and st["fade"] < 1.0:
            px_, py_ = CURVES[st["prev"]]
            self.runs(self.screen(px_, py_), npts, pen_gap(st["prev"]), 0.98 * (1 - st["fade"]), 3.0, False)

        n_pts = max(2, int(s * (npts - 1)) + 1) if not done else npts
        pen_i = min(int(s * (NS - 1)), NS - 1)
        flash = max(0.0, 1.0 - (t - T_DONE) / 0.40) if (done and t >= T_DONE) else 0.0
        t_fill = smooth((t - T_DONE) / 0.45) * (1.0 - smooth((t - 16.0) / 0.5)) if done else 0.0
        self.runs(pts_full, n_pts, gap, 0.98 * (1.0 - 0.92 * t_fill), 3.0 + 3.0 * flash, flash > 0.0)
        if t_fill > 0.0:                                      # the finished line art is inked in USA colours
            ctx.save()
            ctx.identity_matrix()
            ctx.set_source_surface(self.art, 0, 0)
            ctx.paint_with_alpha(t_fill)
            ctx.restore()

        # the two chains and the dashed guides meeting at the pen
        pen = self.P(X[pen_i], Y[pen_i])
        sp = s % 1.0 if s < 1.0 else 0.0
        o = self.P(0.0, 0.0)
        ch_a = 1.0 - 0.92 * t_fill                              # the circles step back when the eagle is inked in
        top_tip = self.chain((o[0], h * 0.215), XR, XP, wts, sp, "x", RED, 0.95 * ch_a)
        left_tip = self.chain((w * 0.20, o[1]), YR, YP, wts, sp, "y", BLUE, 0.95 * ch_a)
        band = cairo.LinearGradient(0, 0, 0, h * 0.215)                  # keep the header readable over the circles
        band.add_color_stop_rgba(0.0, 0.05, 0.052, 0.07, 0.96)
        band.add_color_stop_rgba(0.75, 0.05, 0.052, 0.07, 0.88)
        band.add_color_stop_rgba(1.0, 0.05, 0.052, 0.07, 0.0)
        ctx.set_source(band)
        ctx.rectangle(0, 0, w, h * 0.215)
        ctx.fill()
        for tip in (top_tip, left_tip):
            ctx.set_source_rgba(1, 1, 1, 0.65 * ch_a)
            ctx.set_line_width(2.5)
            ctx.set_dash([12, 10])
            ctx.move_to(*tip)
            ctx.line_to(*pen)
            ctx.stroke()
            ctx.set_dash([])
        c.glow(pen[0], pen[1], 14, (1, 1, 1), strength=0.9 * ch_a, reach=3.0)
        c.circle(pen[0], pen[1], 8, (1, 1, 1), alpha=ch_a)
        c.glow(top_tip[0], top_tip[1], 6, RED, strength=0.8 * ch_a, reach=2.5)
        c.glow(left_tip[0], left_tip[1], 6, BLUE, strength=0.8 * ch_a, reach=2.5)

        # hook text (top) <-> finish text, one at a time
        a_fin = smooth((t - T_DONE - 0.22) / 0.25) * (1.0 - smooth((t - 16.0) / 0.2))
        a_hook = min(1.0, (1.0 - smooth((t - T_DONE) / 0.2)) + smooth((t - 16.2) / 0.3))
        self.flag(w / 2, h * 0.073, 1.0)
        c.caption("Can ~Circles~ Draw\nAmerica’s Bird?", alpha=a_hook, layout=L, span_color=(0.45, 0.7, 1.0))
        c.caption("~1500 Circles~\nOne Eagle.", alpha=a_fin, layout=L, span_color=(1.0, 0.35, 0.40))

        # technical readout (bottom): circle count + error, updated live
        n_show = int(round(n_c))
        err = err_pct(wts) if n_c not in ERR else ERR[int(n_c)]
        c.text_centered(f"N = {n_show} circles", h * 0.752, size=h * 0.032, color=(1, 1, 1), cx=w / 2, max_w=w * 0.9)
        c.text_centered(f"error {err:.2f}%", h * 0.790, size=h * 0.027, color=(0.55, 0.75, 1.0), alpha=0.95,
                        cx=w / 2, max_w=w * 0.9)
        c.watermark(L)

    def flag(self, cx, cy, a):
        ctx = self.canvas.ctx
        wf, hf = 92.0, 58.0
        x0, y0 = cx - wf / 2, cy - hf / 2
        self.canvas.glow(cx, cy, 40, (0.5, 0.65, 1.0), strength=0.35 * a, reach=1.8)
        for i in range(13):
            ctx.set_source_rgba(0.85, 0.12, 0.2, a) if i % 2 == 0 else ctx.set_source_rgba(1, 1, 1, a)
            ctx.rectangle(x0, y0 + hf * i / 13, wf, hf / 13 + 0.5)
            ctx.fill()
        ctx.set_source_rgba(0.12, 0.2, 0.55, a)
        ctx.rectangle(x0, y0, wf * 0.42, hf * 7 / 13)
        ctx.fill()
        for r in range(3):
            for k in range(4):
                self.canvas.circle(x0 + wf * 0.42 * (k + 0.5) / 4, y0 + hf * 7 / 13 * (r + 0.5) / 3, 2.2,
                                   (1, 1, 1), alpha=a)


# --- sound (original synthesis) ------------------------------------------------------------

SR = audio.SR


def _hp(sig, lo, hi):
    return sosfilt(butter(2, [lo, hi], btype="band", fs=SR, output="sos"), sig)


def synth_cry(dur=0.9, seed=1, f0=3400.0, f1=1750.0, notes=1, echo=False):
    """An eagle-like cry: descending, raspy, noisy whistle (pure DSP). `notes` chirps in a row."""
    rng = np.random.default_rng(seed)
    out = np.zeros(int((dur + (1.4 if echo else 0.2)) * SR))
    for j in range(notes):
        n = int(dur / notes * SR * 0.95)
        t = np.arange(n) / SR
        u = t / t[-1]
        f = (f0 * (f1 / f0) ** u) * (1 + 0.012 * np.sin(2 * np.pi * 41 * t)) * (1.0 - 0.06 * j)
        ph = 2 * np.pi * np.cumsum(f) / SR
        tone = np.sin(ph) + 0.55 * np.sin(2 * ph + 0.4) + 0.28 * np.sin(3 * ph + 1.1)
        noise = _hp(rng.standard_normal(n), 1500, 6500)
        sig = tone + 0.7 * noise
        sig *= 0.72 + 0.28 * np.sin(2 * np.pi * 78 * t)                  # rasp
        env = np.minimum(1.0, t / 0.006) * np.exp(-2.2 * u) * (1 - u) ** 0.3
        sig *= env
        i0 = int(j * dur / notes * SR)
        out[i0:i0 + n] += sig
    if echo:
        e = out.copy()
        for d, g in ((0.21, 0.5), (0.43, 0.3), (0.68, 0.18), (0.95, 0.10)):
            k = int(d * SR)
            out[k:] += g * sosfilt(butter(1, 4200, fs=SR, output="sos"), e[:len(out) - k])
    return out / (np.max(np.abs(out)) or 1.0)


def synth_snare(dur=0.16, seed=0):
    rng = np.random.default_rng(seed)
    n = int(dur * SR)
    t = np.arange(n) / SR
    noise = _hp(rng.standard_normal(n), 1800, 7500) * np.exp(-t / 0.045)
    body = np.sin(2 * np.pi * 190 * t) * np.exp(-t / 0.03) * 0.5
    return (noise + body).astype(np.float64)


def synth_brass(midi, dur, vel=1.0, tail=0.35):
    n = int((dur + tail) * SR)
    t = np.arange(n) / SR
    out = np.zeros(n)
    f0 = audio.midi_to_hz(midi)
    for cents in (-7.0, 0.0, 6.0):
        f = f0 * 2 ** (cents / 1200.0) * (1 + 0.003 * np.sin(2 * np.pi * 5.4 * t) * np.minimum(1.0, t / 0.3))
        ph = 2 * np.pi * np.cumsum(f) / SR
        for hmn in range(1, 14):
            if f0 * hmn > 6000:
                break
            bright = 0.35 + 0.65 * np.minimum(1.0, t / 0.09)                # brass: brightens after the attack
            out += (1.0 / hmn) * bright ** (hmn * 0.25) * np.sin(hmn * ph)
    env = np.minimum(1.0, t / 0.035) * np.where(t < dur, 1.0, np.exp(-(t - dur) / 0.12))
    return vel * out * env / 3.0


def build_bed():
    n = int((T_LOOP + 3.5) * SR)
    buf = np.zeros(n)

    def put(sig, t0, g=1.0):
        i0 = int(t0 * SR)
        i1 = min(i0 + len(sig), n)
        if i0 < n and i1 > i0:
            buf[i0:i1] += g * sig[:i1 - i0]
    beat = 0.5
    sn = [synth_snare(seed=i) for i in range(4)]
    ends = [ts for _, ts, _ in STAGES[1:]] + [T_DONE]
    steps, gains = [2, 1, 0.5, 0.25, 0.25], [0.30, 0.42, 0.55, 0.68, 0.82]
    for (t0, t1), step, g in zip(zip([ts for _, ts, _ in STAGES], ends), steps, gains):   # march: busier every round
        t = t0 + (beat if step == 2 else 0.0)
        k = 0
        while t < t1 - 1e-6:
            gg = g * (1.0 + 0.9 * (t - t0) / (t1 - t0) * (1 if step < 1 else 0.0))
            put(sn[k % 4], t, gg * (1.25 if (k % 4 == 0 and step <= 1) else 1.0))
            t += step * beat if step != 2 else 2 * beat
            k += 1
    for tt in (T_DONE, T_DONE + 0.09):                                       # a flam at the finish
        put(sn[0], tt, 0.9)
    t = T_DONE + 0.5
    while t < T_MORPH + 0.6:                                                 # a roll that dies down into the loop
        put(sn[int(t * 8) % 4], t, 0.55 * max(0.0, T_MORPH + 0.8 - t) / 1.5)
        t += 0.0625
    triads = [(60, 64, 67), (64, 67, 72), (67, 72, 76), (72, 76, 79), (76, 79, 84)]     # climbs every round
    for (_, t0, _), (a, b, c3), g in zip(STAGES, triads, (0.55, 0.62, 0.72, 0.80, 0.88)):
        for m, dt, d in ((a, 0.0, 0.5), (b, 0.5, 0.5), (c3, 1.0, 1.4)):
            put(synth_brass(m, d), t0 + dt, g)
    for m in (36, 48, 55, 60, 64, 67, 72):                                   # the finish chord
        put(synth_brass(m, 1.7, tail=0.6), T_DONE, 0.75)
    put(synth_cry(0.85, seed=3, notes=2), 0.0, 0.85)
    put(synth_cry(1.05, seed=9, f0=3600.0, f1=1500.0, notes=1, echo=True), T_DONE, 1.15)
    n_clip = int(T_LOOP * SR)
    buf[: n - n_clip] += buf[n_clip:]                                        # fold the tails over the seam
    return (buf[:n_clip] * 0.30).astype(np.float32)


def build_events(layout):
    """A subtle mechanical tick under the music (6/s)."""
    return [{"t": round(0.08 + i / 6.0, 4), "note": 60, "note_gain": 0.0, "pok": 0.35, "pok_gain": 0.22,
             "gain": 0.4, "x": layout.w / 2} for i in range(int(T_LOOP * 6) - 1)]


# --- main ----------------------------------------------------------------------------------

def main():
    label = arg("--label", "v1")
    studio.OUT_DIR.mkdir(exist_ok=True)
    layout = get_layout("vertical")
    sc = Scene(layout)
    print(f"[{SCENE}] path samples {NS}, errors: " + ", ".join(f"N={n}: {e:.2f}%" for n, e in ERR.items()))
    if kit.has("--still"):
        f = int(arg("--frame", "600"))
        png = studio.OUT_DIR / f"{SCENE}_{label}_f{f}_{layout.tag}.png"
        sc.draw(f)
        studio.save_still(sc.canvas, png)
        print(f"[{SCENE}] -> {png}")
        return
    name = f"{SCENE}_{label}_{layout.tag}"
    video = studio.OUT_DIR / f"{name}_silent.mp4"
    writer = VideoWriter(video, sc.canvas, FPS)
    nf = int(round(T_LOOP * FPS))
    for f in range(nf):
        sc.draw(f)
        writer.write_frame()
    writer.close()
    kit.deliver_loop(SCENE, name, layout, video, build_events(layout), T_LOOP, bed=build_bed())


if __name__ == "__main__":
    main()
