"""FIB MILES — Fibonacci part 3: "Fibonacci converts miles to km: just take the NEXT number".

Built on the two Fibonacci winners (fib_spiral, fib_add): the same solid squares building with a zoom-out, the rule
as one big popping line, the golden spiral sweep and a rewind loop. New: every step reads as a road sign
"5 mi ≈ 8 km" (the miles square outlined cyan, the km square gold), the real value under it.
Why it works (shown, honestly): each Fibonacci number ÷ the one before -> φ = 1.618, and 1 mile = 1.609 km
(0.5 % apart). Finale: 100 mi = 89 + 8 + 3 -> 144 + 13 + 5 = 162 km (real 160.9). Rewind to frame 0.
Audio (original): a glass-harp note per conversion (rising, faster), a chime as it lands, the spiral sweep + chord,
three notes for 89 / 8 / 3 and the answer chord, falling notes on the rewind, a pad.
"""
import math
import sys
from pathlib import Path

import cairo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib import audio, kit, studio  # noqa: E402
from lib.kit import DT, FPS, arg, smooth  # noqa: E402
from lib.layouts import get_layout  # noqa: E402
from lib.studio import Canvas, VideoWriter  # noqa: E402
from scenes.fib_spiral import ARC0, eye, tiling  # noqa: E402  (shared geometry)

SCENE = "fib_miles"
N = 17                                   # squares F[0..16]: up to 1,597
K0 = 4                                   # frame 0: 5 mi (F[4]) -> ? ; first conversion lands at 0.45 s
MI_KM = 1.609344
D0, DK, DMIN = 1.05, 0.88, 0.52          # seconds per conversion: first, decay, floor
T_WHY, T_100, T_BACK = 3.2, 4.4, 1.3     # "why" + spiral sweep, the 100-mile finale, rewind
COLS = [(1.00, 0.42, 0.55), (1.00, 0.70, 0.30), (0.40, 0.85, 0.55), (0.30, 0.70, 1.00), (0.70, 0.50, 1.00)]
GOLD = (1.0, 0.82, 0.40)
CYAN = (0.35, 0.90, 1.00)
GREEN = (0.45, 1.0, 0.55)
GREY = (0.75, 0.78, 0.88)
SIGN = (0.05, 0.40, 0.22)
HUNDRED = ((10, 89), (5, 8), (3, 3))     # 100 = 89 + 8 + 3 : (index of the miles square, value)


def simulate():
    F, sq = tiling(N)
    starts, t = [], 0.45
    for k in range(K0 + 1, N):           # conversion j lands square k = K0 + 1 + j
        starts.append(t)
        t += max(DMIN, D0 * DK ** (k - K0 - 1))
    t_run = t
    t_loop = t_run + T_WHY + T_100 + T_BACK
    return {"F": F, "sq": sq, "starts": starts, "t_run": t_run, "t_loop": t_loop,
            "nf": int(round(t_loop * FPS)), "eye": eye(sq)}


def step_at(sim, t):
    """fractional number of conversions done (0 .. n); smooth rewind at the end."""
    st, tr = sim["starts"], sim["t_run"]
    n = len(st)
    t_back = tr + T_WHY + T_100
    if t >= t_back:
        return n * (1.0 - smooth(min(1.0, (t - t_back) / (T_BACK - 0.3))))     # lands 0.3 s early: exact frame 0
    if t >= tr:
        return float(n)
    if t < st[0]:
        return 0.0
    i = max(j for j in range(n) if st[j] <= t)
    end = st[i + 1] if i + 1 < n else tr
    return i + min(1.0, (t - st[i]) / max(end - st[i], 1e-6))


def ease_back(p):
    p = min(max(p, 0.0), 1.0)
    c1 = 1.70158
    return 1 + (c1 + 1) * (p - 1) ** 3 + c1 * (p - 1) ** 2


