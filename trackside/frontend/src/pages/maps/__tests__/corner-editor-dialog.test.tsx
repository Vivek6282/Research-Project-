/**
 * Trackside Maps — corner editor dialog: click to add, drag, suggestions, save, view-only, duplicate (H3).
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";

vi.mock("../../../lib/api", () => ({ api: { get: vi.fn(), put: vi.fn(), post: vi.fn() } }));
import { api } from "../../../lib/api";
import { CornerEditorDialog } from "../components/corner-editor-dialog";
import { projectOutline } from "../outline-geometry";
import type { EditorPayload, MapTrack } from "../types";

const COUNT = 120;
const outline = Array.from({ length: COUNT }, (_, i) => ({ lat: 12.97 + 0.0004 * Math.sin((2 * Math.PI * i) / COUNT), lng: 77.59 + 0.0004 * Math.cos((2 * Math.PI * i) / COUNT) }));
const radii = Array.from({ length: COUNT }, (_, i) => (i >= 8 && i <= 22 ? 12 : 40));
const projected = projectOutline(outline, 800, 520, 40).points;

/** The editor payload the server would send for a custom map with one corner and two suggestions. */
function makePayload(patch: Partial<EditorPayload> = {}): EditorPayload {
  return {
    track_id: "t1", track_name: "Kari", editable: true, is_schematic: false, outline_version: "v1", spacing_m: 2, outline, radii,
    markers: [{ id: "z1", label: "Hairpin", threshold_g: 1.2, center_index: 15, length_m: 30, radius_m: 12 }],
    suggestions: [
      { center_index: 15, radius_m: 12, suggested_name: "Turn 1", start_index: 8, end_index: 22, already_marked: true },
      { center_index: 80, radius_m: 25, suggested_name: "Turn 2", start_index: 70, end_index: 90, already_marked: false },
    ],
    limit_range_g: { min: 1.0, max: 1.5, default: 1.25 }, zone_length_m: { min: 10, max: 100, default: 30 }, no_curve_radius_m: 9999, ...patch,
  };
}
const map = (patch: Partial<MapTrack> = {}): MapTrack => ({ id: "t1", name: "Kari", source: "vbo", is_builtin: false, is_archived: false, zones: [], ...patch });

/** Make the canvas report an 800 x 520 box so client coordinates equal picture units. */
function sizeCanvas() {
  const canvas = screen.getByTestId("corner-editor-canvas");
  canvas.getBoundingClientRect = () => ({ left: 0, top: 0, width: 800, height: 520, right: 800, bottom: 520, x: 0, y: 0, toJSON: () => ({}) });
  return canvas;
}

