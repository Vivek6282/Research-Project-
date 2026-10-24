/**
 * Trackside phone sensors — sideways g, two ways.
 *
 * Main: speed × turn rate ÷ 9.81 (true for steady cornering). The turn rate is the gyroscope's rotation
 * about the "up" direction found at calibration, so the phone can be mounted at any angle.
 * Check: the accelerometer's sideways part (needs the forward direction). If the two disagree for a few
 * seconds while moving, the phone has probably shifted in its mount.
 */

import { GRAVITY } from "./calibration";
import { type Vec3, angleDeg, cross, dot, norm, normalize } from "./vector";

const DEG_TO_RAD = Math.PI / 180;
export const DISAGREE_G = 0.35;
export const DISAGREE_MS = 3000;
export const DISAGREE_MIN_SPEED_MS = 5;
export const MOUNT_MOVED_DEG = 20;
export const MOUNT_MOVED_MS = 2000;

/** Turn rate about "up" in radians per second, from the gyroscope's degrees per second (phone axes). */
export function yawRateRad(rotationDegPerS: Vec3, up: Vec3): number {
  return dot(rotationDegPerS, up) * DEG_TO_RAD;
}

/** Sideways g from speed (m/s) and turn rate (rad/s), always 0 or more. */
export function lateralGFromYaw(speedMs: number, yawRad: number): number {
  return Math.abs(speedMs * yawRad) / GRAVITY;
}

/** Sideways g from the accelerometer: the part along up × forward. */
export function lateralGFromAccel(acceleration: Vec3, up: Vec3, forward: Vec3): number {
  return Math.abs(dot(acceleration, normalize(cross(up, forward)))) / GRAVITY;
}

/** Watches the two estimates; `disagreed` becomes true once they differ for DISAGREE_MS while moving. */
export class DisagreementWatch {
  private since: number | null = null;
  disagreed = false;

  /** Feed one moment; returns true only at the moment the warning starts. */
  update(nowMs: number, speedMs: number, fromYaw: number, fromAccel: number): boolean {
    const apart = speedMs >= DISAGREE_MIN_SPEED_MS && Math.abs(fromYaw - fromAccel) > DISAGREE_G;
    if (!apart) {
      this.since = null;
      return false;
    }
    this.since ??= nowMs;
    if (!this.disagreed && nowMs - this.since >= DISAGREE_MS) {
      this.disagreed = true;
      return true;
    }
    return false;
  }
}

/** Watches gravity's direction against the calibrated one; hard cornering and braking are ignored. */
export class MountWatch {
  private smoothed: Vec3 | null = null;
  private since: number | null = null;
  moved = false;

  constructor(private readonly up: Vec3) {}

  /** Feed one accelerometer reading; returns true only at the moment the warning starts. */
  update(nowMs: number, acceleration: Vec3): boolean {
    // Only readings within 0.5 m/s² of 1 g show gravity alone. Any kart push that passes this filter tilts the
    // reading by under 19°, below MOUNT_MOVED_DEG, so speeding up, braking and cornering never count as a move.
    if (Math.abs(norm(acceleration) - GRAVITY) > 0.5) return false;
    this.smoothed = this.smoothed
      ? [0, 1, 2].map((i) => this.smoothed![i] * 0.95 + acceleration[i] * 0.05) as Vec3
      : acceleration;
    if (angleDeg(this.smoothed, this.up) <= MOUNT_MOVED_DEG) {
      this.since = null;
      return false;
    }
    this.since ??= nowMs;
    if (!this.moved && nowMs - this.since >= MOUNT_MOVED_MS) {
      this.moved = true;
      return true;
    }
    return false;
  }
}
