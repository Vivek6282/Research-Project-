/**
 * Trackside — Signal Strip & Timing Tower "No Data" Vitest Suite
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { SignalStrip } from "../signal-strip";
import { TimingTowerPanel } from "../../../pages/coach/components/timing-tower-panel";
import { DriverProfile } from "../../../pages/coach/types";

describe("SignalStrip No Data State", () => {
  it("renders label NO DATA and 0 lit segments when stage is no_data", () => {
    render(<SignalStrip stage="no_data" testId="test-strip" />);

    const label = screen.getByTestId("test-strip-stage-label");
    expect(label.textContent).toBe("NO DATA");

    // All 5 segments must have data-lit="false"
    for (let i = 0; i < 5; i++) {
      const seg = screen.getByTestId(`test-strip-segment-${i}`);
      expect(seg.getAttribute("data-lit")).toBe("false");
    }
  });

  it("renders TimingTowerPanel with 0 live and no pulsing LIVE dot for driver with no sessions", () => {
    const mockDrivers: DriverProfile[] = [
      {
        id: "driver-1",
        name: "Test Driver",
        pos: 1,
        gap: "—",
        session: "—",
        lapTime: "—",
        inPit: false,
      } as unknown as DriverProfile,
    ];

    render(
      <TimingTowerPanel
        drivers={mockDrivers}
        selectedDriverId="driver-1"
        setSelectedDriverId={vi.fn()}
        rosterMap={{
          "driver-1": {
            current_g: null,
            active_threshold: null,
            stage: "no_data",
            live: false,
            session_state: "none",
          },
        }}
      />
    );

    expect(screen.getByText(/0 live · 1 drivers/i)).toBeDefined();
    expect(screen.queryByText(/• LIVE/i)).toBeNull();
  });
  it("shows no lights and no g number for an ended driver, but shows them while live", () => {
    const driver = { id: "d1", name: "Ended Driver", pos: 1, gap: "—", session: "—", lapTime: "—", inPit: false } as unknown as DriverProfile;
    const roster = (live: boolean, state: string) => ({
      d1: { current_g: 0.12, active_threshold: 1.2, stage: "nominal", live, session_state: state },
    });
    const view = render(
      <TimingTowerPanel drivers={[driver]} selectedDriverId="d1" setSelectedDriverId={vi.fn()}
        rosterMap={roster(false, "ended")} />
    );
    expect(screen.queryByText("0.12g")).toBeNull();
    expect(screen.getByText("ENDED")).toBeDefined();

    view.rerender(
      <TimingTowerPanel drivers={[driver]} selectedDriverId="d1" setSelectedDriverId={vi.fn()}
        rosterMap={roster(true, "in_progress")} />
    );
    expect(screen.getByText("0.12g")).toBeDefined();
  });
});
