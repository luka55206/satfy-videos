"""Concat clips into a compilation with whoosh audio transitions.

Video is stream-copied (lossless, requires identical specs — the naming/spec
discipline exists for this). Audio is rebuilt: clip audio concatenated, a
synthesized whoosh overlaid leading into each cut (0.12s early, like
blender-physics), then limited and normalized to -14 LUFS.

Usage:
  python tools/build_compilation.py --out final/compilation_grow_16x9.mp4 \
      --clips clip1.mp4,clip2.mp4,...
"""
import subprocess
import sys
import tempfile
from math import gcd
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import butter, resample_poly, sosfilt

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib import audio

SR = audio.SR
LEAD = 0.12  # transition starts this early before each cut
TRANSITION_WAV = Path(__file__).resolve().parent.parent / "sfx" / "transition.wav"


def _arg(flag, default=None):
    a = sys.argv
    return a[a.index(flag) + 1] if flag in a else default


def load_transition(path, sr=SR, gain=0.95) -> np.ndarray:
    """Load a transition SFX (any rate/channels) as mono float32 at `sr`."""
    data, file_sr = sf.read(str(path), dtype="float32")
    if data.ndim > 1:
        data = data.mean(axis=1)
    if file_sr != sr:
        g = gcd(sr, file_sr)
        data = resample_poly(data, sr // g, file_sr // g).astype(np.float32)
    peak = float(np.max(np.abs(data))) or 1.0
    return (data / peak * gain).astype(np.float32)


def synth_whoosh(dur=0.8, sr=SR) -> np.ndarray:
    """Swept band-passed noise swish (deterministic)."""
    n = int(dur * sr)
    rng = np.random.default_rng(7)
    noise = rng.standard_normal(n).astype(np.float32)
    windows = 12
    step = n // windows
    out = np.zeros(n, dtype=np.float32)
    for w in range(windows):
        frac = w / (windows - 1)
        center = 300.0 * (3000.0 / 300.0) ** frac  # 300 Hz -> 3 kHz sweep
        sos = butter(2, [center * 0.6, center * 1.6], btype="band",
                     fs=sr, output="sos")
        i0, i1 = w * step, min((w + 1) * step + step // 2, n)
        seg = sosfilt(sos, noise[i0:i1]).astype(np.float32)
        fade = np.hanning(len(seg)).astype(np.float32)
        out[i0:i1] += seg * fade
    t = np.arange(n, dtype=np.float32) / n
    env = np.sin(np.pi * t ** 0.7).astype(np.float32)  # fast rise, long fall
    out *= env
    peak = float(np.max(np.abs(out))) or 1.0
    return out / peak * 0.5


def clip_duration(path) -> float:
    p = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(path)], capture_output=True, text=True,
        check=True)
    return float(p.stdout.strip())


def extract_audio(path, wav) -> None:
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-i", str(path), "-vn",
         "-ac", "2", "-ar", str(SR), str(wav)], check=True)


def main():
    out = Path(_arg("--out"))
    clips = [Path(c) for c in _arg("--clips").split(",")]
    for c in clips:
        if not c.exists():
            sys.exit(f"missing clip: {c}")

    tmp = Path(tempfile.mkdtemp(prefix="compilation_"))

    # 1) lossless video concat
    listfile = tmp / "list.txt"
    listfile.write_text(
        "".join(f"file '{c.resolve().as_posix()}'\n" for c in clips),
        encoding="utf-8")
    silent = tmp / "video.mp4"
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0",
         "-i", str(listfile), "-c", "copy", "-an", str(silent)], check=True)

    # 2) rebuild audio with whooshes at boundaries
    durs = [clip_duration(c) for c in clips]
    total = sum(durs)
    buf = np.zeros((int((total + 1.0) * SR), 2), dtype=np.float32)
    t0 = 0.0
    for c, d in zip(clips, durs):
        wav = tmp / (c.stem + ".wav")
        extract_audio(c, wav)
        data, sr = sf.read(wav, dtype="float32")
        i0 = int(t0 * SR)
        i1 = min(i0 + len(data), len(buf))
        buf[i0:i1] += data[: i1 - i0]
        t0 += d
    trans = (load_transition(TRANSITION_WAV) if TRANSITION_WAV.exists()
             else synth_whoosh())
    cut = 0.0
    for d in durs[:-1]:
        cut += d
        i0 = int((cut - LEAD) * SR)
        i1 = min(i0 + len(trans), len(buf))
        w = i1 - i0
        # duck the music under the transition (fade in/out) so the swish reads
        # clearly over the busy note-storm endings, then lay the swish on top
        duck = np.full(w, 0.55, dtype=np.float32)
        f = int(0.03 * SR)
        if w > 2 * f:
            duck[:f] = np.linspace(1.0, 0.55, f)
            duck[-f:] = np.linspace(0.55, 1.0, f)
        buf[i0:i1] *= duck[:, None]
        buf[i0:i1, 0] += trans[:w]
        buf[i0:i1, 1] += trans[:w]

    mastered = audio.master(buf)
    mix = tmp / "mix.wav"
    sf.write(str(mix), mastered, SR, subtype="PCM_24")

    # 3) mux
    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-i", str(silent), "-i", str(mix),
         "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy",
         "-c:a", "aac", "-b:a", "384k", "-shortest", str(out)], check=True)
    print(f"wrote {out}  ({total:.1f}s, {len(clips)} clips)")


if __name__ == "__main__":
    main()
