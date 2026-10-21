/**
 * Trackside Maps — tests for the corner editor's pure helpers and its checks (H3).
 */

import { describe, it, expect } from "vitest";
import { checkMarkers, markerRadius, nearestIndex, nextTurnName, segmentIndexes, toServerMarkers } from "../corner-editor-logic";
import type { EditorMarker, EditorPayload } from "../types";

const payload = {
  spacing_m: 2, outline: new Array(200).fill({ lat: 0, lng: 0 }), radii: new Array(200).fill(40),
  limit_range_g: { min: 1.0, max: 1.5, default: 1.25 }, zone_length_m: { min: 10, max: 100, default: 30 },
} as unknown as EditorPayload;

/** A marker with sensible defaults. */
function marker(patch: Partial<EditorMarker> & { key: string }): EditorMarker {
  return { id: null, label: patch.key, limit: "1.25", length: "30", centerIndex: 50, ...patch };
}

describe("zone segments", () => {
  it("is centred on the point: a 30 m zone at 2 m spacing is 8 points either side (about 32 m of line)", () => {
    const indexes = segmentIndexes(50, 30, 2, 200);
    expect(indexes).toHaveLength(17);
    expect(indexes[0]).toBe(42);
    expect(indexes[16]).toBe(58);
  });

  it("wraps round the start of the loop", () => {
    const indexes = segmentIndexes(2, 30, 2, 200);
    expect(indexes[0]).toBe(194);
    expect(indexes).toContain(0);
    expect(indexes[16]).toBe(10);
  });

  it("takes the tightest radius inside the zone", () => {
    const radii = new Array(200).fill(40);
    radii[52] = 12.5;
    expect(markerRadius(radii, 50, 30, 2)).toBe(12.5);
    expect(markerRadius(radii, 120, 30, 2)).toBe(40);
  });

  it("snaps a click to the nearest outline point", () => {
    const points = [{ x: 0, y: 0 }, { x: 10, y: 0 }, { x: 20, y: 0 }];
    expect(nearestIndex(points, 11, 3)).toEqual({ index: 1, distance: Math.hypot(1, 3) });
  });
});

describe("naming and conversion", () => {
  it("picks the first free Turn name", () => {
    expect(nextTurnName([marker({ key: "a", label: "Turn 2" })])).toBe("Turn 3");
    expect(nextTurnName([])).toBe("Turn 1");
  });

  it("sends trimmed names and numbers to the server", () => {
    const sent = toServerMarkers([marker({ key: "a", id: "z1", label: "  Hairpin ", limit: "1.3", length: "40", centerIndex: 9 })]);
    expect(sent).toEqual([{ id: "z1", label: "Hairpin", threshold_g: 1.3, center_index: 9, length_m: 40 }]);
  });
});

describe("checks (same rules as the server)", () => {
  /** The problem text for a single marker. */
  const problem = (patch: Partial<EditorMarker>) => checkMarkers([marker({ key: "m", ...patch })], payload).byKey.m;

  it("accepts a good marker and the boundary values", () => {
    expect(checkMarkers([marker({ key: "a" })], payload).first).toBeNull();
    expect(problem({ limit: "1.0", length: "10" })).toBeUndefined();
    expect(problem({ limit: "1.5", length: "100", label: "x".repeat(40) })).toBeUndefined();
  });

  it("refuses bad names", () => {
    expect(problem({ label: "  " })).toBeTruthy();
    expect(problem({ label: "x".repeat(41) })).toBeTruthy();
    expect(problem({ label: "Straight" })).toContain("Straight");
    expect(problem({ label: "straightaway" })).toContain("Straight");
  });

  it("refuses limits and lengths out of range", () => {
    for (const limit of ["0.99", "1.51", "", "abc"]) expect(problem({ limit })).toBeTruthy();
    for (const length of ["9.9", "100.1", "", "x"]) expect(problem({ length })).toBeTruthy();
  });

  it("refuses an unplaced marker", () => {
    expect(problem({ centerIndex: null })).toContain("Not on the outline");
  });

  it("refuses duplicate names (any case) and overlapping zones", () => {
    const names = checkMarkers([marker({ key: "a", label: "Turn", centerIndex: 20 }), marker({ key: "b", label: "TURN", centerIndex: 120 })], payload);
    expect(names.byKey.b).toContain("same name".replace("same", "this"));
    const overlap = checkMarkers([marker({ key: "a", centerIndex: 50 }), marker({ key: "b", centerIndex: 60 })], payload);
    expect(overlap.byKey.b).toContain("Overlaps");
    expect(overlap.first).toContain("Overlaps");
    expect(checkMarkers([marker({ key: "a", centerIndex: 50 }), marker({ key: "b", centerIndex: 90 })], payload).first).toBeNull();
  });
});
