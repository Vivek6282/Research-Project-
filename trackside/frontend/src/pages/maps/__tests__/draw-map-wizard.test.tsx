/**
 * Trackside Maps — the "Draw on map" wizard: click points, preview, name corners, set limits, save.
 * Leaflet is replaced by a stub that can click points and shows where the map was asked to go.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";

vi.mock("../../../lib/api", () => ({ api: { get: vi.fn(), post: vi.fn(), upload: vi.fn(), delete: vi.fn(), put: vi.fn(), patch: vi.fn() } }));
vi.mock("../components/draw-map-canvas", () => ({
  default: (props: { points: { lat: number; lng: number }[]; onAdd: (p: { lat: number; lng: number }) => void; onMove: (i: number, p: { lat: number; lng: number }) => void; focus: { lat: number; lng: number } | null }) => (
    <div data-testid="draw-map-stub" data-focus={props.focus ? `${props.focus.lat},${props.focus.lng}` : ""}>
      <button data-testid="stub-add" onClick={() => props.onAdd({ lat: 10 + props.points.length * 0.00123456789, lng: 76 + (props.points.length % 4) * 0.0005 })}>add</button>
      <button data-testid="stub-move" onClick={() => props.onMove(0, { lat: 11.123456789, lng: 77.1 })}>move</button>
      <span data-testid="stub-points">{JSON.stringify(props.points)}</span>
    </div>
  ),
}));

import { api } from "../../../lib/api";
import { DrawMapWizard } from "../components/draw-map-wizard";

const mockPost = vi.mocked(api.post);
/** One corner of the preview, in the shape the server sends. */
function corner(number: number, radius: number) {
  const at = { lat: 10 + number * 1e-4, lng: 76 + number * 1e-4 };
  return {
    number, suggested_name: `Turn ${number}`, start: at, end: at, apex: at,
    start_index: number * 10, end_index: number * 10 + 5, apex_index: number * 10 + 2,
    tightest_radius_m: radius, length_m: 20, safe_speed_kmh_at_default: 50,
  };
}
const PREVIEW = {
  source: "drawn", session_title: "", track_name: "", rows_total: 10, rows_used: 10, rows_rejected: 0,
  outline_length_m: 764, outline_spacing_m: 2, corner_radius_m: 60,
  limit_range_g: { min: 0.3, max: 1.5, default: 1.25 },
  outline: [{ lat: 10, lng: 76 }, { lat: 10.0002, lng: 76.0005 }, { lat: 10.0004, lng: 76.0003 }, ...Array.from({ length: 60 }, (_, i) => ({ lat: 10 + i * 1e-5, lng: 76 + i * 1e-5 }))],
  corners: [corner(1, 30), corner(2, 28)],
};

/** Click n points through the stub map. */
function addPoints(n: number) {
  for (let i = 0; i < n; i++) fireEvent.click(screen.getByTestId("stub-add"));
}

/** Render the wizard and wait for the (lazy) map. */
async function open(onSaved = vi.fn()) {
  render(<DrawMapWizard onClose={vi.fn()} onSaved={onSaved} />);
  await screen.findByTestId("draw-map-stub");
  return onSaved;
}

