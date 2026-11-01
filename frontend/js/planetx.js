// "Could this find a Planet X?" on the About page: how a distant planet would move in SPHEREx images, from
// geometry only (Earth's orbit and Kepler's third law), and how faint a Neptune twin would be.
const PIXEL_ARCSEC = 6.15;
const RAD_ARCSEC = 206264.806;
const YEAR_DAYS = 365.25;
// Assumption, said on the page: Neptune is about V 7.8 seen from Earth at about 30 AU from the Sun (29 AU from Earth).
const NEPTUNE = { v: 7.8, r: 30.1, delta: 29.1 };
const WISE0855_MJY = 0.6;   // our own measurement, D6 4.4–5.0 µm (notes/DAY4_FINDINGS.md)

/** Largest shift caused by Earth moving along its orbit in `days` (object seen at right angles to that move). */
export function parallaxArcsec(au, days) {
  const chordAu = 2 * Math.sin((Math.PI * days) / YEAR_DAYS);
  return (chordAu / au) * RAD_ARCSEC;
}

/** The planet's own motion along a circular orbit (period au^1.5 years) in `days`. */
export function orbitArcsec(au, days) {
  return (360 * 3600 * (days / YEAR_DAYS)) / au ** 1.5;
}

/** V magnitude of a planet like Neptune (same size and albedo) at `au` from the Sun, seen at opposition. */
export function neptuneTwinV(au) {
  return NEPTUNE.v + 5 * Math.log10((au * (au - 1)) / (NEPTUNE.r * NEPTUNE.delta));
}

/** AB magnitude to mJy. */
export const abToMjy = (ab) => 3631e3 * 10 ** (-ab / 2.5);

export function planetFacts(au) {
  const px = (arcsec) => arcsec / PIXEL_ARCSEC;
  const v = neptuneTwinV(au);
  return {
    au,
    dayPx: px(parallaxArcsec(au, 1) + orbitArcsec(au, 1)),
    visitPx: px(parallaxArcsec(au, 14) + orbitArcsec(au, 14)),
    halfYearPx: px(parallaxArcsec(au, YEAR_DAYS / 2) + orbitArcsec(au, YEAR_DAYS / 2)),
    halfYearArcmin: (parallaxArcsec(au, YEAR_DAYS / 2) + orbitArcsec(au, YEAR_DAYS / 2)) / 60,
    v,
  };
}

const fmt = (x) => (x >= 100 ? x.toFixed(0) : x >= 10 ? x.toFixed(1) : x >= 0.1 ? x.toFixed(2) : x.toPrecision(2));

export function planetLines(f) {
  return [
    `In one day: up to ${fmt(f.dayPx)} SPHEREx pixels.`,
    `During one visit (about 2 weeks): up to ${fmt(f.visitPx)} pixels, so it would sit in a different place in each exposure.`,
    `Between visits half a year apart: up to ${fmt(f.halfYearPx)} pixels (${fmt(f.halfYearArcmin)}′), ` +
      (f.halfYearArcmin > 1.5 ? "far outside a 3′ flipbook square." : "inside a 3′ flipbook square."),
    `Brightness in visible light, if it were a Neptune twin: about V ${f.v.toFixed(1)} (${fmt(abToMjy(f.v))} mJy). ` +
      `For scale: WISE 0855, the faintest target we measured, is about ${WISE0855_MJY} mJy at 4.4–5 µm, and its single ` +
      "exposures mostly stay below 5σ. SPHEREx sees infrared, where Neptune-like planets are darker (methane absorbs), " +
      "so this is a rough guide only.",
  ];
}

export function initPlanetX() {
  const select = document.getElementById("px-distance");
  const list = document.getElementById("px-lines");
  if (!select || !list) return;
  const draw = () => list.replaceChildren(...planetLines(planetFacts(Number(select.value))).map((t) => {
    const li = document.createElement("li");
    li.textContent = t;
    return li;
  }));
  select.addEventListener("change", draw);
  draw();
}
