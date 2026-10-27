# mandel_dive — Mandelbrot dive to a self-similar minibrot (loop)

Owner request 2026-10-07 after youtube.com/shorts/0L13yN_zFak. Only the maths was taken.

- Target: period-38 minibrot at 0.2850037975659808 + 0.01060078045573048i (Elephant Valley).
  Found by atom-domain period scan + Newton on f_c^p(0) = 0; size S = 1/(β λ²) gives
  |S| = 3.0e-7 (zoom ×3.3M) and arg S = 147°.
- Exact loop camera: end centre = T + S·C0, scale |S|·scale0, rotation R0 + arg S. The last
  frame is near-identical to frame 0; a 2 s dissolve closes it.
- Rendering: numba prange kernel (pip numba 0.68); 540x960 preview ≈ 4 min for 20.5 s.
- Flash: palette cycling on log(n) over a bright sky FAILED at the fastest zoom. Fix: sky darkened
  to the 35th percentile of the frame's counts plus a slower palette (0.38/log-unit).
- FADE 1.3 left the arrival chord at −20.7 dBFS at the seam; 2.0 gives −28.6.
- Superseded by scenes/mandel_graph.py (owner 2026-10-07: zoom OUT, graph look). Real-axis copies
  are exactly upright but the antenna is empty black for most of the zoom; use the period-22
  Elephant Valley copy (6° tilt, ×518k). HUD must be ON at frame 0, or the seam breaks (3.2).
  Post-encode seam delta reads ~2.9 on the contour detail even with identical frames: check pre-encode.
- mandel_graph v2 NONSTOP loop: constant log-zoom speed + self-similar camera
  centre(d) = FIX + (C0 − FIX)·S^d, FIX = nucleus/(1 − S), scale |S|^d. The last 1.2 s blends the
  view at d with the view at d+1 (still moving). Judge the seam as the last→first step vs interior
  steps (≈14.5 here), not against check_clip's static-loop range.
