/**
 * Trackside Driver Dashboard — Best Lap and Session Target Evaluation Panels.
 * Displays cleanest lap highlight and coach goal compliance results.
 */

import { Trophy, Target } from "lucide-react";
import { Panel } from "../../../components/ui/panel";
import { LatestSessionData } from "../hooks/use-driver-dashboard";

interface BestLapTargetPanelProps {
  latestSession: LatestSessionData | null;
}

export function BestLapTargetPanel({ latestSession }: BestLapTargetPanelProps) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
      <Panel testId="driver-panel-best-lap" title="Best Lap Highlight (Raw Telemetry)" icon={Trophy}>
        {latestSession ? (
          <div className="space-y-1 font-mono">
            <div className="flex items-baseline justify-between">
              <span className="text-2xl font-mono font-bold text-[#33D17E]">
                {latestSession.best_lap_time || "—"}
              </span>
              <span className="text-xs font-mono text-[#7C8898]">SESSION BEST</span>
            </div>
            <p className="text-xs text-[#7C8898]">
              Cleanest lap on {latestSession.track_name} — minimal threshold exceedances recorded.
            </p>
          </div>
        ) : (
          <div className="text-xs font-mono text-[#7C8898] py-2">
            No session recorded yet to calculate best lap highlight.
          </div>
        )}
      </Panel>

      <Panel testId="driver-panel-target-evaluation" title="Session Target Evaluation" icon={Target}>
        {latestSession && latestSession.goal_text && latestSession.goal_text.trim() ? (
          <div className="space-y-1 font-mono">
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono text-[#E7EDF3] font-bold">
                {latestSession.goal_text}
              </span>
              {latestSession.goal_passed === true ? (
                <span className="text-xs font-mono font-bold text-[#33D17E] px-2 py-0.5 rounded border border-[#33D17E44] bg-[#33D17E14]">
                  PASSED
                </span>
              ) : latestSession.goal_passed === false ? (
                <span className="text-xs font-mono font-bold text-[#E5473C] px-2 py-0.5 rounded border border-[#E5473C44] bg-[#E5473C14]">
                  NOT MET
                </span>
              ) : (
                <span className="text-xs font-mono font-bold text-[#F2A93B] px-2 py-0.5 rounded border border-[#F2A93B44] bg-[#F2A93B14]">
                  PENDING
                </span>
              )}
            </div>
            <p className="text-xs text-[#7C8898]">
              {latestSession.goal_passed === true
                ? "Session target achieved cleanly."
                : latestSession.goal_passed === false
                ? "Target not met — exceedances recorded during session."
                : "Target evaluation pending post-session coach review."}
            </p>
          </div>
        ) : (
          <div className="text-xs font-mono text-[#7C8898] py-2">
            No goal set for this session
          </div>
        )}
      </Panel>
    </div>
  );
}
