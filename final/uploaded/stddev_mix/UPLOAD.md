# stddev_mix_16x9 - 4K 16:9 long-form, 2:11 - awaiting owner verdict

Five boards in ascending order: 100 -> 500 -> 1000 (deliberately uneven) -> 2000 (slightly off) -> 5000 (almost perfect), then an outro that draws all five piles on one axis (each rescaled to its own middle and spread) with the ideal bell curve drawn over them. Reorder = rebuild only (a few minutes): `tools/build_stddev_mix.py` + `scenes/stddev_outro.py --order`.

## How it is joined (not a concat)
- Each board ends drained with the tube refilled and starts empty with the hum, so every junction is a 1 s crossfade of two empty boards: pegs appear, the counter changes, the old tune rings out while the next hum rises (audio crossfade, no restart).
- Each board is stretched sideways so the 16:9 frame is filled; captions/counter sit in the side panels.
- The outro reprises the opening hum under a resolved chord when the ideal curve lands.
- One known rough spot: during a crossfade the two counters / captions overlap for ~0.3 s.

## Checks
3840x2160, h264 yuv420p 60 fps, 131.5 s. LUFS -14.07, 0 flashes, compliance 0 FAIL. Runtime is under the 8:00 mid-roll floor (owner asked for this video, not a pool compilation). Watermark: SatFy.

## Title options (long-form, no emoji)
- 5 Ball-Drop Boards, One Bell Curve: Which Fits Best? [question]
- Standard Deviation Explained With 5000 Falling Balls [number]
- 100 vs 5000 Balls: Which Pile Is Closest to Perfect? [challenge]

## Description
Five peg-board simulations, from 100 to 5000 balls. Each ball goes left or right at every peg, and the piles are compared with the ideal bell curve (the shaded areas mark 1 and 2 standard deviations). The 1000- and 2000-ball boards are deliberately nudged so their piles do not match the curve; the others are plain random runs. Everything is simulated by code - no footage, no AI voice, original sound.

0:00 100 balls
0:20 500 balls
0:43 1000 balls
1:07 2000 balls
1:32 5000 balls
1:57 All five on one chart

## Tags
standard deviation,bell curve,normal distribution,galton board,bean machine,ball drop,peg board,probability,statistics,simulation

## Thumbnails
thumbnail_A.png (5000 balls, one bell curve), thumbnail_B.png (which fits?) - 1920x1080.

## Pinned comment
Which board did you think was closest to the ideal curve? The 1000- and 2000-ball runs are the ones we nudged on purpose.
