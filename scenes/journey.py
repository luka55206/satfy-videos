"""JOURNEY — counting-family Shorts with real-object milestones (the engine behind the trillion/billion/googol hits).

--topic gplex   "How long to WRITE a googolplex?": blue writes one zero per second, each zero 1 cm wide. The line of
                zeros passes Burj Khalifa (828 m: 1 day), half the Earth's equator (80 years), the Moon (1,218 years),
                the Sun (474,000 years), Pluto (19 million years), across the Milky Way (3 × 10¹⁵ years), across the
                observable universe (2.8 × 10²¹ years). A googol zeros = 10⁷¹ universes long, 3 × 10⁹² years.
--topic stars   "How long to count every star?": 1 star per second: every star you can see at night (~9,000) 2.5 hours,
                the Milky Way (~200 billion) 6,340 years, Andromeda (~1 trillion) 31,700 years, the observable universe
                (~10²⁴, an estimate) 3 × 10¹⁶ years: 2 million times the age of the universe; the last stars die first.
Format: real-time counting first (1, 2, 3 …), then each milestone lands with a hit and an object illustration
(scenes/pi_long.draw_object), the big counter + time on top, one line of text. Rewind into frame 0 (loop).
Audio (original): light music-box bed, a soft tick stream while racing, a hit + chime per milestone, a falling sweep.
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
from scenes import pi_long  # noqa: E402
from scenes.bacteria import Scene as BacScene  # noqa: E402  (moon drawing)
from scenes.stickman import figure  # noqa: E402

TOPIC = arg("--topic", "gplex")
SCENE = f"journey_{TOPIC}"
GOLD, WHITE, SOFT, CYAN, BLUE = pi_long.GOLD, pi_long.WHITE, pi_long.SOFT, pi_long.CYAN, (0.45, 0.8, 1.0)
YEAR = 365.25 * 86400
SUP = "⁰¹²³⁴⁵⁶⁷⁸⁹"

if TOPIC == "gplex":
    # (log10 of zeros written = seconds, object, landmark line)
    MILES = [(math.log10(82800), "tower", "the line is taller than BURJ KHALIFA (828 m)"),
             (math.log10(80 * YEAR), "earth", "80 years: more than halfway around the EARTH"),
             (math.log10(3.844e10), "moon", "the line reaches the MOON"),
             (math.log10(1.496e13), "sun", "…the SUN"),
             (math.log10(5.9e14), "pluto", "…PLUTO"),
             (math.log10(9.46e22), "galaxy", "…across the whole MILKY WAY"),
             (math.log10(8.8e28), "universe", "…across the observable UNIVERSE"),
             (100.0, "universe", "a googol zeros: 10⁷¹ universes long")]
    INTRO = ("Write a GOOGOLPLEX:", "1 followed by a googol zeros", "1 zero per second · each zero 1 cm")
    UNIT = "zeros"
else:
    MILES = [(math.log10(9000), "sky", "every star you can see at night"),
             (math.log10(2e11), "galaxy", "every star in the MILKY WAY (~200 billion)"),
             (math.log10(1e12), "andromeda", "every star in ANDROMEDA (~1 trillion)"),
             (24.0, "universe", "every star in the observable UNIVERSE (~10²⁴)")]
    INTRO = ("Count every STAR", "in the universe", "1 star per second, no breaks")
    UNIT = "stars"
T_REAL = 2.6
STEP = 1.45 if TOPIC == "gplex" else 2.4
T_MILE = [T_REAL + (i + 1) * STEP for i in range(len(MILES))]
T_END = T_MILE[-1] + (1.8 if TOPIC == "gplex" else 3.2)
T_RW = 1.5
T_LOOP = T_END + T_RW + 0.3


def L_at(t):
    """log10 of the count at time t."""
    if t < T_REAL:
        return math.log10(max(1.0, 1 + int(t * 1.6)))
    if t >= T_END:
        u = smooth(min(1.0, (t - T_END) / T_RW))
        return MILES[-1][0] * (1 - u)
    k = sum(1 for tm in T_MILE if tm <= t)
    if k >= len(MILES):
        return MILES[-1][0]
    l0 = math.log10(1 + int(T_REAL * 1.6)) if k == 0 else MILES[k - 1][0]
    t0 = T_REAL if k == 0 else T_MILE[k - 1]
    u = (t - t0) / (T_MILE[k] - t0)
    hold = 0.35
    return l0 + (MILES[k][0] - l0) * smooth(min(1.0, max(0.0, (u - hold) / (1 - hold))))


def sup(n):
    return "".join(SUP[int(d)] for d in str(int(n)))


def big_num(Lg):
    if Lg < 9:
        return f"{int(round(10 ** Lg)):,}"
    e = int(math.floor(Lg + 1e-9))
    m = 10 ** (Lg - e)
    return f"10{sup(e)}" if m < 1.05 else f"{m:.1f} × 10{sup(e)}"


def time_str(Lg):
    s = 10 ** Lg
    if s < 60:
        return f"{int(s)} s"
    if s < 3600:
        return f"{int(s // 60)} min {int(s % 60)} s"
    if s < 86400 * 2:
        return f"{int(s // 3600)} h {int(s % 3600 // 60)} min"
    if s < YEAR:
        return f"{int(s // 86400)} days"
    y = s / YEAR
    if y < 1e6:
        return f"{y:,.0f} years"
    if y < 1e9:
        return f"{y / 1e6:,.0f} million years"
    if y < 1e12:
        return f"{y / 1e9:,.1f} billion years"
    e = int(math.floor(math.log10(y)))
    return f"{y / 10 ** e:.1f} × 10{sup(e)} years"


class Scene:
    def __init__(self, layout):
        self.L = layout
        self.canvas = Canvas(layout.w, layout.h, studio.render_scale())
        self.art = pi_long.Scene.__new__(pi_long.Scene)
        self.art.canvas, self.art.L = self.canvas, layout
        self.bac = BacScene.__new__(BacScene)
        self.bac.canvas, self.bac.L, self.bac.art = self.canvas, layout, self.art
        rng = np.random.default_rng(3)
        self.stars = [(rng.random(), rng.random(), rng.random()) for _ in range(400)]

    def obj(self, kind, x, y, S, a=1.0):
        c = self.canvas
        if kind == "moon":
            self.bac.obj("moon", x, y, S)
        elif kind == "tower":
            c.poly([(x - S * 0.06, y + S * 0.45), (x - S * 0.02, y - S * 0.45), (x + S * 0.02, y - S * 0.45),
                    (x + S * 0.06, y + S * 0.45)], (0.75, 0.8, 0.9))
            c.lines([(x, y - S * 0.45, x, y - S * 0.55)], (0.85, 0.88, 0.95), width=max(1.5, S * 0.01))
        elif kind == "andromeda":
            self.art.draw_object("galaxy", x, y, S * 1.1)
        elif kind == "sky":
            for k in range(60):
                sx, sy, sz = self.stars[k]
                c.circle(x + (sx - 0.5) * S, y + (sy - 0.5) * S * 0.7, 1.5 + 2.5 * sz, (1, 1, 0.9))
        else:
            self.art.draw_object(kind, x, y, S)

    def draw(self, f, rule):
        L, c = self.L, self.canvas
        w, h = L.w, L.h
        t = f * DT
        ctx = c.ctx
        g = cairo.LinearGradient(0, 0, 0, h)
        g.add_color_stop_rgb(0, 0.03, 0.03, 0.09)
        g.add_color_stop_rgb(1, 0.005, 0.005, 0.02)
        ctx.set_source(g)
        ctx.paint()
        Lg = L_at(t)
        k = sum(1 for tm in T_MILE if tm <= t) if t < T_END else len(MILES)
        nstar = 80 if TOPIC == "gplex" else int(min(400, 10 + 40 * Lg))
        for i, (sx, sy, sz) in enumerate(self.stars[:nstar]):
            tw = 0.6 + 0.4 * math.sin(t * (1 + sz) + i)
            c.circle(sx * w, sy * h * 0.62, 0.8 + 1.6 * sz, (1, 1, 1), alpha=0.25 + 0.5 * sz * tw)
        gy, H = h * 0.70, h * 0.13
        c.lines([(0, gy, w, gy)], (0.75, 0.78, 0.9), width=3, alpha=0.5)
        hx = w * 0.14
        writing = t < T_END
        if TOPIC == "gplex":
            figure(c, hx, gy, H, BLUE, (0.3, 0.2), (1.25 + 0.1 * math.sin(t * 20) if writing else 0.3, 0.9), t=t,
                   mouth="open" if 3 <= t < T_END and int(t * 6) % 2 else "smile")
            y_line = gy - H * 0.55
            if t < T_REAL:                                    # the zeros, readable
                nz = 1 + int(t * 1.6)
                c.text_centered("1" + "0" * nz, y_line + h * 0.012, size=h * 0.04, color=GOLD, cx=hx + w * 0.16 + nz * w * 0.018,
                                max_w=w * 0.8)
            else:                                             # the line, getting thinner as we zoom out
                fs = max(0.0, 1 - (t - T_REAL) / 1.2)
                if fs > 0.02:
                    c.text_centered("1" + "0" * 40, y_line + h * 0.012, size=h * 0.04 * (0.4 + 0.6 * fs),
                                    color=GOLD, cx=hx + w * 0.45, alpha=fs, max_w=w * 0.8)
                c.lines([(hx + w * 0.06, y_line, w * 0.98, y_line)], GOLD, width=10, alpha=0.2 * (1 - fs))
                c.lines([(hx + w * 0.06, y_line, w * 0.98, y_line)], GOLD, width=3, alpha=1 - fs)
        else:
            figure(c, hx, gy, H, BLUE, (0.3, 0.2), (2.4, 0.3) if writing else (0.3, 0.2), t=t, look=0.3,
                   mouth="open" if 3 <= t < T_END and int(t * 6) % 2 else "smile")
        # the milestone object, big, with its line
        if 1 <= k:
            Lm, kind, line = MILES[min(k, len(MILES)) - 1]
            tm = T_MILE[min(k, len(MILES)) - 1]
            pop = 1 + 0.15 * math.exp(-(t - tm) / 0.15) if t < T_END else 1.0
            fade = 1.0 if t < T_END else 1 - smooth(min(1.0, (t - T_END) / 0.6))
            if fade > 0.01:
                ox, oy = (w * 0.62, h * 0.42) if TOPIC == "stars" else (w * 0.66, h * 0.42)
                self.obj(kind, ox, oy, w * 0.42 * pop)
                c.text_centered(line, h * 0.77, size=w * 0.045, color=GOLD, alpha=fade, max_w=w * 0.94)
        elif t < T_REAL:
            c.text_centered(INTRO[2], h * 0.77, size=w * 0.042, color=SOFT, bold=False)
        # top: the count and the time
        if t < T_REAL or t >= T_END + T_RW * 0.8:
            c.text_centered(INTRO[0], h * 0.215, size=w * 0.08, color=GOLD)
            c.text_centered(INTRO[1], h * 0.25, size=w * 0.045, color=WHITE, bold=False)
        else:
            c.text_centered(f"{big_num(Lg)} {UNIT}", h * 0.215, size=w * 0.085, color=WHITE, max_w=w * 0.94)
            c.text_centered(time_str(Lg) + (" of writing" if TOPIC == "gplex" else " of counting"), h * 0.252,
                            size=w * 0.045, color=GOLD if k >= len(MILES) else SOFT, bold=False, max_w=w * 0.94)
        if k >= len(MILES) and t < T_END:
            last = "3 × 10⁹² years. The universe is 10¹⁰ years old." if TOPIC == "gplex" else \
                "2 million times the age of the universe"
            c.text_centered(last, h * 0.805, size=w * 0.04, color=WHITE, alpha=min(1.0, (t - T_MILE[-1] - 0.6) / 0.3),
                            max_w=w * 0.94)
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


def sound():
    b = sfx.Bed(T_LOOP, seed=21)
    arp = [(69, 72, 76, 81), (65, 69, 72, 77), (64, 67, 72, 76), (67, 71, 74, 79)]
    pat = [0, 2, 1, 3, 2, 1, 3, 2]
    t, q = 0.0, 0
    while t < T_LOOP - 0.1:
        pi_long.marimba(b, t, arp[int(t // 4.0) % 4][pat[q % 8]], 0.022 if q % 4 else 0.03)
        t += 0.5
        q += 1
    for i in range(int(T_REAL * 1.6)):                       # real-time: a pop per zero / star
        b.pluck(i / 1.6 + 0.3, 76, 0.1, d=0.3)
    tt = T_REAL
    while tt < T_MILE[-1]:                                    # racing: soft ticks, quiet in the holds
        k = sum(1 for tm in T_MILE if tm <= tt)
        t0 = T_REAL if k == 0 else T_MILE[k - 1]
        if (tt - t0) / STEP > 0.3:
            b.tick(tt, 2400 + 30 * k, 0.035)
        tt += 0.06
    for i, tm in enumerate(T_MILE):
        b.hit(tm, 0.22 + 0.04 * (i == len(T_MILE) - 1), low=85)
        b.chime(tm + 0.02, (79 + i % 3, 84 + i % 3), 0.06)
    b.chime(T_MILE[-1] + 0.6, (69, 72, 76, 81, 84), 0.06, decay=1.2)
    b.drop(T_END, T_RW, 0.05, 1500, 200)
    return b.get()


def main():
    label, rule = arg("--label", "v1"), arg("--rule", "")
    studio.OUT_DIR.mkdir(exist_ok=True)
    layout = get_layout(kit.orients()[0])
    print(f"[{SCENE}] {T_LOOP:.2f}s  " + ", ".join(f"{m[2][:28]}: {time_str(m[0])}" for m in MILES))
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
