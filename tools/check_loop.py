"""Loop-seam check: render frame 0 and the LAST frame of a scene and diff them.

Every video on this channel must loop (CLAUDE.md), and the seam has to be
measured PRE-ENCODE: frame 0 is an IDR keyframe and the last frame is a deep
P-frame, so a bit-identical render still measures ~0.1-0.25/255 in the mp4 from
pure H.264 noise. This renders the two frames straight to PNG through the
scene's own render() and compares the pixels.

Runs at NF_FAST resolution — the seam is a question about scene STATE (pose,
counter, caption alpha, accumulated trail), and those are resolution-independent.

Usage:
  python tools/check_loop.py <scene> -- <scene args...>
"""
import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "output"


def load_scene(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scenes" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    scene = sys.argv[1]
    extra = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    os.environ["NF_FAST"] = "1"
    os.environ["NF_ORIENT"] = "vertical"

    # total frame count: ask the scene by rendering a deliberately out-of-range
    # still and reading the error, or just probe upward. Simpler and robust:
    # render frame 0, then binary-search the last valid frame index.
    def render_still(fr):
        cmd = [sys.executable, str(ROOT / "scenes" / f"{scene}.py"), "--",
               "--still", "--frame", str(fr), "--sound", "0",
               "--label", "loopchk"] + extra
        r = subprocess.run(cmd, capture_output=True, text=True,
                           env={**os.environ})
        return r.returncode == 0

    lo, hi = 0, 1
    while render_still(hi) and hi < 1 << 16:
        lo, hi = hi, hi * 2
    while lo + 1 < hi:
        mid = (lo + hi) // 2
        if render_still(mid):
            lo = mid
        else:
            hi = mid
    last = lo
    render_still(0)
    p0 = next(OUT.glob(f"{scene}_loopchk*_f0_9x16.png"))
    render_still(last)
    p1 = next(OUT.glob(f"{scene}_loopchk*_f{last}_9x16.png"))

    a = np.asarray(Image.open(p0).convert("RGB")).astype(np.int16)
    b = np.asarray(Image.open(p1).convert("RGB")).astype(np.int16)
    d = np.abs(a - b)
    n_diff = int((d.max(axis=2) > 2).sum())
    print(f"{scene}: last frame = {last}   max delta {d.max()}/255   "
          f"pixels over 2/255: {n_diff}")
    if d.max() <= 2:
        print("  SEAM EXACT")
    elif n_diff < a.shape[0] * a.shape[1] * 0.002:
        print("  seam effectively exact (antialiasing fringe only)")
    else:
        print("  *** SEAM MISMATCH ***")
    # the binary search leaves a still per probe — clear ALL of them, not just
    # the two that were diffed, or output/ fills with loopchk debris
    for p in OUT.glob(f"{scene}_loopchk*.png"):
        p.unlink()


if __name__ == "__main__":
    main()