class Scene:
    def __init__(self, layout, sim):
        self.L, self.sim = layout, sim
        self.canvas = Canvas(layout.w, layout.h, studio.render_scale())
        w, h = layout.w, layout.h
        self.cy = h * 0.425
        self.half_w, self.half_h = w * 0.44, h * 0.19

    def fit(self, k):
        x0, y0, x1, y1 = self.sim["sq"][k][5]
        E = self.sim["eye"]
        return min(self.half_w / max(E.real - x0, x1 - E.real), self.half_h / max(E.imag - y0, y1 - E.imag))

    def sign(self, lines, y0, y1, alpha, pop=0.0):
        """a green highway sign with 1-2 lines of white text: [(text, size, colour)]"""
        c, w = self.canvas, self.L.w
        ctx = c.ctx
        x0, x1 = w * 0.08, w * 0.92
        r = w * 0.03
        s = 1 + 0.06 * pop
        cxm, cym = (x0 + x1) / 2, (y0 + y1) / 2
        x0, x1 = cxm - (cxm - x0) * s, cxm + (x1 - cxm) * s
        y0, y1 = cym - (cym - y0) * s, cym + (y1 - cym) * s

        def rr(a, b, c_, d, rad):
            ctx.new_path()
            ctx.arc(c_ - rad, b + rad, rad, -math.pi / 2, 0)
            ctx.arc(c_ - rad, d - rad, rad, 0, math.pi / 2)
            ctx.arc(a + rad, d - rad, rad, math.pi / 2, math.pi)
            ctx.arc(a + rad, b + rad, rad, math.pi, 1.5 * math.pi)
            ctx.close_path()
        rr(x0, y0, x1, y1, r)
        ctx.set_source_rgba(*SIGN, 0.96 * alpha)
        ctx.fill()
        rr(x0 + w * 0.012, y0 + w * 0.012, x1 - w * 0.012, y1 - w * 0.012, r * 0.7)
        ctx.set_source_rgba(1, 1, 1, 0.95 * alpha)
        ctx.set_line_width(w * 0.006)
        ctx.stroke()
        n = len(lines)
        for i, (txt, size, col) in enumerate(lines):
            yy = y0 + (y1 - y0) * (i + 0.5) / n + size * 0.36
            c.text_centered(txt, yy, size=size * s, color=col, alpha=alpha, max_w=(x1 - x0) * 0.88)

    def draw(self, f, rule):
        sim, L, c = self.sim, self.L, self.canvas
        w, h = L.w, L.h
        t = f * DT
        F, sq, E = sim["F"], sim["sq"], sim["eye"]
        n = len(sim["starts"])
        s = step_at(sim, t)
        done = int(s)
        p_new = s - done
        k_last = min(K0 + done, N - 1)                  # newest fully placed square
        lk0 = math.log(self.fit(max(k_last, K0 + 1)))
        lk1 = math.log(self.fit(min(max(k_last, K0 + 1) + 1, N - 1)))
        kp = math.exp(lk0 + (lk1 - lk0) * smooth(min(1.0, p_new / 0.4)))
        u100 = t - sim["t_run"] - T_WHY
        z = 0.0
        if 0.0 <= u100 < T_100:                          # the finale zooms in so 89 / 8 / 3 are visible
            z = smooth(min(1.0, u100 / 0.5)) * (1 - smooth(max(0.0, (u100 - (T_100 - 0.5)) / 0.5)))
            kp = math.exp(math.log(kp) + (math.log(self.fit(11)) - math.log(kp)) * z)
        ctx = c.ctx
        g = cairo.RadialGradient(w / 2, self.cy, 0, w / 2, self.cy, max(w, h) * 0.7)
        g.add_color_stop_rgb(0.0, 0.07, 0.06, 0.11)
        g.add_color_stop_rgb(1.0, 0.01, 0.01, 0.02)
        ctx.set_source(g)
        ctx.paint()

        def P(x, y):
            return w / 2 + (x - E.real) * kp, self.cy - (y - E.imag) * kp

        tr = sim["t_run"]
        t_100 = tr + T_WHY
        t_back = t_100 + T_100
        n_show = k_last + (1 if (p_new > 0 and k_last < N - 1) else 0)
        # which pair is "current": miles square km-1, km square km
        k_km = min(K0 + done + (1 if p_new > 0 else 0), N - 1) if done < n else N - 1
        if s <= 0.0:
            k_km = K0 + 1
        pair_a = 0.0 if t >= tr else 1.0
        ctx.save()
        ctx.rectangle(0, h * 0.235, w, h * 0.405)
        ctx.clip()
        rects = {}
        for k in range(n_show + 1):
            x0, y0, side, d, cen, _ = sq[k]
            pop = 1.0 if k <= k_last else ease_back(p_new / 0.55)
            if s <= 0.0 and k > K0:
                continue
            sz = side * kp * max(pop, 0.0)
            cxs, cys = P(x0 + side / 2, y0 + side / 2)
            rects[k] = (cxs, cys, sz)
            fa = 1.0 - z if k > 11 else 1.0                      # the finale keeps only the squares up to 144
            if sz < 0.8 or fa < 0.01:
                continue
            ctx.rectangle(cxs - sz / 2, cys - sz / 2, sz, sz)
            ctx.set_source_rgba(*COLS[k % len(COLS)], 0.88 * fa)
            ctx.fill_preserve()
            ctx.set_source_rgba(0.05, 0.04, 0.08, 0.9 * fa)
            ctx.set_line_width(3)
            ctx.stroke()
            if sz > 36:
                fs = min(sz * 0.36, h * 0.07)
                c.text_centered(f"{F[k]:,}", cys + fs * 0.36, size=fs, color=(0.06, 0.05, 0.09),
                                alpha=min(1.0, (sz - 36) / 40) * fa, cx=cxs, max_w=sz * 0.86)
        # the current pair: miles = cyan, km = gold, with little tags
        if pair_a > 0:
            for k, col, tag in ((k_km - 1, CYAN, "mi"), (k_km, GOLD, "km")):
                if k in rects and (s > 0 or k == K0):
                    cxs, cys, sz = rects[k]
                    if sz < 2:
                        continue
                    ctx.rectangle(cxs - sz / 2, cys - sz / 2, sz, sz)
                    ctx.set_source_rgba(*col, 0.95)
                    ctx.set_line_width(max(4, w * 0.008))
                    ctx.stroke()
                    if sz > 60:
                        c.text_centered(tag, cys + sz * 0.42, size=min(sz * 0.14, h * 0.025), color=(0.06, 0.05, 0.09),
                                        cx=cxs, max_w=sz * 0.8)
        # the 100-mile finale: glow the squares 89, 8, 3 then 144, 13, 5
        if t_100 <= t < t_back:
            u = t - t_100
            for j, (k, v) in enumerate(HUNDRED):
                for kk, col, t_on in ((k, CYAN, 0.35 + 0.3 * j), (k + 1, GOLD, 1.9 + 0.3 * j)):
                    if u >= t_on and kk in rects:
                        cxs, cys, sz = rects[kk]
                        a = min(1.0, (u - t_on) / 0.2)
                        ctx.rectangle(cxs - sz / 2, cys - sz / 2, sz, sz)
                        ctx.set_source_rgba(*col, a)
                        ctx.set_line_width(max(4, w * 0.009))
                        ctx.stroke()
                        c.glow(cxs, cys, max(sz * 0.6, w * 0.02), col, strength=0.35 * a * math.exp(-(u - t_on) / 0.5),
                               reach=2.0)
        ctx.restore()

        # the spiral sweep while the "why" is told
        if tr <= t < t_back + 0.2:
            sweep = smooth((t - tr) / 1.2)
            out = 1.0 - smooth((t - t_100 - 0.2) / 0.5)
            if out > 0:
                total = sweep * N
                arcs = []
                for k in range(N):
                    part = min(1.0, max(0.0, total - k))
                    if part <= 0:
                        break
                    x0, y0, side, d, cen, _ = sq[k]
                    a0 = math.radians(ARC0[d])
                    arcs.append([P(cen[0] + side * math.cos(a0 + math.pi / 2 * part * i / 24),
                                   cen[1] + side * math.sin(a0 + math.pi / 2 * part * i / 24)) for i in range(25)])
                c.polylines(arcs, GOLD, width=26, alpha=0.18 * out)
                c.polylines(arcs, (1.0, 0.92, 0.70), width=8, alpha=0.95 * out)

        # the sign + the real value
        fs = w * 0.085
        y0s, y1s = h * 0.655, h * 0.745
        if t < tr or t >= t_back:
            mi, km = F[k_km - 1], F[k_km]
            landed = s > 0
            pe = math.exp(-((p_new if done < n else 1.0)) / 0.22) if (landed and t < tr) else 0.0
            txt = f"{mi:,} mi  ≈  {km:,} km" if landed else f"{F[K0]:,} mi  ≈  ?  km"
            self.sign([(txt, fs, (1, 1, 1))], y0s, y1s, 1.0, pe)
            if landed:
                real = mi * MI_KM
                err = abs(km / real - 1) * 100
                c.text_centered(f"real:  {mi:,} mi = {real:,.2f} km", h * 0.785, size=w * 0.042, color=GREY,
                                max_w=w * 0.92)
                c.text_centered(f"off by only {err:.1f} %", h * 0.815, size=w * 0.036, color=GREEN, max_w=w * 0.9)
            else:
                c.text_centered("just take the NEXT Fibonacci number", h * 0.785, size=w * 0.042, color=GREY)
        elif t < t_100:
            a = min(1.0, (t - tr) / 0.25)
            self.sign([("next ÷ this  →  φ = 1.618", fs * 0.62, GOLD), ("1 mile = 1.609 km", fs * 0.62, (1, 1, 1))],
                      h * 0.640, h * 0.765, a)
            if t - tr > 1.2:
                c.text_centered("almost the same number: 0.5 % apart", h * 0.80, size=w * 0.042, color=GREEN,
                                alpha=min(1.0, (t - tr - 1.2) / 0.3))
        else:
            u = t - t_100
            a = min(1.0, u / 0.25)
            l1 = "100 mi = 89 + 8 + 3"
            l2 = "→ 144 + 13 + 5 = 162 km" if u >= 1.9 else "→  ?"
            self.sign([(l1, fs * 0.62, CYAN), (l2, fs * 0.62, GOLD if u >= 1.9 else (1, 1, 1))],
                      h * 0.640, h * 0.765, a, math.exp(-max(0.0, u - 1.9) / 0.2) if u >= 1.9 else 0.0)
            if u >= 2.9:
                c.text_centered("real: 160.9 km", h * 0.80, size=w * 0.042, color=GREEN, alpha=min(1.0, (u - 2.9) / 0.3))
        c.text_centered("FAMOUS NUMBERS · FIBONACCI", h * 0.224, size=h * 0.015, color=GOLD, alpha=0.8)
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


