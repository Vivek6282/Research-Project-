import { describe, expect, it } from "vitest";
import { GRAVITY } from "../../../../lib/phone-sensors/calibration";
import { WORLD_FORWARD, WORLD_RIGHT, WORLD_UP, toPhone, wobble } from "../../../../lib/phone-sensors/__tests__/synthetic-kart";
import type { QueuedReading } from "../../../../lib/phone-sensors/upload-queue";
import { type Vec3, scale } from "../../../../lib/phone-sensors/vector";
import { PhoneRun, STILL_COLLECT_MS } from "../phone-run";

// SYNTHETIC run: a tilted phone, calibrated, then a 20 m circle at 15 m/s (1.147 g)
const add = (a: Vec3, b: Vec3): Vec3 => [a[0] + b[0], a[1] + b[1], a[2] + b[2]];
const yawDeg = (15 / 20) * (180 / Math.PI);

function makeRun() {
  const sent: QueuedReading[][] = [];
  const saved: unknown[] = [];
  const run = new PhoneRun(null, {
    send: async (batch) => (sent.push(batch), { kind: "ok" }),
    saveCalibration: async (body) => void saved.push(body),
    wallClock: () => new Date("2026-10-24T10:00:00Z"),
  });
  return { run, sent, saved };
}

function calibrate(run: PhoneRun) {
  run.beginStill(0);
  for (let t = 0; t <= STILL_COLLECT_MS; t += 16) {
    run.onMotion({ t, accel: add(toPhone(scale(WORLD_UP, GRAVITY)), wobble(t, 0.04)), rotation: [0, 0, 0] });
  }
  run.tick(STILL_COLLECT_MS + 1);
  for (let t = 3000; t < 4000; t += 16) {
    run.onMotion({ t, accel: toPhone(add(scale(WORLD_UP, GRAVITY), scale(WORLD_FORWARD, 2.5))), rotation: [0, 0, 0] });
  }
}

describe("PhoneRun (SYNTHETIC sensors)", () => {
  it("goes still → drive → running and saves both directions", () => {
    const { run, saved } = makeRun();
    calibrate(run);
    expect(run.snapshot().step).toBe("drive");
    run.tick(4000);
    expect(run.snapshot().step).toBe("running");
    expect(saved).toHaveLength(2);
  });

  it("sends 1.15 g in the circle with the GPS position, numbered in order", async () => {
    const { run, sent } = makeRun();
    calibrate(run);
    run.tick(4000);
    run.onFix({ t: 4000, lat: 10, lng: 76, speedMs: 15, accuracyM: 3.5 });
    for (let t = 4000; t < 5000; t += 16) {
      run.onMotion({ t, accel: toPhone(add(scale(WORLD_UP, GRAVITY), scale(WORLD_RIGHT, 11.25))), rotation: toPhone(scale(WORLD_UP, yawDeg)) });
      if (t % 100 < 16) run.tick(t);
    }
    await run.queue.flush(6000);
    const readings = sent.flat();
    expect(readings.length).toBeGreaterThan(5);
    // The turn rate is averaged over the last 6 motion readings (~0.1 s), so the first readings still mix in
    // the straight-line calibration; from the third reading on the value is steady
    expect(readings.slice(2).every((r) => Math.abs(r.lateral_g - 1.147) < 0.02)).toBe(true);
    expect(readings[0]).toMatchObject({ speed_kmh: 54, gps_lat: 10, gps_lng: 76, gps_accuracy_m: 3.5 });
    expect(readings.map((r) => r.sequence)).toEqual(readings.map((_, i) => i));
    expect(run.snapshot().warnings).toEqual([]);
  });

  it("refuses to calibrate a shaking phone and sends nothing before 'up' is known", () => {
    const { run } = makeRun();
    run.beginStill(0);
    for (let t = 0; t <= STILL_COLLECT_MS; t += 16) run.onMotion({ t, accel: add(toPhone(scale(WORLD_UP, GRAVITY)), wobble(t, 1.5)), rotation: [0, 0, 0] });
    run.onFix({ t: 100, lat: 10, lng: 76, speedMs: 5, accuracyM: 4 });
    run.tick(STILL_COLLECT_MS + 1);
    expect(run.snapshot()).toMatchObject({ step: "still", queued: 0 });
    expect(run.snapshot().message).toMatch(/moved/);
  });

  it("stops sending when GPS fixes stop for 5 s", () => {
    const { run } = makeRun();
    calibrate(run);
    run.onFix({ t: 4000, lat: 10, lng: 76, speedMs: 10, accuracyM: 5 });
    run.tick(4100);
    run.tick(9100);
    expect(run.snapshot().queued).toBe(1);
  });

  it("warns and saves the flag when the accelerometer disagrees for 3 s", () => {
    const { run, saved } = makeRun();
    calibrate(run);
    run.tick(4000);
    run.onFix({ t: 4000, lat: 10, lng: 76, speedMs: 15, accuracyM: 3 });
    for (let t = 4000; t < 8000; t += 16) {
      // the gyro says a hard corner, the accelerometer says straight: the phone is loose
      run.onMotion({ t, accel: toPhone(scale(WORLD_UP, GRAVITY)), rotation: toPhone(scale(WORLD_UP, yawDeg)) });
      if (t % 100 < 16) run.onFix({ t, lat: 10, lng: 76, speedMs: 15, accuracyM: 3 }), run.tick(t);
    }
    expect(run.snapshot().warnings.join(" ")).toMatch(/disagree/);
    expect(saved).toContainEqual({ flags: ["sensor_disagreement"] });
  });
});
