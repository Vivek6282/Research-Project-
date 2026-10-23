/**
 * Trackside Driver Dashboard — Current Session Panel.
 * The driver's latest run: when it started, its state, laps, alerts and duration.
 * These are the same facts the Coach sees for this driver, read from the same session.
 */

import { Flag } from "lucide-react";
import { Panel } from "../../../components/ui/panel";
import { LatestSessionData } from "../hooks/use-driver-dashboard";

interface SessionStatusPanelProps {
  latestSession: LatestSessionData | null;
}

/** The state word and colour for the session: LIVE while readings arrive, ENDED once it is finished. */
function stateOf(session: LatestSessionData): { label: string; color: string } {
  if (session.live) return { label: "LIVE", color: "#33D17E" };
  if (session.ended_at) return { label: "ENDED", color: "#7C8898" };
  return { label: "WAITING FOR DATA", color: "#F2A93B" };
}

/** A date such as "2026-10-23 14:05", or a dash when the session has no start time. */
function startedText(startedAt: string | undefined): string {
  if (!startedAt) return "—";
  const date = new Date(startedAt);
  return Number.isNaN(date.getTime()) ? "—" : date.toLocaleString([], { dateStyle: "medium", timeStyle: "short" });
}

/** One label and value cell. */
function Fact({ label, value, testId }: { label: string; value: string | number; testId: string }) {
  return (
    <div>
      <p className="text-[10px] text-[#7C8898] uppercase">{label}</p>
      <p data-testid={testId} className="text-sm font-bold text-[#E7EDF3]">{value}</p>
    </div>
  );
}

export function SessionStatusPanel({ latestSession }: SessionStatusPanelProps) {
  const state = latestSession ? stateOf(latestSession) : null;
  return (
    <Panel testId="driver-panel-session-status" title="Current Session" icon={Flag}>
      {latestSession && state ? (
        <div className="space-y-2 font-mono">
          <div className="flex items-center justify-between">
            <span className="text-xs text-[#7C8898]">{latestSession.track_name} · {latestSession.mode}</span>
            <span
              data-testid="driver-session-state"
              className="text-[10px] font-bold px-2 py-0.5 rounded border"
              style={{ color: state.color, borderColor: `${state.color}66`, background: `${state.color}14` }}
            >
              {state.label}
            </span>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <Fact label="Started" value={startedText(latestSession.started_at)} testId="driver-session-started" />
            <Fact label="Laps" value={latestSession.laps ?? "—"} testId="driver-session-laps" />
            <Fact label="Alerts" value={latestSession.alert_count ?? 0} testId="driver-session-alerts" />
            <Fact label="Duration" value={latestSession.duration || "—"} testId="driver-session-duration" />
          </div>
        </div>
      ) : (
        <div className="text-xs font-mono text-[#7C8898] py-2">No session yet. It appears here when the coach starts a run.</div>
      )}
    </Panel>
  );
}
