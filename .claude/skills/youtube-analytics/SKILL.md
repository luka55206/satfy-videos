---
name: youtube-analytics
description: Pull every YouTube Studio metric for the project's channel (identity in lib/channel.py) through the owner's Edge — content table, traffic sources, content type, device, geography, age, gender, sharing service, per-video retention curves — as CSV exports into reports/exports/<date>/, run tools/yt_analytics.py over them, write reports/<date>_channel_analysis.md with what changed since the last report, publish a shareable page, and write each ledger clip's measured outcome into its docs/scenes/<scene>.md. Use whenever the owner says "analyse the channel", "check youtube studio", "how are the videos doing", "score the batch", "pull the analytics". Read-only on YouTube.
---

# YouTube analytics — the channel readout

Everything mechanical (unzipping, families, cohorts, correlations, retention in
seconds, outcome blocks) goes through **`py -3 tools/yt_analytics.py`** so two
reports a month apart compare like for like. The browser part and the WRITING
are this file.

**Read-only.** It never changes a title, description, visibility, thumbnail or
comment, so it can run unattended. Anything outside Studio (YPP emails,
strikes) it cannot see — ask the owner.

**When:** on request, ideally when the latest batch is **≥ 7 days old**
(younger Shorts are still climbing; the tool lists them as "too young").
Read the newest `reports/*_channel_analysis.md` before writing conclusions.

## Before the first run — tool constants still carry the parent's values

| constant / spot in `tools/yt_analytics.py` | state | action once the niche is set |
|---|---|---|
| `NAME_FAMILY` | parent's physics-sim families + scene tokens | replace with this niche's families + clip-stem tokens |
| `TITLE_FAMILY` | parent's title regexes | replace (or empty it and rely on the ledger + `reports/video_families.csv`) |
| `LONGFORM_SEC = 180` | Shorts cap | keep unless Shorts length rules change |
| long-form family label `"megamix"` | parent format name | rename to this project's long-form name |
| `pre_pivot` filter + "physics videos" labels | parent history | harmless; relabel |
| duplicate-title strip `"simulation satisfying shorts"` | parent title boilerplate | replace with this niche's boilerplate (or drop) |
| docstring (blender-physics port, ledger start date, research/channel-performance vocabulary) | stale | ignore |
| `ingest` matches `CHANNEL` in the zip name | reads `lib/channel.py` | with `CHANNEL="TBD"` nothing ingests — correct guard |

Until families are defined, every video lands in `other` — the totals,
correlations, retention and long-form tables are still valid; the family table
is not.

## 0. Browser + channel (every session)

1. **THIS PC's Edge, PROVEN local** — `.claude/skills/crosspost/` §0 exactly.
   `tabs_context_mcp createIfEmpty:true` → work in that tab group.
2. **Channel from `lib/channel.py`. `CHANNEL_ID` empty → STOP.** Open
   `https://studio.youtube.com/channel/<CHANNEL_ID>/analytics/tab-overview/period-default`
   and check BOTH: the URL still carries the id after load AND the sidebar
   reads `CHANNEL`. An analysis of the wrong channel looks perfectly plausible;
   this check is the whole guard.
3. Note the Overview **headline numbers** (views / watch hours / subs, last 28
   days, realtime 48 h) — not in any export.
4. `DATE` = today (YYYY-MM-DD). Exports land in `reports/exports/<DATE>/`.

## 1. Exports — drive Advanced mode BY URL, never by the pickers

```
https://studio.youtube.com/channel/<ID>/analytics/tab-overview/period-default/explore?entity_type=CHANNEL&entity_id=<ID>&time_period=lifetime&explore_type=TABLE_AND_CHART&metric=EXTERNAL_VIEWS&granularity=DAY&dimension=<DIM>&t_metrics=<M1>&t_metrics=<M2>...&o_column=EXTERNAL_VIEWS&o_direction=ANALYTICS_ORDER_DIRECTION_DESC
```

Per report: navigate → **wait 10 s** → screenshot (table rendered) → download
icon (top right, beside "Show chart") → **"Comma-separated values (.csv)"** (the
SECOND item; the first opens Google Sheets) → wait 3 s. After ALL are down:
`py -3 tools/yt_analytics.py ingest --date <DATE>`.

