"""Tiny shared boilerplate for scenes (added 2026-07-27 with the 10 new-concept
test clips).

Every scene repeats the same six things: `_arg()` parsing, the spectral color
wheel, smoothstep, the NF_ORIENT fan-out, the melody flag dance, and the
events -> wav -> mux delivery. That is ~80 lines per scene of pure copy, and it
had already drifted (three spellings of the melody validation). This holds the
ONE copy; the look, physics and schedule still live in the scene file.

Nothing here draws or simulates — it is orchestration only, so a scene can
still ignore it entirely (all older scenes do).
"""
import math
import multiprocessing
import os
import sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib import audio, studio
from lib.studio import PALETTE

FPS = 60
DT = 1.0 / FPS

# PALETTE reindexed red->violet, the channel's continuous-sweep order
# (grow_triangle / shrink_box / mandala all use this exact list).
SPECTRUM = [7, 3, 5, 2, 8, 0, 6, 4, 9, 1]


def arg(flag, default=None):
    a = sys.argv
    return a[a.index(flag) + 1] if flag in a else default


def has(flag) -> bool:
    return flag in sys.argv


def wheel(u):
    """u -> smooth (r,g,b) around the spectral ring (cycles at 1.0)."""
    n = len(SPECTRUM)
    f = (u % 1.0) * n
    i = int(f) % n
    j = (i + 1) % n
    k = f - int(f)
    a, b = PALETTE[SPECTRUM[i]], PALETTE[SPECTRUM[j]]
    return (a[0] + (b[0] - a[0]) * k,
            a[1] + (b[1] - a[1]) * k,
            a[2] + (b[2] - a[2]) * k)


def smooth(p: float) -> float:
    p = 0.0 if p < 0.0 else (1.0 if p > 1.0 else p)
    return p * p * (3.0 - 2.0 * p)


def speed_text(px_per_s, unit=True):
    """The channel's SPEED readout: PIXELS PER SECOND, one place, every scene.

    px/s is the only true unit a 2D sim has — a pixel is a real length here and
    a second is a real duration, while km/h needed an invented `1 px = 2.5 cm`
    and mph/km-h would pick a side of a border for no gain. See CLAUDE.md.

    Quantised to 10 because the number is recomputed every frame: the ones digit
    strobes at 60 Hz and reads as noise, and nothing about a speedometer needs
    that last digit. Thousands separator so the 4-digit values a climax reaches
    stay readable at feed size.
    """
    v = int(round(px_per_s / 10.0)) * 10
    return f"{v:,} px/s" if unit else f"{v:,}"


def shape_tilt(sides):
    """Default rotation for a regular n-gon arena, radians, +y down.

    A SQUARE reads as a square only when its edges are horizontal and vertical,
    i.e. vertices on the diagonals; everything else reads as itself point-up.
    """
    return -math.pi / 4.0 if sides == 4 else -math.pi / 2.0


def poly_reach(theta, sides, tilt):
    """Distance from the centre to a regular n-gon's edge along `theta`, as a
    FRACTION of the circumradius (1.0 at a vertex, cos(pi/n) at an edge
    midpoint). `sides < 3` returns 1.0, i.e. a circle.

    This is the whole polygon-arena trick for the bar-ring scenes: multiply the
    circular scene's radii by `poly_reach(bar angle)` and the entire field —
    hub, bars, arena rim — warps onto the polygon at once, so a value still maps
    to "how far to the wall" and the sorted state still ends flush against it.
    """
    if sides < 3:
        return 1.0
    step = 2.0 * math.pi / sides
    a = (theta - tilt) % step
    return math.cos(math.pi / sides) / math.cos(a - step * 0.5)


def poly_fit(sides, tilt, w, h):
    """Circumradius of a regular n-gon that fits a w x h box exactly.

    Sized off the BOUNDING BOX, not the circumradius: the channel's 9:16 rule
    is about how much of the frame WIDTH the arena spans, and an inscribed
    polygon is much narrower than its circumcircle (a triangle's base is
    1.73 R against the circle's 2 R).
    """
    if sides < 3:
        return min(w, h) * 0.5
    step = 2.0 * math.pi / sides
    xs = [math.cos(tilt + k * step) for k in range(sides)]
    ys = [math.sin(tilt + k * step) for k in range(sides)]
    return min(w / (max(xs) - min(xs)), h / (max(ys) - min(ys)))


