"""TUSI — the circle illusion (Tusi couple, Nasir al-Din al-Tusi, 1247). v2: payoff-first hook + Für Elise.

Dot k slides back and forth on a straight line through the centre at angle α_k:  p_k(t) = R·cos(ωt − α_k)·(cos α_k, sin α_k).
Every dot moves in a STRAIGHT line, yet together they always sit on a circle of radius R/2 that rolls inside the big one.

Timeline (7 periods = exact motion loop):
  0.0–0.9   cold open: the finished illusion (32 lines + the gold rolling circle), "THIS CIRCLE IS FAKE", chord + kick
  0.9–1.5   rewind: the lines vanish back to one
  1.6–9.4   build: each new line = the next note of Für Elise (Beethoven, public domain); the dot traces its line
  ~9.6      the tune's last note = the reveal (gold circle) + the beat drops (kick + bass)
  12.0–14.3 proof: one dot singled out, "this dot? just a straight line"
  15.3–end  "THIS CIRCLE IS FAKE" again = frame 0 (seamless)
Audio (original synthesis): piano melody/chords (events), bell shimmer on every rim touch + kick + sub bass (bed).
Mechanic after the owner's reference clip; the look, timing, explanation and sound are ours.
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

SCENE = "tusi"
NMAX = 32
P = 2.4                                       # one back-and-forth
W = 2 * math.pi / P
T_LOOP = 7 * P                                # 16.8 s
GOLD = (1.0, 0.80, 0.38)
E8 = 15.2 / 75                               # one eighth (≈0.203 s): kicks from the drop land exactly on the loop seam

# Für Elise opening (A minor), (midi, eighths)
_E5, _Ds5, _B4, _D5, _C5, _A4, _C4, _E4, _Gs4, _A3 = 76, 75, 71, 74, 72, 69, 60, 64, 68, 57
FUR = ([(_E5, 1), (_Ds5, 1)] + [(_E5, 1), (_Ds5, 1), (_E5, 1), (_B4, 1), (_D5, 1), (_C5, 1)] + [(_A4, 2)] +
       [(_C4, 1), (_E4, 1), (_A4, 1)] + [(_B4, 2)] + [(_E4, 1), (_Gs4, 1), (_B4, 1)] + [(_C5, 2)] + [(_E4, 1)] +
       [(_E5, 1), (_Ds5, 1), (_E5, 1), (_Ds5, 1), (_E5, 1), (_B4, 1), (_D5, 1), (_C5, 1)] + [(_A4, 2)] +
       [(_C4, 1), (_E4, 1), (_A4, 1)] + [(_B4, 2)] + [(_E4, 1), (_C5, 1), (_B4, 1)] + [(_A4, 3)])
T_BUILD = 1.6
FUR_T = list(T_BUILD + E8 * np.concatenate([[0], np.cumsum([d for _, d in FUR])[:-1]]))
T_REVEAL = FUR_T[-1]                          # the final A = the drop
T_SOLO0, T_SOLO1 = 12.0, 14.3
T_FAKE = 15.3                                 # the hook text returns -> matches frame 0
T_COLD, T_REW1 = 0.9, 1.45


def bitrev(i, bits=5):
    return int(format(i, f"0{bits}b")[::-1], 2)


ORDER = [bitrev(i) for i in range(NMAX)]      # each stage bisects the previous angles
ALPHA = [k * math.pi / NMAX for k in ORDER]
BIRTH = [0.0] + [FUR_T[i] for i in range(1, NMAX)]                         # line i is born on note i (note 0 on line 0)
DIE = [1e9] + [T_COLD + (T_REW1 - T_COLD) * (NMAX - 1 - i) / (NMAX - 2) for i in range(1, NMAX)]   # cold-open lines leave


def hue_col(a):
    h = (a / math.pi) % 1.0
    return tuple(0.55 + 0.45 * math.cos(2 * math.pi * (h + o)) for o in (0.0, 0.33, 0.67))


def s_of(i, t):
    return math.cos(W * t - ALPHA[i])


def alive(i, t):
    return i == 0 or t < DIE[i] or t >= BIRTH[i]


def simulate():
    return {"nf": int(round(T_LOOP * FPS))}


class Scene:
    def __init__(self, layout, sim):
        self.L, self.sim = layout, sim
        self.canvas = Canvas(layout.w, layout.h, studio.render_scale())

    def draw(self, f, rule):
        L, c = self.L, self.canvas
        w, h = L.w, L.h
        t = f * DT
        ctx = c.ctx
        cx, cy, R = w / 2, h * 0.46, w * 0.40
        g = cairo.RadialGradient(cx, cy, 0, cx, cy, max(w, h) * 0.7)
        g.add_color_stop_rgb(0.0, 0.07, 0.06, 0.11)
        g.add_color_stop_rgb(1.0, 0.01, 0.01, 0.02)
        ctx.set_source(g)
        ctx.paint()

        def XY(i, s):
            a = ALPHA[i]
            return cx + R * s * math.cos(a), cy - R * s * math.sin(a)

        live = [i for i in range(NMAX) if alive(i, t)]
        solo = T_SOLO0 <= t < T_SOLO1
        sk = smooth((t - T_SOLO0) / 0.4) * (1 - smooth((t - (T_SOLO1 - 0.4)) / 0.4))
        SOLO_I = 2                                                  # the 45° line
        beat = 0.0                                                  # big-circle pulse on the kick
        if t >= T_REVEAL or t < T_COLD:
            tb = (t - T_REVEAL) % (3 * E8) if t >= T_REVEAL else t
            beat = math.exp(-tb / 0.12)
        ctx.new_path()
        ctx.arc(cx, cy, R, 0, 2 * math.pi)
        ctx.set_source_rgba(0.55, 0.70, 1.0, 0.22 + 0.25 * beat)
        ctx.set_line_width(16 + 14 * beat)
        ctx.stroke()
        ctx.new_path()
        ctx.arc(cx, cy, R, 0, 2 * math.pi)
        ctx.set_source_rgba(0.80, 0.88, 1.0, 0.95)
        ctx.set_line_width(4)
        ctx.stroke()
        for i in live:                                              # lines
            if i == 0 or t < DIE[i] or t - BIRTH[i] >= P / 2:
                lo, hi = -1.0, 1.0
            else:
                age = t - BIRTH[i]
                ss = [s_of(i, BIRTH[i] + age * j / 30) for j in range(31)]
                lo, hi = min(ss), max(ss)
            if t < DIE[i] and DIE[i] - t < 0.12:                    # rewind: retract into the centre
                k = (DIE[i] - t) / 0.12
                lo, hi = lo * k, hi * k
            col = hue_col(ALPHA[i])
            dim = 1 - 0.8 * sk if i != SOLO_I else 1.0
            x0, y0 = XY(i, lo)
            x1, y1 = XY(i, hi)
            c.lines([(x0, y0, x1, y1)], col, width=10, alpha=0.10 * dim)
            c.lines([(x0, y0, x1, y1)], col, width=2.6, alpha=0.75 * dim)
        # the hidden circle (radius R/2, rolling inside): on in the cold open, off for the build, revealed on the drop
        rv = max(1 - smooth((t - T_COLD + 0.1) / 0.35), smooth((t - T_REVEAL) / 0.5))
        if rv > 0.01:
            ox, oy = cx + R / 2 * math.cos(W * t), cy - R / 2 * math.sin(W * t)
            for lw, a in ((20, 0.20), (4.5, 0.95)):
                ctx.new_path()
                ctx.arc(ox, oy, R / 2, 0, 2 * math.pi)
                ctx.set_source_rgba(*GOLD, a * rv * (1 - 0.6 * sk))
                ctx.set_line_width(lw + (8 * beat if lw > 10 else 0))
                ctx.stroke()
        for i in live:                                              # dots
            s = s_of(i, t)
            x, y = XY(i, s)
            col = hue_col(ALPHA[i])
            born = 1.0 if (i == 0 or t < DIE[i]) else smooth((t - BIRTH[i]) / 0.10)
            gone = 1.0 if not (t < DIE[i] and DIE[i] - t < 0.12) else (DIE[i] - t) / 0.12
            fresh = math.exp(-(t - BIRTH[i]) / 0.18) if (i and t >= BIRTH[i]) else 0.0
            dim = 1 - 0.8 * sk if i != SOLO_I else 1.0
            rim = math.exp(-(1 - abs(s)) * 40)
            r = (11 + 6 * rim + 10 * fresh) * born * gone * (1.35 if (i == SOLO_I and solo) else 1.0)
            if r < 0.5:
                continue
            c.glow(x, y, r, col, strength=(0.45 + 0.5 * rim + 0.6 * fresh) * dim, reach=3)
            c.circle(x, y, r, col, alpha=dim)
            c.circle(x - r * 0.3, y - r * 0.3, r * 0.3, (1, 1, 1), alpha=0.6 * dim)
        c.circle(cx, cy, 5, (0.9, 0.92, 1.0), alpha=0.8)
        # text
        n = len(live)
        if t < T_REW1 + 0.05 or t >= T_FAKE:
            a = 1.0 if t < T_REW1 else (smooth((t - T_FAKE) / 0.4) if t >= T_FAKE else 0.0)
            if t < T_REW1:
                a = 1.0 if t < T_COLD else max(0.0, 1 - (t - T_COLD) / 0.4)
            pop = 1.0
            c.text_centered("THIS CIRCLE IS FAKE", h * 0.75, size=w * 0.085 * pop, color=GOLD, alpha=a)
            c.text_centered("sound on", h * 0.79, size=w * 0.034, color=(0.85, 0.86, 0.92), alpha=0.8 * a, bold=False)
        elif t < T_REVEAL:
            c.text_centered(f"{n} straight line{'s' if n != 1 else ''}", h * 0.745, size=w * 0.06,
                            color=(0.95, 0.95, 1.0), alpha=0.95)
            c.text_centered("each dot only moves back and forth", h * 0.785, size=w * 0.034,
                            color=(0.75, 0.78, 0.88), alpha=0.85, bold=False)
        elif solo:
            c.text_centered("this dot? just a straight line", h * 0.745, size=w * 0.05, color=hue_col(ALPHA[SOLO_I]),
                            alpha=sk)
            c.text_centered("back and forth, forever", h * 0.785, size=w * 0.034, color=(0.75, 0.78, 0.88),
                            alpha=0.85 * sk, bold=False)
        else:
            a = smooth((t - T_REVEAL) / 0.4) * (1 - smooth((t - (T_FAKE - 0.4)) / 0.4)) if t < T_SOLO0 or t > T_SOLO1 \
                else 0.0
            c.text_centered("together they roll a circle", h * 0.745, size=w * 0.055, color=GOLD, alpha=a)
            c.text_centered("Tusi couple · al-Tusi, 1247", h * 0.785, size=w * 0.034, color=(0.75, 0.78, 0.88),
                            alpha=0.85 * a, bold=False)
        c.text_centered("CIRCLE ILLUSION", h * 0.205, size=h * 0.015, color=GOLD, alpha=0.85)
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


AM = (45, 57, 64, 69, 72)                       # A minor
PROG = [(45, (57, 64, 69, 72)), (41, (57, 65, 69, 72)), (48, (55, 64, 67, 72)), (40, (56, 64, 68, 71))]  # Am F C E


def build_events(sim, layout):
    """Piano: cold-open chord, falling run on the rewind, Für Elise (one note per new line), drop chords."""
    x = layout.w / 2
    out = [{"t": 0.0 + 0.012 * j, "note": m, "gain": 0.36, "x": x} for j, m in enumerate(AM)]
    run = [81, 76, 72, 69, 64, 60, 57]
    for j, m in enumerate(run):
        out.append({"t": round(T_COLD + 0.05 + j * 0.075, 4), "note": m, "gain": 0.20, "x": x})
    for i, (m, _) in enumerate(FUR):
        out.append({"t": round(FUR_T[i], 4), "note": m, "gain": 0.46, "x": layout.w * (0.5 + 0.3 * math.cos(ALPHA[i % NMAX]))})
        if FUR[i][1] >= 2:                                           # left-hand bass under the long notes
            out.append({"t": round(FUR_T[i], 4), "note": {69: 45, 71: 40, 72: 45}.get(m, 45), "gain": 0.22, "x": x})
    bar = 6 * E8                                                     # 2 kicks per chord
    k, tb = 0, T_REVEAL
    while tb < T_LOOP - 0.05:
        root, ch = PROG[k % 4]
        if not (T_SOLO0 + 0.2 <= tb < T_SOLO1 - 0.2):
            for j, m in enumerate(ch):
                out.append({"t": round(tb + 0.01 * j, 4), "note": m, "gain": 0.20 if k else 0.34, "x": x})
        k += 1
        tb += bar
    return sorted(out, key=lambda e: e["t"])


def rhythm_bed():
    """Bell shimmer on every rim touch (all the time), + kick and sub bass from the drop to the end and in the cold open."""
    sr = audio.SR
    n = int(round(T_LOOP * sr))
    out = np.zeros(n + sr)
    for i in range(NMAX):                                            # rim touches: ωt − α = mπ
        m = math.ceil((-ALPHA[i]) / math.pi)
        while True:
            tt = (ALPHA[i] + m * math.pi) / W
            if tt >= T_LOOP:
                break
            if tt >= 0 and alive(i, tt):
                nl = sum(1 for j in range(NMAX) if alive(j, tt))
                step = int(ALPHA[i] / math.pi * 10) % 10
                midi = 81 + 12 * (step // 5) + [0, 3, 7, 10, 12][step % 5] - 12 + (12 if m % 2 else 0)
                f = audio.midi_to_hz(midi)
                L = int(0.5 * sr)
                tv = np.arange(L) / sr
                bell = (np.sin(2 * np.pi * f * tv) + 0.3 * np.sin(2 * np.pi * 2.76 * f * tv)) * np.exp(-tv / 0.18)
                i0 = int(tt * sr)
                out[i0:i0 + L] += bell * 0.10 / math.sqrt(max(nl, 1))
            m += 1

    def kick(t0, g):
        L = int(0.35 * sr)
        tv = np.arange(L) / sr
        fr = 45 + 85 * np.exp(-tv / 0.04)
        sig = np.sin(2 * np.pi * np.cumsum(fr) / sr) * np.exp(-tv / 0.16)
        i0 = int(t0 * sr)
        out[i0:i0 + L] += g * sig

    def sub(t0, dur, midi, g):
        L = int(dur * sr)
        tv = np.arange(L) / sr
        f = audio.midi_to_hz(midi)
        env = np.clip(tv / 0.02, 0, 1) * np.clip((dur - tv) / 0.08, 0, 1)
        i0 = int(t0 * sr)
        out[i0:i0 + L] += g * env * (np.sin(2 * np.pi * f * tv) + 0.25 * np.sin(4 * np.pi * f * tv))

    kick(0.0, 0.55)
    sub(0.0, T_COLD, 33, 0.30)
    bar = 6 * E8
    k, tb = 0, T_REVEAL
    while tb < T_LOOP - 0.05:
        quiet = T_SOLO0 + 0.2 <= tb < T_SOLO1 - 0.2
        root = PROG[k % 4][0] - 12
        sub(tb, min(bar, T_LOOP - tb), root, 0.16 if quiet else 0.30)
        if not quiet:
            kick(tb, 0.55)
            if tb + 3 * E8 < T_LOOP - 0.05:
                kick(tb + 3 * E8, 0.40)
        k += 1
        tb += bar
    tail = out[n:]
    out = out[:n]
    out[: len(tail)] += tail
    return out.astype(np.float32)


def _worker(o, sim, label, rule):
    layout = get_layout(o)
    name = f"{SCENE}_{label}_{layout.tag}"
    video = studio.OUT_DIR / f"{name}_silent.mp4"
    d = render(layout, sim, video, rule)
    kit.deliver_loop(SCENE, name, layout, video, build_events(sim, layout), d, voice="piano", bed=rhythm_bed(),
                     peak_db=-6.0)


def main():
    label, rule = arg("--label", "v1"), arg("--rule", "")
    studio.OUT_DIR.mkdir(exist_ok=True)
    sim = simulate()
    if kit.has("--still"):
        layout = get_layout(kit.orients()[0])
        f = int(arg("--frame", "0"))
        png = studio.OUT_DIR / f"{SCENE}_{label}_f{f}_{layout.tag}.png"
        render(layout, sim, png, rule, still_frame=f)
        print(f"[{SCENE}] -> {png}")
        return
    print(f"[{SCENE}] {T_LOOP:.1f}s, reveal at {T_REVEAL:.2f}s, {len(FUR)} notes")
    kit.fan_out(_worker, (sim, label, rule), SCENE)


if __name__ == "__main__":
    main()
