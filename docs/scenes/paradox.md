# paradox Shorts: the recipe (2026-10-25)

Owner verdict on v1 (horn, coastline v1, potato on stickman, zeno on stickman): "the idea is good but the video is not
interesting". Only the missing square landed. Compared with the viral ones (Zack D. Films coastline 35M, Lingualin
infinite chocolate 19M, Mark Rober rope 63M; research in reports/2026-10-25_paradox_shorts_research.txt):

1. The impossible result in the first 2-3 s ("65", "16 cm", "50 kg?!", "2 turns"), then the "how".
2. The camera never stops: push-ins, dives, a zoom into the detail for the reveal.
3. Real-looking objects: chocolate, a scale, coins, a rope around the Earth, a ruler. No abstract counters on their own.
4. One giant number that JUMPS (2,400 -> 160,000 km), not one that creeps.
5. One short line of text at a time; no speech bubbles or dialogue in paradox Shorts.
6. 15-17 s, the reveal by about 60%, hits (lib/sfx.Bed.hit) on every number, whooshes on every camera move.
7. The loop: return to the frame-0 state, and make sure the camera, the glow and the text all return too (several seams
   were > 1 only because the text or a glow differed on the last frame).
8. Big-area colour swaps during fast zooms trip flash_check: keep the land and water close in luminance and the
   textures fixed (never re-seed them per frame).

Scenes: paradox_square (v1, liked), paradox_choc, paradox_rope, paradox_coin, paradox_coast2, paradox_potato.
Shared SFX: lib/sfx.py.
