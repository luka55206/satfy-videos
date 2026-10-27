# count_infinity: long-form stickman counting journey (16:9, 9:48)

Brief: `ideas/2026-10-23_count_to_infinity_LONGFORM_PROMPT.txt` (arc, pacing, checked numbers).
Built 2026-10-23 as the channel's first real long-form test, after 3 compilation-style long-forms got 669 views total.

- Structure: 13 chapters in `CHAPTERS` (name, seconds); `T0` gives the start times, which are also the YouTube chapters.
  Each level's draw method is `ch_<name>(t, u)` and returns the counter dict; `REVEAL` holds the answer cards;
  `RUNGS` is the ladder.
- The speech lines in `_L` use chapter-local times. Hold each line >= 1.2 s after its last letter (CPS 21).
- `--at <seconds>` renders a still at a video time (easier than frame numbers on a 10-min video).
- Render: about 35k frames. Preview with `NF_FAST=1 NF_ORIENT=horizontal`; for 4K use `NF_SCALE=2.0`.
- Every number on screen is in the brief's HONEST NUMBERS list. Change a number there first.
