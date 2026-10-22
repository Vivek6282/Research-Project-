/**
 * Trackside Maps — tests for the safe-speed formula, input checks and outline geometry.
 */

import { describe, it, expect } from "vitest";
import { labelError, limitError, parseLimit, safeSpeedKmh } from "../safe-speed";
import { loopRange, projectOutline } from "../outline-geometry";

describe("safe corner speed", () => {
  it("matches sqrt(limit x 9.81 x radius) in km/h", () => {
    expect(safeSpeedKmh(1.25, 20)).toBeCloseTo(56.38, 1);
    expect(safeSpeedKmh(1.5, 12)).toBeCloseTo(Math.sqrt(1.5 * 9.81 * 12) * 3.6, 6);
  });

  it("grows when the limit grows", () => {
    expect(safeSpeedKmh(1.5, 25)).toBeGreaterThan(safeSpeedKmh(1.0, 25));
  });
});

describe("input checks", () => {
  it("accepts limits from 1.0 to 1.5 and rejects the rest", () => {
    expect(limitError("1.0", 1.0, 1.5)).toBeNull();
    expect(limitError("1.5", 1.0, 1.5)).toBeNull();
    expect(limitError("0.99", 1.0, 1.5)).not.toBeNull();
    expect(limitError("1.51", 1.0, 1.5)).not.toBeNull();
    expect(limitError("", 1.0, 1.5)).not.toBeNull();
    expect(limitError("abc", 1.0, 1.5)).not.toBeNull();
    expect(parseLimit("Infinity")).toBeNull();
  });

  it("requires a corner name of 1 to 40 characters", () => {
    expect(labelError("Turn 1")).toBeNull();
    expect(labelError("x".repeat(40))).toBeNull();
    expect(labelError("x".repeat(41))).not.toBeNull();
    expect(labelError("   ")).not.toBeNull();
  });
});

describe("outline geometry", () => {
  it("fits every point inside the picture", () => {
    const outline = [
      { lat: 12.97, lng: 77.59 },
      { lat: 12.9702, lng: 77.5905 },
      { lat: 12.9698, lng: 77.5907 },
    ];
    const { points } = projectOutline(outline, 480, 320, 16);
    for (const p of points) {
      expect(p.x).toBeGreaterThanOrEqual(15.99);
      expect(p.x).toBeLessThanOrEqual(464.01);
      expect(p.y).toBeGreaterThanOrEqual(15.99);
      expect(p.y).toBeLessThanOrEqual(304.01);
    }
  });

  it("puts north at the top", () => {
    const { points } = projectOutline(
      [
        { lat: 12.9, lng: 77.5 },
        { lat: 13.0, lng: 77.5 },
        { lat: 12.95, lng: 77.6 },
      ],
      400,
      400,
    );
    expect(points[1].y).toBeLessThan(points[0].y);
  });

  it("returns nothing for an empty outline", () => {
    expect(projectOutline([], 100, 100).points).toEqual([]);
  });

  it("walks a corner that crosses the start of the loop", () => {
    expect(loopRange(8, 1, 10)).toEqual([8, 9, 0, 1]);
    expect(loopRange(2, 4, 10)).toEqual([2, 3, 4]);
  });
});
