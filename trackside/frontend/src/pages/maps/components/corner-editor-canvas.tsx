/**
 * Trackside Maps — the outline picture of the corner editor. Markers sit on the outline; click the
 * outline to add one, drag a marker along the line, or click a dashed suggestion to accept it.
 */

import { useMemo, useRef, useState, type PointerEvent } from "react";
import { markerRadius, nearestIndex, segmentIndexes } from "../corner-editor-logic";
import { projectOutline } from "../outline-geometry";
import { parseLimit } from "../safe-speed";
import type { CornerSuggestion, EditorMarker, EditorPayload } from "../types";

const WIDTH = 800;
const HEIGHT = 520;
// A click farther than this (picture units) from the outline does not add a marker
const MAX_CLICK_DISTANCE = 45;

interface CornerEditorCanvasProps {
  payload: EditorPayload;
  markers: EditorMarker[];
  selectedKey: string | null;
  editable: boolean;
  onSelect: (key: string) => void;
  onAddAt: (centerIndex: number) => void;
  onAcceptSuggestion: (suggestion: CornerSuggestion) => void;
  onMove: (key: string, centerIndex: number) => void;
}

/** The interactive outline. */
export function CornerEditorCanvas({
  payload, markers, selectedKey, editable, onSelect, onAddAt, onAcceptSuggestion, onMove,
}: CornerEditorCanvasProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const [dragKey, setDragKey] = useState<string | null>(null);
  const didDrag = useRef(false);
  // Project once per outline; drags and typing do not redo the maths
  const points = useMemo(() => projectOutline(payload.outline, WIDTH, HEIGHT, 40).points, [payload.outline]);
  const count = points.length;

  /** Turn a pointer position into picture units. */
  function toPicturePoint(event: PointerEvent | React.MouseEvent) {
    const rect = svgRef.current?.getBoundingClientRect();
    if (!rect || rect.width === 0) return { x: 0, y: 0 };
    return { x: ((event.clientX - rect.left) * WIDTH) / rect.width, y: ((event.clientY - rect.top) * HEIGHT) / rect.height };
  }

  const line = (indexes: number[]) => indexes.map((i, k) => `${k === 0 ? "M" : "L"}${points[i].x.toFixed(1)},${points[i].y.toFixed(1)}`).join(" ");
  const closedPath = points.map((p, i) => `${i === 0 ? "M" : "L"}${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(" ") + " Z";
  // Every outline point that some marker's zone covers
  const covered = useMemo(() => {
    const set = new Set<number>();
    markers.forEach((m) => {
      const length = parseLimit(m.length);
      if (m.centerIndex !== null && length !== null) segmentIndexes(m.centerIndex, length, payload.spacing_m, count).forEach((i) => set.add(i));
    });
    return set;
  }, [markers, payload.spacing_m, count]);
  // A bend is suggested whenever no current marker covers its tightest point (so a removed corner comes back)
  const openSuggestions = payload.suggestions.filter((s) => !covered.has(s.center_index));

  /** Drag: keep the dragged marker on the outline point nearest the pointer. */
  function handleMove(event: PointerEvent<SVGSVGElement>) {
    if (!dragKey) return;
    const p = toPicturePoint(event);
    didDrag.current = true;
    onMove(dragKey, nearestIndex(points, p.x, p.y).index);
  }

  /** Click on the picture: add a marker at the nearest outline point (not after a drag). */
  function handleBackgroundClick(event: React.MouseEvent<SVGSVGElement>) {
    if (!editable || didDrag.current) {
      didDrag.current = false;
      return;
    }
    const p = toPicturePoint(event);
    const near = nearestIndex(points, p.x, p.y);
    if (near.distance <= MAX_CLICK_DISTANCE) onAddAt(near.index);
  }

  return (
    <svg
      ref={svgRef}
      data-testid="corner-editor-canvas"
      viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
      className="w-full h-auto rounded bg-[#0A0E13] border border-[#232B35] touch-none select-none"
      style={{ cursor: editable ? "crosshair" : "default" }}
      role="img"
      aria-label={`Outline of ${payload.track_name} with ${markers.length} corner markers`}
      onPointerMove={handleMove}
      onPointerUp={() => setDragKey(null)}
      onPointerLeave={() => setDragKey(null)}
      onClick={handleBackgroundClick}
    >
      <path d={closedPath} fill="none" stroke="#3A4553" strokeWidth={9} strokeLinejoin="round" />
      <path d={closedPath} fill="none" stroke="#7C8898" strokeWidth={2} strokeLinejoin="round" />
      <circle cx={points[0].x} cy={points[0].y} r={5} fill="#3FA6E0"><title>Start / finish</title></circle>

      {markers.map((m, order) => {
        const length = parseLimit(m.length);
        if (m.centerIndex === null || length === null) return null;
        const centre = points[m.centerIndex];
        const selected = m.key === selectedKey;
        const radius = markerRadius(payload.radii, m.centerIndex, length, payload.spacing_m);
        return (
          <g key={m.key} data-testid={`editor-marker-${order + 1}`}>
            <path d={line(segmentIndexes(m.centerIndex, length, payload.spacing_m, count))} fill="none"
              stroke={selected ? "#3FA6E0" : "#F2A93B"} strokeWidth={7} strokeLinecap="round" opacity={0.85} />
            <g
              style={{ cursor: editable ? "grab" : "pointer" }}
              onClick={(e) => e.stopPropagation()}
              onPointerDown={(e) => {
                e.stopPropagation();
                onSelect(m.key);
                didDrag.current = false;
                if (editable) setDragKey(m.key);
              }}
            >
              <circle cx={centre.x} cy={centre.y} r={13} fill="#12181F" stroke={selected ? "#3FA6E0" : "#F2A93B"} strokeWidth={2.5} />
              <text x={centre.x} y={centre.y + 4} textAnchor="middle" fontSize={12} fontFamily="monospace" fill="#E7EDF3">{order + 1}</text>
              <title>{`${m.label}: radius ${radius.toFixed(0)} m`}</title>
            </g>
          </g>
        );
      })}

      {editable && openSuggestions.map((s) => {
        const at = points[s.center_index];
        return (
          <g
            key={`suggestion-${s.center_index}`}
            data-testid={`editor-suggestion-${s.center_index}`}
            style={{ cursor: "pointer" }}
            onClick={(e) => {
              e.stopPropagation();
              onAcceptSuggestion(s);
            }}
          >
            <circle cx={at.x} cy={at.y} r={12} fill="#0A0E13" stroke="#33D17E" strokeWidth={2} strokeDasharray="4 3" />
            <text x={at.x} y={at.y + 5} textAnchor="middle" fontSize={15} fontFamily="monospace" fill="#33D17E">+</text>
            <title>{`Suggested: tightest point of a bend, radius ${s.radius_m} m. Click to mark it.`}</title>
          </g>
        );
      })}
    </svg>
  );
}
