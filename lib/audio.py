"""Collision events -> mastered musical soundtrack, fully offline.

Pipeline (see PLAN.md section 5):
  events [{t, gain, x, note?}] -> note assignment (ScaleWalker / MelodyAssigner)
  -> synth note bank (deterministic numpy marimba plinks, zero licensing risk)
  -> float32 stereo accumulation buffer (can't clip in float)
  -> pedalboard Reverb + Limiter -> pyloudnorm to -14 LUFS, peak <= -1 dBTP
  -> 48kHz 24-bit WAV.

Audio is re-generable from the events sidecar without re-rendering video.
"""
import json
import math
from pathlib import Path

import numpy as np
import soundfile as sf

SR = 48000

PENTA_MAJOR = [0, 2, 4, 7, 9]
PENTA_MINOR = [0, 3, 5, 7, 10]
MAJOR = [0, 2, 4, 5, 7, 9, 11]


def midi_to_hz(m: float) -> float:
    return 440.0 * 2.0 ** ((m - 69) / 12.0)


# --- synthesis ---------------------------------------------------------------

# Channel signature voice: glass harp via modal synthesis. Wine-glass modal
# ratios; velocity opens brightness (soft hit = pure ring, hard hit = sparkle).
# Detuned partner partials give the glassy shimmer (slow beating).
GLASS_PARTIALS = [  # (ratio, amplitude, decay rate 1/s)
    (1.00, 1.00, 1.6),
    (2.32, 0.30, 2.8),
    (4.25, 0.16, 4.5),
    (6.63, 0.07, 7.0),
    (9.38, 0.035, 10.0),
]


def synth_glassharp(midi_note: int, velocity: float = 0.8, sr: int = SR) -> np.ndarray:
    f0 = midi_to_hz(midi_note)
    dur = float(np.clip(2.3 - (midi_note - 48) * 0.018, 0.5, 2.1))
    n = int(dur * sr)
    t = np.arange(n, dtype=np.float32) / sr
    bright = 0.35 + 0.65 * float(np.clip(velocity, 0.0, 1.0))
    out = np.zeros(n, dtype=np.float32)
    for i, (ratio, amp, dec) in enumerate(GLASS_PARTIALS):
        f = f0 * ratio
        if f > sr * 0.45:
            break
        a = amp * bright ** i
        env = np.exp(-dec * t).astype(np.float32)
        out += a * np.sin(2 * np.pi * f * t).astype(np.float32) * env
        out += 0.55 * a * np.sin(2 * np.pi * f * 1.0016 * t).astype(np.float32) \
            * np.exp(-dec * 1.15 * t).astype(np.float32)
    # glass contact tick (deterministic noise)
    rng = np.random.default_rng(midi_note)
    tick_n = int(0.008 * sr)
    tick = rng.standard_normal(tick_n).astype(np.float32) \
        * np.exp(-np.arange(tick_n, dtype=np.float32) / (0.0015 * sr))
    out[:tick_n] += 0.10 * (0.5 + velocity) * tick
    a = min(int(0.003 * sr), n)
    out[:a] *= np.linspace(0.0, 1.0, a, dtype=np.float32)
    peak = float(np.max(np.abs(out))) or 1.0
    return out / peak


def synth_foley(impulse: float, sr: int = SR) -> np.ndarray:
    """Tactile impact under the note: soft body thump scaled by impulse.

    The ASMR layer competitors caption but never engineer — synthesized from
    the sim's real collision strength. Deterministic.
    """
    impulse = float(np.clip(impulse, 0.0, 1.0))
    dur = 0.10
    n = int(dur * sr)
    t = np.arange(n, dtype=np.float32) / sr
    rng = np.random.default_rng(1234)
    noise = rng.standard_normal(n).astype(np.float32)
    # crude one-pole lowpass; cutoff opens with impact strength
    alpha = float(np.clip(0.04 + 0.18 * impulse, 0.01, 0.5))
    lp = np.empty_like(noise)
    acc = 0.0
    for i in range(n):  # n is ~4800 — fine
        acc += alpha * (noise[i] - acc)
        lp[i] = acc
    body = lp * np.exp(-48.0 * t)
    knock = np.sin(2 * np.pi * (85.0 + 70.0 * impulse) * t) * np.exp(-38.0 * t)
    out = (0.6 * body + 0.9 * knock).astype(np.float32)
    peak = float(np.max(np.abs(out))) or 1.0
    return out / peak * (0.35 + 0.65 * impulse)


def synth_glassbreak(impulse: float, seed: int = 0, sr: int = SR) -> np.ndarray:
    """Glass-shatter transient to layer UNDER the note (this scene's signature,
    per the reference + Luka's ask). A sharp crack + a bright noise body + a few
    random high "shard tinkle" sines. Deterministic (seeded)."""
    impulse = float(np.clip(impulse, 0.0, 1.0))
    dur = 0.18
    n = int(dur * sr)
    t = np.arange(n, dtype=np.float32) / sr
    rng = np.random.default_rng(seed)
    noise = rng.standard_normal(n).astype(np.float32)
    hp = np.diff(noise, prepend=noise[:1])          # crude high-pass -> glassy
    body = hp * np.exp(-22.0 * t).astype(np.float32)         # shatter decay
    crack = noise * np.exp(-450.0 * t).astype(np.float32)    # ms-long initial snap
    tink = np.zeros(n, dtype=np.float32)                     # falling-shard sparkle
    for _ in range(5):
        f = float(rng.uniform(1800.0, 6500.0))
        ph = float(rng.uniform(0.0, 2 * math.pi))
        dec = float(rng.uniform(18.0, 40.0))
        amp = float(rng.uniform(0.15, 0.5))
        tink += amp * np.sin(2 * np.pi * f * t + ph).astype(np.float32) \
            * np.exp(-dec * t).astype(np.float32)
    out = (0.6 * body + 0.5 * crack + 0.5 * tink).astype(np.float32)
    a = min(int(0.001 * sr), n)
    out[:a] *= np.linspace(0.0, 1.0, a, dtype=np.float32)
    peak = float(np.max(np.abs(out))) or 1.0
    return out / peak * (0.4 + 0.6 * impulse)


def synth_concretebreak(size: float, seed: int = 0, sr: int = SR) -> np.ndarray:
    """CONCRETE break, to layer UNDER the note — the shatter scene's concrete
    material (Luka, 2026-08-05: "beton ball shatter", not glass).

    Glass and concrete differ in exactly the three things this synthesizes, and
    inverting each of `synth_glassbreak`'s is what makes the material read:

      * glass is a high-passed noise burst; concrete is a LOW-passed one, so
        the body is gritty rather than bright,
      * glass rings out in random high sine "tinkles"; concrete has no tuned
        partials at all — its tail is a CRUMBLE, a scatter of short filtered
        noise grains (chunks landing on chunks),
      * glass has a millisecond crack; concrete has a deep body THUD that
        sweeps down, which is where the weight comes from.

    ``size`` (0..1) = how big the ball was: a big one lands as a low BOOM with
    a long crumble, a small one as a dry tick. Deterministic (seeded).
    """
    size = float(np.clip(size, 0.0, 1.0))
    dur = 0.26 + 0.20 * size
    n = int(dur * sr)
    t = np.arange(n, dtype=np.float32) / sr
    rng = np.random.default_rng(seed)
    noise = rng.standard_normal(n).astype(np.float32)

    # gritty body: noise smoothed by a short kernel (vectorised one-pole stand-in
    # — a per-sample loop here runs per cache miss). Wider kernel = duller = more
    # rubble, less sand; the big bursts are the dullest.
    k = np.exp(-np.arange(64, dtype=np.float32) * (0.42 - 0.26 * size))
    k /= k.sum()
    grit = np.convolve(noise, k)[:n] * np.exp(-26.0 * t).astype(np.float32)
    # dry surface crack — short, but nothing like glass's sub-ms snap
    crack = noise * np.exp(-260.0 * t).astype(np.float32)
    # body thud: low, sweeping DOWN so it lands like mass hitting mass
    f0 = 140.0 - 78.0 * size
    ph = 2 * np.pi * (f0 * t - 0.30 * f0 * t * t)
    thud = np.sin(ph).astype(np.float32) * \
        np.exp(-(34.0 - 17.0 * size) * t).astype(np.float32)
    # crumble tail: grains of the same dull noise, scattered after the impact.
    # This is the part the ear labels "concrete" — chunks still falling.
    crumble = np.zeros(n, dtype=np.float32)
    for _ in range(int(5 + 7 * size)):
        t0 = float(rng.uniform(0.03, dur * 0.85))
        i0 = int(t0 * sr)
        gn = int(sr * rng.uniform(0.012, 0.045))
        if i0 + gn > n:
            gn = n - i0
        if gn <= 4:
            continue
        tg = np.arange(gn, dtype=np.float32) / sr
        g = np.convolve(noise[i0:i0 + gn], k)[:gn] * \
            np.exp(-rng.uniform(60.0, 170.0) * tg).astype(np.float32)
        crumble[i0:i0 + gn] += g * float(rng.uniform(0.4, 1.0))

    out = (0.75 * grit + 0.45 * crack + 0.95 * thud + 0.9 * crumble)
    out = out.astype(np.float32)
    a = min(int(0.001 * sr), n)
    out[:a] *= np.linspace(0.0, 1.0, a, dtype=np.float32)
    peak = float(np.max(np.abs(out))) or 1.0
    return out / peak * (0.45 + 0.55 * size)


def synth_balloon_pop(size: float, seed: int = 0, sr: int = SR,
                      boom_w: float = 0.75) -> np.ndarray:
    """Balloon POP, to layer UNDER the note: a sub-millisecond CRACK, a short
    burst of escaping air, and a low body BOOM.

    ``size`` (0..1) is how big the balloon was when it burst, and it drives the
    boom's pitch and decay — a big one lands as a deep BANG, a small one as a
    tight snap. That size-to-pitch mapping is the most legible thing about a
    real pop and it is free here, because the sim already knows the radius of
    the thing that just burst. Deterministic (seeded).
    """
    size = float(np.clip(size, 0.0, 1.0))
    dur = 0.16 + 0.10 * size
    n = int(dur * sr)
    t = np.arange(n, dtype=np.float32) / sr
    rng = np.random.default_rng(seed)
    noise = rng.standard_normal(n).astype(np.float32)

    # the snap: broadband, gone in ~2ms. This is what makes it read as a POP
    # rather than as a drum hit.
    crack = noise * np.exp(-900.0 * t).astype(np.float32)
    # escaping air: noise smoothed by a short exponential kernel (vectorised —
    # a per-sample loop here would run per cache miss), decaying fast
    k = np.exp(-np.arange(48, dtype=np.float32) * (0.30 - 0.16 * size))
    k /= k.sum()
    air = np.convolve(noise, k)[:n] * np.exp(-38.0 * t).astype(np.float32)
    # body boom: lower and longer the bigger the balloon, with a slight downward
    # sweep so it lands rather than beeps
    f0 = 210.0 - 145.0 * size
    ph = 2 * np.pi * (f0 * t - 0.35 * f0 * t * t)
    boom = np.sin(ph).astype(np.float32) * np.exp(-(46.0 - 22.0 * size) * t).astype(np.float32)

    # boom_w is the ONLY part of this worth a dial: at the default 0.75 the boom
    # carries ~92% of a full-size pop's energy and rings 177ms, so it is heard as
    # a SECOND sound landing behind the crack (Luka, 2026-08-12: "there is pop
    # sound and other sound when ball is poping"). Pulling it back keeps the
    # snap and the escaping-air hiss while shortening what follows them.
    out = (0.85 * crack + 0.55 * air + float(boom_w) * boom).astype(np.float32)
    a = min(int(0.0004 * sr), n)          # de-click the very first samples only
    if a:
        out[:a] *= np.linspace(0.0, 1.0, a, dtype=np.float32)
    peak = float(np.max(np.abs(out))) or 1.0
    return out / peak * (0.55 + 0.45 * size)


def synth_steam(size: float, seed: int = 0, sr: int = SR) -> np.ndarray:
    """Steam HISS, to layer under (or instead of) the note — a flame being
    QUENCHED, the fire-spiral signature. Deliberately NOT an impact: no crack,
    no boom — a soft ~8ms onset into a band-limited noise hiss whose
    brightness SWEEPS DOWN as it decays (the sizzle dying), plus a faster
    "chh" head so a dense run still reads as separate quenches rather than
    static (broadband TAILS are what pile into static at density, so the
    smaller the size the shorter the tail). ``size`` 0..1: a per-flame quench
    tick at ~0.1s up to a whole ball's evaporation at ~0.45s. Deterministic
    (seeded)."""
    size = float(np.clip(size, 0.0, 1.0))
    dur = 0.09 + 0.36 * size
    n = int(dur * sr)
    t = np.arange(n, dtype=np.float32) / sr
    rng = np.random.default_rng(seed)
    noise = rng.standard_normal(n).astype(np.float32)
    # bright head vs dull tail: the same noise through a narrow and a wide
    # smoothing kernel, crossfaded over the duration = a downward sweep
    kb = np.exp(-np.arange(8, dtype=np.float32) * 0.9)
    kb /= kb.sum()
    kd = np.exp(-np.arange(48, dtype=np.float32) * 0.10)
    kd /= kd.sum()
    bright = np.convolve(noise, kb)[:n]
    dull = np.convolve(noise, kd)[:n]
    xf = np.clip(t / dur, 0.0, 1.0).astype(np.float32)
    hiss = bright * (1.0 - xf) + dull * xf
    env = np.minimum(t / 0.008, 1.0) * np.exp(-(4.2 / dur) * t)
    chh = bright * np.exp(-90.0 * t)          # the quench's own short head
    out = (0.9 * hiss * env + 0.6 * chh).astype(np.float32)
    peak = float(np.max(np.abs(out))) or 1.0
    return out / peak * (0.45 + 0.55 * size)


def synth_splash(size: float, seed: int = 0, sr: int = SR) -> np.ndarray:
    """WATER ENTRY — a shape breaking the surface (buoy_merge's rain).

    Built around a RISING pitch chirp, not around noise, and that is the whole
    design. A real drop reads as water because of the Helmholtz tone of the
    bubble it entrains: the cavity shrinks as it closes, so the pitch sweeps
    UP over a few tens of ms. That tone is what the ear labels "water", and
    being TONAL it survives density — whereas broadband noise with a tail is
    exactly what piles into static when a hundred of them land in a second
    (synth_steam's lesson, and CLAUDE.md's "pop, not shatter").

    So: ~85% rising chirp with a fast decay, plus a ~7ms filtered noise head
    for the surface break and NO noise tail at all. ``size`` 0..1 runs from a
    light tick (a stick landing flat) to a deep plop (a big polygon punching
    through); bigger means LOWER and longer, the way a bigger cavity does.
    Deterministic (seeded)."""
    size = float(np.clip(size, 0.0, 1.0))
    dur = 0.055 + 0.105 * size
    n = int(dur * sr)
    t = np.arange(n, dtype=np.float32) / sr
    rng = np.random.default_rng(seed)

    # the bubble tone: exponential glide UP, ~1.6x over the sound
    f0 = 900.0 - 470.0 * size
    f1 = f0 * (1.55 + 0.25 * size)
    phase = 2.0 * math.pi * f0 * dur / math.log(f1 / f0) * (
        (f1 / f0) ** (t / dur) - 1.0)
    tone = np.sin(phase).astype(np.float32) * np.exp(-(5.5 / dur) * t)

    # the surface break: a few ms of dull noise, hard-gated so nothing rings on
    k = np.exp(-np.arange(10, dtype=np.float32) * 0.55)
    k /= k.sum()
    head = np.convolve(rng.standard_normal(n).astype(np.float32),
                       k)[:n] * np.exp(-260.0 * t)

    out = (0.86 * tone + 0.34 * head).astype(np.float32)
    out *= np.minimum(t / 0.0015, 1.0)          # de-click the attack
    peak = float(np.max(np.abs(out))) or 1.0
    return out / peak * (0.45 + 0.55 * size)


