// Star name -> position and proper motion, straight from SIMBAD's TAP service in the browser.
// The Harvard mirror is tried first because the main CDS server did not answer on 29 and 31 Oct;
// whichever server answers is tried first next time. When /api/resolve exists (Day 3) this can
// call the backend instead.

const SERVERS = [
  "https://simbad.harvard.edu/simbad/sim-tap/sync",
  "https://simbad.cds.unistra.fr/simbad/sim-tap/sync",
];
const TIMEOUT_MS = 12000;
let order = [...SERVERS];

export class NameNotFound extends Error {}
export class ResolverUnavailable extends Error {}

function adqlString(text) {
  return "'" + text.replace(/'/g, "''") + "'";
}

async function ask(server, name) {
  const query =
    "SELECT b.main_id, b.ra, b.dec, b.pmra, b.pmdec FROM basic AS b " +
    "JOIN ident AS i ON i.oidref = b.oid WHERE i.id = " + adqlString(name);
  const url = `${server}?request=doQuery&lang=adql&format=json&query=${encodeURIComponent(query)}`;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);
  try {
    const response = await fetch(url, { signal: controller.signal });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return await response.json();
  } finally {
    clearTimeout(timer);
  }
}

/** -> { name, simbadId, ra, dec, pmra, pmdec, epoch: 2000, server } */
export async function resolveName(name) {
  const clean = name.trim();
  if (!clean) throw new NameNotFound("Empty name");
  const errors = [];
  for (const server of [...order]) {
    let result;
    try {
      result = await ask(server, clean);
    } catch (err) {
      errors.push(`${new URL(server).host}: ${err.name === "AbortError" ? "no answer" : err.message}`);
      continue;
    }
    order = [server, ...order.filter((s) => s !== server)];
    const row = result.data && result.data[0];
    if (!row) throw new NameNotFound(`"${clean}" was not found in SIMBAD. Check the spelling, or type RA and Dec.`);
    const [simbadId, ra, dec, pmra, pmdec] = row;
    return {
      name: clean,
      simbadId: String(simbadId).replace(/\s+/g, " ").trim(),
      ra,
      dec,
      pmra: pmra ?? null,
      pmdec: pmdec ?? null,
      epoch: 2000.0,
      server: new URL(server).host,
    };
  }
  throw new ResolverUnavailable(
    "Name lookup (SIMBAD) is not answering right now. Type RA and Dec, or use a target button. (" +
      errors.join("; ") + ")"
  );
}
