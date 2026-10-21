/**
 * Trackside Coach — the Historical tab labels demo runs (H5).
 */

import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { HistoricalSessionsTab } from "../components/historical-sessions-tab";
import type { HistoricalSession } from "../types";

/** Build one history row with sensible defaults. */
function row(patch: Partial<HistoricalSession>): HistoricalSession {
  return {
    id: "SESS-1", driver: "Ana", kart: "#1", date: "2026-10-21", duration: "5 min", mode: "Safety",
    laps: 3, bestLap: "0:42.1", maxG: "1.1g", alerts: 0, ...patch,
  };
}

describe("Historical sessions tab", () => {
  it("shows a Demo run label only on demo sessions", () => {
    render(<HistoricalSessionsTab historicalSessions={[row({ id: "SESS-REAL" }), row({ id: "SESS-DEMO", isDemo: true })]} />);
    const labels = screen.getAllByTestId("coach-demo-run-label");
    expect(labels).toHaveLength(1);
    expect(labels[0].closest("tr")?.textContent).toContain("SESS-DEMO");
  });
});
