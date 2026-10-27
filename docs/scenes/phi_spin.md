# phi_spin — two arms, one φ times faster; the line never closes

Off-niche (channel niche is Peg Drop); owner request 2026-10-06, after reference
youtube.com/shorts/ZotkUx-PnIU. Only the maths was taken (public); look, HUD, caption and audio are ours.

- θ(t) is exponential: 2.5 → 110 rad/s over DRAW_S 40 s (181 turns). FADE_S 2.5 s dissolve to the
  frame-0 pose. FADE 1.6 left the end chord at −19 dBFS in the last 0.5 s; 2.5 gives −31.
- Trail lives on a persistent ADD-operator surface; per-segment alpha × (1 − 0.75u), or the disc
  burns out to white by 120 turns.
- Arms fade to 0.18 above ~45 rad/s, before they strobe at 60 fps.
- 9:16: caption post-pass `--loop dissolve --rebuild 2.5 --payoff 0 --fade 0.4 --cap-dy -0.05`;
  equation 0.172h, φ 0.200h, disc 0.233-0.706h, counter 0.765h.
- add_caption prints the caption: set PYTHONIOENCODING=utf-8 when it contains φ (cp1252 console crash).
- v2: near-miss zooms at F = 13/55/144 turns. The miss is the SIDEWAYS offset (the tip returns
  almost along the first stretch): use closest(F), not |Z(2πF) − start|. That gives
  0.0068 / 0.00038 / 0.000056 → zoom 88x / 1,576x / 10,800x for a 0.6-arm miss on screen.
  Deep zoom re-traces culled runs at ~2 px per sample (coarse SUB samples show chords above ~6 px).
  Zooms pause the base clock: TZ 4.8 s each, total 56.9 s.
- v3 (owner: zoom earlier, speed up after zoom, shorter): F = 5/21/89, W0 5 rad/s, DRAW_S 33,
  TZ 4.0, RAMP 1.2, JUMP_S 3.0 (base clock skips ahead after each zoom). 38.5 s; first zoom at 4.6 s.
