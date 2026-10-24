/**
 * Trackside phone page — one phone run: calibration, then a reading every 100 ms into the upload queue.
 *
 * Kept free of React and browser APIs (they are passed in), so the whole flow can be tested with
 * SYNTHETIC sensor data. Steps: "still" (find up), "drive" (find forward; readings already flow),
 * "running". The server decides corner and lap from the GPS position.
 */

import { forwardFromDriving, gravityFromStill } from "../../../lib/phone-sensors/calibration";
import { DisagreementWatch, lateralGFromAccel, lateralGFromYaw, MountWatch, yawRateRad } from "../../../lib/phone-sensors/lateral-g";
import { SensorRecording } from "../../../lib/phone-sensors/recording";
import { TrackFollower, type LatLng } from "../../../lib/phone-sensors/track-follower";
import { UploadQueue, type QueuedReading, type SendResult } from "../../../lib/phone-sensors/upload-queue";
import type { Vec3 } from "../../../lib/phone-sensors/vector";
import type { GpsFix, MotionReading } from "./browser-sensors";

export type Step = "still" | "drive" | "running";
export const STILL_COLLECT_MS = 2500;
export const DRIVE_WINDOW_MS = 5000;
export const STALE_GPS_MS = 5000;
const YAW_AVERAGE_OF = 6;
const MAX_G = 10;

export interface RunDeps {
  send: (batch: QueuedReading[]) => Promise<SendResult>;
  saveCalibration: (body: { gravity?: Vec3; forward?: Vec3; flags?: string[] }) => Promise<void>;
  wallClock: () => Date;
}

export interface RunSnapshot {
  step: Step;
  collecting: boolean;
  message: string | null;
  warnings: string[];
  hasFix: boolean;
  lateralG: number | null;
  speedKmh: number | null;
  accuracyM: number | null;
  queued: number;
  sent: number;
  dropped: number;
  rejected: number;
  stoppedMessage: string | null;
}

export class PhoneRun {
  readonly recording = new SensorRecording();
  readonly queue: UploadQueue;
  private readonly follower: TrackFollower | null;
  private step: Step = "still";
  private message: string | null = null;
  private warnings: string[] = [];
  private up: Vec3 | null = null;
  private forward: Vec3 | null = null;
  private collectUntil: number | null = null;
  private stillReadings: Vec3[] = [];
  private driveReadings: { t: number; accel: Vec3 }[] = [];
  private recentYaw: number[] = [];
  private lastAccel: Vec3 | null = null;
  private lastFix: (GpsFix & { speed: number }) | null = null;
  private mountWatch: MountWatch | null = null;
  private readonly disagreement = new DisagreementWatch();
  private lastG: number | null = null;

  constructor(outline: LatLng[] | null, private readonly deps: RunDeps) {
    this.queue = new UploadQueue(deps.send);
    this.follower = outline ? new TrackFollower(outline) : null;
  }

  /** One motion reading from the phone. */
  onMotion(reading: MotionReading): void {
    this.recording.addMotion(reading);
    this.lastAccel = reading.accel;
    if (this.collectUntil !== null) this.stillReadings.push(reading.accel);
    if (!this.up) return;
    this.recentYaw.push(yawRateRad(reading.rotation, this.up));
    if (this.recentYaw.length > YAW_AVERAGE_OF) this.recentYaw.shift();
    if (this.step === "drive") {
      this.driveReadings.push({ t: reading.t, accel: reading.accel });
      this.driveReadings = this.driveReadings.filter((r) => reading.t - r.t <= DRIVE_WINDOW_MS);
    }
    if (this.mountWatch?.update(reading.t, reading.accel)) {
      this.warn("mount_moved", "The phone moved in its mount. Stop, fix it firmly and calibrate again.");
    }
  }

  /** One GPS fix; when the phone gives no speed it is worked out from the last fix. */
  onFix(fix: GpsFix): void {
    this.recording.addGps({ t: fix.t, lat: fix.lat, lng: fix.lng, speed_ms: fix.speedMs, accuracy_m: fix.accuracyM });
    let speed = fix.speedMs ?? 0;
    if (fix.speedMs === null && this.lastFix && fix.t > this.lastFix.t) {
      const metres = Math.hypot((fix.lat - this.lastFix.lat) * 111_320,
        (fix.lng - this.lastFix.lng) * 111_320 * Math.cos((fix.lat * Math.PI) / 180));
      speed = metres / ((fix.t - this.lastFix.t) / 1000);
    }
    this.lastFix = { ...fix, speed };
    this.follower?.onFix({ lat: fix.lat, lng: fix.lng }, speed, fix.t);
  }

