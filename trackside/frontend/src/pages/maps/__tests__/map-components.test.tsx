/**
 * Trackside Maps — component tests: corner table live hint, map list buttons, wizard flow.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { CornerTable } from "../components/corner-table";
import { MapCardGrid } from "../components/map-card-grid";
import { AddMapWizard } from "../components/add-map-wizard";
import type { CornerPreview, ImportPreview, MapTrack } from "../types";

vi.mock("../../../lib/api", () => ({ api: { upload: vi.fn(), get: vi.fn(), delete: vi.fn(), post: vi.fn() } }));
import { api } from "../../../lib/api";
const mockUpload = vi.mocked(api.upload);

const at = { lat: 12.97, lng: 77.59 };
/** Build a corner as the preview endpoint would return it. */
function corner(number: number, radius: number): CornerPreview {
  return {
    number, suggested_name: `Turn ${number}`, start: at, end: at, apex: at,
    start_index: number * 10, end_index: number * 10 + 5, apex_index: number * 10 + 2,
    tightest_radius_m: radius, length_m: 20, safe_speed_kmh_at_default: 50,
  };
}
const PREVIEW: ImportPreview = {
  source: "racechrono_csv", session_title: "Morning", track_name: "Kari Test", rows_total: 900, rows_used: 897,
  rows_rejected: 3, outline_length_m: 602.7, corner_radius_m: 60, limit_range_g: { min: 1, max: 1.5, default: 1.25 },
  outline: [{ lat: 12.97, lng: 77.59 }, { lat: 12.9702, lng: 77.5905 }, { lat: 12.9698, lng: 77.5907 }, ...Array.from({ length: 60 }, (_, i) => ({ lat: 12.97 + i * 1e-5, lng: 77.59 + i * 1e-5 }))],
  corners: [corner(1, 20), corner(2, 12)],
};

/** Build a map row with sensible defaults. */
function map(patch: Partial<MapTrack>): MapTrack {
  return { id: "1", name: "Map", source: "racechrono_csv", is_builtin: false, is_archived: false, zones: [], ...patch };
}

describe("CornerTable", () => {
  it("recalculates the safe speed live when the limit changes", () => {
    const onChange = vi.fn();
    const { rerender } = render(
      <CornerTable corners={[corner(1, 20)]} choices={[{ number: 1, label: "T1", limit: "1.25" }]}
        range={PREVIEW.limit_range_g} onChange={onChange} />,
    );
    expect(screen.getByTestId("corner-speed-1").textContent).toContain("56 km/h");
    rerender(
      <CornerTable corners={[corner(1, 20)]} choices={[{ number: 1, label: "T1", limit: "1.5" }]}
        range={PREVIEW.limit_range_g} onChange={onChange} />,
    );
    expect(screen.getByTestId("corner-speed-1").textContent).toContain("62 km/h");
    fireEvent.change(screen.getByTestId("corner-limit-1"), { target: { value: "1.4" } });
    expect(onChange).toHaveBeenCalledWith(1, { limit: "1.4" });
  });

  it("shows an error and no speed for a limit outside 1.0 to 1.5", () => {
    render(
      <CornerTable corners={[corner(1, 20)]} choices={[{ number: 1, label: "T1", limit: "1.9" }]}
        range={PREVIEW.limit_range_g} onChange={vi.fn()} />,
    );
    expect(screen.getByText("Use 1 to 1.5 g")).toBeTruthy();
    expect(screen.getByTestId("corner-speed-1").textContent).toContain("—");
  });
});

