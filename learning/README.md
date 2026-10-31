# Learning folder: what we built, why, and what comes next

This folder is for **Kripas and [Friend's name]** to read later and understand the whole
project from the beginning. (From 31 Oct Kripas builds everything and [Friend's name] validates and
researches: see [`docs/plan/FRIEND_REVIEW_GUIDE.md`](../docs/plan/FRIEND_REVIEW_GUIDE.md).) Read it in order. Each file is short and in plain English.

| # | File | What you learn | Time |
|---|---|---|---|
| 0 | [00_big_picture.md](00_big_picture.md) | The challenge in simple words, what the final tool does, who does what, the road from today to 15 Nov | 10 min |
| 1 | [01_day1_what_we_built.md](01_day1_what_we_built.md) | Step 1 (find and get the data): the 6 steps of the pipeline, how to run it, what the result means | 15 min |
| 2 | [02_code_walkthrough.md](02_code_walkthrough.md) | Every Day 1 file explained piece by piece: what each function does and why it is written that way | 45 min |
| 3 | [03_archive_facts_and_mistakes.md](03_archive_facts_and_mistakes.md) | Real facts we measured in NASA's archive, and every error we hit and how we fixed it | 20 min |
| 4 | [04_whats_next.md](04_whats_next.md) | Step 2a (clean and line up), Step 2b (compare with proof), Day 4 (connect, online, test), explained from basics | 30 min |
| 5 | [05_nasa_tools_review.md](05_nasa_tools_review.md) | The tools NASA/IRSA already have for SPHEREx, their problems, and the gap our tool fills | 20 min |
| 6 | [06_how_to_win.md](06_how_to_win.md) | How judges score, which features earn points, what to add, the pitch, hard questions | 20 min |
| 7 | [07_glossary.md](07_glossary.md) | Every word you might not know (MJD, TAP, ADQL, cutout, epoch, proper motion, ...) | look up |
| 8 | [08_day1_website.md](08_day1_website.md) | Day 1 website (Kripas): what the page does, how a search flows through the code, why each choice | 20 min |
| 9 | [09_day2_flipbook.md](09_day2_flipbook.md) | Day 2 flipbook (Kripas): real SPHEREx frames, play and blink, honest labels, where the pictures come from | 15 min |
| 10 | [10_day2_pipeline.md](10_day2_pipeline.md) | Day 2 data pipeline (Kripas): clean, line up, add up, render; why each choice; how we know it works | 20 min |
| 11 | [11_day3_gaia_diff_api.md](11_day3_gaia_diff_api.md) | Day 3 (Kripas): Gaia markers, the difference in σ, the API, and how we proved Barnard's Star moves the way Gaia says | 25 min |
| 12 | [12_day4_lightcurve.md](12_day4_lightcurve.md) | Day 4 (Kripas): the light curve from single exposures, comparing only at the same wavelength, the field-star floor, R Dra's asinh scale, and the C4 tests (WISE 0855 moves like WISE 0855) | 25 min |

**The astronomy basics** (coordinates, time, light, FITS files, WCS, SPHEREx, noise and flags) are
already in [`docs/learn/`](../docs/learn/LEARN.md). This folder links to them instead of repeating them.

## How to use this folder
1. Read 00 and 01 first. You should then be able to explain the project to a friend in 2 minutes.
2. Open the code next to 02 and read them side by side. Run the commands yourself.
3. Before each practice day, read the matching part of 04.
4. Read 05 and 06 before writing the pitch.
5. Rule: if something here is not true any more (the archive changed, a plan changed), fix this file.
   These files are only useful if they stay true.

## Ground-truth rule
Every number in this folder comes from a real query or from an official NASA/IRSA document, and
the source is written next to it. If we do not know something, we write "unknown". No guesses.
