---
name: long-form
description: >
  Build the ~1-HOUR long-form video — a background/ambient cut assembled from
  clips that earlier COMPILATIONS already used, read in place, consuming
  nothing. Use whenever the owner asks for a "1 hour video", "hour-long
  compilation", "long-form N", "background / ambient / relax version" or
  "marathon". NOT the 8-10 min `compilation` (that one draws the unspent
  `final/uploaded/` pool and consumes it). Ships video + thumbnails + UPLOAD.md.
---

# Build a long-form (~1 hour)

~60 minutes of finished clips, cut for BACKGROUND / TV viewing rather than the
algorithm's first 30 seconds. Built only from clips in
`final/compilations/compilation N/`, so it needs no new renders and consumes no
inventory. Deliverables go in `final/long-form/long-form N/`: **video +
`MANIFEST.md` + `UPLOAD.md` + `thumbnail/` ONLY — no clip files.**

## Why it exists (parent-channel evidence — re-validate on this niche)

- Parent's 1-hour cut ran **RPM ~3.1x the 8-10 min compilation's** (~78x a
  Short's): ~96% of an average compilation's revenue from ~31% of its views.
- It held **~29% of viewers at the 8:00 mid-roll vs 14-24%** for compilations,
  because 8:00 is 13% into an hour and ~87% into a compilation.
- Ad revenue tracks WATCH TIME (mid-rolls served), not views; marginal cost is
  ~zero. **Cadence: one every 2 weeks.**
- **The risk is discovery** (lowest CTR of any long-form on the parent). An hour
  nobody clicks earns nothing — if compilations aren't landing, fix titles and
  thumbnails first; more minutes won't help. n=1 on the parent; treat as a
  hypothesis here.

## Long-form vs compilation

| | Compilation | Long-form |
|---|---|---|
| Runtime | 8-10 min, both ends hard | ~60 min |
| Pool | `final/uploaded/` (unspent) | `final/compilations/*/` (spent) |
| Consumes clips | yes, permanently | **no — read in place** |
| Head cards / black leads | none between clips | **trimmed off every clip** |
| Swish level | default | **~0.3** (80 cuts fatigue) |
| Title | genre-superlative | **search phrase, runtime first** |

## The reuse exception — and what keeps it authentic

"A clip lives in exactly one place" makes duplicates across COMPILATIONS
impossible; it does not bind this format, which deliberately reuses spent clips.

- Every frame is our own render, so copyright doesn't apply; compilations of a
  creator's own videos are a standard monetised format. **But the
  inauthentic/reused-content policy targets near-duplicate uploads**, so it MUST
  be a genuinely different product: **re-cut the order across compilation
  boundaries — if any compilation's running order survives intact, re-cut it**;
  background framing; a title/thumbnail selling an hour, not a best-of.
- **REFERENCE, never copy or move.** The compilation folder stays each clip's
  only home. `MANIFEST.md` names every source path; duplicating GBs of 4K
  masters buys nothing the manifest doesn't.

## Continuity: nothing black between clips

Continuity is the whole promise. On a TV a cut to black reads as buffering or
the end, and every early exit costs every mid-roll after it. So **strip any
per-clip opening card or black lead** before building (chapters come from the
description, not from cards).

- Measure each clip's lead (per-frame luma scan, `signalstats` YAVG) — the
  number of frames before its content starts. If clips share a known constant
  (e.g. a fixed baked intro), use the constant, verified by **frame counts**,
  never container durations.
- A head trim can't be a clean stream copy (off-keyframe): re-encode a trimmed
  copy into `output/long-form N/` (`-ss` after `-i` for frame accuracy, libx264
  crf 16, audio cut at N x 800 samples @48k/60fps), then assert the output
  frame count. Check: trimmed frame 0 vs source frame N, mean delta ~0.
- Apply the same dead-tail rule as the compilation skill (cut ~5 frames before
  a black loop tail, never earlier).
- A clip opening on its own caption fade-in after the trim is correct.

## Selection and ordering

1. **Source = the numbered 16:9 files in `final/compilations/compilation N/`.**
   Skip the built compilation video and the warning card. **Skip any non-PD
   music clip** (check each against the custom bank — no guard tool yet).
2. **Target ~60 min**, summed from frame counts AFTER trims. Archive short →
   **say so and stop.** Never pad; never borrow from `final/uploaded/` (that is
   the next compilation's pool).
3. **Re-cut across compilation boundaries** — interleave; no run survives.
4. A scene type may repeat across an hour, **never within ~10 minutes of
   itself**.
5. **Vary melody and key between neighbours** — two adjacent clips sharing a
   tune is the one thing a background viewer WILL notice.
6. Alternate dense/sparse and colour theme; keep the harshest clips apart.
7. **Lead with the highest stayed-to-watch clip** — the first 30 s still decide
   whether anyone stays.

## Build steps

1. **Scratch staging `output/long-form N/`** — trimmed clips live here, as
   `NN_<name>_16x9.mp4` in play order. Sources are READ ONLY.
2. **Trim** heads/tails into it (above).
3. **Warning card (conditional, no timestamps)**:
   `python tools/warning_card.py --scan <staged clips in order> --out "output/long-form N/00_warning_card.mp4" --report "output/long-form N/flash-report.json" --no-sections`
   — written only if a clip fails; at ~80 clips a timestamp list is a wall of
   numbers, so the text alone. Never disable it.
4. **Create `final/long-form/long-form N/`** for deliverables only.
5. **Build**:
   `python tools/build_compilation.py --out "output/long-form N/long_form_16x9.mp4" --clips <card>,<01>,<02>,...`
   Caveats for an hour with the current tool: the swish gain is hard-coded
   (0.95 in `load_transition`) — there is no `-WhooshGain` yet, so either
   accept it or ask the owner to approve a small flag edit; whoosh positions use
   container durations and **drift accumulates over ~80 cuts**; the whole hour
   is mastered in one float buffer (~1.4 GB RAM). Verify hard (step 6); if cuts
   drift, the fix is the sample-exact builder below, not ignoring it.
6. **Verify — measure, never eyeball**: spec (h264 / 3840x2160 / yuv420p /
   60 fps / stereo 48k AAC); A/V diff < 50 ms; no PTS gaps (packet delta <=
   1.5/60); swish at EVERY cut — first, middle and last included (an early-cut
   miss with late cuts landing = duration drift); **no black lead after any
   cut** (a missed trim); runtime within a couple of minutes of 60:00; size
   plausible (~57-67 MB/min at 4K). Then MOVE the video into
   `final/long-form/long-form N/`.
7. **Chapters**: one per clip at frame-count cut times, rounded down, first at
   0:00, **every chapter >= 10 s** (one short entry kills the whole list) — fold
   the 3s card into chapter 1.
8. **Thumbnails** — do NOT default to the compilation's before→after formula:
   it promises one moment the viewer can't find in an hour. **Trade CTR for
   watch time on purpose.** Ship **three different designs for Test & Compare**
   (it scores watch-time share — the metric that matters): **mosaic** (grid of
   clips + "1 HOUR / N ..."; keep this one visually loud), **hero** (one
   full-bleed frame + "1 HOUR"), **use-case** ("NO TALKING", "RELAX · STUDY ·
   SLEEP"), plus one before→after as the control. Crop past baked HUD (zoom
   ~2x on tiles); pick tiles from a contact sheet at the final crop. ~15-20
   candidates, PNG only, numbers read off frames, in `thumbnail/`.
9. **Metadata — `UPLOAD.md` AND chat**: **search-phrase title, runtime + genre
   first, no emoji**; description opens with the photosensitivity line only if
   the card fired, then chapters. **Note: ENABLE mid-rolls** — that step carries
   the revenue case. Auto placement is near-ideal here (every cut is a natural
   break); only check none lands in the first ~2 min.
10. **`MANIFEST.md`**: order, trimmed durations, and the **FULL SOURCE PATH** of
    every clip (`final/compilations/compilation N/NN_<name>_16x9.mp4`) — the
    only way to rebuild it.
11. **Delete `output/long-form N/`** once the video is verified and moved.

## Hard rules

- 16:9 only. No clip files in `final/long-form/`. Never modify sources.
- Never leave a head card or black lead in. Never draw from `final/uploaded/`.
- PD-only audio. Conditional warning card, never disabled.
- **HARD STOP after build + verification — the owner reviews before upload.**
- No git commits — the owner commits.

## Tooling to build once the niche is chosen

- **Head/tail trimmer** (parent: `trim_intro.py` + `tail_trim.py`): re-encode
  only the head segment, stream-copy the rest, sample-exact audio, assert frame
  counts; `--out-dir` for batches.
- **Sample-exact builder with whoosh gain** (parent: `megamix.ps1 -WhooshGain
  0.3`): cut times from frame counts; warning card prepended automatically.
- **Verifier** (parent: `verify_longform.py`): spec, A/V, PTS gaps,
  whoosh-per-cut by subtracting each clip's own audio (±5 ms scan), black-lead
  detection after cuts.
- **Docs generator** (parent: `marathon_docs.py`): chapters (card folded into
  chapter 1, >= 10 s check), MANIFEST.md with source paths.
- **Order solver**: re-cut across compilations, 10-minute same-type spacing,
  neighbour melody/key variation, intensity spread.
- **Long-form audio guard** and **thumbnail library** (shared with the
  compilation skill).
