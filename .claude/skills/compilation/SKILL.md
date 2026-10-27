---
name: compilation
description: >
  Build a COMPILATION — the 8-10 minute long-form 16:9 video made of finished,
  already-uploaded Shorts, which permanently CONSUMES the clips it uses. Use
  whenever the owner asks to "make a compilation", "compilation N", "long-form
  from the shorts", "best-of video" or "new long video". Named clips / count /
  order → follow exactly; otherwise fill 8:00-10:00 (both ends hard) and STOP
  if the pool can't reach 8:00. Ships video + thumbnail candidates + UPLOAD.md.
  NOT the ~1-hour reuse video — that is the `long-form` skill.
---

# Build a compilation (8-10 min long-form)

One finished clip per scene type, concatenated 16:9, a transition swish at each
cut, audio rebuilt and mastered to -14 LUFS. Everything lives in
`final/compilations/compilation N/` and is SELF-CONTAINED: clips, video,
`MANIFEST.md`, `UPLOAD.md`, `thumbnail/` — uploading needs nothing else.

## Why it exists (parent-channel evidence — re-validate on this niche)

On the sibling channel long-form was **~90% of revenue and ~80% of watch time
on ~26% of views** (RPM ~27x a Short's). Every Short is therefore judged first
as pool material for the next compilation. Re-run the analytics skill on THIS
channel before trusting any of these ratios.

## Authenticity — why this is not "reused content"

YouTube's inauthentic / reused-content policy targets mass-produced,
near-duplicate uploads and other people's footage. A compilation stays on the
right side only while every clip is our own original render, each video is a
NEW curated selection (no clip ever appears in two compilations), it adds
structure (ordering, chapters, a stated theme), and **a human reviews it before
upload**. That is a discipline, not a guarantee — never relax it for speed.

## What the owner specifies vs what you decide

- **The owner names clips, a count or an order → do exactly that.**
- Otherwise YOU pick, and **runtime decides the count** — measure, never guess.

### 8:00-10:00 is money, not taste — both ends HARD

- **FLOOR 8:00**: YouTube only allows mid-roll ads from 8 minutes. A 7:55 video
  throws the ad slot away for five seconds.
- **CEILING 10:00**: the pool is fixed and a clip is consumed permanently, so
  total minutes are roughly conserved — but upload COUNT is not. Each extra
  upload is another pre-roll, another title/thumbnail shot, another strong
  opener. Minutes 10-12 are worth more seeding the NEXT compilation. (One 11-min
  video out-earns one 8-min video; the real comparison is 3 x 11 vs 3.4 x 10
  from the same pool.)
- **Pool can't reach 8:00 → STOP and report**: the shortfall in seconds, which
  `ready-to-upload/` clips would close it once uploaded, which scene types still
  need a clip. **Never ship short, never pad** (no slowed replays, no filler
  cards, no duplicate clips).
- Pool bigger than 10:00 → build the next compilation sooner; never stretch.
- Measure the CHOSEN clips' sum from **frame counts** (container durations
  drift ~0.01s per clip high):
  `ffprobe -v error -select_streams v:0 -count_packets -show_entries stream=nb_read_packets -of csv=p=0 <clip>` / 60.
  Subtract any tail you will cut (below) and add the warning card (3s) if it
  fires. **Check the runtime again on the BUILT file.**

## Selection rules (when you decide)

1. **Pool = top level of `final/uploaded/` only.** Clips in `final/compilations/`
   are spent — structurally, because building MOVES them there. Never reuse a
   clip from any earlier compilation (a different episode of the same scene is
   fine). `final/compilations/INDEX.md` is the readable record; folders are truth.
2. **One clip per scene type** — never two episodes of one scene in one video.
3. **PD-only audio.** Any clip scored from `audio.MELODIES_CUSTOM` or other
   supplied/licensed music is Shorts-only and never enters long-form, whatever
   it scores. No guard tool exists yet — check each clip's melody (its `.md`,
   scene args or events sidecar) against the custom bank before picking.
4. **ORDER THE FIRST 8 BY STAYED-TO-WATCH, highest first.** Parent evidence
   (11 long-form retention curves): ~35% of the audience is gone by the 10%
   mark — the first clip — while every later step loses 3-6 points. Slot 1 is
   the whole game. Show stay % per slot when proposing the cut; clips with no
   stay data go after the 8.
5. Variety only breaks ties inside that run: alternate dense/sparse, vary the
   colour theme, never two near-identical mechanics back to back.

## Build steps

1. **Create `final/compilations/compilation N/`** (next unused number).
2. **Copy each chosen 16:9 in as `NN_<name>_16x9.mp4`** — the listing IS the
   play order. Sources are never modified.
3. **No black title cards between clips.** Parent evidence: viewers left at
   every black card (~+1.2 audience points lost per cut; ~0 at a mid-clip
   point). Cut straight from running clip to running clip.
   - **Dead tail**: if a clip's loop ends on black/empty frames, cut it **~5
     frames before the black** — never earlier (payoffs often land in the last
     half second). Manual: find the first dead frame (per-frame luma scan,
     `-vf signalstats,metadata=print:key=lavfi.signalstats.YAVG`), then
     re-encode a trimmed copy into `output/` (`-frames:v <N>`, libx264 crf 16,
     `-c:a aac -b:a 384k`, audio cut to the same sample: N x 800 at 48 kHz) and
     use that copy. A static non-black loop end is not cut.
