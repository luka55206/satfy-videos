"""Numeric half of the youtube-analytics skill (.claude/skills/youtube-analytics/).

Ported from blender-physics (Satisfying 3D Sims) 2026-09-15; the ANALYSIS functions are
identical so the two channels' reports compare like for like. The browser half (Studio
exports) is the SKILL.md; this tool does everything that must come out IDENTICAL every
run: the export layout, the family of every video, the cohort tables, the correlations,
the breakout split, the retention curves in seconds, and the per-video outcome blocks.

  ingest      --date D                    unzip every Studio export zip for that date from
                                          ~/Downloads into reports/exports/<D>/<kind>/
                                          (several zips of one kind: newest wins)
  ingest-ret  --date D --id VIDEO_ID [--zip PATH]
                                          move an "Audience retention*.zip" from ~/Downloads
                                          to reports/exports/<D>/retention_<id>/ (default:
                                          the newest one; --zip when several are queued)
  analyze     --date D [--prev P] [--since YYYY-MM-DD] [--mature 7]
                                          print every table; write summary.md + summary.json
                                          beside the exports
  outcomes    --date D [--since YYYY-MM-DD] [--write]
                                          one MEASURED OUTCOME block per video with a ledger
                                          row; --write appends it to the scene's
                                          docs/scenes/<scene>.md (once per date)

FAMILY: the upload ledger (final/YOUTUBE-UPLOADS.md) maps a YouTube id to its clip stem;
the stem's tokens give the family (NAME_FAMILY below). The ledger only starts 2026-09-15 —
every earlier upload was manual, so those classify by title (TITLE_FAMILY) or by a row in
reports/video_families.csv (id,family), which overrides everything: write a row when a
guess is wrong, never patch the regex for one video.

Dates in the export are the export's own last day (Studio's "Sep 8" on a Sep 9 pull);
ages are measured against that, never against today.

Portable: everything channel-specific is in the CONFIG block + the three mapping
functions under it (ledger_map / docs_title_map / scene_of).
"""
import argparse
import json
import re
import shutil
import sys
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

