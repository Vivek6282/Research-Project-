/**
 * Trackside — Path Progress Helper Tests
 *
 * Verifies the lap-wrapping and "short way round" rules that keep the
 * tracker marker from jumping when it crosses the start/finish line.
 */

import { describe, it, expect } from "vitest";
import {
  wrapProgress,
  interpolate,
  resolveNextProgress,
  findNearestProgressOnPath,
} from "../live-track/path-progress";

/** A fake straight 100-unit path from (0,0) to (100,0), enough for measuring. */
function makeStraightPath(): SVGPathElement {
  return {
    getTotalLength: () => 100,
    getPointAtLength: (length: number) => ({ x: Math.min(Math.max(length, 0), 100), y: 0 }),
  } as unknown as SVGPathElement;
}

describe("wrapProgress", () => {
  it("keeps values inside one lap", () => {
    expect(wrapProgress(1.02)).toBeCloseTo(0.02);
    expect(wrapProgress(-0.1)).toBeCloseTo(0.9);
    expect(wrapProgress(0.5)).toBe(0.5);
  });
});

describe("interpolate", () => {
  it("blends between two values", () => {
    expect(interpolate(10, 20, 0)).toBe(10);
    expect(interpolate(10, 20, 0.5)).toBe(15);
    expect(interpolate(10, 20, 1)).toBe(20);
  });
});

describe("resolveNextProgress", () => {
  it("moves forward normally", () => {
    expect(resolveNextProgress(0.2, 0.3)).toBeCloseTo(0.3);
  });

  it("crosses the start/finish line forward from 0.99 to 0.01", () => {
    const next = resolveNextProgress(0.99, 0.01);
    expect(next).toBeCloseTo(1.01); // moved +0.02, did not rewind the lap
  });

  it("keeps working on later laps", () => {
    const next = resolveNextProgress(2.99, 0.02);
    expect(next).toBeCloseTo(3.02);
  });

  it("ignores tiny backwards GPS noise", () => {
    expect(resolveNextProgress(0.5, 0.495)).toBeCloseTo(0.5);
  });

  it("ignores tiny backwards noise across the line too", () => {
    expect(resolveNextProgress(1.005, 0.995)).toBeCloseTo(1.005);
  });
});

describe("findNearestProgressOnPath", () => {
  it("finds how far along the path the closest point is", () => {
    const progress = findNearestProgressOnPath(makeStraightPath(), 25, 10);
    expect(progress).not.toBeNull();
    expect(progress as number).toBeCloseTo(0.25, 2);
  });

  it("returns null when the browser cannot measure paths", () => {
    expect(findNearestProgressOnPath({} as SVGPathElement, 1, 1)).toBeNull();
  });
});
