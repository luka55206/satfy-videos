"""PI CANON — the digits of π play a melody over Pachelbel's Canon (PD, ~1680), drawn as π string art.

Readable by anyone: a big ribbon of π's digits (3.14159…) scrolls across the top, and the digit playing NOW sits in
a gold box. That same digit glows big in the middle of the circle, its arc on the ring flashes, and a coloured
string is drawn from the previous digit's arc to this one, so the strings weave π string art.
Higher digit = higher note: the digit d picks tone d % 3 of the current Canon chord, octave d // 3.
Digits come 2 per beat, then 4, 8, 16, 32 (the rate climbs to the end). After the final chord the artwork folds into
the centre and becomes the "3" that starts the next loop, while the ribbon rewinds to "3.": a continuous loop.
Audio: original synthesis only (glass-voice digits, cello-like Canon bass + string pad).
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

SCENE = "pi_canon"
NUMBER = arg("--number", "pi")                   # pi | e | phi | sqrt2  (episode change: the number)
SONG = arg("--song", "canon")                     # canon | prelude      (and the famous piece)
SYM = {"pi": "π", "e": "e", "phi": "φ", "sqrt2": "√2"}[NUMBER]
if SONG == "canon":
    CBPM = 78.0
    CANON_ROOTS = [38, 33, 35, 30, 31, 26, 31, 33]
    CANON_CHORDS = [(62, 66, 69), (61, 64, 69), (62, 66, 71), (61, 66, 69), (62, 67, 71), (62, 66, 69), (62, 67, 71),
                    (61, 64, 69)]
    CANON_NAMES = ["D", "A", "Bm", "F#m", "G", "D", "G", "A"]
    SONG_NAME = "Pachelbel's Canon"
    FINAL = (50, 57, 62, 66, 69, 74)
    V10 = None
    FUR = None
elif SONG == "furelise":   # Beethoven, Für Elise (PD): the famous melody plays under the digits; digits = chord tones
    CBPM = 70.0
    AM, EM = (45, 48, 52, 57, 60, 64, 69, 72, 76, 81), (44, 47, 52, 56, 59, 64, 68, 71, 76, 80)
    CANON_ROOTS = [33, 33, 28, 33, 33, 33, 28, 33]
    CANON_CHORDS = [(57, 60, 64), (57, 60, 64), (56, 59, 64), (57, 60, 64), (57, 60, 64), (57, 60, 64), (56, 59, 64),
                    (57, 60, 64)]
    CANON_NAMES = ["Am", "Am", "E", "Am", "Am", "Am", "E", "Am"]
    SONG_NAME = "Für Elise"
    FINAL = (33, 45, 57, 60, 64, 69)
    V10 = [list(AM if n.startswith("A") else EM) for n in CANON_NAMES]
    T16 = [(76, .25), (75, .25), (76, .25), (75, .25), (76, .25), (71, .25), (74, .25), (72, .25)]
    FUR = (T16 + [(69, 1.0), (60, 1 / 3), (64, 1 / 3), (69, 1 / 3)] + [(71, 1.0), (64, 1 / 3), (68, 1 / 3), (71, 1 / 3)] +
           [(72, 1.0), (64, 0.5), (76, 0.25), (75, 0.25)] + T16 + [(69, 1.0), (60, 1 / 3), (64, 1 / 3), (69, 1 / 3)] +
           [(71, 1.0), (64, 1 / 3), (72, 1 / 3), (71, 1 / 3)] + [(69, 2.0)])          # 16 beats (beats per note)
else:   # Bach, Prelude in C (WTC I, PD): its first 8 bars, each a 5-note broken chord
    CBPM = 72.0
    PRE5 = [(48, 52, 55, 60, 64), (48, 50, 57, 62, 65), (47, 50, 55, 62, 65), (48, 52, 55, 60, 64),
            (48, 52, 57, 64, 69), (48, 50, 54, 57, 62), (47, 50, 55, 62, 67), (47, 48, 52, 55, 60)]
    CANON_ROOTS = [v[0] - 12 for v in PRE5]
    CANON_CHORDS = [v[2:] for v in PRE5]
    CANON_NAMES = ["C", "Dm7", "G7", "C", "Am", "D7", "G", "Cmaj7"]
    SONG_NAME = "Bach's Prelude in C"
    FINAL = (36, 48, 55, 60, 64, 67, 72)
    V10 = [list(v) + [x + 12 for x in v] for v in PRE5]   # digit d -> note d of the chord's two-octave voicing
    FUR = None
CB = 60.0 / CBPM
DIV = [2, 2, 2, 2, 4, 4, 4, 4, 8, 8, 8, 8, 16, 16, 32, 32]
T_RUN = 16 * CB                       # digits play
T_BLOOM = 0.55                        # finished art glows on the final chord
T_FOLD = 2 * CB - T_BLOOM             # art folds into the centre "3", ribbon rewinds
T_LOOP = T_RUN + T_BLOOM + T_FOLD
GOLD = (1.0, 0.82, 0.40)

TD = np.array([bi * CB + j * CB / dv for bi, dv in enumerate(DIV) for j in range(dv)])
N_DIG = len(TD)


def pi_digits(n):
    """Rabinowitz-Wagon spigot: the first n digits of pi as ints (3, 1, 4, 1, 5, …)."""
    out = []
    q, r, t, k, m, x = 1, 0, 1, 1, 3, 3
    while len(out) < n:
        if 4 * q + r - t < m * t:
            out.append(m)
            q, r, m = 10 * q, 10 * (r - m * t), (10 * (3 * q + r)) // t - 10 * m
        else:
            q, r, t, k, m, x = q * k, (2 * q + r) * x, t * x, k + 1, (q * (7 * k + 2) + r * x) // (t * x), x + 2
    return out


def const_digits(name, n):
    """Digits of e, φ or √2 (integer part first), exact via decimal arithmetic."""
    from decimal import Decimal, getcontext
    getcontext().prec = n + 20
    if name == "e":
        v, term, k = Decimal(1), Decimal(1), 1
        while term > Decimal(10) ** -(n + 15):
            term /= k
            v += term
            k += 1
    elif name == "phi":
        v = (1 + Decimal(5).sqrt()) / 2
    else:
        v = Decimal(2).sqrt()
    txt = str(v).replace(".", "")
    return [int(ch) for ch in txt[:n]]


DIG = pi_digits(N_DIG + 40) if NUMBER == "pi" else const_digits(NUMBER, N_DIG + 40)


def dcol(d):
    h = d / 10.0
    return tuple(0.55 + 0.45 * math.cos(2 * math.pi * (h + o)) for o in (0.0, 0.33, 0.67))


def chord_at(t):
    return int(min(max(t, 0.0), T_RUN - 1e-6) // (2 * CB)) % 8


def canon_note(i):
    """Higher digit = higher note: tone d % 3 of the current chord, octave d // 3 (0..3)."""
    d = DIG[i]
    if V10 is not None:
        return V10[chord_at(TD[i])][d]
    return CANON_CHORDS[chord_at(TD[i])][d % 3] - 12 + 12 * (d // 3)


def simulate():
    return {"nf": int(round(T_LOOP * FPS))}


class Scene:
    def __init__(self, layout, sim):
        self.L, self.sim = layout, sim
        self.canvas = Canvas(layout.w, layout.h, studio.render_scale())
        w, h = layout.w, layout.h
        self.cx, self.cy, self.R = w / 2, h * 0.505, w * 0.33
        c = self.canvas
        self.art = cairo.ImageSurface(cairo.FORMAT_ARGB32, c.pw, c.ph)
        self.actx = cairo.Context(self.art)
        self.actx.scale(c.pw / w, c.ph / h)
        self.actx.set_operator(cairo.OPERATOR_ADD)
        self.done = 0

    def anchor(self, d, i):
        a = -math.pi / 2 + (d + 0.10 + 0.80 * ((i * 0.618) % 1.0)) * 2 * math.pi / 10
        return self.cx + self.R * math.cos(a), self.cy + self.R * math.sin(a)

    def string(self, i, ctx, alpha, width):
        d0, d1 = DIG[i - 1], DIG[i]
        x0, y0 = self.anchor(d0, i - 1)
        x1, y1 = self.anchor(d1, i)
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2
        qx, qy = mx + (self.cx - mx) * 0.5, my + (self.cy - my) * 0.5
        g = cairo.LinearGradient(x0, y0, x1, y1)
        g.add_color_stop_rgba(0, *dcol(d0), alpha)
        g.add_color_stop_rgba(1, *dcol(d1), alpha)
        ctx.move_to(x0, y0)
        ctx.curve_to(qx, qy, qx, qy, x1, y1)
        ctx.set_source(g)
        ctx.set_line_width(width)
        ctx.stroke()

    def catch_up(self, n_now):
        while self.done < n_now:
            if self.done >= 1:
                self.string(self.done, self.actx, 0.30, 1.7)
            self.done += 1

    def ribbon(self, t, n_now):
        """π's digits as a scrolling ribbon; the playing digit sits in the gold box at the centre."""
        c, L = self.canvas, self.L
        w, h = L.w, L.h
        y, step, fs = h * 0.240, w * 0.085, w * 0.075
        if t < T_RUN:
            i = max(n_now - 1, 0)
            pos = float(i)                                       # the ribbon ticks one digit per note
            hl = i                                               # the box always shows the digit playing now
        else:                                                    # rewind to "3." while the art folds
            u = smooth((t - T_RUN - T_BLOOM) / T_FOLD)
            pos = (N_DIG - 1) * (1 - u)
            hl = int(round(pos))
        k0 = hl
        box_w, box_h = step * 1.05, fs * 1.45
        ctx = c.ctx
        ctx.new_path()
        x0, y0r = w / 2 - box_w / 2, y - box_h * 0.72
        r = 14
        ctx.arc(x0 + box_w - r, y0r + r, r, -math.pi / 2, 0)
        ctx.arc(x0 + box_w - r, y0r + box_h - r, r, 0, math.pi / 2)
        ctx.arc(x0 + r, y0r + box_h - r, r, math.pi / 2, math.pi)
        ctx.arc(x0 + r, y0r + r, r, math.pi, 1.5 * math.pi)
        ctx.close_path()
        ctx.set_source_rgba(*GOLD, 0.18)
        ctx.fill_preserve()
        ctx.set_source_rgba(*GOLD, 0.95)
        ctx.set_line_width(3)
        ctx.stroke()
        for k in range(int(pos) - 7, int(pos) + 9):
            if k < 0:
                continue
            dx = (k - pos) * step
            x = w / 2 + dx
            if x < -step or x > w + step:
                continue
            fade = max(0.0, 1 - abs(dx) / (w * 0.52))
            here = k == k0
            col = dcol(DIG[k]) if k <= k0 else (0.85, 0.86, 0.92)
            a = (1.0 if here else (0.75 if k < k0 else 0.35)) * fade
            c.text_centered(str(DIG[k]) + ("." if k == 0 else ""), y, size=fs * (1.12 if here else 1.0), color=col, alpha=a, cx=x)
        c.text_centered(f"{SYM} =", y, size=fs * 0.8, color=GOLD, alpha=0.0 if pos > 2 else 0.9 * (1 - pos / 2),
                        cx=w / 2 - step * 1.6)
        c.text_centered(f"digit #{k0 + 1}", y + box_h * 0.62, size=h * 0.016, color=GOLD, alpha=0.9)

    def draw(self, f, rule):
        L, c = self.L, self.canvas
        w, h = L.w, L.h
        t = f * DT
        ctx = c.ctx
        g = cairo.RadialGradient(w / 2, self.cy, 0, w / 2, self.cy, max(w, h) * 0.7)
        g.add_color_stop_rgb(0.0, 0.07, 0.06, 0.11)
        g.add_color_stop_rgb(1.0, 0.01, 0.01, 0.02)
        ctx.set_source(g)
        ctx.paint()
        n_now = int(np.searchsorted(TD, t, side="right"))
        self.catch_up(n_now)
        fold = smooth((t - T_RUN - T_BLOOM) / T_FOLD)
        bloom = math.exp(-max(0.0, t - T_RUN) / 0.35) if t >= T_RUN else 0.0
        s = 1 - fold                                           # the art folds into the centre
        if s > 0.002:
            ctx.save()
            ctx.translate(self.cx, self.cy)
            ctx.rotate(-fold * math.pi * 0.8)
            ctx.scale(s, s)
            ctx.translate(-self.cx, -self.cy)
            ctx.scale(w / c.pw, h / c.ph)
            ctx.set_source_surface(self.art, 0, 0)
            ctx.paint_with_alpha(min(1.0, 1.0 + bloom))
            if bloom > 0.01:
                ctx.set_operator(cairo.OPERATOR_ADD)
                ctx.set_source_surface(self.art, 0, 0)
                ctx.paint_with_alpha(0.8 * bloom)
                ctx.set_operator(cairo.OPERATOR_OVER)
            ctx.restore()
        # the newest strings: bright, thick, fading into the art
        if t < T_RUN:
            for j in range(max(1, n_now - 6), n_now):
                age = t - TD[j]
                a = max(0.0, 0.95 - age * 2.2)
                if a > 0.01:
                    self.string(j, ctx, a, 4.0)
        # ring of 10 digit arcs (it also folds away and comes back)
        ring = 1.0 if t < T_RUN + T_BLOOM else 1 - math.sin(math.pi * fold) * 0.0
        cur_d = DIG[n_now - 1] if (1 <= n_now and t < T_RUN) else None
        age = t - TD[n_now - 1] if cur_d is not None else 9.0
        pop = math.exp(-age / 0.12)
        for d in range(10):
            a0 = -math.pi / 2 + d * 2 * math.pi / 10 + 0.025
            a1 = a0 + 2 * math.pi / 10 - 0.05
            p = pop if d == cur_d else 0.0
            ctx.new_sub_path()
            ctx.arc(self.cx, self.cy, self.R + 12, a0, a1)
            ctx.set_source_rgba(*dcol(d), 0.55 + 0.45 * p)
            ctx.set_line_width((12 + 14 * p) * ring)
            ctx.stroke()
            am = (a0 + a1) / 2
            rr = self.R + 58
            c.text_centered(str(d), self.cy + rr * math.sin(am) + w * 0.018, size=w * 0.048 * (1 + 0.45 * p),
                            color=dcol(d), alpha=0.6 + 0.4 * p, cx=self.cx + rr * math.cos(am))
        # the playing digit, big in the centre; during the fold it becomes the "3" of the next loop
        if t < T_RUN:
            d = cur_d if cur_d is not None else DIG[0]
            sz = w * 0.16 * (1 + 0.25 * pop)
            c.glow(self.cx, self.cy, w * 0.05, dcol(d), strength=0.35 + 0.5 * pop, reach=3)
            c.text_centered(str(d), self.cy + sz * 0.36, size=sz, color=dcol(d), alpha=0.95)
        else:
            sz = w * 0.16 * fold
            if sz > 2:
                c.glow(self.cx, self.cy, w * 0.05 * fold, dcol(DIG[0]), strength=0.35 * fold, reach=3)
                c.text_centered(str(DIG[0]), self.cy + sz * 0.36, size=sz, color=dcol(DIG[0]), alpha=0.95 * fold)
        self.ribbon(t, n_now)
        ch = CANON_NAMES[chord_at(t)] if t < T_RUN else CANON_NAMES[0]
        c.text_centered("each digit plays a note · higher digit = higher note", h * 0.760, size=w * 0.031,
                        color=(0.85, 0.86, 0.92), alpha=0.85, bold=False)
        c.text_centered(f"{SONG_NAME} chords:  {ch}", h * 0.790, size=w * 0.036, color=GOLD, alpha=0.9)
        if rule:
            c.caption(rule, alpha=1.0, layout=L)
        c.watermark(L)


def render(layout, sim, out_path, rule, still_frame=None):
    sc = Scene(layout, sim)
    writer = None if still_frame is not None else VideoWriter(out_path, sc.canvas, FPS)
    for f in range(sim["nf"]):
        if still_frame is not None and f != still_frame:
            sc.catch_up(int(np.searchsorted(TD, f * DT, side="right")))
            continue
        sc.draw(f, rule)
        if writer is None:
            studio.save_still(sc.canvas, out_path)
            return f / FPS
        writer.write_frame()
    writer.close()
    return sim["nf"] / FPS


def build_events(sim, layout):
    out, last = [], -1.0
    for i, t in enumerate(TD):
        if t - last < 0.045:
            continue
        last = t
        out.append({"t": round(float(t) + 0.004, 4), "note": canon_note(i), "gain": 0.30 if FUR else 0.40,
                    "x": layout.w * (0.5 + 0.3 * math.sin(DIG[i] * 0.63))})
    for j, note in enumerate(FINAL):                                      # final chord
        out.append({"t": round(T_RUN + 0.04 * j, 4), "note": note, "gain": 0.40, "x": layout.w / 2})
    t0 = T_RUN + T_BLOOM + 0.05                                            # soft falling run as the art folds
    for j, note in enumerate((86, 81, 78, 74, 69, 66, 62)):
        out.append({"t": round(t0 + j * (T_FOLD - 0.25) / 7, 4), "note": note, "gain": 0.16, "x": layout.w / 2})
    return sorted(out, key=lambda e: e["t"])


def canon_bed():
    """Pachelbel's Canon (public domain): the bassline (cello-like half notes) + soft string chords."""
    sr = audio.SR
    n = int(round(T_LOOP * sr))
    out = np.zeros(n)
    for k in range(9):
        ci = k % 8 if k < 8 else 0
        t0 = k * 2 * CB
        L = 2 * CB * (1.0 if k < 8 else 0.98)
        i0 = int(t0 * sr)
        tt = np.arange(int(L * sr)) / sr
        f0 = audio.midi_to_hz(CANON_ROOTS[ci])
        ph = 2 * np.pi * f0 * tt
        cello = (np.sin(ph) + 0.5 * np.sin(2 * ph) + 0.25 * np.sin(3 * ph)) * np.clip(tt / 0.05, 0, 1) * np.exp(-tt * 0.6)
        pad = np.zeros(len(tt))
        for m in CANON_CHORDS[ci]:
            fp = audio.midi_to_hz(m - 12)
            pad += np.sin(2 * np.pi * fp * tt) + 0.4 * np.sin(4 * np.pi * fp * tt)
        pad *= np.clip(tt / 0.25, 0, 1) * np.clip((L - tt) / 0.3, 0, 1) / 3
        seg = (0.32 * cello + 0.16 * pad) * (np.clip((L - tt) / 0.4, 0, 1) if k == 8 else 1.0)
        i1 = min(n, i0 + len(seg))
        out[i0:i1] += seg[: i1 - i0]
    if FUR:                                                               # the melody (soft piano, our synthesis)
        t = 0.0
        for m, d in FUR:
            dur = d * CB
            tt = np.arange(int((dur + 0.5) * sr)) / sr
            f = audio.midi_to_hz(m)
            sig = sum(a * np.sin(2 * np.pi * f * k * tt) for k, a in ((1, 1.0), (2, 0.45), (3, 0.2), (4, 0.1)))
            sig *= np.clip(tt / 0.005, 0, 1) * np.exp(-tt / (0.35 + 0.3 * d)) * np.clip((dur + 0.5 - tt) / 0.1, 0, 1)
            i0 = int(t * sr)
            i1 = min(n, i0 + len(sig))
            out[i0:i1] += 1.6 * sig[: i1 - i0]
            t += dur
    return (0.06 * out).astype(np.float32)


def _worker(o, sim, label, rule):
    layout = get_layout(o)
    name = f"{SCENE}_{label}_{layout.tag}"
    video = studio.OUT_DIR / f"{name}_silent.mp4"
    d = render(layout, sim, video, rule)
    kit.deliver_loop(SCENE, name, layout, video, build_events(sim, layout), d, voice="glassharp", bed=canon_bed())


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
    print(f"[{SCENE}] {T_LOOP:.2f}s, {N_DIG} digits {''.join(map(str, DIG[:12]))}…")
    kit.fan_out(_worker, (sim, label, rule), SCENE)


if __name__ == "__main__":
    main()
