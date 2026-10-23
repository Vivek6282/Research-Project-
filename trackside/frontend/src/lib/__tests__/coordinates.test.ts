/**
 * Trackside — typed places ("latitude, longitude") for the drawing map.
 */

import { describe, it, expect } from "vitest";
import { parseCoordinates } from "../coordinates";

describe("parseCoordinates", () => {
  it("reads a comma, space or semicolon separated pair", () => {
    expect(parseCoordinates("10.0123, 76.4567")).toEqual({ lat: 10.0123, lng: 76.4567 });
    expect(parseCoordinates("  -33.86  151.21 ")).toEqual({ lat: -33.86, lng: 151.21 });
    expect(parseCoordinates("51.5;-0.12")).toEqual({ lat: 51.5, lng: -0.12 });
    expect(parseCoordinates("+10, +20")).toEqual({ lat: 10, lng: 20 });
  });

  it("refuses anything that is not exactly two real numbers in range", () => {
    for (const bad of ["", "10", "10, 20, 30", "ten, twenty", "10.5.5, 20", "1e2, 20", "NaN, 20", "Infinity, 1", "91, 20", "-91, 20", "10, 181", "10, -181", "0, 0", "10°, 20°", "10 N, 20 E"]) {
      expect(parseCoordinates(bad), bad).toBeNull();
    }
  });

  it("accepts the edges of the valid range", () => {
    expect(parseCoordinates("90, 180")).toEqual({ lat: 90, lng: 180 });
    expect(parseCoordinates("-90, -180")).toEqual({ lat: -90, lng: -180 });
    expect(parseCoordinates("0, 5")).toEqual({ lat: 0, lng: 5 });
  });
});
