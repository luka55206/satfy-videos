"""Draw the rule caption ONTO a finished clip (no re-render).

STANDING RULE (Luka, 2026-08-10): a new scene renders WITHOUT its caption and
gets it from this tool afterwards, so rewording costs one cheap re-encode
instead of re-drawing every frame. A one-word edit on chaos_fan cost a full 4K
re-render of both orientations, which is what prompted it. Same principle the
channel already applies to sound — `regen_audio.py` / `add_rewind_sfx.py` exist
so the soundtrack is changeable without a re-render; text has no business being
less changeable than audio.

**KEEP THE CAPTION-LESS BASE. `--inplace` DESTROYS IT.** The whole point of this
pass is that text costs one cheap encode instead of a re-render — but --inplace
overwrites the base with the captioned file, and a caption cannot be un-baked, so
the NEXT text or size change costs a full 4K re-render of both orientations. That
happened on survivor v5 -> v6 for a font-size nudge (Luka, 2026-08-12: "why the
fuck it requires rerender"). Render to `<name>base_<tag>.mp4`, pass `--out`, and
keep the base until the clip is uploaded.

Render the base clip with `--rule ""` (every scene already routes its caption
text through that flag, and `Canvas.caption("")` draws nothing), then:

  python tools/add_caption.py <clip.mp4> --rule "240 pendulums" --inplace \
      --loop rewind --rebuild 2.6 --payoff 0.8

Why it is built this way, all of it load-bearing:

  - It draws through `Canvas.caption()`, the SAME call the scenes use, so the
    Arial-bold weight, the soft shadow, the auto-fit shrink and both layouts'
    anchors are identical to a baked caption by construction. ffmpeg `drawtext`
    matches none of those and is not an option.
  - The caption is rendered ONCE at alpha 1 onto a transparent sheet and then
    composited per frame at that frame's alpha. Both the text and its 0.45
    shadow scale linearly with alpha, so this is exactly equal to drawing it at
    that alpha, and it costs one text layout for the whole clip instead of 1,524.
  - Alpha is a pure function of the SOURCE FRAME INDEX, reconstructed from the
    loop parameters the same way `add_rewind_sfx.py` reconstructs its scrub
    curve. That is what keeps the loop seam exact: the caption fades in over
    --fade and is back to EXACTLY 0 on the last frame, so frame 0 and the last
    frame both get nothing drawn on them.
  - Video is re-encoded (unavoidable — the pixels change), audio is copied
    through untouched, and NO -shortest: it discards the last few video frames
    against the AAC stream length and breaks the loop's frame-0 landing.

Order in the pipeline: render -> THIS -> [16:9 only] megamix_intro.py -> audio
passes. The intro slides its big title into the caption's slot and hands off
pixel-matched, so it has to run after the caption exists.
"""
import argparse
import math
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import cairo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dataclasses import replace

from lib.layouts import get_layout
from lib.studio import CAP_SIZE_F, PALETTE, Canvas

SPAN_COLORS = {"cyan": PALETTE[0], "blue": PALETTE[6], "pink": PALETTE[1],
               "lime": PALETTE[2], "orange": PALETTE[3], "violet": PALETTE[4],
               "yellow": PALETTE[5], "red": PALETTE[7], "magenta": PALETTE[9]}


def _one_span_color(s):
    if s in SPAN_COLORS:
        return SPAN_COLORS[s]
    try:
        r, g, b = (float(v) for v in s.split(","))
        return (r, g, b)
    except ValueError:
        sys.exit(f"[add_caption] --span-color {s!r}: use a name "
                 f"({'/'.join(sorted(SPAN_COLORS))}) or 'r,g,b' floats")


def parse_span_size(s):
    """'' -> 1.0, '1.35' -> 1.35, '1/1/1.35' -> [1.0, 1.0, 1.35].

    A list is handed to the ~spans~ in order of appearance and cycles, exactly
    like --span-color — so '1/1/1.35' over three spans enlarges only the third.
    """
    if not s:
        return 1.0
    parts = [t.strip() for t in s.split("/") if t.strip()]
    try:
        vals = [float(t) for t in parts]
    except ValueError:
        sys.exit(f"[add_caption] --span-size {s!r}: use a number or "
                 f"slash-separated numbers ('1/1/1.35')")
    return vals[0] if len(vals) == 1 else vals


