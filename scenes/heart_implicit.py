"""HEART IMPLICIT — "The most famous heart equation: (x² + y² − 1)³ = x²y³" (share-driven Short).

Level sets F(x, y) = c of F = (x² + y² − 1)³ − x²y³: as c rises from below zero the curve is a closed blob that
narrows, dents and — exactly at c = 0 — becomes the heart. Many level sets are drawn as glowing rings that pulse
like a heartbeat; on c = 0 the heart flares, beats, and the share prompt appears. Loop: the rings flow back.
Audio (original): a soft heartbeat (lub-dub), warm romantic piano chords, a shimmer at c = 0.
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

SCENE = "heart_implicit"
T_REVEAL = 6.0
T_LOOP = 13.5
PINK = (1.0, 0.40, 0.55)
GOLD = (1.0, 0.82, 0.40)
BEAT = 0.8                                                           # 75 bpm heartbeat


def c_of(t):
    """The level: from −0.9 (a round blob) to 0 (the heart) at T_REVEAL, held, then smoothly back."""
    if t < T_REVEAL:
        return -0.9 * (1 - smooth(t / T_REVEAL))
    if t < T_LOOP - 2.0:
        return 0.0
    return -0.9 * smooth((t - (T_LOOP - 2.0)) / 2.0)


def F(X, Y):
    return (X * X + Y * Y - 1) ** 3 - X * X * Y ** 3


def simulate():
    return {"nf": int(round(T_LOOP * FPS))}


class Scene:
    def __init__(self, layout, sim):
        self.L, self.sim = layout, sim
        self.canvas = Canvas(layout.w, layout.h, studio.render_scale())

    def curve_img(self, cval, beat):
        c = self.canvas
        pw, ph = c.pw, c.ph
        w, h = self.L.w, self.L.h
        sc = 1.0 + 0.06 * beat
        S = (w * 0.30 * sc) * (pw / w)
        xs = (np.arange(pw) - pw / 2) / S
        ys = -(np.arange(ph) - ph * 0.45) / S
        X, Y = np.meshgrid(xs, ys)
        G = F(X, Y)
        gy, gx = np.gradient(G, -1 / S, 1 / S)
        gn = np.hypot(gx, gy) + 1e-9
        img = np.zeros((ph, pw))
        for k, off in enumerate((0.0, 0.25, 0.5, 0.75, 1.0)):       # nested glowing rings (level sets)
            lv = cval - off * 0.6
            d = np.abs(G - lv) / gn * S
            wpx = (2.2 if k == 0 else 1.2) * pw / w
            img += (1.0 if k == 0 else 0.35 * (1 - off * 0.6)) * np.exp(-(d / wpx) ** 2)
            img += (0.30 if k == 0 else 0.0) * np.exp(-(d / (wpx * 6)) ** 2)
        return np.clip(img, 0, 1)

    def blit(self, inten, col):
        c = self.canvas
        ph, pw = inten.shape
        buf = np.zeros((ph, pw, 4), np.uint8)
        buf[..., 0] = (inten * col[2] * 255).astype(np.uint8)
        buf[..., 1] = (inten * col[1] * 255).astype(np.uint8)
        buf[..., 2] = (inten * col[0] * 255).astype(np.uint8)
        buf[..., 3] = (inten * 255).astype(np.uint8)
        stride = cairo.ImageSurface.format_stride_for_width(cairo.FORMAT_ARGB32, pw)
        if stride != pw * 4:
            pad = np.zeros((ph, stride // 4, 4), np.uint8)
            pad[:, :pw] = buf
            buf = pad
        surf = cairo.ImageSurface.create_for_data(memoryview(np.ascontiguousarray(buf)), cairo.FORMAT_ARGB32, pw, ph,
                                                  stride)
        ctx = c.ctx
        ctx.save()
        ctx.identity_matrix()
        ctx.set_operator(cairo.OPERATOR_ADD)
        ctx.set_source_surface(surf, 0, 0)
        ctx.paint()
        ctx.restore()

    def draw(self, f, rule):
        L, c = self.L, self.canvas
        w, h = L.w, L.h
        t = f * DT
        ctx = c.ctx
        g = cairo.RadialGradient(w / 2, h * 0.45, 0, w / 2, h * 0.45, max(w, h) * 0.7)
        g.add_color_stop_rgb(0.0, 0.12, 0.04, 0.09)
        g.add_color_stop_rgb(1.0, 0.02, 0.01, 0.02)
        ctx.set_source(g)
        ctx.paint()
        ph = (t % BEAT) / BEAT
        beat = math.exp(-ph / 0.08) + 0.6 * math.exp(-max(0.0, ph - 0.22) / 0.08) * (ph > 0.22)
        cval = c_of(t)
        on = 1.0 - min(1.0, abs(cval) / 0.12)
        self.blit(self.curve_img(cval, beat * (0.4 + 0.6 * on)), PINK)
        if on > 0.01:
            c.glow(w / 2, h * 0.45, w * 0.18, PINK, strength=0.35 * on * (0.6 + 0.4 * beat), reach=3)
        c.text_centered("(x² + y² − 1)³ = x² y³", h * 0.73, size=w * 0.062, color=(1, 0.95, 0.97), alpha=0.95)
        c.text_centered(f"= {cval:+.2f}" if on < 0.99 else "= 0   ♥", h * 0.775, size=w * 0.05,
                        color=GOLD if on > 0.5 else (0.85, 0.8, 0.85), alpha=0.95)
        if T_REVEAL + 0.6 <= t < T_LOOP - 2.0:
            a = smooth((t - T_REVEAL - 0.6) / 0.4) * (1 - smooth((t - (T_LOOP - 2.4)) / 0.4))
            c.text_centered("send this to someone ♥", h * 0.82, size=w * 0.045, color=PINK, alpha=a)
        c.text_centered("WATCH IT BECOME A HEART", h * 0.205, size=h * 0.0145, color=GOLD, alpha=0.85)
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
    """Warm piano chords (F – Am – Dm – Bb … romantic), a shimmer on the reveal."""
    prog = [(53, 57, 60, 64), (57, 60, 64, 67), (50, 57, 62, 65), (46, 53, 58, 62)]
    out = []
    k, t = 0, 0.0
    while t < T_LOOP - 0.5:
        for j, m in enumerate(prog[k % 4]):
            out.append({"t": round(t + 0.03 * j, 4), "note": m + 12, "gain": 0.22, "x": layout.w / 2})
        t += 4 * BEAT
        k += 1
    for j, m in enumerate((77, 81, 84, 88, 89)):
        out.append({"t": round(T_REVEAL + 0.06 * j, 4), "note": m, "gain": 0.20, "x": layout.w / 2})
    return sorted(out, key=lambda e: e["t"])


def heartbeat_bed():
    sr = audio.SR
    n = int(round(T_LOOP * sr))
    out = np.zeros(n)
    tv = np.arange(int(0.2 * sr)) / sr
    thump = np.sin(2 * np.pi * np.cumsum(45 + 40 * np.exp(-tv / 0.02)) / sr) * np.exp(-tv / 0.06)
    t = 0.0
    while t < T_LOOP - 0.05:
        for dt_, gn in ((0.0, 1.0), (0.22, 0.65)):
            i0 = int((t + dt_) * sr) % n
            idx = (np.arange(len(thump)) + i0) % n
            np.add.at(out, idx, gn * thump)
        t += BEAT
    return (0.35 * out).astype(np.float32)


def _worker(o, sim, label, rule):
    layout = get_layout(o)
    name = f"{SCENE}_{label}_{layout.tag}"
    video = studio.OUT_DIR / f"{name}_silent.mp4"
    d = render(layout, sim, video, rule)
    pad = kit.loop_pad(T_LOOP, ((53, 1.0), (60, 0.6), (65, 0.4)), gain=0.012)
    kit.deliver_loop(SCENE, name, layout, video, build_events(sim, layout), d, voice="piano",
                     bed=heartbeat_bed() + pad[: int(round(T_LOOP * audio.SR))], peak_db=-6.0)


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
