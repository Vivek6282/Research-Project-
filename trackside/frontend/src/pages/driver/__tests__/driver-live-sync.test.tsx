/**
 * Trackside Driver — the driver screen follows a run the coach starts later (laps, alerts, live readings).
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { act, render, renderHook, screen } from "@testing-library/react";

vi.mock("../../../lib/api", () => ({ api: { get: vi.fn() } }));
import { api } from "../../../lib/api";
import { SUMMARY_REFRESH_MS, useDriverDashboard } from "../hooks/use-driver-dashboard";
import { SessionStatusPanel } from "../components/session-status-panel";
import { TelemetryPanel } from "../components/telemetry-panel";

const mockGet = vi.mocked(api.get);
const NONE = { has_sessions: false, total_sessions: 0, zones: [], latest_session: null };
const RUN = {
  id: "s1", mode: "safety", goal_text: "", goal_passed: null, started_at: "2026-10-23T10:00:00Z",
  track_name: "Kari", best_lap_time: null, is_demo: true, ended_at: null, live: true, laps: 1, alert_count: 0, duration: "In progress", max_g: 0.5,
};

/** A WebSocket stand-in the test can push messages into. */
class FakeSocket {
  static all: FakeSocket[] = [];
  onmessage: ((e: { data: string }) => void) | null = null;
  onclose: (() => void) | null = null;
  onerror: ((e: unknown) => void) | null = null;
  constructor(public url: string) { FakeSocket.all.push(this); }
  close() {}
  send(message: unknown) {
    this.onmessage?.({ data: JSON.stringify(message) });
  }
}

/** Let the pending promises and the timers run for the given milliseconds. */
async function pass(ms: number) {
  await act(async () => { await vi.advanceTimersByTimeAsync(ms); });
}

describe("Driver screen follows the coach's run", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    FakeSocket.all = [];
    vi.stubGlobal("WebSocket", FakeSocket as unknown as typeof WebSocket);
  });
  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
    mockGet.mockReset();
  });

  it("picks up a run started after the page was opened, with its laps and alerts", async () => {
    mockGet.mockResolvedValue(NONE);
    const { result } = renderHook(() => useDriverDashboard());
    await pass(10);
    expect(result.current.latestSession).toBeNull();

    mockGet.mockResolvedValue({ has_sessions: true, total_sessions: 1, zones: [], latest_session: RUN });
    await pass(SUMMARY_REFRESH_MS + 10);
    expect(result.current.latestSession?.id).toBe("s1");
    expect(FakeSocket.all.at(-1)?.url).toContain("/ws/sessions/s1/telemetry/");

    mockGet.mockResolvedValue({ has_sessions: true, total_sessions: 1, zones: [], latest_session: { ...RUN, laps: 3, alert_count: 2 } });
    await pass(SUMMARY_REFRESH_MS + 10);
    expect(result.current.latestSession?.laps).toBe(3);
    expect(result.current.latestSession?.alert_count).toBe(2);
  });

  it("shows the live reading, its corner, limit and stage, then clears them when the run ends", async () => {
    mockGet.mockResolvedValue({ has_sessions: true, total_sessions: 1, zones: [], latest_session: RUN });
    const { result } = renderHook(() => useDriverDashboard());
    await pass(10);
    act(() => FakeSocket.all.at(-1)!.send({
      type: "telemetry_reading", data: { lateral_g: 0.93, zone_label: "Hairpin", threshold: 1.0, stage: "monitoring" },
    }));
    expect(result.current.currentG).toBe(0.93);
    expect(result.current.activeZone).toBe("Hairpin");
    expect(result.current.activeThreshold).toBe(1.0);
    expect(result.current.liveStage).toBe("monitoring");

    mockGet.mockResolvedValue({ has_sessions: true, total_sessions: 1, zones: [], latest_session: { ...RUN, live: false, ended_at: "2026-10-23T10:05:00Z" } });
    await pass(SUMMARY_REFRESH_MS + 10);
    expect(result.current.currentG).toBeNull();
    expect(result.current.activeZone).toBeNull();
    expect(result.current.liveStage).toBeNull();
  });
});

describe("Driver session and telemetry panels", () => {
  it("shows state, laps, alerts and duration of the latest run", () => {
    render(<SessionStatusPanel latestSession={{ ...RUN, laps: 4, alert_count: 3, duration: "6 min" }} />);
    expect(screen.getByTestId("driver-session-state").textContent).toBe("LIVE");
    expect(screen.getByTestId("driver-session-laps").textContent).toBe("4");
    expect(screen.getByTestId("driver-session-alerts").textContent).toBe("3");
    expect(screen.getByTestId("driver-session-duration").textContent).toBe("6 min");
  });

  it("says ENDED for a finished run and explains an empty state", () => {
    const { rerender } = render(<SessionStatusPanel latestSession={{ ...RUN, live: false, ended_at: "2026-10-23T10:05:00Z" }} />);
    expect(screen.getByTestId("driver-session-state").textContent).toBe("ENDED");
    rerender(<SessionStatusPanel latestSession={null} />);
    expect(screen.getByText(/appears here when the coach starts a run/i)).toBeTruthy();
  });

  it("lights the glove strip from the server's stage and the corner's own limit", () => {
    render(<TelemetryPanel currentG={0.45} activeThreshold={0.5} activeZone="Hairpin" stage="monitoring" />);
    expect(screen.getByTestId("driver-signal-strip-stage-label").textContent).toBe("Monitoring");
    expect(screen.getByText(/0.50 g THRESHOLD/)).toBeTruthy();
  });
});
