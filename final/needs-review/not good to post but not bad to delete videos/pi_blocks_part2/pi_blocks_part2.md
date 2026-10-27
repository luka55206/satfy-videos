# pi_blocks_part2 — upload metadata (YouTube Short, 9:16)

On-screen quote (baked): **Part 2: 100,000,000 kg. / Count the hits: π**
HOOK: no slow start — the blocks start touching at the wall, so the clicks begin on frame 0 and the counter races
(≈7,000 hits per second, the clicking turns into a buzz); the mass slams in big; a live "per second" meter.
Round 1: M = 100,000,000 kg → 31,415 collisions → π = 3.1415… · Round 2: M = 10,000,000,000 kg → 314,159 → π = 3.14159…
The why-π circle fills with chords (θ = 0.00573°, then 0.000573°). Cross-fades back into frame 0 (seamless loop).
End message: "Follow for part 3".

## Title (pick one)
1. These blocks compute π: part 2 🤯 (recommended — the part-1 pinned comment promised exactly this)
2. 100,000,000 kg block vs a wall: 31,415 hits 🤯
3. 314,159 collisions spell π 🤯

## Description
Part 2: make the big block 100,000,000 kg and it hits 31,415 times, 10 billion kg and it hits 314,159 times: the digits of π. #math #pi #physics

## Tags
pi, colliding blocks, digits of pi, physics, elastic collision, math, science, satisfying math

## Pinned first comment
Part 3: 1,000,000,000,000 kg → 3,141,592 collisions. Should I do it? 👇

## Upload settings
- Video language: English · Title/description language: English · Category: Education
- Altered or synthetic content: **No** (stylised 2-D physics animation)
- Made for kids: No
- Music/sound: synthesised clicks + chimes. Do not select or credit any YouTube audio track.
- Related video: pi_blocks (part 1).

## Notes (not for upload)
- `scenes/pi_blocks2.py --label prodbase` (new scene; part 1 untouched), NF_CRF=12 → caption/CTA --crf 12.
- 4K h264 yuv420p 2160x3840 60fps, 876 frames, 14.6 s | LUFS −14.01, peak −7.7 dBFS | flashes 0 | seam 0.14.
- Exact event-driven simulation: 31,415 and 314,159 collisions computed (Galperin 2003). The video clock follows the
  collision count (so the counter races from frame 0); positions are the exact simulated ones.
- compliance_check: 0 FAIL, 0 WARN.