4. **Photosensitivity — conditional card.**
   `python tools/warning_card.py --scan <clips in play order> --out "<folder>/00_warning_card.mp4" --report "<folder>/flash-report.json"`
   flash-checks every clip (cached in `output/flash_cache.json`) and writes a
   3s card naming the flashing timestamps **only if a clip fails** (>= 3
   general flashes in a second). Nothing fails → nothing written, no warning.
   Do NOT use `--trim-auto` / `--tail-trim` (they import tools that don't exist
   here); if you cut tails, the named timestamps may be early by those cuts —
   correct them by hand. **Never skip the check to save runtime**: if the card
   pushes past 10:00, drop a clip.
5. **Build**:
   `python tools/build_compilation.py --out "<folder>/compilation_16x9.mp4" --clips 00_warning_card.mp4,01_...,02_...`
   (comma list, full paths). What it actually does: lossless stream-copy concat
   (**identical specs required** — conform any odd clip with one re-encode
   first), clip audio re-laid on a fresh buffer, `sfx/transition.wav` placed
   0.12s before every cut with a 0.55 music duck, mastered to -14 LUFS, muxed
   AAC 384k. Cut times come from container durations, so verify the whoosh
   positions — it is the known drift point. (With a card, a swish also plays at
   the card→clip-1 cut; acceptable.)
6. **Verify — measure, never eyeball**, on the built file:
   - spec: h264 / 3840x2160 (or the channel's long-form res) / yuv420p / 60fps
     / stereo 48k AAC;
   - **A/V stream duration diff < 50 ms**;
   - **no PTS gaps**: every packet delta <= 1.5/60
     (`ffprobe -select_streams v:0 -show_entries packet=pts_time -of csv=p=0`);
   - **swish at every cut**: its onset within ~30 ms of (frame-count cut time −
     0.12s), constant offset (no drift);
   - `python tools/flash_check.py <built>` result matches the card decision;
   - runtime 8:00-10:00 including the card.
7. **Thumbnails — ~15-20 candidates, PNG only, in `thumbnail/`.** Built from
   real frames of THIS compilation's clips (`ffmpeg -ss <t> -i clip -frames:v 1`,
   compose with cairo/PIL). Rules that generalise:
   - Parent's A/B winner was the **before → after split panel** (a small number
     → a big number, read off the clip) at ~50% watch-time share vs ~25% each
     for the alternatives. Parent evidence — test it on this niche with
     YouTube's Test & Compare before treating it as settled.
   - **Every number printed is READ OFF the frame beside it** (counter-crop
     contact sheet). A wrong number is a lie.
   - The after-frame is the VISUAL payoff, not the biggest number.
   - Crop past the baked caption/HUD; no black bands, no baked letterbox. One
     focal shape, max saturation.
   - **A change request is answered with a SWEEP, never one image**: every
     honest value of the named parameter, one file each, named for the value.
     The owner picks the 3 to test.
   - Delete frame scratch when done.
8. **Metadata in chat AND `<folder>/UPLOAD.md`** (permanent, not disposable):
   - **10-15 titles, GENRE-SUPERLATIVE pattern, NO EMOJI**: count + superlative
     or escalation claim + optional parenthetical hook, reading like a search
     phrase ("13 Most Satisfying ... (Every ... )", "13 ... That End In Total
     Chaos"). No tech jargon. Note which pair with which thumbnails.
   - **Description**: opens with
     `Photosensitivity warning: this video contains flashing lights and rapid colour changes.`
     **only when the card fired** (plus its timestamps); chapters at the real
     cut times from FRAME COUNTS, rounded down, first at 0:00, **every chapter
     >= 10 s** or YouTube shows none — fold the 3s card into chapter 1; a
     comment-your-idea hook.
   - Pinned comment (@-mention the commenter if a comment-reply clip is in).
   - Thumbnails to test.
9. **Move the clips and write the records.** Every used clip moves out of
   `final/uploaded/` into the folder — BOTH orientations, `NN_<name>_<tag>.mp4`
   — its permanent home, no copy left in the pool. A clip in the compilation but
   not yet uploaded as a Short stays in `ready-to-upload/`; only its numbered
   16:9 copy goes in. Write `MANIFEST.md` (order, scene type, frame-count
   duration, tail cuts, anything unusual) and add the column to
   `final/compilations/INDEX.md`. Sidecars (`_events.json`, `_audio.wav`) never
   enter `final/`.

## Hard rules

- 8:00-10:00, both ends hard. Short pool → stop and report.
- 16:9 only. No black title cards between clips.
- Never modify source clips; trims happen on copies in `output/`.
- PD-only audio. Conditional warning card; never disabled to save runtime.
- **HARD STOP after build + verification — the owner reviews before upload.**
- Never run a build "to test" without naming the exact target folder; say
  whether a change touches tooling or an already-built folder.
- No git commits — the owner commits.

## Tooling to build once the niche is chosen

- **One-command builder** (parent: `megamix.ps1`): segment split so only ~5s at
  each junction is re-encoded, **sample-exact audio** from frame counts (no
  AAC concat drift), warning card prepended automatically, cut times printed
  for chapters, whoosh gain flag.
- **Tail trimmer** (parent: `tail_trim.py`): detect a loop's dead tail, cut 5
  frames before it, report every cut; feed the same cuts to `warning_card.py`.
- **Long-form audio guard** (parent: `longform_audio_guard.py`): refuse any
  clip scored from a custom bank; needs a recorded tune per clip.
- **Verifier** (parent: `verify_longform.py`): spec, A/V diff, PTS gaps,
  whoosh-per-cut (subtract the clip's own audio, scan ±5 ms), no black lead.
- **Thumbnail library** (parent: `thumb_lib.py`): one copy of the split/hero/
  strip/number layouts + a guard that fails on dead bands or non-PNGs;
  per-compilation scripts are data only.
- **Docs generator**: chapters.txt / MANIFEST.md / INDEX.md from frame counts.
- **Cut transition** (parent: an in-motion transition replacing black cards) —
  design one that fits the niche's look.
