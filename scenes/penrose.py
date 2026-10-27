"""PENROSE — "This pattern never repeats": a Penrose rhombus tiling pops in from the centre.

Two tiles (a fat and a thin rhombus) cover the plane in a pattern that NEVER repeats. Generated
with the standard Robinson-triangle deflation (split every half-tile by the golden ratio, 7 times,
starting from a 10-triangle wheel). A wave of tiles pops in from the centre, faster and faster,
while the camera pulls back from close-up to the whole field; then a GOLDEN wave sweeps across
every tile and the fact lands: fat / thin tiles -> 1.618... (phi), the link to the channel's viral
golden-ratio Short. Finally the tiles collapse back to the centre (loop to frame 0).

Hook: frame 0 already has coloured tiles popping at the centre. Audio (original synthesis only):
glass-harp notes as the wave crosses each ring (climbing, faster), a chord + shimmer on the golden
sweep, a falling glissando on the collapse, a periodic pad.
"""
import cmath
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

SCENE = "penrose"
PHI = (1 + 5 ** 0.5) / 2
GENS = 7
COPY = arg("--copytest", "0") == "1"   # v2: a 4.7 s "copy test" intro shows WHAT never-repeating means
T_SQ, T_PZ, T_FOLD = 2.0, 2.3, 0.4      # squares test, Penrose test, fold into the centre
T_INTRO = (T_SQ + T_PZ + T_FOLD) if COPY else 0.0
T_BUILD, T_GOLD, T_HOLD, T_COLLAPSE = (7.5, 1.6, 0.7, 0.0) if COPY else (9.5, 1.6, 0.9, 1.4)
T_LOOP = T_INTRO + T_BUILD + T_GOLD + T_HOLD + T_COLLAPSE
R0 = 0.06                                # wave radius at frame 0 (a few tiles already popping)
Z0 = 7.0                                 # start zoom: the first tiles fill the frame
THIN = (1.00, 0.45, 0.62)
FAT = (0.25, 0.72, 0.92)
GOLD = (1.0, 0.80, 0.38)
EDGE = (0.04, 0.03, 0.07)


def tiling():
    tris = []
    for i in range(10):
        B = cmath.rect(1, (2 * i - 1) * math.pi / 10)
        C = cmath.rect(1, (2 * i + 1) * math.pi / 10)
        if i % 2 == 0:
            B, C = C, B
        tris.append((0, 0j, B, C))
    for _ in range(GENS):
        out = []
        for col, A, B, C in tris:
            if col == 0:                                   # half of a thin rhombus
                P = A + (B - A) / PHI
                out += [(0, C, P, B), (1, P, C, A)]
            else:                                          # half of a fat rhombus
                Q = B + (A - B) / PHI
                R = B + (C - B) / PHI
                out += [(1, R, C, A), (1, Q, R, B), (0, R, Q, A)]
        tris = out
    return tris


TRIS = tiling()
# rhombus centre = midpoint of the shared diagonal B-C (both halves pop together)
CEN = np.array([(B + C) / 2 for _, A, B, C in TRIS])
RAD = np.abs(CEN)
N_FAT = sum(1 for t in TRIS if t[0] == 1) // 2
N_THIN = sum(1 for t in TRIS if t[0] == 0) // 2


def wave_r(t):
    """Pop-wave radius: starts with a few tiles, accelerates out to the whole field."""
    u = min(max(t / T_BUILD, 0.0), 1.0)
    return R0 + (1.02 - R0) * (0.35 * u + 0.65 * u ** 2.2)


def zoom_at(t):
    """Camera: close-up (x3.2) at the start, the whole field (x1) by the end of the build."""
    return math.exp(math.log(Z0) * (1 - smooth(min(t / T_BUILD, 1.0)) ** 0.8))


def ease_back(p):
    p = min(max(p, 0.0), 1.0)
    c1 = 1.70158
    return 1 + (c1 + 1) * (p - 1) ** 3 + c1 * (p - 1) ** 2


