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
  session_id: "s1", driver_id: "d1", driver_name: "Ana", track_id: "m1", track_name: "Sim Map", backend_url: "https://site.example",
  device_token: "dt_secret123", zones: { Hairpin: "z1", Sweeper: "z2", Chicane: "z3" },
};

const ZONES = ["Hairpin", "Sweeper", "Chicane"].map((label, i) => ({ id: `z${i}`, label, threshold_g: 1.2 }));
const MAPS = [
  { id: "m1", name: "Sim Map", source: "drawn", is_archived: false, zones: ZONES },
  { id: "m2", name: "Two Corners", source: "drawn", is_archived: false, zones: ZONES.slice(0, 2) },
];

/** Roster for the driver list, and the link status the test wants. */
function answers(state: string) {
  mockGet.mockImplementation(async (url: string) => {
    if (url.includes("roster-status")) return { roster: [{ driver_id: "d1", driver_name: "Ana", is_active: true }] };
    if (url === "/api/tracks/") return { results: MAPS };
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
    await waitFor(() => expect(screen.getByText("Sim Map")).toBeDefined());
    fireEvent.change(screen.getByTestId("laptop-link-driver"), { target: { value: "d1" } });
    fireEvent.change(screen.getByTestId("laptop-link-map"), { target: { value: "m1" } });
    answers("waiting");
    fireEvent.click(screen.getByTestId("laptop-link-start"));
    await waitFor(() => expect(screen.getByTestId("laptop-link-env")).toBeDefined());
    expect(mockPost).toHaveBeenCalledWith("/api/laptop-link/start/", { driver_id: "d1", track_id: "m1" });
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
    await waitFor(() => expect(screen.getByText("Sim Map")).toBeDefined());
    fireEvent.change(screen.getByTestId("laptop-link-driver"), { target: { value: "d1" } });
    fireEvent.change(screen.getByTestId("laptop-link-map"), { target: { value: "m1" } });
    fireEvent.click(screen.getByTestId("laptop-link-start"));
    await waitFor(() => expect(screen.getByTestId("laptop-link-error").textContent).toContain("already has Real kart"));
  });

  it("needs a map as well as a driver, and warns when the map lacks the simulator's corners", async () => {
    answers("idle");
    render(<LaptopLinkPanel onWatchLive={() => {}} />);
    await waitFor(() => expect(screen.getByText("Sim Map")).toBeDefined());
    fireEvent.change(screen.getByTestId("laptop-link-driver"), { target: { value: "d1" } });
    expect((screen.getByTestId("laptop-link-start") as HTMLButtonElement).disabled).toBe(true);
    fireEvent.change(screen.getByTestId("laptop-link-map"), { target: { value: "m1" } });
    expect((screen.getByTestId("laptop-link-start") as HTMLButtonElement).disabled).toBe(false);
    expect(screen.queryByTestId("laptop-link-missing")).toBeNull();
    fireEvent.change(screen.getByTestId("laptop-link-map"), { target: { value: "m2" } });
    expect(screen.getByTestId("laptop-link-missing").textContent).toContain("no corner called Chicane");
  });

  it("says so when there are no maps yet", async () => {
    mockGet.mockImplementation(async (url: string) => (url === "/api/tracks/" ? { results: [] } : url.includes("roster-status") ? { roster: [] } : { state: "idle" }));
    render(<LaptopLinkPanel onWatchLive={() => {}} />);
    await waitFor(() => expect(screen.getByTestId("laptop-link-no-maps")).toBeDefined());
  });
});
