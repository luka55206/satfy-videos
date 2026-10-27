"""DOT: THE WAY HOME — one continuous stick-figure film (16:9, ~2:03), side view. Same world/puppet as dot_adventure.

Causal chain (nothing without a reason):
 hook: Dot runs across a bridge that a hungry Zero eats behind him → "earlier…"
 1. Dot wakes on a cliff. A sign: "HOME → 100". Far away across an endless gap: his house, high on a cliff.
 2. A pile of "1" planks (and one odd "÷" he pockets out of curiosity). He lays planks one by one: 1+1+… = 10.
 3. Exhausted after 10 of 100 (keeps a spare "1" as a walking stick) → idea: bundle 10 planks into a "10" beam,
    then 10 beams: 10 × 10 = 100. The bridge shoots across.          (adding is too slow → multiplication)
 4. Across, his house sits on a ledge 1,000 up. A "10" block: each stomp ×10 → 10², 10³ = 1,000. (he needs height)
 5. Too excited, one stomp more: 10⁴ = 10,000 — way above. The pocket "÷": 10,000 ÷ 10 = 1,000. (he overshot)
 6. The door is locked. A rumble: Zero rolls in, eating the bridge (100 × 0 = 0) and the block (1,000 × 0 = 0),
    rolls up the wall. Cornered, Dot holds up his "1" stick and the "÷": Zero swallows "1 ÷ 0" → ERROR → pop.
 7. Click: the door opens. Home. Far away, a new sign: "∞ →". To be continued.
Audio (original): plucked theme, plank taps, pops, dings, rumble, Zero's chomps and glitch, door sounds.
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
import dot_adventure as DA  # noqa: E402

SCENE = "dot_wayhome"
T_END = 123.0
SR = audio.SR
BLUE, GOLD, WHITE = DA.BLUE, DA.GOLD, DA.WHITE
RED = (1.0, 0.35, 0.40)
L = 0.6                                                              # one "1" plank
PILE_X = -2.2
FAR_X0, WALL_X, LEDGE_Y, LEDGE_X1 = 60.8, 63.0, 4.8, 74.0
BLOCK_X = 61.8
HOUSE_X = 67.5
PH = 1.6                                                             # tower height per power of ten


def lerp(a, b, u):
    return a + (b - a) * u


# ---------------------------------------------------------------- plank-laying schedule (gets slower: longer walks)
def plank_schedule():
    out, t = [], 17.0
    for i in range(10):
        end = i * L
        d = abs(end - PILE_X) + 0.3
        go = d / (7.0 - 0.3 * i)
        out.append(dict(t_pick=t, t_walk0=t + 0.25, t_place=t + 0.25 + go, t_back=t + 0.55 + go,
                        t_done=t + 0.55 + 2 * go, end=end))
        t = t + 0.55 + 2 * go
    return out


PLANKS = plank_schedule()
T_TIRED = PLANKS[-1]["t_place"] + 0.4                                # collapses at the bridge end


def planks_down(t):
    return sum(1 for p in PLANKS if t >= p["t_place"])


# ---------------------------------------------------------------- key times
T_BULB, T_BUNDLE, T_PUSH = T_TIRED + 2.4, T_TIRED + 4.0, T_TIRED + 7.0
T_COPY = [T_PUSH + 0.3 + 0.32 * k for k in range(9)]
T_BRIDGE = T_COPY[-1] + 0.4
T_RUN0, T_RUN1 = T_BRIDGE + 1.0, T_BRIDGE + 9.0
T_JUMP_BLOCK = T_RUN1 + 3.0
T_STOMP = [T_JUMP_BLOCK + 1.4, T_JUMP_BLOCK + 3.0, T_JUMP_BLOCK + 5.6]     # 10² · 10³ · (too much) 10⁴
T_DIV = T_STOMP[2] + 3.6
T_LEDGE = T_DIV + 1.2
T_DOOR = T_LEDGE + 2.6
T_RUMBLE = T_DOOR + 1.6
T_ZERO0, T_ZERO1 = T_RUMBLE + 2.0, T_RUMBLE + 9.0                    # Zero eats the bridge (x 0 → 60)
T_ZBLOCK = T_ZERO1 + 0.6
T_ZWALL0, T_ZWALL1 = T_ZBLOCK + 0.8, T_ZBLOCK + 2.6
T_CORNER = T_ZWALL1 + 5.0
T_SWALLOW = T_CORNER + 2.6
T_POP = T_SWALLOW + 3.8
T_CLICK = T_POP + 1.8
T_INSIDE = T_CLICK + 3.5
T_TITLE = T_INSIDE + 5.0
assert T_TITLE + 5.0 <= T_END + 1e-6, T_TITLE


def tower_level(t):
    lv = 1.0 + sum(smooth((t - ts) / 0.6) for ts in T_STOMP)
    lv -= smooth((t - T_DIV) / 0.6)
    if t >= T_ZBLOCK:
        lv *= 1 - smooth((t - T_ZBLOCK) / 0.4)
    return lv


def zero_pos(t):
    """Zero's (x, y): eats the bridge left → right, the block, then rolls up the wall to the ledge."""
    if t < T_ZERO0:
        return None
    if t < T_ZERO1:
        return lerp(-3.0, FAR_X0 - 0.2, smooth((t - T_ZERO0) / (T_ZERO1 - T_ZERO0))), 0.0
    if t < T_ZWALL0:
        return lerp(FAR_X0 - 0.2, BLOCK_X - 0.6, smooth((t - T_ZERO1) / (T_ZWALL0 - T_ZERO1))), 0.0
    if t < T_ZWALL1:
        u = smooth((t - T_ZWALL0) / (T_ZWALL1 - T_ZWALL0))
        return lerp(BLOCK_X - 0.6, WALL_X + 0.6, u), LEDGE_Y * min(1.0, u * 1.25)
    if t < T_SWALLOW:
        return lerp(WALL_X + 0.6, LEDGE_X1 - 2.6, smooth((t - T_ZWALL1) / (T_SWALLOW - T_ZWALL1))), LEDGE_Y
    return LEDGE_X1 - 2.6, LEDGE_Y