  /** Step 1: start collecting 2.5 s of still readings. */
  beginStill(nowMs: number): void {
    this.stillReadings = [];
    this.collectUntil = nowMs + STILL_COLLECT_MS;
    this.message = "Hold still…";
  }

  /** Step 2 can be skipped: readings still flow, only the accelerometer cross-check is off. */
  skipForward(): void {
    if (this.step !== "drive") return;
    this.step = "running";
    this.message = "Running without the forward check.";
  }

  /** Every 100 ms: finish calibration steps and queue a reading. */
  tick(nowMs: number): void {
    if (this.collectUntil !== null && nowMs >= this.collectUntil) this.finishStill();
    if (this.step === "drive" && this.up) {
      const result = forwardFromDriving(this.driveReadings.map((r) => r.accel), this.up);
      if (result.ok) {
        this.forward = result.direction;
        this.step = "running";
        this.message = "Calibrated. Drive normally.";
        this.deps.saveCalibration({ forward: result.direction }).catch(() => undefined);
      }
    }
    if (this.up && this.lastFix && nowMs - this.lastFix.t <= STALE_GPS_MS) this.queueReading(nowMs);
  }

  /** Turn the still readings into "up", or say what went wrong. */
  private finishStill(): void {
    this.collectUntil = null;
    const result = gravityFromStill(this.stillReadings);
    if (!result.ok) {
      this.message = result.reason;
      return;
    }
    this.up = result.direction;
    this.mountWatch = new MountWatch(result.direction);
    this.step = "drive";
    this.message = "Now drive straight and speed up firmly.";
    this.deps.saveCalibration({ gravity: result.direction }).catch(() => undefined);
  }

  /** Make one reading from the latest motion and GPS and add it to the queue. */
  private queueReading(nowMs: number): void {
    const fix = this.lastFix!;
    const yaw = this.recentYaw.length ? this.recentYaw.reduce((a, b) => a + b, 0) / this.recentYaw.length : 0;
    const g = Math.min(MAX_G, lateralGFromYaw(fix.speed, yaw));
    this.lastG = g;
    if (this.forward && this.lastAccel && this.disagreement.update(nowMs, fix.speed, g, lateralGFromAccel(this.lastAccel, this.up!, this.forward))) {
      this.warn("sensor_disagreement", "The motion sensors disagree. Check that the phone is still firmly mounted.");
    }
    const position = this.follower?.positionAt(nowMs) ?? { lat: fix.lat, lng: fix.lng };
    this.queue.push({
      recorded_at: this.deps.wallClock().toISOString(),
      lateral_g: Math.round(g * 1000) / 1000,
      speed_kmh: Math.min(300, Math.round(fix.speed * 36) / 10),
      gps_lat: position.lat, gps_lng: position.lng,
      gps_accuracy_m: fix.accuracyM === null ? null : Math.min(1000, Math.round(fix.accuracyM * 10) / 10),
    });
  }

  /** Show a warning and save it on the session (once each). */
  private warn(flag: string, text: string): void {
    if (this.warnings.includes(text)) return;
    this.warnings = [...this.warnings, text];
    this.deps.saveCalibration({ flags: [flag] }).catch(() => undefined);
  }

  /** The calibration found so far (for the saved recording). */
  calibration(): { gravity?: Vec3; forward?: Vec3 } {
    return { ...(this.up ? { gravity: this.up } : {}), ...(this.forward ? { forward: this.forward } : {}) };
  }

  /** Everything the page shows. */
  snapshot(): RunSnapshot {
    return {
      step: this.step, collecting: this.collectUntil !== null, message: this.message, warnings: this.warnings,
      hasFix: this.lastFix !== null, lateralG: this.lastG, speedKmh: this.lastFix ? Math.round(this.lastFix.speed * 3.6) : null,
      accuracyM: this.lastFix?.accuracyM ?? null, queued: this.queue.queued, sent: this.queue.sent,
      dropped: this.queue.dropped, rejected: this.queue.rejected, stoppedMessage: this.queue.stoppedMessage,
    };
  }
}