describe("MapCardGrid", () => {
  const handlers = { onArchive: vi.fn(), onRestore: vi.fn() };
  const square = [{ lat: 12.97, lng: 77.59 }, { lat: 12.97, lng: 77.592 }, { lat: 12.972, lng: 77.592 }, { lat: 12.972, lng: 77.59 }];

  it("shows Built-in and Simulator map badges, the schematic note, and no archive button for the Demo Circuit", () => {
    const demo = map({ name: "Demo Circuit", is_builtin: true, source: "builtin", is_schematic: true, schematic_outline: square });
    render(<MapCardGrid maps={[demo]} canArchive {...handlers} />);
    const card = screen.getByTestId("map-card-Demo Circuit");
    expect(card.textContent).toContain("Built-in");
    expect(card.textContent).toContain("Simulator map");
    expect(card.textContent).toContain("Schematic");
    expect(screen.getByTestId("outline-thumbnail")).toBeTruthy();
    expect(screen.queryByTestId("archive-Demo Circuit")).toBeNull();
  });

  it("shows the number of alert corners and a thumbnail from the stored outline", () => {
    const zones = [{ id: "a", label: "T1", threshold_g: 1.2 }, { id: "b", label: "T2", threshold_g: 1.3 }];
    render(<MapCardGrid maps={[map({ name: "Kari", zones, reference_line: square }), map({ id: "2", name: "Bare" })]} canArchive {...handlers} />);
    expect(screen.getByTestId("map-card-corners-Kari").textContent).toContain("2 alert corners");
    expect(screen.getByTestId("map-card-corners-Bare").textContent).toContain("0 alert corners");
    expect(screen.getAllByTestId("outline-thumbnail")).toHaveLength(1);
    expect(screen.getAllByTestId("outline-thumbnail-empty")).toHaveLength(1);
  });

  it("offers Archive on active maps and Restore on archived maps", () => {
    render(<MapCardGrid maps={[map({ name: "A" }), map({ id: "2", name: "B", is_archived: true })]} canArchive {...handlers} />);
    expect(screen.getByTestId("archive-A")).toBeTruthy();
    expect(screen.getByTestId("restore-B")).toBeTruthy();
    expect(screen.getByTestId("map-card-B").textContent).toContain("Archived");
    fireEvent.click(screen.getByTestId("restore-B"));
    expect(handlers.onRestore).toHaveBeenCalled();
  });

  it("gives read-only users no change buttons at all", () => {
    render(<MapCardGrid maps={[map({ name: "A" }), map({ id: "2", name: "B", is_archived: true })]} canArchive={false} {...handlers} />);
    expect(screen.queryByTestId("archive-A")).toBeNull();
    expect(screen.queryByTestId("restore-B")).toBeNull();
    expect(screen.queryByTestId("play-A")).toBeNull();
    expect(screen.queryByTestId("edit-corners-A")).toBeNull();
  });

  it("shows Play demo and Edit corners only when the caller allows them, and never Play on archived maps", () => {
    const onPlay = vi.fn();
    const onEdit = vi.fn();
    render(<MapCardGrid maps={[map({ name: "A" }), map({ id: "2", name: "B", is_archived: true })]} canArchive onPlay={onPlay} onEditCorners={onEdit} {...handlers} />);
    fireEvent.click(screen.getByTestId("play-A"));
    fireEvent.click(screen.getByTestId("edit-corners-A"));
    expect(onPlay).toHaveBeenCalledWith(expect.objectContaining({ name: "A" }));
    expect(onEdit).toHaveBeenCalledWith(expect.objectContaining({ name: "A" }));
    expect(screen.queryByTestId("play-B")).toBeNull();
    expect(screen.getByTestId("edit-corners-B").textContent).toContain("View corners");
  });

  it("disables Play with the reason when a demo is running", () => {
    render(<MapCardGrid maps={[map({ name: "A" })]} canArchive onPlay={vi.fn()} playDisabledReason="A demo is running" {...handlers} />);
    const button = screen.getByTestId("play-A") as HTMLButtonElement;
    expect(button.disabled).toBe(true);
    expect(button.title).toBe("A demo is running");
  });

  it("says so when there are no maps", () => {
    render(<MapCardGrid maps={[]} canArchive {...handlers} />);
    expect(screen.getByTestId("maps-empty")).toBeTruthy();
  });
});

