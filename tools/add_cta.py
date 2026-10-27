"""Draw a SMALL end call-to-action onto a finished clip (no re-render).

A soft pill ("Like & subscribe for more calm math") that fades in near the end and is
fully gone before the last frame, so a nonstop loop's seam is untouched (alpha 0 at
frame 0 and at the last frame). Post-render, like add_caption: rewording costs one
encode, not a render. Run it AFTER add_caption.

Placement is the 9:16 band just above the bottom HUD and clear of the Shorts overlay
(which covers the bottom ~18-20%): --y is the pill centre as a fraction of height.
Deliberately quiet: small type, dark translucent pill, no colour pop, no motion.

    python tools/add_cta.py output/x_9x16.mp4 --out output/x_cta_9x16.mp4 \
        --text "Like & subscribe for more calm math" --y 0.735 --start 4.0 --end 0.35
"""
import argparse
import math
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import cairo

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from add_caption import FPS, has_audio, probe  # noqa: E402

LOGICAL_W = 1080.0


def cta_sheet(w, h, text, y_f, size_f):
    """The pill on a transparent full-frame sheet (device px)."""
    s = w / LOGICAL_W
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
    ctx = cairo.Context(surf)
    ctx.select_font_face("Arial", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
    fs = h * size_f
    ctx.set_font_size(fs)
    ext = ctx.text_extents(text)
    pad_x, pad_y = fs * 0.9, fs * 0.55
    pw, ph = ext.x_advance + 2 * pad_x, fs + 2 * pad_y
    cx, cy = w / 2, h * y_f
    x0, y0, r = cx - pw / 2, cy - ph / 2, ph / 2
    ctx.new_sub_path()
    ctx.arc(x0 + pw - r, y0 + r, r, -math.pi / 2, 0)
    ctx.arc(x0 + pw - r, y0 + ph - r, r, 0, math.pi / 2)
    ctx.arc(x0 + r, y0 + ph - r, r, math.pi / 2, math.pi)
    ctx.arc(x0 + r, y0 + r, r, math.pi, 1.5 * math.pi)
    ctx.close_path()
    ctx.set_source_rgba(0.04, 0.04, 0.08, 0.62)
    ctx.fill_preserve()
    ctx.set_source_rgba(1, 1, 1, 0.22)
    ctx.set_line_width(1.5 * s)
    ctx.stroke()
    ctx.set_source_rgba(1, 1, 1, 0.88)
    ctx.move_to(cx - ext.x_advance / 2 - ext.x_bearing, cy + fs * 0.35)
    ctx.show_text(text)
    surf.flush()
    return surf


def smooth(p):
    p = min(max(p, 0.0), 1.0)
    return p * p * (3 - 2 * p)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("clip")
    ap.add_argument("--out", required=True)
    ap.add_argument("--text", default="Like & subscribe for more calm math")
    ap.add_argument("--y", type=float, default=0.735, help="pill centre, fraction of height")
    ap.add_argument("--size", type=float, default=0.0175, help="font size, fraction of height")
    ap.add_argument("--start", type=float, default=4.0, help="seconds before the end it fades in")
    ap.add_argument("--end", type=float, default=0.35, help="seconds before the end it is fully gone")
    ap.add_argument("--fade", type=float, default=0.5)
    ap.add_argument("--crf", type=int, default=18)
    a = ap.parse_args()

    src = Path(a.clip)
    w, h, total = probe(src)
    sheet = cta_sheet(w, h, a.text, a.y, a.size)
    dur = total / FPS
    t_in, t_out = dur - a.start, dur - a.end
    alphas = [smooth((f / FPS - t_in) / a.fade) * smooth((t_out - f / FPS) / a.fade) for f in range(total)]
    assert alphas[0] == 0.0 and alphas[-1] == 0.0, "CTA must be invisible at the loop seam"

    tmp = Path(tempfile.mkdtemp()) / "cta.mp4"
    dec = subprocess.Popen(["ffmpeg", "-v", "error", "-i", str(src), "-map", "0:v:0",
                            "-f", "rawvideo", "-pix_fmt", "bgra", "-"], stdout=subprocess.PIPE)
    enc_cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "rawvideo",
               "-pix_fmt", "bgra", "-s", f"{w}x{h}", "-r", str(FPS), "-i", "pipe:0"]
    if has_audio(src):
        enc_cmd += ["-i", str(src), "-map", "0:v:0", "-map", "1:a:0", "-c:a", "copy"]
    enc_cmd += ["-c:v", "libx264", "-preset", "medium", "-crf", str(a.crf),
                "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(tmp)]
    enc = subprocess.Popen(enc_cmd, stdin=subprocess.PIPE)
    nbytes = w * h * 4
    drawn = 0
    for f in range(total):
        buf = dec.stdout.read(nbytes)
        if len(buf) < nbytes:
            break
        if alphas[f] > 1e-4:
            frame = bytearray(buf)
            surf = cairo.ImageSurface.create_for_data(memoryview(frame), cairo.FORMAT_ARGB32, w, h, w * 4)
            ctx = cairo.Context(surf)
            ctx.set_source_surface(sheet, 0, 0)
            ctx.paint_with_alpha(alphas[f])
            surf.flush()
            del ctx, surf
            enc.stdin.write(bytes(frame))
            drawn += 1
        else:
            enc.stdin.write(buf)
    enc.stdin.close()
    dec.stdout.close()
    if enc.wait() != 0 or dec.wait() not in (0, None):
        sys.exit("[add_cta] ffmpeg failed")
    _, _, out_n = probe(tmp)
    if out_n != total:
        sys.exit(f"[add_cta] packets {total} -> {out_n}; refusing (a dropped frame breaks the loop)")
    shutil.move(str(tmp), a.out)
    print(f"[add_cta] {Path(a.out).name}: {total} packets ok, CTA on {drawn} frames "
          f"({t_in:.2f}-{t_out:.2f}s), invisible at frame 0 and the last frame")


if __name__ == "__main__":
    main()
