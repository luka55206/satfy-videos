"""Original synthesised SFX for 'shock' Shorts (paradox remakes): whoosh, hit, snap, chime, tick, riser, pad.

All numpy, no samples. Build a mono bed with Bed(dur).add(t, sig, gain) and hand bed.out to kit.deliver_loop(bed=...).
Signals here are unit-ish level; mix with gains around 0.03-0.3 and let audio.master() set -14 LUFS.
"""
import numpy as np

from lib import audio

SR = audio.SR


def _tv(d):
    return np.arange(int(d * SR)) / SR


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


class Bed:
    def __init__(self, dur, seed=1):
        self.n = int(round(dur * SR))
        self.out = np.zeros(self.n)
        self.rng = np.random.default_rng(seed)

    def add(self, t0, sig, g=1.0, wrap=True):
        i0 = int(round(t0 * SR))
        idx = np.arange(len(sig)) + i0
        if wrap:
            idx %= self.n
        else:
            keep = idx < self.n
            idx, sig = idx[keep], sig[keep]
        np.add.at(self.out, idx, g * sig)

    def noise(self, d, smooth=1):
        nz = self.rng.standard_normal(int(d * SR))
        if smooth > 1:
            nz = np.convolve(nz, np.ones(smooth) / smooth, mode="same")
        return nz

    # --- one-shots -------------------------------------------------------------------------------
    def whoosh(self, t0, d=0.5, g=0.12, up=True):
        tv = _tv(d)
        nz = self.noise(d, 3)
        sweep = np.sin(2 * np.pi * np.cumsum((300 + 900 * (tv / d if up else 1 - tv / d))) / SR)
        env = np.sin(np.pi * tv / d) ** 2
        self.add(t0, (nz * 1.5 + 0.3 * sweep) * env, g)

    def hit(self, t0, g=0.5, low=45):
        tv = _tv(1.2)
        body = np.sin(2 * np.pi * np.cumsum(low + 110 * np.exp(-tv / 0.05)) / SR) * np.exp(-tv / 0.35)
        click = self.noise(1.2) * np.exp(-tv / 0.012)
        self.add(t0, body + 0.35 * click, g)

    def snap(self, t0, g=0.25):
        """a chocolate snap: a bright crack + a woody knock"""
        tv = _tv(0.18)
        nz = self.noise(0.18)
        nz = nz - np.convolve(nz, np.ones(8) / 8, mode="same")
        knock = np.sin(2 * np.pi * 900 * tv) * np.exp(-tv / 0.02)
        self.add(t0, nz * np.exp(-tv / 0.03) + 0.5 * knock, g)

    def chime(self, t0, notes=(84, 88, 91), g=0.08, decay=0.6):
        for k, m in enumerate(notes):
            tv = _tv(2.0)
            sig = (np.sin(2 * np.pi * hz(m) * tv) + 0.25 * np.sin(2 * np.pi * hz(m) * 2.76 * tv)) * np.exp(-tv / decay)
            self.add(t0 + 0.03 * k, sig, g)

    def pluck(self, t0, m, g=0.12, d=0.4):
        tv = _tv(d)
        ph = 2 * np.pi * hz(m) * tv
        sig = (np.sin(ph) + 0.4 * np.sin(2 * ph) + 0.15 * np.sin(3 * ph)) * np.exp(-tv / (d * 0.3))
        self.add(t0, sig * np.clip(tv / 0.003, 0, 1), g)

    def tick(self, t0, f=2400, g=0.05):
        tv = _tv(0.03)
        self.add(t0, np.sin(2 * np.pi * f * tv) * np.exp(-tv / 0.005), g)

    def riser(self, t0, d, g=0.08, f0=200, f1=1600):
        tv = _tv(d)
        u = tv / d
        sig = np.sin(2 * np.pi * np.cumsum(f0 + (f1 - f0) * u ** 2) / SR) * 0.5 + self.noise(d, 4) * 0.6
        self.add(t0, sig * u ** 2, g)

    def drop(self, t0, d=0.8, g=0.1, f0=1400, f1=120):
        tv = _tv(d)
        sig = np.sin(2 * np.pi * np.cumsum(f0 + (f1 - f0) * tv / d) / SR) * np.sin(np.pi * tv / d)
        self.add(t0, sig, g)

    # --- beds ---------------------------------------------------------------------------------------
    def pad(self, chords, beat, g=0.03):
        """chords: [(t0, (midi...)), ...] — soft sine pad, each chord held until the next (wraps)."""
        for i, (t0, notes) in enumerate(chords):
            t1 = chords[i + 1][0] if i + 1 < len(chords) else self.n / SR
            d = t1 - t0 + 0.4
            tv = _tv(d)
            env = np.clip(tv / 0.3, 0, 1) * np.clip((d - tv) / 0.4, 0, 1)
            sig = sum(np.sin(2 * np.pi * hz(m) * tv) + 0.3 * np.sin(2 * np.pi * hz(m) * 1.003 * tv) for m in notes)
            self.add(t0, sig * env / len(notes), g)

    def pulse(self, t0, t1, beat, notes, g=0.05):
        """an arpeggiated plucked pulse (8ths) through `notes` between t0 and t1."""
        t, k = t0, 0
        while t < t1:
            self.pluck(t, notes[k % len(notes)], g, d=0.3)
            t += beat / 2
            k += 1

    def get(self):
        return self.out.astype(np.float32)
