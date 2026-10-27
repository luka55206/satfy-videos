# YT2_D_PLINKO — code-generated peg-board ball-drop Shorts

Python GENERATES every frame (deterministic, seeded code → cairo → ffmpeg) and
every sound (events → original synthesised soundtrack), in two orientations
(9:16 Shorts, 16:9 long-form). The owner does two things: **validate a test
clip** and **upload**. **Niche: Peg Drop** (balls fall through pegs into bins,
piles trace a bell curve) — brief in `research/niches/pegdrop.md`, chosen by the
owner 2026-10-04 but NOT market-researched. First scene: `scenes/pegdrop.py`
(not yet run: this PC had no Python/ffmpeg when it was written).

## COMPLIANCE FIRST (critical — read `docs/compliance.md`)

1. **Never say the mechanic's trademarked name** (registered mark, FremantleMedia /
   The Price Is Right): not in title, description, tags, hashtags, file names,
   thumbnails, on-screen text, channel name. Say peg board / ball drop / bean
   machine / Galton board. Scene is `pegdrop`, never the trademark.
2. **No gambling look or words**: no money, prizes, multipliers, "win", casino styling.
3. **Original audio only**: melody bank is LOCKED EMPTY, no samples, no music beds
   (`audio.MELODIES = {}`; PD tunes parked in `_PD_RESERVE`).
4. **Gate**: `python tools/compliance_check.py` (metadata + `--clip` + `--scenes`)
   must exit 0 before ship-clip stages anything and before every upload.
5. Everything below about "AI content" rules still applies (inauthentic content,
   one nameable change per video, human validates, honest disclosure).

Forked (engine + process) from the sibling `C:\Users\SE7EN\Desktop\Youtube\satisfying-2d-sims`
(0 → 10k subs, 7.4M views, YPP in 36 days) via `C:\Users\tsurt\VS projects\Yt-2d`.
Its numbers are quoted below as **parent-channel evidence** — a strong prior,
never a law for a new niche. When our data contradicts one, OUR DATA WINS.
## Why this survives YouTube's "AI content" rules (the whole point)

YouTube does not demonetise "AI". It demonetises **inauthentic content**
(mass-produced, repetitive, templated with only cosmetic variation) and
**reused content** (others' material without meaningful added value), and it
requires a **disclosure** for REALISTIC altered/synthetic media. Our defences
are structural — never let one slip, they gate the money:

1. **Every frame is authored code, not a generative model.** No AI video, no
   AI voice-over, no AI-generated footage or stock re-cuts. Stylised,
   obviously-animated output needs no synthetic-content disclosure — check
   YouTube's current wording at upload and answer honestly.
2. **Every video has ONE change a viewer could NAME.** Seed + palette + new
   tune is a RE-SKIN, and re-skins are exactly what the policy targets. The
   test: a sentence someone would say out loud ("this time the arena spins").
3. **A human validates every new format and episode** before it ships.
4. **Only public-domain or owned music**; never another creator's footage.
   `audio.MELODIES` = verified PD only; `MELODIES_CUSTOM` starts EMPTY.
5. **Compilations add value** (ordering, transitions, a new title/hook,
   chapters) and use only OUR clips.

## Setup (this PC has NEITHER yet)

```powershell
winget install Python.Python.3.12      # then reopen the terminal
winget install Gyan.FFmpeg
pip install -r requirements.txt
./run.ps1 -Scene pegdrop -Fast -Still -Frame 600       # smoke test -> output/*.png
```

## Commands

```powershell
./run.ps1 -Scene <name>                              # full 9:16 render + sound
./run.ps1 -Scene <name> -Fast                        # half-res test render
./run.ps1 -Scene <name> -Fast -Still -Frame 900      # single PNG
./run.ps1 -Scene <name> -Orient both -SceneArgs @('--seed','3')
```

- Output is **4K by default** (`NF_SCALE`, 2.0; `1.0` = Full HD). Logical
  coords stay 1080x1920 / 1920x1080. Cap 4K parallelism at 2-3 renders.
- `-Fast` = `NF_FAST=1` (50% scale): identical timing/framing — judge
  composition and timing on it, never pixel detail.
- `NF_ORIENT` = vertical | horizontal | both. `NF_CRF` = encoder crf (18).
- Scene args after `--`, read with `kit.arg(flag, default)`.
- `run.ps1 -SceneArgs @('--rule','')` can DROP the empty string — spot-check a
  frame for stray baked text.

## Architecture

```
lib/channel.py   channel identity: CHANNEL, CHANNEL_ID, WATERMARK, TIMEZONE (TBD)
lib/compliance.py trademark / gambling / IP / audio-provenance scanner (stdlib only)
lib/studio.py    Canvas (cairo draw helpers, caption, counter, goal_bar,
                 comment_card, watermark), VideoWriter (BGRA -> ffmpeg pipe),
                 PALETTE, mux_audio, save_still
lib/audio.py     events -> soundtrack: voices, ScaleWalker, MelodyWalker,
                 PD MELODIES + pick_melody(seed), mix_events, master(-14 LUFS)
lib/kit.py       scene boilerplate: arg/has, smooth, orients(), melody(),
                 deliver() (sidecar + soundtrack + mux), fan_out(), density_report
lib/layouts.py   9:16 / 16:9 canvas + arena placement; sim once, render per tag
scenes/<name>.py two-pass scene; pegdrop.py = the channel format, galton.py = scripted bell-curve sibling, _template.py = starter
tools/           compliance_check (GATE), flash_check, check_clip, check_loop, add_caption, regen_audio,
                 build_compilation, warning_card, yt_analytics, yt_upload_prep
```

The engine is still tuned for the parent's look (neon on black, circle arena,
marimba notes). **When the niche is chosen, re-skin `studio.PALETTE`,
`layouts.py` and the default voice ONCE in lib — scenes stay thin.**

