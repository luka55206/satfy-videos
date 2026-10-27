---
name: youtube-upload
description: Upload finished Shorts to the project's YouTube channel (identity in lib/channel.py) through the owner's Edge via the Claude-in-Chrome extension and SCHEDULE them into the day's slots around whatever is already scheduled or published — Studio upload form end to end (title, synthetic-content disclosure, ad-suitability rating, related video, schedule), then the pinned first comment once each goes live, short casual replies to viewer comments, the ledger, and the move to final/uploaded/. Use whenever the owner says "upload these", "schedule these shorts", "put these on YouTube", "pin the comments", "reply to comments", or hands over clips for YouTube.
---

# YouTube upload — scheduled Shorts

**Scope: 9:16 Shorts only** (`<stem>_9x16.mp4`). Long-form uploads are out of
scope until this skill grows a section for them. Ledger:
**`final/YOUTUBE-UPLOADS.md`** (created on the first `record`). Everything
mechanical — metadata, order, slots, ledger, file moves — goes through
**`tools/yt_upload_prep.py`** so it comes out identical every run; the browser
part is this file.

## Before the first real upload — tool constants still carry the parent's values

`tools/yt_upload_prep.py` was ported from the sibling channel and has NOT been
re-tuned. Set these (owner's call, once the niche is chosen) — until then,
check each one before trusting its output:

| constant / spot | parent value | what to decide |
|---|---|---|
| `TITLE_SUFFIX` | `" #usa"` | keep only if this niche targets the US audience (parent-channel evidence — re-validate) |
| `COMMENT` | "Drop a simulated idea 👇 / and it might be the next video 👀" | the niche's fixed pinned comment |
| `SLOT_HOURS`, `PER_DAY` | `(14,18,22,2,6)`, 5 | slot grid + cadence (see §3) |
| `day_key` / `day_slots` | day boundary hard-coded at 14:00 (`hours=14`, `h < 14`) | must move with the first slot hour |
| `TZ` | fixed UTC+4, labelled Tbilisi | does NOT read `lib/channel.TIMEZONE` — keep in sync by hand |
| `non_pd_music()` | imports `tools/longform_audio_guard.py` | **that module is not in this project — `record` crashes** until it is ported or the call is removed |
| `cmd_order` family | first stem token | fine if stems start with a family word; otherwise define families |
| module docstring | "3 slots … 14:00 22:00 06:00" | stale vs the code (5 slots); trust the code |

## 0. Browser + channel (every session)

1. **THIS PC's Edge, PROVEN local** — follow `.claude/skills/crosspost/` §0
   exactly (start Edge first, select the deviceId stored in
   `.claude/browser.local`, prove it with the marker/localhost check).
   `isLocal:true` is NOT proof. Never ask which browser.
2. **Channel identity comes from `lib/channel.py`.** If `CHANNEL_ID` is empty
   → **STOP** and tell the owner the channel isn't configured. Otherwise open
   `https://studio.youtube.com/channel/<CHANNEL_ID>/videos/short` and check
   BOTH: the URL still carries `<CHANNEL_ID>` after load (Studio silently
   redirects to the active channel) AND the sidebar/avatar name equals
   `CHANNEL`. Wrong → avatar → Switch account → re-check. Same check on
   youtube.com (avatar menu → active account header) before any comment.

## 1. Pinned-comment pass — FIRST, every session

YouTube refuses comments on a scheduled video until it is live.
`python tools/yt_upload_prep.py due` lists ledger rows now live with comment
`pending`. For each:

1. Open `https://www.youtube.com/shorts/<ID>` → click the comments button
   (`find` "View comments" / aria-label containing "comments").
2. **Existing pin first**: a thread with `#pinned-comment-badge` is already
   pinned and ours would REPLACE it. Our fixed comment already pinned → just
   mark it. Any OTHER pinned comment → leave it, ask the owner.
3. **Identity**: `#avatar-btn` → `ytd-active-account-header-renderer` must
   read the channel. (Escape doesn't close that menu; harmless.)
4. `#simplebox-placeholder` → type line 1 → `shift+Return` → line 2. Text =
   the tool's `COMMENT` (not the clip .md's). `#contenteditable-root`
   innerText DROPS emoji — verify emoji on a zoomed screenshot. Submit:
   `ytd-commentbox #submit-button button` (JS click works).
5. Our new thread lands on top → `find` its "Action menu" (⋮) → click →
   `find` **Pin** and click BY REF — **Delete sits right under Pin**; never by
   coordinates (a JS menu-item query once matched the sidebar).
6. Dialog "Pin this comment?" → `find` its Pin → click → confirm
   `#pinned-comment-badge` reads "Pinned by @<handle>".
7. `python tools/yt_upload_prep.py pinned --url <url>`.

- **The first Pin click often doesn't register** (menu stays open, no
  dialog). Screenshot, click the same ref again; always `find` the dialog
  before assuming the pin happened.
