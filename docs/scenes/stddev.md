# stddev scene notes

- `python scenes/stddev.py -- --balls N --seed S [--rows R] [--drop-s SEC]` (run.ps1 -SceneArgs drops nothing useful here; call python directly, NF_FAST=1 for low-res).
- Galton (binomial) model, NOT the physics pegdrop: pegdrop's collisions pile balls on the walls, counts came out near flat.
- Rows by N (`ROWS_FOR`): 100:10, 500:14, 1000:16, 2000:18, 5000:20. Drop time `--drop-s` default 17 s for N>150 (ramp 0.2 s -> solved floor over the first 40% of balls); total clip ~ drop-s + 7.7 s.
- N>150: real balls hex-packed in taller cups (BIN_H_BIG), pile ball radius solved from the largest bin, falling ball radius ~ (100/N)^0.25 shrinking to it on landing, tube shows 6 balls, chimes/knocks thinned.
- End reveal = textbook diagram: bell curve, shaded area under it within 1 and 2 sigma, +-sigma lines (full height + down from the curve), dots at the inflection points. No mean line, no text anywhere (owner, 2026-10-05). Channel watermark: SatFy.
- Loop: bins/tube are constant, only balls/piles/curve fade, so frame 0 == last frame (seam delta 0.18-0.26).
- 5000 balls TODO: per-frame redraw of every settled stripe (5000 rects x ~1500 frames) will be slow at 4K; cache settled stripes; up to ~17 balls/frame spawn at drop-s 17.
- Seeds: pick by lowest chi-square against the exact binomial (all are real draws).

- Series 1000/2000/5000 (owner 2026-10-05): 1000 = uneven on purpose (--skew 0.25 --skew-rows 7, seed 2), 2000 = slightly off (--skew 0.12 --skew-rows 4, seed 2), 5000 = clean draw (seed 2, closest of 8). Skew forces that share of balls right over the last K rows; pile-vs-fitted-curve gap 19% / 8% / 2% of the tallest bin. Settled balls are cached on a layer (_packed_piles), 5000 low-res renders in ~30 s. Slow ramp capped at 250 balls so 5000 fits ~17 s of drops.

- Long-form mix (owner 2026-10-05): 16:9 4K via NF_ORIENT=horizontal (board stretched sideways, kx=auto_kx, one orientation per run), order 1000,100,2000,500,5000 + scenes/stddev_outro.py, joined with tools/build_stddev_mix.py (1 s xfade + acrossfade). 4K board render 5-8 min each (3 in parallel), mix encode ~3 min. Package: final/needs-review/stddev_mix/.

- Outcome (owner-reported 2026-10-05, not verified in Studio): the five Shorts (100/500/1000/2000/5000 balls) are on YouTube, each over 1000 views. The uploaded files in final/uploaded/ are the 540x960 low-res test renders. Per-video numbers still to pull with the youtube-analytics skill.

- regress (linear regression on springs): scenes/regress.py, 4K Short staged in final/needs-review/regress_n30s7_9x16.mp4. Same hum intro/pentatonic notes as the board clips, dropper on a rail instead of the pusher tube.

- Measured outcome (Studio export 2026-10-20, reports/2026-10-20_report.txt): ball deviation x5 = 8,023 views total (1.4k-2.0k each, stayed 32-44 %, 7 subs); regression 1,493, sine/cosine 1,623 (stayed 37-39 %, 0 subs); the 132 s ball long-form 81 views. Channel Shorts median 4,448, stayed-to-watch correlation with views +0.74. Verdict: dead formats, no more of this family.
