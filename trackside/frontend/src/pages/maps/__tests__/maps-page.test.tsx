/**
 * Trackside Maps — page tests: who sees the Add map button, and archive/restore wiring.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

vi.mock("../../../lib/api", () => ({ api: { get: vi.fn(), delete: vi.fn(), post: vi.fn(), upload: vi.fn() } }));
vi.mock("../../../components/shell/top-bar", () => ({ TopBar: () => <div data-testid="topbar" /> }));
const authState: { user: { role: string } | null } = { user: { role: "coach" } };
vi.mock("../../../lib/auth", () => ({ useAuth: () => authState }));

import { api } from "../../../lib/api";
import { MapsPage } from "../index";
const mockGet = vi.mocked(api.get);

const RESULT = {
  results: [
    { id: "d", name: "Demo Circuit", source: "builtin", is_builtin: true, is_archived: false, zones: [] },
    { id: "k", name: "Kari", source: "vbo", is_builtin: false, is_archived: false, zones: [{ id: "z", label: "T1", threshold_g: 1.2 }] },
  ],
};

/** Render the page inside a router. */
function renderPage() {
  return render(<MemoryRouter><MapsPage /></MemoryRouter>);
}

describe("MapsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGet.mockResolvedValue(RESULT);
  });

  it("lets a coach add and archive maps", async () => {
    authState.user = { role: "coach" };
    renderPage();
    await waitFor(() => expect(screen.getByTestId("map-list")).toBeTruthy());
    expect(screen.getByTestId("add-map-btn")).toBeTruthy();
    expect(screen.getByTestId("archive-Kari")).toBeTruthy();
    expect(screen.queryByTestId("archive-Demo Circuit")).toBeNull();
  });

  it("shows a driver the maps but no way to change them", async () => {
    authState.user = { role: "driver" };
    renderPage();
    await waitFor(() => expect(screen.getByTestId("map-list")).toBeTruthy());
    expect(screen.queryByTestId("add-map-btn")).toBeNull();
    expect(screen.queryByTestId("archive-Kari")).toBeNull();
  });

  it("asks for the archived list with ?archived=only", async () => {
    authState.user = { role: "admin" };
    renderPage();
    await waitFor(() => expect(mockGet).toHaveBeenCalledWith("/api/tracks/"));
    fireEvent.click(screen.getByTestId("maps-tab-archived"));
    await waitFor(() => expect(mockGet).toHaveBeenCalledWith("/api/tracks/?archived=only"));
  });

  it("archives after the user confirms, then reloads", async () => {
    authState.user = { role: "admin" };
    vi.mocked(api.delete).mockResolvedValueOnce({ detail: "Map archived. Its session history is kept." });
    renderPage();
    await waitFor(() => expect(screen.getByTestId("archive-Kari")).toBeTruthy());
    fireEvent.click(screen.getByTestId("archive-Kari"));
    fireEvent.click(screen.getByTestId("confirm-dialog-confirm-btn"));
    await waitFor(() => expect(api.delete).toHaveBeenCalledWith("/api/tracks/k/"));
    await waitFor(() => expect(screen.getByTestId("maps-notice").textContent).toContain("archived"));
  });

  it("shows an error instead of an empty list when loading fails", async () => {
    authState.user = { role: "coach" };
    mockGet.mockRejectedValueOnce(new Error("Server unavailable"));
    renderPage();
    await waitFor(() => expect(screen.getByTestId("maps-error").textContent).toContain("Server unavailable"));
  });
});
