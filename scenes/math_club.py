"""MATH CLUB — 5 graphs build a heavy club beat, and at the drop they ADD UP into one wave: the track itself.

Owner reference (2026-10-24): a Russian club / bass-house track (~115 BPM, A minor with G#, a deep sliding 808, dense
hats, clap). Only the STYLE is taken (tempo, key colour, groove, sound palette); every note, rhythm and sound here is
ours and synthesised — no melody, sample or name from the reference.
Each lane shows the REAL waveform of its instrument (the exact signal you hear), with its equation:
  #1 THE 808    y = tanh(3·sin(2π∫f dt)),  f slides A → F → E
  #2 THE KICK   y = e^(−4t)·sin(2π∫(50 + 140e^(−33t)) dt)
  #3 THE HATS   y = e^(−65t)·noise(t)   (16ths, open hat on the off-beat)
  #4 THE CLAP   y = e^(−14t)·noise(t)   (beats 2 and 4)
  #5 THE HOOK   note = A harmonic minor[round(sin(πx/2) + 2·cos(3πx))]  ->  C C B C A G# (every bar)
  Σ  THE DROP   all five lanes slide together and merge into their SUM = the actual soundtrack
v2 (owner: "more active start, more hook"): it OPENS on the drop (all five, the Σ wave, the hook on frame 0), then
strips down and rebuilds two layers at a time, breaks down, and drops again into frame 0 (the loop is drop -> drop).
115 BPM, 8 bars = 16.7 s: drop (1-2) · 808 + kick (3) · + hats + clap (4) · + hook (5) · breakdown, y = x² riser (6) ·
drop (7-8).
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

SCENE = "math_club"
SR = audio.SR
BPM = 115.0
BEAT = 60.0 / BPM
BARS = 8
T_LOOP = BARS * 4 * BEAT                                   # 16.70 s
X_DROP = 24.0                                              # beat of the drop
GOLD, RED, PURPLE, WHITE_, CYAN, GREEN = ((1.0, 0.78, 0.30), (1.0, 0.38, 0.45), (0.72, 0.52, 1.0),
                                          (0.92, 0.94, 1.0), (0.30, 0.90, 1.0), (0.40, 1.0, 0.55))
SCALE = [57, 59, 60, 62, 64, 65, 68, 69, 71, 72, 74, 76, 77, 80, 81]   # A harmonic minor from A3 (G# = 68, 80)
ROOTS = [33, 33, 29, 28]                                   # A1 A1 F1 E1 (808 roots per bar: Am Am F E)
HOOK_16 = [0, 3, 6, 8, 11, 14]                             # 3-3-2 club groove (16ths)
DROP = (0, 1, 6, 7)                                        # the drop bars: the video opens and ends on the drop
LANES = [
    ("#1", "THE 808", "y = tanh(3·sin(2π∫f dt)),  f slides A → F → E", GOLD, 0.08),
    ("#2", "THE KICK", "y = e^(−4t)·sin(2π∫(50 + 140e^(−33t)) dt)", RED, 0.45),
    ("#3", "THE HATS", "y = e^(−65t)·noise(t)", WHITE_, 0.45),
    ("#4", "THE CLAP", "y = e^(−14t)·noise(t)", PURPLE, 0.45),
    ("#5", "THE HOOK", "note = A minor[round(sin(πx/2) + 2·cos(3πx))]", CYAN, 0.025),
]


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def hook_note(x):
    d = int(round(math.sin(math.pi * x / 2) + 2 * math.cos(3 * math.pi * x)))
    return SCALE[min(len(SCALE) - 1, max(0, 7 + d))]


def layer_on(i, bar):
    """which bars each lane plays in: everything in the drop bars, the rebuild two at a time, bar 5 = the breakdown."""
    if bar in DROP:
        return True
    if i <= 1:
        return bar in (2, 3, 4)
    if i == 2:
        return bar in (3, 4)
    if i == 3:
        return bar in (3, 4, 5)
    return bar in (4, 5)


def lane_shown(i, bar):
    return bar >= 4 or (bar == 3 and i <= 3) or (bar == 2 and i <= 1)


def build_stems():
    n = int(round(T_LOOP * SR))
    st = np.zeros((5, n))
    extra = np.zeros(n)                                     # riser (not a lane; counted in the sum)
    rng = np.random.default_rng(11)

    def add(row, t0, sig, g):
        i0 = int(round(t0 * SR)) % n
        idx = (np.arange(len(sig)) + i0) % n
        np.add.at(st[row] if row >= 0 else extra, idx, g * sig)

    def tv_(d):
        return np.arange(int(d * SR)) / SR

    kick_env = np.zeros(n)
    for bar in range(BARS):
        b0 = bar * 4
        # 808: syncopated, with a slide into the next root
        if layer_on(0, bar):
            r, nxt = ROOTS[bar % 4], ROOTS[(bar + 1) % 4]
            notes = [(0.0, r, 1.5, None), (1.5, r, 2.5, None), (2.5, r + 12, 3.25, r), (3.25, r, 4.0, nxt)]
            if bar not in DROP:
                notes = [(0.0, r, 2.5, None), (2.5, r + 12, 4.0, nxt)]
            for x0, m, x1, to in notes:
                d = (x1 - x0) * BEAT
                tv = tv_(d)
                pm = np.full(len(tv), float(m))
                if to is not None:
                    gl = min(0.6 * BEAT, d)
                    k = tv > d - gl
                    u = (tv[k] - (d - gl)) / gl
                    pm[k] = m + (to - m) * (1 - np.exp(-6 * u)) / (1 - math.exp(-6))
                fr = 440.0 * 2 ** ((pm - 69) / 12) * (1 + 1.2 * np.exp(-tv / 0.015))
                sig = np.tanh(3.0 * np.sin(2 * np.pi * np.cumsum(fr) / SR))
                amp = np.clip(tv / 0.003, 0, 1) * np.exp(-tv / 1.2) * np.clip((d - tv) / 0.012, 0, 1)
                add(0, (b0 + x0) * BEAT, sig * amp, 0.30)
        # kick: four on the floor
        if layer_on(1, bar):
            for b in range(4):
                tv = tv_(0.42)
                fr = 50 + 140 * np.exp(-tv * 33)
                sig = np.exp(-tv * 4) * np.sin(2 * np.pi * np.cumsum(fr) / SR) * np.clip(tv / 0.001, 0, 1)
                sig += 0.25 * np.sin(2 * np.pi * 2500 * tv) * np.exp(-tv / 0.003)
                add(1, (b0 + b) * BEAT, sig, 0.55)
                i0 = int(round((b0 + b) * BEAT * SR)) % n
                env = np.exp(-tv / 0.11)
                idx = (np.arange(len(env)) + i0) % n
                kick_env[idx] = np.maximum(kick_env[idx], env)
        # hats: 16ths with accents, open hat on every off-beat
        if layer_on(2, bar):
            for s16 in range(16):
                tv = tv_(0.06)
                nz = np.diff(np.concatenate([[0], np.diff(np.concatenate([[0], rng.standard_normal(len(tv))]))]))
                acc = 1.0 if s16 % 4 == 2 else (0.55 if s16 % 2 else 0.75)
                add(2, (b0 + s16 / 4) * BEAT, nz * np.exp(-tv * 65), 0.05 * acc)
                if s16 % 4 == 2:
                    tv = tv_(0.22)
                    nz = np.diff(np.concatenate([[0], rng.standard_normal(len(tv))]))
                    add(2, (b0 + s16 / 4) * BEAT, nz * np.exp(-tv / 0.07), 0.035)
        # clap: 2 and 4; in the breakdown a roll that doubles (8ths -> 16ths -> 32nds)
        if layer_on(3, bar):
            hits = [1.0, 3.0] if bar != 5 else ([b * 0.5 for b in range(4)] + [2 + b * 0.25 for b in range(4)] +
                                                [3 + b * 0.125 for b in range(4)])
            for j, x in enumerate(hits):
                tv = tv_(0.3)
                nz = rng.standard_normal(len(tv))
                nz = nz - np.convolve(nz, np.ones(6) / 6, mode="same")
                burst = 1 + 0.8 * sum(np.exp(-((tv - k * 0.011) / 0.003) ** 2) for k in range(3))
                sig = nz * np.exp(-tv * 14) * burst + 0.5 * np.sin(2 * np.pi * 210 * tv) * np.exp(-tv / 0.04)
                g = 0.20 if bar != 5 else 0.06 + 0.12 * j / len(hits)
                add(3, (b0 + x) * BEAT, sig, g)
        # the hook: plucked saw in A harmonic minor; the breakdown is darker; the drop doubles it an octave up
        if layer_on(4, bar):
            for p in HOOK_16:
                x = b0 + p / 4
                if 23.5 <= x < 24:
                    continue
                m = hook_note(x)
                tv = tv_(0.26)
                harm = 5 if bar == 5 else 12
                ph = 2 * np.pi * hz(m) * tv
                sig = sum(np.sin(k * ph) / k for k in range(1, harm + 1))
                sig += 0.5 * sum(np.sin(k * ph * 1.005) / k for k in range(1, harm + 1))
                env = np.clip(tv / 0.003, 0, 1) * (0.6 * np.exp(-tv / 0.05) + 0.4 * np.exp(-tv / 0.16))
                add(4, x * BEAT, sig * env, 0.07)
                if bar in DROP:
                    add(4, x * BEAT, np.sin(2 * ph) * env, 0.05)
    # riser in the breakdown: y = x²  (pitch climbs on a parabola), silent for the last half beat
    t_a, t_b = 20 * BEAT, 23.5 * BEAT
    tv = np.arange(int((t_b - t_a) * SR)) / SR
    u = tv / tv[-1]
    fr = 200 + 1600 * u ** 2
    nz = np.convolve(rng.standard_normal(len(tv)), np.ones(5) / 5, mode="same")
    add(-1, t_a, (0.5 * np.sin(2 * np.pi * np.cumsum(fr) / SR) + nz) * u ** 2, 0.08)
    st[0] *= 1 - 0.55 * kick_env                            # the pump: the 808 ducks under every kick
    return st, extra


STEMS, EXTRA = build_stems()
MIX = STEMS.sum(axis=0) + EXTRA
SCALES = [max(1e-6, float(np.percentile(np.abs(s), 99.7))) for s in STEMS]
MIX_SCALE = float(np.percentile(np.abs(MIX), 99.7))


def simulate():
    return {"nf": int(round(T_LOOP * FPS))}


class Scene:
    def __init__(self, layout, sim):
        self.L, self.sim = layout, sim
        self.canvas = Canvas(layout.w, layout.h, studio.render_scale())

    def wave(self, sig, scale, t, win, x0, x1, yc, amp, col, alpha, width):
        """the real signal over the last `win` seconds, scrolling, playhead at the right edge."""
        n = len(sig)
        i1 = int(t * SR)
        npts = 260
        idx = (i1 - (np.arange(npts)[::-1] * (win * SR / npts)).astype(int)) % n
        v = np.clip(sig[idx] / scale, -1.2, 1.2)
        pts = [(x0 + (x1 - x0) * j / (npts - 1), yc - amp * float(v[j])) for j in range(npts)]
        self.canvas.polylines([pts], col, width=width * 3.5, alpha=0.14 * alpha)
        self.canvas.polylines([pts], col, width=width, alpha=0.95 * alpha)

    def level(self, sig, scale, t):
        i = int(t * SR)
        seg = sig[max(0, i - 600): i + 1]
        return float(np.abs(seg).max() / scale) if len(seg) else 0.0

    def draw(self, f, rule):
        L, c = self.L, self.canvas
        w, h = L.w, L.h
        t = f * DT
        ctx = c.ctx
        xb = t / BEAT
        bar = int(xb // 4)
        g = cairo.RadialGradient(w / 2, h * 0.45, 0, w / 2, h * 0.45, h * 0.7)
        kick_lv = self.level(STEMS[1], SCALES[1], t) if layer_on(1, bar) else 0.0
        g.add_color_stop_rgb(0, 0.06 + 0.05 * kick_lv * (bar in DROP), 0.04, 0.10 + 0.04 * kick_lv * (bar in DROP))
        g.add_color_stop_rgb(1, 0.005, 0.005, 0.015)
        ctx.set_source(g)
        ctx.paint()
        e = 0.0
        if xb < 8.0:                                              # opens merged (the drop), splits at bar 3
            merge = 1.0
        elif xb < X_DROP:
            merge = 1.0 - smooth(min(1.0, (xb - 8.0) / 0.6))
        else:
            merge = smooth(min(1.0, (xb - X_DROP) / 1.0))
        top, lane_h = h * 0.245, h * 0.083
        xl0, xl1 = w * 0.30, w * 0.95
        yc_mix = h * 0.455
        for i, (num, name, eq, col, win) in enumerate(LANES):
            active = lane_shown(i, bar) or bar in DROP
            yc0 = top + lane_h * (i + 0.5)
            yc = yc0 + (yc_mix - yc0) * merge
            playing = layer_on(i, bar)
            a_lane = (1.0 if active else 0.25) * (1 - 0.75 * merge)
            if i >= 1:
                a_lane *= 1 - 0.75 * e
            lv = min(1.0, self.level(STEMS[i], SCALES[i], t)) if playing else 0.0
            # lane frame + label
            la = a_lane * (1 - min(1.0, merge / 0.5))              # labels are gone before the lanes meet
            if la > 0.01:
                c.lines([(xl0, yc, xl1, yc)], (0.4, 0.45, 0.65), width=1.2, alpha=0.35 * la)
                pop = 1 + 0.12 * lv
                c.text_centered(num, yc - lane_h * 0.06, size=h * 0.022 * pop, color=col, alpha=la, cx=w * 0.08)
                c.text_centered(name, yc + lane_h * 0.24, size=h * 0.016, color=col, alpha=la, cx=w * 0.17,
                                max_w=w * 0.24)
                c.circle(w * 0.08, yc + lane_h * 0.25, h * 0.006 * (1 + 1.5 * lv), col, alpha=la * (0.4 + 0.6 * lv))
            if active:
                self.wave(STEMS[i], SCALES[i], t, win, xl0, xl1, yc, lane_h * 0.40 * (1 - 0.3 * merge), col,
                          (a_lane * ((1 - e) if i >= 1 else 1.0)) if merge < 0.99 else 0.0, 2.6)
        # the sum: Σ of all five lanes = the soundtrack
        if merge > 0:
            amp = h * 0.13 * merge
            lv = self.level(MIX, MIX_SCALE, t)
            c.glow(w / 2, yc_mix, w * 0.35, GREEN, strength=(0.10 + 0.25 * lv) * merge, reach=1.6)
            self.wave(MIX, MIX_SCALE, t, 0.06, w * 0.05, w * 0.95, yc_mix, amp, GREEN, merge, 4.0)
            self.wave(MIX, MIX_SCALE, t, 0.06, w * 0.05, w * 0.95, yc_mix, amp * 0.9, WHITE_, 0.5 * merge, 1.4)
        # the current layer: name + its equation
        if bar in DROP:
            title, eq, col = "Σ  5 GRAPHS = 1 BEAT", "808 + kick + hats + clap + hook", GREEN
        elif bar == 5:
            title, eq, col = "THE BREAKDOWN", "riser: pitch = x²", (1.0, 0.65, 0.35)
        elif bar == 2:
            title, eq, col = "#1 808  +  #2 KICK", "a sliding sine + a falling chirp", GOLD
        elif bar == 3:
            title, eq, col = "#3 HATS  +  #4 CLAP", "two kinds of decaying noise", PURPLE
        else:
            title, eq, col = "#5  THE HOOK", "note = A minor[round(sin(πx/2) + 2·cos(3πx))]", CYAN
        k = 1.0 if bar in DROP else smooth(min(1.0, (xb - bar * 4) / 0.5))
        c.text_centered(title, h * 0.685, size=w * 0.07, color=col, alpha=k, max_w=w * 0.92)
        c.text_centered(eq, h * 0.72, size=w * 0.034, color=(0.92, 0.93, 1.0), alpha=k, bold=False, max_w=w * 0.94)
        # beat counter: 8 bars × 4 beats as dots
        for b in range(BARS):
            cx_ = w * (0.22 + 0.08 * b)
            on = b <= bar
            cc = GREEN if b in DROP else ((1.0, 0.65, 0.35) if b == 5 else LANES[b - 2][3])
            big = 1.0 if b == bar else 0.0
            al = 0.95 if on else 0.25
            c.circle(cx_, h * 0.765, w * (0.01 + 0.006 * big), cc, alpha=al)
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
    print(f"[{SCENE}] {T_LOOP:.2f}s  hook: {[hook_note(16 + p / 4) for p in HOOK_16]}")
    name = f"{SCENE}_{label}_{layout.tag}"
    video = studio.OUT_DIR / f"{name}_silent.mp4"
    d = render(layout, sim, video, rule)
    kit.deliver_loop(SCENE, name, layout, video, [], d, voice="piano", bed=MIX.astype(np.float32), peak_db=-6.0)


if __name__ == "__main__":
    main()
