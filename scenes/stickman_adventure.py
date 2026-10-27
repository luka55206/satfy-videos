"""STICKMAN ADVENTURE — the native 16:9 parts of the long-form "The Funny Math Adventures of Dot & Prof".

The 7 chapters themselves are the stick-figure episodes (scenes/stickman.py --ep 1..7, caption-less renders),
conformed into 16:9 storybook panels by tools/comp_916.py. This scene renders everything in between:
  --part intro        12 s   title, Dot walks in, Prof promises 7 impossible problems
  --part tr1 … tr7    11 s   walking to the next chapter (parallax landscape + banter + a signpost with the title)
  --part quiz         51.5 s the final boss: 7 questions, 3-2-1 countdown, answer, Dot's reaction
  --part outro        14 s   "which one was the craziest?" + a calm end-screen tail
Audio (original): plucked C–G–Am–F loop, blip voices, footsteps, ticks, dings.
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
import stickman as SM  # noqa: E402  (figure / bubble / props are shared)

SCENE = "stickman_adventure"
PART = arg("--part", "intro")
SR = audio.SR
GOLD, BLUE, ORANGE = SM.GOLD, SM.BLUE, SM.ORANGE

CHAPTERS = ["The Cookie Problem", "The Missing Number", "Three Doors, Two Goats", "The Birthday Party",
            "Paper to the Moon", "The Rope Around the Earth", "Hotel Infinity"]
BANTER = [
    [("B", "First stop: the cookie shop."), ("A", "I'll share them. How hard can it be?")],
    [("A", "That was rude. I DO have friends."), ("B", "Next: is 0.999… smaller than 1?"), ("A", "Obviously. Easy point.")],
    [("B", "Next: three doors and two goats."), ("A", "Goats? Is this still math?")],
    [("A", "Cake! I knew switching was right."), ("B", "Next: a birthday party."), ("A", "Is the cake for me?")],
    [("B", "Next: a piece of paper."), ("A", "Finally. Something safe and boring.")],
    [("A", "I went to the Moon and back. Literally."), ("B", "Next: a rope around the Earth."),
     ("A", "Let me guess. It's not 1 millimeter.")],
    [("B", "Last stop: a hotel."), ("A", "Good. I need to sleep after all this.")],
]
QUIZ = [("6 ÷ 0 = ?", "undefined: no answer"), ("Is 0.999… equal to 1?", "yes, exactly 1"),
        ("3 doors: switch or stay?", "switch (2 out of 3)"), ("People for a 50 % shared birthday?", "only 23"),
        ("Folds to reach the Moon?", "42 folds"), ("Rope + 1 m around the Earth: the gap?", "16 cm"),
        ("A full infinite hotel + 1 guest?", "it fits: room n → n + 1")]
REACT = ["Got it!", "…yes!", "Switch!", "23!", "42!", "16 cm!", "Infinity!"]

if PART == "intro":
    T = 12.0
    LINES = [(2.2, 4.6, "B", "Dot! Ready for 7 impossible math problems?"), (4.8, 6.4, "A", "Impossible? Pfff. Easy."),
             (6.6, 8.4, "B", "We'll see. Chapter 1: cookies."), (8.6, 10.0, "A", "Cookies?! I'm in!")]
elif PART.startswith("tr"):
    K = int(PART[2:]) - 1
    T = 11.0
    LINES, t0 = [], 0.5
    for who, txt in BANTER[K]:
        dur = max(1.6, len(txt) / SM.CPS + 0.8)
        LINES.append((t0, t0 + dur, who, txt))
        t0 += dur + 0.2
elif PART == "quiz":
    QT = 6.5
    T = 3.0 + len(QUIZ) * QT + 3.0
    LINES = [(3.0 + i * QT + 4.6, 3.0 + i * QT + 6.2, "A", REACT[i]) for i in range(len(QUIZ))]
else:
    T = 14.0
    LINES = [(0.3, 2.0, "A", "My brain is officially broken."), (2.2, 3.6, "B", "Then it's working."),
             (3.8, 5.8, "A", "Which one was the craziest?"), (6.0, 7.6, "B", "Tell us in the comments!")]


def simulate():
    return {"nf": int(round(T * FPS))}


class Scene:
    def __init__(self, layout, sim):
        self.L, self.sim = layout, sim
        self.canvas = Canvas(layout.w, layout.h, studio.render_scale())

    def landscape(self, t, scroll):
        c, w, h = self.canvas, self.L.w, self.L.h
        ctx = c.ctx
        g = cairo.LinearGradient(0, 0, 0, h)
        g.add_color_stop_rgb(0, 0.07, 0.07, 0.15)
        g.add_color_stop_rgb(1, 0.02, 0.02, 0.05)
        ctx.set_source(g)
        ctx.paint()
        for k in range(30):                                    # stars
            x = (k * 397.0 - scroll * 0.05) % w
            c.circle(x, h * (0.05 + 0.35 * ((k * 0.37) % 1)), 2, (0.9, 0.9, 1.0), alpha=0.5)
        for layer, (yb, amp, col, sp) in enumerate(((0.62, 0.08, (0.12, 0.12, 0.24), 0.2),
                                                    (0.70, 0.06, (0.16, 0.15, 0.30), 0.45))):
            ctx.move_to(0, h)
            for i in range(0, 61):
                x = w * i / 60
                y = h * (yb - amp * (0.5 + 0.5 * math.sin((x + scroll * sp) / (w * 0.13) + layer)))
                ctx.line_to(x, y)
            ctx.line_to(w, h)
            ctx.close_path()
            ctx.set_source_rgb(*col)
            ctx.fill()
        gy = self.gy
        ctx.rectangle(0, gy, w, h - gy)
        ctx.set_source_rgb(0.05, 0.05, 0.09)
        ctx.fill()
        c.lines([(0, gy, w, gy)], (0.75, 0.78, 0.9), width=4, alpha=0.6)
        for i in range(12):                                    # ground dashes (they move with the walk)
            x = (i * w / 12 - scroll) % w
            c.lines([(x, gy + h * 0.04, x + w * 0.03, gy + h * 0.04)], (0.6, 0.62, 0.75), width=3, alpha=0.4)

    def say(self, t, pos):
        c, w, h = self.canvas, self.L.w, self.L.h
        for t0, t1, who, text in LINES:
            if t0 <= t < t1:
                hx, hy = pos[who]
                SM.bubble(c, hx, hy, text, int((t - t0) * SM.CPS), BLUE if who == "A" else ORANGE, w * 0.62, h * 0.05)

    def talking(self, t, who):
        return any(t0 <= t < t1 and wh == who for t0, t1, wh, _ in LINES) and int(t * 8) % 2

    def draw(self, f, rule):
        L, c = self.L, self.canvas
        w, h = L.w, L.h
        t = f * DT
        self.gy, H = h * 0.80, h * 0.30
        ctx = c.ctx
        if PART == "intro":
            self.landscape(t, 0.0)
            ax = w * 0.32 * smooth(t / 2.0) if t < 10.2 else w * 0.32 + (t - 10.2) * w * 0.45
            bx = w * 0.68 + (max(0.0, t - 10.4) * w * 0.45)
            walkA = t < 2.0 or t >= 10.2
            SM.figure(c, ax, self.gy, H, BLUE, (0.3, 0.2), (0.3, 0.2), walk=(t * 2 if walkA else 0),
                      mouth="open" if self.talking(t, "A") else "smile")
            SM.figure(c, bx, self.gy, H, ORANGE, (0.3, 0.2), (0.3, 0.2), walk=(t * 2 if t >= 10.4 else 0),
                      mouth="open" if self.talking(t, "B") else "smile")
            a = min(1.0, t / 0.4)
            c.text_centered("THE FUNNY MATH ADVENTURES", h * 0.14, size=h * 0.085, color=GOLD, alpha=a)
            c.text_centered("of Dot & Prof", h * 0.215, size=h * 0.05, color=(0.95, 0.95, 1.0), alpha=a, bold=False)
            pos = {"A": (ax, self.gy - H * 1.05), "B": (bx, self.gy - H * 1.05)}
        elif PART.startswith("tr"):
            scroll = t * w * 0.25
            self.landscape(t, scroll)
            ax, bx = w * 0.36, w * 0.58
            SM.figure(c, ax, self.gy, H, BLUE, (0.3, 0.2), (0.3, 0.2), walk=t * 2.2,
                      mouth="open" if self.talking(t, "A") else "smile")
            SM.figure(c, bx, self.gy, H, ORANGE, (0.3, 0.2), (0.3, 0.2), walk=t * 2.2 + 0.25,
                      mouth="open" if self.talking(t, "B") else "smile")
            sp = w * 1.15 - smooth((t - 6.5) / 2.0) * w * 0.33 if t >= 6.5 else w * 1.3   # the signpost arrives
            ctx.rectangle(sp - 8, self.gy - H * 1.15, 16, H * 1.15)
            ctx.set_source_rgb(0.45, 0.30, 0.18)
            ctx.fill()
            ctx.rectangle(sp - w * 0.13, self.gy - H * 1.25, w * 0.26, H * 0.38)
            ctx.set_source_rgb(0.60, 0.42, 0.25)
            ctx.fill()
            c.text_centered(f"CHAPTER {K + 1}", self.gy - H * 1.08, size=h * 0.045, color=(1.0, 0.93, 0.75), cx=sp)
            c.text_centered(CHAPTERS[K], self.gy - H * 0.97, size=h * 0.03, color=(1.0, 0.93, 0.75), cx=sp,
                            bold=False)
            if t >= 8.6:                                       # big in-motion title (no black card)
                u = smooth((t - 8.6) / 0.4)
                c.text_centered(f"CHAPTER {K + 1}", h * 0.13, size=h * 0.06 * (0.8 + 0.2 * u), color=GOLD, alpha=u)
                c.text_centered(CHAPTERS[K], h * 0.22, size=h * 0.08 * (0.8 + 0.2 * u), color=(1, 1, 1), alpha=u)
            pos = {"A": (ax, self.gy - H * 1.05), "B": (bx, self.gy - H * 1.05)}
        elif PART == "quiz":
            self.landscape(t, 0.0)
            ax, bx = w * 0.14, w * 0.86
            q = int((t - 3.0) // QT) if t >= 3.0 else -1
            tq = (t - 3.0) - q * QT if q >= 0 else 0.0
            shock = 0 <= q < len(QUIZ) and tq < 3.6
            SM.figure(c, ax, self.gy, H, BLUE, *(((2.6, 0.4), (2.6, 0.4)) if shock else ((0.3, 0.2), (2.4, 0.3))),
                      mouth="open" if (self.talking(t, "A") or shock) else "smile")
            SM.figure(c, bx, self.gy, H, ORANGE, (0.3, 0.2), (2.3, 0.3), mouth="smile")
            if t < 3.0:
                u = smooth(t / 0.4)
                c.text_centered("FINAL BOSS", h * 0.30, size=h * 0.12 * (0.8 + 0.2 * u), color=GOLD, alpha=u)
                c.text_centered("THE QUIZ: 7 questions, 3 seconds each", h * 0.42, size=h * 0.05, color=(1, 1, 1),
                                alpha=u, bold=False)
            elif q < len(QUIZ):
                qq, ans = QUIZ[q]
                c.text_centered(f"QUESTION {q + 1} / {len(QUIZ)}", h * 0.12, size=h * 0.04, color=GOLD)
                c.text_centered(qq, h * 0.24, size=h * 0.07, color=(1, 1, 1))
                if tq < 3.6:                                   # countdown ring
                    rem = 3.6 - tq
                    cx, cy, R = w / 2, h * 0.45, h * 0.09
                    ctx.new_path()
                    ctx.arc(cx, cy, R, -math.pi / 2, -math.pi / 2 + 2 * math.pi * min(1.0, rem / 3.6))
                    ctx.set_source_rgb(*GOLD)
                    ctx.set_line_width(12)
                    ctx.stroke()
                    c.text_centered(str(max(1, math.ceil(rem * 3 / 3.6))), cy + R * 0.35, size=R, color=(1, 1, 1),
                                    cx=cx)
                else:
                    pop = math.exp(-(tq - 3.6) / 0.15)
                    c.text_centered(ans, h * 0.45, size=h * 0.08 * (1 + 0.15 * pop), color=GOLD)
            else:
                u = smooth((t - (T - 3.0)) / 0.4)
                c.text_centered("How many did YOU get?", h * 0.30, size=h * 0.09, color=GOLD, alpha=u)
                c.text_centered("write your score in the comments", h * 0.42, size=h * 0.05, color=(1, 1, 1),
                                alpha=u, bold=False)
            pos = {"A": (ax, self.gy - H * 1.05), "B": (bx, self.gy - H * 1.05)}
        else:
            self.landscape(t, 0.0)
            ax, bx = w * 0.30, w * 0.70
            dizzy = 1.0 if t < 2.2 else 0.0
            SM.figure(c, ax, self.gy, H, BLUE, (0.3, 0.2), (0.3, 0.2), mouth="open" if self.talking(t, "A") else "smile",
                      dizzy=dizzy, t=t)
            SM.figure(c, bx, self.gy, H, ORANGE, (0.3, 0.2), (1.5 if 6.0 <= t < 7.6 else 0.3, 0.0 if 6.0 <= t < 7.6 else 0.2),
                      mouth="open" if self.talking(t, "B") else "smile")
            if t >= 8.0:
                u = smooth((t - 8.0) / 0.5)
                c.text_centered("THE END", h * 0.16, size=h * 0.09, color=GOLD, alpha=u)
                c.text_centered("more Dot & Prof adventures soon", h * 0.24, size=h * 0.045, color=(1, 1, 1), alpha=u,
                                bold=False)
            pos = {"A": (ax, self.gy - H * 1.05), "B": (bx, self.gy - H * 1.05)}
        self.say(t, pos)
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


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def bed():
    n = int(round(T * SR))
    out = np.zeros(n + 2 * SR)
    rng = np.random.default_rng(3)

    def add(t0, sig, g=1.0):
        i0 = int(t0 * SR)
        sig = sig[: max(0, len(out) - i0)]
        out[i0:i0 + len(sig)] += g * sig

    def tone(f, dur, decay, harm=((1, 1.0), (2, 0.3))):
        tv = np.arange(int(dur * SR)) / SR
        return sum(a * np.sin(2 * np.pi * f * k * tv) for k, a in harm) * np.exp(-tv / decay)

    beat = 0.6
    prog = [(48, (60, 64, 67)), (43, (59, 62, 67)), (45, (60, 64, 69)), (41, (60, 65, 69))]
    tb, b = 0.0, 0
    while tb < T:
        root, ch = prog[b % 4]
        add(tb, tone(hz(root), 1.2, 0.35), 0.10)
        for e in range(8):
            m = ch[(e * 2) % 3] + (12 if e % 4 == 3 else 0)
            add(tb + e * beat / 2, tone(hz(m), 0.3, 0.09, ((1, 1.0), (2, 0.5), (3, 0.2))), 0.035)
        tb += 4 * beat
        b += 1
    for t0, t1, who, text in LINES:                             # blip voices
        base = 700 if who == "A" else 420
        for i in range(0, len(text), 2):
            if text[i] in " .…,":
                continue
            tt = t0 + i / SM.CPS
            if tt >= t1:
                break
            f = base * (1 + 0.12 * rng.standard_normal())
            tv = np.arange(int(0.055 * SR)) / SR
            sig = np.sign(np.sin(2 * np.pi * f * tv)) * 0.4 + np.sin(2 * np.pi * f * tv)
            add(tt, sig * np.clip(tv / 0.004, 0, 1) * np.exp(-tv / 0.03), 0.05)

    def ding(t0):
        for m in (84, 88, 91):
            add(t0, tone(hz(m), 1.2, 0.4, ((1, 1.0), (2.76, 0.25))), 0.06)

    def step(t0):
        tv = np.arange(int(0.06 * SR)) / SR
        add(t0, np.sin(2 * np.pi * 90 * tv) * np.exp(-tv / 0.02), 0.08)

    if PART.startswith("tr"):
        k = 0.0
        while k < T:
            step(k)
            k += 0.45
        ding(8.6)
    elif PART == "intro":
        for k in range(5):
            step(k * 0.4)
        ding(0.05)
        for k in range(5):
            step(10.2 + k * 0.4)
    elif PART == "quiz":
        ding(0.05)
        for i in range(len(QUIZ)):
            t0 = 3.0 + i * QT
            for j in range(3):                                  # tick tick tick
                add(t0 + 1.2 * j, tone(hz(96), 0.05, 0.015), 0.08)
            ding(t0 + 3.6)
        ding(T - 3.0)
    else:
        ding(8.0)
    tail = out[n:]
    out = out[:n]
    out[: len(tail)] += tail
    return out.astype(np.float32)


def _worker(o, sim, label, rule):
    layout = get_layout("horizontal")
    name = f"{SCENE}_{PART}_{label}_{layout.tag}"
    video = studio.OUT_DIR / f"{name}_silent.mp4"
    d = render(layout, sim, video, rule)
    kit.deliver_loop(SCENE, name, layout, video, [], d, voice="piano", bed=bed(), peak_db=-6.0)


def main():
    label = arg("--label", "v1")
    studio.OUT_DIR.mkdir(exist_ok=True)
    sim = simulate()
    if kit.has("--still"):
        layout = get_layout("horizontal")
        f = int(arg("--frame", "0"))
        png = studio.OUT_DIR / f"{SCENE}_{PART}_{label}_f{f}.png"
        render(layout, sim, png, "", still_frame=f)
        print(png)
        return
    print(f"[{SCENE}] {PART} {T:.1f}s")
    _worker("horizontal", sim, label, "")


if __name__ == "__main__":
    main()
