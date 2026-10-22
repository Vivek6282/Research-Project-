/**
 * Trackside Coach — demo availability, status panel, Play dialog and the Maps & Demo tab wiring (H2, H4).
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { act, fireEvent, render, renderHook, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

vi.mock("../../../lib/api", () => ({ api: { get: vi.fn(), post: vi.fn(), delete: vi.fn(), upload: vi.fn(), put: vi.fn() } }));
import { api } from "../../../lib/api";
import { DemoStatusPanel } from "../components/demo-status-panel";
import { MapsDemoTab } from "../components/maps-demo-tab";
import { useDemoRun, type DemoStatus } from "../hooks/use-demo-run";
import { PlayDemoDialog } from "../../maps/components/play-demo-dialog";

const mockGet = vi.mocked(api.get);
const mockPost = vi.mocked(api.post);
const RUN = { session_id: "s1", driver_id: "d1", driver_name: "Ana Driver", track_id: "t1", track_name: "Kari", laps: 5, pace: "edge", pace_applied: true, built_in: false };
const IDLE: DemoStatus = { running: false, state: "idle", laps: null, current_lap: null, bridge_connected: null, port_hint: null, last_lines: [], error: null, run: null };
const RUNNING: DemoStatus = { ...IDLE, running: true, state: "running", laps: 5, current_lap: 2, run: RUN };
const MAPS = { results: [
  { id: "d", name: "Demo Circuit", source: "builtin", is_builtin: true, is_archived: false, zones: [] },
  { id: "t1", name: "Kari", source: "vbo", is_builtin: false, is_archived: false, zones: [{ id: "z", label: "T1", threshold_g: 1.2 }] },
] };
const ROSTER = { roster: [
  { driver_id: "d1", driver_name: "Ana Driver", is_active: true },
  { driver_id: "d2", driver_name: "Gone Driver", is_active: false },
  { driver_id: "d3", driver_name: "Ben Driver", is_active: true },
] };

/** Make the mocked API answer like a server with demo tools on. */
function serve(status: DemoStatus | Error) {
  mockGet.mockImplementation(async (url: string) => {
    if (url.includes("/demo/simulator/status/")) {
      if (status instanceof Error) throw status;
      return status;
    }
    if (url.includes("roster-status")) return ROSTER;
    return MAPS;
  });
  mockPost.mockResolvedValue({});
}

describe("useDemoRun availability", () => {
  beforeEach(() => vi.clearAllMocks());

  it("stays off, and never calls the server, when the build switch is off", () => {
    const { result } = renderHook(() => useDemoRun(false));
    expect(result.current.availability).toBe("off");
    expect(mockGet).not.toHaveBeenCalled();
  });

  it("is available when the status endpoint answers", async () => {
    serve(IDLE);
    const { result } = renderHook(() => useDemoRun(true));
    await waitFor(() => expect(result.current.availability).toBe("available"));
    expect(result.current.isRunning).toBe(false);
  });

  it("tells a switched-off server from a production server", async () => {
    serve(new Error("Demo tools are disabled on this server."));
    const off = renderHook(() => useDemoRun(true));
    await waitFor(() => expect(off.result.current.availability).toBe("off"));
    serve(new Error("Demo tools are disabled in production environment."));
    const prod = renderHook(() => useDemoRun(true));
    await waitFor(() => expect(prod.result.current.availability).toBe("production"));
  });

  it("keeps the server's message when a start is refused", async () => {
    serve(IDLE);
    const { result } = renderHook(() => useDemoRun(true));
    await waitFor(() => expect(result.current.availability).toBe("available"));
    mockPost.mockRejectedValueOnce(new Error("Ana Driver already has kart unit 1234abcd."));
    let started = true;
    await act(async () => {
      started = await result.current.start({ track_id: "t1", driver_id: "d1", laps: 2, pace: "safe" });
    });
    expect(started).toBe(false);
    expect(result.current.actionError).toContain("already has kart unit");
  });
});