- **One tab at a time**: comments don't render in a background tab, and
  acting in a second tab can close the first tab's menu.

## 1b. Replying to viewer comments — casual, short, hearted

With a comment panel open (or when the owner says "reply to comments"):

- **1-4 words or emoji only**, a real creator's voice — never "Thank you so
  much for watching!". A question gets a 2-3 word answer.
- Match their energy and emoji; vary loosely (identical replies read as a bot).
- **Heart every comment we reply to** (confirm red on a screenshot).
- Skip spam, hate, anything that needs an argument — no reply, no heart.
- **Never promise a video.** Requests go to the owner in the report.
- Stops each session: the videos §1 pinned, then the Studio inbox
  `https://studio.youtube.com/channel/<CHANNEL_ID>/comments/inbox`, filtered
  to not-responded, newest first (target count is the owner's call; the parent
  did 20). Unanswerable questions are skipped.

## 1c. Compliance gate (mandatory, every clip, before the form)

Run `python tools/compliance_check.py --title "<title>" --description "<desc>" --tags "<tags>"`
on EVERY title/description/tag set. Any FAIL = fix the text first. Never use the
mechanic's trademarked name or money/prize wording. Answer the synthetic-content
question honestly (see `docs/compliance.md` section 5).

## 2. Queue, order, metadata

1. **Clips**: the owner's list, resolved to `_9x16.mp4` in
   `final/ready-to-upload/` (subfolders too). **No list → pick them yourself,
   never ask**: family absent from the channel longest (ledger + Studio list —
   manual uploads count) → stronger family first (newest
   `reports/*_channel_analysis.md`) → oldest in the queue; never two of one
   family in a batch when avoidable. State picks + one-line reasons in the
   report.
2. **Order = the order the owner wrote them.** Random only when he didn't
   list them: `python tools/yt_upload_prep.py order <clips…>` (keeps same
   family apart).
3. **No photosensitivity line on a Short** (long-form only).
4. **Metadata**: `python tools/yt_upload_prep.py meta <clips…>` → per clip
   `title_options` (suffix appended, ≤100 chars), `problems`, `description`
   and `tags` returned `""`. Non-empty `problems` → write the title by hand.
   **Parent-channel evidence — re-validate on this niche:** Shorts shipped with
   NO description, NO tags, and `#usa` as the only hashtag (at the end of the
   title) tested better there.
5. **Title**: the owner's pick if named; otherwise the best option by the
   project's channel-direction notes. Never a title published in the last few
   weeks (check ledger + Studio) — near-duplicate titles cannibalise.

## 3. Schedule slots

**Cadence — parent-channel evidence, re-validate on this niche:** 5/day beat
3/day there (3/day gave ~+20% per clip but 30-46% fewer views per upload day,
same breakout rate per clip — more uploads = more lottery tickets). Start from
the owner's chosen cadence and re-test with this niche's own data.

1. In Studio **Content → Shorts** read every **Scheduled** Short (date + time)
   and every one **published in the last ~24 h** (open its youtube.com page for
   "N hours ago" only when it could sit within 45 min of a candidate time).
   Manual uploads count. Long-form doesn't.
2. `python tools/yt_upload_prep.py slots --count N --existing "YYYY-MM-DD HH:MM" …`
   (local time per `TZ`). **A slot is a TARGET, not a gate**: a missed slot
   is never skipped — it goes out ASAP (now+10 min, next 15-min mark). **The
   one strict rule: ≥ 45 min between any two Shorts** (the tool pushes forward
   in 15-min steps). **Always run the tool; never pick or skip a time by
   hand.** If the form runs past the given time, re-run `slots` right before
   Schedule.
3. "Publish now" → `--immediate` (now+10 min as a SCHEDULE, never the Publish
   button).
4. State the plan (clip → time → title) in chat, then upload.

## 4. The upload form — one clip at a time

Open `https://studio.youtube.com/channel/<CHANNEL_ID>/videos/upload?d=ud`.
Set `document.title='NFUPLOAD YouTube Studio'` on that tab (another Studio tab
in the window can steal the picker), then:

```powershell
$S = ".claude/skills/crosspost/scripts"
powershell -NoProfile -ExecutionPolicy Bypass -File $S/activate_edge_tab.ps1 -TitleMatch "NFUPLOAD"
powershell -NoProfile -ExecutionPolicy Bypass -File $S/pick_file_dialog.ps1 `
  -Path "<abs path>\<stem>_9x16.mp4" -InvokeButton "Select files" -WindowTitleMatch "NFUPLOAD" -TimeoutS 40