describe("CornerEditorDialog (editable map)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.get).mockResolvedValue(makePayload());
  });

  /** Open the editor and wait until it is drawn. */
  async function open(onChanged = vi.fn(), onClose = vi.fn()) {
    render(<CornerEditorDialog map={map()} onClose={onClose} onChanged={onChanged} />);
    await waitFor(() => expect(screen.getByTestId("corner-marker-table")).toBeTruthy());
    return { onChanged, onClose };
  }

  it("shows the markers with radius and the safe corner speed at the current limit", async () => {
    await open();
    expect(screen.getByTestId("marker-hint-1").textContent).toContain("R 12 m");
    // sqrt(1.2 x 9.81 x 12) x 3.6 = 42.8 km/h
    expect(screen.getByTestId("marker-hint-1").textContent).toContain("43 km/h safe");
    fireEvent.change(screen.getByTestId("marker-limit-1"), { target: { value: "1.5" } });
    expect(screen.getByTestId("marker-hint-1").textContent).toContain("48 km/h safe");
  });

  it("offers only the bends that are not marked yet and accepts a suggestion", async () => {
    await open();
    expect(screen.queryByTestId("editor-suggestion-15")).toBeNull();
    fireEvent.click(screen.getByTestId("editor-suggestion-80"));
    expect((screen.getByTestId("marker-name-2") as HTMLInputElement).value).toBe("Turn 2");
    expect((screen.getByTestId("marker-limit-2") as HTMLInputElement).value).toBe("1.25");
    expect((screen.getByTestId("marker-length-2") as HTMLInputElement).value).toBe("30");
    expect(screen.queryByTestId("editor-suggestion-80")).toBeNull();
  });

  it("suggests a bend again as soon as its marker is removed", async () => {
    await open();
    expect(screen.queryByTestId("editor-suggestion-15")).toBeNull();
    fireEvent.click(screen.getByTestId("marker-remove-1"));
    expect(screen.getByTestId("editor-suggestion-15")).toBeTruthy();
    fireEvent.click(screen.getByTestId("editor-suggestion-15"));
    expect(screen.queryByTestId("editor-suggestion-15")).toBeNull();
    expect((screen.getByTestId("marker-name-1") as HTMLInputElement).value).toBe("Turn 1");
  });

  it("adds a marker when the outline is clicked and ignores clicks far from it", async () => {
    await open();
    const canvas = sizeCanvas();
    const p = projected[60];
    fireEvent.click(canvas, { clientX: p.x + 3, clientY: p.y + 2 });
    expect(screen.getByTestId("marker-row-2")).toBeTruthy();
    fireEvent.click(canvas, { clientX: 400, clientY: 260 });
    expect(screen.queryByTestId("marker-row-3")).toBeNull();
  });

  it("drags a marker along the outline", async () => {
    await open();
    const canvas = sizeCanvas();
    fireEvent.pointerDown(screen.getByTestId("editor-marker-1").querySelectorAll("g")[0], { clientX: projected[15].x, clientY: projected[15].y });
    fireEvent.pointerMove(canvas, { clientX: projected[100].x, clientY: projected[100].y });
    fireEvent.pointerUp(canvas);
    vi.mocked(api.put).mockResolvedValue(makePayload());
    fireEvent.click(screen.getByTestId("editor-save-btn"));
    await waitFor(() => expect(api.put).toHaveBeenCalled());
    expect((vi.mocked(api.put).mock.calls[0][1] as { markers: { center_index: number }[] }).markers[0].center_index).toBe(100);
  });

  it("blocks saving for a bad limit and explains why", async () => {
    await open();
    fireEvent.change(screen.getByTestId("marker-limit-1"), { target: { value: "1.9" } });
    expect((screen.getByTestId("editor-save-btn") as HTMLButtonElement).disabled).toBe(true);
    expect(screen.getByTestId("marker-problem-1").textContent).toContain("Limit");
    expect(screen.getByTestId("editor-blocker").textContent).toContain("Cannot save yet");
  });

  it("saves the markers with the outline version and shows what the server did", async () => {
    await open();
    fireEvent.change(screen.getByTestId("marker-name-1"), { target: { value: "Big Hairpin" } });
    fireEvent.click(screen.getByTestId("editor-suggestion-80"));
    vi.mocked(api.put).mockResolvedValue(makePayload({ saved: { created: 1, updated: 1, deleted: 0, deactivated: 1 } }));
    fireEvent.click(screen.getByTestId("editor-save-btn"));
    await waitFor(() => expect(screen.getByTestId("editor-saved")).toBeTruthy());
    const [url, body] = vi.mocked(api.put).mock.calls[0] as [string, { outline_version: string; markers: Record<string, unknown>[] }];
    expect(url).toBe("/api/tracks/t1/corners/");
    expect(body.outline_version).toBe("v1");
    expect(body.markers).toEqual([
      { id: "z1", label: "Big Hairpin", threshold_g: 1.2, center_index: 15, length_m: 30 },
      { id: null, label: "Turn 2", threshold_g: 1.25, center_index: 80, length_m: 30 },
    ]);
    expect(screen.getByTestId("editor-saved").textContent).toContain("1 hidden");
  });

  it("removes a marker and shows the server's error when the save is refused", async () => {
    const { onChanged } = await open();
    fireEvent.click(screen.getByTestId("marker-remove-1"));
    expect(screen.getByTestId("editor-no-markers")).toBeTruthy();
    vi.mocked(api.put).mockRejectedValue(new Error("This map's outline changed since you opened it."));
    fireEvent.click(screen.getByTestId("editor-save-btn"));
    await waitFor(() => expect(screen.getByTestId("editor-error").textContent).toContain("outline changed"));
    expect(onChanged).not.toHaveBeenCalled();
  });

  it("asks before closing with unsaved changes", async () => {
    const { onClose } = await open();
    fireEvent.change(screen.getByTestId("marker-name-1"), { target: { value: "Changed" } });
    fireEvent.click(screen.getByLabelText("Close"));
    expect(onClose).not.toHaveBeenCalled();
    fireEvent.click(screen.getByTestId("confirm-dialog-confirm-btn"));
    expect(onClose).toHaveBeenCalled();
  });
});