def poly_path(cx, cy, Rc, sides, tilt, a0, a1, samples=4):
    """Points along a regular n-gon's boundary from angle a0 to a1 (a1 >= a0).

    Every VERTEX angle inside the sweep is inserted exactly, so the corners are
    corners and not chords — which is the point of drawing a progress arc on a
    square at all.
    """
    step = 2.0 * math.pi / sides if sides >= 3 else 2.0 * math.pi
    angs = [a0 + (a1 - a0) * i / max(1, samples * max(sides, 3))
            for i in range(samples * max(sides, 3) + 1)]
    if sides >= 3:
        k0 = math.floor((a0 - tilt) / step)
        k = k0
        while tilt + k * step <= a1 + 1e-12:
            v = tilt + k * step
            if a0 < v < a1:
                angs.append(v)
            k += 1
        angs.sort()
    return [(cx + Rc * poly_reach(a, sides, tilt) * math.cos(a),
             cy + Rc * poly_reach(a, sides, tilt) * math.sin(a)) for a in angs]


def orients():
    o = os.environ.get("NF_ORIENT", "vertical")
    return ["vertical", "horizontal"] if o == "both" else [o]


def melody(seed, default="auto", scene="scene"):
    """Resolve --melody: 'auto' rotates the PD bank by seed, '' = pentatonic."""
    m = arg("--melody", default)
    if m == "auto":
        m = audio.pick_melody(seed)
    elif m in ("", "none", "0"):
        m = None
    if m and not audio.is_known_melody(m):
        sys.exit(f"[{scene}] unknown --melody {m!r}; choices: "
                 f"{', '.join(list(audio.MELODIES) + list(audio.MELODIES_CUSTOM))}")
    return m


def deliver(scene, name, layout, silent_video, events, dur, sound=True,
            voice="marimba", drone=None, foley_gain=0.0, foley_kind="thump",
            peak_db=None, bed=None, intro="auto"):
    """events -> sidecar json + mastered wav -> mux onto the silent render.

    drone: optional {t0, dur, midi, gain, fade_in, fade_out} sub-bass bed (see
    audio.synth_drone) — the channel's way of adding weight to a climax without
    firing more events, which would only trip the mixer's density ducking.
    foley_gain/foley_kind pass straight to mix_events (glassbreak scenes).
    peak_db: extra limiter for scenes whose events are IMPULSES (a pop/shatter
    per event) — AAC overshoots those by ~3 dB and clips. See audio.master().
    intro: SILENT-HEAD fill, ON BY DEFAULT for every new build (see
    audio.intro_layer — gate 0.40s, pickup note under 0.80s, riser over).
    "auto" = apply unless `bed` is already set (a bed already solves audibility
    at t=0, e.g. the Pac-Man ghost siren — stacking a second layer would clash).
    Pass an explicit dict to override the gate/riser/gain, or None/False to
    force it off for a scene with a deliberate silent open.
    """
    out_dir = studio.OUT_DIR
    audio.save_events(events, out_dir / f"{name}_events.json")
    final = out_dir / f"{name}.mp4"
    if sound and events:
        wav = out_dir / f"{name}_audio.wav"
        intro_kw = intro
        if intro_kw == "auto":
            intro_kw = None if bed is not None else {}
        audio.render_soundtrack(events, dur, wav, width_px=layout.w, voice=voice,
                                drone=drone, foley_gain=foley_gain,
                                foley_kind=foley_kind, peak_db=peak_db,
                                bed=bed, intro=intro_kw)
        studio.mux_audio(silent_video, wav, final)
        silent_video.unlink()
    else:
        silent_video.replace(final)
    print(f"[{scene}] wrote {final}  ({dur:.2f}s, {len(events)} events)")
    return final


def deliver_wrapped(scene, name, layout, silent_video, events, dur,
                    voice="marimba", peak_db=None, intro=None, **mix_kw):
    """deliver() for a WRAP-LOOP clip: the ring-out is FOLDED across the seam.

    mix_events renders +2s of tail past the clip end; adding that overhang onto
    the clip HEAD makes the seam acoustically an interior moment — the last
    note rings on underneath the first note of the next pass, which is what the
    ear expects from a loop and what stops the seam clicking. Folded BEFORE
    master(), so the loudness match sees the final signal.

    The tail is deliberately NOT silent here. Tail-silence gates and
    tools/regen_audio.py both assume an ending and do NOT apply to wrap clips
    (regen_audio does not know about the fold and would undo it).

    Second copy of chladni's deliver_wrapped, which predates this helper and
    keeps its own inline version so its shipped clips stay bit-reproducible.
    """
    import soundfile as sf
    out_dir = studio.OUT_DIR
    audio.save_events(events, out_dir / f"{name}_events.json")
    final = out_dir / f"{name}.mp4"
    wav = out_dir / f"{name}_audio.wav"
    buf = audio.mix_events(events, dur, width_px=layout.w, voice=voice,
                           **mix_kw)
    n_clip = int(round(dur * audio.SR))
    buf[: len(buf) - n_clip] += buf[n_clip:]
    if intro is not None:
        # A wrap fold is NOT by itself a silent-head fix: it only lends the head
        # whatever the ring-out still has, which is nothing once the last event
        # is a second old (gorge measured -94.7 dBFS across its second second).
        # Omitted => bit-identical to every clip shipped before this parameter.
        kw = {k: v for k, v in intro.items() if k != "enabled"}
        kw.setdefault("ring", mix_kw.get("ring", 1.0))
        lay = audio.intro_layer(events, voice=voice, **kw)
        if lay is not None:
            m = min(len(lay), n_clip)
            buf[:m, 0] += lay[:m]
            buf[:m, 1] += lay[:m]
    out = audio.master(buf[:n_clip], peak_db=peak_db)
    sf.write(str(wav), out, audio.SR, subtype="PCM_24")
    studio.mux_audio(silent_video, wav, final)
    silent_video.unlink()
    print(f"[{scene}] wrote {final}  ({dur:.2f}s, {len(events)} events, "
          f"wrap-loop audio)")
    return final