def simulate():
    return {"nf": int(round(T_LOOP * FPS))}


class Scene:
    def __init__(self, layout, sim):
        self.L, self.sim = layout, sim
        self.canvas = Canvas(layout.w, layout.h, studio.render_scale())
        w, h = layout.w, layout.h
        self.c = (w / 2, h * 0.405)
        self.R = h * 0.205                                 # field radius on screen at zoom 1
        self.clip = (0, h * 0.225, w, h * 0.37)

    def draw(self, f, rule):
        L, c = self.L, self.canvas
        w, h = L.w, L.h
        t = f * DT
        if COPY:
            if t < T_INTRO:
                return self.intro(t, rule)
            t -= T_INTRO
        ctx = c.ctx
        g = cairo.RadialGradient(w / 2, h * 0.47, 0, w / 2, h * 0.47, max(w, h) * 0.7)
        g.add_color_stop_rgb(0.0, 0.07, 0.06, 0.11)
        g.add_color_stop_rgb(1.0, 0.01, 0.01, 0.02)
        ctx.set_source(g)
        ctx.paint()

        tc = T_BUILD + T_GOLD + T_HOLD
        if t < T_BUILD:
            rw, zoom = wave_r(t), zoom_at(t)
        elif t < tc:
            rw, zoom = 1.1, 1.0
        else:                                               # collapse back to frame 0
            k = smooth((t - tc) / T_COLLAPSE)
            rw = 1.1 + (R0 - 1.1) * k
            zoom = math.exp(math.log(Z0) * k)
        gold_r = -1.0
        if T_BUILD <= t < tc + T_COLLAPSE:
            gold_r = 1.15 * smooth((t - T_BUILD) / (T_GOLD * 0.8))
        gold_fade = 1.0 - smooth((t - tc) / 0.5) if t >= tc else 1.0
        S = self.R * zoom
        cx, cy = self.c
        ctx.save()
        ctx.rectangle(*self.clip)
        ctx.clip()
        lim = max(w, h) / S
        band = 0.06                                         # pop zone width (world units)
        ctx.set_line_join(cairo.LINE_JOIN_ROUND)
        for idx, (col, A, B, C) in enumerate(TRIS):
            r = RAD[idx]
            if r > rw + 0.001 or abs(CEN[idx].real) > lim or abs(CEN[idx].imag) > lim:
                continue
            p = ease_back((rw - r) / band) if t < tc else min(1.0, (rw - r) / band)
            if p <= 0.01:
                continue
            m = CEN[idx]
            pts = [m + (z - m) * p for z in (A, B, C)]
            base = FAT if col == 1 else THIN
            shade = 0.80 + 0.20 * math.cos(r * 9.0 + (0.6 if col else 0.0))
            fill = tuple(v * shade for v in base)
            if gold_r > 0 and r < gold_r:                   # the golden sweep
                gk = min(1.0, (gold_r - r) / 0.12) * gold_fade
                gcol = GOLD if col else (1.0, 0.93, 0.72)          # two golds keep the pattern visible
                fill = tuple(a + (b - a) * gk for a, b in zip(fill, gcol))
            sp = [(cx + z.real * S, cy - z.imag * S) for z in pts]
            ctx.move_to(*sp[0])
            ctx.line_to(*sp[1])
            ctx.line_to(*sp[2])
            ctx.close_path()
            ctx.set_source_rgb(*fill)
            ctx.fill_preserve()
            ctx.set_line_width(1.6)                        # seal the anti-alias seam on the diagonal
            ctx.stroke()
            ctx.move_to(*sp[2])                             # outline: C-A-B (no shared diagonal)
            ctx.line_to(*sp[0])
            ctx.line_to(*sp[1])
            ctx.set_source_rgb(*EDGE)
            ctx.set_line_width(max(1.2, 2.2 * min(zoom, 2.0) / 2.0))
            ctx.stroke()
        ctx.restore()

        # HUD
        shown = int(np.count_nonzero(RAD <= rw)) // 2
        fs = w * 0.05
        c.text_centered("FAMOUS PATTERNS · PENROSE", h * 0.205, size=h * 0.015, color=GOLD, alpha=0.8)
        if t < tc + T_COLLAPSE * 0.3:
            c.text_centered(f"{min(shown, N_FAT + N_THIN):,} tiles", h * 0.655, size=fs, color=(1, 1, 1))
        fa = smooth((t - T_BUILD - 0.6) / 0.4) * (1.0 - smooth((t - tc) / 0.35))
        if fa > 0.01:
            c.text_centered(f"fat ÷ thin = {N_FAT / N_THIN:.3f}…  → φ", h * 0.705, size=fs * 0.95, color=GOLD,
                            alpha=fa)
        if t < T_BUILD:
            c.text_centered("2 tile shapes · 0 repeats", h * 0.705, size=fs * 0.70, color=(0.80, 0.82, 0.92),
                            alpha=0.9, bold=False)
        if rule:
            c.caption(rule, alpha=1.0, layout=L)
        c.watermark(L)


