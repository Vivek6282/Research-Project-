/**
 * Trackside Maps — the map browser: Active/Archived filter, map cards, Add track wizard and
 * delete confirmations. One component, used by the Coach "Maps & Demo" tab and the /maps page,
 * so both always behave the same.
 */

import { useState, type ReactNode } from "react";
import { MapPinned, Plus } from "lucide-react";
import { ConfirmDialog } from "../../../components/ui/confirm-dialog";
import { api } from "../../../lib/api";
import { useMaps, type MapView } from "../hooks/use-maps";
import type { MapTrack } from "../types";
import { AddMapWizard } from "./add-map-wizard";
import { DrawMapWizard } from "./draw-map-wizard";
import { CornerEditorDialog } from "./corner-editor-dialog";
import { MapCardGrid } from "./map-card-grid";
import { MapNameDialog } from "./map-name-dialog";

const VIEW_TABS: { id: MapView; label: string }[] = [
  { id: "active", label: "Active" },
  { id: "archived", label: "Archived" },
];

export interface MapsBrowserProps {
  /** Coach and Admin: add, delete and restore maps */
  canManage: boolean;
  /** Called with a map when its Play demo button is pressed; leave out to hide the button */
  onPlay?: (map: MapTrack) => void;
  /** Why Play is switched off right now, or null */
  playDisabledReason?: string | null;
  /** Coach and Admin: show Edit corners (the built-in and archived maps open view-only) */
  canEditCorners?: boolean;
  /** Admin only: rename a map and change its kart class */
  canEditDetails?: boolean;
  /** Bump this number to make the list reload (for example after the corner editor saves) */
  reloadKey?: number;
  /** Extra content shown above the cards (for example the demo status panel) */
  children?: ReactNode;
}

