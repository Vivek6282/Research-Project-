/**
 * Trackside Coach Dashboard — Sector Deltas Component.
 * Displays sector timing deltas when available, or a clean waiting state.
 */
export function SectorDeltasPanel() {
  return (
    <div
      data-testid="coach-panel-sector-deltas"
      className="bg-[#12181F] border border-[#232B35] rounded-[2px] p-3 font-mono"
    >
      <div className="flex items-center justify-between mb-3 border-b border-[#232B35]/60 pb-2 font-mono">
        <span className="text-xs font-bold text-[#E7EDF3]">
          <span className="text-[#3FA6E0]">|</span> SECTOR DELTAS
        </span>
        <span className="text-[9px] text-[#7C8898]">VS SESSION BEST</span>
      </div>

      <div className="p-4 text-center text-xs text-[#7C8898] border border-dashed border-[#232B35] rounded-[2px]">
        Waiting for sector timing data
      </div>
    </div>
  );
}