def build_events(sim, layout):
    walker = audio.ScaleWalker(root_midi=60, scale=audio.PENTA_MAJOR, span=14, pattern="up")
    out, n = [], len(sim["starts"])
    w = layout.w
    for i, t in enumerate(sim["starts"]):
        out.append({"t": round(t, 4), "note": walker.next(), "gain": round(0.40 + 0.14 * i / n, 3), "x": w / 2})
        out.append({"t": round(t + 0.07, 4), "note": 86 if i % 2 else 88, "gain": 0.18, "x": w * 0.6})
    tr = sim["t_run"]
    for j, note in enumerate((60, 64, 67, 72, 76, 79, 84)):          # the spiral sweep
        out.append({"t": round(tr + 0.15 * j, 4), "note": note, "gain": 0.30, "x": w / 2})
    for j, note in enumerate((48, 55, 60, 64, 67)):                  # "φ ≈ 1.609"
        out.append({"t": round(tr + 1.2 + 0.05 * j, 4), "note": note, "gain": 0.40, "x": w / 2})
    t1 = tr + T_WHY
    for j, note in enumerate((67, 72, 76)):                          # 89, 8, 3
        out.append({"t": round(t1 + 0.35 + 0.3 * j, 4), "note": note, "gain": 0.34, "x": w * (0.4 + 0.1 * j)})
    for j, note in enumerate((69, 74, 77)):                          # 144, 13, 5
        out.append({"t": round(t1 + 1.9 + 0.3 * j, 4), "note": note, "gain": 0.34, "x": w * (0.4 + 0.1 * j)})
    for j, note in enumerate((50, 57, 62, 66, 69)):                  # = 162 km
        out.append({"t": round(t1 + 2.9 + 0.05 * j, 4), "note": note, "gain": 0.42, "x": w / 2})
    t_back = t1 + T_100
    for j, note in enumerate((79, 76, 72, 69, 67)):
        out.append({"t": round(t_back + 0.05 + 0.24 * j, 4), "note": note, "gain": 0.22, "x": w / 2})
    return sorted(out, key=lambda e: e["t"])


def main():
    label, rule = arg("--label", "v1"), arg("--rule", "")
    studio.OUT_DIR.mkdir(exist_ok=True)
    sim = simulate()
    layout = get_layout(kit.orients()[0])
    if kit.has("--still"):
        f = int(round(float(arg("--at")) * FPS)) if arg("--at") else int(arg("--frame", "0"))
        png = studio.OUT_DIR / f"{SCENE}_{label}_f{f}_{layout.tag}.png"
        render(layout, sim, png, rule, still_frame=f)
        print(f"[{SCENE}] -> {png}")
        return
    print(f"[{SCENE}] {sim['t_loop']:.2f}s run={sim['t_run']:.2f}s")
    name = f"{SCENE}_{label}_{layout.tag}"
    video = studio.OUT_DIR / f"{name}_silent.mp4"
    d = render(layout, sim, video, rule)
    pad = kit.loop_pad(sim["nf"] / FPS, ((48, 1.0), (55, 0.7), (60, 0.45), (64, 0.3)), gain=0.015)
    kit.deliver_loop(SCENE, name, layout, video, build_events(sim, layout), d, voice="glassharp", bed=pad)


if __name__ == "__main__":
    main()
