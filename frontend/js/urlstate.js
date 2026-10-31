// The view lives in the web address (?ra=&dec=&fov=&det=), so any view can be shared or embedded.

export const FOV_DEFAULT = 3;   // arcminutes
export const FOV_MIN = 1;
export const FOV_MAX = 15;
export const DET_DEFAULT = 2;

export const DETECTORS = {
  1: "0.75–1.09 µm",
  2: "1.10–1.62 µm",
  3: "1.63–2.41 µm",
  4: "2.42–3.82 µm",
  5: "3.83–4.41 µm",
  6: "4.42–5.00 µm",
};

/** "?ra=..&dec=.." -> { ra, dec, fov, det, problems } ; ra/dec are null when missing or invalid. */
export function readUrlState(search) {
  const params = new URLSearchParams(search);
  const problems = [];
  let ra = null;
  let dec = null;
  if (params.has("ra") || params.has("dec")) {
    const r = Number(params.get("ra"));
    const d = Number(params.get("dec"));
    if (params.get("ra") !== "" && params.get("dec") !== "" && r >= 0 && r < 360 && d >= -90 && d <= 90) {
      ra = r;
      dec = d;
    } else {
      problems.push("The link has an invalid position (ra must be 0–360, dec −90 to +90).");
    }
  }
  let fov = Number(params.get("fov") ?? FOV_DEFAULT);
  if (!(fov >= FOV_MIN && fov <= FOV_MAX)) {
    if (params.has("fov")) problems.push(`Field of view must be ${FOV_MIN}–${FOV_MAX} arcmin; using ${FOV_DEFAULT}.`);
    fov = FOV_DEFAULT;
  }
  let det = Number(params.get("det") ?? DET_DEFAULT);
  if (!DETECTORS[det]) {
    if (params.has("det")) problems.push(`Detector must be 1–6; using D${DET_DEFAULT}.`);
    det = DET_DEFAULT;
  }
  return { ra, dec, fov, det, problems };
}

/** { ra, dec, fov, det } -> "?ra=269.446269&dec=4.768204&fov=3&det=2" */
export function buildUrlState({ ra, dec, fov, det }) {
  const params = new URLSearchParams();
  params.set("ra", ra.toFixed(6));
  params.set("dec", dec.toFixed(6));
  params.set("fov", String(fov));
  params.set("det", String(det));
  return "?" + params.toString();
}
