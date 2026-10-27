"""Instagram starter kit for SatFy: profile pictures, story-highlight covers and Reel covers (all drawn in code).

  python tools/instagram_kit.py            -> final/instagram/{profile,highlights,reel_covers}/
Reel covers are a frame of each uploaded Short + a 2-line title inside the 3:4 grid-safe area (y 240..1680 of 1920).
"""
import math
import subprocess
import sys
from pathlib import Path

import cairo
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "final" / "instagram"
BG = (0.035, 0.045, 0.085)
GOLD = (1.0, 0.82, 0.40)


def hsv(h, s=0.6, v=1.0):
    h = h % 1.0
    i = int(h * 6)
    f = h * 6 - i
    p, q, t = v * (1 - s), v * (1 - s * f), v * (1 - s * (1 - f))
    return [(v, t, p), (q, v, p), (p, v, t), (p, q, v), (t, p, v), (v, p, q)][i % 6]


def stroke_path(c, pts, col, width, glow=True, alpha=1.0):
    for w, a in (((width * 5, 0.10), (width * 2.2, 0.25)) if glow else ()) + ((width, 1.0),):
        c.set_source_rgba(*col, a * alpha)
        c.set_line_width(w)
        c.set_line_join(cairo.LINE_JOIN_ROUND)
        c.move_to(*pts[0])
        for p in pts[1:]:
            c.line_to(*p)
        c.stroke()


def bg(c, W, H, cx, cy):
    c.set_source_rgb(*BG)
    c.paint()
    g = cairo.RadialGradient(cx, cy, 0, cx, cy, max(W, H) * 0.65)
    g.add_color_stop_rgba(0, 0.13, 0.11, 0.26, 1)
    g.add_color_stop_rgba(1, 0.02, 0.02, 0.05, 1)
    c.set_source(g)
    c.paint()


def hypo(cx, cy, S, R0=13, r0=8, d0=11.0, n=3000):
    T = 2 * math.pi * r0 / math.gcd(R0, r0)
    t = np.linspace(0, T, n)
    x = (R0 - r0) * np.cos(t) + d0 * np.cos((R0 - r0) / r0 * t)
    y = (R0 - r0) * np.sin(t) - d0 * np.sin((R0 - r0) / r0 * t)
    return list(zip(cx + S * x, cy - S * y))


# ------------------------------------------------------------------ profile pictures (1080x1080, circle-safe)
def profile_spiro(path):
    W = 1080
    s = cairo.ImageSurface(cairo.FORMAT_RGB24, W, W)
    c = cairo.Context(s)
    bg(c, W, W, W / 2, W / 2)
    for j, (q, col) in enumerate(((0.44, hsv(0.72)), (0.72, hsv(0.62)), (1.0, (1.0, 0.6, 0.85)))):
        stroke_path(c, hypo(W / 2, W / 2, 21.0, d0=11 * q), col, 5.5 if j == 2 else 4.5)
    s.write_to_png(str(path))


