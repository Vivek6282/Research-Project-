/**
 * Trackside Maps — the map browser: Active/Archived filter, map cards, Add track wizard and
 * archive confirmation. One component, used by the Coach "Maps & Demo" tab and the /maps page,
 * so both always behave the same.
 */

import { useState, type ReactNode } from "react";
import { Plus } from "lucide-react";
import { ConfirmDialog } from "../../../components/ui/confirm-dialog";
import { useMaps, type MapView } from "../hooks/use-maps";
import type { MapTrack } from "../types";
import { AddMapWizard } from "./add-map-wizard";
import { CornerEditorDialog } from "./corner-editor-dialog";
import { MapCardGrid } from "./map-card-grid";

const VIEW_TABS: { id: MapView; label: string }[] = [
  { id: "active", label: "Active" },
  { id: "archived", label: "Archived" },
];

export interface MapsBrowserProps {
  /** Coach and Admin: add, archive and restore maps */
  canManage: boolean;
  /** Called with a map when its Play demo button is pressed; leave out to hide the button */
  onPlay?: (map: MapTrack) => void;
  /** Why Play is switched off right now, or null */
  playDisabledReason?: string | null;
  /** Coach and Admin: show Edit corners (the built-in and archived maps open view-only) */
  canEditCorners?: boolean;
  /** Bump this number to make the list reload (for example after the corner editor saves) */
  reloadKey?: number;
  /** Extra content shown above the cards (for example the demo status panel) */
  children?: ReactNode;
}

/** The browser itself. */
export function MapsBrowser({ canManage, onPlay, playDisabledReason, canEditCorners = false, reloadKey = 0, children }: MapsBrowserProps) {
  const maps = useMaps(canManage, reloadKey);
  const [editing, setEditing] = useState<MapTrack | null>(null);
  const [showWizard, setShowWizard] = useState(false);
  const [toArchive, setToArchive] = useState<MapTrack | null>(null);

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
          <button
            data-testid="add-map-btn"
            onClick={() => setShowWizard(true)}
            className="inline-flex items-center gap-1.5 text-xs font-mono font-bold px-3 py-2 min-h-[36px] rounded-[2px] bg-[#3FA6E0] text-[#06121B] cursor-pointer"
          >
            <Plus size={14} /> Add track
          </button>
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
      <ConfirmDialog
        isOpen={toArchive !== null}
        title="Archive this map?"
        message={`"${toArchive?.name ?? ""}": if it has sessions or driver limits it is archived and its history is kept. A map that was never used is deleted for good.`}
        confirmText="Archive"
        variant="warning"
        onCancel={() => setToArchive(null)}
        onConfirm={() => {
          if (toArchive) maps.archiveMap(toArchive);
          setToArchive(null);
        }}
      />
    </div>
  );
}