/** The browser itself. */
export function MapsBrowser({ canManage, onPlay, playDisabledReason, canEditCorners = false, canEditDetails = false, reloadKey = 0, children }: MapsBrowserProps) {
  const maps = useMaps(canManage, reloadKey);
  const [editing, setEditing] = useState<MapTrack | null>(null);
  const [showWizard, setShowWizard] = useState(false);
  const [showDrawing, setShowDrawing] = useState(false);
  const [toArchive, setToArchive] = useState<MapTrack | null>(null);
  const [toDeleteForever, setToDeleteForever] = useState<MapTrack | null>(null);
  const [detailsOf, setDetailsOf] = useState<MapTrack | null>(null);
  const [copyOf, setCopyOf] = useState<MapTrack | null>(null);

  return (
    <div className="flex flex-col gap-3" data-testid="maps-browser">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex gap-2" role="tablist">
          {VIEW_TABS.map((tab) => (
            <button
              key={tab.id}
              role="tab"
              aria-selected={maps.view === tab.id}
              data-testid={`maps-tab-${tab.id}`}
              onClick={() => maps.setView(tab.id)}
              className="text-[11px] font-mono px-3 py-1.5 rounded-[2px] border cursor-pointer"
              style={{
                borderColor: maps.view === tab.id ? "#3FA6E0" : "#232B35",
                color: maps.view === tab.id ? "#3FA6E0" : "#7C8898",
              }}
            >
              {tab.label}
            </button>
          ))}
        </div>
        {canManage && (
          <div className="flex flex-wrap gap-2">
            <button
              data-testid="draw-map-btn"
              onClick={() => setShowDrawing(true)}
              className="inline-flex items-center gap-1.5 text-xs font-mono font-bold px-3 py-2 min-h-[36px] rounded-[2px] border border-[#3FA6E0] text-[#3FA6E0] cursor-pointer"
            >
              <MapPinned size={14} /> Draw on map
            </button>
            <button
              data-testid="add-map-btn"
              onClick={() => setShowWizard(true)}
              className="inline-flex items-center gap-1.5 text-xs font-mono font-bold px-3 py-2 min-h-[36px] rounded-[2px] bg-[#3FA6E0] text-[#06121B] cursor-pointer"
            >
              <Plus size={14} /> Add track
            </button>
          </div>
        )}
      </div>

      {children}
      {maps.notice && <p data-testid="maps-notice" className="text-xs text-[#3FA6E0]">{maps.notice}</p>}
      {maps.error && <p data-testid="maps-error" role="alert" className="text-xs text-[#E5473C]">{maps.error}</p>}
      {maps.isLoading ? (
        <p className="text-xs font-mono text-[#7C8898] animate-pulse">Loading maps…</p>
      ) : (
        <MapCardGrid
          maps={maps.maps}
          canArchive={canManage}
          onPlay={onPlay}
          playDisabledReason={playDisabledReason}
          onEditCorners={canEditCorners ? setEditing : undefined}
          onArchive={setToArchive}
          onRestore={maps.restoreMap}
          onDeleteForever={setToDeleteForever}
          onEditDetails={canEditDetails ? setDetailsOf : undefined}
          onDuplicate={canManage ? setCopyOf : undefined}
        />
      )}

      {showWizard && (
        <AddMapWizard
          onClose={() => setShowWizard(false)}
          onSaved={() => {
            setShowWizard(false);
            maps.reload();
          }}
        />
      )}
      {showDrawing && (
        <DrawMapWizard
          onClose={() => setShowDrawing(false)}
          onSaved={() => {
            setShowDrawing(false);
            maps.reload();
          }}
        />
      )}
      {editing && (
        <CornerEditorDialog
          map={editing}
          onClose={() => setEditing(null)}
          onChanged={(message) => {
            maps.reload();
            if (message) maps.announce(message);
          }}
        />
      )}
      {detailsOf && (
        <MapNameDialog
          title="Edit map details" initialName={detailsOf.name} initialKartClass={detailsOf.kart_class ?? "sprint"} submitText="Save"
          onClose={() => setDetailsOf(null)}
          onSubmit={async ({ name, kartClass }) => {
            await api.patch(`/api/tracks/${detailsOf.id}/`, { name, kart_class: kartClass });
            setDetailsOf(null);
            maps.announce(`"${name}" was updated.`);
            await maps.reload();
          }}
        />
      )}
      {copyOf && (
        <MapNameDialog
          title={`Duplicate ${copyOf.name}`} initialName={`${copyOf.name} copy`} submitText="Duplicate"
          onClose={() => setCopyOf(null)}
          onSubmit={async ({ name }) => {
            const res = await api.post<{ clamped?: { label: string; from_g: number; to_g: number }[] }>(`/api/tracks/${copyOf.id}/duplicate/`, { name });
            const note = (res.clamped ?? []).map((c) => `${c.label} limit ${c.from_g} g became ${c.to_g} g (the allowed maximum)`).join("; ");
            setCopyOf(null);
            maps.announce(`Created "${name}".${note ? ` ${note}.` : ""}`);
            await maps.reload();
          }}
        />
      )}
      <ConfirmDialog
        isOpen={toArchive !== null}
        title="Delete this map?"
        message={`"${toArchive?.name ?? ""}": If it has sessions or driver limits it is archived and its history is kept. A map that was never used is deleted for good.`}
        confirmText="Delete"
        variant="warning"
        onCancel={() => setToArchive(null)}
        onConfirm={() => {
          if (toArchive) maps.archiveMap(toArchive);
          setToArchive(null);
        }}
      />
      <ConfirmDialog
        isOpen={toDeleteForever !== null}
        title="Delete this map forever?"
        message={`"${toDeleteForever?.name ?? ""}" and its corners will be removed for good. This cannot be undone. A map that still has sessions cannot be deleted and stays archived.`}
        confirmText="Delete forever"
        variant="danger"
        onCancel={() => setToDeleteForever(null)}
        onConfirm={() => {
          if (toDeleteForever) maps.deleteForever(toDeleteForever);
          setToDeleteForever(null);
        }}
      />
    </div>
  );
}
