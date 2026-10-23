/**
 * Trackside Maps — the "Draw on map" button: shown to people who manage maps, opens the wizard, and the old
 * "Add track" upload stays beside it.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";

vi.mock("../../../lib/api", () => ({ api: { get: vi.fn(), delete: vi.fn(), post: vi.fn(), upload: vi.fn() } }));
vi.mock("../components/draw-map-canvas", () => ({ default: () => <div data-testid="draw-map-stub" /> }));

import { api } from "../../../lib/api";
import { MapsBrowser } from "../components/maps-browser";

describe("Draw on map button", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.get).mockResolvedValue({ results: [] });
    vi.mocked(api.post).mockResolvedValue({});
  });

  it("people who manage maps see Draw on map and Add track side by side, and the button opens the drawing wizard", async () => {
    render(<MapsBrowser canManage />);
    fireEvent.click(await screen.findByTestId("draw-map-btn"));
    expect(screen.getByTestId("add-map-btn")).toBeDefined();
    expect(await screen.findByTestId("draw-map-wizard")).toBeDefined();
    expect(await screen.findByTestId("draw-map-stub")).toBeDefined();
    fireEvent.click(screen.getByLabelText("Close"));
    expect(screen.queryByTestId("draw-map-wizard")).toBeNull();
  });

  it("people who only look at maps see neither button", async () => {
    render(<MapsBrowser canManage={false} />);
    await screen.findByTestId("maps-browser");
    expect(screen.queryByTestId("draw-map-btn")).toBeNull();
    expect(screen.queryByTestId("add-map-btn")).toBeNull();
  });
});
