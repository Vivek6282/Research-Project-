/**
 * Trackside Live Track View — Geometry & Projection Utilities.
 * Normalizes surveyed GPS coordinates into SVG viewBox coordinates and
 * computes the nearest point on the track path for live car positioning.
 */

export interface GpsPoint {
  lat: number;
  lng: number;
}

export interface SvgPoint {
  x: number;
  y: number;
}

export const VIEW_WIDTH = 600;
export const VIEW_HEIGHT = 300;
export const PADDING_RATIO = 0.1;
export const NEAREST_POINT_STEPS = 200;

export interface NormalizedSvgData {
  svgPoints: SvgPoint[];
  minLat: number;
  maxLat: number;
  minLng: number;
  maxLng: number;
}

/**
 * Convert an array of GPS {lat, lng} points to SVG viewBox coordinates.
 * Normalizes against the survey's min/max bounds with padding.
 * Y-axis is inverted (latitude increases upward, SVG Y increases downward).
 */
export function gpsToSvgPoints(gpsPoints: GpsPoint[]): NormalizedSvgData {
  const lats = gpsPoints.map((p) => p.lat);
  const lngs = gpsPoints.map((p) => p.lng);

  const minLat = Math.min(...lats);
  const maxLat = Math.max(...lats);
  const minLng = Math.min(...lngs);
  const maxLng = Math.max(...lngs);

  const latRange = maxLat - minLat || 0.0001;
  const lngRange = maxLng - minLng || 0.0001;

  const padX = VIEW_WIDTH * PADDING_RATIO;
  const padY = VIEW_HEIGHT * PADDING_RATIO;
  const drawWidth = VIEW_WIDTH - 2 * padX;
  const drawHeight = VIEW_HEIGHT - 2 * padY;

  const svgPoints: SvgPoint[] = gpsPoints.map((p) => ({
    x: padX + ((p.lng - minLng) / lngRange) * drawWidth,
    y: padY + (1 - (p.lat - minLat) / latRange) * drawHeight,
  }));

  return { svgPoints, minLat, maxLat, minLng, maxLng };
}

/**
 * Build an SVG path 'd' attribute from an array of SVG points.
 */
export function buildTrackPath(points: SvgPoint[]): string {
  if (points.length === 0) return "";
  return points
    .map((p, i) => `${i === 0 ? "M" : "L"} ${p.x.toFixed(2)} ${p.y.toFixed(2)}`)
    .join(" ");
}

/**
 * Convert a single GPS coordinate to SVG space using normalization bounds.
 */
export function gpsPointToSvg(
  lat: number,
  lng: number,
  minLat: number,
  maxLat: number,
  minLng: number,
  maxLng: number,
): SvgPoint {
  const latRange = maxLat - minLat || 0.0001;
  const lngRange = maxLng - minLng || 0.0001;

  const padX = VIEW_WIDTH * PADDING_RATIO;
  const padY = VIEW_HEIGHT * PADDING_RATIO;
  const drawWidth = VIEW_WIDTH - 2 * padX;
  const drawHeight = VIEW_HEIGHT - 2 * padY;

  return {
    x: padX + ((lng - minLng) / lngRange) * drawWidth,
    y: padY + (1 - (lat - minLat) / latRange) * drawHeight,
  };
}

/**
 * Find the nearest point on an SVG path element to a target (x, y) point
 * using getPointAtLength() sampling.
 */
export function findNearestPointOnPath(
  pathEl: SVGPathElement,
  targetX: number,
  targetY: number,
): SvgPoint {
  const totalLength = pathEl.getTotalLength();
  let bestDist = Infinity;
  let bestPoint: SvgPoint = { x: 0, y: 0 };

  for (let i = 0; i <= NEAREST_POINT_STEPS; i++) {
    const len = (i / NEAREST_POINT_STEPS) * totalLength;
    const pt = pathEl.getPointAtLength(len);
    const dx = pt.x - targetX;
    const dy = pt.y - targetY;
    const dist = dx * dx + dy * dy;
    if (dist < bestDist) {
      bestDist = dist;
      bestPoint = { x: pt.x, y: pt.y };
    }
  }

  return bestPoint;
}
