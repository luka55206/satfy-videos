"""DOT AND THE RABBITS — one continuous stick-figure film (16:9, ~2:38). Script: docs/scripts/dot_rabbits.md.

A 2.5D world: ground plane (x, z), upright sprites; the camera flies (centre, zoom S, tilt k = ground squash).
World state is driven by a world clock tau (the hook shows month 11, then rewinds to the start; after that tau = t).
Fibonacci's rabbit rules: a baby pair grows up in a month; every grown-up pair has a baby pair every month →
pairs per month 1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144. Pens are Fibonacci squares placed on the ranch's long
side; the delivery road is the quarter-arc golden spiral through them; the ranch ratio → φ.
No chapters, no talking: the story is actions, objects, in-world writing (note, calendar, chalkboard) and sound.
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
import dot_adventure as DA  # noqa: E402  (the puppet, poses and cycles are shared)

SCENE = "dot_rabbits"
T_END = 158.0
SR = audio.SR
BLUE, GOLD, WHITE = DA.BLUE, DA.GOLD, DA.WHITE
PHI = (1 + 5 ** 0.5) / 2

P = [1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144]                       # pairs at month 0 … 11
MONTH_T = [8.0, 20.0, 26.0, 32.0, 39.0, 68.0, 73.0, 77.5, 81.5, 100.0, 104.0, 108.0]
F = [1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89]
BUILD = [(15.6, 18.0), (27.5, 30.0), (35.0, 37.5), (40.0, 42.2), (68.8, 70.8), (73.6, 75.6), (78.0, 80.0),
         (82.0, 84.0), (100.5, 102.5), (104.5, 106.5), (108.5, 110.5)]
PEN = 2.0                                                            # world units per Fibonacci unit
ROAD = (89.0, 93.0)
RIDE = (93.0, 99.0)


def tiling():
    sq, box, boxes = [(0.0, 0.0, 1.0)], [0.0, 0.0, 1.0, 1.0], []
    boxes.append(tuple(box))
    for n in range(1, len(F)):
        s, d = F[n], (n - 1) % 4
        if d == 0:
            sq.append((box[2], box[1], s)); box[2] += s
        elif d == 1:
            sq.append((box[0], box[3], s)); box[3] += s
        elif d == 2:
            sq.append((box[0] - s, box[1], s)); box[0] -= s
        else:
            sq.append((box[0], box[1] - s, s)); box[1] -= s
        boxes.append(tuple(box))
    arcs, Pp = [((1.0, 1.0), 1.0, (0.0, 1.0), (1.0, 0.0))], (1.0, 0.0)
    for n in range(1, len(F)):
        x, y, s = sq[n]
        corners = [(x, y), (x + s, y), (x + s, y + s), (x, y + s)]
        bx = boxes[n - 1]
        shared = [q for q in corners if bx[0] - 1e-9 <= q[0] <= bx[2] + 1e-9 and bx[1] - 1e-9 <= q[1] <= bx[3] + 1e-9]
        C = [q for q in shared if abs(q[0] - Pp[0]) + abs(q[1] - Pp[1]) > 1e-9][0]
        Q = [q for q in corners if abs(math.hypot(q[0] - C[0], q[1] - C[1]) - s) < 1e-9 and
             abs(q[0] - Pp[0]) + abs(q[1] - Pp[1]) > 1e-9][0]
        arcs.append((C, s, Pp, Q))
        Pp = Q
    S = [(x * PEN, z * PEN, s * PEN) for x, z, s in sq]
    B = [tuple(v * PEN for v in b) for b in boxes]
    A = [((c[0] * PEN, c[1] * PEN), r * PEN, (p[0] * PEN, p[1] * PEN), (q[0] * PEN, q[1] * PEN)) for c, r, p, q in arcs]
    return S, B, A


SQ, BOXES, ARCS = tiling()
HOUSE = (1.0, 7.2)                                                   # front door (x, z): swallowed by pen 6 later
BOARD = (6.2, 7.4)
BURIED = (-1.0, -4.0)


def road_points():
    pts = []
    for (cx, cz), r, (px, pz), (qx, qz) in ARCS:
        a0, a1 = math.atan2(pz - cz, px - cx), math.atan2(qz - cz, qx - cx)
        da = (a1 - a0 + math.pi) % (2 * math.pi) - math.pi
        for j in range(24):
            a = a0 + da * j / 24
            pts.append((cx + r * math.cos(a), cz + r * math.sin(a)))
    pts.append(ARCS[-1][3])
    return pts


ROAD_PTS = road_points()
ROAD_CUM = np.concatenate([[0.0], np.cumsum([math.dist(a, b) for a, b in zip(ROAD_PTS, ROAD_PTS[1:])])])


N_RIDE = 8 * 24                                                      # the road Dot builds covers pens 0–7


def road_visible(tau):
    """Number of road points visible: grows over pens 0–7 during ROAD, then one arc per newly built pen."""
    if tau < ROAD[0]:
        return 0
    n = int(N_RIDE * min(1.0, (tau - ROAD[0]) / (ROAD[1] - ROAD[0])))
    if tau >= ROAD[1]:
        for i in range(8, len(SQ)):
            b0, b1 = BUILD[i]
            n += int(24 * min(1.0, max(0.0, (tau - b0) / (b1 - b0))))
    return min(len(ROAD_PTS), n + 1)


def road_at(frac):
    s = frac * ROAD_CUM[N_RIDE]
    i = min(len(ROAD_PTS) - 2, int(np.searchsorted(ROAD_CUM, s, side="right")) - 1)
    u = (s - ROAD_CUM[i]) / max(1e-9, ROAD_CUM[i + 1] - ROAD_CUM[i])
    a, b = ROAD_PTS[i], ROAD_PTS[i + 1]
    return a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u


def month_at(tau):
    m = 0
    for k, tm in enumerate(MONTH_T):
        if tau >= tm:
            m = k
    return m


# ---------------------------------------------------------------- the rabbits
def _h(i, k):
    x = math.sin(i * 12.9898 + k * 78.233) * 43758.5453
    return x - math.floor(x)


def build_rabbits():
    out = []
    for j in range(P[-1]):
        b = next(m for m in range(len(P)) if P[m] > j)
        rank = j - (P[b - 1] if b > 0 else 0)
        n_new = P[b] - (P[b - 1] if b > 0 else 0)
        t_born = 18.3 if b == 0 else MONTH_T[b] + 0.3 + 0.8 * rank / max(1, n_new)
        t_grow = MONTH_T[b + 1] + 0.2 if b + 1 < len(MONTH_T) else 1e9
        avail = [i for i in range(len(SQ)) if BUILD[i][1] <= max(t_born, 18.0) + 0.01] or [0]
        wts = np.array([SQ[i][2] ** 1.1 for i in avail])
        u = _h(j, 1) * wts.sum()
        si = avail[int(np.searchsorted(np.cumsum(wts), u))] if j > 0 else 0
        x0, z0, s = SQ[si]
        m = min(0.4, s * 0.2)
        x = x0 + m + (s - 2 * m) * _h(j, 2)
        z = z0 + m + (s - 2 * m) * _h(j, 3)
        for k in range(2):
            out.append(dict(x=x + 0.28 * k, z=z + 0.12 * k, born=t_born, grow=t_grow, face=1 if _h(j, 4 + k) > 0.5 else -1,
                            ph=_h(j, 6 + k) * 6.28, pair=j))
    return out


RABBITS = build_rabbits()


# ---------------------------------------------------------------- Dot's track
# segments: (t0, t1, (x0, z0), (x1, z1), pose, face, extras)
def seg_table():
    D = HOUSE[0], HOUSE[1] - 0.4
    PEN0 = (3.0, 0.9)
    return [
        (0.0, 6.6, BURIED, BURIED, "cheer", 1, dict(mouth="open", eyes="wide", buried=True)),
        (6.6, 8.0, BURIED, D, "stand", 1, dict(hide=True)),
        (8.0, 10.4, D, D, "stand", 1, dict(hide=True)),
        (10.4, 11.0, D, (HOUSE[0] + 0.1, HOUSE[1] - 0.8), "walk", 1, {}),
        (11.0, 11.6, (HOUSE[0] + 0.1, HOUSE[1] - 0.8), (HOUSE[0] + 0.1, HOUSE[1] - 0.8), "stand", 1, dict(mouth="open", eyes="wide", bang=True)),
        (11.6, 12.0, (HOUSE[0] + 0.1, HOUSE[1] - 0.8), (HOUSE[0] + 0.1, HOUSE[1] - 0.8), "crouch", 1, {}),
        (12.0, 14.0, (HOUSE[0] + 0.1, HOUSE[1] - 0.8), (HOUSE[0] + 0.1, HOUSE[1] - 0.8), "hug", 1, dict(basket=True, note=True)),
        (14.0, 15.6, (HOUSE[0] + 0.1, HOUSE[1] - 0.8), PEN0, "walk", 1, dict(basket=True)),
        (15.6, 18.0, PEN0, PEN0, "hammer", -1, dict(hammer=True, basket_down=True)),
        (18.0, 19.0, PEN0, PEN0, "plant", -1, dict(basket=True)),
        (19.0, 21.0, PEN0, PEN0, "stand", -1, {}),
        (21.0, 22.5, PEN0, (-2.5, 4.6), "walk", -1, {}),
        (22.5, 26.0, (-2.5, 4.6), (-2.5, 4.6), "read", 1, dict(book=True)),
        (26.0, 26.5, (-2.5, 4.6), (-2.5, 4.6), "read", 1, dict(book=True)),
        (26.5, 27.0, (-2.5, 4.6), (-2.5, 4.6), "jump", 1, dict(mouth="open", eyes="wide", bang=True, book_drop=True)),
        (27.0, 27.5, (-2.5, 4.6), (3.0, -0.6), "run", 1, {}),
        (27.5, 30.0, (3.0, -0.6), (3.0, -0.6), "hammer", 1, dict(hammer=True)),
        (30.0, 32.6, (3.0, -0.6), (3.0, -0.6), "stand", 1, {}),
        (32.6, 35.0, (3.0, -0.6), (4.7, 4.0), "think", 1, dict(think=True)),
        (35.0, 37.5, (4.7, 4.0), (4.7, 4.0), "hammer", -1, dict(hammer=True)),
        (37.5, 39.0, (4.7, 4.0), (4.7, 4.0), "stand", -1, {}),
        (39.0, 40.0, (4.7, 4.0), (-6.5, 3.0), "run", -1, {}),
        (40.0, 42.2, (-6.5, 3.0), (-6.5, 3.0), "hammer", 1, dict(hammer=True)),
        (42.2, 43.0, (-6.5, 3.0), (-6.5, 3.0), "stand", 1, {}),
        (43.0, 44.5, (-6.5, 3.0), (BOARD[0] - 1.9, BOARD[1] - 0.2), "walk", 1, {}),
        (44.5, 64.5, (BOARD[0] - 1.9, BOARD[1] - 0.2), (BOARD[0] - 1.9, BOARD[1] - 0.2), "write", 1, dict(chalk=True)),
        (64.5, 67.5, (BOARD[0] - 1.9, BOARD[1] - 0.2), (BOARD[0] - 1.9, BOARD[1] - 0.2), "nervous", 1, dict(mouth="open", eyes="wide", chalk_drop=True)),
        (67.5, 68.8, (BOARD[0] - 1.9, BOARD[1] - 0.2), (-1.0, -10.8), "run", -1, {}),
        (68.8, 70.8, (-1.0, -10.8), (-1.0, -10.8), "hammer", 1, dict(hammer=True, sweat=True)),
        (70.8, 73.0, (-1.0, -10.8), (12.0, -10.8), "cart", 1, dict(cart=True, sweat=True)),
        (73.0, 73.6, (12.0, -10.8), (8.0, -10.8), "run", -1, dict(sweat=True)),
        (73.6, 75.6, (8.0, -10.8), (8.0, -10.8), "hammer", 1, dict(hammer=True, sweat=True)),
        (75.6, 77.5, (8.0, -10.8), (8.0, 4.0), "cart", 1, dict(cart=True, sweat=True)),
        (77.5, 78.0, (8.0, 4.0), (7.0, 5.0), "run", 1, dict(sweat=True)),
        (78.0, 80.0, (7.0, 5.0), (7.0, 5.0), "hammer", 1, dict(hammer=True, sweat=True)),
        (80.0, 81.5, (7.0, 5.0), (-6.5, 5.0), "cart", -1, dict(cart=True, sweat=True)),
        (81.5, 82.0, (-6.5, 5.0), (-7.0, 6.0), "run", -1, dict(sweat=True)),
        (82.0, 84.0, (-7.0, 6.0), (-7.0, 6.0), "hammer", -1, dict(hammer=True, sweat=True)),
        (84.0, 86.0, (-7.0, 6.0), (1.5, 1.0), "cart", 1, dict(cart=True, sweat=True)),
        (86.0, 88.0, (1.5, 1.0), (1.5, 1.0), "sit", 1, dict(sweat=True, mouth="flat")),
        (88.0, 89.0, (1.5, 1.0), (1.5, 1.0), "cheer", 1, dict(bulb=True)),
        (89.0, 93.0, (1.5, 1.0), (1.5, 1.0), "poke", 1, {}),
        (93.0, 99.0, (1.5, 1.0), (1.5, 1.0), "ride", 1, dict(cart=True, ride=True)),
        (99.0, 100.0, None, None, "cheer", 1, {}),
        (100.0, 110.5, None, None, "hammer", 1, dict(hammer=True, sweat=True, builder=True)),
        (110.5, 113.0, BURIED, BURIED, "cheer", 1, dict(mouth="open", eyes="wide", buried=True)),
        (113.0, 114.5, BURIED, (BURIED[0] + 2.0, BURIED[1]), "jump", 1, {}),
        (114.5, 126.0, (BURIED[0] + 2.0, BURIED[1]), (BURIED[0] + 2.0, BURIED[1]), "poke", 1, dict(tape=True)),
        (126.0, 141.0, (BURIED[0] + 2.0, BURIED[1]), (BURIED[0] + 2.0, BURIED[1]), "stand", 1, dict(mouth="open")),
        (141.0, 145.5, (BURIED[0] + 2.0, BURIED[1]), (HOUSE[0] + 0.6, HOUSE[1] - 0.5), "walk", 1, {}),
        (145.5, 147.5, (HOUSE[0] + 0.6, HOUSE[1] - 0.5), (HOUSE[0] + 0.6, HOUSE[1] - 0.5), "sit", 1, dict(mouth="flat")),
        (147.5, 151.0, (HOUSE[0] + 0.6, HOUSE[1] - 0.5), (HOUSE[0] + 0.6, HOUSE[1] - 0.5), "sit", 1, dict(mouth="open", eyes="wide", bang=True)),
        (151.0, T_END, (HOUSE[0] + 0.6, HOUSE[1] - 0.5), (HOUSE[0] + 0.6, HOUSE[1] - 0.5), "faint", 1, dict(mouth="open", eyes="closed")),
    ]


SEGS = seg_table()
EXTRA_POSES = {
    "hug": dict(lean=0, head=10, af=(70, 20), ab=(-40, 40), lf=(7, 2), lb=(-7, -2)),
    "think": dict(lean=5, head=15, af=(40, 170), ab=(-15, -5), lf=(7, 2), lb=(-7, -2)),
    "write": dict(lean=5, head=-10, af=(120, 100), ab=(-15, -5), lf=(10, 2), lb=(-10, -2)),
    "read": dict(lean=10, head=30, af=(60, 120), ab=(50, 110), lf=(85, 95), lb=(80, 100), seat=True),
    "cartp": dict(lean=25, head=0, af=(80, 85), ab=(75, 80), lf=(20, 0), lb=(-20, -10)),
    "ride": dict(lean=5, head=-10, af=(150, 170), ab=(80, 90), lf=(85, 95), lb=(80, 100), seat=True),
}


def pose_of(name, t):
    if name == "walk":
        return DA.cycle(t)
    if name == "run":
        return DA.cycle(t, True)
    if name == "hammer":
        up = (math.sin(t * 2 * math.pi * 2.4) > 0)
        return dict(lean=15, head=10, af=((150, 160) if up else (70, 110)), ab=(-10, -5), lf=(25, -5), lb=(-20, -10))
    if name == "cart":
        p = DA.cycle(t, True)
        q = EXTRA_POSES["cartp"]
        return dict(p, af=q["af"], ab=q["ab"], lean=q["lean"])
    if name == "faint":
        return DA.POSES["stand"]
    if name in EXTRA_POSES:
        return EXTRA_POSES[name]
    return DA.POSES[name]


def builder_pos(t):
    """During months 9–11 Dot (tiny) hammers in front of each new square."""
    for i in (8, 9, 10):
        b0, b1 = BUILD[i]
        if t < b1 + 1.5:
            x, z, s = SQ[i]
            return x + s * (0.2 + 0.6 * smooth((t - b0) / (b1 - b0))), z - 0.6
    x, z, s = SQ[10]
    return x + s * 0.8, z - 0.6


def dot_state(t):
    prev = None
    for sg in SEGS:
        t0, t1, p0, p1, pose, face, ex = sg
        if t0 <= t < t1 or (sg is SEGS[-1] and t >= t1):
            if p0 is None:
                if ex.get("builder"):
                    pos = builder_pos(t)
                else:
                    pos = road_at(1.0)
            else:
                u = smooth((t - t0) / max(1e-6, t1 - t0)) if pose in ("walk", "run", "cart", "think", "jump") else 0.0
                pos = (p0[0] + (p1[0] - p0[0]) * u, p0[1] + (p1[1] - p0[1]) * u)
            if ex.get("ride"):
                fr = smooth((t - RIDE[0]) / (RIDE[1] - RIDE[0]))
                pos = road_at(fr)
            pz = pose_of(pose, t)
            if prev is not None and t - t0 < 0.2:
                pz = DA.blend(pose_of(prev, t), pz, smooth((t - t0) / 0.2))
            air = DA.hop(t, t0, t1 - t0, 0.5) if pose == "jump" else 0.0
            return pos, face, pz, ex, air, pose
        prev = sg[4]
    return (0, 0), 1, DA.POSES["stand"], {}, 0.0, "stand"


def tau_of(t):
    if t < 6.6:
        return 111.0
    if t < 8.0:
        return 111.0 + (8.0 - 111.0) * smooth((t - 6.6) / 1.4)
    return t


# ---------------------------------------------------------------- camera
CAM = [  # t, cx, cz, S (fraction of h per world unit), k (tilt)
    (0.0, -1.0, -3.6, 0.17, 0.45), (6.5, -1.0, -3.6, 0.17, 0.45), (8.0, 1.8, 5.2, 0.13, 0.45),
    (10.0, 1.2, 6.2, 0.17, 0.45), (13.5, 1.8, 5.6, 0.12, 0.45), (16.0, 2.2, 1.6, 0.16, 0.50),
    (21.0, 0.6, 3.6, 0.115, 0.50), (26.5, 1.0, 3.0, 0.11, 0.52), (30.0, 1.8, 2.2, 0.10, 0.55),
    (35.0, 1.5, 3.2, 0.075, 0.60), (40.5, -1.0, 3.0, 0.062, 0.60), (43.5, 4.6, 7.0, 0.15, 0.45),
    (48.0, 4.6, 7.0, 0.15, 0.45), (49.5, -1.0, 2.0, 0.07, 0.60), (52.5, -1.0, 2.0, 0.07, 0.60),
    (54.0, 4.6, 7.0, 0.15, 0.45), (66.5, 4.6, 7.0, 0.15, 0.45), (68.5, -1.0, -2.0, 0.05, 0.65),
    (73.0, 5.0, -2.0, 0.045, 0.68), (77.5, 7.0, 11.0, 0.023, 0.72), (81.5, -14.0, 11.0, 0.020, 0.75),
    (86.0, 1.5, 2.0, 0.08, 0.60), (88.8, 1.5, 2.0, 0.08, 0.60), (90.0, -14.0, 11.0, 0.020, 0.78),
    (99.0, -14.0, 11.0, 0.020, 0.78), (100.0, -14.0, -17.0, 0.0068, 0.80), (104.0, 41.0, -17.0, 0.0068, 0.80),
    (108.0, 41.0, 66.0, 0.0028, 0.85), (110.8, 41.0, 66.0, 0.0028, 0.85), (112.0, -1.0, -3.6, 0.17, 0.45),
    (114.0, -1.0, -3.6, 0.17, 0.45), (116.0, 41.0, 66.0, 0.0027, 0.85), (126.0, 41.0, 66.0, 0.0027, 0.85),
    (129.0, 41.0, 66.0, 0.0024, 1.0), (139.5, 41.0, 66.0, 0.0024, 1.0), (143.0, 1.6, 6.2, 0.15, 0.45),
    (T_END, 1.6, 6.2, 0.15, 0.45),
]


def camera(t):
    for (t0, *a), (t1, *b) in zip(CAM, CAM[1:]):
        if t < t1:
            u = smooth((t - t0) / (t1 - t0))
            cx, cz, S, k = (a[i] + (b[i] - a[i]) * u for i in range(4))
            S = math.exp(math.log(a[2]) + (math.log(b[2]) - math.log(a[2])) * u)
            return cx, cz, S, k
    return CAM[-1][1:]


# ---------------------------------------------------------------- render
def simulate():
    return {"nf": int(round(T_END * FPS))}


class Scene:
    def __init__(self, layout, sim):
        self.L, self.sim = layout, sim
        self.canvas = Canvas(layout.w, layout.h, studio.render_scale())

    def draw(self, f, rule):
        L, c = self.L, self.canvas
        w, h = L.w, L.h
        t = f * DT
        tau = tau_of(t)
        ctx = c.ctx
        cx, cz, Sf, k = camera(t)
        S = Sf * h
        Y0 = h * 0.60

        def G(x, z, y=0.0):
            return w / 2 + (x - cx) * S, Y0 - (z - cz) * S * k - y * S

        # sky + ground
        g = cairo.LinearGradient(0, 0, 0, h)
        g.add_color_stop_rgb(0, 0.05, 0.05, 0.12)
        g.add_color_stop_rgb(1, 0.02, 0.02, 0.05)
        ctx.set_source(g)
        ctx.paint()
        for i in range(40):                                        # stars
            c.circle((i * 211.0) % w, (i * 97.0) % (h * 0.35), 1.5, (0.9, 0.9, 1.0), alpha=0.35)
        hz_y = Y0 - (400 - cz) * S * k
        ctx.rectangle(0, max(0.0, min(h, hz_y)), w, h)
        ctx.set_source_rgb(0.045, 0.06, 0.07)
        ctx.fill()
        # pens (ground), fences
        for i, (x0, z0, s) in enumerate(SQ):
            b0, b1 = BUILD[i]
            pr = 1.0 if tau >= b1 else (0.0 if tau < b0 else (tau - b0) / (b1 - b0))
            if pr <= 0:
                continue
            corners = [(x0, z0), (x0 + s, z0), (x0 + s, z0 + s), (x0, z0 + s), (x0, z0)]
            if pr >= 1:
                ctx.move_to(*G(x0, z0))
                for q in corners[1:]:
                    ctx.line_to(*G(*q))
                ctx.close_path()
                ctx.set_source_rgba(0.10, 0.16, 0.11, 0.9)
                ctx.fill()
            per = 4 * s * pr                                       # fence drawn around the perimeter while hammering
            pts, acc = [G(x0, z0)], 0.0
            pts_top = [G(x0, z0, 0.3)]
            for a, b in zip(corners, corners[1:]):
                L_ = s
                if acc + L_ <= per:
                    pts.append(G(*b))
                    pts_top.append(G(*b, 0.3))
                    acc += L_
                else:
                    u = (per - acc) / L_
                    e = (a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u)
                    pts.append(G(*e))
                    pts_top.append(G(*e, 0.3))
                    break
            fw = max(1.0, min(4.0, S * 0.04))
            c.polylines([pts], (0.55, 0.40, 0.25), width=fw, alpha=0.9)
            if 0.3 * S > 2:
                c.polylines([pts_top], (0.75, 0.55, 0.32), width=fw, alpha=0.9)
        # the road (golden spiral)
        n = road_visible(tau)
        if n >= 2:
            pts = [G(x, z) for x, z in ROAD_PTS[:n]]
            c.polylines([pts], GOLD, width=max(2.0, S * 0.35), alpha=0.25)
            c.polylines([pts], GOLD, width=max(1.5, S * 0.12), alpha=0.95)
        # sprites, back to front
        sprites = []
        sprites.append((HOUSE[1] + 0.5, "house", None))
        sprites.append((BOARD[1] + 0.3, "board", None))
        (dx, dz), face, pose, ex, air, pname = dot_state(t)
        if not ex.get("hide"):
            sprites.append((dz, "dot", None))
        for r in RABBITS:
            if tau >= r["born"] and not (r["pair"] == 0 and tau < 18.6):
                sprites.append((r["z"], "rabbit", r))
        sprites.sort(key=lambda s_: -s_[0])
        for _, kind, obj in sprites:
            if kind == "house":
                self.house(G, S, t, tau)
            elif kind == "board":
                self.board(G, S, t)
            elif kind == "rabbit":
                self.rabbit(G, S, obj, tau)
            else:
                self.dot(G, S, t, (dx, dz), face, pose, ex, air, pname)
        # props that sit on top of everything
        if 0.0 <= t < 6.6 or 110.5 <= t < 113.0:
            self.crowd(G, S, t)
        if t >= 32.6 and t < 35.0:
            self.thought(G, S, t, dx, dz)
        if 49.0 <= t < 53.0:
            self.highlight(G, S, t)
        if 114.5 <= t < 126.5:
            self.measure(G, S, t)
        if 126.0 <= t < 140.5:
            self.wonder(G, S, t)
        if 147.0 <= t:
            self.basket_end(G, S, t)
        # rewind look
        if 6.3 <= t < 8.0:
            a = 0.6 * (1 - smooth((t - 7.6) / 0.4))
            for i in range(14):
                yy = (i * 79 + t * 900) % h
                c.lines([(0, yy, w, yy)], (1, 1, 1), width=2, alpha=0.15 * a)
            c.text_centered("11 months earlier…", h * 0.15, size=h * 0.06, color=GOLD,
                            alpha=smooth((t - 6.8) / 0.3) * (1 - smooth((t - 8.6) / 0.4)))
        elif 8.0 <= t < 9.0:
            c.text_centered("11 months earlier…", h * 0.15, size=h * 0.06, color=GOLD, alpha=1 - smooth((t - 8.4) / 0.6))
        # HUD counter
        m = month_at(tau)
        if t >= 8.6 and t < 152.0 or t < 6.6:
            c.text_centered(f"Month {m}  ·  {P[m]} pair{'s' if P[m] > 1 else ''}", h * 0.06, size=h * 0.042,
                            color=(0.95, 0.95, 1.0), alpha=0.9, cx=w * 0.17)
        if t >= 152.0:
            a = smooth((t - 152.0) / 0.8)
            c.text_centered("Dot and the Rabbits", h * 0.14, size=h * 0.08, color=GOLD, alpha=a)
            c.text_centered("to be continued…", h * 0.22, size=h * 0.045, color=WHITE, alpha=a, bold=False)
        c.watermark(L)

    # -------------------------------------------------------------- sprites
    def house(self, G, S, t, tau):
        c = self.canvas
        ctx = c.ctx
        x, z = HOUSE
        wd, ht = 2.6, 2.0
        bl = G(x - wd / 2, z)
        tr = G(x + wd / 2, z, ht)
        ctx.rectangle(bl[0], tr[1], tr[0] - bl[0], bl[1] - tr[1])
        ctx.set_source_rgb(0.25, 0.22, 0.32)
        ctx.fill()
        roof = [G(x - wd / 2 - 0.2, z, ht), G(x, z, ht + 1.1), G(x + wd / 2 + 0.2, z, ht)]
        ctx.move_to(*roof[0])
        for p in roof[1:]:
            ctx.line_to(*p)
        ctx.close_path()
        ctx.set_source_rgb(0.55, 0.25, 0.22)
        ctx.fill()
        open_ = 10.4 <= t < 11.2
        d0, d1 = G(x - 0.35, z), G(x + 0.35, z, 1.3)
        ctx.rectangle(d0[0], d1[1], d1[0] - d0[0], d0[1] - d1[1])
        ctx.set_source_rgb(*((0.95, 0.85, 0.5) if open_ else (0.45, 0.30, 0.20)))
        ctx.fill()
        w0, w1 = G(x + 0.65, z, 0.9), G(x + 1.1, z, 1.45)          # lit window
        ctx.rectangle(w0[0], w1[1], w1[0] - w0[0], w0[1] - w1[1])
        ctx.set_source_rgb(0.95, 0.82, 0.45)
        ctx.fill()
        # the calendar on the wall: flips at every month
        m = month_at(tau)
        flip = min(1.0, min(abs(tau - tm) for tm in MONTH_T[1:]) / 0.18) if tau > 9 else 1.0
        c0, c1 = G(x - 1.15, z, 0.85), G(x - 0.55, z, 1.55)
        hgt = (c0[1] - c1[1]) * flip
        if c1[0] - c0[0] > 4:
            ctx.rectangle(c0[0], c0[1] - hgt, c1[0] - c0[0], hgt)
            ctx.set_source_rgb(0.95, 0.95, 0.97)
            ctx.fill()
            if flip > 0.5 and S > 30:
                c.text_centered("MONTH", c1[1] + (c0[1] - c1[1]) * 0.3, size=S * 0.11, color=(0.6, 0.15, 0.15),
                                cx=(c0[0] + c1[0]) / 2)
                c.text_centered(str(m), c1[1] + (c0[1] - c1[1]) * 0.85, size=S * 0.32, color=(0.1, 0.1, 0.15),
                                cx=(c0[0] + c1[0]) / 2)
        if 9.6 <= t < 12.0:                                        # the basket on the doorstep
            self.basket(G, S, x + 0.75, z - 0.35, t, babies=True)

    def board(self, G, S, t):
        c = self.canvas
        ctx = c.ctx
        x, z = BOARD
        wd, y0, y1 = 3.6, 0.6, 2.7
        a, b = G(x - wd / 2, z, y0), G(x + wd / 2, z, y1)
        for lx in (-wd / 2 + 0.3, wd / 2 - 0.3):
            c.lines([(*G(x + lx, z), *G(x + lx, z, y0))], (0.45, 0.32, 0.2), width=max(1.0, S * 0.05))
        ctx.rectangle(a[0], b[1], b[0] - a[0], a[1] - b[1])
        ctx.set_source_rgb(0.10, 0.22, 0.17)
        ctx.fill_preserve()
        ctx.set_source_rgb(0.45, 0.32, 0.2)
        ctx.set_line_width(max(1.0, S * 0.06))
        ctx.stroke()
        if S < 25:
            return
        lines = [(45.0, "1   1   2   3   5", WHITE, 0.30), (54.0, "5 + 3 = 8", GOLD, 0.30),
                 (56.5, "next = now + last month", GOLD, 0.20), (59.0, "8   13   21   34  …", WHITE, 0.30)]
        for i, (tl, txt, col, sz) in enumerate(lines):
            if t < tl:
                continue
            n = int((t - tl) * 9) + 1
            yy = y1 - 0.42 - i * 0.48
            p = G(x, z, yy)
            c.text_centered(txt[:n], p[1], size=S * sz, color=col, cx=p[0], bold=(i != 2))
        if t >= 50.5 and t < 66.0:
            p = G(x, z, y0 + 0.08)
            c.text_centered("everyone now + a baby pair for each grown-up pair", p[1], size=S * 0.1,
                            color=(0.8, 0.85, 0.9), cx=p[0], bold=False)

    def rabbit(self, G, S, r, tau):
        c = self.canvas
        ctx = c.ctx
        age = tau - r["born"]
        grown = smooth((tau - r["grow"]) / 0.6)
        sc = (0.55 + 0.45 * grown) * min(1.0, age / 0.2 + 0.2) * (1 + 0.3 * math.exp(-age / 0.12))
        hop = abs(math.sin(tau * 3.0 + r["ph"])) * 0.12 * sc
        x, z = r["x"] + 0.15 * math.sin(tau * 0.4 + r["ph"]), r["z"]
        px, py = G(x, z, hop)
        sz = S * 0.42 * sc
        if sz < 0.8:
            return
        col = (0.95, 0.95, 0.97) if grown > 0.5 else (0.62, 0.62, 0.68)
        if sz < 3:
            c.circle(px, py - sz * 0.3, max(0.8, sz * 0.4), col)
            return
        fc = r["face"]
        ctx.save()
        ctx.translate(px, py - sz * 0.32)
        ctx.scale(1.0, 0.62)
        ctx.arc(0, 0, sz * 0.42, 0, 2 * math.pi)
        ctx.restore()
        ctx.set_source_rgb(*col)
        ctx.fill()
        hx, hy = px + fc * sz * 0.35, py - sz * 0.62
        c.circle(hx, hy, sz * 0.22, col)
        for e in (-0.06, 0.08):
            ctx.save()
            ctx.translate(hx + fc * e * sz, hy - sz * 0.3)
            ctx.scale(0.35, 1.0)
            ctx.arc(0, 0, sz * 0.2, 0, 2 * math.pi)
            ctx.restore()
            ctx.set_source_rgb(*col)
            ctx.fill()
        c.circle(hx + fc * sz * 0.08, hy - sz * 0.03, max(0.8, sz * 0.04), (0.1, 0.1, 0.15))
        if grown > 0.5:
            c.circle(hx - fc * sz * 0.12, hy + sz * 0.17, max(1.0, sz * 0.06), GOLD)

    def basket(self, G, S, x, z, t, babies=False, y=0.0):
        c = self.canvas
        ctx = c.ctx
        a, b = G(x - 0.35, z, y), G(x + 0.35, z, y + 0.32)
        ctx.rectangle(a[0], b[1], b[0] - a[0], a[1] - b[1])
        ctx.set_source_rgb(0.65, 0.45, 0.25)
        ctx.fill()
        if babies:
            for k in (-0.12, 0.12):
                p = G(x + k, z, y + 0.38 + 0.03 * math.sin(t * 6 + k * 9))
                c.circle(p[0], p[1], S * 0.09, (0.62, 0.62, 0.68))
                c.circle(p[0] - S * 0.03, p[1] - S * 0.11, S * 0.03, (0.62, 0.62, 0.68))

    def dot(self, G, S, t, pos, face, pose, ex, air, pname):
        c = self.canvas
        ctx = c.ctx
        x, z = pos
        gx, gy = G(x, z)
        X = lambda xx: gx + (xx - x) * S              # noqa: E731
        Y = lambda yy: gy - yy * S                    # noqa: E731
        if pname == "faint":
            fall = smooth((t - 151.0) / 0.5)
            ctx.save()
            ctx.translate(gx, gy)
            ctx.rotate(-math.pi / 2 * fall * face)
            ctx.translate(-gx, -gy)
        if S * 0.05 < 0.6:
            c.circle(gx, gy - S * 0.5, 2.0, BLUE)
            if pname == "faint":
                ctx.restore()
            return
        hands, head = DA.draw_puppet(ctx, X, Y, S, x, 0.0, face, pose, ex.get("mouth", "smile"), ex.get("eyes", "open"),
                                     t=t, airborne=air)
        if pname == "faint":
            ctx.restore()
        hf = hands["af"]
        if ex.get("hammer"):
            c.lines([(X(hf[0]), Y(hf[1]), X(hf[0] + face * 0.05), Y(hf[1] + 0.3))], (0.55, 0.4, 0.25), width=S * 0.04)
            c.lines([(X(hf[0] - 0.08), Y(hf[1] + 0.3), X(hf[0] + 0.16), Y(hf[1] + 0.3))], (0.7, 0.72, 0.8), width=S * 0.08)
        if ex.get("basket"):
            self.basket(G, S, hf[0], 0, t, babies=t < 18.5, y=hf[1] - 0.2) if False else None
            bx, by = X(hf[0] + face * 0.1), Y(hf[1] - 0.05)
            ctx.rectangle(bx - S * 0.3, by - S * 0.15, S * 0.6, S * 0.3)
            ctx.set_source_rgb(0.65, 0.45, 0.25)
            ctx.fill()
            if t < 18.4:
                for k in (-0.1, 0.1):
                    c.circle(bx + k * S, by - S * 0.2 + 0.02 * S * math.sin(t * 6 + k * 9), S * 0.08, (0.62, 0.62, 0.68))
        if ex.get("note") and 12.2 <= t < 14.0:
            nx, ny = X(x + face * 1.6), Y(1.9)
            ctx.rectangle(nx - S * 1.45, ny - S * 0.42, S * 2.9, S * 0.7)
            ctx.set_source_rgb(0.97, 0.95, 0.88)
            ctx.fill()
            c.text_centered("please take care of us ♥", ny + S * 0.07, size=S * 0.24, color=(0.3, 0.2, 0.25), cx=nx)
        if ex.get("book"):
            bx, by = X(hf[0]), Y(hf[1] + 0.05)
            ctx.rectangle(bx - S * 0.15, by - S * 0.12, S * 0.3, S * 0.22)
            ctx.set_source_rgb(0.75, 0.3, 0.3)
            ctx.fill()
        if ex.get("book_drop"):
            u = smooth((t - 26.5) / 0.4)
            bx, by = X(x + 0.4), Y(0.6 * (1 - u) + 0.05)
            ctx.rectangle(bx - S * 0.15, by - S * 0.12, S * 0.3, S * 0.12)
            ctx.set_source_rgb(0.75, 0.3, 0.3)
            ctx.fill()
        if ex.get("chalk"):
            c.circle(X(hf[0]), Y(hf[1]), S * 0.035, (1, 1, 1))
        if ex.get("chalk_drop"):
            u = min(1.0, (t - 64.5) / 0.35)
            c.circle(X(x + face * 0.55), Y(1.4 * (1 - u * u) + 0.03), S * 0.035, (1, 1, 1))
        if ex.get("cart"):
            cx0 = X(hf[0] + face * 0.45)
            cy0 = Y(0.45)
            if ex.get("ride"):
                cx0, cy0 = X(x), Y(0.1)
            ctx.rectangle(cx0 - S * 0.4, cy0 - S * 0.3, S * 0.8, S * 0.35)
            ctx.set_source_rgb(0.5, 0.35, 0.22)
            ctx.fill()
            for k in (-0.25, 0.0, 0.25):
                c.circle(cx0 + k * S, cy0 - S * 0.35, S * 0.07, (1.0, 0.55, 0.15))
            for k in (-0.25, 0.25):
                c.circle(cx0 + k * S, cy0 + S * 0.08, S * 0.08, (0.2, 0.2, 0.25))
        if ex.get("sweat"):
            for k in range(2):
                ph = (t * 1.6 + k * 0.5) % 1.0
                c.circle(head[0] and X(head[0] - face * 0.12), Y(head[1] + 0.05 - ph * 0.3), S * 0.03, (0.6, 0.8, 1.0),
                         alpha=1 - ph)
        if ex.get("bang"):
            c.text_centered("!", Y(1.55), size=S * 0.45, color=GOLD, cx=X(x))
        if ex.get("bulb"):
            bx, by = X(head[0]), Y(head[1] + 0.45)
            c.glow(bx, by, S * 0.12, GOLD, strength=0.9, reach=3)
            c.circle(bx, by, S * 0.1, (1.0, 0.92, 0.55))
        if ex.get("tape") and 114.5 <= t < 116.0:
            c.lines([(X(hf[0]), Y(hf[1]), X(hf[0] + 0.6), Y(hf[1]))], GOLD, width=S * 0.03)

    # -------------------------------------------------------------- set pieces
    def crowd(self, G, S, t):
        """A pile of rabbits around buried Dot (hook + the catch-up shot) and flying carrots."""
        c = self.canvas
        bx, bz = BURIED
        for i in range(70):
            a = _h(i, 11) * 6.28
            r = 0.2 + 1.6 * _h(i, 12) ** 0.7
            x, z = bx + r * math.cos(a), bz - 0.2 + r * math.sin(a) * 0.6
            y = 0.25 * _h(i, 13) * (r < 0.9)
            fake = dict(x=x, z=z, born=-10, grow=-10, face=1 if _h(i, 14) > 0.5 else -1, ph=_h(i, 15) * 6.28, pair=999)
            if z < bz + 0.3:
                self.rabbit(lambda xx, zz, yy=0.0: G(xx, zz, yy + y), S, fake, t)
        for i in range(8):                                         # carrots flying
            ph = (t * 0.7 + i / 8) % 1.0
            x = bx - 3 + 6 * ph + _h(i, 16)
            y = 2.5 * 4 * ph * (1 - ph)
            p = G(x, bz + 1.0 * _h(i, 17), y)
            c.circle(p[0], p[1], S * 0.07, (1.0, 0.55, 0.15))
            c.lines([(p[0], p[1] - S * 0.07, p[0] - S * 0.04, p[1] - S * 0.17)], (0.4, 0.8, 0.35), width=S * 0.03)

    def thought(self, G, S, t, dx, dz):
        c = self.canvas
        ctx = c.ctx
        u = smooth((t - 32.6) / 0.3) * (1 - smooth((t - 34.7) / 0.3))
        hx, hy = G(dx, dz, 1.4)
        bx, by = hx + S * 1.3, hy - S * 1.0
        for k, r in enumerate((0.06, 0.1)):
            c.circle(hx + S * (0.3 + 0.35 * k), hy - S * (0.25 + 0.3 * k), S * r, (0.95, 0.95, 1.0), alpha=u)
        ctx.save()
        ctx.translate(bx, by)
        ctx.scale(1.0, 0.7)
        ctx.arc(0, 0, S * 0.95, 0, 2 * math.pi)
        ctx.restore()
        ctx.set_source_rgba(0.95, 0.95, 1.0, u)
        ctx.fill()
        q = S * 0.28                                               # the 1×2 ranch + a 2×2 square sliding onto the long side
        x0, y0 = bx - q, by + q * 0.4
        ctx.rectangle(x0, y0 - q, q, q)
        ctx.rectangle(x0 + q, y0 - q, q, q)
        ctx.set_source_rgba(0.3, 0.5, 0.35, u)
        ctx.fill()
        sl = smooth((t - 33.2) / 0.8)
        ctx.rectangle(x0, y0 - q - 2 * q - (1 - sl) * q * 1.2, 2 * q, 2 * q)
        ctx.set_source_rgba(0.85, 0.65, 0.25, 0.8 * u)
        ctx.fill()

    def highlight(self, G, S, t):
        """While planning: the grown-up pairs glow gold (3), everyone glows white (5)."""
        c = self.canvas
        for r in RABBITS:
            if r["born"] > 49.0:
                continue
            adult = r["grow"] <= 49.0
            p = G(r["x"], r["z"], 0.2)
            if t < 51.0 and adult:
                c.glow(p[0], p[1], S * 0.18, GOLD, strength=0.9, reach=2.5)
            if t >= 51.0:
                c.glow(p[0], p[1], S * 0.18, (1, 1, 1), strength=0.6, reach=2.5)
        lab = "3 grown-up pairs" if t < 51.0 else "5 pairs now"
        p = G(1.0, 6.0, 1.0)
        c.text_centered(lab, p[1], size=S * 0.5, color=GOLD if t < 51 else WHITE, cx=p[0])

    def measure(self, G, S, t):
        c = self.canvas
        x0, z0, x1, z1 = BOXES[10]
        u = smooth((t - 115.0) / 1.5)
        c.lines([(*G(x0, z0 - 6), *G(x0 + (x1 - x0) * u, z0 - 6))], GOLD, width=5)
        u2 = smooth((t - 116.5) / 1.5)
        c.lines([(*G(x1 + 6, z0), *G(x1 + 6, z0 + (z1 - z0) * u2))], GOLD, width=5)
        h = self.L.h
        if t >= 117.5:
            c.text_centered("144 ÷ 89 = 1.618…", h * 0.80, size=h * 0.06, color=WHITE, alpha=smooth((t - 117.5) / 0.3))
        if t >= 120.0:
            bx0, bz0, bx1, bz1 = BOXES[9]
            ctx = c.ctx
            a, b = G(bx0, bz0), G(bx1, bz1)
            ctx.rectangle(min(a[0], b[0]), min(a[1], b[1]), abs(b[0] - a[0]), abs(b[1] - a[1]))
            ctx.set_source_rgba(*GOLD, 0.8 * smooth((t - 120.0) / 0.3))
            ctx.set_line_width(4)
            ctx.stroke()
            c.text_centered("89 ÷ 55 = 1.618…", h * 0.87, size=h * 0.05, color=WHITE, alpha=smooth((t - 120.0) / 0.3))
        if t >= 123.0:
            pop = math.exp(-(t - 123.0) / 0.2)
            c.text_centered("φ = 1.618…", h * 0.16, size=h * 0.1 * (1 + 0.2 * pop), color=GOLD)

    def wonder(self, G, S, t):
        """From above: the road is a golden spiral — and the same spiral in a sunflower, a shell, a galaxy."""
        c = self.canvas
        ctx = c.ctx
        w, h = self.L.w, self.L.h
        ex, ez = 0.0, 0.0                                          # the spiral's eye (near the first pen)
        for (cx_, cz_), r, _, _ in ARCS[:3]:
            ex += cx_ / 3
            ez += cz_ / 3
        e = G(ex, ez)
        glow = smooth((t - 126.0) / 1.0)
        pts = [G(x, z) for x, z in ROAD_PTS[:road_visible(111.0)]]
        c.polylines([pts], GOLD, width=12, alpha=0.3 * glow)
        R = h * 0.42
        for k, (t0, kind) in enumerate(((129.0, "sunflower"), (132.5, "shell"), (136.0, "galaxy"))):
            a = smooth((t - t0) / 0.8) * (1 - smooth((t - (t0 + 3.0)) / 0.8))
            if a <= 0.01:
                continue
            ctx.save()
            ctx.rectangle(0, 0, w, h)
            ctx.set_source_rgba(0.02, 0.02, 0.05, 0.75 * a)
            ctx.fill()
            ctx.restore()
            cxs, cys = w / 2, h * 0.5
            if kind == "sunflower":
                for i in range(1, 700):
                    rr = R * 0.85 * math.sqrt(i / 700)
                    th = i * math.radians(137.508)
                    c.circle(cxs + rr * math.cos(th), cys + rr * math.sin(th), 3.0 + 3 * i / 700,
                             (0.85, 0.55, 0.15) if i < 600 else (1.0, 0.8, 0.2), alpha=a)
            elif kind == "shell":
                pts = []
                for i in range(400):
                    th = i / 400 * 5 * math.pi
                    rr = R * 0.9 * PHI ** (-(5 * math.pi - th) / (math.pi / 2))
                    pts.append((cxs + rr * math.cos(th), cys + rr * math.sin(th)))
                c.polylines([pts], (0.95, 0.85, 0.7), width=8, alpha=a)
                c.polylines([pts], (0.7, 0.5, 0.35), width=3, alpha=a)
            else:
                for arm in range(2):
                    for i in range(500):
                        th = i / 500 * 3.2 * math.pi + arm * math.pi
                        rr = R * 0.07 * PHI ** (th / (math.pi / 2)) * 0.25
                        jit = (_h(i + arm * 999, 3) - 0.5) * R * 0.06
                        c.circle(cxs + rr * math.cos(th) + jit, cys + rr * math.sin(th) + jit, 1.8,
                                 (0.75, 0.8, 1.0), alpha=a * 0.9)
                c.glow(cxs, cys, R * 0.06, (1.0, 0.95, 0.8), strength=a, reach=3)
            c.text_centered({"sunflower": "a sunflower", "shell": "a snail shell", "galaxy": "a galaxy"}[kind],
                            h * 0.92, size=h * 0.045, color=WHITE, alpha=a, bold=False)
        _ = e

    def basket_end(self, G, S, t):
        c = self.canvas
        x, z = HOUSE[0] - 2.0, HOUSE[1] - 0.45
        drop = smooth((t - 147.0) / 0.25)
        self.basket(G, S, x, z, t, babies=True, y=1.2 * (1 - drop))
        if t >= 148.5:
            p = G(x, z, 1.1)
            a = smooth((t - 148.5) / 0.3)
            c.text_centered("1, 1, …", p[1], size=S * 0.45, color=GOLD, alpha=a, cx=p[0])


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
    rng = np.random.default_rng(31)

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
        f = hz(m) * (1 + 1.5 * tv / 0.09)
        add(t0, np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tv / 0.04), g)

    def ding(t0, base=84):
        for m in (base, base + 4, base + 7):
            add(t0, tone(hz(m), 1.2, 0.4, ((1, 1.0), (2.76, 0.25))), 0.06)

    def knock(t0):
        for k in range(2):
            add(t0 + 0.22 * k, tone(110, 0.12, 0.03, ((1, 1.0), (2.3, 0.5))) + 0.3 * noise(0.12, 0.02), 0.25)

    # music: a plucked loop whose density follows the story (calm → busy → calm pad for the wonder)
    beat = 0.5
    prog = [(48, (60, 64, 67)), (45, (60, 64, 69)), (41, (60, 65, 69)), (43, (59, 62, 67))]
    tb, b = 8.5, 0
    while tb < T_END - 3:
        busy = 2 if (68 <= tb < 100 or tb < 6.6) else (1 if 100 <= tb < 126 else 0)
        calm = 126 <= tb < 141
        root, ch = prog[b % 4]
        if calm:
            tv = np.arange(int(4 * beat * SR)) / SR
            pad = sum(np.sin(2 * np.pi * hz(m) * tv) for m in ch) / 3 * np.clip(tv / 0.5, 0, 1) * np.clip((4 * beat - tv) / 0.5, 0, 1)
            add(tb, pad, 0.05)
        else:
            add(tb, tone(hz(root), 1.0, 0.3), 0.08)
            sub = 8 if busy == 0 else 16
            for e in range(sub):
                m = ch[(e * 2) % 3] + (12 if e % 4 == 3 else 0)
                add(tb + e * 4 * beat / sub, tone(hz(m), 0.25, 0.07, ((1, 1.0), (2, 0.5), (3, 0.2))), 0.026 + 0.006 * busy)
            if busy == 2:
                for q in range(4):
                    add(tb + q * beat, tone(55, 0.2, 0.06), 0.18)
        tb += 4 * beat
        b += 1
    tb = 0.0                                                         # the hook: chaotic fast loop
    while tb < 6.3:
        add(tb, tone(hz(72 + (int(tb * 8) % 5) * 2), 0.12, 0.05), 0.05)
        tb += 0.125
    add(6.3, noise(0.5, 0.2) * np.sin(np.linspace(0, 40, int(0.5 * SR))), 0.25)        # record scratch
    tv = np.arange(int(1.3 * SR)) / SR                                                  # rewind
    add(6.7, np.sin(2 * np.pi * np.cumsum(900 - 600 * tv / 1.3 + 200 * np.sin(2 * np.pi * 9 * tv)) / SR) * 0.5, 0.06)
    knock(10.0)
    add(10.4, tone(220, 0.4, 0.2, ((1, 1.0), (1.5, 0.4))), 0.05)
    pop(11.0, 84)
    for i, (b0, b1) in enumerate(BUILD):                                                # hammering
        k = b0
        while k < b1:
            add(k, tone(170 + 20 * (i % 3), 0.08, 0.025, ((1, 1.0), (3.2, 0.4))) + 0.2 * noise(0.08, 0.02),
                0.10 if i < 8 else 0.05)
            k += 0.21 if i < 4 else 0.14
        ding(b1, 79 + (i % 4) * 2)
    for m in range(1, len(MONTH_T)):                                                    # calendar flips + births
        add(MONTH_T[m], noise(0.15, 0.05), 0.12)
        nb = P[m] - P[m - 1]
        for r in range(min(nb, 20)):
            pop(MONTH_T[m] + 0.3 + 0.8 * r / max(1, min(nb, 20)), 74 + (r % 6) * 2, 0.07)
    for k in range(5):                                                                 # chalk
        add(44.6 + 0.6 * k, noise(0.35, 0.3) * (0.5 + 0.5 * np.sin(np.linspace(0, 60, int(0.35 * SR)))), 0.03)
    for t0 in (54.0, 56.5):
        add(t0, noise(0.8, 0.5) * (0.5 + 0.5 * np.sin(np.linspace(0, 120, int(0.8 * SR)))), 0.03)
    ding(56.6)
    for k in range(4):
        add(59.0 + 0.9 * k, noise(0.4, 0.3), 0.03)
    add(64.5, tone(2400, 0.05, 0.01), 0.1)                                              # chalk drops
    for t0, t1 in ((70.8, 73.0), (75.6, 77.5), (80.0, 81.5), (84.0, 86.0), RIDE):        # cart rattle
        k = t0
        while k < t1:
            add(k, noise(0.05, 0.015), 0.05)
            k += 0.07
    ding(88.0, 88)                                                                       # light bulb
    add(89.0, tone(hz(60), 4.0, 2.0, ((1, 1.0), (2, 0.3))), 0.04)
    for k in range(12):
        pop(93.3 + 0.48 * k, 72 + k, 0.08)
    add(110.6, noise(0.5, 0.2) * np.sin(np.linspace(0, 40, int(0.5 * SR))), 0.18)     # catch-up scratch
    tv = np.arange(int(1.4 * SR)) / SR                                                   # tape measure zips
    for t0 in (115.0, 116.5):
        add(t0, noise(1.4, 1.0) * np.clip(1.4 - tv, 0, 1), 0.04)
    ding(117.5)
    ding(120.0)
    ding(123.0, 79)
    knock(146.6)
    add(147.0, tone(90, 0.3, 0.08), 0.2)
    ding(148.5, 72)
    add(151.2, tone(60, 0.5, 0.15) + 0.4 * noise(0.5, 0.1), 0.3)                       # faint thud
    ding(152.0, 72)
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
    print(f"[{SCENE}] {T_END:.0f}s")
    _worker("horizontal", sim, label, "")


if __name__ == "__main__":
    main()
