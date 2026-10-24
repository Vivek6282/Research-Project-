import { describe, expect, it } from "vitest";
import { TrackFollower, type LatLng } from "../track-follower";
import { BATCH_SIZE, MAX_QUEUED, UploadQueue, type QueuedReading, type SendResult } from "../upload-queue";

// SYNTHETIC: a round 50 m radius track, 200 outline points
const METERS_PER_DEG = 111_320;
const circle: LatLng[] = Array.from({ length: 200 }, (_, i) => {
  const a = (2 * Math.PI * i) / 200;
  return { lat: 10 + (50 * Math.sin(a)) / METERS_PER_DEG, lng: 76 + (50 * Math.cos(a)) / (METERS_PER_DEG * Math.cos((10 * Math.PI) / 180)) };
});
const metres = (a: LatLng, b: LatLng) =>
  Math.hypot((a.lat - b.lat) * METERS_PER_DEG, (a.lng - b.lng) * METERS_PER_DEG * Math.cos((10 * Math.PI) / 180));

describe("TrackFollower", () => {
  it("moves along the track by speed × time between fixes", () => {
    const follower = new TrackFollower(circle);
    follower.onFix(circle[0], 10, 0);
    const later = follower.positionAt(1000)!;
    expect(metres(later, circle[0])).toBeCloseTo(10, 0);
    expect(metres(later, circle[6])).toBeLessThan(2.5);
  });

  it("stops running ahead after 3 s without a fix", () => {
    const follower = new TrackFollower(circle);
    follower.onFix(circle[0], 10, 0);
    expect(follower.positionAt(10_000)).toEqual(follower.positionAt(3000));
  });

  it("uses the raw GPS position far from the track, and nothing before the first fix", () => {
    const follower = new TrackFollower(circle);
    expect(follower.positionAt(0)).toBeNull();
    const pits = { lat: 10.002, lng: 76.002 };
    follower.onFix(pits, 3, 0);
    expect(follower.positionAt(500)).toEqual(pits);
  });
});

const reading = (n: number) => ({ recorded_at: `2026-10-24T10:00:${String(n % 60).padStart(2, "0")}Z`, lateral_g: 0.5,
  speed_kmh: 40, gps_lat: 10, gps_lng: 76, gps_accuracy_m: 4 });

describe("UploadQueue", () => {
  it("numbers readings and sends them in order, at most 100 at a time", async () => {
    const batches: QueuedReading[][] = [];
    const queue = new UploadQueue(async (batch) => (batches.push(batch), { kind: "ok" }));
    for (let i = 0; i < 250; i += 1) queue.push(reading(i));
    for (let t = 0; t < 3; t += 1) await queue.flush(t);
    expect(batches.map((b) => b.length)).toEqual([BATCH_SIZE, BATCH_SIZE, 50]);
    expect(batches.flat().map((r) => r.sequence)).toEqual(Array.from({ length: 250 }, (_, i) => i));
    expect([queue.sent, queue.queued]).toEqual([250, 0]);
  });

  it("keeps readings while offline and retries with a growing delay", async () => {
    let online = false;
    const queue = new UploadQueue(async (): Promise<SendResult> => (online ? { kind: "ok" } : { kind: "retry" }));
    queue.push(reading(1));
    await queue.flush(0);
    await queue.flush(1000);
    expect(queue.queued).toBe(1);
    online = true;
    await queue.flush(1500);
    expect(queue.queued).toBe(1);
    await queue.flush(2000);
    expect([queue.queued, queue.sent]).toEqual([0, 1]);
  });

  it("drops the oldest when full, counts refused batches, and stops on a stop answer", async () => {
    const queue = new UploadQueue(async () => ({ kind: "reject" }));
    for (let i = 0; i < MAX_QUEUED + 5; i += 1) queue.push(reading(i));
    expect([queue.queued, queue.dropped]).toEqual([MAX_QUEUED, 5]);
    await queue.flush(0);
    expect(queue.rejected).toBe(BATCH_SIZE);
    const stopped = new UploadQueue(async () => ({ kind: "stop", message: "Not a real-time session." }));
    stopped.push(reading(1));
    await stopped.flush(0);
    stopped.push(reading(2));
    expect([stopped.stoppedMessage, stopped.queued]).toEqual(["Not a real-time session.", 1]);
  });

  it("removes exactly the sent readings even if old ones were dropped meanwhile", async () => {
    let release: (r: SendResult) => void = () => undefined;
    const queue = new UploadQueue(() => new Promise<SendResult>((resolve) => (release = resolve)));
    for (let i = 0; i < MAX_QUEUED; i += 1) queue.push(reading(i));
    const sending = queue.flush(0);
    for (let i = 0; i < 10; i += 1) queue.push(reading(i));
    release({ kind: "ok" });
    await sending;
    // Readings 0-99 were sent; 0-9 had been dropped meanwhile, so 10-99 go and 2,910 stay
    expect([queue.queued, queue.dropped]).toEqual([MAX_QUEUED + 10 - BATCH_SIZE, 10]);
  });
});
