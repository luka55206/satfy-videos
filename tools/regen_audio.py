"""Re-generate a clip's soundtrack from its events sidecar — NO re-render.

The audio-cheap / visual-expensive lever (same idea as blender-physics
regen_sfx.py): tweak voice/params, remix in seconds, mux onto the existing
video with -c:v copy.

Usage:
  python tools/regen_audio.py <clip.mp4> [--voice marimba|glassharp]
                              [--foley 0.0] [--foley-kind thump|glassbreak]
                              [--suffix _x] [--width 1080] [--inplace]
                              [--intro auto|note|riser|off] [--intro-gate 0.40]
                              [--intro-riser 0.80] [--intro-gain 0.55]
Expects <clip-stem>_events.json next to the clip (output/ convention).
--inplace replaces the clip's audio in the same file (via a temp file).
"""
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib import audio, studio


def _arg(flag, default):
    a = sys.argv
    return a[a.index(flag) + 1] if flag in a else default


def main():
    clip = Path(sys.argv[1]).resolve()
    voice = _arg("--voice", "marimba")
    foley = float(_arg("--foley", "0.0"))
    foley_kind = _arg("--foley-kind", "thump")
    inplace = "--inplace" in sys.argv
    suffix = _arg("--suffix", "" if inplace else f"_{voice}")
    width = float(_arg("--width", "1080"))
    # --intro: fill a SILENT HEAD (see lib.audio.intro_layer). Opt-in; off
    # leaves the mix bit-identical. auto = note under --intro-riser, riser over.
    intro_mode = _arg("--intro", "off")
    intro = None
    if intro_mode != "off":
        intro = dict(gate_s=float(_arg("--intro-gate", "0.40")),
                     riser_s=float(_arg("--intro-riser", "0.80")),
                     gain=float(_arg("--intro-gain", "0.55")))
        if intro_mode == "note":
            intro["riser_s"] = 1e9      # never reach the riser branch
        elif intro_mode == "riser":
            intro["riser_s"] = 0.0      # always riser
        elif intro_mode != "auto":
            sys.exit("--intro must be auto|note|riser|off")

    stem = clip.stem  # e.g. grow_ball_5_9x16
    events_path = studio.OUT_DIR / f"{stem}_events.json"
    if not events_path.exists():
        sys.exit(f"events sidecar not found: {events_path}")
    events = audio.load_events(events_path)

    probe = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(clip)],
        capture_output=True, text=True, check=True)
    dur = float(probe.stdout.strip())

    wav = studio.OUT_DIR / f"{stem}{suffix}_regen.wav"
    audio.render_soundtrack(events, dur, wav, width_px=width, voice=voice,
                            foley_gain=foley, foley_kind=foley_kind,
                            intro=intro)

    if inplace:
        tmp = Path(tempfile.mkdtemp()) / clip.name
        studio.mux_audio(clip, wav, tmp)
        tmp.replace(clip)
        out = clip
    else:
        out = clip.with_name(f"{stem}{suffix}.mp4")
        studio.mux_audio(clip, wav, out)
    wav.unlink(missing_ok=True)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
