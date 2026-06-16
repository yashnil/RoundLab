/**
 * Pure audio-level math, separated from the Web Audio plumbing so it can be
 * unit-tested. Input is time-domain byte data from an AnalyserNode
 * (`getByteTimeDomainData`), centered on 128.
 */

/** RMS amplitude of a time-domain buffer, normalized to 0..1. */
export function computeRmsLevel(timeDomain: Uint8Array | number[]): number {
  if (timeDomain.length === 0) return 0;
  let sumSquares = 0;
  for (let i = 0; i < timeDomain.length; i++) {
    const centered = (timeDomain[i] - 128) / 128; // -1..1
    sumSquares += centered * centered;
  }
  const rms = Math.sqrt(sumSquares / timeDomain.length);
  return Math.min(1, rms);
}

/**
 * Smooth a level toward a target with simple exponential easing, so the meter
 * doesn't jitter frame-to-frame. `factor` in 0..1 (higher = snappier).
 */
export function smoothLevel(previous: number, target: number, factor = 0.3): number {
  const f = Math.min(1, Math.max(0, factor));
  return previous + (target - previous) * f;
}

/** Map a 0..1 level to a small number of meter bars (for an a11y-friendly meter). */
export function levelToBars(level: number, bars: number): number {
  const clamped = Math.min(1, Math.max(0, level));
  return Math.round(clamped * bars);
}
