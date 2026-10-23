/**
 * Trackside Live Track View — the track on a real map.
 * Draws the track line, its corners and the driver's live position at their real latitude and longitude.
 * The Demo Circuit has no real coordinates, so it keeps the plain drawing (TrackCanvas) instead.
 */

import { useEffect, useRef, useState } from "react";
import L from "leaflet";
import { createBaseMap } from "../../../lib/leaflet-base";
import { GpsPoint } from "./geo-utils";
import { TrackCorner } from "./corner-segments";
import { buildCornerArcs } from "./gps-corner-arcs";

export interface GpsMapCanvasProps {
  line: GpsPoint[];
  corners: TrackCorner[];
  activeZoneId?: string | null;
  gpsLat: number | null;
  gpsLng: number | null;
  stageColor: string;
}

const LINE_COLOR = "#3FA6E0";
const CORNER_COLOR = "#F2A93B";

/** A small square flag at the start/finish line. */
function startFinishIcon(): L.DivIcon {
  return L.divIcon({
    className: "",
    html: '<div style="padding:1px 4px;font:700 10px monospace;color:#0A0E13;background:#E7EDF3;border-radius:2px;white-space:nowrap">S/F</div>',
    iconSize: [28, 14],
    iconAnchor: [14, 7],
  });
}

/** Colour and thicken the active corner's line; every other corner goes back to the normal look. */
function highlightCorner(lines: Map<string, L.Polyline>, activeZoneId: string | null, stageColor: string): void {
  lines.forEach((corner, zoneId) => {
    const active = zoneId === activeZoneId;
    corner.setStyle({ color: active ? stageColor : CORNER_COLOR, weight: active ? 9 : 6 });
  });
}

/** The real-map canvas. */
export default function GpsMapCanvas({ line, corners, activeZoneId = null, gpsLat, gpsLng, stageColor }: GpsMapCanvasProps) {
  const box = useRef<HTMLDivElement>(null);
  const mapRef = useRef<L.Map | null>(null);
  const trackLayer = useRef<L.LayerGroup | null>(null);
  const dot = useRef<L.CircleMarker | null>(null);
  const cornerLines = useRef<Map<string, L.Polyline>>(new Map());
  const activeZone = useRef<string | null>(activeZoneId);
  const stage = useRef<string>(stageColor);
  const [tilesDown, setTilesDown] = useState(false);

  // Create the map once, and take it apart when the view goes away
  useEffect(() => {
    if (!box.current) return undefined;
    const base = createBaseMap(box.current, setTilesDown);
    mapRef.current = base.map;
    trackLayer.current = L.layerGroup().addTo(base.map);
    const showZoom = () => { if (box.current) box.current.dataset.zoom = String(base.map.getZoom()); };
    base.map.on("zoomend", showZoom);   // the zoom level is shown as a data attribute, handy for checks
    return () => {
      base.stop();
      mapRef.current = null;
      trackLayer.current = null;
      dot.current = null;
    };
  }, []);

  // Draw the track and its corners, and fit the view to the track. Only when the track itself changes: a coach's
  // own zoom and pan are never reset by the live readings.
  useEffect(() => {
    const map = mapRef.current;
    const layer = trackLayer.current;
    cornerLines.current = new Map();
    if (!map || !layer || line.length < 2) return;
    layer.clearLayers();
    const points = line.map((p) => [p.lat, p.lng] as [number, number]);
    L.polyline([...points, points[0]], { color: "#0A0E13", weight: 8, opacity: 0.55 }).addTo(layer);   // dark edge, readable on any map
    L.polyline([...points, points[0]], { color: LINE_COLOR, weight: 4, opacity: 0.95 }).addTo(layer);
    buildCornerArcs(line, corners).forEach((arc) => {
      const corner = L.polyline(arc.points, { color: CORNER_COLOR, weight: 6, opacity: 0.95 })
        .bindTooltip(arc.label, { permanent: true, direction: "top", offset: [0, -4] })
        .addTo(layer);
      cornerLines.current.set(arc.zoneId, corner);
    });
    L.marker(points[0], { icon: startFinishIcon(), interactive: false, keyboard: false }).addTo(layer);
    map.fitBounds(L.latLngBounds(points), { padding: [28, 28] });
    highlightCorner(cornerLines.current, activeZone.current, stage.current);
  }, [line, corners]);

  // Highlight the corner the kart is in, in the stage colour (a style change only: nothing is rebuilt)
  useEffect(() => {
    activeZone.current = activeZoneId;
    stage.current = stageColor;
    highlightCorner(cornerLines.current, activeZoneId, stageColor);
  }, [activeZoneId, stageColor]);

  // Move the live dot to the driver's real position
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    if (gpsLat == null || gpsLng == null) {
      dot.current?.remove();
      dot.current = null;
      if (box.current) delete box.current.dataset.dotLat;
      return;
    }
    if (!dot.current) {
      dot.current = L.circleMarker([gpsLat, gpsLng], { radius: 8, color: "#FFFFFF", weight: 2, fillColor: stageColor, fillOpacity: 1 }).addTo(map);
    } else {
      dot.current.setLatLng([gpsLat, gpsLng]);
      dot.current.setStyle({ fillColor: stageColor });
    }
    if (box.current) {
      box.current.dataset.dotLat = String(gpsLat);
      box.current.dataset.dotLng = String(gpsLng);
    }
  }, [gpsLat, gpsLng, stageColor]);

  return (
    <div className="relative isolate w-full border border-[#232B35] rounded-[2px] overflow-hidden bg-[#0A0E13]">
      <div ref={box} data-testid="gps-map" style={{ height: "300px" }} />
      {tilesDown && (
        <p data-testid="gps-map-tiles-down" className="absolute bottom-1 left-1 z-[500] text-[10px] font-mono text-[#F2A93B] bg-[#0A0E13]/85 px-1.5 py-0.5 rounded-[2px]">
          Map pictures cannot be loaded (no internet?). The track and the dot still show; use Plain view if you prefer.
        </p>
      )}
    </div>
  );
}
