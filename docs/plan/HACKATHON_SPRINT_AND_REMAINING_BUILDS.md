# SPHEREx Blink: Hackathon Sprint & Remaining Builds
**Document Version:** 1.0 (Team Alignment Reference)  
**Target:** NASA International Space Apps Challenge 2026 — SPHEREx: The Hunt for Planet X and Friends  
**Authors:** Team Not42 (Data & Science Lead: lazylog00 | Engineering Lead: Kripas Khatiwada)  
**Date:** November 2026  

---

## Executive Summary: Where We Stand

We are entering the hackathon in a commanding position. While competing projects (like *SkyShift*) built basic visual swipe tools, our project possesses **true astronomical rigor**:
- **Backend Complete:** 26 modules operational, **148 passed tests**, 0 failures.
- **Scientifically Grounded:** Raw Level-2 FITS ingestion, 5-sigma statistical difference dipoles, sub-pixel centroiding (±0.11 px), topocentric asteroid parallax with NASA JPL Horizons, and 96-channel infrared spectroscopy across Detectors 1–6.
- **The Core Mission Gap Solved:** NASA IRSA has no tool to compare visits across epochs (*Bock et al. 2026*, Table 5). We built the tool NASA lacks.

This document outlines the **exact remaining frontend tasks to build**, the division of labor, and the 1-minute winning pitch for NASA judges.

---

## 1. What Is Already 100% Complete & Tested

| Module / System | File Location | Status | What It Delivers |
|---|---|---|---|
| **Astrometric TAN Alignment** | `backend/app/align.py` | COMPLETE | Un-tilts rotated space exposures onto a North-Up, East-Left grid. |
| **Inverse-Variance Stacking** | `backend/app/coadd.py` | COMPLETE | 1/σ² coaddition beating down Gaussian noise by 1/√N (~65% noise reduction). |
| **Statistical Difference Maps** | `backend/app/diff.py` | COMPLETE | Computes normalized z = (B - A - Δsky) / √(σ_A² + σ_B²), requiring \|z\| ≥ 5.0σ. |
| **LVF Wavelength Pairing** | `backend/app/diff.py` | COMPLETE | `default_pair` restricts Δλ ≤ 0.05 µm, eliminating false flashing of red stars. |
| **Satellite Parallax Asteroids** | `backend/app/known_objects.py` | COMPLETE | Feeds SPHEREx 3D orbit vectors (X_SC, Y_SC, Z_SC) to JPL Horizons. |
| **Gaia DR3 Proper Motion** | `backend/app/gaia.py` | COMPLETE | Propagates catalog stars forward to observation MJD. |
| **96-Channel Spectroscopy** | `backend/app/spectrum.py` | COMPLETE | Stitches continuous infrared SED from 0.75 to 5.0 µm in physical flux (mJy). |
| **Scientist Pixel Inspector** | `backend/app/pixels.py` | COMPLETE | Exposes 32-bit hardware flag bitmasks in decimal, hex, and binary. |
| **Web Server & Endpoints** | `backend/app/main.py` | COMPLETE | FastAPI server running live on port 8000 with all `/api/...` endpoints. |

---

## 2. What Remains to Build / Enhance in Frontend

These 4 high-leverage UI enhancements will secure the **"Best Use of Data"** and **"Most Innovative"** awards:

### Task 1: Explicit Error Bars & Confidence Metrics in UI
* **Files to Edit:** `frontend/js/proof.js`, `frontend/js/diffview.js`
* **Current UI Behavior:** Shows bare numbers (e.g. *"it moved 1.59 pixels north"*).
* **The Upgrade:**
  - In the **Proof Card**, display the full scientific measurement:
    > **Measured Shift:** `1.59 ± 0.11 px` (`9.78 ± 0.68″`)  
    > **Expected (Gaia DR3):** `1.67 px` (`10.27″`)  
    > **Discrepancy:** `0.08 px` (`4.8%`, well within the 1-sigma error budget)  
    > **Statistical Significance:** `7.8-sigma detection` (99.9999% confidence)
  - For stationary targets (RW Aurigae):
    > **Measured Shift:** `0.07 ± 0.11 px` → Tagged: *"Motion below 0.30 px threshold (too small to test / stationary)"*.