# ---------------------------------------------------------------- Dot
POSES = dict(DA.POSES)
POSES.update({
    "hold": dict(lean=0, head=-10, af=(150, 200), ab=(-150, -200), lf=(8, 2), lb=(-8, -2)),
    "push": dict(lean=30, head=0, af=(80, 85), ab=(75, 80), lf=(30, 10), lb=(-35, -20)),
    "rattle": dict(lean=10, head=0, af=(85, 95), ab=(80, 100), lf=(12, 2), lb=(-12, -2)),
    "panic": dict(lean=-10, head=-15, af=(160, 200), ab=(-160, -200), lf=(15, 5), lb=(-15, -5)),
    "brandish": dict(lean=5, head=-5, af=(90, 95), ab=(70, 80), lf=(20, 5), lb=(-20, -5)),
})


def P_(name, t):
    if name == "walk":
        return DA.cycle(t)
    if name == "run":
        return DA.cycle(t, True)
    if name == "carry":
        p = DA.cycle(t)
        return dict(p, af=(160, 190), ab=(-160, -190))
    return POSES[name]


def dot_state(t):
    """(x, y_feet, face, pose_name, extras)."""
    ex = {}
    if t < 4.6:                                                      # hook: running across, Zero right behind
        return lerp(28.0, 37.0, t / 4.6), 0.0, 1, "run", dict(mouth="open", eyes="wide")
    if t < 6.2:
        return lerp(37.0, -1.2, smooth((t - 4.6) / 1.6)), 0.0, 1, "stand", dict(hide=True)
    if t < 8.0:
        return -1.2, 0.0, 1, "sit", dict(eyes="closed", mouth="flat", zz=True)
    if t < 8.5:
        return -1.2, 0.0, 1, "jump", dict(eyes="wide", mouth="open", bang=True, air=DA.hop(t, 8.0, 0.5, 0.35))
    if t < 9.3:
        return -1.2, 0.0, 1, "stand", {}
    if t < 10.2:
        return lerp(-1.2, -0.5, smooth((t - 9.3) / 0.9)), 0.0, 1, "walk", {}
    if t < 14.5:
        return -0.5, 0.0, 1, ("lookdown" if t < 10.6 else "stand"), dict(mouth="open" if t > 11.5 else "smile")
    if t < 15.0:
        return lerp(-0.5, PILE_X + 0.4, smooth((t - 14.5) / 0.5)), 0.0, -1, "walk", {}
    if t < 16.4:                                                     # finds the odd "÷", pockets it
        return PILE_X + 0.4, 0.0, -1, ("poke" if t < 15.6 else "hold"), dict(div_hand=15.3 <= t < 16.2)
    if t < 17.0:
        return PILE_X + 0.4, 0.0, -1, "shrug", {}
    if t < T_TIRED:                                                  # laying planks one by one
        for p in PLANKS:
            if t < p["t_done"]:
                if t < p["t_walk0"]:
                    return PILE_X + 0.4, 0.0, -1, "crouch", {}
                if t < p["t_place"]:
                    u = smooth((t - p["t_walk0"]) / (p["t_place"] - p["t_walk0"]))
                    return lerp(PILE_X + 0.4, p["end"] - 0.25, u), 0.0, 1, "carry", dict(plank=True)
                if t < p["t_back"]:
                    return p["end"] - 0.25, 0.0, 1, "plant", {}
                u = smooth((t - p["t_back"]) / (p["t_done"] - p["t_back"]))
                return lerp(p["end"] - 0.25, PILE_X + 0.4, u), 0.0, -1, "walk", dict(sweat=p is PLANKS[-1] or t > 25)
        return PLANKS[-1]["end"] - 0.25, 0.0, 1, "stand", {}
    end = 10 * L - 0.25
    if t < T_BULB:
        return end, 0.0, 1, "sit", dict(sweat=True, mouth="flat", stick=True)
    if t < T_BUNDLE:
        return end, 0.0, 1, "cheer", dict(bulb=True)
    if t < T_PUSH:
        return lerp(end, -0.3, smooth((t - T_BUNDLE) / 1.0)), 0.0, 1, ("walk" if t < T_BUNDLE + 1.0 else "poke"), \
            dict(stick=True)
    if t < T_RUN0:
        return -0.3, 0.0, 1, ("push" if t < T_BRIDGE else "cheer"), dict(stick=True)
    if t < T_RUN1:
        return lerp(-0.3, BLOCK_X - 1.4, smooth((t - T_RUN0) / (T_RUN1 - T_RUN0))), 0.0, 1, "run", dict(stick=True)
    if t < T_JUMP_BLOCK:
        return BLOCK_X - 1.4, 0.0, 1, ("lookdown" if t < T_RUN1 + 1.0 else "stand"), dict(stick=True, look_up=True)
    top = PH * tower_level(t)
    if t < T_JUMP_BLOCK + 0.6:
        u = smooth((t - T_JUMP_BLOCK) / 0.6)
        return lerp(BLOCK_X - 1.4, BLOCK_X, u), lerp(0.0, PH, u), 1, "jump", dict(stick=True, air=DA.hop(t, T_JUMP_BLOCK, 0.6, 0.8))
    if t < T_DIV + 0.6:
        pose, air, extra = "stand", 0.0, dict(stick=True)
        for ts in T_STOMP:
            if ts - 0.35 <= t < ts + 0.15:
                pose = "jump" if t >= ts - 0.15 else "crouch"
                air = DA.hop(t, ts - 0.15, 0.3, 0.3)
        if T_STOMP[1] + 0.6 <= t < T_STOMP[2] - 0.4:
            pose, extra = "cheer", dict(stick=True, mouth="open")
        if T_STOMP[2] + 0.7 <= t < T_DIV - 0.8:
            pose, extra = "nervous", dict(stick=True, mouth="open", eyes="wide", trem=1.0)
        if T_DIV - 0.8 <= t < T_DIV + 0.6:
            pose, extra = "poke", dict(stick=True, div_hand=t < T_DIV)
        extra["air"] = air
        return BLOCK_X, top, 1, pose, extra
    if t < T_LEDGE:
        u = smooth((t - T_DIV - 0.6) / (T_LEDGE - T_DIV - 0.6))
        return lerp(BLOCK_X, WALL_X + 0.8, u), LEDGE_Y, 1, "jump", dict(stick=True, air=DA.hop(t, T_DIV + 0.6, T_LEDGE - T_DIV - 0.6, 0.6))
    if t < T_DOOR:
        return lerp(WALL_X + 0.8, HOUSE_X - 0.9, smooth((t - T_LEDGE) / (T_DOOR - T_LEDGE))), LEDGE_Y, 1, "walk", dict(stick=True)
    if t < T_RUMBLE:
        return HOUSE_X - 0.9, LEDGE_Y, 1, "rattle", dict(stick=True, shake=True)
    if t < T_ZWALL1:
        return HOUSE_X - 0.9, LEDGE_Y, -1, "nervous", dict(stick=True, mouth="open", eyes="wide", bang=t < T_RUMBLE + 0.8)
    if t < T_CORNER:
        u = smooth((t - T_ZWALL1) / (T_CORNER - T_ZWALL1))
        return lerp(HOUSE_X - 0.9, LEDGE_X1 - 0.8, u), LEDGE_Y, -1, ("panic" if u > 0.6 else "walk"), \
            dict(stick=True, mouth="open", eyes="wide", trem=1.0)
    if t < T_SWALLOW:
        return LEDGE_X1 - 0.8, LEDGE_Y, -1, "brandish", dict(weapon=True, bulb=t < T_CORNER + 0.6)
    if t < T_CLICK:
        return LEDGE_X1 - 0.8, LEDGE_Y, -1, ("nervous" if t < T_POP else "stand"), dict(mouth="open", eyes="wide")
    if t < T_CLICK + 1.2:
        return LEDGE_X1 - 0.8, LEDGE_Y, -1, "cheer", dict(mouth="open")
    if t < T_INSIDE:
        u = smooth((t - T_CLICK - 1.2) / (T_INSIDE - T_CLICK - 1.2))
        return lerp(LEDGE_X1 - 0.8, HOUSE_X, u), LEDGE_Y, -1, "walk", dict(fade=1 - smooth((t - T_INSIDE + 0.4) / 0.4))
    return HOUSE_X, LEDGE_Y, 1, "stand", dict(hide=True)


