# fourier_eagle

- Hand-authored outline in code (`eagle_outline()`: Catmull-Rom head/wings, scalloped feathers, five-feather tail), resampled to 4096 points, mean-centred. DC term must be removed or the fit plateaus at ~3.3 % error.
- x(t) and y(t) are separate real Fourier series (k = 1..200); each term is one circle of a chain (biggest first). Tip x of the red chain = pen x, tip y of the blue chain = pen y.
- Timeline: rounds N = 5/20/60/200 at 0/3/6/9 s (draw 2.6/2.6/2.6/3.6 s), finish 13 s (flash + RWB fill + text), 14-15 s the circle count falls 200 -> 5 exponentially = loop. Measured error 3.85/1.63/0.18/0.02 %.
- Preview: `NF_FAST=1 python scenes/fourier_eagle.py` (12-18 s). 4K only after the owner approves.
- Sound is `build_bed()` (synth cry, snare, brass) folded over the seam by `kit.deliver_loop`; 120 BPM x 30 beats = 15 s.

- v2 (2026-10-21): the owner wanted the exact reference eagle. It is a watermarked Adobe Stock illustration, so it is NOT traced (project rule: no stock art). scenes/eagle_shape.py draws an original flag-coloured eagle from procedural feathers (needs shapely); silhouette = union of all feather polygons, traced by the epicycles; the inked version is painted once into a cached surface and faded in at the finish. Errors 2.73/1.36/0.37/0.07 %. If the owner licenses the stock file and supplies it, check the licence allows derivative use in video before tracing it.

- v3 (2026-10-21, owner: 'make inlines, no colouring'): the pen path = silhouette ring + inline strokes (eagle_shape.lineart(): visible feather edges after painter's-order occlusion, quills, chest scales, beak/eye/brow, greedy stroke order). Pen-up travel is masked (faint at N<=60, hidden at N>=200). Inlines need ~1500 circles (error 0.02 %); K=200 only gives 0.52 % and smears the details. Reconstruction via irfft of truncated spectra (32768 samples). Stages 5/20/60/200/1500, loop 18 s = 36 beats at 120 BPM. Preview renders in ~45 s.

- v4 (2026-10-21, owner: 'white line is bad at the end, USA colours'): the finish fades in es.paint() (cached surface) over the white line art, the chains/guides/pen fade to 8 % while it shows, the white lines drop to 8 % and return as the colour fades (16.0-16.5 s) for the unwind. Seam 0.63.

- 4K render (2026-10-21): python scenes/fourier_eagle.py -- --label 4k with NF_SCALE=2.0, 211 s. 2160x3840 h264 yuv420p 60 fps 1080 frames, seam 0.38, 0 flashes, compliance 0 FAIL. Staged in final/ready-to-upload/fourier_eagle/ (the low-res preview was replaced).
