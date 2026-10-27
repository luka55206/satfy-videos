---
name: ship-clip
description: >
  Finish and ship a validated clip — everything between the owner's green
  light and a self-contained pair in final/ready-to-upload/. Use whenever a
  clip is approved ("ship it", "stage it", "make it ready to upload", "green
  light"), or when staging/promoting any finished render into final/. Covers
  the caption post-pass, the rewind/scrub audio pass, verification numbers,
  staging (no sidecars in final/) and the deliver-twice upload metadata.
  Called by make-video's ship step, episode-batch and comment-video.
---

# Ship a validated clip

Only a clip the owner has validated ships. Pipeline order is fixed:
**render (caption-less base) → caption post-pass → [16:9 title/intro, if the
niche uses one] → audio passes → verify → stage → metadata.** The caption must
exist before anything that hands off to it.

**Shorts-only clip** (any audio that is not verified public-domain / owned —
see Guardrails): 9:16 ONLY. No 16:9 render, caption pass or long-form use; the
staged folder holds `_9x16.mp4` + `.md`.

## 1. Caption (post-render, never baked)

- Render both orientations caption-less at `NF_CRF=14`, named
  `<scene>_<label>base_<tag>.mp4`, and **KEEP the bases** — a rewording then
  costs one re-encode, not a full re-render. Never `--inplace` over a base.
- Pass an empty rule via Bash or direct `python`, not `run.ps1 -SceneArgs`:
  PowerShell 5.1 can DROP a trailing empty-string arg and bake stray text.
  Spot-check a frame for stray text either way.
- `python tools/add_caption.py <base> --rule "<text>" --loop <style>
  --rebuild R --payoff P --fade F --out <final>`. R/P/F are the scene's
  ending constants, recorded in `docs/scenes/<scene>.md`. Loop styles:
  `rewind` (indices walk back), `dissolve`, `constant` (perfect loop — no fade
  at the seam), `none`. Caption alpha is a pure function of the SOURCE frame
  index and must be exactly 0 at a rewind/dissolve seam.
- Whatever `--cap-size` / `--cap-dy` / `~span~` + `--span-color` /
  `--span-size` / `--line-gap` a clip uses must travel to every later pass
  that redraws the caption (e.g. a 16:9 intro), or the hand-off jumps.
- Only the caption is post-render. Counters, bars and other HUD are baked —
  a HUD change costs a full re-render; say so BEFORE spending it and let the
  owner decide. Batch caption + HUD changes into one render.

**Caption checklist — verify on the rendered 9:16 frame before staging:**
1. **Short**: every word earns its place; two lines max; plainest wording
   that states the rule. Shrink-to-fit means shorter = bigger.
2. **1-3 highlighted words** (`~word~` + `--span-color`) on the verb or the
   stake. No highlighted word = defect.
3. **Line 2 states the STAKE**, preferably as a question the VIDEO answers
   on screen (a finite, visible outcome). NEVER a viewer-prediction question
   ("Can you guess…?") and never a question with no finish line on screen.
   *(Parent-channel evidence: sim-answered questions topped stay-to-watch,
   predict questions were the worst — re-validate on this niche.)*
4. **The caption is a SPEC**: re-read it against what the video actually
   does; never promise a certainty that happens by chance.
5. **Fits the frame and the content area** — check width on a still in each
   orientation that carries it.

## 2. Test clip handed over (pre-staging)

Anything the owner is asked to judge lives in `final/needs-review/` (mp4s +
`.md`), never only in `output/` (disposable scratch). Audio passes that would
normally run at staging (e.g. a rewind scrub) are applied BY HAND to a test
clip — it isn't finished without them. Before staging, **rebuild the pristine
file from the base** so a pass is never applied twice.

## 3. Verify (both orientations, on the MUXED mp4)

`python tools/check_clip.py <clip> [...]` plus `python tools/flash_check.py
<clip>`. Pass bar:
- ffprobe: h264, yuv420p, 60 fps, expected size (4K by default: 2160x3840 /
  3840x2160); packet count matches the base (re-muxing audio: drop
  `-shortest`, re-check `nb_read_packets`).
- Integrated LUFS −14 (measured in STEREO); decoded peak ≤ −3 dBFS; last-0.5 s
  near-silent at a loop seam.
- Loop seam: post-encode MEAN per-pixel delta, good 0.12-0.72, broken 1.16+;
  0.8-1.2 → confirm pre-encode with `python tools/check_loop.py <scene> --
  <args>`.
- Durations match across orientations; Short under 59 s.
- Flash check: a FAIL is allowed if the content needs it — the warning goes on
  long-form only (card + description line), never on a Short.
- Encode budget: max 2-3 concurrent 4K encodes, counting caption passes.

## 3b. Compliance gate (mandatory, before staging)

`python tools/compliance_check.py --title "<title>" --description "<desc>" --tags "<a,b>" --clip output/<name>.mp4`
and `python tools/compliance_check.py --scenes`. Any FAIL = do not stage (trademark,
gambling wording, third-party IP, tunes/samples/music beds). Rules: `docs/compliance.md`.

## 4. Stage + metadata (deliver TWICE)

- Move the mp4 pair + write `<stem>.md` into `final/ready-to-upload/`.
  **Those files ONLY — never `_events.json` / `_audio.wav` sidecars in ANY
  `final/` folder** (sidecars live in `output/`). Before reporting staged:
  `ls final/<folder> | grep -E 'json|wav'` must print nothing.
- `.md` sections:
  - `## Title` — 3-4 options from DIFFERENT types (reaction / rule-restated /
    question / number / challenge); every Short option carries 1-3 emoji;
    long-form titles carry none.
  - `## Pinned first comment` — engineered to invite a reply.
  - `## Notes (not for upload)` — exact flags + verification numbers.
- Shorts metadata format (description, tags, hashtags) follows the current
  rule in the project CLAUDE.md; parent-channel evidence was *no description,
  no tags* — re-validate on this niche. Long-form keeps a description
  (chapters, photosensitivity line when earned).
- Deliver the SAME metadata in chat; record flags/lessons in
  `docs/scenes/<scene>.md`. The `.md` changes job with its folder (review
  note → upload metadata) — rewrite it when moving the mp4s.

## Guardrails

- **Authenticity gate** (why this channel stays monetisable): every clip is
  deterministic code-rendered (no gen-AI footage or voice), passed the owner's
  validation, and — if it is an episode — carries ONE change a viewer could
  NAME. A seed/palette/tune swap alone is a re-skin: do not ship it.
- Music: public-domain compositions (or owner-held rights) only.
  `audio.MELODIES_CUSTOM` is empty; anything added there is Shorts-only.
- Change only what was asked; never remove a visible feature without asking.
- Never `git commit` unprompted.

## Tooling to build once the niche is chosen

- `tools/caption_check.py` — **`add_caption.py` imports it for every
  non-empty caption and will crash (ModuleNotFoundError) until it exists.**
  Until then, check the caption rules above by hand (or temporarily guard the
  import).
- `tools/ship_batch.py` — batch staging: caption-string byte-match rows,
  spec/duration/seam verification, sidecar guard (`--guard`). Manual
  equivalent: steps 3-4 above.
- `tools/add_rewind_sfx.py` — rewind audio scrub for rewind-loop clips.
  Manual equivalent: re-render the soundtrack with reversed events.
- A 16:9 title/intro baker (parent: `megamix_intro.py`); a long-form
  non-PD audio guard (parent: `longform_audio_guard.py`).
