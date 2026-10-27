---
name: episode-batch
description: >
  Build a BATCH of new episodes from PROVEN scenes — the owner asks for "N more
  videos", "take the proven ones and change something", "sequel the winners",
  or any multi-clip request that is episodes of existing scenes rather than new
  formats. The SELECTION and BATCHING layer: which scenes to sequel, which
  nameable change each gets, how to de-risk and ship the set. Each episode is
  built through make-video Mode C.
---

# Episode batch — sequel proven scenes at scale

Per-episode rules (nameable change, freeze list, caption-moves-with-mechanic,
flag-defaults-OFF, lighter verification) live in **make-video Mode C**. This
skill covers picking the scenes, picking the changes, and running N through one
pipeline safely.

## 0. Preconditions

- A niche is chosen and briefed (`research/niches/`, `lib/channel.py`). If not,
  stop and point to `niche-research`.
- There are PROVEN scenes to sequel. None yet → this is new-format work, use
  make-video.

## 1. Scope

- N episodes, **N different scene families by default** — five cuts of one
  scene is one franchise flooding its own audience, and a run of near-identical
  uploads is the mass-produced pattern the monetisation policy targets.
- The validation gate applies PER CLIP unless the owner waived it for this batch
  in their own words ("deliver without asking"). A waiver is per-batch, never
  the new rule.

## 2. Scout the pool

- **Proven = shipped AND uploaded**: `final/uploaded/`, clips consumed by
  `final/compilations/`, and the ledger `final/YOUTUBE-UPLOADS.md`.
  `ready-to-upload/` is approved but unproven.
- **Skip in-flight scenes**: an untracked `docs/scenes/*.md` or a modified scene
  file you didn't touch means another session is mid-build. Don't finish
  unknown state.
- **Skip families that shipped an episode in the last few days**, unless
  deliberately franchising a fresh over-performer the owner pointed at.
- Read each candidate's `docs/scenes/<scene>.md` before shortlisting — episode
  history, banned re-skins, sweep metrics.
- **Unattended batches pick from DATA, not taste**: the newest report in
  `reports/` (from the youtube-analytics skill, `tools/yt_analytics.py`) — top
  families by median views and stayed-to-watch first, nothing from the niche
  brief's stop list. Report older than ~2 weeks → pull fresh numbers first.
  (Parent-channel evidence: stayed-to-watch was the strongest reach predictor,
  r = +0.587, and franchising winners within days paid off — re-validate on this
  niche.)

## 3. Pick the change — archetype ladder (cheapest first)

The bar is always Mode C's: one sentence a viewer would say out loud. A new
seed, palette or tune alone never qualifies.

1. **Dormant flag** — an existing option never used as an episode. Scan the
   scene's docstring first.
2. **Shape / container swap** — re-derive sizing for the new geometry and
   RE-SWEEP the parameters; never copy knobs across shapes.
3. **Motion added to something static** — the container moves, rotates,
   shrinks. The loop ending must return it to its frame-0 state.
4. **Count change** — two sources, two teams, two movers. Re-pace (it usually
   halves build time); the caption follows the new number.
5. **Render-memory change** — the picture KEEPS something it used to discard.
   Render-only; derive per-frame visual state purely from the event log.
6. **Inversion / contest reframe** — remove instead of add, teams instead of a
   count. Strong comment engines.

## 4. De-risk the set

- Mix tiers: 1-2 pure-knob picks anchor the batch; the rest are small opt-in
  flags **defaulting OFF**, so every shipped clip re-renders bit-identically
  (verify against numbers recorded in the scene doc).
- **Sweep until the change READS on screen — measure, don't hope.** If the sweep
  shows the change is invisible, change the pick, not the caption.
- Sweep seeds by the scene's OWN metric (recorded in its doc), not a generic
  duration filter.
- Assign tunes across the WHOLE batch — seed-keyed auto-pick gives two scenes
  on the same seed the same tune. Fix duplicates with explicit `--melody`
  (audio-only, no re-render).

## 5. Ship as one batch

- Per-episode verification = make-video Step 2 (stills → `-Fast` full →
  `tools/check_clip.py` → `tools/check_loop.py` for any new ending maths →
  `tools/flash_check.py`).
- Stage each validated clip in `final/needs-review/` (mp4s + `.md` only;
  sidecars stay in `output/`), then finish through **ship-clip** (or its manual
  equivalent in make-video Step 4).
- **Queue 4K renders — 2-3 concurrent encodes max**, counting caption passes.
  Batches are where pile-ups kill ffmpeg pipes.
- Metadata twice per clip (chat + `<stem>.md`): 3-4 titles of different types +
  pinned comment, each naming the episode's change where natural.
- New lessons into each `docs/scenes/<scene>.md` in the same session. Never
  `git commit` unprompted.

## Tooling to build once the niche is chosen

- `tools/ship_batch.py` — one BATCHES table for the set: verify, stage, sidecar
  guard. Until then: per-clip manual staging + `ls final/<folder> | grep -E
  'json|wav'` must be empty.
- A per-scene `--scan N` seed-search convention (scene-local) scoring the metric
  the video is about.
