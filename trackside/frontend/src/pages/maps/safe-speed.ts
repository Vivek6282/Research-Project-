/**
 * Trackside Maps — safe corner speed hint and input checks for the corner table.
 */

const GRAVITY = 9.81;
export const MAX_LABEL_LENGTH = 40;
export const MAX_MAP_NAME_LENGTH = 150;

/** Fastest speed (km/h) that keeps lateral g at the limit: sqrt(limit x 9.81 x radius). */
export function safeSpeedKmh(limitG: number, radiusM: number): number {
  return Math.sqrt(limitG * GRAVITY * radiusM) * 3.6;
}

/** Read a limit typed by the user; returns null when it is not a finite number. */
export function parseLimit(text: string): number | null {
  const cleaned = text.trim();
  if (cleaned === "") return null;
  const value = Number(cleaned);
  return Number.isFinite(value) ? value : null;
}

/** Return an error message for a limit text, or null when it is inside the allowed range. */
export function limitError(text: string, min: number, max: number): string | null {
  const value = parseLimit(text);
  if (value === null) return "Enter a number";
  if (value < min || value > max) return `Use ${min} to ${max} g`;
  return null;
}

/** Return an error message for a corner name, or null when it is fine. */
export function labelError(text: string): string | null {
  const trimmed = text.trim();
  if (!trimmed) return "Name is required";
  if (trimmed.length > MAX_LABEL_LENGTH) return `Max ${MAX_LABEL_LENGTH} characters`;
  return null;
}