describe("DemoStatusPanel", () => {
  const noop = vi.fn();

  it("shows state, lap x of y, the run facts, Stop, Watch live and the visualizer button while running", () => {
    render(<DemoStatusPanel availability="available" status={RUNNING} actionError={null} onStop={noop} onWatchLive={noop} />);
    expect(screen.getByTestId("demo-state").textContent).toBe("Running · lap 2 of 5");
    expect(screen.getByTestId("demo-run-facts").textContent).toContain("Kari · Ana Driver · 5 laps · pace edge");
    expect(screen.getByTestId("demo-stop-btn")).toBeTruthy();
    fireEvent.click(screen.getByTestId("demo-watch-live-btn"));
    expect(noop).toHaveBeenCalledWith("d1");
    expect(screen.getByTestId("demo-open-visualizer-btn")).toBeTruthy();
  });

  it("opens the live visualizer in a new tab without an opener", () => {
    const open = vi.spyOn(window, "open").mockReturnValue(null);
    render(<DemoStatusPanel availability="available" status={IDLE} actionError={null} onStop={noop} onWatchLive={noop} />);
    fireEvent.click(screen.getByTestId("demo-open-visualizer-btn"));
    expect(open).toHaveBeenCalledWith("/demo/track_visualization.html", "_blank", "noopener,noreferrer");
    open.mockRestore();
  });

  it("shows Finished and Failed without a Stop button, and the error text", () => {
    const { rerender } = render(<DemoStatusPanel availability="available" status={{ ...RUNNING, running: false, state: "finished" }} actionError={null} onStop={noop} onWatchLive={noop} />);
    expect(screen.getByTestId("demo-state").textContent).toBe("Finished");
    expect(screen.queryByTestId("demo-stop-btn")).toBeNull();
    rerender(<DemoStatusPanel availability="available" status={{ ...RUNNING, running: false, state: "failed", error: "The COM port is busy." }} actionError={null} onStop={noop} onWatchLive={noop} />);
    expect(screen.getByTestId("demo-error").textContent).toContain("COM port is busy");
  });

  it("hides every control when demo tools are off or in production and says why", () => {
    const { rerender } = render(<DemoStatusPanel availability="off" status={null} actionError={null} onStop={noop} onWatchLive={noop} />);
    expect(screen.getByTestId("demo-unavailable").textContent).toContain("switched off");
    expect(screen.queryByTestId("demo-open-visualizer-btn")).toBeNull();
    rerender(<DemoStatusPanel availability="production" status={null} actionError={null} onStop={noop} onWatchLive={noop} />);
    expect(screen.getByTestId("demo-unavailable").textContent).toContain("production");
    expect(screen.queryByTestId("demo-stop-btn")).toBeNull();
  });
});

describe("PlayDemoDialog", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    serve(IDLE);
  });
  const custom = { id: "t1", name: "Kari", source: "vbo" as const, is_builtin: false, is_archived: false, zones: [] };

  it("lists only active drivers and checks the laps", async () => {
    render(<PlayDemoDialog map={custom} onClose={vi.fn()} onStart={vi.fn()} serverError={null} />);
    await waitFor(() => expect(screen.getByText("Ana Driver")).toBeTruthy());
    expect(screen.queryByText("Gone Driver")).toBeNull();
    const start = screen.getByTestId("play-start-btn") as HTMLButtonElement;
    expect(start.disabled).toBe(true);
    fireEvent.change(screen.getByTestId("play-driver-select"), { target: { value: "d1" } });
    expect(start.disabled).toBe(false);
    for (const bad of ["0", "21", "2.5", "", "x"]) {
      fireEvent.change(screen.getByTestId("play-laps-input"), { target: { value: bad } });
      expect(start.disabled).toBe(true);
    }
    for (const good of ["1", "20"]) {
      fireEvent.change(screen.getByTestId("play-laps-input"), { target: { value: good } });
      expect(start.disabled).toBe(false);
    }
  });

  it("starts with the chosen driver, laps and pace, then closes", async () => {
    const onStart = vi.fn().mockResolvedValue(true);
    const onClose = vi.fn();
    render(<PlayDemoDialog map={custom} onClose={onClose} onStart={onStart} serverError={null} />);
    await waitFor(() => expect(screen.getByText("Ben Driver")).toBeTruthy());
    fireEvent.change(screen.getByTestId("play-driver-select"), { target: { value: "d3" } });
    fireEvent.change(screen.getByTestId("play-laps-input"), { target: { value: "4" } });
    fireEvent.change(screen.getByTestId("play-pace-select"), { target: { value: "over" } });
    fireEvent.click(screen.getByTestId("play-start-btn"));
    await waitFor(() => expect(onClose).toHaveBeenCalled());
    expect(onStart).toHaveBeenCalledWith({ driverId: "d3", laps: 4, pace: "over" });
  });

  it("stays open and shows the server's message when the start is refused", async () => {
    const onClose = vi.fn();
    render(<PlayDemoDialog map={custom} onClose={onClose} onStart={vi.fn().mockResolvedValue(false)} serverError="A demo is already running." />);
    await waitFor(() => expect(screen.getByText("Ana Driver")).toBeTruthy());
    fireEvent.change(screen.getByTestId("play-driver-select"), { target: { value: "d1" } });
    fireEvent.click(screen.getByTestId("play-start-btn"));
    await waitFor(() => expect((screen.getByTestId("play-start-btn") as HTMLButtonElement).disabled).toBe(false));
    expect(onClose).not.toHaveBeenCalled();
    expect(screen.getByTestId("play-server-error").textContent).toContain("already running");
  });

  it("explains that pace does not apply to the Demo Circuit", async () => {
    render(<PlayDemoDialog map={{ ...custom, name: "Demo Circuit", is_builtin: true }} onClose={vi.fn()} onStart={vi.fn()} serverError={null} />);
    expect((screen.getByTestId("play-pace-select") as HTMLSelectElement).disabled).toBe(true);
    expect(screen.getByTestId("play-pace-note").textContent).toContain("custom maps only");
  });
});

