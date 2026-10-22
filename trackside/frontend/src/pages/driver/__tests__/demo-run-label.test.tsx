/**
 * Trackside Driver — the best-lap panel labels a demo run (H5).
 */

import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { BestLapTargetPanel } from "../components/best-lap-target-panel";

const base = { id: "s1", mode: "safety", goal_text: "", goal_passed: null, started_at: "2026-10-21", track_name: "Demo Circuit", best_lap_time: "0:40.0" };

describe("Driver best lap panel", () => {
  it("says when the latest session was a demo run", () => {
    render(<BestLapTargetPanel latestSession={{ ...base, is_demo: true }} />);
    expect(screen.getByTestId("driver-demo-run-label").textContent).toContain("DEMO RUN");
  });

  it("shows no label for real driving", () => {
    render(<BestLapTargetPanel latestSession={{ ...base, is_demo: false }} />);
    expect(screen.queryByTestId("driver-demo-run-label")).toBeNull();
  });
});
