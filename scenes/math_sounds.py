"""MATH SOUNDS — every graph sings its own shape: pitch = height of the line under the pen.

Seven functions are traced one after another by a glowing pen. The sound is not a picked
effect, it IS the graph: the pen's y-value drives the pitch (continuous voices), or each jump
of the graph rings a note (discrete voices). So the shapes become funny-but-soft characters:
the slide whistle |x|, the stairs floor(x), the lullaby sin x, the wobble sin x sin 20x, the
cliff 1/x (it dives, goes silent at the asymptote, drops back in from the top), the doorbell
sign(sin 2x), and the crush (the channel's heart equation; its pitch rides the heart's outline
and the fast wiggle becomes a soft shimmer). Little notes float off the pen.

Reference: youtube.com/shorts/OjEUM0mj0hU ("If Math Functions had a Sound"). Taken: only the
generic idea of giving functions sounds. Ours: the sonification rule (pitch = height), the
function set and nicknames, the look, and every sound (synthesised here; no samples, no memes).

Sound-first opening: --hook 1 (part 2 starts with the boing, a yellow TURN UP YOUR VOLUME prompt
on frame 0 that shrinks into a SOUND ON badge at ~1.5 s and fades out by ~3.1 s).
Part 2: --part 2 (the rocket, the zipper, the yawn, the chirp, the boing, the hopscotch, the echo).
Default --part 1 renders the first video exactly as approved.

    ./run.ps1 -Scene math_sounds -Fast -Still -Frame 300
    ./run.ps1 -Scene math_sounds -Fast
"""
import math
import random
import sys
from pathlib import Path

import cairo
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib import audio, kit, studio  # noqa: E402
from lib.kit import DT, FPS, arg, smooth  # noqa: E402
from lib.layouts import get_layout  # noqa: E402
from lib.studio import Canvas, VideoWriter  # noqa: E402

SCENE = "math_sounds"
DRAW, HOLD, FADE = 3.2, 0.35, 0.25
SEG = DRAW + HOLD + FADE
GREY = (0.75, 0.78, 0.88)


def heart(x):
    """The channel's heart equation (the heart_eq Short at a = 20): fills into a heart."""
    return np.cbrt(x * x) + 0.9 * np.sin(20 * np.pi * x) * np.sqrt(np.maximum(3.3 - x * x, 0.0))


def recip(x):
    with np.errstate(divide="ignore"):
        return np.where(np.abs(x) < 1e-9, np.nan, 1.0 / x)


# name, equation segments [(text, superscript?)], f, x-range, y-view, colour, voice, pitch range
FUNCS = [
    ("the slide whistle", [("y = |x|", False)], np.abs, (-3, 3), (-0.6, 3.4), (0.45, 1.0, 0.55), "whistle", (60, 84)),
    ("the stairs", [("y = floor(x)", False)], np.floor, (-3, 3.99), (-3.6, 3.6), (1.0, 0.80, 0.35), "steps", None),
    ("the lullaby", [("y = sin x", False)], np.sin, (-2 * math.pi, 2 * math.pi), (-1.6, 1.6), (0.45, 0.80, 1.0), "theremin", (62, 74)),
    ("the wobble", [("y = sin x · sin 20x", False)], lambda x: np.sin(x) * np.sin(20 * x), (-math.pi, math.pi), (-1.4, 1.4),
     (0.80, 0.50, 1.0), "theremin", (63, 71)),
    ("the cliff", [("y = 1/x", False)], recip, (-3, 3), (-4.0, 4.0), (1.0, 0.45, 0.45), "whistle", (52, 88)),
    ("the doorbell", [("y = sign(sin 2x)", False)], lambda x: np.sign(np.sin(2 * x)), (-3, 3), (-1.8, 1.8),
     (0.35, 0.90, 0.80), "bells", None),
    ("the crush", [("y = x", False), ("2/3", True), (" + 0.9 sin(20πx)√(3.3 − x²)", False)], heart,
     (-math.sqrt(3.3), math.sqrt(3.3)), (-2.0, 3.0), (1.0, 0.40, 0.60), "shimmer", (62, 79)),
]
# PART 2 (owner: "do another video like part 2"): seven new functions, same rule and look.
FUNCS_2 = [
    ("the rocket", [("y = x²", False)], lambda x: x * x, (-3, 3), (-0.8, 9.6), (1.0, 0.55, 0.35), "whistle", (55, 86)),
    ("the zipper", [("y = x − floor(x)", False)], lambda x: x - np.floor(x), (-3, 3), (-0.4, 1.4),
     (0.45, 0.85, 1.0), "whistle", (62, 79)),
    ("the yawn", [("y = e", False), ("−x²", True)], lambda x: np.exp(-x * x), (-3, 3), (-0.3, 1.3),
     (0.75, 0.60, 1.0), "theremin", (57, 72)),
    ("the chirp", [("y = sin(x²)", False)], lambda x: np.sin(x * x), (-4, 4), (-1.6, 1.6),
     (0.45, 1.0, 0.60), "theremin", (64, 76)),
    ("the boing", [("y = tan x", False)], np.tan, (-4, 4), (-3.2, 3.2), (1.0, 0.80, 0.35), "whistle", (55, 84)),
    ("the hopscotch", [("y = |floor(x)|", False)], lambda x: np.abs(np.floor(x)), (-3.99, 3.99), (-0.6, 4.6),
     (1.0, 0.45, 0.65), "steps", None),
    ("the echo", [("y = sin x / x", False)], lambda x: np.sinc(x / np.pi), (-12, 12), (-0.5, 1.3),
     (0.35, 0.90, 0.85), "theremin", (60, 79)),
]
def _pulse(x):
    u = (x % 2.0) - 1.0
    return np.exp(-(u * 7) ** 2) * 1.6 - 0.15 * np.exp(-((u - 0.25) * 9) ** 2)