describe("AddMapWizard", () => {
  beforeEach(() => vi.clearAllMocks());

  /** Upload a file in the wizard and wait for the review step. */
  async function reachReview(onSaved = vi.fn()) {
    mockUpload.mockResolvedValueOnce(PREVIEW);
    render(<AddMapWizard onClose={vi.fn()} onSaved={onSaved} />);
    const file = new File(["latitude,longitude"], "session.csv", { type: "text/csv" });
    fireEvent.change(screen.getByTestId("map-file-input"), { target: { files: [file] } });
    fireEvent.click(screen.getByTestId("map-preview-btn"));
    await waitFor(() => expect(screen.getByTestId("wizard-summary")).toBeTruthy());
    return onSaved;
  }

  it("refuses a wrong file type before uploading", () => {
    render(<AddMapWizard onClose={vi.fn()} onSaved={vi.fn()} />);
    const file = new File(["x"], "notes.txt", { type: "text/plain" });
    fireEvent.change(screen.getByTestId("map-file-input"), { target: { files: [file] } });
    expect(screen.getByTestId("wizard-error").textContent).toContain(".csv");
    expect((screen.getByTestId("map-preview-btn") as HTMLButtonElement).disabled).toBe(true);
    expect(mockUpload).not.toHaveBeenCalled();
  });

  it("previews, then saves the user's names and limits as the server's JSON", async () => {
    const onSaved = await reachReview();
    expect(screen.getByTestId("wizard-summary").textContent).toContain("897 GPS rows used, 3 rejected");
    expect(screen.getByTestId("outline-svg")).toBeTruthy();
    expect(screen.getByTestId("outline-corner-2")).toBeTruthy();
    fireEvent.change(screen.getByTestId("corner-name-1"), { target: { value: "Hairpin" } });
    fireEvent.change(screen.getByTestId("corner-limit-2"), { target: { value: "1.4" } });
    mockUpload.mockResolvedValueOnce({});
    fireEvent.click(screen.getByTestId("map-save-btn"));
    await waitFor(() => expect(onSaved).toHaveBeenCalled());
    const [url, form] = mockUpload.mock.calls[1] as [string, FormData];
    expect(url).toBe("/api/tracks/import/confirm/");
    expect(form.get("name")).toBe("Kari Test");
    expect(JSON.parse(String(form.get("corners")))).toEqual([
      { number: 1, label: "Hairpin", threshold_g: 1.25 },
      { number: 2, label: "Turn 2", threshold_g: 1.4 },
    ]);
  });

  it("blocks saving for a bad limit, a duplicate name or a blank map name", async () => {
    await reachReview();
    const save = screen.getByTestId("map-save-btn") as HTMLButtonElement;
    expect(save.disabled).toBe(false);
    fireEvent.change(screen.getByTestId("corner-limit-1"), { target: { value: "2" } });
    expect(save.disabled).toBe(true);
    fireEvent.change(screen.getByTestId("corner-limit-1"), { target: { value: "1.2" } });
    fireEvent.change(screen.getByTestId("corner-name-2"), { target: { value: "turn 1" } });
    expect(save.disabled).toBe(true);
    expect(screen.getByTestId("wizard-blocker").textContent).toContain("different name");
    fireEvent.change(screen.getByTestId("corner-name-2"), { target: { value: "Turn 2" } });
    fireEvent.change(screen.getByTestId("map-name-input"), { target: { value: "  " } });
    expect(save.disabled).toBe(true);
  });

  it("shows the server's message when the preview fails", async () => {
    mockUpload.mockRejectedValueOnce(new Error("Could not find one complete lap"));
    render(<AddMapWizard onClose={vi.fn()} onSaved={vi.fn()} />);
    const file = new File(["x"], "s.vbo");
    fireEvent.change(screen.getByTestId("map-file-input"), { target: { files: [file] } });
    fireEvent.click(screen.getByTestId("map-preview-btn"));
    await waitFor(() => expect(screen.getByTestId("wizard-error").textContent).toContain("complete lap"));
  });
});
