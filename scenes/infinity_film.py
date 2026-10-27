"""THE STICKMAN WHO FIXED INFINITY — the full film (16:9 long-form, ~7:45, one continuous journey, no chapter cards).

Owner's 31-shot script (2026-10-18). One connected world the camera never cuts away from:
  origin (0,0) → the x-axis becomes the NUMBER LINE HIGHWAY (−3 … 100, shadow negatives, the "0" gap) → the FRACTION
  ROAD (1/2 + 1/4 + … = 1) → the "+" GATE → POLYNOMIAL MOUNTAINS (skate the parabola, flip, climb the cubic cliff past
  ∞ boulders, the turning point) → the TRIG OCEAN (π surfboard; sin x, 3 sin x, sin 3x; tan x spikes; the unit
  circle) → the FRACTAL LABYRINTH (Sierpinski walls, a true infinite zoom, glitch clones, the Koch snowflake) → the
  FIBONACCI TOWER (a real golden-spiral tiling 1…21, the spiral draws, F(n+1)/F(n) → 1.618) → all six φ shards → one
  golden leap back over the whole world to the origin → BOSS: Divide by Zero (UNDEFINED beams, slide on the x-axis,
  wall-run the y-axis, golden spiral punches, the black hole, the final spiral strike) → RESTORATION at (0,0).
Hero = the Dot-film puppet engine (orange + white edge + glow; a gold chest core that brightens with every shard).
Everything (picture + sound) is ours and synthesised; no samples.
    NF_FAST=1 NF_ORIENT=horizontal python scenes/infinity_film.py
"""
import math
import sys
from pathlib import Path

import cairo
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import audio, kit, studio  # noqa: E402
from lib.kit import DT, FPS, arg  # noqa: E402
from lib.layouts import get_layout  # noqa: E402
from lib.studio import Canvas, VideoWriter  # noqa: E402
import dot_adventure as DA  # noqa: E402

SCENE = "infinity_film"
T_END = 465.0
ORANGE, WHITE, GOLD, RED = (1.0, 0.55, 0.15), (1, 1, 1), (1.0, 0.82, 0.35), (1.0, 0.18, 0.22)
CYAN, BLUEW = (0.35, 0.85, 1.0), (0.25, 0.55, 1.0)
PHI = (1 + 5 ** 0.5) / 2
P = DA.POSES
GUARD = dict(lean=8, head=0, af=(55, 150), ab=(35, 150), lf=(22, 5), lb=(-22, -5))
PUNCH = dict(lean=14, head=-5, af=(92, 88), ab=(35, 150), lf=(28, 5), lb=(-28, -8))
LOOKUP = dict(lean=-6, head=-38, af=(12, 6), ab=(-12, -6), lf=(7, 2), lb=(-7, -2))
REACH = dict(lean=28, head=30, af=(75, 60), ab=(-10, -5), lf=(25, 5), lb=(-20, -10))
CHEST = dict(lean=0, head=25, af=(60, 150), ab=(-20, -10), lf=(7, 2), lb=(-7, -2))
SKATE = dict(lean=12, head=0, af=(70, 20), ab=(-60, -20), lf=(35, -30), lb=(-25, -35))
SLIDE = dict(lean=55, head=-20, af=(100, 20), ab=(-40, -20), lf=(70, 10), lb=(20, 30))
HANG = dict(lean=-80, head=-10, af=(175, 180), ab=(170, 180), lf=(10, 5), lb=(-10, -5))
POWER = dict(lean=-8, head=-20, af=(140, 160), ab=(-140, -160), lf=(15, 0), lb=(-15, 0))


def sm(u):
    u = min(1.0, max(0.0, u))
    return u * u * (3 - 2 * u)


def seg(t, a, b):
    return sm((t - a) / (b - a))


RNG = np.random.default_rng(7)

# ================================================================ the world
# --- origin: the Golden Spiral in the sky + the cracks of chapter 1
SP_C, SP_S = np.array([4.0, 9.0]), 0.09
_th = np.linspace(0, 4.2 * math.pi, 420)
SPIRAL = np.stack([SP_C[0] + SP_S * PHI ** (2 * _th / math.pi) * np.cos(_th),
                   SP_C[1] + SP_S * PHI ** (2 * _th / math.pi) * np.sin(_th)], 1)
SHARDS = []
for k in range(70):
    i0 = int(k / 70 * (len(SPIRAL) - 6))
    p0 = SPIRAL[i0:i0 + 6]
    mid = p0.mean(0)
    SHARDS.append((p0 - mid, mid, (mid - SP_C) * RNG.uniform(0.25, 0.6) + RNG.normal(0, 0.6, 2), RNG.uniform(-14, 14)))
T_SHATTER = 21.0
CRACKS = []
for k in range(9):
    x0 = 1.0 + RNG.uniform(-0.5, 5.5)
    pts, a = [(x0, 0.0)], RNG.uniform(-0.9, 0.9)
    for j in range(7):
        a += RNG.normal(0, 0.5)
        pts.append((pts[-1][0] + 0.35 * math.cos(a), max(-1.6, pts[-1][1] - 0.18 * abs(math.sin(a)) - 0.05)))
    CRACKS.append((RNG.uniform(31.0, 34.5), pts))
CREATURES = [("NaN", 2.2, 36.2, 45.7), ("ERROR", 3.4, 36.8, 46.8), ("NaN", 4.4, 37.5, 48.1), ("ERROR", 5.3, 38.1, 49.5),
             ("NaN", 6.4, 38.8, 50.9), ("ERR", 7.2, 39.3, 52.0)]
HITS1 = [(c[3], "punch" if i % 2 == 0 else "kick") for i, c in enumerate(CREATURES)]

# --- number line highway (on the x-axis): label n sits at x = 33 + 0.47 n; the "0" gap; then the fraction road
NL0, NLS = 33.0, 0.47
GAP = (NL0 - 0.6, NL0 + 0.6)
FR0, FR1 = 80.5, 96.5                                    # fraction road: 1/2 + 1/4 + … ends at "1"
GATE_X = 98.6

# --- polynomial mountains
PV, PA = 111.0, 0.08                                    # parabola y = 0.08 (x − 111)² − 5.12 on [103, 121]
CUB0 = 130.0                                            # cubic y = 1.2u − 0.002u³, u = x − 130, peak u = 14.14


def ground(x):
    if 103.0 <= x < 121.0:
        return PA * (x - PV) ** 2 - 5.12
    if CUB0 <= x < 154.5:
        u = x - CUB0
        return 1.2 * u - 0.002 * u ** 3
    return 0.0


PEAK = (CUB0 + math.sqrt(200.0), ground(CUB0 + math.sqrt(200.0)))

# --- trig ocean [154.5, 211]
SEA0, SEA1 = 154.5, 211.0
CIRC_C = 205.5


def wave_params(t):
    A, k, w = 0.45, 0.9, 1.6
    if t >= 197.0:
        A = 0.45 + 1.2 * seg(t, 197, 199) - 1.2 * seg(t, 203, 204.5)
    if t >= 203.5:
        k = 0.9 + 1.8 * seg(t, 203.5, 205) - 1.8 * seg(t, 209, 211)
        w = 1.6 + 2.6 * seg(t, 203.5, 205) - 2.6 * seg(t, 209, 211)
    if t >= 225.0:
        A *= 1 - 0.9 * seg(t, 225, 229)
    return A, k, w


def wave(x, t):
    A, k, w = wave_params(t)
    return A * math.sin(k * x - w * t)


TAN_SPIKES = [(212.0, 186.5), (214.5, 189.0), (217.0, 191.6), (219.2, 194.0), (221.4, 196.4)]   # (time, x)

# --- fractal labyrinth: Sierpinski triangle on [214, 246]; the Koch snowflake exit
SA, SB = np.array([214.0, 0.0]), np.array([246.0, 0.0])
SC = np.array([230.0, 32 * math.sqrt(3) / 2])
KOCH_C, KOCH_R = np.array([236.0, 3.4]), 2.8


def koch():
    pts = [KOCH_C + KOCH_R * np.array([math.cos(math.pi / 2 + 2 * math.pi * k / 3),
                                       math.sin(math.pi / 2 + 2 * math.pi * k / 3)]) for k in range(3)]
    pts = pts + [pts[0]]
    for _ in range(4):
        new = []
        for a, b in zip(pts, pts[1:]):
            d = (b - a) / 3
            p1, p2 = a + d, a + 2 * d
            rot = np.array([[0.5, math.sqrt(3) / 2], [-math.sqrt(3) / 2, 0.5]])
            new += [a, p1, p1 + rot @ d, p2]
        pts = new + [pts[-1]]
    return np.array(pts)


KOCH = koch()

# --- Fibonacci tower: the golden tiling 1…21 rotated upright, base at x ≈ 256
FIBS = [1, 1, 2, 3, 5, 8, 13, 21]
SQ0 = [(0, 0), (1, 0), (0, 1), (-3, 0), (-3, -5), (2, -5), (-3, 3), (-24, -5)]
ARCS = [((1, 1), 1, 180, 270), ((1, 1), 1, 270, 360), ((0, 1), 2, 0, 90), ((0, 0), 3, 90, 180),
        ((2, 0), 5, 180, 270), ((2, 3), 8, 270, 360), ((-3, 3), 13, 0, 90), ((-3, -5), 21, 90, 180)]
TX = 261.0


def tw(x, y):
    """Original tiling coords → world (rotated 90° clockwise so the 21-square sits on top)."""
    return TX + y, -x + 10.0


SQUARES = []
for (x0, y0), s in zip(SQ0, FIBS):
    corners = [tw(x0, y0), tw(x0 + s, y0), tw(x0 + s, y0 + s), tw(x0, y0 + s)]
    cx_ = sum(p[0] for p in corners) / 4
    cy_ = sum(p[1] for p in corners) / 4
    SQUARES.append((corners, (cx_, cy_), s))
SPIRAL_T = []
for (cxo, cyo), r, a0, a1 in ARCS:
    for a in np.linspace(math.radians(a0), math.radians(a1), 24):
        SPIRAL_T.append(tw(cxo + r * math.cos(a), cyo + r * math.sin(a)))
SPIRAL_T = np.array(SPIRAL_T)
TOWER_TOP = (SQUARES[7][1][0], 34.0)
JUMP_T = [315.6, 317.4, 319.2, 321.0, 322.8, 324.6, 326.5, 328.6]


# ================================================================ the hero's path
def keys_interp(t, keys):
    for (t0, v0), (t1, v1) in zip(keys, keys[1:]):
        if t0 <= t <= t1:
            return v0 + (v1 - v0) * sm((t - t0) / (t1 - t0))
    return keys[-1][1] if t > keys[-1][0] else keys[0][1]


def lin(t, keys):
    for (t0, v0), (t1, v1) in zip(keys, keys[1:]):
        if t0 <= t <= t1:
            return v0 + (v1 - v0) * (t - t0) / (t1 - t0)
    return keys[-1][1] if t > keys[-1][0] else keys[0][1]


def arc(t, t0, t1, p0, p1, h):
    u = min(1.0, max(0.0, (t - t0) / (t1 - t0)))
    return p0[0] + (p1[0] - p0[0]) * u, p0[1] + (p1[1] - p0[1]) * u + 4 * h * u * (1 - u)


def x_ch1(t):
    if t < 38.0:
        return 0.0
    if t < 41.0:
        return -1.2 * sm((t - 38.0) / 3.0)
    if t < 45.0:
        return -1.2
    if t < 52.4:
        k = sum(1 for th, _ in HITS1 if th <= t)
        return -1.2 + 0.55 * k + 0.25 * math.sin(math.pi * min(1, (t - 45) % 1.0))
    return 2.1


SHARD_T = [56.2, 112.0, 173.0, 233.0, 296.0, 349.0]     # when each φ shard is caught


def shards_held(t):
    return sum(1 for s in SHARD_T if t >= s)


def base(t):
    return dict(x=0.0, y=0.0, face=1, pose=P["stand"], airborne=0.0, rot=0.0, alpha=1.0, mouth="smile", eyes="open",
                run=False, scale=1.0, gold=0.0)


