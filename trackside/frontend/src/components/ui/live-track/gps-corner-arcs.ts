/**
 * Trackside Live Track View — corners on a real map.
 * Turns each corner's stored start and end positions into the piece of the track line between them, as plain
 * latitude/longitude points, so a real map can highlight it. Positions come from the corner's own gps_range.
 */

import { GpsPoint } from "./geo-utils";
import { TrackCorner } from "./corner-segments";

export interface CornerArc {
  zoneId: string;
  label: string;
  /** [lat, lng] pairs along the track from the corner's start to its end */
  points: [number, number][];
}

/** Index of the track point nearest to a position (longitude is scaled by latitude so distances are true). */
export function nearestPointIndex(line: GpsPoint[], target: GpsPoint): number {
  const scale = Math.cos((target.lat * Math.PI) / 180);
  let best = 0;
  let bestGap = Infinity;
  line.forEach((p, i) => {
    const gap = (p.lat - target.lat) ** 2 + ((p.lng - target.lng) * scale) ** 2;
    if (gap < bestGap) {
      bestGap = gap;
      best = i;
    }
  });
  return best;
}

/** The track points from one index to another, going the shorter way round the closed loop. */
export function arcBetween(line: GpsPoint[], from: number, to: number): GpsPoint[] {
  const count = line.length;
  const forward = (to - from + count) % count;
  const [first, steps] = forward <= count / 2 ? [from, forward] : [to, count - forward];
  return Array.from({ length: steps + 1 }, (_, k) => line[(first + k) % count]);
}

/** One highlighted arc per corner (none when the line is too short to draw). */
export function buildCornerArcs(line: GpsPoint[], corners: TrackCorner[]): CornerArc[] {
  if (line.length < 2) return [];
  return corners.map((corner) => {
    const arc = arcBetween(line, nearestPointIndex(line, corner.start), nearestPointIndex(line, corner.end));
    return { zoneId: corner.zone_id, label: corner.label, points: arc.map((p) => [p.lat, p.lng] as [number, number]) };
  });
}
