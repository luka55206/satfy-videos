---
name: redesign
description: >
  REDESIGN a proven scene into a NEW scene file (the original stays
  bit-reproducible). Three levels: EASY = new look · NORMAL = new look + new
  rule · HARD = new look + new rule + new structure. Use whenever the owner
  points at a shipped clip and asks for a "redesign", "upgrade", "remake",
  "make it new", "use only the core idea, everything else new", or stacks
  several changes at once (new container, new visuals, new effects, new
  sound). A level word wins; otherwise "change the look, keep the concept" =
  EASY, a plain "redesign" = NORMAL, "only the core mechanic, everything else
  new" = HARD. NOT an episode: an episode changes ONE nameable thing and keeps
  the scene and its look.
user-invocable: true
---

# Redesign — three levels

| job | keeps | changes | ships as |
|---|---|---|---|
| **episode** (make-video Mode C) | the scene AND its look | ONE nameable thing | a flag on the existing scene |
| **EASY** | rule, story, caption | the LOOK | a NEW `scenes/<name>.py` |
| **NORMAL** | the core rule | LOOK + ONE new rule | a NEW `scenes/<name>.py` |
| **HARD** | the core rule | LOOK + new rule + STRUCTURE | a NEW `scenes/<name>.py` |
| **new format** (make-video A/B) | nothing | everything | a new scene from zero |

A redesign is the cheapest way to get a genuinely NEW video out of a PROVEN
format: the core already works and has a doc of measured lessons, so the risk
sits only in what you replace. It is also a strong answer to the
inauthentic-content policy — the result must differ in ways a viewer sees, not
in colour.

- **Rule** = the format's core law. Every level keeps it.
- **Look** = everything seen and heard: object/machine design, colours,
  effects, HUD styling, SFX/music. Rebuilt at EVERY level, never ported.
- **New rule** = one added law that changes what HAPPENS, so the story and the
  caption change with it. **The new rule is the gate**: none = EASY.
- **Structure** = the container/stage, the generator setup (forces, scale,
  pacing model) and the loop construction.
- **The level sets WHAT may change, never how much checking.** Every level gets
  the full verification ladder (§9).
- **Look check, every level:** parent's frame 0 beside the new frame 0. If only
  COLOUR differs, it is not a redesign — at most an episode.

## EASY — new look

The viewer recognises the same video with a new machine in it.
- KEEP = the concept, written as a paragraph in the docstring: rule, story arc,
  HUD, ending type, sound identity, caption.
- Every named part changes COMPLETELY — new to the whole family, not restyled
  (list the siblings before picking).
- §4-5 skipped on purpose; the parent's escalation, ending and destination are
  RE-EXPRESSED through the new parts.
- Probe the new geometry before building (§3); re-search the seed.
- Keep the loop TYPE, re-check its construction — new parts can break it.

## NORMAL — new look + new rule

§0-10 in full; the structure MAY stay when it still serves the new rule — say
why in the doc. When the new rule fights it (loop no longer closes, container
starves the rule), change it.

## HARD — new look + new rule + new structure

NORMAL with the structure rebuilt and nothing skipped:
- new `scenes/<name>.py`; `git diff --stat` on the parent is EMPTY;
- KEEP list of ≤ ~3 bullets (§2); the new rule pays for escalation, ending and
  destination together (§4);
- new container, new generator setup, new loop construction — even where the
  parent's would still work;
- perfect loop hunted BEFORE building, with a STRUCTURAL seam (§6);
- all-new effects pass obeying the source-clock / finite-life invariant (§8);
- new SFX, melody measured on the sidecar (`len(set(notes))` ≥ 8, top pitch
  ≤ ~25%);
- caption checked against the CODE PATH (§5);
- `docs/scenes/<new>.md` with an OPEN PROBLEM section;
- both orientations, `flash_check`, metadata `.md`, staged in
  `final/needs-review/`.

**Batch of N redesigns = N different families.** Loop variety is NOT a rule:
each clip takes the BEST loop it can honestly close; variety only breaks ties.

## 0. Selection — only when the owner named no clip

- Newest report in `reports/`: rank families by median views (and
  stayed-to-watch); one clip per family, top N.
- Skip a family redesigned in the last ~week, anything on the niche brief's
  stop list, and anything mid-build elsewhere (untracked `docs/scenes/*.md`).
- If the owner states the criterion ("most viewed"), use it literally.

## 1. Read the DOC, not the video

`docs/scenes/<scene>.md` is the brief. Look for its OPEN PROBLEM — or, usually,
the failure it ADMITS with a number attached (a sentence that reads like an
apology), and invert it. Read the episode history so the redesign isn't a
re-skin of a shipped episode. Also read the niche brief.

## 2. KEEP list first (NORMAL/HARD)

In the new file's docstring, state exactly what carries over — and that nothing
else does. More than ~3 bullets → it's an episode, not a redesign.

## 3. Apply the owner's asks literally — then find what they BREAK

Asks are parameters, not the design; moving several knobs on a tuned scene
almost always breaks the ending or the escalation. **Measure the breakage
before designing the fix**: call `simulate()`/`generate()` directly in a short
probe (it runs far faster than render) across a few configs × seeds, printing
event counts and events/5 s. Never argue a scene into working from its
docstring.