def synth_zap(size: float, seed: int = 0, sr: int = SR) -> np.ndarray:
    """A LASER ZAP ("pew") for laser_hunt: a fast downward sine chirp with a
    soft second harmonic and a 3 ms noise tick at the front.

    Deliberately PLEASANT (CLAUDE.md, no creepy / no annoying): pure tones,
    no broadband tail, ~110 ms, so a 10/s stream of them reads as a chirping
    pulse, not static. ``size`` (0..1) sets the start pitch (1.6-2.5 kHz), so
    the six NoteBank buckets give six different pews and a volley does not
    machine-gun one waveform. Deterministic (seeded)."""
    size = float(np.clip(size, 0.0, 1.0))
    dur = 0.09 + 0.05 * size
    n = int(dur * sr)
    t = np.arange(n, dtype=np.float32) / sr
    f_hi = 1600.0 + 900.0 * size
    f_lo = f_hi * 0.32
    tau = dur / 3.0
    f = f_lo + (f_hi - f_lo) * np.exp(-t / tau)
    ph = 2 * np.pi * np.cumsum(f) / sr
    env = (1.0 - np.exp(-t * 2500.0)) * np.exp(-t / (dur / 2.6))
    tone = (np.sin(ph) + 0.28 * np.sin(2 * ph)) * env
    rng = np.random.default_rng(seed)
    tick = rng.standard_normal(n).astype(np.float32) * np.exp(-t * 900.0) * 0.18
    out = (tone + tick).astype(np.float32)
    a = min(int(0.0005 * sr), n)
    if a:
        out[:a] *= np.linspace(0.0, 1.0, a, dtype=np.float32)
    b = min(int(0.006 * sr), n)
    if b:
        out[-b:] *= np.linspace(1.0, 0.0, b, dtype=np.float32)
    peak = float(np.max(np.abs(out))) or 1.0
    return out / peak * 0.7


def synth_bounce(size: float, seed: int = 0, sr: int = SR) -> np.ndarray:
    """A rubber-ball BOUNCE "tock" (laser_sweep): a pitched thump dropping
    ~1.3 octaves in 80 ms with a 1.5 ms contact click. One sound per bounce,
    every bounce — the channel's one-note rule for a repeated event, as an SFX.
    ``size`` (0..1) nudges the pitch so the six buckets are siblings, not
    an audible ladder. Deterministic (seeded)."""
    size = float(np.clip(size, 0.0, 1.0))
    dur = 0.11
    n = int(dur * sr)
    t = np.arange(n, dtype=np.float32) / sr
    f_hi = 470.0 * (0.88 + 0.24 * size)
    f = f_hi * np.exp(-t / 0.035) * 0.6 + f_hi * 0.4 * np.exp(-t / 0.2)
    ph = 2 * np.pi * np.cumsum(f) / sr
    env = (1.0 - np.exp(-t * 4000.0)) * np.exp(-t / 0.028)
    body = (np.sin(ph) + 0.30 * np.sin(2 * ph) + 0.08 * np.sin(3 * ph)) * env
    rng = np.random.default_rng(seed)
    click = rng.standard_normal(n).astype(np.float32) * np.exp(-t * 1800.0) * 0.35
    out = (body + click).astype(np.float32)
    a = min(int(0.0004 * sr), n)
    if a:
        out[:a] *= np.linspace(0.0, 1.0, a, dtype=np.float32)
    peak = float(np.max(np.abs(out))) or 1.0
    return out / peak * 0.8


def synth_vaporise(size: float, seed: int = 0, sr: int = SR) -> np.ndarray:
    """A ball VAPORISED by a beam (laser_sweep): a bright 30 ms crackle plus a
    descending "zip" (1.8 kHz -> 350 Hz in 90 ms). No low boom and no tail, so
    a 30/s storm of them reads as sizzling, not as static or bass pile-up."""
    size = float(np.clip(size, 0.0, 1.0))
    dur = 0.12
    n = int(dur * sr)
    t = np.arange(n, dtype=np.float32) / sr
    rng = np.random.default_rng(seed)
    noise = rng.standard_normal(n).astype(np.float32)
    crackle = np.diff(noise, prepend=0.0) * np.exp(-t * 70.0) * 0.55
    f_hi, f_lo = 1800.0 + 500.0 * size, 350.0
    f = f_lo + (f_hi - f_lo) * np.exp(-t / 0.03)
    ph = 2 * np.pi * np.cumsum(f) / sr
    zip_ = np.sin(ph) * (1.0 - np.exp(-t * 3000.0)) * np.exp(-t * 32.0)
    out = (crackle + 0.9 * zip_).astype(np.float32)
    b = min(int(0.005 * sr), n)
    if b:
        out[-b:] *= np.linspace(1.0, 0.0, b, dtype=np.float32)
    peak = float(np.max(np.abs(out))) or 1.0
    return out / peak * 0.7


def synth_ignite(size: float, seed: int = 0, sr: int = SR) -> np.ndarray:
    """A flame catching (steam_split's relight): a soft low "whoomph" — a
    band-passed noise burst with a 12 ms attack and a ~0.3 s decay, a sub thump
    sliding 95 -> 45 Hz under it, and a sparse crackle over the tail. No bright
    click and no long tail, so a handful of them read as a fire catching, not
    as an impact. ``size`` 0..1 scales the thump and the length."""
    size = float(np.clip(size, 0.0, 1.0))
    dur = 0.28 + 0.22 * size
    n = int(dur * sr)
    t = np.arange(n, dtype=np.float32) / sr
    rng = np.random.default_rng(900 + seed)
    noise = rng.standard_normal(n).astype(np.float32)
    k = np.exp(-np.arange(40, dtype=np.float32) * 0.09)
    k /= k.sum()
    low = np.convolve(noise, k)[:n]
    hp = np.diff(low, prepend=low[:1]) * 6.0
    body = (low * 0.6 + hp) * np.minimum(t / 0.012, 1.0) * np.exp(-(7.0 - 2.0 * size) * t)
    f = 45.0 + 50.0 * np.exp(-t / 0.09)
    ph = 2 * np.pi * np.cumsum(f) / sr
    thump = np.sin(ph) * np.exp(-t * 14.0) * (0.5 + 0.5 * size)
    crack = np.zeros(n, dtype=np.float32)
    for i in rng.integers(int(0.03 * sr), n, size=18):
        crack[i] = rng.uniform(0.3, 1.0) * float(np.exp(-t[i] * 5.0))
    kc = np.exp(-np.arange(24, dtype=np.float32) * 0.35)
    crack = np.convolve(crack, kc)[:n] * 0.5
    out = (body + thump + crack).astype(np.float32)
    b = min(int(0.01 * sr), n)
    if b:
        out[-b:] *= np.linspace(1.0, 0.0, b, dtype=np.float32)
    peak = float(np.max(np.abs(out))) or 1.0
    return out / peak * (0.55 + 0.45 * size)


def synth_laser_sweep(dur: float, seed: int = 0, sr: int = SR) -> np.ndarray:
    """A laser SWEEP (laser_sweep): the beam switches on with a chirp, then
    holds a soft rising tone (one octave over the sweep, 6 Hz tremolo) under
    a band-limited whoosh, and releases over 150 ms. ``dur`` = the sweep's
    real duration, so a bigger rotation is audibly a longer, higher sweep —
    the escalation is IN the sound. Sine-heavy on purpose (CLAUDE.md: no
    annoying, no creepy): the body sits under the transients."""
    dur = float(max(0.08, dur))
    rel = 0.15
    n = int((dur + rel) * sr)
    t = np.arange(n, dtype=np.float32) / sr
    u = np.clip(t / dur, 0.0, 1.0)
    f = 240.0 * (2.0 ** u)
    ph = 2 * np.pi * np.cumsum(f) / sr
    trem = 1.0 - 0.15 * (0.5 - 0.5 * np.cos(2 * np.pi * 6.0 * t))
    body = (np.sin(ph) + 0.35 * np.sin(2 * ph) + 0.12 * np.sin(3 * ph)) * trem * 0.45
    # switch-on chirp
    m = int(0.06 * sr)
    tc = t[:m]
    fc = 700.0 + 1700.0 * np.exp(-tc / 0.02)
    chirp = np.zeros(n, dtype=np.float32)
    chirp[:m] = np.sin(2 * np.pi * np.cumsum(fc) / sr) * np.exp(-tc * 40.0)
    rng = np.random.default_rng(seed)
    noise = rng.standard_normal(n).astype(np.float32)
    k = np.ones(24, dtype=np.float32) / 24.0
    whoosh = np.convolve(noise, k)[:n] * 0.5
    whoosh *= 0.35 + 0.65 * np.sin(np.pi * np.clip(u, 0, 1)) ** 2
    env = np.ones(n, dtype=np.float32)
    a = int(0.008 * sr)
    env[:a] = np.linspace(0.0, 1.0, a, dtype=np.float32)
    r0 = int(dur * sr)
    env[r0:] = np.exp(-(t[r0:] - dur) / (rel / 3.5))
    env[-int(0.004 * sr):] *= np.linspace(1.0, 0.0, int(0.004 * sr), dtype=np.float32)
    out = ((body + whoosh) * env + 0.8 * chirp).astype(np.float32)
    peak = float(np.max(np.abs(out))) or 1.0
    return out / peak * 0.6


def synth_chomp(size: float, seed: int = 0, sr: int = SR) -> np.ndarray:
    """PELLET CHOMP (spiral_core's pacman edition): a fast pitch SWEEP, DOWN on
    even seeds and UP on odd ones, so a run of them alternates "wa-ka". Our own
    synthesis, not a sample: a sine with a touch of third harmonic (the
    square-ish arcade timbre), ~70 ms, hard-gated so a dense run stays a pulse
    rather than a tone. ``size`` (0..1) widens the sweep."""
    size = float(np.clip(size, 0.0, 1.0))
    dur = 0.070
    n = int(dur * sr)
    t = np.arange(n, dtype=np.float32) / sr
    f_hi = 480.0 + 180.0 * size
    f_lo = 165.0
    f0, f1 = (f_lo, f_hi) if (int(seed) % 2) else (f_hi, f_lo)
    ph = 2 * np.pi * (f0 * t + 0.5 * (f1 - f0) * t * t / dur)
    wave = np.sin(ph) + 0.35 * np.sin(3.0 * ph)
    env = np.minimum(t / 0.004, 1.0) * np.minimum((dur - t) / 0.014, 1.0)
    out = (wave * env).astype(np.float32)
    peak = float(np.max(np.abs(out))) or 1.0
    return out / peak * 0.8


def synth_wakka(midi_note: int, up: bool, sr: int = SR) -> np.ndarray:
    """A PITCHED chomp (pacman mix B): the same 70 ms sweep as synth_chomp,
    but sweeping THROUGH the melody note (f/1.4 -> f*1.4 or back), so the
    pellets themselves play the tune — one note per pellet, "wa" and "ka"
    alternating. Own synthesis."""
    f = midi_to_hz(int(np.clip(midi_note, 36, 96)))
    dur = 0.070
    n = int(dur * sr)
    t = np.arange(n, dtype=np.float32) / sr
    f0, f1 = (f / 1.4, f * 1.4) if up else (f * 1.4, f / 1.4)
    ph = 2 * np.pi * (f0 * t + 0.5 * (f1 - f0) * t * t / dur)
    wave = np.sin(ph) + 0.35 * np.sin(3.0 * ph)
    env = np.minimum(t / 0.004, 1.0) * np.minimum((dur - t) / 0.014, 1.0)
    out = (wave * env).astype(np.float32)
    peak = float(np.max(np.abs(out))) or 1.0
    return out / peak * 0.8


def synth_pulse_note(midi_note: int, dur: float, sr: int = SR,
                     gain: float = 1.0) -> np.ndarray:
    """One note of the arcade PULSE lead: odd harmonics (a square), 3 ms
    attack, a little decay, 15 ms release. For synth_jingle."""
    f = midi_to_hz(int(midi_note))
    n = int(dur * sr)
    t = np.arange(n, dtype=np.float32) / sr
    ph = 2 * np.pi * f * t
    w = (np.sin(ph) + np.sin(3 * ph) / 3.0 + np.sin(5 * ph) / 5.0
         + np.sin(7 * ph) / 7.0)
    env = (np.minimum(t / 0.003, 1.0) * np.minimum((dur - t) / 0.015, 1.0)
           * (0.75 + 0.25 * np.exp(-8.0 * t)))
    return (w * env * gain / 1.2).astype(np.float32)


def synth_jingle(score, bpm, sr: int = SR, gain: float = 0.6,
                 bass=None, bass_gain: float = 0.35) -> np.ndarray:
    """A (midi, beats) score played straight in the pulse-lead timbre, with
    an optional bass line. Returns mono float32."""
    spb = 60.0 / bpm
    total = sum(d for _n, d in score) * spb
    out = np.zeros(int((total + 0.3) * sr), dtype=np.float32)
    for voice, g in ((score, gain), (bass or [], bass_gain)):
        t0 = 0.0
        for (n, d) in voice:
            if n is not None:
                w = synth_pulse_note(n, d * spb * 0.92, sr, g)
                i0 = int(t0 * sr)
                out[i0:i0 + len(w)] += w[: max(0, len(out) - i0)]
            t0 += d * spb
    return out


# The GAME'S OWN recordings, when Luka drops them in (sfx/pacman/<name>.wav):
# any file present overrides the synthesized sound of the same name in the
# mixer (NoteBank.*) and in spiral_core's bed builder. Absent = synthesis.
PAC_SAMPLE_FILES = {
    "wakka": "pacman/wakka.wav",        # the chomp (unpitched, alternates)
    "death": "pacman/death.wav",
    "gulp": "pacman/eat_ghost.wav",
    "power": "pacman/power.wav",
    "intro": "pacman/intro.wav",        # the start jingle
    "siren": "pacman/siren.wav",        # a loopable chase siren
    "fright": "pacman/fright.wav",      # a loopable frightened warble
}


def pac_sample(name: str):
    """The game's recording for `name`, resampled to SR, or None."""
    rel = PAC_SAMPLE_FILES.get(name)
    if rel and (SFX_DIR / rel).exists():
        return load_sample(rel)
    return None


def synth_gulp(seed: int = 0, sr: int = SR) -> np.ndarray:
    """A GHOST being eaten: two rising steps (an octave apart) with the same
    square-ish timbre as the chomp, ~0.28 s. Own synthesis."""
    dur = 0.28
    n = int(dur * sr)
    t = np.arange(n, dtype=np.float32) / sr
    base = 230.0 * (1.0 + 0.06 * (int(seed) % 3))
    f = np.where(t < 0.5 * dur, base * (1.0 + 2.0 * t / dur),
                 2.0 * base * (1.0 + 1.6 * (t - 0.5 * dur) / dur))
    ph = 2 * np.pi * np.cumsum(f) / sr
    wave = np.sin(ph) + 0.30 * np.sin(3.0 * ph)
    env = np.minimum(t / 0.005, 1.0) * np.exp(-6.0 * t / dur)         * np.minimum((dur - t) / 0.01, 1.0)
    out = (wave * env).astype(np.float32)
    peak = float(np.max(np.abs(out))) or 1.0
    return out / peak * 0.85