describe("DrawMapWizard", () => {
  beforeEach(() => { vi.clearAllMocks(); });

  it("needs 8 points before the track can be previewed, and undo / clear work", async () => {
    await open();
    expect((screen.getByTestId("draw-preview-btn") as HTMLButtonElement).disabled).toBe(true);
    addPoints(7);
    expect(screen.getByTestId("draw-count").textContent).toContain("7 points (need at least 8)");
    addPoints(1);
    expect((screen.getByTestId("draw-preview-btn") as HTMLButtonElement).disabled).toBe(false);
    fireEvent.click(screen.getByTestId("draw-undo"));
    expect(screen.getByTestId("draw-count").textContent).toContain("7 points");
    fireEvent.click(screen.getByTestId("draw-clear"));
    expect(screen.getByTestId("draw-count").textContent).toContain("0 points");
    expect((screen.getByTestId("draw-undo") as HTMLButtonElement).disabled).toBe(true);
  });

  it("rounds points to about a centimetre and lets one be moved", async () => {
    await open();
    addPoints(2);
    fireEvent.click(screen.getByTestId("stub-move"));
    const points = JSON.parse(screen.getByTestId("stub-points").textContent!);
    expect(points[0]).toEqual({ lat: 11.1234568, lng: 77.1 });
    expect(points[1].lat).toBe(10.0012346);
  });

  it("moves the map to typed coordinates, and refuses text that is not a place", async () => {
    await open();
    fireEvent.change(screen.getByTestId("draw-place-input"), { target: { value: "oops" } });
    fireEvent.click(screen.getByTestId("draw-go"));
    expect(screen.getByTestId("wizard-error").textContent).toContain("latitude, longitude");
    fireEvent.change(screen.getByTestId("draw-place-input"), { target: { value: "10.5, 76.25" } });
    fireEvent.click(screen.getByTestId("draw-go"));
    expect(screen.queryByTestId("wizard-error")).toBeNull();
    expect(screen.getByTestId("draw-map-stub").dataset.focus).toBe("10.5,76.25");
  });

  it("sends the points and the radius to the preview, then shows the review step with both corners", async () => {
    mockPost.mockResolvedValueOnce(PREVIEW);
    await open();
    addPoints(8);
    fireEvent.change(screen.getByTestId("draw-radius-input"), { target: { value: "45" } });
    fireEvent.click(screen.getByTestId("draw-preview-btn"));
    await screen.findByTestId("wizard-summary");
    const [url, body] = mockPost.mock.calls[0] as [string, { points: unknown[]; corner_radius_m: number }];
    expect(url).toBe("/api/tracks/draw/preview/");
    expect(body.points).toHaveLength(8);
    expect(body.corner_radius_m).toBe(45);
    expect(screen.getByTestId("wizard-summary").textContent).toContain("8 points clicked · track length 764 m · 2 corners");
    expect(screen.getByTestId("corner-name-1")).toBeDefined();
    expect(screen.getByTestId("corner-name-2")).toBeDefined();
  });

  it("shows the server's message when the preview is refused, and stays on the drawing step", async () => {
    mockPost.mockRejectedValueOnce(new Error("The track must be between 100 m and 20 km long (it is 40 m)."));
    await open();
    addPoints(8);
    fireEvent.click(screen.getByTestId("draw-preview-btn"));
    await waitFor(() => expect(screen.getByTestId("wizard-error").textContent).toContain("it is 40 m"));
    expect(screen.queryByTestId("wizard-summary")).toBeNull();
    expect(screen.getByTestId("draw-count").textContent).toContain("8 points");
  });

  it("saves with the name, the corner names and a limit below 1 g, then reports it saved", async () => {
    mockPost.mockResolvedValueOnce(PREVIEW).mockResolvedValueOnce({});
    const onSaved = await open();
    addPoints(8);
    fireEvent.click(screen.getByTestId("draw-preview-btn"));
    await screen.findByTestId("wizard-summary");
    expect((screen.getByTestId("map-save-btn") as HTMLButtonElement).disabled).toBe(true);        // no name yet
    expect(screen.getByTestId("wizard-blocker").textContent).toContain("Give the map a name");
    fireEvent.change(screen.getByTestId("map-name-input"), { target: { value: "My Kart Track" } });
    fireEvent.change(screen.getByTestId("corner-limit-1"), { target: { value: "0.55" } });
    fireEvent.change(screen.getByTestId("corner-name-2"), { target: { value: "Hairpin" } });
    fireEvent.change(screen.getByTestId("corner-limit-2"), { target: { value: "0.4" } });
    expect((screen.getByTestId("map-save-btn") as HTMLButtonElement).disabled).toBe(false);
    fireEvent.click(screen.getByTestId("map-save-btn"));
    await waitFor(() => expect(onSaved).toHaveBeenCalled());
    const [url, body] = mockPost.mock.calls[1] as [string, Record<string, unknown>];
    expect(url).toBe("/api/tracks/draw/confirm/");
    expect(body.name).toBe("My Kart Track");
    expect(body.corners).toEqual([{ number: 1, label: "Turn 1", threshold_g: 0.55 }, { number: 2, label: "Hairpin", threshold_g: 0.4 }]);
    expect(body.points).toHaveLength(8);
    expect(body).not.toHaveProperty("outline");              // the server builds the outline itself
  });

  it("blocks a limit outside 0.3 to 1.5 g and two corners with the same name", async () => {
    mockPost.mockResolvedValueOnce(PREVIEW);
    await open();
    addPoints(8);
    fireEvent.click(screen.getByTestId("draw-preview-btn"));
    await screen.findByTestId("wizard-summary");
    fireEvent.change(screen.getByTestId("map-name-input"), { target: { value: "X" } });
    fireEvent.change(screen.getByTestId("corner-limit-1"), { target: { value: "0.2" } });
    expect(screen.getByTestId("wizard-blocker").textContent).toContain("Fix corner 1");
    fireEvent.change(screen.getByTestId("corner-limit-1"), { target: { value: "0.6" } });
    fireEvent.change(screen.getByTestId("corner-name-2"), { target: { value: "turn 1" } });
    expect(screen.getByTestId("wizard-blocker").textContent).toContain("different name");
  });

  it("Back to drawing keeps the points", async () => {
    mockPost.mockResolvedValueOnce(PREVIEW);
    await open();
    addPoints(9);
    fireEvent.click(screen.getByTestId("draw-preview-btn"));
    await screen.findByTestId("wizard-summary");
    fireEvent.click(screen.getByText("Back to drawing"));
    expect(await screen.findByTestId("draw-count")).toBeDefined();
    expect(screen.getByTestId("draw-count").textContent).toContain("9 points");
  });
});
