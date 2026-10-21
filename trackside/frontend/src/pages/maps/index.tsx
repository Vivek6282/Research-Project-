/**
 * Trackside — Maps page.
 *
 * Coach and Admin: list maps, add a map from a RaceChrono/VBO export, archive and restore.
 * Drivers can see the maps but nothing here lets them change one (the server enforces it too).
 */

import { useState } from "react";
import { Link } from "react-router-dom";
import { ArrowLeft, Plus } from "lucide-react";
import { TopBar } from "../../components/shell/top-bar";
import { ConfirmDialog } from "../../components/ui/confirm-dialog";
import { Panel } from "../../components/ui/panel";
import { useAuth } from "../../lib/auth";
import { AddMapWizard } from "./components/add-map-wizard";
import { MapList } from "./components/map-list";
import { useMaps, type MapView } from "./hooks/use-maps";
import type { MapTrack } from "./types";

const TABS: { id: MapView; label: string }[] = [
  { id: "active", label: "Active" },
  { id: "archived", label: "Archived" },
];

/** The Maps screen: list, filter, add, archive and restore maps. */
export function MapsPage() {
  const { user } = useAuth();
  const maps = useMaps();
  const [showWizard, setShowWizard] = useState(false);
  const [toArchive, setToArchive] = useState<MapTrack | null>(null);
  const canManage = user?.role === "admin" || user?.role === "coach";

  return (
    <div className="min-h-screen" style={{ background: "var(--color-bg)" }}>
      <TopBar />
      <main className="max-w-[1400px] mx-auto px-3 sm:px-4 py-4 flex flex-col gap-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-3">
            <Link
              to={`/${user?.role ?? "login"}`}
              data-testid="maps-back-link"
              className="inline-flex items-center gap-1 text-[11px] font-mono text-[#7C8898] hover:text-[#3FA6E0]"
            >
              <ArrowLeft size={13} /> Dashboard
            </Link>
            <h1 className="text-sm font-mono uppercase tracking-widest text-[#E7EDF3]">Maps</h1>
          </div>
          {canManage && (
            <button
              data-testid="add-map-btn"
              onClick={() => setShowWizard(true)}
              className="inline-flex items-center gap-1.5 text-xs font-mono font-bold px-3 py-2 min-h-[36px] rounded-[2px] bg-[#3FA6E0] text-[#06121B] cursor-pointer"
            >
              <Plus size={14} /> Add map
            </button>
          )}
        </div>

        <Panel title="Track maps">
          <div className="flex gap-2 mb-3" role="tablist">
            {TABS.map((tab) => (
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
          {maps.notice && <p data-testid="maps-notice" className="text-xs text-[#3FA6E0] mb-2">{maps.notice}</p>}
          {maps.error && <p data-testid="maps-error" role="alert" className="text-xs text-[#E5473C] mb-2">{maps.error}</p>}
          {maps.isLoading ? (
            <p className="text-xs font-mono text-[#7C8898] animate-pulse">Loading maps…</p>
          ) : (
            <MapList maps={maps.maps} canManage={canManage} onArchive={setToArchive} onRestore={maps.restoreMap} />
          )}
        </Panel>
      </main>

      {showWizard && (
        <AddMapWizard
          onClose={() => setShowWizard(false)}
          onSaved={() => {
            setShowWizard(false);
            maps.reload();
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
