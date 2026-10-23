/**
 * Trackside Driver Dashboard — Live Telemetry and Glove Signal Panel.
 * Displays current lateral g-force readings, active threshold, stale data warning,
 * and the synchronized 5-segment glove LED signal strip.
 */

import { Activity } from "lucide-react";
import { Panel } from "../../../components/ui/panel";
import { SignalStrip } from "../../../components/ui/signal-strip";
import { StaleDataBadge } from "../../../components/ui/stale-data-badge";
import { TrajectoryStage } from "../../../components/ui/signal-strip";

interface TelemetryPanelProps {
  currentG: number | null;
  activeThreshold: number | null;
  activeZone?: string | null;
  lastSyncTime?: number;
  stage?: TrajectoryStage | null;
}

/**
 * Renders the driver's current g-force, active zone limit, and glove signal strip.
 */
export function TelemetryPanel({
  currentG,
  activeThreshold,
  activeZone,
  lastSyncTime,
  stage,
}: TelemetryPanelProps) {
  return (
    <Panel testId="driver-panel-telemetry" title="Live Driver Telemetry & Glove LED Feed" icon={Activity}>
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 p-3 bg-[#161D26] border border-[#232B35] rounded-[2px] font-mono">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <p className="text-[10px] text-[#7C8898] uppercase">Active Zone: {activeZone || "—"}</p>
            <StaleDataBadge lastSyncedTimestamp={lastSyncTime} />
          </div>
          <div className="flex items-baseline gap-2 mt-0.5">
            {currentG !== null ? (
              <>
                <span className="text-3xl font-extrabold text-[#3FA6E0]">{currentG} g</span>
                <span className="text-xs text-[#7C8898]">
                  / {activeThreshold !== null && activeThreshold !== undefined ? `${activeThreshold.toFixed(2)} g THRESHOLD` : "no limit on a straight"}
                </span>
              </>
            ) : (
              <span className="text-sm font-bold text-[#7C8898]">Waiting for live data</span>
            )}
          </div>
        </div>

        {/* Synchronized 5-Segment Signal Strip & Status Label */}
        <div className="flex flex-col items-start sm:items-end gap-1">
          <span className="text-[10px] text-[#7C8898] uppercase">GLOVE LED HARDWARE STATUS</span>
          <SignalStrip
            testId="driver-signal-strip"
            stage={currentG !== null ? stage ?? "nominal" : "no_data"}
            size="lg"
            showLabel={true}
          />
        </div>
      </div>
    </Panel>
  );
}