Per-clip outputs: `<scene>_<label>_<tag>.mp4` (tag 9x16|16x9), sidecars
`<name>_events.json` + `<name>_audio.wav` in `output/`.

## Two-pass scene structure (every scene)

1. `simulate()` — pure, seeded, fixed dt=1/60 → per-frame timeline + events.
   Fast: use it for duration calibration and seed search.
2. `render()` — draw through `Canvas`, pipe to ffmpeg.
3. `build_events()` + `kit.deliver()` — audio regenerable from `_events.json`
   without re-rendering (`tools/regen_audio.py`).

Determinism: seed every RNG, fixed dt, no wall-clock in sim/render. Simulate
ONCE and translate per layout — a chaotic sim run per layout is two videos.

## `final/` layout

```
final/
  needs-review/      waiting on the owner's verdict
  ready-to-upload/   approved; youtube-upload moves them out
  uploaded/          uploaded, not yet in a compilation (the pool)
  compilations/      8-10 min long-form, one folder each + INDEX.md (clips move in permanently)
  long-form/         ~1 h reuse compilations: video + MANIFEST + UPLOAD + thumbnail only
  YOUTUBE-UPLOADS.md upload ledger
```

- Folders only, no loose videos. A clip folder holds the mp4 pair + `.md`
  ONLY — **never the `_events.json` / `_audio.wav` sidecars.**
- `output/` is disposable scratch: a clip awaiting review is MOVED to
  `final/needs-review/` before it is presented.
- A clip lives in exactly one place. Nothing is deleted.

## Workflow (enforced)

1. Build/edit scene → `-Fast -Still` at 2-3 timestamps → read the PNGs.
2. `-Fast` full clip → frames + audio stats (onsets ≈ events, -14 LUFS,
   event rate accelerating).
3. Full 4K, one orientation → self-verify again (ffprobe: h264 yuv420p 60fps).
4. **HARD STOP — the owner validates.** Never build a series before that.
5. Green light → both orientations → `ship-clip`.

- **Verify what the scene is ABOUT**, at 1:1 on the busiest region and on the
  exact event frames, out of the ENCODED file.
- **Change only what was asked.** A nearby improvement is a one-line
  suggestion, not part of the edit. **Never remove a visible feature as part
  of a fix — ask first.**
- Look iteration = stills, not clips.
- The owner wants to be corrected: at review, say plainly with evidence when a
  suggestion is wrong, then implement what they decide.
- A reference video URL is downloaded with `yt-dlp` and read as FRAMES — never
  WebFetched. A reference is an EXAMPLE, not a target: take the mechanic, make
  the look ours.

## Format rules carried from the parent (re-validate per niche)

- **US audience first** (owner, 2026-10-27; US = 20% of views, ~60% of revenue): US units first with
  metric in parentheses ("220 lb (100 kg)"), American spelling and names, US objects, uploads at US
  evening (02:00-06:00 Tbilisi). Full rules: `.claude/skills/us-audience/SKILL.md`.

- **Hook**: something MOVING in the first ~2 s; the core mechanic visibly
  fires by second 5. Parent: stayed-to-watch is the #1 reach predictor
  (r=+0.59, n=133; 65%+ stay → 5x median views). Spend effort on the opening.
