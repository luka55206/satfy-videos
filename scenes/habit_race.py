"""HABIT RACE — motivation fades, habits compound: 1.01^x overtakes a fast starter, day 0 -> 365.

Two curves race on a live, auto-rescaling graph. Teal "motivation" y = 1 + 0.5 sqrt(x) shoots up
and keeps rising, ever slower (v3: the old 6 - 5e^(-x/25) visibly levelled off and gave the ending
away); gold "1% a day" y = 1.01^x looks like nothing for months, then overtakes at day ~213 (a glow
ring + chime marks the crossing) and ends day 365 at 37.8 vs 10.6.
Days run slowly at first and faster and faster (the escalation rule). NONSTOP LOOP: after a
short hold at day 365 the lines retract and the axes shrink back to day 0, the exact frame-0
state.

v5 (owner): "talent" (y = 2x) vs "consistency" (y = 1.01^x), and an ORIGINAL orchestral score
(strings, violin-like lead, brass, timpani, cymbal swell) that builds with the race: 8 bars at
120 bpm = the loop. v6 (owner): days start at 0 and slowly (day = 1095 u^p, no linear term), never hold:
they accelerate to day 1,095 at 14.0 s and flow straight into a 2 s rewind; the overtake is on the bar-7
downbeat (12.0 s) and is named on screen ("Day 733 / consistency passes talent").
v7 (owner: never goes lower, should feel unlimited): no rewind. The days run 0 -> ~1,550 (still
accelerating at the last frame); at day 1,095 the y-axis stops chasing the gold line, which breaks out
through the top of the graph. v8 (owner: "too much infinite"): no breakout, the axes follow to the end
and the line stays inside; slower first days (u^3.5: day 1 at 2 s, day 12 at 4 s), overtake at 13.0 s,
day ~1,500 at the last frame; closing line "and it keeps growing". The orchestra stays
full to the last bar with a final roll; the loop restarts at Day 0 with a cut.

Reference: youtube.com/shorts/uAsHHO9bl1Q (x^2 vs 1.1^x race). Taken: only the generic idea of a
function race on rescaling axes with a motivational point. Ours: the functions and the message
(fading motivation vs a 1% daily habit, the real 1.01^365 = 37.8 fact), the look, HUD, caption
and the synthesised sound.

    ./run.ps1 -Scene habit_race -Fast -Still -Frame 600
    ./run.ps1 -Scene habit_race -Fast
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

SCENE = "habit_race"
DAYS = 1095                      # 3 years: 1.01^x catches 2x at day ~733 (2 years)
T_RUN, T_HOLD, T_BACK = 16.0, 0.0, 0.0           # = 8 bars of 4 at 120 bpm; never stops, never goes back
BAR = 2.0
T_CROSS = 13.0                                     # the overtake (bar 7, beat 3); roll + swell lead into it
T_LOOP = T_RUN + T_HOLD + T_BACK
TEAL = (0.25, 0.85, 0.90)
GOLD = (1.00, 0.80, 0.35)
GREY = (0.75, 0.78, 0.88)


def motivation(x):
    """v4 (owner: "2x or something simple"): the straight line y = 2x, steady hard work."""
    return 2.0 * np.asarray(x, dtype=float)


def habit(x):
    return 1.01 ** np.asarray(x, dtype=float)


def crossing():
    xs = np.linspace(20, DAYS, 400000)
    d = habit(xs) - motivation(xs)
    i = int(np.argmax(d > 0))
    return float(xs[i])


X_CROSS = crossing()


P_ACC = 3.5                                       # day = D_END u^P: very slow first days, then faster and faster
D_END = X_CROSS / (T_CROSS / T_RUN) ** P_ACC      # chosen so the overtake lands exactly at T_CROSS (~day 1,550)


def day_at(t):
    u = min(max(t / T_RUN, 0.0), 1.0)
    return D_END * u ** P_ACC


def _t_at_day(d):
    return T_RUN * (d / D_END) ** (1.0 / P_ACC)


T_FREEZE = _t_at_day(DAYS)                        # 3 years: the y-axis stops chasing the gold line
                                                  # and it breaks out through the top ("no limit")


def simulate():
    return {"nf": int(round(T_LOOP * FPS))}


def nice_step(span, n=5):
    raw = span / n
    e = math.floor(math.log10(raw))
    for m in (1, 2, 5, 10):
        if m * 10 ** e >= raw:
            return m * 10 ** e


def fmt(v):
    if v >= 100:
        return f"{v:,.0f}"
    if v >= 10:
        return f"{v:.0f}"
    return f"{v:g}"


class Scene:
    def __init__(self, layout, sim):
        self.L, self.sim = layout, sim
        self.canvas = Canvas(layout.w, layout.h, studio.render_scale())
        self.vertical = layout.h > layout.w
        w, h = layout.w, layout.h
        if self.vertical:
            self.box = (w * 0.14, h * 0.235, w * 0.93, h * 0.665)
        else:
            self.box = (w * 0.22, h * 0.14, w * 0.78, h * 0.84)

    def draw(self, f, rule):
        L, c = self.L, self.canvas
        w, h = L.w, L.h
        t = f * DT
        day = max(day_at(t), 0.0)
        ctx = c.ctx
        g = cairo.RadialGradient(w / 2, h * 0.45, 0, w / 2, h * 0.45, max(w, h) * 0.7)
        g.add_color_stop_rgb(0.0, 0.05, 0.05, 0.09)
        g.add_color_stop_rgb(1.0, 0.01, 0.01, 0.02)
        ctx.set_source(g)
        ctx.paint()

        x0, y0, x1, y1 = self.box                       # (left, top, right, bottom)
        xmax = max(2.0, day * 1.08)                      # small floor: the lines move from ~0.5 s
        dy_ = day                                        # v8: the axes always follow; the line stays inside
        ymax = max(3.0, float(max(motivation(dy_), habit(dy_))) * 1.18)

        def P(x, y):
            return x0 + (x1 - x0) * x / xmax, y1 - (y1 - y0) * y / ymax

        # grid + ticks
        sx, sy = nice_step(xmax), nice_step(ymax)
        segs = []
        k = 1
        while k * sx <= xmax:
            px, _ = P(k * sx, 0)
            segs.append((px, y0, px, y1))
            c.text_centered(fmt(k * sx), y1 + h * 0.018, size=h * 0.011, color=GREY, alpha=0.75,
                            bold=False, cx=px)
            k += 1
        k = 1
        while k * sy <= ymax:
            _, py = P(0, k * sy)
            segs.append((x0, py, x1, py))
            c.text_centered(fmt(k * sy), py + h * 0.004, size=h * 0.011, color=GREY, alpha=0.75,
                            bold=False, cx=x0 - w * 0.05, max_w=w * 0.09)
            k += 1
        c.lines(segs, GREY, width=1, alpha=0.08)
        c.lines([(x0, y1, x1 + 12, y1), (x0, y1, x0, y0 - 12)], GREY, width=2.5, alpha=0.7)
        c.text_centered("days", y1 + h * 0.040, size=h * 0.012, color=GREY, alpha=0.7, bold=False,
                        cx=x1 - w * 0.05)

        # curves
        xs = np.linspace(0, day, 600) if day > 0.01 else np.array([0.0, 0.001])
        for fn, col, wd in ((motivation, TEAL, 5), (habit, GOLD, 6)):
            pts = [P(x, y) for x, y in zip(xs, fn(xs))]
            keep = [q for q in pts if q[1] >= -40]            # the gold line may leave through the top
            if len(keep) < len(pts):                          # end it exactly at the frame edge
                i = len(keep)
                (ax, ay), (bx, by) = pts[i - 1], pts[i]
                k = (ay + 40) / (ay - by)
                keep.append((ax + (bx - ax) * k, -40))
            c.polylines([keep], col, width=wd * 4, alpha=0.10)
            c.polylines([keep], col, width=wd, alpha=0.95)
            tip = keep[-1]
            if tip[1] > 0:
                c.glow(*tip, 7, col, strength=0.6, reach=4)
                c.circle(*tip, 7, (1, 1, 1), alpha=0.95)

        # EQUATION labels at the tips (owner: "with equations"), word + value underneath.
        # The upper curve's label sits above its tip, the lower one's below, so they never touch.
        ym, yh = float(motivation(day)), float(habit(day))
        pm, ph = P(day, ym), P(day, yh)
        cx = min(max(pm[0], x0 + w * 0.30), x1 - w * 0.17)
        up_h = yh >= ym
        eq_sz = h * 0.021
        labs = []
        for (pt, up, col, base, sup, word, val) in (
                (ph, up_h, GOLD, "y = 1.01", "x", "consistency", yh),
                (pm, not up_h, TEAL, "y = 2x", "", "talent", ym)):
            y_eq = pt[1] - h * 0.040 if up else pt[1] + h * 0.042
            if not up and y_eq > y1 - h * 0.032:        # no room under a line hugging the axis:
                y_eq = pt[1] - h * 0.040                # sit just above it instead
            labs.append([y_eq, up, col, base, sup, word, val])
        gap = h * 0.052                                 # keep the two labels a label-height apart
        upper, lower = (labs[0], labs[1]) if labs[0][1] else (labs[1], labs[0])
        if lower[0] - upper[0] < gap:
            upper[0] = lower[0] - gap
        broke = ph[1] < y0                              # the gold line has left through the top
        if broke:                                       # its label rides beside the exit point
            x_exit = P(math.log(ymax) / math.log(1.01), ymax)[0]
            gx = max(x0 + w * 0.17, x_exit - w * 0.19)
        for y_eq, up, col, base, sup, word, val in labs:
            y_eq = max(y_eq, y0 + h * 0.025)
            lx = gx if (broke and col == GOLD) else cx
            self.equation(base, sup, lx, y_eq, eq_sz, col)
            vtxt = f"{val:,.0f}" if val >= 100 else f"{val:.1f}"
            if col == GOLD and ph[1] < y0:                    # broke out of the graph: point up
                vtxt += " ↑"
            c.text_centered(f"{word} · {vtxt}", y_eq + h * 0.022, size=h * 0.0125, color=col,
                            alpha=0.85, bold=False, cx=lx, max_w=w * 0.4)

        # the crossing: a ring pulse + the moment named on screen (owner: "mention surpass moment")
        if day >= X_CROSS:
            age = t - T_CROSS
            fade = 1.0
            pc = P(X_CROSS, float(habit(X_CROSS)))
            if age < 1.2:
                c.ring(*pc, 10 + 60 * smooth(age / 1.2), GOLD, width=3, alpha=0.8 * (1 - age / 1.2))
            c.circle(*pc, 6, GOLD, alpha=0.9 * fade)
            a = smooth(age / 0.35) * fade if age < 50 else fade
            if a > 0.01:
                bx, by = x0 + w * 0.22, y0 + h * 0.165
                c.text_centered(f"Day {X_CROSS:,.0f}", by, size=h * 0.019, color=GOLD, alpha=a, cx=bx)
                c.text_centered("consistency passes talent", by + h * 0.026, size=h * 0.016,
                                color=(1, 1, 1), alpha=a, bold=False, cx=bx, max_w=w * 0.6)

        # HUD
        fs = w * (0.05 if self.vertical else 0.026)
        eq_y, d_y = (h * 0.185, h * 0.77) if self.vertical else (h * 0.07, h * 0.95)
        c.text_centered(f"Day {day:,.0f}", d_y, size=fs * 1.1, color=(1, 1, 1))
        c.text_centered(f"year {int(day // 365) + 1}", d_y + fs * 0.75, size=fs * 0.55,
                        color=GREY, alpha=0.8, bold=False)
        a_end = smooth((t - (T_CROSS + 1.4)) / 0.5)           # the closing line, after the overtake
        if a_end > 0.01:
            bx = x0 + w * 0.22
            c.text_centered("and it keeps growing", y0 + h * 0.255, size=h * 0.020, color=GOLD,
                            alpha=a_end, cx=bx, max_w=w * 0.7)
        if rule:
            c.caption(rule, alpha=1.0, layout=L)
        c.watermark(L)

    def equation(self, base, sup, cx, y, size, col):
        """'base' + a raised, smaller 'sup' (a real exponent), centred on cx, soft shadow."""
        c = self.canvas
        ctx = c.ctx
        c._font(size, True)
        wb = ctx.text_extents(base).x_advance
        c._font(size * 0.62, True)
        ws = ctx.text_extents(sup).x_advance
        x = cx - (wb + ws) / 2
        for txt, sz, dx, dy in ((base, size, 0.0, 0.0), (sup, size * 0.62, wb + 2, -size * 0.42)):
            c._font(sz, True)
            ctx.set_source_rgba(0, 0, 0, 0.55)
            ctx.move_to(x + dx + 2, y + dy + 2)
            ctx.show_text(txt)
            ctx.set_source_rgba(*col, 1.0)
            ctx.move_to(x + dx, y + dy)
            ctx.show_text(txt)

    def _t_cross(self):
        lo, hi = 0.0, T_RUN
        for _ in range(40):
            mid = (lo + hi) / 2
            if day_at(mid) < X_CROSS:
                lo = mid
            else:
                hi = mid
        return hi


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
    """Only celesta-like sparkles on the two big moments; the orchestra (bed) carries the music."""
    out = []
    for j, note in enumerate((86, 90, 93)):
        out.append({"t": round(T_CROSS + 0.04 + 0.09 * j, 4), "note": note, "gain": 0.30, "x": layout.w / 2})
    for j, note in enumerate((90, 93, 98)):
        out.append({"t": round(T_RUN + 0.04 + 0.09 * j, 4), "note": note, "gain": 0.26, "x": layout.w / 2})
    return out


# ---- ORIGINAL orchestral score (inspirational, D major, 8 bars @ 120 bpm = the 16 s loop) ----------
# Composed for this clip: a standard progression (not ownable) and an original melody; synthesised
# strings / brass / timpani / cymbal swell. Bars 1-4 calm, 5 builds, 6 = the overtake (downbeat at
# 10.0 s), 7 = day 1,095 triumph, 8 fades back to bar 1 (the music loops with the video).
PROG = [(50, (62, 66, 69)), (45, (61, 64, 69)), (47, (62, 66, 71)), (43, (62, 67, 71)),
        (40, (64, 67, 71)), (45, (61, 64, 69)), (50, (62, 66, 69)), (45, (61, 64, 69))]
#        D               A               Bm              G               Em              A (build)       D (overtake)    A (still rising)
LEAD = [[(0, 2, 78), (2, 1, 81), (3, 1, 79)],
        [(0, 2, 76), (2, 1, 73), (3, 1, 76)],
        [(0, 1, 78), (1, 1, 83), (2, 1, 81), (3, 1, 78)],
        [(0, 2, 79), (2, 1, 78), (3, 1, 76)],
        [(0, 2, 79), (2, 1, 78), (3, 1, 76)],
        [(0, 1, 76), (1, 1, 79), (2, 1, 83), (3, 1, 85)],
        [(0, 3, 86), (3, 1, 81)],
        [(0, 1, 85), (1, 1, 88), (2, 2, 90)]]
DYN = [0.35, 0.40, 0.48, 0.55, 0.63, 0.78, 1.00, 1.00]   # per-bar loudness: full to the last bar


def _tone(f0, dur, sr, harm, vib=0.0, att=0.08, rel=0.2, det=(1.0,)):
    L = int((dur + rel) * sr)
    tt = np.arange(L) / sr
    env = np.clip(tt / att, 0, 1) * np.clip((dur + rel - tt) / rel, 0, 1)
    out = np.zeros(L)
    for d in det:
        v = 1 + vib * np.sin(2 * np.pi * 5.3 * tt) * np.clip((tt - 0.15) / 0.3, 0, 1)
        ph = 2 * np.pi * np.cumsum(f0 * d * v) / sr
        for k, a in harm:
            out += a * np.sin(k * ph)
    return out * env / len(det)


def orchestra(T):
    sr = audio.SR
    n = int(round(T * sr))
    out = np.zeros(n)
    beat = BAR / 4

    def put(sig, t0, g):
        idx = (np.arange(len(sig)) + int(round(t0 * sr))) % n
        np.add.at(out, idx, g * sig)

    STR = [(1, 1.0), (2, 0.5), (3, 0.33), (4, 0.22), (5, 0.15), (6, 0.1)]
    BRS = [(1, 1.0), (2, 0.8), (3, 0.6), (4, 0.45), (5, 0.3), (6, 0.2), (7, 0.12)]
    for b, (bass, chord) in enumerate(PROG):
        t0, g = b * BAR, DYN[b]
        f = audio.midi_to_hz
        put(_tone(f(bass - 12), BAR, sr, STR, att=0.25, rel=0.35, det=(0.997, 1.003)), t0, 0.55 * g)
        put(_tone(f(bass), BAR, sr, STR, att=0.25, rel=0.35, det=(0.997, 1.003)), t0, 0.35 * g)
        for m in chord:
            put(_tone(f(m), BAR, sr, STR, vib=0.004, att=0.3, rel=0.4, det=(0.996, 1.0, 1.004)), t0, 0.22 * g)
        if b in (6, 7):                                        # brass from the overtake to the end
            for m in chord:
                put(_tone(f(m - 12), BAR * 0.95, sr, BRS, att=0.12, rel=0.3, det=(0.998, 1.002)), t0, 0.20)
        for (st, ln, m) in LEAD[b]:                            # violin-like lead
            put(_tone(f(m), ln * beat * 0.97, sr, STR, vib=0.006, att=0.06, rel=0.18, det=(0.999, 1.001)),
                t0 + st * beat, 0.32 * g + 0.08)
            if b in (6, 7):                                    # cellos/horns double an octave down
                put(_tone(f(m - 12), ln * beat * 0.97, sr, BRS, att=0.08, rel=0.2), t0 + st * beat, 0.14)

    def timp(t0, g, midi=38):
        L = int(1.2 * sr)
        tt = np.arange(L) / sr
        f0 = audio.midi_to_hz(midi) * (1 + 0.25 * np.exp(-tt * 30))
        ph = 2 * np.pi * np.cumsum(f0) / sr
        rng = np.random.default_rng(int(t0 * 1000))
        hit = np.sin(ph) * np.exp(-tt * 3.2) + 0.15 * np.convolve(rng.standard_normal(L), np.ones(30) / 30, "same") * np.exp(-tt * 40)
        put(hit, t0, g)

    for k in range(16):                                        # bar-6 roll, accelerating, crescendo
        x = k / 16
        timp(T_CROSS - 1.05 + 1.0 * (x ** 1.6), 0.12 + 0.30 * x, midi=33)
    timp(T_CROSS, 0.9)                                         # the overtake
    timp(T_CROSS + 2 * beat, 0.45, midi=33)
    timp(T_CROSS + 3 * beat, 0.35, midi=38)
    timp(7 * BAR, 0.7)                                         # bar 8: it keeps climbing
    for k in range(12):                                        # a last roll building into the restart
        x = k / 12
        timp(7 * BAR + 2 * beat + 2 * beat * (x ** 1.5), 0.15 + 0.30 * x, midi=33)

    L = int(1.4 * sr)                                          # soft suspended-cymbal swell into bar 6
    rng = np.random.default_rng(7)
    noise = np.convolve(rng.standard_normal(L), np.ones(6) / 6, "same")
    swell = noise * (np.linspace(0, 1, L) ** 2.5)
    put(swell, T_CROSS - 1.4, 0.10)
    return out.astype(np.float32)


def pad(sim):
    return 0.06 * orchestra(T_LOOP)


def _worker(o, sim, label, rule):
    layout = get_layout(o)
    name = f"{SCENE}_{label}_{layout.tag}"
    video = studio.OUT_DIR / f"{name}_silent.mp4"
    d = render(layout, sim, video, rule)
    kit.deliver_loop(SCENE, name, layout, video, build_events(sim, layout), d,
                     voice="glassharp", bed=pad(sim), peak_db=-6.0)


def main():
    label, rule = arg("--label", "v1"), arg("--rule", "")
    studio.OUT_DIR.mkdir(exist_ok=True)
    sim = simulate()
    if kit.has("--still"):
        layout = get_layout(kit.orients()[0])
        f = int(arg("--frame", "600"))
        png = studio.OUT_DIR / f"{SCENE}_{label}_f{f}_{layout.tag}.png"
        render(layout, sim, png, rule, still_frame=f)
        print(f"[{SCENE}] -> {png}")
        return
    print(f"[{SCENE}] {T_LOOP:.1f}s cross at day {X_CROSS:.1f}, 1.01^365 = {float(habit(365)):.2f}")
    kit.fan_out(_worker, (sim, label, rule), SCENE)


if __name__ == "__main__":
    main()