def hero_base(t):
    s = base(t)
    n = shards_held(t)
    s["core"] = [0.0, 0.25, 0.4, 0.55, 0.7, 0.85, 1.0][n]
    if t < 60.0:                                                  # ------- the origin
        s["x"] = x_ch1(t)
        if t < 10.5:
            s["alpha"] = 0.0
        elif t < 12.5:
            s["alpha"] = sm((t - 10.5) / 0.6)
            s["pose"] = DA.blend(P["crouch"], P["stand"], sm((t - 11.3) / 1.2))
            s["eyes"] = "closed" if t < 11.6 else "open"
        elif t < 15.0:
            s["face"] = -1 if 12.9 <= t < 13.9 else 1
        elif t < 30.0:
            s["pose"] = DA.blend(P["stand"], LOOKUP, seg(t, 15.5, 16.5))
            s["eyes"] = "wide" if t > T_SHATTER else "open"
            s["mouth"] = "open" if T_SHATTER <= t < 24 else "line"
        elif t < 38.0:
            s["pose"] = DA.blend(LOOKUP, P["stand"], seg(t, 30, 30.8))
            s["eyes"], s["mouth"] = ("wide" if t > 33 else "open"), "line"
        elif t < 41.0:
            s["pose"], s["eyes"], s["mouth"] = DA.cycle(t), "wide", "open"
        elif t < 45.0:
            s["pose"], s["mouth"] = DA.blend(P["stand"], GUARD, seg(t, 41.2, 41.7)), "line"
        elif t < 52.6:
            s["pose"] = GUARD
            for th, kind in HITS1:
                d = t - th
                if -0.18 <= d < 0.25:
                    k = 1 - abs(d) / 0.22 if d < 0 else 1 - d / 0.25
                    s["pose"] = DA.blend(GUARD, PUNCH if kind == "punch" else P["kick"], max(0.0, min(1.0, k)))
                    s["mouth"] = "open"
            if 50.2 <= t < 51.0:
                u = (t - 50.2) / 0.8
                s["airborne"], s["rot"], s["pose"] = 0.9 * math.sin(math.pi * u), -2 * math.pi * sm(u), P["jump"]
        elif t < 55.0:
            s["pose"] = DA.blend(GUARD, P["stand"], seg(t, 52.6, 53.2))
        elif t < 56.2:
            s["pose"] = DA.blend(P["stand"], REACH, seg(t, 55.0, 55.5))
        else:
            s["pose"] = DA.blend(REACH, CHEST, seg(t, 56.2, 56.8))
        return s
    if t < 105.0:                                                 # ------- the highway + the fraction road
        if t < 75.0:
            s["x"] = lin(t, [(60, 2.1), (61.5, 3.0), (75, 28.0)])
        elif t < 90.0:
            s["x"] = lin(t, [(75, 28.0), (90, 80.5)])
        else:
            u = (t - 90.0) / 1.9
            s["x"] = FR1 - (FR1 - FR0) * 0.5 ** u if t < 104.4 else FR1
        speed = 3.5 if 75 <= t < 90 else (1.8 if t < 75 else 0.6)
        s["pose"] = DA.cycle(t * (1.3 if speed > 3 else 1.0), run=t < 90)
        s["run"] = t < 90
        if 76.0 <= t < 77.2:                                     # the leap over the "0" gap
            u = (t - 76.0) / 1.2
            s["airborne"], s["pose"] = 1.3 * math.sin(math.pi * u), P["jump"]
        if t >= 104.4:
            s["pose"] = P["stand"]
        if 60 < t < 61.5:
            s["pose"] = DA.blend(CHEST, DA.cycle(t, run=True), seg(t, 60, 61.5))
        return s
    if t < 120.0:                                                 # ------- the "+" gate, shard 2
        s["x"] = keys_interp(t, [(105, FR1), (110, FR1), (111.5, GATE_X), (114, GATE_X), (119.5, 103.0)])
        if 110 <= t < 111.5 or 114 <= t < 119.5:
            s["pose"] = DA.cycle(t)
        if 111.5 <= t < 112.2:
            s["pose"] = REACH
        elif 112.2 <= t < 113.5:
            s["pose"] = CHEST
        return s
    if t < 180.0:                                                 # ------- the polynomial mountains
        if t < 136.0:
            s["x"] = 103.0
            s["pose"] = DA.blend(P["stand"], LOOKUP, seg(t, 121, 122)) if t < 128 else P["stand"]
        elif t < 140.8:                                          # skate down the parabola and up to the lip
            u = (t - 136.0) / 4.8
            s["x"] = 103.0 + 18.0 * (0.55 * u + 0.45 * u * u)
            s["y"] = ground(s["x"])
            s["pose"] = SKATE
            s["rot"] = -math.atan(2 * PA * (s["x"] - PV)) * 0.8
        elif t < 142.4:                                          # off the lip: a backflip through the air
            x, y = arc(t, 140.8, 142.4, (121.0, 2.88), (128.5, 0.0), 3.2)
            s["x"], s["y"], s["pose"] = x, y, P["jump"]
            s["rot"] = 2 * math.pi * sm((t - 140.8) / 1.6)
        elif t < 150.0:
            s["x"] = lin(t, [(142.4, 128.5), (144.5, 128.5), (150, CUB0 + 0.3)])
            s["pose"] = P["crouch"] if t < 143.0 else (P["stand"] if t < 144.5 else DA.cycle(t))
        elif t < 168.0:                                          # climb the cubic past the ∞ boulders
            s["x"] = lin(t, [(150, CUB0 + 0.3), (168, PEAK[0])])
            s["y"] = ground(s["x"])
            p = DA.cycle(t)
            p["lean"] = 25
            s["pose"] = p
            for tj in (152.6, 160.0):
                if tj <= t < tj + 0.9:
                    s["airborne"], s["pose"] = 1.1 * math.sin(math.pi * (t - tj) / 0.9), P["jump"]
            for tp in (156.3, 163.4):
                if tp - 0.2 <= t < tp + 0.3:
                    s["pose"] = PUNCH
        else:
            s["x"], s["y"] = PEAK
            if 172.2 <= t < 173.0:
                s["pose"] = REACH
            elif 173.0 <= t < 175.0:
                s["pose"] = CHEST
        if t >= 150.0 or t < 136.0:
            s["y"] = ground(s["x"])
        return s
    if t < 240.0:                                                 # ------- the trig ocean
        if t < 184.5:                                            # slide down the far side of the cubic
            s["x"] = lin(t, [(180, PEAK[0]), (181, PEAK[0]), (184.5, SEA0 - 0.3)])
            s["y"], s["pose"] = ground(s["x"]), (SLIDE if t > 181 else P["stand"])
            s["rot"] = 0.6 if t > 181 else 0.0
        elif t < 188.0:
            if t < 186.4:
                s["x"], s["y"] = SEA0 - 0.3, 0.0
            else:
                x, y = arc(t, 186.4, 188.0, (SEA0 - 0.3, 0.0), (157.5, wave(157.5, 188.0) + 0.25), 1.6)
                s["x"], s["y"], s["pose"] = x, y, P["jump"]
        else:
            if t < 225.0:
                s["x"] = lin(t, [(188, 157.5), (225, 200.0)])
            else:
                s["x"] = keys_interp(t, [(225, 200.0), (231.5, 202.0), (232.6, CIRC_C), (240, CIRC_C)])
            s["y"] = wave(s["x"], t) + 0.25
            s["pose"] = SKATE
            s["board"] = True
            for ts, xs in TAN_SPIKES:                            # weave between the tan spikes
                if ts - 0.5 <= t < ts + 0.5:
                    s["airborne"], s["pose"] = 1.2 * math.sin(math.pi * (t - ts + 0.5)), P["jump"]
            if 231.5 <= t < 232.6:
                x, y = arc(t, 231.5, 232.6, (202.0, 0.25), (CIRC_C, 0.25), 1.2)
                s["x"], s["y"], s["pose"], s["board"] = x, y, P["jump"], t < 231.6
            if t >= 232.6:
                s["board"] = False
                s["pose"] = REACH if t < 233.4 else (CHEST if t < 235 else P["stand"])
                s["y"] = 0.25
        return s
    if t < 300.0:                                                 # ------- the fractal labyrinth
        if t < 242.0:
            x, y = arc(t, 240.0, 242.0, (CIRC_C, 0.25), (212.0, 0.0), 2.5)
            s["x"], s["y"], s["pose"] = x, y, P["jump"]
        elif t < 270.0:
            s["x"] = lin(t, [(242, 212.0), (255, 215.4), (270, 215.4)])
            s["pose"] = DA.cycle(t) if t < 255 or t >= 255 else P["stand"]
        elif t < 285.0:
            s["x"] = lin(t, [(270, 215.4), (285, 222.0)])
            s["pose"] = GUARD
            for i, th in enumerate(CLONE_T):
                d = t - th
                if -0.15 <= d < 0.25:
                    s["pose"] = PUNCH if i % 3 != 1 else P["kick"]
                    s["face"] = 1 if i % 2 == 0 else -1
            if 279.0 <= t < 279.8:
                u = (t - 279.0) / 0.8
                s["airborne"], s["rot"], s["pose"] = 1.0 * math.sin(math.pi * u), 2 * math.pi * sm(u), P["jump"]
        else:
            s["x"] = keys_interp(t, [(285, 222.0), (293.5, KOCH_C[0] - 0.6), (300, KOCH_C[0] - 0.6)])
            s["pose"] = DA.cycle(t) if t < 293.5 else (REACH if 295.4 <= t < 296.2 else
                                                      (CHEST if 296.2 <= t < 298 else P["stand"]))
        return s
    if t < 360.0:                                                 # ------- the Fibonacci tower
        if t < 315.6:
            s["x"] = keys_interp(t, [(300, KOCH_C[0] - 0.6), (307, TX - 2.0), (315.6, TX - 2.0)])
            s["pose"] = DA.cycle(t, run=True) if t < 307 else DA.blend(P["stand"], LOOKUP, seg(t, 307.5, 308.5))
            s["run"] = t < 307
            if t >= 314.6:
                s["pose"] = P["crouch"]
        elif t < 343.0:
            spots = [(TX - 2.0, 0.0)] + [(sq[1][0], sq[1][1] - 0.45) for sq in SQUARES]
            k = max(i for i, tj in enumerate([0.0] + JUMP_T) if t >= tj)
            k = min(k, 8)
            if k < 8 and t < JUMP_T[k] + 0.0:
                pass
            # flying from spot k-1 to spot k during [JUMP_T[k-1] - 0.9, JUMP_T[k-1]]
            flying = False
            for i, tj in enumerate(JUMP_T):
                if tj - 0.9 <= t < tj:
                    x, y = arc(t, tj - 0.9, tj, spots[i], spots[i + 1], 1.5 + 0.15 * FIBS[i])
                    s["x"], s["y"], s["pose"] = x, y, P["jump"]
                    flying = True
            if not flying:
                j = sum(1 for tj in JUMP_T if t >= tj)
                s["x"], s["y"] = spots[j]
                s["pose"] = P["crouch"] if any(0 <= t - tj < 0.25 for tj in JUMP_T) else P["stand"]
            if t >= 336.0:
                s["pose"] = DA.blend(P["stand"], LOOKUP, seg(t, 336, 337))
        elif t < 345.0:
            x, y = arc(t, 343.0, 345.0, (SQUARES[7][1][0], SQUARES[7][1][1] - 0.45), TOWER_TOP, 2.0)
            s["x"], s["y"], s["pose"] = x, y, P["jump"]
        else:
            s["x"], s["y"] = TOWER_TOP
            s["pose"] = REACH if 348.3 <= t < 349.0 else (POWER if t >= 349.0 else P["stand"])
            s["gold"] = seg(t, 352.0, 355.0)
            s["mouth"] = "open" if 352 <= t < 356 else "smile"
        return s
    if t < 367.0:                                                 # ------- the golden leap home
        x, y = arc(t, 360.0, 367.0, TOWER_TOP, (0.0, 0.0), 30.0)
        s["x"], s["y"], s["pose"], s["gold"] = x, y, P["jump"], 1.0
        s["rot"] = -4 * math.pi * sm((t - 360) / 7.0)
        s["face"] = -1
        s["trail"] = True
        if t > 366.4:
            s["pose"] = P["crouch"]
        return s
    s["gold"] = 1.0 if t < 435 else 1.0 - seg(t, 450, 458) * 0.6
    if t < 375.0:                                                 # ------- BOSS: the sky splits
        s["x"], s["pose"] = 0.0, (P["crouch"] if t < 368 else DA.blend(LOOKUP, GUARD, seg(t, 372, 373.5)))
        s["mouth"] = "line"
        return s
    if t < 390.0:                                                 # beams: slide on the x-axis, wall-run the y-axis
        if t < 378.5:
            s["x"] = keys_interp(t, [(375, 0.0), (376, 0.0), (378.5, -6.0)])
            s["pose"] = SLIDE if t >= 376 else GUARD
            s["face"] = -1
        elif t < 380.0:
            s["x"] = lin(t, [(378.5, -6.0), (380.0, -0.35)])
            s["pose"], s["face"] = DA.cycle(t, run=True), 1
        elif t < 382.6:                                          # running UP the y-axis
            u = (t - 380.0) / 2.6
            s["x"], s["y"] = -0.35, 7.0 * u
            s["pose"], s["rot"] = DA.cycle(t, run=True), -math.pi / 2
            s["wall"] = True
        elif t < 384.4:
            x, y = arc(t, 382.6, 384.4, (-0.35, 7.0), (3.5, 0.0), 2.0)
            s["x"], s["y"], s["pose"] = x, y, P["jump"]
            s["rot"] = 2 * math.pi * sm((t - 382.6) / 1.8)
        else:
            s["x"] = keys_interp(t, [(384.4, 3.5), (386.5, 3.5), (387.5, 1.5), (390, 1.5)])
            s["pose"] = GUARD
            if 386.5 <= t < 387.5:
                s["pose"] = SLIDE
        return s
    if t < 405.0:                                                 # the counterattack: golden spiral punches
        bx, by = BOSS_POS
        if t < 392.5:
            x, y = arc(t, 390.0, 392.5, (1.5, 0.0), (bx - 2.6, by - 1.0), 2.0)
            s["x"], s["y"], s["pose"] = x, y, P["jump"]
        elif t < 403.0:
            s["x"], s["y"] = bx - 2.6 + 0.3 * math.sin(t * 2.0), by - 1.0 + 0.3 * math.sin(t * 1.3)
            s["pose"] = GUARD
            for th in COUNTER_T:
                if th - 0.15 <= t < th + 0.3:
                    s["pose"] = PUNCH
        else:
            x, y = arc(t, 403.0, 405.0, (bx - 2.6, by - 1.0), (-3.0, 0.0), 1.0)
            s["x"], s["y"], s["pose"] = x, y, P["jump"]
        s["fly"] = 392.5 <= t < 403.0
        return s
    if t < 420.0:                                                 # the black hole: hanging onto the x-axis
        s["x"], s["y"] = -3.0, 0.15
        s["pose"] = HANG
        s["rot"] = -0.35 - 0.25 * math.sin(t * 3.0) - 0.4 * seg(t, 405, 410)
        s["mouth"] = "open"
        s["eyes"] = "wide"
        return s
    if t < 435.0:                                                 # the final strike
        bx, by = BOSS_POS
        if t < 427.0:
            s["x"], s["y"] = -3.0, 0.15 + 2.5 * seg(t, 420, 423)
            s["pose"], s["fly"] = POWER, t >= 421
            s["gold"] = 1.0 + 1.5 * seg(t, 420, 422)
        elif t < 429.0:
            u = (t - 427.0) / 2.0
            s["x"], s["y"] = -3.0 + (bx + 5.0 + 3.0) * u, 2.65 + (by + 3.0 - 2.65) * u
            s["pose"], s["fly"], s["trail"] = PUNCH, True, True
            s["gold"] = 2.5
        else:
            s["x"], s["y"] = bx + 5.0, by + 3.0
            s["pose"], s["fly"], s["gold"] = POWER, True, 2.5 - 1.5 * seg(t, 429, 434)
        return s
    # ------------------------------------------------------------- restoration
    if t < 440.0:
        bx, by = BOSS_POS
        x, y = arc(t, 435.0, 440.0, (bx + 5.0, by + 3.0), (0.0, 0.0), 2.0)
        s["x"], s["y"], s["pose"], s["fly"] = x, y, (P["jump"] if t < 439.4 else P["crouch"]), True
        return s
    s["x"] = 0.0
    s["pose"] = P["stand"] if t < 446 else DA.blend(P["stand"], LOOKUP, seg(t, 446, 447.5))
    if t >= 455.0:
        s["face"] = -1 if 455.5 <= t < 456.4 else 1
        nod = math.sin(math.pi * seg(t, 457.0, 458.2)) * 30
        p = dict(P["stand"])
        p["head"] = nod
        s["pose"] = p
    return s


