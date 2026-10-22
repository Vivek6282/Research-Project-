/**
 * Trackside — Coach live screen follows the active session (Prompt 15, A1..A4)
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, waitFor, act } from "@testing-library/react";
import { pickActiveSession, trackIdOf, useActiveSession } from "../hooks/use-active-session";
import { useCoachNotes } from "../hooks/use-coach-notes";
import { useCoachTelemetry } from "../hooks/use-coach-telemetry";

vi.mock("../../../lib/api", () => ({ api: { get: vi.fn(), post: vi.fn() } }));

import { api } from "../../../lib/api";
const mockGet = vi.mocked(api.get);

const session = (id: string, driver: string, started: string, track: string | null, ended: string | null = null) => ({
  id, driver, started_at: started, track, track_name: track ? `Track ${track}` : null, ended_at: ended,
});

describe("pickActiveSession", () => {
  it("takes only the selected driver's sessions, newest first, in-progress before ended", () => {
    const list = [
      session("other-new", "d2", "2026-10-20T12:00:00Z", "t9"),
      session("mine-old-open", "d1", "2026-10-20T08:00:00Z", "t1"),
      session("mine-new-ended", "d1", "2026-10-20T11:00:00Z", "t2", "2026-10-20T11:30:00Z"),
      session("mine-newer-open", "d1", "2026-10-20T10:00:00Z", "t3"),
    ];
    expect(pickActiveSession(list, "d1")?.id).toBe("mine-newer-open");
    expect(pickActiveSession(list.filter((s) => s.id !== "mine-newer-open" && s.id !== "mine-old-open"), "d1")?.id).toBe("mine-new-ended");
    expect(pickActiveSession(list, "d2")?.id).toBe("other-new");
    expect(pickActiveSession(list, "nobody")).toBeNull();
    expect(pickActiveSession(list, "")).toBeNull();
  });

  it("ignores an old unfinished session when the driver is not live, so a newer finished run is shown", () => {
    const list = [
      session("stale-open", "d1", "2026-10-20T08:00:00Z", "apex"),
      session("newer-finished", "d1", "2026-10-21T08:00:00Z", "demo", "2026-10-21T08:30:00Z"),
    ];
    expect(pickActiveSession(list, "d1", true)?.id).toBe("stale-open");
    expect(pickActiveSession(list, "d1", false)?.id).toBe("newer-finished");
  });

  it("reads the track id from an id or an object, null when absent", () => {
    expect(trackIdOf({ track: "t1" })).toBe("t1");
    expect(trackIdOf({ track: { id: "t2" } })).toBe("t2");
    expect(trackIdOf({ track: null })).toBeNull();
    expect(trackIdOf(null)).toBeNull();
  });
});

describe("useActiveSession", () => {
  beforeEach(() => vi.clearAllMocks());

  it("gives the track of the chosen session and follows the driver switch at once", async () => {
    mockGet.mockResolvedValue([session("s1", "d1", "2026-10-20T10:00:00Z", "t1"), session("s2", "d2", "2026-10-20T11:00:00Z", "t2")]);
    const { result, rerender } = renderHook(({ id }) => useActiveSession(id, undefined, "live"), { initialProps: { id: "d1" } });
    await waitFor(() => expect(result.current.activeSessionId).toBe("s1"));
    expect(result.current.activeTrackId).toBe("t1");
    rerender({ id: "d2" });
    expect(result.current.activeSessionId).toBe("s2");
    expect(result.current.activeTrackId).toBe("t2");
    expect(mockGet).toHaveBeenCalledTimes(1);
  });

  it("has no track when the session has none", async () => {
    mockGet.mockResolvedValue([session("s1", "d1", "2026-10-20T10:00:00Z", null)]);
    const { result } = renderHook(() => useActiveSession("d1", undefined, "live"));
    await waitFor(() => expect(result.current.activeSessionId).toBe("s1"));
    expect(result.current.activeTrackId).toBeNull();
  });

  it("reloads the sessions when the driver's session_state or live flag changes in the roster", async () => {
    mockGet.mockResolvedValueOnce([]);
    const roster = (state: string, live: boolean) => ({ current_g: null, active_threshold: null, stage: "no_data", live, session_state: state });
    const { result, rerender } = renderHook(({ item }) => useActiveSession("d1", item, "live"), { initialProps: { item: roster("none", false) } });
    await waitFor(() => expect(mockGet).toHaveBeenCalledTimes(1));
    expect(result.current.activeSessionId).toBeNull();
    mockGet.mockResolvedValueOnce([session("new", "d1", "2026-10-21T09:00:00Z", "t7")]);
    rerender({ item: roster("in_progress", true) });
    await waitFor(() => expect(result.current.activeSessionId).toBe("new"));
    expect(result.current.activeTrackId).toBe("t7");
    expect(mockGet).toHaveBeenCalledTimes(2);
    rerender({ item: roster("in_progress", true) });
    expect(mockGet).toHaveBeenCalledTimes(2);
  });
});

const driver: any = { id: "d1", name: "Ana", kart: "7", baseHr: 0, baseSpo2: 0, baseBreathing: 0 };

describe("useCoachNotes follows the active session and track", () => {
  beforeEach(() => vi.clearAllMocks());

  it("loads zones of the active track only, never asks for the track list, and empties without a track", async () => {
    mockGet.mockImplementation(async (url: string) => (url.includes("/zones/") ? [{ id: "z1", label: "Hairpin", threshold_g: 1.1 }] : []));
    const { result, rerender } = renderHook(({ track }) => useCoachNotes("s1", track, driver), { initialProps: { track: "t1" as string | null } });
    await waitFor(() => expect(result.current.zones.map((z) => z.label)).toEqual(["Hairpin"]));
    expect(mockGet.mock.calls.map((c) => c[0])).toContain("/api/tracks/t1/zones/");
    expect(mockGet.mock.calls.map((c) => c[0])).not.toContain("/api/tracks/");
    rerender({ track: null });
    await waitFor(() => expect(result.current.zones).toEqual([]));
  });

  it("clears the notes when the session goes away and loads the new session's notes", async () => {
    mockGet.mockImplementation(async (url: string) => (url.endsWith("/notes/") ? [{ id: "n1", note_text: "Late brake", zone_label: "Hairpin" }] : []));
    const { result, rerender } = renderHook(({ session }) => useCoachNotes(session, null, driver), { initialProps: { session: "s1" as string | null } });
    await waitFor(() => expect(result.current.notes).toHaveLength(1));
    rerender({ session: null });
    await waitFor(() => expect(result.current.notes).toHaveLength(0));
  });
});

describe("useCoachTelemetry follows the session", () => {
  const sockets: any[] = [];
  class FakeSocket {
    url: string; closed = false; onopen: any; onmessage: any; onclose: any; onerror: any;
    constructor(url: string) { this.url = url; sockets.push(this); }
    close() { this.closed = true; }
  }
  beforeEach(() => { sockets.length = 0; vi.stubGlobal("WebSocket", FakeSocket); });
  afterEach(() => vi.unstubAllGlobals());

  it("closes the old socket, opens one for the new session and clears the old chart", async () => {
    const { result, rerender } = renderHook(({ session }) => useCoachTelemetry(driver, session), { initialProps: { session: "s1" as string | null } });
    expect(sockets[0].url).toContain("/ws/sessions/s1/telemetry/");
    act(() => sockets[0].onmessage({ data: JSON.stringify({ type: "telemetry_reading", data: { speed_kmh: 50, lateral_g: 1.1 } }) }));
    expect(result.current.actualSpeedPath).toEqual([50]);
    rerender({ session: "s2" });
    expect(sockets[0].closed).toBe(true);
    expect(sockets[1].url).toContain("/ws/sessions/s2/telemetry/");
    expect(result.current.actualSpeedPath).toEqual([]);
    expect(result.current.currentGForce).toBeNull();
  });
});
