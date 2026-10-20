/**
 * Trackside Coach Dashboard — Biometrics 3-Card Row Component.
 * Displays Phase 2 placeholder state for biometric strap sensors with no invented numbers.
 */

export function BiometricsCards() {
  return (
    <div data-testid="coach-panel-biometrics" className="grid grid-cols-1 sm:grid-cols-3 gap-3">
      {/* Heart Rate */}
      <div className="bg-[#12181F] border border-[#E8C547]/40 rounded-[2px] p-3 font-mono">
        <div className="flex items-center justify-between text-[10px] mb-2">
          <span className="text-[#E8C547] font-bold">| HEART RATE</span>
          <span className="text-[9px] bg-[#E8C547]/10 text-[#E8C547] px-1 rounded-[1px]">PHASE 2</span>
        </div>
        <div className="h-14 flex items-center justify-center text-center">
          <p className="text-[11px] text-[#7C8898]">
            No sensor connected — the biometric strap is Phase 2.
          </p>
        </div>
      </div>

      {/* Blood Oxygen */}
      <div className="bg-[#12181F] border border-[#E8C547]/40 rounded-[2px] p-3 font-mono">
        <div className="flex items-center justify-between text-[10px] mb-2">
          <span className="text-[#E8C547] font-bold">| BLOOD OXYGEN</span>
          <span className="text-[9px] bg-[#E8C547]/10 text-[#E8C547] px-1 rounded-[1px]">PHASE 2</span>
        </div>
        <div className="h-14 flex items-center justify-center text-center">
          <p className="text-[11px] text-[#7C8898]">
            No sensor connected — the biometric strap is Phase 2.
          </p>
        </div>
      </div>

      {/* Breathing */}
      <div className="bg-[#12181F] border border-[#E8C547]/40 rounded-[2px] p-3 font-mono">
        <div className="flex items-center justify-between text-[10px] mb-2">
          <span className="text-[#E8C547] font-bold">| BREATHING</span>
          <span className="text-[9px] bg-[#E8C547]/10 text-[#E8C547] px-1 rounded-[1px]">PHASE 2</span>
        </div>
        <div className="h-14 flex items-center justify-center text-center">
          <p className="text-[11px] text-[#7C8898]">
            No sensor connected — the biometric strap is Phase 2.
          </p>
        </div>
      </div>
    </div>
  );
}