def profile_golden(path):
    """Golden-ratio squares + spiral, the channel's most-viewed theme."""
    W = 1080
    s = cairo.ImageSurface(cairo.FORMAT_RGB24, W, W)
    c = cairo.Context(s)
    bg(c, W, W, W / 2, W / 2)
    phi = (1 + 5 ** 0.5) / 2
    sq, box = [(0.0, 0.0, 1.0)], [0.0, 0.0, 1.0, 1.0]
    F = [1, 1]
    for _ in range(9):
        F.append(F[-1] + F[-2])
    for n in range(1, len(F)):
        sz, d = F[n], (n - 1) % 4
        if d == 0:
            sq.append((box[2], box[1], sz)); box[2] += sz
        elif d == 1:
            sq.append((box[0], box[3], sz)); box[3] += sz
        elif d == 2:
            sq.append((box[0] - sz, box[1], sz)); box[0] -= sz
        else:
            sq.append((box[0], box[1] - sz, sz)); box[1] -= sz
    bw, bh = box[2] - box[0], box[3] - box[1]
    S = W * 0.80 / max(bw, bh)
    ox, oy = W / 2 - S * (box[0] + bw / 2), W / 2 + S * (box[1] + bh / 2)
    P = lambda x, y: (ox + S * x, oy - S * y)  # noqa: E731
    cols = [(1.00, 0.42, 0.55), (1.00, 0.70, 0.30), (0.40, 0.85, 0.55), (0.30, 0.70, 1.00)]
    for n, (x, y, sz) in enumerate(sq):
        x0, y0 = P(x, y + sz)
        c.rectangle(x0, y0, S * sz, S * sz)
        c.set_source_rgba(*cols[n % 4], 0.55)
        c.fill_preserve()
        c.set_source_rgba(0.03, 0.03, 0.06, 1)
        c.set_line_width(4)
        c.stroke()
    # quarter arcs (same chaining rule as scenes/fib_dive.py)
    Pp = (0.0, 1.0)
    arcs = [((1.0, 1.0), 1.0, (0.0, 1.0), (1.0, 0.0))]
    Pp = (1.0, 0.0)
    bx = [0.0, 0.0, 1.0, 1.0]
    boxes = [tuple(bx)]
    for n in range(1, len(F)):
        x, y, sz = sq[n]
        prev = boxes[-1]
        corners = [(x, y), (x + sz, y), (x + sz, y + sz), (x, y + sz)]
        shared = [q for q in corners if prev[0] - 1e-9 <= q[0] <= prev[2] + 1e-9 and prev[1] - 1e-9 <= q[1] <= prev[3] + 1e-9]
        C = [q for q in shared if abs(q[0] - Pp[0]) + abs(q[1] - Pp[1]) > 1e-9][0]
        Q = [q for q in corners if abs(math.hypot(q[0] - C[0], q[1] - C[1]) - sz) < 1e-9 and abs(q[0] - Pp[0]) + abs(q[1] - Pp[1]) > 1e-9][0]
        arcs.append((C, sz, Pp, Q))
        Pp = Q
        boxes.append((min(prev[0], x), min(prev[1], y), max(prev[2], x + sz), max(prev[3], y + sz)))
    pts = []
    for (Cx, Cy), r, (Px, Py), (Qx, Qy) in arcs:
        a0, a1 = math.atan2(Py - Cy, Px - Cx), math.atan2(Qy - Cy, Qx - Cx)
        da = (a1 - a0 + math.pi) % (2 * math.pi) - math.pi
        pts += [P(Cx + r * math.cos(a0 + da * j / 30), Cy + r * math.sin(a0 + da * j / 30)) for j in range(31)]
    stroke_path(c, pts, (1.0, 0.95, 0.8), 7)
    s.write_to_png(str(path))


