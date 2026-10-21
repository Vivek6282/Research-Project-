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
      },
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
        thresholds={{}}
      />
    );

    expect(screen.getByText(/0 live · 1 drivers/i)).toBeDefined();
    expect(screen.queryByText(/• LIVE/i)).toBeNull();
  });
});
