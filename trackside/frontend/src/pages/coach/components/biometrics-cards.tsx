/**
 * Trackside Coach Dashboard — Biometrics 3-Card Row Component.
 * Displays Heart Rate, Blood Oxygen, and Breathing Rate sparklines and real-time values.
 */

interface BiometricsCardsProps {
  currentHr: number;
  currentSpo2: number;
  currentBreathing: number;
  hrHistory: number[];
  spo2History: number[];
  breathingHistory: number[];
}

export function BiometricsCards({
  currentHr,
  currentSpo2,
  currentBreathing,
  hrHistory,
  spo2History,
  breathingHistory,
}: BiometricsCardsProps) {
  const buildSvgPath = (points: number[]) => {
    const step = 200 / (points.length - 1);
    return points.reduce((acc, y, i) => `${acc} ${i === 0 ? "M" : "L"} ${i * step} ${y}`, "");
  };

  const buildAreaPath = (points: number[]) => {
    const step = 200 / (points.length - 1);
    const linePath = points.reduce((acc, y, i) => `${acc} ${i === 0 ? "M" : "L"} ${i * step} ${y}`, "");
    return `${linePath} L 200 40 L 0 40 Z`;
  };

  return (
    <div data-testid="coach-panel-biometrics" className="grid grid-cols-1 sm:grid-cols-3 gap-3">
      {/* Heart Rate */}
      <div className="bg-[#12181F] border border-[#232B35] rounded-[2px] p-3">
        <div className="flex items-center justify-between text-[10px] font-mono mb-2">
          <span className="text-[#E5473C] font-bold">| HEART RATE</span>
          <span className="text-[#7C8898]">60–190</span>
        </div>
        <div className="flex items-baseline gap-1 font-mono mb-2">
          <span className="text-2xl font-extrabold text-[#E5473C]">{currentHr}</span>
          <span className="text-[10px] text-[#7C8898]">bpm</span>
        </div>
        <div className="w-full h-12 bg-[#0A0E13] rounded-[1px] overflow-hidden p-1">
          <svg className="w-full h-full" viewBox="0 0 200 40" preserveAspectRatio="none">
            <path d={buildAreaPath(hrHistory)} fill="rgba(229, 71, 60, 0.15)" />
            <path d={buildSvgPath(hrHistory)} fill="none" stroke="#E5473C" strokeWidth="1.5" />
          </svg>
        </div>
      </div>

      {/* Blood Oxygen */}
      <div className="bg-[#12181F] border border-[#232B35] rounded-[2px] p-3">
        <div className="flex items-center justify-between text-[10px] font-mono mb-2">
          <span className="text-[#3FA6E0] font-bold">| BLOOD OXYGEN</span>
          <span className="text-[#7C8898]">95–100</span>
        </div>
        <div className="flex items-baseline gap-1 font-mono mb-2">
          <span className="text-2xl font-extrabold text-[#3FA6E0]">{currentSpo2}</span>
          <span className="text-[10px] text-[#7C8898]">%</span>
        </div>
        <div className="w-full h-12 bg-[#0A0E13] rounded-[1px] overflow-hidden p-1">
          <svg className="w-full h-full" viewBox="0 0 200 40" preserveAspectRatio="none">
            <path d={buildAreaPath(spo2History)} fill="rgba(63, 166, 224, 0.15)" />
            <path d={buildSvgPath(spo2History)} fill="none" stroke="#3FA6E0" strokeWidth="1.5" />
          </svg>
        </div>
      </div>

      {/* Breathing */}
      <div className="bg-[#12181F] border border-[#232B35] rounded-[2px] p-3">
        <div className="flex items-center justify-between text-[10px] font-mono mb-2">
          <span className="text-[#33D17E] font-bold">| BREATHING</span>
          <span className="text-[#7C8898]">12–30</span>
        </div>
        <div className="flex items-baseline gap-1 font-mono mb-2">
          <span className="text-2xl font-extrabold text-[#33D17E]">{currentBreathing}</span>
          <span className="text-[10px] text-[#7C8898]">rpm</span>
        </div>
        <div className="w-full h-12 bg-[#0A0E13] rounded-[1px] overflow-hidden p-1">
          <svg className="w-full h-full" viewBox="0 0 200 40" preserveAspectRatio="none">
            <path d={buildAreaPath(breathingHistory)} fill="rgba(51, 209, 126, 0.15)" />
            <path d={buildSvgPath(breathingHistory)} fill="none" stroke="#33D17E" strokeWidth="1.5" />
          </svg>
        </div>
      </div>
    </div>
  );
}
