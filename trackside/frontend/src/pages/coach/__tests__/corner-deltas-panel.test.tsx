/**
 * Trackside — Corner deltas panel (coach) and corner times table (driver)
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, act } from "@testing-library/react";
import { CornerDeltasPanel } from "../components/corner-deltas-panel";
import { CornerTimesPanel } from "../../driver/components/corner-times-panel";

vi.mock("../../../lib/api", () => ({ api: { get: vi.fn() } }));

import { api } from "../../../lib/api";
const mockGet = vi.mocked(api.get);

const corner = (label: string, last: number | null, delta: number | null, best: number | null) => ({
  zone_id: label, label, best_s: best, last_lap_s: last, last_lap_delta_s: delta, laps: [],
});

describe("CornerDeltasPanel", () => {
  beforeEach(() => vi.clearAllMocks());
  afterEach(() => vi.useRealTimers());

  it("shows the heading, one row per corner, coloured deltas and dashes for missing values", async () => {
    mockGet.mockResolvedValue({ corners: [corner("Hairpin", 1.5, 0, 1.5), corner("Sweeper", 2.0, 0.5, 1.5), corner("Chicane", 1.2, null, 1.2)] });
    render(<CornerDeltasPanel sessionId="s1" lapNumber={2} isLive={false} />);
    await waitFor(() => expect(screen.getByTestId("corner-delta-row-Hairpin")).toBeDefined());
    expect(screen.getByText(/CORNER DELTAS vs SESSION BEST/)).toBeDefined();
    const delta = (name: string) => screen.getByTestId(`corner-delta-row-${name}`).querySelectorAll("td")[2] as HTMLElement;
    expect(delta("Hairpin").textContent).toBe("0.000");
    expect(delta("Hairpin").style.color).toBe("rgb(51, 209, 126)");
    expect(delta("Sweeper").textContent).toBe("+0.500");
    expect(delta("Sweeper").style.color).toBe("rgb(242, 169, 59)");
    expect(delta("Chicane").textContent).toBe("—");
    expect(screen.getByText("Sector split timing (GPS split lines) is Phase 2.")).toBeDefined();
  });

  it("says it is waiting when no corner has a completed lap, and never invents numbers", async () => {
    mockGet.mockResolvedValue({ corners: [corner("Hairpin", null, null, null)] });
    render(<CornerDeltasPanel sessionId="s1" lapNumber={1} isLive={false} />);
    await waitFor(() => expect(screen.getByText("Waiting for completed laps")).toBeDefined());
    expect(screen.queryByTestId("corner-delta-row-Hairpin")).toBeNull();
  });

  it("asks nothing without a session", () => {
    render(<CornerDeltasPanel sessionId={null} lapNumber={null} isLive />);
    expect(mockGet).not.toHaveBeenCalled();
  });

  it("reloads when the lap number changes", async () => {
    mockGet.mockResolvedValue({ corners: [] });
    const { rerender } = render(<CornerDeltasPanel sessionId="s1" lapNumber={1} isLive={false} />);
    await waitFor(() => expect(mockGet).toHaveBeenCalledTimes(1));
    rerender(<CornerDeltasPanel sessionId="s1" lapNumber={2} isLive={false} />);
    await waitFor(() => expect(mockGet).toHaveBeenCalledTimes(2));
  });

  it("reloads every 5 seconds only while the session is live", async () => {
    vi.useFakeTimers();
    mockGet.mockResolvedValue({ corners: [] });
    const { rerender } = render(<CornerDeltasPanel sessionId="s1" lapNumber={1} isLive />);
    await act(async () => { await vi.advanceTimersByTimeAsync(10100); });
    expect(mockGet).toHaveBeenCalledTimes(3);
    mockGet.mockClear();
    rerender(<CornerDeltasPanel sessionId="s1" lapNumber={1} isLive={false} />);
    await act(async () => { await vi.advanceTimersByTimeAsync(10100); });
    expect(mockGet.mock.calls.length).toBe(1);
  });
});

describe("CornerTimesPanel (driver)", () => {
  beforeEach(() => vi.clearAllMocks());

  it("shows last lap and best per corner, with dashes for missing values", async () => {
    mockGet.mockResolvedValue({ corners: [corner("Hairpin", 1.5, 0, 1.25), corner("Sweeper", null, null, null)] });
    render(<CornerTimesPanel sessionId="s1" />);
    await waitFor(() => expect(screen.getByTestId("corner-time-row-Hairpin")).toBeDefined());
    expect(screen.getByTestId("corner-time-row-Hairpin").textContent).toContain("1.500 s");
    expect(screen.getByTestId("corner-time-row-Hairpin").textContent).toContain("1.250 s");
    const cells = Array.from(screen.getByTestId("corner-time-row-Sweeper").querySelectorAll("td")).map((c) => c.textContent);
    expect(cells).toEqual(["Sweeper", "—", "—"]);
  });

  it("shows a dash when there is no session or no corners", () => {
    render(<CornerTimesPanel sessionId={null} />);
    expect(screen.getByText("—")).toBeDefined();
  });
});