def synth_pacdeath(sr: int = SR) -> np.ndarray:
    """PAC-MAN'S DEATH: a falling siren under a tremolo that slows as it sinks,
    then two dry pops. ~1.15 s. Own synthesis — nothing sampled."""
    dur = 1.15
    n = int(dur * sr)
    t = np.arange(n, dtype=np.float32) / sr
    f = 760.0 * np.exp(-2.1 * t) + 95.0
    ph = 2 * np.pi * np.cumsum(f) / sr
    trem_f = 12.0 - 7.0 * t / dur
    trem = 0.55 + 0.45 * np.sin(2 * np.pi * np.cumsum(trem_f) / sr)
    body = (np.sin(ph) + 0.30 * np.sin(2.0 * ph)) * trem
    env = np.minimum(t / 0.01, 1.0) * np.where(t < 0.80, 1.0,
                                                np.exp(-30.0 * (t - 0.80)))
    out = (body * env * 0.8).astype(np.float32)
    rng = np.random.default_rng(7)
    for t0 in (0.88, 1.00):
        i0 = int(t0 * sr)
        m = int(0.018 * sr)
        pop = rng.standard_normal(m).astype(np.float32) * np.exp(
            -np.arange(m, dtype=np.float32) / (0.004 * sr))
        out[i0:i0 + m] += 0.9 * pop[: max(0, min(m, n - i0))]
    peak = float(np.max(np.abs(out))) or 1.0
    return out / peak * 0.9


def synth_power(sr: int = SR) -> np.ndarray:
    """The POWER PELLET (pacman edition, mix B): a rising five-note arpeggio
    of the chomp's square-ish timbre — the arcade's "you just got the big
    one" flourish, ~0.42 s. Own synthesis."""
    steps = [0, 4, 7, 12, 16]
    dur_n = 0.085
    out = np.zeros(int((dur_n * len(steps) + 0.25) * sr), dtype=np.float32)
    for k, st in enumerate(steps):
        f = 330.0 * (2.0 ** (st / 12.0))
        n = int((dur_n + 0.18) * sr)
        t = np.arange(n, dtype=np.float32) / sr
        w = np.sin(2 * np.pi * f * t) + 0.35 * np.sin(2 * np.pi * 3 * f * t)
        env = np.minimum(t / 0.004, 1.0) * np.exp(-14.0 * t)
        i0 = int(k * dur_n * sr)
        out[i0:i0 + n] += (w * env).astype(np.float32) * (0.7 + 0.06 * k)
    peak = float(np.max(np.abs(out))) or 1.0
    return out / peak * 0.9


def synth_siren(n: int, f0: float, sr: int = SR, lfo_hz: float = 1.15,
                spread: float = 1.45, fast: bool = False) -> np.ndarray:
    """The GHOST SIREN (pacman edition, mix B): a soft tone wobbling between
    f0 and f0*spread on a triangle LFO — the arcade's chase drone, but
    lowpassed by construction (sine + a little 2nd) and meant to sit ~25 dB
    under the events. `fast` is the frightened-mode warble. Own synthesis."""
    t = np.arange(n, dtype=np.float32) / sr
    lfo = 2.0 * np.abs(((lfo_hz * (3.2 if fast else 1.0)) * t) % 1.0 - 0.5)
    f = f0 * (1.0 + (spread - 1.0) * lfo)
    ph = 2 * np.pi * np.cumsum(f) / sr
    return (np.sin(ph) + 0.25 * np.sin(2.0 * ph)).astype(np.float32) * 0.8


def synth_plink(midi_note: int, sr: int = SR, ring: float = 1.0) -> np.ndarray:
    """Deterministic marimba-like one-shot. Lower notes ring longer.

    ring: scales how long the note SUSTAINS (1.0 = the channel default, which
    holds a note ~400 ms above -20 dB). Below 1.0 the note decays faster and
    the buffer shortens to match. This is the ARTICULATION lever: a note rings
    400 ms while a busy scene fires one every ~100 ms, so 4-8 notes overlap at
    the climax and a single-line melody arrives as a moving chord cluster
    instead of a tune. ring=1.0 is bit-identical to the old code path."""
    f0 = midi_to_hz(midi_note)
    dur = float(np.clip(1.6 - (midi_note - 48) * 0.012, 0.35, 1.4))
    if ring != 1.0:
        dur *= float(ring)
    n = int(dur * sr)
    t = np.arange(n, dtype=np.float32) / sr
    # marimba-ish partials: fundamental + 3.93x + 9.17x, each decaying faster
    out = np.zeros(n, dtype=np.float32)
    for ratio, amp, decay in ((1.0, 1.00, 5.0), (3.93, 0.28, 14.0), (9.17, 0.10, 30.0)):
        decay = decay / float(ring) if ring != 1.0 else decay
        f = f0 * ratio
        if f < sr / 2 * 0.95:
            out += amp * np.sin(2 * np.pi * f * t).astype(np.float32) * \
                np.exp(-decay * t).astype(np.float32)
    # mallet contact: tiny bright click, deterministic (no RNG)
    click = np.sin(2 * np.pi * 2093.0 * t) * np.exp(-220.0 * t)
    out += 0.12 * click.astype(np.float32)
    # 2ms attack ramp to avoid pops
    a = min(int(0.002 * sr), n)
    out[:a] *= np.linspace(0.0, 1.0, a, dtype=np.float32)
    peak = float(np.max(np.abs(out))) or 1.0
    return out / peak


def synth_void(midi_note: int, sr: int = SR) -> np.ndarray:
    """A SWALLOW: filtered noise swept downward, plus a soft sub thump.

    An SFX voice rather than a musical one, for scenes where the event has no
    pitch to encode — accretion's pieces all cross the same horizon at much
    the same speed, so any physics-to-pitch mapping there is a monotone and a
    marimba just states it 900 times (see CLAUDE.md's audio gotchas).

    It still TAKES the note, and that is the point: a sample one-shot
    (SAMPLE_VOICES) ignores the note and plays one identical buffer every hit,
    which is the same buzzer by another route. Here the note only shifts where
    the sweep starts, so consecutive hits differ audibly without ever spelling
    a tune, and dense passages pile into a rushing roar instead of a rattle.

    Deterministic: the noise is seeded from the note (CLAUDE.md's determinism
    rule — no wall-clock RNG anywhere in sim or render).
    """
    dur = 0.28
    n = int(dur * sr)
    t = np.arange(n, dtype=np.float32) / sr
    rng = np.random.default_rng(1000 + int(midi_note))
    noise = rng.standard_normal(n).astype(np.float32)
    # a one-pole lowpass whose cutoff slides down over the shot. Sweeping the
    # FILTER (not the pitch of a tone) is what makes it read as something
    # receding rather than as a siren.
    f_hi = midi_to_hz(midi_note) * 3.0
    cutoff = f_hi * np.exp(-4.2 * t) + 70.0
    a = np.exp(-2.0 * np.pi * cutoff / sr).astype(np.float32)
    out = np.empty(n, dtype=np.float32)
    y = 0.0
    for i in range(n):
        y = a[i] * y + (1.0 - a[i]) * noise[i]
        out[i] = y
    out *= np.exp(-9.0 * t).astype(np.float32)
    # the mass landing: a short sub sine an octave and a half under the note
    sub = (np.sin(2 * np.pi * midi_to_hz(midi_note - 19) * t)
           * np.exp(-16.0 * t)).astype(np.float32)
    out += 0.5 * sub
    a0 = min(int(0.003 * sr), n)
    out[:a0] *= np.linspace(0.0, 1.0, a0, dtype=np.float32)
    peak = float(np.max(np.abs(out))) or 1.0
    return out / peak


def synth_drone(duration_s: float, midi_note: float = 29.0, gain: float = 0.06,
                fade_in: float = 8.0, fade_out: float = 3.0,
                sr: int = SR) -> np.ndarray:
    """A sustained SUB-BASS drone — mono float32, `duration_s` long.

    The only way to add real weight to a climax (CLAUDE.md, 2026-07-28): it is
    NOT an event, so it bypasses `mix_events`' 10ms onset thinning and its
    1/sqrt(density) ducking entirely — firing more notes at a dense passage
    makes it QUIETER, a drone under it does not.

    Two slightly detuned sines (fundamental + a 2.01x partial) give a slow beat
    ~0.3 Hz, which is what makes it read as uneasy rather than as a test tone.
    The envelope MUST end at exactly zero: this rides into the loop seam, and a
    non-zero last sample clicks on every repeat.
    """
    n = max(1, int(duration_s * sr))
    t = np.arange(n, dtype=np.float32) / sr
    f0 = midi_to_hz(midi_note)
    out = (np.sin(2 * np.pi * f0 * t)
           + 0.45 * np.sin(2 * np.pi * f0 * 2.01 * t + 0.7)
           + 0.20 * np.sin(2 * np.pi * f0 * 0.5 * t + 1.3)).astype(np.float32)
    env = np.ones(n, dtype=np.float32)
    a = min(int(fade_in * sr), n)
    if a:
        env[:a] = np.linspace(0.0, 1.0, a, dtype=np.float32) ** 2
    d = min(int(fade_out * sr), n)
    if d:
        env[-d:] *= np.linspace(1.0, 0.0, d, dtype=np.float32) ** 1.5
    env[-1] = 0.0
    return out * env * gain


def synth_piano(midi_note: int, sr: int = SR) -> np.ndarray:
    """Deterministic acoustic-piano-like one-shot (additive string model).

    Differs from the marimba (synth_plink) in the three things the ear uses to
    tell a piano from a mallet: (1) a full harmonic series (many partials, not
    just 3 stretched marimba modes), (2) slight string INHARMONICITY — upper
    partials are sharp by sqrt(1 + B*k^2), the shimmer that reads as "struck
    string / piano", (3) a longer, two-stage decay (a bright strike that mellows
    as the upper partials die faster than the fundamental's sustained ring) plus
    a felt-hammer noise thunk. Lower notes ring longer, like a real piano."""
    f0 = midi_to_hz(midi_note)
    dur = float(np.clip(2.6 - (midi_note - 48) * 0.020, 0.55, 2.4))
    n = int(dur * sr)
    t = np.arange(n, dtype=np.float32) / sr
    B = 0.0004                                   # inharmonicity coefficient
    out = np.zeros(n, dtype=np.float32)
    for k in range(1, 13):
        f = k * f0 * math.sqrt(1.0 + B * k * k)
        if f > sr * 0.45:
            break
        amp = (0.86 ** (k - 1)) / (1.0 + 0.12 * k)      # harmonic rolloff
        dec = 2.4 + 0.85 * k + (midi_note - 48) * 0.02  # upper partials fade faster
        out += (amp * np.sin(2 * np.pi * f * t)).astype(np.float32) \
            * np.exp(-dec * t).astype(np.float32)
    # sustained fundamental "ring" (the slow second decay stage)
    body_dec = 1.5 + (midi_note - 48) * 0.02
    out += 0.5 * np.sin(2 * np.pi * f0 * t).astype(np.float32) \
        * np.exp(-body_dec * t).astype(np.float32)
    # felt-hammer thunk: short bright noise burst, deterministic (seeded by note)
    rng = np.random.default_rng(midi_note + 2000)
    tn = int(0.010 * sr)
    click = rng.standard_normal(tn).astype(np.float32) \
        * np.exp(-np.arange(tn, dtype=np.float32) / (0.0022 * sr))
    out[:tn] += 0.14 * click
    a = min(int(0.003 * sr), n)                  # 3ms attack ramp
    out[:a] *= np.linspace(0.0, 1.0, a, dtype=np.float32)
    peak = float(np.max(np.abs(out))) or 1.0
    return out / peak


SFX_DIR = Path(__file__).resolve().parent.parent / "sfx"

# Sample-backed voices: a real one-shot WAV per hit instead of a synth note.
# Unlike every synth voice here, these are NOT pitched by the event's note —
# the scene's ScaleWalker/MelodyWalker still runs, its note is just ignored, so
# a sample voice is a pure "SFX on hit" layer and any clip can be flipped to it
# (or back) from its events sidecar with tools/regen_audio.py, no re-render.
# Provenance matters: only CC0/owned samples belong here (same discipline as the
# PD-only melody rule — see CLAUDE.md).
SAMPLE_VOICES = {
    # CC0 slime squish, shared with the blender-physics project's sfx/ (Luka,
    # 2026-07-17, for the squish scene's "just slime SFX on hit" cut).
    "slime": "slime_squish_cc0.wav",
}



# --- MACHINE SFX (hydro_press, 2026-09-07): an all-SFX soundtrack ------------
#
# The first scene with NO pitched notes at all (Luka: "remove notes ... press
# sounds, robotic sfx, bounce sound for balls"). Four voices, all deterministic
# and all synthesised here — no samples, no licensing surface:
#   servo   the hydraulic drive: a motor whine that SWEEPS across the stroke
#   clank   the slam: inharmonic metal partials + a snap
#   hiss    the pneumatic release on the retract
#   bounce  a ball's rubbery "toc" on a wall
def synth_servo(dur: float, up: bool = True, sr: int = SR) -> np.ndarray:
    """Hydraulic/servo drive whine lasting `dur` s. Pitch sweeps UP on the
    press stroke (load rising) and DOWN on the retract; a buzzy harmonic stack
    with a slow amplitude wobble so it reads as a motor, not a tone."""
    dur = float(max(0.08, min(dur, 3.0)))
    n = int(dur * sr)
    t = np.arange(n, dtype=np.float32) / sr
    f0, f1 = (95.0, 210.0) if up else (200.0, 80.0)
    u = t / dur
    f = f0 + (f1 - f0) * (u ** 0.8)
    ph = 2 * np.pi * np.cumsum(f) / sr
    w = np.zeros(n, dtype=np.float32)
    for h, a in ((1, 1.0), (2, 0.55), (3, 0.42), (4, 0.28), (5, 0.18), (7, 0.10)):
        w += (a * np.sin(h * ph)).astype(np.float32)
    rng = np.random.default_rng(77 if up else 78)
    grit = rng.standard_normal(n).astype(np.float32)
    k = np.exp(-np.arange(24, dtype=np.float32) * 0.25)
    k /= k.sum()
    grit = np.convolve(grit, k)[:n]
    wob = 1.0 + 0.22 * np.sin(2 * np.pi * 27.0 * t)
    env = np.minimum(t / 0.03, 1.0) * np.minimum((dur - t) / 0.06, 1.0)
    env = np.clip(env, 0.0, 1.0)
    out = ((w + 0.35 * grit) * wob * env).astype(np.float32)
    peak = float(np.max(np.abs(out))) or 1.0
    return out / peak * 0.8


