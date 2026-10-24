import { describe, expect, it } from "vitest";
import { forwardFromDriving, gravityFromStill, GRAVITY } from "../calibration";
import { DisagreementWatch, lateralGFromAccel, lateralGFromYaw, MountWatch, yawRateRad } from "../lateral-g";
import { type Vec3, angleDeg, scale } from "../vector";
import { WORLD_FORWARD, WORLD_RIGHT, WORLD_UP, toPhone, wobble } from "./synthetic-kart";

const add = (a: Vec3, b: Vec3): Vec3 => [a[0] + b[0], a[1] + b[1], a[2] + b[2]];
const stillReadings = (size: number) => Array.from({ length: 120 }, (_, i) => add(toPhone(scale(WORLD_UP, GRAVITY)), wobble(i, size)));

describe("calibration (SYNTHETIC tilted phone)", () => {
  it("finds 'up' in the phone's axes from a still phone", () => {
    const result = gravityFromStill(stillReadings(0.05));
    expect(result.ok).toBe(true);
    if (result.ok) expect(angleDeg(result.direction, toPhone(WORLD_UP))).toBeLessThan(1);
  });

  it("refuses a shaking phone and too few readings", () => {
    expect(gravityFromStill(stillReadings(1.0)).ok).toBe(false);
    expect(gravityFromStill(stillReadings(0.05).slice(0, 30)).ok).toBe(false);
  });

  it("finds forward while speeding up in a straight line", () => {
    const up = toPhone(WORLD_UP);
    const pushes = Array.from({ length: 40 }, (_, i) =>
      add(toPhone(add(scale(WORLD_UP, GRAVITY), scale(WORLD_FORWARD, 2.5))), wobble(i, 0.1)));
    const result = forwardFromDriving(pushes, up);
    expect(result.ok).toBe(true);
    if (result.ok) expect(angleDeg(result.direction, toPhone(WORLD_FORWARD))).toBeLessThan(3);
  });

  it("asks for a firmer push when there was no real acceleration", () => {
    expect(forwardFromDriving(stillReadings(0.05), toPhone(WORLD_UP)).ok).toBe(false);
  });
});

describe("sideways g (SYNTHETIC 20 m circle at 15 m/s = 1.147 g)", () => {
  const up = toPhone(WORLD_UP);
  const forward = toPhone(WORLD_FORWARD);
  const yawDegPerS = (15 / 20) * (180 / Math.PI);

  it("speed × turn rate gives the right g whatever the phone's angle", () => {
    const yaw = yawRateRad(toPhone(scale(WORLD_UP, yawDegPerS)), up);
    expect(yaw).toBeCloseTo(0.75, 3);
    expect(lateralGFromYaw(15, yaw)).toBeCloseTo(1.147, 2);
  });

  it("the accelerometer check agrees, and turning the other way gives the same size", () => {
    const left = toPhone(add(scale(WORLD_UP, GRAVITY), scale(WORLD_RIGHT, -(15 * 15) / 20)));
    const right = toPhone(add(scale(WORLD_UP, GRAVITY), scale(WORLD_RIGHT, (15 * 15) / 20)));
    expect(lateralGFromAccel(left, up, forward)).toBeCloseTo(1.147, 2);
    expect(lateralGFromAccel(right, up, forward)).toBeCloseTo(1.147, 2);
  });

  it("warns once when the two disagree for 3 s while moving, never when slow", () => {
    const watch = new DisagreementWatch();
    expect(watch.update(0, 10, 1.2, 0.5)).toBe(false);
    expect(watch.update(2900, 10, 1.2, 0.5)).toBe(false);
    expect(watch.update(3100, 10, 1.2, 0.5)).toBe(true);
    expect(watch.update(4000, 10, 1.2, 0.5)).toBe(false);
    const slow = new DisagreementWatch();
    slow.update(0, 2, 1.2, 0.1);
    expect(slow.update(5000, 2, 1.2, 0.1)).toBe(false);
  });
});

describe("mount watch (SYNTHETIC)", () => {
  const up = toPhone(WORLD_UP);

  it("hard cornering and braking never count as the phone moving", () => {
    const watch = new MountWatch(up);
    const corner = toPhone(add(scale(WORLD_UP, GRAVITY), scale(WORLD_RIGHT, 14)));
    const brake = toPhone(add(scale(WORLD_UP, GRAVITY), scale(WORLD_FORWARD, -9)));
    for (let t = 0; t < 10_000; t += 20) expect(watch.update(t, t % 40 ? corner : brake)).toBe(false);
  });

  it("a phone that has tipped 35° in its mount is reported after 2 s", () => {
    const watch = new MountWatch(up);
    const tipped = toPhone([0, Math.sin((35 * Math.PI) / 180) * GRAVITY, Math.cos((35 * Math.PI) / 180) * GRAVITY]);
    let warned = 0;
    for (let t = 0; t <= 4000; t += 20) if (watch.update(t, tipped)) warned += 1;
    expect(warned).toBe(1);
    expect(watch.moved).toBe(true);
  });
});
