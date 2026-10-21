/**
 * Trackside Maps — the list under/next to the corner editor picture: name, g limit, zone length,
 * the radius at the marker and the safe corner speed at the current limit.
 */

import { X } from "lucide-react";
import { markerRadius } from "../corner-editor-logic";
import { MAX_LABEL_LENGTH, limitError, parseLimit, safeSpeedKmh } from "../safe-speed";
import type { EditorMarker, EditorPayload } from "../types";

interface CornerMarkerTableProps {
  payload: EditorPayload;
  markers: EditorMarker[];
  selectedKey: string | null;
  editable: boolean;
  problems: Record<string, string>;
  onSelect: (key: string) => void;
  onChange: (key: string, patch: Partial<EditorMarker>) => void;
  onRemove: (key: string) => void;
}

const inputClass =
  "w-full min-w-0 bg-[#0A0E13] border border-[#232B35] rounded-[2px] px-2 py-1.5 text-xs font-mono text-[#E7EDF3] focus:border-[#3FA6E0] outline-none";

/** One editable (or read-only) row per marker. */
export function CornerMarkerTable({ payload, markers, selectedKey, editable, problems, onSelect, onChange, onRemove }: CornerMarkerTableProps) {
  if (markers.length === 0) {
    return (
      <p data-testid="editor-no-markers" className="text-xs font-mono text-[#7C8898] p-3 border border-dashed border-[#232B35] rounded">
        {editable ? "No alert corners yet. Click the outline, or click a green + to accept a suggestion." : "This map has no alert corners."}
      </p>
    );
  }
  return (
    <div data-testid="corner-marker-table" className="flex flex-col gap-2">
      {markers.map((m, order) => {
        const length = parseLimit(m.length);
        const limit = parseLimit(m.limit);
        const radius = m.centerIndex !== null && length !== null ? markerRadius(payload.radii, m.centerIndex, length, payload.spacing_m) : null;
        const validLimit = limit !== null && !limitError(m.limit, payload.limit_range_g.min, payload.limit_range_g.max);
        const speed = radius !== null && limit !== null && validLimit ? safeSpeedKmh(limit, radius) : null;
        const straight = radius !== null && radius >= payload.no_curve_radius_m;
        return (
          <div
            key={m.key}
            data-testid={`marker-row-${order + 1}`}
            onClick={() => onSelect(m.key)}
            className="grid grid-cols-[1.5rem_1fr_1fr] sm:grid-cols-[1.5rem_1.6fr_5rem_5rem_6rem_1.5rem] gap-2 items-start p-2 rounded border bg-[#161D26]"
            style={{ borderColor: m.key === selectedKey ? "#3FA6E0" : "#232B35" }}
          >
            <span className="text-xs font-mono font-bold text-[#F2A93B] pt-2">{order + 1}</span>
            {editable ? (
              <input data-testid={`marker-name-${order + 1}`} aria-label={`Corner ${order + 1} name`} className={inputClass}
                value={m.label} maxLength={MAX_LABEL_LENGTH} onChange={(e) => onChange(m.key, { label: e.target.value })} />
            ) : (
              <span className="text-xs font-mono text-[#E7EDF3] pt-2 truncate">{m.label}</span>
            )}
            {editable ? (
              <>
                <input data-testid={`marker-limit-${order + 1}`} aria-label={`Corner ${order + 1} limit in g`} className={inputClass}
                  inputMode="decimal" value={m.limit} onChange={(e) => onChange(m.key, { limit: e.target.value })} />
                <input data-testid={`marker-length-${order + 1}`} aria-label={`Corner ${order + 1} zone length in metres`} className={inputClass}
                  inputMode="decimal" value={m.length} onChange={(e) => onChange(m.key, { length: e.target.value })} />
              </>
            ) : (
              <>
                <span className="text-xs font-mono text-[#E7EDF3] pt-2">{m.limit} g</span>
                <span className="text-xs font-mono text-[#7C8898] pt-2">{m.length} m</span>
              </>
            )}
            <span data-testid={`marker-hint-${order + 1}`} className="text-[11px] font-mono text-[#7C8898] pt-1.5 col-span-3 sm:col-span-1">
              {radius === null ? "—" : straight ? "straight" : `R ${radius.toFixed(0)} m`}
              {speed !== null && !straight && <span className="block text-[#E7EDF3]">{speed.toFixed(0)} km/h safe</span>}
            </span>
            {editable ? (
              <button aria-label={`Remove corner ${order + 1}`} data-testid={`marker-remove-${order + 1}`}
                onClick={(e) => { e.stopPropagation(); onRemove(m.key); }}
                className="text-[#7C8898] hover:text-[#E5473C] cursor-pointer pt-1.5"><X size={14} /></button>
            ) : <span />}
            {problems[m.key] && <p className="col-span-full text-[10px] text-[#E5473C]" data-testid={`marker-problem-${order + 1}`}>{problems[m.key]}</p>}
          </div>
        );
      })}
    </div>
  );
}
