"""REACTOR — "A nuclear reactor melts down, as math 🔊" (owner brief 2026-10-23; format of the overlap channel that
gets 0.8-1.9M with disasters "as math").

Fictional, generic reactor (no real plant, no real event). Three stacked glowing graph panels in a slowly tilting
3-D view: TEMPERATURE (amber), PRESSURE (cyan), RADIATION (magenta). Every line SINGS its value: pitch rises with
the data (low hum, mid whine, high whistle) and radiation also drives a Geiger-counter click rate.
  0-2 s   hook: huge "CORE TEMP 290°C", a calm three-voice chord, slow push-in
  2-8 s   rising: values and pitches climb, the coolant bar drains, the panels tilt into 3-D
  8-15 s  alarm: lines turn red and spike off their panels, sparks, screen shake grows, grid flickers,
          "SCRAM FAILED" blinks, a two-tone alarm pulse, the three voices clash
  15-16 s event: all three lines shoot vertical, ONE white flash, heavy shake, a deep boom, then black and silence
  16.7 s  hard cut to a huge glowing "?", which then dissolves back into frame 0 (calm hum) = loop
Photosensitivity: a single full-screen flash; red pulses are low-contrast tints; checked with tools/flash_check.py.
Audio: original synthesis only.
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

SCENE = "reactor"
AMBER, CYAN, MAGENTA, RED = (1.0, 0.68, 0.22), (0.30, 0.88, 1.0), (1.0, 0.35, 0.85), (1.0, 0.18, 0.15)
NAVY = (0.02, 0.025, 0.06)
T_SHOOT, T_FLASH, T_BLACK, T_Q, T_BACK, T_LOOP = 15.0, 15.5, 16.0, 16.7, 18.3, 19.0
T_AXIS = 15.6                                  # time span of the graph x-axis
PANELS = [("TEMPERATURE", AMBER, 0.66), ("PRESSURE", CYAN, 0.0), ("RADIATION", MAGENTA, -0.66)]
PW, PH = 1.0, 0.27                             # panel half-width / half-height (world units)
FONT_MONO = "Consolas"
T_SCRAM, T_JAM = 10.4, 10.75                   # control rods drop ... and jam halfway


# --- the data -------------------------------------------------------------------------------------------------------

def _spikes(seed):
    rng = np.random.default_rng(seed)
    ks = []
    t = 8.2
    while t < 14.9:
        ks.append((t, 0.05 + 0.32 * (t - 8) / 7 * rng.uniform(0.6, 1.3), rng.uniform(0.06, 0.16)))
        t += rng.uniform(0.25, 0.6)
    return ks


SPK = [_spikes(11), _spikes(23), _spikes(37)]
SHAPE = [(0.36, 0.55, 0.0), (0.30, 0.62, 0.7), (0.24, 0.75, 1.3)]     # (rise by 8 s, run by 15 s, lag)


def value(ch, t):
    t = np.asarray(t, float)
    a, b, lag = SHAPE[ch]
    v = 0.12 + 0.015 * np.sin(2.1 * t + lag * 3) + a * np.clip((t - 2 - 0.3 * lag) / 6, 0, 1) ** 1.4
    v = v + b * np.clip((t - 8) / 7, 0, 1) ** 1.6
    for tk, ak, wk in SPK[ch]:
        v = v + ak * np.exp(-((t - tk) / wk) ** 2)
    v = v + 9.0 * np.clip((t - T_SHOOT - 0.08 * ch) / 0.45, 0, 1) ** 2   # the event: straight up
    return v


def danger(t):
    return smooth((t - 8.0) / 1.5)


def shake_amp(t):
    if t < 8:
        return 0.0
    if t < T_SHOOT:
        sp = sum(ak * math.exp(-((t - tk) / wk) ** 2) for s in SPK for tk, ak, wk in s)
        return 2.0 + 16.0 * (t - 8) / 7 + 40.0 * sp
    if t < T_BLACK:
        return 28.0 + 60.0 * max(0.0, 1 - abs(t - T_FLASH) / 0.5)
    return 0.0


def readouts(t):
    vT, vP, vR = (float(value(c, min(t, T_SHOOT))) for c in range(3))
    temp = 290 + 2400 * max(0.0, vT - 0.12) ** 1.15
    pres = 7.0 + 16.0 * max(0.0, vP - 0.12)
    rad = 0.1 * 10 ** (3.6 * max(0.0, vR - 0.12))               # mSv/h
    return temp, pres, rad


def coolant(t):
    return 1.0 - smooth((t - 2.5) / 7.5)


# --- the picture ------------------------------------------------------------------------------------------------------

class Scene:
    def __init__(self, layout):
        self.L = layout
        self.canvas = Canvas(layout.w, layout.h, studio.render_scale())
        w, h = layout.w, layout.h
        self.F = w * 0.43
        self.cx, self.cy = w / 2, h * 0.505

    def cam(self, t):
        tilt = math.radians(38) * smooth((t - 2) / 6)
        yaw = math.radians(-17) * smooth((t - 3) / 7)
        D = 3.2 - 0.55 * smooth(t / T_SHOOT)
        return tilt, yaw, D

    def proj(self, X, Y, t):
        """world points (panel plane Z=0) -> screen; X, Y arrays"""
        tilt, yaw, D = self.cam(t)
        X = np.asarray(X, float)
        Y = np.asarray(Y, float)
        y1, z1 = Y * math.cos(tilt), -Y * math.sin(tilt)
        x2, z2 = X * math.cos(yaw) + z1 * math.sin(yaw), -X * math.sin(yaw) + z1 * math.cos(yaw)
        s = D / (D + z2)
        return self.cx + self.F * x2 * s, self.cy - self.F * y1 * s

    def core(self, t, temp):
        """the reactor: a steel vessel cut away, fuel rods heating up, coolant draining, control rods jamming"""
        c, L = self.canvas, self.L
        w, h = L.w, L.h
        ctx = c.ctx
        dg = danger(t)
        a = shake_amp(t) * 0.6
        ox = a * math.sin(t * 47.0 + 0.4)
        oy = a * math.sin(t * 39.0 + 1.7)
        x0, x1 = w * 0.07 + ox, w * 0.32 + ox
        y0, y1 = h * 0.072 + oy, h * 0.235 + oy
        vw, vh = x1 - x0, y1 - y0
        r = vw * 0.32
        heat = min(1.0, max(0.0, (temp - 290) / 2600))

        def capsule():
            ctx.new_path()
            ctx.arc(x0 + r, y0 + r, r, math.pi, 1.5 * math.pi)
            ctx.arc(x1 - r, y0 + r, r, 1.5 * math.pi, 2 * math.pi)
            ctx.arc(x1 - r, y1 - r, r, 0, 0.5 * math.pi)
            ctx.arc(x0 + r, y1 - r, r, 0.5 * math.pi, math.pi)
            ctx.close_path()
        # heat glow around the vessel
        c.glow((x0 + x1) / 2, (y0 + y1) / 2, vw * 0.45, (1.0, 0.45 - 0.3 * heat, 0.15), strength=0.10 + 0.55 * heat, reach=2.0)
        # inside: dark, then the coolant (blue) at its level, then the fuel rods
        capsule()
        ctx.set_source_rgb(0.04, 0.05, 0.09)
        ctx.fill()
        ctx.save()
        capsule()
        ctx.clip()
        lvl = coolant(t)
        wy = y1 - (vh * 0.9) * lvl
        g = cairo.LinearGradient(0, wy, 0, y1)
        g.add_color_stop_rgba(0, 0.25, 0.65, 1.0, 0.55)
        g.add_color_stop_rgba(1, 0.10, 0.30, 0.80, 0.75)
        ctx.rectangle(x0, wy, vw, y1 - wy)
        ctx.set_source(g)
        ctx.fill()
        if lvl > 0.02:                                               # boiling bubbles, faster as it heats
            n_b = int(6 + 30 * heat)
            for k in range(n_b):
                ph = (t * (0.6 + 1.8 * heat) + k * 0.137) % 1.0
                bx = x0 + vw * (0.12 + 0.76 * ((k * 0.381) % 1.0))
                by = y1 - (y1 - wy) * ph
                c.circle(bx, by, 2.0 + 2.5 * ((k * 0.53) % 1.0), (0.8, 0.95, 1.0), alpha=0.6 * (1 - ph))
        # fuel rods: amber -> orange -> white-hot
        rod_col = (1.0, 0.55 + 0.45 * heat, 0.15 + 0.85 * heat ** 2)
        rx = [x0 + vw * (0.2 + 0.15 * k) for k in range(5)]
        rt, rb = y0 + vh * 0.42, y1 - vh * 0.08
        for k, xx in enumerate(rx):
            flick = 0.85 + 0.15 * math.sin(t * 9 + k)
            c.glow(xx, (rt + rb) / 2, vw * 0.05, rod_col, strength=(0.3 + 0.6 * heat) * flick, reach=2.2)
            ctx.rectangle(xx - vw * 0.025, rt, vw * 0.05, rb - rt)
            ctx.set_source_rgba(*rod_col, 0.95)
            ctx.fill()
        # control rods (between the fuel rods): partly in, SLAM down at the scram, jam halfway
        ins = 0.10
        if t >= T_SCRAM:
            ins = 0.10 + 0.42 * smooth((t - T_SCRAM) / (T_JAM - T_SCRAM))
        jam_shake = vw * 0.012 * math.sin(t * 70) if T_JAM <= t < T_FLASH else 0.0
        for k in range(4):
            xx = (rx[k] + rx[k + 1]) / 2 + jam_shake
            bot = y0 + vh * 0.08 + vh * 0.82 * ins
            ctx.rectangle(xx - vw * 0.022, y0 - vh * 0.08, vw * 0.044, bot - (y0 - vh * 0.08))
            ctx.set_source_rgba(0.75, 0.8, 0.9, 0.98)
            ctx.fill()
            if T_JAM <= t < T_JAM + 0.5:                              # sparks where they jam
                u = (t - T_JAM) / 0.5
                for j in range(5):
                    ang = math.pi * (0.1 + 0.8 * ((j * 0.37 + k * 0.21) % 1.0))
                    c.circle(xx + math.cos(ang) * vw * 0.15 * u, bot - math.sin(ang) * vw * 0.1 * u + vh * 0.3 * u * u,
                             2.2, (1.0, 0.85, 0.4), alpha=1 - u)
        ctx.restore()
        # the steel shell + pipes with flowing coolant (they stop when the flow stops)
        capsule()
        ctx.set_source_rgba(0.70 + 0.3 * dg, 0.75 - 0.4 * dg, 0.85 - 0.6 * dg, 0.95)
        ctx.set_line_width(5)
        ctx.stroke()
        flow = coolant(t)
        for side, py in ((-1, y0 + vh * 0.62), (1, y0 + vh * 0.32)):
            px0 = x0 if side < 0 else x1
            px1 = px0 + side * vw * 0.18
            c.lines([(px0, py, px1, py)], (0.6, 0.7, 0.9), width=8, alpha=0.9)
            if flow > 0.02:
                ctx.set_dash([8, 8], -(t * 60 * flow * side) % 16)
                ctx.move_to(px0, py)
                ctx.line_to(px1, py)
                ctx.set_source_rgba(0.35, 0.8, 1.0, 0.9 * flow)
                ctx.set_line_width(3)
                ctx.stroke()
                ctx.set_dash([])
        # the radiation sign on the vessel
        sx_, sy_, sr = x0 + vw * 0.5, y0 + vh * 0.24, vw * 0.075
        c.circle(sx_, sy_, sr * 1.25, (1.0, 0.82, 0.2), alpha=0.95)
        for k in range(3):
            a0 = -math.pi / 2 + k * 2 * math.pi / 3 - math.pi / 6
            ctx.new_path()
            ctx.move_to(sx_, sy_)
            ctx.arc(sx_, sy_, sr, a0, a0 + math.pi / 3)
            ctx.close_path()
            ctx.set_source_rgb(0.05, 0.05, 0.05)
            ctx.fill()
        c.circle(sx_, sy_, sr * 0.22, (1.0, 0.82, 0.2))
        c.circle(sx_, sy_, sr * 0.14, (0.05, 0.05, 0.05))
        if not (T_SCRAM <= t < T_JAM + 0.6):
            self.mono("REACTOR CORE", (x0 + x1) / 2, y0 - h * 0.012, h * 0.016, (0.85, 0.9, 1.0), alpha=0.8, align="center")
        if T_SCRAM <= t < T_JAM + 0.6:
            self.mono("SCRAM ▼", (x0 + x1) / 2, y0 - h * 0.012, h * 0.016, RED, align="center")

    def mono(self, s, x, y, size, col, alpha=1.0, align="left"):
        ctx = self.canvas.ctx
        ctx.select_font_face(FONT_MONO, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        ctx.set_font_size(size)
        ext = ctx.text_extents(s)
        if align == "right":
            x -= ext.x_advance
        elif align == "center":
            x -= ext.x_advance / 2
        ctx.set_source_rgba(*col, alpha)
        ctx.move_to(x, y)
        ctx.show_text(s)

    def scene(self, t):
        """everything up to the black cut"""
        L, c = self.L, self.canvas
        w, h = L.w, L.h
        ctx = c.ctx
        dg = danger(t)
        ctx.set_source_rgb(*NAVY)
        ctx.paint()
        g = cairo.RadialGradient(w / 2, h * 0.5, 0, w / 2, h * 0.5, h * 0.65)
        g.add_color_stop_rgba(0, 0.10 + 0.25 * dg, 0.10 - 0.04 * dg, 0.22 - 0.12 * dg, 0.6)
        g.add_color_stop_rgba(1, 0, 0, 0, 0)
        ctx.set_source(g)
        ctx.paint()
        # screen shake (smooth noise, not a strobe)
        a = shake_amp(t)
        sx = a * (math.sin(t * 61.0) * 0.6 + math.sin(t * 37.3 + 1.1) * 0.4)
        sy = a * (math.sin(t * 53.0 + 2.0) * 0.6 + math.sin(t * 29.7) * 0.4)
        ctx.save()
        ctx.translate(sx, sy)
        # dotted grid, flickering gently in the alarm phase
        flick = 1.0 - 0.45 * dg * (0.5 + 0.5 * math.sin(t * 17.0) * math.sin(t * 5.3))
        step = w / 22
        for gx in np.arange(step / 2, w, step):
            for gy in np.arange(step / 2, h, step):
                ctx.rectangle(gx - 1, gy - 1, 2, 2)
        ctx.set_source_rgba(0.55, 0.65, 1.0, 0.13 * flick)
        ctx.fill()

        ts = np.arange(0.0, min(t, T_FLASH) + 1e-9, 0.02)
        for ch, (name, col0, yc) in enumerate(PANELS):
            col = tuple(col0[i] + (RED[i] - col0[i]) * dg * 0.25 for i in range(3))
            frame_col = tuple(col0[i] + (RED[i] - col0[i]) * dg * 0.9 for i in range(3))
            # the panel (a glowing frame in 3-D)
            corners = [(-PW, yc - PH), (PW, yc - PH), (PW, yc + PH), (-PW, yc + PH)]
            px, py = self.proj([p[0] for p in corners], [p[1] for p in corners], t)
            quad = list(zip(px, py))
            c.poly(quad, frame_col, alpha=0.05 + 0.05 * dg)
            c.polylines([quad + [quad[0]]], frame_col, width=10, alpha=0.10 * flick)
            for q in (0.25, 0.5, 0.75):                                   # inner grid lines
                gx, gy = self.proj([-PW, PW], [yc - PH + 2 * PH * q] * 2, t)
                c.lines([(gx[0], gy[0], gx[1], gy[1])], col, width=1, alpha=0.12 * flick)
            lx, ly = self.proj([-PW + 0.04], [yc + PH - 0.06], t)
            self.mono(name, float(lx[0]), float(ly[0]), h * 0.021, col, alpha=0.95)
            # the curve (it may leave the panel when it spikes)
            if len(ts) > 1:
                v = value(ch, ts)
                X = -PW * 0.94 + 2 * PW * 0.94 * ts / T_AXIS
                Y = yc - PH + 2 * PH * v
                X = np.append(X, X[-1])
                Y = np.append(Y, Y[-1])
                qx, qy = self.proj(X, Y, t)
                pts = list(zip(qx.tolist(), qy.tolist()))
                c.polylines([pts], col, width=14, alpha=0.12)
                c.polylines([pts], col, width=4, alpha=1.0)
                tx, ty = pts[-1]
                c.glow(tx, ty, 9, col, strength=0.9, reach=3.0)
                c.circle(tx, ty, 6, (1, 1, 1))
            # sparks from the tip in the alarm phase (deterministic: seeded per spawn frame)
            if t > 8.0:
                f_now = int(t * FPS)
                for fs in range(max(int(8.0 * FPS), f_now - 50), f_now + 1):
                    tsp = fs / FPS
                    vs = float(value(ch, min(tsp, T_FLASH)))
                    if vs < 0.75 or tsp > T_FLASH:
                        continue
                    rng = np.random.default_rng(fs * 7 + ch)
                    xw = -PW * 0.94 + 2 * PW * 0.94 * min(tsp, T_FLASH) / T_AXIS
                    yw = yc - PH + 2 * PH * vs
                    bx, by = self.proj([xw], [yw], t)
                    age = t - tsp
                    for _ in range(1 + int(3 * dg)):
                        ang = rng.uniform(-math.pi, 0)
                        spd = rng.uniform(150, 520)
                        x = bx[0] + math.cos(ang) * spd * age
                        y = by[0] + math.sin(ang) * spd * age + 900 * age * age
                        c.circle(x, y, 2.6 * (1 - age / 0.85), (1.0, 0.85, 0.5), alpha=max(0.0, 1 - age / 0.85))
        ctx.restore()

        # headline: CORE TEMP (huge), coolant bar, readouts
        temp, pres, rad = readouts(t)
        hot = tuple(AMBER[i] + (RED[i] - AMBER[i]) * dg for i in range(3))
        pop = 1.0 + 0.35 * (1 - smooth(t / 1.6))
        self.core(t, temp)
        hx = w * 0.64
        c.text_centered("CORE TEMP", h * 0.115, size=h * 0.024, color=(0.85, 0.88, 1.0), alpha=0.9, cx=hx)
        c.glow(hx, h * 0.165, w * 0.16, hot, strength=0.18 + 0.2 * dg, reach=1.8)
        c.text_centered(f"{temp:,.0f}°C", h * 0.19, size=h * 0.062 * pop, color=hot, cx=hx, max_w=w * 0.6)
        self.mono(f"PRESSURE  {pres:5.1f} MPa", w * 0.07, h * 0.738, h * 0.024, CYAN)
        rad_s = f"{rad:,.1f} mSv/h" if rad < 1000 else f"{rad / 1000:,.1f} Sv/h"
        self.mono(f"RADIATION {rad_s}", w * 0.07, h * 0.762, h * 0.024, MAGENTA)
        cf = coolant(t)
        bx0, bx1, by = w * 0.07, w * 0.93, h * 0.792
        ctx.rectangle(bx0, by, bx1 - bx0, h * 0.014)
        ctx.set_source_rgba(0.6, 0.7, 1.0, 0.18)
        ctx.fill()
        ctx.rectangle(bx0, by, (bx1 - bx0) * cf, h * 0.014)
        ctx.set_source_rgba(0.3 + 0.7 * (1 - cf), 0.75 * cf + 0.2, 1.0 * cf, 0.95)
        ctx.fill()
        self.mono(f"COOLANT FLOW {cf * 100:3.0f}%", w * 0.07, h * 0.785, h * 0.020, (0.85, 0.9, 1.0), alpha=0.9)
        # SCRAM FAILED (smooth blink, 2 Hz)
        if T_JAM <= t < T_FLASH:
            bl = 0.5 + 0.5 * math.cos(2 * math.pi * 2.0 * (t - T_JAM))
            c.glow(w / 2, h * 0.5, w * 0.28, RED, strength=0.25 * bl, reach=1.6)
            c.text_centered("SCRAM FAILED", h * 0.52, size=h * 0.055, color=(1.0, 0.25, 0.2), alpha=0.25 + 0.75 * bl)
        # red tint pulse (low contrast)
        if dg > 0:
            ctx.set_source_rgba(0.6, 0.0, 0.0, 0.06 * dg * (0.5 + 0.5 * math.sin(2 * math.pi * 1.0 * t)))
            ctx.paint()

    def draw(self, f):
        L, c = self.L, self.canvas
        w, h = L.w, L.h
        t = f * DT
        ctx = c.ctx
        if t < T_BLACK:
            self.scene(t)
            if t >= T_FLASH:                                   # ONE white flash, then the fall to black
                fl = max(0.0, 1.0 - (t - T_FLASH) / 0.32)
                ctx.set_source_rgba(1, 1, 1, fl)
                ctx.paint()
                ctx.set_source_rgba(0, 0, 0, smooth((t - T_FLASH - 0.15) / 0.35))
                ctx.paint()
        elif t < T_Q:
            ctx.set_source_rgb(0, 0, 0)
            ctx.paint()
        else:
            ctx.set_source_rgb(0.01, 0.01, 0.025)
            ctx.paint()
            pulse = 1.0 + 0.04 * math.sin(2 * math.pi * 0.8 * (t - T_Q))
            k = smooth((t - T_BACK) / (T_LOOP - T_BACK))
            if k > 0:                                          # dissolve into frame 0 (the calm start)
                ctx.push_group()
                self.scene(0.0)
                ctx.pop_group_to_source()
                ctx.paint_with_alpha(k)
            a = 1.0 - k
            c.glow(w / 2, h * 0.44, w * 0.22, AMBER, strength=0.55 * a, reach=2.2)
            c.text_centered("?", h * 0.53, size=h * 0.30 * pulse * (1 - 0.4 * k), color=(1.0, 0.82, 0.45), alpha=a)
        c.watermark(L)


def render(layout, out_path, still_frame=None):
    sc = Scene(layout)
    writer = None if still_frame is not None else VideoWriter(out_path, sc.canvas, FPS)
    nf = int(round(T_LOOP * FPS))
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


# --- the sound --------------------------------------------------------------------------------------------------------

SR = audio.SR


def _voice(freq, harm, sr=SR):
    ph = 2 * np.pi * np.cumsum(freq) / sr
    return sum(a * np.sin(k * ph) for k, a in harm)


def build_bed():
    n = int(round(T_LOOP * SR))
    t = np.arange(n) / SR
    live = t < T_FLASH
    tv = np.minimum(t, T_FLASH)
    vT, vP, vR = (np.clip(value(ch, tv), 0, 2.2) for ch in range(3))
    # the three singing lines: pitch follows the value
    fT = 110.0 * 2 ** (1.5 * (vT - 0.12))
    fP = 330.0 * 2 ** (1.3 * (vP - 0.12)) * (1 + 0.004 * np.sin(2 * np.pi * 5.5 * t))
    fR = 880.0 * 2 ** (1.0 * (vR - 0.12))
    hum = _voice(fT, ((1, 1.0), (2, 0.45), (3, 0.25), (4, 0.12), (5, 0.07)))
    whine = _voice(fP, ((1, 1.0), (3, 0.11), (5, 0.04)))
    whistle = _voice(fR, ((1, 1.0), (2, 0.08)))
    dg = np.clip((t - 8.0) / 1.5, 0, 1)
    grow = 0.45 + 1.55 * np.clip((t - 2) / 13, 0, 1) ** 1.3
    mix = (0.20 * hum + 0.10 * whine + 0.045 * whistle) * grow
    # the Geiger counter: click rate follows radiation (deterministic)
    rng = np.random.default_rng(3)
    clicks = np.zeros(n)
    rate = 1.5 + 240.0 * np.clip(vR - 0.12, 0, None) ** 2
    p = rate / SR
    hits = np.nonzero((rng.random(n) < p) & live)[0]
    ck = rng.standard_normal(int(0.0025 * SR)) * np.exp(-np.arange(int(0.0025 * SR)) / (0.0006 * SR))
    for i in hits:
        clicks[i:i + len(ck)] += ck[: max(0, n - i)]
    mix += 0.10 * clicks
    # the alarm: two-tone pulse, 8 s -> flash
    al_t = (t >= 8.0) & live
    tone = np.where((np.floor((t - 8.0) * 2) % 2) == 0, 740.0, 554.0)
    alarm = np.tanh(2.5 * np.sin(2 * np.pi * np.cumsum(tone) / SR)) * (0.6 + 0.4 * np.sin(np.pi * ((t - 8.0) * 2 % 1)))
    mix += 0.055 * alarm * al_t * dg
    # everything cuts at the flash (short fade, no click)
    cut = np.clip((T_FLASH - t) / 0.015, 0, 1)
    mix *= cut
    # the boom
    i0 = int(T_FLASH * SR)
    tb = np.arange(int(2.2 * SR)) / SR
    boom = np.sin(2 * np.pi * np.cumsum(32 + 140 * np.exp(-tb / 0.07)) / SR) * np.exp(-tb / 0.55)
    rumble = np.convolve(rng.standard_normal(len(tb)), np.ones(60) / 60, "same") * np.exp(-tb / 0.4) * 3.0
    mix[i0:i0 + len(tb)] += (1.1 * boom + 0.5 * rumble)[: n - i0]
    mix[int(T_BLACK * SR):int(T_Q * SR)] *= np.clip((T_BLACK + 0.25 - t[int(T_BLACK * SR):int(T_Q * SR)]) / 0.25, 0, 1)
    # the "?": a soft glass shimmer
    j0 = int(T_Q * SR)
    tq = np.arange(int(1.6 * SR)) / SR
    shimmer = sum(np.sin(2 * np.pi * f * tq) * np.exp(-tq / 0.7) for f in (1046.5, 1318.5, 1568.0)) / 3
    mix[j0:j0 + len(tq)] += 0.10 * shimmer[: n - j0]
    # the calm chord returns under the dissolve (same as t = 0) -> seamless loop
    k0 = int(T_BACK * SR)
    tail = t[k0:] - t[k0]
    env = np.clip(tail / (T_LOOP - T_BACK), 0, 1) ** 1.5
    calm = 0.45 * 0.20 * _voice(np.full(len(tail), 110.0), ((1, 1.0), (2, 0.45), (3, 0.25), (4, 0.12), (5, 0.07))) \
        + 0.45 * 0.10 * _voice(np.full(len(tail), 330.0), ((1, 1.0), (3, 0.11), (5, 0.04))) \
        + 0.45 * 0.045 * _voice(np.full(len(tail), 880.0), ((1, 1.0), (2, 0.08)))
    mix[k0:] += calm * env
    return (0.5 * mix).astype(np.float32)


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
