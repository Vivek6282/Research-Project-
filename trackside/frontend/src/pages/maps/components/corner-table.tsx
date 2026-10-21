/**
 * Trackside Maps — table where the user names each corner and sets its g limit.
 * The safe corner speed hint is recalculated live: sqrt(limit x 9.81 x tightest radius).
 */

import { labelError, limitError, MAX_LABEL_LENGTH, parseLimit, safeSpeedKmh } from "../safe-speed";
import type { CornerChoice, CornerPreview, LimitRange } from "../types";

interface CornerTableProps {
  corners: CornerPreview[];
  choices: CornerChoice[];
  range: LimitRange;
  onChange: (number: number, patch: Partial<CornerChoice>) => void;
}

const inputClass =
  "w-full min-w-0 bg-[#0A0E13] border border-[#232B35] rounded-[2px] px-2 py-1.5 text-xs font-mono text-[#E7EDF3] focus:border-[#3FA6E0] outline-none";

/** One editable row per corner with a live safe-speed hint. */
export function CornerTable({ corners, choices, range, onChange }: CornerTableProps) {
  return (
    <div data-testid="corner-table" className="flex flex-col gap-2">
      <div className="hidden sm:grid grid-cols-[2rem_1fr_7rem_6rem_7rem] gap-2 px-2 text-[10px] font-mono uppercase tracking-wider text-[#7C8898]">
        <span>#</span>
        <span>Corner name</span>
        <span>Limit (g)</span>
        <span>Tightest</span>
        <span>Safe speed</span>
      </div>
      {corners.map((corner) => {
        const choice = choices.find((c) => c.number === corner.number);
        if (!choice) return null;
        const nameProblem = labelError(choice.label);
        const limitProblem = limitError(choice.limit, range.min, range.max);
        const limit = parseLimit(choice.limit);
        const speed = limitProblem === null && limit !== null ? safeSpeedKmh(limit, corner.tightest_radius_m) : null;
        return (
          <div
            key={corner.number}
            className="grid grid-cols-2 sm:grid-cols-[2rem_1fr_7rem_6rem_7rem] gap-2 items-start p-2 rounded bg-[#161D26] border border-[#232B35]"
          >
            <span className="text-xs font-mono font-bold text-[#F2A93B] pt-2">#{corner.number}</span>
            <div className="col-span-2 sm:col-span-1 min-w-0">
              <input
                data-testid={`corner-name-${corner.number}`}
                aria-label={`Corner ${corner.number} name`}
                className={inputClass}
                value={choice.label}
                maxLength={MAX_LABEL_LENGTH}
                onChange={(e) => onChange(corner.number, { label: e.target.value })}
              />
              {nameProblem && <p className="text-[10px] text-[#E5473C] mt-1">{nameProblem}</p>}
            </div>
            <div className="min-w-0">
              <input
                data-testid={`corner-limit-${corner.number}`}
                aria-label={`Corner ${corner.number} limit in g`}
                className={inputClass}
                inputMode="decimal"
                value={choice.limit}
                onChange={(e) => onChange(corner.number, { limit: e.target.value })}
              />
              <p className="text-[10px] mt-1" style={{ color: limitProblem ? "#E5473C" : "#7C8898" }}>
                {limitProblem ?? "g limit"}
              </p>
            </div>
            <div className="text-xs font-mono text-[#7C8898] pt-2" data-testid={`corner-radius-${corner.number}`}>
              {corner.tightest_radius_m.toFixed(1)} m
            </div>
            <div className="text-xs font-mono text-[#E7EDF3] pt-2" data-testid={`corner-speed-${corner.number}`}>
              {speed === null ? "—" : `${speed.toFixed(0)} km/h`}
              <span className="block text-[10px] text-[#7C8898]">safe speed</span>
            </div>
          </div>
        );
      })}
    </div>
  );
}
