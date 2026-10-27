"""STICKMAN — funny stick-figure math explainers (no voice: typed speech bubbles + "blip" voices + cartoon SFX).

--ep 1  "Why can't you divide by zero?"  6 cookies shared with 3 friends (2 each), 1 friend (6), 0 friends (???).
        The teacher: "nobody gets anything, it has NO answer → undefined". Punchline: "also… you have no friends."
--ep 2  "0.999… = 1?"  the gap 0.1, 0.01, 0.001 … shrinks to nothing; 1/3 = 0.333… ×3 → 0.999… = 1;
        the student's head explodes (and comes back dizzy).
Hook: frame 0 already shows the question big at the bottom and the first line being said.
Audio (original): plucked C–G–Am–F loop, blip voices (A high, B low), pop / ding / sad trombone / crunch / boom.
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

SCENE = "stickman"
EP = int(arg("--ep", "1"))
SR = audio.SR
GOLD = (1.0, 0.82, 0.40)
BLUE = (0.45, 0.80, 1.00)
ORANGE = (1.00, 0.62, 0.35)
RED = (1.0, 0.35, 0.35)
LIME = (0.55, 1.0, 0.55)
CPS = 22.0                                      # typing speed (chars per second)

if EP == 1:
    T_LOOP = 21.0
    LINES = [  # t0, t1, who, text
        (0.05, 2.35, "A", "Why can't I divide by zero?!"),
        (2.60, 4.00, "A", "6 cookies, 3 friends…"),
        (6.40, 7.40, "A", "Only 1 friend?"),
        (9.50, 10.80, "A", "Now… ZERO friends."),
        (11.60, 13.30, "A", "How many does each one get??"),
        (14.30, 16.60, "B", "Nobody gets anything. It has NO answer."),
        (17.00, 18.40, "B", "Also… you have no friends."),
    ]
elif EP == 2:
    T_LOOP = 20.0
    LINES = [
        (0.05, 1.75, "A", "0.999… is SMALLER than 1. Obviously."),
        (1.90, 2.70, "B", "Is it though?"),
        (3.00, 4.40, "B", "Name ONE number between them."),
        (5.00, 6.20, "A", "uhh… 0.9999…5?"),
        (6.40, 7.70, "B", "Nope. The 9s never end."),
        (8.00, 8.70, "B", "Watch:"),
        (12.20, 12.95, "A", "…wait."),
        (16.30, 17.10, "B", "Told you."),
        (17.30, 18.60, "A", "My brain…"),
    ]
elif EP == 3:   # the 3 doors puzzle (Monty Hall) — no gambling words: a cake and two goats
    T_LOOP = 22.0
    LINES = [
        (0.05, 2.30, "B", "One door hides a cake. Two hide goats. Pick one!"),
        (2.40, 3.30, "A", "Door 1!"),
        (3.50, 5.20, "B", "Let me open a goat door for you…"),
        (5.60, 7.30, "B", "Want to SWITCH to door 2?"),
        (7.50, 9.40, "A", "Pfff. It's 50/50 now."),
        (9.60, 11.00, "B", "Nope. Switching doubles your chances."),
        (15.80, 16.90, "A", "…fine. I switch."),
        (17.40, 18.40, "A", "CAKE!!!"),
        (18.60, 20.00, "B", "Math beats your gut."),
        (20.50, 21.70, "A", "…and door 1 was a goat."),
    ]
elif EP == 4:   # ep 4: the birthday paradox
    T_LOOP = 24.5
    LINES = [
        (0.05, 2.20, "B", "How many people until two share a birthday?"),
        (2.40, 3.90, "A", "Easy. About 180. Half of 365!"),
        (4.20, 5.30, "B", "Let's add people."),
        (5.60, 6.80, "B", "Each new person must…"),
        (6.90, 8.30, "B", "…MISS every earlier birthday."),
        (12.70, 14.30, "A", "23 people?! Already 50%?!"),
        (16.20, 17.60, "B", "70 people: 99.9%."),
        (17.80, 19.30, "A", "But… there are 365 days!"),
        (19.50, 21.60, "B", "Not YOUR birthday. ANY two people."),
        (21.80, 22.90, "A", "…I need to sit down."),
    ]
elif EP == 5:   # fold a paper 42 times
    T_LOOP = 20.5
    LINES = [
        (0.05, 2.00, "B", "Fold this paper 42 times and it reaches the Moon."),
        (2.20, 3.40, "A", "Hahaha. No."),
        (3.60, 4.50, "B", "Let's fold."),
        (11.60, 12.60, "A", "Wait…"),
        (13.00, 14.20, "A", "WAIT."),
        (15.30, 17.20, "B", "42 folds = 439,805 km. The Moon is 384,400 km away."),
        (17.40, 18.80, "A", "I'm never folding anything again."),
    ]
elif EP == 6:   # a rope around the Earth, +1 m
    T_LOOP = 19.5
    LINES = [
        (0.05, 2.20, "B", "A rope hugs the whole Earth. Add just 1 meter."),
        (2.40, 3.50, "B", "How big is the gap now?"),
        (3.70, 5.20, "A", "Like… a thousandth of a millimeter?"),
        (7.00, 8.40, "B", "16 centimeters. All the way around."),
        (8.60, 9.60, "A", "WHAT?!"),
        (13.60, 15.00, "A", "And around a basketball?"),
        (15.20, 16.80, "B", "Also 16 cm. Same gap!"),
    ]
elif EP == 8:   # ep 8: how many ways up 10 stairs (1 or 2 at a time) — Fibonacci; he misses the bus
    T_LOOP = 18.0
    LINES = [
        (0.05, 1.60, "B", "Hurry up! The bus is leaving!"),
        (1.80, 3.80, "A", "Wait. 1 or 2 stairs at a time… how many ways up?"),
        (4.00, 4.90, "B", "JUST CLIMB!"),
        (8.40, 9.30, "B", "Hellooo?"),
        (12.40, 14.00, "A", "Each stair = the two below it. 89 ways!"),
        (14.40, 15.60, "A", "…and 0 buses."),
        (16.40, 17.70, "B", "Next bus! Still 89 ways."),
    ]
elif EP == 9:   # ep 9: racing a turtle (Zeno) — infinitely many steps, finite time
    T_LOOP = 15.0
    LINES = [
        (0.05, 1.70, "B", "The turtle gets a head start."),
        (1.90, 4.10, "B", "You can NEVER pass it: each time you reach its old spot, it has moved on!"),
        (8.40, 9.60, "A", "Infinite steps…"),
        (9.70, 11.20, "A", "…that add up to just a few seconds!"),
        (11.40, 12.70, "B", "…best of three?"),
    ]
elif EP == 10:  # ep 10: counting to a billion
    T_LOOP = 17.0
    LINES = [
        (0.05, 1.60, "A", "I'll count to a billion. Easy!"),
        (1.80, 3.30, "A", "1… 2… 3… 4… 5…"),
        (3.50, 5.00, "B", "One number per second. No sleep."),
        (12.60, 14.20, "A", "…999,999,999… ONE BILLION!"),
        (14.30, 15.70, "B", "It took you 31.7 years."),
    ]
elif EP == 11:  # ep 11: one 18-inch pizza vs two 12-inch pizzas
    T_LOOP = 16.5
    LINES = [
        (0.05, 1.80, "B", 'One 18" pizza, or two 12" pizzas?'),
        (2.00, 3.30, "A", "Two! Two is obviously more!"),
        (3.50, 4.70, "B", 'Then I\'ll take the 18".'),
        (8.80, 10.20, "A", "WAIT. Two is LESS?!"),
        (13.00, 14.50, "B", "Pizza is area: π·r². Double the size, 4× the pizza."),
        (14.70, 15.90, "A", "…I'm still hungry."),
    ]
elif EP == 12:  # ep 12: lily pads double every day
    T_LOOP = 16.0
    LINES = [
        (0.05, 1.80, "B", "These lily pads double every day."),
        (2.00, 3.60, "B", "On day 10 they cover the whole lake."),
        (3.80, 5.40, "A", "Cool. I'll fish until it's half full."),
        (9.60, 11.10, "A", "Day 9, only half full. Plenty of time!"),
        (12.10, 13.10, "A", "…oh."),
        (13.30, 15.00, "B", "Half full is ONE day from full."),
    ]
elif EP == 13:  # ep 13: the ant on a box — unfold it, draw a straight line
    T_LOOP = 17.0
    LINES = [
        (0.05, 1.90, "B", "The ant wants the honey on the far top corner."),
        (2.10, 3.90, "A", "Easy: across the front, then straight back!"),
        (6.80, 8.10, "B", "Shorter: unfold the box!"),
        (14.40, 15.90, "A", "…the ant is smarter than me."),
    ]
elif EP == 14:  # ep 14: counting to a TRILLION — a relay through history, Ice Age → flying cars
    T_LOOP = 18.6
    LINES = [
        (0.05, 1.90, "A", "Let's count to a TRILLION! 1… 2… 3…"),
        (5.10, 6.60, "A", "Pyramids already? We're at 83%!"),
        (12.40, 14.00, "A", "2026… 97.9%… still counting…"),
        (15.10, 16.50, "A", "…ONE TRILLION!"),
    ]
elif EP == 15:  # ep 15: counting to a QUINTILLION — Big Bang → today (43.5%) → the far future
    T_LOOP = 19.4
    LINES = [
        (0.05, 1.90, "A", "Big Bang! Let's count to a QUINTILLION! 1… 2… 3…"),
        (5.35, 6.85, "A", "Earth is born… only 29%!"),
        (8.75, 10.30, "A", "TODAY?! Only 43.5%?!"),
        (13.50, 14.70, "A", "Galaxies crashing… 58%…"),
        (16.30, 17.70, "A", "…ONE QUINTILLION!"),
    ]
elif EP == 16:  # ep 16: counting to a MILLION - 11.6 days without sleep
    T_LOOP = 17.0
    LINES = [
        (0.05, 1.75, "A", "I'll count to a MILLION. Easy!"),
        (1.95, 3.40, "A", "1… 2… 3… 4… 5…"),
        (3.60, 5.30, "B", "One number per second. No sleep."),
        (12.55, 14.15, "A", "…999,999… ONE MILLION!"),
        (14.25, 15.75, "B", "That took 11.6 days."),
    ]
elif EP == 17:  # ep 17: counting to a GOOGOL (a 1 with 100 zeros) - the Sun dies, the stars go out, still counting
    T_LOOP = 19.2
    LINES = [
        (0.05, 2.30, "A", "Let's count to a GOOGOL: a 1 with 100 zeros!"),
        (6.55, 8.05, "A", "…the SUN just died?!"),
        (10.20, 11.60, "A", "All the stars… gone."),
        (13.55, 14.95, "A", "…ONE GOOGOL!"),
        (15.10, 17.40, "B", "3 × 10⁹² years. The universe is only 13.8 billion."),
    ]
elif EP == 18:  # ep 18: count until the COMPUTER says "Infinity" (2^1024 ≈ 1.8 × 10^308: one past its biggest number)
    T_LOOP = 20.0
    LINES = [
        (0.05, 1.85, "A", "Count with me, computer!"),
        (11.00, 12.05, "B", "How are you still ALIVE?!"),
        (12.10, 13.30, "A", "Counting keeps me young."),
        (15.05, 16.05, "A", "INFINITY!!!"),
        (16.20, 17.55, "B", "Nope. Just 2¹⁰²⁴."),
    ]
elif EP == 19:  # ep 19: the potato paradox - 100 kg at 99% water, dried to 98% water = 50 kg
    T_LOOP = 19.0
    LINES = [
        (0.05, 2.40, "A", "100 kg of potatoes. 99% water."),
        (2.60, 4.50, "B", "Let them dry to 98% water."),
        (4.70, 6.20, "A", "Easy. About 99 kg left?"),
        (12.20, 13.40, "A", "50 KG?!"),
        (13.70, 16.40, "B", "The dry part is still 1 kg. Now 1 kg is 2%."),
    ]
elif EP == 20:  # ep 20: Zeno, zoomed - the camera zooms 2x per step so the race looks frozen; real time: 20 s
    T_LOOP = 20.0
    LINES = [
        (0.05, 2.30, "B", "Zeno: you can NEVER catch the turtle."),
        (5.40, 6.90, "A", "…am I even moving?"),
        (7.40, 9.70, "B", "Each step is half the last one. Forever."),
        (15.60, 17.40, "A", "Infinite steps. 20 seconds."),
    ]
else:           # ep 7: the infinite hotel
    T_LOOP = 20.0
    LINES = [
        (0.05, 1.80, "A", "One room, please!"),
        (2.00, 3.60, "B", "We're full. But we have INFINITELY many rooms…"),
        (3.80, 5.00, "B", "Everyone: room n → room n + 1!"),
        (6.80, 7.80, "A", "Nice! Room 1 for me!"),
        (8.60, 9.80, "A", "Uh oh. An infinite bus."),
        (10.00, 11.40, "B", "Easy. Everyone: room n → room 2n!"),
        (14.40, 16.00, "A", "So it was full… and had space… TWICE?!"),
        (16.20, 17.60, "B", "Welcome to infinity."),
    ]


LILY_DAYS = {1: 0.0, 2: 4.0, 3: 4.7, 4: 5.4, 5: 6.1, 6: 6.8, 7: 7.5, 8: 8.3, 9: 9.1, 10: 11.9}   # ep 12
WAYS = [1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89]   # ways to reach stair n (1 or 2 at a time)
STAIR_D = [0.95 - 0.05 * k for k in range(10)]  # the counting speeds up
STAIR_T = [4.9 + sum(STAIR_D[:k]) for k in range(11)]   # stair n is counted at STAIR_T[n]


_U = ["", "un", "duo", "tre", "quattuor", "quin", "se", "septe", "octo", "nove"]
_T = ["", "deci", "viginti", "triginta", "quadraginta", "quinquaginta", "sexaginta", "septuaginta", "octoginta",
      "nonaginta"]
_SMALL = ["", "m", "b", "tr", "quadr", "quint", "sext", "sept", "oct", "non"]


def illion(k):
    """Conway-Wechsler name of 10^(3k+3) (k = 1 -> million), k = 1..100 (100 = centillion)."""
    if k < 10:
        return _SMALL[k] + "illion"
    if k == 100:
        return "centillion"
    u, te = k % 10, k // 10
    pre = _U[u]
    if u == 3 and te in (2, 3, 4, 5, 8):
        pre = "tres"
    elif u == 6 and te in (2, 3, 4, 5):
        pre = "ses"
    elif u == 6 and te == 8:
        pre = "sex"
    elif u in (7, 9):
        pre = pre + ("m" if te in (2, 8) else "n")
    return (pre + _T[te])[:-1] + "illion"


EP18_LOG = [(1.9, 0.0), (4.4, 0.85), (6.0, 17.2), (7.2, 17.2), (8.2, 21.5), (9.2, 21.5), (10.3, 107.5),
            (12.9, 107.5), (13.9, 303.0), (14.6, 303.0), (15.0, 1024 * math.log10(2))]
EP18_RW0, EP18_RW1 = 17.7, 19.2


def ep18_L(t):
    """log10 of the count at time t (None = real-time counting 1, 2, 3 ...)."""
    if t < 4.4 or t >= EP18_RW1:
        return None
    if t >= EP18_RW0:
        return EP18_LOG[-1][1] * (1 - smooth((t - EP18_RW0) / (EP18_RW1 - EP18_RW0)))
    for (t0, v0), (t1, v1) in zip(EP18_LOG, EP18_LOG[1:]):
        if t0 <= t < t1:
            return v0 + (v1 - v0) * smooth((t - t0) / (t1 - t0))
    return EP18_LOG[-1][1]


# ep 19: grid of 100 one-kilo squares; index 44 is the dry kilo; 50 water squares evaporate (top rows first)
POT_DRY = 77
POT_GONE = [i for i in range(100) if i != POT_DRY][:50]             # evaporation order: top rows first
POT_T0, POT_T1, POT_RW0, POT_RW1 = 6.5, 12.0, 16.6, 18.4


def pot_gone_at(t):
    """number of water kilos evaporated by time t (accelerating), rewinding at the end."""
    if t < POT_T0:
        return 0.0
    if t < POT_T1:
        return 50.0 * ((t - POT_T0) / (POT_T1 - POT_T0)) ** 1.4
    if t < POT_RW0:
        return 50.0
    return 50.0 * (1 - smooth(min(1.0, (t - POT_RW0) / (POT_RW1 - POT_RW0))))


# ep 20: A 10 m/s from 0 m, the turtle 5 m/s from 100 m; they meet at 200 m after 20 s
ZEN_P0, ZEN_P1, ZEN_OUT, ZEN_R0, ZEN_R1, ZEN_RW0, ZEN_RW1 = 2.4, 10.2, 11.0, 11.0, 15.5, 17.6, 19.4
ZEN_STEPS = 6


def zeno_state(t):
    """-> (race time tau, zoom exponent p, mode)."""
    if t < ZEN_P0:
        return 0.0, 0.0, "start"
    if t < ZEN_P1:
        p = ZEN_STEPS * (t - ZEN_P0) / (ZEN_P1 - ZEN_P0)
        return 20 * (1 - 2 ** -p), p, "zeno"
    if t < ZEN_OUT:
        u = smooth((t - ZEN_P1) / (ZEN_OUT - ZEN_P1))
        return 20 * (1 - 2 ** -ZEN_STEPS) * (1 - u), ZEN_STEPS * (1 - u), "out"
    if t < ZEN_R1:
        return 30.0 * (t - ZEN_R0) / (ZEN_R1 - ZEN_R0), 0.0, "real"
    if t < ZEN_RW0:
        return 30.0, 0.0, "done"
    if t < ZEN_RW1:
        return 30.0 * (1 - smooth((t - ZEN_RW0) / (ZEN_RW1 - ZEN_RW0))), 0.0, "rewind"
    return 0.0, 0.0, "start"


def bus_dx(t, w):
    """Bus offset: parked → drives off right at 13.0 → the next one rolls in by 17.4 (= frame 0)."""
    if t < 13.0:
        return 0.0
    if t < 14.6:
        return w * 0.45 * smooth((t - 13.0) / 1.6) ** 2
    if t < 15.8:
        return w * 0.45
    return w * 0.45 * (1 - smooth((t - 15.8) / 1.6))


# ---------------------------------------------------------------- drawing helpers
def figure(c, x, gy, H, col, arm_l=(0.35, 0.2), arm_r=(0.35, 0.2), walk=0.0, mouth="smile", tilt=0.0,
           head_alpha=1.0, tear=0.0, dizzy=0.0, t=0.0, look=0.0):
    """Stick figure standing on ground y=gy. Arm angles are (upper, fore) from straight down, outward positive."""
    ctx = c.ctx
    lw = H * 0.045
    hip = (x, gy - 0.45 * H)
    sh = (x, gy - 0.76 * H)
    hc = (x + math.sin(tilt) * 0.12 * H, gy - 0.90 * H)
    hr = 0.115 * H
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)

    def seg(p, q, w=lw):
        ctx.move_to(*p)
        ctx.line_to(*q)
        ctx.set_source_rgb(*col)
        ctx.set_line_width(w)
        ctx.stroke()

    seg(hip, sh)
    for side, (a1, a2) in ((-1, arm_l), (1, arm_r)):           # arms
        e = (sh[0] + side * math.sin(a1) * 0.26 * H, sh[1] + math.cos(a1) * 0.26 * H)
        hnd = (e[0] + side * math.sin(a1 + a2) * 0.24 * H, e[1] + math.cos(a1 + a2) * 0.24 * H)
        seg(sh, e)
        seg(e, hnd)
    for side in (-1, 1):                                       # legs (walk cycle)
        ph = math.sin(walk * 2 * math.pi + (0 if side < 0 else math.pi))
        a = side * 0.22 + 0.45 * ph * (1 if walk else 0)
        k = (hip[0] + math.sin(a) * 0.24 * H, hip[1] + math.cos(a) * 0.24 * H)
        f = (k[0] + math.sin(a * 0.5) * 0.22 * H, gy)
        seg(hip, k)
        seg(k, f)
    if head_alpha > 0.01:
        ctx.new_path()
        ctx.arc(hc[0], hc[1], hr, 0, 2 * math.pi)
        ctx.set_source_rgba(0.05, 0.05, 0.09, head_alpha)
        ctx.fill_preserve()
        ctx.set_source_rgba(*col, head_alpha)
        ctx.set_line_width(lw)
        ctx.stroke()
        ex = hr * 0.38
        for s_ in (-1, 1):                                     # eyes
            ctx.new_path()
            ctx.arc(hc[0] + s_ * ex + look * hr * 0.25, hc[1] - hr * 0.15, hr * 0.11, 0, 2 * math.pi)
            ctx.set_source_rgba(1, 1, 1, head_alpha)
            ctx.fill()
        mx, my = hc[0] + look * hr * 0.2, hc[1] + hr * 0.38
        ctx.new_path()
        ctx.set_source_rgba(1, 1, 1, head_alpha)
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
        if tear > 0:
            ty = hc[1] + hr * (0.05 + 0.9 * (tear % 1.0))
            ctx.new_path()
            ctx.arc(hc[0] + ex, ty, hr * 0.1, 0, 2 * math.pi)
            ctx.set_source_rgba(0.5, 0.8, 1.0, head_alpha)
            ctx.fill()
        if dizzy > 0:                                          # orbiting stars
            for j in range(3):
                a = 2 * math.pi * (t * 1.2 + j / 3)
                sx, sy = hc[0] + hr * 1.5 * math.cos(a), hc[1] - hr * 1.2 + hr * 0.35 * math.sin(a)
                c.text_centered("*", sy + hr * 0.3, size=hr * 0.9, color=GOLD, alpha=dizzy, cx=sx)
    return {"hand_r": None, "head": hc, "hr": hr}


def hand_pos(x, gy, H, side, arm):
    a1, a2 = arm
    sh = (x, gy - 0.76 * H)
    e = (sh[0] + side * math.sin(a1) * 0.26 * H, sh[1] + math.cos(a1) * 0.26 * H)
    return e[0] + side * math.sin(a1 + a2) * 0.24 * H, e[1] + math.cos(a1 + a2) * 0.24 * H


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


def bubble(c, ax, ay, text, shown, col, w, fs):
    """Speech bubble whose tail points at (ax, ay) (top of the speaker's head); typewriter: first `shown` chars."""
    ctx = c.ctx
    ctx.select_font_face("Arial", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    ctx.set_font_size(fs)
    lines = wrap(ctx, text, w * 0.56)
    bw = max(ctx.text_extents(ln).x_advance for ln in lines) + fs * 1.2
    bh = len(lines) * fs * 1.25 + fs * 0.8
    bx = min(max(ax - bw / 2, w * 0.03), w * 0.97 - bw)
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


def cookie(c, x, y, r, alpha=1.0, bite=0.0):
    ctx = c.ctx
    ctx.new_path()
    ctx.arc(x, y, r, 0, 2 * math.pi)
    if bite > 0:
        ctx.new_sub_path()
        ctx.arc_negative(x + r * 0.8, y - r * 0.5, r * 0.55 * bite, 0, -2 * math.pi)
    ctx.set_fill_rule(cairo.FILL_RULE_EVEN_ODD)
    ctx.set_source_rgba(0.82, 0.58, 0.30, alpha)
    ctx.fill()
    ctx.set_fill_rule(cairo.FILL_RULE_WINDING)
    for dx, dy in ((-0.35, -0.25), (0.3, -0.1), (-0.1, 0.35), (0.4, 0.38), (-0.45, 0.25)):
        c.circle(x + dx * r, y + dy * r, r * 0.13, (0.30, 0.17, 0.08), alpha=alpha)


def parab(p, q, u, hgt):
    x = p[0] + (q[0] - p[0]) * u
    y = p[1] + (q[1] - p[1]) * u - hgt * 4 * u * (1 - u)
    return x, y


def poof(c, x, y, u, R):
    for j in range(10):
        a = 2 * math.pi * j / 10
        rr = R * (0.3 + u)
        c.circle(x + rr * math.cos(a), y + rr * math.sin(a), R * 0.25 * (1 - u), (0.9, 0.9, 1.0), alpha=0.7 * (1 - u))


def goat(c, x, gy, s, t):
    ctx = c.ctx
    by = gy - s * 0.42
    for lx in (-0.25, -0.1, 0.15, 0.3):                            # legs
        c.lines([(x + lx * s, by, x + lx * s, gy)], (0.85, 0.85, 0.85), width=s * 0.06)
    ctx.save()
    ctx.translate(x, by)
    ctx.scale(1, 0.55)
    ctx.arc(0, 0, s * 0.36, 0, 2 * math.pi)
    ctx.restore()
    ctx.set_source_rgb(0.92, 0.92, 0.9)
    ctx.fill()
    hx, hy = x - s * 0.36, by - s * 0.22 + s * 0.02 * math.sin(t * 6)
    c.circle(hx, hy, s * 0.13, (0.92, 0.92, 0.9))
    c.lines([(hx - s * 0.04, hy - s * 0.1, hx - s * 0.12, hy - s * 0.24),
             (hx + s * 0.05, hy - s * 0.1, hx + s * 0.1, hy - s * 0.24)], (0.6, 0.5, 0.4), width=s * 0.04)
    c.circle(hx - s * 0.04, hy - s * 0.02, s * 0.025, (0.1, 0.1, 0.1))
    c.lines([(hx - s * 0.02, hy + s * 0.12, hx - s * 0.04, hy + s * 0.22)], (0.85, 0.85, 0.85), width=s * 0.03)


def cake(c, x, gy, s, t):
    ctx = c.ctx
    for k, (wf, col) in enumerate(((1.0, (0.55, 0.32, 0.20)), (0.75, (1.0, 0.65, 0.75)))):
        ww, hh = s * wf, s * 0.22
        y = gy - hh * (k + 1)
        ctx.rectangle(x - ww / 2, y, ww, hh)
        ctx.set_source_rgb(*col)
        ctx.fill()
    c.lines([(x, gy - s * 0.44, x, gy - s * 0.62)], (0.95, 0.95, 1.0), width=s * 0.05)
    c.glow(x, gy - s * 0.67, s * 0.05, (1.0, 0.75, 0.3), strength=0.9, reach=3)
    c.circle(x, gy - s * 0.67 + s * 0.01 * math.sin(t * 20), s * 0.04, (1.0, 0.8, 0.3))


def fmt_len(m):
    if m < 0.01:
        return f"{m * 1000:.1f} mm"
    if m < 1:
        return f"{m * 100:.0f} cm"
    if m < 1000:
        return f"{m:.0f} m"
    return f"{m / 1000:,.0f} km"


def folds_at(t):
    if t < 4.6:
        return 0.0
    return 42.0 * min(1.0, (t - 4.6) / 10.4) ** 1.7


def cat(c, x, gy, s, t):
    """A crawling cat, height ~s (px)."""
    ctx = c.ctx
    col = (0.95, 0.65, 0.30)
    ctx.save()
    ctx.translate(x, gy - s * 0.55)
    ctx.scale(1, 0.45)
    ctx.arc(0, 0, s * 1.0, 0, 2 * math.pi)
    ctx.restore()
    ctx.set_source_rgb(*col)
    ctx.fill()
    hx, hy = x + s * 0.95, gy - s * 0.6
    c.circle(hx, hy, s * 0.38, col)
    for dx in (-0.25, 0.2):
        ctx.move_to(hx + dx * s, hy - s * 0.2)
        ctx.line_to(hx + (dx + 0.08) * s, hy - s * 0.62)
        ctx.line_to(hx + (dx + 0.2) * s, hy - s * 0.25)
        ctx.close_path()
        ctx.set_source_rgb(*col)
        ctx.fill()
    c.circle(hx + s * 0.12, hy - s * 0.05, s * 0.06, (0.1, 0.1, 0.1))
    step = math.sin(t * 14)
    for lx in (-0.6, -0.2, 0.3, 0.6):
        c.lines([(x + lx * s, gy - s * 0.35, x + lx * s + step * s * 0.12 * (1 if lx > 0 else -1), gy)], col,
                width=s * 0.14)
    c.lines([(x - s * 0.95, gy - s * 0.6, x - s * 1.5, gy - s * 1.0 + s * 0.15 * math.sin(t * 5))], col,
            width=s * 0.14)


T23 = 12.5
T70 = 16.0
PAIR = (5, 18)


def crowd_n(t):
    if t < 4.2:
        return 2
    if t < T23:
        return 2 + int(21 * ((t - 4.2) / (T23 - 4.2)) ** 1.8 + 1e-9)    # slow start: read the first fractions
    if t < T23 + 1.8:                               # hold on 23 while A reacts
        return 23
    if t < T70:
        return 23 + int(47 * smooth((t - T23 - 1.8) / (T70 - T23 - 1.8)) + 1e-9)
    return 70


def appear_t(i):
    if i < 2:
        return -1.0
    lo, hi = 0.0, T70
    for _ in range(40):
        mid = (lo + hi) / 2
        if crowd_n(mid) > i:
            hi = mid
        else:
            lo = mid
    return hi


def chance(n):
    q = 1.0
    for k in range(n):
        q *= (365 - k) / 365
    return 1 - q


def simulate():
    return {"nf": int(round(T_LOOP * FPS))}


class Scene:
    def __init__(self, layout, sim):
        self.L, self.sim = layout, sim
        self.canvas = Canvas(layout.w, layout.h, studio.render_scale())

    def bg(self):
        L, c = self.L, self.canvas
        w, h = L.w, L.h
        g = cairo.LinearGradient(0, 0, 0, h)
        g.add_color_stop_rgb(0, 0.07, 0.07, 0.13)
        g.add_color_stop_rgb(1, 0.02, 0.02, 0.04)
        c.ctx.set_source(g)
        c.ctx.paint()
        c.lines([(w * 0.04, self.gy, w * 0.96, self.gy)], (0.75, 0.78, 0.9), width=4, alpha=0.5)

    def say(self, t, who_pos):
        c, w, h = self.canvas, self.L.w, self.L.h
        for t0, t1, who, text in LINES:
            if t0 <= t < t1:
                shown = int((t - t0) * CPS)
                hx, hy = who_pos[who]
                bubble(c, hx, hy, text, shown, BLUE if who == "A" else ORANGE, w, w * 0.052)

    def bottom(self, txt, col, t_on, t, size=0.085):
        c, w, h = self.canvas, self.L.w, self.L.h
        pop = math.exp(-max(0.0, t - t_on) / 0.15)
        c.text_centered(txt, h * 0.765, size=w * size * (1 + 0.2 * pop), color=col, alpha=1.0)

    # ------------------------------------------------------------- episode 1
    def ep1(self, t):
        c, w, h = self.canvas, self.L.w, self.L.h
        gy, H = self.gy, self.H
        ax = w * 0.22
        arm_hold = (0.9, -1.2)                                     # right arm holding the plate forward
        mouth = "open" if any(t0 <= t < t1 and wh == "A" for t0, t1, wh, _ in LINES) and int(t * 8) % 2 else "smile"
        tilt, look, tear = 0.0, 0.0, 0.0
        arm_l, arm_r = (0.3, 0.2), arm_hold
        if t < 2.4:
            arm_l, arm_r = (2.2, 0.6), (2.2, 0.6)                   # shrug
        if 10.8 <= t < 11.6:
            look = math.sin((t - 10.8) * 2 * math.pi * 1.3)
        if t >= 18.4:
            mouth, tear = "sad", (t - 18.4) * 1.5
        figure(c, ax, gy, H, BLUE, arm_l, arm_r, mouth=mouth, tilt=tilt, look=look, tear=tear)
        plate = hand_pos(ax, gy, H, 1, arm_hold)
        pr = H * 0.06
        if t >= 2.4:
            ctx = c.ctx
            ctx.save()
            ctx.translate(plate[0] + H * 0.08, plate[1])
            ctx.scale(1, 0.25)
            ctx.arc(0, 0, H * 0.2, 0, 2 * math.pi)
            ctx.restore()
            ctx.set_source_rgba(0.85, 0.87, 0.95, 0.9)
            ctx.fill()
        slots = [(plate[0] + H * (-0.07 + 0.075 * (i % 3)), plate[1] - pr * (1.0 + 1.6 * (i // 3))) for i in range(6)]
        # friends
        fx3 = [w * 0.58, w * 0.72, w * 0.86]
        fH = H * 0.72
        if t < 2.4:                                                 # hook: the calculator says ERROR
            cx, cy = w * 0.62, gy - H * 0.55
            ctx = c.ctx
            ctx.rectangle(cx - H * 0.35, cy - H * 0.45, H * 0.7, H * 0.9)
            ctx.set_source_rgb(0.18, 0.19, 0.25)
            ctx.fill()
            ctx.rectangle(cx - H * 0.29, cy - H * 0.38, H * 0.58, H * 0.25)
            ctx.set_source_rgb(0.75, 0.85, 0.7)
            ctx.fill()
            err = t > 0.6 and int(t * 4) % 2 == 0
            c.text_centered("ERROR" if t > 0.6 else "6 ÷ 0", cy - H * 0.2, size=H * 0.13,
                            color=RED if err else (0.15, 0.2, 0.15), alpha=1.0, cx=cx)
            for i in range(3):
                for j in range(3):
                    c.circle(cx + (j - 1) * H * 0.17, cy + H * 0.05 + i * H * 0.13, H * 0.05, (0.5, 0.52, 0.6))
            self.bottom("6 ÷ 0 = ?", GOLD, 0.0, t)
            return
        # which friends are on stage and where the cookies are
        if t < 6.2:
            friends, give, t_fly, eq, t_eq = [0, 1, 2], [0, 0, 1, 1, 2, 2], 4.0, "6 ÷ 3 = 2", 5.0
        elif t < 9.4:
            friends, give, t_fly, eq, t_eq = [1], [1] * 6, 7.5, "6 ÷ 1 = 6", 8.4
        else:
            friends, give, t_fly, eq, t_eq = [], None, None, None, None
        for k in friends:
            app = min(1.0, (t - (2.6 if t < 6.2 else 6.2)) / 0.2)
            happy = t_eq is not None and t >= t_eq
            hop = abs(math.sin((t - t_eq) * 9)) * H * 0.06 if happy and t - t_eq < 1.0 else 0.0
            figure(c, fx3[k], gy - hop, fH * app, (0.65, 0.95, 0.6), (0.6 + (1.8 if happy else 0), 0.3),
                   (0.6 + (1.8 if happy else 0), 0.3), mouth="smile" if not happy else "open")
        if 9.4 <= t < 9.8:
            poof(c, fx3[1], gy - fH * 0.6, (t - 9.4) / 0.4, fH * 0.3)
        # cookies
        for i in range(6):
            p = slots[i]
            if give is not None and t >= t_fly + 0.12 * i:
                k = give[i]
                tgt = hand_pos(fx3[k], gy, fH, -1, (0.6, 0.3))
                cnt = give[:i].count(k)
                tgt = (tgt[0] + (cnt % 3) * pr * 1.2 - pr, tgt[1] - pr * 0.6 - (cnt // 3) * pr * 1.6)
                u = min(1.0, (t - t_fly - 0.12 * i) / 0.45)
                p = parab(p, tgt, smooth(u), H * 0.35)
            elif give is None and 11.3 <= t < 17.0:                # zero friends: cookies hover, confused
                u = smooth((t - 11.3) / 0.5)
                hov = (w * 0.50 + ((i % 3) - 1) * pr * 3.0 + math.sin(t * 3 + i) * pr * 0.5,
                       gy - H * 0.85 + (i // 3) * pr * 3.0 - pr * math.sin(t * 2.3 + i * 1.7))
                p = (p[0] + (hov[0] - p[0]) * u, p[1] + (hov[1] - p[1]) * u)
                if i % 2 == 0:
                    c.text_centered("?", p[1] - pr * 1.5, size=pr * 1.8, color=GOLD, alpha=0.9, cx=p[0])
            if t >= 17.0 and i == 5:                               # B takes one and eats it
                bxp = w * 0.74
                hand = hand_pos(bxp, gy, H, -1, (1.2, 0.9))
                if t < 19.6:
                    u = smooth((t - 17.0) / 0.6)
                    p = (p[0] + (hand[0] - p[0]) * u, p[1] + (hand[1] - p[1]) * u)
                else:
                    head = (bxp, gy - 0.9 * H)
                    u = smooth((t - 19.6) / 0.35)
                    p = (hand[0] + (head[0] - hand[0]) * u, hand[1] + (head[1] + H * 0.05 - hand[1]) * u)
                    bite = min(1.0, max(0.0, (t - 19.9) / 0.6)) * 1.6
                    if bite > 1.4:
                        continue
                    cookie(c, p[0], p[1], pr, bite=bite)
                    continue
            cookie(c, p[0], p[1], pr)
        if t >= 13.4:                                              # the teacher walks in
            bxp = w * 0.74 + (1 - smooth((t - 13.4) / 0.8)) * w * 0.45
            walking = t < 14.2
            talk = any(t0 <= t < t1 and wh == "B" for t0, t1, wh, _ in LINES) and int(t * 8) % 2
            armb = (1.2, 0.9) if t >= 17.0 else (0.3, 0.2)
            if t < 17.0:
                figure(c, bxp, gy, H, ORANGE, (0.3, 0.2), (0.3, 0.2),
                       walk=(t * 2.2 if walking else 0.0), mouth="open" if talk else "flat")
            else:                                                  # B reaches with the LEFT hand (towards A)
                figure(c, bxp, gy, H, ORANGE, (1.2, 0.9), (0.3, 0.2), mouth="open" if talk else "smile")
        if eq is not None and t >= t_eq:
            self.bottom(eq, GOLD, t_eq, t)
        elif 9.4 <= t < 15.2:
            self.bottom("6 ÷ 0 = ?", GOLD, 9.4, t)
        elif t >= 15.2:
            self.bottom("6 ÷ 0 = undefined", RED, 15.2, t, size=0.075)

    # ------------------------------------------------------------- episode 2
    def ep2(self, t):
        c, w, h = self.canvas, self.L.w, self.L.h
        gy, H = self.gy, self.H
        ax, bx = w * 0.22, w * 0.78
        talkA = any(t0 <= t < t1 and wh == "A" for t0, t1, wh, _ in LINES) and int(t * 8) % 2
        talkB = any(t0 <= t < t1 and wh == "B" for t0, t1, wh, _ in LINES) and int(t * 8) % 2
        exploded = 13.0 <= t < 14.6
        head_a = 0.0 if exploded else (1.0 if t < 13.0 else smooth((t - 14.6) / 0.3))
        dizzy = smooth((t - 14.6) / 0.3) if t >= 14.6 else 0.0
        armA = ((0.5, -2.2), (0.5, -2.2)) if t < 2.7 else ((0.3, 0.2), (0.3, 0.2))     # hands on hips
        if 12.2 <= t < 13.0:
            armA = ((2.6, 0.4), (2.6, 0.4))                         # hands to head
        figure(c, ax, gy, H, BLUE, *armA, mouth="open" if talkA else ("flat" if t > 7 else "smile"),
               head_alpha=head_a, dizzy=dizzy, t=t)
        armB = ((0.5, -2.2), (0.5, -2.2)) if t < 3.0 else (((0.3, 0.2), (2.3, 0.3)) if 8.0 <= t < 12.5 else
                                                             ((0.3, 0.2), (0.3, 0.2)))
        figure(c, bx, gy, H, ORANGE, *armB, mouth="open" if talkB else "smile")
        if exploded:                                               # head explosion
            u = (t - 13.0) / 1.6
            hc = (ax, gy - 0.9 * H)
            for j in range(26):
                a = 2 * math.pi * j / 26 + j
                r = H * (0.1 + 1.6 * u ** 0.6) * (0.6 + 0.4 * ((j * 7) % 5) / 4)
                px, py = hc[0] + r * math.cos(a), hc[1] + r * math.sin(a) + H * 1.2 * u * u
                if j % 3 == 0:
                    c.text_centered("9", py, size=H * 0.12, color=GOLD, alpha=1 - u, cx=px)
                else:
                    c.circle(px, py, H * 0.03 * (1 - u * 0.5), BLUE if j % 2 else (1.0, 0.85, 0.5), alpha=1 - u)
            c.glow(hc[0], hc[1], H * 0.2 * (1 - u), (1.0, 0.8, 0.4), strength=1.2 * (1 - u), reach=4)
        # the board (number line, then the 1/3 proof)
        top, bot = h * 0.245, h * 0.43
        if 2.8 <= t < 8.0:
            k = min(4, int((t - 2.8) / 1.1))
            u = smooth(((t - 2.8) - 1.1 * k) / 0.5)
            lo_from = 1 - 10 ** -(k) if k > 0 else 0.8
            lo_to = 1 - 10 ** -(k + 1)
            x0, x1 = w * 0.08, w * 0.92
            yl = h * 0.325
            c.lines([(x0, yl, x1, yl)], (0.85, 0.87, 0.95), width=7, alpha=0.85)
            v_dot = lo_from + (lo_to - lo_from) * u                 # the "0.99…" dot slides toward 1
            lo = 1 - 10 ** -(k) * 1.25 if k > 0 else 0.85
            X = lambda v: x0 + (x1 - x0) * (v - lo) / (1 - lo)       # noqa: E731
            c.circle(X(1.0), yl, 12, GOLD)
            c.text_centered("1", yl - h * 0.022, size=w * 0.06, color=GOLD, cx=X(1.0) - w * 0.02)
            label = "0." + "9" * (k + 1)
            c.circle(X(v_dot), yl, 12, BLUE)
            c.text_centered(label, yl - h * 0.022, size=w * 0.055, color=BLUE, cx=max(w * 0.2, X(v_dot) - w * 0.16))
            gap = 10 ** -(k + 1)
            c.text_centered(f"gap = {gap:.{k + 1}f}".rstrip("0") if k < 4 else "gap = 0.00001",
                            h * 0.255, size=w * 0.05, color=(0.9, 0.9, 0.95), alpha=0.95)
            self.bottom("0.999… = 1 ?", GOLD, 2.8, t, size=0.08)
        elif 8.0 <= t < 13.0:
            rows = [(8.2, "1/3  =  0.333…", (0.95, 0.95, 1.0)), (9.4, "× 3          × 3", (0.75, 0.78, 0.9)),
                    (10.6, "3/3  =  0.999…", (0.95, 0.95, 1.0)), (11.8, "1  =  0.999…", GOLD)]
            for i, (tr, txt, col) in enumerate(rows):
                if t >= tr:
                    pop = math.exp(-(t - tr) / 0.15)
                    c.text_centered(txt, h * 0.255 + h * 0.042 * i, size=w * 0.065 * (1 + 0.15 * pop), color=col)
            self.bottom("0.999… = 1 ?", GOLD, 0, t, size=0.08)
        elif t < 2.8:
            self.bottom("0.999… = 1 ?", GOLD, 0.0, t, size=0.08)
        else:
            self.bottom("0.999… = 1", GOLD, 16.0, t, size=0.09)

    # ------------------------------------------------------------- episode 3 (doors)
    def door(self, x, gy, dw, dh, num, open_u, inside, marked):
        c = self.canvas
        ctx = c.ctx
        x0, y0 = x - dw / 2, gy - dh
        ctx.rectangle(x0, y0, dw, dh)
        ctx.set_source_rgb(0.06, 0.06, 0.10)
        ctx.fill()
        if open_u > 0.3:
            if inside == "goat":
                goat(c, x, gy - dh * 0.05, dw * 0.8, self.t)
            else:
                cake(c, x, gy - dh * 0.05, dw * 0.7, self.t)
        wv = dw * (1 - open_u * 0.85)                              # door panel swings open (hinge on the left)
        ctx.rectangle(x0, y0, wv, dh)
        ctx.set_source_rgb(0.55, 0.33, 0.18)
        ctx.fill_preserve()
        ctx.set_source_rgb(0.30, 0.17, 0.08)
        ctx.set_line_width(4)
        ctx.stroke()
        if open_u < 0.5:
            c.text_centered(str(num), y0 + dh * 0.45, size=dw * 0.5, color=(1.0, 0.9, 0.7), alpha=1 - open_u * 2,
                            cx=x0 + wv / 2)
            c.circle(x0 + wv * 0.85, y0 + dh * 0.55, dw * 0.04, GOLD)
        if marked:
            ctx.rectangle(x0 - 6, y0 - 6, dw + 12, dh + 12)
            ctx.set_source_rgba(*BLUE, 0.95)
            ctx.set_line_width(7)
            ctx.stroke()
            c.glow(x, y0 - dh * 0.12, 12, BLUE, strength=0.8, reach=3)
            c.text_centered("A", y0 - dh * 0.06, size=dw * 0.25, color=BLUE, cx=x)

    def ep3(self, t):
        c, w, h = self.canvas, self.L.w, self.L.h
        gy, H = self.gy, self.H
        self.t = t
        ax, bx = w * 0.12, w * 0.88
        dx = [w * 0.33, w * 0.50, w * 0.67]
        dw, dh = w * 0.15, h * 0.21
        contents = ["goat", "cake", "goat"]
        open3 = smooth((t - 4.6) / 0.4)
        open2 = smooth((t - 17.2) / 0.4)
        open1 = smooth((t - 20.5) / 0.4)
        pick = 0 if t < 16.0 else 1
        for i in range(3):
            o = (open1, open2, open3)[i]
            self.door(dx[i], gy, dw, dh, i + 1, o, contents[i], marked=(t >= 2.4 and i == pick and o < 0.5))
        talkA = any(t0 <= t < t1 and wh == "A" for t0, t1, wh, _ in LINES) and int(t * 8) % 2
        talkB = any(t0 <= t < t1 and wh == "B" for t0, t1, wh, _ in LINES) and int(t * 8) % 2
        happy = 17.2 <= t < 20.5
        hop = abs(math.sin((t - 17.2) * 9)) * H * 0.07 if happy and t < 18.4 else 0.0
        armA = ((0.3, 0.2), (1.5, 0.0)) if 2.4 <= t < 3.6 or 16.0 <= t < 16.9 else ((0.3, 0.2), (0.3, 0.2))
        if happy:
            armA = ((2.6, 0.3), (2.6, 0.3))
        if 7.5 <= t < 9.4:
            armA = ((2.2, 0.6), (2.2, 0.6))                         # shrug
        moodA = "open" if talkA else ("smile" if not (20.5 <= t) else "flat")
        figure(c, ax, gy - hop, H, BLUE, *armA, mouth=moodA)
        armB = ((1.5, 0.0), (0.3, 0.2)) if (0.0 <= t < 2.3 or 3.5 <= t < 5.2 or 5.6 <= t < 7.3) else \
            (((0.3, 0.2), (2.3, 0.3)) if 9.6 <= t < 15.6 else ((0.3, 0.2), (0.3, 0.2)))
        figure(c, bx, gy, H, ORANGE, *armB, mouth="open" if talkB else "smile")
        if happy and t < 18.6:                                     # confetti
            u = t - 17.2
            for j in range(40):
                a = j * 2.4
                x = dx[1] + math.cos(a) * w * 0.25 * min(1.0, u * 2) * ((j % 7) / 7 + 0.3)
                y = gy - dh - h * 0.05 + h * 0.20 * u * u - math.sin(a) * h * 0.08 * min(1.0, u * 2)
                c.circle(x, y, 6, studio.hsv(j / 40, 0.6, 1.0), alpha=max(0.0, 1 - u / 1.4))
        if 11.2 <= t < 15.6:                                       # the three cases
            rows = [(11.2, "cake behind 1 → STAY gets it", BLUE), (12.4, "cake behind 2 → SWITCH gets it", ORANGE),
                    (13.6, "cake behind 3 → SWITCH gets it", ORANGE), (14.8, "switch: 2 out of 3!", GOLD)]
            for i, (tr, txt, col) in enumerate(rows):
                if t >= tr:
                    pop = math.exp(-(t - tr) / 0.15)
                    c.text_centered(txt, h * 0.255 + h * 0.042 * i, size=w * 0.05 * (1 + 0.12 * pop), color=col)
        if t < 7.5:
            self.bottom("SWITCH or STAY?", GOLD, 0.0, t, size=0.08)
        elif t < 9.6:
            self.bottom("50 / 50 ?", GOLD, 7.5, t, size=0.08)
        elif t < 17.2:
            self.bottom("stay = 1/3 · switch = 2/3", GOLD, 9.6, t, size=0.065)
        else:
            self.bottom("always switch", GOLD, 17.2, t, size=0.08)

    # ------------------------------------------------------------- episode 4 (birthdays)
    def ep4(self, t):
        c, w, h = self.canvas, self.L.w, self.L.h
        gy, H = self.gy, self.H
        ax, bx = w * 0.12, w * 0.88
        n = crowd_n(t)
        cols, rh, sH = 10, h * 0.042, h * 0.052
        for i in range(n):
            r, k = i // cols, i % cols
            x = w * (0.27 + 0.46 * (k + 0.5 * (r % 2)) / cols)
            pair = i in PAIR and t >= T23
            colr = GOLD if pair else studio.hsv((i * 0.137) % 1.0, 0.35, 0.95)
            age = t - appear_t(i)
            s = min(1.0, max(0.0, age / 0.12))
            figure(c, x, gy - r * rh, sH * s, colr, (0.3, 0.2), (0.3, 0.2), mouth="smile")
            if pair:
                c.glow(x, gy - r * rh - sH * 0.9, sH * 0.18, GOLD, strength=0.6, reach=2.2)
                c.text_centered("MAR 14", gy - r * rh - sH * 1.25, size=w * 0.036, color=GOLD, cx=x)
        talkA = any(t0 <= t < t1 and wh == "A" for t0, t1, wh, _ in LINES) and int(t * 8) % 2
        talkB = any(t0 <= t < t1 and wh == "B" for t0, t1, wh, _ in LINES) and int(t * 8) % 2
        fall = smooth((t - 23.0) / 0.45) if t >= 23.0 else 0.0
        ctx = c.ctx
        ctx.save()
        ctx.translate(ax, gy)
        ctx.rotate(math.pi / 2 * fall)                           # falls over towards the crowd
        ctx.translate(-ax, -gy)
        shock = T23 <= t < T23 + 2.0 or 17.8 <= t < 19.3
        armA = ((2.6, 0.4), (2.6, 0.4)) if shock else ((0.3, 0.2), (0.3, 0.2))
        figure(c, ax, gy, H, BLUE, *armA, mouth="open" if (talkA or shock) else ("flat" if t > 9.5 else "smile"),
               dizzy=fall, t=t)
        ctx.restore()
        armB = ((1.5, 0.0), (0.3, 0.2)) if 4.2 <= t < 5.3 else ((0.3, 0.2), (0.3, 0.2))
        figure(c, bx, gy, H, ORANGE, *armB, mouth="open" if talkB else "smile")
        p = chance(n)                                              # the board: people + the chance bar
        c.text_centered(f"people: {n}", h * 0.224, size=w * 0.055, color=(0.97, 0.97, 1.0))
        x0, x1, yb = w * 0.12, w * 0.88, h * 0.250
        c.lines([(x0, yb, x1, yb)], (0.4, 0.42, 0.55), width=22, alpha=0.8)
        if p > 0.002:
            c.lines([(x0, yb, x0 + (x1 - x0) * p, yb)], GOLD if p >= 0.5 else (0.55, 0.85, 1.0), width=22)
        # how the chance is calculated: multiply the chances that each new person MISSES all earlier birthdays
        miss = 1 - p
        if n <= 2:
            prod = "365/365 × 364/365"
        elif n == 3:
            prod = "365/365 × 364/365 × 363/365"
        else:
            prod = f"365/365 × 364/365 × … × {366 - n}/365"
        c.text_centered(f"no match = {prod}", h * 0.281, size=w * 0.037, color=(0.9, 0.9, 0.96), bold=False,
                        max_w=w * 0.96)
        c.text_centered(f"= {100 * miss:.1f} %", h * 0.306, size=w * 0.04, color=(0.9, 0.9, 0.96), bold=False)
        c.text_centered(f"match = 100 % − {100 * miss:.1f} % = {100 * p:.1f} %", h * 0.335, size=w * 0.042,
                        color=GOLD)
        if t < T23:
            self.bottom("how many people?", GOLD, 0.0, t, size=0.075)
        elif t < 19.5:
            self.bottom("23 people → 50 %", GOLD, T23, t, size=0.08)
        else:
            self.bottom("23 people = 253 pairs", GOLD, 19.5, t, size=0.075)

    # ------------------------------------------------------------- episode 5 (paper to the Moon)
    def ep5(self, t):
        c, w, h = self.canvas, self.L.w, self.L.h
        gy = self.gy
        nf = folds_at(t)
        n = int(nf + 1e-9)
        Hm = 0.0001 * 2 ** nf
        V = max(4.0, min(Hm, 4.4e8) * 1.25)
        top = h * 0.22
        Y = lambda m: gy - (m / V) * (gy - top)                   # noqa: E731
        ctx = c.ctx
        for m, label in ((8, "a house"), (828, "the tallest building"), (11000, "planes fly here"),
                         (100000, "space starts here"), (408000, "space station"), (384400000, "THE MOON")):
            y = Y(m)
            if not (top - 5 < y < gy - h * 0.02) or m / V < 0.015:
                continue
            a = min(1.0, (m / V - 0.015) / 0.05)
            c.lines([(w * 0.04, y, w * 0.96, y)], (0.75, 0.78, 0.9), width=2, alpha=0.35 * a)
            c.text_centered(f"{label}: {fmt_len(m)}", y - h * 0.008, size=w * 0.033, color=(0.9, 0.9, 0.96),
                            alpha=0.9 * a, bold=False, cx=w * 0.74)
            if m == 384400000:
                c.glow(w * 0.24, y, w * 0.07, (0.95, 0.95, 0.85), strength=0.5, reach=2.5)
                c.circle(w * 0.24, y, w * 0.07, (0.92, 0.92, 0.86))
                for dx, dy, r in ((-0.02, -0.02, 0.015), (0.025, 0.01, 0.01), (0.0, 0.03, 0.012)):
                    c.circle(w * (0.24 + dx), y + w * dy, w * r, (0.75, 0.75, 0.7))
        hp = max(10.0, (gy - Y(Hm)))
        xc, cw = w * 0.5, w * 0.05
        ctx.rectangle(xc - cw / 2, gy - hp, cw, hp)
        ctx.set_source_rgb(0.96, 0.96, 0.98)
        ctx.fill()
        if n < 8:
            for k in range(1, 2 ** n):
                yy = gy - hp * k / 2 ** n
                c.lines([(xc - cw / 2, yy, xc + cw / 2, yy)], (0.6, 0.62, 0.7), width=1.5, alpha=0.8)
        if t >= 4.6 and t < 15.2:
            c.glow(xc, gy - hp, 10, GOLD, strength=0.6, reach=3)
        Hpx = 1.8 / V * (gy - top)                                 # the stick figures shrink as we zoom out
        talkA = any(t0 <= t < t1 and wh == "A" for t0, t1, wh, _ in LINES) and int(t * 8) % 2
        talkB = any(t0 <= t < t1 and wh == "B" for t0, t1, wh, _ in LINES) and int(t * 8) % 2
        ax, bx = w * 0.30, w * 0.74
        if Hpx > 3:
            shock = 11.6 <= t < 14.5
            figure(c, ax, gy, Hpx, BLUE, (0.3, 0.2), (1.1, -0.6) if not shock else (2.6, 0.4),
                   mouth="open" if (talkA or shock) else "smile")
            figure(c, bx, gy, Hpx, ORANGE, (0.3, 0.2), (0.3, 0.2), mouth="open" if talkB else "smile")
        self.pos = {"A": (ax, min(gy - h * 0.12, gy - Hpx * 1.05)), "B": (bx, min(gy - h * 0.12, gy - Hpx * 1.05))}
        if t < 15.2:
            c.text_centered(f"folds: {n}", h * 0.745, size=w * 0.07, color=(0.97, 0.97, 1.0))
            c.text_centered(f"0.1 mm × 2^{n} = {fmt_len(0.0001 * 2 ** n)}", h * 0.79, size=w * 0.05, color=GOLD)
        else:
            self.bottom("2^42 × 0.1 mm = 439,805 km", GOLD, 15.2, t, size=0.062)
            c.text_centered("(in theory: real paper stops at about 7 folds)", h * 0.80, size=w * 0.032,
                            color=(0.75, 0.78, 0.88), bold=False)

    # ------------------------------------------------------------- episode 6 (rope around the Earth)
    def ep6(self, t):
        c, w, h = self.canvas, self.L.w, self.L.h
        gy, H = self.gy, self.H
        ctx = c.ctx
        cx, cy = w / 2, h * 0.40
        if t < 5.5:                                                # the Earth with its rope
            R = w * 0.25
            g = cairo.RadialGradient(cx - R * 0.3, cy - R * 0.3, R * 0.1, cx, cy, R)
            g.add_color_stop_rgb(0, 0.35, 0.65, 1.0)
            g.add_color_stop_rgb(1, 0.10, 0.25, 0.60)
            ctx.arc(cx, cy, R, 0, 2 * math.pi)
            ctx.set_source(g)
            ctx.fill()
            for dx, dy, r in ((-0.3, -0.2, 0.35), (0.35, 0.25, 0.28), (0.1, -0.55, 0.2)):
                c.circle(cx + dx * R, cy + dy * R, r * R, (0.30, 0.70, 0.35), alpha=0.85)
            ctx.new_path()
            ctx.arc(cx, cy, R + 4, 0, 2 * math.pi)
            ctx.set_source_rgb(*GOLD)
            ctx.set_line_width(5)
            ctx.stroke()
            if t >= 2.0:
                pop = math.exp(-(t - 2.0) / 0.2)
                c.text_centered("+ 1 m", cy - R - h * 0.02, size=w * 0.06 * (1 + 0.3 * pop), color=GOLD)
            c.text_centered("40,075 km around", cy + h * 0.008, size=w * 0.04, color=(1, 1, 1), alpha=0.9)
        elif t < 10.0:                                             # close-up: the gap, and a cat crawls under it
            yg = h * 0.43
            pxm = h * 0.75                                         # px per metre in the close-up
            ctx.rectangle(0, yg, w, h * 0.05)
            ctx.set_source_rgb(0.30, 0.62, 0.32)
            ctx.fill()
            yr = yg - 0.159 * pxm
            c.lines([(0, yr, w, yr)], GOLD, width=6)
            c.lines([(w * 0.86, yg, w * 0.86, yr)], (1, 1, 1), width=3)
            c.text_centered("16 cm", (yg + yr) / 2 + h * 0.01, size=w * 0.045, color=(1, 1, 1), cx=w * 0.75)
            if t >= 7.0:
                cat(c, -w * 0.15 + (t - 7.0) / 3.0 * w * 1.2, yg, 0.12 * pxm, t)
            c.text_centered("zoomed in to the ground", h * 0.25, size=w * 0.04, color=(0.8, 0.82, 0.92), bold=False)
        elif t < 13.6:                                             # why: the formula
            rows = [(10.0, "rope = 2π × radius", (0.95, 0.95, 1.0)),
                    (11.2, "+1 m of rope → radius + 1 m ÷ 2π", (0.95, 0.95, 1.0)),
                    (12.4, "1 ÷ 6.28 = 0.159 m ≈ 16 cm", GOLD)]
            for i, (tr, txt, col) in enumerate(rows):
                if t >= tr:
                    pop = math.exp(-(t - tr) / 0.15)
                    c.text_centered(txt, h * 0.26 + h * 0.05 * i, size=w * 0.055 * (1 + 0.12 * pop), color=col)
        else:                                                      # the basketball: the same 16 cm gap
            r = w * 0.06
            rr = r * (0.12 + 0.159) / 0.12
            c.circle(cx, cy, r, (0.95, 0.55, 0.20))
            c.lines([(cx - r, cy, cx + r, cy), (cx, cy - r, cx, cy + r)], (0.3, 0.15, 0.05), width=3)
            ctx.new_path()
            ctx.arc(cx, cy, rr, 0, 2 * math.pi)
            ctx.set_source_rgb(*GOLD)
            ctx.set_line_width(5)
            ctx.stroke()
            c.text_centered("basketball + 1 m of rope", cy - rr - h * 0.02, size=w * 0.04, color=(0.9, 0.9, 0.96),
                            bold=False)
        talkA = any(t0 <= t < t1 and wh == "A" for t0, t1, wh, _ in LINES) and int(t * 8) % 2
        talkB = any(t0 <= t < t1 and wh == "B" for t0, t1, wh, _ in LINES) and int(t * 8) % 2
        shock = 8.6 <= t < 9.8
        figure(c, w * 0.12, gy, H, BLUE, *(((2.6, 0.4), (2.6, 0.4)) if shock else ((0.3, 0.2), (0.3, 0.2))),
               mouth="open" if (talkA or shock) else "smile")
        armB = ((0.3, 0.2), (2.3, 0.3)) if 10.0 <= t < 13.6 else ((0.3, 0.2), (0.3, 0.2))
        figure(c, w * 0.88, gy, H, ORANGE, *armB, mouth="open" if talkB else "smile")
        if t < 5.5:
            self.bottom("rope + 1 m → gap = ?", GOLD, 0.0, t, size=0.072)
        elif t < 13.6:
            self.bottom("gap = 16 cm", GOLD, 5.5, t)
        else:
            self.bottom("ANY ball: 1 m ÷ 2π = 16 cm", GOLD, 13.6, t, size=0.06)

    # ------------------------------------------------------------- episode 7 (the infinite hotel)
    def ep7(self, t):
        c, w, h = self.canvas, self.L.w, self.L.h
        gy, H = self.gy, self.H
        ctx = c.ctx
        top, rh = h * 0.235, h * 0.12
        rw = w * 0.092

        def rx(k):
            return w * (0.04 + 0.1 * (k - 1)) + rw / 2

        for k in range(1, 10):                                     # the rooms
            x0 = rx(k) - rw / 2
            ctx.rectangle(x0, top, rw, rh)
            ctx.set_source_rgb(0.22, 0.20, 0.30)
            ctx.fill()
            c.text_centered(str(k), top + rh * 0.22, size=w * 0.035, color=(0.95, 0.85, 0.6), cx=rx(k))
        c.text_centered("… ∞", top + rh * 0.62, size=w * 0.05, color=(0.95, 0.85, 0.6), cx=w * 0.975)
        c.text_centered("HOTEL INFINITY", top - h * 0.012, size=w * 0.04, color=GOLD)

        def guest(k_from, k_to, t0, dur, col, label=None):
            u = smooth((t - t0) / dur) if t >= t0 else 0.0
            k = k_from + (k_to - k_from) * u
            x = rx(1) + (k - 1) * w * 0.1
            y = top + rh * 0.68 - math.sin(math.pi * u) * rh * 0.5
            if -w * 0.05 < x < w * 0.97:
                c.circle(x, y, rw * 0.22, col)
                c.circle(x - rw * 0.07, y - rw * 0.04, rw * 0.04, (0.1, 0.1, 0.15))
                c.circle(x + rw * 0.07, y - rw * 0.04, rw * 0.04, (0.1, 0.1, 0.15))
                if label:
                    c.text_centered(label, y + rw * 0.45, size=w * 0.03, color=col, cx=x)

        S1, S2, BUS = 5.0, 11.4, 12.8
        for i in range(1, 25):                                     # the original guests
            r0, r1, r2 = i, i + 1, 2 * (i + 1)
            col = studio.hsv((i * 0.137) % 1, 0.4, 0.95)
            if t < S2:
                guest(r0, r1, S1, 1.0, col)
            else:
                guest(r1, r2, S2, 1.2, col)
        if t >= 6.0:                                               # A gets room 1 (then room 2)
            if t < S2:
                guest(0.0 if t < 6.6 else 1, 1, 6.0, 0.6, BLUE, "A")
            else:
                guest(1, 2, S2, 1.2, BLUE, "A")
        if t >= BUS:                                               # the bus guests fill the odd rooms
            for j in range(12):
                guest(12.0 + j, 2 * j + 1, BUS + 0.06 * j, 1.0, (0.55, 1.0, 0.55))
        if 8.0 <= t < BUS + 1.2:                                   # the infinite bus
            bx = w * 0.5 + (1 - smooth((t - 8.0) / 0.8)) * w * 0.8 - smooth((t - BUS) / 1.0) * w * 0.9
            ctx.rectangle(bx - w * 0.2, gy - h * 0.11, w * 0.4, h * 0.09)
            ctx.set_source_rgb(0.95, 0.75, 0.2)
            ctx.fill()
            for k in range(4):
                ctx.rectangle(bx - w * 0.18 + k * w * 0.09, gy - h * 0.10, w * 0.07, h * 0.035)
                ctx.set_source_rgb(0.4, 0.6, 0.8)
                ctx.fill()
            c.text_centered("∞ guests", gy - h * 0.035, size=w * 0.04, color=(0.2, 0.15, 0.05), cx=bx)
            for dx in (-0.13, 0.13):
                c.circle(bx + dx * w, gy - h * 0.012, h * 0.016, (0.15, 0.15, 0.2))
        talkA = any(t0 <= t < t1 and wh == "A" for t0, t1, wh, _ in LINES) and int(t * 8) % 2
        talkB = any(t0 <= t < t1 and wh == "B" for t0, t1, wh, _ in LINES) and int(t * 8) % 2
        dizzy = smooth((t - 17.6) / 0.3) if t >= 17.6 else 0.0
        shock = 14.4 <= t < 16.0 or 8.6 <= t < 9.8
        figure(c, w * 0.12, gy, H, BLUE, *(((2.6, 0.4), (2.6, 0.4)) if shock else ((0.3, 0.2), (0.6, -0.9))),
               mouth="open" if (talkA or shock) else "smile", dizzy=dizzy, t=t)
        if not shock:                                              # A's suitcase
            ctx.rectangle(w * 0.155, gy - h * 0.075, w * 0.06, h * 0.045)
            ctx.set_source_rgb(0.6, 0.35, 0.2)
            ctx.fill()
        armB = ((1.5, 0.0), (0.3, 0.2)) if (3.8 <= t < 5.0 or 10.0 <= t < 11.4) else ((0.3, 0.2), (0.3, 0.2))
        figure(c, w * 0.88, gy, H, ORANGE, *armB, mouth="open" if talkB else "smile")
        if t < S1:
            self.bottom("a FULL hotel…", GOLD, 0.0, t)
        elif t < S2:
            self.bottom("room n → room n + 1", GOLD, S1, t, size=0.07)
        elif t < 17.0:
            self.bottom("room n → room 2n", GOLD, S2, t, size=0.07)
        else:
            self.bottom("∞ + 1 = ∞ + ∞ = ∞", GOLD, 17.0, t, size=0.075)

    # ------------------------------------------------------------- episode 8 (stairs, Fibonacci, the bus)
    def ep8(self, t):
        c, w, h = self.canvas, self.L.w, self.L.h
        gy = self.gy
        ctx = c.ctx
        x0, run, top = w * 0.17, w * 0.063, h * 0.43
        rise = (gy - top) / 10
        sx = lambda n: x0 + n * run                                # noqa: E731  left edge of stair n+1
        sy = lambda n: gy - n * rise                               # noqa: E731  top of stair n
        pts = [(sx(0), gy)]
        for n in range(1, 11):
            pts += [(sx(n - 1), sy(n)), (sx(n), sy(n))]
        pts += [(w * 0.985, sy(10)), (w * 0.985, gy)]
        ctx.new_path()
        ctx.move_to(*pts[0])
        for q in pts[1:]:
            ctx.line_to(*q)
        ctx.close_path()
        ctx.set_source_rgb(0.13, 0.13, 0.20)
        ctx.fill()
        c.polylines([pts[:-1]], (0.75, 0.78, 0.9), width=4, alpha=0.7)
        # the bus on the top landing, driver B in the window
        dx = bus_dx(t, w)
        bx, by, bw, bh = w * 0.795 + dx, sy(10) - h * 0.075, w * 0.19, h * 0.062
        bob = math.sin(t * 22) * h * 0.0015                        # idling engine
        ctx.new_path()
        r = bh * 0.18
        ctx.arc(bx + bw - r, by + r + bob, r, -math.pi / 2, 0)
        ctx.line_to(bx + bw, by + bh + bob)
        ctx.line_to(bx, by + bh + bob)
        ctx.arc(bx + r, by + r + bob, r, math.pi, 1.5 * math.pi)
        ctx.close_path()
        ctx.set_source_rgb(0.98, 0.76, 0.22)
        ctx.fill()
        for k in range(3):
            ctx.rectangle(bx + bw * (0.07 + 0.3 * k), by + bh * 0.15 + bob, bw * 0.24, bh * 0.38)
            ctx.set_source_rgb(0.55, 0.75, 0.92)
            ctx.fill()
        hx, hy = bx + bw * 0.19, by + bh * 0.36 + bob
        c.circle(hx, hy, bh * 0.13, ORANGE)
        talkB = any(t0 <= t < t1 and wh == "B" for t0, t1, wh, _ in LINES) and int(t * 8) % 2
        ctx.new_path()
        ctx.arc(hx, hy + bh * 0.03, bh * (0.05 if talkB else 0.035), 0, math.pi)
        ctx.set_source_rgb(0.1, 0.1, 0.12)
        ctx.fill()
        for k in (0.22, 0.78):
            c.circle(bx + bw * k, by + bh + bob, bh * 0.16, (0.12, 0.12, 0.15))
            c.circle(bx + bw * k, by + bh + bob, bh * 0.07, (0.6, 0.6, 0.65))
        # the counts on the stairs (fade out before the seam: frame 0 has none)
        fade = 1 - smooth((t - (T_LOOP - 1.4)) / 0.6)
        n_now = max([n for n in range(11) if STAIR_T[n] <= t], default=-1)
        counting = 0 <= n_now and t < STAIR_T[10] + 0.6
        for n in range(11):
            if t < STAIR_T[n] or fade <= 0:
                continue
            pop = math.exp(-(t - STAIR_T[n]) / 0.15)
            lx = (sx(n - 1) + sx(n)) / 2 if n else x0 - run * 0.4
            col = GOLD if n == 10 else (1, 1, 1)
            if pop > 0.05:
                c.glow(lx, sy(n) - h * 0.02, w * 0.03, GOLD, strength=0.6 * pop, reach=2.5)
            c.text_centered(str(WAYS[n]), sy(n) - h * 0.008, size=w * 0.042 * (1 + 0.35 * pop), color=col,
                            alpha=fade, cx=lx)
        # how stair n is reached: a hop from n-1 and a hop from n-2 (ghost arcs)
        if counting and n_now >= 2 and t < STAIR_T[n_now] + STAIR_D[min(n_now, 9)] * 0.9:
            u = min(1.0, (t - STAIR_T[n_now]) / 0.35)
            n = n_now
            for frm, colr in ((n - 1, BLUE), (n - 2, ORANGE)):
                ax_ = (sx(frm - 1) + sx(frm)) / 2 if frm else x0 - run * 0.4
                bx_ = (sx(n - 1) + sx(n)) / 2
                arc = [parab((ax_, sy(frm) - h * 0.03), (bx_, sy(n) - h * 0.03), j / 20 * u, h * 0.045)
                       for j in range(21)]
                c.polylines([arc], colr, width=4, alpha=0.85)
        # Dot at the bottom, thinking (hand on chin) while counting
        H = h * 0.11
        ax = w * 0.08
        talkA = any(t0 <= t < t1 and wh == "A" for t0, t1, wh, _ in LINES) and int(t * 8) % 2
        think = 4.9 <= t < 12.3
        figure(c, ax, gy, H, BLUE, (0.3, 0.2), (2.4, 2.2) if think else (0.3, 0.2),
               mouth="open" if talkA else "smile", tilt=0.15 * think, t=t, look=0.5 if think else 0.0)
        self.pos = {"A": (ax, gy - H * 1.05), "B": (min(hx, w * 0.9), by - h * 0.005)}
        # bottom line
        if counting and n_now >= 2:
            n = n_now
            c.text_centered(f"{WAYS[n]} = {WAYS[n - 1]} + {WAYS[n - 2]}", h * 0.765, size=w * 0.075, color=GOLD)
            c.text_centered(f"ways to reach stair {n}", h * 0.80, size=w * 0.034, color=(0.85, 0.86, 0.92),
                            bold=False)
        elif STAIR_T[10] + 0.6 <= t:
            pop = math.exp(-max(0.0, t - STAIR_T[10] - 0.6) / 0.15)    # fades with the counts: frame 0 is clean
            c.text_centered("1, 2, 3, 5, 8 … 89 = Fibonacci!", h * 0.765, size=w * 0.06 * (1 + 0.2 * pop), color=GOLD,
                            alpha=fade)

    # ------------------------------------------------------------- episode 9 (Zeno's turtle)
    def turtle(self, x, gy, s, t, moving, shock=False):
        c = self.canvas
        ctx = c.ctx
        GR = (0.42, 0.78, 0.42)
        for k, dx in enumerate((-0.35, -0.12, 0.12, 0.35)):                 # legs
            ph = math.sin(t * 14 + k * 1.7) * (0.06 if moving else 0.0)
            ctx.rectangle(x + (dx + ph) * s - s * 0.05, gy - s * 0.16, s * 0.1, s * 0.16)
            ctx.set_source_rgb(*GR)
            ctx.fill()
        c.circle(x + s * 0.55, gy - s * 0.22, s * 0.14, GR)                  # head
        c.circle(x + s * 0.6, gy - s * 0.26, s * 0.035, (0.05, 0.05, 0.08))
        if shock:
            c.circle(x + s * 0.62, gy - s * 0.17, s * 0.035, (0.05, 0.05, 0.08))
        ctx.new_path()
        ctx.save()
        ctx.translate(x, gy - s * 0.14)
        ctx.scale(1.0, 0.62)
        ctx.arc(0, 0, s * 0.5, math.pi, 2 * math.pi)                         # shell
        ctx.restore()
        ctx.close_path()
        ctx.set_source_rgb(0.25, 0.55, 0.3)
        ctx.fill_preserve()
        ctx.set_source_rgb(0.75, 0.95, 0.6)
        ctx.set_line_width(3)
        ctx.stroke()
        for dx in (-0.22, 0.0, 0.22):
            c.ring(x + dx * s, gy - s * 0.3, s * 0.09, (0.7, 0.9, 0.55), width=2.5, alpha=0.8)

    def ep9(self, t):
        c, w, h = self.canvas, self.L.w, self.L.h
        gy, H = self.gy, self.H
        TR, TC = 4.3, 7.5                                          # race start, the catch (Σ = 1 unit of time)
        xa0, D = w * 0.10, w * 0.28
        vT = D / (TC - TR)
        vA = 2 * vT
        xt0 = xa0 + D
        T_STOP = 8.3
        tr = min(max(t - TR, 0.0), T_STOP - TR)
        xa = xa0 + vA * tr
        xt = xt0 + vT * tr
        # the walk back: the turtle rides on Dot's head (it is too slow to walk back)
        t_up, t_back0, t_back1 = 11.6, 12.0, 14.8
        xa_end = xa0 + vA * (T_STOP - TR)
        xt_end = xt0 + vT * (T_STOP - TR)
        on_head = False
        if t >= t_back0:
            u = smooth((t - t_back0) / (t_back1 - t_back0))
            xa = xa_end + (xa0 - xa_end) * u
        t_down = t_back0 + (t_back1 - t_back0) * 0.62
        walking = (TR <= t < T_STOP) or (t_back0 <= t < t_back1)
        # marks: each Zeno step (Dot reaches the turtle's previous spot)
        marks = []
        for k in range(1, 12):
            tk = TR + (TC - TR) * (1 - 0.5 ** k)
            if t >= tk and t < t_back1:
                marks.append(xa0 + vA * (tk - TR))
        for k, mx in enumerate(marks):
            a = 0.9 if t < t_back0 else max(0.0, 0.9 * (1 - (t - t_back0) / 1.0))
            c.lines([(mx, gy, mx, gy - h * 0.05)], GOLD, width=2.5, alpha=a)
            c.poly([(mx, gy - h * 0.05), (mx + w * 0.025, gy - h * 0.042), (mx, gy - h * 0.034)], GOLD, alpha=a)
        shockT = TC <= t < 11.6
        # turtle position
        if t < t_up:
            tx, ty = xt if t < T_STOP else xt_end, gy
        elif t < t_back0:
            u = (t - t_up) / (t_back0 - t_up)
            tx = xt_end + (xa_end - xt_end) * u
            ty = gy - math.sin(math.pi * u) * h * 0.06 - (gy - (gy - H * 0.82)) * u
            on_head = True
        elif t < t_down:
            tx, ty = xa, gy - H * 0.82
            on_head = True
        elif t < t_down + 0.35:
            u = (t - t_down) / 0.35
            tx = xa + (xt0 - xa) * u
            ty = gy - H * 0.82 * (1 - u) - math.sin(math.pi * u) * h * 0.04
        else:
            tx, ty = xt0, gy
        if t >= t_down + 0.35 or t < t_up:
            pass
        talkA = any(t0 <= t < t1 and wh == "A" for t0, t1, wh, _ in LINES) and int(t * 8) % 2
        talkB = any(t0 <= t < t1 and wh == "B" for t0, t1, wh, _ in LINES) and int(t * 8) % 2
        figure(c, xa, gy, H * 0.8, BLUE, (0.6, 0.4) if walking else (0.3, 0.2), (0.6, 0.4) if walking else (0.3, 0.2),
               walk=(t * 2.2 if walking else 0.0), mouth="open" if talkA else "smile", t=t)
        self.turtle(tx, ty, w * 0.11, t, (TR <= t < T_STOP and not on_head), shock=shockT)
        bxp = w * 0.92
        figure(c, bxp, gy, H * 0.8, ORANGE, (0.3, 0.2), (1.6, -0.2) if (t < 4.2 or t >= 14.6) else (0.3, 0.2),
               mouth="open" if talkB or 7.5 <= t < 8.4 else "smile", t=t)
        self.pos = {"A": (xa, gy - H * 0.8 * 1.05 - (h * 0.06 if on_head else 0)), "B": (bxp, gy - H * 0.8 * 1.05)}
        # the sum
        if t < TR or t >= 14.6:
            self.bottom("Zeno: \"you can never catch it\"", GOLD, 0.0 if t < TR else 14.6, t, size=0.06)
        elif t < TC:
            n = len([1 for k in range(1, 30) if t >= TR + (TC - TR) * (1 - 0.5 ** k)])
            ssum = 1 - 0.5 ** n
            self.bottom(f"steps: {n}   time: {ssum:.4f}…", (0.97, 0.97, 1.0), TR, t, size=0.06)
            c.text_centered("1/2 + 1/4 + 1/8 + 1/16 + …", h * 0.81, size=w * 0.045, color=GOLD, bold=False)
        else:
            self.bottom("1/2 + 1/4 + 1/8 + … = 1", GOLD, TC, t, size=0.07)
            c.text_centered("infinitely many steps, finite time", h * 0.81, size=w * 0.04, color=(0.9, 0.9, 1.0),
                            bold=False)

    # ------------------------------------------------------------- episode 10 (counting to a billion)
    def ep10(self, t):
        c, w, h = self.canvas, self.L.w, self.L.h
        gy, H = self.gy, self.H
        ctx = c.ctx
        L0, L1, RW0, RW1 = 5.0, 12.4, 15.9, 16.75                   # time-lapse, rewind (lands on frame 0)
        YEARS = 1e9 / 31557600
        if t < L0:
            yrs = max(0.0, t - 1.8) / 31557600 if t >= 1.8 else 0.0
            count = int(max(0.0, (t - 1.8) * 3.0)) if t >= 1.8 else 0
        elif t < L1:
            u = (t - L0) / (L1 - L0)
            uu = u ** 1.6
            yrs = YEARS * uu
            count = int(1e9 * uu)
        elif t < RW0:
            yrs, count = YEARS, 1_000_000_000
        elif t < RW1:
            u = smooth((t - RW0) / (RW1 - RW0))
            yrs = YEARS * (1 - u)
            count = int(1e9 * (1 - u))
        else:
            yrs, count = 0.0, 0
        age = yrs / YEARS                                           # 0 … 1
        # calendar + counter
        c.text_centered(f"YEAR {2026 + int(yrs)}", h * 0.205, size=w * 0.06, color=GOLD)
        c.text_centered(f"{count:,}", h * 0.262, size=w * 0.11, color=(1, 1, 1))
        c.text_centered(f"{yrs:4.1f} years of counting", h * 0.300, size=w * 0.04, color=(0.8, 0.82, 0.92), bold=False)
        if RW0 <= t < RW1:
            c.text_centered("<< REWIND", h * 0.335, size=w * 0.05, color=(0.85, 0.86, 0.92))
        talkA = any(t0 <= t < t1 and wh == "A" for t0, t1, wh, _ in LINES) and int(t * 8) % 2
        talkB = any(t0 <= t < t1 and wh == "B" for t0, t1, wh, _ in LINES) and int(t * 8) % 2
        lapse = L0 <= t < L1
        ax, bx = w * 0.24, w * 0.80
        mouthA = "open" if (talkA or (lapse and int(t * 10) % 2)) else "smile"
        figure(c, ax, gy, H, BLUE, (0.3, 0.2), (0.3, 0.2), mouth=mouthA, tilt=0.12 * age, t=t)
        hcx, hcy, hr = ax + math.sin(0.12 * age) * 0.12 * H, gy - 0.90 * H, 0.115 * H
        if age > 0.02:                                              # the beard grows, the hair goes grey
            L_ = H * 0.45 * age
            c.poly([(hcx - hr * 0.8, hcy + hr * 0.35), (hcx + hr * 0.8, hcy + hr * 0.35), (hcx + hr * 0.3, hcy + hr + L_),
                    (hcx, hcy + hr * 1.1 + L_ * 1.05), (hcx - hr * 0.3, hcy + hr + L_)], (0.88, 0.88, 0.9), alpha=0.95)
            ctx.new_path()
            ctx.arc(hcx, hcy, hr * 1.05, math.pi * 1.1, math.pi * 1.9)
            ctx.set_source_rgba(0.9, 0.9, 0.92, min(1.0, age * 1.4))
            ctx.set_line_width(hr * 0.35)
            ctx.stroke()
        # the friend ages too: bent, with a cane
        bend = 0.35 * age
        figure(c, bx, gy, H * (1 - 0.08 * age), ORANGE, (0.3, 0.2), (0.25 + 0.5 * age, 0.1), tilt=-bend,
               mouth="open" if talkB else "smile", t=t)
        if age > 0.3:
            hxx = bx + math.sin(0.25 + 0.5 * age) * 0.26 * H
            c.lines([(hxx - H * 0.02, gy - H * 0.38, hxx - H * 0.02, gy)], (0.6, 0.45, 0.3), width=6,
                    alpha=min(1.0, (age - 0.3) * 4))
            ctx.new_path()
            ctx.arc(bx + math.sin(-bend) * 0.12 * H, gy - 0.90 * H, 0.115 * H * 1.05, math.pi * 1.1, math.pi * 1.9)
            ctx.set_source_rgba(0.9, 0.9, 0.92, min(1.0, age * 1.4))
            ctx.set_line_width(0.115 * H * 0.35)
            ctx.stroke()
        # a kid is born and grows up
        if age > 0.12:
            k = min(1.0, (age - 0.12) / 0.7)
            pop = math.exp(-max(0.0, age - 0.12) * 30)
            figure(c, w * 0.55, gy, H * (0.35 + 0.6 * k) * (1 + 0.2 * pop), LIME, (0.3, 0.2), (0.3, 0.2),
                   mouth="smile", t=t)
        self.pos = {"A": (hcx, gy - H * 1.05), "B": (bx, gy - H * 1.05)}
        if t < L0 or t >= RW1:
            self.bottom("1 number per second", GOLD, 0.0 if t < L0 else RW1, t, size=0.065)
        elif t < L1:
            self.bottom("…and it keeps going", (0.97, 0.97, 1.0), L0, t, size=0.06)
        else:
            self.bottom("1,000,000,000 s = 31.7 years", GOLD, L1, t, size=0.065)

    # ------------------------------------------------------------- episode 11 (pizza: area grows with r²)
    def pizza(self, x, y, r, seed, alpha=1.0):
        c = self.canvas
        c.circle(x, y, r, (0.85, 0.6, 0.3), alpha=alpha)
        c.circle(x, y, r * 0.88, (1.0, 0.82, 0.35), alpha=alpha)
        rng = np.random.default_rng(seed)
        for _ in range(int(6 + 10 * (r / (self.L.w * 0.15)))):
            a, d = rng.uniform(0, 2 * math.pi), math.sqrt(rng.uniform(0, 1)) * r * 0.72
            c.circle(x + d * math.cos(a), y + d * math.sin(a), r * 0.09, (0.8, 0.2, 0.15), alpha=alpha)

    def ep11(self, t):
        c, w, h = self.canvas, self.L.w, self.L.h
        gy, H = self.gy, self.H
        IN = w * 0.0165                                             # px per inch
        R18, R12 = 9 * IN, 6 * IN
        cy = h * 0.34
        app = smooth((t - 4.8) / 0.6) if t >= 4.8 else 0.0
        if t >= 15.3:
            app *= 1 - smooth((t - 15.3) / 0.8)                     # eaten
        if app > 0:
            sx1, sx2, bxp = w * 0.17, w * 0.40, w * 0.73
            self.pizza(sx1, cy, R12 * app, 1)
            self.pizza(sx2, cy, R12 * app, 2)
            self.pizza(bxp, cy, R18 * app, 3)
            if t >= 6.0:
                a = smooth((t - 6.0) / 0.4) * app
                c.text_centered('12"', cy + R12 + h * 0.03, size=w * 0.04, color=BLUE, alpha=a, cx=sx1)
                c.text_centered('12"', cy + R12 + h * 0.03, size=w * 0.04, color=BLUE, alpha=a, cx=sx2)
                c.text_centered('18"', cy + R18 + h * 0.03, size=w * 0.04, color=ORANGE, alpha=a, cx=bxp)
            if t >= 10.3:                                           # area bars
                u = smooth((t - 10.3) / 1.4) * (1 - smooth((t - 15.3) / 0.8))
                y0 = h * 0.205
                bw = w * 0.7
                for i, (lab, val, col) in enumerate((("two 12\"", 226, BLUE), ("one 18\"", 254, ORANGE))):
                    yy = y0 + i * h * 0.03
                    ctx = c.ctx
                    ctx.rectangle(w * 0.2, yy, bw * val / 254 * u, h * 0.022)
                    ctx.set_source_rgb(*col)
                    ctx.fill()
                    c.text_centered(lab, yy + h * 0.018, size=w * 0.03, color=col, cx=w * 0.11)
                    if u > 0.95:
                        c.text_centered(f"{val} in²", yy + h * 0.018, size=w * 0.03, color=(0.05, 0.05, 0.08),
                                        cx=w * 0.2 + bw * val / 254 - w * 0.08)
        talkA = any(t0 <= t < t1 and wh == "A" for t0, t1, wh, _ in LINES) and int(t * 8) % 2
        talkB = any(t0 <= t < t1 and wh == "B" for t0, t1, wh, _ in LINES) and int(t * 8) % 2
        sad = 8.8 <= t < 16.1
        figure(c, w * 0.18, gy, H * 0.7, BLUE, (0.3, 0.2) if not (2.0 <= t < 3.3) else (2.6, 0.4),
               (0.3, 0.2) if not (2.0 <= t < 3.3) else (2.6, 0.4),
               mouth="open" if talkA else ("sad" if sad else "smile"), t=t, tear=(t * 0.8 if 14.7 <= t < 16.1 else 0.0))
        figure(c, w * 0.82, gy, H * 0.7, ORANGE, (0.3, 0.2), (1.3, -0.4) if 9.0 <= t < 15.3 else (0.3, 0.2),
               mouth="open" if talkB else "smile", t=t)
        self.pos = {"A": (w * 0.18, gy - H * 0.7 * 1.05), "B": (w * 0.82, gy - H * 0.7 * 1.05)}
        if t < 6.0 or t >= 15.9:
            self.bottom('two 12" or one 18"?', GOLD, 0.0 if t < 6.0 else 15.9, t, size=0.07)
        elif t < 8.6:
            self.bottom("12 + 12 = 24 > 18 … right?", (0.97, 0.97, 1.0), 6.0, t, size=0.06)
        elif t < 10.3:
            self.bottom("area = π·r²", GOLD, 8.6, t, size=0.075)
        elif t < 12.0:
            self.bottom("2·π·6² = 226   vs   π·9² = 254", GOLD, 10.3, t, size=0.055)
        else:
            self.bottom('one 18" = 12% MORE pizza', GOLD, 12.0, t, size=0.065)

    # ------------------------------------------------------------- episode 12 (lily pads double every day)
    def ep12(self, t):
        c, w, h = self.canvas, self.L.w, self.L.h
        gy, H = self.gy, self.H
        ctx = c.ctx
        lx, ly, rx_, ry_ = w * 0.45, h * 0.47, w * 0.42, h * 0.14
        if not hasattr(self, "pads"):                              # 512 pads on a hex grid that fills the lake
            def grid(d):
                out = []
                for j in range(-40, 41):
                    for i in range(-60, 61):
                        X = (i + 0.5 * (j % 2)) * d
                        Y = j * d * 0.866
                        if (X / (rx_ * 0.97)) ** 2 + (Y / (ry_ * 0.95)) ** 2 < 1:
                            out.append((X, Y))
                return out
            lo, hi = 5.0, 80.0
            for _ in range(40):
                mid = (lo + hi) / 2
                if len(grid(mid)) >= 512:
                    lo = mid
                else:
                    hi = mid
            pts = grid(lo)
            seed = (-rx_ * 0.75, ry_ * 0.1)
            pts.sort(key=lambda p: (p[0] - seed[0]) ** 2 + ((p[1] - seed[1]) * 1.3) ** 2)
            self.pads, self.pad_r = pts[:512], lo * 0.62
        # days: one step per day, the pads double each time (1, 2, 4 … 512)
        day = max(d for d, td in LILY_DAYS.items() if t >= td) if t < 15.8 else 1
        t_day = LILY_DAYS[day]
        frac = 2.0 ** (day - 10)
        fade = 1.0 - smooth((t - 14.6) / 1.2) if t >= 14.6 else 1.0
        ctx.save()
        ctx.translate(lx, ly)
        ctx.scale(rx_, ry_)
        ctx.arc(0, 0, 1, 0, 2 * math.pi)
        ctx.restore()
        ctx.set_source_rgb(0.15, 0.35, 0.6)
        ctx.fill()
        n = 2 ** (day - 1)
        n_prev = n // 2
        pr = self.pad_r
        grow = smooth((t - t_day) / 0.3)
        for i, (px, py) in enumerate(self.pads[:n]):
            a = 1.0 if i == 0 else fade
            if a <= 0.01:
                continue
            r_ = pr * (grow if i >= n_prev and day > 1 else 1.0)
            if r_ < 0.5:
                continue
            X, Y = lx + px, ly + py
            c.circle(X, Y, r_, (0.3, 0.75, 0.35), alpha=a)
            c.poly([(X, Y), (X + r_, Y - r_ * 0.25), (X + r_, Y + r_ * 0.25)], (0.15, 0.35, 0.6), alpha=a)
        # Dot fishing in a little boat (swallowed on day 30)
        bxp, byp = lx + rx_ * 0.45, ly
        sink = smooth((t - 11.9) / 0.4) if 11.9 <= t < 14.6 else 0.0
        ctx.new_path()
        ctx.move_to(bxp - w * 0.08, byp - h * 0.005)
        ctx.line_to(bxp + w * 0.08, byp - h * 0.005)
        ctx.line_to(bxp + w * 0.055, byp + h * 0.025)
        ctx.line_to(bxp - w * 0.055, byp + h * 0.025)
        ctx.close_path()
        ctx.set_source_rgb(0.6, 0.38, 0.2)
        ctx.fill()
        Hs = H * 0.5
        talkA = any(t0 <= t < t1 and wh == "A" for t0, t1, wh, _ in LINES) and int(t * 8) % 2
        talkB = any(t0 <= t < t1 and wh == "B" for t0, t1, wh, _ in LINES) and int(t * 8) % 2
        shock = 11.9 <= t < 13.4
        figure(c, bxp, byp, Hs, BLUE, (0.3, 0.2) if not shock else (2.6, 0.4), (2.0, -0.6),
               mouth="open" if (talkA or shock) else "smile", t=t)
        hx, hy = bxp + math.sin(2.0) * 0.26 * Hs + math.sin(1.4) * 0.24 * Hs, byp - 0.76 * Hs + math.cos(2.0) * 0.26 * Hs
        c.lines([(hx, hy, hx + w * 0.12, hy - h * 0.06)], (0.7, 0.55, 0.35), width=3)
        c.lines([(hx + w * 0.12, hy - h * 0.06, hx + w * 0.13, byp + h * 0.01)], (0.9, 0.9, 0.95), width=1.2, alpha=0.7)
        if sink > 0:                                                # pads pile over the boat
            for k in range(8):
                c.circle(bxp - w * 0.07 + k * w * 0.02, byp - h * 0.005 - (k % 3) * h * 0.006, pr * 0.9,
                         (0.3, 0.75, 0.35), alpha=sink * fade)
        figure(c, w * 0.9, gy, H * 0.8, ORANGE, (0.3, 0.2), (1.4, -0.3) if (t < 3.6 or t >= 15.6) else (0.3, 0.2),
               mouth="open" if talkB else "smile", t=t)
        self.pos = {"A": (bxp, byp - Hs * 1.05), "B": (w * 0.9, gy - H * 0.8 * 1.05)}
        dshow = 1 if t >= 15.8 else (day if t < 14.6 else 10)
        c.text_centered(f"DAY {dshow}", h * 0.27, size=w * 0.07, color=GOLD, cx=w * 0.22)
        cov = "1 lily pad" if n == 1 else f"{n} lily pads · {n / 5.12:.0f}%"
        c.text_centered(cov if (t < 14.6 or t >= 15.8) else "next spring…", h * 0.305, size=w * 0.042, color=(0.85, 0.9, 1.0),
                        bold=False, cx=w * 0.22)
        if t < 4.0 or t >= 15.6:
            self.bottom("×2 every day", GOLD, 0.0 if t < 4.0 else 15.6, t, size=0.075)
        elif t < 11.4:
            self.bottom("day 8: 25%   day 9: 50%", (0.97, 0.97, 1.0), 4.0, t, size=0.06)
        else:
            self.bottom("50% → 100% in ONE day", GOLD, 11.4, t, size=0.07)

    # ------------------------------------------------------------- episode 13 (the ant on a box)
    def ep13(self, t):
        c, w, h = self.canvas, self.L.w, self.L.h
        gy, H = self.gy, self.H
        S = w * 0.30
        ox, oy = w * 0.40, self.gy                                  # front-bottom-left corner: on the ground
        k30 = (math.cos(math.radians(30)) * 0.5, math.sin(math.radians(30)) * 0.5)

        def P(x, y, z):
            return ox + (x + z * k30[0]) * S, oy - (y + z * k30[1]) * S

        a = 0.0                                                     # the top lid unfolds up (0 = closed)
        if 8.1 <= t < 9.5:
            a = smooth((t - 8.1) / 1.4)
        elif 9.5 <= t < 10.8:
            a = 1.0
        elif 10.8 <= t < 12.0:
            a = 1 - smooth((t - 10.8) / 1.2)
        A = a * math.pi / 2

        def top(u, v):                                              # point on the (rotating) top face
            return P(u, 1 + v * math.sin(A), v * math.cos(A))

        CARD = (0.78, 0.58, 0.36)
        c.poly([P(1, 0, 0), P(1, 0, 1), P(1, 1, 1), P(1, 1, 0)], tuple(x * 0.7 for x in CARD))   # right side
        if a < 0.5:
            c.poly([top(0, 0), top(1, 0), top(1, 1), top(0, 1)], tuple(x * 0.9 for x in CARD))
            c.poly([P(0, 0, 0), P(1, 0, 0), P(1, 1, 0), P(0, 1, 0)], CARD)
        else:
            c.poly([P(0, 0, 0), P(1, 0, 0), P(1, 1, 0), P(0, 1, 0)], CARD)
            c.poly([top(0, 0), top(1, 0), top(1, 1), top(0, 1)], tuple(x * 0.9 for x in CARD))
        for pts in ([P(0, 0, 0), P(1, 0, 0), P(1, 1, 0), P(0, 1, 0), P(0, 0, 0)],
                    [top(0, 0), top(1, 0), top(1, 1), top(0, 1), top(0, 0)],
                    [P(1, 0, 0), P(1, 0, 1), P(1, 1, 1)]):
            c.polylines([pts], (0.35, 0.22, 0.12), width=3)
        honey = top(1, 1)
        c.circle(honey[0], honey[1], w * 0.022, (1.0, 0.75, 0.15))
        c.glow(honey[0], honey[1], w * 0.03, GOLD, strength=0.5, reach=2)
        # A's path (red): front diagonal then straight back along the top
        if 4.0 <= t < 12.0:
            u = smooth((t - 4.0) / 2.0)
            pts = [P(0, 0, 0), P(1, 1, 0)] + [top(1, s) for s in np.linspace(0, 1, 8)]
            n = max(2, int(len(pts) * u))
            c.polylines([pts[:n]], RED, width=5, alpha=0.9)
        # the straight line on the net (gold): crosses the edge at x = 0.5
        if t >= 9.0 and t < 16.4:
            u = smooth((t - 9.0) / 0.8)
            pts = [P(s * 0.5, s, 0) for s in np.linspace(0, 1, 6)] + [top(0.5 + 0.5 * s, s) for s in np.linspace(0, 1, 8)]
            n = max(2, int(len(pts) * u))
            c.polylines([pts[:n]], GOLD, width=6, alpha=0.95)
        # the ant walks the gold path, then (loop) back to the start
        if 12.0 <= t < 14.4:
            s_ = smooth((t - 12.0) / 2.4)
        elif 14.4 <= t < 16.2:
            s_ = 1.0
        elif t >= 16.2:
            s_ = 1 - smooth((t - 16.2) / 0.8)
        else:
            s_ = 0.0
        L1, L2 = math.sqrt(0.25 + 1), math.sqrt(0.25 + 1)
        if s_ < 0.5:
            ax_, ay_ = P(s_ * 2 * 0.5, s_ * 2, 0)
        else:
            q = (s_ - 0.5) * 2
            ax_, ay_ = top(0.5 + 0.5 * q, q)
        wig = math.sin(t * 30) * 2 if 0 < s_ < 1 else 0
        for k in range(3):
            c.circle(ax_ - 10 + k * 10, ay_ + (k == 1) * wig * 0.5, 8 if k != 1 else 6, (0.06, 0.06, 0.08))
        c.lines([(ax_ - 10, ay_, ax_ - 19, ay_ + 11 + wig), (ax_, ay_, ax_, ay_ + 13 - wig), (ax_ + 10, ay_, ax_ + 19, ay_ + 11 + wig)],
                (0.06, 0.06, 0.08), width=3)
        talkA = any(t0 <= t < t1 and wh == "A" for t0, t1, wh, _ in LINES) and int(t * 8) % 2
        talkB = any(t0 <= t < t1 and wh == "B" for t0, t1, wh, _ in LINES) and int(t * 8) % 2
        figure(c, w * 0.12, gy, H * 0.8, BLUE, (0.3, 0.2), (1.4, -0.3) if 2.1 <= t < 6.0 else (0.3, 0.2),
               mouth="open" if talkA else ("sad" if 14.4 <= t < 16.3 else "smile"), t=t)
        figure(c, w * 0.9, gy, H * 0.8, ORANGE, (0.3, 0.2), (1.4, -0.3) if 6.8 <= t < 10.8 else (0.3, 0.2),
               mouth="open" if talkB else "smile", t=t)
        self.pos = {"A": (w * 0.12, gy - H * 0.8 * 1.05), "B": (w * 0.9, gy - H * 0.8 * 1.05)}
        if t < 4.0 or t >= 16.3:
            self.bottom("box: 1 m × 1 m × 1 m", GOLD, 0.0 if t < 4.0 else 16.3, t, size=0.06)
        elif t < 8.1:
            self.bottom("√2 + 1 = 2.41 m", RED, 4.0, t, size=0.075)
        elif t < 12.0:
            self.bottom("√(1² + 2²) = √5 = 2.24 m", GOLD, 9.0, t, size=0.065)
        else:
            self.bottom("unfold it: the straight line wins", GOLD, 12.0, t, size=0.055)

    # ------------------------------------------------------------- episode 14 (counting to a trillion through history)
    def ep14(self, t):
        c, w, h = self.canvas, self.L.w, self.L.h
        gy, H = self.gy, self.H * 0.72
        ctx = c.ctx
        YK = [(0.0, -29000), (3.0, -10000), (5.0, -2560), (6.5, -2400), (7.0, 100), (8.8, 1200), (10.6, 1500), (12.4, 2026), (14.0, 2040),
              (15.0, 2700), (16.6, 2700), (18.2, -29000), (18.6, -29000)]
        for (t0, y0), (t1, y1) in zip(YK, YK[1:]):
            if t0 <= t <= t1:
                year = y0 + (y1 - y0) * (t - t0) / (t1 - t0)
                break
        else:
            year = -29000
        frac = (year + 29000) / 31700.0
        count = int(round(1e12 * frac))
        # the eras: (start time, name, figure colour, prop)
        ERAS = [(0.0, "Ice Age", (0.85, 0.75, 0.6), "ice"), (3.0, "first farms", (0.6, 0.9, 0.45), "farm"),
                (5.0, "the pyramids", (1.0, 0.82, 0.4), "pyr"), (7.0, "Rome", (1.0, 0.45, 0.4), "rome"),
                (8.8, "knights", (0.75, 0.78, 0.9), "castle"), (10.6, "explorers", (0.5, 0.8, 1.0), "ship"),
                (12.4, "today", BLUE, "city"), (15.0, "the future", (0.6, 1.0, 0.9), "future")]
        GAP = w * 1.0
        ex = [w * 0.5 + i * GAP for i in range(len(ERAS))]
        # camera: follows the holder, pans through history (and back on the rewind)
        holder = max(i for i, e in enumerate(ERAS) if t >= e[0]) if t < 16.6 else len(ERAS) - 1
        if t >= 16.6:
            u = smooth((t - 16.6) / 1.6)
            camx = ex[-1] + (ex[0] - ex[-1]) * u
            holder = 0 if u > 0.98 else holder
        else:
            nxt = min(len(ERAS) - 1, holder + 1)
            t_next = ERAS[nxt][0] if nxt != holder else 99
            u = smooth((t - (t_next - 0.7)) / 0.7) if t > t_next - 0.7 else 0.0
            camx = ex[holder] + (ex[nxt] - ex[holder]) * u
        X = lambda xw: xw - camx + w / 2                      # noqa: E731

        def head(x):
            return x, gy - 0.90 * H, 0.115 * H

        for i, (t0, name, col, prop) in enumerate(ERAS):
            xc = X(ex[i])
            if xc < -w * 0.6 or xc > w * 1.6:
                continue
            px = xc + w * 0.22
            if prop == "ice":                                    # a cave with paintings, a woolly mammoth, snow
                ctx.new_path()
                ctx.arc(xc - w * 0.05, gy, w * 0.34, math.pi, 2 * math.pi)
                ctx.set_source_rgb(0.28, 0.3, 0.38)
                ctx.fill()
                for k in range(7):                               # rock texture
                    a = math.pi + (k + 0.5) / 7 * math.pi
                    c.lines([(xc - w * 0.05 + math.cos(a) * w * 0.27, gy + math.sin(a) * w * 0.27,
                              xc - w * 0.05 + math.cos(a + 0.1) * w * 0.33, gy + math.sin(a + 0.1) * w * 0.33)],
                            (0.2, 0.22, 0.28), width=3)
                ctx.new_path()
                ctx.arc(xc - w * 0.05, gy, w * 0.25, math.pi, 2 * math.pi)
                ctx.set_source_rgb(0.08, 0.06, 0.06)
                ctx.fill()
                for k, (dx, dy) in enumerate(((-0.17, 0.12), (-0.11, 0.15), (0.0, 0.17))):   # cave paintings
                    hx_, hy_ = xc + w * dx, gy - w * dy
                    if k < 2:                                    # hand prints
                        c.circle(hx_, hy_, w * 0.012, (0.85, 0.35, 0.2), alpha=0.85)
                        for j in range(5):
                            a = -math.pi / 2 + (j - 2) * 0.4
                            c.lines([(hx_, hy_, hx_ + math.cos(a) * w * 0.022, hy_ + math.sin(a) * w * 0.022)],
                                    (0.85, 0.35, 0.2), width=3, alpha=0.85)
                    else:                                        # a painted deer
                        c.lines([(hx_ - 12, hy_, hx_ + 12, hy_), (hx_ - 10, hy_, hx_ - 12, hy_ + 12),
                                 (hx_ + 10, hy_, hx_ + 12, hy_ + 12), (hx_ + 12, hy_, hx_ + 18, hy_ - 8),
                                 (hx_ + 18, hy_ - 8, hx_ + 14, hy_ - 18), (hx_ + 18, hy_ - 8, hx_ + 24, hy_ - 16)],
                                (0.85, 0.35, 0.2), width=3, alpha=0.85)
                # the woolly mammoth (walks in place, trunk swings)
                mx, my, M = xc + w * 0.29, gy, H * 0.95
                fur = (0.52, 0.34, 0.2)
                dark = (0.38, 0.24, 0.14)
                for k, lx in enumerate((-0.32, -0.12, 0.14, 0.3)):   # legs
                    sw = math.sin(t * 4 + k * 1.6) * M * 0.03
                    ctx.rectangle(mx + lx * M - M * 0.07 + sw, my - M * 0.42, M * 0.14, M * 0.42)
                    ctx.set_source_rgb(*(dark if k % 2 else fur))
                    ctx.fill()
                    ctx.rectangle(mx + lx * M - M * 0.08 + sw, my - M * 0.05, M * 0.16, M * 0.05)
                    ctx.set_source_rgb(0.25, 0.17, 0.1)
                    ctx.fill()
                ctx.save()
                ctx.translate(mx, my - M * 0.62)
                ctx.scale(1.0, 0.68)
                ctx.arc(0, 0, M * 0.45, 0, 2 * math.pi)
                ctx.restore()
                ctx.set_source_rgb(*fur)
                ctx.fill()
                for k in range(16):                              # shaggy fur
                    fx_ = mx - M * 0.4 + k * M * 0.053
                    c.lines([(fx_, my - M * 0.45, fx_ + M * 0.02, my - M * 0.3)], dark, width=3)
                c.circle(mx + M * 0.42, my - M * 0.72, M * 0.24, fur)                # the head (high dome)
                c.circle(mx + M * 0.36, my - M * 0.92, M * 0.14, fur)
                c.circle(mx + M * 0.32, my - M * 0.7, M * 0.12, dark)                # ear
                c.circle(mx + M * 0.5, my - M * 0.78, M * 0.03, (0.05, 0.03, 0.02))  # eye
                swing = math.sin(t * 2.2) * 0.25
                trunk = []
                for j in range(14):
                    u = j / 13
                    trunk.append((mx + M * (0.6 + 0.18 * u + 0.12 * math.sin(swing + u * 2.5) * u),
                                  my - M * (0.68 - 0.62 * u) + M * 0.1 * u * u))
                c.polylines([trunk], fur, width=M * 0.11)
                tusk = [(mx + M * (0.55 + 0.25 * math.sin(u * 2.2)), my - M * (0.6 - 0.25 * u) - M * 0.2 * u * u)
                        for u in np.linspace(0, 1, 12)]
                c.polylines([tusk], (0.96, 0.94, 0.86), width=M * 0.045)
                c.polylines([[(mx - M * 0.45, my - M * 0.7), (mx - M * 0.55, my - M * 0.5)]], dark, width=4)   # tail
                for k in range(18):                              # snow
                    sx_ = xc - w * 0.48 + (k * 97) % int(w * 0.96) + math.sin(t + k) * 8
                    sy_ = (k * 151 + t * 55) % (gy - h * 0.25) + h * 0.25
                    c.circle(sx_, sy_, 3 + (k % 3), (1, 1, 1), alpha=0.75)
            elif prop == "farm":
                for k in range(11):                              # wheat swaying
                    x_ = px - H * 0.5 + k * H * 0.1
                    sw = math.sin(t * 2 + k) * H * 0.03
                    c.lines([(x_, gy, x_ + sw, gy - H * 0.5)], (0.85, 0.75, 0.3), width=3)
                    for j in range(3):
                        c.circle(x_ + sw + (j - 1) * 3, gy - H * (0.5 + 0.05 * j), 4, (1.0, 0.85, 0.4))
                ctx.rectangle(xc - w * 0.33, gy - H * 0.45, w * 0.22, H * 0.45)                 # the hut
                ctx.set_source_rgb(0.55, 0.38, 0.22)
                ctx.fill()
                for k in range(5):
                    c.lines([(xc - w * 0.33, gy - H * 0.08 * (k + 1), xc - w * 0.11, gy - H * 0.08 * (k + 1))],
                            (0.42, 0.28, 0.15), width=2)
                ctx.rectangle(xc - w * 0.245, gy - H * 0.28, w * 0.05, H * 0.28)
                ctx.set_source_rgb(0.15, 0.1, 0.06)
                ctx.fill()
                c.poly([(xc - w * 0.36, gy - H * 0.45), (xc - w * 0.08, gy - H * 0.45), (xc - w * 0.22, gy - H * 0.82)],
                       (0.85, 0.7, 0.32))
                for k in range(6):
                    c.lines([(xc - w * 0.34 + k * w * 0.05, gy - H * 0.47, xc - w * 0.22, gy - H * 0.8)],
                            (0.7, 0.55, 0.25), width=2)
                for k in (-0.035, 0.0, 0.03):                    # a fluffy sheep
                    c.circle(xc - w * 0.4 + w * k, gy - H * 0.16, H * 0.07, (0.95, 0.95, 0.9))
                for k in (-0.03, 0.025):
                    c.lines([(xc - w * 0.4 + w * k, gy - H * 0.1, xc - w * 0.4 + w * k, gy)], (0.2, 0.2, 0.2), width=4)
                c.circle(xc - w * 0.4 + w * 0.06, gy - H * 0.2, H * 0.045, (0.2, 0.2, 0.22))
            elif prop == "pyr":
                for (bx0, bx1, ht, colp) in ((-0.42, 0.06, 1.3, (0.88, 0.72, 0.42)), (0.0, 0.38, 1.0, (0.78, 0.62, 0.36))):
                    L_, R_ = xc + w * bx0, xc + w * bx1
                    apex = ((L_ + R_) / 2, gy - H * ht)
                    c.poly([(L_, gy), (R_, gy), apex], colp, alpha=0.95)
                    c.poly([(apex[0], gy), (R_, gy), apex], tuple(v * 0.8 for v in colp), alpha=0.95)    # shaded face
                    rows = 9
                    for r in range(1, rows):                    # stone courses
                        y_ = gy - H * ht * r / rows
                        k = r / rows
                        c.lines([(L_ + (apex[0] - L_) * k, y_, R_ + (apex[0] - R_) * k, y_)], (0.6, 0.48, 0.28),
                                width=2, alpha=0.7)
                c.circle(xc + w * 0.32, gy - H * 1.65, H * 0.16, (1.0, 0.85, 0.4))
                c.glow(xc + w * 0.32, gy - H * 1.65, H * 0.4, (1.0, 0.85, 0.4), strength=0.4, reach=2)
                for k in range(3):                              # palm trees
                    tx_ = xc - w * 0.45 + k * w * 0.05
                    c.lines([(tx_, gy, tx_ + 6, gy - H * 0.6)], (0.5, 0.35, 0.2), width=6)
                    for a in (-2.6, -2.0, -1.2, -0.6):
                        c.lines([(tx_ + 6, gy - H * 0.6, tx_ + 6 + math.cos(a) * H * 0.22, gy - H * 0.6 + math.sin(a) * H * 0.1 + H * 0.06)],
                                (0.35, 0.75, 0.35), width=4)
            elif prop == "rome":
                ctx.rectangle(xc - w * 0.4, gy - H * 0.08, w * 0.4, H * 0.08)            # steps
                ctx.set_source_rgb(0.8, 0.8, 0.77)
                ctx.fill()
                for k in range(4):
                    x_ = xc - w * 0.36 + k * w * 0.09
                    ctx.rectangle(x_, gy - H * 1.0, w * 0.04, H * 0.92)
                    ctx.set_source_rgb(0.9, 0.9, 0.87)
                    ctx.fill()
                    for j in (0.25, 0.5, 0.75):                  # fluting
                        c.lines([(x_ + w * 0.04 * j, gy - H * 0.95, x_ + w * 0.04 * j, gy - H * 0.12)], (0.7, 0.7, 0.68),
                                width=2)
                    ctx.rectangle(x_ - 4, gy - H * 1.04, w * 0.04 + 8, H * 0.05)
                    ctx.set_source_rgb(0.95, 0.95, 0.92)
                    ctx.fill()
                ctx.rectangle(xc - w * 0.39, gy - H * 1.12, w * 0.38, H * 0.08)
                ctx.fill()
                c.poly([(xc - w * 0.40, gy - H * 1.12), (xc + w * 0.0, gy - H * 1.12), (xc - w * 0.2, gy - H * 1.4)],
                       (0.92, 0.92, 0.88))
                c.text_centered("SPQR", gy - H * 1.18, size=H * 0.09, color=(0.6, 0.5, 0.3), cx=xc - w * 0.2)
            elif prop == "castle":
                ctx.rectangle(xc - w * 0.4, gy - H * 0.9, w * 0.32, H * 0.9)
                ctx.set_source_rgb(0.45, 0.47, 0.55)
                ctx.fill()
                for r in range(6):                               # stone blocks
                    for k in range(6):
                        off = (r % 2) * w * 0.026
                        ctx.rectangle(xc - w * 0.4 + off + k * w * 0.053, gy - H * 0.15 * (r + 1), w * 0.05, H * 0.13)
                ctx.set_source_rgb(0.5, 0.52, 0.6)
                ctx.fill()
                for k in range(6):
                    ctx.rectangle(xc - w * 0.4 + k * w * 0.056, gy - H * 1.02, w * 0.03, H * 0.12)
                ctx.set_source_rgb(0.45, 0.47, 0.55)
                ctx.fill()
                ctx.new_path()
                ctx.arc(xc - w * 0.24, gy - H * 0.3, w * 0.035, math.pi, 2 * math.pi)
                ctx.line_to(xc - w * 0.205, gy)
                ctx.line_to(xc - w * 0.275, gy)
                ctx.close_path()
                ctx.set_source_rgb(0.12, 0.1, 0.08)
                ctx.fill()
                c.lines([(xc - w * 0.3, gy - H * 1.02, xc - w * 0.3, gy - H * 1.5)], (0.6, 0.6, 0.6), width=3)
                flag = [(xc - w * 0.3 + k * 6, gy - H * 1.48 + math.sin(t * 6 + k * 0.6) * 4) for k in range(10)]
                c.poly(flag + [(f[0], f[1] + H * 0.14) for f in flag[::-1]], (0.9, 0.25, 0.25))
            elif prop == "ship":
                for k in range(8):
                    x_ = xc - w * 0.5 + k * w * 0.13 + (t * 30) % (w * 0.13)
                    ctx.new_path()
                    ctx.arc(x_, gy - 2, w * 0.065, math.pi, 2 * math.pi)
                    ctx.set_source_rgba(0.35, 0.65, 1.0, 0.75)
                    ctx.set_line_width(4)
                    ctx.stroke()
                bob = math.sin(t * 2.5) * 4
                c.poly([(xc - w * 0.4, gy - H * 0.38 + bob), (xc - w * 0.04, gy - H * 0.38 + bob),
                        (xc - w * 0.09, gy - H * 0.08 + bob), (xc - w * 0.35, gy - H * 0.08 + bob)], (0.55, 0.35, 0.2))
                for k in range(4):                               # planks + portholes
                    c.lines([(xc - w * 0.38, gy - H * (0.32 - 0.06 * k) + bob, xc - w * 0.07, gy - H * (0.32 - 0.06 * k) + bob)],
                            (0.42, 0.26, 0.14), width=2)
                for k in range(3):
                    c.circle(xc - w * 0.3 + k * w * 0.07, gy - H * 0.26 + bob, 4, (0.95, 0.85, 0.5))
                for mxx, ht in ((-0.28, 1.4), (-0.15, 1.15)):
                    c.lines([(xc + w * mxx, gy - H * 0.38 + bob, xc + w * mxx, gy - H * ht + bob)], (0.5, 0.35, 0.2), width=6)
                    ctx.new_path()
                    ctx.move_to(xc + w * mxx, gy - H * (ht - 0.05) + bob)
                    ctx.curve_to(xc + w * (mxx + 0.08), gy - H * (ht - 0.25) + bob, xc + w * (mxx + 0.08),
                                 gy - H * 0.65 + bob, xc + w * mxx, gy - H * 0.5 + bob)
                    ctx.close_path()
                    ctx.set_source_rgb(0.96, 0.94, 0.86)
                    ctx.fill()
                flag = [(xc - w * 0.28 + k * 5, gy - H * 1.42 + bob + math.sin(t * 7 + k) * 3) for k in range(7)]
                c.poly(flag + [(f[0], f[1] + 12) for f in flag[::-1]], (0.9, 0.3, 0.3))
            elif prop == "city":
                for k, hh in enumerate((0.9, 1.45, 1.1, 1.75, 0.8)):
                    x_ = xc - w * 0.44 + k * w * 0.072
                    ctx.rectangle(x_, gy - H * hh, w * 0.062, H * hh)
                    ctx.set_source_rgb(0.2, 0.22, 0.32)
                    ctx.fill()
                    for j in range(int(hh * 6)):
                        for q in (0.012, 0.036):
                            on = (k * 7 + j * 3 + int(q * 100)) % 5 != 0
                            if on:
                                ctx.rectangle(x_ + w * q, gy - H * hh + H * 0.08 + j * H * 0.15, w * 0.013, H * 0.06)
                    ctx.set_source_rgb(1.0, 0.85, 0.45)
                    ctx.fill()
                c.lines([(xc - w * 0.5, gy - 3, xc + w * 0.5, gy - 3)], (0.5, 0.5, 0.55), width=6)   # the street
                for k in range(2):                               # cars driving
                    cxp = xc - w * 0.5 + ((t * 90 + k * 260) % (w * 0.9))
                    ctx.rectangle(cxp, gy - H * 0.14, w * 0.07, H * 0.08)
                    ctx.set_source_rgb(*[(0.9, 0.3, 0.3), (0.3, 0.6, 0.95)][k])
                    ctx.fill()
                    ctx.rectangle(cxp + w * 0.015, gy - H * 0.2, w * 0.04, H * 0.07)
                    ctx.fill()
                    for wx_ in (0.015, 0.055):
                        c.circle(cxp + w * wx_, gy - H * 0.05, H * 0.035, (0.1, 0.1, 0.12))
            elif prop == "future":
                for k, (hh, wd) in enumerate(((1.9, 0.055), (2.5, 0.06), (2.1, 0.05), (1.6, 0.045))):
                    x_ = xc - w * 0.45 + k * w * 0.1
                    ctx.new_path()
                    ctx.move_to(x_, gy)
                    ctx.line_to(x_ + w * wd * 0.15, gy - H * hh)
                    ctx.line_to(x_ + w * wd * 0.85, gy - H * hh)
                    ctx.line_to(x_ + w * wd, gy)
                    ctx.close_path()
                    ctx.set_source_rgba(0.3, 0.85, 1.0, 0.22)
                    ctx.fill_preserve()
                    ctx.set_source_rgba(0.5, 1.0, 1.0, 0.85)
                    ctx.set_line_width(2)
                    ctx.stroke()
                    for j in range(int(hh * 5)):                 # light bands
                        c.lines([(x_ + w * wd * 0.2, gy - H * (0.15 + j * 0.18), x_ + w * wd * 0.8, gy - H * (0.15 + j * 0.18))],
                                (0.6, 1.0, 1.0), width=2, alpha=0.5 + 0.5 * math.sin(t * 3 + j + k))
                    c.glow(x_ + w * wd / 2, gy - H * hh - 6, w * 0.02, (1, 0.4, 0.6), strength=0.8 * (0.5 + 0.5 * math.sin(t * 5 + k)), reach=2)
                for k in range(3):                               # flying cars: body, cabin, driver, hover glow, streaks
                    fx = xc - w * 0.55 + ((t * 110 * (1 + k * 0.35) + k * 280) % (w * 1.15))
                    fy = gy - H * (1.25 + 0.38 * k) + math.sin(t * 3 + k) * 5
                    cw_, ch_ = w * 0.11, H * 0.1
                    body = [(1, 0.45, 0.6), (0.55, 0.8, 1), (1, 0.85, 0.4)][k]
                    for j in range(4):
                        c.lines([(fx - w * (0.03 + 0.03 * j), fy + ch_ * 0.4 + j * 3, fx - w * 0.01, fy + ch_ * 0.4 + j * 3)],
                                (0.6, 1.0, 1.0), width=2, alpha=0.5 - 0.1 * j)
                    ctx.new_path()
                    ctx.move_to(fx, fy + ch_)
                    ctx.curve_to(fx, fy + ch_ * 0.2, fx + cw_ * 0.2, fy, fx + cw_ * 0.5, fy)
                    ctx.curve_to(fx + cw_ * 0.85, fy, fx + cw_, fy + ch_ * 0.3, fx + cw_, fy + ch_)
                    ctx.close_path()
                    ctx.set_source_rgb(*body)
                    ctx.fill()
                    ctx.new_path()
                    ctx.move_to(fx + cw_ * 0.3, fy + ch_ * 0.15)
                    ctx.curve_to(fx + cw_ * 0.35, fy - ch_ * 0.6, fx + cw_ * 0.75, fy - ch_ * 0.6, fx + cw_ * 0.8, fy + ch_ * 0.15)
                    ctx.close_path()
                    ctx.set_source_rgba(0.6, 0.9, 1.0, 0.8)
                    ctx.fill()
                    c.circle(fx + cw_ * 0.55, fy - ch_ * 0.1, ch_ * 0.18, (0.1, 0.1, 0.15))       # the driver
                    for wx_ in (0.2, 0.8):
                        c.glow(fx + cw_ * wx_, fy + ch_ * 1.2, w * 0.022, (0.5, 1, 1), strength=0.9, reach=2)
                        ctx.save()
                        ctx.translate(fx + cw_ * wx_, fy + ch_ * 1.05)
                        ctx.scale(1, 0.35)
                        ctx.arc(0, 0, cw_ * 0.13, 0, 2 * math.pi)
                        ctx.restore()
                        ctx.set_source_rgb(0.7, 1.0, 1.0)
                        ctx.fill()
                if 15.0 <= t < 17.0:                             # fireworks for the trillion
                    for k in range(5):
                        age = t - 15.0 - k * 0.25
                        if 0 <= age < 1.2:
                            fx, fy = xc - w * 0.3 + k * w * 0.15, gy - H * (2.0 + 0.3 * (k % 2))
                            for j in range(12):
                                a = j / 12 * 2 * math.pi
                                c.circle(fx + math.cos(a) * age * w * 0.09, fy + math.sin(a) * age * w * 0.09 + age * age * 30,
                                         4, [(1, 0.8, 0.3), (0.5, 1, 1), (1, 0.5, 0.7)][k % 3], alpha=1 - age / 1.2)
            # the figure of this era (+ its hat)
            fx = xc
            talking = holder == i and any(t0_ <= t < t1_ for t0_, t1_, _, _ in LINES) and int(t * 8) % 2
            counting = holder == i and t < 16.6 and int(t * 6) % 2
            mouth = "open" if (talking or counting) else "smile"
            cheer = prop == "future" and 15.0 <= t < 16.8
            figure(c, fx, gy, H, col, (2.6, 0.4) if cheer else (0.3, 0.2), (2.6, 0.4) if cheer else (1.2, -0.6),
                   mouth=mouth, t=t)
            hx, hy, hr = head(fx)
            if prop == "ice":                                    # messy hair + a club
                for k in range(5):
                    c.lines([(hx - hr + k * hr * 0.5, hy - hr * 0.8, hx - hr * 1.1 + k * hr * 0.55, hy - hr * 1.45)],
                            (0.75, 0.55, 0.3), width=4)
            elif prop == "farm":
                c.poly([(hx - hr * 1.6, hy - hr * 0.7), (hx + hr * 1.6, hy - hr * 0.7), (hx, hy - hr * 1.7)], (0.9, 0.8, 0.4))
            elif prop == "pyr":
                c.poly([(hx - hr * 1.2, hy - hr * 0.5), (hx + hr * 1.2, hy - hr * 0.5), (hx + hr * 1.3, hy + hr * 0.9),
                        (hx - hr * 1.3, hy + hr * 0.9)], (0.3, 0.45, 0.9), alpha=0.85)
                c.lines([(hx - hr * 1.2, hy - hr * 0.5, hx + hr * 1.2, hy - hr * 0.5)], (1, 0.82, 0.4), width=4)
            elif prop == "rome":
                ctx.new_path()
                ctx.arc(hx, hy - hr * 0.6, hr * 0.9, math.pi, 2 * math.pi)
                ctx.set_source_rgb(0.85, 0.7, 0.3)
                ctx.fill()
                c.lines([(hx - hr * 0.8, hy - hr * 1.4, hx + hr * 0.8, hy - hr * 1.4)], (0.9, 0.2, 0.2), width=8)
            elif prop == "castle":
                ctx.rectangle(hx - hr * 1.05, hy - hr * 1.1, hr * 2.1, hr * 1.3)
                ctx.set_source_rgb(0.7, 0.72, 0.8)
                ctx.fill()
                ctx.rectangle(hx - hr * 0.8, hy - hr * 0.35, hr * 1.6, hr * 0.15)
                ctx.set_source_rgb(0.1, 0.1, 0.12)
                ctx.fill()
            elif prop == "ship":
                c.poly([(hx - hr * 1.5, hy - hr * 0.7), (hx + hr * 1.5, hy - hr * 0.7), (hx, hy - hr * 1.6)], (0.2, 0.2, 0.25))
            elif prop == "future":
                ctx.rectangle(hx - hr * 0.95, hy - hr * 0.35, hr * 1.9, hr * 0.4)
                ctx.set_source_rgb(0.4, 1.0, 1.0)
                ctx.fill()
        # the baton (a glowing tablet) — flies to the next holder at each handoff
        for i in range(len(ERAS) - 1):
            th = ERAS[i + 1][0]
            if th - 0.6 <= t < th:
                u = (t - (th - 0.6)) / 0.6
                bx_ = X(ex[i]) + (X(ex[i + 1]) - X(ex[i])) * u
                by_ = gy - H * 0.75 - math.sin(math.pi * u) * H * 0.6
                break
        else:
            bx_, by_ = X(ex[holder]) + H * 0.35, gy - H * 0.7
        if t < 16.6 or t >= 18.2:
            ctx.rectangle(bx_ - H * 0.08, by_ - H * 0.11, H * 0.16, H * 0.22)
            ctx.set_source_rgb(1.0, 0.85, 0.4)
            ctx.fill()
            c.glow(bx_, by_, H * 0.2, GOLD, strength=0.6, reach=2)
        self.pos = {"A": (X(ex[holder]), gy - H * 1.25), "B": (X(ex[holder]), gy - H * 1.25)}
        # the counter: the number, the year, the progress
        yr = f"{int(round(-year)):,} BC" if year < 0 else f"{int(round(year))} AD"
        c.text_centered(f"YEAR {yr}", h * 0.205, size=w * 0.05, color=GOLD)
        c.text_centered(f"{count:,}", h * 0.258, size=w * 0.072, color=(1, 1, 1))
        bx0, bw_ = w * 0.1, w * 0.8
        ctx.rectangle(bx0, h * 0.282, bw_, h * 0.012)
        ctx.set_source_rgba(1, 1, 1, 0.2)
        ctx.fill()
        ctx.rectangle(bx0, h * 0.282, bw_ * frac, h * 0.012)
        ctx.set_source_rgb(1.0, 0.82, 0.4)
        ctx.fill()
        c.text_centered(f"{frac * 100:.1f}% of a trillion", h * 0.315, size=w * 0.032, color=(0.85, 0.87, 0.95), bold=False)
        if t >= 16.6 and t < 18.2:
            c.text_centered("<< REWIND", h * 0.35, size=w * 0.05, color=(0.85, 0.86, 0.92))
        era = ERAS[holder][1]
        if t < 5.0 or t >= 18.2:
            self.bottom("1 number every second", GOLD, 0.0 if t < 5 else 18.2, t, size=0.065)
        elif t < 12.4:
            self.bottom(f"passed on through history: {era}", (0.97, 0.97, 1.0), ERAS[holder][0], t, size=0.05)
        elif t < 15.0:
            self.bottom("today: 97.9% done", BLUE, 12.4, t, size=0.065)
        else:
            self.bottom("10¹² seconds = 31,700 years", GOLD, 15.0, t, size=0.06)

    # ------------------------------------------------------------- episode 15 (a quintillion: the whole universe)
    def ep15(self, t):
        c, w, h = self.canvas, self.L.w, self.L.h
        gy, H = self.gy, self.H * 0.72
        ctx = c.ctx
        AGE_END = 31.6888                                        # 10^18 s in billions of years
        AK = [(0.0, 0.0), (2.0, 0.2), (3.6, 1.0), (5.2, 9.26), (6.9, 9.3), (7.0, 13.6), (8.6, 13.8), (10.3, 13.8),
              (10.6, 13.8000007), (12.0, 13.8000015), (12.9, 13.800002), (13.4, 18.3), (14.8, 18.8), (15.6, 18.85), (16.2, AGE_END), (17.8, AGE_END),
              (19.4, 0.0)]
        for (t0, a0), (t1, a1) in zip(AK, AK[1:]):
            if t0 <= t <= t1:
                age = a0 + (a1 - a0) * (t - t0) / (t1 - t0)
                break
        else:
            age = 0.0
        frac = age / AGE_END
        ERAS = [(0.0, "the Big Bang", "bang"), (2.0, "the first stars", "stars"), (3.6, "galaxies", "galaxy"),
                (5.2, "the Sun and Earth", "earth"), (7.0, "dinosaurs", "dino"), (8.6, "today", "today"),
                (10.6, "robots + flying cars", "future"), (12.0, "cities on Mars", "mars"),
                (13.4, "the Milky Way hits Andromeda", "merge"), (14.8, "the Sun becomes a red giant", "redgiant"),
                (16.2, "the last stars fade", "fade")]
        GAP = w * 1.0
        ex = [w * 0.5 + i * GAP for i in range(len(ERAS))]
        holder = max(i for i, e in enumerate(ERAS) if t >= e[0]) if t < 17.8 else len(ERAS) - 1
        if t >= 17.8:
            u = smooth((t - 17.8) / 1.5)
            camx = ex[-1] + (ex[0] - ex[-1]) * u
            holder = 0 if u > 0.98 else holder
        else:
            nxt = min(len(ERAS) - 1, holder + 1)
            t_next = ERAS[nxt][0] if nxt != holder else 99
            u = smooth((t - (t_next - 0.55)) / 0.55) if t > t_next - 0.55 else 0.0
            camx = ex[holder] + (ex[nxt] - ex[holder]) * u
        X = lambda xw: xw - camx + w / 2                      # noqa: E731
        ctx.set_source_rgb(0.01, 0.01, 0.03)                   # space: no ground line except on planets
        ctx.paint()
        rng = np.random.default_rng(15)
        for k in range(160):                                     # parallax starfield
            sx = (rng.uniform(0, w * 12) - camx * 0.25) % (w * 1.2) - w * 0.1
            sy = rng.uniform(h * 0.17, h * 0.72)
            c.circle(sx, sy, rng.uniform(1, 2.6), (1, 1, 1), alpha=0.25 + 0.35 * abs(math.sin(t * 1.3 + k)))

        def ground(xc, col, line):
            ctx.rectangle(xc - GAP / 2, gy, GAP, h * 0.07)
            ctx.set_source_rgb(*col)
            ctx.fill()
            c.lines([(xc - GAP / 2, gy, xc + GAP / 2, gy)], line, width=4)

        def spiral_galaxy(cx, cy, R, rot, col, alpha=1.0):
            c.glow(cx, cy, R * 0.5, col, strength=0.6 * alpha, reach=2.2)
            for arm in range(2):
                pts = []
                for j in range(70):
                    u_ = j / 70
                    a = rot + arm * math.pi + u_ * 3.6
                    r = R * (0.08 + 0.92 * u_)
                    pts.append((cx + r * math.cos(a), cy + r * math.sin(a) * 0.45))
                for j, (px_, py_) in enumerate(pts):
                    c.circle(px_, py_, 2.2 + 3.5 * (1 - j / 70), (1, 0.95, 0.85) if j % 3 else col, alpha=alpha * (0.9 - 0.5 * j / 70))
            c.circle(cx, cy, R * 0.08, (1, 0.95, 0.8), alpha=alpha)

        def flying_car(fx, fy, cw_, ch_, body):
            for j in range(4):
                c.lines([(fx - w * (0.03 + 0.03 * j), fy + ch_ * 0.4 + j * 3, fx - w * 0.01, fy + ch_ * 0.4 + j * 3)],
                        (0.6, 1.0, 1.0), width=2, alpha=0.5 - 0.1 * j)
            ctx.new_path()
            ctx.move_to(fx, fy + ch_)
            ctx.curve_to(fx, fy + ch_ * 0.2, fx + cw_ * 0.2, fy, fx + cw_ * 0.5, fy)
            ctx.curve_to(fx + cw_ * 0.85, fy, fx + cw_, fy + ch_ * 0.3, fx + cw_, fy + ch_)
            ctx.close_path()
            ctx.set_source_rgb(*body)
            ctx.fill()
            ctx.new_path()
            ctx.move_to(fx + cw_ * 0.3, fy + ch_ * 0.15)
            ctx.curve_to(fx + cw_ * 0.35, fy - ch_ * 0.6, fx + cw_ * 0.75, fy - ch_ * 0.6, fx + cw_ * 0.8, fy + ch_ * 0.15)
            ctx.close_path()
            ctx.set_source_rgba(0.6, 0.9, 1.0, 0.8)
            ctx.fill()
            c.circle(fx + cw_ * 0.55, fy - ch_ * 0.1, ch_ * 0.18, (0.1, 0.1, 0.15))
            for wx_ in (0.2, 0.8):
                c.glow(fx + cw_ * wx_, fy + ch_ * 1.2, w * 0.022, (0.5, 1, 1), strength=0.9, reach=2)

        def robot(x, y_feet, Hr, arms_up=False, t_=0.0):
            figure(c, x, y_feet, Hr, (0.78, 0.82, 0.9), (2.6, 0.4) if arms_up else (0.3, 0.2),
                   (2.6, 0.4) if arms_up else (1.2, -0.6), mouth="smile", t=t_, head_alpha=0.0)
            hx, hy, hr = x, y_feet - 0.90 * Hr, 0.13 * Hr
            ctx.rectangle(hx - hr, hy - hr, 2 * hr, 2 * hr)
            ctx.set_source_rgb(0.7, 0.75, 0.85)
            ctx.fill()
            for sx_ in (-0.4, 0.4):
                c.circle(hx + sx_ * hr, hy - hr * 0.1, hr * 0.22, (0.3, 1.0, 1.0))
            c.lines([(hx - hr * 0.4, hy + hr * 0.45, hx + hr * 0.4, hy + hr * 0.45)], (0.2, 0.25, 0.3), width=4)
            c.lines([(hx, hy - hr, hx, hy - hr * 1.6)], (0.7, 0.75, 0.85), width=3)
            c.circle(hx, hy - hr * 1.7, hr * 0.2, (1, 0.3, 0.4), alpha=0.6 + 0.4 * math.sin(t * 6))

        def astronaut(x, y_feet, Hr):
            figure(c, x, y_feet, Hr, BLUE, (0.6, 0.6), (1.2, -0.6), mouth="open" if int(t * 6) % 2 else "smile", t=t)
            hx, hy, hr = x, y_feet - 0.90 * Hr, 0.115 * Hr
            c.ring(hx, hy, hr * 1.55, (0.9, 0.95, 1.0), width=4, alpha=0.9)
            c.circle(hx - hr * 0.6, hy - hr * 0.6, hr * 0.25, (1, 1, 1), alpha=0.5)

        figure_pos = None
        for i, (t0, name, prop) in enumerate(ERAS):
            xc = X(ex[i])
            if xc < -w * 0.7 or xc > w * 1.7:
                continue
            bob = math.sin(t * 2.2 + i) * h * 0.008
            fy = gy                                              # the counter's feet
            if prop == "bang":
                age_ = min(t, 2.0) if t < 17.8 else 2.0 * (1 - smooth((t - 18.45) / 0.93))   # collapses into frame 0
                R = w * (0.08 + 0.55 * smooth(min(age_, 2.0) / 2.0))
                for k, (col, a) in enumerate((((1, 0.95, 0.8), 0.9), ((1, 0.6, 0.3), 0.6), ((0.8, 0.3, 1.0), 0.4))):
                    c.glow(xc + w * 0.1, h * 0.45, R * (0.4 + 0.3 * k), col, strength=a * 0.8, reach=2.0)
                for k in range(60):
                    a = k * 2.399
                    r = R * (0.2 + 0.8 * ((k * 0.61) % 1.0))
                    c.circle(xc + w * 0.1 + r * math.cos(a), h * 0.45 + r * math.sin(a), 3, (1, 0.9, 0.7), alpha=0.8)
                fy = gy - h * 0.06 + bob
            elif prop == "stars":
                for k, (dx, dy, r_) in enumerate(((-0.3, -0.12, 0.05), (0.25, -0.18, 0.07), (0.1, 0.0, 0.035), (-0.15, 0.05, 0.03))):
                    px_, py_ = xc + w * dx, h * 0.42 + w * dy
                    c.glow(px_, py_, w * r_ * 3, (0.7, 0.85, 1.0), strength=0.7, reach=2.2)
                    c.circle(px_, py_, w * r_ * 0.5, (1, 1, 1))
                    for j in range(4):
                        a = j * math.pi / 2 + t * 0.3
                        c.lines([(px_, py_, px_ + math.cos(a) * w * r_ * 1.6, py_ + math.sin(a) * w * r_ * 1.6)], (1, 1, 1), width=2, alpha=0.6)
                fy = gy - h * 0.06 + bob
            elif prop == "galaxy":
                spiral_galaxy(xc + w * 0.1, h * 0.43, w * 0.36, t * 0.4, (0.7, 0.55, 1.0))
                fy = gy - h * 0.06 + bob
            elif prop == "earth":
                c.glow(xc - w * 0.32, h * 0.33, w * 0.2, (1, 0.8, 0.3), strength=0.9, reach=2.2)
                c.circle(xc - w * 0.32, h * 0.33, w * 0.08, (1, 0.9, 0.5))
                ex_, ey_, er = xc + w * 0.2, h * 0.43, w * 0.13
                c.circle(ex_, ey_, er, (0.2, 0.45, 0.9))
                for dx, dy, rr in ((-0.3, -0.2, 0.35), (0.25, 0.15, 0.4), (-0.1, 0.45, 0.25)):
                    c.circle(ex_ + er * dx, ey_ + er * dy, er * rr, (0.3, 0.7, 0.35))
                ctx.new_path()
                ctx.arc(ex_, ey_, er, -math.pi / 2, math.pi / 2)
                ctx.set_source_rgba(0, 0, 0.05, 0.45)
                ctx.fill()
                a = t * 0.8
                c.circle(ex_ + er * 1.8 * math.cos(a), ey_ + er * 0.7 * math.sin(a), er * 0.25, (0.8, 0.8, 0.82))
                fy = gy - h * 0.06 + bob
            elif prop == "dino":
                ground(xc, (0.18, 0.35, 0.15), (0.4, 0.75, 0.35))
                c.poly([(xc - w * 0.45, gy), (xc - w * 0.3, gy - H * 1.3), (xc - w * 0.24, gy - H * 1.3), (xc - w * 0.1, gy)],
                       (0.4, 0.25, 0.2))                         # a volcano
                c.glow(xc - w * 0.27, gy - H * 1.35, w * 0.05, (1, 0.4, 0.1), strength=0.8, reach=2)
                for k in range(3):
                    sm_ = (t * 0.7 + k * 0.33) % 1.0
                    c.circle(xc - w * 0.27 + sm_ * w * 0.05, gy - H * (1.45 + sm_ * 0.8), w * (0.02 + 0.03 * sm_),
                             (0.45, 0.42, 0.45), alpha=0.7 * (1 - sm_))
                # the T. rex holding the tablet in its tiny arms
                dx_, dg = xc + w * 0.05, gy
                D = H * 1.25
                rex = (0.3, 0.6, 0.3)
                c.poly([(dx_ - D * 0.75, dg - D * 0.55), (dx_ - D * 0.1, dg - D * 0.75), (dx_ + D * 0.25, dg - D * 0.7),
                        (dx_ + D * 0.3, dg - D * 0.45), (dx_ - D * 0.05, dg - D * 0.38)], rex)      # body + tail
                c.poly([(dx_ + D * 0.15, dg - D * 0.72), (dx_ + D * 0.28, dg - D * 1.05), (dx_ + D * 0.62, dg - D * 1.05),
                        (dx_ + D * 0.66, dg - D * 0.9), (dx_ + D * 0.38, dg - D * 0.85), (dx_ + D * 0.3, dg - D * 0.6)], rex)
                jaw = 0.04 * D * (1 + math.sin(t * 9)) if i == holder else 0
                c.poly([(dx_ + D * 0.36, dg - D * 0.86 + jaw), (dx_ + D * 0.64, dg - D * 0.9 + jaw), (dx_ + D * 0.6, dg - D * 0.8 + jaw)],
                       (0.25, 0.5, 0.25))
                c.circle(dx_ + D * 0.42, dg - D * 0.97, D * 0.03, (1, 1, 1))
                c.circle(dx_ + D * 0.43, dg - D * 0.97, D * 0.015, (0.05, 0.05, 0.05))
                for lx, ph in ((-0.05, 0.0), (0.12, math.pi)):                                    # legs
                    st_ = math.sin(t * 5 + ph) * D * 0.04
                    c.lines([(dx_ + D * lx, dg - D * 0.5, dx_ + D * lx + st_, dg)], rex, width=D * 0.1)
                c.lines([(dx_ + D * 0.25, dg - D * 0.6, dx_ + D * 0.36, dg - D * 0.5)], rex, width=D * 0.04)   # tiny arm
                figure_pos = (dx_ + D * 0.4, dg - D * 1.08)
                if i == holder:
                    self.tab = (dx_ + D * 0.4, dg - D * 0.5)
                fy = None
            elif prop == "today":
                ground(xc, (0.1, 0.1, 0.14), (0.5, 0.5, 0.55))
                for k, hh in enumerate((0.9, 1.45, 1.1, 1.75, 0.8)):
                    x_ = xc - w * 0.44 + k * w * 0.072
                    ctx.rectangle(x_, gy - H * hh, w * 0.062, H * hh)
                    ctx.set_source_rgb(0.2, 0.22, 0.32)
                    ctx.fill()
                    for j in range(int(hh * 6)):
                        for q in (0.012, 0.036):
                            if (k * 7 + j * 3 + int(q * 100)) % 5:
                                ctx.rectangle(x_ + w * q, gy - H * hh + H * 0.08 + j * H * 0.15, w * 0.013, H * 0.06)
                    ctx.set_source_rgb(1.0, 0.85, 0.45)
                    ctx.fill()
                fy = gy
            elif prop == "future":
                ground(xc, (0.05, 0.1, 0.14), (0.4, 0.9, 1.0))
                for k, (hh, wd) in enumerate(((1.9, 0.055), (2.5, 0.06), (2.1, 0.05), (1.6, 0.045))):
                    x_ = xc - w * 0.45 + k * w * 0.1
                    ctx.rectangle(x_, gy - H * hh, w * wd, H * hh)
                    ctx.set_source_rgba(0.3, 0.85, 1.0, 0.22)
                    ctx.fill()
                    c.lines([(x_, gy - H * hh, x_ + w * wd, gy - H * hh)], (0.5, 1, 1), width=3)
                for k in range(3):
                    flying_car(xc - w * 0.55 + ((t * 110 * (1 + k * 0.35) + k * 280) % (w * 1.15)),
                               gy - H * (1.3 + 0.38 * k) + math.sin(t * 3 + k) * 5, w * 0.11, H * 0.1,
                               [(1, 0.45, 0.6), (0.55, 0.8, 1), (1, 0.85, 0.4)][k])
                robot(xc + w * 0.36, gy, H * 0.75, t_=t)               # a helper robot walks by
                fy = gy
            elif prop == "mars":
                ground(xc, (0.55, 0.22, 0.12), (0.9, 0.45, 0.3))
                c.circle(xc - w * 0.3, h * 0.33, w * 0.05, (0.95, 0.9, 0.8), alpha=0.6)
                for k, (dx, r_) in enumerate(((-0.35, 0.09), (-0.18, 0.06), (0.3, 0.08))):
                    ctx.new_path()
                    ctx.arc(xc + w * dx, gy, w * r_, math.pi, 2 * math.pi)
                    ctx.set_source_rgba(0.6, 0.9, 1.0, 0.35)
                    ctx.fill_preserve()
                    ctx.set_source_rgba(0.8, 1.0, 1.0, 0.9)
                    ctx.set_line_width(3)
                    ctx.stroke()
                rk = xc + w * 0.42
                lift = max(0.0, t - 12.6) * H * 0.9 if i == holder else 0.0
                c.poly([(rk, gy - H * 1.5 - lift), (rk + w * 0.03, gy - H * 1.2 - lift), (rk + w * 0.03, gy - H * 0.2 - lift),
                        (rk - w * 0.03, gy - H * 0.2 - lift), (rk - w * 0.03, gy - H * 1.2 - lift)], (0.92, 0.92, 0.95))
                if lift > 0:
                    c.glow(rk, gy - H * 0.15 - lift, w * 0.04, (1, 0.6, 0.2), strength=0.9, reach=2)
                fy = gy
            elif prop == "merge":
                spiral_galaxy(xc - w * 0.12, h * 0.4, w * 0.3, t * 0.5, (0.7, 0.55, 1.0))
                spiral_galaxy(xc + w * 0.2, h * 0.47, w * 0.26, -t * 0.6 + 1, (0.5, 0.8, 1.0), alpha=0.9)
                fy = gy - h * 0.06 + bob
            elif prop == "redgiant":
                c.glow(xc + w * 0.2, h * 0.36, w * 0.55, (1, 0.35, 0.15), strength=0.9, reach=1.8)
                c.circle(xc + w * 0.2, h * 0.36, w * 0.38, (0.95, 0.35, 0.15))
                c.circle(xc - w * 0.3, h * 0.55, w * 0.04, (0.45, 0.3, 0.25))
                fy = gy - h * 0.06 + bob
            elif prop == "fade":
                for k in range(8):
                    c.circle(xc - w * 0.4 + k * w * 0.11, h * (0.25 + 0.06 * (k % 3)), 3, (1, 0.5, 0.4),
                             alpha=0.3 + 0.2 * math.sin(t + k))
                if 16.2 <= t < 18.0:                             # the quintillion firework
                    for k in range(5):
                        age_ = t - 16.25 - k * 0.25
                        if 0 <= age_ < 1.2:
                            px_, py_ = xc - w * 0.3 + k * w * 0.15, h * (0.3 + 0.05 * (k % 2))
                            for j in range(12):
                                a = j / 12 * 2 * math.pi
                                c.circle(px_ + math.cos(a) * age_ * w * 0.09, py_ + math.sin(a) * age_ * w * 0.09 + age_ * age_ * 30,
                                         4, [(1, 0.8, 0.3), (0.5, 1, 1), (1, 0.5, 0.7)][k % 3], alpha=1 - age_ / 1.2)
                fy = gy - h * 0.06 + bob
            # the counter of this era
            if fy is not None:
                if prop in ("bang", "stars", "galaxy", "earth"):
                    astronaut(xc, fy, H)
                elif prop == "today":
                    talking = i == holder and any(a_ <= t < b_ for a_, b_, _, _ in LINES) and int(t * 8) % 2
                    shock = 8.6 <= t < 10.3
                    figure(c, xc, fy, H, BLUE, (2.6, 0.4) if shock else (0.3, 0.2), (2.6, 0.4) if shock else (1.2, -0.6),
                           mouth="open" if (talking or shock) else "smile", t=t)
                else:
                    robot(xc, fy, H, arms_up=(prop == "fade" and 16.2 <= t < 17.9), t_=t)
                if i == holder:
                    figure_pos = (xc, fy - H * 1.25)
                    self.tab = (xc + H * 0.35, fy - H * 0.7)
        if 17.8 <= t < 19.4:                                     # dim the fast rewind pan (flash-safe), back to full at the seam
            ctx.rectangle(0, 0, w, h)
            ctx.set_source_rgba(0.01, 0.01, 0.03, 0.8 * math.sin(math.pi * (t - 17.8) / 1.6))
            ctx.fill()
        # the tablet flies between holders at each handoff
        tab = getattr(self, "tab", (w * 0.5, gy - H * 0.7))
        for i in range(len(ERAS) - 1):
            th = ERAS[i + 1][0]
            if th - 0.55 <= t < th:
                u = (t - (th - 0.55)) / 0.55
                tab = (tab[0] + (X(ex[i + 1]) - X(ex[i])) * u * 0.0 + 0, tab[1] - math.sin(math.pi * u) * H * 0.4)
        if t < 17.8 or t >= 19.2:
            ctx.rectangle(tab[0] - H * 0.08, tab[1] - H * 0.11, H * 0.16, H * 0.22)
            ctx.set_source_rgb(1.0, 0.85, 0.4)
            ctx.fill()
            c.glow(tab[0], tab[1], H * 0.2, GOLD, strength=0.6, reach=2)
        fp = figure_pos or (w * 0.5, gy - H * 1.25)
        self.pos = {"A": fp, "B": fp}
        # time label, the count, the progress
        ago = 13.8 - age
        if t >= 17.8 and t < 19.2:
            when = "<< REWIND"
        elif ago >= 1.0:
            when = f"{ago:.1f} BILLION YEARS AGO"
        elif ago >= 0.001:
            when = f"{ago * 1000:.0f} MILLION YEARS AGO"
        elif ago >= -0.000001 and t < 10.6:
            when = "TODAY"
        elif ago >= -0.001:
            when = f"YEAR {2026 + int(-ago * 1e9):,}"
        else:
            when = f"{-ago:.1f} BILLION YEARS FROM NOW"
        c.text_centered(when, h * 0.205, size=w * 0.045, color=GOLD)
        count = int(round(1e18 * frac))
        c.text_centered(f"{count:,}", h * 0.252, size=w * 0.052, color=(1, 1, 1))
        bx0, bw_ = w * 0.1, w * 0.8
        ctx.rectangle(bx0, h * 0.272, bw_, h * 0.012)
        ctx.set_source_rgba(1, 1, 1, 0.2)
        ctx.fill()
        ctx.rectangle(bx0, h * 0.272, bw_ * frac, h * 0.012)
        ctx.set_source_rgb(1.0, 0.82, 0.4)
        ctx.fill()
        c.text_centered(f"{frac * 100:.1f}% of a quintillion", h * 0.303, size=w * 0.032, color=(0.85, 0.87, 0.95), bold=False)
        era = ERAS[holder][1]
        if t < 2.0 or t >= 19.2:
            self.bottom("1 number every second", GOLD, 0.0 if t < 2.0 else 19.2, t, size=0.065)
        elif t < 16.2:
            self.bottom(era, (0.97, 0.97, 1.0), ERAS[holder][0], t, size=0.055)
        else:
            self.bottom("10¹⁸ seconds = 31.7 billion years", GOLD, 16.2, t, size=0.05)

    # ------------------------------------------------------------- episode 16 (counting to a million: 11.6 days)
    def ep16(self, t):
        c, w, h = self.canvas, self.L.w, self.L.h
        gy, H = self.gy, self.H
        ctx = c.ctx
        L0, L1, RW0, RW1 = 4.8, 12.4, 15.9, 16.75
        DAYS = 1e6 / 86400
        if t < L0:
            days = 0.0
            count = int(max(0.0, (t - 1.9) * 3.0)) if t >= 1.9 else 0
        elif t < L1:
            u = ((t - L0) / (L1 - L0)) ** 1.6
            days, count = DAYS * u, int(1e6 * u)
        elif t < RW0:
            days, count = DAYS, 1_000_000
        elif t < RW1:
            u = smooth((t - RW0) / (RW1 - RW0))
            days, count = DAYS * (1 - u), int(1e6 * (1 - u))
        else:
            days, count = 0.0, 0
        age = days / DAYS
        # the window: the sun and the moon swap once a day, faster and faster
        wx0, wy0, ww, wh = w * 0.56, h * 0.335, w * 0.36, h * 0.13
        p = (days + 0.3) % 1.0
        dl = 0.5 + 0.5 * math.sin(2 * math.pi * (p - 0.25))
        sky = (0.08 + 0.35 * dl, 0.10 + 0.55 * dl, 0.22 + 0.70 * dl)
        ctx.rectangle(wx0, wy0, ww, wh)
        ctx.set_source_rgb(*sky)
        ctx.fill_preserve()
        ctx.set_source_rgba(0.85, 0.88, 1.0, 0.8)
        ctx.set_line_width(5)
        ctx.stroke()
        ctx.save()
        ctx.rectangle(wx0, wy0, ww, wh)
        ctx.clip()
        if 0.25 <= p <= 0.75:
            q = (p - 0.25) / 0.5
            sx, sy = wx0 + ww * q, wy0 + wh * 0.95 - math.sin(math.pi * q) * wh * 0.75
            c.glow(sx, sy, wh * 0.14, (1.0, 0.85, 0.3), strength=0.7, reach=2.4)
            c.circle(sx, sy, wh * 0.14, (1.0, 0.9, 0.4))
        else:
            q = ((p + 0.25) % 1.0) / 0.5
            sx, sy = wx0 + ww * q, wy0 + wh * 0.95 - math.sin(math.pi * q) * wh * 0.75
            c.circle(sx, sy, wh * 0.12, (0.93, 0.94, 1.0))
            c.circle(sx + wh * 0.05, sy - wh * 0.03, wh * 0.1, sky)
            for k in range(7):
                c.circle(wx0 + ww * ((k * 0.37 + 0.11) % 1.0), wy0 + wh * ((k * 0.53 + 0.13) % 0.7), 2.5, (1, 1, 1), alpha=0.8)
        ctx.restore()
        c.lines([(wx0 + ww / 2, wy0, wx0 + ww / 2, wy0 + wh), (wx0, wy0 + wh / 2, wx0 + ww, wy0 + wh / 2)],
                (0.85, 0.88, 1.0), width=3, alpha=0.7)
        # the calendar
        cx0, cy0, cw, ch = w * 0.08, h * 0.335, w * 0.26, h * 0.13
        ctx.rectangle(cx0, cy0, cw, ch)
        ctx.set_source_rgb(0.96, 0.96, 0.98)
        ctx.fill()
        ctx.rectangle(cx0, cy0, cw, ch * 0.27)
        ctx.set_source_rgb(0.85, 0.2, 0.25)
        ctx.fill()
        c.text_centered("DAY", cy0 + ch * 0.2, size=w * 0.034, color=(1, 1, 1), cx=cx0 + cw / 2)
        c.text_centered(str(min(12, int(days) + 1)), cy0 + ch * 0.86, size=w * 0.085, color=(0.15, 0.15, 0.2), cx=cx0 + cw / 2)
        # counter
        c.text_centered(f"{int(days)} days {int((days % 1) * 24):02d} h", h * 0.205, size=w * 0.06, color=GOLD)
        c.text_centered(f"{count:,}", h * 0.262, size=w * 0.11, color=(1, 1, 1))
        c.text_centered("of counting, without sleep", h * 0.296, size=w * 0.036, color=(0.8, 0.82, 0.92), bold=False)
        if RW0 <= t < RW1:
            c.text_centered("<< REWIND", h * 0.326, size=w * 0.045, color=(0.85, 0.86, 0.92))
        # the coffee cup tower grows with the days
        for k in range(min(24, int(days * 2))):
            col_, row_ = k // 6, k % 6
            cx_, cy_ = w * 0.40 + col_ * w * 0.045, gy - (row_ + 1) * h * 0.021
            ctx.rectangle(cx_, cy_, w * 0.034, h * 0.019)
            ctx.set_source_rgb(0.92, 0.9, 0.86)
            ctx.fill()
            ctx.rectangle(cx_ + w * 0.004, cy_ + h * 0.002, w * 0.026, h * 0.004)
            ctx.set_source_rgb(0.35, 0.2, 0.12)
            ctx.fill()
        talkA = any(t0 <= t < t1 and wh_ == "A" for t0, t1, wh_, _ in LINES) and int(t * 8) % 2
        talkB = any(t0 <= t < t1 and wh_ == "B" for t0, t1, wh_, _ in LINES) and int(t * 8) % 2
        lapse = L0 <= t < L1
        ax, bx = w * 0.20, w * 0.80
        mouthA = "open" if (talkA or (lapse and int(t * 10) % 2)) else "smile"
        figure(c, ax, gy, H, BLUE, (0.3, 0.2), (0.3, 0.2), mouth=mouthA, tilt=0.05 * age, t=t)
        hcx, hcy, hr = ax, gy - 0.90 * H, 0.115 * H
        if age > 0.03:                                              # the stubble grows
            for k in range(int(26 * min(1.0, age * 2))):
                a = math.pi * (0.12 + 0.76 * ((k * 0.618) % 1.0))
                rr = hr * (0.72 + 0.25 * ((k * 0.37) % 1.0))
                c.circle(hcx + math.cos(a) * rr, hcy + math.sin(a) * rr * 0.9 + hr * 0.12, 2.2, (0.25, 0.25, 0.3), alpha=0.8)
        sleeping = days > 1.2 and not (RW0 <= t < RW1 and days < 1.2)
        figure(c, bx, gy, H, ORANGE, (0.3, 0.2), (0.3, 0.2), mouth="open" if talkB else "smile", tilt=0.35 if sleeping else 0.0, t=t)
        if sleeping:                                                # B sleeps through it: Zzz
            for k in range(3):
                zt = (t * 0.8 + k * 0.33) % 1.0
                c.text_centered("Z", gy - H * (1.05 + 0.4 * zt), size=w * (0.035 + 0.02 * k), color=(0.8, 0.85, 1.0),
                                alpha=(1 - zt) * 0.9, cx=bx + w * (0.04 + 0.025 * zt + 0.02 * k))
        if L1 <= t < L1 + 1.6:                                      # confetti
            for k in range(36):
                fx = (k * 137) % int(w)
                fy = h * 0.2 + ((t - L1) * h * 0.35 + k * 41) % (gy - h * 0.2)
                c.lines([(fx, fy, fx + 7, fy + 12)], [(1, 0.4, 0.5), (0.5, 0.9, 1), (1, 0.85, 0.3)][k % 3], width=7, alpha=0.9)
        self.pos = {"A": (hcx, gy - H * 1.05), "B": (bx, gy - H * 1.05)}
        if t < L0 or t >= RW1:
            self.bottom("1 number per second", GOLD, 0.0 if t < L0 else RW1, t, size=0.065)
        elif t < L1:
            self.bottom("…and it keeps going", (0.97, 0.97, 1.0), L0, t, size=0.06)
        else:
            self.bottom("1,000,000 s = 11.6 days", GOLD, L1, t, size=0.065)

    # ------------------------------------------------------------- episode 17 (counting to a googol)
    def ep17(self, t):
        c, w, h = self.canvas, self.L.w, self.L.h
        gy, H = self.gy, self.H
        ctx = c.ctx
        SUP = "⁰¹²³⁴⁵⁶⁷⁸⁹"

        def sup(n):
            return "".join(SUP[int(d)] for d in str(int(n)))
        # L = log10(years of counting): 0.0 -> the start, 9.7 = the Sun dies, 14 = the last stars die, 92.5 = a googol
        RW0, RW1 = 17.2, 18.8
        LS = -9.0
        if t < 4.4:
            Lg = LS
        elif t < 6.3:
            Lg = LS + (9.7 - LS) * smooth((t - 4.4) / 1.9)
        elif t < 8.0:
            Lg = 9.7
        elif t < 10.0:
            Lg = 9.7 + 4.3 * smooth((t - 8.0) / 2.0)
        elif t < 11.7:
            Lg = 14.0
        elif t < 13.4:
            Lg = 14.0 + 78.5 * smooth((t - 11.7) / 1.7)
        elif t < RW0:
            Lg = 92.5
        elif t < RW1:
            Lg = 92.5 + (LS - 92.5) * smooth((t - RW0) / (RW1 - RW0))
        else:
            Lg = LS
        e = Lg + 7.5                                                # log10(count)
        dark = smooth((Lg - 9.7) / 1.0) * 0.55 + smooth((Lg - 13.0) / 1.5) * 0.4
        # stars: they go out with the last of the stars (L 12 -> 14)
        sa = 1.0 - smooth((Lg - 12.0) / 2.0)
        for k in range(150):
            sx_, sy_ = (k * 197) % int(w), h * 0.17 + ((k * 331) % int(gy - h * 0.2))
            c.circle(sx_, sy_, 1.6 + (k % 3) * 0.7, (1, 1, 1), alpha=sa * (0.35 + 0.5 * (0.5 + 0.5 * math.sin(t * 2 + k))))
        # the Sun: swells, collapses, goes out (video time, while L waits at 9.7)
        sxx, syy, r0 = w * 0.82, h * 0.375, w * 0.05
        if t < 6.3:
            rs, col, al = r0 * (1.0 + 2.2 * smooth((Lg - 9.2) / 0.5)), (1.0, 0.85 - 0.45 * smooth((Lg - 9.2) / 0.5), 0.3 - 0.1 * smooth((Lg - 9.2) / 0.5)), 1.0
        elif t < 6.9:
            u = smooth((t - 6.3) / 0.6)
            rs, col, al = r0 * (3.2 - 2.95 * u), (1.0 - 0.1 * u, 0.4 + 0.5 * u, 0.2 + 0.75 * u), 1.0
        elif t < 8.0:
            rs, col, al = r0 * 0.25, (0.9, 0.9, 0.98), 1.0 - smooth((t - 6.9) / 1.0)
        else:
            rs, col, al = r0 * 0.25, (0.9, 0.9, 0.98), 0.0
        if RW0 <= t < RW1:
            u = smooth((t - RW0) / (RW1 - RW0))
            rs, col, al = r0, (1.0, 0.85, 0.3), u
        elif t >= RW1:
            rs, col, al = r0, (1.0, 0.85, 0.3), 1.0
        elif t < 4.4 or Lg < 9.2:
            rs, col, al = r0, (1.0, 0.85, 0.3), 1.0
        if al > 0:
            c.glow(sxx, syy, rs, col, strength=0.8 * al, reach=2.6)
            c.circle(sxx, syy, rs, col, alpha=al)
        # the darkness
        if dark > 0:
            ctx.rectangle(0, 0, w, h)
            ctx.set_source_rgba(0.0, 0.0, 0.0, min(0.97, dark))
            ctx.fill()
        # counters
        if e < 0.5 or t < 4.4:
            n_real = int(max(0.0, (t - 1.9) * 3.0)) if 1.9 <= t < 4.4 else 0
            ctext = f"{n_real:,}"
        elif e < 9:
            ctext = f"{int(10 ** e):,}"
        else:
            ctext = f"10{sup(e)}"
        if Lg < -1:
            ytext = "0 years"
        elif Lg < 9:
            ytext = f"{10 ** Lg:,.0f} year" + ("" if round(10 ** Lg) == 1 else "s")
        elif 9.69 < Lg < 9.71:
            ytext = "5 billion years"
        elif 13.99 < Lg < 14.01:
            ytext = "100 trillion years"
        elif Lg < 91:
            ytext = f"10{sup(Lg)} years"
        else:
            ytext = "3.2 × 10⁹² years" if t < RW0 else f"10{sup(Lg)} years"
        c.text_centered("1 number per second", h * 0.205, size=w * 0.05, color=GOLD)
        c.text_centered(ctext, h * 0.262, size=w * 0.115 if len(ctext) < 12 else w * 0.09, color=(1, 1, 1))
        c.text_centered(ytext + " of counting", h * 0.300, size=w * 0.04, color=(0.8, 0.82, 0.92), bold=False)
        if 6.3 <= t < 8.0:
            c.text_centered("THE SUN DIES", h * 0.335, size=w * 0.05, color=(1.0, 0.5, 0.35))
        if 10.0 <= t < 11.7:
            c.text_centered("THE LAST STAR DIES", h * 0.335, size=w * 0.05, color=(0.75, 0.85, 1.0))
        if RW0 <= t < RW1:
            c.text_centered("<< REWIND", h * 0.335, size=w * 0.045, color=(0.85, 0.86, 0.92))
        # the two of them
        talkA = any(t0 <= t < t1 and wh_ == "A" for t0, t1, wh_, _ in LINES) and int(t * 8) % 2
        lapse = 4.4 <= t < 13.4
        ax = w * 0.22
        if dark > 0.1:
            c.glow(ax, gy - H * 0.5, H * 0.9, (0.7, 0.8, 1.0), strength=0.35 * min(1.0, dark * 1.5), reach=1.8)
        figure(c, ax, gy, H, BLUE, (0.3, 0.2), (0.3, 0.2), mouth="open" if (talkA or (lapse and int(t * 10) % 2)) else "smile", t=t)
        bx_off = 0.0
        if 6.9 <= t < RW0:
            bx_off = w * 0.45 * smooth((t - 6.9) / 0.8)
        elif RW0 <= t < RW1:
            bx_off = w * 0.45 * (1 - smooth((t - RW0) / (RW1 - RW0)))
        bx = w * 0.78 + bx_off
        if bx < w * 1.1 and not (6.9 <= t < RW0 and bx_off > w * 0.44):
            figure(c, bx, gy, H, ORANGE, (0.3, 0.2), (0.3, 0.2), mouth="smile", t=t)
        self.pos = {"A": (ax, gy - H * 1.05), "B": (w * 0.78, gy - H * 1.05)}
        if t < 4.4 or t >= RW1:
            self.bottom("A GOOGOL = 1 with 100 zeros", GOLD, 0.0 if t < 4.4 else RW1, t, size=0.056)
        elif t < 13.4:
            self.bottom("…and it keeps going", (0.97, 0.97, 1.0), 4.4, t, size=0.06)
        elif t < RW0:
            self.bottom("1 GOOGOL = 3.2 × 10⁹² years", GOLD, 13.4, t, size=0.055)

    def ep18(self, t):
        c, w, h = self.canvas, self.L.w, self.L.h
        gy, H = self.gy, self.H
        ctx = c.ctx
        SUP = "⁰¹²³⁴⁵⁶⁷⁸⁹"
        SOFT_ = (0.8, 0.82, 0.92)

        def sup(n):
            return "".join(SUP[int(d)] for d in str(int(n)))
        Lc = ep18_L(t)
        YR = math.log10(365.25 * 86400)
        Ly = (Lc - YR) if Lc is not None else -9.0             # log10(years of counting)
        rew = EP18_RW0 <= t < EP18_RW1
        dark = smooth((Ly - 9.7) / 1.0) * 0.5 + smooth((Ly - 13.0) / 1.5) * 0.35 + smooth((Ly - 99.0) / 2.0) * 0.1
        sa = 1.0 - smooth((Ly - 12.0) / 2.0)
        for k in range(150):
            sx_, sy_ = (k * 197) % int(w), h * 0.17 + ((k * 331) % int(gy - h * 0.2))
            c.circle(sx_, sy_, 1.6 + (k % 3) * 0.7, (1, 1, 1), alpha=sa * (0.35 + 0.5 * (0.5 + 0.5 * math.sin(t * 2 + k))))
        # the Sun: swells red and goes out while the count waits at 5 billion years
        sxx, syy, r0 = w * 0.84, h * 0.40, w * 0.05
        if Ly < 9.2 or t >= EP18_RW1:
            rs, col, al = r0, (1.0, 0.85, 0.3), 1.0
        elif rew:
            rs, col, al = r0, (1.0, 0.85, 0.3), smooth((t - EP18_RW0) / (EP18_RW1 - EP18_RW0))
        elif t < 6.6:
            u = smooth((t - 6.0) / 0.6)
            rs, col, al = r0 * (1 + 1.8 * u), (1.0, 0.85 - 0.45 * u, 0.3 - 0.1 * u), 1.0
        elif t < 7.2:
            u = smooth((t - 6.6) / 0.6)
            rs, col, al = r0 * (2.8 - 2.55 * u), (1.0, 0.4 + 0.5 * u, 0.2 + 0.75 * u), 1.0 - u
        else:
            rs, col, al = r0, (1.0, 0.85, 0.3), 0.0
        if al > 0:
            c.glow(sxx, syy, rs, col, strength=0.8 * al, reach=2.6)
            c.circle(sxx, syy, rs, col, alpha=al)
        if dark > 0:
            ctx.rectangle(0, 0, w, h)
            ctx.set_source_rgba(0.0, 0.0, 0.0, min(0.95, dark))
            ctx.fill()
        # the computer: a monitor printing the count exactly the way a computer prints numbers
        mx, my, mw, mh = w * 0.53, gy - H * 0.95, w * 0.44, H * 0.55
        glitch = 14.95 <= t < 15.35
        inf = 15.35 <= t < EP18_RW0
        scol = RED if inf else (0.4, 1.0, 0.6)
        c.glow(mx, my, mw * 0.55, scol, strength=0.18 + 0.25 * dark, reach=1.5)
        ctx.rectangle(mx - mw / 2 - 8, my - mh / 2 - 8, mw + 16, mh + 16)
        ctx.set_source_rgb(0.32, 0.34, 0.45)
        ctx.fill()
        ctx.rectangle(mx - mw / 2, my - mh / 2, mw, mh)
        ctx.set_source_rgb(0.02, 0.05, 0.04)
        ctx.fill()
        c.lines([(mx, my + mh / 2 + 8, mx, gy), (mx - mw * 0.2, gy, mx + mw * 0.2, gy)], (0.32, 0.34, 0.45), width=10)
        c.text_centered("COMPUTER", my - mh / 2 - h * 0.014, size=w * 0.032, color=(0.75, 0.8, 0.95), cx=mx)
        n_real = int(max(0.0, (t - 1.9) * 3.0)) if 1.9 <= t < 4.4 else 0
        if Lc is None:
            scr = str(n_real)
        elif Lc < 15:
            scr = str(int(round(10 ** Lc)))
        else:
            e_ = int(math.floor(Lc + 1e-9))
            scr = f"{10 ** (Lc - e_):.3f}e+{e_}"
        if glitch:
            k = int(t * 40)
            scr = "".join("01#%e+9"[(k * 7 + j * 3) % 7] for j in range(10))
        if inf:
            scr = "Infinity"
        c.text_centered("> print(count)", my - mh * 0.24, size=mh * 0.13, color=(0.4, 0.75, 0.55), cx=mx, bold=False)
        c.text_centered(scr, my + mh * 0.18, size=mh * 0.30, color=scol, cx=mx, max_w=mw * 0.9)
        # the counter on top (human-readable) + the -illion name
        if Lc is None:
            big, name = f"{n_real:,}", ""
        elif Lc < 9:
            big, name = f"{int(10 ** Lc):,}", ""
        else:
            e_ = int(math.floor(Lc + 1e-9))
            m_ = 10 ** (Lc - e_)
            big = (f"{m_:.1f} × 10{sup(e_)}" if m_ >= 1.05 else f"10{sup(e_)}")
            k_ = (e_ - 3) // 3
            name = f"= {10 ** (e_ - 3 - 3 * k_):,} {illion(min(100, k_))}" if 1 <= k_ <= 100 else ""
        pop = 1.0
        if 13.9 <= t < 14.6:
            pop = 1.0 + 0.35 * math.exp(-(t - 13.9) / 0.12)
            name = "= 1 CENTILLION"
        if 14.6 <= t < EP18_RW0:
            big, name = "2¹⁰²⁴", "≈ 1.8 × 10³⁰⁸"
        c.text_centered("1 number per second", h * 0.205, size=w * 0.045, color=GOLD)
        c.text_centered(big, h * 0.262, size=w * (0.115 if len(big) < 12 else 0.09), color=(1, 1, 1))
        if name:
            c.text_centered(name, h * 0.298, size=w * 0.042 * pop, color=GOLD if "CENT" in name else SOFT_,
                            max_w=w * 0.94)
        if Lc is None or Ly < -1:
            ytext = "0 years"
        elif Ly < 9:
            ytext = f"{10 ** Ly:,.0f} years"
        elif 9.69 < Ly < 9.71:
            ytext = "5 billion years"
        elif 13.99 < Ly < 14.01:
            ytext = "100 trillion years"
        else:
            e_ = int(math.floor(Ly))
            m_ = 10 ** (Ly - e_)
            ytext = f"{m_:.1f} × 10{sup(e_)} years" if m_ >= 1.05 else f"10{sup(e_)} years"
        c.text_centered(ytext + " of counting", h * 0.330, size=w * 0.036, color=SOFT_, bold=False)
        for t0, t1, txt, cc in ((6.0, 7.2, "THE SUN DIES", (1.0, 0.5, 0.35)),
                                (8.2, 9.2, "THE LAST STAR GOES OUT", (0.75, 0.85, 1.0)),
                                (10.3, 11.0, "THE LAST BLACK HOLE EVAPORATES", (0.8, 0.6, 1.0))):
            if t0 <= t < t1:
                c.text_centered(txt, h * 0.365, size=w * 0.045, color=cc, max_w=w * 0.94)
        if rew:
            c.text_centered("<< REWIND", h * 0.365, size=w * 0.045, color=(0.85, 0.86, 0.92))
        # the two of them
        talkA = any(t0 <= t < t1 and wh_ == "A" for t0, t1, wh_, _ in LINES) and int(t * 8) % 2
        lapse = 4.4 <= t < 15.0
        ax = w * 0.15
        if dark > 0.1:
            c.glow(ax, gy - H * 0.5, H * 0.9, (0.7, 0.8, 1.0), strength=0.35 * min(1.0, dark * 1.5), reach=1.8)
            c.glow(w * 0.88, gy - H * 0.5, H * 0.8, (1.0, 0.75, 0.5), strength=0.25 * min(1.0, dark * 1.5), reach=1.8)
        figure(c, ax, gy, H, BLUE, (0.3, 0.2), (0.3, 0.2),
               mouth="open" if (talkA or (lapse and int(t * 10) % 2)) else "smile", t=t,
               dizzy=1.0 if 15.0 <= t < 16.2 else 0.0)
        bx = w * 0.88
        figure(c, bx, gy, H * 0.92, ORANGE, (1.1, 1.0) if 16.2 <= t < 17.6 else (0.3, 0.2), (0.3, 0.2), mouth="smile",
               t=t, look=-0.6)
        self.pos = {"A": (ax, gy - H * 1.05), "B": (bx, gy - H * 0.97)}
        if 15.4 <= t < EP18_RW0:
            self.bottom("Computers stop at 2¹⁰²⁴, then say \"Infinity\"", GOLD, 15.4, t, size=0.046)
        elif t < 4.4 or t >= EP18_RW1:
            self.bottom("Count until the computer gives up", GOLD, 0.0 if t < 4.4 else EP18_RW1, t, size=0.05)
        elif lapse:
            self.bottom("…and it keeps going", (0.97, 0.97, 1.0), 4.4, t, size=0.06)

    def ep19(self, t):
        c, w, h = self.canvas, self.L.w, self.L.h
        gy, H = self.gy, self.H
        ctx = c.ctx
        gone = pot_gone_at(t)
        kg = 100.0 - gone
        water = (kg - 1.0) / kg * 100
        drying = POT_T0 <= t < POT_T1
        # the sun dries them
        sa = 0.4 + 0.6 * (min(1.0, (t - POT_T0 + 0.5) / 0.5) if t >= POT_T0 - 0.5 else 0.0) * (1.0 if t < POT_RW0 else 0.3)
        c.glow(w * 0.86, h * 0.25, w * 0.05, (1.0, 0.8, 0.3), strength=0.6 * sa, reach=2.4)
        c.circle(w * 0.86, h * 0.25, w * 0.032, (1.0, 0.85, 0.35), alpha=0.5 + 0.5 * sa)
        # the grid: 100 squares = 100 kg
        cs = w * 0.046
        gx0, gy0 = w / 2 - 5 * cs, h * 0.25
        n_gone = int(gone)
        frac = gone - n_gone
        gone_set = set(POT_GONE[:n_gone])
        for i in range(100):
            r, q = divmod(i, 10)
            x, y = gx0 + q * cs, gy0 + r * cs
            if i in gone_set:
                ctx.rectangle(x + 3, y + 3, cs - 6, cs - 6)
                ctx.set_source_rgba(0.5, 0.6, 0.9, 0.25)
                ctx.set_line_width(1.5)
                ctx.stroke()
                continue
            dy = 0.0
            al = 1.0
            if n_gone < 50 and i == POT_GONE[n_gone] and frac > 0:          # this one is rising as steam
                dy = -frac * cs * 1.2
                al = 1 - frac
            col = (0.62, 0.40, 0.22) if i == POT_DRY else (0.30, 0.62, 1.0)
            ctx.rectangle(x + 3, y + 3 + dy, cs - 6, cs - 6)
            ctx.set_source_rgba(*col, al)
            ctx.fill()
        if t >= 13.7 and t < POT_RW0 + 0.3:                                # the dry kilo, highlighted
            r, q = divmod(POT_DRY, 10)
            x, y = gx0 + q * cs + cs / 2, gy0 + r * cs + cs / 2
            c.glow(x, y, cs * 1.2, (1.0, 0.8, 0.4), strength=0.7, reach=2.0)
            c.ring(x, y, cs * 0.75, GOLD, width=4)
        for k in range(6 if drying else 0):                                  # steam
            ph = (t * 0.9 + k / 6) % 1.0
            c.circle(gx0 + cs * (1 + 8 * ((k * 0.37) % 1)), gy0 - ph * h * 0.05, cs * 0.18 * (1 + ph), (0.85, 0.9, 1.0),
                     alpha=0.35 * (1 - ph))
        # the numbers
        pop = 1.0 + (0.25 * math.exp(-(t - POT_T1) / 0.15) if t >= POT_T1 else 0.0)
        c.text_centered(f"{kg:.0f} kg", h * 0.205, size=w * 0.10 * pop, color=(1, 1, 1))
        c.text_centered(f"water: {water:.1f}%", h * 0.237, size=w * 0.042, color=(0.45, 0.75, 1.0))
        # the two of them (the sack sits between them)
        sx_ = w * 0.5
        ctx.new_path()
        ctx.save()
        ctx.translate(sx_, gy - H * 0.22)
        ctx.scale(1.0, 0.8)
        ctx.arc(0, 0, H * 0.3 * (0.75 + 0.25 * kg / 100), 0, 2 * math.pi)
        ctx.restore()
        ctx.set_source_rgb(0.55, 0.38, 0.22)
        ctx.fill()
        c.text_centered("POTATOES", gy - H * 0.2, size=w * 0.03, color=(0.95, 0.85, 0.7), cx=sx_)
        talkA = any(t0 <= t < t1 and wh_ == "A" for t0, t1, wh_, _ in LINES) and int(t * 8) % 2
        ax, bx = w * 0.12, w * 0.88
        figure(c, ax, gy, H, BLUE, (0.3, 0.2), (0.3, 0.2), mouth="open" if talkA else ("open" if 12 <= t < 13.6 else "smile"),
               t=t, dizzy=1.0 if 12.2 <= t < 13.6 else 0.0)
        figure(c, bx, gy, H, ORANGE, (1.1, 1.0) if 13.7 <= t < 16.4 else (0.3, 0.2), (0.3, 0.2), mouth="smile", t=t,
               look=-0.6)
        self.pos = {"A": (ax, gy - H * 1.05), "B": (bx, gy - H * 1.05)}
        if t < POT_T0:
            self.bottom("1 square = 1 kg  ·  brown = the dry part", GOLD, 0.0, t, size=0.045)
        elif t < POT_T1:
            self.bottom("…the water evaporates", (0.97, 0.97, 1.0), POT_T0, t, size=0.06)
        elif t < POT_RW0:
            self.bottom("1 kg is 2% of 50 kg  →  98% water", GOLD, POT_T1, t, size=0.05)
        else:
            self.bottom("<< REWIND", (0.85, 0.86, 0.92), POT_RW0, t, size=0.05)

    def ep20(self, t):
        c, w, h = self.canvas, self.L.w, self.L.h
        gy, H = self.gy, self.H
        ctx = c.ctx
        tau, p, mode = zeno_state(t)
        a_m, t_m = 10 * tau, 100 + 5 * tau
        base = w * 0.80 / 300.0
        zx = w * 0.62
        sc = base * 2 ** p

        def X(m):
            return zx + (m - 200) * sc
        # the ground ruler: tick spacing follows the zoom so it always reads
        step = 50.0 / 2 ** math.floor(p)
        m0 = 200 - (zx + w * 0.1) / sc
        m1 = 200 + (w * 1.1 - zx) / sc
        k0 = math.floor(m0 / step)
        segs = []
        for k in range(k0, k0 + int((m1 - m0) / step) + 2):
            m = k * step
            xx = X(m)
            if -10 < xx < w + 10:
                segs.append((xx, gy, xx, gy + h * 0.015))
                lab = f"{m:g} m" if step >= 1 else f"{m:.2f} m"
                c.text_centered(lab, gy + h * 0.038, size=w * 0.026, color=(0.7, 0.75, 0.9), cx=xx, bold=False)
        c.lines(segs, (0.75, 0.78, 0.9), width=2, alpha=0.6)
        fx = X(300)
        if -10 < fx < w + 10:                                               # the finish line
            c.lines([(fx, gy - H * 1.2, fx, gy)], (1, 1, 1), width=4, alpha=0.8)
            c.text_centered("FINISH", gy - H * 1.25, size=w * 0.03, color=(1, 1, 1), cx=fx)
        mx = X(200)
        if mode in ("zeno", "out") and -10 < mx < w + 10:                   # where they will meet
            c.lines([(mx, gy - H * 0.3, mx, gy)], GOLD, width=2, alpha=0.5)
        running = mode in ("zeno", "real")
        self.turtle(X(t_m), gy, H * 0.55, t, moving=running, shock=mode in ("real", "done") and tau > 20)
        ax = X(a_m)
        figure(c, ax, gy, H, BLUE, (0.3, 0.6) if running else (0.3, 0.2), (0.3, 0.6) if running else (0.3, 0.2),
               walk=(t * 2.2) % 1.0 if running else 0.0, mouth="open" if 5.4 <= t < 6.9 else "smile", t=t)
        bx = w * 0.93                                                        # orange watches from the side
        figure(c, bx, gy, H * 0.85, ORANGE, (0.3, 0.2), (1.1, 1.0) if 7.4 <= t < 9.7 else (0.3, 0.2), mouth="smile",
               t=t, look=-0.6)
        self.pos = {"A": (ax, gy - H * 1.05), "B": (bx, gy - H * 0.9)}
        # the race clock and the step
        c.text_centered(f"race clock: {tau:.2f} s" if tau < 19.99 or mode != "zeno" else "race clock: 19.99 s",
                        h * 0.205, size=w * 0.06, color=(1, 1, 1))
        if mode == "zeno":
            k = min(ZEN_STEPS, int(p) + 1)
            gap = 100 / 2 ** (k - 1)
            c.text_centered(f"STEP {k}:  run {gap:g} m  ·  the turtle moves {gap / 2:g} m", h * 0.25, size=w * 0.038,
                            color=GOLD, max_w=w * 0.94)
            c.text_centered(f"zoom ×{2 ** p:,.0f}", h * 0.285, size=w * 0.034, color=(0.7, 0.75, 0.95), bold=False)
            terms = ["10", "5", "2.5", "1.25", "0.625", "0.3125"][:k]
            self.bottom(" + ".join(terms) + " + …", GOLD, ZEN_P0, t, size=0.05)
        elif mode in ("out", "real", "done"):
            c.text_centered("REAL TIME", h * 0.25, size=w * 0.06, color=(0.45, 1.0, 0.55))
            if tau >= 20:
                k = t - (ZEN_R0 + 20 / 30 * (ZEN_R1 - ZEN_R0))
                pop = 1 + 0.3 * math.exp(-max(0.0, k) / 0.15)
                c.text_centered("PASSED at exactly 20 s", h * 0.295, size=w * 0.055 * pop, color=GOLD)
            self.bottom("10 + 5 + 2.5 + 1.25 + …  =  20 s", GOLD, ZEN_OUT, t, size=0.055)
        elif mode == "rewind":
            self.bottom("<< REWIND", (0.85, 0.86, 0.92), ZEN_RW0, t, size=0.05)
        else:
            self.bottom("Blue: 10 m/s  ·  turtle: 5 m/s, 100 m ahead", GOLD, 0.0, t, size=0.045)

    def draw(self, f, rule):
        L, c = self.L, self.canvas
        w, h = L.w, L.h
        t = f * DT
        self.gy, self.H = h * 0.68, h * 0.205
        self.bg()
        if EP == 1:
            self.ep1(t)
            pos = {"A": (w * 0.22, self.gy - self.H * 1.05)}
            bxp = w * 0.74 + (1 - smooth((t - 13.4) / 0.8)) * w * 0.45
            pos["B"] = (bxp, self.gy - self.H * 1.05)
            pass
        elif EP == 2:
            self.ep2(t)
            pos = {"A": (w * 0.22, self.gy - self.H * 1.05), "B": (w * 0.78, self.gy - self.H * 1.05)}
        else:
            self.pos = None
            {3: self.ep3, 4: self.ep4, 5: self.ep5, 6: self.ep6, 7: self.ep7, 8: self.ep8, 9: self.ep9,
             10: self.ep10, 11: self.ep11, 12: self.ep12, 13: self.ep13, 14: self.ep14, 15: self.ep15,
             16: self.ep16, 17: self.ep17, 18: self.ep18, 19: self.ep19, 20: self.ep20}[EP](t)
            pos = self.pos or {"A": (w * 0.12, self.gy - self.H * 1.05), "B": (w * 0.88, self.gy - self.H * 1.05)}
        self.say(t, pos)
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


# ---------------------------------------------------------------- sound (original)
def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def sound_bed():
    n = int(round(T_LOOP * SR))
    out = np.zeros(n + 2 * SR)
    rng = np.random.default_rng(9)

    def add(t0, sig, g=1.0):
        i0 = int(t0 * SR)
        sig = sig[: max(0, len(out) - i0)]                     # never run past the buffer
        out[i0:i0 + len(sig)] += g * sig

    def tone(f, dur, decay, harm=((1, 1.0), (2, 0.3))):
        tv = np.arange(int(dur * SR)) / SR
        return sum(a * np.sin(2 * np.pi * f * k * tv) for k, a in harm) * np.exp(-tv / decay)

    # plucked loop C G Am F, 100 BPM, 8ths
    beat = 0.6
    prog = [(48, (60, 64, 67)), (43, (59, 62, 67)), (45, (60, 64, 69)), (41, (60, 65, 69))]
    tb, b = 0.0, 0
    while tb < T_LOOP:
        root, ch = prog[b % 4]
        add(tb, tone(hz(root), 1.2, 0.35), 0.10)
        for e in range(8):
            m = ch[(e * 2) % 3] + (12 if e % 4 == 3 else 0)
            add(tb + e * beat / 2, tone(hz(m), 0.3, 0.09, ((1, 1.0), (2, 0.5), (3, 0.2))), 0.035)
        tb += 4 * beat
        b += 1
    # blip voices
    for t0, t1, who, text in LINES:
        base = 700 if who == "A" else 420
        for i in range(0, len(text), 2):
            if text[i] in " .…,":
                continue
            tt = t0 + i / CPS
            if tt >= t1:
                break
            f = base * (1 + 0.12 * rng.standard_normal())
            tv = np.arange(int(0.055 * SR)) / SR
            sig = np.sign(np.sin(2 * np.pi * f * tv)) * 0.4 + np.sin(2 * np.pi * f * tv)
            add(tt, sig * np.clip(tv / 0.004, 0, 1) * np.exp(-tv / 0.03), 0.05)

    def ding(t0):
        for m in (84, 88, 91):
            add(t0, tone(hz(m), 1.2, 0.4, ((1, 1.0), (2.76, 0.25))), 0.06)

    def pop(t0, m=72):
        tv = np.arange(int(0.09 * SR)) / SR
        f = hz(m) * (1 + 1.5 * tv / 0.09)
        add(t0, np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tv / 0.04), 0.12)

    def boom(t0, g=0.5):
        tv = np.arange(int(0.8 * SR)) / SR
        add(t0, np.sin(2 * np.pi * np.cumsum(40 + 90 * np.exp(-tv / 0.05)) / SR) * np.exp(-tv / 0.3), g)
        add(t0, np.diff(np.concatenate([[0], rng.standard_normal(len(tv))])) * np.exp(-tv / 0.25), 0.12)

    if EP == 1:
        boom(0.6, 0.25)                                         # ERROR
        for k in range(3):
            pop(2.6 + 0.07 * k, 67 + 4 * k)
        for i in range(6):
            pop(4.0 + 0.12 * i, 72 + 2 * i)
            pop(7.5 + 0.12 * i, 72 + 2 * i)
        ding(5.0)
        ding(8.4)
        tv = np.arange(int(0.35 * SR)) / SR                     # poof
        add(9.4, np.diff(np.concatenate([[0], rng.standard_normal(len(tv))])) * np.exp(-tv / 0.1), 0.08)
        for k in range(4):                                     # "?" wobble while cookies hover
            pop(11.4 + 0.45 * k, 79 - 3 * k)
        ding(15.2)
        for k, m in enumerate((62, 61, 60, 59)):               # sad trombone (wah wah wah waaah)
            dur = 0.28 if k < 3 else 0.9
            tv = np.arange(int(dur * SR)) / SR
            f = hz(m - 12) * (1 - 0.03 * tv / dur) * (1 + 0.012 * np.sin(2 * np.pi * 6 * tv) * (k == 3))
            ph = 2 * np.pi * np.cumsum(f) / SR
            sig = sum(np.sin(j * ph) / j for j in range(1, 8)) * np.clip(tv / 0.03, 0, 1) * np.clip((dur - tv) / 0.06, 0, 1)
            add(18.4 + 0.3 * k, sig, 0.10)
        for k in range(3):                                     # crunch
            tv = np.arange(int(0.12 * SR)) / SR
            add(19.95 + 0.18 * k, rng.standard_normal(len(tv)) * np.exp(-tv / 0.03), 0.10)
    elif EP == 2:
        for k in range(5):                                     # each zoom step
            pop(2.8 + 1.1 * k, 72 + 3 * k)
        for k, tr in enumerate((8.2, 9.4, 10.6)):
            pop(tr, 76 + 3 * k)
        ding(11.8)
        boom(13.0, 0.55)                                       # the head explodes
        for k in range(6):
            pop(13.1 + 0.08 * k, 90 - 4 * k)
        tv = np.arange(int(0.5 * SR)) / SR                     # head comes back (rising swoop)
        f = 300 * (1 + 3 * tv / 0.5)
        add(14.6, np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tv / 0.25), 0.08)
        ding(16.0)
    elif EP == 3:
        def creak(t0):
            tv = np.arange(int(0.45 * SR)) / SR
            f = 180 + 500 * tv / 0.45 + 40 * np.sin(2 * np.pi * 23 * tv)
            ph = 2 * np.pi * np.cumsum(f) / SR
            add(t0, (np.sign(np.sin(ph)) * 0.3 + np.sin(ph)) * np.exp(-tv / 0.3), 0.04)

        def baa(t0):
            tv = np.arange(int(0.7 * SR)) / SR
            f = 310 * (1 + 0.07 * np.sin(2 * np.pi * 7.5 * tv))
            ph = 2 * np.pi * np.cumsum(f) / SR
            sig = sum(np.sin(k * ph) * a for k, a in ((1, 0.5), (2, 0.6), (3, 1.0), (4, 0.7), (5, 0.4)))
            add(t0, sig * np.clip(tv / 0.05, 0, 1) * np.clip((0.7 - tv) / 0.2, 0, 1), 0.05)

        pop(2.4, 76)
        creak(4.6)
        baa(5.0)
        for k, tr in enumerate((11.2, 12.4, 13.6)):
            pop(tr, 72 + 3 * k)
        ding(14.8)
        pop(16.0, 79)
        creak(17.2)
        ding(17.4)
        for k in range(10):
            pop(17.3 + 0.07 * k, 80 + (k % 5) * 2)
        creak(20.5)
        baa(20.9)
    elif EP == 4:
        last = -1.0
        for i in range(2, 70):                                 # one pop per person (thinned when they rush in)
            ta = appear_t(i)
            if ta - last >= 0.06:
                pop(ta, 64 + (i % 12) * 2)
                last = ta
        ding(T23)
        ding(T70)
        boom(23.35, 0.35)                                     # A falls over
        tv = np.arange(int(0.5 * SR)) / SR                    # dizzy whistle
        f = 900 * (1 - 0.5 * tv / 0.5)
        add(23.5, np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tv / 0.3), 0.05)
    elif EP == 5:
        last = -1.0
        for nn in range(1, 43):                                 # one "fwip" per fold (thinned when fast)
            lo, hi = 4.6, 15.0
            for _ in range(40):
                mid = (lo + hi) / 2
                if folds_at(mid) >= nn:
                    hi = mid
                else:
                    lo = mid
            if hi - last >= 0.07:
                tv = np.arange(int(0.08 * SR)) / SR
                nz = np.diff(np.concatenate([[0], rng.standard_normal(len(tv))]))
                add(hi, nz * np.exp(-tv / 0.03), 0.10)
                pop(hi, 60 + min(nn, 40))
                last = hi
        tv = np.arange(int(1.2 * SR)) / SR                     # whoosh into space
        add(13.0, np.diff(np.concatenate([[0], rng.standard_normal(len(tv))])) * (tv / 1.2) ** 2, 0.06)
        ding(15.1)
        boom(15.1, 0.25)
    elif EP == 6:
        pop(2.0, 79)
        ding(5.5)
        tv = np.arange(int(0.5 * SR)) / SR                     # meow (gliding tone)
        f = 700 * (1 + 0.6 * np.sin(np.pi * tv / 0.5)) * (1 - 0.3 * tv / 0.5)
        ph = 2 * np.pi * np.cumsum(f) / SR
        add(7.6, (np.sin(ph) + 0.3 * np.sin(2 * ph)) * np.sin(np.pi * tv / 0.5), 0.05)
        boom(8.6, 0.2)
        for k, tr in enumerate((10.0, 11.2)):
            pop(tr, 74 + 3 * k)
        ding(12.4)
        tv = np.arange(int(0.4 * SR)) / SR                     # boing for the basketball
        f = 180 * (1 + 0.5 * np.exp(-tv / 0.1) * np.sin(2 * np.pi * 9 * tv))
        add(13.6, np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tv / 0.2), 0.12)
        ding(15.4)
    elif EP == 8:
        def horn(t0):
            for m, d, dt0 in ((64, 0.22, 0.0), (60, 0.40, 0.28)):
                tv = np.arange(int(d * SR)) / SR
                ph = 2 * np.pi * hz(m) * tv
                add(t0 + dt0, (np.sign(np.sin(ph)) * 0.4 + np.sin(ph)) * np.clip((d - tv) / 0.05, 0, 1), 0.04)

        horn(0.3)
        for nn in range(11):                                    # one rising pop per counted stair
            pop(STAIR_T[nn], 64 + 2 * nn)
        ding(STAIR_T[10] + 0.6)
        tv = np.arange(int(1.6 * SR)) / SR                     # the bus drives off (engine glide)
        f = 70 + 60 * tv / 1.6
        add(13.0, np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * tv / 1.6) * (1 + 0.3 * np.sin(2 * np.pi * 18 * tv)),
            0.10)
        boom(14.4, 0.12)
        add(15.8, np.sin(2 * np.pi * np.cumsum(f[::-1]) / SR) * np.sin(np.pi * tv / 1.6), 0.08)
        horn(16.3)
    elif EP == 9:
        for k in range(1, 9):                                   # a rising pop per Zeno step
            pop(4.3 + 3.2 * (1 - 0.5 ** k), 70 + 2 * k)
        ding(7.5)
        tv = np.arange(int(0.4 * SR)) / SR                     # boing: the turtle hops on / off
        f = 220 * (1 + 0.5 * np.exp(-tv / 0.1) * np.sin(2 * np.pi * 9 * tv))
        for t0 in (11.6, 13.7):
            add(t0, np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tv / 0.2), 0.10)
    elif EP == 10:
        for k in range(5):                                      # counting ticks
            pop(1.8 + 0.3 * k, 76)
        tt = 5.0                                                # the clock races during the time-lapse
        while tt < 12.4:
            tv = np.arange(int(0.03 * SR)) / SR
            add(tt, np.sin(2 * np.pi * 2400 * tv) * np.exp(-tv / 0.006), 0.05)
            tt += max(0.035, 0.25 * (1 - (tt - 5.0) / 7.4))
        ding(12.6)
        boom(12.6, 0.15)
        tv = np.arange(int(1.0 * SR)) / SR                     # rewind: a falling sweep
        f = 1600 * (1 - 0.8 * tv)
        add(15.9, np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * tv) * 0.6, 0.06)
    elif EP == 11:
        for k in range(3):
            pop(4.8 + 0.12 * k, 72 + 4 * k)
        for k, m in enumerate((67, 64, 60, 55)):                # "wait…" slide down
            add(8.8 + 0.16 * k, tone(hz(m), 0.5, 0.18), 0.05)
        ding(10.3)
        ding(12.0)
    elif EP == 12:
        for k, tk in LILY_DAYS.items():                         # a pop per day, a little higher each time
            if k > 1:
                pop(tk, 62 + 2 * k)
        boom(11.9, 0.2)
        ding(11.95)
    elif EP == 13:
        tv = np.arange(int(0.6 * SR)) / SR                      # the lid swings open / shut
        add(8.1, np.diff(np.concatenate([[0], rng.standard_normal(len(tv))])) * np.sin(np.pi * tv / 0.6) ** 2, 0.04)
        add(10.8, np.diff(np.concatenate([[0], rng.standard_normal(len(tv))])) * np.sin(np.pi * tv / 0.6) ** 2, 0.04)
        for k in range(12):                                     # the ant's tiny steps
            pop(12.0 + 0.2 * k, 84)
        ding(14.4)
    elif EP == 14:
        tt = 0.25                                               # counting ticks, faster and faster through history
        while tt < 16.4:
            tv = np.arange(int(0.03 * SR)) / SR
            add(tt, np.sin(2 * np.pi * 2200 * tv) * np.exp(-tv / 0.006), 0.04)
            tt += max(0.06, 0.3 * (1 - tt / 16.4) ** 1.5)
        for th in (3.0, 5.0, 7.0, 8.8, 10.6, 12.4, 15.0):       # each handoff: a whoosh + a rising pop
            tv = np.arange(int(0.5 * SR)) / SR
            add(th - 0.6, np.diff(np.concatenate([[0], rng.standard_normal(len(tv))])) * np.sin(np.pi * tv / 0.5) ** 2, 0.05)
            pop(th, 64 + int(th * 1.5))
        ding(15.05)
        boom(15.05, 0.2)
        for k in range(5):                                      # fireworks
            pop(15.0 + 0.25 * k, 80 + 3 * k)
        tv = np.arange(int(1.6 * SR)) / SR                     # rewind: a falling sweep
        f = 1600 * (1 - 0.8 * tv / 1.6)
        add(16.6, np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * tv / 1.6) * 0.6, 0.06)
    elif EP == 15:
        x_ = np.arange(int(2.0 * SR)) / SR                     # the Big Bang: a deep swelling boom
        add(0.0, np.sin(2 * np.pi * np.cumsum(30 + 80 * np.exp(-x_ / 0.3)) / SR) * np.exp(-x_ / 0.8), 0.35)
        tt = 0.4                                                # counting ticks, faster and faster
        while tt < 17.6:
            tv = np.arange(int(0.03 * SR)) / SR
            add(tt, np.sin(2 * np.pi * 2200 * tv) * np.exp(-tv / 0.006), 0.035)
            tt += max(0.06, 0.28 * (1 - tt / 17.6) ** 1.4)
        for th in (2.0, 3.6, 5.2, 7.0, 8.6, 10.6, 12.0, 13.4, 14.8, 16.2):
            tv = np.arange(int(0.45 * SR)) / SR
            add(th - 0.55, np.diff(np.concatenate([[0], rng.standard_normal(len(tv))])) * np.sin(np.pi * tv / 0.45) ** 2, 0.05)
            pop(th, 62 + int(th * 1.4))
        tv = np.arange(int(0.5 * SR)) / SR                     # the T. rex roar (soft, tonal)
        f = 140 * (1 + 0.3 * np.sin(2 * np.pi * 7 * tv))
        add(7.4, np.tanh(2 * np.sin(2 * np.pi * np.cumsum(f) / SR)) * np.sin(np.pi * tv / 0.5), 0.10)
        ding(8.65)
        ding(16.25)
        boom(16.25, 0.2)
        for k in range(5):
            pop(16.25 + 0.25 * k, 80 + 3 * k)
        tv = np.arange(int(1.5 * SR)) / SR
        f = 1600 * (1 - 0.8 * tv / 1.5)
        add(17.8, np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * tv / 1.5) * 0.6, 0.06)
    elif EP == 16:
        for k in range(5):                                      # counting pops
            pop(1.9 + 0.33 * k, 76)
        tt = 4.8                                                # the clock races
        while tt < 12.4:
            tv = np.arange(int(0.03 * SR)) / SR
            add(tt, np.sin(2 * np.pi * 2400 * tv) * np.exp(-tv / 0.006), 0.05)
            tt += max(0.035, 0.25 * (1 - (tt - 4.8) / 7.6))
        for d_ in range(1, 12):                                 # a soft pop for every new day
            pop(4.8 + 7.6 * (d_ / (1e6 / 86400)) ** (1 / 1.6), 60 + d_)
        ding(12.6)
        boom(12.6, 0.15)
        for k in range(5):
            pop(12.7 + 0.2 * k, 80 + 3 * k)
        tv = np.arange(int(0.85 * SR)) / SR                    # rewind: a falling sweep
        f = 1600 * (1 - 0.8 * tv / 0.85)
        add(15.9, np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * tv / 0.85) * 0.6, 0.06)
    elif EP == 17:
        for k in range(5):
            pop(1.95 + 0.33 * k, 76)
        tt = 4.4
        while tt < 13.4:                                        # ticks: fast, then faster, a gap while the Sun dies
            tv = np.arange(int(0.03 * SR)) / SR
            if not (6.3 <= tt < 8.0 or 10.0 <= tt < 11.7):
                add(tt, np.sin(2 * np.pi * 2200 * tv) * np.exp(-tv / 0.006), 0.045)
            tt += 0.05 if (tt < 6.3 or 8.0 <= tt < 10.0) else (0.04 if tt >= 11.7 else 0.05)
        boom(6.35, 0.45)                                        # the Sun dies: a deep boom + a falling sweep
        tv = np.arange(int(1.2 * SR)) / SR
        add(6.4, np.sin(2 * np.pi * np.cumsum(900 * np.exp(-tv / 0.5) + 60) / SR) * np.sin(np.pi * tv / 1.2) * 0.5, 0.07)
        tv = np.arange(int(1.4 * SR)) / SR                     # lights out: a long falling tone
        add(10.0, np.sin(2 * np.pi * np.cumsum(500 * np.exp(-tv / 0.7) + 80) / SR) * np.sin(np.pi * tv / 1.4) * 0.5, 0.06)
        ding(13.45)
        boom(13.45, 0.3)
        for k in range(5):
            pop(13.5 + 0.25 * k, 80 + 3 * k)
        tv = np.arange(int(1.6 * SR)) / SR                     # rewind: a falling sweep
        f = 1600 * (1 - 0.8 * tv / 1.6)
        add(17.2, np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * tv / 1.6) * 0.6, 0.06)
    elif EP == 18:
        for k in range(8):                                      # real-time counting
            pop(1.95 + 0.33 * k, 76)
        tt = 4.4
        holds = ((6.0, 7.2), (8.2, 9.2), (10.3, 12.9), (13.9, 14.6))
        while tt < 15.0:                                        # ticks while racing, quiet at every stop
            if not any(a <= tt < b for a, b in holds):
                tv = np.arange(int(0.03 * SR)) / SR
                add(tt, np.sin(2 * np.pi * (1800 + 40 * (tt - 4.4)) * tv) * np.exp(-tv / 0.006), 0.045)
            tt += 0.05
        boom(6.05, 0.4)                                         # the Sun
        tv = np.arange(int(1.1 * SR)) / SR
        add(6.1, np.sin(2 * np.pi * np.cumsum(900 * np.exp(-tv / 0.5) + 60) / SR) * np.sin(np.pi * tv / 1.1), 0.06)
        tv = np.arange(int(1.0 * SR)) / SR                     # the last star
        add(8.2, np.sin(2 * np.pi * np.cumsum(500 * np.exp(-tv / 0.6) + 80) / SR) * np.sin(np.pi * tv / 1.0), 0.06)
        tv = np.arange(int(1.2 * SR)) / SR                     # the black hole: a low hum dying out
        add(10.3, np.sin(2 * np.pi * np.cumsum(70 + 30 * np.exp(-tv / 0.4)) / SR) * np.exp(-tv / 0.5), 0.25)
        ding(13.9)                                              # CENTILLION
        for k in range(4):
            pop(13.95 + 0.12 * k, 84 + 3 * k)
        for k in range(12):                                     # the glitch: short data chirps
            tv = np.arange(int(0.03 * SR)) / SR
            add(14.95 + 0.033 * k, np.sign(np.sin(2 * np.pi * (600 + 300 * (k % 4)) * tv)) * np.exp(-tv / 0.02), 0.03)
        for k, m in enumerate((72, 67, 64, 60)):                # "Infinity": a falling arpeggio
            pop(15.35 + 0.1 * k, m)
        boom(15.35, 0.2)
        tv = np.arange(int(1.4 * SR)) / SR                     # rewind
        f_ = 1600 * (1 - 0.8 * tv / 1.4)
        add(EP18_RW0, np.sin(2 * np.pi * np.cumsum(f_) / SR) * np.sin(np.pi * tv / 1.4) * 0.6, 0.06)
    elif EP == 19:
        last = -1
        for f_ in range(int(POT_T0 * 100), int(POT_T1 * 100)):              # a soft bubble for every kilo that leaves
            tt = f_ / 100
            g_ = int(pot_gone_at(tt))
            if g_ > last and g_ > 0:
                pop(tt, 84 - g_ * 0.4)
                last = g_
        ding(POT_T1 + 0.05)
        boom(12.2, 0.2)
        for k, m in enumerate((72, 76, 79)):
            pop(13.8 + 0.25 * k, m)
        tv = np.arange(int(1.6 * SR)) / SR
        f_ = 300 + 1300 * tv / 1.6                                         # rewind: a rising sweep (water coming back)
        add(POT_RW0, np.sin(2 * np.pi * np.cumsum(f_) / SR) * np.sin(np.pi * tv / 1.6) * 0.6, 0.05)
    elif EP == 20:
        for k in range(ZEN_STEPS):                                         # each Zeno step: a note, all the same pitch
            pop(ZEN_P0 + k * (ZEN_P1 - ZEN_P0) / ZEN_STEPS, 79)
            tt = ZEN_P0 + k * (ZEN_P1 - ZEN_P0) / ZEN_STEPS
            for q in range(4):                                             # footsteps, the same tempo every step
                tv = np.arange(int(0.04 * SR)) / SR
                add(tt + 0.3 * q, rng.standard_normal(len(tv)) * np.exp(-tv / 0.01), 0.03)
        tv = np.arange(int(0.8 * SR)) / SR                                 # zoom out
        add(ZEN_P1, np.sin(2 * np.pi * np.cumsum(1400 * (1 - 0.8 * tv / 0.8)) / SR) * np.sin(np.pi * tv / 0.8), 0.05)
        tt = ZEN_R0
        while tt < ZEN_R1:                                                 # real time: fast footsteps
            tv = np.arange(int(0.04 * SR)) / SR
            add(tt, rng.standard_normal(len(tv)) * np.exp(-tv / 0.01), 0.035)
            tt += 0.16
        t_pass = ZEN_R0 + 20 / 30 * (ZEN_R1 - ZEN_R0)
        ding(t_pass)
        for k in range(5):
            pop(t_pass + 0.12 * k, 80 + 3 * k)
        tv = np.arange(int(1.6 * SR)) / SR
        f_ = 1600 * (1 - 0.8 * tv / 1.6)
        add(ZEN_RW0, np.sin(2 * np.pi * np.cumsum(f_) / SR) * np.sin(np.pi * tv / 1.6) * 0.6, 0.06)
    else:
        def shuffle(t0, dur):
            tv = np.arange(int(dur * SR)) / SR
            nz = np.diff(np.concatenate([[0], rng.standard_normal(len(tv))]))
            add(t0, nz * np.sin(np.pi * tv / dur) * (0.6 + 0.4 * np.sin(2 * np.pi * 11 * tv)), 0.05)

        shuffle(5.0, 1.0)
        for k in range(9):
            pop(5.05 + 0.1 * k, 72 + k)
        pop(6.0, 84)
        for m, d in ((64, 0.25), (60, 0.45)):                  # bus horn (two-tone)
            tv = np.arange(int(d * SR)) / SR
            ph = 2 * np.pi * hz(m) * tv
            add(8.4 if m == 64 else 8.7, (np.sign(np.sin(ph)) * 0.4 + np.sin(ph)) * np.clip((d - tv) / 0.05, 0, 1), 0.05)
        shuffle(11.4, 1.2)
        for k in range(12):
            pop(12.8 + 0.06 * k, 70 + 2 * (k % 6))
        ding(14.0)
        ding(17.0)
    tail = out[n:]
    out = out[:n]
    out[: len(tail)] += tail
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
        f = int(arg("--frame", "0"))
        png = studio.OUT_DIR / f"{SCENE}_{label}_f{f}_{layout.tag}.png"
        render(layout, sim, png, rule, still_frame=f)
        print(f"[{SCENE}] -> {png}")
        return
    print(f"[{SCENE}] ep {EP}, {T_LOOP:.1f}s")
    kit.fan_out(_worker, (sim, label, rule), SCENE)


if __name__ == "__main__":
    main()
