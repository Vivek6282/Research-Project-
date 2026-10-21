/**
 * Trackside Maps — pure helpers for the corner marker editor: zone segments, radius at a marker,
 * snapping a click to the outline, and the same checks the server makes before saving.
 */

import { labelError, limitError, parseLimit } from "./safe-speed";
import type { EditorMarker, EditorPayload, ServerMarker } from "./types";

/** Indexes of a zone segment of the given length centred on a point (wraps round the loop). */
export function segmentIndexes(center: number, lengthM: number, spacingM: number, count: number): number[] {
  const half = Math.max(1, Math.round(lengthM / 2 / spacingM));
  const indexes: number[] = [];
  for (let k = -half; k <= half; k += 1) indexes.push((((center + k) % count) + count) % count);
  return indexes;
}

/** Tightest radius (m) inside a marker's zone segment, from the server's per-point radii. */
export function markerRadius(radii: number[], center: number, lengthM: number, spacingM: number): number {
  return Math.min(...segmentIndexes(center, lengthM, spacingM, radii.length).map((i) => radii[i]));
}

/** Index of the projected outline point nearest to (x, y), and how far away it is. */
export function nearestIndex(points: { x: number; y: number }[], x: number, y: number): { index: number; distance: number } {
  let best = 0;
  let bestDistance = Infinity;
  points.forEach((p, i) => {
    const d = Math.hypot(p.x - x, p.y - y);
    if (d < bestDistance) {
      best = i;
      bestDistance = d;
    }
  });
  return { index: best, distance: bestDistance };
}

/** Turn a server marker into an editable one. */
export function toEditorMarker(marker: ServerMarker, serial: number): EditorMarker {
  return {
    key: marker.id ?? `new-${serial}`,
    id: marker.id,
    label: marker.label,
    limit: String(marker.threshold_g),
    length: String(marker.length_m),
    centerIndex: marker.center_index,
  };
}

/** Turn editable markers back into what the server expects. */
export function toServerMarkers(markers: EditorMarker[]): Record<string, unknown>[] {
  return markers.map((m) => ({
    id: m.id,
    label: m.label.trim(),
    threshold_g: Number(m.limit),
    center_index: m.centerIndex,
    length_m: Number(m.length),
  }));
}

/** The first free "Turn N" name. */
export function nextTurnName(markers: EditorMarker[]): string {
  const used = new Set(markers.map((m) => m.label.trim().toLowerCase()));
  let n = markers.length + 1;
  while (used.has(`turn ${n}`)) n += 1;
  return `Turn ${n}`;
}

export interface MarkerChecks {
  /** Problem text per marker key (missing key = fine) */
  byKey: Record<string, string>;
  /** The first problem overall, or null when the markers can be saved */
  first: string | null;
}

/** The same rules the server applies: name, limit, zone length, placement, duplicates and overlaps. */
export function checkMarkers(markers: EditorMarker[], payload: EditorPayload): MarkerChecks {
  const byKey: Record<string, string> = {};
  const owner = new Map<number, string>();
  const seen = new Set<string>();
  const { min, max } = payload.limit_range_g;
  const lengthRange = payload.zone_length_m;
  for (const m of markers) {
    const name = labelError(m.label);
    const lower = m.label.trim().toLowerCase();
    const length = parseLimit(m.length);
    if (name) byKey[m.key] = name;
    else if (lower.startsWith("straight")) byKey[m.key] = "A name cannot start with 'Straight'";
    else if (seen.has(lower)) byKey[m.key] = "Another corner has this name";
    else if (limitError(m.limit, min, max)) byKey[m.key] = `Limit: ${limitError(m.limit, min, max)}`;
    else if (length === null || length < lengthRange.min || length > lengthRange.max)
      byKey[m.key] = `Zone length: use ${lengthRange.min} to ${lengthRange.max} m`;
    else if (m.centerIndex === null) byKey[m.key] = "Not on the outline: click the outline to place it";
    else {
      for (const i of segmentIndexes(m.centerIndex, length, payload.spacing_m, payload.outline.length)) {
        const other = owner.get(i);
        if (other && other !== m.key) {
          byKey[m.key] = "Overlaps another corner: shorten the zone or move it";
          break;
        }
        owner.set(i, m.key);
      }
    }
    seen.add(lower);
  }
  const firstKey = markers.find((m) => byKey[m.key])?.key;
  return { byKey, first: firstKey ? byKey[firstKey] : null };
}
