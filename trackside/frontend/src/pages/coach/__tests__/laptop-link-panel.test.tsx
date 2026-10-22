/**
 * Trackside — Laptop link panel (Coach)
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { LaptopLinkPanel } from "../components/laptop-link-panel";

vi.mock("../../../lib/api", () => ({ api: { get: vi.fn(), post: vi.fn() } }));

import { api } from "../../../lib/api";
const mockGet = vi.mocked(api.get);
const mockPost = vi.mocked(api.post);

const started = {
  session_id: "s1", driver_id: "d1", driver_name: "Ana", backend_url: "https://site.example",
  device_token: "dt_secret123", zones: { Hairpin: "z1", Sweeper: "z2", Chicane: "z3" },
};

/** Roster for the driver list, and the link status the test wants. */
function answers(state: string) {
  mockGet.mockImplementation(async (url: string) => {
    if (url.includes("roster-status")) return { roster: [{ driver_id: "d1", driver_name: "Ana", is_active: true }] };
    return { state, driver_id: "d1", driver_name: "Ana", readings: 0 };
  });
}

describe("LaptopLinkPanel", () => {
  beforeEach(() => vi.clearAllMocks());

  it("starts a link for the chosen driver and shows the lines with the token hidden until asked", async () => {
    answers("idle");
    mockPost.mockResolvedValue(started);
    render(<LaptopLinkPanel onWatchLive={() => {}} />);
    await waitFor(() => expect(screen.getByText("Ana")).toBeDefined());
    fireEvent.change(screen.getByTestId("laptop-link-driver"), { target: { value: "d1" } });
    answers("waiting");
    fireEvent.click(screen.getByTestId("laptop-link-start"));
    await waitFor(() => expect(screen.getByTestId("laptop-link-env")).toBeDefined());
    expect(mockPost).toHaveBeenCalledWith("/api/laptop-link/start/", { driver_id: "d1" });
    const text = screen.getByTestId("laptop-link-env").textContent ?? "";
    expect(text).toContain("BACKEND_URL=https://site.example");
    expect(text).toContain("SESSION_ID=s1");
    expect(text).toContain("DEMO_ZONES=");
    expect(text).not.toContain("dt_secret123");
    fireEvent.click(screen.getByText("Show token"));
    expect(screen.getByTestId("laptop-link-env").textContent).toContain("DEVICE_TOKEN=dt_secret123");
  });

  it("shows the state, offers Watch live for the linked driver and ends the link", async () => {
    answers("receiving");
    mockPost.mockResolvedValue({ state: "idle" });
    const onWatchLive = vi.fn();
    render(<LaptopLinkPanel onWatchLive={onWatchLive} />);
    await waitFor(() => expect(screen.getByTestId("laptop-link-state").textContent).toContain("Receiving readings"));
    fireEvent.click(screen.getByTestId("laptop-link-watch"));
    expect(onWatchLive).toHaveBeenCalledWith("d1");
    answers("idle");
    fireEvent.click(screen.getByTestId("laptop-link-stop"));
    await waitFor(() => expect(mockPost).toHaveBeenCalledWith("/api/laptop-link/stop/"));
  });

  it("shows the server's message when the link cannot start", async () => {
    answers("idle");
    mockPost.mockRejectedValue(new Error("Ana already has Real kart."));
    render(<LaptopLinkPanel onWatchLive={() => {}} />);
    await waitFor(() => expect(screen.getByText("Ana")).toBeDefined());
    fireEvent.change(screen.getByTestId("laptop-link-driver"), { target: { value: "d1" } });
    fireEvent.click(screen.getByTestId("laptop-link-start"));
    await waitFor(() => expect(screen.getByTestId("laptop-link-error").textContent).toContain("already has Real kart"));
  });
});
