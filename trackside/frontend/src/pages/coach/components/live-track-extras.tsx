/**
 * Trackside Coach Dashboard — Live Track View extras.
 * Sits under the map: the lateral-g waveform (and, beside it on wide screens, the alert log).
 */

import { AlertLogEntry, GSample } from "../hooks/use-live-readings";
import { AlertLogPanel } from "./alert-log-panel";
import { LateralGWaveform } from "./lateral-g-waveform";

interface LiveTrackExtrasProps {
  gWindow: GSample[];
  limit: number | null;
  stageColor: string;
  alertLog: AlertLogEntry[];
  onClearAlerts: () => void;
}

export function LiveTrackExtras({ gWindow, limit, stageColor, alertLog, onClearAlerts }: LiveTrackExtrasProps) {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-3 mt-3">
      <LateralGWaveform gWindow={gWindow} limit={limit} stageColor={stageColor} />
      <AlertLogPanel alerts={alertLog} onClear={onClearAlerts} />
    </div>
  );
}
