/**
 * Trackside Maps — grid of map cards, shared by the Coach "Maps & Demo" tab and the /maps page.
 * Which buttons appear depends on what the caller allows; the server checks every action again.
 */

import { Archive, Pencil, Play, RotateCcw } from "lucide-react";
import { Chip } from "../../../components/ui/chip";
import { SOURCE_LABELS, type MapTrack } from "../types";
import { OutlineThumbnail } from "./outline-thumbnail";

export interface MapCardActions {
  /** Show Archive / Restore buttons */
  canArchive: boolean;
  /** Opens the corner editor; the button is hidden when this is missing */
  onEditCorners?: (map: MapTrack) => void;
  /** Starts the Play demo dialog; the button is hidden when this is missing */
  onPlay?: (map: MapTrack) => void;
  /** Why Play is switched off right now (for example a demo is running) */
  playDisabledReason?: string | null;
  onArchive: (map: MapTrack) => void;
  onRestore: (map: MapTrack) => void;
}

interface MapCardGridProps extends MapCardActions {
  maps: MapTrack[];
}

const buttonClass =
  "inline-flex items-center gap-1 text-[11px] font-mono px-2 py-1.5 min-h-[32px] rounded-[2px] border border-[#232B35] bg-[#161D26] text-[#7C8898] hover:text-[#3FA6E0] hover:border-[#3FA6E0] cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed";

/** One card: thumbnail, name, badges, corner count and the allowed buttons. */
function MapCard({ map, actions }: { map: MapTrack; actions: MapCardActions }) {
  const outline = map.reference_line && map.reference_line.length > 2 ? map.reference_line : map.schematic_outline;
  const corners = map.zones.length;
  return (
    <li
      data-testid={`map-card-${map.name}`}
      className="flex flex-col gap-2 p-3 rounded bg-[#161D26] border border-[#232B35]"
    >
      <OutlineThumbnail points={outline} label={map.name} />
      <div className="min-w-0">
        <p className="text-sm font-semibold text-[#E7EDF3] truncate">{map.name}</p>
        <p data-testid={`map-card-corners-${map.name}`} className="text-[11px] font-mono text-[#7C8898]">
          {corners} alert {corners === 1 ? "corner" : "corners"} · {SOURCE_LABELS[map.source]}
        </p>
      </div>
      <div className="flex flex-wrap gap-1.5 min-h-[22px]">
        {map.is_builtin && <Chip color="#3FA6E0">Built-in</Chip>}
        {map.is_builtin && <Chip color="#33D17E">Simulator map</Chip>}
        {map.is_schematic && <Chip color="#7C8898">Schematic</Chip>}
        {map.is_archived && <Chip color="#F2A93B">Archived</Chip>}
      </div>
      <div className="flex flex-wrap gap-1.5 mt-auto">
        {actions.onPlay && !map.is_archived && (
          <button
            className={buttonClass}
            data-testid={`play-${map.name}`}
            disabled={Boolean(actions.playDisabledReason)}
            title={actions.playDisabledReason ?? "Play a demo on this map"}
            onClick={() => actions.onPlay?.(map)}
          >
            <Play size={13} /> Play demo
          </button>
        )}
        {actions.onEditCorners && (
          <button className={buttonClass} data-testid={`edit-corners-${map.name}`} onClick={() => actions.onEditCorners?.(map)}>
            <Pencil size={13} /> {map.is_builtin || map.is_archived ? "View corners" : "Edit corners"}
          </button>
        )}
        {actions.canArchive && !map.is_builtin && !map.is_archived && (
          <button className={buttonClass} data-testid={`archive-${map.name}`} onClick={() => actions.onArchive(map)}>
            <Archive size={13} /> Archive
          </button>
        )}
        {actions.canArchive && !map.is_builtin && map.is_archived && (
          <button className={buttonClass} data-testid={`restore-${map.name}`} onClick={() => actions.onRestore(map)}>
            <RotateCcw size={13} /> Restore
          </button>
        )}
      </div>
    </li>
  );
}

/** The grid; says so when there is nothing to show. */
export function MapCardGrid({ maps, ...actions }: MapCardGridProps) {
  if (maps.length === 0) {
    return (
      <p data-testid="maps-empty" className="text-xs font-mono text-[#7C8898] py-6 text-center">
        No maps here yet.
      </p>
    );
  }
  return (
    <ul data-testid="map-list" className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
      {maps.map((map) => (
        <MapCard key={map.id} map={map} actions={actions} />
      ))}
    </ul>
  );
}
