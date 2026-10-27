"""THE STICKMAN WHO FIXED INFINITY — a neon stickman adventure on the math grid (16:9 long-form, built chapter by chapter).

Owner's script (2026-10-18): the orange stickman wakes at (0,0); a glitch monster "Divide by Zero" shatters the
Golden Spiral; he crosses 6 math lands collecting φ shards and beats the boss. One continuous journey (no chapter
cards). This file renders --chapter 1 (THE ORIGIN, 60 s, 4 shots); later chapters are added here.
  Shot 1  0-15  dark grid, a dot pulses at the origin (heartbeat), the axes draw themselves, the dot grows into the hero
  Shot 2 15-30  the camera rises to the Golden Spiral; Divide by Zero tears through it; gold shards rain down
  Shot 3 30-45  the grid cracks red around him; NaN / ERROR creatures crawl out; he backs away, raises his fists
  Shot 4 45-60  a quick fight to a phonk beat; shard "φ 1/6" falls; he grabs it; his chest core lights; close-up
Audio (original): drone + heartbeat, shatter + a glitch sweep, static + tension pulse, phonk beat + hits, a chime.
"""
import math
import sys
from pathlib import Path

import cairo
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import audio, kit, studio  # noqa: E402
from lib.kit import DT, FPS, arg, smooth  # noqa: E402
from lib.layouts import get_layout  # noqa: E402
from lib.studio import Canvas, VideoWriter  # noqa: E402
import dot_adventure as DA  # noqa: E402  (the puppet engine)

SCENE = "infinity_hero"
CHAPTER = int(arg("--chapter", "1"))
T_LOOP = 60.0
ORANGE, WHITE, GOLD, RED = (1.0, 0.55, 0.15), (1, 1, 1), (1.0, 0.82, 0.35), (1.0, 0.18, 0.22)
PHI = (1 + 5 ** 0.5) / 2

P = DA.POSES
GUARD = dict(lean=8, head=0, af=(55, 150), ab=(35, 150), lf=(22, 5), lb=(-22, -5))
PUNCH = dict(lean=14, head=-5, af=(92, 88), ab=(35, 150), lf=(28, 5), lb=(-28, -8))
LOOKUP = dict(lean=-6, head=-38, af=(12, 6), ab=(-12, -6), lf=(7, 2), lb=(-7, -2))
REACH = dict(lean=28, head=30, af=(75, 60), ab=(-10, -5), lf=(25, 5), lb=(-20, -10))
CHEST = dict(lean=0, head=25, af=(60, 150), ab=(-20, -10), lf=(7, 2), lb=(-7, -2))

# ---- shot 2: the Golden Spiral and the boss
SP_C, SP_S = np.array([4.0, 9.0]), 0.09


def spiral_pts():
    th = np.linspace(0, 4.2 * math.pi, 420)
    r = SP_S * PHI ** (2 * th / math.pi)
    return np.stack([SP_C[0] + r * np.cos(th), SP_C[1] + r * np.sin(th)], 1)


SPIRAL = spiral_pts()
RNG = np.random.default_rng(7)
SHARDS = []                                             # (start point, velocity, spin) for 70 pieces of the spiral
for k in range(70):
    i0 = int(k / 70 * (len(SPIRAL) - 6))
    p0 = SPIRAL[i0:i0 + 6]
    mid = p0.mean(0)
    v = (mid - SP_C) * RNG.uniform(0.25, 0.6) + RNG.normal(0, 0.6, 2)
    SHARDS.append((p0 - mid, mid, v, RNG.uniform(-6, 6), RNG.uniform(-14, 14)))
T_SHATTER = 21.0

# ---- shot 3: cracks + creatures
CRACKS = []
for k in range(9):
    x0 = 1.0 + RNG.uniform(-0.5, 5.5)
    pts = [(x0, 0.0)]
    a = RNG.uniform(-0.9, 0.9)
    for j in range(7):
        a += RNG.normal(0, 0.5)
        pts.append((pts[-1][0] + 0.35 * math.cos(a), max(-1.6, pts[-1][1] - 0.18 * abs(math.sin(a)) - 0.05)))
    CRACKS.append((RNG.uniform(31.0, 34.5), pts))
