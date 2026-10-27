"""COUNT_INFINITY — long-form 16:9 (~9:50): the stickman climbs an 11-rung ladder of numbers, 1 number per second.

100 (microwave pizza) -> 1,000 (nap) -> million (days and nights) -> billion (a lifetime, + "say it out loud") ->
trillion (from the Ice Age to today) -> computer: quintillion -> all the sand -> all the atoms -> googol (the stars
die) -> googolplex (can't even be written) -> infinity (never) -> recap table.
Brief: ideas/2026-10-23_count_to_infinity_LONGFORM_PROMPT.txt. Every number on screen is checked there.
Audio (original): plucked chord loop whose key changes per level, pops / ticks / dings / whooshes, blip voices.
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

SCENE = "count_infinity"
SR = audio.SR
GOLD = (1.0, 0.82, 0.40)
BLUE = (0.45, 0.80, 1.00)
ORANGE = (1.00, 0.62, 0.35)
GREEN = (0.55, 1.0, 0.55)
RED = (1.0, 0.38, 0.35)
WHITE = (0.97, 0.97, 1.0)
SOFT = (0.80, 0.82, 0.92)
CPS = 21.0                                       # typing speed (chars per second)
YEAR = 365.25 * 86400
SUP = "⁰¹²³⁴⁵⁶⁷⁸⁹"
PC_RATE = 1e9                                    # the computer: 1 billion numbers per second
SAND = 7.5e18                                    # grains of sand on Earth (estimate)
ARMY = SAND * PC_RATE                            # a computer for every grain: numbers per second

CHAPTERS = [("intro", 12), ("c100", 28), ("c1k", 34), ("c1m", 62), ("c1b", 70), ("c1t", 66), ("cpc", 56),
            ("sand", 52), ("atoms", 56), ("googol", 50), ("gplex", 46), ("inf", 34), ("recap", 22)]
T0 = {}
_acc = 0.0
for _k, _d in CHAPTERS:
    T0[_k] = _acc
    _acc += _d
T_END = _acc
ORDER = [k for k, _ in CHAPTERS]

RUNGS = [("100", "1 min 40 s"), ("1,000", "16 min 40 s"), ("MILLION", "11.6 days"), ("BILLION", "31.7 years"),
         ("TRILLION", "31,710 years"), ("QUINTILLION", "31.7 yrs (PC)"), ("ALL SAND", "237 yrs (PC)"),
         ("ALL ATOMS", "10⁴⁴ years"), ("GOOGOL", "10⁶⁴ years"), ("GOOGOLPLEX", "impossible"), ("INFINITY", "never")]
RUNG_OF = {k: i for i, k in enumerate(["c100", "c1k", "c1m", "c1b", "c1t", "cpc", "sand", "atoms", "googol",
                                       "gplex", "inf"])}
TITLES = {"c100": "ONE HUNDRED", "c1k": "ONE THOUSAND", "c1m": "ONE MILLION", "c1b": "ONE BILLION",
          "c1t": "ONE TRILLION", "cpc": "THE COMPUTER", "sand": "EVERY GRAIN OF SAND",
          "atoms": "EVERY ATOM IN THE UNIVERSE", "googol": "A GOOGOL", "gplex": "A GOOGOLPLEX", "inf": "INFINITY"}
# u_reveal, big line, answer line, small third line
REVEAL = {
    "c100": (22.0, "100", "= 1 min 40 s", ""),
    "c1k": (24.0, "1,000", "= 16 min 40 s", ""),
    "c1m": (43.0, "1,000,000", "= 11 days 13 hours", ""),
    "c1b": (40.0, "1,000,000,000", "= 31.7 years", ""),
    "c1t": (52.0, "1,000,000,000,000", "= 31,710 years", ""),
    "cpc": (42.0, "1 QUINTILLION", "= 31.7 years", "with a computer counting 1 billion per second"),
    "sand": (38.0, "ALL THE SAND ON EARTH", "≈ 237 years", "with the computer"),
    "atoms": (42.0, "ALL THE ATOMS", "≈ 4 × 10⁴⁴ years", "with a computer for every grain of sand"),
    "googol": (33.0, "A GOOGOL", "≈ 4 × 10⁶⁴ years", "with a computer for every grain of sand"),
    "gplex": (33.0, "A GOOGOLPLEX", "can't even be WRITTEN", "it has more zeros than the universe has atoms"),
    "inf": (19.0, "INFINITY", "= never", "there is always one more"),
}
CARD_HOLD, CARD_FLY = 4.2, 0.6

# speech: chapter, u0, u1, who, text
_L = [
    ("intro", 0.0, 2.8, "A", "1… 2… 3…"),
    ("intro", 3.0, 5.6, "B", "How long until you reach INFINITY?"),
    ("intro", 5.8, 7.4, "A", "Let's find out!"),
    ("c100", 2.0, 3.8, "B", "Warm-up: 100."),
    ("c100", 4.0, 5.9, "B", "I'll heat a pizza. 1 min 40 s."),
    ("c100", 23.0, 24.8, "B", "Pizza's ready!"),
    ("c100", 25.0, 26.9, "A", "Too easy. NEXT!"),
    ("c1k", 2.0, 3.5, "B", "Now 1,000."),
    ("c1k", 3.7, 4.9, "A", "Easy!"),
    ("c1k", 8.4, 9.8, "B", "*yaaawn*"),
    ("c1k", 29.4, 31.1, "B", "…did I miss it?"),
    ("c1k", 31.3, 33.3, "A", "Just one nap."),
    ("c1m", 2.0, 3.6, "B", "One MILLION."),
    ("c1m", 3.8, 5.0, "A", "No sleep?"),
    ("c1m", 5.2, 6.6, "B", "No sleep."),
    ("c1m", 49.0, 51.2, "A", "…can I sleep now?"),
    ("c1m", 51.5, 52.7, "B", "No."),
    ("c1m", 53.4, 55.8, "B", "Next: one BILLION."),
    ("c1b", 2.0, 3.6, "B", "One BILLION."),
    ("c1b", 3.8, 5.6, "A", "How long can it take?"),
    ("c1b", 44.5, 46.6, "B", "It took you 31 years."),
    ("c1b", 46.9, 48.5, "A", "Worth it."),
    ("c1b", 49.0, 51.8, "B", "And you cheated. Say THIS in 1 second:"),
    ("c1b", 52.0, 58.8, "A", "seven hundred seventy-seven million, seven hundred seventy-seven thousand, "
                             "seven hundred seventy-seven"),
    ("c1b", 59.4, 61.8, "A", "OK… let's pretend it's 1 second."),
    ("c1t", 2.0, 3.6, "B", "One TRILLION."),
    ("c1t", 3.8, 5.6, "A", "A thousand billions?!"),
    ("c1t", 5.8, 8.6, "B", "Imagine you started in the ICE AGE."),
    ("c1t", 56.8, 58.6, "A", "My throat…"),
    ("c1t", 59.0, 61.0, "B", "I have an idea."),
    ("cpc", 2.6, 5.4, "B", "This computer counts 1 BILLION per second."),
    ("cpc", 5.6, 6.9, "A", "Show off."),
    ("cpc", 15.0, 17.8, "B", "So: 1 QUINTILLION. 18 zeros."),
    ("cpc", 18.4, 20.4, "A", "Wake me up when it's done."),
    ("cpc", 43.0, 44.6, "A", "…done yet?"),
    ("cpc", 46.6, 48.4, "B", "By hand?"),
    ("cpc", 48.7, 51.6, "A", "Twice the age of the universe."),
    ("sand", 2.0, 4.6, "B", "Every grain of sand on every beach."),
    ("sand", 4.8, 6.0, "A", "How many?!"),
    ("sand", 6.2, 8.8, "B", "About 7.5 QUINTILLION."),
    ("sand", 43.0, 45.8, "B", "By hand: 237 BILLION years."),
    ("sand", 46.1, 47.6, "A", "…pass."),
    ("atoms", 2.0, 4.8, "B", "Every ATOM in the universe: about 10⁸⁰."),
    ("atoms", 5.0, 7.8, "A", "Then I want a computer for EVERY grain of sand."),
    ("atoms", 47.0, 49.6, "A", "Older than the universe… by a lot."),
    ("googol", 2.0, 4.6, "B", "A GOOGOL: 1 with 100 zeros."),
    ("googol", 4.8, 6.6, "A", "Same computers. GO!"),
    ("googol", 38.0, 40.0, "B", "Hello? Anybody?"),
    ("googol", 40.4, 42.4, "A", "…it got really dark."),
    ("gplex", 2.0, 4.8, "B", "GOOGOLPLEX: 1 with a GOOGOL zeros."),
    ("gplex", 5.0, 7.0, "A", "I'll just write it down."),
    ("gplex", 38.0, 40.0, "A", "I need more atoms."),
    ("inf", 2.0, 3.6, "B", "And infinity?"),
    ("inf", 3.8, 5.6, "A", "Faster! FASTER!"),
    ("inf", 11.0, 13.8, "B", "Whatever you reach, there's always +1."),
    ("inf", 14.2, 15.6, "A", "So… never?"),
    ("inf", 15.9, 17.0, "B", "Never."),
    ("inf", 25.0, 27.6, "A", "Then I'll keep counting!"),
    ("recap", 2.0, 3.6, "A", "1… 2… 3…"),
]
LINES = [(T0[ch] + a, T0[ch] + b, who, txt) for ch, a, b, who, txt in _L]


def clamp(v, a=0.0, b=1.0):
    return max(a, min(b, v))


def seg(u, a, b):
    return clamp((u - a) / (b - a))


def ease(u, a, b):
    return smooth(seg(u, a, b))


def sup(n):
    s = str(int(n))
    return "".join(SUP[int(d)] for d in s)


def fmt_log(L):
    """10^L as text: '1.3 × 10⁵²'."""
    e = math.floor(L + 1e-9)
    m = 10 ** (L - e)
    if m >= 9.95:
        m, e = 1.0, e + 1
    return f"10{sup(e)}" if m < 1.05 else f"{m:.1f} × 10{sup(e)}"


def fmt_n(n):
    if n < 1e16:
        return f"{int(n):,}"
    return fmt_log(math.log10(n))


def fmt_time(s):
    if s < 60:
        return f"{int(s)} s"
    if s < 3600:
        m, r = divmod(int(s), 60)
        return f"{m} min {r} s"
    if s < 86400:
        hh, r = divmod(int(s), 3600)
        return f"{hh} h {r // 60} min"
    d = s / 86400
    if d < 365.25:
        dd = int(d)
        return f"{dd} day{'s' if dd != 1 else ''} {int((d - dd) * 24)} h"
    return fmt_years(s / YEAR)


def fmt_years(y):
    if y < 100:
        return f"{y:.1f} years"
    if y < 1e6:
        return f"{y:,.0f} years"
    if y < 1e9:
        return f"{y / 1e6:,.0f} million years"
    if y < 1e12:
        return f"{y / 1e9:,.0f} billion years"
    return fmt_log(math.log10(y)) + " years"


def fmt_log_years(Ly):
    if Ly < 12:
        return fmt_years(10 ** Ly)
    return fmt_log(Ly) + " years"


# ---------------------------------------------------------------- drawing helpers
def stick(c, x, gy, H, col, arm_l=(0.35, 0.2), arm_r=(0.35, 0.2), walk=0.0, mouth="smile", eyes="open",
          beard=0.0, hair=0.0, cane=0.0, lie=0.0, look=0.0, dizzy=0.0, t=0.0, alpha=1.0):
    """Stick figure standing on ground y=gy (feet). lie 0..1 rotates it down onto the ground (head to the left)."""
    ctx = c.ctx
    ctx.save()
    if lie > 0:
        ctx.translate(x, gy - 0.05 * H * lie)
        ctx.rotate(-lie * math.pi / 2)
        ctx.translate(-x, -gy)
    lw = H * 0.045
    hip = (x, gy - 0.45 * H)
    sh = (x, gy - 0.76 * H)
    hc = (x, gy - 0.90 * H)
    hr = 0.115 * H
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)

    def ln(p, q, w=lw, cc=col, a=alpha):
        ctx.move_to(*p)
        ctx.line_to(*q)
        ctx.set_source_rgba(*cc, a)
        ctx.set_line_width(w)
        ctx.stroke()

    ln(hip, sh)
    hands = {}
    for side, (a1, a2) in ((-1, arm_l), (1, arm_r)):
        e = (sh[0] + side * math.sin(a1) * 0.26 * H, sh[1] + math.cos(a1) * 0.26 * H)
        hnd = (e[0] + side * math.sin(a1 + a2) * 0.24 * H, e[1] + math.cos(a1 + a2) * 0.24 * H)
        ln(sh, e)
        ln(e, hnd)
        hands[side] = hnd
    for side in (-1, 1):
        ph = math.sin(walk * 2 * math.pi + (0 if side < 0 else math.pi))
        a = side * 0.22 + 0.45 * ph * (1 if walk else 0)
        k = (hip[0] + math.sin(a) * 0.24 * H, hip[1] + math.cos(a) * 0.24 * H)
        f = (k[0] + math.sin(a * 0.5) * 0.22 * H, gy)
        ln(hip, k)
        ln(k, f)
    if cane > 0:
        hx, hy = hands[1]
        ln((hx, hy), (hx + H * 0.05, gy), w=lw * 0.8, cc=(0.75, 0.6, 0.45), a=alpha * cane)
        ln((hx - H * 0.05, hy), (hx + H * 0.02, hy - H * 0.02), w=lw * 0.8, cc=(0.75, 0.6, 0.45), a=alpha * cane)
    ctx.new_path()
    ctx.arc(hc[0], hc[1], hr, 0, 2 * math.pi)
    ctx.set_source_rgba(0.05, 0.05, 0.09, alpha)
    ctx.fill_preserve()
    ctx.set_source_rgba(*col, alpha)
    ctx.set_line_width(lw)
    ctx.stroke()
    if hair > 0:
        ctx.new_path()
        ctx.arc(hc[0], hc[1], hr * 1.08, math.pi * 1.08, math.pi * 1.92)
        ctx.set_source_rgba(0.93, 0.93, 0.97, alpha * hair)
        ctx.set_line_width(lw * 1.5)
        ctx.stroke()
    ex = hr * 0.38
    for s_ in (-1, 1):
        exx, eyy = hc[0] + s_ * ex + look * hr * 0.25, hc[1] - hr * 0.15
        if eyes == "closed":
            ctx.new_path()
            ctx.arc(exx, eyy - hr * 0.05, hr * 0.13, 0.15 * math.pi, 0.85 * math.pi)
            ctx.set_source_rgba(1, 1, 1, alpha)
            ctx.set_line_width(lw * 0.45)
            ctx.stroke()
        elif eyes == "tired":
            ctx.new_path()
            ctx.arc(exx, eyy + hr * 0.02, hr * 0.09, 0, math.pi)
            ctx.set_source_rgba(1, 1, 1, alpha)
            ctx.fill()
            ln((exx - hr * 0.14, eyy - hr * 0.02), (exx + hr * 0.14, eyy - hr * 0.02), w=lw * 0.4, cc=(1, 1, 1))
        else:
            ctx.new_path()
            ctx.arc(exx, eyy, hr * 0.11, 0, 2 * math.pi)
            ctx.set_source_rgba(1, 1, 1, alpha)
            ctx.fill()
    if beard > 0:
        bl = hr * (0.35 + 2.4 * beard)
        ctx.new_path()
        ctx.move_to(hc[0] - hr * 0.75, hc[1] + hr * 0.25)
        ctx.curve_to(hc[0] - hr * 0.7, hc[1] + hr * 0.6 + bl * 0.4, hc[0] - hr * 0.3, hc[1] + bl, hc[0],
                     hc[1] + hr * 0.55 + bl)
        ctx.curve_to(hc[0] + hr * 0.3, hc[1] + bl, hc[0] + hr * 0.7, hc[1] + hr * 0.6 + bl * 0.4,
                     hc[0] + hr * 0.75, hc[1] + hr * 0.25)
        ctx.close_path()
        ctx.set_source_rgba(0.88, 0.88, 0.93, alpha * clamp(beard * 4))
        ctx.fill()
    mx, my = hc[0] + look * hr * 0.2, hc[1] + hr * 0.38
    ctx.new_path()
    mcol = (0.1, 0.1, 0.14) if beard > 0.15 else (1, 1, 1)
    ctx.set_source_rgba(*mcol, alpha)
    ctx.set_line_width(lw * 0.7)
    if mouth == "smile":
        ctx.arc(mx, my - hr * 0.25, hr * 0.35, 0.25 * math.pi, 0.75 * math.pi)
        ctx.stroke()
    elif mouth == "sad":
        ctx.arc(mx, my + hr * 0.2, hr * 0.32, 1.2 * math.pi, 1.8 * math.pi)
        ctx.stroke()
    elif mouth == "open":
        ctx.arc(mx, my, hr * 0.17, 0, 2 * math.pi)
        ctx.fill()
    else:
        ctx.move_to(mx - hr * 0.25, my)
        ctx.line_to(mx + hr * 0.25, my)
        ctx.stroke()
    if dizzy > 0:
        for j in range(3):
            a = 2 * math.pi * (t * 1.2 + j / 3)
            sx, sy = hc[0] + hr * 1.5 * math.cos(a), hc[1] - hr * 1.2 + hr * 0.35 * math.sin(a)
            c.text_centered("*", sy + hr * 0.3, size=hr * 0.9, color=GOLD, alpha=dizzy * alpha, cx=sx)
    ctx.restore()
    return hands


def wrap(ctx, text, maxw):
    words, lines, cur = text.split(), [], ""
    for wd in words:
        t = (cur + " " + wd).strip()
        if ctx.text_extents(t).x_advance <= maxw or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = wd
    if cur:
        lines.append(cur)
    return lines


def bubble(c, ax, ay, text, shown, col, maxw, fs, w):
    """Speech bubble whose tail points at (ax, ay); typewriter: first `shown` chars."""
    ctx = c.ctx
    ctx.select_font_face("Arial", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    ctx.set_font_size(fs)
    lines = wrap(ctx, text, maxw)
    bw = max(ctx.text_extents(ln).x_advance for ln in lines) + fs * 1.2
    bh = len(lines) * fs * 1.25 + fs * 0.8
    bx = min(max(ax - bw / 2, w * 0.02), w * 0.98 - bw)
    by = ay - fs * 0.9 - bh
    r = fs * 0.6
    ctx.new_path()
    ctx.arc(bx + bw - r, by + r, r, -math.pi / 2, 0)
    ctx.arc(bx + bw - r, by + bh - r, r, 0, math.pi / 2)
    ctx.line_to(min(max(ax + fs * 0.4, bx + r), bx + bw - r), by + bh)
    ctx.line_to(ax, ay - fs * 0.15)
    ctx.line_to(min(max(ax - fs * 0.4, bx + r), bx + bw - r), by + bh)
    ctx.arc(bx + r, by + bh - r, r, math.pi / 2, math.pi)
    ctx.arc(bx + r, by + r, r, math.pi, 1.5 * math.pi)
    ctx.close_path()
    ctx.set_source_rgba(0.97, 0.97, 1.0, 0.97)
    ctx.fill_preserve()
    ctx.set_source_rgb(*col)
    ctx.set_line_width(fs * 0.12)
    ctx.stroke()
    left = shown
    for i, ln in enumerate(lines):
        part = ln[:max(0, left)]
        left -= len(ln) + 1
        ctx.move_to(bx + fs * 0.6, by + fs * 0.4 + (i + 1) * fs * 1.25 - fs * 0.25)
        ctx.set_source_rgb(0.08, 0.08, 0.12)
        ctx.show_text(part)


def text_left(c, s, x, y, size, col, alpha=1.0, bold=True):
    ctx = c.ctx
    ctx.select_font_face("Arial", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD if bold else cairo.FONT_WEIGHT_NORMAL)
    ctx.set_font_size(size)
    ctx.move_to(x, y)
    ctx.set_source_rgba(*col, alpha)
    ctx.show_text(s)


def rrect(ctx, x, y, w, h, r):
    ctx.new_path()
    ctx.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    ctx.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    ctx.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    ctx.arc(x + r, y + r, r, math.pi, 1.5 * math.pi)
    ctx.close_path()


def fill(ctx, col, a=1.0):
    ctx.set_source_rgba(*col, a)
    ctx.fill()


def mix(a, b, u):
    return tuple(a[i] + (b[i] - a[i]) * u for i in range(3))


# ---------------------------------------------------------------- the history (trillion) timeline
T_START_YEAR = 2026 - 31710                     # 29,684 BC


def c1t_frac(u):
    """fraction of the trillion done at chapter time u (slower at the end, where history happens)."""
    if u < 9.0:
        return 0.0
    if u < 40.0:
        return 0.85 * (u - 9.0) / 31.0
    if u < 52.0:
        return 0.85 + 0.15 * (u - 40.0) / 12.0
    return 1.0


def c1t_year(u):
    return T_START_YEAR + 31710 * c1t_frac(u)


ERAS = [("ice", -1e9, -10000), ("farm", -10000, -3000), ("pyr", -3000, -500), ("rome", -500, 500),
        ("castle", 500, 1850), ("city", 1850, 1e9)]


def year_str(y):
    y = int(round(y))
    return f"{-y:,} BC" if y <= 0 else (f"{y} AD" if y < 1000 else f"{y}")


# ---------------------------------------------------------------- layout of space props (deterministic)
_rng = np.random.default_rng(7)
STARS = [(float(_rng.random()), float(_rng.random()), float(_rng.random())) for _ in range(260)]
WEB = [(float(_rng.normal()), float(_rng.normal())) for _ in range(160)]
GAL_DOTS = [(float(_rng.random()), float(_rng.normal() * 0.08)) for _ in range(700)]


def simulate():
    return {"nf": int(round(T_END * FPS))}


class Scene:
    def __init__(self, layout, sim):
        self.L, self.sim = layout, sim
        self.canvas = Canvas(layout.w, layout.h, studio.render_scale())

    # ------------------------------------------------------------- common pieces
    def stars(self, t, alpha=1.0, top=0.0, bottom=1.0):
        c, w, h = self.canvas, self.L.w, self.L.h
        for i, (sx, sy, sz) in enumerate(STARS):
            y = h * (top + (bottom - top) * sy)
            tw = 0.55 + 0.45 * math.sin(t * (0.8 + sz) + i)
            c.circle(w * sx, y, 1.2 + 1.8 * sz, (1, 1, 1), alpha=alpha * (0.25 + 0.5 * tw) * (0.5 + 0.5 * sz))

    def sky_bg(self, top, bot):
        c, h = self.canvas, self.L.h
        g = cairo.LinearGradient(0, 0, 0, h)
        g.add_color_stop_rgb(0, *top)
        g.add_color_stop_rgb(1, *bot)
        c.ctx.set_source(g)
        c.ctx.paint()

    def ground(self, col=(0.75, 0.78, 0.9), alpha=0.5, floor=(0.03, 0.03, 0.06)):
        c, w, h = self.canvas, self.L.w, self.L.h
        c.ctx.rectangle(0, self.gy, w, h - self.gy)
        fill(c.ctx, floor, 0.85)
        c.lines([(0, self.gy, w, self.gy)], col, width=4, alpha=alpha)

    def room(self, wall=(0.10, 0.10, 0.18)):
        c, w, h = self.canvas, self.L.w, self.L.h
        self.sky_bg(wall, mix(wall, (0, 0, 0), 0.55))
        ctx = c.ctx
        for k in range(9):                                     # faint wall panels
            x = w * (0.04 + k * 0.115)
            c.lines([(x, h * 0.27, x, self.gy - h * 0.03)], (0.5, 0.55, 0.9), width=2, alpha=0.06)
        c.lines([(0, self.gy - h * 0.025, w, self.gy - h * 0.025)], (0.55, 0.6, 1.0), width=3, alpha=0.18)
        ctx.rectangle(0, self.gy, w, h - self.gy)
        fill(ctx, (0.05, 0.045, 0.08))
        c.lines([(0, self.gy, w, self.gy)], (0.75, 0.78, 0.9), width=4, alpha=0.5)

    def window(self, x0, y0, x1, y1, top, bot, draw_inside=None):
        c = self.canvas
        ctx = c.ctx
        ctx.save()
        ctx.rectangle(x0, y0, x1 - x0, y1 - y0)
        ctx.clip()
        g = cairo.LinearGradient(0, y0, 0, y1)
        g.add_color_stop_rgb(0, *top)
        g.add_color_stop_rgb(1, *bot)
        ctx.set_source(g)
        ctx.paint()
        if draw_inside:
            draw_inside()
        ctx.restore()
        fr = (0.55, 0.6, 0.85)
        c.lines([(x0, y0, x1, y0), (x1, y0, x1, y1), (x1, y1, x0, y1), (x0, y1, x0, y0),
                 ((x0 + x1) / 2, y0, (x0 + x1) / 2, y1), (x0, (y0 + y1) / 2, x1, (y0 + y1) / 2)], fr, width=6,
                alpha=0.9)
        c.lines([(x0 - 12, y1 + 6, x1 + 12, y1 + 6)], fr, width=10, alpha=0.9)

    def computer(self, x, gy, s, u, dust=0.0, label=True, lit=1.0, count=None):
        """a fridge-sized cabinet with blinking lights; its screen shows the count it has reached."""
        c = self.canvas
        ctx = c.ctx
        cw, ch = s * 0.62, s
        x0, y0 = x - cw / 2, gy - ch
        rrect(ctx, x0, y0, cw, ch, s * 0.04)
        fill(ctx, (0.13, 0.14, 0.22))
        rrect(ctx, x0, y0, cw, ch, s * 0.04)
        ctx.set_source_rgba(0.45, 0.8, 1.0, 0.8 * lit)
        ctx.set_line_width(3)
        ctx.stroke()
        sx0, sy0, sw, sh = x0 + cw * 0.08, y0 + ch * 0.07, cw * 0.84, ch * 0.22
        ctx.rectangle(sx0, sy0, sw, sh)
        fill(ctx, (0.02, 0.06, 0.08))
        c.glow(x, sy0 + sh / 2, sw * 0.4, (0.3, 1.0, 0.6), strength=0.25 * lit, reach=1.6)
        if count is not None:
            c.text_centered("count =", sy0 + sh * 0.32, size=sh * 0.2, color=(0.4, 0.8, 0.55), alpha=lit, cx=x,
                            bold=False)
            c.text_centered(count, sy0 + sh * 0.78, size=sh * 0.36, color=(0.4, 1.0, 0.6), alpha=lit, cx=x,
                            max_w=sw * 0.92)
        for r in range(7):
            for q in range(6):
                on = ((r * 5 + q * 3 + int(u * 6 + r * q)) % 4) != 0
                col = (0.3, 1.0, 0.5) if (r + q) % 3 else (1.0, 0.7, 0.3)
                c.circle(x0 + cw * (0.17 + q * 0.133), y0 + ch * (0.38 + r * 0.075), s * 0.012, col,
                         alpha=(0.95 if on else 0.15) * lit)
        if label:
            c.text_centered("COMPUTER", y0 - s * 0.15, size=s * 0.1, color=WHITE, alpha=0.95, cx=x)
            c.text_centered("counts 1 BILLION numbers every second", y0 - s * 0.06, size=s * 0.07, color=GOLD,
                            alpha=0.95, cx=x, max_w=s * 1.6)
        if count is not None and lit > 0.5 and dust < 0.9:      # a billion more every half second, rising off the screen
            for k in range(2):
                ph = (u * 2.0 + k / 2) % 1.0
                c.text_centered("+1,000,000,000", sy0 + sh * 0.5 - ph * s * 0.12, size=s * 0.06, color=(0.4, 1.0, 0.6),
                                alpha=0.9 * (1 - ph) * min(1.0, ph * 5), cx=x + cw * 0.95, max_w=s)
        if dust > 0:
            ctx.rectangle(x0, y0, cw, ch)
            fill(ctx, (0.45, 0.42, 0.38), 0.35 * dust)
            for j in range(5):                                 # cobweb in the corner
                a = j / 4 * math.pi / 2
                c.lines([(x0 + cw, y0, x0 + cw - math.cos(a) * s * 0.3 * dust, y0 + math.sin(a) * s * 0.3 * dust)],
                        (0.85, 0.85, 0.9), width=1.5, alpha=0.6 * dust)
            for rr in (0.1, 0.18, 0.26):
                ctx.new_path()
                ctx.arc(x0 + cw, y0, s * rr * dust, math.pi / 2, math.pi)
                ctx.set_source_rgba(0.85, 0.85, 0.9, 0.5 * dust)
                ctx.set_line_width(1.2)
                ctx.stroke()

    def clock(self, x, y, r, secs):
        c = self.canvas
        c.circle(x, y, r * 1.08, (0.55, 0.6, 0.85), alpha=0.9)
        c.circle(x, y, r, (0.08, 0.08, 0.13))
        for k in range(12):
            a = k / 12 * 2 * math.pi
            c.lines([(x + math.sin(a) * r * 0.82, y - math.cos(a) * r * 0.82, x + math.sin(a) * r * 0.94,
                      y - math.cos(a) * r * 0.94)], WHITE, width=3, alpha=0.8)
        T = 3 * 3600 + secs                                    # starts at 3:00
        for frac, ln, wd, col in ((T / 43200, 0.5, 7, WHITE), (T / 3600, 0.75, 5, WHITE), (T / 60, 0.85, 2.5, RED)):
            a = frac * 2 * math.pi
            c.lines([(x, y, x + math.sin(a) * r * ln, y - math.cos(a) * r * ln)], col, width=wd)
        c.circle(x, y, r * 0.06, GOLD)

    # ------------------------------------------------------------- figures + speech
    def figs(self, t, A=None, B=None, kid=None):
        """A / B: dicts of stick() kwargs plus x; None = not drawn. Talking mouths come from LINES."""
        c, gy, H = self.canvas, self.gy, self.H
        self.pos = {}
        for who, d, col in (("A", A, BLUE), ("B", B, ORANGE)):
            if d is None:
                continue
            d = dict(d)
            x = d.pop("x")
            talking = any(t0 <= t < t1 and wh == who and (t - t0) * CPS < len(tx) for t0, t1, wh, tx in LINES)
            if talking and d.get("lie", 0) < 0.5:
                d["mouth"] = "open" if int(t * 9) % 2 else d.get("mouth", "smile")
            hh = d.pop("H", H)
            counting = d.pop("counting", False)
            stick(c, x, gy, hh, col, t=t, **d)
            self.pos[who] = (x, gy - hh * 1.05)
            if counting:
                self.plus_ones(t, x, gy - hh * 1.02, hh)
        if kid is not None:
            d = dict(kid)
            x = d.pop("x")
            stick(c, x, gy, d.pop("H"), GREEN, t=t, **d)

    def plus_ones(self, t, x, y, hh):
        """counting, shown calmly: small '+1's rise from the head and fade, 3 per second."""
        c = self.canvas
        for k in range(3):
            ph = (t * 1.0 + k / 3) % 1.0
            c.text_centered("+1", y - ph * hh * 0.55, size=hh * (0.15 + 0.04 * (1 - ph)), color=GOLD,
                            alpha=0.9 * (1 - ph) * min(1.0, ph * 6), cx=x + hh * (0.18 + 0.08 * math.sin(k * 2.1)))

    def say(self, t):
        c, w, h = self.canvas, self.L.w, self.L.h
        for t0, t1, who, text in LINES:
            if t0 <= t < t1 and who in self.pos:
                shown = int((t - t0) * CPS)
                hx, hy = self.pos[who]
                long_ = len(text) > 60
                bubble(c, hx, hy, text, shown, BLUE if who == "A" else ORANGE, w * (0.42 if long_ else 0.30),
                       h * 0.036, w)

    # ------------------------------------------------------------- HUD
    def ladder(self, t, ch, u):
        c, w, h = self.canvas, self.L.w, self.L.h
        ctx = c.ctx
        if ch == "recap":
            return
        if ch == "intro":
            if u < 7.4:
                return
            shown_n = int((u - 7.4) / 0.25) + 1
        else:
            shown_n = 11
        cur = RUNG_OF.get(ch, 99)
        n = len(RUNGS)
        x0, x1 = w * 0.025, w * 0.975
        pw = (x1 - x0) / n
        y = h * 0.045
        for i, (name, res) in enumerate(RUNGS):
            if i >= shown_n:
                break
            cx = x0 + pw * (i + 0.5)
            k = ORDER[i + 1]
            ur, *_ = REVEAL[k]
            done_t = T0[k] + ur + CARD_HOLD + CARD_FLY
            done = t >= done_t
            is_cur = i == cur and not done
            pop = 1.0
            if ch == "intro":
                pop = 1 + 0.4 * math.exp(-(u - 7.4 - i * 0.25) / 0.08) if u >= 7.4 + i * 0.25 else 1
            rrect(ctx, cx - pw * 0.46, y - h * 0.028, pw * 0.92, h * 0.056, h * 0.012)
            if done:
                fill(ctx, (0.25, 0.2, 0.06), 0.9)
            elif is_cur:
                fill(ctx, (0.12, 0.16, 0.3), 0.95)
            else:
                fill(ctx, (0.08, 0.08, 0.13), 0.85)
            rrect(ctx, cx - pw * 0.46, y - h * 0.028, pw * 0.92, h * 0.056, h * 0.012)
            if is_cur:
                pul = 0.6 + 0.4 * math.sin(t * 5)
                ctx.set_source_rgba(*BLUE, pul)
                ctx.set_line_width(3)
            else:
                ctx.set_source_rgba(*(GOLD if done else (0.4, 0.42, 0.55)), 0.9)
                ctx.set_line_width(2)
            ctx.stroke()
            col = GOLD if done else (WHITE if is_cur else (0.62, 0.64, 0.74))
            c.text_centered(name, y + h * 0.009, size=h * 0.021 * pop, color=col, cx=cx, max_w=pw * 0.86)
            if done:
                fl = math.exp(-(t - done_t) / 0.25)
                c.text_centered(res, y + h * 0.060, size=h * 0.022 * (1 + 0.5 * fl), color=GOLD, cx=cx,
                                max_w=pw * 0.95, bold=False)
            else:
                c.text_centered("?", y + h * 0.058, size=h * 0.02, color=(0.55, 0.57, 0.68), cx=cx, bold=False)

    def counter(self, cnt):
        if not cnt:
            return
        c, w, h = self.canvas, self.L.w, self.L.h
        if cnt.get("label"):
            c.text_centered(cnt["label"], h * 0.145, size=h * 0.026, color=GOLD, max_w=w * 0.7)
        if cnt.get("big") is not None:
            s = cnt["big"]
            sz = 0.13 if s == "∞" else (0.072 if len(s) < 16 else 0.06)
            c.text_centered(s, h * (0.235 if s == "∞" else 0.225), size=h * sz, color=WHITE, max_w=w * 0.62)
        if cnt.get("sub"):
            c.text_centered(cnt["sub"], h * 0.268, size=h * 0.026, color=SOFT, bold=False, max_w=w * 0.62)
        if cnt.get("ff"):
            a = 0.55 + 0.45 * math.sin(self.t * 6)
            x0, y0, s_ = w * 0.80, h * 0.214, h * 0.03
            for k in range(2):
                c.poly([(x0 + k * s_ * 0.8, y0 - s_ * 0.5), (x0 + k * s_ * 0.8 + s_ * 0.8, y0),
                        (x0 + k * s_ * 0.8, y0 + s_ * 0.5)], WHITE, alpha=a)
            text_left(c, cnt["ff"], x0 + s_ * 2.0, y0 + s_ * 0.36, s_, WHITE, alpha=a)

    def bottom(self, s, t_on, t, col=WHITE, size=0.034):
        c, w, h = self.canvas, self.L.w, self.L.h
        a = clamp((t - t_on) / 0.3)
        ctx = c.ctx
        ctx.select_font_face("Arial", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        ctx.set_font_size(h * size)
        tw = min(w * 0.9, ctx.text_extents(s).x_advance)
        rrect(ctx, w / 2 - tw / 2 - h * 0.02, h * 0.95 - h * size * 1.05, tw + h * 0.04, h * size * 1.55, h * 0.012)
        fill(ctx, (0.02, 0.02, 0.05), 0.55 * a)
        c.text_centered(s, h * 0.95, size=h * size, color=col, alpha=a, max_w=w * 0.9)

    def title_card(self, ch, u):
        if ch not in TITLES or u > 2.2:
            return
        c, w, h = self.canvas, self.L.w, self.L.h
        a = clamp(u / 0.25) * clamp((2.2 - u) / 0.35)
        c.glow(w / 2, h * 0.42, w * 0.18, (0.3, 0.4, 1.0), strength=0.25 * a, reach=1.6)
        c.text_centered(f"LEVEL {RUNG_OF[ch] + 1}", h * 0.36, size=h * 0.035, color=GOLD, alpha=a)
        c.text_centered(TITLES[ch], h * 0.45, size=h * 0.08 * (1 + 0.08 * (1 - clamp(u / 0.4))), color=WHITE,
                        alpha=a, max_w=w * 0.8)

    def reveal(self, ch, u):
        if ch not in REVEAL:
            return
        ur, big, ans, small = REVEAL[ch]
        if not (ur <= u < ur + CARD_HOLD + CARD_FLY):
            return
        c, w, h = self.canvas, self.L.w, self.L.h
        ctx = c.ctx
        k = u - ur
        pop = 1 + 0.25 * math.exp(-k / 0.12) * math.cos(k * 25)
        if k < CARD_HOLD:
            s, cx, cy, a = pop, w / 2, h * 0.43, 1.0
        else:
            f = smooth((k - CARD_HOLD) / CARD_FLY)
            i = RUNG_OF[ch]
            pw = w * 0.95 / 11
            tx = w * 0.025 + pw * (i + 0.5)
            s = 1 - 0.85 * f
            cx, cy, a = w / 2 + (tx - w / 2) * f, h * 0.43 + (h * 0.07 - h * 0.43) * f, 1 - 0.6 * f
        bw, bh = w * 0.56 * s, h * (0.25 if small else 0.21) * s
        c.glow(cx, cy, bw * 0.45, GOLD, strength=0.3 * a, reach=1.5)
        rrect(ctx, cx - bw / 2, cy - bh / 2, bw, bh, h * 0.025 * s)
        fill(ctx, (0.06, 0.06, 0.12), 0.94 * a)
        rrect(ctx, cx - bw / 2, cy - bh / 2, bw, bh, h * 0.025 * s)
        ctx.set_source_rgba(*GOLD, a)
        ctx.set_line_width(4 * s)
        ctx.stroke()
        top = cy - bh / 2
        c.text_centered(big, top + bh * (0.33 if small else 0.40), size=h * 0.06 * s, color=WHITE, alpha=a,
                        cx=cx, max_w=bw * 0.9)
        c.text_centered(ans, top + bh * (0.63 if small else 0.78), size=h * 0.07 * s, color=GOLD, alpha=a, cx=cx,
                        max_w=bw * 0.9)
        if small:
            c.text_centered(small, top + bh * 0.86, size=h * 0.026 * s, color=SOFT, alpha=a, cx=cx, max_w=bw * 0.9,
                            bold=False)

    # ------------------------------------------------------------- chapters
    def ch_intro(self, t, u):
        w, h = self.L.w, self.L.h
        self.sky_bg((0.07, 0.07, 0.14), (0.02, 0.02, 0.05))
        self.stars(t, 0.8, 0.0, 0.8)
        self.ground()
        n = int(u) + 1
        tick = u % 1.0
        self.figs(t, A=dict(x=w * 0.30, counting=True),
                  B=dict(x=w * 0.70, look=-0.4))
        c = self.canvas
        a = clamp((7.0 - u) / 0.5)
        if a > 0:
            c.glow(w / 2, h * 0.08, w * 0.25, (0.3, 0.4, 1.0), strength=0.25 * a, reach=1.6)
            c.text_centered("COUNTING TO INFINITY", h * 0.075, size=h * 0.05, color=WHITE, alpha=a)
        if u >= 8.4:
            self.bottom("Rules: 1 number per second  ·  no sleep  ·  no breaks", 8.4, u, col=GOLD)
        return dict(label="COUNTING TO ∞", big=f"{n:,}", sub="1 number per second")

    def ch_c100(self, t, u):
        c, w, h, gy, H = self.canvas, self.L.w, self.L.h, self.gy, self.H
        ctx = c.ctx
        self.room()
        n = 0 if u < 6 else (100 if u >= 22 else 1 + int(99 * (u - 6) / 16))
        counting = 6 <= u < 22
        # table + microwave
        tx, ty = w * 0.5, gy - h * 0.15
        ctx.rectangle(tx - w * 0.12, ty, w * 0.24, h * 0.022)
        fill(ctx, (0.35, 0.28, 0.25))
        c.lines([(tx - w * 0.1, ty, tx - w * 0.1, gy), (tx + w * 0.1, ty, tx + w * 0.1, gy)], (0.35, 0.28, 0.25), width=10)
        mw, mh = w * 0.19, h * 0.17
        mx0, my0 = tx - mw / 2, ty - mh
        rrect(ctx, mx0, my0, mw, mh, h * 0.012)
        fill(ctx, (0.22, 0.23, 0.32))
        wx0, wy0, ww_, wh_ = mx0 + mw * 0.06, my0 + mh * 0.12, mw * 0.62, mh * 0.76
        running = 4.6 <= u < 22
        rrect(ctx, wx0, wy0, ww_, wh_, h * 0.01)
        fill(ctx, (0.75, 0.6, 0.25) if running else (0.05, 0.05, 0.08), 0.55 if running else 1.0)
        if running:
            c.glow(wx0 + ww_ / 2, wy0 + wh_ / 2, ww_ * 0.4, (1.0, 0.75, 0.3), strength=0.35, reach=1.4)
        if u >= 4.0:                                           # the pizza, turning
            px, py, pr = wx0 + ww_ / 2, wy0 + wh_ * 0.62, ww_ * 0.3
            ctx.save()
            ctx.translate(px, py)
            ctx.scale(1, 0.35)
            ctx.arc(0, 0, pr, 0, 2 * math.pi)
            ctx.restore()
            fill(ctx, (0.95, 0.75, 0.35))
            rot = (u - 4.6) * 1.3 if running else 0
            for j in range(5):
                a = rot + j * 1.26
                c.circle(px + math.cos(a) * pr * 0.6, py + math.sin(a) * pr * 0.2, pr * 0.1, (0.85, 0.25, 0.2))
        # timer panel
        rem = 100 if u < 4.6 else max(0, 100 - n)
        txt = "--:--" if u < 4.0 else f"{rem // 60}:{rem % 60:02d}"
        if u >= 22 and int(u * 4) % 2:
            txt = "DING"
        c.text_centered(txt, my0 + mh * 0.32, size=mh * 0.15, color=(0.4, 1.0, 0.6), cx=mx0 + mw * 0.84,
                        max_w=mw * 0.28)
        for r in range(3):
            c.circle(mx0 + mw * 0.84, my0 + mh * (0.5 + r * 0.13), mh * 0.035, (0.5, 0.52, 0.65))
        tk = (u * 99 / 16) % 1.0 if counting else 1.0
        self.figs(t, A=dict(x=w * 0.22, counting=counting,
                            mouth="open" if counting and tk < 0.5 else "smile"),
                  B=dict(x=w * 0.78, look=-0.6, arm_l=(1.2, 0.3) if 4.0 <= u < 5.0 else (0.35, 0.2)))
        if u >= 23:
            self.bottom("100 seconds = exactly one microwave pizza", 23, u, col=GOLD)
        return dict(label="COUNTING TO 100", big=f"{n:,}", sub=fmt_time(n) + " of counting" if n else "0 s",
                    ff="×6" if counting else None)

    def ch_c1k(self, t, u):
        c, w, h, gy, H = self.canvas, self.L.w, self.L.h, self.gy, self.H
        self.room((0.09, 0.10, 0.19))
        n = 0 if u < 5 else (1000 if u >= 24 else 1 + int(999 * (u - 5) / 19))
        counting = 5 <= u < 24
        self.clock(w * 0.5, h * 0.47, h * 0.11, n)
        lie = ease(u, 10.0, 11.0) * (1 - ease(u, 28.4, 29.2))
        tk = (u * 52.6) % 1.0
        self.figs(t, A=dict(x=w * 0.25, counting=counting, mouth="open" if counting and tk < 0.5 else "smile"),
                  B=dict(x=w * 0.80, lie=lie, eyes="closed" if 10.0 <= u < 28.6 else "open",
                         mouth="flat" if 10 <= u < 28.6 else "smile",
                         arm_l=(2.6, 0.6) if 8.4 <= u < 9.8 else (0.35, 0.2), look=-0.4))
        if 11.0 <= u < 28.4:                                   # Zzz
            for j in range(3):
                ph = ((u - 11.0) * 0.6 + j / 3) % 1.0
                c.text_centered("z" if j % 2 else "Z", gy - H * 0.35 - ph * h * 0.18, size=h * (0.03 + 0.03 * ph),
                                color=SOFT, alpha=0.9 * (1 - ph) * clamp((u - 11.0) / 0.5), cx=w * 0.63 + ph * w * 0.05)
        if u >= 26:
            self.bottom("1,000 seconds = 16 minutes 40 seconds: one short nap", 26, u, col=GOLD)
        return dict(label="COUNTING TO 1,000", big=f"{n:,}", sub=fmt_time(n) + " of counting" if n else "0 s",
                    ff="×53" if counting else None)

    def ch_c1m(self, t, u):
        c, w, h, gy, H = self.canvas, self.L.w, self.L.h, self.gy, self.H
        ctx = c.ctx
        self.room((0.09, 0.09, 0.17))
        n = 0 if u < 7 else (1e6 if u >= 43 else 1e6 * (u - 7) / 36)
        secs = n
        days = secs / 86400
        dayf = (days + 0.375) % 1.0                            # starts at 9 am
        sun = math.sin((dayf - 0.25) * 2 * math.pi)            # +1 noon, -1 midnight
        light = clamp(0.5 + 0.9 * sun)
        top = mix((0.02, 0.03, 0.09), (0.30, 0.55, 0.95), light)
        bot = mix((0.05, 0.05, 0.14), (0.75, 0.85, 1.0), light)
        x0, y0, x1, y1 = w * 0.40, h * 0.33, w * 0.60, h * 0.62

        def inside():
            a = (dayf - 0.25) * 2 * math.pi                    # sun / moon arcs
            cx, cy, R = (x0 + x1) / 2, y1 + (y1 - y0) * 0.1, (x1 - x0) * 0.55
            sxp, syp = cx - math.sin(a) * R, cy - math.cos(a) * R * 0.9
            c.glow(sxp, syp, (x1 - x0) * 0.06, (1.0, 0.85, 0.4), strength=0.8, reach=2.0)
            c.circle(sxp, syp, (x1 - x0) * 0.05, (1.0, 0.88, 0.45))
            mxp, myp = cx + math.sin(a) * R, cy + math.cos(a) * R * 0.9
            c.circle(mxp, myp, (x1 - x0) * 0.04, (0.92, 0.92, 1.0))
            for k in range(30):
                sx, sy, sz = STARS[k]
                c.circle(x0 + (x1 - x0) * sx, y0 + (y1 - y0) * sy * 0.8, 1.5, (1, 1, 1), alpha=(1 - light) * 0.8)
            for k in range(7):                                  # city skyline outside
                bx = x0 + (x1 - x0) * k / 7
                bh = (y1 - y0) * (0.15 + 0.1 * ((k * 37) % 5) / 5)
                ctx.rectangle(bx, y1 - bh, (x1 - x0) / 7 - 4, bh)
                fill(ctx, mix((0.05, 0.05, 0.1), (0.25, 0.3, 0.45), light))
        self.window(x0, y0, x1, y1, top, bot, inside)
        boxes = min(16, int(days * 1.3))                       # pizza boxes pile up
        for b in range(boxes):
            by = gy - (b + 1) * h * 0.022
            off = ((b * 13) % 7 - 3) * 2.0
            ctx.rectangle(w * 0.05 + off, by, w * 0.10, h * 0.02)
            fill(ctx, (0.85, 0.65, 0.35) if b % 2 else (0.78, 0.58, 0.3))
            c.lines([(w * 0.05 + off, by, w * 0.15 + off, by)], (0.45, 0.3, 0.15), width=2)
        counting = 7 <= u < 43
        tired = days > 5
        tk = (u * 9) % 1.0
        self.figs(t, A=dict(x=w * 0.28, beard=0.18 * clamp(days / 11.6), eyes="tired" if tired else "open",
                            mouth=("open" if tk < 0.5 else "flat") if counting else ("flat" if tired else "smile"),
                            counting=counting),
                  B=dict(x=w * 0.76, look=-0.4))
        if 9 <= u < 43:
            self.bottom("…day and night, no sleep", 9, u)
        elif u >= 47.5:
            self.bottom("Longer than the no-sleep world record: 11 days (1964)", 47.5, u, col=GOLD)
        sub = "0 s" if not n else (f"DAY {int(days) + 1}  ·  " + fmt_time(secs) + " of counting")
        return dict(label="COUNTING TO 1 MILLION", big=f"{int(n):,}", sub=sub, ff="×27,800" if counting else None)

    def ch_c1b(self, t, u):
        c, w, h, gy, H = self.canvas, self.L.w, self.L.h, self.gy, self.H
        ctx = c.ctx
        self.room((0.10, 0.09, 0.16))
        if u < 6:
            n = 0.0
        elif u < 40:
            n = 1e9 * (u - 6) / 34
        elif u < 63:
            n = 1e9
        else:
            n = 1e9 * (1 - ease(u, 63, 66.5))
        yrs = n / YEAR
        age = clamp(yrs / 31.7)
        x0, y0, x1, y1 = w * 0.42, h * 0.33, w * 0.62, h * 0.62

        def inside():
            gl = y1 - (y1 - y0) * 0.12
            ctx.rectangle(x0, gl, x1 - x0, y1 - gl)
            fill(ctx, (0.15, 0.35, 0.2))
            tx = (x0 + x1) / 2
            th = (y1 - y0) * (0.12 + 0.6 * age)                # the tree grows
            c.lines([(tx, gl, tx, gl - th)], (0.45, 0.3, 0.2), width=4 + 10 * age)
            c.circle(tx, gl - th, (x1 - x0) * (0.06 + 0.22 * age), (0.25, 0.65, 0.35))
            c.circle(tx - (x1 - x0) * 0.1 * age, gl - th * 0.8, (x1 - x0) * (0.04 + 0.14 * age), (0.3, 0.72, 0.4))
        self.window(x0, y0, x1, y1, (0.35, 0.55, 0.9), (0.7, 0.82, 1.0), inside)
        # calendar
        cx0, cy0 = w * 0.08, h * 0.33
        rrect(ctx, cx0, cy0, w * 0.11, h * 0.15, 8)
        fill(ctx, (0.92, 0.92, 0.96))
        ctx.rectangle(cx0, cy0, w * 0.11, h * 0.04)
        fill(ctx, RED)
        c.text_centered("YEAR", cy0 + h * 0.03, size=h * 0.022, color=WHITE, cx=cx0 + w * 0.055)
        c.text_centered(f"{2026 + int(yrs)}", cy0 + h * 0.115, size=h * 0.05, color=(0.1, 0.1, 0.15),
                        cx=cx0 + w * 0.055)
        kid = None
        if yrs > 5 and u < 66.5:
            kh = H * (0.35 + 0.6 * clamp((yrs - 5) / 18))
            kid = dict(x=w * 0.70, H=kh, alpha=clamp((yrs - 5) / 0.8), look=-0.3)
        counting = 6 <= u < 40
        tk = (u * 9) % 1.0
        self.figs(t, A=dict(x=w * 0.30, beard=0.9 * age, hair=age, eyes="tired" if 0.3 < age < 0.99 else "open",
                            mouth=("open" if tk < 0.5 else "flat") if counting else "smile",
                            counting=counting),
                  B=dict(x=w * 0.84, hair=age, cane=clamp((yrs - 18) / 2), look=-0.4), kid=kid)
        if 52.0 <= u < 63:                                     # the stopwatch
            sw_t = min(u, 58.8) - 52.0
            sx, sy, r = w * 0.12, h * 0.68, h * 0.06
            c.circle(sx, sy, r * 1.1, (0.6, 0.65, 0.9))
            c.circle(sx, sy, r, (0.06, 0.06, 0.1))
            a = sw_t / 10 * 2 * math.pi
            c.lines([(sx, sy, sx + math.sin(a) * r * 0.8, sy - math.cos(a) * r * 0.8)], RED, width=4)
            c.text_centered(f"{sw_t * 0.75:.1f} s", sy + r * 1.75, size=h * 0.035, color=WHITE, cx=sx)
        if u >= 63:
            self.bottom("<< REWIND", 63, u, col=SOFT)
        elif u >= 58.0:
            self.bottom("Big numbers take about 5 s to SAY. A real count to a billion: about 150 years.", 58.0, u,
                        col=GOLD, size=0.03)
        elif 8 <= u < 40:
            self.bottom("…and it keeps going", 8, u)
        sub = "0 s" if not n else fmt_time(n) + " of counting"
        return dict(label="COUNTING TO 1 BILLION", big=f"{int(n):,}", sub=sub,
                    ff="×29,400,000" if counting else ("REWIND" if u >= 63 else None))

    def era_alpha(self, y):
        out = {}
        span = 31710 * 0.012
        for name, a, b in ERAS:
            fa = clamp((y - a) / span + 0.5) if a > -1e8 else 1.0
            fb = clamp((b - y) / span + 0.5) if b < 1e8 else 1.0
            out[name] = min(fa, fb)
        return out

    def ch_c1t(self, t, u):
        c, w, h, gy, H = self.canvas, self.L.w, self.L.h, self.gy, self.H
        ctx = c.ctx
        f = c1t_frac(u)
        yr = c1t_year(u)
        ea = self.era_alpha(yr)
        skies = {"ice": ((0.08, 0.14, 0.26), (0.45, 0.6, 0.8)), "farm": ((0.10, 0.18, 0.30), (0.75, 0.6, 0.45)),
                 "pyr": ((0.20, 0.10, 0.25), (0.95, 0.55, 0.30)), "rome": ((0.14, 0.10, 0.28), (0.75, 0.5, 0.6)),
                 "castle": ((0.05, 0.07, 0.20), (0.35, 0.35, 0.6)), "city": ((0.03, 0.03, 0.10), (0.25, 0.12, 0.35))}
        top, bot = (0, 0, 0), (0, 0, 0)
        tot = sum(ea.values()) or 1
        for k, a in ea.items():
            top = tuple(top[i] + skies[k][0][i] * a / tot for i in range(3))
            bot = tuple(bot[i] + skies[k][1][i] * a / tot for i in range(3))
        self.sky_bg(top, mix(bot, (0, 0, 0), 0.2))
        self.stars(t, 0.35, 0.0, 0.45)
        # far mountains
        ctx.new_path()
        ctx.move_to(0, gy)
        for k in range(13):
            ctx.line_to(w * k / 12, gy - h * (0.16 + 0.1 * math.sin(k * 1.7) ** 2))
        ctx.line_to(w, gy)
        ctx.close_path()
        fill(ctx, mix(bot, (0.05, 0.05, 0.1), 0.7))
        if ea["ice"] > 0:
            self.era_ice(t, u, ea["ice"])
        if ea["farm"] > 0:
            self.era_farm(t, ea["farm"])
        if ea["pyr"] > 0:
            self.era_pyr(ea["pyr"])
        if ea["rome"] > 0:
            self.era_rome(ea["rome"])
        if ea["castle"] > 0:
            self.era_castle(t, ea["castle"])
        if ea["city"] > 0:
            self.era_city(t, ea["city"])
        self.ground(floor=mix(bot, (0.02, 0.02, 0.04), 0.8))
        # the timeline bar
        bx0, bx1, by = w * 0.10, w * 0.90, h * 0.895
        c.lines([(bx0, by, bx1, by)], SOFT, width=4, alpha=0.6)
        for i, (yy, lab) in enumerate(((T_START_YEAR, "Ice Age"), (-10000, "farms"), (-2560, "pyramids"),
                                       (100, "Rome"), (1200, "castles"), (2026, "today"))):
            px = bx0 + (bx1 - bx0) * (yy - T_START_YEAR) / 31710
            c.circle(px, by, 6, GOLD)
            dy = -h * 0.016 if i % 2 == 0 else h * 0.032
            dx = {3: -h * 0.03, 5: h * 0.03}.get(i, 0.0)
            c.text_centered(lab, by + dy, size=h * 0.019, color=SOFT, cx=px + dx, bold=False)
        px = bx0 + (bx1 - bx0) * f
        c.glow(px, by, 18, BLUE, strength=0.8, reach=2)
        c.circle(px, by, 9, WHITE)
        counting = 9 <= u < 52
        tk = (u * 9) % 1.0
        self.figs(t, A=dict(x=w * 0.30, mouth=("open" if tk < 0.5 else "flat") if counting else "smile",
                            counting=counting),
                  B=dict(x=w * 0.72, look=-0.4))
        if u >= 56.5:
            self.bottom("Start with the Ice Age cave painters… and you finish TODAY.", 56.5, u, col=GOLD)
        n = 1e12 * f
        sub = (f"YEAR {year_str(yr)}  ·  " + fmt_years(n / YEAR) + " of counting") if u >= 9 else \
            f"start: YEAR {year_str(T_START_YEAR)}"
        return dict(label="COUNTING TO 1 TRILLION", big=f"{int(n):,}", sub=sub, ff="FAST" if counting else None)

    def era_ice(self, t, u, a):
        c, w, h, gy = self.canvas, self.L.w, self.L.h, self.gy
        ctx = c.ctx
        for k, (mx, mh) in enumerate(((0.12, 0.3), (0.55, 0.36), (0.88, 0.28))):   # snowy peaks
            ctx.new_path()
            ctx.move_to(w * (mx - 0.14), gy - h * 0.05)
            ctx.line_to(w * mx, gy - h * mh)
            ctx.line_to(w * (mx + 0.14), gy - h * 0.05)
            ctx.close_path()
            fill(ctx, (0.35, 0.42, 0.58), a)
            ctx.new_path()
            ctx.move_to(w * (mx - 0.045), gy - h * (mh - 0.1))
            ctx.line_to(w * mx, gy - h * mh)
            ctx.line_to(w * (mx + 0.045), gy - h * (mh - 0.1))
            ctx.close_path()
            fill(ctx, (0.92, 0.95, 1.0), a)
        # the cave with paintings (left)
        ctx.new_path()
        ctx.arc(w * 0.08, gy, h * 0.17, math.pi, 2 * math.pi)
        fill(ctx, (0.25, 0.2, 0.18), a)
        ctx.new_path()
        ctx.arc(w * 0.08, gy, h * 0.10, math.pi, 2 * math.pi)
        fill(ctx, (0.04, 0.03, 0.03), a)
        for k in range(3):
            c.circle(w * (0.035 + 0.045 * k), gy - h * 0.13 + (k % 2) * 8, h * 0.01, (0.8, 0.3, 0.2), alpha=a)
        # mammoths walking
        for k, (mx0, sp, s) in enumerate(((0.45, 0.012, 1.0), (0.62, 0.009, 0.75))):
            x = w * ((mx0 + sp * u) % 1.0)
            self.mammoth(x, gy, h * 0.13 * s, t + k, a)
        # snow
        for k in range(70):
            sx, sy, sz = STARS[k]
            y = (sy * h + t * (30 + 20 * sz)) % (gy)
            x = w * sx + 20 * math.sin(t + k)
            c.circle(x, y, 1.5 + 1.5 * sz, (1, 1, 1), alpha=0.7 * a)

    def mammoth(self, x, gy, s, t, a):
        c = self.canvas
        ctx = c.ctx
        col = (0.45, 0.32, 0.22)
        for lx in (-0.45, -0.2, 0.2, 0.45):
            c.lines([(x + lx * s, gy - s * 0.4, x + lx * s + math.sin(t * 4 + lx * 9) * s * 0.06, gy)], col,
                    width=s * 0.16, alpha=a)
        ctx.save()
        ctx.translate(x, gy - s * 0.62)
        ctx.scale(1, 0.62)
        ctx.arc(0, 0, s * 0.62, 0, 2 * math.pi)
        ctx.restore()
        fill(ctx, col, a)
        hx, hy = x + s * 0.62, gy - s * 0.75
        c.circle(hx, hy, s * 0.28, col, alpha=a)
        ctx.new_path()
        ctx.move_to(hx + s * 0.2, hy)
        ctx.curve_to(hx + s * 0.45, hy + s * 0.2, hx + s * 0.35, hy + s * 0.55, hx + s * 0.5, hy + s * 0.6)
        ctx.set_source_rgba(*col, a)
        ctx.set_line_width(s * 0.1)
        ctx.stroke()
        ctx.new_path()
        ctx.move_to(hx + s * 0.1, hy + s * 0.15)
        ctx.curve_to(hx + s * 0.3, hy + s * 0.45, hx + s * 0.6, hy + s * 0.4, hx + s * 0.62, hy + s * 0.2)
        ctx.set_source_rgba(0.95, 0.92, 0.85, a)
        ctx.set_line_width(s * 0.05)
        ctx.stroke()

    def era_farm(self, t, a):
        c, w, h, gy = self.canvas, self.L.w, self.L.h, self.gy
        ctx = c.ctx
        for k in range(60):                                    # wheat
            x = w * (0.40 + 0.6 * k / 60)
            sw = math.sin(t * 2 + k * 0.4) * 6
            c.lines([(x, gy, x + sw, gy - h * 0.09)], (0.9, 0.75, 0.35), width=3, alpha=a)
            c.circle(x + sw, gy - h * 0.095, 4, (0.95, 0.8, 0.4), alpha=a)
        for hx in (0.08, 0.2):                                 # round huts
            ctx.new_path()
            ctx.arc(w * hx, gy, h * 0.08, math.pi, 2 * math.pi)
            fill(ctx, (0.55, 0.4, 0.25), a)
            ctx.new_path()
            ctx.move_to(w * hx - h * 0.1, gy - h * 0.06)
            ctx.line_to(w * hx, gy - h * 0.18)
            ctx.line_to(w * hx + h * 0.1, gy - h * 0.06)
            ctx.close_path()
            fill(ctx, (0.8, 0.65, 0.35), a)

    def era_pyr(self, a):
        c, w, h, gy = self.canvas, self.L.w, self.L.h, self.gy
        ctx = c.ctx
        for px, ph in ((0.12, 0.32), (0.55, 0.40), (0.88, 0.24)):
            ctx.new_path()
            ctx.move_to(w * px - h * ph, gy)
            ctx.line_to(w * px, gy - h * ph)
            ctx.line_to(w * px + h * ph, gy)
            ctx.close_path()
            fill(ctx, (0.85, 0.62, 0.35), a)
            ctx.new_path()
            ctx.move_to(w * px, gy - h * ph)
            ctx.line_to(w * px + h * ph, gy)
            ctx.line_to(w * px + h * ph * 0.15, gy)
            ctx.close_path()
            fill(ctx, (0.6, 0.4, 0.22), a)

    def era_rome(self, a):
        c, w, h, gy = self.canvas, self.L.w, self.L.h, self.gy
        ctx = c.ctx
        x0, x1 = w * 0.40, w * 0.62
        top = gy - h * 0.27
        ctx.new_path()
        ctx.move_to(x0 - 20, top)
        ctx.line_to((x0 + x1) / 2, top - h * 0.08)
        ctx.line_to(x1 + 20, top)
        ctx.close_path()
        fill(ctx, (0.88, 0.86, 0.8), a)
        ctx.rectangle(x0 - 20, top, x1 - x0 + 40, h * 0.025)
        fill(ctx, (0.8, 0.78, 0.72), a)
        for k in range(7):
            cx = x0 + (x1 - x0) * k / 6
            ctx.rectangle(cx - 9, top + h * 0.025, 18, gy - top - h * 0.025)
            fill(ctx, (0.9, 0.88, 0.82), a)
        for k in range(4):                                     # arches far right (colosseum)
            ctx.new_path()
            ax = w * (0.78 + 0.05 * k)
            ctx.rectangle(ax - 30, gy - h * 0.2, 60, h * 0.2)
            fill(ctx, (0.75, 0.65, 0.5), a)
            ctx.new_path()
            ctx.arc(ax, gy - h * 0.09, 18, math.pi, 2 * math.pi)
            ctx.line_to(ax + 18, gy)
            ctx.line_to(ax - 18, gy)
            ctx.close_path()
            fill(ctx, (0.15, 0.1, 0.12), a)

    def era_castle(self, t, a):
        c, w, h, gy = self.canvas, self.L.w, self.L.h, self.gy
        ctx = c.ctx
        x0, x1 = w * 0.40, w * 0.62
        col = (0.42, 0.44, 0.55)
        ctx.rectangle(x0, gy - h * 0.18, x1 - x0, h * 0.18)
        fill(ctx, col, a)
        for k in range(12):
            ctx.rectangle(x0 + (x1 - x0) * k / 11.5, gy - h * 0.2, (x1 - x0) / 25, h * 0.02)
            fill(ctx, col, a)
        for tx in (x0, x1):
            ctx.rectangle(tx - 30, gy - h * 0.3, 60, h * 0.3)
            fill(ctx, (0.38, 0.4, 0.5), a)
            ctx.new_path()
            ctx.move_to(tx - 38, gy - h * 0.3)
            ctx.line_to(tx, gy - h * 0.38)
            ctx.line_to(tx + 38, gy - h * 0.3)
            ctx.close_path()
            fill(ctx, (0.7, 0.25, 0.3), a)
            c.lines([(tx, gy - h * 0.38, tx, gy - h * 0.43)], WHITE, width=3, alpha=a)
            fw = math.sin(t * 6) * 6
            c.poly([(tx, gy - h * 0.43), (tx + 30, gy - h * 0.42 + fw), (tx, gy - h * 0.405)], GOLD, alpha=a)
        ctx.new_path()
        ctx.arc((x0 + x1) / 2, gy - h * 0.06, 30, math.pi, 2 * math.pi)
        ctx.line_to((x0 + x1) / 2 + 30, gy)
        ctx.line_to((x0 + x1) / 2 - 30, gy)
        ctx.close_path()
        fill(ctx, (0.1, 0.08, 0.1), a)

    def era_city(self, t, a):
        c, w, h, gy = self.canvas, self.L.w, self.L.h, self.gy
        ctx = c.ctx
        for k in range(16):
            bx = w * k / 16
            bh = h * (0.14 + 0.22 * (((k * 53) % 11) / 11))
            ctx.rectangle(bx + 4, gy - bh, w / 16 - 8, bh)
            fill(ctx, (0.10, 0.10, 0.18), a)
            for r in range(int(bh / 28)):
                for q in range(3):
                    on = ((k * 7 + r * 3 + q) % 5) != 0
                    if on:
                        ctx.rectangle(bx + 14 + q * (w / 16 - 24) / 3, gy - bh + 12 + r * 28, 10, 12)
                        fill(ctx, (1.0, 0.85, 0.45), 0.8 * a)

    def ch_cpc(self, t, u):
        c, w, h, gy, H = self.canvas, self.L.w, self.L.h, self.gy, self.H
        ctx = c.ctx
        self.room((0.09, 0.10, 0.17))
        # phase 1: a trillion in 16 min 40 s;  phase 2: a quintillion in 31.7 years
        if u < 7.5:
            n, lab = 0.0, "COUNTING TO 1 TRILLION"
        elif u < 14.5:
            n, lab = 1e12 * clamp((u - 7.5) / 6.0), "COUNTING TO 1 TRILLION"
        elif u < 18.0:
            n, lab = 1e12, "COUNTING TO 1 TRILLION"
        else:
            n, lab = 1e18 * clamp((u - 21.0) / 21.0), "COUNTING TO 1 QUINTILLION"
        secs = n / PC_RATE
        yrs = secs / YEAR if u >= 18 else 0.0
        age = clamp(yrs / 31.7)
        # calendar
        cx0, cy0 = w * 0.08, h * 0.33
        rrect(ctx, cx0, cy0, w * 0.11, h * 0.15, 8)
        fill(ctx, (0.92, 0.92, 0.96))
        ctx.rectangle(cx0, cy0, w * 0.11, h * 0.04)
        fill(ctx, RED)
        c.text_centered("YEAR", cy0 + h * 0.03, size=h * 0.022, color=WHITE, cx=cx0 + w * 0.055)
        c.text_centered(f"{2026 + int(yrs)}", cy0 + h * 0.115, size=h * 0.05, color=(0.1, 0.1, 0.15),
                        cx=cx0 + w * 0.055)
        roll = 1 - ease(u, 0.3, 2.6)
        pcx = w * 0.52 + roll * w * 0.5
        self.computer(pcx, gy, H * 1.45, u, dust=clamp((yrs - 3) / 25), count=fmt_n(n))
        # the two of them: B pushes it in; both walk out at 21, come back old at 40
        out_u = ease(u, 20.8, 23.0)
        back_u = 1 - ease(u, 39.5, 42.0)
        off = w * 0.95 * (out_u if u < 39.5 else back_u)
        old = 1.0 if u >= 39.5 else 0.0
        walking = (20.8 <= u < 23.0) or (39.5 <= u < 42.0) or u < 2.6
        A = dict(x=w * 0.26 + off, walk=(u * 1.6) % 1 if walking and u > 3 else 0.0, beard=0.9 * old, hair=old)
        B = dict(x=w * 0.78 + off + roll * w * 0.5, walk=(u * 1.6) % 1 if walking else 0.0, hair=old, cane=old,
                 look=-0.4)
        if pcx < w * 1.1 or True:
            self.figs(t, A=A if A["x"] < w * 1.15 else None, B=B if B["x"] < w * 1.15 else None)
        if 8.0 <= u < 18.0:
            self.bottom("1 trillion: 16 minutes 40 seconds  (by hand: 31,710 years)", 8.0, u, col=GOLD)
        elif 23.0 <= u < 39.5:
            self.bottom("…the computer keeps counting", 23.0, u)
        elif u >= 46.6:
            self.bottom("By hand: 31.7 BILLION years: more than twice the age of the universe", 46.6, u, col=GOLD)
        sub = "1 billion numbers per second" if n == 0 else fmt_time(secs) + " of counting"
        ff = None
        if 7.5 <= u < 14.5 or 21 <= u < 42:
            ff = "FAST"
        return dict(label=lab, big=fmt_n(n), sub=sub, ff=ff)

    def ch_sand(self, t, u):
        c, w, h, gy, H = self.canvas, self.L.w, self.L.h, self.gy, self.H
        ctx = c.ctx
        self.sky_bg((0.12, 0.08, 0.25), (0.95, 0.55, 0.40))
        self.stars(t, 0.3, 0.0, 0.3)
        sea = h * 0.60
        c.glow(w * 0.5, sea, h * 0.12, (1.0, 0.7, 0.35), strength=0.7, reach=2.2)
        ctx.new_path()
        ctx.arc(w * 0.5, sea, h * 0.1, math.pi, 2 * math.pi)
        fill(ctx, (1.0, 0.78, 0.4))
        ctx.rectangle(0, sea, w, gy - sea)
        g = cairo.LinearGradient(0, sea, 0, gy)
        g.add_color_stop_rgb(0, 0.15, 0.25, 0.5)
        g.add_color_stop_rgb(1, 0.10, 0.35, 0.55)
        ctx.set_source(g)
        ctx.fill()
        for k in range(6):                                     # waves
            yy = sea + (gy - sea) * (k + 0.5) / 6
            ctx.new_path()
            for i in range(0, 81):
                x = w * i / 80
                y = yy + math.sin(x * 0.012 + t * (1.2 + 0.2 * k) + k) * 4
                if i == 0:
                    ctx.move_to(x, y)
                else:
                    ctx.line_to(x, y)
            ctx.set_source_rgba(0.6, 0.85, 1.0, 0.35)
            ctx.set_line_width(2)
            ctx.stroke()
        ctx.rectangle(0, gy - h * 0.035, w, h)
        fill(ctx, (0.85, 0.7, 0.45))
        for k in range(160):
            sx, sy, sz = STARS[k]
            c.circle(w * sx, gy - h * 0.03 + (h - gy) * sy, 1.5 + sz, (0.65, 0.5, 0.3), alpha=0.8)
        n = 0.0 if u < 10 else SAND * clamp((u - 10) / 28)
        secs = n / PC_RATE
        yrs = secs / YEAR
        fr = n / SAND
        # hourglass
        hx, hy, hs = w * 0.09, gy - h * 0.2, h * 0.17
        c.lines([(hx - hs * 0.5, hy - hs, hx + hs * 0.5, hy - hs), (hx - hs * 0.5, hy + hs, hx + hs * 0.5, hy + hs)],
                (0.6, 0.45, 0.3), width=8)
        top_lvl = 1 - fr
        c.poly([(hx - hs * 0.42 * top_lvl, hy - hs * 0.9 * top_lvl), (hx + hs * 0.42 * top_lvl, hy - hs * 0.9 * top_lvl),
                (hx, hy)], (0.95, 0.8, 0.45))
        if 0 < fr < 1:
            c.lines([(hx, hy, hx, hy + hs * 0.9)], (0.95, 0.8, 0.45), width=3)
        c.poly([(hx - hs * 0.42 * fr, hy + hs * 0.95), (hx + hs * 0.42 * fr, hy + hs * 0.95),
                (hx, hy + hs * (0.95 - 0.9 * fr))], (0.95, 0.8, 0.45))
        c.poly([(hx - hs * 0.45, hy - hs * 0.95), (hx + hs * 0.45, hy - hs * 0.95), (hx + 6, hy), (hx + hs * 0.45, hy + hs * 0.95),
                (hx - hs * 0.45, hy + hs * 0.95), (hx - 6, hy)], (0.8, 0.9, 1.0), alpha=0.18)
        self.computer(w * 0.52, gy, H * 1.45, u, count=fmt_n(n))
        counting = 10 <= u < 38
        self.figs(t, A=dict(x=w * 0.27, look=0.4), B=dict(x=w * 0.80, look=-0.4))
        if 10 <= u < 38:
            self.bottom("every beach, every desert: about 7.5 × 10¹⁸ grains (estimate)", 10, u)
        elif u >= 43:
            self.bottom("By hand: 237 BILLION years: 17 times the age of the universe", 43, u, col=GOLD)
        sub = "with the computer: 1 billion per second" if n == 0 else \
            f"YEAR {2026 + int(yrs)}  ·  " + fmt_time(secs) + " of counting"
        return dict(label="COUNTING ALL THE SAND ON EARTH", big=fmt_n(n), sub=sub, ff="FAST" if counting else None)

    def ch_atoms(self, t, u):
        c, w, h, gy, H = self.canvas, self.L.w, self.L.h, self.gy, self.H
        ctx = c.ctx
        self.sky_bg((0.02, 0.02, 0.06), (0.04, 0.03, 0.10))
        self.stars(t, 0.9)
        Ln = 0.0 if u < 14 else 80.0 * clamp((u - 14) / 28)
        z = 4.2 * ease(u, 14, 42)                              # zoom out: 0 Earth, 1 Sun, 2 galaxy, 3+ web
        cx, cy = w * 0.5, h * 0.50
        # Earth
        ae = clamp(1.2 - z)
        if ae > 0:
            r = h * 0.17 * math.exp(-z * 2.0)
            c.glow(cx, cy, r * 1.1, (0.3, 0.6, 1.0), strength=0.5 * ae, reach=1.6)
            c.circle(cx, cy, r, (0.15, 0.4, 0.85), alpha=ae)
            for k, (dx, dy, rr) in enumerate(((-0.3, -0.2, 0.35), (0.25, 0.1, 0.4), (-0.1, 0.45, 0.25))):
                c.circle(cx + dx * r, cy + dy * r, rr * r, (0.25, 0.65, 0.35), alpha=ae)
        # the Sun and orbits
        asun = clamp(z - 0.3) * clamp(2.2 - z)
        if asun > 0:
            sc = h * 0.35 * math.exp(-(z - 1.0) * 1.6)
            c.glow(cx - sc * 0.9, cy, sc * 0.15, (1.0, 0.8, 0.3), strength=0.8 * asun, reach=2.4)
            c.circle(cx - sc * 0.9, cy, sc * 0.08, (1.0, 0.85, 0.35), alpha=asun)
            for k in range(1, 6):
                c.ring(cx - sc * 0.9, cy, sc * 0.25 * k, (0.5, 0.6, 0.9), width=1.5, alpha=0.4 * asun)
                a = t * (0.6 / k) + k
                c.circle(cx - sc * 0.9 + math.cos(a) * sc * 0.25 * k, cy + math.sin(a) * sc * 0.25 * k, 4,
                         (0.6, 0.8, 1.0), alpha=asun)
        # the galaxy
        ag = clamp(z - 1.4) * clamp(3.3 - z)
        if ag > 0:
            gs = h * 0.6 * math.exp(-(z - 2.2) * 1.5)
            rot = t * 0.05
            for k, (rr, jit) in enumerate(GAL_DOTS):
                arm = k % 2
                th = rr * 4.5 + arm * math.pi + rot
                x = cx + math.cos(th) * rr * gs + jit * gs
                y = cy + (math.sin(th) * rr * gs + jit * gs * 0.6) * 0.45
                c.circle(x, y, 1.6, (0.8, 0.85, 1.0) if k % 5 else (1.0, 0.8, 0.6), alpha=ag * (1 - rr * 0.6))
            c.glow(cx, cy, gs * 0.12, (1.0, 0.85, 0.6), strength=0.6 * ag, reach=2)
        # the cosmic web
        aw = clamp(z - 2.7)
        if aw > 0:
            ws = h * 0.35 * math.exp(-(z - 3.6) * 0.8)
            pts = [(cx + gx * ws, cy + gy_ * ws * 0.6) for gx, gy_ in WEB]
            for i in range(len(pts)):
                for j in range(i + 1, min(len(pts), i + 6)):
                    d = math.hypot(pts[i][0] - pts[j][0], pts[i][1] - pts[j][1])
                    if d < ws * 0.6:
                        c.lines([(pts[i][0], pts[i][1], pts[j][0], pts[j][1])], (0.6, 0.5, 1.0), width=1.2,
                                alpha=0.35 * aw)
                c.circle(pts[i][0], pts[i][1], 2.5, (0.85, 0.8, 1.0), alpha=0.8 * aw)
        # the army of computers on the ground: 8 -> 13 they multiply, then fade as we zoom out
        self.ground(col=(0.5, 0.6, 1.0), alpha=0.6, floor=(0.02, 0.02, 0.05))
        arm = clamp((u - 8) / 5) * (1 - ease(u, 14, 17))
        if arm > 0:
            nrow = int(1 + 3 * arm)
            for r in range(nrow):
                cnt = int(4 + arm * 26)
                for k in range(cnt):
                    x = w * (k + 0.5) / cnt
                    s = h * 0.09 * (0.9 - 0.18 * r)
                    yb = gy - h * 0.005 - r * h * 0.035
                    ctx.rectangle(x - s * 0.3, yb - s, s * 0.6, s)
                    fill(ctx, (0.15, 0.17, 0.26), 0.9)
                    c.circle(x, yb - s * 0.75, s * 0.08, (0.3, 1.0, 0.5), alpha=0.9 if (k + r + int(t * 4)) % 3 else 0.2)
            c.text_centered("× 7,500,000,000,000,000,000 computers", h * 0.72, size=h * 0.04, color=GOLD,
                            alpha=clamp((u - 9) / 0.4) * (1 - ease(u, 14, 15)))
        counting = 14 <= u < 42
        self.figs(t, A=dict(x=w * 0.20, look=0.4), B=dict(x=w * 0.82, look=-0.4))
        if u >= 46.5:
            self.bottom("The universe is only 1.4 × 10¹⁰ years old.", 46.5, u, col=GOLD)
        elif 17 <= u < 42:
            labels = ((0.0, "Earth"), (1.0, "the Solar System"), (2.2, "the Milky Way"), (3.4, "the observable universe"))
            lab = [s for zz, s in labels if z >= zz - 0.3][-1]
            self.bottom(f"zooming out: {lab}", 17, u, col=SOFT)
        Ly = Ln - math.log10(ARMY * YEAR)
        if Ln == 0:
            sub = "a computer for every grain of sand"
        elif Ly < -7:
            sub = "less than a second"
        else:
            sub = fmt_time(10 ** Ly * YEAR) + " of counting" if Ly < 12 else fmt_log_years(Ly) + " of counting"
        return dict(label="COUNTING EVERY ATOM IN THE UNIVERSE (≈ 10⁸⁰)", big=fmt_log(Ln) if Ln >= 16 else
                    f"{int(10 ** Ln) if Ln > 0 else 0:,}", sub=sub, ff="FAST" if counting else None)

    def ch_googol(self, t, u):
        c, w, h, gy, H = self.canvas, self.L.w, self.L.h, self.gy, self.H
        ctx = c.ctx
        LS, LSUN, LSTAR = math.log10(ARMY * YEAR) + 9.7, math.log10(ARMY * YEAR) + 14.0, 100.0
        pts = [(8.0, 0.0), (14.0, LS), (17.0, LS), (22.0, LSUN), (25.0, LSUN), (32.0, LSTAR)]
        if u < pts[0][0]:
            Ln = 0.0
        elif u >= pts[-1][0]:
            Ln = LSTAR
        else:
            for (u0, v0), (u1, v1) in zip(pts, pts[1:]):
                if u0 <= u < u1:
                    Ln = v0 + (v1 - v0) * smooth((u - u0) / (u1 - u0))
                    break
        Ly = Ln - math.log10(ARMY * YEAR)
        self.sky_bg((0.04, 0.04, 0.10), (0.02, 0.02, 0.05))
        sa = 1.0 - ease(u, 22.0, 24.5)                          # the stars go out
        self.stars(t, sa)
        # the Sun: swells red, collapses, fades (u 14 -> 17)
        sxx, syy, r0 = w * 0.82, h * 0.42, h * 0.07
        if u < 14:
            rs, col, al = r0 * (1 + 0.3 * ease(u, 12, 14)), mix((1.0, 0.85, 0.3), (1.0, 0.5, 0.25), ease(u, 12, 14)), 1.0
        elif u < 15.6:
            k = ease(u, 14, 15.6)
            rs, col, al = r0 * (1.3 + 1.6 * k), mix((1.0, 0.5, 0.25), (0.95, 0.3, 0.2), k), 1.0
        elif u < 16.3:
            k = ease(u, 15.6, 16.3)
            rs, col, al = r0 * (2.9 - 2.65 * k), mix((0.95, 0.3, 0.2), (0.9, 0.9, 1.0), k), 1.0
        else:
            rs, col, al = r0 * 0.25, (0.9, 0.9, 1.0), 1 - ease(u, 16.3, 17.5)
        if al > 0:
            c.glow(sxx, syy, rs, col, strength=0.7 * al, reach=2.4)
            c.circle(sxx, syy, rs, col, alpha=al)
        dark = 0.55 * ease(u, 16.0, 17.0) + 0.38 * ease(u, 22.0, 24.5)
        self.ground(col=(0.5, 0.55, 0.8), alpha=0.5 * (1 - dark), floor=(0.02, 0.02, 0.04))
        if dark > 0:
            ctx.rectangle(0, 0, w, h)
            fill(ctx, (0, 0, 0), min(0.95, dark))
        if dark > 0.3:
            c.glow(w * 0.30, gy - H * 0.5, H * 0.9, (0.6, 0.75, 1.0), strength=0.4 * dark, reach=1.8)
            c.glow(w * 0.70, gy - H * 0.5, H * 0.9, (1.0, 0.7, 0.4), strength=0.3 * dark, reach=1.8)
        self.figs(t, A=dict(x=w * 0.30, look=0.5 if 14 <= u < 18 else 0.0,
                            mouth="open" if 15 <= u < 18 else "smile"),
                  B=dict(x=w * 0.62, look=0.6 if 14 <= u < 18 else -0.3))
        if 14.0 <= u < 17.5:
            c.text_centered("THE SUN DIES  (in about 5 billion years)", h * 0.37, size=h * 0.04, color=(1.0, 0.55, 0.4),
                            alpha=clamp((u - 14) / 0.3))
        if 22.0 <= u < 25.5:
            c.text_centered("THE LAST STAR GOES OUT  (about 100 trillion years)", h * 0.37, size=h * 0.04,
                            color=(0.75, 0.85, 1.0), alpha=clamp((u - 22) / 0.3))
        if u >= 43:
            self.bottom("By hand, 1 number per second: 3 × 10⁹² years", 43, u, col=GOLD)
        elif 8 <= u < 32:
            self.bottom("…and it keeps going", 8, u)
        if Ln <= 0:
            sub, big = "a computer for every grain of sand", "0"
        else:
            big = fmt_log(Ln) if Ln >= 16 else f"{int(10 ** Ln):,}"
            sub = fmt_time(10 ** Ly * YEAR) + " of counting" if Ly < 9 else fmt_log_years(Ly) + " of counting"
            if Ly < -7:
                sub = "less than a second"
        return dict(label="COUNTING TO A GOOGOL (10¹⁰⁰)", big=big, sub=sub, ff="FAST" if 8 <= u < 32 else None)

    def ch_gplex(self, t, u):
        c, w, h, gy, H = self.canvas, self.L.w, self.L.h, self.gy, self.H
        ctx = c.ctx
        self.sky_bg((0.05, 0.04, 0.10), (0.02, 0.02, 0.05))
        Lz = 0.0 if u < 8 else 80.0 * ease(u, 8, 30) ** 1.15
        # endless zoom-out of zeros: two layers of a self-similar grid, 1/4 size apart
        ph = (Lz / 80.0 * 9.0) % 1.0
        ctx.select_font_face("Consolas", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        if u >= 8:
            for layer in range(2):
                fs = h * 0.09 * 0.25 ** (ph + layer - 0.0)
                fs = max(fs, 2.0)
                a = (1 - ph) if layer == 0 else ph
                a *= clamp((u - 8) / 1.0) * (0.2 if u >= 31 else 0.38)
                if fs < 3 or a < 0.02:
                    continue
                ctx.set_font_size(fs)
                cw = ctx.text_extents("0").x_advance
                ncol = int(w / cw) + 2
                row = "0" * ncol
                nrows = int(h / (fs * 1.1)) + 2
                ctx.set_source_rgba(*GOLD, a)
                for r in range(nrows):
                    ctx.move_to(-((r * 7) % 3) * cw * 0.3, (r + 1) * fs * 1.1)
                    ctx.show_text(row)
        ctx.rectangle(0, 0, w, h)
        fill(ctx, (0.02, 0.02, 0.05), 0.35)
        self.ground(col=(0.8, 0.7, 0.4), alpha=0.5, floor=(0.02, 0.02, 0.04))
        if u >= 30:                                             # OUT OF ATOMS
            k = u - 30
            s = 1 + 0.4 * math.exp(-k / 0.1)
            c.text_centered("OUT OF ATOMS", h * 0.48, size=h * 0.085 * s, color=RED, alpha=clamp(k / 0.15) *
                            (1 - ease(u, 32.6, 33.0)))
        writing = 7.5 <= u < 30
        self.figs(t, A=dict(x=w * 0.30, arm_r=(1.2 + 0.08 * math.sin(u * 6), 1.0) if writing else (0.35, 0.2),
                            mouth="flat" if u >= 30 else "smile", dizzy=ease(u, 37.4, 38.0), look=0.3),
                  B=dict(x=w * 0.72, look=-0.4))
        if 9 <= u < 30:
            self.bottom("one zero on every atom of the universe…", 9, u)
        elif u >= 30:
            self.bottom("Needed: 10¹⁰⁰ zeros.  Atoms in the universe: about 10⁸⁰.", 30, u, col=GOLD)
        big = "1" if Lz <= 0 else ("1" + "0" * int(10 ** Lz) if Lz < 1.0 else fmt_log(Lz) + " zeros")
        if Lz > 0 and Lz < 1.0:
            big = f"{int(10 ** Lz)} zeros"
        return dict(label="WRITING A GOOGOLPLEX (1 with 10¹⁰⁰ zeros)", big=big,
                    sub="zeros written so far" if u >= 8 else "", ff="FAST" if writing else None)

    def ch_inf(self, t, u):
        c, w, h, gy, H = self.canvas, self.L.w, self.L.h, self.gy, self.H
        ctx = c.ctx
        self.sky_bg((0.06, 0.04, 0.14), (0.02, 0.02, 0.05))
        self.stars(t, 0.8)
        cx, cy, R = w * 0.5, h * 0.47, h * 0.14
        a_inf = clamp((u - 1.0) / 1.0)
        ctx.new_path()
        for i in range(201):                                    # the lemniscate
            th = i / 200 * 2 * math.pi
            d = 1 + math.sin(th) ** 2
            x, y = cx + R * 1.8 * math.cos(th) / d, cy + R * 1.8 * math.sin(th) * math.cos(th) / d
            if i == 0:
                ctx.move_to(x, y)
            else:
                ctx.line_to(x, y)
        ctx.set_source_rgba(0.6, 0.5, 1.0, 0.5 * a_inf)
        ctx.set_line_width(16)
        ctx.stroke_preserve()
        ctx.set_source_rgba(0.85, 0.8, 1.0, a_inf)
        ctx.set_line_width(5)
        ctx.stroke()
        sp = 0.5 + 2.5 * ease(u, 4, 12)
        for k in range(6):                                       # bright points running around it
            th = t * sp + k * 2 * math.pi / 6
            d = 1 + math.sin(th) ** 2
            x, y = cx + R * 1.8 * math.cos(th) / d, cy + R * 1.8 * math.sin(th) * math.cos(th) / d
            c.glow(x, y, 16, GOLD, strength=0.8 * a_inf, reach=2.2)
            c.circle(x, y, 5, WHITE, alpha=a_inf)
        # numbers fly from A into the sign
        ax, ay = w * 0.30, gy - H * 1.0
        if 4 <= u < 19:
            for k in range(6):
                ph = ((u - 4) * 0.7 + k / 6) % 1.0
                x = ax + (cx - ax) * ph
                y = ay + (cy - ay) * ph - math.sin(ph * math.pi) * h * 0.12
                val = int((u * 37 + k * 11) * 10 ** (1 + (k % 6)))
                c.text_centered(f"{val:,}", y, size=h * 0.03 * (1 - 0.7 * ph), color=WHITE, alpha=0.9 * (1 - ph), cx=x)
        counting = 4 <= u < 19
        tk = (u * 9) % 1.0
        self.figs(t, A=dict(x=w * 0.30, mouth=("open" if tk < 0.5 else "smile") if counting else "smile",
                            counting=counting),
                  B=dict(x=w * 0.72, look=-0.4))
        if u >= 23.5:
            self.bottom("Infinity is not a number you reach. It is the fact that counting never ends.", 23.5, u,
                        col=GOLD, size=0.03)
        if u < 4:
            big = "0"
        elif u < 19:
            e = 1 + (u - 4) ** 1.6 * 4
            big = "10" + sup(int(e))
        else:
            big = "∞"
        return dict(label="COUNTING TO INFINITY", big=big, sub="+1, +1, +1, …" if u >= 4 else "",
                    ff="FAST" if counting else None)

    def ch_recap(self, t, u):
        c, w, h, gy, H = self.canvas, self.L.w, self.L.h, self.gy, self.H
        ctx = c.ctx
        self.sky_bg((0.07, 0.07, 0.14), (0.02, 0.02, 0.05))
        self.stars(t, 0.6)
        c.text_centered("HOW LONG TO COUNT TO…", h * 0.14, size=h * 0.05, color=WHITE)
        rows = [("100", "1 min 40 s"), ("1,000", "16 min 40 s"), ("1 million", "11.6 days"),
                ("1 billion", "31.7 years"), ("1 trillion", "31,710 years"), ("1 quintillion", "31.7 billion years"),
                ("all the sand on Earth", "237 billion years"), ("all the atoms", "3 × 10⁷² years"),
                ("a googol", "3 × 10⁹² years"), ("a googolplex", "impossible"), ("infinity", "never")]
        y0 = h * 0.22
        for i, (a_, b_) in enumerate(rows):
            col = i % 2
            r = i // 2 if i < 10 else 5
            x = w * (0.08 + 0.43 * col) if i < 10 else w * 0.29
            y = y0 + r * h * 0.085
            al = clamp((u - 0.3 - i * 0.18) / 0.3)
            rrect(ctx, x, y, w * 0.41, h * 0.07, 10)
            fill(ctx, (0.10, 0.10, 0.18), 0.9 * al)
            text_left(c, a_, x + w * 0.015, y + h * 0.047, h * 0.032, WHITE, alpha=al)
            ctx.select_font_face("Arial", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
            ctx.set_font_size(h * 0.032)
            tw = ctx.text_extents(b_).x_advance
            text_left(c, b_, x + w * 0.395 - tw, y + h * 0.047, h * 0.032, GOLD, alpha=al)
        c.text_centered("1 number per second, by hand", h * 0.76, size=h * 0.026, color=SOFT, bold=False)
        if u >= 4:
            c.text_centered("Which one surprised you the most?", h * 0.83, size=h * 0.04, color=GOLD,
                            alpha=clamp((u - 4) / 0.4))
        # A keeps counting, small, in the corner
        self.gy, self.H = h * 0.97, h * 0.14
        n = int(u) + 1
        self.figs(t, A=dict(x=w * 0.06, H=h * 0.14, counting=True))
        return None

    # ------------------------------------------------------------- frame
    def draw(self, f, rule):
        L, c = self.L, self.canvas
        w, h = L.w, L.h
        t = f * DT
        self.t = t
        self.gy, self.H = h * 0.84, h * 0.28
        ch = ORDER[-1]
        for k in ORDER:
            if t >= T0[k]:
                ch = k
        u = t - T0[ch]
        self.pos = {}
        cnt = getattr(self, "ch_" + ch)(t, u)
        g = cairo.LinearGradient(0, 0, 0, h * 0.32)
        g.add_color_stop_rgba(0, 0.0, 0.0, 0.02, 0.55)
        g.add_color_stop_rgba(1, 0.0, 0.0, 0.02, 0.0)
        c.ctx.rectangle(0, 0, w, h * 0.32)
        c.ctx.set_source(g)
        c.ctx.fill()
        self.counter(cnt)
        self.ladder(t, ch, u)
        self.title_card(ch, u)
        self.reveal(ch, u)
        self.say(t)
        # fade through dark at every chapter change
        dur = dict(CHAPTERS)[ch]
        fa = max(clamp(1 - u / 0.35), clamp(1 - (dur - u) / 0.35)) if ch != "intro" else clamp(1 - (dur - u) / 0.35)
        if ch == "recap":
            fa = max(clamp(1 - u / 0.35), clamp(1 - (dur - u) / 1.2))
        if fa > 0:
            c.ctx.rectangle(0, 0, w, h)
            fill(c.ctx, (0.01, 0.01, 0.03), fa * 0.9)
        c.text_centered("SatFy", h * 0.985, size=h * 0.022, color=WHITE, alpha=0.25, cx=w * 0.955, bold=False)


def render(layout, sim, out_path, rule, still_frame=None, f0=0, f1=None):
    sc = Scene(layout, sim)
    writer = None if still_frame is not None else VideoWriter(out_path, sc.canvas, FPS)
    f1 = sim["nf"] if f1 is None else f1
    for f in range(f0, f1):
        if still_frame is not None and f != still_frame:
            continue
        sc.draw(f, rule)
        if writer is None:
            studio.save_still(sc.canvas, out_path)
            return f / FPS
        writer.write_frame()
    writer.close()
    return (f1 - f0) / FPS


# ---------------------------------------------------------------- sound (original)
def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def sound_bed(t0=0.0, t1=None):
    t1 = T_END if t1 is None else t1
    n = int(round((t1 - t0) * SR))
    out = np.zeros(n + 3 * SR)
    rng = np.random.default_rng(9)

    def add(ts, sig, g=1.0):
        i0 = int((ts - t0) * SR)
        if i0 < 0:
            sig = sig[-i0:]
            i0 = 0
        sig = sig[: max(0, len(out) - i0)]
        out[i0:i0 + len(sig)] += g * sig

    def tone(f, dur, decay, harm=((1, 1.0), (2, 0.3))):
        tv = np.arange(int(dur * SR)) / SR
        return sum(a * np.sin(2 * np.pi * f * k * tv) for k, a in harm) * np.exp(-tv / decay)

    def chap_at(tt):
        ch = ORDER[0]
        for k in ORDER:
            if tt >= T0[k]:
                ch = k
        return ch

    # music: plucked arpeggios, 100 BPM; each level has its own key / progression / density
    MAJ = [(0, (12, 16, 19)), (-5, (11, 14, 19)), (-3, (12, 16, 21)), (-7, (12, 17, 21))]     # I V vi IV
    MIN = [(-3, (9, 12, 16)), (-7, (9, 12, 17)), (-4, (11, 14, 19)), (-3, (9, 12, 16))]       # vi IV V vi
    STYLE = {"intro": (48, MAJ, 1.0), "c100": (50, MAJ, 1.0), "c1k": (45, MAJ, 0.9), "c1m": (47, MAJ, 1.0),
             "c1b": (43, MAJ, 0.9), "c1t": (45, MIN, 1.0), "cpc": (48, MAJ, 1.0), "sand": (46, MAJ, 0.9),
             "atoms": (44, MIN, 0.7), "googol": (43, MIN, 0.5), "gplex": (45, MIN, 0.8), "inf": (48, MAJ, 1.0),
             "recap": (48, MAJ, 0.9)}
    beat = 0.6
    tb, b = 0.0, 0
    while tb < T_END:
        ch = chap_at(tb + 0.01)
        root, prog, dens = STYLE[ch]
        r_off, chord = prog[b % 4]
        if t0 - 3 <= tb < t1:
            add(tb, tone(hz(root + r_off), 2.2, 0.6), 0.09)
            add(tb, tone(hz(root + r_off + 12 + chord[0] - 12), 2.4, 1.2, ((1, 1.0),)), 0.025)
            for e in range(8):
                if dens < 1.0 and e % 2 and (e * 3 + b) % 4 >= int(dens * 4):
                    continue
                m = root + r_off + chord[(e * 2) % 3] + (12 if e % 4 == 3 else 0)
                add(tb + e * beat / 2, tone(hz(m), 0.35, 0.10, ((1, 1.0), (2, 0.45), (3, 0.15))), 0.032)
        tb += 4 * beat
        b += 1

    def blip(ts, base):
        f = base * (1 + 0.12 * rng.standard_normal())
        tv = np.arange(int(0.055 * SR)) / SR
        sig = np.sign(np.sin(2 * np.pi * f * tv)) * 0.4 + np.sin(2 * np.pi * f * tv)
        add(ts, sig * np.clip(tv / 0.004, 0, 1) * np.exp(-tv / 0.03), 0.045)

    for a, b_, who, text in LINES:
        base = 700 if who == "A" else 420
        for i in range(0, len(text), 2):
            if text[i] in " .…,":
                continue
            tt = a + i / CPS
            if tt >= b_:
                break
            if t0 - 1 <= tt < t1:
                blip(tt, base)

    def ding(ts, g=0.06):
        for m in (84, 88, 91):
            add(ts, tone(hz(m), 1.4, 0.45, ((1, 1.0), (2.76, 0.25))), g)

    def pop(ts, m=72, g=0.10):
        tv = np.arange(int(0.09 * SR)) / SR
        f = hz(m) * (1 + 1.5 * tv / 0.09)
        add(ts, np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tv / 0.04), g)

    def tick(ts, f=2200, g=0.04):
        tv = np.arange(int(0.03 * SR)) / SR
        add(ts, np.sin(2 * np.pi * f * tv) * np.exp(-tv / 0.006), g)

    def whoosh(ts, dur=0.5, g=0.05, up=True):
        tv = np.arange(int(dur * SR)) / SR
        nz = rng.standard_normal(len(tv))
        k = int(SR * 0.002)
        nz = np.convolve(nz, np.ones(k) / k, mode="same")
        env = np.sin(np.pi * tv / dur) ** 2
        add(ts, nz * env * 6.0, g)

    def boom(ts, g=0.4):
        tv = np.arange(int(1.0 * SR)) / SR
        add(ts, np.sin(2 * np.pi * np.cumsum(40 + 90 * np.exp(-tv / 0.06)) / SR) * np.exp(-tv / 0.35), g)

    def sweep(ts, dur, f0, f1, g=0.06):
        tv = np.arange(int(dur * SR)) / SR
        f = f0 + (f1 - f0) * tv / dur
        add(ts, np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * tv / dur), g)

    def count_ticks(a, b_, rate, m0=76, m1=88):
        """a capped stream of soft ticks while numbers race, pitch rising over the run."""
        step = 1.0 / min(rate, 9.0)
        tt = a
        while tt < b_:
            u = (tt - a) / max(1e-6, b_ - a)
            if t0 - 1 <= tt < t1:
                pop(tt, m0 + (m1 - m0) * u, 0.045)
            tt += step

    T = T0
    # intro: one pop per number (real time); the ladder pops
    for k in range(12):
        pop(T["intro"] + k, 76, 0.09)
    for i in range(11):
        pop(T["intro"] + 7.4 + i * 0.25, 70 + i, 0.07)
    # every level: title whoosh, reveal ding, card flight whoosh
    for k in ORDER[1:-1]:
        whoosh(T[k] + 0.05, 0.6, 0.05)
        ur = REVEAL[k][0]
        ding(T[k] + ur, 0.07)
        boom(T[k] + ur, 0.12)
        whoosh(T[k] + ur + CARD_HOLD, CARD_FLY + 0.1, 0.04)
        pop(T[k] + ur + CARD_HOLD + CARD_FLY, 84, 0.08)
    whoosh(T["recap"] + 0.05, 0.6, 0.05)
    # 100: microwave hum + the real ding
    tv = np.arange(int(17.4 * SR)) / SR
    hum = (np.sin(2 * np.pi * 60 * tv) + 0.5 * np.sin(2 * np.pi * 120 * tv)) * np.clip(tv / 0.2, 0, 1) * \
        np.clip((17.4 - tv) / 0.1, 0, 1)
    add(T["c100"] + 4.6, hum, 0.02)
    pop(T["c100"] + 4.0, 80)
    count_ticks(T["c100"] + 6, T["c100"] + 22, 6.2)
    # 1,000: the clock, a yawn, snores
    count_ticks(T["c1k"] + 5, T["c1k"] + 24, 53)
    sweep(T["c1k"] + 8.5, 1.2, 300, 180, 0.05)
    for k in range(9):
        tsn = T["c1k"] + 11.5 + k * 1.9
        tv = np.arange(int(1.0 * SR)) / SR
        nz = np.convolve(rng.standard_normal(len(tv)), np.ones(40) / 40, mode="same")
        add(tsn, nz * np.sin(np.pi * tv / 1.0) ** 2 * 3.0, 0.03)
    sweep(T["c1k"] + 28.5, 0.4, 300, 700, 0.05)
    # million: a soft chime at every new day
    count_ticks(T["c1m"] + 7, T["c1m"] + 43, 9)
    for d in range(1, 12):
        pop(T["c1m"] + 7 + 36 * d / 11.574, 60 + d, 0.06)
    # billion: chimes every 5 years, stopwatch ticks, rewind sweep
    count_ticks(T["c1b"] + 6, T["c1b"] + 40, 9)
    for y in range(5, 32, 5):
        pop(T["c1b"] + 6 + 34 * y / 31.69, 79, 0.07)
    for k in range(int(6.8 / 0.5)):
        tick(T["c1b"] + 52 + k * 0.5, 3000, 0.035)
    sweep(T["c1b"] + 63, 3.5, 1600, 300, 0.05)
    # trillion: an era chime when the scenery changes
    count_ticks(T["c1t"] + 9, T["c1t"] + 52, 9)
    for yb in (-10000, -3000, -500, 500, 1850):
        lo, hi = 9.0, 52.0
        for _ in range(40):
            mid = (lo + hi) / 2
            if c1t_year(mid) < yb:
                lo = mid
            else:
                hi = mid
        ding(T["c1t"] + hi, 0.035)
    # computer: rolling in, a hum, fast ticks, footsteps out / back
    sweep(T["cpc"] + 0.3, 2.2, 90, 110, 0.03)
    tv = np.arange(int(41 * SR)) / SR
    add(T["cpc"] + 2.6, np.sin(2 * np.pi * 110 * tv) * 0.4 * np.clip(tv / 0.5, 0, 1) * np.clip((41 - tv) / 0.5, 0, 1), 0.02)
    count_ticks(T["cpc"] + 7.5, T["cpc"] + 14.5, 9, 80, 92)
    count_ticks(T["cpc"] + 21, T["cpc"] + 42, 7, 72, 84)
    for k in range(6):
        tick(T["cpc"] + 20.9 + k * 0.33, 500, 0.05)
        tick(T["cpc"] + 39.6 + k * 0.38, 450, 0.05)
    # sand: waves
    tv = np.arange(int(52 * SR)) / SR
    nz = np.convolve(rng.standard_normal(len(tv)), np.ones(60) / 60, mode="same")
    add(T["sand"], nz * (0.5 + 0.5 * np.sin(2 * np.pi * tv / 6.0)) ** 2 * 2.5 * np.clip(tv / 1.0, 0, 1) *
        np.clip((52 - tv) / 1.0, 0, 1), 0.03)
    count_ticks(T["sand"] + 10, T["sand"] + 38, 8)
    # atoms: computers multiplying, a rising zoom sweep
    for k in range(12):
        pop(T["atoms"] + 8 + k * 0.42, 64 + 2 * k, 0.05)
    count_ticks(T["atoms"] + 14, T["atoms"] + 42, 6, 70, 90)
    sweep(T["atoms"] + 14, 28, 120, 420, 0.02)
    # googol: the Sun dies, the last star goes out
    count_ticks(T["googol"] + 8, T["googol"] + 14, 8)
    boom(T["googol"] + 15.6, 0.45)
    tv = np.arange(int(1.6 * SR)) / SR
    add(T["googol"] + 15.7, np.sin(2 * np.pi * np.cumsum(900 * np.exp(-tv / 0.5) + 60) / SR) * np.sin(np.pi * tv / 1.6), 0.05)
    count_ticks(T["googol"] + 17, T["googol"] + 22, 6)
    tv = np.arange(int(2.0 * SR)) / SR
    add(T["googol"] + 22.0, np.sin(2 * np.pi * np.cumsum(500 * np.exp(-tv / 0.8) + 80) / SR) * np.sin(np.pi * tv / 2.0), 0.05)
    count_ticks(T["googol"] + 25, T["googol"] + 32, 7, 64, 80)
    # googolplex: scribbles, then the stamp
    for k in range(int(22.5 * 6)):
        tts = T["gplex"] + 7.5 + k / 6
        tv = np.arange(int(0.06 * SR)) / SR
        add(tts, rng.standard_normal(len(tv)) * np.exp(-tv / 0.02), 0.012)
    boom(T["gplex"] + 30.0, 0.35)
    sweep(T["gplex"] + 30.05, 0.6, 500, 150, 0.06)
    for k in range(4):
        pop(T["gplex"] + 37.4 + 0.2 * k, 86 - 3 * k, 0.06)
    # infinity: faster and faster pops, then a shimmer
    tt = T["inf"] + 4.0
    while tt < T["inf"] + 19.0:
        pop(tt, 72 + 12 * ((tt - T["inf"] - 4) / 15), 0.05)
        tt += max(0.08, 0.4 - 0.03 * (tt - T["inf"] - 4))
    for k in range(6):
        add(T["inf"] + 19.0 + k * 0.12, tone(hz(84 + 3 * k), 1.6, 0.6, ((1, 1.0),)), 0.03)
    # recap: A counting in the corner
    for k in range(22):
        pop(T["recap"] + k, 76, 0.06)
    out = out[:n]
    if t1 >= T_END:                                             # the end: a soft fade with the picture
        k = int(1.5 * SR)
        out[-k:] *= np.linspace(1.0, 0.0, k) ** 2
    return out.astype(np.float32)


def _worker(o, sim, label, rule):
    layout = get_layout(o)
    name = f"{SCENE}_{label}_{layout.tag}"
    video = studio.OUT_DIR / f"{name}_silent.mp4"
    d = render(layout, sim, video, rule)
    kit.deliver_loop(SCENE, name, layout, video, [], d, voice="piano", bed=sound_bed(), peak_db=-6.0)


def main():
    label, rule = arg("--label", "v1"), arg("--rule", "")
    studio.OUT_DIR.mkdir(exist_ok=True)
    sim = simulate()
    if kit.has("--still"):
        layout = get_layout(kit.orients()[0])
        if arg("--at"):
            f = int(round(float(arg("--at")) * FPS))
        else:
            f = int(arg("--frame", "0"))
        png = studio.OUT_DIR / f"{SCENE}_{label}_f{f}_{layout.tag}.png"
        render(layout, sim, png, rule, still_frame=f)
        print(f"[{SCENE}] -> {png}")
        return
    print(f"[{SCENE}] {T_END:.1f}s")
    kit.fan_out(_worker, (sim, label, rule), SCENE)


if __name__ == "__main__":
    main()