def synth_clank(size: float, seed: int = 0, sr: int = SR) -> np.ndarray:
    """Metal SLAM: a broadband snap, then inharmonic partials ringing down at
    different rates (a plate, not a bell). `size` lowers the fundamental and
    lengthens the ring."""
    size = float(np.clip(size, 0.0, 1.0))
    dur = 0.35 + 0.35 * size
    n = int(dur * sr)
    t = np.arange(n, dtype=np.float32) / sr
    rng = np.random.default_rng(300 + seed)
    f0 = 180.0 - 90.0 * size
    ring = np.zeros(n, dtype=np.float32)
    for ratio, amp, dec in ((1.0, 1.0, 9.0), (1.58, 0.7, 12.0), (2.24, 0.55, 15.0),
                            (2.92, 0.4, 19.0), (3.76, 0.3, 24.0), (5.4, 0.2, 30.0)):
        fr = f0 * ratio * float(rng.uniform(0.985, 1.015))
        ring += (amp * np.sin(2 * np.pi * fr * t + float(rng.uniform(0, 6.28)))
                 * np.exp(-dec * t)).astype(np.float32)
    noise = rng.standard_normal(n).astype(np.float32)
    snap = noise * np.exp(-600.0 * t).astype(np.float32)
    body = (np.convolve(noise, np.ones(16, dtype=np.float32) / 16.0)[:n]
            * np.exp(-40.0 * t).astype(np.float32))
    thud = (np.sin(2 * np.pi * (55.0 + 25.0 * size) * t).astype(np.float32)
            * np.exp(-28.0 * t).astype(np.float32))
    out = (0.9 * snap + 0.5 * body + 0.8 * ring + 0.9 * thud).astype(np.float32)
    a = min(int(0.0004 * sr), n)
    if a:
        out[:a] *= np.linspace(0.0, 1.0, a, dtype=np.float32)
    peak = float(np.max(np.abs(out))) or 1.0
    return out / peak * (0.6 + 0.4 * size)


def synth_hiss(size: float, seed: int = 0, sr: int = SR) -> np.ndarray:
    """Pneumatic release: band-limited noise with a fast attack and a ~0.35s
    decay; the "pssht" a press makes when the pressure lets go."""
    size = float(np.clip(size, 0.0, 1.0))
    dur = 0.30 + 0.25 * size
    n = int(dur * sr)
    t = np.arange(n, dtype=np.float32) / sr
    rng = np.random.default_rng(500 + seed)
    noise = rng.standard_normal(n).astype(np.float32)
    hp = np.diff(noise, prepend=noise[:1])
    k = np.exp(-np.arange(6, dtype=np.float32) * 0.5)
    k /= k.sum()
    band = np.convolve(hp, k)[:n]
    env = np.minimum(t / 0.012, 1.0) * np.exp(-(9.0 - 3.0 * size) * t)
    out = (band * env).astype(np.float32)
    peak = float(np.max(np.abs(out))) or 1.0
    return out / peak * (0.5 + 0.5 * size)


def synth_bounce(size: float, seed: int = 0, sr: int = SR) -> np.ndarray:
    """A ball's rubbery TOC on a wall: a damped sine that drops a little in
    pitch over ~60ms plus a tiny contact click. `size` (0..1) = impact
    strength: harder = brighter and a touch longer. NOT a note: the pitch is
    a timbre, the same on every hit within a bucket."""
    size = float(np.clip(size, 0.0, 1.0))
    dur = 0.07 + 0.05 * size
    n = int(dur * sr)
    t = np.arange(n, dtype=np.float32) / sr
    rng = np.random.default_rng(700 + seed)
    f0 = 260.0 + 140.0 * size
    ph = 2 * np.pi * (f0 * t - 0.25 * f0 * t * t)
    tone = np.sin(ph).astype(np.float32) * np.exp(-(52.0 - 12.0 * size) * t).astype(np.float32)
    tone += 0.3 * np.sin(2.0 * ph).astype(np.float32) * np.exp(-90.0 * t).astype(np.float32)
    click = rng.standard_normal(n).astype(np.float32) * np.exp(-1400.0 * t).astype(np.float32)
    out = (tone + 0.25 * click).astype(np.float32)
    a = min(int(0.0004 * sr), n)
    if a:
        out[:a] *= np.linspace(0.0, 1.0, a, dtype=np.float32)
    peak = float(np.max(np.abs(out))) or 1.0
    return out / peak * (0.45 + 0.55 * size)