# PART 3: seven new functions (data only; same rule and look)
with np.errstate(divide="ignore", invalid="ignore"):
    FUNCS_3 = [
        ("the panic", [("y = sin(1/x)", False)], lambda x: np.sin(1 / np.where(np.abs(x) < 1e-6, 1e-6, x)),
         (-1.2, 1.2), (-1.5, 1.5), (1.0, 0.45, 0.45), "whistle", (58, 84)),
        ("the bounce", [("y = |sin x|", False)], lambda x: np.abs(np.sin(x)), (-2 * math.pi, 2 * math.pi), (-0.3, 1.3),
         (1.0, 0.80, 0.35), "whistle", (60, 79)),
        ("the elevator", [("y = x³", False)], lambda x: x ** 3, (-2.2, 2.2), (-11, 11), (0.45, 0.85, 1.0), "whistle",
         (52, 86)),
        ("the witch", [("y = 1/(1 + x²)", False)], lambda x: 1 / (1 + x * x), (-5, 5), (-0.2, 1.2),
         (0.75, 0.55, 1.0), "theremin", (60, 76)),
        ("the heartbeat", [("y = e", False), ("−49(x mod 2 − 1)²", True)], _pulse, (-4, 4), (-0.5, 1.8),
         (1.0, 0.40, 0.60), "whistle", (57, 81)),
        ("the drunk", [("y = sin x + sin(√2·x)", False)], lambda x: np.sin(x) + np.sin(math.sqrt(2) * x),
         (-8, 8), (-2.3, 2.3), (0.45, 1.0, 0.60), "theremin", (60, 79)),
        ("the goodnight", [("y = e", False), ("−x/3", True), ("·sin(4x)", False)],
         lambda x: np.exp(-x / 3) * np.sin(4 * x), (0, 9), (-1.1, 1.1), (0.55, 0.75, 1.0),
         "theremin", (60, 74)),
    ]

PART = int(arg("--part", "1"))
if PART == 3:
    FUNCS = FUNCS_3
if PART == 2:
    FUNCS = FUNCS_2
HOOK = arg("--hook", "0") == "1"      # sound-first opening (default off = the shipped renders)
if HOOK and PART == 2:                # the funniest sound (the boing, tan x) plays on beat 1
    FUNCS = [FUNCS_2[4]] + FUNCS_2[:4] + FUNCS_2[5:]
T_LOOP = SEG * len(FUNCS)


def simulate():
    return {"nf": int(round(T_LOOP * FPS))}


