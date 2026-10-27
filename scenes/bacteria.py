"""BACTERIA — one bacterium doubles every 20 minutes. On a balance scale it overtakes a mouse, an elephant, a whale,
a pyramid, Everest, the Moon… and the EARTH after 44 hours (if nothing stopped it).

The rice-chessboard format (the channel's best retention, 74.4 %): one doubling rule, real objects, a number that
explodes. Masses: a bacterium (E. coli) ≈ 1 picogram = 10⁻¹⁵ kg; doublings needed n = log2(M / 10⁻¹⁵), time = 20 min × n.
salt grain 6×10⁻⁸ kg 8.6 h · mouse 0.02 kg 14.7 h · person 70 kg 18.7 h · elephant 6 t 20.8 h · blue whale 150 t 22.3 h ·
Great Pyramid 6×10⁹ kg 27.4 h · Everest ≈10¹⁴ kg 32.1 h · the Moon 7.35×10²² kg 41.9 h · the Earth 5.97×10²⁴ kg 44.0 h.
Each object drops onto the right pan; the colony grows until the scale tips its way (a chime). Real life: food runs
out long before (said on screen). Loop: the colony shrinks back to one cell.
Audio (original, lib/sfx): a light music-box bed, soft rising ticks for the doublings (capped), a soft thud when an
object lands, a chime + rising pluck when the colony wins, a big chord on the Earth.
"""
import math
import sys
from pathlib import Path

import cairo
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib import kit, sfx, studio  # noqa: E402
from lib.kit import DT, FPS, arg, smooth  # noqa: E402
from lib.layouts import get_layout  # noqa: E402
from lib.studio import Canvas, VideoWriter  # noqa: E402
from scenes.pi_long import Scene as Art  # noqa: E402  (the illustrated objects)

SCENE = "bacteria"
CELL = 1e-15
GREEN, GOLD, WHITE, SOFT, RED = (0.45, 1.0, 0.55), (1.0, 0.82, 0.35), (0.96, 0.97, 1.0), (0.75, 0.78, 0.92), (1.0, 0.4, 0.4)
OBJ = [("A GRAIN OF SALT", 6e-8, "salt"), ("A MOUSE", 0.02, "mouse"), ("A PERSON", 70.0, "person"),
       ("AN ELEPHANT", 6000.0, "elephant"), ("A BLUE WHALE", 1.5e5, "whale"), ("THE GREAT PYRAMID", 6e9, "pyramid"),
       ("MOUNT EVEREST", 1e14, "mountain"), ("THE MOON", 7.35e22, "moon"), ("THE EARTH", 5.97e24, "earth")]
N_OBJ = [math.log2(M / CELL) for _, M, _ in OBJ]
T_SPLIT = 2.6                      # 0 -> 4 doublings shown cell by cell
STEP = 1.35                        # per object: drop 0.25, grow 0.75, hold 0.35
T_OBJ = [T_SPLIT + i * STEP for i in range(len(OBJ))]
T_EARTH_END = T_OBJ[-1] + STEP + 1.6
T_RW0, T_RW1 = T_EARTH_END, T_EARTH_END + 1.6
T_LOOP = T_RW1 + 0.4


