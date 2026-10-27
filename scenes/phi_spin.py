"""PHI SPIN — two arms, the second turning phi times faster; the line never closes.

Z(theta) = e^(i theta) + e^(i phi theta), phi = 1.618... Two equal glowing arms, end to end,
spin from the centre; the tip draws a light trail. Because phi is irrational the
curve can never repeat, so the petals keep landing in new places and the trail
fills the whole disc. The spin accelerates the whole clip (the escalation rule);
the trail is drawn additively, so where it crosses itself it glows brighter, and
its colour drifts rose -> violet -> teal -> gold as it goes.

NEAR MISSES (v2): after a Fibonacci number of turns F (13, 55, 144) the tip comes back
almost exactly to where the line began, and misses by 2|sin(pi(F*phi - F'))| arm
lengths: 0.21, 0.05, 0.02 — closer every time, never touching. At each one the spin
slows, the camera zooms onto the start point (deeper each time, so the miss reads
the same size on screen), the tip glides past the beginning, then the camera pulls
back and the spin picks up where it left off. While zoomed the trail is redrawn as
vectors, so it stays sharp at 30x.

Loop: the trail dissolves and the arms ease back to the frame-0 pose.

Mechanic taken from the well-known phasor-sum visualisation (maths, not anyone's
look); the look, colour, HUD, zooms, caption and sound are ours.

Audio (original synthesis only): a glass-harp note per full turn of the first arm
(capped ~16/s so it stays calm), a soft high chime at each near miss, a D maj7 chord
at the end, an opening pair, a quiet maj7 sine pad.

    ./run.ps1 -Scene phi_spin -Fast -Still -Frame 1800
    ./run.ps1 -Scene phi_spin -Fast
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

SCENE = "phi_spin"
PHI = (1 + 5 ** 0.5) / 2
DRAW_S = 33.0                    # base-clock length of the spin (zooms pause it, JUMP_S skips it)
FADE_S = 2.5
W0, W1 = 5.0, 110.0              # arm-1 speed, rad/s, at start and at DRAW_S (exponential)
SUB = 0.02                       # trail sampling step in theta (rad)
NOTE_GAP = 0.06                  # sounded-note ceiling (~16/s)
TRAIL = [(1.00, 0.36, 0.55), (0.75, 0.40, 1.00), (0.20, 0.85, 0.90), (1.00, 0.78, 0.40)]
START = (2.0, 0.0)               # where the line begins (both arms at angle 0)

ZOOMS = [(5, "so close…"), (21, "closer…"), (89, "almost…")]   # Fibonacci turns
TZ = 4.0                         # seconds per zoom (in, glide past, out)
RAMP = 1.2                       # zoom in / out time
JUMP_S = 3.0                     # after each zoom the spin resumes this much further up its speed curve
MISS_SCREEN = 0.6                # the miss, on screen, in arm lengths
TIP_SCREEN = 0.9                 # tip speed on screen at full zoom, arm lengths / s
TIP_K = 1.0 + PHI                # |dZ/dtheta| when the arms are aligned


def theta_base(t):
    k = math.log(W1 / W0) / DRAW_S
    t = min(max(t, 0.0), DRAW_S)
    return W0 * (math.exp(k * t) - 1.0) / k


def omega_base(t):
    k = math.log(W1 / W0) / DRAW_S
    return W0 * math.exp(k * min(max(t, 0.0), DRAW_S))


def z(th):
    return (math.cos(th) + math.cos(PHI * th), math.sin(th) + math.sin(PHI * th))


def zb(tau):
    """Zoom envelope over one zoom: 0 -> 1 (hold) -> 0."""
    return smooth(tau / RAMP) * smooth((TZ - tau) / RAMP)


def _script(w_in, w_slow, n=4000):
    """Cumulative theta advance over one zoom: speed glides log-wise to w_slow and back."""
    tau = np.linspace(0.0, TZ, n + 1)
    env = np.array([zb(x) for x in tau])
    om = np.exp(math.log(w_in) + (math.log(w_slow) - math.log(w_in)) * env)
    cum = np.concatenate([[0.0], np.cumsum((om[1:] + om[:-1]) * 0.5 * (TZ / n))])
    return tau, cum


def closest(F):
    """theta near 2*pi*F where the tip passes closest to START, and that distance.

    The tip comes back almost ALONG the line's first stretch, so the true miss is the
    sideways offset (~delta^2/2), far smaller than |Z(2 pi F) - START|.
    """
    th_k = 2 * math.pi * F
    lo, hi = th_k - 0.6, th_k + 0.6
    for _ in range(6):
        tt = np.linspace(lo, hi, 2001)
        d = np.hypot(np.cos(tt) + np.cos(PHI * tt) - START[0], np.sin(tt) + np.sin(PHI * tt) - START[1])
        i = int(np.argmin(d))
        step = tt[1] - tt[0]
        lo, hi = tt[i] - step, tt[i] + step
    return float(tt[i]), float(d[i])


def simulate():
    th_l, zoom_l, cx_l, cy_l, zb_l, zi_l = [], [], [], [], [], []
    th, tb = 0.0, 0.0
    zi, script = 0, None
    misses = []
    while True:
        if script is None:
            if tb >= DRAW_S - 1e-9:
                break
            tb2 = tb + DT
            th2 = th + theta_base(tb2) - theta_base(tb)
            if zi < len(ZOOMS):
                F = ZOOMS[zi][0]
                th_k, gap = closest(F)
                q = z(th_k)
                zmax = MISS_SCREEN / gap
                w_in = omega_base(tb2)
                tau, cum = _script(w_in, TIP_SCREEN / (TIP_K * zmax))
                half = float(np.interp(TZ / 2, tau, cum))
                if th2 >= th_k - half:
                    th2 = th_k - half
                    mid = ((q[0] + START[0]) / 2, (q[1] + START[1]) / 2)
                    script = {"tau": 0.0, "t_tab": tau, "cum": cum, "th0": th2, "zmax": zmax,
                              "mid": mid, "zi": zi}
                    misses.append({"F": F, "gap": gap, "zmax": zmax, "f_mid": None})
                    zi += 1
            th, tb = th2, tb2
            th_l.append(th); zoom_l.append(1.0); cx_l.append(0.0); cy_l.append(0.0)
            zb_l.append(0.0); zi_l.append(-1)
        else:
            s = script
            s["tau"] += DT
            tau = min(s["tau"], TZ)
            th = s["th0"] + float(np.interp(tau, s["t_tab"], s["cum"]))
            e = zb(tau)
            zoom = math.exp(math.log(s["zmax"]) * e)
            w = (1.0 - 1.0 / zoom) / (1.0 - 1.0 / s["zmax"])
            if misses[-1]["f_mid"] is None and tau >= TZ / 2:
                misses[-1]["f_mid"] = len(th_l)
            th_l.append(th); zoom_l.append(zoom); cx_l.append(s["mid"][0] * w)
            cy_l.append(s["mid"][1] * w); zb_l.append(e); zi_l.append(s["zi"])
            if s["tau"] >= TZ - 1e-9:
                script = None
                tb += JUMP_S                             # come back out faster than we went in
    nd = len(th_l)
    nf = nd + int(round(FADE_S * FPS))
    pad_n = nf - nd
    th_l += [th_l[-1]] * pad_n
    zoom_l += [1.0] * pad_n; cx_l += [0.0] * pad_n; cy_l += [0.0] * pad_n
    zb_l += [0.0] * pad_n; zi_l += [-1] * pad_n
    return {"th": np.array(th_l), "zoom": np.array(zoom_l), "cx": np.array(cx_l),
            "cy": np.array(cy_l), "zb": np.array(zb_l), "zi": np.array(zi_l),
            "nd": nd, "nf": nf, "misses": misses, "th_end": th_l[nd - 1]}


def trail_col(u):
    n = len(TRAIL)
    f = (u % 1.0) * n
    i = int(f) % n
    k = f - int(f)
    a, b = TRAIL[i], TRAIL[(i + 1) % n]
    return tuple(a[j] + (b[j] - a[j]) * k for j in range(3))


def _chunks(sim):
    """Per drawing frame: world-space points of the trail drawn in that frame + its style."""
    th, out = sim["th"], []
    for f in range(1, sim["nd"]):
        a0, a1 = th[f - 1], th[f]
        n = max(1, int(math.ceil((a1 - a0) / SUB)))
        tt = a0 + (a1 - a0) * np.arange(n + 1) / n
        xs = np.cos(tt) + np.cos(PHI * tt)
        ys = np.sin(tt) + np.sin(PHI * tt)
        u = a1 / sim["th_end"]
        out.append({"a0": a0, "a1": a1, "x": xs, "y": ys, "col": trail_col(u * 1.6), "fade": 1.0 - 0.75 * u,
                    "box": (xs.min(), xs.max(), ys.min(), ys.max())})
    return out


class Scene:
    def __init__(self, layout, sim):
        self.L, self.sim = layout, sim
        w, h = layout.w, layout.h
        self.vertical = h > w
        self.unit = (w * 0.21) if self.vertical else (h * 0.195)
        self.cx, self.cy = w / 2, h * (0.47 if self.vertical else 0.535)
        self.canvas = Canvas(w, h, studio.render_scale())
        c = self.canvas
        self.trail, self.tctx = self._layer()
        self.vec, self.vctx = self._layer()
        self.chunks = _chunks(sim)
        self.done = 0                    # chunks already on the persistent raster

    def _layer(self):
        c = self.canvas
        s = cairo.ImageSurface(cairo.FORMAT_ARGB32, c.pw, c.ph)
        ctx = cairo.Context(s)
        ctx.scale(c.pw / self.L.w, c.ph / self.L.h)
        ctx.set_operator(cairo.OPERATOR_ADD)
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.set_line_join(cairo.LINE_JOIN_ROUND)
        return s, ctx

    def mapper(self, f):
        k = self.unit * self.sim["zoom"][f]
        cx0, cy0 = self.sim["cx"][f], self.sim["cy"][f]
        return lambda x, y: (self.cx + (x - cx0) * k, self.cy - (y - cy0) * k)

    @staticmethod
    def _stroke(ctx, xs, ys, ch):
        ctx.move_to(xs[0], ys[0])
        for x, y in zip(xs[1:], ys[1:]):
            ctx.line_to(x, y)
        ctx.set_source_rgba(*ch["col"], 0.10 * ch["fade"])
        ctx.set_line_width(7.0)
        ctx.stroke_preserve()
        ctx.set_source_rgba(*ch["col"], 0.55 * ch["fade"])
        ctx.set_line_width(1.8)
        ctx.stroke()

    def advance_trail(self, f):
        """Persistent raster of the trail at zoom 1 (used whenever the camera is home)."""
        while self.done < min(f, self.sim["nd"] - 1):
            ch = self.chunks[self.done]
            self._stroke(self.tctx, self.cx + ch["x"] * self.unit, self.cy - ch["y"] * self.unit, ch)
            self.done += 1

    def vector_trail(self, f):
        """The trail so far, redrawn sharp through the zoomed camera (culled to the view)."""
        ctx = self.vctx
        ctx.save()
        ctx.set_operator(cairo.OPERATOR_CLEAR)
        ctx.paint()
        ctx.restore()
        k = self.unit * self.sim["zoom"][f]
        cx0, cy0 = self.sim["cx"][f], self.sim["cy"][f]
        hw, hh = (self.L.w / 2 + 20) / k, (self.L.h / 2 + 20) / k
        x0, x1 = cx0 - hw, cx0 + hw
        y0, y1 = cy0 - (self.L.h - self.cy + 20) / k, cy0 + (self.cy + 20) / k
        for ch in self.chunks[:min(f, self.sim["nd"] - 1)]:
            bx0, bx1, by0, by1 = ch["box"]
            if bx1 < x0 or bx0 > x1 or by1 < y0 or by0 > y1:
                continue
            if k * TIP_K * SUB < 6.0:                    # coarse samples are still smooth here
                self._stroke(ctx, self.cx + (ch["x"] - cx0) * k, self.cy - (ch["y"] - cy0) * k, ch)
                continue
            # deep zoom: re-trace only the stretches inside the view, ~2 px per sample
            xs, ys = ch["x"], ch["y"]
            m = TIP_K * SUB
            inside = (xs > x0 - m) & (xs < x1 + m) & (ys > y0 - m) & (ys < y1 + m)
            if not inside.any():
                continue
            n = len(xs) - 1
            idx = np.nonzero(inside)[0]
            runs, start, prev = [], idx[0], idx[0]
            for i in idx[1:]:
                if i != prev + 1:
                    runs.append((start, prev)); start = i
                prev = i
            runs.append((start, prev))
            for i0, i1 in runs:
                i0, i1 = max(0, i0 - 1), min(n, i1 + 1)
                ta = ch["a0"] + (ch["a1"] - ch["a0"]) * i0 / n
                tb = ch["a0"] + (ch["a1"] - ch["a0"]) * i1 / n
                cnt = int(min(200000, max(2, (tb - ta) * TIP_K * k / 2.0)))
                tt = np.linspace(ta, tb, cnt)
                fx = np.cos(tt) + np.cos(PHI * tt)
                fy = np.sin(tt) + np.sin(PHI * tt)
                ok = (fx > x0) & (fx < x1) & (fy > y0) & (fy < y1)
                if ok.sum() < 2:
                    continue
                j = np.nonzero(ok)[0]
                j0, j1 = max(0, j[0] - 1), min(cnt - 1, j[-1] + 1)
                self._stroke(ctx, self.cx + (fx[j0:j1 + 1] - cx0) * k,
                             self.cy - (fy[j0:j1 + 1] - cy0) * k, ch)
        return self.vec

    def draw(self, f, rule):
        L, c, sim = self.L, self.canvas, self.sim
        nd = sim["nd"]
        t = f * DT
        e = smooth((f - nd) / (sim["nf"] - 1 - nd)) if f >= nd else 0.0
        zoom, zbe = sim["zoom"][f], sim["zb"][f]
        self.advance_trail(f)
        w, h = L.w, L.h
        g = cairo.RadialGradient(w / 2, self.cy, 0, w / 2, self.cy, max(w, h) * 0.7)
        g.add_color_stop_rgb(0.0, 0.05, 0.03, 0.10)
        g.add_color_stop_rgb(1.0, 0.00, 0.00, 0.02)
        c.ctx.set_source(g)
        c.ctx.paint()
        layer = self.vector_trail(f) if zoom > 1.0005 else self.trail
        c.ctx.save()
        c.ctx.identity_matrix()
        c.ctx.set_source_surface(layer, 0, 0)
        c.ctx.paint_with_alpha(1.0 - e)
        c.ctx.restore()

        P = self.mapper(f)
        # arms: real angle while drawing, eased back to the frame-0 pose in the dissolve
        th = sim["th"][min(f, nd - 1)]
        a1, a2 = th, PHI * th
        if e > 0:
            a1 = a1 + (round(a1 / (2 * math.pi)) * 2 * math.pi - a1) * e
            a2 = a2 + (round(a2 / (2 * math.pi)) * 2 * math.pi - a2) * e
        if f == sim["nf"] - 1:
            a1, a2 = 0.0, 0.0
        j1 = (math.cos(a1), math.sin(a1))
        tipw = (j1[0] + math.cos(a2), j1[1] + math.sin(a2))
        p0, p1, p2 = P(0.0, 0.0), P(*j1), P(*tipw)
        om = (sim["th"][min(f + 1, nd - 1)] - sim["th"][max(f - 1, 0)]) / (2 * DT) if f < nd else 0.0
        arm_a = 1.0 if f >= nd else max(0.18, min(1.0, (45.0 - om) / 25.0))
        arm_a *= 1.0 - zbe                               # arms step aside in the close-ups
        tip = trail_col(th / sim["th_end"] * 1.6)
        segs = [(p0[0], p0[1], p1[0], p1[1]), (p1[0], p1[1], p2[0], p2[1])]
        if arm_a > 0.003:
            c.lines(segs, (1, 1, 1), width=10, alpha=0.06 * arm_a)
            c.lines(segs, (0.95, 0.93, 1.0), width=3, alpha=0.85 * arm_a)
            c.circle(*p1, 6, (1, 1, 1), alpha=0.85 * arm_a)
        if zoom < 1.5:
            c.circle(*p0, 7, (1, 1, 1), alpha=0.9 * (1.0 - zbe))

        gold = (1.0, 0.80, 0.45)
        if zbe > 0.002 and f < nd:
            # the two ENDS that almost meet: the line's first stretch (gold) and its newest
            # stretch (white), so the miss reads among hundreds of crossing lines
            span = 3.0 / (TIP_K * zoom)
            for a0, a1, col, wd in ((0.0, span, gold, 3.0), (max(0.0, th - span), th, (1, 1, 1), 2.6)):
                tt = np.linspace(a0, a1, 80)
                pts = [P(math.cos(v) + math.cos(PHI * v), math.sin(v) + math.sin(PHI * v)) for v in tt]
                c.polylines([pts], col, width=wd * 4, alpha=0.10 * zbe)
                c.polylines([pts], col, width=wd, alpha=0.90 * zbe)

        # where the line began: a small gold mark, glowing while the camera is on it
        s0 = P(*START)
        c.glow(*s0, 6, gold, strength=0.15 + 0.45 * zbe, reach=3.5 + 3.0 * zbe)
        c.ring(*s0, 7 + 3 * zbe, gold, width=2.0, alpha=0.55 + 0.4 * zbe)

        c.glow(*p2, 8, tip, strength=0.7, reach=4.0)
        c.circle(*p2, 6, (1, 1, 1), alpha=0.95)

        # HUD (0 at frame 0 and at the seam)
        hud = smooth(t / 0.4) * (1.0 - e)
        turns = int(th / (2 * math.pi))
        if self.vertical:
            eq_y, phi_y, cnt_y, lab_y, sz = h * 0.172, h * 0.200, h * 0.765, h * 0.665, w * 0.040
        else:
            eq_y, phi_y, cnt_y, lab_y, sz = h * 0.055, h * 0.093, h * 0.58, h * 0.84, w * 0.020
        c.text_centered("Z(θ) = e^(iθ) + e^(iφθ)", eq_y, size=sz, color=(0.96, 0.93, 0.98), alpha=hud, bold=False)
        c.text_centered("φ = 1.6180339887…", phi_y, size=sz * 0.8, color=gold, alpha=hud, bold=False)
        c.text_centered(f"turns: {turns:,}", cnt_y, size=sz * 1.2, color=(1, 1, 1), alpha=hud,
                        cx=None if self.vertical else L.cnt_x)        # 16:9: right side panel
        zi = int(sim["zi"][f])
        if zi >= 0:
            c.text_centered(ZOOMS[zi][1], lab_y, size=sz * 1.25, color=(1.0, 0.86, 0.90),
                            alpha=smooth((zbe - 0.55) / 0.35), bold=False)
        if rule:
            c.caption(rule, alpha=hud, layout=L)
        c.watermark(L)


def render(layout, sim, out_path, rule, still_frame=None):
    sc = Scene(layout, sim)
    writer = None if still_frame is not None else VideoWriter(out_path, sc.canvas, FPS)
    for f in range(sim["nf"]):
        if still_frame is not None and f != still_frame:
            sc.advance_trail(f)
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
    th, nd = sim["th"], sim["nd"]
    out = [{"t": 0.02, "note": 50, "gain": 0.45, "x": layout.w / 2},
           {"t": 0.07, "note": 62, "gain": 0.40, "x": layout.w / 2}]
    k, last = 1, -1e9
    for f in range(1, nd):
        while th[f] >= k * 2 * math.pi:
            t = f * DT
            if t - last >= NOTE_GAP:
                last = t
                x = layout.w * (0.5 + 0.3 * math.cos(PHI * th[f]))
                out.append({"t": round(t, 4), "note": walker.next(),
                            "gain": round(0.36 + 0.18 * th[f] / sim["th_end"], 3), "x": round(x, 1)})
            k += 1
    for m in sim["misses"]:                              # the near miss: a soft high chime
        t = m["f_mid"] * DT
        for j, note in enumerate((50, 81, 86)):
            out.append({"t": round(t + 0.05 * j, 4), "note": note, "gain": 0.42, "x": layout.w / 2})
    t_end = nd * DT
    for j, note in enumerate((50, 57, 61, 66)):          # D maj7 as the trail dissolves
        out.append({"t": round(t_end + 0.06 * j, 4), "note": note, "gain": 0.45, "x": layout.w / 2})
    return sorted(out, key=lambda e: e["t"])


def pad(sim):
    """Quiet D maj7 sine pad, decays to silence before the loop seam."""
    sr = audio.SR
    dur = sim["nf"] / FPS
    t = np.arange(int(dur * sr)) / sr
    sig = np.zeros_like(t)
    for m, amp in ((50, 1.0), (57, 0.7), (61, 0.45), (66, 0.35)):
        f0 = audio.midi_to_hz(m)
        sig += amp * (np.sin(2 * np.pi * f0 * t) + 0.5 * np.sin(2 * np.pi * f0 * 1.003 * t))
    lfo = 0.85 + 0.15 * np.sin(2 * np.pi * 0.1 * t)
    env = np.clip(t / 0.5, 0, 1) * np.clip((dur - 0.6 - t) / 2.5, 0, 1) ** 2
    return (0.016 * sig * lfo * env).astype(np.float32)


def _worker(o, sim, label, rule):
    layout = get_layout(o)
    name = f"{SCENE}_{label}_{layout.tag}"
    video = studio.OUT_DIR / f"{name}_silent.mp4"
    d = render(layout, sim, video, rule)
    kit.deliver(SCENE, name, layout, video, build_events(sim, layout), d, True,
                voice="glassharp", bed=pad(sim))


def main():
    label, rule = arg("--label", "v2"), arg("--rule", "")
    studio.OUT_DIR.mkdir(exist_ok=True)
    sim = simulate()
    if kit.has("--still"):
        layout = get_layout(kit.orients()[0])
        f = int(arg("--frame", "1800"))
        png = studio.OUT_DIR / f"{SCENE}_{label}_f{f}_{layout.tag}.png"
        render(layout, sim, png, rule, still_frame=f)
        print(f"[{SCENE}] -> {png}")
        return
    ev = build_events(sim, get_layout("vertical"))
    print(f"[{SCENE}] {sim['nf'] / FPS:.2f}s turns={sim['th_end'] / 6.2832:.0f} "
          f"per5s={kit.density_report(ev, sim['nd'] * DT)}")
    for m in sim["misses"]:
        print(f"  miss F={m['F']} gap={m['gap']:.4f} zoom={m['zmax']:.1f}x at {m['f_mid'] * DT:.2f}s")
    kit.fan_out(_worker, (sim, label, rule), SCENE)


if __name__ == "__main__":
    main()
