/**
 * Trackside Maps — small SVG picture of a map's outline for map cards.
 */

import { useMemo } from "react";
import { projectOutline } from "../outline-geometry";
import type { LatLng } from "../types";

const WIDTH = 180;
const HEIGHT = 110;
// A thumbnail needs far fewer points than the stored outline
const MAX_DRAWN_POINTS = 200;

interface OutlineThumbnailProps {
  points: LatLng[] | null | undefined;
  label: string;
}

/** Draws the outline as one closed line, or a short note when the map has no outline yet. */
export function OutlineThumbnail({ points, label }: OutlineThumbnailProps) {
  // Build the drawn line once per outline
  const path = useMemo(() => {
    if (!points || points.length < 3) return null;
    const stride = Math.max(1, Math.ceil(points.length / MAX_DRAWN_POINTS));
    const thinned = points.filter((_, i) => i % stride === 0);
    const projected = projectOutline(thinned, WIDTH, HEIGHT, 8).points;
    return projected.map((p, i) => `${i === 0 ? "M" : "L"}${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(" ") + " Z";
  }, [points]);

  if (!path) {
    return (
      <div
        data-testid="outline-thumbnail-empty"
        className="w-full h-[110px] flex items-center justify-center rounded bg-[#0A0E13] border border-dashed border-[#232B35] text-[10px] font-mono text-[#7C8898]"
      >
        No outline yet
      </div>
    );
  }
  return (
    <svg
      data-testid="outline-thumbnail"
      viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
      className="w-full h-[110px] rounded bg-[#0A0E13] border border-[#232B35]"
      role="img"
      aria-label={`Outline of ${label}`}
    >
      <path d={path} fill="none" stroke="#3FA6E0" strokeWidth={2.5} strokeLinejoin="round" />
    </svg>
  );
}