* **Why Judges Love This:** It proves we understand detector sampling physics and don't make unsubstantiated discovery claims.

---

### Task 2: One-Click "Download Discovery Dossier" Button
* **Files to Edit:** `frontend/index.html`, `frontend/js/spots.js`, `frontend/js/diffview.js`
* **The Upgrade:**
  - Add a primary action button under the candidate spot details:
    **`[ 📥 Download Candidate Discovery Dossier (JSON / Markdown) ]`**
  - When clicked, it generates and downloads a formatted dossier containing:
    1. Target coordinates (RA, Dec in J2000).
    2. Observation baseline (dates, MJD, days spanned).
    3. Astrometric significance (peak +z and -z dipole values, e.g. `+8.4σ / -7.9σ`).
    4. Measured proper motion rate (arcsec/year).
    5. Gaia DR3 cross-match result (Negative / Uncataloged).
    6. JPL Horizons topocentric asteroid check result (Negative / New Body).
    7. 96-channel infrared flux table (Detectors 1–6 in mJy).
    8. Direct NASA IRSA Level 2 data provenance URLs.
* **Why Judges Love This:** It transforms our web app from a passive viewer into a **real scientific discovery pipeline** that produces submission-ready dossiers for the Minor Planet Center and SPHEREx Science Team.

---

### Task 3: The 4-Timescale Category Badges (Inspired by SkyShift)
* **Files to Edit:** `frontend/index.html`, `frontend/js/targets.js`
* **The Upgrade:**
  - Add a small visual pill badge next to each target indicating the physical timescale being analyzed:
    - **Hours (Intra-Visit):** For fast asteroids crawling across single-visit exposures (Ceres, Hygiea).
    - **Days:** For slow outer solar system drift (Pluto at 3 px/day).
    - **Months (Survey Passes):** For stellar variability and dust obscuration (RW Aurigae dimming by 37%).
    - **Years (Multi-Pass):** For high-proper-motion stars and distant Planet X candidates (Barnard's Star, WISE 0855).
* **Why Judges Love This:** It instantly explains to non-expert judges *why* different targets have different time gaps.

---

### Task 4: Polish the 1-Minute Live Demo Walkthrough
* **Preparation for Team:**
  - **Step 1 (0:00 - 0:15):** Open `http://localhost:8000`, click **Barnard's Star**. Explain that reference stars sit motionless in thin circles while Barnard jumps North by 1.59 px across 360 days.
  - **Step 2 (0:15 - 0:30):** Scroll to **Difference Map**. Show the clean orange/blue dipole exceeding 5-sigma.
  - **Step 3 (0:30 - 0:45):** Click **Check JPL Asteroids** to demonstrate topocentric satellite parallax vetting.
  - **Step 4 (0:45 - 1:00):** Scroll to the **Spectrum**. Show that SPHEREx is a 102-color spectrometer, revealing the full 96-band SED from 0.75 to 5.0 µm.

---

## 3. Recommended Division of Labor

* **Kripas (Engineering / UI Lead):**
  - Implement Task 1 (styling the error bars in the Proof Card).
  - Implement Task 2 (adding the Download Dossier button in `spots.js`).
  - Implement Task 3 (Timescale badges in `targets.js`).
* **lazylog00 (Science & Astrometry Lead):**
  - Verify mathematical calculations and error margins during live judging.
  - Present the core scientific narrative: explaining the mission gap, 5-sigma thresholds, and why 30-day/60-day grouping works.
  - Deliver the pitch and lead Q&A defense.

---

## 4. The 30-Second Elevator Pitch to Memorize

> *"NASA launched SPHEREx to map the sky four times in 102 infrared colors to find moving objects. However, NASA's official IRSA archive has no tool to compare visits across epochs—their moving object catalogs won't arrive until May 2028.
>
> We built **SPHEREx Blink**. Our pipeline un-tilts rotated space exposures onto standard tangent grids, coadds with inverse-variance weights, and computes 5-sigma statistical difference dipoles.
>
> When a candidate mover is spotted, our engine eliminates false alarms: it vetoes cosmic rays and streaks, matches Gaia DR3 proper motions, queries NASA JPL Horizons using the satellite's exact 3D orbital telemetry to catch asteroids, and extracts the 96-channel infrared spectrum to verify its chemical signature—all in one open-source web tool."*

