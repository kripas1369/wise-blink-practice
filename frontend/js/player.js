// Flipbook stepping rules, kept free of the page so they can be tested.

export const SPEEDS = [0.5, 1, 2, 4]; // frames per second
export const DEFAULT_SPEED = 1;
export const BLINK_SPEEDS = [1, 2, 4];
export const DEFAULT_BLINK_SPEED = 2;

/** Index after `i`, or null at the end when not looping. */
export function nextIndex(i, count, loop) {
  if (count <= 0) return null;
  if (i + 1 < count) return i + 1;
  return loop ? 0 : null;
}

/** Index before `i`, or null at the start when not looping. */
export function prevIndex(i, count, loop) {
  if (count <= 0) return null;
  if (i > 0) return i - 1;
  return loop ? count - 1 : null;
}

/** Default blink pair: the first and the last visit (largest time gap, biggest motion). */
export function defaultBlinkPair(count) {
  return count >= 2 ? [0, count - 1] : [0, 0];
}

/** Milliseconds between frames for a speed in frames per second. */
export function intervalMs(fps) {
  return Math.round(1000 / fps);
}
