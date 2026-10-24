/**
 * Trackside phone sensors — calibration: which way is down and which way is forward in the phone's own axes.
 *
 * Step 1 "hold still": the average acceleration of a still phone is gravity (its direction is "up" for the
 * readings; the sign some phones report differently does not matter). The phone must really be still.
 * Step 2 "drive straight": while the kart speeds up in a straight line, the part of the acceleration that is
 * level (at right angles to gravity) points forward.
 */

import { type Vec3, dot, mean, norm, normalize, scale, sub } from "./vector";

export const GRAVITY = 9.81;
/** Step 1 needs at least this many readings (about 2 s at 60 per second). */
export const STILL_MIN_SAMPLES = 90;
/** Largest wobble allowed while "still" (standard deviation per axis, m/s²). */
export const STILL_MAX_SPREAD = 0.35;
/** Step 2 counts only readings with at least this much level acceleration (m/s²). */
export const FORWARD_MIN_ACCEL = 0.8;
export const FORWARD_MIN_SAMPLES = 20;

export type CalibrationResult = { ok: true; direction: Vec3 } | { ok: false; reason: string };

/** Standard deviation of one axis. */
function spread(values: number[]): number {
  const average = values.reduce((a, b) => a + b, 0) / values.length;
  return Math.sqrt(values.reduce((a, b) => a + (b - average) ** 2, 0) / values.length);
}

/** Gravity from readings taken while the phone is held still in its mount. */
export function gravityFromStill(samples: Vec3[]): CalibrationResult {
  if (samples.length < STILL_MIN_SAMPLES) return { ok: false, reason: "Hold still a little longer." };
  if ([0, 1, 2].some((axis) => spread(samples.map((s) => s[axis])) > STILL_MAX_SPREAD)) {
    return { ok: false, reason: "The phone moved. Fix it firmly in the mount and keep the kart still." };
  }
  const gravity = mean(samples);
  if (Math.abs(norm(gravity) - GRAVITY) > 1.5) return { ok: false, reason: "The motion sensor gave odd values. Try again." };
  return { ok: true, direction: normalize(gravity) };
}

/** The level (gravity-free) part of one acceleration reading. */
export function levelPart(acceleration: Vec3, up: Vec3): Vec3 {
  return sub(acceleration, scale(up, dot(acceleration, up)));
}

/** Forward from readings taken while speeding up in a straight line. */
export function forwardFromDriving(samples: Vec3[], up: Vec3): CalibrationResult {
  const pushes = samples.map((s) => levelPart(s, up)).filter((level) => norm(level) >= FORWARD_MIN_ACCEL);
  if (pushes.length < FORWARD_MIN_SAMPLES) return { ok: false, reason: "Speed up firmly in a straight line." };
  const forward = mean(pushes);
  if (norm(forward) < FORWARD_MIN_ACCEL / 2) return { ok: false, reason: "Drive straight, without turning or braking." };
  return { ok: true, direction: normalize(forward) };
}