# ------------------------------------------------------------------ highlight covers (1080x1920, icon in the centre circle)
def highlight(path, kind, col):
    W, H = 1080, 1920
    s = cairo.ImageSurface(cairo.FORMAT_RGB24, W, H)
    c = cairo.Context(s)
    cx, cy = W / 2, H / 2
    bg(c, W, H, cx, cy)
    c.set_source_rgba(*col, 0.9)
    c.set_line_width(10)
    c.arc(cx, cy, 380, 0, 2 * math.pi)
    c.stroke()
    if kind == "sound":
        xs = np.linspace(-280, 280, 400)
        pts = [(cx + x, cy - 130 * math.sin(x / 45) * math.exp(-(x / 230) ** 2)) for x in xs]
        stroke_path(c, pts, col, 12)
    elif kind == "illusion":
        R = 270
        for k in range(8):
            a = k * math.pi / 8
            stroke_path(c, [(cx - R * math.cos(a), cy + R * math.sin(a)), (cx + R * math.cos(a), cy - R * math.sin(a))],
                        hsv(k / 8), 5, glow=False, alpha=0.7)
        t = np.linspace(0, 2 * math.pi, 200)
        stroke_path(c, list(zip(cx + R / 2 + R / 2 * np.cos(t), cy + R / 2 * np.sin(t))), GOLD, 10)
    elif kind == "physics":
        for k in range(7):
            L = 120 + 32 * k
            a = 0.5 * math.sin(k * 0.9)
            x0, y0 = cx - 210 + 70 * k, cy - 260
            bx_, by_ = x0 + L * math.sin(a), y0 + L * math.cos(a)
            stroke_path(c, [(x0, y0), (bx_, by_)], (0.85, 0.85, 0.9), 4, glow=False)
            c.set_source_rgb(*hsv(0.6 - k * 0.09))
            c.arc(bx_, by_, 26, 0, 2 * math.pi)
            c.fill()
        stroke_path(c, [(cx - 260, cy - 260), (cx + 260, cy - 260)], (0.9, 0.9, 1.0), 10, glow=False)
    elif kind == "numbers":
        c.select_font_face("Arial", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        c.set_font_size(430)
        ext = c.text_extents("π")
        for w, a in ((24, 0.12), (10, 0.3)):
            c.move_to(cx - ext.width / 2 - ext.x_bearing, cy + ext.height / 2)
            c.text_path("π")
            c.set_source_rgba(*col, a)
            c.set_line_width(w)
            c.stroke()
        c.move_to(cx - ext.width / 2 - ext.x_bearing, cy + ext.height / 2)
        c.set_source_rgb(*col)
        c.show_text("π")
    elif kind == "art":
        stroke_path(c, hypo(cx, cy, 13.5), col, 5)
    s.write_to_png(str(path))


# ------------------------------------------------------------------ reel covers
REELS = [  # folder, time (s) of the frame, line 1, line 2 (gold)
    ("fib_add_v1", 6.0, "Fibonacci", "part 2"),
    ("fib_spiral_v2", 5.0, "The golden", "spiral"),
    ("math_sounds_v1", 6.0, "What math", "sounds like"),
    ("pi_canon", 11.5, "π plays", "Pachelbel's Canon"),
    ("tusi", 10.5, "This circle", "is FAKE"),
    ("spin_wave", 5.0, "Each one spins", "1 more lap"),
    ("heart_eq_v1", 6.0, "A heart from", "one equation"),
    ("math_sounds_p2h", 6.0, "Math sounds", "part 2"),
    ("sunflower_v1", 6.0, "The sunflower", "secret"),
]


def reel_cover(folder, t, l1, l2, path):
    src = sorted((ROOT / "final" / "uploaded" / folder).glob("*9x16*.mp4"))[0]
    tmp = OUT / "_frame.png"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", str(t), "-i", str(src), "-frames:v", "1",
                    "-vf", "scale=1080:1920", str(tmp)], check=True)
    img = cairo.ImageSurface.create_from_png(str(tmp))
    c = cairo.Context(img)
    g = cairo.LinearGradient(0, 1290, 0, 1400)          # fade into a solid band so burned-in text can't clash
    g.add_color_stop_rgba(0, 0.02, 0.02, 0.05, 0)
    g.add_color_stop_rgba(1, 0.02, 0.02, 0.05, 0.96)
    c.rectangle(0, 1290, 1080, 110)
    c.set_source(g)
    c.fill()
    c.rectangle(0, 1400, 1080, 300)
    c.set_source_rgba(0.02, 0.02, 0.05, 0.96)
    c.fill()
    c.select_font_face("Arial", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    for txt, size, y, col in ((l1, 96, 1520, (1, 1, 1)), (l2, 110, 1640, GOLD)):
        c.set_font_size(size)
        while c.text_extents(txt).width > 980:
            size -= 4
            c.set_font_size(size)
        e = c.text_extents(txt)
        x = 540 - e.width / 2 - e.x_bearing
        c.set_source_rgba(0, 0, 0, 0.8)
        c.move_to(x + 5, y + 5)
        c.show_text(txt)
        c.set_source_rgb(*col)
        c.move_to(x, y)
        c.show_text(txt)
    img.write_to_png(str(path))
    tmp.unlink()


def main():
    for sub in ("profile", "highlights", "reel_covers"):
        (OUT / sub).mkdir(parents=True, exist_ok=True)
    profile_spiro(OUT / "profile" / "profile_A_spirograph.png")
    profile_golden(OUT / "profile" / "profile_B_golden_spiral.png")
    for name, kind, col in (("1_math_sounds", "sound", (0.45, 0.85, 1.0)), ("2_illusions", "illusion", GOLD),
                            ("3_physics", "physics", (0.6, 1.0, 0.7)), ("4_famous_numbers", "numbers", GOLD),
                            ("5_math_art", "art", (1.0, 0.6, 0.85))):
        highlight(OUT / "highlights" / f"{name}.png", kind, col)
    for k, (folder, t, l1, l2) in enumerate(REELS, 1):
        reel_cover(folder, t, l1, l2, OUT / "reel_covers" / f"{k}_{folder}.png")
    print("kit ->", OUT)


if __name__ == "__main__":
    sys.exit(main())