```
`activate_edge_tab` must print `ACTIVE:` (extension tabs are not active).
`NO_BUTTON` right after navigating = a11y lag, wait ~3 s and retry; still
`NO_BUTTON` → crosspost §2's extension-click fallback. Studio prefills the
title with the filename.

**Details**
1. Title: focus by JS (`[contenteditable=true]`[0]) — a ref click + Ctrl+A
   once put everything into the title — select all, type the title, then a
   **trailing space** so a hashtag autocomplete closes instead of rewriting
   it (`#usa` → `#usanewstoday` happened).
2. Description / Tags: per §2.4. Read back before Next:
   `[...document.querySelectorAll('[contenteditable="true"]')].map(b=>b.innerText)`.
3. **Altered or synthetic content** (in "Show more"): answer HONESTLY against
   YouTube's CURRENT wording, read on the form at upload time — never from a
   hard-coded rule. Its scope is realistic content a viewer could mistake for
   a real person, place or event; stylised, clearly non-realistic
   code-rendered animation normally falls outside it. If this niche's clips
   ARE realistic or synthetic depictions of real things, the answer is Yes.
   Unsure → ask the owner, don't guess. Honest disclosure does not demonetise;
   a wrong answer is the policy risk.
4. Audience: leave the channel default (set once in Studio → Settings →
   Channel → Advanced; confirm it is "not made for kids" unless the niche is).

**Monetisation guard (inauthentic / mass-produced content):** YouTube's policy
targets repetitive, templated uploads with only cosmetic differences. Before
uploading a batch, confirm each clip differs in something a viewer could name
(not just seed/colour/music) and titles aren't one formula. Flag doubts to the
owner instead of uploading.

**Ad suitability**: tick **None of the above** (verify — the rating is final)
→ side panel reads **Safe for ads** → **Submit rating** → "Rating saved" → Next.
Only tick a category if the clip really contains it.

**Video elements**: Related video → Add → "Choose specific video" → the Short
published directly before this slot. Scheduled Shorts are never offered →
take the newest PUBLIC one and note the swap in the related column.

**Checks**: nothing → Next.

**Visibility** opens on Save/Unlisted — **never press Save**. Expand
**Schedule** (defaults to tomorrow 00:00):
1. **Time zone** → the entry matching `lib/channel.TIMEZONE` (usually the top
   "Local Time" entry when the PC is in that zone — check its GMT offset).
2. Date → calendar → the slot's `studio_date`.
3. Time: **typing doesn't stick** ("Select a time in the future"). Click the
   field (the first click after the zone menu only closes it — click again),
   `find` `studio_time` in the 15-min dropdown, `scroll_to` + click, re-read
   the value (compare after `.replace(/\s/g,' ')` — Studio uses a narrow
   no-break space). Off-grid time won't stick → next 15-min option, record it.
4. Read back: date, time zone, time value, Schedule enabled.

→ **Schedule**. "We're still checking your content" → **Got it** (advisory).
**"Video scheduled"** dialog → read the date/time back against the slot, copy
the `youtube.com/shorts/ID` URL, Close. Don't start the next clip until the
upload finished (closing mid-upload loses it).

**Record** (ledger row, moves both mp4s to `final/uploaded/`, deletes the .md):
```
python tools/yt_upload_prep.py record --clip <9x16 path> --when "YYYY-MM-DD HH:MM" --title "<as uploaded>" --url <url> --related "<related title>"
```

## 5. Verify + report

- Studio Content → Shorts: every new row **Scheduled** at its slot.
- `final/ready-to-upload/` no longer holds the uploaded pairs.
- Chat: table clip → publish time → title → URL; pins pending until live.

## Gotchas

- **Never press Escape inside the upload dialog — it CLOSES it** (the upload
  survives as a draft: Content → Edit draft).
- **Never click Details fields by coordinates** — a long title wraps and
  shifts the layout.
- **A failed picker run can leave its Open dialog alive**; the next run
  APPENDS to it ("file name is not valid"). Check no `#32770` dialog remains.
- **Studio UI language follows the account**; `?hl=en` is ignored. On a
  non-English UI, record the translated labels here on the first run. Element
  IDs (`#next-button`, `#done-button`, `#toggle-button`) work regardless;
  the time dropdown may be 24 h.
- **Extension site permissions are per install** — "Permission denied … on
  this domain" until the owner allows studio.youtube.com / youtube.com.
- **Posting a comment can be refused by the auto-mode classifier** when the
  request was only "upload" — ask the owner to confirm the pin pass.
- `meta` parses both `.md` title shapes (`1. **Type** — \`title\`` and
  `1. title (type)`); check `title_options` anyway.
- Record new form/UI facts from each real run in this file.
