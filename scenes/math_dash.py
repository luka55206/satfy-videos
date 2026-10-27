"""MATH DASH — "Every level is a math graph": a neon rhythm level where the path IS a function and the sound IS that
same function (the graph you see is the waveform you hear).

STYLE ONLY of the rhythm-platformer genre our comment crowd loves: our own icon (a glowing cyan arrow-dart with a
trail), our own neon grid, spikes and music, all drawn / synthesised here. No game name, asset, icon, sound or level
from any game, on screen or in metadata.
Levels (the camera scrolls, the icon rides the graph, one beat per corner/spike, tempo 120 -> 150 BPM):
  1 THE WAVE      y = arcsin(sin x)                  a triangle wave (the straight 45° zigzag)
  2 THE BOUNCE    y = |sin x|                        the icon bounces like a ball
  3 THE TELEPORT  y = sign(sin x)                    a square wave: it snaps floor <-> ceiling
  4 THE SAW       y = x − floor(x)                   ramp up, drop
  5 THE FINALE    y = sin x + sin 3x/3 + sin 5x/5 …  the square wave builds itself from sines (Fourier), term by term
At 97% a ceiling spike nearly gets it (slow-motion graze), then "100%". The path flattens back into level 1 (loop).
Audio (original): each level's lead uses its own function as the oscillator waveform (soft triangle, rectified sine,
soft square, saw, the Fourier partial sum as it grows), a kick on every beat, off-beat hats, a riser, a chord on 100%.
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

SCENE = "math_dash"
LEVELS = [
    ("THE WAVE", "y = arcsin(sin x)", "a triangle wave", (0.35, 0.9, 1.0), 120, 3.6),
    ("THE BOUNCE", "y = |sin x|", "it bounces", (0.45, 1.0, 0.55), 128, 3.6),
    ("THE TELEPORT", "y = sign(sin x)", "a square wave", (1.0, 0.45, 0.85), 136, 3.6),
    ("THE SAW", "y = x − floor(x)", "a sawtooth", (1.0, 0.62, 0.30), 144, 3.6),
    ("THE FINALE", "y = sin x + sin 3x/3 + sin 5x/5 + …", "sines build a square", (1.0, 0.85, 0.35), 150, 4.0),
]
T_GRAZE, GRAZE_D, GRAZE_RATE = 17.55, 0.35, 0.12          # the 97% near-miss (slow motion)
T_100 = sum(L[5] for L in LEVELS)                          # 18.4 s
WHITE, SOFT = (0.96, 0.97, 1.0), (0.75, 0.78, 0.92)


def _phi_table():
    """phase (beats) at each level boundary, with the slow-motion graze inside level 5."""
    bounds, phi, t = [], 0.0, 0.0
    for name, eq, sub, col, bpm, dur in LEVELS:
        bounds.append((t, phi, bpm))
        r = bpm / 60
        if name == "THE FINALE":
            phi += r * (dur - GRAZE_D) + r * GRAZE_RATE * GRAZE_D
        else:
            phi += r * dur
        t += dur
    return bounds, phi


BOUNDS, PHI_100 = _phi_table()
_N = 2 * math.ceil((PHI_100 + 2.0) / 2)                    # the loop lands on an even beat: level 1 again
T_END = (_N - PHI_100) / 2.0                               # at 120 BPM (2 beats / s)
T_LOOP = T_100 + T_END


def phi_at(t):
    if t >= T_100:
        return PHI_100 + (t - T_100) * 2.0
    for k in range(len(LEVELS) - 1, -1, -1):
        t0, p0, bpm = BOUNDS[k]
        if t >= t0:
            r = bpm / 60
            if LEVELS[k][0] == "THE FINALE":
                a = min(t, T_GRAZE) - t0
                b = max(0.0, min(t, T_GRAZE + GRAZE_D) - T_GRAZE)
                c = max(0.0, t - T_GRAZE - GRAZE_D)
                return p0 + r * a + r * GRAZE_RATE * b + r * c
            return p0 + r * (t - t0)
    return 0.0


def level_of_phi(p):
    if p >= PHI_100:
        return 0                                           # after 100%: level 1 again
    k = 0
    for i, (t0, p0, bpm) in enumerate(BOUNDS):
        if p >= p0:
            k = i
    return k


def fourier_terms(p):
    p0 = BOUNDS[4][1]
    u = (p - p0) / (PHI_100 - p0)
    return 1 + 2 * min(4, int(u * 5))                       # 1, 3, 5, 7, 9


def path(p):
    k = level_of_phi(p)
    x = math.pi * p
    if k == 0:
        return (2 / math.pi) * math.asin(math.sin(x))
    if k == 1:
        return 2 * abs(math.sin(x)) - 1
    if k == 2:
        s = math.sin(x)
        return 0.92 * math.tanh(8 * s)                      # sign(sin x), the corners softened by a hair
    if k == 3:
        return 2 * (p - math.floor(p)) - 1
    n = fourier_terms(p)
    return 0.92 * (4 / math.pi) * sum(math.sin(m * x) / m for m in range(1, n + 1, 2)) / 1.18


class Scene:
    def __init__(self, layout):
        self.L = layout
        self.canvas = Canvas(layout.w, layout.h, studio.render_scale())

    def draw(self, f, rule):
        L, c = self.L, self.canvas
        w, h = L.w, L.h
        t = f * DT
        ctx = c.ctx
        p = phi_at(t)
        k = level_of_phi(p) if t < T_100 else 0
        name, eq, sub, col, bpm, _ = LEVELS[k]
        mid, A = h * 0.475, h * 0.125
        bpx = w * 0.24                                      # pixels per beat
        ix = w * 0.30
        beat_frac = p - math.floor(p)
        shake = 4 * math.exp(-beat_frac * 6)
        g = cairo.LinearGradient(0, 0, 0, h)
        g.add_color_stop_rgb(0, 0.03, 0.03, 0.10)
        g.add_color_stop_rgb(1, 0.01, 0.01, 0.03)
        ctx.set_source(g)
        ctx.paint()
        ctx.save()
        ctx.translate(0, shake)
        # neon grid (scrolls with the phase; periodic every beat)
        x0 = ix - beat_frac * bpx
        vl = [(x0 + j * bpx, mid - A * 2.0, x0 + j * bpx, mid + A * 2.0) for j in range(-3, 6)]
        hl = [(0, mid + q * A * 0.5, w, mid + q * A * 0.5) for q in range(-4, 5)]
        c.lines(vl + hl, col, width=1.2, alpha=0.12)
        floor_y, ceil_y = mid + A * 1.45, mid - A * 1.45
        c.lines([(0, floor_y, w, floor_y), (0, ceil_y, w, ceil_y)], col, width=4, alpha=0.8)

        def Y(v):
            return mid - v * A
        # spikes: on the floor under the path's peaks, on the ceiling over its troughs (one per half beat)
        for j in range(-6, 14):
            q = math.floor(p * 2) / 2 + j * 0.5
            sx = ix + (q - p) * bpx
            if not (-bpx < sx < w + bpx):
                continue
            vs = [path(q + dq) for dq in (-0.18, -0.09, 0.0, 0.09, 0.18)]   # the path near this spot
            col_q = LEVELS[level_of_phi(q)][3]
            hs = A * 0.38
            if min(vs) > 0.25:
                c.poly([(sx - hs * 0.5, floor_y), (sx, floor_y - hs), (sx + hs * 0.5, floor_y)], col_q, alpha=0.85)
            elif max(vs) < -0.25:
                c.poly([(sx - hs * 0.5, ceil_y), (sx, ceil_y + hs), (sx + hs * 0.5, ceil_y)], col_q, alpha=0.85)
        # the 97% spike: hangs from the ceiling and nearly touches the path
        qg = phi_at(T_GRAZE + GRAZE_D / 2)
        sx = ix + (qg - p) * bpx
        if -bpx < sx < w + bpx and t < T_100 + 1.0:
            tipy = Y(path(qg)) - A * 0.07
            c.poly([(sx - A * 0.3, ceil_y), (sx, tipy), (sx + A * 0.3, ceil_y)], (1.0, 0.35, 0.35), alpha=0.95)
            c.glow(sx, tipy, A * 0.25, (1.0, 0.35, 0.35), strength=0.4, reach=2)
        # the path: dim ahead (you see the graph coming), bright behind (the trail)
        ahead, behind = [], []
        for j in range(0, 181):
            q = p - 1.3 + j * 0.025
            pt = (ix + (q - p) * bpx, Y(path(q)))
            (behind if q <= p else ahead).append(pt)
        if ahead:
            c.polylines([[behind[-1]] + ahead if behind else ahead], col, width=3, alpha=0.35)
        if behind:
            c.polylines([behind], col, width=14, alpha=0.15)
            c.polylines([behind], col, width=5, alpha=0.95)
        # the icon: an arrow-dart pointing along the path
        y_i = Y(path(p))
        dy = (Y(path(p + 0.01)) - Y(path(p - 0.01))) / (0.02 * bpx)
        ang = math.atan(dy)
        ctx.save()
        ctx.translate(ix, y_i)
        ctx.rotate(ang)
        s = w * 0.035
        c.glow(0, 0, s * 1.6, (0.35, 0.9, 1.0), strength=0.6, reach=2.0)
        c.poly([(s * 1.1, 0), (-s * 0.8, -s * 0.7), (-s * 0.35, 0), (-s * 0.8, s * 0.7)], (0.75, 0.97, 1.0))
        ctx.restore()
        ctx.restore()
        # HUD: progress bar, level, equation (nothing in the bottom 20%)
        prog = min(1.0, t / T_100) if t < T_LOOP - 0.25 else 0.0
        if T_GRAZE <= t < T_100:
            prog = min(prog, 0.97 + 0.03 * max(0.0, (t - T_GRAZE - GRAZE_D) / (T_100 - T_GRAZE - GRAZE_D)))
        bx0, bx1, by = w * 0.12, w * 0.88, h * 0.205
        c.lines([(bx0, by, bx1, by)], (0.3, 0.32, 0.45), width=14)
        c.lines([(bx0, by, bx0 + (bx1 - bx0) * prog, by)], col, width=14)
        pct = int(prog * 100 + 1e-6)
        hit100 = T_100 <= t < T_LOOP - 0.25
        pop = 1 + 0.4 * math.exp(-(t - T_100) / 0.15) if hit100 else 1.0
        if hit100:
            c.glow(w / 2, h * 0.26, w * 0.2, (1.0, 0.85, 0.35), strength=0.4 * math.exp(-(t - T_100) / 0.6), reach=1.8)
        c.text_centered(f"{pct}%", h * 0.25, size=w * (0.07 if not hit100 else 0.1) * pop,
                        color=(1.0, 0.85, 0.35) if hit100 else WHITE)
        if T_GRAZE <= t < T_GRAZE + GRAZE_D + 0.3:
            c.text_centered("!!", h * 0.35, size=w * 0.08, color=(1.0, 0.4, 0.4))
        lv = k + 1 if t < T_100 else 1
        c.text_centered(eq, h * 0.70, size=w * 0.065, color=col, max_w=w * 0.94)
        c.text_centered(f"LEVEL {lv}/5 · {name}", h * 0.745, size=w * 0.042, color=WHITE)
        if k == 4 and t < T_100:
            n = fourier_terms(p)
            c.text_centered(f"{(n + 1) // 2} sine{'s' if n > 1 else ''} so far", h * 0.78, size=w * 0.036, color=SOFT,
                            bold=False)
        else:
            c.text_centered(sub, h * 0.78, size=w * 0.036, color=SOFT, bold=False)
        if rule:
            c.caption(rule, alpha=1.0, layout=L)
        c.watermark(L)


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


def lead(b, t0, m, d, kind, g, n_terms=1):
    """one note whose WAVEFORM is the level's function."""
    tv = np.arange(int(d * sfx.SR)) / sfx.SR
    x = 2 * np.pi * sfx.hz(m) * tv
    if kind == 0:
        sig = (2 / np.pi) * np.arcsin(np.sin(x))
    elif kind == 1:
        sig = 2 * np.abs(np.sin(x / 2)) - 1                    # |sin| at half freq so the note keeps its pitch
    elif kind == 2:
        sig = np.tanh(3 * np.sin(x))
    elif kind == 3:
        sig = sum(np.sin(k * x) / k for k in range(1, 9)) * 0.6
    else:
        sig = (4 / np.pi) * sum(np.sin(k * x) / k for k in range(1, n_terms + 1, 2)) * 0.8
    env = np.clip(tv / 0.004, 0, 1) * np.exp(-tv / (d * 0.55))
    b.add(t0, sig * env, g)