# ---------------------------------------------------------------- camera
CAM = [  # t, cx, cy, S (fraction of h per unit)
    (0.0, 30.0, 0.8, 0.16), (4.6, 39.0, 0.8, 0.16), (6.2, -1.8, 0.8, 0.20), (9.3, -1.2, 0.8, 0.20),
    (10.6, -0.6, 0.6, 0.20), (11.0, -0.6, 0.6, 0.20), (12.4, 33.0, 3.0, 0.022), (13.6, 33.0, 3.0, 0.022),
    (14.6, -0.6, 0.8, 0.17), (17.0, 0.4, 0.8, 0.15), (T_TIRED - 6, 2.0, 0.8, 0.12), (T_TIRED, 3.0, 0.8, 0.13),
    (T_BUNDLE, 3.0, 0.8, 0.12), (T_PUSH, 3.0, 0.8, 0.10), (T_BRIDGE, 30.0, 2.0, 0.022), (T_RUN0, 30.0, 2.0, 0.022),
    (T_RUN0 + 1.0, 4.0, 1.0, 0.08), (T_RUN1, BLOCK_X + 1.0, 1.5, 0.08), (T_RUN1 + 1.6, WALL_X + 1.0, 3.6, 0.07),
    (T_JUMP_BLOCK, BLOCK_X + 1.0, 2.0, 0.10), (T_STOMP[1] + 0.6, BLOCK_X + 1.5, 4.0, 0.10),
    (T_STOMP[2] + 0.6, BLOCK_X + 1.0, 6.2, 0.10), (T_DIV + 0.6, BLOCK_X + 2.5, 5.2, 0.10),
    (T_DOOR, HOUSE_X - 1.0, 5.6, 0.12), (T_RUMBLE, HOUSE_X - 1.0, 5.6, 0.12), (T_ZERO0, 31.0, 3.0, 0.022),
    (T_ZERO0 + 1.2, 6.0, 1.0, 0.05), (T_ZERO1, FAR_X0 - 2.0, 1.5, 0.05), (T_ZWALL1, WALL_X + 2.0, 4.0, 0.08),
    (T_CORNER, HOUSE_X + 1.5, 5.6, 0.11), (T_SWALLOW + 0.5, HOUSE_X + 2.5, 5.6, 0.13), (T_CLICK + 1.0, HOUSE_X + 1.5, 5.6, 0.12),
    (T_INSIDE, HOUSE_X, 5.8, 0.12), (T_INSIDE + 1.5, HOUSE_X, 5.8, 0.10), (T_TITLE, 80.0, 4.5, 0.028), (T_END, 80.0, 4.5, 0.028),
]