# ---------------------------------------------------------------- CONFIG (per channel)
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib.channel import CHANNEL, CHANNEL_ID  # noqa: E402
EXPORTS = ROOT / "reports" / "exports"
LEDGER = ROOT / "final" / "YOUTUBE-UPLOADS.md"
# Per-video metadata home: the upload .md is DELETED at upload (yt_upload_prep record),
# so outcomes land in the scene's docs/scenes/<scene>.md instead (see scene_of()).
UPLOAD_DOCS = ROOT / "docs" / "scenes"
TITLE_DOC_DIRS = [ROOT / "final" / "ready-to-upload", ROOT / "final" / "needs-review"]
OVERRIDES = ROOT / "reports" / "video_families.csv"
DOWNLOADS = Path.home() / "Downloads"
LONGFORM_SEC = 180
# Studio zip name prefix -> folder name under reports/exports/<date>/
KINDS = {
    "Content": "content",
    "Traffic source": "traffic_source",
    "Content type": "content_type",
    "Device type": "device_type",
    "Geography": "geography",
    "Sharing service": "sharing_service",
    "Viewer age": "viewer_age",
    "Viewer gender": "viewer_gender",
}
# clip-stem token -> family (first match wins, checked in this order). Families follow
# research/channel-performance-2026-09-09.md §6 so reports and audits share vocabulary.
# Tokens are drawn from scenes/*.py names and ledger stems.
NAME_FAMILY = [
    ("pacman", ["pac"]),
    ("press_crush", ["press", "crush", "jaw", "baler", "millstone", "cinch", "choke",
                     "squish", "smash", "pushback", "shrink", "hydro", "tower", "quake",
                     "swing_cage", "v_arms", "crumple", "grind", "anvil", "piston"]),
    ("recursion", ["nest", "droste", "fractal", "tree_ring", "recursion"]),
    ("merge_sink", ["merge", "buoy", "sink"]),
    ("eat_hunter", ["devour", "gorge", "snake", "hunt", "eat"]),
    ("fire_water", ["steam", "fire", "water"]),
    ("melody", ["song", "melody", "note_rain", "carillon", "harp", "chord", "tune"]),
    ("big_number", ["double", "doubling", "multiply", "billion", "trillion", "million",
                    "power", "digit", "counter"]),
    ("overflow_hold", ["spawn_crash", "pop_bowl", "glass_float", "glass_swell",
                       "balloon", "overflow", "boing"]),
    ("beat_rhythm", ["beat_", "neon_tunnel", "solved_bounce", "runner"]),
    ("mitosis_cell", ["mitosis", "cell"]),
    ("escape_door", ["escape", "hatch", "trapdoor", "door", "gate"]),
    ("sort", ["sort", "sift"]),
    ("turf", ["turf", "rps", "paint_giant", "wet_paint"]),
    ("shatter_explode", ["shatter", "spiral", "break_", "cannon", "laser", "blast",
                         "red_zone", "spike"]),
    ("fill_grow", ["grow_", "fill_", "morph", "grid_grow", "packing", "wash", "paint"]),
    ("static_pattern", ["mandala", "harmonograph", "one_line", "chladni", "kaleido",
                        "snowflake", "illusion"]),
    ("prediction", ["plinko", "roll_race", "predict", "compare"]),
]
# title regex fallback for the ~140 manual uploads that predate the ledger (order matters;
# built from the actual uploaded titles in the 2026-09-09 Content export)
TITLE_FAMILY = [
    ("pacman", r"pac[- ]?man|ghost"),
    ("press_crush", r"\bpress\b|crush|jaw\b|grind|millstone|squeez|piston|hydraulic|"
                    r"baler|ram slams|walls? clos|closing walls|shrink|tighter|bale\b|"
                    r"every block"),
    ("recursion", r"how deep|inside a|rings? in(side)? (a|the) ring|nested|deeper|"
                  r"ring inside|another one inside|all the way down"),
    ("merge_sink", r"merge|absorb|swallow|sink|combine"),
    ("eat_hunter", r"\beat|\bate\b|hunter|hunts?\b|devour|feeds? on|it got a taste"),
    ("fire_water", r"fire (vs|and|v)? ?water|water vs|lava|steam"),
    ("melody", r"plays? (what|a |the )|name th(e|is) song|guess the song|song\b|"
               r"melody|sound on|sand understand music"),
    ("big_number", r"doubl(es?|ing)|x ?\d|billion|trillion|million|quintillion|"
                   r"quadrillion|1,000,000|reach(es)? \d|count(er)? (hit|to)|10,?000|"
                   r"\dx past|past the goal"),
    ("overflow_hold", r"overflow|spawns? \d|too many|hold\b|blender|"
                      r"multiply|panicked|handle\b|chance to split|balloon"),
    ("beat_rhythm", r"\bbeat\b|rhythm|tempo|to the music"),
    ("mitosis_cell", r"mitosis|cell|divid(es|ing)|splits? in(to)? (two|2)"),
    ("escape_door", r"escap|way out|door|trapdoor|the gap|get out|let it out|freed?\b|"
                    r"fall(s|ing)? through"),
    ("sort", r"sort"),
    ("turf", r"takes over|turf|colou?r war|territory|team|last colou?r|"
             r"colou?rs? fight|paint(s|ed)? the (board|arena)|which colou?r|"
             r"erased|two colou?rs|colou?r fills|fills? the \w+ last"),
    ("shatter_explode", r"shatter|glass|explo(d|si)|blast|pieces|blade|slice|laser|"
                        r"spike|acid|melt|reach(es)? the cent|hits? the cent|"
                        r"rings? breaks?|breaks? exactly"),
    ("fill_grow", r"fill(s|ed)?( the| it)?\b|gets bigger|arena (grows|gets)|grows? the|"
                  r"every bounce grows|grows? (with )?every|keeps? growing|"
                  r"grows? until|circle turns|becom|morph|paints? the|unpaints?|"
                  r"gains? a (side|mirror)|bigger every|spinning \w+agon"),
    ("static_pattern", r"mandala|kaleidoscope|illusion|one line|snowflake|pattern"),
    ("prediction", r"predict|which (column|moose)|who wins|plinko|pick your"),
]
# ---------------------------------------------------------------------------------------


def log(*a):
    print(*a, flush=True)


def ascii_(s):
    return str(s).encode("ascii", "ignore").decode("ascii").strip()


