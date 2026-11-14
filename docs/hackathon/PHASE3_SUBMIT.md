# Phase 3: finish and submit (Sun 15 Nov, 13:00 to 22:00)

The deadline is **Sun 15 Nov, 23:59 local time**; check whether the local event has an earlier one. **Nothing new after 18:00.** If something is not working by its time, cut it.

## 13:00 to 15:00: finish (both)
- **Kripas:**
  - `?embed=1` compact page (flipbook and controls only) and a "Copy embed code" button that gives an `<iframe>` snippet;
  - "Open in Aladin" and IRSA links on every frame;
  - the IRSA status indicator ("IRSA: OK / slow / down");
  - About page: how the data is cleaned, the limitations (6.15″ pixels, about 2–4 visits so far, the wavelength-range caution), credits (NASA/IPAC IRSA and the AWS open-data copy, ESA Gaia DR3, CatWISE2020 and AllWISE, CDS SIMBAD and Aladin Lite, astropy, astroquery, pyvo, reproject), and "the blink design is inspired by WiseView";
  - README:
    - how to run it;
    - how to add a new data release (`scripts/refresh_release.py`, the `SPHEREX_COLLECTIONS` override);
    - the AI disclosure.
- **Friend:** `scripts/refresh_release.py`, the IRSA status probe, and the last fixes from the review.
- **Both:**
  - tick all 8 of NASA's considerations in VALIDATION.md, each with one line saying how to see it in the tool, plus an example URL;
  - full tests (`pytest backend/tests`, `npm test` in `frontend/`);
  - merge and tag `final`.

## 15:00 to 17:00: deploy (Kripas)
- Choose the hosting and domain (the Space Apps offers: a free domain and hosting). No paid plan without asking each other first.
- One server runs FastAPI and serves `frontend/`. Copy the prepared frames for the 5 targets onto it (they are not in git).
- Pre-warm the cache for the 5 targets (Friend).
- Test from a phone and from another network: search, all 6 detectors, a typed RA/Dec, an empty position.
- Keep the old practice tool running locally as a backup demo.

## 17:00 to 20:00: video and project page
**30-second video, recorded from the real tool:**
1. 0–5 s: the Pluto discovery idea (two photos blinking).
2. 5–10 s: SPHEREx maps the whole sky in 102 colours.
3. 10–18 s: type "Barnard's Star"; it walks over the Gaia markers, in every detector.
4. 18–25 s: WISE 0855 appears only in the long-wavelength detectors (Six Eyes or colour flipbook), then a live spectrum on click.
5. 25–30 s: the name and the URL.

**Project page:**
- the title and a high-level summary;
- the video link (public, no login);
- the GitHub repo (make it public now) and the live link;
- NASA data used: SPHEREx (IRSA, AWS open data);
- other data: ESA Gaia DR3, CatWISE2020 and AllWISE, SIMBAD, Aladin (CDS);
- tools;
- references;
- the AI tools disclosure;
- both team members.

## By 22:00: submit
- [ ] The video plays without login.
- [ ] The repo is public.
- [ ] The live link works from a phone.
- [ ] Both members are on the project page.
- [ ] The submission is confirmed (screenshot it).

## 22:00 to 23:59: rehearse
- Rehearse the live pitch twice: live demo in the first 30 seconds, then the story, the limitations and questions.
- Practise these questions:
  - How do you know the motion is real? (Gaia markers, measured shift within 0.5 px, sigma differences, official flags)
  - Why does WISE 0855 show only in some detectors? (it is cold: methane absorbs at shorter wavelengths, and it glows at 4–5 µm)
  - What happens when new data arrives? (live IRSA search, `refresh_release.py`, the releases panel)
  - Could it find Planet X? (it shows how such an object would move; a real search needs more visits and depth)
  - Who would use it? (volunteers like Backyard Worlds, students, scientists)
- Honesty: never say "discovered" or "Planet X found".
