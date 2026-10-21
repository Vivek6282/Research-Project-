/**
 * Trackside Maps — page tests: who sees what on /maps, and the shared browser behaviour.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";

vi.mock("../../../lib/api", () => ({ api: { get: vi.fn(), delete: vi.fn(), post: vi.fn(), upload: vi.fn() } }));
vi.mock("../../../components/shell/top-bar", () => ({ TopBar: () => <div data-testid="topbar" /> }));
const authState: { user: { role: string } | null } = { user: { role: "admin" } };
vi.mock("../../../lib/auth", () => ({ useAuth: () => authState }));

import { api } from "../../../lib/api";
import { MapsPage } from "../index";
import { MapsBrowser } from "../components/maps-browser";
const mockGet = vi.mocked(api.get);
const mockPost = vi.mocked(api.post);

const RESULT = {
  results: [
    { id: "k", name: "Kari", source: "vbo", is_builtin: false, is_archived: false, zones: [{ id: "z", label: "T1", threshold_g: 1.2 }] },
    { id: "d", name: "Demo Circuit", source: "builtin", is_builtin: true, is_archived: false, zones: [], is_schematic: true },
  ],
};

/** Render the Maps page where a Coach would be redirected to the tab. */
function renderPage() {
  return render(
    <MemoryRouter initialEntries={["/maps"]}>
      <Routes>
        <Route path="/maps" element={<MapsPage />} />
        <Route path="/coach" element={<div data-testid="coach-screen" />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("MapsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGet.mockResolvedValue(RESULT);
    mockPost.mockResolvedValue({});
  });

  it("lets an admin add and archive maps but gives no Play button", async () => {
    authState.user = { role: "admin" };
    renderPage();
    await waitFor(() => expect(screen.getByTestId("map-list")).toBeTruthy());
    expect(screen.getByTestId("add-map-btn")).toBeTruthy();
    expect(screen.getByTestId("archive-Kari")).toBeTruthy();
    expect(screen.queryByTestId("archive-Demo Circuit")).toBeNull();
    expect(screen.queryByTestId("play-Kari")).toBeNull();
  });

  it("shows a driver the maps but no way to change them, and never asks to create the Demo Circuit", async () => {
    authState.user = { role: "driver" };
    renderPage();
    await waitFor(() => expect(screen.getByTestId("map-list")).toBeTruthy());
    expect(screen.queryByTestId("add-map-btn")).toBeNull();
    expect(screen.queryByTestId("archive-Kari")).toBeNull();
    expect(mockPost).not.toHaveBeenCalled();
  });

  it("sends a coach to the Maps & Demo tab", async () => {
    authState.user = { role: "coach" };
    renderPage();
    await waitFor(() => expect(screen.getByTestId("coach-screen")).toBeTruthy());
  });
});

describe("MapsBrowser", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGet.mockResolvedValue(RESULT);
    mockPost.mockResolvedValue({});
  });

  it("lists the Demo Circuit first and makes sure it exists before listing", async () => {
    render(<MapsBrowser canManage />);
    await waitFor(() => expect(screen.getByTestId("map-list")).toBeTruthy());
    expect(mockPost).toHaveBeenCalledWith("/api/tracks/demo-circuit/");
    const names = screen.getAllByTestId(/^map-card-(?!corners)/).map((el) => el.getAttribute("data-testid"));
    expect(names).toEqual(["map-card-Demo Circuit", "map-card-Kari"]);
  });

  it("asks for the archived list with ?archived=only and shows Restore", async () => {
    mockGet.mockImplementation(async (url: string) =>
      url.includes("archived=only")
        ? { results: [{ id: "a", name: "Old", source: "vbo", is_builtin: false, is_archived: true, zones: [] }] }
        : RESULT);
    render(<MapsBrowser canManage />);
    await waitFor(() => expect(mockGet).toHaveBeenCalledWith("/api/tracks/"));
    fireEvent.click(screen.getByTestId("maps-tab-archived"));
    await waitFor(() => expect(mockGet).toHaveBeenCalledWith("/api/tracks/?archived=only"));
    await waitFor(() => expect(screen.getByTestId("restore-Old")).toBeTruthy());
  });

  it("archives after the user confirms, then reloads", async () => {
    vi.mocked(api.delete).mockResolvedValueOnce({ detail: "Map archived. Its session history is kept." });
    render(<MapsBrowser canManage />);
    await waitFor(() => expect(screen.getByTestId("archive-Kari")).toBeTruthy());
    fireEvent.click(screen.getByTestId("archive-Kari"));
    fireEvent.click(screen.getByTestId("confirm-dialog-confirm-btn"));
    await waitFor(() => expect(api.delete).toHaveBeenCalledWith("/api/tracks/k/"));
    await waitFor(() => expect(screen.getByTestId("maps-notice").textContent).toContain("archived"));
  });

  it("restores an archived map", async () => {
    mockGet.mockResolvedValue({ results: [{ id: "a", name: "Old", source: "vbo", is_builtin: false, is_archived: true, zones: [] }] });
    render(<MapsBrowser canManage />);
    fireEvent.click(screen.getByTestId("maps-tab-archived"));
    await waitFor(() => expect(screen.getByTestId("restore-Old")).toBeTruthy());
    fireEvent.click(screen.getByTestId("restore-Old"));
    await waitFor(() => expect(mockPost).toHaveBeenCalledWith("/api/tracks/a/restore/"));
  });

  it("opens the Add track wizard", async () => {
    render(<MapsBrowser canManage />);
    await waitFor(() => expect(screen.getByTestId("add-map-btn")).toBeTruthy());
    fireEvent.click(screen.getByTestId("add-map-btn"));
    expect(screen.getByTestId("add-map-wizard")).toBeTruthy();
  });

  it("shows an error instead of an empty list when loading fails", async () => {
    mockGet.mockRejectedValueOnce(new Error("Server unavailable"));
    render(<MapsBrowser canManage />);
    await waitFor(() => expect(screen.getByTestId("maps-error").textContent).toContain("Server unavailable"));
  });

  it("passes Play and Edit corners handlers to the cards", async () => {
    const onPlay = vi.fn();
    const onEdit = vi.fn();
    render(<MapsBrowser canManage onPlay={onPlay} onEditCorners={onEdit} />);
    await waitFor(() => expect(screen.getByTestId("play-Kari")).toBeTruthy());
    fireEvent.click(screen.getByTestId("play-Kari"));
    fireEvent.click(screen.getByTestId("edit-corners-Demo Circuit"));
    expect(onPlay).toHaveBeenCalledWith(expect.objectContaining({ id: "k" }));
    expect(onEdit).toHaveBeenCalledWith(expect.objectContaining({ id: "d" }));
  });
});
