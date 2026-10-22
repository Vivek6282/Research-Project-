/**
 * Trackside Visualizer — Chosen-map drawing (SIM-4).
 * A run_start message from a custom-track run carries the outline (at most 2,000
 * [x, y] points in metres) and corner labels. track_visualization_map_geometry.js holds the maths; this file draws them in place of the
 * default track and puts the default back when a run has no outline.
 */

window.TracksideMap = (function () {
  const bed = document.getElementById("track-bed");
  const line = document.getElementById("track-path");
  const labels = document.getElementById("corner-labels");
  const pillBar = document.getElementById("corner-chips-bar");
  const startLine = document.getElementById("start-finish-line");
  const startText = document.getElementById("start-finish-label");
  const defaults = {
    bed: bed ? bed.getAttribute("d") : "",
    line: line ? line.getAttribute("d") : "",
    // Keep the original pill elements: the stream script holds references to them
    pills: pillBar ? Array.from(pillBar.children) : [],
  };
  let customPills = null;

  /** Adds one SVG text label (safe: textContent only). */
  function addLabel(text, point) {
    const node = document.createElementNS("http://www.w3.org/2000/svg", "text");
    // Put the label on the side with room, so it is never cut off at the picture's edge
    const onRight = point.x > MAP_VIEW_WIDTH / 2;
    node.setAttribute("x", point.x + (onRight ? 12 : -12));
    node.setAttribute("y", point.y - 10);
    node.setAttribute("text-anchor", onRight ? "start" : "end");
    node.setAttribute("fill", "#F2A93B");
    node.setAttribute("font-family", "'JetBrains Mono', monospace");
    node.setAttribute("font-size", "11");
    node.setAttribute("font-weight", "700");
    node.textContent = text;
    labels.appendChild(node);
  }

  /** Replaces the zone pill bar with one pill per corner plus a straight pill. */
  function showCornerPills(corners) {
    const nodes = [];
    customPills = {};
    corners.concat([{ label: "Straight" }]).forEach((corner) => {
      const pill = document.createElement("span");
      pill.className = "zone-pill";
      pill.textContent = String(corner.label).toUpperCase();
      nodes.push(pill);
      customPills[String(corner.label).toLowerCase()] = pill;
    });
    pillBar.replaceChildren(...nodes);
  }

  /** Draws the run's own outline, start line and corner labels. */
  function drawCustom(event) {
    const points = projectOutlineToView(event.outline);
    const path = buildClosedPath(points);
    bed.setAttribute("d", path);
    line.setAttribute("d", path);
    labels.textContent = "";
    const corners = Array.isArray(event.corners) ? event.corners.slice(0, 200) : [];
    corners.forEach((corner) => {
      const at = points[corner.label_index];
      if (at && typeof corner.label === "string") addLabel(corner.label.slice(0, 40), at);
    });
    showCornerPills(corners.filter((c) => typeof c.label === "string"));
    startLine.setAttribute("x1", points[0].x - 14);
    startLine.setAttribute("x2", points[0].x + 14);
    startLine.setAttribute("y1", points[0].y);
    startLine.setAttribute("y2", points[0].y);
    startText.setAttribute("x", points[0].x - 28);
    startText.setAttribute("y", points[0].y + 16);
    window.dispatchEvent(new CustomEvent("trackside-map-changed"));
  }

  /** Puts the default track, start line and pills back. */
  function drawDefault() {
    bed.setAttribute("d", defaults.bed);
    line.setAttribute("d", defaults.line);
    labels.textContent = "";
    pillBar.replaceChildren(...defaults.pills);
    customPills = null;
    startLine.setAttribute("x1", 105);
    startLine.setAttribute("y1", 315);
    startLine.setAttribute("x2", 135);
    startLine.setAttribute("y2", 345);
    startText.setAttribute("x", 90);
    startText.setAttribute("y", 360);
    window.dispatchEvent(new CustomEvent("trackside-map-changed"));
  }

  /** Draw the map named in a run_start event, or the default track when it has none. */
  function applyRunStart(event) {
    if (!bed || !line || !labels || !pillBar || !startLine || !startText) return;
    if (event && isValidOutline(event.outline)) drawCustom(event);
    else drawDefault();
  }

  /** True while a custom map is drawn. */
  function isCustom() {
    return customPills !== null;
  }

  /** Light up the pill of the zone the kart is in (custom maps only). */
  function highlightZone(zoneName) {
    if (!customPills) return;
    Object.values(customPills).forEach((pill) => pill.classList.remove("active"));
    const pill = customPills[String(zoneName || "straight").toLowerCase()] || customPills.straight;
    if (pill) pill.classList.add("active");
  }

  return { applyRunStart, isCustom, highlightZone };
})();
