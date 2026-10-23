/**
 * Trackside Maps — the real map you click on to draw a track.
 * Each click adds a point; points can be dragged; the line through them (closed back to the first point)
 * shows the shape. The smooth, evenly spaced outline is made by the server when you press Preview.
 */

import { useEffect, useRef, useState } from "react";
import L from "leaflet";
import { createBaseMap } from "../../../lib/leaflet-base";
import type { LatLng } from "../types";

export interface MapFocus {
  lat: number;
  lng: number;
  /** A new number each time, so asking for the same place twice still moves the map */
  seq: number;
}

interface DrawMapCanvasProps {
  points: LatLng[];
  onAdd: (point: LatLng) => void;
  onMove: (index: number, point: LatLng) => void;
  focus: MapFocus | null;
}

/** A round dot for a point (green for the first one, which is the start/finish line). */
function pointIcon(first: boolean): L.DivIcon {
  const colour = first ? "#33D17E" : "#3FA6E0";
  return L.divIcon({
    className: "",
    html: `<div style="width:14px;height:14px;border-radius:50%;background:${colour};border:2px solid #fff;box-shadow:0 0 0 1px #0A0E13"></div>`,
    iconSize: [14, 14],
    iconAnchor: [7, 7],
  });
}

/** The drawing map. */
export default function DrawMapCanvas({ points, onAdd, onMove, focus }: DrawMapCanvasProps) {
  const box = useRef<HTMLDivElement>(null);
  const mapRef = useRef<L.Map | null>(null);
  const layer = useRef<L.LayerGroup | null>(null);
  const onAddRef = useRef(onAdd);
  const onMoveRef = useRef(onMove);
  const pointsAtStart = useRef(points);
  const [tilesDown, setTilesDown] = useState(false);
  onAddRef.current = onAdd;
  onMoveRef.current = onMove;

  // Create the map once; show points that were drawn before (when coming back from the preview)
  useEffect(() => {
    if (!box.current) return undefined;
    const base = createBaseMap(box.current, setTilesDown);
    mapRef.current = base.map;
    layer.current = L.layerGroup().addTo(base.map);
    base.map.on("click", (event: L.LeafletMouseEvent) => onAddRef.current({ lat: event.latlng.lat, lng: event.latlng.lng }));
    if (pointsAtStart.current.length >= 2) {
      base.map.fitBounds(L.latLngBounds(pointsAtStart.current.map((p) => [p.lat, p.lng] as [number, number])), { padding: [30, 30] });
    }
    return () => {
      base.stop();
      mapRef.current = null;
      layer.current = null;
    };
  }, []);

  // Redraw the line and the dots whenever the points change
  useEffect(() => {
    const group = layer.current;
    if (!group) return;
    group.clearLayers();
    const latlngs = points.map((p) => [p.lat, p.lng] as [number, number]);
    if (latlngs.length >= 2) L.polyline(latlngs, { color: "#3FA6E0", weight: 4, opacity: 0.95 }).addTo(group);
    if (latlngs.length >= 3) L.polyline([latlngs[latlngs.length - 1], latlngs[0]], { color: "#3FA6E0", weight: 3, opacity: 0.7, dashArray: "6 8" }).addTo(group);
    latlngs.forEach((latlng, index) => {
      const marker = L.marker(latlng, { icon: pointIcon(index === 0), draggable: true, keyboard: false }).addTo(group);
      marker.on("dragend", () => {
        const moved = marker.getLatLng();
        onMoveRef.current(index, { lat: moved.lat, lng: moved.lng });
      });
    });
  }, [points]);

  // Go to a place the person asked for (their location, or typed coordinates)
  useEffect(() => {
    if (focus && mapRef.current) mapRef.current.setView([focus.lat, focus.lng], 17);
  }, [focus]);

  return (
    <div className="relative isolate w-full border border-[#232B35] rounded-[2px] overflow-hidden bg-[#0A0E13]">
      <div ref={box} data-testid="draw-map" style={{ height: "380px", cursor: "crosshair" }} />
      {tilesDown && (
        <p data-testid="draw-map-tiles-down" className="absolute bottom-1 left-1 z-[500] text-[10px] font-mono text-[#F2A93B] bg-[#0A0E13]/85 px-1.5 py-0.5 rounded-[2px]">
          Map pictures cannot be loaded (no internet?). You can still click points, but you need the map to see where they are.
        </p>
      )}
    </div>
  );
}
