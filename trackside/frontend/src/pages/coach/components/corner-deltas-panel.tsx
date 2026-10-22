/**
 * Trackside Coach Dashboard — Corner Deltas Component.
 * One row per corner of the session's track: last completed lap time through the
 * corner and how far it is from the session's best for that corner.
 */

import { CornerDelta, formatDelta, formatSeconds, useCornerDeltas } from "../../../lib/use-corner-deltas";

const GREEN = "#33D17E";
const AMBER = "#F2A93B";

interface CornerDeltasPanelProps {
  sessionId: string | null;
  lapNumber: number | null;
  isLive: boolean;
}

/** Green for zero or faster than the best, amber for slower, grey when there is no delta. */
function deltaColor(delta: number | null): string {
  if (delta === null) return "#7C8898";
  return delta <= 0 ? GREEN : AMBER;
}

export function CornerDeltasPanel({ sessionId, lapNumber, isLive }: CornerDeltasPanelProps) {
  const { corners } = useCornerDeltas(sessionId, lapNumber, isLive);
  const hasData = corners.some((c: CornerDelta) => c.last_lap_s !== null);

  return (
    <div
      data-testid="coach-panel-corner-deltas"
      className="bg-[#12181F] border border-[#232B35] rounded-[2px] p-3 font-mono"
    >
      <div className="mb-3 border-b border-[#232B35]/60 pb-2 text-xs font-bold text-[#E7EDF3]">
        <span className="text-[#3FA6E0]">|</span> CORNER DELTAS vs SESSION BEST
      </div>

      {hasData ? (
        <table className="w-full text-xs">
          <tbody>
            {corners.map((corner) => (
              <tr key={corner.zone_id} data-testid={`corner-delta-row-${corner.label}`} className="border-b border-[#232B35]/40 last:border-0">
                <td className="py-1 text-[#E7EDF3]">{corner.label}</td>
                <td className="py-1 text-right text-[#7C8898]">{formatSeconds(corner.last_lap_s)}</td>
                <td className="py-1 pl-3 text-right font-bold" style={{ color: deltaColor(corner.last_lap_delta_s) }}>
                  {formatDelta(corner.last_lap_delta_s)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <div className="p-4 text-center text-xs text-[#7C8898] border border-dashed border-[#232B35] rounded-[2px]">
          Waiting for completed laps
        </div>
      )}

      <p className="mt-2 text-[9px] text-[#7C8898]">Sector split timing (GPS split lines) is Phase 2.</p>
    </div>
  );
}