def export_dir(date):
    return EXPORTS / date


# ---------------------------------------------------------------- ingest
def cmd_ingest(a):
    out = export_dir(a.date)
    out.mkdir(parents=True, exist_ok=True)
    found = 0
    # longest prefix first ("Content type" must not be swallowed by "Content");
    # several zips of one kind extract oldest -> newest so the NEWEST export wins
    prefixes = sorted(KINDS.items(), key=lambda kv: -len(kv[0]))
    zs = sorted(DOWNLOADS.glob("*.zip"), key=lambda p: p.stat().st_mtime)
    for z in zs:
        # Downloads can hold several generations of exports — only ingest zips
        # whose own window ENDS on this run's date
        rng = re.search(r"\d{4}-\d{2}-\d{2}_(\d{4}-\d{2}-\d{2})", z.name)
        if not rng or rng.group(1) != a.date:
            continue
        for prefix, kind in prefixes:
            if z.name.startswith(prefix + " ") and CHANNEL in z.name:
                dest = out / kind
                dest.mkdir(exist_ok=True)
                with zipfile.ZipFile(z) as zf:
                    zf.extractall(dest)
                shutil.move(str(z), str(dest / z.name))   # keep the zip beside its CSVs
                log(f"ingested {kind:15s} <- {z.name}")
                found += 1
                break
    if not found:
        log("nothing to ingest: no '<Kind> ... " + CHANNEL + ".zip' in Downloads")
    log(f"exports in {out}")


def cmd_ingest_ret(a):
    if a.zip:
        z = Path(a.zip)
        if not z.exists():
            sys.exit(f"no such zip: {z}")
    else:
        zs = sorted(DOWNLOADS.glob("Audience retention *.zip"),
                    key=lambda p: p.stat().st_mtime)
        if not zs:
            sys.exit("no 'Audience retention*.zip' in Downloads")
        z = zs[-1]
    dest = export_dir(a.date) / f"retention_{a.id}"
    dest.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(z) as zf:
        zf.extractall(dest)
    shutil.move(str(z), str(dest / z.name))
    log(f"ingested retention_{a.id} <- {z.name}")


# ---------------------------------------------------------------- families
def stem_of(clip):
    """`final/uploaded/throne_9x16.mp4` -> `throne`."""
    m = re.search(r"([\w][\w.-]*?)_(?:9x16|16x9)\.mp4", clip)
    return m.group(1) if m else ""


def ledger_map():
    """YouTube id -> clip stem, from the upload ledger (final/YOUTUBE-UPLOADS.md)."""
    m = {}
    if not LEDGER.exists():
        return m
    for line in LEDGER.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|") or "youtube.com" not in line:
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        url = next((c for c in cells if "youtube.com" in c), "")
        clip = next((c for c in cells if ".mp4" in c), "")
        vid = re.search(r"(?:shorts/|v=|youtu\.be/)([\w-]{11})", url)
        name = stem_of(clip)
        if vid and name:
            m[vid.group(1)] = name
    return m


def scene_of(stem):
    """Clip stem -> scene name (docs/scenes/<scene>.md): the longest leading token
    run that names a scenes/<name>.py (`double_up_pentagon` -> `double_up`)."""
    toks = stem.split("_")
    for n in range(len(toks), 0, -1):
        cand = "_".join(toks[:n])
        if (ROOT / "scenes" / f"{cand}.py").exists():
            return cand
    return stem


def _norm_title(t):
    """Compare titles without emoji, hashtags, punctuation or case."""
    t = re.sub(r"#\w+", "", str(t)).lower()
    t = re.sub(r"[^a-z0-9 ]", "", t)
    return re.sub(r"\s+", " ", t).strip()


