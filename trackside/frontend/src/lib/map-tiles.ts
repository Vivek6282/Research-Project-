/**
 * Trackside — Where the real-map pictures (tiles) come from.
 *
 * Default: OpenStreetMap street tiles, which need no key (fine for a demo; their usage rules ask for light use).
 * For satellite or heavier use, set these at build time (for example in Render's Environment):
 *   VITE_MAP_TILE_URL       e.g. https://api.maptiler.com/maps/satellite/{z}/{x}/{y}.jpg?key=YOUR_KEY
 *   VITE_MAP_ATTRIBUTION    the provider's required credit text
 *   VITE_MAP_MAX_ZOOM       the highest zoom the provider offers
 * and tell the server which host to allow with MAP_TILE_HOSTS (see backend/README.md).
 * A key in the address is visible in the browser, so restrict it to this site's address at the provider.
 */

export const TILE_URL: string = import.meta.env.VITE_MAP_TILE_URL || "https://tile.openstreetmap.org/{z}/{x}/{y}.png";
export const TILE_ATTRIBUTION: string = import.meta.env.VITE_MAP_ATTRIBUTION || "&copy; OpenStreetMap contributors";
export const TILE_MAX_ZOOM: number = Number(import.meta.env.VITE_MAP_MAX_ZOOM) || 19;

/** How many failed tile loads in a row mean "the map pictures are not reachable". */
export const TILE_FAILURE_LIMIT = 6;