def load_sample(filename: str, sr: int = SR) -> np.ndarray:
    """Mono float32 one-shot from sfx/, resampled to sr (sfx/ files are 44.1k;
    the mixer is 48k — resample or every hit lands 8.8% sharp and short)."""
    path = SFX_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"sample not found: {path}")
    data, file_sr = sf.read(str(path), dtype="float32")
    if data.ndim > 1:
        data = data.mean(axis=1)
    if file_sr != sr:
        from scipy.signal import resample_poly
        g = math.gcd(int(file_sr), int(sr))
        data = resample_poly(data, sr // g, file_sr // g).astype(np.float32)
    peak = float(np.max(np.abs(data))) or 1.0
    return (data / peak * 0.9).astype(np.float32)   # normalized headroom


#   fuse / cannon / explosion -- cannon_box's three machine sounds

def synth_fuse(dur: float, seed: int = 0, sr: int = SR) -> np.ndarray:
    """A burning FUSE ROPE lasting `dur` s: a soft flickering sizzle plus
    sparse crackles, fading in over 20 ms and out over 50 ms. Kept well under
    the boom it leads into -- it is the wind-up, not the event."""
    dur = float(np.clip(dur, 0.06, 2.0))
    n = int((dur + 0.05) * sr)
    t = np.arange(n, dtype=np.float32) / sr
    rng = np.random.default_rng(1100 + seed)
    noise = rng.standard_normal(n).astype(np.float32)
    hp = np.diff(noise, prepend=noise[:1])
    k = np.exp(-np.arange(7, dtype=np.float32) * 0.45)
    k /= k.sum()
    hiss = np.convolve(hp, k)[:n]
    m = max(2, int(dur * 25) + 3)
    ctrl = rng.uniform(0.35, 1.0, m).astype(np.float32)
    flick = np.interp(t, np.linspace(0.0, dur + 0.05, m), ctrl).astype(np.float32)
    crack = np.zeros(n, dtype=np.float32)
    cnt = int(38 * dur) + 2
    idx = rng.integers(0, max(1, n - 400), size=cnt)
    crack[idx] = (rng.uniform(0.4, 1.0, cnt) * rng.choice([-1.0, 1.0], cnt)).astype(np.float32)
    kc = np.exp(-np.arange(60, dtype=np.float32) * 0.12)
    crack = np.convolve(crack, kc)[:n]
    crack /= float(np.max(np.abs(crack))) or 1.0
    hiss /= float(np.max(np.abs(hiss))) or 1.0
    env = np.minimum(t / 0.02, 1.0) * np.clip((dur + 0.05 - t) / 0.05, 0.0, 1.0)
    out = ((0.45 * hiss * flick + 0.55 * crack) * env).astype(np.float32)
    peak = float(np.max(np.abs(out))) or 1.0
    return out / peak * 0.5


def _smooth_noise(noise, rate, length):
    k = np.exp(-np.arange(length, dtype=np.float32) * rate)
    k /= k.sum()
    out = np.convolve(noise, k)[:len(noise)]
    return out / (float(np.max(np.abs(out))) or 1.0)


def synth_cannon(size: float, seed: int = 0, sr: int = SR) -> np.ndarray:
    """Cannon BOOM: a short dull crack, a noise blast, a sub thump sliding down
    from ~110 Hz and a low rumble. No sub-ms click (AAC rings on those).
    `size` 1.0 = the giant shot: deeper, longer, more rumble."""
    size = float(np.clip(size, 0.0, 1.0))
    dur = 0.55 + 0.95 * size
    n = int(dur * sr)
    t = np.arange(n, dtype=np.float32) / sr
    rng = np.random.default_rng(1200 + seed)
    noise = rng.standard_normal(n).astype(np.float32)
    crack = _smooth_noise(noise, 0.5, 12) * np.minimum(t / 0.0015, 1.0) * np.exp(-t / 0.007)
    body = (_smooth_noise(noise, 0.10 - 0.06 * size, 96) * np.minimum(t / 0.002, 1.0)
            * np.exp(-(10.0 - 5.0 * size) * t))
    fr = (38.0 - 8.0 * size) + 72.0 * np.exp(-t / 0.06)
    thump = (np.sin(2 * np.pi * np.cumsum(fr) / sr) * np.minimum(t / 0.004, 1.0)
             * np.exp(-(7.0 - 3.5 * size) * t))
    rumble = (_smooth_noise(noise[::-1].copy(), 0.012, 400) * np.minimum(t / 0.03, 1.0)
              * np.exp(-(4.0 - 2.0 * size) * t))
    out = (0.50 * crack + 0.80 * body + 1.0 * thump + (0.30 + 0.35 * size) * rumble)
    out = out.astype(np.float32)
    b = min(int(0.03 * sr), n)
    out[-b:] *= np.linspace(1.0, 0.0, b, dtype=np.float32)
    peak = float(np.max(np.abs(out))) or 1.0
    return out / peak * (0.6 + 0.4 * size)


def synth_explosion(size: float, seed: int = 0, sr: int = SR) -> np.ndarray:
    """EXPLOSION on impact: a rounded noise blast, a sub thump, debris grains
    scattered over the tail and a rumble. `size` 1.0 = the shockwave that
    clears the whole box (~1.5 s)."""
    size = float(np.clip(size, 0.0, 1.0))
    dur = 0.45 + 1.05 * size
    n = int(dur * sr)
    t = np.arange(n, dtype=np.float32) / sr
    rng = np.random.default_rng(1300 + seed)
    noise = rng.standard_normal(n).astype(np.float32)
    body = (_smooth_noise(noise, 0.08 - 0.05 * size, 110) * np.minimum(t / 0.003, 1.0)
            * np.exp(-(8.0 - 5.0 * size) * t))
    fr = (30.0 - 6.0 * size) + 60.0 * np.exp(-t / 0.08)
    thump = (np.sin(2 * np.pi * np.cumsum(fr) / sr) * np.minimum(t / 0.005, 1.0)
             * np.exp(-(6.0 - 3.5 * size) * t))
    hp = np.diff(noise, prepend=noise[:1])
    grains = np.zeros(n, dtype=np.float32)
    for _ in range(int(6 + 26 * size)):
        t0 = float(rng.uniform(0.04, dur * 0.8))
        i0 = int(t0 * sr)
        gn = min(int(sr * rng.uniform(0.008, 0.030)), n - i0)
        if gn <= 4:
            continue
        tg = np.arange(gn, dtype=np.float32) / sr
        grains[i0:i0 + gn] += (hp[i0:i0 + gn] * np.exp(-rng.uniform(90.0, 220.0) * tg)
                               * float(rng.uniform(0.3, 1.0) * math.exp(-2.0 * t0)))
    grains /= float(np.max(np.abs(grains))) or 1.0
    rumble = (_smooth_noise(noise[::-1].copy(), 0.012, 400) * np.minimum(t / 0.04, 1.0)
              * np.exp(-(3.2 - 1.8 * size) * t))
    out = (0.80 * body + 0.90 * thump + 0.35 * grains + 0.50 * rumble).astype(np.float32)
    b = min(int(0.04 * sr), n)
    out[-b:] *= np.linspace(1.0, 0.0, b, dtype=np.float32)
    peak = float(np.max(np.abs(out))) or 1.0
    return out / peak * (0.55 + 0.45 * size)


# --- DROP-HAMMER SFX (drop_hammer, 2026-09-16) --------------------------------
#
# hydro_press's machine set measured NOISY (first-10 s centroid 5,721 Hz, 38.9%
# above 4 kHz — its release hiss alone is 94% above 4 kHz). This set is tonal
# and mid-range on purpose: every voice puts its energy at 250-1,100 Hz, where
# a phone speaker plays it, and nearly none above 4 kHz. No sub-ms clicks
# (AAC rings on them): every attack ramps over >= 1 ms.
#   ratchet  the hoist's pawl ticking over one chain link
#   latch    the release clunk at the top of the hoist
#   slam     the hammer landing: thump + mid knock + anvil ring (+ crunch)
#   pok      a ball's light plastic bounce
#   squash   a ball crushed: a downward squelch with a soft pop edge
#   snap     the chain snapping at the break
def _sfx_ramp(out, ms, sr):
    a = min(int(ms * 1e-3 * sr), len(out))
    if a:
        out[:a] *= np.linspace(0.0, 1.0, a, dtype=np.float32)
    return out


def _sfx_fade(out, ms, sr):
    b = min(int(ms * 1e-3 * sr), len(out))
    if b:
        out[-b:] *= np.linspace(1.0, 0.0, b, dtype=np.float32)
    return out


def _lp_noise(rng, n, k):
    x = rng.standard_normal(n).astype(np.float32)
    ker = np.exp(-np.arange(k, dtype=np.float32) * (3.0 / k))
    ker /= ker.sum()
    y = np.convolve(x, ker)[:n]
    return y / (float(np.max(np.abs(y))) or 1.0)


def synth_ratchet(size: float, seed: int = 0, sr: int = SR) -> np.ndarray:
    """The hoist's pawl dropping over one chain link: a short woody-metal TICK
    (1.2 kHz + 2.65 kHz modes over a 165 Hz knock). `size` = hoist speed."""
    size = float(np.clip(size, 0.0, 1.0))
    n = int(0.07 * sr)
    t = np.arange(n, dtype=np.float32) / sr
    rng = np.random.default_rng(2100 + seed)
    j = float(rng.uniform(0.97, 1.03))
    tone = (np.sin(2 * np.pi * 1180.0 * j * t) * np.exp(-70.0 * t)
            + 0.30 * np.sin(2 * np.pi * 2650.0 * j * t + 1.1) * np.exp(-150.0 * t))
    body = 0.45 * np.sin(2 * np.pi * 165.0 * t) * np.exp(-55.0 * t)
    out = _sfx_fade(_sfx_ramp((tone + body).astype(np.float32), 1.5, sr), 6.0, sr)
    return out / (float(np.max(np.abs(out))) or 1.0) * (0.55 + 0.45 * size)


def synth_latch(seed: int = 0, sr: int = SR) -> np.ndarray:
    """The release at the top of the hoist: a mid CLUNK over a low thump."""
    n = int(0.16 * sr)
    t = np.arange(n, dtype=np.float32) / sr
    rng = np.random.default_rng(2200 + seed)
    clunk = (np.sin(2 * np.pi * 540.0 * t) * np.exp(-40.0 * t)
             + 0.60 * np.sin(2 * np.pi * 1290.0 * t + 0.7) * np.exp(-60.0 * t))
    thump = 0.8 * np.sin(2 * np.pi * 105.0 * t) * np.exp(-30.0 * t)
    grit = 0.25 * _lp_noise(rng, n, 10) * np.exp(-120.0 * t)
    out = _sfx_fade(_sfx_ramp((clunk + thump + grit).astype(np.float32), 1.5, sr), 6.0, sr)
    return out / (float(np.max(np.abs(out))) or 1.0) * 0.8


def synth_slam(size: float, crunch: float = 0.0, ring: float = 1.0, seed: int = 0,
               sr: int = SR) -> np.ndarray:
    """The drop hammer landing in the bowl: a thump sliding down, a mid KNOCK
    (what a phone speaker actually plays), a bright ANVIL ring (inharmonic
    partials) and, when the blow crushed something, a crunch of grains inside
    the SAME onset — one action, one sound. `ring` < 1 shortens the anvil ring
    for a fast jam, where long rings would pile into a metallic wash."""
    size = float(np.clip(size, 0.0, 1.0))
    crunch = float(np.clip(crunch, 0.0, 1.0))
    ring = float(np.clip(ring, 0.0, 1.0))
    dur = 0.70 + 0.40 * size
    n = int(dur * sr)
    t = np.arange(n, dtype=np.float32) / sr
    rng = np.random.default_rng(2300 + seed)
    att = np.minimum(t / 0.002, 1.0)
    fr = (52.0 - 8.0 * size) + 110.0 * np.exp(-t / 0.030)
    thump = np.sin(2 * np.pi * np.cumsum(fr) / sr) * att * np.exp(-t / (0.11 + 0.07 * size))
    knock = (np.sin(2 * np.pi * 215.0 * t) * np.exp(-t / 0.050)
             + 0.7 * np.sin(2 * np.pi * 470.0 * t + 0.9) * np.exp(-t / 0.032)) * att
    body = _lp_noise(rng, n, 30) * att * np.exp(-t / 0.035)
    fa = 660.0 * (1.0 - 0.10 * size)
    anv = np.zeros(n, dtype=np.float32)
    for ratio, amp, dec in ((1.0, 1.0, 6.0), (2.76, 0.62, 9.0), (5.40, 0.30, 14.0),
                            (8.93, 0.12, 20.0)):
        d = dec / max(0.35, ring)
        anv += (amp * np.sin(2 * np.pi * fa * ratio * float(rng.uniform(0.99, 1.01)) * t
                             + float(rng.uniform(0, 6.28))) * np.exp(-d * t)).astype(np.float32)
    anv *= np.minimum(t / 0.0015, 1.0)
    grains = np.zeros(n, dtype=np.float32)
    if crunch > 0.0:
        hp = rng.standard_normal(n).astype(np.float32)
        hp = np.diff(hp, prepend=hp[:1])
        k = np.exp(-np.arange(8, dtype=np.float32) * 0.6)
        hp = np.convolve(hp, k / k.sum())[:n]
        for _ in range(int(5 + 12 * crunch)):
            i0 = int(float(rng.uniform(0.0, 0.07)) * sr)
            gn = min(int(sr * rng.uniform(0.003, 0.009)), n - i0)
            tg = np.arange(gn, dtype=np.float32) / sr
            grains[i0:i0 + gn] += (hp[i0:i0 + gn] * np.exp(-rng.uniform(250, 600) * tg)
                                   * float(rng.uniform(0.4, 1.0)))
        grains /= float(np.max(np.abs(grains))) or 1.0
    out = (0.75 * thump + 0.60 * knock + 0.30 * body + (0.40 + 0.12 * size) * anv
           + 0.35 * crunch * grains).astype(np.float32)
    out = _sfx_fade(out, 30.0, sr)
    return out / (float(np.max(np.abs(out))) or 1.0) * (0.70 + 0.30 * size)


def synth_pok(size: float, seed: int = 0, sr: int = SR) -> np.ndarray:
    """A ball's light plastic POK: a damped 540-720 Hz tone gliding down a
    touch. Not a note — one timbre, bucketed by impact strength."""
    size = float(np.clip(size, 0.0, 1.0))
    n = int(0.10 * sr)
    t = np.arange(n, dtype=np.float32) / sr
    rng = np.random.default_rng(2400 + seed)
    f0 = (540.0 + 180.0 * size) * float(rng.uniform(0.98, 1.02))
    ph = 2 * np.pi * (f0 * t - 0.45 * f0 * t * t)
    tone = np.sin(ph) * np.exp(-t / (0.026 + 0.010 * size))
    tone += 0.22 * np.sin(2.3 * ph + 0.4) * np.exp(-t / 0.008)
    out = _sfx_fade(_sfx_ramp(tone.astype(np.float32), 0.9, sr), 6.0, sr)
    return out / (float(np.max(np.abs(out))) or 1.0) * (0.45 + 0.55 * size)


def synth_squash(size: float, seed: int = 0, sr: int = SR) -> np.ndarray:
    """A ball crushed: a short downward SQUELCH (air out of a squashed rubber
    ball, ~980 -> 250 Hz) with a soft pop edge and two tiny bright partials for
    definition at density."""
    size = float(np.clip(size, 0.0, 1.0))
    n = int((0.13 + 0.05 * size) * sr)
    t = np.arange(n, dtype=np.float32) / sr
    rng = np.random.default_rng(2500 + seed)
    f_hi, f_lo = 980.0 - 260.0 * size, 250.0 - 60.0 * size
    fr = f_lo + (f_hi - f_lo) * np.exp(-t / 0.022)
    squelch = (np.sin(2 * np.pi * np.cumsum(fr) / sr) * np.minimum(t / 0.003, 1.0)
               * np.exp(-t / (0.040 + 0.02 * size)))
    edge = _lp_noise(rng, n, 5)
    edge = np.diff(edge, prepend=edge[:1])
    edge /= float(np.max(np.abs(edge))) or 1.0
    edge = edge * np.minimum(t / 0.0008, 1.0) * np.exp(-t / 0.004)
    tw = ((np.sin(2 * np.pi * 2350.0 * t) + 0.6 * np.sin(2 * np.pi * 3700.0 * t + 1.0))
          * np.exp(-t / 0.010))
    out = _sfx_fade((1.0 * squelch + 0.55 * edge + 0.14 * tw).astype(np.float32), 6.0, sr)
    return out / (float(np.max(np.abs(out))) or 1.0) * (0.6 + 0.4 * size)


def synth_snap(seed: int = 0, sr: int = SR) -> np.ndarray:
    """The chain SNAPPING: a bright metallic ping, a crack and a low thunk."""
    n = int(0.45 * sr)
    t = np.arange(n, dtype=np.float32) / sr
    rng = np.random.default_rng(2600 + seed)
    ping = (np.sin(2 * np.pi * 2900.0 * t) * np.exp(-t / 0.07)
            + 0.7 * np.sin(2 * np.pi * 4450.0 * t + 0.3) * np.exp(-t / 0.05)
            + 0.5 * np.sin(2 * np.pi * 1310.0 * t + 1.9) * np.exp(-t / 0.12))
    crack = _lp_noise(rng, n, 6) * np.minimum(t / 0.001, 1.0) * np.exp(-t / 0.008)
    thunk = np.sin(2 * np.pi * 80.0 * t) * np.exp(-t / 0.07)
    out = _sfx_fade(_sfx_ramp((0.45 * ping + 0.6 * crack + 0.8 * thunk).astype(np.float32),
                              1.0, sr), 20.0, sr)
    return out / (float(np.max(np.abs(out))) or 1.0) * 0.9


class NoteBank:
    """Voice cache. velocity is bucketed to 4 levels to keep the cache small
    while letting hard hits sparkle and soft hits ring pure.

    Base channel voice is "marimba" (Luka's pick, 2026-07-04 — video 1's sound
    is the channel baseline). "glassharp" and "piano" are per-video variations.
    Names in SAMPLE_VOICES (e.g. "slime") play a WAV one-shot and ignore the
    note entirely — an SFX-on-hit cut rather than a melodic one."""

    def __init__(self, voice: str = "marimba", ring: float = 1.0):
        self.voice = voice
        self.ring = float(ring)
        self._cache: dict[tuple, np.ndarray] = {}
        self._foley: dict[tuple, np.ndarray] = {}
        self._pop: dict[tuple, np.ndarray] = {}
        self._zap: dict[tuple, np.ndarray] = {}
        self._sfx2: dict[tuple, np.ndarray] = {}

    def get(self, midi_note: int, velocity: float = 0.8) -> np.ndarray:
        midi_note = int(np.clip(midi_note, 36, 96))
        vb = int(np.clip(velocity, 0.0, 0.999) * 4)  # 4 velocity buckets
        if self.voice in SAMPLE_VOICES:
            # unpitched: one cached buffer, note ignored (see SAMPLE_VOICES)
            if "s" not in self._cache:
                self._cache["s"] = load_sample(SAMPLE_VOICES[self.voice])
            return self._cache["s"]
        key = (midi_note, vb if self.voice == "glassharp" else 0)
        if key not in self._cache:
            if self.voice == "glassharp":
                self._cache[key] = synth_glassharp(midi_note, (vb + 0.5) / 4)
            elif self.voice == "marimba":
                self._cache[key] = synth_plink(midi_note, ring=self.ring)
            elif self.voice == "piano":
                self._cache[key] = synth_piano(midi_note)
            elif self.voice == "void":
                self._cache[key] = synth_void(midi_note)
            else:
                raise ValueError(f"unknown voice {self.voice!r}")
        return self._cache[key]

    def foley(self, impulse: float, kind: str = "thump") -> np.ndarray:
        ib = int(np.clip(impulse, 0.0, 0.999) * 6)  # 6 strength buckets
        key = (kind, ib)
        if key not in self._foley:
            if kind == "glassbreak":
                self._foley[key] = synth_glassbreak((ib + 0.5) / 6, seed=ib)
            elif kind == "thump":
                self._foley[key] = synth_foley((ib + 0.5) / 6)
            else:
                raise ValueError(f"unknown foley kind {kind!r}")
        return self._foley[key]

    def pop(self, size: float, variant: int = 0,
            boom_w: float = None) -> np.ndarray:
        """Balloon pop, bucketed by size with a few seeded variants so a burst
        of them doesn't machine-gun the identical waveform."""
        sb = int(np.clip(size, 0.0, 0.999) * 6)     # 6 size buckets
        vb = int(variant) % 4
        bw = 0.75 if boom_w is None else float(boom_w)
        key = (sb, vb, bw)
        if key not in self._pop:
            self._pop[key] = synth_balloon_pop((sb + 0.5) / 6, seed=sb * 4 + vb,
                                               boom_w=bw)
        return self._pop[key]

    def glass(self, size: float, variant: int = 0) -> np.ndarray:
        """Glass shatter, bucketed + varied exactly like pop() — the per-event
        accent for scenes where the burst IS glass (shatter), as opposed to the
        all-or-nothing foley_kind='glassbreak' layer that plays on every event."""
        sb = int(np.clip(size, 0.0, 0.999) * 6)
        vb = int(variant) % 4
        key = ("g", sb, vb)
        if key not in self._pop:
            self._pop[key] = synth_glassbreak((sb + 0.5) / 6, seed=sb * 4 + vb)
        return self._pop[key]

    def rubble(self, size: float, variant: int = 0) -> np.ndarray:
        """Concrete break — glass()'s sibling for the concrete material. Same
        bucketing/variant scheme so a burst of them doesn't machine-gun."""
        sb = int(np.clip(size, 0.0, 0.999) * 6)
        vb = int(variant) % 4
        key = ("c", sb, vb)
        if key not in self._pop:
            self._pop[key] = synth_concretebreak((sb + 0.5) / 6,
                                                 seed=sb * 4 + vb)
        return self._pop[key]

    def steam(self, size: float, variant: int = 0) -> np.ndarray:
        """Steam hiss — the quench accent for the FIRE material, bucketed and
        varied exactly like pop()/glass()/rubble()."""
        sb = int(np.clip(size, 0.0, 0.999) * 6)
        vb = int(variant) % 4
        key = ("st", sb, vb)
        if key not in self._pop:
            self._pop[key] = synth_steam((sb + 0.5) / 6, seed=sb * 4 + vb)
        return self._pop[key]

    def splash(self, size: float, variant: int = 0) -> np.ndarray:
        """Water entry — bucketed and varied exactly like pop()/glass()."""
        sb = int(np.clip(size, 0.0, 0.999) * 6)
        vb = int(variant) % 4
        key = ("sp", sb, vb)
        if key not in self._pop:
            self._pop[key] = synth_splash((sb + 0.5) / 6, seed=sb * 4 + vb)
        return self._pop[key]

    def zap(self, size: float, variant: int = 0) -> np.ndarray:
        """Laser zap, bucketed + varied exactly like pop() (six pitches x four
        noise-tick variants)."""
        sb = int(np.clip(size, 0.0, 0.999) * 6)
        vb = int(variant) % 4
        key = (sb, vb)
        if key not in self._zap:
            self._zap[key] = synth_zap((sb + 0.5) / 6, seed=sb * 4 + vb)
        return self._zap[key]

    def bounce(self, size: float, variant: int = 0) -> np.ndarray:
        """Rubber-ball tock, six pitch buckets x four click variants."""
        key = ("bounce", int(np.clip(size, 0.0, 0.999) * 6), int(variant) % 4)
        if key not in self._sfx2:
            self._sfx2[key] = synth_bounce((key[1] + 0.5) / 6, seed=key[1] * 4 + key[2])
        return self._sfx2[key]

    def vapor(self, size: float, variant: int = 0) -> np.ndarray:
        key = ("vapor", int(np.clip(size, 0.0, 0.999) * 6), int(variant) % 4)
        if key not in self._sfx2:
            self._sfx2[key] = synth_vaporise((key[1] + 0.5) / 6, seed=key[1] * 4 + key[2])
        return self._sfx2[key]

    def ignite(self, size: float, variant: int = 0) -> np.ndarray:
        key = ("ignite", int(np.clip(size, 0.0, 0.999) * 6), int(variant) % 4)
        if key not in self._sfx2:
            self._sfx2[key] = synth_ignite((key[1] + 0.5) / 6, seed=key[1] * 4 + key[2])
        return self._sfx2[key]

    def sweep(self, dur: float, variant: int = 0) -> np.ndarray:
        key = ("sweep", round(float(dur), 2), int(variant) % 4)
        if key not in self._sfx2:
            self._sfx2[key] = synth_laser_sweep(key[1], seed=key[2])
        return self._sfx2[key]

    def chomp(self, size: float, variant: int = 0) -> np.ndarray:
        """Pellet chomp (pacman edition) — bucketed like pop(); the variant's
        PARITY picks the sweep direction, so consecutive events alternate."""
        sb = int(np.clip(size, 0.0, 0.999) * 6)
        vb = int(variant) % 4
        key = ("ch", sb, vb)
        if key not in self._pop:
            self._pop[key] = synth_chomp((sb + 0.5) / 6, seed=sb * 4 + vb)
        return self._pop[key]

    # --- machine SFX (hydro_press) -----------------------------------------
    def servo(self, dur: float, up: bool = True) -> np.ndarray:
        db = int(round(dur * 20.0))              # 50ms duration buckets
        key = ("sv", db, bool(up))
        if key not in self._pop:
            self._pop[key] = synth_servo(db / 20.0, up)
        return self._pop[key]

    def clank(self, size: float, variant: int = 0) -> np.ndarray:
        sb = int(np.clip(size, 0.0, 0.999) * 6)
        vb = int(variant) % 4
        key = ("ck", sb, vb)
        if key not in self._pop:
            self._pop[key] = synth_clank((sb + 0.5) / 6, seed=sb * 4 + vb)
        return self._pop[key]

    def hiss(self, size: float, variant: int = 0) -> np.ndarray:
        sb = int(np.clip(size, 0.0, 0.999) * 6)
        vb = int(variant) % 4
        key = ("hs", sb, vb)
        if key not in self._pop:
            self._pop[key] = synth_hiss((sb + 0.5) / 6, seed=sb * 4 + vb)
        return self._pop[key]

    def bounce(self, size: float, variant: int = 0) -> np.ndarray:
        sb = int(np.clip(size, 0.0, 0.999) * 6)
        vb = int(variant) % 4
        key = ("bn", sb, vb)
        if key not in self._pop:
            self._pop[key] = synth_bounce((sb + 0.5) / 6, seed=sb * 4 + vb)
        return self._pop[key]

    def fuse(self, dur: float, variant: int = 0) -> np.ndarray:
        key = ("fuse", int(round(float(np.clip(dur, 0.06, 2.0)) / 0.02)), int(variant) % 4)
        if key not in self._sfx2:
            self._sfx2[key] = synth_fuse(key[1] * 0.02, seed=key[2])
        return self._sfx2[key]

    def cannon(self, size: float, variant: int = 0) -> np.ndarray:
        key = ("cannon", int(np.clip(size, 0.0, 0.999) * 6), int(variant) % 4)
        if key not in self._sfx2:
            self._sfx2[key] = synth_cannon((key[1] + 0.5) / 6 if size < 0.999 else 1.0,
                                           seed=key[1] * 4 + key[2])
        return self._sfx2[key]

    def blast(self, size: float, variant: int = 0) -> np.ndarray:
        key = ("blast", int(np.clip(size, 0.0, 0.999) * 6), int(variant) % 4)
        if key not in self._sfx2:
            self._sfx2[key] = synth_explosion((key[1] + 0.5) / 6 if size < 0.999 else 1.0,
                                              seed=key[1] * 4 + key[2])
        return self._sfx2[key]

    def wakka(self, midi_note: int, variant: int = 0) -> np.ndarray:
        """Pitched chomp; the variant's PARITY picks the sweep direction.
        The game's own wakka (sfx/pacman/wakka.wav), if present, replaces
        it — unpitched, so the note is ignored."""
        if "wk_s" not in self._pop:
            self._pop["wk_s"] = pac_sample("wakka")
        if self._pop["wk_s"] is not None:
            return self._pop["wk_s"]
        key = ("wk", int(midi_note), int(variant) % 2)
        if key not in self._pop:
            self._pop[key] = synth_wakka(int(midi_note), bool(int(variant) % 2))
        return self._pop[key]

    def gulp(self, variant: int = 0) -> np.ndarray:
        """A ghost eaten (pacman edition), three seeded variants — or the
        game's own recording when present."""
        if "gu_s" not in self._pop:
            self._pop["gu_s"] = pac_sample("gulp")
        if self._pop["gu_s"] is not None:
            return self._pop["gu_s"]
        key = ("gu", int(variant) % 3)
        if key not in self._pop:
            self._pop[key] = synth_gulp(seed=int(variant) % 3)
        return self._pop[key]

    def pacdeath(self) -> np.ndarray:
        if "pd" not in self._pop:
            self._pop["pd"] = pac_sample("death")
            if self._pop["pd"] is None:
                self._pop["pd"] = synth_pacdeath()
        return self._pop["pd"]

    def power(self) -> np.ndarray:
        if "pw" not in self._pop:
            self._pop["pw"] = pac_sample("power")
            if self._pop["pw"] is None:
                self._pop["pw"] = synth_power()
        return self._pop["pw"]

    # --- drop-hammer SFX (drop_hammer) ---------------------------------------
    def ratchet(self, size: float, variant: int = 0) -> np.ndarray:
        key = ("rt", int(np.clip(size, 0.0, 0.999) * 6), int(variant) % 4)
        if key not in self._sfx2:
            self._sfx2[key] = synth_ratchet((key[1] + 0.5) / 6, seed=key[1] * 4 + key[2])
        return self._sfx2[key]

    def latch(self, variant: int = 0) -> np.ndarray:
        key = ("lt", int(variant) % 3)
        if key not in self._sfx2:
            self._sfx2[key] = synth_latch(seed=key[1])
        return self._sfx2[key]

    def slam(self, size: float, crunch: float = 0.0, ring: float = 1.0,
             variant: int = 0) -> np.ndarray:
        """Six size buckets x four crunch buckets x three ring buckets x two
        variants — a jam of identical slams would machine-gun one waveform."""
        key = ("sl", int(np.clip(size, 0.0, 0.999) * 6),
               int(np.clip(crunch, 0.0, 1.0) * 3.999), int(np.clip(ring, 0.0, 1.0) * 2.999),
               int(variant) % 2)
        if key not in self._sfx2:
            self._sfx2[key] = synth_slam((key[1] + 0.5) / 6, key[2] / 3.0, (key[3] + 1) / 3.0,
                                         seed=key[1] * 8 + key[4])
        return self._sfx2[key]

    def pok(self, size: float, variant: int = 0) -> np.ndarray:
        key = ("pk", int(np.clip(size, 0.0, 0.999) * 6), int(variant) % 4)
        if key not in self._sfx2:
            self._sfx2[key] = synth_pok((key[1] + 0.5) / 6, seed=key[1] * 4 + key[2])
        return self._sfx2[key]

    def squash(self, size: float, variant: int = 0) -> np.ndarray:
        key = ("sq", int(np.clip(size, 0.0, 0.999) * 6), int(variant) % 4)
        if key not in self._sfx2:
            self._sfx2[key] = synth_squash((key[1] + 0.5) / 6, seed=key[1] * 4 + key[2])
        return self._sfx2[key]

    def snap(self, variant: int = 0) -> np.ndarray:
        key = ("sn", int(variant) % 2)
        if key not in self._sfx2:
            self._sfx2[key] = synth_snap(seed=key[1])
        return self._sfx2[key]


# --- note assignment ---------------------------------------------------------

class ScaleWalker:
    """Maps event index -> midi note along a scale pattern.

    pattern 'updown': zigzag over `span` scale degrees (musical, ref2/ref6
    style); 'up': ascending ladder that wraps.
    """

    def __init__(self, root_midi=63, scale=PENTA_MINOR, span=10, pattern="updown"):
        degrees = [root_midi + 12 * (d // len(scale)) + scale[d % len(scale)]
                   for d in range(span)]
        if pattern == "updown":
            self.seq = degrees + degrees[-2:0:-1]
        else:
            self.seq = degrees
        self.i = 0

    def next(self) -> int:
        note = self.seq[self.i % len(self.seq)]
        self.i += 1
        return note


class MelodyAssigner:
    """Each event consumes the next note of a (public-domain!) MIDI melody."""

    def __init__(self, midi_path):
        import mido
        notes = []
        for msg in mido.MidiFile(str(midi_path)):
            if msg.type == "note_on" and msg.velocity > 0:
                notes.append(msg.note)
        if not notes:
            raise ValueError(f"no notes in {midi_path}")
        self.notes = notes
        self.i = 0

    def next(self) -> int:
        note = self.notes[self.i % len(self.notes)]
        self.i += 1
        return note


# --- public-domain melody hook -----------------------------------------------
#
# The "I know that tune" hook (Luka, 2026-07-08): some competitor channels play
# recognizable soundtrack melodies note-by-note on the collision voice. Their
# examples (Megalovania, Stranger Things) are COPYRIGHTED — the note sequence
# itself is the protected part, and recognizability is exactly what a manual
# claim keys on, so length ("just a few notes") is no shield. We get the same
# hook with ZERO risk by using PUBLIC-DOMAIN melodies only. Each entry is a raw
# MIDI note list; MelodyWalker cycles it one note per collision, so a scene that
# ACCELERATES (grow_ball, etc.) automatically plays the tune faster and faster —
# which is the whole "it speeds up" appeal of the format.
#
# ADD ONLY genuinely public-domain melodies here (classical / trad-folk whose
# underlying COMPOSITION is PD — a modern arrangement of a folk tune may not be).
_PD_RESERVE = {  # LOCKED: see MELODIES below and docs/compliance.md
    # Grieg, "In the Hall of the Mountain King" (1875, PD). The tiptoe theme in
    # B minor, then restated up a minor 3rd — its own built-in accelerando fits
    # this channel's "event rate must accelerate" rule for free.
    "mountain_king": [
        59, 61, 62, 64, 66, 62, 66, 65, 62, 65, 64, 61, 64,   # B minor statement
        62, 64, 65, 67, 69, 65, 69, 68, 65, 68, 67, 64, 67,   # same, up a minor 3rd
    ],
    # Beethoven, "Ode to Joy" (1824, PD) — instantly recognizable, major key.
    "ode_to_joy": [
        64, 64, 65, 67, 67, 65, 64, 62, 60, 60, 62, 64, 64, 62, 62,
        64, 64, 65, 67, 67, 65, 64, 62, 60, 60, 62, 64, 62, 60, 60,
    ],
    # "Korobeiniki" — the Tetris theme, a PD 19th-c. Russian folk melody.
    "korobeiniki": [
        76, 71, 72, 74, 72, 71, 69, 69, 72, 76, 74, 72, 71, 71, 72, 74, 76, 72, 69, 69,
        74, 77, 81, 79, 77, 76, 72, 76, 74, 72, 71, 71, 72, 74, 76, 72, 69, 69,
    ],
    # Beethoven, "Für Elise" (1810, PD) — one of the most recognizable piano
    # motifs; the E–D# oscillation opening reads instantly even at one note
    # per collision.
    "fur_elise": [
        76, 75, 76, 75, 76, 71, 74, 72, 69,   # E D# E D# E B D C A
        60, 64, 69, 71,                        # C E A B
        64, 68, 71, 72,                        # E G# B C
        64, 76, 75, 76, 75, 76, 71, 74, 72, 69,
        60, 64, 69, 71,
        64, 72, 71, 69,                        # E C B A
    ],
    # J. Strauss II, "The Blue Danube" (1866, PD) — the rising D–F#–A waltz
    # arpeggio is unmistakable; strong pitch contour survives irregular timing.
    "blue_danube": [
        62, 66, 69, 69, 69, 71, 71, 69, 66, 66,   # D F# A A A  B B  A  F# F#
        62, 66, 69, 69, 69, 71, 71, 69, 66, 66,
        66, 69, 74, 74, 74, 76, 76, 74, 71, 71,   # rises a phrase
    ],
    # Scott Joplin, "The Entertainer" (1902, PD) — ragtime; the bouncing
    # C–E–C–E figure and descending run are the signature.
    "entertainer": [
        62, 63, 64,                            # D D# E (chromatic pickup)
        72, 64, 72, 64, 72,                    # C E C E C (the bounce)
        60, 62, 64, 67, 64, 62, 60,            # C D E G E D C
        62, 62, 62, 64, 65, 64, 62, 60,        # D D D E F E D C
        60, 62, 64, 67, 64, 62, 60,
    ],
    # Trad. / Mozart K.265 theme, "Twinkle Twinkle Little Star" (PD) —
    # maximally recognizable, simple major arch.
    "twinkle": [60, 60, 67, 67, 69, 69, 67, 65, 65, 64, 64, 62, 62, 60],
    # Trad. "When the Saints Go Marching In" (PD) — rising C–E–F–G fanfare.
    "when_the_saints": [
        60, 64, 65, 67, 60, 64, 65, 67, 60, 64, 65, 67, 64, 60, 64, 62, 60],
    # Pachelbel, "Canon in D" (c.1680, PD) — the descending melodic line.
    "pachelbel_canon": [
        66, 64, 62, 61, 59, 57, 59, 61, 62, 61, 59, 57, 55, 54, 52, 54],
    # Trad. English "Greensleeves" (16th c., PD) — minor-key, instantly known.
    "greensleeves": [57, 60, 62, 64, 65, 64, 62, 59, 55, 57, 59, 60, 57, 57, 56, 57],
    # Trad. Mexican "La Cucaracha" (PD) — the C–C–C–F–A dance figure.
    "la_cucaracha": [60, 60, 60, 65, 69, 60, 60, 60, 65, 69, 65, 64, 62, 60],
    # Mozart, "Eine kleine Nachtmusik" (1787, PD) — the rising G–D–G–D arpeggio
    # opening; classy and instantly placed.
    "eine_kleine": [67, 62, 67, 62, 67, 71, 74, 67, 62, 57, 62, 57, 62, 66, 69, 62],
    # Mozart, Rondo alla Turca "Turkish March" (1783, PD) — the A-minor scamper.
    "turkish_march": [71, 69, 68, 69, 72, 74, 72, 71, 72, 76, 77, 76, 75, 76, 81, 72, 74, 76, 72],
    # J. Pierpont, "Jingle Bells" (1857, PD) — the E-E-E chorus + verse.
    "jingle_bells": [64, 64, 64, 64, 64, 64, 64, 67, 60, 62, 64,
                     65, 65, 65, 65, 65, 64, 64, 64, 64, 62, 62, 64, 67],
    # Trad. "Frère Jacques" (PD) — round; simple stepwise phrases.
    "frere_jacques": [60, 62, 64, 60, 60, 62, 64, 60, 64, 65, 67, 64, 65, 67,
                      67, 69, 67, 65, 64, 60, 67, 69, 67, 65, 64, 60, 60, 55, 60, 60, 55, 60],
    # Trad. "Row, Row, Row Your Boat" (PD).
    "row_your_boat": [60, 60, 60, 62, 64, 64, 62, 64, 65, 67,
                      72, 72, 72, 67, 67, 67, 64, 64, 64, 60, 60, 60, 67, 65, 64, 62, 60],
    # Trad. "Mary Had a Little Lamb" (PD).
    "mary_lamb": [64, 62, 60, 62, 64, 64, 64, 62, 62, 62, 64, 67, 67,
                  64, 62, 60, 62, 64, 64, 64, 64, 62, 62, 64, 62, 60],
    # Trad. "London Bridge Is Falling Down" (PD).
    "london_bridge": [67, 69, 67, 65, 64, 65, 67, 62, 64, 65, 64, 65, 67,
                      67, 69, 67, 65, 64, 65, 67, 62, 67, 64, 60],
    # Beethoven, Symphony No. 5 opening (1808, PD) — the "da-da-da-DUM" motif.
    "beethoven_5": [67, 67, 67, 63, 65, 65, 65, 62, 67, 67, 67, 63, 65, 65, 65, 62],
    # Handel (tune "Antioch"), "Joy to the World" (PD) — a descending major scale.
    "joy_to_world": [72, 71, 69, 67, 65, 64, 62, 60, 67, 67, 69, 69, 71, 72],
    # F. Gruber, "Silent Night" (1818, PD; Gruber d.1863).
    "silent_night": [67, 69, 67, 64, 67, 69, 67, 64, 74, 74, 71, 72, 72, 67],
    # Brahms, "Wiegenlied / Lullaby" (1868, PD; Brahms d.1897).
    "brahms_lullaby": [64, 64, 67, 64, 64, 67, 64, 67, 72, 71, 69, 69, 67],
    # Bizet, "Habanera" from Carmen (1875, PD) — the chromatic descent.
    "habanera": [74, 73, 72, 71, 70, 69, 69, 70, 71, 72, 74, 73, 72, 71, 70, 69],
    # J.S. Bach, Toccata and Fugue in D minor opening (PD; Bach d.1750).
    "bach_toccata": [69, 67, 69, 62, 60, 58, 57, 55, 53, 52, 50, 62],
    # Wagner, "Bridal Chorus / Here Comes the Bride", Lohengrin (1850, PD;
    # Wagner d.1883).
    "bridal_chorus": [60, 65, 65, 65, 64, 65, 67, 65, 65, 67, 69, 69, 67, 65, 67, 72],
    # Trad. Irish "Londonderry Air / Danny Boy" (PD).
    "danny_boy": [60, 65, 67, 69, 72, 71, 69, 65, 67, 69, 65, 62, 60],
    # Trad. Scottish "Auld Lang Syne" (PD).
    "auld_lang_syne": [60, 65, 65, 65, 69, 67, 65, 67, 69, 65, 65, 69, 72, 74],
    # Vivaldi, "Spring" from The Four Seasons (1725, PD; Vivaldi d.1741).
    "spring_vivaldi": [64, 68, 68, 68, 66, 64, 71, 71, 70, 71, 70, 71],
    # Rossini, William Tell Overture finale (1829, PD; Rossini d.1868).
    "william_tell": [67, 67, 67, 67, 67, 67, 67, 72, 76, 67, 67, 67, 67, 67, 67, 67, 72, 76],
    # Trad. "For He's a Jolly Good Fellow / Marlbrough" (PD).
    "jolly_good_fellow": [60, 65, 65, 65, 67, 65, 64, 60, 60, 62, 64, 62, 60],
    # Chopin, Marche funèbre, Piano Sonata No. 2 Op. 35 iii (1839, PD; Chopin
    # d.1849) — THE funeral tune, and the one the "coffin dance" meme is
    # actually about. Added as the PD answer to a request for "Astronomia",
    # which is Tony Igy / Vicetone (2010) and firmly in copyright. B-flat minor,
    # tolling repeated tonic then the D-flat-C-C-B-flat sigh; the descending
    # B-flat-A-flat-G-flat-F tail is the half everyone hums. Doubles as a
    # creepy-ending voice (CLAUDE.md's climax rule) without touching the mixer.
    "funeral_march": [
        58, 58, 58, 58, 58, 61, 60, 60, 58, 58,      # Bb tolling -> Db C C Bb
        61, 61, 61, 61, 65, 63, 63, 61, 61,          # the Db answer -> F Eb
        70, 68, 66, 65, 65, 61, 58,                  # Bb Ab Gb F F Db Bb
    ],
    # "Ievan polkka" — a TRADITIONAL Finnish polka (Savonian, 19th c.), so the
    # MELODY is PD; Eino Kettunen's 1928 words and Loituma's 1995 arrangement
    # are separate works and neither is used here (we play pitches, no lyrics,
    # no arrangement). D minor. The A PHRASE ONLY (bars 1-4 — the line everyone
    # hums), NOT the whole tune: the full 124-note engraving came round only
    # 1.3 times in a 164-bounce clip and Luka could not place it (2026-09-10).
    # 20 notes = ~8 cycles, the bank's normal range. See the CYCLES rule.
    # Caveat that a trim cannot fix: a POLKA's identity is its 2/4 drive, and
    # collision timing destroys rhythm (the william_tell failure mode) — this
    # tune has a ceiling here however it is cut.
    "ievan_polkka": [
        79, 81, 81, 79, 77, 77, 76, 72, 72, 72, 76, 79, 79, 79, 77, 76, 77, 74, 74, 77,
    ],
}


# YT2_D_PLINKO POLICY (copyright is critical here): the rotating melody bank is
# EMPTY. Even a public-domain composition can draw a Content ID claim (other
# uploads of the same tune are registered), and a recognisable tune is exactly
# what a claim keys on. The channel sound is an ORIGINAL pentatonic scale played
# by our own synthesis (pitch = where the ball hit). The PD tunes are kept in
# _PD_RESERVE for reference only; moving one back needs the owner to say so.
MELODIES = {}


# Benched — verified PD, but less globally recognizable than the 30 in MELODIES
# (more regional, or not a hummable "I know that tune" hook), so kept OUT of
# rotation (Luka, 2026-07-12: trim the bank to the strongest recognizers).
# Preserved here, not deleted, so any can be promoted back into MELODIES.
MELODIES_BENCH = {
    "oh_susanna": [60, 62, 64, 67, 67, 69, 67, 64, 60, 62, 64, 64, 62, 60, 62, 60],
    "camptown_races": [67, 67, 64, 67, 69, 67, 64, 64, 62, 64,
                       67, 67, 64, 67, 69, 67, 64, 62, 64, 60],
    "yankee_doodle": [60, 60, 62, 64, 60, 64, 62, 60, 60, 62, 64, 60, 59,
                      60, 60, 62, 64, 65, 64, 62, 60, 59, 55, 57, 59, 60, 60],
    "home_on_the_range": [67, 60, 64, 64, 64, 62, 60, 55, 57, 62, 62, 60],
    "this_old_man": [67, 64, 67, 67, 64, 67, 69, 67, 65, 64, 62, 64, 65],
    "new_world": [64, 67, 67, 64, 62, 60, 62, 64, 67, 64, 62, 60, 62, 64, 62, 55],
    "minuet_in_g": [74, 67, 69, 71, 72, 74, 67, 67, 76, 72, 74, 76, 78, 79, 67, 67],
    "hallelujah": [69, 69, 74, 74, 69, 74, 76, 78, 78, 78, 78, 76, 74],
    "scarborough_fair": [57, 57, 64, 64, 66, 64, 62, 60, 62, 60, 59, 57, 55, 57],
    "pop_goes_weasel": [60, 60, 62, 62, 64, 67, 64, 60, 60, 62, 64, 60, 62, 64, 65, 64, 62, 60],
}


# User-supplied melodies of UNVERIFIED provenance — NOT public domain by
# default, so this bank is opt-in-by-name ONLY and is never touched by
# pick_melody()'s auto-rotation (that rotation's whole safety guarantee is
# that MELODIES is 100% verified-PD; mixing in an unverified track there
# would silently expose every future auto-rotated video to it). A scene must
# request one of these by its exact key via `--melody <name>`; it will never
# be picked for you. The channel owner confirms the rights before adding one.
MELODIES_CUSTOM = {}


def melody_notes(name: str):
    """Look up a melody's note list, checking the verified-PD bank first,
    then the unverified custom bank. Raises KeyError with the combined
    choice list if not found in either."""
    if name in MELODIES:
        return MELODIES[name]
    if name in MELODIES_CUSTOM:
        return MELODIES_CUSTOM[name]
    choices = ", ".join(list(MELODIES) + list(MELODIES_CUSTOM))
    raise KeyError(f"unknown melody {name!r}; choices: {choices}")


def is_known_melody(name: str) -> bool:
    return name in MELODIES or name in MELODIES_CUSTOM


def pick_melody(n: int) -> str:
    """Rotate through the PD bank so CONSECUTIVE videos get DIFFERENT tunes
    (Luka, 2026-07-11: don't spam the same music a few videos in a row — the
    curated bank stays, since it's the public-domain guarantee, but selection
    auto-cycles it instead of me manually defaulting to the same one).

    Keyed off the render seed, NOT wall-clock or mutable state, so a given
    command still reproduces the same video bit-for-bit (channel determinism
    rule). Add tunes to MELODIES and this rotates over them automatically;
    consecutive seeds (0,1,2,... as a series sweep uses) map to distinct tunes
    as long as the run is shorter than the bank."""
    keys = list(MELODIES)
    if not keys:
        raise RuntimeError(
            "melody bank is locked (copyright policy, docs/compliance.md): use "
            "ScaleWalker / kit.penta_note for original pitch, not a tune")
    return keys[int(n) % len(keys)]


class MelodyWalker:
    """Cycles a fixed note list (a PD MELODIES entry), one note per event.

    List-based sibling of MelodyAssigner — no MIDI file needed, so melodies live
    in code and stay deterministic. Same interface as ScaleWalker (.next())."""

    def __init__(self, notes):
        if not notes:
            raise ValueError("empty melody")
        self.notes = list(notes)
        self.i = 0

    def next(self) -> int:
        note = self.notes[self.i % len(self.notes)]
        self.i += 1
        return note

    def peek(self) -> int:
        """The note next() would return, WITHOUT advancing (an undertone
        that doubles the tune's current pitch must not eat a note of it)."""
        return self.notes[self.i % len(self.notes)]


# --- mixdown / master --------------------------------------------------------

MUSIC_DIR = Path(__file__).resolve().parent.parent / "sfx" / "music"

# --- MUSIC BEDS ---------------------------------------------------------------
#
# The third member of the custom-bank family, alongside `MELODIES_CUSTOM` here
# and `score.SCORES_CUSTOM`: opt-in only, reachable by EXACT name, never picked
# automatically and never listed in a rotation. A bed is a finished track cropped
# to a whole number of bars AND a whole number of video frames by
# `tools/beat_crop.py`, so a scene can lay its events on `frames / (60 * beats)`
# and the clip still wrap-loops.
MUSIC_CUSTOM = {}

def is_known_music(name) -> bool:
    return name in MUSIC_CUSTOM


def music_clip(name):
    """-> (stereo float32 (n, 2) at SR, meta dict from the crop sidecar).

    `n` is exactly `frames / 60 * SR`, which is what lets a scene add the bed to
    a mixed event buffer sample-for-sample with no resampling at delivery time.
    """
    import json
    import soundfile as sf
    if name not in MUSIC_CUSTOM:
        raise KeyError(f"unknown music bed {name!r}; add it to MUSIC_CUSTOM "
                       f"(choices: {', '.join(MUSIC_CUSTOM)})")
    stem = MUSIC_CUSTOM[name]
    meta = json.loads((MUSIC_DIR / f"{stem}.json").read_text())
    x, sr = sf.read(str(MUSIC_DIR / f"{stem}.wav"), always_2d=True,
                    dtype="float32")
    if sr != SR:
        raise ValueError(f"music bed {stem} is {sr} Hz, mixer is {SR}")
    if x.shape[1] == 1:
        x = np.repeat(x, 2, axis=1)
    want = int(round(meta["frames"] / float(meta["fps"]) * SR))
    if abs(len(x) - want) > 1:
        raise ValueError(f"music bed {stem}: {len(x)} samples, expected {want}")
    return x[:want], meta


def mix_events(events, duration_s, width_px=1080.0, sr: int = SR,
               voice: str = "marimba", foley_gain: float = 0.0,
               foley_kind: str = "thump", pop_gain: float = 0.9,
               glass_gain: float = 0.9,
               rubble_gain: float = 1.0, pop_boom: float = None,
               steam_gain: float = 0.9, splash_gain: float = 0.9,
               zap_gain: float = 0.8, bounce_gain: float = 0.8,
               vapor_gain: float = 0.7, sweep_gain: float = 0.6,
               ring: float = 1.0) -> np.ndarray:
    """events: [{t, note, gain, x, note_gain?, pop?, glass?, rubble?, steam?,
    splash?}]
    -> stereo float32.

    Each event = a note, plus (optionally, foley_gain>0) a foley layer scaled by
    impact — foley_kind 'thump' (soft body knock) or 'glassbreak' (shatter, the
    break_rings signature). Base channel sound is marimba with foley off; foley
    and the glassharp voice are opt-in per-video variations.

    An event carrying a ``pop`` key (0..1 = how big the thing that burst was)
    also gets a balloon POP layer at ``pop_gain``. Unlike foley this is
    per-event, so a scene can sound a pop on the few events that ARE one while
    the rest of the stream stays musical. A ``glass`` key works identically at
    ``glass_gain`` but voices a glass SHATTER (the shatter scene's signature),
    and a ``rubble`` key voices a CONCRETE break at ``rubble_gain`` (the same
    scene's concrete material).
    Applies 10ms inter-onset thinning, density ducking (1/sqrt of events in a
    +-0.5s window), and constant-power panning from x position.
    """
    bank = NoteBank(voice, ring=ring)
    n = int((duration_s + 2.0) * sr)  # +2s tail for the last note's ring-out
    buf = np.zeros((n, 2), dtype=np.float32)

    events = sorted(events, key=lambda e: e["t"])
    times = np.array([e["t"] for e in events], dtype=np.float64)

    last_t = -1.0
    for idx, e in enumerate(events):
        if e["t"] - last_t < 0.010:
            continue
        last_t = e["t"]
        density = int(np.searchsorted(times, e["t"] + 0.5)
                      - np.searchsorted(times, e["t"] - 0.5))
        duck = 1.0 / math.sqrt(max(density, 1))
        gain = float(np.clip(e.get("gain", 0.7), 0.15, 1.0)) ** 0.7 * duck
        pan = float(np.clip(e.get("x", width_px / 2) / width_px, 0.0, 1.0))
        left = math.cos(pan * math.pi / 2) * gain
        right = math.sin(pan * math.pi / 2) * gain

        raw = float(np.clip(e.get("gain", 0.7), 0.0, 1.0))
        i0 = int(e["t"] * sr)
        if i0 >= n:
            continue
        # `note_gain` scales ONLY the pitched layer, so an event can be pure SFX
        # (note_gain 0 + a pop/glass/rubble key) while its neighbours in the same
        # stream stay musical. Needed because a scene whose loudest, most
        # frequent event is always the SAME event has no business pitching it
        # (CLAUDE.md's one-note rule) — but its quieter, more varied events still
        # carry the melody. Absent key = 1.0 = exactly the old arithmetic.
        ng = float(e.get("note_gain", 1.0))
        layers = [(bank.get(e["note"], raw), ng)] if ng > 0.0 else []
        if foley_gain > 0:
            layers.append((bank.foley(raw, foley_kind), foley_gain))
        if "pop" in e:
            # PER-EVENT balloon pop (foley_gain/foley_kind are all-or-nothing;
            # this fires only on the events that carry a "pop" size). It takes
            # only the SQUARE ROOT of the density duck: a pop is the rare accent
            # the whole scene is named for, and the full 1/sqrt(density) duck
            # would bury it under its own accompaniment at the climax. Sqrt, not
            # none — an undicked layer would make a dense passage LOUDER, which
            # is the trap the duck exists to prevent.
            # (left/right already carry the full duck, so dividing by sqrt(duck)
            # leaves exactly sqrt(duck) on this layer)
            layers.append((bank.pop(float(e["pop"]), idx, pop_boom),
                           pop_gain / math.sqrt(max(duck, 1e-6))))
        if "glass" in e:
            # same sqrt-of-the-duck treatment as the pop layer, same reason:
            # the shatter is the rare accent the scene is named for.
            layers.append((bank.glass(float(e["glass"]), idx),
                           glass_gain / math.sqrt(max(duck, 1e-6))))
        if "rubble" in e:
            # concrete sibling of the glass layer, same sqrt-of-the-duck rule
            layers.append((bank.rubble(float(e["rubble"]), idx),
                           rubble_gain / math.sqrt(max(duck, 1e-6))))
        if "steam" in e:
            # steam sibling of the glass layer, same sqrt-of-the-duck rule
            layers.append((bank.steam(float(e["steam"]), idx),
                           steam_gain / math.sqrt(max(duck, 1e-6))))
        if "splash" in e:
            # water-entry sibling of the glass layer, same sqrt-of-the-duck rule
            layers.append((bank.splash(float(e["splash"]), idx),
                           splash_gain / math.sqrt(max(duck, 1e-6))))
        if "bounce" in e:
            # rubber-ball tock (laser_sweep), fully ducked like a note: it is
            # the dense stream, not the accent
            layers.append((bank.bounce(float(e["bounce"]), idx), bounce_gain))
        if "vapor" in e:
            layers.append((bank.vapor(float(e["vapor"]), idx),
                           vapor_gain / math.sqrt(max(duck, 1e-6))))
        if "ignite" in e:
            # a flame catching (steam_split's relight): the accent for the
            # loop move, same sqrt-of-the-duck rule as the pop layer
            layers.append((bank.ignite(float(e["ignite"]), idx),
                           0.9 / math.sqrt(max(duck, 1e-6))))
        if "sweep" in e:
            # the sweep is ONE onset lasting up to seconds; the density window
            # around it is full of kills it caused, so it takes the sqrt duck
            layers.append((bank.sweep(float(e["sweep"]), idx),
                           sweep_gain / math.sqrt(max(duck, 1e-6))))
        if "zap" in e:
            # laser zap (laser_hunt): same sqrt-of-the-duck rule as the pop
            layers.append((bank.zap(float(e["zap"]), idx),
                           zap_gain / math.sqrt(max(duck, 1e-6))))
        if "chomp" in e:
            # pellet chomp (pacman edition): same sqrt-of-the-duck rule; the
            # event index alternates the sweep direction ("wa-ka")
            layers.append((bank.chomp(float(e["chomp"]), idx),
                           0.85 / math.sqrt(max(duck, 1e-6))))
        if "wakka" in e:
            # the PITCHED chomp: pellets playing the tune (pacman mix B)
            layers.append((bank.wakka(e["note"], idx),
                           float(e["wakka"]) / math.sqrt(max(duck, 1e-6))))
        if "gulp" in e:
            layers.append((bank.gulp(idx), 0.9 / math.sqrt(max(duck, 1e-6))))
        # machine SFX (hydro_press): same sqrt-of-the-duck rule as the pop
        # layer — each is the accent for ONE kind of event, not a bed
        if "servo" in e:
            layers.append((bank.servo(float(e["servo"]), bool(e.get("up", 1))),
                           float(e.get("servo_gain", 0.7)) / math.sqrt(max(duck, 1e-6))))
        if "clank" in e:
            layers.append((bank.clank(float(e["clank"]), idx),
                           1.0 / math.sqrt(max(duck, 1e-6))))
        if "hiss" in e:
            layers.append((bank.hiss(float(e["hiss"]), idx),
                           0.6 / math.sqrt(max(duck, 1e-6))))
        if "bounce" in e:
            layers.append((bank.bounce(float(e["bounce"]), idx),
                           0.8 / math.sqrt(max(duck, 1e-6))))
        # cannon_box: fuse sizzle / cannon boom / impact explosion, all with
        # the pop layer's sqrt-of-the-duck rule (each is an accent, not a bed)
        if "fuse" in e:
            layers.append((bank.fuse(float(e["fuse"]), idx),
                           float(e.get("fuse_gain", 0.5)) / math.sqrt(max(duck, 1e-6))))
        if "cannon" in e:
            layers.append((bank.cannon(float(e["cannon"]), idx),
                           float(e.get("cannon_gain", 1.0)) / math.sqrt(max(duck, 1e-6))))
        if "blast" in e:
            layers.append((bank.blast(float(e["blast"]), idx),
                           float(e.get("blast_gain", 0.9)) / math.sqrt(max(duck, 1e-6))))
        # drop_hammer: the machine (ratchet / latch / slam / snap) and the crush
        # (squash) are ACCENTS — the pop layer's sqrt-of-the-duck rule; the
        # ball pok is the dense stream and takes the full duck, like a note
        if "ratchet" in e:
            layers.append((bank.ratchet(float(e["ratchet"]), idx),
                           float(e.get("ratchet_gain", 0.45)) / math.sqrt(max(duck, 1e-6))))
        if "latch" in e:
            layers.append((bank.latch(idx), float(e["latch"]) / math.sqrt(max(duck, 1e-6))))
        if "slam" in e:
            layers.append((bank.slam(float(e["slam"]), float(e.get("crunch", 0.0)),
                                     float(e.get("ring", 1.0)), idx),
                           float(e.get("slam_gain", 1.0)) / math.sqrt(max(duck, 1e-6))))
        if "pok" in e:
            layers.append((bank.pok(float(e["pok"]), idx), float(e.get("pok_gain", 0.8))))
        if "squash" in e:
            layers.append((bank.squash(float(e["squash"]), idx),
                           float(e.get("squash_gain", 0.85)) / math.sqrt(max(duck, 1e-6))))
        if "snap" in e:
            layers.append((bank.snap(idx), float(e["snap"]) / math.sqrt(max(duck, 1e-6))))
        if "pacdeath" in e:
            layers.append((bank.pacdeath(), float(e["pacdeath"])))
        if "power" in e:
            layers.append((bank.power(), float(e["power"])))
        for wave, g in layers:
            i1 = min(i0 + len(wave), n)
            seg = wave[: i1 - i0]
            buf[i0:i1, 0] += seg * left * g
            buf[i0:i1, 1] += seg * right * g
    return buf


def master(buf: np.ndarray, sr: int = SR, lufs_target=-14.0,
           peak_db: float = None, reverb: float = 1.0) -> np.ndarray:
    """peak_db: optional EXTRA limiter run before the loudness match, for scenes
    whose events are IMPULSES rather than notes.

    AAC cannot represent a sub-millisecond transient, so its reconstruction rings
    and OVERSHOOTS — and by far more than a pitched voice ever does. survivor's
    pop-per-kill soundtrack measured a float peak of -3.17 dBFS (inside the -3.0
    ceiling this function already guards) and came back from a 384k AAC encode at
    0.00 dBFS with clipped samples: a 3.2 dB overshoot, against ~1.4 dB for the
    scrub that set the -3.0 rule in the first place. Trimming cannot fix it,
    because level and LUFS move together 1:1; the CREST FACTOR has to come down.
    A limiter at -6 dB followed by the usual loudness match lands the same clip
    at -14.03 LUFS with 2.8 dB of AAC headroom and a per-5s RMS curve within
    0.3 dB of untouched — i.e. it costs nothing but the transient peaks.

    Default None keeps the old code path exactly, so every clip mastered before
    this stays bit-reproducible.
    """
    from pedalboard import Pedalboard, Reverb, Limiter
    import pyloudnorm

    # reverb: scales the WET share. 1.0 = the channel default. The room tail
    # is a second smear on top of the note ring — at a 100 ms event gap it
    # blurs consecutive notes into each other, so a scene chasing a LEGIBLE
    # tune turns it down. reverb=1.0 is bit-identical to the old path.
    wet = 0.14 * float(reverb)
    board = Pedalboard([
        Reverb(room_size=0.5, wet_level=wet, dry_level=1.0 - wet, width=0.9),
        Limiter(threshold_db=-3.0, release_ms=120.0),
    ])
    out = board(buf.T, sr).T  # pedalboard wants (channels, samples)

    meter = pyloudnorm.Meter(sr)
    loudness = meter.integrated_loudness(out.astype(np.float64))
    if math.isfinite(loudness):
        out = out * (10.0 ** ((lufs_target - loudness) / 20.0))
    if peak_db is not None:
        # AFTER the loudness match, never before. The raw mix arrives here well
        # under any sane threshold, so a limiter placed ahead of the match does
        # nothing at all and the match's makeup gain then lifts the untouched
        # transients straight back over the ceiling — measured: the peak came out
        # at 0.00 dBFS with clipped samples, i.e. the limiter may as well not
        # have been there. Limit, re-measure, re-drive, and END on the limiter so
        # the last thing that touched the signal is the one holding the ceiling.
        lim = Pedalboard([Limiter(threshold_db=float(peak_db), release_ms=60.0)])
        for _ in range(6):
            out = lim(out.T, sr).T
            l = meter.integrated_loudness(out.astype(np.float64))
            if not math.isfinite(l):
                break
            err = lufs_target - l
            if abs(err) < 0.1:
                break
            out = out * (10.0 ** (err / 20.0))
        out = lim(out.T, sr).T
    peak = float(np.max(np.abs(out))) or 1.0
    ceiling = 10.0 ** (-1.0 / 20.0)  # -1 dBTP approx
    if peak > ceiling:
        # Content that needs gain UP to reach the target lands here, and a plain
        # `out *= ceiling/peak` would UNDO the loudness match it just made — the
        # ceiling would cost LEVEL instead of dynamics. Every synth voice needs
        # gain DOWN (dense, always-ringing) so this branch never fired and the
        # bug stayed hidden until the first sparse SAMPLE voice: the slime cut
        # needed +3.4 dB, peaked 1.62x over the ceiling, and the scale-down
        # landed it at -18.2 LUFS against our -14.0 spec (2026-07-17).
        # Correct fix: drive into a true limiter, which caps peaks while letting
        # loudness come up, and solve for the drive that hits the target.
        for _ in range(6):
            lim = Pedalboard([Limiter(threshold_db=-1.0, release_ms=60.0)])
            test = lim(out.T, sr).T
            l = meter.integrated_loudness(test.astype(np.float64))
            if not math.isfinite(l):
                out = test
                break
            out = test
            err = lufs_target - l
            if abs(err) < 0.1:
                break
            out = out * (10.0 ** (err / 20.0))   # drive harder, limiter re-caps
        peak = float(np.max(np.abs(out))) or 1.0
        if peak > ceiling:                       # final safety trim
            out = out * (ceiling / peak)
    return out.astype(np.float32)


def render_soundtrack(events, duration_s, wav_path, width_px=1080.0,
                      voice: str = "marimba", foley_gain: float = 0.0,
                      foley_kind: str = "thump", drone: dict = None,
                      pop_gain: float = 0.9, glass_gain: float = 0.9,
                      rubble_gain: float = 1.0, peak_db: float = None,
                      pop_boom: float = None, bed: np.ndarray = None,
                      ring: float = 1.0, reverb: float = 1.0,
                      intro: dict = None):
    """drone (optional): {t0, dur, midi, gain, fade_in, fade_out} — a sustained
    sub-bass bed mixed UNDER the events before mastering (see synth_drone).
    pop_gain: level of the balloon-pop layer on events carrying a ``pop`` size;
    glass_gain: same for the glass-shatter layer on a ``glass`` size;
    rubble_gain: same for the concrete-break layer on a ``rubble`` size;
    peak_db: extra pre-loudness limiter for IMPULSE-driven scenes — see master()."""
    buf = mix_events(events, duration_s, width_px, voice=voice,
                     foley_gain=foley_gain, foley_kind=foley_kind,
                     pop_gain=pop_gain, glass_gain=glass_gain,
                     rubble_gain=rubble_gain, pop_boom=pop_boom, ring=ring)
    if drone:
        d = synth_drone(drone.get("dur", 8.0), drone.get("midi", 29.0),
                        drone.get("gain", 0.06), drone.get("fade_in", 8.0),
                        drone.get("fade_out", 3.0))
        i0 = int(drone.get("t0", 0.0) * SR)
        i1 = min(i0 + len(d), len(buf))
        if i1 > i0:
            seg = d[: i1 - i0]
            buf[i0:i1, 0] += seg
            buf[i0:i1, 1] += seg
    if bed is not None:
        # a continuous LAYER mixed under the events before mastering (the
        # pacman siren): mono or stereo, added sample-aligned from t=0
        m = min(len(bed), len(buf))
        if bed.ndim == 1:
            buf[:m, 0] += bed[:m]
            buf[:m, 1] += bed[:m]
        else:
            buf[:m] += bed[:m]
    if intro is not None:
        # OPT-IN silent-head fill; see intro_layer(). intro=None => bit-identical.
        # NOTE: intro={} is a valid "use all defaults" call, so this checks
        # `is not None`, not truthiness — an empty dict must still fire.
        kw = {k: v for k, v in intro.items() if k != "enabled"}
        kw.setdefault("ring", ring)
        lay = intro_layer(events, voice=voice, **kw)
        if lay is not None:
            m = min(len(lay), len(buf))
            buf[:m, 0] += lay[:m]
            buf[:m, 1] += lay[:m]
    out = master(buf, peak_db=peak_db)
    sf.write(str(wav_path), out, SR, subtype="PCM_24")
    return wav_path


def save_events(events, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(events, f)


def load_events(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------- intro fill
# A clip's soundtrack is generated from COLLISION EVENTS, so before the first
# collision there is nothing to play. Measured across 123 shipped 9:16 clips:
# median 0.40s of silence at the head, 53% silent >=0.4s, 8 clips >=2.0s
# (worst merge_spin 3.2s; double_up and merge are 6 of the 8). Autoplay feeds
# are loud, so a silent head is a swipe risk.
#
# NOTE the honest caveat: opening loudness measured r=+0.05 against
# stayed-to-watch (n=31) — this is a fix because silence is obviously wrong,
# not a proven reach lever.
#
# The model is spiral_core_rods (67.1% STW, the channel's best): it is audible
# at t=0 because the ball is launched into 645 rods and HITS one immediately —
# a real collision note in the scene's own voice. So the fill is a note of the
# clip's own voice and pitch, never a foreign SFX or a pad.
#
# OPT-IN ONLY. render_soundtrack(intro=None) is the default, so every shipped
# clip stays bit-reproducible.

def synth_riser(dur_s: float, midi_note: int, sr: int = SR) -> np.ndarray:
    """A soft swell that LANDS on the first collision — for gaps too long for a
    single note to cover (one note decays in ~0.2s; a 2.5s head needs sustain).

    Deliberately gentle: a sine an octave below the landing note gliding up to
    it, amplitude rising as t^2 so it stays out of the way early and arrives
    just as the note lands. No noise layer — broadband reads as static and the
    'no creepy, no annoying' rule bans it."""
    n = max(1, int(dur_s * sr))
    t = np.arange(n, dtype=np.float64) / sr
    frac = t / max(dur_s, 1e-6)
    f0 = midi_to_hz(midi_note - 12.0)
    f1 = midi_to_hz(midi_note - 0.15)          # arrive just under the note
    freq = f0 + (f1 - f0) * (frac ** 1.7)
    phase = 2.0 * np.pi * np.cumsum(freq) / sr
    # Envelope must be AUDIBLE AT t=0 — the whole point is that frame 0 is not
    # silent, so a swell starting from zero defeats it (measured -44 dBFS in
    # the first 0.4s before this floor was added).
    env = 0.30 + 0.70 * (frac ** 1.6)
    env *= np.clip((1.0 - frac) * 24.0, 0.0, 1.0)         # fade out over the last ~40ms
    wave = np.sin(phase) + 0.28 * np.sin(2.0 * phase)     # one octave of body
    return (wave * env * 0.5).astype(np.float32)


def intro_layer(events, voice: str = "marimba", sr: int = SR,
                gate_s: float = 0.40, riser_s: float = 0.80,
                lead_s: float = 0.05, gain: float = 0.55,
                ring: float = 1.0):
    """Fill a clip's SILENT HEAD. Returns a mono float32 buffer, or None when
    the head is already loud enough to leave alone.

    gate_s  : do nothing unless the first sounded event is at least this late
              (0.40s = the measured median, catches ~53% of the library).
    riser_s : at or past this gap use a RISER instead of a single note.
    Pitch comes from the clip's own first note, so the fill is a musical
    PICKUP — when the real first collision lands, the tune simply continues."""
    if not events:
        return None
    sounded = [e for e in events if float(e.get("note_gain", 1.0)) > 0.0
               or e.get("pop") or e.get("glass") or e.get("rubble")
               or e.get("splash") or e.get("steam")]
    if not sounded:
        sounded = list(events)
    t0 = min(float(e["t"]) for e in sounded)
    if t0 < gate_s:
        return None                      # already audible early — leave it
    pitched = [e for e in sorted(sounded, key=lambda e: e["t"])
               if e.get("note") is not None]
    midi = int(pitched[0]["note"]) if pitched else 72
    n = int((t0 + 2.0) * sr)
    buf = np.zeros(n, dtype=np.float32)
    if t0 < riser_s:
        one = NoteBank(voice, ring=ring).get(midi, 0.55)
        if one.ndim > 1:
            one = one.mean(axis=1)
        i0 = int(lead_s * sr)
        m = min(len(one), n - i0)
        if m > 0:
            buf[i0:i0 + m] += one[:m].astype(np.float32) * gain
    else:
        r = synth_riser(max(0.15, t0 - lead_s), midi, sr)
        i0 = int(lead_s * sr)
        m = min(len(r), n - i0)
        if m > 0:
            buf[i0:i0 + m] += r[:m] * gain
    return buf
