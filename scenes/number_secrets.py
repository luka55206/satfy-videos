"""NUMBER SECRETS — "Every number from 1 to 100 has a secret" (improved take on a numbers-grid Short).

A big 10×10 grid. 18 number families light up one after another; each family's members light in a SWEEP (so the
pattern forms visibly) and every lit number plays a note (column → pentatonic pitch, so multiples of 10 sound like a
rhythm and primes sound random). Each family shows a 3-word rule. A tally runs per number; the ending is a heat map
that reveals the number that belongs to the most families (computed, not hand-picked).
Audio (original): cell notes + a bass note per family (C G Am F …) + a reveal chord.
"""
import math
import sys
from pathlib import Path

import cairo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib import kit, studio  # noqa: E402
from lib.kit import DT, FPS, arg, smooth  # noqa: E402
from lib.layouts import get_layout  # noqa: E402
from lib.studio import Canvas, VideoWriter  # noqa: E402

SCENE = "number_secrets"
NUMS = range(1, 101)


def divisors(n):
    return [d for d in range(1, n + 1) if n % d == 0]


def is_prime(n):
    return n > 1 and len(divisors(n)) == 2


def happy(n):
    seen = set()
    while n != 1 and n not in seen:
        seen.add(n)
        n = sum(int(d) ** 2 for d in str(n))
    return n == 1


def lucky_set():
    a = list(range(1, 200, 2))
    i = 1
    while i < len(a) and a[i] <= len(a):
        s = a[i]
        a = [x for k, x in enumerate(a) if (k + 1) % s]
        i += 1
    return set(x for x in a if x <= 100)