describe("CornerEditorDialog (view-only)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.get).mockResolvedValue(makePayload({ editable: false, is_schematic: true, suggestions: [] }));
  });

  it("shows the Demo Circuit's corners read-only with the schematic note and no save button", async () => {
    render(<CornerEditorDialog map={map({ name: "Demo Circuit", is_builtin: true })} onClose={vi.fn()} onChanged={vi.fn()} />);
    await waitFor(() => expect(screen.getByTestId("editor-schematic-note")).toBeTruthy());
    expect(screen.queryByTestId("marker-name-1")).toBeNull();
    expect(screen.queryByTestId("editor-save-btn")).toBeNull();
    expect(screen.getByTestId("editor-help").textContent).toContain("view-only");
    fireEvent.click(sizeCanvas(), { clientX: projected[60].x, clientY: projected[60].y });
    expect(screen.queryByTestId("marker-row-2")).toBeNull();
  });

  it("duplicates the Demo Circuit as a custom map and reports clamped limits", async () => {
    const onChanged = vi.fn();
    const onClose = vi.fn();
    vi.mocked(api.post).mockResolvedValue({ clamped: [{ label: "Sweeper", from_g: 1.55, to_g: 1.5 }] });
    render(<CornerEditorDialog map={map({ name: "Demo Circuit", is_builtin: true })} onClose={onClose} onChanged={onChanged} />);
    await waitFor(() => expect(screen.getByTestId("duplicate-btn")).toBeTruthy());
    fireEvent.change(screen.getByTestId("duplicate-name-input"), { target: { value: "My Copy" } });
    fireEvent.click(screen.getByTestId("duplicate-btn"));
    await waitFor(() => expect(onChanged).toHaveBeenCalled());
    expect(api.post).toHaveBeenCalledWith("/api/tracks/t1/duplicate/", { name: "My Copy" });
    expect(onChanged.mock.calls[0][0]).toContain("Sweeper limit 1.55 g became 1.5 g");
    expect(onClose).toHaveBeenCalled();
  });

  it("shows the server's message when the copy name is taken", async () => {
    vi.mocked(api.post).mockRejectedValue(new Error("A map with this name already exists."));
    render(<CornerEditorDialog map={map({ is_builtin: true })} onClose={vi.fn()} onChanged={vi.fn()} />);
    await waitFor(() => expect(screen.getByTestId("duplicate-btn")).toBeTruthy());
    fireEvent.click(screen.getByTestId("duplicate-btn"));
    await waitFor(() => expect(screen.getByTestId("duplicate-error").textContent).toContain("already exists"));
  });

  it("archived maps are view-only without the duplicate form", async () => {
    render(<CornerEditorDialog map={map({ is_archived: true })} onClose={vi.fn()} onChanged={vi.fn()} />);
    await waitFor(() => expect(screen.getByTestId("editor-help").textContent).toContain("archived"));
    expect(screen.queryByTestId("duplicate-btn")).toBeNull();
  });
});
