"""Mechanical half of the youtube-upload skill (.claude/skills/youtube-upload/).

The browser work (Studio upload form) is done by hand through the extension; this
tool does everything that must come out IDENTICAL every run, so it never drifts:

  meta    <clip_9x16.mp4 | clip.md> ...   parse each clip's .md -> JSON with the
          title options (" #usa" appended + length-checked), the fixed pinned
          comment, file paths, duration. A Short carries NO description and NO
          tags (both returned empty); #usa in the title is its only hashtag.
  order   <clip> ...                      random upload order that keeps two clips
          of the same family (first stem token: sort_*, double_*) apart.
  slots   --count N [--existing "YYYY-MM-DD HH:MM" ...] [--immediate]
          next free publish times, Tbilisi local (UTC+4, no DST).
  record  --clip <9x16.mp4> --when "YYYY-MM-DD HH:MM" --title .. --url .. --related ..
          appends the ledger row (final/YOUTUBE-UPLOADS.md) and moves the mp4
          pair to final/uploaded/ + deletes the used .md.
  due     ledger rows whose publish time has passed and whose comment is pending.
  pinned  --url <url>                     marks that row's comment as pinned.

SCHEDULE: 3 slots per "day" at 14:00 22:00 06:00 Tbilisi (the day runs 14:00 -> 13:59
next day), max 3 per day (manual uploads count). A slot is a TARGET:
one already served by a Short is skipped; a MISSED one (< now+10 min) is never
skipped but moves to now+10 min on the next 15-minute mark. Any time is then pushed
forward in 15-minute steps until it is >= 45 min from every other Short.
"""
import argparse
import datetime as dt
import json
import math
import random
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "final" / "YOUTUBE-UPLOADS.md"
UPLOADED = ROOT / "final" / "uploaded"
SHORTS_ONLY = UPLOADED / "shorts-only"   # non-PD music: uploaded, never megamix pool


def non_pd_music(stem):
    """Reason string if the clip carries custom-bank (non-PD) music, else None."""
    sys.path.insert(0, str(ROOT / "tools"))
    try:
        import longform_audio_guard as g
    except ImportError:     # not ported yet; the custom music banks start empty
        return None
    return g.reason(g.stem_of(stem), g.bank_keys())

TZ = dt.timezone(dt.timedelta(hours=4), "Tbilisi")

# Luka 2026-09-17 (tested: no tags performs better): a Short's ONLY hashtag is #usa in
# the title; description box EMPTY; tags field EMPTY. Long-form metadata is unaffected.
TITLE_SUFFIX = " #usa"
COMMENT = "Drop a simulated idea 👇\nand it might be the next video 👀"

# 5/day (Luka, 2026-09-25). The 3/day test week LOST: +20% per clip but 30-46% FEWER
# views per upload day (reports/2026-09-25_cadence_recheck.md). Test grid was (14, 22, 6) / 3.
SLOT_HOURS = (14, 18, 22, 2, 6)     # 2 and 6 fall on the next calendar day
PER_DAY = 5
# Luka 2026-09-15: a slot is a TARGET ("18:00 means around 18:00"). A missed slot is never
# skipped -- it is published as soon as possible, because every slot of the day is meant to go out. The only
# strict constraint is MIN_GAP between any two Shorts.
MIN_GAP = dt.timedelta(minutes=45)
STEP = dt.timedelta(minutes=15)     # Studio's time dropdown grid
LEAD = dt.timedelta(minutes=10)

LEDGER_HEAD = """# YouTube upload ledger (Shorts)

One row per upload, written by `tools/yt_upload_prep.py record`. Times are Tbilisi
(UTC+4). `comment` = pending until the fixed pinned comment is posted + pinned
after the video goes live (`yt_upload_prep.py due` lists them).

| # | publish (Tbilisi) | clip | title | url | related video | comment |
|---|-------------------|------|-------|-----|---------------|---------|
"""


def out(obj):
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(obj, ensure_ascii=False, indent=2))


def now_tbilisi():
    return dt.datetime.now(TZ).replace(second=0, microsecond=0)


def parse_time(s):
    return dt.datetime.strptime(s.strip(), "%Y-%m-%d %H:%M").replace(tzinfo=TZ)


def fmt(t):
    return t.strftime("%Y-%m-%d %H:%M")


# ---------------------------------------------------------------- meta
def clip_paths(arg):
    p = Path(arg)
    if not p.is_absolute():
        p = (Path.cwd() / p).resolve()
    stem = re.sub(r"_(9x16|16x9)$", "", p.stem)
    d = p.parent
    return stem, d / f"{stem}_9x16.mp4", d / f"{stem}_16x9.mp4", d / f"{stem}.md"


