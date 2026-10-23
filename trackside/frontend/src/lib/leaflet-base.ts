/**
 * Trackside — A Leaflet map with the Trackside picture source, shared by the live map and the drawing map.
 * Leaflet's own style file is bundled with the app (nothing is loaded from another site except the map pictures).
 */

import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { TILE_ATTRIBUTION, TILE_FAILURE_LIMIT, TILE_MAX_ZOOM, TILE_URL } from "./map-tiles";

export interface BaseMap {
  map: L.Map;
  /** Take the map apart (call when the screen closes). */
  stop: () => void;
}

/**
 * Create a map in a container. onTilesUnavailable(true) is called when several map pictures in a row cannot be
 * loaded (no internet, or the provider refuses), and onTilesUnavailable(false) when one loads again.
 */
export function createBaseMap(
  container: HTMLElement,
  onTilesUnavailable: (unavailable: boolean) => void,
  view: { center: [number, number]; zoom: number } = { center: [20, 0], zoom: 2 },
): BaseMap {
  const map = L.map(container, { center: view.center, zoom: view.zoom, zoomControl: true, attributionControl: true });
  const tiles = L.tileLayer(TILE_URL, { attribution: TILE_ATTRIBUTION, maxZoom: TILE_MAX_ZOOM, crossOrigin: false });
  let failures = 0;
  tiles.on("tileerror", () => {
    failures += 1;
    if (failures === TILE_FAILURE_LIMIT) onTilesUnavailable(true);
  });
  tiles.on("tileload", () => {
    if (failures >= TILE_FAILURE_LIMIT) onTilesUnavailable(false);
    failures = 0;
  });
  tiles.addTo(map);
  return { map, stop: () => map.remove() };
}
