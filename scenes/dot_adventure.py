"""DOT ADVENTURE — "Dot vs. Numbers": one continuous stick-figure adventure where the math is physical (16:9 sample).

Format inspiration: an owner-supplied reference (a stick figure interacting with living math). Only the FORMAT is
taken: our own character (blue "Dot"), world, look, gag sequence, timing and sound.

World units: Dot is ~1.05 tall, ground y = 0. A jointed puppet (torso, head, 2-segment arms and legs) is keyframed
with named poses + procedural walk/run cycles; the camera follows him (and rises with the tower).
Story (40 s): asleep → a "1" falls → 1 + 1 = 2 → kicks in +1s up to 10 → the chain collapses into "10" → ² ³ ⁴ lift
him on a 10^k tower → ÷10 stairs down to 1 → an infinite ÷10 pit (→ 0, never reached) → an ∞ boulder rolls in, Dot
jumps the pit, the ∞ falls into it forever → "to be continued…".
Audio (original): thuds, pops, dings, kicks, rising/falling tones, rumble, a light pluck loop.
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

SCENE = "dot_adventure"
T_LOOP = 40.0
SR = audio.SR
BLUE = (0.45, 0.80, 1.00)
GOLD = (1.0, 0.82, 0.40)
WHITE = (0.96, 0.96, 1.0)

# ---------------------------------------------------------------- the puppet
UA, FA, TH, SH, TO, HR = 0.27, 0.25, 0.29, 0.28, 0.33, 0.115
POSES = {  # lean, head tilt, arm front (upper, lower), arm back, leg front (thigh, shin), leg back — degrees from down
    "stand": dict(lean=0, head=0, af=(12, 6), ab=(-12, -6), lf=(7, 2), lb=(-7, -2)),
    "sit": dict(lean=18, head=35, af=(40, 80), ab=(20, 70), lf=(85, 95), lb=(80, 100), seat=True),
    "poke": dict(lean=8, head=-5, af=(80, 88), ab=(-15, -5), lf=(10, 2), lb=(-12, -4)),
    "cheer": dict(lean=-5, head=-15, af=(170, 175), ab=(-170, -175), lf=(10, 0), lb=(-10, 0)),
    "carry": dict(lean=0, head=-10, af=(150, 200), ab=(-150, -200), lf=(8, 2), lb=(-8, -2)),
    "plant": dict(lean=30, head=20, af=(60, 20), ab=(-10, -20), lf=(30, -10), lb=(-25, -15)),
    "kick": dict(lean=-12, head=0, af=(-35, -20), ab=(45, 30), lf=(85, 88), lb=(-6, 0)),
    "crouch": dict(lean=20, head=5, af=(40, 10), ab=(-20, -40), lf=(55, -25), lb=(40, -40)),
    "jump": dict(lean=-5, head=-10, af=(150, 165), ab=(-150, -165), lf=(25, -20), lb=(-10, -50)),
    "shrug": dict(lean=0, head=12, af=(55, 150), ab=(-55, -150), lf=(8, 2), lb=(-8, -2)),
    "nervous": dict(lean=-6, head=25, af=(25, 110), ab=(-25, -110), lf=(10, 4), lb=(-10, -4)),
    "lookdown": dict(lean=25, head=40, af=(25, 10), ab=(-10, -5), lf=(15, 5), lb=(-10, -2)),
    "dust": dict(lean=5, head=10, af=(70, 100), ab=(60, 110), lf=(8, 2), lb=(-8, -2)),
    "peek": dict(lean=-10, head=-10, af=(100, 140), ab=(-20, -10), lf=(8, 2), lb=(-8, -2)),
}


def lerp(a, b, u):
    return a + (b - a) * u


def blend(p, q, u):
    out = {}
    for k in ("lean", "head"):
        out[k] = lerp(p[k], q[k], u)
    for k in ("af", "ab", "lf", "lb"):
        out[k] = (lerp(p[k][0], q[k][0], u), lerp(p[k][1], q[k][1], u))
    out["seat"] = q.get("seat", False) if u > 0.5 else p.get("seat", False)
    return out


def cycle(t, run=False):
    """Walk / run cycle pose."""
    p = t * (2 * math.pi) * (2.2 if run else 1.6)
    A = 38 if run else 24
    lf_t = A * math.sin(p)
    lb_t = -A * math.sin(p)
    lf = (lf_t, lf_t - (45 if run else 28) * max(0.0, math.sin(p + 1.4)))
    lb = (lb_t, lb_t - (45 if run else 28) * max(0.0, math.sin(p + 1.4 + math.pi)))
    ar = 45 if run else 22
    return dict(lean=15 if run else 3, head=0, af=(-ar * math.sin(p), -ar * math.sin(p) + (70 if run else 25)),
                ab=(ar * math.sin(p), ar * math.sin(p) + (70 if run else 25)), lf=lf, lb=lb)


def leg_drop(pose):
    """Vertical extent of the lowest foot below the hip (for auto-grounding)."""
    best = 0.0
    for k in ("lf", "lb"):
        a1, a2 = (math.radians(v) for v in pose[k])
        best = max(best, TH * math.cos(a1) + SH * math.cos(a2))
    return best


def draw_puppet(ctx, X, Y, S, x, y_feet, face, pose, mouth="smile", eyes="open", col=BLUE, tremble=0.0, t=0.0,
                airborne=0.0):
    """x, y_feet in world units; face = +1 right / −1 left. X(), Y() map world → screen; S = px per unit."""
    hip_y = y_feet + (0.12 if pose.get("seat") else leg_drop(pose)) + airborne
    hx, hy = x + tremble * 0.01 * math.sin(t * 60), hip_y
    lean = math.radians(pose["lean"])
    sx, sy = hx + face * math.sin(lean) * TO, hy + math.cos(lean) * TO
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    lw = S * 0.05

    def seg(p, q):
        ctx.move_to(X(p[0]), Y(p[1]))
        ctx.line_to(X(q[0]), Y(q[1]))

    def limb(root, ang, l1, l2):
        a1, a2 = (math.radians(v) for v in ang)
        e = (root[0] + face * math.sin(a1) * l1, root[1] - math.cos(a1) * l1)
        f = (e[0] + face * math.sin(a2) * l2, e[1] - math.cos(a2) * l2)
        seg(root, e)
        seg(e, f)
        return f

    ctx.new_path()
    seg((hx, hy), (sx, sy))
    hands = {}
    for k in ("ab", "lb", "lf", "af"):
        root = (sx, sy) if k[0] == "a" else (hx, hy)
        tip = limb(root, pose[k], UA if k[0] == "a" else TH, FA if k[0] == "a" else SH)
        hands[k] = tip
    ctx.set_source_rgb(*col)
    ctx.set_line_width(lw)
    ctx.stroke()
    ht = math.radians(pose["head"])
    hcx = sx + face * math.sin(lean + ht * 0.5) * (HR + 0.03)
    hcy = sy + math.cos(lean + ht * 0.5) * (HR + 0.03)
    ctx.new_path()
    ctx.arc(X(hcx), Y(hcy), HR * S, 0, 2 * math.pi)
    ctx.set_source_rgb(0.05, 0.05, 0.10)
    ctx.fill_preserve()
    ctx.set_source_rgb(*col)
    ctx.set_line_width(lw)
    ctx.stroke()
    ex = HR * 0.42
    lookdown = -HR * 0.25 * math.sin(ht)
    for s_ in (0.35, 1.0):                                         # eyes (offset toward the facing side)
        cx_ = hcx + face * (ex * s_ + 0.01)
        cy_ = hcy + HR * 0.18 + lookdown
        if eyes == "closed":
            ctx.move_to(X(cx_ - 0.025), Y(cy_))
            ctx.line_to(X(cx_ + 0.025), Y(cy_))
            ctx.set_source_rgb(1, 1, 1)
            ctx.set_line_width(lw * 0.5)
            ctx.stroke()
        else:
            r = HR * (0.16 if eyes == "wide" else 0.11)
            ctx.new_path()
            ctx.arc(X(cx_), Y(cy_), r * S, 0, 2 * math.pi)
            ctx.set_source_rgb(1, 1, 1)
            ctx.fill()
    mx, my = hcx + face * HR * 0.45, hcy - HR * 0.35 + lookdown
    ctx.new_path()
    ctx.set_source_rgb(1, 1, 1)
    ctx.set_line_width(lw * 0.55)
    if mouth == "smile":
        ctx.arc(X(mx), Y(my + HR * 0.12), HR * 0.22 * S, 0.2 * math.pi, 0.8 * math.pi)
        ctx.stroke()
    elif mouth == "open":
        ctx.arc(X(mx), Y(my), HR * 0.13 * S, 0, 2 * math.pi)
        ctx.fill()
    else:
        ctx.move_to(X(mx - HR * 0.15), Y(my))
        ctx.line_to(X(mx + HR * 0.15), Y(my))
        ctx.stroke()
    return hands, (hcx, hcy)


# ---------------------------------------------------------------- the story: Dot's track
def kf_pose(t, keys):
    """keys: [(t, pose_name_or_callable)], blended over 0.25 s."""
    cur = keys[0][1]
    prev, t_ch = cur, -10.0
    for tk, name in keys:
        if t >= tk:
            prev, cur, t_ch = cur, name, tk
    get = lambda n: n(t) if callable(n) else POSES[n]          # noqa: E731
    u = smooth((t - t_ch) / 0.25)
    return blend(get(prev), get(cur), u)


def hop(t, t0, dur, h):
    if t0 <= t < t0 + dur:
        u = (t - t0) / dur
        return 4 * h * u * (1 - u)
    return 0.0


# ---------------------------------------------------------------- scene constants
X1, X1B, XPL, XEQ, XR = 1.3, 2.7, 2.0, 3.4, 4.1
KICKS = [9.4, 10.1, 10.7, 11.2, 11.6, 11.95, 12.25, 12.5]            # each kick adds one "+1": 2 → 10
STEP = 0.72
X10 = 14.0                                                          # where the "10" ends up
EXP_T = [16.4, 17.7, 19.0]                                          # 10² · 10³ · 10⁴
PH = 1.2                                                            # pillar height per power of ten
STAIRS_T = 21.6
HOPS = [22.6, 23.6, 24.6, 25.6]                                     # down to 1000, 100, 10, 1
SW = 1.3                                                            # step width
PIT_X0 = X10 + SW * 4 + SW / 2                                       # where the pit begins (right edge of the "1" tile)


def ones_at(t):
    if t < 7.2:
        return 2
    return 2 + sum(1 for k in KICKS if t >= k + 0.12)


def tower_level(t):
    lv = 1.0
    for k, te in enumerate(EXP_T):
        lv += smooth((t - te) / 0.6)
    return lv                                                       # 1 (10) … 4 (10 000)


def pit_steps():
    out, x, y, w, hgt = [], PIT_X0, 0.0, SW * 0.6, 1.2 * 0.55
    for j in range(16):
        out.append((x, y - hgt, w, 10 ** -(j + 1)))
        x += w
        y -= hgt
        w *= 0.6
        hgt *= 0.6
    return out


PIT = pit_steps()
PIT_X1 = PIT[-1][0] + PIT[-1][2] * 2                                # far edge of the pit


def dot_track(t):
    """x, y(feet), face, pose, mouth, eyes, airborne, tremble."""
    mouth, eyes, tremble, face = "smile", "open", 0.0, 1
    if t < 1.6:                                                      # asleep
        return 0.0, 0.0, 1, POSES["sit"], "flat", "closed", 0.0, 0.0
    if t < 9.0:
        if t < 2.0:
            return 0.0, 0.0, 1, blend(POSES["sit"], POSES["jump"], smooth((t - 1.6) / 0.15)), "open", "wide", hop(t, 1.6, 0.4, 0.35), 0
        x = lerp(0.0, 0.75, smooth((t - 2.6) / 0.8))
        keys = [(0, "stand"), (2.6, lambda tt: cycle(tt)), (3.4, "stand"), (3.45, "poke"), (3.9, "stand"),
                (5.3, "carry"), (5.8, lambda tt: cycle(tt)), (6.2, "plant"), (6.7, "stand"), (7.3, "cheer"),
                (8.3, "stand")]
        if t >= 5.8:
            x = lerp(0.75, XPL - 0.55, smooth((t - 5.8) / 0.45))
        return x, 0.0, 1, kf_pose(t, keys), "open" if 7.2 <= t < 8.3 else "smile", "wide" if 2.0 <= t < 2.6 else "open", \
            hop(t, 7.3, 0.5, 0.35), 0.0
    if t < 15.0:                                                     # kicking +1s along the growing sum
        k = ones_at(t)
        target = X1 + STEP * (2 * k) + 0.8                           # just right of the result
        x = lerp(XPL - 0.55, X1 + STEP * 4 + 0.8, smooth((t - 9.0) / 0.35)) if t < 9.4 else None
        if x is None:
            prev_k = max(2, k - 1)
            t_last = max([kk for kk in KICKS if kk + 0.12 <= t] or [9.4])
            x = lerp(X1 + STEP * (2 * prev_k) + 0.8, target, smooth((t - t_last - 0.12) / 0.3))
        if t >= 12.9:                                                # the chain collapses → Dot steps to the "10"
            x = lerp(X1 + STEP * 20 + 0.8, X10 + 1.2, smooth((t - 12.9) / 0.9))
        keys = [(9.0, lambda tt: cycle(tt, True)), (9.35, "stand")]
        for kk in KICKS:
            keys += [(kk - 0.05, "kick"), (kk + 0.2, lambda tt: cycle(tt, True))]
        keys += [(12.7, "stand"), (12.9, "crouch"), (13.8, "stand"), (14.2, "dust"), (14.8, "stand")]
        return x, 0.0, 1, kf_pose(t, keys), "open" if 12.9 <= t < 13.8 else "smile", "open", 0.0, 0.0
    if t < 21.6:                                                     # the tower
        face = -1
        keys = [(14.8, "stand"), (15.0, "kick"), (15.35, "stand"), (15.6, "crouch"), (15.85, "jump"), (16.2, "stand")]
        x = X10 + 1.2 if t < 15.85 else lerp(X10 + 1.2, X10, smooth((t - 15.85) / 0.35))
        top = PH * tower_level(t)
        y = 0.0 if t < 15.85 else (top if t >= 16.2 else lerp(0.0, PH, smooth((t - 15.85) / 0.35)))
        air = hop(t, 15.85, 0.35, 0.8)
        for te in EXP_T[1:]:                                         # stomps
            keys += [(te - 0.35, "crouch"), (te - 0.15, "jump"), (te + 0.15, "stand")]
            air += hop(t, te - 0.15, 0.3, 0.3)
        keys += [(19.6, "nervous")]
        if t >= 16.2:
            face = 1
        return x, y, face, kf_pose(t, keys), "open" if t >= 19.6 else "smile", "wide" if t >= 19.6 else "open", air, \
            (1.0 if t >= 19.6 else 0.0)
    if t < 27.6:                                                     # hopping down the ÷10 stairs
        lvl = 4
        x, y, air = X10, PH * 4, 0.0
        for j, th in enumerate(HOPS):
            if t >= th:
                u = smooth((t - th) / 0.5)
                x0, y0 = X10 + SW * j, PH * (4 - j - 0) if j > 0 else PH * 4
                y0 = PH * (4 - j)
                x = lerp(X10 + SW * j, X10 + SW * (j + 1), u)
                y = lerp(y0, PH * (3 - j), u)
                air = hop(t, th, 0.5, 0.45)
                lvl = 3 - j
        keys = [(21.6, "nervous"), (22.2, "stand")]
        for th in HOPS:
            keys += [(th - 0.2, "crouch"), (th, "jump"), (th + 0.45, "stand")]
        keys += [(26.6, "cheer"), (27.3, "stand")]
        return x, y, 1, kf_pose(t, keys), "smile", "open", air, 0.0
    if t < 33.6:                                                     # the infinite pit
        x = lerp(X10 + SW * 4, PIT_X0 - 0.35, smooth((t - 27.6) / 0.8))
        keys = [(27.6, lambda tt: cycle(tt)), (28.4, "stand"), (28.5, "lookdown"), (29.0, "poke"), (29.4, "lookdown"),
                (32.0, "shrug"), (33.0, "stand")]
        return x, 0.0, 1, kf_pose(t, keys), "open" if 30.0 <= t < 31.8 else "smile", "open", 0.0, 0.0
    # the ∞ boulder
    x = PIT_X0 - 0.35
    keys = [(33.6, "stand"), (34.2, "nervous")]
    face = -1 if 34.0 <= t < 34.9 else 1
    air = 0.0
    if t >= 34.9:
        keys += [(34.9, lambda tt: cycle(tt, True)), (35.25, "jump"), (35.95, lambda tt: cycle(tt, True)),
                 (36.8, "stand"), (37.1, "peek")]
        x = lerp(PIT_X0 - 0.35, PIT_X1 + 1.6, smooth((t - 34.9) / 1.9))
        air = hop(t, 35.25, 0.7, 0.9)
        face = 1 if t < 36.9 else -1
    return x, 0.0, face, kf_pose(t, keys), "open" if t >= 34.0 else "smile", "wide" if 34.0 <= t < 36.8 else "open", \
        air, (1.0 if 34.2 <= t < 34.9 else 0.0)


BOULDER_PATH = [(34.3, X10, PH * 4), (34.65, X10 + SW, PH * 3), (35.0, X10 + 2 * SW, PH * 2),
                (35.35, X10 + 3 * SW, PH * 1), (35.7, X10 + 4 * SW, 0.0), (36.3, PIT_X0 + 0.2, 0.0)]


def boulder_pos(t):
    """The ∞ bounces down the ÷10 stairs, rolls to the pit (then falls into it, handled in draw)."""
    if t < 34.3:
        return None
    for (t0, x0, y0), (t1, x1, y1) in zip(BOULDER_PATH, BOULDER_PATH[1:]):
        if t < t1:
            u = (t - t0) / (t1 - t0)
            bounce = 0.0 if y0 == y1 else 4 * 0.6 * u * (1 - u)
            return lerp(x0, x1, u), lerp(y0, y1, u) + bounce
    return PIT_X0 + 0.2, 0.0


# ---------------------------------------------------------------- render
def simulate():
    return {"nf": int(round(T_LOOP * FPS))}


class Scene:
    def __init__(self, layout, sim):
        self.L, self.sim = layout, sim
        self.canvas = Canvas(layout.w, layout.h, studio.render_scale())

    def cam(self, t):
        xs = [dot_track(max(0.0, t - d))[0] for d in (0.0, 0.15, 0.3, 0.45)]
        cx = sum(xs) / len(xs)
        if t < 9.0:
            cx = max(cx, 2.2)
        if 9.0 <= t < 13.6:                                          # lean back to show more of the growing sum
            cx -= 1.8 * smooth((t - 9.0) / 0.6)
        if 33.6 <= t < 35.4:                                         # look back at the tower top (the ∞ appears)
            u = smooth((t - 33.7) / 0.5) * (1 - smooth((t - 35.0) / 0.4))
            cx -= 1.9 * u
        if 27.6 <= t < 33.6:
            cx += 0.8 * smooth((t - 28.2) / 1.0)
        cy = 0.0
        if 15.8 <= t < 22.6:
            cy = PH * tower_level(t) * 0.75 * smooth((t - 15.8) / 0.8)
        elif 22.6 <= t < 27.6:
            cy = dot_track(t)[1] * 0.75
        elif 28.4 <= t < 33.6:
            cy = -0.9 * smooth((t - 28.4) / 1.0) * (1 - smooth((t - 33.0) / 0.6))
        elif 33.6 <= t < 35.6:
            cy = 0.9 * smooth((t - 33.7) / 0.5) * (1 - smooth((t - 35.0) / 0.5))
        shake = 0.04 * math.sin(t * 70) * (1 if 33.6 <= t < 36.5 else 0)
        return cx + shake, cy

    def draw(self, f, rule):
        L, c = self.L, self.canvas
        w, h = L.w, L.h
        t = f * DT
        ctx = c.ctx
        S = h * 0.31
        camx, camy = self.cam(t)
        X = lambda x: w / 2 + (x - camx) * S                    # noqa: E731
        Y = lambda y: h * 0.72 - (y - camy) * S                 # noqa: E731
        g = cairo.LinearGradient(0, 0, 0, h)
        g.add_color_stop_rgb(0, 0.05, 0.05, 0.11)
        g.add_color_stop_rgb(1, 0.01, 0.01, 0.03)
        ctx.set_source(g)
        ctx.paint()
        gx0 = math.floor((camx - 6) / 0.5) * 0.5                        # faint world grid
        for i in range(30):
            xx = gx0 + i * 0.5
            c.lines([(X(xx), 0, X(xx), h)], (0.5, 0.55, 0.9), width=1, alpha=0.05)
        for j in range(-12, 12):
            yy = math.floor(camy) + j * 0.5
            c.lines([(0, Y(yy), w, Y(yy))], (0.5, 0.55, 0.9), width=1, alpha=0.05)

        def glyph(txt, x, y, size, col=WHITE, alpha=1.0, rot=0.0, bold=True):
            """Text standing on (x, y) (baseline), size in world units."""
            ctx.save()
            ctx.translate(X(x), Y(y))
            ctx.rotate(rot)
            ctx.select_font_face("Arial", cairo.FONT_SLANT_NORMAL,
                                 cairo.FONT_WEIGHT_BOLD if bold else cairo.FONT_WEIGHT_NORMAL)
            ctx.set_font_size(size * S)
            e = ctx.text_extents(txt)
            ctx.move_to(-e.width / 2 - e.x_bearing, 0)
            ctx.set_source_rgba(*col, alpha)
            ctx.show_text(txt)
            ctx.restore()

        # ground (with the pit cut out)
        ctx.rectangle(0, Y(0), max(0, X(PIT_X0) - 0), h)
        ctx.set_source_rgb(0.035, 0.035, 0.07)
        ctx.fill()
        ctx.rectangle(X(PIT_X1), Y(0), w, h)
        ctx.fill()
        c.lines([(0, Y(0), X(PIT_X0), Y(0)), (X(PIT_X1), Y(0), w, Y(0))], (0.75, 0.78, 0.9), width=3, alpha=0.6)
        # the pit's infinite ÷10 stairs (visible once the stairs exist)
        if t >= STAIRS_T:
            for (sx, sy, sw, val) in PIT:
                ctx.rectangle(X(sx), Y(sy), sw * S, max(1.0, -sy * S))
                ctx.set_source_rgb(0.10, 0.10, 0.18)
                ctx.fill()
                c.lines([(X(sx), Y(sy), X(sx + sw), Y(sy))], (0.75, 0.78, 0.9), width=2, alpha=0.6)
                if sw * S > 22:
                    lab = f"{val:.{-int(round(math.log10(val)))}f}"
                    glyph(lab, sx + sw / 2, sy + 0.05, min(0.32, sw * 0.32), GOLD if t >= 29.0 else WHITE, 0.9)
        # scene 1-3: the sum on the ground
        if t < 13.8:
            k = ones_at(t)
            coll = smooth((t - 12.9) / 0.5) if t >= 12.9 else 0.0
            toks = []
            for i in range(k):
                toks.append(("1", X1 + STEP * 2 * i))
                if i < k - 1:
                    toks.append(("+", X1 + STEP * (2 * i + 1)))
            toks.append(("=", X1 + STEP * (2 * k - 1)))
            toks.append((str(k), X1 + STEP * (2 * k)))
            for i, (txt, x) in enumerate(toks):
                xx = lerp(x, X10, coll)
                if txt == "1" and i == 0 and t < 4.5:                # the first falling "1"
                    y = max(0.0, 6.0 - 9.8 * max(0.0, t - 1.0) ** 2 * 1.4) if t >= 1.0 else None
                    if y is None:
                        continue
                    wob = math.sin((t - 3.5) * 25) * math.exp(-(t - 3.5) * 4) * 0.25 if t >= 3.5 else 0.0
                    glyph("1", xx, y, 0.9, WHITE, rot=wob)
                    continue
                if t < 7.2:                                          # the scene-2 objects, built up in order
                    if i == 0:
                        glyph("1", xx, 0.0, 0.9)
                    elif txt == "1" and i == 2 and t >= 4.5:
                        y = max(0.0, 6.0 - 9.8 * max(0.0, t - 4.5) ** 2 * 1.4)
                        glyph("1", xx, y, 0.9)
                    elif txt == "+" and t >= 5.3:
                        if t < 6.2:
                            hx, hy = dot_track(t)[0] + 0.05, 1.45
                            glyph("+", hx, hy, 0.8, GOLD)
                        else:
                            glyph("+", xx, 0.0, 0.9, WHITE)
                    continue
                if txt in ("=",) or txt == str(k):
                    pop = math.exp(-(t - (7.2 if k == 2 else KICKS[k - 3] + 0.12)) / 0.15)
                    col = GOLD if txt == str(k) else WHITE
                    glyph(txt, xx, 0.0, 0.9 * (1 + 0.25 * pop * (txt != "=")) * (1 - coll * 0.5), col, alpha=1 - coll)
                else:
                    glyph(txt, xx, 0.0, 0.9 * (1 - coll * 0.5), WHITE, alpha=1 - coll)
            if t >= 13.2:
                a10 = smooth((t - 13.2) / 0.3)
                glyph("10", X10, 0.0, 1.4 * (1 + 0.3 * math.exp(-(t - 13.2) / 0.15)), GOLD, alpha=a10)
        # scene 4-5: the 10^k tower and the ÷10 stairs
        if t >= 13.8:
            lv = tower_level(t)
            top = PH * lv
            ctx.rectangle(X(X10 - SW / 2), Y(top), SW * S, top * S)
            ctx.set_source_rgb(0.16, 0.16, 0.28)
            ctx.fill()
            c.lines([(X(X10 - SW / 2), Y(top), X(X10 + SW / 2), Y(top))], GOLD, width=4)
            k = int(round(lv)) if abs(lv - round(lv)) < 0.05 else int(lv)
            val = 10 ** k
            glyph(f"{val:,}", X10, top - 0.55, 0.42 if k < 4 else 0.34, GOLD)
            if t >= 14.8:
                ex = "" if k == 1 else "²³⁴"[k - 2]
                glyph(f"10{ex}", X10 - SW * 0.95, top - 0.25, 0.4, WHITE)
            if t < 15.0:                                             # the little "2" lying on the ground
                glyph("2", X10 + 1.9, 0.0, 0.45, WHITE)
            elif t < 16.4:
                u = smooth((t - 15.0) / 1.2)
                glyph("2", lerp(X10 + 1.9, X10 + 0.3, u), hop(t, 15.0, 1.2, 1.6) + u * PH, 0.45, GOLD)
            if t >= STAIRS_T:                                        # the stairs (rise out of the ground)
                rise = smooth((t - STAIRS_T) / 0.6)
                for j in range(4):
                    sx = X10 + SW * (j + 1) - SW / 2
                    sh = PH * (3 - j) * rise
                    if sh > 0.01:
                        ctx.rectangle(X(sx), Y(sh), SW * S, sh * S)
                        ctx.set_source_rgb(0.14, 0.14, 0.25)
                        ctx.fill()
                    lit = t >= HOPS[j] + 0.45
                    c.lines([(X(sx), Y(sh), X(sx + SW), Y(sh))], GOLD if lit else (0.75, 0.78, 0.9), width=4)
                    glyph(f"{10 ** (3 - j):,}", sx + SW / 2, sh + 0.08, 0.36, GOLD if lit else WHITE, rise)
                    glyph("÷10", sx + 0.05, sh + PH * 0.55 * rise + 0.15, 0.24, (0.75, 0.78, 0.9), rise * 0.9, bold=False)
        # the pebble that falls forever (Zeno)
        if 29.0 <= t < 34.5:
            tt = t - 29.0
            j = 0
            acc, dur = 0.0, 0.5
            while acc + dur < tt and j < len(PIT) - 1:
                acc += dur
                dur *= 0.72
                j += 1
            sx, sy, sw, _ = PIT[j]
            u = (tt - acc) / dur
            px = lerp(PIT_X0 - 0.15 if j == 0 else PIT[j - 1][0] + PIT[j - 1][2] / 2, sx + sw / 2, u)
            py = lerp(0.0 if j == 0 else PIT[j - 1][1], sy, u) + 4 * 0.25 * (0.6 ** j) * u * (1 - u)
            glyph("1", px, py, 0.3 * (0.75 ** j), GOLD)
            if t >= 30.0:
                a = smooth((t - 30.0) / 0.4) * (1 - smooth((t - 33.2) / 0.4))
                glyph("1 ÷ 10 ÷ 10 ÷ 10 …  →  0", PIT_X0 + 1.3, 1.05, 0.3, WHITE, a)
                glyph("(it never gets there)", PIT_X0 + 1.3, 0.72, 0.22, (0.75, 0.78, 0.9), a, bold=False)
        # the ∞ boulder
        bp = boulder_pos(t)
        if bp is not None:
            bx, by = bp
            sc = 1.0
            if t >= 36.3:
                fall = smooth((t - 36.3) / 1.6)
                j = min(len(PIT) - 1, int(fall * 10))
                bx = lerp(PIT_X0 + 0.2, PIT[j][0] + PIT[j][2] / 2, fall)
                by = PIT[j][1] * fall
                sc = 0.7 ** (fall * 8)
            glyph("∞", bx, by, 1.6 * sc, GOLD, rot=0.15 * math.sin(t * 9))
            if t < 36.3:                                             # motion lines
                for k in range(3):
                    c.lines([(X(bx - 0.9 - 0.25 * k), Y(by + 0.3 + 0.2 * k), X(bx - 0.6 - 0.25 * k), Y(by + 0.3 + 0.2 * k))],
                            GOLD, width=3, alpha=0.5)
        # Dot
        x, yf, face, pose, mouth, eyes, air, trem = dot_track(t)
        draw_puppet(ctx, X, Y, S, x, yf, face, pose, mouth, eyes, tremble=trem, t=t, airborne=air)
        if t < 1.6:                                                  # Zz
            for k in range(3):
                ph = (t * 0.8 + k / 3) % 1.0
                glyph("z", 0.35 + ph * 0.5, 1.1 + ph * 0.7, 0.25 * (0.6 + ph), GOLD, 1 - ph, bold=False)
        if 2.0 <= t < 2.6 or 33.6 <= t < 34.3:
            glyph("!", x + 0.05, 1.35, 0.45, GOLD)
        if t >= 38.3:                                                # end card
            a = smooth((t - 38.3) / 0.5)
            c.text_centered("to be continued…", h * 0.16, size=h * 0.07, color=GOLD, alpha=a)
        if t < 3.0:
            c.text_centered("DOT VS. NUMBERS", h * 0.12, size=h * 0.06, color=GOLD, alpha=1 - smooth((t - 2.2) / 0.8))
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


# ---------------------------------------------------------------- sound
def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def bed():
    n = int(round(T_LOOP * SR))
    out = np.zeros(n + 3 * SR)
    rng = np.random.default_rng(21)

    def add(t0, sig, g=1.0):
        i0 = int(t0 * SR)
        sig = sig[: max(0, len(out) - i0)]
        out[i0:i0 + len(sig)] += g * sig

    def tone(f, dur, decay, harm=((1, 1.0), (2, 0.3))):
        tv = np.arange(int(dur * SR)) / SR
        return sum(a * np.sin(2 * np.pi * f * k * tv) for k, a in harm) * np.exp(-tv / decay)

    def thud(t0, g=0.5):
        tv = np.arange(int(0.4 * SR)) / SR
        add(t0, np.sin(2 * np.pi * np.cumsum(55 + 70 * np.exp(-tv / 0.03)) / SR) * np.exp(-tv / 0.12), g)
        add(t0, np.diff(np.concatenate([[0], rng.standard_normal(len(tv))])) * np.exp(-tv / 0.04), 0.06 * g / 0.5)

    def pop(t0, m=72, g=0.12):
        tv = np.arange(int(0.09 * SR)) / SR
        f = hz(m) * (1 + 1.5 * tv / 0.09)
        add(t0, np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tv / 0.04), g)

    def ding(t0, base=84):
        for m in (base, base + 4, base + 7):
            add(t0, tone(hz(m), 1.2, 0.4, ((1, 1.0), (2.76, 0.25))), 0.06)

    def whoosh(t0, dur=0.25, g=0.06):
        tv = np.arange(int(dur * SR)) / SR
        nz = np.diff(np.concatenate([[0], rng.standard_normal(len(tv))]))
        add(t0, nz * np.sin(np.pi * tv / dur), g)

    # soft plucked loop (quiet under the action), pauses for the nervous tower top
    beat = 0.5
    prog = [(48, (60, 64, 67)), (45, (60, 64, 69)), (41, (60, 65, 69)), (43, (59, 62, 67))]
    tb, b = 2.0, 0
    while tb < 38.0:
        if not (19.6 <= tb < 21.6 or 33.6 <= tb < 36.8):
            root, ch = prog[b % 4]
            add(tb, tone(hz(root), 1.0, 0.3), 0.08)
            for e in range(8):
                m = ch[(e * 2) % 3] + (12 if e % 4 == 3 else 0)
                add(tb + e * beat / 2, tone(hz(m), 0.3, 0.08, ((1, 1.0), (2, 0.5), (3, 0.2))), 0.03)
        tb += 4 * beat
        b += 1
    # story SFX
    for k in range(3):                                                # snoring
        add(0.2 + 0.55 * k, tone(140, 0.45, 0.3, ((1, 1.0), (2, 0.5), (3, 0.3))) * np.sin(np.linspace(0, np.pi, int(0.45 * SR))), 0.03)
    whoosh(1.0, 0.4, 0.05)
    thud(1.55)
    pop(1.62, 84, 0.10)
    pop(3.45, 76)
    whoosh(4.5, 0.4, 0.05)
    thud(5.05, 0.4)
    pop(5.3, 79)
    thud(6.25, 0.3)
    pop(6.9, 74)
    ding(7.2)
    for i, kk in enumerate(KICKS):
        whoosh(kk - 0.05, 0.15, 0.07)
        thud(kk + 0.05, 0.22)
        pop(kk + 0.12, 72 + 2 * i, 0.10)
    ding(12.62)
    for k in range(8):
        pop(12.9 + 0.08 * k, 88 - 3 * k, 0.08)
    thud(13.7, 0.35)
    whoosh(15.0, 0.2, 0.07)
    for i, te in enumerate(EXP_T):                                   # the tower grows: rising tone
        tv = np.arange(int(0.6 * SR)) / SR
        f = hz(55 + 7 * i) * (1 + tv / 0.6)
        add(te, np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * tv / 0.6), 0.10)
        ding(te + 0.6, 79 + 5 * i)
    thud(15.95, 0.3)
    tv = np.arange(int(1.6 * SR)) / SR                               # nervous tremolo at the top
    add(19.7, np.sin(2 * np.pi * 300 * tv) * (0.5 + 0.5 * np.sin(2 * np.pi * 14 * tv)) * np.sin(np.pi * tv / 1.6), 0.03)
    thud(STAIRS_T, 0.3)
    for j, th in enumerate(HOPS):                                     # stepping down: falling notes
        thud(th + 0.48, 0.2)
        pop(th + 0.5, 79 - 4 * j, 0.12)
    ding(26.6, 72)
    tt, dur, j = 29.0, 0.5, 0                                         # the pebble: ever-faster, ever-quieter ticks
    while tt < 33.5 and j < 40:
        add(tt, tone(hz(84 + j), 0.08, 0.02), 0.06 * (0.88 ** j))
        tt += dur
        dur *= 0.72
        j += 1
    tv = np.arange(int(3.0 * SR)) / SR                                # rumble + the ∞ rolling
    add(33.6, np.convolve(rng.standard_normal(len(tv)), np.ones(200) / 200, mode="same") * np.clip(tv / 0.5, 0, 1) *
        np.clip((3.0 - tv) / 0.5, 0, 1), 0.6)
    whoosh(35.2, 0.5, 0.06)
    thud(35.95, 0.3)
    tv = np.arange(int(2.2 * SR)) / SR                                # ∞ falls forever: a falling whistle
    f = 1200 * np.exp(-tv / 0.8) + 200
    add(36.3, np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tv / 1.2), 0.04)
    ding(38.3, 72)
    tail = out[n:]
    out = out[:n]
    return out.astype(np.float32)


def _worker(o, sim, label, rule):
    layout = get_layout("horizontal")
    name = f"{SCENE}_{label}_{layout.tag}"
    video = studio.OUT_DIR / f"{name}_silent.mp4"
    d = render(layout, sim, video, rule)
    kit.deliver(SCENE, name, layout, video, [{"t": 0.0, "note": 60, "gain": 0.0001, "x": 960}], d, voice="piano",
                bed=bed(), peak_db=-6.0)


def main():
    label = arg("--label", "v1")
    studio.OUT_DIR.mkdir(exist_ok=True)
    sim = simulate()
    if kit.has("--still"):
        layout = get_layout("horizontal")
        f = int(arg("--frame", "0"))
        png = studio.OUT_DIR / f"{SCENE}_{label}_f{f}.png"
        render(layout, sim, png, "", still_frame=f)
        print(png)
        return
    print(f"[{SCENE}] {T_LOOP:.1f}s")
    _worker("horizontal", sim, label, "")


if __name__ == "__main__":
    main()