CREATURES = [("NaN", 2.2, 36.2, 45.7), ("ERROR", 3.4, 36.8, 46.8), ("NaN", 4.4, 37.5, 48.1), ("ERROR", 5.3, 38.1, 49.5),
             ("NaN", 6.4, 38.8, 50.9), ("ERR", 7.2, 39.3, 52.0)]          # label, spawn x, emerge t, killed at t
HITS = [(c[3], "punch" if i % 2 == 0 else "kick") for i, c in enumerate(CREATURES)]


def hero_x(t):
    if t < 38.0:
        return 0.0
    if t < 41.0:
        return -1.2 * smooth((t - 38.0) / 3.0)
    if t < 45.0:
        return -1.2
    if t < 52.4:                                         # pushes forward through the fight
        k = sum(1 for th, _ in HITS if th <= t)
        return -1.2 + 0.55 * k + 0.25 * math.sin(math.pi * min(1, (t - 45) % 1.0))
    return 2.1


def creature_state(i, t):
    lab, x0, te, tk = CREATURES[i]
    if t < te or t > tk + 0.6:
        return None
    rise = smooth((t - te) / 0.8)
    hx = hero_x(min(t, tk))
    contact = hx + 0.75
    if t < tk - 0.5:
        u = smooth((t - te) / max(0.1, (tk - 0.5 - te)))
        x = x0 + (max(contact, x0 - 2.2) - x0) * u * (1 if t > 41 else 0.35)
    else:
        x = contact
    dead = t >= tk
    return lab, x, -0.45 + 0.45 * rise, dead, (t - tk) if dead else 0.0


def hero(t):
    """Hero state at time t: dict(x, y, face, pose, airborne, rot, alpha, core, mouth, eyes)."""
    s = dict(x=hero_x(t), y=0.0, face=1, pose=P["stand"], airborne=0.0, rot=0.0, alpha=1.0, core=0.0,
             mouth="smile", eyes="open")
    if t < 10.5:
        s["alpha"] = 0.0
    elif t < 12.5:
        s["alpha"] = smooth((t - 10.5) / 0.6)
        s["pose"] = DA.blend(P["crouch"], P["stand"], smooth((t - 11.3) / 1.2))
        s["eyes"] = "closed" if t < 11.6 else "open"
    elif t < 15.0:
        s["face"] = -1 if 12.9 <= t < 13.9 else 1
        s["pose"] = P["stand"]
    elif t < 30.0:
        s["pose"] = DA.blend(P["stand"], LOOKUP, smooth((t - 15.5) / 1.0))
        s["eyes"] = "wide" if t > T_SHATTER else "open"
        s["mouth"] = "open" if T_SHATTER <= t < 24 else "line"
    elif t < 38.0:
        s["pose"] = DA.blend(LOOKUP, P["stand"], smooth((t - 30) / 0.8))
        s["eyes"] = "wide" if t > 33 else "open"
        s["mouth"] = "line"
    elif t < 41.0:
        s["pose"] = DA.cycle(t)
        s["eyes"] = "wide"
        s["mouth"] = "open"
    elif t < 45.0:
        s["pose"] = DA.blend(P["stand"], GUARD, smooth((t - 41.2) / 0.5))
        s["mouth"] = "line"
    elif t < 52.6:
        s["pose"] = GUARD
        for th, kind in HITS:
            d = t - th
            if -0.18 <= d < 0.25:
                k = 1 - abs(d - 0.0) / 0.22 if d < 0 else 1 - d / 0.25
                s["pose"] = DA.blend(GUARD, PUNCH if kind == "punch" else P["kick"], max(0.0, min(1.0, k)))
                s["mouth"] = "open"
        if 50.2 <= t < 51.0:                             # a spinning jump between hits
            u = (t - 50.2) / 0.8
            s["airborne"] = 0.9 * math.sin(math.pi * u)
            s["rot"] = -2 * math.pi * smooth(u)
            s["pose"] = P["jump"]
    elif t < 55.0:
        s["pose"] = DA.blend(GUARD, P["stand"], smooth((t - 52.6) / 0.6))
        s["mouth"] = "smile"
    elif t < 56.2:
        s["pose"] = DA.blend(P["stand"], REACH, smooth((t - 55.0) / 0.5))
    else:
        s["pose"] = DA.blend(REACH, CHEST, smooth((t - 56.2) / 0.6))
        s["eyes"] = "wide" if t < 57.5 else "open"
    if t >= 56.2:
        s["core"] = 0.35 * smooth((t - 56.2) / 0.8)
    return s


