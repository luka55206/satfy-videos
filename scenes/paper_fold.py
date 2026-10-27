"""PAPER FOLD — fold a sheet of paper (0.1 mm) in half 42 times: it reaches past the MOON.

Objects ladder (the rice/bacteria format): one doubling rule, real objects, a number that explodes. Thickness after n
folds = 0.1 mm × 2ⁿ. Milestones: fold 15 = 3.3 m (taller than a person), 22 = 419 m (taller than the Eiffel Tower,
330 m), 27 = 13.4 km (higher than Everest, 8,849 m), 30 = 107 km (into space, 100 km), 42 = 439,805 km (past the Moon,
384,400 km). On screen at the end: the record with real paper is 12 folds.
The camera keeps the stack's top at the same place on screen, so everything else shrinks away: the layer lines double
and blur, the person, the tower and Everest drop away, the Earth curves and becomes a ball, the Moon arrives.
Loop: the stack unfolds back to one sheet (frame 0).
Audio (original, lib/sfx): light marimba bed, a soft paper tick per fold (rising), a chime per milestone, a big chord
at the Moon, a falling sweep on the unfold.
"""
import math
import sys
from pathlib import Path

import cairo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib import kit, sfx, studio  # noqa: E402
from lib.kit import DT, FPS, arg, smooth  # noqa: E402
from lib.layouts import get_layout  # noqa: E402
from lib.studio import Canvas, VideoWriter  # noqa: E402
from scenes.pi_long import marimba  # noqa: E402

SCENE = "paper_fold"
GOLD, WHITE, SOFT, CYAN = (1.0, 0.8, 0.3), (0.96, 0.97, 1.0), (0.75, 0.78, 0.92), (0.35, 0.85, 1.0)
SHEET = 1e-4
R_EARTH, D_MOON, R_MOON = 6.371e6, 3.844e8, 1.7374e6
MILES = {15: ("taller than a PERSON", "person", 1.8), 22: ("taller than the EIFFEL TOWER", "eiffel", 330.0),
         27: ("higher than EVEREST", "everest", 8849.0), 30: ("into SPACE", "space", 1e5),
         42: ("PAST THE MOON", "moon", D_MOON)}
N_MAX = 42
T_START, STEP, PAUSE = 0.35, 0.2, 1.15
FOLD_T = []                     # start time of fold k+1 (n goes k -> k+1)
_t = T_START
for _k in range(N_MAX):
    FOLD_T.append(_t)
    _t += STEP
    if _k + 1 in MILES and _k + 1 != N_MAX:
        _t += PAUSE
T_TOP = _t                      # fold 42 done
T_RW0 = T_TOP + 2.6
T_RW1 = T_RW0 + 1.4
T_LOOP = T_RW1 + 0.3
GY, SPAN = 0.70, 0.36           # ground line, stack height on screen (fractions of h)


def clamp(v, a=0.0, b=1.0):
    return max(a, min(b, v))


def n_at(t):
    if t >= T_RW0:
        return N_MAX * (1 - smooth(clamp((t - T_RW0) / (T_RW1 - T_RW0))))
    n = 0.0
    for k, t0 in enumerate(FOLD_T):
        if t >= t0:
            n = k + smooth(clamp((t - t0) / STEP))
    return n


def hstr(x):
    if x < 0.01:
        return f"{x * 1000:.1f} mm"
    if x < 1:
        return f"{x * 100:.1f} cm"
    if x < 1000:
        return f"{x:,.1f} m"
    return f"{x / 1000:,.0f} km" if x >= 1e5 else f"{x / 1000:,.1f} km"