def sections(md_text):
    secs, cur = {}, None
    for line in md_text.splitlines():
        m = re.match(r"^##\s+(.*)", line)
        if m:
            cur = m.group(1).strip().lower()
            secs[cur] = []
        elif cur is not None:
            secs[cur].append(line)
    return secs


def find_sec(secs, prefix):
    for k, v in secs.items():
        if k.startswith(prefix):
            return v
    return None


def title_options(lines):
    opts = []
    stripped = [l.strip() for l in lines or [] if l.strip()]
    listed = [s for s in stripped if re.match(r"^(?:\d+[.)]|[-*])\s+", s)]
    for s in listed or stripped:            # a list present -> ignore its intro line
        m = re.match(r"^(?:\d+[.)]|[-*])\s+(.*)", s)
        body = m.group(1) if m else s
        tick = re.findall(r"`([^`]+)`", body)
        if tick:
            t = tick[0]
        else:
            t = re.sub(r"\s*\((?:[^()]*)\)\s*$", "", body)       # "(rule restated)"
            t = re.sub(r"^\*\*[^*]+\*\*\s*[—-]\s*", "", t)       # "**Question** — "
            t = t.strip("*\"“” ")
        t = re.sub(r"\s#\w+", "", t).strip()                    # no stray hashtags
        if t:
            opts.append(t)
    return opts


def duration(path):
    try:
        r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                            "-of", "csv=p=0", str(path)], capture_output=True, text=True)
        return round(float(r.stdout.strip()), 2)
    except (ValueError, OSError):
        return None


def cmd_meta(a):
    res = []
    for arg in a.clips:
        stem, v916, v169, md = clip_paths(arg)
        item = {"stem": stem, "short": str(v916), "long_16x9": str(v169), "md": str(md),
                "short_exists": v916.exists(), "duration_s": duration(v916) if v916.exists() else None,
                "problems": []}
        if not v916.exists():
            item["problems"].append("9:16 file missing")
        if not md.exists():
            item["problems"].append(".md missing — write title/description by hand")
            secs = {}
        else:
            secs = sections(md.read_text(encoding="utf-8"))
        titles = title_options(find_sec(secs, "title"))
        item["title_options"] = []
        for t in titles:
            full = t + TITLE_SUFFIX
            item["title_options"].append({"title": full, "len": len(full), "ok": len(full) <= 100})
        if not titles:
            item["problems"].append("no title options parsed")
        item["description"] = ""    # Shorts: description box stays EMPTY
        item["tags"] = ""           # Shorts: tags field stays EMPTY
        item["comment"] = COMMENT
        res.append(item)
    out(res)


# ---------------------------------------------------------------- order
def cmd_order(a):
    stems = [clip_paths(c)[0] for c in a.clips]
    fam = lambda s: s.split("_")[0]
    best = None
    for _ in range(400):
        random.shuffle(stems)
        clashes = sum(fam(x) == fam(y) for x, y in zip(stems, stems[1:]))
        if best is None or clashes < best[0]:
            best = (clashes, list(stems))
        if clashes == 0:
            break
    out({"order": best[1], "adjacent_same_family": best[0]})


# ---------------------------------------------------------------- slots
def day_key(t):
    return (t - dt.timedelta(hours=14)).date()     # the day runs 14:00 -> 13:59


def day_slots(d):
    base = dt.datetime.combine(d, dt.time(), TZ)
    return [base + dt.timedelta(days=1 if h < 14 else 0, hours=h) for h in SLOT_HOURS]


def cmd_slots(a):
    now = parse_time(a.now) if a.now else now_tbilisi()
    taken = sorted(parse_time(s) for s in (a.existing or []))
    got = []
    if a.immediate:
        t = now + LEAD
        t += dt.timedelta(minutes=(-t.minute) % 5)
        got.append(t)
        taken.append(t)
    d = day_key(now)
    while len(got) < a.count:
        slots = day_slots(d)
        ends = slots[1:] + [slots[0] + dt.timedelta(days=1)]
        for i, (s, end) in enumerate(zip(slots, ends)):
            if len(got) >= a.count:
                break
            in_day = [x for x in taken if day_key(x) == d]
            if len(in_day) >= PER_DAY:
                break
            # slot i is already served when the day holds i+1 Shorts before the next slot
            # (a Short that went out at 14:00 covers the 14:00 slot; it is not "missed")
            if sum(x < end for x in in_day) >= i + 1:
                continue
            t = s
            if t < now + LEAD:                          # missed: catch up, don't skip
                t = now + LEAD
                t += dt.timedelta(minutes=(-t.minute) % 15, seconds=-t.second,
                                  microseconds=-t.microsecond)
            while any(abs(t - x) < MIN_GAP for x in taken):
                t += STEP
            if day_key(t) != d:
                break
            got.append(t)
            taken.append(t)
        d += dt.timedelta(days=1)
    out({"now": fmt(now), "timezone": "Asia/Tbilisi (UTC+4)",
         "slots": [{"when": fmt(t), "studio_date": t.strftime("%b %d, %Y").replace(" 0", " "),
                    "studio_time": t.strftime("%I:%M %p").lstrip("0")} for t in got]})


