/**
 * Trackside — the page follows the server's idea of who is signed in (shared browser session).
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { act, render, screen } from "@testing-library/react";

vi.mock("../api", () => ({ api: { get: vi.fn(), post: vi.fn() }, fetchCSRFToken: vi.fn(async () => undefined) }));
import { api } from "../api";
import { SessionNoticeBanner } from "../../components/shell/session-notice-banner";
import { AuthProvider, SESSION_READ_RETRIES, SESSION_READ_RETRY_MS, SESSION_RECHECK_MIN_MS, useAuth } from "../auth";
import { clearPrivateCaches } from "../private-cache";

const mockGet = vi.mocked(api.get);
const DRIVER = { id: "u1", name: "Dee Driver", role: "driver", is_active: true, created_at: "" };
const COACH = { id: "u2", name: "Cole Coach", role: "coach", is_active: true, created_at: "" };

/** Shows who the page believes is signed in. */
function Who() {
  const { user, isLoading } = useAuth();
  return <p data-testid="who">{isLoading ? "loading" : user ? `${user.role}:${user.name}` : "nobody"}</p>;
}

/** Make the failure look like the api wrapper's: an Error carrying the HTTP status. */
function failure(status: number) {
  return Object.assign(new Error(`Request failed with status ${status}`), { status });
}

/** Let promises and timers run for the given time. */
async function pass(ms: number) {
  await act(async () => { await vi.advanceTimersByTimeAsync(ms); });
}

describe("Session follows the server", () => {
  beforeEach(() => { vi.useFakeTimers(); });
  afterEach(() => { vi.useRealTimers(); mockGet.mockReset(); });

  it("switches to the other account when the browser's session changed in another tab", async () => {
    mockGet.mockResolvedValue(DRIVER);
    render(<AuthProvider><Who /></AuthProvider>);
    await pass(10);
    expect(screen.getByTestId("who").textContent).toBe("driver:Dee Driver");

    mockGet.mockResolvedValue(COACH);   // another tab signed in as the coach
    await pass(SESSION_RECHECK_MIN_MS + 10);
    act(() => { window.dispatchEvent(new Event("focus")); });
    await pass(10);
    expect(screen.getByTestId("who").textContent).toBe("coach:Cole Coach");
  });

  it("says why the account changed, and when another tab signed out", async () => {
    mockGet.mockResolvedValue(DRIVER);
    render(<AuthProvider><SessionNoticeBanner /><Who /></AuthProvider>);
    await pass(10);
    expect(screen.queryByTestId("session-notice")).toBeNull();

    mockGet.mockResolvedValue(COACH);
    await pass(SESSION_RECHECK_MIN_MS + 10);
    act(() => { window.dispatchEvent(new Event("focus")); });
    await pass(10);
    expect(screen.getByTestId("session-notice").textContent).toContain("Cole Coach (coach)");
    expect(screen.getByTestId("session-notice").textContent).toContain("second browser");

    mockGet.mockRejectedValue(failure(403));
    await pass(SESSION_RECHECK_MIN_MS + 10);
    act(() => { window.dispatchEvent(new Event("focus")); });
    await pass(10);
    expect(screen.getByTestId("session-notice").textContent).toContain("signed out in another tab");
  });

  it("signs out when the server refuses, but not when it is only unreachable", async () => {
    mockGet.mockResolvedValue(DRIVER);
    render(<AuthProvider><Who /></AuthProvider>);
    await pass(10);

    mockGet.mockRejectedValue(failure(502));
    await pass(SESSION_RECHECK_MIN_MS + 10);
    act(() => { window.dispatchEvent(new Event("focus")); });
    await pass(10);
    expect(screen.getByTestId("who").textContent).toBe("driver:Dee Driver");

    mockGet.mockRejectedValue(failure(403));
    await pass(SESSION_RECHECK_MIN_MS + 10);
    act(() => { window.dispatchEvent(new Event("focus")); });
    await pass(10);
    expect(screen.getByTestId("who").textContent).toBe("nobody");
  });

  it("keeps trying when the server is waking up, so a refresh does not look like a sign-out", async () => {
    mockGet.mockRejectedValueOnce(failure(502)).mockRejectedValueOnce(failure(502)).mockResolvedValue(DRIVER);
    render(<AuthProvider><Who /></AuthProvider>);
    await pass(SESSION_READ_RETRY_MS * 2 + 50);
    expect(screen.getByTestId("who").textContent).toBe("driver:Dee Driver");
    expect(mockGet).toHaveBeenCalledTimes(3);
  });

  it("gives up after the retries and shows nobody", async () => {
    mockGet.mockRejectedValue(failure(502));
    render(<AuthProvider><Who /></AuthProvider>);
    await pass(SESSION_READ_RETRY_MS * (SESSION_READ_RETRIES + 1));
    expect(screen.getByTestId("who").textContent).toBe("nobody");
    expect(mockGet).toHaveBeenCalledTimes(SESSION_READ_RETRIES + 1);
  });

  it("a clear refusal on the first read is not retried", async () => {
    mockGet.mockRejectedValue(failure(403));
    render(<AuthProvider><Who /></AuthProvider>);
    await pass(10);
    expect(screen.getByTestId("who").textContent).toBe("nobody");
    expect(mockGet).toHaveBeenCalledTimes(1);
  });
});

describe("Old private cache", () => {
  it("is deleted by name", async () => {
    const deleteCache = vi.fn(async () => true);
    vi.stubGlobal("caches", { delete: deleteCache });
    await clearPrivateCaches();
    expect(deleteCache).toHaveBeenCalledWith("trackside-api-cache");
    vi.unstubAllGlobals();
  });

  it("does nothing, and does not fail, where the Cache API is missing", async () => {
    vi.stubGlobal("caches", undefined);
    await expect(clearPrivateCaches()).resolves.toBeUndefined();
    vi.unstubAllGlobals();
  });
});
