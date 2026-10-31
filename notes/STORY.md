# Our story (5 beats)

Kripas, Day 1 (Sat 31 Oct 2026). Plan: [HACKATHON_PLAN Part F](../docs/plan/HACKATHON_PLAN.md#part-f-story-pitch-and-video).
Rule: every number has a source. A beat we have not proven yet is marked **not yet proven**.

**One line:** In 1930 one person found Pluto by blinking two photos. Today SPHEREx photographs the whole sky in 102 colours, and our tool lets anyone do what Tombaugh did.

---

## 1. Tombaugh's blink
- In February 1930, Clyde Tombaugh at Lowell Observatory compared two photos of the same patch of sky, taken days apart (23 and 29 January 1930), with a *blink comparator*. One dot jumped. It was Pluto.
- The idea: stars stay still, so anything that moves or changes between two pictures stands out.
- Source: Lowell Observatory history of the Pluto discovery.

## 2. Too much SPHEREx data for one person
- SPHEREx (NASA, launched March 2025) maps the whole sky in 102 colours (0.75–5.0 µm) and repeats it every 6 months.
- We counted the images ourselves on Day 1 (IRSA archive, 31 Oct 2026, [`DAY1_REPORT.md`](DAY1_REPORT.md)): Barnard's Star has 359 images over 3 visits; R Draconis, near the deep-survey area, has 2483 images over 9 visits.
- NASA's own web tools show one image at a time; there is no "flip through time" view ([`learning/05`](../learning/05_nasa_tools_review.md)).

## 3. Our tool
- Type a star name or a position, or click the sky. The page shows that patch and (from Day 2) flips through the SPHEREx visits like Tombaugh's blink.
- Works on a phone, in plain words, and every link can be shared.

## 4. Proof
- **Proven on Day 1:** our page moves each star to where it is *today* using its catalogue motion. On the old 2MASS map (taken 1997–2001), Barnard's Star sits about 4.5′ south of today's position: 26 years of motion, visible by eye. Clicking the bright star on the map gave a position within about 2″ of its catalogue (year 2000) position.
  - Today's position, empty on the old map: `screenshots/day1_barnard_2026_position.png`
  - The star where it was in about 2000: `screenshots/day1_barnard_j2000_on_2mass.png`
  - Both in one view (phone): `screenshots/day1_mobile_barnard_offset.png`
- **Not yet proven:** Barnard's Star walks about 1.7 SPHEREx pixels between its first and last visit and lands on its Gaia positions (Day 3).
- **Not yet proven:** WISE 0855 appears only in the 4–5 µm detectors, which tells us it is cold (Day 2–3).
- **Not yet proven:** R Draconis brightens and fades in step with AAVSO observers' data (Day 4).

## 5. Impact
- Anyone can look for things that move or change: students, volunteers, scientists.
- Two students from Nepal learned SPHEREx data in a few weeks and built this; the tool is meant to be that easy for the next person.
- Honest limits: we never say "discovered" or "Planet X found". The tool shows how such an object *would* move; a real search needs more data and checking.
