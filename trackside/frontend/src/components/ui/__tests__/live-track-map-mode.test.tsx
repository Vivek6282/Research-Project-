/**
 * Trackside — Live Track View: the real map for tracks with real coordinates, the plain drawing otherwise.
 * The Leaflet component is replaced by a stub that shows what it was given (Leaflet itself is checked in a browser).
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { LiveTrackView } from "../live-track-view";

vi.mock("../../../lib/api", () => ({ api: { get: vi.fn() } }));
vi.mock("../live-track/gps-map-canvas", () => ({
  default: (props: { line: unknown[]; corners: unknown[]; gpsLat: number | null; gpsLng: number | null; stageColor: string; activeZoneId?: string | null }) => (
    <div data-testid="gps-map-stub" data-points={props.line.length} data-corners={props.corners.length}
      data-lat={String(props.gpsLat)} data-lng={String(props.gpsLng)} data-zone={String(props.activeZoneId)} data-color={props.stageColor} />
  ),
}));

import { api } from "../../../lib/api";
const mockGet = vi.mocked(api.get);

const line = Array.from({ length: 12 }, (_, i) => ({ lat: 10 + i * 0.0001, lng: 76 + (i % 3) * 0.0001 }));
const corners = [{ zone_id: "z1", label: "Hairpin", start: line[2], end: line[5] }];

/** Show a track the way the Coach page does. */
function show(response: object, gps: [number | null, number | null] = [10.0003, 76.0001], zoneId: string | null = "z1") {
  mockGet.mockResolvedValue({ track_id: "t", ...response });
  return render(<LiveTrackView trackId="t" gpsLat={gps[0]} gpsLng={gps[1]} currentG={0.5} threshold={1.2} zoneId={zoneId} />);
}

describe("LiveTrackView map mode", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.localStorage.removeItem("trackside_live_map_mode");
  });

  it("a track with real coordinates opens on the real map, with its line, corners and the driver's position", async () => {
    show({ reference_line: line, is_schematic: false, corners });
    const map = await screen.findByTestId("gps-map-stub");
    expect(map.dataset).toMatchObject({ points: "12", corners: "1", lat: "10.0003", lng: "76.0001", zone: "z1" });
    expect(screen.queryByTestId("live-track-svg")).toBeNull();
  });

  it("the Demo Circuit (schematic, no real coordinates) keeps the plain drawing and has no Map/Plain switch", async () => {
    show({ reference_line: line, is_schematic: true, corners: [] });
    await waitFor(() => expect(screen.getByTestId("live-track-svg")).toBeDefined());
    expect(screen.queryByTestId("gps-map-stub")).toBeNull();
    expect(screen.queryByTestId("live-view-map")).toBeNull();
  });

  it("Plain switches to the drawing, Map switches back, and the choice is remembered", async () => {
    const view = show({ reference_line: line, is_schematic: false, corners });
    await screen.findByTestId("gps-map-stub");
    fireEvent.click(screen.getByTestId("live-view-plain"));
    expect(screen.getByTestId("live-track-svg")).toBeDefined();
    expect(screen.queryByTestId("gps-map-stub")).toBeNull();
    expect(window.localStorage.getItem("trackside_live_map_mode")).toBe("plain");
    view.unmount();
    show({ reference_line: line, is_schematic: false, corners });                      // a new visit starts in Plain
    await waitFor(() => expect(screen.getByTestId("live-track-svg")).toBeDefined());
    fireEvent.click(screen.getByTestId("live-view-map"));
    expect(await screen.findByTestId("gps-map-stub")).toBeDefined();
  });

  it("an unsurveyed track still shows the fallback, never an empty map", async () => {
    show({ reference_line: null, is_schematic: false, corners: [] });
    await waitFor(() => expect(screen.queryByTestId("gps-map-stub")).toBeNull());
    expect(screen.queryByTestId("live-view-map")).toBeNull();
  });

  it("passes no position to the map before the first reading", async () => {
    show({ reference_line: line, is_schematic: false, corners }, [null, null], null);
    const map = await screen.findByTestId("gps-map-stub");
    expect(map.dataset).toMatchObject({ lat: "null", lng: "null", zone: "null" });
  });
});
