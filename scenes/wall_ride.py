"""WALL RIDE v2 — "How can a car drive UP a wall?" — the ramp + thruster demo, explained with (approximate) numbers.

Matches the real demo's motion: the car starts at the foot of a ~25 m wall and climbs SLOWLY (~25 km/h), so
momentum can't hold it — a fan must suck it to the wall. The top curls ~40° past vertical: the car is upside down at
the lip. Off the top it keeps flipping (nose-down along the wall), twists 90° to face the camera, falls, and a
rocket-style burn of downward jets lands it in a cloud; it then drifts a loop back to the start (seamless).
3-D low-poly car + ramp (our own model, no footage, no logos), 3/4 camera that follows the car.
Estimated numbers (labelled on screen): m = 2 t, μ = 1, wall 25 m, 25 km/h, fan area 4 m², gas v_e ≈ 700 m/s.
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

SCENE = "wall_ride"
G, MASS, MU = 9.81, 2000.0, 1.0
V = 6.0                                   # climb speed, m/s (≈ 22 km/h)
R1, R2 = 5.0, 40.0                        # foot curve, then one long arc that leans back over the top
TH_KNEE, TH_TOP = math.radians(80), math.radians(130)
S_A = R1 * TH_KNEE
S_END = S_A + R2 * (TH_TOP - TH_KNEE)
X_START = -6.0
A_BURN = 12.0                             # burn deceleration (m/s²) → 2.2 g felt
FAN_AREA = 4.0
VE = 700.0
RATE_GROUND, RATE_AIR = 1.0, 0.7          # real time on the wall, slow motion in the air
DRIFT_Z = -7.0                            # it lands beside the ramp (screen-left, like the video)
DCAM = 42.0                               # perspective: camera distance (m)
S_HOOK = S_A + R2 * (math.radians(117) - TH_KNEE)   # frame 0: the car hangs upside down, ~35 m up
HOOK_ZOOM, HOOK_T = 0.055, 2.2                       # close-up scale at frame 0, seconds to pull back to the wide shot
NEED_TOP = MASS * G * (math.sin(TH_TOP) / MU - math.cos(TH_TOP)) - MASS * V * V / R2
GOLD, CYAN, PINK, LIME, BLUE = (1, .82, .4), (.4, .85, 1), (1, .4, .6), (.55, 1, .55), (.45, .7, 1)


# ---------------------------------------------------------------- geometry + rotations
def ramp(s):
    """Point on the riding surface (x, y) and the tangent angle θ at arc length s."""
    if s <= 0:
        return np.array([s, 0.0]), 0.0
    if s <= S_A:
        th = s / R1
        return np.array([R1 * math.sin(th), R1 - R1 * math.cos(th)]), th
    th = TH_KNEE + (s - S_A) / R2
    pa = np.array([R1 * math.sin(TH_KNEE), R1 - R1 * math.cos(TH_KNEE)])
    return pa + R2 * np.array([math.sin(th) - math.sin(TH_KNEE), math.cos(TH_KNEE) - math.cos(th)]), th


def rot(axis, ang):
    a = np.asarray(axis, float) / np.linalg.norm(axis)
    K = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
    return np.eye(3) + math.sin(ang) * K + (1 - math.cos(ang)) * (K @ K)


def frame_from(f, u):
    f = np.asarray(f, float)
    f /= np.linalg.norm(f)
    u = np.asarray(u, float)
    u = u - f * (u @ f)
    u /= np.linalg.norm(u)
    return np.column_stack([f, u, np.cross(f, u)])


def m2q(M):
    tr = M[0, 0] + M[1, 1] + M[2, 2]
    if tr > 0:
        s = math.sqrt(tr + 1) * 2
        q = [0.25 * s, (M[2, 1] - M[1, 2]) / s, (M[0, 2] - M[2, 0]) / s, (M[1, 0] - M[0, 1]) / s]
    elif M[0, 0] > M[1, 1] and M[0, 0] > M[2, 2]:
        s = math.sqrt(1 + M[0, 0] - M[1, 1] - M[2, 2]) * 2
        q = [(M[2, 1] - M[1, 2]) / s, 0.25 * s, (M[0, 1] + M[1, 0]) / s, (M[0, 2] + M[2, 0]) / s]
    elif M[1, 1] > M[2, 2]:
        s = math.sqrt(1 + M[1, 1] - M[0, 0] - M[2, 2]) * 2
        q = [(M[0, 2] - M[2, 0]) / s, (M[0, 1] + M[1, 0]) / s, 0.25 * s, (M[1, 2] + M[2, 1]) / s]
    else:
        s = math.sqrt(1 + M[2, 2] - M[0, 0] - M[1, 1]) * 2
        q = [(M[1, 0] - M[0, 1]) / s, (M[0, 2] + M[2, 0]) / s, (M[1, 2] + M[2, 1]) / s, 0.25 * s]
    return np.array(q)


def q2m(q):
    w, x, y, z = q / np.linalg.norm(q)
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


def slerp(a, b, t):
    d = a @ b
    if d < 0:
        b, d = -b, -d
    if d > 0.9995:
        return (a + t * (b - a)) / np.linalg.norm(a + t * (b - a))
    th = math.acos(d)
    return (math.sin((1 - t) * th) * a + math.sin(t * th) * b) / math.sin(th)


def ramp_pose(th):
    return frame_from([math.cos(th), math.sin(th), 0], [-math.sin(th), math.cos(th), 0])


def smoother(u):
    u = min(1.0, max(0.0, u))
    return u * u * u * (u * (6 * u - 15) + 10)


# ---------------------------------------------------------------- the stunt, per video frame
def build():
    fr = []
    # ground + climb at constant speed
    s = X_START
    while s < S_END:
        p, th = ramp(s)
        if s < 0:
            need = 0.0
        else:
            r = R1 if s <= S_A else R2
            need = max(0.0, MASS * G * math.sin(th) / MU - MASS * G * math.cos(th) - MASS * V * V / r)
        warp = 1.0 - 0.75 * math.exp(-((s - S_HOOK) / 1.8) ** 2)       # slow motion around the hook moment
        fr.append(dict(ph=0 if s < 0 else 1, pos=np.array([p[0], p[1], 0.0]), M=ramp_pose(th), v=V, s=s, th=th,
                       fan=need, gf=1.0, thrust=0.0, rate=RATE_GROUND * warp))
        s += V * RATE_GROUND * warp * DT
    # air: leaves the lip moving along the tangent, keeps flipping, twists to face the camera, burn, land
    p0, th0 = ramp(S_END)
    vx, vy = V * math.cos(th0), V * math.sin(th0)
    t_up = vy / G
    y_peak = p0[1] + vy * t_up / 2
    d1 = y_peak * A_BURN / (G + A_BURN)
    t1 = math.sqrt(2 * d1 / G)
    v1 = G * t1
    t2 = v1 / A_BURN
    TA = t_up + t1 + t2
    M0 = ramp_pose(th0)
    t_roll = t_up + 0.55                                  # side jets roll it 180° (a barrel roll) …
    t_level = t_up + 1.25                                 # … then it pitches level, nose away from the wall
    M_roll = rot(M0[:, 0], math.pi) @ M0
    q_roll, q_end = m2q(M_roll), m2q(frame_from([-1, 0, 0], [0, 1, 0]))
    tau = 0.0
    while tau <= TA:
        if tau < t_up:
            y = p0[1] + vy * tau - 0.5 * G * tau * tau
            vyy, thrust, gf = vy - G * tau, 0.0, 0.0
        elif tau < t_up + t1:
            tt = tau - t_up
            y = y_peak - 0.5 * G * tt * tt
            vyy, thrust, gf = -G * tt, 0.0, 0.0
        else:
            tt = tau - t_up - t1
            y = y_peak - d1 - v1 * tt + 0.5 * A_BURN * tt * tt
            vyy, thrust, gf = -v1 + A_BURN * tt, MASS * (G + A_BURN), 1 + A_BURN / G
        u = tau / TA
        x = p0[0] + 0.6 * vx * TA * (u - 0.5 * u * u)          # side jets kill most of the drift
        z = DRIFT_Z * smoother(u)
        if tau < t_roll:
            M = rot(M0[:, 0], math.pi * smoother(tau / t_roll)) @ M0
        elif tau < t_level:
            M = q2m(slerp(q_roll, q_end, smoother((tau - t_roll) / (t_level - t_roll))))
        else:
            M = q2m(q_end)
        if tau < t_roll:
            stage = "spin"
        elif tau < t_up + t1:
            stage = "fall"
        elif tau < t_up + t1 + t2 / 2:
            stage = "burn"
        else:
            stage = "gas"
        fr.append(dict(ph=2, pos=np.array([x, max(0.0, y), z]), M=M, v=math.hypot(vx * (1 - u), vyy), s=S_END,
                       th=th0, fan=0.0, gf=gf, thrust=thrust, stage=stage))
        tau += RATE_AIR * DT
    land = fr[-1]["pos"].copy()
    land[1] = 0.0
    # settle in the gas cloud
    for j in range(int(0.6 * FPS)):
        fr.append(dict(ph=3, pos=land.copy(), M=q2m(q_end), v=0.0, s=S_END, th=0, fan=0, gf=1, thrust=0,
                       smoke=j / FPS))
    # drift loop back to frame 0 (Hermite in the ground plane): from facing the camera to facing the ramp at speed
    P0, P1 = np.array([land[0], land[2]]), np.array([X_START, 0.0])
    TL = 3.2
    T0, T1 = np.array([-16.0, 6.0]), np.array([V * RATE_GROUND * TL, 0.0])
    n = int(TL * FPS)
    for j in range(n):
        u = (j + 1) / (n + 1)
        h00, h10, h01, h11 = 2 * u ** 3 - 3 * u * u + 1, u ** 3 - 2 * u * u + u, -2 * u ** 3 + 3 * u * u, u ** 3 - u * u
        pt = h00 * P0 + h10 * T0 + h01 * P1 + h11 * T1
        d = (6 * u * u - 6 * u) * P0 + (3 * u * u - 4 * u + 1) * T0 + (-6 * u * u + 6 * u) * P1 + (3 * u * u - 2 * u) * T1
        M = frame_from([d[0], 0, d[1]], [0, 1, 0])
        fr.append(dict(ph=4, pos=np.array([pt[0], 0.0, pt[1]]), M=M, v=np.linalg.norm(d) / TL / RATE_GROUND, s=-1,
                       th=0, fan=0, gf=1, thrust=0, u=u))
    info = dict(y_peak=y_peak, TA=TA, t1=t1, t2=t2, land=land, vfree=math.sqrt(2 * G * y_peak))
    return fr, info


FR, INFO = build()
_i0 = next(i for i, st in enumerate(FR) if st["ph"] == 1 and st["s"] >= S_HOOK)
FR = FR[_i0:] + FR[:_i0]                                  # the loop starts on the most shocking moment
NF = len(FR)
T_LOOP = NF / FPS


# ---------------------------------------------------------------- camera (3/4 view, follows the car)
YAW, PITCH = math.radians(float(arg("--yaw", "68"))), math.radians(float(arg("--pitch", "-5")))
_cy, _sy, _cp, _sp = math.cos(YAW), math.sin(YAW), math.cos(PITCH), math.sin(PITCH)
HOOK_YAW = math.radians(28)                          # the hook starts from the side: the overhang + hanging car read


def set_yaw(a):
    global _cy, _sy
    _cy, _sy = math.cos(a), math.sin(a)


def hook_k(i, n):
    """1 at frame 0 (and the seam), 0 once the hook has played out — circular."""
    return 1.0 - smoother(min(i, n - i) / FPS / HOOK_T)


YAWF = [YAW + (HOOK_YAW - YAW) * hook_k(i, NF) for i in range(NF)]


def view(p):
    x, y, z = p
    x1 = x * _cy + z * _sy
    z1 = -x * _sy + z * _cy
    y2 = y * _cp - z1 * _sp
    z2 = y * _sp + z1 * _cp
    return x1, y2, z2


def camera():
    tx, ty, tz, ts = [], [], [], []
    for i_, st in enumerate(FR):
        set_yaw(YAWF[i_])
        vx_, vy_, vz_ = view(st["pos"])
        ph = st["ph"]
        if ph == 0:
            a, b, sc = vx_ + 1.0, 11.0, 0.0145
        elif ph == 1:
            k = st["s"] / S_END
            a, b, sc = vx_, 11.0 + 0.75 * max(0.0, vy_ - 6.0), 0.0145 + 0.006 * k
        elif ph == 2:
            a, b, sc = vx_, vy_ + 1.0, 0.021
        elif ph == 3:
            a, b, sc = vx_, 6.0, 0.022
        else:
            k = smoother(st["u"])
            a, b, sc = vx_, 6.0 + 5.0 * k, 0.022 - 0.0075 * k
        tx.append(a)
        ty.append(b)
        tz.append(vz_)
        ts.append(sc)
    n_ = len(FR)
    for i in range(n_):                                   # the hook: close on the car at frame 0, pull back to reveal
        d = min(i, n_ - i) / FPS                          # the height; push back in before the seam (circular)
        z = 1.0 - smoother(d / HOOK_T)
        if z > 0:
            set_yaw(YAWF[i])
            vx_, vy_, _ = view(FR[i]["pos"])
            ts[i] = ts[i] + (HOOK_ZOOM - ts[i]) * z
            tx[i] = tx[i] + (vx_ - tx[i]) * z
            ty[i] = ty[i] + (vy_ - 0.6 - ty[i]) * z
    n = len(FR)
    sig = 0.3 * FPS
    k = np.exp(-0.5 * (np.arange(-int(3 * sig), int(3 * sig) + 1) / sig) ** 2)
    k /= k.sum()

    def circ(v):
        v = np.asarray(v)
        ext = np.concatenate([v[-len(k):], v, v[:len(k)]])
        return np.convolve(ext, k, mode="same")[len(k):len(k) + n]
    return circ(tx), circ(ty), circ(tz), circ(ts)


CAMX, CAMY, CAMZ, CAMS = camera()
LIGHT = np.array([-0.45, 0.8, 0.55])
LIGHT /= np.linalg.norm(LIGHT)


def box(x0, x1, y0, y1, z0, z1, top_shrink=(0, 0, 0, 0)):
    """8 corners (optionally a tapered top: shrink x0, x1, z0, z1) → list of (4 corners, outward normal)."""
    a, b, c_, d = top_shrink
    v = [(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1),
         (x0 + a, y1, z0 + c_), (x1 - b, y1, z0 + c_), (x1 - b, y1, z1 - d), (x0 + a, y1, z1 - d)]
    v = [np.array(p, float) for p in v]
    faces = [(0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1), (3, 2, 6, 7), (0, 3, 7, 4), (1, 5, 6, 2)]
    out = []
    ctr = sum(v) / 8
    for f in faces:
        pts = [v[i] for i in f]
        n = np.cross(pts[1] - pts[0], pts[2] - pts[0])
        n /= np.linalg.norm(n) + 1e-9
        if n @ (sum(pts) / 4 - ctr) < 0:
            n = -n
        out.append((pts, n))
    return out


BODY = (0.88, 0.90, 0.95)
GLASS = (0.16, 0.22, 0.32)
PROFILE = [(-2.2, 0.30), (2.2, 0.30), (2.27, 0.45), (2.05, 0.60), (0.95, 0.76), (0.2, 1.10), (-0.9, 1.14),
           (-1.85, 0.86), (-2.27, 0.72), (-2.27, 0.38)]                 # side silhouette (x forward, y up)
GLASS_STRIPS = {4, 6}                                                 # windscreen + rear glass
WINDOW = [(0.78, 0.81), (0.17, 1.06), (-0.85, 1.09), (-1.62, 0.87)]
HW = 0.98


def _prism(profile, z0, z1, col, kind, strip_cols=None):
    """Extrude a side profile across z → faces with outward normals."""
    out = []
    ctr = np.array([np.mean([p[0] for p in profile]), np.mean([p[1] for p in profile]), (z0 + z1) / 2])
    for z, sgn in ((z0, -1), (z1, 1)):
        out.append(([np.array([x, y, z]) for x, y in profile], np.array([0, 0, sgn], float), col, kind))
    n = len(profile)
    for i in range(n):
        (xa, ya), (xb, yb) = profile[i], profile[(i + 1) % n]
        q = [np.array([xa, ya, z0]), np.array([xb, yb, z0]), np.array([xb, yb, z1]), np.array([xa, ya, z1])]
        nn = np.cross(q[1] - q[0], q[3] - q[0])
        nn /= np.linalg.norm(nn) + 1e-9
        if nn @ (sum(q) / 4 - ctr) < 0:
            nn = -nn
        cc = strip_cols.get(i, col) if strip_cols else col
        out.append((q, nn, cc, "glass" if cc is GLASS else kind))
    return out


def _wheel(xw, zw):
    ring = [(xw + 0.36 * math.cos(2 * math.pi * k / 10), 0.36 + 0.36 * math.sin(2 * math.pi * k / 10)) for k in range(10)]
    return _prism(ring, zw - 0.15, zw + 0.15, (0.07, 0.07, 0.09), "wheel")


CAR_PARTS = (_prism(PROFILE, -HW, HW, BODY, "body", {i: GLASS for i in GLASS_STRIPS})
             + [([np.array([x, y, z]) for x, y in WINDOW], np.array([0, 0, sg], float), GLASS, "window")
                for z, sg in ((-HW - 0.01, -1), (HW + 0.01, 1))]
             + [f for xw in (-1.4, 1.42) for zw in (-0.86, 0.86) for f in _wheel(xw, zw)])
LIGHTS = [((2.24, 0.5, -0.8), (2.18, 0.56, -0.35), (1, 1, .92)), ((2.18, 0.56, 0.35), (2.24, 0.5, 0.8), (1, 1, .92)),
          ((-2.28, 0.6, -0.85), (-2.28, 0.6, 0.85), (1, .2, .25))]
JETS = [(-1.4, 0.25, -0.7), (-1.4, 0.25, 0.7), (1.4, 0.25, -0.7), (1.4, 0.25, 0.7)]


def simulate():
    return {"nf": NF}


class Scene:
    def __init__(self, layout, sim):
        self.L, self.sim = layout, sim
        self.canvas = Canvas(layout.w, layout.h, studio.render_scale())
        rng = np.random.default_rng(7)
        w, h = layout.w, layout.h
        self.stars = [(rng.uniform(0, w), rng.uniform(0, h * 0.7), rng.uniform(0.8, 2.2), rng.uniform(0, 6))
                      for _ in range(70)]
        self.ramp_s = np.concatenate([np.linspace(-4, S_A, 16), np.linspace(S_A, S_END, 40)[1:]])

    def P(self, p):
        x, y, z = view(p)
        k = DCAM / max(6.0, DCAM - (z - self.cz))
        return self.L.w / 2 + (x - self.cx) * self.S * k, self.L.h * 0.50 - (y - self.cy) * self.S * k

    def quad(self, pts, col, shade_n=None, alpha=1.0, edge=None, edge_a=0.6):
        c = self.canvas
        ctx = c.ctx
        sp = [self.P(p) for p in pts]
        k = 1.0
        if shade_n is not None:
            k = 0.35 + 0.65 * max(0.0, float(shade_n @ LIGHT))
        ctx.new_path()
        ctx.move_to(*sp[0])
        for q in sp[1:]:
            ctx.line_to(*q)
        ctx.close_path()
        ctx.set_source_rgba(col[0] * k, col[1] * k, col[2] * k, alpha)
        if edge:
            ctx.fill_preserve()
            ctx.set_source_rgba(*edge, edge_a)
            ctx.set_line_width(1.6)
            ctx.stroke()
        else:
            ctx.fill()

    def draw_ramp(self):
        c = self.canvas
        Wd = 2.4
        ss = self.ramp_s
        pts = [ramp(s) for s in ss]
        for i in range(len(ss) - 1):                          # the riding surface
            (pa, tha), (pb, thb) = pts[i], pts[i + 1]
            n = np.array([-math.sin(tha), math.cos(tha), 0.0])
            q = [np.array([pa[0], pa[1], -Wd]), np.array([pb[0], pb[1], -Wd]), np.array([pb[0], pb[1], Wd]),
                 np.array([pa[0], pa[1], Wd])]
            self.quad(q, (0.62, 0.64, 0.70), n)
        for zz in (-Wd, Wd):                                 # neon edge lines + centre dashes
            line = [self.P(np.array([p[0], p[1], zz])) for p, _ in pts]
            c.polylines([line], PINK, width=7, alpha=0.25)
            c.polylines([line], PINK, width=2.5, alpha=0.95)
        dash = []
        for i in range(0, len(ss) - 1, 2):
            a_, b_ = self.P(np.array([*pts[i][0], 0.0])), self.P(np.array([*pts[i + 1][0], 0.0]))
            dash.append((a_[0], a_[1], b_[0], b_[1]))
        c.lines(dash, (1, 1, 1), width=2.5, alpha=0.8)
        tr = []                                              # the truss behind the curved wall
        back = []
        for i, (p_, th_) in enumerate(pts):
            if ss[i] < 1.0:
                continue
            n = np.array([-math.sin(th_), math.cos(th_)])
            back.append((p_ - n * 1.2, p_ - n * 3.8))
        for zz in (-Wd, Wd):
            for j in (0, 1):
                line = [self.P(np.array([b_[j][0], b_[j][1], zz])) for b_ in back]
                c.polylines([line], (0.45, 0.5, 0.65), width=2, alpha=0.5)
            for i in range(0, len(back), 3):
                a_, b_ = self.P(np.array([*back[i][0], zz])), self.P(np.array([*back[i][1], zz]))
                tr.append((a_[0], a_[1], b_[0], b_[1]))
                if i + 3 < len(back):
                    a2 = self.P(np.array([*back[i + 3][1], zz]))
                    tr.append((a_[0], a_[1], a2[0], a2[1]))
        c.lines(tr, (0.45, 0.5, 0.65), width=2, alpha=0.45)

    def draw_car(self, st, t):
        c = self.canvas
        M, pos = st["M"], st["pos"]
        faces = []
        for f, n, col, kind in CAR_PARTS:
            wp = [pos + M @ p for p in f]
            wn = M @ n
            if view(wn)[2] <= 0:                              # back-face cull (camera looks along −z in view space)
                continue
            depth = sum(view(p)[2] for p in wp) / len(wp) + (0.05 if kind == "window" else 0.0)
            faces.append((depth, wp, wn, col, kind))
        faces.sort(key=lambda it: it[0])
        for depth, wp, wn, col, kind in faces:
            self.quad(wp, col, wn, edge=(0.9, 0.95, 1.0) if kind == "body" else None, edge_a=0.35)
        for a_, b_, col in LIGHTS:
            pa, pb = self.P(pos + M @ np.array(a_)), self.P(pos + M @ np.array(b_))
            c.lines([(pa[0], pa[1], pb[0], pb[1])], col, width=5, alpha=0.95)
            c.glow((pa[0] + pb[0]) / 2, (pa[1] + pb[1]) / 2, self.S * 0.5, col, strength=0.5, reach=2)
        if st["thrust"] > 0:                                  # downward jets (rocket-style landing)
            down = -M[:, 1]
            for j_, jp in enumerate(JETS):
                o = pos + M @ np.array(jp)
                e = o + down * (3.2 + 0.4 * math.sin(t * 37 + j_))
                pa, pb = self.P(o), self.P(e)
                c.lines([(pa[0], pa[1], pb[0], pb[1])], (0.75, 0.88, 1.0), width=self.S * 0.55, alpha=0.30)
                c.lines([(pa[0], pa[1], pb[0], pb[1])], (0.9, 0.96, 1.0), width=self.S * 0.18, alpha=0.85)
                c.glow(pa[0], pa[1], self.S * 0.7, BLUE, strength=0.5, reach=2)
        if st.get("stage") == "spin":                         # side jets twist it
            for side in (-1, 1):
                o = pos + M @ np.array([2.0 * side, 0.6, 0.0])
                e = o + M @ np.array([0.0, 0.0, 3.0 * side])
                pa, pb = self.P(o), self.P(e)
                c.lines([(pa[0], pa[1], pb[0], pb[1])], (0.8, 0.9, 1.0), width=self.S * 0.3, alpha=0.6)

    def draw(self, f, rule):
        L, c = self.L, self.canvas
        w, h = L.w, L.h
        t = f * DT
        ctx = c.ctx
        st = FR[f % NF]
        self.cx, self.cy, self.cz, self.S = CAMX[f % NF], CAMY[f % NF], CAMZ[f % NF], CAMS[f % NF] * h
        set_yaw(YAWF[f % NF])
        g = cairo.LinearGradient(0, 0, 0, h)
        g.add_color_stop_rgb(0, 0.02, 0.02, 0.07)
        g.add_color_stop_rgb(0.65, 0.07, 0.04, 0.14)
        g.add_color_stop_rgb(1, 0.02, 0.02, 0.04)
        ctx.set_source(g)
        ctx.paint()
        for (x, y, r, p0) in self.stars:
            c.circle(x, y, r, (1, 1, 1), alpha=0.22 + 0.18 * math.sin(t + p0))
        gl = []                                              # ground grid
        for k in range(-20, 21):
            a_, b_ = self.P(np.array([k * 2.0, 0, -12])), self.P(np.array([k * 2.0, 0, 14]))
            gl.append((a_[0], a_[1], b_[0], b_[1]))
            a_, b_ = self.P(np.array([-40, 0, k * 1.3])), self.P(np.array([40, 0, k * 1.3]))
            gl.append((a_[0], a_[1], b_[0], b_[1]))
        c.lines(gl, (0.45, 0.4, 0.9), width=1.3, alpha=0.18)
        self.draw_ramp()
        if st["ph"] == 2 and st.get("stage") in ("fall", "spin"):   # the drop line
            pa = self.P(st["pos"])
            pb = self.P(np.array([st["pos"][0], 0, st["pos"][2]]))
            c.lines([(pa[0], pa[1], pb[0], pb[1])], PINK, width=2, alpha=0.6)
        if st["ph"] == 3 or (st["ph"] == 2 and st["thrust"] > 0) or (st["ph"] == 4 and st["u"] < 0.6):
            age = st.get("smoke", 0.0)
            pz = st["pos"] if st["ph"] != 4 else INFO["land"]
            fade = 1.0 if st["ph"] != 4 else max(0.0, 1 - st["u"] / 0.6)
            if st["ph"] == 4:
                pz = st["pos"]
            for k in range(9):
                ang = k / 9 * 2 * math.pi
                p_ = self.P(np.array([pz[0] + 2.2 * math.cos(ang), 0.4, pz[2] + 1.6 * math.sin(ang)]))
                c.glow(p_[0], p_[1] - age * 25, self.S * (1.5 + age * 1.5), (0.88, 0.88, 0.95),
                       strength=0.45 * fade, reach=2)
        self.draw_car(st, t)
        # readouts
        ctx.rectangle(0, h * 0.195, w, h * 0.072)
        ctx.set_source_rgba(0.02, 0.02, 0.05, 0.72)
        ctx.fill()
        force = st["fan"] if st["ph"] in (0, 1, 4) else st["thrust"]
        flabel = "fan pull" if st["ph"] in (0, 1, 4) else "jet push"
        c.text_centered(f"{st['v'] * 3.6:3.0f} km/h   ·   {st['pos'][1]:3.0f} m up   ·   {flabel} {force / G / 1000:.1f} t",
                        h * 0.226, size=w * 0.042, color=(1, 1, 1))
        rate = RATE_AIR if st["ph"] == 2 else st.get("rate", RATE_GROUND)
        c.text_centered(("real time" if rate >= 1 else f"slow motion ×{rate:.1f}") + "  ·  numbers are estimates", h * 0.253, size=w * 0.026,
                        color=(0.75, 0.78, 0.9), bold=False)
        # the explanation
        ph, s = st["ph"], st["s"]
        # plain words first (anyone gets it), the formula small and grey (for the curious)
        fl = ""
        ton = lambda kn: f"{kn / G / 1000:.1f}".rstrip("0").rstrip(".")      # noqa: E731  (kN → tonnes of force)
        if ph == 0 or (ph == 4 and st["u"] > 0.6):
            l1, l2, col = "a 2-tonne car, a wall as tall as a 12-storey building", "how does it not fall off?", GOLD
        elif ph == 1 and st["th"] < math.radians(70):
            fl = "pull back = m·g·sinθ"
            l1, l2, col = "the steeper the ramp, the harder gravity", "pulls the car back down", GOLD
        elif ph == 1 and st["th"] < math.radians(95):
            fl = "μ·N ≥ m·g"
            l1, l2, col = "on a wall, only the tyres' grip holds it up:", "they must be pressed with 2 tonnes", CYAN
        elif ph == 1 and st["th"] < math.radians(112):
            fl = "Δp = F / A = 20 kN / 4 m² = 5 kPa"
            l1, l2, col = "it's too slow to stick by speed, so…", "a giant vacuum fan sucks it to the wall", CYAN
        elif ph == 1:
            fl = f"F = m·g·(sinθ/μ − cosθ) − m·v²/r ≈ {NEED_TOP / 1000:.0f} kN"
            l1, l2, col = "upside down, the fan pulls even harder:", f"{ton(NEED_TOP)} tonnes, more than the car weighs!", LIME
        elif ph == 2:
            sg = st["stage"]
            if sg == "spin":
                fl = "torque τ = F·d"
                l1, l2, col = "fan off! side jets flip it right side up", "like spinning a pencil by flicking one end", BLUE
            elif sg == "fall":
                fl = f"v = √(2·g·h) = √(2·9.8·{INFO['y_peak']:.0f}) ≈ {INFO['vfree'] * 3.6:.0f} km/h"
                l1, l2, col = f"now it falls {INFO['y_peak']:.0f} m, like off a 12-storey roof", \
                    f"it would hit the ground at {INFO['vfree'] * 3.6:.0f} km/h", PINK
            elif sg == "burn":
                fl = f"F = m·(g + a) ≈ {MASS * (G + A_BURN) / 1000:.0f} kN"
                l1, l2, col = "rocket jets push down to brake,", \
                    f"like a SpaceX landing: {ton(MASS * (G + A_BURN))} tonnes of push", BLUE
            else:
                fl = "F = (dm/dt)·v_e"
                l1, l2, col = "that push costs a lot of gas:", f"about {MASS * (G + A_BURN) / VE:.0f} kg every second", BLUE
        else:
            l1, l2, col = "it touches down at 0 km/h", "physics, not magic", LIME
        g2 = cairo.LinearGradient(0, h * 0.69, 0, h * 0.71)
        g2.add_color_stop_rgba(0, 0.02, 0.02, 0.05, 0.0)
        g2.add_color_stop_rgba(1, 0.02, 0.02, 0.05, 0.88)
        ctx.rectangle(0, h * 0.69, w, h * 0.14)
        ctx.set_source(g2)
        ctx.fill()
        if fl:
            c.text_centered(fl, h * 0.722, size=w * 0.028, color=(0.62, 0.66, 0.78), bold=False, max_w=w * 0.94)
        c.text_centered(l1, h * 0.757, size=w * 0.042, color=(0.97, 0.97, 1.0), max_w=w * 0.95)
        c.text_centered(l2, h * 0.795, size=w * 0.048, color=col, max_w=w * 0.95)
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


def _key(st):
    if st["ph"] == 1:
        th = st["th"]
        return (1, sum(int(th >= math.radians(a)) for a in (70, 95, 112)))
    return (st["ph"], st.get("stage"))


def build_events(sim, layout):
    out, prev, k = [], None, 0
    notes = [69, 72, 76, 79, 81, 84, 88, 86, 84, 81]
    for f in range(NF):
        key = _key(FR[f])
        if key != prev:
            out.append({"t": round(f / FPS + 0.01, 4), "note": notes[k % len(notes)], "gain": 0.28, "x": layout.w / 2})
            k += 1
            prev = key
    return out


def sound_bed():
    sr = audio.SR
    n = int(round(T_LOOP * sr))
    out = np.zeros(n)
    rng = np.random.default_rng(3)
    fq, motor, fan, jet = np.zeros(n), np.zeros(n), np.zeros(n), np.zeros(n)
    for f in range(NF):
        st = FR[f]
        i0, i1 = f * n // NF, (f + 1) * n // NF
        fq[i0:i1] = 110 + 18 * st["v"]
        motor[i0:i1] = 1.0 if st["ph"] in (0, 1, 4) else 0.1
        fan[i0:i1] = 1.0 if st["ph"] == 1 else 0.0
        jet[i0:i1] = min(1.5, st["thrust"] / (MASS * G)) + (0.5 if st.get("stage") == "spin" else 0.0)
    sm = np.ones(600) / 600
    motor, fan, jet = (np.convolve(a, sm, mode="same") for a in (motor, fan, jet))
    phs = 2 * np.pi * np.cumsum(fq) / sr
    out += 0.05 * motor * (np.sin(phs) + 0.35 * np.sin(2 * phs) + 0.15 * np.sin(3 * phs))
    out += 0.2 * fan * np.convolve(rng.standard_normal(n), np.ones(40) / 40, mode="same")     # fan roar (low)
    out += 0.08 * jet * np.convolve(rng.standard_normal(n), np.ones(10) / 10, mode="same")    # gas hiss
    i0 = int((next(i for i, st in enumerate(FR) if st["ph"] == 3)) / FPS * sr)
    tv = np.arange(int(0.5 * sr)) / sr
    th = np.sin(2 * np.pi * np.cumsum(50 + 60 * np.exp(-tv / 0.04)) / sr) * np.exp(-tv / 0.12)
    out[i0:i0 + len(th)] += 0.45 * th[: n - i0]
    # the hook: a deep bass boom on frame 0 (its tail folds nowhere: it starts the loop) + the fan roar swelling into it
    tv = np.arange(int(1.6 * sr)) / sr
    boom = np.sin(2 * np.pi * np.cumsum(32 + 38 * np.exp(-tv / 0.09)) / sr) * np.exp(-tv / 0.45)
    boom = np.tanh(2.2 * boom) * 0.9 + 0.25 * rng.standard_normal(len(tv)) * np.exp(-tv / 0.03)
    out[:len(boom)] += 0.55 * boom[:n]
    roar = np.convolve(rng.standard_normal(n), np.ones(60) / 60, mode="same") * 6
    tt = np.arange(n) / sr
    swell = np.exp(-np.minimum(tt, T_LOOP - tt) / 1.2)      # loudest at the seam, both sides
    out += 0.10 * swell * roar
    pad = kit.loop_pad(T_LOOP, ((45, 1.0), (52, 0.6), (57, 0.4), (64, 0.25)), gain=0.012)
    return (out + pad[:n]).astype(np.float32)


def _worker(o, sim, label, rule):
    layout = get_layout(o)
    name = f"{SCENE}_{label}_{layout.tag}"
    video = studio.OUT_DIR / f"{name}_silent.mp4"
    d = render(layout, sim, video, rule)
    kit.deliver_loop(SCENE, name, layout, video, build_events(sim, layout), d, voice="glassharp", bed=sound_bed(),
                     peak_db=-6.0)


def main():
    label, rule = arg("--label", "v2"), arg("--rule", "")
    studio.OUT_DIR.mkdir(exist_ok=True)
    sim = simulate()
    if kit.has("--info"):
        ph_t = {p: round(next(i for i, s_ in enumerate(FR) if s_["ph"] == p) / FPS, 2) for p in range(5)}
        print(f"T={T_LOOP:.2f}s phases={ph_t} peak={INFO['y_peak']:.1f} m  air {INFO['TA']:.2f}s real  "
              f"free-fall speed {INFO['vfree'] * 3.6:.0f} km/h  land={np.round(INFO['land'], 1)}  "
              f"max fan {max(s_['fan'] for s_ in FR) / 1000:.1f} kN")
        return
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