def sound():
    b = sfx.Bed(T_LOOP, seed=23)
    prog = [(57, 60, 64), (53, 57, 60), (48, 52, 55), (55, 59, 62)]    # Am F C G
    melody = [0, 2, 1, 2, 0, 2, 1, 3]
    t = 0.0
    beat_i = 0
    while t < T_LOOP - 0.01:
        p = phi_at(t)
        k = level_of_phi(p) if t < T_100 else 0
        bpm = LEVELS[k][4] if t < T_100 else 120
        beat = 60 / bpm
        if T_GRAZE <= t < T_GRAZE + GRAZE_D:
            t += 0.05
            continue
        ch = prog[(beat_i // 4) % 4]
        tone = ch[melody[beat_i % 8] % 3] + 12 * (melody[beat_i % 8] // 3)
        n_terms = fourier_terms(p) if k == 4 and t < T_100 else 1
        lead(b, t, tone + 12, beat * 0.9, k if t < T_100 else 0, 0.10, n_terms)
        lead(b, t + beat / 2, ch[(beat_i + 1) % 3] + 12, beat * 0.45, k if t < T_100 else 0, 0.05, n_terms)
        tv = np.arange(int(0.25 * sfx.SR)) / sfx.SR                    # kick on the beat
        b.add(t, np.sin(2 * np.pi * np.cumsum(50 + 120 * np.exp(-tv / 0.03)) / sfx.SR) * np.exp(-tv / 0.12), 0.35)
        b.tick(t + beat / 2, 7000, 0.05)                               # off-beat hat
        b.add(t, np.sin(2 * np.pi * sfx.hz(ch[0] - 24) * tv) * np.exp(-tv / 0.15), 0.10)   # bass
        t += beat
        beat_i += 1
    for k in range(1, 5):
        b.whoosh(BOUNDS[k][0] - 0.25, 0.4, 0.06)
    b.riser(BOUNDS[4][0] - 0.8, 0.8, 0.05)
    b.whoosh(T_GRAZE, GRAZE_D + 0.2, 0.12, up=False)
    b.tick(T_GRAZE + GRAZE_D / 2, 1800, 0.12)
    b.hit(T_100, 0.5)
    b.chime(T_100 + 0.02, (69, 72, 76, 81, 84), 0.08, decay=0.9)
    return b.get()


def main():
    label, rule = arg("--label", "v1"), arg("--rule", "")
    studio.OUT_DIR.mkdir(exist_ok=True)
    layout = get_layout(kit.orients()[0])
    if kit.has("--still"):
        f = int(round(float(arg("--at")) * FPS)) if arg("--at") else int(arg("--frame", "0"))
        png = studio.OUT_DIR / f"{SCENE}_{label}_f{f}_{layout.tag}.png"
        render(layout, png, rule, still_frame=f)
        print(f"[{SCENE}] -> {png}")
        return
    print(f"[{SCENE}] {T_LOOP:.2f}s  100% at {T_100:.1f}s")
    name = f"{SCENE}_{label}_{layout.tag}"
    video = studio.OUT_DIR / f"{name}_silent.mp4"
    d = render(layout, video, rule)
    kit.deliver_loop(SCENE, name, layout, video, [], d, voice="piano", bed=sound(), peak_db=-6.0)


if __name__ == "__main__":
    main()