def shard_fall(t):
    """The first φ shard: falls at 53, lands near him, flies into his chest at 56."""
    xl = 2.9
    if t < 53.0:
        return None
    if t < 54.6:
        u = (t - 53.0) / 1.6
        return xl, 9.0 * (1 - u * u) + 0.35, 1.0
    if t < 55.6:
        return xl, 0.35 + 0.06 * math.sin((t - 54.6) * 6), 1.0
    if t < 56.2:
        u = smooth((t - 55.6) / 0.6)
        return xl + (hero_x(t) - xl) * u, 0.35 + (0.72 - 0.35) * u, 1.0 - 0.6 * u
    return None


# ---- camera: (centre x, centre y, pixels-per-unit as a fraction of h)
CAM_KEYS = [(0.0, 0.0, 0.3, 0.030), (8.0, 0.0, 0.5, 0.060), (15.0, 0.0, 0.6, 0.22), (16.0, 0.3, 1.2, 0.20),
            (19.5, 2.6, 6.8, 0.085), (23.0, 2.6, 6.0, 0.075), (26.5, 1.8, 3.4, 0.070), (29.5, 1.6, 2.6, 0.080), (31.5, 1.8, 0.8, 0.17),
            (38.0, 1.8, 0.8, 0.17), (41.0, 1.4, 0.8, 0.18), (45.0, 1.8, 0.8, 0.19), (52.4, 2.6, 0.8, 0.19),
            (55.0, 1.8, 0.9, 0.20), (56.4, 1.2, 0.8, 0.26), (60.0, 2.1, 0.75, 0.62)]


def camera(t):
    ks = CAM_KEYS
    for (t0, x0, y0, s0), (t1, x1, y1, s1) in zip(ks, ks[1:]):
        if t0 <= t <= t1:
            u = smooth((t - t0) / (t1 - t0))
            ls = math.log(s0) + (math.log(s1) - math.log(s0)) * u
            return x0 + (x1 - x0) * u, y0 + (y1 - y0) * u, math.exp(ls)
    return ks[-1][1], ks[-1][2], ks[-1][3]


def simulate():
    return {"nf": int(round(T_LOOP * FPS))}