def n_at(t):
    """doublings done by time t."""
    if t < T_SPLIT:
        return float(min(4, int(t / T_SPLIT * 4.6 + 1e-6)))       # whole splits: 1, 2, 4, 8, 16
    if t >= T_RW0:
        u = smooth(min(1.0, (t - T_RW0) / (T_RW1 - T_RW0)))
        return (N_OBJ[-1] + 0.4) * (1 - u)
    i = min(len(OBJ) - 1, int((t - T_SPLIT) // STEP))
    u = t - T_OBJ[i]
    n0 = 4.0 if i == 0 else N_OBJ[i - 1] + 0.4
    n1 = N_OBJ[i] + 0.4
    if u < 0.25:
        return n0
    return n0 + (n1 - n0) * smooth(min(1.0, (u - 0.25) / 0.75))


def sup(n):
    s = str(n)
    return "".join("⁻" if ch == "-" else "⁰¹²³⁴⁵⁶⁷⁸⁹"[int(ch)] for ch in s)


def mass_str(x):
    if x < 1e-3:
        return f"{x * 1e6:.2g} mg"
    if x < 1:
        return f"{x * 1e3:.3g} g"
    return f"{sci(x)} kg"


def sci(x):
    e = math.floor(math.log10(x))
    m = x / 10 ** e
    if -2 <= e < 6:
        return f"{x:,.2f}".rstrip("0").rstrip(".") if x < 1000 else f"{x:,.0f}"
    return f"{m:.1f} × 10{sup(e)}"


class Scene:
    def __init__(self, layout):
        self.L = layout
        self.canvas = Canvas(layout.w, layout.h, studio.render_scale())
        self.art = Art.__new__(Art)
        self.art.canvas, self.art.L = self.canvas, layout

    def obj(self, kind, x, y, S):
        c = self.canvas
        ctx = c.ctx
        if kind in ("person", "pyramid", "mountain", "earth"):
            self.art.draw_object(kind, x, y, S)
            return
        if kind == "salt":
            c.poly([(x - S * 0.18, y), (x, y - S * 0.1), (x + S * 0.18, y), (x, y + S * 0.1)], (1, 1, 1))
            c.poly([(x - S * 0.18, y), (x, y + S * 0.1), (x, y + S * 0.3), (x - S * 0.18, y + S * 0.2)], (0.8, 0.82, 0.88))
            c.poly([(x + S * 0.18, y), (x, y + S * 0.1), (x, y + S * 0.3), (x + S * 0.18, y + S * 0.2)], (0.65, 0.68, 0.75))
        elif kind == "mouse":
            ctx.save()
            ctx.translate(x, y + S * 0.1)
            ctx.scale(S * 0.3, S * 0.18)
            ctx.arc(0, 0, 1, 0, 2 * math.pi)
            ctx.restore()
            ctx.set_source_rgb(0.62, 0.62, 0.68)
            ctx.fill()
            c.circle(x - S * 0.28, y - S * 0.02, S * 0.12, (0.62, 0.62, 0.68))
            c.circle(x - S * 0.26, y - S * 0.15, S * 0.07, (0.95, 0.7, 0.75))
            c.circle(x - S * 0.34, y - S * 0.03, S * 0.02, (0.1, 0.1, 0.1))
            ctx.new_path()
            ctx.move_to(x + S * 0.28, y + S * 0.12)
            ctx.curve_to(x + S * 0.5, y + S * 0.1, x + S * 0.45, y - S * 0.15, x + S * 0.55, y - S * 0.2)
            ctx.set_source_rgb(0.95, 0.7, 0.75)
            ctx.set_line_width(max(1.5, S * 0.025))
            ctx.stroke()
        elif kind == "elephant":
            col = (0.55, 0.58, 0.66)
            ctx.save()
            ctx.translate(x + S * 0.05, y - S * 0.02)
            ctx.scale(S * 0.34, S * 0.22)
            ctx.arc(0, 0, 1, 0, 2 * math.pi)
            ctx.restore()
            ctx.set_source_rgb(*col)
            ctx.fill()
            for dx in (-0.18, -0.02, 0.14, 0.28):
                ctx.rectangle(x + dx * S, y + S * 0.08, S * 0.09, S * 0.22)
                ctx.fill()
            c.circle(x - S * 0.3, y - S * 0.1, S * 0.15, col)
            c.circle(x - S * 0.2, y - S * 0.1, S * 0.12, (0.45, 0.48, 0.56))
            c.lines([(x - S * 0.42, y - S * 0.05, x - S * 0.45, y + S * 0.25)], col, width=S * 0.07)
            c.circle(x - S * 0.36, y - S * 0.14, S * 0.02, (0.1, 0.1, 0.1))
        elif kind == "whale":
            col = (0.3, 0.45, 0.75)
            c.poly([(x - S * 0.48, y), (x - S * 0.3, y - S * 0.15), (x + S * 0.2, y - S * 0.14), (x + S * 0.38, y - S * 0.02),
                    (x + S * 0.5, y - S * 0.14), (x + S * 0.48, y + S * 0.08), (x + S * 0.36, y + S * 0.04),
                    (x + S * 0.1, y + S * 0.13), (x - S * 0.35, y + S * 0.12)], col)
            c.poly([(x - S * 0.45, y + S * 0.04), (x + S * 0.1, y + S * 0.08), (x - S * 0.35, y + S * 0.12)], (0.75, 0.82, 0.95))
            c.circle(x - S * 0.32, y - S * 0.03, S * 0.018, (0.05, 0.05, 0.1))
        elif kind == "moon":
            g = cairo.RadialGradient(x - S * 0.15, y - S * 0.15, S * 0.02, x, y, S * 0.4)
            g.add_color_stop_rgb(0, 0.92, 0.92, 0.95)
            g.add_color_stop_rgb(1, 0.45, 0.46, 0.52)
            ctx.new_path()
            ctx.arc(x, y, S * 0.4, 0, 2 * math.pi)
            ctx.set_source(g)
            ctx.fill()
            for px, py, r in ((-0.12, -0.1, 0.07), (0.15, 0.05, 0.09), (-0.05, 0.2, 0.05), (0.12, -0.2, 0.04)):
                c.circle(x + px * S, y + py * S, r * S, (0.5, 0.5, 0.56), alpha=0.7)

    def colony(self, x, y, R, n, t):
        """a glowing cluster of capsule cells; more cells as n grows (capped), the cluster radius R."""
        c = self.canvas
        ctx = c.ctx
        c.glow(x, y, R * 1.1, GREEN, strength=0.25, reach=1.5)
        cnt = int(min(140, 2 ** min(n, 7.2)))
        rng = np.random.default_rng(7)
        cell = R * (0.42 if cnt <= 1 else max(0.07, 0.42 / math.sqrt(cnt) * 1.6))
        for k in range(cnt):
            a = rng.uniform(0, 2 * math.pi)
            rr = R * math.sqrt(rng.uniform(0, 1)) * (0 if cnt == 1 else 0.85)
            px, py = x + rr * math.cos(a), y + rr * math.sin(a) * 0.8
            ang = rng.uniform(0, math.pi) + 0.3 * math.sin(t * 1.5 + k)
            ctx.save()
            ctx.translate(px, py)
            ctx.rotate(ang)
            ctx.new_path()
            ctx.arc(-cell * 0.5, 0, cell * 0.45, math.pi / 2, 3 * math.pi / 2)
            ctx.arc(cell * 0.5, 0, cell * 0.45, -math.pi / 2, math.pi / 2)
            ctx.close_path()
            ctx.restore()
            col = (0.35 + 0.2 * ((k * 7) % 3) / 2, 0.85 + 0.15 * ((k * 3) % 2), 0.45)
            ctx.set_source_rgba(*col, 0.92)
            ctx.fill()

    def draw(self, f, rule):
        L, c = self.L, self.canvas
        w, h = L.w, L.h
        t = f * DT
        ctx = c.ctx
        g = cairo.RadialGradient(w / 2, h * 0.45, 0, w / 2, h * 0.45, h * 0.7)
        g.add_color_stop_rgb(0, 0.05, 0.08, 0.10)
        g.add_color_stop_rgb(1, 0.005, 0.01, 0.015)
        ctx.set_source(g)
        ctx.paint()
        n = n_at(t)
        mass = CELL * 2 ** n
        if t < T_SPLIT or t >= T_RW0:                            # the first divisions (and the rewind), big
            k = int(2 ** min(4, int(t / T_SPLIT * 4.6 + 1e-6))) if t < T_SPLIT else max(1, int(2 ** min(4.0, n)))
            self.colony(w / 2, h * 0.47, w * (0.06 + 0.06 * math.log2(k + 1)), math.log2(k), t)
            c.text_centered("One bacterium.", h * 0.70, size=w * 0.065, color=WHITE)
            c.text_centered("It splits in two every 20 minutes.", h * 0.74, size=w * 0.042, color=SOFT, bold=False)
        else:
            i = min(len(OBJ) - 1, int((t - T_SPLIT) // STEP)) if t < T_RW0 else len(OBJ) - 1
            name, M, kind = OBJ[i]
            u = t - T_OBJ[i]
            # the balance: beam tips toward the heavier side
            diff = math.log10(mass) - math.log10(M)
            tilt = 0.22 * math.tanh(diff * 1.5)                    # + = colony side (left) down
            px, py = w / 2, h * 0.40
            Lb = w * 0.30
            lx, ly = px - Lb * math.cos(tilt), py + Lb * math.sin(tilt)
            rx, ry = px + Lb * math.cos(tilt), py - Lb * math.sin(tilt)
            c.poly([(px, py), (px - w * 0.06, h * 0.66), (px + w * 0.06, h * 0.66)], (0.35, 0.38, 0.5))
            c.lines([(px - w * 0.15, h * 0.66, px + w * 0.15, h * 0.66)], (0.5, 0.55, 0.7), width=8)
            c.lines([(lx, ly, rx, ry)], (0.85, 0.88, 1.0), width=7)
            c.circle(px, py, w * 0.014, GOLD)
            pan_dy = h * 0.11
            for (ax, ay) in ((lx, ly), (rx, ry)):
                c.lines([(ax, ay, ax - w * 0.08, ay + pan_dy), (ax, ay, ax + w * 0.08, ay + pan_dy)], SOFT, width=2)
                c.lines([(ax - w * 0.11, ay + pan_dy, ax + w * 0.11, ay + pan_dy)], (0.85, 0.88, 1.0), width=6)
            self.colony(lx, ly + pan_dy - w * 0.085, w * 0.085, n, t)
            drop = smooth(min(1.0, u / 0.25)) if t < T_RW0 else 1.0
            oy = ry + pan_dy - w * 0.11 - (1 - drop) * h * 0.2
            self.obj(kind, rx, oy, w * 0.2)
            c.text_centered(name, ry + pan_dy + h * 0.03, size=w * 0.04, color=GOLD, cx=rx, max_w=w * 0.36)
            c.text_centered(mass_str(M), ry + pan_dy + h * 0.055, size=w * 0.032, color=SOFT, bold=False, cx=rx)
            c.text_centered(mass_str(mass), ly + pan_dy + h * 0.055, size=w * 0.032, color=GREEN, bold=False, cx=lx)
            won = mass >= M
            if won and t < T_RW0:
                k_ = smooth(min(1.0, (u - 0.9) / 0.2)) if u > 0.9 else 0.0
                last = i == len(OBJ) - 1
                c.text_centered(f"heavier than {name.lower()}" if not last else "heavier than THE EARTH",
                                h * 0.75, size=w * (0.05 if not last else 0.065), color=GREEN if not last else GOLD,
                                alpha=max(k_, 1.0 if last and u > 1.2 else 0.0), max_w=w * 0.94)
            if t >= T_OBJ[-1] + STEP and t < T_RW0:
                c.text_centered("(in real life, the food runs out long before)", h * 0.79, size=w * 0.033, color=SOFT,
                                bold=False)
        # HUD: the time and the count
        mins = int(round(n * 20))
        hh, mm = divmod(mins, 60)
        c.text_centered(f"{hh} h {mm:02d} min", h * 0.215, size=w * 0.12, color=WHITE if t < T_OBJ[-1] + 1.0 else GOLD)
        cnt = 2 ** n
        ct = f"{int(round(cnt)):,} bacteria" if cnt < 1e6 else f"2{sup(int(round(n)))} ≈ {sci(cnt)} bacteria"
        c.text_centered(ct, h * 0.252, size=w * 0.042, color=GREEN, bold=False, max_w=w * 0.94)
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


def marimba(b, t0, m, g):
    tv = np.arange(int(0.9 * sfx.SR)) / sfx.SR
    f = sfx.hz(m)
    sig = np.sin(2 * np.pi * f * tv) * np.exp(-tv / 0.45) + 0.35 * np.sin(2 * np.pi * f * 3.93 * tv) * np.exp(-tv / 0.05)
    b.add(t0, sig * np.clip(tv / 0.002, 0, 1), g)


def sound():
    b = sfx.Bed(T_LOOP, seed=17)
    arp = [(69, 72, 76, 81), (65, 69, 72, 77), (64, 67, 72, 76), (67, 71, 74, 79)]
    pat = [0, 2, 1, 3, 2, 1, 3, 2]
    t, q = 0.0, 0
    while t < T_LOOP - 0.1:                                       # light music-box bed
        ch = arp[int(t // 4.8) % 4]
        marimba(b, t, ch[pat[q % 8]], 0.022 if q % 4 else 0.03)
        t += 0.3
        q += 1
    for k in range(5):                                           # the first splits: one pop each
        b.pluck(k * T_SPLIT / 4.6 * 1.0 + 0.01, 72 + 3 * k, 0.12, d=0.4)
    prev = 4
    for fr in range(int(T_SPLIT * FPS), int(T_RW0 * FPS)):        # doublings: soft ticks, capped
        tt = fr * DT
        nn = int(n_at(tt))
        if nn > prev and fr % 3 == 0:
            b.tick(tt, 2600 + 15 * nn, 0.035)
            prev = nn
    for i in range(len(OBJ)):
        tt = T_OBJ[i]
        b.hit(tt + 0.25, 0.18, low=90)                            # the object lands
        b.chime(tt + 1.0, (79 + i % 3, 84 + i % 3), 0.06)         # the colony wins
    b.hit(T_OBJ[-1] + 1.0, 0.35, low=70)
    b.chime(T_OBJ[-1] + 1.05, (69, 72, 76, 81, 84, 88), 0.07, decay=1.2)
    b.drop(T_RW0, T_RW1 - T_RW0, 0.05, 1400, 200)
    return b.get()


def main():
    label, rule = arg("--label", "v1"), arg("--rule", "")
    studio.OUT_DIR.mkdir(exist_ok=True)
    layout = get_layout(kit.orients()[0])
    print(f"[{SCENE}] {T_LOOP:.2f}s  hours: " + ", ".join(f"{nm} {n * 20 / 60:.1f}" for (nm, _, _), n in zip(OBJ, N_OBJ)))
    if kit.has("--still"):
        f = int(round(float(arg("--at")) * FPS)) if arg("--at") else int(arg("--frame", "0"))
        png = studio.OUT_DIR / f"{SCENE}_{label}_f{f}_{layout.tag}.png"
        render(layout, png, rule, still_frame=f)
        print(f"[{SCENE}] -> {png}")
        return
    name = f"{SCENE}_{label}_{layout.tag}"
    video = studio.OUT_DIR / f"{name}_silent.mp4"
    d = render(layout, video, rule)
    kit.deliver_loop(SCENE, name, layout, video, [], d, voice="piano", bed=sound(), peak_db=-6.0)


if __name__ == "__main__":
    main()