FIB = {1, 2, 3, 5, 8, 13, 21, 34, 55, 89}
LUCKY = lucky_set()
FAMILIES = [  # name, rule, colour, predicate
    ("Prime numbers", "only 2 divisors", (1.0, 0.75, 0.30), is_prime),
    ("Odd numbers", "not divisible by 2", (1.0, 0.45, 0.40), lambda n: n % 2 == 1),
    ("Multiples of 3", "3, 6, 9, 12 …", (1.0, 0.55, 0.25), lambda n: n % 3 == 0),
    ("Square numbers", "n = k × k", (0.95, 0.85, 0.35), lambda n: int(math.isqrt(n)) ** 2 == n),
    ("Triangular numbers", "1 + 2 + 3 + … + k", (0.70, 0.90, 0.35), lambda n: int(math.isqrt(8 * n + 1)) ** 2 == 8 * n + 1),
    ("Fibonacci numbers", "each = the 2 before added", (0.45, 0.90, 0.45), lambda n: n in FIB),
    ("Powers of 2", "keep doubling", (0.35, 0.90, 0.70), lambda n: n & (n - 1) == 0),
    ("Perfect numbers", "= the sum of its divisors", (0.35, 0.85, 0.95), lambda n: sum(divisors(n)[:-1]) == n),
    ("Abundant numbers", "divisors add up to MORE", (0.40, 0.70, 1.00), lambda n: sum(divisors(n)[:-1]) > n),
    ("Palindromes", "same backwards", (0.55, 0.60, 1.00), lambda n: str(n) == str(n)[::-1]),
    ("Harshad numbers", "divisible by its digit sum", (0.70, 0.55, 1.00), lambda n: n % sum(map(int, str(n))) == 0),
    ("Happy numbers", "square the digits, add … → 1", (0.85, 0.55, 1.00), happy),
    ("Lucky numbers", "survive a special sieve", (1.00, 0.55, 0.90), lambda n: n in LUCKY),
    ("Semiprimes", "prime × prime", (1.00, 0.50, 0.70), lambda n: sum(1 for d in divisors(n) if is_prime(d)) >= 1
     and any(is_prime(d) and is_prime(n // d) for d in divisors(n))),
    ("Evil numbers", "even count of 1s in binary", (1.00, 0.40, 0.50), lambda n: bin(n).count("1") % 2 == 0),
    ("Catalan numbers", "ways to pair brackets", (1.00, 0.70, 0.45), lambda n: n in {1, 2, 5, 14, 42}),
    ("Factorials", "1 × 2 × 3 × … × k", (0.95, 0.90, 0.50), lambda n: n in {1, 2, 6, 24}),
    ("Kaprekar numbers", "split n², add → n", (0.60, 0.95, 0.85), lambda n: n in {1, 9, 45, 55, 99}),
]
MEMBERS = [[n for n in NUMS if f[3](n)] for f in FAMILIES]
TALLY = {n: sum(1 for m in MEMBERS if n in m) for n in NUMS}
TOP = max(TALLY.values())
WINNERS = [n for n in NUMS if TALLY[n] == TOP]
T_FAM = 0.85
T_SWEEP = 0.42
T_END = 4.6
T_B = 2.5                                     # twist: "1 cheats" → the real winners
REAL = sorted(n for n in NUMS if n > 1 and TALLY[n] == max(v for k, v in TALLY.items() if k > 1))
REAL_TOP = TALLY[REAL[0]]
T_LOOP = len(FAMILIES) * T_FAM + T_END
GOLD = (1.0, 0.82, 0.40)


def simulate():
    return {"nf": int(round(T_LOOP * FPS))}


class Scene:
    def __init__(self, layout, sim):
        self.L, self.sim = layout, sim
        self.canvas = Canvas(layout.w, layout.h, studio.render_scale())
        w, h = layout.w, layout.h
        self.cell = w * 0.088
        self.x0 = w / 2 - 5 * self.cell
        self.y0 = h * 0.455 - 5 * self.cell

    def rect(self, x, y, s, col, a):
        ctx = self.canvas.ctx
        r = s * 0.14
        ctx.new_path()
        ctx.arc(x + s - r, y + r, r, -math.pi / 2, 0)
        ctx.arc(x + s - r, y + s - r, r, 0, math.pi / 2)
        ctx.arc(x + r, y + s - r, r, math.pi / 2, math.pi)
        ctx.arc(x + r, y + r, r, math.pi, 1.5 * math.pi)
        ctx.close_path()
        ctx.set_source_rgba(*col, a)
        ctx.fill()

    def draw(self, f, rule):
        L, c = self.L, self.canvas
        w, h = L.w, L.h
        t = f * DT
        ctx = c.ctx
        g = cairo.RadialGradient(w / 2, h * 0.45, 0, w / 2, h * 0.45, max(w, h) * 0.7)
        g.add_color_stop_rgb(0.0, 0.07, 0.06, 0.12)
        g.add_color_stop_rgb(1.0, 0.01, 0.01, 0.02)
        ctx.set_source(g)
        ctx.paint()
        T_F = len(FAMILIES) * T_FAM
        fi = min(int(t // T_FAM), len(FAMILIES) - 1)
        tl = t - fi * T_FAM
        ending = t >= T_F
        name, rl, col, _ = FAMILIES[fi]
        mem = MEMBERS[fi]
        cs = self.cell
        for n in NUMS:
            r_, c_ = (n - 1) // 10, (n - 1) % 10
            x, y = self.x0 + c_ * cs, self.y0 + r_ * cs
            pad = cs * 0.07
            self.rect(x + pad, y + pad, cs - 2 * pad, (0.16, 0.16, 0.24), 0.9)
            lit, pop = 0.0, 0.0
            if ending:
                u = smooth((t - T_F) / 0.6)
                v = TALLY[n] / TOP
                hc = (0.25 + 0.75 * v, 0.20 + 0.62 * v * v, 0.45 - 0.05 * v)
                phase_b = t > T_F + T_B
                win = (n in REAL) if phase_b else (n in WINNERS and t > T_F + 1.2)
                t_w = T_F + (T_B if phase_b else 1.2)
                s_ = 1.0 + (0.25 * smooth((t - t_w) / 0.3) if win else 0.0)
                d = (cs - 2 * pad) * s_
                self.rect(x + cs / 2 - d / 2, y + cs / 2 - d / 2, d, hc, 0.25 + 0.75 * u * (0.3 + 0.7 * v))
                if win:
                    c.glow(x + cs / 2, y + cs / 2, cs * 0.45, GOLD, strength=0.8, reach=2.5)
            elif n in mem:
                k = mem.index(n)
                t_on = T_SWEEP * k / max(1, len(mem) - 1) if len(mem) > 1 else 0.0
                if tl >= t_on:
                    age = tl - t_on
                    lit = 1.0
                    pop = math.exp(-age / 0.09)
                    out = 1 - smooth((tl - (T_FAM - 0.12)) / 0.12)
                    d = (cs - 2 * pad) * (1 + 0.22 * pop)
                    self.rect(x + cs / 2 - d / 2, y + cs / 2 - d / 2, d, col, 0.92 * out)
            tc = (0.06, 0.06, 0.1) if (lit and not ending) else (0.88, 0.88, 0.95)
            if ending:
                tc = (0.06, 0.06, 0.1) if TALLY[n] / TOP > 0.55 else (0.9, 0.9, 0.96)
            c.text_centered(str(n), y + cs * 0.62, size=cs * 0.36, color=tc, alpha=0.95, cx=x + cs / 2)
        if not ending:
            pop = math.exp(-tl / 0.12)
            c.text_centered(name, h * 0.745, size=w * 0.072 * (1 + 0.08 * pop), color=col, alpha=1.0)
            c.text_centered(rl, h * 0.785, size=w * 0.042, color=(0.92, 0.92, 0.97), alpha=0.92, bold=False)
            c.text_centered(f"{fi + 1} / {len(FAMILIES)}", h * 0.82, size=w * 0.03, color=(0.7, 0.72, 0.82),
                            alpha=0.8, bold=False)
            bx0, bx1 = w * 0.2, w * 0.8
            c.lines([(bx0, h * 0.835, bx1, h * 0.835)], (0.6, 0.62, 0.75), width=4, alpha=0.3)
            c.lines([(bx0, h * 0.835, bx0 + (bx1 - bx0) * t / T_F, h * 0.835)], col, width=4, alpha=0.9)
        else:
            if t < T_F + T_B:
                a = smooth((t - T_F - 1.1) / 0.4) * (1 - smooth((t - T_F - T_B + 0.25) / 0.25))
                c.text_centered("the most special number:", h * 0.74, size=w * 0.045, color=(0.92, 0.92, 0.97),
                                alpha=a, bold=False)
                c.text_centered(f"{WINNERS[0]}", h * 0.80, size=w * 0.12, color=GOLD, alpha=a)
                c.text_centered(f"in {TOP} of {len(FAMILIES)} families", h * 0.835, size=w * 0.036,
                                color=(0.85, 0.86, 0.92), alpha=a, bold=False)
            else:
                a = smooth((t - T_F - T_B) / 0.3)
                c.text_centered("…but 1 is in everything. The real winners:", h * 0.74, size=w * 0.040,
                                color=(0.92, 0.92, 0.97), alpha=a, bold=False)
                c.text_centered(" & ".join(map(str, REAL)), h * 0.80, size=w * 0.12, color=GOLD, alpha=a)
                c.text_centered(f"in {REAL_TOP} of {len(FAMILIES)} families each", h * 0.835, size=w * 0.036,
                                color=(0.85, 0.86, 0.92), alpha=a, bold=False)
        c.text_centered("1 TO 100 · NUMBER FAMILIES", h * 0.185, size=h * 0.0145, color=GOLD, alpha=0.85)
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


PENTA = [0, 2, 4, 7, 9]
PROG = [48, 43, 45, 41]


def build_events(sim, layout):
    out = []
    for fi, mem in enumerate(MEMBERS):
        t0 = fi * T_FAM
        out.append({"t": round(t0, 4), "note": PROG[fi % 4], "gain": 0.26, "x": layout.w / 2})
        g = 0.30 / math.sqrt(max(1.0, len(mem) / 6))
        last = -1.0
        for k, n in enumerate(mem):
            t = t0 + (T_SWEEP * k / max(1, len(mem) - 1) if len(mem) > 1 else 0.0)
            if t - last < 0.022:
                continue
            last = t
            col = (n - 1) % 10
            m = 72 + 12 * (col // 5) + PENTA[col % 5]
            out.append({"t": round(t + 0.003, 4), "note": m, "gain": g, "x": layout.w * (0.1 + 0.08 * col)})
    T_F = len(FAMILIES) * T_FAM
    for j, m in enumerate((48, 60, 64, 67, 72, 76)):
        out.append({"t": round(T_F + 0.05 * j, 4), "note": m, "gain": 0.26, "x": layout.w / 2})
    for j, m in enumerate((84, 88, 91, 96)):
        out.append({"t": round(T_F + 1.2 + 0.06 * j, 4), "note": m, "gain": 0.22, "x": layout.w / 2})
    for j, m in enumerate((53, 65, 69, 72, 77, 81)):          # the twist chord
        out.append({"t": round(T_F + T_B + 0.05 * j, 4), "note": m, "gain": 0.26, "x": layout.w / 2})
    return sorted(out, key=lambda e: e["t"])


def _worker(o, sim, label, rule):
    layout = get_layout(o)
    name = f"{SCENE}_{label}_{layout.tag}"
    video = studio.OUT_DIR / f"{name}_silent.mp4"
    d = render(layout, sim, video, rule)
    pad = kit.loop_pad(T_LOOP, ((48, 1.0), (55, 0.7), (60, 0.45), (64, 0.3)), gain=0.012)
    kit.deliver_loop(SCENE, name, layout, video, build_events(sim, layout), d, voice="glassharp", bed=pad,
                     peak_db=-6.0)


def main():
    label, rule = arg("--label", "v1"), arg("--rule", "")
    studio.OUT_DIR.mkdir(exist_ok=True)
    sim = simulate()
    if kit.has("--info"):
        for (nm, *_), m in zip(FAMILIES, MEMBERS):
            print(f"{nm:20s} {len(m):3d}  {m[:12]}")
        print("winner(s):", WINNERS, "in", TOP)
        return
    if kit.has("--still"):
        layout = get_layout(kit.orients()[0])
        f = int(arg("--frame", "0"))
        png = studio.OUT_DIR / f"{SCENE}_{label}_f{f}_{layout.tag}.png"
        render(layout, sim, png, rule, still_frame=f)
        print(f"[{SCENE}] -> {png}")
        return
    print(f"[{SCENE}] {T_LOOP:.1f}s, winner {WINNERS} ({TOP})")
    kit.fan_out(_worker, (sim, label, rule), SCENE)


if __name__ == "__main__":
    main()
