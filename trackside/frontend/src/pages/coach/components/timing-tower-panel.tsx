/**
 * Trackside Coach Dashboard — Timing Tower Component.
 * Displays real-time driver classification standings, live status, and per-driver SignalStrip.
 */

import { SignalStrip } from "../../../components/ui/signal-strip";
import { DriverProfile, RosterStatusItem } from "../types";

interface TimingTowerPanelProps {
  drivers: DriverProfile[];
  selectedKart: string;
  setSelectedKart: (kart: string) => void;
  rosterMap: Record<string, RosterStatusItem>;
  thresholds: Record<string, number>;
}

export function TimingTowerPanel({
  drivers,
  selectedKart,
  setSelectedKart,
  rosterMap,
  thresholds,
}: TimingTowerPanelProps) {
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
          <span className="text-[#7C8898]">{drivers.length}/{drivers.length} ON TRACK</span>
          <span className="animate-pulse">• LIVE</span>
        </div>
      </div>

      {/* Roster Classification Rows */}
      <div className="space-y-1.5 font-mono">
        {drivers.map((d) => {
          const isSelected = selectedKart === d.kart;
          const rosterInfo = rosterMap[d.kart];
          const driverG = rosterInfo
            ? rosterInfo.current_g
            : thresholds[d.kart]
            ? thresholds[d.kart] * 0.7
            : 0.85;
          const driverThresh = rosterInfo
            ? rosterInfo.active_threshold
            : thresholds[d.kart] || 1.15;

          return (
            <div
              key={d.pos}
              onClick={() => setSelectedKart(d.kart)}
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
                  {d.kart}
                </span>
                <div>
                  <p className="font-semibold text-xs text-[#E7EDF3] leading-none mb-1">{d.name}</p>
                  <p className="text-[9px] text-[#7C8898] leading-none">
                    {d.lapTime} ·{" "}
                    <span className={d.inPit ? "text-[#F2A93B]" : "text-[#7C8898]"}>
                      {d.session}
                    </span>
                  </p>
                </div>
              </div>

              <div className="flex flex-col items-end gap-1">
                <SignalStrip
                  currentG={driverG}
                  threshold={driverThresh}
                  size="sm"
                  showLabel={false}
                />
                <span className="text-[#3FA6E0] text-right font-bold text-[10px]">{d.gap}</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
