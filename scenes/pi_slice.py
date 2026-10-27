"""PI SLICE - "The hidden pizza slice": why the bangs count digits of pi (the same two blocks as scenes/pi_blocks*.py).

Rescale the positions by the square roots of the masses (q1 = sqrt(m) x1, q2 = sqrt(M) x2) and the pair of blocks is
ONE point moving in a straight line inside a pizza SLICE of angle theta = arctan(sqrt(m/M)); every bang is the point
bouncing off a side of the slice (kinetic energy = speed^2/2, so the speed never changes). Unfold the slice by
mirroring it at every bounce and the zig-zag becomes ONE straight line crossing slice after slice. The line sweeps a
half turn (180 degrees = pi), so it crosses about pi / theta slices: that is the number of bangs.
    M = 16 kg        theta = 14.04 deg   pi / theta = 12.8   -> 12 bangs   (the slices flip open like a fan)
    M = 10,000 kg    theta = 0.573 deg                       -> 314 bangs
    M = 1,000,000 kg theta = 0.0573 deg                      -> 3,141 bangs
Everything on screen comes from this geometry (block positions in round 1 are the folded point, so the blocks bang
exactly when the dot bounces). Cross-fades into frame 0 (loop).
Audio (original): a click per bang (wall / block pitched differently), a soft whoosh as the slices open, a chime when a
round's count is final, a quiet loop pad.
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

SCENE = "pi_slice"
CYAN, GOLD, PINK, WHITE, LIME, VIOLET = ((0.35, 0.85, 1.0), (1.0, 0.8, 0.3), (1.0, 0.45, 0.6), (1, 1, 1),
                                         (0.55, 1.0, 0.55), (0.62, 0.45, 1.0))
ROUNDS = [(16.0, 7.9), (1e4, 5.7), (1e6, 5.4)]               # (M kg, seconds on screen); m = 1 kg
R_START = np.concatenate([[0.0], np.cumsum([d for _, d in ROUNDS])])
T_LOOP = float(R_START[-1])
S1, X0P = 0.065, 0.2                                         # block size, the small block's start (as pi_blocks3)
GAP = 0.03


def theta_of(M):
    return math.atan(1.0 / math.sqrt(M))


def bangs_of(M):
    return int(math.pi / theta_of(M))


def beta0_of(M):
    """polar angle (from the q2 axis, clockwise) of the start: the first slice"""
    return math.atan2(X0P, (X0P + GAP + S1 - S1) * math.sqrt(M))


def progress(i, u):
    """-> (beta, unfold 0..1) at u seconds into round i. beta sweeps the half turn at an even rate."""
    M = ROUNDS[i][0]
    b0, b1 = beta0_of(M), math.pi - 1e-3
    a, b = {0: (0.55, 3.35), 1: (0.7, 4.3), 2: (0.6, 3.9)}[i]
    q = min(1.0, max(0.0, (u - a) / (b - a)))
    beta = b0 + (b1 - b0) * q
    unf = smooth((u - 3.95) / 1.7) if i == 0 else 1.0
    return beta, unf, q


def slice_pts(R, b0, b1, n=14):
    return [(R * math.sin(b0 + (b1 - b0) * j / n), -R * math.cos(b0 + (b1 - b0) * j / n)) for j in range(n + 1)]


def fold_angle(beta, th):
    k = int(beta // th)
    s = beta - k * th
    return k, (s if k % 2 == 0 else th - s)


class Scene:
    def __init__(self, layout, sim=None):
        self.L = layout
        self.canvas = Canvas(layout.w, layout.h, studio.render_scale())

    def frame(self, t):
        L, c = self.L, self.canvas
        w, h = L.w, L.h
        ctx = c.ctx
        ctx.set_source_rgb(0, 0, 0)
        ctx.paint()
        i = min(len(ROUNDS) - 1, int(np.searchsorted(R_START, t, side="right") - 1))
        u = t - R_START[i]
        M = ROUNDS[i][0]
        th = theta_of(M)
        K = bangs_of(M)
        beta, unf, q = progress(i, u)
        k, phi = fold_angle(beta, th)
        k = min(k, K)
        R = h * 0.145
        ax, ay = w * 0.5 - R * 0.55, h * 0.568
        # ---- title
        pop = math.exp(-u / 0.18)
        c.text_centered(f"M = {M:,.0f} kg", h * 0.233, size=w * 0.062 * (1 + 0.3 * pop), color=GOLD)
        c.text_centered("m = 1 kg  ·  a wall  ·  no friction", h * 0.262, size=w * 0.03, color=CYAN, bold=False)
        # ---- round 1: the blocks, driven by the same geometry (the folded dot)
        if i == 0:
            r = X0P / math.sin(max(beta, 1e-3))
            x1 = r * math.sin(phi)
            x2 = r * math.cos(phi) / math.sqrt(M) + S1
            wx, gy, TW = w * 0.07, h * 0.362, w * 0.9
            sb = min(h * 0.056, w * 0.18)
            c.lines([(wx, h * 0.305, wx, gy), (wx, gy, w * 0.98, gy)], (0.85, 0.88, 1.0), width=3)
            s1 = S1 * TW
            bx1, bx2 = wx + x1 * TW, wx + x2 * TW
            ctx.rectangle(bx1, gy - s1, s1, s1)
            ctx.set_source_rgb(*CYAN)
            ctx.fill()
            if bx2 < w * 1.02:
                ctx.rectangle(bx2, gy - sb, sb, sb)
                ctx.set_source_rgb(*GOLD)
                ctx.fill()
                c.text_centered("M", gy - sb * 0.36, size=sb * 0.42, color=(0.12, 0.08, 0.0), cx=bx2 + sb / 2)
        # ---- the slice picture
        ctx.save()
        ctx.translate(ax, ay)
        disc = [(R * math.sin(b), -R * math.cos(b)) for b in np.linspace(0, math.pi, 90)]
        ctx.new_path()
        ctx.move_to(0, 0)
        for p in disc:
            ctx.line_to(*p)
        ctx.close_path()
        ctx.set_source_rgba(1, 1, 1, 0.05)
        ctx.fill()
        x0d = 0.30 * R
        y_dot = x0d / math.tan(max(beta, 1e-3))
        if i == 0:
            for kk in range(K + 1):                                   # each slice, folded -> unfolded
                ctx.save()
                ctx.rotate(-kk * th * (1 - unf))
                if kk % 2:
                    gam = (kk + 0.5) * th - math.pi / 2
                    ctx.rotate(gam)
                    ctx.scale(1, -math.cos(math.pi * unf))
                    ctx.rotate(-gam)
                sp = slice_pts(R, kk * th, min((kk + 1) * th, math.pi), 12)
                ctx.new_path()
                ctx.move_to(0, 0)
                for p in sp:
                    ctx.line_to(*p)
                ctx.close_path()
                lit = kk <= k
                col = CYAN if kk % 2 == 0 else VIOLET
                ctx.set_source_rgba(*col, 0.42 if kk == k else (0.24 if lit else 0.09))
                ctx.fill_preserve()
                ctx.set_source_rgba(1, 1, 1, 0.5)
                ctx.set_line_width(2)
                ctx.stroke()
                ctx.new_path()                                        # the straight line, cut by this slice
                ctx.move_to(0, 0)
                for p in sp:
                    ctx.line_to(*p)
                ctx.close_path()
                ctx.clip()
                if lit:
                    yy = max(-R * 1.1, -y_dot) if kk == k else R * 1.1
                    top = -R * 1.2
                    ctx.move_to(x0d, top)
                    ctx.line_to(x0d, yy if kk == k else R * 1.2)
                    ctx.set_source_rgba(*WHITE, 0.95)
                    ctx.set_line_width(5)
                    ctx.stroke()
                ctx.restore()
                if kk == k:                                           # the dot lives in slice k
                    ctx.save()
                    ctx.rotate(-kk * th * (1 - unf))
                    if kk % 2:
                        gam = (kk + 0.5) * th - math.pi / 2
                        ctx.rotate(gam)
                        ctx.scale(1, -math.cos(math.pi * unf))
                        ctx.rotate(-gam)
                    if x0d / math.sin(max(beta, 1e-3)) < R:
                        c.glow(x0d, -y_dot, 12, GOLD, strength=0.9, reach=3.0)
                        c.circle(x0d, -y_dot, 9, GOLD)
                    ctx.restore()
        else:
            for pass_, col in ((0, CYAN), (1, VIOLET)):               # the unfolded fan: slices up to the dot
                ctx.new_path()
                for kk in range(pass_, k + 1, 2):
                    b0, b1 = kk * th, min((kk + 1) * th, math.pi)
                    ctx.move_to(0, 0)
                    ctx.line_to(R * math.sin(b0), -R * math.cos(b0))
                    ctx.line_to(R * math.sin(b1), -R * math.cos(b1))
                    ctx.close_path()
                ctx.set_source_rgba(*col, 0.42)
                ctx.fill()
            if K <= 400:
                c.lines([(0, 0, R * math.sin(kk * th), -R * math.cos(kk * th)) for kk in range(K + 2)], WHITE,
                        width=1.2, alpha=0.35 if K < 100 else 0.16)
            ctx.new_path()
            ctx.move_to(0, 0)
            for p in disc:
                ctx.line_to(*p)
            ctx.close_path()
            ctx.clip()
            ctx.move_to(x0d, -R * 1.1)
            ctx.line_to(x0d, max(-y_dot, -R * 1.1))
            ctx.set_source_rgba(*WHITE, 0.95)
            ctx.set_line_width(5)
            ctx.stroke()
            ctx.reset_clip()
            if x0d / math.sin(max(beta, 1e-3)) < R:
                c.glow(x0d, -y_dot, 12, GOLD, strength=0.9, reach=3.0)
                c.circle(x0d, -y_dot, 9, GOLD)
        c.circle(0, 0, 7, WHITE)
        if unf > 0.98:                                                # the half turn: 180° = π
            ctx.new_path()
            ctx.arc(0, 0, R * 1.08, -math.pi / 2, math.pi / 2)
            ctx.set_source_rgba(*GOLD, 0.9 * smooth((unf - 0.98) / 0.02))
            ctx.set_line_width(6)
            ctx.stroke()
            c.text_centered("180° = π", 0, size=w * 0.045, color=GOLD, cx=R * 1.33,
                            alpha=smooth((u - 5.6) / 0.4) if i == 0 else 1.0)
        ctx.restore()
        # ---- counter + the rule
        done = q >= 0.999
        kshow = bangs_of(M) if done else k
        c.text_centered(f"{kshow:,}", h * 0.768, size=w * 0.115, color=GOLD if done else WHITE)
        c.text_centered("bangs", h * 0.797, size=w * 0.036, color=(0.75, 0.78, 0.9), bold=False)
        if i == 0:
            line = ("slice angle θ = 14.04°" if unf < 0.05 else f"{K + 1} slices × 14.04° ≈ 180°  →  {K} bangs")
        else:
            line = f"θ = {math.degrees(th):.3g}°   ·   180° ÷ θ = {math.pi / th:,.1f}"
        c.text_centered(line, h * 0.835, size=w * 0.04, color=CYAN, bold=False)

    def draw(self, f, rule):
        c, L = self.canvas, self.L
        t = f * DT
        self.frame(t)
        k_ = smooth((t - (T_LOOP - 0.45)) / 0.43)
        if k_ > 0:
            c.ctx.push_group()
            self.frame(0.0)
            c.ctx.pop_group_to_source()
            c.ctx.paint_with_alpha(k_)
        if rule:
            c.caption(rule, alpha=1.0, layout=L)
        c.watermark(L)


def render(layout, out_path, rule, still_frame=None):
    sc = Scene(layout)
    writer = None if still_frame is not None else VideoWriter(out_path, sc.canvas, FPS)
    nf = int(round(T_LOOP * FPS))
    for f in range(nf):
        if still_frame is not None and f != still_frame:
            continue
        sc.draw(f, rule)
        if writer is None:
            studio.save_still(sc.canvas, out_path)
            return f / FPS
        writer.write_frame()
    writer.close()
    return nf / FPS


def hit_times(i):
    """video times of every bang of round i (the point crosses a slice boundary)"""
    M = ROUNDS[i][0]
    th, K = theta_of(M), bangs_of(M)
    b0 = beta0_of(M)
    ks = np.arange(1, K + 1)
    beta_k = ks * th
    a, b = {0: (0.55, 3.35), 1: (0.7, 4.3), 2: (0.6, 3.9)}[i]
    q = (beta_k - b0) / ((math.pi - 1e-3) - b0)
    return R_START[i] + a + q * (b - a), ks


def track():
    sr = audio.SR
    n = int(round(T_LOOP * sr))
    out = np.zeros(n)
    for i in range(len(ROUNDS)):
        tm, ks = hit_times(i)
        idx = np.clip((tm * sr).astype(int), 0, n - 1)
        bins = int(sr * 0.05)
        dens = np.bincount(idx // bins, minlength=n // bins + 1)
        g = 0.34 / np.sqrt(np.maximum(1.0, dens[idx // bins] / 3.0))
        for parity, f0 in ((0, 1500.0), (1, 2400.0)):                  # wall / block: two pitches
            train = np.zeros(n)
            sel = ks % 2 == parity
            np.add.at(train, idx[sel], g[sel])
            tv = np.arange(int(0.03 * sr)) / sr
            kern = np.sin(2 * np.pi * f0 * tv) * np.exp(-tv / (0.006 if i == 0 else 0.0025))
            out += np.convolve(train, kern)[:n]
        tc = R_START[i] + {0: 3.45, 1: 4.4, 2: 4.0}[i]                 # the count is final: a chime
        tvc = np.arange(int(1.1 * sr)) / sr
        ch = sum(np.sin(2 * np.pi * 440 * 2 ** ((mm - 69) / 12) * tvc) for mm in (76 + 2 * i, 81 + 2 * i, 84 + 2 * i))
        ch *= np.exp(-tvc / 0.4) / 3
        i0 = int(tc * sr)
        out[i0:i0 + len(ch)] += 0.12 * ch[: max(0, n - i0)]
    t0 = int((R_START[0] + 3.95) * sr)                                 # the slices open: a soft whoosh
    tv = np.arange(int(1.7 * sr)) / sr
    wh = np.random.default_rng(3).standard_normal(len(tv))
    from scipy.signal import butter, sosfilt
    wh = sosfilt(butter(2, [300, 2400], btype="band", fs=sr, output="sos"), wh) * np.sin(np.pi * tv / 1.7) ** 2
    out[t0:t0 + len(wh)] += 0.10 * wh[: max(0, n - t0)]
    out = 0.22 * np.tanh(out / 0.22)
    pad = kit.loop_pad(T_LOOP, ((45, 1.0), (52, 0.6), (57, 0.4), (64, 0.25)), gain=0.035)
    return (out + pad[:n]).astype(np.float32)


def main():
    label, rule = arg("--label", "v1"), arg("--rule", "")
    studio.OUT_DIR.mkdir(exist_ok=True)
    layout = get_layout(kit.orients()[0])
    if kit.has("--still"):
        f = int(arg("--frame", "0"))
        png = studio.OUT_DIR / f"{SCENE}_{label}_f{f}_{layout.tag}.png"
        render(layout, png, rule, still_frame=f)
        print(f"[{SCENE}] -> {png}")
        return
    name = f"{SCENE}_{label}_{layout.tag}"
    video = studio.OUT_DIR / f"{name}_silent.mp4"
    d = render(layout, video, rule)
    kit.deliver_loop(SCENE, name, layout, video, [], d, voice="piano", bed=track(), peak_db=-6.0)


if __name__ == "__main__":
    main()
