// Under the flipbook: the frames as a GIF (flipbook.gif, backend/app/gif.py) and links to the original SPHEREx
// files of every visit at NASA IRSA (originals.json, backend/app/originals.py).
import { loadExtra, remember } from "./frames.js";

const $ = (id) => document.getElementById(id);
const RELEASE = (r) => String(r || "").replace("spherex_", "").toUpperCase();

/** [{ heading, exposures: [{ text, file_url, datalink_url }] }] per visit. */
export function originalsList(originals) {
  return originals.frames.map((f, i) => ({
    heading: `Visit ${i + 1} · ${f.date_iso.slice(0, 10)} · ${f.exposures.length} exposure${f.exposures.length === 1 ? "" : "s"}`,
    exposures: f.exposures.map((e) => ({
      text: `${e.obs_id} D${originals.band}${e.release ? ` · ${RELEASE(e.release)}` : ""}`,
      file_url: e.file_url || null, datalink_url: e.datalink_url || null,
    })),
  }));
}

export function originalsNote(originals) {
  const n = originals.frames.reduce((s, f) => s + f.exposures.length, 0);
  const missing = originals.missing.length ? ` ${originals.missing.length} could not be found at IRSA.` : "";
  return `The ${n} exposures added up in these frames. "FITS" is the full Level 2 file (tens of MB: image, ` +
    `flags, variance, zodiacal light, PSF); "DataLink" is IRSA's list of all its products.${missing}`;
}

function link(href, text) {
  const a = document.createElement("a");
  a.href = href;
  a.textContent = text;
  a.target = "_blank";
  a.rel = "noopener";
  return a;
}

export function createFiles() {
  const el = { box: $("flip-files"), gif: $("flip-gif"), details: $("flip-originals"),
    note: $("flip-originals-note"), list: $("flip-originals-list") };
  let version = 0;

  function gifExists(url) {
    return remember(fetch, `head:${url}`, async () => {
      try {
        return (await fetch(url, { method: "HEAD", cache: "no-cache" })).ok;
      } catch {
        return false;
      }
    });
  }

  /** Frames were shown ({ manifest, base }) or cleared (null). */
  async function show(loaded) {
    const v = ++version;
    el.box.hidden = true;
    el.gif.hidden = true;
    el.details.hidden = true;
    if (!loaded) return;
    const gifUrl = `${loaded.base}/flipbook.gif`;
    const [hasGif, originals] = await Promise.all([gifExists(gifUrl), loadExtra(loaded.base, "originals.json").catch(() => null)]);
    if (v !== version) return;
    if (hasGif) {
      el.gif.href = gifUrl;
      el.gif.download = `spherex_${loaded.manifest.target}_d${loaded.manifest.band}.gif`;
      el.gif.hidden = false;
    }
    if (originals) {
      el.note.textContent = originalsNote(originals);
      el.list.replaceChildren(...originalsList(originals).map((visit) => {
        const h = document.createElement("p");
        h.className = "files-visit";
        h.textContent = visit.heading;
        const ul = document.createElement("ul");
        ul.className = "files-list";
        ul.append(...visit.exposures.map((e) => {
          const li = document.createElement("li");
          li.append(e.text);
          if (e.file_url) li.append(" · ", link(e.file_url, "FITS"));
          if (e.datalink_url) li.append(" · ", link(e.datalink_url, "DataLink"));
          return li;
        }));
        const box = document.createElement("div");
        box.append(h, ul);
        return box;
      }));
      el.details.hidden = false;
    }
    el.box.hidden = !hasGif && !originals;
  }

  return { show };
}
