// Bundle spot vetting data for download — not a discovery claim or MPC submission.
import { targetBase } from "./spectrum.js";

function frameFacts(manifest, epochId) {
  const f = manifest.frames.find((x) => x.epoch_id === epochId);
  if (!f) return null;
  return {
    epoch_id: epochId,
    date_iso: f.date_iso,
    mjd: f.mjd ?? null,
    band: f.band,
    n_images: f.n_images,
  };
}

/** Plain object for JSON download; every field comes from files we already serve. */
export function buildSpotEvidence({
  manifest,
  base,
  pair,
  spotIndex,
  jpl = null,
  spectrum = null,
  originals = null,
  diffPair = null,
}) {
  const spot = pair.spots[spotIndex];
  const fa = frameFacts(manifest, pair.a);
  const fb = frameFacts(manifest, pair.b);
  const spectrumSummary = spectrum
    ? {
        label: spectrum.label,
        detectors: spectrum.detectors.map((d) => ({
          band: d.band,
          band_range_um: d.band_range_um,
          method: d.method,
          reason: d.reason ?? null,
        })),
        visits: spectrum.visits.length,
        n_points: spectrum.visits.reduce((n, v) => n + v.n_points, 0),
      }
    : null;
  const provenance = originals
    ? {
        note: originals.note ?? null,
        visits: (originals.visits || []).map((v) => ({
          visit: v.visit,
          exposures: (v.exposures || []).map((e) => ({
            obs_id: e.obs_id,
            datalink_url: e.datalink_url,
            file_url: e.file_url,
          })),
        })),
      }
    : null;
  return {
    format: "spherex-blink-spot-evidence/1",
    disclaimer: "Spot evidence for vetting only. No match with a known object does not make this a new discovery.",
    target: {
      key: manifest.target ?? null,
      ra: manifest.ra,
      dec: manifest.dec,
      position_epoch: manifest.position_epoch ?? null,
      pixel_arcsec: manifest.pixel_arcsec,
    },
    detector_folder: base,
    target_folder: targetBase(base),
    visit_pair: {
      a: fa,
      b: fb,
      days_between: diffPair?.days ?? (fa && fb && fa.mjd && fb.mjd ? Math.abs(fb.mjd - fa.mjd) : null),
    },
    difference_map: diffPair
      ? {
          max_sigma: diffPair.max_sigma,
          min_sigma: diffPair.min_sigma,
          scatter_sigma: diffPair.scatter_sigma,
        }
      : null,
    spot: {
      index: spotIndex + 1,
      ...spot,
      what_else: spot.what_else,
      confirm: spot.confirm,
    },
    jpl_known_objects: jpl,
    spectrum: spectrumSummary,
    provenance,
    exported_at: new Date().toISOString(),
  };
}

export function downloadSpotEvidence(bundle, filename) {
  const blob = new Blob([JSON.stringify(bundle, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