def parse_span_color(s):
    """'' -> None, one colour -> (r,g,b), 'a/b' -> [(r,g,b), ...].

    A list is handed to the ~spans~ in order of appearance and cycles, so
    'yellow/red' over "Lowest ~color~ is ~ERASED~ / Last ~color~ standing"
    paints both instances of color yellow and ERASED red."""
    if not s:
        return None
    parts = [t.strip() for t in s.split("/") if t.strip()]
    if len(parts) == 1:
        return _one_span_color(parts[0])
    return [_one_span_color(t) for t in parts]

FPS = 60
DT = 1.0 / FPS


def _smooth(p):
    p = 0.0 if p < 0.0 else (1.0 if p > 1.0 else p)
    return p * p * (3.0 - 2.0 * p)


def probe(path):
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_packets",
         "-show_entries", "stream=width,height,nb_read_packets",
         "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True)
    w, h, n = r.stdout.strip().split(",")
    return int(w), int(h), int(n)


def has_audio(path):
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries",
         "stream=index", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True)
    return bool(r.stdout.strip())


def alpha_curve(total, fade, loop, rebuild, payoff):
    """alpha[f], reconstructing the scene's own index map.

    rewind  — the ending replays indices backwards, so alpha follows the index
              back down to 0 on its own.
    dissolve— the ending holds the last index and multiplies alpha by (1-e).
    none    — no loop ending; alpha just fades in and stays.
    constant— NO fade at all, alpha 1 on every frame. For PERFECT loops (zoom /
              wrap): a caption that fades IN marks frame 0 as "the start" and
              one that fades OUT marks the seam as "the end", which is exactly
              the tell the loop exists to hide. The seam is still safe because
              what it requires is that frame 0 and the last frame MATCH — 1 and
              1 qualifies as well as 0 and 0. Only for an ending that lands
              pixel-exact on frame 0; a rewind/dissolve needs its fade.
    """
    if loop == "constant":
        return [1.0] * total
    rew = int(round(rebuild * FPS))
    hold = int(round(payoff * FPS))
    nf = total - hold - rew if loop != "none" else total
    if nf < 1:
        sys.exit(f"[add_caption] {total} frames minus hold+rewind leaves {nf}")
    out = []
    for f in range(total):
        k = 1.0
        if f < nf:
            idx = f
        elif f < nf + hold:
            idx = nf - 1
        else:
            e = _smooth((f - nf - hold + 1) / max(rew, 1))
            if loop == "rewind":
                idx = int(round((1.0 - e) * (nf - 1)))
            else:
                idx = nf - 1
                k = 1.0 - e
        out.append(min(idx * DT / max(fade, 1e-6), 1.0) * k)
    return out


def caption_sheet(w, h, rule, cap_size=CAP_SIZE_F, cap_dy=0.0,
                  span_color=None, span_scale=1.0, line_gap=1.22):
    """The caption alone, at alpha 1, on a transparent sheet."""
    layout = get_layout("vertical" if h > w else "horizontal")
    if cap_dy:
        # shift the whole caption ANCHOR rather than the draw call, so
        # anything else reading layout.cap_y agrees with what is drawn
        layout = replace(layout, cap_y=layout.cap_y + cap_dy * layout.h)
    canvas = Canvas(layout.w, layout.h, w / layout.w)
    if (canvas.pw, canvas.ph) != (w, h):
        sys.exit(f"[add_caption] {w}x{h} is not a {layout.tag} canvas "
                 f"(got {canvas.pw}x{canvas.ph})")
    ctx = canvas.ctx
    ctx.save()
    ctx.set_operator(cairo.OPERATOR_CLEAR)
    ctx.paint()
    ctx.restore()
    canvas.caption(rule, alpha=1.0, layout=layout, size_f=cap_size,
                   span_color=span_color, span_scale=span_scale,
                   line_gap=line_gap)
    canvas.surf.flush()
    return canvas.surf, layout


COUNT_SIZE = {"center": 0.18, "caption": 0.11}