BOSS_POS = (4.0, 9.0)
CLONE_T = [271.2, 272.4, 273.3, 274.6, 275.8, 276.7, 277.9, 280.4, 281.5, 282.6, 283.6]
COUNTER_T = [393.6, 395.0, 396.2, 397.6, 398.8, 400.0, 401.4, 402.4]


# ================================================================ v2: motion, pacing, hit-stops (owner notes)
DODGE = dict(lean=-28, head=-15, af=(40, 120), ab=(30, 140), lf=(30, 10), lb=(-35, -10))
WINDUP = dict(lean=-6, head=0, af=(-50, 100), ab=(35, 150), lf=(25, 5), lb=(-25, -8))
TUCK = dict(lean=10, head=10, af=(60, 120), ab=(40, 120), lf=(95, -120), lb=(80, -120))
SURF_HI = dict(lean=8, head=-5, af=(75, 15), ab=(-65, -15), lf=(28, -12), lb=(-22, -18))
SURF_LO = dict(lean=22, head=10, af=(85, 30), ab=(-80, -30), lf=(60, -70), lb=(-10, -70))
BOULDERS = [(151.0, 152.6, "jump"), (154.3, 156.3, "punch"), (157.8, 160.0, "duck"), (161.5, 163.4, "punch")]


def jump_motion(t, t0, dur, h, air_pose=None):
    """Anticipation crouch → launch → flight → landing squash. Returns (active, airborne, pose)."""
    air_pose = air_pose or P["jump"]
    if t0 - 0.22 <= t < t0:
        return True, 0.0, DA.blend(P["stand"], P["crouch"], sm((t - (t0 - 0.22)) / 0.2))
    if t0 <= t < t0 + dur:
        u = (t - t0) / dur
        pose = DA.blend(P["crouch"], air_pose, sm(u / 0.25)) if u < 0.5 else DA.blend(air_pose, P["crouch"], sm((u - 0.75) / 0.25))
        return True, h * math.sin(math.pi * u), pose
    if t0 + dur <= t < t0 + dur + 0.25:
        return True, 0.0, DA.blend(P["crouch"], P["stand"], sm((t - t0 - dur) / 0.25))
    return False, 0.0, None


def boulder_state(t, tb, tp, kind):
    """An ∞ boulder rolling down the cubic: (x, y, spin, alive) — rolls faster and faster, bounces on the duck."""
    xh = hero_base(tp)["x"]
    x0 = PEAK[0] - 0.3
    xc = xh + (0.62 if kind == "punch" else 0.0)
    if t < tb:
        return None
    if t <= tp:
        u = (t - tb) / (tp - tb)
        x = x0 + (xc - x0) * u ** 1.6
    else:
        if kind == "punch":
            return None
        vend = 1.6 * (x0 - xc) / (tp - tb)
        x = xc - vend * (t - tp)
        if x < CUB0 - 3:
            return None
    y = ground(x) + 0.45
    if kind == "duck":
        y += 1.55 * math.sin(math.pi * min(1.0, max(0.0, (t - (tp - 0.45)) / 0.9)))
    else:
        y += 0.18 * abs(math.sin((x0 - x) * 2.2))                     # small bounces on the way down
    spin = (x0 - x) / 0.45
    return x, y, spin, True


def hero(t):
    s = hero_base(t)
    # the gap leap on the highway: a real jump
    on, air, pose = jump_motion(t, 75.85, 1.15, 1.35, TUCK)
    if on and 75.0 <= t < 78.0:
        s["airborne"], s["pose"] = air, pose
    # the ∞ boulders: jump one, duck one, smash two
    if 150.0 <= t < 168.0:
        for tb, tp, kind in BOULDERS:
            if kind == "jump":
                on, air, pose = jump_motion(t, tp - 0.42, 0.85, 1.35, TUCK)
                if on:
                    s["airborne"], s["pose"] = air, pose
            elif kind == "duck" and tp - 0.55 <= t < tp + 0.45:
                s["airborne"] = 0.0
                s["pose"] = DA.blend(P["crouch"], dict(P["crouch"], lean=40, head=30), sm((t - tp + 0.55) / 0.2))
                s["eyes"] = "wide"
            elif kind == "punch":
                if tp - 0.45 <= t < tp - 0.05:
                    s["airborne"], s["pose"] = 0.0, DA.blend(P["stand"], WINDUP, sm((t - tp + 0.45) / 0.3))
                elif tp - 0.05 <= t < tp + 0.3:
                    s["airborne"], s["pose"], s["mouth"] = 0.0, PUNCH, "open"
    # surfing: lean with the wave, carve, knees pump, arms balance, hop off crests
    if 188.0 <= t < 231.5:
        A, k, w = wave_params(t)
        x = s["x"] + 0.7 * math.sin(0.7 * (t - 188.0)) * min(1.0, (t - 188.0) / 1.5)
        y = wave(x, t)
        slope = A * k * math.cos(k * x - w * t)
        c_ = 0.5 - 0.5 * (y / max(A, 0.05))
        pose = DA.blend(SURF_HI, SURF_LO, max(0.0, min(1.0, c_)))
        pose["af"] = (pose["af"][0] + 18 * math.sin(t * 1.7), pose["af"][1] + 14 * math.sin(t * 2.3))
        pose["ab"] = (pose["ab"][0] + 14 * math.sin(t * 1.3 + 1), pose["ab"][1])
        s["x"], s["y"], s["pose"] = x, y + 0.25, pose
        s["rot"] = -math.atan(slope) * 0.85
        s["airborne"] = 0.0
        hop = None
        for ts, xs in TAN_SPIKES:
            if ts - 0.75 <= t < ts + 0.75:
                hop = (ts - 0.5, 1.0, 1.4)
        for th in (194.0, 201.0, 206.5):
            if th - 0.3 <= t < th + 1.0:
                hop = (th, 0.75, 0.6)
        if hop:
            on, air, pose = jump_motion(t, *hop, air_pose=TUCK)
            if on:
                s["airborne"] = air
                if air > 0.02:
                    s["pose"] = pose
                    if hop[2] > 1.0 and abs(hop[0] - 214.0) < 1.0:   # one full flip over a tan spike
                        s["rot"] = -2 * math.pi * sm((t - hop[0]) / hop[1])
        s["board"] = True
    # the labyrinth clones: they swing first on every other one; he dodges back, then counters
    if 270.0 <= t < 285.0:
        for i, th in enumerate(CLONE_T):
            if i % 2 == 1 and th - 0.55 <= t < th - 0.15:
                s["pose"], s["eyes"] = DODGE, "wide"
                s["face"] = -1 if i % 2 == 1 else 1
            if th - 0.3 <= t < th - 0.12 and not (i % 2 == 1 and t < th - 0.15):
                s["pose"] = WINDUP
    # landing squash after every tower jump
    if 315.0 <= t < 330.0:
        for tj in JUMP_T:
            if tj <= t < tj + 0.3:
                s["pose"] = DA.blend(P["crouch"], P["stand"], sm((t - tj) / 0.3))
    return s


# --- pacing: speed up slow parts, slow motion on near-misses, hit-stop freezes on impacts
SPEED_SEGS = [(16.0, 30.0, 1.15), (60.0, 75.0, 1.2), (90.0, 105.0, 1.2), (105.0, 120.0, 1.3), (120.0, 135.0, 2.5),
              (168.0, 180.0, 1.5), (180.0, 188.0, 1.2), (225.0, 240.0, 1.4), (240.0, 255.0, 1.8), (285.0, 300.0, 1.4),
              (300.0, 315.0, 1.6), (330.0, 345.0, 1.3), (345.0, 360.0, 1.2), (440.0, 455.0, 1.3),
              (377.2, 377.7, 0.35), (381.4, 381.9, 0.35), (427.0, 429.0, 0.45)]
HITSTOPS = ([h[0] for h in HITS1] + [156.3, 163.4] + CLONE_T + COUNTER_T + [428.5])


def _speed(t):
    for a, b, v in SPEED_SEGS:
        if a <= t < b:
            return v
    return 1.0


def _build_map():
    st, vt = [0.0], [0.0]
    stops = sorted(HITSTOPS)
    j = 0
    t, v, dt = 0.0, 0.0, 1 / 600
    while t < T_END:
        while j < len(stops) and stops[j] <= t:
            v += 0.075                                        # the freeze: video time runs, the story waits
            st.append(t)
            vt.append(v)
            j += 1
        t += dt
        v += dt / _speed(t)
        st.append(t)
        vt.append(v)
    return np.array(st), np.array(vt)


_ST, _VT = _build_map()
V_END = float(_VT[-1])


def story(f):
    """Video frame → story time."""
    return float(np.interp(f * DT, _VT, _ST))


def v_of(t):
    """Story time → video time (first occurrence)."""
    return float(np.interp(t, _ST, _VT))


def shake(t):
    """Camera shake (world units) after impacts."""
    a = 0.0
    for th in HITSTOPS:
        d = t - th
        if 0.0 <= d < 0.3:
            a += 0.07 * math.exp(-d / 0.08)
    return a


# ================================================================ camera
def cam_target(t, h):
    """(cx, cy, scale as a fraction of h per unit) — mostly tracking the hero, with authored shots."""
    s = hero(t)
    hx, hy = s["x"], s["y"]
    if t < 60.0:
        K = [(0.0, 0.0, 0.3, 0.030), (8.0, 0.0, 0.5, 0.060), (15.0, 0.0, 0.6, 0.22), (16.0, 0.3, 1.2, 0.20),
             (19.5, 2.6, 6.8, 0.085), (23.0, 2.6, 6.0, 0.075), (26.5, 1.8, 3.4, 0.070), (29.5, 1.6, 2.6, 0.080),
             (31.5, 1.8, 0.8, 0.17), (41.0, 1.4, 0.8, 0.18), (45.0, 1.8, 0.8, 0.19), (52.4, 2.6, 0.8, 0.19),
             (55.0, 1.8, 0.9, 0.20), (56.4, 1.2, 0.8, 0.26), (59.0, 2.1, 0.75, 0.55), (60.0, 2.6, 0.9, 0.3)]
        for (t0, x0, y0, s0), (t1, x1, y1, s1) in zip(K, K[1:]):
            if t0 <= t <= t1:
                u = sm((t - t0) / (t1 - t0))
                return x0 + (x1 - x0) * u, y0 + (y1 - y0) * u, math.exp(math.log(s0) + (math.log(s1) - math.log(s0)) * u)
    if t < 90.0:
        return hx + 2.0, 1.0, 0.16 if t < 75 else 0.13
    if t < 105.0:
        z = min(5.0, (t - 90.0) / 1.9)
        return hx + 1.5 / (1 + 0.3 * z), 0.8, 0.13 * (1 + 0.45 * z)
    if t < 120.0:
        return hx + 1.0, 1.4 if t < 112 else 1.2, 0.17
    if t < 135.0:
        return 116.0 + 4.0 * seg(t, 125, 134), 3.5, 0.045       # wide establishing shot of the mountains
    if t < 150.0:
        return hx + 2.0, hy + 1.0, 0.11
    if t < 168.0:
        return hx + 1.0, hy + 1.8, 0.13
    if t < 180.0:
        a = (t - 168.0) / 12.0 * 2 * math.pi                    # orbit: a slow circle around the peak
        return PEAK[0] + 1.2 * math.sin(a), PEAK[1] + 0.9 + 0.5 * math.cos(a), 0.16 + 0.03 * math.sin(a)
    if t < 188.0:
        return hx + 3.0, hy + 1.5, 0.09
    if t < 225.0:
        return hx + 2.5, 1.4, 0.10 if t < 210 else 0.09
    if t < 240.0:
        return CIRC_C - 1.0, 2.6, 0.075 + 0.02 * seg(t, 226, 232)
    if t < 255.0:
        return hx + 3.0 + 3.0 * seg(t, 244, 252), 2.0 + 4.0 * seg(t, 244, 252), 0.12 - 0.05 * seg(t, 244, 252)
    if t < 270.0:                                                # the infinite zoom (self-similar about SA)
        z = 6.0 * (t - 255.0) / 15.0
        r = np.array([hx, 0.9]) - SA
        c = SA + r / 2 ** z
        return c[0], c[1], 0.10 * 2 ** z
    if t < 285.0:
        return hx + 0.5, 1.6, 0.13
    if t < 300.0:
        return hx + 1.5, 2.6, 0.10
    if t < 315.0:
        return hx + 2.0 + 3.0 * seg(t, 307, 312), 1.5 + 15.0 * seg(t, 308, 314), 0.12 - 0.08 * seg(t, 308, 314)
    if t < 330.0:
        return hx + 1.5, hy + 1.5, 0.07
    if t < 345.0:
        return TX + 4.5, 17.0 + 4.0 * seg(t, 340, 345), 0.035
    if t < 360.0:
        return hx, hy + 1.0, 0.11 + 0.06 * seg(t, 349, 355)
    if t < 367.0:                                                # the leap: pull out over the whole world
        u = (t - 360.0) / 7.0
        zoom = 0.11 * math.exp(-4.2 * math.sin(math.pi * u))
        return hx, hy * 0.8 + 1.0, max(0.0028, zoom)
    if t < 375.0:
        return 1.5, 4.0 + 1.5 * seg(t, 368, 372), 0.08 - 0.02 * seg(t, 368, 372)
    if t < 390.0:
        return 0.5 + 0.4 * hx, 3.2 + 0.4 * hy, 0.075
    if t < 405.0:
        return 0.5 * hx + 2.0, 0.5 * hy + 4.0, 0.07
    if t < 420.0:
        return 0.5, 4.0, 0.065
    if t < 435.0:
        if t < 427.0:
            return 0.5, 4.0, 0.065
        if t < 429.0:
            return hx, hy, 0.09
        return 2.0, 6.0, 0.065 - 0.035 * seg(t, 429, 434)
    if t < 446.0:
        return 2.0 - 1.0 * seg(t, 436, 446), 5.0, 0.04 + 0.02 * seg(t, 438, 446)
    return 0.3, 1.2 + 3.0 * (1 - seg(t, 446, 452)) - 0.0, 0.06 + 0.16 * seg(t, 452, 462)


_CAM_CACHE = {}


