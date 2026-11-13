"""Stage E: choose the variable-protostar sample and matched controls from the SPLICES query result.

    PYTHONPATH=.:research .venv/bin/python research/discovery_2026/scripts/choose_sample.py

Rules (fixed before any of these sources was analysed; see TARGET_SELECTION.md):
  embedded:  class_1 == 'YSO_P' or stype_ml == 'Class I YSO'
  brightness: 6.0 < W2 < 9.5 and W1 > 6.5 (SPHEREx cores saturate for W1 <~ 6: Elias 16 W1 4.5, Elias 29 W1 3.9)
  isolation: SPLICES fluxratioi2 (IRAC 4.5 um neighbours within 7.6") <= 20 % or not measured
  exclusions: within 60" of a Karambelkar et al. 2026 transient or of the validation targets EC 53 / V1647 Ori
  VAR:  w2var_class in (L, C, B, D, I) and w2varamp >= 1.0 mag   (NEOWISE secular change, SPLICES v8.6)
  CTRL: w2var_class == 'N'
N_VAR variables are drawn at random (numpy seed SEED); each is paired with the not-yet-used CTRL source closest in
W2 (|dW2| <= 0.3 mag) of the same embedded class. Background-star controls (SPLICES MAIN, Av > 25, non-variable) are
added from the second query when available.
Output: data/lists/sample.csv, data/selection/sample_selection.json
"""
import csv
import json
import math
from pathlib import Path

import numpy as np
from astropy.table import Table

ROOT = Path(__file__).resolve().parents[1]
SEL = ROOT / "data" / "selection"
LISTS = ROOT / "data" / "lists"
SEED = 20261113
N_VAR = 36
N_BG = 12
EXCLUDE = {  # name: (ra, dec)
    "WTP16aakapb (Karambelkar+2026)": (344.6562, 58.7708),
    "WTP15aaavof (Karambelkar+2026)": (348.5257, 61.5151),
    "FU Ori (Karambelkar+2026 comparison)": (88.0730, 9.0687),
    "V900 Mon (Karambelkar+2026 comparison)": (101.4250, -8.4086),
    "V1057 Cyg (Karambelkar+2026 comparison)": (314.7963, 44.2589),
    "EC 53 (validation)": (277.46325, 1.27789),
    "V1647 Ori (validation)": (86.5547, -0.1013),
}


def sep_arcsec(ra1, dec1, ra2, dec2):
    d = math.radians
    c = math.sin(d(dec1)) * math.sin(d(dec2)) + math.cos(d(dec1)) * math.cos(d(dec2)) * math.cos(d(ra1 - ra2))
    return math.degrees(math.acos(min(1.0, max(-1.0, c)))) * 3600


def val(r, k):
    v = r[k]
    return None if np.ma.is_masked(v) else v


