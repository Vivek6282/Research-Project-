/**
 * Trackside Coach Dashboard — Historical Sessions Tab Component.
 * Displays searchable past academy driving sessions, telemetry metrics, and alert summaries.
 */

import { HistoricalSession } from "../types";

interface HistoricalSessionsTabProps {
  historicalSessions: HistoricalSession[];
  sessionsError?: string | null;
  onRetry?: () => void;
}

/**
 * Displays historical academy sessions or clear empty and error states.
 */
export function HistoricalSessionsTab({
  historicalSessions,
  sessionsError,
  onRetry,
}: HistoricalSessionsTabProps) {
  return (
    <main className="max-w-[1400px] mx-auto px-2.5 sm:px-4 py-3 sm:py-4 font-mono">
      <div className="bg-[#12181F] border border-[#232B35] rounded-[2px] p-3 sm:p-4">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 mb-4 border-b border-[#232B35]/60 pb-3">
          <div>
            <h2 className="text-sm font-bold text-[#E7EDF3]">HISTORICAL ACADEMY SESSIONS</h2>
            <p className="text-xs text-[#7C8898]">
              Raw session telemetry records and historical coach notes
            </p>
          </div>
          <span
            data-testid="coach-historical-count"
            className="text-xs text-[#3FA6E0] font-bold bg-[#3FA6E0]/10 border border-[#3FA6E0]/30 px-2 py-1 rounded-[2px]"
          >
            {historicalSessions.length} SESSIONS RECORDED
          </span>
        </div>

        {sessionsError ? (
          <div className="p-4 text-center text-xs text-[#E5473C] bg-[#E5473C]/10 border border-[#E5473C]/30 rounded-[2px] font-mono">
            <p className="mb-2">{sessionsError}</p>
            {onRetry && (
              <button
                onClick={onRetry}
                className="px-3 py-1 bg-[#232B35] hover:bg-[#2A3441] text-[#E7EDF3] rounded-[2px] text-xs border border-[#3A4553]"
              >
                Retry
              </button>
            )}
          </div>
        ) : historicalSessions.length === 0 ? (
          <div
            data-testid="coach-historical-empty"
            className="p-6 text-center text-xs text-[#7C8898] border border-dashed border-[#232B35] rounded-[2px]"
          >
            No sessions recorded yet.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table data-testid="coach-historical-table" className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-[#232B35] text-[#7C8898]">
                  <th className="py-2 px-3">SESSION ID</th>
                  <th className="py-2 px-3">DRIVER</th>
                  <th className="py-2 px-3">KART</th>
                  <th className="py-2 px-3">DATE</th>
                  <th className="py-2 px-3">DURATION</th>
                  <th className="py-2 px-3">MODE</th>
                  <th className="py-2 px-3">BEST LAP</th>
                  <th className="py-2 px-3">MAX G</th>
                  <th className="py-2 px-3">ALERTS</th>
                </tr>
              </thead>
              <tbody>
                {historicalSessions.map((s) => (
                  <tr
                    key={s.id}
                    data-testid="coach-historical-row"
                    className="border-b border-[#232B35]/60 hover:bg-[#161D26]"
                  >
                    <td className="py-2.5 px-3 font-bold text-[#3FA6E0]">
                      {s.id}
                      {s.isDemo && (
                        <span
                          data-testid="coach-demo-run-label"
                          title="Simulated run started from Maps & Demo, not real driving"
                          className="ml-2 text-[10px] font-bold px-1.5 py-0.5 rounded border border-[#F2A93B66] bg-[#F2A93B14] text-[#F2A93B]"
                        >
                          DEMO RUN
                        </span>
                      )}
                    </td>
                    <td className="py-2.5 px-3 text-[#E7EDF3] font-semibold">{s.driver}</td>
                    <td className="py-2.5 px-3 text-[#7C8898]">{s.kart}</td>
                    <td className="py-2.5 px-3 text-[#7C8898]">{s.date}</td>
                    <td className="py-2.5 px-3 text-[#E7EDF3]">{s.duration}</td>
                    <td className="py-2.5 px-3 text-[#33D17E]">{s.mode}</td>
                    <td className="py-2.5 px-3 text-[#E7EDF3] font-bold">{s.bestLap}</td>
                    <td className="py-2.5 px-3 text-[#F2A93B]">{s.maxG}</td>
                    <td className="py-2.5 px-3 text-[#E5473C] font-bold">{s.alerts}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </main>
  );
}