describe("Maps & Demo tab with demo controls", () => {
  beforeEach(() => vi.clearAllMocks());
  afterEach(() => vi.unstubAllEnvs());

  /** Render the tab with the demo switch on or off. */
  function renderTab(switchOn: boolean, onWatchLive = vi.fn()) {
    vi.stubEnv("VITE_ENABLE_DEMO_TOOLS", switchOn ? "true" : "false");
    return render(<MemoryRouter><MapsDemoTab onWatchLive={onWatchLive} /></MemoryRouter>);
  }

  it("plays a demo from a map card: choose a driver, start, and the server gets exactly those choices", async () => {
    serve(IDLE);
    renderTab(true);
    await waitFor(() => expect(screen.getByTestId("play-Kari")).toBeTruthy());
    fireEvent.click(screen.getByTestId("play-Kari"));
    await waitFor(() => expect(screen.getByText("Ana Driver")).toBeTruthy());
    fireEvent.change(screen.getByTestId("play-driver-select"), { target: { value: "d1" } });
    fireEvent.click(screen.getByTestId("play-start-btn"));
    await waitFor(() => expect(mockPost).toHaveBeenCalledWith("/api/demo/simulator/start/", { track_id: "t1", driver_id: "d1", laps: 3, pace: "safe" }));
  });

  it("hides every Play and Stop control but keeps maps and the corner editor when the switch is off", async () => {
    serve(IDLE);
    renderTab(false);
    await waitFor(() => expect(screen.getByTestId("map-card-Kari")).toBeTruthy());
    expect(screen.queryByTestId("play-Kari")).toBeNull();
    expect(screen.queryByTestId("demo-stop-btn")).toBeNull();
    expect(screen.queryByTestId("demo-open-visualizer-btn")).toBeNull();
    expect(screen.getByTestId("edit-corners-Kari")).toBeTruthy();
    expect(mockGet.mock.calls.some(([url]) => String(url).includes("/demo/"))).toBe(false);
  });

  it("hides Play when the server says demo tools are off", async () => {
    serve(new Error("Demo tools are disabled on this server."));
    renderTab(true);
    await waitFor(() => expect(screen.getByTestId("demo-unavailable")).toBeTruthy());
    expect(screen.queryByTestId("play-Kari")).toBeNull();
    expect(screen.getByTestId("edit-corners-Kari")).toBeTruthy();
  });

  it("disables Play on every card while a demo runs, and Stop and Watch live work", async () => {
    serve(RUNNING);
    const onWatchLive = vi.fn();
    renderTab(true, onWatchLive);
    await waitFor(() => expect(screen.getByTestId("demo-stop-btn")).toBeTruthy());
    expect((screen.getByTestId("play-Kari") as HTMLButtonElement).disabled).toBe(true);
    expect((screen.getByTestId("play-Demo Circuit") as HTMLButtonElement).title).toContain("already running");
    fireEvent.click(screen.getByTestId("demo-watch-live-btn"));
    expect(onWatchLive).toHaveBeenCalledWith("d1");
    fireEvent.click(screen.getByTestId("demo-stop-btn"));
    await waitFor(() => expect(mockPost).toHaveBeenCalledWith("/api/demo/simulator/stop/"));
  });
});
