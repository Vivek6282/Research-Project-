/**
 * Trackside Coach Dashboard — Lateral-g Waveform.
 * The last 3 seconds of lateral g as a plain SVG line, coloured by the current stage,
 * with a dashed red line at the limit and a dashed amber line at 82% of it (only when a limit exists).
 */

import { G_WINDOW_MS, GSample } from "../hooks/use-live-readings";

const WIDTH = 300;
const HEIGHT = 90;
const AMBER_SHARE = 0.82;

interface LateralGWaveformProps {
  gWindow: GSample[];
  limit: number | null;
  stageColor: string;
}

export function LateralGWaveform({ gWindow, limit, stageColor }: LateralGWaveformProps) {
  const highest = Math.max(...gWindow.map((s) => s.g), 0);
  const top = Math.max(limit !== null ? 1.2 * limit : 0, highest);
  const lastT = gWindow.length > 0 ? gWindow[gWindow.length - 1].t : 0;
  const x = (t: number) => WIDTH - ((lastT - t) / G_WINDOW_MS) * WIDTH;
  const y = (g: number) => HEIGHT - (top > 0 ? (g / top) * HEIGHT : 0);
  const points = gWindow.map((s) => `${x(s.t).toFixed(1)},${y(s.g).toFixed(1)}`).join(" ");

  return (
    <div className="border border-[#232B35] bg-[#0A0E13] rounded-[2px] p-2.5 min-w-0">
      <div className="mb-1.5 text-[10px] font-bold uppercase tracking-wider text-[#7C8898]">LATERAL-G WAVEFORM (3 s)</div>
      {gWindow.length === 0 ? (
        <div data-testid="g-waveform" className="flex items-center justify-center text-xs text-[#7C8898]" style={{ height: HEIGHT }}>
          Waiting for live data
        </div>
      ) : (
        <svg data-testid="g-waveform" viewBox={`0 0 ${WIDTH} ${HEIGHT}`} preserveAspectRatio="none" className="w-full" style={{ height: HEIGHT }}>
          {limit !== null && (
            <>
              <line x1="0" x2={WIDTH} y1={y(limit)} y2={y(limit)} stroke="#E5473C" strokeWidth="1" strokeDasharray="4 3" vectorEffect="non-scaling-stroke" />
              <line x1="0" x2={WIDTH} y1={y(limit * AMBER_SHARE)} y2={y(limit * AMBER_SHARE)} stroke="#F2A93B" strokeWidth="1" strokeDasharray="4 3" vectorEffect="non-scaling-stroke" />
            </>
          )}
          <polyline points={points} fill="none" stroke={stageColor} strokeWidth="2" strokeLinejoin="round" vectorEffect="non-scaling-stroke" />
        </svg>
      )}
    </div>
  );
}