# ---- v2 copy-test intro ---------------------------------------------------------------------------
Z_PZ = 4.6                                   # zoom of the Penrose copy test
P0 = complex(0.0, 0.0)                       # patch centre (world)
RP = 0.075                                   # patch radius (world)
SHIFTS = [complex(0.15, 0.03), complex(-0.09, -0.13)]
PATCH = [k for k in range(len(TRIS)) if abs(CEN[k] - P0) < RP]


def _edges():
    e = set()
    for col, A, B, C in TRIS:
        for u, v in ((C, A), (A, B)):
            key = tuple(sorted(((round(u.real, 6), round(u.imag, 6)), (round(v.real, 6), round(v.imag, 6)))))
            e.add(key)
    return e


EDGES = _edges()


def _match(u, v):
    return tuple(sorted(((round(u.real, 6), round(u.imag, 6)), (round(v.real, 6), round(v.imag, 6))))) in EDGES


def _intro(self, t, rule):
    L, c = self.L, self.canvas
    w, h = L.w, L.h
    ctx = c.ctx
    g = cairo.RadialGradient(w / 2, h * 0.47, 0, w / 2, h * 0.47, max(w, h) * 0.7)
    g.add_color_stop_rgb(0.0, 0.07, 0.06, 0.11)
    g.add_color_stop_rgb(1.0, 0.01, 0.01, 0.02)
    ctx.set_source(g)
    ctx.paint()
    cx, cy = self.c
    ctx.save()
    ctx.rectangle(*self.clip)
    ctx.clip()
    GREEN, RED = (0.40, 0.95, 0.50), (1.0, 0.30, 0.30)
    fs = w * 0.05
    if t < T_SQ:                                            # normal tiles: the copy fits every time
        sz = w * 0.13
        motif = [[THIN, FAT], [FAT, (0.95, 0.85, 0.45)]]
        x0, y0 = cx - sz * 4, cy - sz * 3
        for i in range(8):
            for j in range(6):
                ctx.rectangle(x0 + i * sz, y0 + j * sz, sz, sz)
                ctx.set_source_rgb(*motif[j % 2][i % 2])
                ctx.fill_preserve()
                ctx.set_source_rgb(*EDGE)
                ctx.set_line_width(3)
                ctx.stroke()
        hop = [(0.25, 0.85), (1.05, 1.65)]                  # two slides, each 2 tiles to the right
        ox = 0.0
        stamp = -1.0
        for k, (a, b) in enumerate(hop):
            if t >= a:
                ox = 2 * k + 2 * smooth(min(1.0, (t - a) / (b - a)))
            if t >= b:
                stamp = t - b
        bx, by = x0 + 2 * sz + ox * sz, y0 + 2 * sz
        snapped = stamp >= 0 and (t < hop[1][0] or t >= hop[1][1])
        colb = GREEN if snapped else (1, 1, 1)
        ctx.rectangle(bx, by, 2 * sz, 2 * sz)
        ctx.set_source_rgba(1, 1, 1, 0.18)
        ctx.fill_preserve()
        ctx.set_source_rgba(*colb, 0.95)
        ctx.set_line_width(9)
        ctx.stroke()
        ctx.restore()
        c.text_centered("normal tiles", h * 0.655, size=fs, color=(1, 1, 1))
        if snapped:
            c.text_centered("MATCH!  it repeats", h * 0.708, size=fs * 1.05, color=GREEN)
        else:
            c.text_centered("copy… slide…", h * 0.705, size=fs * 0.75, color=(0.8, 0.82, 0.92), bold=False)
    else:
        tt = t - T_SQ
        fold = smooth((tt - T_PZ) / T_FOLD) if tt > T_PZ else 0.0
        zoom = math.exp(math.log(Z_PZ) + (math.log(Z0) - math.log(Z_PZ)) * fold)
        rw = 1.2 + (R0 - 1.2) * fold
        S = self.R * zoom
        lim = max(w, h) / S
        for idx, (col, A, B, C) in enumerate(TRIS):
            if RAD[idx] > rw or abs(CEN[idx].real) > lim or abs(CEN[idx].imag) > lim:
                continue
            m = CEN[idx]
            pp = min(1.0, (rw - RAD[idx]) / 0.06) if fold > 0 else 1.0
            sp = [(cx + (m + (z - m) * pp).real * S, cy - (m + (z - m) * pp).imag * S) for z in (A, B, C)]
            ctx.move_to(*sp[0])
            ctx.line_to(*sp[1])
            ctx.line_to(*sp[2])
            ctx.close_path()
            ctx.set_source_rgb(*(FAT if col == 1 else THIN))
            ctx.fill_preserve()
            ctx.set_line_width(1.6)
            ctx.stroke()
            ctx.move_to(*sp[2])
            ctx.line_to(*sp[0])
            ctx.line_to(*sp[1])
            ctx.set_source_rgb(*EDGE)
            ctx.set_line_width(2.4)
            ctx.stroke()
        result = None
        if fold == 0:
            hop = [(0.20, 0.85), (1.15, 1.80)]
            off, at_rest = 0j, False
            for k, (a, b) in enumerate(hop):
                if tt >= a:
                    prev = SHIFTS[k - 1] if k else 0j
                    off = prev + (SHIFTS[k] - prev) * smooth(min(1.0, (tt - a) / (b - a)))
                if tt >= b:
                    at_rest, result = True, k
            if tt >= hop[1][0] and tt < hop[1][1]:
                at_rest = False
            for idx in PATCH:                               # the glowing copy of the patch
                col, A, B, C = TRIS[idx]
                pts = [z + off for z in (A, B, C)]
                sp = [(cx + z.real * S, cy - z.imag * S) for z in pts]
                ctx.move_to(*sp[0])
                ctx.line_to(*sp[1])
                ctx.line_to(*sp[2])
                ctx.close_path()
                ctx.set_source_rgba(1, 1, 1, 0.30)
                ctx.fill()
                for u, v in ((pts[2], pts[0]), (pts[0], pts[1])):
                    ok = _match(u, v)
                    colr = (GREEN if ok else RED) if (at_rest and off != 0) else (1, 1, 1)
                    ctx.move_to(cx + u.real * S, cy - u.imag * S)
                    ctx.line_to(cx + v.real * S, cy - v.imag * S)
                    ctx.set_source_rgba(*colr, 0.95)
                    ctx.set_line_width(6)
                    ctx.stroke()
            if not at_rest:
                result = None
        ctx.restore()
        if fold < 0.5:
            c.text_centered("Penrose tiles", h * 0.655, size=fs, color=(1, 1, 1))
            if result is not None:
                c.text_centered("NO MATCH, ever", h * 0.708, size=fs * 1.05, color=RED)
            else:
                c.text_centered("same copy test…", h * 0.705, size=fs * 0.75, color=(0.8, 0.82, 0.92), bold=False)
    c.text_centered("FAMOUS PATTERNS · PENROSE", h * 0.205, size=h * 0.015, color=GOLD, alpha=0.8)
    if rule:
        c.caption(rule, alpha=1.0, layout=L)
    c.watermark(L)


