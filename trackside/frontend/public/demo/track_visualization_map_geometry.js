/**
 * Trackside Visualizer — Map geometry helpers (pure functions, no page access).
 * Used by track_visualization_map.js and unit tested with plain Node.js.
 */

const MAP_VIEW_WIDTH = 700;
const MAP_VIEW_HEIGHT = 450;
const MAP_PADDING = 50;
const MAP_MAX_POINTS = 2000;

/**
 * Checks that a run_start outline is a usable list of [x, y] numbers.
 * Input: outline (any). Output: boolean.
 */
function isValidOutline(outline) {
  if (!Array.isArray(outline) || outline.length < 3 || outline.length > MAP_MAX_POINTS) return false;
  return outline.every(
    (p) => Array.isArray(p) && p.length === 2 && Number.isFinite(p[0]) && Number.isFinite(p[1]),
  );
}

/**
 * Scales outline metres into the SVG view, north up, keeping the true shape.
 * Input: outline (list of [x, y]). Output: list of {x, y} in view units.
 */
function projectOutlineToView(outline) {
  const xs = outline.map((p) => p[0]);
  const ys = outline.map((p) => p[1]);
  const minX = Math.min(...xs);
  const maxY = Math.max(...ys);
  const spanX = Math.max(Math.max(...xs) - minX, 1e-6);
  const spanY = Math.max(maxY - Math.min(...ys), 1e-6);
  const scale = Math.min((MAP_VIEW_WIDTH - 2 * MAP_PADDING) / spanX, (MAP_VIEW_HEIGHT - 2 * MAP_PADDING) / spanY);
  const offsetX = (MAP_VIEW_WIDTH - spanX * scale) / 2;
  const offsetY = (MAP_VIEW_HEIGHT - spanY * scale) / 2;
  return outline.map((p) => ({ x: offsetX + (p[0] - minX) * scale, y: offsetY + (maxY - p[1]) * scale }));
}

/**
 * Builds a closed SVG path string through the projected points.
 * Input: points (list of {x, y}). Output: string like "M 1 2 L 3 4 Z".
 */
function buildClosedPath(points) {
  return points.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(" ") + " Z";
}
