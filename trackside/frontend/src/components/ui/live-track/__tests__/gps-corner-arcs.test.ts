/**
 * Trackside — corners placed on a real-coordinate track line.
 */

import { describe, it, expect } from "vitest";
import { arcBetween, buildCornerArcs, nearestPointIndex } from "../gps-corner-arcs";

/** A square-ish closed loop of 40 points, 10 on each side, near latitude 10. */
const LOOP = Array.from({ length: 40 }, (_, i) => {
  const side = Math.floor(i / 10), k = (i % 10) / 10;
  const corners = [[0, 0], [0, 1], [1, 1], [1, 0]];
  const [aLat, aLng] = corners[side], [bLat, bLng] = corners[(side + 1) % 4];
  return { lat: 10 + (aLat + (bLat - aLat) * k) * 0.001, lng: 76 + (aLng + (bLng - aLng) * k) * 0.001 };
});

describe("corner arcs on a real map", () => {
  it("finds the track point nearest to a position", () => {
    expect(nearestPointIndex(LOOP, LOOP[17])).toBe(17);
    expect(nearestPointIndex(LOOP, { lat: LOOP[5].lat + 1e-7, lng: LOOP[5].lng })).toBe(5);
  });

  it("goes the short way round the loop, also across the start of the list", () => {
    expect(arcBetween(LOOP, 3, 7).map((p) => LOOP.indexOf(p))).toEqual([3, 4, 5, 6, 7]);
    expect(arcBetween(LOOP, 38, 2).map((p) => LOOP.indexOf(p))).toEqual([38, 39, 0, 1, 2]);
    expect(arcBetween(LOOP, 2, 38).map((p) => LOOP.indexOf(p))).toEqual([38, 39, 0, 1, 2]);
  });

  it("builds one arc per corner, with its label and zone id", () => {
    const arcs = buildCornerArcs(LOOP, [
      { zone_id: "z1", label: "Hairpin", start: LOOP[8], end: LOOP[12] },
      { zone_id: "z2", label: "Chicane", start: LOOP[30], end: LOOP[33] },
    ]);
    expect(arcs.map((a) => [a.zoneId, a.label, a.points.length])).toEqual([["z1", "Hairpin", 5], ["z2", "Chicane", 4]]);
    expect(arcs[0].points[0]).toEqual([LOOP[8].lat, LOOP[8].lng]);
  });

  it("gives nothing for a line too short to draw", () => {
    expect(buildCornerArcs([LOOP[0]], [{ zone_id: "z", label: "A", start: LOOP[0], end: LOOP[0] }])).toEqual([]);
    expect(buildCornerArcs([], [])).toEqual([]);
  });
});
