/**
 * Trackside Coach Dashboard — Live Trajectory Panel.
 * Displays speed oscillogram, live signal status, and telemetric key indicators.
 */

import { SignalStrip } from "../../../components/ui/signal-strip";
import { DriverProfile } from "../types";

interface LiveTrajectoryPanelProps {
  selectedDriver: DriverProfile;
  currentGForce: number | null;
  currentThreshold: number | null;
  isStraight?: boolean;
  currentSpeed: number | null;
  actualSpeedPath: number[];
}

/**
 * Displays live speed oscillogram waveform and g-force signal status.
 */
export function LiveTrajectoryPanel({
  selectedDriver,
  currentGForce,
  currentThreshold,
  isStraight = false,
  currentSpeed,
  actualSpeedPath,
}: LiveTrajectoryPanelProps) {
  // Converts an array of speed data points into an SVG path string.
  const buildSvgPath = (points: number[]) => {
    if (!points || points.length === 0) return "";
    if (points.length === 1) return `M 0 ${points[0]} L 800 ${points[0]}`;
    const step = 800 / (points.length - 1);
    return points.reduce((acc, y, i) => `${acc} ${i === 0 ? "M" : "L"} ${i * step} ${y}`, "");
  };

  return (
    <div
      data-testid="coach-panel-live-trajectory"
      className="bg-[#12181F] border border-[#232B35] rounded-[2px] p-3 sm:p-4 font-mono"
    >
      {/* Header & Metadata */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 mb-3 border-b border-[#232B35]/60 pb-2.5">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-[#3FA6E0] font-bold">|</span>
          <span className="text-xs font-bold uppercase tracking-wider text-[#E7EDF3]">
            LIVE TRAJECTORY
          </span>
          <span className="text-xs text-[#7C8898]">
            {selectedDriver.name !== "—" ? selectedDriver.name : "—"}
            {selectedDriver.session !== "—" ? ` · ${selectedDriver.session}` : ""}
          </span>
        </div>
        {/* Live Signal Indicator & Stage Label */}
        <SignalStrip
          testId="coach-signal-strip"
          currentG={currentGForce !== null && !isStraight ? currentGForce : undefined}
          stage={isStraight && currentGForce !== null ? "nominal" : undefined}
          threshold={currentThreshold ?? undefined}
          size="md"
          showLabel={true}
        />
      </div>

      {/* Readouts Row */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 mb-4">
        <div className="flex items-baseline gap-1.5 font-mono">
          {currentSpeed !== null ? (
            <>
              <span className="text-3xl sm:text-4xl font-extrabold text-[#3FA6E0] tracking-tight">
                {currentSpeed}
              </span>
              <span className="text-xs text-[#7C8898]">km/h</span>
            </>
          ) : (
            <span className="text-sm font-bold text-[#7C8898]">Waiting for live data</span>
          )}
        </div>

        <div className="grid grid-cols-4 gap-4 sm:flex sm:items-center sm:gap-6 font-mono text-xs w-full sm:w-auto">
          <div>
            <span className="text-[10px] text-[#7C8898] block mb-0.5">LAST</span>
            <span className="font-semibold text-[#E7EDF3]">{selectedDriver.lapTime}</span>
          </div>
          <div>
            <span className="text-[10px] text-[#7C8898] block mb-0.5">BEST</span>
            <span className="font-semibold text-[#33D17E]">—</span>
          </div>
          <div>
            <span className="text-[10px] text-[#7C8898] block mb-0.5">DELTA</span>
            <span className="font-semibold text-[#F2A93B]">{selectedDriver.gap}</span>
          </div>
          <div>
            <span className="text-[10px] text-[#7C8898] block mb-0.5">G-FORCE</span>
            <span className="font-semibold text-[#E7EDF3]">
              {currentGForce !== null ? `${currentGForce} g` : "—"}
            </span>
          </div>
        </div>
      </div>

      {/* Dual Waveform Speed Chart */}
      <div className="relative w-full h-[220px] bg-[#0A0E13] border border-[#232B35] rounded-[2px] p-3 overflow-hidden">
        <div className="absolute left-2 top-2 bottom-6 flex flex-col justify-between text-[10px] font-mono text-[#4B5563]">
          <span>140</span>
          <span>110</span>
          <span>80</span>
          <span>50</span>
          <span>20</span>
        </div>

        <div className="absolute left-9 top-[4px] right-4 bottom-7">
          {actualSpeedPath.length === 0 ? (
            <div className="w-full h-full flex items-center justify-center text-xs text-[#7C8898] font-mono">
              Waiting for live telemetry stream...
            </div>
          ) : (
            <svg className="w-full h-full overflow-visible" preserveAspectRatio="none" viewBox="0 0 800 160">
              <line x1="0" y1="0" x2="800" y2="0" stroke="#232B35" strokeDasharray="3 3" opacity="0.5" />
              <line x1="0" y1="40" x2="800" y2="40" stroke="#232B35" strokeDasharray="3 3" opacity="0.5" />
              <line x1="0" y1="80" x2="800" y2="80" stroke="#232B35" strokeDasharray="3 3" opacity="0.5" />
              <line x1="0" y1="120" x2="800" y2="120" stroke="#232B35" strokeDasharray="3 3" opacity="0.5" />

              <path
                d={buildSvgPath(actualSpeedPath)}
                fill="none"
                stroke="#3FA6E0"
                strokeWidth="2.5"
              />
            </svg>
          )}
        </div>

        <div className="absolute left-9 right-4 bottom-1 flex justify-between text-[9px] font-mono text-[#4B5563]">
          {[1, 3, 5, 7, 9, 11, 13, 15, 17, 19, 21, 23, 25, 27, 29, 31, 33, 35, 37, 39, 41, 43].map((num) => (
            <span key={num}>{num}</span>
          ))}
        </div>

        <div className="absolute left-10 bottom-2.5 flex items-center gap-4 text-[10px] font-mono">
          <span className="flex items-center gap-1.5 text-[#3FA6E0]">
            <span className="w-3 h-0.5 bg-[#3FA6E0]" /> Actual Speed
          </span>
        </div>
      </div>
    </div>
  );
}
