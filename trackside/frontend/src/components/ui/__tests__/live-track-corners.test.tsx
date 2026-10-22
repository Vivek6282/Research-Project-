/**
 * Trackside — Live Track View: schematic tag and corner segments (Prompt 13, L3/L4)
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { LiveTrackView } from "../live-track-view";

vi.mock("../../../lib/api", () => ({ api: { get: vi.fn() } }));

import { api } from "../../../lib/api";
const mockGet = vi.mocked(api.get);

/** A square outline with a point every 0.0001 degrees. */
const square = (() => {
  const points: { lat: number; lng: number }[] = [];
  for (let i = 0; i <= 20; i++) points.push({ lat: 10 + i * 0.0001, lng: 76 });
  for (let i = 1; i <= 20; i++) points.push({ lat: 10.002, lng: 76 + i * 0.0001 });
  for (let i = 1; i <= 20; i++) points.push({ lat: 10.002 - i * 0.0001, lng: 76.002 });
  for (let i = 1; i < 20; i++) points.push({ lat: 10, lng: 76.002 - i * 0.0001 });
  return points;
})();

const corners = [
  { zone_id: "z1", label: "Hairpin", start: { lat: 10.002, lng: 76.0005 }, end: { lat: 10.002, lng: 76.0015 } },
  { zone_id: "z2", label: "Sweeper", start: { lat: 10.001, lng: 76.002 }, end: { lat: 10.0005, lng: 76.002 } },
];

function show(response: object, zoneId: string | null = null) {
  mockGet.mockResolvedValueOnce({ track_id: "t", ...response });
  render(<LiveTrackView trackId="t" gpsLat={null} gpsLng={null} currentG={0.5} threshold={1.2} zoneId={zoneId} />);
}

describe("LiveTrackView schematic tag and corners", () => {
  beforeEach(() => vi.clearAllMocks());

  it("shows the Schematic map tag only when the response says is_schematic", async () => {
    show({ reference_line: square, is_schematic: true, corners: [] });
    await waitFor(() => expect(screen.getByTestId("schematic-tag").textContent).toBe("Schematic map"));
  });

  it("shows no tag for a surveyed custom map", async () => {
    show({ reference_line: square, is_schematic: false, corners });
    await waitFor(() => expect(screen.getByTestId("live-track-svg")).toBeDefined());
    expect(screen.queryByTestId("schematic-tag")).toBeNull();
  });

  it("draws every corner with its name and highlights only the one the kart is in", async () => {
    show({ reference_line: square, is_schematic: false, corners }, "z2");
    await waitFor(() => expect(screen.getByTestId("live-track-corner-Hairpin")).toBeDefined());
    expect(screen.getByText("Hairpin")).toBeDefined();
    expect(screen.getByText("Sweeper")).toBeDefined();
    expect(screen.getByTestId("live-track-corner-Hairpin").getAttribute("data-active")).toBe("false");
    expect(screen.getByTestId("live-track-corner-Sweeper").getAttribute("data-active")).toBe("true");
  });

  it("keeps the 'not surveyed' message for a custom map without an outline", async () => {
    show({ reference_line: null, is_schematic: false, corners: [] });
    await waitFor(() => expect(screen.getByText(/hasn't been surveyed yet/i)).toBeDefined());
    expect(screen.queryByTestId("schematic-tag")).toBeNull();
  });
});