| kind | `dimension` | `t_metrics` |
|---|---|---|
| content | `VIDEO` | `EXTERNAL_VIEWS ENGAGED_VIEWS EXTERNAL_WATCH_TIME SUBSCRIBERS_NET_CHANGE AVERAGE_WATCH_TIME AVERAGE_WATCH_PERCENTAGE VIDEO_THUMBNAIL_IMPRESSIONS VIDEO_THUMBNAIL_IMPRESSIONS_VTR SHORTS_FEED_IMPRESSIONS_VTR ESTIMATED_UNIQUE_VIEWERS UNIQUE_REACH AVERAGE_VIEWS_PER_VIEWER RECENT_VIEWERS RETURNING_VIEWERS OCCASIONAL_VIEWERS FREQUENT_VIEWERS SUBSCRIBERS_GAINED SUBSCRIBERS_LOST RATINGS_LIKES RATINGS_DISLIKES LIKES_PER_LIKES_PLUS_DISLIKES_PERCENT SHARINGS COMMENTS TOTAL_ESTIMATED_EARNINGS AD_EARNINGS YOUTUBE_EARNINGS IMPRESSIONS CPM IMPRESSIONS_CPM PLAYBACKS EPM EXTERNAL_YOUTUBE_RED_VIEWS EXTERNAL_YOUTUBE_RED_WATCH_TIME` |
| traffic_source | `TRAFFIC_SOURCE_TYPE` | `EXTERNAL_VIEWS ENGAGED_VIEWS EXTERNAL_WATCH_TIME AVERAGE_WATCH_TIME AVERAGE_WATCH_PERCENTAGE VIDEO_THUMBNAIL_IMPRESSIONS VIDEO_THUMBNAIL_IMPRESSIONS_VTR` |
| content_type | `CREATOR_CONTENT_TYPE` | `EXTERNAL_VIEWS EXTERNAL_WATCH_TIME AVERAGE_WATCH_TIME SUBSCRIBERS_NET_CHANGE` |
| device_type | `DEVICE_PLATFORM_TYPE` | `EXTERNAL_VIEWS EXTERNAL_WATCH_TIME AVERAGE_WATCH_TIME UNIQUE_REACH` |
| geography | `COUNTRY` | `EXTERNAL_VIEWS ENGAGED_VIEWS EXTERNAL_WATCH_TIME AVERAGE_WATCH_TIME AVERAGE_WATCH_PERCENTAGE SUBSCRIBERS_NET_CHANGE EPM` |
| sharing_service | `SHARING_SERVICE` | `EXTERNAL_VIEWS EXTERNAL_WATCH_TIME AVERAGE_WATCH_TIME` |
| viewer_age | `VIEWER_AGE` | `EXTERNAL_VIEWS ENGAGED_VIEWS EXTERNAL_WATCH_TIME AVERAGE_WATCH_TIME AVERAGE_WATCH_PERCENTAGE` |
| viewer_gender | `VIEWER_GENDER` | same as age |

`SHORTS_FEED_IMPRESSIONS_VTR` = "Stayed to watch", `EPM` = RPM,
`YOUTUBE_EARNINGS` = Premium. `SUBSCRIPTION_SOURCE` is NOT valid (blanks the
page). Custom window: `time_period=<startMs>%2C<endMs>` (epoch ms of Pacific
midnight, 1 day = 86400000); newest first: `o_column=VIDEO_PUBLISH_DATE`.

**Per-video retention** (every long-form + top 5 Shorts + every Short of the
latest batch):
```
https://studio.youtube.com/video/<VIDEO_ID>/analytics/tab-overview/period-default/explore?entity_type=VIDEO&entity_id=<VIDEO_ID>&time_period=lifetime&explore_type=AUDIENCE_RETENTION
```
navigate → wait until the curve is painted (20-40 s) → screenshot → download →
CSV → `py -3 tools/yt_analytics.py ingest-ret --date <DATE> --id <VIDEO_ID>`
**immediately** (the zip is named by TITLE; the tool takes the newest unless
`--zip <path>`). Also screenshot the Overview of the top 1-2 videos ("Key
moments for audience retention" carries the typical-retention comparison the
export lacks).

## 2. Studio traps (keep adding from real runs)

- **Selecting all metrics breaks the query** ("Oops, something went wrong").
  Use the lists above.
- **`DEVICE_TYPE` and `SUBSCRIBED_STATUS` hang the page** — use
  `DEVICE_PLATFORM_TYPE`; the subscriber split comes from the retention
  export's `Subscribers and non-subscribers.csv`.
- **A hung explore page poisons the tab** (every later URL hangs; also after
  ~4-6 retention loads). Open a fresh tab (`tabs_create_mcp` first), close the
  old one, continue.
- **Export before the table renders does nothing**, and the menu then shifts
  onto "Google Sheets". Wait, screenshot, click the CSV item.
- **The CSV click often doesn't register 1-3 times**: `find` the menuitem,
  click by ref, retry until the zip lands in Downloads (a tiny screenshot
  between clicks forces a paint). Menu still open = not registered.
- **Any click before the retention dialog paints DISMISSES it.** Never click
  blind.
- **One report per tool call** — batching navigations times out and later
  clicks land on the wrong page.
- **`get_page_text` cannot see Advanced mode** (dialog outside `<main>`); read
  from the CSV or a screenshot.
- **Chart data.csv only has curves for rows selected in the table** (default
  top 5); `Totals.csv` has the channel total regardless. Don't tick many rows
  for per-video daily views (≈13 ticks froze the renderer) — use one
  single-day table per day instead.
- **Per-video unique/returning columns are blank in lifetime exports.** Expected.
- **Export end date = Studio's last full day**; the tool measures ages from it.
- **A re-export lands as "… (1).zip"** — newest wins at ingest, so re-pull
  with the FULL metric list.