def docs_title_map():
    """normalised title option -> clip stem, from every not-yet-uploaded clip .md's
    '## Title' section (final/ready-to-upload + needs-review; the .md is deleted at
    upload, so this only catches clips uploaded OUTSIDE yt_upload_prep record)."""
    m = {}
    for d in TITLE_DOC_DIRS:
        for doc in d.rglob("*.md"):
            txt = doc.read_text(encoding="utf-8", errors="ignore")
            sec = re.search(r"## Title[^\n]*\n(.*?)(?:\n## |\Z)", txt, re.S)
            if not sec:
                continue
            for line in sec.group(1).splitlines():
                mo = re.match(r"\s*(?:\d+[.)]|[-*])\s+(.+)", line)
                if not mo:
                    continue
                body = mo.group(1)
                tick = re.findall(r"`([^`]+)`", body)
                if tick:
                    t = tick[0]
                else:
                    t = re.split(r"\s+(?:--|—)\s+", body)[0]
                    t = re.sub(r"\s*\((?:[^()]*)\)\s*$", "", t)
                    t = re.sub(r"^\*\*[^*]+\*\*\s*[—-]\s*", "", t)
                    t = t.strip("*\"“” ")
                t = re.sub(r"\s#\w+", "", t).strip()
                if t:
                    m[_norm_title(t)] = doc.stem
    return m


def family_from_name(name):
    n = name.lower()
    for fam, toks in NAME_FAMILY:
        if any(t in n for t in toks):
            return fam
    return "other"


def family_from_title(title, duration):
    t = title.lower()
    if duration >= LONGFORM_SEC:
        return "megamix"
    for fam, pat in TITLE_FAMILY:
        if re.search(pat, t):
            return fam
    return "other"


def overrides():
    if not OVERRIDES.exists():
        return {}
    o = pd.read_csv(OVERRIDES)
    return dict(zip(o["id"], o["family"]))


def assign_families(d):
    lm, ov, tm = ledger_map(), overrides(), docs_title_map()
    fams, names, src = [], [], []
    for vid, title, dur in zip(d.Content, d["Video title"], d.dur):
        name = lm.get(vid.strip(), "")
        by = "ledger"
        if not name:   # manual uploads before the ledger: match the title to a doc's options
            name = tm.get(_norm_title(title), "")
            by = "doc-title"
        if not name and dur < LONGFORM_SEC:   # retitled at upload: best word overlap >= 0.6
            words = set(_norm_title(title).split())
            best, score = "", 0.0
            for opt, nm in tm.items():
                ow = set(opt.split())
                j = len(words & ow) / max(1, len(words | ow))
                if j > score:
                    best, score = nm, j
            if score >= 0.6:
                name, by = best, "doc-fuzzy"
        if vid.strip() in ov:
            fams.append(ov[vid.strip()]); src.append("override")
        elif dur >= LONGFORM_SEC:
            fams.append("megamix"); src.append("length")
        elif name:
            fams.append(family_from_name(name)); src.append(by)
        else:
            fams.append(family_from_title(title, dur)); src.append("title")
        names.append(name)
    d["fam"], d["name"], d["fam_src"] = fams, names, src
    return d


# ---------------------------------------------------------------- load
def load_content(date):
    p = export_dir(date) / "content" / "Table data.csv"
    d = pd.read_csv(p)
    end = pd.Timestamp(re.search(r"\d{4}-\d{2}-\d{2}_(\d{4}-\d{2}-\d{2})",
                                 next((export_dir(date) / "content").glob("Content *.zip")).name).group(1)) \
        if list((export_dir(date) / "content").glob("Content *.zip")) else pd.Timestamp(date)
    end = end - pd.Timedelta(days=1)   # Studio's last full day is the day before the pull
    total = d[d.Content == "Total"].iloc[0] if (d.Content == "Total").any() else None
    d = d[d.Content != "Total"].copy()
    d["pub"] = pd.to_datetime(d["Video publish time"], format="%b %d, %Y", errors="coerce")
    d["dur"] = pd.to_numeric(d.Duration, errors="coerce").fillna(0).astype(int)
    d["age"] = (end - d.pub).dt.days
    d["title"] = d["Video title"].map(ascii_).str.slice(0, 60)
    d = assign_families(d)
    for col in ("Shares", "Likes", "Subscribers", "Engaged views", "Comments added"):
        if col not in d:            # older exports were pulled with fewer metrics
            d[col] = np.nan
    v = d.Views.replace(0, np.nan)
    d["subs1k"] = d.Subscribers / v * 1000
    d["share1k"] = d.Shares / v * 1000
    d["like1k"] = d.Likes / v * 1000
    d["stayed"] = d.get("Stayed to watch (%)")
    d["apv"] = d.get("Average percentage viewed (%)")
    d["ctr"] = d.get("Thumbnail click-through rate (%)")
    return d, total, end


