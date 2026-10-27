---
name: us-audience
description: >
  Write every video for an AMERICAN audience: US units first with metric in
  parentheses ("220 lb (100 kg)", "13 km" → "8 miles (13 km)"), American
  spelling and names, US objects and landmarks, US upload times. Use whenever a
  video, Short, long-form, thumbnail, title, description, pinned comment or
  on-screen text is written or edited, and whenever the owner says "make it for
  Americans", "US style", "American units", "convert to US", or asks to raise
  the US share of views. Applies on top of make-video, episode-batch, redesign,
  ship-clip, long-form, compilation and youtube-upload.
---

# US audience — the default style for every video (owner, 2026-10-27)

**Why:** US viewers pay the most. Measured 2026-10-27 (Studio, lifetime): the US
is 20% of views but ~60% of estimated Shorts revenue and ~60% of long-form
revenue. Estimated RPM: US long-form ~$4, Philippines/Indonesia/India/Vietnam
$0.2-0.3. Blended: Shorts ~$0.04, long-form ~$1.40 per 1,000 views.
US viewers also watch longer (0:41 avg vs 0:30 Indonesia/Brazil).

## 1. Units: US first, metric in parentheses

| quantity | write | never |
|---|---|---|
| mass | `220 lb (100 kg)`, `2.2 million lb (1,000 t)`, `2.2 × 10²⁴ lb (10²⁴ kg)` | `100 kg` alone, `tonnes` |
| big mass words | `tons` = US short tons (1 t = 1.1 tons) | `tonnes` |
| length | `6 ft (1.8 m)`, `1,083 ft (330 m)`, `29,032 ft (8,849 m)` | `m` alone |
| distance | `239,000 miles (384,400 km)`, `62 miles (100 km)` | `km` alone |
| small length | `0.004 in (0.1 mm)` or `a hair-thin sheet (0.1 mm)` | |
| volume | `gallons (liters)` | |
| temperature | `°F (°C)` | |
| speed | `mph (km/h)` | |

- **Physics stays exact.** Simulate in whatever unit keeps the math clean; only
  the LABELS change. π blocks: masses are powers of 100 in kg, the ratio is what
  makes π, so `lbs()` / `us()` in `scenes/pi_long.py` label them
  (`us(100.0)` → `220 lb (100 kg)`). Reuse those helpers; never re-derive.
- When the second unit makes a line too long, keep US on screen and put metric in
  a smaller line below (see `pi_long.ch_other`), never drop the US value.
- Ratios need no unit: "a block 1,000,000× heavier" beats "2.2 million lb" in a
  hook.
- Round US values to 2 significant figures (2.2, 220, 22,000), like the metric
  ones they replace. Re-check every derived fact after converting (a wrong "×700
  cars" is worse than metric).

## 2. Words and spelling

- American spelling: color, center, gray, meter/liter (in parentheses), realize,
  behavior, math (never "maths"), airplane, program, catalog.
- American names: garbage truck (not lorry), soccer field / football field (US
  football), cell phone, apartment, sidewalk, gas, fall (autumn), movie,
  high school, grade 7 (not year 7), counting with commas (1,000,000).
- Large numbers: million / billion / trillion (short scale), commas, never spaces.
- Dates: Month Day ("March 14" = Pi Day).
- Titles: American phrasing, no British idioms.

## 3. Objects and references (prefer US ones when it is a choice)

| instead of | use |
|---|---|
| Eiffel Tower (1,083 ft) | Empire State Building (1,454 ft) or the Statue of Liberty (305 ft) |
| a lorry / a bus | a school bus (~25,000 lb), a garbage truck (~22,000 lb), a pickup (~5,000 lb) |
| a football pitch | an American football field (360 ft long) |
| generic lake | Lake Michigan, Lake Tahoe, Lake Mead |
| generic canyon / mountain | the Grand Canyon, Mount Rainier, Denali (keep Everest when it is "the highest") |
| a city | New York, Texas-sized, coast to coast (2,800 miles) |
| a person | "an average American (~200 lb)" when the figure matters |

Keep a world object when it is THE record (Everest, the Moon, the Sun): the
number is what matters, the unit is what changes.

## 4. Compliance still wins

No money: dollars are money. Never use "$", prices, "worth", salaries, even in
US-style comparisons (`docs/compliance.md`). Use pounds, feet, miles, years,
school buses, football fields instead.

## 5. Publishing

- **Upload time:** US evening 6-10 pm Eastern = 02:00-06:00 Tbilisi; US lunch
  12-1 pm Eastern = 20:00-21:00 Tbilisi. Schedule, never publish in the Georgian
  daytime by default.
- Descriptions: US spelling, US units first; hashtags unchanged.
- Thumbnails: US units (`2.2 LB vs 1/6 OF THE EARTH`).
- Seasonal US hooks: Pi Day (March 14), back to school (late August), Halloween,
  Thanksgiving, the Super Bowl (as a size/time reference, not the brand).

## 6. Checklist before staging

1. grep the scene and the `.md` for ` kg"`, ` km"`, ` m"`, `tonne`, `metre`,
   `colour`, `centre`, `grey`, `maths`: each hit is either converted or sits in
   parentheses after a US value.
2. Every converted number recomputed (not eyeballed).
3. A still of every text-heavy frame: the longer US + metric labels still fit
   (`max_w`) and do not overlap the caption.
4. `tools/compliance_check.py` on the title / description / tags (no "$").

## 7. Not this skill

It never changes the math or the mechanic, and it never removes a metric value
(non-Americans need it). A per-video owner override wins for that video.
