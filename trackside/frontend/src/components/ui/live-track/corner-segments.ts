/**
 * Trackside Live Track View — corner segments.
 * Turns each corner's stored start/end positions into a short piece of the drawn
 * outline. Nothing is invented: the positions come from the corner's gps_range.
 */

import { GpsPoint, NormalizedSvgData, SvgPoint, gpsPointToSvg } from "./geo-utils";

export interface TrackCorner {
  zone_id: string;
  label: string;
  start: GpsPoint;
  end: GpsPoint;
  center?: GpsPoint;
}

export interface CornerSegment {
  zoneId: string;
  label: string;
  path: string;
  labelAt: SvgPoint;
}

/** Index of the outline point closest to a position given in screen coordinates. */
function nearestIndex(points: SvgPoint[], target: SvgPoint): number {
  let best = 0;
  let bestGap = Infinity;
  points.forEach((p, i) => {
    const gap = (p.x - target.x) ** 2 + (p.y - target.y) ** 2;
    if (gap < bestGap) {
      bestGap = gap;
      best = i;
    }
  });
  return best;
}

/** Outline points from one index to another, going the shorter way round the loop. */
function arcBetween(points: SvgPoint[], from: number, to: number): SvgPoint[] {
  const count = points.length;
  const forward = (to - from + count) % count;
  const [first, steps] = forward <= count / 2 ? [from, forward] : [to, count - forward];
  return Array.from({ length: steps + 1 }, (_, k) => points[(first + k) % count]);
}

/** Build the highlighted piece of outline and the label spot for every corner. */
export function buildCornerSegments(corners: TrackCorner[], svg: NormalizedSvgData): CornerSegment[] {
  const { svgPoints, minLat, maxLat, minLng, maxLng } = svg;
  if (svgPoints.length < 2) return [];
  const place = (p: GpsPoint) => gpsPointToSvg(p.lat, p.lng, minLat, maxLat, minLng, maxLng);
  return corners.map((corner) => {
    const arc = arcBetween(svgPoints, nearestIndex(svgPoints, place(corner.start)), nearestIndex(svgPoints, place(corner.end)));
    const middle = arc[Math.floor(arc.length / 2)];
    return {
      zoneId: corner.zone_id,
      label: corner.label,
      path: arc.map((p, i) => `${i === 0 ? "M" : "L"}${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(" "),
      labelAt: { x: middle.x + 7, y: middle.y - 7 },
    };
  });
}
