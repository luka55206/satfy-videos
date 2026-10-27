# pi_blocks — upload metadata (YouTube Short, 9:16)

On-screen quote (baked): **Two blocks crash into a wall. / Count the hits: π**
Opening (hook): M = 1 kg slides into m = 1 kg on frame 0's heels; clicks start within half a second.
Exact elastic simulation, no friction: M = 1, 100, 10,000, 1,000,000 kg → 3, 31, 314, 3141 collisions, then
"π = 3.141…". The "why π?" panel: the velocities as a dot on a circle — every collision is a chord turning it by the
same angle θ, so about π/θ chords fit (3141 chords fill the circle). End message: "Follow for more hidden π".

## Title (pick one)
1. Two blocks crash into a wall. Count the hits: π 🤯 (recommended)
2. These blocks compute π 🤯
3. 3, 31, 314, 3141: the collisions spell π

## Description
Two blocks and a wall, no friction. Make the big block 100 times heavier each time and the number of collisions spells π: 3, 31, 314, 3141. Why? Every bounce turns the velocities by the same tiny angle around a circle. #math #pi #physics

## Tags
pi, colliding blocks, physics, elastic collision, digits of pi, math, science, satisfying math

## Pinned first comment
Next: 100,000,000 kg → 31,415 collisions. Want to see it? 👇

## Upload settings
- Video language: English · Title/description language: English · Category: Education
- Altered or synthetic content: **No** (stylised 2-D physics animation)
- Made for kids: No
- Music/sound: synthesised (clicks + chimes + pad). Do not select or credit any YouTube audio track.
- Related video: π plays Pachelbel's Canon (same π audience).

## Notes (not for upload)
- `scenes/pi_blocks.py --label prodbase`, NF_CRF=12 → add_caption --crf 12 → add_cta --crf 12.
- 4K h264 yuv420p 2160x3840 60fps, 900 frames, 15.0 s | LUFS −14.01, peak −5.9 dBFS | flashes 0 |
  seam 9.8 = the experiment resetting from round 4 to round 1.
- Result is public mathematics (Galperin 2003); presentation, "why" panel, sound and words are ours.
- compliance_check: titles, description, tags and --scenes: 0 FAIL, 0 WARN.
