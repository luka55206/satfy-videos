"""GEORGIA FOURIER — one chain of spinning circles draws the outline of Georgia (the country), N = 2, 6, 16, 64.

Owner brief (2026-10-22): midnight-navy dotted grid, thin glowing vectors (amber = big circles, magenta = mid, cyan =
small), monospaced HUD (top-left "Fourier Series / N = …", bottom-right "error: …%", faint formula bottom-centre),
ghost map underneath, four drawings with more circles each, old trail dissolves into particles between cycles,
final cycle locks onto the ghost map and glows, slow push-in on the last cycle. Calm, precise.
The outline is our own approximate trace from known border coordinates (lon/lat), not map data.
The chain is the complex Fourier series z(t) = Σ cₙ e^{i n t} of that closed outline, terms sorted by size.
Loop: after the final glow the outline dissolves into particles and the 2-circle chain re-forms = frame 0.
Audio (original synthesis): soft pad, slow arpeggio, a light mechanical click that speeds up with N, a chime each
time an outline closes.
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

SCENE = "georgia_fourier"
AMBER, MAGENTA, CYAN = (1.0, 0.70, 0.28), (1.0, 0.35, 0.80), (0.30, 0.90, 1.0)
NAVY = (0.025, 0.035, 0.085)
FONT = "Consolas"
# (N circles, start, draw seconds)
STAGES = [(2, 0.0, 2.3), (6, 2.75, 2.5), (16, 5.7, 2.8), (64, 8.9, 3.5)]
T_LOCK = 12.4            # final outline closes
T_DISSOLVE = 14.3        # outline turns into particles -> back to frame 0
T_LOOP = 15.0
NS = 4096

# --- Georgia, approximate border (lon, lat), clockwise from the Psou river on the Black Sea --------------------------
GEO = [(40.00, 43.38), (40.25, 43.57), (40.70, 43.55), (41.20, 43.38), (41.60, 43.23), (42.00, 43.20), (42.45, 43.22),
       (42.85, 43.15), (43.20, 42.95), (43.60, 42.85), (43.85, 42.75), (44.25, 42.70), (44.55, 42.73), (44.80, 42.62),
       (45.15, 42.70), (45.45, 42.55), (45.75, 42.47), (45.65, 42.20), (46.05, 41.98), (46.45, 41.90), (46.70, 41.80),
       (46.50, 41.60), (46.30, 41.45), (46.15, 41.20), (45.95, 41.15), (45.70, 41.32), (45.20, 41.42), (45.00, 41.30),
       (44.80, 41.20), (44.50, 41.18), (44.15, 41.22), (43.75, 41.15), (43.45, 41.10), (43.20, 41.30), (42.85, 41.50),
       (42.55, 41.45), (42.20, 41.48), (41.85, 41.45), (41.55, 41.53), (41.62, 41.65), (41.75, 41.90), (41.65, 42.15),
       (41.55, 42.40), (41.45, 42.65), (41.10, 42.85), (41.00, 43.00), (40.70, 43.10), (40.30, 43.25)]


def outline():
    lat0 = math.radians(42.3)
    P = np.array([complex(lon * math.cos(lat0), lat) for lon, lat in GEO])
    P = np.concatenate([P, P[:1]])
    seg = np.abs(np.diff(P))
    cum = np.concatenate([[0], np.cumsum(seg)])
    u = np.linspace(0, cum[-1], NS, endpoint=False)
    idx = np.clip(np.searchsorted(cum, u, side="right") - 1, 0, len(seg) - 1)
    f = (u - cum[idx]) / np.maximum(seg[idx], 1e-9)
    Z = P[idx] + (P[idx + 1] - P[idx]) * f
    return Z - Z.mean()


Z = outline()
C = np.fft.fft(Z) / NS
FREQ = np.fft.fftfreq(NS, d=1.0 / NS).astype(int)
ORDER = [i for i in np.argsort(-np.abs(C)) if FREQ[i] != 0]          # biggest circles first (no DC: centred)
DIAG = float(np.hypot(np.ptp(Z.real), np.ptp(Z.imag)))
SF = np.arange(1200) / 1200


def curve(n):
    sel = ORDER[:n]
    return (C[sel][None, :] * np.exp(2j * np.pi * SF[:, None] * FREQ[sel][None, :])).sum(1)


def err_pct(n):
    rec = curve(n)
    orig = Z[(SF * NS).astype(int)]
    return float(np.mean(np.abs(rec - orig)) / DIAG * 100)


CURVES = {n: curve(n) for n, _, _ in STAGES}
ERR = {n: err_pct(n) for n, _, _ in STAGES}


def stage_at(t):
    for i in range(len(STAGES) - 1, -1, -1):
        if t >= STAGES[i][1]:
            return i
    return 0


class Scene:
    def __init__(self, layout):
        self.L = layout
        self.canvas = Canvas(layout.w, layout.h, studio.render_scale())
        w, h = layout.w, layout.h
        self.S = w * 0.84 / float(np.ptp(Z.real))
        self.cx, self.cy = w / 2, h * 0.455
        rng = np.random.default_rng(4)
        self.part = rng.uniform(-1, 1, (900, 2))                        # particle drift directions

    def P(self, z, zoom):
        return self.cx + self.S * zoom * z.real, self.cy - self.S * zoom * z.imag

    def text(self, s, x, y, size, col, alpha=1.0, align="left"):
        ctx = self.canvas.ctx
        ctx.select_font_face(FONT, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        ctx.set_font_size(size)
        ext = ctx.text_extents(s)
        if align == "right":
            x -= ext.x_advance
        elif align == "center":
            x -= ext.x_advance / 2
        ctx.set_source_rgba(*col, alpha)
        ctx.move_to(x, y)
        ctx.show_text(s)

    def particles(self, pts, u, col, zoom):
        """the old trail dissolves: every point drifts and fades"""
        c = self.canvas
        k = max(1, len(pts) // 450)
        for j, p in enumerate(pts[::k]):
            d = self.part[j % len(self.part)]
            x, y = self.P(p, zoom)
            x += d[0] * 60 * u
            y += d[1] * 60 * u - 30 * u
            c.circle(x, y, 2.4 * (1 - 0.5 * u), col, alpha=0.9 * (1 - u))

    def draw(self, f):
        L, c = self.L, self.canvas
        w, h = L.w, L.h
        t = f * DT
        ctx = c.ctx
        ctx.set_source_rgb(*NAVY)
        ctx.paint()
        g = cairo.RadialGradient(w / 2, h * 0.45, 0, w / 2, h * 0.45, h * 0.6)
        g.add_color_stop_rgba(0.0, 0.08, 0.10, 0.22, 0.55)
        g.add_color_stop_rgba(1.0, 0.0, 0.0, 0.0, 0.0)
        ctx.set_source(g)
        ctx.paint()
        step = w / 24                                                     # faint dotted grid
        for gx in np.arange(step / 2, w, step):
            for gy in np.arange(step / 2, h, step):
                ctx.rectangle(gx - 1, gy - 1, 2, 2)
        ctx.set_source_rgba(0.55, 0.65, 1.0, 0.12)
        ctx.fill()

        i = stage_at(t)
        n, ts, dur = STAGES[i]
        last = i == len(STAGES) - 1
        s = min(1.0, (t - ts) / dur)
        zoom = 1.0 + 0.10 * smooth((t - STAGES[-1][1]) / 4.0) if last else 1.0
        if t >= T_DISSOLVE:
            zoom = 1.10 - 0.10 * smooth((t - T_DISSOLVE) / (T_LOOP - T_DISSOLVE))
        lock = smooth((t - T_LOCK) / 0.5) if last else 0.0
        lock *= 1.0 - smooth((t - T_DISSOLVE) / (T_LOOP - T_DISSOLVE - 2 * DT))   # back to the frame-0 look
        # ghost map
        ghost = [self.P(z, zoom) for z in Z[::8]]
        c.poly(ghost, (0.45, 0.55, 0.9), alpha=0.06 + 0.10 * lock)
        c.polylines([ghost + [ghost[0]]], (0.55, 0.65, 1.0), width=2, alpha=0.12 + 0.35 * lock)

        cur = CURVES[n]
        # previous outline dissolving (first 0.6 s of a stage), or the final outline at the loop end
        if i > 0 and t - ts < 0.6:
            pn = STAGES[i - 1][0]
            self.particles(CURVES[pn], (t - ts) / 0.6, CYAN, zoom)
        if t >= T_DISSOLVE:
            self.particles(CURVES[64], (t - T_DISSOLVE) / (T_LOOP - T_DISSOLVE), CYAN, zoom)

        # the trail (bright near the pen, fading behind it)
        if t < T_DISSOLVE:
            m = len(SF) if (last and t >= T_LOCK) else max(2, int(s * len(SF)))
            pts = [self.P(z, zoom) for z in cur[:m]]
            if m >= 2:
                segs = 24
                for q in range(segs):
                    a0 = int(q * (m - 1) / segs)
                    a1 = int((q + 1) * (m - 1) / segs) + 1
                    fade = 0.35 + 0.65 * ((q + 1) / segs) if s < 1 else 1.0
                    c.polylines([pts[a0:a1]], CYAN, width=9 + 10 * lock, alpha=0.10 * fade + 0.15 * lock)
                    c.polylines([pts[a0:a1]], CYAN, width=3.2, alpha=0.95 * fade)
        # the chain
        chain_a = 1.0 - smooth((t - T_LOCK - 0.3) / 0.8) if last else 1.0
        if t >= T_DISSOLVE:
            chain_a = smooth((t - T_DISSOLVE) / (T_LOOP - T_DISSOLVE))
        if chain_a > 0.01:
            nn = n if t < T_DISSOLVE else 2
            ss = s if t < T_DISSOLVE else 0.0
            pos = 0j
            sel = ORDER[:nn]
            rmax = max(abs(C[sel[0]]), 1e-9)
            pen = None
            for idx in sel:
                r = abs(C[idx])
                nxt = pos + C[idx] * np.exp(2j * np.pi * FREQ[idx] * ss)
                x0, y0 = self.P(pos, zoom)
                x1, y1 = self.P(nxt, zoom)
                rr = r * self.S * zoom
                frac = r / rmax
                col = AMBER if frac > 0.35 else (MAGENTA if frac > 0.08 else CYAN)
                if rr > 1.0:
                    if frac > 0.35:
                        c.glow(x0, y0, rr * 0.5, AMBER, strength=0.05 * chain_a, reach=2.2)
                    ctx.new_sub_path()
                    ctx.arc(x0, y0, rr, 0, 2 * math.pi)
                    ctx.set_source_rgba(*col, (0.55 if frac > 0.08 else 0.35) * chain_a)
                    ctx.set_line_width(2.0 if frac > 0.08 else 1.3)
                    ctx.stroke()
                c.lines([(x0, y0, x1, y1)], col, width=2.2, alpha=0.85 * chain_a)
                pos = nxt
                pen = (x1, y1)
            if pen and t < T_DISSOLVE:
                c.glow(pen[0], pen[1], 7, CYAN, strength=0.9 * chain_a, reach=3.0)
                c.circle(pen[0], pen[1], 5, (0.9, 1.0, 1.0), alpha=chain_a)
        # closing flash when an outline completes
        for n_, ts_, d_ in STAGES:
            tc = ts_ + d_
            if 0 <= t - tc < 0.35:
                ctx.set_source_rgba(*CYAN, 0.10 * (1 - (t - tc) / 0.35))
                ctx.paint()

        # HUD (monospaced)
        n_show = n if t < T_DISSOLVE else 2
        e_show = ERR[n] if t < T_DISSOLVE else ERR[2]
        self.text("Fourier Series", w * 0.06, h * 0.135, h * 0.026, (0.85, 0.9, 1.0))
        self.text(f"N = {n_show}", w * 0.06, h * 0.172, h * 0.036, AMBER)
        self.text(f"error: {e_show:.2f}%", w * 0.94, h * 0.745, h * 0.026, CYAN, align="right")
        self.text("f(t) = Σ c_n · e^(i n t)", w / 2, h * 0.79, h * 0.021, (0.75, 0.8, 1.0), alpha=0.55, align="center")
        self.text("GEORGIA", w * 0.94, h * 0.172, h * 0.026, (0.85, 0.9, 1.0), alpha=0.55 + 0.45 * lock,
                  align="right")
        self.text("@TheSatFy", w * 0.06, h * 0.745, h * 0.02, (0.85, 0.9, 1.0), alpha=0.35)


def render(layout, out_path, still_frame=None):
    sc = Scene(layout)
    writer = None if still_frame is not None else VideoWriter(out_path, sc.canvas, FPS)
    nf = int(round(T_LOOP * FPS))
    for f in range(nf):
        if still_frame is not None and f != still_frame:
            continue
        sc.draw(f)
        if writer is None:
            studio.save_still(sc.canvas, out_path)
            return f / FPS
        writer.write_frame()
    writer.close()
    return nf / FPS


def build_events(layout):
    ev = []
    P5 = audio.PENTA_MAJOR
    t = 0.0
    k = 0
    while t < T_LOOP - 0.3:                                            # slow arpeggio (C major pentatonic)
        note = 60 + [0, 4, 7, 12, 7, 4][k % 6] + (0 if (k // 6) % 2 == 0 else -3)
        ev.append({"t": round(t, 4), "note": note, "gain": 0.30, "x": layout.w * (0.35 + 0.3 * ((k % 6) / 5))})
        t += 0.5
        k += 1
    for n, ts, dur in STAGES:                                          # clicks, faster with more circles
        rate = {2: 2.0, 6: 3.5, 16: 6.0, 64: 10.0}[n]
        tt = ts + 0.05
        while tt < ts + dur:
            ev.append({"t": round(tt, 4), "note": 60, "note_gain": 0.0, "pok": 0.35, "pok_gain": 0.22,
                       "gain": 0.4, "x": layout.w / 2})
            tt += 1.0 / rate
        tc = ts + dur                                                  # a chime when the outline closes
        for j, m in enumerate((79, 84, 88)):
            ev.append({"t": round(tc + 0.04 * j, 4), "note": m, "gain": 0.45, "x": layout.w / 2})
    return sorted(ev, key=lambda e: e["t"])


def main():
    label = arg("--label", "v1")
    studio.OUT_DIR.mkdir(exist_ok=True)
    layout = get_layout("vertical")
    print(f"[{SCENE}] errors: " + ", ".join(f"N={n}: {e:.2f}%" for n, e in ERR.items()))
    if kit.has("--still"):
        f = int(arg("--frame", "0"))
        png = studio.OUT_DIR / f"{SCENE}_{label}_f{f}_{layout.tag}.png"
        render(layout, png, still_frame=f)
        print(f"[{SCENE}] -> {png}")
        return
    name = f"{SCENE}_{label}_{layout.tag}"
    video = studio.OUT_DIR / f"{name}_silent.mp4"
    d = render(layout, video)
    pad = kit.loop_pad(d, ((48, 1.0), (55, 0.6), (60, 0.45), (64, 0.3)), gain=0.035)
    kit.deliver_loop(SCENE, name, layout, video, build_events(layout), d, voice="glassharp", bed=pad)


if __name__ == "__main__":
    main()
