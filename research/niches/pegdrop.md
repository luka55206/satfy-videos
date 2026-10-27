# Niche: Peg Drop (peg-board ball-drop simulations)

**Status:** chosen (by the owner, 2026-10-04 -- NOT researched; demand, supply and
RPM are unmeasured. Run `niche-research` scoring before scaling past test clips.)
**One-line pitch:** balls bounce down a field of pegs, land in bins, and the piles
trace a bell curve while the drop rate keeps climbing.

## Hard filters
- [x] Code-renderable at quality (2D rigid circles; `scenes/pegdrop.py`)
- [x] Episodes differ by a nameable change (rows, bins, bounce, drop mode, open lane)
- [x] No borrowed IP: original synthesis only, no tunes, no samples, no game footage
- [x] Short loop/payoff structure (drain to empty board) + 8-10 min compilation structure
- [ ] Advertiser-friendly: UNVERIFIED. The genre sits next to casino content, so the
      channel is a physics/statistics toy: no money, prizes, multipliers, "win" wording.

## Naming (hard rule, see docs/compliance.md)
The common name of this mechanic is a registered trademark (FremantleMedia, The Price
Is Right). It never appears in titles, descriptions, tags, hashtags, file names,
thumbnails or on-screen text. Use: **peg board, ball drop, bean machine, Galton
board, bell curve, ball physics**. Trade-off: it is also the biggest search term;
that is the price of the safe default. Only the owner can change it
(`lib/compliance.ALLOW_TERMS`), and should check the current trademark record first.

## Scores (0-5, evidence required)
Not scored. No competitor data was pulled in this session.

## Look and sound
- Look: dark board, light-blue pegs that flash on a hit, rainbow-by-drop-order balls
  (`kit.wheel`), piles tinted per ball. Neon-on-black palette kept from the engine.
- Sound: pentatonic scale by peg position ("gravity harp") + a low chime on landing.
  Marimba voice, synthesised. No melodies (bank locked), no samples, no music beds.

## 10 episode ideas (each with ONE nameable change)
1. 6 rows vs 16 rows -- "the shallow board"
2. Open middle lane (`--lane center`) -- "the middle is open"
3. Drop point sweeps left to right (`--drop sweep`)
4. Super-bouncy pegs (`--bounce 0.85`)
5. Dead pegs (`--bounce 0.2`) -- balls barely bounce
6. 6 bins vs 14 bins
7. Random drop point (`--drop random`)
8. Narrow board, tall (cols 6, rows 16)
9. A peg field with one rotated/shifted row (code change)
10. Two-colour teams, left half vs right half (code change)

## Engine changes done
- melody bank locked empty; `lib/compliance.py` + `tools/compliance_check.py`
- `scenes/pegdrop.py`; `galton.py` kept as the scripted bell-curve sibling

## Engine changes still needed
- Rendering/validation: this PC has no Python/ffmpeg yet; `pegdrop` has NOT been run.
- Font: cairo uses system "Arial". Switch to an open font (OFL) if you want zero doubt.
- Thumbnail lib, batch shipper (listed at the end of each skill).