## 4. ONE new rule paying three debts (NORMAL/HARD)

It must supply the ESCALATION, the ENDING and the DESTINATION together.
- **Bounded, linear in an accelerating count** — per-event multipliers on an
  accelerating stream run away. Fix the destination up front (`--target N`).
- **Beat the parent's measured ceiling**, don't dodge it.
- **Give back a tight length control** (a count every seed reaches).

## 5. Judge the GOAL before building (NORMAL/HARD)

1. Is the outcome in doubt, or merely scheduled?
2. Does the viewer have something to root for?
If either is weak, add a STAKE the subject might not get — and make it
GEOMETRIC/structural, not lucky, so every seed delivers near-misses and the
outcome by construction. Verify it at generate time (print REACHED/MISSED); the
caption is a spec.

## 6. Hunt the perfect loop at DESIGN time

Ask "can this format close its own circle?" before building — the answer can
change the ending, HUD and even the rule.
- Accumulation fails the test unless something un-accumulates it (a break, a
  clear-out, a zoom to a bigger stage).
- **Make the seam structural**: the ending calls the SAME draw function frame 0
  calls (camera scale as an argument), so there's no checklist of elements to
  return to frame-0 values.
- Nothing frozen while the camera travels; the ending must land on a genuinely
  clean frame.
- Never fake a loop — a near-perfect loop reads worse than an honest rewind.
- (Parent-channel evidence: undetectable loops outranked climax endings —
  re-validate on this niche.)

## 7. New FILE, not flags

Flags on the parent balloon it and endanger every shipped clip. Copy only what's
needed and change it; the old effects pass does not come along. Name the file
for the new idea (`<new_name>.py`, never `<parent>_v2`). Confirm
`git diff --stat scenes/<parent>.py` is empty.

## 8. Look and sound are a REBUILD

- New effects vocabulary, nothing ported.
- **Invariant: every effect is keyed on the SOURCE clock and has a FINITE
  life** — none fired at frame 0, all dead by the payoff. That's what lets the
  ending start clean and the seam land exactly.
- Animate discrete rule changes in a window where nothing collides with them.
- Signature event: consider two sound layers so it gets HEAVIER, not just
  busier. One action = one sound (count sounded events within 60 ms of each
  other). Don't layer noise SFX under a pitched note.
- Re-run the melody health test after ANY seed change (auto-pick is
  seed-keyed); pin the tune explicitly if it fails. PD melodies only.

## 9. Verify cheap → expensive, never skip a rung

1. **Seed scan** (free) — reject: destination missed, non-monotone density,
   long stalls. Score the thing the video is ABOUT.
2. **Stills** (`-Fast -Still`) at 4-6 frames — opening, mid, payoff, loop move,
   frame 0 — and READ them.
3. **Measure what stills can't show**: empty-area brightness (glow wash), frame
   0 vs last (`tools/check_loop.py`), `tools/flash_check.py`.
4. **`-Fast` full clip** → `tools/check_clip.py`: LUFS −14, peak ≤ −3 dBFS,
   per-second RMS, tail silence, events/5 s accelerating.
5. **16:9 still** before the full render.
6. **Full render, both orientations**, `NF_CRF=14` caption-less base, then
   `add_caption.py --out`, then re-measure the seam post-encode (good
   0.12-0.72). Max 2-3 concurrent 4K encodes.

**Seam pre-flight** (each silently breaks otherwise):
- a PULSE driven by the frame index — blend derived values to their frame-0
  values; never wind the phase back;
- an effect frame 0 carries must also be drawn at the landing frame;
- anything keyed on depth/level isn't invariant under a zoom — key on screen
  size;
- a state that ramps during the return must be a pure function of the frame in
  both branches;
- the master reverb outlives the last event — a quiet ending isn't silent; fade
  to true zero or fold the ring-out onto the head.

## 10. Ship

- Perfect loop ⇒ caption `--loop constant`, no rewind scrub. Decide the TAIL:
  ends mid-action → fold the ring-out onto the head (`kit.deliver_wrapped`);
  ends quiet → raised-cosine fade to true zero over ~0.3 s.
- Stage in `final/needs-review/`: the mp4 pair + metadata `.md` (3-4 titles of
  different types + pinned comment) ONLY. Sidecars stay in `output/`. Then
  make-video Step 3 gate, then ship-clip.
- Write `docs/scenes/<new>.md` in the same session, terse: what carries over,
  the measured reason the new rule exists, the shipped command, every trap with
  its number, and an OPEN PROBLEM section — the next redesign's brief.
- Never `git commit` unprompted.

## Tooling to build once the niche is chosen

- `tools/ship_batch.py` with stem registries (no-rewind / wrap / short-tail
  tail-gate exemptions) and the sidecar `--guard`. Until then: choose the tail
  treatment by hand and verify with `check_clip.py`'s last-0.5 s peak.
- A rewind-SFX tool if the niche uses rewind loops.
- A shared `--scan N` seed-scan helper in `lib/kit.py`.
