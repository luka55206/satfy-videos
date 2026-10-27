---
name: make-video
description: >
  Make/create/generate/build a new video for this channel — a new SCENE (a
  parameterized, seeded, code-rendered generator of one video format), a test
  clip, a series, a remake of a reference video, or a new EPISODE / "vol 2" /
  "another one of <scene>" of a scene that already shipped. Use whenever the
  owner asks for a new video, a new scene or format, a remake of something they
  saw, or another episode. Works for any niche: it reads the chosen niche's
  brief in research/niches/ first. Enforces the test-clip -> self-verify ->
  owner-validates -> series lifecycle.
user-invocable: true
---

# Make a new video

A **scene** is `scenes/<name>.py`: a parameterized, seeded, deterministic
generator of one video format. Two passes: `simulate()`/`generate()` builds the
per-frame timeline + an EVENT log, `render()` draws it through `lib/studio.py`
Canvas into an ffmpeg pipe, the soundtrack is built from the events
(`lib/audio.py`), and `kit.deliver()` muxes. Per-scene lessons live in
`docs/scenes/<scene>.md` — read it before touching a scene. This file is the
procedure.

**Why the discipline exists:** YouTube's inauthentic / mass-produced /
repetitive-content policy gates monetisation. This channel stays on the right
side of it because every video is deterministic code-rendered (no generative-AI
footage or voice), passes a human validation gate, and every episode carries a
change a viewer could NAME. Never trade any of the three for speed.

## Step 0a — Load the niche brief (mandatory)

1. Read `lib/channel.py` and `research/niches/`. Find the CHOSEN niche's brief
   (format spec, look, audio identity, length target, what the audience comes
   for, competitor notes, stop list).
2. **No niche chosen yet (no `research/niches/CHOSEN.md`) → STOP.** (Chosen: Peg Drop, see `research/niches/pegdrop.md`; read `docs/compliance.md` too.)
   Tell the owner, and point to the `niche-research` skill. Do not invent a
   niche to have something to build.
3. Everything below that says "the niche's look / audio / length" means what
   that brief says. Where the brief is silent, ask; don't import another
   channel's conventions.

## Step 0b — Identify the input mode

**Mode A — reference video URL:**
1. Download with yt-dlp, never WebFetch (a video is only readable as frames):
   `yt-dlp --js-runtimes node -f "bv*+ba/b" -o "research/reference-videos/ref_<slug>.%(ext)s" --no-playlist "<url>"`
2. Extract frames: contact sheets (`fps=1,scale=360:-1,tile=3x4`) + full-res
   (`fps=3`). READ them.
3. Write a beat sheet: format/mechanic, objects, escalation rule, on-screen
   text, ending, implied sound events.
4. Measure the audio (librosa: onsets, key/register, density curve, discrete
   hits vs a music bed) → one-line **sound spec**. Rebuild it in our own voice;
   never copy samples.
5. **A reference is an EXAMPLE, not a target.** Take the MECHANIC/FORMAT, make
   the look OURS (our PALETTE, caption phrasing, watermark). Never reproduce a
   reference's look — that is exactly the copy-content pattern the policy hits.

**Mode B — idea or variation:** copy the closest scene in `scenes/` and modify.
If `scenes/` is empty (first scene of the niche), build from `lib/kit.py`
(`arg/has`, `orients()`, `deliver()`, `fan_out()`) and `lib/layouts.py`, and
make that first scene the canonical two-pass template for the niche.

**Mode C — new episode of a scene that already shipped.** Not a new format: a
PROVEN scene re-run so it is a genuinely new video, not a re-upload. The code is
validated; only the new values/flag are new. (Several episodes at once → the
**episode-batch** skill, which delegates each build back here.)

1. Identify the scene file and its shipped clips; read `docs/scenes/<scene>.md`
   (episode history, banned re-skins).
