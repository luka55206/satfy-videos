# math_song_part2 — upload metadata (YouTube Short, 9:16)

On-screen quote (baked): **This song is 100% math / Part 2: 5 new functions**
HOOK: the video OPENS ON THE DROP — every lane full and pumping, the loudest part on frame 0; at 2.8 s a tape-stop
rewind ("<< how is this made?") snaps to #6 and the song builds back up layer by layer. The final drop flows straight
into the opening drop (the loop never breaks the music).
New song, new functions (D minor, Dm–C–Bb–C, 128 BPM):
  #6 Melody  y = floor(5 + 3 sin(πx/4) − 1.5 cos(πx)) · #5 Kick  y = 1 + 3e^(−16(x mod 1))
  #4 Bass  y = r[floor(x/4) mod 4] + 12·(floor(2x) mod 2) (octave jumps) · #3 Arpeggio  y = r + t[floor(4x) mod 4] (climbs)
  #2 Riser  y = floor(2^(x/2)) (exponential) · #1 THE DROP. End message: "Follow for part 3".

## Title (pick one)
1. This song is 100% math: part 2 🎵 (recommended)
2. 5 new math functions build a new song 🎵
3. Wait for the drop… it's just equations: part 2 🤯

## Description
Part 2: five new equations build a new song in D minor: the melody, the kick, an octave bass, a climbing arpeggio and an exponential riser. #math #music #edm

## Tags
math music, math song, equations, edm, music production, functions, satisfying math

## Pinned first comment
Which equation should be the drop in part 3? 👇

## Upload settings
- Video language: English · Title/description language: English · Category: Education
- Altered or synthetic content: **No** (stylised animation)
- Made for kids: No
- Music/sound: original, synthesised from the equations. Do not select or credit any YouTube audio track.
- Related video: math_song (part 1).

## Notes (not for upload)
- `scenes/math_song2.py --label prodbase` (new scene; part 1 untouched), NF_CRF=12 → caption/CTA --crf 12.
- 4K h264 yuv420p 2160x3840 60fps, 1069 frames, 17.8 s | LUFS −14.01, peak −5.2 dBFS | flashes 0 |
  seam 4.6 (drop → drop: the music is continuous; the lanes jump half a bar).
- compliance_check: 0 FAIL, 0 WARN.
