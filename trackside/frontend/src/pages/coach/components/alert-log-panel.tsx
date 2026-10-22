/**
 * Trackside Coach Dashboard — Live Alert Log.
 * The alerts that arrived over the live stream (newest first). Clear only empties this local list.
 */

import { AlertLogEntry } from "../hooks/use-live-readings";

const SEVERITY_COLOR = { amber: "#F2A93B", red: "#E5473C" };

interface AlertLogPanelProps {
  alerts: AlertLogEntry[];
  onClear: () => void;
}

/** The time of day of an alert, or a dash when the time is not readable. */
function timeOf(iso: string): string {
  const moment = new Date(iso);
  return Number.isNaN(moment.getTime()) ? "-" : moment.toLocaleTimeString("en-GB");
}

export function AlertLogPanel({ alerts, onClear }: AlertLogPanelProps) {
  return (
    <div className="border border-[#232B35] bg-[#0A0E13] rounded-[2px] p-2.5 min-w-0">
      <div className="mb-1.5 flex items-center justify-between">
        <span className="text-[10px] font-bold uppercase tracking-wider text-[#7C8898]">{alerts.length} ALERTS</span>
        <button
          data-testid="alert-log-clear"
          onClick={onClear}
          className="text-[10px] px-2 py-0.5 rounded-[2px] border border-[#232B35] text-[#7C8898] hover:text-[#E7EDF3] cursor-pointer"
        >
          Clear
        </button>
      </div>
      <div data-testid="alert-log" className="overflow-y-auto text-xs" style={{ maxHeight: 90 }}>
        {alerts.length === 0 ? (
          <div className="py-2 text-[#7C8898]">No alerts yet</div>
        ) : (
          alerts.map((alert) => (
            <div key={alert.id} className="flex items-center gap-2 py-0.5 min-w-0">
              <span className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: SEVERITY_COLOR[alert.severity] }} />
              <span className="text-[#E7EDF3] truncate">{alert.zone_label ?? "-"}</span>
              <span className="text-[#7C8898] whitespace-nowrap">{alert.g_value.toFixed(2)} g / {alert.threshold_applied.toFixed(2)} g</span>
              <span className="ml-auto text-[#7C8898] whitespace-nowrap">{timeOf(alert.triggered_at)}</span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