- **One mechanic + one escalation rule per video; the event rate must still be
  climbing at the last frame.** A falling rate reads as "it's over".
- **Length is ladder-first**: as long as the escalation has honest rungs,
  59 s hard ceiling for Shorts. Never pad; never widen the opening.
- **Every video loops.** Prefer a perfect (undetectable) loop; fall back to
  rewind or dissolve to the exact frame-0 state. Never fake one.
- **Caption = a spec**: states the rule, only promises what the video
  certainly does, persists the whole clip, 1-3 highlighted words, line 2 is a
  finite stake the video answers ("How many can it HANDLE?"). Never a
  viewer-prediction question. Captions are a POST-RENDER pass
  (`tools/add_caption.py`) — keep the caption-less base.
- **Audio**: pleasant only (no creepy drones, no buzzers); one note per
  repeated event, a PD melody where events vary; tail silent at the loop seam;
  measure LUFS/peak on the MUXED mp4.
- **Photosensitivity**: `tools/flash_check.py` on every clip; ≥3 large-area
  flashes in 1 s = FAIL. Prefer the calmer option; never de-tune the mechanic —
  warn on long-form (card + description line) only when it fails.
- **9:16 safe zone**: caption ~0.14h, content ≤ ~0.71h, counter ~0.78h —
  the Shorts UI eats the bottom ~18-20%. Fill the width (0.85-0.90).

## Channel strategy carried from the parent (re-validate per niche)

- **Long-form is the product, Shorts are its fuel.** Parent: long-form = 90%
  of revenue on 26% of views (RPM $1.79 vs $0.067). Every Short is also pool
  material for the next compilation.
- Cadence: parent settled on **5 Shorts/day** (3/day lost on views per day).
  Compilations 1-2/week; the ~1 h long-form every 2 weeks (parent RPM 3.1x the
  8-10 min compilation).
- **Franchise winners fast**, each episode with one nameable change.
- Titles: 3-4 options of different types (reaction / rule / question /
  number / challenge). Shorts 1-3 emoji; long-form none (search phrase).
- Shorts metadata: parent test was title ending `#usa`, no description, no tags. HERE: always run compliance_check on title/description/tags; description = 1-2 plain sentences about the video + 3-4 hashtags. NO "generated/simulated by code" line (owner, 2026-10-17: hurts views; the synthetic-content setting is answered separately, honestly).
- One comment-reply video per week (best sub rate on the parent).

## Skills (`.claude/skills/`)

`niche-research` (START HERE) · `make-video` · `episode-batch` · `redesign` ·
`comment-video` · `ship-clip` · `compilation` · `long-form` ·
`youtube-upload` · `youtube-analytics` · `crosspost` · `us-audience` (applies to EVERY video).
Tooling the parent had but this repo does not yet (batch shipper, compilation
builder with transitions, thumbnail lib, intro baker) is listed at the end of
each skill — build it once the niche fixes the format.

## Verified API gotchas

- cairo `FORMAT_ARGB32` on Windows = premultiplied BGRA → ffmpeg `-pix_fmt bgra`.
- yuv420p needs even dimensions — Canvas rounds down; draw in logical coords.
- pedalboard wants `(channels, samples)`; pyloudnorm float64
  `(samples, channels)`, measure LUFS in STEREO. pedalboard's `Limiter`
  applies makeup gain — it is not a ceiling outside `audio.master()`.
- cairo has no blur: glow = radial gradient; a glow DISC greys empty black —
  hug the geometry.
- Measure a loop seam PRE-encode (`tools/check_loop.py`); post-encode use the
  MEAN per-pixel delta (good 0.12-0.72, broken >1.1).
- Re-muxing audio onto a muxed clip: drop `-shortest` (it eats ~4 frames).
- Two renders sharing a `--label` corrupt the mp4 — one per label at a time.
- ffmpeg `overlay` can drop frames at input junctions: build delayed inputs as
  files first and encode with `-fps_mode cfr -r 60`.

## Owner overrides

Every rule here is compressed evidence, not law. When the owner asks for
something that contradicts one: flag the conflict in ONE line, then build it
fully. A per-video override applies to that video only; a rule changes only
when the owner says to change the rule.

## Git

Never `git commit` unprompted; no AI-attribution trailers. Leave work in the
tree and report what is ready.

## Knowledge lives in the repo

CLAUDE.md, `docs/`, `research/` and `.claude/skills/` are the durable record;
auto-memory is a cache. Per-scene lessons go in `docs/scenes/<scene>.md`.
Keep docs terse: rules and numbers.
