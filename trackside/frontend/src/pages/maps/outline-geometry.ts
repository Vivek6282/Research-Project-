/**
 * Trackside Maps — turn lat/lng outline points into SVG coordinates.
 */

import type { LatLng } from "./types";

export interface Projected {
  points: { x: number; y: number }[];
  width: number;
  height: number;
}

/**
 * Project points to a flat picture that fits inside width x height (with padding).
 * North is up; longitude is shrunk by cos(latitude) so shapes are not stretched.
 */
export function projectOutline(points: LatLng[], width: number, height: number, pad = 16): Projected {
  if (points.length === 0) return { points: [], width, height };
  const meanLat = points.reduce((sum, p) => sum + p.lat, 0) / points.length;
  const squash = Math.cos((meanLat * Math.PI) / 180);
  const flat = points.map((p) => ({ x: p.lng * squash, y: -p.lat }));
  const xs = flat.map((p) => p.x);
  const ys = flat.map((p) => p.y);
  const minX = Math.min(...xs);
  const minY = Math.min(...ys);
  const spanX = Math.max(Math.max(...xs) - minX, 1e-9);
  const spanY = Math.max(Math.max(...ys) - minY, 1e-9);
  const scale = Math.min((width - 2 * pad) / spanX, (height - 2 * pad) / spanY);
  const offsetX = (width - spanX * scale) / 2;
  const offsetY = (height - spanY * scale) / 2;
  return {
    points: flat.map((p) => ({ x: offsetX + (p.x - minX) * scale, y: offsetY + (p.y - minY) * scale })),
    width,
    height,
  };
}

/** Indexes from start to end on a closed loop of `count` points (wraps past the end). */
export function loopRange(start: number, end: number, count: number): number[] {
  const indexes: number[] = [];
  let i = start;
  for (let guard = 0; guard <= count; guard += 1) {
    indexes.push(i);
    if (i === end) break;
    i = (i + 1) % count;
  }
  return indexes;
}