# ---------------------------------------------------------------- ledger
def ledger_rows():
    if not LEDGER.exists():
        return []
    rows = []
    for line in LEDGER.read_text(encoding="utf-8").splitlines():
        if re.match(r"^\|\s*\d+\s*\|", line):
            rows.append([c.strip() for c in line.strip().strip("|").split("|")])
    return rows


def cmd_record(a):
    stem, v916, v169, md = clip_paths(a.clip)
    if not LEDGER.exists():
        LEDGER.write_text(LEDGER_HEAD, encoding="utf-8")
    n = len(ledger_rows()) + 1
    safe = lambda s: s.replace("|", "/").replace("\n", " ")
    non_pd = non_pd_music(stem)
    dest_dir = SHORTS_ONLY if non_pd else UPLOADED               # non-PD never joins the pool
    dest = v916 if a.no_move else dest_dir / v916.name        # where the clip will live
    rel = dest.relative_to(ROOT).as_posix() if dest.is_relative_to(ROOT) else str(dest)
    row = (f"| {n} | {a.when} | `{rel}` | {safe(a.title)} | {a.url} | "
           f"{safe(a.related or '-')} | pending |\n")
    with LEDGER.open("a", encoding="utf-8") as f:
        f.write(row)
    moved = []
    if not a.no_move:
        dest_dir.mkdir(parents=True, exist_ok=True)
        for p in (v916, v169):
            if p.exists() and p.parent.resolve() != dest_dir.resolve():
                shutil.move(str(p), str(dest_dir / p.name))
                moved.append(p.name)
        if md.exists() and md.parent.resolve() != dest_dir.resolve():
            md.unlink()
            moved.append(f"deleted {md.name}")
        try:                                   # drop an emptied family subfolder
            if v916.parent != ROOT / "final" / "ready-to-upload" and not any(v916.parent.iterdir()):
                v916.parent.rmdir()
        except OSError:
            pass
    out({"ledger_row": n, "moved": moved, "shorts_only": non_pd})


def cmd_due(a):
    now = parse_time(a.now) if a.now else now_tbilisi()
    due = [{"row": r[0], "when": r[1], "clip": r[2], "title": r[3], "url": r[4]}
           for r in ledger_rows() if len(r) >= 7 and r[6] == "pending" and parse_time(r[1]) <= now]
    out({"now": fmt(now), "comment": COMMENT, "due": due})


def cmd_pinned(a):
    lines = LEDGER.read_text(encoding="utf-8").splitlines(keepends=True)
    hit = 0
    for i, line in enumerate(lines):
        if a.url in line and line.rstrip().endswith("| pending |"):
            lines[i] = line.rstrip()[: -len("pending |")] + "pinned |\n"
            hit += 1
    LEDGER.write_text("".join(lines), encoding="utf-8")
    out({"marked": hit})


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("meta"); m.add_argument("clips", nargs="+")
    o = sub.add_parser("order"); o.add_argument("clips", nargs="+")
    s = sub.add_parser("slots"); s.add_argument("--count", type=int, required=True)
    s.add_argument("--existing", action="append"); s.add_argument("--immediate", action="store_true")
    s.add_argument("--now")
    r = sub.add_parser("record"); r.add_argument("--clip", required=True); r.add_argument("--when", required=True)
    r.add_argument("--title", required=True); r.add_argument("--url", required=True)
    r.add_argument("--related"); r.add_argument("--no-move", action="store_true")
    d = sub.add_parser("due"); d.add_argument("--now")
    p = sub.add_parser("pinned"); p.add_argument("--url", required=True)
    a = ap.parse_args()
    {"meta": cmd_meta, "order": cmd_order, "slots": cmd_slots, "record": cmd_record,
     "due": cmd_due, "pinned": cmd_pinned}[a.cmd](a)


if __name__ == "__main__":
    main()
