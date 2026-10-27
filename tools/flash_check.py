"""Photosensitivity flash check -- WCAG 2.3.1 / Harding-style approximation.

WHY: the neon-on-black format is inherently low-luminance and MOST clips have
literally zero qualifying flashes (measured mean screen luminance 0.001-0.11).
The failures come from ONE mechanic -- whole-arena colour cycling at a climax.
This tool finds those clips so a warning card is added ONLY where it is earned,
instead of blanket-warning on content that does not flash.

THE THRESHOLD (the clinical one, from WCAG 2.3.1 / the Harding test broadcasters
use): a GENERAL FLASH is a pair of OPPOSING changes in relative luminance of
>= 0.10, where the darker state is < 0.80, over a contiguous area > 25% of the
viewing field. Three or more general flashes in any ONE SECOND = FAIL.

APPROXIMATION + why it is CONSERVATIVE IN THE RIGHT DIRECTION: area is measured
on a 32x18 cell grid against 25% of the WHOLE SCREEN. The real rule is 25% of a
10-degree visual field, which is a much SMALLER patch -- so everything this tool
flags would also fail the real test (true positives), while small-area flashes
it misses might still fail. Treat a PASS as "no large-area flashing", not as a
clinical clearance.

Usage:
  python tools/flash_check.py <clip.mp4> [<clip.mp4> ...]
  python tools/flash_check.py final/uploaded/*.mp4 --json out.json
  python tools/flash_check.py "final/megamix/megamix 6/compilation_megamix_16x9.mp4"

Exit code 1 if ANY input fails (>= 3 general flashes in any 1s window), else 0,
so it can gate a build the way check_loop.py gates a loop seam.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

GRID_W, GRID_H = 32, 18          # cell grid the area test is measured on
CELLS = GRID_W * GRID_H
AREA_FRAC = 0.25                 # >25% of the field must move together
DL = 0.10                        # relative-luminance step that counts
DARK_MAX = 0.80                  # the darker state must be below this
FAIL_PER_SEC = 3                 # >= this many flashes in 1s = FAIL


def _linearize(c):
    """sRGB 0-255 -> linear 0-1 (needed before relative luminance)."""
    c = c / 255.0
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def _probe_fps(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=r_frame_rate", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True).stdout.strip()
    try:
        n, d = out.split("/")
        return float(n) / float(d)
    except Exception:
        return 60.0


def _cell_luma(path):
    """Yield per-frame (relative luminance per cell, saturated-red fraction)."""
    cmd = ["ffmpeg", "-v", "error", "-i", str(path),
           "-vf", f"scale={GRID_W}:{GRID_H}:flags=area",
           "-pix_fmt", "rgb24", "-f", "rawvideo", "-"]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, bufsize=1 << 24)
    fsz = CELLS * 3
    try:
        while True:
            buf = p.stdout.read(fsz)
            if len(buf) < fsz:
                break
            a = np.frombuffer(buf, np.uint8).reshape(CELLS, 3).astype(np.float32)
            r, g, b = _linearize(a[:, 0]), _linearize(a[:, 1]), _linearize(a[:, 2])
            lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
            # saturated red (the Harding red-flash rule tracks these separately)
            s = r + g + b + 1e-9
            red = float((((r / s) >= 0.8) & (r > 0.2)).mean())
            yield lum, red
    finally:
        p.stdout.close()
        p.wait()


def analyse(path, fps=None):
    fps = fps or _probe_fps(path)
    lo = hi = None
    events = []          # (frame_index, direction)
    means, reds = [], []
    n = 0
    for lum, red in _cell_luma(path):
        means.append(float(lum.mean()))
        reds.append(red)
        if lo is None:
            lo = lum.copy()
            hi = lum.copy()
            n = 1
            continue
        np.minimum(lo, lum, out=lo)
        np.maximum(hi, lum, out=hi)
        # a cell has risen (or fallen) >= DL from its last extremum
        up = (lum - lo >= DL) & (lo < DARK_MAX)
        dn = (hi - lum >= DL) & (lum < DARK_MAX)
        nu, nd = int(up.sum()), int(dn.sum())
        if nu >= nd and nu >= CELLS * AREA_FRAC:
            events.append((n, +1))
            lo[up] = lum[up]; hi[up] = lum[up]
        elif nd >= CELLS * AREA_FRAC:
            events.append((n, -1))
            lo[dn] = lum[dn]; hi[dn] = lum[dn]
        n += 1

    if n < 2:
        return None

    # a FLASH is an OPPOSING pair -- count each reversal in the event sequence
    flashes, last = [], 0
    for f, d in events:
        if last and d != last:
            flashes.append(f)
        last = d

    # The threshold is "3 flashes in ANY one second", so the window must SLIDE.
    # bad_seconds is derived from the SAME sliding measure -- deriving it from
    # aligned second-buckets instead lets a clip fail with an EMPTY flagged
    # list (a 1s window straddling a second boundary), and warning_card.py
    # indexes bad_seconds[0] to place its "flashing sections" stamp.
    fl = np.array(flashes, dtype=int)
    worst, worst_t = 0, 0.0
    bad = set()
    for f in fl:
        c = int(((fl >= f) & (fl < f + fps)).sum())
        if c > worst:
            worst, worst_t = c, f / fps
        if c >= FAIL_PER_SEC:
            bad.add(int(f / fps))
    bad = sorted(bad)
    mean = np.array(means)
    return dict(
        path=str(path), frames=n, duration=n / fps, fps=fps,
        transitions=len(events), flashes=len(fl),
        worst_1s=worst, worst_t=round(worst_t, 2),
        bad_seconds=bad, fail=worst >= FAIL_PER_SEC,
        mean_luminance=round(float(mean.mean()), 4),
        p99_luminance=round(float(np.percentile(mean, 99)), 4),
        max_red_area=round(float(max(reds)), 3),
    )


def _ranges(secs):
    """[4,5,6,9] -> '0:04-0:06, 0:09' for a readable report."""
    if not secs:
        return ""
    out, start, prev = [], secs[0], secs[0]
    for s in secs[1:] + [None]:
        if s is not None and s == prev + 1:
            prev = s
            continue
        out.append(f"{start//60}:{start%60:02d}" if start == prev
                   else f"{start//60}:{start%60:02d}-{prev//60}:{prev%60:02d}")
        if s is not None:
            start = prev = s
    return ", ".join(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("clips", nargs="+")
    ap.add_argument("--json", help="write full results here")
    ap.add_argument("--fps", type=float, default=None)
    ap.add_argument("--quiet", action="store_true", help="only print failures")
    a = ap.parse_args()

    results, failed = [], 0
    for c in a.clips:
        p = Path(c)
        if not p.exists():
            print(f"!! missing: {c}", file=sys.stderr)
            continue
        r = analyse(p, a.fps)
        if r is None:
            continue
        results.append(r)
        if r["fail"]:
            failed += 1
        elif a.quiet:
            continue
        mark = "FAIL" if r["fail"] else "ok  "
        print(f"{mark} {p.name}")
        print(f"       {r['duration']:6.1f}s  flashes={r['flashes']:<4d} "
              f"worst 1s={r['worst_1s']} (t={r['worst_t']}s)  "
              f"mean lum={r['mean_luminance']}")
        if r["bad_seconds"]:
            print(f"       flagged: {_ranges(r['bad_seconds'])}")

    if a.json:
        Path(a.json).write_text(json.dumps(results, indent=2))
    print(f"\n{len(results)} checked, {failed} FAIL "
          f"(>= {FAIL_PER_SEC} general flashes in one second)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
