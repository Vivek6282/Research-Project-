/**
 * Trackside Maps — loads the map list (active or archived) and archives/restores maps.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../../../lib/api";
import type { MapTrack } from "../types";

export type MapView = "active" | "archived";

interface ListResponse {
  results?: MapTrack[];
}

/** Holds the map list for the chosen filter plus archive/restore actions. */
export function useMaps(ensureDemoCircuit = false, reloadKey = 0) {
  const [view, setView] = useState<MapView>("active");
  const [maps, setMaps] = useState<MapTrack[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  // Ask the server to create the Demo Circuit only once per screen (React may run effects twice in development)
  const demoCircuitAsked = useRef<Promise<unknown> | null>(null);

  /** Load the list for the current view; shows a clear error instead of an empty list. */
  const load = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      // Coach and Admin: make sure the built-in Demo Circuit exists before listing (safe to repeat)
      if (ensureDemoCircuit) {
        demoCircuitAsked.current ??= api.post("/api/tracks/demo-circuit/").catch(() => undefined);
        await demoCircuitAsked.current;
      }
      const query = view === "archived" ? "?archived=only" : "";
      const res = await api.get<ListResponse | MapTrack[]>(`/api/tracks/${query}`);
      const rows = Array.isArray(res) ? res : res.results ?? [];
      // The built-in Demo Circuit always comes first, then the rest by name
      setMaps([...rows].sort((a, b) => Number(b.is_builtin) - Number(a.is_builtin) || a.name.localeCompare(b.name)));
    } catch (e) {
      setMaps([]);
      setError(e instanceof Error ? e.message : "Could not load maps.");
    } finally {
      setIsLoading(false);
    }
  }, [view, ensureDemoCircuit, reloadKey]);

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
        setError(e instanceof Error ? e.message : "Could not archive the map.");
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

  return { view, setView, maps, isLoading, error, notice, reload: load, archiveMap, restoreMap };
}