def camera(f, h):
    """Smoothed camera: an exponential follow over the authored target (forward-filled, cached per frame)."""
    if f in _CAM_CACHE:
        return _CAM_CACHE[f]
    t = story(f)
    tx, ty, ts = cam_target(t, h)
    if f == 0 or (f - 1) not in _CAM_CACHE:
        _CAM_CACHE[f] = (tx, ty, ts)
        return _CAM_CACHE[f]
    px, py, ps = _CAM_CACHE[f - 1]
    hard = t < 60.0 or 255.0 <= t < 270.0 or 360.0 <= t < 367.0
    a = 1.0 if hard else 0.12
    v = (px + (tx - px) * a, py + (ty - py) * a, math.exp(math.log(ps) + (math.log(ts) - math.log(ps)) * a))
    _CAM_CACHE[f] = v
    return v


# ================================================================ drawing
def simulate():
    return {"nf": int(round(float(arg("--len", str(V_END))) * FPS)), "f0": int(round(float(arg("--from", "0")) * FPS))}


class Scene:
    def __init__(self, layout, sim):
        self.L, self.sim = layout, sim
        self.canvas = Canvas(layout.w, layout.h, studio.render_scale())

    def X(self, x):
        return self.L.w / 2 + (x - self.cx) * self.S

    def Y(self, y):
        return self.L.h * 0.55 - (y - self.cy) * self.S

    def vis(self, x0, x1, margin=2.0):
        half = self.L.w / 2 / self.S
        return x1 >= self.cx - half - margin and x0 <= self.cx + half + margin

    def gtext(self, s, x, y, size, col, a=1.0, glitch=0.0, t=0.0):
        c = self.canvas
        if a <= 0.01:
            return
        if glitch > 0:
            j = glitch * size * 0.06
            c.text_centered(s, y + j * math.sin(t * 53), size=size, color=(1, 0.1, 0.2), alpha=0.6 * a,
                            cx=x - j * (1 + math.sin(t * 37)))
            c.text_centered(s, y - j * math.sin(t * 41), size=size, color=(0.2, 0.9, 1.0), alpha=0.5 * a,
                            cx=x + j * (1 + math.cos(t * 29)))
        c.text_centered(s, y, size=size, color=col, alpha=a, cx=x)

    def burst(self, x, y, age, col, n=14, life=0.6, spread=1.6):
        c = self.canvas
        if age < 0 or age > life:
            return
        for k in range(n):
            a = k / n * 2 * math.pi + 0.3
            r = 0.2 + spread * age
            px, py = x + r * math.cos(a), y + r * math.sin(a) * 0.8 - 1.5 * age * age
            c.circle(self.X(px), self.Y(py), self.S * 0.05 * (1 - age / life) + 1, col, alpha=1 - age / life)

    def shard(self, x, y, a=1.0, label=None, la=1.0):
        c = self.canvas
        X, Y = self.X, self.Y
        c.glow(X(x), Y(y), self.S * 0.4, GOLD, strength=0.9 * a, reach=2.4)
        c.poly([(X(x), Y(y + 0.18)), (X(x + 0.1), Y(y)), (X(x), Y(y - 0.18)), (X(x - 0.1), Y(y))], (1, 0.9, 0.5), alpha=a)
        if label:
            self.gtext(label, X(x), Y(y + 0.42), self.S * 0.22, GOLD, a=la * a)

    # ---------------------------------------------------------------- the grid (+ melting / black-hole warp)
    def grid(self, t):
        c, w, h = self.canvas, self.L.w, self.L.h
        a = sm(t / 2.0)
        half_w, half_h = w / 2 / self.S + 1, h / self.S + 1
        x0, x1 = self.cx - half_w, self.cx + half_w
        y0, y1 = self.cy - half_h, self.cy + half_h
        px_per = self.S
        step = 1 if px_per > 14 else (5 if px_per > 3 else 25)
        warp = 0.0
        if 405.0 <= t < 421.0:
            warp = seg(t, 405, 409) * (1 - seg(t, 419.5, 421))
        melt = seg(t, 368, 372) * (1 - seg(t, 437, 445)) if t >= 368 else 0.0
        red = melt * 0.6
        col = (0.25 + 0.5 * red, 0.32 - 0.1 * red, 0.6 - 0.4 * red)
        lines_s, lines_w = [], []
        bx, by = BOSS_POS
        for gx in range(int(math.floor(x0 / step) * step), int(x1) + 1, step):
            if warp > 0 or melt > 0:
                pts = []
                for yy in np.linspace(y0, y1, 40):
                    px_, py_ = gx, yy
                    if melt > 0:
                        px_ += melt * 0.12 * math.sin(yy * 1.3 + t * 2 + gx)
                    if warp > 0:
                        dx, dy = bx - px_, by - py_
                        d = math.hypot(dx, dy) + 0.5
                        k_ = warp * min(0.85, 6.0 / d)
                        ang = warp * 1.4 / d
                        px_, py_ = px_ + dx * k_ * 0.5, py_ + dy * k_ * 0.5
                        cs, sn = math.cos(ang), math.sin(ang)
                        px_, py_ = bx + (px_ - bx) * cs - (py_ - by) * sn, by + (px_ - bx) * sn + (py_ - by) * cs
                    pts.append((self.X(px_), self.Y(py_)))
                lines_w.append(pts)
            else:
                lines_s.append((self.X(gx), 0, self.X(gx), h))
        for gy in range(int(math.floor(y0 / step) * step), int(y1) + 1, step):
            if warp > 0 or melt > 0:
                pts = []
                for xx in np.linspace(x0, x1, 60):
                    px_, py_ = xx, gy
                    if melt > 0:
                        py_ += melt * 0.12 * math.sin(xx * 1.1 + t * 2.3 + gy)
                    if warp > 0:
                        dx, dy = bx - px_, by - py_
                        d = math.hypot(dx, dy) + 0.5
                        k_ = warp * min(0.85, 6.0 / d)
                        ang = warp * 1.4 / d
                        px_, py_ = px_ + dx * k_ * 0.5, py_ + dy * k_ * 0.5
                        cs, sn = math.cos(ang), math.sin(ang)
                        px_, py_ = bx + (px_ - bx) * cs - (py_ - by) * sn, by + (px_ - bx) * sn + (py_ - by) * cs
                    pts.append((self.X(px_), self.Y(py_)))
                lines_w.append(pts)
            else:
                lines_s.append((0, self.Y(gy), w, self.Y(gy)))
        if lines_s:
            c.lines(lines_s, col, width=1.2, alpha=0.32 * a)
        if lines_w:
            c.polylines(lines_w, col, width=1.2, alpha=0.32 * a)
        # the axes (draw themselves at the start; the x-axis is also the highway)
        L = 400 * sm((t - 2.0) / 4.0) if t < 6.0 else 400
        if L > 0.01:
            ax = [(self.X(-L), self.Y(0), self.X(min(L, 103.0)), self.Y(0)), (self.X(0), self.Y(-L), self.X(0), self.Y(L))]
            if t < 6.0:
                ax = [(self.X(-L), self.Y(0), self.X(L), self.Y(0)), (self.X(0), self.Y(-L), self.X(0), self.Y(L))]
            c.lines(ax, WHITE, width=7, alpha=0.18)
            c.lines(ax, WHITE, width=2.5, alpha=0.9)
            if t >= 6.0 and self.vis(SEA1, 400):
                c.lines([(self.X(SEA1), self.Y(0), self.X(400), self.Y(0))], WHITE, width=2.5, alpha=0.9)
            if t >= 6.0 and self.vis(121, SEA0):
                c.lines([(self.X(121), self.Y(0), self.X(CUB0), self.Y(0))], WHITE, width=2.5, alpha=0.9)

    def cracks(self, t):
        c = self.canvas
        heal = seg(t, 437, 445)
        for t0, pts in CRACKS:
            if t < t0:
                continue
            n = min(len(pts), 1 + int((t - t0) / 0.25))
            n = max(0, int(round(n * (1 - heal))))
            sp = [(self.X(x), self.Y(y)) for x, y in pts[:n]]
            if len(sp) > 1:
                c.polylines([sp], RED, width=10, alpha=0.18)
                c.polylines([sp], (1.0, 0.35, 0.35), width=3, alpha=0.95)

    # ---------------------------------------------------------------- characters
    def creature(self, lab, x, y, t, scale=1.0):
        c, ctx = self.canvas, self.canvas.ctx
        X, Y, S = self.X, self.Y, self.S * scale
        jit = 0.03 * math.sin(t * 47 + x * 9)
        bw, bh = (0.32 + 0.06 * len(lab)) * scale, 0.42 * scale
        for k in range(4):
            lx = x - bw / 2 + 0.1 * scale + k * (bw - 0.2 * scale) / 3
            ph = math.sin(t * 22 + k * 1.7) * 0.06 * scale
            c.lines([(X(lx), Y(y + 0.12 * scale), X(lx + ph - 0.05 * scale), Y(y))], RED, width=S * 0.03)
        ctx.new_path()
        ctx.rectangle(X(x - bw / 2 + jit), Y(y + 0.12 * scale + bh), bw * self.S, bh * self.S)
        ctx.set_source_rgba(0.12, 0.02, 0.03, 0.95)
        ctx.fill_preserve()
        ctx.set_source_rgba(*RED, 0.95)
        ctx.set_line_width(S * 0.025)
        ctx.stroke()
        c.glow(X(x), Y(y + 0.3 * scale), S * 0.5, RED, strength=0.35, reach=2)
        self.gtext(lab, X(x + jit), Y(y + 0.22 * scale), S * 0.2, (1, 0.85, 0.85), glitch=1.0, t=t)

    def boss(self, t, cx, cy, scale, alpha, crack=0.0):
        c = self.canvas
        rng = np.random.default_rng(int(t * 12))
        n = 26
        pts = []
        for k in range(n):
            a = 2 * math.pi * k / n
            r = scale * (1.0 + 0.35 * ((k % 2) * 0.8 + rng.uniform(-0.2, 0.25)))
            pts.append((self.X(cx + r * math.cos(a)), self.Y(cy + r * math.sin(a) * 0.8)))
        for dx, col, al in ((-6, (1, 0.1, 0.2), 0.5), (6, (0.2, 0.9, 1), 0.35)):
            c.poly([(x + dx, y) for x, y in pts], col, alpha=al * alpha)
        c.poly(pts, (0.02, 0.0, 0.01), alpha=alpha)
        c.polylines([pts + [pts[0]]], RED, width=4, alpha=alpha)
        if crack > 0:                                            # white cracks from the golden hits
            r2 = np.random.default_rng(5)
            segs = []
            for k in range(int(12 * crack)):
                a = r2.uniform(0, 2 * math.pi)
                p0 = (cx + 0.2 * math.cos(a) * scale, cy + 0.2 * math.sin(a) * scale)
                p1 = (cx + scale * 1.1 * math.cos(a + r2.uniform(-0.2, 0.2)), cy + scale * 0.9 * math.sin(a))
                segs.append((self.X(p0[0]), self.Y(p0[1]), self.X(p1[0]), self.Y(p1[1])))
            c.lines(segs, WHITE, width=3, alpha=alpha)
        self.gtext("÷0", self.X(cx), self.Y(cy - 0.25 * scale), self.S * scale * 0.9, WHITE, a=alpha, glitch=1.5, t=t)

    def draw_hero(self, s, t, X=None, Y=None, S=None, alpha=1.0, col=ORANGE, edge=WHITE):
        c, ctx = self.canvas, self.canvas.ctx
        X, Y, S = X or self.X, Y or self.Y, S or self.S
        a = s["alpha"] * alpha
        if a <= 0.01 or S < 1.2:
            return
        px, py = X(s["x"]), Y(s["y"] + 0.55 + s["airborne"])
        gold = s.get("gold", 0.0)
        body = tuple(ORANGE[i] + (GOLD[i] - ORANGE[i]) * min(1.0, gold) for i in range(3)) if col == ORANGE else col
        ctx.save()
        if s["rot"]:
            ctx.translate(px, py)
            ctx.rotate(s["rot"])
            ctx.translate(-px, -py)
        c.glow(px, py, S * (0.55 + 0.25 * min(gold, 2.0)), body, strength=(0.2 + 0.25 * min(gold, 2.5)) * a, reach=2.0)
        ctx.push_group()
        DA.draw_puppet(ctx, X, Y, S * 1.35, s["x"], s["y"], s["face"], s["pose"], mouth=s["mouth"], eyes=s["eyes"],
                       col=edge, t=t, airborne=s["airborne"])
        DA.draw_puppet(ctx, X, Y, S, s["x"], s["y"], s["face"], s["pose"], mouth=s["mouth"], eyes=s["eyes"],
                       col=body, t=t, airborne=s["airborne"])
        ctx.pop_group_to_source()
        ctx.paint_with_alpha(a)
        core = s.get("core", 0.0)
        if core > 0 and col == ORANGE:
            hip = DA.leg_drop(s["pose"]) + s["airborne"]
            cyw = s["y"] + hip + DA.TO * 0.75
            c.glow(X(s["x"]), Y(cyw), S * (0.25 + 0.2 * core), GOLD, strength=0.9 * min(1.0, core * 1.5) * a, reach=2.5)
            c.circle(X(s["x"]), Y(cyw), S * 0.05, (1, 0.95, 0.7), alpha=min(1.0, core * 3) * a)
        ctx.restore()

    # ---------------------------------------------------------------- the lands
    def land_highway(self, t):
        c = self.canvas
        X, Y = self.X, self.Y
        if not self.vis(NL0 - 3 * NLS - 2, FR1 + 2):
            return
        hx = hero(t)["x"]
        ticks, labels = [], []
        for n in range(-3, 101):
            x = NL0 + NLS * n
            if not self.vis(x, x, 1):
                continue
            lit = hx >= x - 0.3
            ticks.append((X(x), Y(0) - 8, X(x), Y(0) + 8))
            if self.S > 25:
                labels.append((str(n), x, lit))
        c.lines(ticks, WHITE, width=2, alpha=0.7)
        for lab, x, lit in labels:
            col = GOLD if lit else (0.6, 0.65, 0.85)
            c.text_centered(lab, Y(0) + self.S * 0.32, size=self.S * 0.18, color=col, alpha=1.0 if lit else 0.55, cx=X(x))
            if lit:
                c.glow(X(x), Y(0), self.S * 0.12, GOLD, strength=0.4, reach=2)
        # the "0" gap in the road
        if self.vis(*GAP):
            c.ctx.rectangle(X(GAP[0]), Y(0) - 6, (GAP[1] - GAP[0]) * self.S, 12)
            c.ctx.set_source_rgb(0, 0, 0)
            c.ctx.fill()
            self.gtext("0", X(NL0), Y(0.9), self.S * 0.7, RED, a=0.9, glitch=0.6, t=t)
        # the fraction road: 1/2, 1/4, 1/8 … ending at "1"
        if self.vis(FR0, FR1):
            x, L, k = FR0, (FR1 - FR0) / 2, 1
            col_cycle = [CYAN, GOLD, ORANGE, (0.6, 1, 0.6)]
            while L > 0.004:
                c.lines([(X(x), Y(0) - 10, X(x + L), Y(0) - 10)], col_cycle[k % 4], width=9, alpha=0.9)
                c.lines([(X(x), Y(0) - 18, X(x), Y(0) + 4)], WHITE, width=2, alpha=0.8)
                if L * self.S > 40:
                    c.text_centered(f"1/{2 ** k}", Y(0) + self.S * 0.35, size=min(self.S * 0.22, L * self.S * 0.4),
                                    color=col_cycle[k % 4], cx=X(x + L / 2))
                x += L
                L /= 2
                k += 1
            self.gtext("1", X(FR1), Y(0.9), self.S * 0.5, GOLD, a=1.0)
        # the "+" gate
        if self.vis(GATE_X - 2, GATE_X + 2):
            op = seg(t, 106.0, 109.0)
            g = 0.2
            for sgn in ():
                dy = sgn * op * 2.2
                c.poly([(X(GATE_X - g), Y(2.0 + dy + 1.2)), (X(GATE_X + g), Y(2.0 + dy + 1.2)),
                        (X(GATE_X + g), Y(2.0 + dy - 1.2 if sgn > 0 else 2.0 + dy)), (X(GATE_X - g), Y(2.0 + dy - 1.2 if sgn > 0 else 2.0 + dy))]
                       if False else [(X(GATE_X - g), Y(2.0 + dy * 1.0 + (1.6 if sgn > 0 else -0.0))),
                                      (X(GATE_X + g), Y(2.0 + dy * 1.0 + (1.6 if sgn > 0 else -0.0))),
                                      (X(GATE_X + g), Y(2.0 + dy * 1.0 + (0.0 if sgn > 0 else -1.6 + 1.6))),
                                      (X(GATE_X - g), Y(2.0 + dy * 1.0 + (0.0 if sgn > 0 else 0.0)))],
                       GOLD, alpha=0.0)
            # vertical bar (splits up/down) + horizontal bar (splits left/right)
            for sgn in (1, -1):
                y0 = 2.0 + sgn * (0.25 + op * 1.6)
                y1 = 2.0 + sgn * (1.25 + op * 1.6)
                c.poly([(X(GATE_X - g), Y(y0)), (X(GATE_X + g), Y(y0)), (X(GATE_X + g), Y(y1)), (X(GATE_X - g), Y(y1))],
                       GOLD, alpha=0.45)
                x0 = GATE_X + sgn * (0.25 + op * 1.6)
                x1 = GATE_X + sgn * (1.25 + op * 1.6)
                c.poly([(X(x0), Y(2.0 - g)), (X(x1), Y(2.0 - g)), (X(x1), Y(2.0 + g)), (X(x0), Y(2.0 + g))], GOLD, alpha=0.45)
            c.glow(X(GATE_X), Y(2.0), self.S * 1.2, GOLD, strength=0.25 + 0.3 * op, reach=2)

    def land_mountains(self, t):
        c = self.canvas
        X, Y = self.X, self.Y
        if not self.vis(100.0, SEA0 + 2):
            return
        xs = np.linspace(103, 121, 90)
        par = [(X(x), Y(ground(x))) for x in xs]
        xs2 = np.linspace(CUB0, SEA0, 120)
        cub = [(X(x), Y(ground(x))) for x in xs2]
        for pts, col in ((par, CYAN), (cub, (0.8, 0.5, 1.0))):
            c.polylines([pts], col, width=14, alpha=0.18)
            c.polylines([pts], col, width=4, alpha=0.95)
        c.lines([(X(121), Y(2.88), X(121), Y(0))], CYAN, width=3, alpha=0.6)
        if self.S > 6:
            c.text_centered("y = x²", Y(-6.2), size=self.S * 0.6, color=CYAN, cx=X(PV))
            c.text_centered("y = −x³ + 3x", Y(7.0), size=self.S * 0.55, color=(0.8, 0.5, 1.0), cx=X(CUB0 + 1.5))
        if 165.0 <= t < 182.0:                                   # the turning point
            a = seg(t, 166, 167.5)
            c.lines([(X(PEAK[0] - 2.5), Y(PEAK[1]), X(PEAK[0] + 2.5), Y(PEAK[1]))], GOLD, width=3, alpha=0.8 * a)
            c.glow(X(PEAK[0]), Y(PEAK[1]), self.S * 0.6, GOLD, strength=0.8 * a, reach=2.4)
            self.gtext("turning point: y' = 0", X(PEAK[0]), Y(PEAK[1] - 1.0), self.S * 0.3, GOLD, a=a)
        # ∞ boulders rolling down the cubic (momentum, spin, bounces); smashed ones split into tumbling pieces
        for tb, tp, kind in BOULDERS:
            st = boulder_state(t, tb, tp, kind)
            if st:
                bx_, by_, spin, _ = st
                c.glow(X(bx_), Y(by_), self.S * 0.55, RED, strength=0.45, reach=2)
                ctx = c.ctx
                ctx.save()
                ctx.translate(X(bx_), Y(by_))
                ctx.rotate(spin)
                self.gtext("∞", 0, self.S * 0.32, self.S * 0.95, RED, a=1.0, glitch=0.4, t=t)
                ctx.restore()
            elif kind == "punch" and tp <= t < tp + 1.2:
                a_ = t - tp
                xh = hero_base(tp)["x"] + 0.62
                y0 = ground(xh) + 0.45
                for k, (vx, vy, sp) in enumerate(((2.6, 4.2, 8.0), (1.4, 5.5, -11.0), (3.4, 2.4, 14.0))):
                    px_, py_ = xh + vx * a_, y0 + vy * a_ - 4.9 * a_ * a_
                    fade = 1 - a_ / 1.2
                    ctx = c.ctx
                    ctx.save()
                    ctx.translate(X(px_), Y(py_))
                    ctx.rotate(sp * a_)
                    ctx.new_path()
                    ctx.arc(0, 0, self.S * 0.16, 0.3 * k, 0.3 * k + math.pi * 1.2)
                    ctx.set_source_rgba(1.0, 0.3, 0.3, fade)
                    ctx.set_line_width(self.S * 0.07)
                    ctx.stroke()
                    ctx.restore()
                self.burst(xh, y0, a_, (1, 0.5, 0.4), n=10, life=0.5, spread=1.2)

    def land_ocean(self, t):
        c, ctx = self.canvas, self.canvas.ctx
        X, Y = self.X, self.Y
        if not self.vis(SEA0, SEA1):
            return
        x0, x1 = max(SEA0, self.cx - self.L.w / self.S), min(SEA1, self.cx + self.L.w / self.S)
        xs = np.linspace(x0, x1, 260)
        pts = [(X(x), Y(wave(x, t))) for x in xs]
        ctx.new_path()
        ctx.move_to(pts[0][0], self.L.h)
        for p in pts:
            ctx.line_to(*p)
        ctx.line_to(pts[-1][0], self.L.h)
        ctx.close_path()
        g = cairo.LinearGradient(0, Y(1.0), 0, self.L.h)
        g.add_color_stop_rgba(0, 0.05, 0.25, 0.6, 0.55)
        g.add_color_stop_rgba(1, 0.0, 0.03, 0.1, 0.9)
        ctx.set_source(g)
        ctx.fill()
        c.polylines([pts], CYAN, width=12, alpha=0.2)
        c.polylines([pts], (0.6, 0.9, 1.0), width=3.5, alpha=0.95)
        A, k, w = wave_params(t)
        lab = "y = sin x"
        if 197 <= t < 204:
            lab = "y = 3 sin x"
        elif 204 <= t < 210:
            lab = "y = sin 3x"
        elif 210 <= t < 225:
            lab = "y = tan x"
        elif t >= 225:
            lab = "x² + y² = 1"
        if 182 < t < 240:
            self.gtext(lab, self.L.w * 0.5, self.L.h * 0.13, self.L.w * 0.04, RED if "tan" in lab else CYAN, a=1.0,
                       glitch=0.8 if "tan" in lab else 0.0, t=t)
        for ts, xs_ in TAN_SPIKES:                               # tan x: spikes shooting up at the asymptotes
            if ts - 1.2 <= t < ts + 1.0:
                u = sm((t - ts + 1.2) / 0.5) * (1 - sm((t - ts - 0.6) / 0.4))
                for dx in (-1.6, 1.6):
                    xx = xs_ + dx * 0.5
                    c.lines([(X(xx), Y(0), X(xx), Y(12 * u))], RED, width=10, alpha=0.25 * u)
                    c.lines([(X(xx), Y(0), X(xx), Y(12 * u))], (1, 0.5, 0.5), width=3, alpha=0.9 * u)
        if t >= 225.0:                                           # the calm sea becomes the unit circle (seen from above)
            a = seg(t, 225.5, 228)
            R = 2.6
            ctx.new_path()                                       # (text leaves a current point behind)
            ctx.save()
            ctx.translate(X(CIRC_C), Y(0.3))
            ctx.scale(1, 0.35)
            ctx.arc(0, 0, R * self.S, 0, 2 * math.pi)
            ctx.restore()
            ctx.set_source_rgba(*GOLD, 0.9 * a)
            ctx.set_line_width(4)
            ctx.stroke()
            ang = (t - 225) * 1.5
            c.lines([(X(CIRC_C), Y(0.3), X(CIRC_C + R * math.cos(ang)), Y(0.3 + 0.35 * R * math.sin(ang)))], WHITE,
                    width=3, alpha=a)

    def land_labyrinth(self, t, zoomed=False):
        c = self.canvas
        X, Y = self.X, self.Y
        if not self.vis(SA[0] - 1, SB[0] + 1):
            return
        tris = [(SA, SB, SC)]
        segs = []
        min_px = 10.0
        for _ in range(12):
            new = []
            for a, b, cc in tris:
                L = np.linalg.norm(b - a) * self.S
                if L < min_px:
                    continue
                segs += [(X(a[0]), Y(a[1]), X(b[0]), Y(b[1])), (X(b[0]), Y(b[1]), X(cc[0]), Y(cc[1])),
                         (X(cc[0]), Y(cc[1]), X(a[0]), Y(a[1]))]
                ab, bc, ca = (a + b) / 2, (b + cc) / 2, (cc + a) / 2
                for tri in ((a, ab, ca), (ab, b, bc), (ca, bc, cc)):
                    pts = np.array(tri)
                    xmin, xmax = pts[:, 0].min(), pts[:, 0].max()
                    ymin, ymax = pts[:, 1].min(), pts[:, 1].max()
                    sx0, sx1 = X(xmin), X(xmax)
                    sy0, sy1 = Y(ymax), Y(ymin)
                    if sx1 < 0 or sx0 > self.L.w or sy1 < 0 or sy0 > self.L.h:
                        continue
                    new.append(tri)
            tris = new
            if not tris or len(segs) > 9000:
                break
        if segs:
            c.lines(segs, (0.75, 0.45, 1.0), width=7, alpha=0.15)
            c.lines(segs, (0.85, 0.65, 1.0), width=2, alpha=0.8)
        if self.vis(KOCH_C[0] - 4, KOCH_C[0] + 4) and t >= 284.0:
            a = seg(t, 284, 287)
            pts = [(X(p[0]), Y(p[1])) for p in KOCH]
            c.polylines([pts], CYAN, width=12, alpha=0.2 * a)
            c.polylines([pts], (0.7, 0.95, 1.0), width=3, alpha=0.95 * a)

    def land_tower(self, t):
        c = self.canvas
        X, Y = self.X, self.Y
        if not self.vis(TX - 6, TX + 17):
            return
        for i, (corners, (qx, qy), sz) in enumerate(SQUARES):
            lit = i < sum(1 for tj in JUMP_T if t >= tj) or t >= 343
            pop = 0.0
            if i < len(JUMP_T):
                pop = math.exp(-max(0.0, t - JUMP_T[i]) / 0.3) if t >= JUMP_T[i] else 0.0
            pts = [(X(x), Y(y)) for x, y in corners]
            c.poly(pts, GOLD if lit else (0.25, 0.3, 0.55), alpha=0.25 if lit else 0.15)
            c.polylines([pts + [pts[0]]], GOLD if lit else (0.55, 0.6, 0.9), width=3 + 4 * pop, alpha=0.95)
            if lit and sz * self.S > 18:
                c.text_centered(str(sz), Y(qy) + sz * self.S * 0.12, size=min(sz * self.S * 0.4, self.S * 3),
                                color=GOLD, alpha=0.9, cx=X(qx))
        if t >= 330.0:                                           # the golden spiral draws itself
            n = int(len(SPIRAL_T) * seg(t, 330, 338))
            if n > 1:
                pts = [(X(x), Y(y)) for x, y in SPIRAL_T[:n]]
                c.polylines([pts], GOLD, width=16, alpha=0.2)
                c.polylines([pts], (1, 0.95, 0.7), width=5, alpha=1.0)
        if 335.0 <= t < 346.0:
            k = min(len(FIBS) - 1, 1 + int((t - 335.0) / 1.2))
            fs = [1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377, 610, 987]
            j = min(len(fs) - 2, k + int(max(0.0, t - 340) * 1.6))
            r = fs[j + 1] / fs[j]
            a = seg(t, 335, 336) * (1 - seg(t, 345, 346))
            self.gtext(f"F(n+1)/F(n) = {fs[j + 1]}/{fs[j]} = {r:.4f}", self.L.w * 0.5, self.L.h * 0.13, self.L.w * 0.035,
                       GOLD, a=a)

    # ---------------------------------------------------------------- the frame
    def draw(self, f, rule):
        L, c = self.L, self.canvas
        w, h = L.w, L.h
        t = story(f)
        ctx = c.ctx
        ctx.set_source_rgb(0, 0, 0)
        ctx.paint()
        self.cx, self.cy, sf = camera(f, h)
        self.S = sf * h
        sk = shake(t)
        if sk:
            self.cx += sk * math.sin(t * 157.0) / max(sf * 6, 0.3)
            self.cy += sk * math.cos(t * 131.0) / max(sf * 6, 0.3)
        spin = 0.0
        if 405.0 <= t < 421.0:                                   # the vortex: the whole view slowly spins
            spin = 0.25 * math.sin((t - 405) * 0.6) * seg(t, 405, 408) * (1 - seg(t, 419, 421))
        ctx.save()
        if spin:
            ctx.translate(w / 2, h / 2)
            ctx.rotate(spin)
            ctx.translate(-w / 2, -h / 2)
        X, Y = self.X, self.Y
        s = hero(t)
        self.grid(t)
        self.cracks(t)
        self.land_highway(t)
        self.land_mountains(t)
        self.land_labyrinth(t)
        self.land_ocean(t)
        self.land_tower(t)
        # --- the origin dot + title
        if t < 11.0:
            beat = max(math.exp(-((t - tb) / 0.12) ** 2) for tb in (1.0, 2.6, 4.2, 5.8, 7.4, 9.0))
            a = sm(t / 0.6) * (1 - sm((t - 10.4) / 0.6))
            c.glow(X(0), Y(0), self.S * (0.4 + 0.5 * beat), ORANGE, strength=(0.5 + 0.5 * beat) * a, reach=2.5)
            if t >= 8.0:
                c.lines([(X(0), Y(0), X(0), Y(1.15 * sm((t - 8.0) / 2.4)))], ORANGE, width=self.S * 0.08, alpha=a)
            c.circle(X(0), Y(0), self.S * 0.08 * (1 + 0.4 * beat), (1, 0.85, 0.6), alpha=a)
        if 3.0 < t < 9.0:
            a = sm((t - 3.0) / 1.0) * (1 - sm((t - 8.0) / 1.0))
            self.gtext("THE STICKMAN WHO FIXED INFINITY", w / 2, h * 0.2, w * 0.034, GOLD, a=a)
        # --- the Golden Spiral: shattered at the start, rebuilt at the end
        if 14.0 < t < 31.0:
            if t < T_SHATTER:
                a = sm((t - 14.0) / 2.0)
                pts = [(X(x), Y(y)) for x, y in SPIRAL]
                c.polylines([pts], GOLD, width=14, alpha=0.2 * a)
                c.polylines([pts], (1, 0.92, 0.6), width=4, alpha=0.95 * a)
            else:
                dt_ = t - T_SHATTER
                for off, mid, v, spin_ in SHARDS:
                    pos = mid + v * dt_ + np.array([0, -3.0 * dt_ * dt_])
                    pos[1] = max(pos[1], 0.05)
                    ang = spin_ * dt_
                    rot = np.array([[math.cos(ang), -math.sin(ang)], [math.sin(ang), math.cos(ang)]])
                    pp = [(X(p[0]), Y(p[1])) for p in (off @ rot.T + pos)]
                    fade = 1.0 - sm((t - 28.0) / 2.5)
                    c.polylines([pp], (1, 0.92, 0.6), width=3, alpha=0.95 * fade)
        if t >= 440.0:                                           # rebuilt from the particles
            u = seg(t, 440, 452)
            for off, mid, v, spin_ in SHARDS:
                fall = mid + v * 3.0 + np.array([0, -27.0])
                fall[1] = max(fall[1], 0.05)
                pos = fall + (mid - fall) * u
                ang = spin_ * 3.0 * (1 - u)
                rot = np.array([[math.cos(ang), -math.sin(ang)], [math.sin(ang), math.cos(ang)]])
                pp = [(X(p[0]), Y(p[1])) for p in (off @ rot.T + pos)]
                c.polylines([pp], (1, 0.92, 0.6), width=3 + 2 * u, alpha=0.95)
            if u >= 1.0:
                pts = [(X(x), Y(y)) for x, y in SPIRAL]
                c.polylines([pts], GOLD, width=14, alpha=0.25)
                c.polylines([pts], (1, 0.92, 0.6), width=4, alpha=1.0)
        # --- Divide by Zero
        if 18.5 < t < 31.0:
            u = sm((t - 18.5) / 2.8)
            self.boss(t, 13.0 + (SP_C[0] - 2.5 - 13.0) * u, 11.0 - 1.5 * u, 1.6,
                      sm((t - 18.5) / 0.6) * (1 - sm((t - 29.8) / 1.0)))
        if 22.5 < t < 29.8:
            self.gtext("DIVIDE BY ZERO", w / 2, h * 0.22, w * 0.06, RED, a=sm((t - 22.5) / 0.4) * (1 - sm((t - 29) / 0.8)),
                       glitch=2.0, t=t)
        if 368.0 <= t < 429.0:
            bx, by = BOSS_POS
            if t < 372.0:                                       # the sky splits open
                u = seg(t, 368, 371)
                c.lines([(X(bx - 6 * u), Y(by + 2), X(bx + 6 * u), Y(by + 2.5))], RED, width=6 + 10 * u, alpha=0.8)
            crack = len([1 for th in COUNTER_T if t >= th]) / len(COUNTER_T)
            sc = 3.2 * seg(t, 369.5, 373) * (1 + 0.05 * math.sin(t * 7))
            self.boss(t, bx, by, max(0.05, sc), seg(t, 369.5, 371), crack=crack)
            if 405.0 <= t < 421.0:                              # the black hole at its heart
                a = seg(t, 405, 407) * (1 - seg(t, 419.5, 421))
                c.circle(X(bx), Y(by), self.S * 2.2 * a, (0, 0, 0))
                c.ring(X(bx), Y(by), self.S * 2.3 * a, RED, width=5, alpha=a)
                for k in range(40):
                    ang = k * 2.4 + t * (2.5 + k % 3)
                    r = (k * 0.37 + t * 3) % 9 + 2.3
                    c.circle(X(bx + r * math.cos(ang)), Y(by + r * math.sin(ang)), 3, (1, 0.6, 0.5), alpha=0.6 * a)
        if 429.0 <= t < 433.0:                                  # the boss shatters into white particles
            bx, by = BOSS_POS
            age = t - 429.0
            for k in range(90):
                ang = k * 2.399
                r = (0.5 + (k % 7) * 0.35) * (1 + 6 * age)
                c.circle(X(bx + r * math.cos(ang)), Y(by + r * math.sin(ang) - 2 * age * age), 4 * (1 - age / 4), WHITE,
                         alpha=1 - age / 4)
        # --- UNDEFINED beams
        if 375.5 <= t < 390.0:
            bx, by = BOSS_POS
            for k, tb in enumerate((376.0, 377.4, 378.6, 380.6, 381.6, 382.4, 385.6, 386.9, 388.2)):
                u = (t - tb) / 1.1
                if 0 <= u < 1:
                    tgt = hero(tb + 0.9)
                    ex, ey = tgt["x"] + (0.8 if k % 2 else -0.8), tgt["y"] + 0.8
                    px_, py_ = bx + (ex - bx) * u, by + (ey - by) * u
                    c.lines([(X(bx), Y(by), X(px_), Y(py_))], RED, width=6, alpha=0.35)
                    self.gtext("UNDEFINED", X(px_), Y(py_), self.S * 0.75, (1, 0.8, 0.8), a=1.0, glitch=1.0, t=t)
        # --- creatures (origin), shadow negatives (highway), glitch clones (labyrinth)
        for i, (lab, x0, te, tk) in enumerate(CREATURES):
            if te <= t < tk:
                rise = sm((t - te) / 0.8)
                hx = x_ch1(min(t, tk))
                contact = hx + 0.75
                if t < tk - 0.5:
                    u = sm((t - te) / max(0.1, (tk - 0.5 - te)))
                    x = x0 + (max(contact, x0 - 2.2) - x0) * u * (1 if t > 41 else 0.35)
                    y = -0.45 + 0.45 * rise
                else:                                            # it lunges at him
                    u = (t - (tk - 0.5)) / 0.5
                    x = contact + 0.6 * (1 - u)
                    y = 0.55 * math.sin(math.pi * min(1.0, u * 1.1))
                self.creature(lab, x, y, t)
            elif tk <= t < tk + 0.55:                            # knocked flying, spinning
                a_ = t - tk
                kx, ky = x_ch1(tk) + 0.75 + 3.2 * a_, 0.4 + 3.6 * a_ - 6.5 * a_ * a_
                ctx.save()
                ctx.translate(X(kx), Y(ky + 0.3))
                ctx.rotate(9.0 * a_)
                ctx.translate(-X(kx), -Y(ky + 0.3))
                self.creature(lab, kx, ky, t)
                ctx.restore()
            elif tk + 0.55 <= t < tk + 1.15:
                self.burst(x_ch1(tk) + 0.75 + 1.76, 0.3, t - tk - 0.55, (1, 0.6, 0.4))
        if 75.0 <= t < 90.0:
            for k, lab in enumerate(("−1", "−2", "−3")):
                rise = seg(t, 75.2 + 0.5 * k, 76.4 + 0.5 * k)
                lag = 2.6 + 1.3 * k + 0.6 * math.sin(t * 2 + k)
                sx = hero(t - 0.25 * k)["x"] - lag
                shadow = dict(base(t), x=sx, pose=DA.cycle(t + 0.2 * k, run=True))
                shadow["alpha"] = rise * (1 - seg(t, 87.5, 89.5))
                self.draw_hero(shadow, t, col=(0.12, 0.12, 0.2), edge=(0.6, 0.6, 0.85))
                self.gtext(lab, X(sx), Y(1.6), self.S * 0.28, (0.7, 0.7, 0.95), a=shadow["alpha"])
        if 270.0 <= t < 285.0:
            for i, th in enumerate(CLONE_T):
                side = 1 if i % 2 == 0 else -1
                if th - 1.4 <= t < th:
                    u = (t - (th - 1.4)) / 1.4
                    hx = hero(th)["x"]
                    cx_ = hx + side * (0.85 + 2.5 * (1 - u) ** 1.5)
                    pose = DA.cycle(t, run=True) if u < 0.6 else (WINDUP if u < 0.78 else PUNCH)
                    clone = dict(base(t), x=cx_, face=-side, pose=pose)
                    self.draw_hero(clone, t, col=RED, edge=(0.3, 0.0, 0.0))
                elif th <= t < th + 0.5:                         # knocked back, spinning
                    a_ = t - th
                    hx = hero(th)["x"]
                    clone = dict(base(t), x=hx + side * (0.85 + 3.0 * a_), y=0.0, face=-side, pose=P["jump"],
                                 airborne=2.6 * a_ - 4.5 * a_ * a_, rot=side * 10 * a_, alpha=1 - 0.5 * a_ / 0.5)
                    self.draw_hero(clone, t, col=RED, edge=(0.3, 0.0, 0.0))
                elif th + 0.5 <= t < th + 1.1:
                    self.burst(hero(th)["x"] + side * 2.35, 0.6, t - th - 0.5, RED)
        # --- the hero (+ infinite-zoom copies, spiral trails)
        if 255.0 <= t < 270.0:
            z = 6.0 * (t - 255.0) / 15.0
            for k in range(1, 10):
                if abs(k - z) > 1.2:
                    continue
                sc = 0.5 ** k
                Xk = lambda x, k=k: X(SA[0] + (x - SA[0]) * 0.5 ** k)       # noqa: E731
                Yk = lambda y, k=k: Y(SA[1] + (y - SA[1]) * 0.5 ** k)       # noqa: E731
                self.draw_hero(s, t, X=Xk, Y=Yk, S=self.S * sc)
        if s.get("trail"):
            for k in range(1, 18):
                sp = hero(t - k * 0.03)
                c.circle(X(sp["x"]), Y(sp["y"] + 0.6), self.S * 0.12 * (1 - k / 18), GOLD, alpha=0.7 * (1 - k / 18))
        if 392.5 <= t < 403.0:                                  # golden spiral trails from each punch
            for th in COUNTER_T:
                u = (t - th) / 0.7
                if 0 <= u < 1:
                    bx, by = BOSS_POS
                    pts = []
                    for j in range(40):
                        a = j / 40 * 3 * math.pi * min(1.0, u * 1.5)
                        r = 0.05 * PHI ** (2 * a / math.pi)
                        pts.append((X(bx - 1.2 + r * math.cos(a + th)), Y(by - 0.5 + r * math.sin(a + th))))
                    c.polylines([pts], GOLD, width=5, alpha=1 - u)
                    c.glow(X(bx - 1.2), Y(by - 0.5), self.S * 0.8, GOLD, strength=0.8 * (1 - u), reach=2)
        if 421.5 <= t < 429.0:                                   # he draws a huge golden spiral in the air
            n = int(300 * seg(t, 422, 426))
            bx, by = BOSS_POS
            pts = []
            for j in range(n):
                a = j / 300 * 4.2 * math.pi
                r = 0.08 * PHI ** (2 * a / math.pi)
                pts.append((X(bx + r * math.cos(-a)), Y(by + r * math.sin(-a))))
            if len(pts) > 1:
                c.polylines([pts], GOLD, width=18, alpha=0.25)
                c.polylines([pts], (1, 0.95, 0.7), width=5, alpha=1.0 - seg(t, 428.5, 429))
        if s.get("run") and s["airborne"] < 0.05:              # dust puffs at his heels
            for k in range(6):
                age = ((t * 4.2) + k / 6) % 1.0
                c.circle(X(s["x"] - 0.25 - 1.3 * age), Y(s["y"] + 0.08 + 0.25 * age), self.S * (0.06 + 0.16 * age),
                         (0.75, 0.72, 0.8), alpha=0.35 * (1 - age))
        if 75.0 <= t < 90.0 or 300.0 <= t < 307.0:                # speed lines when he sprints
            for k in range(7):
                yy = s["y"] + 0.25 + k * 0.17
                off = ((t * 9 + k * 0.37) % 1.0)
                c.lines([(X(s["x"] - 0.6 - 2.2 * off), Y(yy), X(s["x"] - 1.3 - 2.2 * off), Y(yy))], WHITE, width=2,
                        alpha=0.35 * (1 - off))
        if s.get("board"):                                      # the π surfboard tilts with the wave; spray off the tail
            bx_, by_ = s["x"], s["y"] + s["airborne"] - 0.08
            ctx.save()
            ctx.translate(X(bx_), Y(by_))
            ctx.rotate(s["rot"] if abs(s["rot"]) < 1.0 else 0.0)
            S_ = self.S
            c.lines([(-0.6 * S_, 0, 0.6 * S_, 0)], GOLD, width=S_ * 0.08)
            for dx in (-0.28, 0.28):
                c.lines([(dx * S_, 0, dx * 1.15 * S_, 0.32 * S_)], GOLD, width=S_ * 0.06)
            ctx.restore()
            if s["airborne"] < 0.1:
                for k in range(14):
                    ph = (t * 2.6 + k / 14) % 1.0
                    dx = -0.55 - 1.4 * ph
                    dy = 0.15 + 1.1 * ph - 1.6 * ph * ph
                    c.circle(X(bx_ + dx), Y(by_ + dy), self.S * 0.035 * (1 - ph) + 1, (0.75, 0.92, 1.0), alpha=0.8 * (1 - ph))
        if not (255.0 <= t < 270.0) or 6.0 * (t - 255.0) / 15.0 < 1.2:
            self.draw_hero(s, t)
        if 352.0 <= t < 356.0:                                   # all six shards orbit him and merge
            u = seg(t, 352, 355.5)
            for k in range(6):
                a = k / 6 * 2 * math.pi + t * 4
                r = 1.4 * (1 - u)
                self.shard(s["x"] + r * math.cos(a), s["y"] + 0.75 + r * math.sin(a) * 0.6, a=1 - 0.5 * u)
        # --- the φ shards waiting to be caught
        waits = [(53.0, SHARD_T[0], (2.9, 0.35), 0.4), (106.5, SHARD_T[1], (GATE_X, 2.0), 0.0),
                 (165.5, SHARD_T[2], (PEAK[0], PEAK[1] + 0.85), 0.0), (228.0, SHARD_T[3], (CIRC_C, 0.95), 0.0),
                 (286.0, SHARD_T[4], (KOCH_C[0], KOCH_C[1]), 0.0), (344.0, SHARD_T[5], (TOWER_TOP[0] + 0.7, 35.0), 0.0)]
        for i, (t0, t1, (sx, sy), fall) in enumerate(waits):
            if t0 <= t < t1:
                if i == 0 and t < 54.6:
                    u = (t - 53.0) / 1.6
                    sy = 9.0 * (1 - u * u) + 0.35
                if i == 3:
                    sy = 0.95 * seg(t, 228, 231) + 0.3
                self.shard(sx, sy + 0.06 * math.sin(t * 6), label=f"φ {i + 1}/6", la=seg(t, t0 + 0.3, t0 + 0.8))
            elif t1 <= t < t1 + 0.5:
                u = sm((t - t1) / 0.5)
                self.shard(sx + (s["x"] - sx) * u, sy + (s["y"] + 0.75 - sy) * u, a=1 - u)
        ctx.restore()
        # --- HUD: shards collected
        n = shards_held(t)
        if n and t < 435.0:
            self.gtext(f"φ {n}/6", w * 0.92, h * 0.08, w * 0.028, GOLD, a=0.9)
            if any(0 <= t - ts < 1.5 for ts in SHARD_T):
                self.gtext(f"φ {n}/6", w * 0.5, h * 0.18, w * 0.045, GOLD, a=1.0)
        if 455.5 <= t:
            a = seg(t, 456.0, 457.5) * (1 - seg(t, 463.0, 465.0))
            self.gtext("Math is never broken.", w / 2, h * 0.16, w * 0.04, WHITE, a=a)
            self.gtext("Just waiting to be solved.", w / 2, h * 0.23, w * 0.04, GOLD, a=a)
        if t >= 462.0:                                          # the film's end: fade to black
            ctx.rectangle(0, 0, w, h)
            ctx.set_source_rgba(0, 0, 0, seg(t, 462.0, 465.0))
            ctx.fill()
        if rule:
            c.caption(rule, alpha=1.0, layout=L)
        c.watermark(L)


