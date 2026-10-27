"""Render the photosensitivity WARNING CARD as a standalone segment.

WHEN IT IS USED (standing rule): a megamix/marathon gets this card at its HEAD
ONLY IF `tools/flash_check.py` FAILS one of its source clips. The format is
mostly low-luminance neon-on-black and most clips never flash -- a blanket
warning on content that does not flash is noise, and noise is what makes people
stop reading warnings. `--sections` names WHERE the flashing is, so one head
card also serves as the per-clip warning without costing extra runtime.

**A MARATHON PASSES `--no-sections`** (Luka, 2026-08-23): an hour of ~87 clips
lists so many timestamps that the line stops being navigable and becomes a wall
of numbers. The warning TEXT alone is enough at that length; the per-section
list is a 8-10 minute megamix's feature.

The card is built to the TARGET CLIP'S EXACT SPEC (resolution, fps, yuv420p,
silent AAC track) so megamix.ps1 can prepend it as segment 0 of both the video
concat and the PCM audio chain with no re-encode of anything else.

It fades up from and back to black -- a warning card must never itself be a
hard cut to a bright frame.

Usage:
  python tools/warning_card.py --like "final/megamix/megamix 7/01_x_16x9.mp4" \
      --out output/warning_card.mp4 --sections 4:06 7:12
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import flash_check
from lib import studio

AMBER = (1.0, 0.85, 0.25)
DEFAULT_DUR = 3.0
FADE_S = 0.4

HEAD = "PHOTOSENSITIVITY WARNING"
BODY = ["This video contains flashing lights", "and rapid colour changes."]


def _probe(clip):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
         "stream=width,height,r_frame_rate", "-of", "csv=p=0", str(clip)],
        capture_output=True, text=True, check=True).stdout.strip().split(",")
    w, h, rate = int(out[0]), int(out[1]), out[2]
    n, d = rate.split("/")
    return w, h, round(float(n) / float(d))


def _duration(clip):
    return float(subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
         "stream=duration", "-of", "csv=p=0", str(clip)],
        capture_output=True, text=True, check=True).stdout.strip().split(",")[0])


def _stamp(sec):
    sec = int(sec)
    return f"{sec // 60}:{sec % 60:02d}"


CACHE_VERSION = 2   # bump whenever analyse()'s output changes meaning


def _cache_key(p):
    st = Path(p).stat()
    return f"v{CACHE_VERSION}|{Path(p).name}|{st.st_size}|{int(st.st_mtime)}"


def scan(clips, cache_path=None, lead=0.0, trim=0.0, ends=None):
    """Flash-check clips IN CUT ORDER; return (needs_card, sections, report).

    Scanning 4K sources is the slow part of a megamix build, so results are
    cached on (name, size, mtime) -- a rebuild of the same cut is instant.
    `trim` = seconds the build drops from each clip's head (megamix.ps1's
    shatter cut drops the baked intro) -- one value, or one per clip -- so the
    timestamps land where they play. `ends` = per clip, the second the build
    CUTS the tail at (tools/tail_trim.py) or None; flashes past it never play.
    """
    cache = {}
    cp = Path(cache_path) if cache_path else None
    if cp and cp.exists():
        try:
            cache = json.loads(cp.read_text())
        except Exception:
            cache = {}

    trims = list(trim) if isinstance(trim, (list, tuple)) else [trim] * len(clips)
    ends = list(ends) if ends else [None] * len(clips)
    offset, sections, report, dirty = lead, [], [], False
    for c, trim, end in zip(clips, trims, ends):
        key = _cache_key(c)
        r = cache.get(key)
        if r is None:
            print(f"  flash-check: {Path(c).name}", file=sys.stderr)
            r = flash_check.analyse(c)
            cache[key] = r
            dirty = True
        cut = r["duration"] if end is None else min(end, r["duration"])
        bad = [s for s in r["bad_seconds"] if s < cut]
        fail = bool(r["fail"]) and (bool(bad) if r["bad_seconds"] else r["worst_t"] < cut)
        # offset + a time inside the clip file = where it plays in the build
        report.append(dict(r, offset=offset - trim, trim=trim, end=cut,
                           fail=fail, bad_seconds=bad))
        if fail:
            # name the FIRST flagged second of each failing clip, mapped onto
            # the finished timeline -- one head card then also tells the viewer
            # WHERE the flashing is, at no extra runtime
            first = bad[0] if bad else int(r["worst_t"])
            sections.append(_stamp(offset + max(first - trim, 0)))
        offset += cut - trim

    if cp and dirty:
        cp.parent.mkdir(parents=True, exist_ok=True)
        cp.write_text(json.dumps(cache, indent=1))
    return bool(sections), sections, report


def _smoothstep(p):
    p = max(0.0, min(1.0, p))
    return p * p * (3 - 2 * p)


def render(out, w, h, fps, dur=DEFAULT_DUR, sections=None, crf=18):
    # logical coords stay 1920x1080 / 1080x1920 so the text math is
    # resolution-independent, exactly like the scenes
    logical_w, logical_h = (1920, 1080) if w >= h else (1080, 1920)
    scale = w / logical_w
    canvas = studio.Canvas(logical_w, logical_h, scale=scale)
    if (canvas.pw, canvas.ph) != (w, h):
        raise SystemExit(f"spec mismatch: built {canvas.pw}x{canvas.ph}, need {w}x{h}")

    tmp = Path(str(out) + ".silent.mp4")
    vw = studio.VideoWriter(tmp, canvas, fps=fps, crf=crf)
    n = int(round(dur * fps))
    fade = max(1, int(round(FADE_S * fps)))
    lh = canvas.h
    for i in range(n):
        a = min(_smoothstep(i / fade), _smoothstep((n - 1 - i) / fade))
        canvas.clear()
        canvas.text_block([HEAD], y=lh * 0.40, size=lh * 0.058,
                          color=AMBER, alpha=a, max_w=canvas.w * 0.86)
        canvas.text_block(BODY, y=lh * 0.545, size=lh * 0.042,
                          color=studio.WHITE, alpha=a * 0.92,
                          max_w=canvas.w * 0.80)
        if sections:
            canvas.text_block([f"Flashing sections:  {'   '.join(sections)}"],
                              y=lh * 0.70, size=lh * 0.030,
                              color=studio.WHITE, alpha=a * 0.62,
                              max_w=canvas.w * 0.80)
        vw.write_frame()
    vw.close()

    # silent AAC at the same duration -- megamix.ps1's audio pass decodes every
    # segment with `-vn`, which errors out on a video-only file
    subprocess.run(
        ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
         "-i", str(tmp), "-f", "lavfi", "-t", f"{n / fps:.6f}",
         "-i", "anullsrc=channel_layout=stereo:sample_rate=48000",
         "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy",
         "-c:a", "aac", "-b:a", "384k", "-movflags", "+faststart", str(out)],
        check=True)
    tmp.unlink()
    return n / fps


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--like", help="clip whose spec the card must match")
    ap.add_argument("--out", required=True)
    ap.add_argument("--dur", type=float, default=DEFAULT_DUR)
    ap.add_argument("--sections", nargs="*", default=None,
                    help="timestamps of the flashing passages, e.g. 4:06 7:12")
    ap.add_argument("--size", help="WxH when --like is not given")
    ap.add_argument("--fps", type=int, default=60)
    ap.add_argument("--crf", type=int, default=18)
    ap.add_argument("--still", action="store_true", help="write a PNG preview instead")
    ap.add_argument("--scan", nargs="*", default=None, metavar="CLIP",
                    help="flash-check these clips IN CUT ORDER; render the card "
                         "ONLY if one fails, with --sections filled in from the "
                         "finished timeline. Writes nothing when none flash.")
    ap.add_argument("--force", action="store_true",
                    help="with --scan: render the card even if nothing failed")
    ap.add_argument("--no-sections", action="store_true",
                    help="omit the 'Flashing sections' line -- the warning text "
                         "alone. Use for a MARATHON: ~87 clips list too many "
                         "timestamps for the line to be navigable.")
    ap.add_argument("--cache", default="output/flash_cache.json")
    ap.add_argument("--report", help="with --scan: write the per-clip result JSON here")
    ap.add_argument("--trim", type=float, default=0.0,
                    help="with --scan: seconds the build drops from each clip's head "
                         "(megamix.ps1's shatter cut), so timestamps match the build")
    ap.add_argument("--trim-auto", action="store_true",
                    help="with --scan: trim 134 frames only from clips that still carry the "
                         "baked intro (tools/intro_detect.py)")
    ap.add_argument("--tail-trim", action="store_true",
                    help="with --scan: the build cuts each loop's black tail early "
                         "(tools/tail_trim.py) -- move later timestamps and ignore "
                         "flashes past the cut")
    a = ap.parse_args()

    if a.scan is not None:
        if not a.scan:
            raise SystemExit("--scan needs at least one clip")
        trim = a.trim
        if a.trim_auto:
            from intro_detect import INTRO_OVERLAY, has_intro
            trim = [INTRO_OVERLAY / 60.0 if has_intro(c) else 0.0 for c in a.scan]
        ends = None
        if a.tail_trim:
            from tail_trim import FPS as TT_FPS, dead_tail
            ends = [(r["end"] / TT_FPS if r else None)
                    for r in (dead_tail(c) for c in a.scan)]
        needed, sections, report = scan(a.scan, a.cache, lead=a.dur, trim=trim, ends=ends)
        if a.report:
            Path(a.report).parent.mkdir(parents=True, exist_ok=True)
            Path(a.report).write_text(json.dumps(report, indent=2))
        bad = [r for r in report if r["fail"]]
        for r in bad:
            print(f"  FLASHES: {Path(r['path']).name} "
                  f"(worst {r['worst_1s']}/s) -> "
                  f"{_stamp(r['offset'] + (r['bad_seconds'][0] if r['bad_seconds'] else int(r['worst_t'])))}")
        if not needed and not a.force:
            print("no flashing clips -- NO WARNING CARD (nothing written)")
            return
        if a.no_sections:
            sections = []
        w, h, fps = _probe(a.scan[0])
        d = render(a.out, w, h, fps, a.dur, sections or None, a.crf)
        print(f"WARNING CARD -> {a.out}  {w}x{h}@{fps}  {d:.3f}s  "
              f"sections: {' '.join(sections) if sections else '(none)'}")
        return

    if a.like:
        w, h, fps = _probe(a.like)
    elif a.size:
        w, h = (int(x) for x in a.size.lower().split("x"))
        fps = a.fps
    else:
        raise SystemExit("need --like or --size")

    if a.still:
        logical_w, logical_h = (1920, 1080) if w >= h else (1080, 1920)
        c = studio.Canvas(logical_w, logical_h, scale=w / logical_w)
        c.clear()
        lh = c.h
        c.text_block([HEAD], y=lh * 0.40, size=lh * 0.058, color=AMBER,
                     max_w=c.w * 0.86)
        c.text_block(BODY, y=lh * 0.545, size=lh * 0.042, color=studio.WHITE,
                     alpha=0.92, max_w=c.w * 0.80)
        if a.sections:
            c.text_block([f"Flashing sections:  {'   '.join(a.sections)}"],
                         y=lh * 0.70, size=lh * 0.030, color=studio.WHITE,
                         alpha=0.62, max_w=c.w * 0.80)
        studio.save_still(c, a.out)
        print(f"still -> {a.out}  ({c.pw}x{c.ph})")
        return

    d = render(a.out, w, h, fps, a.dur, a.sections, a.crf)
    print(f"card -> {a.out}  {w}x{h}@{fps}  {d:.3f}s")


if __name__ == "__main__":
    main()