def main():
    t = Table.read(SEL / "splices_protostars_w2lt10p5.csv")
    rows = [dict(zip(t.colnames, r)) for r in t]
    log = {"n_query": len(rows), "seed": SEED, "steps": []}

    def step(name, keep):
        log["steps"].append({"cut": name, "remaining": len(keep)})
        return keep

    emb = step("embedded (YSO_P or Class I)", [r for r in rows if str(val(r, "class_1")) == "YSO_P"
                                              or str(val(r, "stype_ml")) == "Class I YSO"])
    bright = step("6.0 < W2 < 9.5 and W1 > 6.5", [r for r in emb if val(r, "w2") is not None and 6.0 < r["w2"] < 9.5
                                                  and val(r, "w1") is not None and r["w1"] > 6.5])
    iso = step("fluxratioi2 <= 20% or missing", [r for r in bright if val(r, "fluxratioi2") is None
                                                 or r["fluxratioi2"] <= 20])
    excl = []
    for r in iso:
        hit = [n for n, (a, b) in EXCLUDE.items() if sep_arcsec(r["ra"], r["dec"], a, b) < 60]
        if hit:
            log.setdefault("excluded_by_position", []).append({"designation": str(r["designation"]), "near": hit})
        else:
            excl.append(r)
    clean = step("not within 60\" of excluded objects", excl)
    var = [r for r in clean if str(val(r, "w2var_class")) in ("L", "C", "B", "D", "I")
           and val(r, "w2varamp") is not None and r["w2varamp"] >= 1.0]
    ctrl = [r for r in clean if str(val(r, "w2var_class")) == "N"]
    log["n_var_pool"], log["n_ctrl_pool"] = len(var), len(ctrl)
    rng = np.random.default_rng(SEED)
    order = rng.permutation(len(var))
    chosen, used = [], set()
    for i in order:
        if sum(c["role"] == "VAR" for c in chosen) >= N_VAR:
            break
        v = var[i]
        cand = [c for c in ctrl if str(c["designation"]) not in used and abs(c["w2"] - v["w2"]) <= 0.3]
        if not cand:
            log.setdefault("var_without_control", []).append(str(v["designation"]))
            continue
        c = min(cand, key=lambda c: (abs(c["w2"] - v["w2"]), str(c["designation"])))
        used.add(str(c["designation"]))
        pair = len([x for x in chosen if x["role"] == "VAR"])
        chosen.append({**v, "role": "VAR", "pair": pair})
        chosen.append({**c, "role": "CTRL", "pair": pair})
    bg_file = SEL / "splices_background_stars.csv"
    if bg_file.exists():
        b = Table.read(bg_file)
        brow = [dict(zip(b.colnames, r)) for r in b if not np.ma.is_masked(r["w1"]) and r["w1"] > 6.5]
        # YSOs and AGB stars have their own circumstellar dust, so they cannot isolate interstellar ice.
        brow = [r for r in brow if not any(s in str(r.get("stype_ml") or "") for s in ("YSO", "AGB"))]
        log["n_background_pool"] = len(brow)
        for i in rng.permutation(len(brow))[:N_BG]:
            chosen.append({**brow[i], "role": "BGSTAR", "pair": -1})
    for name, (ra, dec) in (("EC53", (277.46325, 1.27789)), ("V1647Ori", (86.5547, -0.1013))):
        chosen.append({"designation": name, "name": name, "ra": ra, "dec": dec, "role": "VALIDATION", "pair": -1})
    LISTS.mkdir(parents=True, exist_ok=True)
    keys = ["name", "ra", "dec", "role", "pair", "designation", "splices_name", "class_1", "stype_ml", "w1", "w2",
            "w2var_class", "w2varamp", "w1var_class", "w1varamp", "av", "mc", "mc_los", "fluxratioi2", "sel_type"]
    with open(LISTS / "sample.csv", "w", newline="") as f:
        w = csv.DictWriter(f, keys)
        w.writeheader()
        for c in chosen:
            des = str(c["designation"])
            nm = c["name"] if c["role"] == "VALIDATION" else ("S" + des.replace(" ", "").replace("SPLICES", "")[:24])
            w.writerow({"name": nm.replace("+", "p").replace("-", "m").replace(".", ""), "ra": c["ra"], "dec": c["dec"],
                        "role": c["role"], "pair": c["pair"], "designation": des,
                        "splices_name": "" if c["role"] == "VALIDATION" or val(c, "name") is None else str(c["name"]),
                        **{k: ("" if c.get(k) is None or np.ma.is_masked(c.get(k)) else c.get(k))
                           for k in keys[7:]}})
    log["n_chosen"] = {r: sum(c["role"] == r for c in chosen) for r in ("VAR", "CTRL", "BGSTAR", "VALIDATION")}
    (SEL / "sample_selection.json").write_text(json.dumps(log, indent=1, default=str))
    print(json.dumps({k: v for k, v in log.items() if k != "excluded_by_position"}, indent=1, default=str))


if __name__ == "__main__":
    main()
