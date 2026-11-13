// The 5 official challenge targets. Positions (J2000) and proper motions (mas/yr) are SIMBAD's
// values from the Day 1 report (notes/DAY1_REPORT.md, 31 Oct 2026); the page moves them to
// VIEW_EPOCH, so the buttons work even when SIMBAD is down.
//
// `detectors` rates every detector D1–D6 for what `lookFor` asks. Only results written in notes/
// (DAY2–DAY6_FINDINGS) earn "recommended" or "not"; anything unchecked is "try".

export const RATINGS = {
  recommended: "Recommended",
  try: "Try",
  not: "Not recommended",
};

const NOT_PREPARED = "Not prepared yet; not checked.";

export const TARGETS = [
  {
    key: "barnard",
    label: "Barnard's Star",
    kind: "Moving star",
    timescale: "years",
    timescaleLabel: "Years (multi-pass)",
    ra: 269.452077, dec: 4.693365, pmra: -801.551, pmdec: 10362.394,
    lookFor: "The fastest-moving star in the sky (10.4″ per year). Watch it walk about 1.7 pixels.",
    detector: 2,
    detectors: {
      1: { rating: "try", why: NOT_PREPARED },
      2: { rating: "recommended", why: "Motion checked: the saturated centre moved 1.59 px, Gaia says 1.67 px." },
      3: { rating: "try", why: NOT_PREPARED },
      4: { rating: "try", why: NOT_PREPARED },
      5: { rating: "try", why: NOT_PREPARED },
      6: { rating: "try", why: NOT_PREPARED },
    },
  },
  {
    key: "eps_ind_b",
    label: "Epsilon Indi B",
    kind: "Brown-dwarf pair",
    timescale: "years",
    timescaleLabel: "Years (multi-pass)",
    ra: 331.044147, dec: -56.782844, pmra: 3981.977, pmdec: -2466.832,
    lookFor: "Two brown dwarfs moving together (4.7″ per year). A small shift of about 1 pixel.",
    detector: 2,
    detectors: {
      1: { rating: "not", why: "Very faint at 0.75–1.09 µm; the Gaia motion check disagrees here (0.96 px measured, 0.75 px expected)." },
      2: { rating: "recommended", why: "Motion checked: 0.99 px measured, Gaia says 1.09 px." },
      3: { rating: "try", why: "Prepared and in the spectrum; motion not checked in this detector." },
      4: { rating: "try", why: "Prepared and in the spectrum; motion not checked in this detector." },
      5: { rating: "try", why: "Prepared and in the spectrum; motion not checked in this detector." },
      6: { rating: "try", why: "Prepared and in the spectrum; motion not checked in this detector." },
    },
  },
  {
    key: "wise0855",
    label: "WISE 0855",
    kind: "Coldest brown dwarf",
    timescale: "years",
    timescaleLabel: "Years (multi-pass)",
    ra: 133.818908, dec: -7.247048, pmra: -8123.7, pmdec: 673.2,
    lookFor: "Invisible at short wavelengths, it appears only at 4–5 µm (detectors D5–D6).",
    detector: 6,
    detectors: {
      1: { rating: "not", why: "Too faint at these wavelengths; it shows only at 4–5 µm." },
      2: { rating: "not", why: "Too faint here; the dot near the circle is a Gaia star (G 16.3), not WISE 0855." },
      3: { rating: "not", why: "Too faint at these wavelengths; it shows only at 4–5 µm." },
      4: { rating: "not", why: "Too faint at these wavelengths; it shows only at 4–5 µm." },
      5: { rating: "try", why: "Prepared; it gets brighter towards 5 µm, so expect a weaker signal than in D6." },
      6: { rating: "recommended", why: "Seen in the add-ups (11–13σ) and moves like WISE 0855 (0.58 px measured, 0.72 px expected)." },
    },
  },
  {
    key: "rw_aur",
    label: "RW Aurigae",
    kind: "Variable young star",
    timescale: "months",
    timescaleLabel: "Months (survey passes)",
    ra: 76.956526, dec: 30.401438, pmra: 7.23, pmdec: -20.33,
    lookFor: "A young star that dims and brightens between visits.",
    detector: 2,
    detectors: {
      1: { rating: "try", why: "Prepared; the light curve has points, but no change checked yet." },
      2: { rating: "recommended", why: "Light curve: 24% fainter in Sep 2025 at the same wavelength." },
      3: { rating: "try", why: "Prepared; the light curve has points, but no change checked yet." },
      4: { rating: "not", why: "Centre saturated (to 6.2 px): no light curve." },
      5: { rating: "recommended", why: "Fainter in Sep 2026 than in Mar 2026 at the same wavelength (ratio 0.63)." },
      6: { rating: "recommended", why: "Fainter in Sep 2026 than in Mar 2026 at the same wavelength (ratio 0.77)." },
    },
  },
  {
    key: "r_dra",
    label: "R Draconis",
    kind: "Pulsating giant",
    timescale: "months",
    timescaleLabel: "Months (survey passes)",
    ra: 248.167611, dec: 66.754979, pmra: -20.643, pmdec: 6.149,
    lookFor: "A Mira variable: its brightness rises and falls over about 245 days.",
    detector: 2,
    detectors: {
      1: { rating: "try", why: NOT_PREPARED },
      2: { rating: "try", why: "The only prepared detector. Centre saturated (to 6.2 px): pictures only, no light curve." },
      3: { rating: "try", why: NOT_PREPARED },
      4: { rating: "try", why: NOT_PREPARED },
      5: { rating: "try", why: NOT_PREPARED },
      6: { rating: "try", why: NOT_PREPARED },
    },
  },
];

/** Detector numbers of one target with this rating, in order (e.g. [5, 6]). */
export function detectorsRated(target, rating) {
  return Object.entries(target.detectors)
    .filter(([, d]) => d.rating === rating)
    .map(([n]) => Number(n));
}