- **Downloads can hold other channels' / dates' zips** — `ingest` only takes
  zips carrying `CHANNEL` whose window ends on `--date`.
- **QUARANTINE stale `Audience retention*.zip` before a retention run** (move
  to `Downloads/old-analytics-zips/`); with no fresh download `ingest-ret`
  silently files a stale curve under the wrong id. Gate each ingest on a fresh
  zip existing.
- **Two videos can normalise to the same title** — a retention zip's window
  starts at the publish date; resolve collisions with it.
- **After the first download Edge may block further automatic downloads** from
  studio.youtube.com. Fallback: read the table DOM (row `innerText`), build a
  CSV in page `localStorage` → textarea, copy with a REAL mouse click on an
  injected button calling `navigator.clipboard.writeText` (keyboard copy and
  `execCommand` leave it empty), `Get-Clipboard -Raw`.
- **JS `.click()` doesn't sort columns or open the export menu**; real clicks
  do. Screenshot coords: `x * frameWidth / innerWidth`.
- **Table publish-date labels run ahead of the Pacific day buckets** (±1 day).
- **"We updated how views are counted"** can shift old totals a few %; check
  engaged/views is flat across a window before comparing dates.
- **The automation Edge may be signed into another of the owner's channels** —
  ask before switching (it may break another session).

## 3. Run the numbers

```
py -3 tools/yt_analytics.py analyze --date <DATE> --prev <PREV_DATE> --since <BATCH_START> --mature 7
```
Writes `reports/exports/<DATE>/summary.md` + `summary.json`: totals + delta;
**breakouts** (> 15% of Shorts views, excluded from every median); cohort
family table vs before; weekly cohorts; Spearman correlations and length bands;
top 15 / bottom 10; too-young; **duplicate titles** (always flag); long-form
table and subs/1k; daily views split breakout/rest; every breakdown; retention
curves in seconds with the 30 s "vs comparable" split.

**Families**: `reports/video_families.csv` (id,family) overrides everything —
write a row when a guess is wrong, never patch a regex for one video; then the
ledger (url → clip stem → `NAME_FAMILY`); then a title match against unuploaded
clip .mds; then `TITLE_FAMILY`. `fam_src = title` on a video uploaded through
the skill means its ledger row is missing. Check top/bottom families by eye.

**Parent-channel evidence — re-validate on this niche** (use as hypotheses the
first reports test, never as conclusions):
- **Stayed-to-watch was the strongest Shorts reach predictor** (r ≈ +0.59 with
  log views, n≈130; a cliff near 65% where every breakout sat).
- **Shares/likes per view did NOT predict reach** — raw counts track views
  because views cause them. Never target a raw count; only rates are evidence.
- **Length was flat 20-60 s** once the channel had an audience; never argue a
  length from one clip's views.
- **Retention shape**: a 0-3 s swipe, a 4-10 s dip that separates winners from
  losers, then a flat plateau; the end cliff is the payoff, not a defect.
- **Long-form**: most of the revenue on a minority of views; ~35% of the
  audience gone by the 10% mark, so slot 1 matters most.

## 4. Write the report — `reports/<DATE>_channel_analysis.md`

Keep the section order so reports diff:
0. **Headline** — "are we on a good path", Overview numbers, delta table.
1. **What changed since last time** — previous conclusions held/overturned,
   with numbers; add a superseded banner to the PREVIOUS report.
2. **The batch under judgement** — each video vs cohort median, grouped by what
   it tested. This decides the next batch.
3. Families, cadence, correlations, length. 4. Long-form. 5. Audience and
   traffic. 6. Monetisation (once earnings are non-zero; RPM is noisy for
   weeks). 7. Risks / hygiene (duplicate titles, repetitive-content risk under
   the inauthentic-content policy). 8. **Recommendations** — numbered, each
   tied to a number. 9. **Not on disk** — exports that failed.

Every claim carries its number and source table; say "n is small" when n < 6;
no correlation without n; a Shorts spike's decay is not a penalty. Where the
audit contradicts a project rule, THE AUDIT WINS and the rule gets rewritten.

## 5. Land it

1. `py -3 tools/yt_analytics.py outcomes --date <DATE> --since <BATCH_START> --write`
   appends a `MEASURED OUTCOME` block to `docs/scenes/<scene>.md` per ledger
   video (the upload .md is deleted at upload). Unmatched videos are listed —
   classify important ones via `reports/video_families.csv`.
2. Docs carrying a number this run changed get the new number + a pointer to
   the report (project CLAUDE.md's channel-direction pointer, previous report's
   banner, affected scene docs/skills).
3. **Shareable page**: publish the report as an Artifact (load
   `artifact-design` first) — headline tiles, daily views, retention in
   seconds, family table, batch scorecard, recommendations. Same title every
   run, date in the description. Hand the owner the link.
4. Terminal: headline, scorecard, recommendations, link, what didn't export.
   Nothing is committed.

## 6. Not this skill

No edits on YouTube of any kind; no revenue decisions from a few days of data;
no memory writes — durable findings go into the report and the repo docs.
