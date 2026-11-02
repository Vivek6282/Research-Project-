/**
 * Trackside Maps — read-only list of the limit changes of one corner (newest first).
 */

import { useEffect, useState } from "react";
import { X } from "lucide-react";
import { api } from "../../../lib/api";

interface HistoryRow {
  id: string;
  old_g: number | null;
  new_g: number;
  changed_by_name: string | null;
  changed_at: string;
}

interface LimitHistoryDialogProps {
  trackId: string;
  zoneId: string;
  label: string;
  onClose: () => void;
}

/** The dialog; loads the rows when it opens. */
export function LimitHistoryDialog({ trackId, zoneId, label, onClose }: LimitHistoryDialogProps) {
  const [rows, setRows] = useState<HistoryRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api
      .get<{ results?: HistoryRow[] } | HistoryRow[]>(`/api/tracks/${trackId}/zones/${zoneId}/limit-history/`)
      .then((res) => !cancelled && setRows(Array.isArray(res) ? res : res.results ?? []))
      .catch((e) => !cancelled && setError(e instanceof Error ? e.message : "Could not load the history."));
    return () => {
      cancelled = true;
    };
  }, [trackId, zoneId]);

  return (
    <div className="fixed inset-0 z-[110] flex items-center justify-center bg-black/75 backdrop-blur-sm p-3" onClick={onClose}>
      <div onClick={(e) => e.stopPropagation()} data-testid="limit-history-dialog" role="dialog" aria-label={`Limit history of ${label}`}
        className="w-full max-w-md max-h-[85vh] overflow-y-auto bg-[#12181F] border border-[#232B35] rounded-[4px] shadow-2xl font-mono text-[#E7EDF3]">
        <div className="flex items-center justify-between px-4 py-3 border-b border-[#232B35] bg-[#161D26] sticky top-0">
          <span className="text-xs font-bold uppercase tracking-wider truncate">Limit history — {label}</span>
          <button aria-label="Close history" onClick={onClose} className="text-[#7C8898] hover:text-[#E7EDF3] cursor-pointer"><X size={16} /></button>
        </div>
        <div className="p-4 text-xs">
          {error && <p role="alert" data-testid="history-error" className="text-[#E5473C]">{error}</p>}
          {!error && rows === null && <p className="text-[#7C8898] animate-pulse">Loading…</p>}
          {rows && rows.length === 0 && <p data-testid="history-empty" className="text-[#7C8898]">No limit changes recorded for this corner yet.</p>}
          {rows && rows.length > 0 && (
            <ul data-testid="history-list" className="flex flex-col gap-2">
              {rows.map((r) => (
                <li key={r.id} className="flex flex-wrap justify-between gap-x-3 border-b border-[#232B35] pb-2">
                  <span>{r.old_g === null ? "Set to" : `${r.old_g} g →`} <b>{r.new_g} g</b></span>
                  <span className="text-[#7C8898]">{r.changed_by_name ?? "Unknown"} · {new Date(r.changed_at).toLocaleString()}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}
