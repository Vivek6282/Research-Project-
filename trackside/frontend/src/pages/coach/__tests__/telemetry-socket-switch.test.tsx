/**
 * Trackside Coach — moving to another session closes the old live feed for good, so nothing from the
 * old session can reach the glove (the bridge forwards every reading it hears).
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { act, renderHook } from "@testing-library/react";
import { useCoachTelemetry } from "../hooks/use-coach-telemetry";

class FakeSocket {
  static all: FakeSocket[] = [];
  onopen: (() => void) | null = null;
  onmessage: ((e: { data: string }) => void) | null = null;
  onclose: (() => void) | null = null;
  onerror: (() => void) | null = null;
  closed = false;
  constructor(public url: string) { FakeSocket.all.push(this); }
  /** A real browser fires "close" after close() is called: this is what the cleanup triggers. */
  close() {
    this.closed = true;
    setTimeout(() => this.onclose?.(), 0);
  }
}

/** The session id in a socket's address. */
const sessionOf = (socket: FakeSocket) => /sessions\/([^/]+)\//.exec(socket.url)![1];
const DRIVER = { id: "d1", baseHr: 0, baseSpo2: 0, baseBreathing: 0 } as never;

describe("Live feed when the watched session changes", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    FakeSocket.all = [];
    vi.stubGlobal("WebSocket", FakeSocket as unknown as typeof WebSocket);
  });
  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it("does not bring the old session's socket back, and forwards nothing from it", async () => {
    const forwarded: string[] = [];
    const listen = (e: Event) => forwarded.push((e as CustomEvent).detail.tag);
    window.addEventListener("trackside:reading", listen);
    const { rerender } = renderHook(({ id }) => useCoachTelemetry(DRIVER, id), { initialProps: { id: "s1" } });
    rerender({ id: "s2" });
    await act(async () => { await vi.advanceTimersByTimeAsync(7000); });   // two retry periods
    const stillOpenOld = FakeSocket.all.filter((s) => sessionOf(s) === "s1" && !s.closed);
    stillOpenOld.forEach((s) => s.onmessage?.({ data: JSON.stringify({ type: "telemetry_reading", data: { lateral_g: 1, stage: "intervene", tag: "OLD" } }) }));
    window.removeEventListener("trackside:reading", listen);
    expect({ opened: FakeSocket.all.map(sessionOf), oldSocketsOpen: stillOpenOld.length, forwarded })
      .toEqual({ opened: ["s1", "s2"], oldSocketsOpen: 0, forwarded: [] });
  });

  it("still reconnects the current session after an unexpected drop", async () => {
    renderHook(() => useCoachTelemetry(DRIVER, "s1"));
    FakeSocket.all[0].onclose?.();                                           // the server dropped it
    await act(async () => { await vi.advanceTimersByTimeAsync(3100); });
    expect(FakeSocket.all.map(sessionOf)).toEqual(["s1", "s1"]);
  });

  it("stops retrying once the page is closed", async () => {
    const { unmount } = renderHook(() => useCoachTelemetry(DRIVER, "s1"));
    unmount();
    await act(async () => { await vi.advanceTimersByTimeAsync(10000); });
    expect(FakeSocket.all.map(sessionOf)).toEqual(["s1"]);
  });
});
