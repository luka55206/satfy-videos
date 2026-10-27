# Per-scene notes

One file per scene: `docs/scenes/<scene>.md`. Read it before editing a scene; record tuning lessons, shipped episodes (with their nameable change), and measured outcomes here.

## Nonstop loops (owner preference 2026-10-07)
The owner wants the end to flow into the start with no stop or fade. Use `kit.deliver_loop`
(note tails folded over the seam) + `kit.loop_pad` (exactly periodic pad) + `--loop constant`
captions. The motion design must carry the last frame into frame 0: a self-similar zoom
(mandel_graph) or a smooth rewind-dive (fib_spiral).

## Stay-to-watch evidence (owner's YouTube data, 2026-10-07)
heart_eq 56% (best) · trig 33.4% · the rest 30-34%. Goal: 70%+.
Read: the winner is RECOGNISABLE and EMOTIONAL from frame 0 (a heart is coming; the caption is
about love, not maths), with one payoff the eye waits for, and it is short (25 s). The abstract
formats (arms, waves, fractals) need decoding before the viewer cares.
Tests from this read: heart_beat (episode of the winner: it beats, bpm 72→190, relatable caption)
and sunflower (golden-angle seeds → a sunflower). Record their stay-to-watch here when measured.

## Highest-quality final encode
`add_caption.py` and `add_cta.py` re-encode at CRF 18 by default, which undoes a CRF 12-14 base. For the
upload copy, pass `--crf 12` to both and render the base with `NF_CRF=12` (heart_beat_v3: ~28 Mb/s at 4K).

## math_sounds (2026-10-09)
Sonification rule: pitch = height of the graph under the pen (continuous voices), discrete graphs ring a
note per jump. Part 1 (--part 1, default) and Part 2 (--part 2) shipped together. Raw fast oscillations
(the heart's sin 20πx) buzz at ~11 Hz: map pitch to the OUTLINE and put the wiggle in volume instead.

## Channel data, 2026-10-10 (owner's Studio screenshots in final/uploaded/<clip>/)
| clip | title used | published | views | stayed-to-watch | avg view / length | subs |
|---|---|---|---|---|---|---|
| fib_spiral_v2 | The golden ratio hides in this spiral ✨ | Oct 8 | **31,530** (still climbing, 28.7k in 48 h) | **69.5%** | 0:19 / 0:18 (>100%: rewatches) | +20 |
| phi_spin_v3 | They come so close… but never touch | Oct 7 | ~1.3k engaged, 628 unique | 62.8% | 0:30 / 0:39 | – |
| heart_eq_v1 | Can math fall in love? | Oct 7 | 1.8k | 60.9% | 0:19 / 0:25 | – |
| habit_race_v8 | Why consistency always beats talent | Oct 10 | 1.5k in 11 h | 50.5% (early) | 0:21 / 0:17 | +1 |
| mandel_graph_v2 | Zoomed out 518,000× and it's still the same | Oct 9 | 1.4k | 47.2% | 0:19 / 0:21 | 0 |
| sunflower_v1 | Why do sunflowers use 137.5°? | Oct 8 | 1.4k | 43.6% | 0:13 / 0:18 | +4 |
| heart_beat_v4 | Your heart when she texts back | Oct 9 | **167** | **19.1%** | 0:13 / 0:15 | 0 |
Traffic: 92-94% Shorts feed, 98-100% non-subscribers. Audience: male, 13-17 and 25-34 heavy, global
(US 1-13%, Philippines, Indonesia, Russia, Brazil, India). Search: fib 5% ("golden ratio").
Read: every Short gets a ~1-1.8k test batch; ~65-70% stayed-to-watch is the gate to wider reach
(only fib passed). <25% kills a Short in the first batch (heart_beat). The winner had a famous keyword,
frame-0 text that states the game (F(1) = 1, ratio = 1.0000000000), a number that changes every beat,
a visible finish line (digits turning gold = φ), 18 s, and a loop people rewatch.

## math_levels (2026-10-11)
Level ladder (16 levels + LEVEL MAX = phi_spin's curve). Shipped variant: --hook 1 --beat hardtekk:
payoff-first open inside the drop, levels on a 170 BPM grid (2 beats ×8, 1 beat ×8), 34 beats = the loop,
so picture and music loop seamlessly. Owner liked the hardtekk energy for this fast format; keep calm pads for
the calm formats.
