"""POLYRHYTHM — "5 rhythms, 1 moment": dots orbit 5 rings; ring k returns to the top every P_k beats (2, 3, 4, 5, 6).

Each return to the top plays that ring's note, so you hear 5 rhythms at once. Pairs line up often (2 & 4 every 4
beats, 2-3-6 every 6 …) and make little chords; ALL FIVE strike together only every LCM(2,3,4,5,6) = 60 beats —
15 s, which is also the loop: frame 0 and the last frame are the same all-together moment.
Audio (original): one glass note per ring hit (a C major add9 chord spread over the rings), a soft pad.
"""
import math
import sys
from functools import reduce
from pathlib import Path

import cairo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib import kit, studio  # noqa: E402
from lib.kit import DT, FPS, arg  # noqa: E402
from lib.layouts import get_layout  # noqa: E402
from lib.studio import Canvas, VideoWriter  # noqa: E402

SCENE = "polyrhythm"
PER = [2, 3, 4, 5, 6]                                   # beats per lap, inner → outer
U = 0.25                                                # seconds per beat
LCM = reduce(lambda a, b: a * b // math.gcd(a, b), PER)
T_LOOP = LCM * U                                        # 15 s
NOTES = [84, 79, 76, 72, 67]                            # high (fast) → low (slow): C6 G5 E5 C5 G4
COLS = [(1.0, 0.45, 0.55), (1.0, 0.72, 0.30), (0.55, 0.95, 0.45), (0.35, 0.80, 1.00), (0.75, 0.55, 1.00)]
GOLD = (1.0, 0.82, 0.40)


def hits_at(t):
    """Which rings hit the top within the last ~0.2 s, and how long ago."""
    out = []
    for k, p in enumerate(PER):
        per = p * U
        age = t % per
        out.append(age)
    return out


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
        cx, cy = w / 2, h * 0.44
        g = cairo.RadialGradient(cx, cy, 0, cx, cy, max(w, h) * 0.7)
        g.add_color_stop_rgb(0.0, 0.07, 0.06, 0.12)
        g.add_color_stop_rgb(1.0, 0.01, 0.01, 0.02)
        ctx.set_source(g)
        ctx.paint()
        ages = hits_at(t)
        together = [k for k, a in enumerate(ages) if a < 0.18]
        n_now = sum(1 for a in ages if a < 1e-6 or a < DT * 0.5)
        all5 = math.exp(-(t % T_LOOP) / 0.35)                       # flash at the all-together moment (t = 0)
        for k, p in enumerate(PER):
            R = w * (0.13 + 0.065 * k)
            col = COLS[k]
            hit = math.exp(-ages[k] / 0.12)
            ctx.new_path()
            ctx.arc(cx, cy, R, 0, 2 * math.pi)
            ctx.set_source_rgba(*col, 0.25 + 0.5 * hit)
            ctx.set_line_width(3 + 5 * hit)
            ctx.stroke()
            for j in range(p):                                      # beat marks on the ring
                a = -math.pi / 2 + 2 * math.pi * j / p
                c.circle(cx + R * math.cos(a), cy + R * math.sin(a), 4, col, alpha=0.5)
            ang = -math.pi / 2 + 2 * math.pi * (t / (p * U))         # one lap per P beats, starting at the top
            for q in range(10, 0, -1):                              # trail
                a = ang - q * 0.045
                c.circle(cx + R * math.cos(a), cy + R * math.sin(a), 11 * (1 - q / 12), col, alpha=0.06 * (11 - q))
            dx, dy = cx + R * math.cos(ang), cy + R * math.sin(ang)
            c.glow(dx, dy, 14, col, strength=0.5 + 0.8 * hit, reach=3)
            c.circle(dx, dy, 13 + 6 * hit, col, alpha=1.0)
            c.circle(dx - 4, dy - 4, 4, (1, 1, 1), alpha=0.6)
        top = cy - w * (0.13 + 0.065 * 4) - 40
        c.lines([(cx, cy - w * 0.10, cx, top + 20)], GOLD, width=2, alpha=0.35)   # the "strike line"
        c.glow(cx, cy, w * 0.03, GOLD, strength=0.5 * all5, reach=2.5)
        # HUD
        left = T_LOOP - t
        beats_left = int(round(left / U))
        if all5 > 0.15:
            c.text_centered("ALL 5 TOGETHER", h * 0.735, size=w * 0.075, color=GOLD, alpha=min(1.0, all5 * 1.4))
        elif len(together) >= 2:
            names = " + ".join(str(PER[k]) for k in together)
            c.text_centered(f"{names} together", h * 0.735, size=w * 0.06, color=(0.95, 0.95, 1.0), alpha=0.95)
        c.text_centered(f"all 5 again in {beats_left} beats", h * 0.778, size=w * 0.042, color=GOLD, alpha=0.95)
        c.text_centered("LCM(2, 3, 4, 5, 6) = 60", h * 0.812, size=w * 0.034, color=(0.75, 0.78, 0.88), alpha=0.85,
                        bold=False)
        for k, p in enumerate(PER):                                 # legend: beats per lap
            x = w * (0.18 + 0.16 * k)
            c.text_centered(f"{p}", h * 0.205 + 0 * k, size=h * 0.02, color=COLS[k], alpha=0.95, cx=x)
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
    out = []
    for k, p in enumerate(PER):
        n = LCM // p
        for j in range(n):
            t = j * p * U
            out.append({"t": round(t + 0.003, 4), "note": NOTES[k], "gain": 0.30 if j else 0.36,
                        "x": layout.w * (0.3 + 0.1 * k)})
    for j, m in enumerate((48, 55, 60)):                            # the all-together downbeat gets a low chord
        out.append({"t": round(0.01 * j, 4), "note": m, "gain": 0.26, "x": layout.w / 2})
    return sorted(out, key=lambda e: e["t"])


def _worker(o, sim, label, rule):
    layout = get_layout(o)
    name = f"{SCENE}_{label}_{layout.tag}"
    video = studio.OUT_DIR / f"{name}_silent.mp4"
    d = render(layout, sim, video, rule)
    pad = kit.loop_pad(T_LOOP, ((48, 1.0), (55, 0.7), (60, 0.45), (64, 0.3)), gain=0.013)
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
    print(f"[{SCENE}] {T_LOOP:.1f}s, LCM {LCM}")
    kit.fan_out(_worker, (sim, label, rule), SCENE)


if __name__ == "__main__":
    main()
