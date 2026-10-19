/**
 * Trackside Driver Dashboard — Live Telemetry and Glove Signal Panel.
 * Displays current lateral g-force readings, active threshold, stale data warning,
 * and the synchronized 5-segment glove LED signal strip.
 */

import { Activity } from "lucide-react";
import { Panel } from "../../../components/ui/panel";
import { SignalStrip } from "../../../components/ui/signal-strip";
import { StaleDataBadge } from "../../../components/ui/stale-data-badge";

interface TelemetryPanelProps {
  currentG: number;
  activeThreshold: number;
  lastSyncTime: number;
  isMockTelemetry: boolean;
}

export function TelemetryPanel({
  currentG,
  activeThreshold,
  lastSyncTime,
  isMockTelemetry,
}: TelemetryPanelProps) {
  return (
    <Panel testId="driver-panel-telemetry" title="Live Driver Telemetry & Glove LED Feed" icon={Activity}>
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 p-3 bg-[#161D26] border border-[#232B35] rounded-[2px] font-mono">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <p className="text-[10px] text-[#7C8898] uppercase">Active Zone: Turn 4 Hairpin</p>
            <StaleDataBadge lastSyncedTimestamp={lastSyncTime} />
            {isMockTelemetry && (
              <span
                data-testid="driver-simulated-data-badge"
                className="bg-[#F2A93B]/20 border border-[#F2A93B]/60 text-[#F2A93B] font-extrabold text-[9px] px-1.5 py-0.5 rounded uppercase tracking-wider animate-pulse"
              >
                SIMULATED DATA — not live
              </span>
            )}
          </div>
          <div className="flex items-baseline gap-2 mt-0.5">
            <span className="text-3xl font-extrabold text-[#3FA6E0]">{currentG} g</span>
            <span className="text-xs text-[#7C8898]">/ {activeThreshold.toFixed(2)} g THRESHOLD</span>
          </div>
        </div>

        {/* Synchronized 5-Segment Signal Strip & Status Label */}
        <div className="flex flex-col items-start sm:items-end gap-1">
          <span className="text-[10px] text-[#7C8898] uppercase">GLOVE LED HARDWARE STATUS</span>
          <SignalStrip
            testId="driver-signal-strip"
            currentG={currentG}
            threshold={activeThreshold}
            size="lg"
            showLabel={true}
          />
        </div>
      </div>
    </Panel>
  );
}
