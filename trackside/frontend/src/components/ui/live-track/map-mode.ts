/**
 * Trackside Live Track View — "Map" or "Plain" view of a track with real coordinates.
 * The choice is remembered in this browser only (a convenience, never needed for anything to work).
 */

export type MapMode = "map" | "plain";

const KEY = "trackside_live_map_mode";

/** The remembered view; the real map unless the person chose Plain. */
export function readMapMode(): MapMode {
  try {
    return window.localStorage.getItem(KEY) === "plain" ? "plain" : "map";
  } catch {
    return "map";
  }
}

/** Remember the chosen view (a browser that refuses storage just forgets it). */
export function saveMapMode(mode: MapMode): void {
  try {
    window.localStorage.setItem(KEY, mode);
  } catch {
    /* nothing to remember with */
  }
}
