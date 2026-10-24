/**
 * Trackside phone sensors — record the raw sensor data of a run, to save as a test file.
 *
 * Phase 2.1 asks for real phone recordings as test data. The phone page keeps the raw motion readings
 * (about 20 per second) and every GPS fix of the run, and the driver can save them as one JSON file.
 * Nothing here is sent to the server.
 */

import type { Vec3 } from "./vector";

export const RECORDING_FORMAT = "trackside-phone-recording";
export const RECORDING_VERSION = 1;
/** About 10 minutes at 20 readings per second; older readings are dropped first. */
export const MAX_MOTION_SAMPLES = 12_000;
const MOTION_EVERY_MS = 50;

export interface MotionSample {
  t: number;
  accel: Vec3;
  rotation: Vec3;
}

export interface GpsSample {
  t: number;
  lat: number;
  lng: number;
  speed_ms: number | null;
  accuracy_m: number | null;
}

export class SensorRecording {
  motion: MotionSample[] = [];
  gps: GpsSample[] = [];
  private lastMotionAt = -Infinity;

  /** Keep a motion reading if 50 ms have passed since the last kept one. */
  addMotion(sample: MotionSample): void {
    if (sample.t - this.lastMotionAt < MOTION_EVERY_MS) return;
    this.lastMotionAt = sample.t;
    this.motion.push(sample);
    if (this.motion.length > MAX_MOTION_SAMPLES) this.motion.shift();
  }

  /** Keep every GPS fix. */
  addGps(sample: GpsSample): void {
    this.gps.push(sample);
  }

  /** The recording as a JSON text with its format, version and the calibration used. */
  toJson(calibration: { gravity?: Vec3; forward?: Vec3 }, note: string): string {
    return JSON.stringify({
      format: RECORDING_FORMAT, version: RECORDING_VERSION, synthetic: false, note,
      calibration, motion: this.motion, gps: this.gps,
    });
  }
}
