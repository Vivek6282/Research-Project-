/**
 * Trackside Maps — loads the map list (active or archived) and archives/deletes/restores maps.
 */

import { useCallback, useEffect, useState } from "react";
import { api } from "../../../lib/api";
import type { MapTrack } from "../types";

export type MapView = "active" | "archived";

interface ListResponse {
  results?: MapTrack[];
}

/** Holds the map list for the chosen filter plus archive/restore actions. */
export function useMaps(reloadKey = 0) {
  const [view, setView] = useState<MapView>("active");
  const [maps, setMaps] = useState<MapTrack[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  /** Load the list for the current view; shows a clear error instead of an empty list. */
  const load = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const query = view === "archived" ? "?archived=only" : "";
      const res = await api.get<ListResponse | MapTrack[]>(`/api/tracks/${query}`);
      const rows = Array.isArray(res) ? res : res.results ?? [];
      setMaps([...rows].sort((a, b) => a.name.localeCompare(b.name)));
    } catch (e) {
      setMaps([]);
      setError(e instanceof Error ? e.message : "Could not load maps.");
    } finally {
      setIsLoading(false);
    }
  }, [view, reloadKey]);

  useEffect(() => {
    load();
  }, [load]);

  /** Archive a map (or delete it for good when it was never used) and say which happened. */
  const archiveMap = useCallback(
    async (map: MapTrack) => {
      setNotice(null);
      try {
        const res = await api.delete<{ detail?: string }>(`/api/tracks/${map.id}/`);
        setNotice(res.detail ?? `"${map.name}" was deleted (it had no sessions).`);
        await load();
      } catch (e) {
        setError(e instanceof Error ? e.message : "Could not delete the map.");
      }
    },
    [load],
  );

  /** Delete an archived map for good; the server refuses (and says why) when it still has sessions. */
  const deleteForever = useCallback(
    async (map: MapTrack) => {
      setNotice(null);
      try {
        await api.delete(`/api/tracks/${map.id}/?permanent=true`);
        setNotice(`"${map.name}" was deleted for good.`);
        await load();
      } catch (e) {
        setError(e instanceof Error ? e.message : "Could not delete the map.");
      }
    },
    [load],
  );

  /** Bring an archived map back. */
  const restoreMap = useCallback(
    async (map: MapTrack) => {
      setNotice(null);
      try {
        await api.post(`/api/tracks/${map.id}/restore/`);
        setNotice(`"${map.name}" was restored.`);
        await load();
      } catch (e) {
        setError(e instanceof Error ? e.message : "Could not restore the map.");
      }
    },
    [load],
  );

  /** Show a message above the list (used after duplicating a map). */
  const announce = useCallback((message: string) => setNotice(message), []);

  return { announce, view, setView, maps, isLoading, error, notice, reload: load, archiveMap, deleteForever, restoreMap };
}