def load_daily(date):
    p = export_dir(date) / "content" / "Totals.csv"
    if not p.exists():
        return None
    t = pd.read_csv(p); t["Date"] = pd.to_datetime(t.Date)
    return t


def load_chart(date):
    p = export_dir(date) / "content" / "Chart data.csv"
    if not p.exists():
        return None
    c = pd.read_csv(p); c["Date"] = pd.to_datetime(c.Date)
    return c


def load_table(date, kind):
    p = export_dir(date) / kind / "Table data.csv"
    return pd.read_csv(p) if p.exists() else None


# ---------------------------------------------------------------- analysis pieces
def sp(x, y):
    from scipy.stats import spearmanr
    x, y = pd.to_numeric(x, errors="coerce"), pd.to_numeric(y, errors="coerce")
    ok = x.notna() & y.notna()
    return float(spearmanr(x[ok], y[ok]).correlation) if ok.sum() >= 5 else float("nan")


def table(df, cols=None):
    return (df if cols is None else df[cols]).to_string(index=False)


def analyze(a):
    d, total, end = load_content(a.date)
    md, js = [], {"date": a.date, "export_end": str(end.date()), "channel": CHANNEL}
    say = lambda s="": md.append(s)

    phys = d[d.fam != "pre_pivot"]
    shorts = phys[phys.dur < LONGFORM_SEC]
    long = phys[phys.dur >= LONGFORM_SEC]
    say(f"# yt_analytics summary — {CHANNEL}, export to {end.date()}\n")
    say(f"{len(d)} rows | {len(phys)} physics | {len(shorts)} shorts | {len(long)} long-form | "
        f"families from: {d.fam_src.value_counts().to_dict()}\n")

    # totals + delta vs previous export
    tot = {k: float(phys[k].sum()) for k in ("Views", "Engaged views", "Watch time (hours)",
                                             "Subscribers", "Shares", "Likes") if k in phys}
    js["totals"] = tot
    say("## Totals (physics videos)\n")
    say(table(pd.DataFrame([tot]).round(0)))
    if a.prev:
        dp, _, endp = load_content(a.prev)
        pp = dp[dp.fam != "pre_pivot"]
        say(f"\nvs previous export ({endp.date()}): views {pp.Views.sum():,.0f} -> {tot['Views']:,.0f} "
            f"(+{tot['Views']-pp.Views.sum():,.0f}), subs {pp.Subscribers.sum():,.0f} -> "
            f"{tot['Subscribers']:,.0f}")
        js["prev"] = {"date": a.prev, "views": float(pp.Views.sum()), "subs": float(pp.Subscribers.sum())}

    # breakout detection: any short with > 15% of all short views
    share = shorts.Views / shorts.Views.sum()
    brk = shorts[share > 0.15]
    js["breakouts"] = brk.Content.tolist()
    if len(brk):
        say("\n## Breakout(s): > 15% of all Shorts views\n")
        say(table(brk[["Content", "title", "pub", "dur", "Views", "Subscribers", "stayed", "apv", "fam"]]))

    # cohort: mature shorts since --since, breakouts excluded
    since = pd.Timestamp(a.since) if a.since else end - pd.Timedelta(days=42)
    k = shorts[(shorts.age >= a.mature) & (shorts.pub >= since) & ~shorts.Content.isin(brk.Content)].copy()
    say(f"\n## Cohort: Shorts published since {since.date()}, age >= {a.mature} d, breakouts excluded (n={len(k)})\n")
    fam = (k.groupby("fam").agg(n=("Views", "size"), median=("Views", "median"), mean=("Views", "mean"),
                                stayed=("stayed", "median"), apv=("apv", "median"), subs1k=("subs1k", "median"),
                                dur=("dur", "median")).sort_values("median", ascending=False).round(1))
    say("### Family\n"); say(fam.to_string())
    js["family"] = fam.reset_index().to_dict(orient="records")
    # previous window for the same families
    prev_k = shorts[(shorts.age >= a.mature) & (shorts.pub < since) & ~shorts.Content.isin(brk.Content)]
    if len(prev_k):
        pf = prev_k.groupby("fam").Views.agg(["size", "median"]).round(0)
        say(f"\n### Same families, before {since.date()} (n={len(prev_k)})\n"); say(pf.to_string())

    k["week"] = k.pub.dt.to_period("W").astype(str)
    wk = k.groupby("week").agg(n=("Views", "size"), median=("Views", "median"), stayed=("stayed", "median"),
                               dur=("dur", "median"), subs=("Subscribers", "sum")).round(0)
    say("\n### By publish week\n"); say(wk.to_string())

    say("\n### Spearman rho vs views (cohort)\n")
    corr = {}
    for col, lab in (("dur", "duration"), ("stayed", "stayed to watch"), ("apv", "avg % viewed"),
                     ("ctr", "thumbnail CTR"), ("share1k", "shares/1k"), ("like1k", "likes/1k")):
        if col in k:
            corr[lab] = round(sp(k[col], k.Views), 3)
            say(f"- {lab}: {corr[lab]:+.3f}")
    js["corr"] = corr
    k["band"] = pd.cut(k.dur, [0, 25, 35, 45, 70, 999], labels=["<=25", "26-35", "36-45", "46-70", "70+"])
    say("\n### Length bands (cohort)\n")
    say(k.groupby("band", observed=True).agg(n=("Views", "size"), median=("Views", "median"),
                                             stayed=("stayed", "median")).round(0).to_string())

    cols = ["title", "pub", "dur", "Views", "stayed", "apv", "Subscribers", "Shares", "fam", "fam_src"]
    cols = [c for c in cols if c in k]
    say("\n### Top 15 (cohort)\n"); say(table(k.sort_values("Views", ascending=False).head(15)[cols]))
    say("\n### Bottom 10 (cohort)\n"); say(table(k.sort_values("Views").head(10)[cols]))
    say("\n### Too young to score (age < mature)\n")
    say(table(shorts[shorts.age < a.mature].sort_values("pub")[["title", "pub", "age", "Views", "stayed", "fam"]]))

    # duplicates
    stem = shorts["Video title"].str.lower().str.replace(r"[^a-z0-9 ]", "", regex=True) \
        .str.replace(r"\s+", " ", regex=True).str.replace("simulation satisfying shorts", "").str.strip()
    dup = shorts[stem.duplicated(keep=False)]
    if len(dup):
        say("\n## DUPLICATE TITLES (title-gap rule)\n"); say(table(dup[["Content", "title", "pub", "Views"]]))

    # long-form
    if len(long):
        say("\n## Long-form\n")
        lc = [c for c in ["title", "pub", "dur", "Views", "Thumbnail impressions", "ctr", "Average view duration",
                          "apv", "Subscribers", "Watch time (hours)"] if c in long]
        say(table(long.sort_values("pub")[lc]))
        say(f"\nsubs/1k: shorts {shorts.Subscribers.sum()/shorts.Views.sum()*1000:.2f}, "
            f"long-form {long.Subscribers.sum()/long.Views.sum()*1000:.2f}")

    # daily split
    t, c = load_daily(a.date), load_chart(a.date)
    if t is not None:
        m = t.copy()
        if c is not None and len(brk):
            b = c[c.Content.isin(brk.Content)].groupby("Date").Views.sum().rename("breakout")
            m = m.merge(b, on="Date", how="left").fillna(0)
            m["rest"] = m.Views - m.breakout
        say("\n## Daily channel views, last 28 days\n"); say(table(m.tail(28)))
        js["daily_last7_mean"] = float(m.Views.tail(7).mean())

    # channel breakdowns
    for kind, label in (("traffic_source", "Traffic source"), ("content_type", "Content type"),
                        ("device_type", "Device type"), ("sharing_service", "Sharing service"),
                        ("viewer_gender", "Gender"), ("viewer_age", "Age"),
                        ("geography", "Geography (top 12)")):
        tb = load_table(a.date, kind)
        if tb is not None:
            say(f"\n## {label}\n"); say(table(tb.head(13)))

    # retention exports
    for r in sorted(export_dir(a.date).glob("retention_*")):
        vid = r.name.split("_", 1)[1]
        row = d[d.Content.str.strip() == vid]
        csvs = [r / "Organic.csv", r / "All.csv"]
        src = next((p for p in csvs if p.exists()), None)
        if not len(row) or src is None:
            continue
        dur = int(row.dur.iloc[0])
        o = pd.read_csv(src); o["sec"] = o.iloc[:, 0] / 100 * dur
        ret = o.iloc[:, 1]; cmp_ = o.iloc[:, 2] if o.shape[1] > 2 else None
        pts = [0, 3, 5, 10, 15, 20, 30, 40, 50, 60] if dur < LONGFORM_SEC else [0, 10, 30, 60, 90, 120, 180, 240, 300, 360, 480]
        pts = [p for p in pts if p <= dur] + [dur - 1]
        curve = {p: round(float(np.interp(p, o.sec, ret)), 1) for p in pts}
        say(f"\n## Retention: {row.title.iloc[0]} ({dur} s, {int(row.Views.iloc[0]):,} views)\n")
        say("abs % at s: " + ", ".join(f"{p}:{v}" for p, v in curve.items()))
        if cmp_ is not None:
            say(f"vs comparable videos: first 30 s {cmp_[o.sec <= 30].mean():+.1f}, after {cmp_[o.sec > 30].mean():+.1f}")
        js.setdefault("retention", {})[vid] = curve

    out = export_dir(a.date)
    (out / "summary.md").write_text("\n".join(md), encoding="utf-8")
    (out / "summary.json").write_text(json.dumps(js, indent=1, default=str), encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    print("\n".join(md))
    print(f"\nwrote {out/'summary.md'} and summary.json")


# ---------------------------------------------------------------- outcomes
def outcome_block(r, date):
    lines = [f"> ## MEASURED OUTCOME {date} (yt_analytics, export to the day before)",
             ">",
             f"> **{int(r.Views):,} views, {int(r.Subscribers)} subs, {int(r.Shares)} shares, {int(r.Likes)} likes** "
             f"at {int(r.age)} days old; stayed to watch {r.stayed}%, APV {r.apv}%, "
             f"{r.get('Average view duration', '?')} AVD on {int(r.dur)} s. Family `{r.fam}`. "
             f"Clip `{r['name']}`."]
    return "\n".join(lines) + "\n\n"


def cmd_outcomes(a):
    d, _, end = load_content(a.date)
    since = pd.Timestamp(a.since) if a.since else end - pd.Timedelta(days=42)
    sel = d[(d.pub >= since) & (d.name != "")].sort_values("pub")
    sys.stdout.reconfigure(encoding="utf-8")
    for _, r in sel.iterrows():
        blk = outcome_block(r, a.date)
        doc = UPLOAD_DOCS / f"{scene_of(r['name'])}.md"
        print(f"--- {r['name']} -> {doc.name} ({doc.exists() and 'doc found' or 'NO DOC'})")
        print(blk)
        if a.write and doc.exists():
            txt = doc.read_text(encoding="utf-8")
            if f"MEASURED OUTCOME {a.date}" in txt and f"Clip `{r['name']}`" in txt:
                continue
            if not txt.endswith("\n"):
                txt += "\n"
            doc.write_text(txt + "\n" + blk, encoding="utf-8")
            print(f"    appended to {doc.name}")
    unmatched = d[(d.pub >= since) & (d.name == "") & (d.dur < LONGFORM_SEC)]
    if len(unmatched):
        print(f"\n{len(unmatched)} videos since {since.date()} have no ledger row (uploaded "
              f"before the ledger, or manually):")
        print(table(unmatched[["Content", "title", "pub", "Views"]]))


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    s = p.add_subparsers(dest="cmd", required=True)
    q = s.add_parser("ingest"); q.add_argument("--date", required=True); q.set_defaults(f=cmd_ingest)
    q = s.add_parser("ingest-ret"); q.add_argument("--date", required=True); q.add_argument("--id", required=True)
    q.add_argument("--zip"); q.set_defaults(f=cmd_ingest_ret)
    q = s.add_parser("analyze"); q.add_argument("--date", required=True); q.add_argument("--prev")
    q.add_argument("--since"); q.add_argument("--mature", type=int, default=7); q.set_defaults(f=analyze)
    q = s.add_parser("outcomes"); q.add_argument("--date", required=True); q.add_argument("--since")
    q.add_argument("--write", action="store_true"); q.set_defaults(f=cmd_outcomes)
    a = p.parse_args()
    a.f(a)


if __name__ == "__main__":
    main()
