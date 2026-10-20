/**
 * Trackside Admin Dashboard — Audit Trail & System Diagnostics Component.
 * Displays 30-day user modification history with cryptographic audit trail,
 * and active hardware node connectivity with query latency telemetry.
 */

import { Shield, Activity } from "lucide-react";
import { Panel } from "../../../components/ui/panel";
import { AuditEntry, DiagnosticsData } from "../types";

interface AuditAndDiagnosticsProps {
  auditLogs: AuditEntry[];
  audit30DayCount: number;
  diagnostics: DiagnosticsData | null;
}

export function AuditAndDiagnostics({
  auditLogs,
  audit30DayCount,
  diagnostics,
}: AuditAndDiagnosticsProps) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
      <Panel testId="admin-audit-log-panel" title="Security & Audit Trail" icon={Shield}>
        <div className="space-y-3">
          <p className="text-xs font-mono text-[#E7EDF3] flex items-center justify-between">
            <span>
              <strong className="text-[#3FA6E0] font-bold">{audit30DayCount}</strong> user modification
              {audit30DayCount === 1 ? "" : "s"} logged to audit store in the last 30 days.
            </span>
            <span className="text-[10px] text-[#7C8898] uppercase">CSRF & Session Enforced</span>
          </p>

          {/* Audit Log Entries List */}
          <div className="max-h-48 overflow-y-auto divide-y divide-[#232B35] rounded border border-[#232B35] bg-[#0A0E13] p-2">
            {auditLogs.length === 0 ? (
              <div className="text-[11px] font-mono text-[#7C8898] py-2 text-center">
                No user modification audit entries recorded yet.
              </div>
            ) : (
              auditLogs.map((entry) => {
                const actionColor =
                  entry.action === "CREATE_USER" || entry.action === "REACTIVATE_USER"
                    ? "#33D17E"
                    : entry.action === "DEACTIVATE_USER" || entry.action === "DELETE_USER"
                    ? "#E5473C"
                    : "#3FA6E0";

                return (
                  <div
                    key={entry.id}
                    data-testid="admin-audit-log-entry"
                    className="py-1.5 px-1 text-[11px] font-mono flex items-center justify-between"
                  >
                    <div className="flex items-center gap-2">
                      <span
                        className="px-1.5 py-0.5 rounded text-[9px] uppercase font-bold"
                        style={{
                          color: actionColor,
                          border: `1px solid ${actionColor}44`,
                          background: `${actionColor}10`,
                        }}
                      >
                        {entry.action.replace("_", " ")}
                      </span>
                      <span className="text-[#E7EDF3] font-medium">
                        {entry.details || `${entry.actor_name} -> ${entry.target_user_name}`}
                      </span>
                    </div>
                    <span className="text-[10px] text-[#7C8898]">
                      {new Date(entry.timestamp).toLocaleTimeString([], {
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </span>
                  </div>
                );
              })
            )}
          </div>
        </div>
      </Panel>

      <Panel title="Telemetry Diagnostics" icon={Activity}>
        <div className="space-y-3 font-mono text-xs text-[#E7EDF3]">
          <div className="p-3 rounded border border-[#232B35] bg-[#0A0E13] space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-[#7C8898]">Active Registered Nodes:</span>
              <span className="font-bold text-[#33D17E]">
                {diagnostics ? diagnostics.active_nodes : 0} /{" "}
                {diagnostics ? diagnostics.total_nodes : 0} Connected
              </span>
            </div>

            <div className="flex items-center justify-between">
              <span className="text-[#7C8898]">Packet Drops (60 min):</span>
              <div className="flex items-center gap-1.5">
                <span className="font-bold text-[#E7EDF3]">
                  {diagnostics ? diagnostics.packet_drops_last_60_min : 0}
                </span>
              </div>
            </div>

            <div className="flex items-center justify-between border-t border-[#232B35] pt-2 mt-2">
              <span className="text-[#7C8898]">Database ORM Query Time:</span>
              <span className="font-bold text-[#3FA6E0]">
                {diagnostics ? diagnostics.db_query_time_ms : 0}ms
              </span>
            </div>
          </div>
        </div>
      </Panel>
    </div>
  );
}