class Scene:
    def __init__(self, layout, sim):
        self.L, self.sim = layout, sim
        self.canvas = Canvas(layout.w, layout.h, studio.render_scale())

    def X(self, x):
        return self.L.w / 2 + (x - self.cx) * self.S

    def Y(self, y):
        return self.L.h * 0.55 - (y - self.cy) * self.S

    def glow_text(self, s, x, y, size, col, a=1.0, glitch=0.0, t=0.0):
        c = self.canvas
        if glitch > 0:
            j = glitch * size * 0.06
            c.text_centered(s, y + j * math.sin(t * 53), size=size, color=(1, 0.1, 0.2), alpha=0.6 * a,
                            cx=x - j * (1 + math.sin(t * 37)))
            c.text_centered(s, y - j * math.sin(t * 41), size=size, color=(0.2, 0.9, 1.0), alpha=0.5 * a,
                            cx=x + j * (1 + math.cos(t * 29)))
        c.text_centered(s, y, size=size, color=col, alpha=a, cx=x)

    def grid(self, t):
        c, w, h = self.canvas, self.L.w, self.L.h
        a = smooth(t / 2.0)
        x0, x1 = self.cx - w / 2 / self.S - 1, self.cx + w / 2 / self.S + 1
        y0, y1 = self.cy - h / self.S - 1, self.cy + h / self.S + 1
        step = 1 if self.S > h * 0.04 else 2
        lines = []
        for gx in range(int(math.floor(x0 / step) * step), int(x1) + 1, step):
            lines.append((self.X(gx), 0, self.X(gx), h))
        for gy in range(int(math.floor(y0 / step) * step), int(y1) + 1, step):
            lines.append((0, self.Y(gy), w, self.Y(gy)))
        c.lines(lines, (0.25, 0.32, 0.6), width=1.2, alpha=0.32 * a)
        # the axes draw themselves outward from the origin
        L = 40 * smooth((t - 2.0) / 4.0) if t < 6.0 else 40
        if L > 0.01:
            ax = [(self.X(-L), self.Y(0), self.X(L), self.Y(0)), (self.X(0), self.Y(-L), self.X(0), self.Y(L))]
            c.lines(ax, WHITE, width=7, alpha=0.18)
            c.lines(ax, WHITE, width=2.5, alpha=0.9)

    def cracks(self, t):
        c = self.canvas
        for t0, pts in CRACKS:
            if t < t0:
                continue
            n = min(len(pts), 1 + int((t - t0) / 0.25))
            sp = [(self.X(x), self.Y(y)) for x, y in pts[:n]]
            if len(sp) > 1:
                c.polylines([sp], RED, width=10, alpha=0.18)
                c.polylines([sp], (1.0, 0.35, 0.35), width=3, alpha=0.95)

    def creature(self, lab, x, y, dead, age, t):
        c, ctx = self.canvas, self.canvas.ctx
        X, Y, S = self.X, self.Y, self.S
        if dead:
            if age > 0.6:
                return
            for k in range(14):                          # bursts into particles
                a = k / 14 * 2 * math.pi + 0.3
                r = 0.2 + 1.6 * age
                px, py = x + r * math.cos(a), y + 0.3 + r * math.sin(a) * 0.8 - 1.5 * age * age
                c.circle(X(px), Y(py), S * 0.05 * (1 - age / 0.6), (1, 0.4 + 0.5 * (k % 2), 0.4), alpha=1 - age / 0.6)
            return
        jit = 0.03 * math.sin(t * 47 + x * 9)
        bw, bh = 0.32 + 0.06 * len(lab), 0.42
        for k in range(4):                               # scuttling legs
            lx = x - bw / 2 + 0.1 + k * (bw - 0.2) / 3
            ph = math.sin(t * 22 + k * 1.7) * 0.06
            c.lines([(X(lx), Y(y + 0.12), X(lx + ph - 0.05), Y(y)), (X(lx + ph - 0.05), Y(y), X(lx + ph - 0.1), Y(y))],
                    RED, width=S * 0.03)
        ctx.new_path()
        x0, y0 = X(x - bw / 2 + jit), Y(y + 0.12 + bh)
        ctx.rectangle(x0, y0, bw * S, bh * S)
        ctx.set_source_rgba(0.12, 0.02, 0.03, 0.95)
        ctx.fill_preserve()
        ctx.set_source_rgba(*RED, 0.95)
        ctx.set_line_width(S * 0.025)
        ctx.stroke()
        c.glow(X(x), Y(y + 0.3), S * 0.5, RED, strength=0.35, reach=2)
        self.glow_text(lab, X(x + jit), Y(y + 0.22), S * 0.2, (1, 0.85, 0.85), glitch=1.0, t=t)
        for s_ in (-1, 1):                               # angry eyes
            c.circle(X(x + s_ * 0.08), Y(y + 0.47), S * 0.03, WHITE)

    def boss(self, t, cx, cy, scale, alpha):
        c, ctx = self.canvas, self.canvas.ctx
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
        self.glow_text("÷0", self.X(cx), self.Y(cy - 0.25 * scale), self.S * scale * 0.9, WHITE, a=alpha, glitch=1.5, t=t)

    def draw_hero(self, s, t):
        c, ctx = self.canvas, self.canvas.ctx
        if s["alpha"] <= 0.01:
            return
        X, Y, S = self.X, self.Y, self.S
        px, py = X(s["x"]), Y(s["y"] + 0.55 + s["airborne"])
        ctx.save()
        if s["rot"]:
            ctx.translate(px, py)
            ctx.rotate(s["rot"])
            ctx.translate(-px, -py)
        c.glow(px, py, S * 0.55, ORANGE, strength=0.2 * s["alpha"], reach=2.0)
        ctx.push_group()
        DA.draw_puppet(ctx, X, Y, S * 1.35, s["x"], s["y"], s["face"], s["pose"], mouth=s["mouth"], eyes=s["eyes"],
                       col=WHITE, t=t, airborne=s["airborne"])
        DA.draw_puppet(ctx, X, Y, S, s["x"], s["y"], s["face"], s["pose"], mouth=s["mouth"], eyes=s["eyes"],
                       col=ORANGE, t=t, airborne=s["airborne"])
        ctx.pop_group_to_source()
        ctx.paint_with_alpha(s["alpha"])
        if s["core"] > 0:                                # the gold core in his chest
            hip = DA.leg_drop(s["pose"]) + s["airborne"]
            cyw = s["y"] + hip + DA.TO * 0.75
            c.glow(X(s["x"]), Y(cyw), S * 0.35, GOLD, strength=0.9 * s["core"] / 0.35, reach=2.5)
            c.circle(X(s["x"]), Y(cyw), S * 0.05, (1, 0.95, 0.7), alpha=min(1.0, s["core"] * 3))
        ctx.restore()

    def draw(self, f, rule):
        L, c = self.L, self.canvas
        w, h = L.w, L.h
        t = f * DT
        ctx = c.ctx
        ctx.set_source_rgb(0, 0, 0)
        ctx.paint()
        self.cx, self.cy, sf = camera(t)
        self.S = sf * h
        if 49.0 < t < 52.0:                              # tiny shake on the big hits
            for th, _ in HITS:
                if 0 <= t - th < 0.15:
                    self.cx += 0.04 * math.sin(t * 90)
        X, Y = self.X, self.Y
        self.grid(t)
        self.cracks(t)
        # the origin dot (shot 1) + its heartbeat
        if t < 11.0:
            beat = max(math.exp(-((t - tb) / 0.12) ** 2) for tb in (1.0, 2.6, 4.2, 5.8, 7.4, 9.0))
            a = smooth(t / 0.6) * (1 - smooth((t - 10.4) / 0.6))
            c.glow(X(0), Y(0), self.S * (0.4 + 0.5 * beat), ORANGE, strength=(0.5 + 0.5 * beat) * a, reach=2.5)
            if t >= 8.0:                                 # the dot stretches up into a body
                u = smooth((t - 8.0) / 2.4)
                c.lines([(X(0), Y(0), X(0), Y(1.15 * u))], ORANGE, width=self.S * 0.08, alpha=a)
            c.circle(X(0), Y(0), self.S * 0.08 * (1 + 0.4 * beat), (1, 0.85, 0.6), alpha=a)
        # title over the empty world
        if 3.0 < t < 9.0:
            a = smooth((t - 3.0) / 1.0) * (1 - smooth((t - 8.0) / 1.0))
            self.glow_text("THE STICKMAN WHO FIXED INFINITY", w / 2, h * 0.2, w * 0.034, GOLD, a=a)
        # the Golden Spiral, the boss, the shards
        if 14.0 < t < 31.0:
            if t < T_SHATTER:
                a = smooth((t - 14.0) / 2.0)
                pts = [(X(x), Y(y)) for x, y in SPIRAL]
                c.polylines([pts], GOLD, width=14, alpha=0.2 * a)
                c.polylines([pts], (1, 0.92, 0.6), width=4, alpha=0.95 * a)
                c.glow(X(SP_C[0]), Y(SP_C[1]), self.S * 2.5, GOLD, strength=0.25 * a, reach=2)
            else:
                dt_ = t - T_SHATTER
                for off, mid, v, g_, spin in SHARDS:
                    pos = mid + v * dt_ + np.array([0, -0.5 * 6.0 * dt_ * dt_])
                    if pos[1] < 0.05:                    # landed on the grid
                        tl = 0.0
                        pos[1] = 0.05
                    ang = spin * dt_
                    rot = np.array([[math.cos(ang), -math.sin(ang)], [math.sin(ang), math.cos(ang)]])
                    pp = [(X(p[0]), Y(p[1])) for p in (off @ rot.T + pos)]
                    fade = 1.0 - smooth((t - 28.0) / 2.5)
                    c.polylines([pp], (1, 0.92, 0.6), width=3, alpha=0.95 * fade)
                    c.glow(pp[0][0], pp[0][1], self.S * 0.12, GOLD, strength=0.5 * fade, reach=2)
            if 18.5 < t < 31.0:
                u = smooth((t - 18.5) / 2.8)
                bx = 13.0 + (SP_C[0] - 2.5 - 13.0) * u
                by = 11.0 - 1.5 * u
                self.boss(t, bx, by, 1.6, smooth((t - 18.5) / 0.6) * (1 - smooth((t - 29.8) / 1.0)))
        if 22.5 < t < 29.8:
            a = smooth((t - 22.5) / 0.4) * (1 - smooth((t - 29.0) / 0.8))
            self.glow_text("DIVIDE BY ZERO", w / 2, h * 0.22, w * 0.06, RED, a=a, glitch=2.0, t=t)
        # creatures, hero, shard
        for i in range(len(CREATURES)):
            st = creature_state(i, t)
            if st:
                self.creature(st[0], st[1], st[2], st[3], st[4], t)
        self.draw_hero(hero(t), t)
        sh = shard_fall(t)
        if sh:
            x, y, a = sh
            c.glow(X(x), Y(y), self.S * 0.4, GOLD, strength=0.9 * a, reach=2.4)
            c.poly([(X(x), Y(y + 0.18)), (X(x + 0.1), Y(y)), (X(x), Y(y - 0.18)), (X(x - 0.1), Y(y))], (1, 0.9, 0.5),
                   alpha=a)
            if t < 55.6:
                self.glow_text("φ 1/6", X(x), Y(y + 0.4), self.S * 0.22, GOLD, a=smooth((t - 54.3) / 0.4))
        if t >= 56.2:
            self.glow_text("φ 1/6", w * 0.5, h * 0.18, w * 0.045, GOLD, a=smooth((t - 56.4) / 0.5))
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
    if writer is not None:
        writer.close()
    return sim["nf"] / FPS


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def track():
    sr = audio.SR
    n = int(round(T_LOOP * sr))
    out = np.zeros(n)
    rng = np.random.default_rng(3)

    def add(t0, sig, g):
        i0 = int(round(t0 * sr))
        if i0 >= n:
            return
        sig = sig[: n - i0]
        out[i0:i0 + len(sig)] += g * sig

    tt = np.arange(n) / sr
    # drone (shots 1-3): two low detuned sines, swelling
    dr = np.sin(2 * np.pi * 55 * tt) + np.sin(2 * np.pi * 55.4 * tt) + 0.5 * np.sin(2 * np.pi * 82.5 * tt)
    env = np.clip(tt / 3, 0, 1) * np.clip((46 - tt) / 2, 0, 1)
    out += 0.05 * dr * env
    for tb in (1.0, 2.6, 4.2, 5.8, 7.4, 9.0):                  # heartbeat thumps
        tv = np.arange(int(0.3 * sr)) / sr
        th = np.sin(2 * np.pi * np.cumsum(42 + 50 * np.exp(-tv / 0.03)) / sr) * np.exp(-tv / 0.08)
        add(tb, th, 0.6)
        add(tb + 0.22, th, 0.35)
    tv = np.arange(int(1.5 * sr)) / sr                          # the hero forms: a rising shimmer
    add(8.5, np.sin(2 * np.pi * np.cumsum(300 + 500 * tv) / sr) * np.sin(np.pi * tv / 1.5) * 0.3, 0.12)
    # shot 2: a glitch sweep as the boss arrives, then the shatter
    tv = np.arange(int(2.5 * sr)) / sr
    f = 900 * np.exp(-tv * 1.2) + 60
    sw = np.sign(np.sin(2 * np.pi * np.cumsum(f) / sr)) * np.sin(np.pi * tv / 2.5) * (0.5 + 0.5 * (rng.random(len(tv)) > 0.97))
    add(18.8, sw, 0.05)
    tv = np.arange(int(2.0 * sr)) / sr
    nz = rng.standard_normal(len(tv))
    sh = np.diff(np.concatenate([[0], nz])) * np.exp(-tv / 0.35)
    for k in range(10):
        sh += np.sin(2 * np.pi * rng.uniform(2500, 6000) * tv) * np.exp(-tv / rng.uniform(0.2, 0.6)) * 0.3
    add(T_SHATTER, sh, 0.18)
    # shot 3: static crackles + a tension pulse
    for k in range(40):
        t0 = 31 + k * 0.33 + rng.uniform(0, 0.2)
        tv = np.arange(int(0.05 * sr)) / sr
        add(t0, rng.standard_normal(len(tv)) * np.exp(-tv / 0.01), 0.04)
    pulse = np.sin(2 * np.pi * 73.4 * tt) * (0.5 + 0.5 * np.sign(np.sin(2 * np.pi * 2.0 * tt)))
    out += 0.05 * pulse * np.clip((tt - 33) / 3, 0, 1) * np.clip((45.2 - tt) / 0.3, 0, 1)
    # shot 4: a phonk beat (140 BPM half-time, F# minor), hits, the chime
    B = 60 / 140
    t_on = 45.0
    bell = [66, 69, 71, 73, 71, 69, 66, 64]
    for k in range(int((60 - t_on) / (B / 4))):
        tb = t_on + k * B / 4
        pos = k % 16
        if pos in (0, 3, 6, 8, 11, 14):                          # cowbell-style 3-3-2 lead
            m = bell[(k // 16 * 3 + pos) % len(bell)]
            tv = np.arange(int(0.25 * sr)) / sr
            ph = 2 * np.pi * hz(m) * tv
            sig = sum(np.sin(j * ph) / j for j in (1, 3, 5)) + 0.8 * sum(np.sin(j * ph * 1.48) / j for j in (1, 3, 5))
            add(tb, sig * np.exp(-tv / 0.05), 0.06)
        if pos % 2 == 0:                                         # hats
            tv = np.arange(int(0.04 * sr)) / sr
            add(tb, np.diff(np.concatenate([[0], rng.standard_normal(len(tv))])) * np.exp(-tv / 0.01), 0.02)
        if pos in (0, 10):                                       # 808
            tv = np.arange(int(0.8 * sr)) / sr
            fr = hz(30) * (1 + 1.5 * np.exp(-tv / 0.03))
            add(tb, np.tanh(2.4 * np.sin(2 * np.pi * np.cumsum(fr) / sr)) * np.exp(-tv / 0.5), 0.30)
        if pos == 8:                                             # clap on beat 3
            tv = np.arange(int(0.2 * sr)) / sr
            nz = rng.standard_normal(len(tv))
            add(tb, (nz - np.convolve(nz, np.ones(6) / 6, mode="same")) * np.exp(-tv / 0.06), 0.10)
    for th, kind in HITS:                                       # punch / kick impacts
        tv = np.arange(int(0.25 * sr)) / sr
        thud = np.sin(2 * np.pi * np.cumsum(80 + 160 * np.exp(-tv / 0.02)) / sr) * np.exp(-tv / 0.07)
        add(th, thud + 0.5 * rng.standard_normal(len(tv)) * np.exp(-tv / 0.015), 0.35)
    tv = np.arange(int(1.6 * sr)) / sr                          # the shard: a chime
    ch = sum(np.sin(2 * np.pi * hz(m) * tv) for m in (78, 81, 85, 90)) * np.exp(-tv / 0.5) / 4
    add(56.2, ch, 0.18)
    return out.astype(np.float32)


def _worker(o, sim, label, rule):
    layout = get_layout(o)
    name = f"{SCENE}_{label}_{layout.tag}"
    video = studio.OUT_DIR / f"{name}_silent.mp4"
    d = render(layout, sim, video, rule)
    kit.deliver_loop(SCENE, name, layout, video, [], d, voice="piano", bed=track(), peak_db=-3.0)


def main():
    label, rule = arg("--label", "ch1"), arg("--rule", "")
    studio.OUT_DIR.mkdir(exist_ok=True)
    sim = simulate()
    if kit.has("--still"):
        layout = get_layout(kit.orients()[0])
        f = int(arg("--frame", "0"))
        png = studio.OUT_DIR / f"{SCENE}_{label}_f{f}_{layout.tag}.png"
        render(layout, sim, png, rule, still_frame=f)
        print(f"[{SCENE}] -> {png}")
        return
    print(f"[{SCENE}] chapter {CHAPTER}: {T_LOOP:.0f}s")
    kit.fan_out(_worker, (sim, label, rule), SCENE)


if __name__ == "__main__":
    main()
