# [Friend's name]: Day 1 step by step (data side)

**Your role:** data and science. **Your branch:** `friend-backend`. **Your folder:** `backend/`.
**Today's goal:** the Day 1 data code already works (Kripas wrote it before we swapped roles). Today you make it *yours*: run it, understand it, type it again yourself, and check it against NASA's archive with your own eyes.

Every command below was run on a fresh copy of the repo on Sat 31 Oct 2026, and the "you should see" lines are the real results. If you see something different, write it down: it is either new SPHEREx data (the archive grows every week) or a real problem. Never "fix" a number to match.

Time: about 7 hours. Tick each box as you go.

---

## Step 0. Before you start (10 min, once)

- [ ] **Accept the GitHub invite** from `kripas1369` to the repo `wise-blink-practice` (check your email or https://github.com/notifications). Without it you can download the code but cannot push.
- [ ] **Python 3.11 or newer.** Check: `python3 --version` (Windows: `py --version`). Get it from https://www.python.org/downloads/ if missing. We tested with Python 3.14.
- [ ] **Git.** Check: `git --version`. Get it from https://git-scm.com/downloads if missing.
- [ ] A code editor (VS Code or Cursor).

Mac/Linux commands are shown first; Windows (PowerShell) lines are marked **Win**.

---

## Step 1. Get the code (5 min)

```bash
git clone https://github.com/kripas1369/wise-blink-practice.git
cd wise-blink-practice
git checkout friend-backend
git pull
```

You should see: `Switched to branch 'friend-backend'`. Run every later command from this `wise-blink-practice` folder (the "repo root").

---

## Step 2. Set up Python (5 min)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**Win:**
```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

- The install takes 1–2 minutes. A "new release of pip is available" notice is harmless.
- After `activate`, your prompt starts with `(.venv)`. **Every time you open a new terminal**, run the activate line again.
- `.venv/` and `cache/` are ignored by git; never commit them.

---

## Step 3. Run the tests (5 min)

```bash
python -m pytest -q
```

You should see: **`24 passed, 3 skipped`** (in about 5 seconds). A yellow `ErfaWarning ... dubious year` is harmless (a test uses a far-future date on purpose).

The 3 skipped tests use the internet. Run them too:

```bash
RUN_NETWORK=1 python -m pytest backend/tests/test_network.py -q
```
**Win:** `$env:RUN_NETWORK=1; python -m pytest backend/tests/test_network.py -q`

You should see: **`3 passed`**. It can take about 1.5 minutes, because the main SIMBAD server often times out first and the code then switches to the Harvard mirror. That is expected.

Send Kripas a message: "tests: 24 passed offline, 3 passed network" (or what you actually got).

---

## Step 4. Learn it with Kripas (Block 1, about 2 h, on a call)

Read these first, in order (about 45 min):

1. [`learning/00_big_picture.md`](../../learning/00_big_picture.md): the challenge, the final tool, who does what.
2. [`learning/01_day1_what_we_built.md`](../../learning/01_day1_what_we_built.md): the 6 steps of the data pipeline.
3. [`learning/03_archive_facts_and_mistakes.md`](../../learning/03_archive_facts_and_mistakes.md): real facts from the archive and every mistake we already made.
4. Look up words in [`learning/07_glossary.md`](../../learning/07_glossary.md) (MJD, TAP, ADQL, cutout, epoch, proper motion).

Then on the call, Kripas walks you through `notes/DAY1_REPORT.md`. By the end you should be able to answer these out loud:

- [ ] Where does SPHEREx data live, and how do we ask for it? (IRSA archive, TAP service `https://irsa.ipac.caltech.edu/TAP`, table `spherex.obscore`, ADQL query.)
- [ ] Which images cover a star? (`CONTAINS(POINT('ICRS', ra, dec), s_region) = 1`: it checks the image *outline*, not its centre.)
- [ ] Why do we move Barnard's Star before searching? (It moved 270″ = 4.5′ since 2000; a 3′ cutout at the old position misses it.)
- [ ] What are QR2 and QR3? (Two data releases: QR2 up to about April 2026, QR3 from about August 2026. We search 4 collections: `spherex_qr2`, `spherex_qr2_deep`, `spherex_qr3`, `spherex_qr3_deep`, and skip the `_cal` ones.)
- [ ] What is inside a cutout? (IMAGE, FLAGS, VARIANCE, ZODI, PSF in QR2 or EPSF in QR3, WCS-WAVE.)
- [ ] Which time do we use? (`MJD-AVG` = when the picture was taken. **Never `DATE`**: that is when the file was processed.)
- [ ] How are bad pixels marked? (Bits in FLAGS. QR2 names them with `MP_*` keywords, QR3 with `MSKN*`/`MSKM*`. `flags.py` reads both.)

---

## Step 5. Run the Day 1 report yourself (10 min, mostly waiting)

```bash
python -m scripts.day1_report
```

- It takes about **8 minutes** (it asks SIMBAD and IRSA about 5 stars and downloads 9 sample cutouts, about 4–5 MB each). Leave it running.
- It prints one line per target, then `wrote notes/DAY1_REPORT.md`.

Then see what changed:

```bash
git diff notes/DAY1_REPORT.md
```

On 31 Oct only the date and the download times changed. The table should still say:

| Target | Images | Epochs | Collections |
|---|---|---|---|
| Barnard's Star | 359 | 3 | qr2 240, qr3 119 |
| Epsilon Indi B | 445 | 4 | qr2 325, qr3 120 |
| WISE 0855 | 256 | 3 | qr2 256 |
| RW Aurigae | 333 | 3 | qr2 224, qr3 109 |
| R Draconis | 2483 | 9 | qr2 536, qr2_deep 1224, qr3_deep 723 |

If a number is **bigger**, new SPHEREx data arrived (IRSA adds data weekly). That is real: keep it and write it in your learning log. If a number is **smaller** or a target fails, tell Kripas.

If nothing but the date changed, throw the change away: `git checkout notes/DAY1_REPORT.md`.

---

## Step 6. Check one number against NASA yourself (10 min)

This proves our code does not invent numbers. Open this link in your browser. It asks IRSA's own server directly, without our code, how many science images cover Barnard's Star:

https://irsa.ipac.caltech.edu/TAP/sync?LANG=ADQL&FORMAT=csv&QUERY=SELECT%20COUNT%28%2A%29%20AS%20n%20FROM%20spherex.obscore%20WHERE%20CONTAINS%28POINT%28%27ICRS%27%2C269.446269%2C4.768204%29%2Cs_region%29%3D1%20AND%20obs_collection%20IN%20%28%27spherex_qr2%27%2C%27spherex_qr2_deep%27%2C%27spherex_qr3%27%2C%27spherex_qr3_deep%27%29

You should see a tiny file with `n` and **`359`** (on 31 Oct). Compare it with the Barnard's Star "Images" number in your report.

Optional, the point-and-click way: open the [SPHEREx Data Explorer](https://irsa.ipac.caltech.edu/applications/spherex/), search position `269.446269 4.768204`, and compare its image count. (Its count can include calibration rows, which we skip. If it differs, find out why and write it down.)

- [ ] Write both numbers in the learning log.

---

## Step 7. Open one real cutout (10 min)

From the repo root, with the venv active, type `python` to start Python, then paste this (type `exit()` to leave afterwards):

```python
from astropy.io import fits
from backend.app import archive

images = archive.attach_paths(archive.find_images(269.446269, 4.768204)[:1])
path = archive.download_cutout(images[0], 269.446269, 4.768204)
print("file:", path)
with fits.open(path) as hdul:
    hdul.info()
    print("MJD-AVG =", hdul["IMAGE"].header.get("MJD-AVG"), "  DATE =", hdul["IMAGE"].header.get("DATE"))
    print([k for k in hdul["FLAGS"].header if k.startswith(("MP_", "MSKN"))][:8])
print(archive.describe_cutout(path))
```

You should see (31 Oct, about 1 minute):
- 7 parts: `PRIMARY`, `IMAGE (29, 29)`, `FLAGS (29, 29)`, `VARIANCE (29, 29)`, `ZODI (29, 29)`, `PSF (101, 101, 121)`, `WCS-WAVE`;
- `MJD-AVG = 60902.86...` (that is 15 Aug 2025, when the picture was taken) and `DATE = 2025-09-24...` (when it was processed: **not** the observation time);
- flag names starting with `MP_` (this one is a QR2 file);
- `pct_bad` about 7.5 and `pct_source` 100.0 (Barnard's Star is so bright that every pixel near it is labelled SOURCE; SOURCE is a label, not a bad pixel).

Questions to answer in your log: Why is the cutout only 29 × 29 pixels? (0.05° at about 6.2″ per pixel.) Why is the file about 5 MB if the image is tiny? (The PSF cube comes along.)

---

## Step 8. Read the code next to the walkthrough (Block 2, about 1.5 h)

Open [`learning/02_code_walkthrough.md`](../../learning/02_code_walkthrough.md) on one side and the code on the other. Go section by section:

| Section in `learning/02` | File |
|---|---|
| 1 | `backend/app/config.py` |
| 2 | `backend/app/coords.py` |
| 3 | `backend/app/motion.py` |
| 4 | `backend/app/resolve.py` |
| 5 | `backend/app/targets.py` |
| 6 | `backend/app/archive.py` |
| 6b | `backend/app/flags.py` |
| 7 | `scripts/day1_report.py` |
| 8 | `backend/tests/` |

For every function, say in one sentence what goes in, what comes out, and what can go wrong.

---

## Step 9. Type the code again yourself (Block 3, about 2.5 h)

This is how you will be able to rebuild it from memory on 14 Nov. Do one file at a time, in this order:

| Order | File | Check with | Expect |
|---|---|---|---|
| 1 | `coords.py` | `python -m pytest backend/tests/test_coords.py -q` | 12 passed |
| 2 | `motion.py` | `python -m pytest backend/tests/test_motion_archive.py -q` | 8 passed |
| 3 | `flags.py` | `python -m pytest backend/tests/test_flags.py -q` | 4 passed |
| 4 | `resolve.py` | `RUN_NETWORK=1 python -m pytest backend/tests/test_network.py -q` | 3 passed |
| 5 | `archive.find_images` | same network test, plus Step 5 again | 3 passed; same table |

For each file:

1. Keep a copy of the original (the `scratch/` folder is ignored by git):
   ```bash
   mkdir -p scratch
   cp backend/app/coords.py scratch/coords_original.py
   ```
   **Win:** `mkdir scratch` (once), then `copy backend\app\coords.py scratch\coords_original.py`
2. Open `backend/app/coords.py`. Keep the imports at the top, **delete everything else**, and type it again from the description in `learning/02`. Do not look at the original.
3. Run the test from the table. **Never edit the tests** to make them pass.
4. When it passes, compare: `git diff backend/app/coords.py`. Different code is fine if the tests pass and you can explain it.
5. Stuck for more than 20 minutes? Look at `scratch/coords_original.py`, then close it and type the rest yourself. Write in the log where you got stuck (that is useful, not a failure).
6. Want the original back? `git checkout backend/app/coords.py`

Then do the 4 exercises at the end of `learning/02`.

---

## Step 10. Finish the day (20 min)

1. Fill in your entry in `notes/LEARNING_LOG.md` (the "Day 1, Sat 31 Oct, [Friend's name]" section): what you learned, what broke or confused you, planned vs actual hours, and the two Barnard's Star counts from Step 6.
2. Save your work to GitHub:
   ```bash
   git status                 # check: no .venv, cache or .fits files listed
   git add backend notes/LEARNING_LOG.md
   git commit -m "Day 1 (friend): ran tests and report, checked IRSA count, re-typed coords/motion/flags/resolve"
   git push
   ```
3. Open a pull request on GitHub: `friend-backend` → `main` (GitHub shows a "Compare & pull request" button after the push). Kripas reviews it.
4. 15-minute call with Kripas: show each other what works. Agree on tomorrow (Day 2): you will send Barnard's Star PNG frames plus JSON for his flipbook.

---

## Done when (Day 1 checklist)

- [ ] 24 offline tests and 3 network tests pass on **your** laptop.
- [ ] You ran the report, and its numbers match the table above (or you explained why they grew).
- [ ] Your own IRSA count for Barnard's Star matches the report.
- [ ] You opened one cutout and can name its 7 parts and say why `MJD-AVG`, not `DATE`.
- [ ] You re-typed at least `coords.py`, `motion.py` and `flags.py`, and the tests pass.
- [ ] Learning log written, pushed to `friend-backend`, pull request opened.

---

## If something goes wrong

| Problem | Fix |
|---|---|
| `python3: command not found` | Mac: install from python.org. Windows: use `py` instead of `python3`. |
| `ModuleNotFoundError: No module named 'backend'` | You are not in the repo root. `cd` into `wise-blink-practice` and run again. |
| `ModuleNotFoundError: astropy` (or pyvo, pytest) | The venv is not active. Run the activate line from Step 2. |
| **Win:** "running scripts is disabled on this system" | Run once: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, then activate again. |
| Network test or report hangs for a long time | SIMBAD's main server is slow; the code waits, then uses the Harvard mirror. Wait about 2 minutes before worrying. |
| `503` or "busy" from IRSA | Too many downloads at once. Wait a minute and run again; never run two reports at the same time. |
| `git push` asks for a password or says "permission denied" | Accept the GitHub invite (Step 0). GitHub needs a personal access token or GitHub Desktop, not your password. |
| A test fails after you re-typed a file | Read the error from the bottom up: it shows the input, what you returned, and what was expected. |

Questions: ask Kripas, or ask the AI "explain this error" and paste the full error.
