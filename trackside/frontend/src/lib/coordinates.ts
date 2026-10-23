/**
 * Trackside — Read a typed place such as "10.0123, 76.4567" (latitude, longitude in decimal degrees).
 */

export interface Place {
  lat: number;
  lng: number;
}

/** The place the text names, or null when it is not two real numbers in range (the 0, 0 "no GPS" spot is refused). */
export function parseCoordinates(text: string): Place | null {
  const parts = text.trim().split(/[\s,;]+/);
  if (parts.length !== 2) return null;
  const [lat, lng] = parts.map((part) => (/^[+-]?\d+(\.\d+)?$/.test(part) ? Number(part) : NaN));
  if (!Number.isFinite(lat) || !Number.isFinite(lng)) return null;
  if (lat < -90 || lat > 90 || lng < -180 || lng > 180) return null;
  if (lat === 0 && lng === 0) return null;
  return { lat, lng };
}