Scene.intro = _intro


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
    walker = audio.ScaleWalker(root_midi=62, scale=audio.PENTA_MAJOR, span=14, pattern="up")
    out = [{"t": 0.02, "note": n, "gain": 0.40, "x": layout.w / 2} for n in (50, 62, 66)]   # sound on frame 0
    ring, k = 0.07, 1
    for f in range(int(T_BUILD * FPS) + 1):
        t = f * DT
        while wave_r(t) >= R0 + k * ring and R0 + k * ring <= 1.02:
            out.append({"t": round(t, 4), "note": walker.next(), "gain": round(0.34 + 0.14 * k * ring, 3),
                        "x": layout.w * (0.5 + 0.3 * math.sin(k * 2.1))})
            k += 1
    for j, note in enumerate((50, 57, 62, 66, 69, 74)):
        out.append({"t": round(T_BUILD + 0.05 * j, 4), "note": note, "gain": 0.46, "x": layout.w / 2})
    for j, note in enumerate((81, 86, 90, 86)):
        out.append({"t": round(T_BUILD + 0.5 + 0.3 * j, 4), "note": note, "gain": 0.20, "x": layout.w / 2})
    tc = T_BUILD + T_GOLD + T_HOLD
    for j, note in enumerate((86, 81, 78, 74, 69, 66, 62)):
        out.append({"t": round(tc + 0.05 + 0.17 * j, 4), "note": note, "gain": 0.22, "x": layout.w / 2})
    if COPY:                                               # shift the build, add the copy-test sounds
        out = [dict(e, t=round(e["t"] + T_INTRO, 4)) for e in out if e["t"] < T_BUILD + T_GOLD + T_HOLD]
        for b in (0.85, 1.65):                                         # ✓ fits: a bright two-note ding
            for j, note in enumerate((79, 84)):
                out.append({"t": round(b + 0.07 * j, 4), "note": note, "gain": 0.42, "x": layout.w / 2})
        for b in (0.85, 1.80):                                         # ✗ never: a soft falling pair
            for j, note in enumerate((67, 62)):
                out.append({"t": round(T_SQ + b + 0.10 * j, 4), "note": note, "gain": 0.40, "x": layout.w / 2})
        for j, note in enumerate((74, 69, 62)):                        # the fold into the centre
            out.append({"t": round(T_SQ + T_PZ + 0.08 * j, 4), "note": note, "gain": 0.24, "x": layout.w / 2})
        out.append({"t": 0.02, "note": 62, "gain": 0.35, "x": layout.w / 2})
    return sorted(out, key=lambda e: e["t"])


def _worker(o, sim, label, rule):
    layout = get_layout(o)
    name = f"{SCENE}_{label}_{layout.tag}"
    video = studio.OUT_DIR / f"{name}_silent.mp4"
    d = render(layout, sim, video, rule)
    pad = kit.loop_pad(T_LOOP, ((50, 1.0), (57, 0.7), (62, 0.45), (66, 0.3)), gain=0.015)
    kit.deliver_loop(SCENE, name, layout, video, build_events(sim, layout), d, voice="glassharp", bed=pad)


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
    print(f"[{SCENE}] {T_LOOP:.1f}s, {len(TRIS)} half-tiles, fat {N_FAT} thin {N_THIN} ratio {N_FAT / N_THIN:.4f}")
    kit.fan_out(_worker, (sim, label, rule), SCENE)


if __name__ == "__main__":
    main()
