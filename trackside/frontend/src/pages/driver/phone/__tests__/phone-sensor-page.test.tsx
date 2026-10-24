/**
 * Trackside — Phone Sensor page (Driver, Phase 2.1)
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

vi.mock("../../../../components/shell/top-bar", () => ({ TopBar: () => null }));
vi.mock("../../../../lib/api", () => ({
  api: { get: vi.fn(), post: vi.fn(), put: vi.fn() },
  ApiError: class ApiError extends Error {
    status: number;
    constructor(message: string, status: number) {
      super(message);
      this.status = status;
    }
  },
}));

import { api, ApiError } from "../../../../lib/api";
import { PhoneSensorPage } from "../phone-sensor-page";
import { sendResultFromError } from "../phone-api";

const mockGet = vi.mocked(api.get);
const session = (overrides = {}) => ({
  id: "s1", track: "t1", track_name: "Kart Park", started_at: "2026-10-24T10:00:00Z", ended_at: null,
  data_source: "real_time", ...overrides,
});

const show = () => render(<MemoryRouter><PhoneSensorPage /></MemoryRouter>);

describe("PhoneSensorPage", () => {
  beforeEach(() => vi.clearAllMocks());

  it("says to ask the coach when no real-time session is running (simulator and ended ones do not count)", async () => {
    mockGet.mockResolvedValue([session({ data_source: "simulator" }), session({ id: "s2", ended_at: "2026-10-24T11:00:00Z" })]);
    show();
    await waitFor(() => expect(screen.getByTestId("phone-no-session")).toBeDefined());
    expect(screen.queryByTestId("phone-start")).toBeNull();
  });

  it("offers Start for the driver's running real-time session", async () => {
    mockGet.mockResolvedValue({ results: [session()] });
    show();
    await waitFor(() => expect(screen.getByTestId("phone-start")).toBeDefined());
    expect(screen.getByTestId("phone-session").textContent).toContain("Kart Park");
  });
});

describe("sendResultFromError", () => {
  it("drops refused batches, stops on no-consent or simulator sessions, retries everything else", () => {
    expect(sendResultFromError(new ApiError("bad", 400))).toEqual({ kind: "reject" });
    expect(sendResultFromError(new ApiError("No consent", 403))).toEqual({ kind: "stop", message: "No consent" });
    expect(sendResultFromError(new ApiError("Simulator session", 409))).toEqual({ kind: "stop", message: "Simulator session" });
    expect(sendResultFromError(new ApiError("down", 502))).toEqual({ kind: "retry" });
    expect(sendResultFromError(new TypeError("Failed to fetch"))).toEqual({ kind: "retry" });
  });
});
