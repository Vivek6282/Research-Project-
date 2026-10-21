/**
 * Trackside Coach Dashboard — Timing Tower Component.
 * Displays real-time driver classification standings, live status, and per-driver SignalStrip.
 */

import { SignalStrip } from "../../../components/ui/signal-strip";
import { DriverProfile, RosterStatusItem } from "../types";

interface TimingTowerPanelProps {
  drivers: DriverProfile[];
  selectedDriverId: string;
  setSelectedDriverId: (id: string) => void;
  rosterMap: Record<string, RosterStatusItem>;
  thresholds: Record<string, number>;
  driversError?: string | null;
  onRetry?: () => void;
}

/**
 * Renders the driver timing tower classification or clear empty/error states.
 */
export function TimingTowerPanel({
  drivers,
  selectedDriverId,
  setSelectedDriverId,
  rosterMap,
  thresholds,
  driversError,
  onRetry,
}: TimingTowerPanelProps) {
  const liveCount = drivers.filter((d) => rosterMap[d.id]?.live === true).length;

  return (
    <div
      data-testid="coach-panel-timing-tower"
      className="bg-[#12181F] border border-[#232B35] rounded-[2px] p-3 font-mono"
    >
      <div className="flex items-center justify-between mb-3 border-b border-[#232B35]/60 pb-2 font-mono">
        <div className="flex items-center gap-1.5 text-xs font-bold text-[#E7EDF3]">
          <span className="text-[#3FA6E0]">|</span> TIMING TOWER
        </div>
        <div className="flex items-center gap-1 text-[10px] text-[#33D17E]">
          <span className="text-[#7C8898]">{liveCount} live · {drivers.length} drivers</span>
          {liveCount > 0 && <span className="animate-pulse">• LIVE</span>}
        </div>
      </div>

      {driversError ? (
        <div className="p-3 text-center text-xs text-[#E5473C] bg-[#E5473C]/10 border border-[#E5473C]/30 rounded-[2px] font-mono">
          <p className="mb-2">{driversError}</p>
          {onRetry && (
            <button
              onClick={onRetry}
              className="px-2 py-1 bg-[#232B35] hover:bg-[#2A3441] text-[#E7EDF3] rounded-[2px] text-[11px] border border-[#3A4553]"
            >
              Retry
            </button>
          )}
        </div>
      ) : drivers.length === 0 ? (
        <div
          data-testid="coach-timing-tower-empty"
          className="p-4 text-center text-xs text-[#7C8898] border border-dashed border-[#232B35] rounded-[2px]"
        >
          No drivers yet. The Admin creates driver accounts.
        </div>
      ) : (
        /* Roster Classification Rows */
        <div className="space-y-1.5 font-mono">
        {drivers.map((d) => {
          const isSelected = selectedDriverId === d.id;
          const rosterInfo = rosterMap[d.id];
          const hasRealData = Boolean(
            rosterInfo &&
            rosterInfo.stage !== "no_data" &&
            rosterInfo.current_g !== null &&
            rosterInfo.current_g !== undefined
          );
          const driverG = hasRealData ? rosterInfo.current_g : null;
          const driverThresh = hasRealData
            ? (rosterInfo?.active_threshold ?? thresholds[d.id] ?? d.customThreshold ?? undefined)
            : undefined;

          return (
            <div
              key={d.id || d.pos}
              onClick={() => setSelectedDriverId(d.id)}
              className="p-2 rounded-[2px] flex items-center justify-between text-xs cursor-pointer transition-all duration-150"
              style={{
                background: isSelected ? "#161D26" : "transparent",
                border: `1px solid ${isSelected ? "#3FA6E0" : "transparent"}`,
                boxShadow: isSelected ? "0 0 10px rgba(63,166,224,0.15)" : "none",
              }}
            >
              <div className="flex items-center gap-2">
                <span className="text-[#7C8898] text-[10px] w-3">{d.pos}</span>
                <span className="w-5 h-5 rounded-[1px] bg-[#232B35] text-[#E7EDF3] text-[10px] font-bold flex items-center justify-center border border-[#3A4553]">
                  {d.pos}
                </span>
                <div>
                  <p className="font-semibold text-xs text-[#E7EDF3] leading-none mb-1">{d.name}</p>
                  <p className="text-[9px] text-[#7C8898] leading-none">
                    {rosterInfo?.session_state === "in_progress"
                      ? "IN PROGRESS"
                      : rosterInfo?.session_state === "ended"
                      ? "ENDED"
                      : (d.session && d.session !== "—" ? d.session : "—")}
                  </p>
                </div>
              </div>

              <div className="flex flex-col items-end gap-1">
                <SignalStrip
                  stage={hasRealData ? (rosterInfo?.stage as any) : "no_data"}
                  currentG={hasRealData && driverG !== null ? driverG : undefined}
                  threshold={driverThresh}
                  size="sm"
                  showLabel={false}
                />
                <span
                  className={`text-right font-bold text-[10px] ${
                    hasRealData && driverG !== null ? "text-[#3FA6E0]" : "text-[#7C8898]"
                  }`}
                >
                  {hasRealData && driverG !== null ? `${driverG.toFixed(2)}g` : "—"}
                </span>
              </div>
            </div>
          );
        })}
      </div>
      )}
    </div>
  );
}
