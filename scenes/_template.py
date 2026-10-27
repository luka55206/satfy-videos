"""TEMPLATE scene — copy to scenes/<name>.py and replace the mechanic.

Shows the project's two-pass contract in the smallest possible form:

  1. simulate()     pure, seeded, fixed-dt generation -> per-frame timeline +
                    an EVENT list (the audio source of truth). Cheap: use it to
                    calibrate duration and search seeds before rendering.
  2. render()       draws the timeline through studio.Canvas, pipes to ffmpeg.
  3. build_events() event list -> soundtrack via kit.deliver() (regenerable
                    from the _events.json sidecar without re-rendering).

Placeholder mechanic: one dot bouncing inside a circle, a little faster after
every bounce (so the event rate ACCELERATES), then a dissolve back to the exact
frame-0 state so the clip loops.

    ./run.ps1 -Scene _template -Fast -Still -Frame 300
    ./run.ps1 -Scene _template -Fast
    ./run.ps1 -Scene _template -Orient both -SceneArgs @('--seed','3')
"""
import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib import kit, studio  # noqa: E402
from lib.kit import DT, FPS, arg, smooth  # noqa: E402
from lib.layouts import get_layout  # noqa: E402
from lib.studio import PALETTE, Canvas, VideoWriter  # noqa: E402

SCENE = "_template"
REBUILD_S = 1.5          # loop ending: dissolve back to frame 0


# --- pass 1: simulate ---------------------------------------------------------

def simulate(seed, dur, speed0, accel, r_frac=0.04):
    """World units: arena radius = 1.0. Returns (frames, events)."""
    rng = random.Random(seed)
    a = rng.uniform(0, 2 * math.pi)
    speed = speed0
    x, y = 0.0, 0.0
    vx, vy = speed * math.cos(a), speed * math.sin(a)
    lim = 1.0 - r_frac
    frames, events = [], []
    for f in range(int(round(dur * FPS))):
        t = f * DT
        x, y = x + vx * DT, y + vy * DT
        d = math.hypot(x, y)
        if d > lim:                                  # reflect off the wall
            nx, ny = x / d, y / d
            dot = vx * nx + vy * ny
            vx, vy = vx - 2 * dot * nx, vy - 2 * dot * ny
            x, y = nx * lim, ny * lim
            speed *= accel                           # the escalation rule
            s = speed / math.hypot(vx, vy)
            vx, vy = vx * s, vy * s
            events.append({"t": round(t, 5), "x_world": x, "n": len(events)})
        frames.append((x, y, len(events)))
    return frames, events


# --- pass 2: render -----------------------------------------------------------

def draw(canvas, layout, frames, f, e, rule, r_frac):
    cx, cy, R = layout.arena_cx, layout.arena_cy, layout.arena_R
    canvas.clear()
    x, y, n = frames[f]
    col = PALETTE[n % len(PALETTE)]
    canvas.ring(cx, cy, R, col, width=6.0)
    canvas.core(cx + x * R, cy + y * R, r_frac * R, col, alpha=1.0)
    cap_a = min(1.0, f * DT / 0.4) * (1.0 - e)       # 0 at frame 0 AND at the seam
    if rule:
        canvas.caption(rule, alpha=cap_a, layout=layout)
    canvas.counter(f"Bounces: {n:,}", layout=layout, size_f=0.032)
    canvas.watermark(layout)


def render(layout, frames, out_path, rule, r_frac, still_frame=None):
    canvas = Canvas(layout.w, layout.h, studio.render_scale())
    writer = None if still_frame is not None else VideoWriter(out_path, canvas, FPS)
    nf, rew = len(frames), int(REBUILD_S * FPS)
    for f in range(nf + rew):
        if still_frame is not None and f != still_frame:
            continue
        if f < nf:
            src, e = f, 0.0
        else:                                        # replay backwards to frame 0
            e = smooth((f - nf + 1) / rew)
            src = int(round((nf - 1) * (1.0 - e)))
        draw(canvas, layout, frames, src, e, rule, r_frac)
        if writer is None:
            studio.save_still(canvas, out_path)
            return f / FPS
        writer.write_frame()
    writer.close()
    return (nf + rew) / FPS


# --- pass 3: soundtrack -------------------------------------------------------

def build_events(events, layout, seed, dur):
    walker = kit.audio.ScaleWalker(root_midi=57, scale=kit.audio.PENTA_MAJOR)  # original scale, no tunes
    out = []
    for ev in events:
        gain = 0.45 + 0.35 * min(1.0, ev["t"] / max(dur, 1e-6))   # ramp UP to payoff
        out.append({"t": ev["t"], "note": walker.next(), "gain": round(gain, 3),
                    "x": round(layout.arena_cx + ev["x_world"] * layout.arena_R, 1)})
    return out


# --- orchestration ------------------------------------------------------------

def _worker(o, seed, dur, speed0, accel, label, rule, sound):
    layout = get_layout(o)
    frames, events = simulate(seed, dur, speed0, accel)
    name = f"{SCENE}_{label}_{layout.tag}"
    video = studio.OUT_DIR / f"{name}_silent.mp4"
    d = render(layout, frames, video, rule, 0.04)
    kit.deliver(SCENE, name, layout, video, build_events(events, layout, seed, dur),
                d, sound)


def main():
    seed = int(arg("--seed", 0))
    dur = float(arg("--dur", 30.0))
    speed0 = float(arg("--speed", 0.9))
    accel = float(arg("--accel", 1.03))
    label = arg("--label", f"s{seed}")
    rule = arg("--rule", "")                  # captions are a POST-RENDER pass
    sound = arg("--sound", "1") != "0"
    studio.OUT_DIR.mkdir(exist_ok=True)

    frames, events = simulate(seed, dur, speed0, accel)
    if kit.has("--still"):
        layout = get_layout(kit.orients()[0])
        f = int(arg("--frame", str(len(frames) // 2)))
        png = studio.OUT_DIR / f"{SCENE}_{label}_f{f}_{layout.tag}.png"
        render(layout, frames, png, rule, 0.04, still_frame=f)
        print(f"[{SCENE}] -> {png}")
        return
    ev5 = kit.density_report([{"t": e["t"]} for e in events], dur)
    print(f"[{SCENE}] seed={seed} events={len(events)} per5s={ev5}")
    kit.fan_out(_worker, (seed, dur, speed0, accel, label, rule, sound), SCENE)


if __name__ == "__main__":
    main()
