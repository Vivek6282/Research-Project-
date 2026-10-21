/**
 * Trackside Maps — list of maps with Built-in / Archived badges and archive/restore actions.
 */

import { Archive, RotateCcw } from "lucide-react";
import { Chip } from "../../../components/ui/chip";
import { SOURCE_LABELS, type MapTrack } from "../types";

interface MapListProps {
  maps: MapTrack[];
  canManage: boolean;
  onArchive: (map: MapTrack) => void;
  onRestore: (map: MapTrack) => void;
}

const actionClass =
  "inline-flex items-center gap-1 text-[11px] font-mono px-2 py-1.5 min-h-[32px] rounded-[2px] border border-[#232B35] bg-[#161D26] text-[#7C8898] hover:text-[#3FA6E0] hover:border-[#3FA6E0] cursor-pointer";

/** One row per map; change buttons only show when the user may manage maps. */
export function MapList({ maps, canManage, onArchive, onRestore }: MapListProps) {
  if (maps.length === 0) {
    return (
      <p data-testid="maps-empty" className="text-xs font-mono text-[#7C8898] py-6 text-center">
        No maps here yet.
      </p>
    );
  }
  return (
    <ul className="flex flex-col gap-2" data-testid="map-list">
      {maps.map((map) => (
        <li
          key={map.id}
          data-testid={`map-row-${map.name}`}
          className="flex flex-wrap items-center justify-between gap-2 p-3 rounded bg-[#161D26] border border-[#232B35]"
        >
          <div className="min-w-0">
            <p className="text-sm font-semibold text-[#E7EDF3] truncate">{map.name}</p>
            <p className="text-[11px] font-mono text-[#7C8898]">
              {map.zones.length} {map.zones.length === 1 ? "corner" : "corners"} · {SOURCE_LABELS[map.source]}
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {map.is_builtin && <Chip color="#3FA6E0">Built-in</Chip>}
            {map.is_archived && <Chip color="#F2A93B">Archived</Chip>}
            {canManage && !map.is_builtin && !map.is_archived && (
              <button className={actionClass} onClick={() => onArchive(map)} data-testid={`archive-${map.name}`}>
                <Archive size={13} /> Archive
              </button>
            )}
            {canManage && !map.is_builtin && map.is_archived && (
              <button className={actionClass} onClick={() => onRestore(map)} data-testid={`restore-${map.name}`}>
                <RotateCcw size={13} /> Restore
              </button>
            )}
          </div>
        </li>
      ))}
    </ul>
  );
}
