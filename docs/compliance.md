# Compliance: copyright, trademark, platform policy

Compiled 2026-10-04 from public policy as understood then. Risk reduction, not legal
advice. YouTube's wording changes: re-read the current policy at upload time.
Enforced in code by `lib/compliance.py`; run `python tools/compliance_check.py`.

## 1. Copyright (audio, visuals, text)
- Every frame is drawn by our code. No footage, screenshots, game assets, stock, or
  AI-generated media. No imitation of a specific game's look.
- Audio is OUR synthesis only. The melody bank is **locked empty** even though some
  tunes are public domain: PD compositions still draw Content ID claims from other
  uploads of the same tune. No samples, no music beds, no downloaded SFX.
  Enforced: `compliance.scan_scene_source` (scenes) and `scan_events` (sidecar).
- Fonts: the engine asks cairo for "Arial" (system font, text rendered into pixels).
  Low risk; swap to an OFL font (Liberation Sans / Inter) for zero doubt.
- Compilations use only OUR clips.

## 2. Trademark
- The mechanic's common name is a registered mark (FremantleMedia / The Price Is
  Right). Never in title, description, tags, hashtags, file names, thumbnail, on-screen
  text, channel name or handle. Say: peg board, ball drop, bean machine, Galton board.
- Also blocked: other brands and IP (see `BANNED_IP`): game titles, other creators.
- Search-reach cost is accepted on purpose. Relaxing it is the owner's call, in
  `ALLOW_TERMS`, after checking the current trademark record.

## 3. Gambling-adjacent content
- This genre resembles casino games. Keep it a physics toy: no money, currency,
  prizes, multipliers, odds-of-winning, "win/jackpot/bonus", casino styling, no links
  to or mentions of gambling sites, no "crypto". Bins are neutral counters.
- Audience: YouTube may age-restrict or limit ads on gambling-looking content; an
  unmonetised/limited-ads result is possible even when compliant.

## 4. YouTube "inauthentic content" (mass-produced / repetitive)
- Judged at CHANNEL level. A new seed or palette is not a new video: every upload
  changes ONE thing a viewer can name (rows, bins, bounce, drop mode, open lane).
- A human validates each new format/episode before upload (CLAUDE.md workflow).
- Cadence: start low (a few a week) while formats are validated; scale only with
  evidence from the channel's own analytics.

## 5. Disclosure
- Answer YouTube's altered/synthetic-content question honestly at upload. Stylised,
  obviously-animated output is normally "no", but check the current wording.
- Description line: one honest sentence that the video is simulated by code.

## 6. Pre-upload checklist (all must be true)
1. `python tools/compliance_check.py --title "..." --description "..." --tags "..." --clip <output clip>` exits 0
2. `python tools/compliance_check.py --scenes` exits 0
3. `tools/flash_check.py` + `tools/check_clip.py` pass on the muxed mp4
4. Owner has watched it (HARD STOP in the workflow)
5. Title/description contain no price, money or prize language
