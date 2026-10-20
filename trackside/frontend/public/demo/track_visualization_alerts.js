/**
 * Trackside Visualizer — Pure Alert Decision Engine.
 * Mirrors backend alerting rules to prevent duplicate alerts per corner crossing.
 */

/**
 * Checks whether a zone represents an unalerted straight track segment.
 * Input: zone (string, null, or undefined).
 * Output: boolean (true if straight, false if corner).
 */
function isStraight(zone) {
  if (!zone) return true;
  const normalized = String(zone).trim().toLowerCase();
  return normalized === "straight" || normalized.startsWith("straight");
}

/**
 * Evaluates whether an incoming telemetry reading should trigger an INTERVENE alert.
 * Mirrors backend alerting rules:
 * - Trigger only on INTERVENE stage in corner zones.
 * - Trigger when transitioning into INTERVENE (previous reading was not INTERVENE, or previous was straight).
 * - Trigger when entering a new corner zone or new lap while still in INTERVENE.
 * - Suppress duplicate readings within the same corner crossing.
 * - Straights reset the state and never produce alerts.
 *
 * Input: previous (reading object or null), current (reading object or null).
 * Output: boolean (true to record alert, false to skip).
 */
function shouldRecordAlert(previous, current) {
  if (!current) return false;
  const currentStage = (current.stage || "").toUpperCase();
  if (currentStage !== "INTERVENE") return false;
  if (isStraight(current.zone)) return false;

  if (!previous) return true;

  const prevStage = (previous.stage || "").toUpperCase();
  if (prevStage !== "INTERVENE" || isStraight(previous.zone)) {
    return true;
  }

  // Both previous and current are INTERVENE in corner zones:
  // Trigger if entering a new corner zone or crossing into a new lap
  if (previous.zone !== current.zone) return true;
  if (previous.lap !== current.lap) return true;

  return false;
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = { shouldRecordAlert, isStraight };
}
if (typeof window !== "undefined") {
  window.shouldRecordAlert = shouldRecordAlert;
  window.isStraight = isStraight;
}
if (typeof globalThis !== "undefined") {
  globalThis.shouldRecordAlert = shouldRecordAlert;
  globalThis.isStraight = isStraight;
}
