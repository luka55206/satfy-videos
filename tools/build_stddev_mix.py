"""Join the standard-deviation boards into ONE video with real transitions.

Every board clip ends with its piles drained and the tube refilled (an empty board)
and starts on an empty board with the hum, so the cut points are already quiet. Here
each pair is CROSSFADED (video `xfade`, audio `acrossfade`) over --fade seconds: the
old board dissolves into the next one (pegs appear, the counter changes) while the
old tune rings out and the next hum rises, so the audio bridges the cut instead of
restarting. No overlay filters (they drop frames at junctions); the encode is forced
constant-frame-rate.

    python tools/build_stddev_mix.py --out final/needs-review/stddev_mix_16x9.mp4 \
        --clips a.mp4,b.mp4,c.mp4 [--fade 1.0] [--crf 18]

Prints the chapter list (start time of each clip) for the video description.
"""
import subprocess
import sys


def arg(flag, default=None):
    a = sys.argv
    return a[a.index(flag) + 1] if flag in a else default


def frames(path):
    p = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_packets",
                        "-show_entries", "stream=nb_read_packets", "-of", "csv=p=0", str(path)],
                       capture_output=True, text=True, check=True)
    return int(p.stdout.strip().split(",")[0])


def mmss(t):
    return f"{int(t // 60)}:{int(t % 60):02d}"


def main():
    clips = arg("--clips", "").split(",")
    out = arg("--out")
    fade = float(arg("--fade", 1.0))
    crf = arg("--crf", "18")
    if not out or len(clips) < 2:
        sys.exit(__doc__)
    durs = [frames(c) / 60.0 for c in clips]
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-stats"]
    for c in clips:
        cmd += ["-i", c]
    vf, af, starts = [], [], [0.0]
    off, vlast, alast = 0.0, "0:v", "0:a"
    for i in range(1, len(clips)):
        off += durs[i - 1] - fade
        starts.append(off)
        vo, ao = f"v{i}", f"a{i}"
        vf.append(f"[{vlast}][{i}:v]xfade=transition=fade:duration={fade}:offset={off:.4f}[{vo}]")
        af.append(f"[{alast}][{i}:a]acrossfade=d={fade}:c1=tri:c2=tri[{ao}]")
        vlast, alast = vo, ao
    total = sum(durs) - fade * (len(clips) - 1)
    cmd += ["-filter_complex", ";".join(vf + af), "-map", f"[{vlast}]", "-map", f"[{alast}]",
            "-c:v", "libx264", "-crf", crf, "-preset", "medium", "-pix_fmt", "yuv420p",
            "-r", "60", "-fps_mode", "cfr", "-c:a", "aac", "-b:a", "384k", "-movflags", "+faststart", out]
    print(f"[mix] {len(clips)} clips, expected {total:.2f}s ({mmss(total)})")
    subprocess.run(cmd, check=True)
    print(f"[mix] wrote {out}")
    print("[mix] chapters:")
    for c, t in zip(clips, starts):
        print(f"  {mmss(t)}  {c}")


if __name__ == "__main__":
    main()