def render(layout, sim, out_path, rule, still_frame=None):
    sc = Scene(layout, sim)
    f0 = sim.get("f0", 0)
    if still_frame is not None:
        for f in range(max(0, still_frame - 400), still_frame + 1):   # warm the smoothed camera
            camera(f, layout.h)
        sc.draw(still_frame, rule)
        studio.save_still(sc.canvas, out_path)
        return still_frame / FPS
    for f in range(0, f0):
        camera(f, layout.h)
    writer = VideoWriter(out_path, sc.canvas, FPS)
    for f in range(f0, f0 + sim["nf"]):
        sc.draw(f, rule)
        writer.write_frame()
    writer.close()
    return sim["nf"] / FPS


# ================================================================ the score (original, synthesised)
def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def score(v_from, dur):
    """v2 score (owner): ONE hero theme for the whole film, never silent, arranged per scene (driving in fights,
    relaxed surfing, eerie labyrinth, epic tower, heaviest boss, calm ending) + short tonal sound effects synced to
    the action. All in VIDEO time (the story is re-timed: speed-ups, slow motion, hit-stops)."""
    sr = audio.SR
    n = int(round(dur * sr))
    mus = np.zeros(n)
    sfx = np.zeros(n)
    rng = np.random.default_rng(11)

    def add(buf, v0, sig, g):
        i0_ = int(round((v0 - v_from) * sr))
        if i0_ >= n or i0_ + len(sig) <= 0:
            return
        if i0_ < 0:
            sig = sig[-i0_:]
            i0_ = 0
        sig = sig[: n - i0_]
        buf[i0_:i0_ + len(sig)] += g * sig

    def tv(d):
        return np.arange(int(max(d, 0.001) * sr)) / sr

    def env(x, a, d):
        return np.clip(x / a, 0, 1) * np.exp(-x / d)

    # ---------------------------------------------------------------- instruments
    def piano(m, d=1.2):
        x = tv(d)
        f = hz(m)
        return sum(np.sin(2 * np.pi * f * k * x) * (0.6 ** k) for k in range(1, 6)) * env(x, 0.004, 0.45)

    def bell(m, d=0.6):
        x = tv(d)
        f = hz(m)
        return (np.sin(2 * np.pi * f * x) + 0.4 * np.sin(2 * np.pi * f * 2.76 * x)) * env(x, 0.002, 0.25)

    def cowbell(m, d=0.25):
        x = tv(d)
        ph = 2 * np.pi * hz(m) * x
        return (sum(np.sin(j * ph) / j for j in (1, 3, 5)) + 0.8 * sum(np.sin(j * ph * 1.48) / j for j in (1, 3, 5))) * env(x, 0.002, 0.06)

    def saw(m, d=0.3, bright=6):
        x = tv(d)
        f = hz(m)
        return sum(np.sin(2 * np.pi * f * k * x) / k for k in range(1, bright)) * env(x, 0.005, d * 0.6)

    def pluck(m, d=0.35):
        x = tv(d)
        f = hz(m)
        return sum(np.sin(2 * np.pi * f * k * x) / k * np.exp(-x * k * 3) for k in range(1, 5)) * np.clip(x / 0.003, 0, 1)

    def strings(m, d):
        x = tv(d)
        f = hz(m)
        vib = 1 + 0.004 * np.sin(2 * np.pi * 5.5 * x)
        ph = 2 * np.pi * f * np.cumsum(vib) / sr
        return (np.sin(ph) + 0.5 * np.sin(2 * ph) + 0.25 * np.sin(3 * ph)) * np.clip(x / 0.12, 0, 1) * np.clip((d - x) / 0.15, 0, 1)

    def pad(ms, d):
        x = tv(d)
        sig = sum(np.sin(2 * np.pi * hz(m) * x) + 0.4 * np.sin(2 * np.pi * hz(m) * 1.004 * x) for m in ms) / len(ms)
        return sig * np.clip(x / 0.35, 0, 1) * np.clip((d - x) / 0.35, 0, 1)

    def sub(m, d):
        x = tv(d)
        return np.sin(2 * np.pi * hz(m) * x) * np.clip(x / 0.01, 0, 1) * np.clip((d - x) / 0.03, 0, 1)

    def kick():
        x = tv(0.4)
        return np.sin(2 * np.pi * np.cumsum(48 + 110 * np.exp(-x / 0.03)) / sr) * np.exp(-x / 0.16)

    def snare():
        x = tv(0.22)
        nz = rng.standard_normal(len(x))
        return (nz - np.convolve(nz, np.ones(5) / 5, mode="same")) * np.exp(-x / 0.06) + 0.6 * np.sin(2 * np.pi * 190 * x) * np.exp(-x / 0.05)

    def hat(open_=False):
        x = tv(0.12 if open_ else 0.04)
        nz = np.diff(np.concatenate([[0], rng.standard_normal(len(x))]))
        return nz * np.exp(-x / (0.05 if open_ else 0.01))

    def tom(m=45):
        x = tv(0.5)
        return np.sin(2 * np.pi * np.cumsum(hz(m) * (1 + 0.6 * np.exp(-x / 0.05))) / sr) * np.exp(-x / 0.2)

    def b808(m, d=0.7, drive=2.4):
        x = tv(d)
        fr = hz(m) * (1 + 1.5 * np.exp(-x / 0.03))
        return np.tanh(drive * np.sin(2 * np.pi * np.cumsum(fr) / sr)) * np.exp(-x / 0.5)

    # ---------------------------------------------------------------- the hero theme (D minor) + chords
    THEME = [62, 65, 69, 67, 65, 64, 62, 60, 62, 69, 74, 72, 69, 67, 69, 64]      # 2 bars of 8ths
    CH = [(50, 53, 57), (46, 50, 53), (53, 57, 60), (48, 52, 55)]                  # Dm  B♭  F  C
    ROOT = [38, 34, 41, 36]

    STYLE = {
        "intro":    dict(bpm=80, lead="piano", dens=4, oct=0, drums=None, bass="whole", pad=1.0),
        "mystery":  dict(bpm=80, lead="bell", dens=2, oct=12, drums=None, bass="pulse", pad=1.0),
        "tension":  dict(bpm=100, lead="bell", dens=2, oct=0, drums="light", bass="8ths", pad=0.8),
        "fight":    dict(bpm=140, lead="cowbell", dens=1, oct=12, drums="phonk", bass="808", pad=0.5),
        "run":      dict(bpm=150, lead="saw", dens=1, oct=0, drums="drive", bass="8ths", pad=0.5),
        "zeno":     dict(bpm=120, lead="pluck", dens=1, oct=12, drums="light", bass="8ths", pad=0.7, arp=True),
        "gate":     dict(bpm=90, lead="strings", dens=2, oct=0, drums="toms", bass="whole", pad=1.0),
        "mountain": dict(bpm=110, lead="strings", dens=2, oct=0, drums="epic", bass="8ths", pad=0.8),
        "skate":    dict(bpm=128, lead="saw", dens=1, oct=0, drums="drive", bass="8ths", pad=0.6),
        "surf":     dict(bpm=96, lead="pluck", dens=1, oct=12, drums="soft", bass="synthwave", pad=0.9, arp=True),
        "surftan":  dict(bpm=96, lead="pluck", dens=1, oct=12, drums="busy", bass="synthwave", pad=0.9, arp=True),
        "calm":     dict(bpm=84, lead="bell", dens=2, oct=12, drums=None, bass="whole", pad=1.0),
        "eerie":    dict(bpm=88, lead="echo", dens=2, oct=12, drums="pulse", bass="pulse", pad=0.9),
        "clones":   dict(bpm=145, lead="cowbell", dens=1, oct=12, drums="phonk", bass="808", pad=0.5),
        "choir":    dict(bpm=84, lead="piano", dens=2, oct=12, drums=None, bass="whole", pad=1.2),
        "tower":    dict(bpm=104, lead="strings", dens=1, oct=0, drums="build", bass="8ths", pad=0.9),
        "power":    dict(bpm=104, lead="strings", dens=1, oct=12, drums="epic", bass="8ths", pad=1.2),
        "leap":     dict(bpm=120, lead="strings", dens=2, oct=12, drums="toms", bass="whole", pad=1.2),
        "boss":     dict(bpm=155, lead="cowbell", dens=1, oct=12, drums="heavy", bass="808", pad=0.6),
        "vortex":   dict(bpm=78, lead="saw", dens=2, oct=-12, drums="halftime", bass="808", pad=1.0),
        "finale":   dict(bpm=155, lead="saw", dens=1, oct=12, drums="heavy", bass="808", pad=0.8),
        "restore":  dict(bpm=76, lead="piano", dens=2, oct=0, drums=None, bass="whole", pad=1.1),
    }
    SECTIONS = [(0, "intro"), (15, "mystery"), (30, "tension"), (45, "fight"), (60, "run"), (90, "zeno"),
                (105, "gate"), (120, "mountain"), (136, "skate"), (150, "mountain"), (168, "gate"), (180, "surf"),
                (210, "surftan"), (225, "calm"), (240, "eerie"), (270, "clones"), (285, "choir"), (300, "tower"),
                (345, "power"), (360, "leap"), (367, "boss"), (405, "vortex"), (420, "finale"), (435, "restore"),
                (T_END, None)]
    vend = v_from + dur
    for (s0, name), (s1, _) in zip(SECTIONS, SECTIONS[1:]):
        v0, v1 = v_of(s0), v_of(s1)
        if v1 <= v_from or v0 >= vend:
            continue
        st = STYLE[name]
        B = 60.0 / st["bpm"]
        add(mus, v0 - 0.4, pad([m + 12 for m in CH[0]], 0.8), 0.04)              # a soft swell into every scene
        bar = 0
        while v0 + bar * 4 * B < v1:
            vb = v0 + bar * 4 * B
            ci = bar % 4
            ch, rt = CH[ci], ROOT[ci]
            bl = min(4 * B, v1 - vb)
            add(mus, vb, pad([m + 12 for m in ch], bl + 0.3), 0.05 * st["pad"])
            # bass
            if st["bass"] == "whole":
                add(mus, vb, sub(rt, bl), 0.18)
            elif st["bass"] == "pulse":
                for k in range(4):
                    add(mus, vb + k * B, sub(rt, B * 0.7) * np.exp(-tv(B * 0.7) / 0.25), 0.2)
            elif st["bass"] == "8ths":
                for k in range(8):
                    add(mus, vb + k * B / 2, saw(rt + 12, B * 0.45, 4), 0.06)
            elif st["bass"] == "synthwave":
                for k in range(8):
                    add(mus, vb + k * B / 2, saw(rt + 12 + (12 if k % 2 else 0), B * 0.45, 3), 0.05)
            elif st["bass"] == "808":
                for pos in (0, 2.5):
                    if pos * B < bl:
                        add(mus, vb + pos * B, b808(rt), 0.26)
            # drums
            dr = st["drums"]
            for k in range(16):
                vk = vb + k * B / 4
                if vk >= v1:
                    break
                beat, sixteenth = k // 4, k % 4
                if dr == "light" and sixteenth == 0 and beat in (0, 2):
                    add(mus, vk, kick(), 0.30)
                elif dr == "pulse" and sixteenth == 0:
                    add(mus, vk, kick() * 0.6, 0.22)
                elif dr == "soft":
                    if sixteenth == 0 and beat in (0, 2):
                        add(mus, vk, kick(), 0.30)
                    if sixteenth == 0 and beat in (1, 3):
                        add(mus, vk, snare(), 0.08)
                    if sixteenth == 2:
                        add(mus, vk, hat(), 0.015)
                elif dr == "busy":
                    if sixteenth == 0:
                        add(mus, vk, kick(), 0.32)
                    if sixteenth == 0 and beat in (1, 3):
                        add(mus, vk, snare(), 0.10)
                    add(mus, vk, hat(), 0.018)
                elif dr == "drive":
                    if sixteenth == 0:
                        add(mus, vk, kick(), 0.36)
                    if sixteenth == 0 and beat in (1, 3):
                        add(mus, vk, snare(), 0.11)
                    if sixteenth % 2 == 0:
                        add(mus, vk, hat(sixteenth == 2), 0.02)
                elif dr in ("phonk", "heavy"):
                    if sixteenth % 2 == 0:
                        add(mus, vk, hat(), 0.022)
                    if k == 8:
                        add(mus, vk, snare(), 0.13 if dr == "heavy" else 0.10)
                    if dr == "heavy" and k in (0, 6, 10):
                        add(mus, vk, kick(), 0.32)
                elif dr == "toms" and sixteenth == 0:
                    add(mus, vk, tom(43 + (beat % 2) * 5), 0.28)
                elif dr == "epic":
                    if sixteenth == 0:
                        add(mus, vk, tom(41 + beat * 2), 0.26)
                    if k in (0, 10):
                        add(mus, vk, kick(), 0.34)
                    if k in (4, 12):
                        add(mus, vk, snare(), 0.10)
                elif dr == "build":
                    prog = (vk - v0) / max(0.1, (v1 - v0))
                    step = 4 if prog < 0.35 else (2 if prog < 0.7 else 1)
                    if k % step == 0:
                        add(mus, vk, kick(), 0.2 + 0.18 * prog)
                    if prog > 0.5 and k % 4 == 2:
                        add(mus, vk, snare(), 0.06 + 0.06 * prog)
                elif dr == "halftime":
                    if k == 0:
                        add(mus, vk, kick(), 0.4)
                    if k == 8:
                        add(mus, vk, snare(), 0.12)
                    if k % 4 == 2:
                        add(mus, vk, hat(), 0.015)
            # the hero theme
            for k in range(8):
                if k % st["dens"]:
                    continue
                vk = vb + k * B / 2
                if vk >= v1:
                    break
                m = THEME[(bar % 2) * 8 + k] + st["oct"]
                ld = st["lead"]
                if ld == "piano":
                    add(mus, vk, piano(m, B * 2.5), 0.10)
                elif ld == "bell":
                    add(mus, vk, bell(m, B * 2), 0.08)
                elif ld == "cowbell":
                    add(mus, vk, cowbell(m), 0.06)
                elif ld == "saw":
                    add(mus, vk, saw(m, B * 0.5), 0.045)
                elif ld == "pluck":
                    add(mus, vk, pluck(m, B * 0.9), 0.08)
                elif ld == "strings":
                    add(mus, vk, strings(m, B * st["dens"] * 0.55), 0.045)
                elif ld == "echo":
                    for e in range(3):
                        add(mus, vk + e * B * 0.75, bell(m, B * 1.5), 0.06 * 0.5 ** e)
            if st.get("arp"):
                for k in range(16):
                    vk = vb + k * B / 4
                    if vk >= v1:
                        break
                    add(mus, vk, pluck(ch[k % 3] + 24, B * 0.4), 0.025)
            bar += 1

    # ---------------------------------------------------------------- sound effects (story time → video time)
    def fx(t, sig, g):
        add(sfx, v_of(t), sig, g)

    def whoosh(d=0.28):
        x = tv(d)
        nz = np.convolve(rng.standard_normal(len(x)), np.ones(14) / 14, mode="same") * 3
        return nz * np.sin(np.pi * x / d) ** 2

    def thud():
        x = tv(0.35)
        return np.sin(2 * np.pi * np.cumsum(60 + 90 * np.exp(-x / 0.02)) / sr) * np.exp(-x / 0.09)

    def punch():
        th_ = thud()
        x = np.arange(len(th_)) / sr
        return th_ + 0.6 * rng.standard_normal(len(x)) * np.exp(-x / 0.008)

    def chime(base=81):
        return sum(bell(base + k, 1.4) for k in (0, 4, 7, 12)) / 3

    def zap(f0=1800, d=0.4):
        x = tv(d)
        return np.sin(2 * np.pi * np.cumsum(f0 * np.exp(-x / 0.12) + 150) / sr) * np.exp(-x / 0.15)

    def rise(d, f0=200, f1=1400):
        x = tv(d)
        return np.sin(2 * np.pi * np.cumsum(f0 + (f1 - f0) * (x / d) ** 2) / sr) * (x / d) ** 1.5

    def splash():
        x = tv(0.25)
        nz = rng.standard_normal(len(x))
        return (nz - np.convolve(nz, np.ones(4) / 4, mode="same")) * np.exp(-x / 0.05) + 0.3 * sum(
            np.sin(2 * np.pi * rng.uniform(1500, 3500) * x) * np.exp(-x / 0.04) for _ in range(3))

    def rumble(d):
        x = tv(d)
        return np.sin(2 * np.pi * 52 * x) * (0.6 + 0.4 * np.sin(2 * np.pi * 9 * x)) * np.clip(x / 0.2, 0, 1) * np.clip((d - x) / 0.2, 0, 1)

    for tb in (1.0, 2.6, 4.2, 5.8, 7.4, 9.0):
        fx(tb, thud(), 0.5)
        fx(tb + 0.22, thud(), 0.3)
    fx(8.4, rise(2.0, 300, 1200) * 0.5, 0.10)
    fx(14.0, chime(76), 0.10)
    fx(18.8, zap(900, 1.2), 0.08)
    fx(T_SHATTER, sum(bell(rng.integers(84, 100), 1.0) for _ in range(8)) / 4, 0.18)
    fx(T_SHATTER, punch(), 0.4)
    fx(22.5, b808(30, 1.2, 4.0), 0.25)
    for k in range(10):
        fx(31.0 + k * 0.4, zap(2500, 0.08), 0.04)
    for lab, x0, te, tk in CREATURES:
        fx(te, zap(1200, 0.15), 0.05)
        fx(tk - 0.5, whoosh(0.25), 0.10)
    for th, kind in HITS1:
        fx(th, punch(), 0.55)
        fx(th + 0.55, splash() * 0.5, 0.2)
    fx(50.2, whoosh(0.5), 0.12)
    fx(53.0, rise(1.6, 1600, 500), 0.05)
    fx(SHARD_T[0], chime(81), 0.20)
    for k in range(int((90 - 60) * 2.4)):                       # metallic footsteps on the highway
        fx(60.5 + k / 2.4, bell(98, 0.05), 0.03)
    fx(75.2, rise(1.5, 100, 300), 0.08)
    fx(75.85, whoosh(0.4), 0.14)
    fx(77.0, thud(), 0.5)
    for k in range(14):
        fx(90.0 + 1.0 * k, pluck(74 + k * 2, 0.4), 0.08)
    fx(106.0, sum(strings(m, 2.5) for m in (38, 45, 50)) / 2, 0.12)
    fx(106.0, thud(), 0.6)
    fx(SHARD_T[1], chime(83), 0.20)
    fx(136.0, rumble(4.8), 0.10)
    fx(140.8, whoosh(0.5), 0.15)
    fx(142.4, thud(), 0.6)
    for tb, tp, kind in BOULDERS:
        fx(tb, rumble(tp - tb + (0.8 if kind != "punch" else 0.0)), 0.12)
        if kind == "jump":
            fx(tp - 0.42, whoosh(0.35), 0.13)
            fx(tp + 0.43, thud(), 0.4)
        elif kind == "duck":
            fx(tp - 0.2, whoosh(0.45), 0.15)
        else:
            fx(tp - 0.45, whoosh(0.2), 0.08)
            fx(tp, punch(), 0.7)
            fx(tp, sum(bell(rng.integers(70, 85), 0.5) for _ in range(4)) / 3, 0.12)
    fx(167.0, chime(74), 0.14)
    fx(SHARD_T[2], chime(86), 0.20)
    fx(181.0, whoosh(0.8), 0.12)
    fx(188.0, splash(), 0.25)
    tt = 189.0
    while tt < 231.0:                                           # the board carving through the water
        fx(tt, whoosh(0.35) * 0.6, 0.06)
        tt += 1.8
    for th in (194.0, 201.0, 206.5):
        fx(th, whoosh(0.3), 0.10)
        fx(th + 0.75, splash(), 0.2)
    for ts, xs in TAN_SPIKES:
        fx(ts - 1.1, zap(400, 0.6) * -1, 0.05)
        fx(ts - 0.5, whoosh(0.35), 0.12)
        fx(ts + 0.5, splash(), 0.2)
        fx(ts - 1.0, bell(88, 0.15), 0.05)
        fx(ts - 0.85, bell(88, 0.15), 0.05)
    for k in range(4):
        fx(226.0 + 3.0 * k, bell(81 + [0, 4, 7, 12][k], 2.0), 0.10)
    fx(SHARD_T[3], chime(88), 0.20)
    for k in range(6):
        fx(255.0 + 2.5 * k, whoosh(0.6), 0.07)
    for i, th in enumerate(CLONE_T):
        fx(th - 0.35, whoosh(0.2), 0.10)
        fx(th, punch(), 0.6)
        fx(th + 0.5, splash() * 0.5, 0.15)
    fx(279.0, whoosh(0.6), 0.12)
    fx(286.0, sum(bell(m, 2.5) for m in (79, 83, 86, 91)) / 3, 0.12)
    fx(SHARD_T[4], chime(90), 0.20)
    for i, tj in enumerate(JUMP_T):
        fx(tj - 0.9, whoosh(0.35), 0.10)
        fx(tj, thud(), 0.45)
        fx(tj, bell(72 + [0, 2, 3, 5, 7, 8, 10, 12][i], 0.8), 0.10)
    fx(330.0, rise(8.0, 400, 1200) * 0.4, 0.06)
    fx(SHARD_T[5], chime(93), 0.22)
    fx(351.5, rise(3.5, 100, 1500), 0.10)
    fx(355.0, b808(30, 1.6, 3.0), 0.5)
    fx(355.0, thud(), 0.7)
    fx(360.0, whoosh(1.2), 0.15)
    fx(366.4, b808(29, 1.5, 3.0), 0.5)
    fx(368.0, b808(26, 2.0, 5.0), 0.35)
    x = tv(2.5)
    fx(369.5, np.tanh(3 * np.sin(2 * np.pi * np.cumsum(70 - 25 * x / 2.5) / sr)) * np.sin(np.pi * x / 2.5), 0.22)
    for tb in (376.0, 377.4, 378.6, 380.6, 381.6, 382.4, 385.6, 386.9, 388.2):
        fx(tb, zap(2200, 0.5), 0.07)
        fx(tb + 0.85, whoosh(0.3), 0.10)
    fx(376.0, whoosh(1.2), 0.10)
    for k in range(8):
        fx(380.0 + k * 0.32, bell(96, 0.05), 0.04)
    fx(382.6, whoosh(0.6), 0.12)
    fx(384.4, thud(), 0.5)
    for th in COUNTER_T:
        fx(th - 0.15, whoosh(0.15), 0.08)
        fx(th, punch(), 0.75)
        fx(th, bell(86, 0.8), 0.08)
    x = tv(15.0)
    fx(405.0, np.sin(2 * np.pi * np.cumsum(90 * np.exp(-x / 10)) / sr) * np.clip(x / 2, 0, 1) * np.clip((15 - x), 0, 1), 0.10)
    fx(420.0, rise(6.5, 80, 1600), 0.12)
    fx(428.5, punch(), 1.0)
    fx(428.5, b808(26, 2.5, 5.0), 0.6)
    fx(429.0, sum(bell(rng.integers(84, 100), 1.5) for _ in range(10)) / 4, 0.25)
    fx(438.0, rise(6.0, 300, 900) * 0.3, 0.06)
    for k in range(10):
        fx(440.0 + 1.2 * k, bell(81 + [0, 2, 4, 7, 9, 12, 14, 16, 19, 21][k], 1.5), 0.07)
    fx(457.0, piano(74, 4.0), 0.12)
    out = 0.85 * mus + 1.0 * sfx
    tail = np.clip((V_END - (np.arange(n) / sr + v_from)) / 3.0, 0, 1)
    head = np.clip((np.arange(n) / sr + v_from) / 0.3, 0, 1)
    return (out * tail * head).astype(np.float32)


def _worker(o, sim, label, rule):
    layout = get_layout(o)
    name = f"{SCENE}_{label}_{layout.tag}"
    video = studio.OUT_DIR / f"{name}_silent.mp4"
    d = render(layout, sim, video, rule)
    t_from = sim.get("f0", 0) / FPS
    kit.deliver_loop(SCENE, name, layout, video, [], d, voice="piano", bed=score(t_from, d), peak_db=-4.0)


def main():
    label, rule = arg("--label", "full"), arg("--rule", "")
    studio.OUT_DIR.mkdir(exist_ok=True)
    sim = simulate()
    if kit.has("--still"):
        layout = get_layout(kit.orients()[0])
        f = int(arg("--frame", "0"))
        png = studio.OUT_DIR / f"{SCENE}_{label}_f{f}_{layout.tag}.png"
        render(layout, sim, png, rule, still_frame=f)
        print(f"[{SCENE}] -> {png}")
        return
    print(f"[{SCENE}] {sim['nf'] / FPS:.0f}s from {sim.get('f0', 0) / FPS:.0f}s")
    kit.fan_out(_worker, (sim, label, rule), SCENE)


if __name__ == "__main__":
    main()