def loop_pad(dur, notes, gain=0.016, lfo_cycles=2, sr=None):
    """A sine pad that is EXACTLY periodic over `dur` (every partial and the LFO complete a
    whole number of cycles), so it joins itself at a nonstop loop seam with no fade.
    notes: [(midi, amp)]. Frequencies are nudged to k/dur Hz (< 0.03 Hz at dur >= 17 s)."""
    sr = sr or audio.SR
    n = int(round(dur * sr))
    t = np.arange(n) / sr
    sig = np.zeros(n)
    for m, amp in notes:
        for mult, a in ((1.0, 1.0), (1.003, 0.5)):
            f0 = round(audio.midi_to_hz(m) * mult * dur) / dur
            sig += amp * a * np.sin(2 * np.pi * f0 * t)
    lfo = 0.85 + 0.15 * np.sin(2 * np.pi * (lfo_cycles / dur) * t)
    return (gain * sig * lfo).astype(np.float32)


def deliver_loop(scene, name, layout, silent_video, events, dur, voice="glassharp",
                 bed=None, peak_db=None):
    """deliver() for a NONSTOP loop: no fade at the end. Note ring-outs past the end are
    folded onto the head (as deliver_wrapped), and `bed` (e.g. loop_pad) must be periodic
    over `dur`, so the seam is acoustically an interior moment."""
    import soundfile as sf
    out_dir = studio.OUT_DIR
    audio.save_events(events, out_dir / f"{name}_events.json")
    final = out_dir / f"{name}.mp4"
    wav = out_dir / f"{name}_audio.wav"
    buf = audio.mix_events(events, dur, width_px=layout.w, voice=voice)
    n_clip = int(round(dur * audio.SR))
    buf[: len(buf) - n_clip] += buf[n_clip:]
    buf = buf[:n_clip]
    if bed is not None:
        m = min(len(bed), n_clip)
        buf[:m, 0] += bed[:m]
        buf[:m, 1] += bed[:m]
    out = audio.master(buf, peak_db=peak_db)
    sf.write(str(wav), out, audio.SR, subtype="PCM_24")
    studio.mux_audio(silent_video, wav, final)
    silent_video.unlink()
    print(f"[{scene}] wrote {final}  ({dur:.2f}s, {len(events)} events, nonstop-loop audio)")
    return final


def fan_out(worker, args, scene="scene"):
    """Run `worker(orient, *args)` for each requested orientation."""
    os_ = orients()
    if len(os_) == 1:
        worker(os_[0], *args)
        return
    procs = [multiprocessing.Process(target=worker, args=(o,) + tuple(args))
             for o in os_]
    for p in procs:
        p.start()
    for p in procs:
        p.join()
    if any(p.exitcode != 0 for p in procs):
        sys.exit(f"[{scene}] a render worker failed")


# --- the climax-dwell soundtrack (CLAUDE.md "longer, chaotic, creepy endings") -
#
# Every scene that ends with an overtime JAM needs the same three things, and
# they were written out inline five times before this existed (grow_triangle,
# grow_ball, fill_circle, spin_crush, spawn_crash — those five keep their copies
# so their shipped clips stay bit-reproducible; new scenes call this instead).
#
# The rules being encoded, all of them measured rather than assumed:
#   * MORE EVENTS CAN NEVER BE LOUDER. mix_events drops onsets within 10ms and
#     ducks by 1/sqrt(density), so an un-thinned jam lands BELOW the body — the
#     visual payoff arriving as the quietest moment. Hence a sounded-rate
#     ceiling, in the SCENE, not in the shared mixer.
#   * The ceiling is needed in the BUILD too whenever the build itself gets
#     dense. spawn_crash measured a −23 dBFS hole in the seconds BEFORE its
#     crash, where thinning-after-the-jam does nothing.
#   * Creepy comes from TIMBRE/HARMONY: notes drift down over the jam (a dying
#     music box), and the weight comes from a sub-bass DRONE, which is not an
#     event and so bypasses the density duck entirely.
BUILD_GAP_S = 0.012    # ~83/s ceiling on sounded notes during the build
RATTLE_GAP_S = 0.04    # ~25/s ceiling during the jam
DRIFT_SEMI = 0.0       # jam pitch drift; 0 = off (the downward "creepy" drift is retired)