def camera(t):
    for (t0, *a), (t1, *b) in zip(CAM, CAM[1:]):
        if t < t1:
            u = smooth((t - t0) / (t1 - t0))
            cx, cy = a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u
            S = math.exp(math.log(a[2]) + (math.log(b[2]) - math.log(a[2])) * u)
            return cx, cy, S
    return CAM[-1][1:]


# ---------------------------------------------------------------- render
def simulate():
    return {"nf": int(round(T_END * FPS))}


class Scene:
    def __init__(self, layout, sim):
        self.L, self.sim = layout, sim
        self.canvas = Canvas(layout.w, layout.h, studio.render_scale())

    def draw(self, f, rule):
        Lay, c = self.L, self.canvas
        w, h = Lay.w, Lay.h
        t = f * DT
        ctx = c.ctx
        cx, cy, Sf = camera(t)
        S = Sf * h
        if t < 4.6:                                                  # the hook camera follows the run
            cx = dot_state(t)[0] + 1.0
        X = lambda x: w / 2 + (x - cx) * S                          # noqa: E731
        Y = lambda y: h * 0.62 - (y - cy) * S                       # noqa: E731
        shake = 0.0
        if T_RUMBLE <= t < T_RUMBLE + 1.6 or T_POP <= t < T_POP + 0.4:
            shake = 6 * math.sin(t * 90)
        ctx.save()
        ctx.translate(shake, 0)
        g = cairo.LinearGradient(0, 0, 0, h)
        g.add_color_stop_rgb(0, 0.05, 0.05, 0.12)
        g.add_color_stop_rgb(1, 0.01, 0.01, 0.03)
        ctx.set_source(g)
        ctx.paint()
        for i in range(60):
            c.circle((i * 211.0 - cx * S * 0.05) % w, (i * 97.0) % h, 1.4, (0.9, 0.9, 1.0), alpha=0.3)

        def glyph(txt, x, y, size, col=WHITE, alpha=1.0, bold=True, rot=0.0):
            ctx.save()
            ctx.translate(X(x), Y(y))
            ctx.rotate(rot)
            ctx.select_font_face("Arial", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD if bold else cairo.FONT_WEIGHT_NORMAL)
            ctx.set_font_size(max(1.0, size * S))
            e = ctx.text_extents(txt)
            ctx.move_to(-e.width / 2 - e.x_bearing, 0)
            ctx.set_source_rgba(*col, alpha)
            ctx.show_text(txt)
            ctx.restore()

        def rock(x0, x1, ytop):
            ctx.rectangle(X(x0), Y(ytop), (x1 - x0) * S, h)
            ctx.set_source_rgb(0.08, 0.08, 0.15)
            ctx.fill()
            c.lines([(X(x0), Y(ytop), X(x1), Y(ytop))], (0.75, 0.78, 0.9), width=max(1.0, S * 0.03), alpha=0.7)

        rock(-60.0, 0.0, 0.0)                                         # start cliff
        rock(FAR_X0, WALL_X, 0.0)                                     # far cliff foot
        rock(WALL_X, LEDGE_X1, LEDGE_Y)                               # the wall + ledge
        rock(90.0, 104.0, 3.0)                                        # a far cliff (the ending teaser)
        glyph("∞ →", 96.0, 3.6, 1.6, GOLD, alpha=0.8 if t > T_INSIDE else 0.3)
        # signs
        self.sign(X, Y, S, glyph, -0.9, 0.0, "HOME → 100")
        self.sign(X, Y, S, glyph, WALL_X + 0.0, 1.0, "HOME ↑ 1,000", wall=True)
        self.house(X, Y, S, glyph, t)
        # the bridge
        zx = zero_pos(t)[0] if (zero_pos(t) and t < T_ZERO1 + 0.1) else (999 if t < T_ZERO0 else -999)
        if t < 4.6:
            zx = dot_state(t)[0] - 2.6
        if t < 4.6 or t >= T_BRIDGE:
            for k in range(10):
                x0 = k * 6.0
                if x0 + 6.0 < zx - 0.2 and t >= T_ZERO0 or (t < 4.6 and x0 + 6.0 < zx):
                    continue
                self.beam(X, Y, S, glyph, x0, 6.0, "10", 1.0)
            if T_BRIDGE <= t < T_RUN0 + 0.6:
                glyph("10 × 10 = 100", 30.0, 1.6, 2.2, GOLD, alpha=min(1.0, (t - T_BRIDGE) / 0.3) * (1 - smooth((t - T_RUN0) / 0.6)))
        elif t >= 17.0:
            n = planks_down(t)
            bund = smooth((t - T_BUNDLE) / 0.8) if t >= T_BUNDLE else 0.0
            if bund < 1.0:
                for i in range(n):
                    self.beam(X, Y, S, glyph, i * L, L, "1", 1 - bund)
                if n > 0 and t < T_BUNDLE:
                    s_ = " + ".join(["1"] * n) + f" = {n}"
                    glyph(s_, n * L / 2 + 0.6, 1.45, 0.24, GOLD, alpha=1 - bund)
            if bund > 0:
                self.beam(X, Y, S, glyph, 0.0, 6.0, "10", bund)
                glyph("1 + 1 + … + 1 = 10", 3.0, 1.45, 0.28, GOLD, alpha=bund * (1 - smooth((t - T_PUSH) / 0.4)))
            for k, tc in enumerate(T_COPY):                          # the beam multiplies across the gap
                if t >= tc:
                    a = min(1.0, (t - tc) / 0.15)
                    self.beam(X, Y, S, glyph, 6.0 * (k + 1), 6.0, "10", a)
            if t >= T_PUSH + 0.2:
                k = sum(1 for tc in T_COPY if t >= tc) + 1
                glyph(f"10 × {k} = {10 * k}", 3.0 + 3.0 * (k - 1), 2.2, 0.9, GOLD)
        # the pile of "1" planks (and the odd ÷)
        left = max(0, 14 - planks_down(t) - (1 if t >= T_TIRED else 0))
        for i in range(left):
            self.beam(X, Y, S, glyph, PILE_X - 1.1 - 0.05 * (i % 2), L, "1", 1.0, y=0.12 * i, small=True)
        if t < 15.3:
            glyph("÷", PILE_X - 0.8, 0.12 * left + 0.05, 0.3, GOLD)
        # the block / tower
        if t >= 13.6:
            lv = tower_level(t)
            top = PH * lv
            if top > 0.02:
                ctx.rectangle(X(BLOCK_X - 0.6), Y(top), 1.2 * S, top * S)
                ctx.set_source_rgb(0.16, 0.16, 0.28)
                ctx.fill()
                c.lines([(X(BLOCK_X - 0.6), Y(top), X(BLOCK_X + 0.6), Y(top))], GOLD, width=max(1.0, S * 0.05))
                k = max(1, int(round(lv)) if abs(lv - round(lv)) < 0.08 else int(lv))
                glyph(f"{10 ** k:,}", BLOCK_X, top - 0.5, 0.36 if k < 4 else 0.3, GOLD)
                if t >= T_STOMP[0]:
                    ex = "" if k == 1 else "²³⁴"[k - 2]
                    glyph(f"10{ex}", BLOCK_X - 1.3, top - 0.25, 0.42, WHITE)
            if T_DIV - 0.2 <= t < T_DIV + 1.6:
                glyph("10,000 ÷ 10 = 1,000", BLOCK_X + 1.0, PH * 4 + 1.6, 0.42, GOLD, alpha=min(1.0, (t - T_DIV + 0.2) / 0.3))
        # Zero
        if t < 4.6:
            self.zero(X, Y, S, glyph, dot_state(t)[0] - 2.6, 0.0, t, chomp=True)
        zp = zero_pos(t)
        if zp and t < T_POP:
            self.zero(X, Y, S, glyph, zp[0], zp[1], t, chomp=t < T_SWALLOW or t < T_SWALLOW + 0.5,
                      full=t >= T_SWALLOW + 0.4, glitch=max(0.0, (t - T_SWALLOW - 0.8) / 3.0) if t >= T_SWALLOW else 0.0)
            if T_ZERO0 + 0.5 <= t < T_ZERO1:
                glyph("100 × 0 = 0", zp[0] + 2.0, 2.2, 0.8, RED)
            if T_ZBLOCK - 0.2 <= t < T_ZWALL0 + 0.6:
                glyph("1,000 × 0 = 0", BLOCK_X, 3.4, 0.6, RED)
        if T_POP <= t < T_POP + 2.0:                                   # Zero pops into dust
            u = (t - T_POP) / 2.0
            ox, oy = LEDGE_X1 - 2.6, LEDGE_Y + 0.7
            for i in range(40):
                a = i * 2.4
                r = 0.2 + 2.2 * u ** 0.6 * (0.5 + 0.5 * ((i * 7) % 5) / 4)
                c.circle(X(ox + r * math.cos(a)), Y(oy + r * math.sin(a) - 1.2 * u * u), S * 0.05 * (1 - u),
                         RED if i % 3 else WHITE, alpha=1 - u)
        # Dot
        x, yf, face, pname, ex = dot_state(t)
        if not ex.get("hide"):
            pose = P_(pname, t)
            alpha_fade = ex.get("fade", 1.0)
            if alpha_fade < 1.0:
                ctx.push_group()
            hands, head = DA.draw_puppet(ctx, X, Y, S, x, yf, face, pose, ex.get("mouth", "smile"), ex.get("eyes", "open"),
                                         tremble=ex.get("trem", 0.0), t=t, airborne=ex.get("air", 0.0))
            self.props(X, Y, S, glyph, t, x, yf, face, hands, head, ex)
            if alpha_fade < 1.0:
                ctx.pop_group_to_source()
                ctx.paint_with_alpha(alpha_fade)
        ctx.restore()
        # overlays
        if 4.3 <= t < 6.2:
            a = 0.6 * (1 - smooth((t - 5.8) / 0.4))
            for i in range(14):
                yy = (i * 79 + t * 900) % h
                c.lines([(0, yy, w, yy)], (1, 1, 1), width=2, alpha=0.15 * a)
            c.text_centered("earlier…", h * 0.15, size=h * 0.06, color=GOLD, alpha=smooth((t - 4.7) / 0.3))
        elif 6.2 <= t < 7.4:
            c.text_centered("earlier…", h * 0.15, size=h * 0.06, color=GOLD, alpha=1 - smooth((t - 6.6) / 0.8))
        if 17.0 <= t < T_RUN0 + 1.0:
            n = 100 if t >= T_BRIDGE else (10 * (sum(1 for tc in T_COPY if t >= tc) + 1) if t >= T_PUSH + 0.2 else planks_down(t))
            c.text_centered(f"bridge: {n} / 100", h * 0.06, size=h * 0.042, color=(0.95, 0.95, 1.0), alpha=0.9, cx=w * 0.15)
        if t >= T_TITLE:
            a = smooth((t - T_TITLE) / 0.8)
            c.text_centered("Dot: The Way Home", h * 0.14, size=h * 0.08, color=GOLD, alpha=a)
            c.text_centered("to be continued…", h * 0.22, size=h * 0.045, color=WHITE, alpha=a, bold=False)
        c.watermark(Lay)

    # -------------------------------------------------------------- pieces
    def sign(self, X, Y, S, glyph, x, y, txt, wall=False):
        c = self.canvas
        ctx = c.ctx
        if not wall:
            c.lines([(X(x), Y(y), X(x), Y(y + 1.0))], (0.45, 0.32, 0.2), width=max(1.0, S * 0.05))
        bw, bh = 1.25, 0.32
        by = y + (0.95 if not wall else 0.0)
        ctx.rectangle(X(x - bw / 2), Y(by + bh), bw * S, bh * S)
        ctx.set_source_rgb(0.60, 0.42, 0.25)
        ctx.fill()
        glyph(txt, x, by + 0.08, 0.2, (1.0, 0.95, 0.8))

    def house(self, X, Y, S, glyph, t):
        c = self.canvas
        ctx = c.ctx
        x0, y0, wd, ht = HOUSE_X - 1.3, LEDGE_Y, 2.6, 2.0
        ctx.rectangle(X(x0), Y(y0 + ht), wd * S, ht * S)
        ctx.set_source_rgb(0.25, 0.22, 0.32)
        ctx.fill()
        ctx.move_to(X(x0 - 0.2), Y(y0 + ht))
        ctx.line_to(X(HOUSE_X), Y(y0 + ht + 1.1))
        ctx.line_to(X(x0 + wd + 0.2), Y(y0 + ht))
        ctx.close_path()
        ctx.set_source_rgb(0.55, 0.25, 0.22)
        ctx.fill()
        open_ = T_CLICK + 1.2 <= t < T_INSIDE + 0.6
        unlock = T_CLICK <= t
        ctx.rectangle(X(HOUSE_X - 0.35), Y(y0 + 1.3), 0.7 * S, 1.3 * S)
        ctx.set_source_rgb(*((0.95, 0.85, 0.5) if open_ else (0.45, 0.30, 0.20)))
        ctx.fill()
        if not unlock and t >= T_DOOR - 0.5:
            c.circle(X(HOUSE_X + 0.2), Y(y0 + 0.65), S * 0.06, (0.85, 0.85, 0.9))
        lit = t >= T_INSIDE + 0.4
        ctx.rectangle(X(HOUSE_X + 0.55), Y(y0 + 1.45), 0.5 * S, 0.5 * S)
        ctx.set_source_rgb(*((1.0, 0.85, 0.45) if lit else (0.95, 0.82, 0.45)))
        ctx.fill()
        if lit:                                                      # Dot waves in the window
            u = (t - T_INSIDE - 0.4)
            hx, hy = X(HOUSE_X + 0.8), Y(y0 + 1.25)
            c.circle(hx, hy - S * 0.05, S * 0.09, (0.05, 0.05, 0.1))
            ctx.new_path()
            ctx.arc(hx, hy - S * 0.05, S * 0.09, 0, 2 * math.pi)
            ctx.set_source_rgb(*BLUE)
            ctx.set_line_width(S * 0.03)
            ctx.stroke()
            ang = 0.4 * math.sin(u * 8)
            c.lines([(hx + S * 0.1, hy + S * 0.05, hx + S * (0.18 + 0.05 * ang), hy - S * 0.15)], BLUE, width=S * 0.03)

    def beam(self, X, Y, S, glyph, x0, length, label, alpha, y=0.0, small=False):
        c = self.canvas
        ctx = c.ctx
        th = 0.14
        ctx.rectangle(X(x0), Y(y + 0.0), length * S, th * S)
        ctx.set_source_rgba(0.62, 0.45, 0.28, alpha)
        ctx.fill()
        ctx.rectangle(X(x0), Y(y + 0.0), length * S, th * S)
        ctx.set_source_rgba(0.35, 0.22, 0.12, alpha)
        ctx.set_line_width(max(1.0, S * 0.012))
        ctx.stroke()
        if S * 0.12 > 4:
            glyph(label, x0 + length / 2, y - 0.105, 0.12 if small else 0.13, (0.25, 0.15, 0.05), alpha)

    def zero(self, X, Y, S, glyph, x, y, t, chomp=False, full=False, glitch=0.0):
        c = self.canvas
        ctx = c.ctx
        r = 0.6 * (1 + 0.6 * glitch)
        jx = (math.sin(t * 77) * 0.06 * glitch) if glitch else 0.0
        cxp, cyp = X(x + jx), Y(y + r * 1.15)
        col = RED if not glitch or int(t * 14) % 2 else WHITE
        ctx.new_path()
        ctx.save()
        ctx.translate(cxp, cyp)
        ctx.scale(0.8, 1.15)
        ctx.arc(0, 0, r * S, 0, 2 * math.pi)
        ctx.restore()
        ctx.set_source_rgb(*col)
        ctx.set_line_width(max(2.0, r * S * 0.38))
        ctx.stroke()
        bite = 0.5 + 0.5 * math.sin(t * 14) if chomp else 0.3
        ctx.new_path()
        ctx.save()
        ctx.translate(cxp, cyp + r * S * 0.2)
        ctx.scale(0.55, 0.25 + 0.55 * bite)
        ctx.arc(0, 0, r * S * 0.75, 0, 2 * math.pi)
        ctx.restore()
        ctx.set_source_rgb(0.02, 0.0, 0.02)
        ctx.fill()
        for s_ in (-1, 1):                                            # angry eyes
            ex_, ey_ = cxp + s_ * r * S * 0.28, cyp - r * S * 0.45
            c.circle(ex_, ey_, r * S * 0.11, (1, 1, 1))
            c.lines([(ex_ - s_ * r * S * 0.18, ey_ - r * S * 0.2, ex_ + s_ * r * S * 0.12, ey_ - r * S * 0.1)],
                    (0.15, 0.0, 0.0), width=max(1.0, r * S * 0.08))
        if full:
            glyph("1 ÷ 0", x, y + r * 1.0, 0.3, GOLD)
        if glitch > 0.15:
            for k, txt in enumerate(("ERROR", "undefined", "ERROR")):
                a = min(1.0, (glitch - 0.15 - 0.2 * k) * 3)
                if a > 0:
                    glyph(txt, x + (k - 1) * 1.6, y + 2.3 + 0.35 * k + 0.1 * math.sin(t * 30 + k), 0.38, RED if k != 1 else WHITE, a)

    def props(self, X, Y, S, glyph, t, x, yf, face, hands, head, ex):
        c = self.canvas
        ctx = c.ctx
        hf = hands["af"]
        if ex.get("plank"):
            ctx.rectangle(X(hf[0] - L / 2), Y(hf[1] + 0.12), L * S, 0.12 * S)
            ctx.set_source_rgb(0.62, 0.45, 0.28)
            ctx.fill()
        if ex.get("stick"):                                           # the spare "1" on his back
            sx, sy = x - face * 0.12, yf + 0.55 + ex.get("air", 0.0)
            c.lines([(X(sx - face * 0.15), Y(sy - 0.25), X(sx + face * 0.15), Y(sy + 0.5))], (0.62, 0.45, 0.28),
                    width=S * 0.06)
        if ex.get("div_hand"):
            glyph("÷", hf[0], hf[1] - 0.1, 0.35, GOLD)
        if ex.get("weapon"):                                          # "1 ÷" held out against Zero
            glyph("1 ÷", hf[0] + face * 0.55, hf[1] - 0.15, 0.55, GOLD)
        if ex.get("bulb"):
            bx, by = X(head[0]), Y(head[1] + 0.42)
            c.glow(bx, by, S * 0.12, GOLD, strength=0.9, reach=3)
            c.circle(bx, by, S * 0.1, (1.0, 0.92, 0.55))
        if ex.get("bang"):
            glyph("!", x, yf + 1.4, 0.45, GOLD)
        if ex.get("zz"):
            for k in range(3):
                ph = (t * 0.8 + k / 3) % 1.0
                glyph("z", x + 0.35 + ph * 0.5, 1.1 + ph * 0.7, 0.25 * (0.6 + ph), GOLD, 1 - ph, bold=False)
        if ex.get("sweat"):
            for k in range(2):
                ph = (t * 1.6 + k * 0.5) % 1.0
                c.circle(X(head[0] - face * 0.12), Y(head[1] + 0.05 - ph * 0.3), S * 0.03, (0.6, 0.8, 1.0), alpha=1 - ph)


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


