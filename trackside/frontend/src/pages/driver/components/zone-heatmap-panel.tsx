/**
 * Trackside Driver Dashboard — Zone Heatmap Panel.
 * Displays zone risk breakdown and telemetry exceedances over the last 5 sessions.
 */

import { Gauge } from "lucide-react";
import { Panel } from "../../../components/ui/panel";
import { ZoneSummary } from "../hooks/use-driver-dashboard";

interface ZoneHeatmapPanelProps {
  loading: boolean;
  hasSessions: boolean;
  zones: ZoneSummary[];
}

export function ZoneHeatmapPanel({ loading, hasSessions, zones }: ZoneHeatmapPanelProps) {
  return (
    <Panel testId="driver-panel-zone-heatmap" title="Zone Risk Heatmap (Last 5 Sessions)" icon={Gauge}>
      {loading ? (
        <div className="text-center py-6 text-xs font-mono text-[#7C8898]">
          Loading zone alert summary…
        </div>
      ) : !hasSessions || zones.length === 0 ? (
        <div
          data-testid="driver-no-sessions-msg"
          className="rounded-lg p-6 text-center border border-[#232B35] bg-[#161D26] font-mono text-[#7C8898]"
        >
          <Gauge className="mx-auto mb-2 opacity-50 text-[#3FA6E0]" size={28} />
          <p className="text-sm font-bold text-[#E7EDF3]">No sessions recorded yet</p>
          <p className="text-xs text-[#7C8898] mt-1">
            Start a driving session to track zone risk heatmap and telemetry exceedances.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          {zones.map((z) => (
            <div
              key={z.name}
              className="rounded-lg p-3.5 text-center flex flex-col items-center justify-between border transition-all duration-150"
              style={{
                background: "#161D26",
                borderColor: `${z.color}33`,
                boxShadow: `0 4px 15px ${z.color}10`,
              }}
            >
              <span
                className="text-[10px] font-mono font-bold uppercase px-2 py-0.5 rounded mb-2"
                style={{
                  color: z.color,
                  border: `1px solid ${z.color}44`,
                  background: `${z.color}14`,
                }}
              >
                {z.status}
              </span>

              <p className="text-3xl font-mono font-bold my-1" style={{ color: z.color }}>
                {z.count}
              </p>

              <p className="text-xs font-mono text-[#7C8898]">{z.name} Exceedances</p>
            </div>
          ))}
        </div>
      )}
    </Panel>
  );
}
