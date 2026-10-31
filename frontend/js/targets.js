// The 5 official challenge targets. Positions (J2000) and proper motions (mas/yr) are SIMBAD's
// values from the Day 1 report (notes/DAY1_REPORT.md, 31 Oct 2026); the page moves them to
// VIEW_EPOCH, so the buttons work even when SIMBAD is down.

export const TARGETS = [
  {
    key: "barnard",
    label: "Barnard's Star",
    kind: "Moving star",
    ra: 269.452077, dec: 4.693365, pmra: -801.551, pmdec: 10362.394,
    lookFor: "The fastest-moving star in the sky (10.4″ per year). Watch it walk about 1.7 pixels.",
    detector: 2,
  },
  {
    key: "eps_ind_b",
    label: "Epsilon Indi B",
    kind: "Brown-dwarf pair",
    ra: 331.044147, dec: -56.782844, pmra: 3981.977, pmdec: -2466.832,
    lookFor: "Two brown dwarfs moving together (4.7″ per year). A small shift of about 1 pixel.",
    detector: 2,
  },
  {
    key: "wise0855",
    label: "WISE 0855",
    kind: "Coldest brown dwarf",
    ra: 133.818908, dec: -7.247048, pmra: -8123.7, pmdec: 673.2,
    lookFor: "Invisible at short wavelengths, it appears only at 4–5 µm (detectors D5–D6).",
    detector: 6,
  },
  {
    key: "rw_aur",
    label: "RW Aurigae",
    kind: "Variable young star",
    ra: 76.956526, dec: 30.401438, pmra: 7.23, pmdec: -20.33,
    lookFor: "A young star that dims and brightens between visits.",
    detector: 2,
  },
  {
    key: "r_dra",
    label: "R Draconis",
    kind: "Pulsating giant",
    ra: 248.167611, dec: 66.754979, pmra: -20.643, pmdec: 6.149,
    lookFor: "A Mira variable: its brightness rises and falls over about 245 days.",
    detector: 2,
  },
];
