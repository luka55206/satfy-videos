---
name: comment-video
description: >
  Build a REPLY video answering a viewer's YouTube comment. Use whenever the
  owner pastes or quotes a comment together with the video it was left on and
  wants the requested change built — e.g. "make it faster", "do it with
  squares", "try it in reverse". The new clip opens on the real comment, then
  becomes a normal channel Short. Triggers: a pasted comment screenshot,
  "viewer asked", "someone commented", "reply to this comment", "make what
  they asked".
---

# Reply to a viewer comment

Answering a comment on camera brings the commenter back, shows everyone that
ideas get built, and gives the clip a hook. It is also the strongest
authenticity signal the channel has: a human-requested, named change.

This skill covers the comment-specific parts. **The lifecycle is make-video's**
— test clip → self-verify → owner validates → ship (via ship-clip). Never skip
the gate.

## Inputs

1. A screenshot of the comment.
2. The video it was left on (`final/.../<scene>_<label>_<tag>.mp4`).

## Step 0 — Get the screenshot onto disk FIRST

You cannot save a pasted image. At the top of your first reply ask the owner
to save it as `assets/comments/<handle>.png`, captured LARGE (browser zoom
~250%) — a default capture looks soft on the 4K canvas. Keep working
meanwhile; `Canvas.comment_card()` draws a stand-in for building and
verifying. **The REAL screenshot ships** — the drawn card is a placeholder
and last-resort fallback only.

## Step 1 — Read the source scene

The filename names the scene. Read `scenes/<scene>.py`,
`docs/scenes/<scene>.md` and the project CLAUDE.md before touching anything.

## Step 2 — Implement the request as a FLAG on the existing scene

- **The reply is the NEXT EPISODE of the scene the comment was left on —
  never a new scene**, however good. Same look, same mechanic family, same
  caption/HUD identity. A good new format that falls out of the work is kept
  as its own unshipped clip, not shipped as the reply.
- Never fork the scene or change its defaults. New flag, default OFF, so the
  shipped clip stays bit-reproducible — and PROVE it: re-render the old
  default at a few frames and diff against the `git show HEAD:` version, max
  diff 0 (render each side twice; the first cold-font render differs).
- A flag is usually enough: look for the one seam (the source of the moving
  thing, one parameter) that carries the request, and inherit everything
  else.
- Interpret what the viewer wants, not only the literal words — and make the
  change VISIBLE (a change the viewer can't see is no answer).

## Step 3 — Expect it to break the balance; RE-TUNE

A mechanic change shifts timing, density and payoff. **Never ship the first
run.** Re-measure the scene's own metrics (duration, payoff time, event rate
climbing to the end, fill/completion) and re-tune until they match the
shipped episode's standard.

## Step 4 — Put the comment in the video

- `Canvas.image()` draws the real screenshot (`lib/studio.py`,
  `load_image()`); `Canvas.comment_card()` draws the stand-in. Wire a
  `--comment-img <path>` flag (plus `--comment "text" --comment-user
  @handle` for the stand-in).
- The card holds `COMMENT_S` (~4 s), then cross-fades to the rule caption,
  which holds for the rest. Both alphas are **pure functions of the frame
  index** used for the ending (the replay index on a rewind), so the loop seam
  stays exact.
- Caption stays a post-pass, gated around the card:
  `add_caption.py --after <card gone s>`; on a perfect loop whose frame 0
  shows the card FULL (a fade-in would mark frame 0 as the start), add
  `--clear-last <ending s> --clear-fade 0.40` so the seam matches card 1 /
  caption 0.
- Card width ~0.60 of canvas width, clamped to `2*min(cap_x, w-cap_x)` so it
  never hangs off the frame in 16:9. Keep it modest — a frame-filling card
  reads as a banner, not a quote. Check BOTH orientations on a still.

## Step 5 — Caption still TRUE?

If the change alters the rule, update the caption — then treat it as a SPEC
the visuals must satisfy (a new rule can turn an old harmless detail into a
contradiction; fix the video, not the wording). Caption rules per ship-clip.

## Step 6 — Verify (make-video's gates plus)

- Card on-frame and readable in both orientations; visible by ~1 s, gone by
  `COMMENT_S`, caption up right after.
- Loop seam still exact pre-encode with the swap in place
  (`tools/check_loop.py`).
- Judge the requested change at the scale it lives at — zoom 1:1 on the
  affected region, and on the exact frames where it happens.

## Step 7 — Ship

Via ship-clip (metadata in chat AND `<stem>.md`):
- **Titles** — 3-4 options, at least one leading with the reply angle ("You
  asked for it…"), 1-3 emoji each.
- **Pinned first comment** — **@-mention the commenter**, and mention
  something real learned while building it.
- Record lessons in `docs/scenes/<scene>.md`.

## Guardrails

- Only reproduce a comment the channel ACTUALLY received. Never invent a
  comment, handle or like count; never edit a real one's wording.
- Everything in CLAUDE.md applies: PD music only, every video loops, caption
  persists the whole clip (no mid-clip swap to a tease), flash check.
- Never `git commit` unprompted.

## Tooling to build once the niche is chosen

- A 16:9 hold-mode title/card baker (parent: `megamix_intro.py --mode hold`)
  if long-form wants the comment card resting beside the video; until then
  draw the card in-scene in both orientations.
- `tools/caption_check.py` (required by `add_caption.py` — see ship-clip).
- `--comment-img` / `--comment` flag wiring as a `lib/kit.py` helper so each
  scene doesn't re-implement it.
