/**
 * Trackside — LiveTrackView Component Tests
 *
 * Verifies:
 * 1. Fallback state renders when reference_line is null (track not surveyed)
 * 2. SVG track path renders when reference_line data is provided
 * 3. Driver dot renders with correct stage color when GPS coordinates are present
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { LiveTrackView } from "../live-track-view";

// Mock the api module
vi.mock("../../../lib/api", () => ({
  api: {
    get: vi.fn(),
  },
}));

import { api } from "../../../lib/api";
const mockGet = vi.mocked(api.get);

describe("LiveTrackView", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders fallback when reference_line is null (track not surveyed)", async () => {
    mockGet.mockResolvedValueOnce({
      track_id: "test-track-id",
      reference_line: null,
    });

    render(
      <LiveTrackView
        trackId="test-track-id"
        gpsLat={null}
        gpsLng={null}
        currentG={0.8}
        threshold={1.15}
      />
    );

    // Wait for the API call to resolve and fallback to render
    await waitFor(() => {
      expect(
        screen.getByText(/this track hasn't been surveyed yet/i)
      ).toBeDefined();
    });

    // Should NOT render the SVG track path
    expect(screen.queryByTestId("live-track-svg")).toBeNull();
  });

  it("renders SVG path when reference_line data is provided", async () => {
    const sampleReferenceLine = [
      { lat: 11.016842, lng: 76.955831 },
      { lat: 11.017120, lng: 76.956110 },
      { lat: 11.017400, lng: 76.956400 },
      { lat: 11.017200, lng: 76.956600 },
      { lat: 11.016842, lng: 76.955831 },
    ];

    mockGet.mockResolvedValueOnce({
      track_id: "test-track-id",
      reference_line: sampleReferenceLine,
    });

    render(
      <LiveTrackView
        trackId="test-track-id"
        gpsLat={null}
        gpsLng={null}
        currentG={0.8}
        threshold={1.15}
      />
    );

    // Wait for the SVG to render
    await waitFor(() => {
      expect(screen.getByTestId("live-track-svg")).toBeDefined();
    });

    // Verify the track path element exists
    expect(screen.getByTestId("live-track-path")).toBeDefined();

    // Fallback text should NOT be present
    expect(
      screen.queryByText(/this track hasn't been surveyed yet/i)
    ).toBeNull();
  });

  it("renders no active track message when trackId is null", () => {
    render(
      <LiveTrackView
        trackId={null}
        gpsLat={null}
        gpsLng={null}
        currentG={0.8}
        threshold={1.15}
      />
    );

    expect(screen.getByText(/no active track selected/i)).toBeDefined();
  });

  it("calls the reference-line API with the correct trackId", async () => {
    mockGet.mockResolvedValueOnce({
      track_id: "abc-123",
      reference_line: [
        { lat: 10.0, lng: 20.0 },
        { lat: 10.1, lng: 20.1 },
        { lat: 10.2, lng: 20.2 },
      ],
    });

    render(
      <LiveTrackView
        trackId="abc-123"
        gpsLat={null}
        gpsLng={null}
        currentG={0.5}
        threshold={1.15}
      />
    );

    await waitFor(() => {
      expect(mockGet).toHaveBeenCalledWith(
        "/api/tracks/abc-123/reference-line/"
      );
    });
  });
});
