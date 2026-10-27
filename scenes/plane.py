"""PLANE — "A plane loses an engine, as math 🔊 (safe landing)" (owner brief 2026-10-23; idea #3 in
ideas/2026-10-22_short_ideas.txt). Clean instruments only, no damage imagery; a fictional generic twin-engine jet.

Every instrument is a voice: altitude (its pitch follows the altitude), speed, engine 1 and engine 2 hums.
  0-2 s   hook: huge neon panel ALTITUDE 35,000 ft / SPEED 480 kt, two engine gauges, plane over a scrolling horizon
  2-7 s   engine 2 drops to zero with a clunk and a local flash, its note leaves the chord, "ENGINE 2: FAIL",
          the altitude line curves down and its note bends lower
  7-14 s  speed sinks toward the red line, a soft stall-warning pulse, the view tilts; the nose lowers, speed
          recovers, the warning stops; then the altitude steps down calmly, one tone per step
  14-19 s glowing runway, big altitude countdown 500 / 100 / 10, soft touchdown thump, gentle flash, a calm chord,
          "1 ENGINE IS ENOUGH." — hard cut to the start (loop)
Audio: original synthesis only (hums, clunk, soft pulse, glass notes, thump, chord). Time is compressed.
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

SCENE = "plane"
CYAN, AMBER, GREEN, RED, WHITE = (0.30, 0.88, 1.0), (1.0, 0.72, 0.25), (0.40, 1.0, 0.55), (1.0, 0.22, 0.20), (1, 1, 1)
NAVY = (0.02, 0.03, 0.07)
FONT = "Consolas"
T_FAIL, T_STALL0, T_NOSE, T_STALL1 = 2.6, 8.4, 9.6, 10.6
STEPS = [(10.9 + 0.75 * k, 28000 - 3500 * (k + 1)) for k in range(4)]      # calm steps: 24,500 ... 14,000
T_FINAL, T_TOUCH, T_END = 14.0, 17.4, 19.0
CALLS = [(16.2, 500), (16.95, 100), (17.3, 10)]
STALL_KT = 250


def altitude(t):
    if t < 3.0:
        return 35000.0
    if t < 7.0:
        return 35000 - 7000 * smooth((t - 3.0) / 4.0)
    a = 28000.0
    if t >= 7.0:
        a -= 0.0
    for ts, target in STEPS:
        prev = a
        a = prev + (target - prev) * smooth((t - ts) / 0.45)
        if t < ts:
            a = prev
            break
    if t >= T_FINAL:
        a14 = STEPS[-1][1]
        u = (t - T_FINAL) / (T_TOUCH - T_FINAL)
        a = a14 * max(0.0, 1 - u) ** 2.2 if u < 1 else 0.0
    return a


def speed(t):
    v = 480.0
    v -= 225 * smooth((t - 3.5) / 5.5)                 # sinks toward the red line
    v += 90 * smooth((t - T_NOSE) / 1.8)              # nose down: speed recovers
    v -= 175 * smooth((t - T_FINAL) / (T_TOUCH - T_FINAL))   # approach speed
    if t > T_TOUCH:
        v -= 60 * smooth((t - T_TOUCH) / 1.2)          # rollout
    return v


def n1(eng, t):
    if eng == 1:
        return 88 + 8 * smooth((t - T_FAIL - 0.4) / 1.5) - 40 * smooth((t - T_TOUCH) / 0.8)
    return 88 * (1 - smooth((t - T_FAIL) / 0.35))


def pitch(t):
    return (5 * smooth((t - 7.5) / 1.8) - 11 * smooth((t - T_NOSE) / 0.7) + 6 * smooth((t - 11.4) / 1.0)
            - 3 * smooth((t - T_FINAL) / 1.0) + 6 * smooth((t - (T_TOUCH - 0.6)) / 0.5) - 3 * smooth((t - T_TOUCH) / 0.4))


def roll(t):
    yaw_kick = -9 * math.exp(-max(0.0, t - T_FAIL) / 1.1) * smooth((t - T_FAIL) / 0.25)
    stall_wob = 5 * math.sin(2 * math.pi * 0.9 * t) * smooth((t - T_STALL0) / 0.6) * (1 - smooth((t - T_STALL1) / 0.5))
    return yaw_kick + stall_wob


class Scene:
    def __init__(self, layout):
        self.L = layout
        self.canvas = Canvas(layout.w, layout.h, studio.render_scale())

    def mono(self, s, x, y, size, col, alpha=1.0, align="left", bold=True):
        ctx = self.canvas.ctx
        ctx.select_font_face(FONT, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD if bold else cairo.FONT_WEIGHT_NORMAL)
        ctx.set_font_size(size)
        ext = ctx.text_extents(s)
        if align == "right":
            x -= ext.x_advance
        elif align == "center":
            x -= ext.x_advance / 2
        ctx.set_source_rgba(*col, alpha)
        ctx.move_to(x, y)
        ctx.show_text(s)

    def gauge(self, x, y, r, val, label, col, t, flash=0.0):
        c = self.canvas
        ctx = c.ctx
        a0, a1 = math.radians(135), math.radians(405)
        ctx.new_path()
        ctx.arc(x, y, r, a0, a1)
        ctx.set_source_rgba(0.55, 0.65, 1.0, 0.25)
        ctx.set_line_width(r * 0.10)
        ctx.stroke()
        ctx.new_path()
        ctx.arc(x, y, r, a0, a0 + (a1 - a0) * max(0.0, val) / 100)
        ctx.set_source_rgba(*col, 0.95)
        ctx.set_line_width(r * 0.10)
        ctx.stroke()
        an = a0 + (a1 - a0) * max(0.0, val) / 100
        c.lines([(x, y, x + math.cos(an) * r * 0.8, y + math.sin(an) * r * 0.8)], WHITE, width=4)
        c.circle(x, y, r * 0.07, WHITE)
        if flash > 0:
            c.glow(x, y, r * 0.7, (1, 0.9, 0.8), strength=0.9 * flash, reach=2.0)
        self.mono(f"{max(0.0, val):3.0f}%", x, y + r * 0.62, r * 0.30, col, align="center")
        self.mono(label, x, y + r * 1.35, r * 0.24, (0.8, 0.85, 1.0), alpha=0.9, align="center", bold=False)

    def plane_icon(self, x, y, s, col):
        """side view of a generic twin-jet, nose to the right"""
        c = self.canvas
        body = [(-1.0, -0.05), (0.75, -0.08), (1.0, 0.0), (0.75, 0.10), (-0.85, 0.10), (-1.0, 0.04)]
        tail = [(-0.80, -0.06), (-1.0, -0.55), (-0.88, -0.55), (-0.55, -0.06)]
        wing = [(-0.15, 0.04), (0.20, 0.04), (-0.05, 0.42), (-0.25, 0.42)]
        eng = [(0.02, 0.18), (0.30, 0.18), (0.30, 0.30), (0.02, 0.30)]
        for poly, a in ((tail, 0.9), (wing, 0.75), (body, 1.0), (eng, 0.9)):
            c.poly([(x + px * s, y + py * s) for px, py in poly], col, alpha=a)

    def draw(self, f):
        L, c = self.L, self.canvas
        w, h = L.w, L.h
        t = f * DT
        ctx = c.ctx
        alt, spd = altitude(t), speed(t)
        ctx.set_source_rgb(*NAVY)
        ctx.paint()
        g = cairo.RadialGradient(w / 2, h * 0.45, 0, w / 2, h * 0.45, h * 0.65)
        g.add_color_stop_rgba(0, 0.08, 0.12, 0.25, 0.6)
        g.add_color_stop_rgba(1, 0, 0, 0, 0)
        ctx.set_source(g)
        ctx.paint()

        # ---- the instrument panel (top)
        warn = T_STALL0 <= t < T_STALL1
        pulse = 0.5 + 0.5 * math.cos(2 * math.pi * 2.0 * (t - T_STALL0)) if warn else 0.0
        self.mono("ALTITUDE", w * 0.06, h * 0.085, h * 0.020, (0.8, 0.85, 1.0), bold=False)
        self.mono(f"{alt:,.0f} ft", w * 0.06, h * 0.135, h * 0.050, CYAN)
        spd_col = RED if spd < STALL_KT + 20 and t < T_FINAL else AMBER
        self.mono("SPEED", w * 0.94, h * 0.085, h * 0.020, (0.8, 0.85, 1.0), align="right", bold=False)
        self.mono(f"{spd:,.0f} kt", w * 0.94, h * 0.135, h * 0.050, spd_col, align="right")
        # speed tape with the red line
        tx0, tx1, ty = w * 0.52, w * 0.94, h * 0.152
        ctx.rectangle(tx0, ty, tx1 - tx0, h * 0.008)
        ctx.set_source_rgba(0.6, 0.7, 1.0, 0.2)
        ctx.fill()
        fr = min(1.0, spd / 500)
        ctx.rectangle(tx0, ty, (tx1 - tx0) * fr, h * 0.008)
        ctx.set_source_rgba(*spd_col, 0.9)
        ctx.fill()
        rx = tx0 + (tx1 - tx0) * STALL_KT / 500
        c.lines([(rx, ty - h * 0.006, rx, ty + h * 0.014)], RED, width=4)
        fl2 = max(0.0, 1 - (t - T_FAIL) / 0.4) if t >= T_FAIL else 0.0
        e2 = n1(2, t)
        self.gauge(w * 0.27, h * 0.228, w * 0.115, n1(1, t), "ENGINE 1", GREEN, t)
        self.gauge(w * 0.73, h * 0.228, w * 0.115, e2, "ENGINE 2", RED if t >= T_FAIL else GREEN, t, flash=fl2)

        # ---- the view: scrolling horizon graph, plane icon, runway at the end
        vx0, vx1, vy0, vy1 = w * 0.05, w * 0.95, h * 0.335, h * 0.705
        ctx.save()
        ctx.rectangle(vx0, vy0, vx1 - vx0, vy1 - vy0)
        ctx.clip()
        px, py0 = w * 0.62, vy1 - (vy1 - vy0) * 0.12
        ctx.translate(px, (vy0 + vy1) / 2)
        ctx.rotate(math.radians(roll(t)))
        ctx.translate(-px, -(vy0 + vy1) / 2)
        ymap = lambda a: py0 - (vy1 - vy0) * 0.72 * a / 36000   # noqa: E731
        # scrolling grid (speed)
        scroll = 0.0
        tt = np.arange(0, t, 1 / 30)
        scroll = sum(speed(x) for x in tt) / 30 * 0.6 if len(tt) else 0.0
        step = w * 0.08
        off = scroll % step
        for k in range(-2, 16):
            gx = vx0 + k * step - off
            c.lines([(gx, vy0 - 200, gx, vy1 + 200)], (0.5, 0.6, 1.0), width=1, alpha=0.10)
        for k in range(0, 8):
            gy = vy0 + k * (vy1 - vy0) / 7
            c.lines([(vx0 - 200, gy, vx1 + 200, gy)], (0.5, 0.6, 1.0), width=1, alpha=0.08)
        # ground line + runway (fades in for the landing)
        rw = smooth((t - T_FINAL) / 1.0)
        c.lines([(vx0 - 200, py0, vx1 + 200, py0)], (0.6, 0.7, 1.0), width=2, alpha=0.4)
        if rw > 0:
            ctx.new_path()
            for k in range(12):
                lx = vx0 + ((k * step * 1.4 - scroll * 1.3) % ((vx1 - vx0) * 1.2))
                c.circle(lx, py0 + 6, 5, (1.0, 0.9, 0.5), alpha=0.9 * rw)
            g2 = cairo.LinearGradient(0, py0, 0, py0 + h * 0.02)
            g2.add_color_stop_rgba(0, 0.4, 0.9, 1.0, 0.5 * rw)
            g2.add_color_stop_rgba(1, 0.4, 0.9, 1.0, 0.0)
            ctx.rectangle(vx0 - 200, py0, (vx1 - vx0) + 400, h * 0.02)
            ctx.set_source(g2)
            ctx.fill()
            for k in range(1, 7):                                 # perspective runway lines
                c.lines([(px, py0, px + (k - 3.5) * w * 0.12, vy1 + 40)], CYAN, width=2, alpha=0.35 * rw)
        # altitude history: the line the plane leaves behind
        hist = np.arange(max(0.0, t - 5.5), t + 1e-9, 1 / 30)
        if len(hist) > 1:
            pts = [(px - (t - x) * w * 0.10, ymap(altitude(x))) for x in hist]
            c.polylines([pts], CYAN, width=12, alpha=0.12)
            c.polylines([pts], CYAN, width=4, alpha=0.95)
        py = ymap(alt)
        ctx.save()
        ctx.translate(px, py)
        ctx.rotate(math.radians(-pitch(t)))
        c.glow(0, 0, w * 0.06, CYAN, strength=0.35, reach=2.0)
        self.plane_icon(0, 0, w * 0.105, WHITE)
        ctx.restore()
        # stall: the view border pulses red (soft)
        ctx.restore()
        bcol = RED if warn else (0.55, 0.65, 1.0)
        ctx.rectangle(vx0, vy0, vx1 - vx0, vy1 - vy0)
        ctx.set_source_rgba(*bcol, 0.35 + 0.5 * pulse if warn else 0.3)
        ctx.set_line_width(3 + 4 * pulse)
        ctx.stroke()
        # big countdown in the view
        for tc, val in CALLS:
            if tc <= t < tc + 0.9:
                a = 1 - smooth((t - tc - 0.5) / 0.4)
                c.text_centered(f"{val}", vy0 + (vy1 - vy0) * 0.42, size=h * 0.11 * (1 + 0.25 * math.exp(-(t - tc) / 0.15)),
                                color=WHITE, alpha=a)

        # ---- status line
        sy = h * 0.762
        if T_FAIL <= t < 7.0:
            a = 0.65 + 0.35 * math.cos(2 * math.pi * 1.2 * (t - T_FAIL))
            c.text_centered("ENGINE 2: FAIL", sy, size=h * 0.042, color=RED, alpha=a)
        elif warn:
            c.text_centered("STALL WARNING", sy, size=h * 0.042, color=RED, alpha=0.55 + 0.45 * pulse)
        elif T_STALL1 <= t < 12.2:
            c.text_centered("NOSE DOWN · SPEED RECOVERED", sy, size=h * 0.030, color=GREEN)
        elif 12.2 <= t < T_FINAL:
            c.text_centered("DESCENDING ON 1 ENGINE", sy, size=h * 0.030, color=(0.8, 0.85, 1.0))
        elif T_FINAL <= t < T_TOUCH:
            c.text_centered("FINAL APPROACH", sy, size=h * 0.030, color=CYAN)
        else:
            a = smooth((t - T_TOUCH - 0.2) / 0.4)
            c.glow(w / 2, sy - h * 0.015, w * 0.12, GREEN, strength=0.18 * a, reach=1.6)
            c.text_centered("1 ENGINE IS ENOUGH.", sy, size=h * 0.045, color=WHITE, alpha=a)
        # touchdown: a gentle flash
        if T_TOUCH <= t < T_TOUCH + 0.4:
            ctx.set_source_rgba(1, 1, 1, 0.22 * (1 - (t - T_TOUCH) / 0.4))
            ctx.paint()
        c.watermark(L)


def render(layout, out_path, still_frame=None):
    sc = Scene(layout)
    writer = None if still_frame is not None else VideoWriter(out_path, sc.canvas, FPS)
    nf = int(round(T_END * FPS))
    for f in range(nf):
        if still_frame is not None and f != still_frame:
            continue
        sc.draw(f)
        if writer is None:
            studio.save_still(sc.canvas, out_path)
            return f / FPS
        writer.write_frame()
    writer.close()
    return nf / FPS


SR = audio.SR


def _voice(freq, harm):
    ph = 2 * np.pi * np.cumsum(freq) / SR
    return sum(a * np.sin(k * ph) for k, a in harm)


def build_bed():
    n = int(round(T_END * SR))
    t = np.arange(n) / SR
    tk = t[::480]
    alt = np.interp(t, tk, [altitude(x) for x in tk])
    spd = np.interp(t, tk, [speed(x) for x in tk])
    e1 = np.interp(t, tk, [n1(1, x) for x in tk])
    e2 = np.interp(t, tk, [n1(2, x) for x in tk])
    # the instrument chord (A major-ish), each voice follows its instrument
    v_alt = _voice(220.0 * 2 ** (alt / 35000 - 1), ((1, 1.0), (2, 0.3)))
    v_spd = _voice(330.0 * 2 ** ((spd - 480) / 480), ((1, 1.0), (3, 0.08)))
    v_e1 = _voice(110.0 * (0.9 + 0.1 * e1 / 88), ((1, 1.0), (2, 0.5), (3, 0.25)))
    v_e2 = _voice(138.6 * (0.9 + 0.1 * np.maximum(e2, 1) / 88), ((1, 1.0), (2, 0.5), (3, 0.25)))
    mix = 0.16 * v_alt + 0.09 * v_spd + 0.12 * v_e1 * (e1 / 88) + 0.12 * v_e2 * (e2 / 88)
    rng = np.random.default_rng(2)
    i0 = int(T_FAIL * SR)                                               # the clunk
    tc = np.arange(int(0.5 * SR)) / SR
    clunk = np.sin(2 * np.pi * np.cumsum(70 + 90 * np.exp(-tc / 0.03)) / SR) * np.exp(-tc / 0.12)
    clunk += np.convolve(rng.standard_normal(len(tc)), np.ones(20) / 20, "same") * np.exp(-tc / 0.05) * 2
    mix[i0:i0 + len(tc)] += 0.6 * clunk
    warn = (t >= T_STALL0) & (t < T_STALL1)                             # soft stall pulse, 4 beeps/s
    beep = ((t - T_STALL0) * 4 % 1) < 0.45
    mix += 0.07 * np.tanh(1.5 * np.sin(2 * np.pi * 880 * t)) * warn * beep
    for k, (ts, _) in enumerate(STEPS):                                  # calm descending steps
        tv = np.arange(int(1.2 * SR)) / SR
        note = audio.midi_to_hz([76, 74, 72, 69][k])
        s = (np.sin(2 * np.pi * note * tv) + 0.3 * np.sin(4 * np.pi * note * tv)) * np.exp(-tv / 0.35)
        j = int(ts * SR)
        mix[j:j + len(tv)] += 0.18 * s[: n - j]
    for (tcall, _), m in zip(CALLS, (67, 64, 60)):                       # countdown calls
        tv = np.arange(int(0.6 * SR)) / SR
        s = np.sin(2 * np.pi * audio.midi_to_hz(m) * tv) * np.exp(-tv / 0.2)
        j = int(tcall * SR)
        mix[j:j + len(tv)] += 0.20 * s[: n - j]
    j = int(T_TOUCH * SR)                                               # touchdown thump + calm chord
    tv = np.arange(int(1.6 * SR)) / SR
    thump = np.sin(2 * np.pi * np.cumsum(55 + 60 * np.exp(-tv / 0.04)) / SR) * np.exp(-tv / 0.25)
    mix[j:j + len(tv)] += 0.7 * thump[: n - j]
    for m in (57, 61, 64, 69):
        s = np.sin(2 * np.pi * audio.midi_to_hz(m) * tv) * np.sin(np.pi * np.minimum(1, tv / 1.6))
        mix[j:j + len(tv)] += 0.07 * s[: n - j]
    return (0.6 * mix).astype(np.float32)


def main():
    label = arg("--label", "v1")
    studio.OUT_DIR.mkdir(exist_ok=True)
    layout = get_layout("vertical")
    if kit.has("--still"):
        f = int(arg("--frame", "0"))
        png = studio.OUT_DIR / f"{SCENE}_{label}_f{f}_{layout.tag}.png"
        render(layout, png, still_frame=f)
        print(f"[{SCENE}] -> {png}")
        return
    name = f"{SCENE}_{label}_{layout.tag}"
    video = studio.OUT_DIR / f"{name}_silent.mp4"
    d = render(layout, video)
    kit.deliver_loop(SCENE, name, layout, video, [], d, voice="glassharp", bed=build_bed(), peak_db=-6.0)


if __name__ == "__main__":
    main()
