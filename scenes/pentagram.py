"""PENTAGRAM — "φ is hiding in this star": an endless, seamless zoom into nested pentagrams.

A pentagram's inner pentagon holds the next pentagram, φ² = 2.618… times smaller and turned 36°. Every line of a
pentagram is cut in the golden ratio (long : short = φ). The camera zooms ×φ² and turns 36° per level, so after one
level the picture is identical (colours repeat every 2 levels → loop = 2 levels × 4).
Audio (original): a 4-note motif, one note per level, + a soft pad.
"""
import math
import sys
from pathlib import Path

import cairo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib import kit, studio  # noqa: E402
from lib.kit import DT, FPS, arg  # noqa: E402
from lib.layouts import get_layout  # noqa: E402
from lib.studio import Canvas, VideoWriter  # noqa: E402

SCENE = "pentagram"
PHI = (1 + 5 ** 0.5) / 2
K = PHI ** 2                                     # scale between levels
TAU = 1.6                                        # seconds per level
LEVELS = 8
T_LOOP = TAU * LEVELS                            # 12.8 s (a whole number of 2-level colour cycles)
COLS = [(1.0, 0.55, 0.30), (0.40, 0.75, 1.00)]
GOLD = (1.0, 0.82, 0.40)


def simulate():
    return {"nf": int(round(T_LOOP * FPS))}


class Scene:
    def __init__(self, layout, sim):
        self.L, self.sim = layout, sim
        self.canvas = Canvas(layout.w, layout.h, studio.render_scale())

    def draw(self, f, rule):
        L, c = self.L, self.canvas
        w, h = L.w, L.h
        t = f * DT
        ctx = c.ctx
        cx, cy = w / 2, h * 0.45
        g = cairo.RadialGradient(cx, cy, 0, cx, cy, max(w, h) * 0.7)
        g.add_color_stop_rgb(0.0, 0.08, 0.06, 0.13)
        g.add_color_stop_rgb(1.0, 0.01, 0.01, 0.02)
        ctx.set_source(g)
        ctx.paint()
        u = t / TAU                                          # continuous level
        R0 = w * 0.42 * K ** (u % 1.0)                       # radius of level floor(u) on screen
        rot0 = math.radians(36) * (u % 1.0)
        base = int(u)
        ctx.set_line_join(cairo.LINE_JOIN_MITER)
        for j in range(-2, 9):                               # outer → inner
            R = R0 / K ** j
            if R < 2 or R > w * 4:
                continue
            lev = base + j
            rot = rot0 + math.radians(36) * j - math.pi / 2
            col = COLS[lev % 2]
            pts = [(cx + R * math.cos(rot + 2 * math.pi * i / 5), cy + R * math.sin(rot + 2 * math.pi * i / 5))
                   for i in range(5)]
            star = [pts[(2 * i) % 5] for i in range(6)]
            fade = 1.0 if R < w * 0.6 else max(0.0, 1 - (R - w * 0.6) / (w * 0.9))
            c.polylines([pts + [pts[0]]], col, width=2.0, alpha=0.35 * fade)
            c.polylines([star], col, width=14, alpha=0.10 * fade)
            c.polylines([star], col, width=3.2, alpha=0.95 * fade)
            for (x, y) in pts:
                c.circle(x, y, 4, (1, 1, 1), alpha=0.7 * fade)
        c.glow(cx, cy, w * 0.02, GOLD, strength=0.5, reach=4)
        c.text_centered("long ÷ short = φ = 1.618…", h * 0.745, size=w * 0.06, color=GOLD, alpha=1.0)
        c.text_centered("every star is φ² = 2.618… times smaller than the last", h * 0.785, size=w * 0.032,
                        color=(0.88, 0.89, 0.95), alpha=0.9, bold=False)
        c.text_centered("FAMOUS NUMBERS · GOLDEN RATIO", h * 0.205, size=h * 0.015, color=GOLD, alpha=0.85)
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
    motif = [69, 76, 72, 74]
    out = []
    for k in range(LEVELS):
        t = k * TAU
        out.append({"t": round(t + 0.01, 4), "note": motif[k % 4], "gain": 0.40, "x": layout.w / 2})
        out.append({"t": round(t + 0.01, 4), "note": motif[k % 4] - 24, "gain": 0.20, "x": layout.w / 2})
        for j, m in enumerate((81, 88, 84)):
            out.append({"t": round(t + TAU * (0.35 + 0.2 * j), 4), "note": m - 12 * (k % 2), "gain": 0.12,
                        "x": layout.w * (0.3 + 0.2 * j)})
    return sorted(out, key=lambda e: e["t"])


def _worker(o, sim, label, rule):
    layout = get_layout(o)
    name = f"{SCENE}_{label}_{layout.tag}"
    video = studio.OUT_DIR / f"{name}_silent.mp4"
    d = render(layout, sim, video, rule)
    pad = kit.loop_pad(T_LOOP, ((45, 1.0), (52, 0.7), (57, 0.45), (64, 0.3)), gain=0.016)
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
