---
name: crosspost
description: Upload a finished clip to TikTok and Facebook through the owner's Edge via the Claude-in-Chrome extension — pick the clip (given path, or the oldest already-on-YouTube clip not yet crossposted, skipping only weak ones, never the best performers first), drive the real Windows file picker, write the caption, set a climax cover frame, post or schedule, record in final/CROSSPOST.md. Also holds the shared "prove this PC's browser" setup and file-picker scripts the youtube-upload and youtube-analytics skills use. Use whenever the owner says "upload this to tiktok/facebook", "post the next one", "crosspost", "sync with youtube", or hands over a clip for the socials.
---

# Crosspost — TikTok + Facebook

**Platform roles (parent-channel model — confirm with the owner for this
niche):** Facebook = MONETISATION (Reels for Shorts, regular video posts for
long-form, occasionally). TikTok = COMMUNITY — Shorts only, **never long-form**.
YouTube leads; the socials lag and catch up. **Same clip to both platforms on
the same day, one shared cadence** (parent ran 3/day, posts ≥ 6 h apart so each
gets its own test window). Never mass-upload a backlog.

Identity: the channel name is `lib/channel.CHANNEL`; the Facebook Page and
TikTok account for it are recorded at the top of **`final/CROSSPOST.md`**
(ledger: every post, both platforms, source file). Read it first. Channel not
configured (`CHANNEL_ID` empty) or no Page/account recorded → **STOP** and ask.

Helper scripts live in **`.claude/skills/crosspost/scripts/`**:
`activate_edge_tab.ps1`, `pick_file_dialog.ps1`, `verify_local_browser.ps1`.

## 0. Browser setup (every session — shared by all upload/analytics skills)

1. **Use THIS PC's Edge, and PROVE it** — never ask which browser. Another PC
   on the same account can be listed too, and **the extension's `isLocal`
   flag and display names are NOT proof** (another PC reported `isLocal:true`
   and got picked when Edge was closed).
   a. `Get-Process msedge` empty → `Start-Process msedge`, wait ~8 s, BEFORE
      listing, so a remote browser is never the only option.
   b. THIS PC's proven deviceId lives in **`.claude/browser.local`**
      (gitignored; lines `deviceId=<id>`, `computer=<$env:COMPUTERNAME>`,
      `proven=<date>`). File present and `computer` matches →
      `list_connected_browsers` → `select_browser` that id (by ID, not name).
      Missing or `computer` differs → try each listed browser with step c and
      write the file for the one that proves LOCAL. **Never use a deviceId
      that hasn't passed step c this session.**
   c. **Proof:** navigate to a real https page, `javascript_tool` →
      `document.title='NFLOCAL-<random>'`, then
      `powershell -NoProfile -ExecutionPolicy Bypass -File .claude/skills/crosspost/scripts/verify_local_browser.ps1 -Marker NFLOCAL-<random>`.
      Not `LOCAL` → wrong browser (but it can FALSELY say `NOT_LOCAL` when the
      tab isn't active). Decisive proof: serve a random-named file from the
      scratchpad (`python -m http.server <port> --bind 127.0.0.1`, background),
      navigate to `http://127.0.0.1:<port>/<file>`, `get_page_text` shows the
      marker = LOCAL. `file://` is refused by the extension.
   d. Extension switches instance mid-session → `select_browser` the SAME
      proven id; never log in elsewhere.
2. `tabs_context_mcp createIfEmpty:true` → one tab per platform. **The file
   picker targets the ACTIVE tab of the Edge window, and `tabs_create_mcp`
   does not activate it** — run
   `scripts/activate_edge_tab.ps1 -TitleMatch "<page title>"` before every
   picker call and check it prints `ACTIVE:`. A picker run on the wrong tab
   still "succeeds" into a tab the extension can't drive (TikTok then offers
   it as "Continue editing?" next load).
