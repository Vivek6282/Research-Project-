/**
 * Trackside — Real-time (phone) session panel (Coach, Phase 2.1)
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";

vi.mock("../../../lib/api", () => ({ api: { get: vi.fn(), post: vi.fn() } }));

import { api } from "../../../lib/api";
import { RealTimeSessionPanel } from "../components/real-time-session-panel";

const mockGet = vi.mocked(api.get);
const mockPost = vi.mocked(api.post);
const outline = Array.from({ length: 60 }, (_, i) => ({ lat: 10 + i / 1e5, lng: 76 }));

/** Roster, maps (one GPS map, one built-in, one without outline) and sessions. */
function answers(sessions: unknown[]) {
  mockGet.mockImplementation(async (url: string) => {
    if (url.includes("roster-status")) return { roster: [{ driver_id: "d1", driver_name: "Ana", is_active: true }] };
    if (url.startsWith("/api/tracks/")) return [
      { id: "t1", name: "Kart Park", is_builtin: false, is_archived: false, reference_line: outline },
      { id: "t2", name: "Demo Circuit", is_builtin: true, is_archived: false, reference_line: null },
      { id: "t3", name: "Blank", is_builtin: false, is_archived: false, reference_line: null },
    ];
    return sessions;
  });
}

describe("RealTimeSessionPanel", () => {
  beforeEach(() => vi.clearAllMocks());

  it("offers only GPS maps and starts a real-time session for the chosen driver", async () => {
    answers([]);
    mockPost.mockResolvedValue({});
    const watch = vi.fn();
    render(<RealTimeSessionPanel onWatchLive={watch} />);
    await waitFor(() => expect(screen.getByText("Kart Park")).toBeDefined());
    expect(screen.queryByText("Demo Circuit")).toBeNull();
    expect(screen.queryByText("Blank")).toBeNull();
    fireEvent.change(screen.getByTestId("real-time-driver"), { target: { value: "d1" } });
    fireEvent.change(screen.getByTestId("real-time-map"), { target: { value: "t1" } });
    fireEvent.click(screen.getByTestId("real-time-start"));
    await waitFor(() => expect(watch).toHaveBeenCalledWith("d1"));
    expect(mockPost.mock.calls[0][0]).toBe("/api/sessions/");
    expect(mockPost.mock.calls[0][1]).toMatchObject({ driver: "d1", track: "t1", data_source: "real_time" });
  });

  it("lists running real-time sessions with the phone's warnings and finishes one", async () => {
    answers([
      { id: "s1", driver: "d1", driver_name: "Ana", track_name: "Kart Park", started_at: "2026-10-24T10:00:00Z", ended_at: null,
        data_source: "real_time", sensor_flags: ["mount_moved"] },
      { id: "s2", driver: "d1", driver_name: "Ana", track_name: "Kart Park", started_at: "2026-10-24T09:00:00Z", ended_at: null,
        data_source: "simulator" },
    ]);
    mockPost.mockResolvedValue({});
    render(<RealTimeSessionPanel onWatchLive={() => {}} />);
    await waitFor(() => expect(screen.getAllByTestId("real-time-row")).toHaveLength(1));
    expect(screen.getByText(/phone moved in its mount/)).toBeDefined();
    fireEvent.click(screen.getByTestId("real-time-finish"));
    await waitFor(() => expect(mockPost).toHaveBeenCalledWith("/api/sessions/s1/finish/"));
  });
});
