# 09. Day 2 flipbook: real SPHEREx pictures, played over time

Code: `frontend/js/flipbook.js`, `frames.js`, `player.js`; sample frames from `scripts/sample_frames.py`. Run the site as in [08](08_day1_website.md) and click a target, then scroll to **SPHEREx flipbook**.

## What the flipbook does
1. **Play:** shows each SPHEREx visit of the 3′ square in time order (0.5–4 per second, loop on or off, ◀ ▶ buttons, slider, arrow keys, space bar).
2. **Blink 2 visits:** two chosen visits swap quickly (default: first and last, the biggest time gap). This is the 1930 Pluto method.
3. **Label under the picture** (every value from the data): visit number, date and time (UTC), detector, the **wavelength at the star**, exposures used, % pixels flagged, % with no value.
4. **On the picture:** dashed ring = the target's 2026 position; N ↑ E ← ; a 1′ scale bar (exactly 60 / 6.15 = 9.76 pixels); red pixels = flagged bad (toggle); stripes = the file has no value there.
5. **Orange box "Before you trust your eyes":** measured warnings for this target (for example the dot next to WISE 0855).
6. **Honest messages** when there is nothing to show: any non-target position ("arrives with the data API, Day 3"), a detector with no frames (with buttons for the ones we have), a broken file (names the problem).

## Where the pictures come from (`scripts/sample_frames.py`)
```
SIMBAD position, moved to 2026.0          (same rule as the website's ring)
→ IRSA: every SPHEREx image of that spot in detector N, grouped into visits
→ per visit: ONE exposure (the one closest to the visit's middle)
→ cutout → IMAGE − ZODI, official bad-pixel mask
→ reproject onto one north-up 29 × 29 grid of 6.15″ pixels
→ one brightness scale for all visits → PNG + manifest.json
```
This is a **sample**: one exposure per visit, so it is noisy. [Friend's name]'s pipeline adds up all exposures of a visit and replaces these files in the same format ([`FRAMES_FORMAT.md`](../docs/plan/FRAMES_FORMAT.md)).

## Why each choice
| Choice | Reason |
|---|---|
| `image-rendering: pixelated` | A 29-pixel picture shown 380 px wide must keep square pixels; smoothing would invent detail. |
| One brightness scale for every visit | Otherwise a star looks brighter just because the scale changed. |
| Show the wavelength at the star | SPHEREx's filter (LVF) changes wavelength across the detector, so the same star is seen at 1.235 µm in one visit and 1.539 µm in another. A brightness change can come from that, not from the star. |
| Stripes for "no value" | Painting NaN as black would look like empty sky; the core of Barnard's Star is saturated, not dark. |
| `checkManifest` refuses bad files | Frames we cannot label honestly (no time, wrong detector, out of order) are never shown. |
| Load counter in `show()` | If you click another target while frames load, the old ones cannot appear on top. |
| Typed position within 5″ of a target gets its frames | Same patch of sky, so the same frames apply. |

## What we saw (real, 31 Oct)
- Barnard's Star D2: 3 visits over 360 days; 4.0–8.8% flagged; 0.7–1.2% no value at the saturated core. Picture: `notes/screenshots/day2_barnard_d2_flipbook.png`.
- WISE 0855: **not clearly seen** in single D6 exposures (2–5 sigma), and a fixed background dot sits 9″ away in D2. Details and the other targets: [`notes/DAY2_FINDINGS.md`](../notes/DAY2_FINDINGS.md).

## Re-type exercise (Kripas)
Re-type `player.js` (4 small functions) and `frames.js` (`checkManifest`, `frameLabel`) from the descriptions above; run `npm test` until all pass.