class Scene:
    def __init__(self, layout):
        self.L = layout
        self.canvas = Canvas(layout.w, layout.h, studio.render_scale())

    def obj(self, kind, x, gy, hp):
        """a real-height object standing on the ground at x (left edge), hp pixels tall."""
        c = self.canvas
        if hp < 2 or hp > self.L.h * 1.2:
            return
        if kind == "person":
            r = hp * 0.12
            c.circle(x + hp * 0.15, gy - hp + r, r, (1.0, 0.85, 0.7))
            c.lines([(x + hp * 0.15, gy - hp + 2 * r, x + hp * 0.15, gy - hp * 0.45),
                     (x + hp * 0.15, gy - hp * 0.45, x + hp * 0.05, gy), (x + hp * 0.15, gy - hp * 0.45, x + hp * 0.25, gy),
                     (x + hp * 0.15, gy - hp * 0.7, x + hp * 0.02, gy - hp * 0.5),
                     (x + hp * 0.15, gy - hp * 0.7, x + hp * 0.28, gy - hp * 0.5)], (0.45, 0.85, 1.0),
                    width=max(1.5, hp * 0.05))
        elif kind == "eiffel":
            wd = hp * 0.42
            cx = x + wd / 2
            col = (0.75, 0.55, 0.35)
            c.poly([(x, gy), (cx - wd * 0.08, gy - hp * 0.55), (cx, gy - hp), (cx + wd * 0.08, gy - hp * 0.55),
                    (x + wd, gy), (x + wd * 0.75, gy), (cx, gy - hp * 0.28), (x + wd * 0.25, gy)], col)
            c.lines([(x + wd * 0.18, gy - hp * 0.28, x + wd * 0.82, gy - hp * 0.28),
                     (cx - wd * 0.12, gy - hp * 0.55, cx + wd * 0.12, gy - hp * 0.55)], col, width=max(1.5, hp * 0.03))
        elif kind == "everest":
            wd = hp * 2.2
            c.poly([(x, gy), (x + wd * 0.42, gy - hp * 0.75), (x + wd * 0.55, gy - hp), (x + wd * 0.7, gy - hp * 0.7),
                    (x + wd, gy)], (0.42, 0.45, 0.58))
            c.poly([(x + wd * 0.47, gy - hp * 0.86), (x + wd * 0.55, gy - hp), (x + wd * 0.64, gy - hp * 0.8),
                    (x + wd * 0.57, gy - hp * 0.84)], (0.95, 0.97, 1.0))

    def draw(self, f, rule):
        L, c = self.L, self.canvas
        w, h = L.w, L.h
        t = f * DT
        ctx = c.ctx
        g = cairo.LinearGradient(0, 0, 0, h)
        n = n_at(t)
        H = SHEET * 2 ** n
        V = H / SPAN                                               # metres per screen height
        sky = clamp((math.log10(H) - 3.5) / 1.6)                   # blue sky fades to space above ~3 km
        g.add_color_stop_rgb(0, 0.02 + 0.06 * (1 - sky), 0.03 + 0.12 * (1 - sky), 0.06 + 0.22 * (1 - sky))
        g.add_color_stop_rgb(1, 0.01, 0.01, 0.03)
        ctx.set_source(g)
        ctx.paint()
        px = h / V                                                 # pixels per metre
        gy = h * GY
        cx = w * 0.40
        cw = w * 0.16
        # the Earth: flat ground, then a curve, then a ball
        Rp = R_EARTH * px
        ex, ey = cx + cw / 2, gy + Rp
        ctx.new_path()
        if Rp > 2e5:
            ctx.rectangle(0, gy, w, h - gy)
        else:
            ctx.arc(ex, ey, Rp, 0, 2 * math.pi)
        if Rp < w * 0.028:                                         # too small to see: draw it at a visible size
            Rp = w * 0.028
            ey = gy + Rp
            ctx.new_path()
            ctx.arc(ex, ey, Rp, 0, 2 * math.pi)
        if Rp < 2000:
            eg = cairo.RadialGradient(ex - Rp * 0.3, ey - Rp * 0.3, Rp * 0.05, ex, ey, Rp)
            eg.add_color_stop_rgb(0, 0.3, 0.6, 1.0)
            eg.add_color_stop_rgb(1, 0.05, 0.2, 0.55)
            ctx.set_source(eg)
        else:
            ctx.set_source_rgb(0.06, 0.13, 0.1)
        ctx.fill()
        if Rp < 4e5:
            c.ring(ex, ey, Rp + 2, CYAN, width=3, alpha=0.6)
        else:
            c.lines([(0, gy, w, gy)], (0.4, 0.75, 0.5), width=3)
        # space line (100 km)
        ys = gy - 1e5 * px
        if -10 < ys < gy - 4:
            ctx.set_dash([12, 10])
            c.lines([(0, ys, w, ys)], CYAN, width=2, alpha=0.7)
            ctx.set_dash([])
            c.text_centered("SPACE  ·  100 km", ys - h * 0.008, size=w * 0.032, color=CYAN, cx=w * 0.8, bold=False)
        # side objects at their real heights
        for k, (txt, kind, hm) in MILES.items():
            if kind in ("person", "eiffel", "everest"):
                self.obj(kind, cx + cw + w * 0.05, gy, hm * px)
        # the next target: a dashed line at its height, coming down to meet the stack
        nxt = [(m, v) for m, v in MILES.items() if v[2] > H * 1.001]
        if nxt and t < T_RW0:
            m, (txt, kind, hm) = nxt[0]
            yt = gy - hm * px
            if h * 0.35 < yt < gy - 4:
                a = clamp((yt - h * 0.35) / (h * 0.04))
                ctx.set_dash([10, 8])
                c.lines([(w * 0.05, yt, w * 0.95, yt)], GOLD, width=2, alpha=0.8 * a)
                ctx.set_dash([])
                name = {"person": "a person", "eiffel": "Eiffel Tower", "everest": "Everest", "space": "space",
                        "moon": "the Moon"}[kind]
                c.text_centered(name, yt - h * 0.008, size=w * 0.034, color=GOLD, cx=w * 0.18, alpha=a)
        # the stack
        top = gy - H * px
        sg = cairo.LinearGradient(cx, 0, cx + cw, 0)
        sg.add_color_stop_rgb(0, 0.82, 0.84, 0.9)
        sg.add_color_stop_rgb(0.5, 1.0, 1.0, 1.0)
        sg.add_color_stop_rgb(1, 0.78, 0.8, 0.86)
        ctx.rectangle(cx, top, cw, gy - top)
        ctx.set_source(sg)
        ctx.fill()
        layers = 2 ** n
        gap = (gy - top) / layers
        if gap > 2.5:                                              # the layers: they double, then blur
            a = clamp((gap - 2.5) / 6)
            nl = int(layers)
            c.lines([(cx, top + gap * j, cx + cw, top + gap * j) for j in range(1, nl)], (0.55, 0.58, 0.7), width=1.5,
                    alpha=a)
        c.glow(cx + cw / 2, top, cw * 0.6, WHITE, strength=0.25, reach=1.4)
        # the Moon
        my = gy - D_MOON * px
        mr = max(w * 0.045, R_MOON * px)
        ma = clamp((my - h * 0.35) / (h * 0.05))
        mxx = cx + cw + mr + w * 0.02
        if ma > 0:
            mg = cairo.RadialGradient(mxx - mr * 0.3, my - mr * 0.3, mr * 0.05, mxx, my, mr)
            mg.add_color_stop_rgb(0, 0.95, 0.95, 0.97)
            mg.add_color_stop_rgb(1, 0.45, 0.46, 0.52)
            ctx.new_path()
            ctx.arc(mxx, my, mr, 0, 2 * math.pi)
            ctx.save()
            ctx.clip()
            ctx.set_source(mg)
            ctx.paint_with_alpha(ma)
            ctx.restore()
            c.text_centered("THE MOON", my - mr - h * 0.012, size=w * 0.04, color=WHITE, cx=mxx, alpha=ma)
        # HUD
        k = int(math.floor(n + 1e-6))
        c.text_centered(f"FOLD {k}", h * 0.27, size=w * 0.12, color=GOLD if k >= N_MAX and t < T_RW0 else WHITE)
        c.text_centered(hstr(SHEET * 2 ** k), h * 0.305, size=w * 0.055, color=SOFT, bold=False)
        # the milestone line
        if t < T_RW0:
            for m, (txt, kind, hm) in MILES.items():
                td = FOLD_T[m - 1] + STEP
                end = td + PAUSE + (99 if m == N_MAX else 0)
                if td <= t < end:
                    a = clamp((t - td) / 0.15) * clamp((end - t) / 0.15)
                    pop = math.exp(-(t - td) / 0.2)
                    c.text_centered(txt, h * 0.785, size=w * (0.075 if m == N_MAX else 0.06) * (1 + 0.15 * pop),
                                    color=GOLD, alpha=a, max_w=w * 0.94)
                    sub = {"person": "1.8 m", "eiffel": "330 m", "everest": "8,849 m", "space": "100 km",
                           "moon": "384,400 km away"}[kind]
                    c.text_centered(sub, h * 0.818, size=w * 0.042, color=SOFT, alpha=a, bold=False)
            if t >= T_TOP + 1.0:
                c.text_centered("(with real paper, the record is 12 folds)", h * 0.848, size=w * 0.033, color=SOFT,
                                bold=False, alpha=clamp((t - T_TOP - 1.0) / 0.3))
        if n < 3.5:
            a = clamp((3.5 - n) / 0.5)
            c.text_centered("One sheet of paper: 0.1 mm", h * 0.77, size=w * 0.06, color=WHITE, alpha=a)
            c.text_centered("fold it in half… 42 times", h * 0.805, size=w * 0.045, color=GOLD, alpha=a)
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
    b = sfx.Bed(T_LOOP, seed=11)
    arp = [(69, 72, 76, 81), (65, 69, 72, 77), (64, 67, 72, 76), (67, 71, 74, 79)]
    pat = [0, 2, 1, 3, 2, 1, 3, 2]
    t, q = 0.0, 0
    while t < T_LOOP - 0.2:
        marimba(b, t, arp[int(t // 3.2) % 4][pat[q % 8]], 0.018 if q % 4 else 0.024)
        t += 0.4
        q += 1
    scale = [60, 62, 64, 67, 69, 72, 74, 76, 79, 81]
    for k, t0 in enumerate(FOLD_T):
        b.snap(t0 + STEP * 0.8, 0.05)
        b.pluck(t0 + STEP, scale[k % 10] + 12 * (k // 20), 0.045, d=0.3)
    for m in MILES:
        td = FOLD_T[m - 1] + STEP
        if m == N_MAX:
            b.hit(td, 0.3, low=70)
            b.chime(td + 0.02, (69, 72, 76, 81, 84, 88), 0.07, decay=1.2)
        else:
            b.chime(td + 0.02, (79, 84), 0.06)
    b.drop(T_RW0, T_RW1 - T_RW0, 0.05, 1400, 200)
    return b.get()


def main():
    label, rule = arg("--label", "v1"), arg("--rule", "")
    studio.OUT_DIR.mkdir(exist_ok=True)
    layout = get_layout(kit.orients()[0])
    print(f"[{SCENE}] {T_LOOP:.2f}s  " + ", ".join(f"{m}: {hstr(SHEET * 2 ** m)}" for m in MILES))
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
