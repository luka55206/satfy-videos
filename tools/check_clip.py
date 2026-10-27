"""check_clip — the verification rungs a new sand clip has to clear, in one run.

    python tools/check_clip.py output/<clip>.mp4 [more.mp4 ...]

Prints, per clip: duration/fps/size, integrated LUFS (STEREO — a mono downmix
under-reads a panned mix), true peak of the decoded mp4 (AAC overshoot is only
visible here), the last-0.5 s peak (loop-seam click), the post-encode loop seam
as a MEAN per-pixel delta (good band 0.12-0.72, broken 1.16-1.78), and the
sidecar's note health (`len(set(notes))`, top pitch share, events per 5 s).
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def probe(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries",
         "stream=codec_name,width,height,r_frame_rate,pix_fmt,nb_read_packets",
         "-select_streams", "v:0", "-count_packets", "-of", "json", str(path)],
        capture_output=True, text=True, check=True).stdout
    return json.loads(out)["streams"][0]


def frame(path, index, w, h):
    out = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path),
         "-vf", f"select=eq(n\\,{index})", "-fps_mode", "passthrough", "-frames:v", "1",
         "-f", "rawvideo", "-pix_fmt", "gray", "-"],
        capture_output=True, check=True).stdout
    return np.frombuffer(out, dtype=np.uint8).reshape(h, w).astype(np.int16)


def audio_stats(path):
    import pyloudnorm as pyln
    import soundfile as sf
    wav = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path), "-f", "wav", "-"],
        capture_output=True, check=True).stdout
    import io
    data, sr = sf.read(io.BytesIO(wav), dtype="float64", always_2d=True)
    meter = pyln.Meter(sr)
    lufs = meter.integrated_loudness(data)
    peak = 20 * np.log10(max(np.abs(data).max(), 1e-12))
    tail = data[-int(0.5 * sr):]
    tpk = 20 * np.log10(max(np.abs(tail).max(), 1e-12))
    # per-second RMS, to catch a climax that measures QUIETER than the body
    secs = [20 * np.log10(max(np.sqrt(np.mean(data[i * sr:(i + 1) * sr] ** 2)),
                              1e-12))
            for i in range(int(len(data) / sr))]
    return lufs, peak, tpk, secs


def main():
    for arg in sys.argv[1:]:
        p = Path(arg)
        st = probe(p)
        w, h, n = int(st["width"]), int(st["height"]), int(st["nb_read_packets"])
        fps = eval(st["r_frame_rate"])
        print(f"\n=== {p.name}")
        print(f"  {st['codec_name']} {st['pix_fmt']} {w}x{h} @{fps:.0f} "
              f"{n} frames = {n / fps:.2f}s")
        a = frame(p, 0, w, h)
        b = frame(p, n - 1, w, h)
        d = np.abs(a - b)
        print(f"  seam mean |delta| {d.mean():.3f}   max {d.max()}")
        try:
            lufs, peak, tpk, secs = audio_stats(p)
            print(f"  LUFS {lufs:.2f}   peak {peak:.2f} dBFS   "
                  f"last0.5s peak {tpk:.1f} dBFS")
            print(f"  RMS/s {[round(x, 1) for x in secs[::5]]}")
        except Exception as exc:                      # noqa: BLE001
            print(f"  audio: {exc}")
        ev = p.with_name(p.stem + "_events.json")
        if ev.exists():
            e = json.loads(ev.read_text())
            notes = [x["note"] for x in e if x.get("note") is not None]
            if notes:
                from collections import Counter
                c = Counter(notes)
                top = c.most_common(1)[0]
                print(f"  notes {len(notes)}  distinct {len(set(notes))}  "
                      f"top {top[0]} {100 * top[1] / len(notes):.1f}%")
            bins = max(1, int((n / fps) // 5))
            hist = [0] * bins
            for x in e:
                hist[min(int(x["t"] / (n / fps) * bins), bins - 1)] += 1
            print(f"  events/5s {hist}")


if __name__ == "__main__":
    main()
