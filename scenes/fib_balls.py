"""FIB BALLS — Fibonacci's rabbits as bouncing balls: real physics (gravity, ball-ball collisions) inside a circle,
and on every beat each grown-up ball pops out one baby ball. A baby grows up after one beat.
Count per beat: 1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144 (exactly Fibonacci: the rule is applied on the beat), the
circle packs full of crashing balls, and F(n)/F(n-1) -> φ = 1.618… (digits turn gold as they lock).
Physics: semi-implicit Euler, 4 substeps per frame, vectorised pairwise collisions (elastic with a little restitution
loss), elastic circle wall, a small speed cap. The whole run is recorded, then played BACKWARDS (babies merge back into
their parents) to the first ball: the loop.
Audio (original, lib/sfx): marble clacks from the real collisions (capped rate, pentatonic marimba ticks, louder for
harder hits), a plucked chord + soft kick on every birth beat climbing the scale, a pad, a chime on 144, a falling
sweep on the rewind.
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

SCENE = "fib_balls"
BEAT0, BEAT = 0.8, 0.70
N_BEATS = 11                                  # 1 -> 144 after 11 birth beats
T_FWD = BEAT0 + BEAT * (N_BEATS - 1) + 2.2    # run on a little after 144 (the settle + the φ reveal)
T_RW = 3.6
T_LOOP = T_FWD + T_RW + 0.4
R_BALL = 0.064                                # ball radius (circle radius = 1): 144 balls fill ~60 %
GRAV = 2.2
GOLD, WHITE, SOFT = (1.0, 0.82, 0.35), (0.96, 0.97, 1.0), (0.75, 0.78, 0.92)
PHI_STR = "1.6180339887"


def fib(n):
    a, b = 1, 1
    out = [1, 1]
    while len(out) < n:
        a, b = b, a + b
        out.append(b)
    return out


FIBS = fib(N_BEATS + 1)                        # 1, 1, 2, … 144


def simulate():
    rng = np.random.default_rng(8)
    pos = np.array([[0.0, 0.55]])
    vel = np.array([[0.9, 0.0]])
    born = np.array([-1.0])                   # birth time (the first ball is already grown up)
    parent = np.array([-1])
    frames, clacks, births = [], [], []
    nf = int(round(T_FWD * FPS))
    sub = 4
    dt = DT / sub
    beat_i = 0
    for f in range(nf):
        t = f * DT
        if beat_i < N_BEATS and t >= BEAT0 + beat_i * BEAT:
            grown = np.where(born <= t - BEAT * 1.5)[0]          # Fibonacci: a newborn waits 2 beats
            if beat_i == 0:
                grown = np.array([], dtype=int)            # beat 0: the first ball is still a baby (1, 1, …)
            new_p, new_v = [], []
            for i in grown:
                a = rng.uniform(0, 2 * math.pi)
                p = pos[i] + 2.05 * R_BALL * np.array([math.cos(a), math.sin(a)])
                if np.linalg.norm(p) > 1 - R_BALL:
                    p = pos[i] - 2.05 * R_BALL * np.array([math.cos(a), math.sin(a)])
                new_p.append(p)
                sp = np.linalg.norm(vel[i]) + 0.4
                new_v.append(np.array([math.cos(a), math.sin(a)]) * sp)
            if new_p:
                pos = np.vstack([pos, new_p])
                vel = np.vstack([vel, new_v])
                born = np.concatenate([born, np.full(len(new_p), t)])
                parent = np.concatenate([parent, grown])
            births.append((t, len(pos)))
            beat_i += 1
        hits = 0.0
        for _ in range(sub):
            vel[:, 1] -= GRAV * dt
            pos += vel * dt
            # wall
            d = np.linalg.norm(pos, axis=1)
            out = d > 1 - R_BALL
            if out.any():
                nrm = pos[out] / d[out, None]
                vn = (vel[out] * nrm).sum(1)
                hit = vn > 0
                vel[out] -= (1.0 + 0.98) * np.where(hit, vn, 0.0)[:, None] * nrm
                pos[out] = nrm * (1 - R_BALL)
                hits += float(np.clip(vn[hit], 0, None).sum())
            # ball-ball
            n = len(pos)
            if n > 1:
                dp = pos[:, None, :] - pos[None, :, :]
                dist = np.sqrt((dp ** 2).sum(-1)) + np.eye(n) * 10
                ii, jj = np.where(np.triu(dist < 2 * R_BALL, 1))
                if len(ii):
                    nrm = dp[ii, jj] / dist[ii, jj, None]
                    overlap = 2 * R_BALL - dist[ii, jj]
                    np.add.at(pos, ii, nrm * overlap[:, None] * 0.5)
                    np.add.at(pos, jj, -nrm * overlap[:, None] * 0.5)
                    rv = ((vel[ii] - vel[jj]) * nrm).sum(1)
                    app = rv < 0
                    imp = np.where(app, -rv * (1 + 0.92) / 2, 0.0)
                    np.add.at(vel, ii, nrm * imp[:, None])
                    np.add.at(vel, jj, -nrm * imp[:, None])
                    hits += float(imp.sum())
            d = np.linalg.norm(pos, axis=1)                  # the wall wins over the pushes
            out = d > 1 - R_BALL
            if out.any():
                pos[out] *= ((1 - R_BALL) / d[out])[:, None]
        sp = np.linalg.norm(vel, axis=1)                    # a gentle speed cap keeps it lively but sane
        cap = 3.2
        vel[sp > cap] *= (cap / sp[sp > cap])[:, None]
        clacks.append(hits)
        frames.append((pos.copy(), born.copy(), parent.copy()))
    return {"frames": frames, "clacks": clacks, "births": births}


SIM = simulate()


def frame_state(t):
    """forward: the recorded frame; rewind: the recording played backwards; hold: the first frame."""
    nf = len(SIM["frames"])
    if t < T_FWD:
        k = min(nf - 1, int(round(t * FPS)))
        return k, False
    if t < T_FWD + T_RW:
        u = smooth((t - T_FWD) / T_RW)
        return int(round((nf - 1) * (1 - u))), True
    return 0, True


class Scene:
    def __init__(self, layout):
        self.L = layout
        self.canvas = Canvas(layout.w, layout.h, studio.render_scale())

    def draw(self, f, rule):
        L, c = self.L, self.canvas
        w, h = L.w, L.h
        t = f * DT
        ctx = c.ctx
        g_ = cairo.RadialGradient(w / 2, h * 0.47, 0, w / 2, h * 0.47, h * 0.7)
        g_.add_color_stop_rgb(0, 0.07, 0.06, 0.12)
        g_.add_color_stop_rgb(1, 0.005, 0.005, 0.015)
        ctx.set_source(g_)
        ctx.paint()
        k, rew = frame_state(t)
        pos, born, parent = SIM["frames"][k]
        tk = k * DT
        n = len(pos)
        cx, cy, R = w / 2, h * 0.49, w * 0.37
        c.glow(cx, cy, R * 1.03, (0.4, 0.6, 1.0), strength=0.12, reach=1.25)
        c.ring(cx, cy, R, (0.55, 0.7, 1.0), width=5, alpha=0.9)
        r = R_BALL * R
        for i in range(n):
            x, y = cx + pos[i, 0] * R, cy - pos[i, 1] * R
            age = tk - born[i]
            baby = age < BEAT * 1.5 and born[i] >= 0
            col = (0.55, 0.95, 1.0) if baby else GOLD
            pop = math.exp(-age / 0.12) if 0 <= age < 0.5 and not rew else 0.0
            if pop > 0.05:
                c.glow(x, y, r * 1.6, WHITE, strength=0.35 * pop, reach=1.6)
            g = cairo.RadialGradient(x - r * 0.35, y - r * 0.35, r * 0.1, x, y, r * (1 + 0.3 * pop))
            g.add_color_stop_rgb(0, min(1, col[0] + 0.3), min(1, col[1] + 0.3), min(1, col[2] + 0.3))
            g.add_color_stop_rgb(1, col[0] * 0.6, col[1] * 0.55, col[2] * 0.5)
            ctx.new_path()
            ctx.arc(x, y, r * (1 + 0.3 * pop), 0, 2 * math.pi)
            ctx.set_source(g)
            ctx.fill()
        # MATH: the count as a Fibonacci number, the sequence, the ratio -> φ
        bi = sum(1 for bt, _ in SIM["births"] if bt <= tk)
        idx = max(1, bi)                                    # F(idx)
        cnt = n
        pop = 0.0
        if bi >= 1 and not rew:
            pop = math.exp(-(tk - SIM["births"][bi - 1][0]) / 0.12)
        done = cnt == 144 and not rew and t > BEAT0 + BEAT * (N_BEATS - 1) + 0.3
        c.text_centered(f"F({idx + 1}) = {cnt}", h * 0.215, size=w * 0.12 * (1 + 0.25 * pop),
                        color=GOLD if done else WHITE)
        seq = ", ".join(str(v) for v in FIBS[:idx + 1])
        c.text_centered(seq, h * 0.25, size=w * 0.036, color=SOFT, bold=False, max_w=w * 0.94)
        if idx >= 2:
            a, b = FIBS[idx], FIBS[idx - 1]
            rs = f"{a / b:.10f}"
            m = 0
            while m < len(rs) and rs[m] == PHI_STR[m]:
                m += 1
            head = f"{a} ÷ {b} = "
            self.ratio(head, rs, m, h * 0.76, w * 0.05)
        if done:
            c.text_centered("→ φ = 1.618…  the golden ratio", h * 0.80, size=w * 0.042, color=GOLD)
        elif rew:
            c.text_centered("time runs backwards…", h * 0.80, size=w * 0.04, color=SOFT, bold=False)
        else:
            c.text_centered("every beat: each grown-up ball has a baby", h * 0.80, size=w * 0.038, color=SOFT,
                            bold=False, max_w=w * 0.94)
        if rule:
            c.caption(rule, alpha=1.0, layout=L)
        c.watermark(L)

    def ratio(self, head, s, m, y, size):
        c = self.canvas
        ctx = c.ctx
        c._font(size, True)
        wh, ws = ctx.text_extents(head).x_advance, ctx.text_extents(s).x_advance
        x = self.L.w / 2 - (wh + ws) / 2
        ctx.set_source_rgba(*SOFT, 1)
        ctx.move_to(x, y)
        ctx.show_text(head)
        x += wh
        for i, ch in enumerate(s):
            ctx.set_source_rgba(*(GOLD if i < m else WHITE), 1)
            ctx.move_to(x, y)
            ctx.show_text(ch)
            x += ctx.text_extents(ch).x_advance


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
    b = sfx.Bed(T_LOOP, seed=41)
    b.pad([(0.0, (45, 52, 57, 64)), (BEAT0 + 4 * BEAT, (41, 48, 57, 60)), (BEAT0 + 8 * BEAT, (43, 50, 55, 62)),
           (T_FWD, (45, 52, 57, 64))], BEAT, g=0.05)
    penta = [0, 2, 4, 7, 9]
    for k, (bt, n) in enumerate(SIM["births"]):              # a birth beat: chord + kick
        root = 57 + 12 * ((2 * k) // 5) + penta[(2 * k) % 5]
        for q, iv in enumerate((0, 4, 7)):
            b.pluck(bt + 0.01 * q, root + iv, 0.09, d=0.5)
        tv = np.arange(int(0.25 * sfx.SR)) / sfx.SR
        b.add(bt, np.sin(2 * np.pi * np.cumsum(55 + 90 * np.exp(-tv / 0.03)) / sfx.SR) * np.exp(-tv / 0.12), 0.22)
    rng = np.random.default_rng(5)                            # marble clacks from the real collisions
    last = -1.0
    for f, e in enumerate(SIM["clacks"]):
        t = f * DT
        if e > 0.15 and t - last > 0.045:
            m = 72 + penta[rng.integers(5)] + 12 * rng.integers(2)
            g = min(0.07, 0.02 + 0.02 * e)
            tv = np.arange(int(0.12 * sfx.SR)) / sfx.SR
            sig = (np.sin(2 * np.pi * sfx.hz(m) * tv) * np.exp(-tv / 0.05)
                   + 0.4 * np.sin(2 * np.pi * sfx.hz(m) * 3.9 * tv) * np.exp(-tv / 0.01))
            b.add(t, sig, g)
            last = t
    t144 = BEAT0 + BEAT * (N_BEATS - 1)
    b.hit(t144, 0.35)
    b.chime(t144 + 0.3, (72, 76, 79, 84, 88), 0.07, decay=1.0)
    b.drop(T_FWD, T_RW, 0.05, 1500, 200)
    return b.get()


def main():
    label, rule = arg("--label", "v1"), arg("--rule", "")
    studio.OUT_DIR.mkdir(exist_ok=True)
    layout = get_layout(kit.orients()[0])
    print(f"[{SCENE}] {T_LOOP:.2f}s  births {[n for _, n in SIM['births']]}")
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
