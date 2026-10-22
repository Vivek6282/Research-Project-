/**
 * Trackside Maps — SVG picture of a track outline with numbered corners.
 */

import { useMemo } from "react";
import { loopRange, projectOutline } from "../outline-geometry";
import type { CornerPreview, LatLng } from "../types";

const WIDTH = 480;
const HEIGHT = 320;

interface OutlineSvgProps {
  outline: LatLng[];
  corners: CornerPreview[];
}

/** Draws the closed outline, the corner stretches in amber, and a numbered badge at each apex. */
export function OutlineSvg({ outline, corners }: OutlineSvgProps) {
  // Project once per outline so typing in the corner table does not redo the maths
  const projected = useMemo(() => projectOutline(outline, WIDTH, HEIGHT), [outline]);
  const pts = projected.points;
  if (pts.length < 3) return null;

  const toPath = (list: { x: number; y: number }[], close: boolean) =>
    list.map((p, i) => `${i === 0 ? "M" : "L"}${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(" ") + (close ? " Z" : "");

  return (
    <svg
      data-testid="outline-svg"
      viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
      className="w-full h-auto rounded bg-[#0A0E13] border border-[#232B35]"
      role="img"
      aria-label={`Track outline with ${corners.length} numbered corners`}
    >
      <path d={toPath(pts, true)} fill="none" stroke="#7C8898" strokeWidth={3} strokeLinejoin="round" />
      <circle cx={pts[0].x} cy={pts[0].y} r={4} fill="#3FA6E0">
        <title>Start</title>
      </circle>
      {corners.map((corner) => {
        const stretch = loopRange(corner.start_index, corner.end_index, pts.length).map((i) => pts[i]);
        const apex = pts[corner.apex_index];
        return (
          <g key={corner.number} data-testid={`outline-corner-${corner.number}`}>
            <path d={toPath(stretch, false)} fill="none" stroke="#F2A93B" strokeWidth={5} strokeLinecap="round" />
            <circle cx={apex.x} cy={apex.y} r={10} fill="#12181F" stroke="#F2A93B" strokeWidth={1.5} />
            <text x={apex.x} y={apex.y + 4} textAnchor="middle" fontSize={11} fontFamily="monospace" fill="#E7EDF3">
              {corner.number}
            </text>
          </g>
        );
      })}
    </svg>
  );
}