# ---------------------------------------------------------------- sound (original)
def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def bed():
    n = int(round(T_END * SR))
    out = np.zeros(n + 3 * SR)
    rng = np.random.default_rng(41)

    def add(t0, sig, g=1.0):
        i0 = int(t0 * SR)
        if i0 < 0:
            return
        sig = sig[: max(0, len(out) - i0)]
        out[i0:i0 + len(sig)] += g * sig

    def tone(f, dur, decay, harm=((1, 1.0), (2, 0.3))):
        tv = np.arange(int(dur * SR)) / SR
        return sum(a * np.sin(2 * np.pi * f * k * tv) for k, a in harm) * np.exp(-tv / decay)

    def noise(dur, decay):
        tv = np.arange(int(dur * SR)) / SR
        return np.diff(np.concatenate([[0], rng.standard_normal(len(tv))])) * np.exp(-tv / decay)

    def pop(t0, m=76, g=0.10):
        tv = np.arange(int(0.09 * SR)) / SR
        add(t0, np.sin(2 * np.pi * np.cumsum(hz(m) * (1 + 1.5 * tv / 0.09)) / SR) * np.exp(-tv / 0.04), g)

    def ding(t0, base=84):
        for m in (base, base + 4, base + 7):
            add(t0, tone(hz(m), 1.2, 0.4, ((1, 1.0), (2.76, 0.25))), 0.06)

    def thud(t0, g=0.3):
        tv = np.arange(int(0.4 * SR)) / SR
        add(t0, np.sin(2 * np.pi * np.cumsum(55 + 70 * np.exp(-tv / 0.03)) / SR) * np.exp(-tv / 0.12), g)

    def chomp(t0, g=0.2):
        add(t0, tone(80, 0.15, 0.05, ((1, 1.0), (2.5, 0.6))) + 0.6 * noise(0.15, 0.03), g)

    beat = 0.5
    prog = [(45, (57, 60, 64)), (41, (57, 60, 65)), (48, (55, 60, 64)), (43, (55, 59, 62))]   # Am F C G
    tb, b = 6.5, 0
    while tb < T_END - 4:
        tense = T_RUMBLE <= tb < T_POP
        calm = tb < 17.0 or tb >= T_POP + 1.0
        root, ch = prog[b % 4]
        add(tb, tone(hz(root - (12 if tense else 0)), 1.0, 0.3), 0.09 if tense else 0.07)
        sub = 16 if tense else (8 if not calm else 4)
        for e in range(sub):
            m = ch[(e * 2) % 3] + (12 if e % 4 == 3 else 0)
            add(tb + e * 4 * beat / sub, tone(hz(m), 0.25, 0.07, ((1, 1.0), (2, 0.5), (3, 0.2))), 0.026)
        if tense:
            for q in range(4):
                add(tb + q * beat, tone(50, 0.25, 0.08), 0.2)
        tb += 4 * beat
        b += 1
    tb = 0.0                                                          # hook: a fast chase loop + chomps
    while tb < 4.4:
        add(tb, tone(hz(69 + (int(tb * 8) % 4) * 3), 0.12, 0.05), 0.05)
        if int(tb * 8) % 3 == 0:
            chomp(tb, 0.12)
        tb += 0.125
    add(4.4, noise(0.5, 0.2) * np.sin(np.linspace(0, 40, int(0.5 * SR))), 0.25)
    tv = np.arange(int(1.4 * SR)) / SR
    add(4.8, np.sin(2 * np.pi * np.cumsum(900 - 600 * tv / 1.4 + 200 * np.sin(2 * np.pi * 9 * tv)) / SR), 0.05)
    pop(8.0, 84)
    ding(12.4, 72)
    pop(15.3, 88)
    for p in PLANKS:                                                   # plank taps (slower and slower)
        thud(p["t_place"], 0.18)
        pop(p["t_place"] + 0.05, 72 + 2 * PLANKS.index(p), 0.07)
    add(T_TIRED, tone(150, 0.6, 0.3, ((1, 1.0), (2, 0.4))), 0.06)
    ding(T_BULB, 88)
    for k in range(10):
        pop(T_BUNDLE + 0.07 * k, 76 + k, 0.07)
    for k, tc in enumerate(T_COPY):
        thud(tc, 0.15)
        pop(tc, 72 + 2 * k, 0.09)
    ding(T_BRIDGE)
    for k in range(int((T_RUN1 - T_RUN0) / 0.18)):
        add(T_RUN0 + 0.18 * k, tone(90, 0.05, 0.02), 0.08)
    for i, ts in enumerate(T_STOMP):
        thud(ts, 0.3)
        tv = np.arange(int(0.6 * SR)) / SR
        add(ts, np.sin(2 * np.pi * np.cumsum(hz(55 + 7 * i) * (1 + tv / 0.6)) / SR) * np.sin(np.pi * tv / 0.6), 0.10)
        ding(ts + 0.6, 79 + 5 * i)
    pop(T_DIV - 0.8, 88)
    tv = np.arange(int(0.6 * SR)) / SR
    add(T_DIV, np.sin(2 * np.pi * np.cumsum(hz(84) * (1 - 0.5 * tv / 0.6)) / SR) * np.sin(np.pi * tv / 0.6), 0.08)
    ding(T_DIV + 0.6, 76)
    for k in range(4):                                                  # door rattle
        add(T_DOOR + 0.2 + 0.18 * k, tone(300, 0.08, 0.02, ((1, 1.0), (2.7, 0.5))), 0.12)
    tv = np.arange(int(2.0 * SR)) / SR
    add(T_RUMBLE, np.convolve(rng.standard_normal(len(tv)), np.ones(220) / 220, mode="same") * np.clip(tv / 0.3, 0, 1) *
        np.clip((2.0 - tv) / 0.5, 0, 1), 0.7)
    k = T_ZERO0
    while k < T_SWALLOW:                                                # Zero chomps its way through
        chomp(k, 0.14)
        k += 0.28
    thud(T_ZBLOCK, 0.4)
    pop(T_CORNER, 88)
    chomp(T_SWALLOW, 0.4)
    k = T_SWALLOW + 0.8                                                  # glitch bleeps
    while k < T_POP:
        add(k, tone(hz(84 + int(_r(k) * 12)), 0.06, 0.03, ((1, 1.0), (3, 0.5))), 0.08)
        k += 0.09
    add(T_POP, noise(0.8, 0.3), 0.35)
    thud(T_POP, 0.5)
    add(T_CLICK, tone(1800, 0.06, 0.02), 0.15)
    ding(T_CLICK + 0.1, 79)
    add(T_CLICK + 1.2, tone(220, 0.4, 0.2, ((1, 1.0), (1.5, 0.4))), 0.05)
    add(T_INSIDE, tone(120, 0.15, 0.05), 0.15)
    ding(T_TITLE, 72)
    return out[:n].astype(np.float32)


def _r(x):
    v = math.sin(x * 12.9898) * 43758.5453
    return v - math.floor(v)


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
    if kit.has("--times"):
        for k in ("T_TIRED", "T_BRIDGE", "T_RUN1", "T_DIV", "T_DOOR", "T_RUMBLE", "T_ZERO1", "T_SWALLOW", "T_POP",
                  "T_CLICK", "T_INSIDE", "T_TITLE"):
            print(k, round(globals()[k], 2))
        return
    if kit.has("--still"):
        layout = get_layout("horizontal")
        f = int(arg("--frame", "0"))
        png = studio.OUT_DIR / f"{SCENE}_{label}_f{f}.png"
        render(layout, sim, png, "", still_frame=f)
        print(png)
        return
    print(f"[{SCENE}] {T_END:.0f}s")
    _worker("horizontal", sim, label, "")


if __name__ == "__main__":
    main()
