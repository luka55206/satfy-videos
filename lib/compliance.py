"""Publishing-rule gate: trademark, gambling-adjacent wording, audio provenance.

Pure stdlib (no numpy/cairo) so it runs anywhere. Used by tools/compliance_check.py
and importable from any scene or upload tool. These are RISK-REDUCTION rules
compiled from the platform policies as understood on 2026-10-04 -- not legal
advice. Re-check YouTube's current wording at upload time.
"""
import json
import re
from pathlib import Path

# 1. Trademarks. PLINKO is a registered mark (FremantleMedia / The Price Is
#    Right). Default = never in anything a viewer or YouTube's systems can read.
#    The owner may relax ONE term deliberately by editing ALLOW_TERMS below.
BANNED_TRADEMARKS = ["plinko", "price is right", "fremantle", "pachinko"]
ALLOW_TERMS: list = []          # e.g. ["plinko"] ONLY if the owner decides so

# 2. Gambling-adjacent wording. Plinko-style games are a casino category; the
#    channel is a physics/statistics toy, never a game you can win at.
BANNED_GAMBLING = [
    "casino", "gambl", "bet ", "bets", "betting", "jackpot", "payout",
    "multiplier", "wager", "stake.com", "bonus code", "promo code",
    "real money", "cash out", "cashout", "win big", "big win", "you win",
    "free spins", "slots", "roulette", "crypto", "$", "usd", "prize",
    "lottery", "odds of winning", "promo", "affiliate",
]

# 3. Other people's IP that "ball drop / marble" content tends to drift into.
BANNED_IP = ["pac-man", "pacman", "bandai", "tetris", "minecraft", "mario",
             "nintendo", "disney", "pokemon", "squid game", "mrbeast",
             "mr beast", "marble race", "algodoo", "piano tiles", "magic tiles"]

# 4. Audio provenance: ONLY these event voices (all synthesised in lib/audio.py).
ALLOWED_VOICES = {"marimba", "glassharp", "piano"}


def _hay(text: str) -> str:
    return " " + re.sub(r"\s+", " ", text.lower()) + " "


def scan_text(text: str, where: str = "text"):
    """-> list of (severity, where, term). severity: FAIL | WARN."""
    h = _hay(text)
    out = []
    for term in BANNED_TRADEMARKS:
        if term in ALLOW_TERMS:
            continue
        if term in h:
            out.append(("FAIL", where, f"trademark '{term}'"))
    for term in BANNED_GAMBLING:
        if term in h:
            out.append(("FAIL", where, f"gambling wording '{term.strip()}'"))
    for term in BANNED_IP:
        if term in h:
            out.append(("FAIL", where, f"third-party IP '{term}'"))
    return out


def scan_metadata(title="", description="", tags=(), filename="", hashtags=()):
    out = []
    out += scan_text(title, "title")
    out += scan_text(description, "description")
    out += scan_text(" ".join(tags), "tags")
    out += scan_text(" ".join(hashtags), "hashtags")
    out += scan_text(filename, "filename")
    if not (title or "").strip():
        out.append(("FAIL", "title", "empty title"))
    return out


def scan_events(events_json: Path):
    """Audio sidecar check: no unknown voice, no sample/music-bed fields."""
    out = []
    data = json.loads(Path(events_json).read_text(encoding="utf-8"))
    evs = data["events"] if isinstance(data, dict) and "events" in data else data
    for key in ("voice", "sample", "music", "bed", "melody"):
        if isinstance(data, dict) and data.get(key):
            if key == "voice" and data[key] in ALLOWED_VOICES:
                continue
            out.append(("FAIL", "events", f"'{key}' = {data[key]!r} (only "
                        f"original synthesis allowed)"))
    for e in evs:
        for key in ("sample", "music", "melody", "file"):
            if e.get(key):
                out.append(("FAIL", "events", f"event has '{key}'"))
                break
    return out


def scan_scene_source(py_file: Path):
    """Static guard on a scene file: no melody bank, no samples, no music beds."""
    src = Path(py_file).read_text(encoding="utf-8")
    out = []
    for pat, msg in ((r"kit\.melody\(|pick_melody\(|MelodyWalker\(|melody_notes\(",
                      "uses the melody bank (locked)"),
                     (r"load_sample\(|SAMPLE_VOICES|pac_sample\(",
                      "uses recorded samples (provenance unproven)"),
                     (r"music_clip\(|MUSIC_CUSTOM", "uses a music bed"),
                     (r"voice\s*=\s*['\"](?!marimba|glassharp|piano)",
                      "non-whitelisted voice")):
        if re.search(pat, src):
            out.append(("FAIL", py_file.name, msg))
    return out
