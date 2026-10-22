/**
 * Trackside Driver Dashboard — Corner Times (read-only).
 * Last completed lap and best time through each corner of the latest session.
 */

import { Panel } from "../../../components/ui/panel";
import { Timer } from "lucide-react";
import { formatSeconds, useCornerDeltas } from "../../../lib/use-corner-deltas";

interface CornerTimesPanelProps {
  sessionId: string | null;
}

export function CornerTimesPanel({ sessionId }: CornerTimesPanelProps) {
  const { corners } = useCornerDeltas(sessionId, null, false);

  return (
    <Panel testId="driver-panel-corner-times" title="Corner Times" icon={Timer}>
      {corners.length === 0 ? (
        <div className="text-xs font-mono text-[#7C8898] py-2">—</div>
      ) : (
        <table className="w-full text-xs font-mono">
          <thead>
            <tr className="text-[10px] text-[#7C8898] text-left">
              <th className="font-normal pb-1">Corner</th>
              <th className="font-normal pb-1 text-right">Last lap</th>
              <th className="font-normal pb-1 text-right">Best</th>
            </tr>
          </thead>
          <tbody>
            {corners.map((corner) => (
              <tr key={corner.zone_id} data-testid={`corner-time-row-${corner.label}`}>
                <td className="py-0.5 text-[#E7EDF3]">{corner.label}</td>
                <td className="py-0.5 text-right text-[#7C8898]">{formatSeconds(corner.last_lap_s)}</td>
                <td className="py-0.5 text-right text-[#33D17E]">{formatSeconds(corner.best_s)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </Panel>
  );
}
