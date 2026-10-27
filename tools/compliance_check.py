"""Pre-ship / pre-upload gate. Exit code 1 on any FAIL.

    python tools/compliance_check.py --title "..." [--description "..."] \
        [--tags a,b] [--clip output/pegdrop_s0_9x16.mp4] [--scene scenes/pegdrop.py]
    python tools/compliance_check.py --scenes          # lint every scene file

--clip  : filename + sibling <name>_events.json (voices/samples) are scanned.
Run it on EVERY upload's title/description/tags and on every new scene.
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lib import compliance as C  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--title", default="")
    ap.add_argument("--description", default="")
    ap.add_argument("--tags", default="")
    ap.add_argument("--clip", default="")
    ap.add_argument("--scene", default="")
    ap.add_argument("--scenes", action="store_true")
    a = ap.parse_args()

    issues = []
    if a.title or a.description or a.tags or a.clip:
        issues += C.scan_metadata(
            a.title, a.description,
            [t for t in a.tags.split(",") if t.strip()],
            filename=Path(a.clip).name if a.clip else "")
    if a.clip:
        ev = Path(a.clip).with_name(Path(a.clip).stem + "_events.json")
        if ev.exists():
            issues += C.scan_events(ev)
        else:
            print(f"note: no sidecar {ev.name} (fine inside final/, where "
                  f"sidecars are not kept) -- run it on output/ before staging")
    scenes = [Path(a.scene)] if a.scene else []
    if a.scenes:
        scenes += [p for p in (ROOT / "scenes").glob("*.py")]
    for s in scenes:
        issues += C.scan_scene_source(s)

    for sev, where, what in issues:
        print(f"{sev}  [{where}]  {what}")
    fails = [i for i in issues if i[0] == "FAIL"]
    print(f"compliance: {len(fails)} FAIL, {len(issues) - len(fails)} WARN")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
