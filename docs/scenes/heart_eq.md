# heart_eq — the heart equation, a grows 0 -> 20

Off-niche (channel niche is Peg Drop); owner request 2026-10-06.

- Equation: y = x^(2/3) + 0.9 sin(aπx) √(3.3 − x²), |x| ≤ √3.3; N_PTS 4200 covers ~37 waves at a = 20.
- a(t) = 20·(0.55u + 0.45u²), u = t/22 s → rate climbs 2.6x. HOLD 0.7 s, BACK 2.2 s (a eases to 0
  = exact frame 0). Total 24.9 s.
- Audio: glassharp note per +0.5 of a, D-major chord at a = 20, opening D pair at t=0.02, sine pad
  bed (`pad()`). Events/5s 9, 11, 13, 13; LUFS −14, last 0.5 s −57.6 dBFS.
- 9:16 top band (to ~0.16h) is reserved for the quote caption: equation at 0.196h, a readout
  0.233h, graph top 0.25h.
- Caption post-pass: `--loop constant --cap-dy -0.05` (9:16), span colours pink/gold.
- v1 shipped caption: "Even ~math~ knows how to ~love~ / Watch the waves become a heart".
