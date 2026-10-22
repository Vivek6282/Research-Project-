/**
 * Trackside Coach Dashboard — Live Readouts Bar.
 * Four cells under the Live Track View header: lap, corner, g with the limit in force, speed.
 */

interface LiveReadoutsBarProps {
  currentLap: number | null;
  zoneLabel: string | null;
  cornerType: string | null;
  isStraight: boolean;
  currentG: number | null;
  currentLimit: number | null;
  currentSpeed: number | null;
}

/** One labelled cell. */
function Cell({ label, testId, children }: { label: string; testId: string; children: React.ReactNode }) {
  return (
    <div className="min-w-0 border border-[#232B35] bg-[#0A0E13] rounded-[2px] px-2.5 py-1.5">
      <div className="text-[9px] uppercase tracking-wider text-[#7C8898]">{label}</div>
      <div data-testid={testId} className="text-sm font-bold text-[#E7EDF3] truncate">{children}</div>
    </div>
  );
}

export function LiveReadoutsBar({
  currentLap, zoneLabel, cornerType, isStraight, currentG, currentLimit, currentSpeed,
}: LiveReadoutsBarProps) {
  const corner = isStraight ? "Straight" : zoneLabel ? `${zoneLabel}${cornerType ? ` · ${cornerType}` : ""}` : "-";
  const hasG = currentG !== null;
  return (
    <div data-testid="live-readouts-bar" className="grid grid-cols-2 sm:grid-cols-4 gap-2 mb-3">
      <Cell label="Lap" testId="live-lap">{currentLap ?? "-"}</Cell>
      <Cell label="Corner" testId="live-zone">{corner}</Cell>
      <Cell label="G" testId="live-g">
        {hasG ? `${currentG.toFixed(2)} g` : "-"}{" "}
        <span data-testid="live-limit" className="text-[10px] font-normal text-[#7C8898]">
          {currentLimit !== null ? `limit ${currentLimit.toFixed(2)} g` : hasG ? "No limit" : "-"}
        </span>
      </Cell>
      <Cell label="Speed" testId="live-speed">{currentSpeed !== null ? `${currentSpeed} km/h` : "-"}</Cell>
    </div>
  );
}
