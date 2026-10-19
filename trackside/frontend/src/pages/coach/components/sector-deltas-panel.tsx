/**
 * Trackside Coach Dashboard — Sector Deltas Component.
 * Displays Sector 1, 2, and 3 deltas against session best lap with visual progress indicators.
 */

export function SectorDeltasPanel() {
  const s1 = 28.104;
  const s2 = 31.882;
  const s3 = 24.326;

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

      <div className="space-y-3 font-mono">
        <div>
          <div className="flex justify-between text-[11px] mb-1">
            <span className="text-[#7C8898]">SECTOR 1 (HAIRPIN ENTRY)</span>
            <span className="text-[#33D17E] font-bold">{s1}s (-0.142)</span>
          </div>
          <div className="w-full h-1.5 bg-[#0A0E13] rounded-[1px] overflow-hidden">
            <div className="h-full bg-[#33D17E] w-[65%]" />
          </div>
        </div>

        <div>
          <div className="flex justify-between text-[11px] mb-1">
            <span className="text-[#7C8898]">SECTOR 2 (MID CHICANE)</span>
            <span className="text-[#E5473C] font-bold">{s2}s (+0.310)</span>
          </div>
          <div className="w-full h-1.5 bg-[#0A0E13] rounded-[1px] overflow-hidden">
            <div className="h-full bg-[#E5473C] w-[80%]" />
          </div>
        </div>

        <div>
          <div className="flex justify-between text-[11px] mb-1">
            <span className="text-[#7C8898]">SECTOR 3 (FINAL APEX)</span>
            <span className="text-[#33D17E] font-bold">{s3}s (-0.088)</span>
          </div>
          <div className="w-full h-1.5 bg-[#0A0E13] rounded-[1px] overflow-hidden">
            <div className="h-full bg-[#33D17E] w-[55%]" />
          </div>
        </div>
      </div>
    </div>
  );
}