def jam_events(items, walker, jam_t=None, overtime_s=1.0, build_gap=BUILD_GAP_S,
               rattle_gap=RATTLE_GAP_S, drift_semi=DRIFT_SEMI):
    """[(t, gain, x)] -> soundtrack events, rate-capped and pitch-drifted.

    ``items`` is an iterable of (t, gain, x) in any order; ``walker`` is a
    ScaleWalker/MelodyWalker. Events at or after ``jam_t`` are the jam: thinned
    harder and pitched progressively down. Pass jam_t=None for a scene with no
    jam (the build ceiling still applies).
    """
    out = []
    last = -1e9
    for t, gain, x in sorted(items, key=lambda e: e[0]):
        in_jam = jam_t is not None and t >= jam_t
        if t - last < (rattle_gap if in_jam else build_gap):
            continue
        last = t
        note = walker.next()
        if in_jam:
            note += int(round(-drift_semi *
                              min(1.0, (t - jam_t) / max(overtime_s, 1e-6))))
            gain = 0.5
        out.append({"t": round(t, 5), "note": note,
                    "gain": round(gain, 3), "x": round(x, 1)})
    return out


TAIL_SILENCE_S = 1.30   # the drone must be fully decayed this long before the end.
                        # 1.3s, not "a bit": master() runs a Reverb (wet 0.14)
                        # whose tail outlives the drone's own fade_out, so a
                        # 0.3s margin still measured -46 dBFS at the seam where
                        # every hand-tuned clip measures -180. The jam scenes
                        # that predate this helper all happen to leave ~1.3s,
                        # which is where the number comes from.


def jam_drone(jam_t, dur_s, midi=29, gain=0.06, fade_in=1.5, fade_out=2.0,
              clip_dur=None):
    """The sub-bass bed under a jam, as render_soundtrack(drone=...) wants it.

    Pass ``clip_dur`` and the drone is CLAMPED to finish TAIL_SILENCE_S before
    the last sample. That clamp is not defensive tidiness — the tail has to
    decay to silence by the loop seam or the seam clicks, and a drone sized
    from the jam length alone silently overruns: three clips shipped at
    -19.8 dBFS in their final half-second against -180 for every hand-checked
    clip before them, because the drone was started at (dur - creepy) and given
    (creepy + 0.9) seconds to run.
    """
    if clip_dur is not None:
        dur_s = min(dur_s, max(0.5, clip_dur - TAIL_SILENCE_S - jam_t))
    return {"t0": jam_t, "dur": dur_s, "midi": midi, "gain": gain,
            "fade_in": fade_in, "fade_out": fade_out}


def density_report(events, dur, bins=None):
    """events/5s over the clip — the channel's escalation check."""
    if not events:
        return []
    n = bins or max(1, int(dur // 5))
    out = [0] * n
    for e in events:
        i = min(int(e["t"] / dur * n), n - 1)
        out[i] += 1
    return out


def penta_note(u, root=60, scale=None, span=12):
    """u in [0,1] -> a pentatonic midi note `span` degrees above `root`.

    Used by the scenes that map a physical quantity (size, column, height)
    to pitch instead of walking a melody — plinko's "gravity harp" idea.
    """
    scale = scale or audio.PENTA_MINOR
    d = int(round(max(0.0, min(1.0, u)) * (span - 1)))
    return root + 12 * (d // len(scale)) + scale[d % len(scale)]


def ease_to_zero(t, t_end, reset_s):
    """Progress 0..1 through a reset window ending the clip."""
    return smooth((t - t_end) / max(reset_s, 1e-6))


__all__ = ["FPS", "DT", "SPECTRUM", "arg", "has", "wheel", "smooth", "orients",
           "shape_tilt", "poly_reach", "poly_fit", "poly_path",
           "jam_events", "jam_drone", "BUILD_GAP_S", "RATTLE_GAP_S",
           "DRIFT_SEMI",
           "melody", "deliver", "fan_out", "density_report", "penta_note",
           "ease_to_zero", "math"]
