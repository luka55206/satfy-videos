"""Title and chapter cards for long-form (16:9) videos: a short clip with a soft original chord.

    python tools/longform_cards.py --kind title   --line1 "FAMOUS NUMBERS" --line2 "π, φ & Fibonacci, visualised" --out output/card_title.mp4
    python tools/longform_cards.py --kind chapter --line1 "Chapter 1" --line2 "π: how Archimedes found it" --out output/card_ch1.mp4

Cards fade in/out from the same dark background the scenes use, so cuts between cards and chapters
are clean. Resolution follows NF_FAST/NF_SCALE like every scene.
"""
import argparse
import sys
from pathlib import Path

import cairo
import numpy as np
import soundfile as sf

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib import audio, studio  # noqa: E402
from lib.kit import DT, FPS, smooth  # noqa: E402
from lib.layouts import get_layout  # noqa: E402
from lib.studio import Canvas, VideoWriter  # noqa: E402

GOLD = (1.0, 0.82, 0.40)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kind", choices=("title", "chapter"), default="chapter")
    ap.add_argument("--line1", required=True)
    ap.add_argument("--line2", default="")
    ap.add_argument("--dur", type=float, default=0.0)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    dur = a.dur or (4.0 if a.kind == "title" else 2.6)
    L = get_layout("horizontal")
    c = Canvas(L.w, L.h, studio.render_scale())
    silent = Path(a.out).with_suffix(".silent.mp4")
    wr = VideoWriter(silent, c, FPS)
    nf = int(round(dur * FPS))
    for f in range(nf):
        t = f * DT
        al = smooth(t / 0.5) * (1 - smooth((t - dur + 0.5) / 0.5))
        g = cairo.RadialGradient(L.w / 2, L.h / 2, 0, L.w / 2, L.h / 2, L.w * 0.7)
        g.add_color_stop_rgb(0.0, 0.07, 0.06, 0.11)
        g.add_color_stop_rgb(1.0, 0.01, 0.01, 0.02)
        c.ctx.set_source(g)
        c.ctx.paint()
        if a.kind == "title":
            c.glow(L.w / 2, L.h * 0.42, L.h * 0.08, GOLD, strength=0.12 * al, reach=3)
            c.text_centered(a.line1, L.h * 0.46, size=L.h * 0.12, color=GOLD, alpha=al)
            c.text_centered(a.line2, L.h * 0.60, size=L.h * 0.055, color=(0.95, 0.94, 0.98), alpha=al, bold=False)
        else:
            c.text_centered(a.line1, L.h * 0.43, size=L.h * 0.045, color=GOLD, alpha=al)
            c.text_centered(a.line2, L.h * 0.55, size=L.h * 0.075, color=(1, 1, 1), alpha=al)
        c.watermark(L)
        wr.write_frame()
    wr.close()
    # a soft original chord (pad) under the card
    sr = audio.SR
    tt = np.arange(int(dur * sr)) / sr
    sig = np.zeros_like(tt)
    for m, amp in ((48, 1.0), (55, 0.7), (60, 0.5), (64, 0.35)):
        sig += amp * np.sin(2 * np.pi * audio.midi_to_hz(m) * tt)
    env = np.clip(tt / 0.4, 0, 1) * np.clip((dur - tt) / 0.6, 0, 1)
    wav = Path(a.out).with_suffix(".wav")
    st = (0.08 * sig * env).astype(np.float32)
    sf.write(str(wav), np.stack([st, st], 1), sr, subtype="PCM_24")
    studio.mux_audio(silent, wav, Path(a.out))
    silent.unlink()
    wav.unlink()
    print(f"[cards] {a.out} ({dur:.1f}s)")


if __name__ == "__main__":
    main()