def number_sheet(w, h, text, size_f, where="center", dy=0.0):
    """One big COUNT-IN number, alpha 1, on a transparent sheet.

    `where`:
      center  — the ARENA's vanishing point. The emptiest part of the frame
                during a soft open, so the number can be huge.
      caption — the CAPTION's own slot, so the count-in hands its space
                straight to the caption it precedes. Has to be much smaller
                (0.11 h against 0.18) to sit inside that band.
    """
    layout = get_layout("vertical" if h > w else "horizontal")
    canvas = Canvas(layout.w, layout.h, w / layout.w)
    ctx = canvas.ctx
    ctx.save()
    ctx.set_operator(cairo.OPERATOR_CLEAR)
    ctx.paint()
    ctx.restore()
    size = layout.h * size_f
    if where == "caption":
        cx, base, limit = layout.cap_x, layout.cap_y + size * 0.62, layout.cap_maxw
    else:
        cx, base, limit = (layout.arena_cx, layout.arena_cy + size * 0.34,
                           layout.w * 0.9)
    canvas.text_centered(text, base + dy * layout.h, size=size, alpha=1.0,
                         cx=cx, max_w=limit)
    canvas.surf.flush()
    return canvas.surf


def count_curves(total, labels, t0, t1, fade_in=0.09, fade_out=0.16):
    """-> ([alpha[f] per label], caption_gate[f]).

    Each label owns an equal slice of [t0, t1); it fades up, holds, and fades
    out into the next one. `caption_gate` is 0 until t1 and then ramps in, so
    the caption ARRIVES where the count-in leaves — which is the whole point of
    the count-in, and also the reason a clip using it is no longer an invisible
    loop (see the guard in main()).
    """
    n = len(labels)
    slot = (t1 - t0) / n
    curves = []
    for k in range(n):
        s, e = t0 + k * slot, t0 + (k + 1) * slot
        a = []
        for f in range(total):
            t = f * DT
            if t < s or t >= e:
                a.append(0.0)
            else:
                up = min((t - s) / max(fade_in, 1e-6), 1.0)
                dn = min((e - t) / max(fade_out, 1e-6), 1.0)
                a.append(_smooth(up) * _smooth(dn))
        curves.append(a)
    gate = [_smooth(min(max((f * DT - t1) / 0.25, 0.0), 1.0))
            for f in range(total)]
    return curves, gate


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("clip")
    ap.add_argument("--rule", required=True,
                    help="caption text; '\\n' splits into stacked lines")
    ap.add_argument("--out")
    ap.add_argument("--inplace", action="store_true")
    ap.add_argument("--loop", choices=("rewind", "dissolve", "none",
                                       "constant"), default="rewind")
    ap.add_argument("--rebuild", type=float, default=2.6,
                    help="the scene's REWIND_S / REBUILD_S")
    ap.add_argument("--payoff", type=float, default=0.8,
                    help="the scene's HOLD_S")
    ap.add_argument("--fade", type=float, default=0.6,
                    help="the scene's FADE_S")
    ap.add_argument("--crf", type=int, default=18)
    ap.add_argument("--cap-size", type=float, default=CAP_SIZE_F,
                    dest="cap_size",
                    help="caption font as a fraction of canvas height "
                         "(0.036 = the channel default). MUST match the "
                         "--cap-size given to megamix_intro.py for the "
                         "same clip, or the 16:9 intro title lands at a "
                         "different size than the caption it hands off to")
    ap.add_argument("--span-color", default="", dest="span_color",
                    help="colour for ~word~ spans in --rule (a palette "
                         "name or 'r,g,b' floats). SLASH-SEPARATE several "
                         "('yellow/red') to give consecutive spans different "
                         "colours, cycling. A clip using this must hand the "
                         "SAME markup+colour to megamix_intro.py")
    ap.add_argument("--span-size", default="", dest="span_size",
                    help="draw ~word~ spans at this MULTIPLE of the caption "
                         "size, on the same baseline. One number scales every "
                         "span; SLASH-SEPARATE to scale them individually in "
                         "order of appearance ('1/1/1.35' enlarges only the "
                         "third). Measured into the shrink-to-fit. A clip "
                         "using this must hand the SAME value to "
                         "megamix_intro.py --span-size")
    ap.add_argument("--line-gap", type=float, default=1.22, dest="line_gap",
                    help="baseline step between caption lines, as a MULTIPLE "
                         "of the base font size (1.22 default = the channel's, "
                         "bit-identical). The step is keyed to the BASE size, "
                         "so a whole LINE scaled up with --span-size grows "
                         "into the line above it: raise this until it clears "
                         "(hydro_press shr23: line 2 at 1.7x needs 1.75). A "
                         "clip using this must hand the SAME value to "
                         "megamix_intro.py --line-gap")
    ap.add_argument("--countdown", default="",
                    help="COUNT-IN before the caption, e.g. '3,2,1'. Each label "
                         "gets an equal slice of [--countdown-from, "
                         "--countdown-to] at the arena centre, and the caption "
                         "arrives at --countdown-to instead of frame 0. NOTE: a "
                         "clip using this is no longer an INVISIBLE loop — the "
                         "count-in marks frame 0 as the start by design")
    ap.add_argument("--countdown-from", type=float, default=0.0,
                    dest="countdown_from")
    ap.add_argument("--countdown-to", type=float, default=3.0,
                    dest="countdown_to",
                    help="when the last number leaves and the caption arrives. "
                         "Put it on a MUSICAL landmark (the drop), not on a "
                         "round number")
    ap.add_argument("--countdown-at", choices=("center", "caption"),
                    default="center", dest="countdown_at",
                    help="where the count-in is drawn: the arena's vanishing "
                         "point (big), or the caption's own slot so it hands "
                         "that space straight to the caption")
    ap.add_argument("--countdown-size", type=float, default=0.0,
                    dest="countdown_size",
                    help="count-in font as a fraction of canvas height "
                         "(default: 0.18 at center, 0.11 at caption)")
    ap.add_argument("--cap-dy", type=float, default=0.0, dest="cap_dy",
                    help="move the caption DOWN by this fraction of canvas "
                         "height (9:16 only, normally: it closes the gap "
                         "between the caption and the arena). Must match "
                         "megamix_intro.py's --cap-dy for the same clip")
    ap.add_argument("--after", type=float, default=0.0,
                    help="COMMENT-REPLY gate: the caption is 0 until this many "
                         "seconds, then fades in over --fade. For a scene that "
                         "draws the viewer's card in the caption slot first "
                         "(dice_ball: COMMENT_S + COMMENT_FADE_S). 0 = off, "
                         "bit-identical")
    ap.add_argument("--clear-last", type=float, default=0.0, dest="clear_last",
                    help="COMMENT-REPLY gate: the caption starts clearing this "
                         "many seconds before the end, fades out over "
                         "--clear-fade and stays 0 to the last frame, so a "
                         "perfect loop whose frame 0 carries the CARD (not the "
                         "caption) still matches at the seam. 0 = off, "
                         "bit-identical")
    ap.add_argument("--clear-fade", type=float, default=0.40, dest="clear_fade")
    ap.add_argument("--force-caption", action="store_true",
                    help="bake a caption that fails caption_check's HARD rules "
                         "(no ~highlight~, a viewer-prediction question, >2 lines, "
                         "an over-length line, a banned filler phrase). Luka can "
                         "override any rule -- but it has to be a CHOICE, said out "
                         "loud, not a rule quietly forgotten.")
    a = ap.parse_args()

    src = Path(a.clip)
    if not src.exists():
        sys.exit(f"[add_caption] no such clip: {src}")
    if not (a.out or a.inplace):
        sys.exit("[add_caption] pass --out or --inplace")
    rule = a.rule.replace("\\n", "\n")

    # EVERY caption on this channel is baked here, so this is the one place a
    # caption rule can actually be enforced instead of restated. See
    # tools/caption_check.py.
    # caption_check.py is not ported yet (its rules need this niche's corpus);
    # until it exists the check is skipped with a warning, not a crash.
    try:
        from caption_check import check as _caption_check
    except ImportError:
        _caption_check = None
        print("[add_caption] WARNING: tools/caption_check.py missing -- caption "
              "rules NOT enforced; check the wording by hand.")
    if rule.strip() and _caption_check is not None:
        if not _caption_check(rule, a.cap_size, force=a.force_caption):
            sys.exit("[add_caption] caption rejected -- fix the wording, or pass "
                     "--force-caption if this is a deliberate override.")

    w, h, total = probe(src)
    sheet, layout = caption_sheet(w, h, rule, a.cap_size, a.cap_dy,
                                  parse_span_color(a.span_color),
                                  parse_span_size(a.span_size), a.line_gap)
    alphas = alpha_curve(total, a.fade, a.loop, a.rebuild, a.payoff)
    if a.after > 0.0 or a.clear_last > 0.0:
        # pure functions of the frame index, like everything else here
        n_clear = total - int(round(a.clear_last * FPS)) if a.clear_last > 0.0 else None
        nf = max(int(round(a.clear_fade * FPS)), 1)
        gated = []
        for f, al in enumerate(alphas):
            g = 1.0
            if a.after > 0.0:
                g *= min(max((f * DT - a.after) / max(a.fade, 1e-6), 0.0), 1.0)
            if n_clear is not None and f >= n_clear:
                g *= max(0.0, 1.0 - (f - n_clear + 1) / nf)
            gated.append(al * g)
        alphas = gated
        print(f"[add_caption] gated: arrives {a.after:.2f}s (+{a.fade:.2f}s fade), "
              f"clears from frame {n_clear} over {nf} frames")

    labels = [t.strip() for t in a.countdown.split(",") if t.strip()]
    count_sheets, count_alphas = [], []
    if labels:
        csize = a.countdown_size or COUNT_SIZE[a.countdown_at]
        count_sheets = [number_sheet(w, h, t, csize, a.countdown_at)
                        for t in labels]
        count_alphas, gate = count_curves(total, labels, a.countdown_from,
                                          a.countdown_to)
        alphas = [al * g for al, g in zip(alphas, gate)]
        print(f"[add_caption] count-in {labels} at {a.countdown_at} "
              f"(size {csize:.3f} h) over "
              f"{a.countdown_from:.2f}-{a.countdown_to:.2f}s; the caption "
              f"arrives at {a.countdown_to:.2f}s. The loop is DELIBERATELY "
              f"marked at frame 0 — the seam-match guard is waived.")
    elif abs(alphas[0] - alphas[-1]) > 1e-9:
        # what the seam actually requires is that the two ends MATCH — 0/0 for
        # the fading modes, 1/1 for `constant`. A mismatch is silent seam
        # breakage, EXCEPT when a count-in has been asked for on purpose.
        sys.exit(f"[add_caption] caption alpha is {alphas[0]:.3f} at frame 0 "
                 f"and {alphas[-1]:.3f} at the last frame — they must be EQUAL "
                 f"or the loop seam breaks. Check --loop/--rebuild/--payoff.")

    tmp = Path(tempfile.mkdtemp()) / "captioned.mp4"
    dec = subprocess.Popen(
        ["ffmpeg", "-v", "error", "-i", str(src), "-map", "0:v:0",
         "-f", "rawvideo", "-pix_fmt", "bgra", "-"],
        stdout=subprocess.PIPE)
    enc_cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
               "-f", "rawvideo", "-pix_fmt", "bgra", "-s", f"{w}x{h}",
               "-r", str(FPS), "-i", "pipe:0"]
    if has_audio(src):
        enc_cmd += ["-i", str(src), "-map", "0:v:0", "-map", "1:a:0",
                    "-c:a", "copy"]
    enc_cmd += ["-c:v", "libx264", "-preset", "medium", "-crf", str(a.crf),
                "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(tmp)]
    enc = subprocess.Popen(enc_cmd, stdin=subprocess.PIPE)

    nbytes = w * h * 4
    drawn = 0
    for f in range(total):
        buf = dec.stdout.read(nbytes)
        if len(buf) < nbytes:
            break
        al = alphas[f]
        layers = [(sheet, al)] if al > 1e-4 else []
        for k, ca in enumerate(count_alphas):
            if ca[f] > 1e-4:
                layers.append((count_sheets[k], ca[f]))
        if layers:
            frame = bytearray(buf)
            surf = cairo.ImageSurface.create_for_data(
                memoryview(frame), cairo.FORMAT_ARGB32, w, h, w * 4)
            ctx = cairo.Context(surf)
            for sh, av in layers:
                ctx.set_source_surface(sh, 0, 0)
                ctx.paint_with_alpha(av)
            surf.flush()
            del ctx, surf
            enc.stdin.write(bytes(frame))
            drawn += 1
        else:
            enc.stdin.write(buf)
    enc.stdin.close()
    dec.stdout.close()
    if enc.wait() != 0 or dec.wait() not in (0, None):
        sys.exit("[add_caption] ffmpeg failed")

    _, _, out_n = probe(tmp)
    if out_n != total:
        sys.exit(f"[add_caption] packets {total} -> {out_n}; refusing to ship "
                 f"(a dropped frame breaks the loop's frame-0 landing)")
    dst = src if a.inplace else Path(a.out)
    shutil.move(str(tmp), str(dst))
    print(f"[add_caption] {dst.name}: {total} packets ok, caption on "
          f"{drawn} frames ({rule!r}), alpha {alphas[0]:.1f} at frame 0 == "
          f"{alphas[-1]:.1f} at the last frame")


if __name__ == "__main__":
    main()