2. **Vary — BOTH halves required:**
   - **Cosmetic (always, never sufficient):** `--seed`, a different colour FROM
     the palette, starting parameters within the tuned range, musical key.
   - **ONE NAMEABLE change (mandatory).** Seed + palette + a new tune is a
     RE-SKIN. State the change in one sentence a viewer would say out loud
     ("now there are two of them", "now it has to reach 10,000"). Can't write
     the sentence → it isn't an episode yet. A new melody is never the change.
   - Hard rule because it gates money: cosmetic-only uploads are what the
     inauthentic-content policy targets.
3. **Freeze** the scene's identity: layout, loop requirement, watermark, base
   voice, palette (pick a colour from it, don't add colours). The mechanic may
   gain ONE visible extension (the nameable change), but it stays itself.
   **Caption and mechanic move together or not at all** — a changed rule with
   the old caption lies; a new caption on an unchanged sim manufactures fake
   novelty.
4. Implement a new behaviour as a **flag defaulting OFF**, so every shipped clip
   re-renders bit-identically. A new flag touches every parse site and worker
   call site — grep for all of them.
5. Name `<scene>_<label>_<tag>.mp4`, label encoding the change. Verification
   is lighter (Step 2 stills, `-Fast` full, audio, seam), never skipped; Step 3
   still applies.

## Step 1 — Build ONE complete test clip

- Complete, not a stub: real palette, caption, HUD, watermark, sound. Smallest
  parameters that still show the full arc. Vertical only (`run.ps1` default).
- Render with `--rule ""` and add the caption as a post-pass
  (`tools/add_caption.py … --out`) — keep the caption-less base so a rewording
  costs one encode, not a re-render. Spot-check a frame for stray baked text
  (PowerShell can drop a trailing empty argument).
- **Design the ARC first, then the length.** Four beats that must all READ:
  pose the question → escalation the viewer can feel → payoff → loop. The clip
  is as long as the escalation has honest rungs — never padded, never cut
  before its visible completion. Something must MOVE in the first ~2 s, and the
  format must visibly fire by second ~5. Length ceiling = the niche brief's
  (Shorts: under 60 s).
- **Escalation must climb to the last frame.** Print events per 5 s across the
  final third: climbing → keep going; falling → that is where the clip ends.
- **Loop is the default** — design the ending so the last frame returns to the
  frame-0 state (rewind, dissolve, zoom/self-similar, or wrap). Prefer a loop
  the viewer can't detect; never fake one. Parent-channel evidence says loops
  help replays — re-validate on this niche and record the verdict in the brief.
- **The caption is a SPEC**: short, plain words, ≤2 lines, 1-3 highlighted key
  words, states the rule and a VISIBLE stake the video resolves. Never promise a
  certainty the generator only does by chance; never a question asking the
  viewer to predict. Re-read the caption against the code path before shipping.
- **Audio**: PD-only. Every tune comes from `audio.MELODIES` (composition
  genuinely public domain); `MELODIES_CUSTOM` is empty and stays opt-in-only.
  Never copyrighted music — note-by-note replay is a derivative work. A viral
  tune usually has a PD ancestor; offer that instead. If the niche's events are
  one repeated action, one note/SFX per event beats a melody. No silent head
  (`kit.deliver()` adds an intro layer by default).
- Determinism: seeded RNG, fixed timestep, no wall clock. Same command → same
  video bit-for-bit.

## Step 2 — Self-verify (owner NOT involved yet)

Loop until ALL pass:
1. **Stills** at 3-6 timestamps: `./run.ps1 -Scene <s> -Fast -Still -Frame N`,
   READ them. Opening (motion + caption readable), mid (escalation visible),
   payoff, loop landing. Palette, text shadow, watermark subtle, nothing
   cropped.
2. **Verify what the scene is ABOUT at the right scale**: zoom 1:1 on the
   busiest region; check short transients on the exact frames from
   `_events.json`, out of the ENCODED output.
3. **`-Fast` full clip** → extract ~7 frames and read them.
4. **`python tools/check_clip.py output/<clip>.mp4`** — LUFS −14 (stereo),
   decoded-mp4 peak (ceiling −3 dBFS), last-0.5 s peak (seam click), seam mean
   delta (good 0.12-0.72, broken ≥1.16), note health (`len(set(notes))` ≥ 8 on a
   30+ note scene, no pitch over ~25%), events/5 s accelerating.
5. **Pre-encode seam**: `python tools/check_loop.py <scene> -- <args>` (frame 0
   vs last must be identical for rewind/dissolve/zoom; wrap loops are judged
   against an interior consecutive-frame delta instead).
6. **Photosensitivity**: `python tools/flash_check.py <clip>`. Prefer the less
   flashy option when the look is free; if the format needs it, keep it and let
   long-form carry the warning. Never de-tune the content for it.
7. **16:9 still** before any `-Orient both` render (geometry bugs are often
   invisible in 9:16).
8. **Full-res render** → ffprobe: h264, yuv420p, 60 fps, expected size
   (`NF_SCALE`; 4K default 2160x3840 / 3840x2160), duration = the designed arc.
   Cap 4K parallelism at 2-3 concurrent encodes.

## Step 3 — HARD STOP: the owner validates

- **Move** the test clip (the mp4(s) + its `.md`) into `final/needs-review/`
  before presenting. Never leave a clip awaiting a verdict only in `output/`
  (disposable scratch). Sidecars (`_events.json`, `_audio.wav`) stay in
  `output/` — `ls final/needs-review | grep -E 'json|wav'` must be empty. A
  revision replaces the old copy, never sits beside it.
- Present: path + 2-3 stills + one line on the format and (Mode C) the nameable
  change. Build nothing more until the owner explicitly approves.
- Changes: audio-only → regenerate from `_events.json`
  (`tools/regen_audio.py`), no re-render; caption-only → re-run
  `add_caption.py` on the base; visual → re-render, re-stage the same way.
- At the gate, check each owner suggestion against the data/reference and say
  plainly whether it's right, with evidence — then implement.

## Step 4 — On green light

1. Standalone Short by default; a series only when the owner asks.
2. Render `-Orient both` (the 16:9 feeds future compilations) unless the niche
   brief says the format is Shorts-only.
3. Finish via the **ship-clip** skill if present; otherwise manually: caption
   post-pass on each orientation from the kept base, re-run `check_clip.py` and
   `flash_check.py` on the final files, stage the mp4 pair + `.md` in
   `final/ready-to-upload/`, sidecars stay in `output/`.
4. **Metadata delivered TWICE** — in chat AND as `<stem>.md` beside the clip:
   3-4 title options of DIFFERENT types (reaction / rule-restated / question /
   number / challenge) + a pinned first comment. Shorts title emoji/hashtag
   conventions come from the niche brief.
5. Series: sweep the variable, verify each clip, compile with
   `tools/build_compilation.py` (identical specs are load-bearing).
6. Record new tuning lessons in `docs/scenes/<scene>.md` in the same session.
7. Leave changes in the working tree and report — **never `git commit`
   unprompted**, no AI-attribution trailers.

## Guardrails

- Never skip the gate; never ask the owner to validate an unverified clip.
- **Change only what was asked**: one named defect = one minimal change,
  everything else bit-identical. Nearby improvements go to the owner as a
  one-line suggestion.
- **Never remove a visible feature as part of a fix — ask first.**
- Look iteration = stills, not clips. A background agent never exceeds its
  requested scope (no 4K render when a `-Fast` check was asked for).
- Two renders sharing a `--label` corrupt the mp4 — one render per label.
- The owner overrides any rule: flag the conflict in one line, then build it
  fully. A per-video override does not change the rule.

## Tooling to build once the niche is chosen

- `tools/ship_batch.py` — batch staging: verify spec/duration/seam, copy the
  pair to `final/`, and a `--guard` sidecar sweep. Until then: stage by hand and
  run the `grep -E 'json|wav'` check.
- `tools/caption_check.py` — lint captions (lines, words, highlight, no
  prediction question) and preview the baked still. Until then: check by eye
  against the caption rules above.
- A canonical first scene template for the niche (`scenes/<first>.py`).
- Mode A helpers (`research/analyze_audio.py`, frame extractor) and a
  rewind-SFX tool if the niche uses rewind loops. Until then: ffmpeg + librosa.