def seg_at(t):
    i = min(int(t // SEG), len(FUNCS) - 1)
    return i, t - i * SEG


class Scene:
    def __init__(self, layout, sim):
        self.L, self.sim = layout, sim
        self.canvas = Canvas(layout.w, layout.h, studio.render_scale())
        self.vertical = layout.h > layout.w
        w, h = layout.w, layout.h
        self.box = (w * 0.07, h * 0.255, w * 0.93, h * 0.615) if self.vertical else (w * 0.2, h * 0.15, w * 0.8, h * 0.8)

    def draw(self, f, rule):
        L, c = self.L, self.canvas
        w, h = L.w, L.h
        t = f * DT
        i, u = seg_at(t)
        name, eq, fn, (xa, xb), (ya, yb), col, voice, _ = FUNCS[i]
        p = min(1.0, u / DRAW)
        a = 1.0 - smooth((u - DRAW - HOLD) / FADE)
        ctx = c.ctx
        g = cairo.RadialGradient(w / 2, h * 0.44, 0, w / 2, h * 0.44, max(w, h) * 0.7)
        g.add_color_stop_rgb(0.0, 0.06, 0.05, 0.10)
        g.add_color_stop_rgb(1.0, 0.01, 0.01, 0.02)
        ctx.set_source(g)
        ctx.paint()
        x0, y0, x1, y1 = self.box

        def P(x, y):
            return x0 + (x1 - x0) * (x - xa) / (xb - xa), y1 - (y1 - y0) * (y - ya) / (yb - ya)

        ax0 = P(0, 0)                                  # axes through the origin, faint grid
        c.lines([(x0, ax0[1], x1, ax0[1]), (ax0[0], y0, ax0[0], y1)], GREY, width=2, alpha=0.45)
        grid = []
        for k in range(math.ceil(xa), math.floor(xb) + 1):
            grid.append((P(k, 0)[0], y0, P(k, 0)[0], y1))
        for k in range(math.ceil(ya), math.floor(yb) + 1):
            grid.append((x0, P(0, k)[1], x1, P(0, k)[1]))
        c.lines(grid, GREY, width=1, alpha=0.06)

        # the trace so far, split wherever the graph jumps or leaves the view
        xs = np.linspace(xa, xa + (xb - xa) * p, max(2, int(900 * p)))
        ys = fn(xs)
        runs, cur = [], []
        for x, y in zip(xs, ys):
            ok = np.isfinite(y) and ya - 0.5 <= y <= yb + 0.5
            if ok and cur and abs(y - cur[-1][2]) > (yb - ya) * 0.25:
                runs.append(cur)
                cur = []
            if ok:
                cur.append((*P(x, y), y))
            elif cur:
                runs.append(cur)
                cur = []
        if cur:
            runs.append(cur)
        paths = [[(q[0], q[1]) for q in r] for r in runs if len(r) > 1]
        c.polylines(paths, col, width=18, alpha=0.10 * a)
        c.polylines(paths, col, width=5, alpha=0.95 * a)
        if runs and p < 1.0:
            px, py = runs[-1][-1][0], runs[-1][-1][1]
            c.glow(px, py, 8, col, strength=0.7, reach=4)
            c.circle(px, py, 7, (1, 1, 1), alpha=0.95)
            # little notes floating off the pen (deterministic per spawn slot)
            for k in range(int(u / 0.32) + 1):
                ts = k * 0.32
                age = (u - ts) / 1.1
                if not (0 <= age < 1) or ts > DRAW:
                    continue
                xp = xa + (xb - xa) * ts / DRAW
                yp = float(fn(np.array([xp]))[0])
                if not np.isfinite(yp) or not (ya <= yp <= yb):
                    continue
                qx, qy = P(xp, yp)
                rng = random.Random(i * 100 + k)
                c.text_centered("♪", qy - 30 - 90 * age, size=h * 0.022, color=col,
                                alpha=0.8 * (1 - age) * a, cx=qx + rng.uniform(-25, 25) * age)

        # labels: nickname above, equation below
        fs = w * (0.05 if self.vertical else 0.026)
        c.text_centered(f"{i + 1}. {name}", y0 - h * 0.022, size=fs * 0.95, color=col, alpha=a)
        self.equation(eq, w / 2, y1 + h * 0.065, fs * 0.80, (0.96, 0.95, 1.0), a)
        c.text_centered("pitch = height of the graph", y1 + h * 0.105, size=fs * 0.48, color=GREY,
                        alpha=0.7 * a, bold=False)
        if HOOK:
            self.sound_prompt(t)
        if rule:
            c.caption(rule, alpha=1.0, layout=L)
        c.watermark(L)

    def sound_prompt(self, t):
        """Frame 0: a big high-contrast 'TURN UP YOUR VOLUME' pill with a speaker and pulsing waves;
        after ~1.4 s it shrinks into a small 'sound on' badge that stays near the top."""
        c, L = self.canvas, self.L
        ctx = c.ctx
        w, h = L.w, L.h
        k = smooth((t - 1.35) / 0.35)                         # 0 = big centre pill, 1 = small badge
        fa = 1.0 - smooth((t - 2.6) / 0.5)                    # owner: the badge goes away (gone by ~3.1 s)
        if fa <= 0.0:
            return
        cx = w / 2 + (w * 0.79 - w / 2) * k                  # badge parks in the graph's top-right corner
        cy = h * 0.43 + (h * 0.285 - h * 0.43) * k
        sc = 1.0 - 0.66 * k
        bw, bh = w * 0.84 * sc, h * 0.085 * sc
        x0, y0 = cx - bw / 2, cy - bh / 2
        r = bh / 2
        ctx.new_sub_path()
        ctx.arc(x0 + bw - r, y0 + r, r, -math.pi / 2, math.pi / 2)
        ctx.arc(x0 + r, y0 + r, r, math.pi / 2, 1.5 * math.pi)
        ctx.close_path()
        ctx.set_source_rgba(1.0, 0.86, 0.25, 0.97 * fa)            # bright yellow: max contrast on the dark bg
        ctx.fill()
        # speaker icon + waves pulsing in time
        ix, iy, u = x0 + bh * 0.55, cy, bh * 0.18
        ctx.set_source_rgba(0.06, 0.05, 0.09, fa)
        ctx.rectangle(ix - u * 1.2, iy - u * 0.8, u * 1.0, u * 1.6)
        ctx.fill()
        ctx.move_to(ix - u * 0.2, iy - u * 0.8)
        ctx.line_to(ix + u * 1.0, iy - u * 1.8)
        ctx.line_to(ix + u * 1.0, iy + u * 1.8)
        ctx.line_to(ix - u * 0.2, iy + u * 0.8)
        ctx.close_path()
        ctx.fill()
        ctx.set_line_width(u * 0.45)
        for j in range(3):
            ph = (t * 2.5 - j * 0.25) % 1.0
            ctx.set_source_rgba(0.06, 0.05, 0.09, (0.35 + 0.65 * (1 - ph)) * fa)
            ctx.new_sub_path()
            ctx.arc(ix + u * 1.0, iy, u * (1.6 + 0.9 * j), -0.75, 0.75)
            ctx.stroke()
        txt = "TURN UP YOUR VOLUME" if k < 0.5 else "SOUND ON"
        t0 = ix + u * 4.6                                     # text starts after the waves
        avail = x0 + bw - r * 0.6 - t0
        fsz = bh * 0.40
        c._font(fsz, True)
        ext = ctx.text_extents(txt)
        if ext.x_advance > avail:
            fsz *= avail / ext.x_advance
            c._font(fsz, True)
            ext = ctx.text_extents(txt)
        tx = t0 + (avail - ext.x_advance) / 2
        ctx.set_source_rgba(0.06, 0.05, 0.09, fa)
        ctx.move_to(tx, cy + fsz * 0.36)
        ctx.show_text(txt)

    def equation(self, segs, cx, y, size, col, alpha):
        c = self.canvas
        ctx = c.ctx
        widths = []
        for txt, sup in segs:
            c._font(size * (0.6 if sup else 1.0), True)
            widths.append(ctx.text_extents(txt).x_advance)
        total = sum(widths)
        if total > self.L.w * 0.92:
            size *= self.L.w * 0.92 / total
            return self.equation(segs, cx, y, size, col, alpha) if size > 8 else None
        x = cx - total / 2
        for (txt, sup), wd in zip(segs, widths):
            c._font(size * (0.6 if sup else 1.0), True)
            dy = -size * 0.42 if sup else 0
            ctx.set_source_rgba(0, 0, 0, 0.5 * alpha)
            ctx.move_to(x + 2, y + dy + 2)
            ctx.show_text(txt)
            ctx.set_source_rgba(*col, alpha)
            ctx.move_to(x, y + dy)
            ctx.show_text(txt)
            x += wd


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


# ---------------- sound: the graph itself -------------------------------------------------------
def _continuous(fn, xa, xb, ya, yb, mlo, mhi, voice, sr):
    """Pitch follows y under the pen; silent where the graph is undefined / off the view."""
    n = int(DRAW * sr)
    x = xa + (xb - xa) * np.arange(n) / n
    y = fn(x)
    ok = np.isfinite(y) & (y >= ya) & (y <= yb)
    trem = 1.0
    if voice == "shimmer":                                 # the heart: pitch rides its outline, the
        y = np.cbrt(x * x) + 0.9 * np.sqrt(np.maximum(3.3 - x * x, 0.0))   # fast wiggle becomes a
        trem = 0.55 + 0.45 * np.abs(np.sin(20 * np.pi * x))                # soft shimmer in volume
        ok = np.ones_like(y, dtype=bool)
    yc = np.where(ok, y, ya)
    midi = mlo + (mhi - mlo) * (yc - ya) / (yb - ya)
    tt = np.arange(n) / sr
    if voice in ("theremin", "shimmer"):
        midi = midi + 0.25 * np.sin(2 * np.pi * 5.5 * tt)
    freq = 440.0 * 2 ** ((midi - 69) / 12)
    ph = 2 * np.pi * np.cumsum(freq) / sr
    sig = np.sin(ph) + 0.12 * np.sin(2 * ph) + 0.04 * np.sin(3 * ph)
    amp = ok.astype(float)
    k = int(0.02 * sr)                                     # 20 ms ramps at every gap / edge
    amp = np.convolve(amp, np.ones(k) / k, "same")
    env = np.clip(tt / 0.05, 0, 1) * np.clip((DRAW - tt) / 0.12, 0, 1)
    if voice == "whistle":                                 # a breath of air in a slide whistle
        rng = np.random.default_rng(3)
        sig += 0.05 * np.convolve(rng.standard_normal(n), np.ones(12) / 12, "same")
    return sig * amp * env * trem


def soundtrack_bed():
    sr = audio.SR
    n = int(round(T_LOOP * sr))
    out = np.zeros(n)
    for i, (name, eq, fn, (xa, xb), (ya, yb), col, voice, prange) in enumerate(FUNCS):
        if prange is None:
            continue
        s = _continuous(fn, xa, xb, ya, yb, prange[0], prange[1], voice, sr)
        i0 = int(round(i * SEG * sr))
        out[i0:i0 + len(s)] += s[: max(0, n - i0)]
    pad = kit.loop_pad(T_LOOP, ((50, 1.0), (57, 0.6), (62, 0.4)), gain=0.012)
    return (0.10 * out + pad[:n]).astype(np.float32)


def build_events(sim, layout):
    """Discrete voices: the stairs ring a note per step, the doorbell a ding / dong per switch,
    and the crush ends on a little chime."""
    out = []
    scale = [60, 62, 64, 65, 67, 69, 71, 72]
    for i, (name, eq, fn, (xa, xb), (ya, yb), col, voice, prange) in enumerate(FUNCS):
        t0 = i * SEG
        if voice in ("steps", "bells"):
            xs = np.linspace(xa, xb, 4000)
            ys = fn(xs)
            prev = None
            for x, y in zip(xs, ys):
                if prev is None or y != prev:
                    t = t0 + DRAW * (x - xa) / (xb - xa)
                    if voice == "steps":
                        note = scale[int(y) - int(ya + 0.6)] if 0 <= int(y) - int(ya + 0.6) < len(scale) else 60
                    else:
                        note = 76 if y > 0 else 69
                    if y != 0:
                        out.append({"t": round(t + 0.01, 4), "note": note, "gain": 0.55, "x": layout.w / 2})
                prev = y
        if name in ("the crush", "the echo"):
            for j, note in enumerate((72, 76, 79, 84)):
                out.append({"t": round(t0 + DRAW + 0.05 + 0.08 * j, 4), "note": note, "gain": 0.4, "x": layout.w / 2})
    return sorted(out, key=lambda e: e["t"])


def _worker(o, sim, label, rule):
    layout = get_layout(o)
    name = f"{SCENE}_{label}_{layout.tag}"
    video = studio.OUT_DIR / f"{name}_silent.mp4"
    d = render(layout, sim, video, rule)
    kit.deliver_loop(SCENE, name, layout, video, build_events(sim, layout), d,
                     voice="glassharp", bed=soundtrack_bed(), peak_db=-6.0)


def main():
    label, rule = arg("--label", "v1"), arg("--rule", "")
    studio.OUT_DIR.mkdir(exist_ok=True)
    sim = simulate()
    if kit.has("--still"):
        layout = get_layout(kit.orients()[0])
        f = int(arg("--frame", "300"))
        png = studio.OUT_DIR / f"{SCENE}_{label}_f{f}_{layout.tag}.png"
        render(layout, sim, png, rule, still_frame=f)
        print(f"[{SCENE}] -> {png}")
        return
    print(f"[{SCENE}] {T_LOOP:.1f}s, {len(FUNCS)} functions")
    kit.fan_out(_worker, (sim, label, rule), SCENE)


if __name__ == "__main__":
    main()
