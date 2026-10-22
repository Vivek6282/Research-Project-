/**
 * Trackside Coach — demo status and controls: state, lap x of y, Stop, Watch live, Open live visualizer.
 */

import { Eye, ExternalLink, Square } from "lucide-react";
import type { DemoAvailability, DemoStatus } from "../hooks/use-demo-run";

interface DemoStatusPanelProps {
  availability: DemoAvailability;
  status: DemoStatus | null;
  actionError: string | null;
  onStop: () => void;
  onWatchLive: (driverId: string) => void;
}

const STATE_TEXT: Record<string, { text: string; color: string }> = {
  idle: { text: "No demo running", color: "#7C8898" },
  running: { text: "Running", color: "#33D17E" },
  finished: { text: "Finished", color: "#3FA6E0" },
  stopped: { text: "Stopped", color: "#F2A93B" },
  failed: { text: "Failed", color: "#E5473C" },
};
const buttonClass = "inline-flex items-center gap-1.5 text-[11px] font-mono px-3 py-1.5 min-h-[34px] rounded-[2px] border cursor-pointer";

/** "Limits in force: Hairpin 1.00 / Sweeper 1.32", or "Zone defaults" when the driver has no limit of their own. */
function limitsText(limits: Record<string, number> | null | undefined, isCustom: boolean | null | undefined): string | null {
  if (!limits || Object.keys(limits).length === 0) return null;
  if (!isCustom) return "Zone defaults";
  return `Limits in force: ${Object.entries(limits).map(([name, value]) => `${name} ${value.toFixed(2)}`).join(" / ")}`;
}

/** The panel; shows a short note instead of controls when demo tools are not available. */
export function DemoStatusPanel({ availability, status, actionError, onStop, onWatchLive }: DemoStatusPanelProps) {
  if (availability === "checking") return null;
  if (availability !== "available") {
    return (
      <p data-testid="demo-unavailable" className="text-[11px] font-mono text-[#7C8898] border border-dashed border-[#232B35] rounded p-2">
        {availability === "production"
          ? "Demo controls are not available on a production server. You can still view maps and edit corners."
          : "Demo controls are switched off (VITE_ENABLE_DEMO_TOOLS or DEMO_TOOLS_ENABLED). You can still view maps and edit corners."}
      </p>
    );
  }
  const state = status?.state ?? "idle";
  const view = STATE_TEXT[state] ?? STATE_TEXT.idle;
  const run = status?.run;
  const lapText = state === "running" && status?.laps ? ` · lap ${status.current_lap ?? 1} of ${status.laps}` : "";
  return (
    <div data-testid="demo-status-panel" className="flex flex-col gap-2 p-3 rounded border border-[#232B35] bg-[#161D26]">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span data-testid="demo-state" className="text-xs font-mono font-bold" style={{ color: view.color }}>
          {view.text}{lapText}
        </span>
        <div className="flex flex-wrap gap-2">
          {state === "running" && (
            <button data-testid="demo-stop-btn" onClick={onStop} className={`${buttonClass} border-[#E5473C] text-[#E5473C]`}><Square size={13} /> Stop</button>
          )}
          {run && (
            <button data-testid="demo-watch-live-btn" onClick={() => onWatchLive(run.driver_id)} className={`${buttonClass} border-[#232B35] text-[#3FA6E0]`}><Eye size={13} /> Watch live</button>
          )}
          <button data-testid="demo-open-visualizer-btn" onClick={() => window.open("/demo/track_visualization.html", "_blank", "noopener,noreferrer")}
            className={`${buttonClass} border-[#232B35] text-[#3FA6E0]`}><ExternalLink size={13} /> Open live visualizer</button>
        </div>
      </div>
      {run && (
        <p data-testid="demo-run-facts" className="text-[11px] font-mono text-[#7C8898]">
          {run.track_name} · {run.driver_name} · {run.laps} {run.laps === 1 ? "lap" : "laps"} · {run.pace_applied ? `pace ${run.pace}` : "fixed demo pattern"}
        </p>
      )}
      {run && limitsText(status?.limits, status?.limits_custom) && (
        <p data-testid="demo-limits" className="text-[11px] font-mono text-[#7C8898]">{limitsText(status?.limits, status?.limits_custom)}</p>
      )}
      {state === "running" && status?.bridge_connected === false && (
        <p className="text-[11px] font-mono text-[#F2A93B]">The glove bridge is not connected: close the Arduino Serial Monitor and check SERIAL_PORT in trackside/demo/.env.</p>
      )}
      {state === "running" && status?.bridge_connected === true && (
        <p className="text-[11px] font-mono text-[#33D17E]">Glove bridge connected{status.port_hint ? ` (${status.port_hint})` : ""}.</p>
      )}
      {status?.error && <p data-testid="demo-error" className="text-[11px] text-[#E5473C]">{status.error}</p>}
      {actionError && <p data-testid="demo-action-error" role="alert" className="text-[11px] text-[#E5473C]">{actionError}</p>}
    </div>
  );
}