3. **TikTok's login redirect kicks the tab out of the group** — navigate to
   `/tiktokstudio` FIRST, then `/tiktokstudio/upload`.
4. Extension clicks don't need focus; the picker foregrounds Edge ~2 s.

## 1. Pick the clip

- Owner gives a path → use it.
- No path → **OLDEST FIRST among clips already on YouTube** (`final/uploaded/`,
  then long-form folders' clips in their order), then `ready-to-upload/`.
  **NEVER pull the best performers forward** — the backlog runs out of good
  clips fast. Skip only weak ones: clips well under their era's median views
  (Studio export `reports/exports/<date>/content/Table data.csv`, match title
  → file by caption + duration) or formats the latest report says to stop.
- Subtract the ledger — once per platform. Progress marker: the "Queue"
  section of `final/CROSSPOST.md`.
- Shorts → the **9:16** file. Long-form (`final/long-form/…`) → Facebook only.

## 2. Get the file into the page — `scripts/pick_file_dialog.ps1`

The extension's `file_upload` caps at 10 MB and its synthetic click never opens
the OS picker. What works on both sites:

```powershell
$env:PICK_DEBUG_DIR = "<scratchpad>"   # optional desktop PNGs
powershell -NoProfile -ExecutionPolicy Bypass -File .claude/skills/crosspost/scripts/pick_file_dialog.ps1 `
  -Path "<abs path>\<stem>_9x16.mp4" -InvokeButton "Select video" -WindowTitleMatch "TikTok Studio" -TimeoutS 30
```

- `-InvokeButton` = the button's accessible name: TikTok `"Select video"`;
  Facebook Create-reel `"Add video or drag and drop"` (title match
  `"Create reel"`). The script UIA-invokes it, waits for the msedge-owned
  `#32770` dialog, real-clicks the file-name box (AutomationId `1148`), selects
  with HOME+SHIFT+END (Ctrl+A is layout-dependent), types, clicks Open. Success
  ends `DIALOG_CLOSED`.
- `NO_BUTTON` on the wrong tab = §0 activation problem.
- **`NO_BUTTON` on the RIGHT tab = Edge didn't expose the page to UIA. Click
  with the extension instead**: `find` the button ref → start the script
  WITHOUT `-InvokeButton` in the BACKGROUND (it polls for the dialog) →
  `computer left_click` the ref (a trusted gesture that opens the real picker)
  → output ends `DIALOG_CLOSED`. The script must be polling before the click.
- **First click after a `navigate` often misses** (stale ref → `NO_DIALOG`):
  re-`find`, click the fresh ref, restart the script. On Facebook, a fresh
  coordinate click on the box centre works when refs fail twice.
- **Cover PNG → `file_upload` directly** into the `input[type=file]` under
  "Upload cover" (TikTok) / "Edit thumbnail" (Facebook). Only the video needs
  the OS picker.
- Don't: SendKeys Alt+N/Enter (inline-rename / cleared box), UIA
  `ValuePattern.SetValue` (times out). A path rejected → WM_CLOSE the error
  box, fix, Open — never retype from scratch. A zombie dialog from a failed
  run → WM_CLOSE by handle, reload. The extension can't see OS dialogs — take
  a desktop screenshot when unsure.

**Coordinates go stale, refs don't.** The screenshot frame is scaled from CSS
pixels; modals move between renders. Prefer `find` + ref; if a coordinate is
unavoidable compute `rect * (frameWidth / innerWidth)` fresh and click in the
same turn. Verify focus (`document.activeElement`) before typing.

## 3. TikTok Studio (`tiktok.com/tiktokstudio/upload`)

1. Picker (§2) → wait for "Uploaded (NN MB)".
2. Dismiss any "New features" popup.
3. Description: `find` the box, click its REF, `End` → `shift+Home` →
   `Delete`, type. **NEVER Ctrl+A** (Draft.js — a miss selects the whole page
   and the filename stays as caption). Hashtags one at a time, `Escape` after
   each. Read back `.public-DraftEditor-content` innerText — the only proof.
4. Cover: upload a PNG (§2). Target the **CLIMAX** (~75-90 % in: most
   progress visible, biggest number on screen), not the post-payoff frame.
   **De-escalating content** (things disappear toward the end) → the densest
   frame that still shows progress. Save.
5. Settings: Now · Everyone · High-quality ON · comments allowed.
   **AI-generated content toggle: answer HONESTLY against TikTok's CURRENT
   wording** — it targets realistic AI-generated/altered media; clearly
   stylised code-rendered animation is normally outside it. Read the label on
   the form each time; unsure → ask the owner. Commercial-content disclosure
   OFF unless it is a paid promotion.
6. Checks: music copyright must say "No issues" — anything else, stop.
7. Post → Posts list. "Only me" + a timestamp badge while transcoding is
   normal; still "Only me" after 15 min → open the row's privacy dropdown.

## 4. Facebook (the Page recorded in `final/CROSSPOST.md`)

**Verify identity before every post**: the composer reads "What's on your
mind, <Page name>?" and the avatar is the Page's. Personal profile → STOP,
switch profile.

Reel (`facebook.com/reels/create`):
1. Picker with `-InvokeButton "Add video or drag and drop" -WindowTitleMatch "Create reel"`.
2. Next → Next → Reel settings.
3. Caption. Public. **AI label: same honest-answer rule as TikTok.**
4. Cover: click **"Edit" EXACTLY ONCE, then WAIT** (up to ~25 s spinner) — a
   second click stacks a second dialog, nothing saves, and only reloading
   `reels/create` recovers (tell: `find` returns two "Edit thumbnail"
   sections). Poll with `find` for the file input → `file_upload` PNG → Save.
5. "Your reel is safe to publish!" → Post. Verify on the Page's videos tab.

"Scheduling options", "Edit" and the final Schedule button often ignore the
first click while the row settles — `find` again and click the ref.

Long-form (> 3 min, Reels cap): the Page's "Upload video" / Meta Business
Suite video post. Thumbnail + description from the long-form folder's
`UPLOAD.md` (incl. its photosensitivity line when it has one).

## 5. Caption format

```
<Title line> <description of what happens, ending with the payoff>.
<call to turn the sound up / follow, if the niche has sound>
<3-5 niche hashtags>
```
Same text on both platforms. Title line = the YouTube title (the proven hook;
its emoji count as the caption's — don't stack more). Every number must be true
of the clip. Settle the niche's hashtag set with the owner once and record it
here.

## 6. After posting

- Append the ledger row (`final/CROSSPOST.md`): #, date, duration, title,
  TikTok views, FB views/URL, source path, YouTube views.
- Close the tabs you created. Never delete posts; flag weak ones.

## 7. Scheduling instead of posting now

- **TikTok**: "When to post" → `Schedule` → "Allow … scheduled posting?" →
  Allow. The time field is READ-ONLY and ignores wheel scroll: open it and
  click `span.tiktok-timepicker-option-text.tiktok-timepicker-left` (hour) /
  `.tiktok-timepicker-right` (minute) via DOM (`scrollIntoView` + `.click()`
  on the span AND its parent); Escape closes. **Read the field off a
  SCREENSHOT** — an input scan returns the pre-click value. Button becomes
  `Schedule`.
- **Facebook**: Reel settings → `Scheduling options` (re-click if ignored) →
  `find` the time field, `triple_click` its REF, type e.g. `8:30 AM`, click the
  single `[role="option"]` at coordinates computed FRESH → `Schedule for
  later` → row reads "Today at 8:30 AM" → `Schedule`. **Ctrl+A selects the
  whole page**; a stale coordinate picks the wrong suggestion. Business Suite
  planner URLs may not be reachable from the extension — verify scheduled
  reels in the Page's Professional dashboard by hand.
- Ledger date column: `<go-live time> (SCHEDULED)`; fill real numbers next
  session.
