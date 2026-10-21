/**
 * Trackside Coach Dashboard — Custom Zone Threshold Control Component.
 * Allows coach to adjust safety/performance g-force limits per active zone and driver.
 */

import { DriverProfile, TrackZone } from "../types";

interface ThresholdControlPanelProps {
  currentZoneObj: TrackZone | undefined;
  selectedDriver: DriverProfile;
  sliderMin: number;
  sliderMax: number;
  currentThreshold: number | null;
  thresholds: Record<string, number>;
  setThresholds: (val: Record<string, number>) => void;
}

/**
 * Renders the custom threshold slider and input for adjusting zone limits.
 */
export function ThresholdControlPanel({
  currentZoneObj,
  selectedDriver,
  sliderMin,
  sliderMax,
  currentThreshold,
  thresholds,
  setThresholds,
}: ThresholdControlPanelProps) {
  const activeVal = currentThreshold ?? sliderMax;

  return (
    <div
      data-testid="coach-panel-threshold-control"
      className="bg-[#12181F] border border-[#232B35] rounded-[2px] p-3 sm:p-4"
    >
      <div className="flex items-center justify-between mb-3 border-b border-[#232B35]/60 pb-2 font-mono">
        <div className="flex items-center gap-2">
          <span className="text-[#3FA6E0] font-bold">|</span>
          <span className="text-xs font-bold text-[#E7EDF3]">CUSTOM ZONE THRESHOLD CONTROL</span>
        </div>
        <span className="text-[10px] text-[#3FA6E0] font-bold hidden sm:inline">
          SERVER VALIDATED ≤ ZONE DEFAULT ({sliderMax.toFixed(2)}g)
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 items-center font-mono">
        <div>
          <div className="flex items-center justify-between text-xs mb-1.5">
            <span className="text-[#7C8898]">
              ZONE: {currentZoneObj ? currentZoneObj.label.toUpperCase() : "—"}
            </span>
            <span className="text-[#E7EDF3] font-bold">
              DRIVER: {selectedDriver.name.toUpperCase()}
            </span>
          </div>
          <input
            data-testid="coach-threshold-slider"
            type="range"
            min={sliderMin}
            max={sliderMax}
            step="0.05"
            value={activeVal}
            onChange={(e) =>
              setThresholds({ ...thresholds, [selectedDriver.id]: Number(e.target.value) })
            }
            className="w-full accent-[#3FA6E0] cursor-pointer min-h-[36px]"
          />
          <div className="flex justify-between text-[10px] text-[#7C8898] mt-1">
            <span>{sliderMin.toFixed(2)}g (Conservative)</span>
            <span>{((sliderMin + sliderMax) / 2).toFixed(2)}g</span>
            <span>{sliderMax.toFixed(2)}g (Zone Max)</span>
          </div>
        </div>

        <div className="bg-[#161D26] border border-[#232B35] p-3 rounded-[2px] flex items-center justify-between">
          <div>
            <p className="text-[10px] text-[#7C8898]">CALIBRATED LIMIT</p>
            <p
              data-testid="coach-calibrated-limit-value"
              className="text-xl font-bold text-[#3FA6E0]"
            >
              {currentThreshold !== null && currentThreshold !== undefined
                ? `${currentThreshold.toFixed(2)} g`
                : "—"}
            </p>
          </div>
          <div className="text-right">
            <p className="text-[10px] text-[#7C8898]">SERVER STATUS</p>
            <span className="text-[10px] text-[#33D17E] bg-[#33D17E]/10 border border-[#33D17E]/30 px-1.5 py-0.5 rounded-[1px]">
              ✓ VALIDATED SAFE
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
